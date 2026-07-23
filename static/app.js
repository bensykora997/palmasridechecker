const main = document.getElementById("main");

// ---------- i18n (UI chrome only — backend-generated reasons stay in English) ----------

const T = {
  en: {
    subtitle: "Alto de Palmas · Medellín · Tomorrow morning",
    subtitle_today: "Alto de Palmas · Medellín · This morning",
    subtitle_tomorrow: "Alto de Palmas · Medellín · Tomorrow morning",
    framing_this_morning: "This morning",
    framing_tomorrow_morning: "Tomorrow morning",
    share: "Share",
    share_yes: "YES", share_no: "NO",
    offline_banner: "Offline — showing last update from",
    score_label: "Ride Score",
    confidence: "Confidence",
    confidence_high: "high", confidence_medium: "medium", confidence_low: "low",
    window_label: "Riding window",
    road_title: "Road Conditions",
    road_dry: "Dry", road_mostly_dry: "Mostly Dry", road_damp: "Damp",
    road_wet: "Wet", road_unknown: "Unknown",
    analysis: "Analysis",
    data_sources: "Data Sources",
    siata_stations: "SIATA Stations",
    radar: "Radar",
    wrf_forecast: "WRF Forecast",
    open_meteo: "Open-Meteo",
    available: "Available", unavailable: "Unavailable", active: "Active",
    nearby_suffix: "nearby", offline_suffix: "offline",
    refresh: "Refresh", more_details: "More Details", hide_details: "Hide Details",
    history: "History",
    last_updated: "Last updated",
    air_quality: "Air Quality",
    aqi_disclaimer: "Not factored into the ride score.",
    aqi_unavailable: "Air quality data unavailable.",
    radar_unavailable: "Radar unavailable.",
    stations_on_climb: "Stations on the Climb",
    legend_raining: "Raining", legend_dry: "Dry", legend_offline: "Offline",
    legend_route: "Route",
    fetching: "Fetching weather data…",
    failed_load: "Failed to load data",
    retry: "Retry",
    loading_history: "Loading history…",
    history_unavailable: "History unavailable",
    history_unavailable_reason: "Logging is not configured.",
    back: "Back", back_to_today: "Back to Today",
    prediction_accuracy: "Prediction Accuracy",
    accuracy: "accuracy", correct: "correct", wrong: "wrong", pending: "pending",
    recent_predictions: "Recent Predictions",
    no_predictions: "No predictions logged yet.",
    predicted: "Predicted", actual: "Actual",
    rained_label: "rained", dry_label: "dry", pending_label: "pending",
    popup_now: "Now", popup_route_suffix: "km from route",
    source_open_meteo: "🛰️ Open-Meteo", source_siata: "📡 SIATA", source_agreed: "✓ Agreed",
    override_badge: "✏️ Manual",
    override_actual: "you said",
    override_prompt: "What actually happened?",
    override_rained: "It rained",
    override_dry: "It was dry",
    override_clear: "Clear override",
    token_prompt: "Enter override password:",
    token_wrong: "Wrong password — override cancelled.",
    override_saved: "Override saved.",
    override_failed: "Couldn't save override:",
    overridden_label: "overridden",
    shadow_prefix: "Learned model would say",
    shadow_rain_suffix: "rain",
    calibration_title: "Self-Calibration",
    cal_stage: "Stage",
    cal_gathering: "Gathering data",
    cal_stage_threshold: "Threshold tuning",
    cal_stage_probability: "Probability",
    cal_stage_weights: "Weight learning",
    cal_data: "Evaluated days",
    cal_next_unlock: "Next unlock",
    cal_at: "at",
    cal_days: "days",
    cal_rained: "rained",
    cal_hand_tuned: "Hand-tuned",
    cal_calibrated: "Calibrated",
    cal_accuracy: "accuracy",
    cal_balanced: "balanced",
    cal_threshold_learned: "Learned cutoff",
    cal_weights_learned: "Learned weights",
    cal_shadow_note: "Shadow mode — the hand-tuned formula still drives the decision shown above. This panel shows what a model trained on your logged outcomes would do.",
    vibes: [
      [90, "🚴‍♂️💨", "Kit up and clip in!", "yes"],
      [75, "🔥", "Send it, parcero!", "yes"],
      [60, "🦺", "Rideable — pack a gilet", "yes"],
      [50, "🎲", "Roll the dice, roll the wheels", "yes"],
      [35, "🪨", "Zwift and chill, bro", "no"],
      [20, "🌧️", "Not today, parcero", "no"],
      [0,  "🛋️", "Rest day — zero guilt", "no"],
    ],
  },
  es: {
    subtitle: "Alto de Palmas · Medellín · Mañana por la mañana",
    subtitle_today: "Alto de Palmas · Medellín · Esta mañana",
    subtitle_tomorrow: "Alto de Palmas · Medellín · Mañana por la mañana",
    framing_this_morning: "Esta mañana",
    framing_tomorrow_morning: "Mañana por la mañana",
    share: "Compartir",
    share_yes: "SÍ", share_no: "NO",
    offline_banner: "Sin conexión — última actualización de las",
    score_label: "Puntaje de salida",
    confidence: "Confianza",
    confidence_high: "alta", confidence_medium: "media", confidence_low: "baja",
    window_label: "Ventana de salida",
    road_title: "Estado de la vía",
    road_dry: "Seca", road_mostly_dry: "Casi seca", road_damp: "Húmeda",
    road_wet: "Mojada", road_unknown: "Desconocido",
    analysis: "Análisis",
    data_sources: "Fuentes de datos",
    siata_stations: "Estaciones SIATA",
    radar: "Radar",
    wrf_forecast: "Pronóstico WRF",
    open_meteo: "Open-Meteo",
    available: "Disponible", unavailable: "No disponible", active: "Activo",
    nearby_suffix: "cerca", offline_suffix: "sin señal",
    refresh: "Actualizar", more_details: "Más detalles", hide_details: "Ocultar detalles",
    history: "Historial",
    last_updated: "Última actualización",
    air_quality: "Calidad del aire",
    aqi_disclaimer: "No afecta el puntaje de salida.",
    aqi_unavailable: "Calidad del aire no disponible.",
    radar_unavailable: "Radar no disponible.",
    stations_on_climb: "Estaciones del ascenso",
    legend_raining: "Lluvia", legend_dry: "Sin lluvia", legend_offline: "Sin señal",
    legend_route: "Ruta",
    fetching: "Obteniendo datos del clima…",
    failed_load: "Error al cargar los datos",
    retry: "Reintentar",
    loading_history: "Cargando historial…",
    history_unavailable: "Historial no disponible",
    history_unavailable_reason: "El registro no está configurado.",
    back: "Atrás", back_to_today: "Volver a hoy",
    prediction_accuracy: "Precisión de predicciones",
    accuracy: "precisión", correct: "correctas", wrong: "incorrectas", pending: "pendientes",
    recent_predictions: "Predicciones recientes",
    no_predictions: "Aún no hay predicciones registradas.",
    predicted: "Predicción", actual: "Real",
    rained_label: "llovió", dry_label: "seco", pending_label: "pendiente",
    popup_now: "Ahora", popup_route_suffix: "km de la ruta",
    source_open_meteo: "🛰️ Open-Meteo", source_siata: "📡 SIATA", source_agreed: "✓ De acuerdo",
    override_badge: "✏️ Manual",
    override_actual: "dijiste",
    override_prompt: "¿Qué pasó en realidad?",
    override_rained: "Llovió",
    override_dry: "Estuvo seco",
    override_clear: "Quitar marca manual",
    token_prompt: "Ingresá la contraseña de override:",
    token_wrong: "Contraseña incorrecta — se canceló la marca.",
    override_saved: "Marca guardada.",
    override_failed: "No se pudo guardar:",
    overridden_label: "manuales",
    shadow_prefix: "El modelo aprendido diría",
    shadow_rain_suffix: "lluvia",
    calibration_title: "Auto-calibración",
    cal_stage: "Etapa",
    cal_gathering: "Recolectando datos",
    cal_stage_threshold: "Ajuste de umbral",
    cal_stage_probability: "Probabilidad",
    cal_stage_weights: "Aprendizaje de pesos",
    cal_data: "Días evaluados",
    cal_next_unlock: "Próximo nivel",
    cal_at: "a los",
    cal_days: "días",
    cal_rained: "con lluvia",
    cal_hand_tuned: "Manual",
    cal_calibrated: "Calibrado",
    cal_accuracy: "precisión",
    cal_balanced: "balanceada",
    cal_threshold_learned: "Umbral aprendido",
    cal_weights_learned: "Pesos aprendidos",
    cal_shadow_note: "Modo sombra — la fórmula manual sigue decidiendo lo de arriba. Este panel muestra qué haría un modelo entrenado con tus resultados registrados.",
    vibes: [
      [90, "🚴‍♂️💨", "¡Listos, a clavar!", "yes"],
      [75, "🔥", "¡Dale parce, mándale!", "yes"],
      [60, "🦺", "Rodable — llevá chaleco", "yes"],
      [50, "🎲", "A jugársela con las llantas", "yes"],
      [35, "🪨", "Mejor Zwift y chao", "no"],
      [20, "🌧️", "Hoy no, parcero", "no"],
      [0,  "🛋️", "Día de descanso — sin culpa", "no"],
    ],
  },
};

