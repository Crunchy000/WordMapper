# WordMapper

Experiments in encoding geographic coordinates as short, memorable word sequences.

**Live: <https://crunchy000.github.io/WordMapper/>**

## Five words, one 3-metre H3 hexagon

**Five everyday words name any place on earth to one hexagon of Uber's [H3]
grid at resolution 14**: 1.5 m on an edge, about 2.7 m across and 6.3 m² on
average. That is smaller than a what3words square (9 m²). A misheard word is
refused about **98 %** of the time. Nothing else is needed to decode them:
there is no reference point, no network call and no database.

```
sufficient.twist.recommend.apron.paradox      <- Big Ben
```

[`demos/word-grid.html`](demos/word-grid.html) is the scheme live and bare.
Click anywhere and the address appears with its hexagon drawn, or type five
words to go to them.

### Why five words and resolution 14

| Words | Combinations | H3 resolution | Hexagon | Check |
|---|---|---|---|---|
| 3 | 2.18 billion | res 8 | 531 m edge, 0.74 km² | 1 in 3 |
| 4 | 2.82 trillion | res 12 | 10.8 m edge, 307 m² | none |
| **5** | **3.66 quadrillion** | **res 14** | **1.5 m edge, 6.3 m²** | **1 in 44** |
| 5 | 3.66 quadrillion | res 15 | 0.6 m edge, 0.9 m² | 1 in 6 |

Three words was a whole village and four a house. Five words fit H3's finest
level, resolution 15, but only six times over, which leaves a 1-in-6 check.
Resolution 14 fits 44 times over: 122 × 7¹⁴ ≈ 82.7 trillion slots in 1,296⁵.
That 44 becomes the check, and 1.5 m edges are already finer than anyone can
point.

### How a cell becomes five words

The five words are one number, not one word per H3 level. A word can't hold
four of H3's base-7 digits (7⁴ = 2,401 > 1,296), so a word-per-level layout
would fall short of resolution 14.

```
ordinal = base cell × 7¹⁴ + its fourteen digits read in base 7
value   = ordinal × 44 + check         check = sha256(cell) mod 44
number  = scramble(value)              a keyed permutation of all 1,296⁵
words   = number in base 1,296
```

**The check catches most mistakes, and the scramble makes the rest obvious.** A
misheard word is refused when it fails the 1-in-44 check, lands past the last
value that names a cell, or lands on a pentagon's missing child: about
**97.7 %** of the time. The few that pass decode to a real place. The scramble
sends those somewhere unrelated: in the tests the median miss is about
**9,700 km**, and none landed within 100 km. Without it, a wrong last word would
land next door.

The scramble is a six-round Feistel network. 1,296⁵ is 6²⁰, exactly
60,466,176², so it splits into two equal halves even with an odd number of
words, and it is a bijection on every five-word combination with nothing left
over. Every value is below 2⁵³, so the demo's JavaScript does it exactly in
ordinary numbers.

**What it costs:**
- Neighbouring places share no words.
- There is no shorter form: four words do not name a bigger area, and there is
  no dropping words against a nearby reference.
- H3 is not equal-area, so cells vary in size by about 2:1 across the globe.

### What came before

It got here by way of four words to a 307 m² hexagon, three words to a
0.74 km² one, and six words with a word-per-level layout. Before that it was a
square grid on a
cylindrical equal-area projection, whose cells were square only at 55.65°. There
was also an online mode that issued random three-word codes from a database,
backed by a Cloudflare Worker. All of that is gone: five words, decoded
offline, is the scheme. The git history has the rest.

Open the demo file directly in a browser: no build step. It loads Leaflet,
h3-js and map tiles from a CDN, and once loaded the address is computed in the
page. SHA-256 is plain JavaScript rather than `crypto.subtle`, which is missing
outside a secure context.

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

- [`docs/grid-scheme.md`](docs/grid-scheme.md) — the scheme in full: why
  five words at resolution 14, how the cell is numbered, the check, the
  scramble, and what is verified.
- [`docs/coverage.md`](docs/coverage.md) — the square-root law relating area to
  resolution, and the word-list vs address-length trade. Written for an earlier,
  UK-only version of the scheme; the arithmetic still holds.
- [`docs/uk-word-grid-review.md`](docs/uk-word-grid-review.md) — a review of the
  original imported demo. Historical: that demo and its scheme are gone.

## Word list

**1,296 words, every one graded CEFR A1–B2** — the band a person can retrieve
under pressure, not merely recognise. Generated by [`tools/wordlist`](tools/wordlist)
from the 9,025 graded headwords of the Oxford 5000 and the English Vocabulary
Profile, minus names, places, offensive and vulgar words, inflections of other
words, words spelled two ways — and then everything confusable or sound-alike.
**Zero homophones, zero pairs one articulatory feature apart, zero pairs within
one phoneme error.**

BIP-39 was here first and was the wrong list. It is designed to be *typed and
checksummed*, not spoken: it contains `pair`/`pear`, `peace`/`piece`,
`right`/`write` and `wear`/`where`, 53 % of its words have a same-or-one-phoneme
twin, and its only guarantee is unique four-letter prefixes — which says nothing
about a phone line.

**The list size sets the resolution.** 1,311 is the ceiling on A1–B2 graded
vocabulary, so 1,296 is close to everything the easy band has to give. It is
why four words stopped at a 307 m² hexagon: resolution 13 at four words would
need a list of about 1,850. BIP-39's 2,048 would reach it, but the largest phonetically clean
list inside the top 10,000 words of English is 976, and 2,048 needs roughly the
top 30,000.

## Tools

```
pip install -r tools/gridcode/requirements.txt   # h3, the Python bindings
npm ci --prefix tools/gridcode                   # h3-js, for the cross-check
python3 tools/gridcode/test_bip39grid.py      # the scheme: round trip, scramble, wrong words
node    tools/gridcode/check-demo.mjs         # the demo's JS against the Python reference
python3 tools/gridcode/build_fixture.py       # regenerate the cross-check fixture
```

The last two exist because the codec is implemented twice — once in Python as
the reference, once in JavaScript inside the demo. Both sit on the same H3 core,
4.5.0, and the cross-check runs on every push so they cannot drift apart.

## Licence

MIT — see [LICENSE](LICENSE).

[H3]: https://h3geo.org/
