#!/usr/bin/env python3
"""A global word grid: five BIP-39 words for any point on earth, to 1.35 m.

    npm install --prefix tools/gridcode

    leaf.step.cruel.tomato.tone          Big Ben, 1.35 m, checksummed

One grid over the whole world. No prefix, no registry, no agreement about
borders, and nothing the caller has to know about where they are.

An address shortens in TWO directions, and they do different jobs.

DROP TRAILING WORDS for a coarser address that still needs no context. Each
word said narrows the area, and the words already said never change:

    leaf.step.cruel                      244 m
    leaf.step.cruel.tomato               5.4 m
    leaf.step.cruel.tomato.tone          1.35 m, and verified

DROP LEADING WORDS to keep full precision using fewer words, when whoever is
listening already knows roughly where you are. The leading words are the
coarse ones, so context can supply them -- exactly the way nobody dials +44 or
an area code to a neighbour:

    words said   ambiguity left            usable if the listener knows
    5            none                      nothing at all
    4            542 x 460 km              which country, give or take 230 km
    3            16.9 x 7.2 km             which town, give or take 3.6 km
    2            264 x 225 m               which street, give or take 112 m

So a local exchange settles on however few words its own accuracy allows, and
the same words remain a global address the moment the context is written down.

THE CHECKSUM VERIFIES THE RECONSTRUCTION. When leading words are filled in
from a reference point, the 7 check bits cover the whole position, so guessing
the wrong tile fails the check 99.2% of the time. Shortening is therefore not
a leap of faith: a tail that resolves is almost certainly the place meant.

THE LAST WORD DOES TWO JOBS. A whole fifth word of position would reach 8 cm,
finer than anyone needs, so its 11 bits are split: 4 refine the position and 7
carry the checksum. Five words is terminal -- a sixth would have to
reinterpret the check bits.

HOW THE PREFIX PROPERTY IS KEPT. The x and y coordinates are interleaved ONCE
at full precision and the resulting bit string is truncated. Deriving the
interleave order per length instead does not work: 11 bits per word is odd, so
33 bits splits the axes 17/16 while 22 and 44 split evenly, and the three
orders are unrelated sequences rather than prefixes of one another.
"""
import hashlib, json, math, os, subprocess, sys

R = 6371008.8               # mean earth radius, metres
STD_PARALLEL = 30.0         # Lambert equal-area standard parallel
BITS_PER_WORD = 11          # log2(2048), exactly
MAX_WORDS = 5               # terminal: the last word carries the checksum
REFINE_BITS = 4             # of the last word's 11 bits, how many refine position
CHECK_BITS = BITS_PER_WORD - REFINE_BITS
POSITION_BITS = BITS_PER_WORD * (MAX_WORDS - 1) + REFINE_BITS      # 48
SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail

_HERE = os.path.dirname(os.path.abspath(__file__))
_K = math.cos(math.radians(STD_PARALLEL))
_X0, _Y0 = -math.pi * R * _K, -R / _K
_XR, _YR = 2 * math.pi * R * _K, 2 * R / _K


def _bit_order():
    """Which axis each position bit refines, coarse bit first.

    Not a plain alternation. The projected world is 34,667 x 14,713 km, an
    aspect of 2.36, and alternating bits carries that aspect straight down into
    every cell: 2.07 x 0.88 m at full depth. Giving each bit to whichever axis
    is currently wider keeps cells near square at EVERY length -- 1.70 at worst
    against 2.36, and 1.18 at half the lengths -- for the same cell area, since
    the projection is equal-area and only the shape changes.
    """
    order, w, h = [], _XR, _YR
    for _ in range(POSITION_BITS):
        if w >= h:
            order.append(0); w /= 2
        else:
            order.append(1); h /= 2
    return order


_ORDER = _bit_order()
_XB = _ORDER.count(0)                 # 25 bits of x
_YB = POSITION_BITS - _XB             # 23 bits of y


def load_wordlist():
    out = subprocess.check_output(
        ['node', '-e', "console.log(JSON.stringify(require('bip39').wordlists.english))"],
        cwd=_HERE)
    words = json.loads(out)
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


