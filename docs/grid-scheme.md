# A global word grid, on H3

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `pip install -r tools/gridcode/requirements.txt` and
`npm ci --prefix tools/gridcode`.

## One grid, and it is H3

**Six everyday words name any point on earth to one hexagon of Uber's [H3]
grid at resolution 14** — about 2.7 m across its flats and 3.1 m corner to
corner, 6.3 m² on average — and a misheard word is caught at least
**99.9945 %** of the time (1 in 18,252).

```
attempt.clean.      Big Ben
kangaroo.professor.
retina.menu
```

One grid, one address for a place, one length, no scope to choose and nothing to
switch. Six words is what you always say.

### Why hexagons, and why H3

The grid used to be squares on a Lambert cylindrical equal-area projection. The
squares were square *in the projection*, and on the ground only at the standard
parallel, 55.65°:

| latitude | old 2.99 m cell on the ground | farthest point from its centre |
|---|---|---|
| 0° | 1.7 × 5.3 m | 2.78 m |
| 55.65° | 3.0 × 3.0 m | 2.11 m |
| 80° | 9.7 × 0.9 m | 4.88 m |

Shape distortion swamped anything a better cell shape could buy, so moving to
hexagons on the same map would have achieved little. H3 fixes the map as well:
it lays hexagons on an icosahedron, so a cell is close to a regular hexagon
everywhere. Every neighbour is the same distance away, there are no diagonals,
and a point is never more than one edge length — 1.55 m on average — from the
centre of its cell.

The price is area. H3 is not equal-area: resolution-14 cells run from about
3.8 m² to 7.6 m² across the globe. Shape was the point, and shape is what H3
keeps.

## The address is H3's own hierarchy

A resolution-14 H3 cell is a **base cell** (one of 122) and **fourteen base-7
digits**, each choosing one of a cell's seven children. Each word carries a
whole number of those digits plus a digit of checksum —
`value = position × check + check digit`:

| Word | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| H3 digits | base cell + 1 | 3 | 3 | 3 | 2 | 2 |
| Positions | 854 | 343 | 343 | 343 | 49 | 49 |
| Check | 1 | 3 | 3 | 3 | 26 | 26 |
| Reaches resolution | 1 | 4 | 7 | 10 | 12 | 14 |

The checks multiply: `3 × 3 × 3 × 26 × 26 = 18,252`.

**Base 7 does not pack evenly into 1,296.** 7⁴ = 2,401 does not fit, so three
digits is the most a word can hold, and 343 × 3 uses 1,029 of its 1,296 values.
The values no position uses are not wasted. A misheard word that lands on one is
refused before the checksum runs, as is one that lands on a pentagon's missing
child. Measured detection is therefore a little *better* than 1 − 1/18,252.

**The checksum sits in the trailing words** because a tail, an address with its
leading words dropped, keeps only the check its own words carry (see below).
Words five and six each give up a digit they could hold, 49 positions instead of
343, for a check of 26. Spreading the checksum evenly would have given a
slightly bigger total (21,060), but a three-word tail would have kept only 1 in
234 of it.

### What the resolution cost

Six words always had a choice between metres and certainty, and on H3 it is
starker than it was on the square grid:

| Six words reach | Cell | CHECK | Wrong word caught |
|---|---|---|---|
| res 13 (sixth word pure check) | 44 m², 4.1 m edge | 104,976 | 99.99905 % |
| **res 14** | **6.3 m², 1.55 m edge** | **18,252** | **99.9945 %** |
| *old square grid* | *8.9 m², 2.99 m square* | *82,944* | *99.9988 %* |

Shipped at **resolution 14**. It is finer than the square grid everywhere, and
round. Against that, a misheard word slips through 1 time in 18,252 rather than
1 in 82,944. Resolution 13 would have kept a strong check, but a 44 m² cell is a
house rather than a doorstep.

## Drop trailing words: coarser, needs no context

An H3 cell's parent is the same index with its last digits removed, so **every
address is a prefix of a longer one by construction**:

| Words | Big Ben | Cell (average edge) | Checked |
|---|---|---|---|
| 1 | `attempt` | res 1 — 483 km | — |
| 2 | `attempt.clean` | res 4 — 26 km | — |
| 3 | `attempt.clean.kangaroo` | res 7 — 1.4 km | — |
| 4 | `attempt.clean.kangaroo.professor` | res 10 — 76 m | — |
| 5 | `attempt.clean.kangaroo.professor.retina` | res 12 — 10.8 m | — |
| 6 | `attempt.clean.kangaroo.professor.retina.menu` | **res 14 — 1.55 m** | **1 in 18,252** |

Only the full address is checked. The checksum is over the whole res-14 cell,
so no part of it is determined until all fourteen digits are.

