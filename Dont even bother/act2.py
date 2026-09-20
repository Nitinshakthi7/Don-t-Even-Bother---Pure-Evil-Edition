# I am adding comments for me to easily understand the codes
# act2.py - ACT II: THE GAUNTLET. Eight long Geometry-Dash style runs built from
# reusable obstacle chunks (see builder.py). Every chunk is 18 rows tall; the
# floor is rows 15-17 and the player runs along row 14.
#
# Physics cheat sheet (1 tile = 40 px):
#   full jump   ~3.4 tiles high, ~4.6 tiles far on flat ground
#   tap jump    ~1 tile high      (hold jump longer to go higher)

from builder import Chunk, bottom, build_horizontal
from levels import Trigger, SawDef, LaserDef, CannonDef, WindDef

FLOOR_ROWS = 3


def R(width, *parts):
    """One map row: dots, with text written at the given columns. R(8, (2, "P")) -> '..P.....'"""
    row = ["."] * width
    for col, text in parts:
        for i, ch in enumerate(text):
            row[col + i] = ch
    return "".join(row)


def floor(width, gaps=(), char="#"):
    """The three ground rows, with holes at the given columns."""
    line = "".join("." if c in gaps else char for c in range(width))
    return [line] * FLOOR_ROWS


def whole_column(col, width=1):
    """Trigger area covering the full height of a chunk at this column."""
    return (col, 0, width, 18)


# ============================================================== basic pieces
def start():
    return Chunk(bottom(R(8, (2, "P")), *floor(8)))


def rest():
    """A breather with a checkpoint (Normal only). In Brutal the breather has teeth."""
    return Chunk(bottom(R(7, (3, "K")), *floor(7)), edits={"brutal": [(5, 14, "h")]})


def finish():
    return Chunk(bottom(R(10, (6, "G")), *floor(10)))


def spikes(n=2):
    w = n + 6
    return Chunk(bottom(R(w, (3, "^" * n)), *floor(w)))


def pit(n=3):
    w = n + 6
    return Chunk(bottom(R(w), *floor(w, gaps=range(3, 3 + n))))


def island():
    """Two pits with a single-tile pillar between them."""
    return Chunk(bottom(R(13), *floor(13, gaps=(3, 4, 5, 7, 8, 9))))


def spiked_island():
    """Two pits and a 3-wide island with a spike in the middle: land on the edge."""
    return Chunk(bottom(R(15, (7, "^")), *floor(15, gaps=(3, 4, 5, 9, 10, 11))))


def saw_runner(speed=4.0):
    """A saw rolling back and forth along the ground. Jump it."""
    return Chunk(bottom(R(12), *floor(12)), saws=[SawDef([(2, 14), (9, 14)], speed=speed)])


def pit_saw(speed=4.0):
    """A saw bobbing up and down out of a pit you have to jump."""
    return Chunk(bottom(R(10), *floor(10, gaps=(3, 4, 5))),
                 saws=[SawDef([(4, 12), (4, 16)], speed=speed, track=False)])


def ceiling_tunnel():
    """Low spiked ceiling: small taps only, a full jump kills you."""
    return Chunk(bottom(R(14, (1, "#" * 12)), R(14, (1, "v" * 12)), R(14), R(14, (5, "^"), (9, "^")), *floor(14)),
                 edits={"brutal": [(7, 14, "h")]})


def crumble_bridge(n=8):
    w = n + 4
    return Chunk(bottom(R(w), "##" + "c" * n + "##", ("##" + "." * n + "##", 2)))


def collapse_bridge(n=4):
    """Solid-looking bridge that drops the moment you walk on it."""
    w = n + 4
    return Chunk(bottom(R(w), "##" + "1" * n + "##", ("##" + "1" * n + "##", 2)),
                 triggers=[Trigger((2, 10, n, 5), [("drop", "1"), ("sound", "rumble")])])


def hidden_runway():
    return Chunk(bottom(R(14, (4, "h"), (8, "h"), (11, "h")), *floor(14)),
                 edits={"brutal": [(6, 14, "h")]})


def fake_door():
    return Chunk(bottom(R(10, (5, "X")), *floor(10)))


def spring_gap():
    """Spring over a wide pit, with a saw bobbing through the flight path."""
    return Chunk(bottom(R(14, (2, "B")), *floor(14, gaps=range(3, 8))),
                 saws=[SawDef([(5, 3), (5, 10)], speed=3.5)])     # time your jump onto the spring


