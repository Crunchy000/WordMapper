#!/usr/bin/env python3
"""Word addresses from the BIP-39 list, on one global grid.

    npm install --prefix tools/gridcode

FIVE WORDS name any point on earth to 1.35 m:

    leg.tunnel.slam.subway.gown

There is one grid and one address for a place. No regional boxes, no scope to
choose, nothing to switch. A box has to be a rectangle and most of the world
cannot be boxed without swallowing a neighbour, so the boxes that used to exist
here bought a word at the cost of a hand-drawn edge and a second address for the
same place. What replaced them is below.

FOUR WORDS, WHERE SOMETHING ELSE SUPPLIES THE FIFTH. The leading words are the
coarse ones, so they can go unsaid when whoever is listening can supply them.
Two ways to do that:

  - resolve_tail() takes a nearby POINT and picks the nearest tile that fits.
  - candidates_in_box() takes a REGION and lets the checksum pick, trying every
    tile inside it. A country is such a region, and a reverse geocoder will
    hand you its bounding box along with its name.

The second is what turns five words into four in ordinary use: "in the UK" is
worth a word.

HOW MANY WORDS A WINDOW BUYS is one number: how many candidate tiles it holds.
Each word is 11 bits, so one fewer word is 2048 times as many tiles, and the 7
check bits leave one in 128 standing -- so a length works exactly when no OTHER
candidate survives, a Poisson zero at rate (tiles - 1)/128. Nothing about
countries enters into it; a country is just a box someone else drew. Measured
against the boxes Nominatim returns:

    Luxembourg      4,700 km2     1.0 tiles   four, always
    Switzerland    76,000 km2     1.0         four, always
    Ireland       193,000 km2     1.1         four, always
    United Kingdom  1.3 M km2     5.5         four, 97% of the time
    France         1.28 M km2     5.5         four, 97% of the time
    Australia      17.3 M km2      71         five -- over the cap
    United States   159 M km2     638         five -- over the cap

AND IT COSTS DETECTION, which MAX_CANDIDATES is there to bound. A misheard word
removes the true tile, so every candidate in the window is a fresh lottery
against the same 7 check bits and a wrong word is caught only (127/128)**k of
the time -- 95.4% at the cap of 6, against 99.2% for the full address. Uncapped,
a window the size of Australia holds ~70 and falls to 58%, where a third of
mishearings resolve SILENTLY to somewhere else in the country. resolve_tail()
has no such loss: it tests the single nearest tile, one chance to be fooled
rather than k.

THE GRID DOES NOT DEPEND ON THE REGION. The window is used when an address is
READ. It is not part of the address and nothing is bound to it, so a border can
move or a territory change hands and the words for a place are unchanged. A
wrong window costs uniqueness, never correctness: the point is simply not the
only survivor, and the full five words are said instead.

SHORTEN THE OTHER WAY BY DROPPING TRAILING WORDS, for a coarser address that
needs no context at all. Each word narrows the area and the words already said
never change, because every address is a prefix of a longer one.

THE LAST WORD DOES TWO JOBS. A whole final word of position would be finer than
anyone needs, so its 11 bits are split: 4 refine the position and 7 carry a
checksum over it. Five words is terminal because a sixth would have to
reinterpret the check bits.

HOW THE PREFIX PROPERTY IS KEPT. The x and y coordinates are interleaved ONCE
at full precision and the resulting bit string is truncated. Deriving the
interleave order per length instead does not work: 11 bits per word is odd, so
33 bits splits the axes 17/16 while 22 and 44 split evenly, and the three
orders are unrelated sequences rather than prefixes of one another.
"""
import hashlib, math, os, sys

R = 6371008.8               # mean earth radius, metres
BITS_PER_WORD = 10          # log2(1024), exactly
REFINE_BITS = 2             # of the last word's 10 bits, how many refine position
CHECK_BITS = BITS_PER_WORD - REFINE_BITS
WORD_MASK = 2 ** BITS_PER_WORD - 1
SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail
EPS = 1e-9                  # degrees of slack on a box edge, for float error
# Searching a region trades DETECTION for a word, and this is the cap on that
# trade. When a word is wrong the true tile is gone, so every candidate in the
# window is a fresh lottery against the same 7 check bits and a wrong word is
# caught only (127/128)**k of the time. Six candidates holds that at 95.4%,
# against 99.2% for the full address; an uncapped window the size of Australia
# holds ~70 and falls to 58%, where a third of mishearings resolve silently to
# the wrong place. resolve_tail() has no such loss: it tests the single nearest
# tile, one chance to be fooled rather than k.
MAX_CANDIDATES = 6

