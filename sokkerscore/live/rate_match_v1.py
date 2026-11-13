"""rate_match_v1.py — v1 (11 Nov 2026): rates ONE match from what the extension can send — the bundle text and Sokker's match report
(GET /api/match/<id>/report), optionally the lineup (GET /api/match/<id>/lineup, for age / height / weight) — and returns the match
object the page and the extension read (one entry of viz/ratings_data_v52.json). First step towards the shared database.

It is run_all_v19 followed by add_season_v1, for a single match, in one process, without this folder's match lists:
  build_data_v36.job (detectors, ratings_v26, xG / xA)          unchanged
  xg_features_v1.one (shot rows)                                 unchanged
  add_lineups_v4      positions, pid, player_id                  slots and playerId from the report (v3 read lineup dumps)
  nt flag, English national-team names                           nt = both team ids below 1000 (v19: a list of 15 match ids)
  stats.pass_len      match_stats_v8, current touch rules        v19 copied it from ratings_data_v33 (the owner, 11 Nov: recompute)
  add_shots_v7, add_shot_detail_v5                               function versions of v6 / v4, same logic
  ratings_v28.apply, add_contrib_rows_v1.apply_player            unchanged
  add_pen_won_v5      bundle path passed in, no build_data_v33   same rule as v1
  add_injuries_v2     report passed in                           same rule as v1
  add_season_v1.season_of                                        unchanged (the report's competition.season is the competition's own
                                                                 edition number outside the league, so the calendar is used)
Between the steps the match goes through JSON exactly where run_all_v19 wrote a file, so types and rounding are the same.
New fields, not in v52: p['player_id'] (Sokker's playerId) and m['competition'] (name, type, round, league id from the report).
date and comp can be given; by default date = the report's date and comp = a label made from the report's competition.

Checked against the published file by live/check_published_v1.py.
usage (any folder): python -X utf8 -I live/rate_match_v1.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json

CWD0 = os.getcwd()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)                                    # every detector opens its data with paths relative to sokkerscore/
for _p in ('./viz', './run_all', './xg134', './xg158', './poss', './meta153'):
    sys.path.insert(0, _p)
import build_data_v36 as bd                       # must stay first: patches the loader, strikes, shots and touches before any detector import
import run_all_v9 as ra                           # only for EN (national-team names); its build_data_v29 is the one already loaded
import xg_features_v1 as XGF
import match_stats_v8
import add_lineups_v4, add_shots_v7, add_shot_detail_v5, ratings_v28, add_contrib_rows_v1, add_pen_won_v5, add_injuries_v2, add_season_v1

PIPELINE = 'rate_match_v1 (build_data_v36, ratings_v28, add_pen_won_v5)'
_rt = lambda o: json.loads(json.dumps(o, ensure_ascii=False))      # the JSON file run_all wrote between two steps


def is_nt(report):
    return report['home']['teamId'] < 1000 and report['away']['teamId'] < 1000      # national teams: senior = country code, U21 = code + 400


def comp_label(report):
    c = report.get('competition') or {}
    name = c.get('name') or 'Other'
    if c.get('type') == 'league':                 # only here is competition.season Sokker's season number
        return f"{name} S{c.get('season')}" + (f" R{c['round']}" if c.get('round') else '')
    if is_nt(report) and not name.startswith(('World Cup', 'U21')):
        return 'NT ' + (name[0].lower() + name[1:] if name == 'Friendly' else name)
    return name


def rate(bundle, report, bio=None, lineup=None, comp=None, date=None):
    """bundle: path of the bundle text; report / lineup: parsed JSON from Sokker; bio: {(side, surname): (age, height, weight)}."""
    mid = int(report['id'])
    date = date or report['date']['dateTime'][:10]
    comp = comp or comp_label(report)
    m = bd.job((bundle, mid, date, comp))
    if 'error' in m: raise RuntimeError(f"match {mid}: {m['error']}")
    rows = _rt(XGF.one((bundle, mid, 0)))
    m = _rt(m)
    if bio is None and lineup: bio = add_lineups_v4.bio_from_lineup(lineup)
    add_lineups_v4.apply(m, report, bio)
    m['nt'] = is_nt(report)
    if m['nt']: m['home'] = ra.EN.get(m['home'], m['home']); m['away'] = ra.EN.get(m['away'], m['away'])
    pl = {(r['team'], r['name']): (r['pass_len_sum'], r['pass_att']) for r in match_stats_v8.match_stats(bundle)[1]}
    for p in m['players']:
        s, n = pl.get((p['team'], p['name']), (0, 0))
        p['stats']['pass_len'] = round(s / n, 1) if n else None
    m = _rt(m)
    add_shots_v7.apply(m, rows); m = _rt(m)
    add_shot_detail_v5.apply(m, rows, bundle); m = _rt(m)
    ratings_v28.apply(m); m = _rt(m)
    for p in m['players']: add_contrib_rows_v1.apply_player(p)
    m = _rt(m)
    add_pen_won_v5.apply(m, bundle); m = _rt(m)
    add_injuries_v2.apply(m, report)
    m['season'], m['season_week'] = add_season_v1.season_of(m['date'])[:2]
    c = report.get('competition') or {}
    m['competition'] = dict(name=c.get('name'), type=c.get('type'), round=c.get('round'), league_id=c.get('leagueId'))
    m['pipeline'] = PIPELINE
    return _rt(m)


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = {}
    for k in ('--lineup', '--comp', '--date'):
        if k in a: i = a.index(k); opt[k] = a[i + 1]; del a[i:i + 2]
    ab = lambda p: p if os.path.isabs(p) else os.path.join(CWD0, p)
    bundle, rep, out = ab(a[0]), ab(a[1]), ab(a[2])
    report = json.load(open(rep, encoding='utf-8'))
    lineup = json.load(open(ab(opt['--lineup']), encoding='utf-8')) if '--lineup' in opt else None
    m = rate(bundle, report, lineup=lineup, comp=opt.get('--comp'), date=opt.get('--date'))
    json.dump(m, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('rated', m['id'], m['home'], m['score'], m['away'], '|', m['comp'], m['date'], 'season', m['season'], '|', len(m['players']), 'players ->', out)
