from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.macro_statement_service import classify_macro_tone, parse_bank_of_canada_feed


RSS_SAMPLE = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns="http://purl.org/rss/1.0/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <item rdf:about="https://www.bankofcanada.ca/example">
    <title>Bank of Canada maintains policy rate</title>
    <link>https://www.bankofcanada.ca/example</link>
    <description>Underlying inflation remains persistent and price pressures are above target.</description>
    <dc:date>2026-06-10T09:47:13+00:00</dc:date>
  </item>
</rdf:RDF>
"""


def statement(day: str, text: str) -> dict[str, object]:
    return {
        "source": "Press releases",
        "source_url": "https://www.bankofcanada.ca/content_type/press-releases/feed/",
        "title": text,
        "summary": text,
        "url": "https://www.bankofcanada.ca/example",
        "published_date": day,
        "text": text,
    }


def test_parse_bank_of_canada_rdf_feed_extracts_dated_items() -> None:
    rows = parse_bank_of_canada_feed(RSS_SAMPLE, "Press releases", "https://feed.example")

    assert rows == [
        {
            "source": "Press releases",
            "source_url": "https://feed.example",
            "title": "Bank of Canada maintains policy rate",
            "summary": "Underlying inflation remains persistent and price pressures are above target.",
            "url": "https://www.bankofcanada.ca/example",
            "published_date": "2026-06-10",
            "text": "Bank of Canada maintains policy rate. Underlying inflation remains persistent and price pressures are above target.",
        }
    ]


def test_macro_tone_identifies_tightening_risk_off_language() -> None:
    tone = classify_macro_tone(
        [
            statement("2026-06-10", "Underlying inflation remains persistent and price pressures are above target."),
            statement("2026-04-29", "Financial stability risks and tariff uncertainty remain elevated."),
        ],
        date(2026, 6, 12),
    )

    assert tone["classification"] == "risk_off"
    assert tone["rate_bias"] == "tightening"
    assert tone["equity_exposure_multiplier"] < 1
    assert tone["evidence"]


def test_macro_tone_respects_as_of_date_and_can_turn_risk_on() -> None:
    tone = classify_macro_tone(
        [
            statement("2026-06-10", "Inflationary pressures are persistent and above target."),
            statement("2026-01-28", "The Bank is easing policy as weak demand and modest growth create slack."),
        ],
        date(2026, 1, 31),
    )

    assert tone["classification"] == "risk_on"
    assert tone["rate_bias"] == "easing"
    assert tone["latest_statement"]["published_date"] == "2026-01-28"


def test_macro_tone_empty_feed_is_neutral() -> None:
    tone = classify_macro_tone([], date(2026, 6, 12))

    assert tone["classification"] == "neutral"
    assert tone["equity_exposure_multiplier"] == 1.0
    assert tone["source_status"] == "empty"
