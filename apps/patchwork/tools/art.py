"""Patchwork vector art helpers: fabric patches, stitches and folk motifs.

All geometry is built from Rive primitives (Rectangle, Ellipse, Triangle,
Star, PointsPath) so every piece stays editable in the Rive editor.
"""
import math
import random

from rml import (el, shape, node, rect, ellipse, poly_path, curve_path, fill, stroke, solid, argb, new_id)

# ------------------------------------------------------------------ palette
IND = "FF304B75"
TER = "FFCC7051"
ROSE = "FFE9ACB2"
OAT = "FFF5EBDD"
TEAL = "FF4D8F83"
# tints / shades derived from the five brand colours
IND_D = "FF233A5E"
IND_L = "FF5B739C"
TER_D = "FFA95A40"
TER_L = "FFE09A7E"
ROSE_D = "FFD48C95"
ROSE_L = "FFF4D3D6"
OAT_D = "FFE8D9C3"
OAT_DD = "FFD9C6A8"
TEAL_D = "FF3A6E65"
TEAL_L = "FF8DBBB1"
MUST = "FFD9A54A"  # small sun accent, as in the art-direction reference
CREAM = "FFFBF6EE"
SHADOW = "33233A5E"


def a(color, alpha):
    """Return colour with a new alpha (colour is AARRGGBB)."""
    return argb(color[2:], alpha)


_rng = random.Random(7)


def jitter(v=2.5):
    return _rng.uniform(-v, v)


def fabric_quad(w, h, j=2.5, r=3.0, name="Fabric"):
    hw, hh = w / 2, h / 2
    pts = [(-hw + jitter(j), -hh + jitter(j), r), (hw + jitter(j), -hh + jitter(j), r),
           (hw + jitter(j), hh + jitter(j), r), (-hw + jitter(j), hh + jitter(j), r)]
    return poly_path(pts, name=name)


def stitch_rect(w, h, inset=6, color=None, thick=1.4, dash=(5, 4), r=2, name="Stitch"):
    color = color or a(OAT, 0.85)
    return shape(name, rect(w - inset * 2, h - inset * 2, r=r), stroke(color, thick, cap="round", dash=dash))


def patch(name, w, h, color, motif=None, stitch_col=None, shadow=True, x=0, y=0, rot=0.0, j=2.5,
          inner=None, r=3.0):
    """A fabric patch centred on (x, y). Returns (outer_node, body_node)."""
    kids = []
    if inner:
        kids.extend(inner)
    if motif:
        kids.extend(motif)
    kids.append(stitch_rect(w, h, color=stitch_col))
    kids.append(shape("Cloth", fabric_quad(w, h, j=j, r=r), fill(color)))
    if shadow:
        kids.append(shape("Shade", fabric_quad(w, h, j=j, r=r), fill(SHADOW), x=2.5, y=3.5))
    body = node(name + " body", *kids)
    outer = node(name, body, x=x, y=y, rotation=rot)
    return outer, body


# ------------------------------------------------------------------ motifs
# every motif is centred on (0,0) and roughly `s` units across

def m_heart(s, color, x=0, y=0, name="Heart", stitch=True):
    k = s / 100.0
    # build heart from vertices: smoother than primitive union
    verts = [
        el("StraightVertex", x=0, y=38 * k),
        el("CubicDetachedVertex", x=-46 * k, y=-6 * k, inRotation=1.9, inDistance=26 * k, outRotation=-1.57, outDistance=18 * k),
        el("CubicDetachedVertex", x=-24 * k, y=-36 * k, inRotation=3.14159, inDistance=12 * k, outRotation=0, outDistance=12 * k),
        el("CubicDetachedVertex", x=0, y=-20 * k, inRotation=-2.2, inDistance=10 * k, outRotation=-0.94, outDistance=10 * k),
        el("CubicDetachedVertex", x=24 * k, y=-36 * k, inRotation=3.14159, inDistance=12 * k, outRotation=0, outDistance=12 * k),
        el("CubicDetachedVertex", x=46 * k, y=-6 * k, inRotation=-1.57, inDistance=18 * k, outRotation=1.24, outDistance=26 * k),
    ]
    path = el("PointsPath", *verts, isClosed=True, isClockwise=False, name="Path")
    kids = [path, fill(color)]
    out = [shape(name, *kids, x=x, y=y)]
    if stitch:
        verts2 = [el(v.tag, **{kk: (vv * 0.78 if kk in ("x", "y", "inDistance", "outDistance") else vv)
                               for kk, vv in v.attrs.items()}) for v in verts]
        out.insert(0, shape(name + " stitch", el("PointsPath", *verts2, isClosed=True, isClockwise=False, name="Path"),
                            stroke(a(OAT, 0.8), 1.3, dash=(4, 3)), x=x, y=y))
    return out


