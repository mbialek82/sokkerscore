"""xg_features_v1.py — sokker_134. One row per shot (shot_analysis_v16) with the situation at the strike tick:
dist (m to goal centre), angle (deg of goal mouth visible), z (ball height), header (z >= 1.0),
cone_def (outfield opponents inside the triangle ball-post-post), gk_in_cone, gk_line (keeper's distance off his line),
gk_off (keeper's distance from the ball-goal-centre line), press (nearest opponent to the ball),
mates_ahead (team-mates nearer the goal than the ball, inside the box), kind (open / set piece / rebound / error),
speed (ball m/tick over the first 3 ticks), goal (Score-tab goal)."""
import sys, json, os, math
sys.path.insert(0, './shots'); sys.path.insert(0, './poss')
from multiprocessing import Pool
HALF_GOAL = 3.66

def in_tri(p, a, b, c):
    d = lambda p1, p2, p3: (p1[0]-p3[0])*(p2[1]-p3[1]) - (p2[0]-p3[0])*(p1[1]-p3[1])
    d1, d2, d3 = d(p, a, b), d(p, b, c), d(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

def one(args):
    path, mid, season = args
    import shot_analysis_v16 as sa
    from shots_v9 import team, attack_side
    M, rows, who, *_ = sa.analyse(path)
    B, P, gx = M['ball'], M['P'], M['gx']
    out = []
    for r in rows:
        t, sl, T = r['tick'], r['slot'], r['team']; side = attack_side(M, T, t)
        bx, by, bz = B[t][0] * side, B[t][1] * side, B[t][2]          # attacking towards +x
        gpos = lambda q: (P[q][t][0] * side, P[q][t][1] * side)
        p1, p2 = (gx, -HALF_GOAL), (gx, HALF_GOAL)
        a1 = math.atan2(p1[1] - by, p1[0] - bx); a2 = math.atan2(p2[1] - by, p2[0] - bx)
        ang = abs(math.degrees(a2 - a1))
        opp = [q for q in range(22) if team(q) != T]; kq = 21 if T == 'A' else 10
        cone = sum(in_tri(gpos(q), (bx, by), p1, p2) for q in opp if q != kq)
        kx, ky = gpos(kq)
        dx, dy = gx - bx, -by; L = math.hypot(dx, dy) or 1
        gk_off = abs((kx - bx) * dy - (ky - by) * dx) / L
        press = min(math.hypot(gpos(q)[0] - bx, gpos(q)[1] - by) for q in opp if q != kq)
        mates = sum(1 for q in range(22) if team(q) == T and q != sl and gpos(q)[0] > bx and gx - gpos(q)[0] <= 16.5 and abs(gpos(q)[1]) <= 20.16)
        sp = max(math.dist(B[u][:2], B[u+1][:2]) for u in range(t, min(t+3, M['N']-1)))
        link = r['link'] or ''
        kind = 'set' if 'set piece' in link else 'rebound' if 'rebound' in link or 'parry' in link else 'error' if link == 'error' else 'open'
        out.append(dict(season=season, id=mid, tick=t, minute=r['minute'], team=T, shooter=r['shooter'], outcome=r['outcome'],
                        goal=int(r['outcome'] == 'goal'), dist=round(math.hypot(gx - bx, by), 2), angle=round(ang, 2), z=round(bz, 2),
                        header=int(bz >= 1.0), cone_def=cone, gk_in_cone=int(in_tri((kx, ky), (bx, by), p1, p2)),
                        gk_line=round(gx - kx, 2), gk_off=round(gk_off, 2), press=round(press, 2), mates_ahead=mates,
                        kind=kind, speed=round(sp, 2)))
    return out

if __name__ == '__main__':
    season = int(sys.argv[1]); base = f'./s{season}'
    meta = json.load(open(f'{base}/s{season}_meta.json', encoding='utf-8'))
    jobs = [(f"{base}/bundles/match_{m['id']}.txt", m['id'], season) for m in meta]
    with Pool(os.cpu_count()) as p: res = p.map(one, jobs)
    rows = [x for r in res for x in r]
    json.dump(rows, open(f'./xg134/shots_s{season}_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(rows), 'shots', sum(r['goal'] for r in rows), 'goals')
