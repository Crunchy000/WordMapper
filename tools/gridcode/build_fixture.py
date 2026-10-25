#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g
import h3.api.basic_int as h3

# A spread over the whole world, including the seams the codec has to survive:
# both poles, both sides of the antimeridian, the equator -- and a pentagon,
# where H3 has a child missing.
PENTAGON = h3.cell_to_latlng(h3.get_pentagons(g.RES)[3])
POINTS = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (53.34980, -6.26030), (48.85660, 2.35220), (40.75800, -73.98550),
    (37.81990, -122.47860), (55.75580, 37.61730), (-33.86880, 151.20930),
    (1.28970, 103.85010), (-18.14160, 178.44190), (-16.50000, -179.90000),
    (64.14660, -21.94260), (0.00000, 0.00000), (12.00000, -40.00000),
    (-90.0, 0.0), (90.0, 0.0), (0.0, 180.0), (0.0, -180.0), (89.9999, 179.9999),
    PENTAGON,
]
# Tails resolved from a reference POINT: (lat, lng, n_said, ref_lat, ref_lng).
# The reference has to be well inside the cell the dropped words would have
# named: 1.5 km edges at three words said, 26 km at four, 483 km at five.
TAILS = [
    (51.50072, -0.12456, 1, 51.50073, -0.12457),      # a metre: same room
    (51.50072, -0.12456, 3, 51.50200, -0.12500),      # 150 m: same street
    (51.50072, -0.12456, 4, 51.52000, -0.14000),      # 2.5 km: across London
    (51.50072, -0.12456, 5, 52.48620, -1.89040),      # Birmingham
    (-16.50000, -179.99000, 4, -16.49000, -179.97000),
    # The reference sits on the far side of the antimeridian, 2 km away.
    (-16.50000, -179.99000, 4, -16.49000, 179.99000),
]
# References too far away to pick the right cell: must be refused, not resolved
# quietly to the wrong place.
HOPELESS = [(51.50072, -0.12456, 4, 40.71280, -74.00600),
            (51.50072, -0.12456, 3, 48.85660, 2.35220)]


def refused(la, lo, n, rla, rlo, words):
    try:
        got = g.resolve_tail_cell(g.encode(la, lo, words)[-n:], words, rla, rlo)
    except ValueError:
        return True
    return got != g.cell_at(la, lo)


if __name__ == '__main__':
    words = g.load_wordlist()
    hexs = lambda c: format(c, 'x')
    out = {
        'max_words': g.MAX_WORDS,
        'res': g.RES,
        'check': g.CHECK,
        'word_digits': g.WORD_DIGITS,
        'positions': g.POSITIONS,
        'checks': g.CHECKS,
        'res_at': g.RES_AT,
        'points': [{'lat': la, 'lng': lo, 'cell': hexs(g.cell_at(la, lo)),
                    'words': {str(n): g.encode(la, lo, words, n)
                              for n in range(1, g.MAX_WORDS + 1)}}
                   for la, lo in POINTS],
        'tails': [{'n': n, 'ref': [rla, rlo],
                   'words': g.encode(la, lo, words)[-n:],
                   'cell': hexs(g.resolve_tail_cell(
                       g.encode(la, lo, words)[-n:], words, rla, rlo))}
                  for la, lo, n, rla, rlo in TAILS],
        'hopeless': [{'n': n, 'ref': [rla, rlo],
                      'words': g.encode(la, lo, words)[-n:]}
                     for la, lo, n, rla, rlo in HOPELESS
                     if refused(la, lo, n, rla, rlo, words)],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(out['tails'])} tails, "
          f"{len(out['hopeless'])} hopeless -> {path}")
