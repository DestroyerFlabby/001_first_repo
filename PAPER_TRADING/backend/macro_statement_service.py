from __future__ import annotations

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


BANK_OF_CANADA_FEEDS = [
    {
        "name": "Press releases",
        "url": "https://www.bankofcanada.ca/content_type/press-releases/feed/",
    },
    {
        "name": "Monetary Policy Report",
        "url": "https://www.bankofcanada.ca/content_type/mpr/feed/",
    },
    {
        "name": "Summary of deliberations",
        "url": "https://www.bankofcanada.ca/content_type/summary-of-deliberations/feed/",
    },
]
SOURCE_DOCUMENTATION_URL = "https://www.bankofcanada.ca/rss-feeds/"
FETCH_CACHE_SECONDS = 30 * 60
_FETCH_CACHE: dict[str, object] = {
    "fetched_at": None,
    "statements": [],
    "warnings": [],
}

EASING_TERMS = {
    "cut": 4,
    "cuts": 4,
    "lower": 3,
    "lowered": 4,
    "easing": 4,
    "less restrictive": 5,
    "weak demand": 3,
    "slowed": 2,
    "slowing": 2,
    "slack": 3,
    "below target": 4,
    "unemployment": 2,
    "modest growth": 2,
}
TIGHTENING_TERMS = {
    "raise": 4,
    "raised": 4,
    "higher": 2,
    "restrictive": 3,
    "inflationary pressure": 5,
    "inflationary pressures": 5,
    "above target": 4,
    "persistent": 3,
    "wage growth": 3,
    "underlying inflation": 3,
    "price pressures": 3,
    "overheating": 4,
}
RISK_TERMS = {
    "uncertain": 2,
    "uncertainty": 2,
    "tariff": 2,
    "tariffs": 2,
    "geopolitical": 2,
    "financial stability": 3,
    "vulnerabilities": 3,
    "risk": 1,
    "risks": 1,
}
GROWTH_TERMS = {
    "resilience": 2,
    "resilient": 2,
    "growth": 1,
    "strong": 2,
    "accelerate": 2,
    "accelerates": 2,
}


def _clean_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError):
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_bank_of_canada_feed(xml_text: str, source_name: str, source_url: str) -> list[dict[str, object]]:
    root = ET.fromstring(xml_text)
    ns = {
        "rss1": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "cb": "http://www.cbwiki.net/wiki/index.php/Specification_1.2/",
    }
    items: list[dict[str, object]] = []
    for item in root.findall(".//rss1:item", ns):
        title = _clean_text(item.findtext("rss1:title", default="", namespaces=ns))
        description = _clean_text(item.findtext("rss1:description", default="", namespaces=ns))
        link = _clean_text(item.findtext("rss1:link", default="", namespaces=ns))
        published = _parse_date(item.findtext("dc:date", default="", namespaces=ns))
        if not title or not published:
            continue
        items.append(
            {
                "source": source_name,
                "source_url": source_url,
                "title": title,
                "summary": description,
                "url": link,
                "published_date": published.isoformat(),
                "text": f"{title}. {description}",
            }
        )
    return items


def _weighted_count(text: str, terms: dict[str, int]) -> int:
    lowered = text.casefold()
    return sum(weight * lowered.count(term) for term, weight in terms.items())


