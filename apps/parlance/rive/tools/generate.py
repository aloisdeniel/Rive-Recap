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
                 bind, Anim, cond, trans, write, fire_trigger, toggle, copy_str, fire_event, astate)  # noqa

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


def ftok(ex):
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
    # binary op
    a, op, b = ex
    return ([E("FormulaTokenParenthesisOpen")] + ftok(a) + [E("FormulaTokenOperation", {"operationType": OPS[op]})]
            + ftok(b) + [E("FormulaTokenParenthesisClose")])


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
C_FOCUS = [formula(f"Focus ring {k}", fmax(0, (1, "-", fmin(1, (("in", "-", k), "*", ("in", "-", k))))))
           for k in range(0, 6)]

# ---------------------------------------------------------------- assets / fonts
F_DISP = nid()
F_TEXT = nid()
FONTS = [E("FontAsset", {"file": "assets/fonts/BricolageGrotesque-VF.ttf", "name": "Bricolage Grotesque",
                         "id": F_DISP}),
         E("FontAsset", {"file": "assets/fonts/NotoSans-wght400-700.ttf", "name": "Noto Sans", "id": F_TEXT})]


def disp(size, color, wght=800, wdth=None, cid=None, cbinds=None, lh=None, ls=None, sid=None):
    sid = sid or nid()
    style = {800: "ExtraBold", 700: "Bold", 600: "SemiBold", 500: "Medium", 400: "Regular"}.get(wght, "Custom")
    return sid, tstyle(sid, F_DISP, size, color, wght=wght, wdth=wdth, opsz=min(96, max(12, size)), cid=cid,
                       cbinds=cbinds, lh=lh, ls=ls, family="Bricolage Grotesque", style=style)


def body(size, color, wght=400, cid=None, cbinds=None, lh=None, sid=None):
    sid = sid or nid()
    style = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}.get(wght, "Custom")
    return sid, tstyle(sid, F_TEXT, size, color, wght=wght, cid=cid, cbinds=cbinds, lh=lh,
                       family="Noto Sans", style=style)


def bound_text(name, x, y, w, prop_name, font="disp", size=30, color=D, wght=800, lh=None, align=None,
               h=None, sizing="autoHeight", overflow=None, wrap="wrap", tid=None, cid=None, literal=None,
               op=None, conv_id=None, wdth=None):
    tid = tid or nid()
    cid = cid or nid()
    if font == "disp":
        sid, st = disp(size, color, wght, cid=cid, lh=lh, wdth=wdth)
    else:
        sid, st = body(size, color, wght, cid=cid, lh=lh)
    lit = literal if literal is not None else str(PROPS[prop_name][2])
    return tid, cid, text(name, x, y, [st], [run(sid, lit, [bind(V(prop_name), 268, conv_id)])], id=tid, w=w,
                          h=h, sizing=sizing, overflow=overflow, wrap=wrap, align=align, op=op)


def hero_number(name, prop_name, x, y, w, size, color, align=None, counting=True, wdth=88, wght=800):
    """Three tier texts (<1,000 / <1,000,000 / larger) inside one node. Returns (node_id, xml, color ids)."""
    tc = TC if counting else TS
    nid_ = nid()
    sep = V("groupSeparator")
    src = V(prop_name)
    kids, cids = [], []
    hh = size * 1.12

    def tier(label, runs_spec, op_conv):
        cid = nid()
        sid, st = disp(size, color, wght, wdth=wdth, cid=cid, lh=size * 1.0)
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
def bubble_pts(s=1.0, mirror=False):
    pts = [(0, -100), (72, -72), (102, -2), (84, 58), (106, 128, "c", 7), (34, 96), (-4, 101), (-72, 71),
           (-102, 0), (-72, -72)]
    out = []
    for p in pts:
        x, y = p[0] * s, p[1] * s
        if mirror:
            x = -x
        out.append((x, y) + tuple(p[2:]))
    if mirror:
        out = [out[0]] + out[1:][::-1]
    return out


def face(prefix, s=1.0, ink=D, tongue=PD, ids=None):
    """Expressive punctuation face: happy closed eyes + open laughing mouth."""
    ids = ids if ids is not None else {}
    ids["mouth"] = nid()
    ids["eyes"] = nid()
    eye = lambda ex: shape(f"{prefix} eye", [smooth_path([(-13 * s, 5 * s), (0, -8 * s), (13 * s, 5 * s)], closed=False)],
                           [stroke(ink, 8 * s)], x=ex * s, y=-20 * s)
    mouth = node(f"{prefix} mouth", [
        shape(f"{prefix} tongue", [ellipse(36 * s, 16 * s)], [fill(tongue)], y=33 * s),
        shape(f"{prefix} mouth shape", [smooth_path([(-40 * s, 0, "c", 5 * s), (40 * s, 0, "c", 5 * s), (28 * s, 30 * s),
                                                     (0, 45 * s), (-28 * s, 30 * s)])], [fill(ink)]),
    ], id=ids["mouth"], y=14 * s)
    cheeks = [shape(f"{prefix} cheek", [ellipse(22 * s, 12 * s)], [fill("55FFFFFF")], x=cx * s, y=6 * s)
              for cx in (-56, 56)]
    return node(f"{prefix} face", [mouth, node(f"{prefix} eyes", [eye(-34), eye(34)], id=ids["eyes"])] + cheeks,
                id=ids.get("face"))


def motif_bubble(prefix, color, shade, mirror=False, s=1.0, with_face=True, ids=None, tongue=PD):
    ids = ids if ids is not None else {}
    ids.setdefault("root", nid())
    ids.setdefault("bob", nid())
    ids.setdefault("elastic", nid())
    ids.setdefault("face", nid())
    hl_x = 48 if mirror else -48
    kids = []
    if with_face:
        kids.append(face(prefix, s, ids=ids, tongue=tongue))
    kids += [
        shape(f"{prefix} highlight", [ellipse(34 * s, 16 * s)], [fill("66FFFFFF")], x=hl_x * s, y=-60 * s,
              rot=0.6 if mirror else -0.6),
        shape(f"{prefix} body", [smooth_path(bubble_pts(s, mirror))], [fill(color)], id=ids.get("body")),
        shape(f"{prefix} depth", [smooth_path(bubble_pts(s, mirror))], [fill(shade)], x=6 * s, y=9 * s),
    ]
    return node(prefix, [node(f"{prefix} bob", [node(f"{prefix} elastic", kids, id=ids["elastic"])], id=ids["bob"])],
                id=ids["root"])


def comma_pts(s=1.0):
    # a quotation-mark comma: round head with a tapering tail sweeping down-left
    return [(0, -62 * s), (44 * s, -40 * s), (52 * s, 6 * s), (34 * s, 66 * s), (-22 * s, 130 * s, "c", 6 * s),
            (-10 * s, 70 * s), (-34 * s, 38 * s), (-50 * s, -6 * s), (-40 * s, -44 * s)]


def quote_mark(prefix, s, color, shade, x=0, y=0, id=None, hl=True):
    kids = []
    for dx in (-64 * s, 64 * s):
        if hl:
            kids.append(shape(f"{prefix} glint", [ellipse(22 * s, 12 * s)], [fill("70FFFFFF")], x=dx - 18 * s,
                              y=-38 * s, rot=-0.6))
        kids.append(shape(f"{prefix} comma", [smooth_path(comma_pts(s))], [fill(color)], x=dx))
        kids.append(shape(f"{prefix} comma depth", [smooth_path(comma_pts(s))], [fill(shade)], x=dx + 7 * s, y=9 * s))
    return node(prefix, kids, id=id, x=x, y=y)


# ---------------------------------------------------------------- scene scaffolding
SCENES = {}


class Scene:
    def __init__(self, n, bg):
        self.n = n
        self.bg = bg
        self.root = nid()
        self.parts = []          # xml children, top first
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


def count(sc, f0=24, f1=84):
    sc.track(DRIVER, "x", [(0, 0, "hold"), (f0, 0, "out2"), (f1, 1, "hold")])


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


def copy_block(sc, x, y, n, w=342, head_size=34, head_color=D, sup_color=D, unit_size=30, unit_y=None,
               head_y=None, sup_y=None, align=None, f0=70):
    """unit + headline + support for a metric scene, flowed in columns so long copy pushes down instead of
    overlapping. Items closer than 150pt share one column."""
    ids = {}
    entries = []
    if unit_y is not None:
        ids["unit"], ids["unit_c"], t = flow_text(f"S{n} unit", w, f"screen{n}Unit", size=unit_size,
                                                  color=head_color, wght=700, align=align, lh=unit_size * 1.1)
        entries.append((unit_y, t, "unit", 40, 18))
    ids["head"], ids["head_c"], t = flow_text(f"S{n} headline", w, f"screen{n}Headline", size=head_size,
                                              color=head_color, wght=800, lh=head_size * 1.04, align=align, wdth=92)
    entries.append((head_y, t, "head", f0, 26))
    ids["sup"], ids["sup_c"], t = flow_text(f"S{n} support", w, f"screen{n}Support", font="body", size=17,
                                            color=sup_color, wght=500, lh=23, align=align)
    entries.append((sup_y, t, "sup", f0 + 12, 16))
    entries.sort(key=lambda e: e[0])
    groups = []
    for e in entries:
        if groups and e[0] - groups[-1][-1][0] < 150:
            groups[-1].append(e)
        else:
            groups.append([e])
    for gi, g in enumerate(groups):
        bottom = 92 if g[0][0] > 500 else None   # lower copy blocks sit on the control bar and grow upwards
        cid, xml = column(f"S{n} copy {gi}", x, g[0][0], w, [e[1] for e in g], gap=10, bottom=bottom)
        sc.parts.append(xml)
        for (_y, _t, key, fr, dy) in g:
            rise(sc, ids[key], fr, base_y=0, dy=dy)
    return ids


# global motif / driver ids (filled in below)
MA = {"root": nid(), "body": nid()}
MB = {"root": nid(), "body": nid()}
DRIVER = nid()
MOUTH_HIT = nid()

# motif poses: (x, y, sx, sy, rot, faceOpacity)
OFF_A = (-260, -240, 1.2, 1.2, -0.5, 1)
OFF_B = (660, 1120, 1.2, 1.2, 0.5, 1)
COVER_A = (195, 430, 7.4, 8.8, 0.18, 0)
COVER_B = (195, 430, 7.6, 9.0, -0.18, 0)


def motif_keys(anim, ids, keys):
    """keys: list of (frame, pose, ease)."""
    for i, prop in enumerate(["x", "y", "scaleX", "scaleY", "rotation"]):
        anim.k(ids["root"], prop, [(f, pose[i], e) for f, pose, e in keys])
    anim.k(ids["face"], "opacity", [(f, pose[5], e) for f, pose, e in keys])


# ================================================================ SCENES
# Each scene: parts (xml, top-first), enter tracks (frames relative to In start, 60 fps),
# final pose, idle loop.

# ---------- 1. Invitation ----------------------------------------------------
s = Scene(1, WP)
s.motifA = (128, 318, 1.38, 1.38, -0.14, 1)
s.motifB = (284, 408, 1.12, 1.12, 0.12, 1)
name_t = nid()
sid, st = body(17, D, 600)
pill_bg = E("TextStyleBackground", {"cornerRadius": 15, "name": "Pill"}, [fill(L)])
st_pill = st.replace("</TextStylePaint>", pill_bg + "</TextStylePaint>", 1)
s.parts.append(text("S1 name", 24, 102, [st_pill], [run(sid, "  Alex  ", [])], id=name_t, w=250, h=26,
                    sizing="fixed", overflow="ellipsis", wrap="noWrap"))
# The name run is bound below (needs padding spaces around it -> three runs)
s.parts[-1] = text("S1 name", 24, 102, [st_pill], [run(sid, " ", []), run(sid, "Alex", [bind(V("userName"), 268)]),
                                                    run(sid, " ", [])], id=name_t, w=280, h=26, sizing="fixed",
                   overflow="ellipsis", wrap="noWrap")
