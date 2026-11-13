"""add_lineups_v4.py — v4 (11 Nov 2026): the position / player-key step as functions for ONE match, fed by Sokker's match report
(GET /api/match/<id>/report) instead of the hand-made lineup dumps. Written for live/rate_match_v1.
The report gives every player's slot (formation.name: GK / DEF / MID / ATT), which add_lineups_v3 took from the dumps, and Sokker's
stable playerId. On the 63 published matches the report's slot equals the dump's for 1,632 of the 1,633 joined rows.
Changes from v3:
  - join: side + surname as before, but when two players of one side share a surname (44495886: two "Hana Mansoor", a defender who
    played 90 minutes and a goalkeeper who stayed on the bench) the one whose minutes on the pitch fit is taken. v3's dump kept one
    entry per surname (it happened to be the defender's slot); the extension's SS.joinReport takes the last one listed.
  - p['player_id'] = Sokker's playerId (None when the report has no player with that surname on that side).
  - age / height / weight come from an optional bio table {(side, surname): (age, height, weight)}: Sokker's lineup endpoint in
    production (bio_from_lineup), the 5 Nov dumps when checking against the published file (bio_from_dumps). p['pid'] keeps v3's
    format (surname|age|height|weight, or surname|team name without a bio entry), so the page's profiles still join.
Position rules are v3's, unchanged: GK / DEF / ATT from the slot; MID -> W when |average y| >= 16 m, else CM; DEF -> FB when he is the
widest defender on his side among team-mates on the pitch at the same time and |y| >= 12 m, else CB; ATT -> CF. A player without a
report entry gets his class from his average position, as in v3."""
import json

WING_Y = 16.0
FB_Y = 12.0


def report_players(report):
    out = {}
    for side, key in (('A', 'home'), ('B', 'away')):
        for q in ((report or {}).get(key) or {}).get('players') or []:
            out.setdefault((side, q['surname']), []).append(q)
    return out


def pick(p, cands):
    """The report player for rating row p among those sharing his side and surname."""
    if not cands: return None
    if len(cands) == 1: return cands[0]
    played = [q for q in cands if (q.get('minuteOut') or 0) > (q.get('minuteIn') or 0)]
    return min(played or cands, key=lambda q: abs((q.get('minuteIn') or 0) - p['on']) + abs((q.get('minuteOut') or 0) - p['off']))


def bio_from_lineup(lineup):
    """Sokker's GET /api/match/<id>/lineup -> {(side, surname): (age, height, weight)}; a starter wins over a namesake on the bench."""
    out = {}
    for side, key in (('A', 'homePlayers'), ('B', 'awayPlayers')):
        for q in sorted((lineup or {}).get(key) or [], key=lambda q: not q.get('bench')):   # bench first, starters overwrite
            c = (q.get('info') or {}).get('characteristics') or {}
            n = (q.get('name') or {}).get('surname') or ''
            if n and c.get('age'): out[(side, n)] = (c['age'], c['height'], round(c['weight'], 1))
    return out


def bio_from_dumps(mid, paths):
    """The lineup dumps add_lineups_v3 read (both formats) -> the bio table of one match; used to check against the published file."""
    out = {}
    for path in paths:
        lu = json.load(open(path, encoding='utf-8'))
        if 'form' in lu:
            for k, (pid, slot, bench) in (lu['form'].get(str(mid)) or {}).items():
                side, n = k.split('|', 1); _, age, h, w = lu['people'][str(pid)]
                out[(side, n)] = (age, h, w)
        else:
            for side, pid, n, slot, bench, age, h, w, club in lu.get(str(mid)) or []:
                out[(side, n)] = (age, h, w)
    return out


def apply(m, report, bio=None):
    R = report_players(report); bio = bio or {}; miss = 0
    for p in m['players']:
        q = pick(p, R.get((p['team'], p['name'])))
        slot = ((q.get('formation') or {}).get('name') or '') if q else ''
        if p['gk'] or slot == 'GK': pos = 'GK'
        elif slot in ('DEF', 'ATT'): pos = slot
        elif slot == 'MID' or (not slot and -8 <= p['x'] < 10): pos = 'W' if abs(p['y']) >= WING_Y else 'CM'
        else: pos = 'DEF' if p['x'] < -8 else 'ATT'
        p['pos'] = pos
        e = bio.get((p['team'], p['name']))
        if e:
            p['pid'] = f"{p['name']}|{e[0]}|{e[1]}|{e[2]}"; p['age'], p['height'], p['weight'] = (e[0] or None), (e[1] or None), (e[2] or None)
        else:
            p['pid'] = f"{p['name']}|{m['home'] if p['team'] == 'A' else m['away']}"
        p['player_id'] = q['playerId'] if q else None
        if not q: miss += 1
    for T in 'AB':
        D = [p for p in m['players'] if p['team'] == T and p['pos'] == 'DEF']
        for p in D:
            side = 1 if p['y'] >= 0 else -1
            wider = [q for q in D if q is not p and (q['y'] >= 0) == (side > 0) and abs(q['y']) > abs(p['y'])
                     and q['on'] < p['off'] and p['on'] < q['off']]
            p['pos'] = 'FB' if abs(p['y']) >= FB_Y and not wider else 'CB'
    for p in m['players']:
        if p['pos'] == 'ATT': p['pos'] = 'CF'
    return miss
