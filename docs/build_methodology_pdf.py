"""Generate methodology.pdf — a comprehensive technical overview of the
Palmas Ride Engine app.

Run with: python3 docs/build_methodology_pdf.py
Output:    docs/methodology.pdf
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Preformatted, ListFlowable, ListItem, HRFlowable,
)
from reportlab.platypus.flowables import Flowable

# ---------- Colors (match the app's dark-theme accent palette in spirit) ----------

ACCENT = colors.HexColor("#f0a030")   # orange
INK    = colors.HexColor("#1a1a2e")   # near-black
MUTED  = colors.HexColor("#6b6b85")
RULE   = colors.HexColor("#d0d0d8")
CHIP   = colors.HexColor("#f5e9d6")   # pale orange wash
GREEN  = colors.HexColor("#2ecc71")
RED    = colors.HexColor("#e74c3c")
BLUE   = colors.HexColor("#4aa8ff")

# ---------- Styles ----------

styles = getSampleStyleSheet()

# Override "Normal" so all body text picks up our defaults cleanly
NORMAL = ParagraphStyle(
    "PalmasBody",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10.5,
    leading=15,
    textColor=INK,
    alignment=TA_JUSTIFY,
    spaceAfter=8,
)
SMALL = ParagraphStyle("Small", parent=NORMAL, fontSize=9, leading=12, textColor=MUTED, alignment=TA_LEFT, spaceAfter=4)
CAPTION = ParagraphStyle("Caption", parent=NORMAL, fontSize=8.5, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica-Oblique")

TITLE = ParagraphStyle(
    "PalmasTitle", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=30, leading=36,
    textColor=INK, alignment=TA_CENTER, spaceAfter=8,
)
SUBTITLE = ParagraphStyle(
    "PalmasSub", parent=NORMAL,
    fontSize=13, leading=18, textColor=MUTED, alignment=TA_CENTER, spaceAfter=24,
)
TAGLINE = ParagraphStyle(
    "Tag", parent=NORMAL,
    fontSize=11, leading=16, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=4,
    fontName="Helvetica-Bold",
)

H1 = ParagraphStyle(
    "H1", parent=NORMAL, fontName="Helvetica-Bold",
    fontSize=20, leading=26, textColor=INK,
    alignment=TA_LEFT, spaceBefore=18, spaceAfter=10,
)
H2 = ParagraphStyle(
    "H2", parent=NORMAL, fontName="Helvetica-Bold",
    fontSize=14, leading=20, textColor=INK,
    alignment=TA_LEFT, spaceBefore=14, spaceAfter=6,
)
H3 = ParagraphStyle(
    "H3", parent=NORMAL, fontName="Helvetica-Bold",
    fontSize=11, leading=15, textColor=ACCENT,
    alignment=TA_LEFT, spaceBefore=8, spaceAfter=2,
)

CODE = ParagraphStyle(
    "Code", parent=NORMAL, fontName="Courier",
    fontSize=9, leading=12, textColor=INK,
    backColor=colors.HexColor("#f3f3f8"),
    borderColor=RULE, borderWidth=0.5, borderPadding=6,
    spaceAfter=8, alignment=TA_LEFT,
)

CALLOUT = ParagraphStyle(
    "Callout", parent=NORMAL, fontSize=10, leading=14, textColor=INK,
    backColor=CHIP, borderColor=ACCENT, borderWidth=0,
    leftIndent=10, rightIndent=10, borderPadding=10,
    spaceAfter=10, alignment=TA_LEFT,
)


# ---------- Helpers ----------

def hr():
    return HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=4, spaceAfter=10)

def section(name):
    return [Spacer(1, 6), Paragraph(name, H1), HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceBefore=0, spaceAfter=8)]

def sub(name):
    return Paragraph(name, H2)

def kicker(name):
    return Paragraph(name, H3)

def para(text):
    return Paragraph(text, NORMAL)

def small(text):
    return Paragraph(text, SMALL)

def callout(text):
    return Paragraph(text, CALLOUT)

def code(text):
    # Use Preformatted for multi-line code so newlines render
    return Preformatted(text, CODE)

def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, NORMAL), leftIndent=12, bulletColor=ACCENT) for t in items],
        bulletType="bullet", start=u"•",
        leftIndent=14, bulletFontSize=10,
    )

def numbered(items):
    return ListFlowable(
        [ListItem(Paragraph(t, NORMAL), leftIndent=12) for t in items],
        bulletType="1", start="1",
        leftIndent=14, bulletFontSize=10, bulletFormat="%s.",
    )


# ---------- Decorative "score chip" used in headings ----------

class Chip(Flowable):
    def __init__(self, text, fill=ACCENT, w=80, h=18):
        super().__init__()
        self.text = text
        self.fill = fill
        self.w = w
        self.h = h
    def wrap(self, *args, **kwargs):
        return (self.w, self.h)
    def draw(self):
        c = self.canv
        c.setFillColor(self.fill)
        c.setStrokeColor(self.fill)
        c.roundRect(0, 0, self.w, self.h, 4, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(self.w / 2, 5, self.text)


# ---------- Build the document ----------

def build():
    out_path = Path(__file__).parent / "methodology.pdf"
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="Palmas Ride Engine — Methodology",
        author="Palmas Ride Engine",
    )

    story = []

    # ============================================================
    # COVER
    # ============================================================
    story.append(Spacer(1, 1.4 * inch))
    # Big stylized monogram instead of an emoji — built-in fonts don't include emoji glyphs.
    story.append(Paragraph(
        "PRE",
        ParagraphStyle("Monogram", parent=NORMAL, fontName="Helvetica-Bold",
                       fontSize=56, leading=64, alignment=TA_CENTER,
                       textColor=ACCENT, spaceAfter=14)
    ))
    story.append(Paragraph("Palmas Ride Engine", TITLE))
    story.append(Paragraph("How it works · How it decides · How it learns", SUBTITLE))
    story.append(Paragraph("Methodology Document", TAGLINE))
    story.append(Spacer(1, 0.4 * inch))
    story.append(HRFlowable(width="40%", thickness=1, color=ACCENT, hAlign="CENTER", spaceBefore=0, spaceAfter=20))
    story.append(Paragraph(
        "A practical guide to the data sources, scoring formula, rain detection,"
        " and accuracy-tracking that decide whether to ride Alto de Palmas tomorrow morning.",
        ParagraphStyle("Lead", parent=NORMAL, fontSize=11.5, leading=17, alignment=TA_CENTER, textColor=MUTED, spaceAfter=20)
    ))
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle("Date", parent=NORMAL, fontSize=9, textColor=MUTED, alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    # ============================================================
    # 1. Overview
    # ============================================================
    story += section("1. Overview")

    story.append(para(
        "<b>Palmas Ride Engine</b> is a single-purpose web app that answers one"
        " question every morning: <i>should I bike up Alto de Palmas tomorrow at"
        " 5:00 AM?</i> It blends multiple meteorological sources, weights them"
        " through a transparent scoring formula tailored to the Las Palmas climb,"
        " and produces a <b>0–100 score</b>, a <b>YES/NO decision</b>, a"
        " <b>confidence level</b>, and a list of human-readable reasons."
    ))
    story.append(para(
        "Beyond the live prediction, the app keeps an evolving accuracy record:"
        " every prediction is logged the night before, and the next morning the"
        " observed weather is cross-validated from two independent sources and"
        " written back so that, over time, the model's calibration is visible to"
        " the rider."
    ))

    story.append(sub("Why this exists"))
    story.append(para(
        "Open-Meteo and the SIATA weather network each have blind spots when"
        " applied to a microclimate-prone road that climbs from the Aburrá Valley"
        " (~1,500 m) to Alto de Palmas (~2,500 m). Generic forecasts often"
        " under-predict rain at altitude; SIATA stations down in the valley don't"
        " always reflect what's actually falling on the upper sections of the"
        " climb. The engine combines them deliberately so neither source alone"
        " can dictate the call."
    ))

    story.append(sub("What it is not"))
    story.append(para(
        "This is not a general weather forecast. It is narrowly tuned to the"
        " 05:00–07:30 morning ride window at Alto de Palmas, Medellín. The"
        " corridor filter, scoring weights, and time conventions are all built"
        " around that specific use case."
    ))

    story.append(PageBreak())

    # ============================================================
    # 2. Architecture
    # ============================================================
    story += section("2. System Architecture")

    story.append(para(
        "The app is split into four cooperating components running on Vercel."
    ))

    arch_data = [
        ["Layer", "Implementation", "Role"],
        ["Frontend", "Static HTML / vanilla JS / Leaflet", "Renders the main card, the map, the radar, and the history view."],
        ["Backend", "Python on Vercel Functions (@vercel/python)", "Fetches data from SIATA + Open-Meteo, computes the score, exposes /api/check, /api/history, /api/cron."],
        ["Storage", "Vercel Blob (private store)", "predictions.json — append-mostly log of every prediction + its observed actual."],
        ["Scheduler", "Vercel Cron Jobs (twice daily)", "Locks in tomorrow's prediction at 20:00 Bogota and backfills yesterday's actual at 07:00 Bogota."],
    ]
    t = Table(arch_data, colWidths=[1.1*inch, 2.0*inch, 3.6*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(sub("Request flow (live view)"))
    story.append(code(
        "Browser -> GET /api/check\n"
        "           |-- fetch SIATA Pluviometrica.json    (corridor stations)\n"
        "           |-- enrich: per-station {code}.json   (parallel x 15)\n"
        "           |-- fetch SIATA radar animation JSON\n"
        "           |-- fetch SIATA WRF forecast (Centro + Envigado)\n"
        "           |-- fetch Open-Meteo forecast         (hourly precip + wind)\n"
        "           |-- fetch Open-Meteo air quality      (PM2.5, PM10, AQI)\n"
        "           |-- compute score, decision, reasons\n"
        "           '-- best-effort save to predictions.json (Vercel Blob)\n"
        "                       |\n"
        "                       v\n"
        "Browser renders the main card + (optionally) the More Details panel."
    ))

    story.append(sub("Request flow (cron)"))
    story.append(para(
        "Vercel Cron sends authenticated GET requests to <font face='Courier'>/api/cron</font>"
        " at fixed times. The endpoint is identical to a refresh trigger but is"
        " bearer-token gated. It runs the same data pipeline and writes the"
        " prediction or backfill regardless of whether anyone visited the site."
    ))

    story.append(PageBreak())

    # ============================================================
    # 3. Data sources
    # ============================================================
    story += section("3. Data Sources")

    story.append(para(
        "Five real-time inputs feed the engine. Each is queried fresh on every"
        " call (with a short in-memory cache so consecutive visits within five"
        " minutes share data)."
    ))

    sources = [
        ["Source", "Endpoint", "What we use"],
        ["SIATA pluvio (summary)",
         "Pluviometrica.json",
         "Per-station current valor (rainfall snapshot)."],
        ["SIATA pluvio (detail)",
         "{code}.json",
         "p10m, p1h, p24h rainfall totals + sensor freshness."],
        ["SIATA radar",
         "animacion_radar.json",
         "Last ~12 frames of precipitation echoes + bounds, animated in the More Details view."],
        ["SIATA WRF",
         "wrfmedCentro.json + wrfenvigado.json",
         "Local 24-hour rainfall forecast by quarter-day (LOW / MEDIA / ALTA / MUY ALTA). Informational only — not in the score."],
        ["Open-Meteo forecast",
         "forecast?hourly=...",
         "Hourly precip, precip probability, temperature, humidity, wind speed for the next 48 h."],
        ["Open-Meteo air quality",
         "air-quality?current=...",
         "PM2.5, PM10, US AQI, European AQI. Informational only."],
    ]
    t = Table(sources, colWidths=[1.5*inch, 2.0*inch, 3.2*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (1,1), (1,-1), "Courier"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
    ]))
    story.append(t)

    story.append(Spacer(1, 12))
    story.append(callout(
        "<b>SIATA</b> is the Sistema de Alerta Temprana de Medellín y el Valle de"
        " Aburrá — the regional weather-and-hazards network. Their public JSON"
        " endpoints are unauthenticated but use self-signed SSL, so we relax the"
        " certificate check in the fetcher."
    ))

    story.append(PageBreak())

    # ============================================================
    # 4. Corridor filter
    # ============================================================
    story += section("4. The Route Corridor — which stations count")

    story.append(para(
        "SIATA publishes hundreds of stations across the Aburrá Valley. Most are"
        " irrelevant to whether the road up Las Palmas is wet. The first job of"
        " the engine is therefore to <b>narrow the SIATA feed to stations whose"
        " readings actually represent Palmas weather</b>."
    ))

    story.append(sub("How we define \"on the climb\""))
    story.append(para(
        "We pulled the live geometry of <font face='Courier'>Avenida de Las"
        " Palmas</font> (OSM ref=56) and <font face='Courier'>Variante Las"
        " Palmas</font> from OpenStreetMap via the Overpass API. The result is"
        " 186 ordered segments containing 1,883 waypoints, covering the road from"
        " its El Poblado start to past Alto de Palmas."
    ))
    story.append(para(
        "A SIATA station qualifies for the corridor if the minimum great-circle"
        " distance from its (lat, lon) to <i>any</i> route waypoint is <b>at most"
        " 1.5 km</b>. With waypoints this dense, that radius cleanly captures"
        " stations directly on or immediately adjacent to the road and excludes"
        " stations on the other side of the ridge."
    ))

    story.append(sub("In practice"))
    story.append(para(
        "At publication time, 15 stations pass the corridor filter. The top three"
        " by distance from the road are <i>Colegio Latino</i> (0.04 km, literally"
        " on Av. Las Palmas), <i>ISAGEN</i> (0.08 km), and <i>Q. La Sanin</i>"
        " (0.20 km). The farthest in-corridor station sits ~1.4 km off-road."
    ))
    story.append(callout(
        "<b>Why 1.5 km, not 2.5 km?</b> An earlier iteration used a square"
        " bounding box around the climb. That included off-route stations like"
        " Pan de Azucar (4 km north) and Las Flores in Guarne (east, past the"
        " summit) whose rain is essentially uncorrelated with Palmas. The"
        " distance-from-route filter with dense OSM waypoints lets us tighten"
        " the radius substantially without losing any genuinely-on-Palmas station."
    ))

    story.append(PageBreak())

    # ============================================================
    # 5. The Riding Window & Timezone
    # ============================================================
    story += section("5. The Riding Window & Timezone")

    story.append(para(
        "The score is computed for a fixed window: <b>05:00–07:30 Bogota local"
        " time</b> on the next day. All scoring inputs are aggregated over"
        " that window only (with one exception: \"overnight precipitation\","
        " which uses the hours leading <i>up to</i> 05:00)."
    ))

    story.append(sub("Why Bogota time matters"))
    story.append(para(
        "Vercel functions run in UTC. Bogota is UTC−5 with no daylight saving."
        " A naive <font face='Courier'>datetime.now()</font> on the server"
        " disagrees with the rider's wall clock by 5 hours, which matters at"
        " day boundaries: a cron firing at 20:00 Bogota = 01:00 UTC the next"
        " day would compute \"tomorrow\" as the day after the intended one."
        " All date arithmetic therefore goes through a small Bogota timezone"
        " shim (<font face='Courier'>timeutil.py</font>) that anchors"
        " <font face='Courier'>today_str()</font> and"
        " <font face='Courier'>tomorrow_str()</font> to UTC−5."
    ))

    story.append(PageBreak())

    # ============================================================
    # 6. Scoring formula
    # ============================================================
    story += section("6. Scoring Formula")

    story.append(para(
        "Every prediction starts at <b>100</b>. Each input either applies a"
        " penalty (subtracts points) or a bonus (adds points). The final score"
        " is clamped to the range 0–100."
    ))

    story.append(sub("Penalties"))
    pen_data = [
        ["Trigger", "Threshold", "Penalty"],
        ["Average rain probability (05:00–07:30 from Open-Meteo)", "> 60 %", "−40"],
        ["Any corridor SIATA station reports active rain", "valor ≥ 0.1 mm OR p10m ≥ 0.1 mm OR p1h ≥ 0.5 mm", "−50"],
        ["Max wind in the window", "> 20 km/h", "−15"],
        ["Average humidity in the window", "> 90 %", "−10"],
        ["Roads classified \"wet\" (overnight precip > 5 mm OR active rain)", "—", "−15"],
        ["Roads classified \"damp\" (overnight precip 1–5 mm)", "—", "−7 (half)"],
    ]
    t = Table(pen_data, colWidths=[3.6*inch, 2.4*inch, 0.7*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("ALIGN", (-1,0), (-1,-1), "CENTER"),
        ("TEXTCOLOR", (-1,1), (-1,-1), RED),
        ("FONTNAME", (-1,1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(sub("Bonuses"))
    bon_data = [
        ["Trigger", "Threshold", "Bonus"],
        ["Fully dry forecast window (every hour: precip < 0.1 mm AND prob < 50 %)", "all hours", "+25"],
        ["No corridor station reporting rain (and at least one online)", "—", "+10"],
    ]
    t = Table(bon_data, colWidths=[3.6*inch, 2.4*inch, 0.7*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("ALIGN", (-1,0), (-1,-1), "CENTER"),
        ("TEXTCOLOR", (-1,1), (-1,-1), GREEN),
        ("FONTNAME", (-1,1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(sub("Decision & confidence"))
    story.append(code(
        "final_score = clamp(0, 100, sum of penalties + bonuses)\n"
        "\n"
        "decision    = YES if final_score >= 50 else NO\n"
        "confidence  = high   if score >= 70\n"
        "              medium if 40 <= score < 70\n"
        "              low    if score < 40"
    ))

    story.append(sub("What is intentionally NOT in the score"))
    story.append(bullets([
        "<b>WRF forecast</b> — fetched and shown in the reasons list, but contributes no points. It's information-only.",
        "<b>Radar imagery</b> — fetched, displayed in More Details, but never weighted. It's a visual aid.",
        "<b>Air quality (PM2.5, PM10, AQI)</b> — fetched and shown with a non-zero color badge, but explicitly disclaimed as \"not factored into the score.\"",
    ]))

    story.append(callout(
        "The score is a <i>heuristic</i>, not a calibrated probability. A score"
        " of 100 does not mean a 100% chance of dry roads. It means: no penalty"
        " triggered, the dry-window bonus applied, no station reported rain."
        " The empirical mapping from score to actual dry-ride probability is"
        " what the accuracy log is gradually filling in."
    ))

    story.append(PageBreak())

    # ============================================================
    # 7. Rain detection — four signals
    # ============================================================
    story += section("7. Rain Detection — Four Signals")

    story.append(para(
        "A naive \"is it raining now\" check on SIATA's pluviometric data was"
        " responsible for two real-world misses: a sub-millimeter zombie reading"
        " from one station permanently anchored the score at 50, and a real"
        " rainy Saturday morning slipped past entirely because the summary"
        " <font face='Courier'>valor</font> field reported zero between brief"
        " showers."
    ))
    story.append(para(
        "The fix was to stop treating <font face='Courier'>valor</font> as the"
        " only signal. Every corridor station now exposes <b>four</b>"
        " independent rainfall signals; a station is flagged \"raining\" if"
        " <b>any</b> of them crosses its threshold:"
    ))

    sig_data = [
        ["Signal", "Window", "Source", "Raining threshold"],
        ["valor", "current snapshot", "Pluviometrica.json", "≥ 0.1 mm"],
        ["p10m",  "last 10 min",     "{code}.json",         "≥ 0.1 mm"],
        ["p1h",   "last 1 hour",     "{code}.json",         "≥ 0.5 mm"],
        ["p24h",  "last 24 hours",   "{code}.json",         "informational only (used for road-wetness)"],
    ]
    t = Table(sig_data, colWidths=[0.9*inch, 1.4*inch, 1.7*inch, 2.7*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (0,-1), "Courier"),
        ("FONTNAME", (2,1), (2,-1), "Courier"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(sub("Sub-mm noise threshold"))
    story.append(para(
        "Values below 0.1 mm are treated as no rain. SIATA's pluvio stations"
        " regularly report tiny non-zero residuals (e.g. 0.02 mm) on dead"
        " sensors that haven't been re-zeroed. Below this threshold we ignore"
        " the reading rather than let one zombie sensor anchor the entire score."
    ))

    story.append(sub("Sensor-liveness cross-check"))
    story.append(para(
        "Even with the 0.1 mm threshold, SIATA could in principle serve a stale"
        " <font face='Courier'>0.5 mm</font> residual from a sensor whose"
        " rainfall hardware is actually offline. The cross-check fetches the"
        " station's per-station detail file: if all three of"
        " <font face='Courier'>p10m</font>, <font face='Courier'>p1h</font>, and"
        " <font face='Courier'>p24h</font> are <font face='Courier'>-999</font>,"
        " the rain sensor is treated as offline and the value is dropped."
    ))
    story.append(para(
        "Detail files are fetched in parallel for all 15 corridor stations using"
        " a <font face='Courier'>ThreadPoolExecutor</font> with a 3-second"
        " per-station timeout. Total enrichment latency is typically ~0.7 s."
        " Each file is cached for 5 minutes."
    ))

    story.append(PageBreak())

    # ============================================================
    # 8. Road conditions
    # ============================================================
    story += section("8. Road Condition Inference")

    story.append(para(
        "Road wetness is computed separately from \"is it raining\" because the"
        " surface state at 5:00 AM depends on what fell overnight, not on what's"
        " falling at the moment of the prediction (8:00 PM the night before)."
        " Two independent sources are combined:"
    ))

    rc_data = [
        ["Source", "Window", "Used as"],
        ["Open-Meteo overnight precip", "20:00 today → 04:59 tomorrow (Bogota)", "Sum of hourly precip"],
        ["SIATA p24h average", "rolling last 24 h across corridor", "Mean of corridor stations' p24h"],
    ]
    t = Table(rc_data, colWidths=[2.0*inch, 2.5*inch, 2.2*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(para(
        "<b>The worst case wins.</b> The two sources are combined by taking"
        " <font face='Courier'>max(open_meteo_overnight, siata_p24h_avg)</font>"
        " and bucketing the result:"
    ))
    story.append(code(
        "max(om_overnight, siata_p24h_avg)  →  road condition\n"
        "  > 5 mm   →  wet\n"
        "  1–5 mm   →  damp\n"
        "  0.2–1 mm →  mostly_dry\n"
        "  ≤ 0.2 mm →  dry"
    ))
    story.append(para(
        "If SIATA captures rain that Open-Meteo's interpolated grid missed —"
        " the classic Palmas microclimate situation — SIATA wins and the road"
        " is flagged damp or wet accordingly. The reverse also works: if the"
        " Open-Meteo grid sees rain that SIATA stations down in the valley"
        " missed, Open-Meteo wins."
    ))

    story.append(PageBreak())

    # ============================================================
    # 9. Backfill methodology
    # ============================================================
    story += section("9. Recording the Actual — Dual-Source Backfill")

    story.append(para(
        "Each prediction is logged at 20:00 Bogota the night before. The morning"
        " after the ride window closes, the engine records what <i>actually</i>"
        " happened, using the same two sources blended the same way:"
    ))

    story.append(code(
        "open_meteo_precip = sum(forecast.past_days['precipitation']\n"
        "                        for hours 05:00–07:00 of the ride day)\n"
        "siata_p24h_avg    = mean(corridor stations' p24h at 07:00 cron time)\n"
        "                    # p24h covers ~yesterday afternoon → 07:00 = the\n"
        "                    # ride window plus overnight\n"
        "\n"
        "actual.precip_mm  = max(open_meteo_precip, siata_p24h_avg)\n"
        "actual.rained     = actual.precip_mm > 0.1"
    ))

    story.append(sub("Source label & disagreement"))
    story.append(para(
        "Every backfilled actual carries an explicit"
        " <font face='Courier'>source</font> field so a reader can audit which"
        " input dominated the call:"
    ))
    story.append(bullets([
        "<font face='Courier'><b>agreed</b></font> &mdash; both sources within 0.5 mm of each other.",
        "<font face='Courier'><b>open_meteo</b></font> &mdash; Open-Meteo recorded more rain than SIATA.",
        "<font face='Courier'><b>siata_p24h</b></font> &mdash; SIATA recorded more rain than Open-Meteo's grid. <b>These are the interesting ones</b>: cases where the microclimate showed up at the on-road stations but missed the broader forecast model.",
    ]))

    story.append(sub("Why \"max\" instead of average?"))
    story.append(para(
        "When the two sources disagree by a meaningful amount, one of them is"
        " almost always closer to ground truth. The expected error of averaging"
        " is symmetric (under-reporting and over-reporting are equally bad),"
        " but for a cyclist's decision, <i>under-reporting</i> is the worse"
        " failure mode (it tells you to ride when you shouldn't). Taking the"
        " max biases toward over-reporting, which is the safer asymmetry to"
        " carry."
    ))

    story.append(PageBreak())

    # ============================================================
    # 10. Audit trail
    # ============================================================
    story += section("10. The Audit Trail")

    story.append(para(
        "Every prediction in <font face='Courier'>predictions.json</font> stores"
        " a complete snapshot of the sensor state at the time of the prediction"
        " <i>and</i> at the time of the backfill. This lets a reader inspect"
        " any past entry and see exactly what each station was reporting, and"
        " what each external source said about the morning in question."
    ))

    story.append(sub("Schema (one entry)"))
    story.append(code(
        "{\n"
        '  "ride_date": "2026-06-11",\n'
        '  "predicted_at": "2026-06-10T01:00:00Z",\n'
        '  "score": 92, "decision": "YES", "confidence": "high",\n'
        '  "reasons": ["Moderate/low rain probability (8%)", "Low wind ..."],\n'
        '  "forecast": {\n'
        '    "avg_precip_prob": 8.0, "max_wind": 4.2,\n'
        '    "avg_humidity": 96.0, "overnight_precip_mm": 0.3,\n'
        '    "station_snapshots": [   // captured at predict time\n'
        '      {"name": "Colegio Latino", "code": 251,\n'
        '       "distance_km": 0.04,\n'
        '       "valor": 0.0, "p10m": 0.0, "p1h": 0.0, "p24h": 0.6},\n'
        '      ...   // one per corridor station\n'
        '    ]\n'
        '  },\n'
        '  "actual": {            // filled in the next morning by cron\n'
        '    "precip_mm": 5.1, "rained": true, "max_wind": 6.3,\n'
        '    "open_meteo_precip_mm": 0.0,\n'
        '    "siata_p24h_avg_mm": 5.1, "siata_p24h_max_mm": 7.3,\n'
        '    "disagreement_mm": 5.1,\n'
        '    "source": "siata_p24h",\n'
        '    "station_snapshots": [   // captured at backfill time\n'
        '      {"name": "Colegio Latino", "code": 251,\n'
        '       "valor": 0.0, "p10m": 0.0, "p1h": 0.0, "p24h": 7.3},\n'
        '      ...\n'
        '    ]\n'
        '  },\n'
        '  "correct": false   // YES + rained = wrong call\n'
        "}"
    ))

    story.append(callout(
        "Source labels surface directly in the History view as small badges"
        " (Open-Meteo / SIATA / Agreed) so a SIATA badge on a wrong prediction"
        " is the visual signal that microclimate rain was the specific failure"
        " mode."
    ))

    story.append(PageBreak())

    # ============================================================
    # 11. Automation — Cron schedule
    # ============================================================
    story += section("11. Automation")

    story.append(para(
        "Two Vercel Cron Jobs guarantee the daily prediction and backfill happen"
        " whether anyone visits the site or not. Both hit the same endpoint"
        " (<font face='Courier'>/api/cron</font>), which always runs both jobs"
        " — they're idempotent."
    ))

    cron_data = [
        ["Bogota", "UTC cron", "What it does"],
        ["20:00", "0 1 * * *", "Locks in tomorrow's prediction. The prediction is computed and written to predictions.json."],
        ["07:00", "0 12 * * *", "Backfills the just-finished ride's actual using SIATA + Open-Meteo (dual-source)."],
    ]
    t = Table(cron_data, colWidths=[1.0*inch, 1.4*inch, 4.3*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (1,1), (1,-1), "Courier"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(sub("Cron security"))
    story.append(para(
        "<font face='Courier'>/api/cron</font> is gated by"
        " <font face='Courier'>CRON_SECRET</font>, a strong random value stored"
        " as a Vercel environment variable. Vercel attaches"
        " <font face='Courier'>Authorization: Bearer ${CRON_SECRET}</font> to"
        " its outbound cron requests; the endpoint verifies and returns 401"
        " otherwise. The user-facing endpoints"
        " (<font face='Courier'>/api/check</font>,"
        " <font face='Courier'>/api/history</font>) stay unauthenticated so"
        " the browser UI works without secrets."
    ))

    story.append(sub("Why redundant logging?"))
    story.append(para(
        "<font face='Courier'>/api/check</font> and"
        " <font face='Courier'>/api/history</font> also opportunistically save"
        " predictions and backfill actuals — mirroring exactly what cron does."
        " That means the system stays current even if cron has a hiccup, as"
        " long as someone visits the site. Writes are upserts keyed by ride_date"
        " and refuse to overwrite once an actual is recorded, so the redundancy"
        " is safe."
    ))

    story.append(PageBreak())

    # ============================================================
    # 12. UI tour
    # ============================================================
    story += section("12. UI Tour")

    story.append(sub("Main view"))
    story.append(para(
        "The primary card shows tomorrow's <b>vibe line</b> (a playful one-liner"
        " keyed to the score), the numeric <b>score</b> with a gradient bar,"
        " <b>confidence</b>, the <b>05:00–07:30 riding window</b>, the inferred"
        " <b>road conditions</b>, the human-readable <b>reasons</b> that fed the"
        " score, and the live status of each <b>data source</b>."
    ))

    story.append(sub("More Details"))
    story.append(para(
        "A toggle expands the detail panel, which is purely informational:"
    ))
    story.append(bullets([
        "<b>Air Quality</b> — current PM2.5, PM10, US AQI, European AQI from Open-Meteo. Color-coded badge using the standard EPA scale.",
        "<b>Radar</b> — the last ~12 SIATA radar frames overlaid on an OpenStreetMap of the Aburrá Valley, cycling every 600 ms. The route polyline is drawn on top so you can read precipitation against the actual road.",
        "<b>Stations on the Climb</b> — Leaflet mini-map showing each corridor station as a colored pin (green = dry, blue = active rain, gray = offline), with the route polyline. Tapping a pin pops up the station's name, neighborhood, distance from the route, and all four rain signals (now, 10m, 1h, 24h).",
    ]))

    story.append(sub("History"))
    story.append(para(
        "Stats card (accuracy %, correct count, wrong count, pending count)"
        " plus a list of recent predictions with verdict (correct / wrong /"
        " pending), source badge (Open-Meteo / SIATA / Agreed), and the score"
        " in the route's accent color."
    ))

    story.append(sub("Language toggle"))
    story.append(para(
        "A circular EN/ES button fixed to the top-right corner toggles the UI"
        " between English and Colombian Spanish. The choice persists in"
        " <font face='Courier'>localStorage</font>. Dates use the matching"
        " locale (en-US vs es-CO). Backend-generated reasons currently stay in"
        " English regardless — see Limitations."
    ))

    story.append(PageBreak())

    # ============================================================
    # 13. Refresh & caching
    # ============================================================
    story += section("13. Refresh & Caching Semantics")

    story.append(para(
        "Three caching layers exist; understanding them prevents the surprise"
        " of \"I clicked refresh but nothing changed.\""
    ))

    cache_data = [
        ["Layer", "TTL", "Bypassed by"],
        ["Vercel CDN (in front of static assets)", "Standard immutable for /static/*; /api/* is non-cacheable", "n/a (already correct)"],
        ["In-memory cache (cache.py, per Vercel function instance)", "5 minutes per URL", "Refresh button (?fresh=1) clears it explicitly."],
        ["Vercel Blob CDN (in front of predictions.json)", "Up to ~60 seconds even with cache-control: private", "Etag-based cache-busting query string: ?v=<etag>"],
    ]
    t = Table(cache_data, colWidths=[2.4*inch, 2.0*inch, 2.3*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(para(
        "The <b>Refresh button</b> is the user-facing escape hatch: clicking it"
        " sends a request with <font face='Courier'>?fresh=1</font> and"
        " <font face='Courier'>cache: \"no-store\"</font>. The server clears its"
        " in-memory cache before fetching, and the blob read uses the etag"
        " cache-buster so the just-written prediction is visible immediately."
        " The <b>Last updated</b> timestamp on the main card makes any successful"
        " refresh visible even when the underlying numbers haven't changed."
    ))

    story.append(PageBreak())

    # ============================================================
    # 14. Limitations
    # ============================================================
    story += section("14. Limitations & Known Trade-offs")

    story.append(bullets([
        "<b>SIATA detail files are rolling.</b> Their per-station endpoints expose only p10m / p1h / p24h — there's no archive. So we cannot retroactively reconstruct a past day's rain from SIATA. Going forward, the 07:00 cron captures p24h daily; before that, history is limited to what Open-Meteo's grid recorded.",
        "<b>Backend-generated reasons are English-only.</b> The score formula returns fully-formed sentences (\"Moderate/low rain probability (28%)\"). Localizing them would require refactoring analyze.py to return structured keys and formatting on the frontend.",
        "<b>The score is heuristic, not probabilistic.</b> A score of 100 is not P(dry) = 1.0. With enough logged predictions + actuals, calibration becomes possible — that's what the audit trail is preparing for.",
        "<b>Vercel Hobby tier function timeout is 10 s.</b> Current /api/check runtime is ~5 s in the worst case (15 parallel SIATA detail fetches + Open-Meteo + radar JSON). There's headroom but not infinite.",
        "<b>WRF and radar are not in the score.</b> They are shown to the rider but never weighted. A future refinement could parse WRF's morning rain levels (BAJA / MEDIA / ALTA / MUY ALTA) into a small penalty.",
    ]))

    story.append(Spacer(1, 8))
    story.append(callout(
        "These are deliberate boundaries, not unfixed bugs. Each one is a tradeoff:"
        " more sources = more latency and more places for one signal to dominate;"
        " full localization = more code surface; calibrated probabilities require"
        " a much larger labelled dataset than we currently have."
    ))

    story.append(PageBreak())

    # ============================================================
    # 15. Future work
    # ============================================================
    story += section("15. Future Work")

    story.append(bullets([
        "<b>Calibrated probability display.</b> Once the log holds ~30 days of"
        " evaluated predictions, fit a simple isotonic-regression calibrator from"
        " score → P(dry) and display the calibrated number alongside the raw score.",
        "<b>Score auto-tuning.</b> The decision threshold is hardcoded at 50."
        " With a labelled history, that threshold can be set to whatever maximizes"
        " correct calls on the rider's own data.",
        "<b>Per-source accuracy breakdown.</b> Which signal predicts best —"
        " Open-Meteo's precip probability, SIATA's overnight readings, the WRF"
        " forecast? Splitting accuracy by source would reveal which inputs are"
        " carrying the weight.",
        "<b>WRF in the score.</b> Add a small penalty for MUY ALTA / ALTA in the"
        " morning forecast, since it currently contributes nothing.",
        "<b>Push notification at 20:30 Bogota.</b> When the cron finishes the"
        " 20:00 prediction, optionally fire a push or email summarizing tomorrow's"
        " call so the rider doesn't have to open the site.",
        "<b>Backend reason localization.</b> Return structured keys with params"
        " instead of pre-formatted sentences, so the EN/ES toggle covers the"
        " reasons too.",
    ]))

    story.append(PageBreak())

    # ============================================================
    # APPENDIX A — Config knobs
    # ============================================================
    story += section("Appendix A — Configurable Knobs")

    story.append(para(
        "All of these live in <font face='Courier'>config.py</font> and can be"
        " adjusted without touching the rest of the codebase."
    ))

    knobs = [
        ["Knob", "Default", "What it controls"],
        ["RIDE_EARLIEST", "5", "First hour of the ride window (Bogota)"],
        ["RIDE_LATEST", "7", "Hour the ride window ends (07:00–07:59 inclusive)"],
        ["CORRIDOR_RADIUS_KM", "1.5", "Max km a station can sit off-route to count"],
        ["SCORING.rain_prob_high_threshold", "60 %", "Threshold above which the rain-probability penalty fires"],
        ["SCORING.rain_prob_high_penalty", "−40", "Penalty applied above the threshold"],
        ["SCORING.active_rainfall_penalty", "−50", "Applied when any corridor station reports rain"],
        ["SCORING.high_wind_threshold", "20 km/h", "Above this max wind triggers the wind penalty"],
        ["SCORING.high_wind_penalty", "−15", "Applied above the wind threshold"],
        ["SCORING.high_humidity_threshold", "90 %", "Above this avg humidity triggers the humidity penalty"],
        ["SCORING.high_humidity_penalty", "−10", "Applied above the humidity threshold"],
        ["SCORING.dry_window_bonus", "+25", "All hours in window must be precip < 0.1 mm AND prob < 50 %"],
        ["SCORING.no_recent_rain_bonus", "+10", "No corridor station reporting rain"],
        ["SCORING.wet_road_penalty", "−15", "Applied when roads are inferred wet (half for damp)"],
        ["CACHE_TTL_SECONDS", "300", "How long the in-memory cache holds each SIATA / OM response"],
    ]
    t = Table(knobs, colWidths=[2.7*inch, 1.1*inch, 3.0*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (0,-1), "Courier"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("FONTNAME", (1,1), (1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "CENTER"),
    ]))
    story.append(t)

    story.append(PageBreak())

    # ============================================================
    # APPENDIX B — Endpoints
    # ============================================================
    story += section("Appendix B — HTTP Endpoints")

    eps = [
        ["Endpoint", "Method", "Auth", "Purpose"],
        ["/api/check", "GET", "none", "Compute & return tomorrow's prediction. Side effect: opportunistic save + backfill. Supports ?fresh=1 to bypass the in-memory cache."],
        ["/api/history", "GET", "none", "Return the prediction log + accuracy stats. Side effect: opportunistic backfill of pending actuals."],
        ["/api/cron", "GET", "Bearer CRON_SECRET", "Cron-only endpoint. Always logs tomorrow's prediction AND backfills pending actuals. Fail-closed if CRON_SECRET is unset."],
        ["/api/health", "GET", "none", "Simple liveness probe."],
    ]
    t = Table(eps, colWidths=[1.0*inch, 0.6*inch, 1.3*inch, 3.9*inch], hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), INK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (0,-1), "Courier"),
        ("FONTNAME", (2,1), (2,-1), "Courier"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND", (0,1), (-1,-1), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, RULE),
        ("ALIGN", (1,0), (1,-1), "CENTER"),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    story.append(sub("Repository"))
    story.append(small(
        "github.com/bensykora997/palmasridechecker"
    ))
    story.append(sub("File map"))
    story.append(code(
        "config.py             # Tuning knobs (corridor radius, scoring weights)\n"
        "palmas_route_data.py  # Avenida de Las Palmas geometry from OSM\n"
        "timeutil.py           # Bogota timezone shim\n"
        "fetch_siata.py        # SIATA pluvio + radar + WRF\n"
        "fetch_openmeteo.py    # Open-Meteo forecast + archive\n"
        "fetch_air.py          # Open-Meteo air quality\n"
        "analyze.py            # Score + road conditions + station analysis\n"
        "cache.py              # 5-minute in-memory cache\n"
        "db.py                 # Vercel Blob client (predictions.json)\n"
        "api/check.py          # GET /api/check\n"
        "api/history.py        # GET /api/history\n"
        "api/cron.py           # GET /api/cron (Bearer auth)\n"
        "api/health.py         # GET /api/health\n"
        "static/               # index.html + app.js + style.css (vanilla + Leaflet)\n"
        "vercel.json           # Routes + cron schedule"
    ))

    # ============================================================
    # Footer / closer
    # ============================================================
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="40%", thickness=1, color=ACCENT, hAlign="CENTER", spaceBefore=0, spaceAfter=12))
    story.append(Paragraph(
        "<i>Buenas pintas y a clavar, parcero.</i>",
        ParagraphStyle("End", parent=NORMAL, alignment=TA_CENTER, textColor=MUTED, fontSize=10)
    ))

    doc.build(story)
    print(f"Wrote {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
