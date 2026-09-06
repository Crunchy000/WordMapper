# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live and deliberately bare: click anywhere in the UK and the address
sits on the map, nothing else. Three words plus a fourth set apart, because that
one does a different job — it refines the position *and* carries the checksum.

```
flower.era.slogan · quarter        Big Ben — 2.43 m, checked
```

- **Local** — four words over a box around the United Kingdom. This is what the
  demo shows.
- **Global** — five [BIP-39][bip39] words, anywhere on earth, 1.35 m. Built and
  tested, just not surfaced in the demo for now; one constant in the UI brings
  it back.
- The scope is **bound into the checksum**, so the two can never be silently
  confused, and a terminal-length address identifies itself.

Cells are square. The projection's standard parallel is chosen so the projected
world is exactly square (`K = 1/√π`, 55.654°), which makes the 5-word global cell
1.346 m square and Local's 4-word cell 2.51 × 2.36 m. Equal-area throughout, so
this changes shape and not resolution — see
[`docs/grid-scheme.md`](docs/grid-scheme.md).

An address also shortens **two ways**. Drop **trailing** words for a coarser
address that needs no context. Drop **leading** words to keep full precision
with fewer words, when whoever is listening already knows roughly where you are
— marked with a leading `.`, and the checksum verifies the reconstruction, so a
reference too far away is caught 99.2 % of the time rather than resolving
quietly to the wrong place.

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
