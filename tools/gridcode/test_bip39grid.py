#!/usr/bin/env python3
"""Checks for the region-scoped codec. Run: python3 tools/gridcode/test_bip39grid.py"""
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


def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * g.R * math.asin(min(1, math.sqrt(h)))


def sample(code, n):
    """Random points inside a region's box, in real -180..180 longitude."""
    latMin, latMax, lngMin, lngMax = g.REGIONS[code]['box']
    out = []
    for _ in range(n):
        lat = random.uniform(latMin, latMax)
        lng = random.uniform(lngMin, lngMax)
        out.append((lat, (lng + 180.0) % 360.0 - 180.0))
    return out


print('\nregistry')
codes = list(g.REGIONS)
check('every code is unique', len(codes), len(set(codes)))
check('every box is well formed',
      all(r['box'][0] < r['box'][1] and r['box'][2] < r['box'][3]
          for r in g.REGIONS.values()), True)
check('XZ covers every point sampled',
      all(g.covers(lat, lng, 'XZ')
          for lat, lng in [(random.uniform(-90, 90), random.uniform(-180, 180))
                           for _ in range(2000)]), True)
check('nowhere is unaddressable',
      all(g.regions_covering(lat, lng) != []
          for lat, lng in [(random.uniform(-90, 90), random.uniform(-180, 180))
                           for _ in range(500)]), True)
check('regions_covering is tightest first',
      all(g.box_area(cs[0]) <= g.box_area(cs[-1])
          for cs in [g.regions_covering(*p) for p in sample('GB', 50)]), True)

# A spread of regions: the flagship, an overlapping pair, two antimeridian
# boxes, a subdivision, a tiny box and the global fallback.
SPREAD = ['GB', 'IE', 'FR', 'US', 'US-CA', 'RU', 'FJ', 'KI', 'SG', 'XZ']

print('\ngeometry, over a spread of regions')
worst_prefix = 0
for code in SPREAD:
    pts = sample(code, 400)
    bad = 0
    for lat, lng in pts:
        full = g.encode(lat, lng, WORDS, g.MAX_WORDS, code)
        for n in range(1, g.MAX_WORDS):
            if g.encode(lat, lng, WORDS, n, code) != full[:n]:
                bad += 1
    worst_prefix += bad
check('every address is a prefix of the next longer one', worst_prefix, 0)

def proj_err(a, b):
    """Distance in the projection the grid is actually built in.

    Ground distance is the wrong ruler for this bound. The projection is
    equal-area, so cells hold their area but stretch in shape with latitude;
    near the poles a cell is enormously long in latitude and the haversine
    between two points in the same cell exceeds its projected diagonal. The
    codec's guarantee is that a point round trips into its own cell, which is
    a statement about the grid, so it is measured on the grid."""
    (la1, lo1), (la2, lo2) = a, b
    x1, y1 = g.project(la1, lo1)
    x2, y2 = g.project(la2, lo2)
    return math.hypot(x1 - x2, y1 - y2)


for code in SPREAD:
    worst = worst_ground = 0.0
    for lat, lng in sample(code, 300):
        back = g.decode(g.encode(lat, lng, WORDS, g.MAX_WORDS, code), WORDS, code)
        worst = max(worst, proj_err((lat, lng), back))
        worst_ground = max(worst_ground, hav((lat, lng), back))
    w, h = g.cell_size(g.MAX_WORDS, code)
    ok = worst < math.hypot(w, h)
    check(f'{code}: 4 words round trip inside one cell diagonal', ok, True)
    if not ok:
        print(f'        cell {w:.3f} x {h:.3f} m, worst error {worst:.3f} m')
    if code == 'XZ':
        # Worth seeing: the same address is metres wide in the tropics and
        # kilometres tall near the poles, because equal area is not equal shape.
        print(f'  ----  XZ on the ground: up to {worst_ground/1000:.1f} km from a '
              f'{math.sqrt(w*h):.0f} m cell, at extreme latitude')

print('\nno repeats inside a region')
for code in ('GB', 'US-CA'):
    for n in (2, 3):
        seen, dupes = {}, 0
        w, h = g.cell_size(n, code)
        for lat, lng in sample(code, 4000):
            k = tuple(g.encode(lat, lng, WORDS, n, code))
            if k in seen and hav((lat, lng), seen[k]) > math.hypot(w, h):
                dupes += 1
            seen.setdefault(k, (lat, lng))
        check(f'{code}: {n} words never repeat in the region', dupes, 0)

print('\nthe checksum')
caught = tot = 0
for lat, lng in sample('GB', 2000):
    a = g.encode(lat, lng, WORDS, g.MAX_WORDS, 'GB')
    bad_a = list(a)
    i = random.randrange(g.MAX_WORDS)
    while bad_a[i] == a[i]:
        bad_a[i] = random.choice(WORDS)
    tot += 1
    try:
        g.decode(bad_a, WORDS, 'GB')
    except ValueError:
        caught += 1
