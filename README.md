# Don't Even Bother: Pure Evil Edition

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Pygame](https://img.shields.io/badge/pygame-2.6-green.svg)](https://www.pygame.org/)
[![Tests](https://img.shields.io/badge/tests-84%20passing-brightgreen.svg)](#quality-assurance)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red.svg)](LICENSE)

> A merciless troll-platformer where the floor lies, the doors lie, and the narrator definitely lies.
> Every level is beatable. There is a bot that proves it, in both difficulties, and you can race it.

You are a small marshmallow in a scarf. You want to reach the door. The game does not want you to.

Nineteen levels across three acts, two difficulties, and a narrator that remembers how you died and
where. Every trap is **deterministic** — it happens the same way on every attempt, so you can learn it,
and it will still get you the first time.

A game by **Nitin M** (LazyHunter7).

---

## Quick start

```bash
pip install -r "Dont even bother/requirements.txt"
cd "Dont even bother"
python main.py
```

`numpy` is optional: it powers the synthesized audio, and without it the game runs silently.

| Flag | Effect |
| --- | --- |
| `--windowed` | Start in a window instead of fullscreen |
| `--level N` | Jump straight into level N |
| `--brutal` | Start in Brutal mode |
| `--unlock-all` | Unlock every level for this run |
| `--demo` | Autoplay a level from a verified solver replay |

---

## The campaign

| Act | Levels | What it is |
| --- | --- | --- |
| **I — The Warm-Up** | 1–10 | Hand-built troll levels, 40–72 tiles wide. Hard, but you will get through. |
| **II — The Gauntlet** | 11–18 | Endurance runs, 207–461 tiles. This is where you regret it. |
| **III — The Climb** | 19 | A 208-tile vertical tower. Falling does not kill you; it drops you back down, which is worse. |

Act I teaches you the traps. Act II adds things that move on their own and things that aim at you.
Act III stacks all of it into one tower with nothing underneath it.

### Three ways to play

| Mode | What it is |
| --- | --- |
| **Campaign** | The 19 levels, in order, with checkpoints on Normal |
| **Race the Bot** | The solver's verified run, replayed live beside you as a ghost. Beat its time |
| **Story Mode** | Coming soon |

### Normal or Brutal

The mode screen is an ego trap: Normal is small and grey, Brutal is large, red and pulsing, and the
narrator judges whichever one you hover. Progress is stored separately for each.

| Rule | Normal | Brutal |
| --- | --- | --- |
| Checkpoints | Yes | **None, anywhere.** In the Climb, any death sends you to the bottom |
| Extra traps | – | Every level gets extra hidden spikes, fake blocks, arrows and creatures |
| Saws, arrows, crushers | ×1.0 | ×1.25–1.3 |
| Creatures | ×1.0 | ×1.3 |
| Turrets, cannons, lasers | ×1.0 | fire 30% more often |
| Cracked floors | 0.45 s | 0.29 s |
| Hidden-spike range | ×1.0 | ×1.5 |
| Coyote time | 0.09 s | 0.05 s |
| Jump buffer | 0.12 s | 0.07 s |

The coyote and buffer cuts matter more than any speed multiplier: they remove the invisible forgiveness
that makes platformers feel good, so Brutal jumps that *should* have worked simply do not.

---

## The things that kill you

### Traps

| Trap | Behaviour |
| --- | --- |
| Hidden spike | Invisible until you walk within 0.6 tiles, then pops up |
| Cracked block | Falls 0.45 s after you stand on it |
| Fake block | Looks exactly like ground, drops in 0.16 s |
| Invisible block | Nothing there until you hit it from below |
| Fake wall | Looks solid, you walk straight through |
| Fake door | The exit, except it kills you and plays a sad trombone |
| Runaway door | The real exit relocates as you approach |
| Crusher, rising spike floor, moving platform | Groups of blocks under trigger control |
| Reversed controls, lights out | For a whole section |

### Creatures

| Creature | Behaviour | What it tests |
| --- | --- | --- |
| **Crawler** | Patrols a ledge, turns at walls and drops. Stompable | Timing a landing |
| **Spike crawler** | The same, but spiked — stomping kills you | Unlearning the habit you just built |
| **Mimic** | Jumps exactly when you jump | Making it leap, then running underneath |
| **Swooper** | Hangs from ceilings, dives at where you were standing | Moving before it commits |
| **Sentry** | Tracks you and fires aimed orbs, with a readable wind-up | Staying unpredictable |
| **Echo** | A shadow replaying your own last few seconds, chasing you | Not hesitating |

### Machines

| Machine | Behaviour |
| --- | --- |
| **Laser** | Off → warning flicker → firing, placed in rolling waves |
| **Cannon** | Ceiling-mounted, drops heavy orbs on a beat |
| **Blink block** | Two groups alternating on a 1.3 s beat |
| **Flip block** | Red and blue swap every single time you jump |
| **Conveyor** | Drags you back toward what you just escaped |
| **Ice** | Grip drops to 0.08 — you will not stop in time |
| **Updraft** | Carries you up, over gaps too wide to jump |
| **Key and locked door** | The exit will not open until you have fetched the key |

---

## The narrator

It does not insult you at random; it notices things.

| Pool | Fires when |
| --- | --- |
| By cause of death | 11 causes: spike, saw, fall, crush, arrow, enemy, orb, laser, echo, fake door, hidden spike |
| Spot memory | You die in roughly the same place again — *"Third time. Same spot."* |
| Return lines | You come back to a level you have failed a lot |
| Mode taunts | Different insults for Normal and Brutal players |
| **By name** | If you told it your name — *"Nitin versus a rectangle. The rectangle is winning."* |

---

## Earning things

### Spite

Earned by playing, spent on cosmetics. It never touches the rules: nothing you buy makes a level easier.

| Source | Payout |
| --- | --- |
| First clear of a level | 25 |
| Clear with 3 deaths or fewer | +40 |
| Deathless clear | +100 |
| New personal best time | +15 |
| Finishing an act | 150 |
| Beating the bot in a race | 50 |
| Brutal mode | **×2 on everything** |
| Dying | 1, capped at 30 per session |

That cap is the important number. If dying paid well, the best strategy would be walking into a spike
for an hour, and the game would have been replaced by a slot machine.

### Fourteen characters

Not fourteen recolours. Each has its own corner shape (from a blocky ice cube to a pill), one of eleven
faces (tired, X-ed out, monocle, goggles, visor, ring, cyclops, angry…) and its own headgear (cap,
halo, horns, crown, top hat, flame, antenna…). Nine are earned, four are bought, one is free.

All of them are drawn inside the same 26×34 body the game collides with, so a costume never lies about
where you are.

### Twelve awards

Badges of suffering, most of which you get by accident rather than by grinding: dying to every cause,
falling for ten fake doors, clearing a level without dying, finishing Act I on Brutal, beating the bot.
Nine of them hand over a character.

---

## Controls

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| Move | `A` `D` / arrows | Left stick, D-pad |
| Jump (hold for higher) | `Space` / `W` / `Up` / `Z` | A |
| Keep hopping | hold jump — re-jumps on landing, never in mid-air | A (hold) |
| Restart from checkpoint | `R` | Y |
| Pause | `Esc` / `P` | Start |
| Skins / awards tabs | `Tab` | – |
| Fullscreen | `F11` / `Alt+Enter` | – |

---

## Built without a single asset file

There is no `.png`, `.wav` or `.ttf` in this project. Everything is generated at startup.

- **Graphics** — tiles drawn procedurally per theme with speckle and edge highlights, then cached to
  paged surfaces so a 461-tile level still blits in one pass. Seven themes, layered parallax
  backgrounds, ambient particle fields.
- **Audio** — sound effects synthesized with numpy, five music tracks built from generated waveforms.
- **Text** — pygame's built-in font rendering, so no font files ship either.

It started as a constraint and became the project's best feature: the repository is tiny, there are no
licensing questions, and a character is a few numbers rather than a sprite sheet.

---

## How it's built

The central decision: **the simulation knows nothing about presentation.** `World` runs the rules and
emits events; `GameScene` turns those events into particles, sound and screen shake. That split is what
makes the game deterministic, and determinism is what makes the solver bot possible.

![Class diagram](UML%20Diagram.png)

| Module | Lines | Responsibility |
| --- | --- | --- |
| `scenes.py` | 2181 | Every screen, the HUD, the per-frame game loop |
| `world.py` | 738 | The simulation: collision, triggers, deaths, events |
| `traps.py` | 647 | Block and hazard classes |
| `enemies.py` | 491 | Creatures, projectiles, lasers, cannons |
| `levels.py` | 386 | Act I maps, level dataclasses, the legend |
| `graphics.py` | 362 | Procedural tiles, text, backgrounds |
| `utils.py` | 358 | Camera, save manager, easing |
| `audio.py` | 349 | Synthesized effects and music |
| `act2.py` + `act3.py` | 544 | The Gauntlet's chunks and the Climb |
| `settings.py` | 299 | Every tunable constant and all taunt pools |
| `cosmetics.py` | 277 | Skins, and the one function that draws a character |
| `renderer.py` | 231 | Level drawing, paged tile caching |
| `ui.py` | 210 | Menu widgets |
| `player.py` | 200 | Movement, coyote time, jump buffering |
| `builder.py` | 179 | Assembles chunks into levels |
| `achievements.py` + `ghosts.py` + `economy.py` | 266 | Awards, the racing bot, payouts |

About **8,200 lines** of game code, plus 900 more in tests and tools.

### OOP structure

`Entity` is the abstract base; `Block` and `Hazard` derive from it, and specific traps derive from
those (`CrumbleBlock` → `FakeBlock`, `Spike` → `HiddenSpike`, `SwitchBlock` → `FlipBlock` /
`BlinkBlock`). Creatures follow the same pattern from `Enemy`. Levels are frozen dataclasses, so a
Brutal variant is produced by `replace()` with an overlay rather than by mutation.

### Making levels

Three layers, each suited to a different scale:

1. **ASCII maps** for Act I — one character per tile, 18 rows tall, readable and diffable.
2. **Triggers** — an area plus actions that run in order: move a group, fire an arrow, reverse the
   controls, kill the lights, spawn an echo. A trigger can be marked `grounded` so it only fires while
   the player is standing, because flipping someone's controls in mid-air is unfair rather than hard.
3. **Chunks** for Acts II and III — reusable sections assembled by `builder.py`, which offsets every
   trigger, saw, laser, cannon and wind area into place.

```python
build_horizontal(12, "Saw Mill", "EVERYTHING SPINS.", "foundry", [
    start(), saw_runner(4.5), pit_saw(4), saw_ceiling_run(), rest(), ..., finish(),
])
```

Brutal variants are overlays, not copies: `edits={"brutal": [(col, row, "text")]}`. One map, two
difficulties, nothing to keep in sync.

---

## Quality assurance

A game whose selling point is unfairness has to prove it is not broken. Four independent layers do that.

```bash
cd "Dont even bother"
python -m unittest discover tests                    # 84 tests
python dev_tools/level_solver.py                     # the bot plays every level on Normal
python dev_tools/level_solver.py --brutal            # ...and on Brutal
python dev_tools/level_solver.py --verify --brutal   # re-check the saved winning replays
python dev_tools/render_replay.py 18 --brutal        # turn a winning run into a GIF
python dev_tools/make_uml.py                         # redraw the class diagram (needs matplotlib)
python dev_tools/unlock_all.py --all                 # unlock everything in your local save
```

1. **Unit tests** — physics, every trap, creature behaviour, level data, save migration, the Climb's
   layout rule, the economy, skins, awards, and a replay of every saved solution.
2. **The solver bot** — because the simulation is deterministic, a best-first search can play the real
   game. Every winning input sequence is saved to `dev_tools/solutions/` and replayed by the tests, so
   a broken level fails a test instead of a player.
3. **Static audits** — nothing floating with no support, no creature spawned inside terrain, no door
   hanging off the top of the world.
4. **Invariant checks over replays** — the player never ends up inside a wall, no creature gets stuck,
   no projectile count runs away.

| Check | Result |
| --- | --- |
| Unit tests | 84 passing |
| Normal replays | 19 / 19 winning |
| Brutal replays | 19 / 19 winning |
| Geometry, creature and door audits | 0 problems |
| Invariants over all replays | 0 issues |

Every level has been beaten by a machine in both difficulties. The recordings ship with the game.

---

## License

All rights reserved. This code is proprietary — see [LICENSE](LICENSE). It is shared for viewing and
assessment only, and may not be reused or redistributed.
