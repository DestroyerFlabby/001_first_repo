# News-Assisted Strategy Backtest

## Scope

- Requested strategy window: `2026-01-31` to `2026-06-01`.
- Source: Alpaca historical news only. GDELT is currently throttled, YouTube is not configured, and free official X or broad Instagram historical feeds are unavailable.
- News is observed only through the previous market close. Simulated trades execute at the next available close.
- This is an in-sample exploratory backtest over the currently tracked universe, not a forward validation.

## Coverage

- Tracked stock tickers: `140`.
- Tickers with at least one Alpaca news article: `130`.
- Retrieved Alpaca articles: `20502`.
- Article cap reached by tickers: `0`.

## Results

- `technical-baseline`: exit after ten consecutive five-day `none` observations and a one-month return of `-5%` or worse.
- `hold-while-news-active`: apply the baseline exit only when the latest seven-day news count is zero.
- `confirm-news-cooling`: apply the baseline exit only when the latest seven-day news count is no higher than the prior seven-day count.
- `early-exit-on-news-cooling`: exit after five consecutive five-day `none` observations, a one-month return of `-5%` or worse, and cooling seven-day news.
- `require-news-entry`: use the baseline exit, but enter only when the stock has at least one article in the latest seven days.

| Rule | Entries | Closed | Open | Deployed | Ending value | Gain | Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `technical-baseline` | 174 | 80 | 94 | $174,000.00 | $202,007.38 | $28,007.38 | 16.10% |
| `hold-while-news-active` | 156 | 49 | 107 | $156,000.00 | $196,410.60 | $40,410.60 | 25.90% |
| `confirm-news-cooling` | 171 | 75 | 96 | $171,000.00 | $201,298.99 | $30,298.99 | 17.72% |
| `early-exit-on-news-cooling` | 179 | 86 | 93 | $179,000.00 | $204,716.22 | $25,716.22 | 14.37% |
| `technical-baseline + require-news-entry` | 145 | 64 | 81 | $145,000.00 | $169,190.01 | $24,190.01 | 16.68% |

## Interpretation

`hold-while-news-active` produced the strongest in-sample return, but it is permissive: heavily covered companies may almost never reach a zero-article week. It should be tracked as an experimental long-hold comparison, not adopted as the live rule yet.

`confirm-news-cooling` is the more conservative news-assisted candidate. It improved the in-sample result while preserving the original ten-session technical deterioration condition.

The technical baseline remains the reference strategy. News-assisted rules should not replace it unless they improve results on later, unseen closes. Article counts measure media attention, not sentiment, article quality, or social engagement.
