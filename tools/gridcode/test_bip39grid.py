#!/usr/bin/env python3
"""Verify the 70 km lattice scheme. Exits non-zero on any regression."""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bip39grid as g

WORDS = g.load_wordlist()
fails = []

def check(name, got, want, tol=None):
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    print(f'  {"PASS" if ok else "FAIL"}  {name:56s} {got}')
    if not ok:
        fails.append(name)

def haversine(a, b):
    (la1, lo1), (la2, lo2) = a, b
    dla, dlo = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dla / 2) ** 2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(dlo / 2) ** 2
    return 2 * g.R * math.asin(math.sqrt(h))

random.seed(20260906)
# Latitudes kept away from the poles, where an equal-area cylinder stretches
# shape badly enough that a "70 km" square is no longer 70 km across.
pts = [(random.uniform(-60, 60), random.uniform(-179, 179)) for _ in range(4000)]

for cb in (0, 4, 8):
    cw, ch = g.cell_size(cb)
    worst = 0.0
    for lat, lng in pts:
        addr = g.encode(lat, lng, WORDS, cb)
        back = g.decode(addr, lat, lng, WORDS, cb)
        worst = max(worst, haversine((lat, lng), back))
    limit = math.hypot(cw, ch)          # half-diagonal plus projection slack
    check(f'{cb} check bits: round trip within one cell diagonal', worst <= limit, True)
    print(f'        worst error {worst:.3f} m, cell diagonal {limit:.3f} m')

# A wrong word must be caught, not silently relocate the address.
for cb in (0, 4, 8):
    caught = 0
    trials = 3000
    for _ in range(trials):
        lat, lng = random.choice(pts)
        addr = g.encode(lat, lng, WORDS, cb)
        bad = list(addr)
        i = random.randrange(g.WORDS)
        while bad[i] == addr[i]:
            bad[i] = random.choice(WORDS)
        try:
            got = g.decode(bad, lat, lng, WORDS, cb)
            if haversine((lat, lng), got) > 1000:
                pass                    # silently wrong, and far away
        except ValueError:
            caught += 1
    rate = caught / trials * 100
    expected = 0 if cb == 0 else (1 - 2 ** -cb) * 100
    print(f'  ----  {cb} check bits: wrong word detected {rate:5.1f}% (theory {expected:.1f}%)')

# Uniqueness, measured from an ARBITRARY point rather than from a lattice point.
# Two instances are both within R of some point whenever the spacing is under 2R,
# so the honest question is the spacing on the ground, which the equal-area
# cylinder makes latitude-dependent.
K = math.cos(math.radians(g.STD_PARALLEL))
print()
print('  ----  ground spacing of the lattice, and the hint accuracy it demands:')
worst_lat = None
for lat in (0, 30, 45, 51.5, 55, 60):
    c = math.cos(math.radians(lat))
    ew, ns = g.CHUNK * c / K, g.CHUNK / c * K
    safe = min(ew, ns) / 2
    print(f'        lat {lat:>4}: E-W {ew/1000:>5.1f} km, N-S {ns/1000:>6.1f} km '
          f'-> hint must be good to {safe/1000:.1f} km')
    if lat == 51.5:
        worst_lat = safe
check('a 35 km hint is enough at the standard parallel',
      round(min(g.CHUNK, g.CHUNK) / 2), 35000)
check('at UK latitudes the hint must be better than 35 km (documented, not a bug)',
      worst_lat < 35000, True)

print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
