# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## One grid

**Six everyday words name any point on earth to 2.99 m**, and a wrong one is
caught 99.9988 % of the time. That is the whole scheme: one grid, one address
for a place, one length, no scope to choose and nothing to switch.

**The sixth word is pure checksum.** It moves the position not at all: five
words already reach 2.99 m, and the sixth exists only to take a misheard word
from 1-in-64 undetected to 1-in-82,944.

**And six words is what you always say.** There is no country to consult, no
region to search, nothing to shorten against — see *There is nothing to shorten
against*, below.

There used to be regional boxes — the same grid mechanism over a smaller
rectangle, reaching four words over Britain and Ireland, and four over
Australia. They are gone, for three reasons that stack up.

**A box has to be a rectangle, and most of the world cannot be boxed without
swallowing a neighbour.** Africa and Europe interleave across the Mediterranean:
Tunisia reaches further north than the southern tip of Spain, so no horizontal
line separates them and any pair of boxes there overlaps. Europe was the smaller
box, so it won the overlap, and Tunis and Algiers resolved as "Europe". Australia
*could* be boxed cleanly, but only by cutting at 12° S and giving up Cape York,
the Tiwi Islands and the Torres Strait — because Papua New Guinea reaches
11.63° S and Indonesia 10.91° S, both further south than Australia's own northern
tip at 10.05° S.

**A box was coarser than the grid it stood in for.** Four words over Britain was
2.66 m; six words anywhere is 2.99 m and checked. The continental boxes
were worse still — Asia came out at 31.6 m.

**And a box gave a place a second address.** Two addresses for one spot is a
liability whatever the resolution, and it needed a scope tag bound into every
checksum to keep them from cross-verifying, which was still ambiguous 0.8 % of
the time at two boxes and 4.6 % at seven.

What a box was really selling was the **leading word** — and something else
supplies that without a rectangle being drawn by hand. See *A region will do
instead of a point*, below.

## Drop trailing words: coarser, needs no context

Each word narrows the area, and the words already said never change — every
address is a prefix of a longer one.

| Words | Big Ben | Cell | Checked |
|---|---|---|---|
| 1 | `kilo` | 627 km square | — |
| 2 | `kilo.waitress` | 17.4 km square | — |
| 3 | `kilo.waitress.maintain` | 484 m square | — |
| 4 | `kilo.waitress.maintain.table` | 26.89 m square | — |
| 5 | `kilo.waitress.maintain.table.glint` | **2.99 m square** | 1 in 64 |
| 6 | `kilo.waitress.maintain.table.glint.export` | **2.99 m square** | **1 in 82,944** |

The sixth word adds no precision, only certainty. Five words is the finest the
grid goes; the sixth is whether you want the strong check with it — and the
answer is yes, which is why six is the address.

Verification starts at five and not before, because **the checksum is over the
whole position**: no part of it is determined until the whole position is, and
four words stop one split short of full depth. Word four's spare values are dead
weight at that length. That is the price of landing on 2.99 m rather than 3.36 m
— see *Exactly three metres*, below.

Every cell at every length is exactly square, because both axes get the same
base-36 split at every word. Nothing arranges that; see *Why cells are square*.

## Drop leading words: same precision, fewer words, needs context

The leading words are the coarse ones, so whoever is listening can supply them
if they already know roughly where you are — exactly the way nobody dials +44
or an area code to a neighbour. Dropping *k* leading words leaves an ambiguity
of exactly one tile, and any accuracy better than half a tile pins it down.

| Words said | Written | Ambiguity | Usable if the listener knows your position within |
|---|---|---|---|
| 6 | `kilo.waitress.maintain.table.glint.export` | none | nothing at all |
| 5 | `.waitress.maintain.table.glint.export` | 627 km square | 314 km — which country |
| 4 | `.maintain.table.glint.export` | 17.4 km square | 8.7 km — which town |
| 3 | `.table.glint.export` | 484 m square | 242 m — which street |
| 2 | `.glint.export` | 26.89 m square | 13 m — you can already see them |

