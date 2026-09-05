# Review: `demos/uk-word-grid.html`

Findings from auditing the imported demo. All figures are reproducible with
`node tools/grid-check.mjs`, which reads the word list and the Hilbert
implementation out of the demo itself.

Reference figures for the UK bounding box (49.85–60.90 °N, −8.65–1.80 °E):
roughly **661 km wide × 1228 km tall**, an aspect ratio of 1.86.

## Correctness

### 1. The 41×40 grid breaks the Hilbert curve

The whole point of ordering cells along a Hilbert curve is that consecutive
indices are spatially adjacent. At `GRID_W = 41, GRID_H = 40` that guarantee does
not hold: the path jumps from `(39, 38)` to `(40, 37)` at index 1068 — a diagonal
step, not an edge-adjacent one.

This is **not** a bug in the JS port. Transcribing Cerveny's `gilbert2d` back to
Python and running it at 41×40 reproduces the identical discontinuity, so the
port is faithful; 41×40 is simply a size the algorithm does not handle cleanly.
41×41 and 42×40 both come out clean.

### 2. Cells are 1.86:1 rectangles

A near-square grid over a box that is 1.86× taller than it is wide gives level-1
cells of **16.1 km × 30.7 km**. Because `GRID_W ≠ GRID_H`, the ratio also drifts
with depth: cell aspect at level *n* is `1.86 × (41/40)^n`, reaching 2.00 by
level 3. For an addressing scheme, near-square cells are preferable — they
minimise the worst-case distance from a point to its cell centre for a given cell
count.

The drift is slow here, but it is a trap worth naming, because the obvious fix
makes it far worse. See "Choosing grid dimensions" below.

### 3. The stated resolutions are wrong

`resolutions` claims `~12.2 km`, `~300 m`, `~7.5 m`. Actual cell sizes:

| Words | Claimed | Actual |
|---|---|---|
| 1 | ~12.2 km | 16.1 km × 30.7 km |
| 2 | ~300 m | 393 m × 767 m |
| 3 | ~7.5 m | 9.6 m × 19.2 m |

Every figure understates the true cell size, in one case by more than 2×.

### 4. The 7 unused cells leave holes at every level, not just one

`if (d >= words.length) break;` silently drops grid indices 1633–1639. At level 1
those land at roughly 60.4–60.9 °N, 1.0–1.6 °E — open North Sea, so harmless. But
the same grid is re-applied *inside every cell*, so those 7 holes are replicated
within every level-1 and level-2 cell, including cells over land. About 0.43 % of
each parent cell is unaddressable, and the demo gives no indication when you are
standing in one.

### 5. Longitude distortion across the box is ignored

Because the grid divides degrees rather than distance, a level-1 cell is 18.2 km
wide at the Lizard but only 13.8 km wide in Shetland — a 24 % variation. Worth
either documenting as an accepted simplification or correcting.

Note that switching to Web Mercator does *not* fix this on its own: the UK box is
1.876:1 in Mercator metres versus 1.86:1 equirectangular, so the two are
practically interchangeable for this purpose.

### 6. The word list does not match its description

The panel says "4-7 letters". Seven entries are three letters: `ego`, `fax`,
`jet`, `job`, `rio`, `ski`, `yes`. The list is otherwise clean — 1,633 entries,
no duplicates, nothing over 7 letters.

## Choosing grid dimensions

This deserves its own section, because the intuitive fix is a regression.

Cell aspect ratio at level *n* is `boxAspect × (GRID_W / GRID_H)^n`. The
grid-shape term **compounds**. So picking dimensions that make *level-1* cells
square is actively harmful: a 30×56 grid gives beautifully square 22.0 km cells
at level 1, then 734 m × 392 m at level 2 and 24.5 m × 7.0 m at level 3 — an
aspect of 3.5, twice as bad as the current demo.

The only grid shape that keeps cell aspect stable across levels is a **square
grid**, `GRID_W == GRID_H`. That fixes the ratio at the box's own aspect for
every level.

**41×41** is the smallest square grid that holds 1,633 words. It is
Hilbert-continuous, fixes issue 1, and holds cell aspect at a constant 1.86,
fixing the drift in issue 2. It leaves 48 spare cells. Level sizes become
16.1 km × 29.9 km, 393 m × 730 m, and 9.6 m × 17.8 m.

