"""add_season_v1.py — v1 (11 Nov 2026): adds m['season'] and m['season_week'] (Sokker's season number and the week 1–13 inside it) to every match,
so the player profile can split a player's numbers by season (tpl23).

Sokker's GET /api/match/<id> returns time.gameDay = {season, week, seasonWeek, day, date}. That endpoint needs a login, so for the published matches the
season is computed from the match date with Sokker's calendar instead: weeks start on Saturday, week 1183 started on 2026-03-14, a season has 13 weeks and
season 77 is weeks 1184–1196. The extension should read time.gameDay.season from the API directly.

Checks (any mismatch stops the script, nothing is written):
  - the calendar reproduces season and seasonWeek of every Sokker match file under cmp100/data/matches (103 files, seasons 77 and 79);
  - a competition label that names a season ('Ekstraklasa S78 R4', 'NT S78 Group I', 'Ekstraklasa S79') agrees with the computed season.

Usage (from sokkerscore/): python -X utf8 -I meta153/add_season_v1.py viz/ratings_data_v51.json viz/ratings_data_v52.json"""
import sys, json, glob, re, datetime as dt, collections

W0, D0 = 1183, dt.date(2026, 3, 14)          # week 1183 started on Saturday 14 March 2026
S0, SW0, LEN = 77, 1184, 13                  # season 77 = weeks 1184..1196


def season_of(date_str):
    week = W0 + (dt.date.fromisoformat(date_str[:10]) - D0).days // 7
    return S0 + (week - SW0) // LEN, (week - SW0) % LEN + 1, week


def check_calendar():
    n = 0
    for f in glob.glob('./cmp100/data/matches/*.json'):
        try:
            g = json.load(open(f, encoding='utf-8'))['time']['gameDay']
        except Exception:
            continue
        s, sw, w = season_of(g['date']['value'])
        assert (s, sw, w) == (g['season'], g['seasonWeek'], g['week']), (f, g, s, sw, w)
        n += 1
    return n


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    n = check_calendar()
    assert n >= 100, n
    d = json.load(open(src, encoding='utf-8'))
    cnt = collections.Counter()
    for m in d:
        s, sw, _ = season_of(m['date'])
        lab = re.search(r'\bS(\d\d)\b', m.get('comp') or '')
        assert not lab or int(lab.group(1)) == s, (m['id'], m['date'], m['comp'], s)
        m['season'], m['season_week'] = s, sw
        cnt[s] += 1
    json.dump(d, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('calendar checked on', n, 'Sokker match files; matches per season:', dict(sorted(cnt.items())), '->', dst)