theory = (1 - 2 ** -g.CHECK_BITS) * 100
print(f'  ----  a wrong word is rejected {caught/tot*100:.1f}% '
      f'(theory {theory:.2f}%, {g.CHECK_BITS} check bits)')
check('wrong-word detection is within a point of theory',
      abs(caught / tot * 100 - theory) < 1.0, True)

# The region is inside the checksum, so naming the wrong one fails the same
# check. This is what stops an address minted in Ireland resolving in Britain.
caught = tot = 0
for lat, lng in sample('IE', 2000):
    a = g.encode(lat, lng, WORDS, g.MAX_WORDS, 'IE')
    tot += 1
    try:
        g.decode(a, WORDS, 'GB')
    except ValueError:
        caught += 1
print(f'  ----  the wrong region is rejected {caught/tot*100:.1f}% (theory {theory:.2f}%)')
check('wrong-region detection is within a point of theory',
      abs(caught / tot * 100 - theory) < 1.0, True)

check('a valid 4-word address always passes its own checksum',
      all(g.decode(g.encode(lat, lng, WORDS, g.MAX_WORDS, c), WORDS, c) is not None
          for c in SPREAD for lat, lng in sample(c, 100)), True)
check('1-3 word addresses decode without a checksum',
      all(g.decode(g.encode(lat, lng, WORDS, n, 'GB'), WORDS, 'GB') is not None
          for n in (1, 2, 3) for lat, lng in sample('GB', 100)), True)

print('\ncoverage')
# Outside a region there is no address, and inventing one is worse than
# refusing: decode maps onto the box, so an outside point aliases onto a real
# address inside it and passes the checksum, which covers the address and the
# region but not where the caller was standing.
outside = [(48.8566, 2.3522), (40.4168, -3.7038), (40.7128, -74.0060),
           (-33.8688, 151.2093), (64.1466, -21.9426), (0.0, 0.0)]
refused = 0
for lat, lng in outside:
    try:
        g.encode(lat, lng, WORDS, g.MAX_WORDS, 'GB')
    except g.OutsideBox:
        refused += 1
check('a coordinate outside the region is refused, not aliased', refused, len(outside))

corners = []
for code in SPREAD:
    latMin, latMax, lngMin, lngMax = g.REGIONS[code]['box']
    for lat in (latMin, latMax):
        for lng in (lngMin, lngMax):
            corners.append((code, lat, (lng + 180.0) % 360.0 - 180.0))
check('every box corner still encodes',
      all(len(g.encode(lat, lng, WORDS, g.MAX_WORDS, c)) == g.MAX_WORDS
          for c, lat, lng in corners), True)
# A corner sits exactly on a cell boundary, where rounding can land the index
# one past either end; both ends are clamped, so a corner round trips.
check('every box corner round trips inside one cell diagonal',
      all(proj_err((lat, lng),
                   g.decode(g.encode(lat, lng, WORDS, g.MAX_WORDS, c), WORDS, c))
          < math.hypot(*g.cell_size(g.MAX_WORDS, c)) for c, lat, lng in corners), True)
try:
    g.encode(51.5, -0.12, WORDS, 4, 'ZZ')
    check('an unknown region code is refused', False, True)
except g.UnknownRegion:
    check('an unknown region code is refused', True, True)

print('\nthe antimeridian')
# Fiji's box runs 176.9 to 182.0, so a point there arrives as -179 and must be
# read as 181. Without normalisation the box would span the globe instead.
check('boxes past 180 exist in the registry',
      any(r['box'][3] > 180 for r in g.REGIONS.values()), True)
check('FJ covers a point on the far side of the antimeridian',
      g.covers(-16.5, -179.9, 'FJ'), True)
check('such a point round trips',
      hav((-16.5, -179.9),
          g.decode(g.encode(-16.5, -179.9, WORDS, 4, 'FJ'), WORDS, 'FJ'))
      < math.hypot(*g.cell_size(4, 'FJ')), True)

print('\naddress strings')
a = g.format_address('GB', g.encode(51.50072, -0.12456, WORDS, 4, 'GB'))
check('format is region-first, dot separated', a.startswith('GB.') and a.count('.') == 4, True)
check('parse round trips', g.parse_address(a), ('GB', a.split('.')[1:]))
check('parse accepts spaces and lower case',
      g.parse_address('gb plug curtain'), ('GB', ['plug', 'curtain']))

print()
w, h = g.cell_size(g.MAX_WORDS, 'GB')
print(f'  ----  GB: 4 words is {math.sqrt(w*h):.2f} m; '
      f'3 words alone is {math.sqrt(math.prod(g.cell_size(3, "GB"))):.2f} m')
print(f'  ----  {len(g.REGIONS)} regions in the registry')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
