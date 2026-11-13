"""shot_analysis_v17.py — v17 (the owner, 30 Oct, 44496766 79': "no, goalie saved it"):
  (a) a dead ball needs the ball still in 3-D — a ball bouncing in place after a save is not a set piece, so Czerbniak's 79'
      goal is now a rebound from the keeper (no assist; Graffite not credited, as the owner ruled);
  (b) OUTCOME_OVERRIDES: Kupecký 79' was saved by Leañez, not woodwork (video verdict; not a new rule — a general
      "keeper near the ball before a POST event" rule broke two verified woodwork shots, e.g. 30' Czerbniak in 44496706,
      where the commentary has the bar first). Otherwise = v16.
shot_analysis_v16.py — v16: uses shots_v9 (hard close-range strikes aimed at goal but deflected at once). Otherwise = v15.
shot_analysis_v15.py — v15 (uses shots_v8: hard close-range strikes wide of goal = off target) (the owner, 20 Oct: "count a goal when Sokker counts a goal"; season-78 Ekstraklasa check):
  (a) a shot is a goal only when it is anchored to a Score-tab SCORER event; a ball crossing the line inside the frame
      without one is not a goal (outcome 'no goal (line)');
  (b) own goals: a SCORER whose team is not the team whose score went up is an own goal — no shot, no goal for anyone's
      shot list; listed in M['own_goals'] (tick, slot);
  (d) a blocked "shot" from 16 m or more is not a shot (season 78: Sokker counts ~12 % of them vs ~84 % from closer;
      the commentary/API also left out 19' Czerbniak, 21 m, in 44496706);
  (c) one shot per attempt: a shot followed within DEDUP_T ticks by another shot of the same player, with nobody else
      touching the ball in between, is dropped (the later one is the attempt).
shot_analysis_v14.py — v14: uses shots_v7 (forward-speed floor, missed keeper parries). Otherwise = v13.
shot_analysis_v13.py — v13 (the owner, 19 Oct): goal conceded by the goalkeeper -0.15 (was -0.2).
shot_analysis_v12.py — v12 (the owner, 19 Oct): override — VIP 0:2 Team Z 73' Cañate goal: assist to Jańczak
(his shot was spilled by Kiciak; Sokker's Score tab also credits Jańczak). Kiciak keeps the error. Override only, no new rule.
shot_analysis_v11.py — working restore of the project copy (sokker_124/shot_analysis_v11.py), code verbatim; full changelog there.
v11 (the owner, 19 Oct): offside -0.05 each; ratings rounded to one decimal place, halves up."""
import sys, math, json
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, './shots')
from collections import defaultdict
from strikes_v2 import load, strikes
from shots_v9 import attribute, shots, team, attack_side
DEDUP_T, BLOCK_FAR_M = 12, 16.0

HW = 4.0

def occupancy(M):
    v = M['v']; occ = {}
    for i in range(11):
        occ[i] = v.get(f'Human_namea{i}', f'A{i}'); occ[11+i] = v.get(f'Human_nameb{i}', f'B{i}')
    changes = []
    for t, J, p in M['ev']:
        if J == 3:
            s, b = p[0], p[1]
            changes.append((t, s, v.get(f"Human_name{'a' if s < 11 else 'b'}{b}", f'bench{b}')))
    start = dict(occ)
    def who(slot, t):
        name = start[slot]
        for tt, s, n in changes:
            if s == slot and tt <= t: name = n
        return name
    played = {}
    for s in range(22): played[start[s]] = [s, 0, 90]
    for tt, s, n in changes:
        played[who(s, tt - 1)][2] = M['minute'](tt); played[n] = [s, M['minute'](tt), 90]
    return who, played

