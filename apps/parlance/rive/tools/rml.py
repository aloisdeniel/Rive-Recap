"""Tiny RML emitter used by generate.py.

Everything here returns XML strings. Ids are allocated from one counter so the
whole document shares a single id namespace (as RML requires).
"""
import math
from xml.sax.saxutils import escape

_counter = [1000]


def nid():
    _counter[0] += 1
    return f"0:{_counter[0]}"


def reset_ids(start=1000):
    _counter[0] = start


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def attrs(d):
    out = []
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, str):
            out.append(f'{k}="{escape(v, {chr(34): "&quot;"})}"')
        else:
            out.append(f'{k}="{fmt(v)}"')
    return " ".join(out)


def E(tag, a=None, children=None):
    a = a or {}
    kids = [c for c in (children or []) if c]
    s = f"<{tag} {attrs(a)}".rstrip()
    if not kids:
        return s + "/>"
    return s + ">" + "".join(kids) + f"</{tag}>"


# ---------------------------------------------------------------- binding
VM_ID = None  # set by generate.py


def path(prop_id):
    return f"{VM_ID}-{prop_id}"


def bind(prop_id, key, conv=None, **flags):
    a = {"sourcePathIds": path(prop_id), "propertyKey": key, "converterId": conv}
    a.update({k: v for k, v in flags.items()})
    return E("DataBindContext", a)


# ---------------------------------------------------------------- paint
def solid(color, binds=None, id=None):
    return E("SolidColor", {"colorValue": color, "name": "Color", "id": id}, binds or [])


def fill(color, id=None, cid=None, binds=None, feather=None, rule=None, grad=None):
    kids = [grad if grad else solid(color, binds, cid)]
    if feather:
        kids.append(E("Feather", {"strength": feather[0], "offsetX": feather[1] if len(feather) > 1 else None,
                                  "offsetY": feather[2] if len(feather) > 2 else None, "name": "Feather"}))
        rule = "clockwise"
    return E("Fill", {"fillRule": rule, "name": "Fill", "id": id}, kids)


def stroke(color, w, cap="round", join="round", id=None, cid=None, effects=None, binds=None):
    return E("Stroke", {"thickness": w, "cap": cap, "join": join, "name": "Stroke", "id": id},
             [solid(color, binds, cid)] + (effects or []))


def lingrad(stops, sx, sy, ex, ey):
    return E("LinearGradient", {"startX": sx, "startY": sy, "endX": ex, "endY": ey, "name": "Gradient"},
             [E("GradientStop", {"colorValue": c, "position": p, "name": "Stop"}) for c, p in stops])


# ---------------------------------------------------------------- geometry
def rect(w, h, r=0, ox=0.5, oy=0.5, id=None, binds=None, x=None, y=None):
    return E("Rectangle", {"x": x, "y": y, "width": w, "height": h, "cornerRadiusTL": r if r else None,
                           "originX": ox, "originY": oy, "name": "Path", "id": id}, binds or [])


def ellipse(w, h, ox=0.5, oy=0.5, id=None, x=None, y=None):
    return E("Ellipse", {"x": x, "y": y, "width": w, "height": h, "originX": ox, "originY": oy,
                         "name": "Path", "id": id})


def smooth_path(points, closed=True, tension=1.0, id=None, vert_ids=None, cw=True):
    """points: list of (x, y) or (x, y, 'c', radius) for a corner."""
    n = len(points)
    verts = []
    for i, p in enumerate(points):
        vid = vert_ids[i] if vert_ids else None
        if len(p) > 2 and p[2] == "c":
            verts.append(E("StraightVertex", {"x": p[0], "y": p[1], "radius": p[3] if len(p) > 3 else 0,
                                              "id": vid}))
            continue
        if not closed and (i == 0 or i == n - 1):
            prv = points[i] if i == 0 else points[i - 1]
            nxt = points[i + 1] if i == 0 else points[i]
        else:
            prv = points[(i - 1) % n]
            nxt = points[(i + 1) % n]
        tx = (nxt[0] - prv[0]) / 2 * tension
        ty = (nxt[1] - prv[1]) / 2 * tension
        d = math.hypot(tx, ty) / 3
        ang = math.atan2(ty, tx)
        verts.append(E("CubicDetachedVertex", {
            "x": p[0], "y": p[1],
            "inRotation": round(ang + math.pi, 5), "inDistance": round(d, 3),
            "outRotation": round(ang, 5), "outDistance": round(d, 3), "id": vid}))
    return E("PointsPath", {"isClosed": closed, "isClockwise": cw, "name": "Path", "id": id}, verts)


