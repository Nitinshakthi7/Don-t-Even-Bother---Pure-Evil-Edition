# I am adding comments for me to easily understand the codes
# utils.py - small maths helpers, the save system and the camera

import json
import math
import os
import random

import settings
from settings import (DEFAULT_SETTINGS, VIRTUAL_W, VIRTUAL_H, CAMERA_LOOKAHEAD,
                      CAMERA_SMOOTH, RANKS)


# ------------------------------------------------------------------ maths helpers
def clamp(value, low, high):
    """Keep a value between low and high."""
    return max(low, min(high, value))


def lerp(a, b, t):
    """Blend from a to b by t (0..1)."""
    return a + (b - a) * t


def lerp_colour(c1, c2, t):
    """Blend two RGB colours."""
    t = clamp(t, 0.0, 1.0)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def approach(value, target, amount):
    """Move value towards target by at most amount (never overshoots)."""
    if value < target:
        return min(value + amount, target)
    return max(value - amount, target)


def damp(current, target, smoothing, dt):
    """Frame-rate independent smooth follow."""
    return current + (target - current) * (1.0 - math.exp(-smoothing * dt))


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return 3 * t * t - 2 * t * t * t


def ease_in_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t


def ease_out_back(t):
    t = clamp(t, 0.0, 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def format_time(seconds):
    """Turn 83.456 into '1:23.45'."""
    if seconds is None:
        return "--:--.--"
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes}:{secs:05.2f}"


def rank_for_deaths(deaths):
    """Return (letter, comment) for the number of deaths in a clear."""
    for letter, limit, comment in RANKS:
        if deaths <= limit:
            return letter, comment
    return RANKS[-1][0], RANKS[-1][2]


# ------------------------------------------------------------------ save system
class SaveManager:
    """Stores progress, stats and settings in a JSON file next to the game.

    Progress is kept separately for each difficulty ("modes"), so beating
    Normal doesn't unlock anything in Brutal. Lifetime deaths are shared.
    """

    VERSION = 3

    def __init__(self, level_count, path=None, unlock_all=False):
        self.path = path or settings.SAVE_FILE
        self.level_count = level_count
        self.unlock_all = unlock_all
        self.dirty = False
        self.data = self._fresh_data()
        self.load()

    @staticmethod
    def _fresh_mode():
        return {"unlocked": 1, "levels": {}, "completed": False}

    def _fresh_data(self):
        return {
            "version": self.VERSION,
            "total_deaths": 0,
            "total_time": 0.0,
            "difficulty": None,
            "modes": {"normal": self._fresh_mode(), "brutal": self._fresh_mode()},
            "settings": dict(DEFAULT_SETTINGS),
        }

    # -------------------------------------------------------------- disk
    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            print(f"[save] Could not read '{self.path}', starting fresh.")
            return
        if not isinstance(raw, dict):
            return
        version = raw.get("version")
        self.data["total_deaths"] = int(raw.get("total_deaths", 0))
        self.data["total_time"] = float(raw.get("total_time", 0.0))
        merged = dict(DEFAULT_SETTINGS)
        merged.update(raw.get("settings", {}))
        self.data["settings"] = merged
        if version == 2:
            # v2 had one set of progress: it becomes Normal-mode progress
            self.data["modes"]["normal"] = {"unlocked": raw.get("unlocked", 1), "levels": raw.get("levels", {}),
                                            "completed": raw.get("game_completed", False)}
            self.dirty = True
        elif version == self.VERSION:
            self.data["difficulty"] = raw.get("difficulty")
            for mode in ("normal", "brutal"):
                self.data["modes"][mode].update(raw.get("modes", {}).get(mode, {}))
        else:
            self.dirty = True     # v1 or unknown: only lifetime deaths survive

    def save(self):
        """Write to a temp file first, then swap it in, so a crash can't corrupt the save."""
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp_path, self.path)
            self.dirty = False
        except OSError as err:
            print(f"[save] Could not write save file: {err}")

    def flush(self):
        if self.dirty:
            self.save()

    # -------------------------------------------------------------- settings
    @property
    def settings(self):
        return self.data["settings"]

    def set_setting(self, key, value):
        self.data["settings"][key] = value
        self.dirty = True

    # -------------------------------------------------------------- difficulty
    @property
    def difficulty(self):
        return self.data["difficulty"] or "normal"

    @property
    def difficulty_chosen(self):
        return self.data["difficulty"] is not None

    def set_difficulty(self, mode):
        self.data["difficulty"] = mode
        self.save()

    @property
    def mode(self):
        return self.data["modes"][self.difficulty]

    # -------------------------------------------------------------- progress (current difficulty)
    def level_stats(self, level_num, mode=None):
        levels = self.data["modes"][mode or self.difficulty]["levels"]
        stats = levels.setdefault(str(level_num), {})
        stats.setdefault("deaths", 0)
        stats.setdefault("best_time", None)
        stats.setdefault("best_deaths", None)
        stats.setdefault("completed", False)
        return stats

    def is_unlocked(self, level_num):
        return self.unlock_all or level_num <= self.mode["unlocked"]

    def highest_unlocked(self):
        if self.unlock_all:
            return self.level_count
        return min(self.mode["unlocked"], self.level_count)

    def record_death(self, level_num):
        self.data["total_deaths"] += 1
        self.level_stats(level_num)["deaths"] += 1
        self.dirty = True
        return self.data["total_deaths"]

    def add_play_time(self, seconds):
        self.data["total_time"] += seconds
        self.dirty = True

    def record_clear(self, level_num, clear_time, deaths):
        """Save a finished level. Returns (new best time?, new best deaths?)."""
        stats = self.level_stats(level_num)
        stats["completed"] = True
        new_time = stats["best_time"] is None or clear_time < stats["best_time"]
        new_deaths = stats["best_deaths"] is None or deaths < stats["best_deaths"]
        if new_time:
            stats["best_time"] = round(clear_time, 3)
        if new_deaths:
            stats["best_deaths"] = deaths
        if level_num + 1 > self.mode["unlocked"]:
            self.mode["unlocked"] = min(level_num + 1, self.level_count)
        if level_num == self.level_count:
            self.mode["completed"] = True
        self.save()
        return new_time, new_deaths

    def reset_progress(self):
        settings_copy = self.data["settings"]
        self.data = self._fresh_data()
        self.data["settings"] = settings_copy
        self.save()


