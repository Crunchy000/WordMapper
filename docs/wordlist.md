# Word list hunt

Notes from building a soundalike-free replacement for the 1,633-word Tirosh
list. Build with `python3 tools/wordlist/build.py [--count N]`, check with
`python3 tools/wordlist/verify.py data/wordlist.json`. The result is
[`data/wordlist.json`](../data/wordlist.json) — **1,849 everyday words**, 43².

The size must be **the square of a prime**. A square grid keeps cell aspect
constant across levels, and p² with p prime is also what makes GF(1,849) a real
finite field, which the self-correcting codec needs. 46² = 2,116 would be a
perfectly good grid and an impossible field — that constraint, not the word
supply, is what fixes the list at 1,849.

## Sources

All install directly — pypi and the npm registry are reachable:

| Source | What it gives |
|---|---|
| `an-array-of-english-words` (npm) | 274,937 English words |
| `cmu-pronouncing-dictionary` (npm) | 135,155 words as ARPAbet phonemes |
| `wordnet-db` (npm) | 55,491 noun lemmas, hypernym graph, capitalisation |
| `wordfreq` (pypi) | Word frequency in 42 languages |
| `naughty-words`, `profane-words` (npm) | 3,129 blocked terms |

The CMU dictionary is the important one. It gives real pronunciations, so
`sail` and `sale` both come out as `S EY1 L` and can be caught as homophones —
something no spelling rule finds. (`flour`/`flower` too.)

## Method

**Compare pronunciations, not spellings.** Each word becomes its stress-stripped
ARPAbet phoneme sequence, one character per phoneme, so ordinary edit distance
applies to the *sequence*. Two words are rejected if their pronunciations are
within one edit — not just identical.

**Use the deletion trick to avoid O(n²).** Two strings are within edit distance 1
if and only if their sets of one-character deletions intersect. Each accepted
word adds its deletion set to a running index, so each candidate costs a few set
lookups instead of millions of comparisons. `verify.py` then checks all 1.4M
pairs brute-force, to confirm the optimisation rather than trust it.

**Exclude concepts via the hypernym graph, not a blocklist.** Words named in
`BAD_ROOTS` (disease, weapon, crime, body part, …) contribute all their senses as
roots, and anything beneath them in WordNet's hypernym graph is dropped. This
generalises where a list cannot: `leprosy`, `hernia`, `apnea` and `blister` are
all caught as diseases without any of them being listed.

**Religion needs a different test: the dominant sense.** Checking every sense
over-reaches wildly, because ordinary words carry obscure religious senses —
`doctor` is a Doctor of the Church, `placebo` was a vespers office, `fox` is
George Fox and `moon` is Sun Myung Moon. Judging a word by its *first* sense
(WordNet orders them by frequency) keeps all of those and still removes `christ`,
`jonah`, `bishop`, `caliph` and the clergy titles.

The hypernym test alone is still leaky: WordNet's first sense of `messiah` is
"any expected deliverer", which sits under no religious root. The remainder came
from scanning first-sense glosses for religious vocabulary and reading the
results by hand — the scan alone also flags `dinner`, `oxen` and `variety`,
where the keyword only appears in an example sentence. Those survivors are in
`FAITH_WORDS`.

The line drawn is **religious vocabulary as a category** — figures, texts,
practices, places, and labels for believers and non-believers — applied across
faiths equally. Dropping only Christian terms would leave an inconsistent list.
Mythology is deliberately *kept*: `dragon`, `phoenix`, `medusa` are folklore
rather than active religion.

**Measure international recognisability rather than judging it.** Tirosh
preferred words legible to non-native speakers. `wordfreq` covers 26 Latin-script
languages, so each word is scored by how many of them know it — `piano`, `hotel`,
`taxi` and `radio` score 26/26; `soapbox` and `trundle` score 1/26. Only
Latin-script languages count: a loanword in Russian or Japanese is written in
another script, so the English spelling would never appear in its corpus.

### What gets filtered

| Gate | Remaining |
|---|---|
| WordNet single-word noun lemmas | 55,491 |
| 3–7 letters, a–z | 22,142 |
| Has a CMU pronunciation | 13,153 |
| Not a stopword | 13,128 |
| Not a proper noun | 10,270 |
| Not on a profanity list | 10,103 |
| Not an inflected form | 8,654 |
| Not a sensitive concept | 7,924 |
| Frequency band (Zipf 2.5–5.0) | 6,053 |
| **Survives distinctness rules** | **2,880** |

Requiring a **WordNet noun lemma** is the highest-value gate: it removes function
words and inflections together, because WordNet indexes base forms.

**Proper nouns come from WordNet's own data** — a lemma never seen lowercase in
any synset is one. That caught `poulenc`, `saratov`, `ustinov`, `tlingit`.

