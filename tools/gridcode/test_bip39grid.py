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


def in_scope(sc, n):
    """Random points inside a scope's box, in real -180..180 longitude."""
    latMin, latMax, lngMin, lngMax = sc.box
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
# The projected world is square, so the axes split evenly at full depth.
check('the frame is square', round(g.GLOBAL.xr / g.GLOBAL.yr, 9), 1.0)
check('the axes split evenly at full depth', (g.GLOBAL.xb, g.GLOBAL.yb), (24, 24))
# Even bit counts land on frame*4**k and odd ones on frame*2*4**k, so with a
# square frame the even lengths are exactly square and the odd ones are 2:1.
# Both terminal lengths -- 48 bits global, 44 local -- are even.
w, h = g.cell_size(g.GLOBAL.max_words)
check('Global: the terminal cell is exactly square', round(max(w, h) / min(w, h), 9), 1.0)
# A regional box has its own aspect and its own parity, so it cannot be made
# exactly square -- the bit order just gets it as close as the box allows.
check('every regional terminal cell is better than 2:1',
      max(max(w, h) / min(w, h)
          for w, h in (g.cell_size(sc.max_words, sc) for sc in g.REGIONS)) < 2.0, True)
check('global cells are exactly square at even lengths',
      [round(max(w, h) / min(w, h), 9)
       for w, h in (g.cell_size(n) for n in (2, 4))], [1.0, 1.0])
worst = max(max(w, h) / min(w, h) for w, h in
            (g.cell_size(n) for n in range(1, g.GLOBAL.max_words + 1)))
