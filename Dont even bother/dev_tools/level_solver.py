# I am adding comments for me to easily understand the codes
# dev_tools/level_solver.py - automated QA for level design.
#
# A troll game is only fair if every level can actually be beaten. This tool
# plays each level by itself: it searches (best-first, like A*) through the
# real game simulation, trying short bursts of input, until it touches the
# real exit door. Because the physics is deterministic, a found solution will
# work the same way every time - so it is saved as a replay and can be
# re-checked after any change to make sure no level was accidentally broken.
#
#   python dev_tools/level_solver.py                 solve every level on Normal (parallel)
#   python dev_tools/level_solver.py 3 7 --brutal    solve levels 3 and 7 on Brutal
#   python dev_tools/level_solver.py --verify        re-run saved replays (add --brutal for Brutal)

import heapq
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
sys.path.insert(0, GAME)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from settings import FIXED_DT, RUN_SPEED, TILE     # noqa: E402
from campaign import LEVELS                         # noqa: E402
from world import World                             # noqa: E402

SOLUTION_ROOT = os.path.join(HERE, "solutions")
STEPS_PER_ACTION = 6                    # each decision lasts 6 physics steps (0.05 s)
ACTIONS = [(1, False), (1, True), (0, False), (0, True), (-1, False), (-1, True)]
# "stand still for a quarter of a second" - lets the bot wait for platforms and saws
# without exploring every tiny wiggle in between
WAIT = (0, False, 5)
SEGMENT_ACTIONS = ACTIONS + [WAIT]
MAX_EXPANSIONS = 250_000
MAX_SECONDS = 3600                      # long levels are searched section by section; give them time
WEIGHTS = (2.0, 6.0, 15.0)                # retry greedier searches if the careful one gives up
SEGMENT_WEIGHTS = (1.0, 2.0, 6.0)         # long levels solved hint-by-hint prefer a patient search


def apply(world, action, prev_jump):
    move, jump = action[0], action[1]
    repeats = action[2] if len(action) > 2 else 1
    for r in range(repeats):
        for i in range(STEPS_PER_ACTION):
            world.step(FIXED_DT, move, jump, jump and not prev_jump and i == 0 and r == 0)
            world.events.clear()
            if world.state != "play":
                return


def expand(action):
    """A long action becomes several saved single actions (replays stay simple)."""
    return [action[:2]] * (action[2] if len(action) > 2 else 1)


def final_door_position(world):
    """Where the exit ends up once every 'goal' (door runs away) trigger has fired.
    Aiming at that spot stops the search being fooled by a door that hops away."""
    target = None
    for trig in world.trigger_defs:
        for action in trig.actions:
            if action[0] == "goal":
                target = ((action[1] + 0.5) * TILE, (action[2] + 1) * TILE)
    if target is None:
        door = world.real_door
        target = (door.rect.centerx, door.rect.bottom)
    return target


def _distance(ax, ay, bx, by, vertical=0.25):
    return abs(ax - bx) + abs(ay - by) * vertical


def heuristic(world):
    p = world.player
    points = [((c + 0.5) * TILE, (r + 1) * TILE) for c, r in world.defn.waypoints]
    # tick off waypoints as the player reaches them
    while world.solver_wp < len(points):
        wx, wy = points[world.solver_wp]
        if p.on_ground and abs(p.centerx - wx) < TILE * 1.5 and abs(p.bottom - wy) < TILE * 0.75:
            world.solver_wp += 1
        else:
            break
    route = points[world.solver_wp:] + [world.solver_target]
    vertical = 3.0 if world.height > 720 else 0.25     # in the tower, height is what matters
    # judge height by the last thing we stood on, so mid-jump states don't look falsely good
    if p.on_ground:
        world.solver_ground = p.bottom
    total = _distance(p.centerx, max(world.solver_ground, p.bottom), *route[0], vertical)
    for a, b in zip(route, route[1:]):
        total += _distance(*a, *b, vertical)
    return total / RUN_SPEED


GRAIN = [1.0]        # >1 = coarser memory of the player, so the search can look further ahead


def state_key(world):
    p = world.player
    g = GRAIN[0]
    # moving things are tracked coarsely, otherwise every moment spent waiting for a
    # platform or a saw would count as a brand new state and the search would explode
    groups = tuple((g.name, round(g.ox / 30), round(g.oy / 30), g.present) for g in world.groups.values())
    blocks = tuple((getattr(b, "timer", None) is not None, b.visible) for b in world.blocks if b.group is None)
    saws = tuple(round(s.travelled / 36) for s in world.saws
                 if abs(s.x - p.x) < 14 * TILE and abs(s.y - p.y) < 10 * TILE)
    door = world.real_door.rect.topleft
    runners = tuple(r.index for r in world.runners)
    # only nearby enemies matter; far-away ones would make every moment look like a new state
    enemies = tuple((e.alive, round(e.x / 30), round(e.y / 30)) for e in world.enemies
                    if abs(e.x - p.x) < 12 * TILE and abs(e.y - p.y) < 10 * TILE)
    timed = (round(world.time / 0.25) if (world.lasers or world.cannons or world.switch_blocks
                                         or world.echo is not None) else 0)
    return (round(p.x / (5 * g)), round(p.y / (5 * g)), round(p.vx / (55 * g)), round(p.vy / (90 * g)), p.on_ground,
            frozenset(world.fired), groups, blocks, saws, door, len(world.arrows), runners,
            world.checkpoint_spawn, world.solver_wp, round(world.solver_ground / 20),
            enemies, world.flip_state, world.has_key, len(world.orbs), timed)


