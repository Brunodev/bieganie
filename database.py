"""
SQLite database — aktywności biegowe, VDOT historia, sync log.
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get('DB_PATH', '/data/bieganie/bieganie.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Utwórz tabele jeśli nie istnieją."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garmin_id TEXT UNIQUE,
            source TEXT DEFAULT 'garmin',
            date TEXT NOT NULL,
            name TEXT,
            activity_type TEXT,
            distance_m REAL DEFAULT 0,
            duration_s REAL DEFAULT 0,
            moving_duration_s REAL DEFAULT 0,
            pace_s_per_km REAL,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence REAL,
            avg_stride_length REAL,
            elevation_gain REAL,
            elevation_loss REAL,
            calories REAL,
            vo2max_garmin REAL,
            vdot REAL,
            training_effect REAL,
            avg_temperature REAL,
            notes TEXT,
            screenshot TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS manual_entries (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            distance TEXT,
            time TEXT,
            pace TEXT,
            type TEXT,
            notes TEXT,
            screenshot TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT DEFAULT 'running',
            activities_synced INTEGER DEFAULT 0,
            error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);
        CREATE INDEX IF NOT EXISTS idx_activities_garmin_id ON activities(garmin_id);
        CREATE INDEX IF NOT EXISTS idx_activities_vdot ON activities(vdot);
    """)
    conn.commit()
    conn.close()


# ── Activities ──

def upsert_activity(data: dict) -> bool:
    """Wstaw lub zaktualizuj aktywność. Zwraca True jeśli nowa."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM activities WHERE garmin_id = ?",
        (data.get('garmin_id'),)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE activities SET
                date=?, name=?, activity_type=?, distance_m=?, duration_s=?,
                moving_duration_s=?, pace_s_per_km=?, avg_hr=?, max_hr=?,
                avg_cadence=?, avg_stride_length=?, elevation_gain=?, elevation_loss=?,
                calories=?, vo2max_garmin=?, vdot=?, training_effect=?,
                avg_temperature=?, raw_json=?, updated_at=datetime('now')
            WHERE garmin_id=?
        """, (
            data.get('date'), data.get('name'), data.get('activity_type'),
            data.get('distance_m'), data.get('duration_s'),
            data.get('moving_duration_s'), data.get('pace_s_per_km'),
            data.get('avg_hr'), data.get('max_hr'),
            data.get('avg_cadence'), data.get('avg_stride_length'),
            data.get('elevation_gain'), data.get('elevation_loss'),
            data.get('calories'), data.get('vo2max_garmin'),
            data.get('vdot'), data.get('training_effect'),
            data.get('avg_temperature'), data.get('raw_json'),
            data.get('garmin_id')
        ))
        conn.commit()
        conn.close()
        return False

    conn.execute("""
        INSERT INTO activities (
            garmin_id, source, date, name, activity_type, distance_m, duration_s,
            moving_duration_s, pace_s_per_km, avg_hr, max_hr,
            avg_cadence, avg_stride_length, elevation_gain, elevation_loss,
            calories, vo2max_garmin, vdot, training_effect, avg_temperature, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('garmin_id'), data.get('source', 'garmin'),
        data.get('date'), data.get('name'), data.get('activity_type'),
        data.get('distance_m'), data.get('duration_s'),
        data.get('moving_duration_s'), data.get('pace_s_per_km'),
        data.get('avg_hr'), data.get('max_hr'),
        data.get('avg_cadence'), data.get('avg_stride_length'),
        data.get('elevation_gain'), data.get('elevation_loss'),
        data.get('calories'), data.get('vo2max_garmin'),
        data.get('vdot'), data.get('training_effect'),
        data.get('avg_temperature'), data.get('raw_json')
    ))
    conn.commit()
    conn.close()
    return True


def get_activities(limit=200, offset=0):
    """Pobierz aktywności posortowane od najnowszej."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activities ORDER BY date DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_activity_count():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    conn.close()
    return count


def get_vdot_history():
    """Pobierz historię VDOT (tylko biegi z obliczonym VDOT, ≥2km)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT date, vdot, distance_m, duration_s, name
        FROM activities
        WHERE vdot IS NOT NULL AND distance_m >= 2000
        ORDER BY date ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_weekly_stats(weeks=12):
    """Statystyki tygodniowe (objętość, średnie tempo, VDOT)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            strftime('%Y-W%W', date) as week,
            COUNT(*) as runs,
            ROUND(SUM(distance_m) / 1000, 1) as total_km,
            ROUND(SUM(duration_s) / 60, 0) as total_min,
            ROUND(AVG(pace_s_per_km), 0) as avg_pace_s,
            ROUND(AVG(avg_hr), 0) as avg_hr,
            ROUND(MAX(vdot), 1) as best_vdot,
            ROUND(AVG(vdot), 1) as avg_vdot
        FROM activities
        WHERE date >= date('now', ? || ' days')
        GROUP BY week
        ORDER BY week DESC
    """, (str(-weeks * 7),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary_stats():
    """Statystyki ogólne."""
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_runs,
            ROUND(SUM(distance_m) / 1000, 1) as total_km,
            ROUND(SUM(duration_s) / 3600, 1) as total_hours,
            ROUND(AVG(distance_m) / 1000, 1) as avg_distance_km,
            ROUND(AVG(pace_s_per_km), 0) as avg_pace_s,
            ROUND(AVG(avg_hr), 0) as avg_hr,
            MAX(vdot) as best_vdot,
            ROUND(AVG(CASE WHEN vdot IS NOT NULL THEN vdot END), 1) as avg_vdot,
            MAX(date) as last_run,
            MIN(date) as first_run
        FROM activities
    """).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_hr_zone_distribution(hrmax=191):
    """Rozkład tętna w strefach (na podstawie średniego HR aktywności)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT avg_hr, duration_s FROM activities WHERE avg_hr IS NOT NULL
    """).fetchall()
    conn.close()

    zones = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for row in rows:
        hr = row['avg_hr']
        dur = row['duration_s'] or 0
        pct = hr / hrmax * 100
        if pct < 60:
            zones[1] += dur
        elif pct < 75:
            zones[2] += dur
        elif pct < 82:
            zones[3] += dur
        elif pct < 90:
            zones[4] += dur
        else:
            zones[5] += dur

    total = sum(zones.values())
    if total == 0:
        return zones
    return {k: round(v / total * 100, 1) for k, v in zones.items()}


# ── Manual entries (legacy) ──

def save_manual_entry(entry: dict):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO manual_entries (id, date, distance, time, pace, type, notes, screenshot, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry['id'], entry['date'], entry.get('distance'), entry.get('time'),
        entry.get('pace'), entry.get('type'), entry.get('notes'),
        entry.get('screenshot'), entry.get('created', datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()


def get_manual_entries():
    conn = get_db()
    rows = conn.execute("SELECT * FROM manual_entries ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_manual_entry(entry_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM manual_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ── Sync log ──

def log_sync_start():
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sync_log (started_at) VALUES (?)",
        (datetime.now().isoformat(),)
    )
    sync_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sync_id


def log_sync_finish(sync_id: int, count: int, error: str = None):
    conn = get_db()
    conn.execute("""
        UPDATE sync_log SET finished_at=?, status=?, activities_synced=?, error=?
        WHERE id=?
    """, (
        datetime.now().isoformat(),
        'error' if error else 'done',
        count,
        error,
        sync_id
    ))
    conn.commit()
    conn.close()


def get_last_sync():
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# Initialize on import
init_db()
