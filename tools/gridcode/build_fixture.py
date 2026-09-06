#!/usr/bin/env python3
"""Regenerate fixture.json from the Python reference, for check-demo.mjs."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

POINTS = [(51.50072, -0.12456), (51.50550, -0.07540), (51.17889, -1.82624),
          (55.94859, -3.19951), (52.97150, -9.43090), (50.06569, -5.71531),
          (58.64389, -3.07000), (53.46308, -2.29139), (54.5, -6.0), (60.1, -1.2)]

# Points the box does not cover, plus its four inclusive corners. Both ports
# must agree on where coverage stops, not only on what they encode inside it.
OUTSIDE = [(48.8566, 2.3522), (40.4168, -3.7038), (40.7128, -74.0060),
           (-33.8688, 151.2093), (64.1466, -21.9426), (0.0, 0.0),
           (49.84, -2.0), (60.91, -2.0), (55.0, -11.01), (55.0, 1.81)]
CORNERS = [(g.BOX['latMin'], g.BOX['lngMin']), (g.BOX['latMin'], g.BOX['lngMax']),
           (g.BOX['latMax'], g.BOX['lngMin']), (g.BOX['latMax'], g.BOX['lngMax'])]

if __name__ == '__main__':
    words = g.load_wordlist()
    out = {
        'points': [{'lat': la, 'lng': lo,
                    'words': {str(n): g.encode(la, lo, words, n)
                              for n in range(1, g.MAX_WORDS + 1)}}
                   for la, lo in POINTS + CORNERS],
        'outside': [{'lat': la, 'lng': lo} for la, lo in OUTSIDE],
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture.json')
    with open(path, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(f"{len(out['points'])} points + {len(out['outside'])} outside written to {path}")
