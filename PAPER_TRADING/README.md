# Paper Trading Ledger

This folder tracks simulated stock, ETF, and crypto trades in USD. It is intentionally simple:
the CSV file is the source of truth, and the Python scripts use only the
standard library.

## Trade Intake

For each trade, provide:

- timestamp with timezone, preferably `YYYY-MM-DDTHH:MM:SS-04:00`
- investor name
- ticker
- security type: `stock`, `etf`, or `crypto`
- side: `buy` or `sell`
- USD amount, only when overriding the default
- actual execution price, if known

When the USD amount is omitted, the ledger uses:

- `$1,000` for a stock
- `$2,000` for an ETF
- `$1,000` for crypto

Fractional quantities are assumed whenever the USD amount does not purchase a
whole share, ETF unit, or crypto asset. Quantities are calculated as
`USD amount / execution price` without rounding to whole units.

If the execution price is not known, use `lookup_alpaca_price.py` to get an
estimated price. An estimate must stay labeled as an estimate because a bar
close is not necessarily the price that a real order would have received.

Example:

```powershell
python .\paper_trading.py add `
  --timestamp "2026-05-29T10:15:00-04:00" `
  --investor "Example Investor" `
  --ticker AAPL `
  --security-type stock `
  --side buy `
  --execution-price 200.25 `
  --price-basis reported-fill `
  --notes "Example only"
```

View the portfolio:

```powershell
python .\paper_trading.py report
```

View one investor's positions or chronological progress:

```powershell
python .\paper_trading.py report --investor "Example Investor"
python .\paper_trading.py progress --investor "Example Investor"
```

The progress command reports running open cost and realized profit or loss.
Current market valuation can be added later from the Alpaca price feed.

Compare the initial investor portfolios against the latest available prices:

```powershell
python .\compare_investors.py
```

Compare every portfolio over the same market window without changing its
recorded trade baseline:

```powershell
python .\compare_investors.py --from-date 2026-05-20
python .\compare_investors.py --from-date 2026-05-20 --to-date 2026-05-29
```

This is the standard manual progress report. Run it whenever an updated
comparison is requested. Keep `2026-05-20` as the shared reference date so
every trader is measured over the same window.

## Dashboard

Start the local read-only dashboard from the repository root:

