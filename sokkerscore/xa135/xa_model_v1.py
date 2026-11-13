"""xa_model_v1.py — sokker_135. xA by the owner's category method: each key pass gets a situation; xA = share of key
passes in that situation whose shot went in; fallback to the coarser situation below MIN passes (as xG, sokker_134)."""
import sys, json
sys.path.insert(0, './xg134')
import numpy as np
from collections import defaultdict
import xg_model_v1 as xg

def bins(x):
    d = x['recv_dist']
    recv = '0-6' if d < 6 else '6-11' if d < 11 else '11-16' if d < 16 else '16-22' if d < 22 else '22+'
    return [('first', 'first-time' if x['first_time'] else 'controlled'), ('recv', recv), ('cone', str(min(x['recv_cone'], 2))),
            ('ptype', x['ptype']), ('dir', x['direction']), ('wide', 'wide' if x['orig_wide'] else 'central')]

class CategoryXA(xg.CategoryXG):
    def keys(self, x):
        b = bins(x); return [tuple(b[:k]) for k in range(0, min(self.depth, len(b)) + 1)]

if __name__ == '__main__':
    rows = [x for s in sys.argv[1:] for x in json.load(open(f'./xa135/keypasses_s{s}_v1.json'))]
    print(len(rows), 'key passes', sum(x['goal'] for x in rows), 'goals')
    print('base rate        ', xg.cv(rows, lambda: CategoryXA(depth=0))[0])
    print('reception only   ', xg.cv(rows, lambda: CategoryXA(depth=2))[0])
    for MIN in (20, 40):
        print(f'category MIN={MIN:<4}', xg.cv(rows, lambda: CategoryXA(MIN=MIN))[0])
    print('category blend k=30', xg.cv(rows, lambda: CategoryXA(shrink=30))[0])
