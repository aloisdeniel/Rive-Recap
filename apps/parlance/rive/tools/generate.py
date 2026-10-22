#!/usr/bin/env python3
"""Generates the Parlance recap RML (scene.rml, components.rml, data.rml).

Run:  python3 tools/generate.py   (from apps/parlance/rive)

The generated RML is the editable source of truth for the Rive file; this
script exists because ten scenes x (enter / back-enter / reduced-motion /
exit / back-exit / idle) timelines and a ~110-state sequencing graph are far
easier to keep consistent from one description than by hand.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rml  # noqa: E402
from rml import (E, nid, node, shape, rect, ellipse, smooth_path, fill, stroke, solid, text, tstyle, run,
                 bind, Anim, cond, trans, write, fire_trigger, toggle, copy_str, fire_event, astate,
                 cubic_path, key_morph, lingrad, cubic_attrs)  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 390, 844
CX = W / 2

# ---------------------------------------------------------------- palette
P = "FFF36A43"   # persimmon
PD = "FFD9532E"  # persimmon dark
PL = "FFF89A7C"  # persimmon light
L = "FFC7B7F2"   # lilac
LD = "FFA894E6"  # lilac dark
LL = "FFE3DAFA"  # lilac light
D = "FF3D2456"   # deep plum
DD = "FF2A1640"  # plum ink (contrast on persimmon)
DL = "FF5B3D7A"  # plum light
Y = "FFF6E97C"   # lemon
YD = "FFE2D15A"
WP = "FFFFF8EC"  # paper
WD = "FFF1E5CF"
CLEAR = "00FFFFFF"

# ---------------------------------------------------------------- fixture
FIX = json.load(open(os.path.join(ROOT, "fixtures", "sample.json")))

# ---------------------------------------------------------------- view model
VM = "0:100"
rml.VM_ID = VM
PROPS = {}      # name -> (id, kind, default)
_pid = [100]


def prop(name, kind, default):
    _pid[0] += 1
    PROPS[name] = (f"0:{_pid[0]}", kind, default)
    return PROPS[name][0]


def argb(hexrgb):
    return "FF" + hexrgb.lstrip("#").upper()


contract = [
    ("userName", "s"), ("year", "n"), ("periodLabel", "s"), ("locale", "s"),
    ("conversations", "n"), ("practiceMinutes", "n"), ("phrasesSaved", "n"), ("topicsExplored", "n"),
    ("languagesPractised", "n"), ("longestStreakDays", "n"), ("voiceNotes", "n"),
    ("personaIndex", "n"), ("personaName", "s"), ("personaDescription", "s"), ("personaColor", "c"),
    ("autoAdvanceSeconds", "n"), ("autoAdvanceEnabled", "b"), ("isPaused", "b"), ("reducedMotion", "b"),
    ("soundEnabled", "b"), ("currentScreen", "n"), ("screenProgress", "n"), ("shareIncludeName", "b"),
    ("shareIncludeSensitiveValues", "b"), ("continueLabel", "s"), ("previousLabel", "s"), ("pauseLabel", "s"),
    ("playLabel", "s"), ("shareLabel", "s"), ("replayLabel", "s"), ("introHeadline", "s"),
    ("introSupport", "s"), ("summaryHeadline", "s"), ("summarySupport", "s"), ("emptyHeadline", "s"),
    ("emptySupport", "s"), ("personaLabel", "s"),
] + [(f"showScreen{i}", "b") for i in range(1, 11)] + sum(
    [[(f"screen{i}Headline", "s"), (f"screen{i}Support", "s"), (f"screen{i}Unit", "s")] for i in range(2, 9)], [])

for name, kind in contract:
    v = FIX[name]
    if kind == "c":
        v = argb(v)
    prop(name, kind, v)

PERSONAS = [
    ("Conversation Starter", "A hello can open a world.", "#C7B7F2"),
    ("Phrase Collector", "You keep useful words close.", "#3D2456"),
    ("Careful Listener", "You give another voice your attention.", "#F6E97C"),
    ("Brave Improviser", "You make room to try a new expression.", "#FFF8EC"),
]
# adapter additions (documented in README)
prop("groupSeparator", "s", ",")
for k, (nm, ds, _c) in enumerate(PERSONAS):
    prop(f"personaName{k}", "s", nm)
    prop(f"personaDescription{k}", "s", ds)
prop("goNext", "t", None)
prop("goPrevious", "t", None)
prop("requestReplay", "t", None)
# private runtime state (underscore = internal, not part of the host contract)
prop("_dwellStart", "t", None)
prop("_dwellStop", "t", None)
prop("_heroReveal", "n", 1)
prop("_focusIndex", "n", 0)
prop("_pointerDown", "b", False)
prop("_pressSide", "n", 0)
prop("_finishedLatch", "b", False)
prop("_mouthTap", "t", None)
prop("_focusVisible", "n", 0)   # 1 after Tab / Shift+Tab, 0 after any pointer press: a :focus-visible ring
# responsive layout (contract addition: layoutBreakpoint is host-writable; the rest are the file's own solver state)
prop("layoutBreakpoint", "n", 768)  # landscape layout when the artboard is at least this wide
prop("_vw", "n", 390)            # artboard width, written by the root layout box (computedWidth, target -> source)
prop("_vh", "n", 844)            # artboard height
prop("_land", "n", 0)            # 1 = landscape layout (_vw >= layoutBreakpoint)
prop("_split", "n", 0)           # 1 = copy and art side by side (landscape, or a portrait canvas wider than tall)
prop("_k", "n", 1)               # chrome / control scale
prop("_m", "n", 24)              # side margin
prop("_top", "n", 80)            # content band top (below wordmark + progress)
prop("_bot", "n", 764)           # content band bottom (above the control bar)
prop("_sc", "n", 1)              # copy scale of the stacked portrait arrangement
prop("_mixA", "n", 1)            # motif A frame: 0 = scene art space, 1 = full-viewport cover space (keyed)
prop("_mixB", "n", 1)
prop("_motifMap", "n", 1)        # which scene's art space the motif frames use (1, 2, 3 or 9; keyed)
prop("_mixMouth", "n", 0)        # scene 3 mouth: 0 = art space, 1 = cover space (signature 3->4)
for _n in (1, 2, 3, 9):          # art-space frames of the scenes the motif visits (x, y, scale), shared by several frames
    for _c in "xys":
        prop(f"_a{_n}{_c}", "n", 1 if _c == "s" else 0)


def V(name):
    return PROPS[name][0]


# ---------------------------------------------------------------- converters
CONV = []


def conv(xml):
    CONV.append(xml)


C_STR0 = nid()
conv(E("DataConverterToString", {"decimals": 0, "round": True, "name": "Integer text", "id": C_STR0}))
C_PAD3 = nid()
conv(E("DataConverterStringPad", {"length": 3, "text": "0", "padType": 0, "name": "Pad 3", "id": C_PAD3}))
C_NOT = nid()
conv(E("DataConverterBooleanNegate", {"name": "Not", "id": C_NOT}))

FN = {"min": 0, "max": 1, "round": 2, "ceil": 3, "floor": 4, "pow": 6}
OPS = {"+": 0, "-": 1, "*": 2, "/": 3, "%": 4}


PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2}


def ftok(ex, parent=None, right=False):
    if ex == "in":
        return [E("FormulaTokenInput")]
    if isinstance(ex, (int, float)):
        return [E("FormulaTokenValue", {"operationValue": ex})]
    if ex[0] == "vm":
        return [E("FormulaTokenValue", None, [E("DataBindContext", {"sourcePathIds": rml.path(ex[1]),
                                                                   "propertyKey": 777})])]
    if ex[0] == "fn":
        out = [E("FormulaTokenFunction", {"functionType": FN[ex[1]]})]
        for i, a in enumerate(ex[2:]):
            if i:
                out.append(E("FormulaTokenArgumentSeparator"))
            out += ftok(a)
        return out + [E("FormulaTokenParenthesisClose")]
    # binary op: the evaluator uses standard precedence and left associativity, so brackets are emitted only where
    # the tree needs them (keeps the layout formulas small)
    a, op, b = ex
    out = ftok(a, op, False) + [E("FormulaTokenOperation", {"operationType": OPS[op]})] + ftok(b, op, True)
    if parent is not None:
        p, q = PREC[op], PREC[parent]
        if p < q or (p == q and (right and parent in "-/%" or "%" in (op, parent))):
            out = [E("FormulaTokenParenthesisOpen")] + out + [E("FormulaTokenParenthesisClose")]
    return out


def formula(name, ex):
    cid = nid()
    conv(E("DataConverterFormula", {"name": name, "id": cid}, ftok(ex)))
    return cid


def group(name, ids):
    cid = nid()
    conv(E("DataConverterGroup", {"name": name, "id": cid},
           [E("DataConverterGroupItem", {"converterId": i}) for i in ids]))
    return cid


def fmin(a, b):
    return ("fn", "min", a, b)


def fmax(a, b):
    return ("fn", "max", a, b)


def floor(a):
    return ("fn", "floor", a)


T = ("vm", V("_heroReveal"))


# ---------------------------------------------------------------- responsive layout expressions
# Ex wraps the formula AST used by ftok() with arithmetic operators and constant folding, so the layout rules
# below read as maths. Every bind built from an Ex becomes one DataConverterFormula whose tokens read the view
# model directly (FormulaTokenValue + DataBindContext), so it re-evaluates whenever any input changes.
class Ex:
    __slots__ = ("a",)

    def __init__(self, a):
        self.a = a.a if isinstance(a, Ex) else a

    def num(self):
        return self.a if isinstance(self.a, (int, float)) and not isinstance(self.a, bool) else None

    def _bin(self, o, op, rev=False):
        o = Ex(o)
        l, r = (o, self) if rev else (self, o)
        ln, rn = l.num(), r.num()
        if ln is not None and rn is not None:
            return Ex({"+": ln + rn, "-": ln - rn, "*": ln * rn, "/": ln / rn}[op])
        if op == "+" and ln == 0:
            return r
        if op in "+-" and rn == 0:
            return l
        if op == "*" and (ln == 0 or rn == 0):
            return Ex(0)
        if op == "*" and ln == 1:
            return r
        if op in "*/" and rn == 1:
            return l
        return Ex((l.a, op, r.a))

    def __add__(self, o): return self._bin(o, "+")
    def __radd__(self, o): return self._bin(o, "+", True)
    def __sub__(self, o): return self._bin(o, "-")
    def __rsub__(self, o): return self._bin(o, "-", True)
    def __mul__(self, o): return self._bin(o, "*")
    def __rmul__(self, o): return self._bin(o, "*", True)
    def __truediv__(self, o): return self._bin(o, "/")
    def __rtruediv__(self, o): return self._bin(o, "/", True)
    def __neg__(self): return self._bin(-1, "*")


def xmin(a, b):
    a, b = Ex(a), Ex(b)
    if a.num() is not None and b.num() is not None:
        return Ex(min(a.num(), b.num()))
    return Ex(("fn", "min", a.a, b.a))


def xmax(a, b):
    a, b = Ex(a), Ex(b)
    if a.num() is not None and b.num() is not None:
        return Ex(max(a.num(), b.num()))
    return Ex(("fn", "max", a.a, b.a))


def xclamp(x, lo, hi):
    return xmin(hi, xmax(lo, x))


def xfloor(x):
    return Ex(("fn", "floor", Ex(x).a))


def xstep(x):
    """1 when x >= 0, else 0."""
    return xmin(1, xmax(0, xfloor(x) + 1))


def xabs(x):
    return xmax(x, -Ex(x))


def xlerp(a, b, t):
    a, b, t = Ex(a), Ex(b), Ex(t)
    if t.num() == 0:
        return a
    if t.num() == 1:
        return b
    if a.num() is not None and b.num() is not None and a.num() == b.num():
        return a
    if a.num() == 0:
        return b * t
    return a * (1 - t) + b * t


def xhat(x):
    """Tent: 1 at x = 0, falling to 0 at |x| >= 1."""
    return xmax(0, 1 - xabs(x))


def vmx(name):
    return Ex(("vm", V(name)))


_FCACHE = {}


def fx(name, e):
    """One formula converter per distinct expression (deduplicated)."""
    e = Ex(e)
    key = repr(e.a)
    if key not in _FCACHE:
        _FCACHE[key] = formula(name, e.a if not isinstance(e.a, (int, float)) else (e.a, "+", 0))
    return _FCACHE[key]


def lbind(key, e, name="layout"):
    """Bind a component property (propertyKey) to a layout expression. The source is _vw so the bind re-runs on
    resize; the formula itself reads every input it needs."""
    return bind(V("_vw"), key, fx(name, e))


def tier_converters(tag, X):
    """Locale-grouped integer display in three tiers (<1e3, <1e6, >=1e6)."""
    c = {}
    c["small"] = group(f"{tag} small", [formula(f"{tag} X", X), C_STR0])
    c["k"] = group(f"{tag} thousands", [formula(f"{tag} floor(X/1e3)", floor((X, "/", 1000))), C_STR0])
    c["r3"] = group(f"{tag} rest3", [formula(f"{tag} X mod 1e3", (X, "%", 1000)), C_STR0, C_PAD3])
    c["m"] = group(f"{tag} millions", [formula(f"{tag} floor(X/1e6)", floor((X, "/", 1000000))), C_STR0])
    c["k3"] = group(f"{tag} thousands3", [formula(f"{tag} floor(X/1e3) mod 1e3", (floor((X, "/", 1000)), "%", 1000)),
                                          C_STR0, C_PAD3])
    has_k = fmin(1, floor((X, "/", 1000)))
    has_m = fmin(1, floor((X, "/", 1000000)))
    c["op_small"] = formula(f"{tag} tier small", (1, "-", has_k))
    c["op_mid"] = formula(f"{tag} tier mid", (has_k, "-", has_m))
    c["op_large"] = has_m and formula(f"{tag} tier large", has_m)
    return c


X_COUNT = ("fn", "round", (fmax(0, "in"), "*", T))       # counting value (hero)
X_STATIC = ("fn", "round", fmax(0, "in"))               # settled value (summary)
TC = tier_converters("Hero", X_COUNT)
TS = tier_converters("Static", X_STATIC)

C_CLOCK = formula("Dwell speed = 1/clamp(s,4,60)", (1, "/", fmax(4, fmin(60, "in"))))
C_SEG = [None] + [formula(f"Segment {k} fill", fmax(0, fmin(1, ((("in", "+", ("vm", V("screenProgress"))), "-", k), "+",
                                                                 floor(("in", "/", 10))))))
                  for k in range(1, 11)]
C_RIB2 = formula("Ribbon 2 if >=2", fmax(0, fmin(1, ("in", "-", 1))))
C_RIB3 = formula("Ribbon 3 if >=3", fmax(0, fmin(1, ("in", "-", 2))))
C_FOCUS = [formula(f"Focus ring {k}", (fmax(0, (1, "-", fmin(1, (("in", "-", k), "*", ("in", "-", k))))), "*",
                                        ("vm", V("_focusVisible"))))
           for k in range(0, 6)]

# ---------------------------------------------------------------- assets / fonts
F_DISP = nid()
F_TEXT = nid()
F_CJK = nid()
GRAIN = nid()
FONTS = [E("FontAsset", {"file": "assets/fonts/BricolageGrotesque-VF.ttf", "name": "Bricolage Grotesque",
                         "id": F_DISP}),
         E("FontAsset", {"file": "assets/fonts/NotoSans-wght400-700.ttf", "name": "Noto Sans", "id": F_TEXT}),
         # 5 KB subset (ありがとう 안녕 감사) of Noto Sans KR @600 for the two CJK word blocks in scene 4
         E("FontAsset", {"file": "assets/fonts/NotoSansKR-600-subset.ttf", "name": "Noto Sans KR subset", "id": F_CJK}),
         # restrained paper grain (tools/grain.py), drawn with the overlay blend under live copy
         E("ImageAsset", {"file": "assets/images/grain.png", "name": "Paper grain", "id": GRAIN})]


def disp(size, color, wght=800, wdth=None, cid=None, cbinds=None, lh=None, ls=None, sid=None, axis_ids=None):
    sid = sid or nid()
    style = {800: "ExtraBold", 700: "Bold", 600: "SemiBold", 500: "Medium", 400: "Regular"}.get(wght, "Custom")
    return sid, tstyle(sid, F_DISP, size, color, wght=wght, wdth=wdth, opsz=min(96, max(12, size)), cid=cid,
                       cbinds=cbinds, lh=lh, ls=ls, family="Bricolage Grotesque", style=style, axis_ids=axis_ids)


def body(size, color, wght=400, cid=None, cbinds=None, lh=None, sid=None, font=None):
    sid = sid or nid()
    style = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}.get(wght, "Custom")
    if font == F_CJK:
        return sid, tstyle(sid, F_CJK, size, color, cid=cid, lh=lh, family="Noto Sans KR", style="SemiBold")
    return sid, tstyle(sid, F_TEXT, size, color, wght=wght, cid=cid, cbinds=cbinds, lh=lh,
                       family="Noto Sans", style=style)


def bound_text(name, x, y, w, prop_name, font="disp", size=30, color=D, wght=800, lh=None, align=None,
               h=None, sizing="autoHeight", overflow=None, wrap="wrap", tid=None, cid=None, literal=None,
               op=None, conv_id=None, wdth=None, ls=None, valign=None, mods=None, axis_ids=None):
    tid = tid or nid()
    cid = cid or nid()
    if font == "disp":
        sid, st = disp(size, color, wght, cid=cid, lh=lh, wdth=wdth, ls=ls, axis_ids=axis_ids)
    else:
        sid, st = body(size, color, wght, cid=cid, lh=lh)
    lit = literal if literal is not None else str(PROPS[prop_name][2])
    return tid, cid, text(name, x, y, [st], [run(sid, lit, [bind(V(prop_name), 268, conv_id)])], id=tid, w=w,
                          h=h, sizing=sizing, overflow=overflow, wrap=wrap, align=align, op=op, valign=valign,
                          extra_children=mods)


HERO_AX = {}  # hero node id -> wdth axis ids of its three tiers (keyed so digits stretch while counting)


def hero_number(name, prop_name, x, y, w, size, color, align=None, counting=True, wdth=88, wght=800, ls=None):
    """Three tier texts (<1,000 / <1,000,000 / larger) inside one node. Returns (node_id, xml, color ids)."""
    tc = TC if counting else TS
    nid_ = nid()
    sep = V("groupSeparator")
    src = V(prop_name)
    kids, cids = [], []
    hh = size * 1.12
    HERO_AX[nid_] = []

    def tier(label, runs_spec, op_conv):
        cid = nid()
        ax = nid()
        HERO_AX[nid_].append(ax)
        sid, st = disp(size, color, wght, wdth=wdth, cid=cid, lh=size * 1.0, ls=ls, axis_ids={"wdth": ax})
        runs = []
        for kind, cv in runs_spec:
            if kind == "sep":
                runs.append(run(sid, ",", [bind(sep, 268)], name="Separator"))
            else:
                runs.append(run(sid, "0", [bind(src, 268, cv)], name=kind))
        cids.append(cid)
        kids.append(text(f"{name} {label}", 0, 0, [st], runs, w=w, h=hh, sizing="fixed", overflow="fitFontSize",
                         wrap="noWrap", align=align, binds=[bind(src, 18, op_conv)], id=nid()))

    tier("<1k", [("value", tc["small"])], tc["op_small"])
    tier("<1M", [("thousands", tc["k"]), ("sep", None), ("rest", tc["r3"])], tc["op_mid"])
    tier(">=1M", [("millions", tc["m"]), ("sep", None), ("thousands", tc["k3"]), ("sep", None), ("rest", tc["r3"])],
         tc["op_large"])
    return nid_, node(name, kids, id=nid_, x=x, y=y), cids


# ---------------------------------------------------------------- motif art
# The hero motif: two oversized speech forms shaped like punctuation -- a round head whose tail sweeps down like a
# comma. Bodies that take part in transitions are all-cubic 10-vertex paths so they truly morph (rest ->
# anticipation squash -> elongated cover and back) by keying every vertex, not just by scaling.
BUB_REST = [(0, -100), (72, -72), (102, -2), (102, 70), (132, 168, "c", 5), (44, 116), (-6, 102), (-72, 72),
            (-102, 0), (-72, -72)]
BUB_SQUASH = [(0, -82), (84, -60), (116, 2), (110, 58), (150, 140, "c", 5), (62, 98), (-6, 94), (-84, 68),
              (-116, 2), (-84, -60)]
BUB_TALL = [(0, -132), (82, -100), (110, -6), (106, 130), (150, 340, "c", 5), (66, 254), (-6, 246), (-82, 198),
            (-110, 40), (-82, -96)]

# travelling stretch (squash-and-stretch while a form is carried): 40% of the way from rest to the cover shape
BUB_STRETCH = [tuple([round(r[0] + (t[0] - r[0]) * 0.4, 2), round(r[1] + (t[1] - r[1]) * 0.4, 2)]) + tuple(r[2:])
               for r, t in zip(BUB_REST, BUB_TALL)]


def bub(pts, s=1.0, mirror=False):
    out = []
    for p in pts:
        x, y = p[0] * s, p[1] * s
        out.append(((-x if mirror else x), y) + tuple(p[2:]))
    if mirror:
        out = [out[0]] + out[1:][::-1]
    return out


def bubble_pts(s=1.0, mirror=False):
    return bub(BUB_REST, s, mirror)


def shade_fills(color, shade, light, s=1.0, grad=True):
    """Soft tactile shading in place of flat colour: a diagonal light->base->shade gradient plus an inner shadow
    on the lower-right rim (Feather inner). Both paints sit on the body itself so they follow its morphs."""
    base = fill(None, grad=lingrad([(light, 0), (color, 0.42), (color, 0.7), (shade, 1)], -80 * s, -110 * s,
                                   100 * s, 160 * s)) if grad else fill(color)
    inner = E("Fill", {"fillRule": "clockwise", "name": "Inner shade"}, [
        solid("99" + shade[2:]),
        E("Feather", {"strength": 22 * s, "offsetX": -10 * s, "offsetY": -14 * s, "inner": True, "spaceValue": "local",
                      "name": "Feather"})])
    return [base, inner]


# ================================================================ FACE RIG
def _pack(ws):
    """ws: [(tendon index 0-based, weight 0..1)] -> (indices, values) packed, values summing to 255."""
    ws = [w for w in ws if w[1] > 0]
    vals = [int(round(w * 255)) for _t, w in ws]
    vals[vals.index(max(vals))] += 255 - sum(vals)
    ind = sum((t + 1) << (8 * k) for k, (t, _w) in enumerate(ws))
    val = sum(v << (8 * k) for k, v in enumerate(vals))
    return ind, val


def skinned_path(attrs, weights, bones, name="Path", closed=True):
    """attrs: cubic vertex attribute dicts (in the bind frame); weights: per vertex [(tendon, w)];
    bones: [(bone id, bind x, bind y)] -- bind poses are pure translations in the same frame."""
    verts = []
    for a, w in zip(attrs, weights):
        w, wi, wo = w if isinstance(w, tuple) else (w, w, w)
        ind, val = _pack(w)
        ii, iv = _pack(wi)
        oi, ov = _pack(wo)
        verts.append(E("CubicDetachedVertex", {k: round(v, 4) for k, v in a.items()}, [
            E("CubicWeight", {"values": val, "indices": ind, "inValues": iv, "inIndices": ii, "outValues": ov,
                              "outIndices": oi})]))
    skin = E("Skin", {"name": "Skin"}, [E("Tendon", {"boneId": b, "tx": round(x, 4), "ty": round(y, 4), "name": "Tendon"})
                                        for b, x, y in bones])
    return E("PointsPath", {"isClosed": closed, "isClockwise": True, "name": name}, verts + [skin])


def ellipse_attrs(cx, cy, a, b, n=6, start=math.pi):
    k = 4 / 3 * math.tan(math.pi / (2 * n))
    out = []
    for i in range(n):
        t = start + i * 2 * math.pi / n
        x, y = cx + a * math.cos(t), cy + b * math.sin(t)
        tx, ty = -a * math.sin(t), b * math.cos(t)
        d = k * math.hypot(tx, ty)
        out.append({"x": x, "y": y, "inRotation": math.atan2(-ty, -tx), "inDistance": d,
                    "outRotation": math.atan2(ty, tx), "outDistance": d})
    return out


def bone(name, x, y, kids=(), id=None):
    return E("RootBone", {"x": round(x, 4), "y": round(y, 4), "length": 4, "name": name, "id": id}, list(kids))


# mouth bind pose (laughing D, before the 1.16 mouth scale): corners, upper lip, lower lip
MOUTH_PTS = [(-54, 0, "c", 9), (-27, -3), (0, -4), (27, -3), (54, 0, "c", 9), (42, 36), (0, 58), (-42, 36)]
# tendons: 0 upper lip, 1 jaw, 2 corner L, 3 corner R
MOUTH_W = [[(2, 0.8), (1, 0.2)], [(0, 0.7), (2, 0.3)], [(0, 1)], [(0, 0.7), (3, 0.3)], [(3, 0.8), (1, 0.2)],
           [(1, 0.7), (3, 0.3)], [(1, 1)], [(1, 0.7), (2, 0.3)]]
TONGUE_PTS = [(-40, 66), (-33, 47), (-17, 35), (0, 32), (17, 35), (33, 47), (40, 66), (0, 80)]
# tendons: 0 tongue root, 1 tongue tip
TONGUE_W = [[(0, 1)], [(0, 0.6), (1, 0.4)], [(1, 1)], [(1, 1)], [(1, 1)], [(0, 0.6), (1, 0.4)], [(0, 1)], [(0, 1)]]
EYE_X, EYE_Y, EYE_A, EYE_B = 34, -40, 10, 12.5
# eye tendons: 0 upper lids, 1 lower lids, 2 left corners, 3 right corners (shared by both eyes, translation only)
# 4 = lid crease: carries the inward handles of the lower lid, so a squint's lower edge arches up instead of sagging
EYE_W = [[(2, 1)], [(0, 1)], [(0, 1)], [(3, 1)], ([(1, 1)], [(1, 1)], [(4, 1)]), ([(1, 1)], [(4, 1)], [(1, 1)])]


def face(prefix, s=1.0, ink=DD, tongue=PD, ids=None, look=0, cheek="70FF5C7A", rigged=True):
    """Rigged laughing face. Mouth: a skinned D-shape (upper lip, jaw and two corner bones) with teeth and a
    skinned two-bone tongue clipped inside it. Eyes: two skinned ovals on four shared lid/corner bones (open,
    blink, happy squint), glints, brows, gaze. Cheeks and lips are follow-through nodes."""
    ids = ids if ids is not None else {}
    # a static face (the share cards' emblems) is the same art at rest with no skin, bones or keys
    skinned_path_ = skinned_path if rigged else (lambda attrs, *_a: E("PointsPath", {"isClosed": True, "name": "Path"}, [
        E("CubicDetachedVertex", {k: round(v, 4) for k, v in a.items()}) for a in attrs]))
    bone = globals()["bone"] if rigged else (lambda name, x, y, kids=(), id=None: node(name, list(kids), id=id, x=round(x, 4),
                                                                                        y=round(y, 4)))
    R = {k: nid() for k in ("JO", "U", "J", "CL", "CR", "TB", "TT", "teeth", "lips", "mshape", "EU", "ED", "ECL", "ECR",
                            "EA", "gaze", "glints", "browL", "browR", "cheeks")}
    R["s"], R["S"] = s, s * 1.16
    ids["rig"] = R
    ids["mouth"] = nid()
    ids["eyes"] = nid()
    S = R["S"]
    sc = lambda pts: [(p[0] * S, p[1] * S) + tuple(p[2:]) for p in pts]
    # ---- mouth (frame = lips node)
    m_attrs = cubic_attrs(sc(MOUTH_PTS))
    mshape = shape(f"{prefix} mouth shape", [skinned_path_(m_attrs, MOUTH_W, [(R["U"], 0, 0), (R["J"], 0, 0),
                                                                              (R["CL"], -54 * S, 0), (R["CR"], 54 * S, 0)])],
                   [fill(ink)], id=R["mshape"])
    teeth = shape(f"{prefix} teeth", [smooth_path(sc([(-62, -10), (62, -10), (62, 10), (33, 16), (0, 19), (-33, 16),
                                                      (-62, 10)]))], [fill(WP)], id=R["teeth"])
    t_attrs = cubic_attrs(sc(TONGUE_PTS))
    tshape = shape(f"{prefix} tongue", [skinned_path_(t_attrs, TONGUE_W, [(R["TB"], 0, 62 * S), (R["TT"], 0, 40 * S)])],
                   [fill(tongue)])
    crease = shape(f"{prefix} tongue crease", [smooth_path([(0, -1 * S), (0, 11 * S)], closed=False)],
                   [stroke("44000000", 3.2 * S)])
    tip = bone(f"{prefix} tongue tip", 0, -22 * S, [crease], id=R["TT"])
    root = bone(f"{prefix} tongue root", 0, 62 * S, [tip], id=R["TB"])
    inside = node(f"{prefix} mouth inside", [
        E("ClippingShape", {"sourceId": R["mshape"], "name": "Mouth clip"}),
        bone(f"{prefix} upper lip", 0, 0, [teeth], id=R["U"]),
        # the jaw sits in a "jaw override" bone that only transitions key, so a carry can open the mouth wider
        # whatever the idle conversation (a later state machine layer) is doing with the jaw itself
        bone(f"{prefix} jaw override", 0, 0, [bone(f"{prefix} jaw", 0, 0, [root], id=R["J"])], id=R["JO"]),
        tshape,
        bone(f"{prefix} corner L", -54 * S, 0, id=R["CL"]),
        bone(f"{prefix} corner R", 54 * S, 0, id=R["CR"]),
    ])
    lips = node(f"{prefix} lips", [inside, mshape], id=R["lips"])
    mouth = node(f"{prefix} mouth", [lips], id=ids["mouth"], x=look * s)
    # ---- eyes (frame = gaze node)
    eyes = []
    glints = []
    for side in (-1, 1):
        ea = ellipse_attrs(side * EYE_X * s, EYE_Y * s, EYE_A * s, EYE_B * s)
        eyes.append(shape(f"{prefix} eye", [skinned_path_(ea, EYE_W, [(R["EU"], 0, 0), (R["ED"], 0, 0), (R["ECL"], 0, 0),
                                                                     (R["ECR"], 0, 0), (R["EA"], 0, 0)])], [fill(ink)]))
        glints.append(shape(f"{prefix} glint", [ellipse(5.5 * s, 5.5 * s)], [fill(WP)],
                            x=(side * EYE_X + 3.5) * s, y=(EYE_Y - 5) * s))
    brows = []
    for side, bid in ((-1, R["browL"]), (1, R["browR"])):
        brows.append(node(f"{prefix} brow", [shape(f"{prefix} brow line", [smooth_path(
            [(-10 * s, 2.5 * s), (0, -2.5 * s), (10 * s, 2.5 * s)], closed=False)], [stroke(ink, 5.5 * s)])],
            id=bid, x=side * (EYE_X + 2) * s, y=(EYE_Y - 26) * s))
    gaze = node(f"{prefix} gaze", brows + [node(f"{prefix} glints", glints, id=R["glints"])] + eyes + [
        bone(f"{prefix} upper lids", 0, 0, id=R["EU"]), bone(f"{prefix} lower lids", 0, 0, id=R["ED"]),
        bone(f"{prefix} eye corners L", 0, 0, id=R["ECL"]), bone(f"{prefix} eye corners R", 0, 0, id=R["ECR"]),
        bone(f"{prefix} lid crease", 0, 0, id=R["EA"])],
        id=R["gaze"])
    eyes_n = node(f"{prefix} eyes", [gaze], id=ids["eyes"], x=look * s)
    cheeks = node(f"{prefix} cheeks", [shape(f"{prefix} cheek", [ellipse(30 * s, 15 * s)], [fill(cheek, feather=(5 * s,))],
                                             x=side * 66 * s, y=-14 * s) for side in (-1, 1)], id=R["cheeks"])
    return node(f"{prefix} face", [eyes_n, mouth, cheeks], id=ids.get("face"))


# ---------------------------------------------------------------- face channels and choreography
# channel -> [(rig key, property, unit)]; unit: 1 (unitless), "S" mouth scale, "s" face scale (negative = mirrored)
FACE_CH = {
    "open": [("J", "scaleY", 1)], "jo": [("JO", "y", "S")], "drop": [("J", "y", "S")], "narrow": [("J", "scaleX", 1)], "tilt": [("J", "rotation", 1)],
    "smile": [("CL", "y", "S"), ("CR", "y", "S")], "wide": [("CL", "x", "-S"), ("CR", "x", "S")], "lift": [("U", "y", "S")],
    "teeth": [("teeth", "y", "S")],
    "tlift": [("TT", "y", "S")], "tcurl": [("TT", "scaleX", 1)], "twig": [("TT", "rotation", 1)], "tx": [("TB", "x", "S")],
    "trot": [("TB", "rotation", 1)],
    "eu": [("EU", "y", "s")], "ed": [("ED", "y", "s")], "ecx": [("ECL", "x", "-s"), ("ECR", "x", "s")],
    "ecy": [("ECL", "y", "s"), ("ECR", "y", "s")], "ea": [("EA", "y", "s")], "tdrop": [("TB", "y", "S")], "glint": [("glints", "opacity", 1)],
    "brow": [("browL", "y", "s"), ("browR", "y", "s")], "browt": [("browL", "rotation", -1), ("browR", "rotation", 1)],
    "gx": [("gaze", "x", "s")], "gy": [("gaze", "y", "s")],
    "cheek": [("cheeks", "y", "s")], "cheeksx": [("cheeks", "scaleX", 1)], "cheeksy": [("cheeks", "scaleY", 1)],
    "lipsx": [("lips", "scaleX", 1)], "lipsy": [("lips", "scaleY", 1)], "head": [("lips", "x", "s")],
}
FACE_REST = {c: 0 for c in FACE_CH}
FACE_REST.update(open=1, narrow=1, tcurl=1, glint=1, cheeksx=1, cheeksy=1, lipsx=1, lipsy=1)


def _base(R, key, prop):
    S, s = R["S"], R["s"]
    return {("TB", "y"): 62 * S, ("CL", "x"): -54 * S, ("CR", "x"): 54 * S, ("TT", "y"): -22 * S, ("browL", "y"): (EYE_Y - 26) * s,
            ("browR", "y"): (EYE_Y - 26) * s}.get((key, prop), 0)


def _unit(R, u):
    if u in (1, -1):
        return u
    return (-1 if u[0] == "-" else 1) * R[u[-1]]


def face_value(R, c, v):
    """[(object id, property, absolute value)] for channel c at channel value v."""
    out = []
    for key, prop, u in FACE_CH[c]:
        mul = _unit(R, u)
        if prop in ("scaleX", "scaleY", "opacity"):
            out.append((R[key], prop, v))
        else:
            out.append((R[key], prop, _base(R, key, prop) + v * mul))
    return out


def face_rest(anim, R, frame=0):
    """Hold every face channel at rest (the open laughing smile, eyes open), except tracks the timeline keys."""
    for c, v in FACE_REST.items():
        for obj, prop, val in face_value(R, c, v):
            if prop not in anim.tracks.get(obj, {}):
                anim.k(obj, prop, [(frame, round(val, 4), "hold")])


def face_tracks(anim, tracks, offset=0):
    for obj, prop, keys in tracks:
        anim.k(obj, prop, [(f + offset, v, e) for f, v, e in keys])


MOUTHS = {
    "rest": dict(open=1, narrow=1, smile=0, wide=0, lift=0),
    "a": dict(open=1.08, narrow=1.0, smile=-2, wide=3, lift=-1),
    "o": dict(open=0.82, narrow=0.72, smile=2, wide=-13, lift=1),
    "e": dict(open=0.5, narrow=1.06, smile=-5, wide=5, lift=-2),
    "i": dict(open=0.32, narrow=1.04, smile=-6, wide=7, lift=-2),
    "u": dict(open=0.42, narrow=0.64, smile=2, wide=-16, lift=1),
    "l": dict(open=0.62, narrow=0.95, smile=-3, wide=2, lift=-1),
    "m": dict(open=0.13, narrow=0.9, smile=-6, wide=-4, lift=0),
    "smile": dict(open=0.13, narrow=0.92, smile=-16, wide=-3, lift=4),
    "ha": dict(open=1.22, narrow=1.04, smile=-8, wide=6, lift=-3),
    "hm": dict(open=0.7, narrow=1.0, smile=-7, wide=5, lift=-2),
}
EYES = {
    "open": dict(eu=0, ed=0, ea=0, ecx=0, ecy=0, glint=1),
    "blink": dict(eu=12, ed=-7.5, ea=-10, ecx=1, ecy=2, glint=0),
    "squint": dict(eu=0.5, ed=-15, ea=-25, ecx=4, ecy=6, glint=0),
    "soft": dict(eu=4, ed=-1.5, ea=-1.5, ecx=0, ecy=0.5, glint=1),
    "wide": dict(eu=-2.5, ed=1, ea=1, ecx=0, ecy=0, glint=1),
}
OPEN_E = (0.25, 1.55, 0.5, 1)      # snappy open with an overshoot
CLOSE_E = (0.45, 0, 0.55, 1)
LAG = {"lips": 3, "cheek": 4, "head": 3}


class Talk:
    """Face choreography of one character over a loop of `dur` frames, authored as beats (syllables, laughs,
    blinks, squints, glances); follow-through channels (lips, cheeks, head turn, teeth) are derived at build."""

    def __init__(self, R, dur, seed=0.0):
        self.R, self.dur, self.seed = R, dur, seed
        self.k = {c: [] for c in FACE_CH}
        self.mouth_now = "rest"

    def key(self, c, f, v, e="sine"):
        self.k[c].append((f, v, e))

    def pose(self, f, e="sine", **vals):
        for c, v in vals.items():
            self.key(c, f, v, e)

    def mouth(self, f, m, e="sine", scale=1.0):
        vals = dict(MOUTHS[m])
        vals["open"] = vals["open"] * scale if scale != 1.0 else vals["open"]
        self.pose(f, e, **vals)
        self.mouth_now = m

    def say(self, t0, sylls, per, end="smile", tongue=True):
        """Syllables: each opens with an overshoot and half-closes before the next; durations wobble."""
        t = t0
        for i, sy in enumerate(sylls.split()):
            d = per * (1 + 0.2 * math.sin(i * 2.3 + self.seed))
            mid = MOUTHS[sy]
            # between syllables the jaw half-closes (fully on m)
            self.pose(t, OPEN_E, open=0.13 if sy == "m" else 0.24 + 0.12 * math.sin(i * 1.7 + self.seed))
            self.pose(t + d * 0.42, CLOSE_E, **mid)
            self.pose(t, OPEN_E, **{c: v for c, v in mid.items() if c != "open"})
            if tongue:
                self.key("tlift", t + d * 0.5, -13 if sy == "l" else (-4 if sy in ("e", "i") else 2), "sine")
                self.key("twig", t + d * 0.5, 0.1 * math.sin(i * 2.9 + self.seed), "sine")
                self.key("tx", t + d * 0.5, 3 * math.sin(i * 1.3 + self.seed), "sine")
            t += d
        self.mouth(t, end, CLOSE_E)
        if tongue:
            for c in ("tlift", "twig", "tx"):
                self.key(c, t + 2, 0, "sine")
        return t

    def laugh(self, t0, n, per, eyes=True):
        """Ha-ha-ha: wide overshooting pulses, squinting eyes, raised brows, a tongue that wiggles."""
        if eyes:
            self.eye(t0 - 4, "open", "out")
            self.eye(t0 + 2, "squint", "hold")
            self.eye(t0 + n * per, "squint", "io")
            self.eye(t0 + n * per + 8, "open", "hold")
            self.key("brow", t0 - 4, 0, "out")
            self.key("brow", t0 + 3, -6, "hold")
            self.key("brow", t0 + n * per, -6, "io")
            self.key("brow", t0 + n * per + 10, 0, "hold")
        for i in range(n):
            t = t0 + i * per
            self.mouth(t, "hm" if i else self.mouth_now, OPEN_E)
            self.mouth(t + per * 0.45, "ha", CLOSE_E, scale=1.0 - 0.06 * i)
            self.key("tilt", t + per * 0.45, (0.06 if i % 2 else -0.05), "sine")
            self.key("twig", t + per * 0.45, (0.2 if i % 2 else -0.2), "sine")
            self.key("tlift", t + per * 0.45, -6, "sine")
            self.key("tcurl", t + per * 0.45, 0.84, "sine")
        t = t0 + n * per
        self.mouth(t, "hm", "sine")
        for c, v in (("tilt", 0), ("twig", 0), ("tlift", 0), ("tcurl", 1)):
            self.key(c, t + 4, v, "sine")
        return t

    def eye(self, f, pose, e="sine"):
        self.pose(f, e, **EYES[pose])

    def blink(self, t, back="open"):
        self.eye(t, back, (0.55, 0, 0.9, 0.5))
        self.eye(t + 3, "blink", "hold")
        self.eye(t + 5, "blink", "out")
        self.eye(t + 12, back, "hold")

    def look(self, f, x, y=0, e="io", dur=8):
        self.key("gx", f, self.k["gx"][-1][1] if self.k["gx"] else 0, e)
        self.key("gy", f, self.k["gy"][-1][1] if self.k["gy"] else 0, e)
        self.key("gx", f + dur, x, "hold")
        self.key("gy", f + dur, y, "hold")

    def brows(self, f, y, t=0.0, e="back", dur=8):
        self.key("brow", f, self.k["brow"][-1][1] if self.k["brow"] else 0, e)
        self.key("browt", f, self.k["browt"][-1][1] if self.k["browt"] else 0, e)
        self.key("brow", f + dur, y, "hold")
        self.key("browt", f + dur, t, "hold")

    def build(self, start_rest=True, end_rest=True):
        """-> [(object id, property, keys)] for every channel. By default each starts and ends at rest, so an idle
        loop is seamless; a transition can leave the face mid-expression (end_rest=False) or pick one up."""
        dur, R = self.dur, self.R
        k = {c: list(v) for c, v in self.k.items()}
        # follow-through: lips squash/stretch trails the jaw, cheeks trail the smile, the head trails the gaze
        hide = lambda v: 1 - min(1, max(0, (v - 0.12) / 0.43))      # 1 when the mouth is (nearly) shut
        lin = lambda e: "hold" if e == "hold" else "lin"
        k["teeth"] = [(f, -24 * hide(v), lin(e)) for f, v, e in k["open"]]
        k["tdrop"] = [(f, 46 * hide(v), lin(e)) for f, v, e in k["open"]]
        lg = LAG["lips"]
        k["lipsy"] = [(f + lg, 1 + 0.08 * (v - 0.6), e) for f, v, e in k["open"]]
        k["lipsx"] = [(f + lg, 1 - 0.05 * (v - 0.6), e) for f, v, e in k["open"]]
        lg = LAG["cheek"]
        cl = lambda v: max(-9, min(3, v))
        k["cheek"] = [(f + lg, 0.8 * cl(v), e) for f, v, e in k["smile"]]
        k["cheeksx"] = [(f + lg, 1 - 0.015 * cl(v), e) for f, v, e in k["smile"]]
        k["cheeksy"] = [(f + lg, 1 + 0.035 * cl(v), e) for f, v, e in k["smile"]]
        k["head"] = [(f + LAG["head"], 0.4 * v, e) for f, v, e in k["gx"]]
        out = []
        for c, keys in k.items():
            rest = FACE_REST[c]
            byf = {}
            for f, v, e in keys:
                f = int(round(f))
                if 0 <= f <= dur:
                    byf[f] = (v, e)
            if start_rest:
                byf[0] = (rest, byf.get(0, (rest, "sine"))[1])
            if end_rest or not byf:
                byf[dur] = (rest, "hold")
            ks = [(f, v, e) for f, (v, e) in sorted(byf.items())]
            if start_rest and all(abs(v - rest) < 1e-6 for _f, v, _e in ks):
                continue   # never leaves rest here: other timelines' rest holds cover it
            # per object/property
            for i, (obj, prop, _v) in enumerate(face_value(R, c, rest)):
                out.append((obj, prop, [(f, round(face_value(R, c, v)[i][2], 4), e) for f, v, e in ks]))
        return out


def converse(A, B, t0=0, da=1, db=-1):
    """A 240-frame exchange from t0: A talks while B listens (soft eyes, closed smile, a raised brow), both laugh
    with B a beat late, then B answers while A listens. da / db: which way each one looks to find the other.
    Tempi, blinks and glances differ per character so the pair never moves in step."""
    f = lambda x: t0 + x
    A.look(f(2), 6 * da, -1)
    A.brows(f(4), -3, 0.1)
    t = A.say(f(8), "a e l o m i a", 9.5, end="smile")
    A.brows(t - 4, 0, 0)
    A.blink(f(60))
    A.laugh(f(94), 4, 9)
    A.mouth(f(140), "hm", "sine")
    A.mouth(f(150), "smile", "hold")
    A.eye(f(140), "open", "io")
    A.eye(f(148), "soft", "hold")
    A.look(f(140), 7 * da, 0)
    A.blink(f(166), back="soft")
    A.brows(f(178), -5, -0.12, dur=6)
    A.brows(f(190), 0, 0, e="sine", dur=10)
    A.look(f(198), 0, 2, dur=10)
    A.eye(f(206), "soft", "io")
    A.eye(f(214), "open", "hold")
    A.mouth(f(214), "smile", OPEN_E)
    A.mouth(f(224), "rest", "hold")
    B.mouth(f(4), "rest", "sine")
    B.mouth(f(14), "smile", "hold")
    B.look(f(6), 6 * db, 1)
    B.eye(f(10), "open", "io")
    B.eye(f(18), "soft", "hold")
    B.blink(f(40), back="soft")
    B.brows(f(56), -6, 0.15, dur=7)
    B.brows(f(68), 0, 0, e="sine", dur=12)
    B.eye(f(84), "soft", "io")
    B.eye(f(92), "open", "hold")
    B.mouth(f(86), "smile", "hold")
    B.laugh(f(100), 3, 11)
    B.look(f(134), 7 * db, -2)
    B.say(f(146), "o a i e l a", 12.5, end="rest")
    B.blink(f(200))
    B.look(f(214), 0, 0, dur=12)


def monologue(V, d=-1):
    """180 frames: another voice talks into the listener's ear, laughs, and goes on (persona 2)."""
    V.look(2, 5 * d, 1)
    t = V.say(6, "a o e l a i", 11, end="hm")
    V.blink(30)
    t = V.laugh(t + 4, 2, 9)
    V.look(t + 2, 2 * d, -1)
    t = V.say(t + 10, "e o m a", 12, end="rest")
    V.blink(t + 4)
    V.look(t + 6, 0, 0, dur=10)


