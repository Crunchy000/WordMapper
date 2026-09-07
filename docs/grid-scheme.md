# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## One grid

**Five words name any point on earth to 1.35 m**, and that is the whole scheme.
There is one grid, one address for a place, no scope to choose and nothing to
switch.

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
2.66 m; five words anywhere is 1.35 m. The continental boxes were worse still —
Asia came out at 31.6 m.

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

| Words | Big Ben | Cell |
|---|---|---|
| 1 | `leaf` | 353 × 706 km |
| 2 | `leaf.step` | 11.0 km square |
| 3 | `leaf.step.cruel` | 172 × 345 m |
| 4 | `leaf.step.cruel.tomato` | 5.38 m square |
| 5 | `leaf.step.cruel.tomato.unable` | **1.346 m square, verified** |

## Drop leading words: same precision, fewer words, needs context

The leading words are the coarse ones, so whoever is listening can supply them
if they already know roughly where you are — exactly the way nobody dials +44
or an area code to a neighbour. Dropping *k* leading words leaves an ambiguity
of exactly one tile, and any accuracy better than half a tile pins it down.

| Words said | Written | Ambiguity | Usable if the listener knows your position within |
|---|---|---|---|
| 5 | `leaf.step.cruel.tomato.unable` | none | nothing at all |
| 4 | `.step.cruel.tomato.unable` | 353 × 706 km | 176 km — which country |
| 3 | `.cruel.tomato.unable` | 11.0 km square | 5.5 km — which town |
| 2 | `.tomato.unable` | 172 × 345 m | 86 m — which street |
| 1 | `.unable` | 5.38 m square | 2.7 m — you can already see them |

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

**How many words a window buys is one number: how many candidate tiles it
holds.** Each word is 11 bits, so one word fewer is 2048 times as many tiles,
and the 7 check bits leave one in 128 standing. A length works exactly when no
*other* candidate survives — a Poisson zero at rate `(tiles − 1)/128`. Over
Britain:

| Said | Tiles in the box | Survive the check |
|---|---|---|
| 3 | ~10,600 | ~80 |
| 4 | 6 | 1 |
| 5 | 1 | 1 |

Nothing about countries enters into it; a country is just a box someone else
drew, and its size is the whole story. Measured against the boxes Nominatim
returns:

| country | box | tiles in the window | said | wrong word caught |
|---|---|---|---|---|
| Luxembourg | 4,700 km² | 1.0 | **four**, always | 100 % |
| Switzerland | 76,000 km² | 1.0 | **four**, always | 99 % |
| Ireland | 193,000 km² | 1.1 | **four**, always | 100 % |
| United Kingdom | 1.3 M km² | 5.5 | **four**, 97 % of the time | 96 % |
| France | 1.28 M km² | 5.5 | **four**, 97 % of the time | 94 % |
| Australia | 17.3 M km² | 71 | five — over the cap | — |
| United States | 159 M km² | 638 | five — over the cap | — |

**Shortening this way costs detection, and the cap is what bounds the cost.**
When a word is misheard the true tile no longer matches, so every candidate in
the window becomes a fresh lottery against the same 7 check bits: a wrong word
is caught only `(127/128)^k` of the time. At k = 6 that is 95.4 %, against
99.2 % for the full address. Uncapped it was far worse — a window the size of
Australia holds ~70 candidates and falls to 58 %, where a third of mishearings
resolve *silently* to somewhere else in the country, which is the worst failure
there is because it looks like an answer.

So `shortest_in_box()` refuses to buy a word above `MAX_CANDIDATES = 6`, and
`decode_in_box()` refuses to read one. Australia and the United States say all
five words every time, rather than flapping between four and five depending on
where in the country you happened to be.

`resolve_tail()` has no such loss: it takes the single nearest tile to the
reference and tests that one candidate — one chance to be fooled rather than k —
so it stays at 99.2 %. That asymmetry is the real difference between the two
ways of filling a dropped word back in.

The tests assert the measured uniqueness against that Poisson prediction for
each box, and the measured detection against the 93 % floor the cap implies —
rather than against numbers someone wrote down.

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
**six** distinct first words — `leader`, `leaf`, `learn`, `leave`, `staff`,
`stairs` — and most of Great Britain is `leaf`.

```
London      leaf.step.cube.bubble.explain
Manchester  leaf.toilet.garden.cable.voice
Cardiff     leaf.nerve.proud.tube.vapor
Plymouth    leaf.craft.hospital.exile.evidence
Edinburgh   leave.crowd.response.purpose.outdoor
Belfast     learn.few.gold.fury.hip
Dublin      leader.wage.hair.shy.ask
```

So a British conversation drops the first word almost for free, and four words
reach anywhere in the country. It also shows the catch: Edinburgh, Belfast and
Dublin fall on the other side of a seam, and near a seam the dropped word is not
predictable from "we are both in Britain". That is precisely the case the
checksum catches, rather than resolving quietly to the wrong place — and
precisely why the country box search is the more reliable of the two ways to
fill a dropped word back in, since it tries every candidate rather than
assuming the nearest.

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

Cell *area* is untouched — the projection is equal-area, so only the shape
changes and the resolution figures are the same.

The terminal length is an even bit count (48), which is why it lands exactly
square. The cost falls on the odd lengths, which go to 2 : 1 —
a 3-word global cell is 172 × 345 m rather than 264 × 225 m. No frame can square
both: one exponent is odd whenever the other is even. The best compromise that
squares *nothing* but evens everything out is a √2 frame (47.86°), which puts
every length at 1.414 : 1; squaring the lengths that people actually say is
worth more.

The bits are handed to whichever axis is currently wider at each step rather
than alternating, which is what keeps the odd lengths at 2 : 1 rather than
carrying the frame's aspect down into every cell. With a square frame the two
rules agree; the machinery is kept because the aspect is *derived* from the box
rather than written down.

## The last word does two jobs

A whole fifth word of position would reach 8 cm, finer than anyone needs. So its
11 bits are split between refinement and checksum:

| Refine | Check | Cell | Wrong word caught |
|---|---|---|---|
| 3 | 8 | 1.90 m | 99.61 % |
| **4** | **7** | **1.35 m** | **99.22 %** |
| 5 | 6 | 0.95 m | 98.44 % |

Shipped at **4 refine + 7 check**. For comparison, what3words is 3 m with no
checksum at all — this is finer *and* verified.

A checksum genuinely cannot live at *every* length: its bits would sit exactly
where the next word's position bits must go. Reserving 8 bits at every length
would take 2 words from 11 km to 177 km. Putting it in the last word instead
costs nothing at the shorter lengths, which are simply unverified.

Five words is terminal for the same reason — a sixth would have to reinterpret
the check bits. The 7 bits cover the *whole* position, which is what makes both
kinds of shortening safe: a reconstruction that guesses wrong fails the check,
whether the guess came from a reference point or from a box search.

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

Every point on earth encodes, poles and both sides of the antimeridian
included; every address is a prefix of the next longer one; round trip inside
one cell diagonal at every length; no repeats at 2 and 3 words; dropping
leading words and filling them back in from a reference inside the tile
reconstructs exactly; a reference too far away is caught 99.4 %; a wrong word
is rejected 99.1 %; no cell worse than 2 : 1, and exactly square at even
lengths. An index is never negative and never past the end — the clamp is at
both ends, since an unclamped negative would sign-extend under `>>` and mint a
plausible address for the wrong place.

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
