const businessModels = {
  price_drivers_analysis: {
    label: "Price Drivers Analysis",
    description: "Use regional dispatch and trading datasets to explain price movements and market outcomes.",
    datasets: ["dispatch_price", "trading_regionsum", "dispatch_regionsum"]
  },
  demand_net_demand_analysis: {
    label: "Demand & Net Demand Analysis",
    description: "Focus on operational demand, regional summaries, and rooftop PV to study net demand.",
    datasets: ["dispatch_regionsum", "trading_regionsum", "rooftop_pv_actual"]
  },
  bess_trading_analysis: {
    label: "BESS Trading Analysis",
    description: "Combine prices, SCADA, and constraints to study battery dispatch and trading behaviour.",
    datasets: ["dispatch_price", "dispatch_regionsum", "trading_regionsum", "dispatch_unit_scada", "dispatch_constraints"]
  },
  network_constraints_analysis: {
    label: "Network Constraints Analysis",
    description: "Study regional prices, dispatch constraints, and related network behaviour.",
    datasets: ["dispatch_price", "dispatch_constraints"]
  },
  renewable_integration_analysis: {
    label: "Renewable Integration Analysis",
    description: "Use demand, regional summary, and rooftop PV data to study renewable integration.",
    datasets: ["dispatch_regionsum", "trading_regionsum", "rooftop_pv_actual", "dispatch_unit_scada"]
  },
  custom_dataset_selection: {
    label: "Custom Dataset Selection",
    description: "Manually choose only the datasets you want to demonstrate.",
    datasets: []
  }
};

const datasets = [
  { name: "dispatch_price", title: "Dispatch Price", description: "Regional dispatch interval price outcomes.", table: "raw.dispatch_price", enabled: true },
  { name: "dispatch_regionsum", title: "Dispatch Region Summary", description: "Five-minute regional demand and dispatch summary.", table: "raw.dispatch_regionsum", enabled: true },
  { name: "trading_price", title: "Trading Price", description: "Trading interval regional price outcomes.", table: "raw.trading_price", enabled: true },
  { name: "trading_regionsum", title: "Trading Region Summary", description: "Trading interval demand and summary records.", table: "raw.trading_regionsum", enabled: true },
  { name: "dispatch_unit_scada", title: "Dispatch Unit SCADA", description: "Unit-level SCADA and telemetry values.", table: "raw.dispatch_unit_scada", enabled: true },
  { name: "dispatch_constraints", title: "Dispatch Constraints", description: "Constraint outcomes and marginal values.", table: "raw.dispatch_constraints", enabled: true },
  { name: "rooftop_pv_actual", title: "Rooftop PV Actual", description: "Actual rooftop PV estimates.", table: "raw.rooftop_pv_actual", enabled: true }
];

function byId(id) {
  return document.getElementById(id);
}

function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function setRange(start, end) {
  byId("startDate").value = formatDate(start);
  byId("endDate").value = formatDate(end);
  byId("yearSelect").value = String(start.getFullYear());
  byId("monthSelect").value = String(start.getMonth() + 1).padStart(2, "0");
}

function applyRange(type) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const start = new Date(today);
  const end = new Date(today);

  if (type === "today") setRange(start, end);
  if (type === "yesterday") {
    start.setDate(start.getDate() - 1);
    end.setDate(end.getDate() - 1);
    setRange(start, end);
  }
  if (type === "week") {
    const day = today.getDay();
    const mondayShift = day === 0 ? 6 : day - 1;
    start.setDate(today.getDate() - mondayShift);
    setRange(start, end);
  }
  if (type === "7days") {
    start.setDate(today.getDate() - 6);
    setRange(start, end);
  }
  if (type === "month") {
    start.setDate(1);
    setRange(start, end);
  }
}

function populateYearMonth() {
  const yearSelect = byId("yearSelect");
  const monthSelect = byId("monthSelect");
  const now = new Date();
  yearSelect.innerHTML = "";
  monthSelect.innerHTML = "";

  for (let year = now.getFullYear() - 3; year <= now.getFullYear() + 1; year += 1) {
    yearSelect.innerHTML += `<option value="${year}">${year}</option>`;
  }

  const months = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
  ];
  months.forEach((month, i) => {
    const value = String(i + 1).padStart(2, "0");
    monthSelect.innerHTML += `<option value="${value}">${month}</option>`;
  });
}

