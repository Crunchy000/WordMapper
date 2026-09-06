# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live. Click anywhere on earth and watch the address grow a word at a
time, each row adding one word and shrinking the box. Click a row to pick a
length, or resolve an address back to a point.

- **One global grid.** Five [BIP-39][bip39] words name any point on earth to
  1.35 m. No prefix, no registry, no agreement about borders.
- An address shortens **two ways**. Drop **trailing** words for a coarser
  address that still needs no context. Drop **leading** words to keep full
  precision with fewer words, when whoever is listening already knows roughly
  where you are.
- The **checksum verifies the reconstruction**, so filling in dropped leading
  words from a reference point is safe: the wrong tile fails the check 99.2 % of
  the time rather than resolving quietly to the wrong place.

| Words | Big Ben | Cell |
|---|---|---|
| 3 | `leg.tunnel.slam` | 264 × 225 m |
| 4 | `leg.tunnel.slam.subway` | 4.1 × 7.0 m |
| 5 | `leg.tunnel.slam.subway.gown` | 1.03 × 1.75 m, and verified |

Shortened locally, with a leading `.` marking the missing coarse words:

| Words said | Written | Usable if the listener knows your position within |
|---|---|---|
| 4 | `.tunnel.slam.subway.gown` | 230 km — which country |
| 3 | `.slam.subway.gown` | 4.2 km — which town |
| 2 | `.subway.gown` | 112 m — which street |

It falls conveniently over the UK: the whole country spans only six distinct
first words, and most of Great Britain is `leg`. So a UK conversation drops the
first word almost for free. Near a seam it is not free — Edinburgh is `legal`,
Belfast is `left` — which is exactly what the checksum is there to catch.

The fifth word does two jobs: four of its bits refine the position and seven
carry a checksum, so it lands at 1.35 m *and* rejects a wrong word 99.2 % of the
time. what3words is 3 m with no checksum. Five words is terminal — a sixth would
have to reinterpret those bits. See
[`docs/grid-scheme.md`](docs/grid-scheme.md).

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
