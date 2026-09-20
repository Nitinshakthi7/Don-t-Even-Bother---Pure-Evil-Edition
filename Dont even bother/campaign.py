# I am adding comments for me to easily understand the codes
# campaign.py - every level in the game, in order, across all three acts.
#
#   Act I   (levels 1-10)   levels.py   hand-drawn troll levels
#   Act II  (levels 11-18)  act2.py     long gauntlet runs built from chunks
#   Act III (level 19)      act3.py     the vertical Climb

from levels import LEVELS as ACT1
from act2 import ACT2
from act3 import ACT3

LEVELS = ACT1 + ACT2 + ACT3

for _i, _level in enumerate(LEVELS, start=1):
    assert _level.number == _i, f"level numbers must run 1..N in order (found {_level.number} at {_i})"
