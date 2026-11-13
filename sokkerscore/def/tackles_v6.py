"""tackles_v6.py — v6 (31 Oct, the owner's annotation of 44496766): a ball taken off a player on his first touch counts as a tackle when the
taker was within CLOSE_M = 3.0 m of the ball (was 1.5), however long he took to get the ball off him ("dispossessed by opp 5",
0:55); slide tackles count from SLIDE_M = 3.5 m (was 3.0) with ball contact within CONTACT_M = 3.5 m (was 2.5) — the failed
tackles at 5:08 Quadri, 8:32 Sánchez Soler, 11:15 Helvei/Jaruzelski start 2.7-3.3 m from the ball. Old verdicts still 19/19.
tackles_v5.py — v5: uses touches_v3 (shared long kick credited to the player it went forward for). Otherwise = v4.
tackles_v4.py — (project copy has the full changelog).
v4 (19 Oct, from the user's video verdicts on 44471278, 5:41-15:30): stricter WON (KEEP_T), contested first touch
(CLOSE_M), RECOVERY for loose balls (LOOSE_T), CONTACT_M 2.5, slide lag (SLIDE_LAG_T), keeper challenge (22/23)."""
import sys, math
sys.path.insert(0, './poss'); sys.path.insert(0, './shots')
from collections import defaultdict
from touches_v3 import touches, load
from shots_v6 import team
from shot_analysis_v10 import occupancy

SLIDE_M, OFF_FOOT_M, CONTACT_M = 3.5, 3.0, 3.5
KEEP_T, CLOSE_M, LOOSE_T, GK_CHALLENGE, SLIDE_LAG_T = 15, 3.0, 8, (22, 23), 8

def tackles(path):
    M = load(path); T = touches(M); P = M['P']; B = M['ball']; who, played = occupancy(M); N = M['N']
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    st = defaultdict(lambda: defaultdict(int)); ev = []; rec = []
    def won_after(j, q, t0):
        # j = index of first touch after the tackle moment t0
        if j >= len(T) or team(T[j]['slot']) != team(q): return False
        t1 = T[j]['t']
        for k in range(j, len(T)):
            if T[k]['t'] - t1 > KEEP_T: break
            if any(t0 < e <= T[k]['t'] for e in breaks): break
            if team(T[k]['slot']) != team(q): return False
        return True
    for i in range(len(T) - 1):
        a, b = T[i], T[i+1]
        if any(a['t'] < e <= b['t'] for e in breaks): continue
        tm = team(a['slot']); done = set()
        # (a) off the foot
        run = 1; k = i - 1
        while k >= 0 and T[k]['slot'] == a['slot'] and not any(T[k]['t'] < e <= T[k+1]['t'] for e in breaks):
            run += 1; k -= 1
        if team(b['slot']) != tm and max(math.dist(B[u][:2], B[a['t']][:2]) for u in range(a['t'], b['t'] + 1)) < OFF_FOOT_M:
            q = b['slot']
            close = math.hypot(P[q][a['t']][0]-B[a['t']][0], P[q][a['t']][1]-B[a['t']][1]) <= CLOSE_M
            if b['t'] - a['t'] >= LOOSE_T and not close:
                rec.append(dict(t=b['t'], player=who(q, b['t']), after=who(a['slot'], a['t']))); done.add(q)
            elif run >= 2 or close:
                done.add(q)
                ev.append(dict(t=b['t'], tackler=who(q, b['t']), on=who(a['slot'], a['t']), how='took it', won=won_after(i+1, q, b['t'])))
        # (b) sliding tackles while the opponent has the ball (between his touch and the next one)
        for q in range(22):
            if team(q) == tm or q in done: continue
            for u in range(a['t'] + 1, b['t'] + 1):
                c = a['slot']
                code = P[q][u][2]; gk = q in (10, 21) and code in GK_CHALLENGE
                if (code == 2 or gk) and P[q][u-1][2] != code and math.hypot(P[q][u][0]-P[c][u][0], P[q][u][1]-P[c][u][1]) <= SLIDE_M:
                    j = i + 1
                    if j < len(T) and T[j]['slot'] == c and T[j]['t'] - u <= SLIDE_LAG_T: j += 1   # carrier's touch as the tackle arrives
                    won = won_after(j, q, u)
                    contact = any(math.hypot(P[q][w][0]-B[w][0], P[q][w][1]-B[w][1]) <= CONTACT_M for w in range(u, min(N, u + 9)))
                    if not (won or contact or gk): break
                    ev.append(dict(t=u, tackler=who(q, u), on=who(a['slot'], a['t']), how='keeper' if gk else 'slide', won=won)); done.add(q)
                    break
    # one per defender per opponent run: collapse events by the same tackler within 15 ticks
    ev.sort(key=lambda e: e['t']); kept = []
    for e in ev:
        if kept and kept[-1]['tackler'] == e['tackler'] and e['t'] - kept[-1]['t'] <= 15:
            kept[-1]['won'] = kept[-1]['won'] or e['won']; continue
        kept.append(e)
    for e in kept:
        st[e['tackler']]['tackles'] += 1; st[e['tackler']]['tackles_won'] += int(e['won'])
    for r in rec: st[r['player']]['recoveries'] += 1
    rows = []
    for name, (slot, on, off) in played.items():
        if on >= off: continue
        s = st[name]
        rows.append(dict(name=name, team=team(slot), minutes=f'{on}-{off}', tackles=s['tackles'], tackles_won=s['tackles_won'], recoveries=s['recoveries'],
                         display=f"{s['tackles']} ({s['tackles_won']})"))
    return M, sorted(rows, key=lambda r: (r['team'], -r['tackles'])), kept, rec

if __name__ == '__main__':
    M, rows, ev, rec = tackles(sys.argv[1])
    for tm in 'AB':
        r = [x for x in rows if x['team'] == tm]
        print('TEAM', tm, 'tackles (won)', sum(x['tackles'] for x in r), f"({sum(x['tackles_won'] for x in r)})", 'recoveries', sum(x['recoveries'] for x in r))
    for x in rows: print(x)
    for e in ev: print('EV', e)
