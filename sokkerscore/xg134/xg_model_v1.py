"""xg_model_v1.py — sokker_134. Category xG (the owner's method: sort shots into situations, xG = share that went in),
with a fallback: use the most detailed category that holds at least MIN shots, else the next coarser one.
Evaluated with 5-fold cross-validation grouped by match (no match is in its own training data)."""
import json, math, random, sys
import numpy as np
from collections import defaultdict

def bins(x):
    d = x['dist']
    dist = '0-6' if d < 6 else '6-11' if d < 11 else '11-16' if d < 16 else '16-22' if d < 22 else '22+'
    gk = 'beaten' if x['gk_off'] >= 2.5 else 'off line' if x['gk_line'] >= 2 else 'set'
    cone = str(min(x['cone_def'], 2))
    ang = 'narrow' if x['angle'] < 15 else 'mid' if x['angle'] < 30 else 'wide'
    press = 'tight' if x['press'] < 1.0 else 'free'
    mates = '0' if x['mates_ahead'] == 0 else '1+'
    return [('dist', dist), ('gk', gk), ('head', 'header' if x['header'] else 'foot'), ('cone', cone), ('kind', x['kind']),
            ('angle', ang), ('press', press), ('mates', mates)]

LEVELS = ['dist', 'gk', 'head', 'cone', 'kind', 'angle', 'press', 'mates']

class CategoryXG:
    def __init__(self, MIN=20, depth=len(LEVELS), shrink=0):
        self.MIN, self.depth, self.shrink = MIN, depth, shrink
    def keys(self, x):
        b = bins(x); return [tuple(b[:k]) for k in range(0, self.depth + 1)]
    def fit(self, rows):
        self.n = defaultdict(int); self.g = defaultdict(int)
        for x in rows:
            for k in self.keys(x): self.n[k] += 1; self.g[k] += x['goal']
        return self
    def predict1(self, x):
        ks = self.keys(x)
        if self.shrink:                                   # blend each level with its parent, weight n/(n+shrink)
            p = self.g[ks[0]] / self.n[ks[0]]
            for k in ks[1:]:
                if self.n[k] == 0: break
                p = (self.g[k] + self.shrink * p) / (self.n[k] + self.shrink)
            return p
        best = ks[0]
        for k in ks[1:]:
            if self.n[k] >= self.MIN: best = k
            else: break
        return self.g[best] / self.n[best]
    def predict(self, rows): return np.array([self.predict1(x) for x in rows])

def metrics(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)); br = np.mean((p - y) ** 2)
    order = np.argsort(p); r = np.empty(len(p)); r[order] = np.arange(len(p))
    npos = y.sum(); auc = (r[y == 1].sum() - npos * (npos - 1) / 2) / (npos * (len(y) - npos))
    return dict(logloss=round(ll, 4), brier=round(br, 4), auc=round(auc, 3))

def cv(rows, make, folds=5, frac=1.0, seed=0):
    ids = sorted({x['id'] for x in rows}); random.Random(seed).shuffle(ids)
    fold = {i: k % folds for k, i in enumerate(ids)}
    ys, ps = [], []
    for f in range(folds):
        tr_ids = [i for i in ids if fold[i] != f]; tr_ids = tr_ids[:max(1, int(len(tr_ids) * frac))]
        tr = [x for x in rows if x['id'] in set(tr_ids)]; te = [x for x in rows if fold[x['id']] == f]
        m = make().fit(tr); ps.append(m.predict(te)); ys.append(np.array([x['goal'] for x in te]))
    y, p = np.concatenate(ys), np.concatenate(ps)
    return metrics(y, p), y, p

class Logit:
    def fit(self, rows):
        X = self.X(rows); y = np.array([x['goal'] for x in rows]); w = np.zeros(X.shape[1])
        for _ in range(300):
            p = 1 / (1 + np.exp(-X @ w)); g = X.T @ (p - y) + 1.0 * np.r_[0, w[1:]]
            H = X.T @ (X * (p * (1 - p))[:, None]) + np.diag(np.r_[0, np.ones(len(w) - 1)])
            w -= np.linalg.solve(H, g)
        self.w = w; return self
    def X(self, rows):
        f = lambda x: [1, x['dist'], math.log(x['dist'] + 1), x['angle'] / 10, x['header'], min(x['cone_def'], 3), x['gk_off'],
                       x['gk_line'], min(x['press'], 5), x['mates_ahead'], x['kind'] == 'rebound', x['kind'] == 'error', x['kind'] == 'set']
        return np.array([f(x) for x in rows], dtype=float)
    def predict(self, rows): return 1 / (1 + np.exp(-self.X(rows) @ self.w))

if __name__ == '__main__':
    rows = [x for s in sys.argv[1:] for x in json.load(open(f'./xg134/shots_s{s}_v1.json'))]
    print(len(rows), 'shots', sum(x['goal'] for x in rows), 'goals')
    print('base rate      ', cv(rows, lambda: CategoryXG(depth=0))[0])
    print('distance only  ', cv(rows, lambda: CategoryXG(depth=1))[0])
    for MIN in (10, 20, 40):
        print(f'category MIN={MIN:<3}', cv(rows, lambda: CategoryXG(MIN=MIN))[0])
    for s in (10, 30):
        print(f'category blend k={s}', cv(rows, lambda: CategoryXG(shrink=s))[0])
    print('logistic (ref) ', cv(rows, Logit)[0])
    print('learning curve (category MIN=20, share of the training matches used):')
    for fr in (0.25, 0.5, 0.75, 1.0):
        res = [cv(rows, lambda: CategoryXG(MIN=20), frac=fr, seed=s)[0]['logloss'] for s in range(5)]
        print(f'   {fr:.2f}  logloss {np.mean(res):.4f}')
