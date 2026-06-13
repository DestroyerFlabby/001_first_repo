from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from backend.news_strategy import load_daily_news_counts


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT.parent / ".env"
SNAPSHOT_FILE = ROOT / "data" / "news_snapshots.json"
CACHE_TTL = timedelta(hours=6)
CACHE_VERSION = 1
NEWS_WINDOW = timedelta(days=15)
MAX_ARTICLES = 150
DISPLAY_ARTICLES = 15
DISPLAY_VIDEOS = 10
LOCK = Lock()
MARKET_HEADLINE_LIMIT = 30
TRACKED_TICKER_EXCLUSIONS = {
    "A",
    "AI",
    "ARE",
    "FOR",
    "IT",
    "L",
    "ON",
    "OR",
    "T",
}
TOPIC_PATTERNS = {
    "AI / data centers": [
        "ai",
        "artificial intelligence",
        "data center",
        "data centre",
        "gpu",
        "nvidia",
        "accelerator",
    ],
    "Semiconductors": ["semiconductor", "chip", "foundry", "wafer", "memory", "hbm", "asml"],
    "Quantum": ["quantum", "qubit", "dwave", "ionq", "rigetti"],
    "Crypto / mining": ["bitcoin", "crypto", "ethereum", "miner", "mining", "blockchain"],
    "Defense / aerospace": ["defense", "defence", "aerospace", "satellite", "space", "missile"],
    "Energy / power": ["energy", "power", "grid", "nuclear", "uranium", "electricity"],
    "Rates / macro": ["fed", "rate", "inflation", "yield", "treasury", "jobs report"],
    "Gold / metals": ["gold", "silver", "copper", "rare earth", "lithium", "metal"],
    "Biotech / healthcare": ["fda", "drug", "clinical", "obesity", "healthcare", "biotech"],
    "Consumer platforms": ["streaming", "advertising", "e-commerce", "consumer", "subscription"],
}
RSS_SOURCES = [
    {
        "source": "marketwatch-top-stories",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    },
    {
        "source": "seeking-alpha-market-news",
        "url": "https://seekingalpha.com/market_currents.xml",
    },
    {
        "source": "yahoo-finance-news",
        "url": "https://finance.yahoo.com/news/rssindex",
    },
]


def load_dotenv() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def domain(url: str) -> str:
    return urlparse(url).netloc.casefold().removeprefix("www.")


def fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, object]:
    request = Request(
        url,
        headers={"User-Agent": "stock-tracking-advanced/1.0", **(headers or {})},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def fetch_text(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 8,
) -> str:
    request = Request(
        url,
        headers={"User-Agent": "stock-tracking-advanced/1.0", **(headers or {})},
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def alpaca_articles(ticker: str, now: datetime) -> tuple[list[dict[str, str]], dict[str, object]]:
    load_dotenv()
    api_key = os.environ.get("ALPACA_KEY") or os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("ALPACA_SECRET") or os.environ.get("APCA_API_SECRET_KEY")
    if not api_key or not api_secret:
        return [], {"source": "alpaca-news", "status": "unconfigured"}

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }
    articles: list[dict[str, str]] = []
    next_page_token: str | None = None
    while len(articles) < MAX_ARTICLES:
        params = {
            "symbols": ticker,
            "start": (now - NEWS_WINDOW).isoformat(),
            "end": now.isoformat(),
            "limit": min(50, MAX_ARTICLES - len(articles)),
            "sort": "desc",
        }
        if next_page_token:
            params["page_token"] = next_page_token
        payload = fetch_json(
            f"https://data.alpaca.markets/v1beta1/news?{urlencode(params)}",
            headers,
        )
        batch = payload.get("news", [])
        if not isinstance(batch, list):
            break
        articles.extend(
            {
                "headline": str(row.get("headline", "")),
                "url": str(row.get("url", "")),
                "created_at": str(row.get("created_at", "")),
                "source": str(row.get("source", "alpaca-news")),
            }
            for row in batch
            if isinstance(row, dict) and row.get("url") and row.get("created_at")
        )
        next_page_token = str(payload.get("next_page_token") or "") or None
        if not next_page_token or not batch:
            break
    return articles, {
        "source": "alpaca-news",
        "status": "ok",
        "articles": len(articles),
        "truncated": bool(next_page_token),
    }


def gdelt_articles(ticker: str) -> tuple[list[dict[str, str]], dict[str, object]]:
    params = {
        "query": f'"{ticker} stock"',
        "mode": "artlist",
        "maxrecords": 100,
        "format": "json",
        "timespan": "15d",
    }
    payload = fetch_json(
        f"https://api.gdeltproject.org/api/v2/doc/doc?{urlencode(params)}",
        timeout=5,
    )
    rows = payload.get("articles", [])
    if not isinstance(rows, list):
        rows = []
    articles = [
        {
            "headline": str(row.get("title", "")),
            "url": str(row.get("url", "")),
            "created_at": datetime.strptime(
                str(row["seendate"]), "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc).isoformat(),
            "source": str(row.get("domain") or "gdelt"),
        }
        for row in rows
        if isinstance(row, dict) and row.get("url") and row.get("seendate")
    ]
    return articles, {
        "source": "gdelt-doc",
        "status": "ok",
        "articles": len(articles),
        "truncated": len(rows) >= 100,
    }


def youtube_videos(ticker: str, now: datetime) -> tuple[list[dict[str, str]], dict[str, object]]:
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [], {"source": "youtube-data", "status": "unconfigured"}
    params = {
        "part": "snippet",
        "q": f"{ticker} stock",
        "type": "video",
        "order": "date",
        "publishedAfter": (now - NEWS_WINDOW).isoformat(),
        "maxResults": 50,
        "key": api_key,
    }
    payload = fetch_json(f"https://www.googleapis.com/youtube/v3/search?{urlencode(params)}")
    rows = payload.get("items", [])
    if not isinstance(rows, list):
        rows = []
    videos = [
        {
            "headline": str(row.get("snippet", {}).get("title", "")),
            "url": f"https://www.youtube.com/watch?v={row.get('id', {}).get('videoId')}",
            "created_at": str(row.get("snippet", {}).get("publishedAt", "")),
            "source": "youtube.com",
        }
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("id"), dict)
        and row["id"].get("videoId")
        and isinstance(row.get("snippet"), dict)
        and row["snippet"].get("publishedAt")
    ]
    return videos, {
        "source": "youtube-data",
        "status": "ok",
        "videos": len(videos),
        "truncated": bool(payload.get("nextPageToken")),
    }


def source_error(source: str, exc: Exception) -> dict[str, str]:
    if isinstance(exc, HTTPError):
        detail = f"HTTP {exc.code}"
    elif isinstance(exc, URLError):
        detail = str(exc.reason)
    else:
        detail = str(exc)
    return {"source": source, "status": "limited", "detail": detail}


def parse_rss_timestamp(value: str) -> str:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return utc_now().isoformat()


def rss_articles(source_name: str, url: str, limit: int = 20) -> tuple[list[dict[str, str]], dict[str, object]]:
    text = fetch_text(url, timeout=7)
    root = ET.fromstring(text)
    articles: list[dict[str, str]] = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or item.findtext("published") or "").strip()
        description = (item.findtext("description") or "").strip()
        if not title or not link:
            continue
        articles.append(
            {
                "headline": title,
                "url": link,
                "created_at": parse_rss_timestamp(published),
                "source": source_name,
                "summary": re.sub(r"<[^>]+>", "", description)[:500],
            }
        )
    return articles, {"source": source_name, "status": "ok", "articles": len(articles)}


