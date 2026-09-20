# I am adding comments for me to easily understand the codes
# ghosts.py - the bot you race against.
#
# The solver in dev_tools/ proved every level beatable by actually playing it,
# and saved the exact inputs it used. Those recordings are shipped with the
# game, so every level comes with a time that is provably achievable - not a
# designer's guess - and with a ghost that can run the route beside you.
#
# The ghost runs its own World. It never touches yours: it cannot push you,
# kill you, or change a single thing about your run.

import json
import os

from settings import BASE_PATH, FIXED_DT
from world import World

SOLUTIONS = os.path.join(BASE_PATH, "dev_tools", "solutions")
STEPS_PER_ACTION = 6                # must match dev_tools/level_solver.py

_cache = {}


def path_for(level_number, difficulty):
    return os.path.join(SOLUTIONS, difficulty, f"level_{level_number:02d}.json")


def load(level_number, difficulty):
    """The recording for a level, or None when there isn't one."""
    key = (level_number, difficulty)
    if key not in _cache:
        path = path_for(level_number, difficulty)
        try:
            with open(path, encoding="utf-8") as f:
                _cache[key] = json.load(f)
        except (OSError, ValueError):
            _cache[key] = None
    return _cache[key]


def available(level_number, difficulty):
    return load(level_number, difficulty) is not None


def par(level_number, difficulty):
    """How long the bot took, in seconds, or None if it never ran this one."""
    data = load(level_number, difficulty)
    if not data:
        return None
    if "seconds" in data:
        return data["seconds"]
    # older recordings did not store the time; the action count is a close guess
    return round(len(data["actions"]) * STEPS_PER_ACTION * FIXED_DT, 3)


class Ghost:
    """Replays the bot's inputs in its own copy of the level, in real time.

    It steps exactly the way dev_tools/level_solver.py does, so what you watch
    is the same run that was verified, not an approximation of it.
    """

    def __init__(self, level_def, difficulty):
        data = load(level_def.number, difficulty)
        self.actions = [tuple(a) for a in data["actions"]] if data else []
        self.world = World(level_def, difficulty)
        self.par = par(level_def.number, difficulty) or 0.0
        self.index = 0          # which action
        self.repeat = 0         # how many times this action has been repeated
        self.sub = 0            # which of its six physics steps
        self.prev_jump = False
        self.finished = not self.actions
        self.time = 0.0

    @property
    def player(self):
        return self.world.player

    @property
    def won(self):
        return self.world.state == "won"

    def step(self, dt=FIXED_DT):
        """One physics step of the recording."""
        if self.finished or self.index >= len(self.actions):
            self.finished = True
            return
        action = self.actions[self.index]
        move, jump = action[0], action[1]
        repeats = action[2] if len(action) > 2 else 1
        pressed = jump and not self.prev_jump and self.sub == 0 and self.repeat == 0
        self.world.step(dt, move, jump, pressed)
        self.world.events.clear()
        self.time += dt
        if self.world.state != "play":
            self.finished = True
            return
        self.sub += 1
        if self.sub >= STEPS_PER_ACTION:
            self.sub = 0
            self.repeat += 1
            if self.repeat >= repeats:
                self.repeat = 0
                self.prev_jump = jump
                self.index += 1

    def reset(self, level_def, difficulty):
        self.__init__(level_def, difficulty)
