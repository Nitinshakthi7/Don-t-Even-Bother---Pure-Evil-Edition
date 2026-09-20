# I am adding comments for me to easily understand the codes
# enemies.py - things in the level that move by themselves and want you dead.
#
#   Hazard (from traps.py)
#   |-- Enemy (abstract)          walks / flies / watches, kills on touch
#   |   |-- Crawler              patrols a platform; jump on its head to squash it
#   |   |   `-- SpikeCrawler     same, but its back is spiky: DON'T jump on it
#   |   |-- Mimic                jumps every time YOU jump
#   |   |-- Swooper              hangs from the ceiling and dive-bombs you
#   |   |-- Sentry               a floating eye that shoots at where you are
#   |   `-- Echo                 your own shadow, replaying your moves a moment later
#   |-- Orb                      a shot from a Sentry or Cannon
#   |-- Laser                    fires a beam on a fixed rhythm (flickers first)
#   `-- Cannon                   fires cannonballs on a fixed rhythm
#
# Like everything else in the game, every enemy is fully deterministic: it
# only reacts to where you are and when, so it does the same thing every
# attempt and can be learned.

import math
from abc import abstractmethod

import pygame

from settings import TILE, GRAVITY, JUMP_VELOCITY, MAX_FALL_SPEED, INK, PAPER, BLOOD, GOLD, STEEL, STEEL_DARK
from traps import Hazard, rect_overlap


def _circle_hits(cx, cy, r, px, py, pw, ph):
    nx = min(max(cx, px), px + pw)
    ny = min(max(cy, py), py + ph)
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


# ================================================================== enemies
class Enemy(Hazard):
    cause = "enemy"
    stompable = False

    def __init__(self, x, y, w, h):
        super().__init__(int(x), int(y), w, h)
        self.x, self.y = float(x), float(y)
        self.alive = True
        self.anim = 0.0

    def _sync(self):
        self.rect.topleft = (int(self.x), int(self.y))

    def hits(self, px, py, pw, ph):
        return self.alive and rect_overlap(px, py, pw, ph, self.rect.inflate(-6, -4))

    def squash(self, world):
        self.alive = False
        world.emit("stomp", x=self.rect.centerx, y=self.rect.top)

    @abstractmethod
    def draw(self, surface, cam, art, t):
        ...


class Crawler(Enemy):
    """Walks along its platform and turns round at walls and edges."""

    stompable = True
    body = (120, 200, 90)

    def __init__(self, col, row, speed=2.2, speed_mult=1.0):
        super().__init__(col * TILE + 5, (row + 1) * TILE - 24, 30, 24)
        self.direction = -1
        self.speed = speed * TILE * speed_mult
        self.vy = 0.0

    def update(self, world, dt):
        if not self.alive:
            return
        self.anim += dt * self.speed / 12
        # fall if nothing underneath (e.g. its floor collapsed)
        if not world.solids_touching(self.x, self.y + self.rect.h, self.rect.w, 1):
            self.vy = min(self.vy + GRAVITY * dt, MAX_FALL_SPEED)
            self.y += self.vy * dt
            for r in world.solids_touching(self.x, self.y, self.rect.w, self.rect.h):
                self.y = r.top - self.rect.h
                self.vy = 0.0
            if self.y > world.kill_y:
                self.alive = False
            self._sync()
            return
        step = self.direction * self.speed * dt
        front = self.x + (self.rect.w if self.direction > 0 else 0) + step
        wall = world.solids_touching(self.x + step, self.y + 2, self.rect.w, self.rect.h - 4)
        floor_ahead = world.solids_touching(front - self.direction * 2, self.y + self.rect.h + 2, 1, 4)
        if wall or not floor_ahead or not (0 < front < world.width):
            self.direction *= -1
        else:
            self.x += step
        self._sync()

    def draw(self, surface, cam, art, t):
        if not self.alive:
            return
        x, y = self.rect.x - cam[0], self.rect.y - cam[1]
        w, h = self.rect.size
        bob = int(abs(math.sin(self.anim)) * 2)
        body = pygame.Rect(x, y + bob, w, h - bob)
        pygame.draw.ellipse(surface, INK, body.inflate(4, 4))
        pygame.draw.ellipse(surface, self.body, body)
        self._draw_back(surface, body)
        # angry eyes looking the way it walks
        ex = body.centerx + self.direction * 6
        for side in (-1, 1):
            pygame.draw.circle(surface, PAPER, (ex + side * 5, body.y + 9), 4)
            pygame.draw.circle(surface, INK, (ex + side * 5 + self.direction, body.y + 10), 2)
        pygame.draw.line(surface, INK, (ex - 9, body.y + 3), (ex - 2, body.y + 6), 2)
        pygame.draw.line(surface, INK, (ex + 9, body.y + 3), (ex + 2, body.y + 6), 2)
        for i, fx in enumerate((body.x + 6, body.right - 10)):
            lift = int(math.sin(self.anim * 2 + i * math.pi) * 2)
            pygame.draw.rect(surface, INK, (fx, body.bottom - 3 - lift, 5, 4))

    def _draw_back(self, surface, body):
        pass


