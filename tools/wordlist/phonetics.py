#!/usr/bin/env python3
"""Phonetic distance between words, over CMU Pronouncing Dictionary phonemes.

The question this answers is not "do these two words sound different" but "can
one mishearing turn one into the other". So the metric is an edit distance where
a substitution costs what that confusion is WORTH: swapping /p/ for /b/ is one
feature (voicing) and happens constantly on a bad line; swapping /p/ for /l/ does
not happen. Insertions and deletions cost a full step, because a dropped
consonant is a real error but a whole-phoneme one.
"""

VOWELS = set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split())

# Confusion classes: within a class, one feature separates the members. These are
# the pairs that actually swap on a telephone, in noise, or across accents.
CLASSES = [
    set('P B'.split()),            # voicing, bilabial stop
    set('T D'.split()),            # voicing, alveolar stop
    set('K G'.split()),            # voicing, velar stop
    set('F V'.split()),            # voicing, labiodental fricative
    set('S Z'.split()),            # voicing, alveolar fricative
    set('SH ZH'.split()),          # voicing, postalveolar fricative
    set('TH DH'.split()),          # voicing, dental fricative
    set('CH JH'.split()),          # voicing, affricate
    set('M N NG'.split()),         # nasals: place only, and place is what noise eats
    set('F TH'.split()),           # the classic: "free"/"three"
    set('V DH'.split()),
    set('S TH'.split()),           # "sink"/"think"
    set('Z DH'.split()),
    set('L R'.split()),            # liquids
    set('M N'.split()),
    set('N NG'.split()),
    set('S SH'.split()),
    set('Z ZH'.split()),
    set('CH SH'.split()),
    set('JH ZH'.split()),
    set('W V'.split()),
    set('IY IH'.split()),          # tense/lax vowel pairs
    set('UW UH'.split()),
    set('EH AE'.split()),
    set('AA AO'.split()),
    set('AH AA'.split()),
    set('AH ER'.split()),
    set('EY EH'.split()),
    set('OW AO'.split()),
    set('AY OY'.split()),
    set('AW OW'.split()),
]
_NEAR = set()
for c in CLASSES:
    for a in c:
        for b in c:
            if a != b:
                _NEAR.add((a, b))

NEAR, SWAP, CROSS = 0.5, 1.0, 2.0     # near-confusable, plain swap, vowel<->consonant


def sub_cost(a, b):
    if a == b:
        return 0.0
    if (a, b) in _NEAR:
        return NEAR
    if (a in VOWELS) != (b in VOWELS):
        return CROSS
    return SWAP


def phonemes(pron):
    """Strip the stress digits: stress is the first thing lost in noise."""
    return [p.rstrip('012') for p in pron.split()]


def distance(a, b, cutoff=None):
    """Weighted edit distance. `cutoff` abandons the comparison once the best
    possible result exceeds it, which is most of them."""
    if abs(len(a) - len(b)) * SWAP > (cutoff if cutoff else float('inf')):
        return float('inf')
    prev = [i * SWAP for i in range(len(b) + 1)]
    for i, x in enumerate(a, 1):
        cur = [i * SWAP]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j - 1] + sub_cost(x, y),
                           prev[j] + SWAP,
                           cur[j - 1] + SWAP))
        if cutoff is not None and min(cur) > cutoff:
            return float('inf')
        prev = cur
    return prev[-1]


def syllables(ph):
    return sum(1 for p in ph if p in VOWELS)
