"""build_data_v36.py — v36 (11 Nov 2026): build_data_v35 with shots_v13 (shots blocked at once). build_data_v35: build_data_v33 (strikes_v4, shots_v12) plus touches_v5 (touches_v4 + a failed tackle keeps the touch with the attacker when his team touches next): a touch goes to the player who starts a ball animation,
not the nearest one (applied on top of touches_v2 and touches_v3). All three replacements must happen before any detector import; the order here must not change."""
import sys
for p in ('./poss', './shots', './out127', './def', './int130', './du132', './run151', './pen152', './xg134', './xa135'):
    sys.path.insert(0, p)
import strikes_v2, strikes_v3, strikes_v4
strikes_v2.load = strikes_v3.load; strikes_v2.strikes = strikes_v4.strikes
import shots_v9, shots_v13
shots_v9.shots = shots_v13.shots
import touches_v5
touches_v5.patch()
import build_data_v29 as _b


def build(path, mid, date, comp):
    return _b.build(path, mid, date, comp)


def job(j):
    return _b.job(j)
