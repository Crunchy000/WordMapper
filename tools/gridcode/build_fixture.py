#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

# A spread over the whole world, including the seams the codec has to survive:
# both poles, both sides of the antimeridian, and the equator.
GLOBAL_POINTS = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (53.34980, -6.26030), (48.85660, 2.35220), (40.75800, -73.98550),
    (37.81990, -122.47860), (55.75580, 37.61730), (-33.86880, 151.20930),
    (1.28970, 103.85010), (-18.14160, 178.44190), (-16.50000, -179.90000),
    (64.14660, -21.94260), (0.00000, 0.00000), (12.00000, -40.00000),
    (-90.0, 0.0), (90.0, 0.0), (0.0, 180.0), (0.0, -180.0), (89.9999, 179.9999),
]
# One point per region, plus its four box corners, so both ports agree on where
# every box starts and stops.
REGION_POINTS = {
    'local':     [(51.50072, -0.12456), (53.34980, -6.26030), (54.59730, -5.93010),
                  (60.15500, -1.14500)],
    'australia': [(-33.85680, 151.21530), (-37.81360, 144.96310), (-31.95230, 115.86130),
                  (-42.88210, 147.32720), (-12.46340, 130.84560)],
}
# Coordinates no region covers, so both ports must fall back to Global.
# Anywhere no region covers, so both ports must fall back to Global -- including
# the parts of Australia the 12 S cut leaves out.
OCEAN = [(20.0, -40.0), (-40.0, -20.0), (0.0, -140.0), (-60.0, 100.0), (85.0, 0.0),
         (48.85660, 2.35220), (35.65860, 139.74540), (-22.95190, -43.21050),
         (-10.89000, 142.39000), (-11.76000, 130.63000)]
# Points outside Local specifically, which Local must refuse rather than alias.
LOCAL_OUTSIDE = [(48.8566, 2.3522), (40.7128, -74.0060), (-33.8688, 151.2093),
                 (53.2700, -12.5000), (64.1466, -21.9426), (0.0, 0.0)]
# Global tails resolved from a reference: (lat, lng, n_said, ref_lat, ref_lng).
TAILS = [
    (51.50072, -0.12456, 2, 51.50100, -0.12500),
    (51.50072, -0.12456, 3, 51.51000, -0.13000),
    (51.50072, -0.12456, 4, 52.48620, -1.89040),
    (-16.50000, -179.99000, 3, -16.49000, -179.97000),
    # The reference sits on the far side of the antimeridian, 2 km away on the
    # ground but a world apart in index terms. Global x has to wrap.
    (-16.50000, -179.99000, 3, -16.49000, 179.99000),
]
# References too far away to pick the right tile: must be refused, not resolved
# quietly to the wrong place.
HOPELESS = [(51.50072, -0.12456, 3, 40.71280, -74.00600),
            (51.50072, -0.12456, 2, 48.85660, 2.35220)]

# Country boxes, as Nominatim returns them (south, north, west, east), with the
# points the country-shorten demo is checked against. The box is only a search
# window -- never part of an address -- but both ports have to search the SAME
# window, or the same words would be shortened by different amounts.
BOXES = [
    ('United Kingdom', [49.674, 61.061, -14.015, 2.096],
     [(51.50072, -0.12456), (55.94859, -3.19951), (54.59730, -5.93010)]),
    ('Ireland', [51.222, 55.636, -11.017, -5.066], [(53.34980, -6.26030)]),
    ('Switzerland', [45.818, 47.808, 5.956, 10.492], [(46.94800, 7.44740)]),
    ('Australia', [-43.644, -9.221, 112.921, 159.109], [(-33.86880, 151.20930)]),
    # Wrong window on purpose: France's box holds none of the above.
    ('France', [41.303, 51.124, -5.559, 9.662], [(51.50072, -0.12456)]),
    # Nominatim reports an antimeridian country inside out (west > east), which
    # reads as most of the planet: a useless window, and a safe one.
    ('Fiji', [-20.677, -12.480, 176.909, -178.144], [(-18.14160, 178.44190)]),
]


