#!/usr/bin/env python3
"""Four-word PHRASES for anywhere in the UK: adjective noun verb noun.

    cheeky film follow banana

A PHRASE NAMES ONE SQUARE OF ABOUT 7.5 METRES anywhere in the UK, the Isle of
Man and the Channel Islands, with a strip of coastal sea -- the same coverage
and the same 2 km mask as ukgrid.py -- and a misheard word is refused at least
95 % of the time.

ONE LIST PER SLOT. Each slot takes one part of speech, from its own list built
by tools/wordlist/phrases.py: about 370 adjectives, 800 nouns and 420 verbs.
A word only has to be distinct from the other words of ITS part of speech, so
words the single 1,296 list turned away for sounding like a word of another
kind are back. A phrase is A * N * V * N, about 98 billion of them.

THE LAYOUT, the same as the three-word UK grid with a check folded in:

    rank    = the 2 km square's position among the squares in the mask
    cell    = (rank * K + row) * K + column
    value   = cell * CHECK + check       check = sha256(cell) mod CHECK
    number  = scramble(value)            a permutation of all A*N*V*N phrases
    phrase  = number in mixed radix: adjective, noun, verb, noun

K is the most cells per square side that still leaves a check of 20 -- the
95 % -- and CHECK is whatever whole factor that leaves, which comes out at 20.

A MISHEARD WORD is caught three ways. If it comes out as another part of speech
the phrase stops being adjective noun verb noun and is refused before anything
else runs. If it is a word of the right kind, it fails the check 19 times in
20, or lands on a value no cell uses. The rest decode, and the scramble sends
them somewhere unrelated in the UK.

THE SCRAMBLE is a Feistel network on unequal halves: the left is the adjective
and first noun (A * N values), the right the verb and second noun (V * N).
Each round maps Z_a x Z_b to Z_b x Z_a -- (L, R) -> (R, (L + F(R)) mod a) --
which is a bijection whatever a and b are, and an even number of rounds lands
back on Z_a x Z_b. So every phrase is used and none is left over.
"""
import hashlib, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukgrid as g          # the projection and the 2 km mask are shared

_LISTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wordlist')
LIST_FILES = {k: os.path.join(_LISTS, f'phrase-{k}.txt') for k in ('adjective', 'noun', 'verb')}
LIST_SHA256 = {
    'adjective': 'b2fd8a4c54cc415d1f300657f9db645da26a2477b36d3f3da3d2fdd3a0fc2def',
    'noun': '78ae81be267a1b108666ed37f03d52330b73a7788b31966bd430b4764fce80b4',
    'verb': '4192c8cdcfa7b75c2a55ae4d1cf33dbb46457b42807854c66a1098e3d2798822',
}
PATTERN = ('adjective', 'noun', 'verb', 'noun')
ROUNDS = 6
MIN_CHECK = 20              # a misheard word of the right kind fails 19 in 20
SEP = '.'


def load_lists():
    out = {}
    for kind, path in LIST_FILES.items():
        with open(path, 'rb') as fh:
            raw = fh.read()
        got = hashlib.sha256(raw).hexdigest()
        if got != LIST_SHA256[kind]:
            raise ValueError(f'{path} is not the expected {kind} list (sha256 {got})')
        out[kind] = raw.decode().split()
    return out


