const state = {
  overview: null,
  eod: null,
  meta: null,
  universe: null,
  benchmarks: null,
  strategies: null,
  baskets: null,
  research: null,
  wealthIntelligence: null,
  wealthOperations: null,
  externalPortfolios: null,
  modelPortfolio: null,
  modelPortfolioToDate: null,
  modelPortfolioV2: null,
  modelPortfolioV2ToDate: null,
  modelPortfolioV3: null,
  modelPortfolioV3ToDate: null,
  modelPortfolioV4: null,
  modelPortfolioV4ToDate: null,
  dayRotationPortfolio: null,
  dayRotationToDate: null,
  riskPortfolio: null,
  riskRequestKey: null,
  riskCorrelation: null,
  riskCorrelationRequestKey: null,
  riskScenarios: null,
  riskScenarioRequestKey: null,
  wealthAllocation: null,
  wealthAllocationRequestKey: null,
  wealthPerformance: null,
  wealthPerformanceRequestKey: null,
  strategySelector: null,
  strategySelectorRequestKey: null,
  automatedReview: null,
  automatedReviewRequestKey: null,
  marketNews: null,
  marketNewsRequestKey: null,
  rebalanceProfiles: null,
  rebalancePreview: null,
  showLowPriorityPortfolios: false,
};
const $ = (selector) => document.querySelector(selector);
let loadingTimer = null;
let loadingStartedAt = null;
const tabWorkspace = {
  "wealth-overview": "wealth",
  allocation: "wealth",
  risk: "wealth",
  performance: "wealth",
  rebalancing: "wealth",
  "ai-wealth": "wealth",
  "model-portfolio": "wealth",
  "model-portfolio-v2": "wealth",
  "model-portfolio-v3": "wealth",
  "model-portfolio-v4": "wealth",
  "day-rotation": "wealth",
  home: "trading",
  "market-news": "trading",
  portfolios: "trading",
  stocks: "trading",
  sectors: "trading",
  strategy: "admin",
  universe: "admin",
  research: "admin",
};
const workspaceDefaultTab = {
  wealth: "wealth-overview",
  trading: "home",
  admin: "strategy",
};

const money = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value || 0);
const pct = (value) => `${value >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}%`;
const pctOrDash = (value) => value === undefined || value === null ? "-" : pct(value);
const number = (value) => Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const tone = (value) => (Number(value) >= 0 ? "positive" : "negative");
const toneOrEmpty = (value) => value === undefined || value === null ? "" : tone(value);
const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
const safeUrl = (value) => {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? escapeHtml(url.href) : "#";
  } catch {
    return "#";
  }
};
const query = () => {
  const params = new URLSearchParams({ from_date: $("#from-date").value });
  if ($("#to-date").value) params.set("to_date", $("#to-date").value);
  if ($("#wealthsimple-fx-fees").checked) params.set("wealthsimple_fx_fees", "true");
  return params.toString();
};
const wealthsimpleQuery = () =>
  $("#wealthsimple-fx-fees").checked ? "?wealthsimple_fx_fees=true" : "";

function tickerLabel(ticker, metadata = null) {
  const details = metadata || state.overview?.stocks.find((row) => row.ticker === ticker)?.wealthsimple;
  if (!details) return `<strong>${ticker}</strong>`;
  const alternative = details.canadian_hedged_alternative
    ? ` CAD-hedged reference: ${details.canadian_hedged_alternative}.`
    : "";
  return `
    <span class="ticker-tip">
      <strong>${ticker}</strong>
      <span class="ticker-tip-text">Wealthsimple estimate: ${details.availability}. ${details.reason}${alternative}</span>
    </span>`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(`${body.detail || `Request failed: ${response.status}`} (${url})`);
  }
  return response.json();
}

