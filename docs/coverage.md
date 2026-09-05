# Coverage and resolution

Notes on how far the scheme can stretch, and what it costs. Figures from
`node tools/grid-check.mjs` and the arithmetic below.

## The one equation that matters

For an area `A` addressed with `L` words drawn from a list of `N` words:

```
cell side = sqrt( A / N^L )
```

Three things follow, and the third is the one that reframes the question:

1. Resolution scales with the **square root** of area, so coverage is cheap.
   Doubling the area costs only 41 % in cell size.
2. Resolution scales with `N^L`, so the word list and the address length are
   **exponential** levers.
3. **Grid dimensions do not appear.** `GRID_W`/`GRID_H` change the *shape* of
   cells, never their area. Adjusting the grid cannot buy resolution — it is
   purely a cell-aspect knob.

That last point is worth sitting with, because "adjust the grid sizes" is the
intuitive lever and it is the one that does nothing here.

## Extending over Ireland: yes, do it

Already applied to the demo. Moving `lngMin` from −8.65 to −11.00 takes in the
whole island of Ireland (Tearaght Island, the westernmost point, sits at about
−10.65).

| | UK only | UK + Ireland |
|---|---|---|
| Area | 809,990 km² | 992,141 km² (+22 %) |
| 3-word cell | 9.6 × 17.8 m | 11.7 × 17.8 m |
| Equivalent square | 13.1 m | **14.5 m** |

The extra longitude is absorbed by the same 41 columns, so cells get 22 % wider
and no shorter. As an equivalent square that is 13.1 m → 14.5 m: an **11 % cost
in precision for 22 % more area**, which is the square-root law above doing its
work. Nothing about this is a difficult trade.

It also happens to *improve* cell shape. The wider box has an aspect of 1.52
rather than 1.86, so cells are closer to square than before.

Two things to note:

- The name. "British Isles" is the tidy geographic label and is also contested
  in Ireland; "UK and Ireland" is the safer choice for anything user-facing.
- The box now includes a large slice of Atlantic and a corner of France and
  Belgium. That is unavoidable with a rectangle, and harmless — those cells
  simply address ocean and northern France.

## Global coverage: the intuition is half right

The worry is well founded **at three words**, and dissolves at four.

| Words | Whole globe | Land only (29 %) |
|---|---|---|
| 2 | 13.8 km | 7.5 km |
| 3 | **342 m** | 185 m |
| 4 | **8.5 m** | 4.6 m |
| 5 | 21 cm | 11 cm |

Three words globally gives 342 m — useless for an address; it will not
distinguish a building from its neighbourhood. That is the "we would lose too
much resolution" instinct, and it is correct.

Four words gives 8.5 m with the *existing* 1,633-word list. That is a usable
address — comfortably building-scale, within a factor of three of what3words.

So global coverage does not cost resolution. It costs **one more word**.

### Why what3words uses 40,000 words

Working backwards from a 3 m global target:

| Address length | Word list needed for 3 m globally |
|---|---|
| 3 words | 38,411 |
| 4 words | 2,744 |
| 5 words | 563 |

what3words uses ~40,000 words at 3 levels, which by this arithmetic gives 2.8 m
— matching their published 3 m. Their entire design is the top row: they bought
short addresses with an enormous word list.

The trade is stark. Going from 1,633 to 40,000 words means abandoning the
property that makes the Tirosh list good — that no two entries sound alike. A
40,000-word list is deep into homophone territory (`sale`/`sail`,
`there`/`their`) and obscure vocabulary, which is precisely why what3words needs
per-language curation and why their addresses are famously easy to mistype.

**Growing the list to ~2,750 and using four words is a far easier problem**, and
keeps phonetic distinctness within reach. 2,750 non-soundalike 3-7 letter words
is a plausible curation job; 40,000 is not.

## The real global blocker is projection, not resolution

This is the part the resolution question obscures. The current scheme divides
degrees, so cell width scales with `cos(latitude)`:

| Latitude | Cell width vs equator |
|---|---|
| 0° | 100 % |
| 45° | 71 % |
| 60° | 50 % |
| 80° | 17 % |
| 89° | 1.7 % |

Across the UK+Ireland box this is a 1.33× variation — sloppy but tolerable.
Globally the cells collapse to slivers at the poles and the scheme stops being
meaningfully "equal precision everywhere". Any global version has to fix this
first.

Two options:

**Lambert cylindrical equal-area** — substitute `y = sin(lat)` for latitude in
the grid maths. That is close to a one-line change and gives *exactly* equal-area
cells at every latitude. The cost is shape: with the standard parallel at 45°,
cells are square at 45°, 2:1 at 60°, and 7.5:1 at 75°. Area-correct, shape-poor
near the poles. Cheap and honest.

**Equal-area cube (S2/Snyder-style)** — project onto six cube faces, Hilbert
each face. Shape distortion stays bounded near 1.3:1 everywhere and area stays
uniform. This is what serious global grid systems do. It costs real
implementation work, and 1,633 does not divide evenly by six (272.2 cells per
face; a 6 × 16 × 17 top level gives 1,632 with one spare).

## Other options worth considering

### Named zone + 3 words

Instead of a fourth abstract word, make the first token a place name the speaker
already knows — `ireland.piano.tango.mango`, or `ireland` implied by context.
This is the phone country-code model, and it is easier to say and remember than a
fourth random word because it carries meaning.

| Zone scheme | Zone size | 3 words within zone |
|---|---|---|
| ~50 continental regions | 2,978,800 km² | 26.2 m |
| ~200 countries | 744,700 km² | 13.1 m |
| ~500 countries + subdivisions | 297,880 km² | 8.3 m |

A country-sized zone lands at 13 m — essentially the precision the UK demo
already has, available worldwide, with the existing word list and no projection
work beyond a per-zone box. It also means a local address stays three words, and
degrades gracefully: get the zone wrong and you are wrong by a country, not by a
random continent.

The catch is that zone boundaries are political, need maintenance, and leave the
oceans unaddressed.

### Variable-length addresses

Because each word strictly subdivides the previous cell, **every prefix is
already a valid coarser address**. That is a structural advantage over
what3words' fixed three words: the same scheme serves "which town" (3 words) and
"which doorway" (5 words), and a truncated address is degraded, not invalid.

Worth making explicit in the UI and the address format rather than leaving it
implicit.

### Land-only addressing

Skipping ocean cells recovers a 3.4× area saving — 1.85× finer, so 342 m → 185 m
at three words. Tempting, but it does not rescue the 3-word global case, it
requires shipping a coastline mask, it breaks the pure-arithmetic encode/decode,
and it makes Hilbert indices non-contiguous. It also removes marine addressing,
which is one of the more genuinely useful applications. Not recommended.

## Recommendation

1. **Ireland: done.** 11 % resolution cost, better cell aspect, no downside.
2. **For global, plan on four words, not three.** 8.5 m today with the existing
   list; ~3 m if the list grows to ~2,750, which is a realistic curation target.
   Do not chase a 40,000-word list to keep three words — that trades away the
   soundalike-free property that makes this worth building.
3. **Fix the projection before extending the box much further.** Lambert
   cylindrical equal-area is the cheap correct answer; an equal-area cube is the
   thorough one.
4. **Consider the named-zone variant** as a middle path: worldwide coverage at
   13 m, three spoken words, and no new vocabulary.
