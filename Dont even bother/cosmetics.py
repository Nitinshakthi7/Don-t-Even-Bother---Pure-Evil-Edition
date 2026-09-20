# I am adding comments for me to easily understand the codes
# cosmetics.py - the skins you can wear.
#
# A skin is pure data. The player is drawn in code from a few colours, so a
# skin is a handful of numbers rather than an image, which is why there can be
# a lot of them without the game growing at all.
#
# NOTHING in here touches the rules. A skin changes how you look and nothing
# else: no hitbox, no speed, no jump height. If a skin ever changed how the
# game plays, every "this game is unfair" complaint would have a new target.

from dataclasses import dataclass

from settings import PLAYER_BODY, PLAYER_OUTLINE, PLAYER_SCARF, INK


@dataclass(frozen=True)
class Skin:
    id: str
    name: str
    body: tuple
    scarf: tuple
    outline: tuple = PLAYER_OUTLINE
    eyes: tuple = INK
    sole: tuple = (222, 214, 200)     # the little shoe strip along the bottom
    cost: int = 0                     # 0 means it cannot be bought, only earned
    how: str = ""                     # what you have to do to earn it
    achievement: str = None           # the achievement id that unlocks it


DEFAULT = Skin("default", "THE BLANK", PLAYER_BODY, PLAYER_SCARF, how="You start with this one.")

SKINS = [
    DEFAULT,
    # ---------------------------------------------------------------- earned
    Skin("regular", "THE REGULAR", (198, 196, 205), (150, 150, 160), sole=(170, 168, 176),
         how="Die 100 times.", achievement="deaths_100"),
    Skin("gravedigger", "GRAVEDIGGER", (96, 100, 110), (60, 180, 120), sole=(70, 74, 84),
         how="Die 1,000 times.", achievement="deaths_1000"),
    Skin("untouchable", "UNTOUCHABLE", (255, 252, 240), (255, 204, 77), sole=(240, 232, 200),
         how="Clear any level without dying.", achievement="deathless"),
    Skin("gullible", "GULLIBLE", (232, 210, 160), (196, 120, 60), sole=(210, 188, 140),
         how="Die to ten fake doors.", achievement="fake_doors_10"),
    Skin("connoisseur", "CONNOISSEUR", (210, 170, 235), (120, 60, 180), sole=(185, 150, 205),
         how="Die to every cause at least once.", achievement="every_cause"),
    Skin("masochist", "MASOCHIST", (60, 58, 70), (214, 36, 56), sole=(44, 42, 52),
         how="Finish Act I on Brutal.", achievement="act1_brutal"),
    Skin("summiteer", "SUMMITEER", (170, 215, 255), (255, 255, 255), sole=(140, 185, 225),
         how="Reach the top of the Climb.", achievement="climb_done"),
    Skin("ghost", "THE GHOST", (200, 225, 235), (120, 200, 220), outline=(40, 70, 90),
         sole=(170, 200, 212), eyes=(40, 70, 90),
         how="Beat the bot's time on any level.", achievement="beat_ghost"),
    Skin("completionist", "COMPLETIONIST", (255, 215, 90), (60, 40, 10), sole=(226, 186, 70),
         how="Finish every level in both modes.", achievement="all_levels"),
    # ------------------------------------------------------------------ shop
    Skin("ember", "EMBER", (255, 140, 70), (120, 30, 20), sole=(226, 118, 56), cost=150,
         how="Bought with spite."),
    Skin("frost", "FROST", (190, 235, 255), (70, 130, 200), sole=(160, 205, 228), cost=150,
         how="Bought with spite."),
    Skin("neon", "NEON", (255, 70, 200), (60, 240, 220), sole=(220, 60, 175), cost=250,
         how="Bought with spite."),
    Skin("void", "VOID", (28, 26, 38), (90, 60, 160), outline=(8, 6, 14), sole=(20, 18, 28), cost=400,
         how="Bought with spite."),
]

BY_ID = {skin.id: skin for skin in SKINS}


def get(skin_id):
    return BY_ID.get(skin_id, DEFAULT)


def equipped(save):
    """The skin the player is wearing, falling back to the default."""
    worn = save.data["cosmetics"].get("equipped", DEFAULT.id)
    if worn not in unlocked_ids(save):
        return DEFAULT
    return get(worn)


def unlocked_ids(save):
    return set(save.data["cosmetics"].get("unlocked", [DEFAULT.id])) | {DEFAULT.id}


def is_unlocked(save, skin):
    return skin.id in unlocked_ids(save)


def unlock(save, skin_id):
    """Give the player a skin. Returns True if it was not already theirs."""
    owned = save.data["cosmetics"].setdefault("unlocked", [DEFAULT.id])
    if skin_id in owned:
        return False
    owned.append(skin_id)
    save.dirty = True
    save.save()
    return True


def buy(save, skin):
    """Spend spite on a shop skin. Returns True only if the purchase happened."""
    if skin.cost <= 0 or is_unlocked(save, skin):
        return False
    if not save.spend_spite(skin.cost):
        return False
    unlock(save, skin.id)
    return True


def equip(save, skin_id):
    if skin_id not in unlocked_ids(save):
        return False
    save.data["cosmetics"]["equipped"] = skin_id
    save.save()
    return True