const jsonRequest = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function fetchOverviewWithJob() {
  const started = Date.now();
  let job = await fetchJson(`/api/overview-jobs?${query()}`, { method: "POST" });
  if (job.status === "complete" && job.payload) return job.payload;

  let delay = 2500;
  while (true) {
    await sleep(delay);
    const elapsed = Math.floor((Date.now() - started) / 1000);
    updateLoading(
      `Building dashboard cache on the server... ${elapsed}s elapsed. First uncached ranges can take a few minutes on Render.`,
      Math.min(70, 10 + Math.floor(elapsed / 4))
    );
    const response = await fetch(`/api/overview-jobs/${encodeURIComponent(job.job_id)}`);
    if (response.status === 404) {
      updateLoading("Server lost the overview job during deploy/restart. Restarting it...", Math.min(70, 15 + Math.floor(elapsed / 4)));
      job = await fetchJson(`/api/overview-jobs?${query()}`, { method: "POST" });
      if (job.status === "complete" && job.payload) return job.payload;
      delay = 2500;
      continue;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed: ${response.status}`);
    }
    const status = await response.json();
    if (status.status === "complete" && status.payload) {
      return status.payload;
    }
    if (status.status === "error") {
      throw new Error(status.detail || "Overview build failed.");
    }
    delay = Math.min(8000, delay + 500);
  }
}

async function waitForPreloadRebuild() {
  const started = Date.now();
  const initial = await fetchJson("/api/preload-cache/rebuild", { method: "POST" });
  if (initial.status === "complete") {
    return initial;
  }

  let delay = 2500;
  while (true) {
    await sleep(delay);
    const elapsed = Math.floor((Date.now() - started) / 1000);
    updateLoading(
      `Recalculating preloaded cache for latest prices... ${elapsed}s elapsed.`,
      Math.min(80, 10 + Math.floor(elapsed / 4))
    );
    const status = await fetchJson("/api/preload-cache/rebuild");
    if (status.status === "complete") {
      return status;
    }
    if (status.status === "error") {
      throw new Error(status.detail || "Preload cache rebuild failed.");
    }
    delay = Math.min(8000, delay + 500);
  }
}

function setNotificationStatus(message, status = "") {
  const element = $("#notification-status");
  element.textContent = message;
  element.className = `notification-status muted ${status ? `notification-${status}` : ""}`;
  element.classList.toggle("hidden", !message);
}

function notificationMessage(result) {
  if (!result) return "";
  if (result.status === "sent") {
    return `Daily dashboard report emailed to ${result.recipient} for ${result.strategy}: ${result.recent_trades || 0} recent trade(s), ${result.pending_orders} pending order(s), ${result.holdings} holding(s).`;
  }
  if (result.status === "skipped") {
    return `Daily dashboard report email skipped: ${result.reason}.`;
  }
  return `Daily dashboard report email failed: ${result.detail || "unknown error"}.`;
}

async function sendDailyInstructionsEmail() {
  try {
    return await fetchJson(`/api/notifications/daily-instructions?${query()}`, { method: "POST" });
  } catch (error) {
    return { status: "error", detail: error.message };
  }
}

function setProgress(percent) {
  $("#loading-percent").textContent = `${percent}%`;
  $("#progress-bar").style.width = `${percent}%`;
}

function setLoading(message, percent = 0) {
  $("#loading-message").textContent = message;
  $("#loading").classList.remove("hidden");
  setProgress(percent);
  loadingStartedAt = Date.now();
  $("#loading-elapsed").textContent = "0s elapsed";
  clearInterval(loadingTimer);
  loadingTimer = setInterval(() => {
    const seconds = Math.floor((Date.now() - loadingStartedAt) / 1000);
    $("#loading-elapsed").textContent = `${seconds}s elapsed`;
  }, 1000);
}

function updateLoading(message, percent) {
  $("#loading-message").textContent = message;
  setProgress(percent);
}

function clearLoading() {
  clearInterval(loadingTimer);
  loadingTimer = null;
  loadingStartedAt = null;
  $("#loading").classList.add("hidden");
}

function loadingPanel(message) {
  return `
    <div class="drawer-loading">
      <p class="loading">${message}</p>
      <div class="progress-track" aria-label="Drilldown loading in progress">
        <span class="progress-bar indeterminate"></span>
      </div>
    </div>`;
}

function sortableValue(cell) {
  const raw = cell.textContent.trim();
  const numeric = Number(raw.replace(/[$,%+x,]/g, ""));
  return Number.isNaN(numeric) ? raw.toLowerCase() : numeric;
}

function hasExistingRankColumn(table) {
  const firstHeader = table.tHead?.rows?.[0]?.cells?.[0];
  if (!firstHeader) return false;
  return ["rank", "#", "row", "no.", "number"].includes(firstHeader.textContent.trim().toLowerCase());
}

function updateRowNumbers(table) {
  if (!table.tHead) return;
  const headerRow = table.tHead.rows[0];
  const generatedHeader = headerRow.querySelector("th.row-number");
  if (!generatedHeader && hasExistingRankColumn(table)) return;
  if (!generatedHeader) {
    const header = document.createElement("th");
    header.className = "row-number";
    header.scope = "col";
    header.textContent = "#";
    header.title = "Current displayed row number";
    headerRow.prepend(header);
  }
  let rowNumber = 0;
  [...(table.tBodies[0]?.rows || [])].forEach((row) => {
    const placeholder = row.cells.length === 1 && Number(row.cells[0].colSpan || 1) > 1;
    if (placeholder) {
      if (!row.dataset.numberingColspanAdjusted) {
        row.cells[0].colSpan += 1;
        row.dataset.numberingColspanAdjusted = "true";
      }
      return;
    }
    rowNumber += 1;
    let cell = row.querySelector("td.row-number");
    if (!cell) {
      cell = document.createElement("td");
      cell.className = "row-number";
      row.prepend(cell);
    }
    cell.textContent = rowNumber;
  });
}

function sortTable(table, column, direction) {
  const body = table.tBodies[0];
  if (!body) return;
  const rows = [...body.rows];
  rows.sort((left, right) => {
    const a = sortableValue(left.cells[column]);
    const b = sortableValue(right.cells[column]);
    const comparison = typeof a === "number" && typeof b === "number"
      ? a - b
      : String(a).localeCompare(String(b));
    return direction === "asc" ? comparison : -comparison;
  });
  rows.forEach((row) => body.appendChild(row));
  updateRowNumbers(table);
  table.querySelectorAll("th").forEach((header) => header.classList.remove("sort-asc", "sort-desc"));
  table.tHead.rows[0].cells[column].classList.add(`sort-${direction}`);
}

function enableSorting(root = document) {
  root.querySelectorAll("table[data-sortable]").forEach((table) => {
    updateRowNumbers(table);
    if (table.dataset.sortReady) return;
    table.dataset.sortReady = "true";
    table.querySelectorAll("thead th").forEach((header, column) => {
      if (header.classList.contains("row-number")) return;
      header.addEventListener("click", () => {
        const direction = header.classList.contains("sort-asc") ? "desc" : "asc";
        sortTable(table, column, direction);
      });
    });
  });
}

function activeDashboardTab() {
  const requested = window.location.hash.replace("#", "");
  return document.querySelector(`[data-dashboard-tab="${requested}"]`) ? requested : "wealth-overview";
}

function setActiveDashboardTab(tabName, updateHash = true) {
  const nextTab = document.querySelector(`[data-dashboard-tab="${tabName}"]`) ? tabName : "wealth-overview";
  const nextWorkspace = tabWorkspace[nextTab] || "wealth";
  document.querySelectorAll("[data-workspace-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.workspaceTarget === nextWorkspace);
    button.setAttribute("aria-selected", button.dataset.workspaceTarget === nextWorkspace ? "true" : "false");
  });
  document.querySelectorAll("[data-workspace-tab]").forEach((group) => {
    group.classList.toggle("workspace-hidden", group.dataset.workspaceTab !== nextWorkspace);
  });
  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.tabTarget === nextTab);
    button.setAttribute("aria-selected", button.dataset.tabTarget === nextTab ? "true" : "false");
  });
  document.querySelectorAll("[data-dashboard-tab]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.dashboardTab === nextTab);
  });
  if (updateHash && window.location.hash.replace("#", "") !== nextTab) {
    history.replaceState(null, "", `#${nextTab}`);
  }
  if (nextTab === "model-portfolio" && state.overview) {
    loadModelPortfolio().catch(() => {});
  }
  if (nextTab === "model-portfolio-v2" && state.overview) {
    loadModelPortfolioV2().catch(() => {});
  }
  if (nextTab === "model-portfolio-v3" && state.overview) {
    loadModelPortfolioV3().catch(() => {});
  }
  if (nextTab === "model-portfolio-v4" && state.overview) {
    loadModelPortfolioV4().catch(() => {});
  }
  if (nextTab === "day-rotation" && state.overview) {
    loadDayRotationPortfolio().catch(() => {});
  }
  if (nextTab === "wealth-overview" && state.overview) {
    loadStrategySelector().catch(() => {});
    loadAutomatedReview().catch(() => {});
  }
  if (nextTab === "risk" && state.overview) {
    loadRiskPortfolio().catch(() => {});
  }
  if (nextTab === "allocation" && state.overview) {
    loadWealthAllocation().catch(() => {});
  }
  if (nextTab === "performance" && state.overview) {
    loadWealthPerformance().catch(() => {});
  }
  if (nextTab === "rebalancing") {
    loadRebalanceProfiles().catch(() => {});
  }
  if (nextTab === "market-news" && state.overview) {
    loadMarketNews().catch(() => {});
  }
}

function setActiveWorkspace(workspaceName) {
  setActiveDashboardTab(workspaceDefaultTab[workspaceName] || "wealth-overview");
}

function exportRangeSuffix() {
  const from = $("#from-date").value || "from";
  const to = $("#to-date").value || "to";
  return `${from}_to_${to}`;
}

function safeFilename(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "dashboard-export";
}

function exportableTable(table) {
  const copy = table.cloneNode(true);
  copy.querySelectorAll(".ticker-tip-text").forEach((node) => node.remove());
  copy.querySelectorAll("button").forEach((button) => {
    const replacement = document.createElement("span");
    replacement.textContent = button.textContent.trim();
    button.replaceWith(replacement);
  });
  copy.querySelectorAll("th").forEach((header) => header.classList.remove("sort-asc", "sort-desc"));
  return copy.outerHTML;
}

function downloadExcelTables(filenameBase, workbookTitle, tables) {
  const selectedTables = tables.filter((table) => table && table.tBodies[0]?.rows.length);
  if (!selectedTables.length) {
    window.alert("No table rows are available to export yet.");
    return;
  }
  const html = `
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body { font-family: Arial, sans-serif; }
          h1, h2 { text-align: left; }
          table { border-collapse: collapse; margin-bottom: 24px; width: 100%; }
          th, td { border: 1px solid #999; padding: 6px; text-align: left; }
          th { background: #ddebf7; font-weight: bold; }
        </style>
      </head>
      <body>
        <h1>${escapeHtml(workbookTitle)}</h1>
        <p>Exported ${escapeHtml(new Date().toISOString())}</p>
        ${selectedTables.map((table, index) => `<h2>Table ${index + 1}</h2>${exportableTable(table)}`).join("")}
      </body>
    </html>`;
  const blob = new Blob([html], { type: "application/vnd.ms-excel;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${safeFilename(`${filenameBase}_${exportRangeSuffix()}`)}.xls`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

function exportNamedDrawerTable(button) {
  const table = document.querySelector(button.dataset.exportTable);
  downloadExcelTables(button.dataset.exportName, button.dataset.exportTitle, [table]);
}

function signalPill(signal) {
  if (!signal || signal.classification === "none") return '<span class="pill">none</span>';
  const kind = signal.fresh_priority ? "fresh" : signal.classification;
  const label = signal.fresh_priority ? "fresh" : signal.classification;
  return `<span class="pill ${kind}">${label}</span>`;
}

function signalClassification(row) {
  if (!row.signal || row.signal.classification === "none") return "none";
  return row.signal.fresh_priority ? "fresh" : row.signal.classification;
}

function universeByTicker() {
  const rows = state.universe?.assets || [];
  return new Map(rows.map((row) => [String(row.ticker).toUpperCase(), row]));
}

function recommendationRows() {
  const universe = universeByTicker();
  const rows = [];
  for (const stock of state.overview?.stocks || []) {
    if (stock.warning) continue;
    const ticker = String(stock.ticker).toUpperCase();
    const asset = universe.get(ticker);
    const classification = signalClassification(stock);
    const monthly = Number(stock.monthly_change_pct || 0);
    const fiveDay = Number(stock.five_day_change_pct || 0);
    const relative = Number(stock.signal?.five_day_relative_strength_pct || 0);
    if (["fresh", "strict"].includes(classification) && !asset?.strategy_eligible) {
      rows.push({
        stock,
        asset,
        action: "strategy_eligible",
        reason: `${classification} signal with ${pct(relative)} 5D relative strength versus SPY`,
        priority: classification === "fresh" ? 1 : 2,
      });
    } else if (classification === "near" && asset?.status !== "candidate") {
      rows.push({
        stock,
        asset,
        action: "candidate",
        reason: "Near signal: keep watching before strategy promotion",
        priority: 3,
      });
    } else if (classification === "none" && monthly < -10 && fiveDay < 0 && asset?.status === "active") {
      rows.push({
        stock,
        asset,
        action: "archived",
        reason: `No active signal, ${pct(monthly)} monthly move, and weak 5D trend`,
        priority: 4,
      });
    }
  }
  return rows
    .sort((left, right) => left.priority - right.priority || Number(right.stock.return_pct || 0) - Number(left.stock.return_pct || 0))
    .slice(0, 25);
}

function renderRecommendations() {
  const rows = recommendationRows();
  $("#recommendation-rows").innerHTML = rows.length
    ? rows.map(({ stock, asset, action, reason }) => `
      <tr>
        <td>${tickerLabel(stock.ticker, stock.wealthsimple)}</td>
        <td>${escapeHtml(action)}</td>
        <td>${escapeHtml(reason)}</td>
        <td>${signalPill(stock.signal)}</td>
        <td class="${tone(stock.return_pct)}">${pct(stock.return_pct)}</td>
        <td class="${toneOrEmpty(stock.five_day_change_pct)}">${pctOrDash(stock.five_day_change_pct)}</td>
        <td class="${toneOrEmpty(stock.monthly_change_pct)}">${pctOrDash(stock.monthly_change_pct)}</td>
        <td>${escapeHtml(asset?.status || "untracked")}</td>
        <td>
          <div class="asset-action-group">
            <button class="asset-action" data-recommendation-action="${escapeHtml(action)}" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}" data-recommendation-reason="${escapeHtml(reason)}">Approve</button>
            <button class="asset-action" data-recommendation-action="candidate" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}" data-recommendation-reason="${escapeHtml(reason)}">Watch</button>
            <button class="asset-action" data-recommendation-action="archived" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}" data-recommendation-reason="${escapeHtml(reason)}">Archive</button>
            <button class="asset-action" data-recommendation-action="excluded" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}" data-recommendation-reason="${escapeHtml(reason)}">Ignore</button>
          </div>
        </td>
      </tr>`)
      .join("")
    : '<tr><td colspan="9">No current universe suggestions for this window.</td></tr>';
  document.querySelectorAll("[data-recommendation-action]").forEach((button) =>
    button.addEventListener("click", () =>
      saveStockUniverseAction(
        button.dataset.recommendationTicker,
        button.dataset.recommendationType,
        button.dataset.recommendationAction,
        button.dataset.recommendationReason
      )
    )
  );
  enableSorting();
}

function strategyLabParams() {
  const params = new URLSearchParams(query());
  params.set("universe", $("#lab-universe").value);
  params.set("entry_signal_rule", $("#lab-entry-signal").value);
  params.set("entry_news_rule", $("#lab-entry-news").value);
  params.set("exit_rule", $("#lab-exit-rule").value);
  return params;
}

const labLabels = {
  universe: {
    "tracked-stocks": "tracked stocks",
    "mass-change": "mass-change candidates",
    hybrid: "tracked stocks plus mass-change candidates",
  },
  entry: {
    any: "any non-none signal",
    fresh: "fresh signal only",
    strict: "strict signal only",
    near: "near signal only",
    "fresh-or-strict": "fresh or strict signal",
  },
  entryNews: {
    ignore: "ignore",
    active: "active",
    accelerating: "accelerating",
  },
  exit: {
    "signal-disappears": "sell when signal disappears",
    "technical-deterioration": "sell after technical deterioration",
    "hold-while-news-active": "hold while news remains active",
    "confirm-news-cooling": "require news cooling before selling",
    "early-exit-on-news-cooling": "sell earlier when news cools",
    "optimized-grid-winner": "optimized grid winner exit",
  },
};

function defaultLabStrategyName() {
  return [
    "lab",
    $("#lab-universe").value,
    $("#lab-entry-signal").value,
    $("#lab-entry-news").value,
    $("#lab-exit-rule").value,
  ].join("-");
}

function strategyLabRegistryPayload() {
  const universe = $("#lab-universe").value;
  const entry = $("#lab-entry-signal").value;
  const entryNews = $("#lab-entry-news").value;
  const exit = $("#lab-exit-rule").value;
  return {
    strategy_name: $("#lab-strategy-name").value.trim() || defaultLabStrategyName(),
    status: "forward_testing",
    forward_test_start_date: $("#from-date").value || state.meta?.default_from_date || "",
    entry_rule: labLabels.entry[entry] || entry,
    exit_rule: labLabels.exit[exit] || exit,
    news_rule: labLabels.entryNews[entryNews] || entryNews,
    universe: labLabels.universe[universe] || universe,
    benchmark: "SPY",
    position_size: "1000",
    notes: "Saved from the dashboard Strategy Lab. Supported rule sets flow into the dashboard ranking as generated portfolios; no broker trades are created.",
  };
}

function renderStrategyLabResult(detail) {
  $("#strategy-lab-result").classList.remove("hidden");
  $("#strategy-lab-result").innerHTML = strategyPreviewHtml(detail);
  $("#export-strategy-lab").classList.remove("hidden");
  enableSorting();
}

function strategyPreviewHtml(detail) {
  const benchmark = detail.benchmark_comparison;
  const config = detail.lab_config || {};
  const categoryRows = (detail.category_stats || [])
    .map((row) => `
      <tr>
        <td>${escapeHtml(row.category)}</td>
        <td>${row.entries}</td>
        <td>${row.closed_positions}</td>
        <td>${row.open_positions}</td>
        <td>${money(row.deployed_capital)}</td>
        <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
      </tr>`)
    .join("");
  const pendingRows = (detail.pending_next_close_orders || [])
    .map((row) => `
      <tr>
        <td>${escapeHtml(row.action)}</td>
        <td>${tickerLabel(row.ticker)}</td>
        <td>${escapeHtml(row.entry_signal)}</td>
        <td>${escapeHtml(row.signal_observed_date)}</td>
        <td>${row.usd_amount === null ? "-" : money(row.usd_amount)}</td>
      </tr>`)
    .join("");
  return `
    <div class="detail-grid">
      ${stat("Return", pct(detail.return_pct), tone(detail.return_pct))}
      ${stat("Gain / loss", money(detail.gain_loss), tone(detail.gain_loss))}
      ${stat("Current value", money(detail.current_value))}
      ${stat("Open positions", number(detail.position_count))}
      ${benchmark ? stat("Alpha vs SPY", pct(benchmark.alpha_pct), tone(benchmark.alpha_pct)) : ""}
      ${benchmark ? stat("Max drawdown", pct(benchmark.max_drawdown_pct), tone(benchmark.max_drawdown_pct)) : ""}
      ${stat("Trade cycles", number(detail.trade_cycles))}
      ${stat("Position size", money(config.position_size || 1000))}
    </div>
    <p class="muted">Config: universe=${escapeHtml(config.universe || "-")}; entry=${escapeHtml(config.entry_signal_rule || "-")}; entry news=${escapeHtml(config.entry_news_rule || "-")}; exit=${escapeHtml(config.exit_rule || "-")}.</p>
    <h3>Rolling returns</h3>
    <div class="chart">${rollingReturnPolyline(detail.series || [])}</div>
    <h3>Drawdown</h3>
    <div class="chart">${drawdownPolyline(detail.series || [])}</div>
    ${contributorsHtml(detail)}
    ${sectorExposureHtml(detail)}
    ${signalMixHtml(detail)}
    ${capitalDeploymentHtml(detail)}
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr><th>Signal</th><th>Entries</th><th>Closed</th><th>Open</th><th>Deployed</th><th>Gain / loss</th><th>Return</th></tr></thead>
        <tbody>${categoryRows || '<tr><td colspan="7">No category results for this preview.</td></tr>'}</tbody>
      </table>
    </div>
    <h3>Pending next-close actions</h3>
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr><th>Action</th><th>Ticker</th><th>Signal</th><th>Observed</th><th>Amount</th></tr></thead>
        <tbody>${pendingRows || '<tr><td colspan="5">No pending next-close actions for this preview.</td></tr>'}</tbody>
      </table>
    </div>`;
}

function contributorsHtml(detail) {
  const rows = [
    ...(detail.positions || []).map((row) => ({ ...row, status: "open" })),
    ...(detail.realized_positions || []).map((row) => ({ ...row, status: "realized" })),
  ].filter((row) => row.gain_loss !== undefined && row.gain_loss !== null);
  if (!rows.length) return "";
  const byGain = [...rows].sort((left, right) => Number(right.gain_loss || 0) - Number(left.gain_loss || 0));
  const contributors = byGain.slice(0, 5);
  const detractors = byGain.slice(-5).reverse();
  const positionValue = (row) => {
    if (row.current_value !== undefined) return money(row.current_value);
    if (row.ending_value !== undefined) return money(row.ending_value);
    return "-";
  };
  const renderRows = (items) => items
    .map((row) => `
      <tr>
        <td>${tickerLabel(row.ticker)}</td>
        <td>${escapeHtml(row.status)}</td>
        <td>${row.entry_signal ? escapeHtml(row.entry_signal) : "-"}</td>
        <td>${positionValue(row)}</td>
        <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
        <td class="${tone(row.return_pct || 0)}">${pct(row.return_pct || 0)}</td>
      </tr>`)
    .join("");
  return `
    <div class="eod-grid">
      <div>
        <h3>Top contributors</h3>
        <div class="table-wrap">
          <table data-sortable><thead><tr><th>Ticker</th><th>Status</th><th>Signal</th><th>Value</th><th>Gain / loss</th><th>Return</th></tr></thead><tbody>${renderRows(contributors)}</tbody></table>
        </div>
      </div>
      <div>
        <h3>Top detractors</h3>
        <div class="table-wrap">
          <table data-sortable><thead><tr><th>Ticker</th><th>Status</th><th>Signal</th><th>Value</th><th>Gain / loss</th><th>Return</th></tr></thead><tbody>${renderRows(detractors)}</tbody></table>
        </div>
      </div>
    </div>`;
}

function capitalDeploymentHtml(detail) {
  const hasDeployment = (detail.series || []).some((row) => row.deployed_capital !== undefined || row.active_positions !== undefined);
  const trades = detail.simulated_trades || [];
  if (!hasDeployment && !trades.length) return "";
  return `
    <h3>Capital deployment</h3>
    <div class="chart">${deploymentPolyline(detail.series || [])}</div>
    <h3>Strategy turnover</h3>
    <div class="chart">${tradeActivityPolyline(trades)}</div>`;
}

function sectorExposureHtml(detail) {
  if (!(detail.sector_exposure || []).some((row) => (row.sectors || []).length)) return "";
  return `
    <h3>Sector exposure over time</h3>
    <div class="chart">${sectorExposurePolyline(detail.sector_exposure || [])}</div>`;
}

function sectorExposurePolyline(rows) {
  const points = (rows || []).filter((row) => Array.isArray(row.sectors) && row.sectors.length);
  if (points.length < 2) return '<p class="chart-empty">Sector exposure needs at least two daily observations.</p>';
  const sectorMax = new Map();
  for (const row of points) {
    for (const sector of row.sectors) {
      const name = sector.sector || "Unclassified";
      sectorMax.set(name, Math.max(sectorMax.get(name) || 0, Number(sector.weight_pct || 0)));
    }
  }
  const sectors = [...sectorMax.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([sector]) => sector);
  if (!sectors.length) return '<p class="chart-empty">Sector exposure is not available for this view.</p>';
  const width = 680;
  const height = 190;
  const colors = ["#57d3a2", "#6fb7ff", "#ffd166", "#c084fc", "#ff7b7b"];
  const weightFor = (row, sectorName) => Number((row.sectors || []).find((sector) => sector.sector === sectorName)?.weight_pct || 0);
  const pathFor = (sectorName) => points
    .map((row, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - (weightFor(row, sectorName) / 100) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const legend = sectors
    .map((sector, index) => `<text x="${4 + index * 132}" y="232" fill="${colors[index % colors.length]}" font-size="12">${escapeHtml(sector).slice(0, 18)}</text>`)
    .join("");
  return `
    <svg viewBox="0 0 ${width} 240" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <text x="4" y="18" fill="#91a4bd" font-size="12">Top sector weights</text>
      ${sectors.map((sector, index) => `<polyline points="${pathFor(sector)}" fill="none" stroke="${colors[index % colors.length]}" stroke-width="3" vector-effect="non-scaling-stroke" />`).join("")}
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
      ${legend}
    </svg>`;
}

function signalMixHtml(detail) {
  if (!(detail.signal_mix || []).some((row) => (row.signals || []).length)) return "";
  return `
    <h3>Signal mix over time</h3>
    <div class="chart">${signalMixPolyline(detail.signal_mix || [])}</div>`;
}

function signalMixPolyline(rows) {
  const points = (rows || []).filter((row) => Array.isArray(row.signals) && row.signals.length);
  if (points.length < 2) return '<p class="chart-empty">Signal mix needs at least two daily observations.</p>';
  const signals = ["fresh", "strict", "near", "unknown"].filter((signal) =>
    points.some((row) => (row.signals || []).some((item) => item.signal === signal))
  );
  if (!signals.length) return '<p class="chart-empty">Signal mix is not available for this view.</p>';
  const width = 680;
  const height = 190;
  const colors = { fresh: "#57d3a2", strict: "#6fb7ff", near: "#ffd166", unknown: "#91a4bd" };
  const weightFor = (row, signalName) => Number((row.signals || []).find((item) => item.signal === signalName)?.weight_pct || 0);
  const pathFor = (signalName) => points
    .map((row, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - (weightFor(row, signalName) / 100) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const legend = signals
    .map((signal, index) => `<text x="${4 + index * 92}" y="232" fill="${colors[signal] || "#91a4bd"}" font-size="12">${escapeHtml(signal)}</text>`)
    .join("");
  return `
    <svg viewBox="0 0 ${width} 240" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <text x="4" y="18" fill="#91a4bd" font-size="12">Active positions by entry signal</text>
      ${signals.map((signal) => `<polyline points="${pathFor(signal)}" fill="none" stroke="${colors[signal] || "#91a4bd"}" stroke-width="3" vector-effect="non-scaling-stroke" />`).join("")}
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
      ${legend}
    </svg>`;
}

function deploymentPolyline(series) {
  const points = series.filter((row) => row.deployed_capital !== undefined || row.active_positions !== undefined);
  if (points.length < 2) return '<p class="chart-empty">Capital deployment history is not available for this view.</p>';
  const deployedValues = points.map((row) => Number(row.deployed_capital || 0));
  const positionValues = points.map((row) => Number(row.active_positions || 0));
  const maxDeployed = Math.max(...deployedValues, 1);
  const maxPositions = Math.max(...positionValues, 1);
  const width = 680;
  const height = 190;
  const pathFor = (values, maxValue) => values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - (value / maxValue) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <polyline points="${pathFor(deployedValues, maxDeployed)}" fill="none" stroke="#57d3a2" stroke-width="3" vector-effect="non-scaling-stroke" />
      <polyline points="${pathFor(positionValues, maxPositions)}" fill="none" stroke="#6fb7ff" stroke-width="2" vector-effect="non-scaling-stroke" />
      <text x="4" y="18" fill="#57d3a2" font-size="12">${money(maxDeployed)} deployed</text>
      <text x="4" y="36" fill="#6fb7ff" font-size="12">${number(maxPositions)} active positions</text>
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
    </svg>`;
}

function tradeActivityPolyline(trades) {
  if (!trades.length) return '<p class="chart-empty">Trade activity is not available for this view.</p>';
  const counts = new Map();
  for (const trade of trades) {
    if (!trade.date || trade.date === "next available close") continue;
    const row = counts.get(trade.date) || { date: trade.date, buy: 0, sell: 0 };
    if (trade.action === "sell") row.sell += 1;
    else row.buy += 1;
    counts.set(trade.date, row);
  }
  const points = [...counts.values()].sort((left, right) => left.date.localeCompare(right.date));
  if (points.length < 2) return '<p class="chart-empty">Trade activity needs at least two execution dates.</p>';
  const totals = points.map((row) => row.buy + row.sell);
  const maxTotal = Math.max(...totals, 1);
  const width = 680;
  const height = 190;
  const pathFor = (key) => points
    .map((row, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - (row[key] / maxTotal) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <polyline points="${pathFor("buy")}" fill="none" stroke="#57d3a2" stroke-width="3" vector-effect="non-scaling-stroke" />
      <polyline points="${pathFor("sell")}" fill="none" stroke="#ff7b7b" stroke-width="2" vector-effect="non-scaling-stroke" />
      <text x="4" y="18" fill="#91a4bd" font-size="12">Max ${number(maxTotal)} trades/day</text>
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
      <text x="4" y="232" fill="#57d3a2" font-size="12">Buys</text>
      <text x="52" y="232" fill="#ff7b7b" font-size="12">Sells</text>
    </svg>`;
}

function newsActivityPolyline(rows) {
  const points = (rows || []).filter((row) => row.articles !== undefined);
  if (points.length < 2) return '<p class="chart-empty">Historical news activity is not available for this ticker.</p>';
  const values = points.map((row) => Number(row.articles || 0));
  const maxValue = Math.max(...values, 1);
  const width = 680;
  const height = 190;
  const path = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - (value / maxValue) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <polyline points="${path}" fill="none" stroke="#f9c74f" stroke-width="3" vector-effect="non-scaling-stroke" />
      <text x="4" y="18" fill="#f9c74f" font-size="12">Max ${number(maxValue)} articles/day</text>
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
    </svg>`;
}

async function saveStrategyLab() {
  const status = $("#strategy-lab-status");
  const button = $("#save-strategy-lab");
  try {
    status.textContent = "Saving Strategy Lab configuration...";
    button.disabled = true;
    const result = await fetchJson("/api/strategies", jsonRequest("POST", strategyLabRegistryPayload()));
    await refreshUniverse();
    status.textContent = `Saved ${result.strategy.strategy_name} to the strategy registry.`;
  } catch (error) {
    status.textContent = `Strategy save failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function updateStrategyStatus(strategyId, statusValue) {
  const row = (state.strategies?.strategies || []).find((strategy) => strategy.strategy_id === strategyId);
  if (!row) return;
  const payload = { ...row, status: statusValue };
  try {
    await fetchJson("/api/strategies", jsonRequest("POST", payload));
    await refreshUniverse();
    $("#universe-status").textContent = `Updated ${row.strategy_name} to ${statusValue}.`;
  } catch (error) {
    $("#universe-status").textContent = `Strategy update failed: ${error.message}`;
  }
}

async function runStrategyLab() {
  const status = $("#strategy-lab-status");
  const button = $("#run-strategy-lab");
  const exportButton = $("#export-strategy-lab");
  try {
    status.textContent = "Running strategy preview...";
    button.disabled = true;
    exportButton.classList.add("hidden");
    const detail = await fetchJson(`/api/strategy-lab/run?${strategyLabParams().toString()}`);
    renderStrategyLabResult(detail);
    status.textContent = `Preview complete: ${detail.from_date} to ${detail.to_date}. Unsaved strategy only.`;
  } catch (error) {
    status.textContent = `Strategy preview failed: ${error.message}`;
    exportButton.classList.add("hidden");
  } finally {
    button.disabled = false;
  }
}

function classificationPill(classification, label = classification) {
  if (!classification || classification === "none") return '<span class="pill">none</span>';
  return `<span class="pill ${classification}">${label}</span>`;
}

function isLowPriorityPortfolio(row = {}) {
  return String(row.portfolio_priority || "").toLowerCase() === "low";
}

function portfolioRows(rows = []) {
  return state.showLowPriorityPortfolios ? rows : rows.filter((row) => !isLowPriorityPortfolio(row));
}

function lowPriorityCount(rows = []) {
  return rows.filter(isLowPriorityPortfolio).length;
}

function renderLowPriorityControls() {
  const controls = document.querySelectorAll("[data-low-priority-count]");
  const count = lowPriorityCount(state.overview?.traders || []);
  controls.forEach((control) => {
    control.textContent = state.showLowPriorityPortfolios
      ? `${count} research watchlists shown`
      : `${count} research watchlists collapsed`;
  });
  document.querySelectorAll("[data-show-low-priority]").forEach((input) => {
    input.checked = state.showLowPriorityPortfolios;
  });
}

function renderCards() {
  const allTraders = state.overview.traders;
  const traders = portfolioRows(allTraders);
  const stocks = state.overview.stocks;
  const strict = stocks.filter((row) => row.signal?.classification === "strict").length;
  const fresh = stocks.filter((row) => row.signal?.fresh_priority).length;
  const leader = traders[0];
  const wsAvailability = state.overview.wealthsimple_availability;
  const topSector = state.overview.sector_breakdowns?.[0];
  $("#summary-cards").innerHTML = [
    [
      "Portfolios",
      traders.length,
      `Primary portfolios; ${lowPriorityCount(allTraders)} secondary portfolios collapsed into Research Watchlists`,
    ],
    ["Tracked instruments", stocks.length, "Stocks, ETFs, and crypto"],
    ["Leading sector", topSector?.sector || "-", topSector ? pct(topSector.average_return_pct) : "-"],
    ["Fresh signal matches", fresh, `${strict} strict technical matches`],
    ["Leading portfolio", leader?.investor || "-", leader ? pct(leader.return_pct) : "-"],
    ["Wealthsimple estimate", wsAvailability["likely-supported"], `${wsAvailability["verify-in-app"]} verify in app; ${wsAvailability["likely-unsupported"]} likely unsupported`],
  ]
    .map(
      ([label, value, note]) => `
        <article class="summary-card">
          <p class="eyebrow">${label}</p>
          <p class="value">${value}</p>
          <p class="muted">${note}</p>
        </article>`
    )
    .join("");
}

function renderWealthOverview() {
  if (!state.overview) return;
  const allTraders = state.overview.traders || [];
  const traders = portfolioRows(allTraders);
  const stocks = state.overview.stocks || [];
  const leader = traders[0];
  const totalCurrent = traders.reduce((sum, row) => sum + Number(row.current_value || 0), 0);
  const reviewQueue = state.wealthOperations?.advisor_review_queue || [];
  const proposals = state.wealthOperations?.proposal_matrix || [];
  const wsAvailability = state.overview.wealthsimple_availability || {};
  const strict = stocks.filter((row) => row.signal?.classification === "strict").length;
  const fresh = stocks.filter((row) => row.signal?.fresh_priority).length;
  const topSector = state.overview.sector_breakdowns?.[0];
  $("#wealth-overview-window").textContent =
    `${state.overview.from_date} to ${state.overview.latest_available_date || state.overview.to_date || "latest available close"} | Research-only wealth analytics.`;
  $("#wealth-overview-cards").innerHTML = [
    ["Tracked value", money(totalCurrent), `${traders.length} primary portfolios included`],
    ["Leading strategy", leader?.investor || "-", leader ? pct(leader.return_pct) : "No result yet"],
    ["Fresh / strict signals", `${fresh} / ${strict}`, `${stocks.length} tracked instruments`],
    ["Top sector", topSector?.sector || "-", topSector ? pct(topSector.average_return_pct) : "No sector result"],
    ["Review queue", reviewQueue.length, `${proposals.length} draft proposal rows`],
    ["Wealthsimple coverage", wsAvailability["likely-supported"] ?? "-", `${wsAvailability["verify-in-app"] || 0} verify in app`],
  ].map(([label, value, note]) => `
      <article class="summary-card wealth-kpi">
        <p class="eyebrow">${escapeHtml(label)}</p>
        <p class="value">${escapeHtml(value)}</p>
        <p class="muted">${escapeHtml(note)}</p>
      </article>`).join("");
}

function renderStrategySelector() {
  const payload = state.strategySelector;
  if (!payload) return;
  const ranked = payload.ranked_strategies || [];
  $("#strategy-selector-summary").innerHTML = [
    ["Recommendation", String(payload.recommendation_status || "-").replaceAll("_", " "), payload.recommended_action || ""],
    ["Selected strategy", payload.recommended_strategy || "-", `${number(ranked.length)} candidates reviewed`],
    ["Draft blend", `${number((payload.draft_blend || []).length)} sleeves`, "Research-only allocation sketch"],
    ["Review mode", payload.data_quality?.write_behavior || "read only", "No orders or ledgers created"],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value">${escapeHtml(value)}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#strategy-selector-rows").innerHTML = ranked.map((row, index) => {
    const metrics = row.metrics || {};
    return `<tr><td>${index + 1}</td><td><strong>${escapeHtml(row.label || row.strategy_id)}</strong></td><td>${number(row.score)}</td><td class="${tone(metrics.return_pct)}">${pct(metrics.return_pct)}</td><td class="${tone(metrics.max_drawdown_pct)}">${pct(metrics.max_drawdown_pct)}</td><td>${number(metrics.top_five_weight_pct)}%</td><td>${escapeHtml(String(row.review_action || "").replaceAll("_", " "))}</td><td>${escapeHtml((row.warnings || []).join("; ") || "None")}</td></tr>`;
  }).join("") || '<tr><td colspan="8">No strategy candidates available.</td></tr>';
  const blend = payload.draft_blend || [];
  $("#strategy-selector-blend").innerHTML = blend.length
    ? `<h4>Draft blend guardrails</h4><ul class="wealth-list">${blend.map((row) => `<li><strong>${escapeHtml(row.sleeve)}</strong>: ${number(row.target_weight_pct)}% - ${escapeHtml(row.reason)}</li>`).join("")}</ul>`
    : `<h4>Warnings</h4><ul class="wealth-list">${(payload.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>No selector warnings.</li>"}</ul>`;
  $("#strategy-selector-content").classList.remove("hidden");
  $("#strategy-selector-status").textContent = `${payload.from_date} to ${payload.to_date}; ${payload.assumptions?.[0] || "Research-only strategy comparison."}`;
  enableSorting();
}

function renderAutomatedReview() {
  const payload = state.automatedReview;
  if (!payload) return;
  const allocation = payload.allocation_health || {};
  const rebalance = payload.rebalance_health || {};
  $("#automated-review-summary").innerHTML = [
    ["Status", String(payload.review_status || "-").replaceAll("_", " "), payload.next_review_action || ""],
    ["Metadata", `${number(allocation.complete_metadata_pct)}%`, `Asset type ${number(allocation.asset_type_metadata_pct)}%`],
    ["Top five", `${number(allocation.top_five_weight_pct)}%`, `Largest position ${number(allocation.top_position_weight_pct)}%`],
    ["Draft rebalance", rebalance.draft_available ? "Available" : "Blocked", (rebalance.blockers || []).join("; ") || "No blockers"],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value">${escapeHtml(value)}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#automated-review-warnings").innerHTML = `<h4>Warnings &amp; assumptions</h4><ul class="wealth-list">${(payload.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>No warnings.</li>"}${(payload.assumptions || []).map((assumption) => `<li>${escapeHtml(assumption)}</li>`).join("")}</ul>`;
  $("#automated-review-content").classList.remove("hidden");
  $("#automated-review-status").textContent = `${payload.from_date} to ${payload.to_date}; ${payload.data_quality?.write_behavior || "read only"}.`;
}

async function loadAutomatedReview(force = false) {
  if (!$("#from-date").value || !$("#to-date").value) return;
  const requestKey = query();
  if (!force && state.automatedReview && state.automatedReviewRequestKey === requestKey) {
    renderAutomatedReview();
    return;
  }
  const button = $("#reload-automated-review");
  button.disabled = true;
  $("#automated-review-status").textContent = "Running automated wealth review...";
  try {
    state.automatedReview = await fetchJson(`/api/wealth/automated-review?${requestKey}`);
    state.automatedReviewRequestKey = requestKey;
    renderAutomatedReview();
  } catch (error) {
    $("#automated-review-status").textContent = `Automated review failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function loadStrategySelector(force = false) {
  if (!$("#from-date").value || !$("#to-date").value) return;
  const requestKey = query();
  if (!force && state.strategySelector && state.strategySelectorRequestKey === requestKey) {
    renderStrategySelector();
    return;
  }
  const button = $("#reload-strategy-selector");
  button.disabled = true;
  $("#strategy-selector-status").textContent = "Running investment committee selector...";
  try {
    state.strategySelector = await fetchJson(`/api/wealth/strategy-selector?${requestKey}`);
    state.strategySelectorRequestKey = requestKey;
    renderStrategySelector();
  } catch (error) {
    $("#strategy-selector-status").textContent = `Strategy selector failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function listItems(rows, formatter, empty = "No items for this window.") {
  return rows.length
    ? `<ul>${rows.map((row) => `<li>${formatter(row)}</li>`).join("")}</ul>`
    : `<p class="muted">${empty}</p>`;
}

function commandCenterPanel(title, rows, formatter, empty) {
  return `
    <article class="command-card">
      <h3>${escapeHtml(title)}</h3>
      ${listItems(rows, formatter, empty)}
    </article>`;
}

function renderCommandCenter() {
  const stocks = state.overview.stocks || [];
  const sectors = state.overview.sector_breakdowns || [];
  const traders = portfolioRows(state.overview.traders || []);
  const recommendations = recommendationRows();
  const freshSignals = stocks
    .filter((row) => row.signal?.fresh_priority)
    .sort((left, right) => Number(right.signal?.five_day_relative_strength_pct || 0) - Number(left.signal?.five_day_relative_strength_pct || 0))
    .slice(0, 5);
  const relativeMovers = stocks
    .filter((row) => row.signal && !row.warning)
    .sort((left, right) => Number(right.signal?.five_day_relative_strength_pct || 0) - Number(left.signal?.five_day_relative_strength_pct || 0))
    .slice(0, 5);
  const strategyMomentum = traders
    .filter((row) => String(row.source || "").startsWith("derived"))
    .sort((left, right) => Number(right.five_day_change_pct || 0) - Number(left.five_day_change_pct || 0))
    .slice(0, 5);
  const focusedStrategy = traders.find((row) => row.investor === "watchlist-variable-news-optimized-experimental");
  const pendingActions = focusedStrategy?.pending_next_close_orders || [];
  const suggestionRows = recommendations.slice(0, 5);
  $("#command-center-grid").innerHTML = [
    commandCenterPanel(
      "Pending Strategy Actions",
      pendingActions,
      (row) => `<strong>${escapeHtml(row.action)}</strong> ${tickerLabel(row.ticker)} ${escapeHtml(row.entry_signal || "-")} observed ${escapeHtml(row.signal_observed_date || "-")}`,
      "No pending next-close actions for watchlist-variable-news-optimized-experimental."
    ),
    commandCenterPanel(
      "New Fresh Signals",
      freshSignals,
      (row) => `${tickerLabel(row.ticker, row.wealthsimple)} <span class="${tone(row.signal.five_day_relative_strength_pct)}">${pct(row.signal.five_day_relative_strength_pct)} vs SPY</span>`,
      "No fresh-priority signals."
    ),
    commandCenterPanel(
      "Sector Heat",
      sectors.slice(0, 5),
      (row) => `<strong>${escapeHtml(row.sector)}</strong> ${pct(row.average_return_pct)} avg; ${row.signal_counts?.fresh || 0} fresh`,
      "No sector breakdown available."
    ),
    commandCenterPanel(
      "Benchmark-Relative Movers",
      relativeMovers,
      (row) => `${tickerLabel(row.ticker, row.wealthsimple)} <span class="${tone(row.signal.five_day_relative_strength_pct)}">${pct(row.signal.five_day_relative_strength_pct)}</span>`,
      "No benchmark-relative movers."
    ),
    commandCenterPanel(
      "Strategy Momentum",
      strategyMomentum,
      (row) => `<strong>${escapeHtml(row.investor)}</strong> <span class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</span> 5D`,
      "No derived strategy momentum rows."
    ),
    commandCenterPanel(
      "Universe Suggestions",
      suggestionRows,
      ({ stock, action }) => `${tickerLabel(stock.ticker, stock.wealthsimple)} -> ${escapeHtml(action)}`,
      "No add/archive suggestions."
    ),
  ].join("");
}

function renderDiagnostics() {
  const metrics = state.overview.dashboard_metrics;
  if (!metrics) {
    $("#diagnostic-cards").innerHTML = "";
    return;
  }
  const portfolio = metrics.portfolio_breadth;
  const stock = metrics.stock_breadth;
  const signal = metrics.signal_mix;
  const flags = metrics.decision_flags;
  $("#diagnostic-cards").innerHTML = [
    {
      label: "Portfolio breadth",
      value: pct(portfolio.win_rate_pct),
      note: `${portfolio.positive_count} up / ${portfolio.negative_count} down; median ${pct(portfolio.median_return_pct)}`,
      toneValue: portfolio.win_rate_pct - 50,
    },
    {
      label: "Concentration check",
      value: pct(portfolio.top_portfolio_concentration_pct),
      note: "Share of dashboard value in the largest portfolio",
      toneValue: 50 - portfolio.top_portfolio_concentration_pct,
    },
    {
      label: "Stock breadth",
      value: pct(stock.win_rate_pct),
      note: `${stock.positive_count} stocks up / ${stock.negative_count} down; median ${pct(stock.median_return_pct)}`,
      toneValue: stock.win_rate_pct - 50,
    },
    {
      label: "Best / worst stock",
      value: `${stock.top_stock || "-"} ${pct(stock.top_stock_return_pct)}`,
      note: `${stock.bottom_stock || "-"} ${pct(stock.bottom_stock_return_pct)}`,
      toneValue: stock.top_stock_return_pct,
    },
    {
      label: "Active signal mix",
      value: `${flags.fresh_or_strict_count} priority`,
      note: `${signal.fresh} fresh, ${signal.strict} strict, ${signal.near} near, ${signal.none} inactive`,
      toneValue: flags.fresh_or_strict_count,
    },
    {
      label: "Near-signal pipeline",
      value: signal.near,
      note: "Names close to a stronger signal setup",
      toneValue: signal.near,
    },
  ]
    .map(
      (card) => `
        <article class="diagnostic-card">
          <p class="eyebrow">${card.label}</p>
          <p class="value ${tone(card.toneValue)}">${card.value}</p>
          <p class="muted">${card.note}</p>
        </article>`
    )
    .join("");
}

function listHtml(rows = []) {
  return rows.map((row) => `<li>${escapeHtml(row)}</li>`).join("");
}

function renderWealthIntelligence() {
  const payload = state.wealthIntelligence;
  if (!payload) return;
  const readiness = payload.business_readiness || {};
  const positioning = payload.positioning || {};
  $("#ai-wealth-window").textContent = `${payload.from_date} to ${payload.latest_available_date || payload.to_date || "latest"}`;
  $("#ai-wealth-disclaimer").textContent = ` ${payload.disclaimer || ""}`;
  $("#ai-wealth-readiness").innerHTML = [
    {
      label: "Readiness",
      value: `${number(readiness.score)} / 100`,
      note: readiness.stage || "-",
      toneValue: Number(readiness.score || 0) - 60,
    },
    {
      label: "Positioning",
      value: "AI-assisted",
      note: positioning.recommended_claim || "-",
      toneValue: 1,
    },
    {
      label: "Model candidates",
      value: (payload.ai_signal_candidates || []).filter((row) => row.suggested_action === "model_candidate").length,
      note: "Research candidates only; no trades created",
      toneValue: 1,
    },
  ].map((card) => `
    <article class="diagnostic-card">
      <p class="eyebrow">${escapeHtml(card.label)}</p>
      <p class="value ${tone(card.toneValue)}">${escapeHtml(card.value)}</p>
      <p class="muted">${escapeHtml(card.note)}</p>
    </article>`).join("");
  $("#ai-wealth-operating-model").innerHTML = listHtml(payload.operating_model || []);
  $("#ai-wealth-positioning").innerHTML = `
    <p><strong>Use:</strong> ${escapeHtml(positioning.recommended_claim || "-")}</p>
    <p><strong>Avoid:</strong></p>
    <ul class="wealth-list">${listHtml(positioning.avoid_claims || [])}</ul>
    <p class="muted">${escapeHtml((readiness.strengths || []).join(" "))}</p>
    <p class="muted">${escapeHtml((readiness.gaps || []).join(" "))}</p>`;
  $("#ai-wealth-market-rows").innerHTML = (payload.market_context || []).map((row) => `
    <tr>
      <td>${escapeHtml(row.category || "-")}</td>
      <td><strong>${escapeHtml(row.reference || "-")}</strong></td>
      <td>${escapeHtml(row.signal || "-")}</td>
      <td>${escapeHtml(row.product_implication || "-")}</td>
      <td><a href="${safeUrl(row.source)}" target="_blank" rel="noopener noreferrer">Source</a></td>
    </tr>`).join("") || '<tr><td colspan="5">No market context is available.</td></tr>';
  $("#ai-wealth-theme-rows").innerHTML = (payload.theme_opportunities || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.theme)}</strong></td>
      <td>${number(row.candidate_count)}</td>
      <td>${number(row.model_candidates)}</td>
      <td>${number(row.high_risk_count)}</td>
      <td>${number(row.average_score)}</td>
      <td>${escapeHtml((row.top_tickers || []).join(", "))}</td>
    </tr>`).join("") || '<tr><td colspan="6">No theme opportunities available for this window.</td></tr>';
  $("#ai-wealth-basket-rows").innerHTML = (payload.model_baskets || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.name || row.basket_id)}</strong><br><span class="muted">${escapeHtml(row.basket_id || "")}</span></td>
      <td>${escapeHtml(row.role || "-")}</td>
      <td>${escapeHtml(row.status || "-")}</td>
      <td>${number(row.member_count)}</td>
      <td>${escapeHtml(row.benchmark || "-")}</td>
      <td>${escapeHtml(row.rebalance_frequency || "-")}</td>
      <td>${escapeHtml(row.notes || "-")}</td>
    </tr>`).join("") || '<tr><td colspan="7">No model baskets are registered yet.</td></tr>';
  $("#ai-wealth-candidate-rows").innerHTML = (payload.ai_signal_candidates || []).map((row) => `
    <tr class="clickable" data-ai-wealth-stock="${escapeHtml(row.ticker)}">
      <td>${tickerLabel(row.ticker, row.wealthsimple)}</td>
      <td>${escapeHtml(row.sector || "-")}</td>
      <td>${number(row.score)}</td>
      <td>${escapeHtml(row.signal || "-")}</td>
      <td><span class="pill risk-${escapeHtml(row.risk_bucket)}">${escapeHtml(row.risk_bucket || "-")}</span></td>
      <td>${escapeHtml(row.suggested_action || "-")}</td>
      <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
      <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
      <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
      <td>${escapeHtml((row.drivers || []).join(" | "))}</td>
    </tr>`).join("") || '<tr><td colspan="10">No AI signal candidates available for this window.</td></tr>';
  $("#ai-wealth-risk-controls").innerHTML = listHtml(payload.risk_controls || []);
  $("#ai-wealth-next-steps").innerHTML = listHtml(payload.next_build_steps || []);
  document.querySelectorAll("[data-ai-wealth-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.aiWealthStock))
  );
  enableSorting();
}

function renderWealthOperations() {
  const payload = state.wealthOperations;
  if (!payload) return;
  const summary = payload.summary || {};
  $("#wealth-ops-summary").innerHTML = [
    {
      label: "Policy profiles",
      value: number(summary.profile_count),
      note: `${number(summary.ready_profile_count)} ready for internal review`,
      toneValue: summary.ready_profile_count || 0,
    },
    {
      label: "Review queue",
      value: number(summary.review_task_count),
      note: `${number(summary.high_priority_task_count)} high priority item(s)`,
      toneValue: -Number(summary.high_priority_task_count || 0),
    },
    {
      label: "Governance",
      value: "Human review",
      note: payload.disclaimer || "",
      toneValue: 1,
    },
  ].map((card) => `
    <article class="diagnostic-card">
      <p class="eyebrow">${escapeHtml(card.label)}</p>
      <p class="value ${tone(card.toneValue)}">${escapeHtml(card.value)}</p>
      <p class="muted">${escapeHtml(card.note)}</p>
    </article>`).join("");
  $("#wealth-ops-module-rows").innerHTML = (payload.operating_modules || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.module || "-")}</strong></td>
      <td>${escapeHtml(row.status || "-")}</td>
      <td>${escapeHtml(row.description || "-")}</td>
    </tr>`).join("") || '<tr><td colspan="3">No operating modules configured.</td></tr>';
  $("#wealth-command-rows").innerHTML = (payload.ai_command_workbench || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.title || row.command_id)}</strong><br><span class="muted">${escapeHtml(row.command_id || "")}</span></td>
      <td>${escapeHtml(row.category || "-")}</td>
      <td>${escapeHtml(row.trigger || "-")}</td>
      <td>${escapeHtml(row.output_type || "-")}</td>
      <td>${escapeHtml(row.guardrail || "-")}</td>
      <td class="prompt-cell">${escapeHtml(row.generated_prompt || "-")}</td>
      <td><button class="asset-action" data-command-copy="${escapeHtml(row.command_id)}">Copy</button></td>
    </tr>`).join("") || '<tr><td colspan="7">No AI commands configured.</td></tr>';
  $("#wealth-profile-rows").innerHTML = (payload.client_profiles || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.profile_name || row.profile_id)}</strong><br><span class="muted">${escapeHtml(row.profile_id || "")}</span></td>
      <td>${escapeHtml(row.status || "-")}</td>
      <td>${escapeHtml(row.risk_tolerance || "-")}</td>
      <td>${number(row.time_horizon_years)} years</td>
      <td>${escapeHtml(row.primary_objective || "-")}</td>
      <td>${escapeHtml(row.liquidity_need || "-")}</td>
      <td>${number(row.max_tactical_pct)}%</td>
      <td>${number(row.max_single_theme_pct)}%</td>
      <td>${number(row.min_cash_pct)}%</td>
    </tr>`).join("") || '<tr><td colspan="9">No client policy profiles configured.</td></tr>';
  $("#wealth-proposal-rows").innerHTML = (payload.proposal_matrix || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.profile?.profile_name || row.profile?.profile_id)}</strong></td>
      <td>${escapeHtml(row.review_status || "-")}</td>
      <td class="${toneOrEmpty(row.proposal_return_pct)}">${pctOrDash(row.proposal_return_pct)}</td>
      <td class="${toneOrEmpty(row.proposal_alpha_pct)}">${pctOrDash(row.proposal_alpha_pct)}</td>
      <td>${escapeHtml((row.allocations || []).map((allocation) => `${allocation.basket_id} ${allocation.target_weight}%`).join(" | "))}</td>
      <td>${escapeHtml((row.policy_warnings || []).join(" | ") || "-")}</td>
      <td>${escapeHtml((row.next_best_actions || []).join(" | "))}</td>
    </tr>`).join("") || '<tr><td colspan="7">No proposal profiles configured.</td></tr>';
  $("#wealth-review-rows").innerHTML = (payload.advisor_review_queue || []).map((row) => `
    <tr>
      <td><span class="pill risk-${row.priority === "high" ? "high" : "watchlist"}">${escapeHtml(row.priority || "-")}</span></td>
      <td>${escapeHtml(row.task_type || "-")}</td>
      <td><strong>${escapeHtml(row.subject || "-")}</strong></td>
      <td>${escapeHtml(row.source || "-")}</td>
      <td>${escapeHtml(row.detail || "-")}</td>
    </tr>`).join("") || '<tr><td colspan="5">No advisor review tasks for this window.</td></tr>';
  document.querySelectorAll("[data-command-copy]").forEach((button) =>
    button.addEventListener("click", () => copyWealthCommand(button.dataset.commandCopy))
  );
  enableSorting();
}

function renderExternalPortfolios() {
  const payload = state.externalPortfolios;
  if (!payload) return;
  const summary = payload.summary || {};
  $("#external-portfolio-status").textContent =
    `${number(summary.portfolio_count)} integrations | ${number(summary.active_count)} active | ${number(summary.awaiting_source_count)} awaiting source | ${number(summary.invalid_source_count)} invalid`;
  $("#external-portfolio-rows").innerHTML = (payload.portfolios || []).map((row) => {
    const source = row.source_status || {};
    return `
      <tr>
        <td><strong>${escapeHtml(row.portfolio_name || row.portfolio_id)}</strong><br><span class="muted">${escapeHtml(row.portfolio_id || "")}</span></td>
        <td>${escapeHtml(row.portfolio_type || "-")}</td>
        <td>${escapeHtml(row.effective_status || row.status || "-")}</td>
        <td>${escapeHtml(row.source_system || "-")}</td>
        <td>${escapeHtml(row.source_path || "-")}</td>
        <td>${escapeHtml(row.benchmark || "-")}</td>
        <td>${number(source.position_count)}</td>
        <td>${escapeHtml(source.latest_snapshot_date || source.latest_activity_date || "-")}</td>
        <td>${source.latest_weight_pct === null || source.latest_weight_pct === undefined ? "-" : `${number(source.latest_weight_pct)}%`}</td>
        <td>${escapeHtml([...(source.errors || []), ...(source.warnings || [])].join(" | ") || "-")}</td>
      </tr>`;
  }).join("") || '<tr><td colspan="10">No external portfolio integrations configured.</td></tr>';
  enableSorting();
}

function renderSystematicPortfolio(payload, prefix, options = {}) {
  if (!payload) return;
  const stats = payload.statistics || {};
  const benchmark = payload.benchmark_comparison || {};
  const methodology = payload.methodology || {};
  const macro = payload.macro_context || null;
  const selectedLabel = payload.inception_from_date && payload.inception_from_date !== payload.from_date ? "Selected window" : "Return";
  const latestSectors = payload.sector_exposure?.at(-1)?.sectors || [];
  const controlRows = (payload.positions || [])
    .filter((row) => row.drawdown_control_reason || Number(row.current_drawdown_pct || 0) <= -8 || Number(row.max_position_drawdown_pct || 0) <= -12);
  $(`#${prefix}-portfolio-window`).textContent = `${payload.from_date} to ${payload.to_date}`;
  $(`#${prefix}-portfolio-summary`).innerHTML = [
    [selectedLabel, pct(payload.return_pct), tone(payload.return_pct), `${money(payload.selected_gain_loss ?? payload.gain_loss)} selected gain / loss`],
    ...(payload.inception_return_pct === undefined ? [] : [
      ["Since inception", pct(payload.inception_return_pct), tone(payload.inception_return_pct), `${money(payload.inception_gain_loss)} since ${escapeHtml(payload.inception_from_date)}`],
    ]),
    ["Daily", pctOrDash(payload.daily_change_pct), toneOrEmpty(payload.daily_change_pct), "Ending close vs prior close"],
    ["5D", pctOrDash(payload.five_day_change_pct), toneOrEmpty(payload.five_day_change_pct), "Ending close vs five sessions prior"],
    ["Monthly", pctOrDash(payload.monthly_change_pct), toneOrEmpty(payload.monthly_change_pct), "Ending close vs monthly reference"],
    ["Current value", money(payload.current_value), "", `${money(payload.cash)} cash (${number(payload.cash_pct)}%)`],
    ["Positions", number(payload.position_count), "", `${number(stats.sector_count)} sectors`],
    ["Alpha vs SPY", pct(benchmark.alpha_pct), tone(benchmark.alpha_pct), `SPY ${pct(benchmark.benchmark_return_pct)}`],
    ["Max drawdown", pct(benchmark.max_drawdown_pct), tone(benchmark.max_drawdown_pct), `Volatility ${pct(benchmark.volatility_pct)}`],
    ["Turnover", `${number(stats.total_turnover_pct)}%`, "", `${number(stats.total_trades)} trades`],
    ["Closed win rate", pct(stats.closed_win_rate_pct), tone(stats.closed_win_rate_pct - 50), `Median ${pct(stats.median_closed_return_pct)}`],
    ["Concentration", `${number(stats.top_five_weight_pct)}%`, "", `Top five; largest sector ${number(stats.largest_sector_weight_pct)}%`],
    ...(macro ? [
      ["BoC macro", escapeHtml(macro.classification || "neutral"), toneOrEmpty((Number(macro.score || 0))), `${escapeHtml(macro.rate_bias || "neutral")} bias; ${number(macro.equity_exposure_multiplier || 1)}x pending-order guide`],
    ] : []),
    ...(options.showDrawdownControls ? [
      ["DD controls", number(stats.drawdown_control_actions), "", `${number(stats.open_positions_under_8pct_drawdown)} open names below -8% from peak`],
    ] : []),
  ].map(([label, value, className, note]) => `
    <article class="diagnostic-card">
      <p class="eyebrow">${escapeHtml(label)}</p>
      <p class="value ${className}">${value}</p>
      <p class="muted">${note}</p>
    </article>`).join("");
  $(`#${prefix}-methodology`).innerHTML = `
    <strong>Rules:</strong> ${escapeHtml(methodology.weighting || "-")}
    <br>${number(methodology.maximum_positions)} positions maximum; ${number(methodology.maximum_name_weight_pct)}% name cap; ${number(methodology.maximum_sector_weight_pct)}% sector cap; ${number(methodology.rebalance_band_pct)}% rebalance band; ${number(methodology.exit_buffer_sessions)}-session exit buffer.
    ${methodology.drawdown_overlay ? `<br><strong>Drawdown overlay:</strong> ${escapeHtml(methodology.drawdown_overlay.rule || "-")}` : ""}
    ${macro ? `<br><strong>Bank of Canada macro:</strong> ${escapeHtml(methodology.macro_overlay || "-")}` : ""}
    ${macro?.latest_statement ? `<br><strong>Latest BoC item:</strong> ${escapeHtml(macro.latest_statement.title || "-")} (${escapeHtml(macro.latest_statement.published_date || "-")})` : ""}
    <br><strong>Timing:</strong> ${escapeHtml(methodology.execution_convention || "-")}
    <br><strong>Universe:</strong> ${escapeHtml(methodology.universe_convention || "-")}`;
  $(`#${prefix}-portfolio-chart`).innerHTML = polyline(payload.series || [], "value");
  $(`#${prefix}-drawdown-chart`).innerHTML = drawdownPolyline(payload.series || []);
  const drawdownBody = $(`#${prefix}-drawdown-rows`);
  if (drawdownBody) {
    drawdownBody.innerHTML = controlRows.map((row) => `
      <tr>
        <td><strong>${escapeHtml(row.ticker)}</strong></td>
        <td class="${toneOrEmpty(row.current_drawdown_pct)}">${pctOrDash(row.current_drawdown_pct)}</td>
        <td class="${toneOrEmpty(row.max_position_drawdown_pct)}">${pctOrDash(row.max_position_drawdown_pct)}</td>
        <td class="${toneOrEmpty(row.average_daily_drawdown_pct)}">${pctOrDash(row.average_daily_drawdown_pct)}</td>
        <td class="${toneOrEmpty(row.average_drawdown_sell_point_pct)}">${pctOrDash(row.average_drawdown_sell_point_pct)}</td>
        <td>${escapeHtml(row.drawdown_control_reason || "Monitoring drawdown")}</td>
      </tr>`).join("") || '<tr><td colspan="6">No current holdings are triggering drawdown controls.</td></tr>';
  }
  $(`#${prefix}-holding-rows`).innerHTML = (payload.positions || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.ticker)}</strong></td><td>${escapeHtml(row.sector || "-")}</td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.model_score)}</td>
      <td>${number(row.portfolio_weight_pct)}%</td><td>${money(row.current_value)}</td>
      <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td><td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
    </tr>`).join("") || '<tr><td colspan="8">No current holdings.</td></tr>';
  $(`#${prefix}-pending-rows`).innerHTML = (payload.pending_next_close_orders || []).map((row) => `
    <tr><td>${escapeHtml(row.action)}</td><td><strong>${escapeHtml(row.ticker)}</strong></td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.model_score)}</td>
      <td>${number(row.target_weight_pct)}%</td><td>${money(row.usd_amount)}${row.macro_adjusted_usd_amount === undefined ? "" : `<br><span class="muted">BoC guide ${money(row.macro_adjusted_usd_amount)}</span>`}</td>
      <td>${escapeHtml(row.signal_observed_date)}</td><td>${escapeHtml(row.reason || "-")}</td></tr>`).join("") || '<tr><td colspan="8">No next-close orders.</td></tr>';
  $(`#${prefix}-sector-rows`).innerHTML = latestSectors.map((row) => `
    <tr><td>${escapeHtml(row.sector)}</td><td>${money(row.value)}</td><td>${number(row.weight_pct)}%</td></tr>`).join("") || '<tr><td colspan="3">No sector exposure.</td></tr>';
  $(`#${prefix}-rebalance-rows`).innerHTML = [...(payload.daily_rebalances || [])].reverse().map((row) => `
    <tr><td>${escapeHtml(row.date)}</td><td>${escapeHtml(row.signal_observed_date)}</td>
      <td>${number(row.buys)}</td><td>${number(row.sells)}</td><td>${money(row.traded_value)}</td>
      <td>${number(row.turnover_pct)}%</td><td>${number(row.position_count)}</td><td>${number(row.cash_pct)}%</td></tr>`).join("");
  $(`#${prefix}-trade-rows`).innerHTML = [...(payload.trade_ledger || [])].reverse().map((row) => `
    <tr><td>${escapeHtml(row.date)}</td><td>${escapeHtml(row.signal_observed_date)}</td>
      <td>${escapeHtml(row.action)}</td><td><strong>${escapeHtml(row.ticker)}</strong></td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.model_score)}</td>
      <td>${money(row.usd_amount)}</td><td>${number(row.target_weight_pct)}%</td>
      <td class="${toneOrEmpty(row.realized_gain_loss)}">${row.realized_gain_loss === null || row.realized_gain_loss === undefined ? "-" : money(row.realized_gain_loss)}</td>
      <td>${escapeHtml(row.reason || "-")}</td></tr>`).join("");
  $(`#${prefix}-warning-list`).innerHTML = (payload.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  $(`#${prefix}-portfolio-content`).classList.remove("hidden");
  $(`#${prefix}-portfolio-status`).textContent = `Loaded ${number(stats.available_universe_count)} point-in-time eligible stock histories.`;
  enableSorting();
}

function renderModelPortfolio() {
  renderSystematicPortfolio(state.modelPortfolio, "model");
}

function renderModelPortfolioV2() {
  renderSystematicPortfolio(state.modelPortfolioV2, "model2", { showDrawdownControls: true });
}

function renderModelPortfolioV3() {
  renderSystematicPortfolio(state.modelPortfolioV3, "model3", { showDrawdownControls: true });
}

function renderModelPortfolioV4() {
  renderSystematicPortfolio(state.modelPortfolioV4, "model4", { showDrawdownControls: true });
}

async function loadModelPortfolio(force = false) {
  const fromDate = $("#from-date").value;
  const toDate = $("#to-date").value;
  if (!toDate) return;
  const requestKey = `${fromDate || ""}|${toDate}`;
  if (!force && state.modelPortfolio && state.modelPortfolioToDate === requestKey) {
    renderModelPortfolio();
    return;
  }
  const button = $("#reload-model-portfolio");
  button.disabled = true;
  $("#model-portfolio-status").textContent = "Replaying daily point-in-time decisions from 2026-01-31...";
  try {
    state.modelPortfolio = await fetchJson(`/api/model-portfolio?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`);
    state.modelPortfolioToDate = requestKey;
    renderModelPortfolio();
  } catch (error) {
    $("#model-portfolio-status").textContent = `Model portfolio failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function loadModelPortfolioV2(force = false) {
  const fromDate = $("#from-date").value;
  const toDate = $("#to-date").value;
  if (!toDate) return;
  const requestKey = `${fromDate || ""}|${toDate}`;
  if (!force && state.modelPortfolioV2 && state.modelPortfolioV2ToDate === requestKey) {
    renderModelPortfolioV2();
    return;
  }
  const button = $("#reload-model2-portfolio");
  button.disabled = true;
  $("#model2-portfolio-status").textContent = "Replaying drawdown-adjusted daily decisions from 2026-01-31...";
  try {
    state.modelPortfolioV2 = await fetchJson(`/api/model-portfolio-v2?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`);
    state.modelPortfolioV2ToDate = requestKey;
    renderModelPortfolioV2();
  } catch (error) {
    $("#model2-portfolio-status").textContent = `Model 2.0 failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function loadModelPortfolioV3(force = false) {
  const fromDate = $("#from-date").value;
  const toDate = $("#to-date").value;
  if (!toDate) return;
  const requestKey = `${fromDate || ""}|${toDate}`;
  if (!force && state.modelPortfolioV3 && state.modelPortfolioV3ToDate === requestKey) {
    renderModelPortfolioV3();
    return;
  }
  const button = $("#reload-model3-portfolio");
  button.disabled = true;
  $("#model3-portfolio-status").textContent = "Replaying average-drawdown EOD decisions from 2026-01-31...";
  try {
    state.modelPortfolioV3 = await fetchJson(`/api/model-portfolio-v3?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`);
    state.modelPortfolioV3ToDate = requestKey;
    renderModelPortfolioV3();
  } catch (error) {
    $("#model3-portfolio-status").textContent = `Model 3.0 failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function loadModelPortfolioV4(force = false) {
  const fromDate = $("#from-date").value;
  const toDate = $("#to-date").value;
  if (!toDate) return;
  const requestKey = `${fromDate || ""}|${toDate}`;
  if (!force && state.modelPortfolioV4 && state.modelPortfolioV4ToDate === requestKey) {
    renderModelPortfolioV4();
    return;
  }
  const button = $("#reload-model4-portfolio");
  button.disabled = true;
  $("#model4-portfolio-status").textContent = "Replaying intraday-proxy drawdown decisions from 2026-01-31...";
  try {
    state.modelPortfolioV4 = await fetchJson(`/api/model-portfolio-v4?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`);
    state.modelPortfolioV4ToDate = requestKey;
    renderModelPortfolioV4();
  } catch (error) {
    $("#model4-portfolio-status").textContent = `Model 4.0 failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderDayRotationPortfolio() {
  const payload = state.dayRotationPortfolio;
  if (!payload) return;
  const stats = payload.statistics || {};
  const benchmark = payload.benchmark_comparison || {};
  const methodology = payload.methodology || {};
  const latestSectors = payload.sector_exposure?.at(-1)?.sectors || [];
  $("#rotation-window").textContent = `${payload.from_date} to ${payload.to_date}`;
  $("#rotation-summary").innerHTML = [
    ["Return", pct(payload.return_pct), tone(payload.return_pct), `${money(payload.gain_loss)} gain / loss`],
    ["Current value", money(payload.current_value), "", `${money(payload.cash)} cash (${number(payload.cash_pct)}%)`],
    ["Positions", number(payload.position_count), "", `${number(stats.sector_count)} sectors`],
    ["Alpha vs SPY", pct(benchmark.alpha_pct), tone(benchmark.alpha_pct), `SPY ${pct(benchmark.benchmark_return_pct)}`],
    ["Max drawdown", pct(benchmark.max_drawdown_pct), tone(benchmark.max_drawdown_pct), `Volatility ${pct(benchmark.volatility_pct)}`],
    ["Turnover", `${number(stats.total_turnover_pct)}%`, "", `${number(stats.total_trades)} trades`],
    ["Closed win rate", pct(stats.closed_win_rate_pct), tone(stats.closed_win_rate_pct - 50), `Median ${pct(stats.median_closed_return_pct)}`],
    ["Concentration", `${number(stats.top_five_weight_pct)}%`, "", `Top five; largest sector ${number(stats.largest_sector_weight_pct)}%`],
  ].map(([label, value, className, note]) => `
    <article class="diagnostic-card">
      <p class="eyebrow">${escapeHtml(label)}</p>
      <p class="value ${className}">${value}</p>
      <p class="muted">${note}</p>
    </article>`).join("");
  $("#rotation-methodology").innerHTML = `
    <strong>Rules:</strong> ${escapeHtml(methodology.weighting || "-")}
    <br>${number(methodology.maximum_positions)} positions maximum; ${number(methodology.maximum_name_weight_pct)}% name cap; ${number(methodology.maximum_sector_weight_pct)}% sector cap; ${number(methodology.rebalance_band_pct)}% rebalance band.
    <br><strong>Timing:</strong> ${escapeHtml(methodology.execution_convention || "-")}
    <br><strong>Universe:</strong> ${escapeHtml(methodology.universe_convention || "-")}`;
  $("#rotation-chart").innerHTML = polyline(payload.series || [], "value");
  $("#rotation-drawdown-chart").innerHTML = drawdownPolyline(payload.series || []);
  $("#rotation-holding-rows").innerHTML = (payload.positions || []).map((row) => `
    <tr><td><strong>${escapeHtml(row.ticker)}</strong></td><td>${escapeHtml(row.sector || "-")}</td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.rotation_score)}</td>
      <td>${number(row.portfolio_weight_pct)}%</td><td>${money(row.current_value)}</td>
      <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td><td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td></tr>`).join("") || '<tr><td colspan="8">No current holdings.</td></tr>';
  $("#rotation-pending-rows").innerHTML = (payload.pending_next_close_orders || []).map((row) => `
    <tr><td>${escapeHtml(row.action)}</td><td><strong>${escapeHtml(row.ticker)}</strong></td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.rotation_score)}</td>
      <td>${number(row.target_weight_pct)}%</td><td>${money(row.usd_amount)}</td>
      <td>${escapeHtml(row.signal_observed_date)}</td><td>${escapeHtml(row.reason || "-")}</td></tr>`).join("") || '<tr><td colspan="8">No next-close orders.</td></tr>';
  $("#rotation-sector-rows").innerHTML = latestSectors.map((row) => `
    <tr><td>${escapeHtml(row.sector)}</td><td>${money(row.value)}</td><td>${number(row.weight_pct)}%</td></tr>`).join("") || '<tr><td colspan="3">No sector exposure.</td></tr>';
  $("#rotation-rebalance-rows").innerHTML = [...(payload.daily_rebalances || [])].reverse().map((row) => `
    <tr><td>${escapeHtml(row.date)}</td><td>${escapeHtml(row.signal_observed_date)}</td>
      <td>${number(row.buys)}</td><td>${number(row.sells)}</td><td>${money(row.traded_value)}</td>
      <td>${number(row.turnover_pct)}%</td><td>${number(row.position_count)}</td><td>${number(row.cash_pct)}%</td></tr>`).join("");
  $("#rotation-trade-rows").innerHTML = [...(payload.trade_ledger || [])].reverse().map((row) => `
    <tr><td>${escapeHtml(row.date)}</td><td>${escapeHtml(row.signal_observed_date)}</td>
      <td>${escapeHtml(row.action)}</td><td><strong>${escapeHtml(row.ticker)}</strong></td>
      <td>${escapeHtml(row.entry_signal || "-")}</td><td>${number(row.rotation_score)}</td>
      <td>${money(row.usd_amount)}</td><td>${number(row.target_weight_pct)}%</td>
      <td class="${toneOrEmpty(row.realized_gain_loss)}">${row.realized_gain_loss === null || row.realized_gain_loss === undefined ? "-" : money(row.realized_gain_loss)}</td>
      <td>${escapeHtml(row.reason || "-")}</td></tr>`).join("");
  $("#rotation-warning-list").innerHTML = (payload.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  $("#rotation-content").classList.remove("hidden");
  $("#rotation-status").textContent = `Loaded ${number(stats.available_universe_count)} point-in-time eligible stock histories.`;
  enableSorting();
}

async function loadDayRotationPortfolio(force = false) {
  const toDate = $("#to-date").value;
  if (!toDate) return;
  if (!force && state.dayRotationPortfolio && state.dayRotationToDate === toDate) {
    renderDayRotationPortfolio();
    return;
  }
  const button = $("#reload-rotation");
  button.disabled = true;
  $("#rotation-status").textContent = "Replaying daily next-close rotation decisions from 2026-01-31...";
  try {
    state.dayRotationPortfolio = await fetchJson(`/api/day-rotation-portfolio?to_date=${encodeURIComponent(toDate)}`);
    state.dayRotationToDate = toDate;
    renderDayRotationPortfolio();
  } catch (error) {
    $("#rotation-status").textContent = `Daily rotation failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function populateRiskPortfolioOptions() {
  if (!state.overview) return;
  const primary = (state.overview.traders || [])
    .filter((row) => !isLowPriorityPortfolio(row))
    .map((row) => ({ value: row.investor, label: row.investor }));
  const options = [
    { value: "systematic-model-portfolio", label: "Systematic Model Portfolio" },
    { value: "systematic-model-portfolio-2", label: "Systematic Model Portfolio 2.0" },
    { value: "systematic-model-portfolio-3", label: "Systematic Model Portfolio 3.0" },
    { value: "systematic-model-portfolio-4", label: "Systematic Model Portfolio 4.0" },
    { value: "daily-eod-rotation-portfolio", label: "Daily EOD Rotation Portfolio" },
    ...primary,
  ];
  [$("#risk-portfolio-select"), $("#performance-portfolio-select")].forEach((select) => {
    if (!select) return;
    const selected = select.value;
    select.innerHTML = options.map((row) => `<option value="${escapeHtml(row.value)}">${escapeHtml(row.label)}</option>`).join("");
    if (options.some((row) => row.value === selected)) select.value = selected;
  });
}

function renderRiskPortfolio() {
  const payload = state.riskPortfolio;
  if (!payload) return;
  const metrics = payload.metrics || {};
  const quality = payload.data_quality || {};
  $("#risk-summary").innerHTML = [
    ["Volatility", pct(metrics.annualized_volatility_pct), "", "Annualized close-to-close"],
    ["Downside deviation", pct(metrics.downside_deviation_pct), "", "Negative sessions only"],
    ["Maximum drawdown", pct(metrics.maximum_drawdown_pct), tone(metrics.maximum_drawdown_pct), `${number(metrics.longest_recovery_sessions)} recovery sessions`],
    ["Current drawdown", pct(metrics.current_drawdown_pct), tone(metrics.current_drawdown_pct), `${number(metrics.current_underwater_sessions)} sessions underwater`],
    ["Largest position", `${number(metrics.largest_position_weight_pct)}%`, "", `${number(metrics.position_count)} current positions`],
    ["Top five", `${number(metrics.top_five_weight_pct)}%`, "", `Effective holdings ${number(metrics.effective_number_of_holdings)}`],
    ["Beta", metrics.beta === null || metrics.beta === undefined ? "-" : number(metrics.beta), "", `${number(metrics.aligned_sessions)} aligned sessions`],
    ["Tracking error", metrics.tracking_error_pct === null || metrics.tracking_error_pct === undefined ? "-" : pct(metrics.tracking_error_pct), "", `Confidence: ${quality.confidence || "unknown"}`],
  ].map(([label, value, className, note]) => `
    <article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p>
      <p class="value ${className}">${value}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#risk-drawdown-chart").innerHTML = polyline(payload.drawdown_series || [], "drawdown_pct");
  $("#risk-alerts").innerHTML = (payload.alerts || []).map((alert) => `
    <article class="diagnostic-card"><p class="eyebrow">${escapeHtml(alert.severity)}</p>
      <p><strong>${escapeHtml(String(alert.type || "risk").replaceAll("_", " "))}</strong></p>
      <p class="muted">${escapeHtml(alert.message)}</p></article>`).join("") || '<p class="muted">No configured risk thresholds are currently breached.</p>';
  $("#risk-sector-rows").innerHTML = (payload.sector_concentration || []).map((row) => `
    <tr><td>${escapeHtml(row.sector)}</td><td>${money(row.value)}</td><td>${number(row.weight_pct)}%</td></tr>`).join("") || '<tr><td colspan="3">No sector detail available.</td></tr>';
  $("#risk-data-quality").innerHTML = `
    <p><strong>Confidence:</strong> ${escapeHtml(quality.confidence || "unknown")}</p>
    <p class="muted">As of ${escapeHtml(payload.as_of)} | ${number(quality.series_points)} series points | ${number(quality.position_records)} positions</p>
    <h4>Warnings</h4><ul class="wealth-list">${(quality.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>None</li>"}</ul>
    <h4>Assumptions</h4><ul class="wealth-list">${(quality.assumptions || []).map((assumption) => `<li>${escapeHtml(assumption)}</li>`).join("")}</ul>`;
  $("#risk-content").classList.remove("hidden");
  $("#risk-status").textContent = `${payload.portfolio_name}: ${payload.from_date} to ${payload.to_date} in ${payload.base_currency}.`;
  enableSorting();
}

async function loadRiskPortfolio(force = false) {
  const select = $("#risk-portfolio-select");
  if (!select?.value || !$("#from-date").value || !$("#to-date").value) return;
  const params = new URLSearchParams(query());
  params.set("portfolio", select.value);
  const requestKey = params.toString();
  if (!force && state.riskPortfolio && state.riskRequestKey === requestKey) {
    renderRiskPortfolio();
    return;
  }
  const button = $("#reload-risk");
  button.disabled = true;
  $("#risk-status").textContent = `Calculating risk for ${select.options[select.selectedIndex]?.text || select.value}...`;
  try {
    state.riskPortfolio = await fetchJson(`/api/wealth/risk?${requestKey}`);
    state.riskRequestKey = requestKey;
    state.riskCorrelation = null;
    state.riskCorrelationRequestKey = null;
    state.riskScenarios = null;
    state.riskScenarioRequestKey = null;
    $("#risk-correlation-content").classList.add("hidden");
    $("#risk-correlation-status").textContent = "";
    $("#risk-scenario-content").classList.add("hidden");
    $("#risk-scenario-status").textContent = "";
    renderRiskPortfolio();
  } catch (error) {
    $("#risk-status").textContent = `Risk calculation failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderRiskCorrelation() {
  const payload = state.riskCorrelation;
  if (!payload) return;
  const quality = payload.data_quality || {};
  $("#risk-correlation-summary").innerHTML = [
    ["Positions analyzed", number(payload.selected_position_count), `${number(payload.total_position_count)} total positions`],
    ["Average correlation", payload.average_correlation === null ? "-" : number(payload.average_correlation), `${number(quality.valid_pair_count)} valid pairs`],
    ["Unavailable pairs", number(quality.unavailable_pair_count), `${number(payload.minimum_observations)} observations required`],
    ["Diversification", payload.diversification_warning ? "Review" : "No threshold breach", payload.diversification_warning || "Historical pair correlations are below configured warning thresholds."],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value">${escapeHtml(value)}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#risk-correlation-rows").innerHTML = (payload.pairwise_correlations || []).map((row) => `
    <tr><td>${escapeHtml(row.left)}</td><td>${escapeHtml(row.right)}</td><td>${row.correlation === null ? "-" : number(row.correlation)}</td><td>${number(row.observations)}</td><td>${escapeHtml(row.warning || "available")}</td></tr>`).join("") || '<tr><td colspan="5">No position pairs available.</td></tr>';
  $("#risk-correlation-content").classList.remove("hidden");
  $("#risk-correlation-status").textContent = (quality.warnings || []).join(" | ") || "Correlation analysis loaded.";
  enableSorting();
}

async function loadRiskCorrelation(force = false) {
  const select = $("#risk-portfolio-select");
  if (!select?.value) return;
  const params = new URLSearchParams(query());
  params.set("portfolio", select.value);
  const requestKey = params.toString();
  if (!force && state.riskCorrelation && state.riskCorrelationRequestKey === requestKey) {
    renderRiskCorrelation();
    return;
  }
  const button = $("#load-risk-correlation");
  button.disabled = true;
  $("#risk-correlation-status").textContent = "Loading and aligning top-position price histories...";
  try {
    state.riskCorrelation = await fetchJson(`/api/wealth/correlation?${requestKey}`);
    state.riskCorrelationRequestKey = requestKey;
    renderRiskCorrelation();
  } catch (error) {
    $("#risk-correlation-status").textContent = `Correlation analysis failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderRiskScenarios() {
  const payload = state.riskScenarios;
  if (!payload) return;
  const quality = payload.data_quality || {};
  const scenarios = payload.scenarios || [];
  const worst = [...scenarios].sort((left, right) => Number(left.estimated_impact_pct) - Number(right.estimated_impact_pct))[0];
  $("#risk-scenario-summary").innerHTML = [
    ["Current value", money(payload.total_current_value), `${number(payload.position_count)} positions analyzed`],
    ["Worst defined shock", worst ? pct(worst.estimated_impact_pct) : "-", worst?.name || "No scenario result"],
    ["Method", "Linear", payload.calculation_version || "first-order scenario estimate"],
    ["Behavior", "Read only", quality.write_behavior || "No orders or ledger writes"],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value ${String(value).startsWith("-") ? "negative" : ""}">${escapeHtml(value)}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#risk-scenario-rows").innerHTML = scenarios.map((row) => {
    const contributors = (row.largest_affected_positions || []).slice(0, 3)
      .map((position) => `${position.ticker} ${money(position.estimated_dollar_impact)}`).join(", ") || "None classified";
    return `<tr><td title="${escapeHtml(row.description)}">${escapeHtml(row.name)}</td><td class="${tone(row.estimated_impact_pct)}">${pct(row.estimated_impact_pct)}</td><td>${money(row.estimated_dollar_impact)}</td><td>${number(row.affected_position_count)}</td><td>${escapeHtml(contributors)}</td></tr>`;
  }).join("") || '<tr><td colspan="5">No scenario results available.</td></tr>';
  $("#risk-scenario-quality").innerHTML = `<h4>Data Quality &amp; Assumptions</h4><ul class="wealth-list">${(quality.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>No warnings</li>"}${(payload.assumptions || []).map((assumption) => `<li>${escapeHtml(assumption)}</li>`).join("")}</ul>`;
  $("#risk-scenario-content").classList.remove("hidden");
  $("#risk-scenario-status").textContent = `Scenario estimates as of ${payload.as_of} in ${payload.base_currency}.`;
  enableSorting();
}

async function loadRiskScenarios(force = false) {
  const select = $("#risk-portfolio-select");
  if (!select?.value) return;
  const params = new URLSearchParams(query());
  params.set("portfolio", select.value);
  const requestKey = params.toString();
  if (!force && state.riskScenarios && state.riskScenarioRequestKey === requestKey) {
    renderRiskScenarios();
    return;
  }
  const button = $("#load-risk-scenarios");
  button.disabled = true;
  $("#risk-scenario-status").textContent = "Applying defined shocks to current holdings...";
  try {
    state.riskScenarios = await fetchJson(`/api/wealth/scenarios?${requestKey}`);
    state.riskScenarioRequestKey = requestKey;
    renderRiskScenarios();
  } catch (error) {
    $("#risk-scenario-status").textContent = `Scenario analysis failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function allocationRows(rows, label = "name") {
  return (rows || []).map((row) => `<tr><td>${escapeHtml(row[label] || "-")}</td><td>${money(row.current_value)}</td><td>${number(row.weight_pct)}%</td></tr>`).join("");
}

function renderWealthAllocation() {
  const payload = state.wealthAllocation;
  if (!payload) return;
  const concentration = payload.concentration || {};
  const coverage = payload.metadata_coverage || {};
  const quality = payload.data_quality || {};
  $("#allocation-summary").innerHTML = [
    ["Tracked value", money(payload.total_current_value), `${number(payload.included_portfolio_count)} primary portfolios`],
    ["Unique securities", number(payload.unique_security_count), `${number(payload.position_record_count)} position records`],
    ["Largest security", `${number(concentration.top_position_weight_pct)}%`, "Combined overlap weight"],
    ["Top five", `${number(concentration.top_five_weight_pct)}%`, "Combined overlap weight"],
    ["Effective holdings", number(concentration.effective_number_of_holdings), "Concentration-adjusted count"],
    ["Metadata coverage", `${number(coverage.complete_value_pct)}%`, `Type ${number(coverage.asset_type_value_pct)}% | Sector ${number(coverage.sector_value_pct)}% | Currency ${number(coverage.currency_value_pct)}%`],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value">${value}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#allocation-note").textContent = payload.view_note || "";
  $("#allocation-alerts").innerHTML = (payload.concentration_alerts || []).map((alert) => `
    <article class="diagnostic-card"><p class="eyebrow">${escapeHtml(alert.severity)}</p><p><strong>${escapeHtml(String(alert.code || "allocation").replaceAll("_", " "))}</strong></p><p class="muted">${escapeHtml(alert.message)}</p><p class="muted">${escapeHtml(alert.decision)}</p></article>`).join("") || '<p class="muted">No configured allocation thresholds are breached.</p>';
  $("#allocation-data-quality").innerHTML = `<p><strong>As of:</strong> ${escapeHtml(payload.as_of)} | <strong>Completeness:</strong> ${number(quality.completeness_pct)}%</p><ul class="wealth-list">${(quality.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>No warnings</li>"}</ul>`;
  const allocation = payload.allocation || {};
  $("#allocation-portfolio-rows").innerHTML = allocationRows(allocation.portfolio_strategy);
  $("#allocation-sector-rows").innerHTML = allocationRows(allocation.sector);
  $("#allocation-type-rows").innerHTML = allocationRows(allocation.asset_type);
  $("#allocation-currency-rows").innerHTML = allocationRows(allocation.currency);
  $("#allocation-security-rows").innerHTML = (allocation.security || []).map((row) => `
    <tr><td><strong>${escapeHtml(row.ticker)}</strong></td><td>${escapeHtml(row.asset_type)}</td><td>${escapeHtml(row.sector)}</td><td>${escapeHtml(row.currency)}</td><td>${money(row.current_value)}</td><td>${number(row.weight_pct)}%</td></tr>`).join("") || '<tr><td colspan="6">No security allocation available.</td></tr>';
  $("#allocation-content").classList.remove("hidden");
  $("#allocation-status").textContent = `${payload.from_date} to ${payload.as_of}; ${payload.base_currency} research collection.`;
  enableSorting();
}

async function loadWealthAllocation(force = false) {
  if (!$("#from-date").value || !$("#to-date").value) return;
  const requestKey = query();
  if (!force && state.wealthAllocation && state.wealthAllocationRequestKey === requestKey) {
    renderWealthAllocation();
    return;
  }
  const button = $("#reload-allocation");
  button.disabled = true;
  $("#allocation-status").textContent = "Aggregating current values and overlap across primary tracked portfolios...";
  try {
    state.wealthAllocation = await fetchJson(`/api/wealth/allocation?${requestKey}`);
    state.wealthAllocationRequestKey = requestKey;
    renderWealthAllocation();
  } catch (error) {
    $("#allocation-status").textContent = `Allocation calculation failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderWealthPerformance() {
  const payload = state.wealthPerformance;
  if (!payload) return;
  const summary = payload.summary || {};
  const quality = payload.data_quality || {};
  const fixed = payload.fixed_period_changes || {};
  $("#performance-summary").innerHTML = [
    ["Return", pct(summary.return_pct), tone(summary.return_pct), `${money(summary.gain_loss)} gain / loss`],
    ["Current value", money(summary.current_value), "", `${money(summary.initial_value)} opening value`],
    ["Alpha", pct(summary.alpha_pct), tone(summary.alpha_pct), `${summary.benchmark || "SPY"} ${pct(summary.benchmark_return_pct)}`],
    ["Realized", money(summary.realized_gain_loss), tone(summary.realized_gain_loss), "Closed positions"],
    ["Unrealized", money(summary.unrealized_gain_loss), tone(summary.unrealized_gain_loss), "Current positions"],
    ["Residual", money(summary.reconciliation_residual), tone(-Math.abs(summary.reconciliation_residual || 0)), "Unexplained by position detail"],
    ["Daily / 5D", `${pctOrDash(fixed.daily_change_pct)} / ${pctOrDash(fixed.five_day_change_pct)}`, "", "Ending-date changes"],
    ["Monthly", pctOrDash(fixed.monthly_change_pct), toneOrEmpty(fixed.monthly_change_pct), `Confidence: ${quality.confidence || "unknown"}`],
  ].map(([label, value, className, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value ${className}">${value}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#performance-chart").innerHTML = polyline(payload.series || [], "value");
  $("#performance-data-quality").innerHTML = `<p><strong>Confidence:</strong> ${escapeHtml(quality.confidence || "unknown")}</p><p class="muted">${number(quality.series_points)} series points; ${number(quality.open_position_records)} open and ${number(quality.closed_position_records)} closed position records.</p><ul class="wealth-list">${(quality.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("") || "<li>No warnings</li>"}</ul>`;
  $("#performance-contribution-rows").innerHTML = (payload.contributions || []).map((row) => `
    <tr><td><strong>${escapeHtml(row.ticker)}</strong></td><td>${escapeHtml(row.status)}</td><td>${money(row.current_value)}</td><td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td><td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td><td class="${tone(row.contribution_pct)}">${pct(row.contribution_pct)}</td></tr>`).join("") || '<tr><td colspan="6">No position contribution detail available.</td></tr>';
  $("#performance-content").classList.remove("hidden");
  $("#performance-status").textContent = `${payload.portfolio_name}: ${payload.from_date} to ${payload.to_date} in ${payload.base_currency}.`;
  enableSorting();
}

async function loadWealthPerformance(force = false) {
  const select = $("#performance-portfolio-select");
  if (!select?.value || !$("#from-date").value || !$("#to-date").value) return;
  const params = new URLSearchParams(query());
  params.set("portfolio", select.value);
  const requestKey = params.toString();
  if (!force && state.wealthPerformance && state.wealthPerformanceRequestKey === requestKey) {
    renderWealthPerformance();
    return;
  }
  const button = $("#reload-performance");
  button.disabled = true;
  $("#performance-status").textContent = `Calculating performance for ${select.options[select.selectedIndex]?.text || select.value}...`;
  try {
    state.wealthPerformance = await fetchJson(`/api/wealth/performance?${requestKey}`);
    state.wealthPerformanceRequestKey = requestKey;
    renderWealthPerformance();
  } catch (error) {
    $("#performance-status").textContent = `Performance calculation failed: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function selectedRebalanceProfile() {
  const profileId = $("#rebalance-profile")?.value;
  return (state.rebalanceProfiles?.profiles || []).find((row) => row.profile_id === profileId);
}

function renderRebalanceInputs() {
  const profile = selectedRebalanceProfile();
  if (!profile) return;
  $("#rebalance-input-rows").innerHTML = (profile.target_allocations || []).map((row) => `
    <tr><td><strong>${escapeHtml(row.basket_id)}</strong><br><span class="muted">${escapeHtml(row.allocation_role || "")}</span></td><td>${number(row.target_weight)}%</td><td><input class="rebalance-current-weight" data-basket-id="${escapeHtml(row.basket_id)}" type="number" min="0" max="100" step="0.1" value="${number(row.target_weight)}" /></td></tr>`).join("");
  $("#rebalance-input-wrap").classList.remove("hidden");
  $("#rebalance-content").classList.add("hidden");
  $("#rebalance-status").textContent = `${profile.profile_name}: edit current weights so they total 100%, then build the draft preview.`;
}

async function loadRebalanceProfiles() {
  if (!state.rebalanceProfiles) {
    state.rebalanceProfiles = await fetchJson("/api/wealth/rebalance/profiles");
  }
  const select = $("#rebalance-profile");
  const previous = select.value;
  select.innerHTML = (state.rebalanceProfiles.profiles || []).map((row) => `<option value="${escapeHtml(row.profile_id)}">${escapeHtml(row.profile_name)}</option>`).join("");
  if ([...(select.options || [])].some((option) => option.value === previous)) select.value = previous;
  renderRebalanceInputs();
}

function renderRebalancePreview() {
  const payload = state.rebalancePreview;
  if (!payload) return;
  $("#rebalance-summary").innerHTML = [
    ["Portfolio value", money(payload.portfolio_value), payload.profile?.profile_name || ""],
    ["Turnover", `${number(payload.estimated_one_way_turnover_pct)}%`, payload.exact_target ? "Exact-target comparison" : "Boundary method"],
    ["Net funding", money(payload.net_dollar_change), "Should reconcile near zero"],
    ["Status", payload.status, "Human review required"],
  ].map(([label, value, note]) => `<article class="diagnostic-card"><p class="eyebrow">${escapeHtml(label)}</p><p class="value">${escapeHtml(value)}</p><p class="muted">${escapeHtml(note)}</p></article>`).join("");
  $("#rebalance-methodology").textContent = payload.methodology || "";
  $("#rebalance-result-rows").innerHTML = (payload.allocations || []).map((row) => `
    <tr><td><strong>${escapeHtml(row.basket_id)}</strong></td><td>${number(row.current_weight_pct)}%</td><td>${number(row.target_weight_pct)}%</td><td>${number(row.lower_band_pct)}%</td><td>${number(row.upper_band_pct)}%</td><td class="${tone(-Math.abs(row.drift_pct || 0))}">${pct(row.drift_pct)}</td><td>${escapeHtml(row.action)}</td><td>${number(row.proposed_weight_pct)}%</td><td class="${tone(row.proposed_dollar_change)}">${money(row.proposed_dollar_change)}</td></tr>`).join("");
  $("#rebalance-warning-list").innerHTML = (payload.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  $("#rebalance-content").classList.remove("hidden");
  $("#rebalance-status").textContent = "Draft preview calculated. Review every assumption before external use.";
  enableSorting();
}

async function runRebalancePreview() {
  const profile = selectedRebalanceProfile();
  if (!profile) return;
  const currentAllocations = [...document.querySelectorAll(".rebalance-current-weight")].map((input) => ({
    basket_id: input.dataset.basketId,
    current_weight: Number(input.value),
  }));
  $("#run-rebalance").disabled = true;
  $("#rebalance-status").textContent = "Validating policy bands and building a self-financing draft...";
  try {
    state.rebalancePreview = await fetchJson("/api/wealth/rebalance/preview", jsonRequest("POST", {
      profile_id: profile.profile_id,
      current_allocations: currentAllocations,
      portfolio_value: Number($("#rebalance-value").value),
      exact_target: $("#rebalance-exact-target").checked,
    }));
    renderRebalancePreview();
  } catch (error) {
    $("#rebalance-status").textContent = `Rebalance preview failed: ${error.message}`;
  } finally {
    $("#run-rebalance").disabled = false;
  }
}

async function copyWealthCommand(commandId) {
  const command = (state.wealthOperations?.ai_command_workbench || [])
    .find((row) => row.command_id === commandId);
  if (!command) return;
  try {
    await navigator.clipboard.writeText(command.generated_prompt || "");
    $("#wealth-command-status").textContent = `Copied ${command.title}.`;
  } catch {
    $("#wealth-command-status").textContent = `Could not access clipboard. Select the prompt text manually.`;
  }
}

function boolLabel(value) {
  return value ? "yes" : "no";
}

function universeStatusText() {
  if (!state.universe) return "";
  const counts = state.universe.status_counts || {};
  return `${state.universe.total} assets | active ${counts.active || 0}, candidate ${counts.candidate || 0}, archived ${counts.archived || 0}`;
}

function renderUniverseControls() {
  const statuses = state.universe?.statuses || [];
  $("#asset-status").innerHTML = statuses
    .map((status) => `<option value="${status}"${status === "candidate" ? " selected" : ""}>${status}</option>`)
    .join("");
}

function renderUniverse() {
  if (!state.universe || !state.benchmarks || !state.strategies || !state.baskets || !state.research) return;
  $("#universe-status").textContent = universeStatusText();
  $("#asset-universe-rows").innerHTML = state.universe.assets
    .map(
      (row) => `
        <tr>
          <td><strong>${escapeHtml(row.ticker)}</strong></td>
          <td>${escapeHtml(row.asset_type)}</td>
          <td>${escapeHtml(row.status)}</td>
          <td>${escapeHtml(row.sector || "-")}</td>
          <td>${escapeHtml(row.theme || "-")}</td>
          <td>${boolLabel(row.strategy_eligible)}</td>
          <td>${boolLabel(row.watchlist_eligible)}</td>
          <td>${boolLabel(row.benchmark_eligible)}</td>
          <td>${escapeHtml(row.source || "-")}</td>
          <td>${escapeHtml(row.notes || "-")}</td>
          <td>
            <div class="asset-action-group">
              <button class="asset-action" data-asset-action="candidate" data-asset-ticker="${escapeHtml(row.ticker)}" data-asset-type="${escapeHtml(row.asset_type)}">Candidate</button>
              <button class="asset-action" data-asset-action="active" data-asset-ticker="${escapeHtml(row.ticker)}" data-asset-type="${escapeHtml(row.asset_type)}">Active</button>
              <button class="asset-action" data-asset-action="strategy_eligible" data-asset-ticker="${escapeHtml(row.ticker)}" data-asset-type="${escapeHtml(row.asset_type)}">Strategy</button>
              <button class="asset-action" data-asset-action="archived" data-asset-ticker="${escapeHtml(row.ticker)}" data-asset-type="${escapeHtml(row.asset_type)}">Archive</button>
              <button class="asset-action" data-asset-action="excluded" data-asset-ticker="${escapeHtml(row.ticker)}" data-asset-type="${escapeHtml(row.asset_type)}">Exclude</button>
            </div>
          </td>
        </tr>`
    )
    .join("");
  $("#asset-event-rows").innerHTML = (state.universe.recent_events || [])
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.event_date)}</td>
          <td><strong>${escapeHtml(row.ticker)}</strong></td>
          <td>${escapeHtml(row.asset_type)}</td>
          <td>${escapeHtml(row.action)}</td>
          <td>${escapeHtml(row.previous_status || "-")}</td>
          <td>${escapeHtml(row.new_status || "-")}</td>
          <td>${escapeHtml(row.source || "-")}</td>
          <td>${escapeHtml(row.notes || "-")}</td>
        </tr>`
    )
    .join("");
  $("#benchmark-rows").innerHTML = state.benchmarks.benchmarks
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.benchmark_id)}</td>
          <td><strong>${escapeHtml(row.ticker)}</strong></td>
          <td>${escapeHtml(row.name)}</td>
          <td>${escapeHtml(row.asset_type)}</td>
          <td>${escapeHtml(row.exchange)}</td>
          <td>${escapeHtml(row.currency)}</td>
          <td>${escapeHtml(row.category)}</td>
          <td>${escapeHtml(row.default_for)}</td>
          <td>${boolLabel(row.active)}</td>
        </tr>`
    )
    .join("");
  $("#strategy-registry-rows").innerHTML = state.strategies.strategies
    .map(
      (row) => `
        <tr class="clickable" data-strategy-preview="${escapeHtml(row.strategy_id)}">
          <td><strong>${escapeHtml(row.strategy_name)}</strong></td>
          <td>${escapeHtml(row.status)}</td>
          <td>${escapeHtml(row.forward_test_start_date || "-")}</td>
          <td>${escapeHtml(row.universe || "-")}</td>
          <td>${escapeHtml(row.benchmark || "-")}</td>
          <td>${escapeHtml(row.position_size || "-")}</td>
          <td>${escapeHtml(row.entry_rule || "-")}</td>
          <td>${escapeHtml(row.exit_rule || "-")}</td>
          <td>${escapeHtml(row.news_rule || "-")}</td>
          <td>${escapeHtml(row.notes || "-")}</td>
          <td>
            <div class="asset-action-group">
              <button class="asset-action" data-strategy-status="research" data-strategy-id="${escapeHtml(row.strategy_id)}">Research</button>
              <button class="asset-action" data-strategy-status="forward_testing" data-strategy-id="${escapeHtml(row.strategy_id)}">Forward</button>
              <button class="asset-action" data-strategy-status="active" data-strategy-id="${escapeHtml(row.strategy_id)}">Active</button>
              <button class="asset-action" data-strategy-status="retired" data-strategy-id="${escapeHtml(row.strategy_id)}">Retire</button>
            </div>
          </td>
        </tr>`
    )
    .join("");
  $("#basket-rows").innerHTML = state.baskets.baskets
    .map(
      (row) => `
        <tr class="clickable" data-basket="${escapeHtml(row.basket_id)}">
          <td><strong>${escapeHtml(row.basket_name)}</strong></td>
          <td>${escapeHtml(row.status)}</td>
          <td>${escapeHtml(row.weighting_method)}</td>
          <td>${escapeHtml(row.rebalance_frequency)}</td>
          <td>${escapeHtml(row.benchmark || "-")}</td>
          <td>${row.member_count}</td>
          <td>${escapeHtml(row.members.map((member) => member.ticker).join(", "))}</td>
          <td>${escapeHtml(row.notes || "-")}</td>
        </tr>`
    )
    .join("");
  $("#research-rows").innerHTML = state.research.notes
    .map(
      (row) => `
        <tr class="clickable" data-research="${escapeHtml(row.slug)}">
          <td><strong>${escapeHtml(row.title)}</strong></td>
          <td>${escapeHtml(row.tags.join(", "))}</td>
          <td>${escapeHtml(row.filename)}</td>
          <td>${number(row.size_bytes / 1024)} KB</td>
        </tr>`
    )
    .join("");
  document.querySelectorAll("[data-asset-action]").forEach((button) =>
    button.addEventListener("click", () => updateAssetStatus(button))
  );
  document.querySelectorAll("[data-basket]").forEach((row) =>
    row.addEventListener("click", () => openBasket(row.dataset.basket))
  );
  document.querySelectorAll("[data-strategy-preview]").forEach((row) =>
    row.addEventListener("click", () => openSavedStrategy(row.dataset.strategyPreview))
  );
  document.querySelectorAll("[data-strategy-status]").forEach((button) =>
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      updateStrategyStatus(button.dataset.strategyId, button.dataset.strategyStatus);
    })
  );
  document.querySelectorAll("[data-research]").forEach((row) =>
    row.addEventListener("click", () => openResearch(row.dataset.research))
  );
  enableSorting();
}

async function refreshUniverse() {
  const [universe, benchmarks, strategies, baskets, research] = await Promise.all([
    fetchJson("/api/universe/assets"),
    fetchJson("/api/benchmarks"),
    fetchJson("/api/strategies"),
    fetchJson("/api/baskets"),
    fetchJson("/api/research"),
  ]);
  state.universe = universe;
  state.benchmarks = benchmarks;
  state.strategies = strategies;
  state.baskets = baskets;
  state.research = research;
  renderUniverseControls();
  renderUniverse();
}

async function submitAssetForm(event) {
  event.preventDefault();
  const payload = {
    ticker: $("#asset-ticker").value,
    asset_type: $("#asset-type").value,
    status: $("#asset-status").value,
    sector: $("#asset-sector").value,
    theme: $("#asset-theme").value,
    notes: $("#asset-notes").value,
    source: "manual-ui",
  };
  try {
    await fetchJson("/api/universe/assets", jsonRequest("POST", payload));
    $("#asset-form").reset();
    $("#asset-status").value = "candidate";
    await refreshUniverse();
    $("#universe-status").textContent = `Saved ${payload.ticker.toUpperCase()}. ${universeStatusText()}`;
  } catch (error) {
    $("#universe-status").textContent = `Asset save failed: ${error.message}`;
  }
}

async function submitBasketForm(event) {
  event.preventDefault();
  const payload = {
    basket_id: $("#basket-id").value.trim(),
    basket_name: $("#basket-name").value.trim(),
    status: $("#basket-status-field").value,
    weighting_method: $("#basket-weighting").value,
    rebalance_frequency: $("#basket-rebalance").value,
    benchmark: $("#basket-benchmark").value.trim() || "SPY",
    notes: $("#basket-notes").value.trim(),
  };
  try {
    const result = await fetchJson("/api/baskets", jsonRequest("POST", payload));
    $("#basket-form").reset();
    $("#basket-benchmark").value = "SPY";
    await refreshUniverse();
    $("#basket-status").textContent = `Saved basket ${result.basket.basket_id}.`;
  } catch (error) {
    $("#basket-status").textContent = `Basket save failed: ${error.message}`;
  }
}

async function submitBasketMemberForm(event) {
  event.preventDefault();
  const basketId = $("#basket-member-basket-id").value.trim();
  const payload = {
    ticker: $("#basket-member-ticker").value.trim(),
    asset_type: $("#basket-member-type").value,
    target_weight: $("#basket-member-weight").value.trim(),
    notes: $("#basket-member-notes").value.trim(),
  };
  try {
    const result = await fetchJson(
      `/api/baskets/${encodeURIComponent(basketId)}/members`,
      jsonRequest("POST", payload)
    );
    $("#basket-member-form").reset();
    $("#basket-member-basket-id").value = result.member.basket_id;
    await refreshUniverse();
    $("#basket-status").textContent = `Saved ${result.member.ticker} in ${result.member.basket_id}.`;
  } catch (error) {
    $("#basket-status").textContent = `Basket member save failed: ${error.message}`;
  }
}

async function submitBenchmarkForm(event) {
  event.preventDefault();
  const payload = {
    benchmark_id: $("#benchmark-id").value.trim(),
    ticker: $("#benchmark-ticker").value.trim(),
    name: $("#benchmark-name").value.trim(),
    asset_type: $("#benchmark-type").value,
    exchange: $("#benchmark-exchange").value.trim(),
    currency: $("#benchmark-currency").value.trim() || "USD",
    category: $("#benchmark-category").value.trim(),
    default_for: $("#benchmark-default-for").value.trim(),
    active: $("#benchmark-active").value === "true",
    notes: $("#benchmark-notes").value.trim(),
  };
  try {
    const result = await fetchJson("/api/benchmarks", jsonRequest("POST", payload));
    $("#benchmark-form").reset();
    $("#benchmark-currency").value = "USD";
    await refreshUniverse();
    $("#universe-status").textContent = `Saved benchmark ${result.benchmark.benchmark_id}. ${universeStatusText()}`;
  } catch (error) {
    $("#universe-status").textContent = `Benchmark save failed: ${error.message}`;
  }
}

async function updateAssetStatus(button) {
  const ticker = button.dataset.assetTicker;
  const assetType = button.dataset.assetType;
  const status = button.dataset.assetAction;
  const payload = {
    status,
    strategy_eligible: status === "strategy_eligible" ? true : undefined,
  };
  try {
    await fetchJson(
      `/api/universe/assets/${encodeURIComponent(ticker)}?asset_type=${encodeURIComponent(assetType)}`,
      jsonRequest("PATCH", payload)
    );
    await refreshUniverse();
    $("#universe-status").textContent = `Updated ${ticker} to ${status}. ${universeStatusText()}`;
  } catch (error) {
    $("#universe-status").textContent = `Asset update failed: ${error.message}`;
  }
}

async function saveStockUniverseAction(ticker, assetType, action, reason = "") {
  const statusNode = $("#stock-universe-action-status") || $("#recommendation-action-status");
  const existing = universeByTicker().get(String(ticker).toUpperCase());
  const recommendationNote = reason ? `Recommendation ${action}: ${reason}` : "";
  const notes = [existing?.notes, recommendationNote].filter(Boolean).join(" | ");
  const basePayload = {
    ticker,
    asset_type: assetType,
    source: reason ? "recommendation-engine-ui" : "stock-drilldown-ui",
    notes: notes || undefined,
  };
  const payload = action === "strategy_eligible"
    ? { ...basePayload, status: "active", strategy_eligible: true, watchlist_eligible: true }
    : { ...basePayload, status: action };
  try {
    await fetchJson("/api/universe/assets", jsonRequest("POST", payload));
    await refreshUniverse();
    if (state.overview) renderRecommendations();
    if (statusNode) statusNode.textContent = `Saved ${ticker} as ${action}. ${universeStatusText()}`;
  } catch (error) {
    if (statusNode) statusNode.textContent = `Asset update failed: ${error.message}`;
  }
}

function dateOptions(meta, includeLatest = false) {
  const keyDates = meta.key_dates.map((item) => ({ ...item, group: "Key dates" }));
  const checkpoints = meta.checkpoints.map((item) => ({ ...item, group: "Monthly checkpoints" }));
  const rows = includeLatest
    ? [{ label: `Latest available close (${meta.default_to_date})`, date: meta.default_to_date, group: "Current" }, ...keyDates, ...checkpoints]
    : [...keyDates, ...checkpoints];
  let group = "";
  return rows
    .map((row) => {
      const heading = row.group !== group ? `<optgroup label="${row.group}">` : "";
      const closing = row.group !== group && group ? "</optgroup>" : "";
      group = row.group;
      return `${closing}${heading}<option value="${row.date}">${row.label}</option>`;
    })
    .join("") + (group ? "</optgroup>" : "");
}

function portfolioDescription(row = {}) {
  const investor = String(row.investor || "").toLowerCase();
  const source = String(row.source || "").toLowerCase();
  if (source.includes("wealthsimple")) {
    return "Imported Wealthsimple account history for Nisarg; deposits and withdrawals are ignored in return calculations where possible.";
  }
  if (source.includes("saved-strategy-registry")) {
    return "Saved Strategy Lab configuration replayed as a generated portfolio for comparison against live watchlists.";
  }
  if (source.includes("derived-master-signal")) {
    return "Master ranked portfolio: scores the hybrid stock universe with signals, relative strength, volume, news, and overextension checks, then holds only the top capped positions.";
  }
  if (source.includes("derived-news-analysis")) {
    return "News + analysis variable watchlist: requires accelerating news plus a market-analysis score using relative strength, volume confirmation, trend quality, multi-horizon confirmation, and overextension risk.";
  }
  if (source.includes("derived-news-assisted")) {
    if (investor.includes("optimized")) {
      return "News-assisted variable watchlist using EOD signal timing and the optimized news/signal rules selected from backtests.";
    }
    if (investor.includes("active")) {
      return "News-assisted variable watchlist that holds or filters positions while related news remains active.";
    }
    if (investor.includes("cooling")) {
      return "News-assisted variable watchlist variant that uses cooling news behavior as part of sell decisions.";
    }
    if (investor.includes("required-entry")) {
      return "Variable watchlist variant that requires news support before entering positions.";
    }
    return "Derived variable watchlist that combines technical signals with free news activity and next-close execution.";
  }
  if (source.includes("derived-buy-only")) {
    return "Buy-only signal portfolio: buys qualifying signals and keeps positions instead of selling when signals fade.";
  }
  if (source.includes("derived-daily-signal")) {
    return "Variable signal portfolio: replays daily EOD signal changes from the selected start date with next-close execution assumptions.";
  }
  if (source.includes("derived-multi-signal")) {
    return "Variable strategy using multiple signal horizons and exit rules to test whether technical deterioration improves selling.";
  }
  if (investor.includes("mass-change")) {
    return "Candidate discovery portfolio for sector-led volume/news movers; used to collect ideas before promotion to other watchlists.";
  }
  if (investor.includes("long-term-watchlist")) {
    return "Long-term idea basket for stocks selected from research themes and watchlist expansion work.";
  }
  if (investor.includes("short-term-watchlist")) {
    return "Short-term technical setup basket focused on high-momentum and volume-driven candidates.";
  }
  if (investor.includes("insta_watchlist")) {
    return "Creator/social watchlist basket sourced from Instagram-style idea flow and related market themes.";
  }
  if (investor.startsWith("analyst-")) {
    return "Free analyst-pick basket built from visible Buy-rated stocks on public analyst-ranking pages. This is not a disclosed personal portfolio.";
  }
  if (source.includes("paper-ledger")) {
    return "Manually entered paper-trading ledger using the configured position sizing assumptions for stocks, ETFs, and crypto.";
  }
  return "Tracked dashboard portfolio. Click through for holdings, realized positions, benchmark comparison, signal mix, and trade ledger details.";
}

function portfolioNameCell(row) {
  const description = portfolioDescription(row);
  const priorityBadge = isLowPriorityPortfolio(row)
    ? `<span class="priority-badge" title="${escapeHtml(row.portfolio_priority_reason || "Research watchlist")}">Research watchlist</span>`
    : "";
  return `
    <span class="portfolio-tip">
      <strong>${escapeHtml(row.investor)}</strong>
      <span class="info-dot" aria-label="Portfolio description">i</span>
      <span class="portfolio-tip-text">${escapeHtml(description)}</span>
    </span>
    ${priorityBadge}
    <br><span class="muted">${escapeHtml(row.source || "")}</span>`;
}

function renderTraders() {
  $("#trader-rows").innerHTML = portfolioRows(state.overview.traders)
    .map(
      (row) => `
      <tr class="clickable ${isLowPriorityPortfolio(row) ? "low-priority-row" : ""}" data-trader="${escapeHtml(row.investor)}" title="${escapeHtml(portfolioDescription(row))}">
        <td>${row.rank}</td>
        <td>${portfolioNameCell(row)}</td>
        <td>${row.position_count}</td>
        <td>${money(row.initial_value)}</td>
        <td>${money(row.current_value)}</td>
        <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
        <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
        <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
        <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
      </tr>`
    )
    .join("");
  document.querySelectorAll("[data-trader]").forEach((row) =>
    row.addEventListener("click", () => openTrader(row.dataset.trader))
  );
  enableSorting();
}

function renderPortfolioVisibilityViews() {
  renderLowPriorityControls();
  renderCards();
  renderCommandCenter();
  renderEod();
  renderTraders();
}

function renderEod() {
  $("#eod-window-label").textContent = `${state.eod.from_date} to ${state.eod.to_date}`;
  $("#eod-trader-rows").innerHTML = portfolioRows(state.eod.traders || [])
    .map(
      (row) => `
      <tr class="clickable ${isLowPriorityPortfolio(row) ? "low-priority-row" : ""}" data-eod-trader="${escapeHtml(row.investor)}" title="${escapeHtml(portfolioDescription(row))}">
        <td>${portfolioNameCell(row)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
        <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
      </tr>`
    )
    .join("");
  const top = state.eod.stocks.slice(0, 5);
  const bottom = state.eod.stocks.slice(-5).reverse();
  $("#eod-stock-rows").innerHTML = [...top, ...bottom]
    .map(
      (row) => `
      <tr class="clickable" data-eod-stock="${row.ticker}">
        <td>${tickerLabel(row.ticker, row.wealthsimple)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
        <td>${row.owners.join(", ")}</td>
      </tr>`
    )
    .join("");
  document.querySelectorAll("[data-eod-trader]").forEach((row) =>
    row.addEventListener("click", () => openTrader(row.dataset.eodTrader))
  );
  document.querySelectorAll("[data-eod-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.eodStock))
  );
  enableSorting();
}

function shortDateTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? escapeHtml(value)
    : parsed.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function renderMarketNews() {
  const payload = state.marketNews;
  if (!payload) {
    $("#market-news-status").textContent = state.overview ? "News has not been loaded yet." : "Load the dashboard first.";
    $("#market-news-cards").innerHTML = "";
    $("#market-topic-rows").innerHTML = "";
    $("#market-hot-stock-rows").innerHTML = "";
    $("#market-headline-rows").innerHTML = "";
    $("#market-social-rows").innerHTML = "";
    $("#market-news-source-rows").innerHTML = "";
    return;
  }
  const sources = payload.sources || [];
  const workingSources = sources.filter((row) => row.status === "ok").length;
  $("#market-news-status").textContent = `Fetched ${shortDateTime(payload.fetched_at)} from ${workingSources}/${sources.length} working free sources.`;
  $("#market-news-note").textContent = payload.note || "";
  $("#market-news-cards").innerHTML = [
    {
      label: "Headlines",
      value: number(payload.headline_count || (payload.headlines || []).length),
      note: "Latest broad-market rows from free sources",
      toneValue: payload.headline_count || 0,
    },
    {
      label: "Hot topics",
      value: number((payload.hot_topics || []).length),
      note: "Theme matches in current headlines",
      toneValue: (payload.hot_topics || []).length,
    },
    {
      label: "Hot tracked stocks",
      value: number((payload.hot_stocks || []).length),
      note: "Tracked names with news/social attention",
      toneValue: (payload.hot_stocks || []).length,
    },
    {
      label: "Social mentions",
      value: number((payload.social_mentions || []).length),
      note: "Public Stocktwits trending symbols when available",
      toneValue: (payload.social_mentions || []).length,
    },
  ].map((card) => `
    <article class="summary-card">
      <p class="eyebrow">${escapeHtml(card.label)}</p>
      <p class="value ${tone(card.toneValue)}">${escapeHtml(card.value)}</p>
      <p class="muted">${escapeHtml(card.note)}</p>
    </article>`).join("");

  $("#market-topic-rows").innerHTML = (payload.hot_topics || []).map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.topic)}</strong></td>
      <td>${number(row.mentions)}</td>
      <td>${escapeHtml((row.tracked_tickers || []).join(", ") || "-")}</td>
      <td>${escapeHtml(row.example_headline || "-")}</td>
    </tr>`).join("");

  $("#market-hot-stock-rows").innerHTML = (payload.hot_stocks || []).map((row) => `
    <tr class="clickable" data-market-stock="${escapeHtml(row.ticker)}" title="${escapeHtml(row.example_headline || "")}">
      <td>${tickerLabel(row.ticker)}</td>
      <td>${number(row.score)}</td>
      <td>${number(row.mentions)}</td>
      <td>${row.social_rank || "-"}</td>
      <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
      <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
      <td>${escapeHtml(row.signal || "none")}</td>
    </tr>`).join("");

  $("#market-headline-rows").innerHTML = (payload.headlines || []).map((row) => `
    <tr>
      <td><a href="${safeUrl(row.url)}" target="_blank" rel="noreferrer">${escapeHtml(row.headline)}</a></td>
      <td>${escapeHtml(row.domain || row.source || "-")}</td>
      <td>${shortDateTime(row.created_at)}</td>
    </tr>`).join("");

  $("#market-social-rows").innerHTML = (payload.social_mentions || []).map((row) => `
    <tr class="${row.tracked ? "clickable" : ""}" ${row.tracked ? `data-market-stock="${escapeHtml(row.ticker)}"` : ""}>
      <td>${row.rank || "-"}</td>
      <td>${row.tracked ? tickerLabel(row.ticker) : `<strong>${escapeHtml(row.ticker || "-")}</strong>`}</td>
      <td>${escapeHtml(row.title || "-")}</td>
      <td>${row.tracked ? "Yes" : "No"}</td>
      <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
      <td>${escapeHtml((row.owners || []).join(", ") || "-")}</td>
    </tr>`).join("");

  $("#market-news-source-rows").innerHTML = sources.map((row) => `
    <tr>
      <td>${escapeHtml(row.source || "-")}</td>
      <td>${escapeHtml(row.status || "-")}</td>
      <td>${number(row.articles ?? row.symbols ?? row.videos ?? 0)}</td>
      <td>${escapeHtml(row.detail || "")}</td>
    </tr>`).join("");

  document.querySelectorAll("[data-market-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.marketStock))
  );
  enableSorting();
}

async function loadMarketNews(force = false) {
  if (!state.overview) {
    renderMarketNews();
    return;
  }
  const requestKey = `${query()}`;
  if (!force && state.marketNews && state.marketNewsRequestKey === requestKey) {
    renderMarketNews();
    return;
  }
  $("#market-news-status").textContent = "Loading free news and social mentions...";
  $("#reload-market-news").disabled = true;
  try {
    state.marketNews = await fetchJson(`/api/market-news?${query()}`);
    state.marketNewsRequestKey = requestKey;
    renderMarketNews();
  } catch (error) {
    $("#market-news-status").textContent = error.message;
  } finally {
    $("#reload-market-news").disabled = false;
  }
}

function renderSectors() {
  $("#sector-rows").innerHTML = (state.overview.sector_breakdowns || [])
    .map((row) => {
      const signals = row.signal_counts || {};
      return `
        <tr class="clickable" data-sector="${escapeHtml(row.sector)}">
          <td>${row.rank}</td>
          <td><strong>${row.sector}</strong></td>
          <td>${row.instrument_count}</td>
          <td>${pct(row.win_rate_pct)}</td>
          <td class="${tone(row.average_return_pct)}">${pct(row.average_return_pct)}</td>
          <td class="${tone(row.median_return_pct)}">${pct(row.median_return_pct)}</td>
          <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
          <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
          <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
          <td>F ${signals.fresh || 0} / S ${signals.strict || 0} / N ${signals.near || 0} / none ${signals.none || 0}</td>
          <td>${row.top_ticker} ${pct(row.top_return_pct)}</td>
          <td>${row.bottom_ticker} ${pct(row.bottom_return_pct)}</td>
          <td>${(row.tickers || []).join(", ")}</td>
        </tr>`;
    })
    .join("");
  document.querySelectorAll("[data-sector]").forEach((row) =>
    row.addEventListener("click", () => openSector(row.dataset.sector))
  );
  enableSorting();
}

function filteredStocks() {
  const search = $("#stock-search").value.trim().toLowerCase();
  const filter = $("#signal-filter").value;
  return [...state.overview.stocks]
    .filter((row) => !row.warning)
    .filter((row) => {
      const haystack = `${row.ticker} ${row.sector || ""} ${row.owners.join(" ")}`.toLowerCase();
      return !search || haystack.includes(search);
    })
    .filter((row) => {
      if (filter === "all") return true;
      if (filter === "fresh") return row.signal?.fresh_priority;
      return row.signal?.classification === filter;
    })
    .sort((a, b) => b.return_pct - a.return_pct);
}

function renderStocks() {
  $("#stock-rows").innerHTML = filteredStocks()
    .map(
      (row) => `
      <tr class="clickable" data-stock="${row.ticker}">
        <td>${tickerLabel(row.ticker, row.wealthsimple)}<br><span class="muted">${row.yahoo_symbol}</span></td>
        <td>${row.security_type}</td>
        <td>${row.sector || "Unclassified"}<br><span class="muted">${row.sector_source || ""}</span></td>
        <td>${row.owners.join(", ")}</td>
        <td>${number(row.start_price)} ${row.currency}</td>
        <td>${number(row.end_price)} ${row.currency}</td>
        <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
        <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
        <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
        <td>${row.signal ? `${number(row.signal.overall_score)} / 100` : "-"}</td>
        <td><button class="signal-button" data-stock-signal="${row.ticker}" title="Open multi-horizon signal drilldown">${signalPill(row.signal)}</button></td>
      </tr>`
    )
    .join("");
  document.querySelectorAll("[data-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.stock))
  );
  document.querySelectorAll("[data-stock-signal]").forEach((button) =>
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openStock(button.dataset.stockSignal);
    })
  );
  enableSorting();
}

function polyline(series, key) {
  if (!series.length) return '<p class="chart-empty">Daily series is not available for this view.</p>';
  const values = series.map((row) => Number(row[key]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const width = 680;
  const height = 190;
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / spread) * (height - 14) + 2;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 215" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <polyline points="${points}" fill="none" stroke="#57d3a2" stroke-width="3" vector-effect="non-scaling-stroke" />
      <text x="4" y="210" fill="#91a4bd" font-size="12">${series[0].date}</text>
      <text x="${width - 82}" y="210" fill="#91a4bd" font-size="12">${series.at(-1).date}</text>
    </svg>`;
}

function comparisonPolyline(series, benchmarkSeries) {
  if (!series.length || !benchmarkSeries?.length) {
    return '<p class="chart-empty">Benchmark comparison is not available for this view.</p>';
  }
  const benchmarkByDate = new Map(benchmarkSeries.map((row) => [row.date, Number(row.value)]));
  const points = series
    .map((row) => ({ date: row.date, portfolio: Number(row.value), benchmark: benchmarkByDate.get(row.date) }))
    .filter((row) => row.benchmark !== undefined);
  if (points.length < 2) return '<p class="chart-empty">Benchmark comparison needs at least two aligned days.</p>';
  const values = points.flatMap((row) => [row.portfolio, row.benchmark]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const width = 680;
  const height = 190;
  const pathFor = (key) => points
    .map((row, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((row[key] - min) / spread) * (height - 14) + 2;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="192" x2="${width}" y2="192" stroke="#213653" />
      <polyline points="${pathFor("benchmark")}" fill="none" stroke="#6fb7ff" stroke-width="2" vector-effect="non-scaling-stroke" />
      <polyline points="${pathFor("portfolio")}" fill="none" stroke="#57d3a2" stroke-width="3" vector-effect="non-scaling-stroke" />
      <text x="4" y="210" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="210" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
      <text x="4" y="230" fill="#57d3a2" font-size="12">Portfolio</text>
      <text x="92" y="230" fill="#6fb7ff" font-size="12">Benchmark</text>
    </svg>`;
}

function drawdownPolyline(series) {
  if (series.length < 2) return '<p class="chart-empty">Drawdown needs at least two daily values.</p>';
  let peak = Number(series[0].value);
  const points = series.map((row) => {
    const value = Number(row.value);
    if (value > peak) peak = value;
    const drawdown = peak ? ((value - peak) / peak) * 100 : 0;
    return { date: row.date, drawdown };
  });
  const min = Math.min(...points.map((row) => row.drawdown), 0);
  const width = 680;
  const height = 190;
  const spread = Math.abs(min) || 1;
  const path = points
    .map((row, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = 12 + (Math.abs(row.drawdown) / spread) * (height - 22);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="12" x2="${width}" y2="12" stroke="#213653" />
      <line x1="0" y1="${height}" x2="${width}" y2="${height}" stroke="#213653" />
      <polyline points="${path}" fill="none" stroke="#ff7b7b" stroke-width="3" vector-effect="non-scaling-stroke" />
      <text x="4" y="28" fill="#91a4bd" font-size="12">0%</text>
      <text x="4" y="${height - 6}" fill="#ff7b7b" font-size="12">${pct(min)}</text>
      <text x="4" y="215" fill="#91a4bd" font-size="12">${points[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${points.at(-1).date}</text>
    </svg>`;
}

function rollingReturnPolyline(series) {
  if (series.length < 8) return '<p class="chart-empty">Rolling returns need at least eight daily values.</p>';
  const points = [];
  for (let index = 0; index < series.length; index += 1) {
    const current = Number(series[index].value);
    const weekStart = series[Math.max(0, index - 7)];
    const monthStart = series[Math.max(0, index - 30)];
    if (index < 7 || !weekStart || !monthStart) continue;
    const weekBase = Number(weekStart.value);
    const monthBase = Number(monthStart.value);
    points.push({
      date: series[index].date,
      sevenDay: weekBase ? ((current / weekBase) - 1) * 100 : null,
      thirtyDay: index >= 30 && monthBase ? ((current / monthBase) - 1) * 100 : null,
    });
  }
  const plottable = points.filter((row) => row.sevenDay !== null || row.thirtyDay !== null);
  if (plottable.length < 2) return '<p class="chart-empty">Rolling returns need more aligned daily values.</p>';
  const values = plottable.flatMap((row) => [row.sevenDay, row.thirtyDay]).filter((value) => value !== null);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const spread = max - min || 1;
  const width = 680;
  const height = 190;
  const pathFor = (key) => plottable
    .filter((row) => row[key] !== null)
    .map((row, index, rows) => {
      const x = (index / Math.max(rows.length - 1, 1)) * width;
      const y = height - ((row[key] - min) / spread) * (height - 18) + 4;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const zeroY = height - ((0 - min) / spread) * (height - 18) + 4;
  return `
    <svg viewBox="0 0 ${width} 235" preserveAspectRatio="none" role="img">
      <line x1="0" y1="${zeroY.toFixed(2)}" x2="${width}" y2="${zeroY.toFixed(2)}" stroke="#213653" />
      <polyline points="${pathFor("sevenDay")}" fill="none" stroke="#57d3a2" stroke-width="3" vector-effect="non-scaling-stroke" />
      <polyline points="${pathFor("thirtyDay")}" fill="none" stroke="#f9c74f" stroke-width="2" vector-effect="non-scaling-stroke" />
      <text x="4" y="18" fill="#91a4bd" font-size="12">${pct(max)}</text>
      <text x="4" y="${height - 6}" fill="#91a4bd" font-size="12">${pct(min)}</text>
      <text x="4" y="215" fill="#91a4bd" font-size="12">${plottable[0].date}</text>
      <text x="${width - 82}" y="215" fill="#91a4bd" font-size="12">${plottable.at(-1).date}</text>
      <text x="4" y="232" fill="#57d3a2" font-size="12">7D</text>
      <text x="42" y="232" fill="#f9c74f" font-size="12">30D</text>
    </svg>`;
}

function stat(label, value, className = "") {
  return `<div class="detail-stat"><p>${label}</p><p class="${className}">${value}</p></div>`;
}

function relatedResearchNotes(terms = [], tags = []) {
  const normalizedTerms = terms
    .filter(Boolean)
    .flatMap((term) => String(term).split(/[,|]/))
    .map((term) => term.trim().toLowerCase())
    .filter((term) => term.length > 1);
  const wantedTags = new Set(tags.filter(Boolean).map((tag) => String(tag).toLowerCase()));
  return (state.research?.notes || [])
    .map((note) => {
      const haystack = `${note.slug} ${note.title} ${note.filename} ${(note.tags || []).join(" ")}`.toLowerCase();
      const score = normalizedTerms.reduce((total, term) => total + (haystack.includes(term) ? 2 : 0), 0)
        + (note.tags || []).reduce((total, tag) => total + (wantedTags.has(String(tag).toLowerCase()) ? 1 : 0), 0);
      return { ...note, score };
    })
    .filter((note) => note.score > 0)
    .sort((left, right) => right.score - left.score || left.title.localeCompare(right.title))
    .slice(0, 5);
}

function relatedResearchHtml(terms = [], tags = []) {
  const notes = relatedResearchNotes(terms, tags);
  if (!notes.length) return "";
  return `
    <div class="asset-action-panel">
      <h3>Related research</h3>
      <div class="asset-action-group left">
        ${notes.map((note) => `<button class="asset-action" data-related-research="${escapeHtml(note.slug)}">${escapeHtml(note.title)}</button>`).join("")}
      </div>
    </div>`;
}

function bindRelatedResearchLinks(root = document) {
  root.querySelectorAll("[data-related-research]").forEach((button) =>
    button.addEventListener("click", () => openResearch(button.dataset.relatedResearch))
  );
}

function openDrawer(html) {
  $("#drawer-content").innerHTML = html;
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
  $("#backdrop").classList.remove("hidden");
  $("#export-drawer").classList.toggle("hidden", !$("#drawer-content table"));
  bindRelatedResearchLinks($("#drawer-content"));
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  $("#backdrop").classList.add("hidden");
  $("#export-drawer").classList.add("hidden");
}

async function openBasket(basketId) {
  openDrawer(loadingPanel(`Loading ${basketId} basket performance...`));
  try {
    const detail = await fetchJson(`/api/baskets/${encodeURIComponent(basketId)}/performance?${query()}`);
    const basket = detail.basket;
    const rows = (detail.members || [])
      .map((row) => `
        <tr>
          <td>${tickerLabel(row.ticker)}</td>
          <td>${escapeHtml(row.asset_type)}</td>
          <td>${pct(row.weight_pct)}</td>
          <td>${row.start_price === undefined ? "-" : number(row.start_price)}</td>
          <td>${row.end_price === undefined ? "-" : number(row.end_price)}</td>
          <td class="${row.return_pct === null ? "" : tone(row.return_pct)}">${row.return_pct === null ? "-" : pct(row.return_pct)}</td>
          <td class="${row.contribution_pct === null ? "" : tone(row.contribution_pct)}">${row.contribution_pct === null ? "-" : pct(row.contribution_pct)}</td>
          <td>${escapeHtml(row.warning || "-")}</td>
        </tr>`)
      .join("");
    openDrawer(`
      <p class="eyebrow">Custom basket preview</p>
      <h2>${escapeHtml(basket.basket_name)}</h2>
      <div class="detail-grid">
        ${stat("Basket return", pct(detail.return_pct), tone(detail.return_pct))}
        ${detail.benchmark_return_pct === null ? "" : stat(`${basket.benchmark} return`, pct(detail.benchmark_return_pct), tone(detail.benchmark_return_pct))}
        ${detail.alpha_pct === null ? "" : stat("Alpha", pct(detail.alpha_pct), tone(detail.alpha_pct))}
        ${stat("Members", number(basket.member_count))}
        ${stat("Weighting", escapeHtml(basket.weighting_method))}
        ${stat("Rebalance", escapeHtml(basket.rebalance_frequency))}
      </div>
      <p class="muted">${escapeHtml(detail.note || "")}</p>
      ${relatedResearchHtml([basket.basket_id, basket.basket_name, ...(basket.members || []).map((member) => member.ticker)], ["sector", "watchlist"])}
      <h3>Daily basket simulation</h3>
      <div class="chart">${polyline(detail.series || [], "value")}</div>
      <div class="table-wrap">
        <table id="basket-member-performance-table" data-sortable>
          <thead><tr><th>Ticker</th><th>Type</th><th>Weight</th><th>Start</th><th>End</th><th>Return</th><th>Contribution</th><th>Warning</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`);
    enableSorting();
  } catch (error) {
    openDrawer(`<p class="error">Basket performance failed: ${escapeHtml(error.message)}</p>`);
  }
}

function openSector(sectorName) {
  const sector = (state.overview?.sector_breakdowns || []).find((row) => row.sector === sectorName);
  if (!sector) return;
  const stocks = (state.overview?.stocks || [])
    .filter((row) => !row.warning && (row.sector || "Unclassified") === sectorName)
    .sort((left, right) => Number(right.return_pct || 0) - Number(left.return_pct || 0));
  const rows = stocks
    .map((row) => `
      <tr class="clickable" data-sector-stock="${escapeHtml(row.ticker)}">
        <td>${tickerLabel(row.ticker, row.wealthsimple)}</td>
        <td>${signalPill(row.signal)}</td>
        <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
        <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
        <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
        <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
        <td>${escapeHtml((row.owners || []).join(", "))}</td>
      </tr>`)
    .join("");
  openDrawer(`
    <p class="eyebrow">Sector drilldown</p>
    <h2>${escapeHtml(sectorName)}</h2>
    ${relatedResearchHtml([sectorName, ...(sector.tickers || [])], ["sector", "news", "signals"])}
    <div class="detail-grid">
      ${stat("Instruments", number(sector.instrument_count))}
      ${stat("Win rate", pct(sector.win_rate_pct), tone(sector.win_rate_pct - 50))}
      ${stat("Average return", pct(sector.average_return_pct), tone(sector.average_return_pct))}
      ${stat("Median return", pct(sector.median_return_pct), tone(sector.median_return_pct))}
      ${stat("Daily", pctOrDash(sector.daily_change_pct), toneOrEmpty(sector.daily_change_pct))}
      ${stat("5D", pctOrDash(sector.five_day_change_pct), toneOrEmpty(sector.five_day_change_pct))}
      ${stat("Monthly", pctOrDash(sector.monthly_change_pct), toneOrEmpty(sector.monthly_change_pct))}
      ${stat("Signals", `F ${sector.signal_counts?.fresh || 0} / S ${sector.signal_counts?.strict || 0} / N ${sector.signal_counts?.near || 0}`)}
    </div>
    <div class="table-wrap">
      <table id="sector-member-table" data-sortable>
        <thead><tr><th>Ticker</th><th>Signal</th><th>Return</th><th>Daily</th><th>5D</th><th>Monthly</th><th>Owners</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="7">No sector members for this window.</td></tr>'}</tbody>
      </table>
    </div>`);
  enableSorting($("#drawer-content"));
  document.querySelectorAll("[data-sector-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.sectorStock))
  );
}

async function openResearch(slug) {
  openDrawer(loadingPanel(`Loading ${slug} research note...`));
  try {
    const note = await fetchJson(`/api/research/${encodeURIComponent(slug)}`);
    openDrawer(`
      <p class="eyebrow">Research note</p>
      <h2>${escapeHtml(note.title)}</h2>
      <p class="muted">${escapeHtml(note.filename)} | ${escapeHtml(note.tags.join(", "))}</p>
      <pre class="research-note">${escapeHtml(note.content)}</pre>`);
  } catch (error) {
    openDrawer(`<p class="error">Research note failed: ${escapeHtml(error.message)}</p>`);
  }
}

async function openSavedStrategy(strategyId) {
  openDrawer(loadingPanel(`Loading ${strategyId} saved strategy preview...`));
  try {
    const detail = await fetchJson(`/api/strategies/${encodeURIComponent(strategyId)}/preview?${query()}`);
    const strategy = detail.registry_strategy || {};
    openDrawer(`
      <p class="eyebrow">Saved strategy preview</p>
      <h2>${escapeHtml(detail.investor)}</h2>
      <p class="muted">${escapeHtml(strategy.status || "-")} | ${escapeHtml(detail.note || "")}</p>
      ${relatedResearchHtml([detail.investor, strategy.entry_rule, strategy.exit_rule, strategy.news_rule, strategy.universe], ["strategy", "signals", "news"])}
      ${strategyPreviewHtml(detail)}`);
    enableSorting();
  } catch (error) {
    openDrawer(`<p class="error">Saved strategy preview failed: ${escapeHtml(error.message)}</p>`);
  }
}

async function openTrader(investor) {
  openDrawer(loadingPanel(`Loading ${investor} portfolio details...`));
  try {
    const detail = await fetchJson(`/api/traders/${encodeURIComponent(investor)}?${query()}`);
    const rows = detail.positions
      .map(
        (row) => `
        <tr>
          <td>${tickerLabel(row.ticker)}</td>
          <td>${money(row.initial_value)}</td>
          <td>${money(row.current_value)}</td>
          <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
          <td class="${toneOrEmpty(row.daily_change_pct)}">${pctOrDash(row.daily_change_pct)}</td>
          <td class="${toneOrEmpty(row.five_day_change_pct)}">${pctOrDash(row.five_day_change_pct)}</td>
          <td class="${toneOrEmpty(row.monthly_change_pct)}">${pctOrDash(row.monthly_change_pct)}</td>
          <td class="${tone(row.return_pct || 0)}">${row.return_pct === undefined ? "-" : pct(row.return_pct)}</td>
        </tr>`
      )
      .join("");
    const realizedRows = (detail.realized_positions || [])
      .map(
        (row) => `
        <tr>
          <td>${tickerLabel(row.ticker)}</td>
          <td>${row.entry_signal}</td>
          <td>${row.signal_observed_date}</td>
          <td>${row.entry_date}</td>
          <td>${row.exit_signal_observed_date}</td>
          <td>${row.exit_date}</td>
          <td>${money(row.entry_price)}</td>
          <td>${money(row.exit_price)}</td>
          <td>${money(row.initial_value)}</td>
          <td>${money(row.ending_value)}</td>
          <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
          <td class="${tone(row.return_pct || 0)}">${pct(row.return_pct)}</td>
        </tr>`
      )
      .join("");
    const categoryRows = detail.category_stats
      ? detail.category_stats
          .map(
            (row) => `
            <tr>
              <td>${row.category}</td>
              <td>${row.entries}</td>
              <td>${row.closed_positions}</td>
              <td>${row.open_positions}</td>
              <td>${money(row.deployed_capital)}</td>
              <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
              <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
            </tr>`
          )
          .join("")
      : "";
    const ledgerRows = [
      ...(detail.simulated_trades || []).map((row) => ({ ...row, status: "executed" })),
      ...(detail.pending_next_close_orders || []),
    ];
    const benchmark = detail.benchmark_comparison;
    const pendingActionRows = (detail.pending_next_close_orders || [])
      .map(
        (row) => `
        <tr class="pending-row">
          <td>${row.date}</td>
          <td>${row.signal_observed_date}</td>
          <td>${row.action}</td>
          <td>${tickerLabel(row.ticker)}</td>
          <td>${row.entry_signal}</td>
          <td>${row.execution_price === null ? "-" : money(row.execution_price)}</td>
          <td>${row.quantity === null ? "-" : number(row.quantity)}</td>
          <td>${row.usd_amount === null ? "-" : money(row.usd_amount)}</td>
        </tr>`
      )
      .join("");
    const tradeRows = ledgerRows
      .map(
        (row) => `
        <tr class="${row.status === "pending" ? "pending-row" : ""}">
          <td>${row.status}</td>
          <td>${row.date}</td>
          <td>${row.signal_observed_date}</td>
          <td>${row.action}</td>
          <td>${tickerLabel(row.ticker)}</td>
          <td>${row.entry_signal}</td>
          <td>${row.execution_price === null ? "-" : money(row.execution_price)}</td>
          <td>${row.quantity === null ? "-" : number(row.quantity)}</td>
          <td>${row.usd_amount === null ? "-" : money(row.usd_amount)}</td>
          <td class="${row.gain_loss === null ? "" : tone(row.gain_loss)}">${row.gain_loss === null ? "-" : money(row.gain_loss)}</td>
        </tr>`
      )
      .join("");
    openDrawer(`
      <p class="eyebrow">${detail.source}</p>
      <h2>${detail.investor}</h2>
      <p class="portfolio-description">${escapeHtml(portfolioDescription(detail))}</p>
      ${relatedResearchHtml([detail.investor, detail.source, ...(detail.positions || []).map((position) => position.ticker)], ["strategy", "signals", "watchlist"])}
      <div class="detail-grid">
        ${stat("Starting value", money(detail.initial_value))}
        ${stat("Current value", money(detail.current_value))}
        ${stat("Daily", pctOrDash(detail.daily_change_pct), toneOrEmpty(detail.daily_change_pct))}
        ${stat("5D", pctOrDash(detail.five_day_change_pct), toneOrEmpty(detail.five_day_change_pct))}
        ${stat("Monthly", pctOrDash(detail.monthly_change_pct), toneOrEmpty(detail.monthly_change_pct))}
        ${stat("Return", pct(detail.return_pct), tone(detail.return_pct))}
        ${benchmark ? stat(`${benchmark.benchmark} return`, pct(benchmark.benchmark_return_pct), tone(benchmark.benchmark_return_pct)) : ""}
        ${benchmark ? stat("Alpha", pct(benchmark.alpha_pct), tone(benchmark.alpha_pct)) : ""}
        ${benchmark ? stat("Volatility", pct(benchmark.volatility_pct)) : ""}
        ${benchmark ? stat("Max drawdown", pct(benchmark.max_drawdown_pct), tone(benchmark.max_drawdown_pct)) : ""}
        ${benchmark ? stat("Best / worst day", `${pct(benchmark.best_day_pct)} / ${pct(benchmark.worst_day_pct)}`) : ""}
        ${benchmark ? stat("Win vs benchmark", pct(benchmark.win_rate_vs_benchmark_pct)) : ""}
        ${detail.wealthsimple_fx_fees_estimate === undefined ? "" : stat("Estimated USD FX fees", money(detail.wealthsimple_fx_fees_estimate))}
      </div>
      ${benchmark ? `
        <h3>Portfolio vs ${benchmark.benchmark}</h3>
        <div class="chart">${comparisonPolyline(detail.series, benchmark.benchmark_series)}</div>` : ""}
      <h3>Drawdown</h3>
      <div class="chart">${drawdownPolyline(detail.series)}</div>
      <h3>Rolling returns</h3>
      <div class="chart">${rollingReturnPolyline(detail.series)}</div>
      <h3>Daily portfolio value</h3>
      <div class="chart">${polyline(detail.series, "value")}</div>
      ${contributorsHtml(detail)}
      ${sectorExposureHtml(detail)}
      ${signalMixHtml(detail)}
      ${capitalDeploymentHtml(detail)}
      <div class="drawer-section-heading">
        <h3>Holdings</h3>
        <button class="secondary small" data-export-table="#trader-holdings-table" data-export-name="holdings-${detail.investor}" data-export-title="${detail.investor} Holdings">Download holdings</button>
      </div>
      <div class="table-wrap">
        <table id="trader-holdings-table" data-sortable><thead><tr><th>Ticker</th><th>Start</th><th>Current</th><th>Gain / loss</th><th>Daily</th><th>5D</th><th>Monthly</th><th>Return</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>
      ${realizedRows ? `
        <div class="drawer-section-heading">
          <h3>Realized positions</h3>
          <button class="secondary small" data-export-table="#trader-realized-table" data-export-name="realized-positions-${detail.investor}" data-export-title="${detail.investor} Realized Positions">Download realized</button>
        </div>
        <p class="muted">Previously exited positions with entry/exit dates and realized gain/loss.</p>
        <div class="table-wrap">
          <table id="trader-realized-table" data-sortable>
            <thead><tr><th>Ticker</th><th>Entry signal</th><th>Entry observed</th><th>Entry date</th><th>Exit observed</th><th>Exit date</th><th>Entry price</th><th>Exit price</th><th>Start</th><th>Ending</th><th>Gain / loss</th><th>Return</th></tr></thead>
            <tbody>${realizedRows}</tbody>
          </table>
        </div>` : ""}
      ${detail.category_stats ? `
        <div class="drawer-section-heading">
          <h3>Entry signal category results</h3>
          <button class="secondary small" data-export-table="#trader-category-table" data-export-name="entry-signal-results-${detail.investor}" data-export-title="${detail.investor} Entry Signal Results">Download categories</button>
        </div>
        <p class="muted">${detail.category_stats_scope}</p>
        <div class="table-wrap">
          <table id="trader-category-table" data-sortable>
            <thead><tr><th>Category</th><th>Entries</th><th>Closed</th><th>Open</th><th>Deployed</th><th>Gain / loss</th><th>Return</th></tr></thead>
            <tbody>${categoryRows}</tbody>
          </table>
        </div>` : ""}
      ${pendingActionRows ? `
        <div class="drawer-section-heading">
          <h3>Upcoming next-close actions</h3>
          <button class="secondary small" data-export-table="#trader-pending-table" data-export-name="pending-actions-${detail.investor}" data-export-title="${detail.investor} Pending Actions">Download pending</button>
        </div>
        <p class="muted">These are trades observed after the selected To-date close. They should be executed at the next available close under the current EOD convention.</p>
        <div class="table-wrap">
          <table id="trader-pending-table" data-sortable>
            <thead><tr><th>Execution date</th><th>Observed after close</th><th>Action</th><th>Ticker</th><th>Entry signal</th><th>Execution price</th><th>Quantity</th><th>USD amount</th></tr></thead>
            <tbody>${pendingActionRows}</tbody>
          </table>
        </div>` : ""}
      ${detail.simulated_trades ? `
        <div class="drawer-section-heading">
          <h3>Simulated EOD trade ledger</h3>
          <button class="secondary small" data-export-table="#trader-ledger-table" data-export-name="trade-ledger-${detail.investor}" data-export-title="${detail.investor} Simulated Trade Ledger">Download ledger</button>
        </div>
        <p class="muted">${detail.execution_convention}</p>
        <p class="muted">${(detail.pending_next_close_orders || []).length} pending order(s) observed after the selected To-date close.</p>
        <div class="table-wrap">
          <table id="trader-ledger-table" data-sortable>
            <thead><tr><th>Status</th><th>Execution date</th><th>Observed after close</th><th>Action</th><th>Ticker</th><th>Entry signal</th><th>Execution price</th><th>Quantity</th><th>USD amount</th><th>Realized gain / loss</th></tr></thead>
            <tbody>${tradeRows}</tbody>
          </table>
        </div>` : ""}
      ${detail.note ? `<p class="muted">${detail.note}</p>` : ""}
    `);
    enableSorting($("#drawer-content"));
    document.querySelectorAll("[data-export-table]").forEach((button) =>
      button.addEventListener("click", () => exportNamedDrawerTable(button))
    );
  } catch (error) {
    openDrawer(`<p class="error">${error.message}</p>`);
  }
}

async function openStock(ticker) {
  openDrawer(loadingPanel(`Loading ${ticker} prices, signals, and news...`));
  try {
    const [detail, news] = await Promise.all([
      fetchJson(`/api/stocks/${encodeURIComponent(ticker)}?${query()}`),
      fetchJson(`/api/stocks/${encodeURIComponent(ticker)}/news`),
    ]);
    const signalRows = detail.signal
      ? ["3d", "5d", "1w", "1m", "3m"]
          .map((key) => detail.signal.horizons[key])
          .filter(Boolean)
          .map(
            (row) => `
            <tr>
              <td>${row.label}</td>
              <td>${row.start_date}</td>
              <td class="${tone(row.return_pct)}">${pct(row.return_pct)}</td>
              <td class="${tone(row.relative_strength_pct)}">${pct(row.relative_strength_pct)}</td>
              <td>${number(row.volume_ratio)}x</td>
              <td>${pct(row.distance_to_20d_high_pct)}</td>
              <td>${number(row.score)}</td>
              <td>${classificationPill(row.classification, row.fresh_priority ? "fresh" : row.classification)}</td>
            </tr>`
          )
          .join("")
      : "";
    const newsRows = news.articles.length
      ? news.articles
          .map(
            (row) => `
            <li>
              <a href="${safeUrl(row.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.headline)}</a>
              <span>${escapeHtml(row.created_at.slice(0, 10))} | ${escapeHtml(row.domain)}</span>
            </li>`
          )
          .join("")
      : '<li class="muted">No matching articles were returned by the available free sources.</li>';
    const sourceRows = news.sources
      .map((row) => `${escapeHtml(row.source)}: ${escapeHtml(row.status)}${row.detail ? ` (${escapeHtml(row.detail)})` : ""}`)
      .join(" | ");
    const videoRows = news.videos.length
      ? news.videos
          .map(
            (row) => `
            <li>
              <a href="${safeUrl(row.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.headline)}</a>
              <span>${escapeHtml(row.created_at.slice(0, 10))} | YouTube</span>
            </li>`
          )
          .join("")
      : '<li class="muted">YouTube collection is unavailable or returned no matching videos.</li>';
    openDrawer(`
      <p class="eyebrow">${detail.security_type} | ${detail.currency}</p>
      <h2>${tickerLabel(detail.ticker, detail.wealthsimple)}</h2>
      <p class="muted">${detail.owners.join(", ")}</p>
      ${relatedResearchHtml([detail.ticker, detail.sector, detail.owners.join(", "), detail.security_type], ["sector", "signals", "news"])}
      <div class="asset-action-panel">
        <p class="muted">Universe actions update tracking metadata only. They do not create trades.</p>
        <div class="asset-action-group left">
          <button class="asset-action" data-stock-universe-action="candidate" data-stock-ticker="${escapeHtml(detail.ticker)}" data-stock-type="${escapeHtml(detail.security_type)}">Candidate</button>
          <button class="asset-action" data-stock-universe-action="active" data-stock-ticker="${escapeHtml(detail.ticker)}" data-stock-type="${escapeHtml(detail.security_type)}">Active</button>
          <button class="asset-action" data-stock-universe-action="strategy_eligible" data-stock-ticker="${escapeHtml(detail.ticker)}" data-stock-type="${escapeHtml(detail.security_type)}">Strategy eligible</button>
          <button class="asset-action" data-stock-universe-action="archived" data-stock-ticker="${escapeHtml(detail.ticker)}" data-stock-type="${escapeHtml(detail.security_type)}">Archive</button>
          <button class="asset-action" data-stock-universe-action="excluded" data-stock-ticker="${escapeHtml(detail.ticker)}" data-stock-type="${escapeHtml(detail.security_type)}">Exclude</button>
        </div>
        <p id="stock-universe-action-status" class="muted"></p>
      </div>
      <div class="detail-grid">
        ${stat("Start price", number(detail.start_price))}
        ${stat("Latest price", number(detail.end_price))}
        ${stat("Daily", pctOrDash(detail.daily_change_pct), toneOrEmpty(detail.daily_change_pct))}
        ${stat("5D", pctOrDash(detail.five_day_change_pct), toneOrEmpty(detail.five_day_change_pct))}
        ${stat("Monthly", pctOrDash(detail.monthly_change_pct), toneOrEmpty(detail.monthly_change_pct))}
        ${stat("Return", pct(detail.return_pct), tone(detail.return_pct))}
      </div>
      <h3>Daily close</h3>
      <div class="chart">${polyline(detail.series, "price")}</div>
      <div class="detail-grid">
        ${stat("Overall signal", detail.signal ? classificationPill(detail.signal.overall_classification) : "-")}
        ${stat("Weighted score", detail.signal ? `${number(detail.signal.overall_score)} / 100` : "-")}
        ${stat("5d vs SPY", detail.signal ? pct(detail.signal.five_day_relative_strength_pct) : "-", detail.signal ? tone(detail.signal.five_day_relative_strength_pct) : "")}
        ${stat("5d volume", detail.signal ? `${number(detail.signal.five_day_volume_ratio)}x` : "-")}
        ${stat("Distance to 20d high", detail.signal ? pct(detail.signal.distance_to_20d_high_pct) : "-")}
      </div>
      <h3>Multi-horizon signal indicators</h3>
      <p class="muted">The weighted score combines 3-day, 5-day, 1-week, and 1-month indicators. Scores now include relative strength versus SPY; the 3-month signal is shown as context.</p>
      <div class="table-wrap signal-matrix">
        <table data-sortable>
          <thead><tr><th>Horizon</th><th>From</th><th>Return</th><th>Vs SPY</th><th>Volume ratio</th><th>Distance to high</th><th>Score</th><th>Signal</th></tr></thead>
          <tbody>${signalRows}</tbody>
        </table>
      </div>
      <h3>Free news activity</h3>
      <div class="detail-grid">
        ${stat("Articles, latest 24h", number(news.articles_24h))}
        ${stat("Articles, latest 7d", number(news.articles_7d))}
        ${stat("Prior 7d", number(news.articles_prior_7d))}
        ${stat("News velocity", news.daily_velocity_ratio === null ? "-" : `${number(news.daily_velocity_ratio)}x`)}
        ${stat("Source diversity, 7d", number(news.source_diversity_7d))}
        ${stat("Snapshot", escapeHtml(news.snapshot_date))}
      </div>
      <h3>News activity trend</h3>
      <div class="chart">${newsActivityPolyline(news.daily_counts || [])}</div>
      <p class="muted">${escapeHtml(news.note)}</p>
      <p class="source-status">${sourceRows}</p>
      <ul class="news-list">${newsRows}</ul>
      <h3>Free YouTube activity</h3>
      <div class="detail-grid">
        ${stat("Videos, latest 7d", number(news.videos_7d))}
        ${stat("Videos, prior 7d", number(news.videos_prior_7d))}
        ${stat("Video velocity", news.video_velocity_ratio === null ? "-" : `${number(news.video_velocity_ratio)}x`)}
      </div>
      <ul class="news-list">${videoRows}</ul>
    `);
    enableSorting($("#drawer-content"));
    document.querySelectorAll("[data-stock-universe-action]").forEach((button) =>
      button.addEventListener("click", () =>
        saveStockUniverseAction(
          button.dataset.stockTicker,
          button.dataset.stockType,
          button.dataset.stockUniverseAction
        )
      )
    );
  } catch (error) {
    openDrawer(`<p class="error">${error.message}</p>`);
  }
}

function rankTraders() {
  state.overview.traders.sort((left, right) => Number(right.return_pct || 0) - Number(left.return_pct || 0));
  state.overview.traders.forEach((row, index) => {
    row.rank = index + 1;
  });
}

function mergePortfolioRows(rows = []) {
  if (!state.overview || !Array.isArray(state.overview.traders)) return;
  const byInvestor = new Map(
    state.overview.traders.map((row) => [String(row.investor || "").toLowerCase(), row])
  );
  rows.forEach((row) => {
    byInvestor.set(String(row.investor || "").toLowerCase(), row);
  });
  state.overview.traders = [...byInvestor.values()];
  rankTraders();
}

async function refreshPaperLedgerPortfolios() {
  const payload = await fetchJson(`/api/paper-ledger-portfolios?${query()}`);
  mergePortfolioRows(payload.traders || []);
}

function applyPreloadPreset(preloadPreset) {
  if (!preloadPreset) return;
  $("#from-date").value = preloadPreset.from_date;
  $("#to-date").value = preloadPreset.to_date;
  $("#from-quick-date").value = preloadPreset.from_date;
  $("#to-quick-date").value = preloadPreset.to_date;
  $("#wealthsimple-fx-fees").checked = Boolean(preloadPreset.includes_wealthsimple_fx_fees);
}

function renderPreloadPresetControl(preloadPreset) {
  if (!preloadPreset) return;
  const label = preloadPreset.cache_available ? preloadPreset.label : `${preloadPreset.label} (may build cache)`;
  $("#preload-preset").textContent = preloadPreset.includes_wealthsimple_fx_fees
    ? `${label} + fees`
    : label;
}

async function refreshMeta() {
  state.meta = await fetchJson("/api/meta");
  renderPreloadPresetControl(state.meta.preload_preset);
  return state.meta;
}

async function rebuildPreloadAndLoad() {
  $("#content").classList.add("hidden");
  $("#error").classList.add("hidden");
  setNotificationStatus("");
  $("#rebuild-preload").disabled = true;
  $("#apply-window").disabled = true;
  $("#rebuild-preload").textContent = "Recalculating...";
  setLoading("Starting preload cache recalculation...", 5);
  try {
    await waitForPreloadRebuild();
    updateLoading("Preload rebuilt. Refreshing dashboard metadata...", 85);
    const meta = await refreshMeta();
    applyPreloadPreset(meta.preload_preset);
    updateLoading("Preload rebuilt. Loading refreshed dashboard...", 92);
    clearLoading();
    await loadOverview();
  } catch (error) {
    $("#error").textContent = error.message;
    $("#error").classList.remove("hidden");
  } finally {
    clearLoading();
    $("#rebuild-preload").disabled = false;
    $("#apply-window").disabled = false;
    $("#rebuild-preload").textContent = "Recalculate preload";
  }
}

async function loadOverview() {
  if (!$("#from-date").value || !$("#to-date").value) {
    $("#error").textContent = "Select both a From date and a To date before refreshing.";
    $("#error").classList.remove("hidden");
    return;
  }
  $("#content").classList.add("hidden");
  $("#error").classList.add("hidden");
  setNotificationStatus("");
  $("#apply-window").disabled = true;
  $("#apply-window").textContent = "Refreshing...";
  setLoading("Refreshing portfolio rankings and tracked instruments...", 5);
  try {
    state.overview = await fetchOverviewWithJob();
    state.modelPortfolio = null;
    state.modelPortfolioToDate = null;
    state.modelPortfolioV2 = null;
    state.modelPortfolioV2ToDate = null;
    state.modelPortfolioV3 = null;
    state.modelPortfolioV3ToDate = null;
    state.modelPortfolioV4 = null;
    state.modelPortfolioV4ToDate = null;
    state.dayRotationPortfolio = null;
    state.dayRotationToDate = null;
    state.riskPortfolio = null;
    state.riskRequestKey = null;
    state.riskCorrelation = null;
    state.riskCorrelationRequestKey = null;
    state.riskScenarios = null;
    state.riskScenarioRequestKey = null;
    state.wealthAllocation = null;
    state.wealthAllocationRequestKey = null;
    state.wealthPerformance = null;
    state.wealthPerformanceRequestKey = null;
    state.strategySelector = null;
    state.strategySelectorRequestKey = null;
    state.automatedReview = null;
    state.automatedReviewRequestKey = null;
    state.marketNews = null;
    state.marketNewsRequestKey = null;
    updateLoading("Portfolio rankings and tracked instruments loaded. Refreshing paper-ledger portfolios...", 72);
    await refreshPaperLedgerPortfolios();
    updateLoading("Paper-ledger portfolios refreshed. Loading prior-close movers...", 75);
    state.eod = await fetchJson(`/api/eod${wealthsimpleQuery()}`);
    updateLoading("Prior-close movers loaded. Loading universe registries...", 88);
    await refreshUniverse();
    updateLoading("Universe registries loaded. Building AI wealth intelligence...", 92);
    state.wealthIntelligence = await fetchJson(`/api/wealth-intelligence?${query()}`);
    updateLoading("AI wealth intelligence loaded. Building wealth operations workflow...", 94);
    state.wealthOperations = await fetchJson(`/api/wealth-operations?${query()}`);
    state.externalPortfolios = await fetchJson("/api/external-portfolios");
    updateLoading("Wealth operations workflow loaded. Rendering dashboard tables...", 96);
    renderCards();
    renderCommandCenter();
    renderDiagnostics();
    renderWealthIntelligence();
    renderWealthOperations();
    renderWealthOverview();
    renderExternalPortfolios();
    populateRiskPortfolioOptions();
    renderEod();
    renderSectors();
    renderTraders();
    renderLowPriorityControls();
    renderRecommendations();
    renderStocks();
    $("#window-label").textContent =
      `${state.overview.from_date} to ${state.overview.latest_available_date || "latest available close"}`
      + (state.overview.wealthsimple_fx_fees_enabled ? " | Wealthsimple CAD-account USD FX fees enabled" : "");
    $("#content").classList.remove("hidden");
    if (activeDashboardTab() === "model-portfolio") {
      loadModelPortfolio().catch(() => {});
    }
    if (activeDashboardTab() === "model-portfolio-v2") {
      loadModelPortfolioV2().catch(() => {});
    }
    if (activeDashboardTab() === "model-portfolio-v3") {
      loadModelPortfolioV3().catch(() => {});
    }
    if (activeDashboardTab() === "model-portfolio-v4") {
      loadModelPortfolioV4().catch(() => {});
    }
    if (activeDashboardTab() === "day-rotation") {
      loadDayRotationPortfolio().catch(() => {});
    }
    if (activeDashboardTab() === "risk") {
      loadRiskPortfolio().catch(() => {});
    }
    if (activeDashboardTab() === "allocation") {
      loadWealthAllocation().catch(() => {});
    }
    if (activeDashboardTab() === "performance") {
      loadWealthPerformance().catch(() => {});
    }
    if (activeDashboardTab() === "market-news") {
      loadMarketNews().catch(() => {});
    }
    if (activeDashboardTab() === "wealth-overview") {
      loadStrategySelector().catch(() => {});
      loadAutomatedReview().catch(() => {});
    }
    updateLoading("Dashboard ready.", 100);
    sendDailyInstructionsEmail().then((notification) => {
      setNotificationStatus(notificationMessage(notification), notification.status);
    });
  } catch (error) {
    $("#error").textContent = error.message;
    $("#error").classList.remove("hidden");
  } finally {
    clearLoading();
    $("#apply-window").disabled = false;
    $("#apply-window").textContent = "Refresh dashboard";
  }
}

async function init() {
  const meta = await fetchJson("/api/meta");
  state.meta = meta;
  const preloadPreset = meta.preload_preset;
  $("#from-quick-date").innerHTML = dateOptions(meta);
  $("#to-quick-date").innerHTML = dateOptions(meta, true);
  $("#from-quick-date").insertAdjacentHTML("afterbegin", '<option value="">Choose date</option>');
  $("#to-quick-date").insertAdjacentHTML("afterbegin", '<option value="">Choose date</option>');
  $("#from-date").value = "";
  $("#to-date").value = "";
  $("#from-quick-date").value = "";
  $("#to-quick-date").value = "";
  $("#from-quick-date").addEventListener("change", () => {
    $("#from-date").value = $("#from-quick-date").value;
  });
  $("#to-quick-date").addEventListener("change", () => {
    $("#to-date").value = $("#to-quick-date").value;
  });
  $("#from-date").addEventListener("change", () => {
    $("#from-quick-date").value = $("#from-date").value;
  });
  $("#to-date").addEventListener("change", () => {
    $("#to-quick-date").value = $("#to-date").value;
  });
  if (preloadPreset) {
    renderPreloadPresetControl(preloadPreset);
    $("#preload-preset").addEventListener("click", () => {
      applyPreloadPreset(state.meta.preload_preset);
    });
  }
  $("#apply-window").addEventListener("click", loadOverview);
  $("#rebuild-preload").addEventListener("click", rebuildPreloadAndLoad);
  document.querySelectorAll("[data-workspace-target]").forEach((button) => {
    button.addEventListener("click", () => setActiveWorkspace(button.dataset.workspaceTarget));
  });
  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => setActiveDashboardTab(button.dataset.tabTarget));
  });
  window.addEventListener("hashchange", () => setActiveDashboardTab(activeDashboardTab(), false));
  setActiveDashboardTab(activeDashboardTab(), false);
  $("#run-strategy-lab").addEventListener("click", runStrategyLab);
  $("#save-strategy-lab").addEventListener("click", saveStrategyLab);
  $("#export-strategy-lab").addEventListener("click", () => {
    downloadExcelTables(
      "strategy-lab-preview",
      "Strategy Lab Preview",
      [...document.querySelectorAll("#strategy-lab-result table")]
    );
  });
  $("#asset-form").addEventListener("submit", submitAssetForm);
  $("#benchmark-form").addEventListener("submit", submitBenchmarkForm);
  $("#basket-form").addEventListener("submit", submitBasketForm);
  $("#basket-member-form").addEventListener("submit", submitBasketMemberForm);
  $("#stock-search").addEventListener("input", renderStocks);
  $("#signal-filter").addEventListener("change", renderStocks);
  $("#export-eod").addEventListener("click", () => {
    downloadExcelTables(
      "daily-eod-movers",
      "Daily EOD Movers",
      [$("#eod-trader-rows")?.closest("table"), $("#eod-stock-rows")?.closest("table")]
    );
  });
  $("#reload-market-news").addEventListener("click", () => loadMarketNews(true));
  $("#export-market-news").addEventListener("click", () => {
    downloadExcelTables(
      "market-news-headlines",
      "News Headlines and Social Mentions",
      [
        $("#market-topic-table"),
        $("#market-hot-stock-table"),
        $("#market-headline-table"),
        $("#market-social-table"),
        $("#market-news-source-table"),
      ]
    );
  });
  $("#export-traders").addEventListener("click", () => {
    downloadExcelTables("traders", "Portfolio Performance - Traders", [$("#trader-rows")?.closest("table")]);
  });
  document.querySelectorAll("[data-show-low-priority]").forEach((input) => {
    input.addEventListener("change", (event) => {
      state.showLowPriorityPortfolios = Boolean(event.target.checked);
      if (state.overview && state.eod) {
        renderPortfolioVisibilityViews();
      } else {
        renderLowPriorityControls();
      }
    });
  });
  $("#export-sectors").addEventListener("click", () => {
    downloadExcelTables("sector-breakdown", "Sector Breakdown", [$("#sector-rows")?.closest("table")]);
  });
  $("#export-ai-wealth").addEventListener("click", () => {
    downloadExcelTables(
      "ai-wealth-intelligence",
      "AI Wealth Intelligence",
      [
        $("#wealth-ops-module-rows")?.closest("table"),
        $("#external-portfolio-rows")?.closest("table"),
        $("#wealth-command-rows")?.closest("table"),
        $("#wealth-profile-rows")?.closest("table"),
        $("#wealth-proposal-rows")?.closest("table"),
        $("#wealth-review-rows")?.closest("table"),
        $("#ai-wealth-theme-rows")?.closest("table"),
        $("#ai-wealth-market-rows")?.closest("table"),
        $("#ai-wealth-basket-rows")?.closest("table"),
        $("#ai-wealth-candidate-rows")?.closest("table"),
      ]
    );
  });
  $("#reload-strategy-selector").addEventListener("click", () => loadStrategySelector(true));
  $("#reload-automated-review").addEventListener("click", () => loadAutomatedReview(true));
  $("#export-strategy-selector").addEventListener("click", () => {
    downloadExcelTables(
      "strategy-selector",
      "Investment Committee Strategy Selector",
      [$("#strategy-selector-table")]
    );
  });
  $("#reload-risk").addEventListener("click", () => loadRiskPortfolio(true));
  $("#risk-portfolio-select").addEventListener("change", () => loadRiskPortfolio(true));
  $("#load-risk-correlation").addEventListener("click", () => loadRiskCorrelation(true));
  $("#load-risk-scenarios").addEventListener("click", () => loadRiskScenarios(true));
  $("#export-risk").addEventListener("click", () => {
    downloadExcelTables(
      "portfolio-risk",
      "Portfolio Risk and Concentration",
      [$("#risk-sector-table"), $("#risk-correlation-table"), $("#risk-scenario-table")]
    );
  });
  $("#reload-allocation").addEventListener("click", () => loadWealthAllocation(true));
  $("#export-allocation").addEventListener("click", () => {
    downloadExcelTables(
      "wealth-allocation",
      "Allocation and Overlap",
      [
        $("#allocation-portfolio-table"),
        $("#allocation-sector-table"),
        $("#allocation-type-table"),
        $("#allocation-currency-table"),
        $("#allocation-security-table"),
      ]
    );
  });
  $("#reload-performance").addEventListener("click", () => loadWealthPerformance(true));
  $("#performance-portfolio-select").addEventListener("change", () => loadWealthPerformance(true));
  $("#export-performance").addEventListener("click", () => {
    downloadExcelTables(
      "wealth-performance",
      "Performance and Contribution",
      [$("#performance-contribution-table")]
    );
  });
  $("#rebalance-profile").addEventListener("change", renderRebalanceInputs);
  $("#run-rebalance").addEventListener("click", runRebalancePreview);
  $("#export-rebalance").addEventListener("click", () => {
    downloadExcelTables("rebalance-preview", "Draft Rebalance Preview", [$("#rebalance-result-table")]);
  });
  $("#reload-model-portfolio").addEventListener("click", () => loadModelPortfolio(true));
  $("#export-model-portfolio").addEventListener("click", () => {
    downloadExcelTables(
      "systematic-model-portfolio",
      "Systematic Model Portfolio",
      [
        $("#model-pending-table"),
        $("#model-holdings-table"),
        $("#model-sector-table"),
        $("#model-rebalance-table"),
        $("#model-trades-table"),
      ]
    );
  });
  $("#reload-model2-portfolio").addEventListener("click", () => loadModelPortfolioV2(true));
  $("#export-model2-portfolio").addEventListener("click", () => {
    downloadExcelTables(
      "systematic-model-portfolio-2",
      "Systematic Model Portfolio 2.0",
      [
        $("#model2-drawdown-table"),
        $("#model2-pending-table"),
        $("#model2-holdings-table"),
        $("#model2-sector-table"),
        $("#model2-rebalance-table"),
        $("#model2-trades-table"),
      ]
    );
  });
  $("#reload-model3-portfolio").addEventListener("click", () => loadModelPortfolioV3(true));
  $("#export-model3-portfolio").addEventListener("click", () => {
    downloadExcelTables(
      "systematic-model-portfolio-3",
      "Systematic Model Portfolio 3.0",
      [
        $("#model3-drawdown-table"),
        $("#model3-pending-table"),
        $("#model3-holdings-table"),
        $("#model3-sector-table"),
        $("#model3-rebalance-table"),
        $("#model3-trades-table"),
      ]
    );
  });
  $("#reload-model4-portfolio").addEventListener("click", () => loadModelPortfolioV4(true));
  $("#export-model4-portfolio").addEventListener("click", () => {
    downloadExcelTables(
      "systematic-model-portfolio-4",
      "Systematic Model Portfolio 4.0",
      [
        $("#model4-drawdown-table"),
        $("#model4-pending-table"),
        $("#model4-holdings-table"),
        $("#model4-sector-table"),
        $("#model4-rebalance-table"),
        $("#model4-trades-table"),
      ]
    );
  });
  $("#reload-rotation").addEventListener("click", () => loadDayRotationPortfolio(true));
  $("#export-rotation").addEventListener("click", () => {
    downloadExcelTables(
      "daily-eod-rotation-portfolio",
      "Daily EOD Rotation Portfolio",
      [
        $("#rotation-pending-table"),
        $("#rotation-holdings-table"),
        $("#rotation-sector-table"),
        $("#rotation-rebalance-table"),
        $("#rotation-trades-table"),
      ]
    );
  });
  $("#export-universe").addEventListener("click", () => {
    downloadExcelTables(
      "asset-universe",
      "Asset Universe and Benchmarks",
      [$("#asset-universe-rows")?.closest("table"), $("#asset-event-rows")?.closest("table"), $("#benchmark-rows")?.closest("table")]
    );
  });
  $("#export-stocks").addEventListener("click", () => {
    downloadExcelTables("tracked-stocks", "Tracked Stocks", [$("#stock-rows")?.closest("table")]);
  });
  $("#export-drawer").addEventListener("click", () => {
    const title = $("#drawer-content h2")?.textContent || "Dashboard Drilldown";
    downloadExcelTables(`drilldown-${title}`, title, [...document.querySelectorAll("#drawer-content table")]);
  });
  $("#close-drawer").addEventListener("click", closeDrawer);
  $("#backdrop").addEventListener("click", closeDrawer);
}

init().catch((error) => {
  clearLoading();
  $("#error").textContent = error.message;
  $("#error").classList.remove("hidden");
});
