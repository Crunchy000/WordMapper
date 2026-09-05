# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/uk-word-grid.html`

An interactive proof-of-concept that addresses locations in the UK and Ireland
with a sequence of three words.

- The bounding box (49.85–60.90 °N, −11.00–1.80 °E) is divided into a 53×53 grid.
- Cells are numbered along a [generalised Hilbert curve][gilbert] so that
  consecutive words correspond to spatially adjacent cells, and nearby places
  tend to share an address prefix.
- Each cell index maps to a word from [`data/wordlist-2809.json`](data/wordlist-2809.json)
  — 53², exactly one word per cell, so no ground is unaddressable.
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

**One-time setup:** Pages has to be switched on for the repository before the
first deploy can succeed — *Settings → Pages → Build and deployment → Source:
**GitHub Actions***. The workflow cannot do this itself; creating a Pages site
needs repo-admin rights, which the Actions token does not have. Until it is
done, the deploy step fails with `Get Pages site failed`. Once it is done,
re-run the workflow and it will publish.

## Docs

- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — known issues and
  proposed improvements.
- [`docs/coverage.md`](docs/coverage.md) — how far the scheme stretches: the
  Ireland extension, what global coverage would cost, and the word-list vs
  address-length trade.
- [`docs/wordlist.md`](docs/wordlist.md) — building a soundalike-free word list,
  and why phonetic distinctness caps three-word precision at about 6 m.

## Word list

Two lists, both built the same way and both exact squares so every grid cell gets
a word. No two entries in either are within one edit of each other in spelling
*or* pronunciation. The smaller is a strict subset of the larger.

| List | Words | Grid | 3-word cell | Weakest word |
|---|---|---|---|---|
| [`wordlist.json`](data/wordlist.json) | 1,681 | 41×41 | 14.45 m | known in 9 of 26 languages |
| [`wordlist-2809.json`](data/wordlist-2809.json) | 2,809 | 53×53 | 6.69 m | known in 1 of 26 languages |

The demo uses the larger one. The smaller trades precision for word quality —
see [`docs/wordlist.md`](docs/wordlist.md).

- `python3 tools/wordlist/build.py [--count N]` rebuilds either list from CMU
  pronunciations, WordNet and `wordfreq`. Use a perfect square for `N`.
  Dependencies are listed in the script's docstring.
- `python3 tools/wordlist/verify.py data/wordlist.json` checks all 1.4M pairs
  brute-force and exits non-zero on any collision.

Both still want a human read-through — see [`docs/wordlist.md`](docs/wordlist.md).

[gilbert]: https://github.com/jakubcerveny/gilbert

## Licence

MIT — see [LICENSE](LICENSE).
