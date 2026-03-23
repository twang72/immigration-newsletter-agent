"""
SQLite database layer.
The database file is committed back to the repo after each run,
giving us a permanent, growing dataset with zero hosting cost.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "immigration.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Express Entry draw history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ee_draws (
            draw_number     INTEGER PRIMARY KEY,
            draw_date       TEXT NOT NULL,
            draw_type       TEXT NOT NULL,   -- 'CRS' or category name (e.g. 'STEM', 'Healthcare')
            cutoff_score    INTEGER NOT NULL,
            invitations     INTEGER NOT NULL,
            tie_break_date  TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Processing time snapshots (crowdsourced/scraped over time)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processing_times (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT NOT NULL,
            application_type TEXT NOT NULL,  -- 'PR', 'Study Permit', 'Work Permit', etc.
            official_weeks  INTEGER,         -- IRCC's published estimate
            source_url      TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # PNP stream status tracker
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnp_streams (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT NOT NULL,
            province        TEXT NOT NULL,
            stream_name     TEXT NOT NULL,
            status          TEXT NOT NULL,   -- 'open', 'closed', 'paused'
            min_score       INTEGER,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"[db] Database initialized at {DB_PATH}")


def upsert_ee_draw(draw: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ee_draws (draw_number, draw_date, draw_type, cutoff_score, invitations, tie_break_date)
        VALUES (:draw_number, :draw_date, :draw_type, :cutoff_score, :invitations, :tie_break_date)
        ON CONFLICT(draw_number) DO UPDATE SET
            draw_date     = excluded.draw_date,
            draw_type     = excluded.draw_type,
            cutoff_score  = excluded.cutoff_score,
            invitations   = excluded.invitations,
            tie_break_date= excluded.tie_break_date
    """, draw)
    conn.commit()
    conn.close()


def get_recent_ee_draws(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ee_draws ORDER BY draw_date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ee_draws_by_type(draw_type: str, limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ee_draws WHERE draw_type = ? ORDER BY draw_date DESC LIMIT ?",
        (draw_type, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_draw_types() -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT draw_type FROM ee_draws ORDER BY draw_type"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
