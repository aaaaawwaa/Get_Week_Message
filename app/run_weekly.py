from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import logging

from .config import (
    BILIBILI_LIMIT,
    CURRENT_AFFAIRS_LIMIT,
    CURRENT_AFFAIRS_SOURCES,
    WEIBO_LIMIT,
    ensure_dirs,
)
from .ai_summary import generate_weekly_summary
from .cover_cache import cache_covers
from .fetchers.affairs import fetch_current_affairs
from .fetchers.bilibili import fetch_bilibili
from .fetchers.weibo import fetch_weibo
from .logging_utils import configure_logging
from .render import render_index, render_weekly
from .storage import get_items_for_week, get_week_summaries, init_db, upsert_items


_FETCH_JOBS = [
    ("bilibili", lambda: fetch_bilibili(BILIBILI_LIMIT)),
    ("weibo", lambda: fetch_weibo(WEIBO_LIMIT)),
]

if CURRENT_AFFAIRS_SOURCES:
    _FETCH_JOBS.append(("affairs", lambda: fetch_current_affairs(CURRENT_AFFAIRS_LIMIT)))


def _current_week_start() -> str:
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    return week_start.isoformat()


def main() -> None:
    ensure_dirs()
    configure_logging()
    logger = logging.getLogger("weekly")
    init_db()

    week_start = _current_week_start()
    items = []

    with ThreadPoolExecutor(max_workers=len(_FETCH_JOBS)) as executor:
        future_map = {
            executor.submit(job): name
            for name, job in _FETCH_JOBS
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result()
                items.extend(result)
                logger.info("fetch ok: %s: %s items", name, len(result))
            except Exception as exc:
                logger.warning("fetch failed: %s: %s", name, exc)

    cache_covers(items)
    if items:
        upsert_items(week_start, items)

    week_items = get_items_for_week(week_start)
    ai_summary, ai_status = generate_weekly_summary(week_start, week_items)
    render_weekly(week_start, week_items, ai_summary, ai_status)

    summaries = get_week_summaries()
    render_index(summaries)


if __name__ == "__main__":
    main()