def refused(la, lo, n, rla, rlo, words):
    """True if resolving this tail from this reference fails, as it should."""
    try:
        got = g.resolve_tail(g.encode(la, lo, words)[-n:], words, rla, rlo)
    except ValueError:
        return True
    return g._indices(*got) != g._indices(la, lo)


if __name__ == '__main__':
    words = g.load_wordlist()

    def pack(pts, sc):
        return [{'lat': la, 'lng': lo,
                 'words': {str(n): g.encode(la, lo, words, n, sc)
                           for n in range(1, sc.max_words + 1)}}
                for la, lo in pts]

    def search(la, lo, box, words):
        """What a search of this box turns up at each length, and how short the
        address gets. `hits` is null where the search was too big to run."""
        out = {}
        for n in (3, 4, 5):
            got, searched = g.candidates_in_box(
                g.encode(la, lo, words)[-n:], words, box)
            out[str(n)] = {'hits': None if got is None else len(got),
                           'searched': searched}
        return {'lat': la, 'lng': lo,
                'said': g.shortest_in_box(la, lo, words, box)[0], 'search': out}

    regions = {}
    for sc in g.REGIONS:
        pts = list(REGION_POINTS[sc.key])
        latMin, latMax, lngMin, lngMax = sc.box
        for lat in (latMin, latMax):
            for lng in (lngMin, lngMax):
                pts.append((lat, (lng + 180.0) % 360.0 - 180.0))
        regions[sc.key] = {
            'name': sc.name, 'tag': sc.tag, 'box': list(sc.box),
            'max_words': sc.max_words,
            'order': ''.join('xy'[a] for a in sc.order),
            'axis_bits': [sc.xb, sc.yb],
            'points': pack(pts, sc),
        }

    out = {
        'global': {
            'points': pack(GLOBAL_POINTS, g.GLOBAL),
            'tails': [{'lat': la, 'lng': lo, 'n': n, 'ref': [rla, rlo],
                       'words': g.encode(la, lo, words)[-n:],
                       'resolved': list(g.resolve_tail(
                           g.encode(la, lo, words)[-n:], words, rla, rlo))}
                      for la, lo, n, rla, rlo in TAILS],
            'hopeless': [{'n': n, 'ref': [rla, rlo],
                          'words': g.encode(la, lo, words)[-n:]}
                         for la, lo, n, rla, rlo in HOPELESS
                         if refused(la, lo, n, rla, rlo, words)],
            'order': ''.join('xy'[a] for a in g.GLOBAL.order),
            'axis_bits': [g.GLOBAL.xb, g.GLOBAL.yb],
        },
        'regions': regions,
        # Which scope a point picks, and which words that yields. This is the
        # auto-switch: the smallest box containing the point, Global if none.
        'chosen': [{'lat': la, 'lng': lo, 'scope': g.best_scope(la, lo).key,
                    'words': g.encode(la, lo, words, s=g.best_scope(la, lo))}
                   for la, lo in
                   [p for pts in REGION_POINTS.values() for p in pts] + OCEAN],
        'local_outside': [{'lat': la, 'lng': lo} for la, lo in LOCAL_OUTSIDE],
        # Filling dropped leading words back in from a country box rather than
        # from a nearby point: how many cells the search covers, how many pass
        # the checksum, and how short the address gets.
        'boxes': [{'name': name, 'box': box,
                   'points': [search(la, lo, box, words) for la, lo in pts]}
                  for name, box, pts in BOXES],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"global {len(out['global']['points'])} points, "
          f"{len(regions)} regions "
          f"({sum(len(r['points']) for r in regions.values())} points), "
          f"{len(out['chosen'])} scope choices, "
          f"{len(out['boxes'])} country boxes -> {path}")