class SpikeCrawler(Crawler):
    """A crawler with spikes on its back. Stomping it is a very bad idea."""

    stompable = False
    body = (200, 90, 110)
    cause = "spike"

    def _draw_back(self, surface, body):
        for i in range(4):
            bx = body.x + 4 + i * 6
            pygame.draw.polygon(surface, STEEL, [(bx, body.y + 6), (bx + 3, body.y - 5), (bx + 6, body.y + 6)])
            pygame.draw.polygon(surface, INK, [(bx, body.y + 6), (bx + 3, body.y - 5), (bx + 6, body.y + 6)], 1)


class Mimic(Enemy):
    """A spiky ball that jumps whenever you jump. Don't jump next to it. Or do. Once."""

    def __init__(self, col, row):
        super().__init__(col * TILE + 6, (row + 1) * TILE - 28, 28, 28)
        self.vy = 0.0
        self.on_ground = True

    def on_player_jump(self):
        if self.alive and self.on_ground:
            self.vy = -JUMP_VELOCITY * 0.95
            self.on_ground = False

    def update(self, world, dt):
        self.anim += dt * 6
        if self.on_ground:
            return
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL_SPEED)
        self.y += self.vy * dt
        for r in world.solids_touching(self.x, self.y, self.rect.w, self.rect.h):
            if self.vy > 0:
                self.y = r.top - self.rect.h
                self.on_ground = True
            else:
                self.y = r.bottom
            self.vy = 0.0
        self._sync()

    def hits(self, px, py, pw, ph):
        c = self.rect.center
        return self.alive and _circle_hits(c[0], c[1], 12, px, py, pw, ph)

    def draw(self, surface, cam, art, t):
        cx, cy = self.rect.centerx - cam[0], self.rect.centery - cam[1]
        for i in range(8):
            a = i * math.pi / 4 + self.anim * 0.3
            tip = (cx + math.cos(a) * 17, cy + math.sin(a) * 17)
            l = (cx + math.cos(a - 0.35) * 11, cy + math.sin(a - 0.35) * 11)
            r = (cx + math.cos(a + 0.35) * 11, cy + math.sin(a + 0.35) * 11)
            pygame.draw.polygon(surface, STEEL, [l, tip, r])
        pygame.draw.circle(surface, INK, (cx, cy), 13)
        pygame.draw.circle(surface, (150, 90, 210), (cx, cy), 11)
        # a creepy grin that copies yours
        pygame.draw.arc(surface, PAPER, (cx - 7, cy - 4, 14, 10), math.pi + 0.3, 2 * math.pi - 0.3, 2)
        pygame.draw.circle(surface, PAPER, (cx - 4, cy - 4), 2)
        pygame.draw.circle(surface, PAPER, (cx + 4, cy - 4), 2)


