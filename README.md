# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live and deliberately bare: click anywhere on earth and the address
sits on the map, with its hexagon drawn round the point. **Six everyday words
name any point on earth to one [H3] hexagon about three metres across, and catch
a misheard one at least 99.9945 % of the time.** Two words to a line.

```
attempt.clean.
kangaroo.professor.
retina.menu          <- Big Ben
```

**The grid is Uber's H3**, at resolution 14: 2.7 m across the flats, 6.3 m² on
average. It replaced a square grid on a cylindrical equal-area projection, whose
squares were square only at 55.65° and 1.7 × 5.3 m at the equator. H3 puts
hexagons on an icosahedron, so a cell is close to a regular hexagon everywhere.
The trade is area, which H3 does not keep equal: cells run 3.8–7.6 m².

**The address is H3's own hierarchy.** A cell is a base cell (one of 122) and
fourteen base-7 digits. Each word carries a few of those digits plus a digit of
checksum. Word one is the base cell and one digit, words two to four three
digits each, and words five and six two each:

| Word | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| H3 digits | base + 1 | 3 | 3 | 3 | 2 | 2 |
| Check | 1 | 3 | 3 | 3 | 26 | 26 |
| Reaches | res 1, 483 km | res 4, 26 km | res 7, 1.4 km | res 10, 76 m | res 12, 11 m | **res 14, 1.5 m** |

Edges are H3's averages. The checks multiply to 18,252.

**Base 7 does not pack evenly into 1,296-word slots**, and that is the cost of
the move. Six words on the square grid were checked 1 in 82,944; on H3 they are
1 in 18,252, for a finer and rounder cell. Resolution 13 would have kept a
strong check (1 in 104,976), but at 44 m² a cell is a house rather than a
doorstep. The leftover values are not wasted: a misheard word that lands on one,
or on a pentagon's missing child, is refused outright.

**One grid, one address for a place, one length.** There are no regional boxes
and no scope to switch. There is no country search either: it cost detection, it
made the word count unpredictable, and it needed a network call.

**There is an online/offline switch**, and flipping it turns the address into a
three-word *short code*. Refresh issues another. Nothing is stored. The code is
random, which is what a real shortener would do, since a short code is a row in a
database and not an encoding of anywhere.

**All three words are key, and none of them is a checksum, because the database
already is one.** A code either was issued or it was not, so a wrong word names a
code nobody was ever given and is caught. The three words are one word away from
only 3 × 1295 = 3,885 other codes, so the service can look at all of them and
*repair* the wrong word from the one that exists, rather than merely refusing
it.

| codes issued | wrong word caught | repair unambiguous |
|---|---|---|
| 1,000 | 99.99995 % | 99.8 % |
| 10,000 | 99.9995 % | 98.2 % |
| 100,000 | 99.995 % | 83.7 % |
| 1,000,000 | 99.954 % | 16.8 % |

The point of the switch is the difference, not the word count. Six words *say
where you are* and decode with the network down. Three words resolve to the same
exact place, but they are a database row: fewer to read out, meaningless on their
own, and dead the day that database is.

**Dropping trailing words still works** and needs no context at all. An H3
cell's parent is its index with the last digits removed, so every address is a
prefix of a longer one. H3 nests only approximately, so the point is not always
inside the coarse hexagon *as drawn*, but it is always within 1.1 cell radii of
its centre.

**Dropping leading words works too**, given a nearby reference point. The
reference's surrounding H3 cells supply the missing words, and the one nearest
candidate is tested against the checksum. A tail keeps only the check its own
words carry, which is why the checksum is weighted to the last two words: five
words said keep all 18,252, three keep 2,028, and one keeps only 26.

Open the file directly in a browser: no build step. It loads Leaflet, h3-js and
map tiles from a CDN, and once loaded the address is computed entirely in the
page. SHA-256 is plain JavaScript rather than `crypto.subtle`, which is missing
outside a secure context.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
[H3]: https://h3geo.org/

## Code backend

