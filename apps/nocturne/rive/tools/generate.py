#!/usr/bin/env python3
"""Generates the Nocturne recap RML under ../rml/.

Run:  python3 tools/generate.py      (from apps/nocturne/rive)

The RML it writes is the editable source of truth for the build; this script
exists so that the large, regular parts of the file (ten scene state machines,
visibility-aware navigation transitions, keyframe completion) stay consistent.
"""
import math
import os
import random

from rml import *  # noqa: F401,F403
import rml

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "rml")

# ---------------------------------------------------------------- palette
MID = "081526"
MID_DEEP = "050D18"
MID_UP = "0E2240"
ICE = "BCE4E8"
BLUE = "608BFF"
AMBER = "F7BE62"
WHITE = "F4FAFB"

W, H = 390, 844
FPS = 60

# ---------------------------------------------------------------- view model
VMID = nid()
vm = VM("UserRecap", VMID)
rml.VMREF[0] = vm

FIXTURE = {
    "userName": "Alex", "year": 2026, "periodLabel": "January 1–December 31, 2026", "locale": "en-GB",
    "observationNights": 47, "objectsLogged": 128, "observationHours": 93, "constellationsLogged": 31,
    "meteorSightings": 64, "moonSessions": 18, "sketchesMade": 22, "personaIndex": 0,
    "personaName": "Deep Sky Dreamer", "personaDescription": "Wonder beyond the familiar.",
    "personaColor": "BCE4E8", "autoAdvanceSeconds": 7, "autoAdvanceEnabled": True, "isPaused": False,
    "reducedMotion": False, "soundEnabled": False, "currentScreen": 1, "screenProgress": 0,
    "shareIncludeName": False, "shareIncludeSensitiveValues": False, "continueLabel": "Continue",
    "previousLabel": "Previous", "pauseLabel": "Pause", "playLabel": "Play", "shareLabel": "Share",
    "replayLabel": "Replay", "introHeadline": "Your 2026 on Nocturne", "introSupport": "A year, uniquely yours.",
    "summaryHeadline": "A little year. A lot of you.", "summarySupport": "Take a piece of your year with you.",
    "emptyHeadline": "Every story starts somewhere.", "emptySupport": "Your next chapter is waiting.",
    "personaLabel": "Your personal style",
    **{f"showScreen{i}": True for i in range(1, 11)},
    "screen2Headline": "You looked up.", "screen2Support": "And found a little more wonder.", "screen2Unit": "nights outside",
    "screen3Headline": "A sky full of discoveries.", "screen3Support": "Your observation journal kept expanding.", "screen3Unit": "objects logged",
    "screen4Headline": "Time under the stars.", "screen4Support": "A different kind of screen time.", "screen4Unit": "hours observing",
    "screen5Headline": "Patterns you came to know.", "screen5Support": "A personal atlas, night by night.", "screen5Unit": "constellations logged",
    "screen6Headline": "Gone in a bright moment.", "screen6Support": "You were there to notice.", "screen6Unit": "meteors spotted",
    "screen7Headline": "An old friend, new details.", "screen7Support": "You returned to the moon.", "screen7Unit": "lunar sessions",
    "screen8Headline": "You kept a piece of the night.", "screen8Support": "Observations became your own marks.", "screen8Unit": "sky sketches",
}
# Adapter / file-owned additions (documented in README "Binding contract").
ADDITIONS = {
    "navNext": "trigger", "navPrevious": "trigger", "navReplay": "trigger",
    "navDirection": 1, "isHolding": False, "pointerDown": False, "pressSide": 0,
    "recapFinishedFired": False, "hasStats": True, "personaSlot": 0, "motifPose": 0,
    "focusedControl": 0, "captureMode": False,
    **{f"fxCount{i}": 1 for i in range(2, 9)},
}
COLOR_PROPS_VM = {"personaColor"}

NEW_USER = dict(FIXTURE)
NEW_USER.update({
    "userName": "Sam", "observationNights": 0, "objectsLogged": 0, "observationHours": 0, "constellationsLogged": 0,
    "meteorSightings": 0, "moonSessions": 0, "sketchesMade": 0, "personaIndex": 0,
    **{f"showScreen{i}": False for i in range(2, 10)},
})
EXTREME = dict(FIXTURE)
EXTREME.update({
    "userName": "Maximiliana Wilhelmina von Sternenhimmel-Ortega",
    "observationNights": 365, "objectsLogged": 1284567, "observationHours": 98765, "constellationsLogged": 88,
    "meteorSightings": 123456, "moonSessions": 9999, "sketchesMade": 4321, "personaIndex": 3,
    "personaName": "Meteor Watcher", "personaDescription": "You are ready for a fleeting bright moment.", "personaColor": "081526",
    "introHeadline": "Ihr Jahr 2026 auf Nocturne – vollständig erzählt",
    "introSupport": "Ein Jahr, ganz und gar Ihres, Nacht für Nacht.",
    "screen2Headline": "Sie haben nach oben geschaut, immer wieder.", "screen2Support": "Und dabei ein kleines bisschen mehr Staunen gefunden.",
    "screen2Unit": "Nächte unter freiem Himmel",
    "screen3Unit": "katalogisierte Himmelsobjekte", "screen4Unit": "Beobachtungsstunden insgesamt",
    "screen5Unit": "erfasste Sternbilder im Atlas", "screen6Unit": "gesichtete Sternschnuppen",
    "screen7Unit": "Mondbeobachtungen insgesamt", "screen8Unit": "angefertigte Himmelsskizzen",
    "continueLabel": "Weiter lesen", "previousLabel": "Zurückgehen", "pauseLabel": "Anhalten", "playLabel": "Fortsetzen",
    "shareLabel": "Jetzt teilen", "replayLabel": "Wiederholen",
    "summaryHeadline": "Ein kleines Jahr. Ganz schön viel von Ihnen.",
    "summarySupport": "Nehmen Sie ein Stück Ihres Jahres mit auf den Weg.",
    "shareIncludeName": True,
})

FIXTURES = {"Fixture": FIXTURE, "NewUser": NEW_USER, "Extreme": EXTREME}


def kind_of(name, v):
    if v == "trigger":
        return "trigger"
    if name in COLOR_PROPS_VM:
        return "color"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "num"
    return "str"


ALL_PROPS = dict(FIXTURE)
ALL_PROPS.update(ADDITIONS)
PTYPE = {"num": "ViewModelPropertyNumber", "str": "ViewModelPropertyString", "bool": "ViewModelPropertyBoolean",
         "color": "ViewModelPropertyColor", "trigger": "ViewModelPropertyTrigger"}
ITYPE = {"num": "ViewModelInstanceNumber", "str": "ViewModelInstanceString", "bool": "ViewModelInstanceBoolean",
         "color": "ViewModelInstanceColor", "trigger": "ViewModelInstanceTrigger"}
for name, v in ALL_PROPS.items():
    vm.props[name] = (nid(), kind_of(name, v))


def vm_element():
    props = [El(PTYPE[k], name=n, id=i) for n, (i, k) in vm.props.items()]
    insts = []
    inst_ids = {}
    for fname, data in FIXTURES.items():
        vals = []
        for n, (pid, k) in vm.props.items():
            v = data.get(n, ADDITIONS.get(n))
            if k == "trigger":
                vals.append(El(ITYPE[k], viewModelPropertyId=pid))
                continue
            if k == "color":
                v = argb(v)
            vals.append(El(ITYPE[k], propertyValue=v if not isinstance(v, int) or isinstance(v, bool) else float(v),
                           viewModelPropertyId=pid))
        iid = nid()
        inst_ids[fname] = iid
        insts.append(El("ViewModelInstance", *vals, exports=True, name=fname, id=iid))
    return El("ViewModel", *props, *insts, defaultInstanceId=inst_ids["Fixture"], name="UserRecap", id=VMID), inst_ids


VM_EL, INST_IDS = vm_element()

# ---------------------------------------------------------------- converters
CONVERTERS = []


def formula(name, tokens):
    T = []
    fn = {"min(": 0, "max(": 1, "round(": 2, "ceil(": 3, "floor(": 4, "sqrt(": 5, "pow(": 6}
    op = {"+": 0, "-": 1, "*": 2, "/": 3}
    for t in tokens:
        if isinstance(t, (int, float)):
            T.append(El("FormulaTokenValue", operationValue=float(t)))
        elif isinstance(t, tuple) and t[0] == "vm":
            T.append(El("FormulaTokenValue", bind(t[1], 777), operationValue=0.0))
        elif t == "in":
            T.append(El("FormulaTokenInput"))
        elif t in fn:
            T.append(El("FormulaTokenFunction", functionType=fn[t]))
        elif t in op:
            T.append(El("FormulaTokenOperation", operationType=op[t]))
        elif t == "(":
            T.append(El("FormulaTokenParenthesisOpen"))
        elif t == ")":
            T.append(El("FormulaTokenParenthesisClose"))
        elif t == ",":
            T.append(El("FormulaTokenArgumentSeparator"))
        else:
            raise ValueError(t)
    e = El("DataConverterFormula", *T, name=name)
    CONVERTERS.append(e)
    return e.id


def group(name, *ids):
    e = El("DataConverterGroup", *[El("DataConverterGroupItem", converterId=i) for i in ids], name=name)
    CONVERTERS.append(e)
    return e.id


def conv(tag, name, **kw):
    e = El(tag, name=name, **kw)
    CONVERTERS.append(e)
    return e.id


CV_TOSTR_INT = conv("DataConverterToString", "To integer text", decimals=0, round=True)
CV_TOSTR = conv("DataConverterToString", "To text")
CV_TONUM = conv("DataConverterToNumber", "To number")
CV_NOT = conv("DataConverterBooleanNegate", "Not")
CV_CLAMP_INT = formula("Clamp count (>=0, integer)", ["max(", 0, ",", "round(", "in", ")", ")"])
CV_INT_TEXT = group("Count text", CV_CLAMP_INT, CV_TOSTR_INT)
CV_BOOL_NUM = group("Bool to 0/1", CV_TOSTR, CV_TONUM)
CV_NOTBOOL_NUM = group("Not bool to 0/1", CV_NOT, CV_TOSTR, CV_TONUM)
# displayValue: 0 = flex (shown), 1 = none (hidden)
CV_HIDE_IF_FALSE = CV_NOTBOOL_NUM

CV_COUNT = {}
for i in range(2, 9):
    f = formula(f"Count-up {i}", ["max(", 0, ",", "round(", "in", "*", ("vm", f"fxCount{i}"), ")", ")"])
    CV_COUNT[i] = group(f"Count-up text {i}", f, CV_TOSTR_INT)

_EQ = {}


def cv_eq(k):
    """number -> 1 when input == k, else 0 (for integer inputs)."""
    if k not in _EQ:
        _EQ[k] = formula(f"Equals {k}", ["max(", 0, ",", 1, "-", "(", "in", "-", k, ")", "*", "(", "in", "-", k, ")", ")"])
    return _EQ[k]


_OFF = {}


def cv_offscreen_unless(k, base):
    """x position: base when input == k, otherwise far off-artboard (moves hit targets away)."""
    key = (k, base)
    if key not in _OFF:
        _OFF[key] = formula(f"Offscreen unless {k} (x={base})",
                            [base, "+", 3000, "*", "(", 1, "-", "max(", 0, ",", 1, "-", "(", "in", "-", k, ")", "*",
                             "(", "in", "-", k, ")", ")", ")"])
    return _OFF[key]


def cv_offscreen_if(k, base):
    key = ("if", k, base)
    if key not in _OFF:
        _OFF[key] = formula(f"Offscreen if {k} (x={base})",
                            [base, "+", 3000, "*", "max(", 0, ",", 1, "-", "(", "in", "-", k, ")", "*",
                             "(", "in", "-", k, ")", ")"])
    return _OFF[key]


CV_SEG = {k: formula(f"Segment {k} fill", ["min(", 1, ",", "max(", 0, ",", "in", "-", k, "+",
                                            ("vm", "screenProgress"), ")", ")"]) for k in range(1, 11)}

# ---------------------------------------------------------------- fonts / text
FONT_SG = nid()
FONT_MONO = nid()
FONT_MONO_MED = nid()
FONTS = [
    El("FontAsset", file="assets/fonts/SpaceGrotesk-Variable.ttf", name="Space Grotesk", id=FONT_SG),
    El("FontAsset", file="assets/fonts/IBMPlexMono-Regular.ttf", name="IBM Plex Mono", id=FONT_MONO),
    El("FontAsset", file="assets/fonts/IBMPlexMono-Medium.ttf", name="IBM Plex Mono Medium", id=FONT_MONO_MED),
]
WGHT = 2003265652
SG_NAMES = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}


def tstyle(font, size, color, a=1.0, weight=400, ls=0.0, lh=-1.0, name="Style"):
    if font == "sg":
        ch = [fill(color, a), El("TextStyleAxis", tag=WGHT, axisValue=float(weight), name="Weight")]
        return El("TextStylePaint", *ch, fontSize=float(size), fontAssetId=FONT_SG, letterSpacing=float(ls),
                  lineHeight=float(lh), familyName="Space Grotesk", styleName=SG_NAMES[weight], name=name)
    fid = FONT_MONO if font == "mono" else FONT_MONO_MED
    return El("TextStylePaint", fill(color, a), fontSize=float(size), fontAssetId=fid, letterSpacing=float(ls),
              lineHeight=float(lh), familyName="IBM Plex Mono", styleName="Medium" if font == "monoMed" else "Regular",
              name=name)


def text(name, x, y, w, h, style, value="", binding=None, align="center", ox=None, oy=0.0, overflow="ellipsis",
         wrap="wrap", sizing="fixed", valign="top", extra=(), **kw):
    if ox is None:
        ox = {"left": 0.0, "center": 0.5, "right": 1.0}[align]
    run = El("TextValueRun", binding, styleId=style.id, text=value, name="Run")
    return El("Text", style, run, *extra, x=float(x), y=float(y), width=float(w), height=float(h), originX=float(ox),
              originY=float(oy), alignValue=align, sizingValue=sizing, overflowValue=overflow, wrapValue=wrap,
              verticalAlignValue=valign, name=name, **kw)


def tb(prop, conv=None):
    return bind(prop, KEY_TEXT, conv)


# ---------------------------------------------------------------- helpers for scene timelines
def fade_up(oid, f0, f1, dy=18, ease="out", o0=0.0):
    ry = REST[(oid, "y")]
    return [(oid, "opacity", [(0, o0, "hold"), (f0, o0, ease), (f1, 1.0, "hold")]),
            (oid, "y", [(0, ry + dy, "hold"), (f0, ry + dy, ease), (f1, ry, "hold")])]


def fade_out(oid, f0, f1, dy=-16, ease="in"):
    ry = REST[(oid, "y")]
    return [(oid, "opacity", [(f0, 1.0, ease), (f1, 0.0, "hold")]),
            (oid, "y", [(f0, ry, ease), (f1, ry + dy, "hold")])]


def pop(oid, f0, f1, s0=0.0, ease="back", o=True):
    tr_ = [(oid, "scaleX", [(0, s0, "hold"), (f0, s0, ease), (f1, REST[(oid, "scaleX")], "hold")]),
           (oid, "scaleY", [(0, s0, "hold"), (f0, s0, ease), (f1, REST[(oid, "scaleY")], "hold")])]
    if o:
        tr_.append((oid, "opacity", [(0, 0.0, "hold"), (f0, 0.0, "out"), (f0 + max(1, (f1 - f0) * 0.4), REST[(oid, "opacity")], "hold")]))
    return tr_


def scale_to(oid, f0, f1, s0, s1, ease="out"):
    return [(oid, "scaleX", [(f0, s0, ease), (f1, s1, "hold")]), (oid, "scaleY", [(f0, s0, ease), (f1, s1, "hold")])]


def prop_tr(oid, prop, pts):
    """pts: list of (frame, value, ease)"""
    return [(oid, prop, pts)]


def osc(oid, prop, dur, lo, hi, phase=0.0, steps=4):
    """seamless loop oscillation between lo and hi (sine-ish via cubic eases)."""
    keys = []
    mid = (lo + hi) / 2
    amp = (hi - lo) / 2
    n = steps
    for i in range(n + 1):
        f = dur * i / n
        v = mid + amp * math.sin(2 * math.pi * (i / n + phase))
        keys.append((f, v, "sine"))
    return [(oid, prop, keys)]


# ---------------------------------------------------------------- scene component machinery
SCENE_ARTBOARDS = []
COMPONENT_ASSETS = []


