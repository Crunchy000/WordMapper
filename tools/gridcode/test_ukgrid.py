#!/usr/bin/env python3
"""Checks for the three-word UK grid. Run: python3 tools/gridcode/test_ukgrid.py"""
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukgrid as u

WORDS = u.load_wordlist()
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
    return 2 * u.R * math.asin(min(1, math.sqrt(h)))


def in_mask(n):
    """Random points inside squares of the mask, uniform by area."""
    out = []
    for _ in range(n):
        j, i = divmod(random.choice(u.SQUARES), u.GRID_W)
        out.append(u.unproject(u.X0 + (i + random.random()) * u.SQUARE,
                               u.Y0 + (j + random.random()) * u.SQUARE))
    return out


PTS = in_mask(4000)
PLACES = {
    'Big Ben': (51.50072, -0.12456), 'Edinburgh Castle': (55.94859, -3.19951),
    'Land\'s End': (50.06569, -5.71531), 'Belfast City Hall': (54.59661, -5.93011),
    'Cardiff Castle': (51.48216, -3.18108), 'Lerwick': (60.15468, -1.14492),
    'St Mary\'s, Scilly': (49.91432, -6.31515), 'Douglas, Isle of Man': (54.15000, -4.48000),
    'St Helier, Jersey': (49.18580, -2.10910), 'St Peter Port, Guernsey': (49.45580, -2.53570),
    'John o\' Groats': (58.64395, -3.07050), 'Lowestoft Ness': (52.48140, 1.76220),
}

print('\nthe layout')
check('three words are 1296 cubed', u.SPACE, 2_176_782_336)
check('the Feistel halves cover the space exactly', u.HALF ** 2, u.SPACE)
check('the cells fit in the space', u.CELLS <= u.SPACE, True)
check('one more cell per side would not', len(u.SQUARES) * (u.K + 1) ** 2 > u.SPACE, True)
check('a cell is about 11 m', round(u.CELL, 1), 11.4)
check('the mask covers about 280,000 km^2', round(len(u.SQUARES) * 4, -4), 280_000)

print('\nthe projection')
check('project and unproject round-trip to a millimetre',
      all(math.hypot(*(a - b for a, b in zip(u.project(*u.unproject(x, y)), (x, y)))) < 1e-3
          for x, y in ((random.uniform(-6e5, 3.5e5), random.uniform(-6.4e5, 6.7e5))
                       for _ in range(2000))), True)
# Equal-area and close to conformal over the UK: a square stays square. The
# side of a 2 km square measured on the ground, at the far corners of the grid.
worst = 0.0
for i, j in ((0, 0), (u.GRID_W - 1, 0), (0, u.GRID_H - 1), (u.GRID_W - 1, u.GRID_H - 1),
             (243, 320)):
    x, y = u.X0 + i * u.SQUARE, u.Y0 + j * u.SQUARE
    a, b, c = u.unproject(x, y), u.unproject(x + u.SQUARE, y), u.unproject(x, y + u.SQUARE)
    worst = max(worst, abs(hav(a, b) / hav(a, c) - 1))
check('squares stay square to 0.5 % across the whole grid', worst < 0.005, True)

print('\nthe UK')
for name, ll in PLACES.items():
    try:
        got = u.encode(*ll, WORDS)
    except u.OutsideUK:
        got = None
    check(f'{name} has an address', got is not None, True)
for name, ll in (('Paris', (48.8566, 2.3522)), ('Dublin', (53.3498, -6.2603)),
                 ('New York', (40.7128, -74.0060)), ('the North Sea', (56.0, 3.0))):
    try:
        u.encode(*ll, WORDS)
        check(f'{name} is outside', False, True)
    except u.OutsideUK:
        check(f'{name} is outside', True, True)

print('\nround trip')
check('every point decodes to its own cell',
      all(u.value_at(*u.decode(u.encode(la, lo, WORDS), WORDS)) == u.value_at(la, lo)
          for la, lo in PTS), True)
