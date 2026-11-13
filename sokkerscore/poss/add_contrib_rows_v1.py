"""add_contrib_rows_v1.py — v1 (10 Nov 2026, the owner): adds the rating components that were counted but had no row in contrib, so that
"Why this rating" adds up: Expected assists (+0.5 per 1.0 xA), Big chance created (+0.15), Big chance missed (-0.25).
Display only: rating, raw and stats do not change. stats.bcm includes chances lost to the keeper (build_data_v29), which already have
their own row "Big chance missed (lost to keeper)", so only the remainder gets the new row.
Usage: python -X utf8 -I poss/add_contrib_rows_v1.py in.json out.json"""
import sys, json

LOST = 'Big chance missed (lost to keeper)'


def apply_player(p):
    s = p['stats']
    lost = sum(c['n'] or 0 for c in p['contrib'] if c['label'] == LOST)
    bcm = s.get('bcm', 0) - lost
    new = [dict(label='Expected assists (xA)', n=None, pts=round(0.5 * s.get('xa', 0), 3)),
           dict(label='Big chance created', n=s.get('bcc', 0), pts=round(0.15 * s.get('bcc', 0), 3)),
           dict(label='Big chance missed', n=bcm, pts=round(-0.25 * bcm, 3))]
    p['contrib'] = sorted(p['contrib'] + [c for c in new if abs(c['pts']) >= 0.005], key=lambda c: -abs(c['pts']))


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding='utf-8'))
    for m in d:
        for p in m['players']: apply_player(p)
    json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('add_contrib_rows_v1:', len(d), 'matches ->', dst)
