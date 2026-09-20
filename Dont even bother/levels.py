# I am adding comments for me to easily understand the codes
# levels.py - all ten levels, drawn as text maps plus a list of "triggers".
#
# MAP LEGEND (one character = one 40x40 tile, 18 rows tall)
#   .  empty            #  solid ground          ~  fake wall (walk through it)
#   P  player spawn     G  exit door             X  fake exit door (kills you)
#   K  checkpoint       B  spring
#   ^  spike (points away from the block it sits on)   v < >  spikes forced down/left/right
#   h  hidden spike (pops up when you walk over it)
#   c  cracked block (falls after you stand on it)
#   x  fake block (looks exactly like ground, falls instantly)
#   i  invisible block (appears when you hit it from below)
#   1-9  solid blocks that belong to a trigger-controlled group
# Levels can add their own characters with `legend`, e.g. a spike that
# belongs to group "1" so it falls together with the group's blocks.
#
# TRIGGERS: when the player touches `area` (col, row, width, height in tiles)
# the `actions` run in order:
#   ("drop", g)                  group falls (and crushes)
#   ("move", g, dx, dy, secs)    group slides by dx, dy tiles
#   ("vanish", g) / ("appear", g)
#   ("say", text[, secs])        the narrator talks
#   ("goal", col, row)           the exit door runs away
#   ("saw", id)                  switch on a saw
#   ("fire", col, row, dx, dy[, speed])   shoot an arrow
#   ("reverse", True/False)      swap left and right
#   ("dark", True/False)         lights off / on
#   ("shake", amount) ("sound", name) ("wait", secs) ("repeat", index)

from dataclasses import dataclass, field, replace


@dataclass
class Trigger:
    area: tuple
    actions: list
    once: bool = True
    grounded: bool = False      # only fires while the player is standing, never mid-jump


@dataclass
class SawDef:
    path: list
    speed: float = 4.0
    radius: float = 0.7
    active: bool = True
    mode: str = "pingpong"
    saw_id: str = None
    track: bool = True


@dataclass
class LaserDef:
    col: int
    row: int
    dx: int
    dy: int
    on: float = 1.0
    off: float = 1.5
    offset: float = 0.0


@dataclass
class CannonDef:
    col: int
    row: int
    dx: int
    dy: int
    period: float = 2.0
    speed: float = 6.0
    offset: float = 0.0


@dataclass
class WindDef:
    area: tuple                 # (col, row, width, height) in tiles
    fx: float = 0.0             # sideways drift in pixels per second (you can't out-run it easily)
    fy: float = 0.0             # vertical drift it pulls you to, in pixels per second (negative = updraft)


@dataclass
class LevelDef:
    number: int
    name: str
    tagline: str
    theme: str
    rows: list
    intro: str = ""
    legend: dict = field(default_factory=dict)
    triggers: list = field(default_factory=list)
    saws: list = field(default_factory=list)
    dark: bool = False
    music: str = "game"
    act: int = 1
    # extra map edits: {"normal": [...], "brutal": [...]} of (col, row, text).
    # Brutal gets the normal edits too, plus its own.
    edits: dict = field(default_factory=dict)
    brutal_triggers: list = field(default_factory=list)
    brutal_saws: list = field(default_factory=list)
    # route hints for the level-solver bot (tiles). Players never see these.
    waypoints: list = field(default_factory=list)
    lasers: list = field(default_factory=list)
    cannons: list = field(default_factory=list)
    winds: list = field(default_factory=list)
    blink_period: float = 1.3

    def __post_init__(self):
        width = max(len(r) for r in self.rows)
        for i, r in enumerate(self.rows):
            if len(r) != width:
                raise ValueError(f"Level {self.number}: row {i} is {len(r)} wide, expected {width}")
        if len(self.rows) < 18:
            raise ValueError(f"Level {self.number}: needs at least 18 rows, has {len(self.rows)}")
        for mode, edits in self.edits.items():
            for col, row, text in edits:
                if row >= len(self.rows) or col + len(text) > width:
                    raise ValueError(f"Level {self.number}: {mode} edit {text!r} at ({col},{row}) is off the map")


