#!/usr/bin/env python3
"""Pick the largest set of words no two of which a mishearing can confuse."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phonetics import distance, phonemes, SWAP


def audit(entries, threshold):
    """Every pair closer than the threshold. `entries` is (word, phonemes)."""
    by_len = {}
    for w, ph in entries:
        by_len.setdefault(len(ph), []).append((w, ph))
    span = int(threshold // SWAP) + 1
    seen, out = set(), []
    for w, ph in entries:
        for n in range(len(ph) - span, len(ph) + span + 1):
            for v, ph2 in by_len.get(n, ()):
                if v == w or (v, w) in seen:
                    continue
                d = distance(ph, ph2, threshold)
                if d < threshold:
                    seen.add((w, v))
                    out.append((d, w, v))
    return sorted(out)


def select(pool, threshold, want=None):
    """Greedy, most familiar first: take a word if nothing already taken is
    within the threshold of it. Greedy is not optimal -- maximum independent set
    is NP-hard -- but taking the common words first is the ordering that matters,
    since a rare word that displaces three familiar ones is a bad trade."""
    span = int(threshold // SWAP) + 1
    taken, by_len = [], {}
    for w, ph, rank in pool:
        clash = False
        for n in range(len(ph) - span, len(ph) + span + 1):
            for v, ph2 in by_len.get(n, ()):
                if distance(ph, ph2, threshold) < threshold:
                    clash = True
                    break
            if clash:
                break
        if not clash:
            taken.append((w, ph, rank))
            by_len.setdefault(len(ph), []).append((w, ph))
            if want and len(taken) >= want:
                break
    return taken