def analyse(path):
    M = load(path); S = attribute(M, strikes(M)); L = shots(M, S)
    keep = []
    for k, r in enumerate(L):
        nx = L[k+1] if k + 1 < len(L) else None
        if nx and nx['slot'] == r['slot'] and nx['t'] - r['t'] <= DEDUP_T and all(S[j]['slot'] == r['slot'] for j in range(r['idx'], nx['idx'] + 1)):
            continue
        keep.append(r)
    keep = [r for r in keep if not (r['end'][0] == 'blocked' and r['dist'] >= BLOCK_FAR_M)]
    L = anchor_goals(M, S, keep)
    B, P, gx = M['ball'], M['P'], M['gx']
    who, played = occupancy(M)
    scorer_ticks = [(t, p[0]) for t, J, p in M['ev'] if J == 14]
    assist_ticks = [(t, p[0]) for t, J, p in M['ev'] if J == 15]
    shot_idx = {r['idx'] for r in L}
    rows = []
    for r in L:
        t, sl, kind = r['t'], r['slot'], r['end'][0]
        keeper = 10 if r['team'] == 'B' else 21
        goal = r.get('forced_goal', False)
        if goal: out = 'goal'
        elif kind == 'line' and r['end'][4]: out = 'no goal (line)'
        elif kind == 'keeper': out = 'on target (saved)'
        elif kind == 'blocked': out = 'blocked'
        elif kind == 'woodwork': out = 'woodwork'
        elif kind == 'wide': out = 'off target'
        else:
            cy = r['end'][2]; u = r['end'][1]
            dk = min(math.hypot(P[keeper][q][0]-B[q][0], P[keeper][q][1]-B[q][1]) for q in range(t+1, u+1))
            out = 'on target (saved)' if abs(r['aim']) <= HW and abs(cy - r['aim']) > 1.0 and dk <= 2.0 else 'off target'
        for o in OUTCOME_OVERRIDES.get((M['v'].get('TeamA_Name'), M['v'].get('TeamB_Name')), []):
            if o['shooter'] == who(sl, t) and M['minute'](t) == o['minute'] and out == o['was']: out = o['now']
        # v9: team-mate deflection -> the earlier striker's shot
        jd = r['idx'] - 1
        if not r.get('forced_goal') and jd >= 0 and team(S[jd]['slot']) == r['team'] and S[jd]['slot'] != sl \
                and t - S[jd]['t'] <= DEFLECT_TICKS and goalward(M, S, jd):
            r['idx'] = jd; t = S[jd]['t']; sl = S[jd]['slot']; r['slot'] = sl; r['t'] = t
            r['deflected_by'] = who(S[jd + 1]['slot'], S[jd + 1]['t'])
            sd = attack_side(M, r['team'], t); r['x'], r['y'] = round(S[jd]['x'], 1), round(S[jd]['y'], 1)
            r['dist'] = round(math.hypot(gx - S[jd]['x'] * sd, S[jd]['y']), 1)
        # previous touch
        j = r['idx'] - 1
        while j >= 0 and S[j]['slot'] == sl: j -= 1
        prev = S[j] if j >= 0 else None
        link, note = None, ''
        if prev is not None and dead_ball(M, t):
            prev = None; link = 'set piece (direct)'
        if prev is not None:
            q = prev['slot']; gap = t - prev['t']
            if team(q) == r['team']:
                link = 'rebound (team-mate shot)' if j in shot_idx else 'key pass'
            else:
                was_save = j in shot_idx or any(S[k]['t'] >= prev['t'] - 15 and k in shot_idx for k in range(max(0, j-3), j))
                link = 'error'; note = 'opponent touch came right after a shot (save/block/clearance?)' if was_save else ''
                if q in (10, 21) and not (r['dist'] <= GK_ERR_DIST and gap <= GK_ERR_TICKS):
                    link, note = 'keeper parry/punch (no error)', f"shot {r['dist']} m out, {gap} ticks after the keeper's touch"
            prevname = who(q, prev['t']); gap_s = gap
        else:
            prevname, gap_s = None, None
        side = attack_side(M, r['team'], t)
        in_box = (gx - r['x'] * side) <= 16.5 and abs(r['y']) <= 20.16
        rows.append(dict(minute=r['minute'], tick=t, team=r['team'], shooter=who(sl, t), slot=sl, dist_m=r['dist'],
                         header=r['z'] >= 1.0, outcome=out, in_box=in_box, prev_player=prevname,
                         prev_team=(team(prev['slot']) if prev else None), link=link, ticks_since_prev=gap_s, note=note,
                         keeper=who(keeper, t), deflected_by=r.get('deflected_by')))
    return M, rows, who, played, scorer_ticks, assist_ticks

GK_ERR_DIST, GK_ERR_TICKS = 12.0, 9

GOAL_WINDOW = 60
DEFLECT_TICKS = 6

def goalward(M, S, j):
    s = S[j]; t = s['t']; B = M['ball']; gx = M['gx']
    side = attack_side(M, team(s['slot']), t)
    if t + 3 >= M['N'] or s['x'] * side < 0: return False
    if max(math.dist(B[u][:2], B[u+1][:2]) for u in range(t, t+3)) < 0.8: return False
    vx, vy = (B[t+3][0]-B[t+1][0]) / 2, (B[t+3][1]-B[t+1][1]) / 2
    if vx * side <= 0.05: return False
    return abs(B[t+1][1] + (side*gx - B[t+1][0]) * vy / vx) <= 10.0

def dead_ball(M, t):
    B = M['ball']
    return sum(1 for u in range(max(0, t-8), t) if math.dist(B[u][:3], B[u+1][:3]) < 0.05) >= 5