One word said is not on the table: the last word carries no position at all, so
on its own it leaves every cell on earth a candidate and there is nothing for a
reference to choose between.

The leading separator is the whole notation: it says the coarse words are
missing and context must supply them. That is the difference between an address
that is merely vague and one that is precise but local.

A local exchange settles on however few words its own accuracy allows, and the
same words become a global address the moment the context is written down.

### The checksum verifies the reconstruction

This is what makes shortening safe rather than a leap of faith. The checksum —
one of 82,944 values — covers the *whole* position, so when the missing coarse
words are filled in from a reference point, guessing the wrong tile fails the
check **99.9988 %** of the time, measured against references chosen at random
from anywhere on earth.

So a tail that resolves is almost certainly the place meant, and a reference
too far away to fill in the gap says so rather than answering confidently with
the wrong place.

### There is nothing to shorten against

`resolve_tail()` needs a nearby *point*, and takes the nearest tile that fits.
It tests exactly **one** candidate, so it costs no detection at all: one chance
to be fooled, the same as reading the whole address.

There used to be a second way — a *region*, usually a country, whose bounding box
a reverse geocoder would supply. It is gone, for reasons that stack up.

**It cost detection, which is the one thing worth protecting.** A misheard word
removes the true tile, so every candidate the box leaves is a fresh lottery
against the same checksum, and a wrong word was caught only `(1 − 1/CHECK)^k` of
the time rather than `1 − 1/CHECK`. Saying the sixth word costs less than that.

**It made the word count inconsistent.** The same country gave four words in one
place and five in another, depending on where the box edges fell against the
tile lattice — and the largest countries sat right on the cap, shortening most
of the time but not always. An address whose length you cannot predict is worse
than one that is always six words.

**And it needed a network call**, to a service with a rate limit and a usage
policy, for a scheme that otherwise works entirely offline.

What it bought was a single word. Six words, always, is the trade.
## How the grid falls over the UK

Luck rather than design, but useful luck: the whole UK bounding box spans only
**nine** distinct first words, and everywhere below is `kilo` except the
south-west corner.

```
London      kilo.waitress.maintain.table.glint.export
Manchester  kilo.sailor.unfold.fragment.microwave.astonish
Cardiff     kilo.poetry.machine.unpack.speculate.persuade
Plymouth    keystroke.obtain.beauty.athletic.tiptoe.courtesy
Edinburgh   kilo.professor.kilo.duration.dinosaur.gesture
Belfast     kilo.groom.pedantic.interval.expand.statistic
Dublin      kilo.freedom.innermost.picture.waterproof.historic
```

This is a curiosity rather than a feature: nothing shortens against it. It also
shows why it could not have been one. Plymouth falls on the other side of a
seam, so "we are both in Britain" does not predict the first word — the case the
checksum would have had to catch, and the reason a region search was never as
safe as it looked.

## Why the prefix property is free

Each word is one base-36 digit of x and one of y — `value = xdigit × 36 +
ydigit` — so a shorter address is literally the leading digits of a longer one.
The leading digits do not depend on the trailing ones, and there is nothing to
truncate.

This used to take care. The binary layout interleaved the two coordinates
**once at full precision** and truncated the bit string, because deriving the
interleave order per length does not work: at 11 bits a word, 33 bits splits the
axes 17/16 while 22 and 44 split evenly, and those are unrelated sequences
rather than prefixes of one another. Measured then, the three-word address came
out completely different from the two- and four-word ones, which agreed with
each other — so a spot check on 2 and 4 would have passed. Base-36 removes the
whole failure mode rather than testing around it.

The tests still check the property at every length over 1,500 points.

## Why cells are square

Both axes get the same split at every word, so a cell's aspect is the projected
frame's aspect, at every length, full stop. Make the frame square and every cell
is square.

