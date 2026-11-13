"""extras_v1.py — v1 (7 Nov 2026, sokker_162): new per-player stats for the tabbed player card, agreed with the owner:
export (7 Nov 2026): absolute /home/claude/... paths made relative to sokkerscore/; code otherwise exactly as it last ran.
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
for p in ('./poss', './shots', './out127', './def', './int130', './du132'):
    if p not in sys.path: sys.path.insert(0, p)
import strikes_v2, strikes_v3; strikes_v2.load = strikes_v3.load
import ratings_v22  # noqa: sets up the alias web exactly as the published build
from shot_analysis_v17 import analyse as shot_analyse
from touches_v3 import touches
from shots_v9 import team, attack_side

BOX_D, BOX_W = 16.5, 20.16

def extras(path):
    M0, shot_rows, who, played, *_ = shot_analyse(path)
    M = strikes_v2.load(path); T = touches(M); B = M['ball']; P = M['P']; N = M['N']; gx = M['gx']
    gy = float(M['v'].get('pitchwidth', 64)) / 2
    shot_ticks = [r['tick'] for r in shot_rows]
    is_shot = lambda t: any(abs(t - s) <= 2 for s in shot_ticks)
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    restart = lambda t: max(math.dist(B[u][:2], B[t][:2]) for u in range(max(0, t - 15), t + 1)) < 0.3
    out_of = lambda u: abs(B[u][0]) > gx + 0.3 or abs(B[u][1]) > gy + 0.3
    st = defaultdict(lambda: defaultdict(int)); ev = []
    def nm(s, t): return (team(s), who(s, t))
    for i, a in enumerate(T):
        s, t = a['slot'], a['t']; k = nm(s, t); st[k]['touches'] += 1
        b = T[i + 1] if i + 1 < len(T) else None
        brk = b is None or any(t < e <= b['t'] for e in breaks)
        end = b['t'] if b else min(N - 1, t + 60)
        side = attack_side(M, team(s), t)
        out_u = next((u for u in range(t, end + 1) if out_of(u)), None)
        seg = range(t, (out_u if out_u is not None else end) + 1)
        travel = max(math.dist(B[u][:2], B[t][:2]) for u in seg)
        rs, sh = restart(t), is_shot(t)
        nxt_same = b is not None and not brk and out_u is None and b['slot'] != s and team(b['slot']) == team(s)
        prev = T[i - 1] if i else None
        # crosses
        if not rs and not sh and b is not None and b['slot'] != s and B[t][0] * side > gx / 3 and abs(B[t][1]) > BOX_W:
            if any(B[u][0] * side > gx - BOX_D and abs(B[u][1]) < BOX_W for u in seg):
                st[k]['cross_att'] += 1; st[k]['cross_acc'] += nxt_same
                ev.append(dict(kind='cross', acc=nxt_same, t=t, who=k))
        # clearances
        if s not in (10, 21) and not rs and not sh and B[t][0] * side < -gx / 3 and (prev is None or prev['slot'] != s):
            gain = max((B[u][0] - B[t][0]) * side for u in seg)
            peak = max(B[u][2] for u in seg)
            if travel >= 10 and gain >= 5 and (not nxt_same or peak > 3.0):
                st[k]['clearances2'] += 1; ev.append(dict(kind='clearance', t=t, who=k))
        # dispossessions (winner side of match_stats_v4's 'dispossessed')
        if b is not None and not brk and team(b['slot']) != team(s) and not sh:
            tr = max(math.dist(B[u][:2], (a['x'], a['y'])) for u in range(t, (out_u if out_u is not None else b['t']) + 1))
            close = min(math.hypot(P[q][t][0] - a['x'], P[q][t][1] - a['y']) for q in range(22) if team(q) != team(s))
            if tr < 3.0 and close <= 3.0:
                kb = nm(b['slot'], b['t']); st[kb]['dispossessions'] += 1; ev.append(dict(kind='dispossession', t=b['t'], who=kb, victim=k))
        # keeper
        if s in (10, 21) and not rs and (prev is None or prev['slot'] != s) and not (prev is not None and is_shot(prev['t']) and team(prev['slot']) != team(s)):
            held = sum(1 for u in range(t, min(N, t + 15)) if math.dist(B[u][:2], P[s][u][:2]) < 1.0) >= 8
            spd = math.dist(B[min(N - 1, t + 3)][:2], B[t][:2]) / 3
            z = B[t][2]
            if z >= 1.8 and held: st[k]['high_claims'] += 1; ev.append(dict(kind='high_claim', t=t, who=k))
            elif z >= 1.8 and spd >= 0.6: st[k]['punches'] += 1; ev.append(dict(kind='punch', t=t, who=k))
            off_line = gx + P[s][t][0] * side            # own goal is at x = -side*gx
            opp = min(math.hypot(P[q][t][0] - B[t][0], P[q][t][1] - B[t][1]) for q in range(22) if team(q) != team(s))
            moved = (math.dist(P[s][max(0, t - 20)][:2], B[t][:2]) - math.dist(P[s][t][:2], B[t][:2]))
            smother = z < 1.0 and opp <= 2.5 and held and moved >= 3.0
            if (off_line > 6.0 and opp <= 5.0) or smother:
                goals = [e for e, J, p in M['ev'] if J == 1]
                c = next((c for c in T[i + 1:] if c['slot'] != s), None)
                ok = c is not None and team(c['slot']) == team(s) and not any(t < e <= c['t'] for e in goals)
                st[k]['runs_out'] += 1; st[k]['runs_out_won'] += ok
                ev.append(dict(kind='run_out', won=ok, smother=smother, off_line=round(off_line, 1), t=t, who=k))
    return M, {k: dict(v) for k, v in st.items()}, ev

if __name__ == '__main__':
    M, st, ev = extras(sys.argv[1])
    for k, v in sorted(st.items()):
        x = {a: b for a, b in v.items() if a != 'touches' and b}
        print(k, v.get('touches'), x)
    for e in ev:
        if e['kind'] != 'dispossession': print(round(e['t'] / M['N'] * 90, 1), e)
