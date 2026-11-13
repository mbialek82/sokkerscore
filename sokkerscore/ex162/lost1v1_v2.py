"""lost1v1_v2.py — v2 (7 Nov 2026, port into this folder): xG from THIS folder's model (xg158/shots_train_v3.json, bins of 40 = ratings_v25), was shots_train_v2 with bins of 20. Detector unchanged.
lost1v1_v1.py — v1 (7 Nov 2026, sokker_162): chances an attacker lost to the keeper without shooting (the owner: they get xG,
export (7 Nov 2026): absolute /home/claude/... paths made relative to sokkerscore/; code otherwise exactly as it last ran.
added INTO the player's and team's xG total; the keeper gets a save).
Event: a spell on the ball (keeper wins it within 3 m of ball travel, i.e. off the attacker's feet, not a cross he claimed) of >= 2 consecutive touches by one attacker (no goal/end break) whose last touch is inside the
opponents' box, with no shot in the spell, and the next touch is the opposing keeper's within 12 ticks.
xG: the retrained category model (xg158 shots_train_v2) applied to the situation at the attacker's last touch, built
exactly like xg_features_v1 (foot, open play)."""
import sys, math, json
for p in ('./poss', './shots', './out127', './def', './int130', './du132', './xg134'):
    if p not in sys.path: sys.path.insert(0, p)
import strikes_v2, strikes_v3; strikes_v2.load = strikes_v3.load
import ratings_v22  # noqa
from shot_analysis_v17 import analyse as shot_analyse
from touches_v3 import touches
from shots_v9 import team, attack_side
from xg_features_v1 import in_tri, HALF_GOAL
import xg_model_v1 as XG
_MX = None
def model():
    global _MX
    if _MX is None: _MX = XG.CategoryXG(MIN=40).fit(json.load(open('./xg158/shots_train_v3.json', encoding='utf-8')))
    return _MX

def lost(path):
    M0, rows, who, played, *_ = shot_analyse(path)
    M = strikes_v2.load(path); T = touches(M); B, P, gx, N = M['ball'], M['P'], M['gx'], M['N']
    shot_ticks = [r['tick'] for r in rows]
    breaks = sorted(t for t, J, p in M['ev'] if J in (1, 6))
    out = []; i = 0
    while i < len(T):
        j = i
        while j + 1 < len(T) and T[j+1]['slot'] == T[i]['slot'] and not any(T[j]['t'] < e <= T[j+1]['t'] for e in breaks): j += 1
        s = T[i]['slot']; tm = team(s); kq = 21 if tm == 'A' else 10
        nx = T[j+1] if j + 1 < len(T) else None
        t = T[j]['t']; side = attack_side(M, tm, t)
        if (j > i and nx is not None and nx['slot'] == kq and nx['t'] - t <= 12 and s not in (10, 21)
                and not any(t < e <= nx['t'] for e in breaks)
                and not any(T[i]['t'] - 2 <= st <= t + 2 for st in shot_ticks)):
            bx, by, bz = B[t][0] * side, B[t][1] * side, B[t][2]
            travel = max(math.dist(B[u][:2], B[t][:2]) for u in range(t, nx['t'] + 1))
            if gx - bx <= 16.5 and abs(by) <= 20.16 and travel < 3.0:   # v1 fix before first use: keeper took it off his feet (not a cross/pass he claimed)
                gpos = lambda q: (P[q][t][0] * side, P[q][t][1] * side)
                p1, p2 = (gx, -HALF_GOAL), (gx, HALF_GOAL)
                ang = abs(math.degrees(math.atan2(p2[1] - by, p2[0] - bx) - math.atan2(p1[1] - by, p1[0] - bx)))
                opp = [q for q in range(22) if team(q) != tm]
                kx, ky = gpos(kq); dx, dy = gx - bx, -by; L = math.hypot(dx, dy) or 1
                x = dict(dist=round(math.hypot(gx - bx, by), 2), angle=round(ang, 2), z=round(bz, 2), header=0,
                         cone_def=sum(in_tri(gpos(q), (bx, by), p1, p2) for q in opp if q != kq),
                         gk_in_cone=int(in_tri((kx, ky), (bx, by), p1, p2)), gk_line=round(gx - kx, 2),
                         gk_off=round(abs((kx - bx) * dy - (ky - by) * dx) / L, 2),
                         press=round(min(math.hypot(gpos(q)[0] - bx, gpos(q)[1] - by) for q in opp if q != kq), 2),
                         mates_ahead=sum(1 for q in range(22) if team(q) == tm and q != s and gpos(q)[0] > bx and gx - gpos(q)[0] <= 16.5 and abs(gpos(q)[1]) <= 20.16),
                         kind='open')
                out.append(dict(t=t, team=tm, sh=who(s, t), gk=who(kq, t), xg=round(float(model().predict1(x)), 3),
                                dist=round(x['dist'], 1), gl=round(gx - bx, 1), y=round(-by, 1), feat=x))
        i = j + 1
    return M, out

if __name__ == '__main__':
    M, o = lost(sys.argv[1])
    for e in o: print(round(e['t'] / M['N'] * 90, 1), e['team'], e['sh'], '->', e['gk'], e['xg'], e['dist'])
