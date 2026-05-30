const state = { overview: null };
const $ = (selector) => document.querySelector(selector);

const money = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value || 0);
const pct = (value) => `${value >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}%`;
const number = (value) => Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const tone = (value) => (Number(value) >= 0 ? "positive" : "negative");
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

function signalPill(signal) {
  if (!signal || signal.classification === "none") return '<span class="pill">none</span>';
  const kind = signal.fresh_priority ? "fresh" : signal.classification;
  const label = signal.fresh_priority ? "fresh" : signal.classification;
  return `<span class="pill ${kind}">${label}</span>`;
}

function renderCards() {
  const traders = state.overview.traders;
  const stocks = state.overview.stocks;
  const strict = stocks.filter((row) => row.signal?.classification === "strict").length;
  const fresh = stocks.filter((row) => row.signal?.fresh_priority).length;
  const leader = traders[0];
  $("#summary-cards").innerHTML = [
    ["Portfolios", traders.length, "Paper ledgers plus imported account"],
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
        <td>${row.signal ? `${number(row.signal.five_day_volume_ratio)}x` : "-"}</td>
        <td>${signalPill(row.signal)}</td>
      </tr>`
    )
    .join("");
  document.querySelectorAll("[data-stock]").forEach((row) =>
    row.addEventListener("click", () => openStock(row.dataset.stock))
  );
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
        <table><thead><tr><th>Ticker</th><th>Start</th><th>Current</th><th>Gain / loss</th><th>Return</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>
      ${detail.note ? `<p class="muted">${detail.note}</p>` : ""}
    `);
  } catch (error) {
    openDrawer(`<p class="error">${error.message}</p>`);
  }
}

async function openStock(ticker) {
  openDrawer(`<p class="loading">Loading ${ticker}...</p>`);
  try {
    const detail = await fetchJson(`/api/stocks/${encodeURIComponent(ticker)}?${query()}`);
    openDrawer(`
      <p class="eyebrow">${detail.security_type} · ${detail.currency}</p>
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
        ${stat("Signal", signalPill(detail.signal))}
        ${stat("5d volume", detail.signal ? `${number(detail.signal.five_day_volume_ratio)}x` : "-")}
        ${stat("Distance to 20d high", detail.signal ? pct(detail.signal.distance_to_20d_high_pct) : "-")}
      </div>
    `);
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
    renderCards();
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
  $("#presets").innerHTML = meta.presets
    .map((preset) => `<button class="preset" data-date="${preset.from_date}">${preset.label}</button>`)
    .join("");
  $("#checkpoint").innerHTML += meta.checkpoints
    .map((checkpoint) => `<option value="${checkpoint.date}">${checkpoint.label}</option>`)
    .join("");
  document.querySelectorAll("[data-date]").forEach((button) =>
    button.addEventListener("click", () => {
      $("#from-date").value = button.dataset.date;
      document.querySelectorAll(".preset").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      loadOverview();
    })
  );
  $("#checkpoint").addEventListener("change", () => {
    $("#to-date").value = $("#checkpoint").value;
    if ($("#checkpoint").value) loadOverview();
  });
  $("#to-date").addEventListener("change", () => {
    $("#checkpoint").value = $("#to-date").value;
  });
  $("#apply-window").addEventListener("click", loadOverview);
  $("#stock-search").addEventListener("input", renderStocks);
  $("#signal-filter").addEventListener("change", renderStocks);
  $("#close-drawer").addEventListener("click", closeDrawer);
  $("#backdrop").addEventListener("click", closeDrawer);
  document.querySelector('[data-date="2026-05-20"]').classList.add("active");
  loadOverview();
}

init().catch((error) => {
  $("#loading").classList.add("hidden");
  $("#error").textContent = error.message;
  $("#error").classList.remove("hidden");
});