rise(s, name_t, 52, base_y=102, dy=14)
per_t, _c, t_ = bound_text("S1 period", 24, 136, 342, "periodLabel", font="body", size=13, color=DL, wght=500)
s.parts.append(t_)
rise(s, per_t, 60, base_y=136, dy=10)
# wordmark (kinetic): letters stretch up out of a speech envelope
wm_t = nid()
wm_range = nid()
sid, st = disp(84, D, 800, wdth=78, lh=84)
wm_mod = E("TextModifierGroup", {"modifyOpacity": True, "modifyTranslation": True, "modifyScale": True,
                                 "invertOpacity": True, "opacity": 0, "y": 46, "scaleY": 2.1, "scaleX": 0.6,
                                 "originX": 0.5, "originY": 1, "modifyOrigin": True, "name": "Envelope stretch"},
           [E("TextModifierRange", {"modifyFrom": 1.0, "modifyTo": 1, "falloffFrom": 1.25, "falloffTo": 1,
                                    "name": "Sweep", "id": wm_range},
              [E("CubicInterpolatorComponent", {"x1": 0.2, "y1": 0, "x2": 0.2, "y2": 1, "name": "Ease"})])])
dot_id = nid()
s.parts.append(node("S1 wordmark", [
    text("S1 wordmark text", 0, 0, [st], [run(sid, "parlance")], id=wm_t, extra_children=[wm_mod]),
    shape("S1 wordmark bubble", [smooth_path(bubble_pts(0.17))], [fill(P)], id=dot_id, x=268, y=58),
], x=22, y=500))
s.track(wm_range, 327, [(0, -0.35, "hold"), (34, -0.35, "lin"), (78, 1.0, "hold")])
s.track(wm_range, 317, [(0, -0.1, "hold"), (34, -0.1, "lin"), (78, 1.25, "hold")])
pop(s, dot_id, 74, 24, "back2", rot0=-1.2)
ih_t, ih_c, t1_ = flow_text("S1 headline", 342, "introHeadline", size=32, color=D, wght=800, lh=34, wdth=92)
is_t, is_c, t2_ = flow_text("S1 support", 342, "introSupport", font="body", size=17, color=D, wght=500, lh=23)
s.parts.append(column("S1 copy", 24, 606, 342, [t1_, t2_], gap=12, bottom=96)[1])
rise(s, ih_t, 84, base_y=0)
rise(s, is_t, 96, base_y=0, dy=14)
# giant punctuation sculptures behind the motif
q1 = nid()
q2 = nid()
sid, st = disp(300, Y, 800)
s.parts.append(text("S1 giant quote", 196, 92, [st], [run(sid, "“")], id=q1, rot=0.12))
sid, st = disp(190, LL, 800)
s.parts.append(text("S1 giant bang", 14, 300, [st], [run(sid, "!")], id=q2, rot=-0.22))
pop(s, q1, 20, 34, "back", s0=0.4, rot0=0.7, rot1=0.12)
pop(s, q2, 30, 30, "back", s0=0.3, rot0=-0.9, rot1=-0.22)
s.itrack(q1, "rotation", [(0, 0.12, "sine"), (120, 0.04, "sine"), (240, 0.12, "hold")])
s.itrack(q2, "rotation", [(0, -0.22, "sine"), (120, -0.14, "sine"), (240, -0.22, "hold")])

# ---------- 2. Conversations -------------------------------------------------
s = Scene(2, WP)
s.motifA = (96, 646, 1.18, 1.18, 0.08, 1)
s.motifB = (300, 654, 1.08, 1.08, -0.08, 1)
s.mouth_hit = (96, 650, 170, 150)
hid, hx, hc = hero_number("S2 hero", "conversations", 24, 92, 342, 150, D)
s.parts.insert(0, hx)
s.hero = hid
ids2 = copy_block(s, 24, 0, 2, unit_y=258, head_y=304, sup_y=386)
rise(s, hid, 14, base_y=92, dy=30, dur=20)
count(s)
# punctuation tokens exchanged between the two speech forms
TOK = [("?", P), ("!", D), (";", LD), ("”", P), ("…", D), ("¿", LD), (",", P)]
tok_ids = []
for i, (ch, col) in enumerate(TOK):
    tid = nid()
    inner = nid()
    sid, st = disp(54 if ch not in ("…",) else 44, col, 800)
    s.parts.append(node(f"S2 token {i}", [text(f"S2 token glyph {i}", 0, 0, [st], [run(sid, ch)], ox=0.5, oy=0.5,
                                               id=inner)], id=tid, x=195, y=600, op=0))
    tok_ids.append((tid, inner))
    # idle: arc from one mouth to the other, alternating direction
    period = 300
    off = i * 30
    left = (140, 610)
    right = (256, 618)
    a, b = (left, right) if i % 2 == 0 else (right, left)
    peak = 460 + (i % 3) * 30

    def ph(t):
        return (t + off) % period
    # build a piecewise loop: start at t0 = off
    keys_x, keys_y, keys_o, keys_r = [], [], [], []
    t0 = off
    for (dt, x, y, o, r, ex, ey) in [(0, a[0], a[1], 0, -0.6, "lin", "out"),
                                     (8, a[0] + (b[0] - a[0]) * 0.1, a[1] - 40, 1, -0.3, "lin", "out"),
                                     (40, (a[0] + b[0]) / 2, peak, 1, 0.2, "lin", "in"),
                                     (74, b[0], b[1] - 30, 1, 0.6, "lin", "out"),
                                     (82, b[0], b[1], 0, 0.8, "lin", "lin")]:
        pass
    # simpler deterministic loop: travel during first 82 frames of a 150 frame cycle, offset by staggering start
    start = int(off)
    kx = [(0, a[0], "hold"), (start, a[0], "lin"), (start + 82, b[0], "hold"), (period, b[0], "hold")]
    ky = [(0, a[1], "hold"), (start, a[1], "out"), (start + 40, peak, "in"), (start + 82, b[1], "hold"),
          (period, b[1], "hold")]
    ko = [(0, 0, "hold"), (start, 0, "lin"), (start + 8, 1, "hold"), (start + 72, 1, "lin"), (start + 82, 0, "hold"),
          (period, 0, "hold")]
    kr = [(0, -0.7, "hold"), (start, -0.7, "lin"), (start + 82, 0.9 if i % 2 == 0 else -0.9, "hold"),
          (period, 0.9 if i % 2 == 0 else -0.9, "hold")]
    s.itrack(tid, "x", kx)
    s.itrack(tid, "y", ky)
    s.itrack(tid, "opacity", ko)
    s.itrack(inner, "rotation", kr)
    s.settle(tid, "opacity", 0)
s.idle_dur = 300
# soft lemon shadows under the speech forms
sh1, sh2 = nid(), nid()
s.parts.append(shape("S2 shadow A", [ellipse(170, 26)], [fill("99F6E97C")], id=sh1, x=100, y=770))
s.parts.append(shape("S2 shadow B", [ellipse(150, 24)], [fill("99C7B7F2")], id=sh2, x=304, y=772))
pop(s, sh1, 10, 24, "out")
pop(s, sh2, 18, 24, "out")

# ---------- 3. Minutes practising -------------------------------------------
s = Scene(3, L)
s.mouth_hit = (195, 486, 330, 250)
ids3 = copy_block(s, 24, 0, 3, unit_y=98, head_y=140, sup_y=694)
MOUTH = {"outer": nid(), "breath": nid(), "elastic": nid(), "open": nid(), "teeth": nid(), "tongue": nid()}
lips = [(-176, 0, "c", 40), (-104, -112), (-34, -122), (0, -98), (34, -122), (104, -112), (176, 0, "c", 40),
        (104, 120), (0, 134), (-104, 120)]
opening = [(-134, 0, "c", 34), (-64, -64), (0, -58), (64, -64), (134, 0, "c", 34), (64, 80), (0, 92), (-64, 80)]
hid, hx, hc = hero_number("S3 hero", "practiceMinutes", -122, -52, 244, 104, WP, align="center", wdth=80)
s.hero = hid
mouth_xml = node("S3 mouth", [node("S3 mouth breath", [node("S3 mouth elastic", [
    hx,
    shape("S3 teeth", [rect(124, 24, 9)], [fill(WP)], id=MOUTH["teeth"], y=-50),
    shape("S3 tongue", [ellipse(150, 40)], [fill(PD)], id=MOUTH["tongue"], y=66),
    shape("S3 opening", [smooth_path(opening)], [fill(DD)], id=MOUTH["open"]),
    shape("S3 lip glint", [ellipse(90, 16)], [fill("66FFFFFF")], x=-70, y=-96, rot=-0.15),
    shape("S3 lip glint 2", [ellipse(40, 10)], [fill("55FFFFFF")], x=86, y=104, rot=-0.3),
    shape("S3 lips", [smooth_path(lips)], [fill(P)]),
    shape("S3 lips depth", [smooth_path(lips)], [fill(PD)], x=8, y=12),
], id=MOUTH["elastic"])], id=MOUTH["breath"])], id=MOUTH["outer"], x=195, y=486)
s.parts.insert(0, mouth_xml)
pop(s, MOUTH["outer"], 6, 40, "el2", s0=0.15)
s.track(MOUTH["open"], "scaleY", [(0, 0.05, "hold"), (16, 0.05, "el"), (64, 1, "hold")])
s.track(MOUTH["teeth"], "opacity", [(0, 0, "hold"), (30, 0, "lin"), (40, 1, "hold")])
s.track(hid, "scaleY", [(0, 0.2, "hold"), (22, 0.2, "el"), (80, 1, "hold")])
count(s, 22, 86)
# floating syllable chips around the mouth ("ah", "oh", "mm")
for i, (syl, x, y, col, r) in enumerate([("ah", 52, 330, P, -0.25), ("oh", 330, 350, D, 0.2), ("mm", 318, 640, WP, 0.15)]):
    cid_ = nid()
    sid, st = disp(28, col, 800)
    s.parts.append(text(f"S3 syllable {syl}", x, y, [st], [run(sid, syl)], id=cid_, ox=0.5, oy=0.5, rot=r))
    pop(s, cid_, 44 + i * 8, 24, "back", rot0=r - 0.8, rot1=r)
    s.itrack(cid_, "y", [(0, y, "sine"), (120, y - 10, "sine"), (240, y, "hold")])
s.itrack(MOUTH["breath"], "scaleY", [(0, 1, "sine"), (60, 1.035, "sine"), (120, 1, "sine"), (180, 1.035, "sine"), (240, 1, "hold")])
s.itrack(MOUTH["breath"], "scaleX", [(0, 1, "sine"), (60, 0.985, "sine"), (120, 1, "sine"), (180, 0.985, "sine"), (240, 1, "hold")])

# ---------- 4. Phrases saved -------------------------------------------------
s = Scene(4, D)
hid, hx, hc = hero_number("S4 hero", "phrasesSaved", 24, 92, 342, 150, WP)
s.parts.append(hx)
s.hero = hid
rise(s, hid, 14, base_y=92, dy=30, dur=20)
count(s)
ids4 = copy_block(s, 24, 0, 4, unit_y=258, head_y=304, sup_y=386, w=250, head_color=WP, sup_color=LL)
QUOTES = nid()
s.parts.append(quote_mark("S4 quotes", 1.12, Y, YD, x=200, y=640, id=QUOTES))
pop(s, QUOTES, 10, 34, "back", s0=0.2)
s.track(QUOTES, "y", [(0, 700, "hold"), (10, 700, "back"), (44, 640, "hold")])
WORDS = [("hola", P, D), ("merci", Y, D), ("ciao", L, D), ("hallo", LL, D), ("olá", P, WP), ("grazie", WP, D),
         ("привет", L, D), ("γεια", Y, D)]
REST = [(300, 300, 0.32), (322, 372, -0.18), (282, 438, 0.12), (210, 500, -0.22), (330, 512, 0.26),
        (120, 520, 0.18), (250, 568, -0.08), (156, 586, -0.3)]
