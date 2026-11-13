"""strikes_v3.py — v3 (4 Nov 2026): load() cuts a match at the start of a penalty SHOOTOUT, so no detector sees the
shootout kicks (RS SHARKS 1:2 Team Z, Puchar Polski 44746083: 0:0 after 120', the Score tab's three shootout GOAL
events were credited as goals to Novo, Ozieriański and Tabaczyński, and 12 kicks were read as in-match penalties).
Shootout start = the END event at minute >= 120 when anything happens after it; ball, players and events are truncated
there. M['shootout'] = (home, away) shootout score from the uncut Score tab, else None; M['extra_time'] = True when the
match ran past minute 90. Everything else is strikes_v2 verbatim (imported)."""
import strikes_v2 as _s2
from strikes_v2 import *          # noqa  (strikes, LOCO, score_events, ...)
_orig_load = _s2.load              # kept before anyone patches strikes_v2.load to this function

def load(path):
    M = _orig_load(path)
    mm = max((p[0] + 69 * p[1] for t, J, p in M['ev'] if J == 2), default=0)
    M['extra_time'] = mm > 90; M['shootout'] = None
    if mm >= 120:
        ends = [t for t, J, p in M['ev'] if J == 6 and M['minute'](t) >= 120]
        if ends and any(t > ends[0] for t, J, p in M['ev'] if J == 1):
            cut = ends[0] + 1
            g = [p for t, J, p in M['ev'] if J == 1]
            reg = [p for t, J, p in M['ev'] if J == 1 and t < cut]
            ra, rb = (reg[-1][0], reg[-1][1]) if reg else (0, 0)
            M['shootout'] = (g[-1][0] - ra, g[-1][1] - rb)
            M['ball'] = M['ball'][:cut]; M['P'] = {s: v[:cut] for s, v in M['P'].items()}
            M['N'] = cut; M['ev'] = [e for e in M['ev'] if e[0] < cut]
    return M
