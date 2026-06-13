"""Shared dual-source actuals backfill.

Evaluates pending predictions against observed weather, pulling from two
independent sources and recording an audit trail. Used by the nightly cron
and opportunistically by /api/check and /api/history, so every entry point
writes identical fields (previously this logic was copy-pasted in three
places and drifted).

Rain attribution rules (see code review #1 — "stale p24h corrupts labels"):
  - Open-Meteo hourly observations are accurate for the 05:00-07:30 window for
    any date within its lookback, so they are the source for *every* date.
  - SIATA's `p24h` is a *live rolling 24h total*. It only overlaps a ride
    window when read in the morning of that same day. So it is used ONLY for
    today, and ONLY when the backfill runs in the morning. For any older date
    (or a same-day afternoon/evening read) the live total has no meaningful
    overlap with the 05:00-07:30 window and would fabricate the label.
"""

import db
from fetch_openmeteo import fetch_actuals_for_date
from fetch_siata import fetch_pluviometrica
from timeutil import now_bogota, today_str

# Hour (Bogota) before which SIATA's rolling p24h still mostly reflects the
# overnight + ride-window rainfall rather than the day's later weather. After
# this it's dominated by the afternoon/evening and is no longer a window proxy.
SIATA_MORNING_HOUR_LIMIT = 12


def siata_p24h_stats(pluvio):
    """Average / max p24h across corridor stations (Nones excluded)."""
    vals = [s.get("p24h") for s in pluvio.get("stations", []) if s.get("p24h") is not None]
    if not vals:
        return None, None
    return round(sum(vals) / len(vals), 2), round(max(vals), 2)


def station_snapshots(pluvio):
    """Per-station rain readings for the audit trail."""
    return [
        {
            "name": s.get("name"),
            "code": s.get("code"),
            "distance_km": s.get("distance_km"),
            "valor": s.get("value"),
            "p10m": s.get("p10m"),
            "p1h": s.get("p1h"),
            "p24h": s.get("p24h"),
        }
        for s in pluvio.get("stations", [])
    ]


def backfill_pending(pluvio=None):
    """Fill observed weather for every pending date we can evaluate.

    `pluvio` may be a SIATA fetch the caller already has on hand (seconds old);
    if omitted, one is fetched only when there is actually something to backfill.

    Returns a list of per-date outcome dicts. Dates we couldn't evaluate (no
    usable source) are returned with `{"skipped": True}` and left pending.
    """
    pending = db.pending_actuals()
    if not pending:
        return []

    if pluvio is None:
        pluvio = fetch_pluviometrica()

    siata_avg, siata_max = siata_p24h_stats(pluvio)
    snaps = station_snapshots(pluvio)

    today = today_str()
    siata_is_window_proxy = now_bogota().hour < SIATA_MORNING_HOUR_LIMIT

    outcomes = []
    for past_date in pending:
        om = fetch_actuals_for_date(past_date)
        om_precip = om["precip_mm"] if om else None
        om_max_wind = om["max_wind"] if om else None

        # SIATA's live p24h only describes *today's* window, and only in the
        # morning. Never attribute it to older dates or a stale-of-day read.
        use_siata = past_date == today and siata_is_window_proxy
        siata_candidate = siata_avg if use_siata else None

        candidates = [v for v in (om_precip, siata_candidate) if v is not None]
        if not candidates:
            # Nothing usable (e.g. older than Open-Meteo's lookback and SIATA
            # doesn't apply). Leave it pending — don't fabricate a verdict.
            outcomes.append({"ride_date": past_date, "skipped": True})
            continue

        precip_final = round(max(candidates), 2)

        if om_precip is None:
            source, disagreement = "siata_p24h", None
        elif siata_candidate is None:
            source, disagreement = "open_meteo", None
        else:
            disagreement = round(abs(om_precip - siata_candidate), 2)
            if disagreement < 0.5:
                source = "agreed"
            elif siata_candidate > om_precip:
                source = "siata_p24h"
            else:
                source = "open_meteo"

        db.save_actuals(
            ride_date=past_date,
            actual_precip_mm=precip_final,
            actual_max_wind=om_max_wind if om_max_wind is not None else 0,
            actual_rained=precip_final > 0.1,
            open_meteo_precip_mm=om_precip,
            # Only record the SIATA reading on the entry when it actually
            # informed this date — otherwise the audit trail is misleading.
            siata_p24h_avg_mm=siata_avg if use_siata else None,
            siata_p24h_max_mm=siata_max if use_siata else None,
            source=source,
            disagreement_mm=disagreement,
            station_snapshots=snaps,
        )
        outcomes.append({
            "ride_date": past_date,
            "precip_mm": precip_final,
            "rained": precip_final > 0.1,
            "source": source,
            "open_meteo_precip_mm": om_precip,
            "siata_p24h_avg_mm": siata_avg if use_siata else None,
        })
    return outcomes
