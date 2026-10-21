"""Tiny RML authoring library used by gen.py.

Every element gets an explicit, deterministic id so regenerating the project
produces identical markup (and `rive` has nothing to write back).
"""
from xml.sax.saxutils import quoteattr
import math
import random

_ID = [100]


def nid():
    _ID[0] += 1
    return f"0:{_ID[0]}"


def reset_ids(start=100):
    _ID[0] = start


# Element types that must not carry an `id` attribute (none known so far).
NO_ID = {"Rive"}


class E:

    def __init__(self, tag, kids=None, **attrs):
        self.tag = tag
        self.a = {}
        for k, v in attrs.items():
            if v is None:
                continue
            k = k.rstrip("_")
            self.a[k] = v
        if "id" in self.a:
            self.id = self.a.pop("id")
        elif tag in NO_ID:
            self.id = None
        else:
            self.id = nid()
        self.kids = list(kids or [])

    def add(self, *kids):
        for k in kids:
            if k is None:
                continue
            if isinstance(k, (list, tuple)):
                self.add(*k)
            else:
                self.kids.append(k)
        return self

    def xml(self, ind=0, out=None):
        top = out is None
        if top:
            out = []
        pad = "  " * ind
        parts = [self.tag]
        for k, v in self.a.items():
            parts.append(f"{k}={quoteattr(fmt(v))}")
        if self.id:
            parts.append(f'id="{self.id}"')
        if self.kids:
            out.append(pad + "<" + " ".join(parts) + ">")
            for k in self.kids:
                k.xml(ind + 1, out)
            out.append(pad + f"</{self.tag}>")
        else:
            out.append(pad + "<" + " ".join(parts) + "/>")
        if top:
            return "\n".join(out)


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


# ---------------------------------------------------------------- palette
CHALK = "FFF1EEE7"
COAL = "FF20221F"
ACID = "FFDCFF3F"
COBALT = "FF385DF4"
CONCRETE = "FFB9B5AC"
CONCRETE_D = "FF8E8A82"
CHALK_D = "FFD9D5CC"
COAL_L = "FF3A3C38"

SHADES = {
    COBALT: ("FF2440B8", "FF6F8BFF"),
    ACID: ("FF9DB81E", "FFF1FF9C"),
    COAL: ("FF0B0C0B", "FF4A4D47"),
    CHALK: ("FFC9C4B8", "FFFFFFFF"),
    CONCRETE: ("FF8E8A82", "FFD6D2C9"),
}


def solid(c, **kw):
    return E("SolidColor", colorValue=c, name=kw.get("name", "Color"), id=kw.get("id"))


def fill(c, name="Fill", **kw):
    f = E("Fill", name=name, fillRule=kw.get("rule"))
    sc = solid(c, id=kw.get("cid"))
    f.add(sc)
    if kw.get("feather"):
        f.add(E("Feather", strength=kw["feather"], name="Feather"))
    return f


def stroke(c, th, name="Stroke", cap="butt", join="round", effects=None, cid=None):
    s = E("Stroke", thickness=th, cap=cap, join=join, name=name)
    s.add(solid(c, id=cid))
    if effects:
        s.add(effects)
    return s


def poly(pts, closed=True, radius=None, cw=True, name="Path"):
    p = E("PointsPath", isClosed=closed, isClockwise=cw, name=name)
    for (x, y) in pts:
        p.add(E("StraightVertex", x=round(x, 2), y=round(y, 2), radius=radius))
    return p


def shape(name, geoms, paints, x=None, y=None, **kw):
    s = E("Shape", x=x, y=y, name=name, rotation=kw.get("rotation"), opacity=kw.get("opacity"),
          scaleX=kw.get("scaleX"), scaleY=kw.get("scaleY"), id=kw.get("id"))
    s.add(geoms)
    s.add(paints)
    return s


def node(name, kids=(), x=None, y=None, **kw):
    n = E("Node", x=x, y=y, name=name, rotation=kw.get("rotation"), opacity=kw.get("opacity"),
          scaleX=kw.get("scaleX"), scaleY=kw.get("scaleY"), id=kw.get("id"))
    n.add(list(kids))
    return n


def ellipse(w, h=None, x=None, y=None, name="Path"):
    return E("Ellipse", width=w, height=h if h is not None else w, x=x, y=y, name=name)


def rect(w, h, x=None, y=None, ox=None, oy=None, r=None, name="Path", rot=None):
    return E("Rectangle", width=w, height=h, x=x, y=y, originX=ox, originY=oy,
             cornerRadiusTL=r, name=name, rotation=rot)


