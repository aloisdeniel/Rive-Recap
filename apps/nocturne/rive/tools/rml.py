"""Tiny RML authoring DSL used by generate.py.

Every element gets a deterministic id so `rive` never has to write ids back
into the generated files, and so the generator can be re-run safely.
"""
import math
from xml.sax.saxutils import quoteattr

_N = [100]
REST = {}  # (id, prop) -> authored (settled) value, used to auto-complete timelines

TRANSFORM_TAGS = {"Node", "Shape", "Text", "NestedArtboard", "LayoutComponent", "Solo"}
TRANSFORM_DEFAULTS = {"x": 0.0, "y": 0.0, "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0, "opacity": 1.0}


def nid():
    _N[0] += 1
    return f"0:{_N[0]}"


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.5f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(v)


class El:
    def __init__(self, _tag, *children, noid=False, **attrs):
        tag = _tag
        self.tag = tag
        self.children = [c for c in _flatten(children) if c is not None]
        if "id" not in attrs:
            attrs["id"] = nid()
        self.attrs = attrs
        oid = attrs.get("id")
        if tag in TRANSFORM_TAGS:
            for p, d in TRANSFORM_DEFAULTS.items():
                REST[(oid, p)] = float(attrs.get(p, d))
        if tag == "TrimPath":
            for p in ("start", "end", "offset"):
                REST[(oid, p)] = float(attrs.get(p, 0.0))
        if tag in ("Ellipse", "Rectangle"):
            for p in ("width", "height"):
                if p in attrs:
                    REST[(oid, p)] = float(attrs[p])
        if tag in ("SolidColor", "GradientStop") and "colorValue" in attrs:
            REST[(oid, "colorValue")] = attrs["colorValue"]
        if tag == "Star":
            REST[(oid, "innerRadius")] = float(attrs.get("innerRadius", 0.5))
        if tag == "NestedRemapAnimation":
            REST[(oid, "time")] = float(attrs.get("time", 0.0))
        if tag == "Feather":
            REST[(oid, "strength")] = float(attrs.get("strength", 12))
        if tag == "TextModifierRange":
            for p, d in (("modifyFrom", 0.0), ("modifyTo", 1.0), ("falloffFrom", 0.0), ("falloffTo", 1.0), ("offset", 0.0)):
                REST[(oid, p)] = float(attrs.get(p, d))
        if tag == "ScriptInputNumber":
            REST[(oid, "propertyValue")] = float(attrs.get("propertyValue", 0.0))
        if tag == "DashPath":
            REST[(oid, "offset")] = float(attrs.get("offset", 0.0))

    @property
    def id(self):
        return self.attrs["id"]

    def add(self, *children):
        self.children.extend(c for c in _flatten(children) if c is not None)
        return self

    def render(self, ind=0):
        pad = "    " * ind
        order = ["name"]
        attrs = " ".join(f"{k}={quoteattr(fmt(v))}" for k, v in self.attrs.items() if k not in ("name", "id"))
        tail = ""
        if "name" in self.attrs:
            tail += f" name={quoteattr(str(self.attrs['name']))}"
        if "id" in self.attrs:
            tail += f" id={quoteattr(self.attrs['id'])}"
        head = f"{pad}<{self.tag}{(' ' + attrs) if attrs else ''}{tail}"
        if not self.children:
            return head + "/>"
        inner = "\n".join(c.render(ind + 1) if isinstance(c, El) else pad + "    " + c for c in self.children)
        return f"{head}>\n{inner}\n{pad}</{self.tag}>"


def _flatten(items):
    for i in items:
        if isinstance(i, (list, tuple)):
            yield from _flatten(i)
        else:
            yield i


def doc(*roots):
    body = "\n\n".join(r.render(1) for r in _flatten(roots))
    return f'<Rive version="1" kind="fragment">\n{body}\n</Rive>\n'


# ---------------------------------------------------------------- colour
def argb(hex6, a=1.0):
    hex6 = hex6.lstrip("#")
    return f"{int(round(a * 255)):02X}{hex6.upper()}"


# ---------------------------------------------------------------- paint
def solid(hex6, a=1.0, **kw):
    return El("SolidColor", colorValue=argb(hex6, a), name=kw.pop("name", "Color"), **kw)


def fill(hex6=None, a=1.0, paint=None, feather=None, name="Fill", **kw):
    ch = [paint if paint is not None else solid(hex6, a)]
    if feather is not None:
        ch.append(El("Feather", strength=float(feather), name="Feather"))
        kw.setdefault("fillRule", "clockwise")
    return El("Fill", *ch, name=name, **kw)


def stroke(hex6=None, a=1.0, w=1.0, paint=None, cap=None, effects=(), feather=None, name="Stroke", **kw):
    ch = [paint if paint is not None else solid(hex6, a)]
    if feather is not None:
        ch.append(El("Feather", strength=float(feather), name="Feather"))
    ch.extend(effects)
    if cap:
        kw["cap"] = cap
    return El("Stroke", *ch, thickness=float(w), name=name, **kw)


def radial(stops, r, cx=0.0, cy=0.0, name="Radial"):
    return El("RadialGradient",
              *[El("GradientStop", colorValue=argb(c, a), position=float(p), name="Stop") for p, c, a in stops],
              startX=float(cx), startY=float(cy), endX=float(cx + r), endY=float(cy), name=name)


def linear(stops, x0, y0, x1, y1, name="Linear"):
    return El("LinearGradient",
              *[El("GradientStop", colorValue=argb(c, a), position=float(p), name="Stop") for p, c, a in stops],
              startX=float(x0), startY=float(y0), endX=float(x1), endY=float(y1), name=name)


def trim(start=0.0, end=1.0, offset=0.0, mode=None, name="Trim"):
    kw = {}
    if mode:
        kw["modeValue"] = mode
    return El("TrimPath", start=float(start), end=float(end), offset=float(offset), name=name, **kw)


def dash(on, off, name="Dash", offset=0.0):
    return El("DashPath", El("Dash", length=float(on), name="On"), El("Dash", length=float(off), name="Off"),
              offset=float(offset), name=name)


# ---------------------------------------------------------------- geometry
def ellipse(w, h=None, **kw):
    return El("Ellipse", width=float(w), height=float(w if h is None else h), name=kw.pop("name", "Path"), **kw)


def rect(w, h, r=0.0, ox=0.5, oy=0.5, **kw):
    if r:
        kw["cornerRadiusTL"] = float(r)
    return El("Rectangle", width=float(w), height=float(h), originX=float(ox), originY=float(oy),
              name=kw.pop("name", "Path"), **kw)


def poly(points, closed=True, cw=True, name="Path"):
    """points: list of (x, y) straight vertices or (x, y, 'c', rot, dist) mirrored cubic."""
    vs = []
    for p in points:
        if len(p) == 2:
            vs.append(El("StraightVertex", x=float(p[0]), y=float(p[1]), name="V"))
        elif p[2] == "r":
            vs.append(El("StraightVertex", x=float(p[0]), y=float(p[1]), radius=float(p[3]), name="V"))
        else:
            vs.append(El("CubicMirroredVertex", x=float(p[0]), y=float(p[1]), rotation=float(p[3]),
                         distance=float(p[4]), name="V"))
    return El("PointsPath", *vs, isClosed=closed, isClockwise=cw, name=name)


def smooth_path(pts, closed=False, tension=0.33, name="Path"):
    """Catmull-Rom-ish smooth open path through pts using mirrored cubic vertices."""
    out = []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        if (i == 0 or i == n - 1) and not closed:
            out.append((x, y))
            continue
        p0 = pts[(i - 1) % n]
        p2 = pts[(i + 1) % n]
        dx, dy = p2[0] - p0[0], p2[1] - p0[1]
        ang = math.atan2(dy, dx)
        dist = math.hypot(dx, dy) * tension * 0.5
        out.append((x, y, "c", ang, dist))
    return poly(out, closed=closed, name=name)


def shape(name, *children, x=0.0, y=0.0, **kw):
    return El("Shape", *children, x=float(x), y=float(y), name=name, **kw)


def node(name, *children, x=0.0, y=0.0, **kw):
    return El("Node", *children, x=float(x), y=float(y), name=name, **kw)


def star4(name, x, y, size, color, a=1.0, glow=None, glow_a=0.5, inner=0.18, rot=0.0, **kw):
    """A four-point sparkle with optional feathered glow."""
    ch = [El("Star", width=float(size), height=float(size), points=4, innerRadius=float(inner), name="Path")]
    if glow:
        ch.append(fill(color, glow_a, feather=glow, name="Glow"))
    ch.append(fill(color, a))
    return shape(name, *ch, x=x, y=y, rotation=float(rot), **kw)


def dot(name, x, y, d, color, a=1.0, glow=None, glow_a=0.45, **kw):
    ch = [ellipse(d)]
    if glow:
        ch.append(fill(color, glow_a, feather=glow, name="Glow"))
    ch.append(fill(color, a))
    return shape(name, *ch, x=x, y=y, **kw)


# ---------------------------------------------------------------- easing / animation
EASE = {
    "out": (0.16, 1.0, 0.3, 1.0),        # expo-like settle (damped precision)
    "outSoft": (0.25, 0.8, 0.35, 1.0),
    "in": (0.55, 0.0, 0.9, 0.4),
    "inout": (0.65, 0.0, 0.35, 1.0),
    "sine": (0.37, 0.0, 0.63, 1.0),
    "back": (0.3, 1.4, 0.45, 1.0),      # small overshoot / follow-through
    "anticip": (0.5, -0.35, 0.75, 0.6),  # dips before leaving
}


def kf(frame, value, ease="out", color=False):
    tag = "KeyFrameColor" if color else "KeyFrameDouble"
    kw = {}
    if ease == "hold":
        kw["interpolationType"] = "hold"
        ch = []
    elif ease == "lin":
        kw["interpolationType"] = "linear"
        ch = []
    else:
        x1, y1, x2, y2 = EASE[ease] if isinstance(ease, str) else ease
        kw["interpolationType"] = "cubic"
        ch = [El("CubicEaseInterpolator", x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2))]
    val = value if color else float(value)
    return El(tag, *ch, value=val, frame=int(round(frame)), **kw)


