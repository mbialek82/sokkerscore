"""rate_match_v4.py — v4 (14 Nov 2026): rate_match_v3 with pen152/penalties_v2 (a penalty must be at the spot in front of the taker's
opponents' goal; v1 took an indirect free kick on a team's own spot for a missed penalty: Kuziel 45' in 44777783, the owner's tester report).
The pipeline loaded by rate_match_v1 binds penalties_v1.penalties by name in several modules (ratings_v25, the build_data chain), so after the
load every module attribute that IS penalties_v1.penalties is replaced by penalties_v2.penalties (the same way rate_match_v2 swaps the hand fixes).
Penalty misses (-0.5), the 'pens' list, pen_taken / pen_miss and the penalty-won step (+0.25, add_pen_won_v5 reads m['pens']) all follow.
Everything else is rate_match_v3, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v4.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v3 as _v3                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v3 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES   # noqa: F401  (re-exported for the worker and the checks)
sys.path.insert(0, './pen152')
import penalties_v1, penalties_v2

PIPELINE = 'rate_match_v4 (build_data_v36, ratings_v29, add_pen_won_v5, penalties_v2)'

def _is_v1(f):   # the pipeline holds more than one loaded copy of penalties_v1, so match by source file, not by identity
    if not isinstance(f, types.FunctionType): return False
    c = f.__code__
    return os.path.basename(c.co_filename) == 'penalties_v1.py' and c.co_name == 'penalties'


SWAPPED = []
for _name, _mod in list(sys.modules.items()):
    if _mod is None or _name in ('penalties_v1', 'penalties_v2', __name__): continue
    for _k, _v in list(getattr(_mod, '__dict__', {}).items()):
        if _is_v1(_v):
            setattr(_mod, _k, penalties_v2.penalties); SWAPPED.append(f'{_name}.{_k}')
penalties_v1.penalties = penalties_v2.penalties   # a later `from penalties_v1 import penalties` gets v2 as well
if not any(s.startswith('ratings_v25.') for s in SWAPPED):
    raise ImportError('rate_match_v4: penalties_v1 not found in ratings_v25; the pipeline changed, check the swap: ' + ', '.join(SWAPPED))


def rate(bundle, report, **kw):
    m = _v3.rate(bundle, report, **kw)
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