def m_house(s, wall, roof, window=MUST, x=0, y=0, name="House"):
    k = s / 100.0
    return [
        shape(name + " window", rect(18 * k, 18 * k, r=1.5), fill(window), x=x, y=y + 14 * k),
        shape(name + " roof", el("Triangle", width=86 * k, height=40 * k, originX=0.5, originY=1.0, name="Path"),
              fill(roof), x=x, y=y - 6 * k),
        shape(name + " wall", rect(64 * k, 46 * k, r=2), fill(wall), x=x, y=y + 16 * k),
    ]


def m_leaf(s, color, x=0, y=0, rot=0.0, name="Sprig"):
    k = s / 100.0
    leaves = []
    for i, (lx, ly, lr) in enumerate([(-14, -6, -0.7), (14, -18, 0.7), (-14, -30, -0.7), (14, 6, 0.7)]):
        leaves.append(el("Ellipse", width=30 * k, height=14 * k, x=lx * k, y=ly * k, rotation=lr, name=f"Leaf{i}"))
    stem = el("Rectangle", width=4 * k, height=70 * k, x=0, y=-6 * k, name="Stem")
    return [shape(name, stem, *leaves, fill(color), x=x, y=y, rotation=rot)]


def m_sun(s, color, ray=None, x=0, y=0, name="Sun"):
    k = s / 100.0
    ray = ray or color
    rays = []
    for i in range(9):
        ang = math.pi + i * math.pi / 8
        rr = 44 * k
        rays.append(el("Rectangle", width=6 * k, height=18 * k, x=math.cos(ang) * rr, y=math.sin(ang) * rr + 12 * k,
                       rotation=ang + math.pi / 2, name=f"Ray{i}"))
    return [
        shape(name + " rays", *rays, fill(ray), x=x, y=y),
        shape(name + " disc", el("Ellipse", width=56 * k, height=56 * k, y=12 * k, name="Path"),
              el("Rectangle", width=60 * k, height=30 * k, y=27 * k, name="Cut"), fill(color), x=x, y=y),
    ]


def m_people(s, color, x=0, y=0, name="Neighbours"):
    k = s / 100.0
    kids = []
    for i, (px, sc) in enumerate([(-26, 0.8), (26, 0.8), (0, 1.0)]):
        kids.append(el("Ellipse", width=20 * k * sc, height=20 * k * sc, x=px * k, y=(-14 if sc == 1 else -8) * k, name=f"Head{i}"))
        kids.append(el("Rectangle", width=30 * k * sc, height=30 * k * sc, x=px * k, y=(16 if sc == 1 else 18) * k,
                       cornerRadiusTL=14 * k * sc, name=f"Body{i}"))
    return [shape(name, *kids, fill(color), x=x, y=y)]


def m_tree(s, color, trunk=TER_D, x=0, y=0, name="Tree"):
    k = s / 100.0
    return [
        shape(name + " top", el("Triangle", width=50 * k, height=44 * k, y=-26 * k, originY=0.5, name="T1"),
              el("Triangle", width=62 * k, height=46 * k, y=0, originY=0.5, name="T2"), fill(color), x=x, y=y),
        shape(name + " trunk", rect(8 * k, 22 * k), fill(trunk), x=x, y=y + 30 * k),
    ]


def m_star(s, color, x=0, y=0, points=8, inner=0.45, name="Star", rot=0.0):
    return [shape(name, el("Star", width=s, height=s, points=points, innerRadius=inner, cornerRadius=1.5, name="Path"),
                  fill(color), x=x, y=y, rotation=rot)]


def m_flower(s, color, centre=MUST, x=0, y=0, name="Bloom"):
    k = s / 100.0
    petals = [el("Ellipse", width=26 * k, height=26 * k, x=math.cos(i * 1.2566) * 18 * k,
                 y=math.sin(i * 1.2566) * 18 * k, name=f"P{i}") for i in range(5)]
    return [shape(name + " centre", ellipse(16 * k, 16 * k), fill(centre), x=x, y=y),
            shape(name, *petals, fill(color), x=x, y=y)]


def m_snow(s, color, x=0, y=0, name="Frost"):
    k = s / 100.0
    arms = [el("Rectangle", width=6 * k, height=60 * k, rotation=i * math.pi / 3, cornerRadiusTL=3 * k, name=f"A{i}") for i in range(3)]
    return [shape(name, *arms, fill(color), x=x, y=y)]


