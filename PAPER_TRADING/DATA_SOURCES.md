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
