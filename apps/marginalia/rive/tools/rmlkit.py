"""Tiny RML authoring kit used by build_rml.py.

RML is XML; this module provides an element tree with automatic ids, keyframed
animation helpers, state-machine helpers and a few vector-drawing helpers.
Nothing here is Rive-specific magic: every tag/attribute emitted is a real core
type/property (checked with `rive schema`).
"""
from __future__ import annotations

import math
from typing import Any

_next = [1]


def nid() -> str:
    v = _next[0]
    _next[0] += 1
    return f"0:{v}"


def fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


class N:
    """An RML element."""

    def __init__(self, _tag: str, *children: "N | None", **attrs: Any):
        self.tag = _tag
        self.attrs: dict[str, Any] = {}
        self.children: list[N] = []
        self.comment: str | None = attrs.pop("_comment", None)
        for k, v in attrs.items():
            if v is None:
                continue
            self.attrs[k.rstrip("_")] = v
        for c in children:
            self.add(c)

    def add(self, *cs: "N | None | list") -> "N":
        for c in cs:
            if c is None:
                continue
            if isinstance(c, (list, tuple)):
                self.add(*c)
            else:
                self.children.append(c)
        return self

    @property
    def id(self) -> str:
        if "id" not in self.attrs:
            self.attrs["id"] = nid()
        return self.attrs["id"]

    def ensure(self) -> "N":
        _ = self.id
        return self

    def write(self, out: list[str], ind: int = 0) -> None:
        pad = "    " * ind
        if self.comment:
            out.append(f"{pad}<!-- {self.comment} -->")
        attrs = dict(self.attrs)
        ida = attrs.pop("id", None)
        parts = [f'{k}="{esc(fmt(v))}"' for k, v in attrs.items()]
        if ida:
            parts.append(f'id="{ida}"')
        head = f"<{self.tag}" + ("" if not parts else " " + " ".join(parts))
        if not self.children:
            out.append(f"{pad}{head}/>")
        else:
            out.append(f"{pad}{head}>")
            for c in self.children:
                c.write(out, ind + 1)
            out.append(f"{pad}</{self.tag}>")


def doc(*roots: N) -> str:
    out = ['<Rive version="1" kind="fragment">']
    for r in roots:
        r.write(out, 1)
    out.append("</Rive>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- colours
def argb(hex6: str, a: float = 1.0) -> str:
    hex6 = hex6.lstrip("#")
    return f"{int(round(a * 255)):02X}{hex6.upper()}"


def solid(hex6: str, a: float = 1.0, **kw) -> N:
    return N("SolidColor", colorValue=argb(hex6, a), name=kw.pop("name", "Color"), **kw)


def fill(hex6: str | None = None, a: float = 1.0, paint: N | None = None, **kw) -> N:
    f = N("Fill", name=kw.pop("name", "Fill"), **kw)
    f.add(paint if paint is not None else solid(hex6 or "000000", a))
    return f


def stroke(hex6: str, w: float, a: float = 1.0, cap: str | None = None,
           join: str | None = None, effects: list | None = None, **kw) -> N:
    s = N("Stroke", thickness=w, cap=cap, join=join, name=kw.pop("name", "Stroke"), **kw)
    s.add(solid(hex6, a))
    if effects:
        s.add(effects)
    return s


def lin(x1, y1, x2, y2, stops: list[tuple[float, str, float]]) -> N:
    g = N("LinearGradient", startX=x1, startY=y1, endX=x2, endY=y2, name="Gradient")
    for pos, hx, a in stops:
        g.add(N("GradientStop", colorValue=argb(hx, a), position=pos, name="Stop"))
    return g


def rad(cx, cy, r, stops: list[tuple[float, str, float]]) -> N:
    g = N("RadialGradient", startX=cx, startY=cy, endX=cx + r, endY=cy, name="Gradient")
    for pos, hx, a in stops:
        g.add(N("GradientStop", colorValue=argb(hx, a), position=pos, name="Stop"))
    return g


# ---------------------------------------------------------------- geometry
def node(name: str, *children, x=0.0, y=0.0, **kw) -> N:
    return N("Node", *children, x=x, y=y, name=name, **kw)


def shape(name: str, *children, x=0.0, y=0.0, **kw) -> N:
    return N("Shape", *children, x=x, y=y, name=name, **kw)


def rect(w, h, x=0.0, y=0.0, r=0.0, ox=0.5, oy=0.5, rtl=None, rtr=None, rbl=None,
         rbr=None, **kw) -> N:
    a: dict[str, Any] = dict(width=w, height=h, x=x, y=y, originX=ox, originY=oy)
    if any(v is not None for v in (rtl, rtr, rbl, rbr)):
        a.update(linkCornerRadius=False, cornerRadiusTL=rtl or 0, cornerRadiusTR=rtr or 0,
                 cornerRadiusBL=rbl or 0, cornerRadiusBR=rbr or 0)
    elif r:
        a["cornerRadiusTL"] = r
    a["name"] = kw.pop("name", "Rect")
    a.update(kw)
    return N("Rectangle", **a)


def ellipse(w, h, x=0.0, y=0.0, ox=0.5, oy=0.5, **kw) -> N:
    return N("Ellipse", width=w, height=h, x=x, y=y, originX=ox, originY=oy,
             name=kw.pop("name", "Ellipse"), **kw)


def star(w, h, points=4, inner=0.3, x=0.0, y=0.0, **kw) -> N:
    return N("Star", width=w, height=h, points=points, innerRadius=inner, x=x, y=y,
             name=kw.pop("name", "Star"), **kw)


def _clockwise(pts) -> bool:
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i][0], pts[i][1]
        x2, y2 = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
        s += (x2 - x1) * (y2 + y1)
    # y down: positive sum with this formula means counter-clockwise visually
    return s < 0


