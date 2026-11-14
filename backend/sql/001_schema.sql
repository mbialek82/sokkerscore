-- SokkerScore shared database — schema 001 (12 Nov 2026)
--
-- HOW TO RUN: Supabase dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
-- It only creates things whose names start with ss_ (tables, functions) or ss- (storage buckets), touches nothing else in
-- the project, and can be run again without harm (it does not delete data).
--
-- What it sets up (docs/live_database_v1.md explains the flow):
--   storage  ss-raw      private; the extension adds <match id>/bundle.txt(.gz), report.json, lineup.json, match.json; nobody but the worker reads it
--   storage  ss-results  public read; the worker writes matches/<match id>.json (the object the tab renders)
--   ss_matches           one row per match: the queue (queued -> rating -> rated / failed) and the list of rated matches
--   ss_players           Sokker playerId -> name
--   ss_player_matches    which matches a player played (the profile's index)
--   ss_player_totals     per player and position: minutes and summed stats (the profile's comparison groups)
--   ss_settings          a few numbers the functions read
-- Anyone with the extension (Supabase's public "anon" key) may: read the tables, add raw files for a match, call ss_submit,
-- ss_pool and ss_player. Only the worker (service_role key, kept in GitHub's secrets) may claim matches and store results.

begin;

-- ---------------------------------------------------------------- settings
create table if not exists public.ss_settings (
  key   text primary key,
  value text not null
);
insert into public.ss_settings (key, value) values
  ('current_pipeline', ''),      -- pipeline label whose totals ss_pool reads; set by the first stored result, changed by hand after a full re-rate
  ('pool_min_minutes', '180'),   -- a player enters a position's comparison group with this many minutes there
  ('max_queued',       '300'),   -- ss_submit refuses new matches while this many wait
  ('max_attempts',     '3'),     -- a match that fails this often stays 'failed'
  ('stale_minutes',    '30'),    -- a match stuck in 'rating' this long is handed out again
  ('github_repo',      'mbialek82/sokkerscore'),   -- where the worker lives: ss_start_worker starts <github_workflow> there on <github_ref>
  ('github_workflow',  'rate.yml'),
  ('github_ref',       'main')
on conflict (key) do nothing;

-- pg_net lets the database make an outgoing web call (to GitHub, to start the worker). A plain PostgreSQL does not have it.
do $$ begin
  create extension if not exists pg_net with schema extensions;
exception when others then
  raise notice 'pg_net is not available here: the database cannot start the worker itself';
end $$;

-- ---------------------------------------------------------------- matches (queue + rated list)
create table if not exists public.ss_matches (
  match_id        bigint primary key check (match_id > 0),
  status          text not null default 'queued' check (status in ('queued', 'rating', 'rated', 'failed')),
  submitted_at    timestamptz not null default now(),
  claimed_at      timestamptz,
  rated_at        timestamptz,
  attempts        integer not null default 0,
  error           text,
  pipeline        text,          -- version label of the stored result (rate_match's m.pipeline)
  totals_pipeline text,          -- pipeline under which this match is counted in ss_player_totals (null = not counted)
  match_date      date,
  season          integer,
  season_week     integer,
  comp            text,
  competition     jsonb,         -- {name, type, round, league_id} from Sokker's report
  home            text,
  away            text,
  home_id         bigint,
  away_id         bigint,
  score_home      integer,
  score_away      integer,
  nt              boolean,
  walkover        boolean        -- a side scored 8+ (inactive opponent): never in the comparison groups
);
create index if not exists ss_matches_status_idx on public.ss_matches (status, submitted_at);
create index if not exists ss_matches_date_idx   on public.ss_matches (match_date desc);

-- ---------------------------------------------------------------- players and their matches
create table if not exists public.ss_players (
  player_id  bigint primary key,           -- Sokker's playerId
  surname    text not null,
  first_name text,
  updated_at timestamptz not null default now()
);

create table if not exists public.ss_player_matches (
  match_id   bigint   not null references public.ss_matches (match_id) on delete cascade,
  idx        smallint not null,            -- his place in the result file's players list
  player_id  bigint,                       -- null when Sokker's report had no player with that surname
  team       char(1)  not null check (team in ('A', 'B')),
  name       text     not null,
  pos        text,                         -- GK / CB / FB / CM / W / CF
  minutes    smallint not null,
  rating     numeric(3,1) not null,
  starter    boolean,
  match_date date,
  season     integer,
  primary key (match_id, idx)
);
create index if not exists ss_player_matches_player_idx on public.ss_player_matches (player_id, match_date desc) where player_id is not null;

create table if not exists public.ss_player_totals (
  pipeline  text    not null,
  player_id bigint  not null,
  pos       text    not null,
  matches   integer not null default 0,
  minutes   integer not null default 0,
  top_speed numeric not null default 0,
  sums      jsonb   not null default '{}'::jsonb,   -- summed stats, plus plw / pl (pass length x passes, passes)
  primary key (pipeline, player_id, pos)
);
create index if not exists ss_player_totals_pool_idx on public.ss_player_totals (pipeline, pos, minutes);

-- ---------------------------------------------------------------- access: everybody reads, nobody writes directly
alter table public.ss_settings       enable row level security;
alter table public.ss_matches        enable row level security;
alter table public.ss_players        enable row level security;
alter table public.ss_player_matches enable row level security;
alter table public.ss_player_totals  enable row level security;

revoke all on public.ss_settings, public.ss_matches, public.ss_players, public.ss_player_matches, public.ss_player_totals from anon, authenticated;
grant select on public.ss_settings, public.ss_matches, public.ss_players, public.ss_player_matches, public.ss_player_totals to anon, authenticated;
grant all    on public.ss_settings, public.ss_matches, public.ss_players, public.ss_player_matches, public.ss_player_totals to service_role;

drop policy if exists "ss read" on public.ss_settings;
drop policy if exists "ss read" on public.ss_matches;
drop policy if exists "ss read" on public.ss_players;
drop policy if exists "ss read" on public.ss_player_matches;
drop policy if exists "ss read" on public.ss_player_totals;
create policy "ss read" on public.ss_settings       for select to anon, authenticated using (true);
create policy "ss read" on public.ss_matches        for select to anon, authenticated using (true);
create policy "ss read" on public.ss_players        for select to anon, authenticated using (true);
create policy "ss read" on public.ss_player_matches for select to anon, authenticated using (true);
create policy "ss read" on public.ss_player_totals  for select to anon, authenticated using (true);

-- ---------------------------------------------------------------- storage
insert into storage.buckets (id, name, public, file_size_limit) values
  ('ss-raw',     'ss-raw',     false, 2097152),
  ('ss-results', 'ss-results', true,  2097152)
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit;

-- the extension may ADD a match's raw files (never read, replace or delete them); the worker's key ignores these rules
drop policy if exists "ss-raw: anyone may add a match's files" on storage.objects;
create policy "ss-raw: anyone may add a match's files" on storage.objects
  for insert to anon, authenticated
  with check (bucket_id = 'ss-raw' and name ~ '^[0-9]{5,12}/(bundle\.txt|bundle\.txt\.gz|report\.json|lineup\.json|match\.json)$');

-- ---------------------------------------------------------------- helper: add two objects of numbers key by key
create or replace function public.ss_jsonb_add(a jsonb, b jsonb) returns jsonb
language sql immutable as $$
  select coalesce(jsonb_object_agg(k, v), '{}'::jsonb)
  from (select k, sum(v) as v
        from (select key as k, (value #>> '{}')::numeric as v from jsonb_each(coalesce(a, '{}'::jsonb)) where jsonb_typeof(value) = 'number'
              union all
              select key,      (value #>> '{}')::numeric      from jsonb_each(coalesce(b, '{}'::jsonb)) where jsonb_typeof(value) = 'number') t
        group by k) s
$$;

-- ---------------------------------------------------------------- extension: queue a match whose raw files are uploaded
-- returns the match's status ('queued', 'rating', 'rated', 'failed'); a match that is already known is not queued twice
create or replace function public.ss_submit(p_match_id bigint) returns text
language plpgsql security definer set search_path = public, storage, pg_temp as $$
declare
  v_status text;
  v_max    integer;
  v_queued integer;
begin
  if p_match_id is null or p_match_id <= 0 then
    raise exception 'bad match id';
  end if;
  select status into v_status from public.ss_matches where match_id = p_match_id;
  if found then
    return v_status;
  end if;
  if not exists (select 1 from storage.objects where bucket_id = 'ss-raw' and name in (p_match_id || '/bundle.txt', p_match_id || '/bundle.txt.gz'))
     or not exists (select 1 from storage.objects where bucket_id = 'ss-raw' and name = p_match_id || '/report.json') then
    raise exception 'upload the bundle and the report first';
  end if;
  select value::integer into v_max from public.ss_settings where key = 'max_queued';
  select count(*) into v_queued from public.ss_matches where status = 'queued';
  if v_queued >= coalesce(v_max, 300) then
    raise exception 'queue full, try again later';
  end if;
  insert into public.ss_matches (match_id) values (p_match_id) on conflict (match_id) do nothing;
  perform public.ss_start_worker();   -- tell GitHub to rate it now (does nothing without a token; never stops the submission)
  return 'queued';
end
$$;

-- ---------------------------------------------------------------- starting the worker from the database
-- GitHub's own five-minute timer proved unreliable (it did not fire once in the repository's first 90 minutes), so a queued
-- match starts the workflow directly: POST /repos/<repo>/actions/workflows/<workflow>/dispatches with a GitHub token kept in
-- Supabase Vault under the name ss_github_token. The token is a fine-grained one, limited to that repository with
-- "Actions: read and write". Several calls in a row are harmless: the workflow lets one run wait behind the running one.
-- ss_set_github_token stores or replaces the token; only the database owner may call it (not even the worker's key).
create or replace function public.ss_set_github_token(p_token text) returns void
language plpgsql security definer set search_path = public, vault, pg_temp as $$
declare
  v_id uuid;
begin
  if p_token is null or length(trim(p_token)) < 20 then
    raise exception 'that is not a token';
  end if;
  select id into v_id from vault.secrets where name = 'ss_github_token';
  if v_id is null then
    perform vault.create_secret(trim(p_token), 'ss_github_token', 'GitHub token that may start the SokkerScore rating workflow');
  else
    perform vault.update_secret(v_id, trim(p_token));
  end if;
end
$$;

-- returns pg_net's request id, or null when there is no token or the call could not be made
create or replace function public.ss_start_worker() returns bigint
language plpgsql security definer set search_path = public, vault, net, extensions, pg_temp as $$
declare
  v_token text;
  v_repo  text;
  v_wf    text;
  v_ref   text;
  v_id    bigint;
begin
  select decrypted_secret into v_token from vault.decrypted_secrets where name = 'ss_github_token';
  if v_token is null then
    return null;
  end if;
  select value into v_repo from public.ss_settings where key = 'github_repo';
  select value into v_wf   from public.ss_settings where key = 'github_workflow';
  select value into v_ref  from public.ss_settings where key = 'github_ref';
  select net.http_post(
           url     := 'https://api.github.com/repos/' || v_repo || '/actions/workflows/' || v_wf || '/dispatches',
           body    := jsonb_build_object('ref', coalesce(v_ref, 'main')),
           headers := jsonb_build_object('Authorization', 'Bearer ' || v_token, 'Accept', 'application/vnd.github+json',
                                         'X-GitHub-Api-Version', '2022-11-28', 'User-Agent', 'sokkerscore-database',
                                         'Content-Type', 'application/json'))
    into v_id;
  return v_id;
exception when others then
  return null;
end
$$;

-- ---------------------------------------------------------------- worker: take up to p_limit matches to rate
create or replace function public.ss_claim(p_limit integer default 5) returns setof bigint
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_stale interval;
  v_max   integer;
begin
  select (value || ' minutes')::interval into v_stale from public.ss_settings where key = 'stale_minutes';
  select value::integer into v_max from public.ss_settings where key = 'max_attempts';
  v_stale := coalesce(v_stale, interval '30 minutes');
  v_max := coalesce(v_max, 3);
  -- a match that was handed out, never came back and has no attempts left
  update public.ss_matches
     set status = 'failed', error = coalesce(error, 'no result after ' || attempts || ' attempts')
   where status = 'rating' and claimed_at < now() - v_stale and attempts >= v_max;
  return query
    with picked as (
      select match_id from public.ss_matches
       where (status = 'queued' or (status = 'rating' and claimed_at < now() - v_stale)) and attempts < v_max
       order by submitted_at
       limit greatest(p_limit, 0)
       for update skip locked)
    update public.ss_matches m
       set status = 'rating', claimed_at = now(), attempts = m.attempts + 1
      from picked
     where m.match_id = picked.match_id
    returning m.match_id;
end
$$;

-- ---------------------------------------------------------------- worker: a match could not be rated
-- p_final = true: do not try again (the upload itself is wrong: the bundle does not decode or belongs to another match);
-- otherwise it goes back to the queue until max_attempts is reached (a download that failed, a worker that crashed)
drop function if exists public.ss_fail(bigint, text);
create or replace function public.ss_fail(p_match_id bigint, p_error text, p_final boolean default false) returns text
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_max    integer;
  v_status text;
begin
  select value::integer into v_max from public.ss_settings where key = 'max_attempts';
  update public.ss_matches
     set status = case when p_final or attempts >= coalesce(v_max, 3) then 'failed' else 'queued' end,
         error = left(coalesce(p_error, ''), 2000)
   where match_id = p_match_id and status = 'rating'
  returning status into v_status;
  return v_status;
end
$$;

-- ---------------------------------------------------------------- worker: store a rated match (call after writing matches/<id>.json to ss-results)
-- p_meta:    {date, season, season_week, comp, competition, home, away, home_id, away_id, score: [home, away], nt, walkover}
-- p_players: [{idx, player_id, team, name, first_name, pos, minutes, rating, starter, top_speed, sums: {stat: number, ...}}, ...]
-- One transaction: the match row, the player rows and the comparison-group totals change together or not at all.
-- A match is added to the totals once per pipeline label and never when it is a walkover; a match without a queue row
-- (seeding) is created here.
create or replace function public.ss_store_result(p_match_id bigint, p_pipeline text, p_meta jsonb, p_players jsonb) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_prev text;
  v_walk boolean := coalesce((p_meta ->> 'walkover')::boolean, false);
begin
  if p_pipeline is null or p_pipeline = '' then
    raise exception 'pipeline label missing';
  end if;
  insert into public.ss_matches (match_id, status) values (p_match_id, 'rating') on conflict (match_id) do nothing;
  select totals_pipeline into v_prev from public.ss_matches where match_id = p_match_id for update;

  update public.ss_matches set
    status = 'rated', rated_at = now(), error = null, pipeline = p_pipeline,
    match_date = (p_meta ->> 'date')::date, season = (p_meta ->> 'season')::integer, season_week = (p_meta ->> 'season_week')::integer,
    comp = p_meta ->> 'comp', competition = p_meta -> 'competition',
    home = p_meta ->> 'home', away = p_meta ->> 'away',
    home_id = (p_meta ->> 'home_id')::bigint, away_id = (p_meta ->> 'away_id')::bigint,
    score_home = (p_meta -> 'score' ->> 0)::integer, score_away = (p_meta -> 'score' ->> 1)::integer,
    nt = (p_meta ->> 'nt')::boolean, walkover = v_walk
  where match_id = p_match_id;

  delete from public.ss_player_matches where match_id = p_match_id;
  insert into public.ss_player_matches (match_id, idx, player_id, team, name, pos, minutes, rating, starter, match_date, season)
  select p_match_id, (e ->> 'idx')::smallint, (e ->> 'player_id')::bigint, e ->> 'team', e ->> 'name', e ->> 'pos',
         (e ->> 'minutes')::smallint, (e ->> 'rating')::numeric, (e ->> 'starter')::boolean,
         (p_meta ->> 'date')::date, (p_meta ->> 'season')::integer
    from jsonb_array_elements(p_players) e;

  insert into public.ss_players (player_id, surname, first_name)
  select distinct on ((e ->> 'player_id')::bigint) (e ->> 'player_id')::bigint, e ->> 'name', nullif(e ->> 'first_name', '')
    from jsonb_array_elements(p_players) e
   where e ->> 'player_id' is not null
   order by (e ->> 'player_id')::bigint
  on conflict (player_id) do update
     set surname = excluded.surname, first_name = coalesce(excluded.first_name, public.ss_players.first_name), updated_at = now();

  if not v_walk and v_prev is distinct from p_pipeline then
    insert into public.ss_player_totals (pipeline, player_id, pos, matches, minutes, top_speed, sums)
    select distinct on ((e ->> 'player_id')::bigint, e ->> 'pos')
           p_pipeline, (e ->> 'player_id')::bigint, e ->> 'pos', 1, (e ->> 'minutes')::integer,
           coalesce((e ->> 'top_speed')::numeric, 0), coalesce(e -> 'sums', '{}'::jsonb)
      from jsonb_array_elements(p_players) e
     where e ->> 'player_id' is not null and e ->> 'pos' is not null and (e ->> 'minutes')::integer > 0
     order by (e ->> 'player_id')::bigint, e ->> 'pos'
    on conflict (pipeline, player_id, pos) do update
       set matches   = public.ss_player_totals.matches + 1,
           minutes   = public.ss_player_totals.minutes + excluded.minutes,
           top_speed = greatest(public.ss_player_totals.top_speed, excluded.top_speed),
           sums      = public.ss_jsonb_add(public.ss_player_totals.sums, excluded.sums);
    update public.ss_matches set totals_pipeline = p_pipeline where match_id = p_match_id;
  end if;

  update public.ss_settings set value = p_pipeline where key = 'current_pipeline' and value = '';
end
$$;

-- ---------------------------------------------------------------- extension: a position's comparison group
-- {min_minutes, pipeline, pos, pool: [{n, min, spd, plw, pl, goals, ...}, ...]} — the shape of the extension's data/pools.json
create or replace function public.ss_pool(p_pos text) returns jsonb
language sql stable set search_path = public, pg_temp as $$
  select jsonb_build_object(
           'min_minutes', mm.v, 'pipeline', cp.v, 'pos', p_pos,
           'pool', coalesce((select jsonb_agg(t.sums || jsonb_build_object('n', t.matches, 'min', t.minutes, 'spd', t.top_speed) order by t.player_id)
                               from public.ss_player_totals t
                              where t.pipeline = cp.v and t.pos = p_pos and t.minutes >= mm.v), '[]'::jsonb))
    from (select coalesce((select value::integer from public.ss_settings where key = 'pool_min_minutes'), 180) as v) mm,
         (select coalesce((select value from public.ss_settings where key = 'current_pipeline'), '') as v) cp
$$;

-- ---------------------------------------------------------------- extension: a player's matches, newest first
-- {player_id, n, fn, m: [[match id, index in that match's players], ...]} — the shape of one entry of data/players.json; null if unknown
create or replace function public.ss_player(p_player_id bigint) returns jsonb
language sql stable set search_path = public, pg_temp as $$
  select jsonb_build_object(
           'player_id', p.player_id, 'n', p.surname, 'fn', coalesce(p.first_name, ''),
           'm', coalesce((select jsonb_agg(jsonb_build_array(pm.match_id, pm.idx) order by pm.match_date desc nulls last, pm.match_id desc)
                            from public.ss_player_matches pm
                            join public.ss_matches mt on mt.match_id = pm.match_id and mt.status = 'rated'
                           where pm.player_id = p.player_id), '[]'::jsonb))
    from public.ss_players p
   where p.player_id = p_player_id
$$;

-- ---------------------------------------------------------------- extension: several players at once (the squad page)
-- [ss_player(id), ...] for the ids the database knows, in id order; unknown ids are left out. At most 200 ids are looked at.
create or replace function public.ss_squad(p_ids bigint[]) returns jsonb
language sql stable set search_path = public, pg_temp as $$
  select coalesce(jsonb_agg(public.ss_player(p.player_id) order by p.player_id), '[]'::jsonb)
    from public.ss_players p
   where p.player_id = any (p_ids[1:200])
$$;

-- ---------------------------------------------------------------- who may call what
revoke all on function public.ss_jsonb_add(jsonb, jsonb)                 from public, anon, authenticated;
revoke all on function public.ss_submit(bigint)                          from public, anon, authenticated;
revoke all on function public.ss_claim(integer)                          from public, anon, authenticated;
revoke all on function public.ss_fail(bigint, text, boolean)             from public, anon, authenticated;
revoke all on function public.ss_store_result(bigint, text, jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.ss_pool(text)                              from public, anon, authenticated;
revoke all on function public.ss_player(bigint)                          from public, anon, authenticated;
revoke all on function public.ss_squad(bigint[])                         from public, anon, authenticated;
revoke all on function public.ss_start_worker()                          from public, anon, authenticated;
revoke all on function public.ss_set_github_token(text)                  from public, anon, authenticated, service_role;

grant execute on function public.ss_submit(bigint)  to anon, authenticated, service_role;
grant execute on function public.ss_pool(text)      to anon, authenticated, service_role;
grant execute on function public.ss_player(bigint)  to anon, authenticated, service_role;
grant execute on function public.ss_squad(bigint[]) to anon, authenticated, service_role;
grant execute on function public.ss_jsonb_add(jsonb, jsonb)                  to service_role;
grant execute on function public.ss_claim(integer)                           to service_role;
grant execute on function public.ss_fail(bigint, text, boolean)              to service_role;
grant execute on function public.ss_store_result(bigint, text, jsonb, jsonb) to service_role;
grant execute on function public.ss_start_worker()                           to service_role;

commit;
