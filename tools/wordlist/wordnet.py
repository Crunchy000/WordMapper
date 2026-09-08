#!/usr/bin/env python3
"""Just enough WordNet to ask what a word IS.

A hand list of unwanted words has holes -- `lustful`, `cervix`, `puberty` and
`syphilis` all got through one. WordNet knows that syphilis is a disease and a
cervix is a reproductive organ, and it knows it for every word at once, which is
what a hand list can never be.

Reads the WordNet 3.0 database files directly (Debian: `wordnet-base`), because
the usual Python front ends want to download their own copy.
"""
import os, re

WNDIR = os.environ.get('WORDNET_DIR', '/usr/share/wordnet')
POS = {'noun': 'n', 'verb': 'v', 'adj': 'a', 'adv': 'r'}


def _load(pos):
    """(offset -> (words, hypernyms, gloss), lemma -> offsets IN SENSE ORDER).

    The sense order is the whole point and it does not come from `data.<pos>`:
    that file is in offset order. `index.<pos>` lists each lemma's synsets most
    common FIRST, which is what lets a caller ask about what a word usually
    means rather than about every meaning it has ever had. Read all the senses
    of an ordinary word and English will tell you that a banana is a
    reproductive structure, a mother is a nun and an upper is a stimulant.
    """
    syn, index = {}, {}
    path = os.path.join(WNDIR, f'data.{pos}')
    if not os.path.exists(path):
        return syn, index
    with open(path, encoding='latin-1') as fh:
        for line in fh:
            if line.startswith('  '):
                continue
            head = line.split('|')[0].split()
            if len(head) < 4:
                continue
            offset = head[0]
            n_words = int(head[3], 16)
            words = [head[4 + 2 * i].lower().replace('_', ' ')
                     for i in range(n_words)]
            gloss = (line.split('|', 1)[1].strip().lower() if '|' in line else '')
            i = 4 + 2 * n_words
            n_ptr = int(head[i]); i += 1
            hyper = []
            for _ in range(n_ptr):
                sym, target, tpos = head[i], head[i + 1], head[i + 2]
                i += 4
                # @ hypernym, @i instance-of (Paris IS-AN-INSTANCE-OF city),
                # + derivationally related (lustful -> lust).
                if sym in ('@', '@i', '+'):
                    hyper.append((sym, target, tpos))
            syn[offset] = (words, hyper, gloss)
    path = os.path.join(WNDIR, f'index.{pos}')
    if os.path.exists(path):
        with open(path, encoding='latin-1') as fh:
            for line in fh:
                if line.startswith('  '):
                    continue
                f = line.split()
                if len(f) < 6:
                    continue
                # lemma pos synset_cnt p_cnt [ptr...] sense_cnt tagsense_cnt off...
                n_ptr = int(f[3])
                i = 4 + n_ptr
                n_sense = int(f[i])
                index[f[0].lower().replace('_', ' ')] = f[i + 2:i + 2 + n_sense]
    return syn, index


class WordNet:
    def __init__(self):
        self.syn, self.index = {}, {}
        for name, code in POS.items():
            syn, index = _load(name)
            self.syn[code] = syn
            for w, offs in index.items():
                self.index.setdefault(w, []).append((code, offs))

    @property
    def loaded(self):
        return bool(self.index)

    def ancestors(self, word, depth=12, follow_derived=True, senses=1):
        """Every word above this one: its own synonyms, then what it is a kind
        of, all the way up. Derivational links are followed once, so an
        adjective reaches the noun it comes from and inherits its answer.

        `senses` caps how many meanings are consulted, most common first. One
        is the honest default: a word's rarest sense is not what a listener
        hears, and admitting all of them makes every word in English mean
        something unpleasant somewhere."""
        out, seen = set(), set()
        stack = []
        for code, offs in self.index.get(word.lower(), ()):
            offs = offs[:senses]
            # Derivation is followed only OUT of a modifier: `lustful` has to
            # reach `lust` to inherit its answer. Following it out of a noun
            # drags in every verb the noun relates to -- `puberty` arrives at
            # `add up`, `assess`, `convey` -- which is noise, not meaning.
            derive = follow_derived and code in ('a', 'r')
            stack += [(code, o, 0, derive) for o in offs]
        while stack:
            code, off, d, derive = stack.pop()
            if (code, off) in seen or d > depth:
                continue
            seen.add((code, off))
            entry = self.syn.get(code, {}).get(off)
            if not entry:
                continue
            words, hyper, _ = entry
            out.update(words)
            for sym, target, tpos in hyper:
                if sym == '+':
                    if derive:                      # one hop only, or everything
                        stack.append((tpos, target, d, False))
                else:
                    stack.append((tpos, target, d + 1, derive))
        return out

    def is_instance(self, word, senses=1):
        """True if any sense is an INSTANCE of something -- WordNet's own mark
        for a proper noun (Paris, Shakespeare, Jupiter)."""
        for code, offs in self.index.get(word.lower(), ()):
            for off in offs[:senses]:
                entry = self.syn.get(code, {}).get(off)
                if entry and any(sym == '@i' for sym, _, _ in entry[1]):
                    return True
        return False

    def glosses(self, word, senses=1):
        """The definitions of this word's own senses.

        Hypernyms say what a thing IS and that is usually enough, but not
        always: `cervix` and `elbow` are both a `body part`, and only the
        definition -- 'necklike opening to the uterus' -- separates them.
        """
        out = []
        for code, offs in self.index.get(word.lower(), ()):
            for off in offs[:senses]:
                entry = self.syn.get(code, {}).get(off)
                if entry:
                    out.append(entry[2])
        return out
