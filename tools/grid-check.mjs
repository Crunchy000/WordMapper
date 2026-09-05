// Verifies the grid geometry claims in docs/uk-word-grid-review.md.
// Usage: node tools/grid-check.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'demos/uk-word-grid.html'), 'utf8');

// Pull the word list and the Hilbert implementation straight out of the demo so
// this script cannot drift from what the demo actually does.
const words = JSON.parse(html.match(/const words = (\[[^\n]*\]);/)[1]);
const hilbertSrc = html.slice(html.indexOf('function sgn'), html.indexOf('const GRID_W'));
const { gilbert2d } = await import(
  'data:text/javascript,' + encodeURIComponent(hilbertSrc + '\nexport { gilbert2d };')
);

const bbox = JSON.parse(
  html.match(/const bbox = (\{[^}]*\});/)[1].replace(/(\w+):/g, '"$1":')
);
const [, gw, gh] = html.match(/const GRID_W = (\d+), GRID_H = (\d+);/).map(Number);
const midLat = (bbox.latMin + bbox.latMax) / 2;
const kmTall = (bbox.latMax - bbox.latMin) * 111.1;
const kmWide = (bbox.lngMax - bbox.lngMin) * 111.32 * Math.cos((midLat * Math.PI) / 180);

function inspect(w, h) {
  const coords = gilbert2d(w, h);
  let breaks = 0;
  for (let i = 1; i < coords.length; i++) {
    const step =
      Math.abs(coords[i][0] - coords[i - 1][0]) + Math.abs(coords[i][1] - coords[i - 1][1]);
    if (step !== 1) breaks++;
  }
  const cellW = (kmWide / w) * 1000;
  const cellH = (kmTall / h) * 1000;
  return {
    cells: coords.length,
    distinct: new Set(coords.map((c) => c.join(','))).size,
    breaks,
    spare: coords.length - words.length,
    cellW,
    cellH,
    aspect: Math.max(cellW, cellH) / Math.min(cellW, cellH),
  };
}

function report(label, w, h) {
  const r = inspect(w, h);
  console.log(`${label} ${w}x${h}`);
  console.log(`  cells ${r.cells} (distinct ${r.distinct}), spare ${r.spare}, discontinuities ${r.breaks}`);
  for (let lvl = 1; lvl <= 3; lvl++) {
    const cw = r.cellW / w ** (lvl - 1);
    const ch = r.cellH / h ** (lvl - 1);
    const fmt = (m) => (m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m.toFixed(1)} m`);
    const aspect = Math.max(cw, ch) / Math.min(cw, ch);
    console.log(`  level ${lvl}: ${fmt(cw)} x ${fmt(ch)}  (aspect ${aspect.toFixed(2)})`);
  }
}

console.log(`word list: ${words.length} entries, ${new Set(words).size} distinct`);
const short = words.filter((w) => w.length < 4);
console.log(`outside the stated 4-7 letters: ${short.join(', ') || 'none'}`);
console.log(`bbox: ${kmWide.toFixed(0)} km wide x ${kmTall.toFixed(0)} km tall\n`);

console.log(`bbox in demo: ${JSON.stringify(bbox)}`);
console.log(`grid in demo: ${gw}x${gh}\n`);

report('in use        ', gw, gh);

console.log();
report('old (broken)  ', 41, 40);
console.log();
report('square-cell L1', 30, 56); // looks good at level 1, aspect compounds badly
console.log();
report('exact fit     ', 23, 71);

// Assertions, so this is worth running in CI rather than just reading.
const live = inspect(gw, gh);
const problems = [];
if (live.breaks > 0)
  problems.push(`the ${gw}x${gh} Hilbert path has ${live.breaks} discontinuity/ies`);
if (live.cells < words.length)
  problems.push(`grid holds ${live.cells} cells but the word list has ${words.length} entries`);
if (live.distinct !== live.cells)
  problems.push(`Hilbert path revisits cells (${live.cells} steps, ${live.distinct} distinct)`);
if (gw !== gh)
  problems.push(`grid is not square (${gw}x${gh}), so cell aspect compounds with depth`);
if (problems.length) {
  console.error('\nFAIL:\n' + problems.map((p) => `  - ${p}`).join('\n'));
  process.exitCode = 1;
} else {
  console.log('\nOK: grid is square, continuous, and large enough for the word list.');
}
