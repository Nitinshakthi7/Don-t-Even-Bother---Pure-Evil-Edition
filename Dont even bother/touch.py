# I am adding comments for me to easily understand the codes
# touch.py - on-screen buttons for phones and tablets.
#
# The pad stays hidden until something actually touches the screen, so a
# desktop player never sees it and a phone player never has to find a setting.
# Everything reports through Controls like any other device.
#
# Multi-touch matters here: you cannot play a platformer if holding "right"
# stops you pressing "jump". SDL finger events carry an id per finger, so each
# one is tracked separately - mouse events alone only ever give one contact.
#
# Two things drive the look:
#   - every icon is drawn with shapes, never font glyphs. The display face is
#     Impact, which has no arrow characters, so the old labels were rendering
#     as identical blank boxes.
#   - the faces are colour-keyed rather than translucent. A translucent blit
#     costs ~35ms a screenful in a browser, and five of them per frame was a
#     real share of a phone's budget; a colour key blits RLE-encoded and skips
#     everything outside the button.

import math

import pygame

from settings import VIRTUAL_W, VIRTUAL_H, PAPER, BLOOD, GOLD, INK, MUTED

KEY = (255, 0, 255)          # never appears in the art
FACE = (20, 15, 28)          # button body, matches the game's panels
FACE_LIT = (58, 20, 34)      # pressed

# action, centre, radius, kind
# Thumbs sit in the bottom corners, so the pad lives there, and the rarely
# used buttons go up top out of the way.
PLAY_LAYOUT = (
    ("left",    (150, VIRTUAL_H - 130), 92, "left"),
    ("right",   (350, VIRTUAL_H - 130), 92, "right"),
    ("jump",    (VIRTUAL_W - 160, VIRTUAL_H - 140), 108, "jump"),
    # Top-left, beside the death counter. The right of the HUD is taken by the
    # timer and by achievement toasts, and the bottom corners are where thumbs
    # rest - a stray restart in this game would be unforgivable.
    ("pause",   (268, 56), 46, "pause"),
    ("restart", (378, 56), 46, "restart"),
)

# Menus are tapped directly, but every one of them expects an ESC to back out
# of, and a phone has no ESC.
MENU_LAYOUT = (
    # clear of the menu list above and the footer text below
    ("back", (126, VIRTUAL_H - 112), 72, "back"),
)

LAYOUTS = {"play": PLAY_LAYOUT, "menu": MENU_LAYOUT}

# "up" is the same button as jump for anything that reads a direction
ALIASES = {"jump": ("up",)}


# ---------------------------------------------------------------- icon art
def _triangle(surf, centre, size, colour, pointing):
    cx, cy = centre
    h = size
    if pointing == "left":
        pts = [(cx - h * 0.62, cy), (cx + h * 0.42, cy - h * 0.72), (cx + h * 0.42, cy + h * 0.72)]
    elif pointing == "right":
        pts = [(cx + h * 0.62, cy), (cx - h * 0.42, cy - h * 0.72), (cx - h * 0.42, cy + h * 0.72)]
    else:                                              # up
        pts = [(cx, cy - h * 0.66), (cx - h * 0.74, cy + h * 0.40), (cx + h * 0.74, cy + h * 0.40)]
    pygame.draw.polygon(surf, colour, pts)
    pygame.draw.polygon(surf, INK, pts, 3)


def _pause_icon(surf, centre, size, colour):
    cx, cy = centre
    w, h = max(4, int(size * 0.30)), int(size * 1.6)
    for dx in (-1, 1):
        bar = pygame.Rect(0, 0, w, h)
        bar.center = (cx + dx * w, cy)
        pygame.draw.rect(surf, colour, bar, border_radius=2)


def _restart_icon(surf, centre, size, colour):
    """A circular arrow, drawn rather than typed - Impact has no such glyph.

    pygame.draw.arc is thin and ragged at small sizes, so the ring is built
    from short segments instead, which stays even and reads cleanly.
    """
    cx, cy = centre
    r = size * 0.92
    thick = max(3, int(size * 0.30))
    start, end = 55, 340                      # degrees, leaving a gap for the head
    step = 6
    prev = None
    for deg in range(start, end + 1, step):
        a = math.radians(deg)
        point = (cx + r * math.cos(a), cy - r * math.sin(a))
        if prev is not None:
            pygame.draw.line(surf, colour, prev, point, thick)
        prev = point
    # arrowhead at the open end, pointing the way the ring turns
    a = math.radians(start)
    tip = (cx + r * math.cos(a), cy - r * math.sin(a))
    head = size * 0.62
    along = (math.cos(a - math.pi / 2), -math.sin(a - math.pi / 2))
    out = (math.cos(a), -math.sin(a))
    pygame.draw.polygon(surf, colour, [
        (tip[0] + along[0] * head, tip[1] + along[1] * head),
        (tip[0] + out[0] * head * 0.62, tip[1] + out[1] * head * 0.62),
        (tip[0] - out[0] * head * 0.62, tip[1] - out[1] * head * 0.62),
    ])


