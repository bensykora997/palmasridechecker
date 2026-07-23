import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from timeutil import now_bogota
import db
import calibrate
import backfill

CALIBRATION_STALE_SECONDS = 24 * 3600


def _maybe_retrain_calibration():
    """Retrain the shadow model if the stored calibration is missing or older
    than 24h. Mirrors the opportunistic-backfill pattern so the panel stays
    fresh even between nightly cron runs. Returns the (possibly new) state."""
    cal = db.read_calibration()
    stale = True
    ts = (cal or {}).get("trained_at")
    if ts:
        try:
            # trained_at is an ISO string with tz offset (Bogota). Compare in UTC.
            parsed = datetime.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            age = (now_bogota() - parsed).total_seconds()
            stale = age > CALIBRATION_STALE_SECONDS
        except Exception:
            stale = True
    # A stored state from older code (schema/behavior change) is always stale,
    # so a version bump takes effect on the next read rather than waiting for
    # the 24h timer or the nightly cron.
    if (cal or {}).get("model_version") != calibrate.MODEL_VERSION:
        stale = True
    if stale:
        entries = db._read_all().get("predictions", [])
        cal = calibrate.train_calibration(
            entries, trained_at=now_bogota().isoformat(timespec="seconds"))
        db.write_calibration(cal)
    return cal


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if db.is_enabled():
                db.init_schema()
                backfill.backfill_pending()
            data = db.fetch_history(limit=60)
            if db.is_enabled():
                try:
                    cal = _maybe_retrain_calibration()
                    data["calibration"] = cal
                    # Per-day champion vs challenger verdicts for the history
                    # head-to-head (retrospective; see calibrate.evaluate_models).
                    for p in data.get("predictions", []):
                        try:
                            p["model_eval"] = calibrate.evaluate_models(cal, p)
                        except Exception:
                            p["model_eval"] = None
                except Exception as e:
                    data["calibration"] = {"error": str(e)}
        except Exception as e:
            data = {"enabled": False, "error": str(e), "predictions": [], "stats": None}

        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
