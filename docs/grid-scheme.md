# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## Scopes

The same grid mechanism over a different box. **Two regional boxes at four
words, plus Global at five.** The scope follows the click — the demo never asks
you to pick one.

| scope | box | 4-word cell |
|---|---|---|
| Local — UK and Ireland | 0.97 M km² | **2.66 m** |
| Australia | 13.9 M km² | 10.07 m |
| *Global, 5 words* | *whole earth* | *1.35 m* |

### Why only two

**A box is a rectangle, and most continents cannot be boxed without swallowing
a neighbour.** Africa and Europe interleave across the Mediterranean — Tunisia
reaches further north than the southern tip of Spain — so no horizontal line
separates them, and any pair of boxes there overlaps. When both existed, Tunis
and Algiers resolved as "Europe", which is simply wrong.

The continental boxes were also coarse enough to be barely worth the word they
saved: Asia came out at 31.6 m, against Global's 1.35 m for one more word.
Merging them fixes the overlap but makes it worse still — Afro-Eurasia as a
single box is 41.6 m.

So the regions are the two that box cleanly, and Global covers everything else.

### Australia's box is cut at 12° S, and that is the point

Papua New Guinea reaches 11.63° S and Indonesia 10.91° S — **both further south
than Australia's own northern tip at 10.05° S.** So no cut keeps the whole
continent and excludes the neighbours; checked against Natural Earth coastlines
rather than guessed.

Stopping at 12° S catches **no other country's land at all**. It keeps 90 % of
Australia's coastline and every major city, Darwin (12.46° S) included. What it
gives up — Cape York's tip, the Tiwi Islands, the Torres Strait — falls back to
Global, which still works there.

### Choosing the scope

The smallest regional box containing the point, or Global where none does. The
boxes do not overlap each other, so this is only ever a choice between one
region and Global.

### Telling them apart

Each scope's tag is bound into its checksum, so an address minted in one box
cannot verify in another. With two regional boxes a four-word address is
accepted by more than one scope **0.8 %** of the time — measured at 1.0 %. That
is low enough that a four-word address nearly always identifies itself, which
was not true at seven boxes, where it was 4.6 %.

### Boxes are rectangles, not borders

Dublin is in Local by design. Boulogne comes along with it, because the box's
east edge is out in the Channel. Addresses resolve correctly regardless, since
encoding and decoding use the same box; a box is not a claim about anything.

## Drop trailing words: coarser, needs no context

Each word narrows the area, and the words already said never change — every
address is a prefix of a longer one.

| Words | Big Ben, Global | Cell | | Big Ben, UK | Cell |
|---|---|---|---|---|---|
| 1 | `leg` | 542 × 460 km | | `play` | 19.9 km |
| 2 | `leg.tunnel` | 8.5 × 14.4 km | | `play.cram` | 441 m |
| 3 | `leg.tunnel.slam` | 264 × 225 m | | `play.cram.side` | 9.7 m |
| 4 | `leg.tunnel.slam.subway` | 4.1 × 7.0 m | | `play.cram.side.someone` | **2.43 m, verified** |
| 5 | `leg.tunnel.slam.subway.gown` | **1.35 m, verified** | | — | — |

## Drop leading words: same precision, fewer words, needs context

The leading words are the coarse ones, so whoever is listening can supply them
if they already know roughly where you are — exactly the way nobody dials +44
or an area code to a neighbour. Dropping *k* leading words leaves an ambiguity
of exactly one tile, and any accuracy better than half a tile pins it down.

| Words said | Written | Ambiguity | Usable if the listener knows your position within |
|---|---|---|---|
| 5 | `leg.tunnel.slam.subway.gown` | none | nothing at all |
| 4 | `.tunnel.slam.subway.gown` | 542 × 460 km | 230 km — which country |
| 3 | `.slam.subway.gown` | 8.5 × 14.4 km | 4.2 km — which town |
| 2 | `.subway.gown` | 264 × 225 m | 112 m — which street |
| 1 | `.gown` | 4.1 × 7.0 m | 2 m — you can already see them |

The leading separator is the whole notation: it says the coarse words are
missing and context must supply them. That is the difference between an address
that is merely vague and one that is precise but local.

A local exchange settles on however few words its own accuracy allows, and the
same words become a global address the moment the context is written down.

