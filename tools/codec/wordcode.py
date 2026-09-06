#!/usr/bin/env python3
"""Self-correcting word addresses: Reed-Solomon over GF(53^2).

The word list has 1849 = 43^2 entries and 43 is prime, so GF(1849) is a genuine
finite field and one word is exactly one field element -- no wasted symbols, and
every check value is itself a valid word.

Two code lengths, nested so the shorter is a prefix of the longer:

    3 words + 1 check  ->  corrects any single ERASURE, detects any single error
    3 words + 2 checks ->  corrects any single ERROR at an unknown position

An erasure is a symbol known to be wrong. That is the normal case here: the
word list is a tiny subset of English, and no two entries are within one edit of
each other, so a mistyped or misheard word is not in the list at all and its
position is therefore known. Erasure correction needs half the redundancy of
error correction, which is why four words suffice in practice.

The check weights are distinct per position, so swapping two words changes the
syndrome. A plain sum would not: addition is commutative, and word-order swaps
would pass silently.
"""
import json, os

P = 43                      # word list is P*P entries
# x^2 - NR is irreducible over GF(P) when NR is a quadratic non-residue
NR = next(n for n in range(2, P) if pow(n, (P - 1) // 2, P) == P - 1)

# --- GF(P^2) as a + b*t with t^2 = NR -----------------------------------------
def add(u, v): return ((u[0] + v[0]) % P, (u[1] + v[1]) % P)
def sub(u, v): return ((u[0] - v[0]) % P, (u[1] - v[1]) % P)
def mul(u, v):
    a, b = u; c, d = v
    return ((a * c + b * d * NR) % P, (a * d + b * c) % P)
def inv(u):
    a, b = u
    det = pow((a * a - NR * b * b) % P, P - 2, P)
    return ((a * det) % P, (-b * det) % P)
def div(u, v): return mul(u, inv(v))

ZERO = (0, 0)
def to_el(i): return (i % P, i // P)
def to_idx(u): return u[0] + P * u[1]

# Position weights. b_i = a_i^2 makes any two columns of the parity-check matrix
# independent, which is what gives the 5-symbol code distance 3.
A = [to_el(1), to_el(2), to_el(3)]
B = [mul(a, a) for a in A]

def _parity(data, weights):
    t = ZERO
    for w, d in zip(weights, data):
        t = add(t, mul(w, d))
    return sub(ZERO, t)

def encode(indices, checks=1):
    """indices: 3 word indices. Returns 3+checks indices."""
    if len(indices) != 3:
        raise ValueError('this code carries exactly 3 location words')
    d = [to_el(i) for i in indices]
    out = list(d) + [_parity(d, A)]
    if checks == 2:
        out.append(_parity(d, B))
    return [to_idx(x) for x in out]

def _syndromes(cw):
    """cw: list of field elements, length 4 or 5."""
    s0 = add(_parity_sum(cw[:3], A), cw[3])
    if len(cw) == 4:
        return (s0, None)
    return (s0, add(_parity_sum(cw[:3], B), cw[4]))

def _parity_sum(data, weights):
    t = ZERO
    for w, d in zip(weights, data):
        t = add(t, mul(w, d))
    return t

def decode(received):
    """received: list of word indices, or None for a word known to be wrong.

    Returns (indices, status) where status is one of
    'ok', 'corrected', 'detected' (an error exists but cannot be located),
    or 'failed'.
    """
    n = len(received)
    if n not in (4, 5):
        raise ValueError('expected 4 or 5 symbols')
    missing = [i for i, x in enumerate(received) if x is None]
    if len(missing) > 1:
        return None, 'failed'

    if missing:
        pos = missing[0]
        cw = [ZERO if x is None else to_el(x) for x in received]
        # Solve the first parity equation for the one unknown.
        w = (A + [to_el(1)])[pos] if pos < 4 else None
        if pos == 4:                      # second check is the missing one
            out = list(received); out[4] = to_idx(_parity([to_el(x) for x in received[:3]], B))
            return out, 'corrected'
        rest = ZERO
        for i in range(4):
            if i == pos: continue
            wt = A[i] if i < 3 else to_el(1)
            rest = add(rest, mul(wt, cw[i]))
        val = div(sub(ZERO, rest), A[pos] if pos < 3 else to_el(1))
        out = list(received); out[pos] = to_idx(val)
        return out, 'corrected'

    cw = [to_el(x) for x in received]
    s0, s1 = _syndromes(cw)
    if s0 == ZERO and (s1 is None or s1 == ZERO):
        return list(received), 'ok'
    if n == 4:
        return None, 'detected'           # one check cannot locate the error
    if s0 == ZERO:                        # error is in the second check word
        out = list(received); out[4] = to_idx(sub(cw[4], s1)); return out, 'corrected'
    loc = div(s1, s0)
    for i, a in enumerate(A):
        if a == loc:
            e = div(s0, a)
            out = list(received); out[i] = to_idx(sub(cw[i], e)); return out, 'corrected'
    if loc == ZERO:                       # error is in the first check word
        out = list(received); out[3] = to_idx(sub(cw[3], s0)); return out, 'corrected'
    return None, 'failed'

# --- word-level convenience ---------------------------------------------------
def load_words(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'data', 'wordlist.json')
    return json.load(open(path))


def load_aliases(path=None):
    """Alternate spellings that decode to the same address: color -> colour."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'data', 'aliases.json')
    return json.load(open(path)) if os.path.exists(path) else {}

def encode_words(three, words, checks=1):
    idx = {w: i for i, w in enumerate(words)}
    return [words[i] for i in encode([idx[w] for w in three], checks)]

def decode_words(spoken, words, aliases=None):
    """Any word not in the list is treated as a known-position erasure.

    An accepted alternate spelling resolves to its canonical word first, so
    "color" and "colour" reach the same address.
    """
    idx = {w: i for i, w in enumerate(words)}
    if aliases is None:
        aliases = load_aliases()
    received = [idx.get(aliases.get(w, w)) for w in spoken]
    out, status = decode(received)
    return ([words[i] for i in out] if out else None), status