for i, ((word, bgc, ink), (rx, ry, rr)) in enumerate(zip(WORDS, REST)):
    wid = nid()
    inner = nid()
    wpx = 22 + len(word) * 13.5
    sid, st = body(21, ink, 600)
    s.parts.insert(0, node(f"S4 word {word}", [node(f"S4 word float {i}", [
        text(f"S4 word text {i}", 0, 0, [st], [run(sid, word)], ox=0.5, oy=0.5),
        shape(f"S4 word block {i}", [rect(wpx, 42, 13)], [fill(bgc)]),
        shape(f"S4 word block depth {i}", [rect(wpx, 42, 13)], [fill("40000000")], x=3, y=5),
    ], id=inner)], id=wid, x=rx, y=ry, rot=rr))
    f0 = 26 + i * 7
    s.track(wid, "y", [(0, -80, "hold"), (f0, -80, "back"), (f0 + 30, ry, "hold")])
    s.track(wid, "rotation", [(0, rr + 1.2, "hold"), (f0, rr + 1.2, "out"), (f0 + 34, rr, "hold")])
    s.track(wid, "opacity", [(0, 0, "hold"), (f0, 1, "hold")])
    s.itrack(inner, "y", [(0, 0, "sine"), (60 + i * 7, -7, "sine"), (240, 0, "hold")])
    s.itrack(inner, "rotation", [(0, 0, "sine"), (120, 0.06 * (1 if i % 2 else -1), "sine"), (240, 0, "hold")])
# sparkle ticks
for i, (x, y, r) in enumerate([(70, 570, -0.6), (348, 600, 0.5), (58, 640, -0.2)]):
    tk = nid()
    s.parts.append(shape(f"S4 tick {i}", [rect(5, 30, 2.5)], [fill(Y)], id=tk, x=x, y=y, rot=r))
    pop(s, tk, 40 + i * 6, 20, "back")
    s.itrack(tk, "opacity", [(0, 1, "sine"), (40 + i * 30, 0.3, "sine"), (240, 1, "hold")])
# ---------- 5. Topics explored ----------------------------------------------
s = Scene(5, Y)
hid, hx, hc = hero_number("S5 hero", "topicsExplored", 24, 92, 342, 168, D, align="right")
s.parts.append(hx)
s.hero = hid
rise(s, hid, 14, base_y=92, dy=30, dur=20)
count(s)
ids5 = copy_block(s, 24, 0, 5, unit_y=272, head_y=630, sup_y=708, align=None)
RING = nid()
RING_SPIN = nid()
symbols = []
bub = []


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
for i, (bcol, shade, sym_a, sym_b, inkc) in enumerate([(P, PD, "sun", "leaf", WP), (L, LD, "star", "wave", D),
                                                      (D, DD, "cup", "dots", Y)]):
    ang = -math.pi / 2 + i * 2 * math.pi / 3
    bx, by = 112 * math.cos(ang), 112 * math.sin(ang)
    b_id, cr, sa, sb = nid(), nid(), nid(), nid()
    ring_kids.append(node(f"S5 bubble {i}", [node(f"S5 bubble upright {i}", [
        node("sym a", [symbol(sym_a, inkc)], id=sa, y=-4),
        node("sym b", [symbol(sym_b, inkc)], id=sb, y=-4, op=0),
        shape(f"S5 bubble body {i}", [smooth_path(bubble_pts(0.58, i == 1))], [fill(bcol)]),
        shape(f"S5 bubble depth {i}", [smooth_path(bubble_pts(0.58, i == 1))], [fill(shade)], x=4, y=6),
    ], id=cr)], id=b_id, x=bx, y=by))
    bub.append((b_id, cr, sa, sb))
    pop(s, b_id, 20 + i * 8, 30, "back")
    # symbols swap: a -> b -> a over the idle loop, staggered
    st0 = 100 + i * 40
    s.itrack(sa, "opacity", [(0, 1, "hold"), (st0, 1, "lin"), (st0 + 12, 0, "hold"), (st0 + 300, 0, "lin"), (st0 + 312, 1, "hold"), (720, 1, "hold")])
    s.itrack(sb, "opacity", [(0, 0, "hold"), (st0, 0, "lin"), (st0 + 12, 1, "hold"), (st0 + 300, 1, "lin"), (st0 + 312, 0, "hold"), (720, 0, "hold")])
    s.itrack(sa, "scaleX", [(0, 1, "hold"), (st0, 1, "in"), (st0 + 12, 0.3, "hold"), (st0 + 300, 0.3, "back"), (st0 + 324, 1, "hold"), (720, 1, "hold")])
    s.itrack(sb, "scaleX", [(0, 0.3, "hold"), (st0, 0.3, "back"), (st0 + 24, 1, "hold"), (st0 + 300, 1, "in"), (st0 + 312, 0.3, "hold"), (720, 0.3, "hold")])
    s.itrack(cr, "rotation", [(0, 0, "lin"), (720, -2 * math.pi, "hold")])
orbit = shape("S5 orbit", [ellipse(224, 224)], [stroke("553D2456", 2.5, effects=[E("DashPath", {"name": "Dots"}, [
    E("Dash", {"length": 2, "name": "On"}), E("Dash", {"length": 12, "name": "Off"})])])], id=nid())
s.parts.append(node("S5 ring", [node("S5 ring spin", ring_kids + [orbit], id=RING_SPIN)], id=RING, x=195, y=458))
s.track(RING, "rotation", [(0, -2.4, "hold"), (14, -2.4, "out"), (80, 0, "hold")])
s.itrack(RING_SPIN, "rotation", [(0, 0, "lin"), (720, 2 * math.pi, "hold")])
s.idle_dur = 720

# ---------- 6. Languages practised ------------------------------------------
s = Scene(6, WP)
hid, hx, hc = hero_number("S6 hero", "languagesPractised", 24, 92, 342, 168, D)
s.parts.append(hx)
s.hero = hid
rise(s, hid, 14, base_y=92, dy=30, dur=20)
count(s)
ids6 = copy_block(s, 24, 0, 6, unit_y=272, head_y=616, sup_y=694)
RIB = []
rib_specs = [
    (P, [(-40, 400), (60, 360), (170, 420), (270, 470), (430, 420)], "hello · hola · ciao · hallo · olá · hej · ", WP, None),
    (L, [(-40, 520), (80, 450), (190, 390), (300, 430), (430, 500)], "merci · grazie · danke · obrigado · ", D, C_RIB2),
    (D, [(-40, 460), (90, 540), (210, 500), (320, 380), (430, 360)], "привет · γεια · salut · ahoj · ", Y, C_RIB3),
]
rib_parts = []
for i, (col, pts, words, ink, opconv) in enumerate(rib_specs):
    rid, sid_, trim, tmod, grp = nid(), nid(), nid(), nid(), nid()
    st_id, st = body(15, ink, 700)
    words_text = text(f"S6 ribbon words {i}", 0, 0, [st], [run(st_id, words * 2)], id=nid(), extra_children=[
        E("TextModifierGroup", {"name": "Follow ribbon", "id": grp}, [
            E("TextModifierRange", {"modifyFrom": 0, "modifyTo": 1, "name": "All"}),
            E("TextFollowPathModifier", {"targetId": sid_, "orient": True, "offset": 0, "name": "Follow",
                                         "id": tmod})])])
    rib = node(f"S6 ribbon {i}", [
        words_text,
        shape(f"S6 ribbon band {i}", [smooth_path(pts, closed=False, id=nid())],
              [E("Stroke", {"thickness": 36, "cap": "round", "join": "round", "name": "Band"},
                 [solid(col), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Reveal",
                                             "id": trim})])], id=sid_),
    ], id=rid, binds=[bind(V("languagesPractised"), 18, opconv)] if opconv else None)
    RIB.append((rid, sid_, trim, tmod))
    rib_parts.append(rib)
    f0 = 20 + i * 12
    s.track(trim, "end", [(0, 0, "hold"), (f0, 0, "io"), (f0 + 44, 1, "hold")])
    drift = -0.12 if i != 1 else 0.12
    s.itrack(tmod, "offset", [(0, 0, "sine"), (300, drift, "sine"), (600, 0, "hold")])
    s.itrack(rid, "y", [(0, 0, "sine"), (150 + i * 20, -8 + i * 5, "sine"), (600, 0, "hold")])
# weave: a trimmed copy of the plum ribbon drawn over the persimmon one
weave = shape("S6 weave over", [smooth_path(rib_specs[2][1], closed=False)],
              [E("Stroke", {"thickness": 36, "cap": "butt", "join": "round", "name": "Band"},
                 [solid(D), E("TrimPath", {"start": 0.62, "end": 0.78, "modeValue": "sequential", "name": "Segment"})])],
              id=nid(), binds=[bind(V("languagesPractised"), 18, C_RIB3)])
s.parts.append(node("S6 ribbons", [weave] + rib_parts, id=nid()))
s.track(weave_id := None, "opacity", []) if False else None
s.idle_dur = 600

# ---------- 7. Day practice streak ------------------------------------------
s = Scene(7, P)
ids7 = copy_block(s, 24, 0, 7, head_y=98, sup_y=180, head_color=DD, sup_color=DD)
hid, hx, hc = hero_number("S7 hero", "longestStreakDays", 24, 556, 342, 168, DD, wdth=80)
s.parts.append(hx)
s.hero = hid
rise(s, hid, 30, base_y=556, dy=30, dur=20)
count(s, 30, 90)
u7, u7c, t_ = bound_text("S7 unit", 24, 724, 342, "screen7Unit", size=26, color=DD, wght=700, sizing="fixed", h=32,
                         overflow="fitFontSize", wrap="noWrap")
s.parts.append(t_)
rise(s, u7, 46, base_y=724, dy=12)
LINE = nid()
LINE_TRIM = nid()
line_pts = [(-30, 300), (120, 262), (330, 300), (360, 360), (240, 400), (60, 420), (40, 470), (160, 520), (420, 500)]
tokens7 = []
for i, (ch, col) in enumerate([(".", WP), (",", DD), (";", WP), ("!", DD), ("?", WP)]):
    tid, bounce, fp = nid(), nid(), nid()
    sid, st = disp(58, col, 800)
    d0 = 0.08 + i * 0.2
    tokens7.append(E("Node", {"name": f"S7 hop {i}", "id": tid}, [
        E("FollowPathConstraint", {"targetId": LINE, "distance": d0, "orient": False, "name": "Ride line", "id": fp}),
        node(f"S7 hop bounce {i}", [text(f"S7 hop glyph {i}", 0, 0, [st], [run(sid, ch)], ox=0.5, oy=1)], id=bounce)]))
    # idle: travel along the sentence line while hopping (squash on landing)
    s.itrack(fp, "distance", [(0, d0, "lin"), (480, d0 + 0.2, "lin"), (481, d0, "hold")] if False else
             [(0, d0, "sine"), (240, d0 + 0.08, "sine"), (480, d0, "hold")])
    s.itrack(bounce, "y", sum([[(j * 40, -4, "out"), (j * 40 + 20, -40, "in")] for j in range(12)], []) + [(480, -4, "hold")])
    s.itrack(bounce, "scaleY", sum([[(j * 40, 0.8, "out"), (j * 40 + 8, 1.12, "sine"), (j * 40 + 34, 1, "in")]
                                    for j in range(12)], []) + [(480, 0.8, "hold")])
    pop(s, tid, 50 + i * 8, 24, "back")
s.parts.append(node("S7 sentence", tokens7 + [
    shape("S7 line", [smooth_path(line_pts, closed=False)],
          [E("Stroke", {"thickness": 9, "cap": "round", "join": "round", "name": "Line"},
             [solid(WP), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Draw",
                                        "id": LINE_TRIM})])], id=LINE),
    shape("S7 line shadow", [smooth_path(line_pts, closed=False)], [stroke(PD, 9)], x=3, y=6),
], id=nid()))
s.track(LINE_TRIM, "end", [(0, 0, "hold"), (8, 0, "io"), (70, 1, "hold")])
s.idle_dur = 480

# ---------- 8. Voice notes ---------------------------------------------------
s = Scene(8, D)
hid, hx, hc = hero_number("S8 hero", "voiceNotes", 24, 96, 342, 150, WP, align="center")
s.parts.append(hx)
s.hero = hid
rise(s, hid, 14, base_y=96, dy=30, dur=20)
count(s)
ids8 = copy_block(s, 24, 0, 8, unit_y=262, head_y=628, sup_y=706, head_color=WP, sup_color=LL, align="center")
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
    ph = (i * 7) % 5
    for j in range(6):
        seq.append((j * 40 + 20, 0.45 + 0.1 * ((i + j) % 4), "sine"))
        seq.append((j * 40 + 40, 1, "sine"))
    seq[-1] = (240, 1, "hold")
    s.itrack(b, "scaleY", seq)
