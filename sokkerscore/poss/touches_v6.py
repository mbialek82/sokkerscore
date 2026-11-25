"""touches_v6.py — v6 (25 Nov 2026, the owner: Jaruzelski 0/4 passes but an assist in 44496707): a ball that flies past a player unchanged is not his touch.
At 79:xx in 44496707 Jaruzelski's pass to Czerbniak flew 1.6 m past Barroso at 0.8 m height with no change of line; Barroso made no movement. The touch
loop (touches_v2/v3) fires on any change of speed between two ticks above 0.15 m per tick, and ball positions are stored to 0.1 m, so the per-tick speed of
a ball in flight jitters (1.82, 1.73, 1.82, 1.63, 1.73, 1.53 m per tick here) and a player within 2 m gets a touch: the pass became a pass to an opponent
and Barroso won the ball. The shot detector (strikes_v2) only fires on a speed INCREASE, so it saw no touch and gave Jaruzelski the assist (Sokker too).
A touch is dropped when ALL hold:
 (1) the ball moves (3-tick mean speed into t at least MIN_SPEED m per tick) and keeps its line: heading of t-3..t against t..t+3 changes by at most
     HEAD_DEG degrees, and the 3-tick mean speed out is within SPEED_TOL of the mean speed in;
 (2) the ball is not lifted (height at t+3 at most LIFT_Z above the height at t, so headers and flicks stay);
 (3) no player within R_ANIM m of the ball starts an action animation in t-4..t+4 (the strikes_v4 test; touches_v5 already gives the touch to such a player).
Everything else as touches_v5. patch() replaces touches_v5's two functions in every module and function that holds them, so it may run after the
detectors were imported (rate_match_v8 does that)."""
import math, sys, types, gc
import touches_v5 as _v5
import strikes_v2 as _s2

MIN_SPEED, HEAD_DEG, SPEED_TOL, LIFT_Z, R_ANIM, W = 0.5, 12.0, 0.15, 0.3, 3.0, 3


def is_flythrough(M, x):
    B, P, N = M['ball'], M['P'], M['N']; t = x['t']
    if t < W or t + W >= N: return False
    a = (B[t][0] - B[t - W][0], B[t][1] - B[t - W][1]); b = (B[t + W][0] - B[t][0], B[t + W][1] - B[t][1])
    sa, sb = math.hypot(*a) / W, math.hypot(*b) / W
    if sa < MIN_SPEED or sb < 1e-6: return False
    if abs(sb - sa) > SPEED_TOL * sa: return False
    if abs(math.degrees((math.atan2(b[1], b[0]) - math.atan2(a[1], a[0]) + math.pi) % (2 * math.pi) - math.pi)) > HEAD_DEG: return False
    if B[t + W][2] - B[t][2] > LIFT_Z: return False
    for q in range(22):
        if math.hypot(P[q][t][0] - B[t][0], P[q][t][1] - B[t][1]) <= R_ANIM and any(
                P[q][u][2] not in _s2.LOCO and P[q][u][2] != P[q][u - 1][2] for u in range(max(1, t - 4), min(N, t + 5))):
            return False
    return True


def _filter(M, T):
    return [x for x in T if not is_flythrough(M, x)]


def touches_v2(M, **kw): return _filter(M, _v5.touches_v2(M, **kw))
def touches_v3(M, **kw): return _filter(M, _v5.touches_v3(M, **kw))


SWAPPED = []


def patch():
    """Every holder of touches_v5.touches_v2 / touches_v3 (module globals, function globals) gets this module's version."""
    new = {_v5.touches_v2: touches_v2, _v5.touches_v3: touches_v3}
    dicts = {id(m.__dict__): m.__dict__ for m in list(sys.modules.values()) if m is not None and hasattr(m, '__dict__')}
    dicts.update({id(o.__globals__): o.__globals__ for o in gc.get_objects() if isinstance(o, types.FunctionType)})
    mine = globals()
    for d in dicts.values():
        if d is mine or d is _v5.__dict__: continue
        for k in [k for k, v in list(d.items()) if isinstance(v, types.FunctionType) and v in new]:
            d[k] = new[d[k]]; SWAPPED.append(f"{d.get('__name__', '?')}.{k}")
    return SWAPPED
