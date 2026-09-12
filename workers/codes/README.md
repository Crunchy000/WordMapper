# Three-word location codes, on Cloudflare Workers

A backend for the short codes in [`demos/word-grid.html`](../../demos/word-grid.html).
Three words from the same 1,296-word spoken list, resolving to a place.

```
POST /new        {"lat":51.50072,"lng":-0.12456}  ->  {"code":"apron.trophy.export", ...}
GET  /c/<code>                                    ->  {"lat":...,"lng":...}
GET  /health
```

## What a code is, and is not

**All three words are key. None of them is a checksum.** 1296³ = 2,176,782,336
codes. The check is the live set: a code either was issued or it was not, so a
misheard word names a code nobody was given and is caught — and the emptier the
space, the better that gets.

A derived check word would be worse on every axis. It costs 1,296× the space,
caps detection at a flat 1 in 1,296 however few codes are live, and — since the
recipe would have to be public — hands an attacker a 1,296× smaller haystack.

**A code does not encode anywhere.** It is a row in this store and it means
nothing once the row expires. The six-word address in the demo is the opposite:
it decodes in the page with nothing else involved and stays correct forever.
Reach for a code only when saying three fewer words is worth needing a server.

## How many codes can be live at once

Everything hinges on this one number, because a misheard code collides with a
live one at exactly `live ÷ 2,176,782,336`:

| live at once | misheard word hits another live code |
|---|---|
| 1,250 | 1 in 1,741,426 |
| 100,000 | 1 in 21,768 |
| 1,000,000 | 1 in 2,177 |
| 60,000,000 | 1 in 36 |

So **a short TTL is the safety property**, not a housekeeping detail. Codes must
be held for a *job* and released — never assigned per device or per install,
which is an easy thing to build by accident and turns 1-in-1.7-million into
1-in-36. `CODE_TTL_SECONDS` defaults to 15 minutes.

## Repair, in three reads rather than 3,885

A code is one word away from 3 × 1295 = 3,885 others, and checking them one at a
time is absurd. So each code is also written under three **partial keys**, one
per word left out — `p0:b.c`, `p1:a.c`, `p2:a.b` for `a.b.c`. A code with one
wrong word still matches the partial key for the two words heard correctly, so
three reads find it. `GET /c/<code>` returns 404 with `didYouMean` populated.

Two live codes can share a partial key and the later one wins. At ~1,250 live
against 1,679,616 slots that is about one code in 1,300, and it costs a repair
that *fails* rather than one that misleads.

Each code therefore costs **four writes** — itself and three partials. Budget
accordingly; KV free tiers are generous on reads and much less so on writes.

## Setting it up

```sh
npm install -g wrangler          # or use npx
wrangler login

wrangler kv namespace create CODES
wrangler kv namespace create CODES --preview
# paste both ids into wrangler.toml

npm test                         # no account or network needed
npm run dev                      # local, at 127.0.0.1:8787
npm run deploy
```

`npm run words` regenerates `src/words.js` from
`tools/wordlist/spoken-1296-plain.txt`. The test fails if the two drift, so the
worker and the demo can never disagree about the vocabulary.

## Things this deliberately does not do

- **One-shot claim.** Consuming a code and refusing the second claimant is a
  read-then-write race, and KV is eventually consistent. It belongs in a Durable
  Object, not here. Add it there if you need pairing rather than sharing.
- **Real rate limiting.** What is in `index.js` is per-isolate and best-effort:
  it bounds one runaway client, not a distributed one. Put WAF rules or the
  rate-limiting binding in front. Doing it in KV would spend a write per
  request, which is the most expensive way to buy the least.
- **Authentication.** `POST /new` is open. Anyone who can reach it can fill the
  store, and the store is what the detection rate depends on. Put something in
  front before it is public.
- **Storing anything but coordinates.** The body is handed back verbatim on
  resolve. Keep it small, and do not put anything in it you would mind a
  guessed code disclosing.
