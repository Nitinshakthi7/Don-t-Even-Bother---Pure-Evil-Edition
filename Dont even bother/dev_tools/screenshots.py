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
    """630x500 cover image - the thumbnail itch shows everywhere.

    Drawn at double size and scaled down, so the type stays crisp, and
    composed to fill the frame: title up top, the character over a bed of
    spikes at the bottom. It has to read at thumbnail size, so contrast and
    size matter more than detail.
    """
    from graphics import draw_text, render_text, glow_circle, vertical_gradient, TileArt
    from settings import THEMES, BLOOD, DARK_BLOOD, PAPER, GOLD, INK, TILE
    import cosmetics

    W, H = 1260, 1000                      # 2x the final size
    canvas = pygame.Surface((W, H))
    canvas.blit(pygame.transform.smoothscale(
        vertical_gradient(8, H, (16, 10, 22), (58, 8, 24)), (W, H)), (0, 0))

    # a red bloom behind where the character stands
    glow = glow_circle(460, (215, 35, 58), 165)
    canvas.blit(glow, (W // 2 - 460, 700 - 460))

    def fit(text, y, size, colour, max_w, shadow=None):
        """Shrink until it fits the frame - never let the title touch the edge."""
        while size > 10 and render_text(text, size, colour, "display", True).get_width() > max_w:
            size -= 2
        if shadow:
            draw_text(canvas, text, (W // 2 + 5, y + 6), size, shadow, "display", bold=True)
        draw_text(canvas, text, (W // 2, y), size, colour, "display", bold=True)

    fit("DON'T EVEN", 200, 150, PAPER, W - 120, shadow=(0, 0, 0))
    fit("BOTHER", 350, 165, BLOOD, W - 120, shadow=DARK_BLOOD)
    draw_text(canvas, "P U R E   E V I L   E D I T I O N", (W // 2, 470), 44, GOLD, "display", bold=True)

    # spikes along the floor: says "platformer that kills you" without a word.
    # They have to survive being shrunk to a thumbnail, so they are big.
    art = TileArt(THEMES["abyss"])
    size = TILE * 5
    spike = pygame.transform.smoothscale(art.spikes["up"], (size, size))
    for x in range(-size // 2, W + size, size):
        canvas.blit(spike, (x, H - size))
    pygame.draw.rect(canvas, (22, 15, 26), (0, H - 46, W, 46))

    # the character, mid-jump just above the spikes - the whole game in one image
    skin = cosmetics.SKINS[0]
    body = pygame.Rect(0, 0, 200, 250)
    body.center = (W // 2, 700)
    cosmetics.draw_body(canvas, skin, body)

    # darken the corners so the middle carries the eye
    edge = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(90):
        a = int(150 * (1 - i / 90) ** 1.7)
        pygame.draw.rect(edge, (0, 0, 0, a), (i, i, W - i * 2, H - i * 2), 2)
    canvas.blit(edge, (0, 0))

    out = pygame.transform.smoothscale(canvas, (630, 500))
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
