# I am adding comments for me to easily understand the codes
# dev_tools/render_replay.py - turns a saved solver replay into an animated GIF
# using the real game renderer. Great for checking levels visually and for
# making README / portfolio clips.
#
#   python dev_tools/render_replay.py 3            -> dev_tools/replays/normal_level_03.gif
#   python dev_tools/render_replay.py 3 --brutal   -> the Brutal replay
#   python dev_tools/render_replay.py 3 --frames   -> also saves every 10th frame as PNG

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
sys.path.insert(0, GAME)
sys.path.insert(0, HERE)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame                                  # noqa: E402

import settings                                # noqa: E402

OUT_DIR = os.path.join(HERE, "replays")
FPS = 60


class ReplayControls:
    """Pretends to be the keyboard, pressing whatever the replay says."""

    def __init__(self):
        self.move = 0
        self.jump = False
        self.jump_edge = False
        self.pressed = set()
        self.released = set()

    def begin_frame(self):
        pass

    def held(self, action):
        if action == "left":
            return self.move < 0
        if action == "right":
            return self.move > 0
        if action == "jump":
            return self.jump
        return False

    def was_pressed(self, action):
        return action == "jump" and self.jump_edge

    def consume(self, action):
        return False


def render(number, save_frames=False, difficulty="normal"):
    from PIL import Image
    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    import main
    from scenes import GameScene

    with open(os.path.join(HERE, "solutions", difficulty, f"level_{number:02d}.json")) as f:
        data = json.load(f)
    actions = data["actions"]
    steps_per_action = data["steps_per_action"]

    # a throwaway save so replays never touch the player's real progress
    game = main.Game(windowed=True, unlock_all=True, save_path=os.path.join(OUT_DIR, "replay_save.json"))
    game.save.settings["film_grain"] = False
    game.save.set_difficulty(difficulty)
    controls = ReplayControls()
    game.controls = controls
    scene = GameScene(game, number)
    game.scenes.switch(scene, instant=True)
    scene.intro = 0.36                # replays start moving immediately

    frames = []
    physics_per_frame = settings.PHYSICS_HZ // FPS
    total_steps = len(actions) * steps_per_action
    step = 0
    prev_jump = False
    extra = int(FPS * 1.6)            # keep filming the victory for a moment
    frame_index = 0
    while step < total_steps or extra > 0:
        if step < total_steps:
            move, jump = actions[step // steps_per_action]
            controls.move, controls.jump = move, jump
            controls.jump_edge = jump and not prev_jump and step % steps_per_action == 0
            prev_jump = jump
        else:
            controls.move, controls.jump, controls.jump_edge = 0, False, False
            extra -= 1
        scene.accumulator = 0.0
        scene.update(physics_per_frame * settings.FIXED_DT + 1e-9, [])
        step += physics_per_frame
        game.scenes.draw(game.screen)
        if frame_index % 2 == 0:
            small = pygame.transform.smoothscale(game.screen, (640, 360))
            frames.append(Image.frombytes("RGB", small.get_size(), pygame.image.tobytes(small, "RGB")))
        if save_frames and frame_index % 10 == 0:
            pygame.image.save(game.screen, os.path.join(OUT_DIR, f"{difficulty}_{number:02d}_{frame_index:04d}.png"))
        frame_index += 1
    path = os.path.join(OUT_DIR, f"{difficulty}_level_{number:02d}.gif")
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(2000 / FPS), loop=0,
                   optimize=True)
    print(f"Level {number}: {len(frames)} frames -> {path} (final state: {scene.world.state})")
    pygame.quit()


if __name__ == "__main__":
    levels = [int(a) for a in sys.argv[1:] if a.isdigit()]
    for n in levels:
        render(n, "--frames" in sys.argv, "brutal" if "--brutal" in sys.argv else "normal")