def _rows(*parts):
    """Helper so maps can repeat identical rows: _rows(("...", 5), "...#")."""
    out = []
    for p in parts:
        if isinstance(p, tuple):
            out.extend([p[0]] * p[1])
        else:
            out.append(p)
    return out


LEVELS = [
    # ------------------------------------------------------------------ 1
    LevelDef(
        1, "First Doubt", "WALK RIGHT. HOW HARD CAN IT BE?", "ruins",
        intro="Walk right. Touch the door. It's really that simple.",
        rows=_rows(
            ("." * 48, 14),
            "..P......^^...h.....X.....................G.....",
            "#" * 26 + "1111" + "#" * 18,
            ("#" * 26 + "1111" + "#" * 18, 2),
        ),
        triggers=[
            Trigger((26, 11, 4, 4), [("drop", "1"), ("sound", "rumble")]),
            Trigger((39, 9, 2, 6), [("goal", 45, 14), ("say", "Nope. Bit further.")]),
        ],
    ),
    # ------------------------------------------------------------------ 2
    LevelDef(
        2, "Trust Issues", "THE FLOOR HAS TRUST ISSUES", "ruins",
        intro="The floor has trust issues. So should you.",
        rows=_rows(
            ("." * 50, 10),
            "." * 32 + "i" + "." * 17,
            ("." * 50, 2),
            "." * 13 + "ccc" + ".." + "ccc" + ".." + "xxx" + ".." + "###" + "..." + "###" + "." * 13,
            "..P....." + "###" + "." * 35 + "G...",
            ("######" + "." * 33 + "#" * 11, 3),
        ),
    ),
    # ------------------------------------------------------------------ 3
    LevelDef(
        3, "Look Up", "NOTHING UP THERE. PROMISE.", "ruins",
        intro="Nothing up there. Promise.",
        rows=_rows(
            ("......" + "#" * 40 + "......", 8),
            "......" + "#####" + "11" + "#######" + "2" * 14 + "#" * 12 + "......",
            "..........." + "aa" + "......." + "b" * 14 + "." * 18,
            ("." * 52, 4),
            "..P" + "." * 24 + "^^" + "." * 20 + "G..",
            ("#" * 52, 3),
        ),
        legend={"a": ("spike", "1", True), "b": ("spike", "2", True)},
        triggers=[
            Trigger((9, 9, 2, 6), [("drop", "1")]),
            Trigger((18, 9, 2, 6), [("say", "Keep up."), ("sound", "rumble"), ("move", "2", 0, 4, 2.4)]),
            Trigger((40, 9, 2, 6), [("fire", 51, 14, -1, 0, 14)]),
        ],
    ),
    # ------------------------------------------------------------------ 4
    LevelDef(
        4, "Dead End", "SOME WALLS ARE JUST SUGGESTIONS", "grove",
        intro="Nature is beautiful. And sharp.",
        rows=_rows(
            ("." * 39 + "#" * 17, 7),
            "." * 42 + "#" * 14,
            "." * 41 + "X" + "#" * 14,
            ("." * 40 + "##" + "." * 14, 2),
            "." * 37 + "##" + "." + "##" + "." * 14,
            "." * 26 + "####" + "." * 10 + "##" + "." * 14,
            "." * 35 + "##" + "..." + "~~" + "." * 14,
            "..P" + "." * 18 + "B" + "." * 18 + "~~" + "." * 10 + "G...",
            ("#" * 22 + "." * 12 + "#" * 22, 3),
        ),
        saws=[
            SawDef([(6, 14), (12, 14)], speed=4),
            SawDef([(18, 16.5), (18, 14)], speed=5, active=False, saw_id="pop", track=False),
            SawDef([(24, 10), (29, 10)], speed=3),
        ],
        triggers=[
            Trigger((14, 9, 2, 6), [("saw", "pop")]),
            Trigger((38, 12, 1, 3), [("say", "Dead end. Might as well quit.")]),
        ],
    ),
    # ------------------------------------------------------------------ 5
    LevelDef(
        5, "Lights Out", "WHO TURNED OFF THE LIGHTS?", "grove",
        intro="Bit gloomy in here, isn't it?",
        rows=_rows(
            ("." * 50, 11),
            "." * 20 + "h" + "." * 29,
            "." * 19 + "###" + ".." + "ccc" + "." * 9 + "^" + "." * 13,
            "." * 14 + "#x#" + "." * 12 + "###" + ".." + "###" + "." * 13,
            "..P......" + "###" + "." * 27 + "###" + "...X.G..",
            ("#" * 8 + "." * 34 + "#" * 8, 3),
        ),
        triggers=[
            Trigger((5, 8, 2, 7), [("say", "Let me get the lights for you."), ("wait", 0.6), ("dark", True)]),
            Trigger((42, 8, 1, 7), [("dark", False), ("say", "Let there be light. And doors.")]),
        ],
    ),
    # ------------------------------------------------------------------ 6
    LevelDef(
        6, "Wrong Way", "LEFT IS RIGHT. RIGHT IS WRONG.", "foundry",
        intro="This one is straightforward. Mostly.",
        rows=_rows(
            ("." * 30 + "#" * 11 + "." * 13, 4),
            ("." * 32 + "11" + "..." + "22" + "." * 15, 5),
            ("." * 54, 3),
            "." * 17 + "###" + "." * 34,
            "." * 12 + "###" + "." * 7 + "###" + "." * 29,
            "..P" + "." * 48 + "G..",
            ("#" * 10 + "." * 18 + "#" * 26, 3),
        ),
        triggers=[
            Trigger((7, 9, 2, 6), [("say", "Controls are overrated."), ("reverse", True)]),
            Trigger((28, 9, 1, 6), [("reverse", False), ("say", "Better? Good. Now mind your head.")]),
            Trigger((29, 9, 1, 6), [("move", "1", 0, 6, 0.12), ("shake", 0.35), ("sound", "slam"), ("wait", 0.35),
                                    ("move", "1", 0, -6, 0.7), ("wait", 0.55), ("repeat", 0)]),
            Trigger((29, 9, 1, 6), [("wait", 0.8), ("move", "2", 0, 6, 0.12), ("shake", 0.35), ("sound", "slam"),
                                    ("wait", 0.35), ("move", "2", 0, -6, 0.7), ("wait", 0.55), ("repeat", 1)]),
            Trigger((45, 9, 1, 6), [("fire", 53, 14, -1, 0, 12)]),
        ],
    ),
    # ------------------------------------------------------------------ 7
    LevelDef(
        7, "Runaway", "JUST GRAB THE DOOR", "foundry",
        intro="Just grab the door. How hard can it be?",
        rows=_rows(
            ("." * 56, 6),
            "." * 50 + "######",
            "." * 56,
            "." * 47 + "##" + "." * 7,
            "." * 30 + "#" * 15 + "." * 11,
            "." * 56,
            "." * 27 + "cc" + "." * 27,
            "." * 56,
            "." * 14 + "111" + "." * 7 + "cc" + "." * 30,
            "..P......." + "G" + "." * 22 + "^" * 8 + "." * 15,
            ("#" * 13 + "." * 9 + "#" * 34, 3),
        ),
        triggers=[
            Trigger((0, 0, 4, 18), [("move", "1", 4, 0, 1.5), ("wait", 0.35), ("move", "1", -4, 0, 1.5),
                                    ("wait", 0.35), ("repeat", 0)]),
            Trigger((7, 10, 2, 5), [("goal", 53, 5), ("say", "Catch me if you can!")]),
            Trigger((38, 4, 2, 5), [("goal", 43, 14), ("say", "Actually, it's cosier down there.")]),
        ],
        waypoints=[(12, 14), (15, 12), (23, 14), (24, 12), (28, 10), (31, 8), (45, 14)],   # solver: platform, stairs, bridge, drop
    ),
    # ------------------------------------------------------------------ 8
    LevelDef(
        8, "Rising Tension", "UP IS THE ONLY WAY OUT", "foundry",
        intro="Up is the only way out.",
        rows=_rows(
            ("." * 40, 2),
            "." * 38 + "G.",
            "." * 32 + "###." + "####",
            "." * 29 + "h" + "." * 10,
            "." * 27 + "###" + "." * 10,
            "." * 40,
            "." * 23 + "##" + "." * 15,
            "." * 40,
            "." * 18 + "###" + "." * 19,
            "." * 13 + "ccc" + "." * 24,
            "." * 40,
            "." * 8 + "###" + "." * 29,
            "..P" + "." * 37,
            "######" + "." * 34,
            "." * 40,
            "l" * 40,
            "L" * 40,
        ),
        legend={"l": ("spike", "L", True), "L": ("block", "L", True)},
        triggers=[
            Trigger((4, 0, 2, 18), [("say", "Is it getting hot in here?"), ("sound", "rumble"), ("wait", 0.6),
                                    ("move", "L", 0, -6, 4.8), ("say", "Faster, maybe?"), ("move", "L", 0, -6, 3.6)]),
        ],
    ),
    # ------------------------------------------------------------------ 9
    LevelDef(
        9, "Deja Vu", "HAVEN'T WE BEEN HERE BEFORE?", "abyss",
        intro="Level 1 again? Lazy developers.", music="abyss",
        rows=_rows(
            ("." * 48, 14),
            "..P......^^.....hh..G.....................X..X..",
            ("#" * 48, 3),
        ),
        triggers=[
            Trigger((26, 8, 4, 5), [("fire", 47, 11, -1, 0, 18)]),
            Trigger((33, 9, 1, 6), [("say", "Almost there. Trust me.")]),
        ],
    ),
    # ------------------------------------------------------------------ 10
    LevelDef(
        10, "The Final Lie", "EVERYTHING. ALL AT ONCE.", "abyss",
        intro="Everything you've learned. All at once.", music="abyss",
        rows=_rows(
            ("." * 25 + "#" * 11 + "." * 28 + "#" * 6 + "..", 4),
            ("." * 27 + "11" + ".." + "22" + "." * 31 + "#" * 6 + "..", 5),
            "." * 66 + "99" + "....",
            "." * 66 + "zz" + "....",
            "." * 72,
            "." * 16 + "###" + "." * 53,
            "." * 11 + "ccc" + "." * 58,
            "..P" + "." * 19 + "K" + "." * 22 + "qq" + "." * 11 + "K" + ".." + "G" + "." * 10,
            ("#" * 9 + "." * 12 + "#" * 15 + "3333" + "4444" + "5555" + "6666" + "7777" + "#" * 16, 3),
        ),
        legend={"z": ("spike", "9", True), "q": ("spike", "5", True)},
        saws=[SawDef([(14.5, 9), (14.5, 13.5)], speed=4)],
        triggers=[
            Trigger((24, 9, 1, 6), [("move", "1", 0, 6, 0.12), ("shake", 0.35), ("sound", "slam"), ("wait", 0.35),
                                    ("move", "1", 0, -6, 0.7), ("wait", 0.55), ("repeat", 0)]),
            Trigger((24, 9, 1, 6), [("wait", 0.8), ("move", "2", 0, 6, 0.12), ("shake", 0.35), ("sound", "slam"),
                                    ("wait", 0.35), ("move", "2", 0, -6, 0.7), ("wait", 0.55), ("repeat", 1)]),
            Trigger((38, 9, 1, 6), [("say", "RUN."), ("sound", "rumble"), ("shake", 0.4), ("wait", 0.4),
                                    ("drop", "3"), ("wait", 0.5), ("drop", "4"), ("wait", 0.5), ("drop", "5"),
                                    ("wait", 0.5), ("drop", "6"), ("wait", 0.5), ("drop", "7")]),
            Trigger((60, 9, 1, 6), [("goal", 70, 14), ("say", "So close. So, so close.")]),
            Trigger((63, 10, 2, 5), [("drop", "9")]),
        ],
    ),
]


