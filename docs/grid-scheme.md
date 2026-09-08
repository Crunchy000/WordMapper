# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## One grid

**Six everyday words name any point on earth to 4.48 m**, and a wrong one is caught 99.9995 % of the time, and that is the whole scheme.
There is one grid, one address for a place, no scope to choose and nothing to
switch.

**The sixth word is pure checksum.** It moves the position not at all: five
words already reach 4.48 m, and the sixth exists only to take a misheard word
from 1-in-144 undetected to 1-in-186,624. It is therefore *additive* — the first
five words are byte-identical to the five-word scheme this replaced, so an
address already written down is still valid, still checked at 1 in 144, and is
upgraded rather than replaced by appending its sixth word.

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
2.66 m; five words anywhere is 4.48 m, one word shorter. The continental boxes
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
| 4 | `kilo.waitress.maintain.studio` | 13.45 m square | — |
| 5 | `kilo.waitress.maintain.studio.scribble` | **4.48 m square** | 1 in 144 |
| 6 | `kilo.waitress.maintain.studio.scribble.critical` | **4.48 m square** | **1 in 186,624** |

The sixth word adds no precision, only certainty. Five words is the finest the
grid goes; the sixth is whether you want the strong check with it.

Every cell at every length is exactly square, because both axes get the same
base-36 split at every word. Nothing arranges that; see *Why cells are square*.

## Drop leading words: same precision, fewer words, needs context

The leading words are the coarse ones, so whoever is listening can supply them
if they already know roughly where you are — exactly the way nobody dials +44
or an area code to a neighbour. Dropping *k* leading words leaves an ambiguity
of exactly one tile, and any accuracy better than half a tile pins it down.

| Words said | Written | Ambiguity | Usable if the listener knows your position within |
|---|---|---|---|
| 6 | `kilo.waitress.maintain.studio.scribble.critical` | none | nothing at all |
| 5 | `.waitress.maintain.studio.scribble.critical` | 627 km square | 314 km — which country |
| 4 | `.maintain.studio.scribble.critical` | 17.4 km square | 8.7 km — which town |
| 3 | `.studio.scribble.critical` | 484 m square | 242 m — which street |
| 2 | `.scribble.critical` | 13.45 m square | 6.7 m — you can already see them |

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
one of 186,624 values — covers the *whole* position, so when the missing coarse
words are filled in from a reference point, guessing the wrong tile fails the
check **99.9995 %** of the time. Measured at 99.2 % against references chosen at
random from anywhere on earth.

So a tail that resolves is almost certainly the place meant, and a reference
too far away to fill in the gap says so rather than answering confidently with
the wrong place.

### A region will do instead of a point

`resolve_tail()` needs a nearby *point*, and takes the nearest tile that fits.
`candidates_in_box()` needs only a *region*, and lets the checksum choose: it
tries every tile in the region and keeps the ones that pass. A country is such a
region, and a reverse geocoder will hand you its bounding box along with its
name — so "in the UK" can stand in for a word the way "near here" does.

The two are the same information in different shapes. Both are a search window;
one is centred on a point, the other is a rectangle someone else drew.

**How many words a window buys is one number: how many candidate tiles it
holds.** Each *position* word is a base-36 digit on each axis, so one word fewer
is 1,296 times as many tiles, and the check leaves one in 186,624 standing. A
length works exactly when no *other* candidate survives — a Poisson zero at rate
`(tiles − 1)/186,624`. Over Britain:

| Said | Tiles in the box | Survive the check |
|---|---|---|
| 4 | 4,234 | 1 |
| 5 | 4 | 1 |
| 6 | 1 | 1 |

The middle row is where the sixth word pays for itself. Under a 144-value check
those same 4,234 tiles left about 30 survivors, so four words could not be read
back at all; now the true point is the only one standing.

Nothing about countries enters into it; a country is just a box someone else
drew, and its size is the whole story. Measured against the boxes Nominatim
returns:

