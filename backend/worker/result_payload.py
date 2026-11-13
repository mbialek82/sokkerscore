"""result_payload.py — turns a rated match object (sokkerscore/live/rate_match_v2) into the two JSON arguments of the database
function ss_store_result (backend/sql/001_schema.sql):
  meta    = {date, season, season_week, comp, competition, home, away, home_id, away_id, score, nt, walkover}
  players = [{idx, player_id, team, name, first_name, pos, minutes, rating, starter, top_speed, sums}, ...]
`sums` are the per-match numbers the comparison groups add up: every numeric stat except top_speed, pass_len and sent_off, plus
plw (pass length x passes) and pl (passes), so that an average pass length can be made from the totals. These are the sums
extension/tools/package_data.py makes for data/pools.json and extension/src/profile.js makes in the browser.
A walkover (a side scored 8+, an inactive opponent) is stored but never added to the comparison groups (the function skips it)."""

SKIP = {'top_speed', 'pass_len', 'sent_off'}


def sums(stats):
    out = {k: v for k, v in stats.items() if k not in SKIP and isinstance(v, (int, float)) and not isinstance(v, bool) and v}
    if stats.get('pass_len') is not None and stats.get('pass_att'):
        out['plw'] = round(stats['pass_len'] * stats['pass_att'], 3); out['pl'] = stats['pass_att']
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}


def payload(m, report=None):
    first = {}
    for key in ('home', 'away'):
        for q in ((report or {}).get(key) or {}).get('players') or []:
            first[q['playerId']] = q.get('name') or ''
    meta = dict(date=m['date'], season=m.get('season'), season_week=m.get('season_week'), comp=m.get('comp'), competition=m.get('competition'),
                home=m['home'], away=m['away'], home_id=((report or {}).get('home') or {}).get('teamId'), away_id=((report or {}).get('away') or {}).get('teamId'),
                score=m['score'], nt=bool(m.get('nt')), walkover=max(m['score']) >= 8)
    players = [dict(idx=i, player_id=p.get('player_id'), team=p['team'], name=p['name'], first_name=first.get(p.get('player_id'), ''),
                    pos='GK' if p['gk'] else p.get('pos'), minutes=p['off'] - p['on'], rating=p['rating'], starter=bool(p.get('starter')),
                    top_speed=p['stats'].get('top_speed') or 0, sums=sums(p['stats']))
               for i, p in enumerate(m['players'])]
    return meta, players