_HERE = os.path.dirname(os.path.abspath(__file__))

# Lambert equal-area, with the standard parallel chosen so the PROJECTED WORLD
# IS SQUARE. Its aspect is pi*K^2, so K = 1/sqrt(pi) makes it exactly 1.
#
# That is what makes cells square. Cell aspect is the frame's aspect times
# 2**(yb-xb), and xb+yb is fixed by the address length, so parity decides which
# powers of two are reachable: an even bit count can only land on frame*4**k.
# With a square frame the even lengths -- which include both terminal lengths,
# 44 and 48 bits -- come out exactly 1:1. At 30 degrees the frame was 2.356:1
# and the five-word cell was 1.03 x 1.75 m; now it is 1.346 m square, for the
# same area, because the projection is equal-area and only the shape changes.
#
# The cost is the odd lengths, which land on frame*2*4**k and so go to 2:1.
# No frame can square both: one exponent is odd whenever the other is even.
_K = 1.0 / math.sqrt(math.pi)
STD_PARALLEL = math.degrees(math.acos(_K))         # 55.654 degrees


class OutsideBox(ValueError):
    """Raised for a coordinate the scope's box does not cover."""


# 1,024 words, every one graded CEFR A1-B2 -- the vocabulary a person can
# retrieve under pressure -- with everything confusable or sound-alike removed.
# Built by tools/wordlist; see that directory's README for how and why.
#
# BIP-39 was here before it, and was the wrong list for this: it is designed to
# be TYPED and checksummed, and contains pair/pear, peace/piece, right/write and
# wear/where, with 53% of it one articulatory feature from another entry.
WORDLIST = os.path.join(_HERE, '..', 'wordlist', 'spoken-1024-plain.txt')
WORDLIST_SHA256 = '33fc2169cabc4ba9232cce43d015f728ab96b0acb971a402077bfb3040430c20'


def load_wordlist(path=WORDLIST):
    with open(path, 'rb') as fh:
        raw = fh.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != WORDLIST_SHA256:
        raise ValueError(f'{path} is not the expected word list (sha256 {got})')
    words = raw.decode().split()
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


_index_cache = (None, None)


def _index(words):
    """word -> value, built once. Rebuilding this whole dict per call was
    a seventh of the test suite's runtime."""
    global _index_cache
    if _index_cache[0] is not words:
        _index_cache = (words, {w: i for i, w in enumerate(words)})
    return _index_cache[1]


