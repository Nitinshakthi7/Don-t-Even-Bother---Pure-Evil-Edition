# I am adding comments for me to easily understand the codes
# tests/test_game.py - automatic checks for the game rules.
# Run from the game folder with:   python -m unittest discover tests

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
sys.path.insert(0, GAME)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from settings import FIXED_DT, TILE                               # noqa: E402
from levels import LevelDef, Trigger, LaserDef, CannonDef, WindDef  # noqa: E402
from campaign import LEVELS                                      # noqa: E402
from world import World                                          # noqa: E402
from player import wants_jump                                    # noqa: E402
from utils import SaveManager, rank_for_deaths, format_time      # noqa: E402
from economy import clear_payout, total_of, death_payout         # noqa: E402
import cosmetics                                                 # noqa: E402
import achievements                                              # noqa: E402
import ghosts                                                    # noqa: E402
from settings import PAYOUT, DEATH_PAYOUT_CAP                    # noqa: E402

KNOWN_CHARS = set(".#~PGXKB^v<>hcxi123456789eSmuoRUTY{}Ik")


def make_level(rows, **kwargs):
    """Build a tiny test level. Rows are padded up to 18 with empty rows on top."""
    width = len(rows[0])
    full = ["." * width] * (18 - len(rows)) + rows
    return World(LevelDef(99, "Test", "", "ruins", full, **kwargs))


def run(world, seconds, move=0, jump=False):
    steps = int(seconds / FIXED_DT)
    for i in range(steps):
        world.step(FIXED_DT, move, jump, jump and i == 0)
        if world.state != "play":
            break
    return world


class TestLevels(unittest.TestCase):
    def test_every_level_is_well_formed(self):
        for level in LEVELS:
            text = "".join(level.rows)
            self.assertEqual(text.count("P"), 1, f"level {level.number} needs one spawn")
            self.assertEqual(text.count("G"), 1, f"level {level.number} needs one real door")
            unknown = set(text) - KNOWN_CHARS - set(level.legend)
            self.assertFalse(unknown, f"level {level.number} uses unknown characters {unknown}")

    def test_trigger_groups_exist(self):
        for level in LEVELS:
            world = World(level)
            for trig in level.triggers:
                for action in trig.actions:
                    if action[0] in ("drop", "move", "vanish", "appear"):
                        self.assertIn(action[1], world.groups, f"level {level.number}: missing group {action[1]}")

    def test_saved_solutions_still_win(self):
        """Replays recorded by dev_tools/level_solver.py must keep beating their level, in both modes."""
        sys.path.insert(0, os.path.join(GAME, "dev_tools"))
        from level_solver import replay, solution_path
        checked = 0
        for difficulty in ("normal", "brutal"):
            for level in LEVELS:
                path = solution_path(level.number, difficulty)
                if not os.path.exists(path):
                    continue
                with open(path) as f:
                    actions = json.load(f)["actions"]
                state, _ = replay(level.number, actions, difficulty)
                self.assertEqual(state, "won", f"level {level.number} ({difficulty}) replay no longer wins")
                checked += 1
        self.assertGreater(checked, 0)


class TestPlayerPhysics(unittest.TestCase):
    def test_standing_still_never_flickers_off_the_ground(self):
        # The old version lost 'on_ground' every other frame. Never again.
        world = make_level(["..P.....", "########"])
        run(world, 0.3)
        history = []
        for _ in range(240):
            world.step(FIXED_DT)
            history.append(world.player.on_ground)
        self.assertTrue(all(history))

    def test_jump_height_is_about_three_tiles(self):
        world = make_level(["..P.....", "########"])
        run(world, 0.3)
        ground_y = world.player.y
        world.step(FIXED_DT, 0, True, True)
        best = 0
        for _ in range(120):
            world.step(FIXED_DT, 0, True, False)
            best = max(best, ground_y - world.player.y)
        self.assertGreater(best, 3 * TILE)
        self.assertLess(best, 3.6 * TILE)

    def test_walls_block_movement(self):
        world = make_level(["..P..#..", "########"])
        run(world, 1.5, move=1)
        self.assertLessEqual(world.player.x + world.player.w, 5 * TILE)

    def test_falling_in_a_pit_kills(self):
        world = make_level(["..P.....", "###....."])
        run(world, 3, move=1)
        self.assertEqual(world.death_cause, "fall")


