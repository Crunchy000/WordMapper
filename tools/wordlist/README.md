# A word list meant to be spoken

BIP-39 is designed to be **typed and checksummed**. Its one guarantee is unique
four-letter prefixes, which says nothing about what happens when someone reads a
word down a phone line. Scored against the CMU Pronouncing Dictionary:

| | BIP-39 | this list |
|---|---|---|
| outright homophones | **116 pairs**, 213 words (10.4 %) | **0** |
| one confusable feature apart | 1,895 pairs, 1,087 words (53.1 %) | **0** |
| within one phoneme error | 5,332 pairs, 1,417 words (69.2 %) | **0** |
| syllables in a 5-word address | 8.6 | 11.9 |
| mean letters | 5.4 | 7.1 |

`pair`/`pear`, `peace`/`piece`, `right`/`write` and `wear`/`where` are all in
BIP-39, and so are `bomb`/`palm`, `cash`/`catch`, `body`/`buddy`, `angle`/`ankle`
and `free`/`three`. The cost of fixing that is three extra syllables per address:
this list is 2–3 syllable words, because one syllable is where the confusable
pairs live and there is no redundancy in them to survive a dropped phoneme.

## Running it

```
apt-get install wamerican wbritish        # a word list WITH capitalisation
pip install geonamescache                 # cities, countries, states
WORDLIST_DATA=<data-dir> python3 build.py --out spoken-2048.txt
WORDLIST_DATA=<data-dir> python3 build.py --audit some-other-list.txt
```

`<data-dir>` holds four files that are not in this repository, because they are
large and each has its own licence:

| file | what | source |
|---|---|---|
| `cmudict.txt` | pronunciations | CMU Pronouncing Dictionary 0.7b |
| `en50k.txt` | word frequencies | `hermitdave/FrequencyWords`, English 50k |
| `names.txt` | given names | any first-names list |
| `surnames.csv` | surnames | US Census surname file |
| `badwords.txt` | slurs and obscenity | any blocklist |

The first run computes isolation for every candidate against 30,000 common
words, which takes a few minutes; it is cached in `.isolation.json` so that the
selection rules can be tuned without paying for it again.

## How it is built, and why in that order

**Content first, sound second.** A word that is offensive, a name, religious or
grim is out whatever it sounds like, so the phonetic stage never has to choose
between a good word and a clean one.

0. **The pool starts from this list's predecessor AND BIP-39.** BIP-39's words
   are already known to be typable and unambiguous in print; what nobody
   checked is how they sound. They face the same rules as everything else,
   which is how `pair`, `pear`, `peace`, `piece`, `right` and `write` get
   sorted out rather than shipped.

1. **`pool.py`** — every 1–3 syllable word, 4–9 letters, common enough to be
   recognised (top 32,000), minus:
   - anything with two pronunciations (`read`, `live`, `bow`, `wind`): a
     heteronym cannot be said unambiguously;
   - **proper nouns**, caught by capitalisation in the system dictionary. This
     is the one signal that works. A crowd-sourced list like `words_alpha` holds
     `gatsby`, `hitler`, `jehovah` and `bethlehem` in lower case, so it cannot
     tell them from real words;
   - **places**, from a gazetteer, above 200,000 people. The floor matters: with
     every village included, `police`, `freedom`, `airport` and `weasel` are all
     towns somewhere and the filter eats the list;
   - **inflections of words that exist** — `planets` when `planet` does. See
     below;
   - **words spelled two ways** — `colour`/`color`, `centre`/`center`,
     `analyse`/`analyze`. Neither form can be dictated without a follow-up
     question, so the word is unusable at all;
   - **compounds** — `landlady` is land + lady, `ladybug` is lady + bug,
     `boyfriend`, `cowboy`, `busboy` and `boyhood` are all boy + something.
     Phonetic distance says these are far apart, and phonetic distance is the
     wrong ruler: a listener does not compare whole words, they mishear a word
     boundary, and a shared component is a shared way to do it. It costs a few
     good words to accidental splits (`capable` is cap + able) and the pool can
     afford them;
   - **what a word MEANS**, from WordNet (`semantic.py`) — `lustful`, `cervix`,
     `puberty` and `syphilis` all walked through a hand-written blocklist,
     because a blocklist holds only what someone thought of. WordNet knows each
     of them is a state of sexual desire, an opening to the uterus, the onset
     of sexual maturity, a venereal disease. Two senses deep, never all of
     them: read every sense and English will tell you a banana is a
     reproductive structure and a mother is a nun. `allow-semantic.txt` records
     every word the filter is wrong about, so it can stay strict;
   - the hand lists: `function-words.txt`, `exclude-religious.txt`,
     `exclude-negative.txt`, `exclude-proper.txt`, `exclude-register.txt`.

