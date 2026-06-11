"""Manual ground-truth override endpoint.

POST /api/override
  Body: {"ride_date": "YYYY-MM-DD", "rained": true|false|null, "note"?: "..."}
    - rained: true/false sets the override
    - rained: null clears the override (falls back to sensor data)
  Returns: the updated prediction entry

Auth: Bearer ${CRON_SECRET} — reuses the same write-token as the cron
endpoint. The rider enters it once in the UI (saved to localStorage) and
the History view sends it with each override request.

Why auth? Because this endpoint mutates predictions.json. The other
public endpoints (/api/check, /api/history) only write data computed
deterministically from external sources, so an attacker can at worst
re-write the same value. An override accepts an arbitrary boolean from
the request body, so it must be gated.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler

import db


class handler(BaseHTTPRequestHandler):
    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return None

    def do_POST(self):
        secret = os.environ.get("CRON_SECRET")
        if not secret:
            return self._respond(500, {"error": "CRON_SECRET not configured"})

        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            return self._respond(401, {"error": "unauthorized"})

        body = self._read_body()
        if body is None:
            return self._respond(400, {"error": "invalid JSON body"})

        ride_date = body.get("ride_date")
        if not ride_date or not isinstance(ride_date, str):
            return self._respond(400, {"error": "ride_date (YYYY-MM-DD string) required"})

        rained = body.get("rained")
        note = body.get("note") or None

        try:
            if rained is None:
                entry = db.clear_override(ride_date)
            elif isinstance(rained, bool):
                entry = db.set_override(ride_date, rained, note=note)
            else:
                return self._respond(400, {"error": "rained must be true, false, or null"})
        except Exception as e:
            return self._respond(500, {"error": str(e)})

        if entry is None:
            return self._respond(404, {"error": f"no prediction found for {ride_date}"})

        return self._respond(200, {"ok": True, "entry": entry})

    def do_OPTIONS(self):
        # CORS preflight — keep the API friendly to the browser UI.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _respond(self, status, body):
        payload = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)
