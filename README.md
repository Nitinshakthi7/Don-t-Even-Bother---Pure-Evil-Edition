# Don't Even Bother: Pure Evil Edition

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Pygame](https://img.shields.io/badge/pygame-2.1+-green.svg)](https://www.pygame.org/)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red.svg)](LICENSE)

> A merciless troll-platformer where the floor lies, the doors lie, and the narrator definitely lies.
> Every level is beatable. We have a robot that proves it, in both difficulties.

You're a small marshmallow in a red scarf. You want to reach the door. The game doesn't want you to.
There are 19 levels across three acts. Every trap is **deterministic**: it happens the same way on
every attempt. You can learn it, and it will still get you the first time.

A game by **Nitin M** (LazyHunter7).

## The campaign

| Act | Levels | What it is |
|---|---|---|
| **I: The Warm-Up** | 1–10 | Hand-built troll levels. Hard, but you'll get through. |
| **II: The Gauntlet** | 11–18 | Long Geometry Dash-style runs, 160–300+ tiles each. This is where you regret it. |
| **III: The Climb** | 19 | A 134-tile vertical tower in the spirit of Only Up. Falling doesn't kill you. It just drops you back down. |

Act I teaches you the traps. Act II adds things that move on their own and things that
aim at you. Act III stacks all of it into one tower with nothing underneath it.

### Difficulty

When you start, you pick **Normal** or **Brutal**. The game will judge you for picking Normal.
A third card, **Story Mode**, sits next to them marked COMING SOON - the story is still being written.

| | Normal | Brutal |
|---|---|---|
| Checkpoints | Yes | **None, anywhere.** In the Climb, any death sends you back to the bottom. |
| Extra traps | – | Every level gets extra hidden spikes, fake blocks and arrows |
| Saws, arrows, crushers | Normal speed | 25–30% faster |
| Creatures | Normal speed | 30% faster |
| Turrets, cannons, lasers | Normal rate | Fire 30% more often |
| Crumbling floors | 0.45 s | 0.29 s |
| Hidden-spike trigger range | Normal | 1.5× wider |
| Jump forgiveness | Generous | Minimal |

Progress is saved separately for each mode.

## Features

- **Traps:**
  - hidden spikes
  - fake ground
  - crumbling floors
  - invisible blocks you bonk your head on
  - thwomps and crushers
  - moving platforms
  - rising spike floors
  - arrow volleys
  - saws that burst out of the ground
  - fake walls
  - fake doors (with a sad trombone)
  - a door that runs away from you
  - reversed controls
  - lights-out sections
- **Creatures** (they move; the spikes never did):
  - **crawlers** patrol a ledge and turn at walls and drops - stomp them, or die touching them
  - **spike-backed crawlers** punish you for learning to stomp
  - **mimics** jump exactly when you jump, so you have to make them leap and run under
  - **swoopers** hang from ceilings and dive at the spot you were standing in
  - **sentries** track you and fire aimed orbs, with a wind-up you can read
  - **echoes** - a shadow that replays your own last few seconds and chases you with it
- **Machines:**
  - **lasers** that warn, flicker, then fire in rolling waves
  - **ceiling cannons** dropping heavy balls on a beat
  - **blink blocks** that flash in and out in alternating groups
  - **flip blocks** - red and blue platforms swap every single time you jump
  - **switch blocks** that toggle when you hit a switch (and never close on you while you stand there)
  - **conveyors** dragging you back towards what you just escaped
  - **ice** you cannot stop on
  - **updrafts** that carry you over pits too wide to jump
  - **keys and locked doors**
- **A narrator who remembers:**
  - taunts depend on how you died
  - it notices when you die on the same spot again ("Third time. Same spot.")
  - it greets you back to levels you've failed a lot
  - it has different insults for Normal and Brutal players
- **Streamer mode:** big on-screen stats (total deaths, session deaths, all-time deaths on this level). The Climb also shows an altitude meter with your deaths marked on it.
- **Movement:**
  - fixed 120 Hz deterministic physics
  - coyote time, jump buffering and variable jump height
  - hold-to-hop: keep jump held and you bounce again on every landing (toggleable in Settings)
  - squash & stretch
- **Game feel:** hit-stop and screen shake on death, blood that stains the level, and death markers.
- **Full front-end:**
  - the "I dare you" difficulty screen
  - act title cards
  - act-based level select with ranks and best times
  - pause and settings menus
  - ending credits (which mock you if you finished on Normal)
- **No asset files.** Every graphic, sound effect and all five music tracks are generated procedurally at startup.
- **Input and display:** keyboard, mouse and gamepad; any screen size.

## Controls

| Action | Keyboard | Gamepad |
|---|---|---|
| Move | `A` `D` / `←` `→` | Left stick / D-pad |
| Jump (hold for higher) | `Space` / `W` / `↑` / `Z` | A |
| Keep hopping | hold jump - it re-jumps the moment you land (never a mid-air double jump) | A (hold) |
| Restart from checkpoint | `R` | Y |
| Pause | `Esc` / `P` | Start |
| Fullscreen | `F11` / `Alt+Enter` | – |

## Running it

```bash
pip install -r "Dont even bother/requirements.txt"
cd "Dont even bother"
python main.py
```

Command-line options:

- `--windowed`: start in a window instead of fullscreen.
- `--level N`: jump straight into level N.
- `--unlock-all`: unlock every level.
- `--brutal`: start in Brutal mode.

`numpy` is optional. It powers the synthesized audio; without it the game runs silently.

## How it's built (OOP overview)

```
main.py        Game: window, main loop, owns every manager
scenes.py      Scene (base) → SplashScene, TitleScene, DifficultyScene, ActCardScene, LevelSelectScene,
               SettingsScene, CreditsScene, GameScene; SceneManager handles fades and stacking
world.py       World: the pure rules of one level for one difficulty (no drawing, no sound).
               It emits events like "jump", "death" and "crumble" that GameScene turns into juice.
               Static objects are kept in spatial buckets so 300-tile levels stay fast.
traps.py       Entity (abstract)
               ├─ Block ─ CrumbleBlock ─ FakeBlock
               │        └ InvisibleBlock
               ├─ Hazard (abstract) ─ Spike ─ HiddenSpike
               │                    ├ Saw
               │                    └ Arrow
               ├─ Spring, Checkpoint
               └─ Door ─ FakeDoor
               Group: named set of blocks/spikes that level scripts can drop, move or reveal
player.py      Player: movement feel (coyote time, buffering, variable jump) + drawing
levels.py      LevelDef / Trigger / SawDef data classes, Act I maps and their Brutal overlays
builder.py     Chunk + build_horizontal / build_vertical: glue small obstacle chunks into long levels
act2.py        the chunk library and the eight Gauntlet runs
act3.py        the Climb, stacked from vertical chunks
campaign.py    all 19 levels in order
renderer.py    WorldRenderer: paged tile layers, stains, darkness, vertical parallax
graphics.py    Procedural art: tiles, spikes, saws, doors, backgrounds, fonts, icons
audio.py       Procedural synth: sound effects and five music tracks built with numpy
particles.py   ParticleSystem (dust, sparks, bouncing debris, staining blood), AmbientField
ui.py          Menu / MenuItem widgets (buttons, sliders, toggles; keys, mouse, pad)
controls.py    Maps keyboard and gamepad input to actions
utils.py       SaveManager (per-difficulty progress, atomic saves, migration), Camera (2D follow, shake)
```

### Making levels

- **Act I levels** are ASCII maps in `levels.py`, with a scripting layer. The legend is documented at the top of the file.
- **Brutal versions** are overlays: `edits={"brutal": [(col, row, "text")]}`, plus `brutal_triggers` and `brutal_saws`.
- **Long levels** are lists of chunks (see `act2.py`):

```python
build_horizontal(12, "Saw Mill", "EVERYTHING SPINS.", "foundry", [
    start(), saw_runner(4.5), pit_saw(4), saw_ceiling_run(), rest(), ..., finish(),
])
```

Each chunk keeps its own triggers and trap groups. The builder moves them into place and gives every chunk private copies, so reusing a chunk twice just works.

## Quality assurance

```bash
cd "Dont even bother"
python -m unittest discover tests                    # physics, traps, saves, level data, all replays
python dev_tools/level_solver.py                     # the bot plays every level on Normal
python dev_tools/level_solver.py --brutal            # ...and on Brutal
python dev_tools/level_solver.py --verify --brutal   # re-check the saved winning replays
python dev_tools/render_replay.py 18 --brutal        # turn a winning run into a GIF
python dev_tools/make_uml.py                         # redraw the class diagram (needs matplotlib)
```

Because the simulation is deterministic, the solver searches the real game with best-first (A*-style) search. It saves each winning input sequence to `dev_tools/solutions/<difficulty>/`, and the tests replay every one of them. Long levels give the bot route hints at the end of each chunk.

## License

All rights reserved. This code is proprietary - see [LICENSE](LICENSE).
It is shared for viewing and assessment only, and may not be reused or redistributed.
