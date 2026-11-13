"""
bundle_decoder_v5.py

v5 (2026-10-18) — two coupled fixes, both from viewer bundle.js module 3422:
  1. PLAYER TIME BASE. The viewer advances the ball h=6 clock units per ball
     tick (`S += ft*h`, `S += h`) and moves a player over `duration+1` units
     (`InitMoveTo(..., g+1)`). v4 treated one player unit as one ball tick, so
     every player timeline was stretched 6x and truncated at ~1/6 of the
     match. Evidence: sum(duration+1) / len(ball ticks) = 6.000 for every
     Human tab of 43761572. interp_player_to_ticks now samples each player at
     unit 6*t.
  2. BALL X-FLIP REMOVED. v4 negated ball.x, "verified" by scorer-to-ball
     distance at the two goals of 43761572 — but that check ran on the
     mistimed players. With fix 1 and the viewer's own orientation (no flip)
     the scorer is 0.6 m and 1.0 m from the ball at the goal tick; with the
     flip, 62 m and 72 m. The viewer draws ball and players through the same
     convX, so no flip is the correct reading.
  Negative result recorded: the v4 flip was a compensating error, not a
  property of the data. Any downstream constant tuned on v4 output
  (touch radii, possession thresholds, the README's "4 shots, 2.06 xG"
  reference) was tuned on corrupted player positions and must be re-checked.

Canonical offline decoder for Sokker match_video bundle.
All three streams reverse-engineered from viewer source (bundle.js) and
verified against real match 43761572 (Team A: VIP Team Zielona Góra,
Team B: Team Z, final 0-2).

Streams
-------
Ball tab: segment-header + delta-run state machine.
  Each segment:
    2B uint  ft          # duration (render frames ball holds/moves)
    2B uint  A           # number of following 1B deltas
    2B int   abs_x
    2B int   abs_y
    2B int   abs_z
  Then A repeats:
    1B signed  dx
    1B signed  dy
    1B signed  dz

Human tabs (22 of them, Human0..Human21): variable-length keyframe records.
  Each keyframe:
    2B uint  duration          # render frames this segment spans
    1B       type_byte         # low 5 bits = animation type; bit 5 = "relative" flag
    If bit 5 set:
      1B signed dx
      1B signed dy
    Else:
      2B int abs_x
      2B int abs_y

Score tab: sparse event stream with 2B countdown-to-next-event.
  2B header (initial countdown), then repeating:
    1B tag                      # MatchEvents enum value
    (0-2B payload by tag)
    2B next-event delay

Coordinate units: DECIMETRES throughout.
Pitch dimensions vary per match (Sokker users select pitch size). The bundle
exposes them via `pitchheight` (long axis = x) and `pitchwidth` (short axis
= y) in `_vars` — see pitch_geometry.PitchGeometry.from_vars(). Convert
stream values to metres by dividing by 10.

Primitives
----------
  toFlash_I(p)  = data[p] + data[p+1]*69          # unsigned 2B
  toFlash_D(p)  = data[p] + data[p+1]*69 - 1000   # signed 2B
  toFlash_B(p)  = data[p]                          # unsigned 1B
  toFlash_DB(p) = data[p] - 34                     # signed 1B

Extracting the bundle
---------------------
Modern viewer no longer exposes `window._export`. Use this snippet in DevTools
on a match viewer page (/matchview?id=...):

    (function(){
      const payload = {_data: window.match.model._data, _vars: window.match.model._vars};
      const b = new Blob([JSON.stringify(payload)], {type:'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(b); a.download = 'match.json'; a.click();
    })()
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Optional

FLASH_PREC = 69
FLASH_PREC_2 = 34


# ------------------ Primitives ------------------

def to_flash_i(data, p): return data[p] + data[p + 1] * FLASH_PREC
def to_flash_d(data, p): return data[p] + data[p + 1] * FLASH_PREC - 1000
def to_flash_b(data, p): return data[p]
def to_flash_db(data, p): return data[p] - FLASH_PREC_2


# ------------------ Bundle loader ------------------

def load_bundle(path: str) -> dict:
    """Load a Sokker match_video bundle from disk.

    Auto-handles both formats:
      * JSON (modern 2D viewer): {"_data": [...], "_vars": [...]}
      * URL-encoded query-string (older 3D viewer): pitchwidth=...&Ball=...

    Stream values in URL-encoded bundles use a +48 ASCII offset on every
    byte (see bundle_url_converter.convert_bundle_text).
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content.startswith('{'):
        # URL-encoded payload — convert in-memory, no temp file.
        from bundle_url_converter import convert_bundle_text
        return convert_bundle_text(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{'); end = content.rfind('}')
        return json.loads(content[start:end + 1])


def get_tabs(bundle: dict) -> dict[str, list[int]]:
    data = bundle.get('_data') or bundle.get('data') or []
    out = {}
    for entry in data:
        if not entry: continue
        name = entry.get('name')
        tab = entry.get('tab') or {}
        arr = tab.get('data')
        if name and isinstance(arr, list):
            out[name] = arr
    return out


def get_vars(bundle: dict) -> dict[str, str]:
    v = bundle.get('_vars') or bundle.get('vars') or []
    if isinstance(v, dict): return v
    return {e.get('name'): e.get('value') for e in v if e}


# ------------------ Ball decoder ------------------

@dataclass
class BallTick:
    """Ball position at one render frame, in DECIMETRES."""
    x: float
    y: float
    z: float


def decode_ball_per_frame(ball_data: list[int]) -> list[BallTick]:
    """Return one BallTick per render frame for the whole match.

    v5: no x-flip (see module changelog). Ball and player share one frame.
    """
    out: list[BallTick] = []
    end = len(ball_data) - 1
    E = 0
    st = ct = ut = 0
    safety = 0
    while E + 10 <= end and safety < 40000:
        safety += 1
        ft = to_flash_i(ball_data, E); E += 2
        A = to_flash_i(ball_data, E); E += 2
        st = to_flash_d(ball_data, E); E += 2
        ct = to_flash_d(ball_data, E); E += 2
        ut = to_flash_d(ball_data, E); E += 2
        for _ in range(max(0, ft)):
            out.append(BallTick(float(st), float(ct), float(ut)))
        for _ in range(A):
            if E + 2 >= end: break
            dx = to_flash_db(ball_data, E); E += 1
            dy = to_flash_db(ball_data, E); E += 1
            dz = to_flash_db(ball_data, E); E += 1
            st += dx; ct += dy; ut += dz
            out.append(BallTick(float(st), float(ct), float(ut)))
    return out


# ------------------ Human decoder ------------------

@dataclass
class PlayerKeyframe:
    """One segment: player moves from their current position to (x, y) over
    `duration` render frames while playing animation `anim_type`.
    x, y are in DECIMETRES."""
    duration: int
    x: float
    y: float
    anim_type: int
    is_relative: bool


def decode_human(human_data: list[int]) -> list[PlayerKeyframe]:
    """Decode a Human tab using the viewer's variable-length record format."""
    out: list[PlayerKeyframe] = []
    i = 0
    end = len(human_data) - 1
    last_x = last_y = 0.0
    while i + 2 < end:
        if human_data[i] < 0 or human_data[i + 1] < 0: break
        duration = to_flash_i(human_data, i); i += 2
        if duration < 0 or duration > 100000: break
        if i >= end: break
        type_byte = human_data[i]; i += 1
        if type_byte < 0: break
        is_rel = bool(type_byte & 0x20)
        anim = type_byte & ~0x20
        if is_rel:
            if i + 1 >= end or human_data[i] < 0 or human_data[i + 1] < 0: break
            x = last_x + to_flash_db(human_data, i); i += 1
            y = last_y + to_flash_db(human_data, i); i += 1
        else:
            if i + 3 >= end or any(human_data[i + k] < 0 for k in range(4)): break
            x = to_flash_d(human_data, i); i += 2
            y = to_flash_d(human_data, i); i += 2
        out.append(PlayerKeyframe(duration=duration, x=float(x), y=float(y),
                                  anim_type=anim, is_relative=is_rel))
        last_x, last_y = x, y
    return out


def interp_player_to_ticks(frames: list[PlayerKeyframe], total_ticks: int,
                           units_per_tick: int = 6) -> list[tuple[float, float, int]]:
    """Player (x, y, anim_type) at each BALL tick, IN METRES.

    v5: segment j spans `duration+1` viewer units; ball tick t sits at unit
    units_per_tick*t. Linear interpolation from the previous keyframe's
    position to this one's across the segment, like Player.MoveTo.
    """
    if not frames:
        return [(0.0, 0.0, 0)] * total_ticks
    ends, u = [], 0
    for kf in frames:
        u += kf.duration + 1
        ends.append(u)
    out, j = [], 0
    for t in range(total_ticks):
        U = units_per_tick * t
        while j < len(frames) - 1 and ends[j] < U:
            j += 1
        kf = frames[j]
        s0 = ends[j - 1] if j else 0
        px, py = (frames[j - 1].x, frames[j - 1].y) if j else (kf.x, kf.y)
        f = min(1.0, max(0.0, (U - s0) / (ends[j] - s0)))
        out.append(((px + (kf.x - px) * f) / 10.0,
                    (py + (kf.y - py) * f) / 10.0, kf.anim_type))
    return out


# ------------------ Score decoder ------------------

MATCH_EVENTS = {1:'GOAL', 2:'MINUTE', 3:'SUBS', 4:'SPECIAL', 5:'POST', 6:'END',
                7:'YELLOW', 8:'RED', 9:'YELLOW_SECOND', 10:'INJURY', 11:'OFFSIDE',
                12:'FOUL', 14:'SCORER', 15:'ASSISTANT'}


@dataclass
class ScoreEvent:
    tag: str
    minute: int
    player_slot: Optional[int] = None   # 0-10 = Team A, 11-21 = Team B
    sub_on_idx: Optional[int] = None    # for SUBS, the bench player index
    score_a: int = 0
    score_b: int = 0


def decode_score(score_data: list[int]) -> list[ScoreEvent]:
    """Decode the Score tab chronologically. Minute is carried forward from MINUTE markers."""
    x = 2  # skip initial 2B countdown
    end = len(score_data) - 1
    out: list[ScoreEvent] = []
    minute = 0
    sa = sb = 0
    safety = 0
    while x < end and safety < 2000:
        safety += 1
        if x >= end or score_data[x] < 0: break
        J = to_flash_b(score_data, x); x += 1
        tag = MATCH_EVENTS.get(J, f'UNK_{J}')
        ev = ScoreEvent(tag=tag, minute=minute, score_a=sa, score_b=sb)
        if J == 1:  # GOAL
            sa = to_flash_b(score_data, x); x += 1
            sb = to_flash_b(score_data, x); x += 1
            ev.score_a = sa; ev.score_b = sb
        elif J == 2:  # MINUTE
            minute = to_flash_i(score_data, x); x += 2
            ev.minute = minute
        elif J == 3:  # SUBS
            ev.player_slot = to_flash_b(score_data, x); x += 1
            ev.sub_on_idx = to_flash_b(score_data, x); x += 1
        elif J in (7, 8, 9, 10, 11, 12, 14, 15):
            ev.player_slot = to_flash_b(score_data, x); x += 1
        out.append(ev)
        if x + 1 >= end: break
        x += 2  # skip delay
    return out


# ------------------ Player name helpers ------------------

def build_player_names(vars_d: dict) -> dict[int, str]:
    """Map slot (0..21) → display name. Slots 0-10 = team A, 11-21 = team B."""
    names = {}
    for slot in range(22):
        team_letter = 'a' if slot < 11 else 'b'
        pidx = slot if slot < 11 else slot - 11
        names[slot] = vars_d.get(f'Human_name{team_letter}{pidx}', f'slot{slot}')
    return names


# ------------------ Smoke test / CLI ------------------

def main(path: str):
    b = load_bundle(path)
    tabs = get_tabs(b)
    vars_d = get_vars(b)
    print(f'Bundle: {len(tabs)} tabs')
    print(f'  Pitch: {vars_d.get("pitchwidth")}m × {vars_d.get("pitchheight")}m')
    print(f'  Home:  {vars_d.get("TeamA_Name")}')
    print(f'  Away:  {vars_d.get("TeamB_Name")}')

    ball = decode_ball_per_frame(tabs['Ball'])
    print(f'  Ball:  {len(ball)} render frames, z_max = {max(t.z for t in ball)/10:.1f}m')

    score = decode_score(tabs['Score'])
    names = build_player_names(vars_d)
    goals = [e for e in score if e.tag == 'SCORER']
    print(f'  Score: {len(score)} events, {len(goals)} goals')
    for g in goals:
        if g.player_slot is not None:
            team = 'A' if g.player_slot < 11 else 'B'
            print(f'    {g.minute}\'  Goal by {names[g.player_slot]} ({team})')

    human_count = sum(1 for k in tabs if k.startswith('Human') and len(tabs[k]) > 100)
    print(f'  Humans: {human_count} player tabs')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'match.json')
