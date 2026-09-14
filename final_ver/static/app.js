/**
 * app.js - SkyResolve AOCC Professional Dashboard Controller
 * (Person 1 Hackathon Implementation - Polished Edition)
 *
 * Coordinates real-time operations, telemetry clocks, AI Copilot conflict
 * remediation approvals, resource Gantt visualizers, and audit logging.
 */

const API_BASE = window.location.origin;

// Application State
const state = {
  flights: [],
  gates: [],
  crew: [],
  activeConflicts: [],
  activeSuggestions: [],
  autoRefresh: true,
  filterCategory: "all",
  searchTerm: "",
  auditLogs: [
    {
      time: "14:00:00",
      badge: "SYSTEM",
      badgeClass: "badge-cyan",
      msg: "SkyResolve AOCC engine initialized with 12 flights, 5 gates, 4 crews."
    }
  ]
};

// DOM References
const flightTableBody = document.getElementById("flightTableBody");
const flightSelect = document.getElementById("flightSelect");
const delayMinutesInput = document.getElementById("delayMinutes");
const delayForm = document.getElementById("delayForm");
const gatesGrid = document.getElementById("gatesGrid");
const crewGrid = document.getElementById("crewGrid");
const aiResolutionDeck = document.getElementById("aiResolutionDeck");
const alertsList = document.getElementById("alertsList");
const alertCountBadge = document.getElementById("alertCountBadge");
const flightSearch = document.getElementById("flightSearch");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const autoRefreshToggle = document.getElementById("autoRefreshToggle");
const btnResetDemo = document.getElementById("btnResetDemo");
const utcClock = document.getElementById("utcClock");
const localClock = document.getElementById("localClock");
const auditLogStream = document.getElementById("auditLogStream");
const btnClearLogs = document.getElementById("btnClearLogs");
const themeToggle = document.getElementById("themeToggle");
const themeToggleIcon = document.getElementById("themeToggleIcon");
const themeToggleText = document.getElementById("themeToggleText");
const accessScreen = document.getElementById("accessScreen");
const accessForm = document.getElementById("accessForm");
const operatorName = document.getElementById("operatorName");
const btnLogout = document.getElementById("btnLogout");
const operatorGreeting = document.getElementById("operatorGreeting");

// KPI Elements
const kpiTotalFlights = document.getElementById("kpiTotalFlights");
const kpiOnTime = document.getElementById("kpiOnTime");
const kpiOnTimePercent = document.getElementById("kpiOnTimePercent");
const kpiDelayed = document.getElementById("kpiDelayed");
const kpiDelayCount = document.getElementById("kpiDelayCount");
const kpiCritical = document.getElementById("kpiCritical");
const kpiConflictStatus = document.getElementById("kpiConflictStatus");
const kpiCriticalTile = document.getElementById("kpiCriticalTile");
const kpiGateOccupancy = document.getElementById("kpiGateOccupancy");
const kpiGateLoad = document.getElementById("kpiGateLoad");
const tabFlightCount = document.getElementById("tabFlightCount");

// -------------------------------------------------------------
// Clocks & Telemetry
// -------------------------------------------------------------
function tickClocks() {
  const now = new Date();
  utcClock.textContent = now.toISOString().substring(11, 19) + "Z";
  localClock.textContent = now.toTimeString().substring(0, 8);
}
setInterval(tickClocks, 1000);
tickClocks();

// -------------------------------------------------------------
// Colour theme
// -------------------------------------------------------------
function setTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  themeToggleIcon.textContent = isDark ? "☀" : "◐";
  themeToggleText.textContent = isDark ? "Light mode" : "Dark mode";
  themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
  localStorage.setItem("skyresolve-theme", theme);
}

setTheme(localStorage.getItem("skyresolve-theme") || "light");

