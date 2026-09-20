# I am adding comments for me to easily understand the codes
# traps.py - every object in a level that isn't plain ground.
#
# Class tree (this is the OOP heart of the game):
#
#   Entity (abstract)
#   |-- Block                 solid square the player can stand on
#   |   |-- CrumbleBlock      cracked, falls shortly after you stand on it
#   |   |   `-- FakeBlock     looks 100% normal, falls almost instantly
#   |   |-- InvisibleBlock    invisible until you hit it from below
#   |   |-- SwitchBlock       turns solid / ghostly by itself
#   |   |   |-- FlipBlock     red & blue swap every time you jump
#   |   |   `-- BlinkBlock    appear and vanish on a beat
#   |   |-- ConveyorBlock     drags you along
#   |   `-- IceBlock          slippery
#   |-- Hazard (abstract)     anything that kills on touch
#   |   |-- Spike
#   |   |   `-- HiddenSpike   pops out of the floor when you step near it
#   |   |-- Saw               spinning blade that follows a path
#   |   `-- Arrow             flies in a straight line
#   |-- Spring                launches you upwards
#   |-- Door                  the exit
#   |   `-- FakeDoor          ...or is it
#   `-- Checkpoint
#
#   Group                     a named set of Blocks/Spikes that level
#                             triggers can drop, move, hide or reveal.
#
# All positions are world pixels. `cam` is the camera's (x, y) top-left.
# Nothing here stores images, so a whole level can be copied cheaply
# (the level-solver tool relies on that).

import math
from abc import ABC, abstractmethod

import pygame

from settings import (TILE, CRUMBLE_DELAY, FAKE_BLOCK_DELAY, HIDDEN_SPIKE_RANGE,
                      HIDDEN_SPIKE_HEIGHT, DROP_GRAVITY, GOLD, INK, PAPER, MUTED)
from utils import ease_in_out, lerp
from graphics import draw_door

FALL_AWAY = 1600   # how far falling blocks drop before they disappear


def rect_overlap(ax, ay, aw, ah, r):
    """Float rectangle vs pygame.Rect overlap (touching edges do NOT count)."""
    return ax < r.right and ax + aw > r.left and ay < r.bottom and ay + ah > r.top


# ================================================================== base classes
class Entity(ABC):
    """Anything that lives in the level."""

    def __init__(self, x, y, w, h):
        self.base = pygame.Rect(x, y, w, h)   # where it was placed
        self.rect = self.base.copy()          # where it is now
        self.group = None

    def sync_group(self):
        """Follow the group's offset (for moving / falling groups)."""
        if self.group is not None:
            self.rect.topleft = (self.base.x + round(self.group.ox), self.base.y + round(self.group.oy))

    def update(self, world, dt):
        pass

    @abstractmethod
    def draw(self, surface, cam, art, t):
        ...


class Hazard(Entity):
    """Something that kills the player on touch."""

    cause = "spike"

    @abstractmethod
    def hits(self, px, py, pw, ph):
        ...


# ================================================================== blocks
class Block(Entity):
    """A solid tile. Plain level ground is baked into a grid for speed;
    Block objects are only used for tiles that can change."""

    def __init__(self, col, row, visible=True):
        super().__init__(col * TILE, row * TILE, TILE, TILE)
        self.col, self.row = col, row
        self.visible = visible

    @property
    def solid(self):
        return self.visible and (self.group is None or self.group.present)

    def draw(self, surface, cam, art, t):
        if not self.solid:
            return
        img = art.block_image(self)
        lift = int(math.sin(self.group.pop * math.pi) * 6) if self.group else 0
        surface.blit(img, (self.rect.x - cam[0], self.rect.y - cam[1] - lift))


