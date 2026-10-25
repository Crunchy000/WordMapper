#!/usr/bin/env python3
"""Word addresses from an easy-English word list, on Uber's H3 hexagon grid.

SIX WORDS name any point on earth to one H3 resolution-14 hexagon -- about
three metres across, 6.3 m^2 -- and a misheard word is caught at least 18,251
times in 18,252:

    word.word.
    word.word.
    word.word

THE GRID IS H3. It replaced a square grid on a cylindrical equal-area
projection, whose cells were square only at 55.65 degrees: 1.7 x 5.3 m at the
equator and 9.7 x 0.9 m at 80 degrees. H3 lays hexagons on an icosahedron, so a
cell is close to a regular hexagon everywhere on earth -- six equidistant
neighbours, no diagonals, and the centre is never more than one edge length from
any point in it. H3 is not equal-area (cells vary roughly 2:1 in area across
the globe), which is the price of shape.

THE ADDRESS IS H3's OWN HIERARCHY. A res-14 cell is a base cell (one of 122)
and fourteen base-7 digits, each choosing one of a cell's seven children. Each
word carries a whole number of those digits plus a digit of checksum:

    word         1      2    3    4    5    6
    H3 digits    base+1 3    3    3    2    2
    positions    854    343  343  343  49   49
    check        1      3    3    3    26   26     -> CHECK = 18,252
    resolution   1      4    7    10   12   14

value = position * check + check digit. 7**3 = 343 is the most digits a 1,296
word can hold, and it leaves room for a check of 3; 7**2 leaves 26. The values
past position * check are unused, so a misheard word that lands on one is
rejected outright -- detection on top of the checksum.

WHY THE CHECK SITS AT THE END. Dropping leading words drops their check digits
with them, so the checksum is put where the trailing words keep it: a tail of
five words keeps all 18,252, a tail of three keeps 2,028.

DROP TRAILING WORDS for a coarser address that needs no context: H3's parent
of a cell is the same index with its last digits removed, so every address is a
prefix of a longer one by construction. Note that H3 nests approximately: a
coarse hexagon as DRAWN does not exactly contain its descendants, but the point
is always one of them, and always near the coarse cell's centre.

DROP LEADING WORDS given a reference POINT: resolve_tail() fills them in from
the H3 cells around the reference, takes the one candidate nearest it, and
tests that ONE against the checksum -- so it costs no detection.
"""
import collections, hashlib, math, os

import h3.api.basic_int as h3

R = 6371008.8               # mean earth radius, metres
LIST_SIZE = 1296            # the word list
BASE_CELLS = 122            # H3's resolution-0 cells
APERTURE = 7                # children per H3 cell
RES = 14                    # the full address: about 3 m across

# How many H3 digits each word carries, coarsest first. Word one also carries
# the base cell.
WORD_DIGITS = [1, 3, 3, 3, 2, 2]
MAX_WORDS = len(WORD_DIGITS)
POSITIONS = [APERTURE ** d * (BASE_CELLS if k == 0 else 1)
             for k, d in enumerate(WORD_DIGITS)]        # [854, 343, 343, 343, 49, 49]
