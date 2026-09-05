# Word list hunt

Notes from building a soundalike-free replacement for the 1,633-word Tirosh
list. Reproduce with `python3 tools/wordlist/build.py`; the result is committed
as [`data/candidate-wordlist.json`](../data/candidate-wordlist.json).

## Sources

All of these install directly — pypi and the npm registry are reachable:

| Source | What it gives |
|---|---|
| `an-array-of-english-words` (npm) | 274,937 English words |
| `cmu-pronouncing-dictionary` (npm) | 135,155 words as ARPAbet phonemes |
| `wordnet-db` (npm) | 55,491 single-word noun lemmas, sense categories, capitalisation |
| `wordfreq` (pypi) | Zipf frequency, for "would anyone recognise this?" |
| `naughty-words`, `profane-words` (npm) | 3,129 blocked terms |

The CMU dictionary is the important one. It gives real pronunciations, so
`sail` and `sale` both come out as `S EY1 L` and can be caught as homophones —
something no spelling-based rule finds.

## Method

Two ideas do the work.

**Compare pronunciations, not spellings.** Each word becomes its stress-stripped
ARPAbet phoneme sequence, with one character substituted per phoneme so ordinary
edit distance applies to the *sequence*. Two words are rejected as confusable if
their phoneme sequences are within one edit.

**Use the deletion trick to avoid O(n²).** Two strings are within edit distance 1
if and only if their sets of one-character deletions intersect. So each accepted
word contributes its deletion set to a running index, and each candidate is a
few set lookups rather than millions of comparisons.

Selection is greedy in descending frequency, so when two words collide the more
familiar one wins.

### What gets filtered, and why

| Gate | Remaining |
|---|---|
| WordNet single-word noun lemmas | 55,491 |
| 3–7 letters, a–z | 22,142 |
| Has a CMU pronunciation | 13,153 |
| Not a stopword | 13,128 |
| Not a proper noun | 10,270 |
| Not offensive | 10,103 |
| Not an inflected form | 8,654 |

Requiring a **WordNet noun lemma** is the single most useful gate: it removes
function words and inflections in one move, because WordNet indexes base forms.

**Proper nouns** are detected from WordNet's own data rather than a list — a
lemma that never appears lowercase in any synset is a proper noun. That catches
`poulenc`, `saratov`, `ustinov`, `tlingit`.

**Frequency is a band, not a floor** (Zipf 2.5–5.0). A floor alone leaves
`one`, `will`, `time`, `people` at the top, which are too generic to be
memorable. Tirosh's own words sit in this band: `piano` 4.31, `tango` 3.58,
`cobalt` 3.37, `gizmo` 2.61.

## What it costs

The interesting result. Starting from the same 6,660-word pool:

| Rule | Words | 3-word cell |
|---|---|---|
| Reject homophones only | 6,405 | 1.94 m |
| + no 1-letter neighbours | 3,849 | 4.17 m |
| + no 1-phoneme neighbours | 3,299 | 5.26 m |
| **Both (shipped)** | **3,015** | **6.02 m** |

**Phonetic distinctness, not vocabulary size, is the binding constraint.**
Rejecting outright homophones costs almost nothing — 255 words. Requiring that
no two words be within *one phoneme* of each other costs more than half the
list. That single rule is the whole story.

Loosening the frequency band buys a little more, at a visible cost in quality:

| Band | Words | 3-word cell | Rarest kept |
|---|---|---|---|
| 3.0–5.0 | 2,328 | 8.87 m | `soloist`, `stifle` |
| **2.5–5.0** | **3,015** | **6.02 m** | `sherbet`, `soapbox` |
| 2.0–5.0 | 3,443 | 4.93 m | `macrame`, `platen` |
| 1.5–5.0 | 3,633 | 4.55 m | `redpoll`, `baldric` |

## Conclusions

**Closing the coverage hole is comfortably solved.** 1,681 words (41²) removes
the 8.3% of unaddressable ground, and even the strictest, highest-quality
setting yields 2,328 — well past that, with room to spare.

**3 m at three words is not reachable.** It needs 4,795 words. The best any
setting produces is 3,633, and that only by admitting words like `baldric`. The
honest figure for a strict, genuinely soundalike-free list is **3,015 words →
about 6 m**.

So the trade is now quantified: **you cannot have what3words precision *and*
soundalike-free words in three words.** Phonetic distinctness puts a floor of
roughly 6 m on three-word UK addressing. Getting below it means either relaxing
distinctness — which is the one property that makes this scheme worth building —
or spending a fourth word.

## Still to do

The candidate list is **not finished**. Mechanical filtering has taken it as far
as it goes; what remains needs human judgement:

- **Sensitive and unpleasant words.** The profanity lists are passed, but
  `gun`, `cancer`, `disease`, `leprosy`, `hernia` and similar survive. They are
  not profane, they are just wrong for a friendly address scheme. Tirosh clearly
  had a human pass here.
- **Politically loaded and identity terms** need the same review.
- **British vs American spellings** (`centre`/`center`) are treated as separate
  words; one should be picked per pair.
- **International recognisability.** Tirosh favoured words legible to non-native
  English speakers. Zipf frequency is an English-only proxy; `wordfreq` covers
  other languages and could score cross-linguistic familiarity directly.
