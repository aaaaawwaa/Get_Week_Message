from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import CRON_HOUR, CRON_MINUTE, CRON_WEEKDAY, TIMEZONE
from .run_weekly import main as run_weekly

_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        run_weekly,
        CronTrigger(day_of_week=CRON_WEEKDAY, hour=CRON_HOUR, minute=CRON_MINUTE),
        id="weekly_report",
        replace_existing=True,
        misfire_grace_time=3600,  # 错过 1 小时内仍执行
    )
    scheduler.start()
    _scheduler = scheduler
    return _scheduler


def get_next_run_time() -> str:
    """返回下次定时任务的执行时间字符串"""
    if _scheduler is None:
        return ""
    job = _scheduler.get_job("weekly_report")
    if job is None:
        return ""
    next_time = job.next_run_time
    if next_time is None:
        return ""
    return next_time.strftime("%Y-%m-%d %H:%M")
