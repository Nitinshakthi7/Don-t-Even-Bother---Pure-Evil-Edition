# I am adding comments for me to easily understand the codes
# scenes.py - every screen of the game is a Scene (splash, title, level
# select, settings, gameplay, credits). The SceneManager swaps between them
# with a fade, and can stack one scene on top of another (settings over pause).

import math
import random

import pygame

from settings import (CURRENCY, VIRTUAL_W, VIRTUAL_H, FIXED_DT, MAX_STEPS_PER_FRAME, RESPAWN_DELAY, HITSTOP_TIME,
                      THEMES, GAME_TITLE, GAME_SUBTITLE, STUDIO_NAME, DEVELOPER_NAME, VERSION, PAPER, MUTED, DIM, INK,
                      WHITE, BLOOD, DARK_BLOOD, EMBER, GOLD, TOXIC, PLAYER_BODY, PLAYER_SCARF,
                      TAUNTS_GENERAL, TAUNTS_BY_CAUSE, MILESTONES, RANK_COLOURS, MAX_DEATH_MARKERS, NIGHT,
                      SPOT_TAUNTS, MODE_TAUNTS, RETURN_LINES, DIFFICULTIES, ACTS,
                      NAME_TAUNTS, NAME_TAUNT_CHANCE, MAX_NAME, LOW_FX)
from graphics import (draw_text, render_text, panel, dim, draw_skull, draw_lock, draw_clock, Background,
                      glow_circle, fast)
from particles import ParticleSystem, AmbientField
from renderer import WorldRenderer
from ui import Menu, MenuItem
from utils import Camera, format_time, rank_for_deaths, ease_out_cubic, ease_out_back, clamp, damp, lerp_colour
from world import World
import cosmetics
import achievements
import ghosts
from economy import clear_payout, total_of, death_payout
from settings import PAYOUT
from player import wants_jump


# ================================================================== framework
class Scene:
    music = None
    overlay = False          # overlays are drawn on top of the scene below them
    cursor = True

    def __init__(self, game):
        self.game = game
        self.time = 0.0

    def enter(self):
        if self.music:
            self.game.audio.play_music(self.music)
        pygame.mouse.set_visible(self.cursor)

    def update(self, dt, events):
        self.time += dt

    def draw(self, surface):
        pass


class SceneManager:
    FADE_TIME = 0.3

    def __init__(self, game):
        self.game = game
        self.stack = []
        self.fade = 0.0
        self.fade_dir = 0
        self.pending = None

    @property
    def top(self):
        return self.stack[-1] if self.stack else None

    def switch(self, scene, instant=False):
        if instant or not self.stack:
            self.stack = [scene]
            scene.enter()
            return
        if self.fade_dir == 1:
            return
        self.pending = scene
        self.fade_dir = 1

    def push(self, scene):
        self.stack.append(scene)
        scene.enter()

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.stack[-1].enter()

    def update(self, dt, events):
        if self.fade_dir == 1:
            self.fade = min(1.0, self.fade + dt / self.FADE_TIME)
            if self.fade >= 1.0:
                self.stack = [self.pending]
                self.pending.enter()
                self.pending = None
                self.fade_dir = -1
            self.game.controls.pressed.clear()
            events = []
        elif self.fade_dir == -1:
            self.fade = max(0.0, self.fade - dt / self.FADE_TIME)
            if self.fade <= 0:
                self.fade_dir = 0
        if self.top:
            self.top.update(dt, events)

    def draw(self, surface):
        if self.top and self.top.overlay and len(self.stack) > 1:
            self.stack[-2].draw(surface)
        if self.top:
            self.top.draw(surface)
        if self.fade > 0:
            dim(surface, int(255 * ease_out_cubic(self.fade)))


def any_key(events):
    return any(e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN) for e in events)


# ================================================================== splash
class SplashScene(Scene):
    """Content warning, then the studio logo. Any key skips."""

    WARNING_TIME = 3.4
    LOGO_TIME = 3.0

    def __init__(self, game):
        super().__init__(game)
        self.phase = 0
        self.phase_time = 0.0
        self.drips = []

    def update(self, dt, events):
        super().update(dt, events)
        self.phase_time += dt
        if any_key(events):
            self.phase_time = 99
        limit = self.WARNING_TIME if self.phase == 0 else self.LOGO_TIME
        if self.phase_time >= limit:
            self.phase += 1
            self.phase_time = 0.0
            if self.phase == 1:
                self.game.audio.play("splat", 0.8)
            if self.phase >= 2:
                self.game.scenes.switch(TitleScene(self.game))

    def _alpha(self, limit):
        t = self.phase_time
        a = min(1.0, t / 0.5, max(0.0, (limit - t) / 0.5))
        return int(255 * max(0.0, a))

    def draw(self, surface):
        surface.fill((0, 0, 0))
        cx, cy = VIRTUAL_W // 2, VIRTUAL_H // 2
        if self.phase == 0:
            a = self._alpha(self.WARNING_TIME)
            draw_text(surface, "WARNING", (cx, cy - 120), 54, BLOOD, "display", alpha=a)
            lines = ["This game contains flashing lights, screen shake,",
                     "invisible spikes and a narrator who does not like you.",
                     "",
                     "Screen shake and film grain can be turned down in Settings.",
                     "Headphones recommended. Patience required."]
            for i, line in enumerate(lines):
                draw_text(surface, line, (cx, cy - 40 + i * 36), 26, PAPER if i < 2 else MUTED, alpha=a)
        elif self.phase == 1:
            a = self._alpha(self.LOGO_TIME)
            t = self.phase_time
            logo = draw_text(surface, STUDIO_NAME, (cx, cy - 10), 76, PAPER, "display", alpha=a)
            # a drop of blood falls from the logo
            drop_y = logo.bottom - 6 + min(1.0, max(0.0, t - 0.7) / 0.9) ** 2 * 120
            if t > 0.5 and a > 0:
                pygame.draw.circle(surface, BLOOD, (logo.right - 26, int(drop_y)), 7)
                pygame.draw.polygon(surface, BLOOD, [(logo.right - 33, int(drop_y) - 1),
                                                     (logo.right - 26, int(drop_y) - 16),
                                                     (logo.right - 19, int(drop_y) - 1)])
            draw_text(surface, "presents", (cx, cy + 60), 24, MUTED, alpha=a)


# ================================================================== title
# ================================================================== title backdrop
def _ridge_surface(colour, rim, height=190, seed=3):
    """A near-black foreground ridge with spikes along its crest.

    It sits at the bottom of the title screen so the scene has a foreground,
    and it is the game in one shape: ground, and something sharp on it.
    """
    rng = random.Random(seed)
    surf = pygame.Surface((VIRTUAL_W, height), pygame.SRCALPHA)
    crest = []
    for x in range(0, VIRTUAL_W + 1, 10):
        y = 70 - math.sin(x / VIRTUAL_W * math.tau * 1.5) * 22 - math.sin(x / VIRTUAL_W * math.tau * 5) * 8
        crest.append((x, y))
    pygame.draw.polygon(surf, colour, [(0, height)] + crest + [(VIRTUAL_W, height)])
    for x, y in crest[::4]:
        h = rng.randint(26, 48)
        w = rng.randint(10, 15)
        pygame.draw.polygon(surf, colour, [(x - w, y + 3), (x, y - h), (x + w, y + 3)])
        pygame.draw.line(surf, rim, (x, y - h), (x + w, y + 3), 2)
        pygame.draw.line(surf, rim, (x, y - h), (x - w, y + 3), 1)
    pygame.draw.lines(surf, rim, False, crest, 2)
    return fast(surf)


def _far_ridge(colour, height=150, seed=8):
    """A softer ridge behind the sharp one, so the foreground has depth."""
    surf = pygame.Surface((VIRTUAL_W, height), pygame.SRCALPHA)
    pts = [(0, height)]
    for x in range(0, VIRTUAL_W + 1, 12):
        y = 74 - math.sin(x / VIRTUAL_W * math.tau * 2.2 + 1.1) * 26
        pts.append((x, y))
    pts.append((VIRTUAL_W, height))
    pygame.draw.polygon(surf, colour, pts)
    return fast(surf)


def _left_scrim(width=760, alpha=170):
    """A soft dark wash down the left, so the menu always has something to sit on."""
    surf = pygame.Surface((width, VIRTUAL_H), pygame.SRCALPHA)
    for x in range(width):
        a = int(alpha * (1 - x / width) ** 1.6)
        surf.fill((6, 4, 10, a), (x, 0, 1, VIRTUAL_H))
    return fast(surf)


def draw_character_display(surface, skin, centre, scale, t, glow=True, bright=False):
    """The equipped skin, idling, big enough to be worth having earned."""
    bob = math.sin(t * 2.0) * 5
    cx, cy = centre[0], centre[1] + bob
    if glow:
        pulse = 18 * math.sin(t * 2.4) if bright else 0
        halo = glow_circle(170, skin.scarf, int((96 if bright else 52) + pulse))
        surface.blit(halo, (cx - 170, cy - 170))
    # no ground shadow: without a frame there is nothing for it to fall on
    draw_skin_preview(surface, skin, (cx, cy), scale)


