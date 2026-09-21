# The web build used to declare numpy here so pygbag would fetch a wheel to
# synthesise the audio. That cost an 11MB download and a second and a half
# of maths before the game could start, which on a phone is most of the
# wait. The sounds are baked to files at build time instead - see
# dev_tools/prerender_audio.py.
# I am adding comments for me to easily understand the codes
# main.py - starts the game: sets up the window, loads everything, and runs
# the main loop (read input -> update the current scene -> draw -> repeat).
#
# Run it:            python main.py
# Handy flags:       --windowed        start in a window
#                    --level N         jump straight into level N (for testing)
#                    --unlock-all      every level unlocked (for testing)

import argparse
import asyncio
import time
import json
import os
import sys
import tempfile

import pygame

from settings import LOW_FX, WEB_BENCH, VIRTUAL_W, VIRTUAL_H, FPS_CAP, GAME_TITLE, GAME_SUBTITLE
from utils import SaveManager
from controls import Controls
from audio import AudioManager
from graphics import make_vignette, make_grain_frames
from campaign import LEVELS

WEB = sys.platform == "emscripten"   # running inside a browser
from scenes import SceneManager, SplashScene, GameScene, ActCardScene



def bench_primitives(screen):
    """Time the drawing primitives on the real display surface and print the
    result. Costs that are negligible on a desktop GPU are not negligible in
    WASM, and the only way to know the difference is to measure it here."""
    import pygame as pg
    from graphics import draw_text

    W, H = screen.get_size()
    opaque = pg.Surface((W, H)).convert()
    opaque.fill((30, 40, 60))
    alpha = pg.Surface((W, H), pg.SRCALPHA).convert_alpha()
    alpha.fill((30, 40, 60, 120))
    tile = pg.Surface((40, 40)).convert()
    tile.fill((200, 80, 90))
    tile_a = pg.Surface((40, 40), pg.SRCALPHA).convert_alpha()
    tile_a.fill((200, 80, 90, 160))
    font = pg.font.Font(None, 28)

    out = []

    def timed(label, fn, n):
        fn()                                  # warm up, ignore the first
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        ms = (time.perf_counter() - t0) * 1000.0 / n
        line = f"{label:<24}{ms:8.2f} ms"
        print("BENCH " + line)
        out.append(line)
        return ms

    print("BENCH ---- display:", screen.get_flags(), screen.get_bitsize(), "bpp", (W, H))
    timed("fullscreen fill", lambda: screen.fill((10, 10, 14)), 20)
    timed("fullscreen blit opaque", lambda: screen.blit(opaque, (0, 0)), 20)
    timed("fullscreen blit alpha", lambda: screen.blit(alpha, (0, 0)), 20)
    timed("100 small blits opaque", lambda: [screen.blit(tile, (i % 30 * 41, i // 30 * 41))
                                             for i in range(100)], 20)
    timed("100 small blits alpha", lambda: [screen.blit(tile_a, (i % 30 * 41, i // 30 * 41))
                                            for i in range(100)], 20)
    # candidate replacements for the full-screen alpha blit, which is the
    # single most expensive thing we do in a browser
    surf_alpha = pg.Surface((W, H)).convert()          # opaque, surface-level alpha
    surf_alpha.fill((0, 0, 0))
    surf_alpha.set_alpha(120)
    timed("fullscreen set_alpha blit", lambda: screen.blit(surf_alpha, (0, 0)), 20)
    timed("fullscreen fill MULT", lambda: screen.fill((120, 120, 120),
                                                      special_flags=pg.BLEND_RGB_MULT), 20)
    timed("fullscreen fill RGBA_MULT", lambda: screen.fill((120, 120, 120, 255),
                                                           special_flags=pg.BLEND_RGBA_MULT), 20)
    half = pg.Surface((W // 2, H), pg.SRCALPHA).convert_alpha()
    half.fill((0, 0, 0, 120))
    timed("half-screen blit alpha", lambda: screen.blit(half, (0, 0)), 20)
    timed("font.render one line", lambda: font.render("hello world", True, (255, 255, 255)), 20)
    timed("draw_text one line", lambda: draw_text(screen, "hello world", (100, 100), 20,
                                                  (255, 255, 255)), 20)
    timed("display.flip", lambda: pg.display.flip(), 20)
    print("BENCH ---- end")
    # pygbag sends print() to its own canvas terminal, which cannot be read
    # back. Hand the numbers to JS as well so they can be inspected directly.
    try:
        import platform as _pf
        _pf.window.DEB_BENCH = " | ".join(out)
    except Exception:
        pass
    return out



def _perf_requested():
    """True when the page was opened with ?perf - the only way in on a phone."""
    if not WEB:
        return False
    try:
        import platform as _pf
        return "perf" in str(_pf.window.location.search).lower()
    except Exception:
        return False


class Game:
    def __init__(self, windowed=False, unlock_all=False, start_level=None, save_path=None):
        self.levels = LEVELS
        self.save = SaveManager(len(self.levels), path=save_path, unlock_all=unlock_all)
        self.session_death_spite = 0   # dying only pays up to a cap each session
        if windowed:
            self.save.settings["fullscreen"] = False
        self.screen = None
        self._create_window(self.save.settings["fullscreen"])
        pygame.display.set_caption(f"{GAME_TITLE} - {GAME_SUBTITLE}")
        self.clock = pygame.time.Clock()
        self.running = True

        self.controls = Controls()
        self.audio = AudioManager(self.save.settings)
        # a full-screen translucent blit every frame; too dear in a browser
        self.vignette = None if LOW_FX else make_vignette(VIRTUAL_W, VIRTUAL_H)
        # a full-screen translucent blit costs ~35ms in a browser, every
        # frame, for an effect you can barely see. Not worth 3 fps.
        self.grain = None if LOW_FX else make_grain_frames()
        self.grain_index = 0
        # a frame-time readout, so "it lags" can become a number. F3 toggles it;
        # it starts on in the browser, where it is the only way to see inside.
        # F3 shows frame timings, and on the web which audio and save
        # backends came up. Off by default: players should see the game, not
        # the diagnostics. A phone has no F3, so adding ?perf to the address
        # turns it on there.
        self.show_perf = _perf_requested()
        self.perf = {"update": 0.0, "draw": 0.0, "fps": 0.0}
        self._perf_clock = 0.0
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
        # Never ask SDL for fullscreen in a browser: it tears down the WASM
        # runtime. A save carrying fullscreen=True would otherwise crash the
        # game on every load, with no way back in to turn it off.
        if WEB:
            fullscreen = False
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        for attempt in ({"flags": flags, "vsync": 1}, {"flags": flags}, {"flags": 0}):
            try:
                self.screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), **attempt)
                return
            except pygame.error:
                continue
        raise RuntimeError("Could not open a game window")

    @staticmethod
    def _browser_fullscreen(value):
        """Ask the page to go fullscreen, rather than SDL.

        Browsers only grant this from a real user gesture, and the game loop
        runs a tick after the keypress, so it may simply be refused - which is
        fine. What matters is that it fails quietly instead of taking the
        whole runtime down the way SDL's toggle does.
        """
        try:
            import platform as _pf
            doc = _pf.window.document
            if value:
                doc.documentElement.requestFullscreen()
            else:
                doc.exitFullscreen()
        except Exception as err:
            print(f"[display] browser refused fullscreen: {err}")

    def set_fullscreen(self, value):
        if WEB:
            self._browser_fullscreen(value)
            return
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

    def _draw_perf(self):
        from graphics import draw_text
        p = self.perf
        text = f"{p['fps']:4.0f} fps   update {p['update']:5.2f} ms   draw {p['draw']:5.2f} ms"
        draw_text(self.screen, text, (VIRTUAL_W // 2, 16), 20, (120, 255, 170), bold=True)
        if WEB:
            import audio as _audio
            from utils import browser_store
            where = "localStorage" if browser_store() is not None else "file (will not persist!)"
            draw_text(self.screen, f"audio: {_audio.STATUS}", (VIRTUAL_W // 2, 38), 18,
                      (120, 255, 170) if _audio.STATUS.startswith("ok") else (255, 120, 120))
            draw_text(self.screen, f"save: {where}", (VIRTUAL_W // 2, 58), 18, (120, 255, 170))
        for i, line in enumerate(getattr(self, "bench_lines", ())):
            draw_text(self.screen, line, (VIRTUAL_W // 2, 40 + i * 20), 18, (255, 220, 120))

    def stop_demo(self):
        self.running = False

    def quit(self):
        self.running = False

    # ------------------------------------------------------------ main loop
    async def run(self):
        if WEB_BENCH:
            self.bench_lines = bench_primitives(self.screen)
            self.bench_lines.insert(0, f"{self.screen.get_bitsize()}bpp flags={self.screen.get_flags()}")
        while self.running:
            dt = min(self.clock.tick(FPS_CAP) / 1000.0, 0.1)
            self.controls.begin_frame()
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    self.show_perf = not self.show_perf
                    continue
                elif event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or
                                                       (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
                    self.toggle_fullscreen()
                    continue
                self.controls.process_event(event)

            t_update = time.perf_counter()
            self.scenes.update(dt, events)
            t_draw = time.perf_counter()
            self.scenes.draw(self.screen)
            t_done = time.perf_counter()
            if self.save.settings["film_grain"] and self.grain:
                self.grain_index = (self.grain_index + 1) % (len(self.grain) * 2)
                self.screen.blit(self.grain[self.grain_index // 2], (0, 0))
            if self.show_perf:
                self._perf_clock += dt
                if self._perf_clock > 0.25:          # settle the numbers down
                    self._perf_clock = 0.0
                    self.perf = {"update": (t_draw - t_update) * 1000,
                                 "draw": (t_done - t_draw) * 1000,
                                 "fps": 1.0 / max(dt, 1e-6)}
                self._draw_perf()
            pygame.display.flip()
            # hand the frame back to the browser's event loop; on desktop this
            # costs nothing measurable and keeps one code path for both
            await asyncio.sleep(0)

            self.save_timer += dt
            if self.save_timer > 5.0:
                self.save_timer = 0.0
                self.save.flush()

        self.save.save()
        pygame.quit()


async def main():
    parser = argparse.ArgumentParser(description=f"{GAME_TITLE} - {GAME_SUBTITLE}")
    parser.add_argument("--windowed", action="store_true", help="start in a window instead of fullscreen")
    parser.add_argument("--level", type=int, help="jump straight into a level (1-10)")
    parser.add_argument("--unlock-all", action="store_true", help="unlock every level")
    parser.add_argument("--demo", action="store_true", help="watch the game play every level by itself")
    parser.add_argument("--brutal", action="store_true", help="with --demo: watch the Brutal runs")
    parser.add_argument("--from", dest="first", type=int, default=1, help="with --demo: start at this level")
    # a browser tab has no command line, and argparse would choke on its argv
    args = parser.parse_args([]) if WEB else parser.parse_args()
    if WEB:
        args.windowed = True          # the canvas is the window

    if sys.platform == "win32":
        # Crisp rendering on high-DPI Windows displays
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")   # smooth scaling
    # 512 samples is ~12ms of audio. That is fine natively, but in a browser
    # the audio callback shares the main thread with the game and cannot always
    # refill in time, and every underrun is an audible click. A bigger buffer
    # costs a little latency on sound effects and stops the crackling.
    pygame.mixer.pre_init(44100, -16, 2, 2048 if WEB else 512)
    pygame.init()
    if args.demo:
        # the demo uses a throwaway save so it never touches your real progress
        demo_save = os.path.join(tempfile.gettempdir(), "dont_even_bother_demo_save.json")
        if os.path.exists(demo_save):
            os.remove(demo_save)
        game = Game(windowed=args.windowed, unlock_all=True, save_path=demo_save)
        game.start_demo("brutal" if args.brutal else "normal", max(1, min(args.first, len(LEVELS))))
        await game.run()
        return
    start = args.level if args.level and 1 <= args.level <= len(LEVELS) else None
    await Game(windowed=args.windowed, unlock_all=args.unlock_all or bool(start),
               start_level=start).run()


if __name__ == "__main__":
    asyncio.run(main())
