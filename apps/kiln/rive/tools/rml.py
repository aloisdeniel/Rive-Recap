"""Tiny RML authoring helpers used by gen_kiln.py.

Everything here emits plain RML elements; nothing is Rive-runtime specific
beyond the element and attribute names checked with `rive schema`.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

# --------------------------------------------------------------------------
# ids


class Ids:
    def __init__(self, start: int = 100):
        self.n = start

    def __call__(self) -> str:
        self.n += 1
        return f"0:{self.n}"


ID = Ids()


# --------------------------------------------------------------------------
# elements


class E:

    def __init__(self, tag: str, attrs: dict | None = None, *children, text: str | None = None):
        self.tag = tag
        self.attrs = {k: v for k, v in (attrs or {}).items() if v is not None}
        self.children = [c for c in children if c is not None]
        self.text = text

    @property
    def id(self) -> str:
        if "id" not in self.attrs:
            self.attrs["id"] = ID()
        return self.attrs["id"]

    def add(self, *children):
        for c in children:
            if c is None:
                continue
            if isinstance(c, (list, tuple)):
                self.add(*c)
            else:
                self.children.append(c)
        return self

    def render(self, indent: int = 0) -> str:
        pad = "  " * indent
        parts = []
        for k, v in self.attrs.items():
            if isinstance(v, bool):
                v = "true" if v else "false"
            elif isinstance(v, float):
                v = fmt(v)
            parts.append(f"{k}={quoteattr(str(v))}")
        a = (" " + " ".join(parts)) if parts else ""
        if not self.children and self.text is None:
            return f"{pad}<{self.tag}{a}/>"
        out = [f"{pad}<{self.tag}{a}>"]
        if self.text is not None:
            out.append(self.text)
        for c in self.children:
            out.append(c.render(indent + 1))
        out.append(f"{pad}</{self.tag}>")
        return "\n".join(out)


def fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def e(tag, attrs=None, *children):
    return E(tag, attrs, *children)


# --------------------------------------------------------------------------
# colours: ARGB hex, no '#'


def argb(hex6: str, alpha: float = 1.0) -> str:
    h = hex6.lstrip("#").upper()
    if len(h) == 8:
        return h
    return f"{int(round(alpha * 255)):02X}{h}"


def mix(c1: str, c2: str, t: float) -> str:
    a = argb(c1)
    b = argb(c2)
    va = [int(a[i:i + 2], 16) for i in range(0, 8, 2)]
    vb = [int(b[i:i + 2], 16) for i in range(0, 8, 2)]
    return "".join(f"{int(round(x + (y - x) * t)):02X}" for x, y in zip(va, vb))


# --------------------------------------------------------------------------
# paint / geometry


def solid(color, name="Color", alpha=1.0):
    return E("SolidColor", {"colorValue": argb(color, alpha), "name": name})


def fill(color, name="Fill", alpha=1.0, feather=None, rule=None):
    f = E("Fill", {"name": name, "fillRule": rule})
    c = solid(color, alpha=alpha)
    f.add(c)
    if feather is not None:
        f.attrs["fillRule"] = "clockwise"
        f.add(E("Feather", {"strength": float(feather), "name": "Feather"}))
    f.color = c  # type: ignore[attr-defined]
    return f


class _F(E):
    pass


def paint_color(p: E) -> E:
    """the SolidColor inside a Fill/Stroke"""
    for c in p.children:
        if c.tag == "SolidColor":
            return c
    raise ValueError("no SolidColor")


def stroke(color, thick=2.0, name="Stroke", alpha=1.0, cap="round", join="round", trim=None, dash=None, feather=None):
    s = E("Stroke", {"thickness": float(thick), "cap": cap, "join": join, "name": name})
    s.add(solid(color, alpha=alpha))
    if trim is not None:
        st, en = trim
        s.add(E("TrimPath", {"start": float(st), "end": float(en), "name": "Trim"}))
    if dash is not None:
        dp = E("DashPath", {"name": "Dashes"})
        on = True
        for ln in dash:
            dp.add(E("Dash", {"length": float(ln), "name": "On" if on else "Off"}))
            on = not on
        s.add(dp)
    if feather is not None:
        s.add(E("Feather", {"strength": float(feather), "name": "Feather"}))
    return s


def child(el: E, tag: str) -> E:
    for c in el.children:
        if c.tag == tag:
            return c
    raise ValueError(f"{el.tag} has no {tag}")


def rect(w, h, r=0.0, ox=0.5, oy=0.5, name="Path"):
    return E("Rectangle", {"width": float(w), "height": float(h), "cornerRadiusTL": float(r) if r else None,
                           "originX": float(ox), "originY": float(oy), "name": name})


def ellipse(w, h, ox=0.5, oy=0.5, name="Path"):
    return E("Ellipse", {"width": float(w), "height": float(h), "originX": float(ox), "originY": float(oy), "name": name})


def shape(name, x=0.0, y=0.0, *children, **kw):
    a = {"x": float(x), "y": float(y), "name": name}
    a.update(kw)
    return E("Shape", a, *children)


def node(name, x=0.0, y=0.0, *children, **kw):
    a = {"x": float(x), "y": float(y), "name": name}
    a.update(kw)
    return E("Node", a, *children)


# --------------------------------------------------------------------------
# paths


def poly(points, closed=True, radius=0.0, name="Path", clockwise=True):
    p = E("PointsPath", {"isClosed": closed, "isClockwise": clockwise, "name": name})
    for (x, y) in points:
        p.add(E("StraightVertex", {"x": float(x), "y": float(y), "radius": float(radius) if radius else None}))
    return p


def smooth_vertices(points, closed=True, tension=0.17, sharp=None):
    """Catmull-Rom style mirrored vertices: (x, y, rotation, distance)."""
    sharp = sharp or {}
    n = len(points)
    out = []
    for i, (x, y) in enumerate(points):
        if closed:
            px, py = points[(i - 1) % n]
            nx, ny = points[(i + 1) % n]
        else:
            px, py = points[max(i - 1, 0)]
            nx, ny = points[min(i + 1, n - 1)]
        dx, dy = nx - px, ny - py
        rot = math.atan2(dy, dx)
        dist = math.hypot(dx, dy) * tension
        if i in sharp:
            dist = sharp[i]
        out.append((x, y, rot, dist))
    return out


def unwrap(base: float, ang: float) -> float:
    while ang - base > math.pi:
        ang -= 2 * math.pi
    while ang - base < -math.pi:
        ang += 2 * math.pi
    return ang


def smooth_path(verts, closed=True, name="Path", clockwise=False):
    """verts from smooth_vertices; returns (PointsPath, [vertex elements])"""
    p = E("PointsPath", {"isClosed": closed, "isClockwise": clockwise, "name": name})
    vs = []
    for (x, y, r, d) in verts:
        v = E("CubicMirroredVertex", {"x": float(x), "y": float(y), "rotation": float(r), "distance": float(d)})
        v.id  # noqa: B018 - force an id, they get keyed
        p.add(v)
        vs.append(v)
    return p, vs


# --------------------------------------------------------------------------
# text

WGHT = 2003265652


def text_style(font, size, color, family, style, weight=None, line_height=None, spacing=None, name="Style"):
    st = E("TextStylePaint", {"fontSize": float(size), "fontAssetId": font, "familyName": family, "styleName": style,
                              "lineHeight": float(line_height) if line_height else None,
                              "letterSpacing": float(spacing) if spacing else None, "name": name})
    st.id  # noqa: B018
    st.add(E("Fill", {"name": "Fill"}, solid(color)))
    if weight is not None:
        st.add(E("TextStyleAxis", {"tag": WGHT, "axisValue": float(weight), "name": "Weight"}))
    return st


def style_color(st: E) -> E:
    return paint_color(child(st, "Fill"))


# --------------------------------------------------------------------------
# data binding


def bind(path: str, key: int, converter: str | None = None, **kw):
    a = {"sourcePathIds": path, "propertyKey": key, "converterId": converter}
    a.update(kw)
    return E("DataBindContext", a)


# --------------------------------------------------------------------------
# easing

EASES = {
    "out": (0.16, 1.0, 0.3, 1.0),        # long, soft deceleration
    "inout": (0.65, 0.0, 0.35, 1.0),
    "in": (0.55, 0.0, 0.9, 0.45),        # anticipation / gather
    "back": (0.34, 1.45, 0.62, 1.0),     # clay overshoot
    "settle": (0.25, 0.9, 0.25, 1.0),
    "heavy": (0.7, 0.0, 0.2, 1.0),       # weighted, slow start
    "soft": (0.4, 0.0, 0.2, 1.0),
}


def keyframe(kind: str, frame: int, value, ease: str | None):
    a = {"frame": int(frame)}
    if kind == "color":
        tag = "KeyFrameColor"
        a["value"] = argb(value)
    elif kind == "bool":
        tag = "KeyFrameBool"
        a["value"] = bool(value)
    else:
        tag = "KeyFrameDouble"
        a["value"] = float(value)
    k = E(tag, a)
    if ease is None or ease == "hold":
        k.attrs["interpolationType"] = "hold"
    elif ease == "lin":
        k.attrs["interpolationType"] = "linear"
    else:
        k.attrs["interpolationType"] = "cubic"
        x1, y1, x2, y2 = EASES[ease]
        k.add(E("CubicEaseInterpolator", {"x1": x1, "y1": y1, "x2": x2, "y2": y2}))
    return k


COLOR_PROPS = {"colorValue"}


class Anim:
    """A LinearAnimation under construction.

    tracks: {(object_id, prop): [(frame, value, ease)]}
    """

    def __init__(self, name: str, frames: int, loop: str = "oneShot", exempt: bool = False):
        self.name = name
        self.frames = int(frames)
        self.loop = loop
        self.tracks: dict[tuple[str, str], list] = {}
        self.exempt = exempt  # no union fill (a 'freeze' state keys nothing)
        self.el = E("LinearAnimation", {"name": name})
        self.id = self.el.id

    def k(self, obj, prop: str, *kfs):
        oid = obj if isinstance(obj, str) else obj.id
        lst = self.tracks.setdefault((oid, prop), [])
        for kf in kfs:
            if len(kf) == 2:
                kf = (kf[0], kf[1], "out")
            lst.append(kf)
        return self

    def hold(self, obj, prop, value):
        return self.k(obj, prop, (0, value, "hold"))

    def render(self) -> E:
        a = self.el
        a.attrs["duration"] = self.frames
        if self.loop != "oneShot":
            a.attrs["loopValue"] = self.loop
        a.children = []
        by_obj: dict[str, list] = {}
        for (oid, prop), kfs in self.tracks.items():
            by_obj.setdefault(oid, []).append((prop, kfs))
        for oid, props in by_obj.items():
            ko = E("KeyedObject", {"objectId": oid})
            for prop, kfs in props:
                kind = "color" if prop in COLOR_PROPS else ("bool" if prop in ("isVisible",) else "double")
                kp = E("KeyedProperty", {"property": prop})
                seen = {}
                for (f, v, ease) in sorted(kfs, key=lambda t: t[0]):
                    seen[int(f)] = (f, v, ease)
                for f, v, ease in seen.values():
                    kp.add(keyframe(kind, f, v, ease))
                ko.add(kp)
            a.add(ko)
        return a
