# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/word-grid.html`

The scheme, live. Click for an address; the dashed box is the 70 km square that
is never transmitted, and the amber dots are the other places the same three
words land. Check bits are togglable, and addresses can be resolved back.

It carries its own JavaScript port of the codec, checked against the Python
reference by `node tools/gridcode/check-demo.mjs` on every push.

- The world is projected to an equal-area plane and tiled into 70 km squares.
- **The square is never transmitted.** An address names a point within one, and
  the listener supplies the square from knowing roughly where they are. That
  omission is 16.7 bits not spoken, and it is what buys the resolution.
- Three [BIP-39][bip39] words are 33 bits — 8,589,934,592 points in a square,
  a 0.755 m cell. Check bits come out of that: 8 bits gives a 12 m cell and
  catches 99.6 % of wrong words.

Open the file directly in a browser — no build step, and no secure-context
requirement, since the SHA-256 is implemented in plain JavaScript rather than
via `crypto.subtle`. It loads Leaflet and OpenStreetMap tiles from a CDN, so it
needs network access.

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
- [`docs/grid-scheme.md`](docs/grid-scheme.md) — the current scheme: a global
  70 km lattice whose square is never transmitted, BIP-39 words, and the honest
  version of the 35 km uniqueness claim.

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
