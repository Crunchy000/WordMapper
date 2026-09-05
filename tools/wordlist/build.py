#!/usr/bin/env python3
"""Build a soundalike-free mnemonic word list.

Sources (all installable; pypi and the npm registry bypass the sandbox proxy):
    pip  install wordfreq
    npm  install cmu-pronouncing-dictionary wordnet-db naughty-words \
                 profane-words stopword an-array-of-english-words

Run from a directory containing node_modules with those packages:
    python3 build.py > candidate-wordlist.json

The selection rule is that no two words in the output may be within one edit
of each other, in EITHER spelling or pronunciation. Pronunciation comes from
the CMU dictionary as ARPAbet phonemes; comparing phoneme sequences rather
than letters is what catches sail/sale, which no spelling rule would.
"""
import json, re, math, sys, subprocess

BAND = (2.5, 5.0)   # Zipf frequency: below is obscure, above is a function word
LENGTH = (3, 7)

def npm_json(expr):
    """Pull a JSON blob out of an installed npm package."""
    return json.loads(subprocess.check_output(['node', '-e', f'console.log(JSON.stringify({expr}))']))

def load():
    return dict(
        cmu=npm_json("require('cmu-pronouncing-dictionary').dictionary"),
        block=set(npm_json("require('naughty-words').en")) | set(npm_json("require('profane-words')")),
        stop=set(npm_json("require('stopword').eng")),
        wndir=npm_json("require('wordnet-db').path"),
    )

def wordnet(wndir):
    """Noun lemmas, plus which are only ever capitalised (i.e. proper nouns)."""
    lower, upper = set(), set()
    for line in open(f'{wndir}/data.noun', encoding='latin-1'):
        if line.startswith('  '):
            continue
        head = line.split(' | ')[0].split()
        for i in range(int(head[3], 16)):        # w_cnt is hex
            w = head[4 + 2 * i]
            if '_' not in w:
                (upper if w[0].isupper() else lower).add(w.lower())
    nouns = {l.split()[0] for l in open(f'{wndir}/index.noun', encoding='latin-1')
             if not l.startswith('  ')}
    verbs = {l.split()[0] for l in open(f'{wndir}/index.verb', encoding='latin-1')
             if not l.startswith('  ')}
    return nouns, verbs, upper - lower

def inflected(w, nouns, verbs):
    """Plurals, gerunds, participles and agent nouns -- they add confusable
    pairs (wallop/wallops) without adding distinct concepts."""
    if w.endswith('s') and (w[:-1] in nouns or w[:-2] in nouns or w[:-2] + 'y' in nouns):
        return True
    if w.endswith('es') and w[:-2] in nouns:
        return True
    if w.endswith('ing') and (w[:-3] in verbs or w[:-3] + 'e' in verbs or w[:-4] in verbs):
        return True
    if w.endswith(('ed', 'er')) and (w[:-2] in verbs or w[:-1] in verbs):
        return True
    return False

def main():
    from wordfreq import zipf_frequency
    src = load()
    nouns, verbs, proper = wordnet(src['wndir'])
    cmu = src['cmu']

    pool = [w for w in nouns
            if re.fullmatch(rf'[a-z]{{{LENGTH[0]},{LENGTH[1]}}}', w)
            and w in cmu
            and w not in src['stop'] and w not in proper and w not in src['block']
            and not inflected(w, nouns, verbs)]
    freq = {w: zipf_frequency(w, 'en') for w in pool}

    phonemes = {}
    def phkey(w):
        """Stress-stripped ARPAbet, one character per phoneme so that ordinary
        string edit distance works on the sequence."""
        out = ''
        for p in (re.sub(r'\d', '', x) for x in cmu[w].split()):
            out += phonemes.setdefault(p, chr(0x100 + len(phonemes)))
        return out

    def dels(s):
        """s plus its one-character deletions. Two strings are within edit
        distance 1 iff these sets intersect -- avoids O(n^2) comparison."""
        return {s} | {s[:i] + s[i + 1:] for i in range(len(s))}

    # Greedy, most familiar word first, so common words win any collision.
    ordered = sorted((w for w in pool if BAND[0] <= freq[w] <= BAND[1]),
                     key=lambda w: (-freq[w], w))
    sounds, spellings, phone_nbrs, out = set(), set(), set(), []
    for w in ordered:
        key = phkey(w)
        near_spelling, near_sound = dels(w), dels(key)
        if key in sounds:                    # homophone: sail / sale
            continue
        if near_spelling & spellings:        # one letter apart: cat / cot
            continue
        if near_sound & phone_nbrs:          # one phoneme apart
            continue
        out.append(w)
        sounds.add(key)
        spellings |= near_spelling
        phone_nbrs |= near_sound

    print(json.dumps(out, indent=0))
    n = len(out)
    box = 9.92141e11  # UK + Ireland bounding box, m^2
    print(f'{n:,} words -> 3-word cell {math.sqrt(box / n ** 3):.2f} m', file=sys.stderr)

if __name__ == '__main__':
    main()