class Swooper(Enemy):
    """Hangs from the ceiling. When you pass underneath it dives at where you were."""

    def __init__(self, col, row, speed_mult=1.0):
        super().__init__(col * TILE + 6, row * TILE + 2, 28, 22)
        self.home = (self.x, self.y)
        self.state = "rest"
        self.target = self.home
        self.cooldown = 0.0
        self.speed = 9 * TILE * speed_mult

    def update(self, world, dt):
        self.anim += dt * (14 if self.state != "rest" else 3)
        p = world.player
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.state == "rest":
            below = 0 < p.y - self.y < 8 * TILE
            if self.cooldown <= 0 and p.alive and below and abs(p.centerx - self.rect.centerx) < 2.2 * TILE:
                self.state = "dive"
                self.target = (p.x, p.y + 4)
                world.emit("swoop", x=self.rect.centerx, y=self.rect.centery)
        elif self.state in ("dive", "return"):
            tx, ty = self.target if self.state == "dive" else self.home
            speed = self.speed if self.state == "dive" else self.speed * 0.45
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            step = speed * dt
            blocked = self.state == "dive" and world.solids_touching(self.x, self.y, self.rect.w, self.rect.h)
            if dist <= step or blocked:
                if self.state == "dive":
                    self.state = "return"
                else:
                    self.x, self.y = self.home
                    self.state = "rest"
                    self.cooldown = 0.6
            else:
                self.x += dx / dist * step
                self.y += dy / dist * step
        self._sync()

    def draw(self, surface, cam, art, t):
        cx, cy = self.rect.centerx - cam[0], self.rect.centery - cam[1]
        flap = math.sin(self.anim) * 8 if self.state != "rest" else 2
        wing = (70, 40, 90)
        pygame.draw.polygon(surface, wing, [(cx - 3, cy), (cx - 20, cy - 6 - flap), (cx - 14, cy + 6)])
        pygame.draw.polygon(surface, wing, [(cx + 3, cy), (cx + 20, cy - 6 - flap), (cx + 14, cy + 6)])
        pygame.draw.circle(surface, INK, (cx, cy), 10)
        pygame.draw.circle(surface, (110, 60, 130), (cx, cy), 8)
        eye = BLOOD if self.state != "rest" else GOLD
        pygame.draw.circle(surface, eye, (cx - 3, cy - 1), 2)
        pygame.draw.circle(surface, eye, (cx + 3, cy - 1), 2)
        pygame.draw.polygon(surface, PAPER, [(cx - 3, cy + 4), (cx - 1, cy + 8), (cx + 1, cy + 4)])


class Sentry(Enemy):
    """A floating eye. It watches you, then fires where you're standing."""

    RANGE = 9 * TILE

    def __init__(self, col, row, period=1.7, rate_mult=1.0):
        super().__init__(col * TILE + 4, row * TILE + 4, 32, 32)
        self.period = period / rate_mult
        self.timer = self.period * 0.6
        self.look = (0.0, 0.0)

    def update(self, world, dt):
        p = world.player
        cx, cy = self.rect.center
        dx, dy = p.centerx - cx, p.centery - cy
        dist = math.hypot(dx, dy) or 1
        self.look = (dx / dist, dy / dist)
        if dist > self.RANGE or not p.alive:
            self.timer = min(self.timer, self.period)
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.period
            speed = 7 * TILE
            world.orbs.append(Orb(cx + self.look[0] * 16, cy + self.look[1] * 16,
                                  self.look[0] * speed, self.look[1] * speed))
            world.emit("orb", x=cx, y=cy)

    @property
    def charging(self):
        return self.timer < 0.35

    def draw(self, surface, cam, art, t):
        cx, cy = self.rect.centerx - cam[0], self.rect.centery - cam[1]
        bob = int(math.sin(t * 3 + self.x) * 3)
        cy += bob
        pygame.draw.circle(surface, INK, (cx, cy), 18)
        pygame.draw.circle(surface, (230, 226, 214), (cx, cy), 16)
        iris = BLOOD if self.charging else (70, 150, 230)
        ix, iy = cx + self.look[0] * 7, cy + self.look[1] * 7
        pygame.draw.circle(surface, iris, (int(ix), int(iy)), 8)
        pygame.draw.circle(surface, INK, (int(ix), int(iy)), 4)
        if self.charging and int(t * 20) % 2:
            pygame.draw.circle(surface, BLOOD, (cx, cy), 20, 2)
        for i in range(3):
            a = math.pi * 0.25 + i * math.pi * 0.25
            pygame.draw.line(surface, INK, (cx + math.cos(a) * 16, cy + 14), (cx + math.cos(a) * 18, cy + 22), 2)


