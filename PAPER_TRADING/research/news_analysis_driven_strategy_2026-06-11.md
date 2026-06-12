# News + Analysis Driven Variable Portfolio

Created: 2026-06-11

## Portfolio Added

`watchlist-variable-news-analysis-driven`

This is a daily EOD simulation portfolio that starts from the existing tracked stock universe and only buys when all of these are true:

- Signal category is `fresh` or `strict`.
- Seven-day Alpaca news count is accelerating versus the prior seven days.
- Market-analysis score is at least `180`.
- Execution is next available close after the signal is observed.
- Each new entry deploys `$1,000`.

Sell logic matches the optimized news strategy:

- Sell after twenty missing-signal sessions,
- one-month momentum is weak,
- and the latest seven-day Alpaca news count is zero.

## Analysis Score

The score is point-in-time and uses only data available at the prior market close:

- Composite signal score from the existing 3d, 5d, 1w, 1m, and 3m signal model.
- Fresh/strict signal bonus.
- Active and accelerating news bonus.
- Weekly news velocity bonus.
- Five-day and one-month relative strength versus SPY.
- Five-day volume confirmation.
- Distance to recent high as a trend-quality check.
- Multi-horizon confirmation count.
- Penalties for weak relative strength, poor volume, loss of trend, and extreme overextension.

This is deliberately not a same-day or intraday model. The dashboard assumes we observe the signal after close and can only act at the next available close.

## Free / Low-Cost Research Inputs Reviewed

These are useful future inputs for expanding the model, but they should be integrated with point-in-time timestamps before being used in backtests:

- SEC EDGAR APIs: no-key source for company submissions and XBRL company facts. Useful for filings, financial statement facts, share count, revenue, margins, and balance-sheet trend work.
- Alpha Vantage: free-key market data, technical indicators, fundamentals, economic data, and news/sentiment style endpoints.
- Finnhub: free-key stock metrics and basic financials; useful for a normalized ratio layer if rate limits are acceptable.
- Financial Modeling Prep: free-key fundamentals, ratios, key metrics, filings, and financial scores; useful for Piotroski/Altman-style quality overlays.
- SimFin / EODHD: optional free-account or freemium sources for broader financial statement coverage.

## Why Fundamentals Are Not Directly Added Yet

Current ratios from a free API can accidentally leak future information into a January-to-today backtest. Before fundamentals drive entries or exits, the data needs:

- Filing date or report date attached to each metric.
- Restatement handling.
- A rule for when a filing becomes tradable information.
- Coverage rules for Canadian stocks, ETFs, crypto, and non-US listings.

Until that is built, this portfolio uses market-confirmed analysis that is available daily from existing historical close/volume data plus committed daily news counts.

## Next Good Upgrade

Add a point-in-time fundamentals cache:

- SEC EDGAR first for US common stocks.
- Optional API-key providers only as enrichment.
- Store metrics by `ticker`, `metric_date`, `filing_date`, `source`, and `value`.
- Join metrics to the simulation only when `filing_date <= observed_date`.

Candidate future factors:

- Revenue growth acceleration.
- Gross margin trend.
- Free-cash-flow margin.
- Net debt / EBITDA or cash runway.
- Share dilution.
- Analyst estimate revision direction, if a free source is available.
