# I am adding comments for me to easily understand the codes
# settings.py - every tunable number, colour and line of text lives here,
# so the game can be balanced without digging through the other files.

import os

# ---------------------------------------------------------------- identity
GAME_TITLE = "DON'T EVEN BOTHER"
GAME_SUBTITLE = "PURE EVIL EDITION"
STUDIO_NAME = "LAZYHUNTER7"         # shown on the splash screen and title footer
DEVELOPER_NAME = "Nitin M"           # shown in the credits
VERSION = "2.0.0"

# ---------------------------------------------------------------- paths
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_PATH, "rage_save.json")

# ---------------------------------------------------------------- display
# The whole game is drawn on a fixed 1280x720 canvas. pygame.SCALED then
# stretches it (with black bars) to whatever window or monitor we are on.
VIRTUAL_W, VIRTUAL_H = 1280, 720
FPS_CAP = 144
TILE = 40                      # one map character = 40x40 pixels
ROWS = VIRTUAL_H // TILE       # 18 rows, levels only scroll sideways

# ---------------------------------------------------------------- simulation
# Physics runs at a fixed 120 steps per second no matter the frame rate.
# That makes every trap perfectly repeatable, which is what makes a rage
# game fair: you can learn it.
PHYSICS_HZ = 120
FIXED_DT = 1.0 / PHYSICS_HZ
MAX_STEPS_PER_FRAME = 10

# ---------------------------------------------------------------- player
PLAYER_W, PLAYER_H = 26, 34
RUN_SPEED = 330
GROUND_ACCEL = 4200
GROUND_DECEL = 5200
AIR_ACCEL = 3000
AIR_DECEL = 1400
GRAVITY = 3000
FALL_GRAVITY_MULT = 1.35       # falling is faster than rising = snappy jumps
MAX_FALL_SPEED = 1150
JUMP_VELOCITY = 900            # about 3.4 tiles high
JUMP_CUT_MULT = 0.45           # let go of jump early = shorter hop
COYOTE_TIME = 0.09             # you can still jump just after leaving a ledge
JUMP_BUFFER_TIME = 0.12        # a jump pressed just before landing still counts
SPRING_VELOCITY = 1350
KILL_Y = VIRTUAL_H + 80        # fall below this and you are dead

# ---------------------------------------------------------------- traps
CRUMBLE_DELAY = 0.45           # cracked blocks
FAKE_BLOCK_DELAY = 0.16        # blocks that look 100% real
HIDDEN_SPIKE_RANGE = 0.6       # tiles between spike and player centre
HIDDEN_SPIKE_HEIGHT = 1.5      # tiles above the spike that still trigger it
DROP_GRAVITY = 4000
DEFAULT_ARROW_SPEED = 14       # tiles per second

# ---------------------------------------------------------------- difficulty
# Brutal changes the rules everywhere on top of extra traps in the maps.
DIFFICULTIES = {
    "normal": {
        "label": "NORMAL", "checkpoints": True, "saw_speed": 1.0, "crumble": 1.0, "fake": 1.0,
        "hidden_range": 1.0, "coyote": COYOTE_TIME, "buffer": JUMP_BUFFER_TIME, "arrow_speed": 1.0,
        "drop_speed": 1.0, "respawn": 0.8, "enemy_speed": 1.0, "fire_rate": 1.0,
    },
    "brutal": {
        "label": "BRUTAL", "checkpoints": False, "saw_speed": 1.3, "crumble": 0.65, "fake": 0.6,
        "hidden_range": 1.5, "coyote": 0.05, "buffer": 0.07, "arrow_speed": 1.25,
        "drop_speed": 1.25, "respawn": 0.45, "enemy_speed": 1.3, "fire_rate": 1.3,
    },
}

ACTS = {
    1: {"name": "ACT I", "title": "THE WARM-UP", "tagline": "You think you're ready."},
    2: {"name": "ACT II", "title": "THE GAUNTLET", "tagline": "You thought that was hard?"},
    3: {"name": "ACT III", "title": "THE CLIMB", "tagline": "Every step up is a step you can lose."},
}

# ---------------------------------------------------------------- the player
MAX_NAME = 12
# Used when the player has told us their name. "{name}" is filled in. These are
# kept apart from the other pools so a name never turns up twice in one line.
NAME_TAUNTS = [
    "{name}, that was pathetic.",
    "Nice one, {name}.",
    "{name}. Honestly.",
    "Was that on purpose, {name}?",
    "{name} is having a hard time.",
    "Try reading the level, {name}.",
    "Somewhere, {name}'s family is watching.",
    "{name}, the door is THAT way.",
    "This is the part where {name} gives up.",
    "{name} versus a rectangle. The rectangle is winning.",
]
NAME_TAUNT_CHANCE = 0.28