COLOR_PROPS = {"colorValue"}


def anim(name, dur, tracks, loop="oneShot", fps=60, aid=None):
    """tracks: list of (objId, prop, [(frame, value, ease), ...])"""
    by_obj = {}
    for oid, prop, keys in tracks:
        by_obj.setdefault(oid, {}).setdefault(prop, [])
        by_obj[oid][prop].extend(keys)
    kos = []
    for oid, props in by_obj.items():
        kps = []
        for prop, keys in props.items():
            keys = sorted(keys, key=lambda k: k[0])
            # dedupe frames (last wins)
            ded = {}
            for k in keys:
                ded[int(round(k[0]))] = k
            keys = [ded[f] for f in sorted(ded)]
            col = prop in COLOR_PROPS
            kps.append(El("KeyedProperty", *[kf(k[0], k[1], k[2] if len(k) > 2 else "out", col) for k in keys],
                          property=prop, noid=True))
        kos.append(El("KeyedObject", *kps, objectId=oid, noid=True))
    kw = {"id": aid} if aid else {}
    return El("LinearAnimation", *kos, loopValue=loop, fps=fps, duration=int(dur), name=name, **kw)


def keys_of(tracks):
    return {(o, p) for o, p, _ in tracks}


def rest_tracks(pairs, frame=0, overrides=None):
    overrides = overrides or {}
    out = []
    for (o, p) in sorted(pairs):
        v = overrides.get((o, p), REST.get((o, p)))
        if v is None:
            continue
        out.append((o, p, [(frame, v, "hold")]))
    return out


