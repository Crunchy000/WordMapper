# The global word grid

The demos contain the complete JavaScript implementation. Coordinates are
projected onto one global equal-area frame, interleaved into a position bit
string, and represented by five BIP-39 words. The final word carries both
position refinement and a checksum.

## Consistent addresses

The grid is global and does not depend on a country, a boundary dataset, or a
generated fixture. The same coordinate therefore always produces the same five
words. The address is computed before any network request.

## Country shortening

`country-shorten.html` asks OpenStreetMap for the country and its bounding box.
That rectangle is only a search window; it is not part of the address. The
demo tries the trailing four words against every candidate cell in that window.
If exactly one cell passes the checksum, it displays four words. If the box is
too large or ambiguous, it displays all five.

Because country boundaries and bounding boxes can change, shortening is
deliberately opportunistic. Full five-word addresses remain stable and correct.

## Precision

Each additional word narrows the cell. The five-word global cell is about
1.35&nbsp;m square; shorter prefixes are coarser and require no country context.