# ---------------------------------------------------------------- economy
# Spite is earned by playing and spent on cosmetics. It never touches the
# rules of the game: nothing you buy makes a level easier.
CURRENCY = "SPITE"
PAYOUT = {
    "clear": 25,            # first time you finish a level
    "few_deaths": 40,       # ...and you did it with FEW_DEATHS or fewer
    "deathless": 100,       # ...and you did it without dying at all
    "best_time": 15,        # a new personal best on a level you had already cleared
    "act": 150,             # finishing a whole act
    "death": 1,             # a pity payment, capped per session (see below)
}
FEW_DEATHS = 3
DEATH_PAYOUT_CAP = 30       # so farming deaths is never worth it
BRUTAL_PAYOUT = 2.0         # Brutal pays double, because Brutal costs double

# ---------------------------------------------------------------- game feel
RESPAWN_DELAY = 0.8
HITSTOP_TIME = 0.08
CAMERA_LOOKAHEAD = 90
CAMERA_SMOOTH = 7.0
MAX_DEATH_MARKERS = 400

# ---------------------------------------------------------------- colours
INK = (14, 11, 20)
NIGHT = (22, 18, 32)
PAPER = (244, 238, 228)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLOOD = (214, 36, 56)
DARK_BLOOD = (110, 10, 26)
EMBER = (255, 122, 48)
GOLD = (255, 204, 77)
TOXIC = (120, 255, 150)
ICE = (120, 210, 255)
MUTED = (140, 132, 160)
DIM = (80, 74, 96)
STEEL = (206, 208, 220)
STEEL_DARK = (116, 118, 136)

PLAYER_BODY = (250, 244, 232)
PLAYER_OUTLINE = (18, 14, 24)
PLAYER_SCARF = (226, 40, 60)

# Each "world" of levels gets its own palette.
THEMES = {
    "ruins": {
        "name": "The Ruins",
        "sky_top": (30, 16, 46), "sky_bottom": (206, 104, 84),
        "far": (92, 44, 82), "near": (54, 28, 60),
        "block": (92, 62, 80), "block_top": (238, 168, 112),
        "block_dark": (50, 32, 48), "block_detail": (74, 48, 64),
        "accent": (255, 128, 64), "ambient": (255, 190, 130),
        "stars": True,
    },
    "grove": {
        "name": "The Grove",
        "sky_top": (6, 22, 32), "sky_bottom": (34, 104, 104),
        "far": (16, 58, 66), "near": (10, 38, 44),
        "block": (40, 70, 60), "block_top": (132, 216, 118),
        "block_dark": (20, 38, 34), "block_detail": (32, 56, 48),
        "accent": (150, 255, 170), "ambient": (200, 255, 140),
        "stars": True,
    },
    "foundry": {
        "name": "The Foundry",
        "sky_top": (12, 12, 18), "sky_bottom": (78, 56, 46),
        "far": (44, 38, 42), "near": (30, 27, 32),
        "block": (74, 76, 88), "block_top": (250, 186, 60),
        "block_dark": (36, 36, 46), "block_detail": (60, 62, 74),
        "accent": (255, 186, 60), "ambient": (255, 160, 60),
        "stars": False,
    },
    "neon": {
        "name": "The Gauntlet",
        "sky_top": (8, 4, 24), "sky_bottom": (70, 20, 110),
        "far": (40, 14, 80), "near": (22, 8, 48),
        "block": (36, 26, 70), "block_top": (80, 240, 255),
        "block_dark": (18, 12, 36), "block_detail": (30, 20, 58),
        "accent": (255, 60, 220), "ambient": (120, 220, 255),
        "stars": True,
    },
    "frost": {
        "name": "The Gauntlet",
        "sky_top": (8, 18, 40), "sky_bottom": (90, 150, 200),
        "far": (50, 90, 140), "near": (30, 60, 100),
        "block": (60, 86, 120), "block_top": (220, 245, 255),
        "block_dark": (30, 44, 70), "block_detail": (52, 74, 104),
        "accent": (140, 220, 255), "ambient": (230, 245, 255),
        "stars": True,
    },
    "summit": {
        "name": "The Climb",
        "sky_top": (14, 20, 56), "sky_bottom": (240, 150, 110),
        "far": (80, 70, 120), "near": (50, 44, 84),
        "block": (84, 78, 96), "block_top": (250, 230, 200),
        "block_dark": (44, 40, 54), "block_detail": (70, 64, 82),
        "accent": (255, 200, 120), "ambient": (255, 240, 220),
        "stars": True,
    },
    "abyss": {
        "name": "The Abyss",
        "sky_top": (6, 0, 6), "sky_bottom": (96, 8, 22),
        "far": (44, 4, 14), "near": (26, 2, 8),
        "block": (58, 22, 30), "block_top": (255, 76, 76),
        "block_dark": (26, 6, 12), "block_detail": (44, 14, 22),
        "accent": (255, 70, 70), "ambient": (255, 90, 60),
        "stars": False,
    },
}

