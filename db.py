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
from datetime import datetime
from config import RIDE_LATEST
from timeutil import today_str, now_bogota

# New Vercel Blob HTTP API (private stores live here, not blob.vercel-storage.com).
BLOB_API_BASE = "https://vercel.com/api/blob"
BLOB_PATHNAME = "predictions.json"
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
        raise RuntimeError(f"{label} → HTTP {e.code}: {body[:500]}") from e


# ---------- Low-level blob HTTP helpers ----------

def _list_blobs(prefix):
    url = f"{BLOB_API_BASE}/?prefix={urllib.parse.quote(prefix)}&limit=10"
    req = urllib.request.Request(url, headers=_api_headers())
    with _do_request(req, "blob list") as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_url():
    """Return a CDN-cache-bypassing URL for predictions.json, or None.

    Vercel Blob serves the blob URL through a CDN that caches for up to
    60 seconds even with `cache-control: private`, which causes stale
    read-after-write. The list endpoint (vercel.com/api/blob) bypasses
    that CDN and always returns the latest etag, so we use the etag as
    a cache-buster query string. Since the etag changes on every write,
    the cache key changes too and we get fresh content automatically.
    """
    try:
        data = _list_blobs(BLOB_PATHNAME)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    for b in data.get("blobs", []):
        if b.get("pathname") == BLOB_PATHNAME:
            base = b.get("url")
            etag = (b.get("etag") or "").strip('"')
            if base and etag:
                sep = "&" if "?" in base else "?"
                return f"{base}{sep}v={etag}"
            return base
    return None


def _read_all():
    """Read the full prediction log from blob. Returns {'predictions': [...]}."""
    url = _find_url()
    if not url:
        return {"predictions": []}
    # Private blob URLs require the bearer token to download.
    req = urllib.request.Request(url, headers={
        "user-agent": "PalmasRide/1.0",
        "authorization": f"Bearer {_token()}",
    })
    with _do_request(req, "blob get") as resp:
        try:
            return json.loads(resp.read().decode("utf-8"))
        except json.JSONDecodeError:
            return {"predictions": []}


def _write_all(data):
    """Overwrite predictions.json in the blob store with `data`."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    url = f"{BLOB_API_BASE}/?pathname={urllib.parse.quote(BLOB_PATHNAME)}"
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
    req = urllib.request.Request(url, data=body, method="PUT", headers=headers)
    with _do_request(req, "blob put") as resp:
        return json.loads(resp.read().decode("utf-8"))


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
                    forecast_avg_humidity=None, forecast_overnight_precip_mm=None):
    """Save or update the prediction for ride_date.

    Updates only if actuals haven't been filled in yet — once a day is
    evaluated, the prediction is frozen.
    """
    if not is_enabled():
        return

    log = _read_all()
    preds = log.get("predictions", [])
    by_date = _by_date(preds)
    existing = by_date.get(ride_date)

    if existing and existing.get("actual") is not None:
        return  # already finalized — don't overwrite

    entry = {
        "ride_date": ride_date,
        "predicted_at": existing["predicted_at"] if existing else _now_iso(),
        "last_updated_at": _now_iso(),
        "score": score,
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "forecast": {
            "avg_precip_prob": forecast_avg_precip_prob,
            "max_wind": forecast_max_wind,
            "avg_humidity": forecast_avg_humidity,
            "overnight_precip_mm": forecast_overnight_precip_mm,
        },
        "actual": existing.get("actual") if existing else None,
        "correct": existing.get("correct") if existing else None,
    }

    by_date[ride_date] = entry
    log["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
    _write_all(log)


def pending_actuals():
    """Return ride_dates with a prediction but no actuals yet, where the
    ride window has already finished (past day, or today after RIDE_LATEST)."""
    if not is_enabled():
        return []
    now = now_bogota()
    today = now.strftime("%Y-%m-%d")
    # Ride window ends at RIDE_LATEST + 0.5 hour (the +1 hour slot covers 7:00–7:59).
    # Wait until after 08:00 Bogota to ensure Open-Meteo has the final hour.
    window_closed_today = now.hour >= RIDE_LATEST + 1
    log = _read_all()
    out = []
    for p in log.get("predictions", []):
        if p.get("actual") is not None:
            continue
        rd = p["ride_date"]
        if rd < today:
            out.append(rd)
        elif rd == today and window_closed_today:
            out.append(rd)
    return out


def save_actuals(ride_date, actual_precip_mm, actual_max_wind, actual_rained):
    """Fill in observed weather and compute the correctness verdict."""
    if not is_enabled():
        return
    log = _read_all()
    preds = log.get("predictions", [])
    by_date = _by_date(preds)
    entry = by_date.get(ride_date)
    if not entry:
        return

    entry["actual"] = {
        "precip_mm": actual_precip_mm,
        "max_wind": actual_max_wind,
        "rained": actual_rained,
        "updated_at": _now_iso(),
    }
    decision = entry.get("decision")
    if decision == "YES":
        entry["correct"] = not actual_rained
    elif decision == "NO":
        entry["correct"] = bool(actual_rained)
    else:
        entry["correct"] = None

    log["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
    _write_all(log)


def fetch_history(limit=60):
    """Return recent predictions newest-first plus aggregate stats."""
    if not is_enabled():
        return {"enabled": False, "predictions": [], "stats": None}

    log = _read_all()
    preds = sorted(log.get("predictions", []), key=lambda p: p["ride_date"], reverse=True)

    total = len(preds)
    evaluated = sum(1 for p in preds if p.get("actual") is not None)
    correct = sum(1 for p in preds if p.get("correct") is True)
    wrong = sum(1 for p in preds if p.get("correct") is False)
    accuracy = round(100 * correct / evaluated, 1) if evaluated else None

    return {
        "enabled": True,
        "stats": {
            "total_predictions": total,
            "evaluated": evaluated,
            "pending": total - evaluated,
            "correct": correct,
            "wrong": wrong,
            "accuracy_pct": accuracy,
        },
        "predictions": preds[:limit],
    }