The projection's standard parallel is chosen for exactly that. The frame's
aspect is `πK²`, so `K = 1/√π` gives 1 — a standard parallel of 55.654°.

| | 30° (before) | 55.654° (now) |
|---|---|---|
| frame | 34,667 × 14,713 km | 22,585 × 22,585 km |
| 6-word cell | 2.29 × 3.89 m — 1.70 : 1 | **2.99 m square** |
| 4-word cell | 20.6 × 35.1 m — 1.70 : 1 | **26.89 m square** |

Cell *area* is untouched — the projection is equal-area, so only the shape
changes and the resolution figures are the same.

This used to be much harder. Under the binary layout cell aspect was the frame's
aspect times `2**(yb − xb)` with `xb + yb` fixed by the length, so parity decided
what was reachable: an even bit count could only land on `frame × 4ᵏ` and an odd
one on `frame × 2 × 4ᵏ`. A square frame squared the even lengths and left the odd
ones at 2 : 1, and no frame could square both. It also needed a greedy bit order
— hand each bit to whichever axis is currently wider — to stop the frame's aspect
propagating into every cell. Base-36 needs none of it: there is no bit order,
no per-length axis split, and no odd lengths to lose.

## Every word can carry check, and the checks multiply

A word that splits its cell `r × r` keeps `r²` of its 1,296 values for position
and has `1296/r²` left over. So `SPLITS` fixes the resolution and the strength
of the checksum together:

```
SPLITS = [36, 36, 36, 36, 3, 1]
CHECKS = [ 1,  1,  1,  4,  16, 1296]      CHECK = 82,944
```

Words one to three split 36 × 36 and have nothing to spare. Word four splits
18 × 18 and word five 9 × 9, each keeping a little back. **Word six splits
1 × 1: it moves the position not at all and is nothing but check.**

That is why the sixth word is free of any cost in resolution, and why it is
worth 1,296× rather than merely more. Only the *product* of the splits sets the
cell size, so where the check lives across the words does not matter — but the
checks multiply, so spreading them is how the check gets bigger than one word.

The check digits are assigned **least significant first**, so each length's
check modulus divides the next one's: a shorter address is verified more weakly
rather than *differently*, and a longer one only ever strengthens it. Five words
are checked at 1 in 64, six at the whole 82,944.

### Exactly three metres

Word five's refinement has to divide 36, so on its own it jumps 3 → 4 → 6 and
the cell jumps 4.48 → 3.36 → 2.24 m, stepping over 3 m entirely. Landing on it
means taking the last factor of two out of word **four** as well:
36 × 36 × 36 × 18 × 9 = 7,558,272 divisions per axis, or 2.99 m.

That is what costs the four-word length, which coarsens from 13.45 m to 26.89 m
— and word four's spare values go to the checksum, which a four-word address
cannot verify, because the checksum is over the whole position. Dead weight at
that length, and the honest price of the round number.

### What the fifth word could have spent instead

Holding words one to four fixed, word five's split is the whole dial: it sets
the cell size and, because the checks multiply out to `1296⁶ / divisions²`, the
strength of the check at the same time. Every divisor of 36 is available:

| Word 5 splits | Cell | CHECK | Wrong word caught |
|---|---|---|---|
| 1 × 1 | 26.89 m | 6,718,464 | 99.999985 % |
| 2 × 2 | 13.45 m | 1,679,616 | 99.99994 % |
| 4 × 4 | 6.72 m | 419,904 | 99.99976 % |
| 6 × 6 | 4.48 m | 186,624 | 99.99946 % |
| **9 × 9** | **2.99 m** | **82,944** | **99.99879 %** |
| 12 × 12 | 2.24 m | 46,656 | 99.99786 % |
| 36 × 36 | 0.75 m | 5,184 | 99.98071 % |

Shipped at **9 × 9**, for 2.99 m. Every row is a straight trade of metres
against certainty, and there is no free lunch anywhere on it: halving the cell
quarters the check. For comparison, what3words is 3 m with no checksum at all —
this is the same resolution *and* verified to one part in 82,944.

