#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
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
# Tails resolved from a reference POINT: (lat, lng, n_said, ref_lat, ref_lng).
# The reference has to sit inside the tile the dropped words leave, and those
# tiles are 21.5 m, 689 m, 22.1 km and 706 km at 1, 2, 3 and 4 words said.
TAILS = [
    (51.50072, -0.12456, 2, 51.50077, -0.12460),      # a few metres: same room
    (51.50072, -0.12456, 3, 51.50200, -0.12500),      # 150 m: same street
    (51.50072, -0.12456, 4, 51.52000, -0.14000),      # 2.5 km: across London
    (-16.50000, -179.99000, 3, -16.49000, -179.97000),
    # The reference sits on the far side of the antimeridian, 2 km away on the
    # ground but a world apart in index terms. x has to wrap.
    (-16.50000, -179.99000, 3, -16.49000, 179.99000),
]
# References too far away to pick the right tile: must be refused, not resolved
# quietly to the wrong place.
HOPELESS = [(51.50072, -0.12456, 3, 40.71280, -74.00600),
            (51.50072, -0.12456, 2, 48.85660, 2.35220)]

# The other way to fill a dropped word back in: a REGION rather than a point.
# These are country boxes as Nominatim returns them (south, north, west, east).
# The box is only a search window -- never part of an address -- but both ports
# have to search the SAME window, or the same words would shorten by different
# amounts.
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
    sc = g.GLOBAL

    def search(la, lo, box):
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

    out = {
        'max_words': sc.max_words,
        'max_candidates': g.MAX_CANDIDATES,
        'order': ''.join('xy'[a] for a in sc.order),
        'axis_bits': [sc.xb, sc.yb],
        'box': list(sc.box),
        'points': [{'lat': la, 'lng': lo,
                    'words': {str(n): g.encode(la, lo, words, n)
                              for n in range(1, sc.max_words + 1)}}
                   for la, lo in POINTS],
        'tails': [{'lat': la, 'lng': lo, 'n': n, 'ref': [rla, rlo],
                   'words': g.encode(la, lo, words)[-n:],
                   'resolved': list(g.resolve_tail(
                       g.encode(la, lo, words)[-n:], words, rla, rlo))}
                  for la, lo, n, rla, rlo in TAILS],
        'hopeless': [{'n': n, 'ref': [rla, rlo],
                      'words': g.encode(la, lo, words)[-n:]}
                     for la, lo, n, rla, rlo in HOPELESS
                     if refused(la, lo, n, rla, rlo, words)],
        'boxes': [{'name': name, 'box': box,
                   'points': [search(la, lo, box) for la, lo in pts]}
                  for name, box, pts in BOXES],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(out['tails'])} tails, "
          f"{len(out['hopeless'])} hopeless, {len(out['boxes'])} country boxes "
          f"-> {path}")