errs = sorted(hav(p, u.decode(u.encode(*p, WORDS), WORDS)) for p in PTS)
half, worst = errs[len(errs) // 2], errs[-1]
print(f'  ----  half of points within {half:.2f} m of their centre, all within {worst:.2f} m')
check('half within 5 m', half < 5, True)
check('every point within half a cell diagonal (plus 1 %)',
      worst < u.CELL / math.sqrt(2) * 1.01, True)
cells = {u.value_at(la, lo) for la, lo in PTS}
check('different cells never share an address',
      len({tuple(u.number_to_words(u.scramble(v), WORDS)) for v in cells}), len(cells))

print('\nthe scramble')
check('unscramble undoes scramble',
      all(u.unscramble(u.scramble(v)) == v
          for v in (random.randrange(u.SPACE) for _ in range(20000))), True)
check('neighbouring cells share no words',
      sum(a == b for v in random.sample(sorted(cells), 500)
          for a, b in zip(u.number_to_words(u.scramble(v), WORDS),
                          u.number_to_words(u.scramble(v + 1), WORDS))) < 5, True)

print('\na wrong word')
refused, landed = 0, []
tot = 20000
for i in range(tot):
    p = PTS[i % len(PTS)]
    a = u.encode(*p, WORDS)
    bad = list(a)
    k = random.randrange(3)
    while bad[k] == a[k]:
        bad[k] = random.choice(WORDS)
    try:
        landed.append(hav(p, u.decode(bad, WORDS)))
    except ValueError:
        refused += 1
landed.sort()
theory = (1 - u.CELLS / u.SPACE) * 100
print(f'  ----  refused {refused/tot*100:.2f}% (theory {theory:.2f}%)')
print(f'  ----  the rest land a median {landed[len(landed)//2]/1000:.0f} km away; '
      f'{sum(d < 10e3 for d in landed)} of {len(landed)} within 10 km')
check('refused within a point of theory', abs(refused / tot * 100 - theory) < 1, True)
check('a wrong word lands far away (median over 100 km)',
      landed[len(landed) // 2] > 100e3, True)
check('rarely within 10 km (under 1 %)', sum(d < 10e3 for d in landed) < 0.01 * len(landed), True)

print('\nthe optional number')
check('quarters and check fill 00 to 99 exactly',
      u.QUARTERS ** 2 * u.DIGIT_CHECK, 100)
check('with the number, every point decodes to its own quarter',
      all(u.value_at(*u.decode_with(u.encode(la, lo, WORDS), WORDS, u.digits_at(la, lo)))
          == u.value_at(la, lo)
          and u.quarter_at(*u.decode_with(u.encode(la, lo, WORDS), WORDS, u.digits_at(la, lo)))
          == u.quarter_at(la, lo) for la, lo in PTS[:2000]), True)
qerrs = sorted(hav(p, u.decode_with(u.encode(*p, WORDS), WORDS, u.digits_at(*p)))
               for p in PTS[:2000])
print(f'  ----  with the number: half within {qerrs[len(qerrs)//2]:.2f} m, '
      f'all within {qerrs[-1]:.2f} m ({u.CELL / u.QUARTERS:.2f} m squares)')
check('with the number, every point within half a quarter diagonal (plus 1 %)',
      qerrs[-1] < u.CELL / u.QUARTERS / math.sqrt(2) * 1.01, True)
check('without it, the words mean exactly what they did',
      all(u.decode_with(u.encode(la, lo, WORDS), WORDS) == u.decode(u.encode(la, lo, WORDS), WORDS)
          for la, lo in PTS[:500]), True)
caught = landed_far = 0
for i in range(10000):
    q = PTS[i % len(PTS)]
    a, d = u.encode(*q, WORDS), u.digits_at(*q)
    bad = list(a)
    k = random.randrange(3)
    while bad[k] == a[k]:
        bad[k] = random.choice(WORDS)
    try:
        u.decode_with(bad, WORDS, d)
    except ValueError:
        caught += 1
theory = (1 - (1 - (1 - u.CELLS / u.SPACE)) / u.DIGIT_CHECK) * 100
print(f'  ----  with the number, a wrong word is refused {caught/100:.2f}% (theory {theory:.2f}%)')
check('with the number, a wrong word is refused at least 95 %', caught >= 9500, True)
worst = 0.0
for q in PTS[:1000]:
    a, d = u.encode(*q, WORDS), u.digits_at(*q)
    for wrong in range(100):
        if wrong == d:
            continue
        try:
            worst = max(worst, hav(q, u.decode_with(a, WORDS, wrong)))
        except ValueError:
            pass
check('a misheard number never lands outside the 11 m cell',
      worst < u.CELL * math.sqrt(2), True)
for text, want in (('interval level adjective', None), ('interval.level.adjective 07', 7),
                   ('interval level adjective forty two', 42),
                   ('Interval, level, adjective, four two', 42),
                   ('interval level adjective oh seven', 7),
                   ('interval level adjective 4 2', 42)):
    check(f'parse {text!r}', u.parse_full(text), (['interval', 'level', 'adjective'], want))
for text in ('interval level adjective 123', 'interval level adjective forty forty', '42'):
    try:
        u.parse_full(text)
        check(f'{text!r} is refused', False, True)
    except ValueError:
        check(f'{text!r} is refused', True, True)
check('no number word is on the word list', bool(u.NUMBER_WORDS & set(WORDS)), False)

print('\naddress strings')
bb = u.encode(*PLACES['Big Ben'], WORDS)
check('parse round trips', u.parse_address(u.format_address(bb)), bb)
check('parse accepts spaces, commas and case',
      u.parse_address('  LEG, tunnel Slam '), ['leg', 'tunnel', 'slam'])
for bad in (bb[:2], bb + ['zoom'], ['notaword'] + bb[1:]):
    try:
        u.decode(bad, WORDS)
        check(f'{bad} is refused', False, True)
    except ValueError:
        check(f'{"/".join(bad)} is refused', True, True)

print()
for name, ll in PLACES.items():
    print(f'  ----  {name:24s} {u.format_address(u.encode(*ll, WORDS), u.digits_at(*ll))}')
print(f'\n  ----  {len(u.SQUARES):,} squares of 2 km, {u.K} x {u.K} cells each, '
      f'cell {u.CELL:.2f} m')
print()
if fails:
    print(f'{len(fails)} FAILURE(S): ' + ', '.join(fails)); sys.exit(1)
print('all checks passed')
