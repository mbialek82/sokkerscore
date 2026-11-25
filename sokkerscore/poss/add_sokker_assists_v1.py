"""add_sokker_assists_v1.py — v1 (25 Nov 2026, the owner: "sokker assigns assists very restrictively, but lets follow it in our model"): assists are Sokker's own.
Until now an assist was our key pass before a goal (shot_analysis: the last touch of a team-mate before the scorer's shot). Now a player has as many assists
as the ASSISTANT events (Score tab, event 15) that name his slot; a goal with no ASSISTANT event has no assist. The key pass, xA and big chance created
stay with our detector, so a player can have the assist without a key pass, or a key pass to a goal without the assist.
How it runs: a post-step on a rated match (after ratings_v29), like add_pen_won: Assist is worth ASSIST (0.4, unchanged), so raw moves by 0.4 per assist gained
or lost, the 'Assist' contribution row is rewritten, the rating clamped to 3.0-10.0 and rounded half up again. Names must be the names of the rows (rate_match_v8
calls it before the namesake aliases are undone)."""
from decimal import Decimal, ROUND_HALF_UP

ASSIST, LABEL, EV_ASSIST = 0.4, 'Assist', 15


def sokker_assists(M, who):
    """{name: assists} from the bundle's ASSISTANT events; who(slot, tick) is shot_analysis' occupancy lookup."""
    out = {}
    for t, J, p in M['ev']:
        if J == EV_ASSIST and p and isinstance(p[0], int) and 0 <= p[0] < 22:
            n = who(p[0], t); out[n] = out.get(n, 0) + 1
    return out


def apply(m, M, who):
    got = sokker_assists(M, who)
    changed = []
    for p in m['players']:
        new, old = got.get(p['name'], 0), p['stats'].get('assists', 0) or 0
        if new == old: continue
        raw = p['raw'] + ASSIST * (new - old)
        rows = [c for c in p['contrib'] if c['label'] != LABEL]
        if new: rows.append(dict(label=LABEL, n=new, pts=round(ASSIST * new, 3)))
        p['contrib'] = sorted((c for c in rows if abs(c['pts']) >= 0.005), key=lambda c: -abs(c['pts']))
        p['stats']['assists'] = new
        p['rating'] = float(Decimal(str(round(max(3.0, min(10.0, raw)), 6))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
        p['raw'] = round(raw, 2)
        changed.append((p['name'], old, new))
    missing = sorted(set(got) - {p['name'] for p in m['players']})
    if missing: raise ValueError('add_sokker_assists_v1: assister without a player row: ' + ', '.join(missing))
    return changed
