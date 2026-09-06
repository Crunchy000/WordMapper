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
# Inside the UK box, corners included. Dublin is in there: the box is a
# rectangle, not a border.
UK_POINTS = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (54.59730, -5.93010), (60.15500, -1.14500), (53.34980, -6.26030),
    (49.85, -8.70), (49.85, 1.80), (60.90, -8.70), (60.90, 1.80),
]
# Tails resolved from a reference: (lat, lng, n_said, ref_lat, ref_lng).
TAILS = [
    (51.50072, -0.12456, 2, 51.50100, -0.12500),
    (51.50072, -0.12456, 3, 51.51000, -0.13000),
    (51.50072, -0.12456, 4, 52.48620, -1.89040),
    (-16.50000, -179.99000, 3, -16.49000, -179.97000),
    # The reference sits on the far side of the antimeridian, 2 km away on the
    # ground but a world apart in index terms. Global x has to wrap.
    (-16.50000, -179.99000, 3, -16.49000, 179.99000),
]
# References far enough away that the reconstruction must be refused rather
# than resolving quietly to the wrong tile.
HOPELESS = [(51.50072, -0.12456, 3, 40.71280, -74.00600),
            (51.50072, -0.12456, 2, 48.85660, 2.35220)]
# Coordinates the UK box does not cover: both ports must refuse them.
UK_OUTSIDE = [(48.8566, 2.3522), (40.7128, -74.0060), (-33.8688, 151.2093),
              (53.2707, -9.0568), (64.1466, -21.9426), (0.0, 0.0)]


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
        'uk': {
            'points': pack(UK_POINTS, g.UK),
            'outside': [{'lat': la, 'lng': lo} for la, lo in UK_OUTSIDE],
            'order': ''.join('xy'[a] for a in g.UK.order),
            'axis_bits': [g.UK.xb, g.UK.yb],
            'box': g.UK.box,
        },
        # A UK address is not terminal in global mode, so nothing checks it --
        # which is why decode_auto tries the UK reading first. Both ports must
        # agree on that resolution order.
        'auto': [{'words': g.encode(la, lo, words, s=sc), 'scope': sc.key,
                  'verified': True}
                 for sc, la, lo in [(g.UK, 51.50072, -0.12456),
                                    (g.UK, 55.94859, -3.19951),
                                    (g.GLOBAL, 51.50072, -0.12456),
                                    (g.GLOBAL, -33.86880, 151.20930)]]
        + [{'words': g.encode(51.50072, -0.12456, words, 3), 'scope': 'global',
            'verified': False}],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"global: {len(out['global']['points'])} points, "
          f"{len(out['global']['tails'])} tails, "
          f"{len(out['global']['hopeless'])} hopeless; "
          f"uk: {len(out['uk']['points'])} points, "
          f"{len(out['uk']['outside'])} outside; "
          f"auto: {len(out['auto'])} -> {path}")