def scene_component(k, name, art_children, copy_children, anims, root_extra=()):
    """anims: dict enterF, enterB, exitF, exitB, idle -> (dur, tracks)."""
    root = node(f"Scene {k} Root", *art_children, *copy_children, *root_extra, x=0, y=0)
    REST[(root.id, "opacity")] = 1.0

    universe = set()
    for key in ("enterF", "enterB", "exitF", "exitB", "idle"):
        universe |= keys_of(anims[key][1])
    universe.add((root.id, "opacity"))

    dummy = node("Frozen Marker", x=0, y=0)
    A = {}
    A["hidden"] = anim(f"S{k} Hidden", 1, rest_tracks(universe, overrides={(root.id, "opacity"): 0.0}))
    A["static"] = anim(f"S{k} Static (reduced motion)", 1, rest_tracks(universe))
    A["frozen"] = anim(f"S{k} Frozen (paused)", 1, [(dummy.id, "opacity", [(0, 1.0, "hold")])])
    for key in ("enterF", "enterB"):
        d, t = anims[key]
        t = t + [(root.id, "opacity", [(0, 1.0, "hold")])]
        A[key] = anim(f"S{k} Enter {'forward' if key == 'enterF' else 'back'}", d, complete(t, universe, 0))
    for key in ("exitF", "exitB"):
        d, t = anims[key]
        A[key] = anim(f"S{k} Exit {'forward' if key == 'exitF' else 'back'}", d, t)
    d, t = anims["idle"]
    A["idle"] = anim(f"S{k} Idle", d, t, loop="loop")

    S = {n: nid() for n in ("hidden", "enterF", "enterB", "idle", "frozen", "exitF", "exitB", "static")}
    rm_on = c_bool("reducedMotion", True)
    cs_is = lambda: c_num("currentScreen", "equal", k)
    cs_not = lambda: c_num("currentScreen", "notEqual", k)
    fwd = lambda: c_num("navDirection", "greaterThanOrEqual", 0)
    back = lambda: c_num("navDirection", "lessThan", 0)

    def leaving():
        return [
            tr(S["exitF"], cs_not(), fwd(), c_bool("reducedMotion", False), dur=150),
            tr(S["exitB"], cs_not(), back(), c_bool("reducedMotion", False), dur=150),
            tr(S["hidden"], cs_not(), c_bool("reducedMotion", True), dur=220),
        ]

    states = [
        El("AnimationState",
           tr(S["static"], cs_is(), c_bool("reducedMotion", True), dur=220),
           tr(S["enterF"], cs_is(), fwd(), c_bool("reducedMotion", False)),
           tr(S["enterB"], cs_is(), back(), c_bool("reducedMotion", False)),
           animationId=A["hidden"].id, x=0.0, y=0.0, id=S["hidden"]),
        El("AnimationState", *leaving(),
           tr(S["static"], c_bool("reducedMotion", True), dur=220),
           tr(S["idle"], exit_pct=100),
           animationId=A["enterF"].id, reset=True, x=260.0, y=-140.0, id=S["enterF"]),
        El("AnimationState", *leaving(),
           tr(S["static"], c_bool("reducedMotion", True), dur=220),
           tr(S["idle"], exit_pct=100),
           animationId=A["enterB"].id, reset=True, x=260.0, y=140.0, id=S["enterB"]),
        El("AnimationState", *leaving(),
           tr(S["static"], c_bool("reducedMotion", True), dur=220),
           tr(S["frozen"], c_bool("isPaused", True)),
           tr(S["frozen"], c_bool("isHolding", True)),
           animationId=A["idle"].id, x=520.0, y=0.0, id=S["idle"]),
        El("AnimationState", *leaving(),
           tr(S["idle"], c_bool("isPaused", False), c_bool("isHolding", False)),
           animationId=A["frozen"].id, x=520.0, y=200.0, id=S["frozen"]),
        El("AnimationState",
           tr(S["enterB"], cs_is(), back(), c_bool("reducedMotion", False), dur=150),
           tr(S["enterF"], cs_is(), fwd(), c_bool("reducedMotion", False), dur=150),
           tr(S["hidden"], exit_pct=100),
           animationId=A["exitF"].id, reset=True, x=780.0, y=-140.0, id=S["exitF"]),
        El("AnimationState",
           tr(S["enterF"], cs_is(), fwd(), c_bool("reducedMotion", False), dur=150),
           tr(S["enterB"], cs_is(), back(), c_bool("reducedMotion", False), dur=150),
           tr(S["hidden"], exit_pct=100),
           animationId=A["exitB"].id, reset=True, x=780.0, y=140.0, id=S["exitB"]),
        El("AnimationState",
           tr(S["hidden"], cs_not(), dur=220),
           tr(S["idle"], c_bool("reducedMotion", False), dur=220),
           animationId=A["static"].id, x=260.0, y=320.0, id=S["static"]),
    ]
    smid = nid()
    sm = El("StateMachine", layer("Scene", S["hidden"], states), name=f"Scene {k}", id=smid)
    style = El("LayoutComponentStyle", name="Artboard Style")
    ab = El("Artboard", style, root, dummy, sm, *[A[x] for x in ("enterF", "enterB", "idle", "exitF", "exitB", "hidden", "static", "frozen")],
            isComponent=True, clip=False, defaultStateMachineId=smid, styleId=style.id,
            width=float(W), height=float(H), x=float(500 + (k - 1) * 440), y=1000.0, name=f"Scene {k} · {name}")
    SCENE_ARTBOARDS.append(ab)
    COMPONENT_ASSETS.append(El("ComponentAsset", artboardId=ab.id, name=f"Scene {k} · {name}"))
    return ab


# ---------------------------------------------------------------- shared copy block for metric scenes
COPY_Y = {"num": 528, "unit": 594, "div": 628, "head": 646, "sup": 722}


def metric_copy(k, stat, align):
    xs = {"left": 28.0, "center": 195.0, "right": 362.0}[align]
    num = text(f"S{k} Hero Number", xs, COPY_Y["num"], 334, 116,
               tstyle("sg", 108, ICE, weight=300, ls=-3, lh=116), "", tb(stat, CV_COUNT[k]), align=align, oy=0.5,
               overflow="fitFontSize", wrap="noWrap")
    unit = text(f"S{k} Unit", xs, COPY_Y["unit"], 334, 20, tstyle("mono", 14, ICE, 0.82, ls=3.2, lh=20), "",
                tb(f"screen{k}Unit"), align=align)
    # divider: hairline + amber sparkle + hairline
    if align == "center":
        dx = 195.0
        lines = [shape("Rule L", rect(70, 1, ox=1.0), fill(AMBER, 0.55), x=-12, y=0),
                 shape("Rule R", rect(70, 1, ox=0.0), fill(AMBER, 0.55), x=12, y=0)]
    elif align == "left":
        dx = 34.0
        lines = [shape("Rule R", rect(96, 1, ox=0.0), fill(AMBER, 0.55), x=12, y=0)]
    else:
        dx = 356.0
        lines = [shape("Rule L", rect(96, 1, ox=1.0), fill(AMBER, 0.55), x=-12, y=0)]
    div = node(f"S{k} Divider", star4("Spark", 0, 0, 13, AMBER, glow=4, glow_a=0.6), *lines, x=dx, y=COPY_Y["div"])
    head = text(f"S{k} Headline", xs, COPY_Y["head"], 334, 74, tstyle("sg", 30, WHITE, weight=400, lh=36, ls=-0.3), "",
                tb(f"screen{k}Headline"), align=align)
    sup = text(f"S{k} Support", xs, COPY_Y["sup"], 334, 36, tstyle("mono", 12.5, ICE, 0.72, lh=18, ls=0.4), "",
               tb(f"screen{k}Support"), align=align)
    counter = node(f"S{k} Count Playhead", x=1.0, y=0.0)
    counter.add(bind(f"fxCount{k}", KEY_X, direction=True))
    els = [num, unit, div, head, sup]
    copy = node(f"S{k} Copy", *els, x=0, y=0)
    return copy, counter, dict(num=num.id, unit=unit.id, div=div.id, head=head.id, sup=sup.id, copy=copy.id,
                               counter=counter.id)


def copy_enter(c, t0=24):
    """count 0->1 synchronised with the hero (t0..t0+60), then label, rule, headline, support."""
    tr_ = []
    tr_ += prop_tr(c["counter"], "x", [(0, 0.0, "hold"), (t0, 0.0, (0.3, 0.0, 0.2, 1.0)), (t0 + 62, 1.0, "hold")])
    tr_ += fade_up(c["num"], t0 - 6, t0 + 30, dy=26)
    tr_ += fade_up(c["unit"], t0 + 40, t0 + 70, dy=10)
    tr_ += [(c["div"], "scaleX", [(0, 0.0, "hold"), (t0 + 52, 0.0, "out"), (t0 + 84, 1.0, "hold")]),
            (c["div"], "opacity", [(0, 0.0, "hold"), (t0 + 52, 0.0, "out"), (t0 + 66, 1.0, "hold")])]
    tr_ += fade_up(c["head"], t0 + 60, t0 + 92, dy=16)
    tr_ += fade_up(c["sup"], t0 + 72, t0 + 104, dy=12)
    return tr_


def copy_enter_back(c):
    tr_ = []
    tr_ += prop_tr(c["counter"], "x", [(0, 0.0, "hold"), (16, 0.0, "out"), (46, 1.0, "hold")])
    for i, key in enumerate(("num", "unit", "head", "sup")):
        tr_ += fade_up(c[key], 16 + i * 4, 42 + i * 4, dy=-18)
    tr_ += [(c["div"], "scaleX", [(0, 0.0, "hold"), (20, 0.0, "out"), (46, 1.0, "hold")])]
    return tr_


def copy_exit(c, dy=-22):
    tr_ = []
    for i, key in enumerate(("num", "unit", "head", "sup")):
        tr_ += fade_out(c[key], i * 2, 13 + i * 2, dy=dy)
    tr_ += [(c["div"], "scaleX", [(0, 1.0, "in"), (14, 0.0, "hold")])]
    return tr_


def art_exit(art_id, s1=0.86, dy=-10, f1=34, o_end=0.0):
    ry = REST[(art_id, "y")]
    return [(art_id, "opacity", [(0, 1.0, "in"), (f1, o_end, "hold")]),
            (art_id, "scaleX", [(0, 1.0, "in"), (f1, s1, "hold")]),
            (art_id, "scaleY", [(0, 1.0, "in"), (f1, s1, "hold")]),
            (art_id, "y", [(0, ry, "in"), (f1, ry + dy, "hold")])]


rnd = random.Random(2026)


def starfield(name, n, cx, cy, r, dmin=1.0, dmax=2.6, colors=((ICE, 1.0),), amin=0.35, amax=0.95, glow_every=0,
              groups=1, shape_circle=True, rect_wh=None):
    """Return list of group nodes containing pseudo-random stars."""
    grp = [node(f"{name} {g + 1}", x=0, y=0) for g in range(groups)]
    for i in range(n):
        if rect_wh:
            x = cx + (rnd.random() - 0.5) * rect_wh[0]
            y = cy + (rnd.random() - 0.5) * rect_wh[1]
        else:
            a = rnd.random() * 2 * math.pi
            rr = r * math.sqrt(rnd.random())
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        d = dmin + (dmax - dmin) * rnd.random() ** 2.2
        col, ca = colors[i % len(colors)]
        a_ = (amin + (amax - amin) * rnd.random()) * ca
        g = glow_every and (i % glow_every == 0)
        grp[i % groups].add(dot("Star", round(x, 1), round(y, 1), round(d, 2), col, a_, glow=(d * 2.2 if g else None)))
    return grp


# =====================================================================================
# APERTURE component (the reusable motif)
# =====================================================================================
AP_R = 150.0
AP_C = 160.0


def build_aperture():
    blades = []
    nb = 9
    iris_tracks = []
    psi_for = lambda t: math.asin(min(1.0, 0.045 + 0.955 * t))
    # find blade body side
    a0 = 0.0
    th = a0 + math.pi + math.radians(45)
    n = (-math.sin(th), math.cos(th))
    c = (-AP_R * math.cos(a0), -AP_R * math.sin(a0))
    body_neg = (n[0] * c[0] + n[1] * c[1]) > 0
    Wb, Lb = AP_R * 1.15, AP_R * 2.5
    for i in range(nb):
        a = 2 * math.pi * i / nb - math.pi / 2
        px, py = AP_C + AP_R * math.cos(a), AP_C + AP_R * math.sin(a)
        rot_open = a + math.pi + psi_for(1.0)
        oy = 1.0 if body_neg else 0.0
        blade = node(f"Blade {i + 1}",
                     shape("Leaf",
                           rect(Lb, Wb, ox=0.0, oy=oy),
                           stroke(ICE, 0.28, 1.0),
                           fill(paint=linear([(0, "17304F", 1.0), (0.18, "0F2238", 1.0), (1, "091729", 1.0)],
                                             0, 0, 0, (-Wb if body_neg else Wb)))),
                     x=px, y=py, rotation=rot_open)
        blades.append(blade)
        keys = []
        for s in range(0, 61, 5):
            t = s / 60
            keys.append((s, a + math.pi + psi_for(t), "lin"))
        iris_tracks.append((blade.id, "rotation", keys))
    clip_src = shape("Iris Clip", ellipse(AP_R * 2), x=AP_C, y=AP_C)
    blade_grp = node("Blades", *blades, El("ClippingShape", sourceId=clip_src.id, name="Clip"), x=0, y=0)
    pupil = dot("Pupil Glow", AP_C, AP_C, 14, ICE, 0.95, glow=12, glow_a=0.8, opacity=0.0)
    iris_tracks.append((pupil.id, "opacity", [(0, 1.0, "lin"), (14, 0.0, "hold")]))

    ticks_minor = shape("Minor Ticks", ellipse(314), stroke(ICE, 0.32, 5, effects=[dash(0.8, math.pi * 314 / 120 - 0.8)]),
                        x=AP_C, y=AP_C)
    ticks_major = shape("Major Ticks", ellipse(320), stroke(ICE, 0.7, 11, effects=[dash(1.3, math.pi * 320 / 12 - 1.3)]),
                        x=AP_C, y=AP_C)
    ring = shape("Rim", ellipse(AP_R * 2), stroke(ICE, 0.55, 1.2), x=AP_C, y=AP_C)
    ring_glow = shape("Rim Glow", ellipse(AP_R * 2), stroke(BLUE, 0.35, 6, feather=6), x=AP_C, y=AP_C)
    dotted = shape("Inner Dotted", ellipse(268), stroke(BLUE, 0.45, 1, effects=[dash(1.0, 5.0)]), x=AP_C, y=AP_C)
    cross = []
    for i in range(4):
        a = i * math.pi / 2 - math.pi / 2
        for (r0, r1, al) in ((166, 206, 0.55),):
            mx, my = AP_C + (r0 + r1) / 2 * math.cos(a), AP_C + (r0 + r1) / 2 * math.sin(a)
            cross.append(shape(f"Cross {i}", rect(1.0, r1 - r0), fill(ICE, al), x=mx, y=my, rotation=a + math.pi / 2))
        cross.append(star4(f"Cardinal {i}", AP_C + 176 * math.cos(a), AP_C + 176 * math.sin(a), 9, AMBER, 0.95,
                           glow=4, glow_a=0.55, inner=0.32))
    reticle = node("Reticle", ticks_major, ticks_minor, ring, ring_glow, dotted, *cross, x=0, y=0)
    style = El("LayoutComponentStyle", name="Artboard Style")
    iris = anim("Iris", 60, iris_tracks)
    smid = nid()
    hold = anim("Hold", 1, [(pupil.id, "opacity", [(0, 0.0, "hold")])])
    sm = El("StateMachine", layer("Static", nid(), []), name="Aperture", id=smid)
    # the static layer needs a target: build explicitly
    st = nid()
    sm = El("StateMachine", layer("Static", st, [El("AnimationState", animationId=hold.id, x=0.0, y=0.0, id=st)]),
            name="Aperture", id=smid)
    ab = El("Artboard", style, pupil, reticle, blade_grp, clip_src, sm, iris, hold, isComponent=True, clip=False,
            defaultStateMachineId=smid, styleId=style.id, width=320.0, height=320.0, x=500.0, y=0.0,
            name="Aperture Motif")
    return ab, iris


APERTURE, IRIS = build_aperture()
COMPONENT_ASSETS.append(El("ComponentAsset", artboardId=APERTURE.id, name="Aperture Motif"))


def aperture_instance(name, cx, cy, scale, iris_t=1.0, **kw):
    remap = El("NestedRemapAnimation", animationId=IRIS.id, time=float(iris_t), name="Iris Remap")
    na = El("NestedArtboard", remap, artboardId=APERTURE.id, x=-AP_C, y=-AP_C, name="Aperture")
    return node(name, na, x=cx, y=cy, scaleX=scale, scaleY=scale, **kw), remap


