#!/usr/bin/env python3
"""Stage one: every word worth SAYING, before distinctness is considered at all.

The order matters and is deliberate. Content rules come first and are absolute:
a word that is offensive, a name, religious, or grim is out whatever it sounds
like. Only what survives goes on to be thinned for distinctness, so the phonetic
stage never has to choose between a good word and a clean one.
"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import phonemes, syllables
from semantic import classify
from spelling import has_variant, is_inflection
from wordnet import WordNet

DATA = os.environ.get('WORDLIST_DATA', '.')
HERE = os.path.dirname(os.path.abspath(__file__))

# One syllable is where the confusable pairs live -- cat/bat/hat/mat/pat, and
# every homophone in BIP-39 bar one. Two and three syllables carry enough
# redundancy that a single misheard phoneme usually leaves the word recoverable,
# and the stress pattern gives the listener a second cue.
# One syllable used to be barred outright, because that is where the confusable
# pairs live. With BIP-39 in the pool it is allowed back in and the distinctness
# rule decides: of pair/pear it keeps whichever is otherwise stronger, and short
# words make for shorter addresses.
MIN_SYLL, MAX_SYLL = 1, 3
# Four letters minimum: below that the candidates are fragments and
# abbreviations -- amp, ems, ifs, jib, gyro -- not words anyone dictates.
MIN_LEN, MAX_LEN = 4, 9
# Deliberately loose. The pool is not the list: it is the set a person then
# reads and rejects from, and rejecting needs somewhere to reject TO.
FREQ_RANK = 55000

# A LENGTH BUDGET. Long is not the problem and rare is not the problem --
# `beautiful` is nine letters and nobody stumbles, `sphincter` is nine letters
# and everybody does. What grates is a word that is BOTH, so the two are
# coupled: every extra letter has to be paid for in familiarity. This is what
# keeps petticoat, mortician, ventricle, gallantry, pantomime and puppeteer out
# while beautiful, character, apartment and difficult stay.
LENGTH_BUDGET = {4: 55000, 5: 55000, 6: 45000, 7: 38000, 8: 28000, 9: 19000}


def affordable(word, rank):
    return rank <= LENGTH_BUDGET.get(len(word), 0)

def read_cmudict(path):
    """word -> pronunciations. More than one distinct pronunciation means a
    heteronym (read, live, bow, wind), which cannot be said unambiguously."""
    out = {}
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.startswith(';;;'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            w = parts[0].lower()
            if w.endswith(')'):
                w = w[:w.rindex('(')]
            out.setdefault(w, []).append(' '.join(parts[1:]))
    return out


def read_freq(path):
    return {w: int(n) for w, n in
            (l.split() for l in open(path) if len(l.split()) == 2)}


def read_words(path):
    """One list file: whitespace-separated, # starts a comment."""
    out = set()
    for line in open(path, encoding='utf-8', errors='replace'):
        out.update(line.split('#')[0].lower().split())
    return out


# Debian ships these with capitalisation intact: `wbritish` and `wamerican`.
#
# BRITISH FIRST, and British alone for the vocabulary. This is a British
# project and the address is spoken here, so `artefact` is the word and
# `artifact` is not; likewise liquorice, manoeuvre and omelette. Taking the
# vocabulary from the British list drops the American spellings without anyone
# having to list them. The American list is still read, but only to LEARN the
# American spellings, so a word that differs between the two can be recognised
# and refused outright -- neither form can be dictated without a follow-up
# question about how to spell it.
CASED_DICTS = ('/usr/share/dict/british-english',)
OTHER_DICTS = ('/usr/share/dict/american-english',)


def cased_dictionary(paths=CASED_DICTS):
    """(common nouns, proper nouns), told apart by their leading capital.

    Returns lower-cased sets. Possessives and words with apostrophes or accents
    are skipped -- they cannot be dictated as one word anyway.
    """
    common, proper = set(), set()
    for path in paths:
        if not os.path.exists(path):
            continue
        for line in open(path, encoding='utf-8', errors='replace'):
            w = line.strip()
            if not w.isalpha() or not w.isascii():
                continue
            (proper if w[0].isupper() else common).add(w.lower())
    return common, proper


