#!/usr/bin/env python3
"""Checks for the global grid. Run: python3 tools/gridcode/test_bip39grid.py"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

WORDS = g.load_wordlist()
random.seed(20260906)
fails = []


def check(label, got, want):
    ok = got == want
    print(f'  {"PASS" if ok else "FAIL"}  {label:58s} {got}')
    if not ok:
        fails.append(label)


def proj_err(a, b):
    """Distance in the projection the grid is built in.

    Ground distance is the wrong ruler for a cell bound. The projection is
    equal-area, so cells hold their area but stretch in shape with latitude;
    near the poles a cell is very tall and the haversine between two points in
    the same cell exceeds its projected diagonal. The guarantee is that a point
    round trips into its own cell, which is a statement about the grid, so it
    is measured on the grid."""
    x1, y1 = g.project(*a)
    x2, y2 = g.project(*b)
    return math.hypot(x1 - x2, y1 - y2)


def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * g.R * math.asin(min(1, math.sqrt(h)))


def anywhere(n):
    """Uniform over the sphere by area, which is uniform in sin(lat)."""
    return [(math.degrees(math.asin(random.uniform(-1, 1))),
             random.uniform(-180, 180)) for _ in range(n)]


PTS = anywhere(4000)

print('\nthe grid')
check('every point on earth encodes',
      all(len(g.encode(lat, lng, WORDS)) == g.MAX_WORDS for lat, lng in PTS), True)
check('the poles and the antimeridian encode',
      all(len(g.encode(lat, lng, WORDS)) == g.MAX_WORDS
          for lat in (-90, -89.999, 0, 89.999, 90)
          for lng in (-180, -179.999, 0, 179.999, 180)), True)
# Not a plain alternation: the world is 2.36 times wider than tall in this
# projection, and alternating bits carries that aspect into every cell.
check('bit order gives x the extra bits', (g._XB, g._YB), (25, 23))
worst = max(max(w, h) / min(w, h) for w, h in
            (g.cell_size(n) for n in range(1, g.MAX_WORDS + 1)))
check('no cell is worse than 1.7:1', worst < 1.75, True)

print('\ntrailing words: coarser, no context needed')
bad = 0
for lat, lng in PTS[:1500]:
    full = g.encode(lat, lng, WORDS)
    for n in range(1, g.MAX_WORDS):
        if g.encode(lat, lng, WORDS, n) != full[:n]:
            bad += 1
check('every address is a prefix of the next longer one', bad, 0)

for n in range(1, g.MAX_WORDS + 1):
    w, h = g.cell_size(n)
    worst = max(proj_err((lat, lng), g.decode(g.encode(lat, lng, WORDS, n), WORDS))
                for lat, lng in PTS[:800])
    check(f'{n} words: round trip inside one cell diagonal',
          worst < math.hypot(w, h), True)

for n in (2, 3):
    seen, dupes = {}, 0
    w, h = g.cell_size(n)
    for lat, lng in PTS:
        k = tuple(g.encode(lat, lng, WORDS, n))
        if k in seen and proj_err((lat, lng), seen[k]) > math.hypot(w, h):
            dupes += 1
        seen.setdefault(k, (lat, lng))
    check(f'{n} words never repeat anywhere on earth', dupes, 0)

print('\nleading words: same precision, fewer words, needs context')
# Dropping the coarse words leaves an ambiguity of exactly one tile, so a
# reference anywhere inside half a tile must reconstruct the address exactly.
# Only the lengths that actually drop something: at MAX_WORDS nothing is
# dropped, the "tile" is the whole world, and no reference is involved -- that
# case is checked on its own below.
for n in range(1, g.MAX_WORDS):
    tw, th = g.tile_size(n)
    # Offset the reference in index space, by strictly less than half the
    # ambiguity period on each axis. That is exactly the guarantee -- nearer
    # than half a tile -- stated in the units the reconstruction works in, so
    # index truncation cannot eat the margin at the smallest tiles.
    cx, cy = g._known_low(n)
    ok = True
    for lat, lng in PTS[:400]:
        full = g.encode(lat, lng, WORDS)
        xi, yi = g._indices(lat, lng)
        rx = (xi + random.randint(-(2 ** cx // 2 - 1), 2 ** cx // 2 - 1)) % 2 ** g._XB
        ry = min(max(yi + random.randint(-(2 ** cy // 2 - 1), 2 ** cy // 2 - 1), 0),
                 2 ** g._YB - 1)
        ref = g.unproject(g._X0 + (rx + 0.5) / 2 ** g._XB * g._XR,
                          g._Y0 + (ry + 0.5) / 2 ** g._YB * g._YR)
        try:
            got = g.resolve_tail(full[-n:], WORDS, *ref)
        except ValueError:
            ok = False; break
        if g._indices(*got) != (xi, yi):
            ok = False; break
    f = lambda v: f'{v/1000:.1f} km' if v >= 1000 else f'{v:.0f} m'
    check(f'{n} words resolve from a reference inside their {f(tw)} x {f(th)} tile',
          ok, True)

check('a full address needs no reference at all',
      all(g._indices(*g.resolve_tail(g.encode(lat, lng, WORDS), WORDS, 0.0, 0.0))
          == g._indices(lat, lng) for lat, lng in PTS[:200]), True)

# The checksum covers the whole reconstruction, so a reference too far away to
# pick the right tile is caught rather than resolving quietly to the wrong place.
theory = (1 - 2 ** -g.CHECK_BITS) * 100
caught = tot = 0
for lat, lng in PTS[:2000]:
    full = g.encode(lat, lng, WORDS)
    far = anywhere(1)[0]
    if g._indices(*far) == g._indices(lat, lng):
        continue
    tot += 1
    try:
        got = g.resolve_tail(full[-3:], WORDS, *far)
    except ValueError:
        caught += 1
        continue
    if g._indices(*got) == g._indices(lat, lng):
        caught += 1              # got lucky and landed on the right tile anyway
print(f'  ----  a reference too far away is caught {caught/tot*100:.1f}% '
      f'(theory {theory:.2f}%, {g.CHECK_BITS} check bits)')
check('a hopeless reference is caught within a point of theory',
      abs(caught / tot * 100 - theory) < 1.0, True)

print('\nhow few words, in practice')
BIG_BEN = (51.50072, -0.12456)
for ref, label in [((51.5010, -0.1250), 'the same street'),
                   ((51.5100, -0.1300), 'a mile away'),
                   ((51.5, -0.2), 'across London'),
                   ((52.4862, -1.8904), 'Birmingham'),
                   ((48.8566, 2.3522), 'Paris'),
                   ((40.7128, -74.0060), 'New York')]:
    n = g.words_needed(*BIG_BEN, *ref, WORDS)
    print(f'  ----  from {label:16s} {n} words: '
          f'{g.format_address(g.encode(*BIG_BEN, WORDS)[-n:], tail=n < g.MAX_WORDS)}')

print('\nthe checksum')
caught = tot = 0
for lat, lng in PTS[:2000]:
    a = g.encode(lat, lng, WORDS)
    bad_a = list(a)
    i = random.randrange(g.MAX_WORDS)
    while bad_a[i] == a[i]:
        bad_a[i] = random.choice(WORDS)
    tot += 1
    try:
        g.decode(bad_a, WORDS)
    except ValueError:
        caught += 1
print(f'  ----  a wrong word is rejected {caught/tot*100:.1f}% (theory {theory:.2f}%)')
check('detection is within a point of theory',
      abs(caught / tot * 100 - theory) < 1.0, True)
check('a valid address always passes its own checksum',
      all(g.decode(g.encode(lat, lng, WORDS), WORDS) is not None
          for lat, lng in PTS[:500]), True)
check('shorter addresses decode without a checksum',
      all(g.decode(g.encode(lat, lng, WORDS, n), WORDS) is not None
          for n in range(1, g.MAX_WORDS) for lat, lng in PTS[:120]), True)

print('\naddress strings')
full = g.encode(*BIG_BEN, WORDS)
check('an absolute address has no leading separator',
      g.format_address(full), SEP_FULL := '.'.join(full))
check('a tail is marked with one', g.format_address(full[-3:], tail=True),
      '.' + '.'.join(full[-3:]))
check('parse round trips absolute', g.parse_address(SEP_FULL), (full, False))
check('parse round trips a tail',
      g.parse_address(g.format_address(full[-3:], tail=True)), (full[-3:], True))
check('parse accepts spaces and case',
      g.parse_address('  LEG tunnel Slam '), (['leg', 'tunnel', 'slam'], False))

print()
w, h = g.cell_size(g.MAX_WORDS)
print(f'  ----  5 words is {w:.2f} x {h:.2f} m ({math.sqrt(w*h):.2f} m square-equivalent)')
print(f'  ----  4 words alone is {math.sqrt(math.prod(g.cell_size(4))):.2f} m')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