# =====================================================================================
# SCENES
# =====================================================================================
def scene1():
    k = 1
    cx, cy = 195.0, 300.0
    halo = shape("Halo", ellipse(330), fill(ICE, 0.10, feather=46), x=cx, y=cy)
    disk_base = shape("Disk", ellipse(236),
                      fill(paint=radial([(0, "21477A", 1), (0.55, "123059", 1), (1, "0A1B33", 1)], 170, -48, -56)),
                      x=cx, y=cy)
    inner = shape("Disk Atmosphere", ellipse(236), stroke(ICE, 0.28, 18, feather=14), x=cx, y=cy)
    rim_tr = trim(0.0, 0.42, 0.78)
    rim = shape("Rim Light", ellipse(236), stroke(ICE, 0.85, 2.2, effects=[rim_tr], cap="round"), x=cx, y=cy)
    rim_glow_tr = trim(0.0, 0.42, 0.78)
    rim_glow = shape("Rim Glow", ellipse(236), stroke(ICE, 0.5, 8, feather=8, effects=[rim_glow_tr], cap="round"), x=cx, y=cy)
    lat = [shape(f"Latitude {i}", ellipse(236, h), stroke(ICE, 0.07, 1), x=cx, y=cy) for i, h in enumerate((60, 140, 210))]
    lat_clip = shape("Latitude Clip", ellipse(236), x=cx, y=cy)
    lat_grp = node("Latitudes", *lat, El("ClippingShape", sourceId=lat_clip.id, name="Clip"), x=0, y=0)
    wm_style = tstyle("sg", 42, ICE, weight=500, ls=1.5, lh=50)
    wm_mod_rng = El("TextModifierRange", modifyFrom=1.0, modifyTo=1.0, falloffFrom=1.0, falloffTo=1.0, name="Reveal")
    wm_mod = El("TextModifierGroup", wm_mod_rng, modifyOpacity=True, modifyTranslation=True, invertOpacity=True,
                opacity=0.0, y=14.0, name="Letter Reveal")
    # modifier: glyphs inside [modifyFrom, modifyTo] are hidden; rest pose: range collapsed at 1 => nothing hidden
    wordmark = text("Wordmark", cx, cy - 6, 300, 52, wm_style, "Nocturne", None, align="center", oy=0.5, wrap="noWrap",
                    overflow="visible", extra=[wm_mod])
    coord_a = text("Coord RA", cx, cy + 34, 270, 16, tstyle("mono", 10, ICE, 0.55, ls=2.4), "RA 05h 35m · DEC −05° 23′",
                   None, align="center", wrap="noWrap")
    disk = node("Celestial Disk", halo, rim, rim_glow, wordmark, coord_a, lat_grp, lat_clip, inner, disk_base, x=0, y=0)
    stars = starfield("Intro Stars", 26, 195, 300, 0, colors=((ICE, 1.0), (WHITE, 1.0), (AMBER, 0.9)), dmin=1.0, dmax=2.4,
                      rect_wh=(370, 420), groups=3, glow_every=7)
    art = node("S1 Art", disk, *stars, x=0, y=0)

    name = text("S1 Name", 195, 506, 300, 28, tstyle("sg", 21, ICE, 0.9, weight=400, ls=0.2, lh=28), "", tb("userName"),
                align="center")
    head = text("S1 Headline", 195, 544, 334, 88, tstyle("sg", 36, WHITE, weight=400, lh=42, ls=-0.6), "",
                tb("introHeadline"), align="center")
    sup = text("S1 Support", 195, 640, 334, 40, tstyle("mono", 13, ICE, 0.75, lh=19, ls=0.4), "", tb("introSupport"),
               align="center")
    per = text("S1 Period", 195, 690, 334, 18, tstyle("mono", 10.5, AMBER, 0.85, ls=2.2), "", tb("periodLabel"),
               align="center", wrap="noWrap")
    div = node("S1 Divider", star4("Spark", 0, 0, 11, AMBER, glow=4), shape("Rule L", rect(48, 1, ox=1.0), fill(AMBER, 0.5), x=-10),
               shape("Rule R", rect(48, 1, ox=0.0), fill(AMBER, 0.5), x=10), x=195, y=722)
    copy = node("S1 Copy", name, head, sup, per, div, x=0, y=0)

    eF = []
    eF += [(disk.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (40, 1.0, "hold")])]
    eF += scale_to(disk.id, 0, 0, 0.72, 0.72, "hold") + scale_to(disk.id, 10, 72, 0.72, 1.0, "out")
    eF += [(disk.id, "scaleX", [(0, 0.72, "hold"), (10, 0.72, "out"), (72, 1.0, "hold")]),
           (disk.id, "scaleY", [(0, 0.72, "hold"), (10, 0.72, "out"), (72, 1.0, "hold")])]
    eF += [(rim_tr.id, "end", [(0, 0.0, "hold"), (24, 0.0, "out"), (84, 0.42, "hold")]),
           (rim_glow_tr.id, "end", [(0, 0.0, "hold"), (24, 0.0, "out"), (84, 0.42, "hold")]),
           (wm_mod_rng.id, "modifyFrom", [(0, 0.0, "hold"), (30, 0.0, "out"), (78, 1.0, "hold")]),
           (wm_mod_rng.id, "falloffFrom", [(0, 0.25, "hold"), (30, 0.25, "out"), (78, 1.0, "hold")]),
           (coord_a.id, "opacity", [(0, 0.0, "hold"), (60, 0.0, "out"), (86, 1.0, "hold")]),
           (halo.id, "opacity", [(0, 0.0, "hold"), (20, 0.0, "out"), (90, 1.0, "hold")])]
    for i, g in enumerate(stars):
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (20 + i * 14, 0.0, "out"), (60 + i * 14, 1.0, "hold")])]
    eF += fade_up(name.id, 54, 84, 14) + fade_up(head.id, 62, 96, 18) + fade_up(sup.id, 76, 106, 12) + \
        fade_up(per.id, 84, 112, 8)
    eF += [(div.id, "scaleX", [(0, 0.0, "hold"), (90, 0.0, "out"), (118, 1.0, "hold")])]
    eB = []
    eB += [(disk.id, "opacity", [(0, 0.0, "hold"), (2, 0.0, "out"), (30, 1.0, "hold")]),
           (disk.id, "scaleX", [(0, 1.18, "hold"), (2, 1.18, "out"), (44, 1.0, "hold")]),
           (disk.id, "scaleY", [(0, 1.18, "hold"), (2, 1.18, "out"), (44, 1.0, "hold")])]
    for i, key in enumerate((name, head, sup, per)):
        eB += fade_up(key.id, 16 + i * 4, 42 + i * 4, dy=-16)
    xF = art_exit(art.id, 0.8, 0) + [(c.id, prop, keys) for c in [] for prop, keys in []]
    xF += fade_out(copy.id, 0, 14, -24)
    xB = art_exit(art.id, 1.15, 0, f1=24) + fade_out(copy.id, 0, 14, 24)
    idle = []
    idle += osc(halo.id, "opacity", 360, 0.75, 1.0)
    idle += [(rim_tr.id, "offset", [(0, 0.78, "lin"), (720, 1.78, "hold")]),
             (rim_glow_tr.id, "offset", [(0, 0.78, "lin"), (720, 1.78, "hold")])]
    for i, g in enumerate(stars):
        idle += osc(g.id, "opacity", 240, 0.55, 1.0, phase=i / 3)
    return scene_component(k, "Invitation", [art], [copy],
                           dict(enterF=(124, eF), enterB=(56, eB), exitF=(36, xF), exitB=(36, xB), idle=(720, idle)))


