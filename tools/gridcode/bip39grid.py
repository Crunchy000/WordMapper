#!/usr/bin/env python3
"""Word addresses from an easy-English word list, on one global grid.

FIVE WORDS name any point on earth to 4.48 m:

    kangaroo.wagon.machine.structure.science

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
Each word is a base-36 digit on each axis, so one fewer word is 1296 times as
many tiles, and the check leaves one in CHECK standing -- so a length works
exactly when no OTHER candidate survives, a Poisson zero at rate
(tiles - 1)/CHECK. Nothing about
countries enters into it; a country is just a box someone else drew. Measured
against the boxes Nominatim returns:

    Luxembourg      4,700 km2     1.0 tiles   four, always
    Switzerland    76,000 km2     1.0         four, always
    Ireland       193,000 km2     1.0         four, always
    United Kingdom  1.3 M km2     3.6         four, 97% of the time
    France         1.28 M km2     3.5         four, 98% of the time
    Australia      17.3 M km2      45         five -- over the cap
    United States   159 M km2     405         five -- over the cap

AND IT COSTS DETECTION, which MAX_CANDIDATES is there to bound. A misheard word
removes the true tile, so every candidate in the window is a fresh lottery
against the same checksum and a wrong word is caught only ((CHECK-1)/CHECK)**k
of the time -- 95.9% at the cap of 6, against 99.31% for the full address.
Uncapped, a window the size of Australia holds ~45 and falls to 73%, where a
quarter of mishearings resolve SILENTLY to somewhere else in the country.
resolve_tail() has no such loss: it tests the single nearest tile, one chance to
be fooled rather than k.

THE GRID DOES NOT DEPEND ON THE REGION. The window is used when an address is
READ. It is not part of the address and nothing is bound to it, so a border can
move or a territory change hands and the words for a place are unchanged. A
wrong window costs uniqueness, never correctness: the point is simply not the
only survivor, and the full five words are said instead.

SHORTEN THE OTHER WAY BY DROPPING TRAILING WORDS, for a coarser address that
needs no context at all. Each word narrows the area and the words already said
never change, because every address is a prefix of a longer one.

THE LAST WORD DOES TWO JOBS. A whole final word of position would be finer than
anyone needs, so the last word splits a cell only REFINE x REFINE and spends the
rest of its LIST_SIZE values on a checksum over the whole position. Five words
is terminal because a sixth would have to reinterpret the check.

WHY THE PREFIX PROPERTY IS FREE. Each word is one base-36 digit of x and one of
y, so a shorter address is literally the leading digits of a longer one and the
leading digits do not depend on the trailing ones. The binary layout this
replaced had to interleave the coordinates ONCE at full precision and truncate
the bit string: deriving the interleave order per length does not work, because
11 bits per word is odd, so 33 bits splits the axes 17/16 while 22 and 44 split
evenly, and the three orders are unrelated sequences rather than prefixes of one
another.
"""
import hashlib, math, os, sys

R = 6371008.8               # mean earth radius, metres
# THE ADDRESS IS BASE-36, NOT BINARY. Each word subdivides a cell RADIX x RADIX,
# so a word is one digit of x and one of y: word value = xdigit * RADIX + ydigit.
# The list is therefore RADIX**2 words, and a power of two is not required --
# which is the whole point. Binary forced the list to 1024 and the cell to
# 10.8 m; 36 x 36 is 1296 words and 4.5 m, for the same five words said.
#
# It is also simpler. There is no bit-interleaving, no per-length axis split and
# no question of which axis a bit refines: digits are digits, the leading ones
# do not depend on the trailing ones, and the prefix property falls out for
# free. The frame is square and both axes get the same splits, so every cell at
# every length is exactly square without anyone arranging it.
RADIX = 36                  # each word splits a cell RADIX x RADIX
REFINE = 3                  # ...except the last, which splits only REFINE x REFINE
LIST_SIZE = RADIX * RADIX                       # 1296 words
CHECK = LIST_SIZE // (REFINE * REFINE)          # 144 values of checksum
SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail
EPS = 1e-9                  # degrees of slack on a box edge, for float error
# Searching a region trades DETECTION for a word, and this is the cap on that
# trade. When a word is wrong the true tile is gone, so every candidate in the
# window is a fresh lottery against the same checksum and a wrong word is caught
# only ((CHECK-1)/CHECK)**k of the time. Six candidates holds that at 95.9%,
# against 99.31% for the full address; an uncapped window the size of Australia
# holds ~35 and falls to 78%, where a fifth of mishearings resolve silently to
# the wrong place. resolve_tail() has no such loss: it tests the single nearest
# tile, one chance to be fooled rather than k.
MAX_CANDIDATES = 6

