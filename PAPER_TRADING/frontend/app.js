const state = { overview: null, eod: null, meta: null };
const $ = (selector) => document.querySelector(selector);

const money = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value || 0);
const pct = (value) => `${value >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}%`;
const number = (value) => Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const tone = (value) => (Number(value) >= 0 ? "positive" : "negative");
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
  return params.toString();
};

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
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
  $("#summary-cards").innerHTML = [
    ["Portfolios", traders.length, state.meta?.public_dashboard ? "Public paper ledgers" : "Paper ledgers plus imported account"],
    ["Tracked instruments", stocks.length, "Stocks, ETFs, and crypto"],
    ["Fresh signal matches", fresh, `${strict} strict technical matches`],
    ["Leading portfolio", leader.investor, pct(leader.return_pct)],
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
        <td><strong>${row.ticker}</strong></td>
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

function filteredStocks() {
  const search = $("#stock-search").value.trim().toLowerCase();
  const filter = $("#signal-filter").value;
  return [...state.overview.stocks]
    .filter((row) => !row.warning)
    .filter((row) => {
      const haystack = `${row.ticker} ${row.owners.join(" ")}`.toLowerCase();
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
        <td><strong>${row.ticker}</strong><br><span class="muted">${row.yahoo_symbol}</span></td>
        <td>${row.security_type}</td>
        <td>${row.owners.join(", ")}</td>
        <td>${number(row.start_price)} ${row.currency}</td>
        <td>${number(row.end_price)} ${row.currency}</td>
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

function stat(label, value, className = "") {
  return `<div class="detail-stat"><p>${label}</p><p class="${className}">${value}</p></div>`;
}

function openDrawer(html) {
  $("#drawer-content").innerHTML = html;
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
  $("#backdrop").classList.remove("hidden");
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  $("#backdrop").classList.add("hidden");
}

async function openTrader(investor) {
  openDrawer(`<p class="loading">Loading ${investor}...</p>`);
  try {
    const detail = await fetchJson(`/api/traders/${encodeURIComponent(investor)}?${query()}`);
    const rows = detail.positions
      .map(
        (row) => `
        <tr>
          <td>${row.ticker}</td>
          <td>${money(row.initial_value)}</td>
          <td>${money(row.current_value)}</td>
          <td class="${tone(row.gain_loss)}">${money(row.gain_loss)}</td>
          <td class="${tone(row.return_pct || 0)}">${row.return_pct === undefined ? "-" : pct(row.return_pct)}</td>
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
    const tradeRows = ledgerRows
      .map(
        (row) => `
        <tr>
          <td>${row.status}</td>
          <td>${row.date}</td>
          <td>${row.signal_observed_date}</td>
          <td>${row.action}</td>
          <td>${row.ticker}</td>
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
        ${stat("Return", pct(detail.return_pct), tone(detail.return_pct))}
      </div>
      <h3>Daily portfolio value</h3>
      <div class="chart">${polyline(detail.series, "value")}</div>
      <h3>Holdings</h3>
      <div class="table-wrap">
        <table data-sortable><thead><tr><th>Ticker</th><th>Start</th><th>Current</th><th>Gain / loss</th><th>Return</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>
      ${detail.category_stats ? `
        <h3>Entry signal category results</h3>
        <p class="muted">${detail.category_stats_scope}</p>
        <div class="table-wrap">
          <table data-sortable>
            <thead><tr><th>Category</th><th>Entries</th><th>Closed</th><th>Open</th><th>Deployed</th><th>Gain / loss</th><th>Return</th></tr></thead>
            <tbody>${categoryRows}</tbody>
          </table>
        </div>` : ""}
      ${detail.simulated_trades ? `
        <h3>Simulated EOD trade ledger</h3>
        <p class="muted">${detail.execution_convention}</p>
        <p class="muted">${(detail.pending_next_close_orders || []).length} pending order(s) observed after the selected To-date close.</p>
        <div class="table-wrap">
          <table data-sortable>
            <thead><tr><th>Status</th><th>Execution date</th><th>Observed after close</th><th>Action</th><th>Ticker</th><th>Entry signal</th><th>Execution price</th><th>Quantity</th><th>USD amount</th><th>Realized gain / loss</th></tr></thead>
            <tbody>${tradeRows}</tbody>
          </table>
        </div>` : ""}
      ${detail.note ? `<p class="muted">${detail.note}</p>` : ""}
    `);
    enableSorting($("#drawer-content"));
  } catch (error) {
    openDrawer(`<p class="error">${error.message}</p>`);
  }
}

async function openStock(ticker) {
  openDrawer(`<p class="loading">Loading ${ticker}...</p>`);
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
      <h2>${detail.ticker}</h2>
      <p class="muted">${detail.owners.join(", ")}</p>
      <div class="detail-grid">
        ${stat("Start price", number(detail.start_price))}
        ${stat("Latest price", number(detail.end_price))}
        ${stat("Return", pct(detail.return_pct), tone(detail.return_pct))}
      </div>
      <h3>Daily close</h3>
      <div class="chart">${polyline(detail.series, "price")}</div>
      <div class="detail-grid">
        ${stat("Overall signal", detail.signal ? classificationPill(detail.signal.overall_classification) : "-")}
        ${stat("Weighted score", detail.signal ? `${number(detail.signal.overall_score)} / 100` : "-")}
        ${stat("5d volume", detail.signal ? `${number(detail.signal.five_day_volume_ratio)}x` : "-")}
        ${stat("Distance to 20d high", detail.signal ? pct(detail.signal.distance_to_20d_high_pct) : "-")}
      </div>
      <h3>Multi-horizon signal indicators</h3>
      <p class="muted">The weighted score combines 3-day, 5-day, 1-week, and 1-month indicators. The 3-month signal is shown as context.</p>
      <div class="table-wrap signal-matrix">
        <table data-sortable>
          <thead><tr><th>Horizon</th><th>From</th><th>Return</th><th>Volume ratio</th><th>Distance to high</th><th>Score</th><th>Signal</th></tr></thead>
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
  $("#content").classList.add("hidden");
  $("#error").classList.add("hidden");
  $("#loading").classList.remove("hidden");
  try {
    state.overview = await fetchJson(`/api/overview?${query()}`);
    state.eod = await fetchJson("/api/eod");
    renderCards();
    renderEod();
    renderTraders();
    renderStocks();
    $("#window-label").textContent =
      `${state.overview.from_date} to ${state.overview.latest_available_date || "latest available close"}`;
    $("#content").classList.remove("hidden");
  } catch (error) {
    $("#error").textContent = error.message;
    $("#error").classList.remove("hidden");
  } finally {
    $("#loading").classList.add("hidden");
  }
}

async function init() {
  const meta = await fetchJson("/api/meta");
  state.meta = meta;
  $("#from-quick-date").innerHTML = dateOptions(meta);
  $("#to-quick-date").innerHTML = dateOptions(meta, true);
  $("#from-date").value = meta.default_from_date;
  $("#to-date").value = meta.default_to_date;
  $("#from-quick-date").value = meta.default_from_date;
  $("#to-quick-date").value = meta.default_to_date;
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
  $("#apply-window").addEventListener("click", loadOverview);
  $("#stock-search").addEventListener("input", renderStocks);
  $("#signal-filter").addEventListener("change", renderStocks);
  $("#close-drawer").addEventListener("click", closeDrawer);
  $("#backdrop").addEventListener("click", closeDrawer);
  loadOverview();
}

init().catch((error) => {
  $("#loading").classList.add("hidden");
  $("#error").textContent = error.message;
  $("#error").classList.remove("hidden");
});
