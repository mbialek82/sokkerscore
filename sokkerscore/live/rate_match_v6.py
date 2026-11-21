"""rate_match_v6.py — v6 (21 Nov 2026): rate_match_v5 with shots/shots_v14 (never fewer shots per player than Sokker's match report; the owner chose
"only add missing shots" after a manager counted 2-12 in Indonesia 0:0 Australia, 44788004, where we showed 1-11). The pipeline binds shots_v13.shots
(build_data_v36 put it into shots_v9 before the detectors imported it) in many holders, including functions of modules no longer in sys.modules, so
every dictionary that holds it — module globals and the globals of every function object — gets shots_v14.shots, as rate_match_v5 does for the loader
(shots_v14's own globals are left alone: its _base must stay shots_v13). rate() sets shots_v14.TARGET from the report's per-player shot counts
(team, surname -> shots; a surname listed twice in one team is left out) and clears it afterwards. Everything else is rate_match_v5, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v6.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json, types, gc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v5 as _v5                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v5 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES   # noqa: F401  (re-exported for the worker and the checks)
sys.path.insert(0, './shots')
import shots_v14

PIPELINE = 'rate_match_v6 (build_data_v36, ratings_v29, add_pen_won_v5, penalties_v2, strikes_v5, shots_v14)'


def _is_v13(f):   # by source file, not identity
    if not isinstance(f, types.FunctionType): return False
    c = f.__code__
    return os.path.basename(c.co_filename) == 'shots_v13.py' and c.co_name == 'shots'


SWAPPED = []
_dicts = {id(m.__dict__): m.__dict__ for m in sys.modules.values() if m is not None and hasattr(m, '__dict__')}
_dicts.update({id(o.__globals__): o.__globals__ for o in gc.get_objects() if isinstance(o, types.FunctionType)})
for _d in _dicts.values():
    if _d is shots_v14.__dict__: continue
    for _k in [k for k, v in list(_d.items()) if _is_v13(v)]:
        _d[_k] = shots_v14.shots; SWAPPED.append(f"{_d.get('__name__', '?')}.{_k}")
if 'shots_v9.shots' not in SWAPPED or not any(s.startswith('shot_analysis_v1') for s in SWAPPED):
    raise ImportError('rate_match_v6: shots_v13.shots not found where expected; the pipeline changed, check the swap: ' + ', '.join(SWAPPED))

import shot_analysis_v18                          # analyse that keeps a 'filled' far block; same globals as v17's


def _is_v17_analyse(f):
    if not isinstance(f, types.FunctionType): return False
    c = f.__code__
    return os.path.basename(c.co_filename) == 'shot_analysis_v17.py' and c.co_name == 'analyse'


SWAPPED_ANALYSE = []
for _d in _dicts.values():
    for _k in [k for k, v in list(_d.items()) if _is_v17_analyse(v)]:
        _d[_k] = shot_analysis_v18.analyse; SWAPPED_ANALYSE.append(f"{_d.get('__name__', '?')}.{_k}")
if 'shot_analysis_v17.analyse' not in SWAPPED_ANALYSE:
    raise ImportError('rate_match_v6: shot_analysis_v17.analyse not found; check the swap: ' + ', '.join(SWAPPED_ANALYSE))


def target_of(report):
    """{(team, surname): Sokker's shot count} from the match report; a surname listed twice in one team is left out."""
    out, dup = {}, set()
    for side, T in (('home', 'A'), ('away', 'B')):
        for q in (report.get(side) or {}).get('players') or []:
            k = (T, q.get('surname'))
            if k in out: dup.add(k)
            out[k] = int(q.get('shots') or 0)
    return {k: n for k, n in out.items() if k not in dup and k[1]}


def rate(bundle, report, **kw):
    shots_v14.TARGET = target_of(report)
    try:
        m = _v5.rate(bundle, report, **kw)
    finally:
        shots_v14.TARGET = None
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