# ---------------------------------------------------------------------------------------------
# Act I toughening. "normal" edits make every level a little meaner; "brutal" edits are added on
# top of those in Brutal mode. Each edit is (col, row, text) written over the map.
ACT1_EXTRAS = {
    1: dict(edits={"normal": [(33, 14, "^"), (38, 14, "e")],
                   "brutal": [(9, 14, "^^^"), (17, 14, "h"), (31, 14, "h"), (37, 14, "h"), (44, 14, "S")]},
            brutal_triggers=[Trigger((43, 9, 1, 6), [("goal", 47, 14), ("say", "Still no.")])]),
    2: dict(edits={"normal": [(42, 14, "^"), (47, 14, "e")],
                   "brutal": [(8, 14, "ccc"), (29, 13, "c"), (44, 14, "h"), (36, 9, "o")]}),
    3: dict(edits={"normal": [(36, 14, "^"), (34, 9, "u")],
                   "brutal": [(27, 14, "^^"), (15, 14, "h"), (42, 9, "u")]},
            waypoints=[(9, 14), (17, 14), (25, 14), (31, 14), (39, 14)],
            brutal_triggers=[Trigger((40, 9, 2, 6), [("wait", 0.35), ("fire", 51, 12, -1, 0, 14)])]),
    4: dict(edits={"normal": [(46, 14, "^"), (48, 10, "o")],
                   "brutal": [(49, 14, "h"), (28, 11, "h"), (44, 14, "e")]},
            brutal_saws=[SawDef([(43, 12), (50, 12)], speed=3)]),
    5: dict(edits={"normal": [(31, 12, "^"), (43, 14, "m")],
                   "brutal": [(10, 14, "x"), (40, 13, "h")]}),
    6: dict(edits={"normal": [(19, 11, "^"), (46, 10, "o")],
                   "brutal": [(12, 12, "h"), (40, 14, "h")]},
            brutal_triggers=[Trigger((36, 9, 1, 6), [("fire", 53, 13, -1, 0, 12)])]),
    7: dict(edits={"normal": [(35, 8, "^"), (40, 8, "e")],
                   "brutal": [(42, 8, "h"), (40, 8, "S"), (24, 13, "cx")]}),
    8: dict(edits={"normal": [(20, 8, "^"), (26, 1, "o")],
                   "brutal": [(8, 12, "ccc"), (24, 7, "x"), (10, 6, "o")]}),
    9: dict(edits={"normal": [(12, 14, "^")],
                   "brutal": [(19, 14, "h"), (6, 14, "h")]}),
    10: dict(legend={"z": ("spike", "9", True), "q": ("spike", "5", True), "w": ("spike", "6", True),
                     "r": ("spike", "4", True)},
             edits={"normal": [(50, 14, "w")],
                    "brutal": [(41, 14, "r"), (5, 14, "h"), (64, 14, "h"), (50, 8, "o")]},
             # your own shadow starts chasing you from the first checkpoint
             more_triggers=[Trigger((23, 9, 1, 6), [("echo", 1.6), ("say", "Don't look back.")])]),
}


def _toughen(level, extras):
    extras = dict(extras)
    more = extras.pop("more_triggers", [])
    return replace(level, triggers=list(level.triggers) + more, **extras)


LEVELS = [_toughen(level, ACT1_EXTRAS.get(level.number, {})) for level in LEVELS]
