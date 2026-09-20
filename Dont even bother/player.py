# I am adding comments for me to easily understand the codes
# player.py - the little guy you will watch die a thousand times.
# This class decides HOW the player wants to move (speed, jumping, coyote
# time, jump buffering). The World class then moves him and handles walls.

import math

import pygame

from settings import (PLAYER_W, PLAYER_H, RUN_SPEED, GROUND_ACCEL, GROUND_DECEL, AIR_ACCEL,
                      AIR_DECEL, GRAVITY, FALL_GRAVITY_MULT, MAX_FALL_SPEED, JUMP_VELOCITY,
                      JUMP_CUT_MULT, COYOTE_TIME, JUMP_BUFFER_TIME, PLAYER_BODY, PLAYER_OUTLINE,
                      PLAYER_SCARF, INK)
from utils import approach, damp, clamp
import cosmetics
from cosmetics import DEFAULT as DEFAULT_SKIN


def wants_jump(queued, jump_held, on_ground, auto_hop=True):
    """Should this step start a jump?

    A fresh press always counts. On top of that, holding the button down hops
    you again the moment you land - but it never gives you a second jump in
    mid-air, because you have to be standing on something first.
    """
    return bool(queued or (auto_hop and jump_held and on_ground))


class Player:
    def __init__(self, x, y, coyote_time=COYOTE_TIME, buffer_time=JUMP_BUFFER_TIME):
        self.w, self.h = PLAYER_W, PLAYER_H
        self.coyote_time = coyote_time      # Brutal mode is less forgiving
        self.buffer_time = buffer_time
        self.grip = 1.0                     # < 1 on ice
        self.skin = None                    # set by the scene; drawing only, never physics
        self.reset(x, y)

    def reset(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.alive = True
        self.on_ground = False
        self.was_on_ground = False
        self.facing = 1
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.jump_held = False
        self.jumping = False          # true while rising from a jump (so we can cut it)
        self.spring_lock = False      # spring launches cannot be cut short
        # visual-only state
        self.squash_x = self.squash_y = 1.0
        self.run_phase = 0.0
        self.blink = 0.0
        self.blink_timer = 2.0
        self.scarf = [(self.x, self.y)] * 6
        self.air_time = 0.0

    # ------------------------------------------------------------ geometry
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def centerx(self):
        return self.x + self.w / 2

    @property
    def centery(self):
        return self.y + self.h / 2

    @property
    def bottom(self):
        return self.y + self.h

    # ------------------------------------------------------------ control
    def press_jump(self):
        """Remember the jump for a short moment (jump buffering)."""
        self.jump_buffer = self.buffer_time

    def control(self, dt, move_dir, jump_held):
        """Update velocity from input. Returns True if a jump started this step."""
        self.jump_held = jump_held
        if move_dir:
            self.facing = move_dir
        # --- horizontal: accelerate towards the target speed
        target = move_dir * RUN_SPEED
        if move_dir:
            accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
            # turning around is extra snappy
            if self.vx * move_dir < 0:
                accel *= 1.6
        else:
            accel = GROUND_DECEL if self.on_ground else AIR_DECEL
        if self.on_ground:
            accel *= self.grip
        self.vx = approach(self.vx, target, accel * dt)

        # --- timers
        if self.on_ground:
            self.coyote = self.coyote_time
            self.spring_lock = False
        else:
            self.coyote = max(0.0, self.coyote - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)

        # --- jump
        jumped = False
        if self.jump_buffer > 0 and self.coyote > 0:
            self.vy = -JUMP_VELOCITY
            self.jump_buffer = 0.0
            self.coyote = 0.0
            self.jumping = True
            self.on_ground = False
            self.squash_x, self.squash_y = 0.7, 1.35
            jumped = True

        # --- variable jump height: let go early for a small hop
        if self.jumping and not jump_held and self.vy < 0 and not self.spring_lock:
            self.vy *= JUMP_CUT_MULT
            self.jumping = False
        if self.vy >= 0:
            self.jumping = False

        # --- gravity (heavier on the way down)
        g = GRAVITY * (FALL_GRAVITY_MULT if self.vy > 0 else 1.0)
        self.vy = min(self.vy + g * dt, MAX_FALL_SPEED)
        return jumped

    def launch(self, velocity):
        """Used by springs."""
        self.vy = -velocity
        self.jumping = False
        self.spring_lock = True
        self.on_ground = False
        self.coyote = 0.0
        self.squash_x, self.squash_y = 0.6, 1.45

    # ------------------------------------------------------------ visuals
    def animate(self, dt):
        """Purely cosmetic: squash & stretch, running bob, blinking, scarf."""
        self.squash_x = damp(self.squash_x, 1.0, 14, dt)
        self.squash_y = damp(self.squash_y, 1.0, 14, dt)
        if not self.on_ground:
            self.air_time += dt
            stretch = clamp(abs(self.vy) / MAX_FALL_SPEED, 0, 1) * 0.18
            self.squash_y = max(self.squash_y, 1 + stretch)
            self.squash_x = min(self.squash_x, 1 - stretch * 0.6)
        else:
            self.air_time = 0.0
        self.run_phase += dt * abs(self.vx) / 22
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.blink = 0.12
            self.blink_timer = 2.2 + (hash(int(self.x)) % 100) / 40
        self.blink = max(0.0, self.blink - dt)
        # scarf follows the neck with a little delay
        neck = (self.centerx - self.facing * 6, self.y + 19)
        self.scarf[0] = neck
        for i in range(1, len(self.scarf)):
            px, py = self.scarf[i - 1]
            sx, sy = self.scarf[i]
            wave = math.sin(self.run_phase * 0.8 + i * 0.9) * 1.5
            tx = px - self.facing * 4 - self.vx * 0.003
            ty = py + 1.0 + wave - self.vy * 0.002
            nx, ny = damp(sx, tx, 30, dt), damp(sy, ty, 30, dt)
            # keep each scarf segment attached (max 5 px from the previous one)
            dx, dy = nx - px, ny - py
            dist = math.hypot(dx, dy)
            if dist > 5:
                nx, ny = px + dx / dist * 5, py + dy / dist * 5
            self.scarf[i] = (nx, ny)

    def land_impact(self, speed):
        amount = clamp(speed / MAX_FALL_SPEED, 0.2, 1.0)
        self.squash_x = 1 + 0.4 * amount
        self.squash_y = 1 - 0.35 * amount

    def draw(self, surface, cam_x, cam_y=0):
        if not self.alive:
            return
        bob = math.sin(self.run_phase) * 1.5 if self.on_ground and abs(self.vx) > 20 else 0
        w = self.w * self.squash_x
        h = self.h * self.squash_y
        cx = self.centerx - cam_x
        bottom = self.y + self.h - cam_y + bob * 0.3
        body = pygame.Rect(0, 0, int(w), int(h))
        body.midbottom = (int(cx), int(bottom))

        # scarf behind the body
        skin = self.skin or DEFAULT_SKIN
        pts = [(int(x - cam_x), int(y - cam_y + bob * 0.3)) for x, y in self.scarf]
        if len(pts) > 1:
            pygame.draw.lines(surface, skin.scarf, False, pts, 5)
            pygame.draw.circle(surface, skin.scarf, pts[-1], 3)

        # the body itself is drawn by cosmetics, so the character looks the same
        # here as it does on the menus
        look_x = self.facing * 3 + clamp(self.vx / 120, -2, 2)
        look_y = clamp(self.vy / 400, -2, 3)
        cosmetics.draw_body(surface, skin, body, look=(look_x, look_y), blink=self.blink > 0)
