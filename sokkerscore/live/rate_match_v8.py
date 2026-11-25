"""rate_match_v8.py — v8 (25 Nov 2026, the owner: Jaruzelski had 0/4 passes and an assist in 44496707; "ok, fix it ... sokker assigns assists very restrictively,
but lets follow it in our model"): rate_match_v7 with two changes.
1. poss/touches_v6: a ball that flies past a player with no change of line and speed, with nobody starting a movement, is not his touch (passes, possession,
   tackles, interceptions, duels, dribbles, carries all read this touch list). patch() swaps it into every holder after rate_match_v7 has loaded the pipeline.
2. poss/add_sokker_assists_v1: assists are Sokker's ASSISTANT events, not our key pass before a goal; run after ratings_v29, before the namesake aliases are undone.
Everything else is rate_match_v7, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v8.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v7 as _v7                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v7 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES, target_of, strikes_v6   # noqa: F401  (re-exported)
import touches_v6, add_sokker_assists_v1

PIPELINE = 'rate_match_v8 (build_data_v36, ratings_v29, add_pen_won_v5, penalties_v2, strikes_v6, shots_v14, touches_v6, add_sokker_assists_v1)'

SWAPPED = touches_v6.patch()
if not any(s.startswith('match_stats_v4.') for s in SWAPPED):
    raise ImportError('rate_match_v8: touches_v6 did not reach match_stats_v4; swapped: ' + ', '.join(SWAPPED))
LAST = {}                                       # what the assist step changed in the last match (for checks)


def rate(bundle, report, **kw):
    strikes_v6.SEEN.clear()
    _v7._CTX['lineup'] = kw.get('lineup')
    extra = _v7.namesake_targets(bundle, report)
    _tgt = _v7._v6.target_of
    _v7._v6.target_of = lambda r: {**_tgt(r), **extra}
    try:
        m = _v7._v6.rate(bundle, report, **kw)
    finally:
        _v7._v6.target_of = _tgt; _v7._CTX.clear()
    M = strikes_v6.load(bundle)                   # row names are still aliases here, as are the loader's
    from shot_analysis_v17 import occupancy
    who, _ = occupancy(M)
    LAST['assists'] = add_sokker_assists_v1.apply(m, M, who)
    _v7._shot_pids(m)
    m = _v7.unalias(m, dict(strikes_v6.SEEN))
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
