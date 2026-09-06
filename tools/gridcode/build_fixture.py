#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

POINTS = [(51.50072, -0.12456), (51.50550, -0.07540), (51.17889, -1.82624),
          (55.94859, -3.19951), (52.97150, -9.43090), (50.06569, -5.71531),
          (58.64389, -3.07000), (53.46308, -2.29139), (54.5, -6.0), (60.1, -1.2)]

if __name__ == '__main__':
    words = g.load_wordlist()
    out = [{'lat': la, 'lng': lo,
            'words': {str(n): g.encode(la, lo, words, n)
                      for n in range(1, g.MAX_WORDS + 1)},
            'check3': g.check_word(g.encode(la, lo, words, 3), words)}
           for la, lo in POINTS]
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f'{len(out)} points written to {path}')
