#!/usr/bin/env python3
"""Truncatable word addresses over a registry of regions, using BIP-39 words.

    npm install --prefix tools/gridcode

An address is a region code and up to four words:

    GB.plug.curtain                   486 m    a street
    GB.plug.curtain.elder              11 m    a building
    GB.plug.curtain.elder.<4th>       2.4 m    a doorstep, and verified

THE REGION IS CARRIED LIKE A DIALLING CODE. It costs nothing from the four
words, because it travels out of band and is dropped whenever both ends
already know it -- the way nobody says +44 to a neighbour. Every region code
is a published identifier, ISO 3166-1 for a country and ISO 3166-2 for a
subdivision, because a prefix is only worth having if the caller already knows
it: "which country" and "which state" are known, "which numbered box" is not.

WHAT THE PREFIX BUYS. Resolution depends on the area addressed, so scoping to
a region rather than the globe is what keeps four words at metres instead of
tens of metres -- 61 m worldwide, 2.4 m in the UK. It does not buy resolution
over simply saying more words: five words worldwide would reach 1.35 m. It
buys three other things. Four words stays the spoken length everywhere. A
mistaken word lands somewhere in the same region rather than another
continent. And the region is checked by a channel the words do not travel on,
because a dispatcher already knows roughly where the caller is.

REGIONS OVERLAP, DELIBERATELY. US-CA sits inside US; a point in California has
a valid address under either. Overlap is what lets a caller say as much as
they actually know -- the country alone, or the state for a finer cell -- and
it is why border towns need no special case. The registry is built by
tools/regions/build_regions.py; see docs/regions.md.

THE FOURTH WORD does two jobs. Three words alone reach a wide cell, but a
whole fourth word of position would be finer than anyone needs, so its 11 bits
are split: 4 refine the position and 7 carry a checksum, over the region code
as well as the words. Saying the wrong region therefore fails the same check
as saying the wrong word, 99.2% of the time. Four words is terminal: a fifth
would have to reinterpret the check bits.

HOW THE PREFIX PROPERTY IS KEPT. The x and y coordinates are interleaved ONCE
at full precision and the resulting bit string is truncated. Deriving the
interleave order per length instead does not work: 11 bits per word is odd, so
33 bits splits the axes 17/16 while 22 and 44 split evenly, and the three
orders are unrelated sequences rather than prefixes of one another.

COVERAGE. A coordinate outside a region's box has no address in that region,
and encode refuses it rather than inventing one -- decode maps onto the box
and nowhere else, so an outside point would alias onto an address belonging to
a real place inside it, and pass its own checksum. Nowhere is unaddressable:
the XZ region is the whole earth, at 61 m.
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
SEP = '.'
EPS = 1e-9                  # degrees of slack on a box edge, for float error

_HERE = os.path.dirname(os.path.abspath(__file__))
_K = math.cos(math.radians(STD_PARALLEL))


class OutsideBox(ValueError):
    """Raised for a coordinate the named region does not cover."""


class UnknownRegion(ValueError):
    """Raised for a region code that is not in the registry."""


def load_wordlist():
    out = subprocess.check_output(
        ['node', '-e', "console.log(JSON.stringify(require('bip39').wordlists.english))"],
        cwd=_HERE)
    words = json.loads(out)
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


def load_regions():
    with open(os.path.join(_HERE, 'regions.json')) as fh:
        return {r['code']: r for r in json.load(fh)}


REGIONS = load_regions()


def project(lat, lng):
    """Lambert cylindrical equal-area: area-true, which keeps cell areas equal
    across a box. Shape stretches with latitude."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K


def unproject(x, y):
    return (math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))),
            math.degrees(x / (R * _K)))


def region(code):
    try:
        return REGIONS[code]
    except KeyError:
        raise UnknownRegion(f'no region {code!r} in the registry') from None


def _frame(code):
    """Projected origin and extent of a region's box, cached on the entry."""
    r = region(code)
    if '_frame' not in r:
        latMin, latMax, lngMin, lngMax = r['box']
        x0, y0 = project(latMin, lngMin)
        x1, y1 = project(latMax, lngMax)
        r['_frame'] = (x0, y0, x1, y1)
    return r['_frame']


def normalise_lng(lng, code):
    """Bring a longitude into the region's frame.

    A region straddling the antimeridian has a box running past 180 -- Fiji is
    176.9 to 182.0 -- so a point there arrives as -179 and must be read as 181.
    """
    lngMin, lngMax = region(code)['box'][2:]
    if lngMin - EPS <= lng <= lngMax + EPS:
        # Already in frame. Short-circuiting matters: a value a hair BELOW
        # lngMin would otherwise wrap to nearly lngMin + 360, throwing a point
        # on the western edge clean out of its own box.
        return lng
    return lngMin + (lng - lngMin) % 360.0


