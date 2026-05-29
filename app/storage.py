import sqlite3
from typing import Iterable, List, Dict

from .config import DB_PATH


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT source, title, url, author, metric, cover_url, published_at, rank
        FROM items
        WHERE week_start = ?
        ORDER BY source ASC, rank ASC
        """,
        (week_start,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_week_summaries() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