themeToggle.addEventListener("click", () => {
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

// -------------------------------------------------------------
// Demo access screen
// -------------------------------------------------------------
function enterOperationsCenter(name) {
  const operator = name.trim();
  localStorage.setItem("skyresolve-operator", operator);
  operatorGreeting.textContent = ` · Hello, ${operator}`;
  accessScreen.classList.add("is-hidden");
  accessScreen.setAttribute("aria-hidden", "true");
}

const savedOperator = localStorage.getItem("skyresolve-operator");
if (savedOperator) {
  enterOperationsCenter(savedOperator);
} else {
  operatorName.focus();
}

accessForm.addEventListener("submit", event => {
  event.preventDefault();
  enterOperationsCenter(operatorName.value);
});

btnLogout.addEventListener("click", () => {
  localStorage.removeItem("skyresolve-operator");
  operatorGreeting.textContent = "";
  operatorName.value = "";
  accessScreen.classList.remove("is-hidden");
  accessScreen.setAttribute("aria-hidden", "false");
  requestAnimationFrame(() => operatorName.focus());
});

// -------------------------------------------------------------
// Toast Notifications
// -------------------------------------------------------------
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast-msg toast-${type}`;
  
  let icon = "✓";
  if (type === "danger") icon = "⚠";
  if (type === "info") icon = "ℹ";

  toast.innerHTML = `
    <span style="font-size: 1.1rem; font-weight: bold;">${icon}</span>
    <span style="flex: 1;">${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// -------------------------------------------------------------
// Audit Log Manager
// -------------------------------------------------------------
function addAuditLog(msg, badge = "OPS", badgeClass = "badge-green") {
  const time = new Date().toTimeString().substring(0, 8);
  state.auditLogs.unshift({ time, badge, badgeClass, msg });
  if (state.auditLogs.length > 50) state.auditLogs.pop();
  renderAuditLogs();
}

function renderAuditLogs() {
  if (!auditLogStream) return;
  auditLogStream.innerHTML = "";
  state.auditLogs.forEach(item => {
    const row = document.createElement("div");
    row.className = "audit-item";
    row.innerHTML = `
      <span class="audit-time">${item.time}</span>
      <span class="audit-badge ${item.badgeClass}">${item.badge}</span>
      <span class="audit-msg">${item.msg}</span>
    `;
    auditLogStream.appendChild(row);
  });
}

if (btnClearLogs) {
  btnClearLogs.addEventListener("click", () => {
    state.auditLogs = [];
    renderAuditLogs();
  });
}

// -------------------------------------------------------------
// API Data Synchronization
// -------------------------------------------------------------
async function fetchAllData() {
  try {
    const [flightsRes, gatesRes, crewRes] = await Promise.all([
      fetch(`${API_BASE}/flights`),
      fetch(`${API_BASE}/gates`),
      fetch(`${API_BASE}/crew`)
    ]);

    if (!flightsRes.ok || !gatesRes.ok || !crewRes.ok) {
      throw new Error("AOCC backend communication failure.");
    }

    state.flights = await flightsRes.json();
    state.gates = await gatesRes.json();
    state.crew = await crewRes.json();

    renderAllViews();
  } catch (err) {
    console.error("Sync error:", err);
  }
}

// -------------------------------------------------------------
// Master View Rendering
// -------------------------------------------------------------
function renderAllViews() {
  renderKPIs();
  renderFlightDropdown();
  renderFlightTable();
  renderGatesGrid();
  renderCrewGrid();
  renderAlertsDeck();
}

function renderKPIs() {
  const total = state.flights.length;
  let onTime = 0;
  let delayed = 0;
  let critical = 0;

  state.flights.forEach(f => {
    if (f.status === "ON_TIME") onTime++;
    else if (f.status === "DELAYED") delayed++;
    else if (f.status === "CRITICAL") critical++;
  });

  kpiTotalFlights.textContent = total;
  tabFlightCount.textContent = total;
  kpiOnTime.textContent = onTime;
  const onTimePct = total > 0 ? Math.round((onTime / total) * 100) : 100;
  kpiOnTimePercent.textContent = `${onTimePct}%`;

  kpiDelayed.textContent = delayed;
  kpiDelayCount.textContent = `${delayed} FLT`;

  kpiCritical.textContent = critical;
  if (critical > 0) {
    kpiConflictStatus.textContent = `${critical} ALERT`;
    kpiCriticalTile.classList.add("tile-red");
  } else {
    kpiConflictStatus.textContent = "CLEAR";
  }

  const occupiedGates = state.gates.filter(g => g.current_flight_id !== null).length;
  kpiGateOccupancy.textContent = `${occupiedGates} / ${state.gates.length}`;
  const loadPct = state.gates.length > 0 ? Math.round((occupiedGates / state.gates.length) * 100) : 0;
  kpiGateLoad.textContent = `${loadPct}%`;
}

function renderFlightDropdown() {
  const currentVal = flightSelect.value;
  flightSelect.innerHTML = `<option value="">-- Select Scheduled Flight --</option>`;
  state.flights.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f.id;
    opt.textContent = `${f.flight_no} • Sched ${f.sched_time} • Gate ${f.gate_id} (${f.status})`;
    if (f.id === currentVal) opt.selected = true;
    flightSelect.appendChild(opt);
  });
}

function getAirlineCode(flightNo) {
  const prefix = flightNo.substring(0, 2).toUpperCase();
  const known = ["AA", "UA", "DL", "BA", "AF", "LH", "SW", "QF"];
  return known.includes(prefix) ? prefix : "FL";
}

function renderFlightTable() {
  flightTableBody.innerHTML = "";
  const filter = state.searchTerm.toLowerCase();

  const gateMap = Object.fromEntries(state.gates.map(g => [g.id, g.name]));
  const crewMap = Object.fromEntries(state.crew.map(c => [c.id, c.name]));

  state.flights.forEach(f => {
    const gateName = gateMap[f.gate_id] || f.gate_id;
    const crewName = crewMap[f.crew_id] || f.crew_id;

    // Filter Category
    if (state.filterCategory === "on-time" && f.status !== "ON_TIME") return;
    if (state.filterCategory === "delayed" && f.status !== "DELAYED") return;
    if (state.filterCategory === "critical" && f.status !== "CRITICAL") return;

    // Search Query
    if (
      filter &&
      !f.flight_no.toLowerCase().includes(filter) &&
      !f.aircraft_id.toLowerCase().includes(filter) &&
      !gateName.toLowerCase().includes(filter) &&
      !crewName.toLowerCase().includes(filter)
    ) {
      return;
    }

    const schedMins = parseMinutes(f.sched_time);
    const estMins = parseMinutes(f.est_time);
    const diffMins = estMins - schedMins;

    const tr = document.createElement("tr");
    let rowClass = "row-on-time";
    let statusBadge = `<span class="badge-green kpi-badge">ON SCHEDULE</span>`;
    let variancePill = `<span class="variance-pill variance-zero">ON TIME</span>`;

    if (f.status === "DELAYED") {
      rowClass = "row-delayed";
      statusBadge = `<span class="badge-amber kpi-badge">DELAYED</span>`;
      variancePill = `<span class="variance-pill variance-delayed">+${diffMins}m</span>`;
    } else if (f.status === "CRITICAL") {
      rowClass = "row-critical";
      statusBadge = `<span class="badge-red kpi-badge">CRITICAL OVERLAP</span>`;
      variancePill = `<span class="variance-pill variance-critical">+${diffMins}m</span>`;
    }

    tr.className = rowClass;

    const airlineCode = getAirlineCode(f.flight_no);
    const airlineClass = `airline-${airlineCode.toLowerCase()}`;

    tr.innerHTML = `
      <td>
        <div class="flight-cell">
          <span class="airline-badge ${airlineClass}">${airlineCode}</span>
          <span class="flight-num">${f.flight_no}</span>
        </div>
      </td>
      <td><span class="airframe-text">${f.aircraft_id}</span></td>
      <td><span class="time-mono">${f.sched_time}</span></td>
      <td><span class="time-mono ${diffMins > 0 ? 'time-warning' : ''}">${f.est_time}</span></td>
      <td>${variancePill}</td>
      <td><span class="resource-chip">${gateName}</span></td>
      <td><span class="crew-name-text">${crewName}</span></td>
      <td>${statusBadge}</td>
      <td>
        <div class="quick-action-group">
          <button class="btn-mini-sim" data-id="${f.id}" data-mins="15" title="Simulate +15m delay">+15m</button>
          <button class="btn-mini-sim" data-id="${f.id}" data-mins="30" title="Simulate +30m delay">+30m</button>
          <button class="btn-mini-sim" data-id="${f.id}" data-mins="45" title="Simulate +45m delay">+45m</button>
        </div>
      </td>
    `;
    flightTableBody.appendChild(tr);
  });

  // Attach quick-simulation buttons
  document.querySelectorAll(".btn-mini-sim").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      const fid = btn.getAttribute("data-id");
      const mins = parseInt(btn.getAttribute("data-mins"));
      flightSelect.value = fid;
      delayMinutesInput.value = mins;
      triggerDelaySimulation(fid, mins);
    });
  });
}

