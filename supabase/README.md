# Supabase setup

## 1. Run the schema

I can't execute SQL against your live project myself — the `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env.local` is a **publishable** key by design (safe to ship in client code, but it can't run schema changes; that's what Row Level Security is for). Running `schema.sql` needs either the SQL Editor (below) or a `service_role` key / DB connection string, which I'd rather you keep out of chat.

1. Open the [SQL Editor](https://supabase.com/dashboard/project/pduitcpdykkjxskltopc/sql/new) for this project.
2. Paste the full contents of [`schema.sql`](schema.sql).
3. Click **Run**.

It's idempotent — safe to re-run if you add more fields later (it will *not* wipe existing game data; the previous draft's `admin_state`/`profiles`/`progress` tables are dropped in favour of the `players`/`game_state` design below, but that only matters if you'd already run the old version of this file).

Tables created: `rooms`, `players`, `questions` (seeded with the current 30-question bank), `answers`, `game_state`, `weather_events` (seeded with the 3 fixed-leg rules: Turbulence on legs 6 & 10, Storm on leg 8). Plus two views: `questions_public` (what players/presenter may read — no answer key) and `leaderboard` (ranked live from `players`, same tie-break as the app's `rankedPlayers()`).

This also enables Realtime on `players`, `game_state`, `answers` (the `alter publication supabase_realtime add table ...` statements at the bottom) — no separate dashboard step needed. Views aren't part of Realtime's replication (only real tables are); the client should subscribe to `players`/`game_state`/`answers` changes and re-derive the leaderboard, same as it already does today.

## 2. Create the admin user

The schema's RLS policies treat whoever is signed in as `admin@vna-sky-race.local` as the admin (same convention as the Firebase build — see the main [README](../README.md)).

**Dashboard → Authentication → Users → Add user** → email `admin@vna-sky-race.local`, set a strong password. This password is not stored in code.

## 3. What's not done yet

`.env.local` and `schema.sql` are ready, but **`public/index.html` still talks to Firebase, not Supabase** — the client-side sync layer (`fbInit`, `fbWriteAdmin`, `fbWriteMine`, `rebuildPlayers`, the anonymous/email auth calls) hasn't been rewritten to use `@supabase/supabase-js` yet. That's a separate, substantial change — say the word and I'll do it next.

Also worth flagging: the env vars use the `NEXT_PUBLIC_` prefix, which only gets inlined into client code by a **Next.js build step**. This project is currently a single static `public/index.html` with no build tooling at all (that's deliberate — see the main README's "Local-first" philosophy). If you want to keep it that way, the Supabase URL/anon key should just be hardcoded as a JS `const` in `index.html`, the same way `FIREBASE_CONFIG` is today — `.env.local` wouldn't actually get read at runtime. If instead you want a real Next.js app (so Vercel env vars work as usual), that's a bigger restructure. Let me know which you want.
