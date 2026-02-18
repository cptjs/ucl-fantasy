"""
UCL Fantasy Assistant - FastAPI Backend
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import csv
import io
import json
import os
from typing import Optional

ADMIN_KEY = os.environ.get("ADMIN_KEY", "ucl-admin-2026")


def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, "Admin access required")
    return True

from database import init_db, db_session
from scoring import Position, MatchStats, calculate_fantasy_points
from predictor import PlayerProfile, FixtureInfo, predict_points, Prediction
from optimizer import optimize_squad, SquadConstraints, OptimizedSquad
from import_uefa import import_players
from rules import get_stage_rules, get_all_stages, STAGES

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
async def import_players_csv(file: UploadFile = File(...), admin=Depends(require_admin)):
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
def delete_all_players(admin=Depends(require_admin)):
    with db_session() as conn:
        conn.execute("DELETE FROM players")
        return {"status": "cleared"}


@app.post("/api/players/import-uefa")
async def import_uefa_json(file: UploadFile = File(...), admin=Depends(require_admin)):
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


@app.patch("/api/matchdays/{matchday_id}")
def update_matchday(matchday_id: int, m: MatchdayCreate):
    with db_session() as conn:
        conn.execute("UPDATE matchdays SET name=?, stage=?, deadline=? WHERE id=?",
                     (m.name, m.stage, m.deadline, matchday_id))
        return {"status": "ok"}


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


# ─── My Squad ───

class SetSquadRequest(BaseModel):
    player_ids: list[int]  # exactly 15
    captain_id: int
    vice_captain_id: int
    starting_ids: list[int]  # exactly 11


class TransferRequest(BaseModel):
    player_out_id: int
    player_in_id: int


class SetLineupRequest(BaseModel):
    starting_ids: list[int]  # 11 player ids
    captain_id: int
    vice_captain_id: Optional[int] = None


@app.get("/api/my-squad")
def get_my_squad():
    with db_session() as conn:
        squad = conn.execute("""
            SELECT ms.*, p.name, p.club, p.club_code, p.position, p.price, 
                   p.total_points, p.avg_points, p.injury_status
            FROM my_squad ms 
            JOIN players p ON p.id = ms.player_id
            ORDER BY 
                CASE p.position WHEN 'GK' THEN 1 WHEN 'DEF' THEN 2 WHEN 'MID' THEN 3 WHEN 'FWD' THEN 4 END,
                ms.is_starting DESC, p.price DESC
        """).fetchall()
        
        # Get transfer info for active matchday
        md = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
        stage = md["stage"] if md else "league_phase"
        rules = get_stage_rules(stage)
        
        transfers_made = 0
        free_transfers = rules["free_transfers"]
        if md:
            transfers_made = conn.execute(
                "SELECT COUNT(*) as c FROM transfers WHERE matchday_id=?", (md["id"],)
            ).fetchone()["c"]
        
        # Get boosters
        boosters = conn.execute("SELECT * FROM boosters").fetchall()
        
        total_value = sum(dict(s)["price"] for s in squad)
        # Check if user has a custom budget stored
        budget_row = conn.execute("SELECT value FROM settings WHERE key='budget'").fetchone() if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'").fetchone() else None
        budget = float(budget_row["value"]) if budget_row else rules["budget"]
        # If squad costs more than budget, adjust (user has gains from price rises)
        if total_value > budget:
            budget = total_value + 0.9  # preserve their remaining from real Fantasy
        
        return {
            "squad": [dict(s) for s in squad],
            "total_value": round(total_value, 1),
            "budget": budget,
            "budget_remaining": round(budget - total_value, 1),
            "stage": stage,
            "max_per_club": rules["max_per_club"],
            "transfers_made": transfers_made,
            "free_transfers": free_transfers,
            "penalty_transfers": max(0, transfers_made - free_transfers),
            "points_penalty": max(0, transfers_made - free_transfers) * 4,
            "boosters": [dict(b) for b in boosters],
            "active_matchday": dict(md) if md else None,
        }


@app.get("/api/rules")
def get_rules():
    """Get current rules based on active matchday stage."""
    with db_session() as conn:
        md = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
        stage = md["stage"] if md else "league_phase"
        rules = get_stage_rules(stage)
        return {
            "stage": stage,
            "stage_label": rules["label"],
            "budget": rules["budget"],
            "max_per_club": rules["max_per_club"],
            "free_transfers": rules["free_transfers"],
            "transfer_penalty": rules["transfer_penalty"],
            "all_stages": {k: {"label": v["label"], "budget": v["budget"], "max_per_club": v["max_per_club"]} for k, v in STAGES.items()},
        }


@app.post("/api/settings/budget")
def set_budget(budget: float = Query(...), admin=Depends(require_admin)):
    """Set the team budget (e.g. 100 for group, higher for knockout)."""
    with db_session() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('budget', ?)", (str(budget),))
        return {"status": "ok", "budget": budget}


@app.get("/api/settings")
def get_settings():
    with db_session() as conn:
        if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'").fetchone():
            return {"budget": 100.0}
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


@app.post("/api/my-squad/set")
def set_squad(req: SetSquadRequest):
    """Set initial squad (or full rebuild with wildcard)."""
    if len(req.player_ids) != 15:
        raise HTTPException(400, "Squad must have exactly 15 players")
    if len(req.starting_ids) != 11:
        raise HTTPException(400, "Starting XI must have exactly 11 players")
    if req.captain_id not in req.starting_ids:
        raise HTTPException(400, "Captain must be in starting XI")
    
    with db_session() as conn:
        # Validate players exist and check constraints
        players = []
        for pid in req.player_ids:
            p = conn.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
            if not p:
                raise HTTPException(400, f"Player {pid} not found")
            players.append(dict(p))
        
        # Check position counts: 2 GK, 5 DEF, 5 MID, 3 FWD
        pos_counts = {}
        for p in players:
            pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1
        
        required = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
        for pos, cnt in required.items():
            if pos_counts.get(pos, 0) != cnt:
                raise HTTPException(400, f"Need exactly {cnt} {pos}, got {pos_counts.get(pos, 0)}")
        
        # Get rules for current stage
        md = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
        stage = md["stage"] if md else "league_phase"
        rules = get_stage_rules(stage)
        
        # Check budget — warn but allow (user may have higher budget from price changes)
        total_cost = sum(p["price"] for p in players)
        budget_warning = None
        if total_cost > rules["budget"]:
            budget_warning = f"Squad costs €{round(total_cost,1)}M (base budget €{rules['budget']}M)"
        
        # Check club limits
        max_club = rules["max_per_club"]
        club_counts = {}
        for p in players:
            club_counts[p["club"]] = club_counts.get(p["club"], 0) + 1
        for club, cnt in club_counts.items():
            if cnt > max_club:
                raise HTTPException(400, f"Max {max_club} per club ({stage}): {club} has {cnt}")
        
        # Check starting XI validity
        starting_players = [p for p in players if p["id"] in req.starting_ids]
        starting_pos = {}
        for p in starting_players:
            starting_pos[p["position"]] = starting_pos.get(p["position"], 0) + 1
        
        if starting_pos.get("GK", 0) != 1:
            raise HTTPException(400, "Starting XI must have exactly 1 GK")
        if starting_pos.get("DEF", 0) < 3:
            raise HTTPException(400, "Starting XI must have at least 3 DEF")
        
        # Get active matchday
        md = conn.execute("SELECT id FROM matchdays WHERE is_active=1").fetchone()
        md_id = md["id"] if md else None
        
        # Clear and set
        conn.execute("DELETE FROM my_squad")
        for pid in req.player_ids:
            conn.execute("""
                INSERT INTO my_squad (player_id, is_captain, is_vice_captain, is_starting, added_matchday)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pid,
                1 if pid == req.captain_id else 0,
                1 if pid == req.vice_captain_id else 0,
                1 if pid in req.starting_ids else 0,
                md_id,
            ))
        
        return {"status": "ok", "total_cost": round(total_cost, 1), "budget_warning": budget_warning}


