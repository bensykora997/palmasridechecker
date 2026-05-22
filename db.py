"""Vercel Blob-backed logging for predictions and actuals.

Stores the entire prediction log as a single JSON file (`predictions.json`)
in Vercel Blob. For low volume (≈1 write/day) this is fine — no concurrency
control needed.

Env vars required (Vercel auto-injects when the Blob store is linked):
  - BLOB_READ_WRITE_TOKEN  (always required)
  - BLOB_STORE_ID          (optional, useful for diagnostics)

If no token is set, every function becomes a no-op so the app keeps working
without logging.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

BLOB_API_HOST = "blob.vercel-storage.com"
BLOB_PATHNAME = "predictions.json"
# Allow overriding via env in case Vercel bumps the API version
BLOB_API_VERSION = os.environ.get("BLOB_API_VERSION", "7")


def _do_request(req, label):
    """Wrap urlopen so HTTP error bodies surface in logs instead of just '400'."""
    try:
        return urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"{label} → HTTP {e.code}: {body[:500]}") from e


def _token():
    return os.environ.get("BLOB_READ_WRITE_TOKEN")


def is_enabled():
    return bool(_token())


# ---------- Low-level blob HTTP helpers ----------

def _list_blobs(prefix):
    url = f"https://{BLOB_API_HOST}/?prefix={urllib.parse.quote(prefix)}&limit=10"
    req = urllib.request.Request(url, headers={
        "authorization": f"Bearer {_token()}",
        "x-api-version": BLOB_API_VERSION,
    })
    with _do_request(req, "blob list") as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_url():
    """Return the URL of predictions.json in the blob store, or None."""
    try:
        data = _list_blobs(BLOB_PATHNAME)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    for b in data.get("blobs", []):
        if b.get("pathname") == BLOB_PATHNAME:
            return b.get("url")
    return None


def _read_all():
    """Read the full prediction log from blob. Returns {'predictions': [...]}."""
    url = _find_url()
    if not url:
        return {"predictions": []}
    # Private stores require auth on the blob URL too.
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
    # PUT to upload endpoint. Some API versions read access from query string.
    url = f"https://{BLOB_API_HOST}/{urllib.parse.quote(BLOB_PATHNAME)}?access=private"
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "authorization": f"Bearer {_token()}",
            "x-api-version": BLOB_API_VERSION,
            "x-content-type": "application/json",
            # Try multiple header names — Vercel will recognize one of these,
            # and the others are harmless. The blob API has churned on this.
            "x-access-mode": "private",
            "x-blob-access": "private",
            "x-add-random-suffix": "0",
            "x-allow-overwrite": "1",
            "x-cache-control-max-age": "0",
            "content-type": "application/json",
            "content-length": str(len(body)),
        },
    )
    with _do_request(req, "blob put") as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------- Public API (same shape as the Postgres version) ----------

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

    # Don't overwrite a finalized (evaluated) prediction
    if existing and existing.get("actual") is not None:
        return

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

    if existing:
        by_date[ride_date] = entry
    else:
        by_date[ride_date] = entry

    log["predictions"] = sorted(by_date.values(), key=lambda p: p["ride_date"])
    _write_all(log)


def pending_actuals():
    """Return ride_dates with a prediction but no actuals yet (and in the past)."""
    if not is_enabled():
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    log = _read_all()
    return [
        p["ride_date"] for p in log.get("predictions", [])
        if p.get("actual") is None and p["ride_date"] < today
    ]


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
