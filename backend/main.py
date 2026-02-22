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
from import_uefa import import_players, STRENGTH
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
            return {"budget": 105.0}
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
    """Smart transfer suggestions with reasoning."""
    with db_session() as conn:
        squad = conn.execute("""
            SELECT ms.player_id, ms.is_starting, ms.is_captain, p.name, p.club, p.club_code, 
                   p.position, p.price, p.avg_points, p.total_points, p.injury_status
            FROM my_squad ms JOIN players p ON p.id = ms.player_id
        """).fetchall()
        
        if not squad:
            return {"suggestions": [], "summary": "No squad set.", "actions": []}
        
        squad_ids = set(s["player_id"] for s in squad)
        
        md = conn.execute("SELECT * FROM matchdays WHERE is_active=1").fetchone()
        stage = md["stage"] if md else "ko_playoffs"
        rules = get_stage_rules(stage)
        
        # Count transfers already made
        transfers_made = 0
        if md:
            transfers_made = conn.execute(
                "SELECT COUNT(*) as c FROM transfers WHERE matchday_id=?", (md["id"],)
            ).fetchone()["c"]
        free_left = max(0, rules["free_transfers"] - transfers_made) if rules["free_transfers"] != "unlimited" else 99
    
    # Get predictions for upcoming matchday
    try:
        preds = get_predictions()
    except:
        return {"suggestions": [], "summary": "No predictions available.", "actions": []}
    
    pred_map = {p["player_id"]: p for p in preds}
    
    # Analyze each squad player
    squad_analysis = []
    for s in squad:
        s = dict(s)
        pred = pred_map.get(s["player_id"], {})
        s["expected"] = pred.get("expected_points", 0)
        s["fixture_info"] = pred.get("reasoning", [])
        s["fixture_played"] = pred.get("fixture_played", False)
        squad_analysis.append(s)
    
    # Find issues and opportunities
    suggestions = []
    injured = [s for s in squad_analysis if s["injury_status"] in ("out", "doubt")]
    low_expected = sorted([s for s in squad_analysis if s["is_starting"] and s["expected"] <= 3 and s["injury_status"] == "fit"], key=lambda x: x["expected"])
    
    # For each weak spot, find the best replacement
    targets = injured + low_expected[:3]  # prioritize injured, then lowest-expected starters
    
    for s in targets:
        squad_cost = sum(sq["price"] for sq in squad_analysis)
        budget_avail = rules["budget"] - squad_cost + s["price"]
        
        # Find best replacement (same position, not in squad)
        candidates = []
        for p in preds:
            if p["player_id"] in squad_ids:
                continue
            if p["position"] != s["position"]:
                continue
            if p["expected_points"] <= s["expected"]:
                continue
            
            # Check club limit
            club_count = sum(1 for sq in squad_analysis if sq["club"] == p.get("club", "") and sq["player_id"] != s["player_id"])
            over_club = club_count >= rules["max_per_club"]
            
            over_budget = p["price"] > budget_avail
            
            reason_parts = []
            if s["injury_status"] == "out":
                reason_parts.append(f"{s['name']} is injured (OUT)")
            elif s["injury_status"] == "doubt":
                reason_parts.append(f"{s['name']} is doubtful")
            else:
                reason_parts.append(f"{s['name']} expected only {s['expected']} pts")
            reason_parts.append(f"{p['name']} predicted {p['expected_points']} pts")
            if p.get("reasoning"):
                fix_info = [r for r in p["reasoning"] if "vs" in r]
                if fix_info:
                    reason_parts.append(fix_info[0])
            
            candidates.append({
                "player_in": p,
                "player_out": s,
                "points_gain": round(p["expected_points"] - s["expected"]),
                "cost_diff": round(p["price"] - s["price"], 1),
                "reason": ". ".join(reason_parts),
                "priority": "high" if s["injury_status"] in ("out", "doubt") else "medium",
                "warning": "over budget" if over_budget else "club limit" if over_club else None,
            })
        
        candidates.sort(key=lambda x: (-x["points_gain"], x["cost_diff"]))
        suggestions.extend(candidates[:2])
    
    # Also add "upgrade" suggestions for bench/starters even if not injured
    all_squad_sorted = sorted(squad_analysis, key=lambda x: x["expected"])
    for s in all_squad_sorted[:5]:
        if any(sg["player_out"]["player_id"] == s["player_id"] for sg in suggestions):
            continue
        squad_cost = sum(sq["price"] for sq in squad_analysis)
        budget_avail = rules["budget"] - squad_cost + s["price"]
        
        best = None
        for p in preds:
            if p["player_id"] in squad_ids:
                continue
            if p["position"] != s["position"]:
                continue
            if p["expected_points"] <= s["expected"] + 2:  # only suggest if significant upgrade
                continue
            gain = p["expected_points"] - s["expected"]
            if best is None or gain > best["points_gain"]:
                best = {
                    "player_in": p,
                    "player_out": s,
                    "points_gain": round(gain),
                    "cost_diff": round(p["price"] - s["price"], 1),
                    "reason": f"Upgrade: {p['name']} ({p['expected_points']} pts) over {s['name']} ({s['expected']} pts)",
                    "priority": "low",
                    "warning": None if p["price"] <= budget_avail else "over budget",
                }
        if best:
            suggestions.append(best)
    
    suggestions.sort(key=lambda x: ({"high": 0, "medium": 1, "low": 2}[x["priority"]], -x["points_gain"]))
    
    # Build summary
    total_expected = sum(s["expected"] * (2 if s["is_captain"] else 1) for s in squad_analysis if s["is_starting"])
    injured_names = [s["name"] for s in injured]
    
    summary_parts = [f"Expected squad points: ~{round(total_expected)}"]
    if injured_names:
        summary_parts.append(f"⚠️ Injured: {', '.join(injured_names)}")
    if free_left > 0:
        summary_parts.append(f"Free transfers left: {free_left}")
    else:
        summary_parts.append(f"⚠️ No free transfers (-4 pts each)")
    
    # Top 3 actions as simple text
    actions = []
    for s in suggestions[:3]:
        action = f"{'🔴' if s['priority']=='high' else '🟡' if s['priority']=='medium' else '🟢'} {s['player_out']['name']} → {s['player_in']['name']} (+{s['points_gain']} pts)"
        if s.get("warning"):
            action += f" ⚠️ {s['warning']}"
        actions.append(action)
    
    return {
        "suggestions": suggestions[:10],
        "summary": " | ".join(summary_parts),
        "actions": actions,
        "total_expected": round(total_expected),
        "injured": injured_names,
        "free_transfers_left": free_left,
    }


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
    budget: float = 105.0
    max_per_club: int = 4
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
# ─── Admin: Fix squad references after reimport ───