def gazetteer(min_population=200_000):
    """Countries, US states, continents and every city of any size.

    A hand list of place names is whack-a-mole; this is the systematic version.
    The population floor matters: with every village included, `police`,
    `freedom`, `airport`, `butterfly` and `weasel` are all towns somewhere and
    the filter eats the list. Above 200,000 people what is left is nearly all
    genuinely a place -- Tennessee, Munich, Osaka, Vladimir, Milwaukee.
    """
    try:
        import geonamescache
    except ImportError:
        print('  (geonamescache not installed: place names not filtered)',
              file=sys.stderr)
        return set()
    gc = geonamescache.GeonamesCache()
    out = {c['name'].lower() for c in gc.get_cities().values()
           if c['population'] >= min_population}
    for group in (gc.get_countries(), gc.get_us_states(), gc.get_continents()):
        out |= {c['name'].lower() for c in group.values()}
    return {p for p in out if p.isalpha()}


def read_surnames(path, top=25000):
    out = set()
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, row in enumerate(csv.reader(fh)):
            if i and row and i <= top:
                out.add(row[0].lower())
    return out


def excluded():
    """Every hand-maintained exclusion, as one set. These files are the part of
    this that is judgement rather than measurement, so they are kept as plain
    text next to the code and meant to be read and argued with."""
    out = set()
    for name in ('function-words.txt', 'exclude-religious.txt',
                 'exclude-negative.txt', 'exclude-proper.txt',
                 'exclude-register.txt', 'exclude-obscure.txt',
                 'exclude-american.txt'):
        out |= read_words(os.path.join(HERE, name))
    return out


EXTRA = os.path.join(os.path.dirname(HERE), 'gridcode', 'bip39-english.txt')


CEFR_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']


def build_from_cefr(levels=None, min_syll=1, max_syll=3, min_len=3, max_len=10):
    """The graded vocabulary as the BASE, rather than as a filter over frequency.

    9,025 headwords that somebody has certified a learner knows, which is a far
    better answer to "could you say this under pressure" than a count of how
    often it turns up in film subtitles. Everything else here is subtraction:
    names, places, offensive and vulgar words, inflections of other words, words
    spelled two ways, words with two pronunciations, and words whose meaning is
    clinical, sexual, violent or religious.

    Names come from CAPITALISATION in the dictionary and not from a census list:
    a census kills Baker, Cook, Green, Young, Bell, Wood, Field and Price, which
    are ordinary words that happen to be surnames too.

    Returns (pool, reasons) like build(), with the CEFR level in place of a
    frequency rank -- so the caller orders by level, easiest first.
    """
    levels = set(levels or CEFR_ORDER)
    graded = json.load(open(os.path.join(HERE, 'cefr.json')))['level']
    cmu = read_cmudict(os.path.join(DATA, 'cmudict.txt'))
    bad = read_words(os.path.join(DATA, 'badwords.txt'))
    common, proper = cased_dictionary()
    other, _ = cased_dictionary(OTHER_DICTS)
    places = gazetteer()
    excl = excluded()
    allowed = read_words(os.path.join(HERE, 'allow-semantic.txt'))
    wn = WordNet()

    pool, reasons = [], {}
    def drop(why):
        reasons[why] = reasons.get(why, 0) + 1

    for w, lvl in sorted(graded.items(), key=lambda kv: (CEFR_ORDER.index(kv[1]), kv[0])):
        if lvl not in levels:
            drop('not at a wanted level'); continue
        if not re.fullmatch(r'[a-z]+', w):
            drop('not plain letters'); continue
        if not min_len <= len(w) <= max_len:
            drop('too short or long'); continue
        if w not in cmu:
            drop('no pronunciation in CMUdict'); continue
        if len({' '.join(phonemes(p)) for p in cmu[w]}) > 1:
            drop('more than one pronunciation'); continue
        ph = phonemes(cmu[w][0])
        if not min_syll <= syllables(ph) <= max_syll:
            drop('wrong syllable count'); continue
        if w in bad:
            drop('offensive'); continue
        if w in proper:
            drop('capitalised in the dictionary, so a proper noun'); continue
        if w in places:
            drop('a place'); continue
        if common and w not in common:
            drop('not British vocabulary'); continue
        if has_variant(w, common | other):
            drop('spelled two ways'); continue
        if is_inflection(w, cmu, None):
            drop('an inflection of a word that exists'); continue
        if w in excl:
            drop('excluded by hand (vulgar, grim, religious, register)'); continue
        if w not in allowed and classify(wn, w):
            drop('what it means: clinical, sexual, violent or religious'); continue
        pool.append((w, ph, lvl))
    return pool, reasons


