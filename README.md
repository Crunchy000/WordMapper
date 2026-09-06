# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live. Click anywhere and watch the address grow a word at a time,
each row adding one word and shrinking the box. Click a row to pick a length,
or resolve an address of any length back to a point.

- An address is a **prefix of a longer address**: 2 words for a street, 3 for a
  building, 4 for a doorstep. The words already said never change.
- The root is a **fixed box** over the UK and Ireland, not a repeating tile, so
  an address is unambiguous at every length and **no position hint is needed**.
- The [BIP-39][bip39] English list: 2,048 words, exactly 11 bits each.
- The box is the **limit of coverage**. Outside it there is no address, and the
  codec refuses rather than inventing one — an invented address would resolve
  to a real place inside the box and pass its checksum. See
  [`docs/grid-scheme.md`](docs/grid-scheme.md#outside-the-box) for what a wider
  box would cost.

| Words | Big Ben | Area |
|---|---|---|
| 2 | `plug.curtain` | 486 m |
| 3 | `plug.curtain.elder` | 10.7 m |
| 4 | `plug.curtain.elder.script` | 2.69 m, and verified |

The fourth word does two jobs: four of its bits refine the position and seven
carry a checksum, so it lands at 2.69 m *and* rejects a wrong word 99.2 % of the
time. what3words is 3 m with no checksum. Four words is terminal — a fifth would
have to reinterpret those bits. See [`docs/grid-scheme.md`](docs/grid-scheme.md).

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

- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — a review of the
  original imported demo. Historical: that demo and its scheme are gone.
- [`docs/coverage.md`](docs/coverage.md) — how far the scheme stretches: the
  Ireland extension, what global coverage would cost, and the word-list vs
  address-length trade.
- [`docs/grid-scheme.md`](docs/grid-scheme.md) — the current scheme: truncatable
  addresses over a fixed box, the interleaving pitfall that breaks the prefix
  property, and why a checksum cannot live at every length.

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
