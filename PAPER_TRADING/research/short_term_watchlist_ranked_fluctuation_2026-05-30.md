# Short-Term Watchlist Ranked Fluctuation Screen

Research snapshot generated: 2026-05-30

## Purpose

Rank the current `short-term-watchlist` by likelihood of continued elevated
trading activity and price fluctuation. This is a research triage tool, not a
forecast of positive returns and not a buy recommendation.

## Method

The score combines:

- **Momentum:** five-session price return, capped so an extreme move does not
  dominate the ranking.
- **Relative volume:** five-session average volume versus the prior
  20-session average.
- **Breakout strength:** distance from the prior 20-session high.
- **Catalyst quality:** official company disclosures such as earnings,
  bookings, contracts, partnerships, or government-related demand.
- **Historical fluctuation:** annualized volatility calculated from the most
  recent 20 daily returns.
- **Risk penalty:** financing, dilution, macro dependence, or evidence that a
  move may already be overextended.

The first four inputs estimate continued attention. Historical volatility
estimates how large subsequent fluctuations may be. The risk adjustment keeps
high-volume names from being treated as automatically attractive.

## Ranked List

| Rank | Ticker | Overall Score | 5d Return | 5d Volume Ratio | 20d Annualized Volatility | Primary Reason | Main Risk |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `UMAC` | `92` | `+114.73%` | `2.22x` | `227%` | Drone-component demand, revenue growth, and extreme participation | Already overextended; small-cap financing risk |
| 2 | `SNOW` | `84` | `+54.37%` | `1.62x` | `133%` | Earnings repricing and expanded AWS collaboration | Large gap may consolidate after news |
| 3 | `CRSR` | `83` | `+75.18%` | `2.64x` | `123%` | Strongest relative-volume build in the list and earnings improvement | Sharp move; workstation narrative needs execution |
| 4 | `RCAT` | `74` | `+60.58%` | `1.70x` | `145%` | Defense-drone demand and sustained attention | Recent `$225M` offering introduces dilution risk |
| 5 | `QBTS` | `70` | `+17.09%` | `1.99x` | `153%` | Record bookings and commercial quantum-adoption narrative | Valuation and volatility remain high |
| 6 | `ONDS` | `68` | `+44.01%` | `1.39x` | `146%` | Raised revenue outlook and defense-robotics demand | Near-tier volume signal rather than strict match |
| 7 | `GRRR` | `65` | `+43.62%` | `1.48x` | `90%` | AI-infrastructure growth and improving operating cash flow | Near-tier signal and smaller operating base |
| 8 | `MOV` | `64` | `+39.20%` | `1.96x` | `67%` | Earnings and margin repricing with strong volume | Lower ongoing volatility; may be a discrete event |
| 9 | `CRNC` | `62` | `+32.71%` | `1.36x` | `83%` | Guidance raise and automotive-AI adoption | Near-tier signal; customer execution matters |
| 10 | `IBM` | `60` | `+17.72%` | `1.87x` | `66%` | Quantum-foundry and AI announcements with broad attention | Large-cap profile makes extreme fluctuations less likely |
| 11 | `HPQ` | `55` | `+23.47%` | `1.68x` | `74%` | Earnings beat and PC demand recovery | More mature business; lower fluctuation potential |
| 12 | `CLF` | `46` | `+27.10%` | `1.42x` | `61%` | Industrial AI partnership and cyclical steel exposure | Macro and commodity sensitivity |
| 13 | `BBAR` | `38` | `+12.85%` | `1.55x` | `81%` | Strict technical match | Macro-driven Argentina bank ADS, not thematic analogue |

## Highest-Priority Monitoring Group

For the specific question of where another large fluctuation is most
plausible, monitor:

1. `UMAC`
2. `SNOW`
3. `CRSR`
4. `RCAT`
5. `QBTS`
6. `ONDS`

These names combine elevated attention with higher realized volatility. They
also carry higher downside risk. A high ranking means a larger move is more
plausible, not that the next move is likely to be upward.

## Practical Update Rule

Recalculate the screen after each market close. Escalate review when a name:

1. Retains five-session volume above `1.5x` normal.
2. Remains near or above its prior 20-session high.
3. Has an official catalyst that is still developing.
4. Has not introduced a new financing, dilution, or liquidity risk.

## Sources

- [Yahoo Finance](https://finance.yahoo.com/) public chart feed
- [D-Wave Q1 results](https://ir.dwavequantum.com/news/news-details/2026/D-Wave-Reports-First-Quarter-2026-Results/default.aspx)
- [Snowflake and AWS collaboration](https://www.snowflake.com/en/news/press-releases/snowflake-expands-aws-collaboration-with-6b-commitment-to-accelerate-enterprise-agentic-ai-adoption/)
- [UMAC Q1 shareholder letter filed with the SEC](https://www.sec.gov/Archives/edgar/data/1956955/000168316826003912/umac_ex9901.htm)
- [Corsair Q1 results](https://ir.corsair.com/news-releases/news-release-details/corsair-reports-strong-profit-growth-first-quarter-2026)
- [Red Cat offering](https://ir.redcatholdings.com/news-events/press-releases/detail/224/red-cat-announces-pricing-of-public-offering-of-common-stock)
- [Ondas Q1 results](https://ir.ondas.com/press-releases/detail/306/)

