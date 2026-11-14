"""rate_match_v3.py — v3 (14 Nov 2026): rate_match_v2 followed by poss/ratings_v29 (blocked shot -0.1 instead of -0.2; the owner, 14 Nov).
ratings_v28 still runs inside rate_match_v1 at its place in the chain; v29 is a post-step after add_pen_won_v5 that re-prices the 'Shot blocked'
rows and re-rates (raw is a plain sum, so the result equals a run with the new weight at the old place). The pipeline label says v3.
Everything else — the hand-made corrections tied to their match ids, the inputs, the outputs — is rate_match_v2, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v3.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v2 as _v2                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v2 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES   # noqa: F401  (re-exported for the worker and the checks)
sys.path.insert(0, './poss')
import ratings_v29

PIPELINE = 'rate_match_v3 (build_data_v36, ratings_v29, add_pen_won_v5)'


def rate(bundle, report, **kw):
    m = _v2.rate(bundle, report, **kw)
    ratings_v29.apply(m)
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