**H3 nests approximately.** A coarse hexagon, as drawn, does not exactly contain
its seven children: the union of a cell's descendants is a slightly ragged
hexagon, close to the drawn one but not the same. So the point a five-word
address came from is always one of that cell's descendants, but not always
inside its drawn outline. It is always near the centre. The tests measure it at
every length: a point is never more than 1.1 times the cell's own circumradius
from the centre a shorter address decodes to.

## Drop leading words: same precision, fewer words, needs context

The leading words are the coarse ones, so whoever is listening can supply them
if they already know roughly where you are.

`resolve_tail()` takes the reference point's own cell at the resolution the
dropped words reached, and every cell within two rings of it. It appends the
digits that were said to each one, keeps the candidate whose centre is nearest
the reference, and tests **that one** against the checksum. It never searches,
so it costs no detection beyond what the said words carry.

| Words said | Written | Ambiguity (average edge) | Resolves from a reference within | Checked |
|---|---|---|---|---|
| 6 | `attempt.clean.kangaroo.professor.retina.menu` | none | anywhere | 1 in 18,252 |
| 5 | `.clean.kangaroo.professor.retina.menu` | res 1 — 483 km | ~120 km | 1 in 18,252 |
| 4 | `.kangaroo.professor.retina.menu` | res 4 — 26 km | 6.5 km | 1 in 6,084 |
| 3 | `.professor.retina.menu` | res 7 — 1.4 km | 560 m | 1 in 2,028 |
| 2 | `.retina.menu` | res 10 — 76 m | 30 m | 1 in 676 |
| 1 | `.menu` | res 12 — 10.8 m | 4 m | 1 in 26 |

The "within" column is what the tests guarantee. It is 0.4 of the average edge
for one to three words said, and a quarter of an edge for four and five. The
coarse lengths are weaker because of H3's base cells. Where two base cells meet,
their digits point in different directions, so a candidate across the seam can
land nearer the reference than the true one. That only matters when the dropped
cells are big. With five words said, only a base cell and one digit are dropped,
and a reference within a quarter of an edge resolves about 99.5 % of the time
rather than always. The tests hold it to 98 %.

The leading separator is the whole notation. It says the coarse words are
missing and context must supply them.

**A tail keeps only its own words' check.** The dropped words take their check
digits with them, which is why the checksum is weighted to the end. A reference
too far away to pick the right cell is caught 1 − 1/modulus of the time: 99.95 %
for three words said, and 99.995 % for five. A one-word tail is barely checked
at all, so treat it as a convenience between people who can already see each
other.

### There is nothing to shorten against

There used to be a second way to fill in leading words: a *region*, usually a
country, whose bounding box a reverse geocoder would supply. It is gone. Every
candidate the box left was a fresh lottery against the same checksum, it made the
word count unpredictable, and it needed a network call. A reference *point*
tests one candidate and costs nothing.

## The word list

1,296 words, every one graded **CEFR A1–B2** — the band a person can retrieve
under pressure, not merely recognise. Generated by `tools/wordlist` from the
9,025 graded headwords of the Oxford 5000 and the English Vocabulary Profile,
minus names, places, offensive and vulgar words, inflections of other words,
words spelled two ways, and then everything confusable or sound-alike. **Zero
homophones, zero pairs one articulatory feature apart, zero pairs within one
phoneme error.**

1,296 was chosen as 36 × 36 for the square grid, where each word was one base-36
digit of x and one of y. H3 does not need that, but 1,311 is the ceiling on
A1–B2 graded vocabulary, so 1,296 is still close to everything the easy band has
to give.

[BIP-39][bip39] was here first and was the wrong list. It is designed to be
*typed and checksummed*: it holds `pair`/`pear`, `peace`/`piece`,
`right`/`write` and `wear`/`where`, and 53 % of its words have a
same-or-one-phoneme twin.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

- **The layout.** No word holds more than the list, and words one to four could
  not hold another digit. The checks multiply to `CHECK`, each length's check
  divides the next one's, and check digits and H3 indexes round-trip.
- **The grid.** Every point on earth encodes, including the poles, both sides of
  the antimeridian and all twelve pentagons. Every address decodes to the cell
  it came from.
- **Truncation.** Every address is a prefix of the next longer one, and is the
  H3 parent of it. A point is within 1.1 cell radii of the centre at every
  length.
- **Tails.** They resolve from a reference within the distances above,
  including across the antimeridian. A full address needs no reference.
  Hopeless references are caught within a point of theory.
- **The checksum.** A wrong word is rejected at least 1 − 1/18,252 of the time,
  and a value no position uses is refused outright.

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift. It
compares the layout word by word, H3 cells, encodings at every length,
truncation, checksums, tails across the antimeridian, hopeless references and
address parsing. It also checks that the demo loads the same h3-js version that
is installed.

Both run in CI on every push.

[H3]: https://h3geo.org/
[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