def rotate_pts(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def bind(path, key, conv=None, direction=None, id=None):
    return E("DataBindContext", sourcePathIds=path, propertyKey=key, converterId=conv,
             direction=direction, id=id)


# ---------------------------------------------------------------- animation
EASES = {
    "linear": None,
    "out": (0.16, 1.0, 0.3, 1.0),
    "outq": (0.25, 1.0, 0.5, 1.0),
    "in": (0.7, 0.0, 0.84, 0.0),
    "inq": (0.5, 0.0, 0.75, 0.0),
    "inout": (0.65, 0.0, 0.35, 1.0),
    "soft": (0.4, 0.0, 0.2, 1.0),
    "back": (0.34, 1.56, 0.64, 1.0),
    "snap": (0.2, 2.1, 0.45, 1.0),
    "punch": (0.12, 2.6, 0.4, 1.0),
}


class Anim:
    def __init__(self, name, dur, loop=None, fps=60):
        self.name = name
        self.dur = dur
        self.loop = loop
        self.fps = fps
        self.id = nid()
        # (objId, prop) -> {frame: (value, ease, kind)}
        self.keys = {}
        self.order = []

    def k(self, obj, prop, frame, value, ease="hold", kind="double"):
        if isinstance(obj, E):
            obj = obj.id
        key = (obj, prop)
        if key not in self.keys:
            self.keys[key] = {}
            self.order.append(key)
        frame = int(round(max(0, frame)))
        prev = self.keys[key].get(frame)
        if prev is not None and ease == "hold" and prev[1] != "hold":
            ease = prev[1]
        self.keys[key][frame] = (value, ease, kind)
        return self

    def tw(self, obj, prop, f0, f1, v0, v1, ease="out", kind="double"):
        """Tween v0->v1 between f0 and f1 (value held before f0)."""
        if isinstance(obj, E):
            obj = obj.id
        self.k(obj, prop, f0, v0, ease, kind)
        cur = self.keys[(obj, prop)].get(int(round(f1)))
        self.k(obj, prop, f1, v1, cur[1] if cur else "hold", kind)
        return self

    def hold(self, obj, prop, value, frame=0, kind="double"):
        return self.k(obj, prop, frame, value, "hold", kind)

    def final_values(self):
        out = {}
        for key in self.order:
            fr = self.keys[key]
            last = max(fr)
            out[key] = (fr[last][0], fr[last][2])
        return out

    def value_at(self, key, frame):
        fr = self.keys.get(key)
        if not fr:
            return None
        frames = sorted(fr)
        prev = frames[0]
        for f in frames:
            if f <= frame:
                prev = f
        return fr[prev][0]

    def el(self):
        a = E("LinearAnimation", duration=self.dur, fps=self.fps, loopValue=self.loop,
              name=self.name, id=self.id)
        by_obj = {}
        for (obj, prop) in self.order:
            by_obj.setdefault(obj, []).append(prop)
        for obj, props in by_obj.items():
            ko = E("KeyedObject", objectId=obj)
            for prop in props:
                kp = E("KeyedProperty", **({"propertyKey": prop} if isinstance(prop, int) else {"property": prop}))
                for f in sorted(self.keys[(obj, prop)]):
                    v, ease, kind = self.keys[(obj, prop)][f]
                    tag = {"double": "KeyFrameDouble", "color": "KeyFrameColor", "bool": "KeyFrameBool",
                           "id": "KeyFrameId", "uint": "KeyFrameUint"}[kind]
                    if kind != "double":
                        ease = "hold" if kind in ("bool", "id") else ease
                    it = "hold" if ease == "hold" else ("linear" if ease == "linear" else "cubic")
                    kf = E(tag, value=round(v, 4) if isinstance(v, float) else v, frame=f,
                           interpolationType=it)
                    if it == "cubic":
                        x1, y1, x2, y2 = EASES[ease]
                        kf.add(E("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2))
                    kp.add(kf)
                ko.add(kp)
            a.add(ko)
        return a


# ---------------------------------------------------------------- state machine helpers
def cond_num(path, op, value):
    return E("TransitionViewModelCondition", opValue=op, kids=[
        E("TransitionPropertyViewModelComparator", kids=[
            E("BindablePropertyNumber", kids=[bind(path, 636)])]),
        E("TransitionValueNumberComparator", value=value)])


def cond_bool(path, value):
    return E("TransitionViewModelCondition", opValue="equal", kids=[
        E("TransitionPropertyViewModelComparator", kids=[
            E("BindablePropertyBoolean", kids=[bind(path, 634)])]),
        E("TransitionValueBooleanComparator", value=value)])


def cond_trigger(path):
    return E("TransitionViewModelCondition", kids=[
        E("TransitionPropertyViewModelComparator", kids=[
            E("BindablePropertyTrigger", kids=[bind(path, 686)])]),
        E("TransitionValueTriggerComparator")])


def write_num(path, value):
    return E("ListenerViewModelChange", kids=[
        E("BindablePropertyNumber", propertyValue=value, kids=[bind(path, 636, direction=True)])])


def write_bool(path, value):
    return E("ListenerViewModelChange", kids=[
        E("BindablePropertyBoolean", propertyValue=value, kids=[bind(path, 634, direction=True)])])


def fire_trigger(path):
    return E("ListenerViewModelChange", kids=[
        E("BindablePropertyTrigger", propertyValue=1, kids=[bind(path, 686, direction=True)])])


def transition(to, conds=(), duration=None, exit_pct=None, interp=None):
    t = E("StateTransition", stateToId=to, duration=duration,
          enableExitTime=True if exit_pct is not None else None,
          exitTimeIsPercetange=True if exit_pct is not None else None,
          exitTime=exit_pct)
    if interp:
        t.a["interpolationType"] = "cubic"
        x1, y1, x2, y2 = EASES[interp]
        t.add(E("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2))
    t.add(list(conds))
    return t


class RNG(random.Random):
    pass
