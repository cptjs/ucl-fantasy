
# Club strength ratings (1 = Weakest, 5 = Strongest)
# Based on UEFA coefficient / general perception for 2024/25 season

CLUB_STRENGTH = {
    # Tier 1 - Contenders
    "Manchester City": 5,
    "Real Madrid": 5,
    "Bayern München": 5,
    "Liverpool": 5,
    "Arsenal": 5,
    "Inter": 4.5,
    "Barcelona": 4.5,
    "Bayer Leverkusen": 4.5,

    # Tier 2 - Strong
    "Paris Saint-Germain": 4,
    "Atlético Madrid": 4,
    "Borussia Dortmund": 4,
    "Juventus": 4,
    "Milan": 3.5,
    "Atalanta": 3.5,
    "Aston Villa": 3.5,
    "Benfica": 3.5,
    "Sporting CP": 3.5,
    
    # Tier 3 - Mid table
    "RB Leipzig": 3,
    "PSV Eindhoven": 3,
    "Feyenoord": 3,
    "Club Brugge": 3,
    "Lille": 3,
    "Monaco": 3,
    "Stuttgart": 3,
    "Girona": 3,
    "Bologna": 3,

    # Tier 4 - Underdogs
    "Celtic": 2.5,
    "Shakhtar Donetsk": 2.5,
    "Salzburg": 2.5,
    "Young Boys": 2,
    "Crvena Zvezda": 2,
    "Sparta Praha": 2,
    "Dinamo Zagreb": 2,

    # Tier 5 - Minnows
    "Sturm Graz": 1.5,
    "Brest": 1.5,
    "Slovan Bratislava": 1
}

# Default strength if club not found
DEFAULT_STRENGTH = 2.5

def get_club_strength(club_name):
    """Returns club strength (1-5)."""
    # Normalize name if needed (simple check for now)
    for key, val in CLUB_STRENGTH.items():
        if key.lower() in club_name.lower() or club_name.lower() in key.lower():
            return val
    return DEFAULT_STRENGTH

def calculate_fixture_difficulty(my_club, opponent_club, is_home):
    """
    Calculates difficulty rating (1-5) for a specific fixture.
    Higher number = harder match.
    
    Formula:
    Base difficulty = Opponent Strength
    + 0.5 if playing Away
    - 0.5 if playing Home (advantage)
    
    Returns integer 1-5.
    """
    opp_strength = get_club_strength(opponent_club)
    
    difficulty = opp_strength
    
    if is_home:
        difficulty -= 0.5  # Easier at home
    else:
        difficulty += 0.5  # Harder away
        
    # Clamp to 1-5
    return max(1, min(5, round(difficulty)))
