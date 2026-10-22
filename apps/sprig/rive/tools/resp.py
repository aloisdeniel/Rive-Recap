"""Responsive layout kit: a tiny expression language compiled to Rive formula converters.

The artboard's real size reaches the file through scripts/viewport.luau (a fill-sized ScriptedLayout),
which writes private UserRecap properties: _vw, _vh, _dpr, _landscape (= _vw >= layoutBreakpoint),
_tall (= _vh >= 1.1 * _vw) and the arrangement one-hots _rpt/_rpw/_rlw/_rlt. Everything that moves with
the viewport is a data bind on an expression over those values (and the measured copy heights _chN).
Short expressions become DataConverterFormula converters; long ones are solved in the generated
scripts/layoutsolve.luau and bound through private _l... numbers (see bindx / write_solver):

    x = VW / 2 - 195 * S        # Python, at generation time
    place("Art", kids, x=x, y=..., s=S)

Expressions are evaluated here too (ev), so layouts can be checked numerically without rendering.
Defaults of the private properties are the design size (390 x 844, portrait, tall), so every bind is
the identity there and the 390 x 844 file is pixel-identical to the fixed design.
"""
import math

import build_sprig as B
from rml import E, tIn, tV, tOp, tF, tSep, tO, tC, formula


class X:
    __slots__ = ("op", "a")

    def __init__(self, op, *a):
        self.op = op
        self.a = a

    # arithmetic with folding
    def __add__(self, o): return add(self, o)
    def __radd__(self, o): return add(o, self)
    def __sub__(self, o): return sub(self, o)
    def __rsub__(self, o): return sub(o, self)
    def __mul__(self, o): return mul(self, o)
    def __rmul__(self, o): return mul(o, self)
    def __truediv__(self, o): return div(self, o)
    def __rtruediv__(self, o): return div(o, self)
    def __neg__(self): return mul(-1.0, self)

    def key(self):
        if self.op == "c":
            return f"{self.a[0]:.6g}"
        if self.op == "v":
            return self.a[0]
        return f"{self.op}(" + ",".join(w(x).key() for x in self.a) + ")"

    def __repr__(self):
        return self.key()


def w(v):
    return v if isinstance(v, X) else X("c", float(v))


def isc(v, val=None):
    v = w(v)
    return v.op == "c" and (val is None or abs(v.a[0] - val) < 1e-12)


def cv(v):
    return w(v).a[0]


def add(a, b):
    a, b = w(a), w(b)
    if isc(a) and isc(b):
        return w(cv(a) + cv(b))
    if isc(a, 0):
        return b
    if isc(b, 0):
        return a
    return X("+", a, b)


def sub(a, b):
    a, b = w(a), w(b)
    if isc(a) and isc(b):
        return w(cv(a) - cv(b))
    if isc(b, 0):
        return a
    if a.key() == b.key():
        return w(0)
    return X("-", a, b)


def mul(a, b):
    a, b = w(a), w(b)
    if isc(a) and isc(b):
        return w(cv(a) * cv(b))
    if isc(a, 0) or isc(b, 0):
        return w(0)
    if isc(a, 1):
        return b
    if isc(b, 1):
        return a
    return X("*", a, b)


def div(a, b):
    a, b = w(a), w(b)
    if isc(a) and isc(b):
        return w(cv(a) / cv(b))
    if isc(b, 1):
        return a
    if isc(a, 0):
        return w(0)
    return X("/", a, b)


def xmin(*xs):
    xs = [w(x) for x in xs]
    out = xs[0]
    for x in xs[1:]:
        if isc(out) and isc(x):
            out = w(min(cv(out), cv(x)))
        elif out.key() == x.key():
            pass
        else:
            out = X("min", out, x)
    return out


def xmax(*xs):
    xs = [w(x) for x in xs]
    out = xs[0]
    for x in xs[1:]:
        if isc(out) and isc(x):
            out = w(max(cv(out), cv(x)))
        elif out.key() == x.key():
            pass
        else:
            out = X("max", out, x)
    return out


def clamp(x, lo, hi):
    return xmin(xmax(x, lo), hi)


