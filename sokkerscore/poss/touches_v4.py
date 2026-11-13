"""touches_v4.py — v4 (11 Nov 2026, the owner: "you mistake defender clearances for failed attacking actions; whoever touches the ball has his name shown above him"):
a touch belongs to the player who starts a ball animation, not to the nearest player. If the credited player starts no non-locomotion animation within
+-2 ticks of the touch, and another player within 3 m of the ball does (at the tick he starts it), the touch goes to that player (smallest tick gap, then
distance). Exception: a tackle animation (code 2) does not take the touch when the next touch is by the originally credited player (a failed tackle: he kept
the ball, 10:17 Czerbniak v Golias in 44496766).
Applied ON TOP of both older detectors, which stay otherwise unchanged: touches_v2 (passes, unsuccessful touches, dispossessions, dribbles; no animation check
at all, so 2.2% of its touches move) and touches_v3 (tackles, interceptions, duels, blocks, running; 0.7% move).
Checked against the owner's annotation of 44496766 0:00-20:30: 12:59 Romano -> Gieroba (header Gieroba won), 18:35 Coc -> Järvelin (aerial duel Järvelin won),
19:03 Üçok -> Jazbec (Jazbec's heel pass) all agree; 0:52, 12:13, 15:00 cannot be told from the annotation.
In 6 of 8 reviewed big-chance moments (11 Nov) a defender's clearance (code 4) or the keeper's punch (code 10) had been credited to the nearest attacker.
Patch with patch() BEFORE any detector imports touches_v2 / touches_v3 (see build_data_v34)."""
import math
import touches_v2 as _t2
import touches_v3 as _t3
from strikes_v2 import LOCO

R = 3.0
W = 2
TACKLE = 2
_orig2, _orig3 = _t2.touches, _t3.touches


def _start(P, N, q, t):
    g = None
    for u in range(max(1, t - W), min(N, t + W + 1)):
        a = P[q][u][2]
        if a not in LOCO and a != P[q][u - 1][2] and (g is None or abs(u - t) < abs(g[0])): g = (u - t, a)
    return g


def reattribute(M, T):
    B, P, N = M['ball'], M['P'], M['N']
    for k, x in enumerate(T):
        t, s = x['t'], x['slot']
        if _start(P, N, s, t): continue
        c = []
        for q in range(22):
            if q == s: continue
            g = _start(P, N, q, t)
            if not g: continue
            u = t + g[0]; d = math.hypot(P[q][u][0] - B[u][0], P[q][u][1] - B[u][1])
            if d <= R and (B[t][2] <= 2.6 or q in (10, 21)): c.append((abs(g[0]), d, q, g[1]))
        if not c: continue
        _, d, q, a = min(c)
        nx = T[k + 1] if k + 1 < len(T) else None
        if a == TACKLE and nx is not None and nx['slot'] == s: continue
        x['slot_v3'] = s; x['slot'] = q; x['anim_reassign'] = a
    return T


def touches_v2(M, **kw): return reattribute(M, _orig2(M, **kw))
def touches_v3(M, **kw): return reattribute(M, _orig3(M, **kw))


def patch():
    _t2.touches = touches_v2; _t3.touches = touches_v3