SPEECH = nid()
SPEECH_TRIM = nid()
SPEECH_FILL = nid()
speech = node("S8 speech shape", [
    shape("S8 speech outline", [smooth_path(bubble_pts(1.32))],
          [E("Stroke", {"thickness": 9, "cap": "round", "join": "round", "name": "Outline"},
             [solid(L), E("TrimPath", {"start": 0, "end": 1, "modeValue": "sequential", "name": "Draw",
                                       "id": SPEECH_TRIM})])]),
    shape("S8 speech fill", [smooth_path(bubble_pts(1.32))], [fill("33C7B7F2")], id=SPEECH_FILL),
], id=SPEECH, x=195, y=436)
s.parts.append(node("S8 voice", bar_kids, id=(VOICE := nid()), x=195, y=440))
s.parts.append(speech)
s.track(SPEECH_TRIM, "end", [(0, 0, "hold"), (50, 0, "io"), (100, 1, "hold")])
s.track(SPEECH_FILL, "opacity", [(0, 0, "hold"), (80, 0, "out"), (110, 1, "hold")])
s.track(SPEECH, "scaleX", [(0, 0.6, "hold"), (50, 0.6, "back"), (100, 1, "hold")])
s.track(SPEECH, "scaleY", [(0, 0.6, "hold"), (50, 0.6, "back"), (100, 1, "hold")])
s.itrack(SPEECH, "rotation", [(0, 0, "sine"), (120, 0.04, "sine"), (240, 0, "hold")])

# ---------- 9. Persona -------------------------------------------------------
s = Scene(9, L)
BG9 = nid()
p9 = {}
p9["label"], p9["label_c"], tl_ = flow_text("S9 label", 342, "personaLabel", font="body", size=15, color=D, wght=600)
rise(s, p9["label"], 70, base_y=0, dy=10)
p9["title"], p9["title_c"], tt_ = flow_text("S9 title", 342, "personaName", size=48, color=D, wght=800, lh=48, wdth=86)
p9["desc"], p9["desc_c"], td_ = flow_text("S9 description", 342, "personaDescription", font="body", size=20,
                                       color=D, wght=600, lh=26)
s.parts.append(column("S9 copy", 24, 98, 342, [tl_, tt_, td_], gap=8)[1])
rise(s, p9["desc"], 104, base_y=0, dy=14)
TITLE_RANGE = nid()
# title letters reveal via modifier (kinetic)
s.parts = [p.replace(f'id="{p9["title"]}">', f'id="{p9["title"]}">', 1) for p in s.parts]
s.track(p9["title"], "opacity", [(0, 0, "hold"), (82, 0, "lin"), (86, 1, "hold")])
s.track(p9["title"], "y", [(0, 26, "hold"), (82, 26, "back"), (110, 0, "hold")])
s.motifA = (195, 520, 0.001, 0.001, 0, 0)
s.motifB = (195, 520, 0.001, 0.001, 0, 0)
EMB = []  # per persona: (root id, reveal tracks, idle tracks)


def emblem0(scale=1.0):
    ids_a, ids_b = {}, {}
    a = motif_bubble("E0 bubble A", P, PD, False, 0.78 * scale, ids=ids_a)
    b = motif_bubble("E0 bubble B", L, LD, True, 0.74 * scale, ids=ids_b)
    stars = []
    for i, (x, y, sz) in enumerate([(-10, -150, 30), (120, -110, 22), (-130, -96, 18), (8, 112, 16)]):
        stars.append(shape(f"E0 star {i}", [E("Star", {"width": sz * scale, "height": sz * scale, "points": 4,
                                                       "innerRadius": 0.35, "name": "Path"})], [fill(Y if i % 2 == 0 else D)],
                           id=nid(), x=x * scale, y=y * scale))
    marks_id = nid()
    sid, st = disp(90 * scale, D, 800)
    marks = text("E0 speech marks", 0, -40 * scale, [st], [run(sid, "“ ”")], ox=0.5, oy=0.5, id=marks_id)
    return {"a": ids_a, "b": ids_b, "stars": [x.split('id="')[-1].split('"')[0] for x in []], "marks": marks_id,
            "xml": [marks] + stars + [a, b], "star_xml": stars}


def find_ids(xml_list, prefix):
    import re
    out = []
    for x in xml_list:
        m = re.search(r'name="' + prefix + r'[^"]*" id="([0-9:]+)"', x)
        if m:
            out.append(m.group(1))
    return out


def build_emblems(scale=1.0, tag="E"):
    """Four persona emblems with distinct silhouettes. Returns list of dict(root, reveal(anim), idle(anim), xml)."""
    out = []
    # 0 Conversation Starter: welcoming speech marks between two greeting faces
    ia, ib = {}, {}
    a = motif_bubble(f"{tag}0 bubble A", P, PD, False, 0.78 * scale, ids=ia)
    b = motif_bubble(f"{tag}0 bubble B", L, LD, True, 0.74 * scale, ids=ib)
    stars = []
    star_ids = []
    for i, (x, y, sz, col) in enumerate([(-10, -150, 34, Y), (126, -108, 24, D), (-132, -96, 20, D), (6, 118, 18, Y)]):
        si = nid()
        star_ids.append(si)
        stars.append(shape(f"{tag}0 star {i}", [E("Star", {"width": sz * scale, "height": sz * scale, "points": 4,
                                                           "innerRadius": 0.32, "name": "Path"})], [fill(col)],
                           id=si, x=x * scale, y=y * scale))
    marks = nid()
    sid, st = disp(96 * scale, D, 800)
    root = nid()
    xml = node(f"{tag}0 conversation starter", [text(f"{tag}0 marks", 0, -36 * scale, [st], [run(sid, "“ ”")],
                                                     ox=0.5, oy=0.5, id=marks)] + stars + [a, b], id=root)
    rev, idle = [], []
    rev += [(ia["root"], "x", [(0, -300 * scale, "hold"), (8, -300 * scale, "back"), (40, -78 * scale, "hold")]),
            (ia["root"], "y", [(0, 40 * scale, "hold")]),
            (ia["root"], "rotation", [(0, -0.6, "hold"), (8, -0.6, "back"), (40, 0.12, "hold")]),
            (ib["root"], "x", [(0, 300 * scale, "hold"), (14, 300 * scale, "back"), (46, 80 * scale, "hold")]),
            (ib["root"], "y", [(0, 52 * scale, "hold")]),
            (ib["root"], "rotation", [(0, 0.6, "hold"), (14, 0.6, "back"), (46, -0.12, "hold")]),
            (marks, "scaleX", [(0, 0, "hold"), (40, 0, "el"), (80, 1, "hold")]),
            (marks, "scaleY", [(0, 0, "hold"), (40, 0, "el"), (80, 1, "hold")])]
    for i, si in enumerate(star_ids):
        rev += [(si, "scaleX", [(0, 0, "hold"), (50 + i * 6, 0, "back2"), (70 + i * 6, 1, "hold")]),
                (si, "scaleY", [(0, 0, "hold"), (50 + i * 6, 0, "back2"), (70 + i * 6, 1, "hold")])]
        idle.append((si, "rotation", [(0, 0, "sine"), (60 + i * 20, 0.5, "sine"), (240, 0, "hold")]))
    idle += [(ia["bob"], "rotation", [(0, 0, "sine"), (60, 0.08, "sine"), (120, 0, "sine"), (240, 0, "hold")]),
             (ib["bob"], "rotation", [(0, 0, "hold"), (120, 0, "sine"), (180, -0.08, "sine"), (240, 0, "hold")]),
             (ia["mouth"], "scaleY", [(0, 1, "sine"), (30, 0.55, "sine"), (60, 1, "hold"), (240, 1, "hold")]),
             (ib["mouth"], "scaleY", [(0, 1, "hold"), (120, 1, "sine"), (150, 0.55, "sine"), (180, 1, "hold"), (240, 1, "hold")])]
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 240})

    # 1 Phrase Collector: a quotation-mark archive (stacked index cards)
    root = nid()
    cards, rev, idle = [], [], []
    for i, (col, ink) in enumerate([(WP, D), (Y, D), (P, WP), (L, D)]):
        cid_, gid = nid(), nid()
        sid, st = disp(84 * scale, ink, 800)
        cards.append(node(f"{tag}1 card {i}", [
            text(f"{tag}1 card mark {i}", 0, 14 * scale, [st], [run(sid, "”")], ox=0.5, oy=0.5),
            shape(f"{tag}1 card tab {i}", [rect(56 * scale, 18 * scale, 7 * scale)], [fill(col)], x=-44 * scale + i * 30 * scale, y=-70 * scale),
            shape(f"{tag}1 card face {i}", [rect(200 * scale, 130 * scale, 22 * scale)], [fill(col)]),
            shape(f"{tag}1 card depth {i}", [rect(200 * scale, 130 * scale, 22 * scale)], [fill("40000000")], x=4 * scale, y=8 * scale),
        ], id=cid_, y=(i * 34 - 60) * scale, rot=(-0.12 + i * 0.08)))
        f0 = 4 + (3 - i) * 9
        ry = (i * 34 - 60) * scale
        rev += [(cid_, "y", [(0, -420 * scale, "hold"), (f0, -420 * scale, "back"), (f0 + 26, ry, "hold")]),
                (cid_, "rotation", [(0, 0.8 - i * 0.3, "hold"), (f0, 0.8 - i * 0.3, "out"), (f0 + 30, -0.12 + i * 0.08, "hold")])]
        idle.append((cid_, "y", [(0, ry, "sine"), (60 + i * 15, ry - 6 * (4 - i) * scale, "sine"), (240, ry, "hold")]))
    xml = node(f"{tag}1 phrase collector", cards[::-1], id=root)
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 240})

    # 2 Careful Listener: an open parenthesis that becomes an ear, with ripples flowing in
    root, ear, inner, rip = nid(), nid(), nid(), []
    rev, idle = [], []
    paren = [(26, -150, "c", 12), (-42, -92), (-66, 0), (-42, 92), (26, 150, "c", 12), (4, 150, "c", 8), (-22, 90),
             (-34, 0), (-22, -90), (4, -150, "c", 8)]
    swirl = [(18, -60), (-14, -30), (-10, 10), (14, 26), (6, 52)]
    kids = []
    for i in range(3):
        ri = nid()
        rip.append(ri)
        kids.append(shape(f"{tag}2 ripple {i}", [smooth_path([(0, -90 * scale), (40 * scale, 0), (0, 90 * scale)], closed=False)],
                          [stroke(D if i != 1 else P, 9 * scale)], id=ri, x=(84 + i * 38) * scale))
    xml = node(f"{tag}2 careful listener", kids + [
        node(f"{tag}2 ear", [
            shape(f"{tag}2 swirl", [smooth_path([(x * scale, y * scale) for x, y in swirl], closed=False)],
                  [stroke(P, 12 * scale)], id=inner, x=-6 * scale),
            shape(f"{tag}2 paren", [smooth_path([(34 * scale, -140 * scale), (-34 * scale, -76 * scale), (-52 * scale, 0),
                                                (-34 * scale, 76 * scale), (34 * scale, 140 * scale)], closed=False)],
                  [stroke(D, 46 * scale)]),
            shape(f"{tag}2 paren depth", [smooth_path([(34 * scale, -140 * scale), (-34 * scale, -76 * scale), (-52 * scale, 0),
                                                      (-34 * scale, 76 * scale), (34 * scale, 140 * scale)], closed=False)],
                  [stroke(DL, 46 * scale)], x=7 * scale, y=8 * scale),
        ], id=ear, x=-40 * scale)], id=root)
    rev += [(ear, "rotation", [(0, -1.4, "hold"), (4, -1.4, "back"), (40, 0, "hold")]),
            (ear, "scaleX", [(0, 0.2, "hold"), (4, 0.2, "el"), (56, 1, "hold")]),
            (ear, "scaleY", [(0, 0.2, "hold"), (4, 0.2, "el"), (56, 1, "hold")]),
            (inner, "opacity", [(0, 0, "hold"), (36, 0, "lin"), (46, 1, "hold")])]
    for i, ri in enumerate(rip):
        rev.append((ri, "opacity", [(0, 0, "hold"), (40 + i * 8, 0, "lin"), (50 + i * 8, 1, "hold")]))
        # sound arriving: each ripple swells and dims in turn (seamless 180-frame loop)
        ph = i * 30
        idle += [(ri, "scaleY", [(0, 1, "sine"), (ph + 30, 1.18, "sine"), (ph + 90, 0.9, "sine"), (180, 1, "hold")]),
                 (ri, "opacity", [(0, 1, "sine"), (ph + 30, 0.45, "sine"), (ph + 90, 1, "hold"), (180, 1, "hold")])]
    idle.append((inner, "rotation", [(0, 0, "sine"), (90, 0.12, "sine"), (180, 0, "hold")]))
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 180})

    # 3 Brave Improviser: an elastic exclamation mark
    root, bar, dot, squash = nid(), nid(), nid(), nid()
    rev, idle = [], []
    bursts = []
    kids = []
    for i in range(6):
        ang = -math.pi / 2 + (i - 2.5) * 0.5
        bi = nid()
        bursts.append(bi)
        kids.append(shape(f"{tag}3 burst {i}", [rect(8 * scale, 34 * scale, 4 * scale)], [fill(P if i % 2 else D)], id=bi,
                          x=math.cos(ang) * 150 * scale, y=math.sin(ang) * 150 * scale - 20 * scale, rot=ang + math.pi / 2))
    xml = node(f"{tag}3 brave improviser", kids + [node(f"{tag}3 bang", [
        node(f"{tag}3 squash", [
            shape(f"{tag}3 bar", [rect(74 * scale, 200 * scale, 37 * scale)], [fill(P)], id=bar, y=-70 * scale),
            shape(f"{tag}3 bar glint", [rect(14 * scale, 120 * scale, 7 * scale)], [fill("66FFFFFF")], x=-18 * scale, y=-84 * scale),
            shape(f"{tag}3 bar depth", [rect(74 * scale, 200 * scale, 37 * scale)], [fill(PD)], x=7 * scale, y=-62 * scale),
        ], id=squash, y=40 * scale),
        shape(f"{tag}3 dot", [ellipse(76 * scale, 76 * scale)], [fill(D)], id=dot, y=118 * scale),
    ])], id=root)
    rev += [(squash, "y", [(0, -500 * scale, "hold"), (4, -500 * scale, "in"), (24, 40 * scale, "hold")]),
            (squash, "scaleY", [(0, 1.3, "hold"), (24, 1.3, "lin"), (28, 0.62, "el"), (70, 1, "hold")]),
            (squash, "scaleX", [(0, 0.8, "hold"), (24, 0.8, "lin"), (28, 1.32, "el"), (70, 1, "hold")]),
            (dot, "scaleX", [(0, 0, "hold"), (30, 0, "back2"), (46, 1, "hold")]),
            (dot, "scaleY", [(0, 0, "hold"), (30, 0, "back2"), (46, 1, "hold")])]
    for i, bi in enumerate(bursts):
        rev += [(bi, "scaleY", [(0, 0, "hold"), (28 + i * 2, 0, "back2"), (44 + i * 2, 1, "hold")])]
        idle.append((bi, "scaleY", [(0, 1, "sine"), (40, 0.4, "sine"), (80, 1, "hold"), (160, 1, "hold")]))
    idle += [(squash, "y", [(0, 40 * scale, "out"), (28, -30 * scale, "in"), (56, 40 * scale, "hold"), (160, 40 * scale, "hold")]),
             (squash, "scaleY", [(0, 1, "lin"), (56, 1, "lin"), (60, 0.8, "el"), (110, 1, "hold"), (160, 1, "hold")]),
             (squash, "scaleX", [(0, 1, "lin"), (56, 1, "lin"), (60, 1.15, "el"), (110, 1, "hold"), (160, 1, "hold")])]
    out.append({"root": root, "xml": xml, "rev": rev, "idle": idle, "dur": 160})
    return out