class TestTraps(unittest.TestCase):
    def test_spikes_kill(self):
        world = make_level(["..P.^...", "########"])
        run(world, 2, move=1)
        self.assertEqual(world.death_cause, "spike")

    def test_hidden_spike_is_invisible_until_you_are_on_it(self):
        world = make_level(["..P....h....", "############"])
        spike = world.spikes[0]
        run(world, 0.2)
        self.assertFalse(spike.visible)
        run(world, 3, move=1)
        self.assertTrue(spike.visible)
        self.assertEqual(world.death_cause, "hidden")

    def test_fake_block_drops_you(self):
        world = make_level(["..P.....", "###xxx##", "........"])
        run(world, 0.2)
        world.player.x = 3.6 * TILE
        run(world, 2)
        self.assertEqual(world.death_cause, "fall")

    def test_crumble_block_waits_before_falling(self):
        world = make_level(["..P.....", "..c.....", "........"])
        run(world, 0.2)
        self.assertTrue(world.player.on_ground)
        run(world, 1.5)
        self.assertEqual(world.death_cause, "fall")

    def test_invisible_block_only_appears_from_below(self):
        world = make_level(["........", "..i.....", "........", "..P.....", "########"])
        block = world.blocks[0]
        run(world, 0.2)
        run(world, 0.4, jump=True)
        self.assertTrue(block.visible)

    def test_fake_door_kills_and_real_door_wins(self):
        world = make_level(["..P.X...", "########"])
        run(world, 2, move=1)
        self.assertEqual(world.death_cause, "fake_goal")
        world = make_level(["..P.G...", "########"])
        run(world, 2, move=1)
        self.assertEqual(world.state, "won")

    def test_dropping_group_crushes(self):
        world = make_level(["..1.....", "..a.....", "........", "..P.....", "########"],
                           legend={"a": ("spike", "1", True)},
                           triggers=[Trigger((0, 0, 8, 18), [("drop", "1")])])
        run(world, 2)
        self.assertIn(world.death_cause, ("crush", "spike"))

    def test_moving_platform_carries_player(self):
        world = make_level(["........", "..P.....", ".111....", "........"],
                           triggers=[Trigger((0, 0, 8, 18), [("move", "1", 3, 0, 1.0)])])
        run(world, 1.5)
        self.assertEqual(world.state, "play")
        self.assertGreater(world.player.x, 4.5 * TILE)

    def test_reverse_controls(self):
        world = make_level(["....P.......", "############"],
                           triggers=[Trigger((0, 0, 12, 18), [("reverse", True)])])
        start = world.player.x
        run(world, 0.5, move=1)
        self.assertLess(world.player.x, start)

    def test_checkpoint_changes_respawn(self):
        world = make_level(["..P..K....^.", "############"])
        run(world, 3, move=1)
        self.assertEqual(world.state, "dead")
        world.respawn()
        self.assertGreater(world.player.x, 5 * TILE - TILE)

    def test_every_attempt_is_identical(self):
        # Determinism: the same inputs must always give the same result.
        a = run(World(LEVELS[5]), 4, move=1)
        b = run(World(LEVELS[5]), 4, move=1)
        self.assertEqual((a.player.x, a.player.y, a.state), (b.player.x, b.player.y, b.state))


class TestEconomy(unittest.TestCase):
    """Spite is earned by playing well, never by farming deaths."""

    def test_a_clean_first_clear_pays_the_most(self):
        clean = total_of(clear_payout(0, first_clear=True, new_best_time=False, act_finished=False))
        messy = total_of(clear_payout(40, first_clear=True, new_best_time=False, act_finished=False))
        self.assertGreater(clean, messy)
        self.assertEqual(messy, PAYOUT["clear"])        # a clear still pays something

    def test_brutal_pays_double(self):
        normal = total_of(clear_payout(0, True, False, True, brutal=False))
        brutal = total_of(clear_payout(0, True, False, True, brutal=True))
        self.assertEqual(brutal, normal * 2)

    def test_replaying_a_cleared_level_only_pays_for_improving(self):
        nothing = clear_payout(20, first_clear=False, new_best_time=False, act_finished=False)
        better = clear_payout(20, first_clear=False, new_best_time=True, act_finished=False)
        self.assertEqual(total_of(nothing), 0)
        self.assertEqual(total_of(better), PAYOUT["best_time"])

    def test_dying_stops_paying_at_the_cap(self):
        paid = 0
        for _ in range(500):
            paid += death_payout(paid)
        self.assertEqual(paid, DEATH_PAYOUT_CAP)

    def test_a_deathless_run_beats_grinding_deaths(self):
        """The whole point of the cap: playing well must out-earn dying on purpose."""
        self.assertGreater(total_of(clear_payout(0, True, False, False)), DEATH_PAYOUT_CAP)