def node(name, children, id=None, x=None, y=None, sx=None, sy=None, rot=None, op=None, binds=None,
         extra=None):
    a = {"x": x, "y": y, "scaleX": sx, "scaleY": sy, "rotation": rot, "opacity": op, "name": name, "id": id}
    if extra:
        a.update(extra)
    return E("Node", a, (binds or []) + children)


def shape(name, geoms, paints, id=None, x=None, y=None, sx=None, sy=None, rot=None, op=None,
          binds=None, extra=None, children=None):
    a = {"x": x, "y": y, "scaleX": sx, "scaleY": sy, "rotation": rot, "opacity": op, "name": name, "id": id}
    if extra:
        a.update(extra)
    return E("Shape", a, (binds or []) + (children or []) + geoms + paints)


# ---------------------------------------------------------------- text
TAG_WGHT = 2003265652
TAG_WDTH = 2003072104
TAG_OPSZ = 0x6F70737A


def tstyle(sid, font, size, color, wght=None, wdth=None, opsz=None, cid=None, cbinds=None,
           lh=None, ls=None, family=None, style=None, size_binds=None):
    kids = [fill(color, cid=cid, binds=cbinds)]
    if wght:
        kids.append(E("TextStyleAxis", {"tag": TAG_WGHT, "axisValue": wght, "name": "wght"}))
    if wdth:
        kids.append(E("TextStyleAxis", {"tag": TAG_WDTH, "axisValue": wdth, "name": "wdth"}))
    if opsz:
        kids.append(E("TextStyleAxis", {"tag": TAG_OPSZ, "axisValue": opsz, "name": "opsz"}))
    return E("TextStylePaint", {"fontSize": size, "fontAssetId": font, "lineHeight": lh, "letterSpacing": ls,
                                "familyName": family, "styleName": style, "name": "Style", "id": sid},
             (size_binds or []) + kids)


def run(sid, txt, binds=None, id=None, name="Run"):
    return E("TextValueRun", {"styleId": sid, "text": txt, "name": name, "id": id}, binds or [])


def text(name, x, y, styles, runs, id=None, w=None, h=None, sizing="autoWidth", overflow=None,
         align=None, valign=None, wrap=None, ox=None, oy=None, op=None, rot=None, sx=None, sy=None,
         extra_children=None, binds=None):
    a = {"x": x, "y": y, "width": w, "height": h, "sizingValue": sizing, "overflowValue": overflow,
         "alignValue": align, "verticalAlignValue": valign, "wrapValue": wrap, "originX": ox, "originY": oy,
         "opacity": op, "rotation": rot, "scaleX": sx, "scaleY": sy, "name": name, "id": id}
    return E("Text", a, (binds or []) + styles + runs + (extra_children or []))


# ---------------------------------------------------------------- animation
EASES = {
    "out": (0.16, 1, 0.3, 1),
    "out2": (0.22, 1, 0.36, 1),
    "in": (0.55, 0, 0.85, 0.3),
    "io": (0.65, 0, 0.35, 1),
    "sine": (0.37, 0, 0.63, 1),
    "back": (0.34, 1.56, 0.64, 1),
    "back2": (0.3, 1.9, 0.6, 1),
    "antic": (0.5, -0.45, 0.6, 1),
    "snap": (0.7, 0, 0.2, 1),
}


def _interp(ease):
    if ease is None or ease == "hold":
        return "hold", None
    if ease == "lin":
        return "linear", None
    if ease == "el":
        return "elastic", E("ElasticInterpolator", {"easingValue": "easeOut", "amplitude": 1, "period": 0.35})
    if ease == "el2":
        return "elastic", E("ElasticInterpolator", {"easingValue": "easeOut", "amplitude": 1.2, "period": 0.5})
    c = EASES[ease] if isinstance(ease, str) else ease
    return "cubic", E("CubicEaseInterpolator", {"x1": c[0], "y1": c[1], "x2": c[2], "y2": c[3]})