def motif_bubble(prefix, color, shade, mirror=False, s=1.0, with_face=True, ids=None, tongue=PD, light=None,
                 look=None, morph=False, rigged=True):
    ids = ids if ids is not None else {}
    ids.setdefault("root", nid())
    ids.setdefault("bob", nid())
    ids.setdefault("elastic", nid())
    ids.setdefault("face", nid())
    light = light or {P: PL, L: LL}.get(color, color)
    look = (-14 if mirror else 14) if look is None else look
    kids = []
    if with_face:
        kids.append(face(prefix, s, ids=ids, tongue=tongue, look=look,
                         cheek={P: "70FF5C7A", L: "60F27AA6"}.get(color, "60FF5C7A"), rigged=rigged))
    kids.append(shape(f"{prefix} highlight", [ellipse(46 * s, 22 * s)],
                      [fill("88FFFFFF", feather=(7 * s,))], x=(52 if mirror else -52) * s, y=-62 * s,
                      rot=0.7 if mirror else -0.7))
    if morph:
        ids["verts"] = [nid() for _ in range(10)]
        ids["s"], ids["mirror"] = s, mirror
        geo = cubic_path(bub(BUB_REST, s, mirror), ids["verts"])
    else:
        geo = smooth_path(bub(BUB_REST, s, mirror))
    kids.append(shape(f"{prefix} body", [geo], shade_fills(color, shade, light, s), id=ids.get("body")))
    return node(prefix, [node(f"{prefix} bob", [node(f"{prefix} elastic", kids, id=ids["elastic"])], id=ids["bob"])],
                id=ids["root"])


def morph_motif(anim, ids, keys):
    """keys: [(frame, BUB_* table, ease)] -> true vertex morph of a motif body."""
    if "verts" not in ids:
        return
    s_, m_ = ids["s"], ids["mirror"]
    key_morph(anim, ids["verts"], [(f, bub(t, s_, m_), e) for f, t, e in keys], bub(BUB_REST, s_, m_))


# a quotation-mark comma (head on top, tail sweeping down-left) and the same 9 vertices gathered into a dot
COMMA = [(0, -62), (44, -40), (52, 6), (34, 66), (-22, 130, "c", 5), (-10, 70), (-34, 38), (-50, -6), (-40, -44)]
COMMA_DOT = [(round(math.cos(-math.pi / 2 + k * 2 * math.pi / 9) * 34, 2),
              round(math.sin(-math.pi / 2 + k * 2 * math.pi / 9) * 34 - 4, 2)) for k in range(9)]


def comma_pts(s=1.0):
    return [(p[0] * s, p[1] * s) + tuple(p[2:]) for p in COMMA]


def block_quote_pts(s=1.0):
    """Concept screen 4: a flat-topped block quote whose right side rolls down into a comma tail."""
    pts = [(-66, -104, "c", 16), (66, -104, "c", 16), (70, -6), (62, 52), (34, 98), (-30, 122, "c", 4),
           (-4, 74), (4, 34), (-30, 26), (-66, 6, "c", 14)]
    return [(p[0] * s, p[1] * s) + tuple(p[2:]) for p in pts]


def sparkle(name, size, color, x, y, id=None, rot=0):
    return shape(name, [E("Star", {"width": size, "height": size, "points": 4, "innerRadius": 0.3, "cornerRadius": 0.6,
                                   "name": "Path"})], [fill(color)], id=id or nid(), x=x, y=y, rot=rot)


def ground(name, w, h, color, x, y, id=None):
    """Soft ground shadow (feathered ellipse) -- concept's lemon / lilac pools under the speech forms."""
    return shape(name, [ellipse(w, h)], [fill(color, feather=(10,))], id=id or nid(), x=x, y=y)


def grain(name="grain", op=0.55):
    """Restrained raster grain over a scene's art (never carries text), overlay-blended, 2x scale."""
    return E("Image", {"assetId": GRAIN, "x": 195, "y": 422, "scaleX": 2, "scaleY": 2, "opacity": op,
                       "blendModeValue": "overlay", "name": name})


# ---------------------------------------------------------------- scene scaffolding
SCENES = {}


class Parts(list):
    """Scene parts (xml, top first), each tagged with the layout block that is current when it is added."""

    def __init__(self, scene):
        super().__init__()
        self.scene = scene

    def append(self, x):
        super().append((self.scene.blk, x))

    def insert(self, i, x):
        super().insert(i, (self.scene.blk, x))

    def __iadd__(self, xs):
        for x in xs:
            self.append(x)
        return self


class Scene:
    def __init__(self, n, bg):
        self.n = n
        self.bg = bg
        self.root = nid()
        self.blk = "a"           # current layout block: "t" top copy, "b" bottom copy, "a" art (see LAYOUT)
        self.parts = Parts(self)  # (block, xml) children, top first
        self.final = {}          # (obj, prop) -> (value, kind)  settled pose
        self.enter = []          # list of (obj, prop, keys, kind) for In timeline (after cover reveal)
        self.idle = []           # idle tracks
        self.idle_dur = 240
        self.motifA = OFF_A
        self.motifB = OFF_B
        self.mouth_hit = None
        SCENES[n] = self

    def track(self, obj, prop, keys, kind="d"):
        self.enter.append((obj, prop, keys, kind))
        self.final[(obj, prop)] = (keys[-1][1], kind)

    def settle(self, obj, prop, value, kind="d"):
        self.final[(obj, prop)] = (value, kind)

    def itrack(self, obj, prop, keys, kind="d"):
        self.idle.append((obj, prop, keys, kind))


def rise(sc, obj, f0, dy=26, dur=24, base_y=0, ease="out", fade=True):
    sc.track(obj, "y", [(0, base_y + dy, "hold"), (f0, base_y + dy, ease), (f0 + dur, base_y, "hold")])
    if fade:
        sc.track(obj, "opacity", [(0, 0, "hold"), (f0, 0, "out"), (f0 + dur * 0.8, 1, "hold")])


def pop(sc, obj, f0, dur=26, ease="back", s0=0.0, rot0=None, rot1=0):
    sc.track(obj, "scaleX", [(0, s0, "hold"), (f0, s0, ease), (f0 + dur, 1, "hold")])
    sc.track(obj, "scaleY", [(0, s0, "hold"), (f0, s0, ease), (f0 + dur, 1, "hold")])
    if rot0 is not None:
        sc.track(obj, "rotation", [(0, rot0, "hold"), (f0, rot0, ease), (f0 + dur, rot1, "hold")])


def count(sc, f0=24, f1=84, hero=None):
    """Hero value counts 0 -> bound value; its digits start condensed (wdth 75) and stretch out to full width
    as the count lands, so the number itself feels elastic."""
    sc.track(DRIVER, "x", [(0, 0, "hold"), (f0, 0, "out2"), (f1, 1, "hold")])
    for ax in HERO_AX.get(hero or getattr(sc, "hero", None), []):
        sc.track(ax, "axisValue", [(0, 75, "hold"), (f0, 75, "out2"), (f1 - 10, 104, "sine"), (f1 + 8, 100, "hold")])


def kinetic(units=2, y=40, x=0, rot=0.0, scale=None, ease=(0.3, -0.55, 0.55, 1)):
    """Per-word / per-letter cascade on a live text. Authored at the settled (fully revealed) pose; timelines
    key the range. The range ease dips below zero at its revealed edge, so each unit overshoots its rest
    position (follow-through) before settling. Returns (range_id, modifier xml)."""
    rng = nid()
    a = {"modifyOpacity": True, "invertOpacity": True, "modifyTranslation": True, "opacity": 0, "x": x, "y": y,
         "modifyOrigin": True, "originX": 0.5, "originY": 1, "name": "Kinetic cascade"}
    if rot:
        a.update({"modifyRotation": True, "rotation": rot})
    if scale:
        a.update({"modifyScale": True, "scaleX": scale[0], "scaleY": scale[1]})
    return rng, E("TextModifierGroup", a, [
        E("TextModifierRange", {"unitsValue": units, "modifyFrom": 1.6, "modifyTo": 3, "falloffFrom": 2.2,
                                "falloffTo": 3, "name": "Sweep", "id": rng},
          [E("CubicInterpolatorComponent", {"x1": ease[0], "y1": ease[1], "x2": ease[2], "y2": ease[3],
                                            "name": "Overshoot"})])])


def sweep(sc, rng, f0, dur=34, width=0.5, idle=False):
    """Reveal a kinetic() text from its first unit to its last between f0 and f0+dur."""
    sc.track(rng, 327, [(0, -width - 0.02, "hold"), (f0, -width - 0.02, "lin"), (f0 + dur, 1.6, "hold")])
    sc.track(rng, 317, [(0, 0, "hold"), (f0, 0, "lin"), (f0 + dur, 2.2, "hold")])


def flow_text(name, w, prop_name, **kw):
    """A bound text that takes part in a vertical flow (wrapped so its offset/opacity can be animated)."""
    wid, sid_ = nid(), nid()
    tid, cid, t = bound_text(name, 0, 0, w, prop_name, **kw)
    t = t.replace(f'id="{tid}">', f'id="{tid}">' + E("LayoutParticipant", {"layoutWidthScaleType": "fill",
                                                                             "layoutHeightScaleType": "hug",
                                                                             "name": "Flow"}), 1)
    wrap = E("LayoutComponent", {"width": w, "height": 10, "styleId": sid_, "name": f"{name} slot", "id": wid}, [
        E("LayoutComponentStyle", {"layoutWidthScaleType": "fill", "layoutHeightScaleType": "hug",
                                   "name": f"{name} slot style", "id": sid_}), t])
    return wid, cid, wrap


def column(name, x, y, w, items, gap=8, op=None, cid=None, bottom=None):
    """Absolutely positioned vertical flow. With bottom=<pt from artboard bottom> it grows upwards."""
    sid_ = nid()
    vpos = {"positionTop": y, "positionTopUnitsValue": "points"} if bottom is None else \
        {"positionBottom": bottom, "positionBottomUnitsValue": "points"}
    cid = cid or nid()
    return cid, E("LayoutComponent", {"width": w, "height": 10, "styleId": sid_, "opacity": op,
                                     "name": name, "id": cid}, [
        E("LayoutComponentStyle", {"flexDirectionValue": "column", "layoutHeightScaleType": "hug",
                                   "gapVertical": gap, "gapVerticalUnitsValue": "points",
                                   "positionTypeValue": "absolute", "positionLeft": x,
                                   "positionLeftUnitsValue": "points", **vpos,
                                   "name": f"{name} style", "id": sid_})] + items)


# ---- the concept's type system (screens 2 / 4 / 9) ----------------------------------------------------------
HERO_Y, HERO_SIZE = 84, 138        # giant numeral, heavy and tight
UNIT_Y, UNIT_SIZE = 216, 27        # unit sits right under the numeral
HEAD_Y, HEAD_SIZE, HEAD_LH = 256, 39, 41
HEAD_LINES = 3                     # long localized headlines shrink to fit three lines instead of running on
CAPTION_BOTTOM = 94                # the support line is a caption on the control bar, growing upwards


def top_copy(sc, n, x=24, w=342, unit_y=UNIT_Y, head_y=HEAD_Y, ink=D, align=None, f0=56, unit=True,
             head_lines=HEAD_LINES, head_size=HEAD_SIZE):
    """Unit (one line, fit) + headline (fixed box of head_lines lines, fit). Both boxes are bounded, so even the
    extreme fixture's copy cannot grow into the illustration zone below (~y 400-712)."""
    ids = {}
    prev, sc.blk = sc.blk, "t"
    if unit:
        ids["unit_rng"], m = kinetic(units=0, y=0, x=-14, ease=(0.4, 0, 0.2, 1))
        ids["unit"], ids["unit_c"], t = bound_text(f"S{n} unit", x, unit_y, w, f"screen{n}Unit", size=UNIT_SIZE,
                                                   color=ink, wght=650, wdth=96, sizing="fixed", h=UNIT_SIZE * 1.25,
                                                   overflow="fitFontSize", wrap="noWrap", align=align, ls=-0.3,
                                                   mods=[m])
        sc.parts.append(t)
        sweep(sc, ids["unit_rng"], f0 - 22, 26, 0.3)
    hl = head_size * 41 / 39
    ids["head_rng"], m = kinetic(units=2, y=hl * 1.1, rot=0.08)
    ids["head"], ids["head_c"], t = bound_text(f"S{n} headline", x, head_y, w, f"screen{n}Headline", size=head_size,
                                               color=ink, wght=800, wdth=96, lh=hl, sizing="fixed", h=hl * head_lines + 4,
                                               overflow="fitFontSize", wrap="wrap", align=align, ls=-0.6, valign="top",
                                               mods=[m])
    sc.parts.append(t)
    sweep(sc, ids["head_rng"], f0, 40, 0.45)
    sc.blk = prev
    return ids


def caption(sc, n, ink=DL, align=None, f0=86, bottom=CAPTION_BOTTOM, prop=None, x=24, w=342):
    ids = {}
    ids["sup_rng"], m = kinetic(units=2, y=14, ease=(0.4, 0, 0.2, 1))
    ids["sup"], ids["sup_c"], t = flow_text(f"S{n} support", w, prop or f"screen{n}Support", font="body", size=16,
                                            color=ink, wght=500, lh=21, align=align, mods=[m])
    prev, sc.blk = sc.blk, "b"
    sc.parts.append(column(f"S{n} caption", x, 0, w, [t], bottom=bottom)[1])
    sc.blk = prev
    sweep(sc, ids["sup_rng"], f0, 30, 0.4)
    return ids


