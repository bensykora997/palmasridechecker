"""Vercel Blob-backed logging for predictions and actuals.

Stores the entire prediction log as a single JSON file (`predictions.json`)
in a private Vercel Blob store. Read-modify-write on every operation.
For low volume (≈1 write/day) this is fine — no concurrency control needed.

Env vars (Vercel auto-injects when the Blob store is linked):
  - BLOB_READ_WRITE_TOKEN  (required; store ID is also embedded in this token)
  - BLOB_STORE_ID          (optional; if absent, derived from the token)

If no token is set, every function becomes a no-op so the app keeps working
without logging.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from timeutil import today_str, now_bogota, MORNING_CUTOFF_HOUR

# New Vercel Blob HTTP API (private stores live here, not blob.vercel-storage.com).
BLOB_API_BASE = "https://vercel.com/api/blob"
BLOB_PATHNAME = "predictions.json"
CALIBRATION_PATHNAME = "calibration.json"
BLOB_API_VERSION = os.environ.get("BLOB_API_VERSION", "12")


def _token():
    return os.environ.get("BLOB_READ_WRITE_TOKEN")


def _store_id():
    """Return the store ID without the `store_` prefix.

    Vercel sets BLOB_STORE_ID like `store_yVKRNAdf4uRCMRTa`. The header
    `x-vercel-blob-store-id` expects just `yVKRNAdf4uRCMRTa`. If
    BLOB_STORE_ID isn't set, the token format is
    `vercel_blob_rw_<storeId>_<secret>` so we can parse it out.
    """
    sid = os.environ.get("BLOB_STORE_ID", "")
    if sid.startswith("store_"):
        return sid[len("store_"):]
    if sid:
        return sid
    tok = _token() or ""
    if tok.startswith("vercel_blob_rw_"):
        parts = tok.split("_")
        if len(parts) >= 5:
            return parts[3]
    return ""


def is_enabled():
    return bool(_token() and _store_id())


def _api_headers():
    return {
        "authorization": f"Bearer {_token()}",
        "x-api-version": BLOB_API_VERSION,
        "x-vercel-blob-store-id": _store_id(),
    }


class BlobHTTPError(RuntimeError):
    """A blob API call returned a non-2xx status. Carries the HTTP code so
    callers can branch (404 = missing, 412 = precondition / write conflict)."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class _BlobConflict(RuntimeError):
    """A conditional write was rejected because the blob changed under us."""


def _do_request(req, label):
    """Surface API error bodies instead of urllib's bare 'HTTP 400'."""
    try:
        return urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise BlobHTTPError(e.code, f"{label} → HTTP {e.code}: {body[:500]}") from e


# ---------- Low-level blob HTTP helpers ----------

def _list_blobs(prefix):
    url = f"{BLOB_API_BASE}/?prefix={urllib.parse.quote(prefix)}&limit=10"
    req = urllib.request.Request(url, headers=_api_headers())
    with _do_request(req, "blob list") as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_url_and_etag(pathname=BLOB_PATHNAME):
    """Return (cache-bypassing URL, etag) for `pathname`, or (None, None).

    Vercel Blob serves the blob URL through a CDN that caches for up to
    60 seconds even with `cache-control: private`, which causes stale
    read-after-write. The list endpoint (vercel.com/api/blob) bypasses
    that CDN and always returns the latest etag, so we use the etag as
    a cache-buster query string. Since the etag changes on every write,
    the cache key changes too and we get fresh content automatically. The
    etag is also our optimistic-concurrency token (see `_mutate`).
    """
    try:
        data = _list_blobs(pathname)
    except BlobHTTPError as e:
        if e.code == 404:
            return None, None
        raise
    for b in data.get("blobs", []):
        if b.get("pathname") == pathname:
            base = b.get("url")
            etag = (b.get("etag") or "").strip('"')
            if base and etag:
                sep = "&" if "?" in base else "?"
                return f"{base}{sep}v={etag}", etag
            return base, (etag or None)
    return None, None


