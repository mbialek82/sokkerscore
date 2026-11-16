"""strikes_v5.py — v5 (16 Nov 2026): strikes_v3.load with two corrections for a match decided by a golden goal in extra time
(44382583, Radzinki 3:4 Team Z, cup, 29 Jun 2026: the first match the live worker failed to rate, IndexError in strikes()).
  1. Every bundle ends with one GOAL marker 100 ticks after the last END that only repeats the final score. v3 took that marker, after an
     END at 120', for the start of a penalty shootout. A shootout now needs a GOAL after that END that CHANGES the score (44746083's three
     kicks 1:0, 1:1, 1:2 do; the golden-goal match's trailing 3:4 does not).
  2. The END event may sit one tick past the last ball tick (44382583: END at 23557, 23557 ticks), so the cut is capped at the ball length
     and N can never exceed it (v3 set N = 23558 and strikes() read B[23557]).
Everything else — the shootout score, extra_time, strikes() from strikes_v2 — is strikes_v3 verbatim (imported); strikes_v4's bounce rule is
unaffected. Patched in by live/rate_match_v5 (every module that bound strikes_v3.load by name gets this function)."""
import strikes_v3 as _s3
from strikes_v3 import *          # noqa  (strikes, LOCO, score_events, ...)
_orig_load = _s3._orig_load        # strikes_v2's own loader, kept before any patching

def load(path):
    M = _orig_load(path)
    mm = max((p[0] + 69 * p[1] for t, J, p in M['ev'] if J == 2), default=0)
    M['extra_time'] = mm > 90; M['shootout'] = None
    if mm >= 120:
        ends = [t for t, J, p in M['ev'] if J == 6 and M['minute'](t) >= 120]
        if ends:
            cut = min(ends[0] + 1, len(M['ball']))
            reg = [p for t, J, p in M['ev'] if J == 1 and t < cut]
            after = [p for t, J, p in M['ev'] if J == 1 and t >= cut]
            last = (reg[-1][0], reg[-1][1]) if reg else (0, 0)
            if any((p[0], p[1]) != last for p in after):           # a goal after the END that changes the score: a shootout
                M['shootout'] = (after[-1][0] - last[0], after[-1][1] - last[1])
                M['ball'] = M['ball'][:cut]; M['P'] = {s: v[:cut] for s, v in M['P'].items()}
                M['N'] = cut; M['ev'] = [e for e in M['ev'] if e[0] < cut]
    return M
