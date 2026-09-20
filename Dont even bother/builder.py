# I am adding comments for me to easily understand the codes
# builder.py - builds long levels out of reusable "chunks".
#
# Act II levels are 300+ tiles long and the Act III tower is 150+ tiles tall.
# Drawing those as one giant text map would be unreadable, so instead each
# obstacle is a small Chunk (its own little map with its own triggers and
# saws) and a level is just a list of chunks glued together.
#
# The builder takes care of the fiddly parts:
#   * moving every trigger, saw and arrow to the chunk's real position
#   * giving each chunk its own private copy of trigger groups, so two
#     chunks that both use group "1" don't control each other's blocks
#   * adding a route hint (waypoint) at the end of every chunk for the solver

from dataclasses import dataclass, field, replace

from levels import LevelDef, Trigger, SawDef

HEIGHT = 18                    # every horizontal chunk is a full screen tall
_PRIVATE_CHAR = 0xE000         # unicode "private use" characters for renamed groups

GROUP_ACTIONS = ("drop", "move", "vanish", "appear")


@dataclass
class Chunk:
    rows: list
    legend: dict = field(default_factory=dict)
    triggers: list = field(default_factory=list)
    saws: list = field(default_factory=list)
    lasers: list = field(default_factory=list)
    cannons: list = field(default_factory=list)
    winds: list = field(default_factory=list)
    edits: dict = field(default_factory=dict)          # {"normal": [...], "brutal": [...]} local coords
    brutal_triggers: list = field(default_factory=list)
    brutal_saws: list = field(default_factory=list)
    waypoints: list = field(default_factory=list)      # extra local hints; the exit is added automatically
    exit: tuple = None                                 # local (col, row) where the chunk ends

    @property
    def width(self):
        return len(self.rows[0])

    @property
    def height(self):
        return len(self.rows)


def bottom(*rows, height=HEIGHT):
    """Write only the bottom rows of a horizontal chunk; the sky above is added for you.
    Tuples repeat a row: ("#####", 3)."""
    out = []
    for r in rows:
        if isinstance(r, tuple):
            out.extend([r[0]] * r[1])
        else:
            out.append(r)
    width = max(len(r) for r in out)
    for i, r in enumerate(out):
        if len(r) != width:
            raise ValueError(f"chunk row {i} is {len(r)} wide, expected {width}: {r!r}")
    return ["." * width] * (height - len(out)) + out


class _Renamer:
    """Gives every chunk instance its own private group names and map characters."""

    def __init__(self):
        self.next_char = _PRIVATE_CHAR
        self.legend = {}

    def chunk_map(self, index, chunk):
        mapping = {}
        chars = set("".join(chunk.rows))
        for mode_edits in chunk.edits.values():
            for _, _, text in mode_edits:
                chars.update(text)
        for ch in sorted(chars):
            entry = chunk.legend.get(ch)
            if entry is None and ch.isdigit():
                entry = ("block", ch, True)
            if entry is None:
                continue
            new_ch = chr(self.next_char)
            self.next_char += 1
            mapping[ch] = new_ch
            self.legend[new_ch] = (entry[0], f"{index}.{entry[1]}", *entry[2:])
        return mapping


def _move_action(action, index, dc, dr):
    kind = action[0]
    if kind in GROUP_ACTIONS:
        return (kind, f"{index}.{action[1]}", *action[2:])
    if kind == "saw":
        return (kind, f"{index}.{action[1]}")
    if kind == "fire":
        return (kind, action[1] + dc, action[2] + dr, *action[3:])
    if kind == "goal":
        return (kind, action[1] + dc, action[2] + dr)
    return action


def _move_def(d, dc, dr):
    """Shift a LaserDef / CannonDef / WindDef by the chunk's position."""
    if hasattr(d, "area"):
        c, r, w, h = d.area
        return replace(d, area=(c + dc, r + dr, w, h))
    return replace(d, col=d.col + dc, row=d.row + dr)


