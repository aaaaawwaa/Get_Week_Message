from datetime import datetime, timedelta
import json
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

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def fetch_github_trending(limit: int = 10, timeout: int = 15) -> List[Dict]:
    """抓取 GitHub 近一周 stars 增长最快的仓库。"""
    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"created:>={seven_days_ago}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }
    payload = request_json(
        GITHUB_SEARCH_URL,
        params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
        headers=headers,
        timeout=timeout,
        retries=HTTP_RETRIES,
        backoff=HTTP_BACKOFF,
        min_interval=HTTP_MIN_INTERVAL,
        jitter=HTTP_JITTER,
    )

    results: List[Dict] = []
    for idx, repo in enumerate(payload.get("items", [])[:limit], start=1):
        name = repo.get("full_name", "")
        desc = repo.get("description") or ""
        stars = repo.get("stargazers_count", 0)
        language = repo.get("language") or ""
        html_url = repo.get("html_url", "")

        lang_str = f" [{language}]" if language else ""
        title = f"{name}{lang_str}"
        summary = desc[:200] if desc else ""

        results.append({
            "source": "github",
            "title": title,
            "url": html_url,
            "author": repo.get("owner", {}).get("login", ""),
            "metric": f"⭐ {stars}",
            "cover_url": repo.get("owner", {}).get("avatar_url", ""),
            "published_at": repo.get("created_at", ""),
            "rank": idx,
            "raw_json": json.dumps({"description": desc}, ensure_ascii=False) if desc else "",
        })

    return results
