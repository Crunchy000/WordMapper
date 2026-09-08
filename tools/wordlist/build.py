#!/usr/bin/env python3
"""Generate a word list meant to be SPOKEN, and show its work.

    WORDLIST_DATA=<dir> python3 tools/wordlist/build.py --out spoken-2048.txt
    WORDLIST_DATA=<dir> python3 tools/wordlist/build.py --audit <list.txt>

WHY NOT BIP-39. That list is designed to be typed and checksummed, and its only
guarantee is unique four-letter prefixes, which says nothing about speech.
Scored against the CMU Pronouncing Dictionary it contains outright homophones --
pair/pear, peace/piece, right/write, wear/where -- and 53% of it has a twin one
articulatory feature away: bomb/palm, cash/catch, body/buddy, angle/ankle,
free/three. For an address read down a phone line that is the wrong list.

THE ORDER HERE IS DELIBERATE. Content first, sound second:

  1. every 2-3 syllable word common enough to be recognised          (pool.py)
  2. minus offensive words, proper nouns, religious and grim words   (pool.py)
  3. rank what is left by how far it stands from the REST OF THE
     LANGUAGE, not just from the list                           (isolation.py)
  4. take them in that order, skipping any word a single mishearing -- or a
     single keystroke -- could turn into one already taken
                                                     (distinct.py, spelling.py)

Step 3 is what makes step 4 sane. When a confusable set has to be reduced to one
survivor, the one to keep is not the most common -- it is the one hardest to
confuse with anything else in English, because it has to survive contact with
the whole language and not merely with the other 2047 words here.
"""
import argparse, hashlib, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import distance, phonemes, syllables
from distinct import audit
from isolation import isolation_parallel, CUTOFF
from pool import (CEFR_ORDER, build as build_pool, build_from_cefr,
                  cased_dictionary, read_cmudict, read_freq)
from spelling import edit1, parts, family

# The shortest word that still means something inside a longer one. Below this
# the fragments are syllables rather than words: `art` inside `start`.
CONTAIN = 4

# Every pair on the list is at least this far apart. One substitution, insertion
# or deletion costs 1.0; a confusable substitution (free/three, lamp/ramp,
# pin/pen) costs 0.5. So 2.0 means no single phoneme error and no pair of
# confusable ones can turn one word into another.
#
# 2.5 would be better and is not available: the pool yields well under 2048 words
# there, and 2048 is 11 bits exactly, with nothing wasted rounding to a word
# boundary. 2.0 is the strictest margin an 11-bit list can have.
THRESHOLD = 2.0
# BIP-39 guarantees unique FOUR-letter prefixes so a seed phrase can be typed
# short. As a hard rule that cost more than anything else here -- over a
# thousand candidates -- and pushed the selection out of common vocabulary into
# abattoir, bivouac and gazpacho. So it is a preference instead: take every word
# whose three-letter prefix is still free, then fill the remainder from what is
# left. As many words as possible are identified by three letters, and none is
# lost to the rule.
PREFER = 3
REFERENCE = 30000               # how much of the language a word is measured against
BAND = 4.0                      # frequency bands within which isolation decides


def reference_dictionary(cmu, freq, size=REFERENCE):
    ranked = sorted((w for w in freq if w in cmu), key=freq.get, reverse=True)
    return [(w, phonemes(cmu[w][0])) for w in ranked[:size]]


