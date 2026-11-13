"""blocks_fouled_v2.py — v2 (the owner, 19 Oct: 14:12 in 44471278 the fouled player was Inczewski): the fouled player is the
last opponent to touch the ball before the foul (within FOUL_T ticks); the nearest opponent only as a fallback.
Agrees with all 6 fouls in the two test matches.
blocks_fouled_v1.py — sokker_131 (the owner, 19 Oct): shots blocked (+0.1 for the blocker) and was fouled (+0.05).
Block: for every shot that shot_analysis_v13 calls 'blocked', the blocker is the first opponent to touch the ball
after the shot (touches_v3).
Was fouled: for every Score-tab FOUL (tag 12, which names only the fouler), the fouled player is the opponent
nearest the fouler at that tick (all 6 fouls in the two test matches have him within 3 m); 14:12 in 44471278 is
the one case where he (Kupecký) is not the last opponent to touch the ball (Inczewski, 1 tick earlier)."""
import sys, math
for p in ('./poss', './shots'): sys.path.insert(0, p)
from collections import defaultdict
from touches_v3 import touches, load
from shots_v6 import team
from shot_analysis_v13 import analyse

FOUL_T = 30

def blocks_fouled(path):
    M0, rows, who, played, *_ = analyse(path)
    M = load(path); T = touches(M); P = M['P']
    st = defaultdict(lambda: defaultdict(int)); ev = []
    for r in rows:
        if r['outcome'] != 'blocked': continue
        x = next((x for x in T if x['t'] > r['tick'] and team(x['slot']) != r['team']), None)
        if x is None: continue
        n = who(x['slot'], x['t']); st[n]['blocks'] += 1
        ev.append(dict(kind='block', t=r['tick'], player=n, shooter=r['shooter']))
    for t, J, p in M['ev']:
        if J != 12: continue
        f = p[0]
        prev = [x for x in T if x['t'] <= t and team(x['slot']) != team(f)]
        if prev and t - prev[-1]['t'] <= FOUL_T: q = prev[-1]['slot']
        else: q = min((q for q in range(22) if team(q) != team(f)), key=lambda q: math.hypot(P[q][t][0]-P[f][t][0], P[q][t][1]-P[f][t][1]))
        n = who(q, t); st[n]['was_fouled'] += 1
        ev.append(dict(kind='fouled', t=t, player=n, fouler=who(f, t)))
    out = {n: dict(blocks=st[n]['blocks'], was_fouled=st[n]['was_fouled']) for n, (s, on, off) in played.items() if on < off}
    return out, ev

if __name__ == '__main__':
    out, ev = blocks_fouled(sys.argv[1])
    for e in ev: print(e)
