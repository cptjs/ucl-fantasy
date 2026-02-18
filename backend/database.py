"""
Database layer - SQLite for MVP.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "/app/data/fantasy.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db_session() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uefa_id TEXT UNIQUE,
            name TEXT NOT NULL,
            club TEXT NOT NULL,
            club_code TEXT,
            position TEXT NOT NULL CHECK(position IN ('GK','DEF','MID','FWD')),
            price REAL NOT NULL DEFAULT 0,
            is_starter INTEGER DEFAULT 1,
            is_set_piece_taker INTEGER DEFAULT 0,
            injury_status TEXT DEFAULT 'fit',
            total_points INTEGER DEFAULT 0,
            avg_points REAL DEFAULT 0,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            clean_sheets INTEGER DEFAULT 0,
            minutes_played INTEGER DEFAULT 0,
            balls_recovered INTEGER DEFAULT 0,
            selection_pct REAL DEFAULT 0,
            form_rating REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS matchdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'league_phase',
            deadline TEXT,
            is_active INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matchday_id INTEGER REFERENCES matchdays(id),
            home_club TEXT NOT NULL,
            home_code TEXT,
            away_club TEXT NOT NULL,
            away_code TEXT,
            home_strength REAL DEFAULT 0.5,
            away_strength REAL DEFAULT 0.5,
            match_date TEXT,
            kick_off TEXT,
            status TEXT DEFAULT 'scheduled',
            home_score INTEGER,
            away_score INTEGER,
            result TEXT
        );

        CREATE TABLE IF NOT EXISTS match_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER REFERENCES players(id),
            matchday_id INTEGER REFERENCES matchdays(id),
            fixture_id INTEGER REFERENCES fixtures(id),
            minutes INTEGER DEFAULT 0,
            goals INTEGER DEFAULT 0,
            goals_outside_box INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            balls_recovered INTEGER DEFAULT 0,
            player_of_match INTEGER DEFAULT 0,
            penalty_won INTEGER DEFAULT 0,
            penalty_conceded INTEGER DEFAULT 0,
            penalty_missed INTEGER DEFAULT 0,
            penalty_saved INTEGER DEFAULT 0,
            yellow_card INTEGER DEFAULT 0,
            red_card INTEGER DEFAULT 0,
            own_goal INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            goals_conceded INTEGER DEFAULT 0,
            clean_sheet INTEGER DEFAULT 0,
            fantasy_points INTEGER DEFAULT 0,
            UNIQUE(player_id, matchday_id)
        );

        CREATE TABLE IF NOT EXISTS squads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matchday_id INTEGER REFERENCES matchdays(id),
            profile TEXT DEFAULT 'balanced',
            squad_json TEXT,
            total_expected REAL,
            total_cost REAL,
            actual_points INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Migration: add columns if missing (for existing DBs)
        try:
            conn.execute("ALTER TABLE fixtures ADD COLUMN kick_off TEXT")
        except:
            pass
        try:
            conn.execute("ALTER TABLE fixtures ADD COLUMN status TEXT DEFAULT 'scheduled'")
        except:
            pass
        try:
            conn.execute("ALTER TABLE fixtures ADD COLUMN home_score INTEGER")
        except:
            pass
        try:
            conn.execute("ALTER TABLE fixtures ADD COLUMN away_score INTEGER")
        except:
            pass
