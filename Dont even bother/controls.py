# I am adding comments for me to easily understand the codes
# controls.py - turns keyboard and gamepad input into simple "actions"
# (left, right, jump, confirm...) so the rest of the game never checks raw keys.

import pygame

from touch import TouchControls

# Every action can be triggered by any of these keys
KEYMAP = {
    "left": (pygame.K_a, pygame.K_LEFT),
    "right": (pygame.K_d, pygame.K_RIGHT),
    "up": (pygame.K_w, pygame.K_UP),
    "down": (pygame.K_s, pygame.K_DOWN),
    "jump": (pygame.K_SPACE, pygame.K_w, pygame.K_UP, pygame.K_z, pygame.K_k),
    "confirm": (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER),
    "back": (pygame.K_ESCAPE, pygame.K_BACKSPACE),
    "pause": (pygame.K_ESCAPE, pygame.K_p),
    "restart": (pygame.K_r,),
}

# Xbox-style layout: A=0, B=1, X=2, Y=3, Back=6, Start=7
PAD_BUTTONS = {
    "jump": (0,),
    "confirm": (0,),
    "back": (1,),
    "pause": (7,),
    "restart": (3, 6),
}

AXIS_DEADZONE = 0.45
DIRECTIONS = ("left", "right", "up", "down")


class Controls:
    """Tracks which actions are held, and which were pressed this frame."""

    def __init__(self):
        self.pressed = set()
        self.released = set()
        self._key_held = set()
        self._pad_buttons_held = set()
        self._pad_dirs_prev = set()
        self.pads = {}
        self.touch = TouchControls()      # stays invisible until a finger lands
        self.last_device = "keyboard"
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            self._add_pad(i)

    # -------------------------------------------------------------- devices
    def _add_pad(self, index):
        try:
            pad = pygame.joystick.Joystick(index)
            self.pads[pad.get_instance_id()] = pad
        except pygame.error:
            pass

    # -------------------------------------------------------------- per frame
    def begin_frame(self):
        """Call once per frame before handling events."""
        self.pressed.clear()
        self.released.clear()
        self.touch.begin_frame()
        # Turn stick/d-pad directions into "pressed" edges for menus
        dirs = self._pad_directions()
        for d in dirs - self._pad_dirs_prev:
            self.pressed.add(d)
        self._pad_dirs_prev = dirs

    def process_event(self, event):
        if self.touch.handle_event(event):
            self.last_device = "touch"
            self.pressed.update(self.touch.pressed)
            return
        if event.type == pygame.KEYDOWN:
            self.last_device = "keyboard"
            for action, keys in KEYMAP.items():
                if event.key in keys:
                    self.pressed.add(action)
                    self._key_held.add(action)
        elif event.type == pygame.KEYUP:
            for action, keys in KEYMAP.items():
                if event.key in keys:
                    self.released.add(action)
        elif event.type == pygame.JOYBUTTONDOWN:
            self.last_device = "gamepad"
            for action, buttons in PAD_BUTTONS.items():
                if event.button in buttons:
                    self.pressed.add(action)
        elif event.type == pygame.JOYBUTTONUP:
            for action, buttons in PAD_BUTTONS.items():
                if event.button in buttons:
                    self.released.add(action)
        elif event.type == pygame.JOYDEVICEADDED:
            self._add_pad(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            self.pads.pop(event.instance_id, None)
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.last_device = "mouse"

    # -------------------------------------------------------------- queries
    def _pad_directions(self):
        dirs = set()
        for pad in self.pads.values():
            try:
                x = pad.get_axis(0) if pad.get_numaxes() > 0 else 0
                y = pad.get_axis(1) if pad.get_numaxes() > 1 else 0
                hx, hy = pad.get_hat(0) if pad.get_numhats() > 0 else (0, 0)
            except pygame.error:
                continue
            if x < -AXIS_DEADZONE or hx < 0:
                dirs.add("left")
            if x > AXIS_DEADZONE or hx > 0:
                dirs.add("right")
            if y < -AXIS_DEADZONE or hy > 0:
                dirs.add("up")
            if y > AXIS_DEADZONE or hy < 0:
                dirs.add("down")
        return dirs

    def held(self, action):
        if self.touch.held(action):
            return True
        keys = pygame.key.get_pressed()
        if any(keys[k] for k in KEYMAP.get(action, ())):
            return True
        if action in DIRECTIONS and action in self._pad_dirs_prev:
            return True
        for pad in self.pads.values():
            try:
                for b in PAD_BUTTONS.get(action, ()):
                    if b < pad.get_numbuttons() and pad.get_button(b):
                        return True
            except pygame.error:
                pass
        return False

    def was_pressed(self, action):
        return action in self.pressed

    def consume(self, action):
        """Return True once for a press, so two menus can't both react to it."""
        if action in self.pressed:
            self.pressed.discard(action)
            return True
        return False
