#!/usr/bin/env python3
"""Local word addresses on a global 70 km lattice, using the BIP-39 word list.

    npm install --prefix tools/gridcode

The world is projected to an equal-area plane and tiled into 70 km squares. The
square itself is NOT transmitted: an address names a point within a square, and
the listener supplies the square from knowing roughly where they are. That is
what buys the resolution -- 104,095 squares cover the earth, so not sending one
is 16.7 bits you do not have to say aloud.

    3 BIP-39 words = 33 bits = 8,589,934,592 points in a 70 km square

With no checksum that is a 0.755 m cell. Bits spent on a checksum come out of
resolution:

    check bits   0 -> 0.76 m      4 -> 3.02 m      8 -> 12.08 m

A checksum is not decoration here. 53% of BIP-39 words have another word in the
list one phoneme away (pair/pear, right/write, peace/piece, wear/where are
outright homophones), so 89.6% of three-word addresses contain a word that a
single mishearing turns into a different valid word. BIP-39 is built to be typed
and checksummed, not spoken; without check bits, a mishearing here is silently
a different place.

UNIQUENESS. The address repeats on a 70 km lattice, so a disc of radius 35 km
contains at most one instance. The bound is exact and therefore tight: a point
on the lattice midline has two instances at exactly 35 km. Treat 35 km as the
hard limit and ~30 km as the working one.
"""
import hashlib, json, math, os, subprocess, sys

R = 6371008.8               # mean earth radius, metres
STD_PARALLEL = 30.0         # Lambert equal-area standard parallel
CHUNK = 70_000.0            # metres
WORDS = 3
CHECK_BITS = 0              # 0 -> 0.755 m; 4 -> 3.02 m; 8 -> 12.08 m
BITS_PER_WORD = 11          # log2(2048), exactly

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_wordlist():
    out = subprocess.check_output(
        ['node', '-e', "console.log(JSON.stringify(require('bip39').wordlists.english))"],
        cwd=_HERE)
    words = json.loads(out)
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


# --- equal-area projection -------------------------------------------------
_K = math.cos(math.radians(STD_PARALLEL))

def project(lat, lng):
    """Lambert cylindrical equal-area. Area-true everywhere, which is what the
    lattice needs; shape stretches near the poles."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K

def unproject(x, y):
    return math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))), math.degrees(x / (R * _K))


# --- bit plumbing ----------------------------------------------------------
def _bit_order(xbits, ybits):
    """Which source bit each output bit carries, most significant first."""
    order = []
    for i in range(max(xbits, ybits) - 1, -1, -1):
        if i < xbits:
            order.append(('x', i))
        if i < ybits:
            order.append(('y', i))
    return order

def _interleave(x, y, xbits, ybits):
    """Z-order. Keeps the high bits coarse, so the first word alone still
    narrows the location -- a Hilbert curve would have better locality."""
    v = 0
    for axis, i in _bit_order(xbits, ybits):
        v = (v << 1) | (((x if axis == 'x' else y) >> i) & 1)
    return v

def _deinterleave(v, xbits, ybits):
    order = _bit_order(xbits, ybits)
    n = len(order)
    x = y = 0
    for pos, (axis, i) in enumerate(order):
        bit = (v >> (n - 1 - pos)) & 1
        if axis == 'x':
            x |= bit << i
        else:
            y |= bit << i
    return x, y

def _split_bits(check_bits=CHECK_BITS):
    pos = WORDS * BITS_PER_WORD - check_bits
    return pos, (pos + 1) // 2, pos // 2      # total, x bits, y bits

def _checksum(position, bits):
    if not bits:
        return 0
    digest = hashlib.sha256(position.to_bytes(8, 'big')).digest()
    return int.from_bytes(digest, 'big') >> (256 - bits)


def cell_size(check_bits=CHECK_BITS):
    _, xb, yb = _split_bits(check_bits)
    return CHUNK / 2 ** xb, CHUNK / 2 ** yb


# --- the address -----------------------------------------------------------
def encode(lat, lng, words, check_bits=CHECK_BITS):
    pos_bits, xb, yb = _split_bits(check_bits)
    x, y = project(lat, lng)
    u, v = math.fmod(x, CHUNK), math.fmod(y, CHUNK)
    if u < 0: u += CHUNK
    if v < 0: v += CHUNK
    xi = min(int(u / CHUNK * 2 ** xb), 2 ** xb - 1)
    yi = min(int(v / CHUNK * 2 ** yb), 2 ** yb - 1)
    position = _interleave(xi, yi, xb, yb)
    value = (position << check_bits) | _checksum(position, check_bits)
    return [words[(value >> (BITS_PER_WORD * (WORDS - 1 - i))) & (2 ** BITS_PER_WORD - 1)]
            for i in range(WORDS)]


def decode(spoken, near_lat, near_lng, words, check_bits=CHECK_BITS):
    """Resolve an address using an approximate position (must be within 35 km).

    Returns (lat, lng). Raises ValueError on an unknown word or a failed check.
    """
    index = {w: i for i, w in enumerate(words)}
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    value = 0
    for w in spoken:
        value = (value << BITS_PER_WORD) | index[w]
    position = value >> check_bits
    if check_bits and (value & (2 ** check_bits - 1)) != _checksum(position, check_bits):
        raise ValueError('checksum failed - a word is wrong')

    pos_bits, xb, yb = _split_bits(check_bits)
    xi, yi = _deinterleave(position, xb, yb)
    u = (xi + 0.5) / 2 ** xb * CHUNK
    v = (yi + 0.5) / 2 ** yb * CHUNK
    # Pick the lattice square nearest the caller's approximate position.
    nx, ny = project(near_lat, near_lng)
    x = math.floor((nx - u) / CHUNK + 0.5) * CHUNK + u
    y = math.floor((ny - v) / CHUNK + 0.5) * CHUNK + v
    return unproject(x, y)