def gdelt_market_articles() -> tuple[list[dict[str, str]], dict[str, object]]:
    params = {
        "query": '("stock market" OR "nasdaq" OR "s&p 500" OR "ai stocks" OR "semiconductor stocks")',
        "mode": "artlist",
        "maxrecords": 75,
        "format": "json",
        "timespan": "3d",
    }
    payload = fetch_json(
        f"https://api.gdeltproject.org/api/v2/doc/doc?{urlencode(params)}",
        timeout=7,
    )
    rows = payload.get("articles", [])
    if not isinstance(rows, list):
        rows = []
    articles = [
        {
            "headline": str(row.get("title", "")),
            "url": str(row.get("url", "")),
            "created_at": datetime.strptime(
                str(row["seendate"]), "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc).isoformat(),
            "source": str(row.get("domain") or "gdelt"),
            "summary": str(row.get("sourcecountry") or ""),
        }
        for row in rows
        if isinstance(row, dict) and row.get("url") and row.get("seendate")
    ]
    return articles, {
        "source": "gdelt-market-doc",
        "status": "ok",
        "articles": len(articles),
        "truncated": len(rows) >= 75,
    }


def stocktwits_trending_symbols() -> tuple[list[dict[str, object]], dict[str, object]]:
    payload = fetch_json("https://api.stocktwits.com/api/2/trending/symbols.json", timeout=7)
    rows = payload.get("symbols", [])
    if not isinstance(rows, list):
        rows = []
    symbols: list[dict[str, object]] = []
    for index, row in enumerate(rows[:25], start=1):
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        symbols.append(
            {
                "rank": index,
                "ticker": symbol,
                "title": str(row.get("title") or row.get("name") or symbol),
                "exchange": str(row.get("exchange") or ""),
                "watchlist_count": row.get("watchlist_count"),
                "source": "stocktwits-trending",
            }
        )
    return symbols, {"source": "stocktwits-trending", "status": "ok", "symbols": len(symbols)}


def dedupe_articles(articles: list[dict[str, str]], limit: int = MARKET_HEADLINE_LIMIT) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for row in articles:
        url = row.get("url", "").strip()
        headline = row.get("headline", "").strip()
        if not url or not headline:
            continue
        key = url.casefold()
        deduped[key] = {
            **row,
            "headline": headline,
            "url": url,
            "domain": domain(url) or row.get("source", ""),
        }
    return sorted(
        deduped.values(),
        key=lambda row: parse_timestamp(row.get("created_at") or utc_now().isoformat()),
        reverse=True,
    )[:limit]


def tracked_stock_index(overview_payload: dict[str, object] | None) -> dict[str, dict[str, object]]:
    if not overview_payload:
        return {}
    stocks = overview_payload.get("stocks", [])
    if not isinstance(stocks, list):
        return {}
    indexed: dict[str, dict[str, object]] = {}
    for row in stocks:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").upper().strip()
        if ticker:
            indexed[ticker] = row
    return indexed


def detect_tracked_tickers(text: str, tracked_tickers: set[str]) -> list[str]:
    normalized = text.upper()
    matches: list[str] = []
    for ticker in sorted(tracked_tickers):
        if ticker in TRACKED_TICKER_EXCLUSIONS or len(ticker) < 2:
            continue
        pattern = rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])"
        if re.search(pattern, normalized):
            matches.append(ticker)
    return matches


def topic_keyword_matches(text: str, keyword: str) -> bool:
    if " " in keyword or "/" in keyword or len(keyword) > 3:
        return keyword in text
    return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None


def headline_topic_rows(
    articles: list[dict[str, str]],
    tracked_tickers: set[str] | None = None,
    limit: int = 8,
) -> list[dict[str, object]]:
    tracked_tickers = tracked_tickers or set()
    topic_counts: Counter[str] = Counter()
    topic_examples: dict[str, str] = {}
    topic_tickers: dict[str, set[str]] = defaultdict(set)
    for row in articles:
        headline = str(row.get("headline") or "")
        text = f"{headline} {row.get('summary') or ''}".casefold()
        matched_tickers = detect_tracked_tickers(headline, tracked_tickers)
        for topic, keywords in TOPIC_PATTERNS.items():
            if any(topic_keyword_matches(text, keyword) for keyword in keywords):
                topic_counts[topic] += 1
                topic_examples.setdefault(topic, headline)
                topic_tickers[topic].update(matched_tickers)
    return [
        {
            "topic": topic,
            "mentions": count,
            "tracked_tickers": sorted(topic_tickers.get(topic, set()))[:8],
            "example_headline": topic_examples.get(topic, ""),
        }
        for topic, count in topic_counts.most_common(limit)
    ]


