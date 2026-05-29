# -*- coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "weekly.db"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
REPORTS_DIR = STATIC_DIR / "reports"
COVERS_DIR = REPORTS_DIR / "covers"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "weekly.log"
AI_CONFIG_PATH = BASE_DIR / "ai_config.json"

SOURCE_LABELS = {
    "bilibili": "Bilibili 热门",
    "weibo": "微博热搜",
    "affairs": "时事热点",
}

SOURCE_ORDER = ["bilibili", "weibo", "affairs"]

TIMEZONE = "Asia/Shanghai"
CRON_WEEKDAY = "sun"
CRON_HOUR = 8
CRON_MINUTE = 0

BILIBILI_LIMIT = 30
WEIBO_LIMIT = 30
CURRENT_AFFAIRS_LIMIT = 20

CURRENT_AFFAIRS_SOURCES = [
    {"name": "人民日报-时政", "url": "http://www.people.com.cn/rss/politics.xml"},
    {"name": "人民日报-社会", "url": "http://www.people.com.cn/rss/society.xml"},
    {"name": "人民日报-国际", "url": "http://www.people.com.cn/rss/world.xml"},
]
CURRENT_AFFAIRS_KEYWORDS = [
    "时政",
    "政策",
    "国务院",
    "中央",
    "国家",
    "外交",
    "会议",
]

HTTP_TIMEOUT = 10
HTTP_RETRIES = 3
HTTP_BACKOFF = 0.6
HTTP_MIN_INTERVAL = 0.25
HTTP_JITTER = 0.15

COVER_CACHE_MAX_FILES = 300
COVER_CACHE_MAX_DAYS = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)


def ensure_dirs() -> None:
    (BASE_DIR / "db").mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
