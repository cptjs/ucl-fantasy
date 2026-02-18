"""
Import players and fixtures from raw UEFA Fantasy JSON.
Usage: python import_uefa.py <players_json_path>
"""

import json
import sys
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/fantasy.db")

SKILL_TO_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

STATUS_MAP = {
    "": "fit",
    "I": "doubt",       # Injured
    "D": "doubt",       # Doubtful
    "S": "out",         # Suspended
    "E": "out",         # Eliminated
    "NIS": "out",       # Not in squad
    "PQ": "fit",        # Pre-qualified (team eliminated but player available)
}


def import_players(json_path, db_path=DB_PATH):
    with open(json_path) as f:
        data = json.load(f)

    players = data["data"]["value"]["playerList"]
    print(f"Found {len(players)} players")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Init tables if needed
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS player_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER REFERENCES players(id),
        matchday_id INTEGER REFERENCES matchdays(id),
        total_points_before INTEGER DEFAULT 0,
        total_points_after INTEGER,
        matchday_points INTEGER,
        UNIQUE(player_id, matchday_id)
    );
""")
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

    # Check if this is a re-import (players already exist)
    existing_count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    is_reimport = existing_count > 0
    
    # If re-import, snapshot current points for active matchday
    old_points = {}
    if is_reimport:
        for row in conn.execute("SELECT uefa_id, total_points FROM players").fetchall():
            old_points[row[0]] = row[1]
    
    # Clear existing players
    conn.execute("DELETE FROM players")

    # Collect fixtures from player data
    fixtures_seen = set()
    fixture_data = []

    count = 0
    for p in players:
        pos = SKILL_TO_POS.get(p.get("skill", 3), "MID")
        status = STATUS_MAP.get(p.get("pStatus", ""), "fit")
        
        # Determine if starter based on training status and minutes
        trained = p.get("trained", "")
        is_starter = 1
        if "Unlikely" in trained:
            is_starter = 0
        elif status == "out":
            is_starter = 0
        elif p.get("minsPlyd", 0) == 0:
            is_starter = 0

        # Detect set piece takers (penalty earned > 0 or high assist ratio for position)
        is_sp = 0
        if p.get("pE", 0) > 0:  # penalty earned
            is_sp = 1

        conn.execute("""
            INSERT OR REPLACE INTO players 
            (uefa_id, name, club, club_code, position, price, is_starter, 
             is_set_piece_taker, injury_status, total_points, avg_points,
             goals, assists, clean_sheets, minutes_played, balls_recovered,
             selection_pct, form_rating)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p["id"],
            p["pFName"],
            p["tName"],
            p.get("cCode", ""),
            pos,
            p.get("value", 0),
            is_starter,
            is_sp,
            status,
            p.get("totPts", 0),
            p.get("avgPlayerPts", 0),
            p.get("gS", 0),
            p.get("assist", 0),
            p.get("cS", 0),
            p.get("minsPlyd", 0),
            p.get("bR", 0),
            p.get("selPer", 0),
            p.get("rating", 0),
        ))
        count += 1

        # Extract fixtures
        for match in p.get("currentMatchesList", []):
            if match.get("mdId") and match.get("tSCode"):
                key = f"{match['tSCode']}-{match.get('vsTSCode','')}"
                rev_key = f"{match.get('vsTSCode','')}-{match['tSCode']}"
                if key not in fixtures_seen and rev_key not in fixtures_seen:
                    fixtures_seen.add(key)
                    kick_off = match.get("kickOffTime", match.get("matchDate", ""))
                    match_date = match.get("matchDate", "")
                    # Determine if match is played (has score)
                    has_score = match.get("hSc") is not None or match.get("aSc") is not None
                    status = "played" if has_score else "scheduled"
                    h_score = match.get("hSc")
                    a_score = match.get("aSc")
                    
                    if match.get("tLoc") == "H":
                        fixture_data.append({
                            "home": match["tSCode"],
                            "home_code": match.get("cCode", ""),
                            "away": match.get("vsTSCode", ""),
                            "away_code": match.get("vsCCode", ""),
                            "date": match_date,
                            "kick_off": kick_off,
                            "status": status,
                            "home_score": h_score,
                            "away_score": a_score,
                        })
                    else:
                        fixture_data.append({
                            "home": match.get("vsTSCode", ""),
                            "home_code": match.get("vsCCode", ""),
                            "away": match["tSCode"],
                            "away_code": match.get("cCode", ""),
                            "date": match_date,
                            "kick_off": kick_off,
                            "status": status,
                            "home_score": a_score,  # swap since we swapped home/away
                            "away_score": h_score,
                        })

    conn.commit()
    print(f"Imported {count} players")

    # Calculate matchday points if re-importing
    active_md = conn.execute("SELECT id FROM matchdays WHERE is_active=1").fetchone()
    if is_reimport and old_points and active_md:
        md_id = active_md[0]
        updated = 0
        for p in players:
            uefa_id = str(p["id"])
            new_pts = p.get("totPts", 0) or 0
            old_pts = old_points.get(uefa_id, 0) or 0
            md_pts = new_pts - old_pts
            
            row = conn.execute("SELECT id FROM players WHERE uefa_id=?", (uefa_id,)).fetchone()
            if row:
                conn.execute("""
                    INSERT OR REPLACE INTO player_snapshots 
                    (player_id, matchday_id, total_points_before, total_points_after, matchday_points)
                    VALUES (?,?,?,?,?)
                """, (row[0], md_id, old_pts, new_pts, md_pts))
                updated += 1
        conn.commit()
        print(f"Updated matchday points for {updated} players")

    # Create first-import snapshot (baseline)
    # Will be finalized after matchday creation below

    # Create matchday and fixtures if we found any
    if fixture_data:
        conn.execute("UPDATE matchdays SET is_active = 0")
        cur = conn.execute(
            "INSERT INTO matchdays (name, stage, deadline, is_active) VALUES (?,?,?,1)",
            ("Knockout Play-offs", "ko_playoffs", fixture_data[0].get("date", ""))
        )
        md_id = cur.lastrowid

        # Strength estimates based on pot
        STRENGTH = {
            "Real Madrid": 0.95, "Bayern München": 0.9, "Man City": 0.85,
            "Liverpool": 0.9, "Barcelona": 0.85, "Inter": 0.85,
            "Paris": 0.85, "Atleti": 0.8, "B. Dortmund": 0.75,
            "Juventus": 0.8, "Arsenal": 0.85, "Leverkusen": 0.8,
            "Newcastle": 0.7, "Galatasaray": 0.65, "Monaco": 0.6,
            "Benfica": 0.7, "Club Brugge": 0.5, "Atalanta": 0.75,
            "Olympiacos": 0.5, "Sporting CP": 0.65, "Bodø/Glimt": 0.35,
            "Qarabağ": 0.3,
        }

        for fix in fixture_data:
            h_str = STRENGTH.get(fix["home"], 0.5)
            a_str = STRENGTH.get(fix["away"], 0.5)
            conn.execute("""
                INSERT INTO fixtures (matchday_id, home_club, home_code, away_club, away_code, 
                                      home_strength, away_strength, match_date, kick_off, status,
                                      home_score, away_score)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (md_id, fix["home"], fix["home_code"], fix["away"], fix["away_code"],
                  h_str, a_str, fix.get("date", ""), fix.get("kick_off", ""),
                  fix.get("status", "scheduled"), fix.get("home_score"), fix.get("away_score")))

        conn.commit()
        print(f"Created matchday with {len(fixture_data)} fixtures")

        # Create baseline snapshots on first import
        if not is_reimport:
            for p in players:
                uefa_id = str(p["id"])
                row = conn.execute("SELECT id FROM players WHERE uefa_id=?", (uefa_id,)).fetchone()
                if row:
                    conn.execute("""
                        INSERT OR IGNORE INTO player_snapshots 
                        (player_id, matchday_id, total_points_before, total_points_after, matchday_points)
                        VALUES (?,?,?,NULL,NULL)
                    """, (row[0], md_id, p.get("totPts", 0) or 0))
            conn.commit()
            print("Created baseline snapshots")

    conn.close()
    print("Done!")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/players_raw.json"
    db = sys.argv[2] if len(sys.argv) > 2 else DB_PATH
    import_players(path, db)
