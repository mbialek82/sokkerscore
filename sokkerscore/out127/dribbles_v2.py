"""dribbles_v2.py — working restore of the project copy (sokker_127/dribbles_v2.py), code verbatim; full changelog there."""
import sys, math
sys.path.insert(0, './poss'); sys.path.insert(0, './shots')
from collections import defaultdict
from touches_v2 import touches, load
from shots_v6 import team, attack_side
from shot_analysis_v10 import occupancy

CHALLENGE_M, BEHIND_M = 3.0, 1.0

def dribbles(path):
    M = load(path); T = touches(M); P = M['P']; who, played = occupancy(M)
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    keep = []
    for k, x in enumerate(T):
        if keep and k + 1 < len(T) and team(x['slot']) != team(keep[-1]['slot']) and T[k+1]['slot'] == keep[-1]['slot'] \
                and T[k+1]['t'] - x['t'] <= 12 and math.dist(M['ball'][x['t']][:2], M['ball'][T[k+1]['t']][:2]) < 4.0:
            continue
        keep.append(x)
    T = keep
    carries, i = [], 0
    while i < len(T):
        j = i
        while j + 1 < len(T) and T[j+1]['slot'] == T[i]['slot'] and not any(T[j]['t'] < e <= T[j+1]['t'] for e in breaks):
            j += 1
        carries.append((i, j)); i = j + 1
    st = defaultdict(lambda: defaultdict(int)); events = []
    for i, j in carries:
        s = T[i]['slot']; tm = team(s); t0, t1 = T[i]['t'], T[j]['t']
        if t1 - t0 < 3: continue
        nxt = T[j+1] if j + 1 < len(T) else None
        broken = nxt is not None and any(t1 < e <= nxt['t'] for e in breaks)
        lost_to = nxt['slot'] if (nxt is not None and not broken and team(nxt['slot']) != tm) else None
        gx = M['gx']; gy = float(M['v'].get('pitchwidth', 64)) / 2; B = M['ball']
        if lost_to is not None and any(abs(B[u][0]) > gx + 0.3 or abs(B[u][1]) > gy + 0.3 for u in range(t1, nxt['t'] + 1)):
            # out of play: a failed dribble only against an opponent contesting the last touch
            cont = [q for q in range(22) if team(q) != tm and math.hypot(P[q][t1][0]-B[t1][0], P[q][t1][1]-B[t1][1]) <= CHALLENGE_M]
            lost_to = cont[0] if cont else None
        side = attack_side(M, tm, t0)
        for q in range(22):
            if team(q) == tm: continue
            ahead_close = [t for t in range(t0, t1 + 1)
                           if math.hypot(P[q][t][0]-P[s][t][0], P[q][t][1]-P[s][t][1]) <= CHALLENGE_M
                           and (P[q][t][0] - P[s][t][0]) * side > 0]
            if not ahead_close: continue
            ta = ahead_close[0]
            beaten = any((P[q][t][0] - P[s][t][0]) * side <= -BEHIND_M for t in range(ta, t1 + 1))
            carrier, opp = who(s, ta), who(q, ta)
            if beaten:
                st[carrier]['drib_won'] += 1; st[opp]['dribbled_past'] += 1; st[carrier]['drib_att'] += 1
                events.append(dict(t=ta, minute=M['minute'](ta), carrier=carrier, opponent=opp, result='success', won_by=None))
            if lost_to is not None and (lost_to == q or math.hypot(P[lost_to][nxt['t']][0]-P[s][nxt['t']][0],
                                                                    P[lost_to][nxt['t']][1]-P[s][nxt['t']][1]) <= CHALLENGE_M):
                st[carrier]['drib_lost'] += 1; res = 'failed'
            else:
                continue
            st[carrier]['drib_att'] += 1
            events.append(dict(t=nxt['t'] - 3 if beaten else ta, minute=M['minute'](ta), carrier=carrier, opponent=opp, result=res,
                               won_by=who(lost_to, nxt['t']) if lost_to is not None else None))
    rows = []
    for name, (slot, on, off) in played.items():
        if on >= off: continue
        s = st[name]
        rows.append(dict(name=name, team=team(slot), minutes=f'{on}-{off}', dribbles=f"{s['drib_won']}/{s['drib_att']}",
                         drib_won=s['drib_won'], drib_att=s['drib_att'], drib_lost=s['drib_lost'], dribbled_past=s['dribbled_past']))
    return M, sorted(rows, key=lambda r: (r['team'], -r['drib_att'])), events
