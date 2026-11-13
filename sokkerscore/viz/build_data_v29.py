"""build_data_v29.py — v29 (7 Nov 2026, decisions 19–20): ratings_v26 — the new stats (touches, crosses, Opta clearances, dispossessions, keeper claims / punches / run-outs, chances lost to the keeper) are in the rating and in stats; their contribution rows come from ratings_v26.new_contrib; stats.clearances = new definition, clearances_out = the old one; def_contrib = tackles won + interceptions + clearances + blocks; bcm / big_chances / saves / saves_in include the lost 1-on-1s; m.lost_gk lists them (xG capped at 0.30) for add_shots_v6 to put into m.shots and the xG totals.
build_data_v28.py — v28 (7 Nov 2026): ratings_v25 — long balls forward-only (>= 10 m) and no goal kicks (match_stats_v8). Everything else as v27.
build_data_v27.py — v27 (7 Nov 2026): ratings_v24 — xG and xA bins of 40 (page xG / xA from the same models); everything else as v26.
build_data_v26.py — v26 (7 Nov 2026): ratings_v23 — xG / xA models retrained on all levels (shots_train_v3 / keypasses_train_v3); page xG / xA from the same models. Nothing else changed.
build_data_v25.py — v25: ratings_v22 (detector aliases fixed).
build_data_v24.py — v24: ratings_v21; page xG / xA from the same retrained models (sokker_158 shots_train_v2 / keypasses_train_v2).
build_data_v23.py — v23: ratings_v20 (kick-offs not long balls).
build_data_v22.py — v22: ratings_v19 (completed long ball +0.03); stats long_acc / long_att; contribution row "Long balls completed".
build_data_v21.py — v21: strikes_v3 patched in as THE loader (strikes_v2.load = strikes_v3.load, before any detector is imported), so penalty shootouts are cut off everywhere; players on at the end of an extra-time match play to 120'; m.shootout = shootout score.
build_data_v20.py — v20: 20 more season-79 matches (Ekstraklasa R1-R7, Puchar Polski, International Cup II) from s79/bundles; real dates for 44471278 (2 Oct) and 44496766 (28 Oct); sort by date.
build_data_v19.py — v19: a sent-off player's minutes end at the dismissal (off = minute of the red / 2nd yellow, was 90); stats.sent_off = that minute.
build_data_v18.py — v18: running_v2 (carry = path length; top speed = raw m per tick; all distances real metres).
build_data_v17.py — v17: adds stats.red2y (reds that came from a 2nd yellow, ratings_v18) so the page can show the yellow peeking out behind the red only for that case.
build_data_v16.py — v16: ratings_v17 (red card -(90-minute)x0.05, penalty miss -0.5) with "Red card" / "Penalty missed" rows in the contribution list.
build_data_v15.py — v15: all 26 Team Z matches (22 season-78 Ekstraklasa + the 4 earlier), run in parallel; per player also
red cards (Score-tab RED + YELLOW_SECOND) and penalty misses (penalties_v1: penalty taker whose kick was not a goal — saved, post or off);
match meta (round / date / competition) for the profile pages. xG/xA for season-78 matches are in-sample (models were fitted on that season), display only.
build_data_v14.py — v14: running stats (sokker_151/running_v1.py) merged in per player — dist (distance
covered), top_speed (peak m/game-second equiv.), carry_dist (total carrying distance), prog_carries (progressive
carries) — zone-scaled FBref-style rule, metres not yards; see running_v1.py docstring for exact definitions
and caveats (Sokker's compressed movement scale throughout — compare players only, never to real distances).
build_data_v13.py — v13: ratings_v16 (detector fixes from the 44496766 annotation).
build_data_v12.py — v12: ratings_v15 (shot_analysis_v17).
build_data_v11.py — v11: ratings_v14 (BCM -0.25, BCC +0.15, xA +0.5 per unit; big chance = xG >= 0.25); xG/xA/BCM/BCC per player from the rating.
build_data_v10.py — v10: ratings_v13; fourth match 44496766; per-player xG and xA from the season-78 category models (sokker_134/135), display only.
build_data_v9.py — v9: ratings_v12 (shot fixes from the season-78 check).
build_data_v8.py — v8: ratings_v11; third match 44496706 (Team Z 2:0 tetrahydro, Ekstraklasa, 11 Oct).
build_data_v7.py — v7: ratings_v10 (duels).
build_data_v6.py — v6: ratings_v9 (blocks, was fouled).
build_data_v5.py — v5: ratings_v8 (interceptions, keeper conceded -0.15); interceptions in the stats.
build_data_v4.py — v4: ratings_v7 (pass standards 10 / 70 %).
build_data_v3.py — v3: ratings_v6 / shot_analysis_v12 (Jańczak 73' assist).
build_data_v1.py — collect per-player ratings and stats for both matches into one JSON for the ratings page.
Sources: ratings_v16 (sokker_128), match_stats_v4 (sokker_125), tackles_v6 (sokker_129), dribbles_v2 (sokker_127), running_v1 (sokker_151).
Average position: mean of the player's on-pitch ticks, x along his team's attack direction (half-time swap handled)."""
import sys, json, math
for p in ('./poss', './shots', './out127', './def', './int130', './du132', './run151', './pen152', './xg134', './xa135'):
    sys.path.insert(0, p)