function renderGatesGrid() {
  if (!gatesGrid) return;
  gatesGrid.innerHTML = "";

  state.gates.forEach(g => {
    const isOccupied = g.current_flight_id !== null;
    const card = document.createElement("div");
    card.className = `res-board-card ${isOccupied ? 'res-occupied' : ''}`;

    const currentFlight = isOccupied ? state.flights.find(f => f.id === g.current_flight_id) : null;
    const flightDisplay = currentFlight ? `${currentFlight.flight_no} (${currentFlight.sched_time})` : "Available / Turnaround Ready";

    card.innerHTML = `
      <div class="res-card-top">
        <span class="res-card-title">${g.name}</span>
        <span class="kpi-badge ${isOccupied ? 'badge-amber' : 'badge-green'} res-occupancy-status">
          ${isOccupied ? 'BAY OCCUPIED' : 'BAY FREE'}
        </span>
      </div>

      <div class="res-metric-cluster">
        <span class="res-flight-label">CURRENTLY ASSIGNED MOVEMENT</span>
        <span class="res-flight-val">${flightDisplay}</span>
      </div>

      <div class="res-progress-bar-bg">
        <div class="res-progress-fill" style="width: ${isOccupied ? '85%' : '0%'};"></div>
      </div>

      <div class="res-card-footer">
        <span>BAY ID: ${g.id}</span>
        <span>CLEAR TIMELINE: ${g.busy_until}</span>
      </div>
    `;
    gatesGrid.appendChild(card);
  });
}

