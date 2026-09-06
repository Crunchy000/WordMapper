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
import json, re, math, os, sys, subprocess

BAND = (3.0, 5.0)   # Zipf frequency: below is obscure, above is a function word
LENGTH = (3, 7)
COUNT = 1849        # 43**2 -- exactly fills the demo grid, leaving no cell
                    # unaddressed. Override with --count, but use the square of
                    # a PRIME: a square grid keeps cell aspect constant across
                    # levels (docs/uk-word-grid-review.md), and p**2 with p prime
                    # is also what makes GF(count) a real field, which the
                    # self-correcting codec needs (docs/error-correction.md).
                    # 46**2 = 2116 would be a fine grid and an impossible field.

# Only Latin-script languages: a loanword in Russian or Japanese is written in
# another script, so the English spelling would never appear in its corpus.
LANGS = ['ca', 'cs', 'da', 'de', 'en', 'es', 'fi', 'fil', 'fr', 'hu', 'id', 'is',
         'it', 'lt', 'lv', 'ms', 'nb', 'nl', 'pl', 'pt', 'ro', 'sk', 'sl', 'sv',
         'tr', 'vi']

# Concepts a friendly address scheme should not contain. Named by word; every
# sense of each becomes a root, and anything beneath it in WordNet's hypernym
# graph is dropped. This generalises far better than a blocklist -- "leprosy"
# and "hernia" are caught as diseases without either being listed.
BAD_ROOTS = ['disease', 'illness', 'symptom', 'injury', 'disorder', 'pain',
             'wound', 'weapon', 'firearm', 'ammunition', 'crime', 'violence',
             'killing', 'corpse', 'death', 'body_part', 'organ', 'excretion',
             'genitalia', 'narcotic', 'poison', 'insult']

# Religious figures, tested against the DOMINANT sense only. WordNet orders
# senses by frequency, so checking every sense over-reaches wildly: "doctor" is
# a Doctor of the Church, "placebo" was a vespers office, "fox" is George Fox and
# "moon" is Sun Myung Moon. Judging a word by its first sense keeps all of those
# and still removes christ, jonah, messiah and the clergy titles.
FAITH_ROOTS = ['deity', 'religious_person', 'prophet', 'saint', 'clergyman',
               'sacred_text', 'religion']

# The hypernym test alone is leaky: WordNet's first sense of "messiah" is "any
# expected deliverer", which sits under no religious root at all. These are the
# remainder, found by scanning first-sense glosses for religious vocabulary and
# then read by hand -- the scan alone flags "dinner", "oxen" and "variety",
# because the keyword appears in an example sentence rather than the definition.
#
# The line drawn here is religious vocabulary as a category -- figures, texts,
# practices, places and labels for believers and non-believers -- applied across
# faiths equally. Dropping only Christian terms would leave an inconsistent list.
FAITH_WORDS = {
    # figures and labels for people by belief
    'messiah', 'angel', 'creator', 'golem', 'goliath', 'mahatma', 'gentile',
    'heathen', 'infidel', 'pagan', 'heretic', 'atheist', 'clergy', 'laity',
    # texts, doctrine, practices
    'agape', 'baptism', 'dogma', 'fatwa', 'gradual', 'hajj', 'homily', 'idol',
    'karma', 'kosher', 'liturgy', 'mandala', 'mitzvah', 'nirvana', 'sermon',
    'sharia', 'worship', 'rota',
    # places and institutions
    'ashram', 'bethel', 'medina', 'papacy', 'parish', 'priory', 'rectory',
    'shrine', 'steeple', 'yeshiva',
    # not religious, but the same "would rather not" category
    'harem',
}

# Words with two accepted spellings are bad address words on either side of the
# Atlantic: a listener cannot know which one to write down. Derived from data
# rather than hand-listed, because a hand list does not survive regeneration --
# the backfill quietly reintroduced armor, fervor, flavor and rumor.
SPELLING_KEEP = {
    'almanac',   # almanack is archaic; almanac is standard in both
    'filter',    # paired with "philtre", which is a different word entirely
}

