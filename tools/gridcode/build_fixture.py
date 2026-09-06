#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

# A spread over the whole world, including the seams the codec has to survive:
# both poles, both sides of the antimeridian, and the equator.
POINTS = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (53.34980, -6.26030), (48.85660, 2.35220), (40.75800, -73.98550),
    (37.81990, -122.47860), (55.75580, 37.61730), (-33.86880, 151.20930),
    (1.28970, 103.85010), (-18.14160, 178.44190), (-16.50000, -179.90000),
    (64.14660, -21.94260), (0.00000, 0.00000), (12.00000, -40.00000),
    (-90.0, 0.0), (90.0, 0.0), (0.0, 180.0), (0.0, -180.0), (89.9999, 179.9999),
]
# Tails resolved from a reference: (lat, lng, n_said, ref_lat, ref_lng).
TAILS = [
    (51.50072, -0.12456, 2, 51.50100, -0.12500),
    (51.50072, -0.12456, 3, 51.51000, -0.13000),
    (51.50072, -0.12456, 4, 52.48620, -1.89040),
    (-16.50000, -179.99000, 3, -16.49000, -179.97000),
    # The reference sits on the far side of the antimeridian, 2 km away on the
    # ground but a world apart in index terms. x has to wrap.
    (-16.50000, -179.99000, 3, -16.49000, 179.99000)
]
# References far enough away that the reconstruction must be refused rather
# than resolving quietly to the wrong tile.
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
    out = {
        'points': [{'lat': la, 'lng': lo,
                    'words': {str(n): g.encode(la, lo, words, n)
                              for n in range(1, g.MAX_WORDS + 1)}}
                   for la, lo in POINTS],
        'tails': [{'lat': la, 'lng': lo, 'n': n, 'ref': [rla, rlo],
                   'words': g.encode(la, lo, words)[-n:],
                   'resolved': list(g.resolve_tail(
                       g.encode(la, lo, words)[-n:], words, rla, rlo))}
                  for la, lo, n, rla, rlo in TAILS],
        # Kept only where the reference really is too far: the checksum
        # catches that 99.2% of the time, so a case can slip through by luck
        # and must not be baked into the fixture as an expected refusal.
        'hopeless': [{'n': n, 'ref': [rla, rlo],
                      'words': g.encode(la, lo, words)[-n:]}
                     for la, lo, n, rla, rlo in HOPELESS
                     if refused(la, lo, n, rla, rlo, words)],
        'order': ''.join('xy'[a] for a in g._ORDER),
        'axis_bits': [g._XB, g._YB],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(out['tails'])} tails, "
          f"{len(out['hopeless'])} hopeless -> {path}")
