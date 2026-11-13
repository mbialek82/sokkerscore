"""ratings_v26.py — v26 (7 Nov 2026, the owner, decisions 19–20): the new stats of docs/changes_after_handoff_v2.md enter the rating.
On top of ratings_v25 (formula, models, long balls unchanged):
  accurate cross +0.05 · clearance (Opta definition, extras_v1) +0.03 · dispossession +0.05 but only when the same player was
  not credited a won tackle within 15 ticks of it (extras_v2 `dispossessions_solo`; an action that is both counts as the tackle)
  · keeper: punch +0.05, high claim +0.08, run out successful +0.05, run out failed −0.10
  · chance lost to the keeper (lost1v1_v3, xG capped at 0.30): the attacker gets a big chance missed (−0.25, same as a shot)
    when the capped xG >= BIG_XG (0.25); the keeper gets a save in the box (+0.2, same weight as a save on a shot).
  The lost chance's capped xG is added to the attacker's and the team's xG (display, build_data_v29); shot counts unchanged.
Row additions: touches, cross_att, cross_acc, clearances2, dispossessions, dispossessions_solo, punches, high_claims, runs_out,
runs_out_won, lost_gk, lost_gk_xg, lost_gk_bcm, lost_gk_saves, lost_gk_events (list), new_pen (points added), new_contrib
(label, n, pts rows for the page), rating_v25.
ratings_v25.py — v25: long balls forward-only, no goal kicks (match_stats_v8). ratings_v24 — bins of 40. ratings_v23 — models v3."""
import sys
for p in ('./poss', './shots', './def', './pen152', './ex162', './xg134'):
    if p not in sys.path: sys.path.insert(0, p)
from decimal import Decimal, ROUND_HALF_UP
import json
from ratings_v25 import rate as rate25          # also sets the module aliases
import ratings_v25 as _r25, ratings_v14 as _r14
import extras_v2, lost1v1_v3                    # these import ratings_v22 for its aliases, which REFITS _r14's xG/xA models with the
import xg_model_v1 as XG, xa_model_v1 as XA     # old v2 / bins-of-20 sets; restore this folder's current models (ratings_v25) here:
_r14._MX = XG.CategoryXG(MIN=_r25.XG_MIN).fit(json.load(open(_r25.SHOTS, encoding='utf-8')))
_r14._MA = XA.CategoryXA(MIN=_r25.XA_MIN).fit(json.load(open(_r25.KPS, encoding='utf-8')))

W_NEW = dict(cross_acc=0.05, clearance=0.03, dispossession=0.05, punch=0.05, high_claim=0.08, run_out_won=0.05, run_out_failed=-0.10)
SAVE_IN = 0.2                                      # keeper save in the box, as in the shot formula
BIG_XG, BCM = _r14.BIG_XG, _r14.W_BIG['bcm']       # 0.25 and -0.25
LAB = dict(cross_acc='Accurate cross', clearance='Clearance', dispossession='Dispossession', punch='Punch', high_claim='High claim',
           run_out_won='Run out', run_out_failed='Run out failed', lost_bcm='Big chance missed (lost to keeper)', lost_save='Save (one-on-one)')

def rate(path):
    rows = rate25(path)
    _, st, ev = extras_v2.extras(path)
    _, lost = lost1v1_v3.lost(path)
    by_att = {}; by_gk = {}
    for e in lost:
        by_att.setdefault((e['team'], e['sh']), []).append(e)
        by_gk.setdefault(('B' if e['team'] == 'A' else 'A', e['gk']), []).append(e)
    for r in rows:
        k = (r['team'], r['name']); e = st.get(k, {})
        g = lambda f: e.get(f, 0)
        n = dict(touches=g('touches'), cross_att=g('cross_att'), cross_acc=g('cross_acc'), clearances2=g('clearances2'),
                 dispossessions=g('dispossessions'), dispossessions_solo=g('dispossessions_solo'), punches=g('punches'),
                 high_claims=g('high_claims'), runs_out=g('runs_out'), runs_out_won=g('runs_out_won'))
        la = by_att.get(k, []); lg = by_gk.get(k, [])
        n.update(lost_gk=len(la), lost_gk_xg=round(sum(x['xg'] for x in la), 3), lost_gk_bcm=sum(1 for x in la if x['xg'] >= BIG_XG),
                 lost_gk_saves=len(lg), lost_gk_events=la)
        parts = [('cross_acc', n['cross_acc'], W_NEW['cross_acc']), ('clearance', n['clearances2'], W_NEW['clearance']),
                 ('dispossession', n['dispossessions_solo'], W_NEW['dispossession']), ('punch', n['punches'], W_NEW['punch']),
                 ('high_claim', n['high_claims'], W_NEW['high_claim']), ('run_out_won', n['runs_out_won'], W_NEW['run_out_won']),
                 ('run_out_failed', n['runs_out'] - n['runs_out_won'], W_NEW['run_out_failed']),
                 ('lost_bcm', n['lost_gk_bcm'], BCM), ('lost_save', n['lost_gk_saves'], SAVE_IN)]
        contrib = [dict(label=LAB[key], n=int(cnt), pts=round(cnt * w, 3)) for key, cnt, w in parts if cnt]
        pen = round(sum(c['pts'] for c in contrib), 6)
        raw = round(r['raw'] + pen, 6)
        rating = float(Decimal(str(max(3.0, min(10.0, raw)))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        r.update(n, rating_v25=r['rating'], raw=raw, rating=rating, new_pen=pen, new_contrib=contrib)
    return sorted(rows, key=lambda x: (x['team'], -x['rating']))

if __name__ == '__main__':
    for r in rate(sys.argv[1]):
        if r['new_pen']: print(r['team'], r['name'], r['rating_v25'], '->', r['rating'], r['new_contrib'])
