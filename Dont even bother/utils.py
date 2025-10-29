# I am adding comments for me to easily understand the codes

import pygame
import json
import random
import os
from settings import GAME_WIDTH

# This file contains small helper classes used by the game

class SaveManager:
    """Saves and loads simple game data to a JSON file."""
    def __init__(self, save_file="rage_save.json"):
        self.save_file = save_file  # Where we store the save data
        # Default save data when file is missing
        self.data = {
            "total_deaths": 0,      # How many times the player died in total
            "unlocked_level": 1,    # Highest level the player unlocked
            "rage_meter": 0,        # A fun number that grows when you die
            "unlock_all": True      # If True, we show all levels in the UI
        }
        self.load()  # Try to load from file (or keep defaults)

    def load(self):
        """Read the save file if it exists, otherwise keep defaults."""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    self.data.update(json.load(f))  # Merge file data into defaults
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read save file '{self.save_file}'. Using defaults.")
                self.save()  # Write a fresh default file
        # If unlock_all is True, pretend we unlocked many levels
        if self.data.get("unlock_all"):
            self.data["unlocked_level"] = 999

    def save(self):
        """Write the current data back to the JSON file."""
        try:
            with open(self.save_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            print(f"Error: Could not write to save file '{self.save_file}'.")

    def add_death(self):
        """Increase death count and slowly fill the rage meter."""
        self.data["total_deaths"] += 1
        self.data["rage_meter"] = min(100, self.data["rage_meter"] + 3)
        self.save()

    def unlock_level(self, level_num):
        """Update the highest unlocked level if we reached a new one."""
        if level_num > self.data["unlocked_level"]:
            self.data["unlocked_level"] = level_num
            self.save()

class Camera:
    """Keeps track of what part of the level we are looking at."""
    def __init__(self, level_width):
        self.x = 0  # Current left-edge position of the camera
        self.level_width = level_width  # Total width of the level
        self.shake_timer = 0  # How long the camera should shake
        self.shake_intensity = 0  # How strong the shake is
        self.view_width = GAME_WIDTH  # Width of the visible area

    def update(self, target_x, dt):
        """Follow the player smoothly and handle shake timing."""
        target_pos = target_x - self.view_width // 2  # Center camera on player
        # Keep camera inside the level bounds
        target_pos = max(0, min(target_pos, self.level_width - self.view_width))
        # Smoothly move the camera towards the target position
        self.x += (target_pos - self.x) * 10 * dt

        # Reduce shake time each frame
        if self.shake_timer > 0:
            self.shake_timer -= dt

    def shake(self, intensity=12, duration=0.35):
        """Start a camera shake for a short time."""
        self.shake_intensity = intensity
        self.shake_timer = duration

    def get_x(self):
        """Return the current camera X, with shake offset if active."""
        if self.shake_timer > 0:
            offset = random.randint(-int(self.shake_intensity), int(self.shake_intensity))
            return self.x + offset
        return self.x
