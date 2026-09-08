#!/usr/bin/env python3
"""How far a word stands from every OTHER word in the language.

This is the tie-break that decides which member of a confusable set survives.
When `pretty`, `petty` and `plenty` cannot all be on the list, the one to keep is
not the most common -- it is the one that is hardest to confuse with anything
ELSE, because it has to survive contact with the whole language, not just with
the other 2047 words on the list.
"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import distance, NEAR, SWAP

# Past the selection threshold a word is isolated enough and the exact value is
# noise, so the search stops there. This is not a detail: starting the running
# best at 2.0 rather than 3.0 lets the cheap bound reject most of the dictionary
# without ever running the edit distance.
CUTOFF = 2.0


def _bound(ca, cb):
    """A cheap floor on the distance, from phoneme counts alone.

    Every phoneme in one word with no partner in the other must be substituted,
    inserted or deleted, and the cheapest of those is a confusable substitution
    at 0.5. Computing this first skips the full edit distance for the great
    majority of pairs, which is what makes this run at all."""
    return max(sum((ca - cb).values()), sum((cb - ca).values())) * NEAR


def isolation_chunk(args):
    return isolation(*args)


def isolation(pool, reference, cutoff=CUTOFF):
    """word -> distance to its nearest neighbour in `reference`, capped.

    `pool` and `reference` are both [(word, phonemes)]. A word's identical twin
    in the reference is skipped; a homophone of it is not, and scores 0.
    """
    by_len = {}
    counts = {}
    for w, ph in reference:
        by_len.setdefault(len(ph), []).append((w, ph))
        counts[w] = Counter(ph)
    span = int(cutoff // SWAP) + 1
    out = {}
    for w, ph in pool:
        ca = Counter(ph)
        best = cutoff
        # Nearest lengths first: the closest neighbour is usually the same
        # length, and finding it early prunes everything after it.
        for n in sorted(range(len(ph) - span, len(ph) + span + 1),
                        key=lambda k: abs(k - len(ph))):
            for v, ph2 in by_len.get(n, ()):
                if v == w:
                    continue
                if _bound(ca, counts[v]) >= best:
                    continue
                d = distance(ph, ph2, best)
                if d < best:
                    best = d
                    if best == 0.0:
                        break
            if best == 0.0:
                break
        out[w] = best
    return out


def isolation_parallel(pool, reference, cutoff=CUTOFF, workers=None):
    """Same answer, split across cores. Each word is independent of every other,
    so this is the one part of the build that parallelises for free."""
    import multiprocessing
    workers = workers or (os.cpu_count() or 1)
    if workers < 2 or len(pool) < 200:
        return isolation(pool, reference, cutoff)
    n = (len(pool) + workers - 1) // workers
    chunks = [(pool[i:i + n], reference, cutoff) for i in range(0, len(pool), n)]
    out = {}
    with multiprocessing.Pool(workers) as p:
        for part in p.map(isolation_chunk, chunks):
            out.update(part)
    return out
