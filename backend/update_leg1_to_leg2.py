"""
One-time migration script:
1. Update 4 missing Leg 1 fixture results
2. Mark all Leg 1 fixtures as played
3. Save current player totPts as baseline (before Leg 1 points)
4. Import new JSON: update player data, calculate Leg 1 matchday points via snapshots
5. Create Matchday 2 (Leg 2) with new fixtures
"""

import json
import sqlite3
import sys
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/fantasy.db")
JSON_PATH = sys.argv[1] if len(sys.argv) > 1 else "/workspace/ucl-fantasy/data/players_md10.json"

SKILL_TO_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
STATUS_MAP = {
    "": "fit", "I": "doubt", "D": "doubt", "S": "out",
    "E": "out", "NIS": "out", "PQ": "fit",
}

LEG1_RESULTS = [
    {"home": "Qarabağ", "away": "Newcastle", "home_score": 1, "away_score": 6},
    {"home": "Bodø/Glimt", "away": "Inter", "home_score": 3, "away_score": 1},
    {"home": "Club Brugge", "away": "Atleti", "home_score": 3, "away_score": 3},
    {"home": "Olympiacos", "away": "Leverkusen", "home_score": 0, "away_score": 2},
]

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


def run(db_path=DB_PATH, json_path=JSON_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Step 1: Update Leg 1 fixture results
    print("=== Step 1: Update Leg 1 missing results ===")
    for r in LEG1_RESULTS:
        row = conn.execute(
            "SELECT id FROM fixtures WHERE home_club = ? AND away_club = ?",
            (r["home"], r["away"])
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE fixtures SET status='played', home_score=?, away_score=? WHERE id=?",
                (r["home_score"], r["away_score"], row["id"])
            )
            print(f"  Updated: {r['home']} {r['home_score']}-{r['away_score']} {r['away']}")
        else:
            print(f"  WARNING: Fixture not found: {r['home']} vs {r['away']}")

    conn.execute("UPDATE fixtures SET status='played' WHERE matchday_id=1")
    conn.commit()

    # Step 2: Rename Matchday 1
    print("\n=== Step 2: Rename matchday ===")
    conn.execute("UPDATE matchdays SET name='KO Playoffs - Leg 1' WHERE id=1")
    conn.commit()
    print("  Matchday 1 -> 'KO Playoffs - Leg 1'")

    # Step 3: Save current totPts as baseline
    print("\n=== Step 3: Save baseline points ===")
    old_points = {}
    for row in conn.execute("SELECT uefa_id, total_points, id FROM players").fetchall():
        old_points[row["uefa_id"]] = {"total_points": row["total_points"], "db_id": row["id"]}
    print(f"  Saved baseline for {len(old_points)} players")

    # Step 4: Load new JSON and update players
    print("\n=== Step 4: Import new player data ===")
    with open(json_path) as f:
        data = json.load(f)
    players = data["data"]["value"]["playerList"]
    print(f"  Found {len(players)} players in JSON")

    conn.execute("DELETE FROM players")

    count = 0
    for p in players:
        pos = SKILL_TO_POS.get(p.get("skill", 3), "MID")
        status = STATUS_MAP.get(p.get("pStatus", ""), "fit")
        trained = p.get("trained", "")
        is_starter = 1
        if "Unlikely" in trained:
            is_starter = 0
        elif status == "out":
            is_starter = 0
        elif p.get("minsPlyd", 0) == 0:
            is_starter = 0
        is_sp = 1 if p.get("pE", 0) > 0 else 0

        conn.execute("""
            INSERT OR REPLACE INTO players 
            (uefa_id, name, club, club_code, position, price, is_starter, 
             is_set_piece_taker, injury_status, total_points, avg_points,
             goals, assists, clean_sheets, minutes_played, balls_recovered,
             selection_pct, form_rating)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p["id"], p["pFName"], p["tName"], p.get("cCode", ""),
            pos, p.get("value", 0), is_starter, is_sp, status,
            p.get("totPts", 0), p.get("avgPlayerPts", 0),
            p.get("gS", 0), p.get("assist", 0), p.get("cS", 0),
            p.get("minsPlyd", 0), p.get("bR", 0),
            p.get("selPer", 0), p.get("rating", 0),
        ))
        count += 1
    conn.commit()
    print(f"  Imported {count} players")

    # Step 5: Create snapshots (Leg 1 matchday points)
    print("\n=== Step 5: Calculate Leg 1 matchday points ===")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER REFERENCES players(id),
            matchday_id INTEGER REFERENCES matchdays(id),
            total_points_before INTEGER DEFAULT 0,
            total_points_after INTEGER,
            matchday_points INTEGER,
            UNIQUE(player_id, matchday_id)
        )
    """)
    conn.execute("DELETE FROM player_snapshots WHERE matchday_id=1")

    updated_snaps = 0
    for p in players:
        uefa_id = str(p["id"])
        new_pts = p.get("totPts", 0) or 0
        row = conn.execute("SELECT id FROM players WHERE uefa_id=?", (uefa_id,)).fetchone()
        if not row:
            continue
        old_data = old_points.get(uefa_id)
        old_pts = old_data["total_points"] if old_data else new_pts
        old_pts = old_pts or 0
        md_pts = new_pts - old_pts

        conn.execute("""
            INSERT OR REPLACE INTO player_snapshots 
            (player_id, matchday_id, total_points_before, total_points_after, matchday_points)
            VALUES (?,?,?,?,?)
        """, (row["id"], 1, old_pts, new_pts, md_pts))
        updated_snaps += 1

    conn.commit()
    print(f"  Created {updated_snaps} snapshots")
    top = conn.execute("""
        SELECT ps.matchday_points, p.name, p.club 
        FROM player_snapshots ps JOIN players p ON p.id=ps.player_id 
        WHERE ps.matchday_id=1 
        ORDER BY ps.matchday_points DESC LIMIT 10
    """).fetchall()
    print("  Top Leg 1 performers:")
    for t in top:
        print(f"    {t['name']} ({t['club']}): {t['matchday_points']} pts")

    # Step 6: Create Matchday 2 (Leg 2)
    print("\n=== Step 6: Create Leg 2 matchday + fixtures ===")
    conn.execute("UPDATE matchdays SET is_active=0 WHERE id=1")
    cur = conn.execute(
        "INSERT INTO matchdays (name, stage, deadline, is_active) VALUES (?,?,?,1)",
        ("KO Playoffs - Leg 2", "ko_playoffs_leg2", "2026-02-24")
    )
    md2_id = cur.lastrowid
    print(f"  Created matchday {md2_id}: KO Playoffs - Leg 2")

    fixtures_seen = set()
    fixture_count = 0
    for p in players:
        for match in p.get("currentMatchesList", []):
            if not match.get("mdId") or not match.get("tSCode"):
                continue
            if match.get("tLoc") == "H":
                home, home_code = match["tSCode"], match.get("cCode", "")
                away, away_code = match.get("vsTSCode", ""), match.get("vsCCode", "")
            else:
                home, home_code = match.get("vsTSCode", ""), match.get("vsCCode", "")
                away, away_code = match["tSCode"], match.get("cCode", "")

            key = f"{home}-{away}"
            rev_key = f"{away}-{home}"
            if key in fixtures_seen or rev_key in fixtures_seen:
                continue
            fixtures_seen.add(key)

            match_date = match.get("matchDate", "")
            h_str = STRENGTH.get(home, 0.5)
            a_str = STRENGTH.get(away, 0.5)

            conn.execute("""
                INSERT INTO fixtures (matchday_id, home_club, home_code, away_club, away_code,
                                      home_strength, away_strength, match_date, kick_off, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (md2_id, home, home_code, away, away_code,
                  h_str, a_str, match_date, match_date, "scheduled"))
            fixture_count += 1
            print(f"    {home} vs {away} ({match_date})")

    conn.commit()
    print(f"  Created {fixture_count} fixtures")

    # Step 7: Fix my_squad references
    print("\n=== Step 7: Fix squad player references ===")
    old_squad = conn.execute("SELECT * FROM my_squad").fetchall()
    if old_squad:
        old_id_to_uefa = {data["db_id"]: uid for uid, data in old_points.items()}
        conn.execute("DELETE FROM my_squad")
        fixed = 0
        for sq in old_squad:
            old_pid = sq["player_id"]
            uefa_id = old_id_to_uefa.get(old_pid)
            if not uefa_id:
                print(f"  WARNING: no uefa_id for old player_id {old_pid}")
                continue
            new_player = conn.execute("SELECT id FROM players WHERE uefa_id=?", (uefa_id,)).fetchone()
            if not new_player:
                print(f"  WARNING: Player {uefa_id} not in new import")
                continue
            conn.execute("""
                INSERT INTO my_squad (player_id, is_captain, is_vice_captain, is_starting, added_matchday)
                VALUES (?,?,?,?,?)
            """, (new_player["id"], sq["is_captain"], sq["is_vice_captain"],
                  sq["is_starting"], sq["added_matchday"]))
            fixed += 1
        conn.commit()
        print(f"  Remapped {fixed}/{len(old_squad)} squad players")
    else:
        print("  No squad to fix")

    # Verify
    print("\n=== Verification ===")
    pc = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
    f1 = conn.execute("SELECT COUNT(*) as c FROM fixtures WHERE matchday_id=1").fetchone()["c"]
    f2 = conn.execute("SELECT COUNT(*) as c FROM fixtures WHERE matchday_id=?", (md2_id,)).fetchone()["c"]
    sc = conn.execute("SELECT COUNT(*) as c FROM player_snapshots WHERE matchday_id=1").fetchone()["c"]
    sqc = conn.execute("SELECT COUNT(*) as c FROM my_squad").fetchone()["c"]
    amd = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
    print(f"  Players: {pc}")
    print(f"  Leg 1 fixtures: {f1} (all played)")
    print(f"  Leg 2 fixtures: {f2} (scheduled)")
    print(f"  Leg 1 snapshots: {sc}")
    print(f"  Squad players: {sqc}")
    print(f"  Active matchday: {amd['name']} (id={amd['id']})")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    run()