def poly(pts, closed=True, radius=0.0, name="Path", **kw) -> N:
    p = N("PointsPath", isClosed=closed, isClockwise=_clockwise(pts) if closed else True,
          name=name, **kw)
    for pt in pts:
        r = pt[2] if len(pt) > 2 else radius
        p.add(N("StraightVertex", x=pt[0], y=pt[1], radius=r if r else None))
    return p


def smooth(pts, closed=True, tension=1.0, name="Path", sharp: set | None = None, **kw) -> N:
    """Catmull-Rom spline through pts as CubicMirroredVertex points."""
    sharp = sharp or set()
    n = len(pts)
    p = N("PointsPath", isClosed=closed, isClockwise=_clockwise(pts) if closed else True,
          name=name, **kw)
    for i, (x, y) in enumerate(pts):
        if i in sharp or (not closed and (i == 0 or i == n - 1)):
            p.add(N("StraightVertex", x=x, y=y))
            continue
        x0, y0 = pts[(i - 1) % n]
        x2, y2 = pts[(i + 1) % n]
        tx, ty = (x2 - x0) / 2 * tension, (y2 - y0) / 2 * tension
        d = math.hypot(tx, ty) / 3
        rot = math.atan2(ty, tx)
        p.add(N("CubicMirroredVertex", x=x, y=y, rotation=rot, distance=d))
    return p


def arch(w, h, x=0.0, y=0.0, **kw) -> N:
    """A round-topped arch whose origin is bottom-centre."""
    r = w / 2
    return rect(w, h, x=x, y=y, ox=0.5, oy=1.0, rtl=r, rtr=r, rbl=0.0001, rbr=0.0001, **kw)


# ---------------------------------------------------------------- data binding
class VM:
    def __init__(self, name: str):
        self.el = N("ViewModel", name=name).ensure()
        self.inst = N("ViewModelInstance", exports=True, name="Fixture").ensure()
        self.props: dict[str, N] = {}
        self.types: dict[str, str] = {}

    def prop(self, name: str, kind: str, default: Any = None, comment: str | None = None):
        tag = {"number": "ViewModelPropertyNumber", "string": "ViewModelPropertyString",
               "bool": "ViewModelPropertyBoolean", "color": "ViewModelPropertyColor",
               "trigger": "ViewModelPropertyTrigger"}[kind]
        p = N(tag, name=name, _comment=comment).ensure()
        self.el.add(p)
        self.props[name] = p
        self.types[name] = kind
        itag = {"number": "ViewModelInstanceNumber", "string": "ViewModelInstanceString",
                "bool": "ViewModelInstanceBoolean", "color": "ViewModelInstanceColor",
                "trigger": "ViewModelInstanceTrigger"}[kind]
        iv = N(itag, viewModelPropertyId=p.id)
        if default is not None and kind != "trigger":
            iv.attrs["propertyValue"] = default
        self.inst.add(iv)
        return p

    def path(self, name: str) -> str:
        return f"{self.el.id}-{self.props[name].id}"

    def finish(self) -> N:
        self.el.attrs["defaultInstanceId"] = self.inst.id
        self.el.add(self.inst)
        return self.el


V: VM | None = None  # set by build script


def bind(prop: str, key: int, conv: N | None = None, **kw) -> N:
    assert V is not None
    return N("DataBindContext", sourcePathIds=V.path(prop), propertyKey=key,
             converterId=conv.id if conv is not None else None, **kw)


KEY = dict(x=13, y=14, rotation=15, scaleX=16, scaleY=17, opacity=18, text=268,
           color=37, width=20, height=21, isPaused=895, label=983, customNumber=243,
           customString=246)