# Words must appear in the commonest tiers of English, not merely clear the
# frequency floor. Zipf counts written occurrences, so fashion journalism pushes
# "couture" to 3.32 -- above the floor, and not a word anyone reaches for.
# Cumulative tiers 10-35 are roughly the 38,000 commonest English words.
COMMON_TIERS = ['10', '20', '35']
US_KEEP = {'deputy', 'derby', 'grunt'}   # flagged as American, ordinary in the UK

# Proper nouns whose lowercase common-noun sense is too weak to carry them.
#
# These come from WordNet's own capitalisation, but they are curated rather than
# rule-derived: the obvious rule -- "the word's most frequent sense is a
# capitalised proper noun" -- flags 77 words and would take basic, sweet, grey,
# crown, mobile and burger with them, because WordNet's sense ordering puts
# proper nouns first far more often than usage does. Words with a strong
# everyday sense are kept: jersey (garment), ottoman (furniture), scribe,
# swift, smith, marine, drake, ford, polo, diesel, cheddar, cola.
PROPER_NOUNS = {
    'apache', 'argus', 'berlin', 'bohemia', 'bolivia', 'bologna', 'brazil',
    'burgess', 'chapman', 'collins', 'concord', 'danish', 'dixie', 'geneva',
    'hogan', 'japan', 'java', 'kremlin', 'louvre', 'madras', 'mecca', 'medusa',
    'midland', 'morocco', 'nelson', 'newton', 'oxford', 'phoebe', 'pueblo',
    'ritz', 'roman', 'savoy', 'sexton', 'spiegel', 'trojan', 'ulster', 'zaire',
}

# Adult content. "liaison" is deliberately kept: WordNet's first sense is the
# illicit one, but everyday usage is a liaison officer.
ADULT = {'erotica', 'amour', 'deviate', 'virgin'}

# American-only terms an English speaker would not reach for. Words that merely
# mean something different in the two countries (bonnet, chemist, caravan) are
# deliberately kept -- you never need to know what an address word means, only
# how to spell it.
def anglo_filters():
    """(american -> british spelling map, american-only set).

    Two accepted spellings no longer disqualify a word. Both forms decode to the
    same address instead, so "grey" and "gray" are one entry with two written
    forms. The British spelling is canonical, since this is a UK scheme.
    """
    pairs = npm_json(
        "require('american-british-english-translator/data/american_spellings.json')")
    aliases = {k.lower(): v.lower() for k, v in pairs.items()
               if isinstance(v, str) and k.isalpha() and v.isalpha()
               and k.lower() != v.lower() and k.lower() not in SPELLING_KEEP}
    us_only = {k.lower() for k in npm_json(
        "require('american-british-english-translator/data/american_only.json')")
        if ' ' not in k and k.isalpha()} - US_KEEP
    return aliases, us_only


def common_words():
    """The commonest tiers of English, cumulative. Both the general and the
    British sets: the general ones are American-leaning, and would rule out
    colour, grey, humour, catalogue and defence."""
    out = set()
    for tier in COMMON_TIERS:
        for key in (f'english/{tier}', f'english/british/{tier}'):
            out |= set(npm_json(f"require('wordlist-english')[{key!r}]"))
    return out

HERE = os.path.dirname(os.path.abspath(__file__))


def npm_json(expr):
    """Pull a JSON blob out of an installed npm package. Runs node from this
    script's directory so require() finds ./node_modules regardless of cwd."""
    try:
        return json.loads(subprocess.check_output(
            ['node', '-e', f'console.log(JSON.stringify({expr}))'], cwd=HERE))
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(f'Missing npm packages. Run:  npm install --prefix {HERE}')

def load():
    return dict(
        cmu=npm_json("require('cmu-pronouncing-dictionary').dictionary"),
        block=set(npm_json("require('naughty-words').en")) | set(npm_json("require('profane-words')")),
        stop=set(npm_json("require('stopword').eng")),
        wndir=npm_json("require('wordnet-db').path"),
    )

