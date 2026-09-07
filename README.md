# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live and deliberately bare: click anywhere on earth and the address
sits on the map, nothing else. Three words plus a fourth set apart, because that
one does a different job — it refines the position *and* carries the checksum.

```
flush.edge.solution · sun            London — Local, 2.7 m
hello.match.sign · sponsor          Sydney — Australia, 10.1 m
staff.belt.agent.birth · tip        Paris  — Global, 1.35 m
```

**The scope follows the click.** Two regional boxes at four words, plus Global
at five for everywhere else:

| scope | box | 4-word cell |
|---|---|---|
| Local — UK and Ireland | 0.97 M km² | **2.66 m** |
| Australia | 13.9 M km² | 10.07 m |
| *Global — 5 words* | *whole earth* | *1.35 m* |

**Only two, because a box is a rectangle and most continents cannot be boxed
without swallowing a neighbour.** Africa and Europe interleave across the
Mediterranean — Tunisia reaches further north than southern Spain — so no
horizontal line separates them, and when both existed Tunis resolved as
"Europe". The continental boxes were also coarse enough to be barely worth the
word they saved (Asia came out at 31.6 m against Global's 1.35 m).

**Australia's box is cut at 12° S, and that is what makes it clean.** Papua New
Guinea reaches 11.63° S and Indonesia 10.91° S, both further south than
Australia's northern tip at 10.05° S, so no cut keeps the whole continent and
excludes the neighbours. Stopping at 12° S catches no other country's land at
all, keeps 90 % of the coastline and every major city including Darwin, and
gives up Cape York's tip, the Tiwi Islands and the Torres Strait to Global.

Each scope's tag is bound into its checksum, so an address minted in one box
cannot verify in another; with two regions a four-word address is ambiguous only
0.8 % of the time. See [`docs/grid-scheme.md`](docs/grid-scheme.md).

Cells are square: the projection's standard parallel is chosen so the projected
world is exactly square (`K = 1/√π`, 55.654°), which makes the 5-word global
cell 1.346 m square. Equal-area throughout, so this is shape, not resolution.

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
  shortening, why the checksum makes local shortening safe, the interleaving
  pitfall that breaks the prefix property, and why a checksum cannot live at
  every length.
- [`docs/coverage.md`](docs/coverage.md) — the square-root law relating area to
  resolution, and the word-list vs address-length trade. Written for an earlier,
  UK-only version of the scheme; the arithmetic still holds.
- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — a review of the
  original imported demo. Historical: that demo and its scheme are gone.

## Word list

The **[BIP-39 English list][bip39]** — exactly 2,048 words, so exactly 11 bits
each, with nothing wasted rounding to a word boundary. It is used as published,
with no filtering.

That is a deliberate trade. BIP-39 is designed to be *typed and checksummed*,
and its guarantee is unique four-letter prefixes, which says nothing about
sound: the list contains `pair`/`pear`, `peace`/`piece`, `right`/`write` and
`wear`/`where`, and 53 % of its words have a same-or-one-phoneme twin. So 89.6 %
of three-word addresses contain a word that one mishearing turns into a
different *valid* word. **The checksum is doing that work, not the word list** —
see [`docs/grid-scheme.md`](docs/grid-scheme.md).

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
