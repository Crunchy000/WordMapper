#!/usr/bin/env python3
"""Regenerate fixture-ukphrase.json from the Python reference, for check-ukphrase-demo.mjs."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukphrase as p
import ukgrid as g

INSIDE = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (54.59661, -5.93011), (60.15468, -1.14492), (49.91432, -6.31515),
    (54.15000, -4.48000), (49.18580, -2.10910), (58.64395, -3.07050),
]
OUTSIDE = [(48.8566, 2.3522), (53.3498, -6.2603), (56.0, 3.0)]

if __name__ == '__main__':
    rng = random.Random(1)
    pts = INSIDE[:]
    for _ in range(60):
        j, i = divmod(rng.choice(g.SQUARES), g.GRID_W)
        pts.append(g.unproject(g.X0 + (i + rng.random()) * g.SQUARE,
                               g.Y0 + (j + rng.random()) * g.SQUARE))
    values = [0, 1, p.RIGHT - 1, p.RIGHT, p.SPACE - 1] + [rng.randrange(p.SPACE) for _ in range(40)]
    wrong = []
    for la, lo in INSIDE:
        a = p.encode(la, lo)
        for k in range(4):
            b = list(a)
            b[k] = rng.choice(p.LISTS[p.PATTERN[k]])
            try:
                got = p.decode_cell(b)
            except ValueError:
                got = None
            wrong.append({'words': b, 'cell': got})
    # Make sure both outcomes are cross-checked: some wrong phrases decode.
    while sum(w['cell'] is not None for w in wrong) < 5:
        b = p.number_to_phrase(rng.randrange(p.SPACE))
        try:
            wrong.append({'words': b, 'cell': p.decode_cell(b)})
        except ValueError:
            pass
    out = {
        'k': p.K, 'check': p.CHECK, 'sizes': p.SIZES,
        'scramble': [[v, p.scramble(v)] for v in values],
        'points': [{'lat': la, 'lng': lo, 'cell': p.cell_at(la, lo),
                    'words': p.encode(la, lo),
                    'centre': list(p.centre_of(p.cell_at(la, lo)))} for la, lo in pts],
        'outside': [list(q) for q in OUTSIDE],
        'wrong': wrong,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture-ukphrase.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(values)} scrambles, {len(wrong)} wrong phrases "
          f"({sum(w['cell'] is None for w in wrong)} refused) -> {path}")
