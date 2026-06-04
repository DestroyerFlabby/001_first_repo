const state = { overview: null, eod: null, meta: null, universe: null, benchmarks: null };
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
  if (!state.universe || !state.benchmarks) return;
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
  document.querySelectorAll("[data-asset-action]").forEach((button) =>
    button.addEventListener("click", () => updateAssetStatus(button))
  );
  enableSorting();
}

async function refreshUniverse() {
  const [universe, benchmarks] = await Promise.all([
    fetchJson("/api/universe/assets"),
    fetchJson("/api/benchmarks"),
  ]);
  state.universe = universe;
  state.benchmarks = benchmarks;
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
      <h3>Daily portfolio value</h3>
      <div class="chart">${polyline(detail.series, "value")}</div>
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
    renderDiagnostics();
    renderEod();
    renderSectors();
    renderTraders();
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
