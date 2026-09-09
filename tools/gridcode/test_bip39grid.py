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


def _decodes(spoken):
    try:
        g.decode(spoken, WORDS)
        return True
    except ValueError:
        return False


def in_box(box, n):
    """Random points inside a box, in real -180..180 longitude."""
    latMin, latMax, lngMin, lngMax = box
    return [(random.uniform(latMin, latMax),
             (random.uniform(lngMin, lngMax) + 180.0) % 360.0 - 180.0)
            for _ in range(n)]



print('\nthe grid')
check('every point on earth encodes',
      all(len(g.encode(lat, lng, WORDS)) == g.GLOBAL.max_words for lat, lng in PTS), True)
check('the poles and the antimeridian encode',
      all(len(g.encode(lat, lng, WORDS)) == g.GLOBAL.max_words
          for lat in (-90, -89.999, 0, 89.999, 90)
          for lng in (-180, -179.999, 0, 179.999, 180)), True)
# The projected world is square and both axes get the same base-36 splits, so
# every cell at every length is exactly square -- there is nothing to arrange.
# The old binary layout needed a greedy bit order for this and still left the
# odd lengths at 2:1.
check('the frame is square', round(g.GLOBAL.xr / g.GLOBAL.yr, 9), 1.0)
check('cells are exactly square at every length',
      [round(max(w, h) / min(w, h), 9)
       for w, h in (g.cell_size(n) for n in range(1, g.GLOBAL.max_words + 1))],
      [1.0] * g.GLOBAL.max_words)
check('the list is RADIX squared', g.LIST_SIZE, g.RADIX ** 2)
# Every word spends its LIST_SIZE values on position and check, exactly: a
# word that splits r x r keeps r**2 for position and LIST_SIZE//r**2 for check,
# and nothing is left over anywhere.
check('every word spends exactly its list on position and check',
      [r * r * c for r, c in zip(g.GLOBAL.splits, g.GLOBAL.checks)],
      [g.LIST_SIZE] * g.GLOBAL.max_words)
check('the checks multiply out to the whole checksum',
      math.prod(g.GLOBAL.checks), g.CHECK)
# Each length's check is a genuine PREFIX of the next one's, not a different
# function near it: the digits go least-significant first, so the modulus at n
# words divides the modulus at n+1. That is what lets a shorter address be
# verified at all, and lets a longer one only ever strengthen it.
check('each length\'s check divides the next one\'s',
      [math.prod(g.GLOBAL.checks[:n + 1]) % math.prod(g.GLOBAL.checks[:n])
       for n in range(1, g.GLOBAL.max_words)], [0] * (g.GLOBAL.max_words - 1))
check('check digits round-trip through undigits',
      all(g._undigits_check(g._check_digits(v, g.GLOBAL.checks), g.GLOBAL.checks) == v
          for v in (random.randrange(g.CHECK) for _ in range(2000))), True)

# Digits round-trip, which is the whole of the addressing: there is no
# interleaving left to get wrong.
check('digits round-trip through undigits',
      all(g._undigits(g._digits(i, g.GLOBAL.splits), g.GLOBAL.splits) == i
          for i in (xi for lat, lng in PTS[:500]
                    for xi in g._indices(lat, lng))), True)

print('\ntrailing words: coarser, no context needed')
bad = 0
for lat, lng in PTS[:1500]:
    full = g.encode(lat, lng, WORDS)
    for n in range(1, g.GLOBAL.max_words):
        if g.encode(lat, lng, WORDS, n) != full[:n]:
            bad += 1
check('every address is a prefix of the next longer one', bad, 0)

for n in range(1, g.GLOBAL.max_words + 1):
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
# Below two words the only word said is the pure-check one, which pins down no
# position at all: every cell on earth is a candidate, so there is nothing for a
# reference to choose between and no tile to be inside.
for n in range(2, g.GLOBAL.max_words):
    tw, th = g.tile_size(n)
    # Offset the reference in index space, by strictly less than half the
    # ambiguity period on each axis. That is exactly the guarantee -- nearer
    # than half a tile -- stated in the units the reconstruction works in, so
    # index truncation cannot eat the margin at the smallest tiles.
    period = g._known_period(n)
    div = g.GLOBAL.div
    ok = True
    for lat, lng in PTS[:400]:
        full = g.encode(lat, lng, WORDS)
        xi, yi = g._indices(lat, lng)
        slack = period // 2 - 1
        rx = (xi + random.randint(-slack, slack)) % div
        ry = min(max(yi + random.randint(-slack, slack), 0), div - 1)
        ref = g.unproject(g.GLOBAL.x0 + (rx + 0.5) / div * g.GLOBAL.xr,
                          g.GLOBAL.y0 + (ry + 0.5) / div * g.GLOBAL.yr)
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
theory = (1 - 1 / g.CHECK) * 100
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
      f'(theory {theory:.2f}%, 1 of {g.CHECK} check values)')
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
          f'{g.format_address(g.encode(*BIG_BEN, WORDS)[-n:], tail=n < g.GLOBAL.max_words)}')

print('\nthe checksum')
caught = tot = 0
for lat, lng in PTS[:2000]:
    a = g.encode(lat, lng, WORDS)
    bad_a = list(a)
    i = random.randrange(g.GLOBAL.max_words)
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
          for n in range(1, g.GLOBAL.max_words) for lat, lng in PTS[:120]), True)

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

