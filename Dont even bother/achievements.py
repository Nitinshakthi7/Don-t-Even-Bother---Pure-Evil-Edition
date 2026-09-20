# I am adding comments for me to easily understand the codes
# achievements.py - badges of suffering.
#
# Each one is a small function over the save file, so they can all be checked
# after any level without the rest of the game knowing what an achievement is.
# Most of them you get by accident, which is the point: they are a record of
# how you played, not a checklist to grind.

from dataclasses import dataclass

import cosmetics
from settings import TAUNTS_BY_CAUSE

ALL_CAUSES = set(TAUNTS_BY_CAUSE)


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    check: callable
    skin: str = None        # the skin it hands over, if any


def _levels(save, mode):
    return save.data["modes"][mode]["levels"]


def _cleared(save, mode, numbers):
    levels = _levels(save, mode)
    return all(levels.get(str(n), {}).get("completed") for n in numbers)


def _any_level(save, test):
    for mode in ("normal", "brutal"):
        for stats in _levels(save, mode).values():
            if test(stats):
                return True
    return False


ACHIEVEMENTS = [
    Achievement("first_blood", "FIRST BLOOD", "Die once. It won't be the last.",
                lambda save, g: save.data["total_deaths"] >= 1),
    Achievement("deaths_100", "THE REGULAR", "Die 100 times.",
                lambda save, g: save.data["total_deaths"] >= 100, skin="regular"),
    Achievement("deaths_1000", "GRAVEDIGGER", "Die 1,000 times.",
                lambda save, g: save.data["total_deaths"] >= 1000, skin="gravedigger"),
    Achievement("persistent", "PERSISTENT", "Die 50 times on a single level.",
                lambda save, g: _any_level(save, lambda s: s.get("deaths", 0) >= 50)),
    Achievement("deathless", "UNTOUCHABLE", "Clear any level without dying.",
                lambda save, g: _any_level(save, lambda s: s.get("best_deaths") == 0),
                skin="untouchable"),
    Achievement("fake_doors_10", "GULLIBLE", "Fall for ten fake doors.",
                lambda save, g: save.data["death_causes"].get("fake_goal", 0) >= 10,
                skin="gullible"),
    Achievement("every_cause", "CONNOISSEUR", "Die to every cause at least once.",
                lambda save, g: ALL_CAUSES <= set(save.data["death_causes"]),
                skin="connoisseur"),
    Achievement("act1_brutal", "MASOCHIST", "Finish Act I on Brutal.",
                lambda save, g: _cleared(save, "brutal", range(1, 11)), skin="masochist"),
    Achievement("act2_done", "ENDURANCE", "Survive the whole Gauntlet.",
                lambda save, g: (_cleared(save, "normal", range(11, 19))
                                 or _cleared(save, "brutal", range(11, 19)))),
    Achievement("climb_done", "SUMMITEER", "Reach the top of the Climb.",
                lambda save, g: (_levels(save, "normal").get("19", {}).get("completed")
                                 or _levels(save, "brutal").get("19", {}).get("completed")),
                skin="summiteer"),
    Achievement("beat_ghost", "THE GHOST", "Beat the bot's time on any level.",
                lambda save, g: bool(save.data["ghost"]["beaten"]), skin="ghost"),
    Achievement("all_levels", "COMPLETIONIST", "Finish every level, in both modes.",
                lambda save, g: (_cleared(save, "normal", range(1, g + 1))
                                 and _cleared(save, "brutal", range(1, g + 1))),
                skin="completionist"),
]

BY_ID = {a.id: a for a in ACHIEVEMENTS}


def earned(save):
    return set(save.data["achievements"])


def has(save, achievement_id):
    return achievement_id in save.data["achievements"]


def check(save, level_count):
    """Award anything newly deserved. Returns the Achievements just earned.

    Safe to call as often as you like: an achievement is only ever handed over
    once, and it hands over its skin at the same time.
    """
    won = []
    for achievement in ACHIEVEMENTS:
        if has(save, achievement.id):
            continue
        try:
            passed = bool(achievement.check(save, level_count))
        except (AttributeError, KeyError, TypeError, ValueError):
            passed = False          # a half-written save must never crash the game
        if passed:
            save.data["achievements"][achievement.id] = True
            if achievement.skin:
                cosmetics.unlock(save, achievement.skin)
            won.append(achievement)
    if won:
        save.dirty = True
        save.save()
    return won


def progress(save, level_count):
    """How much of the set is done, for the credits screen."""
    return len(earned(save)), len(ACHIEVEMENTS)
