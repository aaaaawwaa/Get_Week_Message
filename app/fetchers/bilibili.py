import json
from datetime import datetime
from typing import Dict, List

from ..config import (
    HTTP_BACKOFF,
    HTTP_JITTER,
    HTTP_MIN_INTERVAL,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from ..http_client import request_json


def fetch_bilibili(limit: int = 30, timeout: int = 10) -> List[Dict]:
    url = "https://api.bilibili.com/x/web-interface/popular"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    payload = request_json(
        url,
        params={"ps": limit, "pn": 1},
        headers=headers,
        timeout=timeout,
        retries=HTTP_RETRIES,
        backoff=HTTP_BACKOFF,
        min_interval=HTTP_MIN_INTERVAL,
        jitter=HTTP_JITTER,
    )

    data = payload.get("data", {})
    items = data.get("list", []) or []

    results: List[Dict] = []
    for idx, item in enumerate(items, start=1):
        title = item.get("title")
        if not title:
            continue

        bvid = item.get("bvid", "")
        link = item.get("short_link_v2") or item.get("short_link")
        if not link and bvid:
            link = f"https://www.bilibili.com/video/{bvid}"
        if not link:
            continue

        owner = item.get("owner", {}) or {}
        stat = item.get("stat", {}) or {}
        view = stat.get("view")
        metric = f"views {view}" if view is not None else ""

        published_at = ""
        pubdate = item.get("pubdate")
        if pubdate:
            published_at = datetime.fromtimestamp(pubdate).isoformat(timespec="seconds")

        cover_url = item.get("pic", "")
        if cover_url.startswith("http://"):
            cover_url = "https://" + cover_url[len("http://"):]

        results.append(
            {
                "source": "bilibili",
                "title": title,
                "url": link or "",
                "author": owner.get("name", ""),
                "metric": metric,
                "cover_url": cover_url,
                "published_at": published_at,
                "rank": idx,
                "raw_json": json.dumps(item, ensure_ascii=True),
            }
        )

    return results
