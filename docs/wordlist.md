# Word list hunt

Notes from building a soundalike-free replacement for the 1,633-word Tirosh
list. Build with `python3 tools/wordlist/build.py`, check with
`python3 tools/wordlist/verify.py data/wordlist.json`. The result is committed
as [`data/wordlist.json`](../data/wordlist.json) — **1,681 words**, exactly 41².

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

**Frequency is a band, not a floor.** A floor alone leaves `one`, `will`, `time`,
`people` at the top, too generic to be memorable. Tirosh's words sit in this
band: `piano` 4.31, `tango` 3.58, `cobalt` 3.37, `gizmo` 2.61.

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

The tail of the selection is whatever survived the rules, not good words. So
truncating trades precision for quality, and the exchange rate is steep:

| Take top | 3-word cell | Mean languages | Worst word | Rarest kept |
|---|---|---|---|---|
| **1,681** | **14.45 m** | **18.2/26** | **9/26** | `snooker`, `equinox` |
| 2,000 | 11.14 m | 16.4/26 | 5/26 | `busby`, `despot` |
| 2,400 | 8.47 m | 14.1/26 | 2/26 | `crozier`, `meiosis` |
| 2,880 | 6.44 m | 12.0/26 | 1/26 | `soapbox`, `trundle` |

**1,681 — exactly the 41² needed to leave no grid cell unaddressed — is also
where word quality is still good.** Every word in it is known in at least 9 of 26
languages. Pushing to 2,880 for 6.4 m admits words one language in 26 knows.

That is a happy coincidence rather than a designed one, and it settles the
question: take the 1,681.

## Conclusions

**The coverage hole closes cleanly.** 1,681 words removes the 8.3% of ground with
no valid 3-word address, with no change to address length and no loss of quality.

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
- **Swapping the list into the demo** — `data/wordlist.json` is not yet wired in;
  `demos/uk-word-grid.html` still carries the inline Tirosh list.
