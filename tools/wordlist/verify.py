#!/usr/bin/env python3
"""Independently verify a word list's distinctness guarantees.

Deliberately brute-force: build.py uses a deletion-set index to avoid O(n^2),
so checking every pair here confirms that optimisation rather than trusting it.

    python3 verify.py ../../data/wordlist.json
"""
import json, re, os, subprocess, sys, math

BOX_M2 = 9.92141e11          # UK + Ireland bounding box


def levenshtein(a, b):
    if abs(len(a) - len(b)) > 1:
        return 2             # only ever asked "is this <= 1?"
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main(path):
    words = json.load(open(path))
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        cmu = json.loads(subprocess.check_output(
            ['node', '-e',
             "console.log(JSON.stringify(require('cmu-pronouncing-dictionary').dictionary))"],
            cwd=here))
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(f'Missing npm packages. Run:  npm install --prefix {here}')

    problems = []
    if len(words) != len(set(words)):
        problems.append('list contains duplicates')
    missing = [w for w in words if w not in cmu]
    if missing:
        problems.append(f'{len(missing)} words have no pronunciation: {missing[:5]}')
    malformed = [w for w in words if not re.fullmatch(r'[a-z]{3,7}', w)]
    if malformed:
        problems.append(f'{len(malformed)} malformed: {malformed[:5]}')
    if missing or malformed:
        print('\n'.join(f'FAIL: {p}' for p in problems))
        return 1

    phon = {w: tuple(re.sub(r'\d', '', p) for p in cmu[w].split()) for w in words}
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            a, b = words[i], words[j]
            if levenshtein(a, b) <= 1:
                problems.append(f'spelling within 1 edit: {a} / {b}')
            if phon[a] == phon[b]:
                problems.append(f'homophone: {a} / {b}')
            elif levenshtein(phon[a], phon[b]) <= 1:
                problems.append(f'pronunciation within 1 edit: {a} / {b}')

    n = len(words)
    print(f'{n:,} words, {n * (n - 1) // 2:,} pairs checked')
    print(f'3-word cell over UK+Ireland: {math.sqrt(BOX_M2 / n ** 3):.2f} m')
    root = math.isqrt(n)
    if root * root == n:
        print(f'exactly {root}x{root} — every grid cell gets a word')
    else:
        print(f'NOTE: {n:,} is not a perfect square; nearest is {root}x{root} '
              f'= {root ** 2:,}, leaving {n - root ** 2:,} words unused')
    if problems:
        print(f'\nFAIL: {len(problems)} problem(s)')
        print('\n'.join('  ' + p for p in problems[:20]))
        return 1
    print('OK: no homophones, and no two words within one edit in spelling or sound')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'data/wordlist.json'))