def lerp(a, b, t):
    """(1 - t) * a + t * b with t a 0/1 selector; each operand appears once in the formula."""
    a, b = w(a), w(b)
    if a.key() == b.key():
        return a
    return add(mul(sub(1, t), a), mul(t, b))


VW = X("v", "vw")
VH = X("v", "vh")
L = X("v", "land")     # 1 in the landscape layout (_vw >= layoutBreakpoint)
T = X("v", "tall")     # 1 when _vh >= 1.1 * _vw
DPR = X("v", "dpr")
# regime one-hots, published by scripts/viewport.luau (exactly one is 1)
R_PT = X("v", "rpt")
R_PW = X("v", "rpw")
R_LW = X("v", "rlw")
R_LT = X("v", "rlt")
CS = X("v", "cs")      # current scene (currentScreen), for the few binds that follow the story
SRC = {"vw": "_vw", "vh": "_vh", "land": "_landscape", "tall": "_tall", "dpr": "_dpr", "cs": "currentScreen",
       "rpt": "_rpt", "rpw": "_rpw", "rlw": "_rlw", "rlt": "_rlt"}
# measured copy-column heights (design units), written back by the columns themselves (computedHeight)
for _k in range(1, 11):
    SRC[f"ch{_k}"] = f"_ch{_k}"


def CH(k):
    return X("v", f"ch{k}")


# solver inputs, in order: the probe passes the first six, the rest are read from the view model
SOLVER_IN = ["vw", "vh", "land", "tall", "dpr", "cs"] + [f"ch{k}" for k in range(1, 11)]
BOOL = {"land", "tall"}


def sel(pt, pw, lw, lt):
    """Pick by regime: portrait-tall, portrait-wide, landscape-wide, landscape-tall (each appears once)."""
    pt, pw, lw, lt = w(pt), w(pw), w(lw), w(lt)
    if pt.key() == pw.key() == lw.key() == lt.key():
        return pt
    if pt.key() == pw.key() and lw.key() == lt.key():
        return lerp(pt, lw, L)
    return add(add(mul(R_PT, pt), mul(R_PW, pw)), add(mul(R_LW, lw), mul(R_LT, lt)))


def by_orient(port, land):
    return lerp(port, land, L)


# ------------------------------------------------------------------ evaluation (numeric checks)

def ev(x, env):
    x = w(x)
    o = x.op
    if o == "c":
        return x.a[0]
    if o == "v":
        return env[x.a[0]]
    vals = [ev(a, env) for a in x.a]
    if o == "+":
        return vals[0] + vals[1]
    if o == "-":
        return vals[0] - vals[1]
    if o == "*":
        return vals[0] * vals[1]
    if o == "/":
        return vals[0] / vals[1] if vals[1] else 0.0
    if o == "min":
        return min(vals)
    if o == "max":
        return max(vals)
    raise ValueError(o)


CH_DESIGN = B.CH_DESIGN


def env_for(vw, vh, bp=768, dpr=1.0, cs=1):
    land = 1.0 if vw >= bp else 0.0
    tall = 1.0 if vh >= 1.1 * vw else 0.0
    return {"vw": float(vw), "vh": float(vh), "land": land, "tall": tall, "dpr": dpr, "cs": float(cs),
            "rpt": (1 - land) * tall, "rpw": (1 - land) * (1 - tall), "rlw": land * (1 - tall), "rlt": land * tall,
            **{f"ch{k}": v for k, v in CH_DESIGN.items()}}


DESIGN = env_for(390, 844)

# ------------------------------------------------------------------ compile to a formula converter


def _vars(x, out):
    x = w(x)
    if x.op == "v":
        out.add(x.a[0])
    elif x.op != "c":
        for a in x.a:
            _vars(a, out)
    return out


def _tokens(x, inp):
    x = w(x)
    o = x.op
    if o == "c":
        return [tV(x.a[0])]
    if o == "v":
        n = x.a[0]
        if n == inp:
            return [tIn()]
        conv = B.c_b2n() if n in BOOL else None
        return [tV(bind_el=B.bind(B.P(SRC[n]), 777, conv))]
    if o in ("min", "max"):
        return [tF(o)] + _tokens(x.a[0], inp) + [tSep()] + _tokens(x.a[1], inp) + [tC()]
    return [tO()] + _tokens(x.a[0], inp) + [tOp(o)] + _tokens(x.a[1], inp) + [tC()]