def wordnet(wndir):
    """Noun lemmas, proper nouns, and the hypernym graph."""
    lower, upper, hyper = set(), set(), {}
    for line in open(f'{wndir}/data.noun', encoding='latin-1'):
        if line.startswith('  '):
            continue
        head = line.split(' | ')[0].split()
        wc = int(head[3], 16)                    # w_cnt is hex
        for i in range(wc):
            w = head[4 + 2 * i]
            if '_' not in w:
                (upper if w[0].isupper() else lower).add(w.lower())
        rest = head[4 + 2 * wc:]
        ptrs = rest[1:]
        hyper[head[0]] = [ptrs[i * 4 + 1] for i in range(int(rest[0]))
                          if ptrs[i * 4] in ('@', '@i') and ptrs[i * 4 + 2] == 'n']
    senses = {}
    for line in open(f'{wndir}/index.noun', encoding='latin-1'):
        if line.startswith('  '):
            continue
        p = line.split()
        senses[p[0]] = [x for x in p if re.fullmatch(r'\d{8}', x)]
    verbs = {l.split()[0] for l in open(f'{wndir}/index.verb', encoding='latin-1')
             if not l.startswith('  ')}
    return set(senses), verbs, upper - lower, senses, hyper


def sensitive_filter(senses, hyper, roots_words=None, depth=None):
    """True for anything under one of `roots_words` in the hypernym graph.

    depth=None checks every sense (right for diseases and weapons -- one bad
    sense is enough to disqualify). depth=1 checks only the dominant sense
    (right for religion, where many ordinary words carry an obscure religious
    sense).
    """
    roots = {o for w in (roots_words or BAD_ROOTS) for o in senses.get(w, [])}
    cache = {}

    def ancestors(off):
        if off not in cache:
            seen, stack = set(), [off]
            while stack:
                for up in hyper.get(stack.pop(), []):
                    if up not in seen:
                        seen.add(up)
                        stack.append(up)
            cache[off] = seen
        return cache[off]

    def bad(w):
        considered = senses.get(w, []) if depth is None else senses.get(w, [])[:depth]
        return any(o in roots or (ancestors(o) & roots) for o in considered)
    return bad

# Plurals no rule derives from the singular. A singular/plural PAIR in the list
# is the dangerous case -- it is what made what3words addresses confusable -- and
# the distinctness rules already make pairs impossible, since table/tables and
# mouse/mice differ by one phoneme. These cover the isolated forms.
IRREGULAR_PLURALS = {
    'teeth', 'feet', 'geese', 'mice', 'lice', 'men', 'women', 'children',
    'people', 'oxen', 'dice', 'pence', 'cacti', 'fungi', 'data', 'media',
    'indices', 'crises', 'alumni', 'criteria', 'phenomena', 'stimuli', 'bacteria',
}


def inflected(w, nouns, verbs):
    """Plurals, gerunds, participles and agent nouns -- they add confusable
    pairs (wallop/wallops) without adding distinct concepts."""
    if w in IRREGULAR_PLURALS:
        return True
    # -ies is three characters back to the singular, not two: flies -> fly.
    if w.endswith('ies') and w[:-3] + 'y' in nouns:
        return True
    if w.endswith('s') and (w[:-1] in nouns or w[:-2] in nouns):
        return True
    if w.endswith('es') and w[:-2] in nouns:
        return True
    if w.endswith('ing') and (w[:-3] in verbs or w[:-3] + 'e' in verbs or w[:-4] in verbs):
        return True
    if w.endswith(('ed', 'er')) and (w[:-2] in verbs or w[:-1] in verbs):
        return True
    return False

