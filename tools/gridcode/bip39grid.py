#!/usr/bin/env python3
"""Word addresses from the BIP-39 list, in two scopes.

    npm install --prefix tools/gridcode

GLOBAL -- five words, anywhere on earth, 1.35 m:

    leg.tunnel.slam.subway.gown

LOCAL -- four words, over a box around the United Kingdom, self-contained.
This is the default:

    hollow.gadget.crane.pupil

Both are the same grid mechanism over a different box. The scope is bound into
the checksum, so a Local address read as a global one fails its check 99.2% of the
time, and the reverse likewise -- the two can never be silently confused.

WHICH TO USE. Local is the default: one word shorter, and it needs nothing
said or known beyond "this is a local address". Global works everywhere and is
finer.

Global mode can also be shortened by dropping LEADING words when whoever is
listening already knows roughly where you are -- and four global words that
way reach 1.35 m against Local's 2.43 m, because one dropped word is worth a
full 11 bits of context where the Local box is worth only 9.3. Local earns its
place on ergonomics rather than resolution: nothing to agree, nothing to
reconstruct, no reference point.

BOTH SHORTEN BY DROPPING TRAILING WORDS, for a coarser address that needs no
context at all. Each word narrows the area and the words already said never
change, because every address is a prefix of a longer one.

THE LAST WORD DOES TWO JOBS in either scope. A whole final word of position
would be finer than anyone needs, so its 11 bits are split: 4 refine the
position and 7 carry a checksum over the scope and the position together. Each
scope's terminal length is terminal because a further word would have to
reinterpret the check bits.

HOW THE PREFIX PROPERTY IS KEPT. The x and y coordinates are interleaved ONCE
at full precision and the resulting bit string is truncated. Deriving the
interleave order per length instead does not work: 11 bits per word is odd, so
33 bits splits the axes 17/16 while 22 and 44 split evenly, and the three
orders are unrelated sequences rather than prefixes of one another.
"""
import hashlib, json, math, os, subprocess, sys

R = 6371008.8               # mean earth radius, metres
BITS_PER_WORD = 11          # log2(2048), exactly
REFINE_BITS = 4             # of the last word's 11 bits, how many refine position
CHECK_BITS = BITS_PER_WORD - REFINE_BITS
SEP = '.'
TAIL_MARK = SEP             # a leading separator marks a context-dependent tail
EPS = 1e-9                  # degrees of slack on a box edge, for float error

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


def load_wordlist():
    out = subprocess.check_output(
        ['node', '-e', "console.log(JSON.stringify(require('bip39').wordlists.english))"],
        cwd=_HERE)
    words = json.loads(out)
    assert len(words) == 2 ** BITS_PER_WORD, len(words)
    return words


def project(lat, lng):
    """Lambert cylindrical equal-area: area-true, which keeps cell areas equal
    across a box. Shape stretches with latitude."""
    return R * math.radians(lng) * _K, R * math.sin(math.radians(lat)) / _K


def unproject(x, y):
    return (math.degrees(math.asin(max(-1.0, min(1.0, y * _K / R)))),
            math.degrees(x / (R * _K)))


class Scope:
    """A box, an address length, and the bit layout they imply."""

    def __init__(self, key, name, tag, box, max_words):
        self.key, self.name, self.box, self.max_words = key, name, box, max_words
        # Bound into the checksum, so an address minted in one scope cannot
        # verify in the other. Global binds the empty string, which no scope
        # tag can be.
        self.tag = tag
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


# Five words over the whole earth. The floor: it always works, and it is what
# anywhere outside every regional box falls back to.
GLOBAL = Scope('global', 'Global', '', (-90.0, 90.0, -180.0, 180.0), 5)