BKEY = dict(number=636, bool=634, string=635, trigger=686, color=638)
BTAG = dict(number="BindablePropertyNumber", bool="BindablePropertyBoolean",
            string="BindablePropertyString", trigger="BindablePropertyTrigger",
            color="BindablePropertyColor")


def _cmp(prop: str) -> N:
    assert V is not None
    kind = V.types[prop]
    return N("TransitionPropertyViewModelComparator",
             N(BTAG[kind], N("DataBindContext", sourcePathIds=V.path(prop),
                             propertyKey=BKEY[kind])))


def cnum(prop: str, op: str, value: float) -> N:
    return N("TransitionViewModelCondition", _cmp(prop),
             N("TransitionValueNumberComparator", value=value), opValue=op)


def cbool(prop: str, value: bool) -> N:
    return N("TransitionViewModelCondition", _cmp(prop),
             N("TransitionValueBooleanComparator", value=value), opValue="equal")


def ctrig(prop: str) -> N:
    return N("TransitionViewModelCondition", _cmp(prop), N("TransitionValueTriggerComparator"))


def write(prop: str, value: Any) -> N:
    """ListenerViewModelChange writing a literal (or firing a trigger)."""
    assert V is not None
    kind = V.types[prop]
    if kind == "trigger":
        value = 1
    return N("ListenerViewModelChange",
             N(BTAG[kind], N("DataBindContext", sourcePathIds=V.path(prop),
                             propertyKey=BKEY[kind], direction=True), propertyValue=value))


# ---------------------------------------------------------------- animation
EASE = {
    "out": (0.16, 1.0, 0.3, 1.0),        # quick settle (paper landing)
    "inout": (0.65, 0.0, 0.35, 1.0),     # page turn
    "in": (0.55, 0.0, 0.9, 0.4),
    "soft": (0.33, 0.0, 0.2, 1.0),
    "back": (0.34, 1.45, 0.64, 1.0),     # overshoot (follow-through)
    "antic": (0.6, -0.35, 0.7, 0.2),     # anticipation dip
    "sine": (0.37, 0.0, 0.63, 1.0),
}


def F(ms: float) -> int:
    return int(round(ms * 0.06))


class Anim:
    def __init__(self, name: str, ms: float, loop: str | None = None):
        self.name = name
        self.dur = max(1, F(ms))
        self.loop = loop
        self.keys: dict[tuple[str, str], list] = {}
        self.el = N("LinearAnimation", name=name).ensure()

    def k(self, obj: N, prop: str, ms: float, value: Any, ease: Any = "linear",
          kind: str = "double") -> "Anim":
        fr = min(self.dur, max(0, F(ms)))
        lst = self.keys.setdefault((obj.id, prop), [])
        lst = [e for e in lst if e[0] != fr]
        lst.append((fr, value, ease, kind))
        lst.sort(key=lambda e: e[0])
        self.keys[(obj.id, prop)] = lst
        return self

    def tw(self, obj: N, prop: str, t0: float, t1: float, v0: Any, v1: Any,
           ease: Any = "out", kind: str = "double", hold_before: bool = True) -> "Anim":
        """Tween prop from v0 at t0 to v1 at t1 (ms). Holds v0 from 0 if hold_before."""
        if hold_before and t0 > 0:
            self.k(obj, prop, 0, v0, "hold" if kind == "double" else "hold", kind)
        self.k(obj, prop, t0, v0, ease, kind)
        self.k(obj, prop, t1, v1, "linear", kind)
        return self

    def set(self, obj: N, prop: str, value: Any, kind: str = "double", ms: float = 0) -> "Anim":
        return self.k(obj, prop, ms, value, "hold", kind)

    def build(self) -> N:
        el = self.el
        el.attrs.update(fps=60, duration=self.dur)
        if self.loop:
            el.attrs["loopValue"] = self.loop
        by_obj: dict[str, list] = {}
        for (oid, prop), frames in self.keys.items():
            by_obj.setdefault(oid, []).append((prop, frames))
        for oid, props in by_obj.items():
            ko = N("KeyedObject", objectId=oid)
            for prop, frames in props:
                kp = N("KeyedProperty", property=prop)
                for fr, val, ease, kind in frames:
                    kp.add(_kf(fr, val, ease, kind))
                ko.add(kp)
            el.add(ko)
        return el


