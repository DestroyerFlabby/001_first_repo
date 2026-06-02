from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DAILY_COUNTS_FILE = ROOT / "data" / "historical_news_daily_counts.json"
NEWS_STRATEGIES = {
    "watchlist-variable-news-active": {
        "rule": "hold-while-news-active",
        "require_news_entry": False,
        "note": "Hold while the latest seven-day Alpaca news count remains above zero.",
    },
    "watchlist-variable-news-cooling": {
        "rule": "confirm-news-cooling",
        "require_news_entry": False,
        "note": "Sell only after technical deterioration and a non-increasing seven-day Alpaca news count.",
    },
    "watchlist-variable-news-cooling-early-exit": {
        "rule": "early-exit-on-news-cooling",
        "require_news_entry": False,
        "note": "Sell after five missing-signal sessions when one-month momentum is weak and Alpaca news is cooling.",
    },
    "watchlist-variable-news-required-entry": {
        "rule": "technical-baseline",
        "require_news_entry": True,
        "note": "Buy only when a technical entry also has at least one Alpaca news article in the latest seven days.",
    },
}


@lru_cache(maxsize=1)
def load_daily_news_counts() -> dict[str, object]:
    if not DAILY_COUNTS_FILE.exists():
        return {"tickers": {}, "to_date": None}
    try:
        payload = json.loads(DAILY_COUNTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"tickers": {}, "to_date": None}
    return payload if isinstance(payload, dict) else {"tickers": {}, "to_date": None}


def news_metrics(
    ticker_counts: dict[str, int],
    observed_day: date,
) -> dict[str, Decimal | int | None]:
    latest_7d = sum(
        int(ticker_counts.get((observed_day - timedelta(days=offset)).isoformat(), 0))
        for offset in range(7)
    )
    prior_7d = sum(
        int(ticker_counts.get((observed_day - timedelta(days=offset)).isoformat(), 0))
        for offset in range(7, 14)
    )
    return {
        "articles_7d": latest_7d,
        "articles_prior_7d": prior_7d,
        "weekly_velocity": Decimal(latest_7d) / prior_7d if prior_7d else None,
    }


def should_exit(
    rule: str,
    none_streak: int,
    one_month_return: Decimal,
    news: dict[str, Decimal | int | None],
) -> bool:
    baseline = none_streak >= 10 and one_month_return <= Decimal("-5")
    if rule == "technical-baseline":
        return baseline
    if rule == "hold-while-news-active":
        return baseline and int(news["articles_7d"]) == 0
    if rule == "confirm-news-cooling":
        return baseline and int(news["articles_7d"]) <= int(news["articles_prior_7d"])
    if rule == "early-exit-on-news-cooling":
        return (
            none_streak >= 5
            and one_month_return <= Decimal("-5")
            and int(news["articles_7d"]) <= int(news["articles_prior_7d"])
        )
    raise ValueError(f"unknown news strategy rule: {rule}")
