# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live and deliberately bare: click anywhere on earth and the address
sits on the map, nothing else. **Six everyday words name any point to 2.99 m,
and catch a misheard one 99.9988 % of the time** — two words to a line, with the
last set apart because it does a different job: it moves the position not at all
and is nothing but checksum.

**One grid, one address for a place, one length.** There are no regional boxes
and no scope to switch — there used to be, around Britain and Ireland and around
Australia, and they are gone: a box has to be a rectangle, most of the world
cannot be boxed without swallowing a neighbour, and each one gave a place a
*second* address.

**And six words, always.** There is nothing to shorten against: no country to
consult, no region to search, and so no network call at all — the address is
drawn the instant you click.

```
kilo.waitress.
maintain.table.
glint.export     <- set apart: pure checksum
```

There used to be a country search, where a reverse geocoder's bounding box
bought the leading word. It is gone, for three reasons that stack up.

**It cost detection, which is the one thing worth protecting.** A misheard word
removes the true tile, so every candidate the box left was a fresh lottery
against the same checksum, and a wrong word was caught `(1 − 1/CHECK)^k` of the
time rather than `1 − 1/CHECK`. Saying the sixth word costs less than that.

**It made the word count inconsistent** — the same country giving four words in
one place and five in another, and the largest countries sitting right on the
cap, shortening most of the time but not always. An address whose length you
cannot predict is worse than one that is always six words.

**And it needed a network call**, to a rate-limited service with a usage policy,
for a scheme that otherwise works entirely offline.

**There is an online/offline toggle, and the online half is a mock.** Flip it and
the address becomes a three-word *short code* — two words of key, giving
1,679,616 of them, plus a check word computed the same way the address's own
checksum is, so a misheard code fails in the page before any lookup. Refresh
issues another. Nothing is stored anywhere and the page says so in red: it is a
sketch of what a lookup service would give you, drawn so the shape can be argued
about before anything is built.

The point of the toggle is the difference, not the word count. Six words *say
where you are* and decode with the network down. Three words are a row in a
database: fewer to read out, meaningless on their own, and dead the day that
database is. Roughly four syllables separate them — which is worth knowing
before paying for a service, since a short domain saves nearly thirty.

Dropping *trailing* words still works and needs no context at all — each word
narrows the area and the words already said never change. So does filling in
dropped *leading* words from a nearby reference point, which tests exactly one
candidate and so costs no detection at all. Only the region search is gone.

Cells are square at every length: both axes get the same split at every word, so
a cell's aspect is just the frame's, and the projection's standard parallel is
chosen to make the projected world exactly square (`K = 1/√π`, 55.654°).
Equal-area throughout, so this is shape, not resolution.

Open the file directly in a browser: no build step, and no secure-context
requirement, since SHA-256 is plain JavaScript rather than `crypto.subtle`. It
loads Leaflet and map tiles from a CDN, but the address itself is computed
entirely offline — nothing about it depends on the network.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md

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

- [`docs/grid-scheme.md`](docs/grid-scheme.md) — the scheme: both directions of
  shortening, why the checksum makes shortening safe, how many words a search
  why the prefix property is free in base-36 and was not in binary, why every
  word can carry check and the checks multiply, and why a checksum cannot be
  verified until the whole position is known.
- [`docs/coverage.md`](docs/coverage.md) — the square-root law relating area to
  resolution, and the word-list vs address-length trade. Written for an earlier,
  UK-only version of the scheme; the arithmetic still holds.
- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — a review of the
  original imported demo. Historical: that demo and its scheme are gone.

## Word list

**1,296 words, every one graded CEFR A1–B2** — the band a person can retrieve
under pressure, not merely recognise. 36 × 36, so each word is one base-36 digit
of x and one of y. Generated by [`tools/wordlist`](tools/wordlist)
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

**The list does not have to be a power of two**, and dropping that assumption is
what pays for the resolution. Binary forced 1,024 words and a 10.8 m cell;
36 × 36 is 1,296 words and 2.99 m at six words, checked to one part in 82,944.
1,311 is the ceiling on A1–B2 graded vocabulary, so 1,296 is
close to everything the easy band has to give — BIP-39's 2,048 would carry more
per word, but the largest phonetically clean list inside the top 10,000 words of
English is 976, and 2,048 needs roughly the top 30,000. Four and a half metres
is a parking space; a sixth word would reach 12 cm if a doorstep were ever
needed.

## Tools

```
npm install --prefix tools/gridcode
python3 tools/gridcode/test_bip39grid.py      # the scheme: round trip, checksums, uniqueness
node    tools/gridcode/check-demo.mjs         # the demo's JS against the Python reference
python3 tools/gridcode/build_fixture.py       # regenerate the cross-check fixture
```

The last two exist because the codec is implemented twice — once in Python as
the reference, once in JavaScript inside the demo. The cross-check runs on every
push so they cannot drift apart.

## Licence

MIT — see [LICENSE](LICENSE).
