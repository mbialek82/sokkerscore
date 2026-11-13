"""ratings_v15.py — v15 (30 Oct): shots from shot_analysis_v17 (3-D dead-ball check; Kupecký 79' in 44496766 saved, not
woodwork, so Czerbniak's goal is a rebound with no assist). Every detector that imports shot_analysis_v10..v16 is routed to
v17. Weights = ratings_v14 (BCM -0.25, BCC +0.15, xA +0.5 per unit, big chance xG >= 0.25)."""
import sys
sys.path.insert(0, './poss'); sys.path.insert(0, './shots')
import shot_analysis_v17 as _sa
for _n in ('shot_analysis_v10', 'shot_analysis_v11', 'shot_analysis_v12', 'shot_analysis_v13', 'shot_analysis_v14',
           'shot_analysis_v15', 'shot_analysis_v16'): sys.modules[_n] = _sa
from ratings_v14 import rate, chances, BIG_XG, W_BIG  # noqa
