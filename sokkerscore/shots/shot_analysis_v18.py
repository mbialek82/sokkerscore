"""shot_analysis_v18.py — v18 (21 Nov 2026): shot_analysis_v17.analyse with one change: a blocked shot from 16 m or further is still dropped
(v15 rule (d): Sokker counts few of them), EXCEPT when shots_v14 marked it 'filled' because the shooter's count in Sokker's match report needs it
(Lessy 49' and McLaren 72' in 44788004, Indonesia 0:0 Australia; Sokker 2 and 3 shots, v17 kept 1 and 2).
Only the function is new. It is compiled from v17's own source with that line changed and runs on v17's module globals, so the hand-made corrections
(OVERRIDES / OUTCOME_OVERRIDES, which live/rate_match_v2 narrows to their match id), the swapped loader and the swapped shot detector are the ones
the pipeline already uses; a copied module would carry its own correction tables. live/rate_match_v6 puts this analyse in place of v17's everywhere."""
import inspect, sys
sys.path.insert(0, './shots')
import shot_analysis_v17 as _a

OLD = "keep = [r for r in keep if not (r['end'][0] == 'blocked' and r['dist'] >= BLOCK_FAR_M)]"
NEW = "keep = [r for r in keep if not (r['end'][0] == 'blocked' and r['dist'] >= BLOCK_FAR_M and not r.get('filled'))]"

_src = inspect.getsource(_a.analyse)
if _src.count(OLD) != 1:
    raise ImportError('shot_analysis_v18: the far-block line of shot_analysis_v17.analyse was not found once')
_ns = {}
exec(compile(_src.replace(OLD, NEW), __file__, 'exec'), _a.__dict__, _ns)
analyse = _ns['analyse']