def m_mug(s, color, x=0, y=0, name="Mug"):
    k = s / 100.0
    return [
        shape(name + " handle", ellipse(24 * k, 24 * k), stroke(color, 6 * k, cap="round"), x=x + 24 * k, y=y),
        shape(name, rect(44 * k, 50 * k, r=6 * k), fill(color), x=x, y=y),
    ]


def m_book(s, color, page=OAT, x=0, y=0, name="Book"):
    k = s / 100.0
    return [
        shape(name + " pages", rect(56 * k, 6 * k), fill(page), x=x, y=y + 18 * k),
        shape(name, rect(64 * k, 46 * k, r=3 * k), fill(color), x=x, y=y),
    ]


def m_bike(s, color, x=0, y=0, name="Bike"):
    k = s / 100.0
    frame = el("PointsPath", el("StraightVertex", x=-22 * k, y=10 * k), el("StraightVertex", x=-4 * k, y=-12 * k),
               el("StraightVertex", x=22 * k, y=10 * k), el("StraightVertex", x=4 * k, y=10 * k), isClosed=True, name="Path")
    return [
        shape(name + " frame", frame, stroke(color, 4 * k), x=x, y=y),
        shape(name + " wheels", el("Ellipse", width=26 * k, height=26 * k, x=-22 * k, y=10 * k, name="W1"),
              el("Ellipse", width=26 * k, height=26 * k, x=22 * k, y=10 * k, name="W2"), stroke(color, 4 * k), x=x, y=y),
    ]


def m_tools(s, a_col, b_col, x=0, y=0, name="Tools"):
    k = s / 100.0
    return [
        shape(name + " hammer head", rect(40 * k, 14 * k, r=3 * k), fill(b_col), x=x - 12 * k, y=y - 20 * k, rotation=-0.7),
        shape(name + " hammer", rect(8 * k, 64 * k, r=3 * k), fill(a_col), x=x - 4 * k, y=y + 2 * k, rotation=-0.7),
        shape(name + " wrench ring", ellipse(26 * k, 26 * k), stroke(b_col, 7 * k), x=x + 18 * k, y=y - 18 * k),
        shape(name + " wrench", rect(8 * k, 60 * k, r=3 * k), fill(b_col), x=x + 4 * k, y=y + 4 * k, rotation=0.7),
    ]


def m_door(s, frame_col, door_col, x=0, y=0, name="Door"):
    k = s / 100.0
    return [
        shape(name + " knob", ellipse(6 * k, 6 * k), fill(MUST), x=x + 10 * k, y=y + 8 * k),
        shape(name + " leaf", rect(30 * k, 50 * k, r=0, cornerRadiusTR=0, linkCornerRadius=False,
                                    cornerRadiusTL=15 * k), fill(door_col), x=x, y=y + 6 * k),
        shape(name + " frame", rect(44 * k, 64 * k, linkCornerRadius=False, cornerRadiusTL=22 * k, cornerRadiusTR=22 * k),
              fill(frame_col), x=x, y=y + 2 * k),
    ]


def m_cross_stitch(s, color, x=0, y=0, name="X", thick=2.4):
    k = s / 100.0
    return shape(name, el("Rectangle", width=thick, height=s, rotation=0.785, name="a"),
                 el("Rectangle", width=thick, height=s, rotation=-0.785, name="b"), fill(color), x=x, y=y)


def needle(name="Needle", x=0, y=0, rot=0.0, scale=1.0):
    """A sewing needle pointing along +y with its eye at the top."""
    k = scale
    body = el("PointsPath",
              el("StraightVertex", x=0, y=46 * k),
              el("CubicMirroredVertex", x=3.2 * k, y=-20 * k, rotation=-1.57, distance=4 * k),
              el("CubicMirroredVertex", x=0, y=-46 * k, rotation=3.14159, distance=3 * k),
              el("CubicMirroredVertex", x=-3.2 * k, y=-20 * k, rotation=1.57, distance=4 * k),
              isClosed=True, isClockwise=True, name="Path")
    eye = shape("Eye", el("Ellipse", width=2.2 * k, height=9 * k, y=-34 * k, name="Path"), fill(IND_D))
    shine = shape("Shine", el("Rectangle", width=1 * k, height=50 * k, x=-0.8 * k, y=-4 * k, name="Path"), fill("88FFFFFF"))
    return node(name, eye, shine, shape("Steel", body, fill("FFB8C1CF"), stroke(IND_D, 0.8)), x=x, y=y, rotation=rot)