class TestSaveUpgrade(unittest.TestCase):
    """A version 3 save has to survive gaining a wallet."""

    def _v3_save(self):
        path = os.path.join(tempfile.mkdtemp(), "save.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 3, "total_deaths": 268, "total_time": 900.0, "difficulty": "brutal",
                       "modes": {"normal": {"unlocked": 19, "levels": {"1": {"deaths": 5}}, "completed": False},
                                 "brutal": {"unlocked": 7, "levels": {}, "completed": False}},
                       "settings": {"master_volume": 0.5}}, f)
        return path

    def test_old_progress_survives(self):
        save = SaveManager(19, path=self._v3_save())
        self.assertEqual(save.data["version"], 4)
        self.assertEqual(save.data["total_deaths"], 268)
        self.assertEqual(save.difficulty, "brutal")
        self.assertEqual(save.data["modes"]["normal"]["unlocked"], 19)
        self.assertEqual(save.data["modes"]["brutal"]["unlocked"], 7)
        self.assertEqual(save.settings["master_volume"], 0.5)

    def test_the_new_sections_appear_empty(self):
        save = SaveManager(19, path=self._v3_save())
        self.assertEqual(save.spite, 0)
        self.assertEqual(save.data["cosmetics"]["equipped"], "default")
        self.assertEqual(save.data["death_causes"], {})

    def test_spending_cannot_go_negative(self):
        save = SaveManager(19, path=self._v3_save())
        save.add_spite(60)
        self.assertFalse(save.spend_spite(61))
        self.assertEqual(save.spite, 60)
        self.assertTrue(save.spend_spite(60))
        self.assertEqual(save.spite, 0)

    def test_deaths_remember_what_killed_you(self):
        save = SaveManager(19, path=self._v3_save())
        save.record_death(3, "spike")
        save.record_death(3, "spike")
        save.record_death(4, "fake_door")
        self.assertEqual(save.data["death_causes"], {"spike": 2, "fake_door": 1})


class TestSkins(unittest.TestCase):
    """Skins are looks only, bought or earned, and never given away by mistake."""

    def _save(self):
        path = os.path.join(tempfile.mkdtemp(), "save.json")
        return SaveManager(19, path=path)

    def test_you_start_with_the_default_and_nothing_else(self):
        save = self._save()
        self.assertEqual(cosmetics.equipped(save).id, "default")
        self.assertEqual(cosmetics.unlocked_ids(save), {"default"})

    def test_buying_needs_the_money_and_takes_it(self):
        save = self._save()
        ember = cosmetics.get("ember")
        self.assertFalse(cosmetics.buy(save, ember))       # broke
        save.add_spite(ember.cost)
        self.assertTrue(cosmetics.buy(save, ember))
        self.assertEqual(save.spite, 0)
        self.assertIn("ember", cosmetics.unlocked_ids(save))
        self.assertFalse(cosmetics.buy(save, ember))       # already owned, no double charge

    def test_earned_skins_cannot_be_bought(self):
        save = self._save()
        save.add_spite(10000)
        earned = cosmetics.get("summiteer")
        self.assertEqual(earned.cost, 0)
        self.assertFalse(cosmetics.buy(save, earned))
        self.assertEqual(save.spite, 10000)

    def test_you_can_only_wear_what_you_own(self):
        save = self._save()
        self.assertFalse(cosmetics.equip(save, "void"))
        self.assertEqual(cosmetics.equipped(save).id, "default")
        cosmetics.unlock(save, "void")
        self.assertTrue(cosmetics.equip(save, "void"))
        self.assertEqual(cosmetics.equipped(save).id, "void")

    def test_a_revoked_skin_falls_back_instead_of_crashing(self):
        save = self._save()
        save.data["cosmetics"]["equipped"] = "nonsense"
        self.assertEqual(cosmetics.equipped(save).id, "default")

    def test_every_skin_is_reachable_somehow(self):
        for skin in cosmetics.SKINS:
            with self.subTest(skin=skin.id):
                self.assertTrue(skin.cost > 0 or skin.achievement or skin.id == "default",
                                f"{skin.id} can never be obtained")
                self.assertTrue(skin.how, f"{skin.id} does not say how to get it")

    def test_a_skin_cannot_change_how_the_game_plays(self):
        """The whole point: cosmetics are drawing only, never physics."""
        rows = ["." * 20, "." * 20, "..P" + "." * 17, "#" * 20]
        plain, dressed = make_level(rows), make_level(rows)
        dressed.player.skin = cosmetics.get("void")
        for _ in range(240):
            plain.step(FIXED_DT, 1, True, True)
            dressed.step(FIXED_DT, 1, True, True)
            plain.events.clear()
            dressed.events.clear()
        self.assertEqual((plain.player.x, plain.player.y, plain.player.vx, plain.player.vy),
                         (dressed.player.x, dressed.player.y, dressed.player.vx, dressed.player.vy))


