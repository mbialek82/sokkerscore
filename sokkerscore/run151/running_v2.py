"""running_v2.py — sokker_151, v2 (4 Nov 2026, the owner):
  carry_dist   now the PATH length of each carry — the sum of the ball's straight-line travel between consecutive touches of
               the same spell (v1 took first-touch -> last-touch straight-line, which undercounts winding dribbles; Rădoi in
               44496766: 169.5 -> 185.5 m);
  top_speed    now the raw peak single-tick step in metres per tick (v1 scaled it by the Score-tab clock to "m per game-second",
               which is meaningless: the viewer plays ticks faster than the clock and not at a constant rate).
  Units: everything is REAL METRES — the bundle's coordinates are decimetres/10 on a pitch of `pitchheight` x `pitchwidth` m
  (102 x 72 in 44496766; penalty spot at exactly 11.0 m). The totals look small next to real football (3.5-4.9 km, not 10-12)
  because Sokker's 90-minute clock holds only ~16,400 ticks and nobody moves more than ~0.55 m per tick: a Sokker match simply
  contains about a third of a real match's movement. Compare players with each other.
running_v1.py — sokker_151. Running/carrying stats per player for one match (both teams), for the match-ratings page:
  dist          — distance covered, m, all on-pitch ticks, steps >= 3.0 m excluded as decoder noise/teleports
                  (same filter as sokker_148's player_season_v1).
  carry_dist    — per the owner's choice, ONE carry runs from the touch that wins the ball to the touch that ends his spell on it
                  (pass/shot/lost), merging every consecutive touch by the same player in the touches_v3 stream. A single
                  isolated touch (no second touch before it moves on) is not a carry.
  prog_carries  — count of those carries that are "progressive" by the zone-scaled FBref/StatsBomb rule, in round metres:
                  forward progress (first touch -> last touch, on the attack-normalised x-axis) >= 10 m if the carry STARTS in
                  the player's own half, >= 5 m if it starts in the opponent's half, OR the carry ends inside the penalty box
                  (last 16.5 m x 40.3 m) regardless of distance. Carries that lose ground don't count.
Both stats computed for all 22 slots (both teams), matching build_data's match-ratings scope."""
import sys, math
for p in ('./poss', './shots', './def', './int130', './du132', './out127'):
    sys.path.insert(0, p)
import shot_analysis_v17 as _sa
from touches_v3 import touches, load
from shots_v9 import team, attack_side

NOISE_M = 3.0          # same decoder-noise filter as player_season_v1
BOX_X, BOX_Y = 16.5, 20.16

def ticks_per_minute(M):
    mins = [(t, p[0] + 69 * p[1]) for t, J, p in M['ev'] if J == 2]
    if len(mins) < 2: return None
    t0, m0 = mins[0]; t1, m1 = mins[-1]
    return (t1 - t0) / (m1 - m0) if m1 != m0 else None

def running(path):
    M0, rows, who, played, *_ = _sa.analyse(path)
    M = load(path); P = M['P']; N = M['N']; gx = M['gx']; gy = float(M['v'].get('pitchwidth', 64)) / 2
    tpm = ticks_per_minute(M); tps = tpm / 60 if tpm else None
    acc = {}
    def A(n): return acc.setdefault(n, dict(dist=0.0, top_tick=0.0, carry_dist=0.0, prog_carries=0, n_carries=0))
    # distance + top speed: per-tick player movement, all 22 slots
    for s in range(22):
        for t in range(1, N):
            n = who(s, t)
            st = math.hypot(P[s][t][0] - P[s][t-1][0], P[s][t][1] - P[s][t-1][1])
            if st < NOISE_M:
                a = A(n); a['dist'] += st
                if st > a['top_tick']: a['top_tick'] = st
    # carries: merge consecutive same-player touches into one spell
    T = touches(M)
    i = 0
    while i < len(T):
        j = i
        s0 = T[i]['slot']; n0 = who(s0, T[i]['t'])
        while j + 1 < len(T) and T[j+1]['slot'] == s0 and who(s0, T[j+1]['t']) == n0:
            j += 1
        if j > i:          # at least 2 touches -> an actual carry
            x0, y0, t0 = T[i]['x'], T[i]['y'], T[i]['t']
            x1, y1, t1 = T[j]['x'], T[j]['y'], T[j]['t']
            side = attack_side(M, team(s0), t0)
            length = sum(math.hypot(T[k+1]['x'] - T[k]['x'], T[k+1]['y'] - T[k]['y']) for k in range(i, j))   # v2: path length
            progress = (x1 - x0) * side
            a = A(n0); a['carry_dist'] += length; a['n_carries'] += 1
            start_own = (x0 * side) < 0
            in_box = (x1 * side) >= gx - BOX_X and abs(y1) <= BOX_Y
            prog = in_box or (progress >= (10.0 if start_own else 5.0))
            if prog: a['prog_carries'] += 1
        i = j + 1
    out = {}
    for n, (s, on, off) in played.items():
        if on >= off: continue
        a = acc.get(n, dict(dist=0.0, top_tick=0.0, carry_dist=0.0, prog_carries=0, n_carries=0))
        out[n] = dict(dist=round(a['dist'], 1), top_speed=round(a['top_tick'], 2),   # v2: m per tick, unscaled
                      carry_dist=round(a['carry_dist'], 1), prog_carries=a['prog_carries'], n_carries=a['n_carries'])
    return out

if __name__ == '__main__':
    r = running(sys.argv[1])
    for n, v in sorted(r.items(), key=lambda kv: -kv[1]['dist'])[:5]: print(n, v)
