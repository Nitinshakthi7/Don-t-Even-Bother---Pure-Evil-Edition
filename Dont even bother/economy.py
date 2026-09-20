# I am adding comments for me to easily understand the codes
# economy.py - how much Spite a run is worth.
#
# Kept away from the save file and the scenes on purpose: these are pure
# functions over plain numbers, so the payout rules can be tested without
# starting pygame or touching anyone's progress.

from settings import PAYOUT, FEW_DEATHS, BRUTAL_PAYOUT, DEATH_PAYOUT_CAP


def clear_payout(deaths, first_clear, new_best_time, act_finished, brutal=False):
    """What a finished level pays, as a list of (reason, amount) lines.

    The lines are what the level-complete screen shows, so the player can see
    exactly why a run paid what it did - a total on its own feels arbitrary.
    """
    lines = []
    if first_clear:
        lines.append(("LEVEL CLEARED", PAYOUT["clear"]))
    if deaths == 0:
        lines.append(("NOT ONE DEATH", PAYOUT["deathless"]))
    elif deaths <= FEW_DEATHS:
        lines.append((f"{deaths} DEATHS OR FEWER", PAYOUT["few_deaths"]))
    if new_best_time and not first_clear:
        lines.append(("NEW BEST TIME", PAYOUT["best_time"]))
    if act_finished:
        lines.append(("ACT COMPLETE", PAYOUT["act"]))
    if brutal and lines:
        total = sum(amount for _, amount in lines)
        lines.append(("BRUTAL", int(total * BRUTAL_PAYOUT) - total))
    return lines


def total_of(lines):
    return sum(amount for _, amount in lines)


def death_payout(paid_this_session):
    """Dying pays a single coin, and stops paying once the session cap is hit."""
    if paid_this_session >= DEATH_PAYOUT_CAP:
        return 0
    return PAYOUT["death"]
