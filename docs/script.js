const businessModels = {
  price_drivers_analysis: {
    label: "Price Drivers Analysis",
    description: "Use regional dispatch and trading datasets to explain price movements and market outcomes.",
    datasets: ["dispatch_price", "trading_regionsum", "dispatch_regionsum"],
    theme: "price",
    badges: ["Fast run", "Core tables", "Market pulse"]
  },
  demand_net_demand_analysis: {
    label: "Demand & Net Demand Analysis",
    description: "Focus on operational demand, regional summaries, and rooftop PV to study net demand.",
    datasets: ["dispatch_regionsum", "trading_regionsum", "rooftop_pv_actual"],
    theme: "renewables",
    badges: ["Demand focus", "Net demand", "Regional view"]
  },
  bess_trading_analysis: {
    label: "BESS Trading Analysis",
    description: "Combine prices, SCADA, and constraints to study battery dispatch and trading behaviour.",
    datasets: ["dispatch_price", "dispatch_regionsum", "trading_regionsum", "dispatch_unit_scada", "dispatch_constraints"],
    theme: "price",
    badges: ["Battery lens", "Trading view", "Dispatch context"]
  },
  network_constraints_analysis: {
    label: "Network Constraints Analysis",
    description: "Study regional prices, dispatch constraints, and related network behaviour.",
    datasets: ["dispatch_price", "dispatch_constraints"],
    theme: "constraints",
    badges: ["Operator use", "Constraint view", "Grid pathways"]
  },
  renewable_integration_analysis: {
    label: "Renewable Integration Analysis",
    description: "Use demand, regional summary, and rooftop PV data to study renewable integration.",
    datasets: ["dispatch_regionsum", "trading_regionsum", "rooftop_pv_actual", "dispatch_unit_scada"],
    theme: "renewables",
    badges: ["Recommended", "Renewables", "Power BI friendly"]
  },
  custom_dataset_selection: {
    label: "Custom Dataset Selection",
    description: "Manually choose only the datasets you want to demonstrate.",
    datasets: [],
    theme: "constraints",
    badges: ["Custom selection", "Manual bundle", "Flexible run"]
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

const progressStages = [
  "Connecting to database",
  "Reading dataset config",
  "Checking duplicate data",
  "Scanning NEMWeb directories",
  "Downloading files",
  "Extracting ZIP files",
  "Parsing AEMO C/I/D records",
  "Cleaning data",
  "Validating data",
  "Creating schemas/tables",
  "Loading into PostgreSQL",
  "Completed"
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

function formatDisplayDate(value) {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
}

function setRange(start, end) {
  byId("startDate").value = formatDate(start);
  byId("endDate").value = formatDate(end);
  byId("yearSelect").value = String(start.getFullYear());
  byId("monthSelect").value = String(start.getMonth() + 1).padStart(2, "0");
  updateSummaryBar();
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
  if (type === "current_week") {
    const day = today.getDay();
    const mondayShift = day === 0 ? 6 : day - 1;
    start.setDate(today.getDate() - mondayShift);
    setRange(start, end);
  }
  if (type === "last_7_days") {
    start.setDate(today.getDate() - 6);
    setRange(start, end);
  }
  if (type === "current_month") {
    start.setDate(1);
    setRange(start, end);
  }

  document.querySelectorAll(".compact-slicer").forEach((button) => {
    button.classList.toggle("active", button.dataset.range === type);
  });
}

function populateYearMonth() {
  const yearSelect = byId("yearSelect");
  const monthSelect = byId("monthSelect");
  const now = new Date();
  yearSelect.innerHTML = `<option value="">Select year</option>`;
  monthSelect.innerHTML = `<option value="">Select month</option>`;

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
  select.value = "renewable_integration_analysis";
}

function renderDatasets() {
  const grid = byId("datasetGrid");
  grid.innerHTML = "";
  datasets.forEach((dataset) => {
    grid.innerHTML += `
      <label class="dataset-card ${dataset.enabled ? "recommended" : ""}">
        <div class="dataset-toggle">
          <input type="checkbox" name="dataset" value="${dataset.name}">
          <div>
            <h3>${dataset.title}</h3>
            <p class="muted">${dataset.description}</p>
            <div class="pill-row top-gap">
              <span class="mini-chip">${dataset.table}</span>
              <span class="mini-chip">${dataset.enabled ? "Enabled" : "Advanced"}</span>
            </div>
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
  updateDatasetSummary();
  updateSummaryBar();
}

function selectedDatasets() {
  return Array.from(document.querySelectorAll('input[name="dataset"]:checked')).map((node) => node.value);
}

function enabledCore() {
  return datasets.filter((d) => d.enabled).map((d) => d.name);
}

function updateDatasetSummary() {
  const selected = selectedDatasets();
  const labels = selected
    .map((name) => datasets.find((d) => d.name === name)?.title)
    .filter(Boolean);

  byId("selectedDatasetSummary").textContent = selected.length
    ? `${selected.length} selected: ${labels.join(", ")}`
    : "Select datasets to see the live count and current bundle summary here.";

  byId("summarySelectedDatasets").textContent = `${selected.length} selected`;
}

function updateBusinessModel() {
  const selected = byId("businessModel").value;
  const model = businessModels[selected];
  if (!model) return;

  byId("summaryBusinessModel").textContent = model.label;
  byId("businessModelOverviewTitle").textContent = model.label;
  byId("businessModelDescription").textContent = model.description;

  const overview = byId("businessModelOverview");
  overview.className = `model-overview-shell theme-${model.theme}`;

  const badgeRow = byId("businessModelBadgeRow");
  badgeRow.innerHTML = model.badges.map((badge) => `<span class="model-theme-chip">${badge}</span>`).join("");

  if (selected === "custom_dataset_selection") {
    byId("businessModelDatasets").textContent = "Custom mode is active. Manually choose any demo datasets.";
    return;
  }

  const labels = model.datasets
    .map((name) => datasets.find((d) => d.name === name)?.title)
    .filter(Boolean);

  byId("businessModelDatasets").textContent = `Recommended datasets: ${labels.join(", ")}.`;
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

function updateSummaryBar() {
  const start = byId("startDate").value;
  const end = byId("endDate").value;
  const selected = selectedDatasets();

  byId("summaryDateWindow").textContent = start && end
    ? `${formatDisplayDate(start)} to ${formatDisplayDate(end)}`
    : "Not set";

  byId("summarySelectedDatasets").textContent = `${selected.length} selected`;
  byId("summaryExpectedRuntime").textContent =
    selected.length > 5 ? "Moderate archive pull" :
    selected.length > 0 ? "Fast run" :
    "Pending";

  byId("summaryReadiness").textContent =
    start && end && selected.length > 0 ? "Ready" : "Waiting for input";
}

function renderProgressStages(activeIndex = 0) {
  const container = byId("progressStageList");
  container.innerHTML = "";

  progressStages.forEach((stage, index) => {
    const oneBased = index + 1;
    let stateClass = "pending";
    let stateText = "Pending";

    if (activeIndex > oneBased) {
      stateClass = "done";
      stateText = "Done";
    } else if (activeIndex === oneBased) {
      stateClass = "live";
      stateText = "Active";
    }

    container.innerHTML += `
      <div class="status-stage">
        <span>${oneBased}. ${stage}</span>
        <span class="stage-state ${stateClass}">${stateText}</span>
      </div>
    `;
  });
}

function showModal() {
  byId("contactModal").classList.add("show");
}

function hideModal() {
  byId("contactModal").classList.remove("show");
}

function actionPopup(actionName) {
  byId("currentStatusPill").textContent = "Demo";
  byId("runHeadline").textContent = `${actionName} locked`;
  byId("statusMessage").textContent = `${actionName} is available in the live backend-connected version. Please contact me directly using the options below for a full ETL walkthrough and demo access.`;
  showModal();
}

function clearLogs() {
  byId("logPanel").textContent = `[Demo mode]
Logs cleared.
For a live ETL run, please contact me directly.`;
}

function initTheme() {
  const stored = localStorage.getItem("demo-theme") || "dark";
  document.body.classList.toggle("low-energy", stored === "low");
  byId("accentGlow").checked = stored !== "low";

  byId("accentGlow").addEventListener("change", (e) => {
    const low = !e.target.checked;
    document.body.classList.toggle("low-energy", low);
    localStorage.setItem("demo-theme", low ? "low" : "dark");
  });
}

function initTabs() {
  const tabs = document.querySelectorAll(".review-tab");
  const panels = document.querySelectorAll(".review-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach((item) => item.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));
      tab.classList.add("active");
      byId(target).classList.add("active");
    });
  });
}

function init() {
  initTheme();
  initTabs();
  populateYearMonth();
  populateBusinessModels();
  renderDatasets();
  renderProgressStages(0);
  applyRange("last_7_days");
  updateBusinessModel();
  updateSummaryBar();

  document.querySelectorAll("[data-range]").forEach((btn) => {
    btn.addEventListener("click", () => applyRange(btn.dataset.range));
  });

  byId("yearSelect").addEventListener("change", syncFromYearMonth);
  byId("monthSelect").addEventListener("change", syncFromYearMonth);
  byId("startDate").addEventListener("change", updateSummaryBar);
  byId("endDate").addEventListener("change", updateSummaryBar);
  byId("businessModel").addEventListener("change", updateBusinessModel);

  byId("useRecommendedButton").addEventListener("click", () => {
    const model = businessModels[byId("businessModel").value];
    tickDatasets(model?.datasets || []);
  });

  byId("useEnabledButton").addEventListener("click", () => tickDatasets(enabledCore()));
  byId("clearSelectionButton").addEventListener("click", () => tickDatasets([]));

  document.querySelectorAll('input[name="dataset"]').forEach((node) => {
    node.addEventListener("change", updateDatasetSummary);
    node.addEventListener("change", updateSummaryBar);
  });

  byId("runButton").addEventListener("click", () => actionPopup("Run Pipeline"));
  byId("checkExistingButton").addEventListener("click", () => actionPopup("Check Existing Data"));
  byId("testDbButton").addEventListener("click", () => actionPopup("Test Database Connection"));
  byId("clearLogsButton").addEventListener("click", clearLogs);
  byId("closeModalBtn").addEventListener("click", hideModal);
}

init();
