# I am adding comments for me to easily understand the codes
# touch.py - on-screen buttons for phones and tablets.
#
# The pads stay hidden until something actually touches the screen, so a
# desktop player never sees them and a phone player never has to find a
# setting. Everything reports through Controls like any other device.
#
# Multi-touch matters here: you cannot play a platformer if holding "right"
# stops you pressing "jump". SDL finger events carry an id per finger, so
# each one is tracked separately - mouse events alone would only ever give
# us one contact point.

import math

import pygame

from settings import VIRTUAL_W, VIRTUAL_H

# action, centre, radius, label
LAYOUT = (
    ("left",  (130, VIRTUAL_H - 120), 78, "◀"),
    ("right", (310, VIRTUAL_H - 120), 78, "▶"),
    ("jump",  (VIRTUAL_W - 150, VIRTUAL_H - 130), 92, "JUMP"),
    ("pause", (VIRTUAL_W - 54, 54), 38, "II"),
)

# "up" is the same button as jump for anything that reads a direction
ALIASES = {"jump": ("up",)}


class TouchControls:
    """On-screen buttons, driven by SDL finger events."""

    def __init__(self):
        self.active = False           # flips on the first touch we ever see
        self._fingers = {}            # finger id -> action it is holding
        self.pressed = set()          # actions that went down this frame
        self._faces = {}              # cached button art, drawn once

    # ------------------------------------------------------------ geometry
    @staticmethod
    def _to_virtual(nx, ny):
        """SDL gives finger positions as 0..1 of the window.

        The game draws on a fixed 1280x720 canvas that pygame.SCALED centres
        inside the window with black bars, so undo that letterboxing rather
        than assuming the canvas fills the screen.
        """
        try:
            win_w, win_h = pygame.display.get_window_size()
        except pygame.error:
            win_w, win_h = VIRTUAL_W, VIRTUAL_H
        if not win_w or not win_h:
            return 0.0, 0.0
        scale = min(win_w / VIRTUAL_W, win_h / VIRTUAL_H) or 1.0
        pad_x = (win_w - VIRTUAL_W * scale) / 2
        pad_y = (win_h - VIRTUAL_H * scale) / 2
        return (nx * win_w - pad_x) / scale, (ny * win_h - pad_y) / scale

    @staticmethod
    def _hit(x, y):
        """Which button, if any, is under this point."""
        for action, (cx, cy), radius, _label in LAYOUT:
            # a little forgiveness: fingers are fatter than a mouse pointer
            if math.hypot(x - cx, y - cy) <= radius * 1.25:
                return action
        return None

    # ------------------------------------------------------------ per frame
    def begin_frame(self):
        self.pressed.clear()

    def handle_event(self, event):
        """True if this was a touch event, so the caller can stop there."""
        if event.type not in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            return False
        self.active = True
        finger = getattr(event, "finger_id", None)
        if event.type == pygame.FINGERUP:
            self._fingers.pop(finger, None)
            return True

        action = self._hit(*self._to_virtual(event.x, event.y))
        was = self._fingers.get(finger)
        if action == was:
            return True
        if action is None:
            self._fingers.pop(finger, None)      # slid off the button
            return True
        # sliding from one button onto another counts as pressing the new one
        self._fingers[finger] = action
        self.pressed.add(action)
        for alias in ALIASES.get(action, ()):
            self.pressed.add(alias)
        return True

    # ------------------------------------------------------------ queries
    def held(self, action):
        if not self.active:
            return False
        holding = set(self._fingers.values())
        for held in list(holding):
            holding.update(ALIASES.get(held, ()))
        return action in holding

    # ------------------------------------------------------------ drawing
    def _face(self, action, radius, label, lit):
        """The button art, built once and reused.

        Translucent blits are the expensive thing in a browser, so these are
        baked rather than redrawn, and they are small enough to be cheap.
        """
        key = (action, lit)
        surf = self._faces.get(key)
        if surf is not None:
            return surf
        from graphics import draw_text
        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        fill = (255, 255, 255, 70) if lit else (255, 255, 255, 34)
        edge = (255, 255, 255, 200) if lit else (255, 255, 255, 110)
        pygame.draw.circle(surf, fill, (radius, radius), radius)
        pygame.draw.circle(surf, edge, (radius, radius), radius, 3)
        draw_text(surf, label, (radius, radius), 30 if len(label) > 2 else 40,
                  (255, 255, 255), bold=True)
        self._faces[key] = surf
        return surf

    def draw(self, surface):
        if not self.active:
            return
        for action, (cx, cy), radius, label in LAYOUT:
            face = self._face(action, radius, label, self.held(action))
            surface.blit(face, (cx - radius, cy - radius))