def scene2():
    k = 2
    cx, cy, r = 195.0, 290.0, 158.0
    sky_bg = shape("Sky", ellipse(r * 2), fill(paint=radial([(0, "17335C", 1), (0.6, "0D2343", 1), (1, "081526", 1)], r, 20, 30)),
                   x=cx, y=cy)
    band = node("Milky Band",
                shape("Band Blue", ellipse(420, 96), fill(BLUE, 0.30, feather=34)),
                shape("Band Ice", ellipse(300, 46), fill(ICE, 0.20, feather=22), y=-6),
                shape("Band Amber", ellipse(190, 54), fill(AMBER, 0.26, feather=26), x=-60, y=22),
                shape("Dust Lane", ellipse(260, 14), fill(MID, 0.55, feather=10), x=10, y=4),
                x=cx, y=cy + 30, rotation=-0.55)
    stars = starfield("Field", 70, cx, cy, r - 6, dmin=0.9, dmax=3.0, colors=((WHITE, 1), (ICE, 1), (ICE, 1), (AMBER, 0.95)),
                      glow_every=9, groups=5)
    bright = star4("Bright Star", cx + 72, cy + 6, 26, AMBER, 1.0, glow=10, glow_a=0.7, inner=0.12)
    clip = shape("Sky Clip", ellipse(r * 2), x=cx, y=cy)
    sky = node("Sky Disk", bright, *stars, band, sky_bg, El("ClippingShape", sourceId=clip.id, name="Clip"), x=0, y=0)
    outer = starfield("Outer", 16, 195, 290, 0, rect_wh=(380, 440), dmin=0.8, dmax=1.8, amin=0.25, amax=0.6, groups=2)
    art = node("S2 Art", sky, clip, *outer, x=0, y=0)
    copy, counter, c = metric_copy(k, "observationNights", "center")
    eF = copy_enter(c, 26)
    eF += [(sky.id, "opacity", [(0, 0.0, "hold"), (8, 0.0, "out"), (26, 1.0, "hold")]),
           (sky.id, "scaleX", [(0, 1.0, "hold")]), ]
    eF += [(band.id, "x", [(0, cx - 40, "hold"), (14, cx - 40, "out"), (100, cx, "hold")]),
           (band.id, "opacity", [(0, 0.0, "hold"), (14, 0.0, "out"), (70, 1.0, "hold")])]
    for i, g in enumerate(stars):  # stars kindle in rhythm with the count
        f0 = 26 + i * 11
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (f0, 0.0, "out"), (f0 + 22, 1.0, "hold")])]
    eF += pop(bright.id, 70, 96, 0.0, "back")
    for i, g in enumerate(outer):
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (40 + i * 20, 0.0, "out"), (80 + i * 20, 1.0, "hold")])]
    eB = copy_enter_back(c) + [(sky.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (34, 1.0, "hold")]),
                               (band.id, "x", [(0, cx + 40, "hold"), (4, cx + 40, "out"), (50, cx, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.82, -6)
    xB = copy_exit(c, 22) + art_exit(art.id, 1.12, 6)
    idle = [(band.id, "x", [(0, cx, "sine"), (300, cx + 10, "sine"), (600, cx, "hold")])]
    for i, g in enumerate(stars):
        idle += osc(g.id, "opacity", 200 + 0, 0.5, 1.0, phase=i / 5)
    idle += osc(bright.id, "rotation", 600, -0.08, 0.08)
    return scene_component(k, "Nights outside", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(56, eB), exitF=(36, xF), exitB=(36, xB), idle=(600, idle)))


def scene3():
    k = 3
    cx, cy, R = 236.0, 292.0, 128.0
    rings = [
        shape("Ring", ellipse(R * 2), stroke(ICE, 0.5, 1.0), x=cx, y=cy),
        shape("Outer Ring", ellipse(R * 2 + 44), stroke(BLUE, 0.4, 1.0, effects=[dash(2, 4)]), x=cx, y=cy),
        shape("Tick Ring", ellipse(R * 2 + 18), stroke(ICE, 0.35, 7, effects=[dash(0.8, math.pi * (R * 2 + 18) / 180 - 0.8)]), x=cx, y=cy),
        shape("Inner Ring", ellipse(110), stroke(ICE, 0.15, 1.0), x=cx, y=cy),
    ]
    spokes = [shape(f"Spoke {i}", rect(1.0, 52), fill(ICE, 0.12), x=cx + 82 * math.cos(i * math.pi / 6),
                    y=cy + 82 * math.sin(i * math.pi / 6), rotation=i * math.pi / 6 + math.pi / 2) for i in range(12)]
    labels = []
    for i, lab in enumerate(("000", "090", "180", "270")):
        a = i * math.pi / 2 - math.pi / 2
        labels.append(text(f"Bearing {lab}", cx + (R + 38) * math.cos(a), cy + (R + 38) * math.sin(a) - 7, 40, 14,
                           tstyle("mono", 9.5, ICE, 0.55, ls=1.5), lab, None, align="center", wrap="noWrap"))
    sweep_tr = trim(0.0, 0.085, 0.0)
    sweep = node("Sweep",
                 shape("Sweep Wedge", poly([(0, 0)] + [((R - 6) * math.cos(-math.pi / 2 - math.radians(34) * t / 10), (R - 6) * math.sin(-math.pi / 2 - math.radians(34) * t / 10)) for t in range(11)]),
                       fill(paint=linear([(0, BLUE, 0.38), (1, BLUE, 0.0)], 0, -R, -R * 0.6, -R * 0.75))),
                 shape("Sweep Arm", rect(R + 12, 1.2, ox=0.0), fill(BLUE, 0.9), rotation=-math.pi / 2),
                 x=cx, y=cy, rotation=0.0)
    markers = []
    nm = 36
    for i in range(nm):
        a = -math.pi / 2 + 2 * math.pi * i / nm
        col = AMBER if i % 6 == 0 else ICE
        d = 7.0 if i % 6 == 0 else 4.6
        markers.append(dot(f"Marker {i + 1}", cx + R * math.cos(a), cy + R * math.sin(a), d, col, 1.0, glow=d * 1.6, glow_a=0.6))
    mk = node("Markers", *markers, x=0, y=0)
    art = node("S3 Art", sweep, mk, *labels, *rings, *spokes, x=0, y=0)
    copy, counter, c = metric_copy(k, "objectsLogged", "left")
    eF = copy_enter(c, 26)
    for g in rings + spokes:
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (40, REST[(g.id, "opacity")], "hold")])]
    eF += scale_to(rings[0].id, 0, 0, 0.6, 0.6, "hold") + [(rings[0].id, "scaleX", [(0, 0.6, "hold"), (10, 0.6, "back"), (50, 1.0, "hold")]),
                                                           (rings[0].id, "scaleY", [(0, 0.6, "hold"), (10, 0.6, "back"), (50, 1.0, "hold")])]
    eF += [(sweep.id, "rotation", [(0, -1.2, "hold"), (20, -1.2, (0.4, 0.0, 0.2, 1.0)), (92, 2 * math.pi, "hold")]),
           (sweep.id, "opacity", [(0, 0.0, "hold"), (20, 0.0, "out"), (30, 1.0, "hold")])]
    for i, m in enumerate(markers):  # light in order with the sweep
        f0 = 26 + i * 1.75
        eF += [(m.id, "opacity", [(0, 0.12, "hold"), (f0, 0.12, "out"), (f0 + 10, 1.0, "hold")]),
               (m.id, "scaleX", [(0, 0.4, "hold"), (f0, 0.4, "back"), (f0 + 14, 1.0, "hold")]),
               (m.id, "scaleY", [(0, 0.4, "hold"), (f0, 0.4, "back"), (f0 + 14, 1.0, "hold")])]
    for i, l in enumerate(labels):
        eF += [(l.id, "opacity", [(0, 0.0, "hold"), (60 + i * 6, 0.0, "out"), (80 + i * 6, 1.0, "hold")])]
    eB = copy_enter_back(c) + [(art.id, "rotation", [(0, 0.0, "hold")]),
                               (sweep.id, "rotation", [(0, 2 * math.pi + 1.5, "hold"), (4, 2 * math.pi + 1.5, "out"), (48, 2 * math.pi, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.7, -4)
    xB = copy_exit(c, 22) + art_exit(art.id, 1.12, 4)
    idle = [(sweep.id, "rotation", [(0, 2 * math.pi, "lin"), (900, 4 * math.pi, "hold")])]
    for i in range(0, nm, 3):
        idle += osc(markers[i].id, "opacity", 300, 0.55, 1.0, phase=i / nm)
    return scene_component(k, "Objects logged", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(56, eB), exitF=(36, xF), exitB=(36, xB), idle=(900, idle)))


def scene4():
    k = 4
    cx, cy = 195.0, 292.0
    arcs, trims = [], []
    n = 15
    for i in range(n):
        r = 46 + i * 9.4
        L = 0.28 + 0.5 * ((i * 37) % 11) / 10
        off = ((i * 53) % 17) / 17
        t = trim(0.0, L, off)
        trims.append((t, L, off))
        warm = i >= 9
        paint = linear([(0, BLUE, 0.95), (0.55, ICE, 0.75), (1, AMBER if warm else ICE, 0.95)], -r, 0, r, 0)
        arcs.append(shape(f"Trail {i + 1}", ellipse(r * 2), stroke(w=1.3 if i % 3 else 2.0, paint=paint, effects=[t], cap="round"),
                          x=cx, y=cy))
    glow_tr = trim(0.0, 0.5, 0.1)
    glow_arc = shape("Exposure Glow", ellipse(330), stroke(AMBER, 0.45, 10, feather=10, effects=[glow_tr], cap="round"), x=cx, y=cy)
    cross = node("Crosshair",
                 shape("V", rect(1, 400), fill(ICE, 0.22)),
                 shape("H", rect(380, 1), fill(ICE, 0.22)),
                 dot("Top Pip", 0, -186, 7, ICE, 0.0), shape("Top Ring", ellipse(10), stroke(AMBER, 0.9, 1.2), y=-186),
                 dot("Bottom Pip", 0, 186, 6, AMBER, 0.95, glow=5),
                 x=cx, y=cy)
    phases = []
    for j, (dx, s) in enumerate(((-130, 1), (-112, 1), (-96, 1), (96, -1), (112, -1), (130, -1))):
        phases.append(node(f"Phase {j}",
                           dot("Lit", 0, 0, 9, AMBER, 0.9),
                           shape("Shadow", ellipse(9), fill(MID, 1.0), x=3.2 * s * (1 + j % 3 * 0.25)),
                           x=cx + dx, y=cy))
    center_ring = shape("Midnight Ring", ellipse(70), stroke(AMBER, 0.45, 1, effects=[dash(1, 4)]), x=cx, y=cy)
    art = node("S4 Art", *phases, center_ring, glow_arc, *arcs, cross, x=0, y=0)
    copy, counter, c = metric_copy(k, "observationHours", "center")
    eF = copy_enter(c, 26)
    for i, (t, L, off) in enumerate(trims):  # long exposure traces out in rhythm with the count
        f0 = 20 + i * 3
        eF += [(t.id, "end", [(0, 0.0, "hold"), (f0, 0.0, (0.35, 0.0, 0.25, 1.0)), (f0 + 62, L, "hold")]),
               (t.id, "offset", [(0, off - 0.06, "hold"), (f0, off - 0.06, "out"), (f0 + 70, off, "hold")])]
    eF += [(glow_tr.id, "end", [(0, 0.0, "hold"), (40, 0.0, "out"), (110, 0.5, "hold")]),
           (cross.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (34, 1.0, "hold")]),
           (cross.id, "scaleX", [(0, 0.4, "hold"), (6, 0.4, "out"), (46, 1.0, "hold")]),
           (center_ring.id, "opacity", [(0, 0.0, "hold"), (60, 0.0, "out"), (90, 1.0, "hold")])]
    for j, p in enumerate(phases):
        eF += [(p.id, "opacity", [(0, 0.0, "hold"), (70 + j * 5, 0.0, "out"), (90 + j * 5, 1.0, "hold")])]
    eB = copy_enter_back(c)
    for i, (t, L, off) in enumerate(trims):
        eB += [(t.id, "offset", [(0, off + 0.08, "hold"), (2, off + 0.08, "out"), (44, off, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.86, -4)
    xB = copy_exit(c, 22) + art_exit(art.id, 1.1, 4)
    idle = []
    for i, (t, L, off) in enumerate(trims):
        idle += [(t.id, "offset", [(0, off, "lin"), (3600, off + 1.0, "hold")])]
    idle += [(glow_tr.id, "offset", [(0, 0.1, "lin"), (3600, 1.1, "hold")])]
    idle += osc(center_ring.id, "opacity", 360, 0.5, 1.0)
    return scene_component(k, "Hours observing", [art], [copy, counter],
                           dict(enterF=(134, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(3600, idle)))


def scene5():
    k = 5
    P5 = [(56, 402), (104, 334), (84, 256), (150, 206), (226, 236), (262, 170), (316, 124),
          (300, 298), (238, 352), (166, 398), (350, 228)]
    E5 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (4, 7), (7, 8), (8, 9), (9, 1), (7, 10)]
    grid = [shape("Great Circle A", ellipse(640, 300), stroke(BLUE, 0.13, 1), x=195, y=380, rotation=-0.35),
            shape("Great Circle B", ellipse(520, 760), stroke(BLUE, 0.11, 1), x=330, y=300, rotation=0.2),
            shape("Great Circle C", ellipse(900, 520), stroke(BLUE, 0.09, 1), x=40, y=180, rotation=0.5)]
    glabels = [text("Dec +30", 40, 140, 60, 14, tstyle("mono", 9, ICE, 0.45, ls=1.2), "+30°", None, align="left", wrap="noWrap"),
               text("Dec +60", 300, 440, 60, 14, tstyle("mono", 9, ICE, 0.45, ls=1.2), "+60°", None, align="left", wrap="noWrap"),
               text("RA 14h", 28, 452, 80, 14, tstyle("mono", 9, ICE, 0.45, ls=1.2), "RA 14h", None, align="left", wrap="noWrap")]
    lines, ltrims = [], []
    for a, b in E5:
        (x0, y0), (x1, y1) = P5[a], P5[b]
        t = trim(0.0, 1.0, 0.0)
        ltrims.append(t)
        lines.append(shape(f"Link {a}-{b}", poly([(x0, y0), (x1, y1)], closed=False), stroke(ICE, 0.55, 1.0, effects=[t], cap="round")))
    pts = []
    for i, (x, y) in enumerate(P5):
        col = AMBER if i in (3, 6, 8) else ICE
        pts.append(node(f"Point {i}", dot("Core", 0, 0, 6.5 if col == AMBER else 5.2, col, 1.0, glow=7, glow_a=0.7),
                        shape("Halo Ring", ellipse(17), stroke(col, 0.35, 1)), x=x, y=y))
    art = node("S5 Art", *pts, *lines, *glabels, *grid, x=0, y=0)
    copy, counter, c = metric_copy(k, "constellationsLogged", "left")
    eF = copy_enter(c, 26)
    for g in grid:
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (50, 1.0, "hold")])]
    eF += [(g.id, "opacity", [(0, 0.0, "hold"), (70, 0.0, "out"), (96, 1.0, "hold")]) for g in glabels]
    order = list(range(len(P5)))
    for i in order:
        f0 = 20 + i * 6
        eF += pop(pts[i].id, f0, f0 + 18, 0.0, "back")
    for j, (a, b) in enumerate(E5):
        f0 = 22 + max(a, b) * 6
        eF += [(ltrims[j].id, "end", [(0, 0.0, "hold"), (f0, 0.0, (0.45, 0.0, 0.25, 1.0)), (f0 + 18, 1.0, "hold")])]
    eB = copy_enter_back(c)
    for j, t in enumerate(ltrims):
        eB += [(t.id, "start", [(0, 1.0, "hold"), (2, 1.0, "out"), (30, 0.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.9, -8)
    for j, t in enumerate(ltrims):
        xF += [(t.id, "start", [(0, 0.0, "in"), (24, 1.0, "hold")])]
    xB = copy_exit(c, 22) + art_exit(art.id, 1.08, 8)
    idle = []
    for i, p in enumerate(pts):
        idle += osc(p.id, "opacity", 240, 0.62, 1.0, phase=(i * 0.37) % 1)
    idle += [(grid[0].id, "rotation", [(0, -0.35, "sine"), (900, -0.3, "sine"), (1800, -0.35, "hold")])]
    return scene_component(k, "Constellations logged", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(1800, idle)))


def meteor(name, length, width, color=ICE, head=6.0):
    tail = shape("Trail", poly([(0, -width / 2), (0, width / 2), (-length, 0)], closed=True),
                 fill(paint=linear([(0, color, 0.95), (0.35, color, 0.4), (1, color, 0.0)], 0, 0, -length, 0)))
    tail_glow = shape("Trail Glow", poly([(0, -width * 1.6), (0, width * 1.6), (-length * 0.6, 0)], closed=True),
                      fill(paint=linear([(0, BLUE, 0.5), (1, BLUE, 0.0)], 0, 0, -length * 0.6, 0), feather=6))
    return node(name, dot("Head", 0, 0, head, WHITE, 1.0, glow=head * 1.5, glow_a=0.8), tail, tail_glow, x=0, y=0)


def scene6():
    k = 6
    wx, wy, ww, wh = 195.0, 286.0, 334.0, 344.0
    ang = math.radians(146)  # travel direction: down-left
    ux, uy = math.cos(ang), math.sin(ang)
    frame = shape("Window Frame", rect(ww, wh, r=20), stroke(ICE, 0.2, 1), x=wx, y=wy)
    corners = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            corners.append(shape("Corner", poly([(sx * (ww / 2 - 14), sy * (wh / 2 - 4)), (sx * (ww / 2 - 4), sy * (wh / 2 - 4)),
                                                   (sx * (ww / 2 - 4), sy * (wh / 2 - 14))], closed=False),
                                 stroke(AMBER, 0.75, 1.2), x=wx, y=wy))
    win_bg = shape("Window Sky", rect(ww, wh, r=20), fill(paint=linear([(0, "0F2747", 1), (1, "081526", 1)], 0, -wh / 2, 0, wh / 2)),
                   x=wx, y=wy)
    clip = shape("Window Clip", rect(ww, wh, r=20), x=wx, y=wy)
    faint = starfield("Window Stars", 24, wx, wy, 0, rect_wh=(ww - 20, wh - 20), dmin=0.8, dmax=2.0, amin=0.3, amax=0.8, groups=2)
    radiant = (wx + 130, wy - 140)
    # bounded pool: 5 meteors, re-used by the idle loop
    specs = [  # (offset across, length, width, start frame idle, colour)
        (0, 190, 3.2, 0, ICE), (-60, 120, 2.0, 52, BLUE), (52, 150, 2.4, 104, AMBER), (-120, 90, 1.6, 150, ICE),
        (100, 110, 1.8, 196, ICE)]
    pool = []
    for i, (off, L, wd, f0, col) in enumerate(specs):
        m = meteor(f"Meteor {i + 1}", L, wd, col, head=4.0 + wd)
        # each meteor sits on its own lane rotated into the travel direction
        lane = node(f"Lane {i + 1}", m, x=radiant[0] - uy * off * 0.6, y=radiant[1] + ux * off * 0.6, rotation=ang)
        pool.append((lane, m, L, f0))
    met_grp = node("Meteor Pool", *[p[0] for p in pool], El("ClippingShape", sourceId=clip.id, name="Clip"), x=0, y=0)
    sky_grp = node("Window Sky Group", *faint, win_bg, El("ClippingShape", sourceId=clip.id, name="Clip"), x=0, y=0)
    hero_flash = shape("Hero Afterglow", rect(330, 6, ox=1.0), fill(ICE, 0.22, feather=10), x=radiant[0], y=radiant[1],
                       rotation=ang, opacity=0.0)
    # long-exposure memory: faint persistent trails left by the meteors you counted (bounded: 7 strokes)
    trails, ttr = [], []
    for j, (off, L, al) in enumerate(((0, 300, 0.30), (-60, 210, 0.22), (52, 250, 0.24), (-120, 170, 0.18), (100, 190, 0.2),
                                      (-28, 120, 0.16), (150, 140, 0.14))):
        t = trim(0.0, 1.0, 0.0)
        ttr.append(t)
        x0, y0 = radiant[0] - uy * off * 0.6 + ux * 40, radiant[1] + ux * off * 0.6 + uy * 40
        trails.append(shape(f"Exposure Trail {j}", poly([(x0, y0), (x0 + ux * L, y0 + uy * L)], closed=False),
                            stroke(ICE if j % 3 else AMBER, al, 1.0, effects=[t], cap="round")))
    trail_grp = node("Exposure Trails", *trails, El("ClippingShape", sourceId=clip.id, name="Clip"), x=0, y=0)
    radiant_glow = shape("Radiant", ellipse(90), fill(AMBER, 0.14, feather=30), x=radiant[0], y=radiant[1])
    art = node("S6 Art", *corners, frame, met_grp, hero_flash, trail_grp, radiant_glow, sky_grp, clip, x=0, y=0)
    for lane, m, L, f0 in pool:
        REST[(m.id, "x")] = 0.0
        REST[(m.id, "opacity")] = 0.0
        m.attrs["opacity"] = 0.0
    copy, counter, c = metric_copy(k, "meteorSightings", "right")
    eF = copy_enter(c, 26)
    eF += [(sky_grp.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (30, 1.0, "hold")]),
           (frame.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (24, REST[(frame.id, "opacity")], "hold")])]
    for g in corners:
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (14, 0.0, "out"), (34, 1.0, "hold")])]
    travel = 560
    # hero meteor + two followers synchronised with the count's beat
    for idx, (lane, m, L, f0) in enumerate(pool[:3]):
        s = 22 + idx * 18
        dur = 38 - idx * 4
        eF += [(m.id, "x", [(0, -20, "hold"), (s, -20, (0.3, 0.2, 0.6, 1.0)), (s + dur, travel, "hold")]),
               (m.id, "opacity", [(0, 0.0, "hold"), (s, 0.0, "lin"), (s + 4, 1.0, "hold"), (s + dur - 10, 1.0, "lin"), (s + dur, 0.0, "hold")])]
    eF += [(hero_flash.id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "out"), (52, 1.0, "in"), (110, 0.0, "hold")])]
    for j, t in enumerate(ttr):
        f0 = 30 + j * 9
        eF += [(t.id, "end", [(0, 0.0, "hold"), (f0, 0.0, (0.3, 0.2, 0.4, 1.0)), (f0 + 26, 1.0, "hold")])]
    eF += [(radiant_glow.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (60, 1.0, "hold")])]
    eB = copy_enter_back(c) + [(sky_grp.id, "opacity", [(0, 0.0, "hold"), (2, 0.0, "out"), (24, 1.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.9, -6)
    xB = copy_exit(c, 22) + art_exit(art.id, 1.08, 6)
    idle = []
    loop = 250
    idle += osc(radiant_glow.id, "opacity", loop, 0.7, 1.0)
    for lane, m, L, f0 in pool:
        dur = 46
        s = f0 % loop
        keys_x = [(0, -20, "hold"), (s, -20, (0.3, 0.2, 0.6, 1.0)), (s + dur, travel, "hold"), (loop, -20, "hold")]
        keys_o = [(0, 0.0, "hold"), (s, 0.0, "lin"), (s + 5, 1.0, "hold"), (s + dur - 12, 1.0, "lin"), (s + dur, 0.0, "hold"), (loop, 0.0, "hold")]
        idle += [(m.id, "x", keys_x), (m.id, "opacity", keys_o)]
    for i, g in enumerate(faint):
        idle += osc(g.id, "opacity", 180, 0.6, 1.0, phase=i / 2)
    return scene_component(k, "Meteors spotted", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(loop, idle)))


def scene7():
    k = 7
    cx, cy, d = 182.0, 296.0, 256.0
    lit_paint = lambda: radial([(0, "E6F4F6", 1), (0.5, "B3CFE0", 1), (1, "5E80A8", 1)], d * 0.75, d * 0.18, -d * 0.12)
    dark = "0C1F38"
    litB = shape("Lit Gibbous", ellipse(0.0001, d), fill(paint=lit_paint()), x=cx, y=cy)
    half_dark = shape("Dark Half", rect(d / 2 + 1, d + 2, ox=1.0, oy=0.5), fill(dark, 1.0), x=cx, y=cy)
    darkA = shape("Shadow Crescent", ellipse(d, d), fill(dark, 1.0), x=cx, y=cy)
    lit = shape("Lit Disk", ellipse(d), fill(paint=lit_paint()), x=cx, y=cy)
    craters = []
    cr = [(-40, -50, 34), (30, -20, 22), (55, 40, 40), (-20, 60, 26), (-70, 10, 18), (10, -84, 14), (80, -40, 16),
          (-50, 95, 12), (90, 80, 10)]
    for i, (dx, dy, cd) in enumerate(cr):
        craters.append(shape(f"Crater {i}", ellipse(cd, cd * 0.92), fill("3A5C86", 0.16), stroke(ICE, 0.14, 0.8), x=cx + dx, y=cy + dy))
    maria = shape("Mare", poly([(cx - 60, cy - 10, "c", 0.4, 30), (cx + 10, cy - 40, "c", 0.2, 34), (cx + 40, cy + 20, "c", 1.9, 30),
                                (cx - 30, cy + 40, "c", 3.4, 30)], closed=True), fill("6F8FB5", 0.16, feather=10))
    clip = shape("Moon Clip", ellipse(d), x=cx, y=cy)
    moon_body = node("Moon Body", *craters, maria, litB, half_dark, darkA, lit, El("ClippingShape", sourceId=clip.id, name="Clip"), x=0, y=0)
    halo = shape("Moon Halo", ellipse(d + 60), fill(ICE, 0.12, feather=40), x=cx, y=cy)
    rim = shape("Moon Rim", ellipse(d + 2), stroke(ICE, 0.4, 1), x=cx, y=cy)
    orbit = shape("Session Orbit", ellipse(d + 96), stroke(ICE, 0.18, 1, effects=[dash(1, 6)]), x=cx, y=cy)
    glyphs = []
    ng = 9
    for i in range(ng):
        a = math.radians(-200 + i * 28)
        gx, gy = cx + (d / 2 + 48) * math.cos(a), cy + (d / 2 + 48) * math.sin(a)
        frac = i / (ng - 1)
        glyphs.append(node(f"Session {i + 1}", dot("Lit", 0, 0, 11, ICE, 0.95),
                           shape("Shade", ellipse(11), fill(MID, 1.0), x=-11 * (1 - frac) + 0.0, opacity=1.0 - frac * 0.9),
                           shape("Ring", ellipse(15), stroke(ICE, 0.3, 1)), x=gx, y=gy))
    art = node("S7 Art", *glyphs, orbit, rim, moon_body, clip, halo, x=0, y=0)
    copy, counter, c = metric_copy(k, "moonSessions", "right")
    # successive masked illumination: new -> crescent -> half -> gibbous (settled)
    darkA_w_rest = 0.0001
    REST[(darkA.id, "width")] = 0.0001
    darkA[0] if False else None
    for ch in darkA.children:
        if ch.tag == "Ellipse":
            ch.attrs["width"] = 0.0001
            REST[(ch.id, "width")] = 0.0001
            darkA_e = ch
    for ch in litB.children:
        if ch.tag == "Ellipse":
            ch.attrs["width"] = 168.0
            REST[(ch.id, "width")] = 168.0
            litB_e = ch
    eF = copy_enter(c, 26)
    eF += [(darkA_e.id, "width", [(0, d, "hold"), (18, d, (0.45, 0.0, 0.55, 1.0)), (62, 0.0001, "hold")]),
           (litB_e.id, "width", [(0, 0.0001, "hold"), (62, 0.0001, (0.3, 0.0, 0.3, 1.0)), (96, 168.0, "hold")]),
           (moon_body.id, "rotation", [(0, -0.25, "hold"), (10, -0.25, "out"), (100, 0.0, "hold")]),
           (halo.id, "opacity", [(0, 0.0, "hold"), (30, 0.0, "out"), (100, 1.0, "hold")]),
           (orbit.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (40, REST[(orbit.id, "opacity")], "hold")])]
    for i, g in enumerate(glyphs):
        f0 = 26 + i * 7
        eF += pop(g.id, f0, f0 + 16, 0.2, "back")
    eB = copy_enter_back(c) + [(darkA_e.id, "width", [(0, 0.0001, "hold")]),
                               (litB_e.id, "width", [(0, d, "hold"), (2, d, "out"), (40, 168.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.86, -6) + [(litB_e.id, "width", [(0, 168.0, "in"), (30, d, "hold")])]
    xB = copy_exit(c, 22) + art_exit(art.id, 1.08, 6) + [(darkA_e.id, "width", [(0, 0.0001, "in"), (30, 120, "hold")])]
    idle = osc(halo.id, "opacity", 480, 0.7, 1.0) + [(moon_body.id, "rotation", [(0, 0.0, "sine"), (600, 0.03, "sine"), (1200, 0.0, "hold")])]
    idle += [(orbit.id, "rotation", [(0, 0.0, "lin"), (1200, 2 * math.pi / 16, "hold")])]
    return scene_component(k, "Lunar sessions", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(1200, idle)))


def scene8():
    k = 8
    cx, cy = 195.0, 288.0
    pw, ph = 296.0, 336.0
    paper = shape("Sheet", rect(pw, ph, r=8), fill(paint=linear([(0, "102540", 1), (1, "0A1A30", 1)], 0, -ph / 2, 0, ph / 2)),
                  stroke(ICE, 0.22, 1))
    margin = shape("Margin", rect(pw - 28, ph - 28, r=4), stroke(ICE, 0.12, 1, effects=[dash(3, 4)]))
    regs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            regs.append(node("Registration", shape("h", rect(10, 1), fill(AMBER, 0.7)), shape("v", rect(1, 10), fill(AMBER, 0.7)),
                             x=sx * (pw / 2 - 22), y=sy * (ph / 2 - 22)))
    ann = text("Annotation", -pw / 2 + 22, ph / 2 - 40, 200, 14, tstyle("mono", 9, ICE, 0.55, ls=1.6), "FIG. 08 · NEBULA STUDY",
               None, align="left", wrap="noWrap")
    ann2 = text("Annotation 2", pw / 2 - 22, -ph / 2 + 26, 120, 14, tstyle("mono", 9, ICE, 0.55, ls=1.6), "f/8 · 2026",
                None, align="right", wrap="noWrap")
    # nebula study strokes (invented, decorative)
    strokes_def = []
    rr = random.Random(8)
    for i in range(7):  # swirling contour lines
        pts = []
        base_r = 30 + i * 13
        for j in range(9):
            a = j * 0.78 + i * 0.35
            rad = base_r * (1 + 0.18 * math.sin(j * 1.3 + i))
            pts.append((rad * math.cos(a) * 1.15, rad * math.sin(a) * 0.82 - 8))
        col = [ICE, ICE, BLUE, ICE, AMBER, BLUE, ICE][i]
        strokes_def.append((pts, col, 0.75 if col == ICE else 0.7, 1.1 if i % 2 else 1.5))
    hatch = []
    for j in range(14):
        x0 = -70 + j * 9
        hatch.append(([(x0, 70), (x0 + 22, 40)], ICE, 0.35, 0.9))
    sketch = []
    trims8 = []
    for i, (pts, col, a, w) in enumerate(strokes_def + hatch):
        t = trim(0.0, 1.0, 0.0)
        trims8.append(t)
        pth = smooth_path(pts) if len(pts) > 2 else poly(pts, closed=False)
        sketch.append(shape(f"Stroke {i + 1}", pth, stroke(col, a, w, effects=[t], cap="round")))
    crosses = []
    for (sx, sy, s) in ((-96, -110, 7), (104, -60, 9), (80, 96, 6), (-110, 40, 5), (20, -126, 6)):
        crosses.append(node("Star Mark", shape("h", rect(s * 2, 1.1), fill(WHITE, 0.85)), shape("v", rect(1.1, s * 2), fill(WHITE, 0.85)),
                            x=sx, y=sy))
    glow = shape("Nebula Wash", ellipse(200, 140), fill(BLUE, 0.16, feather=36), y=-8)
    glow2 = shape("Nebula Warm", ellipse(90, 60), fill(AMBER, 0.12, feather=24), x=30, y=10)
    sheet = node("Sketch Sheet", *crosses, *sketch, ann, ann2, *regs, glow2, glow, margin, paper, x=cx, y=cy, rotation=-0.045)
    art = node("S8 Art", sheet, x=0, y=0)
    copy, counter, c = metric_copy(k, "sketchesMade", "left")
    eF = copy_enter(c, 26)
    eF += [(sheet.id, "y", [(0, cy + 44, "hold"), (4, cy + 44, "back"), (44, cy, "hold")]),
           (sheet.id, "rotation", [(0, -0.16, "hold"), (4, -0.16, "back"), (50, -0.045, "hold")]),
           (sheet.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (22, 1.0, "hold")])]
    for i, t in enumerate(trims8):
        f0 = 24 + (i * 5 if i < 7 else 60 + (i - 7) * 2.5)
        eF += [(t.id, "end", [(0, 0.0, "hold"), (f0, 0.0, (0.4, 0.0, 0.3, 1.0)), (f0 + 34, 1.0, "hold")])]
    eF += [(glow.id, "opacity", [(0, 0.0, "hold"), (50, 0.0, "out"), (110, 1.0, "hold")]),
           (glow2.id, "opacity", [(0, 0.0, "hold"), (70, 0.0, "out"), (120, 1.0, "hold")])]
    for i, cc in enumerate(crosses):
        eF += pop(cc.id, 80 + i * 6, 96 + i * 6, 0.0, "back")
    eB = copy_enter_back(c) + [(sheet.id, "rotation", [(0, 0.08, "hold"), (2, 0.08, "back"), (44, -0.045, "hold")]),
                               (sheet.id, "opacity", [(0, 0.0, "hold"), (2, 0.0, "out"), (20, 1.0, "hold")])]
    xF = copy_exit(c) + [(sheet.id, "y", [(0, cy, "in"), (34, cy - 30, "hold")]),
                         (sheet.id, "rotation", [(0, -0.045, "in"), (34, 0.06, "hold")]),
                         (sheet.id, "opacity", [(0, 1.0, "in"), (34, 0.0, "hold")])]
    xB = copy_exit(c, 22) + [(sheet.id, "y", [(0, cy, "in"), (34, cy + 40, "hold")]),
                             (sheet.id, "opacity", [(0, 1.0, "in"), (34, 0.0, "hold")])]
    idle = [(sheet.id, "y", [(0, cy, "sine"), (240, cy - 3, "sine"), (480, cy, "hold")]),
            (sheet.id, "rotation", [(0, -0.045, "sine"), (240, -0.035, "sine"), (480, -0.045, "hold")])]
    idle += osc(glow.id, "opacity", 480, 0.7, 1.0)
    return scene_component(k, "Sky sketches", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(480, idle)))


def scene9():
    k = 9
    cx, cy = 195.0, 290.0
    em = []
    eF, idle = [], []

    def slot_node(i, *children):
        n_ = node(f"Emblem {i}", *children, x=cx, y=cy)
        n_.add(bind("personaSlot", KEY_OPACITY, cv_eq(i)))
        return n_

    # 0 Deep Sky Dreamer: nested nebula aperture
    neb = [shape("Nebula A", ellipse(230, 160), fill(ICE, 0.26, feather=38), rotation=0.4),
           shape("Nebula B", ellipse(150, 110), fill(BLUE, 0.45, feather=28), x=-24, y=12, rotation=-0.6),
           shape("Nebula C", ellipse(80, 56), fill(AMBER, 0.32, feather=16), x=26, y=-16),
           shape("Nebula Core", ellipse(26), fill(WHITE, 0.55, feather=10), x=4, y=-2)]
    rings0 = []
    for j, (dd, dir_) in enumerate(((236, 1), (176, -1), (118, 1))):
        rings0.append(node(f"Nested Ring {j}",
                           shape("Ring", ellipse(dd), stroke(ICE, 0.5 - j * 0.08, 1.0)),
                           shape("Ticks", ellipse(dd + 10), stroke(ICE, 0.35, 5, effects=[dash(0.8, math.pi * (dd + 10) / (24 + 12 * j) - 0.8)])),
                           star4("Mark", dd / 2, 0, 8, AMBER, glow=3), x=0, y=0))
    inner_ap, inner_remap = aperture_instance("Inner Aperture", 0, 0, 0.26, 1.0)
    e0 = slot_node(0, inner_ap, *rings0, *neb)
    for j, rg in enumerate(rings0):
        f0 = 40 + j * 10
        eF += pop(rg.id, f0, f0 + 34, 0.25 + j * 0.2, "back")
        idle += [(rg.id, "rotation", [(0, 0.0, "lin"), (1440, (1 if j % 2 == 0 else -1) * 2 * math.pi / (2 + j), "hold")])]
    for j, nb in enumerate(neb):
        eF += pop(nb.id, 30 + j * 8, 90 + j * 8, 0.3, "out")
    eF += [(inner_remap.id, "time", [(0, 0.0, "hold"), (60, 0.0, "out"), (100, 1.0, "hold")])]
    em.append(e0)

    # 1 Lunar Archivist: lunar disk with orbiting phases
    disk_fill = solid(ICE, 1.0)
    disk_fill.add(bind("personaColor", KEY_COLOR))
    ldisk = node("Lunar Disk",
                 shape("Disk Glow", ellipse(186), fill(BLUE, 0.3, feather=26)),
                 *[shape(f"Crater {i}", ellipse(s), fill(MID, 0.22), x=dx, y=dy) for i, (dx, dy, s) in
                   enumerate(((-30, -26, 30), (24, 10, 22), (-8, 44, 18), (40, -40, 12), (-50, 20, 10)))],
                 shape("Terminator", ellipse(172), fill(paint=linear([(0, MID, 0.0), (0.55, MID, 0.0), (1, MID, 0.75)], -86, 0, 86, 0))),
                 shape("Disk", ellipse(172), El("Fill", disk_fill, name="Persona Fill")),
                 shape("Disk Rim", ellipse(174), stroke(ICE, 0.5, 1.2)),
                 x=0, y=0)
    orbit1 = node("Phase Orbit", shape("Orbit Path", ellipse(268, 268), stroke(ICE, 0.25, 1, effects=[dash(1, 5)])), x=0, y=0)
    for j in range(6):
        a = j * math.pi / 3
        orbit1.add(node(f"Phase {j}", dot("Lit", 0, 0, 14, ICE, 0.95),
                        shape("Shade", ellipse(14), fill(MID, 1.0), x=7 * math.cos(j * 1.1)),
                        x=134 * math.cos(a), y=134 * math.sin(a)))
    e1 = slot_node(1, orbit1, ldisk)
    eF += [(ldisk.id, "y", [(0, 110, "hold"), (30, 110, "back"), (80, 0, "hold")]),
           (ldisk.id, "opacity", [(0, 0.0, "hold"), (30, 0.0, "out"), (50, 1.0, "hold")]),
           (orbit1.id, "rotation", [(0, -2.4, "hold"), (40, -2.4, (0.2, 0.9, 0.3, 1.0)), (110, 0.0, "hold")]),
           (orbit1.id, "scaleX", [(0, 0.3, "hold"), (40, 0.3, "back"), (100, 1.0, "hold")]),
           (orbit1.id, "scaleY", [(0, 0.3, "hold"), (40, 0.3, "back"), (100, 1.0, "hold")]),
           (orbit1.id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "out"), (60, 1.0, "hold")])]
    idle += [(orbit1.id, "rotation", [(0, 0.0, "lin"), (1440, 2 * math.pi, "hold")])]
    em.append(e1)

    # 2 Planet Tracker: orbital reticle
    o_tr = trim(0.0, 1.0, 0.0)
    o_tr2 = trim(0.0, 1.0, 0.25)
    planet_fill = solid(AMBER, 1.0)
    planet_fill.add(bind("personaColor", KEY_COLOR))
    def orbit_xy(th, r=128.0, sq=0.42, tilt=-0.32):
        x, y = r * math.cos(th), r * sq * math.sin(th)
        return x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt)
    px0, py0 = orbit_xy(0.6)
    planet = node("Planet", shape("Planet Glow", ellipse(44), fill(AMBER, 0.4, feather=14)),
                  shape("Planet Body", ellipse(34), El("Fill", planet_fill, name="Persona Fill")),
                  shape("Planet Ring", ellipse(58, 12), stroke(ICE, 0.7, 1.2), rotation=-0.3),
                  x=px0, y=py0)
    orbit_plane = node("Orbit Plane", shape("Orbit", ellipse(256), stroke(AMBER, 0.65, 1.2, effects=[o_tr])),
                       x=0, y=0, scaleY=0.42, rotation=-0.32)
    arm = planet

    def planet_path(th0, th1, f0, f1, steps, ease_mid="lin"):
        kx, ky = [], []
        for i in range(steps + 1):
            u = i / steps
            # ease-out progress along the orbit for the entrance; linear for the loop
            e = 1 - (1 - u) ** 3 if ease_mid == "out" else u
            th = th0 + (th1 - th0) * e
            x, y = orbit_xy(th)
            f = f0 + (f1 - f0) * u
            kx.append((f, x, "lin")); ky.append((f, y, "lin"))
        return [(planet.id, "x", kx), (planet.id, "y", ky)]
    reticle2 = node("Tracker Reticle",
                    shape("Ring", ellipse(200), stroke(ICE, 0.45, 1)),
                    shape("Ring2", ellipse(290), stroke(ICE, 0.25, 1, effects=[o_tr2, dash(2, 6)])),
                    *[shape(f"Hair {i}", rect(1, 60), fill(ICE, 0.5), x=130 * math.cos(i * math.pi / 2), y=130 * math.sin(i * math.pi / 2),
                            rotation=i * math.pi / 2) for i in range(4)],
                    *[star4(f"Pin {i}", 165 * math.cos(i * math.pi / 2 + math.pi / 4), 165 * math.sin(i * math.pi / 2 + math.pi / 4), 8, AMBER, glow=3)
                      for i in range(4)],
                    x=0, y=0)
    e2 = slot_node(2, planet, orbit_plane, reticle2, shape("Core", ellipse(10), fill(ICE, 0.9)))
    eF += [(reticle2.id, "rotation", [(0, 0.7, "hold"), (30, 0.7, (0.2, 1.35, 0.4, 1.0)), (76, 0.0, "hold")]),
           (reticle2.id, "scaleX", [(0, 1.4, "hold"), (30, 1.4, "out"), (70, 1.0, "hold")]),
           (reticle2.id, "scaleY", [(0, 1.4, "hold"), (30, 1.4, "out"), (70, 1.0, "hold")]),
           (reticle2.id, "opacity", [(0, 0.0, "hold"), (30, 0.0, "out"), (50, 1.0, "hold")]),
           (o_tr.id, "end", [(0, 0.0, "hold"), (44, 0.0, "out"), (96, 1.0, "hold")]),
           (o_tr2.id, "end", [(0, 0.0, "hold"), (50, 0.0, "out"), (104, 1.0, "hold")]),
           (arm.id, "opacity", [(0, 0.0, "hold"), (44, 0.0, "out"), (60, 1.0, "hold")])]
    eF += [(t[0], t[1], [(0, t[2][0][1], "hold")] + t[2]) for t in planet_path(-2.6, 0.6, 44, 104, 12, "out")]
    idle += planet_path(0.6, 0.6 + 2 * math.pi, 0, 1440, 36)
    em.append(e2)

    # 3 Meteor Watcher: meteor arc around a midnight (persona colour) disk
    m_tr = trim(0.0, 0.62, 0.55)
    m_tr_g = trim(0.0, 0.62, 0.55)
    arc_paint = linear([(0, ICE, 0.0), (0.5, ICE, 0.7), (1, AMBER, 1.0)], -140, 0, 140, 0)
    mw_fill = solid(MID, 1.0)
    mw_fill.add(bind("personaColor", KEY_COLOR))
    head = node("Arc Head", dot("Head", 0, 0, 12, WHITE, 1.0, glow=14, glow_a=0.9), x=0, y=0, rotation=0.0)
    head_arm = node("Arc Head Arm", node("Head Pos", dot("Head", 0, 0, 11, WHITE, 1.0, glow=14, glow_a=0.9), x=140, y=0),
                    x=0, y=0, rotation=2 * math.pi * (0.55 + 0.62))
    e3 = slot_node(3,
                   head_arm,
                   shape("Meteor Arc", ellipse(280), stroke(w=3.0, paint=arc_paint, effects=[m_tr], cap="round")),
                   shape("Meteor Arc Glow", ellipse(280), stroke(AMBER, 0.5, 10, feather=10, effects=[m_tr_g], cap="round")),
                   node("Eclipse",
                        shape("Eclipse Corona", ellipse(176), fill(ICE, 0.35, feather=24)),
                        shape("Eclipse Rim", ellipse(150), stroke(ICE, 0.75, 1.4)),
                        shape("Eclipse Disk", ellipse(148), El("Fill", mw_fill, name="Persona Fill")), x=0, y=0),
                   *[node(f"Streak {j}", meteor(f"Mini {j}", 70 - j * 12, 1.6, ICE, head=3.0), x=-40 + j * 38, y=-96 + j * 22,
                          rotation=math.radians(150)) for j in range(3)])
    eclipse = [c_ for c_ in e3.children if c_.attrs.get("name") == "Eclipse"][0]
    eF += [(m_tr.id, "end", [(0, 0.0, "hold"), (36, 0.0, (0.5, 0.0, 0.15, 1.0)), (70, 0.62, "hold")]),
           (m_tr_g.id, "end", [(0, 0.0, "hold"), (36, 0.0, (0.5, 0.0, 0.15, 1.0)), (70, 0.62, "hold")]),
           (head_arm.id, "rotation", [(0, 2 * math.pi * 0.55, "hold"), (36, 2 * math.pi * 0.55, (0.5, 0.0, 0.15, 1.0)),
                                      (70, 2 * math.pi * 1.17, "hold")]),
           (eclipse.id, "scaleX", [(0, 0.2, "hold"), (50, 0.2, "back"), (92, 1.0, "hold")]),
           (eclipse.id, "scaleY", [(0, 0.2, "hold"), (50, 0.2, "back"), (92, 1.0, "hold")])]
    idle += [(m_tr.id, "offset", [(0, 0.55, "sine"), (720, 0.58, "sine"), (1440, 0.55, "hold")]),
             (m_tr_g.id, "offset", [(0, 0.55, "sine"), (720, 0.58, "sine"), (1440, 0.55, "hold")]),
             (head_arm.id, "rotation", [(0, 2 * math.pi * 1.17, "sine"), (720, 2 * math.pi * 1.20, "sine"), (1440, 2 * math.pi * 1.17, "hold")])]
    em.append(e3)

    emblems = node("Emblems", *em, x=0, y=0)
    REST[(head.id, "rotation")] = 0.0
    # copy
    lab = text("S9 Label", 195, 486, 334, 18, tstyle("mono", 11, ICE, 0.75, ls=3.0), "", tb("personaLabel"),
               align="center", wrap="noWrap")
    title = text("S9 Title", 195, 510, 350, 96, tstyle("sg", 40, WHITE, weight=400, lh=46, ls=-0.8), "", tb("personaName"),
                 align="center")
    spark_fill = solid(AMBER, 1.0)
    spark_fill.add(bind("personaColor", KEY_COLOR))
    divp = node("S9 Divider",
                shape("Spark Ring", ellipse(18), stroke(ICE, 0.6, 1)),
                shape("Spark", El("Star", width=14.0, height=14.0, points=4, innerRadius=0.2, name="Path"), El("Fill", spark_fill, name="Persona Fill")),
                shape("Rule L", rect(64, 1, ox=1.0), fill(AMBER, 0.55), x=-16),
                shape("Rule R", rect(64, 1, ox=0.0), fill(AMBER, 0.55), x=16), x=195, y=622)
    desc = text("S9 Description", 195, 642, 334, 52, tstyle("mono", 13.5, ICE, 0.85, lh=20, ls=0.6), "", tb("personaDescription"),
                align="center")
    copy = node("S9 Copy", lab, title, divp, desc, x=0, y=0)
    art = node("S9 Art", emblems, x=0, y=0)
    eF += fade_up(lab.id, 70, 96, 10) + fade_up(title.id, 82, 118, 22) + fade_up(desc.id, 104, 134, 10)
    eF += [(divp.id, "scaleX", [(0, 0.0, "hold"), (96, 0.0, "back"), (124, 1.0, "hold")]),
           (title.id, "scaleX", [(0, 0.94, "hold"), (82, 0.94, "out"), (130, 1.0, "hold")]),
           (art.id, "opacity", [(0, 0.0, "hold"), (24, 0.0, "out"), (44, 1.0, "hold")])]
    eB = [(art.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (30, 1.0, "hold")])]
    for i, kk in enumerate((lab, title, desc)):
        eB += fade_up(kk.id, 16 + i * 4, 42 + i * 4, -16)
    xF = art_exit(art.id, 0.8, 0) + fade_out(copy.id, 0, 14, -20)
    xB = art_exit(art.id, 1.15, 0, f1=24) + fade_out(copy.id, 0, 14, 20)
    return scene_component(k, "Persona reveal", [art], [copy],
                           dict(enterF=(140, eF), enterB=(50, eB), exitF=(36, xF), exitB=(36, xB), idle=(1440, idle)))