class TitleScene(Scene):
    music = "menu"

    # the left column everything hangs off
    LEFT = 96
    PANEL = pygame.Rect(902, 150, 300, 366)

    def __init__(self, game):
        super().__init__(game)
        self.bg = Background(THEMES["abyss"], seed=5)
        self.embers = AmbientField(VIRTUAL_W, VIRTUAL_H, (255, 110, 70), count=70, rising=True, seed=9)
        # light enough to read as a shape against the dark sky, dark enough to
        # still be a silhouette
        self.ridge = _ridge_surface((27, 18, 31), (86, 46, 56))
        self.far_ridge = _far_ridge((16, 11, 19))
        self.scrim = _left_scrim()
        self._baked = None            # LOW_FX: the whole static backdrop, flattened
        self.cam = 0.0
        save = game.save
        has_progress = save.mode["unlocked"] > 1 or save.data["total_deaths"] > 0
        items = [MenuItem("NEW GAME", "new")]
        if has_progress:
            items.append(MenuItem("CONTINUE", "play"))
        items += [
            MenuItem("PLAY", "play_menu"),
            MenuItem("SETTINGS", "settings"),
            MenuItem("CREDITS", "credits"),
            MenuItem("QUIT", "quit"),
        ]
        self.has_progress = has_progress
        rows = len(items)
        self.menu = Menu(items, center=(self.LEFT + 210, 300 + (rows - 1) * 25), spacing=50,
                         width=420, size=34, align="split")
        self.confirm = None
        self.glitch = 0.0
        self.next_glitch = 2.5
        self.focus = "menu"        # or "character", the skins button on the right

    def _open_quit_dialog(self):
        deaths = self.game.save.data["total_deaths"]
        if deaths < 10:
            msg = f"Leaving already? {deaths} deaths is barely a warm-up."
        else:
            msg = f"{deaths} deaths and you're giving up? Fair, honestly."
        self.confirm = (msg, Menu([MenuItem("STAY", "stay"), MenuItem("QUIT ANYWAY", "quit")],
                                  center=(VIRTUAL_W // 2, VIRTUAL_H // 2 + 60), spacing=60, width=340, size=32))

    def update(self, dt, events):
        super().update(dt, events)
        self.cam += dt * 24
        self.embers.update(dt)
        self.next_glitch -= dt
        self.glitch = max(0.0, self.glitch - dt)
        if self.next_glitch <= 0:
            self.glitch = 0.18
            self.next_glitch = random.uniform(2.5, 5.0)

        controls = self.game.controls
        audio = self.game.audio
        if self.confirm:
            action = self.confirm[1].update(dt, controls, events, audio)
            if action == "stay" or controls.consume("back"):
                self.confirm = None
            elif action == "quit":
                self.game.running = False
            return

        # the character on the right IS the skins button
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                where = "character" if self.PANEL.collidepoint(e.pos) else None
                if where is None and any(item.rect.collidepoint(e.pos) for item in self.menu.items):
                    where = "menu"
                if where and where != self.focus:
                    self.focus = where
                    audio.play("ui_move", 0.6)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.PANEL.collidepoint(e.pos):
                audio.play("ui_select")
                self.game.scenes.switch(SkinsScene(self.game))
                return

        if self.focus == "character":
            if controls.consume("confirm"):
                audio.play("ui_select")
                self.game.scenes.switch(SkinsScene(self.game))
                return
            if controls.consume("left") or controls.consume("up") or controls.consume("down"):
                self.focus = "menu"
                audio.play("ui_move")
            elif controls.consume("back"):
                self._open_quit_dialog()
            return

        if controls.consume("right"):
            self.focus = "character"
            audio.play("ui_move")
            return

        action = self.menu.update(dt, controls, events, audio)
        if action == "play":
            self.game.start_level(self.game.continue_level())
        elif action == "new":
            self.game.scenes.switch(NewGameScene(self.game) if self.has_progress
                                    else NameEntryScene(self.game))
        elif action == "play_menu":
            self.game.scenes.switch(PlayScene(self.game))
        elif action == "skins":
            self.game.scenes.switch(SkinsScene(self.game))
        elif action == "settings":
            self.game.scenes.push(SettingsScene(self.game))
        elif action == "credits":
            self.game.scenes.switch(CreditsScene(self.game))
        elif action == "quit":
            self._open_quit_dialog()

    def draw_title(self, surface, y):
        pulse = 1.0 + 0.012 * math.sin(self.time * 2.2)
        glow = glow_circle(240, BLOOD, 60)
        surface.blit(glow, (self.LEFT + 120 - 240, y - 240))
        if self.glitch > 0:
            for offset, colour in ((-6, (255, 30, 60)), (6, (40, 220, 255))):
                draw_text(surface, GAME_TITLE, (self.LEFT + offset, y + random.randint(-3, 3)), 84, colour,
                          "display", alpha=150, scale=pulse, anchor="midleft")
        draw_text(surface, GAME_TITLE, (self.LEFT, y), 84, PAPER, "display", shadow=DARK_BLOOD,
                  scale=pulse, anchor="midleft")
        draw_text(surface, "  ".join(GAME_SUBTITLE), (self.LEFT + 4, y + 58), 21, BLOOD, "body",
                  bold=True, anchor="midleft")

    def draw_character(self, surface):
        save = self.game.save
        skin = cosmetics.equipped(save)
        selected = self.focus == "character"
        # No frame around this: the character stands in the same scene the menu
        # does. PANEL is only the click target.
        box = self.PANEL
        draw_text(surface, "WEARING", (box.centerx, box.top + 30), 16, MUTED, bold=True)
        draw_character_display(surface, skin, (box.centerx, box.top + 186), 4.6, self.time,
                               glow=True, bright=selected)
        draw_text(surface, skin.name, (box.centerx, box.bottom - 64), 28, PAPER if selected else MUTED,
                  "display")
        owned = len(cosmetics.unlocked_ids(save))
        draw_text(surface, f"{owned} of {len(cosmetics.SKINS)} skins", (box.centerx, box.bottom - 32), 17,
                  MUTED, bold=True)
        draw_text(surface, "SKINS", (box.centerx, box.bottom + 16), 30, GOLD if selected else MUTED,
                  "display")
        if not selected:
            bob = math.sin(self.time * 4) * 2
            draw_text(surface, "\u2192", (box.left - 30 + bob, box.centery), 30, DIM, "display")
        if selected:
            pygame.draw.line(surface, GOLD, (box.centerx - 52, box.bottom + 36),
                             (box.centerx + 52, box.bottom + 36), 2)
        if save.spite:
            draw_text(surface, f"{save.spite} {CURRENCY}", (box.centerx, box.bottom + 60), 19,
                      GOLD, bold=True)

    def _bake_backdrop(self, size):
        """Flatten every static layer of the backdrop into one opaque image.

        A full-screen translucent blit costs about 35ms in a browser against
        0.6ms for an opaque one, and this screen used to stack four of them
        every frame. None of them move, so they can all be painted once.
        """
        canvas = pygame.Surface(size)
        self.bg.draw(canvas, self.cam)
        dim(canvas, 70)
        canvas.blit(self.far_ridge, (0, VIRTUAL_H - self.far_ridge.get_height() - 26))
        canvas.blit(self.ridge, (0, VIRTUAL_H - self.ridge.get_height()))
        canvas.blit(self.scrim, (0, 0))
        return canvas.convert()

    def draw(self, surface):
        if LOW_FX:
            if self._baked is None:
                self._baked = self._bake_backdrop(surface.get_size())
            surface.blit(self._baked, (0, 0))
            # the embers still move, so they go on top of the flattened layers
            self.embers.draw(surface, self.cam, 0.5)
        else:
            self.bg.draw(surface, self.cam)
            self.embers.draw(surface, self.cam, 0.5)
            dim(surface, 70)
            surface.blit(self.far_ridge, (0, VIRTUAL_H - self.far_ridge.get_height() - 26))
            surface.blit(self.ridge, (0, VIRTUAL_H - self.ridge.get_height()))
            surface.blit(self.scrim, (0, 0))
            if self.game.vignette:
                surface.blit(self.game.vignette, (0, 0))
        self.draw_title(surface, 168)
        if self.confirm:
            self.menu.draw(surface, alpha=90)
            dim(surface, 170)
            box = pygame.Rect(0, 0, 760, 280)
            box.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 + 10)
            panel(surface, box)
            draw_text(surface, self.confirm[0], (VIRTUAL_W // 2, box.top + 60), 28, PAPER)
            self.confirm[1].draw(surface)
            return
        self.menu.draw(surface, show_cursor=self.focus == "menu")
        self.draw_character(surface)
        deaths = self.game.save.data["total_deaths"]
        draw_skull(surface, (40, VIRTUAL_H - 38), 26)
        name = self.game.save.player_name
        label = f"{name}  ·  {deaths} lifetime deaths" if name else f"{deaths} lifetime deaths"
        draw_text(surface, label, (64, VIRTUAL_H - 38), 22, PAPER, anchor="midleft")
        draw_text(surface, f"v{VERSION}  |  {STUDIO_NAME}", (VIRTUAL_W - 30, VIRTUAL_H - 38), 20, MUTED,
                  anchor="midright")


# ================================================================== difficulty choice
class DifficultyScene(Scene):
    """The ego trap. Normal is right there... if you can live with yourself."""

    music = "menu"
    NORMAL_LINES = ["Really? Normal?", "Your chat is typing 'L' right now.", "Sure. Pick the baby mode.",
                    "Nobody's watching. (Everyone's watching.)", "Mum said you could pick Normal?"]
    BRUTAL_LINES = ["That's the spirit.", "Finally, someone with a spine.", "You won't last ten minutes.",
                    "No checkpoints. No mercy. Good.", "Bold. Stupid, but bold."]
    STORY_LINES = ["Not yet. Suffer without context for now.",
                   "A story? For you? It's being written.",
                   "Locked. Even the narrator hasn't read it.",
                   "Soon. Assuming you survive the other two."]

    def __init__(self, game, from_title=False, start_at=None):
        super().__init__(game)
        self.from_title = from_title
        self.start_at = start_at
        self.bg = Background(THEMES["abyss"], seed=31)
        self.embers = AmbientField(VIRTUAL_W, VIRTUAL_H, (255, 90, 60), count=80, seed=12)
        self.choice = 1 if not game.save.difficulty_chosen else (1 if game.save.difficulty == "brutal" else 0)
        self.cards = [pygame.Rect(55, 210, 360, 330), pygame.Rect(435, 175, 430, 400),
                      pygame.Rect(890, 215, 330, 330)]           # the third one is Story: locked
        self.anim = [0.0, 0.0, 0.0]
        self.line = random.choice(self.BRUTAL_LINES)
        self.confirm = None          # second chance when picking Normal
        self.flash = 0.0

    def _pick_line(self):
        pool = (self.NORMAL_LINES, self.BRUTAL_LINES, self.STORY_LINES)[self.choice]
        self.line = random.choice(pool)

    def _commit(self, mode):
        save = self.game.save
        save.set_difficulty(mode)
        audio = self.game.audio
        audio.play("slam" if mode == "brutal" else "sad", 0.8)
        if self.from_title:
            self.game.scenes.switch(TitleScene(self.game))
        else:
            self.game.start_level(self.start_at or self.game.continue_level())

    def update(self, dt, events):
        super().update(dt, events)
        self.embers.update(dt)
        self.flash = max(0.0, self.flash - dt * 2)
        controls, audio = self.game.controls, self.game.audio
        if self.confirm:
            action = self.confirm.update(dt, controls, events, audio)
            if action == "normal":
                self._commit("normal")
            elif action == "brutal":
                self.confirm = None
                self.choice = 1
                self.flash = 1.0
                self._commit("brutal")
            elif controls.consume("back"):
                self.confirm = None
            return
        old = self.choice
        if controls.consume("left"):
            self.choice = max(0, self.choice - 1)
        if controls.consume("right"):
            self.choice = min(len(self.cards) - 1, self.choice + 1)
        chosen = None
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                for i, card in enumerate(self.cards):
                    if card.collidepoint(e.pos):
                        self.choice = i
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, card in enumerate(self.cards):
                    if card.collidepoint(e.pos):
                        self.choice = i
                        chosen = i
        if old != self.choice:
            audio.play("ui_move")
            self._pick_line()
        if controls.consume("confirm"):
            chosen = self.choice
        if chosen == 2:
            audio.play("sad", 0.7)         # Story mode is not here yet
            self.line = random.choice(self.STORY_LINES)
        elif chosen == 1:
            self._commit("brutal")
        elif chosen == 0:
            audio.play("troll")
            self.confirm = Menu([MenuItem("FINE. BRUTAL.", "brutal"), MenuItem("I'M SCARED (NORMAL)", "normal")],
                                center=(VIRTUAL_W // 2, 470), spacing=62, width=460, size=32)
        if controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))
        for i in range(len(self.cards)):
            self.anim[i] = damp(self.anim[i], 1.0 if i == self.choice else 0.0, 12, dt)

    def draw(self, surface):
        self.bg.draw(surface, self.time * 12)
        self.embers.draw(surface, self.time * 12)
        dim(surface, 120)
        draw_text(surface, "CHOOSE YOUR SUFFERING", (VIRTUAL_W // 2, 86), 60, PAPER, "display", shadow=INK)
        # --- NORMAL: small, grey, a bit embarrassing
        a = self.anim[0]
        r = self.cards[0].inflate(int(12 * a), int(12 * a))
        panel(surface, r, fill=(20, 18, 26, 230), border=(255, 255, 255, 60 if a > 0.5 else 25))
        draw_text(surface, "NORMAL", (r.centerx, r.y + 60), 48, MUTED, "display")
        for i, text in enumerate(["Checkpoints.", "Forgiving jumps.", "For people who want to", "see the ending."]):
            draw_text(surface, text, (r.centerx, r.y + 130 + i * 34), 24, MUTED)
        draw_text(surface, "(nobody will judge you. we will.)", (r.centerx, r.bottom - 36), 18, DIM, bold=True)
        # --- BRUTAL: big, red, pulsing
        a = self.anim[1]
        pulse = 0.5 + 0.5 * math.sin(self.time * 4)
        r = self.cards[1].inflate(int(16 * a), int(16 * a))
        surface.blit(glow_circle(300, BLOOD, int(60 + 50 * pulse)), (r.centerx - 300, r.centery - 300))
        panel(surface, r, fill=(40, 6, 14, 240), border=(*BLOOD, 255), width=4)
        draw_text(surface, "I DARE YOU", (r.centerx, r.y + 34), 20, GOLD, bold=True)
        draw_text(surface, "BRUTAL", (r.centerx, r.y + 92), 76, BLOOD, "display", shadow=INK,
                  scale=1.0 + 0.03 * pulse)
        for i, text in enumerate(["No checkpoints. Anywhere.", "Faster saws. Faster floors.", "Extra traps in every level.",
                                  "The way it was meant to be suffered."]):
            draw_text(surface, text, (r.centerx, r.y + 175 + i * 36), 25, PAPER if i < 3 else EMBER)
        draw_text(surface, "Only 1% of players will finish this.", (r.centerx, r.bottom - 40), 18, GOLD, bold=True)
        # --- STORY: locked, for now
        a = self.anim[2]
        r = self.cards[2].inflate(int(10 * a), int(10 * a))
        panel(surface, r, fill=(16, 16, 24, 230), border=(*GOLD, 90 if a > 0.5 else 35), width=2)
        draw_text(surface, "STORY", (r.centerx, r.y + 52), 44, MUTED, "display")
        draw_text(surface, "MODE", (r.centerx, r.y + 96), 44, MUTED, "display")
        badge = pygame.Rect(0, 0, r.width - 60, 40)
        badge.center = (r.centerx, r.y + 165)
        panel(surface, badge, fill=(60, 45, 10, 220), border=(*GOLD, 160), width=2)
        draw_text(surface, "COMING SOON", badge.center, 22, GOLD, bold=True)
        for i, text in enumerate(["Who are you?", "Why is the door lying?", "Who built this place?"]):
            draw_text(surface, text, (r.centerx, r.y + 212 + i * 30), 21, DIM)
        draw_text(surface, "being written", (r.centerx, r.bottom - 32), 17, DIM, bold=True)
        # narrator reacts to what you're hovering
        draw_text(surface, self.line, (VIRTUAL_W // 2, 640), 28, BLOOD if self.choice == 0 else GOLD, bold=True)
        draw_text(surface, "Progress is saved separately for each mode.", (VIRTUAL_W // 2, 690), 16, DIM, bold=True)
        if self.confirm:
            dim(surface, 190)
            box = pygame.Rect(0, 0, 720, 330)
            box.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 + 20)
            panel(surface, box, fill=(14, 10, 20, 252), border=(*BLOOD, 200), width=3)
            draw_text(surface, "Are you sure?", (VIRTUAL_W // 2, box.top + 56), 44, PAPER, "display")
            draw_text(surface, "Real players pick Brutal. Just saying.", (VIRTUAL_W // 2, box.top + 110), 26, MUTED)
            self.confirm.draw(surface)
        if self.flash > 0:
            dim(surface, int(200 * self.flash), BLOOD)


# ================================================================== skins
def draw_skin_preview(surface, skin, center, scale=1.0, alpha=255):
    """A stand-in for the player, drawn by the same code that draws the real one."""
    w, h = int(26 * scale), int(34 * scale)
    pad = int(18 * scale)
    layer = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    inner = pygame.Rect(pad, pad, w, h)
    # a stub of scarf, since the real one trails behind a moving player
    pygame.draw.rect(layer, skin.scarf, (inner.x - int(7 * scale), inner.y + int(h * 0.5) + 1,
                                         int(8 * scale), max(2, int(4 * scale))))
    cosmetics.draw_body(layer, skin, inner)
    if alpha < 255:
        layer.set_alpha(alpha)
    surface.blit(layer, (center[0] - layer.get_width() // 2, center[1] - layer.get_height() // 2))


class SkinsScene(Scene):
    """Pick what you die in. Nothing on this screen changes how the game plays."""

    music = "menu"
    COLS = 7

    def __init__(self, game):
        super().__init__(game)
        self.bg = Background(THEMES["abyss"], seed=44)
        self.skins = list(cosmetics.SKINS)
        worn = cosmetics.equipped(game.save).id
        self.index = next((i for i, s in enumerate(self.skins) if s.id == worn), 0)
        self.anims = {}
        self.flash = 0.0
        self.note = None            # [text, colour, seconds left]
        self.page = "skins"         # the other page is "awards"

    def _layout(self):
        cards = []
        for i in range(len(self.skins)):
            col, row = i % self.COLS, i // self.COLS
            cards.append(pygame.Rect(32 + col * 176, 178 + row * 190, 160, 170))
        return cards

    def _say(self, text, colour):
        self.note = [text, colour, 2.4]

    def _choose(self, audio):
        save, skin = self.game.save, self.skins[self.index]
        if cosmetics.is_unlocked(save, skin):
            if cosmetics.equipped(save).id == skin.id:
                audio.play("ui_move")
                return
            cosmetics.equip(save, skin.id)
            audio.play("ui_select")
            self.flash = 1.0
            self._say(skin.name + " EQUIPPED", TOXIC)
        elif skin.cost:
            if cosmetics.buy(save, skin):
                audio.play("checkpoint")
                cosmetics.equip(save, skin.id)
                self.flash = 1.0
                self._say("BOUGHT " + skin.name, GOLD)
            else:
                audio.play("bump")
                self._say(f"{skin.cost - save.spite} MORE {CURRENCY} NEEDED", BLOOD)
        else:
            audio.play("bump")
            self._say(skin.how.upper(), MUTED)

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.note:
            self.note[2] -= dt
            if self.note[2] <= 0:
                self.note = None
        old = self.index
        if controls.consume("left"):
            self.index = max(0, self.index - 1)
        if controls.consume("right"):
            self.index = min(len(self.skins) - 1, self.index + 1)
        if controls.consume("up"):
            self.index = max(0, self.index - self.COLS)
        if controls.consume("down"):
            self.index = min(len(self.skins) - 1, self.index + self.COLS)
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_TAB:
                self.page = "awards" if self.page == "skins" else "skins"
                audio.play("ui_move")
        if self.page == "awards":
            if controls.consume("back"):
                audio.play("ui_back")
                self.game.scenes.switch(TitleScene(self.game))
            return
        cards = self._layout()
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(cards):
                    if rect.collidepoint(e.pos):
                        self.index = i
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, rect in enumerate(cards):
                    if rect.collidepoint(e.pos):
                        self.index = i
                        self._choose(audio)
        if old != self.index:
            audio.play("ui_move")
        if controls.consume("confirm"):
            self._choose(audio)
        if controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))
        for i in range(len(self.skins)):
            self.anims[i] = damp(self.anims.get(i, 0.0), 1.0 if i == self.index else 0.0, 14, dt)

    def _draw_tabs(self, surface):
        for i, (name, key) in enumerate((("SKINS", "skins"), ("AWARDS", "awards"))):
            x = VIRTUAL_W // 2 + (-110 if i == 0 else 110)
            live = self.page == key
            draw_text(surface, name, (x, 56), 40 if live else 32, PAPER if live else DIM, "display",
                      shadow=INK if live else None)
        draw_text(surface, "TAB  switch", (VIRTUAL_W // 2, 92), 15, DIM, bold=True)

    def _draw_awards(self, surface):
        save = self.game.save
        done, total = achievements.progress(save, len(self.game.levels))
        draw_text(surface, f"{done} of {total} earned", (VIRTUAL_W // 2, 124), 22, GOLD, bold=True)
        for i, award in enumerate(achievements.ACHIEVEMENTS):
            col, row = i % 2, i // 2
            r = pygame.Rect(40 + col * 610, 156 + row * 88, 590, 76)
            got = achievements.has(save, award.id)
            panel(surface, r, fill=(22, 18, 30, 230) if got else (13, 11, 17, 230),
                  border=(*GOLD, 180) if got else (255, 255, 255, 30), width=2)
            if award.skin:
                draw_skin_preview(surface, cosmetics.get(award.skin), (r.left + 46, r.centery), 1.1,
                                  255 if got else 45)
            else:
                draw_skull(surface, (r.left + 46, r.centery), 22 if got else 20,
                           PAPER if got else DIM)
            draw_text(surface, award.name, (r.left + 86, r.top + 26), 24, PAPER if got else MUTED,
                      "display", anchor="midleft")
            draw_text(surface, award.description, (r.left + 86, r.top + 52), 17, MUTED if got else DIM,
                      anchor="midleft")
            if got:
                draw_text(surface, "EARNED", (r.right - 20, r.centery), 16, TOXIC, bold=True,
                          anchor="midright")
            else:
                draw_lock(surface, (r.right - 34, r.centery), 18, DIM)

    def draw(self, surface):
        self.bg.draw(surface, self.time * 12)
        dim(surface, 160)
        save = self.game.save
        self._draw_tabs(surface)
        if self.page == "awards":
            self._draw_awards(surface)
            draw_text(surface, "TAB  skins     ESC  back", (VIRTUAL_W // 2, VIRTUAL_H - 38), 18, DIM, bold=True)
            return
        draw_text(surface, f"{save.spite}  {CURRENCY}", (VIRTUAL_W // 2, 124), 24, GOLD, bold=True)
        worn = cosmetics.equipped(save).id
        for i, (skin, r0) in enumerate(zip(self.skins, self._layout())):
            a = self.anims.get(i, 0.0)
            r = r0.inflate(int(12 * a), int(12 * a)).move(0, int(-5 * a))
            owned = cosmetics.is_unlocked(save, skin)
            border = (*GOLD, 220) if i == self.index else (255, 255, 255, 40)
            panel(surface, r, fill=(22, 18, 30, 235) if owned else (13, 11, 17, 235),
                  border=border, width=3 if i == self.index else 2)
            draw_skin_preview(surface, skin, (r.centerx, r.y + 56), 1.35, 255 if owned else 45)
            if not owned:
                draw_lock(surface, (r.centerx, r.y + 56), 20, DIM)
            draw_text(surface, skin.name, (r.centerx, r.y + 112), 16, PAPER if owned else MUTED, bold=True)
            if skin.id == worn:
                draw_text(surface, "EQUIPPED", (r.centerx, r.y + 138), 15, TOXIC, bold=True)
            elif owned:
                draw_text(surface, "OWNED", (r.centerx, r.y + 138), 15, MUTED, bold=True)
            elif skin.cost:
                draw_text(surface, f"{skin.cost} {CURRENCY}", (r.centerx, r.y + 138), 16,
                          GOLD if save.spite >= skin.cost else DIM, bold=True)
            else:
                draw_text(surface, "LOCKED", (r.centerx, r.y + 138), 15, DIM, bold=True)
        draw_text(surface, self.skins[self.index].how, (VIRTUAL_W // 2, VIRTUAL_H - 132), 24, MUTED)
        if self.note:
            draw_text(surface, self.note[0], (VIRTUAL_W // 2, VIRTUAL_H - 88), 28, self.note[1], bold=True)
        draw_text(surface, "ARROWS / MOUSE  choose     ENTER  equip or buy     TAB  awards     ESC  back",
                  (VIRTUAL_W // 2, VIRTUAL_H - 38), 18, DIM, bold=True)
        if self.flash > 0:
            dim(surface, int(80 * self.flash), GOLD)


# ================================================================== starting over
class NewGameScene(Scene):
    """Asked before a new game wipes anything, because a save is hard-won here."""

    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.bg = Background(THEMES["abyss"], seed=71)
        self.menu = Menu([
            MenuItem("KEEP MY PROGRESS", "keep"),
            MenuItem("WIPE IT ALL AND START FRESH", "wipe"),
            MenuItem("BACK", "back"),
        ], center=(VIRTUAL_W // 2, 430), spacing=58, width=620, size=30)

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        action = self.menu.update(dt, controls, events, audio)
        if action == "keep":
            self.game.scenes.switch(NameEntryScene(self.game))
        elif action == "wipe":
            name = self.game.save.player_name
            self.game.save.reset_progress()
            self.game.save.set_name(name)
            audio.play("slam", 0.8)
            self.game.scenes.switch(NameEntryScene(self.game))
        elif action == "back" or controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))

    def draw(self, surface):
        self.bg.draw(surface, self.time * 12)
        dim(surface, 170)
        save = self.game.save
        draw_text(surface, "YOU ALREADY HAVE A GAME", (VIRTUAL_W // 2, 190), 48, PAPER, "display", shadow=INK)
        draw_text(surface, f"{save.data['total_deaths']} deaths and "
                           f"{sum(1 for lv in self.game.levels if save.level_stats(lv.number)['completed'])} "
                           f"levels cleared are sitting in that save.",
                  (VIRTUAL_W // 2, 248), 22, MUTED)
        draw_text(surface, "Wiping clears levels, times and awards. Skins and spite go too.",
                  (VIRTUAL_W // 2, 286), 19, DIM, bold=True)
        self.menu.draw(surface)


# ================================================================== who are you
class NameEntryScene(Scene):
    """Asks what to call you. The narrator will use it, which is the whole point."""

    music = "menu"
    PROMPTS = ["So the narrator knows who to blame.",
               "It will be used against you.",
               "Leave it blank if you're shy."]

    def __init__(self, game, on_done=None):
        super().__init__(game)
        self.bg = Background(THEMES["abyss"], seed=63)
        self.text = game.save.player_name
        self.caret = 0.0
        self.prompt = random.choice(self.PROMPTS)
        self.on_done = on_done or (lambda: self.game.scenes.switch(DifficultyScene(self.game, start_at=1)))

    def _accept(self):
        self.game.save.set_name(self.text)
        self.game.audio.play("ui_select")
        self.on_done()

    def update(self, dt, events):
        super().update(dt, events)
        self.caret = (self.caret + dt) % 1.0
        controls, audio = self.game.controls, self.game.audio
        for e in events:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._accept()
                return
            if e.key == pygame.K_ESCAPE:
                audio.play("ui_back")
                self.game.scenes.switch(TitleScene(self.game))
                return
            if e.key == pygame.K_BACKSPACE:
                if self.text:
                    self.text = self.text[:-1]
                    audio.play("ui_move", 0.5)
                continue
            char = e.unicode
            if char and char.isprintable() and len(self.text) < MAX_NAME:
                self.text += char
                audio.play("ui_move", 0.4)
        if controls.consume("confirm"):
            self._accept()

    def draw(self, surface):
        self.bg.draw(surface, self.time * 12)
        dim(surface, 170)
        draw_text(surface, "WHAT DO WE CALL YOU?", (VIRTUAL_W // 2, 210), 52, PAPER, "display", shadow=INK)
        draw_text(surface, self.prompt, (VIRTUAL_W // 2, 262), 22, MUTED)
        box = pygame.Rect(0, 0, 560, 96)
        box.center = (VIRTUAL_W // 2, 380)
        panel(surface, box, fill=(18, 14, 24, 240), border=(*GOLD, 200), width=3)
        shown = self.text if self.text else ""
        draw_text(surface, shown, (box.centerx, box.centery), 44, PAPER, "display")
        if not self.text:
            draw_text(surface, "nobody", (box.centerx, box.centery), 40, DIM, "display")
        if self.caret < 0.5:
            width = render_text(shown, 44, PAPER, "display").get_width() if shown else 0
            cx = box.centerx + width // 2 + 12
            pygame.draw.rect(surface, GOLD, (cx, box.centery - 22, 4, 44))
        draw_text(surface, f"{len(self.text)} / {MAX_NAME}", (box.right - 16, box.bottom - 14), 16, DIM,
                  bold=True, anchor="midright")
        draw_text(surface, "TYPE a name     ENTER  continue     ESC  back",
                  (VIRTUAL_W // 2, VIRTUAL_H - 60), 20, DIM, bold=True)


# ================================================================== how to play
class PlayScene(Scene):
    """The three ways to play, and the difficulty that applies to them."""

    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.bg = Background(THEMES["neon"], seed=55)
        save = game.save
        label = DIFFICULTIES[save.difficulty]["label"]
        self.menu = Menu([
            MenuItem("CAMPAIGN", "campaign", hint="19 levels, 3 acts"),
            MenuItem("RACE THE BOT", "race", hint="beat the solver's time"),
            MenuItem("STORY MODE", "story", enabled=False, hint="coming soon"),
            MenuItem(f"DIFFICULTY: {label}", "difficulty"),
            MenuItem("BACK", "back"),
        ], center=(VIRTUAL_W // 2, 400), spacing=62, width=560, size=34, align="split")

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        action = self.menu.update(dt, controls, events, audio)
        if action == "campaign":
            self.game.scenes.switch(LevelSelectScene(self.game))
        elif action == "race":
            self.game.scenes.switch(RaceSelectScene(self.game))
        elif action == "difficulty":
            self.game.scenes.switch(DifficultyScene(self.game, from_title=True))
        elif action == "back" or controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))

    def draw(self, surface):
        self.bg.draw(surface, self.time * 14)
        dim(surface, 160)
        draw_text(surface, "HOW DO YOU WANT TO SUFFER?", (VIRTUAL_W // 2, 150), 50, PAPER, "display",
                  shadow=INK)
        self.menu.draw(surface)
        save = self.game.save
        done = sum(1 for lv in self.game.levels if save.level_stats(lv.number)["completed"])
        draw_text(surface, f"{done} of {len(self.game.levels)} levels cleared on "
                           f"{DIFFICULTIES[save.difficulty]['label']}",
                  (VIRTUAL_W // 2, VIRTUAL_H - 70), 20, MUTED)
        draw_text(surface, "ENTER  choose     ESC  back", (VIRTUAL_W // 2, VIRTUAL_H - 38), 18, DIM, bold=True)


# ================================================================== act title card
class ActCardScene(Scene):
    """Big title card between acts. Any key skips."""

    music = None
    cursor = False

    def __init__(self, game, act, next_level):
        super().__init__(game)
        self.act = act
        self.next_level = next_level

    def enter(self):
        super().enter()
        self.game.audio.play("rumble", 0.8)

    def update(self, dt, events):
        super().update(dt, events)
        if self.time > 4.2 or (self.time > 0.6 and any_key(events)):
            self.game.start_level(self.next_level, card=False)

    def draw(self, surface):
        surface.fill((0, 0, 0))
        info = ACTS[self.act]
        t = self.time
        a = int(255 * min(1.0, t / 0.6, max(0.0, (4.2 - t) / 0.6)))
        cx, cy = VIRTUAL_W // 2, VIRTUAL_H // 2
        draw_text(surface, info["name"], (cx, cy - 90), 30, BLOOD, bold=True, alpha=a)
        draw_text(surface, info["title"], (cx, cy - 20), 96, PAPER, "display", alpha=a,
                  scale=1.0 + 0.02 * min(t, 3))
        draw_text(surface, info["tagline"], (cx, cy + 60), 26, MUTED, alpha=a)
        if self.game.save.difficulty == "brutal":
            draw_text(surface, "BRUTAL MODE  \u00b7  NO CHECKPOINTS  \u00b7  NO MERCY", (cx, cy + 120), 18, BLOOD,
                      bold=True, alpha=a)


# ================================================================== level select
class LevelSelectScene(Scene):
    """Levels grouped into acts. Left/right past the edge of an act flips to the next one."""

    music = "menu"

    def __init__(self, game, selected=None):
        super().__init__(game)
        self.bg = Background(THEMES["ruins"], seed=21)
        self.levels = game.levels
        number = selected or game.continue_level()
        self.act = self.levels[number - 1].act
        self.index = [d.number for d in self._act_levels()].index(number)
        self.anims = {}
        self.arrows = (pygame.Rect(30, 330, 60, 80), pygame.Rect(VIRTUAL_W - 90, 330, 60, 80))

    def _act_levels(self, act=None):
        return [d for d in self.levels if d.act == (act or self.act)]

    def _acts(self):
        return sorted({d.act for d in self.levels})

    def _layout(self):
        levels = self._act_levels()
        count = len(levels)
        if count == 1:
            return [pygame.Rect(VIRTUAL_W // 2 - 260, 170, 520, 360)]
        cols = 5 if count > 8 else 4
        card_w, card_h, gap = 210, 180, 26
        rows = (count + cols - 1) // cols
        total_w = cols * card_w + (cols - 1) * gap
        x0 = (VIRTUAL_W - total_w) // 2
        y0 = 160 if rows > 1 else 240
        return [pygame.Rect(x0 + (i % cols) * (card_w + gap), y0 + (i // cols) * (card_h + gap), card_w, card_h)
                for i in range(count)]

    def _switch_act(self, direction, audio):
        acts = self._acts()
        i = acts.index(self.act) + direction
        if 0 <= i < len(acts):
            self.act = acts[i]
            self.index = 0 if direction > 0 else len(self._act_levels()) - 1
            audio.play("ui_select")

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        cards = self._layout()
        count = len(cards)
        cols = 5 if count > 8 else (4 if count > 1 else 1)
        old = (self.act, self.index)
        if controls.consume("left"):
            if self.index % cols == 0:
                self._switch_act(-1, audio)
            else:
                self.index -= 1
        if controls.consume("right"):
            if self.index % cols == cols - 1 or self.index == count - 1:
                self._switch_act(1, audio)
            else:
                self.index += 1
        if controls.consume("up") and self.index >= cols:
            self.index -= cols
        if controls.consume("down") and self.index + cols < count:
            self.index += cols
        cards = self._layout()
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(cards):
                    if rect.collidepoint(e.pos):
                        self.index = i
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.arrows[0].collidepoint(e.pos):
                    self._switch_act(-1, audio)
                elif self.arrows[1].collidepoint(e.pos):
                    self._switch_act(1, audio)
                for i, rect in enumerate(cards):
                    if rect.collidepoint(e.pos):
                        self.index = i
                        self._choose(audio)
        if old != (self.act, self.index):
            audio.play("ui_move")
        if controls.consume("confirm"):
            self._choose(audio)
        if controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))
        for d in self._act_levels():
            key = d.number
            target = 1.0 if d.number == self._act_levels()[self.index].number else 0.0
            self.anims[key] = damp(self.anims.get(key, 0.0), target, 14, dt)

    def _choose(self, audio):
        number = self._act_levels()[self.index].number
        if self.game.save.is_unlocked(number):
            audio.play("ui_select")
            self.game.start_level(number)
        else:
            audio.play("bump")

    def draw(self, surface):
        self.bg.draw(surface, self.time * 15)
        dim(surface, 150)
        save = self.game.save
        info = ACTS[self.act]
        draw_text(surface, f"{info['name']}  \u00b7  {info['title']}", (VIRTUAL_W // 2, 70), 54, PAPER, "display",
                  shadow=INK)
        brutal = save.difficulty == "brutal"
        draw_text(surface, f"MODE: {DIFFICULTIES[save.difficulty]['label']}", (VIRTUAL_W // 2, 116), 18,
                  BLOOD if brutal else MUTED, bold=True)
        acts = self._acts()
        for i, rect in enumerate(self.arrows):
            if (i == 0 and self.act != acts[0]) or (i == 1 and self.act != acts[-1]):
                cx, cy = rect.center
                d = -1 if i == 0 else 1
                pygame.draw.polygon(surface, PAPER, [(cx - 14 * d, cy - 26), (cx + 16 * d, cy), (cx - 14 * d, cy + 26)])
        for i, (defn, r0) in enumerate(zip(self._act_levels(), self._layout())):
            number = defn.number
            theme = THEMES[defn.theme]
            a = self.anims.get(number, 0.0)
            r = r0.inflate(int(14 * a), int(14 * a)).move(0, int(-6 * a))
            unlocked = save.is_unlocked(number)
            stats = save.level_stats(number)
            panel(surface, r, fill=(24, 18, 32, 235) if unlocked else (14, 12, 18, 235),
                  border=(*theme["accent"], 200) if a > 0.5 else (255, 255, 255, 30), width=3 if a > 0.5 else 2)
            strip = pygame.Rect(r.x + 3, r.y + 3, r.w - 6, 10)
            pygame.draw.rect(surface, theme["accent"] if unlocked else DIM, strip,
                             border_top_left_radius=12, border_top_right_radius=12)
            if not unlocked:
                draw_lock(surface, (r.centerx, r.centery - 8), 38, DIM)
                draw_text(surface, "LOCKED", (r.centerx, r.bottom - 32), 20, DIM, bold=True)
                continue
            big = r.w > 400
            draw_text(surface, f"{number:02d}", (r.x + 18, r.y + 22), 96 if big else 54, PAPER, "display",
                      anchor="topleft")
            draw_text(surface, defn.name.upper(), (r.x + 18, r.y + (150 if big else 92)), 34 if big else 21,
                      theme["accent"], bold=True, anchor="topleft")
            draw_skull(surface, (r.x + 28, r.bottom - 30), 18)
            draw_text(surface, str(stats["deaths"]), (r.x + 44, r.bottom - 30), 20, PAPER, anchor="midleft")
            if stats["completed"] and stats["best_time"] is not None:
                draw_clock(surface, (r.x + 110, r.bottom - 30), 18, MUTED)
                draw_text(surface, format_time(stats["best_time"]), (r.x + 124, r.bottom - 30), 18, MUTED,
                          anchor="midleft")
            if stats["completed"] and stats["best_deaths"] is not None:
                letter, _ = rank_for_deaths(stats["best_deaths"])
                badge = pygame.Rect(0, 0, 44, 44)
                badge.topright = (r.right - 14, r.y + 24)
                pygame.draw.rect(surface, INK, badge, border_radius=10)
                pygame.draw.rect(surface, RANK_COLOURS[letter], badge, 3, border_radius=10)
                draw_text(surface, letter, badge.center, 30, RANK_COLOURS[letter], "display")

        defn = self._act_levels()[self.index]
        if save.is_unlocked(defn.number):
            draw_text(surface, f"\u201c{defn.tagline}\u201d", (VIRTUAL_W // 2, 596), 26, PAPER)
            draw_text(surface, THEMES[defn.theme]["name"].upper(), (VIRTUAL_W // 2, 630), 18, MUTED, bold=True)
        else:
            draw_text(surface, "Beat the previous level to unlock. Good luck with that.", (VIRTUAL_W // 2, 606),
                      24, MUTED)
        draw_text(surface, "ARROWS / MOUSE  select     LEFT / RIGHT past the edge  change act     ENTER  play     ESC  back",
                  (VIRTUAL_W // 2, VIRTUAL_H - 30), 17, DIM, bold=True)


# ================================================================== settings
class SettingsScene(Scene):
    overlay = True

    def __init__(self, game):
        super().__init__(game)
        s = game.save
        self.confirm_reset = 0

        def setter(key, after=None):
            def _set(value):
                s.set_setting(key, value)
                if after:
                    after(value)
            return _set

        self.menu = Menu([
            MenuItem("Master volume", kind="slider", get=lambda: s.settings["master_volume"],
                     set=setter("master_volume", lambda v: game.audio.update_volumes())),
            MenuItem("Music volume", kind="slider", get=lambda: s.settings["music_volume"],
                     set=setter("music_volume", lambda v: game.audio.update_volumes())),
            MenuItem("Sound effects", kind="slider", get=lambda: s.settings["sfx_volume"],
                     set=setter("sfx_volume", lambda v: game.audio.play("ui_move"))),
            MenuItem("Screen shake", kind="slider", get=lambda: s.settings["screen_shake"],
                     set=setter("screen_shake")),
            MenuItem("Fullscreen", kind="toggle", get=lambda: s.settings["fullscreen"],
                     set=setter("fullscreen", game.set_fullscreen)),
            MenuItem("Speedrun timer", kind="toggle", get=lambda: s.settings["show_timer"],
                     set=setter("show_timer")),
            MenuItem("Death markers", kind="toggle", get=lambda: s.settings["death_markers"],
                     set=setter("death_markers")),
            MenuItem("Film grain", kind="toggle", get=lambda: s.settings["film_grain"],
                     set=setter("film_grain")),
            MenuItem("Streamer mode (big stats)", kind="toggle", get=lambda: s.settings["streamer_mode"],
                     set=setter("streamer_mode")),
            MenuItem("Hold jump to keep hopping", kind="toggle", get=lambda: s.settings["auto_hop"],
                     set=setter("auto_hop")),
            MenuItem("Reset all progress", "reset", hint="careful"),
            MenuItem("Back", "back"),
        ], center=(VIRTUAL_W // 2, VIRTUAL_H // 2 + 36), spacing=48, width=720, size=27, align="split")

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        action = self.menu.update(dt, controls, events, audio)
        reset_item = next(it for it in self.menu.items if it.action == "reset")
        if self.menu.current.action != "reset":
            self.confirm_reset = 0
            reset_item.label = "Reset all progress"
        if action == "reset":
            self.confirm_reset += 1
            if self.confirm_reset == 1:
                reset_item.label = "Really? Press again to wipe everything"
            else:
                self.game.save.reset_progress()
                self.game.markers.clear()
                reset_item.label = "Progress wiped. Fresh suffering awaits."
                audio.play("sad")
        if action == "back" or controls.consume("back") or controls.consume("pause"):
            audio.play("ui_back")
            self.game.save.save()
            self.game.scenes.pop()

    def draw(self, surface):
        dim(surface, 225, NIGHT)
        box = pygame.Rect(0, 0, 800, 590)
        box.midtop = (VIRTUAL_W // 2, 108)
        panel(surface, box, fill=(16, 12, 24, 240))
        draw_text(surface, "SETTINGS", (VIRTUAL_W // 2, 62), 58, PAPER, "display", shadow=INK)
        self.menu.draw(surface)


# ================================================================== credits / ending
class CreditsScene(Scene):
    music = "menu"

    def __init__(self, game, ending=True):
        super().__init__(game)
        self.ending = ending
        self.bg = Background(THEMES["abyss"], seed=77)
        self.embers = AmbientField(VIRTUAL_W, VIRTUAL_H, (255, 120, 80), count=60, seed=4)
        save = game.save.data
        lines = []
        if ending and game.save.difficulty == "brutal":
            lines += [("YOU BEAT BRUTAL.", 64, BLOOD, "display"), ("", 30, PAPER, "body"),
                      ("That was not supposed to be possible.", 28, PAPER, "body"),
                      ("Go show your chat. They won't believe you.", 28, MUTED, "body"), ("", 60, PAPER, "body")]
        elif ending:
            lines += [("YOU ACTUALLY DID IT.", 64, PAPER, "display"), ("", 30, PAPER, "body"),
                      ("On Normal.", 28, MUTED, "body"),
                      ("Now try Brutal. Unless you're scared.", 28, BLOOD, "body"), ("", 60, PAPER, "body")]
        lines += [
            (f"Lifetime deaths: {save['total_deaths']}", 34, BLOOD, "display"),
            (f"Lifetime time spent suffering: {format_time(save['total_time'])}", 26, PAPER, "body"),
            ("", 70, PAPER, "body"),
            (GAME_TITLE, 60, PAPER, "display"), (GAME_SUBTITLE, 24, BLOOD, "body"), ("", 50, PAPER, "body"),
            ("A GAME BY", 20, MUTED, "body"), (DEVELOPER_NAME, 44, PAPER, "display"),
            (f"aka {STUDIO_NAME}", 24, BLOOD, "body"), ("", 30, PAPER, "body"),
            ("GAME DESIGN, CODE, ART & SOUND", 20, MUTED, "body"), (DEVELOPER_NAME, 34, PAPER, "display"),
            ("", 30, PAPER, "body"),
            ("BUILT WITH", 20, MUTED, "body"), ("Python  +  Pygame  +  numpy", 30, PAPER, "body"),
            ("", 30, PAPER, "body"),
            ("ART & AUDIO", 20, MUTED, "body"), ("100% procedurally generated at startup", 30, PAPER, "body"),
            ("No image or sound files were harmed.", 24, MUTED, "body"),
            ("", 30, PAPER, "body"),
            ("LEVEL DESIGN", 20, MUTED, "body"), ("Pure, distilled spite", 30, PAPER, "body"),
            ("", 30, PAPER, "body"),
            ("QUALITY ASSURANCE", 20, MUTED, "body"),
            ("An automated solver that beat every level so you can't say it's impossible", 24, PAPER, "body"),
            ("", 30, PAPER, "body"),
            ("AWARDS", 20, MUTED, "body"),
            (f"{achievements.progress(game.save, len(game.levels))[0]} of "
             f"{len(achievements.ACHIEVEMENTS)} badges of suffering collected", 28, GOLD, "body"),
            ("", 30, PAPER, "body"),
            ("SPECIAL THANKS", 20, MUTED, "body"), ("You. For not quitting. Yet.", 30, PAPER, "body"),
            ("", 120, PAPER, "body"),
            ("THE END?", 70, BLOOD, "display"),
        ]
        self.lines = lines
        self.scroll = -VIRTUAL_H * 0.9
        self.height = sum(size + 18 for _, size, _, _ in lines)

    def update(self, dt, events):
        super().update(dt, events)
        self.embers.update(dt)
        controls = self.game.controls
        speed = 200 if (controls.held("confirm") or controls.held("jump")) else 60
        self.scroll += dt * speed
        done = self.scroll > self.height - VIRTUAL_H * 0.45
        if controls.consume("back") or (done and any_key(events)):
            self.game.audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))
        self.scroll = min(self.scroll, self.height - VIRTUAL_H * 0.45)

    def draw(self, surface):
        self.bg.draw(surface, self.time * 10)
        self.embers.draw(surface, self.time * 10)
        dim(surface, 140)
        y = -self.scroll
        for text, size, colour, kind in self.lines:
            if text and -80 < y < VIRTUAL_H + 80:
                draw_text(surface, text, (VIRTUAL_W // 2, y), size, colour, kind, anchor="midtop")
            y += size + 18
        if self.game.vignette:
            surface.blit(self.game.vignette, (0, 0))
        draw_text(surface, "hold SPACE to speed up   |   ESC to leave", (VIRTUAL_W // 2, VIRTUAL_H - 26), 16, DIM)


# ================================================================== gameplay
class GameScene(Scene):
    cursor = False

    def __init__(self, game, number, demo=None):
        super().__init__(game)
        self.number = number
        # demo = a recorded list of (move, jump) inputs, 6 physics steps each (autoplay)
        self.demo = demo
        self.demo_step = 0
        self.demo_prev_jump = False
        self.defn = game.levels[number - 1]
        self.music = self.defn.music
        self.difficulty = game.save.difficulty
        self.world = World(self.defn, self.difficulty)
        self.renderer = WorldRenderer(self.world)
        self.theme = self.renderer.theme
        self.world.player.skin = cosmetics.equipped(game.save)   # looks only
        self.camera = Camera(self.world.width, self.world.height)
        self.camera.snap(self.world.player.centerx, self.world.player.bottom)
        self.particles = ParticleSystem()
        self.canvas = pygame.Surface((VIRTUAL_W, VIRTUAL_H)).convert()
        self.markers = game.markers.setdefault((self.difficulty, number), [])

        self.accumulator = 0.0
        self.hitstop = 0.0
        self.dead_timer = 0.0
        self.win_timer = 0.0
        self.flash = 0.0
        self.flash_colour = WHITE
        self.level_time = 0.0
        self.deaths = 0
        self.death_bump = 0.0
        self.jump_queued = False
        self.toasts = []             # achievements that just landed
        self.intro = 0.0
        self.taunt = None            # [text, timer]
        self.last_taunt = None
        self.subtitle = None         # [text, timer, duration]
        self.say_tick = 0.0
        self.paused = False
        self.pause_menu = Menu([MenuItem("RESUME", "resume"), MenuItem("RESTART LEVEL", "restart"),
                                MenuItem("SETTINGS", "settings"), MenuItem("LEVEL SELECT", "levels"),
                                MenuItem("MAIN MENU", "menu")],
                               center=(VIRTUAL_W // 2, VIRTUAL_H // 2 + 50), spacing=58, width=400, size=34)
        self.complete = None
        # the narrator remembers how badly this level went last time
        history = game.save.level_stats(number)["deaths"]
        line = next((text.format(n=history) for limit, text in RETURN_LINES if history >= limit), None)
        if line or self.defn.intro:
            self._say(line or self.defn.intro, 3.2, delay=0.9)

    # ------------------------------------------------------------ helpers
    def _say(self, text, duration=2.6, delay=0.0):
        self.subtitle = [text, -delay, duration]

    def _taunt_for(self, cause, total_deaths, x, y):
        if total_deaths in MILESTONES:
            return MILESTONES[total_deaths]
        # how many times have we died on this exact spot?
        here = sum(1 for mx, my in self.markers if abs(mx - x) < 60 and abs(my - y) < 60)
        if here in SPOT_TAUNTS:
            return random.choice(SPOT_TAUNTS[here])
        name = self.game.save.player_name
        if name and random.random() < NAME_TAUNT_CHANCE:
            return random.choice(NAME_TAUNTS).format(name=name)
        roll = random.random()
        if roll < 0.15:
            pool = MODE_TAUNTS[self.difficulty]
        elif roll < 0.65:
            pool = TAUNTS_BY_CAUSE.get(cause, [])
        else:
            pool = []
        pool = pool or TAUNTS_GENERAL
        choice = random.choice(pool)
        if choice == self.last_taunt and len(pool) > 1:
            choice = random.choice([t for t in pool if t != self.last_taunt])
        self.last_taunt = choice
        return choice

    def _restart_from_checkpoint(self, count_death=True):
        if self.world.state == "play" and count_death:
            self.world.kill("restart")
            self._process_world_events()
            self.dead_timer = 0.25

    # ------------------------------------------------------------ world events -> juice
    def _process_world_events(self):
        audio = self.game.audio
        p = self.world.player
        for name, d in self.world.events:
            if name == "jump":
                audio.play("jump", 0.8, pitch_jitter=True)
                self.particles.dust(d["x"], d["y"], PAPER, 6)
            elif name == "land":
                speed = d["speed"]
                if speed > 250:
                    audio.play("land", clamp(speed / 1000, 0.3, 1.0))
                    self.particles.dust(d["x"], d["y"], PAPER, int(4 + speed / 120))
            elif name == "death":
                self._on_death(d)
            elif name == "crumble_start":
                audio.play("crumble", 0.35)
                self.particles.dust(d["x"], d["y"], self.theme["block_top"], 5)
            elif name == "crumble":
                audio.play("crumble", 0.8)
                self.particles.debris(d["rect"], self.theme["block"], 10)
            elif name == "spike_pop":
                audio.play("pop")
                self.particles.sparks(d["x"], d["y"], PAPER, 8)
            elif name == "reveal":
                audio.play("reveal")
                self.particles.sparks(d["x"], d["y"], GOLD, 14)
            elif name == "bump":
                audio.play("bump", 0.8)
            elif name == "spring":
                audio.play("spring")
                self.particles.dust(d["x"], d["y"], PAPER, 10)
                self.camera.add_trauma(0.15)
            elif name == "checkpoint":
                audio.play("checkpoint")
                self.particles.sparks(d["x"], d["y"], GOLD, 24)
                self._say("Checkpoint. Don't get used to it.", 2.2)
            elif name == "win":
                audio.play("win")
                self.particles.sparks(d["x"], d["y"], self.theme["accent"], 40)
                self.particles.sparks(d["x"], d["y"], GOLD, 30)
                self.flash, self.flash_colour = 0.5, WHITE
                self._on_win()
            elif name == "fake_door":
                audio.play("sad", 0.9)
                self.particles.sparks(d["x"], d["y"], EMBER, 40)
                self.particles.burst(d["x"], d["y"], 30, [(40, 30, 50), (80, 60, 90)], speed=(100, 400),
                                     life=(0.4, 0.9), size=(3, 7), square=True)
            elif name == "door_hop":
                audio.play("troll")
                self.particles.dust(d["x"], d["y"], PAPER, 12)
            elif name == "door_land":
                self.particles.dust(d["x"], d["y"], PAPER, 14)
                self.camera.add_trauma(0.12)
            elif name == "drop":
                audio.play("rumble", 0.5)
            elif name == "slam":
                audio.play("slam", 0.8)
                self.camera.add_trauma(0.4)
                self.particles.dust(d["x"], d["y"], self.theme["block_top"], 18)
            elif name == "arrow_fire":
                audio.play("arrow")
            elif name == "arrow_hit":
                self.particles.sparks(d["x"], d["y"], PAPER, 8)
            elif name == "saw_on":
                audio.play("saw_on")
            elif name == "say":
                self._say(d["text"], d["duration"])
            elif name == "shake":
                self.camera.add_trauma(d["amount"])
            elif name == "sound":
                audio.play(d["name"])
            elif name == "reverse":
                audio.play("reverse")
                self.flash, self.flash_colour = 0.25, (140, 60, 255)
            elif name == "dark":
                audio.play("dark")
            elif name == "appear":
                audio.play("pop")
            elif name == "stomp":
                audio.play("stomp")
                self.particles.burst(d["x"], d["y"], 16, [(120, 200, 90), PAPER], speed=(80, 260),
                                     life=(0.3, 0.7), size=(2, 5), square=True)
                self.camera.add_trauma(0.15)
            elif name == "orb":
                audio.play("orb", 0.6)
            elif name == "cannon":
                audio.play("cannon", 0.7)
                self.camera.add_trauma(0.08)
                self.particles.dust(d["x"], d["y"], (120, 120, 130), 6)
            elif name == "laser":
                audio.play("laser", 0.6)
            elif name == "flip":
                audio.play("flip", 0.35)
            elif name == "swoop":
                audio.play("swoop", 0.6)
            elif name == "key":
                audio.play("checkpoint")
                self.particles.sparks(d["x"], d["y"], GOLD, 30)
                self._say("Got the key. The door is open. Probably.", 2.4)
            elif name == "echo":
                audio.play("reverse")
                self.flash, self.flash_colour = 0.3, (120, 40, 200)
                self._say("Something is following you.", 2.6)
            elif name == "respawn":
                self.particles.burst(d["x"], d["y"], 18, [PLAYER_BODY, self.theme["accent"]], speed=(40, 160),
                                     life=(0.2, 0.5), size=(2, 4), gravity=-100, drag=3)
        self.world.events.clear()

    def _on_death(self, d):
        audio, save = self.game.audio, self.game.save
        audio.play("death")
        audio.play("splat", 0.8)
        self.hitstop = HITSTOP_TIME
        self.camera.add_trauma(0.65)
        self.flash, self.flash_colour = 0.35, BLOOD
        x, y = d["x"], d["y"]
        vx, vy = d["vx"] * 0.3, min(d["vy"], 0) * 0.3
        self.particles.burst(x, y, 16, [PLAYER_BODY, (222, 214, 200), PLAYER_SCARF], speed=(150, 420),
                             life=(0.6, 1.2), size=(3, 6), gravity=1500, drag=0.4, square=True, up_bias=200)
        self.particles.burst(x, y, 40, [BLOOD, (170, 20, 40), (240, 60, 70)], speed=(120, 520), life=(0.5, 1.4),
                             size=(2, 4.5), gravity=1300, drag=0.3, stain=True, up_bias=150)
        for p in self.particles.particles[-56:]:
            p.vx += vx
            p.vy += vy
        self.markers.append((int(x), int(y)))
        if len(self.markers) > MAX_DEATH_MARKERS:
            self.markers.pop(0)
        self.deaths += 1
        self.death_bump = 1.0
        total = save.record_death(self.number, d["cause"])
        coin = death_payout(self.game.session_death_spite)
        if coin:
            self.game.session_death_spite += coin
            save.add_spite(coin)
        self.taunt = [self._taunt_for(d["cause"], total, x, y), 0.0]
        self._check_achievements()
        self.dead_timer = self.world.diff["respawn"]
        self.game.session_deaths += 1

    def _on_win(self):
        self.win_timer = 0.9
        save = self.game.save
        first_clear = not save.level_stats(self.number)["completed"]
        new_time, new_deaths = save.record_clear(self.number, self.level_time, self.deaths)
        letter, comment = rank_for_deaths(self.deaths)
        lines = clear_payout(self.deaths, first_clear, new_time, self._act_finished(),
                             brutal=save.difficulty == "brutal")
        earned = total_of(lines)
        if earned:
            save.add_spite(earned)
            save.save()
        self.complete_data = {"time": self.level_time, "deaths": self.deaths, "letter": letter,
                              "comment": comment, "new_time": new_time, "new_deaths": new_deaths,
                              "payout": lines, "earned": earned,
                              "par": ghosts.par(self.number, self.difficulty)}
        self._check_achievements()

    def _check_achievements(self):
        for won in achievements.check(self.game.save, len(self.game.levels)):
            self.toasts.append([won, 0.0])
            self.game.audio.play("reveal", 0.9)

    def _act_finished(self):
        """True when this level was the last one of its act."""
        levels = self.game.levels
        act = levels[self.number - 1].act
        later = [lv for lv in levels if lv.act == act and lv.number > self.number]
        return not later

    def _open_complete(self):
        last = self.number >= len(self.game.levels)
        pygame.mouse.set_visible(True)
        items =[MenuItem("FINISH" if last else "NEXT LEVEL", "next"), MenuItem("RETRY", "retry"),
                 MenuItem("LEVEL SELECT", "levels")]
        self.complete = {"t": 0.0, "menu": Menu(items, center=(VIRTUAL_W // 2, 545), spacing=50, width=360,
                                                size=30), **self.complete_data}

    # ------------------------------------------------------------ update
    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio

        if self.complete:
            before = self.complete["t"]
            self.complete["t"] += dt
            if before < 1.2 <= self.complete["t"]:
                audio.play("slam", 0.7)
                self.camera.add_trauma(0.25)
            self._update_visuals(dt)
            action = self.complete["menu"].update(dt, controls, events, audio) if self.complete["t"] > 0.8 else None
            if self.demo is not None:
                action = "next" if self.complete["t"] > 3.0 else None
                if controls.consume("back"):
                    self.game.stop_demo()
                    return
            if action == "next":
                if self.number >= len(self.game.levels):
                    self.game.scenes.switch(CreditsScene(self.game, ending=True))
                else:
                    self.game.start_level(self.number + 1)
            elif action == "retry":
                self.game.start_level(self.number, card=False)
            elif action == "levels" or controls.consume("back"):
                self.game.scenes.switch(LevelSelectScene(self.game, self.number))
            return

        if self.paused:
            action = self.pause_menu.update(dt, controls, events, audio)
            if action == "resume" or controls.consume("pause") or controls.consume("back"):
                self._set_paused(False)
            elif action == "restart":
                self.game.start_level(self.number, card=False)
            elif action == "settings":
                self.game.scenes.push(SettingsScene(self.game))
            elif action == "levels":
                self.game.scenes.switch(LevelSelectScene(self.game, self.number))
            elif action == "menu":
                self.game.scenes.switch(TitleScene(self.game))
            return

        if self.demo is not None:
            if controls.consume("pause") or controls.consume("back"):
                self.game.stop_demo()
                return
            events = []
        elif controls.consume("pause"):
            self._set_paused(True)
            return
        for e in events:
            if e.type == pygame.WINDOWFOCUSLOST or (e.type == pygame.ACTIVEEVENT and getattr(e, "gain", 1) == 0):
                self._set_paused(True)
                return
        if controls.consume("restart"):
            self._restart_from_checkpoint()

        self.intro += dt
        for toast in self.toasts:
            toast[1] += dt
        self.toasts = [t for t in self.toasts if t[1] < 4.2]
        if self.world.state == "play":
            self.level_time += dt
            self.game.save.add_play_time(dt)

        if controls.was_pressed("jump"):
            self.jump_queued = True

        # hit-stop: freeze the world for a split second when you die (it sells the impact)
        if self.hitstop > 0:
            self.hitstop -= dt
            self._update_visuals(dt * 0.1)
            return

        move = 0
        if controls.held("left"):
            move -= 1
        if controls.held("right"):
            move += 1
        jump_held = controls.held("jump")
        if self.intro < 0.35 and self.demo is None:
            move, jump_held, self.jump_queued = 0, False, False

        self.accumulator += dt
        steps = 0
        while self.accumulator >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            if self.demo is not None:
                move, jump_held, pressed = self._demo_input()
                self.world.step(FIXED_DT, move, jump_held, pressed)
            else:
                pressed = wants_jump(self.jump_queued, jump_held, self.world.player.on_ground,
                                     self.game.save.settings.get("auto_hop", True))
                self.world.step(FIXED_DT, move, jump_held, pressed)
            self.jump_queued = False
            self.accumulator -= FIXED_DT
            steps += 1
            if self.world.events:
                self._process_world_events()
            if self.hitstop > 0:
                self.accumulator = 0.0
                break
        if steps == MAX_STEPS_PER_FRAME:
            self.accumulator = 0.0

        if self.world.state == "dead" and self.hitstop <= 0:
            self.dead_timer -= dt
            if self.dead_timer <= 0:
                old_x, old_y = self.camera.x, self.camera.y
                self.world.respawn()
                self._process_world_events()
                p = self.world.player
                if abs(p.centerx - old_x - VIRTUAL_W / 2) > VIRTUAL_W or abs(p.bottom - old_y) > VIRTUAL_H * 1.5:
                    self.camera.snap(p.centerx, p.bottom)
        elif self.world.state == "won":
            self.win_timer -= dt
            if self.win_timer <= 0 and not self.complete:
                self._open_complete()

        self._update_visuals(dt)

    def _demo_input(self):
        """Feed the recorded run in exactly the way the level-solver played it."""
        index, sub = divmod(self.demo_step, 6)
        move, jump = self.demo[index] if index < len(self.demo) else (0, False)
        pressed = False
        if sub == 0:
            pressed = jump and not self.demo_prev_jump
            self.demo_prev_jump = jump
        self.demo_step += 1
        return move, jump, pressed

    def _update_visuals(self, dt):
        w = self.world
        p = w.player
        self.camera.shake_scale = self.game.save.settings["screen_shake"]
        if p.alive or not self.markers:
            focus = (p.centerx, p.bottom)
        else:
            focus = self.markers[-1]
        self.camera.update(dt, focus[0], p.facing if p.alive else 0, focus[1])
        self.particles.update(dt, w.solid_at, self.renderer.add_stain)
        self.renderer.update(dt)
        p.animate(dt)
        self.flash = max(0.0, self.flash - dt * 1.6)
        self.death_bump = max(0.0, self.death_bump - dt * 3)
        if self.taunt:
            self.taunt[1] += dt
            if self.taunt[1] > 2.2:
                self.taunt = None
        if self.subtitle:
            before = int(max(0, self.subtitle[1]) * 45)
            self.subtitle[1] += dt
            after = int(max(0, self.subtitle[1]) * 45)
            if after > before and after <= len(self.subtitle[0]) and after % 3 == 0:
                self.game.audio.play("say", 0.5)
            if self.subtitle[1] > self.subtitle[2] + len(self.subtitle[0]) / 45 + 0.4:
                self.subtitle = None

    def _set_paused(self, value):
        if self.paused == value:
            return
        self.paused = value
        self.game.audio.play("ui_select" if value else "ui_back")
        self.game.audio.duck_music(0.35 if value else 1.0)
        pygame.mouse.set_visible(value)
        if not value:
            self.game.audio.update_volumes()

    def enter(self):
        super().enter()
        pygame.mouse.set_visible(self.paused)
        self.game.audio.update_volumes()
        if self.paused:
            self.game.audio.duck_music(0.35)

    # ------------------------------------------------------------ draw
    def draw(self, surface):
        c = self.canvas
        w = self.world
        ox, oy = self.camera.shake_offset()
        cam = (self.camera.view_x() + ox, self.camera.view_y() + oy)
        self.renderer.draw_back(c, cam, self.time)
        self.renderer.draw_world(c, cam, self.time)
        self._draw_world_extras(c, cam)
        if self.game.save.settings["death_markers"]:
            self.renderer.draw_death_markers(c, cam, self.markers, self.time)
        if w.state != "won" or self.win_timer > 0.6:
            w.player.draw(c, cam[0], cam[1])
        self.particles.draw(c, cam[0], cam[1])
        self.renderer.draw_darkness(c, cam, (w.player.centerx, w.player.centery) if w.player.alive else
                                    (self.markers[-1] if self.markers else None))
        # This used to allocate a fresh full-screen alpha surface every frame
        # it was visible. dim() keeps a cache; on web we skip the flash, where
        # one translucent full-screen blit costs more than the whole frame
        # budget and death already reads clearly from the hitstop and debris.
        if self.flash > 0 and not LOW_FX:
            dim(c, int(160 * self.flash), self.flash_colour)
        if self.game.vignette:
            c.blit(self.game.vignette, (0, 0))
        self._draw_hud(c)
        self._draw_toasts(c)
        surface.blit(c, (0, 0))
        if self.paused:
            self._draw_pause(surface)
        if self.complete:
            self._draw_complete(surface)

    def _draw_world_extras(self, canvas, cam):
        """Nothing extra in a normal run; the race scene paints its ghost here."""

    def _draw_hud(self, c):
        s = self.game.save.settings
        # deaths (top left)
        bump = 1.0 + 0.5 * self.death_bump
        panel(c, pygame.Rect(18, 16, 150, 50), fill=(10, 8, 14, 160), border=None, radius=12)
        draw_skull(c, (46, 41), int(26 * bump), PAPER if self.death_bump < 0.3 else BLOOD)
        draw_text(c, str(self.deaths), (72, 41), int(30 * bump), PAPER, "display", anchor="midleft")
        # level name (top centre)
        draw_text(c, f"{self.number:02d}  ·  {self.defn.name.upper()}", (VIRTUAL_W // 2, 30), 20, MUTED,
                  bold=True)
        brutal = self.difficulty == "brutal"
        label = DIFFICULTIES[self.difficulty]["label"] + ("  ·  AUTOPLAY (ESC to stop)" if self.demo is not None else "")
        draw_text(c, label, (VIRTUAL_W // 2, 52), 14, BLOOD if brutal else DIM, bold=True)
        if s.get("streamer_mode"):
            save = self.game.save
            lines = [f"TOTAL DEATHS  {save.data['total_deaths']}",
                     f"THIS SESSION  {self.game.session_deaths}",
                     f"THIS LEVEL (ALL TIME)  {save.level_stats(self.number)['deaths']}"]
            panel(c, pygame.Rect(18, 74, 270, 86), fill=(10, 8, 14, 170), border=None, radius=12)
            for i, text in enumerate(lines):
                draw_text(c, text, (32, 92 + i * 25), 18, PAPER if i else BLOOD, bold=True, anchor="midleft")
        if self.world.height > VIRTUAL_H:
            # altitude meter for the tower
            p = self.world.player
            climbed = 1.0 - clamp(p.bottom / self.world.height, 0, 1)
            bar = pygame.Rect(VIRTUAL_W - 34, 90, 10, 420)
            pygame.draw.rect(c, (10, 8, 14), bar.inflate(6, 6), border_radius=6)
            fill = bar.copy()
            fill.height = int(bar.height * climbed)
            fill.bottom = bar.bottom
            pygame.draw.rect(c, self.theme["accent"], fill, border_radius=5)
            for mx, my in self.markers[-40:]:
                yy = bar.bottom - int(bar.height * (1.0 - clamp(my / self.world.height, 0, 1)))
                pygame.draw.line(c, BLOOD, (bar.left - 5, yy), (bar.left - 1, yy), 2)
            draw_text(c, f"{int(climbed * 100)}%", (bar.centerx, bar.bottom + 22), 16, PAPER, bold=True)
        # timer (top right)
        if s["show_timer"]:
            panel(c, pygame.Rect(VIRTUAL_W - 178, 16, 160, 50), fill=(10, 8, 14, 160), border=None, radius=12)
            draw_text(c, format_time(self.level_time), (VIRTUAL_W - 34, 41), 26, PAPER, "mono",
                      anchor="midright", bold=True)
        if self.world.reverse:
            a = int(160 + 95 * math.sin(self.time * 10))
            draw_text(c, "<  CONTROLS REVERSED  >", (VIRTUAL_W // 2, 72), 24, (190, 120, 255), bold=True, alpha=a)

        # level intro card
        if self.intro < 2.6:
            t = self.intro
            appear = ease_out_cubic(min(1.0, t / 0.4))
            leave = ease_out_cubic(max(0.0, (t - 2.0) / 0.6))
            a = int(255 * appear * (1 - leave))
            y = VIRTUAL_H // 2 - 90 - int(30 * leave)
            band = pygame.Surface((VIRTUAL_W, 150), pygame.SRCALPHA)
            band.fill((0, 0, 0, int(150 * appear * (1 - leave))))
            c.blit(band, (0, y - 75))
            draw_text(c, f"LEVEL {self.number}", (VIRTUAL_W // 2, y - 40), 22, self.theme["accent"], bold=True,
                      alpha=a)
            draw_text(c, self.defn.name.upper(), (VIRTUAL_W // 2 + int(40 * (1 - appear)), y + 4), 64, PAPER,
                      "display", alpha=a)
            draw_text(c, self.defn.tagline, (VIRTUAL_W // 2, y + 50), 20, MUTED, bold=True, alpha=a)

        # narrator subtitle (bottom)
        if self.subtitle and self.subtitle[1] > 0:
            text, t, duration = self.subtitle
            shown = text[: int(t * 45)]
            fade = clamp((duration + len(text) / 45 + 0.4 - t) / 0.4, 0, 1)
            surf = render_text(text, 26, PAPER)
            box = pygame.Rect(0, 0, surf.get_width() + 60, 52)
            box.midbottom = (VIRTUAL_W // 2, VIRTUAL_H - 28)
            panel(c, box, fill=(8, 6, 12, int(200 * fade)), border=(255, 255, 255, int(30 * fade)), radius=26)
            draw_text(c, shown, (box.left + 30, box.centery), 26, PAPER, anchor="midleft", alpha=int(255 * fade))

        # taunt after death
        if self.taunt:
            text, t = self.taunt
            pop = ease_out_back(min(1.0, t / 0.25))
            a = int(255 * clamp((2.2 - t) / 0.4, 0, 1))
            draw_text(c, text, (VIRTUAL_W // 2, 140), 44, BLOOD, "display", shadow=INK, alpha=a,
                      scale=0.6 + 0.4 * pop)

    def _draw_pause(self, surface):
        dim(surface, 175, NIGHT)
        draw_text(surface, "PAUSED", (VIRTUAL_W // 2, 150), 80, PAPER, "display", shadow=INK)
        if self.difficulty == "normal":
            draw_text(surface, "Pausing on Normal. Of course.", (VIRTUAL_W // 2, 250), 18, DIM, bold=True)
        save = self.game.save
        draw_text(surface, f"{self.deaths} deaths this attempt  ·  {save.level_stats(self.number)['deaths']} "
                           f"on this level  ·  {save.data['total_deaths']} total",
                  (VIRTUAL_W // 2, 222), 22, MUTED)
        self.pause_menu.draw(surface)
        draw_text(surface, "Tip: R restarts from the last checkpoint instantly.", (VIRTUAL_W // 2, VIRTUAL_H - 40),
                  18, DIM, bold=True)

    def _draw_toasts(self, surface):
        """Achievement popups, sliding in at the top right and drifting away."""
        for i, (won, t) in enumerate(self.toasts):
            slide = ease_out_back(min(1.0, t / 0.45))
            fade = 1.0 if t < 3.4 else max(0.0, (4.2 - t) / 0.8)
            box = pygame.Rect(0, 0, 420, 76)
            box.topright = (VIRTUAL_W - 24 + int(440 * (1 - slide)), 96 + i * 88)
            panel(surface, box, fill=(20, 16, 28, int(240 * fade)), border=(*GOLD, int(220 * fade)), width=3)
            draw_text(surface, "ACHIEVEMENT", (box.left + 20, box.top + 22), 15, GOLD, bold=True,
                      anchor="midleft", alpha=int(255 * fade))
            draw_text(surface, won.name, (box.left + 20, box.top + 48), 26, PAPER, "display",
                      anchor="midleft", alpha=int(255 * fade))
            if won.skin:
                draw_skin_preview(surface, cosmetics.get(won.skin), (box.right - 44, box.centery), 1.1)

    def _draw_complete(self, surface):
        d = self.complete
        t = d["t"]
        dim(surface, int(170 * min(1.0, t / 0.4)), NIGHT)
        rise = ease_out_cubic(min(1.0, t / 0.5))
        box = pygame.Rect(0, 0, 640, 580)
        box.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 + int(40 * (1 - rise)))
        panel(surface, box, border=(*self.theme["accent"], 160), width=3)
        heading = "LEVEL CLEARED" if d["deaths"] < 60 else "LEVEL CLEARED... SOMEHOW"
        draw_text(surface, heading, (box.centerx, box.top + 50), 46, PAPER, "display", alpha=int(255 * rise))
        # count-up stats
        k = ease_out_cubic(clamp((t - 0.3) / 0.8, 0, 1))
        rows = [("TIME", format_time(d["time"] * k), d["new_time"]),
                ("DEATHS", str(int(round(d["deaths"] * k))), d["new_deaths"])]
        for i, (label, value, best) in enumerate(rows):
            y = box.top + 125 + i * 56
            draw_text(surface, label, (box.left + 70, y), 24, MUTED, bold=True, anchor="midleft")
            draw_text(surface, value, (box.left + 330, y), 34, PAPER, "display", anchor="midright")
            if best and t > 1.1:
                draw_text(surface, "NEW BEST", (box.left + 350, y), 18, TOXIC, bold=True, anchor="midleft")
        if d.get("par") and t > 1.0:
            gap = d["time"] - d["par"]
            if gap > 0:
                nudge = f"THE BOT DID IT IN {format_time(d['par'])}  ·  YOU WERE {gap:.1f}s SLOWER"
            else:
                nudge = f"THE BOT NEEDED {format_time(d['par'])}  ·  YOU WERE FASTER"
            draw_text(surface, nudge, (box.centerx, box.top + 224), 17, MUTED, bold=True)
            draw_text(surface, "RACE THE BOT  ·  MAIN MENU", (box.centerx, box.top + 246), 15, GOLD,
                      bold=True)
        # rank stamp slams in
        if t > 1.2:
            s = ease_out_back(min(1.0, (t - 1.2) / 0.3))
            colour = RANK_COLOURS[d["letter"]]
            badge = pygame.Rect(0, 0, 120, 120)
            badge.center = (box.right - 120, box.top + 150)
            pygame.draw.rect(surface, INK, badge.inflate(int(20 * (1 - s)), int(20 * (1 - s))), border_radius=18)
            pygame.draw.rect(surface, colour, badge, 5, border_radius=18)
            draw_text(surface, d["letter"], badge.center, 90, colour, "display", scale=2.2 - 1.2 * s)
            draw_text(surface, d["comment"], (box.centerx, box.top + 278), 26, colour)
        if t > 1.5 and d.get("earned"):
            k2 = ease_out_cubic(clamp((t - 1.5) / 0.6, 0, 1))
            draw_text(surface, f"+{int(round(d['earned'] * k2))} {CURRENCY}",
                      (box.centerx, box.top + 330), 34, GOLD, "display")
            reasons = "  ·  ".join(label.lower() for label, _ in d["payout"])
            draw_text(surface, reasons, (box.centerx, box.top + 360), 16, MUTED, bold=True)
        if t > 0.8:
            d["menu"].draw(surface)


# ================================================================== racing the bot
class RaceScene(GameScene):
    """You against the solver's verified run, side by side, from the same frame.

    The ghost lives in its own World and replays recorded inputs, so it cannot
    touch you. Dying just restarts the race - there are no deaths to count here
    and nothing to lose but time.
    """

    def __init__(self, game, number):
        super().__init__(game, number)
        self.ghost = ghosts.Ghost(self.defn, self.difficulty)
        self.result = None           # set when someone crosses the line
        self.started = False         # neither runner moves until you do
        self.intro = 0.0

    # ------------------------------------------------------------ racing
    def _restart_race(self):
        """Both runners go back to the start. No death count, no checkpoints."""
        self.world = World(self.defn, self.difficulty)
        self.world.player.skin = cosmetics.equipped(self.game.save)
        self.renderer = WorldRenderer(self.world)
        self.ghost = ghosts.Ghost(self.defn, self.difficulty)
        self.camera.snap(self.world.player.centerx, self.world.player.bottom)
        self.started = False
        self.level_time = 0.0
        self.dead_timer = 0.0
        self.hitstop = 0.0
        self.accumulator = 0.0

    def _on_death(self, d):
        """Dying costs you the run and nothing else."""
        self.game.audio.play("death")
        self.camera.add_trauma(0.5)
        self.flash, self.flash_colour = 0.3, BLOOD
        self.particles.burst(d["x"], d["y"], 30, [BLOOD, (170, 20, 40)], speed=(120, 460),
                             life=(0.4, 1.0), size=(2, 4.5), gravity=1300, drag=0.3)
        self.dead_timer = 0.45

    def _on_win(self):
        self.win_timer = 0.6
        save = self.game.save
        mine, theirs = self.level_time, self.ghost.par
        beaten = mine < theirs
        record = save.data["ghost"]["best"].get(str(self.number))
        if record is None or mine < record:
            save.data["ghost"]["best"][str(self.number)] = round(mine, 3)
        if beaten and str(self.number) not in save.data["ghost"]["beaten"]:
            save.data["ghost"]["beaten"].append(str(self.number))
        save.save()
        earned = 0
        if beaten:
            earned = PAYOUT["clear"] * 2
            save.add_spite(earned)
            save.save()
        self.result = {"t": 0.0, "mine": mine, "theirs": theirs, "beaten": beaten, "earned": earned,
                       "menu": Menu([MenuItem("RACE AGAIN", "again"), MenuItem("PICK A LEVEL", "levels"),
                                     MenuItem("MAIN MENU", "menu")],
                                    center=(VIRTUAL_W // 2, 486), spacing=48, width=340, size=28)}
        self._check_achievements()

    # ------------------------------------------------------------ update
    def update(self, dt, events):
        Scene.update(self, dt, events)
        controls, audio = self.game.controls, self.game.audio
        for toast in self.toasts:
            toast[1] += dt
        self.toasts = [t for t in self.toasts if t[1] < 4.2]

        if self.result:
            self.result["t"] += dt
            self._update_visuals(dt)
            action = self.result["menu"].update(dt, controls, events, audio) if self.result["t"] > 0.5 else None
            if action == "again":
                self.game.scenes.switch(RaceScene(self.game, self.number))
            elif action == "levels":
                self.game.scenes.switch(RaceSelectScene(self.game, self.number))
            elif action == "menu" or controls.consume("back"):
                self.game.scenes.switch(TitleScene(self.game))
            return

        if controls.consume("back") or controls.consume("pause"):
            audio.play("ui_back")
            self.game.scenes.switch(RaceSelectScene(self.game, self.number))
            return
        if controls.consume("restart"):
            self._restart_race()
            return

        self.intro += dt
        if self.dead_timer > 0:
            self.dead_timer -= dt
            self._update_visuals(dt)
            if self.dead_timer <= 0:
                self._restart_race()
            return

        if controls.was_pressed("jump"):
            self.jump_queued = True
        move = (1 if controls.held("right") else 0) - (1 if controls.held("left") else 0)
        jump_held = controls.held("jump")
        if self.intro < 0.35:
            move, jump_held, self.jump_queued = 0, False, False

        if not self.started:
            # The bot replays a recording, so it would react on the exact frame
            # every time while you are still reaching for a key. Nothing moves -
            # not your world, not the ghost's, not the clock - until you go.
            if self.intro >= 0.35 and (move or jump_held or self.jump_queued):
                self.started = True
            else:
                self._update_visuals(dt)
                return

        self.accumulator += dt
        steps = 0
        while self.accumulator >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            pressed = wants_jump(self.jump_queued, jump_held, self.world.player.on_ground,
                                 self.game.save.settings.get("auto_hop", True))
            self.world.step(FIXED_DT, move, jump_held, pressed)
            self.ghost.step(FIXED_DT)              # started on the same frame you did
            self.jump_queued = False
            self.accumulator -= FIXED_DT
            steps += 1
            if self.world.events:
                self._process_world_events()
            if self.world.state != "play":
                break
        # The bot's par is World.time from the solver's run, so read the clock the
        # same way here: same mechanism, same rounding, nothing to argue about.
        self.level_time = self.world.time
        self._update_visuals(dt)

    # ------------------------------------------------------------ draw
    def draw(self, surface):
        super().draw(surface)
        if self.result:
            self._draw_result(surface)

    def _draw_world_extras(self, canvas, cam):
        """The ghost, drawn behind everything the player cares about."""
        if self.ghost.finished and self.ghost.won:
            return
        layer = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        self.ghost.player.draw(layer, cam[0], cam[1])
        layer.set_alpha(110)
        canvas.blit(layer, (0, 0))

    def _draw_hud(self, c):
        super()._draw_hud(c)
        if self.result:
            return
        if not self.started:
            pulse = 0.6 + 0.4 * math.sin(self.time * 5)
            draw_text(c, "MOVE TO START", (VIRTUAL_W // 2, 104), 36, GOLD, "display",
                      alpha=int(255 * pulse), shadow=INK)
            draw_text(c, f"the bot waits for you  ·  par {format_time(self.ghost.par)}",
                      (VIRTUAL_W // 2, 140), 18, MUTED, bold=True)
            return
        gap = self.level_time - self.ghost.time
        ahead = gap <= 0
        colour = TOXIC if ahead else BLOOD
        label = f"{'-' if ahead else '+'}{abs(gap):.2f}s"
        draw_text(c, label, (VIRTUAL_W // 2, 92), 34, colour, "display", shadow=INK)
        draw_text(c, "AHEAD OF THE BOT" if ahead else "BEHIND THE BOT",
                  (VIRTUAL_W // 2, 122), 16, colour, bold=True)
        draw_text(c, f"BOT PAR  {format_time(self.ghost.par)}", (VIRTUAL_W // 2, VIRTUAL_H - 28), 18,
                  MUTED, bold=True)

    def _draw_result(self, surface):
        d = self.result
        t = d["t"]
        dim(surface, int(180 * min(1.0, t / 0.4)), NIGHT)
        box = pygame.Rect(0, 0, 620, 420)
        box.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 + int(30 * (1 - ease_out_cubic(min(1.0, t / 0.5)))))
        panel(surface, box, border=(*(GOLD if d["beaten"] else BLOOD), 200), width=3)
        heading = "YOU BEAT THE BOT" if d["beaten"] else "THE BOT WINS"
        draw_text(surface, heading, (box.centerx, box.top + 54), 44, GOLD if d["beaten"] else PAPER,
                  "display", shadow=INK)
        rows = [("YOU", format_time(d["mine"]), GOLD if d["beaten"] else PAPER),
                ("BOT", format_time(d["theirs"]), PAPER if d["beaten"] else GOLD)]
        for i, (label, value, colour) in enumerate(rows):
            y = box.top + 120 + i * 50
            draw_text(surface, label, (box.left + 80, y), 24, MUTED, bold=True, anchor="midleft")
            draw_text(surface, value, (box.right - 80, y), 34, colour, "display", anchor="midright")
        margin = abs(d["mine"] - d["theirs"])
        draw_text(surface, f"by {margin:.2f} seconds", (box.centerx, box.top + 212), 22, MUTED)
        if d["earned"]:
            draw_text(surface, f"+{d['earned']} {CURRENCY}", (box.centerx, box.top + 248), 26, GOLD, bold=True)
        if t > 0.5:
            d["menu"].draw(surface)


class RaceSelectScene(Scene):
    """Which level to race on. Only ones you have already finished yourself."""

    music = "menu"
    COLS = 5

    def __init__(self, game, selected=None):
        super().__init__(game)
        self.bg = Background(THEMES["neon"], seed=77)
        self.levels = [lv for lv in game.levels if ghosts.available(lv.number, game.save.difficulty)]
        self.index = 0
        if selected:
            self.index = next((i for i, lv in enumerate(self.levels) if lv.number == selected), 0)
        self.anims = {}

    def _layout(self):
        return [pygame.Rect(72 + (i % self.COLS) * 228, 162 + (i // self.COLS) * 126, 208, 110)
                for i in range(len(self.levels))]

    def _playable(self, defn):
        return self.game.save.level_stats(defn.number)["completed"]

    def _choose(self, audio):
        defn = self.levels[self.index]
        if self._playable(defn):
            audio.play("ui_select")
            self.game.scenes.switch(RaceScene(self.game, defn.number))
        else:
            audio.play("bump")

    def update(self, dt, events):
        super().update(dt, events)
        controls, audio = self.game.controls, self.game.audio
        old = self.index
        if controls.consume("left"):
            self.index = max(0, self.index - 1)
        if controls.consume("right"):
            self.index = min(len(self.levels) - 1, self.index + 1)
        if controls.consume("up"):
            self.index = max(0, self.index - self.COLS)
        if controls.consume("down"):
            self.index = min(len(self.levels) - 1, self.index + self.COLS)
        cards = self._layout()
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(cards):
                    if r.collidepoint(e.pos):
                        self.index = i
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(cards):
                    if r.collidepoint(e.pos):
                        self.index = i
                        self._choose(audio)
        if old != self.index:
            audio.play("ui_move")
        if controls.consume("confirm"):
            self._choose(audio)
        if controls.consume("back"):
            audio.play("ui_back")
            self.game.scenes.switch(TitleScene(self.game))
        for i in range(len(self.levels)):
            self.anims[i] = damp(self.anims.get(i, 0.0), 1.0 if i == self.index else 0.0, 14, dt)

    def draw(self, surface):
        self.bg.draw(surface, self.time * 14)
        dim(surface, 165)
        save = self.game.save
        draw_text(surface, "RACE THE BOT", (VIRTUAL_W // 2, 58), 54, PAPER, "display", shadow=INK)
        draw_text(surface, "The solver proved every level. Now beat its time.",
                  (VIRTUAL_W // 2, 104), 20, MUTED)
        beaten = save.data["ghost"]["beaten"]
        for i, (defn, r0) in enumerate(zip(self.levels, self._layout())):
            a = self.anims.get(i, 0.0)
            r = r0.inflate(int(12 * a), int(12 * a)).move(0, int(-5 * a))
            playable = self._playable(defn)
            won = str(defn.number) in beaten
            theme = THEMES[defn.theme]
            panel(surface, r, fill=(22, 18, 30, 235) if playable else (13, 11, 17, 235),
                  border=(*theme["accent"], 210) if i == self.index else (255, 255, 255, 34),
                  width=3 if i == self.index else 2)
            draw_text(surface, f"{defn.number:02d}", (r.left + 18, r.top + 26), 30, PAPER if playable else DIM,
                      "display", anchor="midleft")
            draw_text(surface, defn.name.upper(), (r.left + 18, r.top + 54), 16,
                      theme["accent"] if playable else DIM, bold=True, anchor="midleft")
            if not playable:
                draw_lock(surface, (r.right - 30, r.top + 30), 18, DIM)
                draw_text(surface, "clear it first", (r.left + 18, r.bottom - 22), 15, DIM,
                          bold=True, anchor="midleft")
                continue
            par = ghosts.par(defn.number, save.difficulty)
            draw_text(surface, f"BOT {format_time(par)}", (r.left + 18, r.bottom - 38), 17, MUTED,
                      bold=True, anchor="midleft")
            mine = save.data["ghost"]["best"].get(str(defn.number))
            if mine is not None:
                draw_text(surface, f"YOU {format_time(mine)}", (r.left + 18, r.bottom - 18), 17,
                          GOLD if won else MUTED, bold=True, anchor="midleft")
            if won:
                draw_text(surface, "BEATEN", (r.right - 18, r.bottom - 22), 16, TOXIC, bold=True,
                          anchor="midright")
        draw_text(surface, "ARROWS / MOUSE  choose     ENTER  race     ESC  back",
                  (VIRTUAL_W // 2, VIRTUAL_H - 38), 18, DIM, bold=True)
