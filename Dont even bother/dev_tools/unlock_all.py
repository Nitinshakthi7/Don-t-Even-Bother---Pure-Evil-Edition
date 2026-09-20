# dev_tools/unlock_all.py - unlock every level in YOUR local save.
# Only touches rage_save.json, which is git-ignored, so nothing here ever
# reaches the repo. Your deaths, best times and settings are kept.
#
#   python dev_tools/unlock_all.py            unlock both modes
#   python dev_tools/unlock_all.py --brutal   unlock Brutal only
#   python dev_tools/unlock_all.py --lock     put it back to level 1

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign import LEVELS          # noqa: E402
from utils import SaveManager        # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Unlock every level in your local save.")
    parser.add_argument("--normal", action="store_true", help="only the Normal campaign")
    parser.add_argument("--brutal", action="store_true", help="only the Brutal campaign")
    parser.add_argument("--lock", action="store_true", help="lock everything back to level 1")
    args = parser.parse_args()

    modes = [m for m, on in (("normal", args.normal), ("brutal", args.brutal)) if on] or ["normal", "brutal"]
    save = SaveManager(len(LEVELS))
    for mode in modes:
        save.data["modes"][mode]["unlocked"] = 1 if args.lock else len(LEVELS)
    save.save()

    print(f"save: {save.path}")
    for mode in ("normal", "brutal"):
        print(f"  {mode:>6}: {save.data['modes'][mode]['unlocked']} / {len(LEVELS)} unlocked")
    print(f"  lifetime deaths kept: {save.data['total_deaths']}")


if __name__ == "__main__":
    main()
