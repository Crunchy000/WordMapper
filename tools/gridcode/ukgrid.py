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

THE SCRAMBLE IS THE SAFETY. There is no check digit -- every address the space
can spare goes on precision -- so a misheard word is refused only when it
lands on a value no cell uses. The rest decode, and the scramble sends them
somewhere unrelated in the UK rather than next door. It is the same six-round
Feistel network as the global grid: 1,296**3 is exactly 46,656**2.
"""
import hashlib, math, os

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


def format_address(spoken):
    return SEP.join(spoken)


def parse_address(text):
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts
