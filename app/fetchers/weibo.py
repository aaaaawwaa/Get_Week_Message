import json
from typing import Dict, List
from urllib.parse import quote

from ..config import (
    HTTP_BACKOFF,
    HTTP_JITTER,
    HTTP_MIN_INTERVAL,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from ..http_client import request_json


WEIBO_HOT_URL = "https://weibo.com/ajax/side/hotSearch"


def fetch_weibo(limit: int = 50, timeout: int = 10) -> List[Dict]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": "https://weibo.com/",
    }
    payload = request_json(
        WEIBO_HOT_URL,
        headers=headers,
        timeout=timeout,
        retries=HTTP_RETRIES,
        backoff=HTTP_BACKOFF,
        min_interval=HTTP_MIN_INTERVAL,
        jitter=HTTP_JITTER,
    )

    realtime = payload.get("data", {}).get("realtime", []) or []
    results: List[Dict] = []

    for idx, item in enumerate(realtime[:limit], start=1):
        if item.get("is_ad") == 1:
            continue

        word = item.get("word") or item.get("note") or ""
        if not word:
            continue

        link = item.get("link") or ""
        if link:
            if link.startswith("http"):
                url = link
            else:
                url = f"https://s.weibo.com{link}"
        else:
            url = "https://s.weibo.com/weibo?q=" + quote(word)

        metric = item.get("num")
        metric_text = f"hot {metric}" if metric is not None else ""

        results.append(
            {
                "source": "weibo",
                "title": word,
                "url": url,
                "author": "",
                "metric": metric_text,
                "cover_url": "",
                "published_at": "",
                "rank": item.get("rank", idx),
                "raw_json": json.dumps(item, ensure_ascii=True),
            }
        )

    return results