```powershell
.\.venv\Scripts\python.exe .\PAPER_TRADING\run_dashboard.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The dashboard reads `data/trades.csv` and the imported Wealthsimple history.
It does not submit trades or modify the ledger. It provides:

- trader rankings and holding-level drilldowns
- daily paper-portfolio value charts
- stock, ETF, and crypto price-history drilldowns
- explicit From and To date controls for every selected-window calculation
- January 1, May 20, and May 29 key-date shortcuts for both From and To
- beginning-of-month, mid-month, and end-of-month shortcuts for both From and
  To from January 2026 onward
- daily EOD portfolio movers and top stock movers versus the prior market close
- click-to-sort columns in the dashboard tables and trader holding drilldowns
- 3-day, 5-day, 1-week, 1-month, and 3-month signal indicators calculated as
  of the selected To date
- weighted composite signal score using the 3-day, 5-day, 1-week, and 1-month
  indicators, with the 3-month indicator retained as longer-term context
- strict, near-match, and fresh-priority volume-signal classifications
- lazy free-news enrichment in stock drilldowns using Alpaca historical news
  when credentials are configured and GDELT public-web discovery when
  available
- cached daily news snapshots with 24-hour article count, seven-day article
  count, prior-week comparison, news velocity, source diversity, and catalyst
  links
- `watchlist-variable`: derived daily-rebalanced signal portfolio that starts
  on January 31, 2026, holds only non-`none` stock signals, executes changes
  at the next available close, deploys `$1,000` per entry, and intentionally
  ignores FX
- `watchlist-variable-buy-only`: companion strategy that buys `$1,000` once
  after each stock's first non-`none` signal and never sells, for comparison
  against the sell-on-`none` strategy
- `watchlist-variable-more-signals`: companion strategy that enters on the
  same five-day non-`none` signals, but exits only after ten consecutive
  five-day `none` observations and a one-month return of `-5%` or worse
- Nisarg's security-only Wealthsimple summary with deposits and withdrawals
  excluded

### Free Public Deployment

The repository includes a Render Blueprint at `../render.yaml`. It creates a
free public web service named `stock-tracking-advanced`, with a URL similar to:

```text
https://stock-tracking-advanced.onrender.com
```

Render service names must be unique. If that name is already taken, Render
will ask for a variation such as `stock-tracking-advanced-nisarg`.

The hosted service runs with `PUBLIC_DASHBOARD=true`. Public mode includes the
paper-trading portfolios and market-data drilldowns, but intentionally omits
Nisarg's imported Wealthsimple account and blocks that private drilldown. The
Wealthsimple CSV files, raw account export, `.env`, and API keys are gitignored
and must not be committed.

Deploy it:

1. Push this repository to GitHub.
2. Sign in to [Render](https://render.com/) and connect the GitHub repository.
3. Open the [Render Blueprint setup page for this repository](https://dashboard.render.com/blueprint/new?repo=https%3A%2F%2Fgithub.com%2FDestroyerFlabby%2F001_first_repo).
   Alternatively, choose **New > Blueprint** and select the repository.
4. Confirm the `stock-tracking-advanced` free web service and deploy it.
5. Open the generated `onrender.com` URL after the build completes.

Render's free web services sleep after periods without traffic, so the first
request after inactivity can take longer. No custom domain is required.

Create a non-extended `$10-50` portfolio snapshot for the next weekday
session:

```powershell
python .\scan_daily_fresh_setups.py --top 10 --record-portfolio
```

The scanner defaults to a trader name such as `daily-watchlist-2026-06-01`.
Each dated trader is kept separately so the next-session snapshots can be
compared later without overwriting earlier selections. Omit
`--record-portfolio` to generate the research files without adding ledger
positions. Repeated same-day runs reuse the saved snapshot to avoid unnecessary
requests to the public chart feed. Use `--refresh` after a new market close.

Shared-window comparisons automatically add a `Nisarg` row calculated from
the imported Wealthsimple activity history. Inspect that security-only
calculation directly with:

```powershell
python .\nisarg_window_return.py --from-date 2026-05-20
```

Related research notes:

- `research/top_10_news_themes_2026-05-30.md`: sourced catalysts and inferred
  themes for the combined `bdinvesting` and `russellckai` top 10 holdings
- `research/ai_infrastructure_10_20_screen_2026-05-30.md`: broad-market
  `$10-20` candidate screen with pre-spike and current valuation context
- `research/ai_infrastructure_10_20_screen_2026-05-30.csv`: sortable version of
  the `$10-20` candidate screen for spreadsheet analysis
- `research/trader_comparison_2026-05-20_to_2026-05-30.md`: dated same-window
  trader comparison snapshot
- `research/tracked_stock_volume_spikes_since_2026-01-01.md`: pre-spike volume
  analysis for tracked stocks crossing `+25%` since the January 2 close
- `research/tracked_stock_volume_spikes_since_2026-01-01.csv`: sortable
  per-stock measurements for the volume-spike analysis
- `research/tracked_stock_forward_volume_signals_since_2026-01-01.md`: rolling
  event study for technical conditions associated with future volume
- `research/tracked_stock_forward_volume_signals_since_2026-01-01.csv`: sortable
  rolling observations for the forward-volume event study
- `research/current_forward_volume_catalyst_review_2026-05-30.md`: current
  strict technical matches with official-news catalyst review
- `research/short_term_watchlist_broad_market_additions_2026-05-30.md`: ten
  `$10-50` broad-market additions with technical tiers and catalyst context
- `research/short_term_watchlist_ranked_fluctuation_2026-05-30.md`: weighted
  ranking of short-term names by continued activity and fluctuation potential
- `research/raw_materials_specialty_gases_2026-05-30.md`: sector tracker for
  strategic materials, quartz exposure, and semiconductor specialty gases
- `research/silicon_wafers_2026-05-30.md`: sector tracker for silicon and
  compound-semiconductor wafer suppliers
- `research/lithography_2026-05-30.md`: sector tracker for lithography tools,
  EUV dependencies, and mature-node alternatives
- `research/photomasks_eda_2026-05-30.md`: sector tracker for EDA software,
  photomask materials, mask writers, and inspection tools
- `research/deposition_etch_2026-05-30.md`: sector tracker for deposition,
  etch, and related wafer-fabrication equipment
- `research/cmp_cleaning_metrology_2026-05-30.md`: sector tracker for CMP
  materials, cleaning inputs, inspection, and metrology
- `research/advanced_packaging_2026-05-30.md`: sector tracker for CoWoS,
  HBM, OSAT capacity, hybrid bonding, and temporary bonding materials
- `research/leading_edge_logic_foundry_2026-05-30.md`: sector tracker for
  leading-edge logic fabrication and geographic concentration
- `research/memory_2026-05-30.md`: sector tracker for DRAM, NAND, HBM,
  and flash-memory joint ventures
- `research/chip_design_2026-05-30.md`: sector tracker for chip design,
  accelerator vendors, custom silicon, and processor IP
- `research/watchlist_variable_strategy_2026-01-31_to_2026-06-01.md`: derived
  daily signal-portfolio snapshot with entry-category results
- `research/watchlist_variable_buy_only_strategy_2026-01-31_to_2026-06-01.md`:
  buy-only comparison snapshot and interpretation
- `research/watchlist_variable_more_signals_strategy_2026-01-31_to_2026-06-01.md`:
  transition analysis and the sustained-loss exit-rule comparison
- `research/news_assisted_strategy_backtest_2026-01-31_to_2026-06-01.md`:
  exploratory Alpaca-news entry and exit variants compared with the technical baseline

The initial simulated portfolios were requested for January 1, 2026, a market
holiday, so unpriced stocks and ETFs use the next available market close. The
forward `long-term-watchlist` stores May 20, 2026 closing prices as its fills. Shared
window comparisons use `--from-date` to rebase every portfolio at the same
date without modifying either recorded baseline. Canadian listings are
converted between CAD and USD using the corresponding daily CAD/USD rates.
The comparison script uses Yahoo Finance's public chart feed so it can cover
both US and Canadian listings.

## Free Market Data

The preferred optional API is [Alpaca Market Data](https://docs.alpaca.markets/docs/about-market-data-api).
Its Basic plan is free for paper and live accounts. For US equities, free
real-time data comes from IEX only, rather than all US exchanges. Historical
data is available since 2016 and the Basic historical endpoint excludes the
latest 15 minutes.

Add the paper-account credentials to the repository `.env` file before using
the lookup helper:

```env
ALPACA_KEY=...
ALPACA_SECRET=...
ALPACA_ENDPOINT=https://paper-api.alpaca.markets/v2
```

Then run:

```powershell
python .\lookup_alpaca_price.py AAPL "2026-05-29T10:15:00-04:00" --basis intraday
```

For a daily close estimate:

```powershell
python .\lookup_alpaca_price.py AAPL "2026-05-29" --basis eod
```

The helper uses Alpaca's free IEX feed. It does not submit orders.

## Free News Signals

Stock drilldowns fetch news activity lazily so a normal dashboard refresh does
not issue a news request for every tracked ticker. The enrichment layer uses:

- [Alpaca historical news](https://docs.alpaca.markets/us/docs/historical-news-data)
  with the existing `ALPACA_KEY` and `ALPACA_SECRET` values
- [GDELT DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) as
  an unauthenticated broad-web source when it is available
- [YouTube Data API](https://developers.google.com/youtube/v3) for optional
  public-video counts when `YOUTUBE_API_KEY` is configured

The dashboard caches results for six hours and stores one ignored local JSON
snapshot per ticker per day in `data/news_snapshots.json`. Free sources may be
incomplete or temporarily rate-limited. The drawer reports each source's
status instead of failing the stock drilldown.

YouTube is optional because it requires a separate free Google API key. Add it
to `.env` to include seven-day video counts and week-over-week video velocity:

```env
YOUTUBE_API_KEY=...
```

Refresh one or more tickers manually:

```powershell
.\.venv\Scripts\python.exe .\PAPER_TRADING\refresh_news_signals.py AAPL NVDA
```

Refresh every tracked stock with a one-second pause between tickers:

```powershell
.\.venv\Scripts\python.exe .\PAPER_TRADING\refresh_news_signals.py
```

Run the exploratory historical Alpaca-news strategy comparison:

```powershell
.\.venv\Scripts\python.exe .\PAPER_TRADING\analyze_news_assisted_strategy.py --max-articles 5000
```

This first version intentionally keeps news and video metrics separate from the trading
rules. Collect forward snapshots before assigning news velocity a buy or sell
weight. Official X public-post reads are paid usage, and Instagram's official
API is not a broad public stock-mention feed.

## File Layout

- `data/trades.csv`: append-only simulated trade ledger
- `paper_trading.py`: add trades and report open positions
- `lookup_alpaca_price.py`: optional free API lookup for estimated prices
- `compare_investors.py`: compare initial allocations against latest available prices
- `nisarg_window_return.py`: calculate Nisarg's security-only Wealthsimple return for one window
- `analyze_volume_spikes.py`: analyze pre-spike volume for tracked stocks up at least 25% since January 2
- `analyze_forward_volume_signals.py`: test which technical conditions preceded elevated volume over the next five sessions
- `refresh_news_signals.py`: cache free Alpaca and GDELT news-activity snapshots for tracked stocks
- `analyze_news_assisted_strategy.py`: compare exploratory Alpaca-news-assisted entry and exit rules against the technical baseline
- `scan_daily_fresh_setups.py`: rank non-extended `$10-50` stocks for the next session and optionally record a daily portfolio
- `backend/`: read-only FastAPI analytics API for the local dashboard
- `frontend/`: dependency-free local browser dashboard
- `run_dashboard.py`: start the local dashboard server
- `wealthsimple_tracker.py`: import and summarize real Wealthsimple account history
- `data/wealthsimple_activities.csv`: normalized granular Wealthsimple history
- `data/wealthsimple_imports.csv`: Wealthsimple import audit log
- `DATA_SOURCES.md`: provider notes and tradeoffs

## Wealthsimple Account History

Nisarg's real Wealthsimple account history is stored separately from the
simulated investor comparison. Import a downloaded activity export with:

```powershell
python .\wealthsimple_tracker.py import .\activities-export-2026-05-30.csv --owner Nisarg
```

The import is idempotent: importing the same full-history export again does
not duplicate activities. Exact repeated rows within an export are retained as
separate occurrences because they may represent separate transactions.

Use the concise summary during high-level review:

```powershell
python .\wealthsimple_tracker.py summary --owner Nisarg
```

Drill into quantities or source-level activity when needed:

```powershell
python .\wealthsimple_tracker.py positions --owner Nisarg
python .\wealthsimple_tracker.py activities --owner Nisarg --symbol SPY
python .\wealthsimple_tracker.py activities --owner Nisarg --activity-type Dividend --limit 25
```

Every normalized activity retains the Wealthsimple source file and source-row
number for auditability.

Calculate Nisarg's return for securities traded since January 1, 2026:

```powershell
python .\nisarg_2026_return.py
```

This reconstructs opening units needed to support 2026 sales, adds actual 2026
purchase cash costs, counts actual final sale proceeds, and values remaining
units with current market prices. Deposits and withdrawals are excluded. The
activity export alone does not contain a January 1 holdings snapshot, so this
is a traded-securities sleeve return rather than a certified whole-account
performance figure.
