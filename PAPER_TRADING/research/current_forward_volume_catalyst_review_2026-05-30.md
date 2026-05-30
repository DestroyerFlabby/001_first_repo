# Current Forward-Volume Catalyst Review

Research snapshot generated: 2026-05-30

## Technical Screen

The rolling event study in
`research/tracked_stock_forward_volume_signals_since_2026-01-01.md` found that
the strict three-factor setup was associated with next-five-session average
volume of at least `1.5x` normal in `53.6%` of historical observations,
compared with `15.8%` across all observations.

Strict setup:

1. Five-session price return of at least `+10%`.
2. Five-session average volume of at least `1.5x` the prior 20-session average.
3. Close within `2%` of the prior 20-session high.

The latest available close was May 29, 2026. Current strict matches:

| Ticker | Prior 5d Return | Prior 5d Volume Ratio | Distance to Prior 20d High |
|---|---:|---:|---:|
| `CRSR` | `+75.18%` | `2.64x` | `+1.59%` |
| `UMAC` | `+114.73%` | `2.22x` | `+7.36%` |
| `QBTS` | `+17.09%` | `1.99x` | `+2.20%` |
| `MOV` | `+39.20%` | `1.96x` | `+7.56%` |
| `IBM` | `+17.72%` | `1.87x` | `+12.71%` |
| `RCAT` | `+60.58%` | `1.70x` | `+2.47%` |
| `HPQ` | `+23.47%` | `1.68x` | `+6.08%` |
| `SNOW` | `+54.37%` | `1.62x` | `+6.84%` |
| `BBAR` | `+12.85%` | `1.55x` | `+4.14%` |

Positive distance means the latest close has already broken above the prior
20-session high.

## Fresh Priority Queue

To avoid chasing names that have already moved sharply, apply an additional
working filter: prioritize strict matches with a five-session return no higher
than `+25%`.

| Ticker | Prior 5d Return | Prior 5d Volume Ratio | Tracked In |
|---|---:|---:|---|
| `QBTS` | `+17.09%` | `1.99x` | `long-term-watchlist`, `short-term-watchlist` |
| `IBM` | `+17.72%` | `1.87x` | `long-term-watchlist`, `short-term-watchlist` |
| `HPQ` | `+23.47%` | `1.68x` | `daily-watchlist-2026-06-01`, `short-term-watchlist` |
| `BBAR` | `+12.85%` | `1.55x` | `daily-watchlist-2026-06-01`, `short-term-watchlist` |

These strict matches pass the measured technical screen, but they still
require catalyst, valuation, liquidity, dilution, float, and short-interest
review before any trading decision.

## Extended Strict Matches

The following names technically qualify but have already risen more than
`25%` over five sessions. Treat them as review-only rather than fresh-entry
candidates.

| Ticker | Prior 5d Return | Prior 5d Volume Ratio |
|---|---:|---:|
| `UMAC` | `+114.73%` | `2.22x` |
| `CRSR` | `+75.18%` | `2.64x` |
| `RCAT` | `+60.58%` | `1.70x` |
| `SNOW` | `+54.37%` | `1.62x` |
| `MOV` | `+39.20%` | `1.96x` |

## Near-Match Queue

These names are near the prior 20-session high with at least `1.25x` volume,
but do not yet pass every strict threshold.

| Ticker | Prior 5d Return | Prior 5d Volume Ratio | Distance to Prior 20d High |
|---|---:|---:|---:|
| `AXTA` | `+5.63%` | `1.62x` | `+1.45%` |
| `TEO` | `+23.93%` | `1.50x` | `+5.22%` |
| `GRRR` | `+43.62%` | `1.48x` | `+15.45%` |
| `BRZE` | `+9.48%` | `1.48x` | `+0.71%` |
| `BOX` | `+6.14%` | `1.42x` | `+4.09%` |
| `CLF` | `+27.10%` | `1.42x` | `+2.33%` |
| `MRVL` | `+7.50%` | `1.41x` | `-1.57%` |
| `ONDS` | `+44.01%` | `1.39x` | `-0.23%` |
| `BIRK` | `+13.61%` | `1.37x` | `+2.27%` |
| `CRNC` | `+32.71%` | `1.36x` | `+8.34%` |
| `PATH` | `+10.88%` | `1.35x` | `+1.21%` |

## Catalyst Review

### QBTS - D-Wave Quantum

D-Wave reported first-quarter 2026 bookings of `$33.4 million`, up nearly
`2,000%` year over year, and discussed expanding commercial adoption and its
gate-model strategy. This gives the technical move an identifiable
company-specific catalyst.

Source:
- [D-Wave Q1 2026 results](https://ir.dwavequantum.com/news/news-details/2026/D-Wave-Reports-First-Quarter-2026-Results/default.aspx)

### IBM

IBM has a dense sequence of official announcements rather than one isolated
headline. Recent disclosures include a proposed `$1 billion` CHIPS award for
a purpose-built quantum foundry and a `$5 billion` IBM and Red Hat commitment
to secure open source software with AI-assisted engineering.

Sources:
- [IBM quantum foundry and proposed CHIPS award](https://newsroom.ibm.com/ibm-and-u-s-department-of-commerce-announce-americas-first-purpose-built-quantum-foundry)
- [IBM and Red Hat Project Lightwell commitment](https://newsroom.ibm.com/2026-05-28-ibm-and-red-hat-commit-5-billion-to-redefine-the-future-of-open-source-in-the-ai-era)
- [IBM Think 2026 AI operating model announcements](https://newsroom.ibm.com/2026-05-05-think-2026-ibm-delivers-the-blueprint-for-the-ai-operating-model-as-the-ai-divide-widens)

### SNOW - Snowflake

Snowflake's latest move coincided with its fiscal 2027 first-quarter results
and an expanded AWS collaboration. Snowflake disclosed a multi-year agreement
that includes a `$6 billion` commitment for Graviton compute and AI spend on
AWS over five years.

Sources:
- [Snowflake newsroom](https://www.snowflake.com/en/news/)
- [Snowflake and AWS collaboration](https://www.snowflake.com/en/news/press-releases/snowflake-expands-aws-collaboration-with-6b-commitment-to-accelerate-enterprise-agentic-ai-adoption/)

## Inferred Pattern

This is an inference from the measured technical screen and the official
company disclosures:

1. **Price strength is the first filter.** Volume alone generated too many
   noisy observations. The stronger setup combined price momentum with
   expanding participation.
2. **The best volume setups frequently have a concrete catalyst.** Earnings,
   bookings, major contracts, partnerships, government funding, and strategic
   commitments can cause both repricing and sustained attention.
3. **Breakouts are more useful than raw spikes.** A stock trading near or
   above a recent high with sustained five-day volume expansion was more
   likely to see further elevated volume than the baseline tracked stock.
4. **Elevated future volume is not the same as positive future return.**
   Technical screening should surface names for research, not automatically
   trigger a buy.

## Practical Watch Rule

Monitor tracked names daily and escalate research when all three technical
conditions are met. Then confirm whether an official catalyst exists and
review valuation, liquidity, dilution, float, and short interest separately.