[`workers/codes`](workers/codes) is a Cloudflare Worker that issues and resolves
the three-word codes — the real version of what the demo's switch mocks. It is
KV-backed, dependency-free, and its tests run on plain node with a `Map` for a
KV, so CI checks it without a Cloudflare account or a network.

```
POST /new   {"lat":51.50072,"lng":-0.12456}  ->  {"code":"apron.trophy.export"}
GET  /c/<code>                               ->  {"lat":...,"lng":...}
```

Connect it from the Cloudflare dashboard with **Import a repository**, root
directory `workers/codes`, deploy command `npx wrangler deploy` — the KV binding
carries no id so the first deploy provisions or connects one rather than failing
on a placeholder.

Two things in it are worth knowing even if you never deploy it. **A short TTL is
the safety property**: a misheard code collides with a live one at exactly
`live ÷ 2,176,782,336`, so codes held for a job and released give 1 in 1.7
million, while a code assigned per handset would give 1 in 36. And **repair
costs three reads, not 3,885** — each code is also written under three partial
keys, one per word left out, so a code with one wrong word still matches on the
two that were heard correctly.

## Publishing

`index.html` and `demos/` are deployed to GitHub Pages by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to
`main`. Pull requests run the build and the grid check without deploying.

**One-time setup:** Pages has to be switched on for the repository before the
first deploy can succeed — *Settings → Pages → Build and deployment → Source:
**GitHub Actions***. The workflow cannot do this itself; creating a Pages site
needs repo-admin rights, which the Actions token does not have. Until it is
done, the deploy step fails with `Get Pages site failed`. Once it is done,
re-run the workflow and it will publish.

## Docs

- [`docs/grid-scheme.md`](docs/grid-scheme.md) — the scheme: why H3 replaced the
  square grid, how H3's base-7 digits are packed into words, what the resolution
  cost in checksum strength, both directions of shortening, and why the check is
  weighted to the last words.
- [`docs/coverage.md`](docs/coverage.md) — the square-root law relating area to
  resolution, and the word-list vs address-length trade. Written for an earlier,
  UK-only version of the scheme; the arithmetic still holds.
- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — a review of the
  original imported demo. Historical: that demo and its scheme are gone.

## Word list

**1,296 words, every one graded CEFR A1–B2** — the band a person can retrieve
under pressure, not merely recognise. Generated by [`tools/wordlist`](tools/wordlist)
from the 9,025 graded headwords of the Oxford 5000 and the English Vocabulary
Profile, minus names, places, offensive and vulgar words, inflections of other
words, words spelled two ways — and then everything confusable or sound-alike.
**Zero homophones, zero pairs one articulatory feature apart, zero pairs within
one phoneme error.**

BIP-39 was here first and was the wrong list. It is designed to be *typed and
checksummed*, not spoken: it contains `pair`/`pear`, `peace`/`piece`,
`right`/`write` and `wear`/`where`, 53 % of its words have a same-or-one-phoneme
twin, and its only guarantee is unique four-letter prefixes — which says nothing
about a phone line.

**The list does not have to be a power of two.** It is 1,296 because that was
36 × 36 on the square grid, where each word was one base-36 digit of x and one
of y. H3 does not need that, but 1,311 is the ceiling on A1–B2 graded
vocabulary, so 1,296 is close to everything the easy band has to give.
BIP-39's 2,048 would carry more per word, but the largest phonetically clean
list inside the top 10,000 words of English is 976, and 2,048 needs roughly the
top 30,000.

## Tools

```
pip install -r tools/gridcode/requirements.txt   # h3, the Python bindings
npm ci --prefix tools/gridcode                   # h3-js, for the cross-check
python3 tools/gridcode/test_bip39grid.py      # the scheme: round trip, checksums, uniqueness
node    tools/gridcode/check-demo.mjs         # the demo's JS against the Python reference
python3 tools/gridcode/build_fixture.py       # regenerate the cross-check fixture
```

The last two exist because the codec is implemented twice — once in Python as
the reference, once in JavaScript inside the demo. Both sit on the same H3 core,
4.5.0, and the cross-check runs on every push so they cannot drift apart.

## Licence

MIT — see [LICENSE](LICENSE).
