"""Synthetic complex footprints shared by geometry tests and diagnostic renders."""
import numpy as np
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union


def complex_roofs():
    shapes = [
        ("L wings / recessed entrance", unary_union([box(0, 0, 26, 9), box(0, 0, 10, 26)]).difference(box(10, 0, 14, 2))),
        ("T wings / unequal spans", unary_union([box(0, 16, 34, 26), box(12, 0, 22, 26)])),
        ("H wings / opposing recesses", unary_union([box(0, 0, 8, 30), box(24, 0, 34, 30), box(0, 11, 34, 19)])),
        ("U wings / deep open court", box(0, 0, 34, 30).difference(box(8, 0, 25, 23))),
        ("Two enclosed courtyards", box(0, 0, 42, 32).difference(unary_union([box(6, 7, 17, 25), box(25, 6, 36, 24)]))),
        ("Stepped wings / narrow link", unary_union([box(0, 0, 20, 10), box(8, 8, 20, 26),
                                                    box(18, 19, 25, 21), box(24, 14, 38, 26)])),
        ("Diagonal wing / acute joins", unary_union([box(0, 0, 25, 12),
                                                     affinity.rotate(box(7, 0, 17, 32), -32, origin=(12, 6))])),
        ("Bay fronts / bevels / recess", box(0, 0, 30, 22).union(affinity.rotate(box(6, -4, 15, 5), 32, origin=(10, 0)))
          .difference(box(18, 0, 23, 5)).union(box(29.999999, 8, 34, 14))),
        ("Offset court / thin rear wing", box(0, 0, 38, 26).difference(box(3, 4, 29, 23)).union(box(36, 8, 48, 11))),
        ("Eight wings / oblique edges", unary_union([affinity.rotate(box(-5, -5, 25, 5), angle, origin=(0, 0))
                                                     for angle in range(0, 360, 45)])),
        ("Sawtooth outline / small edges", box(0, 0, 40, 20).union(unary_union([box(x, -2, x+2, 2) for x in range(0, 40, 4)]))),
        ("Courtyard with oblique corner", box(0, 0, 36, 28).difference(affinity.rotate(box(8, 6, 27, 21), 17, origin=(18, 14)))),
    ]
    return [(name, tuple(poly.exterior.coords)[:-1], tuple(tuple(h.coords)[:-1] for h in poly.interiors))
            for name, poly in shapes]


def transform(ring, angle=0., scale=1., offset=(0., 0.)):
    t = np.radians(angle)
    rotation = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return tuple(map(tuple, np.asarray(ring) @ rotation.T * scale + offset))
