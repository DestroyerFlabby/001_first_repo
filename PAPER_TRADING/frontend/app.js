const state = { overview: null, eod: null, meta: null, universe: null, benchmarks: null, strategies: null, baskets: null, research: null };
const $ = (selector) => document.querySelector(selector);
let loadingTimer = null;
let loadingStartedAt = null;

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
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

const jsonRequest = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

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
  table.querySelectorAll("th").forEach((header) => header.classList.remove("sort-asc", "sort-desc"));
  table.tHead.rows[0].cells[column].classList.add(`sort-${direction}`);
}

function enableSorting(root = document) {
  root.querySelectorAll("table[data-sortable]").forEach((table) => {
    if (table.dataset.sortReady) return;
    table.dataset.sortReady = "true";
    table.querySelectorAll("thead th").forEach((header, column) => {
      header.addEventListener("click", () => {
        const direction = header.classList.contains("sort-asc") ? "desc" : "asc";
        sortTable(table, column, direction);
      });
    });
  });
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
            <button class="asset-action" data-recommendation-action="${escapeHtml(action)}" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}">Approve</button>
            <button class="asset-action" data-recommendation-action="candidate" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}">Watch</button>
            <button class="asset-action" data-recommendation-action="archived" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}">Archive</button>
            <button class="asset-action" data-recommendation-action="excluded" data-recommendation-ticker="${escapeHtml(stock.ticker)}" data-recommendation-type="${escapeHtml(stock.security_type)}">Ignore</button>
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
        button.dataset.recommendationAction
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
    status: "research",
    forward_test_start_date: $("#from-date").value || state.meta?.default_from_date || "",
    entry_rule: labLabels.entry[entry] || entry,
    exit_rule: labLabels.exit[exit] || exit,
    news_rule: labLabels.entryNews[entryNews] || entryNews,
    universe: labLabels.universe[universe] || universe,
    benchmark: "SPY",
    position_size: "1000",
    notes: "Saved from the dashboard Strategy Lab. Registry-only entry; it does not create trades or generated portfolios yet.",
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

function renderCards() {
  const traders = state.overview.traders;
  const stocks = state.overview.stocks;
  const strict = stocks.filter((row) => row.signal?.classification === "strict").length;
  const fresh = stocks.filter((row) => row.signal?.fresh_priority).length;
  const leader = traders[0];
  const wsAvailability = state.overview.wealthsimple_availability;
  const topSector = state.overview.sector_breakdowns?.[0];
  $("#summary-cards").innerHTML = [
    ["Portfolios", traders.length, state.meta?.public_dashboard ? "Public paper ledgers" : "Paper ledgers plus imported account"],
    ["Tracked instruments", stocks.length, "Stocks, ETFs, and crypto"],
    ["Leading sector", topSector?.sector || "-", topSector ? pct(topSector.average_return_pct) : "-"],
    ["Fresh signal matches", fresh, `${strict} strict technical matches`],
    ["Leading portfolio", leader.investor, pct(leader.return_pct)],
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
  const traders = state.overview.traders || [];
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
  const suggestionRows = recommendations.slice(0, 5);
  $("#command-center-grid").innerHTML = [
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

async function saveStockUniverseAction(ticker, assetType, action) {
  const statusNode = $("#stock-universe-action-status") || $("#recommendation-action-status");
  const basePayload = {
    ticker,
    asset_type: assetType,
    source: "stock-drilldown-ui",
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

function renderTraders() {
  $("#trader-rows").innerHTML = state.overview.traders
    .map(
      (row) => `
      <tr class="clickable" data-trader="${row.investor}">
        <td>${row.rank}</td>
        <td><strong>${row.investor}</strong><br><span class="muted">${row.source}</span></td>
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

function renderEod() {
  $("#eod-window-label").textContent = `${state.eod.from_date} to ${state.eod.to_date}`;
  $("#eod-trader-rows").innerHTML = state.eod.traders
    .map(
      (row) => `
      <tr class="clickable" data-eod-trader="${row.investor}">
        <td><strong>${row.investor}</strong></td>
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

function renderSectors() {
  $("#sector-rows").innerHTML = (state.overview.sector_breakdowns || [])
    .map((row) => {
      const signals = row.signal_counts || {};
      return `
        <tr>
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

function openDrawer(html) {
  $("#drawer-content").innerHTML = html;
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
  $("#backdrop").classList.remove("hidden");
  $("#export-drawer").classList.toggle("hidden", !$("#drawer-content table"));
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
    const tradeRows = ledgerRows
      .map(
        (row) => `
        <tr>
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
    state.overview = await fetchJson(`/api/overview?${query()}`);
    updateLoading("Portfolio rankings and tracked instruments loaded. Loading prior-close movers...", 75);
    state.eod = await fetchJson(`/api/eod${wealthsimpleQuery()}`);
    updateLoading("Prior-close movers loaded. Loading universe registries...", 88);
    await refreshUniverse();
    updateLoading("Universe registries loaded. Rendering dashboard tables...", 95);
    renderCards();
    renderCommandCenter();
    renderDiagnostics();
    renderEod();
    renderSectors();
    renderTraders();
    renderRecommendations();
    renderStocks();
    $("#window-label").textContent =
      `${state.overview.from_date} to ${state.overview.latest_available_date || "latest available close"}`
      + (state.overview.wealthsimple_fx_fees_enabled ? " | Wealthsimple CAD-account USD FX fees enabled" : "");
    $("#content").classList.remove("hidden");
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
    $("#preload-preset").textContent = preloadPreset.includes_wealthsimple_fx_fees
      ? `${preloadPreset.label} + fees`
      : preloadPreset.label;
    $("#preload-preset").addEventListener("click", () => {
      $("#from-date").value = preloadPreset.from_date;
      $("#to-date").value = preloadPreset.to_date;
      $("#from-quick-date").value = preloadPreset.from_date;
      $("#to-quick-date").value = preloadPreset.to_date;
      $("#wealthsimple-fx-fees").checked = Boolean(preloadPreset.includes_wealthsimple_fx_fees);
    });
  }
  $("#apply-window").addEventListener("click", loadOverview);
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
  $("#stock-search").addEventListener("input", renderStocks);
  $("#signal-filter").addEventListener("change", renderStocks);
  $("#export-eod").addEventListener("click", () => {
    downloadExcelTables(
      "daily-eod-movers",
      "Daily EOD Movers",
      [$("#eod-trader-rows")?.closest("table"), $("#eod-stock-rows")?.closest("table")]
    );
  });
  $("#export-traders").addEventListener("click", () => {
    downloadExcelTables("traders", "Portfolio Performance - Traders", [$("#trader-rows")?.closest("table")]);
  });
  $("#export-sectors").addEventListener("click", () => {
    downloadExcelTables("sector-breakdown", "Sector Breakdown", [$("#sector-rows")?.closest("table")]);
  });
  $("#export-universe").addEventListener("click", () => {
    downloadExcelTables(
      "asset-universe",
      "Asset Universe and Benchmarks",
      [$("#asset-universe-rows")?.closest("table"), $("#benchmark-rows")?.closest("table")]
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