CHECKS = [LIST_SIZE // p for p in POSITIONS]            # [1, 3, 3, 3, 26, 26]
CHECK = math.prod(CHECKS)                               # 18,252
RES_AT = [sum(WORD_DIGITS[:n]) for n in range(1, MAX_WORDS + 1)]   # [1, 4, 7, 10, 12, 14]
assert RES_AT[-1] == RES

SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail
# How far around the reference's own cell resolve_tail looks for the dropped
# words. H3 nests approximately, so a point's true ancestor can be a neighbour
# of the cell its reference falls in; two rings covers that with room to spare.
TAIL_RINGS = 2
_HERE = os.path.dirname(os.path.abspath(__file__))

Tail = collections.namedtuple('Tail', 'res digits check modulus divisor')

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


# --- H3 indexes as base cell + digits ----------------------------------------
# The 64-bit H3 cell index: mode 1 at bits 59-62, resolution at 52-55, base cell
# at 45-51, then fifteen 3-bit digits, resolution 1 highest, unused ones 7.

def cell_digits(h):
    """(base cell, [digit at res 1, ..., digit at the cell's res])."""
    res = (h >> 52) & 0xF
    return (h >> 45) & 0x7F, [(h >> ((15 - r) * 3)) & 7 for r in range(1, res + 1)]


def make_cell(base, digits):
    """The H3 index for a base cell and its digits. Not necessarily valid: a
    pentagon has no children on one axis, and base cells stop at 121."""
    h = (1 << 59) | (len(digits) << 52) | (base << 45)
    for r in range(1, 16):
        h |= (digits[r - 1] if r <= len(digits) else 7) << ((15 - r) * 3)
    return h


def cell_at(lat, lng, res=RES):
    return h3.latlng_to_cell(lat, lng, res)


def _checksum(cell):
    """One of CHECK values over the whole res-14 cell."""
    return int.from_bytes(hashlib.sha256(cell.to_bytes(8, 'big')).digest()[:8],
                          'big') % CHECK


def _check_digits(v, checks):
    """One checksum spread across the words, least significant first, so each
    length's check modulus divides the next one's."""
    out = []
    for c in checks:
        out.append(v % c)
        v //= c
    return out


def _undigits_check(digits, checks):
    v = 0
    for d, c in zip(reversed(digits), reversed(checks)):
        v = v * c + d
    return v


def _word_positions(base, digits):
    """Each word's position value, coarsest first: word one is the base cell and
    its first digit, the rest are their digits read as a base-7 number."""
    out, at = [], 0
    for k, n in enumerate(WORD_DIGITS):
        v = base if k == 0 else 0
        for d in digits[at:at + n]:
            v = v * APERTURE + d
        out.append(v)
        at += n
    return out


def _position_digits(k, pos):
    """A word's position value back to (base cell or None, its digits)."""
    n = WORD_DIGITS[k]
    ds = []
    for _ in range(n):
        pos, d = divmod(pos, APERTURE)
        ds.append(d)
    return (pos if k == 0 else None), ds[::-1]


def _word_values(cell):
    base, digits = cell_digits(cell)
    cd = _check_digits(_checksum(cell), CHECKS)
    return [p * c + d for p, c, d in zip(_word_positions(base, digits), CHECKS, cd)]


def encode(lat, lng, words, n_words=MAX_WORDS):
    """The first n_words of the address. Coarser as n_words falls; needs no
    context at any length."""
    if not 1 <= n_words <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    return [words[v] for v in _word_values(cell_at(lat, lng))[:n_words]]


def _split(spoken, words, first):
    """Words to (base, digits, check digits), the first word said being word
    number `first`. Rejects words off the list and values no position uses."""
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    base, digits, cd = None, [], []
    for i, w in enumerate(spoken):
        k = first + i
        pos, chk = divmod(index[w], CHECKS[k])
        if pos >= POSITIONS[k]:
            raise ValueError(f'"{w}" cannot be word {k + 1} - a word is wrong')
        b, ds = _position_digits(k, pos)
        if b is not None:
            base = b
        digits += ds
        cd.append(chk)
    return base, digits, cd


def decode_cell(spoken, words):
    """The H3 cell an absolute address names. A full address is checked."""
    n = len(spoken)
    if not 1 <= n <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    base, digits, cd = _split(spoken, words, 0)
    cell = make_cell(base, digits)
    if not h3.is_valid_cell(cell):
        raise ValueError('no such cell - a word is wrong')
    if n == MAX_WORDS and _checksum(cell) != _undigits_check(cd, CHECKS):
        raise ValueError('checksum failed - a word is wrong')
    return cell


def decode(spoken, words):
    """Resolve an address to the centre of its cell: the first n words, coarser
    as n falls. A full-length address is checked; raises ValueError if a word
    is wrong."""
    return h3.cell_to_latlng(decode_cell(spoken, words))


def _tail(spoken, words):
    """What a tail of n words fixes: the resolution the dropped words reached,
    the digits below it, and the part of the checksum the words said carry --
    `(checksum // divisor) % modulus`, since the dropped words took their own
    check digits with them."""
    n = len(spoken)
    if not 1 <= n <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    dropped = MAX_WORDS - n
    _, digits, cd = _split(spoken, words, dropped)
    return Tail(RES_AT[dropped - 1] if dropped else None, digits,
                _undigits_check(cd, CHECKS[dropped:]),
                math.prod(CHECKS[dropped:]), math.prod(CHECKS[:dropped]))


def hav(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def resolve_tail_cell(spoken, words, near_lat, near_lng):
    """The res-14 cell a tail names, given a reference point.

    The dropped words are the coarse ones, so the reference supplies them: every
    cell at the dropped resolution within TAIL_RINGS of the reference's own is
    a candidate parent, the said digits are appended to each, and the one whose
    centre is nearest the reference is taken. Only that one is tested against
    the checksum, so a reference too far off is caught rather than resolving
    quietly to the wrong place -- and nothing is spent searching.
    """
    t = _tail(spoken, words)
    if t.res is None:
        return decode_cell(spoken, words)
    best, best_d = None, math.inf
    for parent in h3.grid_disk(cell_at(near_lat, near_lng, t.res), TAIL_RINGS):
        base, digits = cell_digits(parent)
        cell = make_cell(base, digits + t.digits)
        if not h3.is_valid_cell(cell):
            continue            # a pentagon has no children on one axis
        d = hav(near_lat, near_lng, *h3.cell_to_latlng(cell))
        if d < best_d:
            best, best_d = cell, d
    if best is None or (_checksum(best) // t.divisor) % t.modulus != t.check:
        raise ValueError('checksum failed - a word is wrong, or the reference '
                         'point is too far away to fill in the missing words')
    return best


def resolve_tail(spoken, words, near_lat, near_lng):
    """Resolve an address given only its last words, plus a reference point."""
    return h3.cell_to_latlng(resolve_tail_cell(spoken, words, near_lat, near_lng))


def words_needed(lat, lng, near_lat, near_lng, words):
    """The fewest trailing words that resolve back to this point from that
    reference, or the full length if even that is needed."""
    full, want = encode(lat, lng, words), cell_at(lat, lng)
    for n in range(1, MAX_WORDS + 1):
        try:
            if resolve_tail_cell(full[-n:], words, near_lat, near_lng) == want:
                return n
        except ValueError:
            continue
    return MAX_WORDS


def edge_length(n_words):
    """H3's average hexagon edge at this address length, in metres -- which is
    also the farthest a point can be from its cell's centre."""
    return h3.average_hexagon_edge_length(RES_AT[n_words - 1], 'm')


def tile_edge(n_said):
    """The ambiguity left by dropping the LEADING words: the average edge of
    the cell the dropped words would have named."""
    return h3.average_hexagon_edge_length(RES_AT[MAX_WORDS - n_said - 1], 'm')


def format_address(spoken, tail=False):
    """'above.hollow.eager' absolute, '.hollow.eager' for a tail."""
    return (TAIL_MARK if tail else '') + SEP.join(spoken)


def parse_address(text):
    """Split into (words, is_tail)."""
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    tail = text.startswith(SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts, tail
