"""
match_stats.py

Three features on top of bundle_decoder:
  1. Extended assist  — last teammate PASS before a goal, even if scorer took N touches
  2. Own-assist       — defender's bad pass led directly to opponent's goal (1-step-back)
  3. Heatmaps         — per-player position density across the match

v3 changes from v2 (chat 5):
  - Set-piece fallback WIRED UP end-to-end. The three patches flagged in the
    chat-4 handoff are complete:
      (a) extract_goals now populates scorer_event_idx so the Score-tab
          ASSISTANT lookup has a starting index.
      (b) find_attributions accepts set_pieces + score_events and runs the
          fallback when the positional walker found nothing AND a set piece
          launched within 240 render ticks before the goal.
      (c) AssistAttribution gains attribution_source, and run() prints
          "(set-piece taker per Sokker)" next to the assist when the
          fallback fires.
  - run() now calls detect_set_pieces on the ball stream and passes the
    set pieces + raw score events into find_attributions.

v2 (chat 4) design notes — still current:
  - The Sokker engine does NOT model set-piece takers in the position stream
    (the ball teleports from rest into flight without any player visible at
    the ball). For goals where the positional walker finds no extended assist
    AND a set piece launched within 240 ticks before the goal, fall back to
    the Score-tab ASSISTANT event (which Sokker emits correctly for
    set-piece goals). For open-play goals with no positional assist, no
    fallback is applied — a solo goal stays a solo goal.
  - attribution_source values: 'positional' | 'set_piece_fallback'. Default
    is 'positional' regardless of whether a slot was found, because the
    positional walker is the source of truth we tried first; 'none' would
    add a third value that carries no extra information vs checking whether
    extended_assist_slot is None.

Pass definition (per your spec):
  A pass is an intentional possession transfer toward a teammate.
  Ball leaves a player's zone heading toward a teammate and that teammate
  receives it. We detect by:
    - ball was in player X's zone at time t1
    - ball travelled ≥ 4m
    - ball settled in teammate Y's zone at time t2
    - Y was NOT right next to X (else it's a give-and-go touch, not a progressive pass)

Touches that DON'T break the assist chain:
  - same-player touches (dribble)
  - ricochets off opponents with no receiver control

Own-assist:
  1 step back only. At the instant the scoring team first gained possession of the
  final attack, check: was the last player to touch the ball an opponent who lost
  control via a misplaced pass or bad touch? If yes → that opponent gets own-assist.
"""

from __future__ import annotations
import math, json

from bundle_decoder import (
    load_bundle, get_tabs, get_vars,
    decode_ball_per_frame, decode_human, decode_score,
    interp_player_to_ticks, build_player_names,
    ScoreEvent, BallTick, PlayerKeyframe,
)
from set_piece import (
    detect_set_pieces, goal_followed_set_piece, assistant_slot_for_goal,
    SetPiece,
)
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter, defaultdict


# ============================================================
# Tick-level state builder
# ============================================================

@dataclass
class TickState:
    tick: int
    bx: float   # metres
    by: float
    bz: float
    owner: Optional[int]          # slot 0..21, or None if ball is loose/airborne
    players: dict[int, tuple[float, float]]  # slot → (x,y) in metres
    minute: int = 0


