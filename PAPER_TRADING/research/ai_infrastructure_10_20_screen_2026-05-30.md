# AI Infrastructure `$10-20` Broad-Market Screen

Research date: 2026-05-30

This is a research screen, not an investment recommendation. A `$10-20` share
price is a discovery filter only. It does not mean that a company is cheap.
Market capitalization, revenue scale, dilution, debt, margins, and execution
risk matter more than the price of one share.

The sortable data is in
`research/ai_infrastructure_10_20_screen_2026-05-30.csv`.

## Method

- Screened publicly traded companies exposed to the same broad themes as the
  prior top-10 performers: AI networking, photonics, power-backed compute,
  data-center energy, physical AI, and commercial space infrastructure.
- `strict` means the latest share price was between `$10` and `$20`.
- `near-band` means the latest share price was close to the requested range,
  between `$8` and `$10`.
- Used January 2, 2026 as the pre-spike comparison date because January 1 was a
  market holiday.
- Interpreted "market size before the spike" as approximate equity market
  capitalization. Total addressable market (TAM) is a separate industry-level
  question, not a company valuation metric.
- Approximate market capitalizations are share price multiplied by the latest
  SEC-reported shares available at each comparison date.
- Approximate P/S ratios use the latest full-year revenue filed with the SEC
  by each comparison date. They are screening values, not audited valuation
  models. Foreign issuers and companies with rapidly changing share counts
  need manual reconciliation before a decision.