EMB = build_emblems(1.0, "E")
halo = nid()
s.parts.append(node("S9 emblem stage", [e["xml"] for e in EMB] + [
    shape("S9 halo", [ellipse(330, 120)], [stroke("88FFFFFF", 3)], id=halo, y=150),
    shape("S9 halo 2", [ellipse(250, 80)], [fill("44FFFFFF")], y=160),
], id=(EMB_STAGE := nid()), x=195, y=500))
pop(s, halo, 70, 30, "out")
s.idle_dur = 240

# ---------- 10. Summary ------------------------------------------------------
s = Scene(10, D)
sum_h = {}
sum_h["head"], sum_h["head_c"], ta_ = flow_text("S10 headline", 342, "summaryHeadline", size=30, color=WP, wght=800, lh=32, wdth=92)
sum_h["sup"], _c, tb_ = flow_text("S10 support", 342, "summarySupport", font="body", size=15, color=LL, wght=500, lh=20)
sum_h["ehead"], _c, tc_ = flow_text("S10 empty headline", 342, "emptyHeadline", size=30, color=WP, wght=800, lh=32, wdth=92)
sum_h["esup"], _c, td_ = flow_text("S10 empty support", 342, "emptySupport", font="body", size=15, color=LL, wght=500, lh=20)
sum_h["col"], xa = column("S10 copy", 24, 96, 342, [ta_, tb_], gap=8)
sum_h["ecol"], xb = column("S10 new-user copy", 24, 96, 342, [tc_, td_], gap=8, op=0)
s.parts += [xa, xb]
rise(s, sum_h["col"], 20, base_y=0, fade=False)
CARD = nid()
CARD_SM = nid()
CARD_AB = nid()
s.parts.insert(0, E("NestedArtboard", {"artboardId": CARD_AB, "x": 24, "y": 200, "name": "S10 share card", "id": CARD},
                    [E("NestedStateMachine", {"animationId": CARD_SM, "name": "Card machine"})]))
s.track(CARD, "y", [(0, 900, "hold"), (8, 900, "back"), (44, 200, "hold")])
s.track(CARD, "rotation", [(0, 0.3, "hold"), (8, 0.3, "out"), (50, 0, "hold")])

# ================================================================ CHROME
CH = {}
chrome = []
# top: wordmark + year
CH["wm_c"] = nid()
CH["dot_c"] = nid()
sid, st = disp(22, D, 800, wdth=80, cid=CH["wm_c"])
chrome.append(node("Chrome wordmark", [
    shape("Chrome wordmark bubble", [smooth_path(bubble_pts(0.055))], [fill(P, cid=CH["dot_c"])], x=91, y=16),
    text("Chrome wordmark text", 0, 0, [st], [run(sid, "parlance")])], x=24, y=30))
CH["year_c"] = nid()
sid, st = disp(15, D, 700, cid=CH["year_c"])
chrome.append(text("Chrome year", 366, 34, [st], [run(sid, "2026", [bind(V("year"), 268, C_STR0)])], ox=1))
# progress segments: a flex row; hidden scenes are display:none so exactly the visible count renders
SEG = {}
seg_kids = []
for k in range(1, 11):
    SEG[k] = {"lc": nid(), "style": nid(), "fill": nid(), "fstyle": nid(), "track_c": nid(), "fill_c": nid()}
    seg_kids.append(E("LayoutComponent", {"width": 10, "height": 4, "styleId": SEG[k]["style"], "name": f"Segment {k}",
                                          "id": SEG[k]["lc"]}, [
        E("LayoutComponentStyle", {"layoutWidthScaleType": "fill", "cornerRadiusTL": 2, "name": f"Segment {k} style",
                                   "id": SEG[k]["style"]}),
        E("LayoutComponent", {"width": 100, "height": 4, "styleId": SEG[k]["fstyle"], "name": f"Segment {k} fill",
                              "id": SEG[k]["fill"]}, [
            E("LayoutComponentStyle", {"positionTypeValue": "absolute", "widthUnitsValue": "percent",
                                       "layoutHeightScaleType": "fill", "cornerRadiusTL": 2,
                                       "name": f"Segment {k} fill style", "id": SEG[k]["fstyle"]}),
            bind(V("currentScreen"), 16, C_SEG[k]),
            fill(P, cid=SEG[k]["fill_c"])]),
        fill("333D2456", cid=SEG[k]["track_c"])]))
chrome.append(E("LayoutComponent", {"width": 342, "height": 4, "styleId": (PSTYLE := nid()),
                                    "name": "Progress", "id": (PROG := nid())},
                [E("LayoutComponentStyle", {"flexDirectionValue": "row", "gapHorizontal": 4,
                                            "gapHorizontalUnitsValue": "points", "positionTypeValue": "absolute",
                                            "positionLeft": 24, "positionTop": 66, "positionLeftUnitsValue": "points",
                                            "positionTopUnitsValue": "points", "name": "Progress style", "id": PSTYLE})]
                + seg_kids))

# bottom controls (inside a focus scope that also hosts the keyboard listeners)
BTN = {}


def button(key, idx, x, y, w, h, label_prop=None, icon=None, label_size=17):
    b = {"id": nid(), "bg_c": nid(), "ink_c": nid(), "ring": nid(), "x": x, "w": w, "focus": nid()}
    kids = [E("FocusData", {"name": "Focus", "id": b["focus"]}),
            E("SemanticData", {"role": "button", "label": PROPS[label_prop][2], "name": "Semantics"},
              [bind(V(label_prop), 983)])]
    if label_prop and icon is None:
        sid, st = disp(label_size, WP, 700, cid=b["ink_c"])
        kids.append(text(f"{key} label", -w / 2 + 22, -12, [st], [run(sid, PROPS[label_prop][2], [bind(V(label_prop), 268)])],
                         w=w - 64, h=26, sizing="fixed", overflow="fitFontSize", wrap="noWrap", align="center"))
        kids.append(shape(f"{key} arrow", [smooth_path([(-8, -7), (0, 0), (-8, 7)], closed=False)], [stroke(WP, 2.6, cid=b["ink_c2"]) if False else stroke(WP, 2.6, cid=(b.setdefault("ink2_c", nid())))],
                          x=w / 2 - 26))
        kids.append(shape(f"{key} arrow stem", [rect(16, 2.6, 1.3)], [fill(WP, cid=b.setdefault("ink3_c", nid()))], x=w / 2 - 33))
    elif icon:
        kids += icon(b)
    kids.append(shape(f"{key} focus ring", [rect(w + 10, h + 10, (h + 10) / 2)], [stroke(P, 3)], id=b["ring"],
                      binds=[bind(V("_focusIndex"), 18, C_FOCUS[idx])]))
    kids.append(shape(f"{key} surface", [rect(w, h, h / 2)], [fill(D, cid=b["bg_c"])]))
    kids += [rect(w, h, h / 2), fill(CLEAR)]  # hit geometry of the button itself
    xml = E("Shape", {"x": x, "y": y, "isTargetOpaque": True, "name": key, "id": b["id"]}, kids)
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
    button("Pause", 2, 112, 790, 52, 52, "pauseLabel", icon=icon_pause),
    button("Continue", 3, 260, 790, 212, 52, "continueLabel"),
    button("Replay", 4, -400, 790, 128, 52, "replayLabel", label_size=16),
    button("Share", 5, -400, 790, 140, 52, "shareLabel", label_size=16),
]
KEYHOST = nid()
chrome.append(E("Node", {"name": "Controls", "id": KEYHOST}, [E("FocusData", {"canFocus": False, "name": "Focus scope"})] + controls))

# navigation regions (transparent but hit-testable); declared after controls so buttons win
NAV_L, NAV_R = nid(), nid()
chrome.append(shape("Nav back region", [rect(130, 656, 0, 0, 0)], [fill(CLEAR)], id=NAV_L, x=0, y=96))
chrome.append(shape("Nav next region", [rect(260, 656, 0, 0, 0)], [fill(CLEAR)], id=NAV_R, x=130, y=96))
mouth_hit_xml = E("Shape", {"x": -500, "y": -500, "isTargetOpaque": True, "name": "Mouth hit (signature interaction)",
                            "id": MOUTH_HIT}, [rect(10, 10), fill(CLEAR)])

