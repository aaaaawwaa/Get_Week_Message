from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import feedparser

from ..config import (
    CURRENT_AFFAIRS_KEYWORDS,
    CURRENT_AFFAIRS_SOURCES,
    HTTP_BACKOFF,
    HTTP_JITTER,
    HTTP_MIN_INTERVAL,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from ..http_client import request_bytes


def _matches_keywords(title: str, summary: str) -> bool:
    if not CURRENT_AFFAIRS_KEYWORDS:
        return True
    text = f"{title} {summary}".lower()
    for keyword in CURRENT_AFFAIRS_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False


def _format_published(entry: Dict) -> str:
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6]).isoformat(sep=" ")
    if getattr(entry, "updated_parsed", None):
        return datetime(*entry.updated_parsed[:6]).isoformat(sep=" ")
    return getattr(entry, "published", "") or getattr(entry, "updated", "") or ""


def fetch_current_affairs(limit: int = 20, timeout: int = 10) -> List[Dict]:
    results: List[Dict] = []

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }

    for source in CURRENT_AFFAIRS_SOURCES:
        if len(results) >= limit:
            break

        url = source.get("url", "") if isinstance(source, dict) else ""
        name = source.get("name", "") if isinstance(source, dict) else ""
        if not url:
            continue

        data = request_bytes(
            url,
            headers=headers,
            timeout=timeout,
            retries=HTTP_RETRIES,
            backoff=HTTP_BACKOFF,
            min_interval=HTTP_MIN_INTERVAL,
            jitter=HTTP_JITTER,
        )
        feed = feedparser.parse(data)

        for entry in feed.entries:
            if len(results) >= limit:
                break

            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            if not title or not link:
                continue
            if not _matches_keywords(title, summary):
                continue

            author = entry.get("author", "") or name
            results.append(
                {
                    "source": "affairs",
                    "title": title,
                    "url": link,
                    "author": author,
                    "metric": "",
                    "cover_url": "",
                    "published_at": _format_published(entry),
                    "rank": len(results) + 1,
                    "raw_json": "",
                }
            )

    return results
