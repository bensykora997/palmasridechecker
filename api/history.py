import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler
import db
import calibrate
import backfill


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if db.is_enabled():
                db.init_schema()
                backfill.backfill_pending()
            data = db.fetch_history(limit=60)
            if db.is_enabled():
                try:
                    # Read-only. Training is owned by the cron (api/cron.py step
                    # 3, twice daily). Retraining here would run the calibration
                    # CV inside a user request with no dedup — the Vercel Fluid
                    # CPU-spike path (a MODEL_VERSION bump or failed write made
                    # every /api/history request retrain the whole model).
                    cal = db.read_calibration()
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
