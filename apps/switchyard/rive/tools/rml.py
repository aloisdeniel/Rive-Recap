"""Tiny RML authoring helpers used by gen.py.

Everything here produces plain RML elements; the generator is a convenience
for keeping ~200 state transitions and ~10 scene timelines consistent. The
emitted `scene.rml` is the editable source of truth for the Rive project.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

_next = [1000]


def nid() -> str:
    _next[0] += 1
    return f"0:{_next[0]}"


def fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "", "-") else s
    return str(v)


class E:
    """One RML element. `id` is assigned lazily the first time it is read."""

    def __init__(self, _tag, *children, **attrs):
        self.tag = _tag
        self.children = [c for c in children if c is not None]
        self._id = attrs.pop("id", None)
        self.attrs = {}
        for k, v in attrs.items():
            if v is None:
                continue
            self.attrs[k.rstrip("_")] = v

    @property
    def id(self) -> str:
        if self._id is None:
            self._id = nid()
        return self._id

    def add(self, *cs):
        self.children.extend(c for c in cs if c is not None)
        return self

    def get(self, k, default=None):
        return self.attrs.get(k, default)

    def xml(self, ind=0) -> str:
        pad = "  " * ind
        a = "".join(f' {k}="{escape(fmt(v), {chr(34): "&quot;"})}"' for k, v in self.attrs.items())
        if self._id:
            a += f' id="{self._id}"'
        if not self.children:
            return f"{pad}<{self.tag}{a}/>"
        inner = "\n".join(c.xml(ind + 1) if isinstance(c, E) else f"{pad}  {c}" for c in self.children)
        return f"{pad}<{self.tag}{a}>\n{inner}\n{pad}</{self.tag}>"


# ---------------------------------------------------------------- palette
RED = "FFF44533"
BLUE = "FF1B4ED0"
YEL = "FFFFD64B"
WHITE = "FFF5F2E9"
BLACK = "FF171B20"
DEEP = "FF163FA8"     # darker transit blue for wave bands
SKY = "FF4F7BEA"      # lighter transit blue
GREY = "FF2A3038"     # board tile
INK60 = "99171B20"
CLEAR = "00FFFFFF"

# ---------------------------------------------------------------- easing
EO = (0.16, 1.0, 0.3, 1.0)        # decisive ease-out (arrivals)
EIO = (0.65, 0.0, 0.35, 1.0)      # scheduled in-out (departures, sweeps)
EI = (0.55, 0.0, 0.9, 0.45)       # ease-in (collapse)
POP = (0.34, 1.45, 0.64, 1.0)     # overshoot (stations snapping in)
SOFT = (0.42, 0.0, 0.58, 1.0)


def solid(c, **kw):
    return E("SolidColor", colorValue=c, name=kw.get("name", "Color"), id=kw.get("id"))


def fill(c, name="Fill"):
    return E("Fill", solid(c), name=name)


def stroke(c, t, name="Stroke", cap="round", join="round", *extra):
    return E("Stroke", solid(c), *extra, thickness=t, cap=cap, join=join, name=name)


def node(name, *children, **attrs):
    return E("Node", *children, name=name, **attrs)


def rect(x, y, w, h, color=None, r=0, name="Rect", line=None, lw=0, ox=0.0, oy=0.0, **attrs):
    s = E("Shape", E("Rectangle", width=w, height=h, originX=ox, originY=oy,
                     cornerRadiusTL=r if r else None, name="Path"),
          x=x, y=y, name=name, **attrs)
    if color:
        s.add(fill(color))
    if line:
        s.add(stroke(line, lw))
    return s


def circle(cx, cy, d, color=None, name="Circle", line=None, lw=0, **attrs):
    s = E("Shape", E("Ellipse", width=d, height=d, name="Path"), x=cx, y=cy, name=name, **attrs)
    if color:
        s.add(fill(color))
    if line:
        s.add(stroke(line, lw))
    return s


def path_shape(pts, color=None, name="Poly", line=None, lw=0, closed=True, radius=0, x=0, y=0, **attrs):
    verts = [E("StraightVertex", x=float(p[0]), y=float(p[1]), radius=(p[2] if len(p) > 2 else radius) or None)
             for p in pts]
    s = E("Shape", E("PointsPath", *verts, isClosed=closed, isClockwise=_clockwise(pts), name="Path"),
          x=x, y=y, name=name, **attrs)
    if color:
        s.add(fill(color))
    if line:
        s.add(stroke(line, lw))
    return s


def _clockwise(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i][0], pts[i][1]
        x2, y2 = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
        a += (x2 - x1) * (y2 + y1)
    # y grows downward: a negative shoelace sum here means clockwise on screen
    return a < 0


def route(pts, color, t=14, name="Route", radius=26, trim=True, dash=None, cap="round"):
    """An open schematic route line. Returns (shape, trim_or_None)."""
    verts = [E("StraightVertex", x=float(p[0]), y=float(p[1]), radius=radius if 0 < i < len(pts) - 1 else None)
             for i, p in enumerate(pts)]
    tp = E("TrimPath", start=0.0, end=1.0, modeValue="sequential", name="Draw") if trim else None
    extra = []
    if dash:
        extra.append(E("DashPath", *[E("Dash", length=d, name="D") for d in dash], name="Dashes"))
    st = E("Stroke", solid(color), *( [tp] if tp else []), *extra, thickness=t, cap=cap, join="round", name="Stroke")
    s = E("Shape", E("PointsPath", *verts, isClosed=False, name="Path"), st, name=name)
    return s, tp


def polyline_length(pts):
    return sum(math.dist(pts[i][:2], pts[i + 1][:2]) for i in range(len(pts) - 1))


def point_along(pts, f):
    """Point at fraction f (0..1) along a polyline (corners treated as sharp)."""
    total = polyline_length(pts)
    target = max(0.0, min(1.0, f)) * total
    acc = 0.0
    for i in range(len(pts) - 1):
        seg = math.dist(pts[i][:2], pts[i + 1][:2])
        if acc + seg >= target or i == len(pts) - 2:
            u = 0 if seg == 0 else (target - acc) / seg
            u = max(0.0, min(1.0, u))
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)
        acc += seg
    return pts[-1][:2]


def vertex_fractions(pts):
    total = polyline_length(pts)
    out, acc = [0.0], 0.0
    for i in range(len(pts) - 1):
        acc += math.dist(pts[i][:2], pts[i + 1][:2])
        out.append(acc / total)
    return out


# ---------------------------------------------------------------- animation
class Anim:
    def __init__(self, name, dur, loop="oneShot"):
        self.name, self.dur, self.loop = name, int(dur), loop
        self.tracks = {}          # (obj, prop) -> [(frame, value, ease)]
        self.order = []
        self.el = None

    def key(self, obj, prop, *frames):
        k = (obj, prop)
        if k not in self.tracks:
            self.tracks[k] = []
            self.order.append(k)
        self.tracks[k].extend(frames)
        return self

    def hold(self, obj, prop, value, frame=0):
        return self.key(obj, prop, (frame, value, "hold"))

    def has(self, obj, prop):
        return (obj, prop) in self.tracks

    def build(self):
        if self.el:
            return self.el
        el = E("LinearAnimation", duration=self.dur, loopValue=self.loop if self.loop != "oneShot" else None,
               name=self.name)
        by_obj = {}
        for (obj, prop) in self.order:
            by_obj.setdefault(obj, []).append(prop)
        for obj, props in by_obj.items():
            ko = E("KeyedObject", objectId=obj.id)
            for prop in props:
                kp = E("KeyedProperty", property=prop)
                frames = sorted(self.tracks[(obj, prop)], key=lambda f: f[0])
                seen = {}
                for f in frames:
                    seen[f[0]] = f          # last write wins per frame
                for fr, val, ease in sorted(seen.values(), key=lambda f: f[0]):
                    kp.add(keyframe(fr, val, ease))
                ko.add(kp)
            el.add(ko)
        self.el = el
        return el


def keyframe(frame, value, ease):
    if isinstance(value, str):
        return E("KeyFrameColor", value=value, frame=int(frame),
                 interpolationType="hold" if ease == "hold" else "linear")
    if isinstance(value, bool):
        return E("KeyFrameBool", value=value, frame=int(frame), interpolationType="hold")
    kw = dict(value=float(value), frame=int(frame))
    if ease == "hold":
        return E("KeyFrameDouble", interpolationType="hold", **kw)
    if ease in (None, "lin"):
        return E("KeyFrameDouble", interpolationType="linear", **kw)
    if isinstance(ease, tuple) and ease[0] == "el":
        return E("KeyFrameDouble", E("ElasticInterpolator", easingValue=1, amplitude=ease[1], period=ease[2]),
                 interpolationType="elastic", **kw)
    x1, y1, x2, y2 = ease
    return E("KeyFrameDouble", E("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2),
             interpolationType="cubic", **kw)


DEFAULTS = {"x": 0.0, "y": 0.0, "opacity": 1.0, "scaleX": 1.0, "scaleY": 1.0, "rotation": 0.0,
            "start": 0.0, "end": 1.0, "offset": 0.0, "strength": 1.0}


def rest_value(obj, prop):
    if prop in obj.attrs:
        return obj.attrs[prop]
    if prop in DEFAULTS:
        return DEFAULTS[prop]
    raise KeyError(f"no rest value for {obj.tag}.{prop} ({obj.attrs.get('name')})")