**Frequency is a band, not a floor** (Zipf 3.0–5.0). A floor alone leaves `one`,
`will`, `time`, `people` at the top, too generic to be memorable.

The lower bound was raised from 2.5 to 3.0 to cut words that are technically
English but not in everyday use: `myelin`, `niacin`, `oryx`, `biotin`, `moiety`,
`stover`, `liana`, `tiffin`, `snafu`, `batik`, `troika`, `simian`. The rarest
words now kept are `duchy`, `hummus`, `kiosk`, `acacia`, `ukulele`, `equinox`.

**Two accepted spellings disqualifies a word.** `color`/`colour`,
`humor`/`humour`, `catalog`/`catalogue`, `defense`/`defence`, `disk`/`disc`,
`sulfur`/`sulphur`, `yogurt`/`yoghurt` — a listener cannot know which to write,
which is a stronger objection than nationality. Separately, American-only terms
an English speaker would not reach for are dropped: `mailman`, `freeway`,
`ladybug`, `hobo`, `critter`, `caboose`, `bodega`, `beltway`.

Words that merely *mean* something different in the two countries — `bonnet`,
`chemist`, `caravan`, `pavement` — are deliberately kept. You never need to know
what an address word means, only how to spell it.

## What distinctness costs

The main result. From the same 6,053-word pool:

| Rule | Words | 3-word cell |
|---|---|---|
| Reject homophones only | 5,829 | 2.24 m |
| + no 1-letter neighbours | 3,613 | 4.59 m |
| + no 1-phoneme neighbours | 3,110 | 5.74 m |
| **Both (shipped)** | **2,880** | **6.44 m** |

**Phonetic distinctness, not vocabulary size, is the binding constraint.**
Rejecting outright homophones costs 224 words — nothing. Requiring that no two
words be within *one phoneme* costs nearly half the pool. That single rule is the
whole story.

## The quality dial

Raising the frequency floor costs address space quickly, and the grid can only
land on the square of a prime:

| Floor | Words available | Largest usable grid | 3-word cell |
|---|---|---|---|
| 2.5 | 2,807 | 53×53 = 2,809 (just misses) → 52² not prime → 47×47 | 9.59 m |
| **3.0** | **2,167** | **43×43 = 1,849** | **12.53 m** |
| 3.25 | 1,811 | 41×41 = 1,681 | 14.45 m |
| 3.5 | 1,462 | 37×37 = 1,369 | 16.55 m |

Land masking would recover about 1.64× on any of these, putting the shipped list
at roughly **7.6 m** in practice.

## Conclusions

**The coverage hole is closed.** An exact word-per-cell fit removes the 8.3% of
ground that had no valid 3-word address. The demo's `break` statement, which
caused it, is gone — replaced by a guard that throws if the grid and the word
list ever drift apart again.

**3 m at three words is not reachable.** It needs 4,795 words; the pipeline's
absolute ceiling is 2,880, and that already includes words like `trundle`.

So the trade is quantified: **you cannot have what3words precision *and*
soundalike-free words in three words.** Phonetic distinctness puts a floor of
roughly 6 m on three-word UK addressing, and a defensible-quality floor nearer
14 m. Below that you either relax distinctness — the one property that makes the
scheme worth building — or spend a fourth word.

**Independent validation:** 616 of the 1,681 words (37%) also appear in Tirosh.
The pipeline rediscovered a third of a hand-curated list from mechanical rules,
which is reassuring about both.

## Still to do

- **A human read-through.** The hypernym filter is good but not a substitute for
  judgement; words like `despot`, `zealot` and `addict` survive because they are
  not diseases, weapons or crimes. Tirosh clearly had a human pass here.
- **British vs American spellings** (`centre`/`center`) are separate words; one
  should be picked per pair.
- **Proper nouns still leak occasionally.** `zaire` (a currency unit) and
  `sexton` (WordNet's first sense is the poet Anne Sexton) both got through.
- **`virgin` survives** — its dominant sense is not religious, but it is the
  next thing a human pass should look at. A different category from religion,
  and not one an automated filter is going to settle.
- **`erotica` and `gangsta` survive**, and `heaven` slipped the religion filter.
  A human pass should take these.
- **`spiegel` is another proper-noun leak** (Der Spiegel), joining `zaire` and
  `sexton`.
- **The margin is comfortable now.** 2,167 words survive against the 1,849 that
  43² needs, so there is room for further curation without changing the grid —
  the next step down would be 41² = 1,681.
- **Rendering cost.** At 2,809 words the demo now draws up to 8,428 rectangles
  across three levels, up from 4,900. Issue 13 in the demo review — switching to
  the canvas renderer — matters more than it did.
