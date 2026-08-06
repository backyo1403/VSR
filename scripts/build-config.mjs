/**
 * Runs at Vercel build time (see vercel.json: buildCommand + outputDirectory).
 * Copies public/ -> dist/, substituting the Supabase config placeholders in
 * index.html with real values from the environment along the way.
 *
 * Deliberately does NOT edit public/index.html in place — that file stays
 * checked into git with literal __SUPABASE_URL__/__SUPABASE_ANON_KEY__
 * placeholders, so running this locally can never leave real credentials
 * sitting in a tracked file. dist/ is the build output (gitignored).
 *
 * Local test build:
 *   NEXT_PUBLIC_SUPABASE_URL=... NEXT_PUBLIC_SUPABASE_ANON_KEY=... node scripts/build-config.mjs
 * (or export both from .env.local first — no dotenv dependency here on
 * purpose; this project has zero npm dependencies by design, see README).
 */
import { cp, readFile, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'public');
const OUT = path.join(ROOT, 'dist');

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error(
    'FAILED: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must both be set.\n' +
    'Set them in Vercel -> Project Settings -> Environment Variables (all environments),\n' +
    'or export them in your shell for a local test build. See .env.example.'
  );
  process.exit(1);
}

async function main() {
  await rm(OUT, { recursive: true, force: true });
  await cp(SRC, OUT, { recursive: true });

  const indexPath = path.join(OUT, 'index.html');
  let html = await readFile(indexPath, 'utf8');

  const before = html;
  html = html.replaceAll('__SUPABASE_URL__', SUPABASE_URL);
  html = html.replaceAll('__SUPABASE_ANON_KEY__', SUPABASE_ANON_KEY);

  if (html === before) {
    console.error('FAILED: no __SUPABASE_URL__/__SUPABASE_ANON_KEY__ placeholders found in public/index.html — did they get renamed or already substituted upstream?');
    process.exit(1);
  }

  await writeFile(indexPath, html, 'utf8');
  console.log(`Built dist/ with Supabase config injected (project ref: ${new URL(SUPABASE_URL).hostname.split('.')[0]}).`);
}

main().catch(e => { console.error('FAILED:', e.message); process.exit(1); });