def project(lat, lng):
    """Lambert cylindrical equal-area: area-true, which keeps cell areas equal
    across a box. Shape stretches with latitude."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K


def unproject(x, y):
    return (math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))),
            math.degrees(x / (R * _K)))


class Scope:
    """A box, an address length, and the bit layout they imply.

    There is one of these -- GLOBAL. It is a class rather than a handful of
    module constants because the bit layout is DERIVED from the box: which axis
    each bit refines depends on the box's aspect, and having that in one place
    is what lets the tests state the derivation rather than the answer.
    """

    def __init__(self, key, name, box, max_words):
        self.key, self.name, self.box, self.max_words = key, name, box, max_words
        self.position_bits = BITS_PER_WORD * (max_words - 1) + REFINE_BITS
        latMin, latMax, lngMin, lngMax = box
        self.x0, self.y0 = project(latMin, lngMin)
        x1, y1 = project(latMax, lngMax)
        self.xr, self.yr = abs(x1 - self.x0), abs(y1 - self.y0)
        # Which axis each position bit refines, coarse bit first. Not a plain
        # alternation: a box wider than it is tall would carry that aspect down
        # into every cell. Giving each bit to whichever axis is currently wider
        # keeps cells near square at every length, for the same cell area --
        # the projection is equal-area, so only the shape changes.
        self.order, w, h = [], self.xr, self.yr
        for _ in range(self.position_bits):
            if w >= h:
                self.order.append(0); w /= 2
            else:
                self.order.append(1); h /= 2
        self.xb = self.order.count(0)
        self.yb = self.position_bits - self.xb

    def __repr__(self):
        return f'<Scope {self.key} {self.max_words} words>'


# Five words over the whole earth, and the only scope there is.
GLOBAL = Scope('global', 'Global', (-90.0, 90.0, -180.0, 180.0), 6)
DEFAULT = GLOBAL
SCOPES = {GLOBAL.key: GLOBAL}


def _wrap(latlng):
    """A box past 180 unprojects past 180 too; bring it back to -180..180."""
    lat, lng = latlng
    return lat, (lng + 180.0) % 360.0 - 180.0


def scope(s=GLOBAL):
    """Accept a Scope or its key."""
    return s if isinstance(s, Scope) else SCOPES[s]


def normalise_lng(lng, s=GLOBAL):
    """Bring a longitude into the box's frame.

    A box straddling the antimeridian runs past 180 -- Asia is 26 to 190 -- so
    a point in Chukotka arrives as -175 and must be read as 185. The
    short-circuit matters: a value a hair BELOW lngMin would otherwise wrap to
    nearly lngMin + 360, throwing a point on the western edge out of its box.
    """
    s = scope(s)
    lngMin, lngMax = s.box[2], s.box[3]
    if lngMin - EPS <= lng <= lngMax + EPS:
        return lng
    return lngMin + (lng - lngMin) % 360.0


def covers(lat, lng, s=GLOBAL):
    s = scope(s)
    latMin, latMax, lngMin, lngMax = s.box
    return (latMin - EPS <= lat <= latMax + EPS
            and lngMin - EPS <= normalise_lng(lng, s) <= lngMax + EPS)


def _indices(lat, lng, s=GLOBAL):
    """Grid indices of a point: s.xb bits of x, s.yb bits of y."""
    s = scope(s)
    if not covers(lat, lng, s):
        raise OutsideBox(f'{lat:.5f}, {lng:.5f} is outside {s.name} '
                         f'({s.box[0]}..{s.box[1]}, {s.box[2]}..{s.box[3]})')
    x, y = project(lat, normalise_lng(lng, s))
    # Both ends are clamped. The top saturates a point on the boundary -- the
    # poles, the antimeridian, a box edge -- into the last cell. The bottom is
    # only reachable by floating-point slop, but an unclamped negative index
    # would sign-extend under >> and mint a plausible address for the wrong
    # place, so it is clamped rather than trusted.
    def cell(v, lo, span, bits):
        return min(max(int((v - lo) / span * 2 ** bits), 0), 2 ** bits - 1)
    return cell(x, s.x0, s.xr, s.xb), cell(y, s.y0, s.yr, s.yb)


def _interleave(xi, yi, s=GLOBAL):
    s = scope(s)
    v, xa, ya = 0, s.xb, s.yb
    for axis in s.order:
        if axis == 0:
            xa -= 1; v = (v << 1) | ((xi >> xa) & 1)
        else:
            ya -= 1; v = (v << 1) | ((yi >> ya) & 1)
    return v


def _spread(val, axis, s=GLOBAL):
    """One axis's bits placed at their positions in the interleaved value, with
    the other axis's positions left zero.

    Interleaving is bit-disjoint between the axes -- every output bit belongs to
    exactly one of them -- so _interleave(xi, yi) is exactly
    _spread(xi, 0) | _spread(yi, 1). Searching a box exploits that: the two axes
    are spread once each and OR-ed per candidate, which is what makes the search
    O(nx + ny) interleaves rather than O(nx * ny).
    """
    s = scope(s)
    out, a = 0, (s.xb if axis == 0 else s.yb)
    for ax in s.order:
        out <<= 1
        if ax == axis:
            a -= 1
            out |= (val >> a) & 1
    return out


def _deinterleave(v, bits, s=GLOBAL):
    s = scope(s)
    xi = yi = 0
    for i, axis in enumerate(s.order[:bits]):
        bit = (v >> (bits - 1 - i)) & 1
        if axis == 0:
            xi = (xi << 1) | bit
        else:
            yi = (yi << 1) | bit
    return xi, yi


def _position_bits(n_words, s=GLOBAL):
    """Position bits an n-word address carries. The last word contributes only
    REFINE_BITS, the rest all 10."""
    s = scope(s)
    if n_words < s.max_words:
        return BITS_PER_WORD * n_words
    return s.position_bits


def _axis_bits(n_words, s=GLOBAL):
    s = scope(s)
    bits = _position_bits(n_words, s)
    xb = s.order[:bits].count(0)
    return xb, bits - xb


def cell_size(n_words, s=GLOBAL):
    """(width, height) in metres of the cell an n-word address names."""
    s = scope(s)
    xb, yb = _axis_bits(n_words, s)
    return s.xr / 2 ** xb, s.yr / 2 ** yb


def tile_size(n_said, s=GLOBAL):
    """(width, height) of the ambiguity left when an address is given as its
    last n_said words, the leading ones dropped."""
    s = scope(s)
    return cell_size(s.max_words - n_said, s) if n_said < s.max_words else (s.xr, s.yr)


def _checksum(position, s=GLOBAL):
    """Seven bits over the whole position -- which is what makes both kinds of
    shortening safe, since a reconstruction that guesses wrong fails it."""
    payload = position.to_bytes(8, 'big')
    return int.from_bytes(hashlib.sha256(payload).digest()[:2], 'big') >> (16 - CHECK_BITS)


def _value(lat, lng, s=GLOBAL):
    """The full address value: position bits then CHECK_BITS of checksum."""
    s = scope(s)
    position = _interleave(*_indices(lat, lng, s), s)
    return (position << CHECK_BITS) | _checksum(position, s)


def encode(lat, lng, words, n_words=None, s=GLOBAL):
    """The first n_words of the address. Coarser as n_words falls; needs no
    context at any length."""
    s = scope(s)
    n_words = s.max_words if n_words is None else n_words
    if not 1 <= n_words <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    value = _value(lat, lng, s)
    if n_words < s.max_words:
        # Truncate the position; the check bits are not part of a short form.
        value >>= BITS_PER_WORD * (s.max_words - n_words)
    return [words[(value >> (BITS_PER_WORD * (n_words - 1 - i))) & WORD_MASK]
            for i in range(n_words)]


def _from_position(position, s=GLOBAL):
    s = scope(s)
    xi, yi = _deinterleave(position, s.position_bits, s)
    return _wrap(unproject(s.x0 + (xi + 0.5) / 2 ** s.xb * s.xr,
                           s.y0 + (yi + 0.5) / 2 ** s.yb * s.yr))


def decode(spoken, words, s=GLOBAL):
    """Resolve an address: the first n words, coarser as n falls.

    A full-length address is checked; raises ValueError if a word is wrong.
    """
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    if not 1 <= len(spoken) <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    value = 0
    for w in spoken:
        value = (value << BITS_PER_WORD) | index[w]
    if len(spoken) < s.max_words:
        prefix = value
    else:
        prefix = value >> CHECK_BITS
        if (value & (2 ** CHECK_BITS - 1)) != _checksum(prefix, s):
            raise ValueError('checksum failed - a word is wrong')
    bits = _position_bits(len(spoken), s)
    xb, yb = _axis_bits(len(spoken), s)
    xi, yi = _deinterleave(prefix, bits, s)
    return _wrap(unproject(s.x0 + (xi + 0.5) / 2 ** xb * s.xr,
                           s.y0 + (yi + 0.5) / 2 ** yb * s.yr))


def _known_low(n_said, s=GLOBAL):
    """How many low bits of each axis index a tail of n_said words pins down."""
    s = scope(s)
    dropped = BITS_PER_WORD * (s.max_words - n_said)
    dx = s.order[:dropped].count(0)
    return s.xb - dx, s.yb - (dropped - dx)


def resolve_tail(spoken, words, near_lat, near_lng, s=GLOBAL):
    """Resolve an address given only its last words, plus a reference point.

    The dropped words are the coarse ones, so the reference supplies them: for
    each axis, take the candidate matching the known low bits that is nearest
    the reference. The checksum then covers the whole reconstruction, so a
    reference too far off to pick the right tile is caught 99.2% of the time
    rather than resolving quietly to the wrong place.
    """
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    n = len(spoken)
    if not 1 <= n <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    value_low = 0
    for w in spoken:
        value_low = (value_low << BITS_PER_WORD) | index[w]
    check = value_low & (2 ** CHECK_BITS - 1)
    known_bits = BITS_PER_WORD * n - CHECK_BITS
    pos_low = value_low >> CHECK_BITS
    cx, cy = _known_low(n, s)
    known_x = known_y = 0
    for i in range(known_bits):
        seq = s.position_bits - known_bits + i
        bit = (pos_low >> (known_bits - 1 - i)) & 1
        if s.order[seq] == 0:
            known_x = (known_x << 1) | bit
        else:
            known_y = (known_y << 1) | bit
    xi_ref, yi_ref = _indices(near_lat, near_lng, s)

    def nearest_x(known, count, ref):
        """The candidate nearest the reference, going the short way round.

        Global x wraps: the projection is a cylinder, so a reference a few
        kilometres west of the antimeridian is a whole world-width away in
        index terms while being next door on the ground. A partial box does not
        wrap, so it is clamped like y.
        """
        period = 2 ** count
        if s is GLOBAL:
            total = 2 ** s.xb
            k = round(((ref - known) % total) / period) % (total // period)
            return (known + k * period) % total
        return _clamp_lattice(known, period, ref, s.xb)

    def nearest_y(known, count, ref):
        """y never wraps -- latitude ends at the poles -- so it is clamped, but
        to the last point ON the lattice: clamping to the last index would
        leave a value the known bits do not match."""
        return _clamp_lattice(known, 2 ** count, ref, s.yb)

    xi = nearest_x(known_x, cx, xi_ref)
    yi = nearest_y(known_y, cy, yi_ref)
    position = _interleave(xi, yi, s)
    if _checksum(position, s) != check:
        raise ValueError('checksum failed - a word is wrong, or the reference '
                         'point is too far away to fill in the missing words')
    return _from_position(position, s)


def _clamp_lattice(known, period, ref, bits):
    v = known + round((ref - known) / period) * period
    return min(max(v, known), known + (2 ** bits - 1 - known) // period * period)


def candidates_in_box(spoken, words, box, s=GLOBAL, limit=20000):
    """Every point inside `box` whose address ends with these words and whose
    checksum passes.

    This is the other way to fill in dropped leading words. resolve_tail() needs
    a reference POINT and takes the nearest candidate; this needs only a REGION
    and lets the checksum choose, which is what a country name gives you. The
    region is never part of the address -- it is a search window -- so getting it
    slightly wrong costs uniqueness, never correctness.

    Returns (candidates, searched). More than one candidate means the region is
    too big to pin these words down; none means the words do not belong in it.
    """
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not BIP-39 words: {unknown}')
    n = len(spoken)
    if not 1 <= n <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    value = 0
    for w in spoken:
        value = (value << BITS_PER_WORD) | index[w]
    check = value & (2 ** CHECK_BITS - 1)
    known_bits = BITS_PER_WORD * n - CHECK_BITS
    pos_low = value >> CHECK_BITS
    cx, cy = _known_low(n, s)
    known_x = known_y = 0
    for i in range(known_bits):
        seq = s.position_bits - known_bits + i
        bit = (pos_low >> (known_bits - 1 - i)) & 1
        if s.order[seq] == 0:
            known_x = (known_x << 1) | bit
        else:
            known_y = (known_y << 1) | bit
    # The window, clipped to the scope's own box.
    latMin, latMax, lngMin, lngMax = box
    x0, y0 = project(latMin, normalise_lng(lngMin, s))
    x1, y1 = project(latMax, normalise_lng(lngMax, s))
    to_i = lambda v, lo, span, bits: int((v - lo) / span * 2 ** bits)
    lo_x = max(0, to_i(min(x0, x1), s.x0, s.xr, s.xb))
    hi_x = min(2 ** s.xb - 1, to_i(max(x0, x1), s.x0, s.xr, s.xb))
    lo_y = max(0, to_i(min(y0, y1), s.y0, s.yr, s.yb))
    hi_y = min(2 ** s.yb - 1, to_i(max(y0, y1), s.y0, s.yr, s.yb))
    px, py = 2 ** cx, 2 ** cy
    xs = range(known_x + -(-(lo_x - known_x) // px) * px, hi_x + 1, px)
    ys = range(known_y + -(-(lo_y - known_y) // py) * py, hi_y + 1, py)
    count = len(xs) * len(ys)
    if count > limit:
        return None, count                  # too many to be worth enumerating
    # See _spread(): the axes occupy disjoint bits, so each is spread once and
    # the candidates are an OR of the two, not an interleave apiece.
    ys_spread = [_spread(yi, 1, s) for yi in ys]
    out = []
    for xi in xs:
        xv = _spread(xi, 0, s)
        for yv in ys_spread:
            position = xv | yv
            if _checksum(position, s) == check:
                out.append(_from_position(position, s))
    return out, count


def shortest_in_box(lat, lng, words, box, s=GLOBAL):
    """The fewest trailing words that identify this point uniquely inside `box`,
    WITHOUT weakening the checksum past MAX_CANDIDATES.

    Falls back to the full address when the region is too big -- either because
    nothing shorter is unique, or because pinning it down would have cost more
    detection than a word is worth. The second is what stops a country the size
    of Australia from shortening: a window that big is unique often enough to be
    tempting and weak enough to be wrong.
    """
    s = scope(s)
    full = encode(lat, lng, words, s.max_words, s)
    want = _indices(lat, lng, s)
    for n in range(1, s.max_words):
        # The cap doubles as the enumeration limit: a window it would reject is
        # counted and dropped rather than searched, which is what keeps this
        # cheap at the lengths that were never going to work.
        got, searched = candidates_in_box(full[-n:], words, box, s, MAX_CANDIDATES)
        if searched > MAX_CANDIDATES:
            continue
        if got and len(got) == 1 and _indices(got[0][0], got[0][1], s) == want:
            return n, full[-n:]
    return s.max_words, full


def decode_in_box(spoken, words, box, s=GLOBAL):
    """Resolve a shortened address inside a region, or refuse.

    The reader's half of shortest_in_box(), and where the MAX_CANDIDATES cap
    actually protects anyone: a window too big to search safely is refused
    rather than answered from, so an address that should never have been
    shortened cannot be read as though it had been.
    """
    got, searched = candidates_in_box(spoken, words, box, s, MAX_CANDIDATES)
    if searched > MAX_CANDIDATES:
        raise ValueError(
            f'{searched} candidates in this region, more than the {MAX_CANDIDATES} '
            f'a 7-bit check can screen - say the whole address')
    if not got:
        raise ValueError('checksum failed - a word is wrong, or this address '
                         'does not belong in this region')
    if len(got) > 1:
        raise ValueError(f'{len(got)} places here match - say one more word')
    return got[0]


def words_needed(lat, lng, near_lat, near_lng, words, s=GLOBAL):
    """The fewest trailing words that resolve back to this point from that
    reference, or the scope's full length if even that is needed."""
    s = scope(s)
    full = encode(lat, lng, words, s=s)
    for n in range(1, s.max_words + 1):
        try:
            got = resolve_tail(full[-n:], words, near_lat, near_lng, s)
        except ValueError:
            continue
        if _indices(*got, s) == _indices(lat, lng, s):
            return n
    return s.max_words


def format_address(spoken, tail=False):
    """'leg.tunnel.slam' absolute, '.slam.subway.gown' for a tail."""
    return (TAIL_MARK if tail else '') + SEP.join(spoken)


def parse_address(text):
    """Split into (words, is_tail)."""
    text = text.strip().replace(',', SEP).replace(' ', SEP)
    tail = text.startswith(SEP)
    parts = [p.lower() for p in text.split(SEP) if p]
    if not parts:
        raise ValueError('empty address')
    return parts, tail