class CrumbleBlock(Block):
    """Stand on it and it starts shaking... then falls away."""

    cracked = True

    def __init__(self, col, row, delay=CRUMBLE_DELAY):
        super().__init__(col, row)
        self.delay = delay
        self.timer = None      # None = not triggered yet
        self.falling = False
        self.fall_y = 0.0
        self.fall_v = 0.0

    @property
    def solid(self):
        return not self.falling

    @property
    def busy(self):
        """Still needs updating (shaking or falling)."""
        return self.timer is not None and self.fall_y < FALL_AWAY

    def touch(self, world):
        if self.timer is None:
            self.timer = self.delay
            world.emit("crumble_start", x=self.rect.centerx, y=self.rect.top)

    def update(self, world, dt):
        if self.timer is not None and not self.falling:
            self.timer -= dt
            if self.timer <= 0:
                self.falling = True
                world.emit("crumble", rect=self.rect.copy())
        if self.falling and self.fall_y < FALL_AWAY:
            self.fall_v += DROP_GRAVITY * 0.6 * dt
            self.fall_y += self.fall_v * dt

    def draw(self, surface, cam, art, t):
        if self.fall_y >= FALL_AWAY:
            return
        img = art.block_image(self)
        shake = 0
        if self.timer is not None and not self.falling:
            shake = int(math.sin(t * 90) * 2)
        surface.blit(img, (self.rect.x - cam[0] + shake, self.rect.y + self.fall_y - cam[1]))


class FakeBlock(CrumbleBlock):
    """Identical to normal ground. Is not normal ground."""

    cracked = False

    def __init__(self, col, row, delay=FAKE_BLOCK_DELAY):
        super().__init__(col, row, delay)


class InvisibleBlock(Block):
    """Can't be seen or stood on - until you bonk it from below. Then it's very solid."""

    def __init__(self, col, row):
        super().__init__(col, row, visible=False)
        self.reveal_anim = 0.0

    @property
    def busy(self):
        return self.reveal_anim > 0

    def reveal(self, world):
        if not self.visible:
            self.visible = True
            self.reveal_anim = 1.0
            world.emit("reveal", x=self.rect.centerx, y=self.rect.centery)

    def update(self, world, dt):
        self.reveal_anim = max(0.0, self.reveal_anim - dt * 4)

    def draw(self, surface, cam, art, t):
        if not self.visible:
            return
        img = art.block_image(self)
        lift = int(math.sin(self.reveal_anim * math.pi) * 8)
        surface.blit(img, (self.rect.x - cam[0], self.rect.y - cam[1] - lift))


class SwitchBlock(Block):
    """Base for blocks that turn solid / ghostly by themselves.
    If a block switches on while you're inside it, it waits until you've left
    (so it never traps you unfairly)."""

    def __init__(self, col, row, on):
        super().__init__(col, row)
        self.on = on
        self.waiting = False          # wants to be solid, but the player is inside it

    @property
    def solid(self):
        return self.on and not self.waiting

    def set_on(self, on, world):
        if on == self.on:
            return
        self.on = on
        p = world.player
        self.waiting = on and rect_overlap(p.x, p.y, p.w, p.h, self.rect)

    def settle(self, world):
        if self.waiting:
            p = world.player
            self.waiting = rect_overlap(p.x, p.y, p.w, p.h, self.rect)

    def _draw_switch(self, surface, cam, fill, edge):
        r = self.rect.move(-cam[0], -cam[1])
        if self.solid:
            pygame.draw.rect(surface, fill, r, border_radius=4)
            pygame.draw.rect(surface, edge, r, 3, border_radius=4)
            light = tuple(min(255, c + 60) for c in fill)
            pygame.draw.rect(surface, light, (r.x + 5, r.y + 5, r.w - 10, 5), border_radius=2)
        else:
            # dashed outline: "this will be here soon"
            for i in range(0, TILE, 8):
                pygame.draw.line(surface, edge, (r.x + i, r.y + 1), (r.x + i + 4, r.y + 1), 2)
                pygame.draw.line(surface, edge, (r.x + i, r.bottom - 2), (r.x + i + 4, r.bottom - 2), 2)
                pygame.draw.line(surface, edge, (r.x + 1, r.y + i), (r.x + 1, r.y + i + 4), 2)
                pygame.draw.line(surface, edge, (r.right - 2, r.y + i), (r.right - 2, r.y + i + 4), 2)


class FlipBlock(SwitchBlock):
    """Red and blue blocks swap every time you jump."""

    COLOURS = {"red": ((220, 60, 80), (120, 20, 40)), "blue": ((70, 120, 240), (20, 40, 120))}

    def __init__(self, col, row, colour):
        super().__init__(col, row, on=(colour == "red"))
        self.colour = colour

    def draw(self, surface, cam, art, t):
        self._draw_switch(surface, cam, *self.COLOURS[self.colour])


