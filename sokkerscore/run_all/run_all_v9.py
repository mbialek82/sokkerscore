"""run_all_v9.py — v9 (7 Nov 2026): build_data_v29 (ratings_v26: new stats in the rating) -> add_lineups_v3 -> pass_len from v33 -> add_shots_v6 (shots + lost 1-on-1s) -> add_shot_detail_v3 -> viz/ratings_data_v39.json.
run_all_v8.py — v8 (7 Nov 2026): build_data_v28 (ratings_v25, long-ball rule v8) -> viz/ratings_data_v39.json.
run_all_v7.py — v7 (7 Nov 2026): build_data_v27 (ratings_v24, xG bins of 40) -> viz/ratings_data_v35.json; pass_len still copied from v33.
run_all_v6.py — v6 (7 Nov 2026): rebuilds the 63 published matches with build_data_v26 (ratings_v23: xG / xA retrained on all
levels) for the before/after check against viz/ratings_data_v33.json. Output: viz/ratings_data_v39.json.
Post-processing as v5 except: stats.pass_len is copied from v33 (it does not depend on xG, and add_pass_len_v1 imports the retired
run_all_v2 / build_data_v23), and the per-shot list uses add_shots_v4 with shots_train_v3. RUN FROM THE PACKAGE ROOT with -X utf8.
run_all_v5.py — handoff copy: reads the match list from viz/matches_v1.json, adds the per-shot xG list (add_shots_v2) at the end."""
import sys, os, json, subprocess, time
sys.path.insert(0, './viz')
from multiprocessing import Pool
import build_data_v29 as bd
EN = {'België': 'Belgium', 'Deutschland': 'Germany', 'Hayastan U21': 'Armenia U21', 'Nederland': 'Netherlands', 'Nippon': 'Japan', 'Polska': 'Poland',
      'Polska U21': 'Poland U21', 'România': 'Romania', 'Rossiya': 'Russia', 'Slovenija': 'Slovenia', 'Slovensko': 'Slovakia', 'Türkiye': 'Turkey', 'U.A.E. U21': 'UAE U21'}
NT = {44742695, 44742698, 44495876, 44495886, 44742728, 44742725, 44742723, 44750197, 44742796, 44139675, 44139681, 44139689, 44139693, 44139702, 44139688}
SPECIAL = {43761572: './uploads/match_43761572.json', 44471278: './uploads/Downloads/match_44471278_fctex_bundle.txt',
           44496706: './m44496706/match_44496706.txt', 44496766: './m44496766/match_44496766.txt'}
def path(i):
    if i in SPECIAL: return SPECIAL[i]
    for d in ('s78', 's79', 'nt'):
        p = f'./{d}/bundles/match_{i}.txt'
        if os.path.exists(p): return p
    raise FileNotFoundError(i)
if __name__ == '__main__':
    PY = [sys.executable, '-X', 'utf8', '-I']
    prev = json.load(open('./viz/matches_v1.json', encoding='utf-8'))
    jobs = [(path(m['id']), m['id'], m['date'], m['comp']) for m in prev]
    t0 = time.time()
    with Pool(2) as p: out = p.map(bd.job, jobs, chunksize=1)
    print('rated', len(out), 'in', round(time.time() - t0), 's')
    bad = [m for m in out if 'error' in m]
    for m in bad: print('ERROR', m['id'], m['error'])
    out = sorted([m for m in out if 'error' not in m], key=lambda m: (m['date'], m['id']), reverse=True)
    json.dump(out, open('./viz/ratings_data_v39_in.json', 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run(PY + ['./meta153/add_lineups_v3.py', './viz/ratings_data_v39_in.json', './viz/ratings_data_v39_pos.json',
                         './uploads/Downloads/sokker_lineups_46.json', './nt/lineups_4.json', './nt/lineups_12.json', './nt/lineups_today.json'], check=True)
    d = json.load(open('./viz/ratings_data_v39_pos.json', encoding='utf-8'))
    old = {(m['id'], p['team'], p['name']): p['stats'].get('pass_len') for m in json.load(open('./viz/ratings_data_v33.json', encoding='utf-8')) for p in m['players']}
    for m in d:
        m['nt'] = m['id'] in NT
        if m['nt']: m['home'] = EN.get(m['home'], m['home']); m['away'] = EN.get(m['away'], m['away'])
        for p in m['players']: p['stats']['pass_len'] = old.get((m['id'], p['team'], p['name']))
    json.dump(d, open('./viz/ratings_data_v39_p.json', 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run(PY + ['./xg158/add_shots_v6.py', './viz/ratings_data_v39_p.json', './viz/ratings_data_v39_s.json', './xg158/shots_train_v3.json',
                         './xg134/shots_s78_v1.json', './xg158/shots_new_v1.json'], check=True)
    subprocess.run(PY + ['./xg158/add_shot_detail_v3.py', './viz/ratings_data_v39_s.json', './viz/ratings_data_v39.json'], check=True)
    print('all done', len(d), 'matches -> viz/ratings_data_v39.json')
