"""ratings_v16.py — v16 (31 Oct, sokker_145: fixes from the owner's action-by-action annotation of 44496766, 0:00-20:30).
Routes the detectors to their new versions; weights unchanged (= ratings_v15 / v14):
  match_stats_v4  — passes between team-mates from 1 m; dispossessed vs unsuccessful touch by opponent proximity (3 m);
  tackles_v6      — first-touch losses to a close opponent are tackles; slide tackles from 3.5 m with contact within 3.5 m;
  interceptions_v3 — contested headers (ball >= 2 m, receiver within 3 m) are aerial duels; a carried ball taken off the
                    carrier is not an interception;
  duels_v2        — aerial duels from 2.5 m; no duel within 15 ticks of a tackle / dribble / interception / foul.
Score on the annotation: 87 -> 99 of 131 events right; the 19 Oct verdicts (tackles 19/19, interceptions 6/6, duels 6/6) hold."""
import sys
for p in ('./poss', './shots', './def', './int130', './du132'): sys.path.insert(0, p)
import match_stats_v4, tackles_v6, interceptions_v3, duels_v2
sys.modules['match_stats_v3'] = match_stats_v4; sys.modules['tackles_v5'] = tackles_v6
sys.modules['interceptions_v2'] = interceptions_v3; sys.modules['duels_v1'] = duels_v2
from ratings_v15 import rate, chances, BIG_XG, W_BIG  # noqa
