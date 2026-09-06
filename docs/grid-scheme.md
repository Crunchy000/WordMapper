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
| 4 | `plug.curtain.elder.scale` | 24 cm — a doorstep |
| 5 | `plug.curtain.elder.scale.buffalo` | 1 cm |

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

## Checksums cannot live at every length

A checksum's bits would sit exactly where the next word's position bits must
go. Reserving 8 bits at every length costs most of the resolution:

| Words | No checksum | With 8 check bits |
|---|---|---|
| 2 | 486 m | 7.78 km |
| 3 | 10.75 m | 172 m |
| 4 | 24 cm | 3.80 m |

So the checksum is a **separate optional suffix** — one extra word, covering
the word count as well as the words, so a three-word address plus check cannot
pass as a four-word address. It rejects a wrong word 99.9 % of the time
(theory: 1 − 1/2048 = 99.95 %).

It must be transmitted **distinguishably** — a different separator, or "check"
spoken before it. Otherwise `a.b.c.d` is ambiguous between a four-word address
and a three-word address with its check word.

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
cell is about 9.4 × 12.3 m rather than square. An equal-area cube would bound
that distortion if the box ever went global.

## Verified

`python3 tools/gridcode/test_bip39grid.py`:

- every address is a prefix of the next longer one, 4,000 points × 5 lengths
- round trip inside one cell diagonal at every length
- no address repeats anywhere in the box, at 2 and 3 words
- the check word rejects a wrong word 99.9 % of the time, and is length-specific

`node tools/gridcode/check-demo.mjs` runs the demo's own JavaScript port against
a fixture from the Python reference — encodings, truncation and check words — so
the two implementations cannot drift. CI runs both on every push.

[bip39]: https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039-wordlists.md
