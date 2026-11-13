"""add_shot_detail_v5.py — v5 (11 Nov 2026): add_shot_detail_v4 as a function for ONE match (live/rate_match_v1): the bundle path and the
shot rows are arguments, so there is no lookup in run_all's path table (which only knows the 63 published matches). The per-shot logic
is v4's, unchanged: gl, y, spd, and where the shot was heading at the goal line (ey, ez; ex = 1 when the ball really reached the line,
0 when it was stopped first and the point is projected from the strike's first 3 ticks). "Lost to keeper" entries have no feature row
and are skipped. Must be imported after build_data_v36 (the loader and shot patches)."""
import sys, math
for p in ('./poss', './shots'): sys.path.insert(0, p)
from strikes_v3 import load
from shots_v9 import attack_side

G = 9.81 / (184 / 60) ** 2 / 3.0   # rough gravity per tick^2 on Sokker's clock; only used for projected heights


def apply(m, rows, bundle):
    R = sorted(rows, key=lambda x: x['tick'])
    real_shots = [s for s in m['shots'] if s.get('out') != 'lost to keeper']
    assert len(R) == len(real_shots), (m['id'], len(R), len(real_shots))
    M = load(bundle); B = M['ball']; gx = M['gx']; N = M['N']
    real = 0
    for s, x in zip(real_shots, R):
        t = x['tick']; side = attack_side(M, x['team'], t)
        s['gl'] = round(gx - B[t][0] * side, 1); s['y'] = round(-B[t][1] * side, 1); s['spd'] = round(x['speed'], 2)
        ey = ez = None; ex = 0
        for u in range(t + 1, min(N - 1, t + 60)):
            a, b = B[u][0] * side, B[u + 1][0] * side
            if a < gx <= b:
                f = (gx - a) / (b - a) if b != a else 0
                ey = -(B[u][1] + f * (B[u + 1][1] - B[u][1])) * side; ez = B[u][2] + f * (B[u + 1][2] - B[u][2]); ex = 1; break
            if b < a - 0.05 or math.dist(B[u][:2], B[u + 1][:2]) < 0.05: break      # turned back / stopped
        if not ex:
            vx = (B[t + 3][0] - B[t][0]) / 3 * side; vy = (B[t + 3][1] - B[t][1]) / 3; vz = (B[t + 3][2] - B[t][2]) / 3
            if vx > 0.05:
                k = (gx - B[t][0] * side) / vx
                ey = -(B[t][1] + vy * k) * side; ez = max(0.0, B[t][2] + vz * k - 0.5 * G * k * k)
        real += ex
        s['ey'] = None if ey is None else round(ey, 2); s['ez'] = None if ez is None else round(ez, 2); s['ex'] = ex
    return real
