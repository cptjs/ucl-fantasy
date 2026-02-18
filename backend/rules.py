"""
UCL Fantasy Football Rules Engine
All stage-dependent rules in one place.
"""

STAGES = {
    "league_phase": {
        "budget": 100.0,
        "max_per_club": 3,
        "free_transfers": 2,  # per matchday
        "transfer_penalty": 4,
        "label": "League Phase",
        "matchdays": list(range(1, 9)),  # MD 1-8
    },
    "ko_playoffs": {
        "budget": 105.0,
        "max_per_club": 4,
        "free_transfers": 2,
        "transfer_penalty": 4,
        "unlimited_transfers_before": True,  # unlimited free before this stage
        "label": "Knockout Play-offs",
        "matchdays": [9, 10],  # 2 legs
    },
    "round_of_16": {
        "budget": 105.0,
        "max_per_club": 4,
        "free_transfers": 2,
        "transfer_penalty": 4,
        "unlimited_transfers_before": True,
        "label": "Round of 16",
        "matchdays": [11, 12],
    },
    "quarter_finals": {
        "budget": 105.0,
        "max_per_club": 5,
        "free_transfers": 2,
        "transfer_penalty": 4,
        "label": "Quarter-finals",
        "matchdays": [13, 14],
    },
    "semi_finals": {
        "budget": 105.0,
        "max_per_club": 6,
        "free_transfers": 2,
        "transfer_penalty": 4,
        "label": "Semi-finals",
        "matchdays": [15, 16],
    },
    "final": {
        "budget": 105.0,
        "max_per_club": 8,
        "free_transfers": 2,
        "transfer_penalty": 4,
        "label": "Final",
        "matchdays": [17],
    },
}


def get_stage_rules(stage: str) -> dict:
    """Get rules for a given stage."""
    return STAGES.get(stage, STAGES["league_phase"])


def get_all_stages():
    """Return all stages with their rules."""
    return STAGES