class BlinkBlock(SwitchBlock):
    """Appears and disappears on a steady beat. Two groups take turns."""

    def __init__(self, col, row, phase):
        super().__init__(col, row, on=(phase == 0))
        self.phase = phase

    def draw(self, surface, cam, art, t):
        self._draw_switch(surface, cam, (240, 200, 90), (130, 90, 20))


class ConveyorBlock(Block):
    """A solid belt that drags whatever stands on it."""

    SPEED = 2.6 * TILE

    def __init__(self, col, row, direction):
        super().__init__(col, row)
        self.direction = direction

    def draw(self, surface, cam, art, t):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, (60, 62, 72), r)
        pygame.draw.rect(surface, INK, r, 2)
        pygame.draw.rect(surface, (40, 40, 48), (r.x, r.y, r.w, 10))
        shift = int(t * self.SPEED * self.direction) % 16
        for i in range(-16, TILE + 16, 16):
            x0 = r.x + i + shift
            if r.x <= x0 <= r.right - 8:
                pts = [(x0, r.y + 2), (x0 + 6 * self.direction, r.y + 5), (x0, r.y + 8)]
                pygame.draw.lines(surface, GOLD, False, pts, 2)


class IceBlock(Block):
    """Slippery. You keep sliding long after you let go."""

    def draw(self, surface, cam, art, t):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, (150, 210, 245), r)
        pygame.draw.rect(surface, (220, 245, 255), (r.x, r.y, r.w, 7))
        pygame.draw.rect(surface, (70, 130, 180), r, 2)
        pygame.draw.line(surface, (255, 255, 255), (r.x + 8, r.y + 14), (r.x + 18, r.y + 24), 2)
        pygame.draw.line(surface, (255, 255, 255), (r.x + 22, r.y + 12), (r.x + 26, r.y + 16), 2)


# ================================================================== hazards
SPIKE_HITBOX = {
    # (x, y, w, h) inside the tile: smaller than the drawing so deaths feel fair
    "up": (8, TILE - 16, TILE - 16, 16),
    "down": (8, 0, TILE - 16, 16),
    "left": (TILE - 16, 8, 16, TILE - 16),
    "right": (0, 8, 16, TILE - 16),
}


class Spike(Hazard):
    cause = "spike"

    def __init__(self, col, row, direction="up", visible=True):
        super().__init__(col * TILE, row * TILE, TILE, TILE)
        self.col, self.row = col, row
        self.direction = direction
        self.extend = 1.0 if visible else 0.0
        self.visible = visible

    @property
    def active(self):
        present = self.group is None or self.group.present
        return present and self.extend > 0.45

    def hits(self, px, py, pw, ph):
        if not self.active:
            return False
        hx, hy, hw, hh = SPIKE_HITBOX[self.direction]
        hit = pygame.Rect(self.rect.x + hx, self.rect.y + hy, hw, hh)
        return rect_overlap(px, py, pw, ph, hit)

    def update(self, world, dt):
        if self.visible and self.extend < 1.0:
            self.extend = min(1.0, self.extend + dt * 16)

    def show(self, world):
        if not self.visible:
            self.visible = True
            world.emit("spike_pop", x=self.rect.centerx, y=self.rect.centery)

    def draw(self, surface, cam, art, t):
        if self.extend <= 0 or (self.group is not None and not self.group.present):
            return
        img = art.spikes[self.direction]
        # slide out of the surface while extending
        amount = int((1 - self.extend) * TILE * 0.8)
        dx, dy = {"up": (0, amount), "down": (0, -amount), "left": (amount, 0), "right": (-amount, 0)}[self.direction]
        surface.blit(img, (self.rect.x - cam[0] + dx, self.rect.y - cam[1] + dy))


