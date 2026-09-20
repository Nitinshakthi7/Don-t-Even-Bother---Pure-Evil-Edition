# I am adding comments for me to easily understand the codes
# renderer.py - draws a World.
#
# Ground tiles and plain spikes never change, so they are drawn once into
# "pages" (1024x1024 images) the first time the camera sees them. Long
# levels therefore cost no more per frame than short ones. Blood stains are
# painted onto pages the same way.

import math

import pygame

from settings import TILE, VIRTUAL_W, VIRTUAL_H, THEMES, BLOOD
from graphics import TileArt, Background, make_light_mask
from particles import AmbientField
from traps import CrumbleBlock

PAGE = 1024


class LevelArt(TileArt):
    """TileArt plus a cache of block images for this level's dynamic blocks."""

    def __init__(self, theme, world):
        super().__init__(theme)
        self.world = world
        self._block_cache = {}

    def neighbours(self, col, row):
        w = self.world
        return (w.looks_solid(col, row - 1), w.looks_solid(col, row + 1),
                w.looks_solid(col - 1, row), w.looks_solid(col + 1, row))

    def block_image(self, block):
        cracked = isinstance(block, CrumbleBlock) and block.cracked
        key = (block.col, block.row, cracked)
        img = self._block_cache.get(key)
        if img is None:
            img = self.make_block_surface(self.neighbours(block.col, block.row), block.col * 7919 + block.row * 104729,
                                          cracked)
            self._block_cache[key] = img
        return img


