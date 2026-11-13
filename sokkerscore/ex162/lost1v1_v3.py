"""lost1v1_v3.py — v3 (7 Nov 2026, the owner, decision 20): the xG of a chance lost to the keeper is CAPPED at XG_CAP = 0.30
(the model reads a keeper already on the ball as "keeper off his line" and gave up to 0.83). `xg` is the capped value that
enters the totals and the rating; `xg_raw` keeps the model's value. Detector unchanged from v1 / v2.
lost1v1_v2.py — v2: xG from this folder's model (xg158/shots_train_v3.json, bins of 40).
lost1v1_v1.py — v1 (7 Nov 2026, sokker_162): chances an attacker lost to the keeper without shooting (the owner: they get xG,
added INTO the player's and team's xG total; the keeper gets a save). Event: a spell of >= 2 consecutive touches by one
attacker (no goal/end break) whose last touch is inside the opponents' box, with no shot in the spell, and the next touch is
the opposing keeper's within 12 ticks with < 3 m of ball travel."""
import sys
for p in ('./ex162',):
    if p not in sys.path: sys.path.insert(0, p)
from lost1v1_v2 import lost as lost2

XG_CAP = 0.30

def lost(path):
    M, out = lost2(path)
    for e in out:
        e['xg_raw'] = e['xg']; e['xg'] = round(min(e['xg'], XG_CAP), 3)
    return M, out

if __name__ == '__main__':
    M, o = lost(sys.argv[1])
    for e in o: print(round(e['t'] / M['N'] * 90, 1), e['team'], e['sh'], '->', e['gk'], 'xG', e['xg'], '(raw', e['xg_raw'], ')', e['dist'], 'm')