def _find_url(pathname=BLOB_PATHNAME):
    return _find_url_and_etag(pathname)[0]


def _current_etag(pathname=BLOB_PATHNAME):
    return _find_url_and_etag(pathname)[1]


def _get_blob(pathname, raise_on_corrupt=False):
    """Fetch and JSON-parse `pathname`. Returns (data, etag).

    (None, None) if the blob doesn't exist. If the blob EXISTS but its body
    doesn't parse as JSON, returning an empty default would let the next write
    overwrite real data with nothing (silent history wipe) — so when
    `raise_on_corrupt` is set we raise instead; otherwise we return (None, etag)
    for regenerable data (e.g. calibration) that can simply be rebuilt.
    """
    url, etag = _find_url_and_etag(pathname)
    if not url:
        return None, None
    # Private blob URLs require the bearer token to download.
    req = urllib.request.Request(url, headers={
        "user-agent": "PalmasRide/1.0",
        "authorization": f"Bearer {_token()}",
    })
    with _do_request(req, "blob get") as resp:
        raw = resp.read().decode("utf-8")
    try:
        return json.loads(raw), etag
    except json.JSONDecodeError as e:
        if raise_on_corrupt:
            raise RuntimeError(
                f"{pathname} exists but did not parse as JSON ({len(raw)} bytes) "
                f"— refusing to treat as empty (would wipe data on next write)"
            ) from e
        return None, etag


def _read_blob(pathname, default):
    """Read and JSON-parse `pathname`. Returns `default` if the blob doesn't
    exist (or, for regenerable data, can't be parsed)."""
    data, _ = _get_blob(pathname)
    return default if data is None else data


def _write_blob(pathname, data, if_match=None):
    """Overwrite `pathname` in the blob store with `data` (JSON-serialized).

    When `if_match` (an etag) is given it is sent as a precondition; a store
    that honors it rejects the write with HTTP 412 if the blob changed since,
    which we surface as `_BlobConflict` so `_mutate` can retry.
    """
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    url = f"{BLOB_API_BASE}/?pathname={urllib.parse.quote(pathname)}"
    headers = {
        **_api_headers(),
        "x-vercel-blob-access": "private",
        "x-content-type": "application/json",
        "x-add-random-suffix": "0",
        "x-allow-overwrite": "1",
        "x-cache-control-max-age": "0",
        "content-type": "application/json",
        "content-length": str(len(body)),
    }
    if if_match:
        headers["if-match"] = if_match
    req = urllib.request.Request(url, data=body, method="PUT", headers=headers)
    try:
        with _do_request(req, "blob put") as resp:
            return json.loads(resp.read().decode("utf-8"))
    except BlobHTTPError as e:
        if e.code == 412:
            raise _BlobConflict(str(e)) from e
        raise


def _read_all_with_etag():
    """Read the full prediction log + its etag. Returns ({'predictions': [...]},
    etag-or-None). Raises if the blob exists but is corrupt or mis-shaped, so a
    bad read can never be mistaken for an empty log (which a write would then
    make permanent)."""
    data, etag = _get_blob(BLOB_PATHNAME, raise_on_corrupt=True)
    if data is None:
        return {"predictions": []}, None  # blob doesn't exist yet — legit empty
    if not isinstance(data, dict) or not isinstance(data.get("predictions"), list):
        raise RuntimeError(
            "predictions blob has an unexpected shape — refusing to treat as "
            "empty (would wipe history on next write)"
        )
    return data, etag


def _read_all():
    """Read the full prediction log from blob. Returns {'predictions': [...]}."""
    return _read_all_with_etag()[0]


def _write_all(data, if_match=None):
    """Overwrite predictions.json in the blob store with `data`."""
    return _write_blob(BLOB_PATHNAME, data, if_match=if_match)


# Sentinel a mutator returns to signal "no change — don't write".
_UNCHANGED = object()


