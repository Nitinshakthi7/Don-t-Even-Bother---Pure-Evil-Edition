# I am adding comments for me to easily understand the codes
# graphics.py - fonts, cached text, gradients and every procedurally drawn
# piece of art (tiles, spikes, saws, doors, backgrounds, icons).
# Nothing here needs an image file, so the game looks crisp at any size.

import math
import random
from collections import OrderedDict

import pygame

from settings import (LOW_FX, TILE, VIRTUAL_W, VIRTUAL_H, STEEL, STEEL_DARK, INK, PAPER, WHITE,
                      BLOOD, GOLD)
from utils import lerp_colour

# ------------------------------------------------------------------ fonts & text
FONT_FACES = {
    "body": "bahnschrift,segoeui,helveticaneue,arial",
    "display": "impact,bahnschrift,arialblack,arial",
    "mono": "consolas,menlo,couriernew",
}

_fonts = {}
_text_cache = OrderedDict()


def font(size, kind="body", bold=False):
    key = (size, kind, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.SysFont(FONT_FACES[kind], size, bold=bold)
        except Exception:
            _fonts[key] = pygame.font.Font(None, int(size * 1.3))
    return _fonts[key]


def render_text(text, size, color, kind="body", bold=False):
    """Rendered text is cached, because rendering fonts every frame is slow."""
    key = (text, size, color, kind, bold)
    surf = _text_cache.get(key)
    if surf is None:
        surf = font(size, kind, bold).render(text, True, color)
        _text_cache[key] = surf
        if len(_text_cache) > 600:
            _text_cache.popitem(last=False)
    else:
        _text_cache.move_to_end(key)
    return surf


def draw_text(surface, text, pos, size, color, kind="body", anchor="center", bold=False,
              shadow=None, alpha=255, scale=1.0):
    surf = render_text(text, size, color, kind, bold)
    if scale != 1.0:
        surf = pygame.transform.smoothscale(
            surf, (max(1, int(surf.get_width() * scale)), max(1, int(surf.get_height() * scale))))
    rect = surf.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        sh = render_text(text, size, shadow, kind, bold)
        if scale != 1.0:
            sh = pygame.transform.smoothscale(sh, surf.get_size())
        if alpha < 255:
            sh = sh.copy()
            sh.set_alpha(alpha)
        surface.blit(sh, rect.move(3, 3))
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(alpha)
    surface.blit(surf, rect)
    return rect


# ------------------------------------------------------------------ basic shapes
def vertical_gradient(width, height, top, bottom):
    surf = pygame.Surface((width, height)).convert()
    for y in range(height):
        pygame.draw.line(surf, lerp_colour(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surf


def make_vignette(width, height, strength=170):
    """Dark edges, clear centre. Built once and reused every frame."""
    small_w, small_h = width // 8, height // 8
    small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    cx, cy = small_w / 2, small_h / 2
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot((x - cx) * 0.9, y - cy) / max_d
            a = int(strength * max(0.0, d - 0.45) / 0.55 * 1.2)
            small.set_at((x, y), (0, 0, 0, min(255, a)))
    return fast(pygame.transform.smoothscale(small, (width, height)))


def make_light_mask(radius, darkness=246):
    """Alpha mask used for the 'lights out' levels: transparent circle, dark edge."""
    size = radius * 2
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    mask.fill((0, 0, 0, darkness))
    for r in range(radius, 0, -2):
        t = r / radius
        a = int(darkness * (t ** 2.2))
        pygame.draw.circle(mask, (0, 0, 0, a), (radius, radius), r)
    return mask


def make_grain_frames(count=4, w=VIRTUAL_W // 2, h=VIRTUAL_H // 2, alpha=15):
    frames = []
    try:
        import numpy as np
        for _ in range(count):
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            noise = np.random.randint(0, 255, (w, h), dtype=np.uint8)
            rgb = pygame.surfarray.pixels3d(surf)
            rgb[:, :, 0] = noise
            rgb[:, :, 1] = noise
            rgb[:, :, 2] = noise
            del rgb
            alpha_arr = pygame.surfarray.pixels_alpha(surf)
            alpha_arr[:, :] = alpha
            del alpha_arr
            frames.append(pygame.transform.scale(surf, (w * 2, h * 2)))
    except ImportError:
        pass
    return frames


def panel(surface, rect, fill=(18, 14, 26, 225), border=(255, 255, 255, 40), radius=14, width=2):
    shape = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shape, fill, shape.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(shape, border, shape.get_rect(), width, border_radius=radius)
    surface.blit(shape, rect.topleft)


def fast(surface, alpha=True):
    """Match the display's pixel format so blits don't convert every frame.

    Software renderers (a browser, mainly) pay that conversion on every single
    blit, which is where most of a frame goes if you let it.
    """
    try:
        return surface.convert_alpha() if alpha else surface.convert()
    except pygame.error:
        return surface            # no display yet: fine, just slower


_DIM_CACHE = {}


def dim(surface, alpha=150, color=(0, 0, 0)):
    """A translucent wash over the whole surface.

    The shade is cached per size, colour and alpha. It used to allocate and
    fill a fresh 1280x720 surface on every call, several times a frame, which
    is cheap on a desktop GPU and very expensive under a browser's software
    renderer.
    """
    alpha = max(0, min(255, int(alpha)))
    if alpha <= 0:
        return
    key = (surface.get_size(), color, alpha)
    shade = _DIM_CACHE.get(key)
    if shade is None:
        if len(_DIM_CACHE) > 96:          # a scene fading in touches many alphas
            _DIM_CACHE.clear()
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((*color, alpha))
        shade = fast(shade)
        _DIM_CACHE[key] = shade
    surface.blit(shade, (0, 0))


_GLOW_CACHE = {}


def glow_circle(radius, color, intensity=120):
    """A soft radial glow.

    Built from radius/2 stacked circles, so it is far too expensive to make
    fresh every frame - and it used to be, several times a frame. Cached on
    the arguments instead; pulsing callers round to a handful of entries.
    """
    key = (radius, color, int(intensity))
    surf = _GLOW_CACHE.get(key)
    if surf is None:
        if len(_GLOW_CACHE) > 160:
            _GLOW_CACHE.clear()
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            a = int(intensity * (1 - r / radius) ** 1.6)
            pygame.draw.circle(surf, (*color, a), (radius, radius), r)
        surf = fast(surf)
        _GLOW_CACHE[key] = surf
    return surf


# ------------------------------------------------------------------ icons
def draw_skull(surface, center, size, color=PAPER, eye=INK):
    x, y = center
    r = size // 2
    pygame.draw.circle(surface, color, (x, y - r // 5), r)
    pygame.draw.rect(surface, color, (x - r * 0.62, y + r * 0.2, r * 1.24, r * 0.75), border_radius=max(1, r // 4))
    er = max(2, r // 3)
    pygame.draw.circle(surface, eye, (x - r * 0.4, y - r * 0.1), er)
    pygame.draw.circle(surface, eye, (x + r * 0.4, y - r * 0.1), er)
    pygame.draw.polygon(surface, eye, [(x, y + r * 0.15), (x - r * 0.15, y + r * 0.4), (x + r * 0.15, y + r * 0.4)])
    for i in (-1, 0, 1):
        pygame.draw.line(surface, eye, (x + i * r * 0.28, y + r * 0.62), (x + i * r * 0.28, y + r * 0.92), max(1, r // 8))


def draw_lock(surface, center, size, color):
    x, y = center
    w = size
    pygame.draw.rect(surface, color, (x - w // 2, y - w // 6, w, int(w * 0.75)), border_radius=w // 8)
    pygame.draw.arc(surface, color, (x - w // 3, y - w * 0.62, w * 2 // 3, w * 0.9), 0, math.pi, max(3, w // 7))
    pygame.draw.circle(surface, INK, (x, y + w // 6), max(2, w // 9))


def draw_clock(surface, center, size, color):
    x, y = center
    pygame.draw.circle(surface, color, center, size // 2, max(2, size // 9))
    pygame.draw.line(surface, color, center, (x, y - size * 0.3), 2)
    pygame.draw.line(surface, color, center, (x + size * 0.22, y), 2)


# ------------------------------------------------------------------ tile art
class TileArt:
    """Pre-renders all level art for one theme."""

    def __init__(self, theme):
        self.theme = theme
        self.spikes = {d: self._make_spike(d) for d in ("up", "down", "left", "right")}
        self.saw_frames = {}

    # blocks ---------------------------------------------------------------
    def draw_block(self, surface, x, y, neighbours, seed, cracked=False):
        """Draw one 40x40 block. neighbours = (up, down, left, right) solid flags."""
        up, down, left, right = neighbours
        t = self.theme
        rng = random.Random(seed)
        # chamfer the outside corners slightly for a softer, hand-made look
        c = 5
        pts = [
            (x + (c if not up and not left else 0), y),
            (x + TILE - (c if not up and not right else 0), y),
            (x + TILE, y + (c if not up and not right else 0)),
            (x + TILE, y + TILE - (c if not down and not right else 0)),
            (x + TILE - (c if not down and not right else 0), y + TILE),
            (x + (c if not down and not left else 0), y + TILE),
            (x, y + TILE - (c if not down and not left else 0)),
            (x, y + (c if not up and not left else 0)),
        ]
        pygame.draw.polygon(surface, t["block"], pts)
        # texture: a few stones / rivets
        for _ in range(3):
            w = rng.randint(6, 14)
            h = rng.randint(4, 8)
            px = x + rng.randint(3, TILE - w - 3)
            py = y + rng.randint(12 if not up else 4, TILE - h - 3)
            pygame.draw.rect(surface, t["block_detail"], (px, py, w, h), border_radius=2)
        # shading on exposed sides
        if not down:
            pygame.draw.rect(surface, t["block_dark"], (x + (c if not left else 0), y + TILE - 6,
                                                        TILE - (c if not left else 0) - (c if not right else 0), 6))
        if not left:
            pygame.draw.line(surface, t["block_dark"], (x, y + c), (x, y + TILE - c), 3)
        if not right:
            pygame.draw.line(surface, t["block_dark"], (x + TILE - 2, y + c), (x + TILE - 2, y + TILE - c), 3)
        # top cap (grass / moss / hazard paint / lava crust depending on theme)
        if not up:
            cap_l = x + (c if not left else 0)
            cap_w = TILE - (c if not left else 0) - (c if not right else 0)
            pygame.draw.rect(surface, t["block_top"], (cap_l, y, cap_w, 8))
            pygame.draw.line(surface, lerp_colour(t["block_top"], WHITE, 0.35), (cap_l, y), (cap_l + cap_w - 1, y), 2)
            for _ in range(rng.randint(1, 3)):
                dx = rng.randint(2, TILE - 8)
                pygame.draw.rect(surface, t["block_top"], (x + dx, y + 8, rng.randint(3, 6), rng.randint(2, 6)),
                                 border_radius=2)
        if cracked:
            crack = lerp_colour(t["block_dark"], INK, 0.5)
            pygame.draw.lines(surface, crack, False, [(x + 8, y + 10), (x + 16, y + 20), (x + 12, y + 30), (x + 20, y + 38)], 2)
            pygame.draw.lines(surface, crack, False, [(x + 30, y + 9), (x + 24, y + 18), (x + 32, y + 26)], 2)

    def make_block_surface(self, neighbours, seed, cracked=False):
        surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        self.draw_block(surf, 0, 0, neighbours, seed, cracked)
        return surf

    # spikes ---------------------------------------------------------------
    def _make_spike(self, direction):
        surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        base_y = TILE
        height = 24
        for i in range(2):
            left = 2 + i * 18
            tip = (left + 9, base_y - height)
            bl, br = (left, base_y), (left + 18, base_y)
            pygame.draw.polygon(surf, STEEL, [bl, tip, br])
            pygame.draw.polygon(surf, STEEL_DARK, [(left + 9, base_y), tip, br])
            pygame.draw.line(surf, WHITE, (left + 3, base_y - 4), (tip[0] - 1, tip[1] + 4), 1)
            pygame.draw.polygon(surf, INK, [bl, tip, br], 2)
            pygame.draw.circle(surf, BLOOD, (tip[0], tip[1] + 3), 2)
        angle = {"up": 0, "down": 180, "left": 90, "right": -90}[direction]
        return pygame.transform.rotate(surf, angle)

    # saws -----------------------------------------------------------------
    def saw_frame(self, radius, angle):
        """Rotated saw images are cached in 10 degree steps."""
        key = (radius, int(angle % 360) // 10)
        frame = self.saw_frames.get(key)
        if frame is None:
            base = self.saw_frames.get((radius, "base"))
            if base is None:
                base = self._make_saw(radius)
                self.saw_frames[(radius, "base")] = base
            frame = pygame.transform.rotate(base, -key[1] * 10)
            self.saw_frames[key] = frame
        return frame

    def _make_saw(self, radius):
        size = radius * 2 + 8
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        teeth = 12
        pts = []
        for i in range(teeth * 2):
            a = math.pi * i / teeth
            r = radius + 4 if i % 2 == 0 else radius - 5
            pts.append((c + math.cos(a) * r, c + math.sin(a) * r))
        pygame.draw.polygon(surf, STEEL, pts)
        pygame.draw.polygon(surf, INK, pts, 2)
        pygame.draw.circle(surf, STEEL_DARK, (c, c), radius - 9)
        pygame.draw.circle(surf, lerp_colour(STEEL, WHITE, 0.3), (c, c), radius - 12, 2)
        for i in range(3):
            a = i * math.tau / 3
            pygame.draw.circle(surf, INK, (c + math.cos(a) * radius * 0.45, c + math.sin(a) * radius * 0.45), 3)
        pygame.draw.circle(surf, BLOOD, (c, c), 6)
        pygame.draw.circle(surf, INK, (c, c), 6, 2)
        return surf


def draw_door(surface, rect, t, accent, open_amount=0.0):
    """The exit door. Real and fake doors use exactly the same drawing. Of course."""
    x, y, w, h = rect
    frame = (50, 40, 58)
    pygame.draw.rect(surface, frame, (x - 4, y - 4, w + 8, h + 4), border_top_left_radius=22, border_top_right_radius=22)
    inner = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, (10, 6, 16), inner, border_top_left_radius=18, border_top_right_radius=18)
    # swirling portal light
    cx, cy = inner.centerx, inner.centery + 4
    for i in range(5):
        phase = t * 2.2 + i * 1.3
        r = int(8 + i * 3 + math.sin(phase) * 2)
        col = lerp_colour(accent, WHITE, 0.15 * (4 - i))
        pygame.draw.ellipse(surface, col, (cx - r * 0.7, cy - r, r * 1.4, r * 2), 2)
    pygame.draw.ellipse(surface, lerp_colour(accent, WHITE, 0.6), (cx - 4, cy - 7, 8, 14))
    # sign above the door
    pygame.draw.rect(surface, GOLD, (x + w // 2 - 12, y - 16, 24, 9), border_radius=3)
    pygame.draw.rect(surface, INK, (x + w // 2 - 12, y - 16, 24, 9), 1, border_radius=3)


# ------------------------------------------------------------------ backgrounds
class Background:
    """Gradient sky, stars, two layers of parallax hills. Built once per theme."""

    def __init__(self, theme, seed=11):
        self.theme = theme
        rng = random.Random(seed)
        self.sky = vertical_gradient(VIRTUAL_W, VIRTUAL_H, theme["sky_top"], theme["sky_bottom"])
        if theme.get("stars"):
            for _ in range(140):
                x, y = rng.randint(0, VIRTUAL_W), rng.randint(0, int(VIRTUAL_H * 0.6))
                b = rng.randint(90, 230)
                self.sky.fill((b, b, b), (x, y, rng.choice((1, 1, 2)), rng.choice((1, 1, 2))))
        # a big pale moon / sun
        moon = glow_circle(170, lerp_colour(theme["sky_bottom"], WHITE, 0.5), 90)
        self.sky.blit(moon, (VIRTUAL_W * 0.72 - 170, 120 - 170))
        pygame.draw.circle(self.sky, lerp_colour(theme["sky_bottom"], WHITE, 0.55), (int(VIRTUAL_W * 0.72), 120), 46)
        self.sky = fast(self.sky, alpha=False)
        self.far = self._hills(theme["far"], base=VIRTUAL_H * 0.55, amp=110, rng=rng, jagged=True)
        self.near = self._hills(theme["near"], base=VIRTUAL_H * 0.7, amp=70, rng=rng, jagged=False)
        self._tall = None          # baked on first use when LOW_FX is on
        self._max_sink = 0         # how much headroom that bake has above the sky

    @staticmethod
    def _hills(color, base, amp, rng, jagged):
        """Tileable silhouette built from sine waves whose periods divide the width."""
        w, h = VIRTUAL_W, VIRTUAL_H
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        waves = [(rng.choice((1, 2, 3)), rng.uniform(0, 6.28), 1.0),
                 (rng.choice((4, 5, 6)), rng.uniform(0, 6.28), 0.45),
                 (rng.choice((9, 11, 13)), rng.uniform(0, 6.28), 0.2 if not jagged else 0.35)]
        pts = [(0, h)]
        for x in range(0, w + 1, 8):
            y = base
            for freq, phase, weight in waves:
                y -= math.sin(x / w * math.tau * freq + phase) * amp * weight
            pts.append((x, y))
        pts.append((w, h))
        pygame.draw.polygon(surf, color, pts)
        return fast(surf)

    def _bake_tall(self, max_sink):
        """Sky and both hill layers flattened into one opaque image, with
        max_sink pixels of spare sky above them.

        The headroom is what lets climbing stay cheap: sinking the hills
        becomes a matter of sliding the source window down this image, so it
        is still a single opaque blit no matter how high you are.
        """
        tall = pygame.Surface((VIRTUAL_W, VIRTUAL_H + max_sink))
        if max_sink:
            tall.fill(self.sky.get_at((0, 0)), (0, 0, VIRTUAL_W, max_sink))
        tall.blit(self.sky, (0, max_sink))
        tall.blit(self.far, (0, max_sink))
        tall.blit(self.near, (0, max_sink))
        self._max_sink = max_sink
        return fast(tall, alpha=False)

    def draw(self, surface, cam_x, sink=0):
        """sink pushes the hills down (used while climbing tall levels)."""
        if LOW_FX:
            # Every layer here is translucent, and a full-screen translucent
            # blit costs ~35ms in a browser against ~0.6ms for an opaque one.
            # Climbing used to fall through to four of them, which is why the
            # frame rate tracked how high up the level you were.
            need = min(int(sink), VIRTUAL_H)
            if self._tall is None or need > self._max_sink:
                self._tall = self._bake_tall(min(VIRTUAL_H, ((need + 127) // 128) * 128))
            top = self._max_sink - need
            # one screenful of opaque pixels, wrapped, so the hills still drift
            off = int(cam_x * 0.25) % VIRTUAL_W
            surface.blit(self._tall, (0, 0), (off, top, VIRTUAL_W - off, VIRTUAL_H))
            if off:
                surface.blit(self._tall, (VIRTUAL_W - off, 0), (0, top, off, VIRTUAL_H))
            return
        surface.blit(self.sky, (0, 0))
        for layer, factor, depth in ((self.far, 0.15, 0.6), (self.near, 0.35, 1.0)):
            off = int(cam_x * factor) % VIRTUAL_W
            dy = int(sink * depth)
            if dy >= VIRTUAL_H:
                continue
            surface.blit(layer, (-off, dy))
            surface.blit(layer, (VIRTUAL_W - off, dy))
