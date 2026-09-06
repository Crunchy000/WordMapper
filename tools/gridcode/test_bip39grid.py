#!/usr/bin/env python3
"""Verify the truncatable address scheme. Exits non-zero on any regression."""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

WORDS = g.load_wordlist()
fails = []

def check(name, got, want):
    ok = got == want
    print(f'  {"PASS" if ok else "FAIL"}  {name:58s} {got}')
    if not ok:
        fails.append(name)

def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    dla, dlo = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dla/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlo/2)**2
    return 2 * g.R * math.asin(math.sqrt(h))

random.seed(20260906)
pts = [(random.uniform(g.BOX['latMin']+.2, g.BOX['latMax']-.2),
        random.uniform(g.BOX['lngMin']+.2, g.BOX['lngMax']-.2)) for _ in range(4000)]

# The property the whole design rests on.
bad = 0
for lat, lng in pts:
    a = [g.encode(lat, lng, WORDS, n) for n in range(1, g.MAX_WORDS + 1)]
    for i in range(len(a) - 1):
        if a[i + 1][:len(a[i])] != a[i]:
            bad += 1
check('every address is a prefix of the next longer one', bad, 0)

# Round trip at each length, within the cell it names.
for n in range(1, g.MAX_WORDS + 1):
    w, h = g.cell_size(n)
    limit = math.hypot(w, h)
    worst = max(hav((lat, lng), g.decode(g.encode(lat, lng, WORDS, n), WORDS))
                for lat, lng in pts[:800])
    check(f'{n} words: round trip inside one cell diagonal', worst <= limit, True)
    print(f'        cell {w:.3f} x {h:.3f} m, worst error {worst:.3f} m')

# No repeats: distinct points that share an address must be in the same cell.
for n in (2, 3):
    seen, dupes = {}, 0
    w, h = g.cell_size(n)
    for lat, lng in pts:
        k = '.'.join(g.encode(lat, lng, WORDS, n))
        if k in seen and hav((lat, lng), seen[k]) > math.hypot(w, h):
            dupes += 1
        seen.setdefault(k, (lat, lng))
    check(f'{n} words: no address repeats anywhere in the box', dupes, 0)

# The fourth word carries the checksum, so a wrong word must be rejected.
caught = tot = 0
for lat, lng in pts[:2000]:
    a = g.encode(lat, lng, WORDS, g.MAX_WORDS)
    bad_a = list(a)
    i = random.randrange(g.MAX_WORDS)
    while bad_a[i] == a[i]:
        bad_a[i] = random.choice(WORDS)
    tot += 1
    try:
        g.decode(bad_a, WORDS)
    except ValueError:
        caught += 1
theory = (1 - 2 ** -g.CHECK_BITS) * 100
print(f'  ----  4 words: a wrong word is rejected {caught/tot*100:.1f}% '
      f'(theory {theory:.2f}%, {g.CHECK_BITS} check bits)')
check('detection is within a point of theory', abs(caught/tot*100 - theory) < 1.0, True)

check('a valid 4-word address always passes its own checksum',
      all(g.decode(g.encode(lat, lng, WORDS, g.MAX_WORDS), WORDS) is not None
          for lat, lng in pts[:500]), True)

# Shorter forms carry no checksum and must not be rejected for lacking one.
check('1-3 word addresses decode without a checksum',
      all(g.decode(g.encode(lat, lng, WORDS, n), WORDS) is not None
          for n in (1, 2, 3) for lat, lng in pts[:200]), True)

# Outside the box there is no address, and inventing one is worse than
# refusing: decode maps onto the box, so an outside point aliases onto a real
# address inside it and passes the checksum, which covers the address rather
# than the caller's position. Before this was guarded, 99.7% of out-of-box
# points minted a checksum-valid address for somewhere else -- Sydney landed
# in the North Sea, 17,790 km out.
outside = [(48.8566, 2.3522), (40.4168, -3.7038), (40.7128, -74.0060),
           (-33.8688, 151.2093), (64.1466, -21.9426), (0.0, 0.0),
           (49.84, -2.0), (60.91, -2.0), (55.0, -11.01), (55.0, 1.81)]
refused = 0
for lat, lng in outside:
    try:
        g.encode(lat, lng, WORDS, g.MAX_WORDS)
    except g.OutsideBox:
        refused += 1
check('a coordinate outside the box is refused, not aliased', refused, len(outside))

# The corners are inclusive, and must still encode rather than trip the guard.
corners = [(g.BOX['latMin'], g.BOX['lngMin']), (g.BOX['latMin'], g.BOX['lngMax']),
           (g.BOX['latMax'], g.BOX['lngMin']), (g.BOX['latMax'], g.BOX['lngMax'])]
check('the box corners still encode',
      all(len(g.encode(lat, lng, WORDS, g.MAX_WORDS)) == g.MAX_WORDS
          for lat, lng in corners), True)

# A corner sits exactly on a cell boundary, where rounding can land the index
# one past either end. Both ends are clamped, so a corner round trips.
check('the box corners round trip inside one cell diagonal',
      max(hav((lat, lng), g.decode(g.encode(lat, lng, WORDS, g.MAX_WORDS), WORDS))
          for lat, lng in corners) < math.hypot(*g.cell_size(g.MAX_WORDS)), True)

w, h = g.cell_size(g.MAX_WORDS)
print(f'  ----  4 words: {math.sqrt(w*h):.2f} m with {g.REFINE_BITS} refine + '
      f'{g.CHECK_BITS} check bits (3 words alone is {math.sqrt(math.prod(g.cell_size(3))):.2f} m)')

print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
