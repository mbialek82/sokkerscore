"""rate_match_v5.py — v5 (16 Nov 2026): rate_match_v4 with shots/strikes_v5 as the loader (a match decided by a golden goal in extra time is
not a penalty shootout, and the cut at an END event never runs past the ball data; 44382583 Radzinki 3:4 Team Z, the first match
the live worker failed to rate: IndexError in strikes()). The pipeline loaded by rate_match_v1 binds strikes_v3.load by name in several modules
(`from strikes_v2 import load` after build_data_v36's patch), so after the load every dictionary that holds a strikes_v3.load — module
globals, including those of shot_analysis_v11–v13, which are no longer in sys.modules — gets strikes_v5.load (the globals of every function object are
walked; rate_match_v4 swaps penalties_v2 in the same spirit). Every match rated by v4 rates identically under v5 (live/check_published_v5:
63 of 63); only matches v4 could not rate change. Everything else is rate_match_v4, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v5.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json, types, gc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v4 as _v4                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v4 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES   # noqa: F401  (re-exported for the worker and the checks)
sys.path.insert(0, './shots')
import strikes_v2, strikes_v3, strikes_v5

PIPELINE = 'rate_match_v5 (build_data_v36, ratings_v29, add_pen_won_v5, penalties_v2, strikes_v5)'

def _is_v3(f):   # match by source file, not by identity: the pipeline holds more than one loaded copy of strikes_v3
    if not isinstance(f, types.FunctionType): return False
    c = f.__code__
    return os.path.basename(c.co_filename) == 'strikes_v3.py' and c.co_name == 'load'


# Some holders are not in sys.modules any more (shot_analysis_v11-v13 were replaced there by aliases to v17, but their functions, with their
# own globals, still run inside the detectors), so the swap walks the globals of every function object as well as every module.
SWAPPED = []
_dicts = {id(m.__dict__): m.__dict__ for m in sys.modules.values() if m is not None and hasattr(m, '__dict__')}
_dicts.update({id(o.__globals__): o.__globals__ for o in gc.get_objects() if isinstance(o, types.FunctionType)})
for _d in _dicts.values():
    for _k in [k for k, v in list(_d.items()) if _is_v3(v)]:
        _d[_k] = strikes_v5.load; SWAPPED.append(f"{_d.get('__name__', '?')}.{_k}")
if 'strikes_v2.load' not in SWAPPED or not any(s.startswith('shot_analysis_v1') for s in SWAPPED):
    raise ImportError('rate_match_v5: strikes_v3.load not found where expected; the pipeline changed, check the swap: ' + ', '.join(SWAPPED))


def rate(bundle, report, **kw):
    m = _v4.rate(bundle, report, **kw)
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
