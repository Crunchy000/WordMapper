#!/usr/bin/env python3
"""Exercise every failure mode of the codec. Exits non-zero on any regression."""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wordcode as wc

N = 2809
AZ = 'abcdefghijklmnopqrstuvwxyz'
fails = []

def check(name, got, want):
    ok = got == want
    print(f'  {"PASS" if ok else "FAIL"}  {name:52s} {got}')
    if not ok:
        fails.append(f'{name}: got {got}, want {want}')

random.seed(20260905)

# --- the code is nested: 4-word address is a prefix of the 5-word one ---------
nested = all(wc.encode(d := random.sample(range(N), 3), 1) == wc.encode(d, 2)[:4]
             for _ in range(5000))
check('4-word address is a prefix of the 5-word one', nested, True)

# --- clean round trip ---------------------------------------------------------
for checks in (1, 2):
    ok = 0
    for _ in range(5000):
        d = random.sample(range(N), 3)
        cw = wc.encode(d, checks)
        out, st = wc.decode(cw)
        if st == 'ok' and out == cw: ok += 1
    check(f'{3+checks} words, clean input accepted', ok, 5000)

# --- single erasure: correctable at both lengths ------------------------------
for checks in (1, 2):
    ok = 0
    n = 3 + checks
    for _ in range(5000):
        d = random.sample(range(N), 3)
        cw = wc.encode(d, checks)
        pos = random.randrange(n)
        recv = list(cw); recv[pos] = None
        out, st = wc.decode(recv)
        if st == 'corrected' and out == cw: ok += 1
    check(f'{n} words, 1 erasure corrected', ok, 5000)

# --- single error, unknown position -------------------------------------------
det = 0
for _ in range(5000):
    d = random.sample(range(N), 3)
    cw = wc.encode(d, 1)
    pos = random.randrange(4)
    bad = list(cw)
    while bad[pos] == cw[pos]: bad[pos] = random.randrange(N)
    _, st = wc.decode(bad)
    if st == 'detected': det += 1
check('4 words, 1 error detected (cannot locate)', det, 5000)

cor = 0
for _ in range(5000):
    d = random.sample(range(N), 3)
    cw = wc.encode(d, 2)
    pos = random.randrange(5)
    bad = list(cw)
    while bad[pos] == cw[pos]: bad[pos] = random.randrange(N)
    out, st = wc.decode(bad)
    if st == 'corrected' and out == cw: cor += 1
check('5 words, 1 error CORRECTED at unknown position', cor, 5000)

# --- word-order swaps must not pass silently ----------------------------------
for checks in (1, 2):
    caught = 0
    for _ in range(5000):
        d = random.sample(range(N), 3)
        cw = wc.encode(d, checks)
        i, j = random.sample(range(3), 2)
        sw = list(cw); sw[i], sw[j] = sw[j], sw[i]
        out, st = wc.decode(sw)
        if st != 'ok': caught += 1
    check(f'{3+checks} words, swapped word order not silently accepted', caught, 5000)

# --- end to end on real words: every single-character typo --------------------
words = wc.load_words()
good = tot = 0
for _ in range(200):
    three = random.sample(words, 3)
    addr = wc.encode_words(three, words, 1)
    for pos in range(4):
        w = addr[pos]
        for i in range(len(w)):
            for c in AZ:
                if c == w[i]: continue
                spoken = list(addr); spoken[pos] = w[:i] + c + w[i+1:]
                out, st = wc.decode_words(spoken, words)
                tot += 1
                if out == addr: good += 1
check(f'4 words, every single typo auto-corrected ({tot:,} cases)', good, tot)

print()
if fails:
    print(f'{len(fails)} FAILURE(S)'); [print('  ' + f) for f in fails]; sys.exit(1)
print('all checks passed')
