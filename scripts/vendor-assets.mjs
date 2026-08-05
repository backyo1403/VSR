/**
 * Pull every external asset into public/vendor/ and repoint index.html at the local
 * copies, so the only network dependency left at the venue is the Firebase WebSocket.
 *
 *   node scripts/vendor-assets.mjs
 *
 * Safe to re-run: it always rewrites from the current index.html and overwrites vendor/.
 * Needs a working internet connection (run it at the office, not at the venue).
 */
import { writeFile, mkdir, readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const VENDOR = path.join(ROOT, 'public', 'vendor');
const INDEX = path.join(ROOT, 'public', 'index.html');

// a desktop UA makes Google Fonts serve woff2 rather than the older formats
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

const SCRIPTS = [
  ['https://cdnjs.cloudflare.com/ajax/libs/canvas-confetti/1.9.2/confetti.browser.min.js', 'confetti.min.js'],
  ['https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js',      'firebase-app-compat.js'],
  ['https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js',     'firebase-auth-compat.js'],
  ['https://www.gstatic.com/firebasejs/10.12.2/firebase-database-compat.js', 'firebase-database-compat.js'],
];
const FONT_CSS = 'https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap';

async function get(url, asText = false) {
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return asText ? res.text() : Buffer.from(await res.arrayBuffer());
}

async function main() {
  if (!existsSync(INDEX)) throw new Error('public/index.html not found — run this from the VNA_Race folder');
  await mkdir(VENDOR, { recursive: true });
  let html = await readFile(INDEX, 'utf8');

  for (const [url, name] of SCRIPTS) {
    process.stdout.write(`  ${name} … `);
    await writeFile(path.join(VENDOR, name), await get(url));
    html = html.replaceAll(url, `vendor/${name}`);
    console.log('ok');
  }

  process.stdout.write('  fonts.css … ');
  let css = await get(FONT_CSS, true);
  const urls = [...new Set([...css.matchAll(/url\((https:\/\/[^)]+)\)/g)].map(m => m[1]))];
  console.log(`ok (${urls.length} font files)`);

  let i = 0;
  for (const u of urls) {
    const name = `font-${String(++i).padStart(2, '0')}.woff2`;
    process.stdout.write(`  ${name} … `);
    await writeFile(path.join(VENDOR, name), await get(u));
    css = css.replaceAll(u, name);
    console.log('ok');
  }
  await writeFile(path.join(VENDOR, 'fonts.css'), css, 'utf8');

  // swap the Google Fonts <link> tags for the local stylesheet
  html = html
    .replace(/<link rel="preconnect" href="https:\/\/fonts\.googleapis\.com">\s*/, '')
    .replace(/<link href="https:\/\/fonts\.googleapis\.com\/css2[^"]*" rel="stylesheet">/,
             '<link href="vendor/fonts.css" rel="stylesheet">');

  await writeFile(INDEX, html, 'utf8');

  const left = [...html.matchAll(/(?:src|href)="(https?:\/\/[^"]+)"/g)].map(m => m[1]);
  console.log(`\nDone. External references still in index.html: ${left.length}`);
  left.forEach(u => console.log('  ! ' + u));
  if (!left.length) console.log('  none — the page is fully self-contained.');
}

main().catch(e => { console.error('\nFAILED:', e.message); process.exit(1); });
