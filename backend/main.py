"""
UCL Fantasy Assistant - FastAPI Backend
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import csv
import io
import json
from typing import Optional

from database import init_db, db_session
from scoring import Position, MatchStats, calculate_fantasy_points
from predictor import PlayerProfile, FixtureInfo, predict_points, Prediction
from optimizer import optimize_squad, SquadConstraints, OptimizedSquad
from import_uefa import import_players

app = FastAPI(title="UCL Fantasy Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ─── Players ───

class PlayerCreate(BaseModel):
    name: str
    club: str
    position: str
    price: float
    is_starter: bool = True
    is_set_piece_taker: bool = False
    injury_status: str = "fit"


@app.get("/api/players")
def get_players(position: Optional[str] = None, club: Optional[str] = None):
    with db_session() as conn:
        q = "SELECT * FROM players WHERE 1=1"
        params = []
        if position:
            q += " AND position = ?"
            params.append(position)
        if club:
            q += " AND club = ?"
            params.append(club)
        q += " ORDER BY price DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/players")
def create_player(p: PlayerCreate):
    with db_session() as conn:
        conn.execute(
            "INSERT INTO players (name, club, position, price, is_starter, is_set_piece_taker, injury_status) VALUES (?,?,?,?,?,?,?)",
            (p.name, p.club, p.position, p.price, p.is_starter, p.is_set_piece_taker, p.injury_status)
        )
        return {"status": "ok"}


@app.post("/api/players/import-csv")
async def import_players_csv(file: UploadFile = File(...)):
    """
    Import players from CSV.
    Expected columns: name, club, position, price, is_starter, is_set_piece_taker, injury_status
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    with db_session() as conn:
        for row in reader:
            conn.execute("""
                INSERT INTO players (name, club, position, price, is_starter, is_set_piece_taker, injury_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """, (
                row["name"].strip(),
                row["club"].strip(),
                row["position"].strip().upper(),
                float(row.get("price", 0)),
                int(row.get("is_starter", 1)),
                int(row.get("is_set_piece_taker", 0)),
                row.get("injury_status", "fit").strip(),
            ))
            count += 1

    return {"imported": count}


@app.delete("/api/players")
def delete_all_players():
    with db_session() as conn:
        conn.execute("DELETE FROM players")
        return {"status": "cleared"}


@app.post("/api/players/import-uefa")
async def import_uefa_json(file: UploadFile = File(...)):
    """Import players directly from UEFA Fantasy JSON (players_80_en_10.json)."""
    import tempfile, os
    content = await file.read()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False, dir='/app/data') as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        db_path = os.environ.get("DB_PATH", "/app/data/fantasy.db")
        import_players(tmp_path, db_path)
        
        # Count results
        import sqlite3
        conn = sqlite3.connect(db_path)
        players = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        fixtures = conn.execute("SELECT COUNT(*) FROM fixtures WHERE matchday_id = (SELECT id FROM matchdays WHERE is_active=1)").fetchone()[0]
        conn.close()
        
        return {"players": players, "fixtures": fixtures, "status": "ok"}
    finally:
        os.unlink(tmp_path)


# ─── Matchdays & Fixtures ───

class MatchdayCreate(BaseModel):
    name: str
    stage: str = "knockout"
    deadline: Optional[str] = None


class FixtureCreate(BaseModel):
    matchday_id: int
    home_club: str
    away_club: str
    home_strength: float = 0.5
    away_strength: float = 0.5


@app.get("/api/matchdays")
def get_matchdays():
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM matchdays ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/matchdays")
def create_matchday(m: MatchdayCreate):
    with db_session() as conn:
        # Deactivate all, activate new
        conn.execute("UPDATE matchdays SET is_active = 0")
        cur = conn.execute(
            "INSERT INTO matchdays (name, stage, deadline, is_active) VALUES (?,?,?,1)",
            (m.name, m.stage, m.deadline)
        )
        return {"id": cur.lastrowid}


@app.get("/api/fixtures")
def get_fixtures(matchday_id: int):
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM fixtures WHERE matchday_id = ?", (matchday_id,)).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/fixtures")
def create_fixture(f: FixtureCreate):
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO fixtures (matchday_id, home_club, away_club, home_strength, away_strength) VALUES (?,?,?,?,?)",
            (f.matchday_id, f.home_club, f.away_club, f.home_strength, f.away_strength)
        )
        return {"id": cur.lastrowid}


