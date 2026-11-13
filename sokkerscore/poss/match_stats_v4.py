"""match_stats_v4.py — v4 (31 Oct, the owner's annotation of 44496766, sokker_145): a pass between team-mates needs >= 1 m of ball
travel (was 3: 2:50 Temelkoski -> Bas); a loss with < 3 m of travel is a DISPOSSESSION when an opponent was within 3 m of the
ball, however many touches the player had (0:55 Järvelin by Coc), and an UNSUCCESSFUL TOUCH only when nobody was near; a short
touch that runs out of play to an opponent restart is one of those two, not a pass or clearance (7:30 Rădoi).
match_stats_v3.py — working restore of the project copy (sokker_125/match_stats_v3.py), code verbatim; full changelog there."""
import sys, math
sys.path.insert(0, './poss'); sys.path.insert(0, './shots')
from collections import defaultdict
from touches_v2 import touches, load
from shots_v6 import team, attack_side
from shot_analysis_v10 import analyse as shot_analyse, ratings as shot_ratings, occupancy

PASS_MIN_M = 3.0
PASS_SAME_M, CLOSE_M = 1.0, 3.0

def match_stats(path):
    M0, shot_rows, who, played, *_ = shot_analyse(path)
    M = load(path); T = touches(M); B = M['ball']; P = M['P']; v = M['v']
    gx = M['gx']; gy = float(v.get('pitchwidth', 64)) / 2
    shot_ticks = [r['tick'] for r in shot_rows]
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    st = defaultdict(lambda: defaultdict(int))
    for i, a in enumerate(T):
        pa = who(a['slot'], a['t']); st[pa]['touches'] += 1
        if i + 1 >= len(T): break
        b = T[i+1]
        if b['slot'] == a['slot'] or any(a['t'] < e <= b['t'] for e in breaks): continue
        is_shot = any(abs(a['t'] - s) <= 2 for s in shot_ticks)
        out_u = next((u for u in range(a['t'], b['t'] + 1) if abs(B[u][0]) > gx + 0.3 or abs(B[u][1]) > gy + 0.3), None)
        same = team(b['slot']) == team(a['slot'])
        travelled = max(math.dist(B[u][:2], (a['x'], a['y'])) for u in range(a['t'], (out_u if out_u is not None else b['t']) + 1))
        pb = who(b['slot'], b['t'])
        close = min(math.hypot(P[q][a['t']][0] - a['x'], P[q][a['t']][1] - a['y']) for q in range(22) if team(q) != team(a['slot']))
        if not same and not is_shot and travelled < PASS_MIN_M:
            st[pa]['poss_lost'] += 1; st[pb]['ball_won'] += 1
            st[pa]['dispossessed' if close <= CLOSE_M else 'bad_touch'] += 1
            continue
        if out_u is not None:
            if same or is_shot: continue                       # own restart (missed touch) or a shot
            side = attack_side(M, team(a['slot']), a['t'])
            opp = min(math.hypot(P[q][a['t']][0] - a['x'], P[q][a['t']][1] - a['y']) for q in range(22) if team(q) != team(a['slot']))
            if a['x'] * side < -gx / 3 or (a['x'] * side < 0 and opp <= 3.0):
                st[pa]['clearance_out'] += 1
            else:
                st[pa]['pass_att'] += 1; st[pa]['pass_out'] += 1
            continue
        if not same:
            st[pa]['poss_lost'] += 1; st[pb]['ball_won'] += 1
        if is_shot: continue
        if same and travelled < PASS_SAME_M: continue          # tiny contact between team-mates: not a pass
        st[pa]['pass_att'] += 1
        st[pa]['pass_acc' if same else 'pass_to_opp'] += 1
    rat = {r['name']: r for r in shot_ratings(M0, shot_rows, who, played)}
    rows = []
    for name, (slot, on, off) in played.items():
        if on >= off: continue
        s = st[name]; r = rat.get(name, {})
        rows.append(dict(name=name, team=team(slot), gk=slot in (10, 21), minutes=f'{on}-{off}',
                         passes=f"{s['pass_acc']}/{s['pass_att']}" + (f" ({round(100*s['pass_acc']/s['pass_att'])}%)" if s['pass_att'] else ''),
                         pass_acc=s['pass_acc'], pass_att=s['pass_att'], pass_to_opp=s['pass_to_opp'], pass_out=s['pass_out'],
                         clearance_out=s['clearance_out'], bad_touch=s['bad_touch'], dispossessed=s['dispossessed'], poss_lost=s['poss_lost'], ball_won=s['ball_won'], touches=s['touches'],
                         rating_shots_only=r.get('rating'), **{k: r[k] for k in r if k not in ('name', 'team', 'gk', 'minutes', 'rating', 'raw')}))
    return M, sorted(rows, key=lambda d: (d['team'], -d['pass_att']))
