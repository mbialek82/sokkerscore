"""shots_v13.py — v13 (11 Nov 2026, the owner's blind check of big chances without a shot: 4 of 8 were real shots blocked or headed at once that shots_v9 drops,
because it judges direction and speed over t+1..t+3, which already include the block): BLOCKED-AT-ONCE SHOTS. A strike that is not already a shot counts as one
when the player is in the opponents' box, starts a shot kick (animation 1, 3 or 11) within 3 ticks, the ball moves toward the goal until the next touch
(at most 3 ticks), and the next touch is an opponent's within 10 ticks and 12 m (keeper -> saved, anyone else -> blocked); no OFFSIDE within 40 ticks.
No aim limit: Herghelegiu's header at 2:51 in 44140446 and Eierkicker's at 7:42 in 44742725 left at an angle (aim 24 m off centre) before the block.
Against Sokker's shot counts on 146 matches (mean error per team): shots_v12 1.038 -> 1.010 with an aim <= 10 m limit, 0.986 without (+33 shots); adding animation
20 (Shipley 86:26 in 44140501) -> 1.021, so 20 stays out. Hrablo 88:52 in 44140512 is still missed: no touch is detected for the blocker.
shots_v9.shots must be replaced by this function BEFORE any detector imports it (see build_data_v36)."""
import math
import shots_v9 as _s9
import shots_v11 as _s11
import shots_v12 as _s12

SHOT_ANIM = {1, 3, 11}
BLOCK_T, BLOCK_M = 10, 12.0
_v12 = _s12.shots


def blocked_at_once(M, S, have):
    B, gx, N = M['ball'], M['gx'], M['N']
    off = [t for t, J, p in M['ev'] if J == 11]
    out = []
    for i, s in enumerate(S):
        if i in have or i + 1 >= len(S): continue
        t, sl = s['t'], s['slot']; T = _s9.team(sl); side = _s9.attack_side(M, T, t); x, y = B[t][0], B[t][1]
        if sl in (10, 21) or t + 4 >= N or gx - x * side > 16.5 or abs(y) > 20.16: continue
        nx = S[i + 1]
        if _s9.team(nx['slot']) == T or nx['t'] - t > BLOCK_T or math.hypot(nx['x'] - x, nx['y'] - y) > BLOCK_M: continue
        if any(t <= o <= t + _s11.OFFSIDE_TICKS for o in off): continue
        u = max(t + 1, min(nx['t'], t + 3)); vx, vy = (B[u][0] - B[t][0]) / (u - t), (B[u][1] - B[t][1]) / (u - t)
        if vx * side <= 0: continue
        if _s11.anim(M, sl, t) not in SHOT_ANIM: continue
        aim = y + (side * gx - x) * vy / vx
        end = ('keeper', nx['t'], nx['slot']) if nx['slot'] in (10, 21) else ('blocked', nx['t'], nx['slot'])
        out.append(dict(t=t, minute=M['minute'](t), slot=sl, team=T, x=round(x, 1), y=round(y, 1), z=round(B[t][2], 1),
                        dist=round(math.hypot(gx - x * side, y), 1), aim=round(aim, 1), end=end, idx=i))
    return out


def shots(M, S, **kw):
    L = _v12(M, S, **kw)
    return sorted(L + blocked_at_once(M, S, {r['idx'] for r in L}), key=lambda r: r['t'])