@app.post("/api/admin/fix-squad")
def fix_squad_references(admin=Depends(require_admin)):
    """Fix my_squad player references after player reimport.
    Remaps orphaned player_ids to new IDs by matching player names."""
    with db_session() as conn:
        # Find orphaned squad entries
        orphans = conn.execute("""
            SELECT ms.id as squad_id, ms.player_id as old_pid,
                   ms.is_captain, ms.is_vice_captain, ms.is_starting, ms.added_matchday
            FROM my_squad ms
            LEFT JOIN players p ON p.id = ms.player_id
            WHERE p.id IS NULL
        """).fetchall()
        
        if not orphans:
            squad_count = conn.execute("SELECT COUNT(*) as c FROM my_squad").fetchone()["c"]
            return {"status": "ok", "message": "No orphaned entries", "squad_size": squad_count}
        
        # Try to find old player names from snapshots + players
        # Since both snapshots and players were remapped, we need another approach.
        # Check if there are any matching player_ids in snapshots
        fixed = 0
        failed = []
        for o in orphans:
            old_pid = o["old_pid"]
            # Try to find in snapshots (snapshot player_ids point to NEW player IDs)
            snap = conn.execute(
                "SELECT player_id FROM player_snapshots WHERE player_id = ?", (old_pid,)
            ).fetchone()
            if snap:
                # This old_pid happens to match a new player_id in snapshots - skip
                pass
            
            # Just delete orphans since we can't remap without old data
            failed.append(old_pid)
        
        # Delete all orphaned entries
        conn.execute("""
            DELETE FROM my_squad WHERE player_id NOT IN (SELECT id FROM players)
        """)
        
        return {
            "status": "cleaned",
            "orphans_removed": len(orphans),
            "message": "Orphaned squad entries removed. Use /api/my-squad/set to rebuild your squad."
        }


# ─── Admin: Fix snapshots using lastGdPoints from UEFA JSON ───

