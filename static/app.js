const main = document.getElementById("main");

const DAYS_ES = [
  "domingo", "lunes", "martes", "miércoles",
  "jueves", "viernes", "sábado",
];
const MONTHS_ES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function formatDateES(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  const day = DAYS_ES[d.getDay()];
  const num = d.getDate();
  const month = MONTHS_ES[d.getMonth()];
  return `${day}, ${num} de ${month}`;
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

const ROAD_LABELS = {
  dry: "Dry",
  mostly_dry: "Mostly Dry",
  damp: "Damp",
  wet: "Wet",
  unknown: "Unknown",
};

function getVibe(score) {
  if (score >= 90) return { emoji: "🚴‍♂️💨", text: "Kit up and clip in!", cls: "yes" };
  if (score >= 75) return { emoji: "🔥", text: "Send it, parcero!", cls: "yes" };
  if (score >= 60) return { emoji: "🦺", text: "Rideable — pack a gilet", cls: "yes" };
  if (score >= 50) return { emoji: "🎲", text: "Roll the dice, roll the wheels", cls: "yes" };
  if (score >= 35) return { emoji: "🪨", text: "Zwift and chill, bro", cls: "no" };
  if (score >= 20) return { emoji: "🌧️", text: "Not today, parcero", cls: "no" };
  return              { emoji: "🛋️", text: "Rest day — zero guilt", cls: "no" };
}

function render(data) {
  const ds = data.data_sources;
  const road = data.road_conditions || { condition: "unknown", detail: "", factors: [] };
  const vibe = getVibe(data.score);

  main.innerHTML = `
    <div class="card">
      <div class="decision-hero">
        <div class="decision-emoji">${vibe.emoji}</div>
        <div class="decision-text ${vibe.cls}">
          ${vibe.text}
        </div>
        <div class="decision-date">${formatDateES(data.tomorrow_date)}</div>
      </div>

      <div class="score-section">
        <div class="score-header">
          <span class="score-label">Ride Score</span>
          <span class="score-value" style="color:${scoreColor(data.score)}">${data.score}/100</span>
        </div>
        <div class="score-bar">
          <div class="score-fill" id="scoreFill"></div>
        </div>
      </div>

      <div class="confidence-row">
        <span class="badge ${data.confidence}">Confidence: ${data.confidence}</span>
      </div>

      <div class="window-card">
        <div class="window-icon">🕐</div>
        <div>
          <div class="window-label">Riding window</div>
          <div class="window-time">05:00 – 07:30</div>
        </div>
      </div>
    </div>

    <div class="road-card">
      <div class="road-header">
        <div class="road-icon">${ROAD_ICONS[road.condition] || "❓"}</div>
        <div>
          <div class="road-title">Road Conditions</div>
          <div class="road-status ${road.condition}">${ROAD_LABELS[road.condition] || "Unknown"}</div>
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
      <div class="reasons-title">Analysis</div>
      ${data.reasons.map(r => `
        <div class="reason-item">
          <div class="reason-dot"></div>
          <div>${r}</div>
        </div>
      `).join("")}
    </div>

    <div class="sources-card">
      <div class="reasons-title">Data Sources</div>
      <div class="source-row">
        <span class="source-name">SIATA Stations</span>
        <span class="source-status">
          ${ds.siata_stations.count} nearby (${ds.siata_stations.offline} offline)
          <span class="dot ${ds.siata_stations.count > 0 ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">Radar</span>
        <span class="source-status">
          ${ds.radar.available ? "Active" : "Unavailable"}
          <span class="dot ${ds.radar.available ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">WRF Forecast</span>
        <span class="source-status">
          ${ds.wrf_forecast.available ? "Available" : "Unavailable"}
          <span class="dot ${ds.wrf_forecast.available ? "on" : "off"}"></span>
        </span>
      </div>
      <div class="source-row">
        <span class="source-name">Open-Meteo</span>
        <span class="source-status">
          ${ds.open_meteo.available ? "Available" : "Unavailable"}
          <span class="dot ${ds.open_meteo.available ? "on" : "off"}"></span>
        </span>
      </div>
    </div>

    <div class="actions-row">
      <button class="refresh-btn" onclick="load()">Refresh</button>
      <button class="refresh-btn secondary" onclick="loadHistory()">View History</button>
    </div>
  `;

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
      <p>Failed to load data</p>
      <p style="font-size:0.85rem;margin-top:0.5rem;opacity:0.7">${msg}</p>
      <button class="refresh-btn" style="margin-top:1rem" onclick="load()">Retry</button>
    </div>
  `;
}

function renderHistory(data) {
  if (!data.enabled) {
    main.innerHTML = `
      <div class="card">
        <div class="reasons-title">History unavailable</div>
        <p style="opacity:0.75;font-size:0.9rem;margin-top:0.5rem">
          ${data.error || "Logging is not configured. Set POSTGRES_URL to enable."}
        </p>
        <button class="refresh-btn" style="margin-top:1rem" onclick="load()">Back</button>
      </div>
    `;
    return;
  }

  const s = data.stats || {};
  const accuracy = s.accuracy_pct == null ? "—" : `${s.accuracy_pct}%`;

  const rows = (data.predictions || []).map(p => {
    const date = formatDateES(p.ride_date);
    const verdict = p.correct === true ? "✓"
                  : p.correct === false ? "✗"
                  : "…";
    const verdictCls = p.correct === true ? "ok"
                     : p.correct === false ? "bad"
                     : "pending";
    const actualBit = p.actual
      ? (p.actual.rained
          ? `rained (${p.actual.precip_mm}mm)`
          : `dry (${p.actual.precip_mm}mm)`)
      : "pending";
    return `
      <div class="history-row">
        <div class="history-date">
          <div class="history-verdict ${verdictCls}">${verdict}</div>
          <div>
            <div>${date}</div>
            <div class="history-sub">Predicted: ${p.decision} · Actual: ${actualBit}</div>
          </div>
        </div>
        <div class="history-score" style="color:${scoreColor(p.score)}">${p.score}</div>
      </div>
    `;
  }).join("");

  main.innerHTML = `
    <div class="card">
      <div class="reasons-title">Prediction Accuracy</div>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-num">${accuracy}</div>
          <div class="stat-label">accuracy</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.correct || 0}</div>
          <div class="stat-label">correct</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.wrong || 0}</div>
          <div class="stat-label">wrong</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">${s.pending || 0}</div>
          <div class="stat-label">pending</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="reasons-title">Recent Predictions</div>
      ${rows || '<p style="opacity:0.6;font-size:0.9rem;margin-top:0.5rem">No predictions logged yet.</p>'}
    </div>

    <button class="refresh-btn" onclick="load()">Back to Today</button>
  `;
}

async function loadHistory() {
  main.innerHTML = `
    <div class="loader" id="loader">
      <div class="spinner"></div>
      <p>Loading history…</p>
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

async function load() {
  main.innerHTML = `
    <div class="loader" id="loader">
      <div class="spinner"></div>
      <p>Fetching weather data…</p>
    </div>
  `;

  try {
    const res = await fetch("/api/check");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    render(data);
  } catch (err) {
    renderError(err.message);
  }
}

load();