class Echo(Enemy):
    """Your own shadow. It replays exactly what you did a moment ago."""

    cause = "echo"

    def __init__(self, x, y):
        super().__init__(x, y, 26, 34)
        self.visible = False

    def follow(self, pos):
        if pos is None:
            self.visible = False
            return
        self.visible = True
        self.x, self.y = pos
        self._sync()

    def hits(self, px, py, pw, ph):
        return self.visible and rect_overlap(px, py, pw, ph, self.rect.inflate(-8, -8))

    def update(self, world, dt):
        self.anim += dt

    def draw(self, surface, cam, art, t):
        if not self.visible:
            return
        body = self.rect.move(-cam[0], -cam[1])
        glow = pygame.Surface((body.w + 16, body.h + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (140, 40, 200, 70), glow.get_rect(), border_radius=12)
        surface.blit(glow, (body.x - 8, body.y - 8))
        pygame.draw.rect(surface, (20, 6, 30), body, border_radius=8)
        pygame.draw.rect(surface, (160, 60, 220), body, 2, border_radius=8)
        for side in (-1, 1):
            pygame.draw.rect(surface, BLOOD, (body.centerx + side * 5 - 2, body.y + 7, 4, 7), border_radius=2)


# ================================================================== projectiles & emitters
class Orb(Hazard):
    cause = "orb"

    def __init__(self, x, y, vx, vy, radius=8, colour=(255, 90, 120)):
        super().__init__(int(x) - radius, int(y) - radius, radius * 2, radius * 2)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.radius = radius
        self.colour = colour
        self.dead = False
        self.age = 0.0

    def update(self, world, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))
        if self.age > 0.08 and world.static_solid_at(self.x, self.y):
            self.dead = True
            world.emit("arrow_hit", x=self.x, y=self.y)
        if not (-100 < self.x < world.width + 100 and -100 < self.y < world.height + 100) or self.age > 8:
            self.dead = True

    def hits(self, px, py, pw, ph):
        return not self.dead and _circle_hits(self.x, self.y, self.radius * 0.8, px, py, pw, ph)

    def draw(self, surface, cam, art, t):
        cx, cy = int(self.x - cam[0]), int(self.y - cam[1])
        pygame.draw.circle(surface, INK, (cx, cy), self.radius + 2)
        pygame.draw.circle(surface, self.colour, (cx, cy), self.radius)
        pygame.draw.circle(surface, PAPER, (cx - self.radius // 3, cy - self.radius // 3), max(2, self.radius // 3))


class Cannon(Hazard):
    """Fires a heavy ball in a fixed direction on a fixed beat."""

    cause = "orb"

    def __init__(self, col, row, dx, dy, period=2.0, speed=6.0, offset=0.0, rate_mult=1.0):
        super().__init__(col * TILE, row * TILE, TILE, TILE)
        self.dx, self.dy = dx, dy
        self.period = period / rate_mult
        self.speed = speed * TILE * rate_mult
        self.timer = offset % self.period if offset else self.period
        self.recoil = 0.0

    def update(self, world, dt):
        self.recoil = max(0.0, self.recoil - dt * 4)
        self.timer -= dt
        if self.timer <= 0:
            self.timer += self.period
            cx, cy = self.rect.center
            world.orbs.append(Orb(cx + self.dx * 24, cy + self.dy * 24, self.dx * self.speed, self.dy * self.speed,
                                  radius=12, colour=(60, 60, 70)))
            self.recoil = 1.0
            world.emit("cannon", x=cx, y=cy)

    def hits(self, px, py, pw, ph):
        return False          # the barrel itself is safe to stand on

    def draw(self, surface, cam, art, t):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, (50, 48, 58), r.inflate(-4, -4), border_radius=6)
        pygame.draw.rect(surface, INK, r.inflate(-4, -4), 2, border_radius=6)
        kick = int(self.recoil * 5)
        mouth = (r.centerx + self.dx * (14 - kick), r.centery + self.dy * (14 - kick))
        pygame.draw.circle(surface, (30, 28, 36), mouth, 11)
        pygame.draw.circle(surface, INK, mouth, 11, 2)
        if self.timer < 0.4 and int(t * 16) % 2:
            pygame.draw.circle(surface, GOLD, r.center, 5)


class Laser(Hazard):
    """An emitter on a wall. Off... flicker... BEAM. Always on the same rhythm."""

    cause = "laser"
    WARNING = 0.45

    def __init__(self, col, row, dx, dy, on=1.0, off=1.5, offset=0.0, rate_mult=1.0):
        super().__init__(col * TILE, row * TILE, TILE, TILE)
        self.col, self.row = col, row
        self.dx, self.dy = dx, dy
        self.on_time = on
        self.off_time = off / rate_mult
        self.clock = offset
        self.beam = None           # worked out on first update (needs the level)
        self.was_on = False

    def _make_beam(self, world):
        c, r = self.col + self.dx, self.row + self.dy
        while 0 <= c < world.cols and 0 <= r < world.nrows and not world.grid[r][c]:
            c += self.dx
            r += self.dy
        # (c, r) is the first solid tile (or off the map)
        cx, cy = self.rect.center
        ex, ey = (c + 0.5) * TILE - self.dx * TILE / 2, (r + 0.5) * TILE - self.dy * TILE / 2
        thick = 12
        if self.dx:
            left, right = sorted((cx + self.dx * TILE / 2, ex))
            self.beam = pygame.Rect(int(left), int(cy - thick / 2), int(right - left), thick)
        else:
            top, bottom = sorted((cy + self.dy * TILE / 2, ey))
            self.beam = pygame.Rect(int(cx - thick / 2), int(top), thick, int(bottom - top))

    @property
    def phase(self):
        cycle = self.on_time + self.off_time
        return self.clock % cycle

    @property
    def firing(self):
        return self.phase >= self.off_time

    @property
    def warning(self):
        return self.off_time - self.WARNING <= self.phase < self.off_time

    def update(self, world, dt):
        if self.beam is None:
            self._make_beam(world)
        self.clock += dt
        if self.firing and not self.was_on:
            world.emit("laser", x=self.rect.centerx, y=self.rect.centery)
        self.was_on = self.firing

    def hits(self, px, py, pw, ph):
        return self.beam is not None and self.firing and rect_overlap(px, py, pw, ph, self.beam.inflate(-2, -2))

    def draw(self, surface, cam, art, t):
        r = self.rect.move(-cam[0], -cam[1])
        pygame.draw.rect(surface, (60, 58, 70), r.inflate(-8, -8), border_radius=5)
        pygame.draw.rect(surface, INK, r.inflate(-8, -8), 2, border_radius=5)
        lens = BLOOD if (self.firing or self.warning) else (90, 40, 50)
        pygame.draw.circle(surface, lens, (r.centerx + self.dx * 10, r.centery + self.dy * 10), 6)
        if self.beam is None:
            return
        b = self.beam.move(-cam[0], -cam[1])
        if self.firing:
            glow = b.inflate(10 if self.dy else 0, 10 if self.dx else 0)
            shade = pygame.Surface(glow.size, pygame.SRCALPHA)
            shade.fill((255, 40, 70, 90))
            surface.blit(shade, glow.topleft)
            pygame.draw.rect(surface, (255, 70, 90), b)
            core = b.inflate(-8 if self.dy else 0, -8 if self.dx else 0)
            pygame.draw.rect(surface, (255, 230, 235), core)
        elif self.warning and int(t * 24) % 2:
            thin = b.inflate(-10 if self.dy else 0, -10 if self.dx else 0)
            pygame.draw.rect(surface, (255, 80, 100), thin)


class KeyItem:
    """The exit is locked until you grab this. Plain object: it can't hurt you."""

    def __init__(self, col, row):
        self.rect = pygame.Rect(col * TILE + 8, row * TILE + 6, 24, 28)
        self.taken = False

    def draw(self, surface, cam, art, t):
        if self.taken:
            return
        x, y = self.rect.x - cam[0], self.rect.y - cam[1] + int(math.sin(t * 3) * 4)
        pygame.draw.circle(surface, INK, (x + 12, y + 8), 9)
        pygame.draw.circle(surface, GOLD, (x + 12, y + 8), 7)
        pygame.draw.circle(surface, INK, (x + 12, y + 8), 3)
        pygame.draw.rect(surface, GOLD, (x + 10, y + 14, 4, 14))
        pygame.draw.rect(surface, GOLD, (x + 14, y + 22, 5, 3))
        pygame.draw.rect(surface, GOLD, (x + 14, y + 26, 4, 2))
