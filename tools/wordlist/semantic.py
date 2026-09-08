#!/usr/bin/env python3
"""What a word MEANS, as a filter -- the part hand lists keep getting wrong.

`lustful`, `cervix`, `puberty` and `syphilis` all survived a hand-written
exclusion list, because a hand list can only hold what someone thought of.
WordNet knows what each of them is: a state of sexual desire, an opening to the
uterus, the onset of sexual maturity, a venereal disease. It knows it for the
whole language at once, which is the difference.

Two questions, because one is not enough. HYPERNYMS say what a thing IS and
carry most of the weight -- syphilis is a disease, cocaine is a narcotic,
a cathedral is a place of worship. But `cervix` and `elbow` are both a `body
part`, and only the DEFINITION separates them, so glosses are read too.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordnet import WordNet

# What a word is a kind of. Each of these is a WordNet synset member, so the
# match is on the taxonomy rather than on a string appearing in the word.
# What a word is a kind of. Each is a WordNet synset member, so the match is on
# the taxonomy rather than on a string appearing in the word.
#
# Every root here was narrowed against the actual output. `wrongdoing` caught
# envy, laziness and gluttony; `reproductive structure` caught banana, peanut
# and pineapple, because a fruit is one; `drug` and `medicine` caught water and
# aspirin; `religious belief` caught mother, brother and office. A root that
# needs a second look is a root that is too high up the tree.
ROOTS = {
    'clinical': {
        'disease', 'illness', 'sickness', 'syndrome', 'infection', 'ailment',
        'health problem', 'pathology', 'malignancy', 'injury', 'trauma',
        'wound', 'internal organ', 'viscus',
    },
    'drugs': {'narcotic', 'drug of abuse', 'controlled substance', 'poison',
              'toxin', 'venom', 'hallucinogen'},
    'violence': {'killing', 'homicide', 'murder', 'execution', 'weapon',
                 'firearm', 'explosive', 'corpse', 'funeral', 'burial',
                 'torture'},
    'sexual': {'sexual desire', 'eroticism', 'sexual activity', 'sex act',
               'sexual intercourse', 'copulation', 'genitalia', 'sex organ',
               'reproductive organ', 'prostitution'},
    'religious': {'place of worship', 'religious person', 'religious ceremony',
                  'deity', 'sacred text', 'clergyman', 'religious residence'},
}

# Read only when the taxonomy cannot separate two words that sit under the same
# node. Deliberately narrow: a gloss is prose, and prose matches by accident.
GLOSS = {
    'sexual': re.compile(
        r'\b(sexual|sexually|genital|genitalia|uterus|uterine|vagina\w*|penis|'
        r'testis|testicle|ovary|ovaries|copulation|intercourse|erotic\w*|'
        r'orgasm\w*|menstrua\w*|lust|prostitut\w*|obscene|incest\w*|'
        r'sex glands?|sex organs?|sex hormones?)\b'),
    'clinical': re.compile(
        r'\b(disease|diseased|infection|infected|inflammation|inflamed|'
        r'tumor|tumour|cancer|cancerous|malignant|carcinoma|abscess|ulcer|'
        r'venereal|contagious|parasit\w*|deformity|paralysis|amputat\w*)\b'),
}


SENSES = 2      # the dominant meaning and its runner-up, never the long tail


def classify(wn, word, senses=SENSES):
    """The category this word falls into, or None. Checked in a fixed order so
    the answer is stable and a word lands in one bucket.

    Two senses, not one and not all. One misses `cervix`, whose first sense is
    the anatomical neck; all of them means every word in English is unpleasant
    somewhere, because English is deeply polysemous and WordNet records the
    rarest sense as readily as the common one."""
    if not wn.loaded:
        return None
    anc = wn.ancestors(word, senses=senses)
    for name in ('sexual', 'violence', 'drugs', 'clinical', 'religious'):
        if anc & ROOTS[name]:
            return name
    text = ' '.join(wn.glosses(word, senses=senses))
    if text:
        for name in ('sexual', 'clinical'):
            if GLOSS[name].search(text):
                return name
    return None