class PagedLayer:
    """A huge transparent image split into pages that are only created when needed."""

    def __init__(self, width, height, painter=None):
        self.width, self.height = width, height
        self.painter = painter            # fills a fresh page (for baked tiles)
        self.pages = {}

    def page(self, px, py, create=True):
        key = (px, py)
        surf = self.pages.get(key)
        if surf is None and create:
            surf = pygame.Surface((PAGE, PAGE), pygame.SRCALPHA)
            if self.painter:
                self.painter(surf, px * PAGE, py * PAGE)
            self.pages[key] = surf
        return surf

    def draw(self, surface, cam, create=True):
        cx, cy = cam
        for py in range(max(0, cy // PAGE), (cy + VIRTUAL_H) // PAGE + 1):
            for px in range(max(0, cx // PAGE), (cx + VIRTUAL_W) // PAGE + 1):
                if px * PAGE >= self.width or py * PAGE >= self.height:
                    continue
                surf = self.page(px, py, create)
                if surf is not None:
                    surface.blit(surf, (px * PAGE - cx, py * PAGE - cy))


class WorldRenderer:
    def __init__(self, world):
        self.world = world
        self.theme = THEMES[world.defn.theme]
        self.art = LevelArt(self.theme, world)
        self.background = Background(self.theme, seed=world.defn.number * 17)
        self.ambient = AmbientField(VIRTUAL_W, VIRTUAL_H, self.theme["ambient"], count=45,
                                    rising=world.defn.theme in ("ruins", "abyss", "foundry", "neon"),
                                    seed=world.defn.number)
        self.static = PagedLayer(world.width, world.height, self._paint_static)
        self.stains = PagedLayer(world.width, world.height)
        self.light_mask = make_light_mask(190)
        self.darkness = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        self.dark_amount = 1.0 if world.dark else 0.0

    def _paint_static(self, surf, ox, oy):
        """Draw every ground tile, fake wall and plain spike that falls on this page."""
        w = self.world
        c0, c1 = max(0, ox // TILE - 1), min(w.cols - 1, (ox + PAGE) // TILE + 1)
        r0, r1 = max(0, oy // TILE - 1), min(w.nrows - 1, (oy + PAGE) // TILE + 1)
        ghosts = set(w.ghosts)
        for spike in w.static_spikes:
            if c0 <= spike.col <= c1 and r0 <= spike.row <= r1:
                spike.draw(surf, (ox, oy), self.art, 0)
        for r in range(r0, r1 + 1):
            row = w.grid[r]
            for c in range(c0, c1 + 1):
                if row[c] or (c, r) in ghosts:
                    self.art.draw_block(surf, c * TILE - ox, r * TILE - oy, self.art.neighbours(c, r),
                                        c * 7919 + r * 104729)

    def add_stain(self, x, y, color, size):
        """Blood splat that stays on the level (drawn slightly darker than the particle)."""
        if not (0 <= x < self.world.width and 0 <= y < self.world.height):
            return
        dark = tuple(int(ch * 0.75) for ch in color)
        r = max(2, int(size * 1.4))
        px, py = int(x) // PAGE, int(y) // PAGE
        page = self.stains.page(px, py)
        lx, ly = int(x) - px * PAGE, int(y) - py * PAGE
        pygame.draw.circle(page, (*dark, 220), (lx, ly), r)
        pygame.draw.circle(page, (*color, 200), (lx, ly), max(1, r - 2))

    def update(self, dt):
        self.ambient.update(dt)
        target = 1.0 if self.world.dark else 0.0
        self.dark_amount += (target - self.dark_amount) * min(1.0, dt * 6)

    # ------------------------------------------------------------ drawing
    def draw_back(self, surface, cam, t):
        # in tall levels the hills sink away as you climb
        climb = max(0, (self.world.height - VIRTUAL_H) - cam[1])
        self.background.draw(surface, cam[0], climb * 0.15)
        self.ambient.draw(surface, cam[0], 0.25)

    def draw_world(self, surface, cam, t):
        """Everything in the level except the player and particles."""
        w = self.world
        art = self.art
        view = pygame.Rect(cam[0] - 80, cam[1] - 80, VIRTUAL_W + 160, VIRTUAL_H + 160)

        # saw tracks and saws sit behind the ground (so hidden saws really hide)
        for saw in w.saws:
            xs = [p[0] for p in saw.points]
            ys = [p[1] for p in saw.points]
            if saw.show_track and view.colliderect(pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1,
                                                               max(ys) - min(ys) + 1)):
                saw.draw_track(surface, cam)
        for saw in w.saws:
            if view.colliderect(saw.rect):
                saw.draw(surface, cam, art, t)

        # changeable spikes are drawn before blocks so they slide out of the surface
        for s in w.spikes:
            if view.colliderect(s.rect):
                s.draw(surface, cam, art, t)

        self.static.draw(surface, cam)
        # fake walls get a faint shimmer every few seconds - the only hint you get
        pulse = max(0.0, math.sin(t * 1.3)) ** 12
        if pulse > 0.05:
            shimmer = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            shimmer.fill((255, 255, 255, int(28 * pulse)))
            for c, r in w.ghosts:
                if view.collidepoint(c * TILE, r * TILE):
                    surface.blit(shimmer, (c * TILE - cam[0], r * TILE - cam[1]))

        # a group that has risen from the bottom of the level (like a rising spike floor)
        # drags solid rock up with it instead of floating on thin air
        for g in w.groups.values():
            if g.present and g.oy < 0 and g.box.bottom - g.oy >= w.height and g.box.bottom < w.height:
                fill = pygame.Rect(g.box.left - cam[0], g.box.bottom - cam[1], g.box.width, w.height - g.box.bottom)
                pygame.draw.rect(surface, self.theme["block_dark"], fill)
                pygame.draw.line(surface, self.theme["block"], fill.topleft, fill.topright, 3)
        for b in w.blocks:
            if view.colliderect(b.rect) or isinstance(b, CrumbleBlock):
                b.draw(surface, cam, art, t)
        self.stains.draw(surface, cam, create=False)
        self._draw_wind(surface, cam, t)
        for obj in (*w.springs, *w.checkpoints, *w.doors, *w.arrows, *w.cannons, *w.lasers):
            if view.colliderect(obj.rect) or getattr(obj, "beam", None) is not None:
                obj.draw(surface, cam, art, t)
        if w.key is not None:
            w.key.draw(surface, cam, art, t)
            real = w.real_door
            if real is not None and not w.has_key and view.colliderect(real.rect):
                self._draw_padlock(surface, real.rect.move(-cam[0], -cam[1]))
        for e in w.enemies:
            if view.colliderect(e.rect):
                e.draw(surface, cam, art, t)
        for o in w.orbs:
            o.draw(surface, cam, art, t)
        if w.echo is not None:
            w.echo.draw(surface, cam, art, t)

    def _draw_padlock(self, surface, door):
        cx, cy = door.centerx, door.centery + 6
        pygame.draw.rect(surface, (230, 190, 60), (cx - 11, cy - 4, 22, 18), border_radius=4)
        pygame.draw.rect(surface, (30, 20, 10), (cx - 11, cy - 4, 22, 18), 2, border_radius=4)
        pygame.draw.arc(surface, (230, 190, 60), (cx - 8, cy - 16, 16, 20), 0, math.pi, 3)
        pygame.draw.circle(surface, (30, 20, 10), (cx, cy + 4), 3)

    def _draw_wind(self, surface, cam, t):
        """Wind zones show drifting streaks in the direction they push."""
        for area, fx, fy in self.world.winds:
            r = area.move(-cam[0], -cam[1])
            if not r.colliderect(surface.get_rect()):
                continue
            mag = max(1.0, (fx * fx + fy * fy) ** 0.5)
            ux, uy = fx / mag, fy / mag
            tint = pygame.Surface(r.size, pygame.SRCALPHA)
            tint.fill((200, 230, 255, 18))
            surface.blit(tint, r.topleft)
            for i in range(max(4, r.w * r.h // 9000)):
                seed = (i * 7919) % 997
                px = r.x + (seed * 37 + t * ux * 260) % max(1, r.w)
                py = r.y + (seed * 53 + t * uy * 260) % max(1, r.h)
                pygame.draw.line(surface, (220, 240, 255), (px, py), (px - ux * 18, py - uy * 18), 2)

    def draw_death_markers(self, surface, cam, markers, t):
        for i, (x, y) in enumerate(markers):
            sx, sy = int(x - cam[0]), int(y - cam[1])
            if -20 < sx < VIRTUAL_W + 20 and -20 < sy < VIRTUAL_H + 20:
                fresh = i == len(markers) - 1
                size = 7 if fresh else 5
                col = BLOOD if fresh else (150, 30, 44)
                pygame.draw.line(surface, col, (sx - size, sy - size), (sx + size, sy + size), 3)
                pygame.draw.line(surface, col, (sx - size, sy + size), (sx + size, sy - size), 3)

    def draw_darkness(self, surface, cam, focus):
        if self.dark_amount < 0.01:
            return
        self.darkness.fill((0, 0, 0, int(246 * self.dark_amount)))
        if focus is not None:
            fx, fy = int(focus[0] - cam[0]), int(focus[1] - cam[1])
            r = self.light_mask.get_width() // 2
            self.darkness.blit(self.light_mask, (fx - r, fy - r), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(self.darkness, (0, 0))
