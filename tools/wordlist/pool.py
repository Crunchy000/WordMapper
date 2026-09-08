#!/usr/bin/env python3
"""Stage one: every word worth SAYING, before distinctness is considered at all.

The order matters and is deliberate. Content rules come first and are absolute:
a word that is offensive, a name, religious, or grim is out whatever it sounds
like. Only what survives goes on to be thinned for distinctness, so the phonetic
stage never has to choose between a good word and a clean one.
"""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import phonemes, syllables
from spelling import has_variant, is_inflection

DATA = os.environ.get('WORDLIST_DATA', '.')
HERE = os.path.dirname(os.path.abspath(__file__))

# One syllable is where the confusable pairs live -- cat/bat/hat/mat/pat, and
# every homophone in BIP-39 bar one. Two and three syllables carry enough
# redundancy that a single misheard phoneme usually leaves the word recoverable,
# and the stress pattern gives the listener a second cue.
MIN_SYLL, MAX_SYLL = 2, 3
MIN_LEN, MAX_LEN = 4, 9
FREQ_RANK = 35000               # rarer than this and nobody is sure of the spelling

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


# Debian ships these with capitalisation intact: `wamerican` and `wbritish`.
CASED_DICTS = ('/usr/share/dict/american-english', '/usr/share/dict/british-english',
               '/usr/share/dict/words')


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
                 'exclude-negative.txt', 'exclude-proper.txt'):
        out |= read_words(os.path.join(HERE, name))
    return out


def build(max_syll=MAX_SYLL, min_syll=MIN_SYLL, min_len=MIN_LEN,
          max_len=MAX_LEN, freq_rank=FREQ_RANK):
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
    if not common:
        print('  (no cased system dictionary: proper nouns not filtered)',
              file=sys.stderr)
    excl = excluded()
    places = gazetteer()
    ranked = {w: i for i, w in enumerate(sorted(freq, key=freq.get, reverse=True))}

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
        if is_inflection(w, cmu, freq):
            drop('an inflection of a word that exists'); continue
        if has_variant(w, cmu) or has_variant(w, common):
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
