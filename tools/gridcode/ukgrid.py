#!/usr/bin/env python3
"""Three everyday words for anywhere in the UK.

THREE WORDS NAME ONE SQUARE OF ABOUT 11 METRES anywhere in the UK, the Isle of
Man and the Channel Islands, with a strip of coastal sea. Half of all points
are within about 4.5 m of the centre the words decode to. Nothing else is
needed to decode them: no reference point, no network, no database.

WHY THREE WORDS FIT. Three words from the 1,296-word list are 1,296**3 = 2.18
billion addresses. The UK with its coastal strip is about 280,000 km^2, so
each address gets about 130 m^2.

WHY NOT H3. H3's cells shrink 7x per level, and at UK latitudes resolution 12
is about 270 m^2 while resolution 13 does not fit -- the step lands a factor of
two short of what three words can carry. A flat grid can be sized exactly, and
over an area the size of the UK flat is accurate: a Lambert azimuthal
equal-area projection centred on the UK keeps every square the same area and
square to within 0.2 %.

THE LAYOUT. The projected plane is cut into 2 km SQUARES; a committed mask
(uk-mask.txt) says which are in -- land, plus every square next to land. Each
square in the mask is cut into K x K CELLS. Then:

    rank     = the square's position among the squares in the mask
    value    = (rank * K + row) * K + column
    number   = scramble(value)          a keyed permutation of all 1,296**3
    words    = number in base 1,296

THE SCRAMBLE IS THE SAFETY. There is no check word -- every address the space
can spare goes on precision -- so a misheard word is refused only when it
lands on a value no cell uses. The rest decode, and the scramble sends them
somewhere unrelated in the UK rather than next door. It is the same six-round
Feistel network as the global grid: 1,296**3 is exactly 46,656**2.

AND AN OPTIONAL TWO-DIGIT NUMBER, for when it matters:

    interval level adjective 42

The three words are unchanged and still name the 11 m cell on their own. The
number, 00 to 99, is 4 x 25: which QUARTER of the cell (2 x 2, so a 5.7 m
square) and a CHECK of 1 in 25 over the cell and the quarter together. Said
with the number, a misheard word is caught 96 % of the time, because it names
another cell and the check no longer fits. A misheard number either fails the
check or lands in another quarter of the same cell -- a few metres, never
somewhere else. Said without it, nothing changes.
"""
import hashlib, math, os, re

LIST_SIZE = 1296
N_WORDS = 3
SPACE = LIST_SIZE ** N_WORDS                    # 2,176,782,336
HALF = 46656                                    # SPACE == HALF ** 2
ROUNDS = 6
SEP = '.'
assert HALF * HALF == SPACE

R = 6371008.8               # mean earth radius, metres
LAT0, LNG0 = 54.9, -3.4     # projection centre, roughly the middle of the UK
SQUARE = 2000.0             # metres, the mask's resolution
X0, Y0 = -616000.0, -642000.0                   # south-west corner of the grid
GRID_W, GRID_H = 486, 656                       # squares across and up
K = 0                       # cells per square side, set below from the mask

_HERE = os.path.dirname(os.path.abspath(__file__))
WORDLIST = os.path.join(_HERE, '..', 'wordlist', 'spoken-1296-plain.txt')
WORDLIST_SHA256 = '2c8879100afeb330d01b91cd86ce89419c7602ad0895d0fdf61ac8cad1842e53'
MASK = os.path.join(_HERE, 'uk-mask.txt')


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
    global _index_cache
    if _index_cache[0] is not words:
        _index_cache = (words, {w: i for i, w in enumerate(words)})
    return _index_cache[1]


# --- the projection ----------------------------------------------------------
# Lambert azimuthal equal-area on the sphere, centred on the UK.

_P0, _L0 = math.radians(LAT0), math.radians(LNG0)
_SIN0, _COS0 = math.sin(_P0), math.cos(_P0)


def project(lat, lng):
    p, dl = math.radians(lat), math.radians(lng) - _L0
    sp, cp, cl = math.sin(p), math.cos(p), math.cos(dl)
    k = math.sqrt(2 / (1 + _SIN0 * sp + _COS0 * cp * cl))
    return R * k * cp * math.sin(dl), R * k * (_COS0 * sp - _SIN0 * cp * cl)