def covers(lat, lng, code):
    """True if the region's box covers this point. Edges are inclusive."""
    latMin, latMax, lngMin, lngMax = region(code)['box']
    # A hair of tolerance, because normalising a longitude across the seam is
    # not exact in binary and a point on the boundary must not fall out of its
    # own box. EPS degrees is well under a millimetre.
    return (latMin - EPS <= lat <= latMax + EPS
            and lngMin - EPS <= normalise_lng(lng, code) <= lngMax + EPS)


def box_area(code):
    x0, y0, x1, y1 = _frame(code)
    return abs((x1 - x0) * (y1 - y0))


def regions_covering(lat, lng):
    """Every region whose box covers the point, tightest first.

    Tightest first because a smaller box is a finer cell, so the head of this
    list is the best address available and the tail is the most widely known.
    """
    found = [c for c in REGIONS if covers(lat, lng, c)]
    return sorted(found, key=lambda c: (box_area(c), c))


def best_region(lat, lng):
    found = regions_covering(lat, lng)
    if not found:
        raise OutsideBox(f'{lat:.5f}, {lng:.5f} is in no region')  # XZ makes this
        # unreachable in practice, but the registry is data and may be edited
    return found[0]


def _full_index(lat, lng, code):
    """x and y interleaved at full precision, coarse bits first."""
    if not covers(lat, lng, code):
        latMin, latMax, lngMin, lngMax = region(code)['box']
        raise OutsideBox(f'{lat:.5f}, {lng:.5f} is outside {code} '
                         f'({latMin}..{latMax}, {lngMin}..{lngMax})')
    x0, y0, x1, y1 = _frame(code)
    x, y = project(lat, normalise_lng(lng, code))
    # Both ends are clamped. The top saturates a point on the boundary into the
    # last cell, which is what an inclusive edge means. The bottom is only
    # reachable by floating-point slop at the boundary, since covers() has
    # refused anything genuinely outside -- but an unclamped negative index
    # would sign-extend under >> and mint a plausible address for the wrong
    # place, so it is clamped rather than trusted.
    def cell(v, lo, hi):
        return min(max(int((v - lo) / (hi - lo) * 2 ** PRECISION), 0),
                   2 ** PRECISION - 1)
    xi, yi = cell(x, x0, x1), cell(y, y0, y1)
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


def cell_size(n_words, code):
    """(width, height) in metres of the cell an n-word address names."""
    x0, y0, x1, y1 = _frame(code)
    xb, yb = _axis_bits(n_words)
    return abs(x1 - x0) / 2 ** xb, abs(y1 - y0) / 2 ** yb


def _checksum(position, code):
    """Over the region as well as the position, so naming the wrong region
    fails the same check as saying the wrong word."""
    payload = code.encode() + b'\0' + position.to_bytes(8, 'big')
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:2], 'big') >> (16 - CHECK_BITS)


def encode(lat, lng, words, n_words=3, code=None):
    """Words for a point. With no region, the tightest one covering it."""
    if not 1 <= n_words <= MAX_WORDS:
        raise ValueError(f'1..{MAX_WORDS} words')
    if code is None:
        code = best_region(lat, lng)
    bits = _position_bits(n_words)
    position = _full_index(lat, lng, code) >> (2 * PRECISION - bits)
    if n_words < MAX_WORDS:
        value = position
    else:
        # last word = REFINE_BITS of position, then the checksum over all of it
        value = (position << CHECK_BITS) | _checksum(position, code)
    return [words[(value >> (BITS_PER_WORD * (n_words - 1 - i))) & 0x7ff]
            for i in range(n_words)]


def decode(spoken, words, code):
    """Resolve an address within a region.

    A four-word address is checked; raises ValueError if a word or the region
    is wrong.
    """
    region(code)                                    # reject an unknown region first
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
        if (value & (2 ** CHECK_BITS - 1)) != _checksum(prefix, code):
            raise ValueError('checksum failed - a word or the region is wrong')
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
    x0, y0, x1, y1 = _frame(code)
    x = x0 + (xi + 0.5) / 2 ** xb * (x1 - x0)
    y = y0 + (yi + 0.5) / 2 ** yb * (y1 - y0)
    lat, lng = unproject(x, y)
    return lat, (lng + 180.0) % 360.0 - 180.0       # back into -180..180


def format_address(code, spoken):
    return SEP.join([code] + list(spoken))


def parse_address(text):
    """Split 'GB.plug.curtain' into ('GB', ['plug', 'curtain']).

    The region is the first token. It never collides with a word: BIP-39 has no
    word shorter than three letters and none containing a digit or a hyphen.
    """
    parts = [p for p in text.replace(',', SEP).replace(' ', SEP).split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts[0].upper(), [p.lower() for p in parts[1:]]
