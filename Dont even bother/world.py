# I am adding comments for me to easily understand the codes
# world.py - the pure game simulation for one level.
#
# The World knows nothing about drawing or sound. Instead it "emits" events
# (jump, land, death, crumble...) and the GameScene turns those into
# particles, screen shake and audio. Keeping the rules separate like this
# means the same World can be run thousands of times by the level-solver
# tool to prove every level can actually be beaten.
#
# Long levels can have thousands of objects, so objects that never move are
# sorted into "buckets" of 8 columns. Each step only looks at the buckets
# near the player instead of the whole level.

import io
import math
import pickle

import pygame

from settings import (TILE, SPRING_VELOCITY, JUMP_VELOCITY, DEFAULT_ARROW_SPEED, PLAYER_W, PLAYER_H, DIFFICULTIES, PHYSICS_HZ,
                      CRUMBLE_DELAY, FAKE_BLOCK_DELAY, DROP_GRAVITY)
from player import Player
from utils import approach
from enemies import Crawler, SpikeCrawler, Mimic, Swooper, Sentry, Echo, Cannon, Laser, KeyItem
from traps import (FlipBlock, BlinkBlock, ConveyorBlock, IceBlock, SwitchBlock)
from traps import (Block, CrumbleBlock, FakeBlock, InvisibleBlock, Spike, HiddenSpike, Saw, Arrow,
                   Spring, Door, FakeDoor, Checkpoint, Group, rect_overlap)

# Map characters that are drawn as a normal-looking block (used for auto-tiling)
LOOKS_SOLID = set("#~x123456789{}I")
BUCKET = 8                     # columns per spatial bucket


