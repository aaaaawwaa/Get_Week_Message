from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List, Tuple

import requests

from .config import AI_CONFIG_PATH, HTTP_BACKOFF, HTTP_RETRIES, HTTP_TIMEOUT, SOURCE_LABELS, SOURCE_ORDER

DEFAULT_AI_SETTINGS: Dict = {
    "enabled": False,
    "base_url": "",
    "api_key": "",
    "model": "",
    "max_tokens": 600,
    "max_items_per_source": 12,
}


def read_ai_config_file() -> Dict:
    settings = dict(DEFAULT_AI_SETTINGS)
    if AI_CONFIG_PATH.exists():
        try:
            data = json.loads(AI_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                settings.update({k: v for k, v in data.items() if v is not None})
        except (OSError, json.JSONDecodeError) as exc:
            logging.getLogger("weekly").warning("ai_config.json read failed: %s", exc)
    return settings


def save_ai_config_file(settings: Dict) -> None:
    payload = dict(DEFAULT_AI_SETTINGS)
    payload.update({k: v for k, v in settings.items() if v is not None})
    AI_CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _load_ai_settings() -> Dict:
    settings = read_ai_config_file()

    if os.getenv("AI_SUMMARY_ENABLED"):
        settings["enabled"] = os.getenv("AI_SUMMARY_ENABLED", "0") == "1"
    if os.getenv("AI_API_BASE_URL"):
        settings["base_url"] = os.getenv("AI_API_BASE_URL", "")
    if os.getenv("AI_API_KEY"):
        settings["api_key"] = os.getenv("AI_API_KEY", "")
    if os.getenv("AI_MODEL"):
        settings["model"] = os.getenv("AI_MODEL", "")

    return settings


def _build_prompt(items: List[Dict], max_items_per_source: int) -> str:
    grouped: Dict[str, List[Dict]] = {}
    for item in items:
        grouped.setdefault(item.get("source", "unknown"), []).append(item)

    lines: List[str] = [
        "Summarize the weekly news highlights based on the items below.",
        "Respond in Chinese using 5-8 bullet points.",
        "Be concise, factual, and avoid speculation.",
        "",
    ]

    for source in SOURCE_ORDER:
        if source not in grouped:
            continue
        label = SOURCE_LABELS.get(source, source)
        lines.append(f"{label}:")
        for item in grouped[source][:max_items_per_source]:
            title = item.get("title", "")
            author = item.get("author", "")
            if author:
                lines.append(f"- {title} ({author})")
            else:
                lines.append(f"- {title}")
        lines.append("")

    for source, entries in grouped.items():
        if source in SOURCE_ORDER:
            continue
        label = SOURCE_LABELS.get(source, source)
        lines.append(f"{label}:")
        for item in entries[:max_items_per_source]:
            title = item.get("title", "")
            author = item.get("author", "")
            if author:
                lines.append(f"- {title} ({author})")
            else:
                lines.append(f"- {title}")
        lines.append("")

    return "\n".join(lines)


def _post_chat_completion(settings: Dict, prompt: str) -> Tuple[str, Dict]:
    logger = logging.getLogger("weekly")
    base_url = str(settings.get("base_url", "")).rstrip("/")
    api_key = settings.get("api_key", "")
    model = settings.get("model", "") or "gpt-4o-mini"
    max_tokens = int(settings.get("max_tokens", 600))

    endpoint = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful news summarizer."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    info: Dict = {}
    start = time.monotonic()
    logger.info(
        "ai summary: prompt length=%s chars, model=%s, max_tokens=%s",
        len(prompt),
        model,
        max_tokens,
    )

    last_exc: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
            # 4xx 错误（如无效 API Key）不重试，立即返回
            if 400 <= response.status_code < 500:
                logger.warning(
                    "ai summary rejected (status=%s): %s", response.status_code, response.text[:200]
                )
                return "", info
            response.raise_for_status()
            data = response.json()
            elapsed = time.monotonic() - start
            usage = data.get("usage", {}) or {}
            info = {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "elapsed_s": round(elapsed, 2),
                "model": model,
            }
            logger.info(
                "ai summary success: elapsed=%.2fs, prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
                elapsed,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                return str(content).strip(), info
            return "", info
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning("ai summary failed (attempt %s/%s): %s", attempt + 1, HTTP_RETRIES, exc)
            if attempt < HTTP_RETRIES - 1:
                time.sleep(HTTP_BACKOFF * (2**attempt))

    if last_exc:
        raise last_exc
    return "", info


def generate_weekly_summary(week_start: str, items: List[Dict]) -> Tuple[str, str]:
    settings = _load_ai_settings()
    if not settings.get("enabled"):
        return "", "disabled"
    if not settings.get("base_url") or not settings.get("api_key"):
        return "", "disabled"
    if not items:
        return "", "empty"

    prompt = _build_prompt(items, int(settings.get("max_items_per_source", 12)))
    try:
        summary, info = _post_chat_completion(settings, prompt)
        if not summary:
            return "", "error"
        return summary, "ok"
    except Exception as exc:
        return "", "error"


def test_ai_connection(settings: Dict) -> Tuple[bool, str]:
    if not settings.get("base_url") or not settings.get("api_key"):
        return False, "missing base_url or api_key"

    prompt = "Reply with OK."
    try:
        result, info = _post_chat_completion(settings, prompt)
        if not result:
            return False, "empty response"
        return True, result[:200]
    except Exception as exc:
        return False, str(exc)
