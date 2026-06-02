# Watchlist Variable More-Signals Strategy

## Purpose

This analysis tests whether the original `watchlist-variable` strategy sells
too quickly when its five-day signal temporarily returns to `none`.

The candidate portfolio is named `watchlist-variable-more-signals`. It uses
the same tracked stock universe, January 31, 2026 start date, `$1,000` entry
size, no FX conversion, and next-close execution convention as
`watchlist-variable`.

## Signal Transition Findings

The five-day `near` signal is not usually a reliable promise that a stronger
signal will follow:

| Look-ahead window | Near signals | Upgraded to fresh or strict | Returned to none |
| --- | ---: | ---: | ---: |
| Next session | 548 | 10.2% | 39.4% |
| Within 3 sessions | 548 | 15.0% | 66.8% |
| Within 5 sessions | 548 | 16.2% | 77.2% |
| Within 10 sessions | 548 | 20.1% | 79.0% |

One-session transitions show why immediate exits are noisy:

| Current signal | Next-session none | Next-session near | Next-session fresh | Next-session strict |
| --- | ---: | ---: | ---: | ---: |
| none | 96.9% | 2.3% | 0.4% | 0.4% |
| near | 39.4% | 50.4% | 6.8% | 3.5% |
| fresh | 27.2% | 10.8% | 43.7% | 18.4% |
| strict | 35.8% | 3.8% | 8.8% | 51.6% |

The useful pattern is not that `near` consistently upgrades. It is that a
single `none` observation is common even after stronger signals, so selling
immediately creates repeated entry and exit cycles.

## Added Exit Rule

`watchlist-variable-more-signals`:

1. Buys a stock at the next available close after any five-day `fresh`,
   `strict`, or `near` signal.
2. Holds through temporary signal loss.
3. Sells at the next available close only after ten consecutive five-day
   `none` observations and a one-month return of `-5%` or worse.

This combines sustained signal loss with weakening medium-term momentum.

## Jan 31 To Jun 1 Request

The requested end date resolves to the latest available market close:
May 29, 2026.

| Strategy | Entries | Closed positions | Open positions | Deployed capital | Ending value | Gain | Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `watchlist-variable` | 333 | 312 | 21 | $333,000.00 | $337,635.42 | $4,635.42 | 1.39% |
| `watchlist-variable-more-signals` | 174 | 80 | 94 | $174,000.00 | $202,126.34 | $28,126.34 | 16.16% |
| `watchlist-variable-buy-only` | 123 | 0 | 123 | $123,000.00 | $174,475.30 | $51,475.30 | 41.85% |

The more-signals strategy materially improves the original strategy while
still retaining an explicit sell rule.

## Entry Category Results

| Entry category | Entries | Closed | Open | Deployed capital | Gain | Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fresh | 27 | 15 | 12 | $27,000.00 | $7,339.80 | 27.18% |
| near | 132 | 60 | 72 | $132,000.00 | $20,255.09 | 15.34% |
| strict | 15 | 5 | 10 | $15,000.00 | $531.46 | 3.54% |

## Interpretation And Limits

The stronger result suggests the original sell-on-first-`none` rule is too
reactive for this stock universe. However, the new rule was chosen after
examining this same January-to-June sample. It is not an out-of-sample result.

The tracked universe was also assembled over time and may contain hindsight
bias. Returns exclude trading costs, bid-ask spreads, taxes, FX conversion,
and capital-allocation limits. Treat this as a forward-tracking candidate,
then compare it against the original and buy-only portfolios on new closes.