class Anim:
    def __init__(self, name, dur, loop=None, id=None):
        self.name = name
        self.dur = dur
        self.loop = loop
        self.id = id or nid()
        self.tracks = {}  # obj -> {prop: (kind, keys)}

    def k(self, obj, prop, keys, kind="d"):
        """keys: list of (frame, value, ease). kind d=double c=color u=uint b=bool i=id."""
        if obj is None:
            return self
        self.tracks.setdefault(obj, {})[prop] = (kind, keys)
        return self

    def hold(self, obj, prop, value, kind="d", frame=0):
        return self.k(obj, prop, [(frame, value, "hold")], kind)

    def xml(self):
        objs = []
        for obj, props in self.tracks.items():
            kps = []
            for prop, (kind, keys) in props.items():
                kfs = []
                for (f, v, ease) in sorted(keys, key=lambda t: t[0]):
                    f = int(round(f))
                    if kind == "c":
                        kfs.append(E("KeyFrameColor", {"value": v, "frame": f,
                                                       "interpolationType": "hold" if ease in (None, "hold") else "linear"}))
                    elif kind == "u":
                        kfs.append(E("KeyFrameUint", {"value": v, "frame": f, "interpolationType": "hold"}))
                    elif kind == "b":
                        kfs.append(E("KeyFrameBool", {"value": v, "frame": f, "interpolationType": "hold"}))
                    elif kind == "i":
                        kfs.append(E("KeyFrameId", {"value": v, "frame": f, "interpolationType": "hold"}))
                    else:
                        it, ip = _interp(ease)
                        kfs.append(E("KeyFrameDouble", {"value": v, "frame": f, "interpolationType": it},
                                     [ip] if ip else None))
                if isinstance(prop, int):
                    kps.append(E("KeyedProperty", {"propertyKey": prop}, kfs))
                else:
                    kps.append(E("KeyedProperty", {"property": prop}, kfs))
            objs.append(E("KeyedObject", {"objectId": obj}, kps))
        return E("LinearAnimation", {"loopValue": self.loop, "duration": self.dur, "name": self.name,
                                     "id": self.id}, objs)


# ---------------------------------------------------------------- state machine
def _bp(kind, key, prop_id, value=None, direction=None, conv=None, bid=None):
    tag = {"n": "BindablePropertyNumber", "b": "BindablePropertyBoolean", "t": "BindablePropertyTrigger",
           "s": "BindablePropertyString", "c": "BindablePropertyColor"}[kind]
    keyv = {"n": 636, "b": 634, "t": 686, "s": 635, "c": 638}[kind]
    return tag, keyv


def cond(prop_id, kind, value=None, op=None):
    tag, key = _bp(kind, None, prop_id)
    left = E("TransitionPropertyViewModelComparator", None,
             [E(tag, None, [E("DataBindContext", {"sourcePathIds": path(prop_id), "propertyKey": key})])])
    if kind == "t":
        right = E("TransitionValueTriggerComparator")
    elif kind == "b":
        right = E("TransitionValueBooleanComparator", {"value": value})
    else:
        right = E("TransitionValueNumberComparator", {"value": value})
    return E("TransitionViewModelCondition", {"opValue": op}, [left, right])


def trans(to, conds=None, dur=None, exit_pct=None, early=None, ease=None):
    a = {"stateToId": to, "duration": dur}
    if exit_pct is not None:
        a.update({"enableExitTime": True, "exitTimeIsPercetange": True, "exitTime": exit_pct})
    if early:
        a["enableEarlyExit"] = True
    kids = list(conds or [])
    if ease:
        it, ip = _interp(ease)
        a["interpolationType"] = it
        if ip:
            kids.append(ip)
    return E("StateTransition", a, kids)


def write(prop_id, kind, value):
    tag, key = _bp(kind, None, prop_id)
    a = {"propertyValue": value}
    return E("ListenerViewModelChange", None,
             [E(tag, a, [E("DataBindContext", {"sourcePathIds": path(prop_id), "propertyKey": key,
                                               "direction": True})])])


def fire_trigger(prop_id):
    return write(prop_id, "t", 1)


def toggle(prop_id, negate_conv):
    rid = nid()
    return E("ListenerViewModelChange", {"fromViewModelProperty": True, "fromDataBindId": rid},
             [E("BindablePropertyBoolean", None, [
                 E("DataBindContext", {"sourcePathIds": path(prop_id), "propertyKey": 634, "id": rid,
                                       "converterId": negate_conv}),
                 E("DataBindContext", {"sourcePathIds": path(prop_id), "propertyKey": 634, "direction": True})])])


def copy_str(src, dst):
    rid = nid()
    return E("ListenerViewModelChange", {"fromViewModelProperty": True, "fromDataBindId": rid},
             [E("BindablePropertyString", None, [
                 E("DataBindContext", {"sourcePathIds": path(src), "propertyKey": 635, "id": rid}),
                 E("DataBindContext", {"sourcePathIds": path(dst), "propertyKey": 635, "direction": True})])])


def fire_event(eid, at_end=False):
    return E("StateMachineFireEvent", {"eventId": eid, "occursValue": 1 if at_end else 0})


def astate(sid, anim, x, y, children=None, reset=None, speed=None, caption=None):
    return E("AnimationState", {"x": x, "y": y, "animationId": anim, "reset": reset, "speed": speed,
                                "stateName": caption, "id": sid}, children or [])
