# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## Two scopes

The same grid mechanism over a different box.

```
leg.tunnel.slam.subway.gown          Big Ben, Global — 5 words, 1.35 m
play.cram.side.someone               Big Ben, UK     — 4 words, 2.43 m
```

**Global** is five [BIP-39][bip39] words over the whole world. No registry, no
agreement about borders, nothing the caller has to know about where they are.

**UK** is four words over a box around the United Kingdom — Lizard Point to
Shetland, St Kilda to Lowestoft. One word shorter, self-contained, and needs
nothing said or known beyond "this is a UK address".

The scope is bound into the checksum, so **the two can never be silently
confused**: a UK address read as a global one fails its check 99.2 % of the
time. That asymmetry has one gap worth knowing, covered under
[Telling them apart](#telling-them-apart).

### Which to use

UK mode wins on ergonomics, not resolution. Global mode shortened by one
leading word is also four words and reaches **1.35 m against UK's 2.43 m**,
because one dropped word is worth a full 11 bits of context where the UK box is
worth only 9.3. What UK mode buys is that there is nothing to reconstruct and
no reference point: four words, and you are done.

An address shortens in **two directions** in either scope, and they do
different jobs.

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

## Which axis gets each bit

Not a plain alternation. The projected world is 34,667 × 14,713 km, an aspect of
2.36, and alternating bits carries that aspect straight down into every cell:
2.07 × 0.88 m at full depth.

Giving each bit to whichever axis is currently *wider* keeps cells near square
at every length — 1.70 : 1 at worst, 1.18 : 1 at half the lengths — for exactly
the same cell area, since the projection is equal-area and only the shape
changes. x ends up with 25 bits and y with 23.

```
x x y x y x y x y x y x y x y x y x y x y x y x y ...
```

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

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift: both
scopes' encodings, truncation, checksums, the UK box and its refusals, tail
resolution across the antimeridian, hopeless references, both bit orders, the
scope-identification order, and address parsing.

Both run in CI on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
