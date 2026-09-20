# I am adding comments for me to easily understand the codes
# main.py - starts the game: sets up the window, loads everything, and runs
# the main loop (read input -> update the current scene -> draw -> repeat).
#
# Run it:            python main.py
# Handy flags:       --windowed        start in a window
#                    --level N         jump straight into level N (for testing)
#                    --unlock-all      every level unlocked (for testing)

import argparse
import json
import os
import sys
import tempfile

import pygame

from settings import VIRTUAL_W, VIRTUAL_H, FPS_CAP, GAME_TITLE, GAME_SUBTITLE
from utils import SaveManager
from controls import Controls
from audio import AudioManager
from graphics import make_vignette, make_grain_frames
from campaign import LEVELS
from scenes import SceneManager, SplashScene, GameScene, ActCardScene


class Game:
    def __init__(self, windowed=False, unlock_all=False, start_level=None, save_path=None):
        self.levels = LEVELS
        self.save = SaveManager(len(self.levels), path=save_path, unlock_all=unlock_all)
        if windowed:
            self.save.settings["fullscreen"] = False
        self.screen = None
        self._create_window(self.save.settings["fullscreen"])
        pygame.display.set_caption(f"{GAME_TITLE} - {GAME_SUBTITLE}")
        self.clock = pygame.time.Clock()
        self.running = True

        self.controls = Controls()
        self.audio = AudioManager(self.save.settings)
        self.vignette = make_vignette(VIRTUAL_W, VIRTUAL_H)
        self.grain = make_grain_frames()
        self.grain_index = 0
        self.demo = False
        self.markers = {}            # death markers per (difficulty, level), kept for the whole session
        self.session_deaths = 0
        self.save_timer = 0.0

        self.scenes = SceneManager(self)
        if start_level:
            self.scenes.switch(GameScene(self, start_level), instant=True)
        else:
            self.scenes.switch(SplashScene(self), instant=True)

    # ------------------------------------------------------------ window
    def _create_window(self, fullscreen):
        """pygame.SCALED draws our fixed 1280x720 canvas scaled to fit any
        screen, adds black bars when needed and fixes mouse coordinates for us."""
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        for attempt in ({"flags": flags, "vsync": 1}, {"flags": flags}, {"flags": 0}):
            try:
                self.screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), **attempt)
                return
            except pygame.error:
                continue
        raise RuntimeError("Could not open a game window")

    def set_fullscreen(self, value):
        if bool(value) != bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN):
            pygame.display.toggle_fullscreen()

    def toggle_fullscreen(self):
        value = not self.save.settings["fullscreen"]
        self.save.set_setting("fullscreen", value)
        self.set_fullscreen(value)

    # ------------------------------------------------------------ flow helpers
    def continue_level(self):
        """The first level you haven't beaten yet (or the last one)."""
        for n in range(1, len(self.levels) + 1):
            if not self.save.level_stats(n)["completed"]:
                return min(n, self.save.highest_unlocked())
        return len(self.levels)

    def start_level(self, number, card=True):
        """Start a level. The first level of each act gets a big title card first."""
        defn = self.levels[number - 1]
        first_of_act = number == 1 or self.levels[number - 2].act != defn.act
        if card and first_of_act:
            self.scenes.switch(ActCardScene(self, defn.act, number))
        elif self.demo:
            self.scenes.switch(GameScene(self, number, demo=self._demo_actions(number)))
        else:
            self.scenes.switch(GameScene(self, number))

    # ------------------------------------------------------------ autoplay demo
    def _demo_actions(self, number):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev_tools", "solutions",
                            self.save.difficulty, f"level_{number:02d}.json")
        with open(path, encoding="utf-8") as f:
            return [tuple(a) for a in json.load(f)["actions"]]

    def start_demo(self, difficulty, first_level=1):
        """Watch the game play itself through every level, using the solver's verified runs."""
        self.demo = True
        self.save.set_difficulty(difficulty)
        self.start_level(first_level)

    def stop_demo(self):
        self.running = False

    def quit(self):
        self.running = False

    # ------------------------------------------------------------ main loop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS_CAP) / 1000.0, 0.1)
            self.controls.begin_frame()
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or
                                                       (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
                    self.toggle_fullscreen()
                    continue
                self.controls.process_event(event)

            self.scenes.update(dt, events)
            self.scenes.draw(self.screen)
            if self.save.settings["film_grain"] and self.grain:
                self.grain_index = (self.grain_index + 1) % (len(self.grain) * 2)
                self.screen.blit(self.grain[self.grain_index // 2], (0, 0))
            pygame.display.flip()

            self.save_timer += dt
            if self.save_timer > 5.0:
                self.save_timer = 0.0
                self.save.flush()

        self.save.save()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=f"{GAME_TITLE} - {GAME_SUBTITLE}")
    parser.add_argument("--windowed", action="store_true", help="start in a window instead of fullscreen")
    parser.add_argument("--level", type=int, help="jump straight into a level (1-10)")
    parser.add_argument("--unlock-all", action="store_true", help="unlock every level")
    parser.add_argument("--demo", action="store_true", help="watch the game play every level by itself")
    parser.add_argument("--brutal", action="store_true", help="with --demo: watch the Brutal runs")
    parser.add_argument("--from", dest="first", type=int, default=1, help="with --demo: start at this level")
    args = parser.parse_args()

    if sys.platform == "win32":
        # Crisp rendering on high-DPI Windows displays
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")   # smooth scaling
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    if args.demo:
        # the demo uses a throwaway save so it never touches your real progress
        demo_save = os.path.join(tempfile.gettempdir(), "dont_even_bother_demo_save.json")
        if os.path.exists(demo_save):
            os.remove(demo_save)
        game = Game(windowed=args.windowed, unlock_all=True, save_path=demo_save)
        game.start_demo("brutal" if args.brutal else "normal", max(1, min(args.first, len(LEVELS))))
        game.run()
        return
    start = args.level if args.level and 1 <= args.level <= len(LEVELS) else None
    Game(windowed=args.windowed, unlock_all=args.unlock_all or bool(start), start_level=start).run()


if __name__ == "__main__":
    main()