def build(max_syll=MAX_SYLL, min_syll=MIN_SYLL, min_len=MIN_LEN,
          max_len=MAX_LEN, freq_rank=FREQ_RANK, extra=EXTRA):
    cmu = read_cmudict(os.path.join(DATA, 'cmudict.txt'))
    freq = read_freq(os.path.join(DATA, 'en50k.txt'))
    names = read_words(os.path.join(DATA, 'names.txt'))
    surnames = read_surnames(os.path.join(DATA, 'surnames.csv'))
    bad = read_words(os.path.join(DATA, 'badwords.txt'))
    # CMUdict has no case, so Gatsby, Jehovah, Nikolai and Aberdeen look like
    # ordinary words. The system word list DOES have case -- proper nouns are
    # capitalised in it -- which is the one signal that separates them cleanly.
    # A crowd-sourced list like dwyl/words_alpha does not work here: it holds
    # gatsby, hitler, jehovah and bethlehem in lower case alongside real words.
    common, proper = cased_dictionary()
    # Everything the other dialect spells differently, so has_variant() can see
    # across the Atlantic and not just inside one dictionary.
    other, _ = cased_dictionary(OTHER_DICTS)
    both = common | other
    if not common:
        print('  (no cased system dictionary: proper nouns not filtered)',
              file=sys.stderr)
    excl = excluded()
    places = gazetteer()
    # What a word MEANS, from WordNet, with an explicit allow list for the
    # senses that mislead it. A hand-written blocklist cannot be complete --
    # lustful, cervix, puberty and syphilis all walked through one -- and a
    # blocklist you cannot check is worse than a filter you can argue with.
    wn = WordNet()
    allowed = read_words(os.path.join(HERE, 'allow-semantic.txt'))
    if not wn.loaded:
        print('  (no WordNet: meaning not filtered -- apt-get install wordnet-base)',
              file=sys.stderr)
    ranked = {w: i for i, w in enumerate(sorted(freq, key=freq.get, reverse=True))}
    # BIP-39's words are already known to be typable and unambiguous in print;
    # what nobody checked is how they sound. They go in as candidates and face
    # exactly the same rules as everything else -- which is how pair, pear,
    # peace, piece, right and write get sorted out rather than shipped.
    bonus = read_words(extra) if extra and os.path.exists(extra) else set()
    for w in bonus:
        ranked.setdefault(w, freq_rank)

    pool, reasons = [], {}
    def drop(why):
        reasons[why] = reasons.get(why, 0) + 1

    for w, prons in cmu.items():
        if not re.fullmatch(r'[a-z]+', w):
            drop('not plain letters'); continue
        if not min_len <= len(w) <= max_len:
            drop('too short or long'); continue
        if len({p.rstrip('012') for pr in prons for p in [pr]} ) > 1 and len(
                {' '.join(phonemes(p)) for p in prons}) > 1:
            drop('more than one pronunciation'); continue
        ph = phonemes(prons[0])
        if not min_syll <= syllables(ph) <= max_syll:
            drop('not 2 or 3 syllables'); continue
        r = ranked.get(w)
        if r is None or r > freq_rank:
            drop('too rare'); continue
        if not affordable(w, r):
            drop(f'too long for how rare it is'); continue
        if w in bad:
            drop('offensive'); continue
        if w in names or w in surnames:
            drop('someone\'s name'); continue
        if w in places:
            drop('a place'); continue
        if common and w not in common:
            drop('not a common noun in the system dictionary'); continue
        if w in proper:
            drop('capitalised in the dictionary, so a proper noun'); continue
        if w in excl:
            drop('excluded by hand (function, religious or grim)'); continue
        if w not in allowed:
            kind = classify(wn, w)
            if kind:
                drop(f'what it means: {kind}'); continue
        if is_inflection(w, cmu, freq):
            drop('an inflection of a word that exists'); continue
        if has_variant(w, cmu) or has_variant(w, both):
            drop('spelled two ways (colour/color, centre/center)'); continue
        pool.append((w, ph, r))
    pool.sort(key=lambda t: t[2])
    return pool, reasons


if __name__ == '__main__':
    pool, reasons = build()
    print(f'pool: {len(pool)} words worth saying')
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f'  dropped {n:6d}  {why}')
    print('\n  most common 40:', ' '.join(w for w, _, _ in pool[:40]))
    print('\n  rarest 20:', ' '.join(w for w, _, _ in pool[-20:]))