_HERE = os.path.dirname(os.path.abspath(__file__))

# Lambert equal-area, with the standard parallel chosen so the PROJECTED WORLD
# IS SQUARE. Its aspect is pi*K^2, so K = 1/sqrt(pi) makes it exactly 1.
#
# That is what makes cells square, and with base-36 digits it is the only thing
# that has to: both axes get the same RADIX split at every word, so a square
# frame gives a square cell at every length, full stop. Under the old binary
# layout this took a greedy bit order and still left the odd lengths at 2:1.
# At 30 degrees the frame was 2.356:1 and cells inherited that aspect; the
# projection is equal-area, so fixing it changes shape and never resolution.
_K = 1.0 / math.sqrt(math.pi)
STD_PARALLEL = math.degrees(math.acos(_K))         # 55.654 degrees


class OutsideBox(ValueError):
    """Raised for a coordinate the scope's box does not cover."""


# 1,296 words, every one graded CEFR A1-B2 -- the vocabulary a person can
# retrieve under pressure -- with everything confusable or sound-alike removed.
# Built by tools/wordlist; see that directory's README for how and why.
#
# BIP-39 was here before it, and was the wrong list for this: it is designed to
# be TYPED and checksummed, and contains pair/pear, peace/piece, right/write and
# wear/where, with 53% of it one articulatory feature from another entry.
WORDLIST = os.path.join(_HERE, '..', 'wordlist', 'spoken-1296-plain.txt')
WORDLIST_SHA256 = '6737c7c8ea7645cca2fe5534cf63de485d77be68b04a2c1df9e298082b169e37'


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
    """A box, an address length, and the subdivision they imply.

    There is one of these -- GLOBAL. It is a class rather than a handful of
    module constants because the layout is DERIVED from the box and the length,
    and having that derivation in one place is what lets the tests state it
    rather than restate its answer.
    """

    def __init__(self, key, name, box, max_words):
        self.key, self.name, self.box, self.max_words = key, name, box, max_words
        # How far each word subdivides a cell, coarsest first. Every word but
        # the last splits RADIX x RADIX; the last splits only REFINE x REFINE
        # and spends the rest of itself on the checksum.
        self.splits = [RADIX] * (max_words - 1) + [REFINE]
        self.div = math.prod(self.splits)       # divisions per axis at full length
        latMin, latMax, lngMin, lngMax = box
        self.x0, self.y0 = project(latMin, lngMin)
        x1, y1 = project(latMax, lngMax)
        self.xr, self.yr = abs(x1 - self.x0), abs(y1 - self.y0)

    def divisions(self, n_words):
        """Divisions per axis for an address of this many words."""
        return math.prod(self.splits[:n_words])

    def __repr__(self):
        return f'<Scope {self.key} {self.max_words} words>'


# Five words over the whole earth, and the only scope there is.
GLOBAL = Scope('global', 'Global', (-90.0, 90.0, -180.0, 180.0), 5)
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
    """Grid indices of a point, each in [0, s.div)."""
    s = scope(s)
    if not covers(lat, lng, s):
        raise OutsideBox(f'{lat:.5f}, {lng:.5f} is outside {s.name} '
                         f'({s.box[0]}..{s.box[1]}, {s.box[2]}..{s.box[3]})')
    x, y = project(lat, normalise_lng(lng, s))
    # Both ends are clamped. The top saturates a point on the boundary -- the
    # poles, the antimeridian -- into the last cell; the bottom is only
    # reachable by floating-point slop, but an unclamped negative index would
    # mint a plausible address for the wrong place.
    def cell(v, lo, span):
        return min(max(int((v - lo) / span * s.div), 0), s.div - 1)
    return cell(x, s.x0, s.xr), cell(y, s.y0, s.yr)