def solve(number, difficulty="normal", verbose=True, weight=2.0, budget=MAX_EXPANSIONS):
    defn = LEVELS[number - 1]
    if defn.waypoints:
        return solve_segmented(number, difficulty, verbose, weight)
    start = World(defn, difficulty)
    start.solver_target = final_door_position(start)
    start.solver_wp = 0
    start.solver_ground = start.player.bottom
    counter = itertools.count()
    frontier = [(heuristic(start), next(counter), start, False, [])]
    seen = set()
    t0 = time.time()
    expansions = 0
    best_h = 1e9
    while frontier:
        _, _, world, prev_jump, path = heapq.heappop(frontier)
        expansions += 1
        if expansions > budget or time.time() - t0 > MAX_SECONDS:
            break
        if verbose and expansions % 5000 == 0:
            print(f"  L{number} (w={weight}): {expansions} expansions, best distance {best_h * RUN_SPEED / TILE:.1f} tiles,"
                  f" {time.time() - t0:.0f}s", flush=True)
        for action in ACTIONS:
            child = world.clone()
            apply(child, action, prev_jump)
            if child.state == "dead":
                continue
            new_path = path + [action]
            if child.state == "won":
                return {"level": number, "solved": True, "actions": new_path, "time": child.time,
                        "expansions": expansions, "seconds": round(time.time() - t0, 1)}
            h = heuristic(child)          # (also ticks off reached waypoints)
            key = state_key(child)
            if key in seen:
                continue
            seen.add(key)
            best_h = min(best_h, h)
            # greedy-leaning A*: time so far + estimated time left (weighted)
            heapq.heappush(frontier, (child.time + h * weight, next(counter), child, action[1], new_path))
    return {"level": number, "solved": False, "expansions": expansions,
            "best_tiles_from_door": round(best_h * RUN_SPEED / TILE, 1), "seconds": round(time.time() - t0, 1)}


BEAM = 12                   # how many different arrival states we carry into the next segment
SEGMENT_BUDGET = 6000


def solve_segmented(number, difficulty="normal", verbose=True, weight=2.0):
    """Long levels: search from route hint to route hint instead of all at once.

    For each segment we collect up to BEAM different ways of arriving (different
    times, speeds, trap states) and search the next segment from all of them, so a
    bad arrival (say, just as a saw comes round) doesn't doom the whole run."""
    defn = LEVELS[number - 1]
    start = World(defn, difficulty)
    start.solver_target = final_door_position(start)
    start.solver_wp = 0
    start.solver_ground = start.player.bottom
    vertical = 3.0 if start.height > 720 else 0.25
    targets = [((c + 0.5) * TILE, (r + 1) * TILE) for c, r in defn.waypoints] + [start.solver_target]
    t0 = time.time()
    counter = itertools.count()
    beam = [(start, False, [])]
    expansions_total = 0

    def cost(world, target):
        p = world.player
        if p.on_ground:
            world.solver_ground = p.bottom
        # height = last thing we stood on, unless we've since fallen below it
        # (while a spring is carrying us, real height counts - it's guaranteed progress)
        y = p.bottom if p.spring_lock else max(world.solver_ground, p.bottom)
        return _distance(p.centerx, y, *target, vertical) / RUN_SPEED

    def search_segment(target, final, seg_weight, budget):
        """Best-first search from every beam state towards one target.
        Returns (arrivals, expansions, winning path or None)."""
        frontier, seen, arrivals = [], set(), []
        for world, prev_jump, path in beam:
            heapq.heappush(frontier, (world.time + seg_weight * cost(world, target), next(counter), world,
                                      prev_jump, path))
        expansions = 0
        while frontier and expansions < budget and len(arrivals) < BEAM:
            if time.time() - t0 > MAX_SECONDS:
                break
            _, _, world, prev_jump, path = heapq.heappop(frontier)
            expansions += 1
            for action in SEGMENT_ACTIONS:
                child = world.clone()
                apply(child, action, prev_jump)
                if child.state == "dead":
                    continue
                new_path = path + expand(action)
                if child.state == "won":
                    return arrivals, expansions, (child, new_path)
                p = child.player
                h = cost(child, target)
                if not final and p.on_ground and abs(p.centerx - target[0]) < TILE * 1.5                         and abs(p.bottom - target[1]) < TILE * 0.75:
                    arrivals.append((child, action[1], new_path))
                    continue
                key = state_key(child)
                if key in seen:
                    continue
                seen.add(key)
                heapq.heappush(frontier, (child.time + seg_weight * h, next(counter), child, action[1], new_path))
        return arrivals, expansions, None

    for seg, target in enumerate(targets):
        final = seg == len(targets) - 1
        arrivals, expansions = [], 0
        # a stubborn segment gets retried with different search styles and a bigger budget
        for seg_weight, budget, grain in ((weight, SEGMENT_BUDGET, 1.0), (6.0, SEGMENT_BUDGET, 1.0),
                                          (1.0, SEGMENT_BUDGET * 2, 3.0), (2.0, SEGMENT_BUDGET * 2, 1.0),
                                          (1.0, SEGMENT_BUDGET * 3, 5.0), (15.0, SEGMENT_BUDGET * 2, 1.0)):
            GRAIN[0] = grain
            arrivals, spent, won = search_segment(target, final, seg_weight, budget)
            GRAIN[0] = 1.0
            expansions += spent
            if won:
                child, path = won
                return {"level": number, "solved": True, "actions": path, "time": child.time,
                        "expansions": expansions_total + expansions, "seconds": round(time.time() - t0, 1)}
            if arrivals or time.time() - t0 > MAX_SECONDS:
                break
        expansions_total += expansions
        if time.time() - t0 > MAX_SECONDS and not arrivals:
            return {"level": number, "solved": False, "expansions": expansions_total,
                    "best_tiles_from_door": f"ran out of time at hint {seg + 1}/{len(targets)}",
                    "seconds": round(time.time() - t0, 1)}
        if verbose:
            print(f"  L{number} [{difficulty}] segment {seg + 1}/{len(targets)}: {len(arrivals)} arrivals, "
                  f"{expansions} expansions, {time.time() - t0:.0f}s", flush=True)
        if not arrivals:
            stuck = targets[seg - 1] if seg else (start.player.centerx, start.player.bottom)
            return {"level": number, "solved": False, "expansions": expansions_total,
                    "best_tiles_from_door": f"stuck before hint {seg + 1}/{len(targets)} "
                                            f"(tile {int(target[0] // TILE)},{int(target[1] // TILE) - 1}), "
                                            f"last reached ({int(stuck[0] // TILE)},{int(stuck[1] // TILE) - 1})",
                    "seconds": round(time.time() - t0, 1)}
        arrivals.sort(key=lambda a: a[0].time)
        beam = arrivals[:BEAM]
    return {"level": number, "solved": False, "expansions": expansions_total,
            "best_tiles_from_door": "never reached the door", "seconds": round(time.time() - t0, 1)}


