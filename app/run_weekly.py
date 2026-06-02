from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import logging
import threading
import time

from . import config as _cfg
from .config import ensure_dirs
from .data_config import apply_data_config_to_module
from .ai_summary import generate_weekly_summary, translate_github_descriptions
from .cover_cache import cache_covers
from .fetchers.affairs import fetch_current_affairs
from .fetchers.bilibili import fetch_bilibili
from .fetchers.github import fetch_github_trending
from .fetchers.weibo import fetch_weibo
from .logging_utils import configure_logging
from .render import render_index, render_weekly
from .storage import get_items_for_week, get_week_summaries, init_db, upsert_items, delete_stale_sources, delete_old_weeks


def _build_fetch_jobs():
    """在 main() 内部调用，确保 apply_data_config_to_module 已生效"""
    jobs = [
        ("bilibili", lambda: fetch_bilibili(_cfg.BILIBILI_LIMIT)),
        ("weibo", lambda: fetch_weibo(_cfg.WEIBO_LIMIT)),
        ("github", lambda: fetch_github_trending(_cfg.GITHUB_LIMIT)),
    ]
    if _cfg.CURRENT_AFFAIRS_SOURCES:
        jobs.append(("affairs", lambda: fetch_current_affairs(_cfg.CURRENT_AFFAIRS_LIMIT)))
    return jobs


_progress_lock = threading.Lock()
_run_lock = threading.Lock()  # 防止同一时间多个 main() 并发执行
_progress_state = {
    "status": "idle",
    "completed": 0,
    "total": 0,
    "message": "",
    "started_at": "",
    "updated_at": "",
    "finished_at": "",
    "sources": {},
}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _set_run_message(message: str) -> None:
    with _progress_lock:
        _progress_state["message"] = message
        _progress_state["updated_at"] = _now_str()


def _start_run_progress(source_names):
    with _progress_lock:
        _progress_state.update(
            {
                "status": "running",
                "completed": 0,
                "total": len(source_names),
                "message": "fetching",
                "started_at": _now_str(),
                "updated_at": _now_str(),
                "finished_at": "",
                "sources": {
                    name: {"status": "pending", "items": 0}
                    for name in source_names
                },
            }
        )


def _update_run_source(name: str, status: str, items: int = 0, error: str = "", elapsed: float = 0) -> None:
    with _progress_lock:
        source = _progress_state.setdefault("sources", {}).setdefault(
            name, {"status": "pending", "items": 0, "error": "", "elapsed": 0}
        )
        source["status"] = status
        if items:
            source["items"] = items
        if error:
            source["error"] = error
        if elapsed:
            source["elapsed"] = round(elapsed, 2)
        _progress_state["updated_at"] = _now_str()


def _advance_run_progress() -> None:
    with _progress_lock:
        total = _progress_state.get("total", 0) or 0
        completed = _progress_state.get("completed", 0) or 0
        _progress_state["completed"] = min(total, completed + 1)
        _progress_state["updated_at"] = _now_str()


def _finish_run_progress(status: str, message: str) -> None:
    with _progress_lock:
        total = _progress_state.get("total", 0) or 0
        now = _now_str()
        started = _progress_state.get("started_at", "")
        total_elapsed = 0.0
        if started:
            try:
                t0 = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
                total_elapsed = round((datetime.now() - t0).total_seconds(), 1)
            except ValueError:
                pass
        _progress_state.update(
            {
                "status": status,
                "completed": total,
                "message": message,
                "updated_at": now,
                "finished_at": now,
                "total_elapsed": total_elapsed,
            }
        )