def classify_macro_tone(statements: list[dict[str, object]], as_of: date | None = None) -> dict[str, object]:
    eligible = [
        row for row in statements
        if not as_of or date.fromisoformat(str(row["published_date"])) <= as_of
    ]
    eligible.sort(key=lambda row: str(row["published_date"]), reverse=True)
    recent = eligible[:6]
    if not recent:
        return {
            "classification": "neutral",
            "rate_bias": "neutral",
            "score": 0,
            "equity_exposure_multiplier": 1.0,
            "growth_tilt_multiplier": 1.0,
            "evidence": [],
            "latest_statement": None,
            "source_status": "empty",
            "source_documentation_url": SOURCE_DOCUMENTATION_URL,
        }

    easing = tightening = risk = growth = 0
    evidence: list[dict[str, object]] = []
    for index, row in enumerate(recent):
        recency_weight = max(1, 6 - index)
        text = str(row.get("text") or "")
        row_easing = _weighted_count(text, EASING_TERMS) * recency_weight
        row_tightening = _weighted_count(text, TIGHTENING_TERMS) * recency_weight
        row_risk = _weighted_count(text, RISK_TERMS) * recency_weight
        row_growth = _weighted_count(text, GROWTH_TERMS) * recency_weight
        easing += row_easing
        tightening += row_tightening
        risk += row_risk
        growth += row_growth
        if row_easing or row_tightening or row_risk or row_growth:
            evidence.append(
                {
                    "date": row["published_date"],
                    "source": row["source"],
                    "title": row["title"],
                    "url": row["url"],
                    "easing_score": row_easing,
                    "tightening_score": row_tightening,
                    "risk_score": row_risk,
                    "growth_score": row_growth,
                }
            )

    raw_score = easing + growth - tightening - risk
    if raw_score >= 12:
        classification = "risk_on"
    elif raw_score <= -12:
        classification = "risk_off"
    else:
        classification = "neutral"
    if easing - tightening >= 8:
        rate_bias = "easing"
    elif tightening - easing >= 8:
        rate_bias = "tightening"
    else:
        rate_bias = "neutral"
    equity_multiplier = {"risk_on": 1.05, "neutral": 1.0, "risk_off": 0.9}[classification]
    growth_multiplier = {"risk_on": 1.05, "neutral": 1.0, "risk_off": 0.92}[classification]
    return {
        "classification": classification,
        "rate_bias": rate_bias,
        "score": raw_score,
        "equity_exposure_multiplier": equity_multiplier,
        "growth_tilt_multiplier": growth_multiplier,
        "evidence": evidence[:5],
        "latest_statement": recent[0],
        "source_status": "ok",
        "source_documentation_url": SOURCE_DOCUMENTATION_URL,
        "input_scores": {
            "easing": easing,
            "tightening": tightening,
            "risk": risk,
            "growth": growth,
        },
        "methodology": (
            "Classifies recent official Bank of Canada RSS items by easing, tightening, risk, "
            "and growth language. Used as a macro context overlay; historical portfolio replay "
            "only uses dated statements available on or before the simulated day."
        ),
    }


def fetch_bank_of_canada_statements(timeout_seconds: float = 4.0) -> tuple[list[dict[str, object]], list[str]]:
    cached_at = _FETCH_CACHE.get("fetched_at")
    if isinstance(cached_at, datetime) and (datetime.now(timezone.utc) - cached_at).total_seconds() < FETCH_CACHE_SECONDS:
        return list(_FETCH_CACHE["statements"]), list(_FETCH_CACHE["warnings"])

    statements: list[dict[str, object]] = []
    warnings: list[str] = []
    for feed in BANK_OF_CANADA_FEEDS:
        try:
            request = urllib.request.Request(
                str(feed["url"]),
                headers={"User-Agent": "paper-trading-dashboard/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
            statements.extend(parse_bank_of_canada_feed(body, str(feed["name"]), str(feed["url"])))
        except Exception as exc:  # pragma: no cover - network behavior varies by environment.
            warnings.append(f"{feed['name']}: {exc}")
    unique: dict[tuple[str, str], dict[str, object]] = {}
    for row in statements:
        unique[(str(row["url"]), str(row["published_date"]))] = row
    ordered = sorted(unique.values(), key=lambda row: str(row["published_date"]), reverse=True)
    _FETCH_CACHE.update(
        {
            "fetched_at": datetime.now(timezone.utc),
            "statements": ordered,
            "warnings": warnings,
        }
    )
    return ordered, warnings


def bank_of_canada_macro_context(as_of: date | None = None) -> dict[str, Any]:
    statements, warnings = fetch_bank_of_canada_statements()
    tone = classify_macro_tone(statements, as_of)
    tone["as_of"] = as_of.isoformat() if as_of else None
    tone["fetched_at"] = datetime.now(timezone.utc).isoformat()
    tone["statements"] = [
        {key: value for key, value in row.items() if key != "text"}
        for row in statements[:12]
        if not as_of or date.fromisoformat(str(row["published_date"])) <= as_of
    ]
    tone["warnings"] = warnings
    tone["sources"] = {
        "documentation": SOURCE_DOCUMENTATION_URL,
        "feeds": BANK_OF_CANADA_FEEDS,
    }
    if warnings and not statements:
        tone["source_status"] = "unavailable"
        tone["classification"] = "neutral"
        tone["rate_bias"] = "neutral"
        tone["score"] = 0
        tone["equity_exposure_multiplier"] = 1.0
        tone["growth_tilt_multiplier"] = 1.0
    return tone
