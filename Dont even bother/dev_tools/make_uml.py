# dev_tools/make_uml.py - draws the class diagram for the game.
#
# The diagram is generated rather than drawn by hand, so it can be rebuilt
# whenever the code changes:
#
#     python dev_tools/make_uml.py
#
# It writes "UML Diagram.png" next to the README, one folder up.

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle  # noqa: E402

W, H = 2820, 2130                      # drawing units (1 unit = 1 px at dpi 100)
INK = "#1b1b24"
LINE = "#2b2b38"
FILL = "#ffffff"
HEAD = "#e8e8f0"
ABSTRACT = "#f3f0ff"
NOTE = "#6b6b7b"

TITLE_H = 34
ROW_H = 21
PAD = 10

BLOCK_KIDS = ["CrumbleBlock", "InvisibleBlock", "SwitchBlock", "ConveyorBlock", "IceBlock"]
HAZARD_KIDS = ["Spike", "Saw", "Arrow", "Orb", "Cannon", "Laser"]
ENEMY_KIDS = ["Crawler", "Mimic", "Swooper", "Sentry", "Echo"]
SCENE_KIDS = ["TitleScene", "DifficultyScene", "LevelSelectScene", "SettingsScene",
              "CreditsScene", "ActCardScene", "SkinsScene", "RaceSelectScene"]
LOOSE_ENTITIES = ["Door", "Spring", "Checkpoint", "Group", "KeyItem"]

boxes = {}


class Box:
    def __init__(self, name, x, y, w, attrs=(), methods=(), stereotype=None, compact=False):
        self.name, self.x, self.y, self.w = name, x, y, w
        self.attrs, self.methods = list(attrs), list(methods)
        self.stereotype, self.compact = stereotype, compact
        self.head_h = TITLE_H + (16 if stereotype else 0)
        body = 0 if compact else (len(self.attrs) + len(self.methods)) * ROW_H + 2 * PAD
        self.h = self.head_h + body

    @property
    def top(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    def anchor(self, side):
        return {"top": (self.cx, self.top),
                "bottom": (self.cx, self.y),
                "left": (self.x, self.y + self.h / 2),
                "right": (self.x + self.w, self.y + self.h / 2)}[side]


def box(name, x, y, w, attrs=(), methods=(), stereotype=None, compact=False):
    boxes[name] = Box(name, x, y, w, attrs, methods, stereotype, compact)
    return boxes[name]


def draw_box(ax, b):
    fill = ABSTRACT if b.stereotype == "abstract" else FILL
    ax.add_patch(FancyBboxPatch((b.x, b.y), b.w, b.h, boxstyle="round,pad=0,rounding_size=4",
                                linewidth=1.6, edgecolor=LINE, facecolor=fill, zorder=3))
    ax.add_patch(Rectangle((b.x, b.top - b.head_h), b.w, b.head_h,
                           linewidth=0, facecolor=HEAD, zorder=3.1))
    y = b.top - 26
    if b.stereotype:
        ax.text(b.cx, b.top - 15, "«" + b.stereotype + "»", ha="center", va="center",
                fontsize=9.5, style="italic", color=NOTE, zorder=4)
        y = b.top - 34
    style = "italic" if b.stereotype == "abstract" else "normal"
    # a point is 100/72 drawing units here, and bold text runs about 0.62 em a
    # character, so this is what actually fits inside the box
    size = min(12.5, (b.w - 22) / (len(b.name) * 0.62 * 100 / 72))
    ax.text(b.cx, y, b.name, ha="center", va="center", fontsize=size, fontweight="bold",
            color=INK, style=style, zorder=4)
    if b.compact:
        return
    ax.plot([b.x, b.x + b.w], [b.top - b.head_h] * 2, color=LINE, lw=1.2, zorder=4)
    ty = b.top - b.head_h - PAD - ROW_H / 2
    for text in b.attrs:
        ax.text(b.x + 12, ty, text, ha="left", va="center", fontsize=10, color=INK, zorder=4)
        ty -= ROW_H
    if b.attrs and b.methods:
        ax.plot([b.x, b.x + b.w], [ty + ROW_H / 2 - 3] * 2, color=LINE, lw=1.2, zorder=4)
        ty -= 6
    for text in b.methods:
        italic = text.endswith("*")
        ax.text(b.x + 12, ty, text.rstrip("*"), ha="left", va="center", fontsize=10,
                color=INK, style="italic" if italic else "normal", zorder=4)
        ty -= ROW_H


def path(ax, pts, dashed=False):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=LINE, lw=1.4, zorder=2,
            linestyle=(0, (5, 4)) if dashed else "solid", solid_capstyle="round")