class HiddenSpike(Spike):
    """Invisible spike that springs up when you walk over it. No warning. As advertised."""

    cause = "hidden"

    def __init__(self, col, row, direction="up", range_mult=1.0):
        super().__init__(col, row, direction, visible=False)
        self.range = HIDDEN_SPIKE_RANGE * range_mult

    def update(self, world, dt):
        p = world.player
        if not self.visible and p.alive:
            close_x = abs(p.centerx - self.rect.centerx) <= self.range * TILE + p.w / 2
            height = self.rect.bottom - p.bottom
            if close_x and -TILE * 0.5 <= height <= HIDDEN_SPIKE_HEIGHT * TILE:
                self.show(world)
        super().update(world, dt)


class Saw(Hazard):
    """A spinning saw blade that follows a list of points (in tile units).

    Its position is worked out from how far it has travelled, so it moves
    exactly the same way on every attempt."""

    cause = "saw"

    def __init__(self, path, speed=4.0, radius=0.7, active=True, mode="pingpong", saw_id=None, track=True):
        self.points = [((c + 0.5) * TILE, (r + 0.5) * TILE) for c, r in path]
        self.radius = int(radius * TILE)
        super().__init__(int(self.points[0][0]) - self.radius, int(self.points[0][1]) - self.radius,
                         self.radius * 2, self.radius * 2)
        self.speed = speed * TILE
        self.active = active
        self.mode = mode
        self.saw_id = saw_id
        self.show_track = track
        self.x, self.y = self.points[0]
        self.travelled = 0.0
        self.angle = 0.0
        pts = self.points + ([self.points[0]] if mode == "loop" else [])
        self.segments = []
        for a, b in zip(pts, pts[1:]):
            self.segments.append((a, b, math.hypot(b[0] - a[0], b[1] - a[1])))
        self.length = sum(seg[2] for seg in self.segments)

    def activate(self, world):
        if not self.active:
            self.active = True
            world.emit("saw_on", x=self.x, y=self.y)

    def _place(self):
        if self.length <= 0:
            return
        if self.mode == "loop":
            d = self.travelled % self.length
        else:
            d = self.travelled % (2 * self.length)
            if d > self.length:
                d = 2 * self.length - d
        last = len(self.segments) - 1
        for i, (a, b, seg_len) in enumerate(self.segments):
            if d <= seg_len or i == last:
                k = min(1.0, d / seg_len) if seg_len else 0
                self.x = a[0] + (b[0] - a[0]) * k
                self.y = a[1] + (b[1] - a[1]) * k
                break
            d -= seg_len
        self.rect.center = (int(self.x), int(self.y))

    def update(self, world, dt):
        self.angle += dt * (720 if self.active else 90)
        if self.active:
            self.travelled += self.speed * dt
            self._place()

    def hits(self, px, py, pw, ph):
        r = self.radius * 0.78
        nx = min(max(self.x, px), px + pw)
        ny = min(max(self.y, py), py + ph)
        return (self.x - nx) ** 2 + (self.y - ny) ** 2 < r * r

    def draw(self, surface, cam, art, t):
        img = art.saw_frame(self.radius, self.angle)
        surface.blit(img, img.get_rect(center=(int(self.x - cam[0]), int(self.y - cam[1]))))

    def draw_track(self, surface, cam):
        if len(self.points) > 1:
            pts = [(int(x - cam[0]), int(y - cam[1])) for x, y in self.points]
            pygame.draw.lines(surface, (0, 0, 0), self.mode == "loop", pts, 6)
            pygame.draw.lines(surface, (70, 64, 80), self.mode == "loop", pts, 2)
            for p in pts:
                pygame.draw.circle(surface, (70, 64, 80), p, 5)