let LANG = (localStorage.getItem("palmas_lang") === "en") ? "en" : "es";
const t = (key) => (T[LANG] && T[LANG][key]) || T.en[key] || key;

function setLanguage(lang) {
  LANG = (lang === "en") ? "en" : "es";
  localStorage.setItem("palmas_lang", LANG);
  document.documentElement.lang = LANG;
  const btn = document.getElementById("langToggle");
  if (btn) btn.textContent = LANG === "en" ? "ES" : "EN";
  document.querySelector(".subtitle").textContent = t("subtitle");
  if (window.__lastData) render(window.__lastData);
}

// Localized date — "domingo, 24 de mayo" in ES, "Sunday, May 24" in EN.
function formatDate(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  if (LANG === "en") {
    return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  }
  return d.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
}

// Which day's morning the prediction is for. Falls back to "tomorrow_morning".
function framingOf(data) {
  return (data && data.framing) || "tomorrow_morning";
}
function framingLabel(data) {
  return t("framing_" + framingOf(data));
}

// ---------- WhatsApp / native share ----------

const APP_URL = "https://palmasridechecker.vercel.app";

function buildShareText(data) {
  const yn = data.decision === "YES" ? t("share_yes") : t("share_no");
  const when = framingLabel(data).toLowerCase();
  // e.g. "🚴 Palmas — esta mañana: SÍ 92/100 · 05:00–07:30"
  return `🚴 Palmas — ${when}: ${yn} ${data.score}/100 · 05:00–07:30\n${APP_URL}`;
}

