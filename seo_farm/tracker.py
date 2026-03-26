"""
SQLite tracker for the SEO farm.
Prevents duplicate articles and tracks publishing history.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "seo_farm.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword       TEXT NOT NULL,
            country       TEXT NOT NULL,
            slug          TEXT NOT NULL UNIQUE,
            title         TEXT NOT NULL,
            wp_post_id    INTEGER,
            wp_url        TEXT,
            status        TEXT DEFAULT 'draft',
            published_at  TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keyword_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword     TEXT NOT NULL,
            country     TEXT NOT NULL,
            source      TEXT,
            priority    INTEGER DEFAULT 5,
            used        INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(keyword, country)
        )
    """)
    conn.commit()
    conn.close()


def is_published(keyword: str, country: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM articles WHERE keyword = ? AND country = ?",
        (keyword, country)
    ).fetchone()
    conn.close()
    return row is not None


def record_article(keyword: str, country: str, slug: str, title: str,
                   wp_post_id: int = None, wp_url: str = None, status: str = "draft"):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO articles (keyword, country, slug, title, wp_post_id, wp_url, status, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (keyword, country, slug, title, wp_post_id, wp_url, status))
    conn.commit()
    conn.close()


def add_keywords(keywords: list[dict]):
    """Add keyword dicts with keys: keyword, country, source, priority."""
    conn = get_conn()
    for kw in keywords:
        conn.execute("""
            INSERT OR IGNORE INTO keyword_queue (keyword, country, source, priority)
            VALUES (:keyword, :country, :source, :priority)
        """, kw)
    conn.commit()
    conn.close()


def get_next_keywords(limit: int = 5) -> list[dict]:
    """Return unused keywords ordered by priority (lower = higher priority)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT kq.keyword, kq.country, kq.source
        FROM keyword_queue kq
        LEFT JOIN articles a ON kq.keyword = a.keyword AND kq.country = a.country
        WHERE kq.used = 0 AND a.id IS NULL
        ORDER BY kq.priority ASC, kq.created_at ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_keyword_used(keyword: str, country: str):
    conn = get_conn()
    conn.execute(
        "UPDATE keyword_queue SET used = 1 WHERE keyword = ? AND country = ?",
        (keyword, country)
    )
    conn.commit()
    conn.close()


def get_published_count() -> int:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()
    return count