def moving_platform():
    return Chunk(bottom(R(16), "##111" + "." * 9 + "##", ("##" + "." * 12 + "##", 2)),
                 triggers=[Trigger(whole_column(0), [("move", "1", 8, 0, 1.8), ("wait", 0.3),
                                                     ("move", "1", -8, 0, 1.8), ("wait", 0.3), ("repeat", 0)])])


def pillars():
    """Climb three pillars over a spike floor, then drop."""
    return Chunk(bottom(R(15, (9, "#")),
                        R(15, (9, "#")),
                        R(15, (6, "#"), (9, "#")),
                        R(15, (6, "#"), (9, "#")),
                        R(15, (3, "#"), (6, "#"), (9, "#")),
                        R(15, (3, "#"), (4, "^^"), (6, "#"), (7, "^^"), (9, "#"), (10, "^^^")),
                        *floor(15)))


def thwomps():
    """Three ceiling crushers that drop as you pass. Stop, let them fall, hop over."""
    rows = bottom(*[R(15, (0, "#" * 15))] * 10,
                  R(15, (0, "###"), (3, "11"), (5, "##"), (7, "22"), (9, "##"), (11, "33"), (13, "##")),
                  R(15, (3, "aa"), (7, "bb"), (11, "cc")),
                  R(15), R(15), R(15), *floor(15))
    return Chunk(rows, legend={"a": ("spike", "1", True), "b": ("spike", "2", True), "c": ("spike", "3", True)},
                 triggers=[Trigger((1, 11, 2, 4), [("drop", "1")]),
                           Trigger((5, 11, 2, 4), [("drop", "2")]),
                           Trigger((9, 11, 2, 4), [("drop", "3")])])


def pistons():
    rows = bottom(*[R(14, (0, "#" * 14))] * 4,
                  *[R(14, (4, "11"), (9, "22"))] * 5,
                  *[R(14)] * 6, *floor(14))
    slam = [("move", "1", 0, 6, 0.12), ("shake", 0.3), ("sound", "slam"), ("wait", 0.35),
            ("move", "1", 0, -6, 0.7), ("wait", 0.5)]
    return Chunk(rows, triggers=[
        Trigger(whole_column(1), slam + [("repeat", 0)]),
        Trigger(whole_column(1), [("wait", 0.8)] + [(a[0], "2", *a[2:]) if a[0] == "move" else a for a in slam]
                + [("repeat", 1)]),
    ])


def arrow_volley():
    """Arrows from ahead: low (jump), high (stay down), low again."""
    return Chunk(bottom(R(16), *floor(16)), triggers=[
        Trigger((2, 9, 1, 6), [("fire", 15, 14, -1, 0, 11), ("wait", 0.75), ("fire", 15, 12, -1, 0, 11),
                               ("wait", 0.75), ("fire", 15, 14, -1, 0, 11)])])


def invisible_bonk():
    """A pit with an invisible block right where your head goes."""
    return Chunk(bottom(R(12, (5, "i")), R(12), R(12), R(12), *floor(12, gaps=(4, 5, 6))))


def saw_ceiling_run():
    """Low tunnel with a small saw sweeping at head height, and a gap you must tap over."""
    return Chunk(bottom(R(16, (1, "#" * 14)), R(16), R(16), R(16), *floor(16, gaps=(8,))),
                 saws=[SawDef([(2, 12), (13, 12)], speed=3.5, radius=0.5)])


def stairs_spikes():
    return Chunk(bottom(R(14, (6, "^^")), R(14, (4, "######")), R(14, (4, "######")), *floor(14)))


def double_pit():
    return Chunk(bottom(R(16, (7, "h")), *floor(16, gaps=(3, 4, 5, 9, 10, 11))))


def trigger_chunk(actions, width=4):
    return Chunk(bottom(R(width), *floor(width)), triggers=[Trigger(whole_column(0, width), actions)])


def dark(on):
    return trigger_chunk([("dark", on)] + ([("say", "Lights out. Good luck.")] if on else []))


def reverse(on):
    return trigger_chunk([("reverse", on)] + ([("say", "Left. Right. Whatever.")] if on else []))


# ============================================================== creatures & machines
def bumped(width, *parts):
    """A floor with a one-tile bump at each end, so walking enemies stay in their pen."""
    return bottom(R(width, (0, "#"), (width - 1, "#"), *parts), *floor(width))