async function share() {
  const data = window.__lastData;
  if (!data) return;
  const text = buildShareText(data);
  // Prefer the native share sheet (includes WhatsApp on mobile).
  if (navigator.share) {
    try { await navigator.share({ text }); return; }
    catch (e) { if (e && e.name === "AbortError") return; /* else fall through */ }
  }
  // Fallback: open WhatsApp directly.
  window.open("https://wa.me/?text=" + encodeURIComponent(text), "_blank");
}

function scoreColor(score) {
  if (score >= 70) return "var(--accent-green)";
  if (score >= 40) return "var(--accent-orange)";
  return "var(--accent-red)";
}

function scoreBgPosition(score) {
  // Shift gradient so color matches score level
  if (score >= 80) return "100% 0";
  if (score >= 50) return "50% 0";
  return "0% 0";
}

const ROAD_ICONS = {
  dry: "☀️",
  mostly_dry: "🌤️",
  damp: "💧",
  wet: "🌊",
  unknown: "❓",
};

function roadLabel(condition) {
  const key = "road_" + condition;
  return t(key) || condition;
}

function getVibe(score) {
  const vibes = t("vibes");
  for (const [threshold, emoji, text, cls] of vibes) {
    if (score >= threshold) return { emoji, text, cls };
  }
  return { emoji: "🛋️", text: "", cls: "no" };
}

function render(data) {
  const ds = data.data_sources;
  const road = data.road_conditions || { condition: "unknown", detail: "", factors: [] };
  const vibe = getVibe(data.score);
  const now = new Date();
  const locale = LANG === "en" ? "en-US" : "es-CO";
  const updatedAt = now.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const confidenceLabel = t("confidence_" + data.confidence) || data.confidence;
  const targetDate = data.target_date || data.tomorrow_date;

  // Framing-aware subtitle ("This morning" vs "Tomorrow morning")
  const subtitleEl = document.querySelector(".subtitle");
  if (subtitleEl) {
    subtitleEl.textContent = framingOf(data) === "this_morning"
      ? t("subtitle_today") : t("subtitle_tomorrow");
  }

  // Shadow line — what the self-calibrating model would say (display only)
  let shadowLine = "";
  const sh = data.calibration_shadow;
  if (sh && sh.shadow_decision) {
    const pct = (sh.shadow_prob_rain != null)
      ? ` (${Math.round(sh.shadow_prob_rain * 100)}% ${t("shadow_rain_suffix")})`
      : "";
    shadowLine = `<div class="shadow-line">${t("shadow_prefix")}: <b>${sh.shadow_decision}</b>${pct}</div>`;
  }

  main.innerHTML = `
    <div class="card">
      <div class="decision-hero">
        <div class="decision-emoji">${vibe.emoji}</div>
        <div class="decision-text ${vibe.cls}">
          ${vibe.text}
        </div>
        <div class="decision-date">${framingLabel(data)} · ${formatDate(targetDate)}</div>
      </div>

      <div class="score-section">
        <div class="score-header">
          <span class="score-label">${t("score_label")}</span>
          <span class="score-value" style="color:${scoreColor(data.score)}">${data.score}/100</span>
        </div>
        <div class="score-bar">
          <div class="score-fill" id="scoreFill"></div>
        </div>
      </div>

      <div class="confidence-row">
        <span class="badge ${data.confidence}">${t("confidence")}: ${confidenceLabel}</span>
      </div>

      ${shadowLine}

      <div class="window-card">
        <div class="window-icon">🕐</div>
        <div>
          <div class="window-label">${t("window_label")}</div>
          <div class="window-time">05:00 – 07:30</div>
        </div>
      </div>
    </div>

    <div class="road-card">
      <div class="road-header">
        <div class="road-icon">${ROAD_ICONS[road.condition] || "❓"}</div>
        <div>
          <div class="road-title">${t("road_title")}</div>
          <div class="road-status ${road.condition}">${roadLabel(road.condition)}</div>
        </div>
      </div>
      <div class="road-detail">${road.detail}</div>
      ${road.factors.length ? `
        <div class="road-factors">
          ${road.factors.map(f => `
            <div class="road-factor">
              <div class="road-factor-dot"></div>
              <span>${f}</span>
            </div>
          `).join("")}
        </div>
      ` : ""}
    </div>

    <div class="reasons-card">
      <div class="reasons-title">${t("analysis")}</div>
      ${data.reasons.map(r => `
        <div class="reason-item">
          <div class="reason-dot"></div>
          <div>${r}</div>
        </div>
      `).join("")}
    </div>

    <div class="sources-card">
      <div class="reasons-title">${t("data_sources")}</div>
      <div class="source-row">
        <span class="source-name">${t("siata_stations")}</span>
        <span class="source-status">
          ${ds.siata_stations.count} ${t("nearby_suffix")} (${ds.siata_stations.offline} ${t("offline_suffix")})
          <span class="dot ${ds.siata_stations.count > 0 ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">${t("radar")}</span>
        <span class="source-status">
          ${ds.radar.available ? t("active") : t("unavailable")}
          <span class="dot ${ds.radar.available ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">${t("wrf_forecast")}</span>
        <span class="source-status">
          ${ds.wrf_forecast.available ? t("available") : t("unavailable")}
          <span class="dot ${ds.wrf_forecast.available ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">${t("open_meteo")}</span>
        <span class="source-status">
          ${ds.open_meteo.available ? t("available") : t("unavailable")}
          <span class="dot ${ds.open_meteo.available ? "on" : "off"}"></span>
        </span>
      </div>
    </div>

    <div id="details-slot"></div>

    <div class="updated-row">${t("last_updated")}: ${updatedAt}</div>

    <div class="actions-row">
      <button class="refresh-btn" onclick="refresh()">${t("refresh")}</button>
      <button class="refresh-btn secondary" onclick="share()">${t("share")}</button>
      <button class="refresh-btn secondary" id="detailsBtn" onclick="toggleDetails()">${t("more_details")}</button>
      <button class="refresh-btn secondary" onclick="loadHistory()">${t("history")}</button>
    </div>
  `;

  // Stash data for the details view to use
  window.__lastData = data;

  // Animate score bar
  requestAnimationFrame(() => {
    const fill = document.getElementById("scoreFill");
    if (fill) {
      fill.style.backgroundPosition = scoreBgPosition(data.score);
      fill.style.width = data.score + "%";
    }
  });
}

