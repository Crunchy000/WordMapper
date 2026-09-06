#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

# A spread of regions: the flagship, an overlapping pair, a subdivision, two
# boxes crossing the antimeridian, a tiny one and the global fallback.
POINTS = [
    ('GB', 51.50072, -0.12456), ('GB', 55.94859, -3.19951),
    ('GB', 50.06569, -5.71531), ('IE', 53.34980, -6.26030),
    ('IE', 52.97150, -9.43090), ('FR', 48.85660, 2.35220),
    ('US', 40.75800, -73.98550), ('US-NY', 40.75800, -73.98550),
    ('US-CA', 37.81990, -122.47860), ('RU', 55.75580, 37.61730),
    ('FJ', -18.14160, 178.44190), ('FJ', -16.50000, -179.90000),
    ('KI', 1.87110, -157.36720), ('SG', 1.28970, 103.85010),
    ('XZ', -33.86880, 151.20930), ('XZ', 64.14660, -21.94260),
]
# Coordinates each named region does not cover: both ports must refuse them.
OUTSIDE = [('GB', 48.8566, 2.3522), ('GB', 40.7128, -74.0060),
           ('IE', 51.5007, -0.1246), ('FR', 51.5007, -0.1246),
           ('SG', 3.1390, 101.6869), ('US-CA', 40.7580, -73.9855)]
# The region is inside the checksum, so an address minted in one region must
# fail in another: this is what stops Dublin resolving in Britain.
WRONG_REGION = [('IE', 'GB', 53.34980, -6.26030), ('GB', 'IE', 54.60000, -6.00000),
                ('US-NY', 'US-NJ', 40.75800, -73.98550)]

if __name__ == '__main__':
    words = g.load_wordlist()
    corners = []
    for code in ('GB', 'FJ', 'KI', 'XZ', 'US-CA'):
        latMin, latMax, lngMin, lngMax = g.REGIONS[code]['box']
        for lat in (latMin, latMax):
            for lng in (lngMin, lngMax):
                corners.append((code, lat, (lng + 180.0) % 360.0 - 180.0))
    out = {
        'points': [{'code': c, 'lat': la, 'lng': lo,
                    'covering': g.regions_covering(la, lo),
                    'words': {str(n): g.encode(la, lo, words, n, c)
                              for n in range(1, g.MAX_WORDS + 1)}}
                   for c, la, lo in POINTS + corners],
        'outside': [{'code': c, 'lat': la, 'lng': lo} for c, la, lo in OUTSIDE],
        'wrong_region': [{'minted': m, 'claimed': c, 'lat': la, 'lng': lo,
                          'words': g.encode(la, lo, words, g.MAX_WORDS, m)}
                         for m, c, la, lo in WRONG_REGION],
        'regions': len(g.REGIONS),
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(out['outside'])} outside, "
          f"{len(out['wrong_region'])} wrong-region -> {path}")