def complete(tracks, universe, frame=0):
    """Add hold keys at `frame` with rest values for every (obj, prop) in universe not keyed."""
    have = keys_of(tracks)
    return tracks + rest_tracks(universe - have, frame)


# ---------------------------------------------------------------- data binding
class VM:
    def __init__(self, name, vid):
        self.name = name
        self.id = vid
        self.props = {}   # name -> (id, kind)

    def path(self, prop):
        return f"{self.id}-{self.props[prop][0]}"


VMREF = [None]


def P(prop):
    return VMREF[0].path(prop)


def bind(prop, key, conv=None, direction=False, **kw):
    a = dict(sourcePathIds=P(prop), propertyKey=key)
    if conv:
        a["converterId"] = conv
    if direction:
        a["direction"] = True
    a.update(kw)
    return El("DataBindContext", **a)


KEY_TEXT = 268
KEY_OPACITY = 18
KEY_X = 13
KEY_Y = 14
KEY_SCALEX = 16
KEY_COLOR = 37
KEY_DISPLAY = 596
KEY_SCALEY = 17
KEY_WIDTH_PATH = 20      # ParametricPath (Rectangle, Ellipse) width
KEY_HEIGHT_PATH = 21
KEY_WIDTH_LC = 7         # LayoutComponent width / height
KEY_HEIGHT_LC = 8
KEY_TEXT_W = 285         # Text width / height
KEY_TEXT_H = 286
KEY_TEXT_ALIGN = 281     # Text alignValue: left 0, right 1, center 2
KEY_GRAD_ENDY = 35       # LinearGradient endY


