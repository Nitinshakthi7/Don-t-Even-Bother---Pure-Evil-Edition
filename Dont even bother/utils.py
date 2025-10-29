import pygame
import json
import random
import os
from settings import GAME_WIDTH

class SaveManager:
    def __init__(self, save_file="rage_save.json"):
        self.save_file = save_file
        self.data = {
            "total_deaths": 0,
            "unlocked_level": 1,
            "rage_meter": 0
        }
        self.load()

    def load(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read save file '{self.save_file}'. Using defaults.")
                self.save()

    def save(self):
        try:
            with open(self.save_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            print(f"Error: Could not write to save file '{self.save_file}'.")

    def add_death(self):
        self.data["total_deaths"] += 1
        self.data["rage_meter"] = min(100, self.data["rage_meter"] + 3)
        self.save()

    def unlock_level(self, level_num):
        if level_num > self.data["unlocked_level"]:
            self.data["unlocked_level"] = level_num
            self.save()

class Camera:
    def __init__(self, level_width):
        self.x = 0
        self.level_width = level_width
        self.shake_timer = 0
        self.shake_intensity = 0
        self.view_width = GAME_WIDTH

    def update(self, target_x, dt):
        target_pos = target_x - self.view_width // 2
        target_pos = max(0, min(target_pos, self.level_width - self.view_width))
        self.x += (target_pos - self.x) * 10 * dt

        if self.shake_timer > 0:
            self.shake_timer -= dt

    def shake(self, intensity=12, duration=0.35):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def get_x(self):
        if self.shake_timer > 0:
            offset = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            return self.x + offset
        return self.x