function renderError(msg) {
  main.innerHTML = `
    <div class="error-card">
      <p>${t("failed_load")}</p>
      <p style="font-size:0.85rem;margin-top:0.5rem;opacity:0.7">${msg}</p>
      <button class="refresh-btn" style="margin-top:1rem" onclick="refresh()">${t("retry")}</button>
    </div>
  `;
}

// ---------- More Details (radar + map + AQI) ----------

// Returns age of latest radar frame in minutes, or null if unparseable.
// SIATA frame timestamps are Bogota local time ("YYYY-MM-DD HH:MM"), UTC-5.
function _radarAgeMinutes(frames) {
  if (!frames || !frames.length) return null;
  const raw = frames[frames.length - 1].time; // e.g. "2026-06-21 15:22"
  const parsed = new Date(raw.trim().replace(" ", "T") + ":00-05:00");
  if (isNaN(parsed)) return null;
  return Math.round((Date.now() - parsed.getTime()) / 60000);
}

function _radarAgeLabel(minutes) {
  if (minutes == null) return "";
  if (minutes < 2) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return m > 0 ? `${h}h ${m}m ago` : `${h}h ago`;
}

let __radarTimer = null;
let __miniMap = null;
let __radarMap = null;

function toggleDetails() {
  const slot = document.getElementById("details-slot");
  const btn = document.getElementById("detailsBtn");
  if (!slot) return;
  if (slot.dataset.open === "1") {
    closeDetails();
    btn.textContent = t("more_details");
  } else {
    renderDetails(window.__lastData);
    slot.dataset.open = "1";
    btn.textContent = t("hide_details");
  }
}

function closeDetails() {
  const slot = document.getElementById("details-slot");
  if (!slot) return;
  if (__radarTimer) { clearInterval(__radarTimer); __radarTimer = null; }
  if (__miniMap) { __miniMap.remove(); __miniMap = null; }
  if (__radarMap) { __radarMap.remove(); __radarMap = null; }
  slot.innerHTML = "";
  slot.dataset.open = "0";
}

function aqiColor(tier) {
  return {
    good: "#2ecc71",
    moderate: "#f1c40f",
    usg: "#f0a030",
    unhealthy: "#e74c3c",
    very_unhealthy: "#9b59b6",
    hazardous: "#7b241c",
  }[tier] || "#888";
}