To get genuinely *square* cells, the bounding box itself has to be square in
whatever units the grid divides. Padding the box to 1228 km on a side and using
41×41 gives exactly square cells — 29.9 km, 730 m, 17.8 m — at the cost of only
54 % of the padded box covering the real UK, so a good fraction of the address
space is spent on ocean and France. That is a legitimate trade (what3words makes
the analogous choice globally); it is just worth making deliberately.

If the 17.8 m final cell is too coarse, a fourth word takes it to sub-metre
(0.23 m × 0.43 m) with an address space of 1633⁴ ≈ 7.1 × 10¹².

### Handle spare cells deliberately

Whichever grid is chosen, replace `break` with something explicit: either extend
the word list to the exact cell count, or map spare indices onto a reserved word
so every point in the box has an address. Silently unaddressable regions are the
kind of defect that only surfaces when someone is standing in one.

For what it is worth, 1,633 factors as 23 × 71, and 23×71 is Hilbert-clean — an
exact fit with zero spare cells. But it is not a square grid, so cell aspect
compounds from 1.66 at level 1 to 15.8 by level 3 — a 54 m × 3 m sliver.
Exactness is not worth that.

## Usability

### 7. You cannot see a cell's word before clicking it

The only way to learn a cell's word is to click it, which also subdivides it. A
`bindTooltip` on hover would make the mapping legible and make the Hilbert
locality property visible — the thing the demo exists to show.

### 8. Levels 2 and 3 are effectively unclickable

1,633 cells inside one level-1 cell are sub-pixel at UK-wide zoom. The
`zoom-toggle` checkbox acknowledges this, but it is off by default, so the
default experience is a grid you cannot use past the first level. Zooming to the
selected cell should be the default.

### 9. There is no decoder

The demo only encodes (click a map, get words). The inverse — type
`word.word.word`, land on the map — is the half that makes such a scheme useful,
and it is a straightforward reverse of the existing index lookup.

### 10. No shareable state

An address cannot be linked to. Reflecting the current selection into
`location.hash` and reading it on load would make results shareable and give the
decoder a natural entry point.

### 11. No error detection

A single mistyped or misheard word yields a valid address somewhere else in the
country, with nothing to flag it. Production schemes use a checksum — for
example, reserving a fraction of the address space so that most single-word
errors decode to nothing rather than to Aberdeen. The Hilbert ordering helps
here: an error in the *last* word stays spatially close, which is itself worth
demonstrating.

### 12. The rainbow fill obscures the map

Cycling hue across 1,633 cells at `fillOpacity` 0.22–0.42 makes the underlying
map hard to read and encodes nothing a user can act on. Consider outlines only,
with fill reserved for the selected cell.

## Implementation

### 13. Use the canvas renderer

Each level draws 1,633 `L.rectangle` layers as individual SVG paths — up to
~4,900 DOM nodes across three levels, all rebuilt on every click. Passing
`preferCanvas: true` to `L.map` renders them to a single canvas and removes most
of that cost.

### 14. Only draw cells that are visible

At levels 2 and 3 nearly every cell is off-screen or sub-pixel. Culling to the
current viewport, or deferring the draw until the map is zoomed in far enough to
resolve cells, avoids the work entirely.

### 15. Pin CDN assets with SRI

Leaflet is loaded from unpkg with no `integrity` attribute and no fallback. Add
subresource integrity hashes, or vendor the library, so the demo is not one CDN
incident away from a blank page.

### 16. Minor

- `updatePanel` writes to `innerHTML`. The words are a trusted static array so
  there is no injection risk today, but creating the `<code>` element and
  assigning `textContent` costs nothing and stays safe if the list ever becomes
  user-supplied.
- The default panel text is duplicated between the markup and `updatePanel`;
  the two will drift.
- No `<meta name="viewport">`, so the demo renders poorly on mobile.
- The word list is inlined as a 20 KB literal in the middle of the script. Moving
  it to a separate `words.json` (or at least the end of the file) would make the
  logic readable.