def build_tick_states(
    ball: list[BallTick],
    per_tick_players: dict[int, list[tuple[float, float, int]]],
    N: int,
    pickup_radius_m: float = 3.5,
    release_radius_m: float = 5.5,
    loose_timeout_ticks: int = 15,
) -> list[TickState]:
    """Walk the match frame-by-frame with STICKY possession.

    Rules:
      - If no current owner: the closest player within `pickup_radius_m` (on ground)
        becomes owner
      - If there IS a current owner: they KEEP possession until either:
          * another player comes within pickup_radius_m AND is closer than the current owner, OR
          * ball travels > release_radius_m from the current owner for > loose_timeout_ticks frames

    This makes a through-ball or shot retain the "sender" as the last known owner
    during flight, until the receiver (or nobody, if ball goes out) takes possession.
    """
    out: list[TickState] = []
    cur_owner = None
    frames_since_owner_near = 0
    for t in range(N):
        bx = ball[t].x / 10.0
        by = ball[t].y / 10.0
        bz = ball[t].z / 10.0
        players = {slot: (per_tick_players[slot][t][0], per_tick_players[slot][t][1])
                   for slot in per_tick_players}

        # Find closest ON-GROUND candidate
        best_slot = None; best_d = pickup_radius_m
        for slot, (px, py) in players.items():
            d = math.hypot(bx - px, by - py)
            if d < best_d:
                best_d = d; best_slot = slot

        if cur_owner is None:
            # No owner — look for pickup (only when ball is on ground)
            if bz < 2.0 and best_slot is not None:
                cur_owner = best_slot
                frames_since_owner_near = 0
        else:
            # There IS an owner. Are they still near the ball?
            if cur_owner in players:
                ox, oy = players[cur_owner]
                d_owner = math.hypot(bx - ox, by - oy)
                if d_owner <= release_radius_m:
                    frames_since_owner_near = 0
                else:
                    frames_since_owner_near += 1
            else:
                frames_since_owner_near += 1
            # Did a closer player intercept?
            if best_slot is not None and best_slot != cur_owner and bz < 2.0:
                if cur_owner in players:
                    ox, oy = players[cur_owner]
                    d_owner = math.hypot(bx - ox, by - oy)
                else:
                    d_owner = 999
                # Only transfer if the new candidate is clearly closer
                if best_d < d_owner - 0.5:
                    cur_owner = best_slot
                    frames_since_owner_near = 0
            # Release if ball has been far from owner for too long
            if frames_since_owner_near > loose_timeout_ticks:
                cur_owner = None
                frames_since_owner_near = 0

        out.append(TickState(
            tick=t, bx=bx, by=by, bz=bz, owner=cur_owner, players=players,
        ))
    return out


# ============================================================
# Possession events (who owns ball, for how long, where)
# ============================================================

@dataclass
class PossessionSpan:
    """Continuous ownership run by one player (or None for loose/airborne)."""
    owner: Optional[int]
    start_tick: int
    end_tick: int           # inclusive
    start_pos: tuple[float, float]
    end_pos: tuple[float, float]
    end_ball_pos: tuple[float, float]


def collapse_to_possessions(ticks: list[TickState]) -> list[PossessionSpan]:
    """Run-length encode the owner-per-tick stream into PossessionSpans."""
    if not ticks: return []
    spans: list[PossessionSpan] = []
    cur_owner = ticks[0].owner
    cur_start = 0
    for t in range(1, len(ticks)):
        if ticks[t].owner != cur_owner:
            s = ticks[cur_start]; e = ticks[t - 1]
            sp_start = s.players.get(cur_owner, (s.bx, s.by)) if cur_owner is not None else (s.bx, s.by)
            sp_end   = e.players.get(cur_owner, (e.bx, e.by)) if cur_owner is not None else (e.bx, e.by)
            spans.append(PossessionSpan(
                owner=cur_owner, start_tick=cur_start, end_tick=t - 1,
                start_pos=sp_start, end_pos=sp_end, end_ball_pos=(e.bx, e.by),
            ))
            cur_owner = ticks[t].owner
            cur_start = t
    # Last span
    s = ticks[cur_start]; e = ticks[-1]
    sp_start = s.players.get(cur_owner, (s.bx, s.by)) if cur_owner is not None else (s.bx, s.by)
    sp_end   = e.players.get(cur_owner, (e.bx, e.by)) if cur_owner is not None else (e.bx, e.by)
    spans.append(PossessionSpan(
        owner=cur_owner, start_tick=cur_start, end_tick=len(ticks) - 1,
        start_pos=sp_start, end_pos=sp_end, end_ball_pos=(e.bx, e.by),
    ))
    return spans


# ============================================================
# Classify transitions between possessions
# ============================================================

def team_of(slot: int) -> int:
    """Return 0 for Team A (slots 0-10), 1 for Team B (slots 11-21)."""
    return 0 if slot < 11 else 1


@dataclass
class Transition:
    """What happened between two adjacent owned-possession spans (or around a loose period)."""
    from_span: Optional[PossessionSpan]  # None if first possession
    to_span: PossessionSpan
    loose_gap_ticks: int        # how long ball was loose in between
    distance_travelled_m: float # ball travel during the transition
    kind: str                   # 'pass' | 'touch' | 'turnover' | 'recovery' | 'start'


PASS_MIN_DISTANCE_M = 4.0
DRIBBLE_MAX_DISTANCE_M = 3.0


