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


# ---------- Time-aware ride targeting ----------
#
# The app is read at two times: the night before (~20:00) and pre-dawn (~4am).
# Before the morning cutoff, the relevant ride is TODAY's 05:00-07:30 window
# (imminent); at/after the cutoff that ride is over, so we point at tomorrow.
# The cutoff is 08:00 — just past RIDE_LATEST (07:00 slot covers 07:00-07:59,
# window ends 07:30), giving a small buffer.
MORNING_CUTOFF_HOUR = 8


def target_date_str():
    """The date whose 05:00-07:30 window the prediction is for: today before
    08:00 Bogota, tomorrow at/after."""
    if now_bogota().hour < MORNING_CUTOFF_HOUR:
        return today_str()
    return tomorrow_str()


def framing():
    """'this_morning' if the target ride is today, else 'tomorrow_morning'."""
    return "this_morning" if now_bogota().hour < MORNING_CUTOFF_HOUR else "tomorrow_morning"


def evening_before(date_str):
    """Return the calendar date before `date_str` (YYYY-MM-DD) — the evening
    that precedes a given ride morning, used for the overnight-precip window."""
    d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    return d.strftime("%Y-%m-%d")
