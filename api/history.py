import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler
from fetch_openmeteo import fetch_actuals_for_date
import db


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if db.is_enabled():
                db.init_schema()
                # Opportunistic backfill on every history view too
                for past_date in db.pending_actuals():
                    actuals = fetch_actuals_for_date(past_date)
                    if actuals:
                        db.save_actuals(
                            ride_date=past_date,
                            actual_precip_mm=actuals["precip_mm"],
                            actual_max_wind=actuals["max_wind"],
                            actual_rained=actuals["rained"],
                        )
            data = db.fetch_history(limit=60)
        except Exception as e:
            data = {"enabled": False, "error": str(e), "predictions": [], "stats": None}

        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
