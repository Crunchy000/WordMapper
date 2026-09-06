# A global word grid

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## The idea

One grid over the whole world. Five [BIP-39][bip39] words name any point on
earth to 1.35 m. No prefix, no registry, no agreement about borders, nothing
the caller has to know about where they are.

```
leg.tunnel.slam.subway.gown          Big Ben
```

An address shortens in **two directions**, and they do different jobs.

## Drop trailing words: coarser, needs no context

Each word narrows the area, and the words already said never change — every
address is a prefix of a longer one.

| Words | Big Ben | Cell |
|---|---|---|
| 1 | `leg` | 542 × 460 km |
| 2 | `leg.tunnel` | 8.5 × 14.4 km |
| 3 | `leg.tunnel.slam` | 264 × 225 m |
| 4 | `leg.tunnel.slam.subway` | 4.1 × 7.0 m |
| 5 | `leg.tunnel.slam.subway.gown` | **1.03 × 1.75 m, and verified** |

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

### How it falls over the UK

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

**Five words is therefore terminal** — a sixth would have to reinterpret the
check bits.

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

- every point on earth encodes, the poles and both sides of the antimeridian
  included
- every address is a prefix of the next longer one, every length
- round trip inside one cell diagonal at every length
- no address repeats anywhere on earth, at 2 and 3 words
- dropping leading words and filling them back in from a reference inside the
  tile reconstructs the address exactly, at every length
- a reference too far away is caught 99.4 % of the time, within a point of the
  99.22 % the check bits allow
- a wrong word in a five-word address is rejected 99.1 %, likewise
- no cell is worse than 1.7 : 1

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture generated from the Python reference, so the two cannot drift:
encodings, truncation, checksums, tail resolution across the antimeridian,
refusal of hopeless references, the bit order itself, and address parsing.

Both run in CI on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
