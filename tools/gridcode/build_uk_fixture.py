#!/usr/bin/env python3
"""Regenerate fixture-uk.json from the Python reference, for check-uk-demo.mjs."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukgrid as u

# Corners of the UK and its islands, and places that must stay outside.
INSIDE = [
    (51.50072, -0.12456), (55.94859, -3.19951), (50.06569, -5.71531),
    (54.59661, -5.93011), (60.15468, -1.14492), (49.91432, -6.31515),
    (54.15000, -4.48000), (49.18580, -2.10910), (49.45580, -2.53570),
    (58.64395, -3.07050), (52.48140, 1.76220), (57.59630, -13.68720),
]
OUTSIDE = [(48.8566, 2.3522), (53.3498, -6.2603), (40.7128, -74.0060), (56.0, 3.0)]

def _fits(u, words, la, lo, d):
    try:
        u.decode_with(u.encode(la, lo, words), words, d)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    words = u.load_wordlist()
    rng = random.Random(1)
    pts = INSIDE[:]
    for _ in range(60):
        j, i = divmod(rng.choice(u.SQUARES), u.GRID_W)
        pts.append(u.unproject(u.X0 + (i + rng.random()) * u.SQUARE,
                               u.Y0 + (j + rng.random()) * u.SQUARE))
    values = [0, 1, u.HALF - 1, u.HALF, u.SPACE - 1] + [rng.randrange(u.SPACE) for _ in range(40)]
    wrong = []
    for la, lo in INSIDE:
        a = u.encode(la, lo, words)
        for k in range(u.N_WORDS):
            b = list(a)
            b[k] = words[(words.index(a[k]) + 1 + rng.randrange(1295)) % 1296]
            try:
                got = u.decode_value(b, words)
            except ValueError:
                got = None
            wrong.append({'words': b, 'value': got})
    # About 1 % of addresses name no cell. Add a few so the refusal path is
    # cross-checked too.
    while sum(w['value'] is None for w in wrong) < 5:
        n = rng.randrange(u.SPACE)
        if u.unscramble(n) >= u.CELLS:
            wrong.append({'words': u.number_to_words(n, words), 'value': None})
    out = {
        'k': u.K, 'cells': u.CELLS, 'squares': len(u.SQUARES),
        'scramble': [[v, u.scramble(v)] for v in values],
        'points': [{'lat': la, 'lng': lo, 'value': u.value_at(la, lo),
                    'words': u.encode(la, lo, words),
                    'centre': list(u.centre_of(u.value_at(la, lo))),
                    'digits': u.digits_at(la, lo), 'quarter': u.quarter_at(la, lo),
                    'quarter_centre': list(u.decode_with(u.encode(la, lo, words), words,
                                                         u.digits_at(la, lo)))}
                   for la, lo in pts],
        # Every number against a few cells: the ports must agree on which fit.
        'numbers': [{'value': u.value_at(la, lo),
                     'fits': [d for d in range(100) if _fits(u, words, la, lo, d)]}
                    for la, lo in INSIDE[:4]],
        'parse': [[t, list(u.parse_full(t))] for t in (
            'interval level adjective', 'interval.level.adjective 07',
            'interval level adjective forty two', 'Interval, level, adjective, four two',
            'interval level adjective oh seven', 'interval level adjective 4 2')],
        'outside': [list(p) for p in OUTSIDE],
        'wrong': wrong,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture-uk.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points, {len(values)} scrambles, {len(wrong)} wrong words "
          f"({sum(w['value'] is None for w in wrong)} refused) -> {path}")