function renderDetails(data) {
  const slot = document.getElementById("details-slot");
  const d = (data && data.details) || {};
  const radar = d.radar || {};
  const stations = d.stations || [];
  const routeSegments = d.route_segments || [];
  const aqi = d.air_quality || {};

  slot.innerHTML = `
    <div class="card details-card">
      <div class="reasons-title">${t("air_quality")}</div>
      ${aqi.available ? `
        <div class="aqi-row">
          <div class="aqi-pill" style="background:${aqiColor(aqi.tier)}">${aqi.us_aqi ?? "—"}</div>
          <div>
            <div class="aqi-label">${aqi.label || "—"}</div>
            <div class="aqi-sub">PM2.5: ${aqi.pm2_5 ?? "—"} µg/m³ · PM10: ${aqi.pm10 ?? "—"} µg/m³ · EAQI: ${aqi.european_aqi ?? "—"}</div>
          </div>
        </div>
        <div class="aqi-note">${t("aqi_disclaimer")}</div>
      ` : `<p style="opacity:0.6;font-size:0.9rem">${t("aqi_unavailable")}</p>`}
    </div>

    <div class="card details-card">
      ${(() => {
        const radarAge = _radarAgeMinutes(radar.frames);
        const stale = radarAge != null && radarAge > 90;
        const ageLabel = _radarAgeLabel(radarAge);
        return `
          <div class="reasons-title radar-title-row">
            ${t("radar")}
            ${ageLabel ? `<span class="radar-age${stale ? " radar-age--stale" : ""}">${ageLabel}</span>` : ""}
          </div>
          ${radar.available && radar.frames && radar.frames.length ? `
            <div id="radar-map" class="radar-map"></div>
            <div id="radarTime" class="radar-time-inline"></div>
          ` : `<p style="opacity:0.6;font-size:0.9rem">${t("radar_unavailable")}</p>`}
        `;
      })()}
    </div>

    <div class="card details-card">
      <div class="reasons-title">${t("stations_on_climb")}</div>
      <div id="mini-map" class="mini-map"></div>
      <div class="map-legend">
        <span><span class="map-dot raining"></span> ${t("legend_raining")}</span>
        <span><span class="map-dot dry"></span> ${t("legend_dry")}</span>
        <span><span class="map-dot offline"></span> ${t("legend_offline")}</span>
        <span><span class="map-line"></span> ${t("legend_route")}</span>
      </div>
    </div>
  `;

  const allRoutePts = routeSegments.flat();

  const drawRoute = (map) => {
    routeSegments.forEach(seg => {
      if (seg.length >= 2) {
        L.polyline(seg, { color: "#f0a030", weight: 4, opacity: 0.85 }).addTo(map);
      }
    });
  };

  // Initialize the station map. Wait for Leaflet if it hasn't loaded yet.
  const initStationMap = () => {
    if (typeof L === "undefined") return setTimeout(initStationMap, 100);
    const mapEl = document.getElementById("mini-map");
    if (!mapEl) return;

    __miniMap = L.map(mapEl, { zoomControl: true, scrollWheelZoom: false }).setView([6.19, -75.52], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© OpenStreetMap', maxZoom: 18,
    }).addTo(__miniMap);

    drawRoute(__miniMap);

    const fmt = v => (v === null || v === undefined) ? "—" : `${Number(v).toFixed(1)} mm`;
    stations.forEach(s => {
      const color = s.offline ? "#888" : (s.raining ? "#4aa8ff" : "#2ecc71");
      const dot = L.circleMarker([s.lat, s.lon], {
        radius: 7, color: "#000", weight: 1, fillColor: color, fillOpacity: 0.9,
      }).addTo(__miniMap);
      const valStr = s.offline ? "offline" : fmt(s.value);
      dot.bindPopup(`
        <b>${s.name}</b><br>
        ${s.neighborhood || ""}<br>
        ${t("popup_now")}: ${valStr} · 10m: ${fmt(s.p10m)} · 1h: ${fmt(s.p1h)} · 24h: ${fmt(s.p24h)}<br>
        ${s.distance_km} ${t("popup_route_suffix")}
      `);
    });

    const bounds = [];
    allRoutePts.forEach(p => bounds.push(p));
    stations.forEach(s => bounds.push([s.lat, s.lon]));
    if (bounds.length) __miniMap.fitBounds(bounds, { padding: [20, 20] });
  };

  // Initialize the radar map (PNG overlay using SIATA bounds)
  const initRadarMap = () => {
    if (!radar.available || !radar.frames || !radar.frames.length) return;
    if (typeof L === "undefined") return setTimeout(initRadarMap, 100);
    const mapEl = document.getElementById("radar-map");
    if (!mapEl) return;

    const b = radar.bounds || {};
    const radarBounds = (b.north != null && b.south != null && b.east != null && b.west != null)
      ? [[b.south, b.west], [b.north, b.east]]
      : null;

    __radarMap = L.map(mapEl, { zoomControl: true, scrollWheelZoom: false }).setView([6.19, -75.55], 9);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© OpenStreetMap', maxZoom: 14,
    }).addTo(__radarMap);

    drawRoute(__radarMap);

    // Pre-create one overlay per frame; all images fetch in parallel so each
    // frame is ready before the animation reaches it — no per-tick HTTP request.
    const overlays = radarBounds
      ? radar.frames.map((f, idx) =>
          L.imageOverlay(f.image, radarBounds, { opacity: idx === 0 ? 0.65 : 0 }).addTo(__radarMap)
        )
      : [];

    // Zoom to the climb area (with a buffer) rather than full radar coverage
    if (allRoutePts.length) {
      const lats = allRoutePts.map(p => p[0]);
      const lons = allRoutePts.map(p => p[1]);
      const buf = 0.04;
      __radarMap.fitBounds([
        [Math.min(...lats) - buf, Math.min(...lons) - buf],
        [Math.max(...lats) + buf, Math.max(...lons) + buf],
      ]);
    } else if (radarBounds) {
      __radarMap.fitBounds(radarBounds);
    }

    const timeLabel = document.getElementById("radarTime");
    let i = 0;
    if (timeLabel) timeLabel.textContent = radar.frames[0].time;
    const tick = () => {
      const next = (i + 1) % radar.frames.length;
      if (overlays.length) {
        overlays[i].setOpacity(0);
        overlays[next].setOpacity(0.65);
      }
      i = next;
      if (timeLabel) timeLabel.textContent = radar.frames[i].time;
    };
    __radarTimer = setInterval(tick, 600);
  };

  initStationMap();
  initRadarMap();
}

