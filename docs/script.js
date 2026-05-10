const BUSINESS_MODELS = {
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

const DATASETS = {
  dispatch_price: {
    display_name: "Dispatch Price",
    description: "Regional dispatch interval price outcomes.",
    target_table: "raw.dispatch_price",
    enabled: true,
    category: "Core",
    group: "Prices"
  },
  dispatch_regionsum: {
    display_name: "Dispatch Region Summary",
    description: "Five-minute regional demand and dispatch summary.",
    target_table: "raw.dispatch_regionsum",
    enabled: true,
    category: "Core",
    group: "Demand"
  },
  trading_price: {
    display_name: "Trading Price",
    description: "Trading interval regional price outcomes.",
    target_table: "raw.trading_price",
    enabled: true,
    category: "Core",
    group: "Prices"
  },
  trading_regionsum: {
    display_name: "Trading Region Summary",
    description: "Trading interval demand and summary records.",
    target_table: "raw.trading_regionsum",
    enabled: true,
    category: "Core",
    group: "Demand"
  },
  dispatch_unit_scada: {
    display_name: "Dispatch Unit SCADA",
    description: "Unit-level SCADA and telemetry values.",
    target_table: "raw.dispatch_unit_scada",
    enabled: true,
    category: "Core",
    group: "Telemetry"
  },
  dispatch_constraints: {
    display_name: "Dispatch Constraints",
    description: "Constraint outcomes and marginal values.",
    target_table: "raw.dispatch_constraints",
    enabled: true,
    category: "Core",
    group: "Constraints"
  },
  rooftop_pv_actual: {
    display_name: "Rooftop PV Actual",
    description: "Actual rooftop PV estimates.",
    target_table: "raw.rooftop_pv_actual",
    enabled: true,
    category: "Core",
    group: "Renewables"
  }
};

const PROGRESS_STAGES = [
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

let runTimer = null;
let stageTimer = null;
let runStartTime = null;

function byId(id) {
  return document.getElementById(id);
}

function showMessage(text, isError = false) {
  const box = byId("formMessage");
  box.textContent = text;
  box.className = `form-message${isError ? " error" : ""}`;
  box.style.display = "block";
}

function hideMessage() {
  const box = byId("formMessage");
  box.textContent = "";
  box.className = "form-message";
  box.style.display = "none";
}

function formatDate(dateValue) {
  const year = dateValue.getFullYear();
  const month = String(dateValue.getMonth() + 1).padStart(2, "0");
  const day = String(dateValue.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDisplayDate(dateString) {
  if (!dateString) return "Not set";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  return date.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
}

function setDateRange(startDate, endDate) {
  byId("startDate").value = formatDate(startDate);
  byId("endDate").value = formatDate(endDate);
  byId("yearSelect").value = String(startDate.getFullYear());
  byId("monthSelect").value = String(startDate.getMonth() + 1).padStart(2, "0");
  updateSummaryBar();
}

function applyQuickRange(rangeName) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(today);
  const start = new Date(today);

  if (rangeName === "today") {
    setDateRange(start, end);
  } else if (rangeName === "yesterday") {
    start.setDate(start.getDate() - 1);
    end.setDate(end.getDate() - 1);
    setDateRange(start, end);
  } else if (rangeName === "current_week") {
    const dayIndex = today.getDay();
    const mondayShift = dayIndex === 0 ? 6 : dayIndex - 1;
    start.setDate(today.getDate() - mondayShift);
    setDateRange(start, end);
  } else if (rangeName === "last_7_days") {
    start.setDate(today.getDate() - 6);
    setDateRange(start, end);
  } else if (rangeName === "current_month") {
    start.setDate(1);
    setDateRange(start, end);
  }

  document.querySelectorAll(".compact-slicer").forEach((button) => {
    button.classList.toggle("active", button.dataset.range === rangeName);
  });
}

function populateYearMonthControls() {
  const now = new Date();
  const yearSelect = byId("yearSelect");
  const monthSelect = byId("monthSelect");
  yearSelect.innerHTML = `<option value="">Select year</option>`;
  monthSelect.innerHTML = `<option value="">Select month</option>`;

  for (let year = now.getFullYear() - 5; year <= now.getFullYear() + 1; year += 1) {
    yearSelect.innerHTML += `<option value="${year}">${year}</option>`;
  }

  [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ].forEach((name, index) => {
    const monthValue = String(index + 1).padStart(2, "0");
    monthSelect.innerHTML += `<option value="${monthValue}">${name}</option>`;
  });
}

function updateDateRangeFromYearMonth() {
  const year = byId("yearSelect").value;
  const month = byId("monthSelect").value;
  if (!year || !month) return;
  const start = new Date(Number(year), Number(month) - 1, 1);
  const end = new Date(Number(year), Number(month), 0);
  setDateRange(start, end);
}

function populateBusinessModels() {
  const select = byId("businessModel");
  select.innerHTML = "";
  Object.entries(BUSINESS_MODELS).forEach(([key, model]) => {
    select.innerHTML += `<option value="${key}">${model.label}</option>`;
  });
  select.value = "renewable_integration_analysis";
}

function enabledDatasetNames() {
  return Object.entries(DATASETS)
    .filter(([, dataset]) => dataset.enabled)
    .map(([name]) => name);
}

function selectedDatasets() {
  return Array.from(document.querySelectorAll('input[name="dataset"]:checked')).map((node) => node.value);
}

function recommendedDatasetsForCurrentModel() {
  const selected = byId("businessModel").value;
  const model = BUSINESS_MODELS[selected];
  return model ? model.datasets.slice() : [];
}

function renderDatasets() {
  const grid = byId("datasetGrid");
  grid.innerHTML = "";

  Object.entries(DATASETS).forEach(([datasetName, dataset]) => {
    grid.innerHTML += `
      <label class="dataset-card ${dataset.enabled ? "recommended" : ""}">
        <div class="dataset-toggle">
          <input type="checkbox" name="dataset" value="${datasetName}">
          <div>
            <h3>${dataset.display_name}</h3>
            <p class="muted">${dataset.description}</p>
            <div class="pill-row top-gap">
              <span class="mini-chip">${dataset.target_table}</span>
              <span class="mini-chip">${dataset.category}</span>
              <span class="mini-chip">${dataset.group}</span>
            </div>
          </div>
        </div>
      </label>
    `;
  });
}

function tickDatasets(datasetNames) {
  document.querySelectorAll('input[name="dataset"]').forEach((node) => {
    node.checked = datasetNames.includes(node.value);
  });
  updateDatasetSummary();
  updateSummaryBar();
}

function updateDatasetSummary() {
  const selected = selectedDatasets();
  const labels = selected.map((datasetName) => DATASETS[datasetName]?.display_name).filter(Boolean);
  byId("selectedDatasetSummary").textContent = selected.length
    ? `${selected.length} selected: ${labels.join(", ")}`
    : "Select datasets to see the live count and current bundle summary here.";
  byId("summarySelectedDatasets").textContent = `${selected.length} selected`;
}

function updateBusinessModelSelection() {
  const selected = byId("businessModel").value;
  const model = BUSINESS_MODELS[selected];
  if (!model) return;

  const overview = byId("businessModelOverview");
  const badgeRow = byId("businessModelBadgeRow");

  overview.className = `model-overview-shell theme-${model.theme}`;
  byId("businessModelOverviewTitle").textContent = model.label;
  byId("businessModelDescription").textContent = model.description;
  badgeRow.innerHTML = model.badges.map((badge) => `<span class="model-theme-chip">${badge}</span>`).join("");

  if (selected === "custom_dataset_selection") {
    byId("businessModelDatasets").textContent = "Custom mode is active. Manually tick only the datasets you want to include in the demo bundle.";
    updateSummaryBar();
    return;
  }

  const recommended = recommendedDatasetsForCurrentModel();
  const recommendedLabels = recommended.map((datasetName) => DATASETS[datasetName]?.display_name).filter(Boolean);
  byId("businessModelDatasets").textContent = `Recommended and auto-selected: ${recommendedLabels.join(", ")}.`;
  tickDatasets(recommended);
  updateSummaryBar();
}

function updateSummaryBar() {
  const start = byId("startDate").value;
  const end = byId("endDate").value;
  const selected = selectedDatasets();
  const modelValue = byId("businessModel").value;
  const model = BUSINESS_MODELS[modelValue];

  byId("summaryDateWindow").textContent = start && end ? `${formatDisplayDate(start)} to ${formatDisplayDate(end)}` : "Not set";
  byId("summaryBusinessModel").textContent = model?.label || "Custom";
  byId("summarySelectedDatasets").textContent = `${selected.length} selected`;
  byId("summaryExpectedRuntime").textContent = selected.length > 5 ? "Moderate archive pull" : selected.length > 0 ? "Fast run" : "Pending";
  byId("summaryReadiness").textContent = selected.length > 0 && start && end ? "Ready" : "Waiting for input";
}

function renderProgressStages(activeIndex = 0) {
  const container = byId("progressStageList");
  container.innerHTML = "";

  PROGRESS_STAGES.forEach((stage, index) => {
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

function setCurrentStatus(status, message, elapsedSeconds) {
  const lowered = String(status || "Idle").toLowerCase();
  byId("currentStatusPill").textContent = status;
  byId("runtimeValue").textContent = `${String(Math.floor((elapsedSeconds || 0) / 60)).padStart(2, "0")}:${String((elapsedSeconds || 0) % 60).padStart(2, "0")}`;
  byId("statusMessage").textContent = message || "";
  byId("runHeadline").textContent =
    lowered === "processing" ? "Pipeline running" :
    lowered === "completed" ? "Pipeline completed" :
    lowered === "failed" ? "Pipeline failed" :
    "Pipeline ready";
  byId("processingRow").style.display = lowered === "processing" ? "block" : "none";
  byId("runButton").disabled = lowered === "processing";
}

function renderSummaryCards(statusText, rowsLoaded = 0) {
  const start = byId("startDate").value;
  const end = byId("endDate").value;
  const modelValue = byId("businessModel").value;
  const model = BUSINESS_MODELS[modelValue];

  byId("summaryCards").innerHTML = `
    <div class="check-score"><strong>${statusText}</strong><span class="muted">Current status</span></div>
    <div class="check-score"><strong>${start && end ? `${formatDisplayDate(start)} to ${formatDisplayDate(end)}` : "N/A"}</strong><span class="muted">Date range</span></div>
    <div class="check-score"><strong>${model?.label || "Custom"}</strong><span class="muted">Business model</span></div>
    <div class="check-score"><strong>${rowsLoaded}</strong><span class="muted">Rows loaded</span></div>
  `;
}

function renderExistingData(results) {
  const panel = byId("existingDataPanel");
  if (!results || results.length === 0) {
    panel.innerHTML = `<p class="muted">No duplicate check result available for the current selection.</p>`;
    return;
  }

  panel.innerHTML = results.map((row) => `
    <div class="check-score" style="margin-top:12px;">
      <strong>${row.display_name}</strong>
      <span class="muted">${row.status_message}</span>
      <div class="pill-row" style="margin-top:10px;">
        <span class="mini-chip">${row.target_table}</span>
        <span class="mini-chip">Rows: ${row.rows_in_range}</span>
        <span class="mini-chip">Min: ${row.min_datetime}</span>
        <span class="mini-chip">Max: ${row.max_datetime}</span>
      </div>
    </div>
  `).join("");
}

function renderResultCards(results) {
  const resultCards = byId("resultCards");
  if (!results.length) {
    resultCards.innerHTML = `
      <div class="result-card warn">
        <h3>No dataset results</h3>
        <p class="muted" style="margin-top:14px;">No dataset-level results were returned for this run.</p>
      </div>
    `;
    return;
  }

  resultCards.innerHTML = results.map((result) => {
    let cardClass = "warn";
    if (result.status === "success") cardClass = "good";
    if (result.status === "failed") cardClass = "fail";

    return `
      <div class="result-card ${cardClass}">
        <h3>${result.display_name}</h3>
        <div class="pill-row">
          <span class="mini-chip">Files: ${result.files_detected}</span>
          <span class="mini-chip">Rows loaded: ${result.rows_loaded}</span>
          <span class="mini-chip">Status: ${result.status}</span>
        </div>
        <p class="muted" style="margin-top:14px;">${result.message}</p>
      </div>
    `;
  }).join("");
}

function resetRunView() {
  renderSummaryCards("Processing", 0);
  byId("resultCards").innerHTML = `
    <div class="result-card warn">
      <h3>Pipeline started</h3>
      <p class="muted" style="margin-top:14px;">Fresh dataset outcomes will appear here during this demo run.</p>
    </div>
  `;
  byId("logPanel").textContent = "Starting a fresh demo pipeline run...";
}

function appendLog(line) {
  const panel = byId("logPanel");
  const existing = panel.textContent.trim();
  panel.textContent = existing ? `${existing}\n${line}` : line;
  panel.scrollTop = panel.scrollHeight;
}

function demoLogPrefix(level = "INFO") {
  const now = new Date();
  const stamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  return `${stamp} | ${level} | nemweb_pipeline |`;
}

function buildDemoExistingData() {
  return selectedDatasets().map((datasetName, index) => {
    const dataset = DATASETS[datasetName];
    return {
      display_name: dataset.display_name,
      target_table: dataset.target_table,
      rows_in_range: index % 2 === 0 ? 0 : 1440,
      min_datetime: index % 2 === 0 ? "N/A" : byId("startDate").value,
      max_datetime: index % 2 === 0 ? "N/A" : byId("endDate").value,
      status_message: index % 2 === 0
        ? "No existing rows were found for the selected period."
        : "Existing rows were found in the selected period. A live run would avoid duplicate loads."
    };
  });
}

function buildDemoResults() {
  return selectedDatasets().map((datasetName, index) => {
    const dataset = DATASETS[datasetName];
    const fileCount = 24 + (index + 1) * 17;
    const rowCount = fileCount * (datasetName === "dispatch_unit_scada" ? 228 : datasetName === "dispatch_constraints" ? 176 : 12);
    return {
      display_name: dataset.display_name,
      status: "success",
      files_detected: fileCount,
      rows_loaded: rowCount,
      message: `Demo run completed successfully for ${dataset.display_name}. The live backend version would write the cleaned output to ${dataset.target_table}.`
    };
  });
}

function stopDemoRun() {
  if (runTimer) clearInterval(runTimer);
  if (stageTimer) clearTimeout(stageTimer);
  runTimer = null;
  stageTimer = null;
  runStartTime = null;
}

function runPipeline() {
  hideMessage();

  const start = byId("startDate").value;
  const end = byId("endDate").value;
  const chosenDatasets = selectedDatasets();

  if (!start || !end) {
    showMessage("Select a start date and end date first.", true);
    return;
  }

  if (chosenDatasets.length === 0) {
    showMessage("Select at least one dataset before running the demo pipeline.", true);
    return;
  }

  stopDemoRun();
  resetRunView();
  renderProgressStages(1);
  setCurrentStatus("Processing", "Demo run is progressing through the enhanced dashboard flow.", 0);
  showMessage("Demo pipeline started. This static version simulates the live workflow and status surfaces.");

  const results = buildDemoResults();
  const totalRows = results.reduce((sum, row) => sum + row.rows_loaded, 0);
  let activeStage = 1;

  appendLog(`${demoLogPrefix()} Initialising enhanced static demo run`);
  appendLog(`${demoLogPrefix()} Selected datasets: ${chosenDatasets.map((name) => DATASETS[name].display_name).join(", ")}`);

  runStartTime = Date.now();
  runTimer = setInterval(() => {
    const elapsedSeconds = Math.floor((Date.now() - runStartTime) / 1000);
    setCurrentStatus("Processing", "Demo run is progressing through the enhanced dashboard flow.", elapsedSeconds);
  }, 1000);

  function advanceStage() {
    renderProgressStages(activeStage);
    appendLog(`${demoLogPrefix()} ${PROGRESS_STAGES[activeStage - 1]}`);

    if (activeStage === 3) {
      renderExistingData(buildDemoExistingData());
    }

    if (activeStage >= PROGRESS_STAGES.length) {
      stopDemoRun();
      renderProgressStages(PROGRESS_STAGES.length);
      setCurrentStatus("Completed", "Demo run completed. Contact Vivek for the full backend-connected walkthrough.", Math.floor((Date.now() - runStartTime) / 1000));
      renderSummaryCards("Completed", totalRows);
      renderResultCards(results);
      appendLog(`${demoLogPrefix()} Final dataset summary for this run:`);
      results.forEach((result) => {
        appendLog(`${demoLogPrefix()} - ${result.display_name} | status=${result.status} | rows_loaded=${result.rows_loaded} | files_detected=${result.files_detected}`);
      });
      appendLog(`${demoLogPrefix()} Completed status: Completed`);
      showMessage("Demo pipeline completed. The full Flask + PostgreSQL ETL version is available in the live walkthrough.");
      return;
    }

    activeStage += 1;
    stageTimer = setTimeout(advanceStage, 650);
  }

  stageTimer = setTimeout(advanceStage, 450);
}

function checkExistingData() {
  hideMessage();
  const start = byId("startDate").value;
  const end = byId("endDate").value;

  if (!start || !end) {
    showMessage("Select a start date and end date first.", true);
    return;
  }

  const results = buildDemoExistingData();
  renderExistingData(results);
  appendLog(`${demoLogPrefix()} Existing data demo check completed for ${results.length} dataset(s)`);
  showMessage("Existing data demo check completed.");
}

function testDbConnection() {
  byId("dbConnectionStatus").textContent = "Demo mode: connection checks are simulated here. The live Flask dashboard performs the real PostgreSQL health check.";
  appendLog(`${demoLogPrefix()} Database readiness check simulated successfully`);
  showMessage("Database readiness demo check completed.");
}

function clearLogs() {
  stopDemoRun();
  byId("logPanel").textContent = "Logs cleared. Run the demo pipeline again to repopulate the enhanced signal view.";
  byId("existingDataPanel").innerHTML = `<p class="muted">No duplicate check run yet. Use Check Existing Data to populate this panel.</p>`;
  byId("resultCards").innerHTML = `
    <div class="result-card warn">
      <h3>No pipeline run yet</h3>
      <p class="muted" style="margin-top:14px;">Use the demo actions to preview how results, statuses, and messages appear.</p>
    </div>
  `;
  renderSummaryCards("Idle", 0);
  renderProgressStages(0);
  setCurrentStatus("Idle", "This GitHub demo shows the enhanced run-state layout without executing the live ETL workflow.", 0);
  showMessage("Logs and demo run state cleared.");
}

function showModal() {
  byId("contactModal").classList.add("show");
}

function hideModal() {
  byId("contactModal").classList.remove("show");
}

function initialiseTabs() {
  const reviewTabs = document.querySelectorAll(".review-tab");
  const reviewPanels = document.querySelectorAll(".review-panel");

  reviewTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      reviewTabs.forEach((item) => item.classList.remove("active"));
      reviewPanels.forEach((panel) => panel.classList.remove("active"));
      tab.classList.add("active");
      byId(target)?.classList.add("active");
    });
  });
}

function initialiseThemeToggle() {
  const stored = localStorage.getItem("demo-theme") || "dark";
  document.body.classList.toggle("low-energy", stored === "low");
  byId("accentGlow").checked = stored !== "low";

  byId("accentGlow").addEventListener("change", (event) => {
    const lowEnergy = !event.target.checked;
    document.body.classList.toggle("low-energy", lowEnergy);
    localStorage.setItem("demo-theme", lowEnergy ? "low" : "dark");
  });
}

function initialise() {
  initialiseTabs();
  initialiseThemeToggle();
  populateYearMonthControls();
  populateBusinessModels();
  renderDatasets();
  renderProgressStages(0);
  renderSummaryCards("Idle", 0);
  applyQuickRange("last_7_days");
  updateBusinessModelSelection();
  updateSummaryBar();
  setCurrentStatus("Idle", "This GitHub demo shows the enhanced run-state layout without executing the live ETL workflow.", 0);

  document.querySelectorAll(".compact-slicer").forEach((button) => {
    button.addEventListener("click", () => applyQuickRange(button.dataset.range));
  });

  byId("yearSelect").addEventListener("change", updateDateRangeFromYearMonth);
  byId("monthSelect").addEventListener("change", updateDateRangeFromYearMonth);
  byId("startDate").addEventListener("change", updateSummaryBar);
  byId("endDate").addEventListener("change", updateSummaryBar);
  byId("businessModel").addEventListener("change", updateBusinessModelSelection);

  byId("useRecommendedButton").addEventListener("click", () => {
    const modelValue = byId("businessModel").value;
    tickDatasets(modelValue === "custom_dataset_selection" ? [] : recommendedDatasetsForCurrentModel());
    showMessage("Recommended dataset bundle applied.");
  });

  byId("useEnabledButton").addEventListener("click", () => {
    tickDatasets(enabledDatasetNames());
    showMessage("Enabled core datasets selected.");
  });

  byId("clearSelectionButton").addEventListener("click", () => {
    tickDatasets([]);
    showMessage("Dataset selection cleared.");
  });

  document.querySelectorAll('input[name="dataset"]').forEach((node) => {
    node.addEventListener("change", updateDatasetSummary);
    node.addEventListener("change", updateSummaryBar);
  });

  byId("runButton").addEventListener("click", runPipeline);
  byId("checkExistingButton").addEventListener("click", checkExistingData);
  byId("testDbButton").addEventListener("click", testDbConnection);
  byId("clearLogsButton").addEventListener("click", clearLogs);
  byId("requestDemoChip").addEventListener("click", showModal);
  byId("closeModalBtn").addEventListener("click", hideModal);
}

initialise();
