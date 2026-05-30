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

Because the simulated start date is January 1, 2026, a market holiday, the
comparison uses the January 2, 2026 close for stocks and ETFs. Crypto uses its
January 1, 2026 close. Canadian listings are converted between CAD and USD
using the corresponding daily CAD/USD rates. The comparison script uses
Yahoo Finance's public chart feed so it can cover both US and Canadian
listings.

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

## File Layout

- `data/trades.csv`: append-only simulated trade ledger
- `paper_trading.py`: add trades and report open positions
- `lookup_alpaca_price.py`: optional free API lookup for estimated prices
- `compare_investors.py`: compare initial allocations against latest available prices
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
