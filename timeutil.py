"""Bogota timezone helpers.

The app's logical "today" and "tomorrow" are anchored to Medellín/Bogota
local time (UTC-5, no DST), not the server's UTC clock. Without this,
predictions made via Vercel Cron at 20:00 Bogota (= 01:00 UTC the
following day) would log a ride_date one day too far in the future.
"""

from datetime import datetime, timedelta, timezone

BOGOTA_TZ = timezone(timedelta(hours=-5))


def now_bogota():
    return datetime.now(BOGOTA_TZ)


def today_str():
    return now_bogota().strftime("%Y-%m-%d")


def tomorrow_str():
    return (now_bogota() + timedelta(days=1)).strftime("%Y-%m-%d")


def today_date():
    return now_bogota().date()
