"""
Expected Fantasy Points Predictor v3

Primary signal: player's average points per GAME PLAYED (not per matchday).
Adjusted by fixture difficulty, home/away, price quality signal.

Note: predictions are EXPECTED VALUES. A prediction of 7 means "on average 
this player scores 7 in this type of fixture". Actual results will vary 
widely (2-20+) due to variance. The value is in RANKING players correctly,
not predicting exact scores.
"""

from dataclasses import dataclass, field
from scoring import Position


@dataclass
class PlayerProfile:
    player_id: int
    name: str
    club: str
    position: Position
    price: float
    avg_minutes_last5: float = 0
    avg_points_last5: float = 0
    total_goals: int = 0
    total_assists: int = 0
    total_clean_sheets: int = 0
    matches_played: int = 0
    is_starter: bool = True
    is_set_piece_taker: bool = False
    injury_status: str = "fit"


@dataclass
class FixtureInfo:
    opponent_club: str
    opponent_strength: float
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
    confidence: str
    points_per_million: float = 0
    risk_level: str = "medium"
    reasoning: list[str] = field(default_factory=list)


# Fallback when no avg data (by position, for a "generic" starter)
POSITION_BASELINE = {
    Position.GK: 5.0,
    Position.DEF: 5.0,
    Position.MID: 5.0,
    Position.FWD: 4.5,
}


def _estimate_base(player: PlayerProfile) -> tuple[float, str]:
    """
    Core prediction base. Uses avg_points as primary signal.
    Falls back to price-based estimate if no data.
    """
    avg = player.avg_points_last5
    mp = player.matches_played
    
    if mp >= 2 and avg > 0:
        # avg_points from UEFA is already per-game. Use it directly.
        base = avg
        
        # But supplement with price signal for context:
        # If a €10M player averages only 3pts, trust the average mostly
        # but acknowledge price implies quality (blend slightly)
        price_expected = 2.5 + player.price * 0.6  # €5M→5.5, €8M→7.3, €10M→8.5
        
        # Blend: 75% actual avg, 25% price expectation
        if mp >= 5:
            blended = avg * 0.80 + price_expected * 0.20
        else:
            blended = avg * 0.65 + price_expected * 0.35  # less data → lean more on price
        
        return blended, f"Avg: {avg:.1f} pts/game ({mp}gp), price adj → {blended:.1f}"
    
    # No history: use price as primary signal
    price_expected = 2.5 + player.price * 0.6
    base = max(price_expected, POSITION_BASELINE[player.position])
    return base, f"Est: {base:.1f} (no history, €{player.price}M)"


def _fixture_modifier(fixture: FixtureInfo, position: Position) -> tuple[float, str]:
    """
    Fixture difficulty creates the spread between matchdays.
    
    Scale: 0.65x (vs Real Madrid away) to 1.50x (vs Qarabağ home)
    """
    opp = fixture.opponent_strength
    
    # Core modifier: weaker opponent = higher multiplier
    # opp=0.3 → 1.40, opp=0.5 → 1.00, opp=0.7 → 0.80, opp=0.95 → 0.63
    mod = 1.0 + (0.5 - opp) * 2.0
    
    # Attackers swing more with fixture difficulty
    if position in (Position.FWD, Position.MID):
        extra = (0.5 - opp) * 0.3  # FWD/MID get extra boost vs weak teams
        mod += max(0, extra)
    
    # Defenders: clean sheet boost vs weak teams
    if position in (Position.GK, Position.DEF):
        cs_extra = (0.5 - opp) * 0.25
        mod += max(0, cs_extra)
    
    # Home advantage
    home_bonus = 0.08 if fixture.is_home else 0
    mod += home_bonus
    
    # Knockout intensity
    if fixture.is_knockout:
        mod *= 1.04
    
    mod = max(0.60, min(1.55, mod))
    
    loc = "🏠" if fixture.is_home else "✈️"
    difficulty = "easy" if opp < 0.4 else "medium" if opp < 0.7 else "hard"
    return mod, f"{loc} vs {fixture.opponent_club} ({difficulty}): x{mod:.2f}"


def _minutes_probability(player: PlayerProfile) -> float:
    if player.injury_status == "out":
        return 0.0
    if player.injury_status == "doubt":
        return 0.25
    if not player.is_starter:
        return 0.30
    if player.avg_minutes_last5 >= 80:
        return 0.95
    if player.avg_minutes_last5 >= 60:
        return 0.85
    if player.avg_minutes_last5 >= 30:
        return 0.55
    if player.matches_played == 0:
        return 0.70 if player.is_starter else 0.30
    return 0.45


def predict_points(player: PlayerProfile, fixture: FixtureInfo) -> Prediction:
    reasons = []

    min_prob = _minutes_probability(player)
    if min_prob == 0:
        return Prediction(
            player_id=player.player_id, name=player.name,
            position=player.position, club=player.club, price=player.price,
            expected_points=0, confidence="high", risk_level="high",
            reasoning=["Injured / unavailable"]
        )

    # 1. Base from avg_points + price signal
    base, base_reason = _estimate_base(player)
    reasons.append(base_reason)

    # 2. Fixture modifier (biggest differentiator)
    fix_mod, fix_reason = _fixture_modifier(fixture, player.position)
    reasons.append(fix_reason)

    pts = base * fix_mod

    # 3. Set piece taker: more chances for assists/goals
    if player.is_set_piece_taker:
        sp_bonus = 1.2 + max(0, (0.5 - fixture.opponent_strength)) * 0.8
        pts += sp_bonus
        reasons.append(f"Set pieces: +{sp_bonus:.1f}")

    # 4. Upside factor: UCL Fantasy points are right-skewed.
    # Players often score above their average due to haul potential.
    # Model "expected if things go well" rather than pure mean.
    # This makes predictions more useful for squad decisions.
    upside = 1.35  # ~35% above pure mean (approximates 65th percentile)
    
    # Higher-priced players have more upside (they're priced for explosiveness)
    if player.price >= 8:
        upside += 0.08
    elif player.price >= 6:
        upside += 0.04
    
    pts *= upside

    # 5. Apply minutes probability
    expected = pts * min_prob

    # Sub cameo chance
    if 0 < min_prob < 0.5:
        expected += (1 - min_prob) * 0.15 * 1.5

    reasons.append(f"Mins prob: {min_prob:.0%}")

    # Confidence & risk
    if player.matches_played >= 5 and min_prob > 0.8:
        confidence = "high"
    elif player.matches_played >= 2 and min_prob > 0.5:
        confidence = "medium"
    else:
        confidence = "low"

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
