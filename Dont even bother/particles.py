# I am adding comments for me to easily understand the codes
# particles.py - tiny visual effects: dust, sparks, debris and blood.
# Blood particles can "stain" the level when they hit a wall, so every
# death leaves a permanent mark (a classic touch from Super Meat Boy).

import math
import random

from settings import MOBILE

import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color",
                 "gravity", "drag", "square", "stain", "spin", "angle")

    def __init__(self, x, y, vx, vy, life, size, color, gravity, drag, square, stain):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.drag = drag
        self.square = square
        self.stain = stain
        self.spin = random.uniform(-8, 8)
        self.angle = random.uniform(0, 6.28)


class ParticleSystem:
    """Owns every particle. Uses plain draw calls (no per-particle surfaces) so it stays fast."""

    def __init__(self, limit=1500):
        if MOBILE:
            limit = 220          # a phone cannot afford a thousand of anything
        self.particles = []
        self.limit = limit

    def clear(self):
        self.particles.clear()

    def burst(self, x, y, count, colors, speed=(60, 200), life=(0.3, 0.8), size=(2, 4),
              gravity=900, drag=1.5, angle=(0, math.tau), square=False, stain=False, up_bias=0):
        for _ in range(count):
            if len(self.particles) >= self.limit:
                self.particles.pop(0)
            a = random.uniform(*angle)
            s = random.uniform(*speed)
            self.particles.append(Particle(
                x, y, math.cos(a) * s, math.sin(a) * s - up_bias,
                random.uniform(*life), random.uniform(*size), random.choice(colors),
                gravity, drag, square, stain))

    # Handy presets -----------------------------------------------------------
    def dust(self, x, y, color, count=8, direction=0):
        self.burst(x, y, count, [color], speed=(20, 90), life=(0.25, 0.5), size=(2, 4),
                   gravity=-60, drag=4, angle=(math.pi + 0.3, math.tau - 0.3) if direction == 0 else
                   ((math.pi - 0.6, math.pi + 0.2) if direction > 0 else (-0.2, 0.6)))

    def sparks(self, x, y, color, count=12):
        self.burst(x, y, count, [color, (255, 255, 220)], speed=(120, 360), life=(0.15, 0.4),
                   size=(1.5, 3), gravity=600, drag=2)

    def debris(self, rect, color, count=14):
        for _ in range(count):
            px = random.uniform(rect.left, rect.right)
            py = random.uniform(rect.top, rect.bottom)
            self.burst(px, py, 1, [color], speed=(30, 160), life=(0.5, 1.0), size=(3, 7),
                       gravity=1400, drag=0.5, square=True, up_bias=80)

    # Simulation --------------------------------------------------------------
    def update(self, dt, solid_at=None, on_stain=None):
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            if p.drag:
                f = max(0.0, 1.0 - p.drag * dt)
                p.vx *= f
                p.vy *= f
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.angle += p.spin * dt
            if solid_at and (p.stain or p.square) and solid_at(p.x, p.y):
                if p.stain:
                    if on_stain:
                        on_stain(p.x, p.y, p.color, p.size)
                    continue
                # chunks bounce off the ground instead of falling through it
                p.x -= p.vx * dt
                p.y -= p.vy * dt
                p.vy *= -0.35
                p.vx *= 0.6
                p.spin *= 0.5
            alive.append(p)
        self.particles = alive

    def draw(self, surface, cam_x, cam_y=0):
        for p in self.particles:
            t = p.life / p.max_life
            size = p.size * (0.35 + 0.65 * t)
            x = p.x - cam_x
            y = p.y - cam_y
            if p.square:
                s = max(1, int(size * 2))
                c, sn = math.cos(p.angle) * s * 0.7, math.sin(p.angle) * s * 0.7
                pts = [(x + c, y + sn), (x - sn, y + c), (x - c, y - sn), (x + sn, y - c)]
                pygame.draw.polygon(surface, p.color, pts)
            elif size < 1.5:
                surface.fill(p.color, (int(x), int(y), 2, 2))
            else:
                pygame.draw.circle(surface, p.color, (int(x), int(y)), int(size))


class AmbientField:
    """Slow floating motes (embers, fireflies, ash) that make each world feel alive."""

    def __init__(self, width, height, color, count=40, rising=True, seed=3):
        if MOBILE:
            count = max(5, count // 6)
        rng = random.Random(seed)
        self.width, self.height = width, height
        self.color = color
        self.rising = rising
        self.motes = [[rng.uniform(0, width), rng.uniform(0, height), rng.uniform(8, 30),
                       rng.uniform(0, 6.28), rng.uniform(1, 2.6), rng.uniform(0.3, 1.0)]
                      for _ in range(count)]

    def update(self, dt):
        for m in self.motes:
            m[3] += dt
            m[1] += (-m[2] if self.rising else m[2] * 0.6) * dt
            m[0] += math.sin(m[3] * 0.9) * 12 * dt
            if m[1] < -10:
                m[1] = self.height + 10
            elif m[1] > self.height + 10:
                m[1] = -10

    def draw(self, surface, cam_x, parallax=0.6):
        w = self.width
        for x, y, _, phase, size, bright in self.motes:
            flicker = 0.55 + 0.45 * math.sin(phase * 3.1)
            sx = (x - cam_x * parallax) % w
            c = tuple(int(ch * bright * flicker) for ch in self.color)
            pygame.draw.circle(surface, c, (int(sx), int(y)), max(1, int(size)))