# global motif / driver ids (filled in below)
MA = {"root": nid(), "body": nid()}
MB = {"root": nid(), "body": nid()}
DRIVER = nid()
MOUTH_HIT = nid()

# motif poses: (x, y, sx, sy, rot, faceOpacity). COVER_* are paired with the BUB_TALL morph: the elongated
# speech form, scaled ~3x, fills the 390x844 frame.
OFF_A = (560, 1040, 1.2, 1.2, 0.5, 1)
OFF_B = (-170, 1040, 1.2, 1.2, -0.5, 1)
COVER_A = (195, 200, 2.95, 2.95, 0.04, 0)
COVER_B = (195, 200, 2.95, 2.95, -0.04, 0)


# Poses authored in cover space (the 390x844 frame scaled to cover the canvas) rather than in a scene's art space:
# off-stage, the elongated cover, the swing-in of an elongation, and the points where a form leaves or is swallowed.
COVER_SPACE = {OFF_A[:2], OFF_B[:2], COVER_A[:2], (285, 560), (105, 560), (-200, 1000), (560, 700), (195, 430)}


def _calm(e):
    """Ease for a frame blend: overshooting eases would extrapolate the frame, so they become a plain in-out."""
    if e in ("back", "back2", "el", "el2", "antic") or (isinstance(e, tuple) and (min(e[1], e[3]) < 0 or max(e[1], e[3]) > 1)):
        return "io"
    return e


def motif_keys(anim, ids, keys):
    """keys: list of (frame, pose, ease). Also keys the motif's frame blend (art space vs cover space) and, when the
    timeline belongs to a scene with the motif on stage, which scene's art space that is."""
    for i, prop in enumerate(["x", "y", "scaleX", "scaleY", "rotation"]):
        anim.k(ids["root"], prop, [(f, pose[i], e) for f, pose, e in keys])
    anim.k(ids["face"], "opacity", [(f, pose[5], e) for f, pose, e in keys])
    drv = MIXA_DRV if ids is MA else MIXB_DRV
    anim.k(drv, "x", [(f, 1 if tuple(pose[:2]) in COVER_SPACE else 0, _calm(e)) for f, pose, e in keys])
    mp = getattr(anim, "motif_map", None)
    if mp:
        anim.k(MAP_DRV, "x", mp)


# ================================================================ RESPONSIVE LAYOUT
# The host presents the artboard with the runtime's layout fit, so the artboard is resized to the canvas. A root
# layout box that fills the artboard writes its computed size into _vw/_vh; a small solver (hidden nodes whose x
# is bound from a formula and written back to the view model) derives the shared quantities below, and every
# frame node in the scene binds its x / y / scale to a formula over them. Nothing is letterboxed: backgrounds,
# covers, chrome and hit regions follow the real size, and each block of copy or art is placed and scaled on its
# own.
#
#   _land  = _vw >= layoutBreakpoint                          landscape layout
#   _split = _land or (_vw >= _vh)                            copy and art side by side
#   portrait: stacked (top copy / art / bottom copy) or, on a canvas wider than tall, side by side
#   landscape: always side by side (copy column + art column, persona and summary mirrored / re-proportioned)
VW, VH = vmx("_vw"), vmx("_vh")
BP = xmax(1, vmx("layoutBreakpoint"))
LX = xstep(VW - BP)
KP = xclamp(xmin(VW / 390, VH / 640), 0.85, 1.12)
KL = xclamp(VH / 780, 0.9, 1.3)
MP = xclamp(VW * (24 / 390), 14, 44)
ML = xclamp(VW * 0.042, 36, 96)
BTP = xclamp(VH * 0.095, 60, 80)   # portrait chrome band (80 at 844 tall, tighter on short canvases)
BBP = xclamp(VH * 0.095, 64, 80)   # portrait control band
SOLVE = {
    "_land": LX,
    "_split": xmax(LX, xstep(VW / xmax(1, VH) - 1)),
    "_k": xlerp(KP, KL, LX),
    "_m": xlerp(MP, ML, LX),
    "_top": xlerp(KP * BTP, KL * 88, LX),
    "_bot": VH - xlerp(KP * BBP, KL * 90, LX),
    "_sc": xclamp(xmin((VW - 2 * MP) / 342, 0.35 + 0.65 * ((VH - KP * BBP - KP * BTP) / 684)), 0.7, 1.3),
}
LND, SPL, K, M, TOP, BOT, SC = (vmx(n) for n in ("_land", "_split", "_k", "_m", "_top", "_bot", "_sc"))
WIDE = xstep(VW / xmax(1, VH) - 1)   # canvas wider than tall
solver_xml = node("Layout solver", [
    node(f"Solve {name}", [], binds=[lbind(13, e, f"Solve {name}"), bind(V(name), 13, None, direction=True)])
    for name, e in SOLVE.items()])

DT, DB = 80, 764          # design content band (390x844 master)
ANCHOR_X = {"l": 24, "r": 366, "c": 195}
# Per scene: copy blocks t (top) and b (bottom) as (design y0, y1, alignment); art = (x range, y range) of the
# illustration used to fit it; f = copy column share when side by side; mirror = art on the left; wide = the box
# of the wide share card (scene 10).
LAYOUT = {
    1: dict(t=(96, 150, "l"), b=(508, 736, "l"), art=((0, 390), (70, 570))),
    2: dict(t=(84, 383, "l"), b=(729, 750, "l"), art=((-40, 430), (396, 720))),
    3: dict(t=(92, 259, "l"), b=(729, 750, "l"), art=((0, 390), (384, 736))),
    4: dict(t=(84, 383, "l"), b=(729, 750, "l"), art=((60, 390), (140, 720)), split_art=((60, 390), (120, 712))),
    5: dict(t=(84, 383, "r"), b=(729, 750, "r"), art=((20, 380), (384, 724)), mirror=True),
    6: dict(t=(84, 383, "l"), b=(729, 750, "l"), art=((-40, 430), (440, 724))),
    7: dict(t=(92, 228, "l"), b=(540, 758, "l"), art=((-30, 420), (250, 560))),
    8: dict(t=(84, 383, "c"), b=(729, 750, "c"), art=((40, 350), (350, 730))),
    9: dict(t=(104, 300, "l"), b=None, art=((0, 390), (300, 745)), mirror=True, f=0.42),
    10: dict(t=(90, 186, "l"), b=None, art=((24, 366), (196, 752)), wide=((0, 766), (0, 300)), f=0.4),
}


def stack_frames(n):
    """Portrait, stacked: top copy under the chrome, bottom copy over the controls (both at the copy scale _sc,
    which never drops below 0.7), and the art fitted into what is left between them."""
    L_ = LAYOUT[n]
    sC = SC
    mC = xmin(M, xmax(10, (VW - 342 * sC) / 2))
    fr = {}
    for key in ("t", "b"):
        b = L_.get(key)
        if not b:
            continue
        y0, y1, h = b
        Y = TOP + (y0 - DT) * sC if key == "t" else BOT - (DB - y0) * sC
        X = {"l": mC, "r": VW - mC, "c": VW / 2}[h]
        fr[key] = (X - sC * ANCHOR_X[h], Y - sC * y0, sC)
    s0 = L_["t"][1] if L_.get("t") else DT
    s1 = L_["b"][0] if L_.get("b") else DB
    (_x0, _x1), (a0, a1) = L_["art"]
    slotT = TOP + (s0 - DT) * sC
    slotB = BOT - (DB - s1) * sC
    gT, gB = a0 - s0, s1 - a1
    avail = slotB - slotT - (gT + gB) * sC
    sA = xclamp(xmin(VW / 390, avail / (a1 - a0)), 0.2, 1.7)
    extra = xmax(0, avail - (a1 - a0) * sA)
    ya0 = slotT + gT * sC + extra / 2
    fr["a"] = (VW / 2 - sA * 195, ya0 - sA * a0, sA)
    fr["w"] = fr["a"]
    return fr


def split_frames(n):
    """Side by side: a copy column (blocks stacked, vertically centred) and an art column (illustration fitted
    and centred). The content width is capped at 2.4x the band height so ultra-wide canvases keep a composition."""
    L_ = LAYOUT[n]
    band = BOT - TOP
    Wc = xmin(VW - 2 * M, 2.4 * band)
    x0 = (VW - Wc) / 2
    gap = 0.05 * Wc
    copyW = xmax(L_.get("f", 0.44) * Wc, 342 * 0.66)
    artW = Wc - copyW - gap
    if L_.get("mirror"):
        artL, copyL = x0, x0 + artW + gap
    else:
        copyL, artL = x0, x0 + copyW + gap
    blocks = [(k, L_[k]) for k in ("t", "b") if L_.get(k)]
    G = 26
    T = sum(b[1] - b[0] for _k, b in blocks) + G * (len(blocks) - 1)
    sC = xclamp(xmin(xmin(copyW / 342, 0.9 * band / T), 1.7), 0.62, 1.7)   # 5% breathing room above and below
    Y = TOP + (band - T * sC) / 2
    fr, off = {}, 0
    for k, (y0, y1, h) in blocks:
        X = {"l": copyL, "r": copyL + copyW, "c": copyL + copyW / 2}[h]
        fr[k] = (X - sC * ANCHOR_X[h], Y + off * sC - sC * y0, sC)
        off += (y1 - y0) + G
    fr["artL"] = artL
    cx, cy = artL + artW / 2, TOP + band / 2
    for key, box in (("a", L_.get("split_art", L_["art"])), ("w", L_.get("wide", L_["art"]))):
        (bx0, bx1), (by0, by1) = box
        sA = xclamp(xmin(artW / (bx1 - bx0), band / (by1 - by0)), 0.2, 2.6)
        fr[key] = (cx - sA * (bx0 + bx1) / 2, cy - sA * (by0 + by1) / 2, sA)
    return fr


_FRAMES = {}


def frames(n):
    if n not in _FRAMES:
        st, sp = stack_frames(n), split_frames(n)
        _FRAMES[n] = {k: tuple(xlerp(a, b, SPL) for a, b in zip(st[k], sp[k])) for k in st}
        _FRAMES[n]["artL"] = sp["artL"]
    return _FRAMES[n]


def frame_binds(fr, name):
    x, y, s_ = fr
    return [lbind(13, x, f"{name} x"), lbind(14, y, f"{name} y"), lbind(16, s_, f"{name} scale"),
            lbind(17, s_, f"{name} scale")]


SCOV = xmax(VW / 390, VH / 844)
COVER = (VW / 2 - SCOV * 195, VH / 2 - SCOV * 422, SCOV)   # the 390x844 frame scaled to cover the canvas


def blend(frs, ws):
    return tuple(sum((w * f[i] for f, w in zip(frs[1:], ws[1:])), ws[0] * frs[0][i]) for i in range(3))


ART_VM = {n: tuple(vmx(f"_a{n}{c}") for c in "xys") for n in (1, 2, 3, 9)}
_art_solve = []
for _n in (1, 2, 3, 9):
    for _i, _c in enumerate("xys"):
        _art_solve.append(node(f"Solve _a{_n}{_c}", [], binds=[lbind(13, frames(_n)["a"][_i], f"Solve _a{_n}{_c}"),
                                                                 bind(V(f"_a{_n}{_c}"), 13, None, direction=True)]))
solver_xml = node("Layout solver", [solver_xml] + _art_solve)


def art(n):
    """Scene n's art frame: from the solver's view model values for the scenes the motif visits."""
    return ART_VM[n] if n in ART_VM else frames(n)["a"]


def motif_frame(mix_name):
    """Motif A / B live in one frame: the art space of the scene named by _motifMap (1, 2, 3 or 9, keyed by the
    timelines; a carry between scenes keys it from one to the next) blended into cover space by _mixA/_mixB, so
    the same keyed pose that sits in a scene's art also fills the whole canvas when it elongates into a cover."""
    mp = vmx("_motifMap")
    ks = (1, 2, 3, 9)
    art_ = blend([art(k) for k in ks], [xhat(mp - k) for k in ks])
    mix = vmx(mix_name)
    return tuple(xlerp(a, c, mix) for a, c in zip(art_, COVER))


# ================================================================ SCENES
# Each scene: parts (xml, top-first), enter tracks (frames relative to In start, 60 fps),
# final pose, idle loop. Metric scenes share the concept's type system (top_copy + caption): giant numeral,
# unit tight underneath, a heavy 2-3 line headline, and the support line as a caption on the control bar,
# leaving a protected illustration zone of roughly y 400-712.

# ---------- 1. Invitation ----------------------------------------------------
s = Scene(1, WP)
s.motifA = (126, 300, 1.3, 1.3, -0.12, 1)
s.motifB = (292, 392, 1.06, 1.06, 0.1, 1)
s.blk = "t"
name_t = nid()
sid, st = body(17, D, 600)
pill_bg = E("TextStyleBackground", {"cornerRadius": 15, "name": "Pill"}, [fill(L)])
st_pill = st.replace("</TextStylePaint>", pill_bg + "</TextStylePaint>", 1)
s.parts.append(text("S1 name", 24, 96, [st_pill], [run(sid, " ", []), run(sid, "Alex", [bind(V("userName"), 268)]),
                                                   run(sid, " ", [])], id=name_t, w=280, h=26, sizing="fixed",
                    overflow="ellipsis", wrap="noWrap"))
rise(s, name_t, 52, base_y=96, dy=14)
per_t, _c, t_ = bound_text("S1 period", 24, 130, 342, "periodLabel", font="body", size=14, color=DL, wght=500)
s.parts.append(t_)
rise(s, per_t, 60, base_y=130, dy=10)
# wordmark (kinetic): letters stretch up out of a speech envelope
s.blk = "b"
wm_t = nid()
wm_range = nid()
sid, st = disp(86, D, 800, wdth=84, lh=86, ls=-2)
wm_mod = E("TextModifierGroup", {"modifyOpacity": True, "modifyTranslation": True, "modifyScale": True,
                                 "invertOpacity": True, "opacity": 0, "y": 46, "scaleY": 2.1, "scaleX": 0.6,
                                 "originX": 0.5, "originY": 1, "modifyOrigin": True, "name": "Envelope stretch"},
           [E("TextModifierRange", {"modifyFrom": 1.0, "modifyTo": 1, "falloffFrom": 1.25, "falloffTo": 1,
                                    "name": "Sweep", "id": wm_range},
              [E("CubicInterpolatorComponent", {"x1": 0.2, "y1": 0, "x2": 0.2, "y2": 1, "name": "Ease"})])])
dot_id = nid()
s.parts.append(node("S1 wordmark", [
    text("S1 wordmark text", 0, 0, [st], [run(sid, "Parlance")], id=wm_t, extra_children=[wm_mod]),
    shape("S1 wordmark comma", [smooth_path(comma_pts(0.3))], [fill(P)], id=dot_id, x=334, y=70),
], x=22, y=508))
s.track(wm_range, 327, [(0, -0.35, "hold"), (34, -0.35, "lin"), (78, 1.0, "hold")])
s.track(wm_range, 317, [(0, -0.1, "hold"), (34, -0.1, "lin"), (78, 1.25, "hold")])
pop(s, dot_id, 74, 24, "back2", rot0=-1.2)
ih_rng, m1 = kinetic(units=2, y=40, rot=0.08)
is_rng, m2 = kinetic(units=2, y=14, ease=(0.4, 0, 0.2, 1))
# bounded boxes: a long localized intro shrinks to two lines instead of climbing over the wordmark
ih_t, ih_c, t1_ = bound_text("S1 headline", 24, 604, 342, "introHeadline", size=37, color=D, wght=800, lh=39, wdth=96,
                             ls=-0.6, sizing="fixed", h=82, overflow="fitFontSize", valign="top", mods=[m1])
is_t, is_c, t2_ = bound_text("S1 support", 24, 692, 342, "introSupport", font="body", size=16, color=DL, wght=500,
                             lh=21, sizing="fixed", h=44, overflow="ellipsis", mods=[m2])
s.parts += [t1_, t2_]
sweep(s, ih_rng, 84, 40)
sweep(s, is_rng, 104, 30, 0.4)
# giant punctuation sculptures behind the motif
s.blk = "a"
q1, q2 = nid(), nid()
sid, st = disp(300, Y, 800)
s.parts.append(text("S1 giant quote", 196, 80, [st], [run(sid, "“")], id=q1, rot=0.12))
sid, st = disp(190, LL, 800)
s.parts.append(text("S1 giant bang", 10, 288, [st], [run(sid, "!")], id=q2, rot=-0.22))
pop(s, q1, 20, 34, "back", s0=0.4, rot0=0.7, rot1=0.12)
pop(s, q2, 30, 30, "back", s0=0.3, rot0=-0.9, rot1=-0.22)
s.itrack(q1, "rotation", [(0, 0.12, "sine"), (120, 0.04, "sine"), (240, 0.12, "hold")])
s.itrack(q2, "rotation", [(0, -0.22, "sine"), (120, -0.14, "sine"), (240, -0.22, "hold")])
for i, (x, y, sz, col) in enumerate([(338, 120, 26, D), (40, 250, 18, Y), (356, 470, 16, P)]):
    sp = nid()
    s.parts.append(sparkle(f"S1 sparkle {i}", sz, col, x, y, id=sp))
    pop(s, sp, 60 + i * 8, 22, "back2", rot0=-1)
    s.itrack(sp, "rotation", [(0, 0, "sine"), (120, 0.4, "sine"), (240, 0, "hold")])
s.parts.append(ground("S1 shadow A", 190, 26, "77F6E97C", 128, 476))

# ---------- 2. Conversations -------------------------------------------------
s = Scene(2, WP)
s.motifA = (68, 506, 1.06, 1.06, -0.06, 1)
s.motifB = (356, 526, 0.96, 0.96, 0.06, 1)
s.mouth_hit = (90, 520, 180, 170)
hid, hx, hc = hero_number("S2 hero", "conversations", 24, HERO_Y, 342, HERO_SIZE, D, wdth=100, ls=-5)
s.blk = "t"
s.parts.append(hx)
s.blk = "a"
s.hero = hid
rise(s, hid, 10, base_y=HERO_Y, dy=34, dur=22, ease="back")
count(s, 20, 82)
ids2 = top_copy(s, 2)
ids2.update(caption(s, 2))
# punctuation tokens: a cascade of marks between the two speech forms (settled composition from the concept)
TOK = [(",", L, 208, 394, 0.35, 58), ("?", P, 236, 418, 0.18, 70), (",", Y, 172, 430, 0.5, 44),
       ("!", D, 202, 480, -0.1, 76), ("pill", Y, 236, 510, 0.5, 0), ("dot", DL, 206, 540, 0, 0),
       (",", L, 196, 572, 0.25, 54), (",", P, 214, 606, 0.0, 60)]
mouthA = (110, 540)
for i, (ch, col, x, y, r, sz) in enumerate(TOK):
    tid, inner = nid(), nid()
    if ch == "pill":
        g = shape(f"S2 token pill {i}", [rect(16, 40, 8)], [fill(col)])
    elif ch == "dot":
        g = shape(f"S2 token dot {i}", [ellipse(14, 14)], [fill(col)])
    else:
        sid, st = disp(sz, col, 800)
        g = text(f"S2 token glyph {i}", 0, 0, [st], [run(sid, ch)], ox=0.5, oy=0.5)
    s.parts.append(node(f"S2 token {i}", [node(f"S2 token bob {i}", [g], id=inner, rot=r)], id=tid, x=x, y=y))
    # entrance: each mark is spat out of the persimmon mouth and arcs to its place (staggered)
    f0 = 34 + i * 5
    s.track(tid, "x", [(0, mouthA[0], "hold"), (f0, mouthA[0], "out"), (f0 + 26, x, "hold")])
    s.track(tid, "y", [(0, mouthA[1], "hold"), (f0, mouthA[1], (0.2, 1.6, 0.4, 1)), (f0 + 26, y, "hold")])
    s.track(tid, "scaleX", [(0, 0.2, "hold"), (f0, 0.2, "back2"), (f0 + 22, 1, "hold")])
    s.track(tid, "scaleY", [(0, 0.2, "hold"), (f0, 0.2, "back2"), (f0 + 22, 1, "hold")])
    s.track(tid, "opacity", [(0, 0, "hold"), (f0, 1, "hold")])
    per = 240
    ph = (i * 37) % 120
    s.itrack(inner, "y", [(0, 0, "sine"), (ph + 30, -6, "sine"), (ph + 90, 4, "sine"), (per, 0, "hold")])
    s.itrack(inner, "rotation", [(0, r, "sine"), (ph + 60, r + (0.14 if i % 2 else -0.14), "sine"), (per, r, "hold")])
# travelling tokens: a few marks keep passing from one mouth to the other (idle exchange)
for i, (ch, col) in enumerate([("?", P), ("!", D), (",", LD)]):
    tid, inner = nid(), nid()
    sid, st = disp(40, col, 800)
    s.parts.append(node(f"S2 traveller {i}", [text(f"S2 traveller glyph {i}", 0, 0, [st], [run(sid, ch)], ox=0.5,
                                                    oy=0.5, id=inner)], id=tid, x=140, y=560, op=0))
    a_, b_ = ((130, 552), (320, 560)) if i % 2 == 0 else ((320, 560), (130, 552))
    st0 = 10 + i * 72
    s.itrack(tid, "x", [(0, a_[0], "hold"), (st0, a_[0], "sine"), (st0 + 70, b_[0], "hold"), (st0 + 72, a_[0], "hold"),
                        (240, a_[0], "hold")])
    s.itrack(tid, "y", [(0, a_[1], "hold"), (st0, a_[1], "out"), (st0 + 35, 430 + i * 14, "in"), (st0 + 70, b_[1], "hold"),
                        (st0 + 72, a_[1], "hold"), (240, a_[1], "hold")])
    s.itrack(tid, "opacity", [(0, 0, "hold"), (st0, 0, "lin"), (st0 + 8, 1, "hold"), (st0 + 60, 1, "lin"),
                              (st0 + 70, 0, "hold"), (240, 0, "hold")])
    s.itrack(inner, "rotation", [(0, -0.6, "hold"), (st0, -0.6, "lin"), (st0 + 70, 0.8, "hold"), (st0 + 72, -0.6, "hold"),
                                 (240, -0.6, "hold")])
    s.settle(tid, "opacity", 0)
# motion dashes by the lilac mouth
for i, (x, y, r) in enumerate([(244, 470, -0.5), (240, 544, 0.0), (162, 610, 0.5)]):
    dsh = nid()
    s.parts.append(shape(f"S2 dash {i}", [rect(16, 4.5, 2.2)], [fill(D)], id=dsh, x=x, y=y, rot=r))
    pop(s, dsh, 60 + i * 4, 16, "back")
    s.itrack(dsh, "opacity", [(0, 1, "sine"), (60 + i * 20, 0.35, "sine"), (240, 1, "hold")])
s.idle_dur = 240
# soft lemon / lilac pools under the speech forms
sh1, sh2 = nid(), nid()
s.parts.append(ground("S2 shadow A", 176, 30, "AAF6E97C", 92, 700, id=sh1))
s.parts.append(ground("S2 shadow B", 156, 26, "AAC7B7F2", 306, 704, id=sh2))
pop(s, sh1, 10, 24, "out")
pop(s, sh2, 18, 24, "out")

# ---------- 3. Minutes practising -------------------------------------------
s = Scene(3, L)
s.mouth_hit = (195, 548, 330, 250)
ids3 = top_copy(s, 3, unit_y=92, head_y=132, f0=40)
ids3.update(caption(s, 3, ink=D))
MOUTH = {"outer": nid(), "breath": nid(), "elastic": nid(), "open": nid(), "teeth": nid(), "tongue": nid(),
         "lips": nid(), "inner": nid(), "lipverts": [nid() for _ in range(10)], "openverts": [nid() for _ in range(8)],
         "TB": nid(), "TT": nid()}
# lips: 10 all-cubic vertices, ordered like the speech-form body so the mouth can morph into a speech bubble
LIPS = [(0, -96), (36, -122), (106, -112), (178, 0, "c", 30), (106, 120), (0, 134), (-106, 120), (-178, 0, "c", 30),
        (-106, -112), (-36, -122)]
LIPS_PUCKER = [(0, -100), (30, -128), (86, -120), (138, 0, "c", 20), (86, 128), (0, 142), (-86, 128), (-138, 0, "c", 20),
               (-86, -120), (-30, -128)]
opening = [(-134, 0, "c", 34), (-64, -64), (0, -58), (64, -64), (134, 0, "c", 34), (64, 80), (0, 92), (-64, 80)]
# the cavity talks in a slow "ah - oh - ee - mm" (true vertex morph; the numerals stay framed in every shape)
OPEN_OH = [(round(p[0] * 0.8, 2), round(p[1] * (1.16 if p[1] > 0 else 1.07), 2)) + tuple(p[2:]) for p in opening]
OPEN_EE = [(round(p[0] * 1.08, 2), round(p[1] * (0.72 if p[1] > 0 else 0.92), 2)) + tuple(p[2:]) for p in opening]
OPEN_MM = [(round(p[0] * 0.97, 2), round(p[1] * (0.76 if p[1] > 0 else 0.88), 2)) + tuple(p[2:]) for p in opening]
# a two-bone tongue (root + tip) skinned in the inner frame, clipped to the cavity
TONGUE3 = [(-82, 104), (-68, 76), (-36, 56), (0, 50), (36, 56), (68, 76), (82, 104), (0, 122)]
hid, hx, hc = hero_number("S3 hero", "practiceMinutes", -122, -52, 244, 104, WP, align="center", wdth=100, ls=-3)
s.hero = hid
mouth_xml = node("S3 mouth", [node("S3 mouth breath", [node("S3 mouth elastic", [
    node("S3 mouth inner", [
        hx,
        node("S3 cavity", [
            E("ClippingShape", {"sourceId": MOUTH["open"], "name": "Cavity clip"}),
            shape("S3 teeth", [rect(124, 24, 9)], [fill(WP)], id=MOUTH["teeth"], y=-50),
            node("S3 tongue wag", [bone("S3 tongue root", 0, 96, [bone("S3 tongue tip", 0, -36, [
                shape("S3 tongue crease", [smooth_path([(0, -2), (0, 22)], closed=False)], [stroke("44000000", 5)])],
                id=MOUTH["TT"])], id=MOUTH["TB"])], id=MOUTH["tongue"]),
            shape("S3 tongue", [skinned_path(cubic_attrs(TONGUE3), TONGUE_W, [(MOUTH["TB"], 0, 96), (MOUTH["TT"], 0, 60)])],
                  [fill(PD)]),
        ]),
        shape("S3 opening", [cubic_path(opening, MOUTH["openverts"])], [fill(DD)], id=MOUTH["open"]),
        shape("S3 lip glint", [ellipse(90, 16)], [fill("66FFFFFF", feather=(4,))], x=-70, y=-96, rot=-0.15),
        shape("S3 lip glint 2", [ellipse(40, 10)], [fill("55FFFFFF", feather=(3,))], x=86, y=104, rot=-0.3),
    ], id=MOUTH["inner"]),
    shape("S3 lips", [cubic_path(LIPS, MOUTH["lipverts"])], shade_fills(P, PD, PL, 1.6), id=MOUTH["lips"]),
], id=MOUTH["elastic"])], id=MOUTH["breath"])], id=MOUTH["outer"], x=195, y=548)
# the mouth's own frame: identity inside scene 3's art, blended into cover space (_mixMouth) by the signature 3->4 so
# the lips -> bubble cover fills the whole canvas whatever its size
_a3, _mixm = art(3), vmx("_mixMouth")
mouth_frame = ((COVER[0] - _a3[0]) / _a3[2] * _mixm, (COVER[1] - _a3[1]) / _a3[2] * _mixm,
               1 + (COVER[2] / _a3[2] - 1) * _mixm)
s.parts.append(node("S3 mouth frame", [mouth_xml], binds=frame_binds(mouth_frame, "S3 mouth frame")))
pop(s, MOUTH["outer"], 6, 40, "el2", s0=0.15)
s.track(MOUTH["open"], "scaleY", [(0, 0.05, "hold"), (16, 0.05, "el"), (64, 1, "hold")])
s.track(MOUTH["teeth"], "opacity", [(0, 0, "hold"), (30, 0, "lin"), (40, 1, "hold")])
s.track(hid, "scaleY", [(0, 0.2, "hold"), (22, 0.2, "el"), (80, 1, "hold")])
count(s, 22, 86)
for i, (syl, x, y, col, r) in enumerate([("ah", 54, 404, P, -0.25), ("oh", 334, 420, D, 0.2), ("mm", 322, 700, WP, 0.15)]):
    cid_ = nid()
    sid, st = disp(30, col, 800)
    s.parts.append(text(f"S3 syllable {syl}", x, y, [st], [run(sid, syl)], id=cid_, ox=0.5, oy=0.5, rot=r))
    pop(s, cid_, 44 + i * 8, 24, "back", rot0=r - 0.8, rot1=r)
    s.itrack(cid_, "y", [(0, y, "sine"), (120, y - 10, "sine"), (240, y, "hold")])
for i, (x, y, sz, col) in enumerate([(64, 640, 22, WP), (336, 560, 16, D)]):
    sp = nid()
    s.parts.append(sparkle(f"S3 sparkle {i}", sz, col, x, y, id=sp))
    pop(s, sp, 70 + i * 8, 22, "back2", rot0=-1)
    s.itrack(sp, "rotation", [(0, 0, "sine"), (120, 0.5, "sine"), (240, 0, "hold")])
s.parts.append(ground("S3 shadow", 260, 30, "55A894E6", 195, 718))
S3_TALK = [(0, opening, "sine"), (26, OPEN_OH, CLOSE_E), (50, opening, OPEN_E), (84, OPEN_EE, "sine"), (104, OPEN_EE, CLOSE_E),
           (124, OPEN_MM, OPEN_E), (146, opening, "sine"), (174, OPEN_OH, CLOSE_E), (198, opening, "sine"), (240, opening, "hold")]