# ---------------------------------------------------------------- state machine pieces
def c_num(prop, op, v):
    return El("TransitionViewModelCondition",
              El("TransitionPropertyViewModelComparator",
                 El("BindablePropertyNumber", bind(prop, 636), noid=True), noid=True),
              El("TransitionValueNumberComparator", value=float(v), noid=True),
              opValue=op, noid=True)


def c_bool(prop, v=True):
    return El("TransitionViewModelCondition",
              El("TransitionPropertyViewModelComparator",
                 El("BindablePropertyBoolean", bind(prop, 634), noid=True), noid=True),
              El("TransitionValueBooleanComparator", value=bool(v), noid=True),
              opValue="equal", noid=True)


def c_trig(prop):
    return El("TransitionViewModelCondition",
              El("TransitionPropertyViewModelComparator",
                 El("BindablePropertyTrigger", bind(prop, 686), noid=True), noid=True),
              El("TransitionValueTriggerComparator", noid=True), noid=True)


def a_num(prop, v):
    return El("ListenerViewModelChange",
              El("BindablePropertyNumber", bind(prop, 636, direction=True), propertyValue=float(v), noid=True),
              noid=True)


def a_bool(prop, v):
    return El("ListenerViewModelChange",
              El("BindablePropertyBoolean", bind(prop, 634, direction=True), propertyValue=bool(v), noid=True),
              noid=True)


def a_str(prop, v):
    return El("ListenerViewModelChange",
              El("BindablePropertyString", bind(prop, 635, direction=True), propertyValue=v, noid=True),
              noid=True)


def a_color(prop, v):
    return El("ListenerViewModelChange",
              El("BindablePropertyColor", bind(prop, 638, direction=True), propertyValue=v, noid=True),
              noid=True)


def a_trig(prop):
    return El("ListenerViewModelChange",
              El("BindablePropertyTrigger", bind(prop, 686, direction=True), propertyValue=1, noid=True),
              noid=True)


def a_toggle(prop, negate_id):
    rid = nid()
    return El("ListenerViewModelChange",
              El("BindablePropertyBoolean",
                 El("DataBindContext", sourcePathIds=P(prop), propertyKey=634, converterId=negate_id, id=rid),
                 bind(prop, 634, direction=True), noid=True),
              fromViewModelProperty=True, fromDataBindId=rid, noid=True)


def tr(to, *conds, dur=0, exit_pct=None, exit_ms=None, actions=(), ease=None, **kw):
    a = dict(stateToId=to, duration=int(dur))
    if exit_pct is not None:
        a.update(enableExitTime=True, exitTimeIsPercetange=True, exitTime=int(exit_pct))
    if exit_ms is not None:
        a.update(enableExitTime=True, exitTime=int(exit_ms))
    ch = list(conds) + list(actions)
    if ease and dur:
        x1, y1, x2, y2 = EASE[ease]
        a["interpolationType"] = "cubic"
        ch.append(El("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2, noid=True))
    a.update(kw)
    return El("StateTransition", *ch, **a)


def layer(name, entry_to, states, x0=0, y0=0, any_tr=()):
    """states: list of AnimationState El (already positioned)."""
    return El("StateMachineLayer",
              El("AnyState", *any_tr, x=float(x0 + 0), y=float(y0 - 340)),
              El("ExitState", x=float(x0 + 220), y=float(y0 - 340)),
              El("EntryState", El("StateTransition", stateToId=entry_to), x=float(x0 - 220), y=float(y0)),
              *states, name=name)
