# I am adding comments for me to easily understand the codes
# ui.py - reusable menu widgets. One Menu class handles buttons, sliders
# and on/off toggles, and works with keyboard, mouse and gamepad.

import math

import pygame

from settings import PAPER, MUTED, INK, BLOOD, WHITE, DIM, GOLD
from graphics import draw_text, render_text
from utils import damp


class MenuItem:
    """kind is 'button', 'slider' or 'toggle'.
    Sliders/toggles read and write their value through get/set callbacks."""

    def __init__(self, label, action=None, kind="button", get=None, set=None, step=0.1, enabled=True,
                 hint=None):
        self.label = label
        self.action = action
        self.kind = kind
        self.get = get
        self.set = set
        self.step = step
        self.enabled = enabled
        self.hint = hint
        self.anim = 0.0          # 0..1 highlight animation
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.bar_rect = None


class Menu:
    def __init__(self, items, center, spacing=64, width=460, size=36, align="center", accent=BLOOD):
        self.items = items
        self.center = center
        self.spacing = spacing
        self.width = width
        self.size = size
        self.align = align
        self.accent = accent
        self.index = 0
        self.time = 0.0
        self.dragging = False
        self._skip_disabled(1)

    # ------------------------------------------------------------ navigation
    def _skip_disabled(self, direction):
        for _ in range(len(self.items)):
            if self.items[self.index].enabled:
                return
            self.index = (self.index + direction) % len(self.items)

    def move(self, direction, audio=None):
        self.index = (self.index + direction) % len(self.items)
        self._skip_disabled(direction)
        if audio:
            audio.play("ui_move")

    @property
    def current(self):
        return self.items[self.index]

    def _adjust(self, item, direction, audio):
        if item.kind == "slider":
            value = round(min(1.0, max(0.0, item.get() + item.step * direction)), 2)
            item.set(value)
            if audio:
                audio.play("ui_move")
        elif item.kind == "toggle":
            item.set(not item.get())
            if audio:
                audio.play("ui_select")

    def update(self, dt, controls, events, audio=None):
        """Returns the action of an activated button (or None)."""
        self.time += dt
        for i, item in enumerate(self.items):
            item.anim = damp(item.anim, 1.0 if i == self.index else 0.0, 14, dt)

        if controls.consume("up"):
            self.move(-1, audio)
        if controls.consume("down"):
            self.move(1, audio)
        item = self.current
        if item.kind in ("slider", "toggle"):
            if controls.consume("left"):
                self._adjust(item, -1, audio)
            if controls.consume("right"):
                self._adjust(item, 1, audio)
        if controls.consume("confirm") and item.enabled:
            if item.kind == "toggle":
                self._adjust(item, 1, audio)
            elif item.kind == "button":
                if audio:
                    audio.play("ui_select")
                return item.action

        # mouse
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                for i, it in enumerate(self.items):
                    if it.enabled and it.rect.collidepoint(event.pos) and i != self.index:
                        self.index = i
                        if audio:
                            audio.play("ui_move", 0.6)
                if self.dragging and self.current.kind == "slider":
                    self._set_slider_from_mouse(self.current, event.pos[0])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, it in enumerate(self.items):
                    if it.enabled and it.rect.collidepoint(event.pos):
                        self.index = i
                        if it.kind == "slider":
                            self.dragging = True
                            self._set_slider_from_mouse(it, event.pos[0])
                        elif it.kind == "toggle":
                            self._adjust(it, 1, audio)
                        else:
                            if audio:
                                audio.play("ui_select")
                            return it.action
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            elif event.type == pygame.MOUSEWHEEL and self.current.kind == "slider":
                self._adjust(self.current, 1 if event.y > 0 else -1, audio)
        return None

    def _set_slider_from_mouse(self, item, mx):
        if item.bar_rect:
            value = (mx - item.bar_rect.left) / item.bar_rect.width
            item.set(round(min(1.0, max(0.0, value)), 2))

    # ------------------------------------------------------------ drawing
    def draw(self, surface, alpha=255):
        cx, cy = self.center
        top = cy - (len(self.items) - 1) * self.spacing / 2
        for i, item in enumerate(self.items):
            y = int(top + i * self.spacing)
            a = item.anim
            row = pygame.Rect(0, 0, self.width, self.spacing - 10)
            row.center = (cx, y)
            item.rect = row
            # highlight bar: a slanted blade shape that slides in
            if a > 0.02:
                w = int(row.width * (0.55 + 0.45 * a))
                bar = pygame.Surface((w, row.height), pygame.SRCALPHA)
                slant = 16
                pts = [(slant, 0), (w, 0), (w - slant, row.height), (0, row.height)]
                pygame.draw.polygon(bar, (*self.accent, int(220 * a * alpha / 255)), pts)
                bar_x = row.centerx - w // 2
                surface.blit(bar, (bar_x, row.y))
                # little arrow marker, gently bobbing
                bob = math.sin(self.time * 6) * 3
                ax = bar_x - 22 + bob
                pygame.draw.polygon(surface, PAPER, [(ax, y - 9), (ax + 12, y), (ax, y + 9)])

            colour = PAPER if item.enabled else DIM
            if not item.enabled:
                colour = DIM
            elif a < 0.5:
                colour = MUTED if self.align == "split" else PAPER
            size = self.size
            if item.kind == "button" and self.align == "center":
                draw_text(surface, item.label, (cx, y), size, WHITE if a > 0.5 else colour, "display",
                          alpha=alpha, scale=1.0 + 0.06 * a)
                if item.hint:       # e.g. a locked entry saying what it's waiting for
                    draw_text(surface, item.hint, (cx, y + size // 2 + 4), max(12, size - 20), GOLD,
                              "body", bold=True, alpha=alpha)
            else:
                draw_text(surface, item.label, (row.left + 26, y), size, WHITE if a > 0.5 else colour,
                          "body", anchor="midleft", bold=True, alpha=alpha)
                if item.kind == "slider":
                    self._draw_slider(surface, item, row, y, alpha)
                elif item.kind == "toggle":
                    self._draw_toggle(surface, item, row, y, alpha)
                elif item.hint:
                    draw_text(surface, item.hint, (row.right - 26, y), size - 10, MUTED, "body",
                              anchor="midright", alpha=alpha)

    def _draw_slider(self, surface, item, row, y, alpha):
        value = item.get()
        bar = pygame.Rect(0, 0, 220, 10)
        bar.midright = (row.right - 90, y)
        item.bar_rect = bar
        pygame.draw.rect(surface, INK, bar.inflate(4, 4), border_radius=6)
        pygame.draw.rect(surface, DIM, bar, border_radius=5)
        fill = bar.copy()
        fill.width = int(bar.width * value)
        pygame.draw.rect(surface, PAPER, fill, border_radius=5)
        pygame.draw.circle(surface, WHITE, (bar.left + fill.width, y), 10)
        pygame.draw.circle(surface, INK, (bar.left + fill.width, y), 10, 2)
        draw_text(surface, f"{int(round(value * 100))}%", (row.right - 24, y), self.size - 8, PAPER, "body",
                  anchor="midright", alpha=alpha)

    def _draw_toggle(self, surface, item, row, y, alpha):
        on = item.get()
        pill = pygame.Rect(0, 0, 76, 32)
        pill.midright = (row.right - 24, y)
        pygame.draw.rect(surface, (60, 180, 110) if on else DIM, pill, border_radius=16)
        knob_x = pill.right - 16 if on else pill.left + 16
        pygame.draw.circle(surface, WHITE, (knob_x, y), 12)
        label = render_text("ON" if on else "OFF", 16, WHITE, "body", True)
        lx = pill.left + 12 if on else pill.right - 12 - label.get_width()
        surface.blit(label, (lx, y - label.get_height() // 2))