def project(lat, lng):
    """Lambert cylindrical equal-area: area-true, which keeps cell areas equal
    everywhere. Shape stretches with latitude, so a cell near the poles is the
    same area but much taller on the ground."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K


def unproject(x, y):
    return (math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))),
            math.degrees(x / (R * _K)))


def _indices(lat, lng):
    """Grid indices of a point: _XB bits of x, _YB bits of y."""
    lng = (lng + 180.0) % 360.0 - 180.0
    x, y = project(lat, lng)
    # Both ends are clamped. The top saturates a point on the boundary -- the
    # poles, the antimeridian -- into the last cell. The bottom is only
    # reachable by floating-point slop, but an unclamped negative index would
    # sign-extend under >> and mint a plausible address for the wrong place.
    def cell(v, lo, span, bits):
        return min(max(int((v - lo) / span * 2 ** bits), 0), 2 ** bits - 1)
    return cell(x, _X0, _XR, _XB), cell(y, _Y0, _YR, _YB)


def _interleave(xi, yi):
    """x and y interleaved in _ORDER, coarse bits first."""
    v, xa, ya = 0, _XB, _YB
    for axis in _ORDER:
        if axis == 0:
            xa -= 1; v = (v << 1) | ((xi >> xa) & 1)
        else:
            ya -= 1; v = (v << 1) | ((yi >> ya) & 1)
    return v


def _deinterleave(v, bits=POSITION_BITS):
    """Inverse of _interleave over the top `bits` of the sequence."""
    xi = yi = 0
    for i, axis in enumerate(_ORDER[:bits]):
        bit = (v >> (bits - 1 - i)) & 1
        if axis == 0:
            xi = (xi << 1) | bit
        else:
            yi = (yi << 1) | bit
    return xi, yi


def _position_bits(n_words):
    """Position bits an n-word address carries. The last word contributes only
    REFINE_BITS, the rest all 11."""
    if n_words < MAX_WORDS:
        return BITS_PER_WORD * n_words
    return POSITION_BITS


def _axis_bits(n_words):
    bits = _position_bits(n_words)
    xb = _ORDER[:bits].count(0)
    return xb, bits - xb


def cell_size(n_words):
    """(width, height) in metres of the cell an n-word address names."""
    xb, yb = _axis_bits(n_words)
    return _XR / 2 ** xb, _YR / 2 ** yb


def tile_size(n_said):
    """(width, height) in metres of the ambiguity left when an address is given
    as its last n_said words, the leading ones dropped."""
    xb, yb = _axis_bits(MAX_WORDS - n_said)
    return _XR / 2 ** xb, _YR / 2 ** yb


def _checksum(position):
    digest = hashlib.sha256(position.to_bytes(8, 'big')).digest()
    return int.from_bytes(digest[:2], 'big') >> (16 - CHECK_BITS)


def _value(lat, lng):
    """The full 55-bit address value: 48 position bits then 7 check bits."""
    position = _interleave(*_indices(lat, lng))
    return (position << CHECK_BITS) | _checksum(position)


def encode(lat, lng, words, n_words=MAX_WORDS):
    """The first n_words of the address. Coarser as n_words falls; needs no
    context at any length."""
    if not 1 <= n_words <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    value = _value(lat, lng)
    if n_words < MAX_WORDS:
        # Truncate the position; the check bits are not part of a short form.
        value >>= BITS_PER_WORD * (MAX_WORDS - n_words)
    return [words[(value >> (BITS_PER_WORD * (n_words - 1 - i))) & 0x7ff]
            for i in range(n_words)]


def _from_position(position):
    xi, yi = _deinterleave(position)
    return unproject(_X0 + (xi + 0.5) / 2 ** _XB * _XR,
                     _Y0 + (yi + 0.5) / 2 ** _YB * _YR)


def decode(spoken, words):
    """Resolve an absolute address: the first n words, coarser as n falls.

    A full-length address is checked; raises ValueError if a word is wrong.
    """
    index = {w: i for i, w in enumerate(words)}
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    if not 1 <= len(spoken) <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    value = 0
    for w in spoken:
        value = (value << BITS_PER_WORD) | index[w]
    if len(spoken) < MAX_WORDS:
        prefix = value
    else:
        prefix = value >> CHECK_BITS
        if (value & (2 ** CHECK_BITS - 1)) != _checksum(prefix):
            raise ValueError('checksum failed - a word is wrong')
    bits = _position_bits(len(spoken))
    xb, yb = _axis_bits(len(spoken))
    xi, yi = _deinterleave(prefix, bits)
    x = _X0 + (xi + 0.5) / 2 ** xb * _XR
    y = _Y0 + (yi + 0.5) / 2 ** yb * _YR
    return unproject(x, y)


def _known_low(n_said):
    """How many low bits of each axis index a tail of n_said words pins down.

    A tail drops the top 11*(MAX_WORDS - n_said) bits of the address value,
    which are position bits, and those interleave x first. So x loses the
    ceiling half of them and y the floor half.
    """
    dropped = BITS_PER_WORD * (MAX_WORDS - n_said)
    dx = _ORDER[:dropped].count(0)
    return _XB - dx, _YB - (dropped - dx)


def resolve_tail(spoken, words, near_lat, near_lng):
    """Resolve an address given only its last words, plus a reference point.

    The dropped words are the coarse ones, so the reference supplies them: for
    each axis, take the candidate matching the known low bits that is nearest
    the reference. The checksum then covers the whole reconstruction, so a
    reference too far off to pick the right tile is caught 99.2% of the time
    rather than resolving quietly to the wrong place.
    """
    index = {w: i for i, w in enumerate(words)}
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    n = len(spoken)
    if not 1 <= n <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    value_low = 0
    for w in spoken:
        value_low = (value_low << BITS_PER_WORD) | index[w]
    check = value_low & (2 ** CHECK_BITS - 1)
    known_bits = BITS_PER_WORD * n - CHECK_BITS          # of the position
    pos_low = value_low >> CHECK_BITS
    cx, cy = _known_low(n)
    # De-interleave the known low position bits into low bits of each axis.
    known_x = known_y = 0
    for i in range(known_bits):
        # Sequence position of this bit, counting from the coarse end.
        seq = POSITION_BITS - known_bits + i
        bit = (pos_low >> (known_bits - 1 - i)) & 1
        if _ORDER[seq] == 0:
            known_x = (known_x << 1) | bit
        else:
            known_y = (known_y << 1) | bit
    xi_ref, yi_ref = _indices(near_lat, near_lng)

    def nearest_x(known, count, ref):
        """The candidate nearest the reference, going the short way round.

        x wraps: the projection is a cylinder, so a reference a few kilometres
        west of the antimeridian is a whole world-width away in index terms
        while being next door on the ground. Linear arithmetic here picks a
        tile on the far side of the planet.
        """
        period, total = 2 ** count, 2 ** _XB
        k = round(((ref - known) % total) / period) % (total // period)
        return (known + k * period) % total

    def nearest_y(known, count, ref):
        """y does not wrap -- latitude ends at the poles -- so the candidate is
        clamped, but to the last point ON the lattice: clamping to the last
        index would leave a value the known bits do not match."""
        period = 2 ** count
        v = known + round((ref - known) / period) * period
        return min(max(v, known), known + (2 ** _YB - 1 - known) // period * period)

    xi = nearest_x(known_x, cx, xi_ref)
    yi = nearest_y(known_y, cy, yi_ref)
    position = _interleave(xi, yi)
    if _checksum(position) != check:
        raise ValueError('checksum failed - a word is wrong, or the reference '
                         'point is too far away to fill in the missing words')
    return _from_position(position)


def words_needed(lat, lng, near_lat, near_lng, words):
    """The fewest trailing words that resolve back to this point from that
    reference, or MAX_WORDS if even the full address is needed."""
    full = encode(lat, lng, words)
    for n in range(1, MAX_WORDS + 1):
        try:
            got = resolve_tail(full[-n:], words, near_lat, near_lng)
        except ValueError:
            continue
        if _indices(*got) == _indices(lat, lng):
            return n
    return MAX_WORDS


def format_address(spoken, tail=False):
    """'leaf.step.cruel' absolute, '.cruel.tomato.tone' for a tail.

    The leading separator is the whole notation: it says the coarse words are
    missing and context must supply them, which is the difference between an
    address that is merely vague and one that is precise but local.
    """
    return (TAIL_MARK if tail else '') + SEP.join(spoken)


def parse_address(text):
    """Split into (words, is_tail)."""
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    tail = text.startswith(SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts, tail
