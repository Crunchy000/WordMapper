# Local word addresses on a 70 km lattice

Reference implementation: [`tools/gridcode/bip39grid.py`](../tools/gridcode/bip39grid.py),
tests in [`test_bip39grid.py`](../tools/gridcode/test_bip39grid.py).
Setup: `npm install --prefix tools/gridcode`.

## The idea

The world is projected to an equal-area plane and tiled into 70 km squares. **The
square is not transmitted.** An address names a point *within* a square, and the
listener supplies the square from knowing roughly where they are.

That omission is the whole trick. 104,095 squares cover the earth, so not saying
which one is **16.7 bits you never have to speak**, and those bits go into
resolution instead.

## Bit budget

A BIP-39 word is exactly 11 bits, because the list is exactly 2,048 words.

| Words | Bits | Points per 70 km square | Cell |
|---|---|---|---|
| 2 | 22 | 4,194,304 | 34.2 m |
| **3** | **33** | **8,589,934,592** | **0.755 m** |
| 4 | 44 | 1.76 × 10¹³ | 1.7 cm |

Check bits come out of resolution:

| Check bits | Cell | Wrong word detected |
|---|---|---|
| 0 | 0.53 × 1.07 m | 0 % |
| 4 | 2.1 × 4.3 m | 93.8 % |
| 8 | 8.5 × 17.1 m | 99.6 % |

Measured detection matches theory exactly.

## The checksum is not optional

BIP-39 is built to be **typed and checksummed**, not spoken. Its guarantee is
unique four-letter prefixes, which says nothing about sound. Measured against the
whole list:

- **4 outright homophones**: `pair`/`pear`, `peace`/`piece`, `right`/`write`, `wear`/`where`
- **806** pairs one letter apart, **1,824** pairs one phoneme apart
- **53 %** of words have a same-or-one-phoneme twin, so **89.6 %** of three-word
  addresses contain a word that a single mishearing turns into a different valid word

Without check bits, such a mishearing is silently a different place. With 8 check
bits it is caught 99.6 % of the time. Choose accordingly.

BIP-39 does get one thing right that cost real effort elsewhere: **zero plurals**.

## Uniqueness, and the honest version of the 35 km claim

The address repeats on the lattice, so two instances are both within *R* of some
point exactly when the spacing is below 2*R*. A 35 km guarantee therefore needs
**70 km spacing in both directions** — and an equal-area cylinder only delivers
that at its standard parallel:

| Latitude | E–W spacing | N–S spacing | Hint must be good to |
|---|---|---|---|
| 0° | 80.8 km | 60.6 km | 30.3 km |
| **30° (standard parallel)** | **70.0 km** | **70.0 km** | **35.0 km** |
| 45° | 57.2 km | 85.7 km | 28.6 km |
| 51.5° (London) | 50.3 km | 97.4 km | **25.2 km** |
| 60° | 40.4 km | 121.2 km | 20.2 km |

So the 70 km square is 70 km in *equal-area units*, not on the ground. At UK
latitudes it is roughly 50 km × 97 km, and the position hint has to be good to
about 25 km rather than 35 km.

Three ways to fix it, none free:

1. **Move the standard parallel to the region** — 55° makes the lattice exactly
   70 km square over the UK, and worse elsewhere. Fine for a national scheme.
2. **Latitude bands**, as UTM does. Standard practice, more machinery.
3. **An equal-area cube** (S2/Snyder). Shape distortion bounded near 1.3:1
   everywhere, so the hint requirement never falls below ~27 km globally.

## Worked examples

| Place | Address (0 check bits) |
|---|---|
| Big Ben | `shoulder.few.lottery` |
| Tower Bridge | `success.chase.alley` |
| Stonehenge | `leg.athlete.trial` |
| Edinburgh Castle | `machine.cruise.bunker` |
| Sydney Opera House | `approve.net.merit` |
| Statue of Liberty | `copy.tissue.cushion` |

Round trip is within one cell diagonal at every check-bit setting, over 4,000
random points between ±60° latitude.

## What this gives up

An address is no longer self-contained. `shoulder.few.lottery` is meaningless
without knowing which 70 km square, so it cannot be read out to a stranger who
has no idea where you are — which is precisely the emergency-services case. The
natural fix is to prefix a place name when out of context: *"Cornwall:
shoulder.few.lottery"*.

Ordering is Z-order (Morton) rather than Hilbert: the high bits still narrow the
location, so a prefix is meaningful, but locality is a little worse than a
Hilbert curve would give.