S3_IDLE = Anim("S3 mouth talk (idle tracks)", 240)
key_morph(S3_IDLE, MOUTH["openverts"], S3_TALK, opening)
# lips: squash and stretch trailing each cavity shape by 4 frames, with an overshoot
LIPS_SS = {id(opening): (1, 1), id(OPEN_OH): (0.95, 1.05), id(OPEN_EE): (1.04, 0.96), id(OPEN_MM): (1.02, 0.97)}
for i_, prop_ in enumerate(("scaleX", "scaleY")):
    S3_IDLE.k(MOUTH["breath"], prop_, [(min(240, f + 4) if 0 < f < 240 else f, LIPS_SS[id(p)][i_], "back" if e != "hold" else e)
                                        for f, p, e in S3_TALK])
S3_IDLE.k(MOUTH["teeth"], "y", [(0, -50, "sine"), (26, -55, CLOSE_E), (50, -50, OPEN_E), (84, -45, "sine"), (104, -45, CLOSE_E),
                                (124, -47, OPEN_E), (146, -50, "sine"), (174, -55, CLOSE_E), (198, -50, "sine"), (240, -50, "hold")])
S3_IDLE.k(MOUTH["TT"], "y", [(0, -36, "sine"), (30, -36, "sine"), (44, -58, "back"), (60, -40, "sine"), (88, -60, "sine"),
                             (104, -50, "sine"), (128, -30, "sine"), (150, -36, "sine"), (180, -56, "back"), (200, -36, "sine"),
                             (240, -36, "hold")])
S3_IDLE.k(MOUTH["TT"], "rotation", [(0, 0, "sine"), (36, 0.14, "sine"), (52, -0.1, "sine"), (68, 0.06, "sine"), (96, 0, "sine"),
                                    (150, -0.12, "sine"), (166, 0.12, "sine"), (184, -0.05, "sine"), (210, 0, "sine"), (240, 0, "hold")])
S3_IDLE.k(MOUTH["TT"], "scaleX", [(0, 1, "sine"), (26, 0.82, "sine"), (52, 1, "sine"), (86, 1.08, "sine"), (124, 0.9, "sine"),
                                  (150, 1, "sine"), (176, 0.82, "sine"), (204, 1, "sine"), (240, 1, "hold")])
S3_IDLE.k(MOUTH["TB"], "x", [(0, 0, "sine"), (60, 7, "sine"), (120, -5, "sine"), (190, 4, "sine"), (240, 0, "hold")])
for obj_, props_ in S3_IDLE.tracks.items():
    for prop_, (kind_, keys_) in props_.items():
        s.itrack(obj_, prop_, keys_, kind_)

# ---------- 4. Phrases saved -------------------------------------------------
s = Scene(4, D)
hid, hx, hc = hero_number("S4 hero", "phrasesSaved", 24, HERO_Y, 342, HERO_SIZE, WP, wdth=100, ls=-5)
s.blk = "t"
s.parts.append(hx)
s.blk = "a"
s.hero = hid
rise(s, hid, 10, base_y=HERO_Y, dy=34, dur=22, ease="back")
count(s, 20, 82)
ids4 = top_copy(s, 4, ink=WP, w=272)
ids4.update(caption(s, 4, ink=LL))
# word-shaped blocks cascade from the upper right into the gap between two giant block quotes
WORDS = [("ありがとう", L, D, 318, 222, 0.36, True), ("merci", Y, D, 344, 292, -0.32, False),
         ("ciao", L, D, 338, 392, 0.36, False), ("hola", P, D, 246, 414, -0.1, False),
         ("안녕", P, D, 312, 452, -0.16, True), ("hallo", LL, D, 214, 470, 0.36, False),
         ("olá", Y, D, 150, 448, -0.3, False), ("привет", L, D, 284, 516, 0.1, False)]
BLANKS = [(P, 344, 162, 28, 40, -0.4), (Y, 282, 262, 22, 22, 0.3), (L, 350, 344, 26, 26, 0.5), (Y, 140, 404, 30, 30, 0.4),
          (LL, 262, 474, 16, 34, 0.4), (Y, 350, 470, 18, 40, 0.5), (L, 96, 476, 32, 28, -0.4)]
CONF = [(P, 274, 300, 9), (P, 206, 536, 14), (L, 206, 574, 14), (Y, 120, 362, 8)]
blk = []
for i, (word, bgc, ink, rx, ry, rr, cjk) in enumerate(WORDS):
    wid, inner = nid(), nid()
    if cjk:
        wpx = 26 + len(word) * 20
        sid, st = body(19, ink, 600, font=F_CJK)
    else:
        wpx = 26 + len(word) * 12.5
        sid, st = body(21, ink, 600)
    s.parts.insert(0, node(f"S4 word {i}", [node(f"S4 word float {i}", [
        text(f"S4 word text {i}", 0, 0, [st], [run(sid, word)], ox=0.5, oy=0.5),
        shape(f"S4 word block {i}", [rect(wpx, 44, 13)], shade_fills(bgc, {P: PD, L: LD, Y: YD, LL: L}[bgc], bgc, 0.35)),
    ], id=inner)], id=wid, x=rx, y=ry, rot=rr))
    blk.append((wid, inner, rx, ry, rr))
for i, (col, x, y, w_, h_, r) in enumerate(BLANKS):
    wid, inner = nid(), nid()
    s.parts.insert(0, node(f"S4 blank {i}", [node(f"S4 blank float {i}", [
        shape(f"S4 blank block {i}", [rect(w_, h_, 7)], shade_fills(col, {P: PD, L: LD, Y: YD, LL: L}[col], col, 0.25))],
        id=inner)], id=wid, x=x, y=y, rot=r))
    blk.append((wid, inner, x, y, r))
for i, (col, x, y, sz) in enumerate(CONF):
    wid, inner = nid(), nid()
    s.parts.insert(0, node(f"S4 confetti {i}", [node(f"S4 confetti float {i}", [
        shape(f"S4 diamond {i}", [rect(sz, sz, 2)], [fill(col)], rot=0.785)], id=inner)], id=wid, x=x, y=y))
    blk.append((wid, inner, x, y, 0))
# the cascade: everything falls in along the diagonal from top-right, lands with a tilt overshoot
blk.sort(key=lambda b: b[3])
for i, (wid, inner, rx, ry, rr) in enumerate(blk):
    f0 = 22 + i * 3.2
    s.track(wid, "x", [(0, rx + 140, "hold"), (f0, rx + 140, "out"), (f0 + 30, rx, "hold")])
    s.track(wid, "y", [(0, ry - 300, "hold"), (f0, ry - 300, (0.25, 1.25, 0.5, 1)), (f0 + 30, ry, "hold")])
    s.track(wid, "rotation", [(0, rr + 1.4, "hold"), (f0, rr + 1.4, "back"), (f0 + 34, rr, "hold")])
    s.track(wid, "opacity", [(0, 0, "hold"), (f0, 1, "hold")])
    s.itrack(inner, "y", [(0, 0, "sine"), (60 + (i * 13) % 90, -6, "sine"), (240, 0, "hold")])
    s.itrack(inner, "rotation", [(0, 0, "sine"), (120, 0.06 * (1 if i % 2 else -1), "sine"), (240, 0, "hold")])
# a slow stream of tiny blocks keeps pouring into the quotes (idle, seamless)
for i, col in enumerate([Y, L, P]):
    tid = nid()
    s.parts.insert(0, shape(f"S4 pour {i}", [rect(12, 16, 4)], [fill(col)], id=tid, x=300, y=300, op=0))
    st0 = i * 70
    s.itrack(tid, "x", [(0, 330, "hold"), (st0, 330, "in"), (st0 + 90, 206, "hold"), (st0 + 92, 330, "hold"), (240, 330, "hold")])
    s.itrack(tid, "y", [(0, 250, "hold"), (st0, 250, "in"), (st0 + 90, 560, "hold"), (st0 + 92, 250, "hold"), (240, 250, "hold")])
    s.itrack(tid, "rotation", [(0, 0, "hold"), (st0, 0, "lin"), (st0 + 90, 3.2, "hold"), (st0 + 92, 0, "hold"), (240, 0, "hold")])
    s.itrack(tid, "opacity", [(0, 0, "hold"), (st0, 0, "lin"), (st0 + 12, 1, "hold"), (st0 + 74, 1, "lin"),
                              (st0 + 90, 0, "hold"), (240, 0, "hold")])
    s.settle(tid, "opacity", 0)
# the giant block quotes (concept screen 4)
QUOTES, QL, QR = nid(), nid(), nid()
qkids = []
for qid, qx in ((QL, -92), (QR, 92)):
    qkids.append(node("S4 quote", [
        shape("S4 quote glint", [ellipse(60, 14)], [fill("66FFFFFF", feather=(4,))], x=-14, y=-94),
        shape("S4 quote body", [smooth_path(block_quote_pts(1.0))], shade_fills(Y, YD, "FFFFF6B8", 1.0)),
    ], id=qid, x=qx))
s.parts.append(node("S4 quotes", qkids, id=QUOTES, x=195, y=574))
for i, qid in enumerate((QL, QR)):
    f0 = 8 + i * 6
    s.track(qid, "y", [(0, 260, "hold"), (f0, 260, (0.3, 1.35, 0.55, 1)), (f0 + 30, 0, "hold")])
    s.track(qid, "scaleY", [(0, 1.3, "hold"), (f0 + 20, 1.3, "lin"), (f0 + 28, 0.82, "el"), (f0 + 70, 1, "hold")])
    s.track(qid, "scaleX", [(0, 0.8, "hold"), (f0 + 20, 0.8, "lin"), (f0 + 28, 1.14, "el"), (f0 + 70, 1, "hold")])
    s.itrack(qid, "rotation", [(0, 0, "sine"), (120, 0.025 * (1 if i else -1), "sine"), (240, 0, "hold")])
for i, (x, y, r) in enumerate([(50, 420, -0.55), (34, 456, -1.0), (370, 610, 0.6), (30, 640, -0.3)]):
    tk = nid()
    s.parts.append(shape(f"S4 tick {i}", [rect(5, 28, 2.5)], [fill(Y)], id=tk, x=x, y=y, rot=r))
    pop(s, tk, 46 + i * 5, 20, "back")
    s.itrack(tk, "opacity", [(0, 1, "sine"), (40 + i * 30, 0.3, "sine"), (240, 1, "hold")])
s.parts.append(ground("S4 shadow L", 150, 22, "CC2A1640", 104, 694))
s.parts.append(ground("S4 shadow R", 150, 22, "CC2A1640", 288, 694))

# ---------- 5. Topics explored ----------------------------------------------
s = Scene(5, Y)
hid, hx, hc = hero_number("S5 hero", "topicsExplored", 24, HERO_Y, 342, HERO_SIZE, D, align="right", wdth=100, ls=-5)
s.blk = "t"
s.parts.append(hx)
s.blk = "a"
s.hero = hid
rise(s, hid, 10, base_y=HERO_Y, dy=34, dur=22, ease="back")
count(s, 20, 82)
ids5 = top_copy(s, 5, align="right")
ids5.update(caption(s, 5, align="right", ink=D))
RING = nid()
RING_SPIN = nid()
bub5 = []


def symbol(kind, col):
    if kind == "sun":
        return node("sym sun", [shape("core", [ellipse(30, 30)], [fill(col)]),
                                shape("ring", [ellipse(52, 52)], [stroke(col, 5)])])
    if kind == "leaf":
        return shape("sym leaf", [smooth_path([(0, -30, "c", 2), (20, 0), (0, 30, "c", 2), (-20, 0)])], [fill(col)], rot=0.6)
    if kind == "star":
        return shape("sym star", [E("Star", {"width": 54, "height": 54, "points": 5, "innerRadius": 0.5,
                                             "cornerRadius": 3, "name": "Path"})], [fill(col)])
    if kind == "wave":
        return shape("sym wave", [smooth_path([(-26, 0), (-13, -12), (0, 0), (13, 12), (26, 0)], closed=False)],
                     [stroke(col, 7)])
    if kind == "cup":
        return node("sym cup", [shape("cup", [rect(34, 30, 8)], [fill(col)], y=4),
                                shape("handle", [ellipse(16, 16)], [stroke(col, 5)], x=20, y=2),
                                shape("steam", [smooth_path([(-6, -26), (0, -34), (-4, -42)], closed=False)],
                                      [stroke(col, 4)], y=0)])
    return node("sym dots", [shape("d", [ellipse(14, 14)], [fill(col)], x=x_) for x_ in (-18, 0, 18)])


ring_kids = []
for i, (bcol, shade, light, sym_a, sym_b, inkc) in enumerate([(P, PD, PL, "sun", "leaf", WP), (L, LD, LL, "star", "wave", D),
                                                              (D, DD, DL, "cup", "dots", Y)]):
    ang = -math.pi / 2 + i * 2 * math.pi / 3
    bx, by = 104 * math.cos(ang), 104 * math.sin(ang)
    b_id, cr, sa, sb = nid(), nid(), nid(), nid()
    ring_kids.append(node(f"S5 bubble {i}", [node(f"S5 bubble upright {i}", [
        node("sym a", [symbol(sym_a, inkc)], id=sa, y=-6),
        node("sym b", [symbol(sym_b, inkc)], id=sb, y=-6, op=0),
        shape(f"S5 bubble body {i}", [smooth_path(bubble_pts(0.52, i == 1))], shade_fills(bcol, shade, light, 0.52)),
    ], id=cr)], id=b_id, x=bx, y=by))
    bub5.append((b_id, cr, sa, sb))
    pop(s, b_id, 20 + i * 8, 30, "back")
    st0 = 100 + i * 40
    s.itrack(sa, "opacity", [(0, 1, "hold"), (st0, 1, "lin"), (st0 + 12, 0, "hold"), (st0 + 300, 0, "lin"), (st0 + 312, 1, "hold"), (720, 1, "hold")])
    s.itrack(sb, "opacity", [(0, 0, "hold"), (st0, 0, "lin"), (st0 + 12, 1, "hold"), (st0 + 300, 1, "lin"), (st0 + 312, 0, "hold"), (720, 0, "hold")])
    s.itrack(sa, "scaleX", [(0, 1, "hold"), (st0, 1, "in"), (st0 + 12, 0.3, "hold"), (st0 + 300, 0.3, "back"), (st0 + 324, 1, "hold"), (720, 1, "hold")])
    s.itrack(sb, "scaleX", [(0, 0.3, "hold"), (st0, 0.3, "back"), (st0 + 24, 1, "hold"), (st0 + 300, 1, "in"), (st0 + 312, 0.3, "hold"), (720, 0.3, "hold")])
    s.itrack(cr, "rotation", [(0, 0, "lin"), (720, -2 * math.pi, "hold")])
orbit = shape("S5 orbit", [ellipse(208, 208)], [stroke("663D2456", 2.5, effects=[E("DashPath", {"name": "Dots"}, [
    E("Dash", {"length": 2, "name": "On"}), E("Dash", {"length": 12, "name": "Off"})])])], id=nid())
s.parts.append(node("S5 ring", [node("S5 ring spin", ring_kids + [orbit], id=RING_SPIN)], id=RING, x=195, y=548))
s.track(RING, "rotation", [(0, -2.4, "hold"), (14, -2.4, "out"), (80, 0, "hold")])
s.itrack(RING_SPIN, "rotation", [(0, 0, "lin"), (720, 2 * math.pi, "hold")])
for i, (x, y, sz, col) in enumerate([(60, 430, 22, D), (336, 680, 18, P), (70, 690, 14, WP)]):
    sp = nid()
    s.parts.append(sparkle(f"S5 sparkle {i}", sz, col, x, y, id=sp))
    pop(s, sp, 60 + i * 8, 22, "back2", rot0=-1)
s.parts.append(ground("S5 shadow", 240, 26, "55E2D15A", 195, 712))
s.idle_dur = 720

# ---------- 6. Languages practised ------------------------------------------
s = Scene(6, WP)
hid, hx, hc = hero_number("S6 hero", "languagesPractised", 24, HERO_Y, 342, HERO_SIZE, D, wdth=100, ls=-5)
s.blk = "t"
s.parts.append(hx)
s.blk = "a"
s.hero = hid
rise(s, hid, 10, base_y=HERO_Y, dy=34, dur=22, ease="back")
count(s, 20, 82)
ids6 = top_copy(s, 6)
ids6.update(caption(s, 6))
RIB = []
DY6 = 104
S6_CLIP, S7_CLIP = nid(), nid()   # art-column clips (side by side), see the scene emission


def tails(pts, length=260):
    """Straight bleed extensions continuing an open path's end tangents, so a band that runs off the 390 frame
    still runs off a wider canvas (in the stacked arrangement the art is never wider than the canvas)."""
    def ext(a, b):
        dx, dy = a[0] - b[0], a[1] - b[1]
        d = math.hypot(dx, dy)
        return [(a[0] + dx / d * length, a[1] + dy / d * length), a]
    return ext(pts[0], pts[1]), ext(pts[-1], pts[-2])
rib_specs = [
    (P, [(-40, 400), (60, 360), (170, 420), (270, 470), (430, 420)], "hello · hola · ciao · hallo · olá · hej · ", WP, None),
    (L, [(-40, 520), (80, 450), (190, 390), (300, 430), (430, 500)], "merci · grazie · danke · obrigado · ", D, C_RIB2),
    (D, [(-40, 460), (90, 540), (210, 500), (320, 380), (430, 360)], "привет · γεια · salut · ahoj · ", Y, C_RIB3),
]
rib_specs = [(c, [(x, y + DY6) for x, y in pts], w, ink, oc) for c, pts, w, ink, oc in rib_specs]
rib_parts = []
for i, (col, pts, words, ink, opconv) in enumerate(rib_specs):
    rid, sid_, trim, tmod, grp = nid(), nid(), nid(), nid(), nid()
    st_id, st = body(15, ink, 700)
    words_text = text(f"S6 ribbon words {i}", 0, 0, [st], [run(st_id, words * 2)], id=nid(), extra_children=[
        E("TextModifierGroup", {"name": "Follow ribbon", "id": grp}, [
            E("TextModifierRange", {"modifyFrom": 0, "modifyTo": 1, "name": "All"}),
            E("TextFollowPathModifier", {"targetId": sid_, "orient": True, "offset": 0, "name": "Follow",
                                         "id": tmod})])])
    tl, tr = tails(pts)
    tail_l, tail_r = nid(), nid()
    rib = node(f"S6 ribbon {i}", [
        words_text,
        shape(f"S6 ribbon tail L {i}", [smooth_path(tl, closed=False)], [stroke(col, 36)], id=tail_l),
        shape(f"S6 ribbon tail R {i}", [smooth_path(tr, closed=False)], [stroke(col, 36)], id=tail_r),
        shape(f"S6 ribbon band {i}", [smooth_path(pts, closed=False, id=nid())],
              [E("Stroke", {"thickness": 36, "cap": "round", "join": "round", "name": "Band"},
                 [solid(col), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Reveal",
                                             "id": trim})])], id=sid_),
    ], id=rid, binds=[bind(V("languagesPractised"), 18, opconv)] if opconv else None)
    RIB.append((rid, sid_, trim, tmod))
    rib_parts.append(rib)
    f0 = 20 + i * 12
    s.track(trim, "end", [(0, 0, "hold"), (f0, 0, "io"), (f0 + 44, 1, "hold")])
    s.track(tail_l, "opacity", [(0, 0, "hold"), (f0, 1, "hold")])
    s.track(tail_r, "opacity", [(0, 0, "hold"), (f0 + 42, 1, "hold")])
    drift = -0.12 if i != 1 else 0.12
    s.itrack(tmod, "offset", [(0, 0, "sine"), (300, drift, "sine"), (600, 0, "hold")])
    s.itrack(rid, "y", [(0, 0, "sine"), (150 + i * 20, -8 + i * 5, "sine"), (600, 0, "hold")])
# The weave: one segment of the plum ribbon is drawn again over the lilac ribbon, so the plum band passes over
# the lilac and *under* the persimmon one. It sits between those two in the draw order (top first: persimmon,
# weave, lilac, plum), draws on with the plum band's reveal and drifts with it.
W0, W1 = 0.62, 0.78
weave_id, weave_trim = nid(), nid()
weave = shape("S6 weave (plum over lilac, under persimmon)", [smooth_path(rib_specs[2][1], closed=False)],
              [E("Stroke", {"thickness": 36, "cap": "butt", "join": "round", "name": "Band"},
                 [solid(D), E("TrimPath", {"start": W0, "end": W1, "modeValue": "sequential", "name": "Segment",
                                           "id": weave_trim})])],
              id=weave_id, binds=[bind(V("languagesPractised"), 18, C_RIB3)])


def _io_time(y, c=(0.65, 0, 0.35, 1)):
    """Time fraction at which the cubic ease c reaches progress y (bisection)."""
    bz = lambda t, a, b: 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi) / 2
        if bz(m, c[1], c[3]) < y:
            lo = m
        else:
            hi = m
    # convert the bezier parameter to time
    return bz(lo, c[0], c[2])


_f0 = 20 + 2 * 12   # the plum band's reveal: trim end 0 -> 1 from _f0 to _f0 + 44 ("io")
s.track(weave_trim, "end", [(0, W0, "hold"), (_f0 + 44 * _io_time(W0), W0, "lin"), (_f0 + 44 * _io_time(W1), W1, "hold")])
s.itrack(weave_id, "y", [(0, 0, "sine"), (150 + 2 * 20, -8 + 2 * 5, "sine"), (600, 0, "hold")])
s.parts.append(node("S6 ribbons", [E("ClippingShape", {"sourceId": S6_CLIP, "name": "Art column clip"}),
                                   rib_parts[0], weave] + rib_parts[1:], id=nid()))
s.parts.append(ground("S6 shadow", 300, 26, "44C7B7F2", 195, 712))
s.idle_dur = 600

# ---------- 7. Day practice streak ------------------------------------------
s = Scene(7, P)
ids7 = top_copy(s, 7, unit=False, head_y=92, ink=DD, f0=40, head_lines=2)
ids7["sup_rng"], m = kinetic(units=2, y=14, ease=(0.4, 0, 0.2, 1))
ids7["sup"], ids7["sup_c"], t_ = bound_text("S7 support", 24, 92 + 2 * 39 + 14, 342, "screen7Support", font="body",
                                            size=16, color=DD, wght=500, lh=21, sizing="fixed", h=44,
                                            overflow="ellipsis", mods=[m])
s.blk = "t"
s.parts.append(t_)
s.blk = "a"
sweep(s, ids7["sup_rng"], 76, 30, 0.4)
hid, hx, hc = hero_number("S7 hero", "longestStreakDays", 24, 540, 342, 176, DD, wdth=100, ls=-6)
s.blk = "b"
s.parts.append(hx)
s.hero = hid
rise(s, hid, 30, base_y=540, dy=34, dur=22, ease="back")
count(s, 30, 92)
u7rng, m = kinetic(units=0, y=0, x=-14, ease=(0.4, 0, 0.2, 1))
u7, u7c, t_ = bound_text("S7 unit", 24, 724, 342, "screen7Unit", size=UNIT_SIZE, color=DD, wght=650, wdth=96,
                         sizing="fixed", h=34, overflow="fitFontSize", wrap="noWrap", ls=-0.3, mods=[m])
s.parts.append(t_)
s.blk = "a"
sweep(s, u7rng, 50, 26, 0.3)
LINE = nid()
LINE_TRIM = nid()
line_pts = [(-30, 330), (120, 292), (330, 330), (360, 390), (240, 430), (60, 450), (40, 500), (160, 548), (420, 528)]
tokens7 = []
for i, (ch, col) in enumerate([(".", WP), (",", DD), (";", WP), ("!", DD), ("?", WP)]):
    tid, bounce, fp = nid(), nid(), nid()
    sid, st = disp(58, col, 800)
    d0 = 0.08 + i * 0.2
    tokens7.append(E("Node", {"name": f"S7 hop {i}", "id": tid}, [
        E("FollowPathConstraint", {"targetId": LINE, "distance": d0, "orient": False, "name": "Ride line", "id": fp}),
        node(f"S7 hop bounce {i}", [text(f"S7 hop glyph {i}", 0, 0, [st], [run(sid, ch)], ox=0.5, oy=1)], id=bounce)]))
    s.itrack(fp, "distance", [(0, d0, "sine"), (240, d0 + 0.08, "sine"), (480, d0, "hold")])
    s.itrack(bounce, "y", sum([[(j * 40, -4, "out"), (j * 40 + 20, -40, "in")] for j in range(12)], []) + [(480, -4, "hold")])
    s.itrack(bounce, "scaleY", sum([[(j * 40, 0.8, "out"), (j * 40 + 8, 1.12, "sine"), (j * 40 + 34, 1, "in")]
                                    for j in range(12)], []) + [(480, 0.8, "hold")])
    pop(s, tid, 50 + i * 8, 24, "back")
tl7, tr7 = tails(line_pts)
LT7 = [nid(), nid()]
s.parts.append(node("S7 sentence", [E("ClippingShape", {"sourceId": S7_CLIP, "name": "Art column clip"})] + tokens7 + [
    shape("S7 line tail L", [smooth_path(tl7, closed=False)], [stroke(WP, 9)], id=LT7[0]),
    shape("S7 line tail R", [smooth_path(tr7, closed=False)], [stroke(WP, 9)], id=LT7[1]),
    shape("S7 line tail shadow L", [smooth_path(tl7, closed=False)], [stroke(PD, 9)], x=3, y=6),
    shape("S7 line tail shadow R", [smooth_path(tr7, closed=False)], [stroke(PD, 9)], x=3, y=6),
    shape("S7 line", [smooth_path(line_pts, closed=False)],
          [E("Stroke", {"thickness": 9, "cap": "round", "join": "round", "name": "Line"},
             [solid(WP), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Draw",
                                        "id": LINE_TRIM})])], id=LINE),
    shape("S7 line shadow", [smooth_path(line_pts, closed=False)], [stroke(PD, 9)], x=3, y=6),
], id=nid()))
s.track(LINE_TRIM, "end", [(0, 0, "hold"), (8, 0, "io"), (70, 1, "hold")])
s.track(LT7[0], "opacity", [(0, 0, "hold"), (8, 1, "hold")])
s.track(LT7[1], "opacity", [(0, 0, "hold"), (68, 1, "hold")])
s.idle_dur = 480

# ---------- 8. Voice notes ---------------------------------------------------
s = Scene(8, D)
hid, hx, hc = hero_number("S8 hero", "voiceNotes", 24, HERO_Y, 342, HERO_SIZE, WP, align="center", wdth=100, ls=-5)
s.blk = "t"
s.parts.append(hx)
s.blk = "a"
s.hero = hid
rise(s, hid, 10, base_y=HERO_Y, dy=34, dur=22, ease="back")
count(s, 20, 82)
ids8 = top_copy(s, 8, ink=WP, align="center")
ids8.update(caption(s, 8, ink=LL, align="center"))
BARS = []
heights = [36, 62, 104, 150, 92, 132, 172, 124, 80, 140, 100, 58, 34]
bar_kids = []
for i, hgt in enumerate(heights):
    b = nid()
    x = (i - 6) * 20
    bar_kids.append(shape(f"S8 bar {i}", [rect(11, hgt, 5.5)], [fill(P if i % 3 == 1 else (Y if i % 5 == 0 else WP))],
                          id=b, x=x))
    BARS.append(b)
    s.track(b, "scaleY", [(0, 0.05, "hold"), (12 + abs(i - 6) * 3, 0.05, "el"), (52 + abs(i - 6) * 3, 1, "hold")])
    seq = [(0, 1, "sine")]
    for j in range(6):
        seq.append((j * 40 + 20, 0.45 + 0.1 * ((i + j) % 4), "sine"))
        seq.append((j * 40 + 40, 1, "sine"))
    seq[-1] = (240, 1, "hold")
    s.itrack(b, "scaleY", seq)
SPEECH = nid()
SPEECH_TRIM = nid()
SPEECH_FILL = nid()
speech = node("S8 speech shape", [
    shape("S8 speech outline", [smooth_path(bubble_pts(1.08))],
          [E("Stroke", {"thickness": 9, "cap": "round", "join": "round", "name": "Outline"},
             [solid(L), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Draw",
                                       "id": SPEECH_TRIM})])]),
    shape("S8 speech fill", [smooth_path(bubble_pts(1.08))], [fill("33C7B7F2")], id=SPEECH_FILL),
], id=SPEECH, x=195, y=528)
s.parts.append(node("S8 voice", bar_kids, id=(VOICE := nid()), x=195, y=528))
s.parts.append(speech)
for i, (x, y, sz, col) in enumerate([(60, 440, 20, Y), (340, 640, 16, L), (330, 430, 12, P)]):
    sp = nid()
    s.parts.append(sparkle(f"S8 sparkle {i}", sz, col, x, y, id=sp))
    pop(s, sp, 90 + i * 8, 22, "back2", rot0=-1)
    s.itrack(sp, "rotation", [(0, 0, "sine"), (120, 0.5, "sine"), (240, 0, "hold")])
s.parts.append(ground("S8 shadow", 220, 24, "CC2A1640", 195, 716))
s.track(SPEECH_TRIM, "end", [(0, 0, "hold"), (50, 0, "io"), (100, 1, "hold")])
s.track(SPEECH_FILL, "opacity", [(0, 0, "hold"), (80, 0, "out"), (110, 1, "hold")])
s.track(SPEECH, "scaleX", [(0, 0.6, "hold"), (50, 0.6, "back"), (100, 1, "hold")])
s.track(SPEECH, "scaleY", [(0, 0.6, "hold"), (50, 0.6, "back"), (100, 1, "hold")])
s.itrack(SPEECH, "rotation", [(0, 0, "sine"), (120, 0.04, "sine"), (240, 0, "hold")])

# ---------- 9. Persona -------------------------------------------------------
s = Scene(9, L)
p9 = {}
p9["label"], p9["label_c"], tl_ = flow_text("S9 label", 342, "personaLabel", font="body", size=16, color=D, wght=500)
rise(s, p9["label"], 70, base_y=0, dy=10)
p9["title_rng"], m = kinetic(units=0, y=34, scale=(0.6, 0.2), ease=(0.3, -0.7, 0.5, 1))
p9["title"], p9["title_c"], tt_ = flow_text("S9 title", 342, "personaName", size=52, color=D, wght=800, lh=52, wdth=94,
                                         ls=-1.2, mods=[m])
