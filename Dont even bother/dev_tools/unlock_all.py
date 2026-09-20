# dev_tools/unlock_all.py - unlock things in YOUR local save, for testing.
#
# Only touches rage_save.json, which is git-ignored, so nothing here ever
# reaches the repo.
#
#   python dev_tools/unlock_all.py            every level, both modes
#   python dev_tools/unlock_all.py --brutal   Brutal only
#   python dev_tools/unlock_all.py --all      levels, skins, awards and spite
#   python dev_tools/unlock_all.py --lock     put the levels back to level 1
#
# --all marks every level as completed, which is how Race the Bot decides what
# you may race. That overwrites real progress, so it takes a backup first and
# tells you where it put it.

import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import achievements                 # noqa: E402
import cosmetics                    # noqa: E402
from campaign import LEVELS         # noqa: E402
from utils import SaveManager       # noqa: E402

MODES = ("normal", "brutal")


def back_up(path):
    if not os.path.exists(path):
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    copy = f"{os.path.splitext(path)[0]}.backup-{stamp}.json"
    shutil.copy2(path, copy)
    return copy


def unlock_everything(save):
    """Levels, skins, awards and a pile of spite - the lot, for testing."""
    for mode in MODES:
        save.data["modes"][mode]["unlocked"] = len(LEVELS)
        for level in LEVELS:
            stats = save.level_stats(level.number, mode)
            stats["completed"] = True
        save.data["modes"][mode]["completed"] = True
    save.data["spite"] = max(save.spite, 9999)
    save.data["cosmetics"]["unlocked"] = [skin.id for skin in cosmetics.SKINS]
    for award in achievements.ACHIEVEMENTS:
        save.data["achievements"][award.id] = True
    save.dirty = True


def main():
    parser = argparse.ArgumentParser(description="Unlock things in your local save.")
    parser.add_argument("--normal", action="store_true", help="only the Normal campaign")
    parser.add_argument("--brutal", action="store_true", help="only the Brutal campaign")
    parser.add_argument("--all", action="store_true",
                        help="levels, skins, awards and spite (overwrites progress)")
    parser.add_argument("--lock", action="store_true", help="lock the levels back to level 1")
    args = parser.parse_args()

    save = SaveManager(len(LEVELS))
    if args.all:
        copy = back_up(save.path)
        if copy:
            print(f"backed up your save to: {copy}")
        unlock_everything(save)
    else:
        modes = [m for m, on in (("normal", args.normal), ("brutal", args.brutal)) if on] or list(MODES)
        for mode in modes:
            save.data["modes"][mode]["unlocked"] = 1 if args.lock else len(LEVELS)
    save.save()

    print(f"save: {save.path}")
    for mode in MODES:
        print(f"  {mode:>6}: {save.data['modes'][mode]['unlocked']} / {len(LEVELS)} levels unlocked")
    if args.all:
        cleared = sum(1 for level in LEVELS
                      if save.level_stats(level.number, "brutal")["completed"])
        print(f"  levels marked cleared: {cleared} / {len(LEVELS)} per mode")
        print(f"  skins:  {len(save.data['cosmetics']['unlocked'])} / {len(cosmetics.SKINS)}")
        print(f"  awards: {len(save.data['achievements'])} / {len(achievements.ACHIEVEMENTS)}")
        print(f"  spite:  {save.spite}")
        print("  ghost races are left alone - go and actually beat the bot")
    print(f"  lifetime deaths kept: {save.data['total_deaths']}")


if __name__ == "__main__":
    main()
