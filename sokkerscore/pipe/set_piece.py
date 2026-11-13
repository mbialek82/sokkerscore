"""
set_piece_v1.py  (chat 4)

Detects set-piece launches in the ball stream. For set-piece goals, falls
back to the Score-tab ASSISTANT event because Sokker's match engine does
NOT model the taker in the position data — players walking up to the ball
is not represented; the ball simply teleports from rest into flight at
launch.

Empirical confirmation
----------------------
For match 43761572 Goal 2 (Herghelegiu 73', credited assist Jańczak):
  - Ball stationary at (-28.5, -32.0) for ~70 ticks before launch
  - Closest player at launch: Atak (defender) at 9.4m
  - Jańczak (the credited assister) is 25.5m from the ball at launch
  - No raw player keyframe is within 5m of the ball anchor in the launch
    window, even at the keyframe-tick level
  - Conclusion: the engine handles set-piece takers procedurally and emits
    no positional data for them. The Score tab ASSISTANT event is the only
    source of attribution.

Why bother detecting set pieces at all?
---------------------------------------
We need to know WHEN to override the positional walker. If the walker
returned no extended-assist for a goal AND a set piece preceded it, the
Score-tab ASSISTANT is the right answer. If the walker returned no
extended-assist for an open-play goal (genuine no-assist case, scorer
dribbled from deep), we should NOT fabricate one — Sokker's ASSISTANT
event is sometimes empty for solo goals, and we should respect when it's
empty.

Detection rule
--------------
A set-piece launch fires when:
  1. Ball stationary (||v|| < SET_PIECE_STATIONARY_VEL_DM) for
     >= SET_PIECE_DEAD_TICKS consecutive ticks.
  2. Ball then accelerates (||v|| >= SET_PIECE_LAUNCH_VEL_DM) at tick T.
  3. Ball goes airborne (z rises >= SET_PIECE_AIRBORNE_RISE_DM within
     SET_PIECE_AIRBORNE_WINDOW ticks of T) — filters out short ground
     passes from rest.

Conventions
-----------
Ball positions are in DECIMETRES (decoder native) on input; anchors are
returned in METRES for symmetry with match_stats_v1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ---------------- tunables ----------------

SET_PIECE_DEAD_TICKS         = 20    # min consecutive stationary ticks
SET_PIECE_STATIONARY_VEL_DM  = 1.0   # ||v|| under this = stationary
SET_PIECE_LAUNCH_VEL_DM      = 10.0  # ||v|| over this = launch
SET_PIECE_AIRBORNE_RISE_DM   = 5.0   # ball.z must rise this much within
SET_PIECE_AIRBORNE_WINDOW    = 10    #   this many ticks after launch

# A goal counts as set-piece-following if the launch happened within this
# many render ticks before the goal_tick_est. ~10s of match time at h=6.
POST_LAUNCH_GOAL_WINDOW_TICKS = 240


# ---------------- dataclass ----------------

@dataclass
class SetPiece:
    launch_tick: int
    anchor_x_m: float
    anchor_y_m: float
    dead_ticks: int
    launch_vel_dm: float


# ---------------- detection ----------------

def detect_set_pieces(ball_ticks_dm) -> list[SetPiece]:
    """Scan the ball stream, return all set-piece launch events.

    ball_ticks_dm: list of BallTick(x, y, z) IN DECIMETRES (decoder native).
    Anchors in returned SetPiece are in METRES.
    """
    out: list[SetPiece] = []
    if len(ball_ticks_dm) < 2:
        return out

    dead_run = 0
    dead_anchor_sum = (0.0, 0.0)

    i = 1
    while i < len(ball_ticks_dm):
        prev = ball_ticks_dm[i - 1]
        cur = ball_ticks_dm[i]
        dx = cur.x - prev.x
        dy = cur.y - prev.y
        dz = cur.z - prev.z
        v = math.sqrt(dx * dx + dy * dy + dz * dz)

        if v < SET_PIECE_STATIONARY_VEL_DM:
            dead_run += 1
            dead_anchor_sum = (dead_anchor_sum[0] + cur.x,
                               dead_anchor_sum[1] + cur.y)
            i += 1
            continue

        if dead_run >= SET_PIECE_DEAD_TICKS and v >= SET_PIECE_LAUNCH_VEL_DM:
            z0 = prev.z
            airborne = False
            for k in range(i, min(i + SET_PIECE_AIRBORNE_WINDOW, len(ball_ticks_dm))):
                if ball_ticks_dm[k].z - z0 >= SET_PIECE_AIRBORNE_RISE_DM:
                    airborne = True
                    break
            if airborne:
                anchor_x = dead_anchor_sum[0] / dead_run / 10.0
                anchor_y = dead_anchor_sum[1] / dead_run / 10.0
                out.append(SetPiece(
                    launch_tick=i,
                    anchor_x_m=anchor_x,
                    anchor_y_m=anchor_y,
                    dead_ticks=dead_run,
                    launch_vel_dm=v,
                ))

        dead_run = 0
        dead_anchor_sum = (0.0, 0.0)
        i += 1

    return out


# ---------------- goal-side helpers ----------------

def goal_followed_set_piece(
    goal_tick: int,
    set_pieces: list[SetPiece],
) -> Optional[SetPiece]:
    """Return the latest set piece whose launch is within the lookback
    window before the goal tick, or None.
    """
    candidates = [
        sp for sp in set_pieces
        if goal_tick - POST_LAUNCH_GOAL_WINDOW_TICKS <= sp.launch_tick <= goal_tick
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda s: s.launch_tick)


def assistant_slot_for_goal(
    goal_event_index: int,
    score_events: list,
) -> Optional[int]:
    """Find the ASSISTANT event that follows the SCORER for a given goal.
    Returns the slot, or None if no ASSISTANT was emitted.

    Sokker emits events in order: GOAL, SCORER, [ASSISTANT], MINUTE...
    ASSISTANT may be omitted for solo goals and for some set pieces where
    the engine doesn't credit anyone.

    `goal_event_index` is the index of the SCORER event (not the GOAL),
    matching how match_stats_v1 stores GoalContext.
    """
    for j in range(goal_event_index + 1, min(goal_event_index + 6, len(score_events))):
        ev = score_events[j]
        if ev.tag == 'ASSISTANT':
            return ev.player_slot
        if ev.tag in ('GOAL', 'SCORER', 'MINUTE'):
            break
    return None