# ------------------------------------------------------------------ large expressions: solved in Luau
# A formula that would be long (min/max over four arrangements) is not compiled into a converter.
# Instead it becomes a private view model number that scripts/layoutsolve.luau (generated below, with
# shared subexpressions computed once) recomputes whenever the viewport, the breakpoint or the scene
# changes; the property bind is then a plain bind. Small expressions stay native formulas.
LIMIT = 40
PROMOTED = {}      # expression key -> (view model property, expression)


def ntok(x, cache=None):
    x = w(x)
    if x.op in ("c", "v"):
        return 1
    return 3 + sum(ntok(a) for a in x.a)


def _promote(expr, name):
    k = expr.key()
    if k in PROMOTED:
        return PROMOTED[k][0]
    base = "_l" + "".join(ch for ch in name.title() if ch.isalnum())
    vm, i = base, 2
    while vm in B.PROPS:
        vm, i = f"{base}{i}", i + 1
    B.prop(vm, "number", float(ev(expr, DESIGN)))
    PROMOTED[k] = (vm, expr)
    return vm


def bindx(key, expr, name="Layout"):
    """A DataBindContext that sets property `key` to expr. Returns None for a constant expression
    (callers set the constant as the attribute instead)."""
    expr = w(expr)
    vs = _vars(expr, set())
    if not vs:
        return None
    if ntok(expr) > LIMIT:
        return B.bind(B.P(_promote(expr, name)), key)
    inp = "vw" if "vw" in vs else sorted(vs)[0]
    toks = _tokens(expr, inp)
    k = expr.key()
    cid = B.CV.add(("resp", k), formula(f"{name}: {k[:80]}", toks))
    conv = cid
    if inp in BOOL:
        conv = B.CV.group(("respb", k), [B.c_b2n(), cid], f"{name} (bool)")
    return B.bind(B.P(SRC[inp]), key, conv)


KEY = {"x": 13, "y": 14, "sx": 16, "sy": 17, "rot": 15, "op": 18, "lc_w": 7, "lc_h": 8, "rect_w": 20, "rect_h": 21,
       "text_w": 285, "vx": 24, "vy": 25, "trim_off": 116, "trim_end": 115, "input": 243, "jx": 303, "jy": 304,
       "jw": 305, "jh": 306}


def apply(el, name="Layout", **props):
    """Bind (or set, when constant) responsive properties on an element. props: x, y, s (uniform), sx, sy,
    lc_w, rect_w, rect_h, text_w, vx, vy, trim_off, input, jx, jy, jw, jh."""
    if "s" in props:
        s = props.pop("s")
        props["sx"] = s
        props["sy"] = s
    attr = {"x": "x", "y": "y", "sx": "scaleX", "sy": "scaleY", "rot": "rotation", "op": "opacity",
            "lc_w": "width", "lc_h": "height", "rect_w": "width", "rect_h": "height", "text_w": "width",
            "vx": "x", "vy": "y", "trim_off": "offset", "input": "propertyValue", "jx": "posX", "jy": "posY",
            "jw": "width", "jh": "height"}
    for p, expr in props.items():
        if expr is None:
            continue
        expr = w(expr)
        b = bindx(KEY[p], expr, f"{name} {p}")
        # the authored value is the design value, so the file reads right before data arrives
        el.attrs[attr[p]] = float(ev(expr, DESIGN))
        if b is not None:
            el.add(b)
    return el


def place(name, *kids, id=None, **props):
    """A plain Node whose transform follows the viewport. Children keep their design coordinates:
    screen = (x + p.x * sx, y + p.y * sy)."""
    n = E("Node", *kids, x=0.0, y=0.0, name=name, id=id or B.ID())
    return apply(n, name, **props)


def fit_box(box, target, ax=0.5, ay=0.5, smin=None, smax=None):
    """Contain-fit design box (x0, y0, x1, y1) into target (x0, y0, x1, y1) of expressions.
    Returns (x, y, s) for place(): the wrapper maps design -> screen."""
    bx0, by0, bx1, by1 = box
    tx0, ty0, tx1, ty1 = target
    s = xmin((tx1 - tx0) / (bx1 - bx0), (ty1 - ty0) / (by1 - by0))
    if smin is not None or smax is not None:
        s = clamp(s, smin if smin is not None else -1e9, smax if smax is not None else 1e9)
    X0 = tx0 + ((tx1 - tx0) - (bx1 - bx0) * s) * ax
    Y0 = ty0 + ((ty1 - ty0) - (by1 - by0) * s) * ay
    return X0 - bx0 * s, Y0 - by0 * s, s


