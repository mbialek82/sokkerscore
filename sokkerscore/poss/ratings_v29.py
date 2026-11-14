"""ratings_v29.py — v29 (14 Nov 2026, the owner: "are we not too harsh for blocked shot?"): ratings_v28 with the blocked shot at -0.1 instead of -0.2.
Why: a blocked shot cost the shooter the same as an off-target one (net -0.1 with the +0.1 for the shot; -0.35 as a big chance) while the
blocker was already paid +0.1 for the same event, and blocked shots are better chances than misses (63 published matches: 69 blocked at a mean
xG of 0.20, 246 off target at 0.13); in Sokker the engine aims the kick, so a body in the line is mostly the simulation. At -0.1 a blocked shot is
net zero for the shooter and the big-chance penalty still applies on top (-0.25 instead of -0.35). The calibration stays at 0.18 per 90: about
one blocked shot per match moves the league mean by well under 0.01.
How it runs: a post-step on a match that already carries ratings_v28 (raw, rating, contrib rows), like add_pen_won: +0.1 per blocked shot
(stats.blocked) is added to raw, the 'Shot blocked' row is re-priced, the rating is clamped and rounded again, the rows re-sorted.
rate_match_v3 calls it after add_pen_won_v5; on the published file: python -X utf8 -I poss/ratings_v29.py viz/ratings_data_v52.json viz/ratings_data_v53.json"""
import sys, json
from decimal import Decimal, ROUND_HALF_UP

BLOCKED_OLD, BLOCKED = -0.2, -0.1


def apply_player(p):
    n = p['stats'].get('blocked', 0) or 0
    if n:
        raw = p['raw'] + (BLOCKED - BLOCKED_OLD) * n
        rows = [c for c in p['contrib'] if c['label'] != 'Shot blocked']
        rows.append(dict(label='Shot blocked', n=n, pts=round(BLOCKED * n, 3)))
        p['contrib'] = sorted((c for c in rows if abs(c['pts']) >= 0.005), key=lambda c: -abs(c['pts']))
        p['rating'] = float(Decimal(str(round(max(3.0, min(10.0, raw)), 6))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        p['raw'] = round(raw, 2)
    return p


def apply(m):
    assert m.get('rating_version') == 'ratings_v28', f"ratings_v29 is a step on top of ratings_v28, got {m.get('rating_version')!r}"
    for p in m['players']: apply_player(p)
    m['rating_version'] = 'ratings_v29'
    return m


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding='utf-8'))
    for m in d: apply(m)
    json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('ratings_v29:', len(d), 'matches ->', dst)
