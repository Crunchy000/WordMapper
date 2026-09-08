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
# The five-word check is a genuine PREFIX of the six-word one, not a different
# function near it -- which is what keeps every address already in circulation
# valid. 144 divides 186,624, and the check digits go least-significant first.
check('the sixth word only ever adds to the fifth', g.CHECK % 144, 0)
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

print('\nshortening against a country box')
# The other way to fill in dropped leading words. resolve_tail() needs a nearby
# POINT; this needs only a REGION, and lets the checksum pick. A country name is
# such a region, and OpenStreetMap will hand you its bounding box. The box is
# never part of the address -- it is a search window -- so the properties worth
# pinning down are about what a WRONG window costs.
BOXES = {                       # as Nominatim returns them: south, north, west, east
    'Luxembourg':     (49.447, 50.183, 5.735, 6.531),
    'Switzerland':    (45.818, 47.808, 5.956, 10.492),
    'Ireland':        (51.222, 55.636, -11.017, -5.066),
    'United Kingdom': (49.674, 61.061, -14.015, 2.096),
    'France':         (41.303, 51.124, -5.559, 9.662),
    'Australia':      (-43.644, -9.221, 112.921, 159.109),
    'United States':  (18.910, 71.441, -179.231, 179.859),
}
IN_UK = [(51.50072, -0.12456), (55.94859, -3.19951), (54.59730, -5.93010),
         (50.06569, -5.71531), (57.47780, -4.22470)]
# "The country supplies one word" is max_words - 1 said, whatever the address
# length happens to be. Writing 4 here was right once and silently wrong after.
SAY = g.GLOBAL.max_words - 1

check('the true point is never lost from the search',
      all(g.candidates_in_box(g.encode(la, lo, WORDS)[-SAY:], WORDS,
                              BOXES['United Kingdom'])[0] is not None
          and g._indices(la, lo) in
          [g._indices(a, b) for a, b in
           g.candidates_in_box(g.encode(la, lo, WORDS)[-SAY:], WORDS,
                               BOXES['United Kingdom'])[0]]
          for la, lo in IN_UK), True)

# HOW MANY WORDS A BOX BUYS is one number: how many candidate tiles it holds.
# Each word is 11 bits, so one fewer word is 2048 times as many tiles, and 7
# check bits leave one in 128 standing. So a length works exactly when no OTHER
# candidate survives -- a Poisson zero at rate (tiles - 1)/128. Nothing about
# countries enters into it; a country is just a box someone else drew.
# HOW MANY WORDS A BOX BUYS is one number: how many candidate tiles it holds.
# Each word is 11 bits, so one fewer word is 2048 times as many tiles, and 7
# check bits leave one in 128 standing. Uniqueness is then a Poisson zero at
# rate (tiles - 1)/128. Nothing about countries enters into it; a country is
# just a box someone else drew.
#
# But uniqueness is NOT the whole test, because the same k candidates are also
# k lotteries against the same check when a word is wrong. So shortening is
# capped at MAX_CANDIDATES, and these two are measured separately: the law
# below, and the detection it costs further down.
said, tiles, over_cap = {}, {}, []
for name, box in BOXES.items():
    pts = in_box(box, 60)
    said[name] = [g.shortest_in_box(la, lo, WORDS, box)[0] for la, lo in pts]
    ks = [g.candidates_in_box(g.encode(la, lo, WORDS)[-SAY:], WORDS, box)[1]
          for la, lo in pts]
    tiles[name] = sum(ks) / len(ks)
    # The cap is per point, not per country: a box averaging under it still has
    # corners where the window is wider, and those points say every word.
    over_cap += [(name, k) for n, k in zip(said[name], ks)
                 if n < g.GLOBAL.max_words and k > g.MAX_CANDIDATES]
    # The same points on both sides, so this compares the rule against the
    # measurement rather than against a second sample of it.
    unique = sum(1 for la, lo in pts
                 if len(g.candidates_in_box(
                     g.encode(la, lo, WORDS)[-SAY:], WORDS, box)[0] or []) == 1)
    unique = unique / len(pts) * 100
    poisson = sum(math.exp(-(k - 1) / g.CHECK) for k in ks) / len(ks) * 100
    four = sum(1 for n in said[name] if n <= SAY) / len(said[name]) * 100
    print(f'  ----  {name}: {tiles[name]:6.1f} tiles, unique {unique:3.0f}% '
          f'(poisson {poisson:3.0f}%), shortens {four:3.0f}%')
    check(f'{name} uniqueness matches the Poisson law', abs(unique - poisson) < 12, True)

# The cap, not luck, is what decides. This is the safety property itself: no
# address is ever shortened against a window too wide to screen it, however
# temptingly unique the survivor looked.
check('no address is shortened against a window over the cap', over_cap, [])
check('a box comfortably under the cap always buys a word',
      all(n <= SAY for name in ('Luxembourg', 'Switzerland', 'Ireland')
          for n in said[name]), True)
# A 186,624-value check screens a far wider window than a 144-value one did, so
# the small countries now buy TWO words rather than one, and the big ones buy
# their first. Nothing here is over the cap, which is the point: at this check
# strength a country-sized box is simply not a hard problem any more.
check('every country box buys at least one word',
      max(n for name in BOXES for n in said[name]) <= SAY, True)
check('the small countries can buy two',
      min(n for name in ('Luxembourg', 'Switzerland', 'Ireland')
          for n in said[name]), g.GLOBAL.max_words - 2)
check('Australia and the United States now buy one, where 144 refused them',
      (set(said['Australia']), set(said['United States'])), ({SAY}, {SAY}))

