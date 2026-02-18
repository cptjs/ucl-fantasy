"""
UCL Fantasy Football Scoring Engine
Full implementation of UEFA Champions League Fantasy scoring rules.
"""

from enum import Enum
from dataclasses import dataclass


class Position(str, Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


@dataclass
class MatchStats:
    """Raw match statistics for a single player in a single match."""
    player_id: int
    position: Position
    minutes: int = 0
    goals: int = 0
    goals_outside_box: int = 0
    assists: int = 0
    balls_recovered: int = 0
    player_of_match: bool = False
    penalty_won: int = 0
    penalty_conceded: int = 0
    penalty_missed: int = 0
    penalty_saved: int = 0
    yellow_card: bool = False
    red_card: bool = False
    own_goal: int = 0
    saves: int = 0
    goals_conceded: int = 0
    clean_sheet: bool = False


def calculate_fantasy_points(stats: MatchStats) -> int:
    """Calculate fantasy points based on UCL Fantasy rules."""
    pts = 0

    # Appearance
    if stats.minutes > 0:
        pts += 1
    # 60+ minutes
    if stats.minutes >= 60:
        pts += 1

    # Goals by position
    goal_pts = {Position.GK: 6, Position.DEF: 6, Position.MID: 5, Position.FWD: 4}
    pts += stats.goals * goal_pts[stats.position]

    # Goals from outside box
    pts += stats.goals_outside_box

    # Assists
    pts += stats.assists * 3

    # Balls recovered (every 3)
    pts += stats.balls_recovered // 3

    # Player of the Match
    if stats.player_of_match:
        pts += 3

    # Penalties
    pts += stats.penalty_won * 2
    pts -= stats.penalty_conceded
    pts -= stats.penalty_missed * 2

    # Cards
    if stats.red_card:
        pts -= 3
    elif stats.yellow_card:
        pts -= 1

    # Own goals
    pts -= stats.own_goal * 2

    # GK specific
    if stats.position == Position.GK:
        pts += stats.penalty_saved * 5
        if stats.clean_sheet:
            pts += 4
        pts += stats.saves // 3
        pts -= stats.goals_conceded // 2

    # DEF specific
    if stats.position == Position.DEF:
        if stats.clean_sheet:
            pts += 4
        pts -= stats.goals_conceded // 2

    # MID specific
    if stats.position == Position.MID:
        if stats.clean_sheet:
            pts += 1

    return pts
