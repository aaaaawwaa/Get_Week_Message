import sqlite3
from typing import Iterable, List, Dict

from .config import DB_PATH, DB_MAX_SIZE


_DB_TIMEOUT = 5.0  # seconds


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=_DB_TIMEOUT)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA cache_size = -20000;")
    # 设置数据库最大大小 2GB（每次连接都生效）
    page_size = conn.execute("PRAGMA page_size;").fetchone()[0]
    max_pages = DB_MAX_SIZE // page_size
    conn.execute(f"PRAGMA max_page_count = {max_pages};")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            author TEXT,
            metric TEXT,
            cover_url TEXT,
            published_at TEXT,
            rank INTEGER,
            raw_json TEXT,
            UNIQUE(week_start, source, url)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_week_source ON items(week_start, source)"
    )
    conn.commit()
    conn.close()


def upsert_items(week_start: str, items: Iterable[Dict]) -> int:
    conn = _get_conn()
    count = 0
    for item in items:
        before = conn.total_changes
        conn.execute(
            """
            INSERT INTO items (
                week_start, source, title, url, author, metric, cover_url,
                published_at, rank, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, source, url) DO UPDATE SET
                title = excluded.title,
                author = excluded.author,
                metric = excluded.metric,
                cover_url = excluded.cover_url,
                published_at = excluded.published_at,
                rank = excluded.rank,
                raw_json = excluded.raw_json
            """,
            (
                week_start,
                item.get("source", ""),
                item.get("title", ""),
                item.get("url", ""),
                item.get("author", ""),
                item.get("metric", ""),
                item.get("cover_url", ""),
                item.get("published_at", ""),
                item.get("rank"),
                item.get("raw_json", ""),
            ),
        )
        count += conn.total_changes - before
    conn.commit()
    conn.close()
    return count


def get_items_for_week(week_start: str) -> List[Dict]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT source, title, url, author, metric, cover_url, published_at, rank, raw_json
        FROM items
        WHERE week_start = ?
        ORDER BY source ASC, rank ASC
        """,
        (week_start,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_week_summaries() -> List[Dict]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT week_start, COUNT(*) AS total
        FROM items
        GROUP BY week_start
        ORDER BY week_start DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_week_items(week_start: str, source: str = "") -> int:
    """删除指定周次的条目。若指定 source 则只删该源。"""
    conn = _get_conn()
    if source:
        conn.execute("DELETE FROM items WHERE week_start = ? AND source = ?", (week_start, source))
    else:
        conn.execute("DELETE FROM items WHERE week_start = ?", (week_start,))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected


def delete_stale_sources(week_start: str, active_sources: List[str]) -> int:
    """删除当前周中所有不在 active_sources 列表里的源的条目。"""
    if not active_sources:
        return 0
    conn = _get_conn()
    placeholders = ",".join("?" for _ in active_sources)
    sql = f"DELETE FROM items WHERE week_start = ? AND source NOT IN ({placeholders})"
    conn.execute(sql, [week_start] + list(active_sources))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected


def delete_old_weeks(keep_weeks: int = 12) -> int:
    """删除超过 keep_weeks 周的旧数据，防止数据库无限增长。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT DISTINCT week_start FROM items ORDER BY week_start DESC LIMIT ?",
        (keep_weeks + 1,),
    ).fetchall()
    if len(rows) <= keep_weeks:
        conn.close()
        return 0
    cutoff = rows[-1]["week_start"]
    conn.execute("DELETE FROM items WHERE week_start < ?", (cutoff,))
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return affected