function renderCrewGrid() {
  if (!crewGrid) return;
  crewGrid.innerHTML = "";

  state.crew.forEach(c => {
    const isAssigned = c.current_flight_id !== null;
    const card = document.createElement("div");
    card.className = `res-board-card ${isAssigned ? 'res-occupied' : ''}`;

    const currentFlight = isAssigned ? state.flights.find(f => f.id === c.current_flight_id) : null;
    const flightDisplay = currentFlight ? `${currentFlight.flight_no} (${currentFlight.sched_time})` : "Active On-Station Standby";

    card.innerHTML = `
      <div class="res-card-top">
        <span class="res-card-title">${c.name}</span>
        <span class="kpi-badge ${isAssigned ? 'badge-amber' : 'badge-cyan'} res-occupancy-status">
          ${isAssigned ? 'COMMITTED' : 'STANDBY READY'}
        </span>
      </div>

      <div class="res-metric-cluster">
        <span class="res-flight-label">ASSIGNED FLIGHT DUTY</span>
        <span class="res-flight-val">${flightDisplay}</span>
      </div>

      <div class="res-progress-bar-bg">
        <div class="res-progress-fill" style="width: ${isAssigned ? '70%' : '15%'}; background: ${isAssigned ? 'var(--amber)' : 'var(--cyan)'};"></div>
      </div>

      <div class="res-card-footer">
        <span>CREW CODE: ${c.id}</span>
        <span>DUTY WINDOW UNTIL: ${c.busy_until}</span>
      </div>
    `;
    crewGrid.appendChild(card);
  });
}