def unproject(x, y):
    rho = math.hypot(x, y)
    if rho == 0:
        return LAT0, LNG0
    c = 2 * math.asin(rho / (2 * R))
    sc, cc = math.sin(c), math.cos(c)
    lat = math.asin(cc * _SIN0 + y * sc * _COS0 / rho)
    lng = _L0 + math.atan2(x * sc, rho * _COS0 * cc - y * _SIN0 * sc)
    return math.degrees(lat), math.degrees(lng)


# --- the mask ----------------------------------------------------------------

def _load_mask(path=MASK):
    """Square index (row-major from the south-west) -> rank, and back."""
    with open(path) as fh:
        runs = [int(v) for v in fh.read().strip().split(',')]
    squares, at, inside = [], 0, False
    for n in runs:
        if inside:
            squares.extend(range(at, at + n))
        at += n
        inside = not inside
    assert at == GRID_W * GRID_H, at
    return squares, {s: r for r, s in enumerate(squares)}


# build_uk_mask.py imports this module to project, before any mask exists.
SQUARES, RANK = _load_mask() if os.path.exists(MASK) else ([], {})
# As many cells per side as the space allows: K*K cells in every square.
K = math.isqrt(SPACE // len(SQUARES)) if SQUARES else 1
CELL = SQUARE / K
CELLS = len(SQUARES) * K * K                    # values that name a cell


# --- the scramble ------------------------------------------------------------

def _sha_int(data, nbytes):
    return int.from_bytes(hashlib.sha256(data).digest()[:nbytes], 'big')


def _round(i, half):
    # The 'uk' prefix keys this scramble apart from the global grid's.
    return _sha_int(b'uk' + bytes([i]) + half.to_bytes(4, 'big'), 4) % HALF


def scramble(v):
    left, right = divmod(v, HALF)
    for i in range(ROUNDS):
        left, right = right, (left + _round(i, right)) % HALF
    return left * HALF + right


def unscramble(n):
    left, right = divmod(n, HALF)
    for i in reversed(range(ROUNDS)):
        left, right = (right - _round(i, left)) % HALF, left
    return left * HALF + right


# --- addresses ---------------------------------------------------------------

class OutsideUK(ValueError):
    """Raised for a point no square of the mask covers."""


def value_at(lat, lng):
    """The cell value of a point, before scrambling."""
    x, y = project(lat, lng)
    fx, fy = (x - X0) / SQUARE, (y - Y0) / SQUARE
    i, j = math.floor(fx), math.floor(fy)
    rank = RANK.get(j * GRID_W + i) if 0 <= i < GRID_W and 0 <= j < GRID_H else None
    if rank is None:
        raise OutsideUK(f'{lat:.5f}, {lng:.5f} is outside the UK grid')
    col = min(int((fx - i) * K), K - 1)
    row = min(int((fy - j) * K), K - 1)
    return (rank * K + row) * K + col


def centre_of(v):
    """The centre of the cell a value names, as (lat, lng)."""
    rank, rest = divmod(v, K * K)
    row, col = divmod(rest, K)
    j, i = divmod(SQUARES[rank], GRID_W)
    return unproject(X0 + i * SQUARE + (col + 0.5) * CELL,
                     Y0 + j * SQUARE + (row + 0.5) * CELL)


def number_to_words(n, words):
    out = []
    for _ in range(N_WORDS):
        n, d = divmod(n, LIST_SIZE)
        out.append(words[d])
    return out[::-1]


def encode(lat, lng, words):
    """The three words for a point in the UK. Raises OutsideUK elsewhere."""
    return number_to_words(scramble(value_at(lat, lng)), words)


def decode_value(spoken, words):
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
    if v >= CELLS:
        raise ValueError('no such address - a word is wrong')
    return v


def decode(spoken, words):
    """The centre of the cell three words name."""
    return centre_of(decode_value(spoken, words))


# --- the optional number -------------------------------------------------------

QUARTERS = 2                # the number splits a cell QUARTERS x QUARTERS
DIGIT_CHECK = 100 // (QUARTERS * QUARTERS)       # 25: what is left is check
assert QUARTERS * QUARTERS * DIGIT_CHECK == 100


def _digit_check(v, q):
    return _sha_int(b'ukd' + v.to_bytes(8, 'big') + bytes([q]), 8) % DIGIT_CHECK


def quarter_at(lat, lng):
    """Which quarter of its cell a point is in: row * QUARTERS + column."""
    x, y = project(lat, lng)
    fx, fy = (x - X0) / SQUARE * K, (y - Y0) / SQUARE * K
    col = min(int((fx - math.floor(fx)) * QUARTERS), QUARTERS - 1)
    row = min(int((fy - math.floor(fy)) * QUARTERS), QUARTERS - 1)
    return row * QUARTERS + col


def digits_at(lat, lng):
    """The optional number for a point, 0 to 99: the quarter, then the check."""
    v, q = value_at(lat, lng), quarter_at(lat, lng)
    return q * DIGIT_CHECK + _digit_check(v, q)


def centre_of_quarter(v, q):
    rank, rest = divmod(v, K * K)
    row, col = divmod(rest, K)
    qrow, qcol = divmod(q, QUARTERS)
    j, i = divmod(SQUARES[rank], GRID_W)
    sub = CELL / QUARTERS
    return unproject(X0 + i * SQUARE + col * CELL + (qcol + 0.5) * sub,
                     Y0 + j * SQUARE + row * CELL + (qrow + 0.5) * sub)


def decode_with(spoken, words, digits=None):
    """The centre of what three words, and optionally the number, name: the
    11 m cell without it, its 5.7 m quarter with it."""
    v = decode_value(spoken, words)
    if digits is None:
        return centre_of(v)
    if not 0 <= digits <= 99:
        raise ValueError('the number is 00 to 99')
    q, chk = divmod(digits, DIGIT_CHECK)
    if _digit_check(v, q) != chk:
        raise ValueError('the number does not fit the words - a word or the number is wrong')
    return centre_of_quarter(v, q)


def format_address(spoken, digits=None):
    return SEP.join(spoken) + ('' if digits is None else f' {digits:02d}')


UNITS = {'zero': 0, 'oh': 0, 'nought': 0, 'one': 1, 'two': 2, 'three': 3,
         'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
TEENS = {'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
         'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
         'nineteen': 19}
TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
        'seventy': 70, 'eighty': 80, 'ninety': 90}
NUMBER_WORDS = set(UNITS) | set(TEENS) | set(TENS)


def _number(tokens):
    """Digits or English for 0 to 99: '42', '4 2', 'forty two', 'four two',
    'oh seven'. None of these words is on the word list, so they cannot be
    mistaken for the address."""
    if all(t.isdigit() for t in tokens):
        s = ''.join(tokens)
        if not 1 <= len(s) <= 2:
            raise ValueError('the number is two digits')
        return int(s)
    if len(tokens) == 1:
        t = tokens[0]
        for table in (UNITS, TEENS, TENS):
            if t in table:
                return table[t]
    if len(tokens) == 2:
        a, b = tokens
        if a in TENS and b in UNITS and UNITS[b]:
            return TENS[a] + UNITS[b]
        if a in UNITS and b in UNITS:
            return UNITS[a] * 10 + UNITS[b]
    raise ValueError(f'not a number from 00 to 99: {" ".join(tokens)}')


def parse_address(text):
    """Words only: 'a.b.c', 'a b c' or 'a, b, c'."""
    words, _ = parse_full(text)
    return words


def parse_full(text):
    """(words, number or None). The number, if there is one, comes last."""
    tokens = [t for t in re.split(r'[\s.,;:/-]+', text.strip().lower()) if t]
    if not tokens:
        raise ValueError('empty address')
    at = len(tokens)
    while at > 0 and (tokens[at - 1].isdigit() or tokens[at - 1] in NUMBER_WORDS):
        at -= 1
    words, num = tokens[:at], tokens[at:]
    if not words:
        raise ValueError('no words before the number')
    return words, (_number(num) if num else None)