def _mutate(apply_fn, retries=4):
    """Read-modify-write predictions.json with optimistic concurrency.

    `apply_fn(data)` may mutate the {'predictions': [...]} dict in place and
    returns the caller's result, or `_UNCHANGED` to skip the write entirely.

    Between our read and our write a concurrent serverless invocation may have
    committed (e.g. /api/check logging while /api/override is saving). We hold
    the etag from the read, re-check it just before writing, and also send it
    as an If-Match precondition; either signal of a change makes us re-read and
    re-apply rather than clobber the other write. This is what stops a routine
    prediction log from silently erasing a hand-entered ground-truth override.
    """
    for _ in range(retries):
        data, etag = _read_all_with_etag()
        result = apply_fn(data)
        if result is _UNCHANGED:
            return None
        if etag is not None and _current_etag() not in (None, etag):
            continue  # blob moved during our modify window — retry on fresh data
        try:
            _write_all(data, if_match=etag)
            return result
        except _BlobConflict:
            continue
    # Retries exhausted under contention: re-apply on the freshest copy and
    # write best-effort so the caller's change isn't dropped entirely.
    data, _ = _read_all_with_etag()
    result = apply_fn(data)
    if result is _UNCHANGED:
        return None
    _write_all(data)
    return result


# ---------- Calibration state (calibration.json) ----------

def read_calibration():
    """Return the stored calibration state dict, or None if not yet trained."""
    if not is_enabled():
        return None
    return _read_blob(CALIBRATION_PATHNAME, None)


def write_calibration(state):
    """Persist the calibration state dict to calibration.json."""
    if not is_enabled():
        return
    _write_blob(CALIBRATION_PATHNAME, state)


# ---------- Public API (same shape as the original) ----------

def init_schema():
    """No-op for blob storage."""
    return


def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _by_date(predictions):
    return {p["ride_date"]: p for p in predictions}


