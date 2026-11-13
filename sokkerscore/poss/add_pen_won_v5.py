"""add_pen_won_v5.py — v5 (11 Nov 2026): the penalty-won step for ONE match with the bundle path as an argument (live/rate_match_v1).
The rule, the +0.25 weight and the re-rating are add_pen_won_v1's, copied unchanged; two things differ in how it runs:
  - no lookup in run_all_v9's path table (it only knows the 63 published matches);
  - it does NOT import build_data_v33. add_pen_won_v1 does, and that import sets shots_v9.shots back to shots_v12; in a process that
    goes on to rate other matches this would silently undo shots_v13. The step itself does not use shots (only who-is-who, touches
    and the fouled events), so the result is the same.
Must be imported after build_data_v36."""
import sys
from decimal import Decimal, ROUND_HALF_UP
assert 'build_data_v36' in sys.modules, 'import build_data_v36 first (loader, shot and touch patches)'
import strikes_v2
import touches_v3
import blocks_fouled_v2 as bf
from shots_v9 import team
from shot_analysis_v17 import analyse

PEN_WON = 0.25
FOUL_WINDOW = 150
GAP = 20


def winners(m, bundle):
    _, _, who, *_ = analyse(bundle); M = strikes_v2.load(bundle); T = touches_v3.touches(M)
    _, ev = bf.blocks_fouled(bundle)
    out = []
    for e in m['pens']:
        f = [x for x in ev if x['kind'] == 'fouled' and e['t'] - FOUL_WINDOW <= x['t'] < e['t']]
        if f:
            out.append((f[-1]['player'], 'fouled'))
            continue
        prev = [x for x in T if x['t'] < e['t'] - GAP and team(x['slot']) == e['team'] and x['slot'] not in (10, 21)]
        out.append((who(prev[-1]['slot'], prev[-1]['t']), 'last touch') if prev else (None, None))
    return out


def rerate(p, n):
    raw = p['raw'] + PEN_WON * n
    p['contrib'].append(dict(label='Penalty won', n=n, pts=round(PEN_WON * n, 3)))
    p['rating'] = float(Decimal(str(round(max(3.0, min(10.0, raw)), 6))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
    p['raw'] = round(raw, 2)


def apply(m, bundle):
    for p in m['players']: p['stats']['pen_won'] = 0
    if not m.get('pens'): return m
    for e, (name, how) in zip(m['pens'], winners(m, bundle)):
        e['won_by'], e['won_how'] = name, how
        p = next((p for p in m['players'] if p['name'] == name and p['team'] == e['team']), None)
        if p: p['stats']['pen_won'] += 1
        else: print('WARNING', m['id'], e['minute'], 'no player', name)
    for p in m['players']:
        if p['stats']['pen_won']: rerate(p, p['stats']['pen_won'])
    return m
