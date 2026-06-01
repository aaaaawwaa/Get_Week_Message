from datetime import datetime
import logging
import traceback
from typing import Dict, List

import feedparser

from .. import config as _cfg
from ..http_client import request_bytes


def _matches_keywords(title: str, summary: str) -> bool:
    if not _cfg.CURRENT_AFFAIRS_KEYWORDS:
        return True
    text = f"{title} {summary}".lower()
    for keyword in _cfg.CURRENT_AFFAIRS_KEYWORDS:
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
        "User-Agent": _cfg.USER_AGENT,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }

    # 计算每个源的平均分配数，确保每个源都有机会
    num_sources = max(1, len(_cfg.CURRENT_AFFAIRS_SOURCES))
    per_source_limit = max(1, limit // num_sources) if num_sources > 1 else limit

    for source in _cfg.CURRENT_AFFAIRS_SOURCES:
        if len(results) >= limit:
            break

        url = source.get("url", "") if isinstance(source, dict) else ""
        name = source.get("name", "") if isinstance(source, dict) else ""
        if not url:
            continue

        try:
            data = request_bytes(
                url,
                headers=headers,
                timeout=timeout,
                retries=_cfg.HTTP_RETRIES,
                backoff=_cfg.HTTP_BACKOFF,
                min_interval=_cfg.HTTP_MIN_INTERVAL,
                jitter=_cfg.HTTP_JITTER,
            )
        except Exception as exc:
            logger = logging.getLogger("weekly")
            err_msg = f"{type(exc).__name__}: {exc}"
            logger.warning("fetch_current_affairs: %s failed: %s", name, err_msg)
            # 将错误信息写入 results 中的标记项，供 run_weekly 汇总
            results.append({
                "source": name,
                "title": "",
                "url": "",
                "author": "",
                "metric": "",
                "cover_url": "",
                "published_at": "",
                "rank": 0,
                "raw_json": "",
                "_error": err_msg,
            })
            continue

        feed = feedparser.parse(data)

        source_count = 0
        for entry in feed.entries:
            if len(results) >= limit or source_count >= per_source_limit:
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
                    "source": name,
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
            source_count += 1

    return results
