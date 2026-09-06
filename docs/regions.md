# Regions

An address is a region code and up to four words:

```
GB.plug.curtain.elder.script
```

The region is carried the way a dialling code is: out of band, and dropped
whenever both ends already know it. Nobody says +44 to a neighbour.

## Why a prefix rather than a fifth word

Scoping to a region is what keeps four words at metres. Resolution depends on
the area addressed, so the same 2,048⁴ addresses spread over one country are
far finer than over the globe — 2.4 m in the UK against 61 m worldwide.

It does **not** buy resolution over simply saying more words. Five words
worldwide would reach 1.35 m, better than region-scoped four words anywhere.
The prefix wins on three other things:

- **Four words stays the spoken length everywhere.** The prefix appears only
  when crossing a border, so the address does not grow for everyone in order
  to cover everyone.
- **A mistaken word stays in the region.** It lands somewhere in the same
  country rather than on another continent — the containment a flat global
  grid cannot offer.
- **The region is checked on a channel the words do not travel on.** A
  dispatcher already knows roughly where the caller is, so the coarse bits are
  confirmed for free. This is exactly why phone numbers can drop the country
  code.

## Every code is a published identifier

ISO 3166-1 for a country (`GB`, `FR`), ISO 3166-2 for a subdivision (`US-CA`,
`RU-MOW`). Nothing here invents a code.

That constraint is the whole design. A prefix is only worth having if the
caller already knows it: *which country* and *which state* are known, *which
of the six boxes of the United States* is not. So boxes are never split into
numbered parts or geographic quadrants, however much resolution that would
buy. `XZ` is the sole exception — the ISO user-assigned range, used here for
the whole earth.

## Regions overlap, deliberately

`US-CA` sits inside `US`; a point in California has a valid address under
either, and under `XZ`. Overlap is what lets a caller say as much as they
actually know, and it means border towns need no special case — a point near
the Irish border is simply in both `IE` and `GB`.

A box is a bounding box, not a claim of jurisdiction. Boxes are rectangles and
countries are not, so a point can fall inside the box of a region it is not
politically in: Times Square is inside New Jersey's bounding box. The address
still resolves correctly, because encoding and decoding use the same box. Pick
the region you know you are in; the demo lists every one that covers the point.

## What it costs

| | 4-word cell |
|---|---|
| median region | **1.25 m** |
| 90th percentile | 3.9 m |
| 95 % of regions | under 5 m |
| worst (`US`, which has 51 subdivisions) | 19.7 m |
| `XZ`, the global fallback | 60.9 m |

541 regions: 246 countries and 294 subdivisions. Natural Earth carries
subdivisions for essentially the countries whose own box is too big to be
useful, which is what keeps the tail in check — a caller in Russia says the
oblast they are standing in and gets 0.85 m rather than 17.1 m.

| | country | best subdivision |
|---|---|---|
| United Kingdom | 2.36 m | — |
| Germany | 2.03 m | — |
| France | 2.97 m | — |
| United States | 19.70 m | `US-NY` 1.55 m, `US-CA` 2.66 m |
| Russia | 17.10 m | `RU-MOW` 0.85 m |
| Singapore | 0.11 m | — |

## Building the registry

```
python3 tools/regions/build_regions.py <admin_0> <admin_1> <map_subunits>
```

from [Natural Earth](https://www.naturalearthdata.com/) 1:50m vectors. Rerun
it rather than editing `tools/gridcode/regions.json` by hand.

Two details in there are not obvious.

**Longitude is normalised, not clipped.** A country straddling the
antimeridian has a naive bounding box spanning the globe — Kiribati's is the
whole earth. So a box may run past 180 (`FJ` is 176.9 to 182.0) and the codec
brings a query longitude into the box's frame. The seam is placed at the
territory's widest empty gap in longitude, which is the narrowest box that
contains it. Kiribati comes out at 7.3 m instead of 61 m.

**Each code takes the tighter of two sources.** Neither Natural Earth layer is
right for every country: the country layer puts French Guiana inside `FR`,
giving Paris a 26 m cell, while the subunit layer puts Diego Garcia inside
`GB`, giving London a 20 m one. Taking whichever draws a code tighter fixes
both. Territory a tighter box leaves out is not lost — it keeps its own region
where it has its own ISO code, and every point on earth is inside `XZ`.

## Limits worth knowing

- **Disputed territory has no code.** Natural Earth carries Northern Cyprus
  and Somaliland with no ISO code, so they get no region of their own and fall
  to their neighbours' boxes and `XZ`. Any registry of this kind inherits the
  politics of its source; that is the real cost of the prefix, and it is not a
  technical one.
- **Antarctica is excluded** — an enormous box and nothing to address. It is
  inside `XZ`.
- **`XZ` cells distort near the poles.** The projection is equal-area, so
  cells hold their area but stretch in shape with latitude. An `XZ` address is
  61 m square in the tropics and up to several kilometres tall at extreme
  latitude. Regions spanning a narrow band of latitude do not have this
  problem, which is nearly all of them.
- **Coastline simplification** means a box is drawn from 1:50m geometry and
  padded by 0.05°. A point just offshore may fall outside its country's box
  and be covered only by `XZ`.
