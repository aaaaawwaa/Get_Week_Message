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
    )
    scheduler.start()
    _scheduler = scheduler
    return _scheduler
