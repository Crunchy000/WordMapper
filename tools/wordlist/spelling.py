#!/usr/bin/env python3
"""The typing half. Sound is only one of the two ways an address gets mangled.

Two words can be perfectly distinct out loud and still a menace in a text box:
`water` and `later` are one keystroke apart, `colour` and `color` are the same
word spelled two ways, and `planet` invites `planets` from anyone typing at
speed. None of that is audible, so none of it is caught by phonetic distance.
"""
import re

# Regular English inflections, as (suffix, what the base would be).
#
# STRONG endings are inflections whenever the base is a real word: nothing that
# ends in -ed or -ing has a real word as its stem by accident. WEAK endings
# collide with ordinary words that merely end that way -- number/numb,
# corner/corn, matter/matt -- so those need the base to be the commoner of the
# two before the word is treated as derived from it.
STRONG = [
    ('ies', 'y'), ('ied', 'y'),
    ('sses', 'ss'), ('shes', 'sh'), ('ches', 'ch'), ('xes', 'x'), ('zes', 'z'),
    ('ves', 'f'), ('ves', 'fe'),
    ('es', ''), ('s', ''),
    ('ed', ''), ('ed', 'e'), ('d', ''),
    ('ing', ''), ('ing', 'e'),
]
WEAK = [
    ('ier', 'y'), ('iest', 'y'), ('ily', 'y'),
    ('er', ''), ('er', 'e'), ('est', ''), ('est', 'e'),
    ('ly', ''), ('ness', ''), ('ment', ''),
]
INFLECTIONS = STRONG + WEAK

# Spellings the same word has on two sides of the Atlantic, or in two house
# styles. If both forms exist, neither can be dictated without a follow-up
# question, so the word is not usable at all.
VARIANTS = [
    ('our', 'or'), ('or', 'our'),                # colour / color
    ('ise', 'ize'), ('ize', 'ise'),              # realise / realize
    ('isation', 'ization'), ('ization', 'isation'),
    ('yse', 'yze'), ('yze', 'yse'),              # analyse / analyze
    ('re', 'er'), ('er', 're'),                  # centre / center
    ('ce', 'se'), ('se', 'ce'),                  # defence / defense
    ('ogue', 'og'), ('og', 'ogue'),              # catalogue / catalog
    ('ae', 'e'), ('oe', 'e'),                    # anaemia / anemia
    ('ll', 'l'), ('l', 'll'),                    # travelling / traveling
    ('mme', 'm'), ('m', 'mme'),                  # programme / program
    ('que', 'ck'), ('ck', 'que'),                # cheque / check
    ('ph', 'f'), ('f', 'ph'),                    # sulphur / sulfur
    ('gramme', 'gram'),
]


def base_forms(w, endings=INFLECTIONS):
    """Every word this could be a regular inflection of."""
    out = set()
    for suffix, repl in endings:
        if w.endswith(suffix) and len(w) - len(suffix) + len(repl) >= 3:
            stem = w[:len(w) - len(suffix)] + repl
            out.add(stem)
            # walked -> walk, but also stopped -> stop and running -> run
            if len(stem) > 3 and stem[-1] == stem[-2] and stem[-1] not in 'aeiou':
                out.add(stem[:-1])
    out.discard(w)
    return out


def is_inflection(w, vocab, freq=None):
    """True if this is a regular inflection of a word that actually exists.

    The point is not tidiness. A list holding both `planet` and `planets` is a
    list where one dropped consonant, or one autocorrect, silently changes the
    address -- and holding only the base means a stray plural is at least
    REJECTED rather than accepted as somewhere else."""
    if any(b in vocab for b in base_forms(w, STRONG)):
        return True
    return any(b in vocab and (freq is None or freq.get(b, 0) >= freq.get(w, 0))
               for b in base_forms(w, WEAK))


def variant_spellings(w):
    """Other spellings of the same word, under the usual house-style swaps."""
    out = set()
    for a, b in VARIANTS:
        for m in re.finditer(f'(?={re.escape(a)})', w):
            i = m.start()
            out.add(w[:i] + b + w[i + len(a):])
    out.discard(w)
    return {v for v in out if len(v) >= 3}


def has_variant(w, vocab):
    return any(v in vocab for v in variant_spellings(w))


def edit1(a, b):
    """True if one insertion, deletion or substitution turns a into b."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) <= 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def parts(word, vocab, min_part=3):
    """The words this word is made of, plus itself.

    `landlady` is {land, lady, landlady}; `water` is just {water}. A word can
    split more than one way, and every reading counts, because a listener only
    needs one of them to mishear the boundary.
    """
    out = {word}
    for i in range(min_part, len(word) - min_part + 1):
        if word[:i] in vocab and word[i:] in vocab:
            out.add(word[:i])
            out.add(word[i:])
    return out


def shares_component(word, vocab, claimed, min_part=3):
    """True if this word is built from a piece some chosen word already uses.

    Banning compounds outright works and costs too much: it removes a fifth of
    the pool, which forces the selection down into rarer vocabulary than the
    words it was protecting. What actually goes wrong is a FAMILY -- lady,
    landlady, ladybug; boy, boyfriend, cowboy, busboy, bellboy -- where several
    words share a piece and so share a way to mishear the boundary between
    them. One compound alone is harmless. So the rule is one word per piece:
    whichever gets there first keeps it.
    """
    return bool(parts(word, vocab, min_part) & claimed)


def is_compound(word, vocab, min_part=3):
    """True if this word is two words stuck together.

    `landlady` is land + lady, `ladybug` is lady + bug, `boyfriend`, `cowboy`,
    `busboy`, `bellboy` and `boyhood` are all boy + something or something +
    boy. Phonetic distance says these are far apart -- adding four phonemes is
    twice the margin -- and phonetic distance is the wrong ruler here, because a
    listener does not compare whole words. They hear a word boundary that is not
    there, or miss one that is, and a set of words sharing a component is a set
    of ways to make that slip.

    It does not matter whether the component is itself on the list: what a
    listener nearly hears is any word they know, not just the 2047 others.
    """
    for i in range(min_part, len(word) - min_part + 1):
        if word[:i] in vocab and word[i:] in vocab:
            return True
    return False
