"""Tiny RML authoring helpers used by gen.py.

The .rml files in the project root are the editable source of truth for the
Rive file; this module only exists so the repetitive parts (coins, keyframes,
formula tokens, state-machine boilerplate) are written once.
"""
import math
from xml.sax.saxutils import quoteattr

_next = [100]


def nid():
    _next[0] += 1
    return f"0:{_next[0]}"


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s if s not in ("-0", "") else "0"
    return str(v)


def el(tag, attrs=None, children=None):
    attrs = attrs or {}
    a = "".join(f" {k}={quoteattr(fmt(v))}" for k, v in attrs.items() if v is not None)
    if not children:
        return f"<{tag}{a}/>"
    inner = "\n".join(c for c in children if c)
    return f"<{tag}{a}>\n{inner}\n</{tag}>"


# ---------------------------------------------------------------- palette
GRAPE = "FF5C36BB"
GRAPE_D = "FF432790"
GRAPE_L = "FF7B5AD8"
MINT = "FFBFF4D4"
MINT_D = "FF86D9AE"
PEACH = "FFFFB490"
PEACH_D = "FFE88A62"
INK = "FF241B3C"
CREAM = "FFFFF4DD"
GOLD = "FFFFCB5C"
GOLD_D = "FFE59A2E"
GOLD_L = "FFFFE7A3"
WHITE = "FFFFFFFF"
CLEAR = "00FFFFFF"


def alpha(color, a):
    return f"{int(round(a * 255)):02X}{color[2:]}"


# ---------------------------------------------------------------- paint
def solid(color, bind=None):
    ch = [bind] if bind else None
    return el("SolidColor", {"colorValue": color}, ch)


def fill(color=None, grad=None, bind=None, feather=None, name="Fill", fid=None, rule=None):
    paint = grad if grad else solid(color, bind)
    ch = [paint]
    if feather:
        ch.append(feather)
        rule = "clockwise"
    return el("Fill", {"name": name, "id": fid, "fillRule": rule}, ch)


def stroke(color, th=4, cap="round", join="round", trim=None, bind=None, name="Stroke", sid=None, feather=None):
    ch = [solid(color, bind)]
    if trim:
        ch.append(trim)
    if feather:
        ch.append(feather)
    return el("Stroke", {"thickness": th, "cap": cap, "join": join, "name": name, "id": sid}, ch)


def lin(stops, sx, sy, ex, ey):
    return el("LinearGradient", {"startX": sx, "startY": sy, "endX": ex, "endY": ey},
              [el("GradientStop", {"colorValue": c, "position": p}) for p, c in stops])


def rad(stops, cx, cy, r):
    return el("RadialGradient", {"startX": cx, "startY": cy, "endX": cx + r, "endY": cy},
              [el("GradientStop", {"colorValue": c, "position": p}) for p, c in stops])


def shadow(strength=10, oy=6, color="55241B3C"):
    return fill(color, feather=el("Feather", {"strength": strength, "offsetY": oy}), name="Shadow")


# ---------------------------------------------------------------- geometry
def rect(w, h, r=0, x=0, y=0, ox=0.5, oy=0.5, rid=None, name="Rect", radii=None):
    a = {"x": x, "y": y, "width": w, "height": h, "originX": ox, "originY": oy, "name": name, "id": rid}
    if radii:
        a.update({"cornerRadiusTL": radii[0], "cornerRadiusTR": radii[1], "cornerRadiusBR": radii[2],
                  "cornerRadiusBL": radii[3], "linkCornerRadius": False})
    elif r:
        a["cornerRadiusTL"] = r
    return el("Rectangle", a)


def ellipse(w, h=None, x=0, y=0, eid=None, name="Ellipse"):
    return el("Ellipse", {"x": x, "y": y, "width": w, "height": h if h is not None else w, "name": name, "id": eid})


def star(w, h=None, points=5, inner=0.5, corner=0, x=0, y=0, sid=None, name="Star"):
    return el("Star", {"x": x, "y": y, "width": w, "height": h if h is not None else w, "points": points,
                       "innerRadius": inner, "cornerRadius": corner, "name": name, "id": sid})


