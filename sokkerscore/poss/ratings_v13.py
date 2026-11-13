"""ratings_v13.py — v13 (30 Oct): shots from shot_analysis_v16 / shots_v9 (hard close-range strikes aimed at goal but deflected at once). Weights unchanged.
ratings_v12.py — v12 (20 Oct): shots from shot_analysis_v15 / shots_v8 (goals only from the Score tab, own goals, one shot per attempt, no long-range blocked shots, wide close-range shots). Weights unchanged.
ratings_v11.py — v11 (the owner, 19 Oct): fouled player = last opponent to touch the ball (blocks_fouled_v2); shots from
shot_analysis_v14 / shots_v7 (forward-speed floor, missed keeper parries; 43761572 and 44471278 unchanged).
Every detector that imports shot_analysis_v10/v11/v12/v13 is routed to v14 here, so all of them see the same shot list.
Weights unchanged.
ratings_v10.py — v10 (the owner, 19 Oct): duels (duels_v1, sokker_132): ground won +0.02 / lost -0.02, aerial won +0.05 / lost -0.05.
ratings_v9.py — v9 (the owner, 19 Oct): blocks +0.1, was fouled +0.05 (blocks_fouled_v1, sokker_131).
ratings_v8.py — v8 (the owner, 19 Oct): interceptions +0.05 (interceptions_v2, sokker_130); keeper goal conceded -0.15
(shot_analysis_v13).
ratings_v7.py — v7 (the owner, 19 Oct): pass standards lowered to 10 completed per 90 (scaled by minutes) and 70 % accuracy.
Slopes unchanged: volume +0.1 per 10 above / -0.2 per 10 below; accuracy +0.2 per 10 points above / -0.1 per 10 below.
ratings_v6.py — v6 (19 Oct): uses shot_analysis_v12 (Jańczak 73' assist override). Weights unchanged.
ratings_v5.py — v5 (the owner, 19 Oct): pass volume BELOW the default counts double: -0.2 per 10 completed under it
(above: still +0.1 per 10). 10 completed at 70 % for a 90-minute player is now -0.3 (was -0.2).
ratings_v4.py — v4 (the owner, 19 Oct): PASSES.
  Volume: default completed passes = minutes played / 90 x 20; +/-0.1 per 10 completed above/below (linear, continuous:
          30 -> +0.1, 60 -> +0.4, 10 -> -0.1 for a 90-minute player).
  Accuracy (completed / attempted, match_stats_v3): default 80 %; above it +0.2 per 10 points (90 % -> +0.2, 100 % -> +0.4),
          below it -0.1 per 10 points (70 % -> -0.1). Counts only if >= 4 completed passes OR >= 35 minutes played.
ratings_v3.py — v3 (the owner, 19 Oct): tackles added — tackle won +0.05, tackle failed -0.1 (tackles_v5, sokker_129).
A failed tackle = tackles - tackles won. Recoveries are not weighted.
ratings_v2.py — v2 (the owner, 19 Oct): successful dribble +0.1 (was +0.05), failed dribble -0.05 (was -0.02),
unsuccessful touch -0.05 added (match_stats_v3 'bad_touch').
ratings_v1.py — SokkerScore partial rating combining:
  shot_analysis_v11 (Score-tab + shot stats, offsides; sokker_124),
  dribbles_v2 (sokker_127): successful dribble +0.05, failed dribble -0.02 (the owner, 19 Oct),
  match_stats_v3 (sokker_125): dispossessed -0.05 (the owner, 19 Oct).
Not weighted yet: possessions lost, clearances, balls won, dribbled past, recoveries.
Rating = 6.5 + sum(weights), clipped 3-10, rounded to one decimal, halves up."""
import sys
sys.path.insert(0, './poss'); sys.path.insert(0, './shots'); sys.path.insert(0, './out127')
sys.path.insert(0, './def')
from decimal import Decimal, ROUND_HALF_UP
import shot_analysis_v16 as _sa
for _n in ('shot_analysis_v10', 'shot_analysis_v11', 'shot_analysis_v12', 'shot_analysis_v13', 'shot_analysis_v14', 'shot_analysis_v15'): sys.modules[_n] = _sa
PASS_STD, ACC_STD = 10, 70   # v7 (the owner, 19 Oct, 'after VAR review'): was 20 completed / 80 %
from shot_analysis_v16 import analyse, ratings as shot_ratings
from dribbles_v2 import dribbles
from match_stats_v3 import match_stats
from tackles_v5 import tackles
from interceptions_v2 import interceptions
sys.path.insert(0, './bf131')
from blocks_fouled_v2 import blocks_fouled
sys.path.insert(0, './du132')
from duels_v1 import duels

W_EXTRA = dict(drib_won=0.1, drib_lost=-0.05, dispossessed=-0.05, bad_touch=-0.05, tackle_won=0.05, tackle_failed=-0.1, interception=0.05, blocks=0.1, was_fouled=0.05,
               ground_won=0.02, ground_lost=-0.02, aerial_won=0.05, aerial_lost=-0.05)

def rate(path):
    M, rows, who, played, *_ = analyse(path)
    base = {r['name']: r for r in shot_ratings(M, rows, who, played)}
    _, drows, _ = dribbles(path)
    _, mrows = match_stats(path)
    _, trows, _, _ = tackles(path)
    bf, _ = blocks_fouled(path)
    du, _ = duels(path)
    ic = {x['name']: x['interceptions'] for x in interceptions(path)[1]}
    d = {r['name']: r for r in drows}; m = {r['name']: r for r in mrows}; tk = {r['name']: r for r in trows}
    out = []
    for name, r in base.items():
        t = tk.get(name, {}); ms = m.get(name, {})
        on, off = (int(x) for x in r['minutes'].split('-')); mins = off - on
        comp, att = ms.get('pass_acc', 0), ms.get('pass_att', 0)
        gap = comp - mins / 90 * PASS_STD
        vol = gap / 10 * (0.1 if gap >= 0 else 0.2)
        acc = 0.0
        if att and (comp >= 4 or mins >= 35):
            pct = 100 * comp / att
            acc = (pct - ACC_STD) / 10 * (0.2 if pct >= ACC_STD else 0.1)
        extra = {'drib_won': d.get(name, {}).get('drib_won', 0), 'drib_lost': d.get(name, {}).get('drib_lost', 0),
                 'dispossessed': m.get(name, {}).get('dispossessed', 0), 'bad_touch': m.get(name, {}).get('bad_touch', 0),
                 'tackle_won': t.get('tackles_won', 0), 'tackle_failed': t.get('tackles', 0) - t.get('tackles_won', 0), 'interception': ic.get(name, 0), **bf.get(name, dict(blocks=0, was_fouled=0)),
                 **du.get(name, dict(ground_won=0, ground_lost=0, aerial_won=0, aerial_lost=0))}
        raw = round(r['raw'] + sum(W_EXTRA[k] * v for k, v in extra.items()) + vol + acc, 6)
        rating = float(Decimal(str(max(3.0, min(10.0, raw)))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        out.append(dict(r, **extra, raw=raw, rating=rating, rating_before=r['rating'], passes=f'{comp}/{att}', pass_vol=round(vol, 3), pass_accb=round(acc, 3)))
    return sorted(out, key=lambda x: (x['team'], -x['rating']))

if __name__ == '__main__':
    for x in rate(sys.argv[1]): print(x)
