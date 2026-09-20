# I am adding comments for me to easily understand the codes
# act3.py - ACT III: THE CLIMB. One giant vertical tower in the spirit of
# Only Up / Getting Over It. Falling doesn't kill you - it just drops you back
# down the tower, which is far worse. Brutal has no checkpoints at all, so
# dying anywhere sends you back to the very bottom.
#
# The tower is built from chunks 32 tiles wide (one screen), stacked bottom to
# top. Inside a chunk, rows are listed top (row 0) to bottom. By convention a
# chunk's first platform is on its bottom row and its last platform is on
# row 1, so every chunk hands over to the next one with a 2-tile climb.

from builder import Chunk, build_vertical
from levels import Trigger, SawDef, WindDef

W = 32


def R(*parts):
    """One 32-wide tower row with text written at the given columns."""
    row = ["."] * W
    for col, text in parts:
        for i, ch in enumerate(text):
            row[col + i] = ch
    return "".join(row)


def rows(spec, height=12):
    """spec = {row: [(col, text), ...]} -> list of rows (top to bottom)."""
    return [R(*spec.get(r, [])) for r in range(height)]


def platform_hints(spec):
    """Route hints for the solver bot: stand on every platform, bottom to top."""
    hints = []
    for r in sorted(spec, reverse=True):
        for col, text in spec[r]:
            if text and set(text) <= set("#xcRUTYI"):
                hints.append((col + len(text) // 2, r - 1))
    return hints[:-1]          # the last platform is the chunk's exit


def tower(spec, height=12, **kwargs):
    """A tower chunk whose solver hints are generated from its platforms."""
    return Chunk(rows(spec, height), waypoints=platform_hints(spec), **kwargs)


# --------------------------------------------------------------- the staircase
# Every ledge sits two rows above the last one, and each chunk walks steadily
# across the tower - right-handed chunks start on the left and finish on the
# right, left-handed ones do the opposite, so they hand over to each other at
# the edges. Walking in ONE direction per chunk matters: in a tight zig-zag the
# ledge four rows up sits directly over your head, your jump bonks into it, and
# the gap becomes impossible. This way you always have clear sky above you.
RIGHT_FLIGHT = [(11, 2, 4), (9, 7, 3), (7, 11, 3), (5, 15, 3), (3, 19, 3), (1, 24, 4)]
LEFT_FLIGHT = [(11, 28, 4), (9, 23, 3), (7, 19, 3), (5, 15, 3), (3, 11, 3), (1, 6, 4)]


def flight(going, tiles=None, extras=(), drop=0, **kwargs):
    """A chunk-high staircase of six ledges, bottom to top.

    `tiles` gives the block for each ledge (one character to fill the whole
    ledge, or the exact text to write), so a chunk can make its ledges ice,
    cracked, blinking and so on. `extras` are (row, col, text) additions.

    `drop` pushes the whole flight down and makes the chunk that much taller,
    which buys headroom above the top ledge. A door is 62px tall in a 40px
    tile, so one standing on row 0 would hang off the top of the world.
    """
    ledges = RIGHT_FLIGHT if going == "right" else LEFT_FLIGHT
    tiles = list(tiles or "######")
    spec = {}
    for (row, col, width), tile in zip(ledges, tiles):
        spec.setdefault(row + drop, []).append((col, tile * width if len(tile) == 1 else tile))
    for row, col, text in extras:
        spec.setdefault(row, []).append((col, text))
    top_row, top_col, top_width = ledges[-1]
    kwargs.setdefault("exit", (top_col + top_width // 2, drop))
    kwargs.setdefault("height", 12 + drop)
    return tower(spec, **kwargs)


def base():
    return Chunk([R((1, "P")), "#" * W, "#" * W], exit=(1, 0))


def stairs():
    """The gentle one. Six ledges, straight up the right-hand side."""
    return flight("right", edits={"brutal": [(10, 7, "x")]})


def crumble_back():
    """Two of the ledges give way under you."""
    return flight("left", tiles="##cc##", edits={"brutal": [(11, 3, "c")]})


def spike_saw():
    """A saw patrols the middle of the staircase and a spike guards a landing."""
    return flight("right", extras=[(6, 12, "^")],
                  saws=[SawDef([(8, 8), (14, 8)], speed=3)],
                  edits={"brutal": [(20, 2, "h")]})


def fakes_checkpoint():
    """Half of these ledges are lies. There's a checkpoint if you get through."""
    return flight("left", tiles=["#", "#x#", "x##", "#x#", "###", "#"],
                  extras=[(10, 29, "K")],
                  edits={"brutal": [(20, 7, "x")]})


def flip_tower():
    """Red and blue ledges swap every time you jump, so plan the whole flight."""
    return flight("right", tiles=["#", "U", "R", "U", "R", "#"],
                  edits={"brutal": [(26, 0, "h")]})


def spring_launch():
    """A spring on the second ledge. It will not ask where you wanted to go."""
    return flight("left", extras=[(8, 24, "B")],
                  saws=[SawDef([(14, 4), (20, 4)], speed=3.5)],
                  edits={"brutal": [(12, 2, "h")]})


def reversed_climb():
    """Left is right in here. Up is still up, which is the only mercy."""
    return flight("right",
                  triggers=[Trigger((0, 10, W, 2), [("reverse", True), ("say", "Up is still up. Left isn't.")],
                                    once=False, grounded=True),
                            Trigger((0, 0, W, 1), [("reverse", False)], once=False)],
                  edits={"brutal": [(12, 6, "h")]})


def swooper_nest():
    """Bats hang over the gaps and dive at wherever you were standing."""
    return flight("left", extras=[(8, 26, "u"), (6, 22, "u"), (4, 18, "u"), (10, 29, "K")],
                  edits={"brutal": [(14, 2, "u")]})


def ice_ledges():
    """Ice. Land, and keep sliding, straight off the far end."""
    return flight("right", tiles=["#", "I", "I", "I", "I", "#"],
                  edits={"brutal": [(22, 3, "I")]})


def crusher_wall():
    """A block sweeps back and forth across the staircase at head height."""
    return flight("left", extras=[(6, 26, "11")],
                  triggers=[Trigger((0, 10, W, 2), [("move", "1", -10, 0, 2.2), ("wait", 0.5),
                                                    ("move", "1", 10, 0, 2.2), ("wait", 0.5), ("repeat", 0)])])


def updraft_shaft():
    """An updraft carries you the last six rows. The ceiling above it bites."""
    spec = {11: [(2, "####")], 9: [(7, "###")], 7: [(11, "###")], 5: [(15, "###")],
            1: [(24, "####")]}
    return Chunk(rows(spec), winds=[WindDef((19, 0, 5, 12), fy=-230)],
                 waypoints=[(3, 10), (8, 8), (12, 6), (16, 4)], exit=(25, 0))


def dark_checkpoint():
    """Lights out. The staircase is still there. Probably."""
    return flight("left", extras=[(10, 29, "K")],
                  triggers=[Trigger((0, 10, W, 2), [("dark", True), ("say", "Mind the gap. All of them.")],
                                    once=False, grounded=True),
                            Trigger((0, 0, W, 1), [("dark", False)], once=False)])


def blink_tower():
    """Ledges that blink in and out to a beat. Two groups take turns."""
    return flight("right", tiles=["#", "T", "Y", "T", "Y", "#"])


def bonk_tower():
    """Invisible blocks stand beside the landings, exactly where you want to be."""
    return flight("left", extras=[(9, 22, "i"), (5, 18, "i")],
                  edits={"brutal": [(10, 3, "i")]})


def sentry_perch():
    """A floating eye watches the whole flight and fires at you."""
    return flight("right", extras=[(4, 7, "o")],
                  edits={"brutal": [(8, 26, "o")]})


def saw_gauntlet():
    """Two saws, both of them in your way."""
    return flight("left", tiles="##cc##",
                  saws=[SawDef([(26, 10), (26, 6)], speed=3), SawDef([(13, 4), (18, 4)], speed=3)],
                  edits={"brutal": [(24, 8, "h")]})


def summit():
    """The top. One of those doors is a lie."""
    return flight("right", drop=1, extras=[(3, 20, "X"), (1, 26, "h"), (1, 25, "G")],
                  edits={"brutal": [(22, 4, "x")]})


def summit_with_echo():
    chunk = summit()
    chunk.triggers = [Trigger((0, 10, W, 3), [("echo", 1.3), ("say", "Your past self wants a word.")])]
    return chunk


ACT3 = [
    build_vertical(19, "The Climb", "EVERY STEP UP IS A STEP YOU CAN LOSE.", "summit", [
        base(), stairs(), crumble_back(), spike_saw(), fakes_checkpoint(), flip_tower(), spring_launch(),
        reversed_climb(), swooper_nest(), ice_ledges(), crusher_wall(), updraft_shaft(), dark_checkpoint(),
        blink_tower(), bonk_tower(), sentry_perch(), saw_gauntlet(), summit_with_echo(),
    ], intro="Up there is the exit. Down here is you.", act=3, music="climb"),
]
