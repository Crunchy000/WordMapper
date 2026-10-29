#!/usr/bin/env python3
"""Build uk-mask.txt: which 2 km squares of the UK grid can be addressed.

Run once, with Natural Earth's 1:10m admin-0 countries as input:

    curl -sSLO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson
    python3 tools/gridcode/build_uk_mask.py ne_10m_admin_0_countries.geojson

A square is in if any land of the UK, the Isle of Man, Jersey or Guernsey
touches it -- sampled every 250 m, plus every outline vertex so a rock smaller
than a sample still counts -- or if it borders one that does. That border is
the coastal strip: harbours, piers, beaches and the first couple of kilometres
of sea.

The mask is written as run lengths over the grid, row by row from the south,
alternating out/in and starting with out. It is committed, so neither CI nor
the demo needs the source data.
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ukgrid as u

COUNTRIES = ('GBR', 'IMN', 'JEY', 'GGY')
SAMPLE = 250.0              # metres between land samples


def rings(path):
    with open(path) as fh:
        data = json.load(fh)
    for f in data['features']:
        if f['properties'].get('ADM0_A3') not in COUNTRIES:
            continue
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            for ring in poly:
                yield np.array([u.project(lat, lng) for lng, lat in ring])


def main(path):
    all_rings = list(rings(path))
    k = int(u.SQUARE / SAMPLE)
    ns_x, ns_y = u.GRID_W * k, u.GRID_H * k
    land = np.zeros((ns_y, ns_x), dtype=bool)
    # Even-odd scanline fill at the centre of each sample row: the parity of
    # crossings to the left of a sample says whether it is on land.
    for j in range(ns_y):
        y = u.Y0 + (j + 0.5) * SAMPLE
        xs = []
        for r in all_rings:
            a, b = r[:-1], r[1:]
            hit = (a[:, 1] <= y) != (b[:, 1] <= y)
            if hit.any():
                a, b = a[hit], b[hit]
                xs.append(a[:, 0] + (y - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1]))
        if not xs:
            continue
        xs = np.sort(np.concatenate(xs))
        cols = np.searchsorted(xs, u.X0 + (np.arange(ns_x) + 0.5) * SAMPLE)
        land[j] = cols % 2 == 1
    squares = land.reshape(u.GRID_H, k, u.GRID_W, k).any(axis=(1, 3))
    for r in all_rings:
        for x, y in r:
            i, j = int((x - u.X0) // u.SQUARE), int((y - u.Y0) // u.SQUARE)
            if 0 <= i < u.GRID_W and 0 <= j < u.GRID_H:
                squares[j, i] = True
    # The coastal strip: every square next to land, diagonals included.
    grown = squares.copy()
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            grown |= np.roll(np.roll(squares, dj, 0), di, 1)
    grown[0, :] = grown[-1, :] = grown[:, 0] = grown[:, -1] = False
    flat = grown.ravel()
    runs, cur, n = [], False, 0
    for v in flat:
        if v == cur:
            n += 1
        else:
            runs.append(n); cur, n = v, 1
    runs.append(n)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uk-mask.txt')
    with open(out, 'w') as fh:
        fh.write(','.join(map(str, runs)) + '\n')
    print(f'{int(squares.sum())} land squares, {int(grown.sum())} with the coastal strip, '
          f'{len(runs)} runs -> {out}')


if __name__ == '__main__':
    main(sys.argv[1])