p9["desc_rng"], m = kinetic(units=2, y=18, ease=(0.4, -0.3, 0.3, 1))
p9["desc"], p9["desc_c"], td_ = flow_text("S9 description", 342, "personaDescription", size=22, color=D, wght=600,
                                       lh=27, wdth=96, mods=[m])
s.blk = "t"
s.parts.append(column("S9 copy", 24, 104, 342, [tl_, tt_, td_], gap=8)[1])
s.blk = "a"
sweep(s, p9["title_rng"], 80, 30, 0.35)
sweep(s, p9["desc_rng"], 104, 30, 0.4)
STAGE_Y = 540
s.motifA = OFF_A   # the pair only passes through (anticipation), then hides inside the emblem
s.motifB = OFF_B


WRAPS = set()


def blob(cx, cy, r, k, s_=1.0):
    pts = []
    for j in range(7):
        a = j * 2 * math.pi / 7
        rr = r * (0.72 + 0.28 * math.sin(j * 2.3 + k))
        pts.append(((cx + math.cos(a) * rr * 1.25) * s_, (cy + math.sin(a) * rr) * s_))
    return pts


def build_emblems(scale=1.0, tag="E"):
    """Four persona emblems with distinct silhouettes and choreography. Returns list of
    dict(root, xml, rev tracks, idle tracks, dur, ring colours)."""
    S_ = scale
    out = []
    rigged = tag == "E"     # the share cards' emblems are static: same art, no face rig

    def tick(name, x, y, rot, col, w=7, h=30):
        i_ = nid()
        return i_, shape(name, [rect(w * S_, h * S_, w * S_ / 2)], [fill(col)], id=i_, x=x * S_, y=y * S_, rot=rot)

    # 0 Conversation Starter: two laughing speech forms hug a little world (concept screen 9)
    ia, ib = {}, {}
    a = motif_bubble(f"{tag}0 bubble A", P, PD, False, 0.88 * S_, ids=ia, look=-22, rigged=rigged)
    b = motif_bubble(f"{tag}0 bubble B", L, LD, True, 0.84 * S_, ids=ib, look=22, rigged=rigged)
    root, globe, land, gclip = nid(), nid(), nid(), nid()
    R = 80
    lands = []
    for copy_ in (0, 1):
        for j, (cx, cy, r) in enumerate([(-40, -34, 34), (30, 14, 30), (-22, 52, 20), (54, -46, 16)]):
            lands.append(shape(f"{tag}0 land {copy_}{j}", [smooth_path(blob(cx + copy_ * 2 * R, cy, r, j, S_))],
                               [fill(Y)]))
    world = node(f"{tag}0 world", [
        shape(f"{tag}0 globe rim", [ellipse(2 * R * S_, 2 * R * S_)], [fill("55FFFFFF", feather=(6 * S_,))], x=-14 * S_,
              y=-16 * S_, op=0.6),
        node(f"{tag}0 lands", lands + [E("ClippingShape", {"sourceId": gclip, "name": "Clip to globe"})], id=land),
        shape(f"{tag}0 globe", [ellipse(2 * R * S_, 2 * R * S_)], shade_fills(D, DD, DL, 0.8 * S_)),
        shape(f"{tag}0 globe clip", [ellipse(2 * R * S_ - 2, 2 * R * S_ - 2)], [], id=gclip),
    ], id=globe, y=-40 * S_)
    ticks = [tick(f"{tag}0 tick {k}", x, y, r, c) for k, (x, y, r, c) in enumerate(
        [(-150, -176, -0.7, P), (-168, -138, -1.2, P), (12, -196, 0.05, D), (128, -184, 0.6, D), (150, -150, 1.0, D)])]
    xml = node(f"{tag}0 conversation starter", [t[1] for t in ticks] + [
        world,
        node(f"{tag}0 pair A", [a], x=-120 * S_, y=-78 * S_, rot=-0.1, sx=0.84),
        node(f"{tag}0 pair B", [b], x=122 * S_, y=-68 * S_, rot=0.1, sx=0.84)], id=root)
    rev = [(ia["root"], "x", [(0, -260 * S_, "hold"), (10, -260 * S_, (0.3, 1.3, 0.5, 1)), (40, 0, "hold")]),
           (ia["root"], "rotation", [(0, -0.8, "hold"), (10, -0.8, "back"), (44, 0, "hold")]),
           (ib["root"], "x", [(0, 260 * S_, "hold"), (16, 260 * S_, (0.3, 1.3, 0.5, 1)), (46, 0, "hold")]),
           (ib["root"], "rotation", [(0, 0.8, "hold"), (16, 0.8, "back"), (50, 0, "hold")]),
           (globe, "scaleX", [(0, 0, "hold"), (2, 0, "el2"), (44, 1, "hold")]),
           (globe, "scaleY", [(0, 0, "hold"), (2, 0, "el2"), (44, 1, "hold")]),
           (land, "x", [(0, -2 * R * S_, "hold"), (2, -2 * R * S_, "out"), (60, 0, "hold")])]
    # reveal: both burst out laughing as they land (the persona idle takes over with the conversation); every face
    # channel ends at rest, which is what the settled persona and the share card hold
    ta, tb = Talk(ia["rig"], 70, 0.4), Talk(ib["rig"], 70, 2.1)
    ta.laugh(28, 3, 9)
    tb.laugh(36, 3, 10)
    rev += (ta.build() + tb.build()) if rigged else []
    for k, (ti, _x) in enumerate(ticks):
        rev += [(ti, "scaleY", [(0, 0, "hold"), (44 + k * 4, 0, "back2"), (60 + k * 4, 1, "hold")])]
    WRAPS.add((land, "x"))  # two copies of the land, 2R apart: 0 -> -2R is a seamless spin
    idle = [(land, "x", [(0, 0, "lin"), (480, -2 * R * S_, "hold")]),
            (ia["bob"], "rotation", [(0, 0, "sine"), (120, 0.06, "sine"), (240, 0, "sine"), (480, 0, "hold")]),
            (ib["bob"], "rotation", [(0, 0, "sine"), (120, -0.06, "sine"), (240, 0, "sine"), (480, 0, "hold")]),
            ]
    # two conversations per loop: A starts the first, B the second; each looks across the globe to the other
    ta, tb = Talk(ia["rig"], 480, 0.4), Talk(ib["rig"], 480, 2.1)
    converse(ta, tb, 0, 1, -1)
    # second half: quieter -- both look out at the viewer, share one laugh, then glance back at each other
    for t_, d_, o_ in ((ta, 1, 0), (tb, -1, 7)):
        t_.look(250 + o_, -2 * d_, 2)
        t_.blink(276 + o_ * 3)
        t_.laugh(320 + o_, 3, 9 + o_ / 3)
        t_.look(372 + o_, 6 * d_, 0)
        t_.blink(420 - o_ * 2)
        t_.look(450, 0, 0, dur=12)
    idle += (ta.build() + tb.build()) if rigged else []
    for k, (ti, _x) in enumerate(ticks):
        idle.append((ti, "opacity", [(0, 1, "sine"), (60 + k * 50, 0.35, "sine"), (480, 1, "hold")]))
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 480, "rings": (LL, Y, WP), "ground": "55A894E6"})

    # 1 Phrase Collector: a quotation-mark archive (stacked index cards, each holding a kept phrase mark)
    root = nid()
    cards, rev, idle = [], [], []
    for i, (col, ink, shade) in enumerate([(WP, D, WD), (Y, D, YD), (P, WP, PD), (L, D, LD)]):
        cid_ = nid()
        sid, st = disp(110 * S_, ink, 800)
        cards.append(node(f"{tag}1 card {i}", [
            text(f"{tag}1 card mark {i}", 0, 28 * S_, [st], [run(sid, "”")], ox=0.5, oy=0.5),
            shape(f"{tag}1 card tab {i}", [rect(64 * S_, 22 * S_, 8 * S_)], shade_fills(col, shade, col, 0.3 * S_),
                  x=(-60 + i * 36) * S_, y=-84 * S_),
            shape(f"{tag}1 card face {i}", [rect(236 * S_, 156 * S_, 24 * S_)], shade_fills(col, shade, col, 0.9 * S_)),
        ], id=cid_, y=(i * 40 - 92) * S_, rot=(-0.12 + i * 0.08)))
        f0 = 4 + (3 - i) * 9
        ry = (i * 40 - 92) * S_
        rev += [(cid_, "y", [(0, -460 * S_, "hold"), (f0, -460 * S_, (0.3, 1.3, 0.5, 1)), (f0 + 26, ry, "hold")]),
                (cid_, "rotation", [(0, 0.8 - i * 0.3, "hold"), (f0, 0.8 - i * 0.3, "out"), (f0 + 30, -0.12 + i * 0.08, "hold")]),
                (cid_, "scaleY", [(0, 1, "hold"), (f0 + 24, 1, "lin"), (f0 + 28, 0.86, "el"), (f0 + 60, 1, "hold")])]
        idle.append((cid_, "y", [(0, ry, "sine"), (60 + i * 15, ry - 6 * (4 - i) * S_, "sine"), (240, ry, "hold")]))
    ticks = [tick(f"{tag}1 tick {k}", x, y, r, c) for k, (x, y, r, c) in enumerate(
        [(-150, -170, -0.7, Y), (150, -170, 0.7, Y), (0, -206, 0, L)])]
    xml = node(f"{tag}1 phrase collector", [t[1] for t in ticks] + cards[::-1], id=root)
    for k, (ti, _x) in enumerate(ticks):
        rev += [(ti, "scaleY", [(0, 0, "hold"), (50 + k * 4, 0, "back2"), (66 + k * 4, 1, "hold")])]
        idle.append((ti, "opacity", [(0, 1, "sine"), (60 + k * 40, 0.35, "sine"), (240, 1, "hold")]))
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 240, "rings": (L, P, Y), "ground": "CC2A1640"})

    # 2 Careful Listener: an open parenthesis that becomes an ear; another voice's ripples flow into it
    root, ear, inner, rip = nid(), nid(), nid(), []
    rev, idle = [], []
    kids = []
    for i in range(3):
        ri = nid()
        rip.append(ri)
        kids.append(shape(f"{tag}2 ripple {i}", [smooth_path([(0, -90 * S_), (40 * S_, 0), (0, 90 * S_)], closed=False)],
                          [stroke(D if i != 1 else P, 10 * S_)], id=ri, x=(40 + i * 40) * S_, y=-30 * S_))
    vb = {}
    voice = node(f"{tag}2 voice", [motif_bubble(f"{tag}2 voice bubble", L, LD, True, 0.42 * S_, ids=vb, look=-10, rigged=rigged)],
                 id=(VOICE_ID := nid()), x=150 * S_, y=-120 * S_)
    paren = [(34, -150), (-36, -82), (-56, 0), (-36, 82), (34, 150)]
    xml = node(f"{tag}2 careful listener", [voice] + kids + [
        node(f"{tag}2 ear", [
            shape(f"{tag}2 swirl", [smooth_path([(18 * S_, -62 * S_), (-16 * S_, -30 * S_), (-12 * S_, 12 * S_),
                                                 (16 * S_, 28 * S_), (6 * S_, 56 * S_)], closed=False)],
                  [stroke(P, 13 * S_)], id=inner, x=-4 * S_),
            shape(f"{tag}2 paren", [smooth_path([(x * S_, y * S_) for x, y in paren], closed=False)],
                  [E("Stroke", {"thickness": 52 * S_, "cap": "round", "join": "round", "name": "Stroke"},
                    [lingrad([(DL, 0), (D, 0.5), (DD, 1)], -60 * S_, -150 * S_, 40 * S_, 150 * S_)])]),
        ], id=ear, x=-62 * S_, y=-30 * S_)], id=root)
    rev += [(ear, "rotation", [(0, -1.4, "hold"), (4, -1.4, "back"), (40, 0, "hold")]),
            (ear, "scaleX", [(0, 0.2, "hold"), (4, 0.2, "el"), (56, 1, "hold")]),
            (ear, "scaleY", [(0, 0.2, "hold"), (4, 0.2, "el"), (56, 1, "hold")]),
            (inner, "opacity", [(0, 0, "hold"), (36, 0, "lin"), (46, 1, "hold")]),
            (VOICE_ID, "x", [(0, 300 * S_, "hold"), (20, 300 * S_, "back"), (50, 150 * S_, "hold")])]
    for i, ri in enumerate(rip):
        rev.append((ri, "opacity", [(0, 0, "hold"), (44 + i * 8, 0, "lin"), (54 + i * 8, 1, "hold")]))
        ph = i * 30
        idle += [(ri, "scaleY", [(0, 1, "sine"), (ph + 30, 1.18, "sine"), (ph + 90, 0.9, "sine"), (180, 1, "hold")]),
                 (ri, "opacity", [(0, 1, "sine"), (ph + 30, 0.45, "sine"), (ph + 90, 1, "hold"), (180, 1, "hold")])]
    idle += [(inner, "rotation", [(0, 0, "sine"), (90, 0.12, "sine"), (180, 0, "hold")])]
    tv = Talk(vb["rig"], 180, 3.3)
    monologue(tv, -1)
    idle += tv.build() if rigged else []
    tv = Talk(vb["rig"], 60)
    tv.say(4, "a o e", 10, end="rest")
    rev += [(o_, p_, [(f + 50, v, e) for f, v, e in ks]) for o_, p_, ks in tv.build()] if rigged else []
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 180, "rings": (P, L, WP), "ground": "66E2D15A"})

    # 3 Brave Improviser: an elastic exclamation mark that jumps, squashes and bursts
    root, dot, squash = nid(), nid(), nid()
    rev, idle = [], []
    bursts = []
    kids = []
    for i in range(7):
        ang = -math.pi / 2 + (i - 3) * 0.42
        bi = nid()
        bursts.append(bi)
        kids.append(shape(f"{tag}3 burst {i}", [rect(9 * S_, 36 * S_, 4.5 * S_)], [fill(P if i % 2 else D)], id=bi,
                          x=math.cos(ang) * 168 * S_, y=math.sin(ang) * 168 * S_ - 10 * S_, rot=ang + math.pi / 2))
    bar = [(0, -132), (40, -100), (26, 60), (0, 78), (-26, 60), (-40, -100)]
    xml = node(f"{tag}3 brave improviser", kids + [node(f"{tag}3 bang", [
        node(f"{tag}3 squash", [
            shape(f"{tag}3 bar glint", [rect(14 * S_, 110 * S_, 7 * S_)], [fill("77FFFFFF", feather=(4 * S_,))],
                  x=-14 * S_, y=-30 * S_, rot=0.04),
            shape(f"{tag}3 bar", [smooth_path([(x * S_, y * S_) for x, y in bar])],
                  shade_fills(P, PD, PL, 1.0 * S_)),
        ], id=squash, y=-30 * S_),
        shape(f"{tag}3 dot", [ellipse(76 * S_, 76 * S_)], shade_fills(D, DD, DL, 0.4 * S_), id=dot, y=96 * S_),
    ], y=-24 * S_)], id=root)
    rev += [(squash, "y", [(0, -560 * S_, "hold"), (4, -560 * S_, "in"), (24, -30 * S_, "hold")]),
            (squash, "scaleY", [(0, 1.3, "hold"), (24, 1.3, "lin"), (28, 0.62, "el"), (70, 1, "hold")]),
            (squash, "scaleX", [(0, 0.8, "hold"), (24, 0.8, "lin"), (28, 1.32, "el"), (70, 1, "hold")]),
            (dot, "scaleX", [(0, 0, "hold"), (30, 0, "back2"), (46, 1, "hold")]),
            (dot, "scaleY", [(0, 0, "hold"), (30, 0, "back2"), (46, 1, "hold")])]
    for i, bi in enumerate(bursts):
        rev += [(bi, "scaleY", [(0, 0, "hold"), (28 + i * 2, 0, "back2"), (44 + i * 2, 1, "hold")])]
        idle.append((bi, "scaleY", [(0, 1, "sine"), (40, 0.4, "sine"), (80, 1, "hold"), (160, 1, "hold")]))
    idle += [(squash, "y", [(0, -30 * S_, "out"), (28, -90 * S_, "in"), (56, -30 * S_, "hold"), (160, -30 * S_, "hold")]),
             (squash, "scaleY", [(0, 1, "lin"), (56, 1, "lin"), (60, 0.8, "el"), (110, 1, "hold"), (160, 1, "hold")]),
             (squash, "scaleX", [(0, 1, "lin"), (56, 1, "lin"), (60, 1.15, "el"), (110, 1, "hold"), (160, 1, "hold")])]
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 160, "rings": (L, Y, P), "ground": "55C7B7F2"})
    return out


def emblem_stage(EM, scale, tag):
    """Shared base under every persona emblem: three swirl rings (colour keyed per persona), a soft ground pool and
    sparkles. Returns (xml, ids)."""
    S_ = scale
    ids = {"rings": [], "ring_c": [], "trim": [], "ground_c": nid(), "sparks": [], "root": nid()}
    rings = []
    for k, (w_, h_, th, rot) in enumerate([(330, 84, 18, -0.08), (296, 62, 11, 0.1), (356, 100, 5, 0.02)]):
        rid, cid, tid = nid(), nid(), nid()
        ids["rings"].append(rid)
        ids["ring_c"].append(cid)
        ids["trim"].append(tid)
        rings.append(shape(f"{tag} ring {k}", [ellipse(w_ * S_, h_ * S_)],
                           [E("Stroke", {"thickness": th * S_, "cap": "round", "name": "Ring"},
                              [solid(EM[0]["rings"][k], id=cid),
                               E("TrimPath", {"start": 0, "end": 1, "offset": k * 0.3, "modeValue": "sequential",
                                              "name": "Draw", "id": tid})])], id=rid, y=100 * S_, rot=rot))
    sparks = []
    for k, (x, y, sz, col) in enumerate([(-170, 54, 30, Y), (-78, 118, 30, D), (156, 52, 26, D), (110, 134, 18, D),
                                         (-176, 128, 14, Y), (176, 6, 18, Y)]):
        si = nid()
        ids["sparks"].append(si)
        sparks.append(sparkle(f"{tag} sparkle {k}", sz * S_, col, x * S_, y * S_, id=si))
    xml = node(f"{tag} stage", sparks + [e["xml"] for e in EM] + rings + [
        shape(f"{tag} ground", [ellipse(240 * S_, 34 * S_)], [fill(EM[0]["ground"], cid=ids["ground_c"], feather=(10 * S_,))],
              y=186 * S_)], id=ids["root"])
    return xml, ids


EMB = build_emblems(1.0, "E")
stage_xml, STG = emblem_stage(EMB, 1.0, "S9")
s.parts.append(node("S9 emblem", [stage_xml], id=(EMB_STAGE := nid()), x=195, y=STAGE_Y))
# the motif pair's collapse (frame ~68) releases a ring burst: swirl rings draw on, sparkles pop
for k, (rid, tid) in enumerate(zip(STG["rings"], STG["trim"])):
    s.track(tid, "end", [(0, 0, "hold"), (60 + k * 6, 0, (0.2, 0, 0.2, 1)), (102 + k * 6, 1, "hold")])
    s.track(rid, "scaleX", [(0, 0.3, "hold"), (58, 0.3, "back"), (94 + k * 6, 1, "hold")])
for k, si in enumerate(STG["sparks"]):
    pop(s, si, 68 + k * 5, 22, "back2", rot0=-1.4)
    s.itrack(si, "rotation", [(0, 0, "sine"), (120, 0.5 * (1 if k % 2 else -1), "sine"), (240, 0, "hold")])
s.idle_dur = 240

# ---------- 10. Summary ------------------------------------------------------
s = Scene(10, D)
sum_h = {}
sum_h["head_rng"], m = kinetic(units=2, y=36, rot=0.08)
# bounded: two headline lines (fit) + one support line, so long copy never reaches the card at y 196
hb = dict(sizing="fixed", h=70, overflow="fitFontSize", valign="top")
sb = dict(font="body", size=15, color=LL, wght=500, lh=20, sizing="fixed", h=22, overflow="ellipsis", wrap="noWrap")
sum_h["head"], sum_h["head_c"], ta_ = bound_text("S10 headline", 0, 0, 342, "summaryHeadline", size=32, color=WP, wght=800,
                                                lh=34, wdth=96, ls=-0.5, mods=[m], **hb)
sum_h["sup"], _c, tb_ = bound_text("S10 support", 0, 74, 342, "summarySupport", **sb)
sum_h["ehead"], _c, tc_ = bound_text("S10 empty headline", 0, 0, 342, "emptyHeadline", size=32, color=WP, wght=800,
                                     lh=34, wdth=96, ls=-0.5, **hb)
sum_h["esup"], _c, td_ = bound_text("S10 empty support", 0, 74, 342, "emptySupport", **sb)
sum_h["col"] = nid()
sum_h["ecol"] = nid()
s.blk = "t"
s.parts += [node("S10 copy", [ta_, tb_], id=sum_h["col"], x=24, y=90),
            node("S10 new-user copy", [tc_, td_], id=sum_h["ecol"], x=24, y=90, op=0)]
sweep(s, sum_h["head_rng"], 18, 36)
rise(s, sum_h["sup"], 40, base_y=74, dy=10)
CARD = nid()
CARD_SM = nid()
CARD_AB = nid()
CARDW, CARDW_SM, CARDW_AB = nid(), nid(), nid()
s.blk = "a"   # tall card: the stacked portrait arrangement
s.parts.insert(0, E("NestedArtboard", {"artboardId": CARD_AB, "x": 24, "y": 196, "name": "S10 share card", "id": CARD},
                    [E("NestedStateMachine", {"animationId": CARD_SM, "name": "Card machine"})]))
s.blk = "w"   # wide card: side-by-side arrangements (landscape, short portrait)
s.parts.insert(0, E("NestedArtboard", {"artboardId": CARDW_AB, "x": 0, "y": 0, "name": "S10 share card wide",
                                       "id": CARDW},
                    [E("NestedStateMachine", {"animationId": CARDW_SM, "name": "Wide card machine"})]))
s.blk = "a"
# the card is thrown up from below, overshoots, tilts back and lands with a squash
s.track(CARD, "y", [(0, 900, "hold"), (6, 900, (0.25, 1.25, 0.5, 1)), (40, 196, "hold")])
s.track(CARD, "rotation", [(0, 0.35, "hold"), (6, 0.35, "back"), (48, 0, "hold")])
s.track(CARD, "scaleY", [(0, 1.08, "hold"), (36, 1.08, "lin"), (42, 0.95, "el"), (80, 1, "hold")])
s.track(CARDW, "y", [(0, 640, "hold"), (6, 640, (0.25, 1.25, 0.5, 1)), (40, 0, "hold")])
s.track(CARDW, "rotation", [(0, 0.2, "hold"), (6, 0.2, "back"), (48, 0, "hold")])
s.track(CARDW, "scaleY", [(0, 1.08, "hold"), (36, 1.08, "lin"), (42, 0.95, "el"), (80, 1, "hold")])
count(s, 60, 120)

# ================================================================ CHROME
# Chrome follows the real canvas: wordmark and year sit in the margins, the progress row spans the real width, the
# controls hug the bottom corners (Continue narrows on small phones, never below 150), and the tap zones split the
# real width into thirds. _k scales it all (0.85 keeps every control at 44+).
CH = {}
chrome = []
viewport_kids = []
# top: wordmark + year
CH["wm_c"] = nid()
CH["dot_c"] = nid()
sid, st = disp(21, D, 750, wdth=92, cid=CH["wm_c"], ls=-0.3)
# concept wordmark: "Parlance" in heavy title case; the comma is a tiny persimmon speech mark
chrome.append(node("Chrome wordmark", [
    text("Chrome wordmark text", 0, 0, [st], [run(sid, "Parlance")])], x=24, y=30,
    binds=[lbind(13, M, "chrome left"), lbind(14, TOP * (30 / 80), "wordmark y"), lbind(16, K, "k"), lbind(17, K, "k")]))
CH["year_c"] = nid()
sid, st = disp(15, D, 600, cid=CH["year_c"])
chrome.append(text("Chrome year", 366, 35, [st], [run(sid, "2026", [bind(V("year"), 268, C_STR0)])], ox=1,
                   binds=[lbind(13, VW - M, "chrome right"), lbind(14, TOP * (35 / 80), "year y"), lbind(16, K, "k"),
                          lbind(17, K, "k")]))
# progress segments: a flex row stretched between the margins; hidden scenes are display:none so exactly the
# visible count renders
SEG = {}
seg_kids = []
for k in range(1, 11):
    SEG[k] = {"lc": nid(), "style": nid(), "fill": nid(), "fstyle": nid(), "track_c": nid(), "fill_c": nid()}
    seg_kids.append(E("LayoutComponent", {"width": 10, "height": 3.5, "styleId": SEG[k]["style"], "name": f"Segment {k}",
                                          "id": SEG[k]["lc"]}, [
        E("LayoutComponentStyle", {"layoutWidthScaleType": "fill", "cornerRadiusTL": 2, "name": f"Segment {k} style",
                                   "id": SEG[k]["style"]}),
        E("LayoutComponent", {"width": 100, "height": 3.5, "styleId": SEG[k]["fstyle"], "name": f"Segment {k} fill",
                              "id": SEG[k]["fill"]}, [
            E("LayoutComponentStyle", {"positionTypeValue": "absolute", "widthUnitsValue": "percent",
                                       "layoutHeightScaleType": "fill", "cornerRadiusTL": 2,
                                       "name": f"Segment {k} fill style", "id": SEG[k]["fstyle"]}),
            bind(V("currentScreen"), 16, C_SEG[k]),
            fill(P, cid=SEG[k]["fill_c"])]),
        fill("333D2456", cid=SEG[k]["track_c"])]))
viewport_kids.append(E("LayoutComponent", {"width": 342, "height": 3.5, "styleId": (PSTYLE := nid()),
                                           "name": "Progress", "id": (PROG := nid())},
                       [lbind(7, VW - 2 * M, "progress width"), E("LayoutComponentStyle", {"flexDirectionValue": "row", "gapHorizontal": 4,
                                                   "gapHorizontalUnitsValue": "points", "positionTypeValue": "absolute",
                                                   "positionLeft": 24, "positionTop": 66,
                                                   "positionLeftUnitsValue": "points",
                                                   "positionTopUnitsValue": "points", "name": "Progress style",
                                                   "id": PSTYLE},
                          [lbind(516, M, "chrome left"), lbind(518, TOP * (66 / 80), "progress y")])]
                       + seg_kids))

# bottom controls (inside a focus scope that also hosts the keyboard listeners)
BTN = {}
IS_SUM = xclamp(vmx("currentScreen") - 9, 0, 1)
CTRL_Y = BOT + xmax(0.325 * (VH - BOT), 26 * K)   # 790 at 844 tall; never rides up over the content band
CONT_W = xclamp((VW - 2 * M) / K - 118, 150, 224)     # Continue's width in button units (224 at 390 wide)
HIDE = -3000
CTRL_X = {   # (story mode, summary mode); HIDE takes a control off the canvas
    "Previous": (M + 26 * K, M + 26 * K),
    "Pause": (M + 86 * K, HIDE),
    "Continue": (VW - M - CONT_W / 2 * K, HIDE),
    "Replay": (HIDE, VW - M - 208 * K),
    "Share": (HIDE, VW - M - 70 * K),
}


def button(key, idx, x, y, w, h, label_prop=None, icon=None, label_size=17, flex=False):
    """flex: the width follows CONT_W (surface, focus ring, hit area, label box and arrow all bound)."""
    b = {"id": nid(), "bg_c": nid(), "ink_c": nid(), "ring": nid(), "x": x, "w": w, "focus": nid()}
    wb = (lambda key_, e: [lbind(key_, e, f"{key} width")]) if flex else (lambda key_, e: None)
    kids = [E("FocusData", {"name": "Focus", "id": b["focus"]}),
            E("SemanticData", {"role": "button", "label": PROPS[label_prop][2], "name": "Semantics"},
              [bind(V(label_prop), 983)])]
    if label_prop and icon is None:
        sid, st = disp(label_size, WP, 700, cid=b["ink_c"])
        kids.append(text(f"{key} label", -w / 2 + 22, -12, [st], [run(sid, PROPS[label_prop][2], [bind(V(label_prop), 268)])],
                         w=w - 64, h=26, sizing="fixed", overflow="fitFontSize", wrap="noWrap", align="center",
                         binds=(wb(13, CONT_W * -0.5 + 22) or []) + (wb(285, CONT_W - 64) or [])))
        kids.append(shape(f"{key} arrow", [smooth_path([(-8, -7), (0, 0), (-8, 7)], closed=False)],
                          [stroke(WP, 2.6, cid=(b.setdefault("ink2_c", nid())))], x=w / 2 - 26,
                          binds=wb(13, CONT_W * 0.5 - 26)))
        kids.append(shape(f"{key} arrow stem", [rect(16, 2.6, 1.3)], [fill(WP, cid=b.setdefault("ink3_c", nid()))],
                          x=w / 2 - 33, binds=wb(13, CONT_W * 0.5 - 33)))
    elif icon:
        kids += icon(b)
    kids.append(shape(f"{key} focus ring", [rect(w + 10, h + 10, (h + 10) / 2, binds=wb(20, CONT_W + 10))],
                      [stroke(P, 3)], id=b["ring"], binds=[bind(V("_focusIndex"), 18, C_FOCUS[idx])]))
    kids.append(shape(f"{key} surface", [rect(w, h, h / 2, binds=wb(20, CONT_W))], [fill(D, cid=b["bg_c"])]))
    kids += [rect(w, h, h / 2, binds=wb(20, CONT_W)), fill(CLEAR)]  # hit geometry of the button itself
    sx_, sm_ = CTRL_X[key]
    pos = [lbind(13, xlerp(sx_, sm_, IS_SUM), f"{key} x"), lbind(14, CTRL_Y, "controls y"), lbind(16, K, "k"),
           lbind(17, K, "k")]
    xml = E("Shape", {"x": x, "y": y, "isTargetOpaque": True, "name": key, "id": b["id"]}, pos + kids)
    b["xml"] = xml
    b["idx"] = idx
    BTN[key] = b
    return xml


