"""
UCL Fantasy Football Rules Engine
All stage-dependent rules in one place.
"""

# Each matchday has its own transfer rules
# Knockout stages have separate rules for 1st leg and 2nd leg
MATCHDAY_RULES = {
    # League Phase: MD 1-8
    "league_phase": {
        "budget": 100.0,
        "max_per_club": 3,
        "transfer_penalty": 4,
        "can_carry_forward": True,  # 1 unused transfer carries to next MD
        "max_carry": 1,
    },
    # Knockout play-offs
    "ko_playoffs": {
        "budget": 105.0,
        "max_per_club": 4,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    "ko_playoffs_leg2": {
        "budget": 105.0,
        "max_per_club": 4,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    # Round of 16
    "round_of_16": {
        "budget": 105.0,
        "max_per_club": 4,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    "round_of_16_leg2": {
        "budget": 105.0,
        "max_per_club": 4,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    # Quarter-finals
    "quarter_finals": {
        "budget": 105.0,
        "max_per_club": 5,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    "quarter_finals_leg2": {
        "budget": 105.0,
        "max_per_club": 5,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    # Semi-finals
    "semi_finals": {
        "budget": 105.0,
        "max_per_club": 6,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    "semi_finals_leg2": {
        "budget": 105.0,
        "max_per_club": 6,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
    # Final
    "final": {
        "budget": 105.0,
        "max_per_club": 8,
        "transfer_penalty": 4,
        "can_carry_forward": False,
    },
}

# Free transfers per matchday transition
# "before_X" = transfers available before that matchday
FREE_TRANSFERS = {
    "before_league_phase": "unlimited",
    "league_phase": 2,  # per matchday, can carry 1
    "before_ko_playoffs": "unlimited",
    "ko_playoffs_leg2": 2,
    "before_round_of_16": "unlimited",
    "round_of_16_leg2": 3,
    "quarter_finals": 5,
    "quarter_finals_leg2": 3,
    "semi_finals": 5,
    "semi_finals_leg2": 3,
    "final": 5,
}

# Stage labels
STAGE_LABELS = {
    "league_phase": "League Phase",
    "ko_playoffs": "Knockout Play-offs (Leg 1)",
    "ko_playoffs_leg2": "Knockout Play-offs (Leg 2)",
    "round_of_16": "Round of 16 (Leg 1)",
    "round_of_16_leg2": "Round of 16 (Leg 2)",
    "quarter_finals": "Quarter-finals (Leg 1)",
    "quarter_finals_leg2": "Quarter-finals (Leg 2)",
    "semi_finals": "Semi-finals (Leg 1)",
    "semi_finals_leg2": "Semi-finals (Leg 2)",
    "final": "Final",
}

# Mid-matchday rules
MID_MATCHDAY = {
    "max_subs_per_day": 4,  # max manual subs between days
    "can_change_captain": True,  # can switch to player whose team hasn't played
    "auto_subs_disabled_on_manual_change": True,
}


def get_stage_rules(stage: str) -> dict:
    """Get rules for a given stage."""
    base = MATCHDAY_RULES.get(stage, MATCHDAY_RULES["league_phase"])
    ft = FREE_TRANSFERS.get(stage, 2)
    label = STAGE_LABELS.get(stage, stage)
    return {
        **base,
        "free_transfers": ft,
        "label": label,
        "stage": stage,
        "mid_matchday": MID_MATCHDAY,
    }


def get_all_stages():
    """Return all stages summary."""
    result = {}
    for stage in STAGE_LABELS:
        rules = get_stage_rules(stage)
        result[stage] = {
            "label": rules["label"],
            "budget": rules["budget"],
            "max_per_club": rules["max_per_club"],
            "free_transfers": rules["free_transfers"],
        }
    return result


# Keep backward compat
STAGES = {k: get_stage_rules(k) for k in STAGE_LABELS}