class Arrow(Hazard):
    cause = "arrow"

    def __init__(self, x, y, dx, dy, speed):
        w, h = (34, 8) if dx else (8, 34)
        super().__init__(int(x - w / 2), int(y - h / 2), w, h)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = dx * speed * TILE, dy * speed * TILE
        self.dead = False
        self.age = 0.0

    def update(self, world, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))
        tip_x = self.x + (self.rect.w / 2) * (1 if self.vx > 0 else -1 if self.vx < 0 else 0)
        tip_y = self.y + (self.rect.h / 2) * (1 if self.vy > 0 else -1 if self.vy < 0 else 0)
        if self.age > 0.1 and world.static_solid_at(tip_x, tip_y):
            self.dead = True
            world.emit("arrow_hit", x=tip_x, y=tip_y)
        if not (-200 < self.x < world.width + 200 and -200 < self.y < world.height + 200):
            self.dead = True

    def hits(self, px, py, pw, ph):
        return not self.dead and rect_overlap(px, py, pw, ph, self.rect.inflate(-4, -2))

    def draw(self, surface, cam, art, t):
        x, y = self.x - cam[0], self.y - cam[1]
        ux = 1 if self.vx > 0 else -1 if self.vx < 0 else 0
        uy = 1 if self.vy > 0 else -1 if self.vy < 0 else 0
        tail = (x - ux * 17, y - uy * 17)
        tip = (x + ux * 17, y + uy * 17)
        pygame.draw.line(surface, (120, 90, 60), tail, tip, 3)
        px, py = -uy, ux
        head = [(tip[0] + ux * 6, tip[1] + uy * 6), (tip[0] + px * 6, tip[1] + py * 6), (tip[0] - px * 6, tip[1] - py * 6)]
        pygame.draw.polygon(surface, PAPER, head)
        for k in (0, 5):
            base = (tail[0] + ux * k, tail[1] + uy * k)
            pygame.draw.line(surface, (220, 60, 70), base, (base[0] - ux * 6 + px * 6, base[1] - uy * 6 + py * 6), 2)
            pygame.draw.line(surface, (220, 60, 70), base, (base[0] - ux * 6 - px * 6, base[1] - uy * 6 - py * 6), 2)