class FixtureUpdate(BaseModel):
    status: Optional[str] = None  # scheduled, live, played
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    kick_off: Optional[str] = None


@app.patch("/api/fixtures/{fixture_id}")
def update_fixture(fixture_id: int, update: FixtureUpdate):
    with db_session() as conn:
        parts = []
        params = []
        if update.status is not None:
            parts.append("status = ?")
            params.append(update.status)
        if update.home_score is not None:
            parts.append("home_score = ?")
            params.append(update.home_score)
        if update.away_score is not None:
            parts.append("away_score = ?")
            params.append(update.away_score)
        if update.kick_off is not None:
            parts.append("kick_off = ?")
            params.append(update.kick_off)
        if not parts:
            return {"status": "nothing to update"}
        params.append(fixture_id)
        conn.execute(f"UPDATE fixtures SET {', '.join(parts)} WHERE id = ?", params)
        return {"status": "ok"}


@app.post("/api/fixtures/bulk-update")
def bulk_update_fixtures(updates: list[dict]):
    """Bulk update fixture statuses and scores."""
    with db_session() as conn:
        for u in updates:
            fid = u.get("id")
            if not fid:
                continue
            parts = []
            params = []
            for field in ["status", "home_score", "away_score", "kick_off"]:
                if field in u and u[field] is not None:
                    parts.append(f"{field} = ?")
                    params.append(u[field])
            if parts:
                params.append(fid)
                conn.execute(f"UPDATE fixtures SET {', '.join(parts)} WHERE id = ?", params)
    return {"status": "ok"}


# ─── Match Stats Import ───

@app.post("/api/stats/import-csv")
async def import_stats_csv(matchday_id: int, file: UploadFile = File(...)):
    """
    Import match stats CSV.
    Columns: player_name, minutes, goals, goals_outside_box, assists, balls_recovered,
    player_of_match, penalty_won, penalty_conceded, penalty_missed, penalty_saved,
    yellow_card, red_card, own_goal, saves, goals_conceded, clean_sheet
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    with db_session() as conn:
        for row in reader:
            # Find player
            player = conn.execute(
                "SELECT id, position FROM players WHERE name = ?",
                (row["player_name"].strip(),)
            ).fetchone()
            if not player:
                continue

            stats = MatchStats(
                player_id=player["id"],
                position=Position(player["position"]),
                minutes=int(row.get("minutes", 0)),
                goals=int(row.get("goals", 0)),
                goals_outside_box=int(row.get("goals_outside_box", 0)),
                assists=int(row.get("assists", 0)),
                balls_recovered=int(row.get("balls_recovered", 0)),
                player_of_match=bool(int(row.get("player_of_match", 0))),
                penalty_won=int(row.get("penalty_won", 0)),
                penalty_conceded=int(row.get("penalty_conceded", 0)),
                penalty_missed=int(row.get("penalty_missed", 0)),
                penalty_saved=int(row.get("penalty_saved", 0)),
                yellow_card=bool(int(row.get("yellow_card", 0))),
                red_card=bool(int(row.get("red_card", 0))),
                own_goal=int(row.get("own_goal", 0)),
                saves=int(row.get("saves", 0)),
                goals_conceded=int(row.get("goals_conceded", 0)),
                clean_sheet=bool(int(row.get("clean_sheet", 0))),
            )
            fps = calculate_fantasy_points(stats)

            conn.execute("""
                INSERT OR REPLACE INTO match_stats
                (player_id, matchday_id, minutes, goals, goals_outside_box, assists,
                balls_recovered, player_of_match, penalty_won, penalty_conceded,
                penalty_missed, penalty_saved, yellow_card, red_card, own_goal,
                saves, goals_conceded, clean_sheet, fantasy_points)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                player["id"], matchday_id,
                stats.minutes, stats.goals, stats.goals_outside_box, stats.assists,
                stats.balls_recovered, int(stats.player_of_match),
                stats.penalty_won, stats.penalty_conceded, stats.penalty_missed,
                stats.penalty_saved, int(stats.yellow_card), int(stats.red_card),
                stats.own_goal, stats.saves, stats.goals_conceded,
                int(stats.clean_sheet), fps
            ))
            count += 1

    return {"imported": count}