check('no cell is worse than 2:1', worst <= 2.0 + 1e-9, True)

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
for n in range(1, g.GLOBAL.max_words):
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
        rx = (xi + random.randint(-(2 ** cx // 2 - 1), 2 ** cx // 2 - 1)) % 2 ** g.GLOBAL.xb
        ry = min(max(yi + random.randint(-(2 ** cy // 2 - 1), 2 ** cy // 2 - 1), 0),
                 2 ** g.GLOBAL.yb - 1)
        ref = g.unproject(g.GLOBAL.x0 + (rx + 0.5) / 2 ** g.GLOBAL.xb * g.GLOBAL.xr,
                          g.GLOBAL.y0 + (ry + 0.5) / 2 ** g.GLOBAL.yb * g.GLOBAL.yr)
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

print('\nthe regional scopes')
theory = (1 - 2 ** -g.CHECK_BITS) * 100
for sc in g.REGIONS:
    pts = in_scope(sc, 600)
    w, h = g.cell_size(sc.max_words, sc)
    ok_prefix = all(g.encode(lat, lng, WORDS, n, sc) ==
                    g.encode(lat, lng, WORDS, sc.max_words, sc)[:n]
                    for lat, lng in pts[:200] for n in range(1, sc.max_words))
    worst = max(proj_err((lat, lng),
                         g.decode(g.encode(lat, lng, WORDS, s=sc), WORDS, sc))
                for lat, lng in pts)
    check(f'{sc.name}: prefix property and round trip',
          ok_prefix and worst < math.hypot(w, h), True)
    print(f'        {sc.max_words} words, {math.sqrt(w*h):>6.2f} m, '
          f'{max(w,h)/min(w,h):.2f}:1, box {sc.xr*sc.yr/1e6:>11,.0f} km2')

check('every region is four words',
      sorted({sc.max_words for sc in g.REGIONS}), [4])
check('every tag is unique',
      len({sc.tag for sc in g.REGIONS}), len(g.REGIONS))

print('\nchoosing a scope from the point')
# Smallest containing box wins, which is both the finest cell and the region a
# person would name -- the boxes are nested where they overlap.
for lat, lng, want in [(51.5007, -0.1246, 'Local'), (53.3498, -6.2603, 'Local'),
                       (54.5973, -5.9301, 'Local'), (60.1550, -1.1450, 'Local'),
                       (-33.8568, 151.2153, 'Australia'), (-12.4634, 130.8456, 'Australia'),
                       (-42.8821, 147.3272, 'Australia'), (-31.9523, 115.8613, 'Australia'),
                       (48.8584, 2.2945, 'Global'), (35.6586, 139.7454, 'Global'),
                       (-22.9519, -43.2105, 'Global'), (20.0, -40.0, 'Global')]:
    got = g.best_scope(lat, lng)
    check(f'{want} is chosen at {lat:.2f},{lng:.2f}', got.name, want)
check('Ireland is inside Local now', g.covers(53.3498, -6.2603, g.LOCAL), True)
check('an ocean point falls back to Global',
      all(g.best_scope(lat, lng) is g.GLOBAL
          for lat, lng in [(20.0, -40.0), (-40.0, -20.0), (0.0, -140.0), (-60.0, 100.0)]), True)
check('there are exactly two regional scopes plus Global',
      ([sc.name for sc in g.REGIONS], g.GLOBAL.max_words), (['Local', 'Australia'], 5))
check('the chosen scope always covers the point',
      all(g.covers(lat, lng, g.best_scope(lat, lng)) for lat, lng in PTS[:1500]), True)
check('every point on earth gets some scope',
      all(len(g.encode(lat, lng, WORDS, s=g.best_scope(lat, lng)))
          in (4, 5) for lat, lng in PTS[:800]), True)

print('\nthe antimeridian')
# No scope box crosses 180 now, but Global's tail resolution still has to wrap:
# a reference just west of the seam is a whole world away in index terms.
check('no scope box runs past 180',
      [sc.name for sc in g.REGIONS + [g.GLOBAL] if sc.box[3] > 180], [])
check('a point either side of the seam encodes globally',
      all(len(g.encode(lat, lng, WORDS)) == 5
          for lat, lng in [(-16.5, 179.99), (-16.5, -179.99), (0.0, 180.0), (0.0, -180.0)]), True)
near = g.encode(-16.50, -179.99, WORDS)
check('a global tail resolves from the far side of the seam',
      proj_err((-16.50, -179.99),
               g.resolve_tail(near[-3:], WORDS, -16.49, 179.99))
      < math.hypot(*g.cell_size(5)), True)

print('\ncoverage and refusal')
# Galway is inside Local now that the box reaches Ireland, so the Atlantic
# west of it stands in as the nearby-but-outside case.
outside = [(48.8566, 2.3522), (40.7128, -74.0060), (-33.8688, 151.2093),
           (53.2700, -12.5000), (64.1466, -21.9426), (0.0, 0.0)]
refused = 0
for lat, lng in outside:
    try:
        g.encode(lat, lng, WORDS, s=g.LOCAL)
    except g.OutsideBox:
        refused += 1
check('Local refuses a coordinate outside its box', refused, len(outside))
check('those same points all have global addresses',
      all(len(g.encode(lat, lng, WORDS)) == 5 for lat, lng in outside), True)
# A box is a rectangle, not a border. Dublin is in Local by design; Boulogne
# comes along with it, because the box's east edge is out in the Channel.
# Worth asserting so nobody reads a box as a claim.
check('a box is a rectangle, not a border (Boulogne is in Local\'s box)',
      g.covers(50.7264, 1.6139, g.LOCAL), True)
# Australia's box stops at 12 S so that NO other country's land falls inside
# it. PNG reaches 11.6 S and Indonesia 10.9 S, both further south than
# Australia's own northern tip, so the cut is what buys the clean box -- at the
# cost of Cape York's tip, the Tiwi Islands and the Torres Strait.
au = g.SCOPES['australia']
for place, lat, lng, want in [('Sydney', -33.86, 151.21, 'Australia'),
                              ('Perth', -31.95, 115.86, 'Australia'),
                              ('Hobart', -42.88, 147.33, 'Australia'),
                              ('Darwin', -12.46, 130.84, 'Australia'),
                              ('Broome', -17.96, 122.24, 'Australia'),
                              ('Bamaga, Cape York', -10.89, 142.39, 'Global'),
                              ('Tiwi Islands', -11.76, 130.63, 'Global'),
                              ('Port Moresby, PNG', -9.44, 147.18, 'Global'),
                              ('Denpasar, Bali', -8.65, 115.22, 'Global'),
                              ('Dili, Timor-Leste', -8.56, 125.56, 'Global')]:
    check(f'{place} is in {want}', g.best_scope(lat, lng).name, want)
check('no neighbour reaches into the Australia box',
      [n for n, la, lo in [('PNG south', -11.63, 145.0), ('Indonesia south', -10.91, 123.0),
                           ('Timor-Leste south', -9.51, 125.0), ('Solomons south', -11.83, 160.0)]
       if g.covers(la, lo, au)], [])

print('\ntelling the scopes apart')
for sc in g.REGIONS:
    caught = tot = 0
    for lat, lng in in_scope(sc, 800):
        a = g.encode(lat, lng, WORDS, s=sc)
        bad_a = list(a)
        i = random.randrange(sc.max_words)
        while bad_a[i] == a[i]:
            bad_a[i] = random.choice(WORDS)
        tot += 1
        try:
            g.decode(bad_a, WORDS, sc)
        except ValueError:
            caught += 1
    check(f'{sc.name}: a wrong word is rejected within a point of theory',
          abs(caught / tot * 100 - theory) < 1.5, True)

# The tag is bound into the checksum, so an address minted in one region must
# not verify in another. With seven regions the reverse also matters: an
# address can be accepted by more than one box by luck, and then it does NOT
# identify itself and the region has to be stated.
amb = tot = 0
for sc in g.REGIONS:
    for lat, lng in in_scope(sc, 400):
        tot += 1
        if len(g.scopes_accepting(g.encode(lat, lng, WORDS, s=sc), WORDS)) > 1:
            amb += 1
expected = (1 - (1 - 2 ** -g.CHECK_BITS) ** (len(g.REGIONS) - 1)) * 100
print(f'  ----  a 4-word address is accepted by more than one scope '
      f'{amb/tot*100:.1f}% of the time (theory {expected:.1f}%)')
check('ambiguity is within a point of theory',
      abs(amb / tot * 100 - expected) < 1.5, True)
check('the minting scope always accepts its own address',
      all(g.SCOPES[sc.key] in g.scopes_accepting(g.encode(lat, lng, WORDS, s=sc), WORDS)
          for sc in g.REGIONS for lat, lng in in_scope(sc, 60)), True)
check('decode_auto identifies every 5-word global address',
      all(g.decode_auto(g.encode(lat, lng, WORDS), WORDS)[2] is g.GLOBAL
          for lat, lng in PTS[:400]), True)

print()
w, h = g.cell_size(g.GLOBAL.max_words)
print(f'  ----  global: 5 words is {w:.2f} x {h:.2f} m; 4 words alone is '
      f'{math.sqrt(math.prod(g.cell_size(4))):.2f} m')
print(f'  ----  {len(g.REGIONS)} regional scopes at 4 words, plus Global at 5')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