def icon_prev(b):
    return [shape("prev arrow", [smooth_path([(4, -8), (-4, 0), (4, 8)], closed=False)], [stroke(WP, 3, cid=b["ink_c"])], x=-2)]


def icon_pause(b):
    b["bars"] = nid()
    b["tri"] = nid()
    b["ink2_c"] = nid()
    return [node("pause bars", [shape("bar l", [rect(5, 18, 2)], [fill(WP, cid=b["ink_c"])], x=-5),
                                shape("bar r", [rect(5, 18, 2)], [fill(WP, cid=(b.setdefault("ink3_c", nid())))], x=5)], id=b["bars"]),
            shape("play triangle", [smooth_path([(-6, -9, "c", 2), (9, 0, "c", 2), (-6, 9, "c", 2)])], [fill(WP, cid=b["ink2_c"])],
                  id=b["tri"], x=1, op=0)]


controls = [
    button("Previous", 1, 50, 790, 52, 52, "previousLabel", icon=icon_prev),
    button("Pause", 2, 110, 790, 52, 52, "pauseLabel", icon=icon_pause),
    button("Continue", 3, 254, 790, 224, 56, "continueLabel", flex=True),
    button("Replay", 4, -400, 790, 128, 52, "replayLabel", label_size=16),
    button("Share", 5, -400, 790, 140, 52, "shareLabel", label_size=16),
]
KEYHOST = nid()
chrome.append(E("Node", {"name": "Controls", "id": KEYHOST}, [E("FocusData", {"canFocus": False, "name": "Focus scope"})] + controls))

# navigation regions (transparent but hit-testable); declared after controls so buttons win. The left third of the
# real width goes back, the right two-thirds go forward; both span the story area between chrome and controls.
NAV_L, NAV_R = nid(), nid()
NAV_Y = TOP + 16 * K
NAV_H = BOT - 12 * K - NAV_Y
chrome.append(shape("Nav back region", [rect(130, 656, 0, 0, 0, binds=[lbind(20, VW / 3, "third"), lbind(21, NAV_H, "nav h")])],
                    [fill(CLEAR)], id=NAV_L, x=0, y=96, binds=[lbind(14, NAV_Y, "nav y")]))
chrome.append(shape("Nav next region", [rect(260, 656, 0, 0, 0, binds=[lbind(20, VW * (2 / 3), "two thirds"),
                                                                        lbind(21, NAV_H, "nav h")])],
                    [fill(CLEAR)], id=NAV_R, x=130, y=96, binds=[lbind(13, VW / 3, "third"), lbind(14, NAV_Y, "nav y")]))
# the mouth hit target lives in the art space of scene 2 (laughing form) or 3 (elastic mouth)
mouth_hit_xml = node("Mouth hit frame", [E("Shape", {"x": -500, "y": -500, "isTargetOpaque": True,
                                                     "name": "Mouth hit (signature interaction)", "id": MOUTH_HIT},
                                           [rect(10, 10), fill(CLEAR)])],
                     binds=frame_binds(tuple(xlerp(a, b, xclamp(vmx("currentScreen") - 2, 0, 1))
                                             for a, b in zip(art(2), art(3))), "Mouth hit frame"))

# global motif, each in its own frame (scene art space <-> cover space)
mA = node("Motif A frame", [motif_bubble("Motif A", P, PD, False, 1.0, ids=MA, morph=True)],
          binds=frame_binds(motif_frame("_mixA"), "Motif A frame"))
mB = node("Motif B frame", [motif_bubble("Motif B", L, LD, True, 1.0, ids=MB, tongue=P, morph=True)],
          binds=frame_binds(motif_frame("_mixB"), "Motif B frame"))
# hidden drivers (two-way bound: their animated x writes the view model)
MIXA_DRV, MIXB_DRV, MAP_DRV, MIXM_DRV = nid(), nid(), nid(), nid()
driver_xml = node("Drivers", [
    node("Hero reveal driver", [], id=DRIVER, x=1, binds=[bind(V("_heroReveal"), 13, None, twoWay=True)]),
    node("Motif A cover mix driver", [], id=MIXA_DRV, x=1, binds=[bind(V("_mixA"), 13, None, twoWay=True)]),
    node("Motif B cover mix driver", [], id=MIXB_DRV, x=1, binds=[bind(V("_mixB"), 13, None, twoWay=True)]),
    node("Motif scene map driver", [], id=MAP_DRV, x=1, binds=[bind(V("_motifMap"), 13, None, twoWay=True)]),
    node("Mouth cover mix driver", [], id=MIXM_DRV, x=0, binds=[bind(V("_mixMouth"), 13, None, twoWay=True)]),
])
# aperture used by the signature transition (quote-shaped clip for scene 4)
# One quote-shaped aperture is the clip source for every scene: a pair of commas whose 9 vertices morph from two
# round dots (":") into a quotation mark, then open until the next scene fills the frame. It lives in cover space,
# so at full size it opens past every edge of any canvas.
APER = nid()
APER_BLOOM = nid()
APER_V = {"L": [nid() for _ in COMMA], "R": [nid() for _ in COMMA]}
aperture = node("Cover frame", [node("Quote aperture", [
    shape("Aperture bloom", [ellipse(100, 100)], [], id=APER_BLOOM, sx=0.01, sy=0.01),
    shape("Aperture comma L", [cubic_path(COMMA_DOT, APER_V["L"])], [], x=-54),
    shape("Aperture comma R", [cubic_path(COMMA_DOT, APER_V["R"])], [], x=54),
], id=APER, x=195, y=430, sx=0.01, sy=0.01)], binds=frame_binds(COVER, "Cover frame"))
# the plate under every scene: the colour of the speech form that just filled the frame, seen around the
# aperture while it opens (and around the closing quote on the way back)
PLATE, PLATE_C = nid(), nid()
plate_xml = shape("Transition plate", [rect(W + 40, H + 40, 0, 0, 0, binds=[lbind(20, VW + 40, "bleed w"),
                                                                            lbind(21, VH + 40, "bleed h")])],
                  [fill(P, cid=PLATE_C)], id=PLATE, x=-20, y=-20)
# restrained paper grain over the whole canvas (under the chrome): a 5x3 grid of the 390x844 tile around the
# centre, scaled up only when a canvas outgrows it, so its grain size stays the same on every screen
GRAIN_N = nid()
grain_tiles = [E("Image", {"assetId": GRAIN, "x": i * 390, "y": j * 844, "scaleX": 2, "scaleY": 2,
                           "blendModeValue": "overlay", "name": f"grain {i},{j}"})
               for j in (-1, 0, 1) for i in (-2, -1, 0, 1, 2)]
GSC = xmax(1, xmax(VW / 1950, VH / 2532))
grain_xml = node("Grain", grain_tiles, id=GRAIN_N, op=0.55,
                 binds=[lbind(13, VW / 2, "centre x"), lbind(14, VH / 2, "centre y"), lbind(16, GSC, "grain scale"),
                        lbind(17, GSC, "grain scale")])

# clock component placement
CLOCK = nid()
CLOCK_AB = nid()
CLOCK_SM = nid()
clock_xml = E("NestedArtboard", {"artboardId": CLOCK_AB, "x": -100, "y": -100, "name": "Dwell clock", "id": CLOCK}, [
    bind(V("autoAdvanceSeconds"), 907, C_CLOCK),
    bind(V("isPaused"), 895),
    E("NestedStateMachine", {"animationId": CLOCK_SM, "name": "Clock machine"})])

# scene backgrounds + roots. Each scene is
#   anchor (canvas centre) > root (keyed: opacity, handoff offsets and scale, aperture clip) > pivot (back to the
#   canvas origin) > frames (one per layout block: copy on top, art below) + a background that bleeds 10% past
#   every edge, so a handoff that shrinks the scene about the centre never shows a gap.
BLOCK_ORDER = ("t", "b", "w", "a")
scene_xml = []
for n in range(10, 0, -1):
    sc = SCENES[n]
    sc.bg_id = nid()
    sc.bg_c = nid()
    if n == 9:
        bgfill = fill(L, cid=sc.bg_c, binds=[bind(V("personaColor"), 37)])
    else:
        bgfill = fill(sc.bg, cid=sc.bg_c)
    fr = frames(n)
    sc.frames = {}
    kids = []
    for key in BLOCK_ORDER:
        items = [x for b_, x in sc.parts if b_ == key]
        if not items:
            continue
        binds = frame_binds(art(n) if key == "a" else fr[key], f"S{n} {key}")
        # the wide card only on canvases wider than tall; a tall landscape canvas keeps the tall card in its art
        # column, where it can use the height
        if n == 10 and key == "a":
            binds.append(lbind(18, 1 - WIDE, "tall card"))
        if n == 10 and key == "w":
            binds.append(lbind(18, WIDE, "wide card"))
        sc.frames[key] = nid()
        kids.append(node(f"S{n} frame {key}", items, id=sc.frames[key], binds=binds))
    kids.append(shape(f"S{n} background", [rect(W + 40, H + 40, 0, 0, 0, binds=[lbind(20, VW * 1.2 + 40, "bg w"),
                                                                               lbind(21, VH * 1.2 + 40, "bg h")])],
                      [bgfill], id=sc.bg_id, x=-20, y=-20,
                      binds=[lbind(13, VW * -0.1 - 20, "bg x"), lbind(14, VH * -0.1 - 20, "bg y")]))
    if n in (6, 7):
        # side by side, bands that bleed off the canvas are cut at the art column's left edge (never under the copy)
        cl = xlerp(-200, fr["artL"] - 12, SPL)
        kids.append(shape(f"S{n} art column clip", [rect(W + 400, H + 400, 0, 0, 0,
                                                         binds=[lbind(20, VW + 400 - cl, "clip w"),
                                                                lbind(21, VH + 400, "clip h")])], [],
                          id=S6_CLIP if n == 6 else S7_CLIP, x=-200, y=-200, binds=[lbind(13, cl, "clip x")]))
    sc.clip = nid()
    clip = [E("ClippingShape", {"sourceId": APER, "isVisible": False, "name": "Quote aperture clip", "id": sc.clip})]
    pivot = node(f"Scene {n} pivot", kids, binds=[lbind(13, VW * -0.5, "-centre x"), lbind(14, VH * -0.5, "-centre y")])
    root = E("Node", {"name": f"Scene {n}", "id": sc.root, "opacity": 1 if n == 1 else 0}, clip + [pivot])
    scene_xml.append(node(f"Scene {n} anchor", [root], binds=[lbind(13, VW / 2, "centre x"), lbind(14, VH / 2, "centre y")]))

# ================================================================ EVENTS
EV = {k: nid() for k in ("screenChanged", "shareTapped", "recapFinished", "mouthTapped")}
events = [
    E("Event", {"name": "screenChanged", "id": EV["screenChanged"]},
      [E("CustomPropertyNumber", {"propertyValue": 1, "name": "screen"}, [bind(V("currentScreen"), 243)])]),
    E("Event", {"name": "shareTapped", "id": EV["shareTapped"]}),
    E("Event", {"name": "recapFinished", "id": EV["recapFinished"]}),
    E("Event", {"name": "mouthTapped", "id": EV["mouthTapped"]},
      [E("CustomPropertyBoolean", {"propertyValue": False, "name": "soundEnabled"}, [bind(V("soundEnabled"), 245)])]),
]

# ================================================================ ANIMATIONS
ANIMS = []


def anim(name, dur, loop=None, scene=None, motif_map=None):
    a = Anim(name, dur, loop)
    a.motif_map = motif_map or ([(0, scene, "hold")] if scene in (1, 2, 3, 9) else None)
    ANIMS.append(a)
    return a


EMPTY = anim("Empty", 1)


def hide_others(a, n, frame=0, keep=()):
    for m in range(1, 11):
        if m != n and m not in keep:
            a.hold(SCENES[m].root, "opacity", 0, frame=frame)


def root_reset(a, sc, opacity=1):
    a.hold(sc.root, "opacity", opacity)
    a.hold(sc.root, "x", 0)
    a.hold(sc.root, "y", 0)
    a.hold(sc.root, "scaleX", 1)
    a.hold(sc.root, "scaleY", 1)
    a.hold(sc.root, "rotation", 0)


def mouth_hit(a, sc):
    if sc.mouth_hit:
        x, y, w, h = sc.mouth_hit
        a.hold(MOUTH_HIT, "x", x)
        a.hold(MOUTH_HIT, "y", y)
        a.hold(MOUTH_HIT, "scaleX", w / 10)
        a.hold(MOUTH_HIT, "scaleY", h / 10)
    else:
        a.hold(MOUTH_HIT, "x", -500)
        a.hold(MOUTH_HIT, "y", -500)


def apply_final(a, sc, frame=0):
    for (obj, prop_), (v, kind) in sc.final.items():
        a.k(obj, prop_, [(frame, v, "hold")], kind)


def apply_enter(a, sc, offset=0, scale=1.0):
    for obj, prop_, keys, kind in sc.enter:
        a.k(obj, prop_, [(offset + f * scale, v, e) for f, v, e in keys], kind)


def clip(a, sc, keys):
    """keys: [(frame, bool)] for this scene's quote-aperture clip."""
    a.k(sc.clip, "isVisible", [(f, v, "hold") for f, v in keys], kind="b")


def motif_pose(a, M, keys, morph=None):
    """Motif transform keys plus (optionally) its true body morph: morph = [(frame, BUB_* table, ease)]."""
    motif_keys(a, M, keys)
    offscreen = all(k[1][:2] in (OFF_A[:2], OFF_B[:2]) for k in keys)
    if morph or not offscreen:   # an off-stage form keeps whatever shape it had; elongate() always re-keys it
        morph_motif(a, M, morph or [(keys[0][0], BUB_REST, "hold")])


def aperture_open(a, f0=0, rot0=-0.35, flip=False):
    """THE SIGNATURE, second half: two dots (":") sprout comma tails into a quotation mark that opens until the
    next scene fills the frame. ~40 frames. flip turns the mark into an opening quote."""
    base = math.pi if flip else 0.0
    a.k(APER, "scaleX", [(0, 0.5, "hold"), (f0, 0.5, "back"), (f0 + 10, 1.2, (0.6, 0, 0.9, 0.5)), (f0 + 34, 14, "hold")])
    a.k(APER, "scaleY", [(0, 0.5, "hold"), (f0, 0.5, "back"), (f0 + 10, 1.2, (0.6, 0, 0.9, 0.5)), (f0 + 34, 14, "hold")])
    a.k(APER, "rotation", [(0, base + rot0, "hold"), (f0, base + rot0, "out"), (f0 + 34, base + rot0 + 0.3, "hold")])
    a.k(APER, "y", [(0, 430, "hold"), (f0 + 10, 430, "in"), (f0 + 34, 380, "hold")])
    for side in ("L", "R"):
        key_morph(a, APER_V[side], [(0, COMMA_DOT, "hold"), (f0 + 1, COMMA_DOT, (0.3, 1.5, 0.5, 1)), (f0 + 13, COMMA, "hold")],
                  COMMA_DOT)
    a.k(APER_BLOOM, "scaleX", [(0, 0.01, "hold"), (f0 + 12, 0.01, "in"), (f0 + 34, 2.6, "hold")])
    a.k(APER_BLOOM, "scaleY", [(0, 0.01, "hold"), (f0 + 12, 0.01, "in"), (f0 + 34, 2.6, "hold")])


def aperture_close(a, f1=30):
    """Designed reverse: the scene shrinks into a closing quotation mark, whose tails retract into two dots that
    blink out -- the signature transition played backwards."""
    a.k(APER, "scaleX", [(0, 14, "out"), (f1 * 0.55, 1.1, "in"), (f1 * 0.85, 0.55, "in"), (f1, 0.0, "hold")])
    a.k(APER, "scaleY", [(0, 14, "out"), (f1 * 0.55, 1.1, "in"), (f1 * 0.85, 0.55, "in"), (f1, 0.0, "hold")])
    a.k(APER, "rotation", [(0, -0.05, "out"), (f1, -0.4, "hold")])
    a.k(APER, "y", [(0, 380, "out"), (f1 * 0.55, 430, "hold")])
    for side in ("L", "R"):
        key_morph(a, APER_V[side], [(0, COMMA, "hold"), (f1 * 0.5, COMMA, "in"), (f1 * 0.85, COMMA_DOT, "hold")],
                  COMMA_DOT)
    a.k(APER_BLOOM, "scaleX", [(0, 2.6, "out"), (f1 * 0.45, 0.01, "hold")])
    a.k(APER_BLOOM, "scaleY", [(0, 2.6, "out"), (f1 * 0.45, 0.01, "hold")])


def plate(a, color, frame=0):
    a.k(PLATE_C, "colorValue", [(frame, color, "hold")], kind="c")


# Which speech form elongates into each scene (its colour must differ from that scene's background)
COVER_INTO = {1: "A", 2: "A", 3: "A", 4: "A", 5: "A", 6: "B", 7: "B", 8: "A", 9: "A", 10: "B"}
MOT = {"A": (MA, OFF_A, COVER_A, P), "B": (MB, OFF_B, COVER_B, L)}


def elongate(a, which, start=None, dur=32):
    """THE SIGNATURE, first half: a speech form swings in, gathers (squash = anticipation), then its tail and body
    truly elongate (vertex morph) until it fills the frame. Its colour is left on the plate."""
    M, off, cover, col = MOT[which]
    start = start or off
    mid = (195 + (90 if which == "A" else -90), 560, 1.25, 1.25, (0.3 if which == "A" else -0.3), 1)
    motif_pose(a, M, [(0, start, "out"), (dur * 0.3, mid, (0.5, 0, 0.3, 1)), (dur, cover, "hold")],
               [(0, BUB_REST, "hold"), (dur * 0.08, BUB_REST, "out"), (dur * 0.3, BUB_SQUASH, (0.5, 0, 0.2, 1)),
                (dur, BUB_TALL, "hold")])
    a.k(M["face"], "opacity", [(0, 1, "hold"), (dur * 0.45, 1, "lin"), (dur * 0.7, 0, "hold")])
    t = Talk(M["rig"], dur)
    t.mouth(0, "rest", "sine")
    t.mouth(dur * 0.3, "o", OPEN_E)              # gather: a little gulp while the body squashes
    t.mouth(dur * 0.55, "ha", "hold")           # stretch: a wide whoop as it elongates
    t.eye(0, "open", "sine")
    t.eye(dur * 0.3, "wide", (0.5, 0, 0.6, 1))
    t.eye(dur * 0.55, "squint", "hold")
    t.brows(0, -7, 0.12, dur=dur * 0.3)
    t.look(0, 0, -3, dur=dur * 0.3)
    face_tracks(a, t.build(end_rest=False))
    plate(a, col)


for n in range(1, 11):
    sc = SCENES[n]
    a_pose, b_pose = sc.motifA, sc.motifB

    # ---- In (forward): the frame is one solid speech-form colour; the scene opens through a quote aperture ----
    a = anim(f"{n:02d} In", 130, scene=n)
    sc.anim_in = a
    hide_others(a, n)
    root_reset(a, sc)
    mouth_hit(a, sc)
    if n == 1:
        # intro / replay: the covering speech form deflates (TALL -> SQUASH -> REST) into the motif pair
        clip(a, sc, [(0, False)])
        motif_pose(a, MA, [(0, COVER_A, (0.6, 0, 0.25, 1)), (34, a_pose, "hold")],
                   [(0, BUB_TALL, (0.6, 0, 0.25, 1)), (26, BUB_SQUASH, "el"), (60, BUB_REST, "hold")])
        motif_pose(a, MB, [(0, OFF_B, "hold"), (18, (60, b_pose[1] + 80) + b_pose[2:5] + (1,), "back"), (48, b_pose, "hold")],
                   [(0, BUB_REST, "hold"), (40, BUB_SQUASH, "el"), (70, BUB_REST, "hold")])
        apply_enter(a, sc)
    else:
        clip(a, sc, [(0, True), (36, False)])
        aperture_open(a, 0, rot0=-0.35 + 0.12 * (n % 3), flip=(n % 2 == 1))
        for M, pose, off in ((MA, a_pose, OFF_A), (MB, b_pose, OFF_B)):
            if pose[:2] == off[:2]:
                motif_pose(a, M, [(0, off, "hold")])
            else:
                motif_pose(a, M, [(0, off, "hold"), (14, off, "back"), (46, pose, "hold")])
        apply_enter(a, sc, offset=8)

    # ---- Back-in (designed reverse): the lilac form that filled the frame deflates down-left ----
    a = anim(f"{n:02d} Back In", 84, scene=n)
    sc.anim_backin = a
    hide_others(a, n)
    root_reset(a, sc)
    mouth_hit(a, sc)
    clip(a, sc, [(0, False)])
    a.k(sc.root, "x", [(0, -40, "hold"), (6, -40, "out"), (40, 0, "hold")])
    a.k(sc.root, "rotation", [(0, -0.03, "hold"), (6, -0.03, "out"), (40, 0, "hold")])
    end_b = b_pose if b_pose[:2] != OFF_B[:2] else (-200, 1000, 1.1, 1.1, -0.6, 1)
    motif_pose(a, MB, [(0, COVER_B, (0.55, 0, 0.3, 1)), (30, end_b, "hold")] + ([(31, b_pose, "hold")] if end_b != b_pose else []),
               [(0, BUB_TALL, (0.4, 0, 0.2, 1)), (16, BUB_SQUASH, "el"), (44, BUB_REST, "hold")])
    a.k(MB["face"], "opacity", [(0, 0, "hold"), (10, 0, "lin"), (22, 1, "hold")])
    motif_pose(a, MA, [(0, a_pose, "hold")])
    apply_enter(a, sc, offset=0, scale=0.6)

    # ---- Settled (reduced motion: final values + short opacity fade, no movement) ----
    a = anim(f"{n:02d} Settled (reduced motion)", 14, scene=n)
    sc.anim_rm = a
    hide_others(a, n)
    root_reset(a, sc)
    clip(a, sc, [(0, False)])
    a.k(sc.root, "opacity", [(0, 0, "lin"), (12, 1, "hold")])
    mouth_hit(a, sc)
    motif_pose(a, MA, [(0, a_pose, "hold")])
    motif_pose(a, MB, [(0, b_pose, "hold")])
    apply_final(a, sc)

    # ---- Out (forward handoff, generic): the next scene's speech form elongates over this one ----
    a = anim(f"{n:02d} Out", 28, scene=n)
    sc.anim_out = a
    elongate(a, COVER_INTO[min(n + 1, 10)], dur=28)
    a.k(sc.root, "scaleX", [(0, 1, "antic"), (28, 0.95, "hold")])
    a.k(sc.root, "scaleY", [(0, 1, "antic"), (28, 0.95, "hold")])
    a.k(sc.root, "x", [(0, 0, "in"), (28, -10, "hold")])
    a.k(sc.root, "y", [(0, 0, "antic"), (28, -30, "hold")])

    # ---- Out back (designed reverse): the scene closes into a quotation mark on a lilac plate ----
    a = anim(f"{n:02d} Out Back", 30, scene=n)
    sc.anim_outback = a
    plate(a, L)
    clip(a, sc, [(0, True)])
    aperture_close(a, 30)
    a.k(sc.root, "scaleX", [(0, 1, "in"), (30, 0.9, "hold")])
    a.k(sc.root, "scaleY", [(0, 1, "in"), (30, 0.9, "hold")])
    a.k(sc.root, "x", [(0, 0, "in"), (30, 20, "hold")])
    a.k(sc.root, "y", [(0, 0, "in"), (30, 43, "hold")])
    for M, pose, off in ((MA, a_pose, OFF_A), (MB, b_pose, OFF_B)):
        if pose[:2] != off[:2]:   # visible motif pieces get swallowed by the closing quote
            motif_keys(a, M, [(0, pose, "in"), (20, (195, 430, 0.05, 0.05, pose[4], 1), "hold")])

    # ---- reduced-motion out: a short fade ----
    a = anim(f"{n:02d} Out (reduced motion)", 10, scene=n)
    sc.anim_outrm = a
    plate(a, WP)
    a.k(sc.root, "opacity", [(0, 1, "lin"), (10, 0, "hold")])
    a.k(MA["root"], "opacity", [(0, 1, "lin"), (10, 0, "hold")])
    a.k(MB["root"], "opacity", [(0, 1, "lin"), (10, 0, "hold")])

    # ---- Idle loop ----
    a = anim(f"{n:02d} Idle", sc.idle_dur, "loop")
    sc.anim_idle = a
    for obj, prop_, keys, kind in sc.idle:
        if keys:
            a.k(obj, prop_, keys, kind)
    if a_pose != OFF_A and n != 9:
        a.k(MA["bob"], "y", [(0, 0, "sine"), (sc.idle_dur / 2, -8, "sine"), (sc.idle_dur, 0, "hold")])
    if b_pose != OFF_B and n != 9:
        a.k(MB["bob"], "y", [(0, -6, "sine"), (sc.idle_dur / 2, 2, "sine"), (sc.idle_dur, -6, "hold")])
    if a_pose != OFF_A and b_pose != OFF_B and n != 9:
        # the conversation: scene 2 opens with the persimmon form talking, scene 1 with the lilac one
        ta, tb = Talk(MA["rig"], sc.idle_dur, 0.2 + n), Talk(MB["rig"], sc.idle_dur, 1.7 + n)
        if n == 1:
            converse(tb, ta, 0, -1, 1)
        else:
            converse(ta, tb, 0, 1, -1)
        face_tracks(a, ta.build() + tb.build())

# ---- persona anticipation: the motif pair circles, winds up and collapses into the emblem ----
s9 = SCENES[9]
a = s9.anim_in
cy = STAGE_Y - 20
motif_pose(a, MA, [(0, OFF_A, "hold"), (10, OFF_A, "out"), (26, (112, cy, 0.62, 0.62, -0.2, 1), "sine"),
                   (40, (195, cy - 80, 0.58, 0.58, 0.3, 1), "sine"), (54, (278, cy, 0.62, 0.62, 0.5, 1), "antic"),
                   (68, (195, cy + 20, 0.02, 0.02, 1.4, 0), "hold"), (69, OFF_A, "hold")],
           [(0, BUB_REST, "hold"), (50, BUB_REST, "sine"), (58, BUB_SQUASH, "in"), (68, BUB_TALL, "hold")])
motif_pose(a, MB, [(0, OFF_B, "hold"), (14, (-60, cy, 0.6, 0.6, -0.4, 1), "out"), (28, (278, cy - 20, 0.58, 0.58, 0.2, 1), "sine"),
                   (42, (195, cy + 70, 0.56, 0.56, -0.3, 1), "sine"), (54, (112, cy, 0.6, 0.6, -0.5, 1), "antic"),
                   (68, (195, cy + 20, 0.02, 0.02, -1.4, 0), "hold"), (69, OFF_B, "hold")],
           [(0, BUB_REST, "hold"), (50, BUB_REST, "sine"), (58, BUB_SQUASH, "in"), (68, BUB_TALL, "hold")])
ta, tb = Talk(MA["rig"], 68, 0.9), Talk(MB["rig"], 68, 2.6)
ta.look(4, 5, -2)
ta.laugh(12, 4, 8)
ta.mouth(50, "o", OPEN_E)
tb.look(6, -5, -2)
tb.laugh(18, 3, 10)
tb.mouth(54, "u", OPEN_E)
for t_ in (ta, tb):
    t_.brows(50, -7, 0.1, dur=6)
face_tracks(a, ta.build() + tb.build())

# ---- special continuity transitions ----------------------------------------
# 1 -> 2: the two speech forms are carried down into the conversation scene, landing with a squash
s1, s2, s3, s4 = SCENES[1], SCENES[2], SCENES[3], SCENES[4]
a = anim("01 Out (carry motif to 2)", 40, motif_map=[(0, 1, "io"), (40, 2, "hold")])
s1.anim_out_special = a
plate(a, WP)
motif_pose(a, MA, [(0, s1.motifA, "antic"), (10, (s1.motifA[0] + 6, s1.motifA[1] - 30) + s1.motifA[2:], "io"), (40, s2.motifA, "hold")],
           [(0, BUB_REST, "sine"), (12, BUB_STRETCH, "sine"), (26, BUB_REST, "hold")])
motif_pose(a, MB, [(0, s1.motifB, "antic"), (14, (s1.motifB[0] - 6, s1.motifB[1] - 24) + s1.motifB[2:], "io"), (40, s2.motifB, "hold")],
           [(0, BUB_REST, "sine"), (16, BUB_STRETCH, "sine"), (30, BUB_REST, "hold")])
a.k(s1.root, "y", [(0, 0, "in"), (28, -60, "hold")])
a.k(s1.root, "opacity", [(0, 1, "in"), (28, 0, "hold")])
a = anim("02 Carry In (from 1)", 120, scene=2)
s2.anim_carry = a
hide_others(a, 2)
root_reset(a, s2)
mouth_hit(a, s2)
clip(a, s2, [(0, False)])
motif_pose(a, MA, [(0, s2.motifA, "hold")], [(0, BUB_SQUASH, "el"), (40, BUB_REST, "hold")])
motif_pose(a, MB, [(0, s2.motifB, "hold")], [(0, BUB_REST, "hold"), (6, BUB_SQUASH, "el"), (46, BUB_REST, "hold")])
a.k(MA["elastic"], "scaleY", [(0, 1, "lin"), (6, 0.88, "el"), (40, 1, "hold")])
a.k(MB["elastic"], "scaleY", [(0, 1, "lin"), (12, 0.88, "el"), (46, 1, "hold")])
apply_enter(a, s2)

# 2 -> 3: persimmon speech form flies centre-stage, its mouth becomes the elastic mouth
a = anim("02 Out (carry motif to 3)", 34, motif_map=[(0, 2, "io"), (34, 3, "hold")])
s2.anim_out_special = a
plate(a, L)
motif_pose(a, MA, [(0, s2.motifA, "antic"), (34, (195, 520, 2.7, 2.7, 0, 1), "hold")],
           [(0, BUB_REST, "antic"), (12, BUB_SQUASH, "out"), (34, BUB_REST, "hold")])
