#!/usr/bin/env python3
"""Word lists for PHRASES: one list per part of speech.

    WORDLIST_DATA=<dir> python3 tools/wordlist/phrases.py

An address read as a phrase -- adjective noun verb noun, "cheeky film follow
banana" -- puts each word in a slot that only takes one part of speech. That
changes what has to be kept apart. A word only competes with the other words
that could fill ITS slot: a noun is never heard where a verb belongs, so a noun
and a verb that sound alike cannot be confused for each other. Mishear one as
the other and the phrase stops being grammatical, which is caught on the spot.

So every rule the single list applies -- nothing within 2.0 by sound, nothing
one keystroke apart, one word per piece and per root, no word inside another --
is applied WITHIN each part of speech and not across them. Words the single
list turned away because they clashed with a word of a different part of speech
come back.

Everything before selection is unchanged: the same CEFR A1-B2 pool, the same
content rules, the same homophone bar, the same ordering by familiarity band
then isolation. The only new judgement is the part of speech itself, which comes
from WordNet's tagged sense counts -- the part of speech a word is MOST USED as
-- with pos-override.txt for the cases where that is wrong.

Writes phrase-adjective.txt, phrase-noun.txt and phrase-verb.txt.
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import distance
from pool import CEFR_ORDER, build_from_cefr, cased_dictionary
from spelling import edit1, parts, family
from build import THRESHOLD, PREFER, BAND, CONTAIN

HERE = os.path.dirname(os.path.abspath(__file__))
WNDIR = os.environ.get('WORDNET_DIR', '/usr/share/wordnet')
KINDS = {'a': 'adjective', 'n': 'noun', 'v': 'verb'}
# A word must be used as its part of speech at least this much of the time --
# by WordNet's tagged sense counts -- to be read as one. `change` is a noun as
# often as a verb and reads as either; `banana` is only ever a noun.
DOMINANCE = 0.5


def tagged_counts():
    """lemma -> {pos letter: tagged sense count}. Satellite adjectives are
    folded into 'a'."""
    out = {}
    for name, tag in (('noun', 'n'), ('verb', 'v'), ('adj', 'a'), ('adv', 'r')):
        path = os.path.join(WNDIR, f'index.{name}')
        with open(path, encoding='latin-1') as fh:
            for line in fh:
                if line.startswith(' '):
                    continue
                f = line.split()
                p_cnt = int(f[3])
                out.setdefault(f[0], {})[tag] = int(f[5 + p_cnt]) + 1
    return out


def read_overrides():
    """pos-override.txt: `word pos` per line, pos one of a, n, v or - (none)."""
    out = {}
    path = os.path.join(HERE, 'pos-override.txt')
    if os.path.exists(path):
        for line in open(path):
            line = line.split('#')[0].split()
            if len(line) == 2:
                out[line[0]] = line[1]
    return out


def part_of_speech(w, counts, overrides):
    """'a', 'n', 'v', or None when the word is not clearly one of them."""
    if w in overrides:
        return None if overrides[w] == '-' else overrides[w]
    c = counts.get(w)
    if not c:
        return None
    best = max(c, key=c.get)
    if best not in KINDS or c[best] / sum(c.values()) < DOMINANCE:
        return None
    return best


def select(order, common):
    """The single list's selection rules, applied to one part of speech."""
    taken, prefixes, seen, claimed = [], set(), set(), set()
    dropped = dict.fromkeys(('sound', 'spelling', 'shared piece', 'shared root',
                             'contained'), 0)

    def consider(w, ph):
        if parts(w, common) & claimed:
            dropped['shared piece'] += 1; return
        if family(w, common) & claimed:
            dropped['shared root'] += 1; return
        if any(len(v) >= CONTAIN and v in w or len(w) >= CONTAIN and w in v
               for v, _ in taken):
            dropped['contained'] += 1; return
        if any(distance(ph, ph2, THRESHOLD) < THRESHOLD
               for _, ph2 in taken if abs(len(ph2) - len(ph)) <= 2):
            dropped['sound'] += 1; return
        if any(edit1(w, v) for v, _ in taken if abs(len(v) - len(w)) <= 1):
            dropped['spelling'] += 1; return
        taken.append((w, ph))
        prefixes.add(w[:PREFER])
        seen.add(w)
        claimed.update(parts(w, common))
        claimed.update(family(w, common))

    for w, ph in order:
        if w[:PREFER] not in prefixes:
            consider(w, ph)
    for w, ph in order:
        if w not in seen:
            consider(w, ph)
    return [w for w, _ in taken], dropped


def main():
    pool, _ = build_from_cefr(['A1', 'A2', 'B1', 'B2'])
    rank_of = {lvl: i for i, lvl in enumerate(CEFR_ORDER)}
    iso = json.load(open(os.path.join(HERE, '.isolation.json')))
    eligible = [(w, ph, rank_of[lvl] * 1000) for w, ph, lvl in pool if iso[w] > 0.0]
    band = lambda rank: int(math.log(rank + 2, BAND))
    order = sorted(eligible, key=lambda t: (band(t[2]), -iso[t[0]], t[2]))

    counts, overrides = tagged_counts(), read_overrides()
    common, _ = cased_dictionary()
    single = set(open(os.path.join(HERE, 'spoken-1296-plain.txt')).read().split())
    by_kind = {k: [] for k in KINDS}
    unclear = 0
    for w, ph, _ in order:
        k = part_of_speech(w, counts, overrides)
        if k is None:
            unclear += 1
        else:
            by_kind[k].append((w, ph))
    print(f'{len(eligible)} eligible words; {unclear} not clearly one part of speech')
    for k, name in KINDS.items():
        words, dropped = select(by_kind[k], common)
        back = sorted(set(words) - single)
        print(f'  {name:9s} {len(by_kind[k]):5d} candidates -> {len(words):5d} taken '
              f'({len(back)} the single list turned away); skipped '
              + ', '.join(f'{n} on {why}' for why, n in dropped.items()))
        with open(os.path.join(HERE, f'phrase-{name}.txt'), 'w') as fh:
            fh.write('\n'.join(sorted(words)) + '\n')


if __name__ == '__main__':
    main()
