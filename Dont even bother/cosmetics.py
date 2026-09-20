# I am adding comments for me to easily understand the codes
# cosmetics.py - the skins you can wear, and how they are drawn.
#
# A skin is pure data: colours plus a few shape choices (corner rounding, what
# its eyes look like, what sits on its head). Everything is drawn in code, so
# fourteen characters cost a table rather than fourteen sprite sheets.
#
# NOTHING in here touches the rules. A skin changes how you look and nothing
# else: no hitbox, no speed, no jump height. Every skin is drawn inside the
# same 26x34 body, so what you see is always the box the game collides with -
# a costume must never lie about where you are.

from dataclasses import dataclass

import pygame

from settings import PLAYER_BODY, PLAYER_OUTLINE, PLAYER_SCARF, INK, PLAYER_W, PLAYER_H


@dataclass(frozen=True)
class Skin:
    id: str
    name: str
    body: tuple
    scarf: tuple
    outline: tuple = PLAYER_OUTLINE
    eyes: tuple = INK
    sole: tuple = (222, 214, 200)     # the little shoe strip along the bottom
    # --- shape, which is what actually makes them different characters
    radius: int = 8                   # 0 is a blocky robot, 13 is a pill
    look: str = "dots"                # see EYE_STYLES below
    crest: str = None                 # something on its head
    crest_colour: tuple = None        # defaults to the scarf colour
    belt: bool = True                 # the scarf band around the middle
    # --- how you get it
    cost: int = 0                     # 0 means it cannot be bought, only earned
    how: str = ""                     # what you have to do to earn it
    achievement: str = None           # the achievement id that unlocks it


DEFAULT = Skin("default", "THE BLANK", PLAYER_BODY, PLAYER_SCARF, how="You start with this one.")

SKINS = [
    DEFAULT,
    # ---------------------------------------------------------------- earned
    Skin("regular", "THE REGULAR", (198, 196, 205), (150, 150, 160), sole=(170, 168, 176),
         radius=8, look="tired", crest="cap",
         how="Die 100 times.", achievement="deaths_100"),
    Skin("gravedigger", "GRAVEDIGGER", (96, 100, 110), (60, 180, 120), sole=(70, 74, 84),
         radius=1, look="x", crest="cap",
         how="Die 1,000 times.", achievement="deaths_1000"),
    Skin("untouchable", "UNTOUCHABLE", (255, 252, 240), (255, 204, 77), sole=(240, 232, 200),
         radius=13, look="calm", crest="halo",
         how="Clear any level without dying.", achievement="deathless"),
    Skin("gullible", "GULLIBLE", (232, 210, 160), (196, 120, 60), sole=(210, 188, 140),
         radius=11, look="wide", crest=None, belt=False,
         how="Die to ten fake doors.", achievement="fake_doors_10"),
    Skin("connoisseur", "CONNOISSEUR", (210, 170, 235), (120, 60, 180), sole=(185, 150, 205),
         radius=9, look="monocle", crest="tophat",
         how="Die to every cause at least once.", achievement="every_cause"),
    Skin("masochist", "MASOCHIST", (60, 58, 70), (214, 36, 56), sole=(44, 42, 52),
         eyes=(255, 92, 110), radius=3, look="angry", crest="horns",
         how="Finish Act I on Brutal.", achievement="act1_brutal"),
    Skin("summiteer", "SUMMITEER", (170, 215, 255), (255, 255, 255), sole=(140, 185, 225),
         radius=10, look="goggles", crest="bobble",
         how="Reach the top of the Climb.", achievement="climb_done"),
    Skin("ghost", "THE GHOST", (200, 225, 235), (120, 200, 220), outline=(40, 70, 90),
         sole=(170, 200, 212), eyes=(40, 70, 90), radius=13, look="ring", crest=None, belt=False,
         how="Beat the bot's time on any level.", achievement="beat_ghost"),
    Skin("completionist", "COMPLETIONIST", (255, 215, 90), (60, 40, 10), sole=(226, 186, 70),
         radius=6, look="calm", crest="crown",
         how="Finish every level in both modes.", achievement="all_levels"),
    # ------------------------------------------------------------------ shop
    Skin("ember", "EMBER", (255, 140, 70), (120, 30, 20), sole=(226, 118, 56),
         radius=7, look="angry", crest="flame", crest_colour=(255, 214, 90),
         cost=150, how="Bought with spite."),
    Skin("frost", "FROST", (190, 235, 255), (70, 130, 200), sole=(160, 205, 228),
         radius=0, look="calm", crest="shard", cost=150, how="Bought with spite."),
    Skin("neon", "NEON", (255, 70, 200), (60, 240, 220), sole=(220, 60, 175),
         radius=4, look="visor", crest="antenna", cost=250, how="Bought with spite."),
    Skin("void", "VOID", (28, 26, 38), (90, 60, 160), outline=(8, 6, 14), sole=(20, 18, 28),
         eyes=(150, 110, 255), radius=13, look="cyclops", crest=None, belt=False,
         cost=400, how="Bought with spite."),
]

