"""shots_v12.py — v12 (10 Nov 2026): the pass-kick rule of v11 applies only beyond 25 m, and the height rule comes back from 35 m. Why: v11's full rebuild (ratings_data_v44, not published) removed real close shots, low balls from 7-16 m
with xG up to 0.46 (Inczewski, Czerbniak, Zamolo), because near goal the engine also uses animations 4/18/19 for shots. It also added 50-59 m balls that peaked at 8-17 m and were caught by the keeper. On 146 matches against Sokker's shot counts:
mean error per team v42 rules 1.144, v11 1.041, v12 1.031.
Rules: a strike beyond 25 m whose credited player starts animation 4, 18 or 19 within 3 ticks is not a shot unless the ball crosses the line inside the goal; a strike followed by an OFFSIDE event within 40 ticks is not a shot; distance limit 60 m;
a strike from 35 m or further that ends with the keeper and peaks at 4 m or higher is not a shot (shots_v9's LOFT rule with LOFT_DIST 35).
shots_v9.shots must be replaced by this function BEFORE any detector imports it (see build_data_v33)."""
import shots_v9 as _s9
import shots_v11 as _s11

MAXD = 60.0
LOFT_DIST = 35.0
LOFT_Z = 4.0
ANIM_FROM = 25.0
_orig = _s11._orig


def shots(M, S, **kw):
    kw.setdefault('MAXD', MAXD); kw.setdefault('LOFT_DIST', LOFT_DIST); kw.setdefault('LOFT_Z', LOFT_Z)
    off = [t for t, J, p in M['ev'] if J == 11]
    out = []
    for r in _orig(M, S, **kw):
        if any(r['t'] <= x <= r['t'] + _s11.OFFSIDE_TICKS for x in off): continue
        if r['dist'] >= ANIM_FROM and _s11.anim(M, r['slot'], r['t']) in _s11.PASS_ANIM and not _s11.in_goal(r): continue
        out.append(r)
    return out
