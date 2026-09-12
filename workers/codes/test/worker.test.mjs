// Runs on plain node with no Cloudflare account and no network: the only thing
// the worker needs from the platform is a KV binding, and a Map is one.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import worker, { parseCode, partialKeys, newCode } from '../src/index.js';
import { WORDS, WORDLIST_SHA256 } from '../src/words.js';

const here = dirname(fileURLToPath(import.meta.url));
let fails = [];
const check = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(56)} ${JSON.stringify(got)}`);
  if (!ok) fails.push(name);
};

// A KV good enough to be honest about: get/put, and an expiry we can fast-forward.
const makeKV = () => {
  const m = new Map();
  let now = () => Date.now();
  return {
    async get(k) {
      const e = m.get(k);
      if (!e) return null;
      if (e.expires && e.expires <= now()) { m.delete(k); return null; }
      return e.value;
    },
    async put(k, value, opts = {}) {
      m.set(k, { value, expires: opts.expirationTtl ? now() + opts.expirationTtl * 1000 : 0 });
    },
    _size: () => m.size,
    _travel: (secs) => { const base = Date.now() + secs * 1000; now = () => base; },
  };
};
const env = () => ({ CODES: makeKV(), CODE_TTL_SECONDS: '900', RATE_LIMIT_PER_MINUTE: '1000' });
const call = (e, path, init) =>
  worker.fetch(new Request(`https://x.invalid${path}`, init), e);
const post = (e, path, body) =>
  call(e, path, { method: 'POST', body: JSON.stringify(body),
                  headers: { 'content-type': 'application/json' } });

console.log('\nthe word list');
const src = readFileSync(join(here, '..', '..', '..', 'tools', 'wordlist',
                              'spoken-1296-plain.txt'));
check('src/words.js has not drifted from the source of truth',
      createHash('sha256').update(src).digest('hex'), WORDLIST_SHA256);
check('1,296 words', WORDS.length, 1296);

console.log('\nparsing what someone typed');
check('a clean code parses', parseCode('apron.trophy.export'),
      ['apron', 'trophy', 'export']);
check('case and stray punctuation forgiven', parseCode('  APRON, trophy / Export '),
      ['apron', 'trophy', 'export']);
// `banana` is ON the list -- picking a word that merely sounds unlikely is how
// this test passed for the wrong reason the first time round.
check('a word off the list is refused', parseCode('apron.trophy.aardvark'), null);
check('two words is not a code', parseCode('apron.trophy'), null);
check('four words is not a code', parseCode('a.b.c.d') && true, null);

console.log('\nissue and resolve');
{
  const e = env();
  const made = await post(e, '/new', { lat: 51.50072, lng: -0.12456 });
  const body = await made.json();
  check('POST /new is 201', made.status, 201);
  check('it is three words from the list', parseCode(body.code) !== null, true);
  const got = await call(e, `/c/${body.code}`);
  const back = await got.json();
  check('GET /c/<code> is 200', got.status, 200);
  check('the place comes back exactly', [back.lat, back.lng], [51.50072, -0.12456]);
  check('an unissued code is 404',
        (await call(e, '/c/apron.trophy.export')).status === 404 ||
        body.code === 'apron.trophy.export', true);
  check('rubbish is 400, not 404', (await call(e, '/c/not.real.rubbish')).status, 400);
  check('bad coordinates are refused', (await post(e, '/new', { lat: 999, lng: 0 })).status, 400);
}

console.log('\nrepair: one wrong word, found in three reads');
{
  const e = env();
  const body = await (await post(e, '/new', { lat: 10, lng: 20 })).json();
  const words = body.words;
  let repaired = 0;
  for (let i = 0; i < 3; i++) {
    const bad = [...words];
    do { bad[i] = WORDS[Math.floor(Math.random() * WORDS.length)]; }
    while (bad[i] === words[i]);
    const res = await call(e, `/c/${bad.join('.')}`);
    const j = await res.json();
    if (res.status === 404 && j.didYouMean.includes(body.code)) repaired++;
  }
  check('a wrong word in any of the three positions is offered back', repaired, 3);
  // Both replacements must actually DIFFER from what was issued. Picking
  // WORDS[0] and WORDS[1] does not guarantee that: if the issued code already
  // started with WORDS[0] only one word changed, repair rightly found it, and
  // the test failed at 1 in 1,296. CI drew that on the first run.
  const other = (i) => {
    let w; do { w = WORDS[Math.floor(Math.random() * WORDS.length)]; }
    while (w === words[i]);
    return w;
  };
  const two = [other(0), other(1), words[2]];
  const far = await (await call(e, `/c/${two.join('.')}`)).json();
  check('two wrong words is not repaired, and says so', far.didYouMean, []);
  check('each code costs 4 writes: itself and three partials', e.CODES._size(), 4);
}

console.log('\npartial keys leave out exactly one word each');
check('three of them, one per position',
      partialKeys(['a', 'b', 'c']), ['p0:b.c', 'p1:a.c', 'p2:a.b']);

console.log('\nthe code expires');
{
  const e = env();
  const body = await (await post(e, '/new', { lat: 1, lng: 2 })).json();
  check('live before the TTL', (await call(e, `/c/${body.code}`)).status, 200);
  e.CODES._travel(901);
  check('gone after it', (await call(e, `/c/${body.code}`)).status, 404);
}

console.log('\nrate limiting is best-effort but does something');
{
  const e = { ...env(), RATE_LIMIT_PER_MINUTE: '3' };
  const codes = [];
  for (let i = 0; i < 5; i++) {
    const r = await worker.fetch(new Request('https://x.invalid/new', {
      method: 'POST', body: JSON.stringify({ lat: 0, lng: 0 }),
      headers: { 'content-type': 'application/json', 'cf-connecting-ip': '203.0.113.9' },
    }), e);
    codes.push(r.status);
  }
  check('the fourth request onward is 429', codes, [201, 201, 201, 429, 429]);
}

console.log('\nrandomness');
{
  const many = new Set(Array.from({ length: 5000 }, newCode));
  check('5,000 codes, no repeats', many.size, 5000);
}

console.log();
if (fails.length) { console.error(`${fails.length} FAILURE(S): ${fails.join(', ')}`); process.exit(1); }
console.log('all checks passed');
