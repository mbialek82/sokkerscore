"""rate_match_v7.py — v7 (21 Nov 2026): rate_match_v6 with shots/strikes_v6 as the loader: two players of one team with the same surname are
no longer merged into one row (Indonesia's keeper Alkatiri and the striker Alkatiri in 44788004; 4 of 106 rated matches).
1. Every holder of strikes_v5.load (module globals and the globals of every function object, as rate_match_v5 did for strikes_v3) gets
   strikes_v6.load, which names the later namesake '<surname>#<slot index>' for the whole rating.
2. add_lineups_v4.apply joins the rows to the report by the bare surname: an aliased row takes its bare name for the join (the existing
   minutes fit then picks the right report player, keeper or striker) and gets its alias back for the steps after it.
3. At the end every alias in the result (player rows, shots, penalties, contribution rows, any text) becomes the bare surname, so the result
   has two rows both called 'Alkatiri' with their own minutes, position and playerId; the extension already joins namesakes by minutes.
4. Namesakes elsewhere: Sokker's shot counts reach shots_v14 for each namesake too (the report player is matched to the row by minutes; v6
   left namesakes out); age / height / weight come from the line-up entry with the same surname and the same bench / starter role (the
   line-up has no number; when that does not decide, they stay empty instead of taking the namesake's); every shot row gets 'pid', the
   shooter's playerId, so the extension can tell namesakes' shots apart (it matched shots by surname); every row gets 'first', the
   player's first name from the report (the owner: tell namesakes apart by playerId and first name; the extension shows 'S. Alkatiri').
Everything else is rate_match_v6, unchanged.
usage (any folder): python -X utf8 -I live/rate_match_v7.py <bundle.txt> <report.json> <out.json> [--lineup lineup.json] [--comp "label"] [--date YYYY-MM-DD]"""
import sys, os, json, types, gc, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate_match_v6 as _v6                       # sets the working directory and the import paths, loads the pipeline
from rate_match_v6 import ra, comp_label, is_nt, CWD0, ROOT, HAND_FIXES, target_of   # noqa: F401  (re-exported)
sys.path.insert(0, './shots'); sys.path.insert(0, './meta153')
import strikes_v6, add_lineups_v4

PIPELINE = 'rate_match_v7 (build_data_v36, ratings_v29, add_pen_won_v5, penalties_v2, strikes_v6, shots_v14)'


def _is_v5(f):
    if not isinstance(f, types.FunctionType): return False
    c = f.__code__
    return os.path.basename(c.co_filename) == 'strikes_v5.py' and c.co_name == 'load'


SWAPPED = []
_dicts = {id(m.__dict__): m.__dict__ for m in sys.modules.values() if m is not None and hasattr(m, '__dict__')}
_dicts.update({id(o.__globals__): o.__globals__ for o in gc.get_objects() if isinstance(o, types.FunctionType)})
for _d in _dicts.values():
    if _d is strikes_v6.__dict__: continue          # its _load5 must stay strikes_v5.load
    for _k in [k for k, v in list(_d.items()) if _is_v5(v)]:
        _d[_k] = strikes_v6.load; SWAPPED.append(f"{_d.get('__name__', '?')}.{_k}")
if 'strikes_v2.load' not in SWAPPED:
    raise ImportError('rate_match_v7: strikes_v5.load not found in strikes_v2; check the swap: ' + ', '.join(SWAPPED))

_apply = add_lineups_v4.apply
_CTX = {}                                       # the line-up of the match being rated (set by rate())


def _bio_namesakes(m):
    """Namesake rows: age / height / weight from the line-up entry with the same surname and bench role, or none."""
    lu = _CTX.get('lineup') or {}
    for T, key in (('A', 'homePlayers'), ('B', 'awayPlayers')):
        rows = [p for p in m['players'] if p['team'] == T]
        names = [strikes_v6.bare(p['name']) for p in rows]
        for p, b in zip(rows, names):
            if names.count(b) < 2: continue
            starter = p['on'] == 0
            L = [q for q in lu.get(key) or [] if ((q.get('name') or {}).get('surname') or '') == b and bool(q.get('bench')) != starter]
            c = ((L[0].get('info') or {}).get('characteristics') or {}) if len(L) == 1 else {}
            if c.get('age'):
                p['age'], p['height'], p['weight'] = c['age'], c.get('height'), round(c.get('weight') or 0, 1) or None
                p['pid'] = f"{b}|{p['age']}|{p['height']}|{p['weight']}"
            else:
                p['age'] = p['height'] = p['weight'] = None
                p['pid'] = f"{b}|{m['home'] if T == 'A' else m['away']}"


def _apply_bare(m, report, bio=None):
    keep = {}
    for p in m['players']:
        b = strikes_v6.bare(p['name'])
        if b != p['name']: keep[id(p)] = p['name']; p['name'] = b
    try:
        r = _apply(m, report, bio)
        _bio_namesakes(m)
        first = {q.get('playerId'): (q.get('name') or '').strip() for side in ('home', 'away') for q in (report.get(side) or {}).get('players') or []}
        for p in m['players']: p['first'] = first.get(p.get('player_id')) or None
        return r
    finally:
        for p in m['players']:
            if id(p) in keep: p['name'] = keep[id(p)]


add_lineups_v4.apply = _apply_bare
for _d in _dicts.values():                      # holders that bound apply by name (not this module: its _apply stays the original)
    if _d is globals(): continue
    for _k in [k for k, v in list(_d.items()) if v is _apply]: _d[_k] = _apply_bare

def unalias(m, aliases):
    """Every alias the loader made for this match ('<surname>#<i>') becomes '<surname>', wherever it appears in the result."""
    if not aliases: return m
    rx = re.compile('|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)))
    return json.loads(rx.sub(lambda g: aliases[g.group(0)], json.dumps(m, ensure_ascii=False)))


def namesake_targets(bundle, report):
    """{(team, row name): Sokker's shots} for namesakes (row name may be an alias): each report namesake is matched to a row by minutes."""
    M = strikes_v6.load(bundle)
    if not M['aliases']: return {}
    from shot_analysis_v17 import occupancy
    _, played = occupancy(M)
    out = {}
    for name, (slot, on, off) in played.items():
        b = strikes_v6.bare(name); T = 'A' if slot <= 10 else 'B'
        if b not in M['aliases'].values(): continue
        L = [q for q in (report.get('home' if T == 'A' else 'away') or {}).get('players') or [] if q.get('surname') == b]
        L = [q for q in L if (q.get('minuteOut') or 0) > (q.get('minuteIn') or 0)] or L
        if L:
            q = min(L, key=lambda q: abs((q.get('minuteIn') or 0) - on) + abs((q.get('minuteOut') or 0) - off))
            out[(T, name)] = int(q.get('shots') or 0)
    return out


def _shot_pids(m):
    ids = {(p['team'], p['name']): p.get('player_id') for p in m['players']}
    for s in m.get('shots') or []:
        s['pid'] = ids.get((s.get('team'), s.get('sh')))


def rate(bundle, report, **kw):
    strikes_v6.SEEN.clear()
    _CTX['lineup'] = kw.get('lineup')
    extra = namesake_targets(bundle, report)
    _tgt = _v6.target_of
    _v6.target_of = lambda r: {**_tgt(r), **extra}
    try:
        m = _v6.rate(bundle, report, **kw)
    finally:
        _v6.target_of = _tgt; _CTX.clear()
    _shot_pids(m)                                 # names are still unique here (aliases)
    m = unalias(m, dict(strikes_v6.SEEN))
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
