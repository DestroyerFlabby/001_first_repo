# Wealth Management Dashboard And Portfolio Weighting Assignment

Date: 2026-06-12
From: Dashboard agent
Repository scope: `PAPER_TRADING` only
Current phase: Research and planning only

## Objective

Review the existing dashboard and propose how to optimize its current pages or create new pages that provide materially better wealth-management analysis.

The dashboard already contains portfolio returns, holdings, realized positions, trade ledgers, signals, news, sector analysis, model portfolios, and daily EOD rotation. The next phase should make it more useful for portfolio construction, risk management, allocation decisions, and ongoing wealth-management reviews.

## Assignment

Develop a concrete plan covering both dashboard design and portfolio weighting methodology.

### 1. Wealth-Management Pages

Review the current frontend and backend capabilities. Recommend which existing pages should be reorganized, simplified, or expanded and which new pages should be created.

Consider decision-useful analysis such as:

- Household or total-wealth overview
- Asset allocation by asset class, geography, currency, sector, account, and strategy
- Risk and return analysis
- Drawdown and recovery analysis
- Contribution analysis and performance attribution
- Realized versus unrealized gains
- Income, dividends, and cash-flow views where data supports them
- Concentration and overlap between portfolios
- Correlation and diversification analysis
- Benchmark-relative performance
- Goal tracking and required-return analysis
- Rebalancing recommendations
- Scenario and stress testing
- Tax-aware analysis, clearly separated from financial advice
- Data quality, stale-price, missing-history, and confidence indicators
- Client-style review reports and downloadable summaries

Do not propose decorative metrics. Explain what decision each page or metric supports.

### 2. Portfolio Weighting Plan

Develop a defensible approach for weighting portfolios and securities. The plan should address:

- Strategic asset allocation versus tactical tilts
- Equal weight, market-cap weight, risk parity, inverse volatility, minimum variance, maximum diversification, and score-weighted approaches
- Position, sector, geography, currency, and thematic caps
- Liquidity and volatility constraints
- Signal and news confidence without allowing either to dominate risk controls
- Cash allocation
- Rebalancing frequency and tolerance bands
- Turnover and transaction-cost controls
- Benchmark selection
- Drawdown controls and de-risking rules
- How to handle ETFs, individual stocks, crypto, Canadian securities, and USD exposure
- How weighting should differ by portfolio purpose and risk profile
- Point-in-time backtesting and next-close execution requirements
- Avoiding lookahead, survivorship, overfitting, and in-sample optimization

Propose a default methodology and any justified alternatives. Include formulas or pseudocode where useful.

### 3. Research

Use whatever research is needed to support the recommendations. Prefer primary or high-quality sources such as:

- CFA Institute research
- MSCI and S&P Dow Jones methodology documents
- AQR and established asset-management research
- Academic finance papers
- Regulatory guidance relevant to portfolio reporting and risk disclosure
- Official documentation for any proposed data sources

Clearly separate sourced facts, professional conventions, and your own recommendations. Include links and access dates in the response.

### 4. Compatibility Review

Inspect the current repository before proposing architecture. Identify:

- Existing calculations and components that can be reused
- Missing data required for each proposed feature
- Expensive calculations that need caching or asynchronous jobs on Render
- Changes that could affect mobile performance
- API contracts and files likely to be changed
- Dependencies on `PERSONAL_WEALTH_PLANNING` or other folders, but do not edit outside `PAPER_TRADING`

### 5. Prioritized Delivery Plan

Return a phased implementation plan:

1. Immediate improvements with existing data
2. Medium-complexity analytics
3. Advanced portfolio construction and optimization
4. Features blocked by unavailable or unreliable data

For each proposed item include:

- User value
- Required data
- Backend changes
- Frontend changes
- Testing strategy
- Performance implications
- Risks and assumptions
- Priority and estimated implementation complexity

## Constraints

- Planning and research only. Do not implement yet.
- Do not modify existing application files.
- Do not revert or overwrite concurrent changes.
- Keep this project educational and analytical; do not present personalized investment advice as guaranteed or suitable.
- Weighting recommendations must prioritize risk controls and robustness over maximizing the historical backtest.
- Preserve point-in-time data and next-close execution conventions.

## Response Instructions

Create a timestamped response in this folder:

`response-YYYYMMDD-HHMMSS-wealth-management-plan.md`

The response should contain:

1. Executive recommendation
2. Current-state assessment
3. Proposed page and navigation structure
4. Proposed portfolio-weighting methodology
5. Research findings and source links
6. Data and architecture requirements
7. Phased implementation plan
8. Open questions and identified conflicts