def _move_trigger(trig, index, dc, dr):
    c, r, w, h = trig.area
    return Trigger((c + dc, r + dr, w, h), [_move_action(a, index, dc, dr) for a in trig.actions],
                   trig.once, trig.grounded)


def _move_saw(saw, index, dc, dr):
    return replace(saw, path=[(c + dc, r + dr) for c, r in saw.path],
                   saw_id=f"{index}.{saw.saw_id}" if saw.saw_id else None)


def _translate(text, mapping):
    return "".join(mapping.get(ch, ch) for ch in text)


def _assemble(chunks, placements, total_w, total_h):
    """placements[i] = (col offset, row offset) of chunk i. Returns the merged pieces."""
    renamer = _Renamer()
    grid = [["."] * total_w for _ in range(total_h)]
    triggers, saws, brutal_triggers, brutal_saws, waypoints = [], [], [], [], []
    extras = {"lasers": [], "cannons": [], "winds": []}
    edits = {"normal": [], "brutal": []}
    for i, (chunk, (dc, dr)) in enumerate(zip(chunks, placements)):
        mapping = renamer.chunk_map(i, chunk)
        for r, row in enumerate(chunk.rows):
            for c, ch in enumerate(row):
                grid[r + dr][c + dc] = mapping.get(ch, ch)
        triggers += [_move_trigger(t, i, dc, dr) for t in chunk.triggers]
        brutal_triggers += [_move_trigger(t, i, dc, dr) for t in chunk.brutal_triggers]
        saws += [_move_saw(s, i, dc, dr) for s in chunk.saws]
        brutal_saws += [_move_saw(s, i, dc, dr) for s in chunk.brutal_saws]
        for name in extras:
            extras[name] += [_move_def(d, dc, dr) for d in getattr(chunk, name)]
        for mode, mode_edits in chunk.edits.items():
            edits[mode] += [(c + dc, r + dr, _translate(text, mapping)) for c, r, text in mode_edits]
        waypoints += [(c + dc, r + dr) for c, r in chunk.waypoints]
        exit_c, exit_r = chunk.exit if chunk.exit else (chunk.width - 1, 14)
        waypoints.append((exit_c + dc, exit_r + dr))
    rows = ["".join(r) for r in grid]
    return rows, renamer.legend, triggers, saws, edits, brutal_triggers, brutal_saws, waypoints, extras


def build_horizontal(number, name, tagline, theme, chunks, **extra):
    """Chunks placed left to right. Each is 18 rows tall."""
    placements, x = [], 0
    for ch in chunks:
        if ch.height != HEIGHT:
            raise ValueError(f"horizontal chunks must be {HEIGHT} rows tall")
        placements.append((x, 0))
        x += ch.width
    rows, legend, trig, saws, edits, btrig, bsaws, wps, more = _assemble(chunks, placements, x, HEIGHT)
    return LevelDef(number, name, tagline, theme, rows, legend=legend, triggers=trig, saws=saws, edits=edits,
                    brutal_triggers=btrig, brutal_saws=bsaws, waypoints=wps[:-1], **more, **extra)


def build_vertical(number, name, tagline, theme, chunks, **extra):
    """Chunks stacked from the bottom (first in the list) to the top. All must be the same width."""
    width = chunks[0].width
    total_h = sum(ch.height for ch in chunks)
    placements, y = [], total_h
    for ch in chunks:
        if ch.width != width:
            raise ValueError("vertical chunks must all be the same width")
        y -= ch.height
        placements.append((0, y))
    rows, legend, trig, saws, edits, btrig, bsaws, wps, more = _assemble(chunks, placements, width, total_h)
    return LevelDef(number, name, tagline, theme, rows, legend=legend, triggers=trig, saws=saws, edits=edits,
                    brutal_triggers=btrig, brutal_saws=bsaws, waypoints=wps[:-1], **more, **extra)