def hot_stock_rows(
    articles: list[dict[str, str]],
    overview_payload: dict[str, object] | None,
    social_symbols: list[dict[str, object]] | None = None,
    limit: int = 12,
) -> list[dict[str, object]]:
    indexed = tracked_stock_index(overview_payload)
    article_counts: Counter[str] = Counter()
    headline_examples: dict[str, str] = {}
    for row in articles:
        headline = str(row.get("headline") or "")
        for ticker in detect_tracked_tickers(headline, set(indexed)):
            article_counts[ticker] += 1
            headline_examples.setdefault(ticker, headline)
    social_rank = {
        str(row.get("ticker") or "").upper(): int(row.get("rank") or 999)
        for row in social_symbols or []
        if isinstance(row, dict)
    }
    candidates = set(article_counts) | (set(social_rank) & set(indexed))
    rows: list[dict[str, object]] = []
    for ticker in candidates:
        stock = indexed.get(ticker, {})
        signal = stock.get("signal") if isinstance(stock.get("signal"), dict) else {}
        news_mentions = article_counts.get(ticker, 0)
        social_score = max(0, 26 - social_rank.get(ticker, 999))
        daily = stock.get("daily_change_pct")
        five_day = stock.get("five_day_change_pct")
        monthly = stock.get("monthly_change_pct")
        score = (
            news_mentions * 4
            + social_score
            + max(0, float(signal.get("overall_score") or 0)) * 0.5
            + max(0, float(five_day or 0)) * 0.25
        )
        rows.append(
            {
                "ticker": ticker,
                "mentions": news_mentions,
                "social_rank": social_rank.get(ticker),
                "score": round(score, 2),
                "daily_change_pct": daily,
                "five_day_change_pct": five_day,
                "monthly_change_pct": monthly,
                "return_pct": stock.get("return_pct"),
                "owners": stock.get("owners") or [],
                "signal": signal.get("entry_signal") or signal.get("label") or "none",
                "example_headline": headline_examples.get(ticker, ""),
            }
        )
    return sorted(rows, key=lambda row: float(row.get("score") or 0), reverse=True)[:limit]


def social_mention_rows(
    social_symbols: list[dict[str, object]],
    overview_payload: dict[str, object] | None,
    limit: int = 15,
) -> list[dict[str, object]]:
    indexed = tracked_stock_index(overview_payload)
    rows: list[dict[str, object]] = []
    for row in social_symbols[:limit]:
        ticker = str(row.get("ticker") or "").upper()
        stock = indexed.get(ticker, {})
        rows.append(
            {
                **row,
                "tracked": ticker in indexed,
                "daily_change_pct": stock.get("daily_change_pct"),
                "five_day_change_pct": stock.get("five_day_change_pct"),
                "monthly_change_pct": stock.get("monthly_change_pct"),
                "owners": stock.get("owners") or [],
            }
        )
    return rows


def read_snapshots() -> dict[str, object]:
    if not SNAPSHOT_FILE.exists():
        return {"snapshots": {}}
    try:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"snapshots": {}}
    return payload if isinstance(payload, dict) else {"snapshots": {}}


def write_snapshot(ticker: str, summary: dict[str, object]) -> None:
    with LOCK:
        payload = read_snapshots()
        snapshots = payload.setdefault("snapshots", {})
        if not isinstance(snapshots, dict):
            snapshots = {}
            payload["snapshots"] = snapshots
        ticker_rows = snapshots.setdefault(ticker, {})
        if not isinstance(ticker_rows, dict):
            ticker_rows = {}
            snapshots[ticker] = ticker_rows
        ticker_rows[str(summary["snapshot_date"])] = summary
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def cached_snapshot(ticker: str, now: datetime) -> dict[str, object] | None:
    snapshots = read_snapshots().get("snapshots", {})
    if not isinstance(snapshots, dict):
        return None
    ticker_rows = snapshots.get(ticker, {})
    if not isinstance(ticker_rows, dict):
        return None
    summary = ticker_rows.get(now.date().isoformat())
    if not isinstance(summary, dict):
        return None
    if summary.get("cache_version") != CACHE_VERSION:
        return None
    fetched_at = summary.get("fetched_at")
    if not isinstance(fetched_at, str):
        return None
    try:
        is_fresh = now - parse_timestamp(fetched_at) <= CACHE_TTL
    except ValueError:
        return None
    return summary if is_fresh else None