STATS10 = [("observationNights", 2), ("objectsLogged", 3), ("observationHours", 4), ("constellationsLogged", 5),
           ("meteorSightings", 6)]


def scene10():
    k = 10
    cx = 195.0
    top, bottom = 96.0, 640.0
    ch = bottom - top
    cy = (top + bottom) / 2
    card_tr = trim(0.0, 1.0, 0.0)
    card_bg = shape("Card", rect(334, ch, r=22),
                    fill(paint=linear([(0, "0F2644", 1), (0.6, "0B1C33", 1), (1, "091629", 1)], 0, -ch / 2, 0, ch / 2)), x=cx, y=cy)
    card_edge = shape("Card Edge", rect(334, ch, r=22), stroke(ICE, 0.3, 1, effects=[card_tr]), x=cx, y=cy)
    card_inner = shape("Card Inner", rect(314, ch - 20, r=14), stroke(BLUE, 0.18, 1, effects=[dash(2, 5)]), x=cx, y=cy)
    card_glow = shape("Card Glow", rect(334, ch, r=22), fill(BLUE, 0.16, feather=30), x=cx, y=cy + 10)
    # data ring around the seal (seal itself = traveling motif from the main artboard)
    seal_y = 178.0
    ring_arcs = []
    cols = [BLUE, ICE, AMBER, BLUE, ICE]
    for j in range(5):
        t = trim(0.0, 0.16, j * 0.2 + 0.02)
        ring_arcs.append((shape(f"Data Arc {j}", ellipse(104), stroke(cols[j], 0.9, 3, effects=[t], cap="round"), x=cx, y=seal_y), t))
    ring_grp = node("Data Ring", *[a for a, _ in ring_arcs], x=0, y=0)
    wm = text("Card Wordmark", cx, 238, 300, 26, tstyle("sg", 20, ICE, weight=500, ls=3.0), "NOCTURNE", None, align="center", wrap="noWrap")
    yr = text("Card Year", cx, 264, 200, 16, tstyle("mono", 11, AMBER, 0.95, ls=4.0), "", tb("year", CV_INT_TEXT), align="center", wrap="noWrap")
    nm = text("Card Name", cx, 286, 290, 16, tstyle("mono", 11, ICE, 0.75, ls=1.5), "", tb("userName"), align="center", wrap="noWrap")
    nm.add(bind("shareIncludeName", KEY_OPACITY, CV_BOOL_NUM))
    p_fill = solid(ICE, 1.0)
    p_fill.add(bind("personaColor", KEY_COLOR))
    persona_blk = node("Card Persona",
                       text("Card Persona Label", 0, 0, 290, 14, tstyle("mono", 9.5, ICE, 0.6, ls=2.4), "", tb("personaLabel"),
                            align="center", wrap="noWrap"),
                       text("Card Persona Name", 0, 18, 290, 30, tstyle("sg", 24, WHITE, weight=400, ls=-0.3), "", tb("personaName"),
                            align="center", wrap="noWrap"),
                       shape("Persona Swatch Ring", ellipse(14), stroke(ICE, 0.7, 1), x=0, y=58),
                       shape("Persona Swatch", ellipse(10), El("Fill", p_fill, name="Persona Fill"), x=0, y=58),
                       x=cx, y=312)
    persona_blk.add(bind("showScreen9", KEY_OPACITY, CV_BOOL_NUM))
    stat_nodes = []
    pos = [(110, 394), (280, 394), (110, 460), (280, 460), (195, 526)]
    for (prop, sk), (sx, sy) in zip(STATS10, pos):
        n_ = node(f"Stat {prop}",
                  text("Value", 0, 0, 160, 40, tstyle("sg", 34, ICE, weight=300, ls=-1, lh=40), "", tb(prop, CV_INT_TEXT),
                       align="center", oy=0.5, overflow="fitFontSize", wrap="noWrap"),
                  text("Unit", 0, 22, 160, 14, tstyle("mono", 9.5, ICE, 0.7, ls=1.6), "", tb(f"screen{sk}Unit"), align="center",
                       wrap="noWrap"),
                  x=sx, y=sy)
        n_.add(bind(f"showScreen{sk}", KEY_OPACITY, CV_BOOL_NUM))
        stat_nodes.append(n_)
    sh = text("Card Headline", cx, 578, 300, 48, tstyle("sg", 18, WHITE, weight=400, lh=23), "", tb("summaryHeadline"), align="center")
    full = node("Card Full", *stat_nodes, sh, persona_blk, x=0, y=0)
    full.add(bind("hasStats", KEY_OPACITY, CV_BOOL_NUM))
    # empty / new-user variant: a small, complete motif (the seal) and a welcoming invitation
    eh = text("Empty Headline", cx, 330, 290, 84, tstyle("sg", 30, WHITE, weight=400, lh=38), "", tb("emptyHeadline"), align="center")
    es = text("Empty Support", cx, 430, 290, 40, tstyle("mono", 13, ICE, 0.8, lh=19), "", tb("emptySupport"), align="center")
    trio = node("First Stars", dot("a", -40, 0, 5, ICE, 1, glow=6), dot("b", 0, -14, 7, AMBER, 1, glow=7), dot("c", 42, 4, 4, ICE, 1, glow=5),
                shape("l1", poly([(-40, 0), (0, -14)], closed=False), stroke(ICE, 0.4, 1)),
                shape("l2", poly([(0, -14), (42, 4)], closed=False), stroke(ICE, 0.4, 1, effects=[dash(2, 4)])), x=cx, y=520)
    empty = node("Card Empty", eh, es, trio, x=0, y=0)
    empty.add(bind("hasStats", KEY_OPACITY, CV_NOTBOOL_NUM))
    card = node("Share Card", wm, yr, nm, full, empty, ring_grp, card_inner, card_edge, card_bg, card_glow, x=0, y=0)
    sup = text("S10 Support", cx, 664, 334, 36, tstyle("mono", 12.5, ICE, 0.78, lh=18, ls=0.4), "", tb("summarySupport"), align="center")
    art = node("S10 Art", card, x=0, y=0)
    copy = node("S10 Copy", sup, x=0, y=0)
    # assembly
    eF = [(card_bg.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (34, 1.0, "hold")]),
          (card_bg.id, "scaleX", [(0, 0.92, "hold"), (6, 0.92, "back"), (44, 1.0, "hold")]),
          (card_bg.id, "scaleY", [(0, 0.86, "hold"), (6, 0.86, "back"), (44, 1.0, "hold")]),
          (card_glow.id, "opacity", [(0, 0.0, "hold"), (20, 0.0, "out"), (80, 1.0, "hold")]),
          (card_tr.id, "end", [(0, 0.0, "hold"), (10, 0.0, (0.5, 0.0, 0.2, 1.0)), (60, 1.0, "hold")]),
          (card_inner.id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "out"), (70, REST[(card_inner.id, "opacity")], "hold")])]
    for j, (a_, t) in enumerate(ring_arcs):
        eF += [(t.id, "end", [(0, 0.0, "hold"), (34 + j * 6, 0.0, "out"), (64 + j * 6, 0.16, "hold")])]
    eF += fade_up(wm.id, 40, 64, 10) + fade_up(yr.id, 46, 70, 8) + fade_up(nm.id, 50, 74, 8)
    eF += fade_up(persona_blk.id, 54, 84, 14)
    for j, sn in enumerate(stat_nodes):
        eF += fade_up(sn.id, 60 + j * 7, 92 + j * 7, 24)
    eF += fade_up(sh.id, 96, 124, 10) + fade_up(eh.id, 40, 72, 14) + fade_up(es.id, 56, 86, 10) + pop(trio.id, 70, 100, 0.3, "back")
    eF += fade_up(sup.id, 110, 136, 10)
    # persona/stat/name opacities are bound; animate their y + use a wrapper-free fade on y only
    for b in (nm, persona_blk, *stat_nodes):
        eF = [t for t in eF if not (t[0] == b.id and t[1] == "opacity")]
    eB = [(card_bg.id, "opacity", [(0, 0.0, "hold"), (2, 0.0, "out"), (24, 1.0, "hold")]),
          (card.id, "y", [(0, -30, "hold"), (12, -30, "out"), (46, 0, "hold")]),
          (card.id, "opacity", [(0, 0.0, "hold"), (12, 0.0, "out"), (36, 1.0, "hold")])]
    eB += fade_up(sup.id, 10, 40, -12)
    xF = art_exit(art.id, 0.9, -10) + fade_out(copy.id, 0, 14, -16)
    xB = art_exit(art.id, 0.94, 30, f1=20) + fade_out(copy.id, 0, 14, 16)
    idle = [(ring_grp.id, "rotation", [(0, 0.0, "lin"), (2400, 2 * math.pi, "hold")])]
    # ring rotates about the seal: wrap pivot
    ring_grp.attrs["x"] = cx
    ring_grp.attrs["y"] = seal_y
    REST[(ring_grp.id, "x")] = cx
    REST[(ring_grp.id, "y")] = seal_y
    for a_, t in ring_arcs:
        a_.attrs["x"] = 0.0
        a_.attrs["y"] = 0.0
    idle += osc(card_glow.id, "opacity", 480, 0.65, 1.0)
    return scene_component(k, "Summary", [art], [copy],
                           dict(enterF=(140, eF), enterB=(50, eB), exitF=(36, xF), exitB=(36, xB), idle=(2400, idle)))