def main(count=COUNT):
    from wordfreq import zipf_frequency
    src = load()
    nouns, verbs, proper, senses, hyper = wordnet(src['wndir'])
    to_uk, us_only = anglo_filters()
    common = common_words()
    # WordNet and the CMU dictionary are American, so the American spelling
    # drives the pipeline and the British one is what gets published -- but only
    # when the British form is itself a legal entry. "catalogue" is nine letters
    # and "yoghurt" has no CMU pronunciation, so those stay American.
    def display(w):
        uk = to_uk.get(w)
        if uk and LENGTH[0] <= len(uk) <= LENGTH[1] and uk in cmu:
            return uk
        return w
    sensitive = sensitive_filter(senses, hyper)
    religious = sensitive_filter(senses, hyper, FAITH_ROOTS, depth=1)
    cmu = src['cmu']

    pool = [w for w in nouns
            if re.fullmatch(rf'[a-z]{{{LENGTH[0]},{LENGTH[1]}}}', w)
            and w in cmu
            and w not in src['stop'] and w not in proper and w not in src['block']
            and not inflected(w, nouns, verbs)
            and not sensitive(w) and not religious(w)
            and w not in FAITH_WORDS
            and w not in us_only
            and (w in common or to_uk.get(w) in common)
            and w not in PROPER_NOUNS and w not in ADULT]
    freq = {w: zipf_frequency(w, 'en') for w in pool}
    pool = [w for w in pool if BAND[0] <= freq[w] <= BAND[1]]
    # How many Latin-script languages know this word -- Tirosh's "internationally
    # recognisable" criterion, measured rather than judged.
    intl = {w: sum(1 for l in LANGS if zipf_frequency(w, l) >= 2.0) for w in pool}

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

    # Greedy, most internationally recognisable first, so those win collisions.
    ordered = sorted(pool, key=lambda w: (-intl[w], -freq[w], w))
    sounds, spellings, phone_nbrs, out, alias_of = set(), set(), set(), [], {}
    for w in ordered:
        # A word's alternate spelling has to be as distinct from everything else
        # as the word itself, or a typo could land on the wrong address instead
        # of being caught. The two forms are exempt from each other, since they
        # decode to the same place.
        forms = {w, display(w)}
        # Both spellings sound the same, so one pronunciation covers the pair.
        key = phkey(w)
        near_spelling = set().union(*(dels(f) for f in forms))
        near_sound = dels(key)
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
        if len(forms) > 1:
            alias_of[w] = display(w)         # american spelling -> published one

    # Truncating costs precision but sharply improves word quality: the tail of
    # the selection is whatever survived the distinctness rules, not good words.
    full = len(out)
    if count > full:
        sys.exit(f'Only {full:,} words survived selection; cannot supply {count:,}.')
    out = out[:count]
    n = len(out)
    box = 9.92141e11  # UK + Ireland bounding box, m^2
    mean = sum(intl[w] for w in out) / n
    kept = set(out)
    published_set = {display(w) for w in out}
    aliases = {us: uk for us, uk in alias_of.items() if us in kept}
    # Also accept the American spelling of any word that entered under its
    # British form -- "grey" is a WordNet lemma in its own right, so "gray"
    # would otherwise not decode. But an alias has to be as distinct as a real
    # entry: "gray" is one edit from "grab" and "gravy", so accepting it would
    # make a typo of those resolve silently to grey's address. Those are refused.
    accepted = set(published_set) | set(aliases)
    index = set().union(*(dels(f) for f in accepted))
    for us, uk in sorted(to_uk.items()):
        if uk not in published_set or us in accepted:
            continue
        near = dels(us)
        own = dels(uk)
        if near & (index - own):
            continue                          # collides with a different address
        aliases[us] = uk
        accepted.add(us)
        index |= near
    published = sorted(published_set)
    print(json.dumps(published, indent=0))
    with open(os.path.join(HERE, '..', '..', 'data', 'aliases.json'), 'w') as fh:
        json.dump(dict(sorted(aliases.items())), fh, indent=0)
    print(f'{full:,} words survived selection; kept top {n:,}', file=sys.stderr)
    print(f'{len(aliases):,} accepted alternate spellings written to data/aliases.json',
          file=sys.stderr)
    print(f'3-word cell {math.sqrt(box / n ** 3):.2f} m; '
          f'mean {mean:.1f}/{len(LANGS)} languages, worst {min(intl[w] for w in out)}',
          file=sys.stderr)

if __name__ == '__main__':
    n = COUNT
    if '--count' in sys.argv:
        n = int(sys.argv[sys.argv.index('--count') + 1])
        root = math.isqrt(n)
        if root * root != n:
            print(f'warning: {n:,} is not a perfect square; a {root}x{root + 1} grid '
                  'makes cell aspect drift with depth', file=sys.stderr)
    main(n)