import strikes_v2, strikes_v3; strikes_v2.load = strikes_v3.load   # v21: must precede every detector import
from ratings_v26 import rate
from match_stats_v4 import match_stats
from tackles_v6 import tackles
from dribbles_v2 import dribbles
from strikes_v2 import load
from shot_analysis_v17 import occupancy, W
from shots_v9 import team, attack_side
from running_v2 import running
from penalties_v1 import penalties
from multiprocessing import Pool

W_EXTRA = dict(drib_won=0.1, drib_lost=-0.05, dispossessed=-0.05, bad_touch=-0.05, tackle_won=0.05, tackle_failed=-0.1, interception=0.05, blocks=0.1, was_fouled=0.05, ground_won=0.02, ground_lost=-0.02, aerial_won=0.05, aerial_lost=-0.05)
LAB = dict(goal='Goal', assist='Assist', key_pass='Key pass', shot='Shot', sot='Shot on target', off='Shot off target',
           blocked='Shot blocked', woodwork='Hit woodwork', err_shot='Error leading to shot', err_goal='Error leading to goal',
           err_goal_gk='Error leading to goal', foul='Foul', yellow='Yellow card', offside='Offside', save_in='Save (in box)',
           save_out='Save (outside box)', conceded='Goal conceded', drib_won='Dribble completed', drib_lost='Dribble failed',
           dispossessed='Dispossessed', bad_touch='Unsuccessful touch', tackle_won='Tackle won', tackle_failed='Tackle failed', interception='Interception', blocks='Block', was_fouled='Was fouled', ground_won='Ground duel won', ground_lost='Ground duel lost', aerial_won='Aerial duel won', aerial_lost='Aerial duel lost')

