# Draft Rebalance Methodology

The rebalance engine requires explicit current sleeve weights and compares them with an existing demo policy profile. It does not infer holdings, create orders, or write to a trading ledger.

For each target weight, the tolerance is the larger of two percentage points or 20% of target weight. A breached sleeve first moves to the nearest permitted boundary. Remaining net buys or sells are distributed within other sleeves' available policy bands so proposed weights remain self-financing and total 100%.

Exact-target mode is available only as an explicit comparison. The default boundary method is intended to reduce unnecessary turnover.

Outputs remain `draft_review_required`. Taxes, tax lots, spreads, FX, commissions, liquidity, and account restrictions are not modeled.