class TestAchievements(unittest.TestCase):
    """Badges are earned once, hand over their skin, and never fire early."""

    def _save(self):
        return SaveManager(19, path=os.path.join(tempfile.mkdtemp(), "save.json"))

    def test_a_fresh_save_has_earned_nothing(self):
        save = self._save()
        self.assertEqual(achievements.check(save, 19), [])
        self.assertEqual(achievements.earned(save), set())

    def test_deaths_unlock_in_order(self):
        save = self._save()
        save.data["total_deaths"] = 1
        self.assertEqual([a.id for a in achievements.check(save, 19)], ["first_blood"])
        save.data["total_deaths"] = 100
        self.assertEqual([a.id for a in achievements.check(save, 19)], ["deaths_100"])
        self.assertTrue(achievements.has(save, "first_blood"))

    def test_an_award_hands_over_its_skin(self):
        save = self._save()
        save.data["total_deaths"] = 1000
        achievements.check(save, 19)
        self.assertTrue(achievements.has(save, "deaths_1000"))
        self.assertIn("gravedigger", cosmetics.unlocked_ids(save))

    def test_nothing_is_awarded_twice(self):
        save = self._save()
        save.data["total_deaths"] = 5000
        first = achievements.check(save, 19)
        self.assertTrue(first)
        self.assertEqual(achievements.check(save, 19), [])

    def test_connoisseur_needs_every_cause(self):
        save = self._save()
        causes = list(achievements.ALL_CAUSES)
        save.data["death_causes"] = {c: 1 for c in causes[:-1]}
        achievements.check(save, 19)
        self.assertFalse(achievements.has(save, "every_cause"))
        save.data["death_causes"][causes[-1]] = 1
        achievements.check(save, 19)
        self.assertTrue(achievements.has(save, "every_cause"))

    def test_act_one_on_brutal_is_not_earned_by_normal(self):
        save = self._save()
        for n in range(1, 11):
            save.data["modes"]["normal"]["levels"][str(n)] = {"completed": True}
        achievements.check(save, 19)
        self.assertFalse(achievements.has(save, "act1_brutal"))
        for n in range(1, 11):
            save.data["modes"]["brutal"]["levels"][str(n)] = {"completed": True}
        achievements.check(save, 19)
        self.assertTrue(achievements.has(save, "act1_brutal"))

    def test_every_award_points_at_a_real_skin(self):
        for award in achievements.ACHIEVEMENTS:
            if award.skin:
                with self.subTest(award=award.id):
                    self.assertIn(award.skin, cosmetics.BY_ID)

    def test_every_earned_skin_has_an_award_that_gives_it(self):
        """Otherwise a skin sits in the list that nobody can ever unlock."""
        handed_out = {a.skin for a in achievements.ACHIEVEMENTS if a.skin}
        for skin in cosmetics.SKINS:
            if skin.achievement:
                with self.subTest(skin=skin.id):
                    self.assertIn(skin.id, handed_out)
                    self.assertIn(skin.achievement, achievements.BY_ID)

    def test_a_broken_save_does_not_crash_the_check(self):
        save = self._save()
        save.data["modes"]["normal"]["levels"] = None      # nonsense on purpose
        self.assertEqual(achievements.check(save, 19), [])