| country | box | tiles in the window | said | wrong word caught |
|---|---|---|---|---|
| Luxembourg | 4,700 km² | 1.0 | **four** — two words bought | 100 % |
| Switzerland | 76,000 km² | 1.0 | **four** — two words bought | 99.8 % |
| Ireland | 193,000 km² | 1.0 | **four** — two words bought | 99.8 % |
| United Kingdom | 1.3 M km² | 3.6 | **five**, always | 100 % |
| France | 1.28 M km² | 3.7 | **five**, always | 100 % |
| Australia | 17.3 M km² | 45 | **five**, always | 100 % |
| United States | 159 M km² | 404 | **five**, always | 99.7 % |

**Every country on earth now buys a word, and the small ones buy two.** Under a
144-value check the cap was six candidates, which refused Australia and the
United States outright and left Britain shortening only 97 % of the time. The
sixth word moved the check three orders of magnitude and the cap with it, so a
country-sized window stopped being a hard problem.

**Shortening this way costs detection, and the cap is what bounds the cost.**
When a word is misheard the true tile no longer matches, so every candidate in
the window becomes a fresh lottery against the same checksum: a wrong word is
caught only `(1 − 1/CHECK)^k` of the time.

So the cap is **derived from the checksum** rather than written down — the most
candidates that still leave `FLOOR` of the detection standing. At `FLOOR = 0.995`
and a 186,624-value check that is **935 candidates**, against 6 when the check
was 144. The United States, at 404, sits comfortably inside it and still catches
99.7 %; under the old check the same window fell to 6 %, where nearly every
mishearing resolved *silently* to somewhere else in the country.

`shortest_in_box()` still refuses to buy a word above `MAX_CANDIDATES`, and
`decode_in_box()` still refuses to read one — but at this check strength no
country reaches it. What the cap now stops is the genuinely reckless case: a
window two words further back, where the same box holds tens of millions.

`resolve_tail()` has no such loss: it takes the single nearest tile to the
reference and tests that one candidate — one chance to be fooled rather than k —
so it stays at 99.9995 %. That asymmetry is the real difference between the two
ways of filling a dropped word back in, and it now costs far less than it did.

The tests assert the measured uniqueness against that Poisson prediction for
each box, and measure the false-survivor rate directly by searching with a
checksum that is deliberately *wrong* — counting the survivors of a real address
no longer measures anything, because at 186,624 the only thing that passes is
the true point.

**The grid does not depend on the country.** The window is used when an address
is *read*; it is not part of the address and nothing is bound to it. So a border
can move, a territory can change hands, and the words for a place are unchanged
— which is the property that makes this usable at all, since the alternative
(binding a country code into the address) would make every disputed border a
correctness problem for its neighbours too.

A wrong window therefore costs uniqueness, never correctness: the point simply
is not the only survivor, and the full address is said instead. Nominatim
reports an antimeridian country inside out (west > east), which reads as most of
the planet — a useless window, and a safe one.

## How the grid falls over the UK

Luck rather than design, but useful luck: the whole UK bounding box spans only
**nine** distinct first words, and everywhere below is `kilo` except the
south-west corner.

```
London      kilo.waitress.maintain.studio.scribble.critical
Manchester  kilo.sailor.unfold.fiction.visibly
Cardiff     kilo.poetry.machine.volunteer.obvious
Plymouth    keystroke.obtain.beauty.bedside.reproduce
Edinburgh   kilo.professor.kilo.drink.mutual
Belfast     kilo.groom.pedantic.inference.mischief
Dublin      kilo.freedom.innermost.plastic.sweat
```

