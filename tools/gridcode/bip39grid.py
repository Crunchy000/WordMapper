#!/usr/bin/env python3
"""Word addresses from an easy-English word list, on one global grid.

SIX WORDS name any point on earth to 2.99 m, and a misheard word is caught
999,988 times in a million:

    kilo.waitress.maintain.table.glint.export

There is one grid and one address for a place. No regional boxes, no scope to
choose, nothing to switch, and NOTHING TO SHORTEN AGAINST. Six words is the
address, everywhere, always.

That last part used to be otherwise. A country could supply the leading word,
which bought a word at the cost of a network call, an inconsistent word count
(the same country giving four words here and five there), and -- the real
objection -- DETECTION. A misheard word removes the true tile, so every
candidate the country box leaves is a fresh lottery against the same checksum,
and a wrong word was caught only ((CHECK-1)/CHECK)**k of the time instead of
(CHECK-1)/CHECK. Saying the sixth word costs less than that and is the same
every time.

THE ADDRESS IS BASE-36. Each word subdivides a cell by its split, so a word is
one digit of x, one of y and one of the checksum: value = (xd*split + yd)*check
+ chk. The list is RADIX**2 = 1296 words, and a power of two is not required --
which is the whole point. Binary forced the list to 1024 and the cell to 10.8 m.

EVERY WORD CAN CARRY CHECK, AND THE CHECKS MULTIPLY. A word that splits its cell
r x r keeps r**2 of its 1296 values for position and has 1296/r**2 left over, so
SPLITS fixes the resolution and the strength of the checksum together:

    SPLITS = [36, 36, 36, 18,  9,    1]
    CHECKS = [ 1,  1,  1,  4, 16, 1296]   ->  CHECK = 82,944

Words one to three have nothing to spare. Word four splits 18 x 18 and word five
9 x 9, each keeping a little back. WORD SIX SPLITS 1 x 1: it moves the position
not at all and is nothing but check. Only the PRODUCT of the splits sets the
cell size, so where the check lives across the words does not matter -- but the
checks MULTIPLY, which is how the check gets far bigger than any one word.

THE CHECKSUM IS OVER THE WHOLE POSITION, so no part of it can be verified until
the whole position is known. Five words reach full depth (word six adds no
position), so five words are checked at 1 in 64 and six at the whole 82,944.
Below five the check digits are dead weight -- the price of 2.99 m.

SHORTEN BY DROPPING TRAILING WORDS, for a coarser address that needs no context
at all. Each word narrows the area and the words already said never change,
because every address is a prefix of a longer one -- which in base-36 is free,
since the leading digits do not depend on the trailing ones.

    1 word   627 km      4 words   26.89 m
    2 words   17.4 km    5 words    2.99 m   checked 1 in 64
    3 words  484 m       6 words    2.99 m   checked 1 in 82,944

DROPPING LEADING WORDS still works, given a reference POINT: resolve_tail()
takes the candidate nearest the reference and tests that ONE candidate, so it
costs no detection at all. That is what distinguishes it from the country search
that used to be here, and why it survived the cull.
"""
import collections, hashlib, math, os, sys

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
RADIX = 36                  # a word that splits a cell RADIX x RADIX
LIST_SIZE = RADIX * RADIX                       # 1296 words
# EVERY WORD CAN CARRY CHECK, AND THE CHECKS MULTIPLY. A word that splits its
# cell r x r spends r**2 of its LIST_SIZE values on position and has
# LIST_SIZE // r**2 left over -- so SPLITS fixes both the resolution and the
# strength of the checksum, and they trade against each other one for one.
#
# The last word splits 1 x 1: it moves the position not at all and is pure
# check. That is the whole of what the sixth word is. It costs no resolution
# and multiplies the check by 1296.
#
# Check digits are assigned least-significant-first, so each length's check
# modulus divides the next one's: a shorter address is verified more weakly
# rather than differently, and a longer one only ever strengthens it.
# EXACTLY THREE METRES. Word five's refinement has to divide 36, so on its own
# it jumps 3 -> 4 -> 6 and the cell jumps 4.48 -> 3.36 -> 2.24 m, stepping over
# 3 m entirely. Getting there means taking the last factor of 2 out of word
# FOUR as well: 36 x 36 x 36 x 18 x 9 = 7,558,272 divisions, or 2.99 m.
#
# That costs a four-word address, which coarsens from 13.45 m to 26.9 m -- and
# it is the reason to think twice. Word four's spare values go to the checksum,
# but the checksum is over the WHOLE position, so a four-word address cannot
# verify them -- they are dead weight at that length and pay off only at five
# words and six.
SPLITS = [RADIX, RADIX, RADIX, RADIX // 2, RADIX // 4, 1]
CHECKS = [LIST_SIZE // (r * r) for r in SPLITS]  # [1, 1, 1, 1, 144, 1296]
CHECK = math.prod(CHECKS)                        # 186,624 values of checksum
SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail
EPS = 1e-9                  # degrees of slack on a box edge, for float error
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


Tail = collections.namedtuple('Tail', 'known_x known_y check modulus divisor period')


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

    def __init__(self, key, name, box, splits=None):
        self.key, self.name, self.box = key, name, box
        # How far each word subdivides a cell, coarsest first, and what each
        # therefore has left over for the checksum.
        self.splits = list(SPLITS if splits is None else splits)
        self.checks = [LIST_SIZE // (r * r) for r in self.splits]
        self.max_words = len(self.splits)
        self.check = math.prod(self.checks)
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
GLOBAL = Scope('global', 'Global', (-90.0, 90.0, -180.0, 180.0))
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


def _check_digits(v, checks):
    """One checksum spread across the words, LEAST significant first.

    Least-significant-first is the whole of the backwards compatibility: word
    five gets `v % 144`, which is exactly the checksum it carried when it was
    the last word, and everything above 144 goes to word six. Big-endian would
    have moved word five and invalidated every address in circulation.
    """
    out = []
    for c in checks:
        out.append(v % c)
        v //= c
    return out


def _undigits_check(digits, checks):
    """Check digits back to the value they encode, for the same checks."""
    v = 0
    for d, c in zip(reversed(digits), reversed(checks)):
        v = v * c + d
    return v


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
    it.

    Note 144 divides 186,624, so this modulo agrees with the old one on its low
    digit: the five-word check is a genuine prefix of the six-word one, not a
    different function that happens to be near it.
    """
    s = scope(s)
    payload = xi.to_bytes(8, 'big') + yi.to_bytes(8, 'big')
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big') % s.check


def _word_values(xi, yi, s=GLOBAL):
    """The value of each word of the full address, coarsest first.

    Each word packs a digit of x, a digit of y and a digit of the checksum:
    (xd * split + yd) * check + chk. A word that splits 36 x 36 has nothing
    left for check; the last word splits 1 x 1 and is nothing but check.
    """
    s = scope(s)
    xd, yd = _digits(xi, s.splits), _digits(yi, s.splits)
    cd = _check_digits(_checksum(xi, yi, s), s.checks)
    return [(xd[k] * s.splits[k] + yd[k]) * s.checks[k] + cd[k]
            for k in range(s.max_words)]


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
    xd, yd, cd = [], [], []
    for k, w in enumerate(spoken):
        pos, chk = divmod(index[w], s.checks[k])
        xd.append(pos // s.splits[k]); yd.append(pos % s.splits[k]); cd.append(chk)
    splits = s.splits[:n]
    xi, yi = _undigits(xd, splits), _undigits(yd, splits)
    # THE CHECKSUM IS OVER THE WHOLE POSITION, so no prefix of it is determined
    # until the whole position is. A four-word address stops one split short of
    # full depth, so word four's check digit -- which is a digit of a hash of
    # digits it has not said yet -- cannot be verified from it, and is simply
    # dead weight at that length. Five words reach full depth (word six splits
    # 1 x 1 and adds no position), so five is where verification starts: 1 in
    # 64 there, and the whole 82,944 at six.
    modulus = math.prod(s.checks[:n]) if s.divisions(n) == s.div else 1
    if modulus > 1 and _checksum(xi, yi, s) % modulus != _undigits_check(cd, s.checks[:n]):
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
    """Tail(known_x, known_y, check, modulus, divisor, period) for an address
    missing its leading words. The known digits are the low ones; the period is
    how far apart the candidates sit; the check the words carry is
    `(checksum // divisor) % modulus`, since the dropped words took their own
    check digits with them."""
    s = scope(s)
    index = _index(words)
    unknown = [w for w in spoken if w not in index]
    if unknown:
        raise ValueError(f'not on the word list: {unknown}')
    n = len(spoken)
    if not 1 <= n <= s.max_words:
        raise ValueError(f'1..{s.max_words} words in {s.name}')
    dropped = s.max_words - n
    xd, yd, cd = [], [], []
    for k, w in enumerate(spoken):
        j = dropped + k
        pos, chk = divmod(index[w], s.checks[j])
        xd.append(pos // s.splits[j]); yd.append(pos % s.splits[j]); cd.append(chk)
    tail_splits, tail_checks = s.splits[dropped:], s.checks[dropped:]
    return Tail(_undigits(xd, tail_splits), _undigits(yd, tail_splits),
                _undigits_check(cd, tail_checks), math.prod(tail_checks),
                math.prod(s.checks[:dropped]), math.prod(tail_splits))


def resolve_tail(spoken, words, near_lat, near_lng, s=GLOBAL):
    """Resolve an address given only its last words, plus a reference point.

    The dropped words are the coarse ones, so the reference supplies them: for
    each axis, take the candidate matching the known low digits that is nearest
    the reference. The checksum then covers the whole reconstruction, so a
    reference too far off to pick the right tile is caught rather than resolving
    quietly to the wrong place.
    """
    s = scope(s)
    t = _tail_position(spoken, words, s)
    known_x, known_y, period = t.known_x, t.known_y, t.period
    if t.modulus == 1:
        raise ValueError('a tail must reach the words that carry the checksum')
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
    if (_checksum(xi, yi, s) // t.divisor) % t.modulus != t.check:
        raise ValueError('checksum failed - a word is wrong, or the reference '
                         'point is too far away to fill in the missing words')
    return _from_indices(xi, yi, s.max_words, s)


def _clamp_lattice(known, period, ref, div):
    """The lattice point nearest the reference, kept inside [0, div)."""
    v = known + round((ref - known) / period) * period
    return min(max(v, known), known + (div - 1 - known) // period * period)


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
