"""shot_analysis_v10.py — WORKING SHIM: re-exports shot_analysis_v11. v11 differs from v10 only in the offside weight and the
rounding of ratings; analyse()/occupancy() are identical, which is all that match_stats_v3, dribbles_v2 and tackles use.
The real v10 is in the project (sokker_124/shot_analysis_v10.py)."""
import sys
sys.path.insert(0, './shots')
from shot_analysis_v11 import *  # noqa
from shot_analysis_v11 import occupancy, analyse, ratings  # noqa
