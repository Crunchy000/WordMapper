#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g
import h3.api.basic_int as h3

# A spread over the whole world, including the seams the codec has to survive:
# both poles, both sides of the antimeridian, the equator -- and a pentagon,
# where H3 has a child missing.
POINTS = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (53.34980, -6.26030), (48.85660, 2.35220), (40.75800, -73.98550),
    (37.81990, -122.47860), (55.75580, 37.61730), (-33.86880, 151.20930),
    (1.28970, 103.85010), (-18.14160, 178.44190), (-16.50000, -179.90000),
    (64.14660, -21.94260), (0.00000, 0.00000), (12.00000, -40.00000),
    (-90.0, 0.0), (90.0, 0.0), (0.0, 180.0), (0.0, -180.0), (89.9999, 179.9999),
    h3.cell_to_latlng(h3.get_pentagons(g.RES)[3]),
]

if __name__ == '__main__':
    words = g.load_wordlist()
    hexs = lambda c: format(c, 'x')
    rng = random.Random(1)
    # The scramble on its own, so a mismatch says which half disagrees.
    values = [0, 1, g.HALF - 1, g.HALF, g.SPACE - 1] + [rng.randrange(g.SPACE) for _ in range(40)]
    # Misheard addresses: one word swapped. Each either decodes to some cell or
    # is refused, and the two ports must agree on which.
    wrong = []
    for la, lo in POINTS[:12]:
        a = g.encode(la, lo, words)
        for k in range(3):
            b = list(a)
            b[k] = words[(words.index(a[k]) + 1 + rng.randrange(1295)) % 1296]
            try:
                got = hexs(g.decode_cell(b, words))
            except ValueError:
                got = None
            wrong.append({'words': b, 'cell': got})
    out = {
        'res': g.RES, 'check': g.CHECK, 'half': g.HALF, 'rounds': g.ROUNDS,
        'scramble': [[v, g.scramble(v)] for v in values],
        'points': [{'lat': la, 'lng': lo, 'cell': hexs(g.cell_at(la, lo)),
                    'words': g.encode(la, lo, words)} for la, lo in POINTS],
        'wrong': wrong,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(values)} scrambles, "
          f"{len(wrong)} wrong words ({sum(w['cell'] is None for w in wrong)} refused) -> {path}")
