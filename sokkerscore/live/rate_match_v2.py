"""rate_match_v2.py — v2 (12 Nov 2026): rate_match_v1 with the hand-made corrections tied to the matches they were made for.

The shot analysis carries three corrections from video review (shot_analysis_v11–v17: OVERRIDES and OUTCOME_OVERRIDES):
  43761572  VIP Team Zielona Góra 0:2 Team Z   Jańczak gets the assist for the 0:2 (73')
  44471278  Team Z 9:0 fc_tex                   Pihkala's error leading to the 5:0
  44496766  Team Z 1:1 503 Service Unavailable  Kupecký's shot at 79' was saved, not woodwork
They are stored under (home team name, away team name), not under a match id. For the 63 published matches that was enough;
on the live system every later match between the same two teams would get the same correction (a phantom assist, a phantom
error). The team-name key already reaches a second published match (44140485, the season-78 game against 503), where it
happens to change nothing.
v2 keeps each correction for its own match id only: while a match is rated, every other entry is taken out of the tables (in
every loaded copy: the old versions v11–v13 are still used by the detectors that imported them), and put back afterwards.
A correction added later without an entry in HAND_FIXES stops the import, so it cannot leak unnoticed.
Everything else is rate_match_v1, unchanged; the pipeline label in the result says v2.

Checked by live/check_published_v2.py.
usage (any folder): python -X utf8 -I live/rate_match_v2.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v1 as _v1                       # sets the working directory and the import paths, loads the pipeline (build_data_v36 first)
from rate_match_v1 import ra, comp_label, is_nt, CWD0, ROOT   # noqa: F401  (re-exported for the worker and the checks)

PIPELINE = 'rate_match_v2 (build_data_v36, ratings_v28, add_pen_won_v5)'
HAND_FIXES = {
    ('VIP Team Zielona Góra', 'Zabujcze Strzały'): 43761572,
    ('Zabujcze Strzały', 'fc_tex'): 44471278,
    ('Zabujcze Strzały', '503 Service Unavailable'): 44496766,
}


def _tables():
    """Every OVERRIDES / OUTCOME_OVERRIDES dict that loaded pipeline code can see, each once, with a copy of its content."""
    seen = {}
    for mod in list(sys.modules.values()):
        if not isinstance(mod, types.ModuleType): continue
        try: vals = list(vars(mod).values())
        except Exception: continue
        for v in vals + [mod]:
            g = vars(v) if v is mod else getattr(v, '__globals__', None)
            if not isinstance(g, dict): continue
            for name in ('OVERRIDES', 'OUTCOME_OVERRIDES'):
                t = g.get(name)
                if isinstance(t, dict) and t and all(isinstance(k, tuple) for k in t): seen[id(t)] = t
    return [(t, dict(t)) for t in seen.values()]


_T = _tables()
_unknown = sorted({k for t, full in _T for k in full} - set(HAND_FIXES))
assert _T and not _unknown, f'hand-made corrections without a match id in HAND_FIXES: {_unknown}'


def rate(bundle, report, **kw):
    mid = int(report['id'])
    for t, full in _T:
        t.clear(); t.update({k: v for k, v in full.items() if HAND_FIXES.get(k) == mid})
    try:
        m = _v1.rate(bundle, report, **kw)
    finally:
        for t, full in _T:
            t.clear(); t.update(full)
    m['pipeline'] = PIPELINE
    return m


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
