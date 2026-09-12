// A backend for the three-word location codes.
//
// WHAT A CODE IS. Three words from the 1,296-word spoken list, all three
// random, none of them a checksum -- 1296**3 = 2,176,782,336 of them. The
// checksum is missing on purpose: THE LIVE SET IS THE CHECK. A code either was
// issued or it was not, so a misheard word names a code nobody was given and is
// caught, and the emptier the space the better that gets. A derived check word
// would cost 1,296x the space, cap detection at a flat 1 in 1,296 however few
// codes exist, and -- because the recipe would be public -- hand an attacker a
// 1,296x smaller haystack. See ../../docs/grid-scheme.md.
//
// WHAT IT IS NOT. A code does not encode anywhere. It is a row in this store,
// and it stops meaning anything when the row expires. The six-word address in
// demos/word-grid.html is the opposite of that: it decodes in the page with
// nothing else involved and is correct forever. Reach for a code only when
// saying four fewer words is worth a lookup.
import { WORDS, INDEX } from './words.js';

const SEP = '.';
const WORDS_PER_CODE = 3;

// --- codes ------------------------------------------------------------------

const randomWord = () => WORDS[crypto.getRandomValues(new Uint32Array(1))[0] % WORDS.length];
const newCode = () => Array.from({ length: WORDS_PER_CODE }, randomWord).join(SEP);

/** The words of a well-formed code, or null. Case and separators are forgiving
 *  -- someone typing what they heard should not be punished for a comma. */
function parseCode(text) {
  const parts = String(text || '').trim().toLowerCase().split(/[^a-z]+/).filter(Boolean);
  if (parts.length !== WORDS_PER_CODE) return null;
  return parts.every((w) => INDEX.has(w)) ? parts : null;
}

/** REPAIR IN THREE READS RATHER THAN 3,885.
 *
 *  A code is one word away from 3 x 1295 = 3,885 others, and checking them one
 *  by one is 3,885 reads -- absurd. So each code is also written under three
 *  PARTIAL keys, one per word left out: `p0:b.c` for the code `a.b.c`, and so
 *  on. A code with one wrong word still matches the partial key for the two
 *  words that were heard correctly, so three reads find it.
 *
 *  Two live codes can share a partial key (same two words in the same places),
 *  and the later one wins. At ~1,250 live codes against 1,679,616 slots that is
 *  about one code in 1,300, and the cost is a repair that fails rather than one
 *  that misleads: the caller is asked to say it again.
 */
const partialKeys = (w) => [`p0:${w[1]}${SEP}${w[2]}`,
                            `p1:${w[0]}${SEP}${w[2]}`,
                            `p2:${w[0]}${SEP}${w[1]}`];

// --- store ------------------------------------------------------------------

const codeKey = (words) => `c:${words.join(SEP)}`;
const num = (v, fallback) => (Number.isFinite(Number(v)) ? Number(v) : fallback);

async function reserve(env, payload, ttl) {
  // Collisions are a 1-in-2.18-billion event, so this loop is belt and braces
  // rather than load-bearing. KV is eventually consistent, so it cannot promise
  // the key is free -- it only makes an already-vanishing case vanishing twice.
  for (let attempt = 0; attempt < 5; attempt++) {
    const words = newCode().split(SEP);
    if (await env.CODES.get(codeKey(words))) continue;
    const value = JSON.stringify({ ...payload, created: Date.now() });
    const opts = { expirationTtl: ttl };
    await Promise.all([env.CODES.put(codeKey(words), value, opts),
                       ...partialKeys(words).map((k) =>
                         env.CODES.put(k, words.join(SEP), opts))]);
    return words;
  }
  return null;
}

/** The live codes one word away from this one. Usually none or one. */
async function neighbours(env, words) {
  const found = await Promise.all(partialKeys(words).map((k) => env.CODES.get(k)));
  const self = words.join(SEP);
  return [...new Set(found.filter((c) => c && c !== self))];
}

// --- http -------------------------------------------------------------------

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': 'content-type',
};
const json = (body, status = 200) =>
  new Response(JSON.stringify(body, null, 2) + '\n',
    { status, headers: { 'content-type': 'application/json; charset=utf-8', ...CORS } });

// Best-effort, per-isolate, and deliberately not the real defence. Cloudflare
// runs many isolates per colo and many colos, so this bounds one runaway client
// rather than a distributed one. REAL rate limiting belongs in front of the
// worker, in WAF rules or the rate-limiting binding; doing it in KV would spend
// a write per request, which is the most expensive way to buy the least.
const seen = new Map();
function overLimit(ip, perMinute) {
  const now = Date.now(), windowStart = now - 60_000;
  const hits = (seen.get(ip) || []).filter((t) => t > windowStart);
  hits.push(now);
  seen.set(ip, hits);
  if (seen.size > 10_000) seen.clear();          // crude, bounded, good enough
  return hits.length > perMinute;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

    const ttl = num(env.CODE_TTL_SECONDS, 900);
    const perMinute = num(env.RATE_LIMIT_PER_MINUTE, 30);
    const ip = request.headers.get('cf-connecting-ip') || 'unknown';

    if (path === '/' || path === '/health')
      return json({ ok: true, words: WORDS.length, wordsPerCode: WORDS_PER_CODE,
                    codeSpace: WORDS.length ** WORDS_PER_CODE, ttl });

    // Issue a code for a place. The body is stored as given and handed back on
    // resolve; keep it small and keep it boring.
    if (path === '/new' && request.method === 'POST') {
      if (overLimit(ip, perMinute)) return json({ error: 'rate limited' }, 429);
      let body;
      try { body = await request.json(); } catch { return json({ error: 'expected JSON' }, 400); }
      const lat = Number(body?.lat), lng = Number(body?.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) ||
          lat < -90 || lat > 90 || lng < -180 || lng > 180)
        return json({ error: 'lat and lng required, in range' }, 400);
      const words = await reserve(env, { lat, lng }, ttl);
      if (!words) return json({ error: 'could not allocate a code' }, 503);
      return json({ code: words.join(SEP), words, lat, lng,
                    expiresInSeconds: ttl }, 201);
    }

    // Resolve one. A code that is not live comes back 404 WITH the live codes a
    // single word away, so the caller can offer "did you mean" rather than just
    // asking for the whole thing again.
    if (path.startsWith('/c/') && request.method === 'GET') {
      const words = parseCode(decodeURIComponent(path.slice(3)));
      if (!words) return json({ error: 'not three words from the list' }, 400);
      const hit = await env.CODES.get(codeKey(words));
      if (hit) return json({ code: words.join(SEP), ...JSON.parse(hit) });
      return json({ error: 'no such live code', didYouMean: await neighbours(env, words) }, 404);
    }

    return json({ error: 'not found' }, 404);
  },
};

export { parseCode, partialKeys, newCode };
