"""penalties_v1.py — sokker_152. Penalty kicks and whether they were scored, per match.
A penalty = the ball lies still (< 0.3 m movement, >= 8 ticks, height < 0.5 m) within 1.2 m of a penalty spot
(11 m from the goal line, on the goal-line centre axis), with exactly one outfield-or-keeper player within TAKER_M
(3.2 m) of it and the next-nearest player > 5 m away (taker alone; a contested loose ball has two players close),
and the taker is not a goalkeeper. Taker = the nearest player at the first tick the ball moves.
Outcome: 'goal' if a Score-tab GOAL event falls within 90 ticks of the kick, else 'post' if a POST event does, else 'saved/missed'.
Unverified against video: the owner to confirm the list (candidates printed by __main__). Misses = every non-goal."""
import sys, math
for p in ('./poss', './shots', './def'): sys.path.insert(0, p)
from strikes_v2 import load
from shot_analysis_v17 import occupancy
from shots_v9 import team

SPOT_M, TAKER_M, ALONE_M = 11.0, 3.2, 5.0

def penalties(path, M=None):
    M = M or load(path); B = M['ball']; N = M['N']; gx = M['gx']; P = M['P']; who, _ = occupancy(M)
    out = []; t = 0
    while t < N - 30:
        x, y, z = B[t]
        if abs(abs(x) - (gx - SPOT_M)) < 1.2 and abs(y) < 1.2 and z < 0.5:
            u = t
            while u < N - 1 and math.dist(B[u][:2], B[t][:2]) < 0.3: u += 1
            if u - t >= 8:
                near = sorted((math.hypot(P[s][u][0] - B[u][0], P[s][u][1] - B[u][1]), s) for s in range(22))
                (d1, s1), (d2, s2) = near[0], near[1]
                if d1 <= TAKER_M and d2 > ALONE_M and s1 not in (10, 21):
                    goal = any(J == 1 and u <= tt <= u + 90 for tt, J, p in M['ev'])
                    post = any(J == 5 and u <= tt <= u + 90 for tt, J, p in M['ev'])
                    out.append(dict(t=u, minute=M['minute'](u), taker=who(s1, u), team=team(s1),
                                    outcome='goal' if goal else 'post' if post else 'saved/missed'))
                t = u + 1; continue
        t += 1
    return out

if __name__ == '__main__':
    for e in penalties(sys.argv[1]): print(e)