2. **`isolation.py`** — how far each survivor stands from its nearest neighbour
   in the *rest of the language*, not just from the list.

3. **`build.py`** — takes them in order, skipping any word that a single
   mishearing or a single keystroke could confuse with one already taken.

   A unique short prefix is a **preference, not a rule**. BIP-39 guarantees
   unique four-letter prefixes so a seed phrase can be typed short; as a hard
   rule here it cost more than everything else put together — over a thousand
   candidates — and pushed the selection out of common vocabulary into
   `abattoir`, `bivouac` and `gazpacho`. So the build takes every word whose
   three-letter prefix is still free, then fills the remainder from what is
   left: **1,017 of 2,048** are the only word with their first three letters,
   and not one word was lost to the rule.

### Why isolation is a tie-break and not a sort key

When a confusable set has to be reduced to one survivor, the one to keep is not
the most common — it is the one hardest to confuse with anything *else* in
English, because it has to survive contact with the whole language.

But sorting by that alone gives a list of `gazpacho`, `bivouac` and `sprocket`:
rare long words are exactly what stands apart from the language, so isolation and
familiarity pull in opposite directions. Only 471 words are both common and fully
isolated, against the 2,048 needed. So familiarity leads in **coarse bands** and
isolation decides within a band. Members of a confusable set are almost always of
comparable frequency, so they land in one band and the most isolated of them wins
it — the rule wanted — while the list stays made of words people know.

A word with an **exact homophone anywhere in the language** is barred outright,
however common it is: `principal` cannot be dictated without `principle` being
written down instead, and that is true whether or not `principle` is on the list.

### Plurals

Both halves of a plural pair can never both be on the list — adding /s/ costs a
full phoneme and the margin is 2.0, and they share a four-letter prefix besides.
The reason to exclude inflections anyway is the **stray** plural: a speaker says
`planet` and a listener writes `planets`. If `planets` is not a word on the list
that is a *detected* error. If the list held it as an independent entry, one
stray keystroke would silently mean somewhere else.

The rule needs the base form to actually exist. An earlier version matched the
ending alone and threw away `water`, `number`, `address`, `glass`, `island`,
`friend`, `silver`, `weather` and `shoulder` — 42 of 43 good words in a spot
check. Endings split into **strong** (`-ed`, `-ing`, `-s`: nothing has a real
word as its stem by accident) and **weak** (`-er`, `-est`, `-ly`: `number`/`numb`
and `corner`/`corn` collide, so the base must be the commoner of the two).

## The margin

Every pair on the list is at least **2.0** apart, where one substitution,
insertion or deletion costs 1.0 and a *confusable* substitution costs 0.5 —
`free`/`three`, `lamp`/`ramp`, `pin`/`pen`. So no single phoneme error and no
pair of confusable ones can turn one word into another.

2.5 would be better and is not available: the pool yields well under 2,048 words
there. 2,048 is 11 bits exactly, with nothing wasted rounding to a word boundary,
so **2.0 is the strictest margin an 11-bit list can have**.

## What is measured and what is judgement

Everything in the table at the top is measured and re-checkable with `--audit`.

The **tone** of the list is not, and no rule reaches it. The exclusion files are
hand-written, deliberately over-broad, and meant to be read and argued with.
They exist because reading the generated list is the only thing that finds
`lustful`, `bozo`, `iphone` and `landlady` — measurement finds none of them.
`exclude-register.txt` is the clearest case: slang and brand names are *common*,
so frequency actively argues for keeping them.

They will not be complete. Read the output before adopting it.