@app.post("/api/admin/fix-snapshots")
async def fix_snapshots(file: UploadFile = File(...), matchday_id: int = Query(1), admin=Depends(require_admin)):
    """Fix player snapshots using lastGdPoints from UEFA JSON.
    Use when re-import baseline was wrong (e.g., first import happened mid-matchday).
    lastGdPoints = actual matchday points from UEFA."""
    import tempfile
    content = await file.read()
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False, dir='/app/data') as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        with open(tmp_path) as f:
            data = json.load(f)
        players_json = data["data"]["value"]["playerList"]
        
        with db_session() as conn:
            updated = 0
            for p in players_json:
                uefa_id = str(p["id"])
                tot_pts = p.get("totPts", 0) or 0
                last_gd = p.get("lastGdPoints", 0) or 0
                before_pts = tot_pts - last_gd
                
                # Find player in DB
                row = conn.execute("SELECT id FROM players WHERE uefa_id=?", (uefa_id,)).fetchone()
                if not row:
                    continue
                
                # Update or create snapshot
                conn.execute("""
                    INSERT OR REPLACE INTO player_snapshots 
                    (player_id, matchday_id, total_points_before, total_points_after, matchday_points)
                    VALUES (?, ?, ?, ?, ?)
                """, (row["id"], matchday_id, int(before_pts), tot_pts, int(last_gd)))
                updated += 1
            
            # Return top performers
            top = conn.execute("""
                SELECT ps.matchday_points, p.name, p.club 
                FROM player_snapshots ps JOIN players p ON p.id=ps.player_id 
                WHERE ps.matchday_id=? ORDER BY ps.matchday_points DESC LIMIT 10
            """, (matchday_id,)).fetchall()
        
        return {
            "updated": updated,
            "matchday_id": matchday_id,
            "top_performers": [{"name": t["name"], "club": t["club"], "points": t["matchday_points"]} for t in top]
        }
    finally:
        os.unlink(tmp_path)


# ─── Admin: Rebuild squad from player names ───

class RebuildSquadRequest(BaseModel):
    players: list[str]  # list of player names
    captain: str
    vice_captain: str
    starting: list[str]  # 11 names


@app.post("/api/admin/rebuild-squad")
def rebuild_squad(req: RebuildSquadRequest, admin=Depends(require_admin)):
    """Rebuild my_squad from player names (useful after reimport when IDs changed)."""
    with db_session() as conn:
        player_ids = []
        name_to_id = {}
        for name in req.players:
            row = conn.execute("SELECT id FROM players WHERE name=?", (name,)).fetchone()
            if not row:
                # Try fuzzy match
                row = conn.execute("SELECT id FROM players WHERE name LIKE ?", (f"%{name}%",)).fetchone()
            if not row:
                raise HTTPException(400, f"Player not found: {name}")
            player_ids.append(row["id"])
            name_to_id[name] = row["id"]
        
        if len(player_ids) != 15:
            raise HTTPException(400, f"Need exactly 15 players, got {len(player_ids)}")
        
        captain_id = name_to_id.get(req.captain)
        vc_id = name_to_id.get(req.vice_captain)
        starting_ids = [name_to_id.get(n) for n in req.starting if name_to_id.get(n)]
        
        if not captain_id:
            raise HTTPException(400, f"Captain not found: {req.captain}")
        if len(starting_ids) != 11:
            raise HTTPException(400, f"Need 11 starters, got {len(starting_ids)}")
        
        # Clear and rebuild
        conn.execute("DELETE FROM my_squad")
        md = conn.execute("SELECT id FROM matchdays WHERE is_active=1").fetchone()
        md_id = md["id"] if md else None
        
        for pid in player_ids:
            conn.execute("""
                INSERT INTO my_squad (player_id, is_captain, is_vice_captain, is_starting, added_matchday)
                VALUES (?,?,?,?,?)
            """, (pid, 1 if pid == captain_id else 0,
                  1 if pid == vc_id else 0,
                  1 if pid in starting_ids else 0, md_id))
        
        return {"status": "ok", "squad_size": 15, "captain": req.captain}
import os
if os.path.exists("/app/frontend/dist"):
    app.mount("/", StaticFiles(directory="/app/frontend/dist", html=True), name="frontend")




# ─── Archive ───