def sel3(pt, pw, lw, lt):
    """sel() over (x, y, s) triples."""
    return tuple(sel(a, b, c, d) for a, b, c, d in zip(pt, pw, lw, lt))


# ------------------------------------------------------------------ Luau code generation

def _lua_num(v):
    return repr(float(v)) if v == v else "0"


def write_solver(path):
    """scripts/layoutsolve.luau: computes every promoted value from the viewport. Generated; do not edit."""
    outs = list(PROMOTED.values())
    # count subexpression uses to share them
    uses = {}
    nodes = {}

    def walk(x):
        x = w(x)
        if x.op in ("c", "v"):
            return
        k = x.key()
        uses[k] = uses.get(k, 0) + 1
        if uses[k] == 1:
            nodes[k] = x
            for a in x.a:
                walk(a)
    for _, e in outs:
        walk(e)
    temps = {}
    lines = []
    used = set()

    def code(x, top=False):
        x = w(x)
        if x.op == "c":
            return _lua_num(x.a[0])
        if x.op == "v":
            used.add(x.a[0])
            return x.a[0]
        k = x.key()
        if k in temps:
            return temps[k]
        a = [code(y) for y in x.a]
        if x.op in ("min", "max"):
            c = f"math.{x.op}({a[0]}, {a[1]})"
        elif x.op == "/":
            c = f"dv({a[0]}, {a[1]})"
        else:
            c = f"({a[0]} {x.op} {a[1]})"
        if not top and uses.get(k, 0) > 1 and ntok(x) > 4:
            i = len(temps) + 1
            temps[k] = f"t[{i}]"
            lines.append(f"    t[{i}] = {c}")
            return temps[k]
        return c

    body = []
    for i, (vm, e) in enumerate(outs, 1):
        c = code(e, top=True)
        lines.append(f"    out[{i}] = {c}")
    names = ",\n".join(f"    '{vm}'" for vm, _ in outs)
    regdef = {"rpt": "(1 - land) * tall", "rpw": "(1 - land) * (1 - tall)", "rlw": "land * (1 - tall)",
              "rlt": "land * tall"}
    regs = [f"    local {r} = {d}" for r, d in regdef.items() if r in used]
    if regs:
        used.update({"land", "tall"})
    src = f"""--!strict
-- GENERATED by tools/resp.py (python3 tools/sprig_main.py) -- do not edit by hand.
--
-- The responsive layout solver. Every placement whose expression is too long for a native formula
-- converter (tools/layout.py describes them) is computed here, once per viewport / breakpoint / scene
-- change, by scripts/viewport.luau, which writes the results into the private UserRecap numbers listed
-- in `names`. Shared subexpressions are computed once (t[]). Division by zero yields 0.
--
--   vw, vh     artboard size (pt)          land, tall   1 / 0 (layout and aspect)
--   dpr        device pixels per point     cs           currentScreen
--   ch1..ch10  each scene's copy column height as laid out (design units, from computedHeight)
--   rpt, rpw, rlw, rlt   one-hot arrangement: portrait tall / wide, landscape wide / tall

local function dv(a: number, b: number): number
    if b == 0 then
        return 0
    end
    return a / b
end

local names: {{string}} = {{
{names},
}}

local t: {{number}} = table.create({max(1, len(temps))}, 0)

local inputs: {{string}} = {{ {", ".join(repr(SRC[n]) for n in SOLVER_IN)} }}

local function solve(inp: {{number}}, out: {{number}})
{chr(10).join(f"    local {n} = inp[{i}]" for i, n in enumerate(SOLVER_IN, 1) if n in used)}
{chr(10).join(regs)}
{chr(10).join(lines)}
end

return {{ names = names, inputs = inputs, solve = solve }}
"""
    with open(path, "w") as f:
        f.write(src)
    return len(outs), len(temps)
