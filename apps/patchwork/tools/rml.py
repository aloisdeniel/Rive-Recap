"""Tiny RML builder used to generate the Patchwork recap scene.

Every element gets a deterministic id so the generated scene.rml is stable
between runs (the Rive CLI would otherwise write ids back into the file).
"""
from __future__ import annotations

from xml.sax.saxutils import quoteattr

_next = [1000]


def reset_ids(start: int = 1000) -> None:
    _next[0] = start


def new_id() -> str:
    _next[0] += 1
    return f"0:{_next[0]}"


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.5f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


# Elements that must not carry an id/name (filters, tokens etc. accept ids but
# a few reject name).  We only add ids, never names, automatically.
NO_ID = {"Rive"}


class E:

    def __init__(self, tag, attrs=None, children=None, id=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = list(children or [])
        self.text = text
        if tag in NO_ID:
            self.id = None
        else:
            self.id = id or self.attrs.pop("id", None) or new_id()

    def add(self, *kids):
        for k in kids:
            if k is None:
                continue
            if isinstance(k, (list, tuple)):
                self.add(*k)
            else:
                self.children.append(k)
        return self

    def render(self, ind=0, out=None):
        out = [] if out is None else out
        pad = "    " * ind
        a = "".join(f" {k}={quoteattr(fmt(v))}" for k, v in self.attrs.items() if v is not None)
        if self.id:
            a += f' id="{self.id}"'
        if not self.children and self.text is None:
            out.append(f"{pad}<{self.tag}{a}/>")
        else:
            out.append(f"{pad}<{self.tag}{a}>")
            if self.text is not None:
                out.append(self.text)
            for c in self.children:
                c.render(ind + 1, out)
            out.append(f"{pad}</{self.tag}>")
        return out


def el(tag, *children, **attrs):
    eid = attrs.pop("id", None)
    e = E(tag, attrs, id=eid)
    e.add(*children)
    return e


# ---------------------------------------------------------------- colours

def argb(hex6: str, alpha: float = 1.0) -> str:
    hex6 = hex6.lstrip("#")
    a = max(0, min(255, round(alpha * 255)))
    return f"{a:02X}{hex6.upper()}"


# ---------------------------------------------------------------- paint

def solid(color, name="Color", **kw):
    return el("SolidColor", colorValue=color, name=name, **kw)


def fill(color, name="Fill", **kw):
    c = solid(color) if isinstance(color, str) else color
    return el("Fill", c, name=name, **kw)


def stroke(color, thickness=2.0, cap="round", join="round", dash=None, trim=None, name="Stroke", **kw):
    kids = [solid(color) if isinstance(color, str) else color]
    if dash:
        kids.append(el("DashPath", *[el("Dash", length=d, name=f"d{i}") for i, d in enumerate(dash)], name="Dashes"))
    if trim is not None:
        kids.append(trim)
    return el("Stroke", *kids, thickness=thickness, cap=cap, join=join, name=name, **kw)


# ---------------------------------------------------------------- geometry

def rect(w, h, r=0.0, ox=0.5, oy=0.5, name="Path", **kw):
    a = dict(width=w, height=h, originX=ox, originY=oy, name=name)
    if r:
        a["cornerRadiusTL"] = r
    a.update(kw)
    return el("Rectangle", **a)


def ellipse(w, h, ox=0.5, oy=0.5, name="Path", **kw):
    return el("Ellipse", width=w, height=h, originX=ox, originY=oy, name=name, **kw)


def poly_path(points, closed=True, radius=0.0, name="Path"):
    """points: list of (x, y) or (x, y, r) straight vertices; clockwise is computed."""
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[(i + 1) % n][0], points[(i + 1) % n][1]
        area += x1 * y2 - x2 * y1
    cw = area > 0  # y down => positive shoelace is clockwise on screen
    verts = []
    for p in points:
        r = p[2] if len(p) > 2 else radius
        a = dict(x=p[0], y=p[1])
        if r:
            a["radius"] = r
        verts.append(el("StraightVertex", **a))
    return el("PointsPath", *verts, isClosed=closed, isClockwise=cw, name=name)


def curve_path(points, closed=False, name="Path"):
    """points: list of (x, y, rotation, distance) mirrored cubic vertices or (x,y) straight."""
    verts = []
    for p in points:
        if len(p) == 2:
            verts.append(el("StraightVertex", x=p[0], y=p[1]))
        else:
            verts.append(el("CubicMirroredVertex", x=p[0], y=p[1], rotation=p[2], distance=p[3]))
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[(i + 1) % n][0], points[(i + 1) % n][1]
        area += x1 * y2 - x2 * y1
    return el("PointsPath", *verts, isClosed=closed, isClockwise=area > 0, name=name)


def shape(name, *kids, x=0.0, y=0.0, **kw):
    return el("Shape", *kids, x=x, y=y, name=name, **kw)


def node(name, *kids, x=0.0, y=0.0, **kw):
    return el("Node", *kids, x=x, y=y, name=name, **kw)


# ---------------------------------------------------------------- data binding

class VM:
    def __init__(self, name, vid=None):
        self.name = name
        self.id = vid or new_id()
        self.props = {}  # name -> (type, id, default)
        self.order = []

    def prop(self, name, typ, default=None):
        pid = new_id()
        self.props[name] = (typ, pid, default)
        self.order.append(name)
        return pid

    def path(self, name):
        return f"{self.id}-{self.props[name][1]}"

    def element(self, inst_id):
        kids = []
        inst = []
        for n in self.order:
            typ, pid, default = self.props[n]
            kids.append(E(f"ViewModelProperty{typ}", {"name": n}, id=pid))
            ia = {"viewModelPropertyId": pid}
            if typ != "Trigger" and default is not None:
                ia = {"propertyValue": default, **ia}
            inst.append(E(f"ViewModelInstance{typ}", ia))
        kids.append(E("ViewModelInstance", {"exports": True, "name": "Default"}, inst, id=inst_id))
        return E("ViewModel", {"defaultInstanceId": inst_id, "name": self.name}, kids, id=self.id)


def bind(vm: VM, prop, key, conv=None, **flags):
    a = dict(sourcePathIds=vm.path(prop), propertyKey=key)
    if conv:
        a["converterId"] = conv
    a.update(flags)
    return el("DataBindContext", **a)


BINDABLE_KEY = {"Number": 636, "Boolean": 634, "String": 635, "Trigger": 686, "Color": 638, "Integer": 686}


def _bp(vm, prop, typ, value=None, direction=False, conv=None):
    a = {}
    if value is not None:
        a["propertyValue"] = value
    ctx = dict(sourcePathIds=vm.path(prop), propertyKey=BINDABLE_KEY[typ])
    if direction:
        ctx["direction"] = True
    if conv:
        ctx["converterId"] = conv
    return el(f"BindableProperty{typ}", el("DataBindContext", **ctx), **a)


def set_vm(vm, prop, typ, value):
    """ListenerViewModelChange writing a literal (usable in listeners and states)."""
    if typ == "Trigger":
        value = 1
    return el("ListenerViewModelChange", _bp(vm, prop, typ, value, direction=True))


def set_vm_from(vm, src_prop, dst_prop, typ, conv):
    """Write conv(src) into dst."""
    rid = new_id()
    bp = el(f"BindableProperty{typ}",
            el("DataBindContext", sourcePathIds=vm.path(src_prop), propertyKey=BINDABLE_KEY[typ],
               converterId=conv, id=rid),
            el("DataBindContext", sourcePathIds=vm.path(dst_prop), propertyKey=BINDABLE_KEY[typ], direction=True))
    return el("ListenerViewModelChange", bp, fromViewModelProperty=True, fromDataBindId=rid)


def cond(vm, prop, typ, value=None, op="equal"):
    left = el("TransitionPropertyViewModelComparator", _bp(vm, prop, typ))
    if typ == "Trigger":
        right = el("TransitionValueTriggerComparator")
    elif typ == "Boolean":
        right = el("TransitionValueBooleanComparator", value=value)
    elif typ in ("Number", "Integer"):
        right = el("TransitionValueNumberComparator", value=value)
    elif typ == "String":
        right = el("TransitionValueStringComparator", value=value)
    else:
        raise ValueError(typ)
    a = {} if op == "equal" else {"opValue": op}
    return el("TransitionViewModelCondition", left, right, **a)


def trans(to, *conds, duration=0, exit_pct=None, **kw):
    a = dict(stateToId=to)
    if duration:
        a["duration"] = duration
    if exit_pct is not None:
        a.update(enableExitTime=True, exitTimeIsPercetange=True, exitTime=exit_pct)
    a.update(kw)
    return el("StateTransition", *conds, **a)


# ---------------------------------------------------------------- animation

def cubic(x1, y1, x2, y2):
    return el("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2)


EASES = {
    "out": (0.16, 1.0, 0.3, 1.0),        # soft settle (fabric landing)
    "in": (0.55, 0.0, 0.9, 0.4),
    "inout": (0.65, 0.0, 0.35, 1.0),
    "back": (0.34, 1.45, 0.64, 1.0),      # anticipation-free overshoot (follow-through)
    "antic": (0.5, -0.45, 0.6, 1.0),      # anticipation dip then go
    "cloth": (0.22, 1.18, 0.36, 1.0),     # light overshoot like fabric settling
    "thread": (0.45, 0.05, 0.25, 1.0),
}


class Anim:
    def __init__(self, name, frames, loop="oneShot", aid=None):
        self.name = name
        self.frames = frames
        self.loop = loop
        self.id = aid or new_id()
        self.keys = {}  # (obj, prop) -> list of (frame, value, kind, interp)
        self.order = []

    def key(self, obj, prop, frame, value, interp="hold", kind="Double"):
        k = (obj, prop)
        if k not in self.keys:
            self.keys[k] = []
            self.order.append(k)
        self.keys[k].append((int(round(frame)), value, kind, interp))
        return self

    def tween(self, obj, prop, f0, v0, f1, v1, ease="out", kind="Double"):
        """Key v0 at f0 easing to v1 at f1."""
        self.key(obj, prop, f0, v0, ease, kind)
        self.key(obj, prop, f1, v1, "hold", kind)
        return self

    def seq(self, obj, prop, pts, kind="Double"):
        """pts: list of (frame, value, ease_to_next)."""
        for p in pts:
            self.key(obj, prop, p[0], p[1], p[2] if len(p) > 2 else "hold", kind)
        return self

    def element(self):
        by_obj = {}
        objs = []
        for (o, p) in self.order:
            if o not in by_obj:
                by_obj[o] = []
                objs.append(o)
            by_obj[o].append(p)
        kos = []
        for o in objs:
            kps = []
            for p in by_obj[o]:
                frames = {}
                for (f, v, kind, interp) in self.keys[(o, p)]:
                    frames[f] = (v, kind, interp)  # later wins
                kfs = []
                for f in sorted(frames):
                    v, kind, interp = frames[f]
                    a = dict(value=v, frame=f) if kind != "Callback" else dict(frame=f)
                    kids = []
                    if kind == "Callback":
                        pass
                    elif interp == "hold" or kind in ("Id", "Bool"):
                        a["interpolationType"] = "hold"
                    elif interp == "linear":
                        a["interpolationType"] = "linear"
                    else:
                        a["interpolationType"] = "cubic"
                        kids.append(cubic(*EASES[interp]) if isinstance(interp, str) else cubic(*interp))
                    kfs.append(el(f"KeyFrame{kind}", *kids, **a))
                if isinstance(p, int):
                    kps.append(el("KeyedProperty", *kfs, propertyKey=p))
                else:
                    kps.append(el("KeyedProperty", *kfs, property=p))
            kos.append(el("KeyedObject", *kps, objectId=o))
        return E("LinearAnimation", {"loopValue": self.loop, "duration": self.frames, "name": self.name}, kos, id=self.id)