@app.post("/api/my-squad/transfer")
def make_transfer(req: TransferRequest):
    """Make a single transfer: swap one player out for one in."""
    with db_session() as conn:
        # Check player_out is in squad
        out_row = conn.execute("SELECT * FROM my_squad WHERE player_id=?", (req.player_out_id,)).fetchone()
        if not out_row:
            raise HTTPException(400, "Player not in your squad")
        
        # Check player_in exists and not already in squad
        pin = conn.execute("SELECT * FROM players WHERE id=?", (req.player_in_id,)).fetchone()
        if not pin:
            raise HTTPException(400, "Player not found")
        
        existing = conn.execute("SELECT id FROM my_squad WHERE player_id=?", (req.player_in_id,)).fetchone()
        if existing:
            raise HTTPException(400, "Player already in squad")
        
        # Check same position
        pout = conn.execute("SELECT * FROM players WHERE id=?", (req.player_out_id,)).fetchone()
        if pin["position"] != pout["position"]:
            raise HTTPException(400, f"Position mismatch: selling {pout['position']}, buying {pin['position']}")
        
        # Check budget from rules
        md_row = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
        stage = md_row["stage"] if md_row else "league_phase"
        rules = get_stage_rules(stage)
        squad_cost = conn.execute("""
            SELECT SUM(p.price) as total FROM my_squad ms JOIN players p ON p.id = ms.player_id
        """).fetchone()["total"]
        new_cost = squad_cost - pout["price"] + pin["price"]
        if new_cost > rules["budget"]:
            raise HTTPException(400, f"Over budget: €{round(new_cost, 1)}M > €{rules['budget']}M")
        
        # Check club limit
        max_club = rules["max_per_club"]
        club_count = conn.execute("""
            SELECT COUNT(*) as c FROM my_squad ms JOIN players p ON p.id = ms.player_id
            WHERE p.club = ? AND ms.player_id != ?
        """, (pin["club"], req.player_out_id)).fetchone()["c"]
        if club_count >= max_club:
            raise HTTPException(400, f"Club limit: already have {max_club} from {pin['club']}")
        
        # Get matchday
        md = conn.execute("SELECT id FROM matchdays WHERE is_active=1").fetchone()
        md_id = md["id"] if md else None
        
        # Count transfers this matchday
        transfers_count = 0
        if md_id:
            transfers_count = conn.execute(
                "SELECT COUNT(*) as c FROM transfers WHERE matchday_id=?", (md_id,)
            ).fetchone()["c"]
        
        is_free = 1 if transfers_count < 2 else 0
        
        # Execute transfer
        was_starting = out_row["is_starting"]
        was_captain = out_row["is_captain"]
        was_vc = out_row["is_vice_captain"]
        
        conn.execute("DELETE FROM my_squad WHERE player_id=?", (req.player_out_id,))
        conn.execute("""
            INSERT INTO my_squad (player_id, is_captain, is_vice_captain, is_starting, added_matchday)
            VALUES (?, ?, ?, ?, ?)
        """, (req.player_in_id, was_captain, was_vc, was_starting, md_id))
        
        # Record transfer
        conn.execute("""
            INSERT INTO transfers (matchday_id, player_in_id, player_out_id, is_free)
            VALUES (?, ?, ?, ?)
        """, (md_id, req.player_in_id, req.player_out_id, is_free))
        
        penalty = 0 if is_free else 4
        return {
            "status": "ok",
            "is_free": bool(is_free),
            "penalty": penalty,
            "total_transfers": transfers_count + 1,
            "player_out": pout["name"],
            "player_in": pin["name"],
        }


