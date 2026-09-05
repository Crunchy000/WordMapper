# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

## Demos

### `demos/uk-word-grid.html`

An interactive proof-of-concept that addresses locations in the United Kingdom
with a sequence of three words.

- The UK bounding box (49.85–60.90 °N, −8.65–1.80 °E) is divided into a grid.
- Cells are numbered along a [generalised Hilbert curve][gilbert] so that
  consecutive words correspond to spatially adjacent cells, and nearby places
  tend to share an address prefix.
- Each cell index maps to a word from the 1,633-word Tirosh mnemonic list
  (chosen to avoid soundalikes).
- Clicking a cell subdivides it with the same grid, so each additional word
  refines the address: `word.word.word`.

Open the file directly in a browser — no build step. It loads Leaflet and
OpenStreetMap tiles from a CDN, so it needs network access.

See [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) for known
issues and proposed improvements.

[gilbert]: https://github.com/jakubcerveny/gilbert

## Licence

MIT — see [LICENSE](LICENSE).
