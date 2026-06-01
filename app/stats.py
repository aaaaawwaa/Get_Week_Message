# -*- coding: utf-8 -*-
"""系统统计与数据分析接口"""

import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from .config import DB_PATH, DB_MAX_SIZE, LOG_FILE, LOG_DIR, REPORTS_DIR, STATIC_DIR


def get_system_stats() -> Dict:
    """系统健康与资源统计"""
    now = datetime.now()

    # 数据库大小
    db_size = 0
    if DB_PATH.exists():
        db_size = DB_PATH.stat().st_size
    db_size_str = _format_size(db_size)
    db_max_str = _format_size(DB_MAX_SIZE)
    db_usage_percent = round((db_size / DB_MAX_SIZE) * 100, 1) if DB_MAX_SIZE > 0 else 0

    # 日志大小
    log_size = 0
    if LOG_DIR.exists():
        log_size = sum(
            f.stat().st_size for f in LOG_DIR.glob("*") if f.is_file()
        )
    log_size_str = _format_size(log_size)

    # 报告文件
    report_files = list(REPORTS_DIR.glob("*.html")) if REPORTS_DIR.exists() else []
    report_count = len(report_files)
    report_total_size = sum(f.stat().st_size for f in report_files)
    report_size_str = _format_size(report_total_size)

    # 封面文件
    covers_dir = REPORTS_DIR / "covers"
    cover_count = len(list(covers_dir.glob("*"))) if covers_dir.exists() else 0

    # 最新报告
    latest_report = ""
    if report_files:
        dates = []
        for f in report_files:
            if f.stem not in ("latest", "index"):
                dates.append(f.stem)
        if dates:
            dates.sort(reverse=True)
            latest_report = dates[0]

    # 容器运行时间（通过 /proc/uptime 或环境变量，仅在 Docker 中有意义）
    uptime_str = ""
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.read().split()[0])
            uptime_str = _format_duration(int(uptime_seconds))
    except (OSError, IndexError, ValueError):
        uptime_str = "N/A"

    return {
        "db_size": db_size,
        "db_size_str": db_size_str,
        "db_max_size": DB_MAX_SIZE,
        "db_max_str": db_max_str,
        "db_usage_percent": db_usage_percent,
        "log_size": log_size,
        "log_size_str": log_size_str,
        "report_count": report_count,
        "report_size_str": report_size_str,
        "cover_count": cover_count,
        "latest_report": latest_report,
        "uptime": uptime_str,
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_source_stats() -> List[Dict]:
    """从日志解析各数据源的抓取历史"""
    if not LOG_FILE.exists():
        return []

    max_read_bytes = 500 * 1024
    file_size = LOG_FILE.stat().st_size
    with LOG_FILE.open("rb") as fh:
        if file_size > max_read_bytes:
            fh.seek(file_size - max_read_bytes)
            leftover = fh.readline()
            raw = (leftover + fh.read()).decode("utf-8", errors="replace")
        else:
            raw = fh.read().decode("utf-8", errors="replace")

    source_stats: Dict[str, Dict] = {}
    for line in raw.splitlines():
        m = re.search(
            r"^(\d{4}-\d{2}-\d{2})\s+.*fetch ok:\s*(\w+):\s*(\d+)\s*items", line
        )
        if m:
            day = m.group(1)
            source = m.group(2)
            count = int(m.group(3))
            key = f"{day}:{source}"
            if key not in source_stats:
                source_stats[key] = {
                    "date": day,
                    "source": source,
                    "count": count,
                }
            else:
                source_stats[key]["count"] += count

    return sorted(source_stats.values(), key=lambda x: (x["date"], x["source"]), reverse=True)


def get_weekly_trend() -> List[Dict]:
    """从日志分析每周抓取趋势"""
    from .storage import get_week_summaries

    weeks = []
    try:
        raw = get_week_summaries()
        weeks = [
            {"week_start": r["week_start"], "total": r["total"]}
            for r in raw
        ]
    except Exception:
        pass
    return weeks


def get_fetch_summary() -> Dict:
    """抓取汇总统计（从数据库 + 最近日志）"""
    from .storage import get_week_summaries

    weeks = []
    total_all = 0
    try:
        raw = get_week_summaries()
        weeks = [{"week_start": r["week_start"], "total": r["total"]} for r in raw]
        total_all = sum(r["total"] for r in raw)
    except Exception:
        pass

    # 从日志统计各源总抓取次数
    source_counts: Dict[str, int] = {}
    if LOG_FILE.exists():
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r"fetch ok:\s*(\w+):\s*(\d+)\s*items", line)
                if m:
                    src = m.group(1)
                    cnt = int(m.group(2))
                    source_counts[src] = source_counts.get(src, 0) + cnt

    return {
        "total_items": total_all,
        "total_weeks": len(weeks),
        "source_breakdown": source_counts,
        "weeks": weeks,
    }


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_duration(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    mins = (seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"