@app.post("/api/my-squad/lineup")
def set_lineup(req: SetLineupRequest):
    """Update starting XI and captain."""
    with db_session() as conn:
        # Validate all players are in squad
        squad_ids = [r["player_id"] for r in conn.execute("SELECT player_id FROM my_squad").fetchall()]
        for pid in req.starting_ids:
            if pid not in squad_ids:
                raise HTTPException(400, f"Player {pid} not in squad")
        if req.captain_id not in req.starting_ids:
            raise HTTPException(400, "Captain must be in starting XI")
        
        if len(req.starting_ids) != 11:
            raise HTTPException(400, "Need exactly 11 starters")
        
        # Update all
        conn.execute("UPDATE my_squad SET is_starting=0, is_captain=0, is_vice_captain=0")
        for pid in req.starting_ids:
            conn.execute("UPDATE my_squad SET is_starting=1 WHERE player_id=?", (pid,))
        conn.execute("UPDATE my_squad SET is_captain=1 WHERE player_id=?", (req.captain_id,))
        if req.vice_captain_id:
            conn.execute("UPDATE my_squad SET is_vice_captain=1 WHERE player_id=?", (req.vice_captain_id,))
        
        return {"status": "ok"}


@app.get("/api/my-squad/suggestions")
def transfer_suggestions():
    """Suggest transfers based on current squad and predictions."""
    with db_session() as conn:
        # Get current squad
        squad = conn.execute("""
            SELECT ms.player_id, p.name, p.club, p.position, p.price
            FROM my_squad ms JOIN players p ON p.id = ms.player_id
        """).fetchall()
        
        if not squad:
            return {"suggestions": [], "message": "No squad set. Set your squad first."}
        
        squad_ids = set(s["player_id"] for s in squad)
        squad_positions = {}
        for s in squad:
            squad_positions.setdefault(s["position"], []).append(dict(s))
    
    # Get predictions
    try:
        preds = get_predictions()
    except:
        return {"suggestions": [], "message": "No predictions available"}
    
    pred_map = {p["player_id"]: p for p in preds}
    
    suggestions = []
    for s in squad:
        s = dict(s)
        s_pred = pred_map.get(s["player_id"], {}).get("expected_points", 0)
        
        # Find better players at same position within budget
        squad_cost = sum(dict(sq)["price"] for sq in squad)
        budget_left = 100 - squad_cost + s["price"]
        
        better = []
        for p in preds:
            if p["player_id"] in squad_ids:
                continue
            if p["position"] != s["position"]:
                continue
            if p["price"] > budget_left:
                continue
            if p["expected_points"] > s_pred:
                better.append({
                    "player_in": p,
                    "player_out": s,
                    "points_gain": round(p["expected_points"] - s_pred),
                    "cost_diff": round(p["price"] - s["price"], 1),
                })
        
        better.sort(key=lambda x: -x["points_gain"])
        suggestions.extend(better[:2])  # top 2 per position
    
    suggestions.sort(key=lambda x: -x["points_gain"])
    return {"suggestions": suggestions[:10]}


# ─── Auto-fetch Results ───

@app.post("/api/fetch-results")
def fetch_results():
    """Fetch latest match results from football-data.org."""
    from fetch_results import fetch_and_update
    import os
    db_path = os.environ.get("DB_PATH", "/app/data/fantasy.db")
    updated = fetch_and_update(db_path)
    return {"updated": updated}


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
        for p in preds_raw
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