def _bucket_of(x):
    return int(x // TILE) // BUCKET


def _near(buckets, x0, x1):
    """Every object in the buckets touching the x-range [x0, x1] (plus one either side)."""
    for b in range(_bucket_of(x0) - 1, _bucket_of(x1) + 2):
        yield from buckets.get(b, ())


class _Shared:
    """Holds the parts of a World that never change, so copies can share them."""

    def __init__(self):
        self.map = {}

    def share(self, *objects):
        for obj in objects:
            self.map[id(obj)] = obj


class _SharingPickler(pickle.Pickler):
    def __init__(self, file, shared):
        super().__init__(file, protocol=pickle.HIGHEST_PROTOCOL)
        self.shared = shared

    def persistent_id(self, obj):
        key = id(obj)
        return key if key in self.shared else None


class _SharingUnpickler(pickle.Unpickler):
    def __init__(self, file, shared):
        super().__init__(file)
        self.shared = shared

    def persistent_load(self, pid):
        return self.shared[pid]


def apply_edits(level_def, difficulty):
    """The map for a difficulty: Brutal adds its own extra traps on top of the base map."""
    rows = [list(r) for r in level_def.rows]
    for mode in ("normal", "brutal"):
        if mode == "brutal" and difficulty != "brutal":
            break
        for col, row, text in level_def.edits.get(mode, []):
            for i, ch in enumerate(text):
                rows[row][col + i] = ch
    return ["".join(r) for r in rows]


class TriggerRunner:
    """Runs one trigger's action list over time (handles 'wait' and 'repeat')."""

    def __init__(self, actions):
        self.actions = actions
        self.index = 0
        self.wait = 0.0
        self.done = False

    def update(self, world, dt):
        if self.done:
            return
        if self.wait > 0:
            self.wait -= dt
            if self.wait > 0:
                return
        guard = 0
        while self.index < len(self.actions):
            guard += 1
            if guard > 64:          # a 'repeat' with no 'wait' would loop forever
                return
            action = self.actions[self.index]
            self.index += 1
            kind = action[0]
            if kind == "wait":
                self.wait += action[1]
                return
            if kind == "repeat":
                self.index = action[1] if len(action) > 1 else 0
                continue
            world.do_action(action)
            if kind == "move":
                # a move finishes before the script carries on
                self.wait += action[4]
                return
        self.done = True


class World:
    def __init__(self, level_def, difficulty="normal"):
        self.defn = level_def
        self.difficulty = difficulty
        self.diff = DIFFICULTIES[difficulty]
        self.rows = apply_edits(level_def, difficulty)
        self.nrows = len(self.rows)
        self.cols = len(self.rows[0])
        self.width = self.cols * TILE
        self.height = self.nrows * TILE
        self.kill_y = self.height + 80
        brutal = difficulty == "brutal"
        self.trigger_defs = list(level_def.triggers) + (list(level_def.brutal_triggers) if brutal else [])
        self.saw_defs = list(level_def.saws) + (list(level_def.brutal_saws) if brutal else [])
        self.events = []
        self._parse_static()
        self.checkpoint_spawn = None
        self.reset()

        self._shared = _Shared()
        self._shared.share(self._shared, self.defn, self.rows, self.grid, self.ghosts, self.static_spikes,
                           self.static_spike_buckets, self.trigger_defs, self.saw_defs, self.diff)
        for trig in self.trigger_defs:
            self._shared.share(trig, trig.actions)

    # ================================================================ building
    def _char(self, col, row):
        if 0 <= row < self.nrows and 0 <= col < self.cols:
            return self.rows[row][col]
        return "."

    def _legend(self, ch):
        """What does this map character mean? Returns a tuple or None."""
        custom = self.defn.legend.get(ch)
        if custom:
            return custom
        if ch.isdigit():
            return ("block", ch, True)
        return None

    def looks_solid(self, col, row):
        ch = self._char(col, row)
        if ch in LOOKS_SOLID:
            return True
        entry = self._legend(ch)
        return bool(entry and entry[0] == "block" and entry[2])

    def _spike_direction(self, col, row):
        if self.looks_solid(col, row + 1):
            return "up"
        if self.looks_solid(col, row - 1):
            return "down"
        if self.looks_solid(col - 1, row):
            return "right"
        if self.looks_solid(col + 1, row):
            return "left"
        return "up"

    def _parse_static(self):
        """Things that never change: ground grid, fake walls, plain spikes, spawn, checkpoints."""
        self.grid = [[ch == "#" for ch in row] for row in self.rows]
        self.ghosts = []
        self.spawn = (2 * TILE, 13 * TILE)
        self.checkpoints = []
        self.static_spikes = []
        self.static_spike_buckets = {}
        forced = {"v": "down", "<": "left", ">": "right"}
        for r, row in enumerate(self.rows):
            for c, ch in enumerate(row):
                if ch == "~":
                    self.ghosts.append((c, r))
                elif ch == "P":
                    self.spawn = (c * TILE + (TILE - PLAYER_W) // 2, (r + 1) * TILE - PLAYER_H)
                elif ch == "K" and self.diff["checkpoints"]:
                    self.checkpoints.append(Checkpoint(c, r))
                elif ch == "^" or ch in forced:
                    spike = Spike(c, r, forced.get(ch) or self._spike_direction(c, r))
                    self.static_spikes.append(spike)
                    self.static_spike_buckets.setdefault(c // BUCKET, []).append(spike)

    def reset(self):
        """Build every object that can change. Runs at the start and after each death,
        so every trap happens exactly the same way every attempt."""
        spawn = self.checkpoint_spawn or self.spawn
        self.player = Player(*spawn, coyote_time=self.diff["coyote"], buffer_time=self.diff["buffer"])
        self.groups = {}
        self.blocks = []              # every changeable block (for drawing)
        self.loose_buckets = {}       # blocks that aren't in a group, by position
        self.busy = []                # blocks that are currently animating
        self.spikes = []              # hidden + group spikes (static ones live in static_spikes)
        self.hidden_buckets = {}
        self.group_spikes = []
        self.saws = []
        self.arrows = []
        self.springs = []
        self.doors = []
        self.runners = []
        self.fired = set()            # one-shot triggers that already went off
        self.inside = set()           # repeatable triggers the player is standing in
        self.reverse = False
        self.dark = self.defn.dark
        self.enemies = []
        self.orbs = []                # shots from sentries and cannons
        self.switch_blocks = []
        self.flip_state = False       # False = red blocks solid, True = blue blocks solid
        self.key = None
        self.has_key = False
        self.echo = None
        self.echo_steps = 0
        self.trail = []               # the player's recent positions, for the Echo
        self.state = "play"            # play / dead / won
        self.death_cause = None
        self.time = 0.0
        crumble_delay = CRUMBLE_DELAY * self.diff["crumble"]
        fake_delay = FAKE_BLOCK_DELAY * self.diff["fake"]

        for r, row in enumerate(self.rows):
            for c, ch in enumerate(row):
                entry = self._legend(ch)
                if entry:
                    kind, group_name, visible = entry[0], entry[1], entry[2]
                    group = self.groups.get(group_name)
                    if group is None:
                        group = self.groups[group_name] = Group(group_name)
                        group.gravity = DROP_GRAVITY * self.diff["drop_speed"]
                    if kind == "block":
                        obj = Block(c, r, visible=visible)
                        self.blocks.append(obj)
                    else:
                        direction = entry[3] if len(entry) > 3 else self._spike_direction(c, r)
                        obj = Spike(c, r, direction, visible=visible)
                        self.spikes.append(obj)
                        self.group_spikes.append(obj)
                    group.add(obj)
                    continue
                block = None
                if ch == "c":
                    block = CrumbleBlock(c, r, crumble_delay)
                elif ch == "x":
                    block = FakeBlock(c, r, fake_delay)
                elif ch == "i":
                    block = InvisibleBlock(c, r)
                elif ch == "h":
                    spike = HiddenSpike(c, r, self._spike_direction(c, r), self.diff["hidden_range"])
                    self.spikes.append(spike)
                    self.hidden_buckets.setdefault(c // BUCKET, []).append(spike)
                elif ch == "B":
                    self.springs.append(Spring(c, r))
                elif ch == "G":
                    self.doors.append(Door(c, r))
                elif ch == "X":
                    self.doors.append(FakeDoor(c, r))
                elif ch in "eS":
                    cls = Crawler if ch == "e" else SpikeCrawler
                    self.enemies.append(cls(c, r, speed_mult=self.diff["enemy_speed"]))
                elif ch == "m":
                    self.enemies.append(Mimic(c, r))
                elif ch == "u":
                    self.enemies.append(Swooper(c, r, self.diff["enemy_speed"]))
                elif ch == "o":
                    self.enemies.append(Sentry(c, r, rate_mult=self.diff["fire_rate"]))
                elif ch == "k":
                    self.key = KeyItem(c, r)
                elif ch in "RU":
                    block = FlipBlock(c, r, "red" if ch == "R" else "blue")
                elif ch in "TY":
                    block = BlinkBlock(c, r, 0 if ch == "T" else 1)
                elif ch in "{}":
                    block = ConveyorBlock(c, r, -1 if ch == "{" else 1)
                elif ch == "I":
                    block = IceBlock(c, r)
                if isinstance(block, SwitchBlock):
                    self.switch_blocks.append(block)
                if block:
                    self.blocks.append(block)
                    self.loose_buckets.setdefault(c // BUCKET, []).append(block)
        for sd in self.saw_defs:
            self.saws.append(Saw(sd.path, sd.speed * self.diff["saw_speed"], sd.radius, sd.active, sd.mode,
                                 sd.saw_id, sd.track))
        self.triggers = [(pygame.Rect(t.area[0] * TILE, t.area[1] * TILE, t.area[2] * TILE, t.area[3] * TILE), t)
                         for t in self.trigger_defs]
        rate = self.diff["fire_rate"]
        self.lasers = [Laser(d.col, d.row, d.dx, d.dy, d.on, d.off, d.offset, rate) for d in self.defn.lasers]
        self.cannons = [Cannon(d.col, d.row, d.dx, d.dy, d.period, d.speed, d.offset, rate) for d in self.defn.cannons]
        self.winds = [(pygame.Rect(d.area[0] * TILE, d.area[1] * TILE, d.area[2] * TILE, d.area[3] * TILE), d.fx, d.fy)
                      for d in self.defn.winds]

    def clone(self):
        """Fast deep copy (via pickle) that shares the parts that never change.
        Used by the level-solver tool, which copies worlds thousands of times."""
        buffer = io.BytesIO()
        _SharingPickler(buffer, self._shared.map).dump(self)
        buffer.seek(0)
        return _SharingUnpickler(buffer, self._shared.map).load()

    # ================================================================ queries
    def emit(self, event, **data):
        self.events.append((event, data))

    def static_solid_at(self, x, y):
        c, r = int(x // TILE), int(y // TILE)
        return 0 <= r < self.nrows and 0 <= c < self.cols and self.grid[r][c]

    def _dynamic_blocks_near(self, x0, y0, x1, y1):
        """Solid changeable blocks that might overlap the box."""
        for b in _near(self.loose_buckets, x0, x1):
            if b.solid:
                yield b
        for g in self.groups.values():
            if g.present and g.box.right > x0 - TILE and g.box.left < x1 + TILE \
                    and g.box.bottom > y0 - TILE and g.box.top < y1 + TILE:
                for m in g.members:
                    if isinstance(m, Block) and m.solid:
                        yield m

    def solid_at(self, x, y):
        """Static ground or a solid dynamic block at this point? (used by blood stains)"""
        if self.static_solid_at(x, y):
            return True
        for b in self._dynamic_blocks_near(x, y, x, y):
            if b.rect.collidepoint(x, y):
                return True
        return False

    def solids_touching(self, x, y, w, h):
        """Every solid rectangle overlapping the (float) box."""
        found = []
        c0, c1 = max(0, int(x // TILE)), min(self.cols - 1, int((x + w) // TILE))
        r0, r1 = max(0, int(y // TILE)), min(self.nrows - 1, int((y + h) // TILE))
        for r in range(r0, r1 + 1):
            grid_row = self.grid[r]
            for c in range(c0, c1 + 1):
                if grid_row[c]:
                    tile = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                    if rect_overlap(x, y, w, h, tile):
                        found.append(tile)
        for b in self._dynamic_blocks_near(x, y, x + w, y + h):
            if rect_overlap(x, y, w, h, b.rect):
                found.append(b.rect)
        return found

    def blocks_under_player(self):
        p = self.player
        return [b for b in self._dynamic_blocks_near(p.x, p.y, p.x + p.w, p.y + p.h + 1)
                if rect_overlap(p.x, p.y + p.h, p.w, 1, b.rect)]

    @property
    def real_door(self):
        for d in self.doors:
            if not d.is_fake:
                return d
        return None

    # --- helpers used by Group while falling
    def group_would_land(self, group, move):
        return self._group_fall_room(group) < move

    def group_land_distance(self, group, move):
        return max(0.0, min(move, self._group_fall_room(group)))

    def _group_fall_room(self, group):
        room = math.inf
        for m in group.members:
            rect = m.rect
            start_row = int(math.ceil(rect.bottom / TILE))
            for c in range(rect.left // TILE, (rect.right - 1) // TILE + 1):
                for r in range(max(0, start_row), self.nrows):
                    if 0 <= c < self.cols and self.grid[r][c]:
                        room = min(room, r * TILE - rect.bottom)
                        break
        return room

    # ================================================================ actions
    def do_action(self, action):
        kind, args = action[0], action[1:]
        if kind == "drop":
            group = self.groups.get(args[0])
            if group:
                group.start_drop()
                self.emit("drop", x=group.box.centerx, y=group.box.bottom)
        elif kind == "move":
            group = self.groups.get(args[0])
            if group:
                group.start_tween(args[1] * TILE, args[2] * TILE, args[3])
        elif kind == "vanish":
            group = self.groups.get(args[0])
            if group and group.present:
                group.present = False
                for b in group.blocks:
                    self.emit("crumble", rect=b.rect.copy())
        elif kind == "appear":
            group = self.groups.get(args[0])
            if group:
                group.pop = 1.0
                for m in group.members:
                    if isinstance(m, Spike):
                        m.show(self)
                    else:
                        m.visible = True
                self.emit("appear", x=group.box.centerx, y=group.box.centery)
                p = self.player
                for b in group.blocks:
                    if rect_overlap(p.x, p.y, p.w, p.h, b.rect):
                        self.kill("crush")
        elif kind == "say":
            self.emit("say", text=args[0], duration=args[1] if len(args) > 1 else 2.6)
        elif kind == "shake":
            self.emit("shake", amount=args[0])
        elif kind == "sound":
            self.emit("sound", name=args[0])
        elif kind == "goal":
            door = self.real_door
            if door:
                door.hop(self, args[0], args[1])
        elif kind == "saw":
            for saw in self.saws:
                if saw.saw_id == args[0]:
                    saw.activate(self)
        elif kind == "fire":
            col, row, dx, dy = args[0], args[1], args[2], args[3]
            speed = (args[4] if len(args) > 4 else DEFAULT_ARROW_SPEED) * self.diff["arrow_speed"]
            self.arrows.append(Arrow((col + 0.5) * TILE, (row + 0.5) * TILE, dx, dy, speed))
            self.emit("arrow_fire", x=(col + 0.5) * TILE, y=(row + 0.5) * TILE)
        elif kind == "reverse":
            self.reverse = bool(args[0])
            self.emit("reverse", on=self.reverse)
        elif kind == "dark":
            self.dark = bool(args[0])
            self.emit("dark", on=self.dark)
        elif kind == "echo":
            # your shadow starts following you, `args[0]` seconds behind
            if self.echo is None:
                self.echo = Echo(self.player.x, self.player.y)
                self.echo_steps = max(1, int(round(args[0] * PHYSICS_HZ)))
                self.trail = []
                self.emit("echo", x=self.player.centerx, y=self.player.centery)
        else:
            raise ValueError(f"Unknown trigger action: {kind}")

    # ================================================================ life & death
    def kill(self, cause):
        p = self.player
        if not p.alive or self.state != "play":
            return
        p.alive = False
        self.state = "dead"
        self.death_cause = cause
        self.emit("death", cause=cause, x=p.centerx, y=p.centery, vx=p.vx, vy=p.vy)

    def respawn(self):
        """Called by the scene after the death animation."""
        self.reset()
        self.emit("respawn", x=self.player.centerx, y=self.player.centery)

    # ================================================================ main step
    def step(self, dt, move_dir=0, jump_held=False, jump_pressed=False):
        if self.state == "play":
            self.time += dt
        self._run_triggers(dt)
        self._move_groups(dt)
        if self.state == "play":
            self._move_player(dt, move_dir, jump_held, jump_pressed)
        p = self.player
        for obj in self.busy:
            obj.update(self, dt)
        self.busy = [b for b in self.busy if b.busy]
        for obj in _near(self.hidden_buckets, p.x, p.x + p.w):
            obj.update(self, dt)
        for obj in self.group_spikes:
            obj.update(self, dt)
        for obj in self.saws:
            obj.update(self, dt)
        for obj in self.arrows:
            obj.update(self, dt)
        self.arrows = [a for a in self.arrows if not a.dead]
        for obj in self.springs:
            obj.update(self, dt)
        for obj in self.doors:
            obj.update(self, dt)
        for obj in self.checkpoints:
            obj.update(self, dt)
        # blink blocks follow the level clock; switch blocks wait until you've stepped out of them
        if self.switch_blocks:
            beat = int(self.time / self.defn.blink_period) % 2
            for b in self.switch_blocks:
                if isinstance(b, BlinkBlock):
                    b.set_on(b.phase == beat, self)
                b.settle(self)
        for obj in self.enemies:
            obj.update(self, dt)
        for obj in self.cannons:
            obj.update(self, dt)
        for obj in self.lasers:
            obj.update(self, dt)
        for obj in self.orbs:
            obj.update(self, dt)
        self.orbs = [o for o in self.orbs if not o.dead]
        if self.echo is not None and self.state == "play":
            self.trail.append((p.x, p.y))
            if len(self.trail) > self.echo_steps + 1:
                del self.trail[0]
            self.echo.follow(self.trail[0] if len(self.trail) > self.echo_steps else None)
            self.echo.update(self, dt)
        if self.state == "play":
            self._check_interactions()

    def _run_triggers(self, dt):
        p = self.player
        if self.state == "play":
            for i, (area, trig) in enumerate(self.triggers):
                touching = rect_overlap(p.x, p.y, p.w, p.h, area)
                if trig.grounded and not p.on_ground:
                    touching = False    # things like reversed controls wait until you land
                if trig.once:
                    if touching and i not in self.fired:
                        self.fired.add(i)
                        self.runners.append(TriggerRunner(trig.actions))
                elif touching and i not in self.inside:
                    self.inside.add(i)          # fires again every time you walk back in
                    self.runners.append(TriggerRunner(trig.actions))
                elif not touching:
                    self.inside.discard(i)
        for runner in self.runners:
            runner.update(self, dt)
        self.runners = [r for r in self.runners if not r.done]

    def _move_groups(self, dt):
        p = self.player
        standing_on = {b.group for b in self.blocks_under_player() if b.group} if p.alive else set()
        for group in self.groups.values():
            if group.mode == "idle":
                group.dx = group.dy = 0.0
                if group.pop > 0:
                    group.pop = max(0.0, group.pop - dt * 5)
                continue
            dx, dy = group.step(self, dt)
            if not p.alive or (dx == 0 and dy == 0):
                continue
            if group in standing_on:
                p.x += dx
                if dy < 0 or group.mode != "drop":
                    p.y += dy
            for b in group.blocks:
                if not b.solid or not rect_overlap(p.x, p.y, p.w, p.h, b.rect):
                    continue
                if dy > 0 and p.centery > b.rect.centery:
                    self.kill("crush")
                elif dy < 0:
                    p.y = b.rect.top - p.h
                    if p.vy > 0:
                        p.vy = 0.0
                elif dx != 0:
                    p.x = b.rect.right if dx > 0 else b.rect.left - p.w
                    if self.solids_touching(p.x, p.y, p.w, p.h):
                        self.kill("crush")

    def _move_player(self, dt, move_dir, jump_held, jump_pressed):
        p = self.player
        if self.reverse:
            move_dir = -move_dir
        if jump_pressed:
            p.press_jump()
        was_on_ground = p.on_ground
        # what are we standing on? ice is slippery, belts drag you
        under = self.blocks_under_player() if p.on_ground else []
        p.grip = 0.08 if any(isinstance(b, IceBlock) for b in under) else 1.0
        belt = next((b.direction for b in under if isinstance(b, ConveyorBlock)), 0)
        if p.control(dt, move_dir, jump_held):
            self.emit("jump", x=p.centerx, y=p.bottom)
            self._on_player_jump()
        for area, fx, fy in self.winds:
            if rect_overlap(p.x, p.y, p.w, p.h, area):
                p.x += fx * dt           # a steady drift you have to fight against
                if fy:
                    # an updraft carries you at a steady speed, whatever gravity thinks
                    p.vy = approach(p.vy, fy, 12000 * dt)
        if belt:
            p.x += belt * ConveyorBlock.SPEED * dt

        # ---- horizontal move, then resolve walls
        p.x += p.vx * dt
        if p.x < 0:
            p.x, p.vx = 0.0, 0.0
        elif p.x + p.w > self.width:
            p.x, p.vx = float(self.width - p.w), 0.0
        for r in self.solids_touching(p.x, p.y, p.w, p.h):
            if not rect_overlap(p.x, p.y, p.w, p.h, r):
                continue
            if p.vx > 0 or (p.vx == 0 and p.centerx < r.centerx):
                p.x = float(r.left - p.w)
            else:
                p.x = float(r.right)
            p.vx = 0.0

        # ---- vertical move, then resolve floors / ceilings
        prev_top = p.y
        p.y += p.vy * dt
        if p.vy < 0:
            for b in _near(self.loose_buckets, p.x, p.x + p.w):
                if (isinstance(b, InvisibleBlock) and not b.visible
                        and rect_overlap(p.x, p.y, p.w, p.h, b.rect) and prev_top >= b.rect.bottom - 1):
                    b.reveal(self)
                    self.busy.append(b)
        impact = p.vy
        for r in self.solids_touching(p.x, p.y, p.w, p.h):
            if not rect_overlap(p.x, p.y, p.w, p.h, r):
                continue
            if p.vy > 0:
                p.y = float(r.top - p.h)
            elif p.vy < 0:
                p.y = float(r.bottom)
                self.emit("bump", x=p.centerx, y=p.y)
            else:
                if p.centery < r.centery:
                    p.y = float(r.top - p.h)
                else:
                    p.y = float(r.bottom)
            p.vy = 0.0

        # ---- are we standing on something? (1 pixel probe = no flicker)
        p.on_ground = bool(self.solids_touching(p.x, p.y + p.h, p.w, 1)) and p.vy >= 0
        if p.on_ground:
            for b in self.blocks_under_player():
                if isinstance(b, CrumbleBlock) and b.timer is None:
                    b.touch(self)
                    self.busy.append(b)
            if not was_on_ground:
                p.land_impact(impact)
                self.emit("land", x=p.centerx, y=p.bottom, speed=impact)

        if p.y > self.kill_y:
            self.kill("fall")

    def _on_player_jump(self):
        for e in self.enemies:
            if isinstance(e, Mimic):
                e.on_player_jump()
        flips = [b for b in self.switch_blocks if isinstance(b, FlipBlock)]
        if flips:
            self.flip_state = not self.flip_state
            for b in flips:
                b.set_on((b.colour == "red") != self.flip_state, self)
            self.emit("flip", x=self.player.centerx, y=self.player.centery)

    def _check_interactions(self):
        p = self.player
        box = (p.x, p.y, p.w, p.h)
        for e in self.enemies:
            if not e.alive or not e.hits(*box):
                continue
            if e.stompable and p.vy > 0 and p.bottom - e.rect.top < 16:
                e.squash(self)
                p.vy = -JUMP_VELOCITY * 0.7          # bounce off its head
                p.jumping = p.jump_held
                continue
            self.kill(e.cause)
            return
        for thing in (*self.orbs, *self.lasers):
            if thing.hits(*box):
                self.kill(thing.cause)
                return
        if self.echo is not None and self.echo.hits(*box):
            self.kill("echo")
            return
        if self.key and not self.key.taken and rect_overlap(*box, self.key.rect):
            self.key.taken = True
            self.has_key = True
            self.emit("key", x=self.key.rect.centerx, y=self.key.rect.centery)
        for s in _near(self.static_spike_buckets, p.x, p.x + p.w):
            if s.hits(*box):
                self.kill("spike")
                return
        for s in _near(self.hidden_buckets, p.x, p.x + p.w):
            if s.hits(*box):
                self.kill(s.cause)
                return
        for s in self.group_spikes:
            if s.hits(*box):
                self.kill("spike")
                return
        for s in self.saws:
            if s.hits(*box):
                self.kill("saw")
                return
        for a in self.arrows:
            if a.hits(*box):
                self.kill("arrow")
                return
        for spring in self.springs:
            if p.vy >= 0 and rect_overlap(*box, spring.rect) and p.bottom <= spring.rect.top + 14:
                p.y = spring.rect.top - p.h
                p.launch(SPRING_VELOCITY)
                spring.squash = 1.0
                self.emit("spring", x=spring.rect.centerx, y=spring.rect.top)
        for cp in self.checkpoints:
            if not cp.active and rect_overlap(*box, cp.rect):
                for other in self.checkpoints:
                    other.active = False
                cp.active = True
                self.checkpoint_spawn = cp.spawn
                self.emit("checkpoint", x=cp.rect.centerx, y=cp.rect.top)
        for door in self.doors:
            if door.hopping:
                continue
            if rect_overlap(*box, door.hitbox):
                if not door.is_fake and self.key and not self.has_key:
                    continue                    # locked: go and find the key first
                if door.is_fake:
                    self.emit("fake_door", x=door.rect.centerx, y=door.rect.centery)
                    self.kill("fake_goal")
                else:
                    self.state = "won"
                    p.vx *= 0.3
                    self.emit("win", x=door.rect.centerx, y=door.rect.centery)
                return