class TestGhosts(unittest.TestCase):
    """The bot you race is the same verified run the tests replay."""

    def test_every_level_has_a_ghost_in_both_modes(self):
        missing = [(lv.number, d) for lv in LEVELS for d in ("normal", "brutal")
                   if not ghosts.available(lv.number, d)]
        self.assertEqual(missing, [], f"no recording for {missing}")

    def test_par_times_are_real_numbers(self):
        for lv in LEVELS:
            for difficulty in ("normal", "brutal"):
                with self.subTest(level=lv.number, difficulty=difficulty):
                    par = ghosts.par(lv.number, difficulty)
                    self.assertIsNotNone(par)
                    self.assertGreater(par, 0)

    def test_a_missing_recording_answers_politely(self):
        self.assertIsNone(ghosts.par(999, "normal"))
        self.assertFalse(ghosts.available(999, "normal"))

    def test_the_ghost_finishes_exactly_on_its_par(self):
        for number in (1, 9):
            with self.subTest(level=number):
                ghost = ghosts.Ghost(LEVELS[number - 1], "normal")
                steps = 0
                while not ghost.finished and steps < 100000:
                    ghost.step()
                    steps += 1
                self.assertTrue(ghost.won, "the ghost failed its own level")
                self.assertAlmostEqual(ghost.time, ghost.par, places=2)

    def test_the_ghost_cannot_touch_your_run(self):
        """It runs in its own World, so racing must not change the game you play."""
        number = 1
        alone = World(LEVELS[number - 1], "normal")
        watched = World(LEVELS[number - 1], "normal")
        ghost = ghosts.Ghost(LEVELS[number - 1], "normal")
        for _ in range(600):
            alone.step(FIXED_DT, 1, True, True)
            watched.step(FIXED_DT, 1, True, True)
            ghost.step()
            alone.events.clear()
            watched.events.clear()
        self.assertEqual((alone.player.x, alone.player.y, alone.state),
                         (watched.player.x, watched.player.y, watched.state))


class TestClimbLayout(unittest.TestCase):
    """The Climb has to stay climbable: a ledge overhead caps your jump."""

    STAND = set("#IcxRUTY123456789")

    def ledges(self, rows):
        found = []
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                if row[c] in self.STAND:
                    start = c
                    while c < len(row) and row[c] in self.STAND:
                        c += 1
                    if not (start == c - 1 and r + 1 < len(rows) and rows[r + 1][start] in self.STAND):
                        found.append((r, start, c - 1))      # a wall column is not a ledge
                else:
                    c += 1
        return found

    def test_no_ledge_is_capped_by_the_one_above_it(self):
        """A full jump is ~3.4 tiles. A ledge four rows up steals most of that, so
        wherever one sits directly overhead the next ledge must be close enough
        to still reach with the stub of a jump that's left."""
        climb = next(level for level in LEVELS if level.act == 3)
        ledges = self.ledges(climb.rows)
        by_row = {}
        for r, c0, c1 in ledges:
            by_row.setdefault(r, []).append((c0, c1))
        problems = []
        for r, c0, c1 in ledges:
            overhead = [(a, b) for a, b in by_row.get(r - 4, []) if a <= c1 + 1 and b >= c0 - 1]
            if not overhead:
                continue
            nxt = by_row.get(r - 2, [])
            close = [(a, b) for a, b in nxt if (a - c1 - 1) <= 2 and (c0 - b - 1) <= 2]
            if not close:
                problems.append(f"row {r} cols {c0}-{c1} is capped by {overhead} with nothing near above")
        self.assertEqual(problems, [], "; ".join(problems))