# ─── Predictions ───

@app.get("/api/predictions")
def get_predictions(matchday_id: Optional[int] = None):
    """Get expected points predictions for all players in current/specified matchday."""
    with db_session() as conn:
        # Get active matchday
        if matchday_id:
            md = conn.execute("SELECT * FROM matchdays WHERE id = ?", (matchday_id,)).fetchone()
        else:
            md = conn.execute("SELECT * FROM matchdays WHERE is_active = 1").fetchone()

        if not md:
            raise HTTPException(404, "No active matchday")

        fixtures = conn.execute("SELECT * FROM fixtures WHERE matchday_id = ?", (md["id"],)).fetchall()
        players = conn.execute("SELECT * FROM players").fetchall()

        # Build club -> fixture mapping (try both name and code)
        club_fixtures = {}
        played_clubs = set()  # clubs whose fixtures are already played
        for f in fixtures:
            home_name = f["home_club"]
            away_name = f["away_club"]
            home_code = f["home_code"] if "home_code" in f.keys() else ""
            away_code = f["away_code"] if "away_code" in f.keys() else ""
            f_status = f["status"] if "status" in f.keys() else "scheduled"
            
            if f_status == "played":
                played_clubs.add(home_name)
                played_clubs.add(away_name)
                if home_code:
                    played_clubs.add(home_code)
                if away_code:
                    played_clubs.add(away_code)
            
            home_fix = FixtureInfo(
                opponent_club=away_name,
                opponent_strength=f["away_strength"],
                is_home=True,
                is_knockout=md["stage"] != "league_phase"
            )
            away_fix = FixtureInfo(
                opponent_club=home_name,
                opponent_strength=f["home_strength"],
                is_home=False,
                is_knockout=md["stage"] != "league_phase"
            )
            club_fixtures[home_name] = home_fix
            club_fixtures[away_name] = away_fix
            if home_code:
                club_fixtures[home_code] = home_fix
            if away_code:
                club_fixtures[away_code] = away_fix

        # Get historical stats for form
        results = []
        for p in players:
            club_key = p["club"]
            club_code = p["club_code"] if "club_code" in p.keys() else ""
            if club_key not in club_fixtures and club_code not in club_fixtures:
                continue  # club not playing this matchday

            fixture = club_fixtures.get(club_key) or club_fixtures.get(club_code)

            # Use UEFA avg stats if no historical match_stats
            stats = conn.execute("""
                SELECT fantasy_points, minutes FROM match_stats
                WHERE player_id = ? ORDER BY matchday_id DESC LIMIT 5
            """, (p["id"],)).fetchall()

            if stats:
                avg_pts = sum(s["fantasy_points"] for s in stats) / max(len(stats), 1)
                avg_min = sum(s["minutes"] for s in stats) / max(len(stats), 1)
                matches = len(stats)
            else:
                # Use UEFA data
                _avg_pts = p["avg_points"] if "avg_points" in p.keys() else 0
                _tot_pts = p["total_points"] if "total_points" in p.keys() else 0
                _mins = p["minutes_played"] if "minutes_played" in p.keys() else 0
                avg_pts = _avg_pts or (_tot_pts / max(1, (_mins // 90)))
                avg_min = _mins / max(1, 8)
                matches = max(1, _mins // 60) if _mins > 0 else 0

            profile = PlayerProfile(
                player_id=p["id"],
                name=p["name"],
                club=p["club"],
                position=Position(p["position"]),
                price=p["price"],
                avg_minutes_last5=avg_min,
                avg_points_last5=avg_pts if avg_pts else (p["avg_points"] if "avg_points" in p.keys() else 0),
                matches_played=matches,
                is_starter=bool(p["is_starter"]),
                is_set_piece_taker=bool(p["is_set_piece_taker"]),
                injury_status=p["injury_status"],
            )

            pred = predict_points(profile, fixture)
            
            # Check if this player's fixture is already played
            is_played = p["club"] in played_clubs or (club_code and club_code in played_clubs)
            
            # Get actual fantasy points from snapshots or match_stats
            actual_pts = None
            snap = conn.execute(
                "SELECT matchday_points FROM player_snapshots WHERE player_id = ? AND matchday_id = ?",
                (p["id"], md["id"])
            ).fetchone()
            if snap and snap["matchday_points"] is not None:
                actual_pts = snap["matchday_points"]
            elif is_played:
                actual_row = conn.execute(
                    "SELECT fantasy_points FROM match_stats WHERE player_id = ? AND matchday_id = ?",
                    (p["id"], md["id"])
                ).fetchone()
                if actual_row:
                    actual_pts = actual_row["fantasy_points"]
            
            results.append({
                "player_id": pred.player_id,
                "name": pred.name,
                "position": pred.position.value,
                "club": pred.club,
                "price": pred.price,
                "expected_points": pred.expected_points,
                "points_per_million": pred.points_per_million,
                "confidence": pred.confidence,
                "risk_level": pred.risk_level,
                "reasoning": pred.reasoning,
                "fixture_played": is_played,
                "actual_points": actual_pts,
            })

        results.sort(key=lambda x: -x["expected_points"])
        return results


# ─── Squad Optimizer ───

class OptimizeRequest(BaseModel):
    matchday_id: Optional[int] = None
    budget: float = 100.0
    max_per_club: int = 3
    risk_profile: str = "balanced"  # safe, balanced, aggressive


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    """Build optimal squad from predictions. Excludes players from already-played fixtures."""
    preds_raw = get_predictions(req.matchday_id)

    # Filter out players whose fixtures have already been played
    available = [p for p in preds_raw if not p.get("fixture_played", False)]

    predictions = [
        Prediction(
            player_id=p["player_id"],
            name=p["name"],
            position=Position(p["position"]),
            club=p["club"],
            price=p["price"],
            expected_points=p["expected_points"],
            points_per_million=p["points_per_million"],
            confidence=p["confidence"],
            risk_level=p["risk_level"],
            reasoning=p["reasoning"],
        )
        for p in available
    ]

    constraints = SquadConstraints(
        budget=req.budget,
        max_per_club=req.max_per_club,
    )

    result = optimize_squad(predictions, constraints, req.risk_profile)
    if not result:
        raise HTTPException(400, "Could not find optimal squad with these constraints")

    def player_dict(p: Prediction, is_captain=False):
        return {
            "player_id": p.player_id,
            "name": p.name,
            "position": p.position.value,
            "club": p.club,
            "price": p.price,
            "expected_points": p.expected_points * (2 if is_captain else 1),
            "confidence": p.confidence,
            "risk_level": p.risk_level,
            "reasoning": p.reasoning,
            "is_captain": is_captain,
        }

    return {
        "formation": result.formation,
        "total_expected": result.total_expected,
        "total_cost": result.total_cost,
        "captain": player_dict(result.captain, True),
        "starting_xi": [player_dict(p, p.player_id == result.captain.player_id) for p in result.starting_xi],
        "bench": [player_dict(p) for p in result.bench],
        "squad": [player_dict(p, p.player_id == result.captain.player_id) for p in result.squad],
    }


# ─── Stats & Dashboard ───

@app.get("/api/dashboard")
def dashboard():
    with db_session() as conn:
        player_count = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
        md = conn.execute("SELECT * FROM matchdays WHERE is_active = 1").fetchone()
        fixture_count = 0
        if md:
            fixture_count = conn.execute("SELECT COUNT(*) as c FROM fixtures WHERE matchday_id = ?", (md["id"],)).fetchone()["c"]
        stats_count = conn.execute("SELECT COUNT(*) as c FROM match_stats").fetchone()["c"]

        return {
            "players": player_count,
            "active_matchday": dict(md) if md else None,
            "fixtures": fixture_count,
            "total_stats_records": stats_count,
        }


@app.get("/api/clubs")
def get_clubs():
    with db_session() as conn:
        rows = conn.execute("SELECT DISTINCT club FROM players ORDER BY club").fetchall()
        return [r["club"] for r in rows]


# Serve frontend in production
import os
if os.path.exists("/app/frontend/dist"):
    app.mount("/", StaticFiles(directory="/app/frontend/dist", html=True), name="frontend")
