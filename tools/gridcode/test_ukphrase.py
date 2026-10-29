#!/usr/bin/env python3
"""Checks for the four-word UK phrases. Run: python3 tools/gridcode/test_ukphrase.py"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukphrase as p
import ukgrid as g
from collections import Counter

random.seed(20261029)
fails = []


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
    return 2 * g.R * math.asin(min(1, math.sqrt(h)))


def in_mask(n):
    out = []
    for _ in range(n):
        j, i = divmod(random.choice(g.SQUARES), g.GRID_W)
        out.append(g.unproject(g.X0 + (i + random.random()) * g.SQUARE,
                               g.Y0 + (j + random.random()) * g.SQUARE))
    return out


PTS = in_mask(4000)
PLACES = {
    'Big Ben': (51.50072, -0.12456), 'Edinburgh Castle': (55.94859, -3.19951),
    'Land\'s End': (50.06569, -5.71531), 'Belfast City Hall': (54.59661, -5.93011),
    'Lerwick': (60.15468, -1.14492), 'St Helier, Jersey': (49.18580, -2.10910),
}

print('\nthe lists')
all_words = [w for k in p.LISTS for w in p.LISTS[k]]
check('no word is in two lists', len(all_words), len(set(all_words)))
check('each list is sorted and has no repeats',
      all(p.LISTS[k] == sorted(set(p.LISTS[k])) for k in p.LISTS), True)
check('the slots are adjective noun verb noun', p.PATTERN,
      ('adjective', 'noun', 'verb', 'noun'))

print('\nthe layout')
check('the check is at least 20', p.CHECK >= p.MIN_CHECK, True)
check('one more cell per side would break it',
      len(g.SQUARES) * (p.K + 1) ** 2 * p.MIN_CHECK > p.SPACE, True)
check('the cells and their checks fit', p.USED <= p.SPACE, True)
check('a cell is about 7.5 m', round(p.CELL, 1), 7.5)
check('the halves of the scramble cover every phrase', p.LEFT * p.RIGHT, p.SPACE)

print('\nthe scramble')
check('unscramble undoes scramble',
      all(p.unscramble(p.scramble(v)) == v
          for v in (random.randrange(p.SPACE) for _ in range(20000))), True)
check('scramble undoes unscramble',
      all(p.scramble(p.unscramble(n)) == n
          for n in (random.randrange(p.SPACE) for _ in range(20000))), True)
check('the ends of the space stay inside it',
      all(0 <= p.scramble(v) < p.SPACE and 0 <= p.unscramble(v) < p.SPACE
          for v in (0, 1, p.RIGHT - 1, p.RIGHT, p.SPACE - 1)), True)

print('\nround trip')
check('every point decodes to its own cell',
      all(p.decode_cell(p.encode(la, lo)) == p.cell_at(la, lo) for la, lo in PTS), True)
errs = sorted(hav(q, p.decode(p.encode(*q))) for q in PTS)
print(f'  ----  half of points within {errs[len(errs)//2]:.2f} m of their centre, '
      f'all within {errs[-1]:.2f} m')
check('half within 3.5 m', errs[len(errs) // 2] < 3.5, True)
check('every point within half a cell diagonal (plus 1 %)',
      errs[-1] < p.CELL / math.sqrt(2) * 1.01, True)
cells = {p.cell_at(la, lo) for la, lo in PTS}
check('different cells never share a phrase',
      len({tuple(p.encode(*p.centre_of(c))) for c in cells}), len(cells))
for name, ll in (('Paris', (48.8566, 2.3522)), ('Dublin', (53.3498, -6.2603))):
    try:
        p.encode(*ll)
        check(f'{name} is outside', False, True)
    except g.OutsideUK:
        check(f'{name} is outside', True, True)

print('\na wrong word of the right kind')
refused, landed, tot = 0, [], 20000
for i in range(tot):
    q = PTS[i % len(PTS)]
    a = p.encode(*q)
    k = random.randrange(4)
    bad = list(a)
    while bad[k] == a[k]:
        bad[k] = random.choice(p.LISTS[p.PATTERN[k]])
    try:
        landed.append(hav(q, p.decode(bad)))
    except ValueError:
        refused += 1
landed.sort()
theory = (1 - p.USED / p.SPACE + p.USED / p.SPACE * (1 - 1 / p.CHECK)) * 100
print(f'  ----  refused {refused/tot*100:.2f}% (theory {theory:.2f}%)')
print(f'  ----  the rest land a median {landed[len(landed)//2]/1000:.0f} km away; '
      f'{sum(d < 10e3 for d in landed)} of {len(landed)} within 10 km')
check('refused within a point of theory', abs(refused / tot * 100 - theory) < 1, True)
check('at least 95 %', refused / tot >= 0.94, True)
check('the rest land far away (median over 100 km)', landed[len(landed) // 2] > 100e3, True)

print('\na wrong word of the wrong kind')
bad_kind = 0
for q in PTS[:2000]:
    a = p.encode(*q)
    k = random.randrange(4)
    other = random.choice([x for x in p.LISTS if x != p.PATTERN[k]])
    b = list(a)
    b[k] = random.choice(p.LISTS[other])
    try:
        p.decode(b)
    except ValueError:
        bad_kind += 1
check('always refused: the phrase stops being grammatical', bad_kind, 2000)

print('\nphrase strings')
bb = p.encode(*PLACES['Big Ben'])
check('parse round trips', p.parse_phrase(p.format_phrase(bb)), bb)
check('parse accepts spaces, commas and case',
      p.parse_phrase('  Cheeky, film FOLLOW banana '), ['cheeky', 'film', 'follow', 'banana'])
for bad in (bb[:3], bb + [bb[1]], [bb[1], bb[0], bb[2], bb[3]]):
    try:
        p.decode(bad)
        check(f'{"/".join(bad)} is refused', False, True)
    except ValueError:
        check(f'{"/".join(bad)} is refused', True, True)

print()
for name, ll in PLACES.items():
    print(f'  ----  {name:20s} {" ".join(p.encode(*ll))}')
print(f'\n  ----  {" x ".join(map(str, p.SIZES))} = {p.SPACE:,} phrases; '
      f'{p.K} x {p.K} cells of {p.CELL:.2f} m per 2 km square; check 1 in {p.CHECK}')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