motif_keys(a, MB, [(0, s2.motifB, "in"), (24, (560, 700, 1.0, 1.0, 0.6, 1), "hold")])
a.k(MA["mouth"], "scaleY", [(0, 1, "io"), (34, 1.9, "hold")])
a.k(MA["mouth"], "scaleX", [(0, 1, "io"), (34, 1.25, "hold")])
a.k(MA["eyes"], "opacity", [(0, 1, "lin"), (26, 0, "hold")])
t = Talk(MA["rig"], 34)
t.key("jo", 0, 0, "sine")
t.key("jo", 6, -3, OPEN_E)      # a gulp, then the jaw drops wide open as it flies in
t.key("jo", 18, 34, "hold")
face_tracks(a, t.build(end_rest=False))
a.k(s2.root, "opacity", [(0, 1, "in"), (26, 0, "hold")])
a = anim("03 Carry In (from 2)", 120, scene=3)
s3.anim_carry = a
hide_others(a, 3)
root_reset(a, s3)
mouth_hit(a, s3)
clip(a, s3, [(0, False)])
motif_pose(a, MA, [(0, (195, 520, 2.7, 2.7, 0, 1), "in"), (18, (195, 548, 3.6, 3.2, 0, 0), "hold"), (19, OFF_A, "hold")])
a.k(MA["root"], "opacity", [(0, 1, "lin"), (12, 0, "hold"), (19, 1, "hold")])
a.k(MA["mouth"], "scaleY", [(0, 1.9, "hold"), (19, 1, "hold")])
a.k(MA["mouth"], "scaleX", [(0, 1.25, "hold"), (19, 1, "hold")])
a.k(MA["eyes"], "opacity", [(0, 0, "hold"), (19, 1, "hold")])
t = Talk(MA["rig"], 19)
t.key("jo", 0, 34, "hold")
face_tracks(a, t.build(start_rest=False))
motif_pose(a, MB, [(0, OFF_B, "hold")])
apply_enter(a, s3)
a.k(MOUTH["outer"], "scaleX", [(0, 0.7, "hold"), (8, 0.7, "el2"), (50, 1, "hold")])
a.k(MOUTH["outer"], "scaleY", [(0, 0.7, "hold"), (8, 0.7, "el2"), (50, 1, "hold")])
# 3 -> 4 SIGNATURE (hero version): the mouth purses, closes and becomes a speech bubble (true vertex morph of the
# lips into the motif silhouette), the bubble elongates until it fills the frame, then opens as a quotation mark
# onto scene 4, whose giant quotes land where the aperture was.
SIG = 1.6
a = anim("03 Out (signature: mouth -> bubble fills frame)", 44)
s3.anim_out_special = a
plate(a, P)
key_morph(a, MOUTH["lipverts"], [(0, LIPS, "antic"), (10, LIPS_PUCKER, (0.5, 0, 0.3, 1)),
                                 (24, bub(BUB_REST, SIG), (0.4, 0, 0.3, 1)), (44, bub(BUB_TALL, SIG), "hold")], LIPS)
a.k(MOUTH["inner"], "scaleX", [(0, 1, "in"), (12, 0.0, "hold")])
a.k(MOUTH["inner"], "scaleY", [(0, 1, "in"), (10, 0.0, "hold")])
a.k(MOUTH["outer"], "scaleX", [(0, 1, "antic"), (10, 0.92, "out"), (24, 1.0, "in"), (40, 1.9, "lin"), (44, 2.4, "hold")])
a.k(MOUTH["outer"], "scaleY", [(0, 1, "antic"), (10, 1.04, "out"), (24, 1.0, "in"), (40, 1.9, "lin"), (44, 2.4, "hold")])
a.k(MOUTH["outer"], "y", [(0, 548, "antic"), (24, 470, "in"), (44, 200, "hold")])
a.k(MOUTH["outer"], "rotation", [(0, 0, "out"), (24, -0.08, "in"), (44, 0.04, "hold")])
for key_ in ("unit", "head", "sup"):
    a.k(ids3[key_], "opacity", [(0, 1, "lin"), (12, 0, "hold")])
a.k(MIXM_DRV, "x", [(0, 0, "hold"), (24, 0, "in"), (44, 1, "hold")])
a = anim("04 Carry In (signature aperture)", 130)
s4.anim_carry = a
hide_others(a, 4)
root_reset(a, s4)
mouth_hit(a, s4)
clip(a, s4, [(0, True), (36, False)])
aperture_open(a, 0, rot0=-0.2)
motif_pose(a, MA, [(0, OFF_A, "hold")])
motif_pose(a, MB, [(0, OFF_B, "hold")])
apply_enter(a, s4, offset=6)
# restore scene 3 parts that the signature changed
for an in [s3.anim_in, s3.anim_backin, s3.anim_rm, s3.anim_carry]:
    key_morph(an, MOUTH["lipverts"], [(0, LIPS, "hold")], LIPS)
    key_morph(an, MOUTH["openverts"], [(0, opening, "hold")], opening)
    for obj_, prop_, v in ((MOUTH["teeth"], "y", -50), (MOUTH["TT"], "y", -36), (MOUTH["TT"], "rotation", 0),
                           (MOUTH["TT"], "scaleX", 1), (MOUTH["TB"], "x", 0), (MOUTH["breath"], "scaleX", 1),
                           (MOUTH["breath"], "scaleY", 1)):
        if prop_ not in an.tracks.get(obj_, {}):
            an.hold(obj_, prop_, v)
    for prop_, v in (("y", 548), ("rotation", 0)):
        an.hold(MOUTH["outer"], prop_, v)
    if an is not s3.anim_carry and an is not s3.anim_in and an is not s3.anim_backin:
        an.hold(MOUTH["outer"], "scaleX", 1)
        an.hold(MOUTH["outer"], "scaleY", 1)
    an.hold(MOUTH["inner"], "scaleX", 1)
    an.hold(MOUTH["inner"], "scaleY", 1)
    an.hold(MIXM_DRV, "x", 0)
    for key_ in ("unit", "head", "sup"):
        an.hold(ids3[key_], "opacity", 1)
# cover used when a carry transition's target scene is hidden
for n in (1, 2, 3):
    sc = SCENES[n]
    a = anim(f"{n:02d} Cover (skip)", 24)
    sc.anim_cover = a
    elongate(a, "A", dur=24)

# replay cover
REPLAY_COVER = anim("Replay cover", 32)
elongate(REPLAY_COVER, "A")
REPLAY_COVER.k(DRIVER, "x", [(0, 0, "hold")])
BOOT = anim("Boot", 1)
for an_ in (BOOT, REPLAY_COVER):
    an_.hold(MA["root"], "opacity", 1)
    an_.hold(MB["root"], "opacity", 1)
motif_pose(BOOT, MA, [(0, COVER_A, "hold")], [(0, BUB_TALL, "hold")])
motif_pose(BOOT, MB, [(0, OFF_B, "hold")])
plate(BOOT, P)
BOOT.hold(SCENES[1].root, "opacity", 1)
hide_others(BOOT, 1)

for an in [x for x in ANIMS if x.name.endswith("In") or "Settled" in x.name or "Back In" in x.name
           or ("Carry In" in x.name and "from 2" not in x.name)]:
    if "Settled" in an.name:
        an.k(MA["root"], "opacity", [(0, 0, "lin"), (12, 1, "hold")])
        an.k(MB["root"], "opacity", [(0, 0, "lin"), (12, 1, "hold")])
    else:
        an.hold(MA["root"], "opacity", 1)
        an.hold(MB["root"], "opacity", 1)
    for M in (MA, MB):
        an.hold(M["mouth"], "scaleX", 1)
        if "scaleY" not in an.tracks.get(M["mouth"], {}):
            an.hold(M["mouth"], "scaleY", 1)
        an.hold(M["eyes"], "opacity", 1)
        if "opacity" not in an.tracks.get(M["face"], {}):
            an.hold(M["face"], "opacity", 1)
        if an.name[:2] in ("01", "02", "09"):   # the scenes where the speech forms are on stage
            face_rest(an, M["rig"])


# mouth expressions (signature interaction, silent)
SQ3 = anim("Mouth tap: scene 3 elastic", 60)
SQ3.k(MOUTH["elastic"], "scaleX", [(0, 1, "out"), (6, 1.22, "el"), (60, 1, "hold")])
SQ3.k(MOUTH["elastic"], "scaleY", [(0, 1, "out"), (6, 0.72, "el"), (60, 1, "hold")])
SQ3.k(MOUTH["tongue"], "scaleX", [(0, 1, "out"), (8, 1.25, "el"), (60, 1, "hold")])
SQ3.k(MOUTH["tongue"], "rotation", [(0, 0, "out"), (6, 0.22, "el"), (60, 0, "hold")])
SQ2 = anim("Mouth tap: scene 2 laugh", 50)
SQ2.k(MA["elastic"], "scaleY", [(0, 1, "out"), (5, 0.78, "el"), (50, 1, "hold")])
SQ2.k(MA["elastic"], "scaleX", [(0, 1, "out"), (5, 1.16, "el"), (50, 1, "hold")])
SQ2.k(MA["mouth"], "scaleX", [(0, 1, "out"), (5, 1.3, "el"), (50, 1, "hold")])

# Persona animations (reveal starts as the motif pair collapses at frame 64 of the scene-9 entrance)
PERS = []
for k, e in enumerate(EMB):
    rev = anim(f"Persona {k} reveal", 150)
    stat = anim(f"Persona {k} static", 1)
    idle = anim(f"Persona {k} idle", e["dur"], "loop")
    for m, e2 in enumerate(EMB):
        rev.hold(e2["root"], "opacity", 1 if m == k else 0)
        stat.hold(e2["root"], "opacity", 1 if m == k else 0)
    rev.k(e["root"], "opacity", [(0, 0, "hold"), (64, 1, "hold")])
    for obj, prop_, keys in e["rev"]:
        rev.k(obj, prop_, [(f + 64, v, ez) for f, v, ez in keys])
        stat.hold(obj, prop_, keys[-1][1])
    for obj, prop_, keys in e["idle"]:
        idle.k(obj, prop_, keys)
    dark = (k == 1)
    ink = WP if dark else D
    for an in (rev, stat):
        for cidk in ("label_c", "title_c", "desc_c"):
            an.k(p9[cidk], "colorValue", [(0, ink, "hold")], kind="c")
        for ci, col in zip(STG["ring_c"], e["rings"]):
            an.k(ci, "colorValue", [(0, col, "hold")], kind="c")
        an.k(STG["ground_c"], "colorValue", [(0, e["ground"], "hold")], kind="c")
    PERS.append((rev, stat, idle))

# Theme animations (chrome colours per background)
THEMES = {}
for tname, ink, btn_bg, btn_ink, track, fillc in [("light", D, D, WP, "333D2456", P), ("dark", WP, L, D, "55C7B7F2", P),
                                                   ("warm", DD, DD, WP, "402A1640", WP)]:
    a = anim(f"Theme {tname}", 1)
    a.hold(GRAIN_N, "opacity", 0.45 if tname == "dark" else 0.55)
    a.k(CH["wm_c"], "colorValue", [(0, ink, "hold")], kind="c")
    a.k(CH["year_c"], "colorValue", [(0, ink, "hold")], kind="c")
    for k in range(1, 11):
        a.k(SEG[k]["track_c"], "colorValue", [(0, track, "hold")], kind="c")
        a.k(SEG[k]["fill_c"], "colorValue", [(0, fillc, "hold")], kind="c")
    for b in BTN.values():
        a.k(b["bg_c"], "colorValue", [(0, btn_bg, "hold")], kind="c")
        for kk in ("ink_c", "ink2_c", "ink3_c"):
            if kk in b:
                a.k(b[kk], "colorValue", [(0, btn_ink, "hold")], kind="c")
    THEMES[tname] = a
SCENE_THEME = {1: "light", 2: "light", 3: "light", 4: "dark", 5: "light", 6: "light", 7: "warm", 8: "dark", 10: "dark"}

# Chrome layout per mode
# (positions are bound to the layout: CTRL_X picks story or summary placement from currentScreen; these timelines
# only decide which controls can take focus)
CH_NORMAL = anim("Controls: story", 1)
CH_SUMMARY = anim("Controls: summary", 1)
for key_ in BTN:
    CH_SUMMARY.hold(BTN[key_]["focus"], "canFocus", key_ not in ("Pause", "Continue"), kind="b")
    CH_NORMAL.hold(BTN[key_]["focus"], "canFocus", key_ not in ("Replay", "Share"), kind="b")
PAUSE_ICON = anim("Pause icon: playing", 8)
PAUSE_ICON.k(BTN["Pause"]["bars"], "opacity", [(0, 0, "lin"), (8, 1, "hold")])
PAUSE_ICON.k(BTN["Pause"]["tri"], "opacity", [(0, 1, "lin"), (8, 0, "hold")])
PLAY_ICON = anim("Pause icon: paused", 8)
PLAY_ICON.k(BTN["Pause"]["bars"], "opacity", [(0, 1, "lin"), (8, 0, "hold")])
PLAY_ICON.k(BTN["Pause"]["tri"], "opacity", [(0, 0, "lin"), (8, 1, "hold")])

# Visibility (progress segments)
VIS = {}
for k in range(2, 10):
    sh = anim(f"Segment {k} shown", 1)
    hd = anim(f"Segment {k} hidden", 1)
    sh.k(SEG[k]["style"], "displayValue", [(0, 0, "hold")], kind="u")
    hd.k(SEG[k]["style"], "displayValue", [(0, 1, "hold")], kind="u")
    VIS[k] = (sh, hd)

# summary headline mode
SUM_FULL = anim("Summary copy: full", 1)
SUM_EMPTY = anim("Summary copy: new user", 1)
for an, full in ((SUM_FULL, True), (SUM_EMPTY, False)):
    an.hold(sum_h["col"], "opacity", 1 if full else 0)
    an.hold(sum_h["ecol"], "opacity", 0 if full else 1)

# Press (hold-to-pause) timeline
PRESS = anim("Press timer (hold threshold 350ms)", 21)

# ================================================================ STATE MACHINE
L_ = {}
layers = []


def layer(name, entry_to, states, any_trans=None, x0=0):
    lid = nid()
    any_ = E("AnyState", {"x": x0 - 200, "y": -200}, any_trans or [])
    ex = E("ExitState", {"x": x0 - 200, "y": -320})
    en = E("EntryState", {"x": x0 - 200, "y": 0}, [trans(entry_to)])
    layers.append(E("StateMachineLayer", {"name": name, "id": lid}, [any_, ex, en] + states))


TRUE, FALSE = True, False
cs = V("currentScreen")
RM = V("reducedMotion")


def show(k):
    return V(f"showScreen{k}")


# ---------------- Sequence layer
S = {}
for n in range(1, 11):
    for kind in ("G", "B", "In", "BackIn", "RMIn", "H", "Out", "OutBack", "OutRM", "OutBackRM", "GC", "Carry", "Cover", "Fin", "Settle"):
        S[(kind, n)] = nid()
S_BOOT = nid()
S_REPLAY = nid()
seq_states = []
col = lambda n: n * 300
row = {"G": -300, "B": 900, "In": -150, "BackIn": 750, "RMIn": 600, "H": 150, "Out": 0, "OutBack": 450,
       "OutRM": 300, "OutBackRM": 1050, "GC": -450, "Carry": -600, "Cover": -750, "Fin": 1200, "Settle": 1350}
NEXT = cond(V("goNext"), "t")
PREV = cond(V("goPrevious"), "t")
RMT = cond(RM, "b", True)
RMF = cond(RM, "b", False)


def entry_actions(n):
    return [write(cs, "n", n), fire_trigger(V("_dwellStop")), fire_event(EV["screenChanged"])]


def nav_out(n, mix=None, entering=False):
    """transitions taken from an active scene state on next/previous. While a scene is still entering, a tap
    skips straight to the neighbouring gate (the next entrance blends in over 150 ms), so rapid taps step one
    scene per tap and settle on the last requested scene."""
    t = []
    if entering:
        if n < 10:
            t.append(trans(S[("G", n + 1)], [NEXT, RMF]))
            t.append(trans(S[("OutRM", n)], [NEXT, RMT]))
        if n > 1:
            t.append(trans(S[("B", n - 1)], [PREV, RMF]))
            t.append(trans(S[("OutBackRM", n)], [PREV, RMT]))
        return t
    if n < 10:
        out_target = S[("Out", n)]
        t.append(trans(out_target, [NEXT, RMF], dur=mix))
        t.append(trans(S[("OutRM", n)], [NEXT, RMT]))
    if n > 1:
        t.append(trans(S[("OutBack", n)], [PREV, RMF], dur=mix))
        t.append(trans(S[("OutBackRM", n)], [PREV, RMT]))
    return t


for n in range(1, 11):
    sc = SCENES[n]
    always = n in (1, 10)
    nxt = S[("G", n + 1)] if n < 10 else None
    prv = S[("B", n - 1)] if n > 1 else None
    # forward gate
    g = []
    if always:
        g += [trans(S[("In", n)], [RMF]), trans(S[("RMIn", n)], [RMT])]
    else:
        g += [trans(S[("In", n)], [cond(show(n), "b", True), RMF]), trans(S[("RMIn", n)], [cond(show(n), "b", True), RMT]),
              trans(nxt, [cond(show(n), "b", False)])]
    seq_states.append(astate(S[("G", n)], EMPTY.id, col(n), row["G"], g, caption=f"Gate {n} (forward)"))
    # back gate
    g = []
    if always:
        g += [trans(S[("BackIn", n)], [RMF]), trans(S[("RMIn", n)], [RMT])]
    else:
        g += [trans(S[("BackIn", n)], [cond(show(n), "b", True), RMF]), trans(S[("RMIn", n)], [cond(show(n), "b", True), RMT]),
              trans(prv, [cond(show(n), "b", False)])]
    seq_states.append(astate(S[("B", n)], EMPTY.id, col(n), row["B"], g, caption=f"Gate {n} (back)"))
    # entering states
    settle_to = S[("Settle", n)] if n == 10 else S[("H", n)]
    for kind, an in (("In", sc.anim_in), ("BackIn", sc.anim_backin), ("RMIn", sc.anim_rm)):
        seq_states.append(astate(S[(kind, n)], an.id, col(n), row[kind],
                                 entry_actions(n) + ([write(V("screenProgress"), "n", 1)] if n == 10 else [])
                                 + [trans(settle_to, exit_pct=100)] + nav_out(n, entering=True), reset=True,
                                 caption=f"{kind} {n}"))
    if n in (2, 3, 4):
        seq_states.append(astate(S[("Carry", n)], sc.anim_carry.id, col(n), row["Carry"],
                                 entry_actions(n) + [trans(settle_to, exit_pct=100)] + nav_out(n, entering=True), reset=True,
                                 caption=f"Carry-in {n}"))
    # hold / dwell
    h_actions = [fire_trigger(V("_dwellStart"))] if n < 10 else []
    seq_states.append(astate(S[("H", n)], EMPTY.id, col(n), row["H"], h_actions + nav_out(n), caption=f"Dwell {n}"))
    if n == 10:
        seq_states.append(astate(S[("Settle", n)], EMPTY.id, col(n), row["Settle"], [
            trans(S[("Fin", n)], [cond(V("_finishedLatch"), "b", False)]),
            trans(S[("H", n)], [cond(V("_finishedLatch"), "b", True)])], caption="Summary settled?"))
        seq_states.append(astate(S[("Fin", n)], EMPTY.id, col(n), row["Fin"], [
            fire_event(EV["recapFinished"]), write(V("_finishedLatch"), "b", True), trans(S[("H", n)])],
            caption="recapFinished (once)"))
    # exits
    if n < 10:
        special = n in (1, 2, 3)
        out_anim = sc.anim_out_special if special else sc.anim_out
        to = S[("GC", n + 1)] if special else nxt
        seq_states.append(astate(S[("Out", n)], out_anim.id, col(n), row["Out"], [
            fire_trigger(V("_dwellStop")), trans(to, exit_pct=100), trans(S[("G", min(n + 2, 10))], [NEXT]),
            trans(S[("B", n)], [PREV])], reset=True, caption=f"Out {n}" + (" (carry)" if special else "")))
        seq_states.append(astate(S[("OutRM", n)], sc.anim_outrm.id, col(n), row["OutRM"], [
            fire_trigger(V("_dwellStop")), trans(nxt, exit_pct=100)], reset=True, caption=f"Out {n} (reduced)"))
        if special:
            seq_states.append(astate(S[("GC", n + 1)], EMPTY.id, col(n + 1), row["GC"], [
                trans(S[("Carry", n + 1)], [cond(show(n + 1), "b", True), RMF]),
                trans(S[("RMIn", n + 1)], [cond(show(n + 1), "b", True), RMT]),
                trans(S[("Cover", n)], [cond(show(n + 1), "b", False)])], caption=f"Carry gate {n + 1}"))
            seq_states.append(astate(S[("Cover", n)], sc.anim_cover.id, col(n), row["Cover"], [
                trans(S[("G", n + 2)], exit_pct=100)], reset=True, caption=f"Cover after {n} (skip)"))
    if n > 1:
        seq_states.append(astate(S[("OutBack", n)], sc.anim_outback.id, col(n), row["OutBack"], [
            fire_trigger(V("_dwellStop")), trans(prv, exit_pct=100), trans(S[("B", max(n - 2, 1))], [PREV]),
            trans(S[("G", n)], [NEXT])],
            reset=True, caption=f"Out back {n}"))
        seq_states.append(astate(S[("OutBackRM", n)], sc.anim_outrm.id, col(n), row["OutBackRM"], [
            fire_trigger(V("_dwellStop")), trans(prv, exit_pct=100)], reset=True, caption=f"Out back {n} (reduced)"))

# remove S entries for unused keys
seq_states.append(astate(S_BOOT, BOOT.id, 0, 0, [E("FocusActionTarget", {"targetId": BTN["Continue"]["id"]}),
                                                write(V("_finishedLatch"), "b", False), trans(S[("G", 1)])], caption="Boot"))
seq_states.append(astate(S_REPLAY, REPLAY_COVER.id, 0, 300, [
    write(V("_finishedLatch"), "b", False), fire_trigger(V("_dwellStop")), trans(S[("G", 1)], exit_pct=100)],
    reset=True, caption="Replay (cover, reset latch)"))
layer("Sequence", S_BOOT, seq_states, any_trans=[trans(S_REPLAY, [cond(V("requestReplay"), "t")])])

# ---------------- Idle layer (decorative loops; frozen while paused or in reduced motion)
idle_states, idle_any = [], []
FROZEN = nid()
idle_states.append(astate(FROZEN, EMPTY.id, 0, 200, caption="Frozen"))
idle_any += [trans(FROZEN, [cond(V("isPaused"), "b", True)]), trans(FROZEN, [RMT])]
for n in range(1, 11):
    sid_ = nid()
    idle_states.append(astate(sid_, SCENES[n].anim_idle.id, n * 200, 0, caption=f"Idle {n}"))
    idle_any.append(trans(sid_, [cond(cs, "n", n), cond(V("isPaused"), "b", False), RMF]))
layer("Idle loops", FROZEN, idle_states, idle_any)

# ---------------- Persona layer (derives name/description/colour atomically + emblem choreography)
pers_states, pers_any = [], []
P_SYNC0 = None


def idx_ranges(k):
    if k == 0:
        return [[cond(V("personaIndex"), "n", 0.5, "lessThan")], [cond(V("personaIndex"), "n", 3.5, "greaterThanOrEqual")]]
    return [[cond(V("personaIndex"), "n", k - 0.5, "greaterThanOrEqual"), cond(V("personaIndex"), "n", k + 0.5, "lessThan")]]


for k, (rev, stat, idle) in enumerate(PERS):
    sync_id, rev_id = nid(), nid()
    if k == 0:
        P_SYNC0 = sync_id
    color = argb(PERSONAS[k][2])
    acts = lambda: [copy_str(V(f"personaName{k}"), V("personaName")),
                    copy_str(V(f"personaDescription{k}"), V("personaDescription")), write(V("personaColor"), "c", color)]
    pers_states.append(astate(sync_id, stat.id, k * 250, 0, acts(), caption=f"Persona {k} (settled)"))
    pers_states.append(astate(rev_id, rev.id, k * 250, 200, acts(), reset=True, caption=f"Persona {k} reveal"))
    for rg in idx_ranges(k):
        pers_any.append(trans(sync_id, rg + [cond(cs, "n", 9, "notEqual")]))
        pers_any.append(trans(sync_id, rg + [RMT]))
        pers_any.append(trans(rev_id, rg + [cond(cs, "n", 9), RMF]))
layer("Persona", P_SYNC0, pers_states, pers_any)

# persona idle layer
pi_states, pi_any = [], []
PI_FROZEN = nid()
pi_states.append(astate(PI_FROZEN, EMPTY.id, 0, 200, caption="Persona idle frozen"))
pi_any += [trans(PI_FROZEN, [cond(V("isPaused"), "b", True)]), trans(PI_FROZEN, [RMT]),
           trans(PI_FROZEN, [cond(cs, "n", 9, "notEqual")])]
for k, (rev, stat, idle) in enumerate(PERS):
    sid_ = nid()
    pi_states.append(astate(sid_, idle.id, k * 250, 0, caption=f"Persona {k} idle"))
    for rg in idx_ranges(k):
        pi_any.append(trans(sid_, rg + [cond(cs, "n", 9), cond(V("isPaused"), "b", False), RMF]))
layer("Persona idle", PI_FROZEN, pi_states, pi_any)

# ---------------- Theme layer
th_states, th_any = [], []
TH = {}
for i, (tname, an) in enumerate(THEMES.items()):
    TH[tname] = nid()
    th_states.append(astate(TH[tname], an.id, i * 250, 0, caption=f"Theme {tname}"))
for n, tname in SCENE_THEME.items():
    th_any.append(trans(TH[tname], [cond(cs, "n", n)], dur=300))
for rg in idx_ranges(1):
    th_any.append(trans(TH["dark"], rg + [cond(cs, "n", 9)], dur=300))
for k in (0, 2, 3):
    for rg in idx_ranges(k):
        th_any.append(trans(TH["light"], rg + [cond(cs, "n", 9)], dur=300))
layer("Chrome theme", TH["light"], th_states, th_any)

# ---------------- Controls mode + pause icon
cm_n, cm_s = nid(), nid()
layer("Controls mode", cm_n, [
    astate(cm_n, CH_NORMAL.id, 0, 0, [trans(cm_s, [cond(cs, "n", 10)])], caption="Story controls"),
    astate(cm_s, CH_SUMMARY.id, 250, 0, [trans(cm_n, [cond(cs, "n", 10, "notEqual")])], caption="Summary controls")])
pi_play, pi_pause = nid(), nid()
layer("Pause icon", pi_play, [
    astate(pi_play, PAUSE_ICON.id, 0, 0, [trans(pi_pause, [cond(V("isPaused"), "b", True)])], caption="Playing"),
    astate(pi_pause, PLAY_ICON.id, 250, 0, [trans(pi_play, [cond(V("isPaused"), "b", False)])], caption="Paused")])

# ---------------- Visibility layers
for k in range(2, 10):
    sh_id, hd_id = nid(), nid()
    sh, hd = VIS[k]
    layer(f"Segment {k} visibility", sh_id, [
        astate(sh_id, sh.id, 0, 0, [trans(hd_id, [cond(show(k), "b", False)])], caption="Shown"),
        astate(hd_id, hd.id, 250, 0, [trans(sh_id, [cond(show(k), "b", True)])], caption="Hidden")])

# ---------------- Summary copy mode (new user = every metric scene hidden)
sf, se = nid(), nid()
all_hidden = [cond(show(k), "b", False) for k in range(2, 9)]
layer("Summary copy", sf, [
    astate(sf, SUM_FULL.id, 0, 0, [trans(se, all_hidden)], caption="Full"),
    astate(se, SUM_EMPTY.id, 250, 0, [trans(sf, [cond(show(k), "b", True)]) for k in range(2, 9)], caption="New user")])

# ---------------- Press layer: tap vs hold
pr_idle, pr_press, pr_next, pr_prev, pr_holdA, pr_holdB = (nid() for _ in range(6))
down_ = cond(V("_pointerDown"), "b", True)
up_ = cond(V("_pointerDown"), "b", False)
layer("Press (tap vs hold)", pr_idle, [
    astate(pr_idle, EMPTY.id, 0, 0, [trans(pr_press, [down_])], caption="Idle"),
    astate(pr_press, PRESS.id, 250, 0, [
        trans(pr_next, [up_, cond(V("_pressSide"), "n", 0, "greaterThan")]),
        trans(pr_prev, [up_, cond(V("_pressSide"), "n", 0, "lessThan")]),
        trans(pr_idle, [up_, cond(V("_pressSide"), "n", 0)]),
        trans(pr_holdA, [cond(V("isPaused"), "b", False)], exit_pct=100),
        trans(pr_holdB, [cond(V("isPaused"), "b", True)], exit_pct=100)], reset=True, caption="Pressing"),
    astate(pr_next, EMPTY.id, 500, -150, [fire_trigger(V("goNext")), trans(pr_idle)], caption="Tap: next"),
    astate(pr_prev, EMPTY.id, 500, 150, [fire_trigger(V("goPrevious")), trans(pr_idle)], caption="Tap: previous"),
    astate(pr_holdA, EMPTY.id, 750, -100, [write(V("isPaused"), "b", True),
                                           E("ListenerViewModelChange", None, [])][:1] + [trans((pr_rel := nid()), [up_])],
           caption="Held (paused by hold)"),
    astate(pr_rel, EMPTY.id, 1000, -100, [write(V("isPaused"), "b", False), trans(pr_idle)], caption="Released: resume"),
    astate(pr_holdB, EMPTY.id, 750, 100, [trans(pr_idle, [up_])], caption="Held (already paused)")])

