#!/usr/bin/env python3
"""Derive the region registry from Natural Earth geometry.

    python3 tools/regions/build_regions.py <admin_0> <admin_1> <map_subunits>

Writes tools/gridcode/regions.json. Rerun it rather than editing that file.

EVERY REGION CODE IS A PUBLISHED IDENTIFIER -- ISO 3166-1 for a country, ISO
3166-2 for a subdivision. Nothing here invents a code, because the prefix is
only worth having if the caller already knows it. "Which country am I in" and
"which state am I in" are known; "which of the six boxes of the United States
am I in" is not, so numbered parts are not offered at any price in resolution.

That is also why boxes are never split into geographic quadrants, and why the
country box is kept even where subdivisions exist: US-CA sits inside US and
both are valid, so knowing only the country still works, just more coarsely.
Overlapping boxes are the point, not a defect.

Large countries are exactly the ones Natural Earth carries subdivisions for,
which is what keeps the resolution tail in check: a caller in Russia says the
oblast they are standing in rather than accepting a 17 m cell.

LONGITUDE IS NORMALISED, NOT CLIPPED. A country straddling the antimeridian
has a naive bounding box spanning the globe -- Kiribati's is the whole earth.
So a box may run past 180 (Fiji is 176.9 to 182.0) and the codec normalises a
query longitude into the box's range. The seam is placed at the territory's
widest empty gap in longitude, which is the narrowest box that contains it.
"""
import json, math, os, sys

R = 6371008.8
K = math.cos(math.radians(30.0))     # the codec's projection, so areas compare
PAD = 0.05                           # degrees of slack, for coastline simplification


def polygons(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates'][0]]
    return [p[0] for p in geom['coordinates']]


def span(lngs):
    """The narrowest longitude interval containing every point, as
    (start, end) with end possibly past 180.

    Longitude is circular, so the narrowest interval is the complement of the
    widest empty gap between consecutive points. Taking min and max instead
    gives the whole globe for anything crossing the antimeridian.
    """
    s = sorted(set(lngs))
    if len(s) == 1:
        return s[0], s[0]
    gaps = [(s[i + 1] - s[i], i) for i in range(len(s) - 1)]
    gaps.append((s[0] + 360 - s[-1], len(s) - 1))   # the gap across the seam
    _, i = max(gaps)
    if i == len(s) - 1:
        return s[0], s[-1]                          # widest gap already at the seam
    return s[i + 1], s[i] + 360


def box_of(rings):
    lats = [c[1] for r in rings for c in r]
    lng0, lng1 = span([c[0] for r in rings for c in r])
    return [min(lats), max(lats), lng0, lng1]


def area(b):
    latMin, latMax, lngMin, lngMax = b
    dy = abs(math.sin(math.radians(latMax)) - math.sin(math.radians(latMin))) * R / K
    return abs(math.radians(lngMax - lngMin) * R * K * dy)


def pad(b):
    return [round(max(-90.0, b[0] - PAD), 4), round(min(90.0, b[1] + PAD), 4),
            round(b[2] - PAD, 4), round(b[3] + PAD, 4)]


def boxes_by_code(path, code_key, name_key, label=None):
    """One box per ISO code, with the longitude span taken over every vertex of
    that code at once. Computing a box per feature and unioning those does not
    work across the antimeridian: each feature picks its own seam, and boxes
    written in different frames cannot be compared."""
    rings, names = {}, {}
    for f in json.load(open(path))['features']:
        p = f['properties']
        code, name = p.get(code_key), p.get(name_key)
        if not code or code in ('-99', '') or code == 'AQ' or not name:
            continue          # AQ is Antarctica; a blank code means disputed
        rings.setdefault(code, []).extend(polygons(f['geometry']))
        names.setdefault(code, label(p) if label else name)
    return {c: (pad(box_of(r)), names[c]) for c, r in rings.items()}


def main(admin0, admin1, subunits=None):
    # Natural Earth files some territory under its sovereign's code and some
    # under its own, and neither file is right for every country: the country
    # layer puts French Guiana inside FR (a 26 m cell for Paris), while the
    # subunit layer puts Diego Garcia inside GB (a 20 m cell for London).
    #
    # So take, for each code, whichever source draws it tighter. Both are
    # honest representations of the same code, and a tighter box is strictly
    # better resolution. Territory a tighter box leaves out is not lost: it
    # keeps its own region where it has an ISO code of its own, and every point
    # on earth is inside XZ regardless.
    best = boxes_by_code(admin0, 'ISO_A2_EH', 'NAME_EN')
    if subunits:
        for code, (box, name) in boxes_by_code(subunits, 'ISO_A2_EH', 'NAME_EN').items():
            if code not in best:
                best[code] = (box, name)          # a territory the country layer lacks
            elif area(box) < area(best[code][0]):
                # Tighter box, but keep the country layer's name: the subunit
                # layer would call FR "Corsica" and NZ "South Island".
                best[code] = (box, best[code][1])

    out = [{'code': c, 'name': n, 'box': b} for c, (b, n) in best.items()]
    out += [{'code': c, 'name': n, 'box': b} for c, (b, n) in boxes_by_code(
        admin1, 'iso_3166_2', 'name',
        label=lambda p: f"{p['name']}, {p.get('admin')}").items() if c not in best]

    out.sort(key=lambda r: r['code'])
    # Everywhere else: open ocean, airspace, and anything the registry misses.
    # Every point on earth has an address; most land has a much finer one.
    out.append({'code': 'XZ', 'name': 'International (whole earth)',
                'box': [-90.0, 90.0, -180.0, 180.0]})

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'gridcode', 'regions.json')
    with open(dest, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f'{len(out)} regions -> {os.path.normpath(dest)}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