BY_ID = {skin.id: skin for skin in SKINS}
EYE_STYLES = ("dots", "tired", "x", "calm", "wide", "monocle", "angry", "goggles", "ring",
              "visor", "cyclops")
CRESTS = (None, "cap", "halo", "tophat", "horns", "bobble", "crown", "flame", "shard", "antenna")


# ====================================================================== drawing
# One function draws a character everywhere: in the level, on the menus, in the
# achievement popups. If it lived in two places they would drift apart.
def draw_body(surface, skin, rect, look=(0, 0), blink=False):
    """Draw `skin` filling `rect`. Everything scales off the rect's height."""
    s = rect.h / PLAYER_H                    # 1.0 in game, larger on menus
    radius = max(0, int(skin.radius * s))
    pygame.draw.rect(surface, skin.outline, rect.inflate(int(4 * s), int(4 * s)),
                     border_radius=radius + max(1, int(s)))
    pygame.draw.rect(surface, skin.body, rect, border_radius=radius)
    sole_h = max(2, int(7 * s))
    pygame.draw.rect(surface, skin.sole, (rect.x, rect.bottom - sole_h, rect.w, sole_h),
                     border_bottom_left_radius=radius, border_bottom_right_radius=radius)
    if skin.belt:
        pygame.draw.rect(surface, skin.scarf,
                         (rect.x, rect.y + int(rect.h * 0.5), rect.w, max(2, int(5 * s))))
    _draw_crest(surface, skin, rect, s)
    _draw_eyes(surface, skin, rect, s, look, blink)


def _draw_crest(surface, skin, rect, s):
    """Whatever sits on its head. Decoration only - the hitbox is the body."""
    crest, top, cx = skin.crest, rect.top, rect.centerx
    colour = skin.crest_colour or skin.scarf
    if crest is None:
        return
    if crest == "cap":
        brim = pygame.Rect(0, 0, int(rect.w * 1.25), max(2, int(4 * s)))
        brim.midbottom = (cx, top + int(2 * s))
        pygame.draw.rect(surface, colour, brim, border_radius=max(1, int(2 * s)))
        pygame.draw.rect(surface, colour, (rect.x + int(3 * s), top - int(4 * s),
                                           rect.w - int(6 * s), int(5 * s)))
    elif crest == "tophat":
        pygame.draw.rect(surface, colour, (rect.x - int(2 * s), top - int(2 * s),
                                           rect.w + int(4 * s), max(2, int(3 * s))))
        pygame.draw.rect(surface, colour, (rect.x + int(4 * s), top - int(11 * s),
                                           rect.w - int(8 * s), int(10 * s)))
    elif crest == "halo":
        ring = pygame.Rect(0, 0, int(rect.w * 0.8), max(4, int(6 * s)))
        ring.midbottom = (cx, top - int(3 * s))
        pygame.draw.ellipse(surface, colour, ring, max(1, int(2 * s)))
    elif crest == "horns":
        for side in (-1, 1):
            base = cx + side * int(rect.w * 0.34)
            pygame.draw.polygon(surface, colour, [
                (base - int(3 * s), top + int(1 * s)),
                (base + side * int(4 * s), top - int(9 * s)),
                (base + int(3 * s), top + int(1 * s))])
    elif crest == "bobble":
        pygame.draw.rect(surface, colour, (rect.x + int(2 * s), top - int(4 * s),
                                           rect.w - int(4 * s), int(5 * s)),
                         border_radius=max(1, int(2 * s)))
        pygame.draw.circle(surface, skin.sole, (cx, top - int(8 * s)), max(2, int(4 * s)))
    elif crest == "crown":
        pts = []
        for i in range(5):
            x = rect.x + int(rect.w * i / 4)
            pts.append((x, top - (int(9 * s) if i % 2 == 0 else int(2 * s))))
        pygame.draw.polygon(surface, colour, [(rect.x, top + int(2 * s))] + pts +
                            [(rect.right, top + int(2 * s))])
    elif crest == "flame":
        pygame.draw.polygon(surface, colour, [
            (cx - int(5 * s), top + int(2 * s)), (cx - int(1 * s), top - int(7 * s)),
            (cx + int(2 * s), top - int(2 * s)), (cx + int(4 * s), top - int(11 * s)),
            (cx + int(6 * s), top + int(2 * s))])
    elif crest == "shard":
        pygame.draw.polygon(surface, colour, [
            (cx - int(4 * s), top + int(1 * s)), (cx, top - int(12 * s)),
            (cx + int(4 * s), top + int(1 * s))])
    elif crest == "antenna":
        pygame.draw.line(surface, colour, (cx, top), (cx, top - int(9 * s)), max(1, int(2 * s)))
        pygame.draw.circle(surface, colour, (cx, top - int(10 * s)), max(2, int(3 * s)))