# ---------------------------------------------------------------- default settings
DEFAULT_SETTINGS = {
    "master_volume": 0.8,
    "music_volume": 0.55,
    "sfx_volume": 0.8,
    "screen_shake": 1.0,
    "fullscreen": True,
    "show_timer": True,
    "death_markers": True,
    "film_grain": True,
    "streamer_mode": False,
    "auto_hop": True,
}

# ---------------------------------------------------------------- taunts
TAUNTS_GENERAL = [
    "Skill issue detected.", "Did you even try?", "Frame-perfect failure.",
    "Pro tip: don't die.", "Impressive. Impressively bad.", "Achievement unlocked: Instant Regret.",
    "Respawning. Again.", "A rock would have waited.", "Your keyboard deserves better.",
    "Bold strategy.", "Have you tried not doing that?", "Peak performance.",
    "That looked painful. Good.", "Maybe try the tutorial. Oh wait.",
    "I'd say 'nice try' but...", "Ouch. For you, not me.", "The game is winning.",
    "History repeats itself.", "Definitely lag.", "Stunning. Truly.",
]

TAUNTS_BY_CAUSE = {
    "spike": ["Pointy things are bad. Noted?", "You found the spikes!", "Spikes: 1. You: 0.",
              "That spike was there all along.", "Look before you leap. Oh, you can't."],
    "hidden": ["You didn't see that coming. Nobody does.", "Surprise!", "Invisible. Not imaginary.",
               "The floor had teeth.", "No warnings. As promised."],
    "saw": ["Sliced and diced.", "The saw sends its regards.", "Timing is a skill. Allegedly.",
            "Round and round it goes."],
    "crush": ["Flat as a pancake.", "Heavy lesson.", "You should look up more.",
              "Squished. Beautifully."],
    "fall": ["Gravity works. Congrats.", "The floor was a suggestion.", "Down you go.",
             "Trust issues: justified.", "That ground was fake. Like my sympathy."],
    "fake_goal": ["That door was a lie.", "Doors are not your friends.", "Did it look real? Good.",
                  "Welcome to the exit. Just kidding.", "Wrong door. Obviously."],
    "arrow": ["Should've heard that coming.", "Pew.", "Arrow to the everything.",
              "Duck. Or jump. Either, really."],
    "enemy": ["It was just walking. You walked into it.", "Beaten by a blob.", "Jump ON them. Not INTO them.",
              "The locals don't like you."],
    "orb": ["It saw you coming.", "Shot on sight.", "The eye never blinks.", "Dodge. It's a verb."],
    "laser": ["It flickered first. It always flickers first.", "Zapped.", "Timing. Look it up.", "Crispy."],
    "echo": ["Killed by your own past.", "Your shadow caught up.", "You were your own worst enemy. Literally.",
             "Should've moved faster than yourself."],
}

# The narrator remembers where you keep dying (deaths within ~1.5 tiles of each other)
SPOT_TAUNTS = {
    3: ["Third time. Same spot.", "This spot again? Really?", "You're getting good at dying HERE."],
    5: ["Five times right here. It's a tradition now.", "This tile knows your name."],
    10: ["Ten deaths on this exact spot. Moving in?", "We should put a plaque here."],
    20: ["Twenty. Here. Unbelievable.", "At this point it's a pilgrimage."],
    50: ["Fifty deaths on one spot. Streamers, clip this."],
}

MODE_TAUNTS = {
    "normal": ["Even on Normal? Wow.", "This is the easy mode, you know.", "Baby mode. Still dying.",
               "Brutal players are laughing at you."],
    "brutal": ["You chose Brutal. Remember that.", "No checkpoints. No mercy. No chance.",
               "Your ego wrote a cheque your hands can't cash.", "Brutal was a choice. A bad one."],
}

RETURN_LINES = [
    (100, "Back again? {n} deaths on this level. Impressive commitment."),
    (40, "Welcome back. {n} deaths here so far."),
    (15, "Oh, it's you again."),
]

MILESTONES = {
    10: "10 deaths. Just warming up?",
    25: "25 deaths. Still here?",
    50: "50 deaths. Stubborn. I respect it.",
    100: "100 deaths. Seek help.",
    200: "200 deaths. The game is laughing.",
    300: "300 deaths. This is a lifestyle now.",
    500: "500 deaths. You're the real villain here.",
    1000: "1000 deaths. Legend. Tragic legend.",
}

# Rank letter from the number of deaths in a clear (letter, max deaths, comment).
RANKS = [
    ("S", 0, "Flawless. Suspicious."),
    ("A", 3, "Annoyingly competent."),
    ("B", 10, "Acceptable suffering."),
    ("C", 25, "Tragic, but it counts."),
    ("D", 60, "Deeply painful to watch."),
    ("F", 10 ** 9, "Should've read the title."),
]
RANK_COLOURS = {"S": GOLD, "A": TOXIC, "B": ICE, "C": PAPER, "D": EMBER, "F": BLOOD}