def get_run_progress():
    with _progress_lock:
        total = _progress_state.get("total", 0) or 0
        completed = _progress_state.get("completed", 0) or 0
        percent = int(round((completed / total) * 100)) if total else 0
        if _progress_state.get("status") in {"done", "error"}:
            percent = 100
        return {
            "status": _progress_state.get("status", "idle"),
            "completed": completed,
            "total": total,
            "percent": percent,
            "message": _progress_state.get("message", ""),
            "started_at": _progress_state.get("started_at", ""),
            "updated_at": _progress_state.get("updated_at", ""),
            "finished_at": _progress_state.get("finished_at", ""),
            "total_elapsed": _progress_state.get("total_elapsed", 0),
            "sources": {
                name: {
                    k: v for k, v in info.items()
                    if k in ("status", "items", "error", "elapsed")
                }
                for name, info in (_progress_state.get("sources") or {}).items()
            },
        }


def _current_week_start() -> str:
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    return week_start.isoformat()


def main() -> None:
    # 防止并发运行
    if not _run_lock.acquire(blocking=False):
        logger = logging.getLogger("weekly")
        logger.warning("run_weekly already in progress, skipping concurrent run")
        return
    try:
        ensure_dirs()
        configure_logging()
        apply_data_config_to_module()
        logger = logging.getLogger("weekly")
        init_db()

        week_start = _current_week_start()
        items = []
        fetch_jobs = _build_fetch_jobs()
        _start_run_progress([name for name, _ in fetch_jobs])
        try:
            with ThreadPoolExecutor(max_workers=len(fetch_jobs)) as executor:
                # 记录每个 future 的提交时间，用于计算真实耗时
                job_start: dict = {}
                future_map: dict = {}
                for name, job in fetch_jobs:
                    t0 = time.monotonic()
                    fut = executor.submit(job)
                    future_map[fut] = name
                    job_start[fut] = t0
                for future in as_completed(future_map):
                    name = future_map[future]
                    elapsed = round(time.monotonic() - job_start.get(future, 0), 2)
                    try:
                        result = future.result()
                        # 过滤出有效条目和错误标记
                        valid = [r for r in result if not r.get("_error")]
                        errors = [r for r in result if r.get("_error")]
                        items.extend(valid)
                        logger.info("fetch ok: %s: %s items (%.1fs)", name, len(valid), elapsed)
                        _update_run_source(name, "done", len(valid), elapsed=elapsed)
                        if errors:
                            err_detail = "; ".join(
                                f"{e['source']}: {e['_error']}" for e in errors
                            )
                            logger.warning("fetch partial failures for %s: %s", name, err_detail)
                            _update_run_source(name, "done", len(valid), error=err_detail, elapsed=elapsed)
                    except Exception as exc:
                        logger.warning("fetch failed: %s: %s (%.1fs)", name, exc, elapsed)
                        _update_run_source(name, "error", 0, error=str(exc), elapsed=elapsed)
                    finally:
                        _advance_run_progress()

            # GitHub 项目描述翻译（AI 可选）
            _set_run_message("translating")
            translated = translate_github_descriptions(items)
            if translated:
                logger.info("translated %s github descriptions", translated)

            _set_run_message("rendering")
            cache_covers(items)
            # 清理已被移除的数据源条目
            active_sources = {"bilibili", "weibo", "github"}
            for it in items:
                src = it.get("source", "")
                if src:
                    active_sources.add(src)
            cleaned = delete_stale_sources(week_start, sorted(active_sources))
            if cleaned:
                logger.info("cleaned %s stale source items for %s", cleaned, week_start)
            if items:
                upsert_items(week_start, items)

            week_items = get_items_for_week(week_start)
            ai_summary, ai_status = generate_weekly_summary(week_start, week_items)
            render_weekly(week_start, week_items, ai_summary, ai_status)

            summaries = get_week_summaries()
            render_index(summaries)

            # 清理超过 12 周的旧数据
            cleaned_old = delete_old_weeks(keep_weeks=12)
            if cleaned_old:
                logger.info("cleaned %s old items (kept last 12 weeks)", cleaned_old)

            _finish_run_progress("done", "done")
            logger.info("weekly report generated successfully for %s", week_start)
        except Exception:
            _finish_run_progress("error", "error")
            raise
    finally:
        _run_lock.release()


if __name__ == "__main__":
    main()
