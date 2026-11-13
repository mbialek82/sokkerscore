"""touches_v5.py — v5 (11 Nov 2026, the owner's blind check of 8 reassigned touches): a tackle animation (code 2) no longer takes the touch when the next touch is by
ANY player of the originally credited player's team (v4: only by that player himself). At 0:49 in 44742723 Papatya dribbled past Ascane's failed tackle and
Vardar collected the ball; v4 gave the touch to Ascane.
Blind check result for v4 (8 moments): new rule right in 4 (Pilic, Barber, Quadri, Berja), wrong in 3 (Helvei 89:00 in 44140524: no animation from Helvei at all;
Machín 5:29 in 44139688: his cross animation starts at +3, outside the +-2 window, Cankar's block attempt at +2; Papatya, fixed here), 1 unclear.
The +-2 window is not widened: that would fix Machín but undo Quadri (35:24 in 44140468, his start at +2 against Bucilă's at -3).
Everything else as touches_v4. Patch with patch() BEFORE any detector imports touches_v2 / touches_v3 (see build_data_v35)."""
import math
import touches_v4 as _v4

TACKLE = _v4.TACKLE


def reattribute(M, T):
    B, P, N = M['ball'], M['P'], M['N']
    team = lambda q: q <= 10
    for k, x in enumerate(T):
        t, s = x['t'], x['slot']
        if _v4._start(P, N, s, t): continue
        c = []
        for q in range(22):
            if q == s: continue
            g = _v4._start(P, N, q, t)
            if not g: continue
            u = t + g[0]; d = math.hypot(P[q][u][0] - B[u][0], P[q][u][1] - B[u][1])
            if d <= _v4.R and (B[t][2] <= 2.6 or q in (10, 21)): c.append((abs(g[0]), d, q, g[1]))
        if not c: continue
        _, d, q, a = min(c)
        nx = T[k + 1] if k + 1 < len(T) else None
        if a == TACKLE and nx is not None and team(nx['slot']) == team(s): continue
        x['slot_v3'] = s; x['slot'] = q; x['anim_reassign'] = a
    return T


def touches_v2(M, **kw): return reattribute(M, _v4._orig2(M, **kw))
def touches_v3(M, **kw): return reattribute(M, _v4._orig3(M, **kw))


def patch():
    import touches_v2 as _t2, touches_v3 as _t3
    _t2.touches = touches_v2; _t3.touches = touches_v3
