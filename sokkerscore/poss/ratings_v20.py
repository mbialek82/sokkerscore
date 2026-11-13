"""ratings_v20.py — v20: long balls from match_stats_v6 (kick-offs excluded).
ratings_v19.py — v19 (6 Nov 2026, the owner): + LONG_BALL = +0.03 per completed long ball (pass of 30 m+ reaching a team-mate,
match_stats_v5). Failed long balls only count in pass accuracy, as before. Adds long_acc / long_att to every row.
ratings_v18.py — v18 (4 Nov 2026): same red-card / penalty-miss penalties as ratings_v17 (unchanged formula), but
now also reports `red2y` — how many of a player's reds came from a 2nd yellow (Score-tab YELLOW_SECOND, J=9) rather
than a straight red (J=8) — so the page can draw the "yellow peeking out behind the red" icon only for that case.
`reds`/`red_pen`/`red_minutes` still cover both kinds together, unchanged from v17."""
import sys
for p in ('./poss', './shots', './def', './pen152'): sys.path.insert(0, p)
from decimal import Decimal, ROUND_HALF_UP
from ratings_v16 import rate as rate16
from strikes_v2 import load
from shot_analysis_v17 import occupancy
from penalties_v1 import penalties
import match_stats_v6 as match_stats_v5

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
