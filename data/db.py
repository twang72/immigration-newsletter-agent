"""
SQLite database layer.
The database file is committed back to the repo after each run,
giving us a permanent, growing dataset with zero hosting cost.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "immigration.db")

# IRCC score band labels for dd1-dd18 fields
# Source: IRCC Express Entry rounds JSON
SCORE_BANDS = {
    "dd1":  "601-1200",
    "dd2":  "501-600",
    "dd3":  "491-500",
    "dd4":  "481-490",
    "dd5":  "471-480",
    "dd6":  "461-470",
    "dd7":  "451-460",
    "dd8":  "441-450",
    "dd9":  "431-440",
    "dd10": "421-430",
    "dd11": "411-420",
    "dd12": "401-410",
    "dd13": "391-400",
    "dd14": "381-390",
    "dd15": "371-380",
    "dd16": "361-370",
    "dd17": "351-360",
    "dd18": "301-350",
}


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
            draw_type       TEXT NOT NULL,
            cutoff_score    INTEGER NOT NULL,
            invitations     INTEGER NOT NULL,
            tie_break_date  TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Score band distribution per draw (dd1-dd18 from IRCC JSON)
    # Tells us how many candidates were in each CRS score band at draw time
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ee_score_bands (
            draw_number     INTEGER NOT NULL,
            score_band      TEXT NOT NULL,    -- e.g. '451-460'
            candidate_count INTEGER NOT NULL,
            PRIMARY KEY (draw_number, score_band),
            FOREIGN KEY (draw_number) REFERENCES ee_draws(draw_number)
        )
    """)

    # Processing time snapshots
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processing_times (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT NOT NULL,
            application_type TEXT NOT NULL,
            official_weeks  INTEGER,
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
            status          TEXT NOT NULL,
            min_score       INTEGER,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"[db] Database initialized at {DB_PATH}")


def upsert_ee_draw(draw: dict):
    """Upsert draw record and its score band distribution."""
    conn = get_conn()

    conn.execute("""
        INSERT INTO ee_draws (draw_number, draw_date, draw_type, cutoff_score, invitations, tie_break_date)
        VALUES (:draw_number, :draw_date, :draw_type, :cutoff_score, :invitations, :tie_break_date)
        ON CONFLICT(draw_number) DO UPDATE SET
            draw_date      = excluded.draw_date,
            draw_type      = excluded.draw_type,
            cutoff_score   = excluded.cutoff_score,
            invitations    = excluded.invitations,
            tie_break_date = excluded.tie_break_date
    """, draw)

    # Store score band distribution if present
    for dd_key, band_label in SCORE_BANDS.items():
        raw = draw.get(dd_key)
        if raw is None:
            continue
        try:
            count = int(str(raw).replace(",", "").strip())
        except ValueError:
            continue
        conn.execute("""
            INSERT INTO ee_score_bands (draw_number, score_band, candidate_count)
            VALUES (?, ?, ?)
            ON CONFLICT(draw_number, score_band) DO UPDATE SET
                candidate_count = excluded.candidate_count
        """, (draw["draw_number"], band_label, count))

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


def get_score_band_distribution(draw_number: int) -> dict:
    """Returns candidate counts per score band for a specific draw."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT score_band, candidate_count FROM ee_score_bands WHERE draw_number = ? ORDER BY score_band DESC",
        (draw_number,)
    ).fetchall()
    conn.close()
    return {r["score_band"]: r["candidate_count"] for r in rows}


def get_pool_size_trend(limit: int = 10) -> list[dict]:
    """Returns total pool size (sum of all bands) per draw — shows if pool is growing/shrinking."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.draw_number, d.draw_date, d.draw_type, d.cutoff_score,
               SUM(b.candidate_count) as total_pool
        FROM ee_draws d
        LEFT JOIN ee_score_bands b ON d.draw_number = b.draw_number
        GROUP BY d.draw_number
        ORDER BY d.draw_date DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