def _draw_eyes(surface, skin, rect, s, look, blink):
    """The face. This is what makes two skins read as two characters."""
    style = skin.look
    lx, ly = look
    ey = rect.y + int(rect.h * 0.18) + int(ly)
    w = max(2, int(4 * s))
    h = max(2, int(9 * s))
    gap = int(5 * s)
    if blink:
        for side in (-1, 1):
            ex = rect.centerx + side * gap + int(lx)
            pygame.draw.rect(surface, skin.eyes, (ex - w // 2, ey + h // 2, w, max(1, int(2 * s))))
        return
    if style == "visor":
        bar = pygame.Rect(rect.x + int(3 * s), ey, rect.w - int(6 * s), h)
        pygame.draw.rect(surface, skin.eyes, bar, border_radius=max(1, int(3 * s)))
        return
    if style == "goggles":
        bar = pygame.Rect(rect.x + int(2 * s), ey, rect.w - int(4 * s), h)
        pygame.draw.rect(surface, skin.eyes, bar, border_radius=max(1, int(3 * s)))
        pygame.draw.rect(surface, skin.scarf, (rect.x, ey + h // 3, rect.w, max(1, int(2 * s))))
        return
    if style == "cyclops":
        pygame.draw.circle(surface, skin.eyes, (rect.centerx + int(lx), ey + h // 2),
                           max(3, int(7 * s)))
        pygame.draw.circle(surface, skin.outline, (rect.centerx + int(lx), ey + h // 2),
                           max(1, int(3 * s)))
        return
    if style == "monocle":
        left = rect.centerx - gap + int(lx)
        pygame.draw.circle(surface, skin.eyes, (left, ey + h // 2), max(3, int(6 * s)),
                           max(1, int(2 * s)))
        pygame.draw.rect(surface, skin.eyes, (left - w // 2, ey + int(2 * s), w, h - int(4 * s)))
        right = rect.centerx + gap + int(lx)
        pygame.draw.rect(surface, skin.eyes, (right - w // 2, ey, w, h), border_radius=2)
        return
    for side in (-1, 1):
        ex = rect.centerx + side * gap + int(lx)
        if style == "tired":
            pygame.draw.rect(surface, skin.eyes, (ex - w, ey + h // 3, w * 2, max(2, int(3 * s))))
        elif style == "calm":
            pygame.draw.rect(surface, skin.eyes, (ex - w // 2, ey + int(2 * s), w, h - int(4 * s)),
                             border_radius=max(1, int(2 * s)))
        elif style == "wide":
            pygame.draw.circle(surface, skin.eyes, (ex, ey + h // 2), max(3, int(6 * s)))
            pygame.draw.circle(surface, skin.body, (ex, ey + h // 2), max(1, int(2 * s)))
        elif style == "ring":
            pygame.draw.circle(surface, skin.eyes, (ex, ey + h // 2), max(3, int(5 * s)),
                               max(1, int(2 * s)))
        elif style == "x":
            r = max(2, int(4 * s))
            for dx in (-1, 1):
                pygame.draw.line(surface, skin.eyes, (ex - r, ey + h // 2 - r * dx),
                                 (ex + r, ey + h // 2 + r * dx), max(1, int(2 * s)))
        elif style == "angry":
            pygame.draw.polygon(surface, skin.eyes, [
                (ex - w, ey + int(2 * s)), (ex + w, ey + h // 2 - int(1 * s)),
                (ex + w, ey + h), (ex - w, ey + h)] if side > 0 else [
                (ex + w, ey + int(2 * s)), (ex - w, ey + h // 2 - int(1 * s)),
                (ex - w, ey + h), (ex + w, ey + h)])
        else:                                   # "dots", the original face
            pygame.draw.rect(surface, skin.eyes, (ex - w // 2, ey, w, h), border_radius=2)


# ==================================================================== the save
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
