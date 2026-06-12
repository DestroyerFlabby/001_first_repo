from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.dashboard_service import MAIN_PRIORITY_PORTFOLIOS, add_portfolio_priority, portfolio_priority


def portfolio(investor: str, source: str = "paper-ledger", positions: int = 4) -> dict[str, object]:
    return {"investor": investor, "source": source, "position_count": positions}


def test_primary_dashboard_set_has_thirteen_table_portfolios() -> None:
    # The systematic model and daily EOD rotation live in dedicated tabs,
    # bringing the visible decision set to fifteen portfolios in total.
    assert len(MAIN_PRIORITY_PORTFOLIOS) == 13


def test_named_traders_and_core_strategies_remain_primary() -> None:
    for investor in (
        "nisarg",
        "amswann",
        "bdinvesting",
        "brandon",
        "joyeeyang",
        "russellckai",
        "watchlist-variable",
        "watchlist-master",
        "watchlist-variable-news-optimized-experimental",
        "watchlist-variable-news-optimized-hybrid",
        "watchlist-variable-news-analysis-driven",
        "long-term-watchlist",
        "short-term-watchlist",
    ):
        assert portfolio_priority(portfolio(investor))[0] == "main"


def test_secondary_and_future_portfolios_default_to_research_watchlists() -> None:
    for investor in ("memory", "insta_watchlist", "analyst-mike-mayo", "future-experiment"):
        tagged = add_portfolio_priority(portfolio(investor))
        assert tagged["portfolio_priority"] == "low"
        assert tagged["portfolio_group"] == "research-watchlists"
        assert "Research Watchlists" in str(tagged["portfolio_priority_reason"])