### The checksum verifies the reconstruction

This is what makes shortening safe rather than a leap of faith. The 7 check
bits cover the *whole* position, so when the missing coarse words are filled in
from a reference point, guessing the wrong tile fails the check **99.2 %** of
the time. Measured at 99.4 % against references chosen at random from anywhere
on earth.

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

**It buys exactly one word.** Seven check bits kill 127 candidates in 128, so
the window has to be down to a few hundred tiles before one survivor is likely.
Over Britain:

| Said | Tiles in the box | Survive the check |
|---|---|---|
| 3 | ~10,600 | ~80 |
| 4 | 6 | 1 |
| 5 | 1 | 1 |

Measured over real Nominatim boxes, five words become four always in
Switzerland and Ireland, 98 % of the time in the UK, 92 % in France and 70 % in
Australia. Three words is out of reach everywhere.

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

## Telling them apart

A terminal-length address carries a checksum over its own scope, so it
identifies itself: four words that pass the UK check are a UK address, five
that pass the global check are a global one. `decode_auto` does this without
being told.

**The two directions are not symmetrical, and this is the one sharp edge.** A
global *prefix* carries no checksum at all — that is the whole point of a short
form. So:

- A four-word global prefix read as UK fails the UK checksum 99.2 % of the time
  and is caught.
- A four-word UK address read as a global prefix would decode **silently** to
  a different place, because nothing checks a prefix.

So the UK reading is always tried first. The tests assert that order, and the
cross-check asserts both ports agree on it.

## Outside the UK box

The UK box is a **rectangle, not a border**. Dublin sits inside it and gets a
UK-mode address, which resolves correctly because encoding and decoding use the
same box — it is simply not a claim about jurisdiction.

Outside the box there is no UK address, and `encode` refuses rather than
inventing one: decode maps onto the box and nowhere else, so an outside point
would alias onto an address belonging to a real place inside it and pass its own
checksum. Every such point still has a global address.

### How the global grid falls over the UK

Luck rather than design, but useful luck: the whole UK bounding box spans only
**six** distinct first words — `lecture`, `left`, `leg`, `legal`, `present`,
`pretty` — and most of Great Britain is `leg`.

```
London      leg.tunnel.slab.company.confirm
Manchester  leg.stable.divert.copper.trophy
Cardiff     leg.hamster.spring.steel.hat
Plymouth    leg.country.initial.monster.picnic
Edinburgh   legal.december.exist.frozen.mixture
Belfast     left.prevent.giraffe.pulse.unit
```

So a UK conversation drops the first word almost for free, and four words
reaches anywhere in the country. It also shows the catch: Edinburgh and Belfast
fall on the other side of a seam, and near a seam the dropped word is not
predictable from "we are both in Britain". That is precisely the case the
checksum catches rather than resolving quietly to the wrong place.

## Why the prefix property needs care

Coordinates are interleaved **once at full precision** and the resulting bit
string is truncated. Deriving the interleave order per length does not work, and
fails in a way that is easy to miss: 11 bits per word is odd, so 33 bits splits
the axes 17/16 while 22 and 44 split evenly. Those are unrelated sequences, not
prefixes of one another. Measured, the three-word address came out completely
different from the two- and four-word ones, which agreed with each other — so a
spot check on 2 and 4 would have passed.

The tests check this at every length over 1,500 points.

## Why cells are square

Cell aspect is the projected frame's aspect times `2**(yb - xb)`, and `xb + yb`
is fixed by the address length. So **parity decides which aspects are
reachable**: an even bit count can only land on `frame × 4ᵏ`, an odd one only on
`frame × 2 × 4ᵏ`.

The projection's standard parallel is therefore chosen to make the projected
world **exactly square**. Its aspect is `πK²`, so `K = 1/√π` gives 1 — a
standard parallel of 55.654°.

| | 30° (before) | 55.654° (now) |
|---|---|---|
| frame | 34,667 × 14,713 km | 22,585 × 22,585 km |
| 5-word cell | 1.03 × 1.75 m — 1.70 : 1 | **1.346 × 1.346 m — 1.00 : 1** |
| 4-word cell | 4.13 × 7.02 m — 1.70 : 1 | **5.385 m square** |
| Local's 4-word cell | 1.93 × 3.07 m — 1.59 : 1 | **2.51 × 2.36 m — 1.07 : 1** |

