"""match_stats_v8.py — v8 (7 Nov 2026, the owner, decision 8): a LONG BALL must also go FORWARD by >= LONG_FWD_M = 10 m (end point at least
10 m closer to the opponent's goal than the passer's touch, along the team's attack direction at that tick) and must not be a GOAL KICK:
the first touch after the ball went out behind the kicker's own goal line (checked between the previous touch and this one) is a goal
kick and is excluded like a kick-off. A position rule (touch inside the goal area) was tried first and rejected on the annotated match
44496766: it dropped Leañez's open-play throws from his hands at 5' and 10' and kept the real goal kick at 11', taken 5.6 m from the line.
Sideways and backward 30 m+ passes (mostly balls back to the keeper) no longer count as long balls. They remain ordinary passes;
pass counts, accuracy, pass_len and every other stat are unchanged from v7.
match_stats_v7.py — v7 (6 Nov 2026): pass_len_sum per player = summed length of every attempted pass (to the next touch, or to
where the ball left the pitch); average pass length = pass_len_sum / pass_att. Everything else unchanged from v6.
match_stats_v6.py — v6 (6 Nov 2026): KICK-OFFS are not long balls. In Sokker the kick-off is usually played ~40 m back to the
keeper (Kajoza 0:51: Przybyłowski got 52 "long balls", all kick-offs to Mangini). A pass whose first touch is within
KICKOFF_M = 1.5 m of the centre spot is excluded from long_att / long_acc (still a normal pass).
match_stats_v5.py — v5 (6 Nov 2026, the owner): also counts LONG BALLS per player: a pass (as defined below) whose length is
>= LONG_M = 30 m, measured from the passer's touch to the next touch (or to where the ball left the pitch). long_att = all
such passes, long_acc = those reaching a team-mate. Pass counts and every other stat are unchanged from v4.
match_stats_v4.py — v4 (31 Oct, the owner's annotation of 44496766, sokker_145): a pass between team-mates needs >= 1 m of ball
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
LONG_M = 30.0
KICKOFF_M = 1.5
LONG_FWD_M = 10.0

def long_ball(M, a, end, t_prev):
    """True if the pass from touch a (dict with x, y, t, slot) to end=(x, y) counts as a long ball under v8.
    t_prev = tick of the previous touch (any player); a goal kick is recognised by the ball having crossed the kicker's own goal
    line between that touch and this one (the restart after the ball went out behind his goal)."""
    if math.dist(end, (a['x'], a['y'])) < LONG_M or math.hypot(a['x'], a['y']) <= KICKOFF_M: return False
    side = attack_side(M, team(a['slot']), a['t']); gx = M['gx']; B = M['ball']
    if (end[0] - a['x']) * side < LONG_FWD_M: return False                                  # not forward enough
    if any(B[u][0] * side < -gx - 0.3 for u in range(t_prev + 1, a['t'] + 1)): return False  # goal kick (ball was out behind own goal)
    return True

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
                st[pa]['pass_len_sum'] += math.dist(B[out_u][:2], (a['x'], a['y']))
                if long_ball(M, a, B[out_u][:2], T[i-1]['t'] if i else 0): st[pa]['long_att'] += 1
            continue
        if not same:
            st[pa]['poss_lost'] += 1; st[pb]['ball_won'] += 1
        if is_shot: continue
        if same and travelled < PASS_SAME_M: continue          # tiny contact between team-mates: not a pass
        st[pa]['pass_att'] += 1
        st[pa]['pass_acc' if same else 'pass_to_opp'] += 1
        st[pa]['pass_len_sum'] += math.hypot(b['x'] - a['x'], b['y'] - a['y'])
        if long_ball(M, a, (b['x'], b['y']), T[i-1]['t'] if i else 0):
            st[pa]['long_att'] += 1
            if same: st[pa]['long_acc'] += 1
    rat = {r['name']: r for r in shot_ratings(M0, shot_rows, who, played)}
    rows = []
    for name, (slot, on, off) in played.items():
        if on >= off: continue
        s = st[name]; r = rat.get(name, {})
        rows.append(dict(name=name, team=team(slot), gk=slot in (10, 21), minutes=f'{on}-{off}',
                         passes=f"{s['pass_acc']}/{s['pass_att']}" + (f" ({round(100*s['pass_acc']/s['pass_att'])}%)" if s['pass_att'] else ''),
                         pass_acc=s['pass_acc'], pass_att=s['pass_att'], pass_to_opp=s['pass_to_opp'], pass_out=s['pass_out'],
                         pass_len_sum=round(s['pass_len_sum'], 1), long_att=s['long_att'], long_acc=s['long_acc'], clearance_out=s['clearance_out'], bad_touch=s['bad_touch'], dispossessed=s['dispossessed'], poss_lost=s['poss_lost'], ball_won=s['ball_won'], touches=s['touches'],
                         rating_shots_only=r.get('rating'), **{k: r[k] for k in r if k not in ('name', 'team', 'gk', 'minutes', 'rating', 'raw')}))
    return M, sorted(rows, key=lambda d: (d['team'], -d['pass_att']))
