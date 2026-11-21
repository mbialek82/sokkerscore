"""shots_v14.py — v14 (21 Nov 2026, the owner after a manager's complaint, Indonesia 0:0 Australia 44788004: Sokker counted 2-12 shots, we showed 1-11):
NEVER FEWER SHOTS THAN SOKKER'S REPORT. Sokker's match report gives every player's shot count (no minute, no outcome). Across the 95 rated matches
our team counts equalled Sokker's in 81 of 190, were lower in 63 and higher in 46. the owner chose "only add missing shots": when a player has fewer
shots than the report says, his likeliest missed strikes are added as shots until he has Sokker's number; extra shots we detect are kept.
How: shots_v13 runs first. Its blocked shots from 16 m or further are dropped later by shot_analysis (rule (d), Sokker counts few of them), so they
do not count toward the player's total; when he is below Sokker's count his own such blocks are kept first, nearest first, by marking them 'filled'
(shot_analysis_v18 keeps a filled one). In 44788004 that alone gives Lessy his 2 and McLaren his 3. Only then are other strikes added. TARGET (set by live/rate_match_v6 from the report for one match, then cleared) maps (team, surname) -> Sokker's count.
For a player below his count, every strike of his that is not a shot is a candidate when: he is not a keeper, the ball moves toward the opponents'
goal over t+1..t+3 and at 0.8 m per tick or faster, the strike is in the opponents' half within 45 m of goal, no OFFSIDE follows within 40 ticks,
and he has no other shot within 30 ticks (shot_analysis would merge the two). Candidates are ranked by a score:
  +3 shot kick (animation 1, 3, 11) · −2 pass kick (4, 18, 19) · +2 the next touch is an opponent's or the ball crosses the goal line ·
  −2 a team-mate touches next within 120 ticks · +1 aimed within 10 m of the goal centre · −distance / 10
and the best ones are taken. The end is found like shots_v9: a POST event -> woodwork; the ball crossing the goal line -> wide; the opponents'
keeper touching next -> saved; another opponent within 10 ticks and 12 m -> blocked (only within 20 m, shot_analysis drops far blocks); else wide.
Each added row carries 'filled': True. Without TARGET (the 63 published matches, the old checks) the result is shots_v13's, unchanged.
shots_v9.shots must be replaced by this function in every holder (see live/rate_match_v6)."""
import math
import shots_v9 as _s9
import shots_v11 as _s11
import shots_v13 as _s13

TARGET = None            # {(team 'A'/'B', surname): Sokker's shot count}, set per match by the caller
MAXD, MINV, NEAR_T = 45.0, 0.8, 30
BLOCK_FAR_M = 16.0       # shot_analysis_v15+ rule (d): a blocked shot from 16 m or further is dropped unless 'filled' (shot_analysis_v18)
SHOT_ANIM, PASS_ANIM = {1, 3, 11}, {4, 18, 19}
_base = _s13.shots


def _who(M):
    from shot_analysis_v17 import occupancy      # late import: shot_analysis_v17 imports shots_v9
    return occupancy(M)[0]


def _end(M, S, i, side):
    B, P, gx, N = M['ball'], M['P'], M['gx'], M['N']
    t, T = S[i]['t'], _s9.team(S[i]['slot']); nx = S[i + 1] if i + 1 < len(S) else None
    end_t = nx['t'] if nx else N - 1
    post = [pt for t2, J, p in M['ev'] if J == 5 for pt in [t2] if t < pt <= min(end_t, t + 120) + 3]
    if post: return ('woodwork', post[0])
    for u in range(t + 1, min(end_t, t + 120, N - 1) + 1):
        if B[u][0] * side >= gx: return ('wide', u)
    if nx and _s9.team(nx['slot']) != T and nx['t'] <= t + 120:
        if nx['slot'] in (10, 21): return ('keeper', nx['t'], nx['slot'])
        dist = math.hypot(gx - B[t][0] * side, B[t][1])
        if nx['t'] - t <= 10 and math.hypot(nx['x'] - B[t][0], nx['y'] - B[t][1]) <= 12 and dist < 20: return ('blocked', nx['t'], nx['slot'])
    return ('wide', t)


def candidates(M, S, have, name_of):
    B, gx, N = M['ball'], M['gx'], M['N']
    off = [t for t, J, p in M['ev'] if J == 11]
    out = []
    for i, s in enumerate(S):
        if i in have: continue
        t, sl = s['t'], s['slot']
        if sl in (10, 21) or t + 4 >= N: continue
        T = _s9.team(sl); side = _s9.attack_side(M, T, t); x, y = B[t][0], B[t][1]; dist = math.hypot(gx - x * side, y)
        if x * side <= 0 or dist > MAXD: continue
        if max(math.dist(B[u][:2], B[u + 1][:2]) for u in range(t, t + 3)) < MINV: continue
        vx, vy = (B[t + 3][0] - B[t + 1][0]) / 2, (B[t + 3][1] - B[t + 1][1]) / 2
        if vx * side <= 0.1: continue
        if any(t <= o <= t + _s11.OFFSIDE_TICKS for o in off): continue
        aim = B[t + 1][1] + (side * gx - B[t + 1][0]) * vy / vx
        nx = S[i + 1] if i + 1 < len(S) else None
        a = _s11.anim(M, sl, t)
        crosses = any(B[u][0] * side >= gx for u in range(t + 1, min((nx['t'] if nx else N - 1), t + 120, N - 1) + 1))
        mate_next = bool(nx and _s9.team(nx['slot']) == T and nx['t'] - t <= 120)
        score = (3 if a in SHOT_ANIM else -2 if a in PASS_ANIM else 0) + (2 if crosses or (nx and _s9.team(nx['slot']) != T) else 0) \
            - (2 if mate_next else 0) + (1 if abs(aim) <= 10 else 0) - dist / 10
        out.append(dict(t=t, minute=M['minute'](t), slot=sl, team=T, x=round(x, 1), y=round(y, 1), z=round(B[t][2], 1), dist=round(dist, 1),
                        aim=round(aim, 1), end=_end(M, S, i, side), idx=i, filled=True, fill_score=round(score, 2), name=name_of(sl, t)))
    return out


def _far_block(r): return r['end'][0] == 'blocked' and r['dist'] >= BLOCK_FAR_M


def shots(M, S, **kw):
    L = _base(M, S, **kw)
    if not TARGET: return L
    who = _who(M)
    have = {}
    for r in L:
        if _far_block(r): continue                  # shot_analysis drops these unless they are marked 'filled'
        k = (r['team'], who(r['slot'], r['t'])); have[k] = have.get(k, 0) + 1
    need = {k: n - have.get(k, 0) for k, n in TARGET.items() if n > have.get(k, 0)}
    if not need: return L
    for r in sorted((r for r in L if _far_block(r)), key=lambda r: r['dist']):   # first: his own blocked shots from 16 m+, nearest first
        k = (r['team'], who(r['slot'], r['t']))
        if need.get(k, 0) > 0: r['filled'] = True; need[k] -= 1
    add = []
    C = sorted((c for c in candidates(M, S, {r['idx'] for r in L}, who) if need.get((c['team'], c['name']), 0) > 0), key=lambda c: -c['fill_score'])
    for c in C:
        k = (c['team'], c['name'])
        if need.get(k, 0) <= 0: continue
        if any(r2['slot'] == c['slot'] and abs(c['t'] - r2['t']) <= NEAR_T for r2 in L + add): continue
        add.append(c); need[k] -= 1
    for c in add: c.pop('name', None)
    return sorted(L + add, key=lambda r: r['t'])
