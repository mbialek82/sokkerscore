"""extras_v2.py — v2 (7 Nov 2026, the owner, decision 19): each dispossession is also checked against tackles_v6: if the same player
was credited a WON tackle within TACKLE_T = 15 ticks of it, the action is one and the same and only the tackle bonus applies.
New stat `dispossessions_solo` = dispossessions with no such tackle credit (these get the +0.05 in ratings_v26); events carry
`tackle=True/False`. Everything else exactly as extras_v1.
extras_v1.py — v1 (7 Nov 2026, sokker_162): new per-player stats for the tabbed player card, agreed with the owner:
- touches: every touch (strike) attributed to the player (same touches_v3 list match_stats uses).
- crosses (Opta style): open-play pass from the wide area of the final third (outside the width of the box, |y| > 20.16 m,
  x beyond the last third line) whose path enters the opponents' box before the next touch; corners/free kicks (restarts)
  and shots excluded. Accurate = next touch by a team-mate.
- clearances (Opta style): first-time touch (not his own previous touch) by an outfield player in his own third, not a
  restart or shot, that sends the ball >= 10 m and >= 5 m away from his own goal, with no team-mate receiving it (next
  touch by an opponent, or out of play), or that goes high (peak > 3 m) whoever gets it.
- dispossessions: times he took the ball off an opponent who was then counted as 'Dispossessed' (match_stats_v4 rule:
  loss with < 3 m of ball travel and an opponent within 3 m) — the winner's side of that event.
- keeper: high claim = keeper's first touch of a spell, not a restart and not a shot on him, ball >= 1.8 m high, then he
  holds it (ball within 1 m of him for >= 8 of the next 15 ticks); punch = same but not held and the ball leaves at
  >= 0.6 m/tick; run out = first touch of a spell, not a restart / shot on him, more than 6 m off his goal line with an
  opponent within 5 m of the ball, OR a smother (low ball < 1 m, opponent within 2.5 m, he held it, and he moved >= 3 m
  towards it in the previous 20 ticks); successful when the next touch by another player is a team-mate's.
Restart = the ball moved < 0.3 m in the 15 ticks before the touch."""
import sys, math
from collections import defaultdict
for p in ('./poss', './shots', './out127', './def', './int130', './du132', './ex162'):
    if p not in sys.path: sys.path.insert(0, p)
import strikes_v2, strikes_v3; strikes_v2.load = strikes_v3.load
import ratings_v22  # noqa: sets up the alias web exactly as the published build
from extras_v1 import extras as extras1
from tackles_v6 import tackles

TACKLE_T = 15

def extras(path):
    M, st, ev = extras1(path)
    _, _, kept, _ = tackles(path)
    won = defaultdict(list)                       # tackler name -> ticks of his WON tackles
    for e in kept:
        if e['won']: won[e['tackler']].append(e['t'])
    for e in ev:
        if e['kind'] != 'dispossession': continue
        tm, name = e['who']
        e['tackle'] = any(abs(e['t'] - t) <= TACKLE_T for t in won.get(name, []))
        if not e['tackle']:
            st.setdefault((tm, name), {}); st[(tm, name)]['dispossessions_solo'] = st[(tm, name)].get('dispossessions_solo', 0) + 1
    return M, st, ev

if __name__ == '__main__':
    M, st, ev = extras(sys.argv[1])
    for k, v in sorted(st.items()):
        x = {a: b for a, b in v.items() if a != 'touches' and b}
        print(k, v.get('touches'), x)
    print('dispossessions', sum(1 for e in ev if e['kind'] == 'dispossession'), 'of which also a won tackle',
          sum(1 for e in ev if e['kind'] == 'dispossession' and e['tackle']))