# ------------------------------------------------------------------ camera
class Camera:
    """Follows the player (sideways, and up/down in tall levels) with look-ahead,
    and handles screen shake. Shake uses a 'trauma' value: hits add trauma,
    it fades out over time, and the shake is trauma squared so small hits stay subtle.
    """

    MAX_SHAKE = 22

    def __init__(self, level_width, level_height=VIRTUAL_H):
        self.level_width = level_width
        self.level_height = level_height
        self.x = 0.0
        self.y = float(max(0, level_height - VIRTUAL_H))
        self.look = 0.0
        self.trauma = 0.0
        self.time = random.uniform(0, 100)
        self.shake_scale = 1.0

    def _clamp_x(self, x):
        return clamp(x, 0, max(0, self.level_width - VIRTUAL_W))

    def _clamp_y(self, y):
        return clamp(y, 0, max(0, self.level_height - VIRTUAL_H))

    def _target_y(self, focus_y):
        # keep the player a bit below the middle so you can see what's coming from above
        return self._clamp_y(focus_y - VIRTUAL_H * 0.58)

    def snap(self, focus_x, focus_y=None):
        self.look = 0.0
        self.x = self._clamp_x(focus_x - VIRTUAL_W / 2)
        if focus_y is not None:
            self.y = self._target_y(focus_y)

    def update(self, dt, focus_x, facing, focus_y=None):
        self.time += dt
        self.look = damp(self.look, CAMERA_LOOKAHEAD * facing, 3.0, dt)
        target = self._clamp_x(focus_x + self.look - VIRTUAL_W / 2)
        self.x = damp(self.x, target, CAMERA_SMOOTH, dt)
        if focus_y is not None:
            self.y = damp(self.y, self._target_y(focus_y), CAMERA_SMOOTH * 0.9, dt)
        self.trauma = max(0.0, self.trauma - dt * 1.6)

    def add_trauma(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def shake_offset(self):
        """Smooth pseudo-random shake built from layered sine waves."""
        power = (self.trauma ** 2) * self.MAX_SHAKE * self.shake_scale
        if power < 0.3:
            return 0, 0
        t = self.time * 38
        ox = math.sin(t * 1.1) * 0.6 + math.sin(t * 2.3 + 1.7) * 0.4
        oy = math.sin(t * 1.7 + 4.2) * 0.6 + math.sin(t * 2.9 + 0.3) * 0.4
        return int(ox * power), int(oy * power)

    def view_x(self):
        return int(round(self.x))

    def view_y(self):
        return int(round(self.y))