def poly(pts, closed=True, cw=True, name="Path", pid=None):
    """pts: list of (x, y) or (x, y, radius) or ('c', x, y, rot, dist)."""
    vs = []
    for p in pts:
        if p[0] == "c":
            vs.append(el("CubicMirroredVertex", {"x": p[1], "y": p[2], "rotation": p[3], "distance": p[4]}))
        elif p[0] == "d":
            _, x, y, ir, idist, orot, odist = p
            vs.append(el("CubicDetachedVertex", {"x": x, "y": y, "inRotation": ir, "inDistance": idist,
                                                  "outRotation": orot, "outDistance": odist}))
        else:
            a = {"x": p[0], "y": p[1]}
            if len(p) > 2:
                a["radius"] = p[2]
            vs.append(el("StraightVertex", a))
    return el("PointsPath", {"isClosed": closed, "isClockwise": cw, "name": name, "id": pid}, vs)


def shape(name, paths, paints, x=0, y=0, sid=None, opacity=None, rot=None, sx=None, sy=None, extra=None):
    ch = list(extra or []) + list(paths) + list(paints)
    return el("Shape", {"x": x, "y": y, "rotation": rot, "scaleX": sx, "scaleY": sy, "opacity": opacity,
                        "name": name, "id": sid}, ch)


def node(name, children, x=0, y=0, nid_=None, opacity=None, rot=None, sx=None, sy=None, binds=None):
    ch = list(binds or []) + list(children)
    return el("Node", {"x": x, "y": y, "rotation": rot, "scaleX": sx, "scaleY": sy, "opacity": opacity,
                       "name": name, "id": nid_}, ch)


def bind(path, key, conv=None, did=None, direction=None):
    return el("DataBindContext", {"sourcePathIds": path, "propertyKey": key, "converterId": conv,
                                  "direction": direction, "id": did})


# ---------------------------------------------------------------- animation
EASES = {
    "out": (0.16, 1.0, 0.3, 1.0),        # expo-ish out
    "in": (0.55, 0.0, 0.85, 0.35),
    "inout": (0.65, 0.0, 0.35, 1.0),
    "soft": (0.33, 0.0, 0.2, 1.0),
    "snap": (0.7, 0.0, 0.1, 1.0),
    "drop": (0.5, 0.0, 0.9, 0.6),        # gravity accelerate
    "rise": (0.1, 0.55, 0.35, 1.0),      # decelerate up
}


class Anim:
    def __init__(self, name, frames, loop=None, aid=None):
        self.name = name
        self.frames = frames
        self.loop = loop
        self.id = aid or nid()
        self.keys = {}  # (obj, prop) -> (kind, [(f, v, ease)])

    def key(self, obj, prop, kfs, kind="double"):
        """kfs: list of (frame, value, ease) ; ease applies to segment leaving the key."""
        norm = []
        for k in kfs:
            if len(k) == 2:
                norm.append((k[0], k[1], "linear"))
            else:
                norm.append(k)
        self.keys[(obj, prop)] = (kind, norm)
        return self

    def hold(self, obj, prop, value, kind="double"):
        return self.key(obj, prop, [(0, value, "hold")], kind)

    def xml(self):
        by_obj = {}
        for (obj, prop), (kind, kfs) in self.keys.items():
            by_obj.setdefault(obj, []).append((prop, kind, kfs))
        kos = []
        for obj, props in by_obj.items():
            kps = []
            for prop, kind, kfs in props:
                frames = []
                for f, v, ease in kfs:
                    tag = {"double": "KeyFrameDouble", "color": "KeyFrameColor", "uint": "KeyFrameUint",
                           "bool": "KeyFrameBool", "id": "KeyFrameId", "string": "KeyFrameString"}[kind]
                    ch = None
                    it = ease
                    if kind != "double" and ease not in ("hold", "linear"):
                        it = "linear"
                    if kind == "double" and ease in EASES:
                        x1, y1, x2, y2 = EASES[ease]
                        ch = [el("CubicEaseInterpolator", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})]
                        it = "cubic"
                    elif kind == "double" and isinstance(ease, tuple):
                        ch = [el("CubicEaseInterpolator", {"x1": ease[0], "y1": ease[1], "x2": ease[2], "y2": ease[3]})]
                        it = "cubic"
                    elif kind == "double" and ease == "elastic":
                        ch = [el("ElasticInterpolator", {"easingValue": 1, "amplitude": 1, "period": 0.35})]
                        it = "elastic"
                    if kind in ("bool", "id"):
                        it = "hold"
                    frames.append(el(tag, {"frame": int(round(f)), "value": v, "interpolationType": it}, ch))
                pk = {"property": prop} if not str(prop).isdigit() else {"propertyKey": prop}
                kps.append(el("KeyedProperty", pk, frames))
            kos.append(el("KeyedObject", {"objectId": obj}, kps))
        return el("LinearAnimation", {"loopValue": self.loop, "fps": 60, "duration": self.frames,
                                      "name": self.name, "id": self.id}, kos or None)


