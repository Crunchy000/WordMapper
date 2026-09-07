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
    'local':    [(51.50072, -0.12456), (53.34980, -6.26030), (54.59730, -5.93010)],
    'europe':   [(48.85840, 2.29450), (55.75390, 37.62080), (64.14660, -21.94260)],
    'africa':   [(30.04440, 31.23570), (-33.92490, 18.42410), (6.52440, 3.37920)],
    'namerica': [(40.75800, -73.98550), (19.43260, -99.13320), (64.50110, -165.40640)],
    'samerica': [(-22.95190, -43.21050), (-34.60370, -58.38160), (4.71100, -74.07210)],
    'asia':     [(35.65860, 139.74540), (28.61390, 77.20900), (64.73140, 177.50850),
                 (66.00000, -174.00000)],
    'oceania':  [(-33.85680, 151.21530), (-36.84850, 174.76330), (-18.14160, 178.44190),
                 (-16.50000, -179.90000)],
}
# Coordinates no region covers, so both ports must fall back to Global.
OCEAN = [(20.0, -40.0), (-40.0, -20.0), (0.0, -140.0), (-60.0, 100.0), (85.0, 0.0)]
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
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"global {len(out['global']['points'])} points, "
          f"{len(regions)} regions "
          f"({sum(len(r['points']) for r in regions.values())} points), "
          f"{len(out['chosen'])} scope choices -> {path}")
