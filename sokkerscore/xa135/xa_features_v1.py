"""xa_features_v1.py — sokker_135. One row per KEY PASS (a team-mate's pass straight before a shot; shot_analysis_v16 link
'key pass'), describing the pass: where it started and where the shooter received it, its type and how the shooter used it.
recv_dist   distance to goal where the shooter first touched the ball
orig_dist   distance to goal where the pass was played; orig_wide = started outside the box's width (|y| > 20.16 m)
length      straight-line length (m); peak = highest ball point during the pass (m)
ptype       cross (from wide, in the final 30 m, lofted) / lofted (peak >= 2 m) / ground
direction   back = cut-back (received nearer the goal line than ... ball travelled away from goal), forward otherwise
recv_cone   outfield defenders between the reception point and the goal; first_time = shot with the first touch
goal        the shot it set up went in (Score tab)."""
import sys, json, os, math
sys.path.insert(0, './shots'); sys.path.insert(0, './poss'); sys.path.insert(0, './xg134')
from multiprocessing import Pool
from xg_features_v1 import in_tri, HALF_GOAL

def one(args):
    path, mid, season = args
    import shot_analysis_v16 as sa
    from strikes_v2 import strikes
    from shots_v9 import attribute, team, attack_side
    M, rows, who, *_ = sa.analyse(path)
    S = attribute(M, strikes(M)); B, P, gx = M['ball'], M['P'], M['gx']
    idx = {(s['t'], s['slot']): k for k, s in enumerate(S)}
    out = []
    for r in rows:
        if r['link'] != 'key pass': continue
        k = idx.get((r['tick'], r['slot']))
        if k is None: continue
        j = k - 1
        while j >= 0 and S[j]['slot'] == r['slot']: j -= 1
        if j < 0: continue
        p, rc = S[j], S[j + 1]; T = r['team']; side = attack_side(M, T, p['t'])
        ox, oy = B[p['t']][0] * side, B[p['t']][1] * side; rx, ry = B[rc['t']][0] * side, B[rc['t']][1] * side
        peak = max(B[u][2] for u in range(p['t'], rc['t'] + 1))
        orig_dist = math.hypot(gx - ox, oy); recv_dist = math.hypot(gx - rx, ry)
        orig_wide = abs(oy) > 20.16
        ptype = 'cross' if (orig_wide and gx - ox <= 30 and peak >= 1.5) else 'lofted' if peak >= 2.0 else 'ground'
        direction = 'back' if (rx < ox - 1.0 and gx - ox <= 20) else 'forward'
        kq = 21 if T == 'A' else 10
        cone = sum(in_tri((P[q][rc['t']][0] * side, P[q][rc['t']][1] * side), (rx, ry), (gx, -HALF_GOAL), (gx, HALF_GOAL))
                   for q in range(22) if team(q) != T and q != kq)
        out.append(dict(season=season, id=mid, shot_tick=r['tick'], passer=r['prev_player'], shooter=r['shooter'], team=T,
                        goal=int(r['outcome'] == 'goal'), recv_dist=round(recv_dist, 2), orig_dist=round(orig_dist, 2),
                        orig_wide=int(orig_wide), length=round(math.dist((ox, oy), (rx, ry)), 2), peak=round(peak, 2),
                        ptype=ptype, direction=direction, recv_cone=cone, first_time=int(k == j + 1)))
    return out

if __name__ == '__main__':
    season = int(sys.argv[1]); base = f'./s{season}'
    meta = json.load(open(f'{base}/s{season}_meta.json', encoding='utf-8'))
    jobs = [(f"{base}/bundles/match_{m['id']}.txt", m['id'], season) for m in meta]
    with Pool(os.cpu_count()) as p: res = p.map(one, jobs)
    rows = [x for r in res for x in r]
    json.dump(rows, open(f'./xa135/keypasses_s{season}_v1.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(rows), 'key passes', sum(r['goal'] for r in rows), 'led to goals')
