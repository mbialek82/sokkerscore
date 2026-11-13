"""ratings_v27.py — v27 (10 Nov 2026, the owner, decision 21; evidence in docs/rating_recalibration_v1.md): recalibration for Sokker.
Unlike v13–v26 this is a FINAL POST-PROCESSING step on a finished ratings_data file, because the team-defence term needs the positions
(add_lineups_v3) and the per-shot xG list (add_shots_v6), which do not exist inside rate(). It imports no detector and no xG/xA model,
so the ratings_v22 refit pitfall does not apply. Stats are not touched; only rating, raw and contrib change.
On top of ratings_v26:
  1. CB / FB team defence: +0.15 x (2.32 x minutes/90 - xG conceded while on the pitch)
  2. key pass +0.2 -> +0.1 (xA already pays for chance quality)
  3. unsuccessful touch -0.05 -> -0.085; dribble failed -0.05 -> -0.075 (ball losses cost more in Sokker than the old weights said)
  4. aerial duel +-0.05 -> +-0.025 (no link to match results)
  5. keeper: save and goal-conceded points replaced by +0.5 x goals prevented + 0.54 x minutes/90; goals prevented = sum over shots on
     target faced of P(goal | on target, xG bin) minus goals conceded. High claims, punches and run-outs are unchanged.
  6. a goal scored when the scorer's team is already 2+ ahead or 3+ behind counts +0.7 instead of +1.0
  7. calibration +0.13 x minutes/90 for everyone, which keeps the league mean at its v26 level (6.97)
No position offsets: position gaps are partly real skill, since the best players play W, CF and CM (the owner).
Constants were fitted on the 56 published matches without a team scoring 8+ (P_ON_TARGET also on the 92 comparison matches); they are frozen here.
Adds per player: rating_v26, raw_v26; per match: rating_version. Usage: python -X utf8 -I poss/ratings_v27.py in.json out.json"""
import sys, json
from decimal import Decimal, ROUND_HALF_UP

K_DEF, XGA_BASE = 0.15, 2.32
KEY_PASS, BAD_TOUCH, DRIB_LOST, AERIAL = 0.1, -0.085, -0.075, 0.025
K_GP, GK_BASE = 0.5, 0.54
GOAL_CUT = 0.3
CALIBRATION = 0.13
XG_EDGES = (0.05, 0.1, 0.2, 0.3, 0.5)          # bins: [0, .05) [.05, .1) [.1, .2) [.2, .3) [.3, .5) [.5, 1]
P_ON_TARGET = (0.09, 0.17, 0.20, 0.27, 0.42, 0.86)
ON_TARGET = {'goal', 'on target (saved)', 'lost to keeper', 'no goal (line)'}
GK_OLD = {'Save (in box)', 'Save (outside box)', 'Save (one-on-one)', 'Goal conceded'}


def p_on_target(xg):
    return P_ON_TARGET[sum(1 for e in XG_EDGES if xg >= e)]


def decided_goals(m):
    """(team, scorer) -> goals scored with the scorer's team already 2+ ahead or 3+ behind."""
    a = b = 0; out = {}
    for s in sorted((s for s in m['shots'] if s['out'] == 'goal'), key=lambda s: s['min']):
        lead = a - b if s['team'] == 'A' else b - a
        if lead >= 2 or lead <= -3: out[(s['team'], s['sh'])] = out.get((s['team'], s['sh']), 0) + 1
        if s['team'] == 'A': a += 1
        else: b += 1
    return out


def n_of(p, label):
    return sum(c['n'] or 0 for c in p['contrib'] if c['label'] == label)


def reprice(rows, label, weight):
    for c in rows:
        if c['label'] == label: c['pts'] = round(c['n'] * weight, 3)


def apply_player(m, p, dec):
    opp = 'B' if p['team'] == 'A' else 'A'; mins = max(0, p['off'] - p['on']); frac = mins / 90
    faced = [s for s in m['shots'] if s['team'] == opp and p['on'] <= s['min'] <= p['off']]
    delta = 0.0; rows = [dict(c) for c in p['contrib']]; extra = []

    n_kp, n_bt, n_df, n_aw, n_al = p['stats']['key_passes'], n_of(p, 'Unsuccessful touch'), n_of(p, 'Dribble failed'), n_of(p, 'Aerial duel won'), n_of(p, 'Aerial duel lost')
    delta += (KEY_PASS - 0.2) * n_kp + (BAD_TOUCH + 0.05) * n_bt + (DRIB_LOST + 0.05) * n_df + (AERIAL - 0.05) * n_aw + (0.05 - AERIAL) * n_al
    for label, w in (('Key pass', KEY_PASS), ('Unsuccessful touch', BAD_TOUCH), ('Dribble failed', DRIB_LOST), ('Aerial duel won', AERIAL), ('Aerial duel lost', -AERIAL)):
        reprice(rows, label, w)

    if p['pos'] in ('CB', 'FB'):
        d = K_DEF * (XGA_BASE * frac - sum(s['xg'] for s in faced))
        delta += d; extra.append(dict(label='Team defence', n=None, pts=round(d, 3)))
    if p['pos'] == 'GK':
        old = sum(c['pts'] for c in rows if c['label'] in GK_OLD)
        rows = [c for c in rows if c['label'] not in GK_OLD]
        on_t = [s for s in faced if s['out'] in ON_TARGET]
        gp = K_GP * sum(p_on_target(min(1, s['xg'])) - (s['out'] == 'goal') for s in on_t)
        base = GK_BASE * frac
        delta += gp + base - old
        extra += [dict(label='Goals prevented', n=None, pts=round(gp, 3)), dict(label='Keeper baseline', n=None, pts=round(base, 3))]
    n_dec = dec.get((p['team'], p['name']), 0)
    if n_dec:
        delta -= GOAL_CUT * n_dec; extra.append(dict(label='Goal in a decided match', n=n_dec, pts=round(-GOAL_CUT * n_dec, 3)))
    cal = CALIBRATION * frac
    delta += cal; extra.append(dict(label='Calibration', n=None, pts=round(cal, 3)))

    raw = p['raw'] + delta
    p['rating_v26'], p['raw_v26'] = p['rating'], p['raw']
    p['rating'] = float(Decimal(str(round(max(3.0, min(10.0, raw)), 6))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
    p['raw'] = round(raw, 2)
    p['contrib'] = sorted((c for c in rows + extra if abs(c['pts']) >= 0.005), key=lambda c: -abs(c['pts']))


def apply(m):
    dec = decided_goals(m)
    for p in m['players']: apply_player(m, p, dec)
    m['rating_version'] = 'ratings_v27'
    return m


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding='utf-8'))
    for m in d: apply(m)
    json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('ratings_v27:', len(d), 'matches ->', dst)
