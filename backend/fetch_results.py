"""
Fetch match results from football-data.org free API.
Updates fixture scores and statuses in the database.
Run via cron after match days.
"""

import requests
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DB_PATH", "/app/data/fantasy.db")
# football-data.org free tier: 10 requests/min, UCL competition code = CL
API_URL = "https://api.football-data.org/v4/competitions/CL/matches"

# Map football-data team names to our DB names
TEAM_MAP = {
    "Real Madrid CF": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "FC Bayern München": "Bayern München",
    "Liverpool FC": "Liverpool",
    "Paris Saint-Germain FC": "Paris",
    "Manchester City FC": "Man City",
    "FC Internazionale Milano": "Inter",
    "Borussia Dortmund": "B. Dortmund",
    "Juventus FC": "Juventus",
    "Club Atlético de Madrid": "Atleti",
    "Arsenal FC": "Arsenal",
    "Bayer 04 Leverkusen": "Leverkusen",
    "SL Benfica": "Benfica",
    "AS Monaco FC": "Monaco",
    "Atalanta BC": "Atalanta",
    "Club Brugge KV": "Club Brugge",
    "Newcastle United FC": "Newcastle",
    "Galatasaray SK": "Galatasaray",
    "Olympiacos FC": "Olympiacos",
    "Sporting Clube de Portugal": "Sporting CP",
    "FK Bodø/Glimt": "Bodø/Glimt",
    "Qarabağ FK": "Qarabağ",
}


def normalize_team(name):
    return TEAM_MAP.get(name, name)


def fetch_and_update(db_path=DB_PATH):
    """Fetch recent CL results and update fixture statuses."""
    headers = {}
    # Optional: set API key for higher rate limits
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if api_key:
        headers["X-Auth-Token"] = api_key

    # Fetch matches from last 7 days
    date_from = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        r = requests.get(
            API_URL,
            params={"dateFrom": date_from, "dateTo": date_to},
            headers=headers,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"API error: {e}")
        return 0

    matches = data.get("matches", [])
    print(f"Fetched {len(matches)} matches from football-data.org")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    updated = 0
    for m in matches:
        if m["status"] not in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue
            
        home = normalize_team(m["homeTeam"]["name"])
        away = normalize_team(m["awayTeam"]["name"])
        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]
        status = "played" if m["status"] == "FINISHED" else "live"
        
        # Find matching fixture
        row = conn.execute(
            "SELECT id FROM fixtures WHERE home_club = ? AND away_club = ? AND status != 'played'",
            (home, away)
        ).fetchone()
        
        if row:
            conn.execute(
                "UPDATE fixtures SET status = ?, home_score = ?, away_score = ? WHERE id = ?",
                (status, home_score, away_score, row["id"])
            )
            updated += 1
            print(f"  Updated: {home} {home_score}-{away_score} {away}")
        else:
            # Try reverse lookup or partial match
            row = conn.execute(
                "SELECT id, home_club, away_club FROM fixtures WHERE status != 'played' AND (home_club LIKE ? OR away_club LIKE ?)",
                (f"%{home[:6]}%", f"%{away[:6]}%")
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE fixtures SET status = ?, home_score = ?, away_score = ? WHERE id = ?",
                    (status, home_score, away_score, row["id"])
                )
                updated += 1
                print(f"  Updated (fuzzy): {row['home_club']} {home_score}-{away_score} {row['away_club']}")

    conn.commit()
    conn.close()
    print(f"Updated {updated} fixtures")
    return updated


if __name__ == "__main__":
    fetch_and_update()
