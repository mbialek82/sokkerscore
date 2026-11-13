"""ratings_v28.py — v28 (11 Nov 2026, the owner: publish touches_v5 "with the league average restored"): ratings_v27 with CALIBRATION 0.13 -> 0.18 per 90.
touches_v5 (touches go to the player who starts a ball animation) turns about 730 completed passes (4%) into failed ones and lowered the league mean
(players with 60+ minutes, matches without an 8+ score) from 6.97 to 6.92; at 0.18 it is 6.966 before add_pen_won and 6.969 after. Everything else as v27.
usage (from sokkerscore/): python -X utf8 -I poss/ratings_v28.py <src.json> <dst.json>"""
import sys, json
sys.path.insert(0, './poss')
import ratings_v27 as _r

_r.CALIBRATION = CALIBRATION = 0.18


def apply(m):
    _r.apply(m)
    m['rating_version'] = 'ratings_v28'
    return m


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding='utf-8'))
    for m in d: apply(m)
    json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('ratings_v28:', len(d), 'matches ->', dst)
