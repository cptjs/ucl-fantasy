"""
Fixture Difficulty Engine
Rates opponents 1-5 stars. Used for calendar view and transfer planning.
"""

# Club strength ratings mapped to our DB club names
CLUB_STRENGTH = {
    # Tier 5 - Elite
    "Real Madrid": 5.0, "Man City": 5.0, "Bayern München": 5.0,
    "Liverpool": 5.0, "Arsenal": 4.8,
    # Tier 4 - Strong
    "Barcelona": 4.5, "Inter": 4.5, "Leverkusen": 4.5,
    "Paris": 4.3, "Atleti": 4.2, "B. Dortmund": 4.0,
    "Juventus": 4.0,
    # Tier 3 - Competitive
    "Atalanta": 3.8, "Benfica": 3.5, "Sporting CP": 3.5,
    "Lille": 3.3, "Monaco": 3.2, "Newcastle": 3.2,
    "Club Brugge": 3.0, "PSV": 3.0, "Feyenoord": 3.0,
    "Stuttgart": 3.0, "Bologna": 3.0,
    # Tier 2 - Underdogs
    "Celtic": 2.5, "Galatasaray": 2.8,
    "Olympiacos": 2.5, "Shakhtar": 2.5,
    # Tier 1 - Minnows
    "Bodø/Glimt": 2.0, "Qarabağ": 1.5,
    "Slovan Bratislava": 1.5, "Young Boys": 2.0,
}

DEFAULT_STRENGTH = 3.0


def get_club_strength(club_name):
    """Get club strength 1-5. Tries exact match, then fuzzy."""
    if club_name in CLUB_STRENGTH:
        return CLUB_STRENGTH[club_name]
    # Fuzzy match
    lower = club_name.lower()
    for key, val in CLUB_STRENGTH.items():
        if key.lower() in lower or lower in key.lower():
            return val
    return DEFAULT_STRENGTH


def fixture_difficulty(opponent, is_home):
    """
    Difficulty rating 1-5 for a fixture.
    1 = very easy (weak team at home)
    5 = very hard (elite team away)
    """
    strength = get_club_strength(opponent)
    diff = strength
    if is_home:
        diff -= 0.5
    else:
        diff += 0.5
    return max(1, min(5, round(diff)))


def difficulty_color(rating):
    """CSS color class for difficulty rating."""
    if rating <= 2:
        return "bg-green-500"   # easy
    if rating <= 3:
        return "bg-yellow-500"  # medium
    if rating <= 4:
        return "bg-orange-500"  # hard
    return "bg-red-500"         # very hard


def difficulty_label(rating):
    if rating <= 1.5:
        return "Very Easy"
    if rating <= 2.5:
        return "Easy"
    if rating <= 3.5:
        return "Medium"
    if rating <= 4.5:
        return "Hard"
    return "Very Hard"
