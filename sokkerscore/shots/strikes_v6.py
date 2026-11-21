"""strikes_v6.py — v6 (21 Nov 2026, the owner: "how is Indonesia without a goalie", 44788004): strikes_v5.load, then two players of one team with the
same surname get different names. Indonesia's keeper Alkatiri (#1, 90 minutes) and the striker Alkatiri (#9, on at 53') were one row: the pipeline
keys players by name (occupancy's `played`, the ratings, the build), so the keeper vanished from the table and the pitch and his saves went to a
"CF who came on at 53'". It happens in 4 of the 106 rated matches (44788004 and 44779222 Alkatiri, 44139689 Jerman, 44766479 Ampudia).
The bundle names players in v['Human_namea<i>'] / v['Human_nameb<i>'] (0-10 the starters, 11+ the bench). The first holder of a surname in a team
keeps it; every later one becomes '<surname>#<i>' (ALIAS). live/rate_match_v7 joins the aliased rows to the report by the bare surname (the
existing minutes fit picks the right report player) and gives every row its bare surname back at the end.
Everything else is strikes_v5.load, unchanged."""
import strikes_v5 as _s5
from strikes_v5 import *          # noqa  (strikes, LOCO, score_events, ...)

ALIAS = '#'
_load5 = _s5.load       # kept before live/rate_match_v7 swaps every strikes_v5.load (strikes_v5's own name too) for this load


def dedupe_names(v):
    """Renames, in place, every later holder of a surname within a team to '<surname>#<i>'; returns {alias: surname}."""
    out = {}
    for t in 'ab':
        seen = set()
        for i in sorted(int(k[len('Human_name') + 1:]) for k in v if k.startswith('Human_name' + t) and k[len('Human_name') + 1:].isdigit()):
            k = f'Human_name{t}{i}'; n = v[k]
            if not n: continue
            if n in seen:
                a = f'{n}{ALIAS}{i}'; v[k] = a; out[a] = n
            else:
                seen.add(n)
    return out


def bare(name):
    """'Alkatiri#16' -> 'Alkatiri'; any other name unchanged."""
    if isinstance(name, str) and ALIAS in name:
        h, _, t = name.rpartition(ALIAS)
        if h and t.isdigit(): return h
    return name


SEEN = {}               # every alias made since the caller last cleared it: {alias: surname} (rate_match_v7 uses it to undo them)


def load(path):
    M = _load5(path)
    M['aliases'] = dedupe_names(M['v'])
    SEEN.update(M['aliases'])
    return M
