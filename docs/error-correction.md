# Self-correcting addresses

An address can repair itself. Reference implementation in
[`tools/codec/wordcode.py`](../tools/codec/wordcode.py), tests in
[`test_wordcode.py`](../tools/codec/test_wordcode.py), and the demo shows both
forms once three words are chosen.

## The field falls out for free

The word list is **1,849 = 43²** and 43 is prime, so **GF(1849) is a genuine
finite field** and one word is exactly one field element — no wasted symbols, and
every check value is itself a valid word.

This is now a *binding* constraint rather than a happy accident. The list size
must be the square of a prime to be both a square grid and a field: 46² = 2,116
is a fine grid and no field at all, so a word list capped at 2,167 words lands on
43², not 46².

## Two lengths, nested

| Form | Corrects | Detects |
|---|---|---|
| 3 words + 1 check | any single **erasure** | any single error, any word-order swap |
| 3 words + 2 checks | any single **error** at unknown position | as above |

The 4-word address is a **prefix** of the 5-word one, so the shorter is just the
longer with its last word dropped.

## Why four words is enough in practice

The Singleton bound says correcting an error at an *unknown* position costs two
check symbols; correcting an **erasure** — a symbol known to be wrong — costs one.

The word list turns errors into erasures. It is a tiny subset of English and no
two entries are within one edit of each other, so a mistyped or misheard word is
simply *not in the list*, and its position is therefore known. Measured over
every single-character variant of every word:

| Variant | Cases | Land on another valid word |
|---|---|---|
| substitution | 425,725 | 0 |
| deletion | 16,593 | 0 |
| insertion | 498,759 | 0 |
| transposition | 13,784 | 0 |
| **total** | **954,861** | **0** |

So single-error *correction* costs one check word rather than two. The
distinctness rule that made the word list expensive to build is what pays for
this.

## Weighted checks, not a sum

Each position carries a distinct weight. The obvious alternative — sum the three
words — is **blind to word-order swaps**, because addition is commutative;
measured, it detects 0% of them. Weighting detects 100% and still recovers
erasures. Same length, strictly better.

The second check uses the squares of the first check's weights, which makes any
two columns of the parity-check matrix independent and gives the 5-word code
minimum distance 3.

## Verified

`python3 tools/codec/test_wordcode.py` — every case at 5,000 trials unless noted:

- 4-word address is a prefix of the 5-word one
- clean input accepted at both lengths, no false corrections
- single erasure corrected at both lengths
- 4 words: single error detected (cannot locate — as the bound requires)
- 5 words: single error **corrected** at unknown position
- word-order swaps never silently accepted, at both lengths
- **118,350 real single-character typos, 100% auto-corrected**

The demo's JavaScript codec is cross-checked against this Python one over 4,000
random addresses — zero mismatches in either form.

## What it will not do

One valid word replaced by a *different valid* word — someone reads the wrong
line entirely. The 4-word form detects it; only the 5-word form corrects it.
Two simultaneous errors need 7 words and are out of scope.

## Cost

The check words carry no location, so precision stays at the three-word level.
That is the right trade: a fourth *location* word would reach ~0.3 m, well past
useful, whereas a fourth *check* word makes a 4-metre address that repairs
itself.
