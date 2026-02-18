"""
Expected Fantasy Points Predictor
Weighted heuristic approach for MVP.
"""

from dataclasses import dataclass, field
from typing import Optional
from scoring import Position


@dataclass
class PlayerProfile:
    player_id: int
    name: str
    club: str
    position: Position
    price: float  # in millions
    avg_minutes_last5: float = 0
    avg_points_last5: float = 0
    total_goals: int = 0
    total_assists: int = 0
    total_clean_sheets: int = 0
    matches_played: int = 0
    is_starter: bool = True
    is_set_piece_taker: bool = False
    injury_status: str = "fit"  # fit, doubt, out


@dataclass
class FixtureInfo:
    opponent_club: str
    opponent_strength: float  # 0-1 scale, 1 = strongest
    is_home: bool = True
    is_knockout: bool = False


@dataclass
class Prediction:
    player_id: int
    name: str
    position: Position
    club: str
    price: float
    expected_points: float
    confidence: str  # high, medium, low
    points_per_million: float = 0
    risk_level: str = "medium"  # low, medium, high
    reasoning: list[str] = field(default_factory=list)


# Base expected points by position (league phase averages)
BASE_POINTS = {
    Position.GK: 3.5,
    Position.DEF: 3.8,
    Position.MID: 3.5,
    Position.FWD: 3.2,
}

# Opponent strength modifier (-30% to +30%)
def _fixture_modifier(fixture: FixtureInfo, position: Position) -> float:
    """Easier fixture = more points expected."""
    # Attacking players benefit more from weak opponents
    base = 1.0 - (fixture.opponent_strength - 0.5) * 0.6
    if position in (Position.FWD, Position.MID):
        base += (1 - fixture.opponent_strength) * 0.15
    # Home advantage
    if fixture.is_home:
        base += 0.08
    # Knockout intensity
    if fixture.is_knockout:
        base *= 1.05  # slightly higher scoring
    return max(0.5, min(1.5, base))


def _form_modifier(player: PlayerProfile) -> float:
    """Recent form adjustment."""
    if player.matches_played == 0:
        return 0.8
    base = player.avg_points_last5 / max(BASE_POINTS[player.position], 1)
    return max(0.6, min(1.5, base))


def _minutes_probability(player: PlayerProfile) -> float:
    """Probability of playing 60+ minutes."""
    if player.injury_status == "out":
        return 0.0
    if player.injury_status == "doubt":
        return 0.3
    if not player.is_starter:
        return 0.35
    if player.avg_minutes_last5 >= 80:
        return 0.92
    if player.avg_minutes_last5 >= 60:
        return 0.80
    return 0.55


def predict_points(player: PlayerProfile, fixture: FixtureInfo) -> Prediction:
    """Predict expected fantasy points for a player in a specific fixture."""
    reasons = []

    # Start probability
    min_prob = _minutes_probability(player)
    if min_prob == 0:
        return Prediction(
            player_id=player.player_id, name=player.name,
            position=player.position, club=player.club, price=player.price,
            expected_points=0, confidence="high", risk_level="high",
            reasoning=["Player is injured/unavailable"]
        )

    # Base points
    base = BASE_POINTS[player.position]
    reasons.append(f"Base for {player.position.value}: {base:.1f}")

    # Fixture modifier
    fix_mod = _fixture_modifier(fixture, player.position)
    reasons.append(f"Fixture vs {fixture.opponent_club}: x{fix_mod:.2f}")

    # Form modifier
    form_mod = _form_modifier(player)
    if player.matches_played > 0:
        reasons.append(f"Form (avg {player.avg_points_last5:.1f}pts last 5): x{form_mod:.2f}")

    # Set piece bonus
    sp_bonus = 0
    if player.is_set_piece_taker:
        sp_bonus = 0.8
        reasons.append("Set piece taker: +0.8")

    # Calculate
    raw = base * fix_mod * form_mod + sp_bonus
    expected = raw * min_prob
    reasons.append(f"Minutes probability: {min_prob:.0%}")

    # Confidence
    if player.matches_played >= 5 and min_prob > 0.8:
        confidence = "high"
    elif player.matches_played >= 2 and min_prob > 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    # Risk
    if min_prob < 0.5 or player.injury_status == "doubt":
        risk = "high"
    elif min_prob < 0.8 or player.matches_played < 3:
        risk = "medium"
    else:
        risk = "low"

    return Prediction(
        player_id=player.player_id,
        name=player.name,
        position=player.position,
        club=player.club,
        price=player.price,
        expected_points=round(expected),
        points_per_million=round(expected / max(player.price, 0.1), 1),
        confidence=confidence,
        risk_level=risk,
        reasoning=reasons,
    )