class TestHoldToHop(unittest.TestCase):
    """Holding the jump button re-jumps on landing, but never twice in the air."""

    FLAT = ["." * 20, "." * 20, "..P" + "." * 17, "#" * 20]

    def _hold_jump(self, auto_hop, seconds=4.0):
        world = make_level(self.FLAT)
        jumps = airborne = 0
        queued = False
        for _ in range(int(seconds / FIXED_DT)):
            grounded = world.player.on_ground
            world.step(FIXED_DT, 0, True, wants_jump(queued, True, grounded, auto_hop))
            if any(e[0] == "jump" for e in world.events):
                jumps += 1
                if not grounded:
                    airborne += 1
            world.events.clear()
        return jumps, airborne

    def test_holding_jump_keeps_hopping(self):
        jumps, airborne = self._hold_jump(auto_hop=True)
        self.assertGreater(jumps, 3)            # it bounces every time it lands
        self.assertEqual(airborne, 0)           # and never starts one in mid-air

    def test_hopping_can_be_turned_off(self):
        jumps, _ = self._hold_jump(auto_hop=False)
        self.assertEqual(jumps, 0)              # then only a fresh press jumps

    def test_a_press_still_jumps_once(self):
        self.assertTrue(wants_jump(True, False, True, True))
        self.assertTrue(wants_jump(True, False, False, True))    # buffered / coyote press
        self.assertFalse(wants_jump(False, True, False, True))   # held, but in mid-air
        self.assertTrue(wants_jump(False, True, True, True))     # held, and standing


class TestNewMechanics(unittest.TestCase):
    def test_crawler_can_be_stomped(self):
        world = make_level(["............", "..P.....e...", "############"])
        run(world, 0.2)
        # drop the player straight onto the crawler
        crawler = world.enemies[0]
        world.player.x, world.player.y = crawler.x, crawler.y - 120
        world.player.vy = 400
        run(world, 0.6)
        self.assertFalse(crawler.alive)
        self.assertEqual(world.state, "play")

    def test_walking_into_a_crawler_kills(self):
        world = make_level(["..P......e..", "############"])
        run(world, 3, move=1)
        self.assertEqual(world.death_cause, "enemy")

    def test_spike_crawler_cannot_be_stomped(self):
        world = make_level(["............", "..P.....S...", "############"])
        run(world, 0.2)
        crawler = world.enemies[0]
        world.player.x, world.player.y = crawler.x, crawler.y - 120
        world.player.vy = 400
        run(world, 0.6)
        self.assertEqual(world.death_cause, "spike")

    def test_crawler_turns_at_ledges(self):
        world = make_level(["..P....e......", "###..######..."])
        run(world, 4)
        crawler = world.enemies[0]
        self.assertTrue(crawler.alive)
        self.assertTrue(5 * TILE <= crawler.x <= 11 * TILE)

    def test_mimic_jumps_when_you_jump(self):
        world = make_level(["..P......m..", "############"])
        run(world, 0.3)
        mimic = world.enemies[0]
        start_y = mimic.y
        world.step(FIXED_DT, 0, True, True)
        run(world, 0.15, jump=True)
        self.assertLess(mimic.y, start_y - TILE)

    def test_sentry_shoots_at_you(self):
        world = make_level(["........o...", "............", "..P.........", "############"])
        run(world, 2.5)
        self.assertEqual(world.death_cause, "orb")

    def test_laser_only_hurts_when_firing(self):
        # beam fires straight down through the player's column
        world = make_level(["....#.......", "............", "............", "..P.........", "############"],
                           lasers=[LaserDef(4, 14, 0, 1, on=1.0, off=1.0)])
        world.player.x = 4 * TILE + 7
        run(world, 0.5)
        self.assertEqual(world.state, "play")            # still in the "off" part of the cycle
        run(world, 1.0)
        self.assertEqual(world.death_cause, "laser")

    def test_cannon_fires_on_a_beat(self):
        world = make_level(["..P........#", "############"], cannons=[CannonDef(10, 16, -1, 0, period=1.0, speed=8)])
        run(world, 3)
        self.assertEqual(world.death_cause, "orb")

    def test_flip_blocks_swap_when_you_jump(self):
        world = make_level(["............", "..P...RU....", "############"])
        red = next(b for b in world.blocks if b.colour == "red")
        blue = next(b for b in world.blocks if b.colour == "blue")
        self.assertTrue(red.solid and not blue.solid)
        run(world, 0.2)
        run(world, 0.1, jump=True)
        self.assertTrue(blue.solid and not red.solid)

    def test_switch_block_never_traps_you(self):
        world = make_level(["............", "............", "..PU........", "############"])
        blue = world.blocks[0]
        world.player.x = blue.rect.x + 4          # stand inside the (ghost) blue block
        run(world, 0.2)
        world.step(FIXED_DT, 0, True, True)       # jumping turns blue on...
        self.assertTrue(blue.on)
        self.assertFalse(blue.solid)              # ...but it waits until we're out of it
        run(world, 1.0, jump=True)
        self.assertEqual(world.state, "play")
        self.assertTrue(blue.solid)
        self.assertFalse(blue.rect.colliderect(world.player.rect))

    def test_blink_blocks_take_turns(self):
        world = make_level(["............", "..P...TY....", "############"], blink_period=0.5)
        a = next(b for b in world.blocks if b.phase == 0)
        b = next(b for b in world.blocks if b.phase == 1)
        run(world, 0.2)
        first = (a.solid, b.solid)
        run(world, 0.5)
        self.assertEqual((a.solid, b.solid), (first[1], first[0]))

    def test_conveyor_drags_you(self):
        world = make_level(["..P.........", "#}}}}}}}}}}#"])
        start = world.player.x
        run(world, 1.0)
        self.assertGreater(world.player.x, start + 2 * TILE)

    def test_ice_keeps_you_sliding(self):
        slides = []
        for floor in ("IIIIIIIIIIIIIIIIIIIIIIIIIIIIII", "##############################"):
            w = make_level(["..P" + "." * 27, floor])
            run(w, 1.5, move=1)                  # get up to full speed
            start = w.player.x
            run(w, 1.0, move=0)                  # let go
            slides.append(w.player.x - start)
        self.assertGreater(slides[0], slides[1] + 2 * TILE)

    def test_updraft_carries_you_up(self):
        world = make_level(["............", "............", "..P.........", "###.........", "............"],
                           winds=[WindDef((3, 0, 9, 18), fy=-150)])
        run(world, 1.2, move=1)                 # walk off the ledge into the updraft
        self.assertEqual(world.state, "play")
        self.assertLess(world.player.vy, 0)     # being carried upwards, not falling

    def test_wind_pushes_you(self):
        world = make_level(["..P.........", "############"], winds=[WindDef((0, 0, 12, 18), fx=-250)])
        start = world.player.x
        run(world, 1.0, move=1)
        self.assertLess(world.player.x, start + 2 * TILE)

    def test_door_is_locked_until_you_have_the_key(self):
        world = make_level(["..P.G.......k", "#############"])
        run(world, 1.0, move=1)
        self.assertEqual(world.state, "play")          # walked straight through the locked door
        run(world, 2.0, move=1)
        self.assertTrue(world.has_key)
        run(world, 3.0, move=-1)
        self.assertEqual(world.state, "won")

    def test_echo_replays_your_moves_and_kills(self):
        world = make_level(["..P.............", "################"],
                           triggers=[Trigger((0, 0, 16, 18), [("echo", 0.5)])])
        run(world, 1.0, move=1)
        run(world, 1.5, move=0)          # stand still: your shadow walks into you
        self.assertEqual(world.death_cause, "echo")


