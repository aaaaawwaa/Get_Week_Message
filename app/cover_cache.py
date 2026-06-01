import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Iterable
from urllib.parse import urlparse

from .config import (
    COVER_CACHE_MAX_DAYS,
    COVER_CACHE_MAX_FILES,
    COVERS_DIR,
    HTTP_BACKOFF,
    HTTP_JITTER,
    HTTP_MIN_INTERVAL,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from .http_client import download_file


def _normalize_url(url: str) -> str:
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def _guess_suffix(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix
    if not suffix or len(suffix) > 5:
        return ".jpg"
    return suffix


def _cleanup_cover_cache(logger: logging.Logger) -> None:
    if not COVERS_DIR.exists():
        return

    now = time.time()
    if COVER_CACHE_MAX_DAYS > 0:
        cutoff = now - (COVER_CACHE_MAX_DAYS * 86400)
        for path in COVERS_DIR.glob("*"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                logger.warning("failed to remove old cover: %s", path)

    if COVER_CACHE_MAX_FILES > 0:
        files = [p for p in COVERS_DIR.glob("*") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[COVER_CACHE_MAX_FILES:]:
            try:
                path.unlink()
            except OSError:
                logger.warning("failed to remove extra cover: %s", path)


def cache_covers(items: Iterable[Dict]) -> None:
    logger = logging.getLogger("weekly")
    for item in items:
        cover_url = item.get("cover_url", "") or ""
        if not cover_url:
            continue
        if cover_url.startswith("covers/"):
            continue

        normalized = _normalize_url(cover_url)
        suffix = _guess_suffix(normalized)
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        file_name = f"{digest}{suffix}"
        target_path = COVERS_DIR / file_name

        if not target_path.exists():
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": "https://www.bilibili.com/",
            }
            try:
                download_file(
                    normalized,
                    target_path,
                    headers=headers,
                    timeout=HTTP_TIMEOUT,
                    retries=HTTP_RETRIES,
                    backoff=HTTP_BACKOFF,
                    min_interval=HTTP_MIN_INTERVAL,
                    jitter=HTTP_JITTER,
                )
            except Exception:
                logger.warning("cover download failed: %s", normalized)
                continue

        item["cover_url"] = f"/reports/covers/{file_name}"

    _cleanup_cover_cache(logger)
