-- ============================================================================
-- VNA Sky Race — Supabase migration 0001: initial schema
--
-- Tables: rooms, players, questions (+ questions_public view), answers,
-- game_state, weather_events, plus a `leaderboard` view.
--
-- Run via the Supabase CLI (`supabase db push`) or paste into the SQL
-- Editor and Run — see ../schema.sql, an identical copy for the latter.
-- Idempotent: safe to re-run. Table/seed statements use IF NOT EXISTS /
-- ON CONFLICT so existing game data is never wiped by a re-run.
-- ============================================================================

create extension if not exists pgcrypto; -- gen_random_uuid()

-- ---------- drop earlier drafts of this schema (renamed/restructured) -----
drop table if exists admin_state cascade;
drop table if exists profiles cascade;
drop table if exists progress cascade;
drop view if exists questions_public cascade;
drop view if exists leaderboard cascade;

-- ============================================================================
-- 1. rooms — one row per game room. Players join by typing this code (or
--    via a ?room=CODE QR link, which just pre-fills the field). is_open
--    lets admin close a room to new joiners once the event starts;
--    max_players is an advisory cap the join flow checks client-side
--    against a count of `players` (200 by default, per the event's scale).
-- ============================================================================
create table if not exists rooms (
  code text primary key,
  max_players int not null default 200,
  is_open boolean not null default true,
  created_at timestamptz not null default now()
);
insert into rooms (code) values ('SKY01') on conflict (code) do nothing;

-- ============================================================================
-- 2. players — identity + position + running score, one row per player per
--    room. RLS alone can't protect individual columns, so a trigger further
--    guards the scoring columns from anyone but admin (see below).
-- ============================================================================
create table if not exists players (
  id uuid not null,                    -- = auth.uid() of the player's (anonymous) session
  room text not null references rooms(code) on delete cascade,
  name text not null check (char_length(name) between 1 and 18),
  avatar text not null,                -- flag SVG/emoji key, see AVATARS in the app
  position int not null default 0,     -- 0 = START … 12 = FINISH
  correct_count int not null default 0,
  total_answer_time int not null default 0, -- ms, summed across all answered legs
  turbo_used boolean not null default false,
  finish_rank int,                     -- true arrival order once they land on FINISH
  current_streak int not null default 0,
  longest_streak int not null default 0,
  answered_count int not null default 0,
  joined_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (room, id)
);
create index if not exists idx_players_room_position on players(room, position desc);

-- ============================================================================
-- 3. questions — the trivia bank. `tier` mirrors pickQuestionIndex() in the
--    app: legs 1-4 draw tier 1, legs 5-8 draw tier 2, legs 9-12 (and the
--    admin's Power Question, any leg) draw tier 3.
--    correct_index is sensitive — see questions_public view + RLS below,
--    which is what keeps players from reading the answer key via the API.
-- ============================================================================
create table if not exists questions (
  id serial primary key,
  question text not null unique, -- so ON CONFLICT below can actually detect a re-run;
                                  -- `id` is a fresh serial value every insert, so it can
                                  -- never itself be the conflict target for seed data
  options text[] not null check (array_length(options,1) = 4),
  correct_index int not null check (correct_index between 0 and 3),
  explanation text,                    -- optional, shown to the admin only
  tier smallint not null check (tier between 1 and 3),
  created_at timestamptz not null default now()
);

insert into questions (question, options, correct_index, tier) values
  ('What is Vietnam Airlines'' Skytrax rating target by 2030?', ARRAY['3-Star Airline','4-Star Airline','5-Star Airline','6-Star Airline'], 2, 1),
  ('Vietnam Airlines is a member of which global airline alliance?', ARRAY['Star Alliance','Oneworld','SkyTeam','Value Alliance'], 2, 1),
  ('In which year did Vietnam Airlines officially join SkyTeam?', ARRAY['2006','2008','2010','2012'], 2, 1),
  ('What milestone does Vietnam Airlines celebrate in 2025?', ARRAY['20th Anniversary','25th Anniversary','30th Anniversary','35th Anniversary'], 2, 1),
  ('How many domestic destinations does Vietnam Airlines currently serve?', ARRAY['19','22','30','39'], 1, 1),
  ('Vietnam Airlines operates more than how many domestic flights per day?', ARRAY['100','150','200','300'], 3, 1),
  ('How many Boeing 787 aircraft are currently in Vietnam Airlines'' fleet?', ARRAY['14','15','17','20'], 2, 1),
  ('How many Airbus A350 aircraft are currently in Vietnam Airlines'' fleet?', ARRAY['10','12','14','16'], 2, 1),
  ('Vietnam Airlines became the first Vietnamese airline to use Sustainable Aviation Fuel (SAF) on flights to which region?', ARRAY['United States','Japan','Europe','Australia'], 2, 1),
  ('Approximately how many tonnes of fuel did Vietnam Airlines save in 2024?', ARRAY['30,000','50,000','70,000','100,000'], 2, 1),

  ('How many international routes does Vietnam Airlines currently operate?', ARRAY['60','65','70','75'], 2, 2),
  ('Vietnam Airlines'' international network covers how many geographical regions?', ARRAY['5','6','7','8'], 2, 2),
  ('Vietnam Airlines currently serves how many countries and territories?', ARRAY['20','22','24','28'], 1, 2),
  ('How many direct international destinations does Vietnam Airlines offer?', ARRAY['98','100','107','115'], 2, 2),
  ('How many additional destinations are available through partnership networks?', ARRAY['80','95','100','130'], 3, 2),
  ('How many routes does Vietnam Airlines currently operate within Asia?', ARRAY['45','50','53','60'], 2, 2),
  ('Vietnam Airlines currently operates direct flights to which U.S. city?', ARRAY['Los Angeles','Seattle','San Francisco','Chicago'], 2, 2),
  ('What is the maximum seat pitch in Premium Economy Class?', ARRAY['96 cm','100 cm','107 cm','112 cm'], 2, 2),
  ('Business Class seats on wide-body aircraft can recline to:', ARRAY['150°','170°','180° (Fully Flat)','200°'], 2, 2),
  ('LotusMiles currently has more than how many members?', ARRAY['2 million','3 million','5 million','8 million'], 2, 2),

  ('According to the Sales Kit, Corporate Accounts can receive discounts of up to how much off the Published Fare?', ARRAY['15%','20%','25%','30%'], 3, 3),
  ('Which benefit is available to Tour Series partners?', ARRAY['Complimentary cabin upgrade','Lower fares than FIT Fare','Free checked baggage','Complimentary tickets'], 1, 3),
  ('The Top 3 revenue-generating agents are awarded which status?', ARRAY['Gold','Diamond','Platinum','Elite'], 2, 3),
  ('Agents ranked from 4th to 10th in revenue are awarded which status?', ARRAY['Platinum','Gold','Silver','Elite'], 1, 3),
  ('According to the Sales Kit, what is NDC?', ARRAY['BSP payment system','A communication standard between airlines and travel agents','A CRM platform','An airline ticketing website'], 1, 3),
  ('What is TAP at Vietnam Airlines?', ARRAY['A CRM system','A loyalty platform','A direct ticketing platform connected to the Passenger Service System (PSS)','A mobile application'], 2, 3),
  ('How many Branch Offices does Vietnam Airlines currently have?', ARRAY['18','19','20','22'], 1, 3),
  ('Vietnam Airlines has General Sales Agents (GSAs) in how many countries and territories?', ARRAY['18','19','20','22'], 2, 3),
  ('What is Vietnam Airlines'' brand ambition by 2030?', ARRAY['Become one of the Top 5 low-cost airlines in Asia','Become one of the Top 3 full-service airlines in Southeast Asia','Become one of the Top 10 largest airlines in the world','Become the No.1 low-cost airline in Southeast Asia'], 1, 3),
  ('According to Vision 2030, which of the following is NOT one of Vietnam Airlines'' seven strategic directions?', ARRAY['Digital Airline Transformation','Green Airline','Absolute Safety & Security','Become the Largest Low-cost Carrier in Asia'], 3, 3)
on conflict (question) do nothing;

-- ============================================================================
-- 4. game_state — one row per room; the single source of truth the admin
--    client drives and everyone else subscribes to. current_leg is 0-based
--    (matches the app's `currentQ`, NOT the human-facing "Leg N" label,
--    which is current_leg + 1).
-- ============================================================================
create table if not exists game_state (
  room text primary key references rooms(code) on delete cascade,
  game_status text not null default 'lobby'
    check (game_status in ('lobby','question','locked','reveal','finished')),
  current_leg int not null default 0,
  current_question_id int references questions(id),
  -- Set by admin only at reveal time (alongside game_status='reveal'). questions_public
  -- deliberately omits correct_index so players/presenter can't read the answer key
  -- early via the API — this column is how they legitimately learn it once revealed,
  -- without needing broader access to `questions`.
  current_correct_index int,
  question_index_by_leg jsonb not null default '{}'::jsonb, -- {"0": 4, "1": 17, ...} for history/review
  power_question_active boolean not null default false,
  power_question_used boolean not null default false,
  question_opened_at timestamptz,
  deadline timestamptz,
  revealed_legs jsonb not null default '{}'::jsonb,          -- {"0": true, ...} idempotency guard
  undo_snapshot jsonb,                                       -- one-step rollback payload
  paused boolean not null default false,
  winner_id uuid,
  milestones jsonb not null default '{"HAN":null,"SPC":null,"SGN":null}'::jsonb,
  award_shown boolean not null default false,
  congrats_shown boolean not null default false,
  storm_cleared_ids jsonb not null default '[]'::jsonb,      -- ["uid1","uid2",...], fastest first
  storm_reveal_at timestamptz,
  finish_seq int not null default 0,
  updated_at timestamptz not null default now()
);
insert into game_state (room) values ('SKY01') on conflict (room) do nothing;

-- ============================================================================
-- 5. weather_events — the fixed-leg special rounds, as data instead of a
--    hardcoded TURBULENCE_LEGS/STORM_LEG constant in the client. room = NULL
--    means "applies to every room" (today's single global ruleset); a
--    non-null room lets a future event override just that room.
-- ============================================================================
create table if not exists weather_events (
  id serial primary key,
  room text references rooms(code) on delete cascade,
  leg int not null,                     -- 0-based, same convention as game_state.current_leg
  weather_type text not null check (weather_type in ('turbulence','storm')),
  config jsonb not null default '{}'::jsonb, -- e.g. {"clearanceCount": 10} for storm
  created_at timestamptz not null default now()
);
-- Plain UNIQUE(room,leg,weather_type) wouldn't actually stop duplicate seed rows on
-- a re-run: standard SQL treats every NULL as distinct from every other NULL, and
-- room is NULL for the global ruleset below — so two partial indexes instead, one
-- per case, which is how Postgres recommends handling uniqueness with a nullable
-- column.
create unique index if not exists uniq_weather_events_global
  on weather_events(leg, weather_type) where room is null;
create unique index if not exists uniq_weather_events_room
  on weather_events(room, leg, weather_type) where room is not null;

insert into weather_events (room, leg, weather_type, config)
select null, 5, 'turbulence', '{}'::jsonb
where not exists (select 1 from weather_events where room is null and leg=5 and weather_type='turbulence')
union all
select null, 9, 'turbulence', '{}'::jsonb
where not exists (select 1 from weather_events where room is null and leg=9 and weather_type='turbulence')
union all
select null, 7, 'storm', '{"clearanceCount": 10}'::jsonb
where not exists (select 1 from weather_events where room is null and leg=7 and weather_type='storm');

-- ============================================================================
-- 6. answers — one row per (room, leg, player). Insert/update guarded by RLS
--    below so a player can only ever touch their own not-yet-submitted
--    answer, only while the leg is actually open.
-- ============================================================================
create table if not exists answers (
  room text not null,
  leg int not null,
  player_id uuid not null,
  question_id int references questions(id),
  choice int not null check (choice between 0 and 3),
  turbo boolean not null default false,
  submitted boolean not null default false,
  time_taken int, -- ms from question_opened_at to submit
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (room, leg, player_id),
  foreign key (room, player_id) references players(room, id) on delete cascade
);
create index if not exists idx_answers_room_leg on answers(room, leg);

-- ============================================================================
-- updated_at housekeeping
-- ============================================================================
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_players_updated on players;
create trigger trg_players_updated before update on players
  for each row execute function set_updated_at();

drop trigger if exists trg_game_state_updated on game_state;
create trigger trg_game_state_updated before update on game_state
  for each row execute function set_updated_at();

drop trigger if exists trg_answers_updated on answers;
create trigger trg_answers_updated before update on answers
  for each row execute function set_updated_at();

-- ============================================================================
-- Row Level Security
--
-- Admin identity: whoever is signed in as admin@vna-sky-race.local (same
-- convention as the earlier Firebase build — see the main README). Players
-- sign in anonymously; their auth.uid() becomes players.id / answers.player_id.
-- ============================================================================
create or replace function is_admin() returns boolean
language sql stable as $$
  select coalesce((auth.jwt() ->> 'email') = 'admin@vna-sky-race.local', false);
$$;

alter table rooms enable row level security;
alter table players enable row level security;
alter table questions enable row level security;
alter table game_state enable row level security;
alter table weather_events enable row level security;
alter table answers enable row level security;

-- rooms: anyone signed in can see the room list (needed to validate a room
-- code before joining); only admin creates/opens/closes rooms.
drop policy if exists "rooms readable by authenticated" on rooms;
create policy "rooms readable by authenticated" on rooms
  for select using (auth.role() = 'authenticated');
drop policy if exists "rooms writable by admin" on rooms;
create policy "rooms writable by admin" on rooms
  for all using (is_admin()) with check (is_admin());

-- players: everyone signed in can read (leaderboard); a player can insert
-- their own row only into a room that's open, and can update their own row;
-- admin can touch any row. The scoring columns are further locked down by
-- the trigger below — RLS is row-level only, so it can't by itself stop a
-- player editing their own `position`.
drop policy if exists "players readable by authenticated" on players;
create policy "players readable by authenticated" on players
  for select using (auth.role() = 'authenticated');
drop policy if exists "players writable by owner or admin" on players;
create policy "players writable by owner or admin" on players
  for all using (auth.uid() = id or is_admin())
  with check (
    is_admin()
    or (
      auth.uid() = id
      and exists (select 1 from rooms r where r.code = players.room and r.is_open)
    )
  );

create or replace function protect_player_scoring_columns() returns trigger
language plpgsql as $$
begin
  if not is_admin() then
    if new.position          is distinct from old.position
    or new.correct_count     is distinct from old.correct_count
    or new.total_answer_time is distinct from old.total_answer_time
    or new.turbo_used        is distinct from old.turbo_used
    or new.finish_rank       is distinct from old.finish_rank
    or new.current_streak    is distinct from old.current_streak
    or new.longest_streak    is distinct from old.longest_streak
    or new.answered_count    is distinct from old.answered_count
    then
      raise exception 'only admin may modify scoring fields on players';
    end if;
  end if;
  return new;
end;
$$;
drop trigger if exists trg_players_protect_scoring on players;
create trigger trg_players_protect_scoring
  before update on players
  for each row execute function protect_player_scoring_columns();

-- questions: only admin can read the full table (it has the answer key).
-- Players/presenter use the questions_public view defined further down.
drop policy if exists "questions readable by admin" on questions;
create policy "questions readable by admin" on questions
  for select using (is_admin());
drop policy if exists "questions writable by admin" on questions;
create policy "questions writable by admin" on questions
  for all using (is_admin()) with check (is_admin());

-- game_state: readable by anyone signed in, writable by admin only.
drop policy if exists "game_state readable by authenticated" on game_state;
create policy "game_state readable by authenticated" on game_state
  for select using (auth.role() = 'authenticated');
drop policy if exists "game_state writable by admin" on game_state;
create policy "game_state writable by admin" on game_state
  for all using (is_admin()) with check (is_admin());

-- weather_events: the ruleset is public knowledge (the current app already
-- prints "Turbulence auto-applies on legs 6 & 10" in the admin UI), so it's
-- fine for anyone signed in to read it; only admin edits the ruleset.
drop policy if exists "weather_events readable by authenticated" on weather_events;
create policy "weather_events readable by authenticated" on weather_events
  for select using (auth.role() = 'authenticated');
drop policy if exists "weather_events writable by admin" on weather_events;
create policy "weather_events writable by admin" on weather_events
  for all using (is_admin()) with check (is_admin());

-- answers: a player reads/writes only their own row; admin reads/writes all
-- (to run the reveal and to correct/undo). Insert/update both require the
-- leg to actually be open (game_status = 'question') and, if set, before
-- the deadline — the same guards the earlier Firebase security rules enforced.
drop policy if exists "answers readable by owner or admin" on answers;
create policy "answers readable by owner or admin" on answers
  for select using (auth.uid() = player_id or is_admin());

drop policy if exists "answers insertable by owner while question is open" on answers;
create policy "answers insertable by owner while question is open" on answers
  for insert with check (
    auth.uid() = player_id
    and exists (
      select 1 from game_state g
      where g.room = answers.room
        and g.game_status = 'question'
        and (g.deadline is null or g.deadline > now())
    )
  );

drop policy if exists "answers updatable by owner until submitted" on answers;
create policy "answers updatable by owner until submitted" on answers
  for update using (
    auth.uid() = player_id and submitted = false
  ) with check (
    auth.uid() = player_id
    and exists (
      select 1 from game_state g
      where g.room = answers.room
        and g.game_status = 'question'
        and (g.deadline is null or g.deadline > now())
    )
  );

drop policy if exists "answers writable by admin" on answers;
create policy "answers writable by admin" on answers
  for all using (is_admin()) with check (is_admin());

-- ============================================================================
-- Views
-- ============================================================================

-- questions_public: what players/presenter are allowed to see — no
-- correct_index, no explanation. This works because the view is owned by
-- the migration role (which owns `questions` too and so bypasses its RLS,
-- Postgres' standard "table owners bypass their own RLS" rule); the GRANT
-- below is what actually controls who may query the view. Verify this
-- stays true to your Supabase project's role setup before the event by
-- querying questions_public as an authenticated test user.
create view questions_public as
  select id, question, options, tier from questions;
grant select on questions_public to authenticated;

-- leaderboard: a VIEW, not a table — computed fresh from `players` every
-- query, so it can never drift out of sync with the scoring in `players`.
-- Note Supabase Realtime (postgres_changes) only replicates physical
-- tables, not views — the app subscribes to `players` changes and
-- re-derives this same ordering client-side (rankedPlayers() in the app).
-- Order matches rankedPlayers(): finished players first by true arrival
-- order (finish_rank), then still-racing players by position desc, then
-- total_answer_time asc.
create view leaderboard as
  select
    p.*,
    row_number() over (
      partition by p.room
      order by
        case when p.finish_rank is not null then 0 else 1 end,
        p.finish_rank asc nulls last,
        p.position desc,
        p.total_answer_time asc
    ) as rank
  from players p;
grant select on leaderboard to authenticated;

-- ============================================================================
-- Realtime — publish the tables that actually change during play so the
-- player/presenter/admin screens can subscribe via postgres_changes at
-- 200-concurrent-player scale. Views (leaderboard, questions_public) can't
-- be added here — see the note above leaderboard.
-- ============================================================================
alter table players replica identity full;
alter table game_state replica identity full;
alter table answers replica identity full;

do $$
begin
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and tablename='players') then
    alter publication supabase_realtime add table players;
  end if;
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and tablename='game_state') then
    alter publication supabase_realtime add table game_state;
  end if;
  if not exists (select 1 from pg_publication_tables where pubname='supabase_realtime' and tablename='answers') then
    alter publication supabase_realtime add table answers;
  end if;
end $$;