LISTS = load_lists()
SIZES = [len(LISTS[k]) for k in PATTERN]
SPACE = math.prod(SIZES)                        # every phrase
LEFT = SIZES[0] * SIZES[1]                      # adjective, first noun
RIGHT = SIZES[2] * SIZES[3]                     # verb, second noun
# The most cells per square side that leaves MIN_CHECK, and the check that leaves.
K = math.isqrt(SPACE // (len(g.SQUARES) * MIN_CHECK))
CELL = g.SQUARE / K
CELLS = len(g.SQUARES) * K * K
CHECK = SPACE // CELLS
USED = CELLS * CHECK                            # values that name a cell
_INDEX = {k: {w: i for i, w in enumerate(LISTS[k])} for k in LISTS}


def _sha_int(data, nbytes):
    return int.from_bytes(hashlib.sha256(data).digest()[:nbytes], 'big')


def _check(cell):
    return _sha_int(b'ukp-check' + cell.to_bytes(8, 'big'), 8) % CHECK


def _round(i, half, modulus):
    return _sha_int(b'ukp' + bytes([i]) + half.to_bytes(8, 'big'), 8) % modulus


def scramble(v):
    """A permutation of [0, SPACE): (L, R) in Z_LEFT x Z_RIGHT, each round
    (L, R) -> (R, (L + F(R)) mod |L|), so the halves swap sizes every round."""
    a, b = LEFT, RIGHT
    left, right = divmod(v, b)
    for i in range(ROUNDS):
        left, right = right, (left + _round(i, right, a)) % a
        a, b = b, a
    return left * b + right


def unscramble(n):
    # After an even number of rounds the sizes are back where they started.
    a, b = LEFT, RIGHT
    left, right = divmod(n, b)
    for i in reversed(range(ROUNDS)):
        a, b = b, a                     # the sizes this round produced
        # Now (a, b) are the sizes round i started from: it took (L, R) to
        # (R, (L + F(R)) mod a), so L = (right - F(left)) mod a and R = left.
        left, right = (right - _round(i, left, a)) % a, left
    return left * RIGHT + right


def number_to_phrase(n):
    out = []
    for kind, size in zip(reversed(PATTERN), reversed(SIZES)):
        n, d = divmod(n, size)
        out.append(LISTS[kind][d])
    return out[::-1]


def encode(lat, lng):
    """The phrase for a point in the UK. Raises ukgrid.OutsideUK elsewhere."""
    cell = _cell_at(lat, lng)
    return number_to_phrase(scramble(cell * CHECK + _check(cell)))


def _cell_at(lat, lng):
    x, y = g.project(lat, lng)
    fx, fy = (x - g.X0) / g.SQUARE, (y - g.Y0) / g.SQUARE
    i, j = math.floor(fx), math.floor(fy)
    rank = g.RANK.get(j * g.GRID_W + i) if 0 <= i < g.GRID_W and 0 <= j < g.GRID_H else None
    if rank is None:
        raise g.OutsideUK(f'{lat:.5f}, {lng:.5f} is outside the UK grid')
    col = min(int((fx - i) * K), K - 1)
    row = min(int((fy - j) * K), K - 1)
    return (rank * K + row) * K + col


def cell_at(lat, lng):
    return _cell_at(lat, lng)


def decode_cell(spoken):
    """The cell a phrase names. Raises ValueError for a phrase that is not one."""
    if len(spoken) != len(PATTERN):
        raise ValueError(f'a phrase is {len(PATTERN)} words: ' + ' '.join(PATTERN))
    n = 0
    for word, kind, size in zip(spoken, PATTERN, SIZES):
        i = _INDEX[kind].get(word)
        if i is None:
            others = [k for k in _INDEX if word in _INDEX[k]]
            raise ValueError(f'"{word}" is not a word for the {kind} slot'
                             + (f' (it is a {others[0]})' if others else ''))
        n = n * size + i
    v = unscramble(n)
    if v >= USED:
        raise ValueError('no such phrase - a word is wrong')
    cell, chk = divmod(v, CHECK)
    if _check(cell) != chk:
        raise ValueError('check failed - a word is wrong')
    return cell


def centre_of(cell):
    rank, rest = divmod(cell, K * K)
    row, col = divmod(rest, K)
    j, i = divmod(g.SQUARES[rank], g.GRID_W)
    return g.unproject(g.X0 + i * g.SQUARE + (col + 0.5) * CELL,
                       g.Y0 + j * g.SQUARE + (row + 0.5) * CELL)


def decode(spoken):
    return centre_of(decode_cell(spoken))


def format_phrase(spoken):
    return SEP.join(spoken)


def parse_phrase(text):
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty phrase')
    return parts