def triangle(ax, tip, direction):
    """Hollow triangle = inheritance, pointing at the parent."""
    x, y = tip
    s = 11
    if direction == "up":
        pts = [(x, y), (x - s, y - s * 1.5), (x + s, y - s * 1.5)]
    elif direction == "down":
        pts = [(x, y), (x - s, y + s * 1.5), (x + s, y + s * 1.5)]
    elif direction == "left":
        pts = [(x, y), (x + s * 1.5, y - s), (x + s * 1.5, y + s)]
    else:
        pts = [(x, y), (x - s * 1.5, y - s), (x - s * 1.5, y + s)]
    ax.add_patch(Polygon(pts, closed=True, facecolor="white", edgecolor=LINE, lw=1.4, zorder=4))


def diamond(ax, at, direction, filled=True):
    """Filled diamond = composition, hollow = aggregation. Sits on the owner."""
    x, y = at
    a, b = 10, 15
    if direction in ("up", "down"):
        d = b if direction == "up" else -b
        pts = [(x, y), (x - a, y + d / 2), (x, y + d), (x + a, y + d / 2)]
    else:
        d = b if direction == "right" else -b
        pts = [(x, y), (x + d / 2, y - a), (x + d, y), (x + d / 2, y + a)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=LINE if filled else "white",
                         edgecolor=LINE, lw=1.4, zorder=4))


def elbow(a, sa, b, sb, mid=None):
    """An orthogonal path between two box anchors."""
    p, q = boxes[a].anchor(sa), boxes[b].anchor(sb)
    if sa in ("top", "bottom") and sb in ("top", "bottom"):
        m = mid if mid is not None else (p[1] + q[1]) / 2
        return [p, (p[0], m), (q[0], m), q]
    if sa in ("left", "right") and sb in ("left", "right"):
        m = mid if mid is not None else (p[0] + q[0]) / 2
        return [p, (m, p[1]), (m, q[1]), q]
    if sa in ("top", "bottom"):
        return [p, (p[0], q[1]), q]
    return [p, (q[0], p[1]), q]


def inherit(ax, child, parent, mid=None, side=("top", "bottom")):
    pts = elbow(child, side[0], parent, side[1], mid)
    path(ax, pts)
    triangle(ax, pts[-1], {"bottom": "up", "top": "down", "left": "right", "right": "left"}[side[1]])


def inherit_bus(ax, children, parent, bus_x):
    """Several classes inheriting one parent, joined by a single vertical run."""
    ys = [boxes[c].anchor("left")[1] for c in children]
    path(ax, [(bus_x, min(ys)), (bus_x, max(ys))])
    for c in children:
        x, y = boxes[c].anchor("left")
        path(ax, [(bus_x, y), (x, y)])
    p = boxes[parent].anchor("right")
    path(ax, [(bus_x, p[1]), p])
    triangle(ax, p, "left")


def owns(ax, owner, part, so, sp, mid=None, filled=True):
    pts = elbow(owner, so, part, sp, mid)
    path(ax, pts)
    diamond(ax, pts[0], {"top": "up", "bottom": "down", "left": "left", "right": "right"}[so], filled)


def uses(ax, src, dst, ss, sd, label=None, mid=None):
    pts = elbow(src, ss, dst, sd, mid)
    path(ax, pts, dashed=True)
    x, y = pts[-1]
    dx, dy = x - pts[-2][0], y - pts[-2][1]
    sx = (dx / abs(dx)) if dx else 0
    sy = (dy / abs(dy)) if dy else 0
    ax.annotate("", xy=(x, y), xytext=(x - sx * 14, y - sy * 14),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.4, mutation_scale=14), zorder=4)
    if label:
        i = len(pts) // 2
        mx = (pts[i - 1][0] + pts[i][0]) / 2
        my = (pts[i - 1][1] + pts[i][1]) / 2
        ax.text(mx, my + 8, label, ha="center", va="bottom", fontsize=9, color=NOTE, zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))


def build():
    # ---------------------------------------------------------- application
    box("Game", 40, 1790, 330,
        ["-screen: Surface", "-scenes: SceneManager", "-save: SaveManager",
         "-audio: AudioEngine", "-controls: Controls"],
        ["+run()", "+start_level(n: int)", "+set_fullscreen(on)"])
    box("SceneManager", 430, 1830, 280, ["-stack: list[Scene]"],
        ["+switch(scene)", "+push(scene)", "+pop()", "+update(dt)", "+draw(surface)"])
    box("Controls", 760, 1851, 250, ["-keymap: dict", "-pads: list"],
        ["+held(action): bool", "+was_pressed(action)", "+consume(action)"])
    box("AudioEngine", 1060, 1851, 250, ["-sfx: dict", "-tracks: dict"],
        ["+play(name, vol)", "+music(name)", "+update_volumes()"])
    box("SaveManager", 1370, 1830, 290, ["-path: str", "-data: dict", "-unlock_all: bool"],
        ["+load()", "+save()", "+level_stats(n)", "+is_unlocked(n): bool", "+set_difficulty(m)"])
    box("Camera", 1710, 1851, 240, ["-x, -y: float", "-trauma: float"],
        ["+follow(target, dt)", "+add_trauma(amount)", "+snap(x, y)"])
    box("Menu", 2010, 1851, 250, ["-items: list[MenuItem]", "-index: int"],
        ["+update(dt, controls)", "+draw(surface)"])

    # ---------------------------------------------------------------- scenes
    box("Scene", 430, 1560, 280, ["#game: Game", "#time: float"],
        ["+enter()*", "+update(dt, events)*", "+draw(surface)*"], stereotype="abstract")
    for i, name in enumerate(SCENE_KIDS):
        # two staggered rows: wide enough for the long names, and the second
        # row's connectors thread up through the gaps in the first
        col, row = i % 4, i // 4
        box(name, 40 + col * 232 + row * 116, 1400 - row * 64, 212, compact=True)
    box("GameScene", 1180, 1500, 360,
        ["-world: World", "-camera: Camera", "-particles: ParticleSystem", "-deaths: int"],
        ["+update(dt, events)", "+draw(surface)", "-_process_world_events()", "-_on_death(cause)"])
    box("RaceScene", 1600, 1640, 250, compact=True)
    box("Ghost", 1640, 1380, 300,
        ["-world: World", "-actions: list", "+par: float", "+finished: bool"],
        ["+step(dt)", "+reset()"])
    box("economy", 2300, 1700, 300, [],
        ["+clear_payout(...)", "+death_payout(paid)"], stereotype="module")
    box("Skin", 2300, 1130, 240,
        ["+id, +name: str", "+body, +scarf: tuple", "+cost: int", "+achievement: str"],
        [], stereotype="dataclass")
    box("Achievement", 2300, 950, 240,
        ["+id, +name: str", "+check: callable", "+skin: str"],
        [], stereotype="dataclass")
    box("Renderer", 2000, 1560, 250, ["-tile_pages: dict"],
        ["+draw_level(world, cam)", "+draw_stains()"])
    box("ParticleSystem", 2000, 1380, 250, ["-parts: list"],
        ["+burst(x, y, kind)", "+update(dt)", "+draw(surface)"])

    # ------------------------------------------------------------ simulation
    box("World", 1180, 1080, 400,
        ["-player: Player", "-blocks, -spikes, -saws: list", "-enemies: list[Enemy]",
         "-triggers, -winds: list", "-state: str", "-events: list"],
        ["+step(dt, move, held, pressed)", "+kill(cause)", "+emit(name, **data)",
         "+solids_touching(x, y, w, h)", "+clone()"])
    box("Player", 1640, 1130, 320,
        ["-x, -y, -vx, -vy: float", "-on_ground: bool", "-coyote, -jump_buffer: float",
         "-grip: float"],
        ["+control(dt, move, held)", "+press_jump()", "+launch(velocity)", "+draw(surface, cam)"])

    # ------------------------------------------------------------ level data
    box("LevelDef", 40, 1060, 330,
        ["+number: int", "+name, +theme: str", "+rows: list[str]", "+triggers: list[Trigger]",
         "+saws, +lasers, +cannons: list", "+winds: list[WindDef]", "+edits: dict", "+act: int"],
        [], stereotype="dataclass")
    box("Trigger", 430, 1160, 280,
        ["+area: tuple", "+actions: list", "+once: bool", "+grounded: bool"],
        [], stereotype="dataclass")
    box("Chunk", 760, 1160, 250, ["+rows: list[str]", "+waypoints: list", "+exit: tuple"],
        [], stereotype="dataclass")
    for i, name in enumerate(["SawDef", "LaserDef", "CannonDef", "WindDef"]):
        box(name, 430 + i * 148, 1020, 138, compact=True)
    box("builder", 760, 880, 250, [],
        ["+build_horizontal(chunks)", "+build_vertical(chunks)"], stereotype="module")
    box("campaign", 40, 880, 330, ["+LEVELS: list[LevelDef]"], [], stereotype="module")

    # -------------------------------------------------------- entity classes
    box("Entity", 1180, 720, 320, ["#rect: Rect"],
        ["+update(dt, world)*", "+draw(surface, cam)*"], stereotype="abstract")
    box("Block", 700, 520, 290, ["+solid: bool"],
        ["+update(dt, world)", "+draw(surface, cam)"])
    box("Hazard", 1560, 520, 290, [],
        ["+hits(px, py, pw, ph): bool*", "+update(dt, world)"], stereotype="abstract")
    box("Enemy", 1980, 340, 250, ["+alive: bool"],
        ["+stomped(world)", "+hits(px, py, pw, ph)"], stereotype="abstract")

    for i, name in enumerate(BLOCK_KIDS):
        box(name, 40 + i * 190, 360, 178, compact=True)
    box("FakeBlock", 40, 240, 178, compact=True)
    box("FlipBlock", 420, 240, 178, compact=True)
    box("BlinkBlock", 610, 240, 178, compact=True)

    for i, name in enumerate(HAZARD_KIDS):
        box(name, 1060 + i * 150, 360, 138, compact=True)
    box("HiddenSpike", 1060, 240, 178, compact=True)

    for i, name in enumerate(ENEMY_KIDS):
        box(name, 1560 + i * 165, 130, 152, compact=True)
    box("SpikeCrawler", 1560, 30, 178, compact=True)

    for i, name in enumerate(LOOSE_ENTITIES):
        box(name, 2560, 820 - i * 80, 240, compact=True)
    box("FakeDoor", 2560, 900, 240, compact=True)