class TestSaveAndUtils(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "save.json")

    def test_progress_roundtrip(self):
        save = SaveManager(10, path=self.path)
        save.record_death(1)
        save.record_clear(1, 12.5, 1)
        again = SaveManager(10, path=self.path)
        self.assertTrue(again.is_unlocked(2))
        self.assertFalse(again.is_unlocked(3))
        self.assertEqual(again.level_stats(1)["best_time"], 12.5)
        self.assertEqual(again.data["total_deaths"], 1)

    def test_old_save_is_migrated(self):
        with open(self.path, "w") as f:
            json.dump({"total_deaths": 649, "unlocked_level": 999, "rage_meter": 100, "unlock_all": True}, f)
        save = SaveManager(10, path=self.path)
        self.assertEqual(save.data["total_deaths"], 649)
        self.assertFalse(save.is_unlocked(2))   # the old 'unlock everything' flag is gone

    def test_corrupt_save_does_not_crash(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        save = SaveManager(10, path=self.path)
        self.assertEqual(save.data["total_deaths"], 0)

    def test_ranks_and_time_format(self):
        self.assertEqual(rank_for_deaths(0)[0], "S")
        self.assertEqual(rank_for_deaths(500)[0], "F")
        self.assertEqual(format_time(83.456), "1:23.46")


if __name__ == "__main__":
    unittest.main()