def _digits(i, splits):
    """One index as per-word digits, coarsest first."""
    out, rem = [], i
    for k in range(len(splits)):
        period = math.prod(splits[k + 1:])
        out.append(rem // period)
        rem %= period
    return out


def _undigits(digits, splits):
    """Digits back to an index. The inverse of _digits for the same splits."""
    i = 0
    for d, sp in zip(digits, splits):
        i = i * sp + d
    return i


def cell_size(n_words, s=GLOBAL):
    """Metres on the ground for an address of this many words."""
    s = scope(s)
    d = s.divisions(n_words)
    return s.xr / d, s.yr / d


def tile_size(n_said, s=GLOBAL):
    """The ambiguity left by dropping the LEADING words: how far apart the
    candidates sit, and so how close a reference has to be."""
    s = scope(s)
    return cell_size(s.max_words - n_said, s) if n_said < s.max_words else (s.xr, s.yr)


def _checksum(xi, yi, s=GLOBAL):
    """One of CHECK values over the whole position -- which is what makes both
    kinds of shortening safe, since a reconstruction that guesses wrong fails
    it."""
    payload = xi.to_bytes(8, 'big') + yi.to_bytes(8, 'big')
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big') % CHECK


def _word_values(xi, yi, s=GLOBAL):
    """The value of each word of the full address, coarsest first."""
    s = scope(s)
    xd, yd = _digits(xi, s.splits), _digits(yi, s.splits)
    out = [xd[k] * RADIX + yd[k] for k in range(s.max_words - 1)]
    last = xd[-1] * REFINE + yd[-1]
    return out + [last * CHECK + _checksum(xi, yi, s)]


def encode(lat, lng, words, n_words=None, s=GLOBAL):
    """The first n_words of the address. Coarser as n_words falls; needs no
    context at any length.

    The leading digits do not depend on the trailing ones, so a shorter address
    is literally a prefix of the longer one -- no truncation subtlety, unlike
    the interleaved binary layout this replaced.
    """
    s = scope(s)
    n_words = s.max_words if n_words is None else n_words
    if not 1 <= n_words <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    return [words[v] for v in _word_values(*_indices(lat, lng, s), s)[:n_words]]


def _from_indices(xi, yi, n_words, s=GLOBAL):
    """The centre of the cell those indices name, at that address length."""
    s = scope(s)
    d = s.divisions(n_words)
    return _wrap(unproject(s.x0 + (xi + 0.5) / d * s.xr,
                           s.y0 + (yi + 0.5) / d * s.yr))


def decode(spoken, words, s=GLOBAL):
    """Resolve an address: the first n words, coarser as n falls.

    A full-length address is checked; raises ValueError if a word is wrong.
    """
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    n = len(spoken)
    if not 1 <= n <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    xd, yd, check = [], [], None
    for k, w in enumerate(spoken):
        v = index[w]
        if k == s.max_words - 1:
            pos, check = divmod(v, CHECK)
            xd.append(pos // REFINE); yd.append(pos % REFINE)
        else:
            xd.append(v // RADIX); yd.append(v % RADIX)
    splits = s.splits[:n]
    xi, yi = _undigits(xd, splits), _undigits(yd, splits)
    if check is not None and _checksum(xi, yi, s) != check:
        raise ValueError('checksum failed - a word is wrong')
    return _from_indices(xi, yi, n, s)


def _known_period(n_said, s=GLOBAL):
    """The spacing of the candidates a tail of n_said words leaves.

    The words said fix the TRAILING digits, so the candidates are every index
    congruent to them modulo the product of those digits' places.
    """
    s = scope(s)
    dropped = s.max_words - n_said
    return math.prod(s.splits[dropped:])


def _tail_position(spoken, words, s=GLOBAL):
    """(known_x, known_y, check, period) for an address missing its leading
    words. The known digits are the low ones; the period is how far apart the
    candidates sit."""
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    n = len(spoken)
    if not 1 <= n <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    dropped = s.max_words - n
    xd, yd, check = [], [], None
    for k, w in enumerate(spoken):
        v = index[w]
        if dropped + k == s.max_words - 1:
            pos, check = divmod(v, CHECK)
            xd.append(pos // REFINE); yd.append(pos % REFINE)
        else:
            xd.append(v // RADIX); yd.append(v % RADIX)
    tail_splits = s.splits[dropped:]
    return (_undigits(xd, tail_splits), _undigits(yd, tail_splits), check,
            math.prod(tail_splits))


def resolve_tail(spoken, words, near_lat, near_lng, s=GLOBAL):
    """Resolve an address given only its last words, plus a reference point.

    The dropped words are the coarse ones, so the reference supplies them: for
    each axis, take the candidate matching the known low digits that is nearest
    the reference. The checksum then covers the whole reconstruction, so a
    reference too far off to pick the right tile is caught rather than resolving
    quietly to the wrong place.
    """
    s = scope(s)
    known_x, known_y, check, period = _tail_position(spoken, words, s)
    if check is None:
        raise ValueError('a tail must include the last word, which carries the '
                         'checksum')
    xi_ref, yi_ref = _indices(near_lat, near_lng, s)

    def nearest_x(known, ref):
        """The candidate nearest the reference, going the short way round.

        Global x wraps: the projection is a cylinder, so a reference a few
        kilometres west of the antimeridian is a whole world-width away in
        index terms while being next door on the ground. A partial box does not
        wrap, so it is clamped like y.
        """
        if s is GLOBAL:
            k = round(((ref - known) % s.div) / period) % (s.div // period)
            return (known + k * period) % s.div
        return _clamp_lattice(known, period, ref, s.div)

    xi = nearest_x(known_x, xi_ref)
    yi = _clamp_lattice(known_y, period, yi_ref, s.div)
    if _checksum(xi, yi, s) != check:
        raise ValueError('checksum failed - a word is wrong, or the reference '
                         'point is too far away to fill in the missing words')
    return _from_indices(xi, yi, s.max_words, s)


def _clamp_lattice(known, period, ref, div):
    """The lattice point nearest the reference, kept inside [0, div)."""
    v = known + round((ref - known) / period) * period
    return min(max(v, known), known + (div - 1 - known) // period * period)


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
    known_x, known_y, check, period = _tail_position(spoken, words, s)
    if check is None:
        return [], 0
    # The window, clipped to the scope's own box.
    latMin, latMax, lngMin, lngMax = box
    x0, y0 = project(latMin, normalise_lng(lngMin, s))
    x1, y1 = project(latMax, normalise_lng(lngMax, s))
    to_i = lambda v, lo, span: int((v - lo) / span * s.div)
    lo_x = max(0, to_i(min(x0, x1), s.x0, s.xr))
    hi_x = min(s.div - 1, to_i(max(x0, x1), s.x0, s.xr))
    lo_y = max(0, to_i(min(y0, y1), s.y0, s.yr))
    hi_y = min(s.div - 1, to_i(max(y0, y1), s.y0, s.yr))
    xs = range(known_x + -(-(lo_x - known_x) // period) * period, hi_x + 1, period)
    ys = range(known_y + -(-(lo_y - known_y) // period) * period, hi_y + 1, period)
    count = len(xs) * len(ys)
    if count > limit:
        return None, count                  # too many to be worth enumerating
    out = [_from_indices(xi, yi, s.max_words, s)
           for xi in xs for yi in ys if _checksum(xi, yi, s) == check]
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
            f'a {CHECK}-value check can screen - say the whole address')
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
