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

# The check word must catch wrong words and wrong lengths.
caught = tot = 0
for lat, lng in pts[:1500]:
    n = random.randint(2, 4)
    a = g.encode(lat, lng, WORDS, n)
    c = g.check_word(a, WORDS)
    bad_a = list(a)
    i = random.randrange(n)
    while bad_a[i] == a[i]:
        bad_a[i] = random.choice(WORDS)
    tot += 1
    if not g.verify(bad_a, c, WORDS):
        caught += 1
print(f'  ----  check word rejects a wrong word: {caught/tot*100:.1f}% '
      f'(theory {(1 - 1/2048)*100:.2f}%)')

wrong_len = sum(1 for lat, lng in pts[:500]
                if not g.verify(g.encode(lat, lng, WORDS, 3),
                                g.check_word(g.encode(lat, lng, WORDS, 4), WORDS), WORDS))
check('check word is length-specific', wrong_len, 500)

check('a valid address round trips its own check word',
      all(g.verify(a, g.check_word(a, WORDS), WORDS)
          for a in (g.encode(lat, lng, WORDS, 3) for lat, lng in pts[:500])), True)

print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