def main():
    build()
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=180)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # ---- relationships, drawn beneath the boxes
    owns(ax, "Game", "SceneManager", "right", "left")
    for part in ["Controls", "AudioEngine", "SaveManager"]:
        owns(ax, "Game", part, "bottom", "bottom", mid=1758)
    owns(ax, "SceneManager", "Scene", "bottom", "top", filled=False)
    for name in SCENE_KIDS:
        inherit(ax, name, "Scene", mid=1500)
    inherit(ax, "GameScene", "Scene", side=("left", "right"), mid=950)
    uses(ax, "Scene", "Menu", "top", "bottom", mid=1782)
    owns(ax, "GameScene", "Camera", "top", "bottom", mid=1812)
    owns(ax, "GameScene", "World", "bottom", "top")
    owns(ax, "GameScene", "Renderer", "right", "left", mid=1780)
    owns(ax, "GameScene", "ParticleSystem", "right", "left", mid=1830)
    owns(ax, "World", "Player", "right", "left")
    inherit(ax, "RaceScene", "GameScene", side=("left", "right"), mid=1570)
    owns(ax, "RaceScene", "Ghost", "bottom", "top")
    owns(ax, "Ghost", "World", "left", "right", mid=1610)
    uses(ax, "GameScene", "economy", "right", "left", mid=1920)
    uses(ax, "Player", "Skin", "right", "left", label="wears")
    uses(ax, "Achievement", "Skin", "top", "bottom", label="unlocks")
    uses(ax, "World", "LevelDef", "top", "top", mid=1310, label="built from")
    owns(ax, "LevelDef", "Trigger", "right", "left")
    uses(ax, "builder", "Chunk", "top", "bottom")
    uses(ax, "campaign", "LevelDef", "top", "bottom")
    for name in ["SawDef", "LaserDef", "CannonDef", "WindDef"]:
        uses(ax, name, "LevelDef", "top", "bottom", mid=1042)
    owns(ax, "World", "Entity", "bottom", "top", mid=1000)

    inherit(ax, "Block", "Entity", side=("right", "left"), mid=1090)
    inherit(ax, "Hazard", "Entity", side=("top", "bottom"), mid=680)
    inherit(ax, "Enemy", "Hazard", side=("top", "bottom"), mid=500)
    inherit_bus(ax, LOOSE_ENTITIES, "Entity", 2500)
    inherit(ax, "FakeDoor", "Door", side=("bottom", "top"))
    for name in BLOCK_KIDS:
        inherit(ax, name, "Block", mid=480)
    inherit(ax, "FakeBlock", "CrumbleBlock")
    inherit(ax, "FlipBlock", "SwitchBlock", mid=330)
    inherit(ax, "BlinkBlock", "SwitchBlock", mid=330)
    for name in HAZARD_KIDS:
        inherit(ax, name, "Hazard", mid=480)
    inherit(ax, "HiddenSpike", "Spike")
    for name in ENEMY_KIDS:
        inherit(ax, name, "Enemy", mid=280)
    inherit(ax, "SpikeCrawler", "Crawler")

    for b in boxes.values():
        draw_box(ax, b)

    ax.text(40, 2085, "DON'T EVEN BOTHER: PURE EVIL EDITION", fontsize=21,
            fontweight="bold", color=INK, va="bottom")
    ax.text(40, 2056, "Class diagram   ·   filled diamond = composition   ·   "
                      "hollow diamond = aggregation   ·   hollow triangle = inheritance   ·   "
                      "dashed = uses", fontsize=11, color=NOTE, va="bottom")

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(root, "UML Diagram.png")
    fig.savefig(out, bbox_inches="tight", facecolor="white", pad_inches=0.3)
    print("wrote", out)


if __name__ == "__main__":
    main()
