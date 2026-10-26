#!/usr/bin/env python3
"""Checks for the four-word H3 grid. Run: python3 tools/gridcode/test_bip39grid.py"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g
import h3.api.basic_int as h3

WORDS = g.load_wordlist()
random.seed(20261026)
fails = []
R = 6371008.8


def check(label, got, want):
    ok = got == want
    print(f'  {"PASS" if ok else "FAIL"}  {label:62s} {got}')
    if not ok:
        fails.append(label)


def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def anywhere(n):
    """Uniform over the sphere by area, which is uniform in sin(lat)."""
    return [(math.degrees(math.asin(random.uniform(-1, 1))),
             random.uniform(-180, 180)) for _ in range(n)]


def circumradius(cell):
    c = h3.cell_to_latlng(cell)
    return max(hav(c, v) for v in h3.cell_to_boundary(cell))


PTS = anywhere(4000)
BIG_BEN = g.encode(51.50072, -0.12456, WORDS)
SEAMS = [(lat, lng) for lat in (-90, -89.999, 0, 89.999, 90)
         for lng in (-180, -179.999, 0, 179.999, 180)]

print('\nthe layout')
check('four words are 1296 to the fourth', g.SPACE, 2_821_109_907_456)
check('resolution 12 fits, with no whole factor to spare', (g.CELLS <= g.SPACE, g.CHECK), (True, 1))
check('resolution 13 would not fit', g.BASE_CELLS * g.APERTURE ** 13 > g.SPACE, True)
check('the Feistel halves cover the space exactly', g.HALF ** 2, g.SPACE)
check('ordinals round-trip through cells',
      all(g.cell_to_ordinal(g.ordinal_to_cell(x)) == x
          for x in (random.randrange(g.CELLS) for _ in range(5000))), True)
check('cells round-trip through ordinals',
      all(g.ordinal_to_cell(g.cell_to_ordinal(g.cell_at(la, lo))) == g.cell_at(la, lo)
          for la, lo in PTS[:2000]), True)

print('\nthe scramble')
check('unscramble undoes scramble',
      all(g.unscramble(g.scramble(v)) == v
          for v in (random.randrange(g.SPACE) for _ in range(20000))), True)
check('scramble undoes unscramble',
      all(g.scramble(g.unscramble(n)) == n
          for n in (random.randrange(g.SPACE) for _ in range(20000))), True)
check('the ends of the space map inside it',
      all(0 <= g.scramble(v) < g.SPACE and 0 <= g.unscramble(v) < g.SPACE
          for v in (0, 1, g.HALF - 1, g.HALF, g.SPACE - 1)), True)

print('\nthe grid')
check('every point on earth encodes to four words',
      all(len(g.encode(la, lo, WORDS)) == 4 for la, lo in PTS), True)
check('an address decodes to the cell it came from',
      all(g.decode_cell(g.encode(la, lo, WORDS), WORDS) == g.cell_at(la, lo)
          for la, lo in PTS + SEAMS), True)
check('all twelve pentagons encode and decode',
      all(g.decode_cell(g.encode_cell(p, WORDS), WORDS) == p
          for p in h3.get_pentagons(g.RES)), True)
check('a point is within its cell\'s radius of the centre',
      all(hav((la, lo), g.decode(g.encode(la, lo, WORDS), WORDS))
          <= circumradius(g.cell_at(la, lo)) * 1.001 for la, lo in PTS[:1000]), True)
cells = {g.cell_at(la, lo) for la, lo in PTS}
check('different cells never share an address',
      len({tuple(g.encode_cell(c, WORDS)) for c in cells}), len(cells))

print('\nneighbours share nothing')
# The scramble's whole point: nearby places are unrelated, so nothing about an
# address says where it is -- and nothing about a wrong word lands near.
shared = tot = 0
for la, lo in PTS[:500]:
    c = g.cell_at(la, lo)
    a = g.encode_cell(c, WORDS)
    for nb in h3.grid_ring(c, 1):
        b = g.encode_cell(nb, WORDS)
        tot += g.N_WORDS
        shared += sum(x == y for x, y in zip(a, b))
print(f'  ----  a neighbour shares a word in the same place {shared/tot*100:.3f}% '
      f'of the time (chance {100/1296:.3f}%)')
check('neighbours share words no more than chance', shared / tot < 3 / 1296, True)

print('\na wrong word')
# Caught when it lands past the last value that names a cell or on a pentagon's
# missing child -- there is no check at resolution 12. Otherwise it decodes,
# somewhere unrelated.
spare = 1 - g.USED / g.SPACE
theory = (spare + (1 - spare) * (1 - 1 / g.CHECK)) * 100
caught, tot, landed = 0, 20000, []
for i in range(tot):
    la, lo = PTS[i % len(PTS)]
    a = g.encode(la, lo, WORDS)
    bad = list(a)
    k = random.randrange(g.N_WORDS)
    while bad[k] == a[k]:
        bad[k] = random.choice(WORDS)
    try:
        landed.append(hav((la, lo), g.decode(bad, WORDS)))
    except ValueError:
        caught += 1
landed.sort()
print(f'  ----  caught {caught/tot*100:.2f}% (theory {theory:.2f}%)')
print(f'  ----  the rest land a median {landed[len(landed)//2]/1000:,.0f} km away; '
      f'{sum(d < 100e3 for d in landed)} of {len(landed)} within 100 km')
check('a wrong word is caught within two points of theory',
      abs(caught / tot * 100 - theory) < 2, True)
check('a wrong word that decodes lands far away (median over 5,000 km)',
      landed[len(landed) // 2] > 5_000e3, True)
check('almost never within 100 km (under 0.5%)',
      sum(d < 100e3 for d in landed) < 0.005 * len(landed), True)
def refused(spoken):
    try:
        g.decode_cell(spoken, WORDS)
    except ValueError:
        return True
    return False


# 40 % of values name no cell; find some by unscrambling and check they are
# refused outright.
past = [n for n in (random.randrange(g.SPACE) for _ in range(2000))
        if g.unscramble(n) >= g.USED]
check('a value past the last cell is refused',
      bool(past) and all(refused(g.number_to_words(n, WORDS)) for n in past), True)
check('three words or five are refused',
      refused(BIG_BEN[:3]) and refused(BIG_BEN + ['zoom']), True)

print('\naddress strings')
full = g.encode(51.50072, -0.12456, WORDS)
check('format joins with dots', g.format_address(full), '.'.join(full))
check('parse round trips', g.parse_address(g.format_address(full)), full)
check('parse accepts spaces, commas and case',
      g.parse_address('  LEG, tunnel Slam '), ['leg', 'tunnel', 'slam'])

print()
print(f'  ----  four words: H3 res {g.RES}, '
      f'{h3.average_hexagon_edge_length(g.RES, "m"):.1f} m edge, '
      f'{h3.average_hexagon_area(g.RES, "m^2"):.0f} m^2')
print(f'  ----  Big Ben is {g.format_address(full)}')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