def build(path, mid, date, comp):
    M = load(path); who, played = occupancy(M); P = M['P']; N = M['N']
    R = rate(path); _, ms, = match_stats(path)[0], match_stats(path)[1]
    ms = {r['name']: r for r in ms}
    tk = {r['name']: r for r in tackles(path)[1]}
    dr = {r['name']: r for r in dribbles(path)[1]}
    rn = running(path)
    pens = penalties(path, M)
    pen_miss = {}; pen_taken = {}
    for e in pens:
        pen_taken[e['taker']] = pen_taken.get(e['taker'], 0) + 1
        if e['outcome'] != 'goal': pen_miss[e['taker']] = pen_miss.get(e['taker'], 0) + 1
    acc = {}
    for t in range(0, N, 3):
        for s in range(22):
            n = who(s, t); side = attack_side(M, team(s), t)
            a = acc.setdefault(n, [0.0, 0.0, 0]); a[0] += P[s][t][0] * side; a[1] += P[s][t][1] * (side if team(s) == 'A' else side); a[2] += 1
    goals = [p for t, J, p in M['ev'] if J == 1]
    sa, sb = (goals[-1][0], goals[-1][1]) if goals else (0, 0)
    players = []
    for r in R:
        n = r['name']; m = ms.get(n, {}); t = tk.get(n, {}); d = dr.get(n, {}); rr = rn.get(n, {})
        on, off = (int(x) for x in r['minutes'].split('-'))
        if M.get('extra_time') and off == 90: off = max(p_[0] + 69 * p_[1] for t_, J_, p_ in M['ev'] if J_ == 2)
        sent_off = min(r['red_minutes']) if r.get('red_minutes') else None
        if sent_off is not None: off = min(off, max(on, sent_off))
        contrib = [dict(label=LAB[k], n=int(r[k]), pts=round((W.get(k) if k in W else W_EXTRA[k]) * r[k], 3))
                   for k in list(W) + list(W_EXTRA) if r.get(k)]
        contrib += [dict(label='Pass volume', n=None, pts=r['pass_vol']), dict(label='Pass accuracy', n=None, pts=r['pass_accb'])]
        if r.get('red_pen'): contrib.append(dict(label='Red card (min ' + ', '.join(str(x) for x in r['red_minutes']) + ')', n=r['reds'], pts=r['red_pen']))
        if r.get('long_pen'): contrib.append(dict(label='Long balls completed', n=r['long_acc'], pts=r['long_pen']))
        if r.get('pen_miss_pen'): contrib.append(dict(label='Penalty missed', n=r['pen_misses'], pts=r['pen_miss_pen']))
        contrib += r.get('new_contrib', [])
        contrib = [c for c in contrib if abs(c['pts']) >= 0.005]
        a = acc.get(n, [0, 0, 1])
        players.append(dict(
            name=n, team=r['team'], gk=r['gk'], on=on, off=off, starter=on == 0, rating=r['rating'], raw=round(r['raw'], 2),
            x=round(a[0] / a[2], 1), y=round(a[1] / a[2], 1),
            stats=dict(goals=r.get('goal', 0), assists=r.get('assist', 0), key_passes=r.get('key_pass', 0),
                       shots=r.get('shot', 0) + r.get('goal', 0), sot=r.get('sot', 0) + r.get('goal', 0), off=r.get('off', 0),
                       blocked=r.get('blocked', 0), woodwork=r.get('woodwork', 0),
                       pass_acc=m.get('pass_acc', 0), pass_att=m.get('pass_att', 0),
                       drib_won=d.get('drib_won', 0), drib_att=d.get('drib_won', 0) + d.get('drib_lost', 0),
                       dispossessed=m.get('dispossessed', 0), bad_touch=m.get('bad_touch', 0), poss_lost=m.get('poss_lost', 0),
                       tackles=t.get('tackles', 0), tackles_won=t.get('tackles_won', 0), interceptions=r.get('interception', 0), bcm=r.get('bcm', 0) + r.get('lost_gk_bcm', 0), bcc=r.get('bcc', 0), big_chances=r.get('big_chances', 0) + r.get('lost_gk_bcm', 0), blocks=r.get('blocks', 0), **{k: r.get(k, 0) for k in ('ground_won', 'ground_lost', 'aerial_won', 'aerial_lost')}, was_fouled=r.get('was_fouled', 0), recoveries=t.get('recoveries', 0),
                       clearances=r.get('clearances2', 0), clearances_out=m.get('clearance_out', 0), def_contrib=t.get('tackles_won', 0) + r.get('interception', 0) + r.get('clearances2', 0) + r.get('blocks', 0), balls_won=m.get('ball_won', 0), dribbled_past=d.get('dribbled_past', 0),
                       err_shot=r.get('err_shot', 0), err_goal=r.get('err_goal', 0) + r.get('err_goal_gk', 0),
                       fouls=r.get('foul', 0), yellow=r.get('yellow', 0), offsides=r.get('offside', 0),
                       saves=r.get('save_in', 0) + r.get('save_out', 0) + r.get('lost_gk_saves', 0), saves_in=r.get('save_in', 0) + r.get('lost_gk_saves', 0), conceded=r.get('conceded', 0),
                       dist=rr.get('dist'), top_speed=rr.get('top_speed'), carry_dist=rr.get('carry_dist'),
                       prog_carries=rr.get('prog_carries'), n_carries=rr.get('n_carries'),
                       long_acc=r.get('long_acc', 0), long_att=r.get('long_att', 0), red=r.get('reds', 0), red2y=r.get('red2y', 0), sent_off=sent_off, pen_taken=pen_taken.get(n, 0), pen_miss=pen_miss.get(n, 0),
                       touches=r.get('touches', 0), cross_att=r.get('cross_att', 0), cross_acc=r.get('cross_acc', 0), dispossessions=r.get('dispossessions', 0),
                       high_claims=r.get('high_claims', 0), punches=r.get('punches', 0), runs_out=r.get('runs_out', 0), runs_out_won=r.get('runs_out_won', 0),
                       lost_gk=r.get('lost_gk', 0), lost_gk_xg=r.get('lost_gk_xg', 0)),
            contrib=sorted(contrib, key=lambda c: -abs(c['pts']))))
    lost_gk = [dict(min=M['minute'](e['t']), team=e['team'], sh=e['sh'], xg=e['xg'], out='lost to keeper', kind='open', dist=e['dist'], head=0, gl=e['gl'], y=e['y'], spd=None, ey=None, ez=None, ex=0)
               for r in R for e in r.get('lost_gk_events', [])]
    return dict(id=mid, date=date, comp=comp, home=M['v'].get('TeamA_Name'), away=M['v'].get('TeamB_Name'), lost_gk=lost_gk,
                score=[sa, sb], shootout=M.get('shootout'), extra_time=M.get('extra_time'), pens=pens, gx=M['gx'], gy=float(M['v'].get('pitchwidth', 64)) / 2, players=players)


_models = {}
def _xg_models():
    if not _models:
        import xg_model_v1 as XG, xa_model_v1 as XA, xg_features_v1 as XGF, xa_features_v1 as XAF
        _models.update(XGF=XGF, XAF=XAF,
                       mx=XG.CategoryXG(MIN=40).fit(json.load(open('./xg158/shots_train_v3.json'))),
                       ma=XA.CategoryXA(MIN=40).fit(json.load(open('./xg158/keypasses_train_v3.json'))))
    return _models