class TouchControls:
    """On-screen buttons, driven by SDL finger events."""

    def __init__(self):
        self.active = False           # flips on the first touch we ever see
        self._fingers = {}            # finger id -> action it is holding
        self.pressed = set()          # actions that went down this frame
        self._faces = {}              # cached button art, drawn once
        self.mode = "menu"            # which set of buttons is on screen

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
    def _hit(x, y, mode):
        """Which button, if any, is under this point.

        Generous on purpose, and nearest wins: a thumb is a wide, imprecise
        thing, and missing a jump because you were ten pixels low is the worst
        possible way to die in this game.
        """
        best, best_d = None, None
        for action, (cx, cy), radius, _kind in LAYOUTS[mode]:
            d = math.hypot(x - cx, y - cy)
            if d <= radius * 1.45 and (best_d is None or d < best_d):
                best, best_d = action, d
        return best

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

        where = self._to_virtual(event.x, event.y)
        action = self._hit(*where, self.mode)
        was = self._fingers.get(finger)
        if action is None:
            self._fingers.pop(finger, None)      # slid off the button, or missed
            # A tap on empty space is how you use a menu. This has to come
            # before the "nothing changed" check below, because a tap that
            # hits no button leaves both action and was as None.
            if event.type == pygame.FINGERDOWN:
                self._as_click(where)
            return True
        if action == was:
            return True
        # sliding from one button onto another counts as pressing the new one
        self._fingers[finger] = action
        self.pressed.add(action)
        for alias in ALIASES.get(action, ()):
            self.pressed.add(alias)
        return True

    @staticmethod
    def _as_click(where):
        """Report a tap that missed the buttons as a mouse click.

        Menus are all built around clicking, and a phone has no mouse. The
        motion goes first so anything that highlights on hover has caught up
        by the time the click lands.
        """
        pos = (int(where[0]), int(where[1]))
        for event, extra in ((pygame.MOUSEMOTION, {"rel": (0, 0), "buttons": (0, 0, 0)}),
                             (pygame.MOUSEBUTTONDOWN, {"button": 1}),
                             (pygame.MOUSEBUTTONUP, {"button": 1})):
            try:
                pygame.event.post(pygame.event.Event(event, pos=pos, touch=True, **extra))
            except pygame.error:
                return

    # ------------------------------------------------------------ queries
    def held(self, action):
        if not self.active:
            return False
        holding = set(self._fingers.values())
        for held in list(holding):
            holding.update(ALIASES.get(held, ()))
        return action in holding

    # ------------------------------------------------------------ drawing
    def _face(self, kind, radius, lit):
        """The button art, built once and reused.

        Colour-keyed rather than translucent: SDL blits these RLE-encoded and
        skips every pixel outside the button, which matters when five of them
        go over the top of the game on a phone every frame.
        """
        key = (kind, radius, lit)
        surf = self._faces.get(key)
        if surf is not None:
            return surf

        from graphics import draw_text
        size = radius * 2 + 12
        surf = pygame.Surface((size, size))
        surf.fill(KEY)
        mid = size // 2
        body = FACE_LIT if lit else FACE
        ring = GOLD if lit else PAPER

        if kind in ("left", "right"):
            # a chunky rounded square, like the level's blocks
            box = pygame.Rect(0, 0, radius * 2, radius * 2)
            box.center = (mid, mid)
            pygame.draw.rect(surf, body, box, border_radius=22)
            pygame.draw.rect(surf, ring, box, 5, border_radius=22)
            _triangle(surf, (mid, mid), radius * 0.52, ring, kind)
        elif kind == "jump":
            pygame.draw.circle(surf, body, (mid, mid), radius)
            pygame.draw.circle(surf, GOLD if lit else BLOOD, (mid, mid), radius, 6)
            _triangle(surf, (mid, int(mid - radius * 0.20)), radius * 0.42, ring, "up")
            draw_text(surf, "JUMP", (mid, int(mid + radius * 0.50)), 30, ring, "display")
        elif kind == "back":
            box = pygame.Rect(0, 0, radius * 2, int(radius * 1.15))
            box.center = (mid, mid)
            pygame.draw.rect(surf, body, box, border_radius=16)
            pygame.draw.rect(surf, ring, box, 5, border_radius=16)
            _triangle(surf, (int(mid - radius * 0.56), mid), radius * 0.28, ring, "left")
            draw_text(surf, "BACK", (int(mid + radius * 0.20), mid), 30, ring, "display")
        else:
            box = pygame.Rect(0, 0, radius * 2, radius * 2)
            box.center = (mid, mid)
            pygame.draw.rect(surf, body, box, border_radius=16)
            pygame.draw.rect(surf, ring if lit else MUTED, box, 4, border_radius=16)
            if kind == "pause":
                _pause_icon(surf, (mid, mid), radius * 0.42, ring)
            else:
                _restart_icon(surf, (mid, mid), radius * 0.46, ring)

        try:
            surf = surf.convert()
        except pygame.error:
            pass
        surf.set_colorkey(KEY, pygame.RLEACCEL)
        self._faces[key] = surf
        return surf

    def draw(self, surface, mode="play"):
        """Draw the buttons for this kind of scene, and remember which set is up."""
        if mode != self.mode:
            # Buttons that no longer exist cannot be let go of, so a jump held
            # as the pause menu opens would stay held forever.
            self._fingers.clear()
            self.mode = mode
        if not self.active:
            return
        for action, (cx, cy), radius, kind in LAYOUTS[mode]:
            face = self._face(kind, radius, self.held(action))
            surface.blit(face, (cx - face.get_width() // 2, cy - face.get_height() // 2))