def report(entries, label):
    print(f'\n{label}: {len(entries)} words')
    for th, what in ((0.6, 'homophones'),
                     (1.1, 'one confusable feature apart'),
                     (2.0, 'within one phoneme error')):
        bad = audit(entries, th)
        inv = {w for _, w, _ in bad} | {v for _, _, v in bad}
        print(f'  {what:30s} {len(bad):6d} pairs, {len(inv):5d} words '
              f'({len(inv) / len(entries) * 100:4.1f}%)')
    return audit(entries, 1.1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--threshold', type=float, default=THRESHOLD)
    ap.add_argument('--out')
    ap.add_argument('--audit', help='score an existing list instead of building')
    ap.add_argument('--base', choices=('frequency', 'cefr'), default='frequency',
                    help='what the pool is drawn FROM. "cefr" starts from the '
                         '9,025 graded headwords instead of a frequency list.')
    ap.add_argument('--cefr', metavar='LEVELS', default=None,
                    help='keep only words graded at these CEFR levels, e.g. A1,A2,B1,B2. '
                         'Graded vocabulary is what a person can retrieve under pressure; '
                         'see cefr.json and the README for what it costs.')
    args = ap.parse_args()
    data = os.environ.get('WORDLIST_DATA', '.')
    cmu = read_cmudict(os.path.join(data, 'cmudict.txt'))

    if args.audit:
        words = [l.strip() for l in open(args.audit) if l.strip()]
        entries = [(w, phonemes(cmu[w][0])) for w in words if w in cmu]
        print(f'{args.audit}: {len(words)} words, {len(entries)} found in CMUdict')
        for d, a, b in report(entries, 'scored')[:20]:
            print(f'      {d:.1f}  {a} / {b}')
        return 0

    if args.base == 'cefr':
        # The graded vocabulary IS the pool: certified-known words, minus
        # everything unsayable. Ordered easiest first, so the list fills with
        # A1 before it ever reaches C1.
        pool, reasons = build_from_cefr(
            args.cefr.split(',') if args.cefr else None)
        rank_of = {lvl: i for i, lvl in enumerate(CEFR_ORDER)}
        pool = [(w, ph, rank_of[lvl] * 1000) for w, ph, lvl in pool]
        args.cefr = None
    else:
        pool, reasons = build_pool()
    if args.cefr:
        # CEFR grades a word by the level at which a learner reliably knows it.
        # A1-B2 is roughly "everyday English": the vocabulary someone can
        # produce and recognise without stopping to think, which is the only
        # kind that survives being read out in a hurry.
        want = {x.strip().upper() for x in args.cefr.split(',')}
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cefr.json')
        graded = json.load(open(path))['level']
        before = len(pool)
        pool = [t for t in pool if graded.get(t[0]) in want]
        reasons[f'not graded {"/".join(sorted(want))} in CEFR'] = before - len(pool)
    print(f'1-2. pool: {len(pool)} words worth saying')
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f'       dropped {n:6d}  {why}')

    freq = read_freq(os.path.join(data, 'en50k.txt'))
    ref = reference_dictionary(cmu, freq)
    # Isolation takes minutes and never changes for a given pool, so it is
    # cached: the selection rules above it get tuned far more often than the
    # dictionary underneath does.
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.isolation.json')
    iso = {}
    if os.path.exists(cache):
        iso = json.load(open(cache))
    missing = [(w, ph) for w, ph, _ in pool if w not in iso]
    if missing:
        print(f'\n3.  ranking {len(missing)} words against the nearest of '
              f'{len(ref)} common words (a few minutes)')
        iso.update(isolation_parallel(missing, ref))
        json.dump(iso, open(cache, 'w'))
    else:
        print(f'\n3.  isolation from cache ({len(pool)} words)')
    for step in (2.0, 1.5, 1.0, 0.5, 0.0):
        n = sum(1 for v in iso.values() if v == step)
        print(f'       {n:5d} words sit {step:.1f} from their nearest neighbour'
              + ('  (at or past the cutoff)' if step >= CUTOFF else ''))

    # ORDERING, which is the whole argument. Sorting by isolation alone gives a
    # list of `gazpacho`, `bivouac` and `sprocket`: rare long words are exactly
    # what stands apart from the language, so isolation and familiarity pull in
    # opposite directions -- only 471 words are both common and fully isolated,
    # against the 2048 needed.
    #
    # So familiarity leads, in COARSE bands, and isolation decides within a
    # band. Members of a confusable set are almost always of comparable
    # frequency, so they land in one band and the most isolated of them wins it
    # -- which is the rule wanted -- while the list as a whole stays made of
    # words people know.
    #
    # A word with an exact homophone anywhere in the language is barred
    # outright, however common it is. `principal` cannot be dictated without
    # `principle` being written down instead, and that is true whether or not
    # `principle` is on this list.
    eligible = [t for t in pool if iso[t[0]] > 0.0]
    print(f'       {len(pool) - len(eligible)} barred: an exact homophone exists '
          f'somewhere in the language')
    band = lambda rank: int(math.log(rank + 2, BAND))
    order = sorted(eligible, key=lambda t: (band(t[2]), -iso[t[0]], t[2]))

    print(f'\n4.  taking {args.size}: nothing within {args.threshold} by sound '
          f'or one keystroke by spelling, preferring a free {PREFER}-letter prefix')
    taken, prefixes, seen = [], set(), set()
    claimed = set()                 # word-pieces and roots already spoken for
    common, _ = cased_dictionary()
    dropped = {'sound': 0, 'spelling': 0, 'shared piece': 0, 'shared root': 0,
               'contained': 0}

    def consider(w, ph, rank):
        # One word per piece. Banning compounds outright works and costs too
        # much -- a fifth of the pool, which pushes the selection into rarer
        # words than the ones it was protecting. What goes wrong is a FAMILY:
        # lady, landlady, ladybug; boy, boyfriend, cowboy, busboy, bellboy --
        # several words sharing a piece, and so sharing a way to mishear the
        # boundary between them. One compound alone is harmless.
        if common and (parts(w, common) & claimed):
            dropped['shared piece'] += 1; return False
        # Same rule, the other way English builds words. parts() only sees
        # COMPOUNDS, where both halves are words, so help/helpful/unhelpful,
        # certain/uncertain and classic/classical went straight through it:
        # `ful` and `un` are not words. A shared root is a shared way to lose
        # an ending or miss a prefix, which is the failure the piece rule
        # exists for.
        if common and (family(w, common) & claimed):
            dropped['shared root'] += 1; return False
        # And the blunt version of the same idea, which catches what no affix
        # table does: no chosen word may sit INSIDE another, either way round.
        # lady/landlady/ladybird is the case that started this, but so are
        # rate/celebrate/tolerate/vibrate and scope/telescope -- not a shared
        # root at all, just the same run of sounds at the end of a longer word,
        # which is the same thing to a listener.
        if any(len(v) >= CONTAIN and v in w or len(w) >= CONTAIN and w in v
               for v, _, _ in taken):
            dropped['contained'] += 1; return False
        if any(distance(ph, ph2, args.threshold) < args.threshold
               for _, ph2, _ in taken if abs(len(ph2) - len(ph)) <= 2):
            dropped['sound'] += 1; return False
        # One keystroke apart is invisible to phonetics and fatal in a text box:
        # water/later, hollow/follow, batter/butter.
        if any(edit1(w, v) for v, _, _ in taken if abs(len(v) - len(w)) <= 1):
            dropped['spelling'] += 1; return False
        taken.append((w, ph, rank))
        prefixes.add(w[:PREFER])
        seen.add(w)
        if common:
            claimed.update(parts(w, common))
            claimed.update(family(w, common))
        return True

    # First pass: only words whose short prefix is still free. Second pass:
    # everything else, so the preference never costs a word.
    for w, ph, rank in order:
        if len(taken) >= args.size:
            break
        if w[:PREFER] not in prefixes:
            consider(w, ph, rank)
    unique = len(taken)
    for w, ph, rank in order:
        if len(taken) >= args.size:
            break
        if w not in seen:
            consider(w, ph, rank)
    print('       skipped ' + ', '.join(f'{n} on {k}' for k, n in dropped.items()))
    print(f'       {unique} of {len(taken)} are the only word with their first '
          f'{PREFER} letters')
    if len(taken) < args.size:
        print(f'       only {len(taken)} -- widen the pool or lower the threshold')
        return 1

    words = sorted(w for w, _, _ in taken)
    text = '\n'.join(words) + '\n'
    print(f'       took {len(taken)}; how far each stands from the rest of the '
          f'language: ' + ', '.join(
              f'{s_}: {sum(1 for w, _, _ in taken if iso[w] == s_)}'
              for s_ in (2.0, 1.5, 1.0, 0.5)))
    print(f'\n    sha256 {hashlib.sha256(text.encode()).hexdigest()}')
    print('    syllables: ' + ', '.join(
        f'{n}: {sum(1 for _, ph, _ in taken if syllables(ph) == n)}' for n in (1, 2, 3)))
    print(f'    letters {min(map(len, words))}-{max(map(len, words))}, '
          f'mean {sum(map(len, words)) / len(words):.1f}')
    report([(w, ph) for w, ph, _ in taken], '    result')
    if args.out:
        open(args.out, 'w').write(text)
        print(f'\n    -> {args.out}')
    else:
        print('\n' + ' '.join(words[:60]) + ' ...')
    return 0


if __name__ == '__main__':
    sys.exit(main())
