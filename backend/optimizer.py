"""
Squad Optimizer using Integer Linear Programming.
Builds optimal 15-man squad under UCL Fantasy constraints.
"""

from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus
from dataclasses import dataclass
from scoring import Position
from predictor import Prediction


@dataclass
class SquadConstraints:
    budget: float = 100.0  # millions
    max_per_club: int = 3  # league phase default
    squad_size: int = 15
    gk_count: int = 2
    def_count: int = 5
    mid_count: int = 5
    fwd_count: int = 3


@dataclass
class OptimizedSquad:
    squad: list[Prediction]
    starting_xi: list[Prediction]
    bench: list[Prediction]
    captain: Prediction
    total_expected: float
    total_cost: float
    formation: str  # e.g. "3-4-3"


def optimize_squad(
    predictions: list[Prediction],
    constraints: SquadConstraints = SquadConstraints(),
    risk_profile: str = "balanced",  # safe, balanced, aggressive
) -> OptimizedSquad | None:
    """
    Find optimal 15-man squad using ILP.
    Risk profiles:
    - safe: penalize high-risk players
    - balanced: as-is expected points
    - aggressive: boost high-ceiling players (differential picks)
    """
    prob = LpProblem("UCL_Fantasy_Squad", LpMaximize)

    # Filter out unavailable
    players = [p for p in predictions if p.expected_points > 0]

    # Decision variables: 1 if player is in squad
    x = {p.player_id: LpVariable(f"x_{p.player_id}", cat="Binary") for p in players}

    # Adjust points by risk profile
    def adjusted_points(p: Prediction) -> float:
        base = p.expected_points
        if risk_profile == "safe":
            # Heavily penalize risky players, reward consistent ones
            if p.risk_level == "high":
                base *= 0.3
            elif p.risk_level == "medium":
                base *= 0.7
            if p.confidence == "high":
                base *= 1.2
            elif p.confidence == "low":
                base *= 0.6
        elif risk_profile == "aggressive":
            # Boost high-ceiling differentials, penalize safe picks
            if p.risk_level == "high":
                base *= 1.4
            elif p.risk_level == "low":
                base *= 0.85
            if p.confidence == "low":
                base *= 1.3  # differential boost
            # Favor cheaper high-upside players
            base += p.points_per_million * 0.3
        return base

    # Objective: maximize total expected points
    prob += lpSum(adjusted_points(p) * x[p.player_id] for p in players)

    # Budget constraint
    prob += lpSum(p.price * x[p.player_id] for p in players) <= constraints.budget

    # Squad size
    prob += lpSum(x[p.player_id] for p in players) == constraints.squad_size

    # Position constraints
    for pos, count in [
        (Position.GK, constraints.gk_count),
        (Position.DEF, constraints.def_count),
        (Position.MID, constraints.mid_count),
        (Position.FWD, constraints.fwd_count),
    ]:
        prob += lpSum(x[p.player_id] for p in players if p.position == pos) == count

    # Club limit
    clubs = set(p.club for p in players)
    for club in clubs:
        prob += lpSum(x[p.player_id] for p in players if p.club == club) <= constraints.max_per_club

    # Solve
    prob.solve()

    if LpStatus[prob.status] != "Optimal":
        return None

    # Extract squad
    squad = [p for p in players if x[p.player_id].varValue == 1]
    squad.sort(key=lambda p: (-adjusted_points(p)))

    # Pick starting XI (best 11 with valid formation: 1 GK, 3+ DEF, 2+ MID, 1+ FWD)
    starting_xi = _pick_starting_xi(squad)
    bench = [p for p in squad if p not in starting_xi]

    # Captain = highest expected points in starting XI
    captain = max(starting_xi, key=lambda p: p.expected_points)

    # Determine formation
    def_count = sum(1 for p in starting_xi if p.position == Position.DEF)
    mid_count = sum(1 for p in starting_xi if p.position == Position.MID)
    fwd_count = sum(1 for p in starting_xi if p.position == Position.FWD)
    formation = f"{def_count}-{mid_count}-{fwd_count}"

    total_exp = sum(p.expected_points for p in starting_xi) + captain.expected_points  # captain x2
    total_cost = sum(p.price for p in squad)

    return OptimizedSquad(
        squad=squad,
        starting_xi=starting_xi,
        bench=bench,
        captain=captain,
        total_expected=round(total_exp, 2),
        total_cost=round(total_cost, 2),
        formation=formation,
    )


def _pick_starting_xi(squad: list[Prediction]) -> list[Prediction]:
    """Pick best 11 from 15 satisfying min formation: 1 GK, 3 DEF, 2 MID, 1 FWD."""
    by_pos = {pos: [] for pos in Position}
    for p in squad:
        by_pos[p.position].append(p)

    for pos in by_pos:
        by_pos[pos].sort(key=lambda p: -p.expected_points)

    # Mandatory minimums
    xi = []
    xi.append(by_pos[Position.GK][0])  # 1 GK
    xi.extend(by_pos[Position.DEF][:3])  # 3 DEF
    xi.extend(by_pos[Position.MID][:2])  # 2 MID
    xi.extend(by_pos[Position.FWD][:1])  # 1 FWD

    # Fill remaining 4 spots with best available (max 1 GK in XI)
    remaining = [p for p in squad if p not in xi]
    remaining.sort(key=lambda p: -p.expected_points)

    for p in remaining:
        if len(xi) >= 11:
            break
        # Don't add second GK to starting XI
        if p.position == Position.GK:
            continue
        xi.append(p)

    return xi
