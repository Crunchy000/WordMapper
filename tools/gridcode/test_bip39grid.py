#!/usr/bin/env python3
"""Checks for the H3 word grid. Run: python3 tools/gridcode/test_bip39grid.py"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g
import h3.api.basic_int as h3

WORDS = g.load_wordlist()
random.seed(20261025)
fails = []


def check(label, got, want):
    ok = got == want
    print(f'  {"PASS" if ok else "FAIL"}  {label:62s} {got}')
    if not ok:
        fails.append(label)


def anywhere(n):
    """Uniform over the sphere by area, which is uniform in sin(lat)."""
    return [(math.degrees(math.asin(random.uniform(-1, 1))),
             random.uniform(-180, 180)) for _ in range(n)]


def offset(lat, lng, metres):
    """A point up to `metres` away in a random direction, uniform by area."""
    d, b = metres * math.sqrt(random.random()), random.uniform(0, 2 * math.pi)
    la = lat + math.degrees(d * math.cos(b) / g.R)
    lo = lng + math.degrees(d * math.sin(b) / g.R / max(1e-6, math.cos(math.radians(lat))))
    return max(-90.0, min(90.0, la)), (lo + 180.0) % 360.0 - 180.0


def circumradius(cell):
    c = h3.cell_to_latlng(cell)
    return max(g.hav(*c, *v) for v in h3.cell_to_boundary(cell))


PTS = anywhere(4000)
SEAMS = [(lat, lng) for lat in (-90, -89.999, 0, 89.999, 90)
         for lng in (-180, -179.999, 0, 179.999, 180)]

print('\nthe layout')
check('word one carries the base cell and one digit', g.POSITIONS[0], 122 * 7)
check('no word holds more than the list',
      all(p * c <= g.LIST_SIZE for p, c in zip(g.POSITIONS, g.CHECKS)), True)
# 7**4 = 2401 does not fit in 1296, so three digits a word is the most there is.
# Words five and six hold two on purpose: each gives up a digit for a check of
# 26, which keeps the checksum in the trailing words, where a tail keeps it.
check('words one to four could not hold another digit',
      all(p * g.APERTURE > g.LIST_SIZE for p in g.POSITIONS[:4]), True)
check('words five and six each trade a digit for check',
      g.CHECKS[4:], [26, 26])
check('the checks multiply out to the whole checksum', math.prod(g.CHECKS), g.CHECK)
check('six words reach resolution 14', g.RES_AT[-1], 14)
check('each length\'s check divides the next one\'s',
      [math.prod(g.CHECKS[:n + 1]) % math.prod(g.CHECKS[:n])
       for n in range(1, g.MAX_WORDS)], [0] * (g.MAX_WORDS - 1))
check('check digits round-trip',
      all(g._undigits_check(g._check_digits(v, g.CHECKS), g.CHECKS) == v
          for v in (random.randrange(g.CHECK) for _ in range(2000))), True)
check('H3 indexes round-trip through base cell and digits',
      all(g.make_cell(*g.cell_digits(c)) == c
          for c in (g.cell_at(la, lo, random.randint(0, 15)) for la, lo in PTS[:2000])),
      True)

print('\nthe grid')
check('every point on earth encodes',
      all(len(g.encode(la, lo, WORDS)) == g.MAX_WORDS for la, lo in PTS), True)
check('the poles and the antimeridian encode',
      all(len(g.encode(la, lo, WORDS)) == g.MAX_WORDS for la, lo in SEAMS), True)
check('an address decodes to the cell it came from',
      all(g.decode_cell(g.encode(la, lo, WORDS), WORDS) == g.cell_at(la, lo)
          for la, lo in PTS + SEAMS), True)
check('all twelve pentagons encode and decode',
      all(g.decode_cell(g.encode(*h3.cell_to_latlng(p), WORDS), WORDS)
          == g.cell_at(*h3.cell_to_latlng(p))
          for p in h3.get_pentagons(g.RES)), True)

print('\ntrailing words: coarser, no context needed')
check('every address is a prefix of the next longer one',
      sum(g.encode(la, lo, WORDS, n) != g.encode(la, lo, WORDS)[:n]
          for la, lo in PTS[:1500] for n in range(1, g.MAX_WORDS)), 0)
check('a shorter address is the H3 parent of the longer one',
      all(g.decode_cell(g.encode(la, lo, WORDS, n), WORDS)
          == h3.cell_to_parent(g.cell_at(la, lo), g.RES_AT[n - 1])
          for la, lo in PTS[:500] for n in range(1, g.MAX_WORDS + 1)), True)
# H3 nests approximately: the hexagon of a coarse cell, as drawn, does not quite
# contain all its descendants. So a point is not always inside the coarse
# hexagon -- but it is always close to its centre, within a few percent of the
# cell's own circumradius.
for n in range(1, g.MAX_WORDS + 1):
    worst = 0.0
    for la, lo in PTS[:800]:
        cell = g.decode_cell(g.encode(la, lo, WORDS, n), WORDS)
        worst = max(worst, g.hav(la, lo, *h3.cell_to_latlng(cell)) / circumradius(cell))
    check(f'{n} words (res {g.RES_AT[n - 1]:2d}): within 1.1 cell radii of the centre',
          worst < 1.1, True)

print('\nleading words: same precision, fewer words, needs context')
# Dropping the coarse words leaves one cell of ambiguity at the dropped
# resolution, and a reference near enough picks it back out. H3 cells vary in
# size and orientation across the globe, so the guarantee is stated against the
# average edge. Where two base cells meet their digits point different ways, so
# a candidate across the seam can sit nearer the reference than the true one;
# that only bites when the dropped cells are big. So: 0.4 of an edge for one
# to three words said, a quarter for four, and for five -- only a base cell and
# a digit dropped -- a quarter and 98 % rather than all.
FRAC = {1: (0.4, 1.0), 2: (0.4, 1.0), 3: (0.4, 1.0), 4: (0.25, 1.0), 5: (0.25, 0.98)}
for n in range(1, g.MAX_WORDS):
    e = g.tile_edge(n)
    frac, need = FRAC[n]
    ok = 0
    for la, lo in PTS[:400]:
        try:
            got = g.resolve_tail_cell(g.encode(la, lo, WORDS)[-n:], WORDS, *offset(la, lo, frac * e))
        except ValueError:
            continue
        ok += got == g.cell_at(la, lo)
    f = lambda v: f'{v/1000:.3g} km' if v >= 1000 else f'{v:.0f} m'
    check(f'{n} words said resolve from a reference within {f(frac * e)}',
          ok >= need * 400, True)

check('a full address needs no reference at all',
      all(g.resolve_tail_cell(g.encode(la, lo, WORDS), WORDS, 0.0, 0.0) == g.cell_at(la, lo)
          for la, lo in PTS[:200]), True)

# The checksum covers the whole reconstruction, so a reference too far away to
# pick the right cell is caught rather than resolving quietly to the wrong one.
# A tail keeps only the check its own words carry.
for n in (3, 5):
    modulus = math.prod(g.CHECKS[g.MAX_WORDS - n:])
    caught = tot = 0
    for la, lo in PTS[:3000]:
        full = g.encode(la, lo, WORDS)
        far = anywhere(1)[0]
        if g.hav(la, lo, *far) < 4 * g.tile_edge(n):
            continue
        tot += 1
        try:
            g.resolve_tail_cell(full[-n:], WORDS, *far)
        except ValueError:
            caught += 1
    theory = (1 - 1 / modulus) * 100
    print(f'  ----  {n} words from a hopeless reference: caught {caught/tot*100:.2f}% '
          f'(theory {theory:.2f}%, 1 in {modulus:,})')
    check(f'{n} words: a hopeless reference is caught within a point of theory',
          abs(caught / tot * 100 - theory) < 1.0, True)

print('\nhow few words, in practice')
BIG_BEN = (51.50072, -0.12456)
for ref, label in [((51.5008, -0.1246), 'the same room'),
                   ((51.5010, -0.1250), 'the same street'),
                   ((51.5100, -0.1300), 'a mile away'),
                   ((51.5, -0.2), 'across London'),
                   ((52.4862, -1.8904), 'Birmingham'),
                   ((48.8566, 2.3522), 'Paris'),
                   ((40.7128, -74.0060), 'New York')]:
    n = g.words_needed(*BIG_BEN, *ref, WORDS)
    print(f'  ----  from {label:16s} {n} words: '
          f'{g.format_address(g.encode(*BIG_BEN, WORDS)[-n:], tail=n < g.MAX_WORDS)}')

print('\nthe checksum')
theory = (1 - 1 / g.CHECK) * 100
caught, tot = 0, 20000
for i in range(tot):
    a = g.encode(*PTS[i % len(PTS)], WORDS)
    bad = list(a)
    k = random.randrange(g.MAX_WORDS)
    while bad[k] == a[k]:
        bad[k] = random.choice(WORDS)
    try:
        g.decode(bad, WORDS)
    except ValueError:
        caught += 1
# Detection beats 1 - 1/CHECK: a misheard word that lands on a value no position
# uses, or on a pentagon's missing child, is refused before the checksum runs.
print(f'  ----  a wrong word is rejected {caught/tot*100:.4f}% (at least {theory:.4f}%)')
check('detection is at least the checksum\'s', caught / tot * 100 >= theory - 0.02, True)
check('a valid address always passes its own checksum',
      all(g.decode(g.encode(la, lo, WORDS), WORDS) is not None for la, lo in PTS[:500]), True)
check('shorter addresses decode without a checksum',
      all(g.decode(g.encode(la, lo, WORDS, n), WORDS) is not None
          for n in range(1, g.MAX_WORDS) for la, lo in PTS[:120]), True)
unused = next(i for i in range(g.LIST_SIZE) if i // g.CHECKS[1] >= g.POSITIONS[1])
try:
    g.decode(g.encode(*BIG_BEN, WORDS, 1) + [WORDS[unused]], WORDS)
    check('a value no position uses is refused', False, True)
except ValueError:
    check('a value no position uses is refused', True, True)

print('\naddress strings')
full = g.encode(*BIG_BEN, WORDS)
check('an absolute address has no leading separator', g.format_address(full), '.'.join(full))
check('a tail is marked with one', g.format_address(full[-3:], tail=True),
      '.' + '.'.join(full[-3:]))
check('parse round trips absolute', g.parse_address('.'.join(full)), (full, False))
check('parse round trips a tail',
      g.parse_address(g.format_address(full[-3:], tail=True)), (full[-3:], True))
check('parse accepts spaces and case',
      g.parse_address('  LEG tunnel Slam '), (['leg', 'tunnel', 'slam'], False))

print('\nthe antimeridian')
# The reference is 2 km away on the ground but on the other side of 180, so the
# four words said leave a 26 km cell to fill in -- plenty.
near = g.encode(-16.50, -179.99, WORDS)
check('a tail resolves from the far side of the seam',
      g.resolve_tail_cell(near[-4:], WORDS, -16.49, 179.99) == g.cell_at(-16.50, -179.99), True)

print()
for n in range(1, g.MAX_WORDS + 1):
    mod = g.CHECK if n == g.MAX_WORDS else 1
    print(f'  ----  {n} words: res {g.RES_AT[n - 1]:2d}, edge {g.edge_length(n):>12,.2f} m, '
          + (f'checked 1 in {mod:,}' if mod > 1 else 'unverified'))
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
