"""touches_v2.py — working restore of the project copy (sokker_125/touches_v2.py), code verbatim.
v2: a touch needs the ball within reach — height <= Z_REACH m (keepers <= Z_REACH_GK)."""
import sys, math
sys.path.insert(0, './shots')
from strikes_v2 import load, LOCO
from shots_v6 import attribute

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
    return attribute(M, out)