# Four words over a regional box. Each tag is bound into the checksum, so an
# address minted in one region cannot verify in another.
#
# Asia and Oceania run PAST 180 rather than stopping at it, so that Chukotka
# and Fiji stay inside one box instead of being split in half by the
# antimeridian; see normalise_lng.
REGIONS = [
    Scope('local',   'Local',         'GB', (49.85, 60.90, -10.70,   1.80), 4),
    Scope('europe',  'Europe',        'EU', (34.00, 71.50, -25.00,  60.00), 4),
    Scope('africa',  'Africa',        'AF', (-35.00, 37.50, -18.00,  52.00), 4),
    Scope('namerica', 'North America', 'NA', (5.00, 83.50, -168.00, -52.00), 4),
    Scope('samerica', 'South America', 'SA', (-56.00, 13.50, -82.00, -34.00), 4),
    Scope('asia',    'Asia',          'AS', (-11.00, 81.50,  26.00, 190.00), 4),
    # Oceania stops at 9 degrees south, which is what keeps Java, Bali and
    # Timor in Asia where they belong: Australia's northern tip is 10.7 S, so
    # the whole continent still fits under the line. PNG and the Solomons are
    # cut by it -- a rectangle cannot follow the Indonesian archipelago.
    Scope('oceania', 'Oceania',       'OC', (-48.00, -9.00, 112.00, 184.00), 4),
]
LOCAL = REGIONS[0]
UK = LOCAL                                  # the old name, still accepted
DEFAULT = LOCAL
SCOPES = {sc.key: sc for sc in REGIONS + [GLOBAL]}


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
    REFINE_BITS, the rest all 11."""
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
    """Over the scope as well as the position, so a Local address read as a global
    one fails the same check as a wrong word."""
    s = scope(s)
    # Global's payload is the bare position, which is what it has always been,
    # so every global address ever published stays valid. A tagged scope
    # prepends its tag, which no untagged payload can begin with.
    payload = position.to_bytes(8, 'big')
    if s.tag:
        payload = s.tag.encode() + b'\0' + payload
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
    return [words[(value >> (BITS_PER_WORD * (n_words - 1 - i))) & 0x7ff]
            for i in range(n_words)]


def _from_position(position, s=GLOBAL):
    s = scope(s)
    xi, yi = _deinterleave(position, s.position_bits, s)
    return _wrap(unproject(s.x0 + (xi + 0.5) / 2 ** s.xb * s.xr,
                           s.y0 + (yi + 0.5) / 2 ** s.yb * s.yr))


def decode(spoken, words, s=GLOBAL):
    """Resolve an address: the first n words, coarser as n falls.

    A full-length address is checked; raises ValueError if a word is wrong or
    the address belongs to the other scope.
    """
    s = scope(s)
    index = {w: i for i, w in enumerate(words)}
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
            raise ValueError('checksum failed - a word is wrong, '
                             'or this address belongs to the other scope')
    bits = _position_bits(len(spoken), s)
    xb, yb = _axis_bits(len(spoken), s)
    xi, yi = _deinterleave(prefix, bits, s)
    return _wrap(unproject(s.x0 + (xi + 0.5) / 2 ** xb * s.xr,
                           s.y0 + (yi + 0.5) / 2 ** yb * s.yr))


def best_scope(lat, lng):
    """The scope to use for a point: the SMALLEST regional box containing it,
    or Global where none does.

    Smallest wins for two reasons that agree. It is the finest cell, and it is
    also the region a person would name: boxes are nested where they overlap,
    so Local beats Europe over Britain and Europe beats Asia over Moscow.
    """
    hit = [sc for sc in REGIONS if covers(lat, lng, sc)]
    return min(hit, key=lambda sc: (sc.xr * sc.yr, sc.key)) if hit else GLOBAL


def scopes_covering(lat, lng):
    """Every regional box containing the point, smallest first."""
    return sorted((sc for sc in REGIONS if covers(lat, lng, sc)),
                  key=lambda sc: (sc.xr * sc.yr, sc.key))


def decode_auto(spoken, words):
    """Resolve without being told the scope. Returns (lat, lng, scope, verified).

    A terminal-length address carries a checksum over its own scope, so it
    identifies itself: four words that pass the Local check are a Local address, and
    five that pass the global check are a global one. Anything shorter is an
    unverified coarse prefix, and only the caller knows which scope it belongs
    to, so global is assumed and `verified` says it was not confirmed.

    This matters because the two directions are not symmetrical. A global
    prefix read as UK fails its checksum 99.2% of the time and is caught. A Local
    address read as a global prefix would decode silently to a different place
    entirely, since nothing checks a prefix -- so the Local reading is tried first.
    """
    matches = []
    for sc in REGIONS + [GLOBAL]:
        if len(spoken) != sc.max_words:
            continue
        try:
            lat, lng = decode(spoken, words, sc)
        except ValueError:
            continue
        matches.append((lat, lng, sc))
    if matches:
        # More than one scope can accept the same words by luck: each wrong one
        # passes its own 7-bit check with probability 1/128, so with seven
        # regional boxes an address is ambiguous about 5% of the time. The
        # caller usually knows the region -- pass it to decode() instead of
        # guessing here -- so this returns the first match and leaves the
        # ambiguity to be measured rather than hidden. See scopes_accepting().
        lat, lng, sc = matches[0]
        return lat, lng, sc, True
    lat, lng = decode(spoken, words, GLOBAL)
    return lat, lng, GLOBAL, False


def scopes_accepting(spoken, words):
    """Every scope whose checksum accepts these words. More than one means the
    address does not identify itself and the region has to be stated."""
    out = []
    for sc in REGIONS + [GLOBAL]:
        if len(spoken) != sc.max_words:
            continue
        try:
            decode(spoken, words, sc)
        except ValueError:
            continue
        out.append(sc)
    return out


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
    index = {w: i for i, w in enumerate(words)}
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