So a British conversation drops the first word almost for free, and five words
reach anywhere in the country. It also shows the catch: Plymouth falls on the
other side of a seam, and near a seam the dropped word is not
predictable from "we are both in Britain". That is precisely the case the
checksum catches, rather than resolving quietly to the wrong place — and
precisely why the country box search is the more reliable of the two ways to
fill a dropped word back in, since it tries every candidate rather than
assuming the nearest.

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
| 5-word cell | 3.43 × 5.83 m — 1.70 : 1 | **4.48 m square** |
| 4-word cell | 10.3 × 17.5 m — 1.70 : 1 | **13.45 m square** |

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
CHECKS = [ 1,  1,  1,  1, 144, 1296]      CHECK = 186,624
```

Words one to four split 36 × 36 and have nothing to spare. Word five refines
3 × 3 and spends the other 144 values on check. **Word six splits 1 × 1: it
moves the position not at all and is nothing but check.**

That is why the sixth word is free of any cost in resolution, and why it is
worth 1,296× rather than merely more. Only the *product* of the splits sets the
cell size, so where the check lives across the words does not matter — but the
checks multiply, so spreading them is how the check gets bigger than one word.

The check digits are assigned **least significant first**, which is the whole of
the backwards compatibility: word five gets `checksum % 144`, exactly what it
carried when it was the last word. Big-endian would have moved word five and
invalidated every address in circulation. And 144 divides 186,624, so the
five-word check is a genuine *prefix* of the six-word one rather than a
different function that happens to sit near it.

### What the fifth word could have spent instead

A whole fifth word of position would reach 37 cm, finer than anyone needs, so it
splits only 3 × 3. The two multiply out to 1,296, and any square factorisation
is available:

| Refine | Check values | Cell | Wrong word caught |
|---|---|---|---|
| 1 | 1,296 | 13.45 m | 99.92 % |
| 2 | 324 | 6.72 m | 99.69 % |
| **3** | **144** | **4.48 m** | **99.9995 %** |
| 4 | 81 | 3.36 m | 98.77 % |
| 6 | 36 | 2.24 m | 97.22 % |

Shipped at **3 refine + 144 check**, which the sixth word then multiplies by
1,296. For comparison, what3words is 3 m with no checksum at all — this is
comparable *and* verified to one part in 186,624.

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
36 × 36 is 1,296 words and 4.48 m, for the same five words said and a stronger
check than the 8 bits 1,024 could spare. 1,311 is the ceiling on A1–B2 graded
vocabulary, so 1,296 is close to everything the easy band has to give.

BIP-39's 2,048 would carry more per word, but not from words anyone can say
under pressure: the largest phonetically clean list inside the top 10,000 words
of English is 976, and 2,048 needs roughly the top 30,000.

## Projection

Lambert cylindrical equal-area, standard parallel 55.654°. Area-true, so every
cell at a given length has the same area anywhere on earth.

Shape is not preserved. Cells stretch with latitude, so a five-word cell that is
4.48 m square in the projection is the same area but much taller on the ground
near the poles — up to about 100 m at extreme latitude. The tests measure
round-trip error in the projection for that reason: ground distance is the wrong
ruler for a claim about cells.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

Every point on earth encodes, poles and both sides of the antimeridian
included; every address is a prefix of the next longer one; round trip inside
one cell diagonal at every length; no repeats at 2 and 3 words; dropping
leading words and filling them back in from a reference inside the tile
reconstructs exactly; a reference too far away is caught 99.2 %; a wrong word
is rejected 99.2 % against a theoretical 99.9995 %; every cell exactly square at
every length. An index is never negative and never past the end — the clamp is
at both ends, since an unclamped negative would mint a plausible address for the
wrong place.

**Shortening against a country box** — the true point is never lost from the
search; uniqueness matches the Poisson law box by box; **no address is ever
shortened against a window over the cap**, and a window over it is refused
rather than answered from; a misheard word in a shortened address is still
caught over 93 % of the time, measured per country; the shortened form reads
back to the same cell; a box that excludes the point falls back to the full
address; an inside-out box costs words, not correctness; the address itself does
not depend on the box; a search too big to be worth running is refused rather
than run.

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift: the bit
order, the axis split, the box, encodings at every length, truncation,
checksums, tail resolution across the antimeridian, hopeless references, address
parsing, and the box search — which cells it looks at, how many survive the
check, and how short the address ends up.

Both run in CI on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
