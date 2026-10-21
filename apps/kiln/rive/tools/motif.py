"""The persistent hero motif: a sculptural vessel with a cobalt glaze accent,
plus the asymmetric plinth it stands on.

Every vessel profile has the same 12 vertices in the same order, so any two
profiles can be keyed against each other and the runtime interpolates the
silhouette (lump -> vessel, vessel -> slab -> plinth, the six forms of scene 7).
"""
from __future__ import annotations

import math

from rml import smooth_vertices, unwrap

T = [0.0, 0.2, 0.44, 0.68, 0.88, 1.0]

# name: (height, [(cx, half_width)] at the six T heights)
PROFILES = {
    "lump":   (96,  [(0, 86), (2, 94), (4, 84), (2, 66), (0, 44), (0, 24)]),
    "slab":   (24,  [(0, 118), (0, 120), (0, 120), (0, 119), (0, 118), (0, 116)]),
    "pinch":  (70,  [(0, 60), (0, 74), (0, 70), (0, 50), (0, 30), (0, 10)]),
    "vessel": (250, [(0, 46), (2, 80), (4, 92), (0, 60), (-2, 32), (-2, 46)]),
    "vase":   (350, [(0, 46), (-12, 74), (16, 50), (6, 76), (-14, 34), (-6, 46)]),
    "bowl":   (88,  [(0, 40), (0, 72), (0, 94), (0, 106), (0, 112), (0, 114)]),
    "cup":    (128, [(0, 40), (0, 46), (0, 50), (0, 52), (0, 54), (0, 56)]),
    "bottle": (300, [(0, 52), (0, 72), (0, 70), (0, 36), (0, 15), (0, 22)]),
    "jar":    (200, [(0, 58), (0, 86), (0, 92), (0, 80), (0, 56), (0, 60)]),
    "idea":   (236, [(0, 42), (16, 82), (-10, 58), (8, 76), (18, 34), (22, 44)]),
    "orb":    (124, [(0, 12), (0, 50), (0, 61.5), (0, 57.5), (0, 40), (0, 9)]),
    "jug":    (200, [(0, 46), (0, 68), (0, 76), (0, 56), (0, 42), (0, 60)]),
    "tall":   (300, [(0, 30), (0, 46), (0, 52), (0, 40), (0, 24), (0, 30)]),
    # persona pieces (3D only)
    "coilpot": (132, [(0, 46), (0, 56), (0, 60), (0, 58), (0, 52), (0, 50)]),
    "shell":  (96,  [(0, 34), (0, 70), (0, 92), (0, 104), (0, 110), (0, 112)]),
}
SEVEN = ["bowl", "cup", "vessel", "bottle", "jar", "idea"]


def profile_points(name: str):
    h, rows = PROFILES[name]
    right = [(cx + w, -h * t) for (t, (cx, w)) in zip(T, rows)]
    left = [(cx - w, -h * t) for (t, (cx, w)) in zip(T, rows)]
    # counter-clockwise in y-down space: up the right side, back down the left
    return right + list(reversed(left))


def profile_vertices(name: str, base=None):
    pts = profile_points(name)
    n = len(pts)
    # 0 = bottom-right corner, 5 = right lip, 6 = left lip, 11 = bottom-left corner
    sharp = {0: 5.0, 11: 5.0, 5: 3.0, 6: 3.0}
    vs = smooth_vertices(pts, closed=True, tension=0.18, sharp=sharp)
    # lips and base corners: point the handles along the silhouette, not across
    out = []
    for i, (x, y, r, d) in enumerate(vs):
        if i in (0, 11):  # base corners: tangent along the bottom
            r = 0.0 if i == 0 else math.pi
        if base is not None:
            r = unwrap(base[i][2], r)
        out.append((x, y, r, d))
    return out


def profile_height(name: str) -> float:
    return PROFILES[name][0]


# Plinth: an asymmetric carved block. 6 front vertices + 4 top-face vertices.
def plinth_points(w: float, h: float, tilt: float = 6.0, depth: float = 16.0, skew: float = 10.0):
    front = [
        (-w / 2, 0.0),
        (w * 0.12, -tilt * 0.4),
        (w / 2, -tilt),
        (w / 2 + 3, h),
        (-w / 2 - 6, h),
        (-w / 2 - 3, h * 0.45),
    ]
    top = [
        (-w / 2, 0.0),
        (-w / 2 + skew, -depth),
        (w / 2 + skew * 0.6, -depth - tilt),
        (w / 2, -tilt),
    ]
    return front, top