def classify_transitions(spans: list[PossessionSpan], ticks: list[TickState]) -> list[Transition]:
    """For each owned possession, figure out HOW the player got the ball:

      - 'pass'      = last owned possession was a teammate, ball travelled ≥ PASS_MIN, 
                      loose gap > 0 (ball went through air/ground to reach them)
      - 'touch'     = same player retained (shouldn't happen with run-length encoding, 
                      but covers edge cases)
      - 'turnover'  = last owned possession was an opponent AND transition looks
                      intentional from the opponent's side (they attempted a pass)
      - 'recovery'  = last owned possession was an opponent but it was a loose/scrap
                      ball (tackle, blocked shot)
      - 'start'     = first owned possession of match, or after extended dead-ball
    """
    owned_spans = [(i, s) for i, s in enumerate(spans) if s.owner is not None]
    out: list[Transition] = []
    for idx, (i, span) in enumerate(owned_spans):
        if idx == 0:
            out.append(Transition(from_span=None, to_span=span,
                                  loose_gap_ticks=0, distance_travelled_m=0.0, kind='start'))
            continue
        prev_i, prev = owned_spans[idx - 1]
        loose_gap = span.start_tick - prev.end_tick - 1
        dx = span.start_pos[0] - prev.end_ball_pos[0]
        dy = span.start_pos[1] - prev.end_ball_pos[1]
        dist = math.hypot(dx, dy)

        if prev.owner == span.owner:
            kind = 'touch'
        elif team_of(prev.owner) == team_of(span.owner):
            # Teammate-to-teammate transition
            if dist >= PASS_MIN_DISTANCE_M:
                kind = 'pass'
            elif loose_gap > 8 and dist >= 2.0:
                # short delivery with air time — still a pass (layoff)
                kind = 'pass'
            else:
                kind = 'touch'  # give-and-go, dribble carry
        else:
            # Opponent change
            # If the losing player was holding ball for a while then lost to a tackle nearby,
            # it's a recovery/tackle. If they released it (airborne span, then opponent collects),
            # it was likely a misplaced pass → turnover.
            if loose_gap >= 4 and dist >= PASS_MIN_DISTANCE_M:
                kind = 'turnover'   # losing player tried to pass; went to opponent
            else:
                kind = 'recovery'   # opponent took it near the previous player
        out.append(Transition(from_span=prev, to_span=span,
                              loose_gap_ticks=loose_gap, distance_travelled_m=dist, kind=kind))
    return out


# ============================================================
# Goal → scorer linkage via Score tab
# ============================================================

@dataclass
class GoalContext:
    goal_minute: int
    scorer_slot: Optional[int]
    scoring_team: int            # 0 or 1
    # Tick in the render-frame timeline when we think the goal happened.
    goal_tick_est: int = 0
    # Which goal was scored INTO (in physical x coords): -1 means x≈-51 end, +1 means x≈+51 end.
    goal_side: int = 0
    # v2: index of the SCORER event in score_events list. Lets us look forward
    # for the matching ASSISTANT event when applying the set-piece fallback.
    scorer_event_idx: int = -1


def find_halftime_tick(score_raw: list[int]) -> int:
    """Find the END event (halftime) tick by walking the Score tab cumulative delays."""
    from bundle_decoder import to_flash_i, to_flash_b
    x = 2; end = len(score_raw) - 1; cumulative = 0
    while x < end:
        if score_raw[x] < 0: break
        J = to_flash_b(score_raw, x); x += 1
        if J == 6:
            return cumulative // 6  # First END is halftime
        if J == 1: x += 2
        elif J == 2: x += 2
        elif J == 3: x += 2
        elif J in (7,8,9,10,11,12,14,15): x += 1
        if x + 1 >= end: break
        cumulative += to_flash_i(score_raw, x); x += 2
    return 0


