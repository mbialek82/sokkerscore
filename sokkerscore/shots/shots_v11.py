"""shots_v11.py — v11 (10 Nov 2026, the owner: "you can shoot from anywhere, the engine must display those differently"): the kick animation, not distance or height, separates shots from passes.
A strike whose credited player starts a pass-kick animation (4, 18 or 19) within 3 ticks of it is never a shot, unless the ball crosses the goal line inside the goal. A strike followed by an OFFSIDE event within 40 ticks
is never a shot (it was a pass to an offside player). The distance limit goes to 60 m and the height rule (LOFT_Z) is switched off, because the animation does their job.
Tested on 146 matches against Sokker's shot counts: mean error per team 1.144 (35 m + height rule + offside) -> 1.041; removes 10 of the 12 false long shots the owner reviewed and keeps Abutreika's real 42 m shot (animation 11).
Replaces shots_v10 (50 m, never published). shots_v9.shots must be replaced by this function BEFORE any detector imports it (see build_data_v32)."""
import shots_v9 as _s9

MAXD = 60.0
LOFT_Z = 99.0
PASS_ANIM = {4, 18, 19}
ANIM_WIN = 3
OFFSIDE_TICKS = 40
_orig = _s9.shots


def anim(M, slot, t):
    """First non-locomotion animation the player starts in t-3..t+3, or None."""
    P, N = M['P'], M['N']
    for u in range(max(1, t - ANIM_WIN), min(N, t + ANIM_WIN + 1)):
        a = P[slot][u][2]
        if a not in _s9.LOCO and a != P[slot][u - 1][2]: return a
    return None


def in_goal(r):
    e = r['end']
    return e[0] == 'line' and bool(e[4])


def shots(M, S, **kw):
    kw.setdefault('MAXD', MAXD); kw.setdefault('LOFT_Z', LOFT_Z)
    off = [t for t, J, p in M['ev'] if J == 11]
    out = []
    for r in _orig(M, S, **kw):
        if any(r['t'] <= x <= r['t'] + OFFSIDE_TICKS for x in off): continue
        if anim(M, r['slot'], r['t']) in PASS_ANIM and not in_goal(r): continue
        out.append(r)
    return out
