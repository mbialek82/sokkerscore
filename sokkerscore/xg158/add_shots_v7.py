"""add_shots_v7.py — v7 (11 Nov 2026): add_shots_v6 as functions for ONE match (live/rate_match_v1): the shot rows are passed in instead
of read from row files, and the model is fitted once per process. The per-match logic is v6's, unchanged: m.shots rebuilt from the
feature rows with each shot's xG from the category model (bins of 40), the chances lost to the keeper appended (m.lost_gk), sorted by
minute, and stats.xg / m.xg reset to the sum of the listed shots."""
import sys, json
sys.path.insert(0, './xg134')
import xg_model_v1 as XG

_model = {}


def model(train='./xg158/shots_train_v3.json'):
    if train not in _model: _model[train] = XG.CategoryXG(MIN=40).fit(json.load(open(train, encoding='utf-8')))
    return _model[train]


def apply(m, rows, mx=None):
    mx = mx or model()
    S = sorted(zip(rows, [float(p) for p in mx.predict(rows)]) if rows else [], key=lambda t: t[0]['tick'])
    m['shots'] = [dict(min=x['minute'], team=x['team'], sh=x['shooter'], xg=round(p, 3), out=x['outcome'], kind=x['kind'],
                       dist=round(x['dist'], 1), head=int(x['header'])) for x, p in S]
    m['shots'] = sorted(m['shots'] + m.get('lost_gk', []), key=lambda z: (z['min'], z.get('out') == 'lost to keeper'))
    bad = 0
    for pl in m['players']:
        s = sum(z['xg'] for z in m['shots'] if z['team'] == pl['team'] and z['sh'] == pl['name'])
        if abs(s - (pl['stats'].get('xg') or 0)) > 0.02: bad += 1
        pl['stats']['xg'] = round(s, 2)
    m['xg'] = [round(sum(z['xg'] for z in m['shots'] if z['team'] == T), 2) for T in 'AB']
    return bad