def extract_goals(score_events: list[ScoreEvent], score_raw: list[int], N: int) -> list[GoalContext]:
    """Pair each GOAL marker with the next SCORER event.
    Tick = Score tab's cumulative delay ÷ 6 (viewer h=6 multiplier).
    This is the AUTHORITATIVE engine frame for the event, not a linear minute estimate.
    """
    from bundle_decoder import to_flash_i, to_flash_b
    # Re-walk Score tab to get cumulative delay at each event
    x = 2
    end = len(score_raw) - 1
    cumulative = 0
    # Map each event index → tick
    event_ticks = []
    while x < end:
        if score_raw[x] < 0: break
        J = to_flash_b(score_raw, x); x += 1
        if J == 1: x += 2
        elif J == 2: x += 2
        elif J == 3: x += 2
        elif J in (7,8,9,10,11,12,14,15): x += 1
        event_ticks.append(cumulative // 6)
        if x + 1 >= end: break
        delay = to_flash_i(score_raw, x); x += 2
        cumulative += delay
    # Now pair with the parsed events
    goals: list[GoalContext] = []
    last_goal_min = None
    last_goal_idx = None
    for i, ev in enumerate(score_events):
        if ev.tag == 'GOAL':
            last_goal_min = ev.minute
            last_goal_idx = i
        elif ev.tag == 'SCORER' and last_goal_min is not None:
            slot = ev.player_slot
            team = team_of(slot) if slot is not None else 0
            tick = event_ticks[last_goal_idx] if last_goal_idx < len(event_ticks) else 0
            goals.append(GoalContext(
                goal_minute=last_goal_min,
                scorer_slot=slot,
                scoring_team=team,
                goal_tick_est=min(N - 1, max(0, tick)),
                scorer_event_idx=i,
            ))
            last_goal_min = None
            last_goal_idx = None
    return goals


# ============================================================
# FEATURE 1 + 2: Assist & own-assist detection per goal
# ============================================================

@dataclass
class AssistAttribution:
    goal: GoalContext
    extended_assist_slot: Optional[int] = None   # last teammate PASS, any touches back
    extended_assist_dist_m: float = 0.0
    own_assist_slot: Optional[int] = None         # opponent whose misplay set it up
    own_assist_kind: str = ''                     # 'misplaced_pass' | 'bad_touch'
    # v3: source of the extended assist attribution.
    # 'positional'          — from the possession-chain walker (default)
    # 'set_piece_fallback'  — Score-tab ASSISTANT event, used when the walker
    #                         found nothing AND a set piece launched < 240
    #                         render ticks before the goal. Reflects Sokker's
    #                         engine not modelling the taker in positions.
    attribution_source: str = 'positional'


def find_attributions(
    goals: list[GoalContext],
    spans: list[PossessionSpan],
    transitions: list[Transition],
    set_pieces: Optional[list[SetPiece]] = None,
    score_events: Optional[list[ScoreEvent]] = None,
) -> list[AssistAttribution]:
    """For each goal, reconstruct the last-pass and last-opponent-touch chains.

    v3: if `set_pieces` and `score_events` are both supplied, and the positional
    walker finds no extended assist for a goal, check whether a set-piece launch
    preceded the goal within POST_LAUNCH_GOAL_WINDOW_TICKS. If so, use the
    Score-tab ASSISTANT event as the extended-assist slot. This is the
    documented set-piece fallback (chat 4 discovery).
    """
    owned_spans = [s for s in spans if s.owner is not None]
    out: list[AssistAttribution] = []

    for g in goals:
        att = AssistAttribution(goal=g)
        scorer = g.scorer_slot
        if scorer is None:
            out.append(att); continue

        # Find scorer's LAST owned span ending at or just before goal_tick_est.
        # The SCORER Score event fires AFTER the goal is dispatched, so the scoring
        # touch is the scorer's most recent span ending before goal_tick_est + small fudge.
        FUDGE = 30  # render frames (~1-2 sec of match time)
        candidates = [i for i, s in enumerate(owned_spans)
                      if s.owner == scorer and s.end_tick <= g.goal_tick_est + FUDGE]
        if not candidates:
            out.append(att); continue
        scoring_idx = max(candidates, key=lambda i: owned_spans[i].end_tick)

        # --- EXTENDED ASSIST: skip back past ALL scorer's own touches, find first teammate ---
        # The rule you gave: "pass is when you move the ball in a way to make it
        # move to your [teammate's] play". So scorer can dribble/touch many times,
        # and the assist is still the last teammate who played them the ball.
        # BUT if an opponent touched it between the teammate and the scorer, the
        # chain is broken.
        idx = scoring_idx
        assist_found = False
        while idx > 0:
            idx -= 1
            prev_span = owned_spans[idx]
            if prev_span.owner == scorer:
                # Scorer's own earlier touch — keep walking back (multi-touch allowed)
                continue
            # First non-scorer owner found
            if team_of(prev_span.owner) == g.scoring_team:
                # Teammate! Check the transition from this teammate to whoever received next
                # (which is either the scorer directly, or the scorer via their own touches)
                for tr in transitions:
                    if tr.from_span is prev_span and tr.kind == 'pass':
                        att.extended_assist_slot = prev_span.owner
                        att.extended_assist_dist_m = tr.distance_travelled_m
                        assist_found = True
                        break
                # Even if it wasn't flagged as 'pass' by the classifier, if distance
                # was substantial and it went from teammate → scorer (directly or via
                # scorer's touches), it's still an assist per user spec
                if not assist_found:
                    # Reconstruct: how far did ball travel from prev_span.end to
                    # scorer's FIRST touch after prev_span?
                    # Find the first scorer span after prev_span
                    first_scorer = None
                    for s in owned_spans:
                        if s.owner == scorer and s.start_tick > prev_span.end_tick:
                            first_scorer = s; break
                    if first_scorer:
                        dx = first_scorer.start_pos[0] - prev_span.end_ball_pos[0]
                        dy = first_scorer.start_pos[1] - prev_span.end_ball_pos[1]
                        d = math.hypot(dx, dy)
                        if d >= PASS_MIN_DISTANCE_M:
                            att.extended_assist_slot = prev_span.owner
                            att.extended_assist_dist_m = d
                            assist_found = True
                break  # stop at first teammate found
            else:
                # Opponent touched the ball between assist and scorer — chain broken
                break

        # --- v3 SET-PIECE FALLBACK ---
        # Sokker's engine doesn't model set-piece takers in the position stream,
        # so the positional walker cannot find them. If the walker returned no
        # extended_assist AND a set piece launched within 240 render ticks
        # before the goal, use the Score-tab ASSISTANT event. Confirmed on
        # match 43761572 Goal 2 where Jańczak (credited assister) is 25.5m
        # from the ball at launch.
        if (att.extended_assist_slot is None
                and set_pieces
                and score_events
                and g.scorer_event_idx >= 0):
            sp = goal_followed_set_piece(g.goal_tick_est, set_pieces)
            if sp is not None:
                slot = assistant_slot_for_goal(g.scorer_event_idx, score_events)
                if slot is not None and team_of(slot) == g.scoring_team:
                    att.extended_assist_slot = slot
                    att.attribution_source = 'set_piece_fallback'

        # --- OWN-ASSIST: 1-step-back only ---
        # Find the most recent opponent-owned span that preceded the scoring team's
        # current attack. The "current attack" starts when scoring team got ball
        # from an opponent.
        idx = scoring_idx
        last_scoring_team_idx = scoring_idx
        while idx > 0:
            idx -= 1
            prev_span = owned_spans[idx]
            if team_of(prev_span.owner) == g.scoring_team:
                last_scoring_team_idx = idx
                continue
            # First opponent span → this is the ball-losing player
            # Find the transition opponent → scoring-team that started this attack
            for tr in transitions:
                if (tr.from_span is prev_span
                        and tr.to_span is owned_spans[last_scoring_team_idx]):
                    if tr.kind == 'turnover':
                        att.own_assist_slot = prev_span.owner
                        att.own_assist_kind = 'misplaced_pass'
                    break
            break
        out.append(att)
    return out


# ============================================================
# FEATURE 3: Heatmaps (grid-bin per player)
# ============================================================

def build_heatmap(
    per_tick_players: dict[int, list[tuple[float, float, int]]],
    slot: int,
    pitch_length_m: float = 102,
    pitch_width_m: float = 64,
    cols: int = 32,
    rows: int = 20,
) -> list[list[int]]:
    """Grid of (rows × cols) tick counts for a player's position."""
    grid = [[0] * cols for _ in range(rows)]
    ticks = per_tick_players[slot]
    for (x, y, _) in ticks:
        col = int((x + pitch_length_m / 2) / pitch_length_m * (cols - 1))
        row = int((y + pitch_width_m / 2) / pitch_width_m * (rows - 1))
        col = max(0, min(cols - 1, col))
        row = max(0, min(rows - 1, row))
        grid[row][col] += 1
    return grid


# ============================================================
# Main pipeline
# ============================================================

def run(path: str):
    b = load_bundle(path)
    tabs = get_tabs(b)
    vars_d = get_vars(b)
    team_a = vars_d.get('TeamA_Name', 'Home')
    team_b = vars_d.get('TeamB_Name', 'Away')
    ball = decode_ball_per_frame(tabs['Ball'])
    score = decode_score(tabs['Score'])
    names = build_player_names(vars_d)
    real_humans = sorted(
        [k for k in tabs if k.startswith('Human') and len(tabs[k]) > 100],
        key=lambda s: int(s.replace('Human', '')),
    )
    humans = {int(n.replace('Human', '')): decode_human(tabs[n]) for n in real_humans}
    N = len(ball)
    per_tick_players = {slot: interp_player_to_ticks(kfs, N) for slot, kfs in humans.items()}

    print(f'Processing: N={N} render frames, {len(per_tick_players)} players')
    ticks = build_tick_states(ball, per_tick_players, N)
    spans = collapse_to_possessions(ticks)
    owned = [s for s in spans if s.owner is not None]
    print(f'  Possession spans: {len(spans)} total, {len(owned)} owned')

    transitions = classify_transitions(spans, ticks)
    kind_hist = Counter(t.kind for t in transitions)
    print(f'  Transitions: {dict(kind_hist)}')

    goals = extract_goals(score, tabs['Score'], N)
    halftime_tick = find_halftime_tick(tabs['Score'])
    print(f'  Halftime tick: {halftime_tick}')
    # In the data, both keepers stay at their physical positions all match
    # but the engine flips which goal "belongs" to which team after halftime.
    # 1st half: Team A defends -x, Team B defends +x (matches keeper physical positions)
    # 2nd half: SWAPPED — Team A defends +x, Team B defends -x (engine-internal swap)
    for g in goals:
        is_2nd_half = g.goal_tick_est >= halftime_tick
        # Team B scoring in 1st half → ball goes to -x (VIP's physical goal).
        # Team B scoring in 2nd half → ball goes to +x (Vodenac's physical goal,
        # which is now the "VIP defended" goal post-swap).
        if g.scoring_team == 1:  # Team B (Team Z) scoring
            g.goal_side = -1 if not is_2nd_half else +1
        else:                    # Team A (VIP) scoring
            g.goal_side = +1 if not is_2nd_half else -1
    print(f'  Goals to analyse: {len(goals)}')
    for g in goals:
        print(f'    {g.goal_minute}\'  {names.get(g.scorer_slot, "?")} (tick est {g.goal_tick_est})')

    # v3: detect set-piece launches so the assist attributor can fall back
    # to the Score-tab ASSISTANT when the positional walker comes up empty.
    set_pieces = detect_set_pieces(ball)
    print(f'  Set-piece launches detected: {len(set_pieces)}')

    attributions = find_attributions(goals, spans, transitions,
                                     set_pieces=set_pieces, score_events=score)

    print()
    print('=' * 70)
    print('ASSIST ATTRIBUTIONS (feature 1 + 2)')
    print('=' * 70)
    for att in attributions:
        g = att.goal
        scorer = names.get(g.scorer_slot, '?')
        print(f'\nGoal: {g.goal_minute}\'  {scorer} ({"A" if g.scoring_team == 0 else "B"})')
        if att.extended_assist_slot is not None:
            a_name = names[att.extended_assist_slot]
            if att.attribution_source == 'set_piece_fallback':
                print(f'  Extended assist:  {a_name}  (set-piece taker per Sokker)')
            else:
                print(f'  Extended assist:  {a_name}  (pass length {att.extended_assist_dist_m:.1f}m)')
        else:
            print(f'  Extended assist:  — (no teammate pass detected before the goal)')
        if att.own_assist_slot is not None:
            o_name = names[att.own_assist_slot]
            print(f'  Own-assist:       {o_name}  (misplaced pass led to goal)')
        else:
            print(f'  Own-assist:       — (no clean turnover 1 step back)')

    # Heatmaps for a few notable players
    print()
    print('=' * 70)
    print('HEATMAPS (position density across match)')
    print('=' * 70)
    # Print a small text heatmap for each player (rows×cols grid)
    focus_slots = sorted(per_tick_players.keys())
    COLS = 40; ROWS = 14
    for slot in focus_slots:
        grid = build_heatmap(per_tick_players, slot, cols=COLS, rows=ROWS)
        team = 'A' if slot < 11 else 'B'
        flat = [v for row in grid for v in row]
        mx = max(flat) if flat else 1
        print(f'\n{names[slot]} ({team}) — peak {mx} ticks in busiest cell')
        chars = ' .:-=+*#%@'
        for row in grid:
            line = ''.join(chars[min(len(chars) - 1, int(9 * v / max(1, mx)))] for v in row)
            print('  ' + line)

    return dict(
        ball=ball, per_tick_players=per_tick_players, ticks=ticks, spans=spans,
        transitions=transitions, goals=goals, attributions=attributions,
        names=names, N=N, team_a=team_a, team_b=team_b,
    )


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'match.json'
    run(path)
