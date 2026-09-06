# Truncatable word addresses

Reference: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## The idea

An address is a **prefix of a longer address**. Say as many words as you need
and stop; each one narrows the area, and the words already said never change.

| Words | Big Ben | Area |
|---|---|---|
| 1 | `plug` | 22.0 km |
| 2 | `plug.curtain` | 486 m — a street |
| 3 | `plug.curtain.elder` | 10.7 m — a building |
| 4 | `plug.curtain.elder.script` | **2.69 m, and verified** |

The root is a **fixed bounding box** (UK and Ireland), not a repeating tile, so
an address is unambiguous at every length. There are no repeats to disambiguate
and **no position hint is required** — an approximate location becomes a sanity
check rather than a precondition.

That is the useful shape for an emergency call: a caller who manages two words
before the line drops has still given a real answer, and one who keeps going
narrows it without repeating themselves.

## Why the prefix property needs care

Coordinates are interleaved **once at full precision** and the resulting bit
string is truncated. Deriving the interleave order per length does not work,
and fails in a way that is easy to miss: 11 bits per word is odd, so 33 bits
splits the axes 17/16 while 22 and 44 split evenly. Those are three unrelated
sequences, not prefixes of one another. Measured, the three-word address came
out completely different from the two- and four-word ones, which agreed with
each other — so a spot check on 2 and 4 would have passed.

The test suite checks this directly, at every length, over 4,000 points.

## The fourth word does two jobs

Three words alone reach 10.75 m, which is wide. A whole fourth word of position
would reach 24 cm, which is finer than anyone needs. So the fourth word's 11
bits are **split between refinement and checksum**:

| Refine | Check | 4-word cell | Wrong word caught |
|---|---|---|---|
| 2 | 9 | 5.37 m | 99.80 % |
| 3 | 8 | 3.80 m | 99.61 % |
| **4** | **7** | **2.69 m** | **99.22 %** |
| 5 | 6 | 1.90 m | 98.44 % |
| 6 | 5 | 1.34 m | 96.88 % |

Shipped at **4 refine + 7 check**. For comparison, what3words is 3 m with no
checksum at all — this is finer *and* verified.

A checksum genuinely cannot live at *every* length: its bits would sit exactly
where the next word's position bits must go. Reserving 8 bits at every length
would take 2 words from 486 m to 7.78 km. Putting it in the last word instead
costs nothing at lengths 1–3, which are simply unverified.

**Four words is therefore terminal** — a fifth would have to reinterpret the
checksum bits. Nothing is ambiguous, because the fourth word is always last.

## The word list

The [BIP-39 English list][bip39] as published, 2,048 words, exactly 11 bits
each. It is designed to be *typed and checksummed*, not spoken: it contains
`pair`/`pear`, `peace`/`piece`, `right`/`write` and `wear`/`where`, and 53 % of
its words have a same-or-one-phoneme twin, so 89.6 % of three-word addresses
contain a word one mishearing turns into a different valid word. The check word
is what stands against that, not the list.

It does contain **zero plurals**, which is the failure mode that made other
schemes' addresses confusable.

## Projection

Lambert cylindrical equal-area, standard parallel 30°. Cell *areas* are
constant across the box; cell *shapes* stretch with latitude, so the 3-word
cell is about 9.4 × 12.3 m rather than square, and the 4-word one 2.4 × 3.1 m.
An equal-area cube would bound that distortion if the box ever went global.

## Locality

Sharing *k* words means being in the same level-*k* cell — exact, in both
directions. So a shared prefix **proves** proximity: two addresses sharing two
words are within 602 × 393 m of each other, no exceptions.

The converse leaks at cell boundaries. Two points a metre apart share their
first two words 99.8 % of the time and all three words 87.8 % of the time, but
not always. Treat a matching prefix as confirmation and a mismatch as worth
asking again, rather than as an error.

This is a property of the grid partition, not of the curve used to order cells:
a Hilbert ordering would change which word is assigned to each cell, never
which cell a point falls in.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

- every address is a prefix of the next longer one, 4,000 points × 5 lengths
- round trip inside one cell diagonal at every length
- no address repeats anywhere in the box, at 2 and 3 words
- a wrong word in a four-word address is rejected 99.1 % of the time, within a
  point of the 99.22 % theory for 7 check bits
- one-, two- and three-word addresses decode without needing a checksum

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture from the Python reference — encodings, truncation and check words — so
the two implementations cannot drift. CI runs both on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
