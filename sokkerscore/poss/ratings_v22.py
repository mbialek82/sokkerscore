"""ratings_v22.py — v22: same as v21 but imports ratings_v16 FIRST. v21 imported ratings_v14 before the v16 module aliases were
set, so the old pre-annotation detectors (tackles_v5, match_stats_v3, interceptions_v2, duels_v1) were loaded and used:
59% of ratings moved, e.g. Konev 7.5 -> 8.4 from changed tackle counts. Retrained xG/xA unchanged.
ratings_v21.py — v21 (6 Nov 2026, the owner): xG / xA inside the rating (big chances, BCM/BCC, xA weight) now come from
category models trained on season-78 Ekstraklasa PLUS 39 newer matches (Team Z season 79 league and cups, two older cup
matches, Poland and Argentina national-team matches): sokker_158 shots_train_v2.json / keypasses_train_v2.json. The two
mismatches Kajoza 0:51 and ZUCH 0:23 are left out of training (52% shot conversion vs 25%). Rating formula unchanged
from ratings_v20."""
import sys, json
for p in ('./poss', './xg134', './xa135'): sys.path.insert(0, p)
import ratings_v16  # noqa: F401  (sets the detector-module aliases; must come before ratings_v14)
import ratings_v14 as _r14, xg_model_v1 as XG, xa_model_v1 as XA
SHOTS, KPS = './xg158/shots_train_v2.json', './xg158/keypasses_train_v2.json'
_r14._MX = XG.CategoryXG(MIN=20).fit(json.load(open(SHOTS)))
_r14._MA = XA.CategoryXA(MIN=20).fit(json.load(open(KPS)))
from ratings_v20 import *          # noqa
from ratings_v20 import rate        # noqa
