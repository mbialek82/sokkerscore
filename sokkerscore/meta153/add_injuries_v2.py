"""add_injuries_v2.py — v2 (11 Nov 2026): add_injuries_v1 as a function for ONE match with the report passed in (live/rate_match_v1),
instead of reading cmp100/data/reports/<id>.json. Logic unchanged: p['injury'] = {minute, severe} from the report's `injury` /
`injury_severe` events, joined by side (home = A) and surname. Stats and ratings are not touched."""


def apply(m, report):
    n = miss = 0
    r = report or {}
    name = {q['playerId']: (side, q['surname']) for side, k in (('A', 'home'), ('B', 'away')) for q in (r.get(k) or {}).get('players') or []}
    for e in r.get('events') or []:
        if not str(e.get('type', '')).startswith('injury'): continue
        key = name.get(e['playerId'])
        p = next((p for p in m['players'] if key and (p['team'], p['name']) == key), None)
        if p is None: miss += 1; print('WARNING no player', m['id'], e); continue
        p['injury'] = dict(minute=e['minute'], severe=e['type'] == 'injury_severe'); n += 1
    return n, miss