Cell *area* is untouched — the projection is equal-area, so only the shape
changes and the resolution figures are the same.

Both terminal lengths are even bit counts (48 global, 44 local), which is why
both land exactly square. The cost falls on the odd lengths, which go to 2 : 1 —
a 3-word global cell is 172 × 345 m rather than 264 × 225 m. No frame can square
both: one exponent is odd whenever the other is even. The best compromise that
squares *nothing* but evens everything out is a √2 frame (47.86°), which puts
every length at 1.414 : 1; squaring the lengths that people actually say is
worth more.

Within a box the bits are still handed to whichever axis is currently wider, so
a box with its own aspect — Local's is 1 : 1.9 — still comes out near square.

## The last word does two jobs

A whole fifth word of position would reach 8 cm, finer than anyone needs. So its
11 bits are split between refinement and checksum:

| Refine | Check | Global cell | UK cell | Wrong word caught |
|---|---|---|---|---|
| 3 | 8 | 1.90 m | 3.44 m | 99.61 % |
| **4** | **7** | **1.35 m** | **2.43 m** | **99.22 %** |
| 5 | 6 | 0.95 m | 1.72 m | 98.44 % |

Shipped at **4 refine + 7 check**. For comparison, what3words is 3 m with no
checksum at all — this is finer *and* verified.

A checksum genuinely cannot live at *every* length: its bits would sit exactly
where the next word's position bits must go. Reserving 8 bits at every length
would take 2 words from 11 km to 177 km. Putting it in the last word instead
costs nothing at the shorter lengths, which are simply unverified.

Each scope's terminal length is terminal for the same reason — a further word
would have to reinterpret the check bits. The checksum also covers the scope
tag, which is what keeps the two apart.

## The word list

[BIP-39][bip39] English: exactly 2,048 words, so exactly 11 bits each, with no
waste and no ambiguity about how many bits a word carries. Every word is 3–8
letters with a unique 4-letter prefix, which is a typing property rather than a
sound property — the list was designed for written seed phrases, not for being
read aloud over a bad line. The checksum is what covers that gap here.

## Projection

Lambert cylindrical equal-area, standard parallel 30°. Area-true, so every cell
at a given length has the same area anywhere on earth.

Shape is not preserved. Cells stretch with latitude, so a five-word cell that is
1.03 × 1.75 m in the tropics is the same area but much taller on the ground near
the poles — up to about 100 m at extreme latitude. The tests measure round-trip
error in the projection for that reason: ground distance is the wrong ruler for
a claim about cells.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

**Global** — every point on earth encodes, poles and both sides of the
antimeridian included; every address is a prefix of the next longer one; round
trip inside one cell diagonal at every length; no repeats at 2 and 3 words;
dropping leading words and filling them back in from a reference inside the
tile reconstructs exactly; a reference too far away is caught 99.4 %; a wrong
word is rejected 99.1 %; no cell worse than 1.7 : 1.

**UK** — every point in the box encodes; prefix property and round trip hold;
no repeats at 3 words; a coordinate outside the box is refused rather than
aliased, and those same points still have global addresses; a wrong word is
rejected 99.2 %. Dublin is inside the box and round trips, because the box is a
rectangle rather than a border.

**Both** — a UK address is *not* checked when read as a global prefix (asserted,
because it is the reason resolution order matters); `decode_auto` identifies
every UK address as UK and every five-word global address as global, and reports
a short address as unverified.

**Shortening against a country box** — the true point is never lost from the
search; the shortened form resolves back to the same cell; a box that excludes
the point falls back to the full address; an inside-out box costs words, not
correctness; the address itself does not depend on the box; survivors match the
1-in-128 checksum rate; a search too big to be worth running is refused rather
than run.

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift: both
scopes' encodings, truncation, checksums, the UK box and its refusals, tail
resolution across the antimeridian, hopeless references, both bit orders, the
scope-identification order, and address parsing. It also checks the second demo:
that `country-shorten.html` carries the *same* codec text and word list rather
than a drifted copy, and that its box search agrees with the reference on which
cells it looks at, how many survive the check, and how short the address ends
up.

Both run in CI on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