def solution_path(number, difficulty):
    return os.path.join(SOLUTION_ROOT, difficulty, f"level_{number:02d}.json")


def replay(number, actions, difficulty="normal"):
    """Play a saved input list and report whether it still wins."""
    world = World(LEVELS[number - 1], difficulty)
    prev = False
    for action in actions:
        apply(world, tuple(action), prev)
        prev = action[1]
        if world.state != "play":
            break
    return world.state, world.time


def _solve_and_save(job):
    number, difficulty = job
    weights = SEGMENT_WEIGHTS if LEVELS[number - 1].waypoints else WEIGHTS
    for weight in weights:
        result = solve(number, difficulty, weight=weight, budget=MAX_EXPANSIONS // len(WEIGHTS))
        if result["solved"]:
            break
    result["difficulty"] = difficulty
    if result["solved"]:
        path = solution_path(number, difficulty)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"level": number, "difficulty": difficulty, "steps_per_action": STEPS_PER_ACTION,
                       "actions": [list(a) for a in result["actions"]]}, f)
        state, t = replay(number, result["actions"], difficulty)
        result["replay"] = state
        del result["actions"]
    return result


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    numbers = [int(a) for a in args] or list(range(1, len(LEVELS) + 1))
    difficulty = "brutal" if "--brutal" in sys.argv else "normal"
    if "--verify" in sys.argv:
        ok = True
        for n in numbers:
            path = solution_path(n, difficulty)
            if not os.path.exists(path):
                print(f"Level {n:2d}: no saved solution")
                ok = False
                continue
            with open(path) as f:
                data = json.load(f)
            state, t = replay(n, data["actions"], difficulty)
            print(f"Level {n:2d} [{difficulty}]: {'PASS' if state == 'won' else 'FAIL'} ({state}, {t:.2f}s)")
            ok &= state == "won"
        sys.exit(0 if ok else 1)

    with Pool(min(len(numbers), os.cpu_count() or 2)) as pool:
        results = pool.map(_solve_and_save, [(n, difficulty) for n in numbers], chunksize=1)
    print()
    for r in sorted(results, key=lambda r: r["level"]):
        if r["solved"]:
            print(f"Level {r['level']:2d} [{r['difficulty']}]: SOLVED in {r['time']:.2f}s of game time "
                  f"({r['expansions']} expansions, {r['seconds']}s) replay={r['replay']}")
        else:
            print(f"Level {r['level']:2d} [{r['difficulty']}]: NOT SOLVED - got within {r['best_tiles_from_door']} tiles "
                  f"({r['expansions']} expansions, {r['seconds']}s)")
    sys.exit(0 if all(r["solved"] for r in results) else 1)


if __name__ == "__main__":
    main()
