#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

POINTS = [(51.50072, -0.12456), (51.50550, -0.07540), (51.17889, -1.82624),
          (55.94859, -3.19951), (-33.85678, 151.21528), (40.68925, -74.04450),
          (0.0, 0.0), (-45.3, 170.2), (60.1, -2.0), (35.68, 139.77)]

if __name__ == '__main__':
    words = g.load_wordlist()
    out = [{'lat': la, 'lng': lo, 'a0': g.encode(la, lo, words, 0),
            'a8': g.encode(la, lo, words, 8)} for la, lo in POINTS]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f'{len(out)} points written to {path}')