function renderAlertsDeck() {
  if (!state.activeConflicts || state.activeConflicts.length === 0) {
    aiResolutionDeck.classList.add("hidden");
    alertsList.innerHTML = "";
    return;
  }

  aiResolutionDeck.classList.remove("hidden");
  const count = state.activeConflicts.length;
  alertCountBadge.textContent = `${count} Active Issue${count > 1 ? 's' : ''}`;
  alertsList.innerHTML = "";

  state.activeConflicts.forEach((conf, idx) => {
    const suggestion = state.activeSuggestions[idx] || null;
    const isNoSolution = suggestion && suggestion.no_solution;

    const card = document.createElement("div");
    card.className = "conflict-remediation-card";
    card.innerHTML = `
      <div class="conflict-summary-row">
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <span class="conflict-type-pill ${conf.type === 'gate' ? 'type-gate' : 'type-crew'}">
            ${conf.type} CONTENTION
          </span>
          <span class="badge-red kpi-badge">ANOMALY DETECTED</span>
        </div>
        <span class="conflict-window-badge">
          CONFLICTION WINDOW: ${conf.overlap_start} - ${conf.overlap_end}
        </span>
      </div>

      <div class="conflict-narrative">
        <strong>Root Cause:</strong> ${conf.details}
      </div>

      ${suggestion ? `
        <div class="ai-recommendation-box ${isNoSolution ? 'no-solution' : ''}">
          <div class="rec-content-block">
            <span class="rec-label">
              ${isNoSolution ? 'OPTIMAL SOLUTION UNAVAILABLE: MANUAL ACTION REQUIRED' : 'OPTIMAL SOLUTION'}
            </span>
            <p class="rec-text">${suggestion.reason}</p>
          </div>

          <div class="rec-actions-block">
            ${!isNoSolution ? `
              <button class="btn-command btn-success-solid btn-approve-shift"
                data-flight="${suggestion.flight_id}"
                data-type="${suggestion.resource_type}"
                data-target="${suggestion.new_resource_id}">
                ✓ Approve ${suggestion.resource_type === 'gate' ? 'Gate Shift' : 'Crew Shift'}
              </button>
            ` : ''}
            <button class="btn-command btn-ghost btn-dismiss-alert" data-idx="${idx}">
              Dismiss
            </button>
          </div>
        </div>
      ` : ''}
    `;
    alertsList.appendChild(card);
  });

  // Attach Approve Shift listeners
  document.querySelectorAll(".btn-approve-shift").forEach(btn => {
    btn.addEventListener("click", () => {
      const flightId = btn.getAttribute("data-flight");
      const resourceType = btn.getAttribute("data-type");
      const targetId = btn.getAttribute("data-target");
      reassignResource(flightId, resourceType, targetId);
    });
  });

  // Attach Dismiss listeners
  document.querySelectorAll(".btn-dismiss-alert").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-idx"));
      state.activeConflicts.splice(idx, 1);
      state.activeSuggestions.splice(idx, 1);
      renderAlertsDeck();
    });
  });
}