# =====================================================================================
# MAIN ARTBOARD
# =====================================================================================
POSES = {  # motif centre, scale, iris openness (0 pupil .. 1 open), rotation; lodestar; sky offset/scale
    1: dict(m=(195, 300, 0.86, 1.0, 0.0), l=(292, 196, 1.0, 1.0), sky=(0, 0, 1.0)),
    2: dict(m=(195, 290, 1.07, 0.70, 0.35), l=(267, 296, 0.0, 0.0), sky=(0, -18, 1.08)),
    3: dict(m=(236, 292, 0.30, 0.55, 0.9), l=(236, 164, 0.8, 1.0), sky=(-14, -6, 0.94)),
    4: dict(m=(195, 292, 0.15, 0.10, 1.2), l=(338, 233, 0.9, 1.0), sky=(0, 10, 1.2)),
    5: dict(m=(318, 124, 0.24, 0.85, 1.6), l=(56, 402, 0.8, 1.0), sky=(12, 0, 0.9)),
    6: dict(m=(84, 152, 0.30, 0.82, 2.0), l=(325, 146, 1.1, 1.0), sky=(20, 14, 1.05)),
    7: dict(m=(182, 296, 0.97, 1.0, 2.3), l=(252, 200, 0.7, 1.0), sky=(-10, 6, 1.0)),
    8: dict(m=(316, 470, 0.22, 0.78, 2.6), l=(272, 330, 0.7, 1.0), sky=(-20, -10, 1.12)),
    9: dict(m=(195, 290, 0.95, 1.0, 3.0), l=(195, 104, 1.2, 1.0), sky=(0, 0, 1.25)),
    10: dict(m=(195, 178, 0.19, 0.92, 3.3), l=(276, 150, 0.6, 1.0), sky=(0, -24, 0.96)),
}


