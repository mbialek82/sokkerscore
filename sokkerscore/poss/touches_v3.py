"""touches_v3.py — v3 (19 Oct, the owner's verdicts on Macovei, 43761572 7:51 and 14:42): the contested-pass override in
shots_v6.attribute (credit a shared touch to the contender whose team-mate makes the next touch) no longer applies when the
animation evidence is clear — the first-pass pick STARTED an action animation within -3..+3 ticks of the touch and the
override's choice did not. At 7:51 and 14:42 Macovei starts a kick (animation 4) at t+2 while Herghelegiu stays in the
animation he was already in; the override had given both 28-37 m clearances to Herghelegiu, so Macovei's won tackles read
as "not won".
Rejected drafts (same day): crediting a shared long ball (>= 15 m) to the contender it went forward for — gave Suvanto's
19 m pass back at 17:10 (44471278) to Rădoi; adding "in his own half" did not separate them (Rădoi was at x = -6.9).
touches_v2.py — v2: a touch needs the ball within reach — height <= Z_REACH m (keepers <= Z_REACH_GK)."""
import sys, math
sys.path.insert(0, './shots')
from strikes_v2 import load, LOCO
from shots_v6 import attribute

def _start_gap(M, q, t):
    P = M['P']; g = None
    for u in range(max(1, t-3), min(M['N'], t+4)):
        if P[q][u][2] not in LOCO and P[q][u][2] != P[q][u-1][2]:
            if g is None or abs(u-t) < g: g = abs(u-t)
    return g

def touches(M, ANG=12.0, DV=0.15, R=2.0, R_STRETCH=3.0, MERGE=2, MIN_MOVE=0.15, Z_REACH=2.6, Z_REACH_GK=3.0):
    B, P, N = M['ball'], M['P'], M['N']
    vel = [(0, 0, 0)] + [tuple(B[t][i] - B[t-1][i] for i in range(3)) for t in range(1, N)]
    out = []
    for t in range(2, N - 1):
        a, b = vel[t], vel[t+1]
        sa, sb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
        if max(sa, sb) < MIN_MOVE: continue                  # ball at rest both sides
        if sa > 1e-6 and sb > 1e-6:
            turn = math.degrees(math.acos(max(-1, min(1, (a[0]*b[0] + a[1]*b[1]) / (sa*sb)))))
        else:
            turn = 180.0
        lift = b[2] - a[2] > 0.25 and B[t][2] < 2.6
        if not (turn > ANG or abs(sb - sa) > DV or lift): continue
        if B[t][2] > Z_REACH_GK: continue
        ds = sorted((math.hypot(P[s][t][0] - B[t][0], P[s][t][1] - B[t][1]), s) for s in range(22)
                    if B[t][2] <= Z_REACH or s in (10, 21))
        if not ds: continue
        if ds[0][0] > R:
            st = [(d, q) for d, q in ds if d <= R_STRETCH and any(P[q][u][2] not in LOCO and P[q][u][2] != P[q][u-1][2]
                                                               for u in range(max(1, t-2), min(N, t+4)))]
            if not st: continue
            if out and st[0][1] == out[-1]['slot'] and t - out[-1]['t'] <= 5: continue
            ds = st + [x for x in ds if x not in st]
        if out and t - out[-1]['t'] <= MERGE: continue
        out.append(dict(t=t, slot=ds[0][1], d=round(ds[0][0], 2), near=[(round(d, 1), s) for d, s in ds[:3]],
                        x=B[t][0], y=B[t][1], z=B[t][2], speed_out=sb, speed_in=sa))
    out = attribute(M, out)
    for x in out:                                   # v3 guard against the contested-pass override
        c = x.get('cands', [])
        if len(c) < 2: continue
        starts = sorted((g, i, q) for i, q in enumerate(c) if (g := _start_gap(M, q, x['t'])) is not None)
        if not starts: continue
        pick = starts[0][2]
        if x['slot'] != pick and _start_gap(M, x['slot'], x['t']) is None:
            x['slot'] = pick; x['anim_guard'] = True
    return out