# ================================================================== helpers
class Spring(Entity):
    def __init__(self, col, row):
        super().__init__(col * TILE + 4, row * TILE + TILE - 14, TILE - 8, 14)
        self.squash = 0.0

    def update(self, world, dt):
        self.squash = max(0.0, self.squash - dt * 5)

    def draw(self, surface, cam, art, t):
        x, y, w, h = self.rect.x - cam[0], self.rect.y - cam[1], self.rect.w, self.rect.h
        comp = int(self.squash * 6)
        pygame.draw.rect(surface, (40, 36, 48), (x, y + h - 4, w, 4), border_radius=2)
        for i in range(3):
            yy = y + h - 5 - i * (3 - comp // 3)
            pygame.draw.line(surface, (190, 190, 200), (x + 6, yy), (x + w - 6, yy - 2), 2)
        top = y + comp - 6
        pygame.draw.rect(surface, (230, 60, 70), (x - 2, top, w + 4, 7), border_radius=3)
        pygame.draw.rect(surface, INK, (x - 2, top, w + 4, 7), 1, border_radius=3)


class Door(Entity):
    """The exit. Stands on the tile below its map position."""

    is_fake = False

    def __init__(self, col, row):
        super().__init__(col * TILE + 2, row * TILE + TILE - 62, TILE - 4, 62)
        self.hop_from = None
        self.hop_to = None
        self.hop_t = 0.0

    @property
    def hitbox(self):
        return self.rect.inflate(-10, -8).move(0, 4)

    def hop(self, world, col, row):
        self.hop_from = self.rect.topleft
        self.hop_to = (col * TILE + 2, row * TILE + TILE - 62)
        self.hop_t = 0.0
        world.emit("door_hop", x=self.rect.centerx, y=self.rect.bottom)

    @property
    def hopping(self):
        return self.hop_to is not None

    def update(self, world, dt):
        if self.hop_to is None:
            return
        self.hop_t = min(1.0, self.hop_t + dt / 0.45)
        e = ease_in_out(self.hop_t)
        x = lerp(self.hop_from[0], self.hop_to[0], e)
        y = lerp(self.hop_from[1], self.hop_to[1], e) - math.sin(self.hop_t * math.pi) * 90
        self.rect.topleft = (int(x), int(y))
        if self.hop_t >= 1.0:
            self.rect.topleft = self.hop_to
            self.hop_to = None
            world.emit("door_land", x=self.rect.centerx, y=self.rect.bottom)

    def draw(self, surface, cam, art, t):
        draw_door(surface, self.rect.move(-cam[0], -cam[1]), t, art.theme["accent"])


class FakeDoor(Door):
    is_fake = True


class Checkpoint(Entity):
    def __init__(self, col, row):
        super().__init__(col * TILE + 12, row * TILE - 20, 18, 60)
        self.spawn = (col * TILE + (TILE - 26) // 2, (row + 1) * TILE - 34)
        self.active = False
        self.wave = 0.0

    def update(self, world, dt):
        self.wave += dt * (8 if self.active else 3)

    def draw(self, surface, cam, art, t):
        x, y = self.rect.x - cam[0], self.rect.y - cam[1]
        pygame.draw.rect(surface, (40, 36, 48), (x, y + self.rect.h - 6, 16, 6), border_radius=2)
        pygame.draw.line(surface, PAPER, (x + 3, y + 4), (x + 3, y + self.rect.h - 4), 3)
        col = GOLD if self.active else MUTED
        pts = [(x + 5, y + 4)]
        for i in range(1, 6):
            pts.append((x + 5 + i * 5, y + 4 + math.sin(self.wave + i * 0.8) * (2 + i * 0.4)))
        for i in range(5, -1, -1):
            pts.append((x + 5 + i * 5, y + 20 + math.sin(self.wave + i * 0.8) * (2 + i * 0.4)))
        pygame.draw.polygon(surface, col, pts)


# ================================================================== groups
class Group:
    """Named set of blocks/spikes that level triggers can control."""

    def __init__(self, name, present=True):
        self.name = name
        self.present = present
        self.members = []
        self.ox = self.oy = 0.0            # current offset in pixels
        self.dx = self.dy = 0.0            # movement this step (for carrying the player)
        self.mode = "idle"                 # idle / drop / tween
        self.vy = 0.0
        self.gravity = DROP_GRAVITY
        self.tween_from = (0.0, 0.0)
        self.tween_to = (0.0, 0.0)
        self.tween_time = 0.0
        self.tween_t = 0.0
        self.landed = False
        self.pop = 0.0                     # appear animation
        self.box = pygame.Rect(0, 0, 0, 0)

    def add(self, entity):
        entity.group = self
        self.members.append(entity)
        self.box = self.bbox()

    @property
    def blocks(self):
        return [m for m in self.members if isinstance(m, Block)]

    @property
    def spikes(self):
        return [m for m in self.members if isinstance(m, Spike)]

    def start_drop(self):
        if self.mode != "drop" and self.present:
            self.mode = "drop"
            self.vy = 0.0

    def start_tween(self, dx, dy, duration):
        self.mode = "tween"
        self.tween_from = (self.ox, self.oy)
        self.tween_to = (self.ox + dx, self.oy + dy)
        self.tween_time = max(0.01, duration)
        self.tween_t = 0.0

    def step(self, world, dt):
        """Move the group. Returns (dx, dy) moved this step."""
        old = (self.ox, self.oy)
        self.pop = max(0.0, self.pop - dt * 5)
        if self.mode == "drop":
            self.vy = min(self.vy + self.gravity * dt, 1600)
            move = self.vy * dt
            # stop if a member would hit the static level
            if world.group_would_land(self, move):
                move = world.group_land_distance(self, move)
                self.mode = "idle"
                self.landed = True
                world.emit("slam", x=self.box.centerx, y=self.box.bottom + move)
            self.oy += move
            if self.oy > world.height + 200:
                self.mode = "idle"
                self.present = False
        elif self.mode == "tween":
            self.tween_t = min(1.0, self.tween_t + dt / self.tween_time)
            e = ease_in_out(self.tween_t) if self.tween_time > 0.25 else self.tween_t
            self.ox = lerp(self.tween_from[0], self.tween_to[0], e)
            self.oy = lerp(self.tween_from[1], self.tween_to[1], e)
            if self.tween_t >= 1.0:
                self.mode = "idle"
        self.dx, self.dy = self.ox - old[0], self.oy - old[1]
        if self.dx or self.dy:
            for m in self.members:
                m.sync_group()
            self.box = self.bbox()
        return self.dx, self.dy

    def bbox(self):
        rects = [m.rect for m in self.members]
        return rects[0].unionall(rects[1:]) if rects else pygame.Rect(0, 0, 0, 0)