# global motif
mA = motif_bubble("Motif A", P, PD, False, 1.0, ids=MA)
mB = motif_bubble("Motif B", L, LD, True, 1.0, ids=MB, tongue=P)
# hidden drivers (two-way bound: their animated x writes the view model)
driver_xml = node("Hero reveal driver", [], id=DRIVER, x=1, binds=[bind(V("_heroReveal"), 13, None, twoWay=True)])
# aperture used by the signature transition (quote-shaped clip for scene 4)
APER = nid()
APER_CLIP = nid()
aperture = node("Quote aperture", [
    shape("Aperture bloom", [ellipse(100, 100)], [], id=(APER_BLOOM := nid()), sx=0.01, sy=0.01),
    shape("Aperture comma L", [smooth_path(comma_pts(1.0))], [], x=-50),
    shape("Aperture comma R", [smooth_path(comma_pts(1.0))], [], x=50),
], id=APER, x=195, y=440, sx=0.01, sy=0.01)

# clock component placement
CLOCK = nid()
CLOCK_AB = nid()
CLOCK_SM = nid()
clock_xml = E("NestedArtboard", {"artboardId": CLOCK_AB, "x": -100, "y": -100, "name": "Dwell clock", "id": CLOCK}, [
    bind(V("autoAdvanceSeconds"), 907, C_CLOCK),
    bind(V("isPaused"), 895),
    E("NestedStateMachine", {"animationId": CLOCK_SM, "name": "Clock machine"})])

# scene backgrounds + roots
scene_xml = []
for n in range(10, 0, -1):
    sc = SCENES[n]
    sc.bg_id = nid()
    sc.bg_c = nid()
    if n == 9:
        bgfill = fill(L, cid=sc.bg_c, binds=[bind(V("personaColor"), 37)])
    else:
        bgfill = fill(sc.bg, cid=sc.bg_c)
    kids = list(sc.parts) + [shape(f"S{n} background", [rect(W + 40, H + 40, 0, 0, 0)], [bgfill], id=sc.bg_id, x=-20, y=-20)]
    extra = {}
    clip = []
    if n == 4:
        clip = [E("ClippingShape", {"sourceId": APER, "isVisible": False, "name": "Quote aperture clip", "id": APER_CLIP})]
    scene_xml.append(E("Node", {"name": f"Scene {n}", "id": sc.root, "opacity": 1 if n == 1 else 0}, clip + kids))

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


def anim(name, dur, loop=None):
    a = Anim(name, dur, loop)
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


def scene4_clip_off(a, frame=0):
    a.hold(APER_CLIP, "isVisible", False, kind="b", frame=frame)


for n in range(1, 11):
    sc = SCENES[n]
    a_pose, b_pose = sc.motifA, sc.motifB

    # ---- In (generic: arrives from the persimmon cover pose) ----
    a = anim(f"{n:02d} In", 130)
    sc.anim_in = a
    hide_others(a, n)
    root_reset(a, sc)
    mouth_hit(a, sc)
    if n == 4:
        scene4_clip_off(a)
    if a_pose == OFF_A:
        motif_keys(a, MA, [(0, COVER_A, "antic"), (26, (-240, -260, 1.3, 2.6, -0.5, 0), "hold"), (27, OFF_A, "hold")])
    else:
        motif_keys(a, MA, [(0, COVER_A, "out"), (30, a_pose, "hold")])
    if b_pose == OFF_B:
        motif_keys(a, MB, [(0, OFF_B, "hold")])
    else:
        motif_keys(a, MB, [(0, OFF_B, "hold"), (16, (520, b_pose[1] + 60) + b_pose[2:5] + (1,), "back"), (44, b_pose, "hold")])
    apply_enter(a, sc)
    if n in (2,):
        pass

    # ---- Back-in (alternate: lilac cover retreats to the right, compressed rebuild) ----
    a = anim(f"{n:02d} Back In", 84)
    sc.anim_backin = a
    hide_others(a, n)
    root_reset(a, sc)
    mouth_hit(a, sc)
    if n == 4:
        scene4_clip_off(a)
    a.k(sc.root, "x", [(0, -60, "hold"), (6, -60, "out"), (40, 0, "hold")])
    motif_keys(a, MB, [(0, COVER_B, "antic"), (26, (640, 980, 1.6, 2.2, 0.6, 0), "hold"), (27, b_pose, "hold")])
    motif_keys(a, MA, [(0, a_pose, "hold")])
    apply_enter(a, sc, offset=0, scale=0.6)

    # ---- Settled (reduced motion: final values + short opacity fade, no movement) ----
    a = anim(f"{n:02d} Settled (reduced motion)", 14)
    sc.anim_rm = a
    hide_others(a, n)
    root_reset(a, sc)
    a.k(sc.root, "opacity", [(0, 0, "lin"), (12, 1, "hold")])
    mouth_hit(a, sc)
    if n == 4:
        scene4_clip_off(a)
    motif_keys(a, MA, [(0, a_pose, "hold")])
    motif_keys(a, MB, [(0, b_pose, "hold")])
    apply_final(a, sc)

    # ---- Out (generic: persimmon motif sweeps in, stretches and covers) ----
    a = anim(f"{n:02d} Out", 28)
    sc.anim_out = a
    motif_keys(a, MA, [(0, a_pose if a_pose != OFF_A else (470, 1010, 1.0, 1.0, 0.7, 1), "antic"),
                       (12, (300, 700, 2.0, 2.8, 0.45, 0.4), "in"), (28, COVER_A, "hold")])
    a.k(sc.root, "scaleX", [(0, 1, "in"), (28, 0.94, "hold")])
    a.k(sc.root, "scaleY", [(0, 1, "in"), (28, 0.94, "hold")])
    a.k(sc.root, "x", [(0, 0, "in"), (28, 12, "hold")])
    a.k(sc.root, "y", [(0, 0, "in"), (28, 26, "hold")])

    # ---- Out back (mirror: lilac motif sweeps in from the left) ----
    a = anim(f"{n:02d} Out Back", 30)
    sc.anim_outback = a
    motif_keys(a, MB, [(0, b_pose if b_pose != OFF_B else (-160, 200, 1.0, 1.0, -0.7, 1), "antic"),
                       (13, (90, 330, 2.0, 2.8, -0.45, 0.4), "in"), (30, COVER_B, "hold")])
    a.k(sc.root, "x", [(0, 0, "in"), (30, 40, "hold")])
    a.k(sc.root, "rotation", [(0, 0, "in"), (30, 0.04, "hold")])

    # ---- reduced-motion out: a short fade ----
    a = anim(f"{n:02d} Out (reduced motion)", 10)
    sc.anim_outrm = a
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
        a.k(MA["mouth"], "scaleY", [(0, 1, "sine"), (24, 0.6, "sine"), (48, 1, "hold"), (sc.idle_dur, 1, "hold")])
    if b_pose != OFF_B and n != 9:
        a.k(MB["bob"], "y", [(0, -6, "sine"), (sc.idle_dur / 2, 2, "sine"), (sc.idle_dur, -6, "hold")])
        half = sc.idle_dur / 2
        a.k(MB["mouth"], "scaleY", [(0, 1, "hold"), (half, 1, "sine"), (half + 24, 0.6, "sine"), (half + 48, 1, "hold"),
                                    (sc.idle_dur, 1, "hold")])

# ---- persona anticipation: the motif pair circles, winds up and collapses into the emblem ----
s9 = SCENES[9]
a = s9.anim_in
motif_keys(a, MA, [(0, COVER_A, "out"), (24, (112, 500, 0.62, 0.62, -0.2, 1), "sine"), (40, (195, 420, 0.58, 0.58, 0.3, 1), "sine"),
                   (54, (278, 500, 0.62, 0.62, 0.5, 1), "antic"), (68, (195, 520, 0.02, 0.02, 1.4, 0), "hold")])
motif_keys(a, MB, [(0, OFF_B, "hold"), (14, (560, 520, 0.6, 0.6, 0.4, 1), "out"), (28, (278, 500, 0.58, 0.58, 0.2, 1), "sine"),
                   (42, (195, 590, 0.56, 0.56, -0.3, 1), "sine"), (54, (112, 500, 0.6, 0.6, -0.5, 1), "antic"),
                   (68, (195, 520, 0.02, 0.02, -1.4, 0), "hold")])
a.k(MA["mouth"], "scaleY", [(0, 1, "sine"), (30, 0.5, "sine"), (44, 1.2, "sine"), (68, 1, "hold")])
a.k(MB["mouth"], "scaleY", [(0, 1, "sine"), (36, 1.25, "sine"), (50, 0.5, "sine"), (68, 1, "hold")])
burst9 = nid()

# ---- special continuity transitions ----------------------------------------
# 1 -> 2: the two speech forms are carried down into the conversation scene
s1, s2, s3, s4 = SCENES[1], SCENES[2], SCENES[3], SCENES[4]
a = anim("01 Out (carry motif to 2)", 40)
s1.anim_out_special = a
motif_keys(a, MA, [(0, s1.motifA, "antic"), (10, (s1.motifA[0] + 6, s1.motifA[1] - 30) + s1.motifA[2:], "io"), (40, s2.motifA, "hold")])
motif_keys(a, MB, [(0, s1.motifB, "antic"), (14, (s1.motifB[0] - 6, s1.motifB[1] - 24) + s1.motifB[2:], "io"), (40, s2.motifB, "hold")])
a.k(s1.root, "y", [(0, 0, "in"), (28, -60, "hold")])
a.k(s1.root, "opacity", [(0, 1, "in"), (28, 0, "hold")])
a = anim("02 Carry In (from 1)", 120)
s2.anim_carry = a
hide_others(a, 2)
root_reset(a, s2)
mouth_hit(a, s2)
motif_keys(a, MA, [(0, s2.motifA, "hold")])
motif_keys(a, MB, [(0, s2.motifB, "hold")])
a.k(MA["elastic"], "scaleY", [(0, 1, "lin"), (6, 0.82, "el"), (40, 1, "hold")])
a.k(MB["elastic"], "scaleY", [(0, 1, "lin"), (12, 0.82, "el"), (46, 1, "hold")])
apply_enter(a, s2)

# 2 -> 3: persimmon speech form flies centre-stage, its mouth becomes the elastic mouth
a = anim("02 Out (carry motif to 3)", 34)
s2.anim_out_special = a
motif_keys(a, MA, [(0, s2.motifA, "antic"), (34, (195, 470, 2.7, 2.7, 0, 1), "hold")])
motif_keys(a, MB, [(0, s2.motifB, "in"), (24, (560, 700, 1.0, 1.0, 0.6, 1), "hold")])
a.k(MA["mouth"], "scaleY", [(0, 1, "io"), (34, 1.9, "hold")])
a.k(MA["mouth"], "scaleX", [(0, 1, "io"), (34, 1.25, "hold")])
a.k(MA["eyes"], "opacity", [(0, 1, "lin"), (26, 0, "hold")])
a.k(s2.root, "opacity", [(0, 1, "in"), (26, 0, "hold")])
a = anim("03 Carry In (from 2)", 120)
s3.anim_carry = a
hide_others(a, 3)
root_reset(a, s3)
mouth_hit(a, s3)
motif_keys(a, MA, [(0, (195, 470, 2.7, 2.7, 0, 1), "in"), (18, (195, 486, 3.6, 3.2, 0, 0), "hold"), (19, OFF_A, "hold")])
a.k(MA["root"], "opacity", [(0, 1, "lin"), (18, 0, "hold"), (19, 1, "hold")])
a.k(MA["mouth"], "scaleY", [(0, 1.9, "hold"), (19, 1, "hold")])
a.k(MA["mouth"], "scaleX", [(0, 1.25, "hold"), (19, 1, "hold")])
a.k(MA["eyes"], "opacity", [(0, 0, "hold"), (19, 1, "hold")])
motif_keys(a, MB, [(0, OFF_B, "hold")])
apply_enter(a, s3)
a.k(MOUTH["outer"], "scaleX", [(0, 0.7, "hold"), (8, 0.7, "el2"), (50, 1, "hold")])
a.k(MOUTH["outer"], "scaleY", [(0, 0.7, "hold"), (8, 0.7, "el2"), (50, 1, "hold")])
for an in [x for x in ANIMS if x.name.endswith("In") or "Settled" in x.name or "Back In" in x.name
           or ("Carry In" in x.name and "from 2" not in x.name)]:
    if "Settled" in an.name:
        an.k(MA["root"], "opacity", [(0, 0, "lin"), (12, 1, "hold")])
        an.k(MB["root"], "opacity", [(0, 0, "lin"), (12, 1, "hold")])
    else:
        an.hold(MA["root"], "opacity", 1)
        an.hold(MB["root"], "opacity", 1)
    an.hold(MA["mouth"], "scaleX", 1)
    an.hold(MA["mouth"], "scaleY", 1)
    an.hold(MA["eyes"], "opacity", 1)