def summarize_articles(
    ticker: str,
    articles: list[dict[str, str]],
    videos: list[dict[str, str]],
    sources: list[dict[str, object]],
    now: datetime,
) -> dict[str, object]:
    deduped = {
        row["url"].casefold(): {
            **row,
            "domain": domain(row["url"]) or row["source"],
        }
        for row in articles
        if row.get("url") and row.get("created_at")
    }
    rows = sorted(
        deduped.values(),
        key=lambda row: parse_timestamp(row["created_at"]),
        reverse=True,
    )
    last_day = [row for row in rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=1)]
    last_week = [row for row in rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=7)]
    prior_week = [
        row
        for row in rows
        if now - timedelta(days=14) <= parse_timestamp(row["created_at"]) < now - timedelta(days=7)
    ]
    prior_daily_average = len(prior_week) / 7
    velocity = len(last_day) / prior_daily_average if prior_daily_average else None
    video_rows = sorted(
        videos,
        key=lambda row: parse_timestamp(row["created_at"]),
        reverse=True,
    )
    videos_last_week = [
        row for row in video_rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=7)
    ]
    videos_prior_week = [
        row
        for row in video_rows
        if now - timedelta(days=14) <= parse_timestamp(row["created_at"]) < now - timedelta(days=7)
    ]
    video_velocity = (
        len(videos_last_week) / len(videos_prior_week) if videos_prior_week else None
    )
    return {
        "ticker": ticker,
        "cache_version": CACHE_VERSION,
        "snapshot_date": now.date().isoformat(),
        "fetched_at": now.isoformat(),
        "articles_24h": len(last_day),
        "articles_7d": len(last_week),
        "articles_prior_7d": len(prior_week),
        "daily_velocity_ratio": round(velocity, 4) if velocity is not None else None,
        "source_diversity_7d": len({row["domain"] for row in last_week}),
        "videos_7d": len(videos_last_week),
        "videos_prior_7d": len(videos_prior_week),
        "video_velocity_ratio": round(video_velocity, 4) if video_velocity is not None else None,
        "sources": sources,
        "articles": rows[:DISPLAY_ARTICLES],
        "videos": video_rows[:DISPLAY_VIDEOS],
        "note": (
            "News velocity compares the latest 24-hour article count with the "
            "daily average from the preceding seven days. Free sources can be "
            "incomplete or temporarily rate-limited."
        ),
    }


def historical_daily_counts(ticker: str) -> list[dict[str, object]]:
    payload = load_daily_news_counts()
    tickers = payload.get("tickers", {})
    if not isinstance(tickers, dict):
        return []
    counts = tickers.get(ticker.upper(), {})
    if not isinstance(counts, dict):
        return []
    rows: list[dict[str, object]] = []
    for day, value in sorted(counts.items()):
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        rows.append({"date": day, "articles": count})
    return rows


def news_summary(ticker: str) -> dict[str, object]:
    normalized = ticker.upper()
    now = utc_now()
    cached = cached_snapshot(normalized, now)
    if cached:
        return {**cached, "daily_counts": historical_daily_counts(normalized)}

    articles: list[dict[str, str]] = []
    videos: list[dict[str, str]] = []
    sources: list[dict[str, object]] = []
    try:
        rows, status = alpaca_articles(normalized, now)
        articles.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("alpaca-news", exc))
    try:
        rows, status = gdelt_articles(normalized)
        articles.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("gdelt-doc", exc))
    try:
        rows, status = youtube_videos(normalized, now)
        videos.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("youtube-data", exc))

    summary = summarize_articles(normalized, articles, videos, sources, now)
    try:
        write_snapshot(normalized, summary)
    except OSError:
        pass
    return {**summary, "daily_counts": historical_daily_counts(normalized)}


def market_news_dashboard(overview_payload: dict[str, object] | None = None) -> dict[str, object]:
    articles: list[dict[str, str]] = []
    sources: list[dict[str, object]] = []
    for source in RSS_SOURCES:
        try:
            rows, status = rss_articles(str(source["source"]), str(source["url"]))
            articles.extend(rows)
            sources.append(status)
        except Exception as exc:
            sources.append(source_error(str(source["source"]), exc))
    try:
        rows, status = gdelt_market_articles()
        articles.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("gdelt-market-doc", exc))

    social_symbols: list[dict[str, object]] = []
    try:
        social_symbols, status = stocktwits_trending_symbols()
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("stocktwits-trending", exc))

    headlines = dedupe_articles(articles)
    indexed = tracked_stock_index(overview_payload)
    social_rows = social_mention_rows(social_symbols, overview_payload)
    return {
        "schema_version": "1.0",
        "calculation_version": "market-news-dashboard-1.0",
        "fetched_at": utc_now().isoformat(),
        "headline_count": len(headlines),
        "headlines": headlines,
        "hot_topics": headline_topic_rows(headlines, set(indexed)),
        "hot_stocks": hot_stock_rows(headlines, overview_payload, social_symbols),
        "social_mentions": social_rows,
        "sources": sources,
        "note": (
            "Market news uses free RSS/API-style sources plus the tracked-stock universe. "
            "Social mentions are directional because public social endpoints can change, "
            "rate-limit, or omit exact message counts."
        ),
    }