print('\nthe antimeridian')
# The box does not cross 180, but tail resolution still has to wrap: a reference
# just west of the seam is a whole world away in index terms.
check('a point either side of the seam encodes',
      all(len(g.encode(lat, lng, WORDS)) == g.GLOBAL.max_words
          for lat, lng in [(-16.5, 179.99), (-16.5, -179.99), (0.0, 180.0), (0.0, -180.0)]), True)
near = g.encode(-16.50, -179.99, WORDS)
# Say enough words that the reference, 2 km away on the ground, is inside the
# tile the dropped ones leave -- otherwise this measures the reference being
# too far away rather than the wrap being handled.
said = next(n for n in range(1, g.GLOBAL.max_words + 1)
            if max(g.tile_size(n)) > 4000)
check('a global tail resolves from the far side of the seam',
      proj_err((-16.50, -179.99),
               g.resolve_tail(near[-said:], WORDS, -16.49, 179.99))
      < math.hypot(*g.cell_size(g.GLOBAL.max_words)), True)

print('\nthe whole earth, and only the whole earth')
check('every point on earth is covered',
      all(g.covers(lat, lng) for lat, lng in PTS), True)
check('the poles and the seam are covered',
      all(g.covers(lat, lng) for lat, lng in
          [(-90.0, 0.0), (90.0, 0.0), (0.0, 180.0), (0.0, -180.0)]), True)
# Clamping is at BOTH ends. The top saturates a point on the boundary into the
# last cell; the bottom is only reachable by floating-point slop, but an
# unclamped negative index would mint a plausible address for the wrong place
# -- which is exactly the bug regional boxes used to have outside them, and the
# reason there is now nothing outside.
check('an index is never negative and never past the end',
      all(0 <= xi < g.GLOBAL.div and 0 <= yi < g.GLOBAL.div
          for xi, yi in (g._indices(lat, lng) for lat, lng in
                         PTS + [(-90.0, -180.0), (90.0, 180.0)])), True)
check('there is exactly one scope', sorted(g.SCOPES), ['global'])

print('\nthe checksum at every length')
# The checksum is over the WHOLE position, so nothing about it can be verified
# until the whole position is. Word six adds no position, so five words already
# reach full depth -- which is why verification starts there and not at six.
import math as _m
for n in range(1, g.GLOBAL.max_words + 1):
    full_depth = g.GLOBAL.divisions(n) == g.GLOBAL.div
    mod = _m.prod(g.GLOBAL.checks[:n]) if full_depth else 1
    print(f'  ----  {n} words: {g.cell_size(n)[0]:>10,.2f} m, '
          + (f'checked 1 in {mod:,}' if mod > 1 else 'unverified'))
check('verification starts exactly where the position reaches full depth',
      [g.GLOBAL.divisions(n) == g.GLOBAL.div for n in range(1, g.GLOBAL.max_words + 1)],
      [False] * (g.GLOBAL.max_words - 2) + [True, True])
check('the full address is checked to one in CHECK', _m.prod(g.GLOBAL.checks), g.CHECK)

# There is nothing left to shorten AGAINST. The country box search is gone: it
# bought a word at the cost of a network call, an inconsistent word count, and
# detection -- every candidate the box left was a fresh lottery against the same
# checksum. Saying the sixth word costs less than that and is the same every
# time. What remains is a reference POINT, which tests ONE candidate and so
# costs no detection at all.
check('no box search survives',
      [n for n in dir(g) if 'box' in n or n in ('MAX_CANDIDATES', 'FLOOR')], [])

print('\ncity-root phrases (experimental)')
CITIES = [
    ('London', 51.5074, -0.1278),
    ('Paris', 48.8566, 2.3522),
    ('New York', 40.7128, -74.0060),
]
BIG_BEN = (51.50072, -0.12456)
root, tail = g.encode_city_phrase(*BIG_BEN, WORDS, CITIES, city_radius_m=30000)
check('closest city is the phrase root', root, 'London')
city_scope = g.city_phrase_scope(CITIES[0], 30000, n_words=3)
got = g.decode_city_phrase(root, tail, WORDS, CITIES, city_radius_m=30000)
check('city root + 3 words round-trips to the same local cell',
      g._indices(*got, city_scope) == g._indices(*BIG_BEN, city_scope), True)
try:
    g.encode_city_phrase(51.40, -0.50, WORDS, CITIES, city_radius_m=2000)
    ok = False
except ValueError:
    ok = True
check('too-small city radius is rejected', ok, True)
try:
    g.encode_city_phrase(-55.0, -140.0, WORDS, CITIES, max_city_radius_m=1000)
    ok = False
except ValueError:
    ok = True
check('max city search radius is enforced', ok, True)
try:
    g.decode_city_phrase('Atlantis', tail, WORDS, CITIES, city_radius_m=30000)
    ok = False
except ValueError:
    ok = True
check('unknown city names are rejected', ok, True)

print()
w, h = g.cell_size(g.GLOBAL.max_words)
print(f'  ----  {g.GLOBAL.max_words} words is {w:.2f} x {h:.2f} m; '
      f'{g.GLOBAL.max_words - 1} words alone is '
      f'{math.sqrt(math.prod(g.cell_size(g.GLOBAL.max_words - 1))):.2f} m')
print('  ----  one grid, one address for a place, and always the same six words')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