// -------------------------------------------------------------
// Operations Handlers (Delay & Reassignment)
// -------------------------------------------------------------
async function triggerDelaySimulation(flightId, delayMinutes) {
  try {
    const res = await fetch(`${API_BASE}/delay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flight_id: flightId,
        delay_minutes: parseInt(delayMinutes)
      })
    });

    if (!res.ok) throw new Error("Delay simulation endpoint returned error.");
    const data = await res.json();

    if (data.conflicts && data.conflicts.length > 0) {
      state.activeConflicts = data.conflicts;
      state.activeSuggestions = data.suggestions && data.suggestions.length > 0
        ? data.suggestions
        : [data.suggestion];

      addAuditLog(
        `Delay simulated on ${data.flight.flight_no} (+${delayMinutes}m). Conflict triggered on ${data.conflicts[0].resource_name}.`,
        "ALERT",
        "badge-red"
      );
      showToast(`Conflict detected: ${data.conflicts[0].details}`, "danger");
    } else {
      state.activeConflicts = [];
      state.activeSuggestions = [];
      addAuditLog(
        `Flight ${data.flight.flight_no} delayed by ${delayMinutes}m (Est ${data.flight.est_time}). No turnaround conflict.`,
        "DELAY",
        "badge-amber"
      );
      showToast(`Flight ${data.flight.flight_no} updated to ${data.flight.est_time}. Schedule clear.`, "info");
    }

    await fetchAllData();
  } catch (err) {
    console.error("Delay error:", err);
    showToast("Failed to simulate delay on server.", "danger");
  }
}

async function reassignResource(flightId, resourceType, newResourceId) {
  try {
    const res = await fetch(`${API_BASE}/reassign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flight_id: flightId,
        resource_type: resourceType,
        new_resource_id: newResourceId
      })
    });

    if (!res.ok) throw new Error("Resource reassignment error.");
    const data = await res.json();

    addAuditLog(
      `Recommended shift executed: Flight ${data.flight.flight_no} reassigned to ${newResourceId}.`,
      "RESOLVED",
      "badge-green"
    );
    showToast(data.message, "success");

    state.activeConflicts = [];
    state.activeSuggestions = [];
    await fetchAllData();
  } catch (err) {
    console.error("Reassign error:", err);
    showToast("Failed to execute resource reassignment.", "danger");
  }
}

async function resetSystemDatabase() {
  try {
    const res = await fetch(`${API_BASE}/reset`, { method: "POST" });
    if (!res.ok) throw new Error("Reset endpoint error.");

    state.activeConflicts = [];
    state.activeSuggestions = [];
    addAuditLog("System state reset to calibrated seed database.", "RESET", "badge-cyan");
    showToast("AOCC state reset to seed data.", "success");
    await fetchAllData();
  } catch (err) {
    console.error("Reset error:", err);
    showToast("Failed to reset system database.", "danger");
  }
}

// -------------------------------------------------------------
// Utilities & Event Listeners
// -------------------------------------------------------------
function parseMinutes(timeStr) {
  const [h, m] = timeStr.split(":").map(Number);
  return h * 60 + m;
}

// Delay Form
delayForm.addEventListener("submit", e => {
  e.preventDefault();
  const fid = flightSelect.value;
  const mins = delayMinutesInput.value;
  if (!fid) {
    showToast("Select a flight to simulate delay.", "danger");
    return;
  }
  triggerDelaySimulation(fid, mins);
});

// Preset buttons
document.querySelectorAll(".preset-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".preset-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    delayMinutesInput.value = chip.getAttribute("data-mins");
  });
});

// Search & Clear
flightSearch.addEventListener("input", e => {
  state.searchTerm = e.target.value;
  clearSearchBtn.style.display = state.searchTerm ? "block" : "none";
  renderFlightTable();
});

clearSearchBtn.addEventListener("click", () => {
  state.searchTerm = "";
  flightSearch.value = "";
  clearSearchBtn.style.display = "none";
  renderFlightTable();
});

// Filter Pills
document.querySelectorAll(".filter-pill").forEach(pill => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    state.filterCategory = pill.getAttribute("data-filter");
    renderFlightTable();
  });
});

// Workspace Tabs
document.querySelectorAll(".tab-btn").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

    tab.classList.add("active");
    const targetId = tab.getAttribute("data-tab");
    document.getElementById(targetId).classList.add("active");

    const auxControls = document.getElementById("flightsAuxControls");
    if (auxControls) {
      auxControls.style.display = targetId === "tab-flights" ? "flex" : "none";
    }
  });
});

// Auto-sync Toggle
autoRefreshToggle.addEventListener("change", e => {
  state.autoRefresh = e.target.checked;
});

// Reset Button
btnResetDemo.addEventListener("click", resetSystemDatabase);

// 5-Second Background Polling
setInterval(() => {
  if (state.autoRefresh && document.activeElement !== flightSearch) {
    fetchAllData();
  }
}, 5000);

// Initialize
fetchAllData();