def job(j):
    path, mid, date, comp = j
    try:
        m = build(path, mid, date, comp)
        K = _xg_models(); XGF, XAF, mx, ma = K['XGF'], K['XAF'], K['mx'], K['ma']
        sh = XGF.one((path, mid, 0)); kp = XAF.one((path, mid, 0))
        xg_ = {}; xa_ = {}
        for x, p in zip(sh, mx.predict(sh) if sh else []): xg_[(x['team'], x['shooter'])] = xg_.get((x['team'], x['shooter']), 0) + float(p)
        for x, p in zip(kp, ma.predict(kp) if kp else []): xa_[(x['team'], x['passer'])] = xa_.get((x['team'], x['passer']), 0) + float(p)
        for p in m['players']:
            p['stats']['xg'] = round(xg_.get((p['team'], p['name']), 0), 2); p['stats']['xa'] = round(xa_.get((p['team'], p['name']), 0), 2)
        for e in m.get('lost_gk', []): xg_[(e['team'], e['sh'])] = xg_.get((e['team'], e['sh']), 0) + e['xg']
        for p in m['players']: p['stats']['xg'] = round(xg_.get((p['team'], p['name']), 0), 2)
        m['xg'] = [round(sum(v for (t, _), v in xg_.items() if t == T), 2) for T in 'AB']
        return m
    except Exception:
        import traceback; return dict(id=mid, error=traceback.format_exc()[-800:])

if __name__ == '__main__':
    meta = json.load(open('./s78/s78_meta.json', encoding='utf-8'))
    jobs = [(f"./s78/bundles/match_{m['id']}.txt", m['id'], m['date'], f"Ekstraklasa S78 R{m['round']}") for m in meta if 'Zabujcze Strzały' in (m['home'], m['away'])]
    jobs += [('./uploads/match_43761572.json', 43761572, '2026-04-17', 'International Cup II'),
             ('./uploads/Downloads/match_44471278_fctex_bundle.txt', 44471278, '2026-10-02', 'International Cup II'),
             ('./m44496706/match_44496706.txt', 44496706, '2026-10-11', 'Ekstraklasa S79'),
             ('./m44496766/match_44496766.txt', 44496766, '2026-10-28', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496662.txt', 44496662, '2026-09-27', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496674.txt', 44496674, '2026-09-30', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496688.txt', 44496688, '2026-10-04', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496694.txt', 44496694, '2026-10-07', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496718.txt', 44496718, '2026-10-14', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496730.txt', 44496730, '2026-10-18', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496742.txt', 44496742, '2026-10-21', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496754.txt', 44496754, '2026-10-25', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44496778.txt', 44496778, '2026-11-01', 'Ekstraklasa S79'),
             ('./s79/bundles/match_44467009.txt', 44467009, '2026-09-21', 'Puchar Polski'),
             ('./s79/bundles/match_44738825.txt', 44738825, '2026-09-28', 'Puchar Polski'),
             ('./s79/bundles/match_44746083.txt', 44746083, '2026-10-05', 'Puchar Polski'),
             ('./s79/bundles/match_44751799.txt', 44751799, '2026-10-12', 'Puchar Polski'),
             ('./s79/bundles/match_44757029.txt', 44757029, '2026-10-19', 'Puchar Polski'),
             ('./s79/bundles/match_44762009.txt', 44762009, '2026-10-26', 'Puchar Polski'),
             ('./s79/bundles/match_44471276.txt', 44471276, '2026-09-25', 'International Cup II'),
             ('./s79/bundles/match_44471281.txt', 44471281, '2026-10-09', 'International Cup II'),
             ('./s79/bundles/match_44471282.txt', 44471282, '2026-10-16', 'International Cup II'),
             ('./s79/bundles/match_44471284.txt', 44471284, '2026-10-23', 'International Cup II'),
             ('./s79/bundles/match_44471287.txt', 44471287, '2026-10-30', 'International Cup II'),]
    with Pool(2) as pool: out = pool.map(job, jobs, chunksize=1)
    bad = [m for m in out if 'error' in m]
    for m in bad: print('ERROR', m['id'], m['error'])
    out = sorted([m for m in out if 'error' not in m], key=lambda m: (m['date'], m['id']), reverse=True)  # newest first; two undated matches placed by id
    json.dump(out, open('./viz/ratings_data_v28_raw.json', 'w', encoding='utf-8'), ensure_ascii=False)
    for m in out: print(m['id'], m['home'], m['score'], m['away'], len(m['players']), 'players', len(m['pens']), 'pens')
