"""interceptions_v3.py — v3 (31 Oct, the owner's annotation of 44496766 + agreed definition 1): a header-height ball (>= AIR_Z = 2.0 m) won
with the intended receiver within AIR_NEAR_M is an aerial duel, not an interception (2:00 Üçok v Jazbec, 19:25 Tabaczyński;
11:48 Rădoi in 44471278, a confirmed interception, was at 1.6 m); a ball played by a player who was carrying it (>= 2 touches)
with the 'interceptor' within CARRY_CLOSE_M of the ball is a dispossession, not an interception (3:00 Jazbec / Wasielkiewicz).
tackles_v6 is used for the no-double-count check.
interceptions_v2.py — v2 (the owner's video verdicts, 19 Oct, 44471278: 11:48 Rădoi yes, 48:20 Virabyan yes;
1:03 Pihkala no — Inczewski kept the ball; 7:08 Kupecký no — Půda tackled; 26:38 Rădoi no — loose ball after
Pihkala's unsuccessful touch):
  KEEP: the interceptor's team must keep the ball — no opponent touch within KEEP_T ticks of his touch (as tackles' WON);
  AHEAD_M 25 -> 8: the intended receiver must be close to where the ball was cut out (a loose ball rolling towards a
  distant team-mate is not an interception).
interceptions_v1.py — sokker_130. Interception (the owner, 19 Oct): an opponent cuts out a pass that would have
been accurate if he hadn't blocked it. Weight +0.05.
Detector, on touches_v3:
  a pass = a touch by team X followed by a touch by opponent Y, with no Score-tab break between, not a shot,
           and the ball at least PASS_MIN_M from the passer's touch point when Y touches it;
  would have been accurate = continue the ball's line from Y's touch (direction over the previous DIR_T ticks)
           up to AHEAD_M metres: the first player within LANE_M of that line (other than Y) is a team-mate
           of the passer;
  not counted again when the same player is credited with a tackle at that moment (tackles_v5, +/-TACKLE_T ticks)."""
import sys, math
for p in ('./poss', './shots', './def'): sys.path.insert(0, p)
from collections import defaultdict
from touches_v3 import touches, load
from shots_v6 import team
from shot_analysis_v12 import analyse
from tackles_v6 import tackles

AIR_Z, AIR_NEAR_M, CARRY_CLOSE_M = 2.0, 3.0, 3.0
PASS_MIN_M, DIR_T, AHEAD_M, LANE_M, TACKLE_T, KEEP_T = 3.0, 3, 8.0, 3.0, 6, 15

def interceptions(path):
    M0, shot_rows, who, played, *_ = analyse(path)
    M = load(path); T = touches(M); P = M['P']; B = M['ball']
    shot_ticks = [r['tick'] for r in shot_rows]
    tk = tackles(path)[2]
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    st = defaultdict(int); ev = []
    for i in range(len(T) - 1):
        a, b = T[i], T[i+1]
        if team(a['slot']) == team(b['slot']) or any(a['t'] < e <= b['t'] for e in breaks): continue
        if any(abs(a['t'] - s) <= 2 for s in shot_ticks): continue
        tb = b['t']
        if math.dist(B[tb][:2], (a['x'], a['y'])) < PASS_MIN_M: continue
        u0 = max(a['t'], tb - DIR_T)
        dx, dy = B[tb][0] - B[u0][0], B[tb][1] - B[u0][1]; L = math.hypot(dx, dy)
        if L < 0.3: continue
        ux, uy = dx / L, dy / L; x0, y0 = B[tb][0], B[tb][1]
        best = None
        for q in range(22):
            if q in (b['slot'], a['slot']): continue          # neither the interceptor nor the passer himself
            px, py = P[q][tb][0] - x0, P[q][tb][1] - y0
            along = px * ux + py * uy; perp = abs(-px * uy + py * ux)
            if 0 < along <= AHEAD_M and perp <= LANE_M and (best is None or along < best[0]): best = (along, q, perp)
        if best is None or team(best[1]) != team(a['slot']): continue
        if i >= 1 and T[i-1]['slot'] == a['slot'] and math.hypot(P[b['slot']][a['t']][0] - B[a['t']][0], P[b['slot']][a['t']][1] - B[a['t']][1]) <= CARRY_CLOSE_M: continue
        if B[tb][2] >= AIR_Z and math.hypot(P[best[1]][tb][0] - P[b['slot']][tb][0], P[best[1]][tb][1] - P[b['slot']][tb][1]) <= AIR_NEAR_M: continue
        lost = False
        for k in range(i + 2, len(T)):
            if T[k]['t'] - tb > KEEP_T or any(tb < e <= T[k]['t'] for e in breaks): break
            if team(T[k]['slot']) != team(b['slot']): lost = True; break
        if lost: continue
        name = who(b['slot'], tb)
        if any(e['tackler'] == name and abs(e['t'] - tb) <= TACKLE_T for e in tk): continue
        st[name] += 1
        ev.append(dict(t=tb, minute=M['minute'](tb), interceptor=name, passer=who(a['slot'], a['t']),
                       target=who(best[1], tb), ahead_m=round(best[0], 1), lane_m=round(best[2], 1),
                       pass_m=round(math.dist(B[tb][:2], (a['x'], a['y'])), 1)))
    rows = [dict(name=n, team=team(s), minutes=f'{on}-{off}', interceptions=st[n]) for n, (s, on, off) in played.items() if on < off]
    return M, sorted(rows, key=lambda r: (r['team'], -r['interceptions'])), ev

if __name__ == '__main__':
    M, rows, ev = interceptions(sys.argv[1])
    for tm in 'AB': print('TEAM', tm, sum(r['interceptions'] for r in rows if r['team'] == tm))
    for r in rows:
        if r['interceptions']: print(r)
    for e in ev: print('EV', e)