// ---------- Self-calibration panel ----------

function _pct(v) {
  return (v == null) ? "—" : `${Math.round(v * 100)}%`;
}

function calibrationPanel(cal) {
  if (!cal || cal.error) return "";

  const stageNames = {
    gathering: t("cal_gathering"),
    threshold: t("cal_stage_threshold"),
    probability: t("cal_stage_probability"),
    weights: t("cal_stage_weights"),
  };
  const stageLabel = stageNames[cal.stage] || cal.stage;

  // Gathering state — just show what's needed.
  if (cal.stage === "gathering") {
    const nu = cal.next_unlock || {};
    return `
      <div class="card cal-card">
        <div class="reasons-title">${t("calibration_title")}</div>
        <div class="cal-gathering">
          <div class="cal-stage-line">${t("cal_gathering")}</div>
          <div class="cal-sub">${cal.reason || ""}</div>
          <div class="cal-sub">${t("cal_data")}: ${cal.n_evaluated || 0} · ${cal.n_rained || 0} ${t("cal_rained")}</div>
        </div>
        <div class="cal-note">${t("cal_shadow_note")}</div>
      </div>
    `;
  }

  const base = cal.baseline || {};
  const c = cal.calibrated || {};
  const stageIdx = cal.stage_index || 1;

  // Next-unlock hint
  let unlockLine = "";
  if (cal.next_unlock) {
    const nu = cal.next_unlock;
    const at = nu.at_evaluated || nu.at_featured;
    const unlockStage = stageNames[nu.stage] || nu.stage;
    unlockLine = `<div class="cal-row"><span>${t("cal_next_unlock")}</span><span>${unlockStage} ${t("cal_at")} ${at} ${t("cal_days")}</span></div>`;
  }

  // Learned-model specifics by stage
  let learned = "";
  if (cal.stage === "threshold" && c.threshold != null) {
    learned = `<div class="cal-row"><span>${t("cal_threshold_learned")}</span><span>${c.threshold} (${t("cal_hand_tuned")}: ${base.threshold})</span></div>`;
  } else if (cal.stage === "weights" && c.weights && c.weights.coef) {
    const keys = (c.feature_keys || []);
    const items = c.weights.coef.map((coef, i) =>
      `<div class="cal-weight"><span>${keys[i] || ("f" + i)}</span><span>${coef >= 0 ? "+" : ""}${coef.toFixed(2)}</span></div>`
    ).join("");
    learned = `<div class="cal-weights-label">${t("cal_weights_learned")}</div><div class="cal-weights">${items}</div>`;
  }

  // Accuracy comparison — show both raw and balanced
  const accTable = `
    <div class="cal-acc-grid">
      <div class="cal-acc-head"></div>
      <div class="cal-acc-head">${t("cal_accuracy")}</div>
      <div class="cal-acc-head">${t("cal_balanced")}</div>

      <div class="cal-acc-name">${t("cal_hand_tuned")}</div>
      <div class="cal-acc-val">${_pct(base.accuracy)}</div>
      <div class="cal-acc-val">${_pct(base.balanced_accuracy)}</div>

      <div class="cal-acc-name">${t("cal_calibrated")}</div>
      <div class="cal-acc-val cal-hi">${_pct(c.accuracy)}</div>
      <div class="cal-acc-val cal-hi">${_pct(c.balanced_accuracy)}</div>
    </div>
  `;

  return `
    <div class="card cal-card">
      <div class="reasons-title">${t("calibration_title")}</div>
      <div class="cal-row"><span>${t("cal_stage")}</span><span>${stageLabel} (${stageIdx}/3)</span></div>
      <div class="cal-row"><span>${t("cal_data")}</span><span>${cal.n_evaluated} · ${cal.n_rained} ${t("cal_rained")}</span></div>
      ${unlockLine}
      ${accTable}
      ${learned}
      <div class="cal-note">${t("cal_shadow_note")}</div>
    </div>
  `;
}