# WHAT THE CAP IS FOR. A wrong word removes the true tile, so all k candidates
# are lotteries against the same 7 check bits and detection falls to
# (127/128)**k. Uncapped over Australia that is 58%, and a third of mishearings
# would resolve silently to the wrong place inside the country -- the worst
# failure there is, because it looks like an answer.
def mishear(spoken):
    """One word replaced by a different BIP-39 word."""
    out = list(spoken)
    i = random.randrange(len(out))
    while True:
        w = random.choice(WORDS)
        if w != out[i]:
            out[i] = w
            return out


for name in ('Ireland', 'United Kingdom', 'France'):
    box = BOXES[name]
    caught = trials = 0
    for la, lo in in_box(box, 250):
        n, tail = g.shortest_in_box(la, lo, WORDS, box)
        if n == g.GLOBAL.max_words:
            continue
        trials += 1
        try:
            g.decode_in_box(mishear(tail), WORDS, box)
        except ValueError:
            caught += 1
    rate = caught / trials * 100
    print(f'  ----  {name}: a misheard word in a shortened address is caught '
          f'{rate:.0f}% of the time ({trials} shortened)')
    check(f'{name} still catches a wrong word 93% of the time', rate > 93, True)

check('the full address is better than either, and unaffected',
      sum(1 for _ in range(400)
          if not _decodes(mishear(g.encode(*PTS[_], WORDS)))) / 400 > 0.97, True)

# The reader's half. A window too big to screen is refused rather than answered
# from, so an address that should never have been shortened cannot be read as
# though it had been. Australia no longer qualifies -- 45 tiles is comfortably
# inside a 935 cap -- so the window has to be the one that genuinely is too
# wide: two words further back, where the same box holds tens of millions.
TOO_WIDE = g.encode(-33.8688, 151.2093, WORDS)[-(SAY - 2):]
_, searched = g.candidates_in_box(TOO_WIDE, WORDS, BOXES['Australia'],
                                  limit=g.MAX_CANDIDATES)
check('such a window is over the cap', searched > g.MAX_CANDIDATES, True)
try:
    g.decode_in_box(TOO_WIDE, WORDS, BOXES['Australia'])
    refused = False
except ValueError:
    refused = True
check('a window over the cap is refused, not answered from', refused, True)
check('a shortened address reads back to the same cell',
      all(g._indices(*g.decode_in_box(
          g.shortest_in_box(la, lo, WORDS, BOXES['United Kingdom'])[1],
          WORDS, BOXES['United Kingdom'])) == g._indices(la, lo)
          for la, lo in IN_UK), True)

# A wrong window costs uniqueness, never correctness. The address itself is
# arithmetic on the coordinates; the country is only consulted to decide how
# much of it can go unsaid.
check('the address does not depend on the box',
      len({tuple(g.encode(51.50072, -0.12456, WORDS)) for _ in BOXES}), 1)
check('a box that excludes the point falls back to the full address',
      all(g.shortest_in_box(la, lo, WORDS, BOXES['France'])[0] == g.GLOBAL.max_words
          for la, lo in IN_UK), True)
# Nominatim reports an antimeridian country inside out (west > east). That box
# reads as most of the planet, which is a useless window but a safe one.
check('an inside-out box costs words, not correctness',
      g.shortest_in_box(-18.14160, 178.44190, WORDS,
                        (-20.68, -12.48, 176.9, -178.1))[0], g.GLOBAL.max_words)

# Whatever tail comes back, saying it inside that box has to land back here.
def lands_back(la, lo, box):
    n, tail = g.shortest_in_box(la, lo, WORDS, box)
    got, _ = g.candidates_in_box(tail, WORDS, box)
    return got is not None and len(got) == 1 and g._indices(*got[0]) == g._indices(la, lo)
check('the shortened form resolves back to the same cell',
      all(lands_back(la, lo, BOXES['United Kingdom']) for la, lo in IN_UK), True)

# A direct look at the 1-in-CHECK rate the whole scheme rests on. Counting the
# survivors of a REAL address no longer measures it: at 186,624 the false
# survivors are so rare that the only thing passing is the true point itself,
# which says nothing. So the check is deliberately set to a value that is NOT
# the true one -- then every survivor is a false positive and the rate is what
# is being measured rather than inferred.
false_pass = searched_total = 0
for la, lo in IN_UK:
    tail = list(g.encode(la, lo, WORDS)[-(SAY - 1):])
    wrong = WORDS[(WORDS.index(tail[-1]) + 1) % g.LIST_SIZE]   # a different check word
    tail[-1] = wrong
    hits, searched = g.candidates_in_box(tail, WORDS, BOXES['United Kingdom'],
                                         limit=10 ** 7)
    false_pass += len(hits)
    searched_total += searched
expected = searched_total / g.CHECK
print(f'  ----  {SAY - 1} words over the UK with a wrong check word: '
      f'{searched_total:,} cells searched across {len(IN_UK)} points, '
      f'{false_pass} pass anyway (expected {expected:.2f} at 1 in {g.CHECK:,})')
# A Poisson count this small can only be bounded, not matched: at an expected
# 0.1 the odds of seeing 4 or more are about one in a hundred thousand.
check('false survivors are as rare as the checksum says',
      false_pass <= max(3, expected * 3), True)
check('a search too big to be worth running is refused, not run',
      g.candidates_in_box(g.encode(51.50072, -0.12456, WORDS)[-(SAY - 2):], WORDS,
                          BOXES['United Kingdom'])[0], None)

print()
w, h = g.cell_size(g.GLOBAL.max_words)
print(f'  ----  {g.GLOBAL.max_words} words is {w:.2f} x {h:.2f} m; '
      f'{g.GLOBAL.max_words - 1} words alone is '
      f'{math.sqrt(math.prod(g.cell_size(g.GLOBAL.max_words - 1))):.2f} m')
print('  ----  one grid, one address for a place; a country buys one word')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