def _kf(fr: int, val: Any, ease: Any, kind: str) -> N:
    tag = {"double": "KeyFrameDouble", "color": "KeyFrameColor", "bool": "KeyFrameBool",
           "id": "KeyFrameId", "uint": "KeyFrameUint"}[kind]
    if kind != "double":
        return N(tag, value=val, frame=fr, interpolationType="hold" if kind != "color" else
                 ("hold" if ease == "hold" else "linear"))
    if ease == "hold":
        return N(tag, value=val, frame=fr, interpolationType="hold")
    if ease == "linear":
        return N(tag, value=val, frame=fr, interpolationType="linear")
    if isinstance(ease, tuple) and ease and ease[0] == "elastic":
        return N(tag, N("ElasticInterpolator", easingValue=1, amplitude=ease[1], period=ease[2]),
                 value=val, frame=fr, interpolationType="elastic")
    c = EASE[ease] if isinstance(ease, str) else ease
    return N(tag, N("CubicEaseInterpolator", x1=c[0], y1=c[1], x2=c[2], y2=c[3]),
             value=val, frame=fr, interpolationType="cubic")


# ---------------------------------------------------------------- state machines
class Layer:
    def __init__(self, name: str):
        self.el = N("StateMachineLayer", name=name).ensure()
        self.any = N("AnyState", x=-200, y=-200)
        self.exit = N("ExitState", x=-200, y=200)
        self.entry = N("EntryState", x=-200, y=0)
        self.states: list[N] = []
        self._col = 0

    def state(self, anim: Anim | N, x: float | None = None, y: float | None = None,
              **kw) -> N:
        aid = anim.el.id if isinstance(anim, Anim) else anim.id
        if x is None:
            x = 100 + (len(self.states) % 6) * 220
            y = -300 + (len(self.states) // 6) * 160 + (len(self.states) % 2) * 40
        s = N("AnimationState", animationId=aid, x=x, y=y, **kw).ensure()
        self.states.append(s)
        return s

    def start(self, s: N) -> None:
        self.entry.add(N("StateTransition", stateToId=s.id))

    def build(self) -> N:
        self.el.add(self.any, self.exit, self.entry, *self.states)
        return self.el


def trans(frm: N, to: N, *conds: N, ms: int = 0, ease: Any = None, exit_pct: float | None = None,
          **kw) -> N:
    t = N("StateTransition", stateToId=to.id, duration=ms or None, **kw)
    if exit_pct is not None:
        t.attrs.update(enableExitTime=True, exitTimeIsPercetange=True, exitTime=exit_pct)
    if ease is not None and ms:
        c = EASE[ease] if isinstance(ease, str) else ease
        t.attrs["interpolationType"] = "cubic"
        t.add(N("CubicEaseInterpolator", x1=c[0], y1=c[1], x2=c[2], y2=c[3]))
    t.add(*conds)
    frm.add(t)
    return t


# ---------------------------------------------------------------- text
FONT_IDS: dict[str, str] = {}
WGHT = 2003265652


def tstyle(font: str, size: float, color: str, weight: float | None = None, ls: float = 0,
           lh: float | None = None, alpha: float = 1.0, name: str = "Style", family: str = "",
           style_name: str = "", color_bind: N | None = None, lining: bool = False) -> N:
    sc = solid(color, alpha)
    if color_bind is not None:
        sc.add(color_bind)
    st = N("TextStylePaint", fontSize=size, fontAssetId=FONT_IDS[font], familyName=family,
           styleName=style_name, letterSpacing=ls or None, lineHeight=lh, name=name).ensure()
    st.add(N("Fill", sc, name="Fill"))
    if lining:
        st.add(N("TextStyleFeature", tag=1819178349, featureValue=1, name="lnum"))
    if weight is not None:
        st.add(N("TextStyleAxis", tag=WGHT, axisValue=weight, name="Weight"))
    return st


def text(name: str, x: float, y: float, runs: list[tuple[N, str, N | None]],
         w: float | None = None, h: float | None = None, align: str = "left",
         ox: float = 0.0, oy: float = 0.0, sizing: str | None = None,
         overflow: str | None = None, wrap: str | None = None, valign: str | None = None,
         styles: list[N] | None = None, **kw) -> N:
    if sizing is None:
        sizing = "autoWidth" if w is None else ("autoHeight" if h is None else "fixed")
    t = N("Text", x=x, y=y, width=w, height=h, sizingValue=sizing, alignValue=align,
          originX=ox, originY=oy, overflowValue=overflow, wrapValue=wrap,
          verticalAlignValue=valign, name=name, **kw).ensure()
    seen = []
    for st, _, _ in runs:
        if st not in seen:
            seen.append(st)
    for st in (styles or []):
        if st not in seen:
            seen.append(st)
    t.add(seen)
    for st, literal, b in runs:
        r = N("TextValueRun", styleId=st.id, text=literal, name="Run")
        if b is not None:
            r.add(b)
        t.add(r)
    return t