def crawler_patrol():
    """Two walkers. Jump over them, or jump ON them."""
    return Chunk(bumped(16, (5, "e"), (11, "e")), edits={"brutal": [(8, 14, "e")]})


def spike_crawlers():
    """Walkers with spiky backs: stomping is suicide, so jump clean over."""
    return Chunk(bumped(16, (5, "S"), (11, "S")))


def sentry_alley():
    """A floating eye that fires at wherever you are standing. Keep moving."""
    return Chunk(bottom(R(18, (9, "o")), R(18), R(18), R(18), R(18), R(18, (6, "^"), (12, "^")), *floor(18)),
                 edits={"brutal": [(14, 9, "o")]})


def swooper_cave():
    """Bats hang from the ceiling and dive at the spot where you were."""
    rows = bottom(*[R(16, (0, "#" * 16))] * 9, R(16, (4, "u"), (9, "u"), (13, "u")),
                  R(16), R(16), R(16), R(16, (7, "^")), *floor(16))
    return Chunk(rows)


def mimic_gate():
    """It jumps when you jump. Tap-jump to make it leap, then run underneath."""
    return Chunk(bottom(R(12, (7, "m")), *floor(12)))


def flip_bridge():
    """Red and blue blocks swap every time you jump. Count your jumps."""
    return Chunk(bottom(R(16), "##..UU..RR..UU##", ("##............##", 2)))


def blink_bridge():
    """Blocks that appear and vanish on a beat."""
    return Chunk(bottom(R(16), "##..TT..YY..TT##", ("##............##", 2)))


def conveyor_run():
    """A belt dragging you backwards, with spikes to hop on the way."""
    return Chunk(bottom(R(16, (7, "^^")), "#" + "{" * 14 + "#", ("#" * 16, 2)))


def ice_slide():
    """Ice. You will not stop in time. Jump the spike, then the pit."""
    return Chunk(bottom(R(18, (7, "^")), "##" + "I" * 10 + "..." + "###", ("#" * 12 + "..." + "###", 2)))


def updraft_gap():
    """A pit far too wide to jump - but an updraft will carry you. Don't jump into it."""
    rows = bottom(R(16, (3, "#" * 10)), R(16, (3, "v" * 10)), R(16), R(16), R(16), R(16), R(16), R(16),
                  *floor(16, gaps=range(3, 13)))
    return Chunk(rows, winds=[WindDef((4, 0, 8, 18), fy=-150)])


def laser_hall():
    """Three lasers from the ceiling, fired in a rolling wave."""
    rows = bottom(*[R(16, (0, "#" * 16))] * 9, *[R(16)] * 6, *floor(16))
    return Chunk(rows, lasers=[LaserDef(4, 8, 0, 1, on=0.7, off=1.9, offset=0.0),
                               LaserDef(8, 8, 0, 1, on=0.7, off=1.9, offset=0.9),
                               LaserDef(12, 8, 0, 1, on=0.7, off=1.9, offset=1.8)])


def mortar_rain():
    """Cannons in the ceiling drop heavy balls on a rhythm."""
    rows = bottom(*[R(16, (0, "#" * 16))] * 9, *[R(16)] * 6, *floor(16))
    return Chunk(rows, cannons=[CannonDef(4, 8, 0, 1, period=1.8, speed=7, offset=0.3),
                                CannonDef(8, 8, 0, 1, period=1.8, speed=7, offset=0.9),
                                CannonDef(12, 8, 0, 1, period=1.8, speed=7, offset=1.5)])


def key_ledge():
    """The exit is locked. The key is up there."""
    return Chunk(bottom(R(14, (11, "k")), R(14, (10, "###")), R(14), R(14, (7, "##")), R(14),
                        R(14, (4, "##")), R(14), *floor(14)),
                 waypoints=[(5, 12), (8, 10), (11, 8)])


def echo_start(delay=1.6):
    return trigger_chunk([("echo", delay)], width=6)


