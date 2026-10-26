#!/usr/bin/env python3
"""Five everyday words for any place on earth, on Uber's H3 hexagon grid.

FIVE WORDS NAME ONE H3 RESOLUTION-14 HEXAGON: 1.5 m on an edge, about 2.7 m
across and 6.3 m^2 on average -- smaller than a what3words square. Nothing else
is needed to decode them: no reference point, no network, no database.

WHY RESOLUTION 14. Five words from a 1,296-word list are 1,296**5 = 3.66
quadrillion combinations. H3 has 122 * 7**14 = 82.7 trillion resolution-14
index slots, which fits 44 times over, and the 44 is a check: a misheard word
is refused about 98 % of the time. Resolution 15 also fits, but only 6 times
over -- a 0.9 m^2 hexagon with a 1-in-6 check, a worse trade.

THE FIVE WORDS ARE ONE NUMBER, NOT ONE WORD PER LEVEL. 7**4 = 2,401 does not
fit in a word, so no word can carry whole H3 levels deep enough to reach
resolution 14 in five. The cell is numbered, the check is folded in, and the
result is written in base 1,296:

    ordinal  = base cell * 7**14 + its fourteen digits read in base 7
    value    = ordinal * 44 + check         (check: sha256 of the cell, mod 44)
    number   = SCRAMBLE(value)              (a keyed permutation of 1296**5)
    words    = number in base 1296, five digits

THE SCRAMBLE MAKES THE REST OBVIOUS. The one misheard word in 44 that passes
the check would otherwise land next door, plausible and hard to spot. With the
scramble, changing any one word sends the address to an unrelated place
anywhere on earth -- usually an ocean or another continent. The price is that
neighbouring places share no words, and there is no shorter form.

The scramble is a six-round Feistel network over two halves of 60,466,176
each: 1296**5 is 6**20, exactly (6**10)**2, so it is a bijection on every
five-word combination with nothing left over.
"""
import hashlib, math, os

import h3.api.basic_int as h3

LIST_SIZE = 1296            # the word list
N_WORDS = 5
SPACE = LIST_SIZE ** N_WORDS                     # 3,656,158,440,062,976 addresses
BASE_CELLS = 122            # H3's resolution-0 cells
APERTURE = 7                # children per H3 cell
RES = 14                    # 1.5 m edge, 6.3 m^2
CELLS = BASE_CELLS * APERTURE ** RES             # 82,743,214,887,578 index slots
CHECK = SPACE // CELLS                           # 44, the whole factor to spare
USED = CELLS * CHECK                             # values that name a cell
HALF = math.isqrt(SPACE)    # 60,466,176: SPACE == HALF ** 2, the Feistel halves
ROUNDS = 6
SEP = '.'
assert HALF * HALF == SPACE and CHECK == 44

_HERE = os.path.dirname(os.path.abspath(__file__))

# 1,296 words, every one graded CEFR A1-B2 -- the vocabulary a person can
# retrieve under pressure -- with everything confusable or sound-alike removed.
# Built by tools/wordlist; see that directory's README for how and why.
WORDLIST = os.path.join(_HERE, '..', 'wordlist', 'spoken-1296-plain.txt')
WORDLIST_SHA256 = '2c8879100afeb330d01b91cd86ce89419c7602ad0895d0fdf61ac8cad1842e53'


def load_wordlist(path=WORDLIST):
    with open(path, 'rb') as fh:
        raw = fh.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != WORDLIST_SHA256:
        raise ValueError(f'{path} is not the expected word list (sha256 {got})')
    words = raw.decode().split()
    assert len(words) == LIST_SIZE, len(words)
    return words


_index_cache = (None, None)


def _index(words):
    """word -> value, built once."""
    global _index_cache
    if _index_cache[0] is not words:
        _index_cache = (words, {w: i for i, w in enumerate(words)})
    return _index_cache[1]


def _sha_int(data, nbytes):
    return int.from_bytes(hashlib.sha256(data).digest()[:nbytes], 'big')


# --- H3 cells as ordinals -----------------------------------------------------
# The 64-bit H3 cell index: mode 1 at bits 59-62, resolution at 52-55, base cell
# at 45-51, then fifteen 3-bit digits, resolution 1 highest, unused ones 7.

def cell_to_ordinal(cell):
    """A resolution-14 cell as a number in [0, CELLS)."""
    x = (cell >> 45) & 0x7F
    for r in range(1, RES + 1):
        x = x * APERTURE + ((cell >> ((15 - r) * 3)) & 7)
    return x


def ordinal_to_cell(x):
    """The H3 index for an ordinal. Not necessarily valid: a pentagon has no
    children on one axis."""
    digits = []
    for _ in range(RES):
        x, d = divmod(x, APERTURE)
        digits.append(d)
    h = (1 << 59) | (RES << 52) | (x << 45)
    for r in range(1, 16):
        h |= (digits[RES - r] if r <= RES else 7) << ((15 - r) * 3)
    return h


def cell_at(lat, lng):
    return h3.latlng_to_cell(lat, lng, RES)


def _check(cell):
    """One of CHECK values for the cell."""
    return _sha_int(cell.to_bytes(8, 'big'), 8) % CHECK


# --- the scramble -------------------------------------------------------------

def _round(i, half):
    return _sha_int(bytes([i]) + half.to_bytes(4, 'big'), 8) % HALF


def scramble(v):
    """A keyed permutation of [0, SPACE): a balanced Feistel network, so it is
    a bijection by construction."""
    left, right = divmod(v, HALF)
    for i in range(ROUNDS):
        left, right = right, (left + _round(i, right)) % HALF
    return left * HALF + right


def unscramble(n):
    left, right = divmod(n, HALF)
    for i in reversed(range(ROUNDS)):
        left, right = (right - _round(i, left)) % HALF, left
    return left * HALF + right


# --- addresses ----------------------------------------------------------------

def number_to_words(n, words):
    """A number in [0, SPACE) as N_WORDS words, most significant first."""
    out = []
    for _ in range(N_WORDS):
        n, d = divmod(n, LIST_SIZE)
        out.append(words[d])
    return out[::-1]


def encode_cell(cell, words):
    return number_to_words(scramble(cell_to_ordinal(cell) * CHECK + _check(cell)), words)


def encode(lat, lng, words):
    """The five words for a point."""
    return encode_cell(cell_at(lat, lng), words)


def decode_cell(spoken, words):
    """The H3 cell five words name. Raises ValueError for a wrong word, when it
    can tell: about 98 % of the time."""
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    if len(spoken) != N_WORDS:
        raise ValueError(f'an address is {N_WORDS} words')
    n = 0
    for w in spoken:
        n = n * LIST_SIZE + index[w]
    v = unscramble(n)
    if v >= USED:
        raise ValueError('no such address - a word is wrong')
    ordinal, chk = divmod(v, CHECK)
    cell = ordinal_to_cell(ordinal)
    if not h3.is_valid_cell(cell):
        raise ValueError('no such cell - a word is wrong')
    if _check(cell) != chk:
        raise ValueError('check failed - a word is wrong')
    return cell


def decode(spoken, words):
    """The centre of the cell five words name."""
    return h3.cell_to_latlng(decode_cell(spoken, words))


def format_address(spoken):
    return SEP.join(spoken)


def parse_address(text):
    """Split 'a.b.c.d.e', 'a b c d e' or 'a, b, c, d, e' into words."""
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts
