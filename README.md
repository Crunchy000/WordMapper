# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live and deliberately bare: click anywhere on earth and the address
sits on the map, nothing else. **Five everyday words name any point to 4.48 m.** Four
plus a fourth set apart, because that one does a different job — it refines the
position *and* carries the checksum.

Then the address *shortens*. The five words are drawn immediately, with no
network involved; OpenStreetMap's reverse geocoder is asked which country the
click landed in, and the leading words the country can stand in for are shown
greyed rather than said:

```
kangaroo. wagon.machine.structure · science      Big Ben — United Kingdom, 4 said
kangaroo. forecast.inflation.platform · survey   Dublin — Ireland, 4 said
logic. overweight.atmosphere.popular · proposal  Luxembourg City — 4 said
fully.solvent.continue.year · breakfast          mid-Atlantic — no country, all 5
```

**One grid, one address for a place.** There are no regional boxes and no scope
to switch. There used to be — a box around Britain and Ireland, another around
Australia — and they are gone. A box has to be a rectangle, and most of the
world cannot be boxed without swallowing a neighbour: Africa and Europe
interleave across the Mediterranean, since Tunisia reaches further north than
southern Spain, so no horizontal line separates them. Each box also gave a place
a *second* address, and was coarser than the global grid it replaced (2.66 m
over the UK against 4.48 m, and one word shorter). A country supplies the leading word instead, and
does it without any rectangle being drawn by hand.

**A region is the other way to fill in a dropped leading word.** `resolve_tail()`
needs a nearby *point* and takes the nearest tile; `candidates_in_box()` needs
only a *region* and lets the checksum choose, trying every tile inside it.

**How many words a window buys is one number: how many candidate tiles it
holds.** Each word is a base-36 digit on each axis, so one fewer word is 1,296
times as many tiles, and the check leaves one in 144 standing — a length works
exactly when no *other* candidate survives, a Poisson zero at rate
`(tiles − 1)/144`. Nothing
about countries enters into it; a country is just a box someone else drew.

| country | box | tiles in the window | said | wrong word caught |
|---|---|---|---|---|
| Luxembourg | 4,700 km² | 1.0 | **four**, always | 100 % |
| Switzerland | 76,000 km² | 1.0 | **four**, always | 100 % |
| Ireland | 193,000 km² | 1.0 | **four**, always | 100 % |
| United Kingdom | 1.3 M km² | 3.6 | **four**, 97 % of the time | 98 % |
| France | 1.28 M km² | 3.5 | **four**, 98 % of the time | 96 % |
| Australia | 17.3 M km² | 45 | five — over the cap | — |
| United States | 159 M km² | 405 | five — over the cap | — |

**Shortening this way costs detection, and the cap is what bounds the cost.**
When a word is misheard the true tile no longer matches, so every candidate in
the window becomes a fresh lottery against the same checksum: a wrong word is
caught only `(143/144)^k` of the time. At k = 6 that is 95.9 %, against
99.31 % for the full address. Uncapped it was far worse — a window the size of
Australia holds ~45 candidates and falls to 73 %, where a quarter of mishearings
resolve *silently* to somewhere else in the country, which is the worst failure
there is because it looks like an answer.

So `shortest_in_box()` refuses to buy a word above `MAX_CANDIDATES = 6`, and
`decode_in_box()` refuses to read one. Australia and the United States say all
every word every time, rather than flapping depending on
where in the country you happened to be.

`resolve_tail()` has no such loss: it takes the single nearest tile to the
reference and tests that one candidate — one chance to be fooled rather than k —
so it stays at 99.31 %. That asymmetry is the real difference between the two
ways of filling a dropped word back in.

**The grid never moves.** The country is consulted when the address is *read*,
as a search window; it is not part of the address, and nothing is bound to it. A
border can be redrawn or a territory change hands and the words for a place are
unchanged — a wrong window costs uniqueness, never correctness. Nominatim
reports an antimeridian country inside out (west > east), which reads as most of
the planet: a useless window, and a safe one — you get every word.

Cells are square at every length: both axes get the same base-36 split at every
word, so a cell's aspect is just the frame's, and the projection's standard
parallel is chosen to make the projected world exactly square (`K = 1/√π`,
55.654°). Equal-area throughout, so this is shape, not resolution.

The geocoder is called at most once a second and cached by two-decimal-place
coordinates, per that service's usage policy. The demo works without it: if the
lookup fails, the five-word address is already on screen and stays there.

Open the file directly in a browser: no build step, and no secure-context
requirement, since SHA-256 is plain JavaScript rather than `crypto.subtle`. It
loads Leaflet and OpenStreetMap tiles from a CDN, so it needs network access.

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
  window buys, why the prefix property is free in base-36 and was not in
  binary, and why a checksum cannot live at every length.
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
36 × 36 is 1,296 words and 4.48 m, for the same five words said and a stronger
check besides. 1,445 is the ceiling on A1–B2 graded vocabulary, so 1,296 is
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
