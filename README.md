# WordMapper

WordMapper encodes geographic coordinates as five memorable BIP-39 words.
The grid is global and implemented directly in the browser; no Python reference
implementation or generated fixture is required.

## Demos

- [`demos/word-grid.html`](demos/word-grid.html) — the global five-word grid.
- [`demos/country-shorten.html`](demos/country-shorten.html) — uses a country
  bounding box as a search window and drops the leading word only when the
  remaining four words identify one cell. Otherwise all five words remain.

The address is always generated locally and immediately. OpenStreetMap is
consulted only by the country-shortening demo, and a failed lookup leaves the
full five-word address intact.

## Publishing

`index.html` and `demos/` are deployed to GitHub Pages by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) on pushes to
`main`. Pull requests assemble the same site without deploying.

## Word list

The demos embed the BIP-39 English list: 2,048 words at exactly 11 bits each.
It is used as published, with no filtering.

## Licence

MIT — see [`LICENSE`](LICENSE).