# ---------------------------------------------------------------- formula
class Formula:
    """Compile a tiny infix expression into DataConverterFormula tokens.

    in      -> the bind's incoming value
    $name   -> a UserRecap property (bound FormulaTokenValue)
    numbers, + - * / %, parentheses, min() max() floor() round() ceil() pow()
    Every binary operation is emitted fully parenthesised so precedence never
    depends on the runtime's parser.
    """
    FN = {"min": 0, "max": 1, "round": 2, "ceil": 3, "floor": 4, "sqrt": 5, "pow": 6}
    OP = {"+": 0, "-": 1, "*": 2, "/": 3, "%": 4}

    def __init__(self, src, resolve):
        self.toks = self._lex(src)
        self.i = 0
        self.resolve = resolve
        self.out = []
        self._expr()

    def _lex(self, s):
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c.isspace():
                i += 1
            elif c.isdigit() or c == ".":
                j = i
                while j < len(s) and (s[j].isdigit() or s[j] == "."):
                    j += 1
                out.append(("num", float(s[i:j])))
                i = j
            elif c == "$" or c.isalpha() or c == "_":
                j = i + 1 if c == "$" else i
                while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                    j += 1
                word = s[i:j]
                out.append(("var", word[1:]) if c == "$" else ("id", word))
                i = j
            else:
                out.append(("sym", c))
                i += 1
        return out

    def _peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def _take(self):
        t = self._peek()
        self.i += 1
        return t

    def _expr(self):
        # parse into an AST then emit
        self.ast = self._add()

    def _add(self):
        left = self._mul()
        while self._peek() in (("sym", "+"), ("sym", "-")):
            op = self._take()[1]
            left = ("bin", op, left, self._mul())
        return left

    def _mul(self):
        left = self._unary()
        while self._peek() in (("sym", "*"), ("sym", "/"), ("sym", "%")):
            op = self._take()[1]
            left = ("bin", op, left, self._unary())
        return left

    def _unary(self):
        if self._peek() == ("sym", "-"):
            self._take()
            return ("bin", "*", ("num", -1.0), self._unary())
        return self._atom()

    def _atom(self):
        kind, v = self._take()
        if kind == "num":
            return ("num", v)
        if kind == "var":
            return ("var", v)
        if kind == "id" and v == "in":
            return ("in",)
        if kind == "id":
            assert self._take() == ("sym", "("), v
            args = [self._add()]
            while self._peek() == ("sym", ","):
                self._take()
                args.append(self._add())
            assert self._take() == ("sym", ")")
            return ("fn", v, args)
        if (kind, v) == ("sym", "("):
            e = self._add()
            assert self._take() == ("sym", ")")
            return e
        raise ValueError(f"bad token {kind} {v}")

    def emit(self, n=None):
        n = n or self.ast
        t = []
        if n[0] == "num":
            t.append(el("FormulaTokenValue", {"operationValue": n[1]}))
        elif n[0] == "var":
            t.append(el("FormulaTokenValue", {"operationValue": 0}, [bind(self.resolve(n[1]), 777)]))
        elif n[0] == "in":
            t.append(el("FormulaTokenInput"))
        elif n[0] == "fn":
            t.append(el("FormulaTokenFunction", {"functionType": self.FN[n[1]]}))
            for k, a in enumerate(n[2]):
                if k:
                    t.append(el("FormulaTokenArgumentSeparator"))
                t += self.emit(a)
            t.append(el("FormulaTokenParenthesisClose"))
        elif n[0] == "bin":
            t.append(el("FormulaTokenParenthesisOpen"))
            t += self.emit(n[2])
            t.append(el("FormulaTokenOperation", {"operationType": self.OP[n[1]]}))
            t += self.emit(n[3])
            t.append(el("FormulaTokenParenthesisClose"))
        return t
