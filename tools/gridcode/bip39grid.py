#!/usr/bin/env python3
"""Truncatable word addresses over a fixed box, using the BIP-39 word list.

    npm install --prefix tools/gridcode

An address is a prefix of a longer address. Say as many words as you need and
stop; each one narrows the area, and the words already said never change:

    plug.curtain                      486 m    a street
    plug.curtain.elder                 11 m    a building
    plug.curtain.elder.<4th>          2.7 m    a doorstep, and verified

The fourth word does two jobs at once. Three words alone reach 10.75 m, which
is wide, but a whole fourth word of position would reach 24 cm, which is finer
than anyone needs. So its 11 bits are split: 4 refine the position and 7 carry
a checksum. That lands at 2.69 m -- better than what3words' 3 m -- while
catching a wrong word 99.2% of the time, which what3words does not do at all.

The root is a fixed bounding box rather than a repeating tile, so an address
is unambiguous at every length -- there are no repeats to disambiguate and no
position hint is needed. An approximate location is then a sanity check rather
than a requirement, which is the useful shape for emergency calls: a partial
address is still a real answer.

HOW THE PREFIX PROPERTY IS KEPT. The x and y coordinates are interleaved ONCE
at full precision and the resulting bit string is truncated. Deriving the
interleave order per length instead does not work: 11 bits per word is odd, so
33 bits splits the axes 17/16 while 22 and 44 split evenly, and the three
orders are unrelated sequences rather than prefixes of one another.

CHECKSUMS. A checksum cannot live at every length: its bits would sit exactly
where the next word's position bits must go. Rather than pay for one at every
length, the four-word form carries it inside its own last word, which is why
four words is terminal -- a fifth word would have to reinterpret those bits.
One to three words are position only and unverified; four words is refined and
verified. Nothing is ambiguous, because the fourth word is always the last.
"""
import hashlib, json, math, os, subprocess, sys

R = 6371008.8               # mean earth radius, metres
STD_PARALLEL = 30.0         # Lambert equal-area standard parallel
BITS_PER_WORD = 11          # log2(2048), exactly
MAX_WORDS = 4               # terminal: the last word carries the checksum
REFINE_BITS = 4             # of the last word's 11 bits, how many refine position
CHECK_BITS = BITS_PER_WORD - REFINE_BITS
POSITION_BITS = BITS_PER_WORD * (MAX_WORDS - 1) + REFINE_BITS
PRECISION = (POSITION_BITS + 1) // 2               # bits per axis at full depth

# UK and Ireland. Any box works; it fixes the resolution at every length.
BOX = {'latMin': 49.85, 'latMax': 60.90, 'lngMin': -11.00, 'lngMax': 1.80}

_HERE = os.path.dirname(os.path.abspath(__file__))
_K = math.cos(math.radians(STD_PARALLEL))


def load_wordlist():
    out = subprocess.check_output(
        ['node', '-e', "console.log(JSON.stringify(require('bip39').wordlists.english))"],
        cwd=_HERE)
    words = json.loads(out)
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


def project(lat, lng):
    """Lambert cylindrical equal-area: area-true, which keeps cell areas equal
    across the box. Shape stretches with latitude."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K


def unproject(x, y):
    return (math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))),
            math.degrees(x / (R * _K)))


_X0, _Y0 = project(BOX['latMin'], BOX['lngMin'])
_X1, _Y1 = project(BOX['latMax'], BOX['lngMax'])


def _full_index(lat, lng):
    """x and y interleaved at full precision, coarse bits first."""
    x, y = project(lat, lng)
    xi = min(int((x - _X0) / (_X1 - _X0) * 2 ** PRECISION), 2 ** PRECISION - 1)
    yi = min(int((y - _Y0) / (_Y1 - _Y0) * 2 ** PRECISION), 2 ** PRECISION - 1)
    v = 0
    for i in range(PRECISION - 1, -1, -1):
        v = (v << 1) | ((xi >> i) & 1)
        v = (v << 1) | ((yi >> i) & 1)
    return v


def _position_bits(n_words):
    """Position bits an n-word address carries. The last word contributes only
    REFINE_BITS, the rest all 11."""
    if n_words < MAX_WORDS:
        return BITS_PER_WORD * n_words
    return POSITION_BITS


def _axis_bits(n_words):
    bits = _position_bits(n_words)
    return (bits + 1) // 2, bits // 2      # x gets the odd bit


def cell_size(n_words):
    """(width, height) in metres of the cell an n-word address names."""
    xb, yb = _axis_bits(n_words)
    return (_X1 - _X0) / 2 ** xb, (_Y1 - _Y0) / 2 ** yb


def encode(lat, lng, words, n_words=3):
    if not 1 <= n_words <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    bits = _position_bits(n_words)
    position = _full_index(lat, lng) >> (2 * PRECISION - bits)
    if n_words < MAX_WORDS:
        value = position
    else:
        # last word = REFINE_BITS of position, then the checksum over all of it
        value = (position << CHECK_BITS) | _checksum(position)
    return [words[(value >> (BITS_PER_WORD * (n_words - 1 - i))) & 0x7ff]
            for i in range(n_words)]


def _checksum(position):
    payload = position.to_bytes(8, 'big')
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:2], 'big') >> (16 - CHECK_BITS)


def decode(spoken, words):
    """Resolve an address of any length. No position hint is needed.

    A four-word address is checked; raises ValueError if a word is wrong.
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
    # De-interleave the truncated sequence back into partial x and y.
    bits = _position_bits(len(spoken))
    xb, yb = _axis_bits(len(spoken))
    xi = yi = 0
    for pos in range(bits):
        bit = (prefix >> (bits - 1 - pos)) & 1
        if pos % 2 == 0:
            xi = (xi << 1) | bit
        else:
            yi = (yi << 1) | bit
    x = _X0 + (xi + 0.5) / 2 ** xb * (_X1 - _X0)
    y = _Y0 + (yi + 0.5) / 2 ** yb * (_Y1 - _Y0)
    return unproject(x, y)