def build_main():
    children = []
    # ---------- background + parallax sky (back-most, declared last)
    bg = shape("Background", rect(W, H, ox=0, oy=0), fill(paint=linear([(0, "0A1A30", 1), (0.5, MID, 1), (1, MID_DEEP, 1)], 0, 0, 0, H)))
    nebula_bg = shape("Ambient Glow", ellipse(520, 380), fill(BLUE, 0.07, feather=90), x=195, y=300)
    sky_groups = starfield("Sky", 64, 195, 422, 0, rect_wh=(470, 900), dmin=0.7, dmax=2.1, amin=0.2, amax=0.75,
                           colors=((ICE, 1), (WHITE, 1), (ICE, 1), (AMBER, 0.8)), groups=4, glow_every=13)
    sky = node("Parallax Sky", *[node("Sky Layer", g, x=-195, y=-422) for g in sky_groups], x=195, y=422)
    # ---------- scenes (nested components)
    scene_nodes = []
    for ab in SCENE_ARTBOARDS:
        scene_nodes.append(El("NestedArtboard", El("NestedStateMachine", animationId=ab.attrs["defaultStateMachineId"], name="Scene SM"),
                              artboardId=ab.id, x=0.0, y=0.0, name=ab.attrs["name"]))
    scenes = node("Scenes", *reversed(scene_nodes), x=0, y=0)
    # ---------- motif (traveling aperture) + lodestar
    m0 = POSES[1]["m"]
    motif, remap = aperture_instance("Motif", m0[0], m0[1], m0[2], m0[3])
    lode = star4("Lodestar", POSES[1]["l"][0], POSES[1]["l"][1], 22, AMBER, 1.0, glow=9, glow_a=0.75, inner=0.12)
    # ---------- finder (signature interaction, scene 1 only)
    fc = node("Finder Centre", x=0, y=0)
    lens_clip = shape("Lens", ellipse(84), x=0, y=0)
    hidden_stars = starfield("Revealed", 120, 0, 0, 122, dmin=1.0, dmax=3.2, colors=((WHITE, 1), (ICE, 1), (ICE, 1), (AMBER, 1)),
                             amin=0.75, amax=1.0, glow_every=4, groups=1)
    hidden_stars += [shape("Hidden Nebula A", ellipse(120, 60), fill(BLUE, 0.35, feather=24), x=-40, y=30, rotation=0.5),
                     shape("Hidden Nebula B", ellipse(70, 40), fill(AMBER, 0.25, feather=16), x=50, y=-40, rotation=-0.4),
                     shape("Hidden Nebula C", ellipse(90, 50), fill(ICE, 0.22, feather=20), x=10, y=70)]
    hit = shape("Finder Hit", ellipse(64), fill(ICE, 0.0), isTargetOpaque=True)
    handle = node("Finder Handle",
                  El("DistanceConstraint", targetId=fc.id, distance=84.0, modeValue="closer", name="Bound to disk"),
                  hit,
                  shape("Finder Ring", ellipse(46), stroke(ICE, 0.9, 1.2)),
                  shape("Finder Glow", ellipse(46), stroke(BLUE, 0.6, 5, feather=5)),
                  *[shape(f"Finder Tick {i}", rect(1.2, 8), fill(ICE, 0.9), x=29 * math.cos(i * math.pi / 2), y=29 * math.sin(i * math.pi / 2),
                          rotation=i * math.pi / 2 + math.pi / 2) for i in range(4)],
                  lens_clip,
                  x=46, y=-38)
    reveal = node("Revealed Stars", *hidden_stars, El("ClippingShape", sourceId=lens_clip.id, name="Lens Clip"), x=0, y=0)
    finder = node("Finder (drag)", handle, reveal, fc, x=195, y=300)
    finder.add(bind("currentScreen", KEY_X, cv_offscreen_unless(1, 195)))
    REST[(finder.id, "x")] = 195.0
    # ---------- header chrome
    year_t = text("Year", 362, 34, 100, 16, tstyle("mono", 11, ICE, 0.85, ls=3.0), "", tb("year", CV_INT_TEXT), align="right", wrap="noWrap")
    mark = node("Wordmark Mark", shape("Ring", ellipse(13), stroke(ICE, 0.9, 1.1)),
                *[shape(f"t{i}", rect(1.1, 4), fill(ICE, 0.9), x=9 * math.cos(i * math.pi / 2), y=9 * math.sin(i * math.pi / 2),
                        rotation=i * math.pi / 2 + math.pi / 2) for i in range(4)],
                dot("Pupil", 0, 0, 3, AMBER, 1.0), x=36, y=42)
    wordmark = text("Wordmark", 54, 34, 200, 18, tstyle("sg", 15, ICE, weight=500, ls=3.2), "Nocturne", None, align="left", wrap="noWrap")
    # progress segments: flex row, hidden scenes collapse out of the row
    segs = []
    for kk in range(1, 11):
        fill_lc = El("LayoutComponent",
                     El("LayoutComponentStyle", positionTypeValue="absolute", layoutWidthScaleType="fixed", layoutHeightScaleType="fixed",
                        widthUnitsValue="percent", heightUnitsValue="percent", name="Fill Style", id=(fs := nid())),
                     fill(BLUE, 1.0),
                     width=100.0, height=100.0, styleId=fs, name=f"Segment {kk} Progress")
        fill_lc.add(El("ComponentOrigin", originX=0.0, originY=0.5, name="Origin"))
        fill_lc.add(bind("currentScreen", KEY_SCALEX, CV_SEG[kk]))
        st = El("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fill", name="Segment Style", id=nid())
        if 2 <= kk <= 9:
            st.add(bind(f"showScreen{kk}", KEY_DISPLAY, CV_HIDE_IF_FALSE))
        seg = El("LayoutComponent", st, fill_lc, fill(ICE, 0.18), width=10.0, height=3.0, styleId=st.id, name=f"Segment {kk}")
        segs.append(seg)
    seg_style = El("LayoutComponentStyle", flexDirectionValue="row", gapHorizontal=5.0, gapHorizontalUnitsValue="points",
                   name="Progress Style")
    progress = El("LayoutComponent", seg_style, *segs, x=28.0, y=66.0, width=334.0, height=3.0, styleId=seg_style.id,
                  name="Progress Segments")
    header = node("Header", year_t, wordmark, mark, x=0, y=0)

    # ---------- controls
    def button(name, idx, x, y, label_prop, icon_children, accent=ICE, primary=False, label2=None):
        d = 50.0 if primary else 44.0
        ring = shape("Ring", ellipse(d), stroke(accent, 0.85 if primary else 0.55, 1.3))
        focus = shape("Focus Ring", ellipse(d + 9), stroke(AMBER, 0.8, 1.4, effects=[dash(3, 3)]))
        focus.add(bind("focusedControl", KEY_OPACITY, cv_eq(idx)))
        REST[(focus.id, "opacity")] = 1.0
        hitb = shape(f"{name} Hit", El("FocusData", name="Focus"),
                     El("SemanticData", bind(label_prop, 983), role="button", label=name, name="Semantics"),
                     rect(76, 64, r=12), fill(ICE, 0.0), isTargetOpaque=True, x=0, y=6)
        lab = text("Label", 0, d / 2 + 6, 110, 14, tstyle("mono", 9.5, ICE, 0.8, ls=2.0, lh=14), "", tb(label_prop), align="center")
        labs = [lab]
        if label2:
            lab.add(bind(label2[1], KEY_OPACITY, CV_NOTBOOL_NUM))
            lab2 = text("Label Alt", 0, d / 2 + 6, 110, 14, tstyle("mono", 9.5, ICE, 0.8, ls=2.0, lh=14), "", tb(label2[0]), align="center")
            lab2.add(bind(label2[1], KEY_OPACITY, CV_BOOL_NUM))
            labs.append(lab2)
        b = node(name, *labs, *icon_children, focus, ring, hitb, x=x, y=y)
        return b, hitb

    chev = lambda s: shape("Chevron", poly([(-3 * s, -7), (4 * s, 0), (-3 * s, 7)], closed=False), stroke(ICE, 0.95, 1.6, cap="round"))
    pause_icon = node("Pause Icon", shape("a", rect(2.2, 13), fill(ICE, 0.95), x=-4), shape("b", rect(2.2, 13), fill(ICE, 0.95), x=4))
    pause_icon.add(bind("isPaused", KEY_OPACITY, CV_NOTBOOL_NUM))
    play_icon = shape("Play Icon", poly([(-4, -7), (7, 0), (-4, 7)], closed=True), fill(ICE, 0.95))
    play_icon.add(bind("isPaused", KEY_OPACITY, CV_BOOL_NUM))
    share_icon = node("Share Icon", shape("Arrow", poly([(0, 6), (0, -7)], closed=False), stroke(AMBER, 1, 1.6, cap="round")),
                      shape("Head", poly([(-5, -2), (0, -7), (5, -2)], closed=False), stroke(AMBER, 1, 1.6, cap="round")),
                      shape("Tray", poly([(-7, 2), (-7, 8), (7, 8), (7, 2)], closed=False), stroke(AMBER, 1, 1.4, cap="round")))
    replay_icon = node("Replay Icon", shape("Loop", ellipse(14), stroke(ICE, 0.95, 1.5, effects=[trim(0.0, 0.8, 0.1)], cap="round")),
                       shape("Tip", poly([(3, -10), (8, -7), (3, -3)], closed=True), fill(ICE, 0.95)))
    by = 780.0
    prev_b, prev_hit = button("Previous", 1, 70, by, "previousLabel", [chev(-1)])
    pause_b, pause_hit = button("Pause", 2, 320, by, "pauseLabel", [pause_icon, play_icon], label2=("playLabel", "isPaused"))
    next_b, next_hit = button("Continue", 3, 195, by, "continueLabel", [chev(1)], accent=BLUE, primary=True)
    share_b, share_hit = button("Share", 4, 195, by, "shareLabel", [share_icon], accent=AMBER, primary=True)
    replay_b, replay_hit = button("Replay", 5, 320, by, "replayLabel", [replay_icon])
    next_b.add(bind("currentScreen", KEY_X, cv_offscreen_if(10, 195)))
    pause_b.add(bind("currentScreen", KEY_X, cv_offscreen_if(10, 320)))
    share_b.add(bind("currentScreen", KEY_X, cv_offscreen_unless(10, 195)))
    replay_b.add(bind("currentScreen", KEY_X, cv_offscreen_unless(10, 320)))
    controls = node("Controls", prev_b, next_b, pause_b, share_b, replay_b, x=0, y=0)
    chrome = node("Chrome", header, progress, controls, x=0, y=0)
    chrome.add(bind("captureMode", KEY_OPACITY, CV_NOTBOOL_NUM))
    # ---------- gesture regions
    tap_prev = shape("Tap Previous (left third)", rect(130, 650, ox=0, oy=0), fill(ICE, 0.0), x=0, y=104)
    tap_next = shape("Tap Next (right two-thirds)", rect(260, 650, ox=0, oy=0), fill(ICE, 0.0), x=130, y=104)
    # ---------- clock script (auto-advance dwell timer)
    clock_style = El("LayoutComponentStyle", name="Clock Style")
    clock = El("LayoutComponent", clock_style, El("ScriptedLayout", scriptAssetId=CLOCK_SCRIPT, name="Dwell Clock"),
               x=0.0, y=0.0, width=1.0, height=1.0, styleId=clock_style.id, name="Dwell Clock Host")
    # ---------- events
    if os.environ.get("NOCTURNE_EVENT_PROBE"):  # test-only: OpenUrlEvents are logged by the CLI, plain Events are not
        ev_screen = El("OpenUrlEvent", url="probe://screenChanged", targetValue=0, name="screenChanged")
        ev_share = El("OpenUrlEvent", url="probe://shareTapped", targetValue=0, name="shareTapped")
        ev_fin = El("OpenUrlEvent", url="probe://recapFinished", targetValue=0, name="recapFinished")
    else:
        ev_screen = El("Event", El("CustomPropertyNumber", bind("currentScreen", 243), propertyValue=1.0, name="screen"),
                       name="screenChanged")
        ev_share = El("Event", name="shareTapped")
        ev_fin = El("Event", name="recapFinished")
    seq_dummy = node("Sequencer Marker", x=0, y=0)
    stage = node("Stage", El("FocusData", canFocus=False, name="Keyboard Host"),
                 chrome, finder, lode, motif, scenes, sky, nebula_bg, tap_prev, tap_next, x=0, y=0)
    stage_bg = bg

    # =================================================================== timelines (main)
    A = []
    tick = anim("Sequencer Tick", 60, [(seq_dummy.id, "opacity", [(0, 1.0, "hold")])])
    A.append(tick)

    def pose_tracks(kk, frame=0, scale_mul=1.0, iris=None, rot_add=0.0, lode_o=None, ease="hold"):
        p = POSES[kk]
        mx, my, ms, mi, mr = p["m"]
        lx, ly, ls_, lo = p["l"]
        sx, sy, ss = p["sky"]
        return [
            (motif.id, "x", [(frame, mx, ease)]), (motif.id, "y", [(frame, my, ease)]),
            (motif.id, "scaleX", [(frame, ms * scale_mul, ease)]), (motif.id, "scaleY", [(frame, ms * scale_mul, ease)]),
            (motif.id, "rotation", [(frame, mr + rot_add, ease)]),
            (remap.id, "time", [(frame, mi if iris is None else iris, ease)]),
            (lode.id, "x", [(frame, lx, ease)]), (lode.id, "y", [(frame, ly, ease)]),
            (lode.id, "scaleX", [(frame, ls_, ease)]), (lode.id, "scaleY", [(frame, ls_, ease)]),
            (lode.id, "opacity", [(frame, lo if lode_o is None else lode_o, ease)]),
            (sky.id, "x", [(frame, 195 + sx, ease)]), (sky.id, "y", [(frame, 422 + sy, ease)]),
            (sky.id, "scaleX", [(frame, ss, ease)]), (sky.id, "scaleY", [(frame, ss, ease)]),
        ]

    def merge(*lists):
        d = {}
        for lst in lists:
            for o, p_, keys in lst:
                d.setdefault((o, p_), []).extend(keys)
        return [(o, p_, ks) for (o, p_), ks in d.items()]

    POSE_A, THF_A, THB_A = {}, {}, {}
    for kk in range(1, 11):
        POSE_A[kk] = anim(f"Motif Pose {kk}", 1, pose_tracks(kk))
        # signature transition: hold the pupil closed briefly, then open onto the new scale of sky
        hold_f, open_f = 12, 46 if kk != 9 else 70
        mi = POSES[kk]["m"][3]
        fwd = merge(pose_tracks(kk, 0, 0.62, 0.0, 0.55, 0.0),
                    pose_tracks(kk, hold_f, 0.62, 0.0, 0.55, 0.0, ease=(0.3, 0.0, 0.25, 1.0)),
                    [(motif.id, "scaleX", [(hold_f + (open_f - hold_f) * 0.7, POSES[kk]["m"][2] * 1.035, "out")]),
                     (motif.id, "scaleY", [(hold_f + (open_f - hold_f) * 0.7, POSES[kk]["m"][2] * 1.035, "out")])],
                    pose_tracks(kk, open_f))
        if kk == 9:  # persona anticipation: the pupil breathes twice before opening
            fwd = [t for t in fwd if not (t[0] == remap.id)]
            fwd.append((remap.id, "time", [(0, 0.0, "hold"), (14, 0.0, "sine"), (24, 0.12, "sine"), (34, 0.0, "sine"),
                                           (42, 0.08, "sine"), (50, 0.0, (0.3, 0.0, 0.2, 1.0)), (70, 1.0, "hold")]))
        THF_A[kk] = anim(f"Motif Through {kk} (forward)", open_f, fwd)
        bwd = merge(pose_tracks(kk, 0, 1.45, 0.0, -0.55, 0.0),
                    pose_tracks(kk, 8, 1.45, 0.0, -0.55, 0.0, ease=(0.3, 0.0, 0.25, 1.0)),
                    pose_tracks(kk, 40))
        THB_A[kk] = anim(f"Motif Through {kk} (back)", 40, bwd)
        A += [POSE_A[kk], THF_A[kk], THB_A[kk]]
    ambient_idle = anim("Ambient Idle", 720,
                        sum([osc(g.id, "opacity", 720, 0.55, 1.0, phase=i / 4, steps=4) for i, g in enumerate(sky_groups)], []) +
                        osc(lode.id, "rotation", 720, -0.12, 0.12, steps=4) +
                        osc(nebula_bg.id, "opacity", 720, 0.7, 1.0), loop="loop")
    ambient_frozen = anim("Ambient Frozen", 1, [(seq_dummy.id, "opacity", [(0, 1.0, "hold")])])
    ambient_static = anim("Ambient Static", 1, rest_tracks({(g.id, "opacity") for g in sky_groups} | {(lode.id, "rotation"), (nebula_bg.id, "opacity")}))
    A += [ambient_idle, ambient_frozen, ambient_static]
    # finder invitation pulse (scene 1)
    finder_pulse = anim("Finder Invite", 180, osc(handle.id, "scaleX", 180, 0.94, 1.06) + osc(handle.id, "scaleY", 180, 0.94, 1.06), loop="loop")
    A.append(finder_pulse)

    # =================================================================== state machine
    layers = []
    # --- Boot: initial focus for keyboard
    boot_st = nid()
    layers.append(layer("Boot", boot_st, [El("AnimationState", El("FocusActionTarget", targetId=next_hit.id),
                                             animationId=ambient_frozen.id, x=0.0, y=0.0, id=boot_st)]))
    # --- Sequence
    SEQ = {kk: nid() for kk in range(1, 11)}
    SEQ_DONE = nid()
    shown = lambda m: c_bool(f"showScreen{m}", True)
    hidden_ = lambda m: c_bool(f"showScreen{m}", False)
    seq_states = []
    for kk in range(1, 11):
        trs = []
        # forward: nearest eligible scene after kk (10 is always eligible)
        for j in range(kk + 1, 11):
            conds = [c_trig("navNext")] + [hidden_(m) for m in range(kk + 1, j) if 2 <= m <= 9]
            if 2 <= j <= 9:
                conds.append(shown(j))
            trs.append(tr(SEQ[j], *conds, actions=[a_num("navDirection", 1)]))
        for j in range(kk - 1, 0, -1):
            conds = [c_trig("navPrevious")] + [hidden_(m) for m in range(j + 1, kk) if 2 <= m <= 9]
            if 2 <= j <= 9:
                conds.append(shown(j))
            trs.append(tr(SEQ[j], *conds, actions=[a_num("navDirection", -1)]))
        if kk == 10:
            trs.append(tr(SEQ_DONE, c_bool("recapFinishedFired", False), exit_ms=1800))
        if kk > 1:
            trs.append(tr(SEQ[1], c_trig("navReplay"), actions=[a_num("navDirection", 1), a_bool("recapFinishedFired", False)]))
        st = El("AnimationState",
                a_num("currentScreen", kk),
                El("StateMachineFireEvent", eventId=ev_screen.id, occursValue=0),
                *trs,
                animationId=tick.id, reset=True, x=float(220 * kk), y=float(0 if kk % 2 else 160), id=SEQ[kk])
        seq_states.append(st)
    done_trs = []
    for j in range(9, 0, -1):
        conds = [c_trig("navPrevious")] + [hidden_(m) for m in range(j + 1, 10) if 2 <= m <= 9]
        if 2 <= j <= 9:
            conds.append(shown(j))
        done_trs.append(tr(SEQ[j], *conds, actions=[a_num("navDirection", -1)]))
    done_trs.append(tr(SEQ[1], c_trig("navReplay"), actions=[a_num("navDirection", 1), a_bool("recapFinishedFired", False)]))
    seq_states.append(El("AnimationState", a_bool("recapFinishedFired", True),
                         El("StateMachineFireEvent", eventId=ev_fin.id, occursValue=0), *done_trs,
                         animationId=tick.id, x=2420.0, y=320.0, id=SEQ_DONE))
    layers.append(layer("Sequence", SEQ[1], seq_states))

    # --- Gesture: tap vs hold
    G = {n_: nid() for n_ in ("idle", "press", "hold", "tapN", "tapP")}
    g_states = [
        El("AnimationState", a_bool("isHolding", False), tr(G["press"], c_bool("pointerDown", True)),
           animationId=tick.id, x=0.0, y=0.0, id=G["idle"]),
        El("AnimationState",
           tr(G["tapN"], c_bool("pointerDown", False), c_num("pressSide", "greaterThan", 0)),
           tr(G["tapP"], c_bool("pointerDown", False), c_num("pressSide", "lessThan", 0)),
           tr(G["idle"], c_bool("pointerDown", False)),
           tr(G["hold"], exit_ms=380),
           animationId=tick.id, reset=True, x=240.0, y=0.0, id=G["press"]),
        El("AnimationState", a_bool("isHolding", True), tr(G["idle"], c_bool("pointerDown", False)),
           animationId=tick.id, x=480.0, y=-140.0, id=G["hold"]),
        El("AnimationState", a_trig("navNext"), tr(G["idle"]), animationId=tick.id, x=480.0, y=40.0, id=G["tapN"]),
        El("AnimationState", a_trig("navPrevious"), tr(G["idle"]), animationId=tick.id, x=480.0, y=180.0, id=G["tapP"]),
    ]
    layers.append(layer("Gesture (tap / hold)", G["idle"], g_states))

    # --- Motif (traveling aperture, signature close/open transition)
    M = {}
    m_states = []
    any_tr = []
    for kk in range(1, 11):
        M[("p", kk)], M[("f", kk)], M[("b", kk)] = nid(), nid(), nid()
    for kk in range(1, 11):
        base = lambda: [c_num("currentScreen", "equal", kk), c_num("motifPose", "notEqual", kk)]
        any_tr += [
            tr(M[("p", kk)], *base(), c_bool("reducedMotion", True)),
            tr(M[("f", kk)], *base(), c_num("navDirection", "greaterThanOrEqual", 0), c_bool("reducedMotion", False), dur=260, ease="inout"),
            tr(M[("b", kk)], *base(), c_num("navDirection", "lessThan", 0), c_bool("reducedMotion", False), dur=260, ease="inout"),
        ]
        m_states += [
            El("AnimationState", a_num("motifPose", kk), tr(M[("p", kk)], exit_pct=100),
               animationId=THF_A[kk].id, reset=True, x=float(220 * kk), y=-160.0, id=M[("f", kk)]),
            El("AnimationState", a_num("motifPose", kk), tr(M[("p", kk)], exit_pct=100),
               animationId=THB_A[kk].id, reset=True, x=float(220 * kk), y=160.0, id=M[("b", kk)]),
            El("AnimationState", a_num("motifPose", kk), animationId=POSE_A[kk].id, x=float(220 * kk), y=0.0, id=M[("p", kk)]),
        ]
    layers.append(layer("Motif", M[("f", 1)], m_states, any_tr=any_tr))

    # --- Ambient (decorative loops; frozen while paused, static under reduced motion)
    AM = {n_: nid() for n_ in ("idle", "frozen", "static")}
    layers.append(layer("Ambient", AM["idle"], [
        El("AnimationState", tr(AM["static"], c_bool("reducedMotion", True), dur=200),
           tr(AM["frozen"], c_bool("isPaused", True)), tr(AM["frozen"], c_bool("isHolding", True)),
           animationId=ambient_idle.id, x=0.0, y=0.0, id=AM["idle"]),
        El("AnimationState", tr(AM["static"], c_bool("reducedMotion", True)),
           tr(AM["idle"], c_bool("isPaused", False), c_bool("isHolding", False)),
           animationId=ambient_frozen.id, x=240.0, y=-120.0, id=AM["frozen"]),
        El("AnimationState", tr(AM["idle"], c_bool("reducedMotion", False), dur=200),
           animationId=ambient_static.id, x=240.0, y=120.0, id=AM["static"]),
    ]))
    FP = {n_: nid() for n_ in ("on", "off")}
    layers.append(layer("Finder Invite", FP["on"], [
        El("AnimationState", tr(FP["off"], c_bool("reducedMotion", True)), tr(FP["off"], c_bool("isPaused", True)),
           animationId=finder_pulse.id, x=0.0, y=0.0, id=FP["on"]),
        El("AnimationState", tr(FP["on"], c_bool("reducedMotion", False), c_bool("isPaused", False)),
           animationId=ambient_frozen.id, x=240.0, y=0.0, id=FP["off"]),
    ]))

    # --- Persona mapping (derived binding: personaIndex -> name, description, colour, slot)
    PERSONAS = [("Deep Sky Dreamer", "Wonder beyond the familiar.", "BCE4E8"),
                ("Lunar Archivist", "You notice something new in an old companion.", "608BFF"),
                ("Planet Tracker", "You enjoy following a moving mystery.", "F7BE62"),
                ("Meteor Watcher", "You are ready for a fleeting bright moment.", "081526")]
    PS = [nid() for _ in PERSONAS]
    p_states = []
    for i, (pn, pd, pc) in enumerate(PERSONAS):
        trs = []
        for j in range(4):
            if j == i:
                continue
            if j == 0:
                trs.append(tr(PS[0], c_num("personaIndex", "notEqual", 1), c_num("personaIndex", "notEqual", 2),
                              c_num("personaIndex", "notEqual", 3)))
            else:
                trs.append(tr(PS[j], c_num("personaIndex", "equal", j)))
        p_states.append(El("AnimationState", a_num("personaSlot", i), a_str("personaName", pn), a_str("personaDescription", pd),
                           a_color("personaColor", argb(pc)), *trs, animationId=tick.id, x=float(240 * i), y=float(0 if i % 2 else 140),
                           id=PS[i]))
    p_entry = nid()
    entry_trs = [tr(PS[j], c_num("personaIndex", "equal", j)) for j in (1, 2, 3)] + [tr(PS[0])]
    p_states.insert(0, El("AnimationState", *entry_trs, animationId=tick.id, x=-200.0, y=260.0, id=p_entry))
    layers.append(layer("Persona Mapping", p_entry, p_states))

    # --- Eligibility (hasStats derived from visibility flags)
    EL_ = {n_: nid() for n_ in ("has", "none")}
    layers.append(layer("Eligibility", EL_["has"], [
        El("AnimationState", a_bool("hasStats", True),
           tr(EL_["none"], *[c_bool(f"showScreen{m}", False) for m in range(2, 9)]),
           animationId=tick.id, x=0.0, y=0.0, id=EL_["has"]),
        El("AnimationState", a_bool("hasStats", False),
           *[tr(EL_["has"], c_bool(f"showScreen{m}", True)) for m in range(2, 9)],
           animationId=tick.id, x=260.0, y=0.0, id=EL_["none"]),
    ]))

    # =================================================================== listeners
    L = []

    def lst(name, target, inputs, actions):
        return El("StateMachineListener", *inputs, *actions, targetId=target, name=name)

    it = lambda t: El("ListenerInputType", listenerTypeValue=t)
    kb = lambda *keys: El("ListenerInputTypeKeyboard", *[El("KeyboardInput", keyType=k_, keyPhase=1) for k_ in keys],
                          listenerTypeValue="keyboard")
    sem_tap = lambda: El("ListenerInputTypeSemantic", El("SemanticInput", actionType="tap"), listenerTypeValue="semanticAction")
    # gestures
    L.append(lst("Tap Prev Down", tap_prev.id, [it("down")], [a_num("pressSide", -1), a_bool("pointerDown", True)]))
    L.append(lst("Tap Next Down", tap_next.id, [it("down")], [a_num("pressSide", 1), a_bool("pointerDown", True)]))
    for t_ in (tap_prev, tap_next):
        L.append(lst("Release", t_.id, [it("up")], [a_bool("pointerDown", False)]))
        L.append(lst("Cancel On Exit", t_.id, [it("exit")], [a_num("pressSide", 0), a_bool("pointerDown", False)]))
    # signature interaction: drag the bounded finder
    L.append(El("StateMachineListenerSingle", El("ListenerAlignTarget", targetId=handle.id, preserveOffset=True),
                targetId=hit.id, listenerTypeValue="drag", name="Drag Finder"))
    # buttons: pointer click, keyboard Enter on the focused button, screen-reader tap
    L.append(lst("Previous", prev_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_trig("navPrevious")]))
    L.append(lst("Continue", next_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_trig("navNext")]))
    L.append(lst("Pause / Play", pause_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_toggle("isPaused", CV_NOT)]))
    L.append(lst("Share", share_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [El("ListenerFireEvent", eventId=ev_share.id)]))
    L.append(lst("Replay", replay_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_trig("navReplay")]))
    for idx, hb in ((1, prev_hit), (2, pause_hit), (3, next_hit), (4, share_hit), (5, replay_hit)):
        L.append(lst(f"Focus {idx}", hb.id, [it("focus")], [a_num("focusedControl", idx)]))
        L.append(lst(f"Blur {idx}", hb.id, [it("blur")], [a_num("focusedControl", 0)]))
    # keyboard on the stage (keys bubble up from whichever control holds focus)
    L.append(lst("Key Right", stage.id, [kb("right")], [a_trig("navNext")]))
    L.append(lst("Key Left", stage.id, [kb("left")], [a_trig("navPrevious")]))
    L.append(lst("Key Space", stage.id, [kb("space")], [a_toggle("isPaused", CV_NOT)]))
    L.append(lst("Key Tab", stage.id, [El("ListenerInputTypeKeyboard", El("KeyboardInput", keyType="tab", keyPhase=1), listenerTypeValue="keyboard")],
                 [El("FocusActionTraversal", traversalKind="next")]))
    L.append(lst("Key Shift Tab", stage.id, [El("ListenerInputTypeKeyboard", El("KeyboardInput", keyType="tab", keyPhase=1, modifiers=1),
                                                 listenerTypeValue="keyboard")],
                 [El("FocusActionTraversal", traversalKind="previous")]))

    smid = nid()
    sm = El("StateMachine", *L, *layers, name="Recap", id=smid)
    style = El("LayoutComponentStyle", name="Artboard Style")
    ab = El("Artboard", style, stage, clock, seq_dummy, stage_bg, ev_screen, ev_share, ev_fin, sm, *A,
            viewModelId=VMID, viewModelInstanceId=INST_IDS["Fixture"], defaultStateMachineId=smid, styleId=style.id,
            width=float(W), height=float(H), x=0.0, y=0.0, name="Nocturne Recap")
    return ab