- Current and historical share prices use Yahoo Finance's public chart feed.
  Fundamental inputs use [SEC company facts](https://data.sec.gov/api/xbrl/companyfacts/).

## Strict `$10-20` Candidates

| Ticker | Price | Pre-Spike Price | Change | Approx. Market Cap: Pre / Current | Approx. P/S: Pre / Current | Theme | Fit |
|---|---:|---:|---:|---:|---:|---|---|
| `POET` | `$12.29` | `$7.16` | `+71.65%` | `$548M / $1.63B` | `13223x / 1513x` | Photonic engines for AI interconnects | Direct |
| `BTDR` | `$17.49` | `$11.55` | `+51.43%` | `$2.22B / $4.12B` | `6.35x / 11.78x` | AI cloud, data centers, and Bitcoin mining | Direct, mixed |
| `CLSK` | `$18.29` | `$11.55` | `+58.35%` | `$2.95B / $4.69B` | `3.85x / 6.12x` | Power, land, and AI/HPC-applicable sites | Direct-adjacent, mixed |
| `FLNC` | `$18.88` | `$23.01` | `-17.95%` | `$3.00B / $2.50B` | `1.33x / 1.11x` | Grid-scale energy storage | Adjacent |
| `SHLS` | `$12.45` | `$9.09` | `+36.96%` | `$1.53B / $2.09B` | `3.84x / 4.39x` | Electrical infrastructure for solar deployment | Adjacent |
| `MNTS` | `$16.85` | `$5.74` | `+193.55%` | `$139M / $168M` | `65.57x / 151.69x` | In-space transportation and satellite services | Direct space, speculative |

## Near-Band Candidates

| Ticker | Price | Pre-Spike Price | Change | Approx. Market Cap: Pre / Current | Approx. P/S: Pre / Current | Theme | Fit |
|---|---:|---:|---:|---:|---:|---|---|
| `SERV` | `$9.35` | `$11.83` | `-20.96%` | `$881M / $723M` | `486x / 273x` | Autonomous delivery robots | Physical AI |
| `SATL` | `$9.51` | `$1.96` | `+385.20%` | `$54M / $260M` | `4.16x / 14.66x` | Earth-observation satellites and defense intelligence | Direct space |
| `STEM` | `$9.72` | `$16.96` | `-42.69%` | `$142M / $87M` | `0.98x / 0.56x` | Energy-storage software and services | Adjacent |
| `EOSE` | `$8.43` | `$12.97` | `-35.00%` | `$3.74B / $2.86B` | `240x / 25.06x` | Long-duration energy storage | Adjacent |

## Company Notes

### POET - Photonics

Industry: Photonic integrated circuits and optical engines

Direction: POET is moving from development toward commercial execution for AI
and hyperscale data-center interconnects. Its May 2026 Lumilens agreement
included an initial purchase order valued at `$50 million` for EOI-based
engines.

Valuation read: The share-price move and dilution-expanded market cap are
visible, but P/S is not useful yet because recognized revenue remains tiny.
This is a commercialization thesis, not a conventional value screen.

Sources:
- [POET Q1 2026 results](https://www.globenewswire.com/news-release/2026/05/14/3295506/0/en/poet-technologies-reports-first-quarter-2026-financial-results.html)
- [POET and Lumilens agreement](https://www.nasdaq.com/press-release/poet-technologies-and-lumilens-advance-wafer-level-photonic-integration-next)

### BTDR - Power-Backed Compute

Industry: Bitcoin mining, data centers, and AI cloud

Direction: Bitdeer is deploying NVIDIA GB200 NVL72 infrastructure and
evaluating conversions of powered sites into colocation or AI cloud capacity.
Its management describes AI and colocation as a major long-term opportunity.

Valuation read: P/S expanded from approximately `6.35x` to `11.78x`. Bitcoin
production, power assets, AI-cloud utilization, capital intensity, and
conversion execution all affect the thesis.

Sources:
- [Bitdeer investor relations](https://ir.bitdeer.com/)
- [Bitdeer February 2026 operations update](https://ir.bitdeer.com/news-releases/news-release-details/bitdeer-announces-february-2026-production-and-operations-update)
- [Bitdeer NVIDIA GB200 NVL72 deployment](https://bitdeer.gcs-web.com/news-releases/news-release-details/bitdeer-ai-accelerates-global-ai-cloud-expansion-nvidia-gb200)

### CLSK - Data-Center Site Optionality

Industry: Data-center development and Bitcoin mining

Direction: CleanSpark is building a portfolio of power, land, and data-center
assets. In its May 2026 results, management said it aimed to commercialize
AI/HPC-applicable assets while continuing to mine efficiently.

Valuation read: P/S expanded from approximately `3.85x` to `6.12x`. The market
is assigning value to AI/HPC optionality, but existing revenue is still tied
to Bitcoin mining economics.

Sources:
- [CleanSpark investor relations](https://investors.cleanspark.com/overview/default.aspx)
- [CleanSpark fiscal Q2 2026 results](https://investors.cleanspark.com/news/news-details/2026/CleanSpark-Reports-Second-Fiscal-Quarter-2026-Results/default.aspx)

### FLNC - Grid Storage

Industry: Grid-scale battery storage and energy optimization software

Direction: Fluence sells energy-storage systems, services, and asset
optimization software. Its data-center materials frame storage as part of
reliable, scalable power infrastructure for the AI economy.

Valuation read: P/S declined from approximately `1.33x` to `1.11x`. This is an
established-revenue adjacency play, not a pure-play AI company.

Sources:
- [Fluence fiscal Q2 2026 results](https://ir.fluenceenergy.com/news-releases/news-release-details/fluence-energy-inc-reports-second-quarter-2026-results-reaffirms/)
- [Fluence data-center brochure](https://info.fluenceenergy.com/hubfs/Fluence-Data%20Centre%20Brochure-BR-065-01-EN.pdf)

### SHLS - Electrical Infrastructure

Industry: Electrical balance-of-system equipment for solar projects

Direction: Shoals supplies electrical infrastructure used in solar energy
deployments. The relationship to the AI buildout is indirect: growing power
demand can support generation and grid investment.

Valuation read: P/S increased from approximately `3.84x` to `4.39x`. Treat
this as a power-buildout adjacency, not as a data-center infrastructure
supplier without further customer-level evidence.

Source: [Shoals investor relations](https://ir.shoals.com/)

### MNTS - In-Space Infrastructure

Industry: Satellite buses, transportation, and in-orbit services

Direction: Momentus is developing satellite and orbital-infrastructure
services, including Vigoride vehicles and NASA-contract mission work.

Valuation read: The share price increased approximately `194%`, while P/S
expanded from about `65.57x` to `151.69x`. Revenue remains small and financing
risk is material. This is a speculative space-economy screen result.

Source: [Momentus investor relations](https://investors.momentus.space/)

### SERV - Physical AI

Industry: Autonomous sidewalk delivery robots

Direction: Serve has deployed more than 2,000 delivery robots and is scaling
AI-powered last-mile delivery through enterprise partnerships.

Valuation read: The current price is slightly below the target band. P/S is
still above `270x`, so the relevant questions are fleet utilization, revenue
per robot, operating economics, and dilution.

Sources:
- [Serve Robotics investor relations](https://investors.serverobotics.com/)
- [Serve 2,000-robot fleet announcement](https://investors.serverobotics.com/news-releases/news-release-details/serve-robotics-builds-2000-autonomous-delivery-robots-creating)

### SATL - Geospatial Intelligence

Industry: Earth-observation satellites and analytics

Direction: Satellogic is expanding from imagery sales toward persistent
monitoring, defense intelligence, and sovereign satellite programs. Q1 2026
revenue rose `80%` year over year to `$6.1 million`.

Valuation read: The stock increased approximately `385%`, and P/S expanded
from about `4.16x` to `14.66x`. The business has improving traction, but
contract execution, constellation investment, and dilution remain important.

Sources:
- [Satellogic investor relations](https://investors.satellogic.com/)
- [Satellogic Q1 2026 results](https://investors.satellogic.com/news-releases/news-release-details/satellogic-reports-first-quarter-2026-financial-results)

### STEM - Grid Optimization Turnaround

Industry: Energy-storage software and services

Direction: Stem is an energy-storage optimization and services adjacency
screen. It requires separate turnaround diligence before being treated as an
AI-infrastructure candidate.

Valuation read: P/S fell from approximately `0.98x` to `0.56x`. A low multiple
can reflect business stress rather than opportunity.

Source: [Stem investor relations](https://investors.stem.com/)

### EOSE - Long-Duration Storage

Industry: Long-duration energy storage manufacturing

Direction: Eos is an energy-storage adjacency candidate. The relevant thesis
is whether grid and data-center power constraints support its manufacturing
ramp and project economics.

Valuation read: P/S compressed sharply as revenue ramped, but the current
multiple remains approximately `25x`. Manufacturing execution and financing
remain central risks.

Source: [Eos Energy investor relations](https://investors.eose.com/)

## Inferred Themes

These are inferences from company disclosures and the screen:

1. **Optical bandwidth remains a credible bottleneck.** POET is the closest
   lower-priced analogue to the `AAOI` and `LITE` winners, but it is earlier in
   commercialization and materially riskier.

2. **Power access has become an asset class.** BTDR and CLSK are attempting to
   monetize land and power portfolios across Bitcoin mining, colocation, and
   AI cloud workloads. FLNC, SHLS, STEM, and EOSE approach the same constraint
   from the grid side.

3. **Space infrastructure has a barbell profile.** SATL has visible contract
   and revenue momentum. MNTS offers more speculative upside with a much
   smaller operating base and greater financing risk.

4. **Physical AI is still early.** SERV fits the theme, but its multiple is
   driven by expected scale rather than current sales.

5. **Post-spike valuation must be separated from thematic quality.** A company
   can match the right industry narrative and still be expensive, diluted, or
   operationally unproven.

## Suggested Diligence Order

This is a research priority list, not a buy list:

1. `POET`: closest thematic match to the optical-networking winners; validate
   purchase-order conversion, manufacturing ramp, and dilution.
2. `BTDR`: quantify AI-cloud revenue separately from Bitcoin exposure and
   validate site-conversion timelines.
3. `CLSK`: separate monetizable AI/HPC sites from mining optionality.
4. `SATL`: validate backlog conversion, sovereign-customer concentration, and
   future capital needs.
5. `FLNC`: assess whether data-center demand changes growth materially or
   remains a broader grid-storage tailwind.
6. `SERV`: track fleet utilization and unit economics before relying on TAM.

## Caveats

- Share prices and valuation multiples move daily.
- Approximate historical market caps can differ from vendor values because
  SEC-reported shares update periodically and may not capture every intra-
  quarter issuance.
- P/S is not sufficient for capital-intensive or pre-revenue companies.
- Foreign issuers and mixed businesses require segment-level analysis.
- This screen does not evaluate balance-sheet quality, debt covenants,
  customer concentration, insider selling, or technical trading conditions.
