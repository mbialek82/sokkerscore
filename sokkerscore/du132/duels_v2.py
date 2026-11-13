"""duels_v2.py — v2 (31 Oct, the owner's annotation of 44496766): an aerial duel counts with the opponent within AIR_DUEL_M = 2.5 m
of the ball (ground stays 1.5 m) — 11:10 Temelkoski v Tabaczyński was 1.7 m apart; uses tackles_v6 and interceptions_v3
(contested headers are no longer interceptions, so they reach this detector).
duels_v1.py — sokker_132 (the owner, 19 Oct): ground duels (ball low) and aerial duels (ball high).
Weights (ratings_v10): ground won +0.02, lost -0.02; aerial won +0.05, lost -0.05.
Only contests NOT already counted as a tackle, dribble, interception or foul (the owner: "only other contests").
Detector, on touches_v3:
  a duel = a touch by player s with an opponent q within DUEL_M of the ball at that tick (q is the nearest such);
  aerial when the ball is at least AERIAL_Z high at the touch, otherwise ground;
  aerial winner = the player who got his head/body to the ball (s); q loses;
  ground winner = the side that has the next touch (within KEEP_T ticks, no break): s's team -> s wins, q loses;
                  q's team -> q wins, s loses; nobody (break / out of play) -> not counted;
  skipped: shots (+/-2 ticks), dead-ball restarts, and any moment within SKIP_T ticks of a tackle, dribble,
  interception or foul involving s or q; one duel per pair within PAIR_T ticks."""
import sys, math
for p in ('./poss', './shots', './def', './out127', './int130'): sys.path.insert(0, p)
from collections import defaultdict
from touches_v3 import touches, load
from shots_v6 import team
from shot_analysis_v13 import analyse, dead_ball
from tackles_v6 import tackles
from dribbles_v2 import dribbles
from interceptions_v3 import interceptions

DUEL_M, AERIAL_Z, KEEP_T, SKIP_T, PAIR_T = 1.5, 1.5, 15, 15, 15
AIR_DUEL_M = 2.5

def duels(path):
    M0, rows, who, played, *_ = analyse(path)
    M = load(path); T = touches(M); P = M['P']; B = M['ball']
    shot_ticks = [r['tick'] for r in rows]
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    busy = defaultdict(list)                                  # name -> ticks of events already counted elsewhere
    for e in tackles(path)[2]: busy[e['tackler']].append(e['t']); busy[e['on']].append(e['t'])
    for e in dribbles(path)[2]:
        busy[e['carrier']].append(e['t']); busy[e['opponent']].append(e['t'])
        if e.get('won_by'): busy[e['won_by']].append(e['t'])
    for e in interceptions(path)[2]: busy[e['interceptor']].append(e['t']); busy[e['passer']].append(e['t'])
    for t, J, p in M['ev']:
        if J == 12:
            f = p[0]; busy[who(f, t)].append(t)
            q = min((q for q in range(22) if team(q) != team(f)), key=lambda q: math.hypot(P[q][t][0]-P[f][t][0], P[q][t][1]-P[f][t][1]))
            busy[who(q, t)].append(t)
    isbusy = lambda n, t: any(abs(u - t) <= SKIP_T for u in busy[n])
    st = defaultdict(lambda: defaultdict(int)); ev = []; last = {}
    for i, x in enumerate(T):
        t, s = x['t'], x['slot']
        if any(abs(t - u) <= 2 for u in shot_ticks) or dead_ball(M, t): continue
        opp = [(math.hypot(P[q][t][0]-B[t][0], P[q][t][1]-B[t][1]), q) for q in range(22) if team(q) != team(s)]
        d, q = min(opp)
        if d > (AIR_DUEL_M if B[t][2] >= AERIAL_Z else DUEL_M): continue
        ns, nq = who(s, t), who(q, t)
        if isbusy(ns, t) or isbusy(nq, t): continue
        key = frozenset((ns, nq))
        if key in last and t - last[key] <= PAIR_T: continue
        aerial = B[t][2] >= AERIAL_Z
        if aerial:
            win, lose = ns, nq
        else:
            nxt = T[i+1] if i + 1 < len(T) else None
            if nxt is None or nxt['t'] - t > KEEP_T or any(t < e <= nxt['t'] for e in breaks): continue
            win, lose = (ns, nq) if team(nxt['slot']) == team(s) else (nq, ns)
        last[key] = t
        k = 'aerial' if aerial else 'ground'
        st[win][k + '_won'] += 1; st[lose][k + '_lost'] += 1
        ev.append(dict(t=t, minute=M['minute'](t), kind=k, won=win, lost=lose, z=round(B[t][2], 1), d=round(d, 1)))
    out = {n: {k: st[n][k] for k in ('ground_won', 'ground_lost', 'aerial_won', 'aerial_lost')} for n, (s, on, off) in played.items() if on < off}
    return out, ev

if __name__ == '__main__':
    out, ev = duels(sys.argv[1])
    for k in ('ground', 'aerial'): print(k, sum(1 for e in ev if e['kind'] == k))
    for n, r in sorted(out.items(), key=lambda kv: -sum(kv[1].values())): print(n, r)
    for e in ev: print('EV', e)
