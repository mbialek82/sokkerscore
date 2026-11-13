"""ratings_v14.py — v14 (the owner, 30 Oct): big chances and xA in the rating.
  big chance = a shot with xG >= BIG_XG (0.25; season-78 category xG, sokker_134);
  BCM (big chance missed, shooter) -0.25 each; BCC (big chance created, the key passer) +0.15 each;
  xA (season-78 category xA, sokker_135) +0.05 per 0.1, i.e. +0.5 x xA — on top of key pass +0.2 and assist +0.4.
  xG is computed and shown but not weighted. Everything else = ratings_v13."""
import sys, json
sys.path.insert(0, './poss'); sys.path.insert(0, './xg134'); sys.path.insert(0, './xa135')
from decimal import Decimal, ROUND_HALF_UP
import ratings_v13 as base
import xg_model_v1 as XG, xa_model_v1 as XA, xg_features_v1 as XGF, xa_features_v1 as XAF
BIG_XG = 0.25
W_BIG = dict(bcm=-0.25, bcc=0.15, xa_per_unit=0.5)
_MX = XG.CategoryXG(MIN=20).fit(json.load(open('./xg134/shots_s78_v1.json')))
_MA = XA.CategoryXA(MIN=20).fit(json.load(open('./xa135/keypasses_s78_v1.json')))

def chances(path):
    sh = XGF.one((path, 0, 0)); kp = XAF.one((path, 0, 0))
    for x, p in zip(sh, _MX.predict(sh) if sh else []): x['xg'] = float(p)
    for x, p in zip(kp, _MA.predict(kp) if kp else []): x['xa'] = float(p)
    xg_at = {x['tick']: x['xg'] for x in sh}
    for x in kp: x['shot_xg'] = xg_at.get(x['shot_tick'], 0.0)
    return sh, kp

def rate(path):
    rows = base.rate(path); sh, kp = chances(path)
    acc = {}
    for x in sh:
        a = acc.setdefault((x['team'], x['shooter']), dict(xg=0.0, xa=0.0, bcm=0, bcc=0, big_chances=0))
        a['xg'] += x['xg']
        if x['xg'] >= BIG_XG:
            a['big_chances'] += 1; a['bcm'] += int(not x['goal'])
    for x in kp:
        a = acc.setdefault((x['team'], x['passer']), dict(xg=0.0, xa=0.0, bcm=0, bcc=0, big_chances=0))
        a['xa'] += x['xa']; a['bcc'] += int(x['shot_xg'] >= BIG_XG)
    out = []
    for r in rows:
        a = acc.get((r['team'], r['name']), dict(xg=0.0, xa=0.0, bcm=0, bcc=0, big_chances=0))
        extra = W_BIG['bcm'] * a['bcm'] + W_BIG['bcc'] * a['bcc'] + W_BIG['xa_per_unit'] * a['xa']
        raw = round(r['raw'] + extra, 6)
        rating = float(Decimal(str(max(3.0, min(10.0, raw)))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        out.append(dict(r, xg=round(a['xg'], 2), xa=round(a['xa'], 2), bcm=a['bcm'], bcc=a['bcc'], big_chances=a['big_chances'],
                        raw=raw, rating=rating, rating_v13=r['rating']))
    return sorted(out, key=lambda x: (x['team'], -x['rating']))