// Last history payload, retained so an override can update the view from the
// authoritative POST response instead of a stale blob re-read (see setOverride).
let __historyData = null;

function _recomputeHistoryStats(preds) {
  const gt = p => {
    const ov = p.user_override || {};
    if (ov.rained != null) return !!ov.rained;
    const a = p.actual || {};
    if (a.rained != null) return !!a.rained;
    return null;
  };
  const total = preds.length;
  const evaluated = preds.filter(p => gt(p) !== null).length;
  const correct = preds.filter(p => p.correct === true).length;
  const wrong = preds.filter(p => p.correct === false).length;
  const overridden = preds.filter(p => (p.user_override || {}).rained != null).length;
  return {
    total_predictions: total,
    evaluated,
    pending: total - evaluated,
    correct,
    wrong,
    overridden,
    accuracy_pct: evaluated ? Math.round(1000 * correct / evaluated) / 10 : null,
  };
}

function renderHistory(data) {
  __historyData = data;   // retain for optimistic override updates
  if (!data.enabled) {
    main.innerHTML = `
      <div class="card">
        <div class="reasons-title">${t("history_unavailable")}</div>
        <p style="opacity:0.75;font-size:0.9rem;margin-top:0.5rem">
          ${data.error || t("history_unavailable_reason")}
        </p>
        <button class="refresh-btn" style="margin-top:1rem" onclick="load()">${t("back")}</button>
      </div>
    `;
    return;
  }

  const s = data.stats || {};
  const accuracy = s.accuracy_pct == null ? "—" : `${s.accuracy_pct}%`;

  const escapeAttr = s => String(s).replace(/"/g, "&quot;");

  const rows = (data.predictions || []).map(p => {
    const date = formatDate(p.ride_date);
    const verdict = p.correct === true ? "✓"
                  : p.correct === false ? "✗"
                  : "…";
    const verdictCls = p.correct === true ? "ok"
                     : p.correct === false ? "bad"
                     : "pending";
    const actualBit = p.actual
      ? (p.actual.rained
          ? `${t("rained_label")} (${p.actual.precip_mm}mm)`
          : `${t("dry_label")} (${p.actual.precip_mm}mm)`)
      : t("pending_label");

    // Source badge (sensor-derived)
    let sourceBadge = "";
    if (p.actual && p.actual.source) {
      const sourceMap = {
        "open_meteo": { label: t("source_open_meteo"), cls: "src-om" },
        "siata_p24h": { label: t("source_siata"),      cls: "src-siata" },
        "agreed":     { label: t("source_agreed"),     cls: "src-agreed" },
      };
      const info = sourceMap[p.actual.source] || { label: p.actual.source, cls: "" };
      sourceBadge = `<span class="src-badge ${info.cls}">${info.label}</span>`;
    }

    // Override badge — wins visual priority when present
    const ov = p.user_override;
    let overrideBadge = "";
    let overrideLine = "";
    if (ov && ov.rained !== undefined && ov.rained !== null) {
      overrideBadge = `<span class="src-badge src-override">${t("override_badge")}</span>`;
      const word = ov.rained ? t("rained_label") : t("dry_label");
      overrideLine = `<div class="history-override-line">${t("override_actual")}: <b>${word}</b></div>`;
    }

    const rd = escapeAttr(p.ride_date);
    const hasOverride = ov && ov.rained !== undefined && ov.rained !== null;
    const clearBtn = hasOverride
      ? `<button class="override-btn override-clear" onclick="event.stopPropagation(); clearOverride('${rd}')">${t("override_clear")}</button>`
      : "";

    return `
      <div class="history-row" data-history-row="${rd}">
        <div class="history-summary">
          <div class="history-date">
            <div class="history-verdict ${verdictCls}">${verdict}</div>
            <div>
              <div>${date}</div>
              <div class="history-sub">${t("predicted")}: ${p.decision} · ${t("actual")}: ${actualBit} ${overrideBadge}${sourceBadge}</div>
              ${overrideLine}
            </div>
          </div>
          <div class="history-score" style="color:${scoreColor(p.score)}">${p.score}</div>
        </div>
        <div class="history-controls">
          <div class="override-label">${t("override_prompt")}</div>
          <div class="override-buttons">
            <button class="override-btn override-rained" onclick="setOverride('${rd}', true)">${t("override_rained")}</button>
            <button class="override-btn override-dry" onclick="setOverride('${rd}', false)">${t("override_dry")}</button>
            ${clearBtn}
          </div>
        </div>
      </div>
    `;
  }).join("");

  const overrideCount = s.overridden || 0;
  const overrideLine = overrideCount > 0
    ? `<div class="overridden-line">${overrideCount} ${t("overridden_label")}</div>`
    : "";

  main.innerHTML = `
    <div class="card">
      <div class="reasons-title">${t("prediction_accuracy")}</div>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-num">${accuracy}</div>
          <div class="stat-label">${t("accuracy")}</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.correct || 0}</div>
          <div class="stat-label">${t("correct")}</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.wrong || 0}</div>
          <div class="stat-label">${t("wrong")}</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.pending || 0}</div>
          <div class="stat-label">${t("pending")}</div>
        </div>
      </div>
      ${overrideLine}
    </div>

    ${calibrationPanel(data.calibration)}

    <div class="card">
      <div class="reasons-title">${t("recent_predictions")}</div>
      ${rows || `<p style="opacity:0.6;font-size:0.9rem;margin-top:0.5rem">${t("no_predictions")}</p>`}
    </div>

    <button class="refresh-btn" onclick="load()">${t("back_to_today")}</button>
  `;
}

async function loadHistory() {
  main.innerHTML = `
    <div class="loader" id="loader">
      <div class="spinner"></div>
      <p>${t("loading_history")}</p>
    </div>
  `;
  try {
    const res = await fetch("/api/history");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderHistory(data);
  } catch (err) {
    renderError(err.message);
  }
}

async function load(forceFresh = false) {
  main.innerHTML = `
    <div class="loader" id="loader">
      <div class="spinner"></div>
      <p>${t("fetching")}</p>
    </div>
  `;

  try {
    // forceFresh: append a cache-buster and ?fresh=1 so the server skips its
    // in-memory cache. Plain page-load uses the default (cached) path so the
    // first paint is fast.
    const url = forceFresh
      ? `/api/check?fresh=1&_=${Date.now()}`
      : "/api/check";
    const res = await fetch(url, { cache: forceFresh ? "no-store" : "default" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Stash the last good prediction for the offline fallback.
    try {
      localStorage.setItem("palmas_last_check",
        JSON.stringify({ data, at: Date.now() }));
    } catch (e) { /* quota / private mode — ignore */ }
    render(data);
  } catch (err) {
    // Offline / network failure: fall back to the last good prediction with a
    // banner, instead of an error. Critical for the spotty-signal 4am case.
    const cached = _loadCachedCheck();
    if (cached) {
      render(cached.data);
      _showOfflineBanner(cached.at);
    } else {
      renderError(err.message);
    }
  }
}

function _loadCachedCheck() {
  try {
    const raw = localStorage.getItem("palmas_last_check");
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}

function _showOfflineBanner(atMs) {
  const locale = LANG === "en" ? "en-US" : "es-CO";
  const when = new Date(atMs).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  const div = document.createElement("div");
  div.className = "offline-banner";
  div.textContent = `${t("offline_banner")} ${when}`;
  main.prepend(div);
}

// Refresh button always forces a fresh fetch
function refresh() { return load(true); }

// ---------- User override (manual ground-truth marking) ----------

// Simple shared password — kept in sync with api/override.py.
// Light auth: deters casual abuse from someone who finds the URL,
// no need to store/prompt for a per-user token.
const OVERRIDE_PASSWORD = "palmas";

async function postOverride(rideDate, rained) {
  // Clean up any leftover token from earlier versions of this app.
  if (localStorage.getItem("palmas_override_token")) {
    localStorage.removeItem("palmas_override_token");
  }
  const res = await fetch("/api/override", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${OVERRIDE_PASSWORD}`,
    },
    body: JSON.stringify({ ride_date: rideDate, rained }),
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    alert(`${t("override_failed")} HTTP ${res.status} — ${txt.slice(0, 200)}`);
    return null;
  }
  const data = await res.json();
  return data.entry;
}

// Ask for the password once per session, then remember it — repeated marks
// shouldn't re-block with a dialog each time.
let __overrideAuthed = false;

async function setOverride(rideDate, rained) {
  if (!__overrideAuthed) {
    const pw = prompt(t("token_prompt"));
    if (pw === null) return;          // user hit Cancel
    if (pw !== OVERRIDE_PASSWORD) {
      alert(t("token_wrong"));
      return;
    }
    __overrideAuthed = true;
  }
  const entry = await postOverride(rideDate, rained);
  if (!entry) return;                 // failure already surfaced by postOverride

  // Render from the authoritative server response, NOT a fresh /api/history
  // fetch: Vercel Blob's CDN can serve a stale, override-less copy for up to
  // ~60s after the write, which made overrides look like they "did nothing."
  // set_override/clear_override return the entry only after a committed write,
  // so this can never get ahead of persisted state.
  if (__historyData && Array.isArray(__historyData.predictions)) {
    const preds = __historyData.predictions;
    const i = preds.findIndex(p => p.ride_date === rideDate);
    if (i >= 0) preds[i] = entry;     // full updated record (override cleared → no user_override key)
    __historyData.stats = _recomputeHistoryStats(preds);
    renderHistory(__historyData);
  } else {
    await loadHistory();              // first-load edge case: nothing retained yet
  }
}

function clearOverride(rideDate) {
  return setOverride(rideDate, null);
}

// Apply persisted language preference to the page chrome before first fetch
setLanguage(LANG);
load();
