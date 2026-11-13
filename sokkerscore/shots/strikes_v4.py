"""strikes_v4.py — v4 (10 Nov 2026, the owner's blind video check, match 44496694 at 26:24): a ball bouncing next to a player is not a strike by him. Klinik's long shot bounced 1.6 m from Bucilă, who made
no kicking movement, and the bounce was read as Bucilă's shot (a false big chance missed, and Klinik's strike became a key pass).
A strike is dropped when ALL hold: (1) the ball keeps its sideways line (heading change <= HEAD_DEG between t-2..t and t..t+2); (2) it comes down to the ground and goes up again (lowest point of
t-1..t+2 at most LOW_Z, at least DROP_Z lower than at t-2 and at least RISE_Z lower than at t+2 or t+3); (3) no player within R_ANIM m of the ball starts an action animation in t-4..t+4.
Only strikes() changes, which feeds the shot detectors. touches_v2/v3 have their own loop, so passes, tackles, dribbles and possession are not affected.
strikes_v2.strikes must be replaced by this function BEFORE any detector is imported (see build_data_v30), as with the loader in strikes_v3."""
import math
import strikes_v2 as _s2

HEAD_DEG, LOW_Z, DROP_Z, RISE_Z, R_ANIM = 12.0, 0.4, 0.3, 0.2, 3.0
_orig = _s2.strikes


def is_bounce(M, s):
    B, P, N = M['ball'], M['P'], M['N']; t = s['t']
    if t < 3 or t + 3 >= N: return False
    a, b = (B[t][0] - B[t - 2][0], B[t][1] - B[t - 2][1]), (B[t + 2][0] - B[t][0], B[t + 2][1] - B[t][1])
    if math.hypot(*a) < 1e-6 or math.hypot(*b) < 1e-6: return False
    if abs(math.degrees((math.atan2(b[1], b[0]) - math.atan2(a[1], a[0]) + math.pi) % (2 * math.pi) - math.pi)) > HEAD_DEG: return False
    low = min(B[u][2] for u in range(t - 1, t + 3))
    if low > LOW_Z or B[t - 2][2] - low < DROP_Z or max(B[t + 2][2], B[t + 3][2]) - low < RISE_Z: return False
    for q in range(22):
        if math.hypot(P[q][t][0] - B[t][0], P[q][t][1] - B[t][1]) <= R_ANIM and any(P[q][u][2] not in _s2.LOCO and P[q][u][2] != P[q][u - 1][2] for u in range(max(1, t - 4), min(N, t + 5))):
            return False
    return True


def strikes(M, **kw):
    return [s for s in _orig(M, **kw) if not is_bounce(M, s)]