# ============================================================== the eight runs
ACT2 = [
    build_horizontal(11, "Warm Welcome", "YOU THOUGHT THAT WAS HARD?", "neon", [
        start(), spikes(2), pit(3), crawler_patrol(), saw_runner(4), spikes(3), pit(4), rest(),
        island(), ceiling_tunnel(), collapse_bridge(4), flip_bridge(), hidden_runway(), rest(),
        thwomps(), pit_saw(4), mimic_gate(), fake_door(), stairs_spikes(), finish(),
    ], intro="Act One was the tutorial. Welcome to the game.", act=2, music="gauntlet"),

    build_horizontal(12, "Saw Mill", "EVERYTHING SPINS. EVERYTHING CUTS.", "foundry", [
        start(), saw_runner(4.5), pit_saw(4), saw_ceiling_run(), spikes(2), rest(),
        mortar_rain(), spring_gap(), saw_runner(5.5), pit_saw(5), pillars(), rest(),
        laser_hall(), pit_saw(5.5), saw_runner(6.5), island(), saw_ceiling_run(), finish(),
    ], intro="Mind the blades. Or don't. I'm not your mum.", act=2, music="gauntlet"),

    build_horizontal(13, "Glass Floor", "DON'T STOP. DON'T EVER STOP.", "frost", [
        start(), collapse_bridge(3), crumble_bridge(8), pit(3), ice_slide(), collapse_bridge(4), rest(),
        crumble_bridge(10), blink_bridge(), island(), hidden_runway(), invisible_bonk(), rest(),
        conveyor_run(), collapse_bridge(4), ice_slide(), crumble_bridge(12), double_pit(), finish(),
    ], intro="The floor is lying. The floor is always lying.", act=2, music="gauntlet"),

    build_horizontal(14, "Pinball", "BOING. SPLAT. BOING. SPLAT.", "neon", [
        start(), spring_gap(), spikes(3), updraft_gap(), spring_gap(), pillars(), rest(),
        moving_platform(), mimic_gate(), spring_gap(), pit(4), rest(),
        updraft_gap(), moving_platform(), spiked_island(), crawler_patrol(), spring_gap(), finish(),
    ], intro="Springs! Fun! (It won't be fun.)", act=2, music="gauntlet"),

    build_horizontal(15, "Clockwork", "EVERYTHING HERE HAS A RHYTHM. YOU DON'T.", "foundry", [
        start(), pistons(), laser_hall(), moving_platform(), thwomps(), rest(),
        blink_bridge(), pistons(), arrow_volley(), mortar_rain(), rest(),
        thwomps(), laser_hall(), blink_bridge(), pistons(), spiked_island(), finish(),
    ], intro="Count the beats. Die on the off-beat.", act=2, music="gauntlet"),

    build_horizontal(16, "Whiteout", "YOU WON'T SEE THIS ONE COMING. LITERALLY.", "frost", [
        start(), dark(True), spikes(2), pit(3), swooper_cave(), island(), rest(),
        ceiling_tunnel(), collapse_bridge(4), dark(False), sentry_alley(), fake_door(), rest(),
        echo_start(1.8), dark(True), pit_saw(4), pillars(), swooper_cave(), double_pit(), dark(False), finish(),
    ], intro="Hope you memorised Act One.", act=2, music="gauntlet"),

    build_horizontal(17, "Overclocked", "LEFT IS RIGHT AND FAST IS SLOW.", "neon", [
        start(), reverse(True), spikes(2), pit(3), island(), reverse(False), conveyor_run(), rest(),
        saw_runner(7), flip_bridge(), pit_saw(6), arrow_volley(), spike_crawlers(), rest(),
        echo_start(1.5), reverse(True), ceiling_tunnel(), collapse_bridge(3), reverse(False),
        mimic_gate(), spring_gap(), saw_ceiling_run(), finish(),
    ], intro="Everything is faster now. Especially your deaths.", act=2, music="gauntlet"),

    build_horizontal(18, "The Gauntlet", "EVERYTHING. AGAIN. LONGER.", "abyss", [
        start(), spikes(3), pit(4), crawler_patrol(), island(), saw_runner(6), rest(),
        thwomps(), pistons(), laser_hall(), ceiling_tunnel(), rest(),
        collapse_bridge(4), hidden_runway(), flip_bridge(), spring_gap(), pit_saw(5), key_ledge(), rest(),
        moving_platform(), arrow_volley(), mortar_rain(), pillars(), invisible_bonk(), sentry_alley(), rest(),
        echo_start(1.4), swooper_cave(), fake_door(), saw_ceiling_run(), spike_crawlers(), double_pit(),
        ice_slide(), spiked_island(), stairs_spikes(), finish(),
    ], intro="This is the last flat ground you will ever see.", act=2, music="abyss"),
]