def anchor_goals(M, S, L):
    B, gx = M['B'] if 'B' in M else M['ball'], M['gx']
    M['own_goals'] = []; prev = (0, 0); scorer_team = {}
    for t, J, p in M['ev']:
        if J == 1:
            sc_ = (p[0], p[1])
            if sc_ != prev: scorer_team[t] = 'A' if sc_[0] > prev[0] else 'B'
            prev = sc_
    for tg, J, p in [e for e in M['ev'] if e[1] == 14]:
        sc = p[0]
        if tg in scorer_team and team(sc) != scorer_team[tg]:
            M['own_goals'].append((tg, sc)); continue
        near = [r for r in L if tg - GOAL_WINDOW <= r['t'] <= tg + 3]
        mine = [r for r in near if r['slot'] == sc]
        if mine:
            mine[-1]['forced_goal'] = True; continue
        cand = [i for i, s in enumerate(S) if s['slot'] == sc and tg - GOAL_WINDOW <= s['t'] <= tg + 3]
        if not cand:
            cand = [i for i, s in enumerate(S) if sc in s.get('cands', []) and tg - GOAL_WINDOW <= s['t'] <= tg + 3]
            if cand: S[cand[-1]]['slot'] = sc
        if not cand:
            continue
        i = cand[-1]; s = S[i]; t = s['t']
        for r in near:                      # someone else's 'goal' flight in the same move
            if r['t'] >= t - 3: L.remove(r)
        side = attack_side(M, team(sc), t)
        L.append(dict(t=t, minute=M['minute'](t), slot=sc, team=team(sc), x=round(s['x'], 1), y=round(s['y'], 1),
                      z=round(s['z'], 1), dist=round(math.hypot(gx - s['x'] * side, s['y']), 1), aim=0.0,
                      end=('goal', tg), idx=i, forced_goal=True))
    return sorted(L, key=lambda r: r['t'])

OUTCOME_OVERRIDES = {
    ('Zabujcze Strzały', '503 Service Unavailable'): [
        dict(shooter='Kupecký', minute=79, was='woodwork', now='on target (saved)', why="the owner 30 Oct: the goalie saved it"),
    ],
}

OVERRIDES = {
    ('VIP Team Zielona Góra', 'Zabujcze Strzały'): [
        dict(player='Jańczak', stat='assist', n=1, why="73' 0:2 Cañate — Jańczak's shot spilled by Kiciak; Score-tab assist (the owner, 19 Oct)"),
    ],
    ('Zabujcze Strzały', 'fc_tex'): [
        dict(player='Pihkala', stat='err_goal', n=1, why="47:37 5:0 — left the ball for Kupecký (video, 18 Oct)"),
    ],
}

W = dict(goal=1.0, shot=0.1, sot=0.2, off=-0.2, blocked=-0.2, woodwork=0.1, key_pass=0.2, assist=0.4, err_shot=-0.2, err_goal=-1.0,
         err_goal_gk=-1.0, yellow=-0.3, foul=-0.1, offside=-0.05, save_in=0.2, save_out=0.15, conceded=-0.15)

def ratings(M, rows, who, played):
    st = defaultdict(lambda: defaultdict(float)); notes = defaultdict(list)
    for t, J, p in M['ev']:
        if J in (7, 12): st[who(p[0], t)]['yellow' if J == 7 else 'foul'] += 1
        if J == 11: st[who(p[0], t)]['offside'] += 1
    for r in rows:
        n, gk = r['shooter'], r['slot'] in (10, 21)
        if r['outcome'] == 'goal': st[n]['goal'] += 1
        elif not gk:
            st[n]['shot'] += 1
            if r['outcome'].startswith('on target'): st[n]['sot'] += 1
            elif r['outcome'].startswith('off'): st[n]['off'] += 1
            elif r['outcome'] == 'blocked': st[n]['blocked'] += 1
            elif r['outcome'] == 'woodwork': st[n]['woodwork'] += 1
        if r['link'] == 'key pass':
            st[r['prev_player']]['key_pass'] += 1
            if r['outcome'] == 'goal': st[r['prev_player']]['assist'] += 1
        if r['link'] == 'error':
            pk = r['prev_player']; is_gk = played[pk][0] in (10, 21)
            st[pk]['err_goal_gk' if (r['outcome'] == 'goal' and is_gk) else 'err_goal' if r['outcome'] == 'goal' else 'err_shot'] += 1
        if r['outcome'].startswith('on target'): st[r['keeper']]['save_in' if r['in_box'] else 'save_out'] += 1
        if r['outcome'] == 'goal': st[r['keeper']]['conceded'] += 1
    for o in OVERRIDES.get((M['v'].get('TeamA_Name'), M['v'].get('TeamB_Name')), []):
        st[o['player']][o['stat']] += o['n']
    out = []
    for n, (slot, on, off) in played.items():
        if on >= off: continue
        s = st[n]; raw = round(6.5 + sum(W[k] * c for k, c in s.items()), 4)
        out.append(dict(name=n, team=team(slot), gk=slot in (10, 21), minutes=f'{on}-{off}', rating=float(Decimal(str(round(max(3, min(10, raw)), 6))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)),
                        raw=round(raw, 2), **{k: int(c) for k, c in s.items()}))
    return sorted(out, key=lambda d: (d['team'], -d['rating']))

if __name__ == '__main__':
    M, rows, who, played, sc, asg = analyse(sys.argv[1])
    for r in rows: print(r)
    print()
    for r in ratings(M, rows, who, played): print(r)