# 3 -> 4 SIGNATURE: the mouth elongates to fill the frame, then opens as a quotation mark onto scene 4
a = anim("03 Out (signature: mouth fills frame)", 36)
s3.anim_out_special = a
a.k(MOUTH["outer"], "scaleY", [(0, 1, "antic"), (36, 7.5, "hold")])
a.k(MOUTH["outer"], "scaleX", [(0, 1, "lin"), (8, 0.86, "in"), (36, 2.9, "hold")])
a.k(MOUTH["outer"], "y", [(0, 486, "in"), (36, 430, "hold")])
a.k(MOUTH["open"], "scaleY", [(0, 1, "in"), (36, 0.1, "hold")])
a.k(MOUTH["teeth"], "opacity", [(0, 1, "lin"), (14, 0, "hold")])
for key_ in ("unit", "head", "sup"):
    a.k(ids3[key_], "opacity", [(0, 1, "lin"), (12, 0, "hold")])
a.k(s3.hero, "opacity", [(0, 1, "lin"), (10, 0, "hold")])
a = anim("04 Carry In (signature aperture)", 130)
s4.anim_carry = a
a.hold(MA["root"], "opacity", 1)
a.hold(MB["root"], "opacity", 1)
hide_others(a, 4, keep=(3,))
a.k(SCENES[3].root, "opacity", [(0, 1, "hold"), (44, 0, "hold")])
root_reset(a, s4)
mouth_hit(a, s4)
motif_keys(a, MA, [(0, OFF_A, "hold")])
motif_keys(a, MB, [(0, OFF_B, "hold")])
a.k(APER_CLIP, "isVisible", [(0, True, "hold"), (44, False, "hold")], kind="b")
a.k(APER, "scaleX", [(0, 0.05, "hold"), (2, 0.05, "in"), (42, 9.5, "hold")])
a.k(APER, "scaleY", [(0, 0.05, "hold"), (2, 0.05, "in"), (42, 9.5, "hold")])
a.k(APER, "rotation", [(0, -0.5, "hold"), (2, -0.5, "out"), (42, 0, "hold")])
a.k(APER_BLOOM, "scaleX", [(0, 0.01, "hold"), (18, 0.01, "in"), (42, 2.4, "hold")])
a.k(APER_BLOOM, "scaleY", [(0, 0.01, "hold"), (18, 0.01, "in"), (42, 2.4, "hold")])
apply_enter(a, s4, offset=10)
# restore scene 3 parts that the signature out changed
for an in [s3.anim_in, s3.anim_backin, s3.anim_rm, s3.anim_carry]:
    an.hold(MOUTH["open"], "scaleY", 1) if (MOUTH["open"], "scaleY") not in [(o, p) for o, p, _, _ in s3.enter] else None
    an.hold(MOUTH["outer"], "y", 486)
    for key_ in ("unit", "head", "sup"):
        pass
    an.hold(s3.hero, "opacity", 1)
for an in [s2.anim_in, s2.anim_backin, s2.anim_rm, s2.anim_carry]:
    an.hold(MA["mouth"], "scaleX", 1)
# cover used when a carry transition's target scene is hidden
for n in (1, 2, 3):
    sc = SCENES[n]
    a = anim(f"{n:02d} Cover (skip)", 18)
    sc.anim_cover = a
    motif_keys(a, MA, [(0, (470, 1010, 1.0, 1.0, 0.7, 1), "in"), (18, COVER_A, "hold")])

# replay cover
REPLAY_COVER = anim("Replay cover", 30)
motif_keys(REPLAY_COVER, MA, [(0, (470, 1010, 1.0, 1.0, 0.7, 1), "antic"), (30, COVER_A, "hold")])
REPLAY_COVER.k(DRIVER, "x", [(0, 0, "hold")])
BOOT = anim("Boot", 1)
for an_ in (BOOT, REPLAY_COVER):
    an_.hold(MA["root"], "opacity", 1)
    an_.hold(MB["root"], "opacity", 1)
motif_keys(BOOT, MA, [(0, COVER_A, "hold")])
motif_keys(BOOT, MB, [(0, OFF_B, "hold")])
BOOT.hold(SCENES[1].root, "opacity", 1)
hide_others(BOOT, 1)

# mouth expressions (signature interaction, silent)
SQ3 = anim("Mouth tap: scene 3 elastic", 60)
SQ3.k(MOUTH["elastic"], "scaleX", [(0, 1, "out"), (6, 1.22, "el"), (60, 1, "hold")])
SQ3.k(MOUTH["elastic"], "scaleY", [(0, 1, "out"), (6, 0.72, "el"), (60, 1, "hold")])
SQ3.k(MOUTH["teeth"], "y", [(0, -50, "out"), (5, -40, "el"), (50, -50, "hold")])
SQ3.k(MOUTH["tongue"], "scaleX", [(0, 1, "out"), (8, 1.25, "el"), (60, 1, "hold")])
SQ2 = anim("Mouth tap: scene 2 laugh", 50)
SQ2.k(MA["elastic"], "scaleY", [(0, 1, "out"), (5, 0.78, "el"), (50, 1, "hold")])
SQ2.k(MA["elastic"], "scaleX", [(0, 1, "out"), (5, 1.16, "el"), (50, 1, "hold")])
SQ2.k(MA["mouth"], "scaleX", [(0, 1, "out"), (5, 1.3, "el"), (50, 1, "hold")])

# Persona animations
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
    PERS.append((rev, stat, idle))

# Theme animations (chrome colours per background)
THEMES = {}
for tname, ink, btn_bg, btn_ink, track, fillc in [("light", D, D, WP, "333D2456", P), ("dark", WP, L, D, "40FFF8EC", Y),
                                                   ("warm", DD, DD, WP, "402A1640", WP)]:
    a = anim(f"Theme {tname}", 1)
    a.k(CH["wm_c"], "colorValue", [(0, ink, "hold")], kind="c")
    a.k(CH["year_c"], "colorValue", [(0, ink, "hold")], kind="c")
    a.k(CH["dot_c"], "colorValue", [(0, P if tname != "warm" else WP, "hold")], kind="c")
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
CH_NORMAL = anim("Controls: story", 1)
CH_SUMMARY = anim("Controls: summary", 1)
for b in BTN.values():
    CH_NORMAL.hold(b["id"], "x", b["x"])
pos_sum = {"Previous": 50, "Pause": -400, "Continue": -400, "Replay": 158, "Share": 296}
for key_, x in pos_sum.items():
    CH_SUMMARY.hold(BTN[key_]["id"], "x", x)
    CH_SUMMARY.hold(BTN[key_]["focus"], "canFocus", x > 0, kind="b")
for key_, b in BTN.items():
    CH_NORMAL.hold(b["focus"], "canFocus", key_ not in ("Replay", "Share"), kind="b")
CH_NORMAL.hold(BTN["Replay"]["id"], "x", -400)
CH_NORMAL.hold(BTN["Share"]["id"], "x", -600)
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
        g += [trans(S[("In", n)], [RMF], dur=150, early=True), trans(S[("RMIn", n)], [RMT])]
    else:
        g += [trans(S[("In", n)], [cond(show(n), "b", True), RMF], dur=150, early=True), trans(S[("RMIn", n)], [cond(show(n), "b", True), RMT]),
              trans(nxt, [cond(show(n), "b", False)])]
    seq_states.append(astate(S[("G", n)], EMPTY.id, col(n), row["G"], g, caption=f"Gate {n} (forward)"))
    # back gate
    g = []
    if always:
        g += [trans(S[("BackIn", n)], [RMF], dur=150, early=True), trans(S[("RMIn", n)], [RMT])]
    else:
        g += [trans(S[("BackIn", n)], [cond(show(n), "b", True), RMF], dur=150, early=True), trans(S[("RMIn", n)], [cond(show(n), "b", True), RMT]),
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
    lis(tgt, "down", [write(V("_pointerDown"), "b", True), write(V("_pressSide"), "n", side)], f"Press {nm} region")
    lis(tgt, "up", [write(V("_pointerDown"), "b", False)], f"Release {nm} region")
    lis(tgt, "exit", [write(V("_pointerDown"), "b", False)], f"Leave {nm} region")
lis(BTN["Previous"]["id"], "click", [fire_trigger(V("goPrevious"))], "Previous button")
lis(BTN["Pause"]["id"], "click", [toggle(V("isPaused"), C_NOT)], "Pause button")
lis(BTN["Continue"]["id"], "click", [fire_trigger(V("goNext"))], "Continue button")
lis(BTN["Replay"]["id"], "click", [fire_trigger(V("requestReplay"))], "Replay button")
lis(BTN["Share"]["id"], "click", [E("ListenerFireEvent", {"eventId": EV["shareTapped"]})], "Share button")
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
    E("FocusActionTraversal", {"traversalKind": "next"})]))
listeners.append(E("StateMachineListener", {"targetId": KEYHOST, "name": "Key: Shift+Tab"}, [
    E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
      [E("KeyboardInput", {"keyType": "tab", "keyPhase": 1, "modifiers": 1})]),
    E("FocusActionTraversal", {"traversalKind": "previous"})]))
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
# Everything lives in one fixed 390x844 stage box so absolutely positioned copy columns resolve against the
# design frame, not against whatever size a host resizes the artboard to (hosts should use Fit.contain).
main_children.append(E("LayoutComponent", {"width": W, "height": H, "styleId": STAGE_STYLE, "name": "Stage", "id": STAGE}, [
    E("LayoutComponentStyle", {"positionTypeValue": "absolute", "positionLeft": 0, "positionTop": 0,
                               "positionLeftUnitsValue": "points", "positionTopUnitsValue": "points",
                               "name": "Stage style", "id": STAGE_STYLE}),
    node("Stage content", chrome + [mouth_hit_xml, clock_xml, driver_xml, aperture, mA, mB] + scene_xml)]))
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

# ================================================================ SHARE CARD COMPONENT
CARD_W, CARD_H = 342, 556
cd = {"style": nid()}
card_parts = []
card_anims = []
# top row
sid, st = disp(24, D, 800, wdth=80)
card_parts.append(node("Card wordmark", [
    shape("Card wordmark bubble", [smooth_path(bubble_pts(0.06))], [fill(P)], x=99, y=17),
    text("Card wordmark text", 0, 0, [st], [run(sid, "parlance")])], id=(CD_WM := nid()), x=24, y=22))
sid, st = disp(24, P, 800)
card_parts.append(text("Card year", 318, 24, [st], [run(sid, "2026", [bind(V("year"), 268, C_STR0)])], ox=1, id=(CD_YEAR := nid())))
CD_NAME, _c, t_ = bound_text("Card name", 24, 58, 294, "userName", font="body", size=14, color=DL, wght=600,
                             sizing="fixed", h=20, overflow="ellipsis", wrap="noWrap")
card_parts.append(t_)
# persona block
CEMB = build_emblems(0.42, "CE")
CD_EMB = nid()
card_parts.append(node("Card persona emblem", [e["xml"] for e in CEMB], id=CD_EMB, x=171, y=150))
CD_PT, CD_PT_C, t_ = bound_text("Card persona title", 24, 232, 294, "personaName", size=26, color=D, wght=800, lh=27,
                                align="center", wdth=86)
card_parts.append(t_)
CD_PD, _c, t_ = bound_text("Card persona description", 24, 264, 294, "personaDescription", font="body", size=13,
                           color=DL, wght=500, lh=17, align="center")
