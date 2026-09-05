# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Demos

### `demos/uk-word-grid.html`

An interactive proof-of-concept that addresses locations in the UK and Ireland
with a sequence of three words.

- The bounding box (49.85–60.90 °N, −11.00–1.80 °E) is divided into a 43×43 grid.
- Cells are numbered along a [generalised Hilbert curve][gilbert] so that
  consecutive words correspond to spatially adjacent cells, and nearby places
  tend to share an address prefix.
- Each cell index maps to a word from [`data/wordlist.json`](data/wordlist.json)
  — 43², exactly one word per cell, so no ground is unaddressable.
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
- [`docs/error-correction.md`](docs/error-correction.md) — addresses that repair
  themselves, and why four words suffice where the textbook bound wants five.

## Word list

[`data/wordlist.json`](data/wordlist.json) is **1,849 everyday words** — 43², so
every grid cell gets one. No two entries are within one edit of each other in
spelling *or* pronunciation, and none has a second accepted spelling.

The size is the square of a **prime** on purpose. A square grid keeps cell aspect
constant across levels, and p² with p prime also makes GF(1,849) a real finite
field, which the self-correcting codec needs. 46² = 2,116 would be a fine grid
and an impossible field.

- `python3 tools/wordlist/build.py [--count N]` rebuilds it from CMU
  pronunciations, WordNet and `wordfreq`. Use the square of a prime for `N`.
- `python3 tools/wordlist/verify.py data/wordlist.json` brute-forces every pair
  and exits non-zero on any collision.

It still wants a human read-through — see [`docs/wordlist.md`](docs/wordlist.md).

[gilbert]: https://github.com/jakubcerveny/gilbert

## Licence

MIT — see [LICENSE](LICENSE).