A checksum genuinely cannot live at *every* length: it would have to occupy the
values the next word needs for position. Reserving 144 of a word's 1,296 values
at every length would take 2 words from 17 km to 209 km. Putting it in the last
word instead costs nothing at the shorter lengths, which are simply unverified.

**Six words is terminal.** A seventh would have nothing left to do: the sixth
already spends its entire word on check, so a seventh could only add position
the grid does not need or a second check symbol — and two check symbols is a
different design, one that *corrects* a wrong word rather than detecting it.
That is worth having and is not this.

The checksum covers the *whole* position, which is what makes both kinds of
shortening safe: a reconstruction that guesses wrong fails the check, whether
the guess came from a reference point or from a box search.

## The word list

1,296 words, every one graded **CEFR A1–B2** — the band a person can retrieve
under pressure, not merely recognise. 36 × 36, so each word is one base-36 digit
of x and one of y. Generated by `tools/wordlist` from the 9,025
graded headwords of the Oxford 5000 and the English Vocabulary Profile, minus
names, places, offensive and vulgar words, inflections of other words, words
spelled two ways, and then everything confusable or sound-alike. **Zero
homophones, zero pairs one articulatory feature apart, zero pairs within one
phoneme error.**

[BIP-39][bip39] was here first and was the wrong list for this. It is designed
to be *typed and checksummed*: it holds `pair`/`pear`, `peace`/`piece`,
`right`/`write` and `wear`/`where`, 53 % of its words have a same-or-one-phoneme
twin, and its only guarantee is unique four-letter prefixes, which says nothing
about a phone line.

**The list does not have to be a power of two**, and dropping that assumption is
what pays for the resolution. Binary forced 1,024 words and a 10.8 m cell;
36 × 36 is 1,296 words and 2.99 m at six, for a stronger
check than the 8 bits 1,024 could spare. 1,311 is the ceiling on A1–B2 graded
vocabulary, so 1,296 is close to everything the easy band has to give.

BIP-39's 2,048 would carry more per word, but not from words anyone can say
under pressure: the largest phonetically clean list inside the top 10,000 words
of English is 976, and 2,048 needs roughly the top 30,000.

## Projection

Lambert cylindrical equal-area, standard parallel 55.654°. Area-true, so every
cell at a given length has the same area anywhere on earth.

Shape is not preserved. Cells stretch with latitude, so a five-word cell that is
2.99 m square in the projection is the same area but much taller on the ground
near the poles — up to about 100 m at extreme latitude. The tests measure
round-trip error in the projection for that reason: ground distance is the wrong
ruler for a claim about cells.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

Every point on earth encodes, poles and both sides of the antimeridian
included; every address is a prefix of the next longer one; round trip inside
one cell diagonal at every length; no repeats at 2 and 3 words; dropping
leading words and filling them back in from a reference inside the tile
reconstructs exactly; a reference too far away is caught 99.9988 %; a wrong word
is rejected 99.9988 %; every cell exactly square at every length. An index is
never negative and never past the end — the clamp is at both ends, since an
unclamped negative would mint a plausible address for the wrong place.

**The check at every length** — verification starts exactly where the position
reaches full depth and not before, the full address is checked to one in
`CHECK`, each length's check modulus divides the next one's, and check digits
round-trip. And **no box search survives**: the test asserts that no function
with `box` in its name, and neither `MAX_CANDIDATES` nor `FLOOR`, is left in the
module at all.

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift: the
splits, the per-word check budget, the box, encodings at every length,
truncation, checksums, tail resolution across the antimeridian, hopeless
references, check-digit round-trips, and address parsing. It also asserts that
the demo carries no `candidatesInBox`, `shortestInBox`, `decodeInBox`,
`MAX_CANDIDATES` or `countryAt` — a stray copy in one port would be a silent
divergence.

Both run in CI on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
