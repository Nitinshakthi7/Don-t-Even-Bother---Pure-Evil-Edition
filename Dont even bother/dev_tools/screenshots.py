# dev_tools/screenshots.py - capture store screenshots and a cover image.
#
#   python dev_tools/screenshots.py
#
# Renders the real game offscreen rather than staging anything: the gameplay
# shots are the solver's own verified runs, played to a chosen frame, so what
# ends up on the store page is genuinely the game running.
#
# Writes into press/.

import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "press")
FIXED = 1.0 / 120.0


def build_game():
    """A game with everything unlocked, on a throwaway save."""
    # normally main() does this before constructing the Game
    pygame.init()
    pygame.font.init()
    import main
    save = os.path.join(tempfile.mkdtemp(), "shots.json")
    game = main.Game(windowed=True, unlock_all=True, save_path=save)
    game.save.data["spite"] = 2450
    game.save.data["player_name"] = "NITIN"
    return game


def advance(game, frames, dt=FIXED):
    for _ in range(frames):
        pygame.event.pump()
        game.controls.begin_frame()
        game.scenes.update(dt, [])
        game.scenes.draw(game.screen)


def shot(game, name, frames):
    advance(game, frames)
    path = os.path.join(OUT, name)
    pygame.image.save(game.screen, path)
    print(f"  {name:<24} {os.path.getsize(path) / 1024:6.0f} KB")


def gameplay(game, level, frames, name):
    """Let the solver play the level, then grab a frame mid-run.

    The intro card runs for 2.6s and the opening taunt until about 4s, so the
    frame counts here are deliberately past both - a store page should show
    the game, not its title cards.
    """
    import cosmetics
    game.demo = True
    game.save.set_difficulty("normal")
    # a different character each shot, so the page shows some variety
    skins = [s.id for s in cosmetics.SKINS]
    game.save.data["cosmetics"]["equipped"] = skins[level % len(skins)]
    game.start_level(level)
    advance(game, frames)

    # the HUD says AUTOPLAY while the solver is driving. Playback has already
    # happened by now, so clear it for the one frame we actually keep.
    scene = game.scenes.top
    was, scene.demo = scene.demo, None
    scene.draw(game.screen)
    path = os.path.join(OUT, name)
    pygame.image.save(game.screen, path)
    scene.demo = was
    game.demo = False
    print(f"  {name:<24} {os.path.getsize(path) / 1024:6.0f} KB")


def cover(game):
    """630x500 cover image: the store's thumbnail everywhere on itch."""
    from graphics import draw_text, Background, dim
    from settings import THEMES, BLOOD, PAPER, GOLD, VIRTUAL_W, VIRTUAL_H
    import cosmetics
    from scenes import draw_character_display

    big = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
    Background(THEMES["abyss"], seed=5).draw(big, 0)
    dim(big, 110)
    skin = cosmetics.SKINS[0]
    draw_character_display(big, skin, (VIRTUAL_W // 2, 470), 3.1, 0.0, glow=True, bright=True)
    draw_text(big, "DON'T EVEN", (VIRTUAL_W // 2, 150), 116, PAPER, "display", bold=True)
    draw_text(big, "BOTHER", (VIRTUAL_W // 2, 250), 116, BLOOD, "display", bold=True)
    draw_text(big, "PURE EVIL EDITION", (VIRTUAL_W // 2, 330), 34, GOLD, "display")

    # crop to the cover's aspect, then scale: keeps the art rather than squashing it
    target_w, target_h = 630, 500
    crop_h = VIRTUAL_H
    crop_w = int(crop_h * target_w / target_h)
    crop = big.subsurface(((VIRTUAL_W - crop_w) // 2, 0, crop_w, crop_h)).copy()
    out = pygame.transform.smoothscale(crop, (target_w, target_h))
    path = os.path.join(OUT, "cover.png")
    pygame.image.save(out, path)
    print(f"  {'cover.png':<24} {os.path.getsize(path) / 1024:6.0f} KB  (630x500)")


def main_():
    os.makedirs(OUT, exist_ok=True)
    game = build_game()
    from scenes import TitleScene, SkinsScene, LevelSelectScene

    print(f"writing to {OUT}")
    game.scenes.switch(TitleScene(game), instant=True)
    shot(game, "01-title.png", 90)

    gameplay(game, 3, 760, "02-gameplay.png")
    gameplay(game, 12, 900, "03-traps.png")
    gameplay(game, 19, 1500, "04-the-climb.png")

    game.scenes.switch(SkinsScene(game), instant=True)
    shot(game, "05-characters.png", 40)

    game.scenes.switch(LevelSelectScene(game), instant=True)
    shot(game, "06-levels.png", 40)

    cover(game)
    print("done")


if __name__ == "__main__":
    main_()
