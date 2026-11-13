"""strikes_v2.py — v2: a player 2-3 m from the ball counts as the toucher when nobody is within R and he starts
an action animation (not 0/5/26/27) within -2..+3 ticks (stretching touch; Inczewski at 47:37 in 44471278 played
the ball from 2.7 m with animation 2 and was missed). A stretching touch within 5 ticks of the same player's
previous strike is his follow-through, not a new touch (else Berlinger's 49' shot in 43761572 became a pass to himself).
strikes_v1.py — touch/strike stream from ball physics on the v5 decoder (diagnostic).
A strike = tick where the ball's 3-D motion changes sharply (direction > ANG deg, speed
change > DV m/tick, or vertical bounce/kick) with a player within R m. Consecutive
detections within MERGE ticks collapse to the first. Also returns the minute of each tick
from the Score tab (MINUTE events at cumulative/6)."""
import sys, math
sys.path.insert(0, './pipe')
from bundle_decoder import (load_bundle, get_tabs, get_vars, decode_ball_per_frame,
                            decode_human, interp_player_to_ticks, to_flash_i)
from match_stats import find_halftime_tick

PAY = {1: 2, 2: 2, 3: 2, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1, 15: 1}

def score_events(d):
    out, x = [], 2
    cum = to_flash_i(d, 0) - 1
    while x + 1 < len(d) and d[x] >= 0:
        J = d[x]; x += 1
        out.append((cum // 6, J, d[x:x + PAY.get(J, 0)]))
        x += PAY.get(J, 0)
        if x + 1 >= len(d) or d[x] < 0 or d[x + 1] < 0: break
        cum += to_flash_i(d, x); x += 2
    return out

def load(path):
    b = load_bundle(path); tabs = get_tabs(b); v = get_vars(b)
    ball = decode_ball_per_frame(tabs['Ball']); N = len(ball)
    P = {s: interp_player_to_ticks(decode_human(tabs[f'Human{s}']), N) for s in range(22)}
    ev = score_events(tabs['Score'])
    minutes = [(t, p[0] + 69 * p[1]) for t, J, p in ev if J == 2]
    def minute(t):
        m = 0
        for tt, mm in minutes:
            if tt <= t: m = mm
            else: break
        return m
    return dict(ball=[(p.x/10, p.y/10, p.z/10) for p in ball], P=P, N=N, v=v, ev=ev,
                H=find_halftime_tick(tabs['Score']), gx=float(v.get('pitchheight', 102))/2, minute=minute)

LOCO = {0, 5, 26, 27}

def strikes(M, ANG=12.0, DV=0.15, R=2.0, R_STRETCH=3.0, MERGE=2):
    B, P, N = M['ball'], M['P'], M['N']
    vel = [(0, 0, 0)] + [tuple(B[t][i] - B[t-1][i] for i in range(3)) for t in range(1, N)]
    out = []
    for t in range(2, N - 1):
        a, b = vel[t], vel[t + 1]                     # motion into t, motion out of t
        sa, sb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
        if sb < 0.15: continue
        if sa > 1e-6:
            c = max(-1, min(1, (a[0]*b[0] + a[1]*b[1]) / (sa * sb)))
            turn = math.degrees(math.acos(c))
        else:
            turn = 180.0
        lift = b[2] - a[2] > 0.25 and B[t][2] < 2.6     # kicked/headed upward
        if not (turn > ANG or sb - sa > DV or lift): continue
        ds = sorted((math.hypot(P[s][t][0] - B[t][0], P[s][t][1] - B[t][1]), s) for s in range(22))
        if ds[0][0] > R:
            st = [(d, q) for d, q in ds if d <= R_STRETCH and any(P[q][u][2] not in LOCO and P[q][u][2] != P[q][u-1][2]
                                                               for u in range(max(1, t-2), min(N, t+4)))]
            if not st: continue
            if out and st[0][1] == out[-1]['slot'] and t - out[-1]['t'] <= 5: continue
            ds = st + [x for x in ds if x not in st]
        if out and t - out[-1]['t'] <= MERGE: continue
        out.append(dict(t=t, slot=ds[0][1], d=round(ds[0][0], 2), near=[(round(d, 1), s) for d, s in ds[:3]],
                        x=B[t][0], y=B[t][1], z=B[t][2], speed_out=sb))
    return out
