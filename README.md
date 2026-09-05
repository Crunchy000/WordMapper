# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/uk-word-grid.html`

An interactive proof-of-concept that addresses locations in the UK and Ireland
with a sequence of three words.

- The bounding box (49.85–60.90 °N, −11.00–1.80 °E) is divided into a 41×41 grid.
- Cells are numbered along a [generalised Hilbert curve][gilbert] so that
  consecutive words correspond to spatially adjacent cells, and nearby places
  tend to share an address prefix.
- Each cell index maps to a word from the 1,633-word Tirosh mnemonic list
  (chosen to avoid soundalikes).
- Clicking a cell subdivides it with the same grid, so each additional word
  refines the address: `word.word.word`.

[Try it here](https://crunchy000.github.io/WordMapper/demos/uk-word-grid.html), or
open the file directly in a browser — no build step. It loads Leaflet and
OpenStreetMap tiles from a CDN, so it needs network access.

Run `node tools/grid-check.mjs` to verify the grid geometry; it reads the word
list, bounding box and Hilbert implementation out of the demo itself, so it
cannot drift from what the demo does. It exits non-zero if the grid stops being
square, continuous, or large enough for the word list, and runs on every push.

## Publishing

`index.html` and `demos/` are deployed to GitHub Pages by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to
`main`. Pull requests run the build and the grid check without deploying.

## Docs

- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — known issues and
  proposed improvements.
- [`docs/coverage.md`](docs/coverage.md) — how far the scheme stretches: the
  Ireland extension, what global coverage would cost, and the word-list vs
  address-length trade.

[gilbert]: https://github.com/jakubcerveny/gilbert

## Licence

MIT — see [LICENSE](LICENSE).
