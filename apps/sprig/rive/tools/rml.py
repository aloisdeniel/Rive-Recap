"""Tiny RML authoring kit used by build_sprig.py.

Everything here emits plain RML (Rive markup).  The generated scene.rml is the
editable source of truth for designers; this kit only exists so ten scenes,
their timelines and ~1,000 state-machine objects stay consistent.
"""
import math
import re

# ---------------------------------------------------------------- ids

class Ids:
    def __init__(self, start=1000):
        self.n = start

    def __call__(self):
        self.n += 1
        return f"0:{self.n}"


ID = Ids()

# ---------------------------------------------------------------- xml


class El:
    __slots__ = ("tag", "attrs", "kids", "text")

    def __init__(self, tag, attrs=None, kids=None, text=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids = [k for k in (kids or []) if k is not None]
        self.text = text

    def add(self, *kids):
        for k in kids:
            if k is None:
                continue
            if isinstance(k, (list, tuple)):
                self.add(*k)
            else:
                self.kids.append(k)
        return self

    @property
    def id(self):
        return self.attrs.get("id")


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if abs(v) < 1e-9:
            return "0"
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(v)


def E(_tag, *kids, **attrs):
    clean = {}
    for k, v in attrs.items():
        if v is None:
            continue
        clean[k.rstrip("_")] = v
    flat = []
    for k in kids:
        if isinstance(k, (list, tuple)):
            flat.extend(x for x in k if x is not None)
        elif k is not None:
            flat.append(k)
    return El(_tag, clean, flat)


def render(el, ind=0, out=None):
    out = [] if out is None else out
    pad = "  " * ind
    a = "".join(f' {k}="{escape(fmt(v))}"' for k, v in el.attrs.items())
    if not el.kids and el.text is None:
        out.append(f"{pad}<{el.tag}{a}/>")
    else:
        out.append(f"{pad}<{el.tag}{a}>")
        for k in el.kids:
            render(k, ind + 1, out)
        out.append(f"{pad}</{el.tag}>")
    return out


def escape(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

# ---------------------------------------------------------------- colours


class Col(str):
    """ARGB hex colour, used to pick KeyFrameColor."""


def col(hexrgb, a=1.0):
    h = hexrgb.lstrip("#")
    return Col(f"{int(round(a * 255)):02X}{h.upper()}")


FOREST = "#173E32"
CREAM = "#F6F1DC"
LEAF = "#A8CC72"
APRICOT = "#F3AD7D"
# tints derived from the four brand colours (paper shading only)
FOREST_DEEP = "#0F2C23"
FOREST_MID = "#1F4E3F"
FOREST_SOFT = "#2A614E"
FOREST_PALE = "#3C7A61"
LEAF_DARK = "#7FA850"
LEAF_DEEP = "#5C8A3C"
LEAF_PALE = "#C9E0A3"
CREAM_SHADE = "#E9E0C2"
CREAM_DARK = "#D8CBA2"
APRICOT_DARK = "#DD8D5D"
APRICOT_PALE = "#F8CDAE"

# ---------------------------------------------------------------- paint


def solid(c, name="Color", id=None):
    return E("SolidColor", colorValue=c, name=name, id=id)


def fill(c, name="Fill", id=None, color_id=None, bind=None, feather=None, rule=None):
    sc = solid(c, id=color_id)
    if bind is not None:
        sc.add(bind)
    kids = [sc]
    if feather:
        kids.append(E("Feather", strength=float(feather), name="Feather"))
        rule = "clockwise"
    return E("Fill", *kids, name=name, id=id, fillRule=rule)


def lin_grad(stops, sx, sy, ex, ey, name="Fill"):
    g = E("LinearGradient", startX=float(sx), startY=float(sy), endX=float(ex), endY=float(ey), name="Gradient")
    for pos, c in stops:
        g.add(E("GradientStop", colorValue=c, position=float(pos)))
    return E("Fill", g, name=name)


def rad_grad(stops, cx, cy, r, name="Fill"):
    g = E("RadialGradient", startX=float(cx), startY=float(cy), endX=float(cx + r), endY=float(cy), name="Gradient")
    for pos, c in stops:
        g.add(E("GradientStop", colorValue=c, position=float(pos)))
    return E("Fill", g, name=name)


def stroke(c, w, name="Stroke", cap="round", join="round", trim=None, id=None, color_id=None,
           fixed=False, feather=None, bind=None):
    sc = solid(c, id=color_id)
    if bind is not None:
        sc.add(bind)
    kids = [sc]
    if feather:
        kids.append(E("Feather", strength=float(feather), name="Feather"))
    if trim is not None:
        kids.append(trim)
    return E("Stroke", *kids, thickness=float(w), cap=cap, join=join, name=name, id=id,
             transformAffectsStroke=(False if fixed else None))


def trim(start=0.0, end=1.0, offset=0.0, id=None, bind=None):
    t = E("TrimPath", start=float(start), end=float(end), offset=float(offset), modeValue="sequential",
          name="Trim", id=id)
    if bind is not None:
        t.add(bind)
    return t

# ---------------------------------------------------------------- geometry

TOK = re.compile(r"[MCLZmclz]|-?\d*\.?\d+(?:e-?\d+)?")


def parse_d(d):
    """Parse absolute M/C/L/Z into contours of segments."""
    toks = TOK.findall(d)
    i = 0
    contours = []
    cur = None
    cmd = None
    while i < len(toks):
        t = toks[i]
        if t in "MCLZ":
            cmd = t
            i += 1
            if cmd == "Z":
                cur["closed"] = True
                continue
        def num():
            nonlocal i
            v = float(toks[i]); i += 1
            return v
        if cmd == "M":
            cur = {"start": (num(), num()), "segs": [], "closed": False}
            contours.append(cur)
            cmd = "L"
        elif cmd == "L":
            cur["segs"].append(("L", (num(), num())))
        elif cmd == "C":
            c1 = (num(), num()); c2 = (num(), num()); p = (num(), num())
            cur["segs"].append(("C", c1, c2, p))
        else:
            raise ValueError(d)
    return contours


def _ang(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0]), math.hypot(b[0] - a[0], b[1] - a[1])


def path_el(d, name="Path", id=None, closed=None):
    cs = parse_d(d)
    out = []
    for ci, c in enumerate(cs):
        pts = [c["start"]]
        hin = [None]
        hout = []
        for s in c["segs"]:
            if s[0] == "L":
                hout.append(None)
                pts.append(s[1]); hin.append(None)
            else:
                hout.append(s[1])
                pts.append(s[3]); hin.append(s[2])
        hout.append(None)
        is_closed = c["closed"] if closed is None else closed
        if is_closed and len(pts) > 1 and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < 1e-6:
            hin[0] = hin[-1]
            pts.pop(); hin.pop(); hout.pop()
        area = 0
        for i in range(len(pts)):
            x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
            area += x1 * y2 - x2 * y1
        verts = []
        for p, hi, ho in zip(pts, hin, hout):
            if hi is None and ho is None:
                verts.append(E("StraightVertex", x=float(p[0]), y=float(p[1])))
            else:
                ia, idist = _ang(p, hi) if hi else (0.0, 0.0)
                oa, odist = _ang(p, ho) if ho else (0.0, 0.0)
                if hi is None:
                    ia = oa + math.pi
                if ho is None:
                    oa = ia + math.pi
                verts.append(E("CubicDetachedVertex", x=float(p[0]), y=float(p[1]),
                               inRotation=float(ia), inDistance=float(idist),
                               outRotation=float(oa), outDistance=float(odist)))
        out.append(E("PointsPath", *verts, isClosed=bool(is_closed), isClockwise=bool(area > 0),
                     name=name if ci == 0 else f"{name} {ci}", id=id if ci == 0 else None))
    return out


def rect(w, h, r=0.0, ox=0.5, oy=0.5, name="Rect", id=None, bind=None):
    el = E("Rectangle", width=float(w), height=float(h), originX=float(ox), originY=float(oy),
           cornerRadiusTL=float(r) if r else None, name=name, id=id)
    if bind is not None:
        el.add(bind)
    return el


def ellipse(w, h, ox=0.5, oy=0.5, name="Ellipse", id=None):
    return E("Ellipse", width=float(w), height=float(h), originX=float(ox), originY=float(oy), name=name, id=id)


def shape(name, *kids, x=0.0, y=0.0, id=None, rot=None, sx=None, sy=None, op=None, opaque=None, blend=None):
    return E("Shape", *kids, x=float(x), y=float(y), rotation=_f(rot), scaleX=_f(sx), scaleY=_f(sy),
             opacity=_f(op), isTargetOpaque=opaque, blendModeValue=blend, name=name, id=id or ID())


def node(name, *kids, x=0.0, y=0.0, id=None, rot=None, sx=None, sy=None, op=None):
    return E("Node", *kids, x=float(x), y=float(y), rotation=_f(rot), scaleX=_f(sx), scaleY=_f(sy),
             opacity=_f(op), name=name, id=id or ID())


def _f(v):
    return None if v is None else float(v)

# leaf geometry: base at (0,0), tip at (bend,-L)


def leaf_half_d(L, W, side=-1, bend=0.0, fat=0.62):
    s = side
    return (f"M0 0 C{s*W*fat:.2f} {-L*0.12:.2f} {s*W*0.6+bend*0.4:.2f} {-L*0.74:.2f} {bend:.2f} {-L:.2f} "
            f"C{bend*0.7:.2f} {-L*0.66:.2f} {bend*0.25:.2f} {-L*0.3:.2f} 0 0 Z")


def leaf_full_d(L, W, bend=0.0, fat=0.62):
    return (f"M0 0 C{-W*fat:.2f} {-L*0.12:.2f} {-W*0.6+bend*0.4:.2f} {-L*0.74:.2f} {bend:.2f} {-L:.2f} "
            f"C{W*0.6+bend*0.4:.2f} {-L*0.74:.2f} {W*fat:.2f} {-L*0.12:.2f} 0 0 Z")


def heart_half_d(L, W, side=-1):
    s = side
    return (f"M0 {-L*0.16:.2f} C{s*W*0.2:.2f} {L*0.06:.2f} {s*W*0.62:.2f} {-L*0.02:.2f} {s*W*0.52:.2f} {-L*0.42:.2f} "
            f"C{s*W*0.44:.2f} {-L*0.74:.2f} {s*W*0.14:.2f} {-L*0.86:.2f} 0 {-L:.2f} Z")


def rib_d(L, bend=0.0):
    return f"M0 {-L*0.04:.2f} C{bend*0.25:.2f} {-L*0.35:.2f} {bend*0.7:.2f} {-L*0.7:.2f} {bend*0.92:.2f} {-L*0.93:.2f}"


def leaf(name, x, y, L, W, rot=0.0, light=LEAF, dark=LEAF_DARK, rib=CREAM, rib_a=0.35, bend=0.0,
         kind="leaf", s=1.0, op=None, ids=None):
    """Folded-paper leaf: two halves (light/dark) hinged on the midrib.

    Returns (node_el, parts) where parts holds ids for animation:
      parts['node'], parts['left'], parts['right']
    The halves are shapes at the midrib, so keying scaleX opens/closes the fold.
    """
    nid = ID(); lid = ID(); rid = ID()
    if kind == "heart":
        ld, rd = heart_half_d(L, W, -1), heart_half_d(L, W, 1)
    else:
        ld, rd = leaf_half_d(L, W, -1, bend), leaf_half_d(L, W, 1, bend)
    kids = []
    if rib:
        kids.append(shape(f"{name} rib", *path_el(rib_d(L, bend if kind != 'heart' else 0), closed=False),
                          stroke(col(rib, rib_a), max(0.8, W * 0.035)), id=ID()))
    kids.append(shape(f"{name} R", *path_el(rd), fill(col(dark)), id=rid))
    kids.append(shape(f"{name} L", *path_el(ld), fill(col(light)), id=lid))
    n = node(name, *kids, x=x, y=y, rot=rot, sx=s if s != 1 else None, sy=s if s != 1 else None, op=op, id=nid)
    return n, {"node": nid, "left": lid, "right": rid}

# ---------------------------------------------------------------- animation

EASES = {
    "io": (0.45, 0.0, 0.55, 1.0),
    "out": (0.16, 1.0, 0.3, 1.0),
    "outs": (0.22, 0.61, 0.36, 1.0),
    "in": (0.55, 0.0, 0.85, 0.35),
    "soft": (0.33, 0.0, 0.15, 1.0),
    "back": (0.34, 1.42, 0.64, 1.0),
    "backs": (0.3, 1.25, 0.6, 1.0),
    "antic": (0.6, -0.35, 0.7, 0.05),
    "fold": (0.7, 0.0, 0.25, 1.0),
    "sine": (0.37, 0.0, 0.63, 1.0),
}


def keyframe(frame, value, ease="io"):
    if isinstance(value, bool):
        return E("KeyFrameBool", value=value, frame=int(frame))
    if isinstance(value, Col):
        tag = "KeyFrameColor"
    else:
        tag = "KeyFrameDouble"
        value = float(value)
    if ease in ("hold", None):
        return E(tag, value=value, frame=int(frame), interpolationType="hold")
    if ease == "lin":
        return E(tag, value=value, frame=int(frame), interpolationType="linear")
    if ease == "elastic":
        return E(tag, E("ElasticInterpolator", easingValue="easeOut", amplitude=1.0, period=0.45),
                 value=value, frame=int(frame), interpolationType="elastic")
    x1, y1, x2, y2 = EASES[ease] if isinstance(ease, str) else ease
    return E(tag, E("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2), value=value, frame=int(frame),
             interpolationType="cubic")


class Anim:
    """A LinearAnimation under construction: tracks keyed by (objectId, property)."""

    def __init__(self, name, dur, loop="oneShot"):
        self.name = name
        self.dur = int(dur)
        self.loop = loop
        self.tracks = {}
        self.id = ID()

    def key(self, obj, prop, keys):
        """keys: list of (frame, value[, ease]). Replaces an existing track."""
        norm = []
        for k in keys:
            f, v = k[0], k[1]
            e = k[2] if len(k) > 2 else "io"
            norm.append((int(round(f)), v, e))
        norm.sort(key=lambda t: t[0])
        self.tracks[(obj, prop)] = norm
        return self

    def set(self, obj, prop, value):
        self.tracks[(obj, prop)] = [(0, value, "hold")]
        return self

    def el(self):
        a = E("LinearAnimation", loopValue=self.loop, duration=self.dur, name=self.name, id=self.id)
        byobj = {}
        for (obj, prop), keys in self.tracks.items():
            byobj.setdefault(obj, []).append((prop, keys))
        for obj, props in byobj.items():
            ko = E("KeyedObject", objectId=obj)
            for prop, keys in props:
                kp = E("KeyedProperty", property=prop)
                for f, v, e in keys:
                    kp.add(keyframe(f, v, e))
                ko.add(kp)
            a.add(ko)
        return a

# ---------------------------------------------------------------- data binding


def bind(path, key, conv=None, two_way=False, direction=False, id=None):
    return E("DataBindContext", sourcePathIds=path, propertyKey=key, converterId=conv,
             twoWay=True if two_way else None, direction=True if direction else None, id=id)


class Converters:
    """Root-level data converters, deduplicated by key."""

    def __init__(self):
        self.items = []
        self.cache = {}

    def add(self, key, builder):
        if key in self.cache:
            return self.cache[key]
        cid = ID()
        el = builder(cid)
        self.items.append(el)
        self.cache[key] = cid
        return cid

    def group(self, key, ids, name):
        def b(cid):
            g = E("DataConverterGroup", name=name, id=cid)
            for i in ids:
                g.add(E("DataConverterGroupItem", converterId=i))
            return g
        return self.add(("group", key), b)


# formula tokens
def tIn():
    return E("FormulaTokenInput")


def tV(v=None, bind_el=None):
    el = E("FormulaTokenValue", operationValue=float(v) if v is not None else None)
    if bind_el is not None:
        el.add(bind_el)
    return el


OPS = {"+": 0, "-": 1, "*": 2, "/": 3, "%": 4}
FUN = {"min": 0, "max": 1, "round": 2, "ceil": 3, "floor": 4}


def tOp(o):
    return E("FormulaTokenOperation", operationType=OPS[o])


def tF(f):
    return E("FormulaTokenFunction", functionType=FUN[f])


def tSep():
    return E("FormulaTokenArgumentSeparator")


def tO():
    return E("FormulaTokenParenthesisOpen")


def tC():
    return E("FormulaTokenParenthesisClose")


def formula(name, tokens):
    def b(cid):
        return E("DataConverterFormula", *tokens, name=name, id=cid)
    return b
