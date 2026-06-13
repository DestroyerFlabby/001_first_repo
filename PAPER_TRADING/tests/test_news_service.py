from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.news_service import (
    detect_tracked_tickers,
    headline_topic_rows,
    hot_stock_rows,
    social_mention_rows,
)


def test_detect_tracked_tickers_avoids_common_word_false_positives() -> None:
    text = "AI stocks rally as ARM and NVDA lead chip gains"

    assert detect_tracked_tickers(text, {"AI", "ARM", "NVDA", "IT"}) == ["ARM", "NVDA"]


def test_headline_topics_group_market_themes_and_tracked_tickers() -> None:
    articles = [
        {
            "headline": "NVDA and ARM jump as AI data center spending accelerates",
            "summary": "",
        },
        {
            "headline": "Bitcoin miners rally after crypto prices rise",
            "summary": "",
        },
        {
            "headline": "Quantum stocks gain after new contract news",
            "summary": "",
        },
    ]

    rows = headline_topic_rows(articles, {"NVDA", "ARM", "BTC", "QBTS"})

    assert rows[0]["topic"] == "AI / data centers"
    assert rows[0]["mentions"] == 1
    assert rows[0]["tracked_tickers"] == ["ARM", "NVDA"]
    assert {row["topic"] for row in rows} >= {"Crypto / mining", "Quantum"}


def test_hot_stock_rows_combines_news_mentions_social_rank_and_signals() -> None:
    overview = {
        "stocks": [
            {
                "ticker": "NVDA",
                "daily_change_pct": 2.0,
                "five_day_change_pct": 8.0,
                "monthly_change_pct": 18.0,
                "return_pct": 40.0,
                "owners": ["chip_design"],
                "signal": {"overall_score": 90, "entry_signal": "fresh"},
            },
            {
                "ticker": "ARM",
                "daily_change_pct": 1.0,
                "five_day_change_pct": 4.0,
                "monthly_change_pct": 9.0,
                "return_pct": 20.0,
                "owners": ["insta_watchlist"],
                "signal": {"overall_score": 70, "entry_signal": "strict"},
            },
        ]
    }
    articles = [
        {"headline": "NVDA extends AI rally", "url": "https://example.com/nvda"},
        {"headline": "ARM demand grows with AI chips", "url": "https://example.com/arm"},
        {"headline": "NVDA data center revenue focus", "url": "https://example.com/nvda-2"},
    ]
    social = [{"ticker": "ARM", "rank": 1}, {"ticker": "NVDA", "rank": 4}]

    rows = hot_stock_rows(articles, overview, social)

    assert rows[0]["ticker"] == "NVDA"
    assert rows[0]["mentions"] == 2
    assert rows[0]["signal"] == "fresh"
    assert {row["ticker"] for row in rows} == {"NVDA", "ARM"}


def test_social_mention_rows_marks_untracked_symbols() -> None:
    rows = social_mention_rows(
        [{"ticker": "NVDA", "rank": 1}, {"ticker": "XYZ", "rank": 2}],
        {"stocks": [{"ticker": "NVDA", "owners": ["chip_design"], "five_day_change_pct": 5.5}]},
    )

    assert rows[0]["tracked"] is True
    assert rows[0]["owners"] == ["chip_design"]
    assert rows[1]["tracked"] is False