def save_prediction(ride_date, score, decision, confidence, reasons,
                    forecast_avg_precip_prob=None, forecast_max_wind=None,
                    forecast_avg_humidity=None, forecast_overnight_precip_mm=None,
                    station_snapshots=None, shadow=None, morning=False):
    """Save or update the prediction for ride_date.

    Updates only if actuals haven't been filled in yet — once a day is
    evaluated, the prediction is frozen.

    station_snapshots: optional list of {name, code, valor, p10m, p1h, p24h}
    captured from SIATA at prediction time. Used for the audit trail.

    shadow: optional {shadow_decision, shadow_prob_rain, shadow_basis, stage}
    — what the calibration model (as trained at the time) would have predicted.
    Recorded so the shadow model accrues its own real-time track record.

    morning: when True this is a pre-dawn ("this morning") re-score. The
    canonical night-before prediction (score/decision/shadow/correct) is left
    UNTOUCHED and the re-score is recorded in a separate `morning` slot as
    observational data only. Calibration grades the canonical prediction, not
    the morning slot. If no canonical entry exists yet (night-before run was
    missed), we fall back to writing it as canonical so there's always
    something to grade.
    """
    if not is_enabled():
        return

    def apply(data):
        by_date = _by_date(data.get("predictions", []))
        existing = by_date.get(ride_date)

        if existing and existing.get("actual") is not None:
            return _UNCHANGED  # already finalized — don't overwrite

        # Morning observation: don't disturb the canonical prediction.
        if morning and existing is not None:
            existing["morning"] = {
                "score": score,
                "decision": decision,
                "confidence": confidence,
                "shadow": shadow,
                "at": _now_iso(),
            }
            existing["last_updated_at"] = _now_iso()
            by_date[ride_date] = existing
            data["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
            return existing

        forecast = {
            "avg_precip_prob": forecast_avg_precip_prob,
            "max_wind": forecast_max_wind,
            "avg_humidity": forecast_avg_humidity,
            "overnight_precip_mm": forecast_overnight_precip_mm,
        }
        if station_snapshots is not None:
            forecast["station_snapshots"] = station_snapshots

        entry = {
            "ride_date": ride_date,
            "predicted_at": existing["predicted_at"] if existing else _now_iso(),
            "last_updated_at": _now_iso(),
            "score": score,
            "decision": decision,
            "confidence": confidence,
            "reasons": reasons,
            "forecast": forecast,
            "actual": existing.get("actual") if existing else None,
        }
        # Preserve an existing shadow if the caller didn't supply a fresh one.
        if shadow is not None:
            entry["shadow"] = shadow
        elif existing and existing.get("shadow") is not None:
            entry["shadow"] = existing["shadow"]
        # Preserve any existing morning observation across canonical refreshes.
        if existing and existing.get("morning") is not None:
            entry["morning"] = existing["morning"]
        # Edge case: morning re-score with no prior canonical entry — mirror it
        # into the morning slot too, so the observation is still captured.
        if morning:
            entry["morning"] = {
                "score": score, "decision": decision,
                "confidence": confidence, "shadow": shadow, "at": _now_iso(),
            }
        # Preserve a manual ground-truth override across canonical refreshes.
        # Without this, a re-score of a not-yet-finalized overridden day would
        # silently drop the override (and leave `correct` inconsistent with it).
        if existing and existing.get("user_override") is not None:
            entry["user_override"] = existing["user_override"]
        # Re-derive correctness from the preserved actual + override.
        entry["correct"] = _compute_correct(entry)

        by_date[ride_date] = entry
        data["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
        return entry

    _mutate(apply)


# Open-Meteo's forecast endpoint reliably serves past observations roughly
# this far back (matches fetch_openmeteo.fetch_actuals_for_date's past_days
# cap). Pending dates older than this can't be observed any more, so we leave
# them pending rather than label them from unrelated live data.
MAX_BACKFILL_AGE_DAYS = 14


def pending_actuals():
    """Return ride_dates with a prediction but no actuals yet that we can
    still evaluate honestly.

    Two guards keep the ground-truth labels trustworthy (see code review):
      - Same-day isn't eligible until MORNING_CUTOFF_HOUR (08:00), so we never
        freeze a verdict before the 05:00-07:30 window has actually finished
        (#2). The ride window technically ends 07:30; 08:00 gives the hourly
        observation time to publish.
      - Dates older than MAX_BACKFILL_AGE_DAYS are skipped (#1): Open-Meteo can
        no longer serve their observations, and labeling them from any live
        signal would be fabricated. They stay pending rather than mislabeled.
    """
    if not is_enabled():
        return []
    now = now_bogota()
    today = now.strftime("%Y-%m-%d")
    oldest = (now - timedelta(days=MAX_BACKFILL_AGE_DAYS)).strftime("%Y-%m-%d")
    window_closed_today = now.hour >= MORNING_CUTOFF_HOUR
    log = _read_all()
    out = []
    for p in log.get("predictions", []):
        if p.get("actual") is not None:
            continue
        rd = p["ride_date"]
        if rd < today:
            if rd >= oldest:
                out.append(rd)
        elif rd == today and window_closed_today:
            out.append(rd)
    return out


def save_actuals(ride_date, actual_precip_mm, actual_max_wind, actual_rained,
                 open_meteo_precip_mm=None, siata_p24h_avg_mm=None,
                 siata_p24h_max_mm=None, source=None,
                 disagreement_mm=None, station_snapshots=None):
    """Fill in observed weather and compute the correctness verdict.

    Extra fields (all optional) form an audit trail for the dual-source
    rain capture: which source the precip_mm value came from, what each
    source reported, and what each corridor station was reading.
    """
    if not is_enabled():
        return

    def apply(data):
        by_date = _by_date(data.get("predictions", []))
        entry = by_date.get(ride_date)
        if not entry:
            return _UNCHANGED

        actual = {
            "precip_mm": actual_precip_mm,
            "max_wind": actual_max_wind,
            "rained": actual_rained,
            "updated_at": _now_iso(),
        }
        if open_meteo_precip_mm is not None:
            actual["open_meteo_precip_mm"] = open_meteo_precip_mm
        if siata_p24h_avg_mm is not None:
            actual["siata_p24h_avg_mm"] = siata_p24h_avg_mm
        if siata_p24h_max_mm is not None:
            actual["siata_p24h_max_mm"] = siata_p24h_max_mm
        if source is not None:
            actual["source"] = source
        if disagreement_mm is not None:
            actual["disagreement_mm"] = disagreement_mm
        if station_snapshots is not None:
            actual["station_snapshots"] = station_snapshots
        entry["actual"] = actual
        entry["correct"] = _compute_correct(entry)

        data["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
        return entry

    _mutate(apply)


def _ground_truth_rained(entry):
    """Return the best-known answer to 'did it actually rain?' for an entry.

    User overrides take priority over auto-detected actuals. Returns None
    if neither is set (entry is still pending).
    """
    ov = entry.get("user_override") or {}
    if ov.get("rained") is not None:
        return bool(ov["rained"])
    actual = entry.get("actual") or {}
    if actual.get("rained") is not None:
        return bool(actual["rained"])
    return None


def _compute_correct(entry):
    """Re-derive the correctness verdict from the prediction + ground truth.

    Pure function over the entry's existing fields — call this any time
    user_override or actual changes.
    """
    truth = _ground_truth_rained(entry)
    if truth is None:
        return None
    decision = entry.get("decision")
    if decision == "YES":
        return not truth
    if decision == "NO":
        return bool(truth)
    return None


def set_override(ride_date, rained, note=None):
    """Set or update the user's ground-truth override for a ride_date.

    `rained` should be a bool. Pass `note` for an optional free-text comment.
    Recomputes `correct` from the override.
    """
    if not is_enabled():
        return None

    def apply(data):
        by_date = _by_date(data.get("predictions", []))
        entry = by_date.get(ride_date)
        if not entry:
            return _UNCHANGED

        override = {
            "rained": bool(rained),
            "set_at": _now_iso(),
        }
        if note:
            override["note"] = note
        entry["user_override"] = override
        entry["correct"] = _compute_correct(entry)

        data["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
        return entry

    return _mutate(apply)


def clear_override(ride_date):
    """Remove the user override. `correct` falls back to the auto-detected actual."""
    if not is_enabled():
        return None

    def apply(data):
        by_date = _by_date(data.get("predictions", []))
        entry = by_date.get(ride_date)
        if not entry:
            return _UNCHANGED

        if "user_override" in entry:
            del entry["user_override"]
        entry["correct"] = _compute_correct(entry)

        data["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
        return entry

    return _mutate(apply)


def fetch_history(limit=60):
    """Return recent predictions newest-first plus aggregate stats."""
    if not is_enabled():
        return {"enabled": False, "predictions": [], "stats": None}

    log = _read_all()
    preds = sorted(log.get("predictions", []), key=lambda p: p["ride_date"], reverse=True)

    total = len(preds)
    # An entry counts as evaluated if we have ANY ground truth — auto-detected
    # actual OR a user override.
    evaluated = sum(1 for p in preds if _ground_truth_rained(p) is not None)
    correct = sum(1 for p in preds if p.get("correct") is True)
    wrong = sum(1 for p in preds if p.get("correct") is False)
    overridden = sum(1 for p in preds if (p.get("user_override") or {}).get("rained") is not None)
    accuracy = round(100 * correct / evaluated, 1) if evaluated else None

    return {
        "enabled": True,
        "stats": {
            "total_predictions": total,
            "evaluated": evaluated,
            "pending": total - evaluated,
            "correct": correct,
            "wrong": wrong,
            "overridden": overridden,
            "accuracy_pct": accuracy,
        },
        "predictions": preds[:limit],
    }
