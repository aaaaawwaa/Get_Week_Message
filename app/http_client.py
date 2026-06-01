import logging
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

_rate_lock = threading.Lock()
_last_request: Dict[str, float] = {}


def _rate_limit(url: str, min_interval: float, jitter: float) -> None:
    if min_interval <= 0:
        return
    host = urlparse(url).netloc
    if not host:
        return

    wait = 0.0
    now = time.monotonic()
    with _rate_lock:
        last = _last_request.get(host, 0.0)
        wait = min_interval - (now - last)
        if wait > 0:
            _last_request[host] = now + wait
        else:
            _last_request[host] = now

    if wait > 0:
        time.sleep(wait + random.uniform(0, max(0.0, jitter)))


def _is_client_error(exc: Exception) -> bool:
    """4xx 错误不应重试"""
    if isinstance(exc, requests.HTTPError):
        resp = getattr(exc, "response", None)
        if resp is not None and 400 <= resp.status_code < 500:
            return True
    return False


def request_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    retries: int = 3,
    backoff: float = 0.6,
    min_interval: float = 0.0,
    jitter: float = 0.0,
) -> Dict[str, Any]:
    logger = logging.getLogger("weekly")
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            _rate_limit(url, min_interval, jitter)
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "request_json failed (attempt %s/%s): %s",
                attempt + 1,
                retries,
                exc,
            )
            if _is_client_error(exc):
                raise
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))

    if last_exc:
        raise last_exc
    raise RuntimeError("request_json failed without exception")


def download_file(
    url: str,
    target_path: Path,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    retries: int = 3,
    backoff: float = 0.6,
    min_interval: float = 0.0,
    jitter: float = 0.0,
) -> None:
    logger = logging.getLogger("weekly")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + ".part")

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            _rate_limit(url, min_interval, jitter)
            with requests.get(url, headers=headers, timeout=timeout, stream=True) as resp:
                resp.raise_for_status()
                with tmp_path.open("wb") as handle:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            handle.write(chunk)
            tmp_path.replace(target_path)
            return
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "download_file failed (attempt %s/%s): %s",
                attempt + 1,
                retries,
                exc,
            )
            if _is_client_error(exc):
                if tmp_path.exists():
                    tmp_path.unlink()
                raise
            if tmp_path.exists():
                tmp_path.unlink()
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))

    if last_exc:
        raise last_exc
    raise RuntimeError("download_file failed without exception")


def request_bytes(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    retries: int = 3,
    backoff: float = 0.6,
    min_interval: float = 0.0,
    jitter: float = 0.0,
) -> bytes:
    logger = logging.getLogger("weekly")
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            _rate_limit(url, min_interval, jitter)
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "request_bytes failed (attempt %s/%s): %s",
                attempt + 1,
                retries,
                exc,
            )
            if _is_client_error(exc):
                raise
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))

    if last_exc:
        raise last_exc
    raise RuntimeError("request_bytes failed without exception")
