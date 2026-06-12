# Wealth UI Revamp Assignment

Date: 2026-06-12
From: Main Codex integration agent
To: Listening wealth-management agent

## Objective

Revamp the dashboard information architecture and visual design so wealth management feels like its own product area, not just another crowded section inside the stock-tracking dashboard.

The user specifically wants:

- Wealth management moved fully into a separate top-level tab/area at the top of the page.
- A cleaner, more professional wealth-management UI inspired by modern investment, private banking, and family-office dashboard patterns.
- The other trading/research dashboard content should remain available, but wealth should become its own clearly separated experience.
- Keep the daily stock and trader movers on the main/home trading page.

## External design research summary

Use these observations as design direction, not as copied layouts:

1. Family-office dashboards emphasize consolidated portfolio visibility, cash flow, performance, risk, allocation, rebalancing, reconciliation, compliance/review workflows, and customizable decision pages.
   - Source: Masttro family office dashboard article, https://masttro.com/insights/family-office-dashboards
2. Wealth-management case studies frequently put performance and asset allocation at the top, with flexible views by asset class, manager, or region.
   - Source: UXDA Bugatti-Caliber wealth-management case study, https://theuxda.com/blog/ux-case-study-bugatti-caliber-experience-uhnwi-200-billion-assets
3. Investment dashboard UX guidance treats net worth/value, absolute and percentage return, asset allocation, chronological performance periods, and direct action/review entry points as standard portfolio-dashboard requirements.
   - Source: Lollypop investment dashboard UX guide, https://lollypop.design/blog/2026/may/investment-dashboard-ux-design-guide/
4. Financial dashboard guidance stresses moving beyond raw monitoring into actionable, mobile-friendly reporting and decision support.
   - Source: Qlik financial dashboard examples, https://www.qlik.com/us/dashboard-examples/financial-dashboards
5. Current design galleries for wealth dashboards repeatedly use:
   - Calm dark/navy or off-white premium backgrounds.
   - Green/teal positive accents and restrained red/orange risk accents.
   - Rounded summary cards.
   - Clear sidebar/top navigation.
   - Large portfolio value and allocation/risk modules above detail tables.
   - Mobile-friendly card stacking.
   - Sources: Dribbble wealth dashboard search and investment dashboard examples, https://dribbble.com/search/wealth-management-dashboard and https://dribbble.com/shots/27049016-Investment-Dashboard-UI-Portfolio-Tracking-Wealth-Management

## Design direction

Do not create a flashy retail-trading theme. Prefer a calm wealth-management look:

- Background: deep navy / slate (`#071421`, `#0d1b2a`) or warm light alternative if simpler.
- Primary accent: teal/emerald (`#39d98a`, `#42e6b8`) for health/positive/action.
- Secondary accent: muted gold (`#d6b56d`) for premium/wealth cues.
- Risk accent: soft red/orange (`#ff6b6b`, `#f59e0b`) only for alerts.
- Neutral text: high contrast but not pure neon.
- Reduce visual crowding by creating a wealth shell with sub-tabs or side navigation.

## Desired information architecture

At the top level, separate the app into at least:

1. **Trading Dashboard**
   - Keep current home / daily movers / portfolios / stocks / sectors / strategy/research flow.
   - Daily movers for stocks and traders should stay prominent here.

2. **Wealth Management**
   - A separate top-level tab or shell.
   - Inside it, use wealth-specific navigation:
     - Overview
     - Allocation
     - Risk
     - Performance
     - Rebalancing
     - Model / Rotation Research
     - AI Wealth / Operations
   - The existing services and panels can be reused; the task is to reorganize, not rewrite analytics.

3. **Admin / Research**
   - Universe, Strategy Lab, research notes, registries, and operational tools that are not daily wealth review.

## Wealth landing page requirements

Create a clear Wealth Overview landing experience that can reuse existing API data:

- Hero row:
  - selected date window
  - portfolio/tracked value if available
  - leading portfolio/strategy
  - risk/data quality status
  - action count or review queue count
- Decision cards:
  - Allocation drift / concentration
  - Risk / drawdown
  - Performance / contribution
  - Rebalance candidate
  - Data quality
- Make each card link or switch to the relevant wealth section.

## Implementation constraints

- Keep changes scoped to `PAPER_TRADING`.
- Do not remove existing functionality.
- Do not alter calculation logic unless needed for UI data plumbing.
- Do not create broker/order behavior.
- Keep all investment language educational/research-oriented.
- Mobile/responsive behavior matters: wealth subnavigation must work on phone widths.
- Avoid adding a heavy frontend framework unless the existing app cannot support the change.
- Prefer existing `index.html`, `app.js`, and `styles.css` patterns.

## Suggested implementation plan

1. Add a top-level app mode switch, likely:
   - Trading
   - Wealth Management
   - Admin / Research
2. Move current wealth panels behind the Wealth Management area:
   - AI Wealth
   - Allocation
   - Risk
   - Performance
   - Rebalancing
   - Model Portfolio
   - Day Rotation
3. Keep trading panels in the Trading area:
   - Home
   - Portfolios
   - Stocks
   - Sectors
4. Move Universe, Strategy Lab, Research to Admin / Research.
5. Add a wealth overview panel that gives a compact executive summary and links to wealth panels.
6. Update CSS for a professional wealth shell:
   - cleaner spacing
   - less crowded tab groups
   - better mobile stacking
   - clearer active states
   - premium but restrained color tokens
7. Add minimal tests/checks:
   - `node --check PAPER_TRADING/frontend/app.js`
   - selector/static smoke check if practical
   - existing Python tests if backend touched
   - local page smoke if feasible

## Response expected

Create:

`response-20260612-<time>-wealth-ui-revamp.md`

Include:

1. What UI structure you recommend.
2. What files you changed.
3. Any screenshots are optional; textual summary is enough.
4. How you validated it.
5. Any blockers or decisions needed from the integration agent.

If you think this should be split into two phases, implement the safe first phase and explain the second.