card_parts.append(t_)
# neutral motif (shown when persona hidden / new user)
CD_NEUTRAL = nid()
na, nb = {}, {}
card_parts.append(node("Card neutral motif", [motif_bubble("Card motif A", P, PD, False, 0.5, ids=na),
                                              motif_bubble("Card motif B", L, LD, True, 0.45, ids=nb)],
                       id=CD_NEUTRAL, x=171, y=160, op=0))
card_parts[-1] = card_parts[-1]  # positions of the two bubbles set below via x attributes
card_parts[-1] = card_parts[-1].replace(f'name="Card motif A" id="{na["root"]}"', f'name="Card motif A" id="{na["root"]}" x="-42"', 1) \
    if False else card_parts[-1]
CD_EMPTY_H, _c, t_ = bound_text("Card empty headline", 24, 300, 294, "emptyHeadline", size=26, color=D, wght=800, lh=28,
                                align="center", op=0)
card_parts.append(t_)
CD_EMPTY_S, _c, t_ = bound_text("Card empty support", 24, 370, 294, "emptySupport", font="body", size=15, color=DL,
                                wght=500, lh=20, align="center", op=0)
card_parts.append(t_)
# stat tiles (5 aggregates + a collectible motif tile)
TILES = []
tile_specs = [("conversations", "screen2Unit", P, D, 2), ("practiceMinutes", "screen3Unit", L, D, 3),
              ("phrasesSaved", "screen4Unit", Y, D, 4), ("topicsExplored", "screen5Unit", LL, D, 5),
              ("languagesPractised", "screen6Unit", D, WP, 6)]
for i, (pn, un, bgc, ink, scr) in enumerate(tile_specs):
    tx = 24 + (i % 2) * 151
    ty = 316 + (i // 2) * 76
    t_id = nid()
    hn, hx_, _ = hero_number(f"Card {pn}", pn, 14, 8, 115, 30, ink, counting=False, wdth=84)
    un_id, _c, ut = bound_text(f"Card {pn} label", 14, 44, 115, un, font="body", size=11, color=ink, wght=600,
                               sizing="fixed", h=16, overflow="ellipsis", wrap="noWrap")
    mask = nid()
    sid, st = disp(30, ink, 800)
    masked = text(f"Card {pn} private", 14, 8, [st], [run(sid, "—")], id=mask, op=0)
    TILES.append({"id": t_id, "num": hn, "mask": mask, "scr": scr})
    card_parts.append(node(f"Card tile {pn}", [hx_, masked, ut,
                                               shape("tile", [rect(143, 68, 18, 0, 0)], [fill(bgc)])], id=t_id, x=tx, y=ty))
CD_MTILE = nid()
mt_a, mt_b = {}, {}
card_parts.append(node("Card tile motif", [
    node("tile motif A", [motif_bubble("Tile motif A", P, PD, False, 0.22, ids=mt_a)], x=48, y=36),
    node("tile motif B", [motif_bubble("Tile motif B", L, LD, True, 0.2, ids=mt_b)], x=96, y=38),
    shape("tile", [rect(143, 68, 18, 0, 0)], [fill(WD)])], id=CD_MTILE, x=175, y=468))
CD_BG = nid()
card_parts.append(shape("Card blob", [smooth_path(bubble_pts(1.3, True))], [fill("55F6E97C")], x=250, y=150, rot=-0.3,
                        children=[E("ClippingShape", {"sourceId": CD_BG, "name": "Clip to card"})]))
card_parts.append(shape("Card face", [rect(CARD_W, CARD_H, 30, 0, 0)], [fill(WP)], id=CD_BG))
card_parts.append(shape("Card shadow", [rect(CARD_W, CARD_H, 30, 0, 0)], [fill("55000000", feather=(18, 0, 14))]))

# card animations
c_rest = Anim("Card settled", 1)
c_asm = Anim("Card assemble", 110)
c_empty_off = Anim("Card mode: stats", 1)
c_empty_on = Anim("Card mode: new user", 1)
c_name_on, c_name_off = Anim("Card name shown", 1), Anim("Card name hidden", 1)
c_sens_on, c_sens_off = Anim("Card minutes shown", 1), Anim("Card minutes private", 1)
c_pers_on, c_pers_off = Anim("Card persona shown", 1), Anim("Card persona hidden (neutral motif)", 1)
c_pick = [Anim(f"Card persona {k}", 1) for k in range(4)]
assemble_items = [(CD_WM, 0), (CD_YEAR, 4), (CD_EMB, 14), (CD_PT, 26), (CD_PD, 32)] + \
                 [(t["id"], 40 + i * 7) for i, t in enumerate(TILES)] + [(CD_MTILE, 76)]
for obj, f0 in assemble_items:
    c_asm.k(obj, "opacity", [(0, 0, "hold"), (f0, 0, "out"), (f0 + 14, 1, "hold")])
    c_rest.hold(obj, "opacity", 1)
for t in TILES + [{"id": CD_MTILE}]:
    oy = None
for i, t in enumerate(TILES):
    ty = 316 + (i // 2) * 76
    f0 = 40 + i * 7
    c_asm.k(t["id"], "y", [(0, ty - 40, "hold"), (f0, ty - 40, "back"), (f0 + 24, ty, "hold")])
    c_rest.hold(t["id"], "y", ty)
c_asm.k(CD_MTILE, "y", [(0, 430, "hold"), (76, 430, "back"), (100, 468, "hold")])
c_asm.k(CD_MTILE, "rotation", [(0, 0.5, "hold"), (76, 0.5, "back"), (100, 0, "hold")])
c_rest.hold(CD_MTILE, "y", 468)
c_rest.hold(CD_MTILE, "rotation", 0)
c_asm.k(CD_EMB, "scaleX", [(0, 1.8, "hold"), (14, 1.8, "el"), (60, 1, "hold")])
c_asm.k(CD_EMB, "scaleY", [(0, 1.8, "hold"), (14, 1.8, "el"), (60, 1, "hold")])
c_rest.hold(CD_EMB, "scaleX", 1)
c_rest.hold(CD_EMB, "scaleY", 1)
for an, empty in ((c_empty_off, False), (c_empty_on, True)):
    for t in TILES:
        an.hold(t["id"], "x", -900 if empty else (24 + (TILES.index(t) % 2) * 151))
    an.hold(CD_MTILE, "x", -900 if empty else 175)
    an.hold(CD_EMPTY_H, "opacity", 1 if empty else 0)
    an.hold(CD_EMPTY_S, "opacity", 1 if empty else 0)
for an, on in ((c_name_on, True), (c_name_off, False)):
    an.hold(CD_NAME, "opacity", 1 if on else 0)
mins = TILES[1]
for an, on in ((c_sens_on, True), (c_sens_off, False)):
    an.hold(mins["num"], "opacity", 1 if on else 0)
    an.hold(mins["mask"], "opacity", 0 if on else 1)
for an, on in ((c_pers_on, True), (c_pers_off, False)):
    an.hold(CD_EMB, "x", 171 if on else -900)
    an.hold(CD_PT, "x", 24 if on else -900)
    an.hold(CD_PD, "x", 24 if on else -900)
    an.hold(CD_NEUTRAL, "opacity", 0 if on else 1)
for k, an in enumerate(c_pick):
    for m, e in enumerate(CEMB):
        an.hold(e["root"], "opacity", 1 if m == k else 0)
        for obj, prop_, keys in e["rev"]:
            an.hold(obj, prop_, keys[-1][1])
CARD_ANIMS = [c_rest, c_asm, c_empty_off, c_empty_on, c_name_on, c_name_off, c_sens_on, c_sens_off, c_pers_on, c_pers_off] + c_pick


def two_state(name, a_anim, b_anim, cond_a, cond_b, cap_a, cap_b):
    ia, ib = nid(), nid()
    return E("StateMachineLayer", {"name": name, "id": nid()}, [
        E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
        E("EntryState", {"x": -200, "y": 0}, [trans(ia)]),
        astate(ia, a_anim.id, 0, 0, [trans(ib, cond_b)], caption=cap_a),
        astate(ib, b_anim.id, 250, 0, [trans(ia, cond_a)], caption=cap_b)])


asm_rest, asm_go = nid(), nid()
card_layers = [
    E("StateMachineLayer", {"name": "Assemble", "id": nid()}, [
        E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
        E("EntryState", {"x": -200, "y": 0}, [trans(asm_rest)]),
        astate(asm_rest, c_rest.id, 0, 0, [trans(asm_go, [cond(cs, "n", 10), RMF])], caption="Settled"),
        astate(asm_go, c_asm.id, 250, 0, [trans(asm_rest, [cond(cs, "n", 10, "notEqual")])], reset=True,
               caption="Assemble (summary)")]),
    two_state("Mode", c_empty_off, c_empty_on, [], [], "Stats", "New user"),
    two_state("Name privacy", c_name_off, c_name_on, [cond(V("shareIncludeName"), "b", False)],
              [cond(V("shareIncludeName"), "b", True)], "Name hidden", "Name shown"),
    two_state("Sensitive values", c_sens_off, c_sens_on, [cond(V("shareIncludeSensitiveValues"), "b", False)],
              [cond(V("shareIncludeSensitiveValues"), "b", True)], "Minutes private", "Minutes shown"),
    two_state("Persona visibility", c_pers_on, c_pers_off, [cond(show(9), "b", True)], [cond(show(9), "b", False)],
              "Persona shown", "Neutral motif"),
]
# Mode layer conditions (all metric scenes hidden -> new user)
card_layers[1] = E("StateMachineLayer", {"name": "Mode", "id": nid()}, [
    E("AnyState", {"x": -200, "y": -200}), E("ExitState", {"x": -200, "y": -320}),
    E("EntryState", {"x": -200, "y": 0}, [trans((m_a := nid()))]),
    astate(m_a, c_empty_off.id, 0, 0, [trans((m_b := nid()), all_hidden)], caption="Stats"),
    astate(m_b, c_empty_on.id, 250, 0, [trans(m_a, [cond(show(k), "b", True)]) for k in range(2, 9)], caption="New user")])
pick_states, pick_any = [], []
for k, an in enumerate(c_pick):
    sid_ = nid()
    pick_states.append(astate(sid_, an.id, k * 250, 0, caption=f"Persona {k}"))
    for rg in idx_ranges(k):
        pick_any.append(trans(sid_, rg))
card_layers.append(E("StateMachineLayer", {"name": "Persona pick", "id": nid()}, [
    E("AnyState", {"x": -200, "y": -200}, pick_any), E("ExitState", {"x": -200, "y": -320}),
    E("EntryState", {"x": -200, "y": 0}, [trans(pick_states and pick_states[0].split('id="')[-1].split('"')[0])])] + pick_states))
card_ab = E("Artboard", {"isComponent": True, "defaultStateMachineId": CARD_SM, "viewModelId": VM, "viewModelInstanceId": "0:95",
                         "styleId": cd["style"], "width": CARD_W, "height": CARD_H, "x": 460, "y": 100,
                         "name": "Share Card", "id": CARD_AB},
               [E("LayoutComponentStyle", {"name": "Card style", "id": cd["style"]})] + card_parts +
               [E("StateMachine", {"name": "Card", "id": CARD_SM}, card_layers)] + [a.xml() for a in CARD_ANIMS])

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
              E("ComponentAsset", {"artboardId": CARD_AB, "name": "Share Card"})]


def doc(children):
    return '<Rive version="1" kind="fragment">\n' + "\n".join(children) + "\n</Rive>\n"


open(os.path.join(ROOT, "scene.rml"), "w").write(doc([main_xml]))
open(os.path.join(ROOT, "components.rml"), "w").write(doc([clock_ab, card_ab] + components))
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
                wrap_ok = prop_ == "rotation" and abs(abs(v1 - v0) - 2 * math.pi) < 1e-3
                if abs(v0 - v1) > 1e-6 and not wrap_ok:
                    print(f"SEAM WARNING {an.name}: {obj}.{prop_} {v0} -> {v1}")
                if ks[-1][0] > an.dur:
                    print(f"KEY PAST END {an.name}: {obj}.{prop_} frame {ks[-1][0]} > {an.dur}")
