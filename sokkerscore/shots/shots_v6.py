"""shots_v6.py — working restore of the project copy (sokker_124/shots_v6.py); only attribute/team/attack_side are
needed by the touch and tackle detectors, the shots() function is kept verbatim.
(Full changelog in the project copy.)"""
import sys, math
sys.path.insert(0, './shots')
from strikes_v2 import load, strikes

LOCO = {0, 5, 26, 27}

def attribute(M, S, CONTEST=1.5):
    P = M['P']
    evt = sorted(t for t, J, p in M['ev'] if J not in (2,))
    for s in S:
        t = s['t']; best = s['near'][0][0]
        cands = [q for d, q in sorted((math.hypot(P[q][t][0]-s['x'], P[q][t][1]-s['y']), q) for q in range(22))
                 if d <= best + CONTEST]
        def start_gap(q):
            g = None
            for u in range(max(1, t-3), min(M['N'], t+4)):
                if P[q][u][2] not in LOCO and P[q][u][2] != P[q][u-1][2]:
                    if g is None or abs(u-t) < g: g = abs(u-t)
            return g
        starts = [(start_gap(q), i, q) for i, q in enumerate(cands) if start_gap(q) is not None]
        s['slot'] = min(starts)[2] if starts else cands[0]
        s['cands'] = cands
    for i in range(len(S) - 1):
        s, n = S[i], S[i+1]
        if len(s['cands']) > 1 and team(n['slot']) != team(s['slot']) and n['slot'] not in (10, 21) and 10 < n['t'] - s['t'] <= 60 \
                and not any(s['t'] < e <= n['t'] for e in evt):
            mates = [q for q in s['cands'] if team(q) == team(n['slot']) and q != n['slot']]
            if mates: s['slot'] = mates[0]
    return S

def team(slot): return 'A' if slot <= 10 else 'B'

def attack_side(M, tm, t):          # x-sign of the goal team tm attacks at tick t
    d = 1 if tm == 'A' else -1
    return d if t < M['H'] else -d

def shots(M, S, MAXD=35.0, AIM=10.0, HW=4.0, HH=2.7, BLOCK_TICKS=10, BLOCK_M=12.0, MINV=0.8,
          LOFT_DIST=25.0, LOFT_Z=4.0, TACKLE_M=5.0):
    P = M['P']
    posts = [t for t, J, p in M['ev'] if J == 5]
    B, gx, N = M['ball'], M['gx'], M['N']
    out = []
    for i, s in enumerate(S):
        t, sl = s['t'], s['slot']; T = team(sl); side = attack_side(M, T, t)
        x, y = B[t][0], B[t][1]
        if x * side < 0 or math.hypot(gx - x*side, y) > MAXD: continue
        if t + 4 >= N: continue
        if max(math.dist(B[u][:2], B[u+1][:2]) for u in range(t, t+3)) < MINV: continue
        vx, vy = (B[t+3][0]-B[t+1][0]) / 2, (B[t+3][1]-B[t+1][1]) / 2
        if vx * side <= 0.05: continue
        aim = B[t+1][1] + (side*gx - B[t+1][0]) * vy / vx
        if abs(aim) > AIM: continue
        nxt = S[i+1] if i + 1 < len(S) else None
        end_t = nxt['t'] if nxt else N - 1
        res = None
        wood = [pt for pt in posts if t < pt <= min(end_t, t+120) + 3]
        if wood:
            res = ('woodwork', wood[0])
        for u in ([] if res else range(t+1, min(end_t, t+120) + 1)):
            if B[u][0] * side >= gx:                     # crossed goal line
                f = B[u-1]; g = B[u]; k = (side*gx - f[0]) / (g[0]-f[0]) if g[0] != f[0] else 0
                cy, cz = f[1] + k*(g[1]-f[1]), f[2] + k*(g[2]-f[2])
                if abs(cy) <= AIM:
                    res = ('line', u, round(cy, 1), round(cz, 1), abs(cy) <= HW and cz <= HH)
                break
        if res is None and nxt and nxt['t'] <= t + 120:
            q = nxt['slot']
            if team(q) == T: continue                      # a pass / cross
            if q in (10, 21):
                res = ('keeper', nxt['t'], q)
            elif nxt['t'] - t <= BLOCK_TICKS and math.hypot(nxt['x'] - x, nxt['y'] - y) <= BLOCK_M:
                res = ('blocked', nxt['t'], q)
        if res is None: continue
        dist = math.hypot(gx - x*side, y)
        if res[0] == 'keeper' and dist >= LOFT_DIST and max(B[u][2] for u in range(t, res[1] + 1)) >= LOFT_Z:
            continue
        if res[0] != 'blocked' and any(team(q) != T and math.hypot(P[q][t][0] - x, P[q][t][1] - y) <= TACKLE_M
               and any(P[q][u][2] == 2 and P[q][u-1][2] != 2 for u in range(max(1, t-2), min(N, t+4)))
               for q in range(22)):
            continue
        out.append(dict(t=t, minute=M['minute'](t), slot=sl, team=T, x=round(x, 1), y=round(y, 1), z=round(B[t][2], 1),
                        dist=round(math.hypot(gx - x*side, y), 1), aim=round(aim, 1), end=res, idx=i))
    return out