function populateBusinessModels() {
  const select = byId("businessModel");
  select.innerHTML = "";
  Object.entries(businessModels).forEach(([key, model]) => {
    select.innerHTML += `<option value="${key}">${model.label}</option>`;
  });
  select.value = "price_drivers_analysis";
}

function renderDatasets() {
  const grid = byId("datasetGrid");
  grid.innerHTML = "";
  datasets.forEach((dataset) => {
    grid.innerHTML += `
      <label class="dataset-card">
        <input type="checkbox" name="dataset" value="${dataset.name}">
        <div>
          <h4>${dataset.title}</h4>
          <div class="muted">${dataset.description}</div>
          <div class="pill-row top-gap">
            <span class="pill">${dataset.table}</span>
            <span class="pill">${dataset.enabled ? "Enabled" : "Advanced"}</span>
          </div>
        </div>
      </label>
    `;
  });
}

function tickDatasets(names) {
  document.querySelectorAll('input[name="dataset"]').forEach((node) => {
    node.checked = names.includes(node.value);
  });
}

function enabledCore() {
  return datasets.filter((d) => d.enabled).map((d) => d.name);
}

function updateBusinessModel() {
  const selected = byId("businessModel").value;
  const model = businessModels[selected];
  if (!model) return;

  byId("modelDescription").textContent = model.description;
  if (selected === "custom_dataset_selection") {
    byId("modelDatasets").textContent = "Custom mode is active. Manually choose any demo datasets.";
    return;
  }

  const labels = model.datasets
    .map((name) => datasets.find((d) => d.name === name)?.title)
    .filter(Boolean);

  byId("modelDatasets").textContent = `Recommended datasets: ${labels.join(", ")}.`;
  tickDatasets(model.datasets);
}

function syncFromYearMonth() {
  const year = byId("yearSelect").value;
  const month = byId("monthSelect").value;
  if (!year || !month) return;
  const start = new Date(Number(year), Number(month) - 1, 1);
  const end = new Date(Number(year), Number(month), 0);
  setRange(start, end);
}

function showModal() {
  byId("contactModal").classList.add("show");
}

function hideModal() {
  byId("contactModal").classList.remove("show");
}

function actionPopup(actionName) {
  showModal();
  const card = document.querySelector(".modal-card p");
  card.textContent = `${actionName} is available in the live backend-connected version. Please contact me directly using the options below for a full ETL walkthrough and demo access.`;
}

function clearLogs() {
  byId("logPanel").textContent = `[Demo mode]
Logs cleared.
For a live ETL run, please contact me directly.`;
}

function initTheme() {
  const stored = localStorage.getItem("demo-theme") || "light";
  document.body.classList.toggle("dark", stored === "dark");
  byId("themeToggle").checked = stored === "dark";
  byId("themeLabel").textContent = stored === "dark" ? "Light mode" : "Dark mode";

  byId("themeToggle").addEventListener("change", (e) => {
    const theme = e.target.checked ? "dark" : "light";
    document.body.classList.toggle("dark", theme === "dark");
    byId("themeLabel").textContent = theme === "dark" ? "Light mode" : "Dark mode";
    localStorage.setItem("demo-theme", theme);
  });
}

function init() {
  initTheme();
  populateYearMonth();
  populateBusinessModels();
  renderDatasets();
  applyRange("7days");
  updateBusinessModel();

  document.querySelectorAll("[data-range]").forEach((btn) => {
    btn.addEventListener("click", () => applyRange(btn.dataset.range));
  });

  byId("yearSelect").addEventListener("change", syncFromYearMonth);
  byId("monthSelect").addEventListener("change", syncFromYearMonth);
  byId("businessModel").addEventListener("change", updateBusinessModel);

  byId("useRecommended").addEventListener("click", () => {
    const model = businessModels[byId("businessModel").value];
    tickDatasets(model?.datasets || []);
  });

  byId("useCore").addEventListener("click", () => tickDatasets(enabledCore()));
  byId("clearSelection").addEventListener("click", () => tickDatasets([]));

  byId("runPipelineBtn").addEventListener("click", () => actionPopup("Run Pipeline"));
  byId("checkExistingBtn").addEventListener("click", () => actionPopup("Check Existing Data"));
  byId("testDbBtn").addEventListener("click", () => actionPopup("Test Database Connection"));
  byId("clearLogsBtn").addEventListener("click", clearLogs);

  byId("closeModalBtn").addEventListener("click", hideModal);
}

init();
