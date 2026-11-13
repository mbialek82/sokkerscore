"""ratings_v25.py — v25 (7 Nov 2026, the owner, decision 8): long balls from match_stats_v8 — a completed long ball (+0.03) must be a 30 m+ pass that goes forward by >= 10 m and is neither a kick-off nor a goal kick (first touch inside the own goal area). Models and everything else as v24; v20's rate() is inlined here with match_stats_v8.
ratings_v24.py — v24 (7 Nov 2026, the owner): xG category bins need 40 shots instead of 20 (XG_MIN); held-out log-loss 0.4635 vs 0.4732 and far steadier across shuffles. xA likewise 40 key passes per bin (0.4652 -> 0.4555). Training data (v3) and formula unchanged.
ratings_v23.py — v23 (7 Nov 2026, the owner: retrain on all levels): xG / xA category models fitted on sokker_161 shots_train_v3 / keypasses_train_v3 = v2 + 1,713 shots / 1,208 key passes from Polish divisions 2–6, Ekstraklasa S77, four foreign top divisions and five national teams (blowouts with a team scoring 8+ excluded). Match-grouped CV log-loss 0.4728 -> 0.4663 (xG), 0.477 -> 0.457 (xA). Formula and detectors unchanged.
ratings_v22.py — v22: same as v21 but imports ratings_v16 FIRST. v21 imported ratings_v14 before the v16 module aliases were
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
SHOTS, KPS = './xg158/shots_train_v3.json', './xg158/keypasses_train_v3.json'
XG_MIN, XA_MIN = 40, 40   # v24: a bin needs 40 shots / 40 key passes (was 20)
_r14._MX = XG.CategoryXG(MIN=XG_MIN).fit(json.load(open(SHOTS)))
_r14._MA = XA.CategoryXA(MIN=XA_MIN).fit(json.load(open(KPS)))
import sys
for p in ('./poss', './shots', './def', './pen152'): sys.path.insert(0, p)
from decimal import Decimal, ROUND_HALF_UP
from ratings_v16 import rate as rate16
from strikes_v2 import load
from shot_analysis_v17 import occupancy
from penalties_v1 import penalties
import match_stats_v8 as match_stats_v5

RED_PER_MIN, PEN_MISS, LONG_BALL = -0.05, -0.5, 0.03

def rate(path):
    M = load(path); who, _ = occupancy(M)
    red = {}; red2y = {}; miss = {}
    for t, J, p in M['ev']:
        if J in (8, 9):
            n = who(p[0], t); red.setdefault(n, []).append(M['minute'](t))
            if J == 9: red2y[n] = red2y.get(n, 0) + 1
    for e in penalties(path, M):
        if e['outcome'] != 'goal': miss[e['taker']] = miss.get(e['taker'], 0) + 1
    lb = {x['name']: (x['long_acc'], x['long_att']) for x in match_stats_v5.match_stats(path)[1]}
    out = []
    for r in rate16(path):
        n = r['name']; rp = round(sum(RED_PER_MIN * (90 - m) for m in red.get(n, [])), 3); pm = round(PEN_MISS * miss.get(n, 0), 3)
        la, lt = lb.get(n, (0, 0)); lbp = round(LONG_BALL * la, 3)
        raw = round(r['raw'] + rp + pm + lbp, 6)
        rating = float(Decimal(str(max(3.0, min(10.0, raw)))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        out.append(dict(r, raw=raw, rating=rating, rating_v16=r['rating'], red_pen=rp, pen_miss_pen=pm,
                        long_acc=la, long_att=lt, long_pen=lbp, reds=len(red.get(n, [])), red2y=red2y.get(n, 0), red_minutes=red.get(n, []), pen_misses=miss.get(n, 0)))
    return sorted(out, key=lambda x: (x['team'], -x['rating']))