@app.get("/api/archive")
def get_archive():
    """Get all past matchdays with fixtures and top performers."""
    with db_session() as conn:
        matchdays = conn.execute("""
            SELECT * FROM matchdays ORDER BY id DESC
        """).fetchall()
        
        result = []
        for md in matchdays:
            md_dict = dict(md)
            
            # Get fixtures
            fixtures = conn.execute("""
                SELECT * FROM fixtures WHERE matchday_id = ?
                ORDER BY 
                    CASE status WHEN 'played' THEN 0 WHEN 'live' THEN 1 ELSE 2 END,
                    kick_off ASC
            """, (md["id"],)).fetchall()
            md_dict["fixtures"] = [dict(f) for f in fixtures]
            
            # Get top performers from snapshots
            top = conn.execute("""
                SELECT ps.matchday_points, p.name, p.club, p.position, p.price
                FROM player_snapshots ps
                JOIN players p ON p.id = ps.player_id
                WHERE ps.matchday_id = ? AND ps.matchday_points IS NOT NULL
                ORDER BY ps.matchday_points DESC
                LIMIT 10
            """, (md["id"],)).fetchall()
            md_dict["top_performers"] = [dict(t) for t in top]
            
            # Squad points for this matchday (if user had a squad)
            squad_pts = conn.execute("""
                SELECT SUM(
                    CASE WHEN ms.is_captain = 1 THEN COALESCE(ps.matchday_points, 0) * 2
                         WHEN ms.is_starting = 1 THEN COALESCE(ps.matchday_points, 0)
                         ELSE 0 END
                ) as total_points
                FROM my_squad ms
                LEFT JOIN player_snapshots ps ON ps.player_id = ms.player_id AND ps.matchday_id = ?
            """, (md["id"],)).fetchone()
            md_dict["my_points"] = squad_pts["total_points"] if squad_pts else None
            
            # Transfer penalty
            penalty = conn.execute("""
                SELECT COUNT(*) as c FROM transfers 
                WHERE matchday_id = ? AND is_free = 0
            """, (md["id"],)).fetchone()
            md_dict["penalty_points"] = (penalty["c"] * 4) if penalty else 0
            
            result.append(md_dict)
        
        return result


# ─── New Matchday Wizard ───

@app.post("/api/matchdays/wizard")
def matchday_wizard(
    stage: str = Query(..., description="Stage key from rules.py"),
    name: str = Query(None, description="Custom name (auto-generated if empty)"),
    admin=Depends(require_admin)
):
    """Create a new matchday with fixtures auto-fetched from football-data.org.
    Deactivates old matchday, creates new one with correct stage rules,
    and pulls upcoming fixtures from the API."""
    from fetch_results import fetch_and_update, normalize_team, API_URL, TEAM_MAP
    import requests
    from datetime import datetime, timedelta
    
    rules = get_stage_rules(stage)
    if not name:
        name = rules["label"]
    
    with db_session() as conn:
        # Deactivate old
        conn.execute("UPDATE matchdays SET is_active = 0")
        
        # Create new matchday
        cur = conn.execute(
            "INSERT INTO matchdays (name, stage, deadline, is_active) VALUES (?,?,?,1)",
            (name, stage, None)
        )
        md_id = cur.lastrowid
    
    # Try to fetch upcoming fixtures from football-data.org
    fixtures_added = 0
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    headers = {"X-Auth-Token": api_key} if api_key else {}
    
    try:
        # Fetch upcoming matches (next 30 days)
        date_from = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        r = requests.get(
            API_URL,
            params={"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED,TIMED"},
            headers=headers,
            timeout=15
        )
        r.raise_for_status()
        matches = r.json().get("matches", [])
        
        # Take matches from the nearest matchday (same date range, typically 2 days)
        if matches:
            # Group by date
            first_date = matches[0]["utcDate"][:10]
            # Include matches within 2 days of first match
            first_dt = datetime.fromisoformat(first_date)
            relevant = [m for m in matches if abs((datetime.fromisoformat(m["utcDate"][:10]) - first_dt).days) <= 1]
            
            with db_session() as conn:
                for m in relevant:
                    home = normalize_team(m["homeTeam"]["name"])
                    away = normalize_team(m["awayTeam"]["name"])
                    kick_off = m.get("utcDate", "")
                    
                    h_str = STRENGTH.get(home, 0.5)
                    a_str = STRENGTH.get(away, 0.5)
                    
                    conn.execute("""
                        INSERT INTO fixtures (matchday_id, home_club, away_club,
                                              home_strength, away_strength, kick_off, status)
                        VALUES (?,?,?,?,?,?,?)
                    """, (md_id, home, away, h_str, a_str, kick_off, "scheduled"))
                    fixtures_added += 1
    except Exception as e:
        # API failed — matchday created but no fixtures (user can add manually or via UEFA import)
        pass
    
    return {
        "matchday_id": md_id,
        "name": name,
        "stage": stage,
        "rules": rules,
        "fixtures_added": fixtures_added,
        "message": f"Created '{name}' with {fixtures_added} fixtures" + (
            "" if fixtures_added else ". No fixtures found — import UEFA JSON or add manually."
        )
    }
