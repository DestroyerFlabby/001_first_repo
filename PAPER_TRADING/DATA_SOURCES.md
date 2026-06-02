# Market Data Sources

Checked on 2026-05-30.

## Recommended Starting Point: Alpaca

[Alpaca Market Data](https://docs.alpaca.markets/docs/about-market-data-api)
has a free Basic plan for paper and live trading accounts. It requires an
account and API credentials.

For US equities, the free feed is IEX. It is suitable for paper-trading
estimates, but it is not a consolidated view of every US exchange. Alpaca's
documentation says the free historical API supports data since 2016, excludes
the latest 15 minutes, and permits 200 historical API calls per minute.

Use:

- minute bars when the trade timestamp matters
- daily bars when end-of-day estimates are sufficient
- `reported-fill` when an actual simulated execution price is known

## Other Options

- [Alpha Vantage](https://www.alphavantage.co/documentation/) offers a free
  API key for many datasets, but its official support page currently says the
  free service is limited to 25 requests per day. Its intraday stock endpoint
  is marked premium in the official documentation.
- [Polygon](https://polygon.io/pricing) advertises a free stock-data tier with
  end-of-day data, 15-minute delayed data, two years of history, and five API
  calls per minute.
- [Stooq](https://stooq.com/db/h/) publishes free historical downloads,
  including US data. Its direct CSV download endpoint currently asks the user
  to generate an API key through a CAPTCHA flow, so it is not used by the
  scripts in this folder.

Provider terms and free-tier limits can change. Keep the recorded
`price_basis` value with every trade so results remain auditable.

## Wealthsimple Eligibility and CAD-Account Fee Estimates

Wealthsimple does not publish a public API for checking whether a specific
security is currently tradable in a user's account. The dashboard therefore
shows an estimate based on Wealthsimple's documented eligibility criteria:

- `likely-supported`
- `verify-in-app`
- `likely-unsupported`

Always confirm a ticker in Wealthsimple before placing an order. Availability
can change because of exchange support, settlement, liquidity, halts, and
limited OTC coverage.

The optional dashboard fee switch estimates the `1.5%` FX fee Wealthsimple
documents for USD trades placed from CAD accounts. It is disabled by default.
The estimate is not applicable when a suitable USD account is used.

Ticker hover details may include a curated Canadian-dollar CDR reference.
These are informational alternatives to verify before use, not automatic
replacements or guaranteed Wealthsimple listings.

- [Wealthsimple stock and ETF eligibility criteria](https://help.wealthsimple.com/hc/en-ca/articles/360056580834)
- [Wealthsimple CAD and USD conversion fees](https://help.wealthsimple.com/hc/en-ca/articles/4415548242971-Convert-funds-between-CAD-and-USD)
- [Wealthsimple USD accounts](https://help.wealthsimple.com/hc/en-ca/articles/4414660979355-Upgrade-to-USD-accounts-for-stock-and-crypto-trading)
- [CIBC Canadian Depositary Receipts](https://www.cibc.com/en/personal-banking/investments/canadian-depositary-receipts.html)

## Free News Enrichment

- [Alpaca historical news](https://docs.alpaca.markets/us/docs/historical-news-data)
  provides structured stock and crypto news dating back to 2015. The
  dashboard uses the existing Alpaca credentials when available.
- [GDELT DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
  provides public-web news discovery without an API key. It is treated as a
  best-effort source because public requests may be throttled.
- [YouTube Data API](https://developers.google.com/youtube/v3) provides
  optional public-video search with a free quota after `YOUTUBE_API_KEY` is
  configured. Search calls consume quota, so results are cached daily.

The dashboard caches daily news snapshots locally. News coverage is an
attention indicator, not a complete record of every article published about a
company.