# ---------------- Mouth (signature interaction)
mo_rest, mo2, mo3 = nid(), nid(), nid()
tap = cond(V("_mouthTap"), "t")
layer("Mouth tap", mo_rest, [
    astate(mo_rest, EMPTY.id, 0, 0, [trans(mo3, [tap, cond(cs, "n", 3)]), trans(mo2, [tap, cond(cs, "n", 2)])], caption="Rest"),
    astate(mo3, SQ3.id, 250, -100, [fire_event(EV["mouthTapped"]), trans(mo_rest, exit_pct=100), trans(mo3, [tap])],
           reset=True, caption="Elastic mouth"),
    astate(mo2, SQ2.id, 250, 100, [fire_event(EV["mouthTapped"]), trans(mo_rest, exit_pct=100)], reset=True,
           caption="Laughing bubble")])

# ---------------- Listeners
listeners = []


def lis(target, typ, actions, name):
    listeners.append(E("StateMachineListenerSingle", {"targetId": target, "listenerTypeValue": typ, "name": name}, actions))


def keylis(target, key, actions, name, mods=None):
    listeners.append(E("StateMachineListener", {"targetId": target, "name": name}, [
        E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
          [E("KeyboardInput", {"keyType": key, "keyPhase": 1, "modifiers": mods})])] + actions))


for tgt, side, nm in ((NAV_R, 1, "next"), (NAV_L, -1, "back")):
    lis(tgt, "down", [write(V("_pointerDown"), "b", True), write(V("_pressSide"), "n", side),
                      write(V("_focusVisible"), "n", 0)], f"Press {nm} region")
    lis(tgt, "up", [write(V("_pointerDown"), "b", False)], f"Release {nm} region")
    lis(tgt, "exit", [write(V("_pointerDown"), "b", False)], f"Leave {nm} region")
FV0 = lambda: write(V("_focusVisible"), "n", 0)
lis(BTN["Previous"]["id"], "click", [fire_trigger(V("goPrevious")), FV0()], "Previous button")
lis(BTN["Pause"]["id"], "click", [toggle(V("isPaused"), C_NOT), FV0()], "Pause button")
lis(BTN["Continue"]["id"], "click", [fire_trigger(V("goNext")), FV0()], "Continue button")
lis(BTN["Replay"]["id"], "click", [fire_trigger(V("requestReplay")), FV0()], "Replay button")
lis(BTN["Share"]["id"], "click", [E("ListenerFireEvent", {"eventId": EV["shareTapped"]}), FV0()], "Share button")
lis(MOUTH_HIT, "down", [write(V("_pressSide"), "n", 0)], "Mouth press (cancels story tap)")
lis(MOUTH_HIT, "click", [write(V("_pressSide"), "n", 0), fire_trigger(V("_mouthTap"))], "Tap the mouth")
for key_, b in BTN.items():
    lis(b["id"], "focus", [write(V("_focusIndex"), "n", b["idx"])], f"{key_} focused")
    lis(b["id"], "blur", [write(V("_focusIndex"), "n", 0)], f"{key_} blurred")
keylis(KEYHOST, "right", [fire_trigger(V("goNext"))], "Key: Right")
keylis(KEYHOST, "left", [fire_trigger(V("goPrevious"))], "Key: Left")
keylis(KEYHOST, "space", [toggle(V("isPaused"), C_NOT)], "Key: Space")
listeners.append(E("StateMachineListener", {"targetId": KEYHOST, "name": "Key: Tab"}, [
    E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"}, [E("KeyboardInput", {"keyType": "tab", "keyPhase": 1})]),
    E("FocusActionTraversal", {"traversalKind": "next"}), write(V("_focusVisible"), "n", 1)]))
listeners.append(E("StateMachineListener", {"targetId": KEYHOST, "name": "Key: Shift+Tab"}, [
    E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
      [E("KeyboardInput", {"keyType": "tab", "keyPhase": 1, "modifiers": 1})]),
    E("FocusActionTraversal", {"traversalKind": "previous"}), write(V("_focusVisible"), "n", 1)]))
enter_actions = {"Previous": [fire_trigger(V("goPrevious"))], "Pause": [toggle(V("isPaused"), C_NOT)],
                 "Continue": [fire_trigger(V("goNext"))], "Replay": [fire_trigger(V("requestReplay"))],
                 "Share": [E("ListenerFireEvent", {"eventId": EV["shareTapped"]})]}
for key_, acts in enter_actions.items():
    listeners.append(E("StateMachineListener", {"targetId": BTN[key_]["id"], "name": f"Enter on {key_}"}, [
        E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
          [E("KeyboardInput", {"keyType": "enter", "keyPhase": 1}), E("KeyboardInput", {"keyType": "kpEnter", "keyPhase": 1})])] + acts))

MAIN_SM = nid()
sm_xml = E("StateMachine", {"name": "Recap", "id": MAIN_SM}, listeners + layers)

# ================================================================ MAIN ARTBOARD
MAIN = nid()
MAIN_STYLE = nid()
main_children = [E("LayoutComponentStyle", {"name": "Artboard style", "id": MAIN_STYLE})]
STAGE, STAGE_STYLE = nid(), nid()
VIEWPORT, VIEWPORT_STYLE = nid(), nid()
# The viewport box fills the artboard (which the host's layout fit sizes to the canvas): its computed size is the
# input of the whole responsive layout, and it carries the progress row, which stretches between the margins.
main_children.append(E("LayoutComponent", {"width": W, "height": H, "clip": False, "styleId": VIEWPORT_STYLE,
                                           "name": "Viewport", "id": VIEWPORT}, [
    E("LayoutComponentStyle", {"layoutWidthScaleType": "fill", "layoutHeightScaleType": "fill",
                               "name": "Viewport style", "id": VIEWPORT_STYLE}),
    bind(V("_vw"), 810, None, direction=True),
    bind(V("_vh"), 811, None, direction=True)] + viewport_kids))
# Everything else lives in a 390x844 stage box at the origin: the absolutely positioned copy columns resolve against
# this design frame, and the frame nodes above them map design coordinates onto the real canvas.
main_children.append(E("LayoutComponent", {"width": W, "height": H, "clip": False, "styleId": STAGE_STYLE,
                                           "name": "Stage", "id": STAGE}, [
    E("LayoutComponentStyle", {"positionTypeValue": "absolute", "positionLeft": 0, "positionTop": 0,
                               "positionLeftUnitsValue": "points", "positionTopUnitsValue": "points",
                               "name": "Stage style", "id": STAGE_STYLE}),
    node("Stage content", chrome + [grain_xml, mouth_hit_xml, clock_xml, driver_xml, solver_xml, aperture, mA, mB]
         + scene_xml + [plate_xml])]))
main_children += [fill(WP)] + events + [sm_xml] + [a.xml() for a in ANIMS]
main_xml = E("Artboard", {"defaultStateMachineId": MAIN_SM, "viewModelId": VM, "viewModelInstanceId": "0:95",
                          "styleId": MAIN_STYLE, "width": W, "height": H, "clip": True, "x": 0, "y": 0,
                          "name": "Parlance Recap", "id": MAIN}, main_children)

# ================================================================ CLOCK COMPONENT
rml_ids_clock = {}
CK_DRV = nid()
ck = {k: nid() for k in ("off", "reset", "run", "done", "lid", "style")}
ck_off_a, ck_run_a = Anim("Clock zero", 1), Anim("Clock run (1s; speed = 1/autoAdvanceSeconds)", 60)
ck_off_a.hold(CK_DRV, "x", 0)
ck_run_a.k(CK_DRV, "x", [(0, 0, "lin"), (60, 1, "hold")])
clock_ab = E("Artboard", {"isComponent": True, "defaultStateMachineId": CLOCK_SM, "viewModelId": VM, "styleId": ck["style"],
                          "width": 8, "height": 8, "x": 460, "y": 0, "name": "Dwell Clock", "id": CLOCK_AB}, [
    E("LayoutComponentStyle", {"name": "Clock style", "id": ck["style"]}),
    node("Progress driver", [], id=CK_DRV, binds=[bind(V("screenProgress"), 13, None, twoWay=True)]),
    E("StateMachine", {"name": "Clock", "id": CLOCK_SM}, [E("StateMachineLayer", {"name": "Dwell", "id": ck["lid"]}, [
        E("AnyState", {"x": -200, "y": -200}, [trans(ck["reset"], [cond(V("_dwellStart"), "t")]),
                                               trans(ck["off"], [cond(V("_dwellStop"), "t")])]),
        E("ExitState", {"x": -200, "y": -320}),
        E("EntryState", {"x": -200, "y": 0}, [trans(ck["off"])]),
        astate(ck["off"], ck_off_a.id, 0, 0, caption="Off"),
        astate(ck["reset"], ck_off_a.id, 250, 0, [trans(ck["run"], [cond(V("autoAdvanceEnabled"), "b", True)])],
               caption="Armed (waits for autoAdvanceEnabled)"),
        astate(ck["run"], ck_run_a.id, 500, 0, [trans(ck["done"], exit_pct=100),
                                                trans(ck["reset"], [cond(V("autoAdvanceEnabled"), "b", False)])],
               reset=True, caption="Counting dwell"),
        astate(ck["done"], ck_off_a.id, 750, 0, [fire_trigger(V("goNext"))], caption="Done: request next")])]),
    ck_off_a.xml(), ck_run_a.xml()])

# ================================================================ SHARE CARD COMPONENTS
# Two artboards from one builder: the tall card (342x556) used by the stacked portrait arrangement, and a wide card
# (766x300: persona on the left, the five tiles in a 3x2 grid on the right) used whenever copy and art sit side by
# side. Each is a self-contained component a host can render alone for the share snapshot.
CARD_SPECS = {
    "tall": dict(W=342, H=556, name="Share Card", tag="Card", wm=(24, 22), year=(318, 24), name_box=(24, 58, 294),
                 emb=(171, 140), title=(24, 232, 294), desc=(24, 264, 294), neutral=(171, 160),
                 empty_h=(24, 300, 294), empty_s=(24, 370, 294),
                 tiles=[(24 + (i % 2) * 151, 316 + (i // 2) * 76) for i in range(5)], mtile=(175, 468),
                 blob=(250, 150)),
    "wide": dict(W=766, H=300, name="Share Card Wide", tag="Wide card", wm=(24, 22), year=(742, 24),
                 name_box=(24, 58, 260), emb=(150, 140), title=(10, 232, 280), desc=(10, 264, 280), neutral=(150, 160),
                 empty_h=(300, 104, 440), empty_s=(300, 174, 440),
                 tiles=[(296 + (i % 3) * 151, 76 + (i // 3) * 80) for i in range(5)], mtile=(598, 156),
                 blob=(640, 80)),
}


def build_card(variant, ab_id, sm_id):
    cs_ = CARD_SPECS[variant]
    CW, CH_ = cs_["W"], cs_["H"]
    tg = cs_["tag"]
    cd = {"style": nid()}
    card_parts = []
    # top row
    sid, st = disp(23, D, 750, wdth=92, ls=-0.3)
    wm_id = nid()
    card_parts.append(node(f"{tg} wordmark", [
        text(f"{tg} wordmark text", 0, 0, [st], [run(sid, "Parlance")])], id=wm_id, x=cs_["wm"][0], y=cs_["wm"][1]))
    sid, st = disp(24, P, 800)
    year_id = nid()
    card_parts.append(text(f"{tg} year", cs_["year"][0], cs_["year"][1], [st], [run(sid, "2026", [bind(V("year"), 268, C_STR0)])],
                           ox=1, id=year_id))
    nx, ny, nw = cs_["name_box"]
    name_id, _c, t_ = bound_text(f"{tg} name", nx, ny, nw, "userName", font="body", size=14, color=DL, wght=600,
                                 sizing="fixed", h=20, overflow="ellipsis", wrap="noWrap")
    card_parts.append(t_)
    # persona block
    CEMB = build_emblems(0.42, "CE" if variant == "tall" else "WE")
    emb_id = nid()
    cstage_xml, CSTG = emblem_stage(CEMB, 0.42, tg)
    card_parts.append(node(f"{tg} persona emblem", [cstage_xml], id=emb_id, x=cs_["emb"][0], y=cs_["emb"][1]))
    tx_, ty_, tw_ = cs_["title"]
    pt_id, _c, t_ = bound_text(f"{tg} persona title", tx_, ty_, tw_, "personaName", size=27, color=D, wght=800, lh=28,
                               align="center", wdth=94, ls=-0.6)
    card_parts.append(t_)
    dx_, dy_, dw_ = cs_["desc"]
    pd_id, _c, t_ = bound_text(f"{tg} persona description", dx_, dy_, dw_, "personaDescription", font="body", size=13,
                               color=DL, wght=500, lh=17, align="center")
    card_parts.append(t_)
    # neutral motif (shown when persona hidden / new user)
    neutral_id = nid()
    na, nb = {}, {}
    card_parts.append(node(f"{tg} neutral motif", [
        node(f"{tg} neutral A", [motif_bubble(f"{tg} motif A", P, PD, False, 0.5, ids=na)], x=-36),
        node(f"{tg} neutral B", [motif_bubble(f"{tg} motif B", L, LD, True, 0.45, ids=nb)], x=44, y=10)],
        id=neutral_id, x=cs_["neutral"][0], y=cs_["neutral"][1], op=0))
    ex_, ey_, ew_ = cs_["empty_h"]
    empty_h, _c, t_ = bound_text(f"{tg} empty headline", ex_, ey_, ew_, "emptyHeadline", size=26, color=D, wght=800,
                                 lh=28, align="center", op=0)
    card_parts.append(t_)
    ex_, ey_, ew_ = cs_["empty_s"]
    empty_s, _c, t_ = bound_text(f"{tg} empty support", ex_, ey_, ew_, "emptySupport", font="body", size=15, color=DL,
                                 wght=500, lh=20, align="center", op=0)
    card_parts.append(t_)
    # stat tiles (5 aggregates + a collectible motif tile)
    tiles = []
    tile_specs = [("conversations", "screen2Unit", P, D, 2), ("practiceMinutes", "screen3Unit", L, D, 3),
                  ("phrasesSaved", "screen4Unit", Y, D, 4), ("topicsExplored", "screen5Unit", LL, D, 5),
                  ("languagesPractised", "screen6Unit", D, WP, 6)]
    for i, (pn, un, bgc, ink, scr) in enumerate(tile_specs):
        tx, ty = cs_["tiles"][i]
        t_id = nid()
        hn, hx_, _ = hero_number(f"{tg} {pn}", pn, 14 - 71, 8 - 34, 115, 30, ink, counting=True, wdth=100, ls=-1)
        un_id, _c, ut = bound_text(f"{tg} {pn} label", 14 - 71, 44 - 34, 115, un, font="body", size=11, color=ink,
                                   wght=600, sizing="fixed", h=16, overflow="ellipsis", wrap="noWrap")
        mask = nid()
        sid, st = disp(30, ink, 800)
        masked = text(f"{tg} {pn} private", 14 - 71, 8 - 34, [st], [run(sid, "—")], id=mask, op=0)
        fly = nid()
        tiles.append({"id": t_id, "num": hn, "mask": mask, "scr": scr, "fly": fly, "x": tx})
        card_parts.append(node(f"{tg} tile {pn}", [node(f"{tg} tile fly {pn}", [
            hx_, masked, ut, shape("tile", [rect(143, 68, 18, 0, 0)], [fill(bgc)], x=-71, y=-34)], id=fly, x=71, y=34)],
            id=t_id, x=tx, y=ty))
    mtile_id = nid()
    mt_a, mt_b = {}, {}
    mtx, mty = cs_["mtile"]
    card_parts.append(node(f"{tg} tile motif", [
        node("tile motif A", [motif_bubble(f"{tg} tile motif A", P, PD, False, 0.22, ids=mt_a)], x=48, y=36),
        node("tile motif B", [motif_bubble(f"{tg} tile motif B", L, LD, True, 0.2, ids=mt_b)], x=96, y=38),
        shape("tile", [rect(143, 68, 18, 0, 0)], [fill(WD)])], id=mtile_id, x=mtx, y=mty))
    bg_id = nid()
    card_parts.append(shape(f"{tg} blob", [smooth_path(bubble_pts(1.3, True))], [fill("55F6E97C")], x=cs_["blob"][0],
                            y=cs_["blob"][1], rot=-0.3,
                            children=[E("ClippingShape", {"sourceId": bg_id, "name": "Clip to card"})]))
    card_parts.append(shape(f"{tg} face", [rect(CW, CH_, 30, 0, 0)], [fill(WP)], id=bg_id))
    card_parts.append(shape(f"{tg} shadow", [rect(CW, CH_, 30, 0, 0)], [fill("55000000", feather=(18, 0, 14))]))

    # card animations
    c_rest = Anim(f"{tg} settled", 1)
    c_asm = Anim(f"{tg} assemble", 140)
    c_empty_off = Anim(f"{tg} mode: stats", 1)
    c_empty_on = Anim(f"{tg} mode: new user", 1)
    c_name_on, c_name_off = Anim(f"{tg} name shown", 1), Anim(f"{tg} name hidden", 1)
    c_sens_on, c_sens_off = Anim(f"{tg} minutes shown", 1), Anim(f"{tg} minutes private", 1)
    c_pers_on, c_pers_off = Anim(f"{tg} persona shown", 1), Anim(f"{tg} persona hidden (neutral motif)", 1)
    c_pick = [Anim(f"{tg} persona {k}", 1) for k in range(4)]

    # Assembly: the wordmark slides in, the year lands like a stamp, the persona emblem drops in with a squash and
    # its rings draw on, the title cascades, then the five tiles are dealt in from alternating sides (counting up)
    # and the collectible motif tile flips in last.
    def asm(obj, prop_, keys, rest):
        c_asm.k(obj, prop_, keys)
        c_rest.hold(obj, prop_, rest)

    wmx = cs_["wm"][0]
    ey0 = cs_["emb"][1]
    for obj, f0 in [(wm_id, 0), (year_id, 6), (emb_id, 12), (pt_id, 30), (pd_id, 38), (mtile_id, 84)] + \
            [(t["id"], 44 + i * 6) for i, t in enumerate(tiles)]:
        asm(obj, "opacity", [(0, 0, "hold"), (f0, 1, "hold")], 1)
    asm(wm_id, "x", [(0, wmx - 104, "hold"), (0, wmx - 104, (0.25, 1.3, 0.5, 1)), (22, wmx, "hold")], wmx)
    asm(year_id, "scaleX", [(0, 2.4, "hold"), (6, 2.4, (0.6, 0, 0.9, 0.6)), (14, 0.86, "el"), (44, 1, "hold")], 1)
    asm(year_id, "scaleY", [(0, 2.4, "hold"), (6, 2.4, (0.6, 0, 0.9, 0.6)), (14, 0.86, "el"), (44, 1, "hold")], 1)
    asm(year_id, "rotation", [(0, -0.5, "hold"), (6, -0.5, "out"), (16, 0.04, "el"), (44, 0, "hold")], 0)
    asm(emb_id, "y", [(0, ey0 - 110, "hold"), (12, ey0 - 110, (0.5, 0, 0.9, 0.5)), (30, ey0, "hold")], ey0)
    asm(emb_id, "scaleY", [(0, 1.2, "hold"), (28, 1.2, "lin"), (32, 0.74, "el"), (74, 1, "hold")], 1)
    asm(emb_id, "scaleX", [(0, 0.86, "hold"), (28, 0.86, "lin"), (32, 1.22, "el"), (74, 1, "hold")], 1)
    for k, tid in enumerate(CSTG["trim"]):
        asm(tid, "end", [(0, 0, "hold"), (32 + k * 5, 0, "io"), (64 + k * 5, 1, "hold")], 1)
    for k, si in enumerate(CSTG["sparks"]):
        asm(si, "scaleX", [(0, 0, "hold"), (40 + k * 4, 0, "back2"), (56 + k * 4, 1, "hold")], 1)
        asm(si, "scaleY", [(0, 0, "hold"), (40 + k * 4, 0, "back2"), (56 + k * 4, 1, "hold")], 1)
    asm(pt_id, "y", [(0, ty_ + 20, "hold"), (30, ty_ + 20, "back"), (50, ty_, "hold")], ty_)
    asm(pd_id, "y", [(0, dy_ + 12, "hold"), (38, dy_ + 12, "out"), (58, dy_, "hold")], dy_)
    for i, t in enumerate(tiles):
        f0 = 44 + i * 6
        side = -1 if i % 2 == 0 else 1
        asm(t["fly"], "x", [(0, 71 + side * 260, "hold"), (f0, 71 + side * 260, (0.2, 1.2, 0.45, 1)), (f0 + 26, 71, "hold")], 71)
        asm(t["fly"], "rotation", [(0, side * 0.7, "hold"), (f0, side * 0.7, "back"), (f0 + 30, 0, "hold")], 0)
        asm(t["fly"], "scaleX", [(0, 1, "hold"), (f0 + 22, 1, "lin"), (f0 + 26, 1.08, "el"), (f0 + 56, 1, "hold")], 1)
        asm(t["fly"], "scaleY", [(0, 1, "hold"), (f0 + 22, 1, "lin"), (f0 + 26, 0.9, "el"), (f0 + 56, 1, "hold")], 1)
    asm(mtile_id, "y", [(0, mty - 48, "hold"), (84, mty - 48, "back"), (104, mty, "hold")], mty)
    asm(mtile_id, "rotation", [(0, 0.6, "hold"), (84, 0.6, "back"), (108, 0, "hold")], 0)
    for an, empty in ((c_empty_off, False), (c_empty_on, True)):
        for t in tiles:
            an.hold(t["id"], "x", -900 if empty else t["x"])
        an.hold(mtile_id, "x", -900 if empty else mtx)
        an.hold(empty_h, "opacity", 1 if empty else 0)
        an.hold(empty_s, "opacity", 1 if empty else 0)
    for an, on in ((c_name_on, True), (c_name_off, False)):
        an.hold(name_id, "opacity", 1 if on else 0)
    mins = tiles[1]
    for an, on in ((c_sens_on, True), (c_sens_off, False)):
        an.hold(mins["num"], "opacity", 1 if on else 0)
        an.hold(mins["mask"], "opacity", 0 if on else 1)
    for an, on in ((c_pers_on, True), (c_pers_off, False)):
        an.hold(emb_id, "x", cs_["emb"][0] if on else -900)
        an.hold(pt_id, "x", tx_ if on else -900)
        an.hold(pd_id, "x", dx_ if on else -900)
        an.hold(neutral_id, "opacity", 0 if on else 1)
    for k, an in enumerate(c_pick):
        for m, e in enumerate(CEMB):
            an.hold(e["root"], "opacity", 1 if m == k else 0)
            for obj, prop_, keys in e["rev"]:
                an.hold(obj, prop_, keys[-1][1])
        for ci, col in zip(CSTG["ring_c"], CEMB[k]["rings"]):
            an.k(ci, "colorValue", [(0, col, "hold")], kind="c")
        an.k(CSTG["ground_c"], "colorValue", [(0, CEMB[k]["ground"], "hold")], kind="c")
    card_anims = [c_rest, c_asm, c_empty_off, c_empty_on, c_name_on, c_name_off, c_sens_on, c_sens_off, c_pers_on,
                  c_pers_off] + c_pick

    def two_state(name, a_anim, b_anim, cond_a, cond_b, cap_a, cap_b):
        ia, ib = nid(), nid()
        return E("StateMachineLayer", {"name": name, "id": nid()}, [
            E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
            E("EntryState", {"x": -200, "y": 0}, [trans(ia)]),
            astate(ia, a_anim.id, 0, 0, [trans(ib, cond_b)], caption=cap_a),
            astate(ib, b_anim.id, 250, 0, [trans(ia, cond_a)], caption=cap_b)])

    asm_rest, asm_go = nid(), nid()
    m_a, m_b = nid(), nid()
    card_layers = [
        E("StateMachineLayer", {"name": "Assemble", "id": nid()}, [
            E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
            E("EntryState", {"x": -200, "y": 0}, [trans(asm_rest)]),
            astate(asm_rest, c_rest.id, 0, 0, [trans(asm_go, [cond(cs, "n", 10), RMF])], caption="Settled"),
            astate(asm_go, c_asm.id, 250, 0, [trans(asm_rest, [cond(cs, "n", 10, "notEqual")])], reset=True,
                   caption="Assemble (summary)")]),
        # Mode layer (all metric scenes hidden -> new user)
        E("StateMachineLayer", {"name": "Mode", "id": nid()}, [
            E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
            E("EntryState", {"x": -200, "y": 0}, [trans(m_a)]),
            astate(m_a, c_empty_off.id, 0, 0, [trans(m_b, all_hidden)], caption="Stats"),
            astate(m_b, c_empty_on.id, 250, 0, [trans(m_a, [cond(show(k), "b", True)]) for k in range(2, 9)],
                   caption="New user")]),
        two_state("Name privacy", c_name_off, c_name_on, [cond(V("shareIncludeName"), "b", False)],
                  [cond(V("shareIncludeName"), "b", True)], "Name hidden", "Name shown"),
        two_state("Sensitive values", c_sens_off, c_sens_on, [cond(V("shareIncludeSensitiveValues"), "b", False)],
                  [cond(V("shareIncludeSensitiveValues"), "b", True)], "Minutes private", "Minutes shown"),
        two_state("Persona visibility", c_pers_on, c_pers_off, [cond(show(9), "b", True)], [cond(show(9), "b", False)],
                  "Persona shown", "Neutral motif"),
    ]
    pick_states, pick_any = [], []
    first_pick = None
    for k, an in enumerate(c_pick):
        sid_ = nid()
        first_pick = first_pick or sid_
        pick_states.append(astate(sid_, an.id, k * 250, 0, caption=f"Persona {k}"))
        for rg in idx_ranges(k):
            pick_any.append(trans(sid_, rg))
    card_layers.append(E("StateMachineLayer", {"name": "Persona pick", "id": nid()}, [
        E("AnyState", {"x": -200, "y": -200}, pick_any), E("ExitState", {"x": -200, "y": -320}),
        E("EntryState", {"x": -200, "y": 0}, [trans(first_pick)])] + pick_states))
    ab = E("Artboard", {"isComponent": True, "defaultStateMachineId": sm_id, "viewModelId": VM,
                        "viewModelInstanceId": "0:95", "styleId": cd["style"], "width": CW, "height": CH_,
                        "x": 460 if variant == "tall" else 860, "y": 100, "name": cs_["name"], "id": ab_id},
           [E("LayoutComponentStyle", {"name": f"{tg} style", "id": cd["style"]})] + card_parts +
           [E("StateMachine", {"name": "Card", "id": sm_id}, card_layers)] + [a.xml() for a in card_anims])
    return ab, card_anims


card_ab, CARD_ANIMS = build_card("tall", CARD_AB, CARD_SM)
cardw_ab, CARDW_ANIMS = build_card("wide", CARDW_AB, CARDW_SM)
CARD_ANIMS = CARD_ANIMS + CARDW_ANIMS

# ================================================================ VIEW MODEL + instances


def vm_value(pid, kind, v):
    tag = {"n": "ViewModelInstanceNumber", "s": "ViewModelInstanceString", "b": "ViewModelInstanceBoolean",
           "c": "ViewModelInstanceColor", "t": "ViewModelInstanceTrigger"}[kind]
    a = {"viewModelPropertyId": pid}
    if kind != "t":
        a["propertyValue"] = v
    return E(tag, a)


def instance(name, iid, overrides):
    vals = []
    for pname, (pid, kind, default) in PROPS.items():
        v = overrides.get(pname, default)
        if kind == "c" and isinstance(v, str) and v.startswith("#"):
            v = argb(v)
        vals.append(vm_value(pid, kind, v))
    return E("ViewModelInstance", {"exports": True, "name": name, "id": iid}, vals)


fx_zero = json.load(open(os.path.join(ROOT, "fixtures", "zero-user.json")))
fx_ext = json.load(open(os.path.join(ROOT, "fixtures", "extreme.json")))
vm_props = []
for pname, (pid, kind, default) in PROPS.items():
    tag = {"n": "ViewModelPropertyNumber", "s": "ViewModelPropertyString", "b": "ViewModelPropertyBoolean",
           "c": "ViewModelPropertyColor", "t": "ViewModelPropertyTrigger"}[kind]
    vm_props.append(E(tag, {"name": pname, "id": pid}))
vm_xml = E("ViewModel", {"defaultInstanceId": "0:95", "name": "UserRecap", "id": VM}, vm_props + [
    instance("Sample fixture", "0:95", {}),
    instance("New user fixture", "0:96", fx_zero),
    instance("Extreme fixture", "0:97", fx_ext)])

components = [E("ComponentAsset", {"artboardId": CLOCK_AB, "name": "Dwell Clock"}),
              E("ComponentAsset", {"artboardId": CARD_AB, "name": "Share Card"}),
              E("ComponentAsset", {"artboardId": CARDW_AB, "name": "Share Card Wide"})]


def doc(children):
    return '<Rive version="1" kind="fragment">\n' + "\n".join(children) + "\n</Rive>\n"


open(os.path.join(ROOT, "scene.rml"), "w").write(doc([main_xml]))
open(os.path.join(ROOT, "components.rml"), "w").write(doc([clock_ab, card_ab, cardw_ab] + components))
open(os.path.join(ROOT, "data.rml"), "w").write(doc([vm_xml] + CONV + FONTS))
print("generated: %d animations, %d converters, %d view model properties" % (len(ANIMS) + len(CARD_ANIMS) + 2, len(CONV), len(PROPS)))

# ---------------------------------------------------------------- loop seam check
for an in ANIMS + CARD_ANIMS:
    if an.loop != "loop":
        continue
    for obj, props in an.tracks.items():
        for prop_, (kind, keys) in props.items():
            ks = sorted(keys, key=lambda t: t[0])
            if len(ks) > 1 and kind == "d":
                v0, v1 = ks[0][1], ks[-1][1]
                wrap_ok = (prop_ == "rotation" and abs(abs(v1 - v0) - 2 * math.pi) < 1e-3) or (obj, prop_) in WRAPS
                if abs(v0 - v1) > 1e-6 and not wrap_ok:
                    print(f"SEAM WARNING {an.name}: {obj}.{prop_} {v0} -> {v1}")
                if ks[-1][0] > an.dur:
                    print(f"KEY PAST END {an.name}: {obj}.{prop_} frame {ks[-1][0]} > {an.dur}")