CLOCK_SCRIPT = nid()


def main():
    scenes = [scene1(), scene2(), scene3(), scene4(), scene5(), scene6(), scene7(), scene8(), scene9(), scene10()]
    main_ab = build_main()
    os.makedirs(OUT, exist_ok=True)
    files = {
        "00_data.rml": [VM_EL, *CONVERTERS, *FONTS, El("ScriptAsset", file="clock.luau", name="clock", id=CLOCK_SCRIPT)],
        "10_main.rml": [main_ab],
        "20_aperture.rml": [APERTURE],
        "30_scenes.rml": [*SCENE_ARTBOARDS, *COMPONENT_ASSETS],
    }
    import json
    fx = os.path.join(HERE, "..", "fixtures")
    os.makedirs(fx, exist_ok=True)
    for fname, data in FIXTURES.items():
        d = {k: (("#" + v) if k == "personaColor" else v) for k, v in data.items()}
        with open(os.path.join(fx, {"Fixture": "sample", "NewUser": "new-user", "Extreme": "extreme-long-copy"}[fname] + ".json"), "w") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    for fn, roots in files.items():
        with open(os.path.join(OUT, fn), "w") as f:
            f.write("<!-- GENERATED by tools/generate.py; edit the generator or hand-edit and stop regenerating. -->\n")
            f.write(doc(*roots))
    print("wrote", ", ".join(files))


if __name__ == "__main__":
    main()
