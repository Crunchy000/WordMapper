#!/usr/bin/env python3
"""Three everyday words for any place on earth, on Uber's H3 hexagon grid.

THREE WORDS NAME ONE H3 RESOLUTION-8 HEXAGON: 531 m on an edge, 0.74 km^2 on
average, a neighbourhood. Nothing else is needed to decode them -- no reference
point, no network, no database.

WHY RESOLUTION 8. Three words from a 1,296-word list are 1,296**3 = 2.18
billion combinations. H3 has 122 * 7**8 = 703 million resolution-8 index
slots, which fits three times over; resolution 9 would need 4.9 billion, which
does not. So the address is resolution 8, and the factor of three to spare is
a check: a misheard word is caught about two times in three.

THE THREE WORDS ARE ONE NUMBER, NOT ONE WORD PER LEVEL. 7**4 = 2,401 does not
fit in a word, so no word can carry whole H3 levels deep enough to reach
resolution 8 in three. The cell is numbered, the check is folded in, and the
result is written in base 1,296:

    ordinal  = base cell * 7**8 + its eight digits read in base 7
    value    = ordinal * 3 + check          (check: sha256 of the cell, mod 3)
    number   = SCRAMBLE(value)              (a keyed permutation of 1296**3)
    words    = number in base 1296, three digits

THE SCRAMBLE IS THE SAFETY. A check of 3 cannot stop a misheard word, so the
next best thing is to make one obvious. Without the scramble the ordinal keeps
H3's order: a wrong last word would land a few kilometres away, plausible and
hard to spot. With it, changing any one word sends the address to an unrelated
place anywhere on earth -- usually an ocean or another continent. The price is
that neighbouring places share no words, and there is no shorter form: two
words do not name a bigger area.

The scramble is a six-round Feistel network over two halves of 46,656 each:
1296**3 is exactly 46656**2, so it is a bijection on every three-word
combination with nothing left over.
"""
import hashlib, os

import h3.api.basic_int as h3

LIST_SIZE = 1296            # the word list
N_WORDS = 3
SPACE = LIST_SIZE ** N_WORDS                     # 2,176,782,336 addresses
BASE_CELLS = 122            # H3's resolution-0 cells
APERTURE = 7                # children per H3 cell
RES = 8                     # 531 m edge, 0.74 km^2
CELLS = BASE_CELLS * APERTURE ** RES             # 703,305,722 index slots
CHECK = SPACE // CELLS                           # 3
USED = CELLS * CHECK                             # values that name a cell
HALF = 46656                # SPACE == HALF ** 2, the Feistel halves
ROUNDS = 6
SEP = '.'
assert HALF * HALF == SPACE and CHECK == 3

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
    """A resolution-8 cell as a number in [0, CELLS)."""
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
    return _sha_int(bytes([i]) + half.to_bytes(4, 'big'), 4) % HALF


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

def encode_cell(cell, words):
    n = scramble(cell_to_ordinal(cell) * CHECK + _check(cell))
    return [words[n // LIST_SIZE ** 2], words[n // LIST_SIZE % LIST_SIZE],
            words[n % LIST_SIZE]]


def encode(lat, lng, words):
    """The three words for a point."""
    return encode_cell(cell_at(lat, lng), words)


def decode_cell(spoken, words):
    """The H3 cell three words name. Raises ValueError for a wrong word, when it
    can tell: about two times in three."""
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    if len(spoken) != N_WORDS:
        raise ValueError(f'an address is {N_WORDS} words')
    a, b, c = (index[w] for w in spoken)
    v = unscramble((a * LIST_SIZE + b) * LIST_SIZE + c)
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
    """The centre of the cell three words name."""
    return h3.cell_to_latlng(decode_cell(spoken, words))


def format_address(spoken):
    return SEP.join(spoken)


def parse_address(text):
    """Split 'a.b.c', 'a b c' or 'a, b, c' into words."""
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts
