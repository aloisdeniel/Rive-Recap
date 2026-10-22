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
    "layoutBreakpoint": 768,
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
    "focusedControl": 0, "captureMode": False, "onSummary": False,
    "primaryPressed": "trigger", "secondaryPressed": "trigger",
    "primaryA11yLabel": "Continue", "secondaryA11yLabel": "Pause",
    **{f"fxCount{i}": 1 for i in range(2, 9)},
}
# Responsive layout outputs, written by layout.luau from the real artboard size (README "Responsive layout").
# The defaults are the 390 x 844 portrait values, so the first frame is right before the script runs.
LAYOUT_OUT = {
    "isLandscape": False, "isSideBySide": False, "layoutWidth": 390, "layoutHeight": 844, "layScale": 1,
    "laySideT": 0, "layCardT": 0, "layChrome": 1,
    "layHdrLX": 28, "layHdrRX": 362, "layHdrY": 42, "layHdrAlpha": 1,
    "layProgX": 28, "layProgY": 66, "layProgW": 334, "layProgH": 3,
    "layPrevX": 70, "layPrevY": 780, "layPrimX": 195, "layPrimY": 780, "laySecX": 320, "laySecY": 780,
    "layTapTop": 104, "layTapH": 650, "layTapPrevW": 130, "layTapNextX": 130, "layTapNextW": 260,
    "layArtX": 0, "layArtXB": 0, "layArtY": 0, "layArtS": 1,
    "layCopyX": 0, "layCopyXB": 0, "layCopyY": 0, "layCopyS": 1, "layNumBox": 116,
    "layCardX": 0, "layCardY": 0, "layCardS": 1, "layHeroX": 0, "layHeroY": 0, "layHeroS": 1,
    "layArtRes": 1, "layStageRes": 1.9, "layAnnot": 1, "laySkyX": 0, "laySkyY": 0, "laySkyS": 1,
}
ADDITIONS.update(LAYOUT_OUT)
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
FORMAT_SCRIPT = nid()
_fmt = El("ScriptedDataConverter", El("ScriptInputNumber", propertyValue=0.0, name="decimals"),
          El("ScriptInputNumber", propertyValue=1.0, name="grouping"), scriptAssetId=FORMAT_SCRIPT, name="Grouped integer (locale)")
CONVERTERS.append(_fmt)
CV_FMT = _fmt.id
CV_INT_TEXT = group("Count text", CV_CLAMP_INT, CV_FMT)
CV_YEAR_TEXT = group("Year text", CV_CLAMP_INT, CV_TOSTR_INT)
CV_BOOL_NUM = group("Bool to 0/1", CV_TOSTR, CV_TONUM)
CV_NOTBOOL_NUM = group("Not bool to 0/1", CV_NOT, CV_TOSTR, CV_TONUM)
# displayValue: 0 = flex (shown), 1 = none (hidden)
CV_HIDE_IF_FALSE = CV_NOTBOOL_NUM

CV_COUNT = {}
for i in range(2, 9):
    f = formula(f"Count-up {i}", ["max(", 0, ",", "round(", "in", "*", ("vm", f"fxCount{i}"), ")", ")"])
    CV_COUNT[i] = group(f"Count-up text {i}", f, CV_FMT)

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

# ---------------------------------------------------------------- responsive layout helpers
_LIN = {}


def cv_lin(a, b):
    """number -> a + input * b (orientation blends: a portrait value, b the landscape difference)."""
    key = (round(float(a), 4), round(float(b), 4))
    if key not in _LIN:
        _LIN[key] = formula(f"{key[0]:g} + in * {key[1]:g}", [key[0], "+", "in", "*", key[1]])
    return _LIN[key]


_RES = {}


def cv_res(orig):
    """GPU canvas density from layArtRes (art scale x device scale): keep the authored supersampling at @1x and
    follow the device beyond it."""
    if orig not in _RES:
        _RES[orig] = formula(f"Density x{orig:g}", [orig / 2.0, "*", "max(", 2, ",", "in", ")"])
    return _RES[orig]


CV_HALF_NUM = formula("Number slot offset", ["(", "in", "-", 116, ")", "*", 0.5])
CV_NUM_SHIFT = formula("Copy below number offset", ["in", "-", 116])

FRAME_PROPS = {"artA": ("layArtX", "layArtY", "layArtS"), "artB": ("layArtXB", "layArtY", "layArtS"),
               "copyA": ("layCopyX", "layCopyY", "layCopyS"), "copyB": ("layCopyXB", "layCopyY", "layCopyS"),
               "card": ("layCardX", "layCardY", "layCardS"), "hero": ("layHeroX", "layHeroY", "layHeroS")}


def frame(name, kind, *children):
    """A translate + uniform-scale frame bound to the layout script's output (design space -> canvas)."""
    px, py, ps = FRAME_PROPS[kind]
    n = node(name, *children, x=0, y=0)
    n.add(bind(px, KEY_X), bind(py, KEY_Y), bind(ps, KEY_SCALEX), bind(ps, KEY_SCALEY))
    return n


def side_bind(el, key, pv, lv, prop="laySideT"):
    """Bind one property to its portrait value pv, or lv when art and copy sit side by side (prop 0 -> 1)."""
    if pv != lv:
        el.add(bind(prop, key, cv_lin(pv, lv - pv)))
    return el


def place(name, child, p, l, prop="laySideT"):
    """Wrap child in a node at its stacked position p, moving to l side by side; child's own (keyed) transform
    becomes relative to it."""
    child.attrs["x"] = 0.0
    child.attrs["y"] = 0.0
    REST[(child.id, "x")] = 0.0
    REST[(child.id, "y")] = 0.0
    w = node(name, child, x=p[0], y=p[1])
    side_bind(w, KEY_X, float(p[0]), float(l[0]), prop)
    side_bind(w, KEY_Y, float(p[1]), float(l[1]), prop)
    return w


def annot(name, *children):
    """Decorative instrument annotations: they fade out before the art scale would draw them below 8 pt."""
    n = node(name, *children, x=0, y=0)
    n.add(bind("layAnnot", KEY_OPACITY))
    return n


CV_ALIGN_CL = cv_lin(2, -2)   # Text alignValue: center (2) stacked, left (0) side by side


def align_left_when_side(*texts):
    for t in texts:
        t.add(bind("laySideT", KEY_TEXT_ALIGN, CV_ALIGN_CL))


# ---------------------------------------------------------------- scripts (GPU drawables)
SCRIPT_IDS = {n: nid() for n in ("sky", "iris", "orb")}
SCRIPT_IDS["format"] = FORMAT_SCRIPT
SCRIPT_FILES = {"sky": "scripts/sky.luau", "iris": "scripts/iris.luau", "orb": "scripts/orb.luau", "format": "scripts/format.luau"}
KEY_SI_NUM, KEY_SI_BOOL, KEY_SI_COLOR = 243, 245, 836


def scripted(name, script, nums=None, bools=None, colors=None, binds=None, **kw):
    """A ScriptedDrawable with typed script inputs. binds: input name -> DataBindContext.
    Returns (element, {input name: input id}) so timelines can key the inputs (property propertyValue)."""
    nums, bools, colors, binds = nums or {}, bools or {}, colors or {}, binds or {}
    ch, ids = [], {}
    for k, v in nums.items():
        e = El("ScriptInputNumber", propertyValue=float(v), name=k)
        ch.append(e)
        ids[k] = e.id
    for k, v in bools.items():
        e = El("ScriptInputBoolean", propertyValue=bool(v), name=k)
        ch.append(e)
        ids[k] = e.id
    for k, v in colors.items():
        e = El("ScriptInputColor", propertyValue=argb(v), name=k)
        ch.append(e)
        ids[k] = e.id
    for e in ch:
        b = binds.get(e.attrs["name"])
        if b is not None:
            e.add(b)
    return El("ScriptedDrawable", *ch, scriptAssetId=SCRIPT_IDS[script], name=name, **kw), ids


def motion_binds(live=None):
    """Standard bindings: reduced motion -> still, pause and hold freeze."""
    d = {"still": bind("reducedMotion", KEY_SI_BOOL), "paused": bind("isPaused", KEY_SI_BOOL),
         "holding": bind("isHolding", KEY_SI_BOOL)}
    if live is not None:
        d["live"] = live
    return d


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


def flow_text(name, style, binding, align="left", max_h=None, value=""):
    """A Text that is a flex item: fills the column width, hugs its height (wraps then pushes what follows)."""
    kw = {}
    if max_h:
        kw.update(maxHeight=float(max_h), maxHeightUnitsValue="points")
    part = El("LayoutParticipant", layoutWidthScaleType="fill", layoutHeightScaleType="hug", name="Flow", **kw)
    run = El("TextValueRun", binding, styleId=style.id, text=value, name="Run")
    return El("Text", part, style, run, x=0.0, y=0.0, originX=0.0, originY=0.0, alignValue=align, sizingValue="autoHeight",
              overflowValue="ellipsis", wrapValue="wrap", verticalAlignValue="top", width=334.0, height=20.0, name=name)


def flow_box(name, w, h, *children):
    """A fixed-size flex item that hosts free-positioned art (a divider ornament)."""
    st = El("LayoutComponentStyle", layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", name=f"{name} Style")
    return El("LayoutComponent", st, *children, width=float(w), height=float(h), styleId=st.id, name=name)


def column(name, x, y, w, h, *items, gap=10.0, align="left"):
    """Copy stack: a flex column whose items keep a constant rhythm whatever the line count."""
    cross = {"left": "topLeft", "center": "topCenter", "right": "topRight"}[align]
    st = El("LayoutComponentStyle", flexDirectionValue="column", gapVertical=float(gap), gapVerticalUnitsValue="points",
            layoutAlignmentType=cross, name=f"{name} Style")
    return El("LayoutComponent", st, *items, x=float(x), y=float(y), width=float(w), height=float(h), styleId=st.id, name=name)


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


def shift(tracks, df):
    """Delay every key after frame 0 by df frames (frame-0 holds stay)."""
    return [(o, p_, [(f + df if f > 0 else f, *rest) for f, *rest in keys]) for o, p_, keys in tracks]


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


def scene_component(k, name, art_children, copy_children, anims, root_extra=(), kind="A"):
    """anims: dict enterF, enterB, exitF, exitB, idle -> (dur, tracks).

    kind picks the responsive frames: "A" art left / copy right side by side, "B" mirrored (art right),
    "card" the summary (art and copy share the card frame). Stacked, A and B are the same."""
    if kind == "card":
        frames = [frame(f"S{k} Card Frame", "card", *art_children, *copy_children)]
    else:
        frames = [frame(f"S{k} Art Frame", "art" + kind, *art_children),
                  frame(f"S{k} Copy Frame", "copy" + kind, *copy_children)]
    root = node(f"Scene {k} Root", *frames, *root_extra, x=0, y=0)
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
COPY_Y = {"num": 516, "unit": 582, "div": 616, "head": 634, "sup": 710}


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
    head = flow_text(f"S{k} Headline", tstyle("sg", 30, WHITE, weight=400, lh=36, ls=-0.3), tb(f"screen{k}Headline"), align, max_h=78)
    sup = flow_text(f"S{k} Support", tstyle("mono", 12.5, ICE, 0.72, lh=18, ls=0.4), tb(f"screen{k}Support"), align, max_h=40)
    col = column(f"S{k} Copy Column", 28, COPY_Y["head"], 334, 110, head, sup, gap=9, align=align)
    counter = node(f"S{k} Count Playhead", x=1.0, y=0.0)
    counter.add(bind(f"fxCount{k}", KEY_X, direction=True))
    if align == "center":
        # side by side the copy column reads left, toward the art: the text aligns left and the divider takes its
        # left-hand form (spark at the margin, one rule)
        align_left_when_side(num, unit, head, sup)
        side_bind(div, KEY_X, dx, 34.0)
        lines[0].add(bind("laySideT", KEY_OPACITY, cv_lin(1, -1)))
    # the hero number's box shrinks on short canvases (layNumBox, 84..116): the font fits the box and the copy
    # below moves up with it
    num.add(bind("layNumBox", KEY_TEXT_H))
    num_slot = node(f"S{k} Number Slot", num, x=0, y=0)
    num_slot.add(bind("layNumBox", KEY_Y, CV_HALF_NUM))
    lower = node(f"S{k} Below Number", unit, div, col, x=0, y=0)
    lower.add(bind("layNumBox", KEY_Y, CV_NUM_SHIFT))
    copy = node(f"S{k} Copy", num_slot, lower, x=0, y=0)
    return copy, counter, dict(num=num.id, unit=unit.id, div=div.id, head=head.id, sup=sup.id, copy=copy.id,
                               counter=counter.id, col=col.id)


def copy_enter(c, t0=24):
    """count 0->1 synchronised with the hero (t0..t0+60), then label, rule, headline, support."""
    tr_ = []
    tr_ += prop_tr(c["counter"], "x", [(0, 0.0, "hold"), (t0, 0.0, (0.3, 0.0, 0.2, 1.0)), (t0 + 62, 1.0, "hold")])
    tr_ += fade_up(c["num"], t0 - 6, t0 + 30, dy=26)
    tr_ += fade_up(c["unit"], t0 + 40, t0 + 70, dy=10)
    tr_ += [(c["div"], "scaleX", [(0, 0.0, "hold"), (t0 + 52, 0.0, "out"), (t0 + 84, 1.0, "hold")]),
            (c["div"], "opacity", [(0, 0.0, "hold"), (t0 + 52, 0.0, "out"), (t0 + 66, 1.0, "hold")])]
    # the copy column slides as one; headline and support stagger in opacity (flex items cannot be keyed in y)
    tr_ += fade_up(c["col"], t0 + 60, t0 + 100, dy=16)
    tr_ += [(c["head"], "opacity", [(0, 0.0, "hold"), (t0 + 60, 0.0, "out"), (t0 + 90, 1.0, "hold")]),
            (c["sup"], "opacity", [(0, 0.0, "hold"), (t0 + 74, 0.0, "out"), (t0 + 104, 1.0, "hold")])]
    return tr_


def copy_enter_back(c):
    tr_ = []
    tr_ += prop_tr(c["counter"], "x", [(0, 0.0, "hold"), (16, 0.0, "out"), (46, 1.0, "hold")])
    for i, key in enumerate(("num", "unit", "col")):
        tr_ += fade_up(c[key], 16 + i * 4, 42 + i * 4, dy=-18)
    tr_ += [(c["div"], "scaleX", [(0, 0.0, "hold"), (20, 0.0, "out"), (46, 1.0, "hold")])]
    return tr_


def copy_exit(c, dy=-22):
    tr_ = []
    for i, key in enumerate(("num", "unit", "col")):
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
    iris_tracks = []
    # lit GPU blades (shaders/iris.wgsl, mode 1) inside the housing; the Iris timeline keys the hole,
    # linear in time (the main timelines ease the remap), from a pupil to fully retracted
    blades_sd, AI = scripted("Blades (GPU)", "iris",
                             nums=dict(mode=1, cx=AP_C, cy=AP_C, hole=AP_R + 6, spin=0.0, blades=9, curl=0.85, curve=0.6, hand=1,
                                       bloom=0.0, rim=0.9, lightness=1.0, thick=2.0, outer=AP_R, opacity=1, res=2.4),
                             binds={"res": bind("layArtRes", KEY_SI_NUM, cv_res(2.4))})
    iris_tracks.append((AI["hole"], "propertyValue", [(0, 6.0, "lin"), (60, AP_R + 6, "hold")]))
    iris_tracks.append((AI["bloom"], "propertyValue", [(0, 0.9, "lin"), (20, 0.25, "lin"), (60, 0.0, "hold")]))
    blade_grp = node("Blades", blades_sd, x=0, y=0)
    clip_src = node("Iris Clip (unused)", x=0, y=0)
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
def sky_disk(name, k, cx, cy, r, **look):
    """A GPU sky disk (shaders/sky.wgsl mode 1) that twinkles only while scene k is current."""
    nums = dict(mode=1, cx=cx, cy=cy, radius=r, edge=1.6, viewX=0, viewY=0, viewScale=1, viewRot=0, density=1.0, band=1.3,
                twinkle=1, bandAngle=-0.6, bandWidth=60, warm=0.85, vignette=0.45, exposure=1.0, seed=7, res=2.2, live=0)
    nums.update(look)
    b = motion_binds(live=bind("currentScreen", KEY_SI_NUM, cv_eq(k)))
    b["res"] = bind("layArtRes", KEY_SI_NUM, cv_res(float(nums["res"])))
    return scripted(name, "sky", nums=nums, bools=dict(still=False, paused=False, holding=False), binds=b)


def scene1():
    k = 1
    cx, cy = 195.0, 300.0
    halo = shape("Halo", ellipse(330), fill(ICE, 0.10, feather=46), x=cx, y=cy)
    disk_base, SD1 = sky_disk("Disk Sky (GPU)", 1, cx, cy, 118, seed=5, band=0.75, bandAngle=0.35, bandWidth=46, warm=0.6,
                              exposure=0.85, vignette=0.55, density=0.8)
    disk_tint = shape("Disk Tint", ellipse(236), fill(paint=radial([(0, "2A5A96", 0.45), (0.6, "123059", 0.25), (1, "0A1B33", 0.0)], 150, -48, -56)),
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
    disk = node("Celestial Disk", halo, rim, rim_glow, wordmark, annot("S1 Coordinates", coord_a), lat_grp, lat_clip, inner, disk_tint,
                disk_base, x=0, y=0)
    stars = starfield("Intro Stars", 26, 195, 300, 0, colors=((ICE, 1.0), (WHITE, 1.0), (AMBER, 0.9)), dmin=1.0, dmax=2.4,
                      rect_wh=(370, 420), groups=3, glow_every=7)
    art = node("S1 Art", disk, *stars, x=0, y=0)

    name = text("S1 Name", 195, 506, 334, 28, tstyle("sg", 21, ICE, 0.9, weight=400, ls=0.2, lh=28), "", tb("userName"),
                align="center")
    head = text("S1 Headline", 195, 544, 334, 88, tstyle("sg", 36, WHITE, weight=400, lh=42, ls=-0.6), "",
                tb("introHeadline"), align="center")
    sup = text("S1 Support", 195, 640, 334, 40, tstyle("mono", 13, ICE, 0.75, lh=19, ls=0.4), "", tb("introSupport"),
               align="center")
    per = text("S1 Period", 195, 690, 334, 18, tstyle("mono", 10.5, AMBER, 0.85, ls=2.2), "", tb("periodLabel"),
               align="center", wrap="noWrap")
    rule_l = shape("Rule L", rect(48, 1, ox=1.0), fill(AMBER, 0.5), x=-10)
    div = node("S1 Divider", star4("Spark", 0, 0, 11, AMBER, glow=4), rule_l,
               shape("Rule R", rect(48, 1, ox=0.0), fill(AMBER, 0.5), x=10), x=195, y=722)
    # side by side the greeting reads left, toward the disk
    align_left_when_side(name, head, sup, per)
    side_bind(div, KEY_X, 195.0, 34.0)
    rule_l.add(bind("laySideT", KEY_OPACITY, cv_lin(1, -1)))
    copy = node("S1 Copy", name, head, sup, per, div, x=0, y=0)
    # on short canvases the copy box shrinks with the hero-number box (layNumBox); the greeting moves up with it
    copy_slot = node("S1 Copy Slot", copy, x=0, y=0)
    copy_slot.add(bind("layNumBox", KEY_Y, CV_NUM_SHIFT))

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
    eF = shift(eF, 20)   # the app opens behind the stage iris; let the disk build as the blades part
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
    return scene_component(k, "Invitation", [art], [copy_slot],
                           dict(enterF=(144, eF), enterB=(56, eB), exitF=(36, xF), exitB=(36, xB), idle=(720, idle)))


def scene2():
    k = 2
    cx, cy, r = 195.0, 290.0, 158.0
    # the iris opens on a dense Milky Way (GPU): it develops like a long exposure as the count runs
    disk, SD = sky_disk("Sky Disk (GPU)", k, cx, cy, r, seed=11, bandAngle=-0.62, bandWidth=58, band=1.35, warm=0.9)
    bright = star4("Bright Star", cx + 72, cy + 6, 26, AMBER, 1.0, glow=10, glow_a=0.7, inner=0.12)
    sky = node("Sky Disk", bright, disk, x=0, y=0)
    art = node("S2 Art", sky, x=0, y=0)
    copy, counter, c = metric_copy(k, "observationNights", "center")
    eF = copy_enter(c, 26)
    eF += [(sky.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (22, 1.0, "hold")]),
           (SD["exposure"], "propertyValue", [(0, 0.15, "hold"), (24, 0.15, (0.3, 0.0, 0.2, 1.0)), (90, 1.0, "hold")]),
           (SD["band"], "propertyValue", [(0, 0.1, "hold"), (14, 0.1, (0.4, 0.0, 0.2, 1.0)), (104, 1.35, "hold")]),
           (SD["viewScale"], "propertyValue", [(0, 1.35, "hold"), (8, 1.35, (0.2, 0.8, 0.3, 1.0)), (110, 1.0, "hold")]),
           (SD["viewRot"], "propertyValue", [(0, -0.35, "hold"), (8, -0.35, (0.2, 0.8, 0.3, 1.0)), (120, 0.0, "hold")])]
    eF += pop(bright.id, 70, 96, 0.0, "back")
    eB = copy_enter_back(c) + [(sky.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (30, 1.0, "hold")]),
                               (SD["viewRot"], "propertyValue", [(0, 0.3, "hold"), (4, 0.3, "out"), (50, 0.0, "hold")]),
                               (SD["viewScale"], "propertyValue", [(0, 0.85, "hold"), (4, 0.85, "out"), (50, 1.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.82, -6)
    xB = copy_exit(c, 22) + art_exit(art.id, 1.12, 6)
    idle = [(SD["viewRot"], "propertyValue", [(0, 0.0, "sine"), (600, 0.05, "sine"), (1200, 0.0, "hold")])]
    idle += osc(bright.id, "rotation", 600, -0.08, 0.08, steps=4) + osc(bright.id, "rotation", 1200, -0.08, 0.08)
    return scene_component(k, "Nights outside", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(56, eB), exitF=(36, xF), exitB=(36, xB), idle=(1200, idle)))


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
    art = node("S3 Art", sweep, mk, annot("S3 Bearings", *labels), *rings, *spokes, x=0, y=0)
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
    art = node("S5 Art", *pts, *lines, annot("S5 Grid Labels", *glabels), *grid, x=0, y=0)
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
                 fill(paint=linear([(0, WHITE, 1.0), (0.12, color, 0.75), (0.5, color, 0.25), (1, color, 0.0)], 0, 0, -length, 0)))
    tail_glow = shape("Trail Glow", poly([(0, -width * 2.2), (0, width * 2.2), (-length * 0.7, 0)], closed=True),
                      fill(paint=linear([(0, BLUE, 0.55), (1, BLUE, 0.0)], 0, 0, -length * 0.7, 0), feather=8))
    flare = shape("Head Flare", ellipse(head * 5, head * 1.6), fill(ICE, 0.35, feather=head * 1.4))
    return node(name, dot("Head", 0, 0, head, WHITE, 1.0, glow=head * 2.0, glow_a=0.9), flare, tail, tail_glow, x=0, y=0)


def scene6():
    k = 6
    rx, ry = 300.0, 128.0          # the radiant: where every trail points back to (the motif sits here)
    # long-exposure lanes radiating from the radiant: (angle deg, start dist, length, colour, alpha)
    lanes = [(126, 60, 300, ICE, 0.46), (140, 48, 320, AMBER, 0.40), (154, 80, 250, ICE, 0.34), (112, 70, 260, BLUE, 0.40),
             (164, 100, 190, ICE, 0.26), (134, 150, 180, BLUE, 0.30), (102, 60, 210, ICE, 0.24), (148, 190, 140, ICE, 0.22),
             (118, 40, 150, ICE, 0.22)]
    trails, ttr = [], []
    for j, (ang, s0, L, col, al) in enumerate(lanes):
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        t = trim(0.0, 1.0, 0.0)
        ttr.append(t)
        x0, y0 = rx + ux * s0, ry + uy * s0
        trails.append(shape(f"Exposure Trail {j}", poly([(x0, y0), (x0 + ux * L, y0 + uy * L)], closed=False),
                            stroke(w=1.1 if j % 3 else 1.6, paint=linear([(0, col, 0.0), (0.25, col, al), (1, col, al * 0.5)],
                                                                          x0, y0, x0 + ux * L, y0 + uy * L), effects=[t], cap="round")))
    # bounded pool: 5 meteors riding five of the lanes, re-used by the idle loop
    specs = [(1, 230, 3.4, 0, ICE), (3, 150, 2.4, 50, BLUE), (0, 180, 2.6, 100, ICE), (5, 120, 2.0, 150, AMBER), (2, 140, 2.2, 200, ICE)]
    pool = []
    for i, (lane_i, L, wd, f0, col) in enumerate(specs):
        ang, s0, LL, _, _ = lanes[lane_i]
        m = meteor(f"Meteor {i + 1}", L, wd, col, head=3.6 + wd)
        lane = node(f"Lane {i + 1}", m, x=rx, y=ry, rotation=math.radians(ang))
        pool.append((lane, m, s0, s0 + LL + 40, f0))
    met_grp = node("Meteor Pool", *[p[0] for p in pool], x=0, y=0)
    # altitude grid: faint arcs of an all-sky camera with two labels
    grid = [shape("Altitude 30", ellipse(560, 560), stroke(BLUE, 0.13, 1), x=rx, y=ry),
            shape("Altitude 60", ellipse(330, 330), stroke(BLUE, 0.11, 1, effects=[dash(2, 5)]), x=rx, y=ry),
            shape("Meridian", poly([(rx, ry), (rx - 330, ry + 330)], closed=False), stroke(ICE, 0.08, 1))]
    glabels = [text("Alt 60", rx - 150, ry + 96, 70, 14, tstyle("mono", 9, ICE, 0.45, ls=1.2), "ALT 60°", None, align="left", wrap="noWrap"),
               text("Alt 30", 40, 300, 70, 14, tstyle("mono", 9, ICE, 0.45, ls=1.2), "ALT 30°", None, align="left", wrap="noWrap"),
               text("Radiant", rx - 46, ry + 34, 92, 14, tstyle("mono", 9, AMBER, 0.75, ls=1.6), "RADIANT", None, align="center", wrap="noWrap")]
    radiant_glow = shape("Radiant", ellipse(120), fill(AMBER, 0.16, feather=40), x=rx, y=ry)
    hero_flash = shape("Hero Afterglow", rect(360, 8, ox=0.0), fill(ICE, 0.18, feather=12), x=rx, y=ry,
                       rotation=math.radians(lanes[1][0]), opacity=0.0)
    art = node("S6 Art", met_grp, hero_flash, *trails, annot("S6 Grid Labels", *glabels), radiant_glow, *grid, x=0, y=0)
    for lane, m, xs, xe, f0 in pool:
        m.attrs["x"] = float(xs)
        REST[(m.id, "x")] = float(xs)
        REST[(m.id, "opacity")] = 0.0
        m.attrs["opacity"] = 0.0
    copy, counter, c = metric_copy(k, "meteorSightings", "right")
    eF = copy_enter(c, 26)
    for g in grid:
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (40, REST[(g.id, "opacity")], "hold")])]
    eF += [(g.id, "opacity", [(0, 0.0, "hold"), (60, 0.0, "out"), (90, 1.0, "hold")]) for g in glabels]
    eF += scale_to(grid[0].id, 0, 0, 0.7, 0.7, "hold") + [(grid[0].id, "scaleX", [(0, 0.7, "hold"), (4, 0.7, "out"), (60, 1.0, "hold")]),
                                                          (grid[0].id, "scaleY", [(0, 0.7, "hold"), (4, 0.7, "out"), (60, 1.0, "hold")])]
    # hero meteor + two followers on the count's beat; each leaves its exposure trail
    for idx, (lane, m, xs, xe, f0) in enumerate(pool[:3]):
        st = 22 + idx * 16
        dur = 34 - idx * 4
        eF += [(m.id, "x", [(0, xs, "hold"), (st, xs, (0.3, 0.2, 0.6, 1.0)), (st + dur, xe, "hold")]),
               (m.id, "opacity", [(0, 0.0, "hold"), (st, 0.0, "lin"), (st + 3, 1.0, "hold"), (st + dur - 9, 1.0, "lin"), (st + dur, 0.0, "hold")])]
    eF += [(hero_flash.id, "opacity", [(0, 0.0, "hold"), (32, 0.0, "out"), (42, 1.0, "in"), (110, 0.0, "hold")])]
    for j, t in enumerate(ttr):
        f0 = 24 + j * 8
        eF += [(t.id, "end", [(0, 0.0, "hold"), (f0, 0.0, (0.3, 0.2, 0.4, 1.0)), (f0 + 24, 1.0, "hold")])]
    eF += [(radiant_glow.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (60, 1.0, "hold")])]
    eB = copy_enter_back(c)
    for j, t in enumerate(ttr):
        eB += [(t.id, "start", [(0, 1.0, "hold"), (2, 1.0, "out"), (32, 0.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.9, -6)
    for j, t in enumerate(ttr):
        xF += [(t.id, "start", [(0, 0.0, "in"), (22, 1.0, "hold")])]
    xB = copy_exit(c, 22) + art_exit(art.id, 1.08, 6)
    idle = []
    loop = 250
    idle += osc(radiant_glow.id, "opacity", loop, 0.7, 1.0)
    for lane, m, xs, xe, f0 in pool:
        dur = 40
        st = f0 % loop
        keys_x = [(0, xs, "hold"), (st, xs, (0.3, 0.2, 0.6, 1.0)), (st + dur, xe, "hold"), (loop, xs, "hold")]
        keys_o = [(0, 0.0, "hold"), (st, 0.0, "lin"), (st + 4, 1.0, "hold"), (st + dur - 10, 1.0, "lin"), (st + dur, 0.0, "hold"), (loop, 0.0, "hold")]
        idle += [(m.id, "x", keys_x), (m.id, "opacity", keys_o)]
    return scene_component(k, "Meteors spotted", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(loop, idle)), kind="B")


def orb(name, k, cx, cy, r, live=None, **kw):
    nums = dict(kind=0, cx=cx, cy=cy, radius=r, phase=0.78, turn=0.0, spinSpeed=0.02, tilt=0.0, earthshine=0.6, tintAmount=0.0,
                rimWarm=1.0, ringTilt=0.42, ring=1.0, exposure=1.0, halo=1.0, seed=3, res=2.2, live=0)
    colors = {"tint": kw.pop("tint", ICE)}
    nums.update(kw)
    binds = motion_binds(live=live if live is not None else bind("currentScreen", KEY_SI_NUM, cv_eq(k)))
    binds["res"] = bind("layArtRes", KEY_SI_NUM, cv_res(float(nums["res"])))
    return scripted(name, "orb", nums=nums, bools=dict(still=False, paused=False, holding=False), colors=colors, binds=binds)


def scene7():
    k = 7
    cx, cy, d = 182.0, 296.0, 256.0
    # a lit 3D moon (GPU): the sun sweeps round it in step with the count, new -> crescent -> half -> gibbous
    moon, MO = orb("Moon (GPU)", k, cx, cy, d / 2, phase=0.78, earthshine=0.7, seed=4.0, tilt=0.25)
    halo = shape("Moon Halo", ellipse(d + 70), fill(ICE, 0.10, feather=44), x=cx, y=cy)
    warm = shape("Moon Warm Limb", ellipse(d + 18), stroke(AMBER, 0.22, 10, feather=12, effects=[trim(0.0, 0.32, 0.88)]), x=cx, y=cy)
    rim = shape("Moon Rim", ellipse(d + 10), stroke(ICE, 0.22, 1), x=cx, y=cy)
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
    moon_body = node("Moon Body", moon, x=0, y=0)
    art = node("S7 Art", *glyphs, orbit, rim, warm, moon_body, halo, x=0, y=0)
    copy, counter, c = metric_copy(k, "moonSessions", "right")
    eF = copy_enter(c, 26)
    eF += [(MO["phase"], "propertyValue", [(0, 0.0, "hold"), (14, 0.0, (0.35, 0.0, 0.25, 1.0)), (96, 0.78, "hold")]),
           (MO["turn"], "propertyValue", [(0, -0.5, "hold"), (8, -0.5, (0.2, 0.7, 0.3, 1.0)), (110, 0.0, "hold")]),
           (moon_body.id, "scaleX", [(0, 0.9, "hold"), (4, 0.9, "back"), (60, 1.0, "hold")]),
           (moon_body.id, "scaleY", [(0, 0.9, "hold"), (4, 0.9, "back"), (60, 1.0, "hold")]),
           (halo.id, "opacity", [(0, 0.0, "hold"), (30, 0.0, "out"), (100, 1.0, "hold")]),
           (warm.id, "opacity", [(0, 0.0, "hold"), (70, 0.0, "out"), (110, 1.0, "hold")]),
           (rim.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (40, REST[(rim.id, "opacity")], "hold")]),
           (orbit.id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "out"), (40, REST[(orbit.id, "opacity")], "hold")])]
    for i, g in enumerate(glyphs):  # each session glyph lands as the terminator passes it
        f0 = 26 + i * 7
        eF += pop(g.id, f0, f0 + 16, 0.2, "back")
    eB = copy_enter_back(c) + [(MO["phase"], "propertyValue", [(0, 1.0, "hold"), (2, 1.0, "out"), (44, 0.78, "hold")]),
                               (MO["turn"], "propertyValue", [(0, 0.4, "hold"), (2, 0.4, "out"), (50, 0.0, "hold")])]
    xF = copy_exit(c) + art_exit(art.id, 0.86, -6) + [(MO["phase"], "propertyValue", [(0, 0.78, "in"), (30, 1.0, "hold")])]
    xB = copy_exit(c, 22) + art_exit(art.id, 1.08, 6) + [(MO["phase"], "propertyValue", [(0, 0.78, "in"), (30, 0.45, "hold")])]
    idle = osc(halo.id, "opacity", 480, 0.7, 1.0) + [(orbit.id, "rotation", [(0, 0.0, "lin"), (1200, 2 * math.pi / 16, "hold")])]
    idle += osc(warm.id, "opacity", 600, 0.7, 1.0)
    return scene_component(k, "Lunar sessions", [art], [copy, counter],
                           dict(enterF=(132, eF), enterB=(52, eB), exitF=(36, xF), exitB=(36, xB), idle=(1200, idle)), kind="B")


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
    # filaments: a few wisps leaving the core
    hatch = []
    for j, (a0, L) in enumerate(((-0.5, 120), (2.2, 110), (3.6, 95), (1.0, 80))):
        pts = [((26 + t * L) * math.cos(a0 + t * 0.7), (20 + t * L * 0.7) * math.sin(a0 + t * 0.7) - 8) for t in (0, 0.33, 0.66, 1.0)]
        hatch.append((pts, ICE if j % 2 else BLUE, 0.45, 0.9))
    sketch = []
    trims8 = []
    for i, (pts, col, a, w) in enumerate(strokes_def + hatch):
        t = trim(0.0, 1.0, 0.0)
        trims8.append(t)
        pth = smooth_path(pts) if len(pts) > 2 else poly(pts, closed=False)
        sketch.append(shape(f"Stroke {i + 1}", pth, stroke(col, a, w, effects=[t], cap="round")))
    # stipple: pencil dots densest at the core, laid down in four passes
    stip = [node(f"Stipple {g + 1}", x=0, y=0) for g in range(4)]
    sr = random.Random(88)
    for i in range(64):
        rad = 92 * (sr.random() ** 1.6)
        a = sr.random() * 2 * math.pi
        stip[i % 4].add(dot("Dot", round(rad * math.cos(a) * 1.15, 1), round(rad * math.sin(a) * 0.82 - 8, 1),
                            round(0.9 + 1.1 * sr.random(), 2), ICE if i % 5 else AMBER, 0.55 + 0.35 * sr.random()))
    crosses = []
    for (sx, sy, s) in ((-96, -110, 7), (104, -60, 9), (80, 96, 6), (-110, 40, 5), (20, -126, 6)):
        crosses.append(node("Star Mark", shape("h", rect(s * 2, 1.1), fill(WHITE, 0.85)), shape("v", rect(1.1, s * 2), fill(WHITE, 0.85)),
                            x=sx, y=sy))
    glow = shape("Nebula Wash", ellipse(200, 140), fill(BLUE, 0.16, feather=36), y=-8)
    glow2 = shape("Nebula Warm", ellipse(90, 60), fill(AMBER, 0.12, feather=24), x=30, y=10)
    sheet = node("Sketch Sheet", *crosses, *stip, *sketch, annot("S8 Annotations", ann, ann2), *regs, glow2, glow, margin, paper,
                 x=cx, y=cy, rotation=-0.045)
    # the loupe (the travelling motif sits on it) shows the sky the sketch was drawn from
    lx, ly = POSES[8]["m"][0], POSES[8]["m"][1]
    loupe, LP = sky_disk("Loupe Sky (GPU)", k, lx, ly, 38, seed=31, band=1.7, bandAngle=0.5, bandWidth=15, warm=1.0, density=1.5,
                         vignette=0.5, res=3.0)
    loupe_grp = node("Loupe", loupe, shape("Loupe Shadow", ellipse(92), fill(MID_DEEP, 0.45, feather=10), x=lx + 3, y=ly + 5), x=0, y=0)
    art = node("S8 Art", loupe_grp, sheet, x=0, y=0)
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
    for i, g in enumerate(stip):
        eF += [(g.id, "opacity", [(0, 0.0, "hold"), (54 + i * 12, 0.0, "out"), (70 + i * 12, 1.0, "hold")])]
    eF += [(loupe_grp.id, "opacity", [(0, 0.0, "hold"), (84, 0.0, "out"), (112, 1.0, "hold")]),
           (LP["exposure"], "propertyValue", [(0, 0.0, "hold"), (90, 0.0, (0.3, 0.0, 0.2, 1.0)), (130, 1.0, "hold")]),
           (LP["viewScale"], "propertyValue", [(0, 1.8, "hold"), (90, 1.8, (0.2, 0.8, 0.3, 1.0)), (140, 1.0, "hold")])]
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
    neb_gpu, NB = sky_disk("Deep Sky (GPU)", 9, 0, 0, 100, seed=21, band=1.6, bandAngle=0.85, bandWidth=34, warm=1.0,
                           density=1.1, vignette=0.7, exposure=1.0, res=2.4)
    for nb in neb:
        nb.attrs["opacity"] = 0.55
        REST[(nb.id, "opacity")] = 0.55
    e0 = slot_node(0, inner_ap, *rings0, neb_gpu, *neb)
    for j, rg in enumerate(rings0):
        f0 = 40 + j * 10
        eF += pop(rg.id, f0, f0 + 34, 0.25 + j * 0.2, "back")
        idle += [(rg.id, "rotation", [(0, 0.0, "lin"), (1440, (1 if j % 2 == 0 else -1) * 2 * math.pi / (2 + j), "hold")])]
    for j, nb in enumerate(neb):
        eF += pop(nb.id, 30 + j * 8, 90 + j * 8, 0.3, "out")
    eF += [(inner_remap.id, "time", [(0, 0.0, "hold"), (60, 0.0, "out"), (100, 1.0, "hold")]),
           (NB["viewScale"], "propertyValue", [(0, 2.6, "hold"), (24, 2.6, (0.2, 0.8, 0.3, 1.0)), (130, 1.0, "hold")]),
           (NB["viewRot"], "propertyValue", [(0, -0.9, "hold"), (24, -0.9, (0.2, 0.8, 0.3, 1.0)), (130, 0.0, "hold")]),
           (NB["exposure"], "propertyValue", [(0, 0.0, "hold"), (24, 0.0, "out"), (90, 1.0, "hold")])]
    idle += [(NB["viewRot"], "propertyValue", [(0, 0.0, "lin"), (1440, 0.35, "hold")])]
    em.append(e0)

    # 1 Lunar Archivist: lunar disk with orbiting phases
    pmoon, PM = orb("Persona Moon (GPU)", 9, 0, 0, 86, phase=0.86, tintAmount=0.55, earthshine=0.8, seed=8.0, tilt=-0.3,
                    halo=1.2, tint=ICE)
    s_tint = pmoon.children[[c_.attrs.get("name") for c_ in pmoon.children].index("tint")]
    s_tint.add(bind("personaColor", KEY_SI_COLOR))
    ldisk = node("Lunar Disk",
                 shape("Disk Glow", ellipse(200), fill(BLUE, 0.28, feather=30)),
                 pmoon,
                 shape("Disk Rim", ellipse(184), stroke(ICE, 0.35, 1.0)),
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
    eF += [(PM["phase"], "propertyValue", [(0, 0.2, "hold"), (30, 0.2, (0.3, 0.0, 0.2, 1.0)), (110, 0.86, "hold")])]
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
    pplanet, PP = orb("Persona Planet (GPU)", 9, 0, 0, 21, kind=1, tintAmount=1.0, seed=5.0, tilt=-0.35, ringTilt=0.38,
                      spinSpeed=0.12, halo=1.0, res=3.0, tint=AMBER)
    p_tint = pplanet.children[[c_.attrs.get("name") for c_ in pplanet.children].index("tint")]
    p_tint.add(bind("personaColor", KEY_SI_COLOR))
    planet = node("Planet", shape("Planet Glow", ellipse(60), fill(AMBER, 0.30, feather=18)), pplanet, x=px0, y=py0)
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
    ecl_gpu, EC = orb("Eclipse (GPU)", 9, 0, 0, 74, kind=2, tintAmount=1.0, seed=2.0, earthshine=0.7, spinSpeed=0.01, halo=1.0,
                      tint=MID, res=2.2)
    e_tint = ecl_gpu.children[[c_.attrs.get("name") for c_ in ecl_gpu.children].index("tint")]
    e_tint.add(bind("personaColor", KEY_SI_COLOR))
    head_arm = node("Arc Head Arm", node("Head Pos", dot("Head", 0, 0, 11, WHITE, 1.0, glow=14, glow_a=0.9), x=140, y=0),
                    x=0, y=0, rotation=2 * math.pi * (0.55 + 0.62))
    e3 = slot_node(3,
                   head_arm,
                   shape("Meteor Arc", ellipse(280), stroke(w=3.0, paint=arc_paint, effects=[m_tr], cap="round")),
                   shape("Meteor Arc Glow", ellipse(280), stroke(AMBER, 0.5, 10, feather=10, effects=[m_tr_g], cap="round")),
                   node("Eclipse", ecl_gpu, shape("Eclipse Rim", ellipse(150), stroke(ICE, 0.35, 1.0)), x=0, y=0),
                   *[node(f"Streak {j}", meteor(f"Mini {j}", 70 - j * 12, 1.6, ICE, head=3.0), x=-40 + j * 38, y=-96 + j * 22,
                          rotation=math.radians(150)) for j in range(3)])
    eclipse = [c_ for c_ in e3.children if c_.attrs.get("name") == "Eclipse"][0]
    eF += [(m_tr.id, "end", [(0, 0.0, "hold"), (36, 0.0, (0.5, 0.0, 0.15, 1.0)), (70, 0.62, "hold")]),
           (m_tr_g.id, "end", [(0, 0.0, "hold"), (36, 0.0, (0.5, 0.0, 0.15, 1.0)), (70, 0.62, "hold")]),
           (head_arm.id, "rotation", [(0, 2 * math.pi * 0.55, "hold"), (36, 2 * math.pi * 0.55, (0.5, 0.0, 0.15, 1.0)),
                                      (70, 2 * math.pi * 1.17, "hold")]),
           (EC["halo"], "propertyValue", [(0, 0.0, "hold"), (60, 0.0, (0.3, 0.0, 0.2, 1.0)), (100, 1.0, "hold")]),
           (eclipse.id, "scaleX", [(0, 0.2, "hold"), (50, 0.2, "back"), (92, 1.0, "hold")]),
           (eclipse.id, "scaleY", [(0, 0.2, "hold"), (50, 0.2, "back"), (92, 1.0, "hold")])]
    idle += [(m_tr.id, "offset", [(0, 0.55, "sine"), (720, 0.58, "sine"), (1440, 0.55, "hold")]),
             (m_tr_g.id, "offset", [(0, 0.55, "sine"), (720, 0.58, "sine"), (1440, 0.55, "hold")]),
             (head_arm.id, "rotation", [(0, 2 * math.pi * 1.17, "sine"), (720, 2 * math.pi * 1.20, "sine"), (1440, 2 * math.pi * 1.17, "hold")])]
    em.append(e3)

    emblems = node("Emblems", *em, x=0, y=0)
    REST[(head.id, "rotation")] = 0.0
    # copy
    lab = flow_text("S9 Label", tstyle("mono", 11, ICE, 0.75, ls=3.0), tb("personaLabel"), "center", max_h=20)
    title = flow_text("S9 Title", tstyle("sg", 40, WHITE, weight=400, lh=46, ls=-0.8), tb("personaName"), "center", max_h=96)
    spark_fill = solid(AMBER, 1.0)
    spark_fill.add(bind("personaColor", KEY_COLOR))
    rule9_l = shape("Rule L", rect(64, 1, ox=1.0), fill(AMBER, 0.55), x=-16)
    divp = node("S9 Divider",
                shape("Spark Ring", ellipse(18), stroke(ICE, 0.6, 1)),
                shape("Spark", El("Star", width=14.0, height=14.0, points=4, innerRadius=0.2, name="Path"), El("Fill", spark_fill, name="Persona Fill")),
                rule9_l,
                shape("Rule R", rect(64, 1, ox=0.0), fill(AMBER, 0.55), x=16), x=167, y=11)
    div_box = flow_box("S9 Divider Slot", 334, 22, divp)
    desc = flow_text("S9 Description", tstyle("mono", 13.5, ICE, 0.85, lh=20, ls=0.6), tb("personaDescription"), "center", max_h=62)
    # side by side the persona reads as a title page beside the emblem: left aligned, the divider at the margin
    align_left_when_side(lab, title, desc)
    side_bind(divp, KEY_X, 167.0, 9.0)
    rule9_l.add(bind("laySideT", KEY_OPACITY, cv_lin(1, -1)))
    col = column("S9 Copy Column", 28, 486, 334, 230, lab, title, div_box, desc, gap=10, align="center")
    copy = node("S9 Copy", col, x=0, y=0)
    art = node("S9 Art", emblems, x=0, y=0)
    fo = lambda oid, f0, f1: [(oid, "opacity", [(0, 0.0, "hold"), (f0, 0.0, "out"), (f1, 1.0, "hold")])]
    eF += fade_up(col.id, 70, 124, 22) + fo(lab.id, 70, 96) + fo(title.id, 82, 116) + fo(desc.id, 104, 134)
    eF += [(divp.id, "scaleX", [(0, 0.0, "hold"), (96, 0.0, "back"), (124, 1.0, "hold")]),
           (art.id, "opacity", [(0, 0.0, "hold"), (24, 0.0, "out"), (44, 1.0, "hold")])]
    eB = [(art.id, "opacity", [(0, 0.0, "hold"), (4, 0.0, "out"), (30, 1.0, "hold")])]
    eB += fade_up(col.id, 16, 50, -16) + fo(lab.id, 16, 40) + fo(title.id, 20, 44) + fo(desc.id, 24, 48)
    xF = art_exit(art.id, 0.8, 0) + fade_out(copy.id, 0, 14, -20)
    xB = art_exit(art.id, 1.15, 0, f1=24) + fade_out(copy.id, 0, 14, 20)
    return scene_component(k, "Persona reveal", [art], [copy],
                           dict(enterF=(140, eF), enterB=(50, eB), exitF=(36, xF), exitB=(36, xB), idle=(1440, idle)))


STATS10 = [("observationNights", 2), ("objectsLogged", 3), ("observationHours", 4), ("constellationsLogged", 5),
           ("meteorSightings", 6)]


def scene10():
    k = 10
    cx = 195.0
    # Two arrangements of one card, blended by layCardT (0 tall, 1 wide). The seal (where the travelling
    # motif lands) stays at design (195, 178) in both, so the motif pose is the same and only the card frame moves.
    TALL = dict(cx=195.0, cy=358.0, w=334.0, h=524.0)    # portrait: a tall card, support line below
    WIDE = dict(cx=375.0, cy=253.0, w=600.0, h=330.0)    # landscape: seal panel | stats panel, support below
    tp, wp = (TALL["cx"], TALL["cy"]), (WIDE["cx"], WIDE["cy"])
    # the card's own switch (layCardT): wide side by side, but the tall card on tall landscape canvases
    side_bind = lambda el, key, pv, lv: globals()["side_bind"](el, key, pv, lv, "layCardT")
    place = lambda name, child, p, l: globals()["place"](name, child, p, l, "layCardT")

    def sized_rect(w_off, h_off, r):
        rc = rect(TALL["w"] + w_off, TALL["h"] + h_off, r=r)
        side_bind(rc, KEY_WIDTH_PATH, TALL["w"] + w_off, WIDE["w"] + w_off)
        side_bind(rc, KEY_HEIGHT_PATH, TALL["h"] + h_off, WIDE["h"] + h_off)
        return rc

    card_grad = linear([(0, "0F2644", 1), (0.6, "0B1C33", 1), (1, "091629", 1)], 0, -TALL["h"] / 2, 0, TALL["h"] / 2)
    side_bind(card_grad, 33, -TALL["h"] / 2, -WIDE["h"] / 2)
    side_bind(card_grad, KEY_GRAD_ENDY, TALL["h"] / 2, WIDE["h"] / 2)
    card_tr = trim(0.0, 1.0, 0.0)
    card_bg = shape("Card", sized_rect(0, 0, 22), fill(paint=card_grad))
    card_edge = shape("Card Edge", sized_rect(0, 0, 22), stroke(ICE, 0.3, 1, effects=[card_tr]))
    card_inner = shape("Card Inner", sized_rect(-20, -20, 14), stroke(BLUE, 0.18, 1, effects=[dash(2, 5)]))
    card_glow = shape("Card Glow", sized_rect(0, 0, 22), fill(BLUE, 0.16, feather=30))
    card_shapes = [place("Card Place", card_bg, tp, wp), place("Card Edge Place", card_edge, tp, wp),
                   place("Card Inner Place", card_inner, tp, wp),
                   place("Card Glow Place", card_glow, (tp[0], tp[1] + 10), (wp[0], wp[1] + 10))]
    # data ring around the seal (the seal itself is the travelling motif from the main artboard)
    seal_y = 178.0
    ring_arcs = []
    cols = [BLUE, ICE, AMBER, BLUE, ICE]
    for j in range(5):
        t = trim(0.0, 0.16, j * 0.2 + 0.02)
        ring_arcs.append((shape(f"Data Arc {j}", ellipse(104), stroke(cols[j], 0.9, 3, effects=[t], cap="round"), x=0, y=0), t))
    ring_grp = node("Data Ring", *[a for a, _ in ring_arcs], x=cx, y=seal_y)
    seal_sky, SS = sky_disk("Seal Sky (GPU)", 10, cx, seal_y, 41, seed=13, band=1.4, bandAngle=-0.7, bandWidth=18, warm=0.9,
                            density=1.3, vignette=0.6, res=3.0)
    corners = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            c_ = shape("Plate Corner", poly([(0, -sy * 12), (0, 0), (-sx * 12, 0)], closed=False), stroke(AMBER, 0.6, 1.1))
            corners.append((c_, place("Corner Place", c_, (TALL["cx"] + sx * (TALL["w"] / 2 - 16), TALL["cy"] + sy * (TALL["h"] / 2 - 16)),
                                      (WIDE["cx"] + sx * (WIDE["w"] / 2 - 16), WIDE["cy"] + sy * (WIDE["h"] / 2 - 16)))))
    # stat grid rules: one set per arrangement
    grid_tall = [shape("Grid V", rect(1, 96), fill(ICE, 0.08), x=cx, y=424),
                 shape("Grid H1", rect(250, 1), fill(ICE, 0.08), x=cx, y=418),
                 shape("Grid H2", rect(250, 1), fill(ICE, 0.08), x=cx, y=478)]
    grid_wide = [shape("Panel Rule", rect(1, 250), fill(ICE, 0.10), x=315, y=WIDE["cy"]),
                 shape("Grid H", rect(320, 1), fill(ICE, 0.08), x=495, y=200),
                 shape("Grid V1", rect(1, 56), fill(ICE, 0.08), x=438, y=160),
                 shape("Grid V2", rect(1, 56), fill(ICE, 0.08), x=552, y=160)]
    g_tall = node("Grid (tall)", *grid_tall, x=0, y=0)
    g_tall.add(bind("layCardT", KEY_OPACITY, cv_lin(1, -1)))
    g_wide = node("Grid (wide)", *grid_wide, x=0, y=0)
    g_wide.add(bind("layCardT", KEY_OPACITY))
    wm = text("Card Wordmark", cx, 238, 300, 26, tstyle("sg", 20, ICE, weight=500, ls=3.0), "NOCTURNE", None, align="center", wrap="noWrap")
    yr = text("Card Year", cx, 264, 200, 16, tstyle("mono", 11, AMBER, 0.95, ls=4.0), "", tb("year", CV_YEAR_TEXT), align="center", wrap="noWrap")
    # single-line ellipsis texts keep one width in both arrangements (the left panel's 228): a bound width does not
    # re-centre an ellipsised line. The name wraps inside a one-line box, so a long name is cut at a word boundary and
    # stays centred (a noWrap ellipsis is centred on its untruncated width)
    nm = text("Card Name", cx, 286, 228, 16, tstyle("mono", 11, ICE, 0.75, ls=1.5), "", tb("userName"), align="center", wrap="wrap")
    nm.add(bind("shareIncludeName", KEY_OPACITY, CV_BOOL_NUM))
    p_fill = solid(ICE, 1.0)
    p_fill.add(bind("personaColor", KEY_COLOR))
    p_label = text("Card Persona Label", 0, 0, 228, 15, tstyle("mono", 10.5, ICE, 0.6, ls=2.2), "", tb("personaLabel"),
                   align="center", wrap="noWrap")
    p_name = text("Card Persona Name", 0, 18, 228, 30, tstyle("sg", 24, WHITE, weight=400, ls=-0.3), "", tb("personaName"),
                  align="center", wrap="noWrap")
    persona_blk = node("Card Persona", p_label, p_name,
                       shape("Persona Rule L", rect(40, 1, ox=1.0), fill(AMBER, 0.45), x=-12, y=58),
                       shape("Persona Rule R", rect(40, 1, ox=0.0), fill(AMBER, 0.45), x=12, y=58),
                       shape("Persona Spark Ring", ellipse(13), stroke(ICE, 0.6, 1), x=0, y=58),
                       shape("Persona Spark", El("Star", width=10.0, height=10.0, points=4, innerRadius=0.22, name="Path"),
                             El("Fill", p_fill, name="Persona Fill"), x=0, y=58),
                       x=cx, y=312)
    persona_blk.add(bind("showScreen9", KEY_OPACITY, CV_BOOL_NUM))
    stat_nodes, stat_places = [], []
    pos_t = [(110, 388), (280, 388), (110, 448), (280, 448), (195, 508)]
    # wide cells sit inside the stats panel (335..655, like Grid H), so a long label never reaches the card edge
    pos_w = [(381, 156), (495, 156), (609, 156), (438, 234), (552, 234)]
    for (prop, sk), pt_, pw_ in zip(STATS10, pos_t, pos_w):
        val = text("Value", 0, 0, 160, 40, tstyle("sg", 34, ICE, weight=300, ls=-1, lh=40), "", tb(prop, CV_INT_TEXT),
                   align="center", oy=0.5, overflow="fitFontSize", wrap="noWrap")
        unit_t = text("Unit", 0, 22, 160, 32, tstyle("mono", 10.5, ICE, 0.72, ls=0.8, lh=14), "", tb(f"screen{sk}Unit"),
                      align="center", wrap="noWrap")
        for t_ in (val, unit_t):
            side_bind(t_, KEY_TEXT_W, 160.0, 104.0)
        side_bind(unit_t, 683, 1.0, 0.0)   # wrapValue: one line in the tall card, two in the wide card's narrow columns
        n_ = node(f"Stat {prop}", val, unit_t, x=0, y=0)
        n_.add(bind(f"showScreen{sk}", KEY_OPACITY, CV_BOOL_NUM))
        stat_nodes.append(n_)
        stat_places.append(place(f"Stat {prop} Place", n_, pt_, pw_))
    sh = text("Card Headline", 0, 0, 300, 48, tstyle("sg", 18, WHITE, weight=400, lh=23), "", tb("summaryHeadline"), align="center")
    side_bind(sh, KEY_TEXT_W, 300.0, 320.0)
    sh_p = place("Card Headline Place", sh, (cx, 552), (495, 318))
    full = node("Card Full", *stat_places, g_tall, g_wide, sh_p, persona_blk, x=0, y=0)
    full.add(bind("hasStats", KEY_OPACITY, CV_BOOL_NUM))
    # empty / new-user variant: a small, complete motif (the seal) and a welcoming invitation
    eh = text("Empty Headline", 0, 0, 290, 84, tstyle("sg", 30, WHITE, weight=400, lh=38), "", tb("emptyHeadline"), align="center")
    es = text("Empty Support", 0, 0, 290, 40, tstyle("mono", 13, ICE, 0.8, lh=19), "", tb("emptySupport"), align="center")
    for t_ in (eh, es):
        side_bind(t_, KEY_TEXT_W, 290.0, 320.0)
    trio = node("First Stars", dot("a", -40, 0, 5, ICE, 1, glow=6), dot("b", 0, -14, 7, AMBER, 1, glow=7), dot("c", 42, 4, 4, ICE, 1, glow=5),
                shape("l1", poly([(-40, 0), (0, -14)], closed=False), stroke(ICE, 0.4, 1)),
                shape("l2", poly([(0, -14), (42, 4)], closed=False), stroke(ICE, 0.4, 1, effects=[dash(2, 4)])), x=0, y=0)
    empty = node("Card Empty", place("Empty Headline Place", eh, (cx, 330), (495, 130)),
                 place("Empty Support Place", es, (cx, 430), (495, 236)), place("First Stars Place", trio, (cx, 520), (495, 320)),
                 x=0, y=0)
    empty.add(bind("hasStats", KEY_OPACITY, CV_NOTBOOL_NUM))
    # bound-opacity content (name, persona, stats) sits in a keyed wrapper so nothing pops in before the card lands
    reveal = node("Card Reveal", nm, full, empty, x=0, y=0)
    card = node("Share Card", wm, yr, reveal, ring_grp, seal_sky, *[cp for _, cp in corners], *card_shapes, x=0, y=0)
    sup = text("S10 Support", 0, 0, 334, 36, tstyle("mono", 12.5, ICE, 0.78, lh=18, ls=0.4), "", tb("summarySupport"), align="center")
    side_bind(sup, KEY_TEXT_W, 334.0, 560.0)
    sup_p = place("S10 Support Place", sup, (cx, 640), (375, 436))
    art = node("S10 Art", card, x=0, y=0)
    copy = node("S10 Copy", sup_p, x=0, y=0)
    # assembly
    eF = [(card_bg.id, "opacity", [(0, 0.0, "hold"), (6, 0.0, "out"), (34, 1.0, "hold")]),
          (card_bg.id, "scaleX", [(0, 0.92, "hold"), (6, 0.92, "back"), (44, 1.0, "hold")]),
          (card_bg.id, "scaleY", [(0, 0.86, "hold"), (6, 0.86, "back"), (44, 1.0, "hold")]),
          (card_glow.id, "opacity", [(0, 0.0, "hold"), (20, 0.0, "out"), (80, 1.0, "hold")]),
          (card_tr.id, "end", [(0, 0.0, "hold"), (10, 0.0, (0.5, 0.0, 0.2, 1.0)), (60, 1.0, "hold")]),
          (card_inner.id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "out"), (70, REST[(card_inner.id, "opacity")], "hold")])]
    for j, (a_, t) in enumerate(ring_arcs):
        eF += [(t.id, "end", [(0, 0.0, "hold"), (34 + j * 6, 0.0, "out"), (64 + j * 6, 0.16, "hold")])]
    eF += [(reveal.id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "out"), (66, 1.0, "hold")])]
    eF += [(seal_sky.id, "opacity", [(0, 0.0, "hold"), (30, 0.0, "out"), (60, 1.0, "hold")]),
           (SS["viewRot"], "propertyValue", [(0, -1.2, "hold"), (30, -1.2, (0.2, 0.8, 0.3, 1.0)), (120, 0.0, "hold")])]
    for j, (g, _) in enumerate(corners):
        eF += pop(g.id, 50 + j * 5, 70 + j * 5, 0.3, "back")
    for j, g in enumerate(grid_tall + grid_wide):
        vertical = g.attrs["name"] in ("Grid V", "Panel Rule", "Grid V1", "Grid V2")
        eF += [(g.id, "scaleY" if vertical else "scaleX", [(0, 0.0, "hold"), (70 + (j % 4) * 6, 0.0, "out"), (100 + (j % 4) * 6, 1.0, "hold")])]
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
    idle += osc(card_glow.id, "opacity", 480, 0.65, 1.0)
    return scene_component(k, "Summary", [art], [copy],
                           dict(enterF=(140, eF), enterB=(50, eB), exitF=(36, xF), exitB=(36, xB), idle=(2400, idle)), kind="card")


# =====================================================================================
# MAIN ARTBOARD
# =====================================================================================
IRIS_OPEN = 1000.0  # stage iris hole radius that covers nothing from any pose


def iris_open(kk):
    """Smallest hole that clears the stage from pose kk's centre (farthest corner + margin): no wasted travel."""
    mx, my = POSES[kk]["m"][0], POSES[kk]["m"][1]
    return max(math.hypot(cx_ - mx, cy_ - my) for cx_ in (0, W) for cy_ in (0, H)) + 20.0
POSES = {  # motif centre, scale, iris openness (0 pupil .. 1 open), rotation; lodestar; sky offset/scale
    1: dict(m=(195, 300, 0.86, 1.0, 0.0), l=(292, 196, 1.0, 1.0), sky=(0, 0, 1.0)),
    2: dict(m=(195, 290, 1.07, 0.70, 0.35), l=(267, 296, 0.0, 0.0), sky=(0, -18, 1.08)),
    3: dict(m=(236, 292, 0.30, 0.55, 0.9), l=(236, 164, 0.8, 1.0), sky=(-14, -6, 0.94)),
    4: dict(m=(195, 292, 0.15, 0.10, 1.2), l=(338, 233, 0.9, 1.0), sky=(0, 10, 1.2)),
    5: dict(m=(318, 124, 0.24, 0.85, 1.6), l=(56, 402, 0.8, 1.0), sky=(12, 0, 0.9)),
    6: dict(m=(300, 128, 0.24, 0.80, 2.0), l=(300, 128, 1.25, 1.0), sky=(20, 14, 1.05)),
    7: dict(m=(182, 296, 0.97, 1.0, 2.3), l=(252, 200, 0.7, 1.0), sky=(-10, 6, 1.0)),
    8: dict(m=(234, 262, 0.27, 0.93, 2.6), l=(272, 330, 0.7, 1.0), sky=(-20, -10, 1.12)),
    9: dict(m=(195, 290, 0.95, 1.0, 3.0), l=(195, 104, 1.2, 1.0), sky=(0, 0, 1.25)),
    10: dict(m=(195, 178, 0.19, 0.92, 3.3), l=(276, 150, 0.6, 1.0), sky=(0, -24, 0.96)),
}


def build_main():
    children = []
    # ---------- background + parallax sky (back-most, declared last)
    # the background bleeds edge to edge: sized to the laid-out artboard (layoutWidth x layoutHeight)
    bg_rect = rect(W, H, ox=0, oy=0)
    bg_rect.add(bind("layoutWidth", KEY_WIDTH_PATH), bind("layoutHeight", KEY_HEIGHT_PATH))
    bg_grad = linear([(0, "0A1A30", 1), (0.5, MID, 1), (1, MID_DEEP, 1)], 0, 0, 0, H)
    bg_grad.add(bind("layoutHeight", KEY_GRAD_ENDY))
    bg = shape("Background", bg_rect, fill(paint=bg_grad))
    nebula_bg = shape("Ambient Glow", ellipse(520, 380), fill(BLUE, 0.07, feather=90), x=195, y=300)
    sky_groups = starfield("Sky", 64, 195, 422, 0, rect_wh=(470, 900), dmin=0.7, dmax=2.1, amin=0.2, amax=0.75,
                           colors=((ICE, 1), (WHITE, 1), (ICE, 1), (AMBER, 0.8)), groups=4, glow_every=13)
    sky = node("Parallax Sky", *[node("Sky Layer", g, x=-195, y=-422) for g in sky_groups], x=195, y=422)
    sky_cover = node("Sky Cover", sky, x=0, y=0)   # the vector fallback sky scales to cover the canvas
    sky_cover.add(bind("laySkyX", KEY_X), bind("laySkyY", KEY_Y), bind("laySkyS", KEY_SCALEX), bind("laySkyS", KEY_SCALEY))
    # GPU sky (shaders/sky.wgsl): opaque, so the vector sky above is only the no-shader fallback. It is sized to the
    # real canvas at the stage density.
    sky_binds = motion_binds()
    sky_binds.update(width=bind("layoutWidth", KEY_SI_NUM), height=bind("layoutHeight", KEY_SI_NUM), res=bind("layStageRes", KEY_SI_NUM))
    sky_gpu, SKY = scripted("Sky (GPU)", "sky",
                            nums=dict(mode=0, width=W, height=H, viewX=0, viewY=0, viewScale=1, viewRot=0, density=0.30,
                                      band=0.75, twinkle=1, bandAngle=-0.62, bandWidth=150, warm=0.55, vignette=0, exposure=1.0,
                                      seed=3, res=2, live=1),
                            bools=dict(still=False, paused=False, holding=False), binds=sky_binds)
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
    # ---------- stage iris (signature transition, shaders/iris.wgsl)
    # it covers the real canvas; its centre and hole are keyed in hero design space and mapped by the hero frame
    iris_stage, IR = scripted("Stage Iris (GPU)", "iris",
                              nums=dict(mode=0, width=W, height=H, cx=195, cy=300, hole=0.0, spin=0.62,
                                        blades=9, curl=0.85, curve=0.55, hand=1, bloom=0.6, rim=1, lightness=1, thick=2.4,
                                        outer=150, opacity=1, res=2, fx=0, fy=0, fs=1),
                              binds=dict(width=bind("layoutWidth", KEY_SI_NUM), height=bind("layoutHeight", KEY_SI_NUM),
                                         res=bind("layStageRes", KEY_SI_NUM), fx=bind("layHeroX", KEY_SI_NUM),
                                         fy=bind("layHeroY", KEY_SI_NUM), fs=bind("layHeroS", KEY_SI_NUM)))
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
                  x=-60, y=-58)
    reveal = node("Revealed Stars", *hidden_stars, El("ClippingShape", sourceId=lens_clip.id, name="Lens Clip"), x=0, y=0)
    finder = node("Finder (drag)", handle, reveal, fc, x=195, y=300)
    finder.add(bind("currentScreen", KEY_X, cv_offscreen_unless(1, 195)))
    REST[(finder.id, "x")] = 195.0
    # ---------- header chrome
    # header: the wordmark pinned to the left margin, the year to the right one (layHdr*), scaled by layChrome
    year_t = text("Year", 0, -8, 100, 16, tstyle("mono", 11, ICE, 0.85, ls=3.0), "", tb("year", CV_YEAR_TEXT), align="right", wrap="noWrap")
    mark = node("Wordmark Mark", shape("Ring", ellipse(13), stroke(ICE, 0.9, 1.1)),
                *[shape(f"t{i}", rect(1.1, 4), fill(ICE, 0.9), x=9 * math.cos(i * math.pi / 2), y=9 * math.sin(i * math.pi / 2),
                        rotation=i * math.pi / 2 + math.pi / 2) for i in range(4)],
                dot("Pupil", 0, 0, 3, AMBER, 1.0), x=8, y=0)
    wordmark = text("Wordmark", 26, -8, 200, 18, tstyle("sg", 15, ICE, weight=500, ls=3.2), "Nocturne", None, align="left", wrap="noWrap")
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
    # the segments span the real width (margin to margin)
    progress.add(bind("layProgX", KEY_X), bind("layProgY", KEY_Y), bind("layProgW", KEY_WIDTH_LC), bind("layProgH", KEY_HEIGHT_LC))
    head_l = node("Header Left", wordmark, mark, x=28, y=42)
    head_r = node("Header Right", year_t, x=362, y=42)
    for hn, hx in ((head_l, "layHdrLX"), (head_r, "layHdrRX")):
        hn.add(bind(hx, KEY_X), bind("layHdrY", KEY_Y), bind("layChrome", KEY_SCALEX), bind("layChrome", KEY_SCALEY))
    header = node("Header", head_l, head_r, progress, x=0, y=0)
    header.add(bind("layHdrAlpha", KEY_OPACITY))   # steps aside on the summary only when the share card needs the room

    # ---------- controls: three always-present slots (nothing hidden stays in the Tab order).
    # The centre slot is Continue, or Share on the summary; the right slot is Pause/Play, or Replay on the summary.
    # A router layer reads `onSummary` to decide what a press means.
    LAB = lambda: tstyle("mono", 9.5, ICE, 0.8, ls=2.0, lh=14)

    def hit_target(name, idx, a11y_prop):
        focus = shape("Focus Ring", ellipse(59 if idx == 3 else 53), stroke(AMBER, 0.8, 1.4, effects=[dash(3, 3)]))
        focus.add(bind("focusedControl", KEY_OPACITY, cv_eq(idx)))
        REST[(focus.id, "opacity")] = 1.0
        hitb = shape(f"{name} Hit", El("FocusData", name="Focus"),
                     El("SemanticData", bind(a11y_prop, 983), role="button", label=name, name="Semantics"),
                     rect(76, 64, r=12), fill(ICE, 0.0), isTargetOpaque=True, x=0, y=6)
        return focus, hitb

    def face(name, d, accent, a, icon, label_prop, show):
        lab = text("Label", 0, d / 2 + 6, 110, 14, LAB(), "", tb(label_prop), align="center")
        f = node(name, lab, *icon, shape("Ring", ellipse(d), stroke(accent, a, 1.3)), x=0, y=0)
        if show is not None:
            f.add(bind("onSummary", KEY_OPACITY, show))
        return f, lab

    chev = lambda s: shape("Chevron", poly([(-3 * s, -7), (4 * s, 0), (-3 * s, 7)], closed=False), stroke(ICE, 0.95, 1.6, cap="round"))
    pause_icon = node("Pause Icon", shape("a", rect(2.2, 13), fill(ICE, 0.95), x=-4), shape("b", rect(2.2, 13), fill(ICE, 0.95), x=4))
    pause_icon.add(bind("isPaused", KEY_OPACITY, CV_NOTBOOL_NUM))
    play_icon = shape("Play Icon", poly([(-4, -7), (7, 0), (-4, 7)], closed=True), fill(ICE, 0.95))
    play_icon.add(bind("isPaused", KEY_OPACITY, CV_BOOL_NUM))
    share_icon = node("Share Icon", shape("Arrow", poly([(0, 5), (0, -8)], closed=False), stroke(AMBER, 1, 1.6, cap="round")),
                      shape("Head", poly([(-4.5, -3.5), (0, -8), (4.5, -3.5)], closed=False), stroke(AMBER, 1, 1.6, cap="round", join="round")),
                      shape("Tray", poly([(-7, 0), (-7, 8), (7, 8), (7, 0)], closed=False), stroke(AMBER, 1, 1.4, cap="round")))
    # replay: a clockwise arc open at the top; the arrowhead sits on the arc's end, aligned to its tangent
    rr, a0, a1 = 6.5, math.radians(-62), math.radians(242)
    arc_pts = [(rr * math.cos(a0 + (a1 - a0) * i / 28), 0.6 + rr * math.sin(a0 + (a1 - a0) * i / 28)) for i in range(29)]
    ex, ey = arc_pts[-1]
    tx, ty = -math.sin(a1), math.cos(a1)          # tangent (direction of travel)
    nx_, ny_ = math.cos(a1), math.sin(a1)         # outward normal
    tip = [(ex + tx * 3.6, ey + ty * 3.6), (ex - tx * 1.2 + nx_ * 3.2, ey - ty * 1.2 + ny_ * 3.2),
           (ex - tx * 1.2 - nx_ * 3.2, ey - ty * 1.2 - ny_ * 3.2)]
    replay_icon = node("Replay Icon", shape("Loop", poly(arc_pts[:-1] + [(ex - tx * 0.8, ey - ty * 0.8)], closed=False),
                                            stroke(ICE, 0.95, 1.5, cap="round")),
                       shape("Tip", poly(tip, closed=True), fill(ICE, 0.95)))
    by = 780.0
    # previous
    prev_focus, prev_hit = hit_target("Previous", 1, "previousLabel")
    prev_face, _ = face("Previous Face", 44.0, ICE, 0.55, [chev(-1)], "previousLabel", None)
    prev_b = node("Previous", prev_face, prev_focus, prev_hit, x=70, y=by)
    # primary: Continue / Share
    prim_focus, next_hit = hit_target("Primary", 3, "primaryA11yLabel")
    cont_face, _ = face("Continue Face", 50.0, BLUE, 0.85, [chev(1)], "continueLabel", CV_NOTBOOL_NUM)
    share_face, _ = face("Share Face", 50.0, AMBER, 0.9, [share_icon], "shareLabel", CV_BOOL_NUM)
    next_b = node("Continue / Share", cont_face, share_face, prim_focus, next_hit, x=195, y=by)
    # secondary: Pause / Play / Replay
    sec_focus, pause_hit = hit_target("Secondary", 2, "secondaryA11yLabel")
    lab_pause = text("Label", 0, 28, 110, 14, LAB(), "", tb("pauseLabel"), align="center")
    lab_pause.add(bind("isPaused", KEY_OPACITY, CV_NOTBOOL_NUM))
    lab_play = text("Label Alt", 0, 28, 110, 14, LAB(), "", tb("playLabel"), align="center")
    lab_play.add(bind("isPaused", KEY_OPACITY, CV_BOOL_NUM))
    transport = node("Transport Face", lab_pause, lab_play, pause_icon, play_icon, shape("Ring", ellipse(44), stroke(ICE, 0.55, 1.3)))
    transport.add(bind("onSummary", KEY_OPACITY, CV_NOTBOOL_NUM))
    replay_face, _ = face("Replay Face", 44.0, ICE, 0.55, [replay_icon], "replayLabel", CV_BOOL_NUM)
    pause_b = node("Pause / Replay", transport, replay_face, sec_focus, pause_hit, x=320, y=by)
    # the transport follows the layout: a centred bottom row, or a right-hand rail side by side on wide canvases
    for b_, px_, py_ in ((prev_b, "layPrevX", "layPrevY"), (next_b, "layPrimX", "layPrimY"), (pause_b, "laySecX", "laySecY")):
        b_.add(bind(px_, KEY_X), bind(py_, KEY_Y), bind("layChrome", KEY_SCALEX), bind("layChrome", KEY_SCALEY))
    controls = node("Controls", prev_b, next_b, pause_b, x=0, y=0)
    chrome = node("Chrome", header, controls, x=0, y=0)
    chrome.add(bind("captureMode", KEY_OPACITY, CV_NOTBOOL_NUM))
    # ---------- gesture regions
    # tap zones over the real canvas (minus header and transport): left third back, right two-thirds next
    tp_rect = rect(130, 650, ox=0, oy=0)
    tp_rect.add(bind("layTapPrevW", KEY_WIDTH_PATH), bind("layTapH", KEY_HEIGHT_PATH))
    tn_rect = rect(260, 650, ox=0, oy=0)
    tn_rect.add(bind("layTapNextW", KEY_WIDTH_PATH), bind("layTapH", KEY_HEIGHT_PATH))
    tap_prev = shape("Tap Previous (left third)", tp_rect, fill(ICE, 0.0), x=0, y=104)
    tap_prev.add(bind("layTapTop", KEY_Y))
    tap_next = shape("Tap Next (right two-thirds)", tn_rect, fill(ICE, 0.0), x=130, y=104)
    tap_next.add(bind("layTapNextX", KEY_X), bind("layTapTop", KEY_Y))
    # ---------- clock script (auto-advance dwell timer)
    clock_style = El("LayoutComponentStyle", name="Clock Style")
    clock = El("LayoutComponent", clock_style, El("ScriptedLayout", scriptAssetId=CLOCK_SCRIPT, name="Dwell Clock"),
               x=0.0, y=0.0, width=1.0, height=1.0, styleId=clock_style.id, name="Dwell Clock Host")
    # ---------- responsive layout (layout.luau): an absolutely positioned box that fills the artboard, so the script
    # receives the real laid-out size and the device scale and writes the layout into UserRecap
    probe_style = El("LayoutComponentStyle", positionTypeValue="absolute", layoutWidthScaleType="fill", layoutHeightScaleType="fill",
                     widthUnitsValue="auto", heightUnitsValue="auto",
                     positionLeft=0.0, positionLeftUnitsValue="points", positionRight=0.0, positionRightUnitsValue="points",
                     positionTop=0.0, positionTopUnitsValue="points", positionBottom=0.0, positionBottomUnitsValue="points",
                     name="Layout Probe Style")
    # test-only: NOCTURNE_RESIZE_PROBE="<seconds>:<W>x<H>[:<W0>x<H0>]" lays out as if the canvas were resized to W x H
    # at that time (and were W0 x H0 before it)
    sim = os.environ.get("NOCTURNE_RESIZE_PROBE", "")
    sim_at, sim_w, sim_h, sim_w0, sim_h0 = -1.0, 0.0, 0.0, 0.0, 0.0
    if sim:
        parts = sim.split(":")
        sim_at, (sim_w, sim_h) = float(parts[0]), [float(v) for v in parts[1].split("x")]
        if len(parts) > 2:
            sim_w0, sim_h0 = [float(v) for v in parts[2].split("x")]
    layout_probe = El("LayoutComponent", probe_style,
                      El("ScriptedLayout", El("ScriptInputNumber", propertyValue=sim_at, name="simAt"),
                         El("ScriptInputNumber", propertyValue=sim_w, name="simWidth"),
                         El("ScriptInputNumber", propertyValue=sim_h, name="simHeight"),
                         El("ScriptInputNumber", propertyValue=sim_w0, name="simFromWidth"),
                         El("ScriptInputNumber", propertyValue=sim_h0, name="simFromHeight"),
                         scriptAssetId=LAYOUT_SCRIPT, name="Responsive Layout"),
                      x=0.0, y=0.0, width=float(W), height=float(H), styleId=probe_style.id, name="Responsive Layout Host")
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
    # the motif, the lodestar and the scene-1 finder travel in the current scene's hero frame
    hero = frame("Hero Frame", "hero", finder, lode, motif)
    hero_glow = frame("Hero Glow Frame", "hero", nebula_bg)
    stage = node("Stage", El("FocusData", canFocus=False, name="Keyboard Host"),
                 chrome, iris_stage, hero, scenes, sky_gpu, sky_cover, hero_glow, tap_prev, tap_next, x=0, y=0)
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
            (SKY["viewX"], "propertyValue", [(frame, sx * 4.0, ease)]), (SKY["viewY"], "propertyValue", [(frame, sy * 4.0, ease)]),
            (IR["cx"], "propertyValue", [(frame, mx, ease)]), (IR["cy"], "propertyValue", [(frame, my, ease)]),
            (IR["hole"], "propertyValue", [(frame, iris_open(kk), ease)]), (IR["spin"], "propertyValue", [(frame, kk * 0.62, ease)]),
            (IR["bloom"], "propertyValue", [(frame, 0.0, ease)]), (IR["hand"], "propertyValue", [(frame, 1.0, ease)]),
            (SKY["viewScale"], "propertyValue", [(frame, ss, ease)]), (SKY["viewRot"], "propertyValue", [(frame, p.get("rot", (kk - 1) * 0.11), ease)]),
        ]

    def merge(*lists):
        d = {}
        for lst in lists:
            for o, p_, keys in lst:
                d.setdefault((o, p_), []).extend(keys)
        return [(o, p_, ks) for (o, p_), ks in d.items()]

    POSE_A, THF_A, THB_A = {}, {}, {}
    IRIS_IDS = {IR[n] for n in ("cx", "cy", "hole", "spin", "bloom", "hand")}
    CLOSE = (0.55, 0.0, 0.85, 0.45)      # accelerating shutter
    OPEN = (0.42, 0.0, 0.18, 1.0)        # the pupil lingers, then the blades fly back and settle
    IRIS_F_END = {kk: 56 for kk in range(1, 11)}
    IRIS_F_END[1], IRIS_F_END[9] = 74, 84

    def iris_static(kk, f_end, hand):
        mx, my = POSES[kk]["m"][0], POSES[kk]["m"][1]
        return [(IR["cx"], "propertyValue", [(0, mx, "hold"), (f_end, mx, "hold")]),
                (IR["cy"], "propertyValue", [(0, my, "hold"), (f_end, my, "hold")]),
                (IR["hand"], "propertyValue", [(0, hand, "hold"), (f_end, hand, "hold")])]

    def iris_forward(kk):
        s_ = kk * 0.62
        f_end = IRIS_F_END[kk]
        IRIS_OPEN = iris_open(kk)
        tr_ = iris_static(kk, f_end, 1.0)
        if kk == 1:   # opening the app (and replay): start shut, breathe, open on the intro sky
            hole = [(0, 0.0, "hold"), (14, 0.0, (0.4, 0.0, 0.6, 1.0)), (26, 9.0, "sine"), (32, 7.0, OPEN), (f_end, IRIS_OPEN, "hold")]
            bloom = [(0, 0.5, "sine"), (26, 1.0, "sine"), (44, 0.35, "out"), (f_end, 0.0, "hold")]
            spin = [(0, s_ - 1.6, (0.3, 0.0, 0.2, 1.0)), (f_end, s_, "hold")]
        elif kk == 9:  # persona anticipation: the pupil breathes twice before opening
            hole = [(0, IRIS_OPEN, CLOSE), (15, 7.0, "sine"), (25, 46.0, "sine"), (34, 9.0, "sine"), (43, 34.0, "sine"),
                    (52, 6.0, OPEN), (f_end, IRIS_OPEN, "hold")]
            bloom = [(0, 0.0, "out"), (15, 0.9, "sine"), (25, 0.5, "sine"), (34, 1.0, "sine"), (43, 0.6, "sine"),
                     (52, 1.2, "out"), (70, 0.2, "out"), (f_end, 0.0, "hold")]
            spin = [(0, s_ - 1.0, "inout"), (15, s_ - 0.45, "sine"), (52, s_ - 0.3, (0.3, 0.0, 0.2, 1.0)), (f_end, s_, "hold")]
        else:
            hole = [(0, IRIS_OPEN, CLOSE), (15, 6.5, (0.3, 0.0, 0.4, 1.0)), (19, 11.0, "sine"), (24, 8.5, OPEN), (f_end, IRIS_OPEN, "hold")]
            bloom = [(0, 0.0, "out"), (13, 0.25, "out"), (16, 1.0, "sine"), (24, 0.85, "out"), (38, 0.2, "out"), (f_end, 0.0, "hold")]
            spin = [(0, s_ - 1.0, "inout"), (15, s_ - 0.38, (0.3, 0.0, 0.2, 1.0)), (f_end, s_, "hold")]
        return tr_ + [(IR["hole"], "propertyValue", hole), (IR["bloom"], "propertyValue", bloom), (IR["spin"], "propertyValue", spin)]

    def iris_back(kk):
        # reverse: mirrored blades, opposite spin, a quicker shutter
        s_ = kk * 0.62
        IRIS_OPEN = iris_open(kk)
        tr_ = iris_static(kk, 44, -1.0)
        hole = [(0, IRIS_OPEN, CLOSE), (12, 8.0, (0.3, 0.0, 0.4, 1.0)), (16, 12.0, OPEN), (44, IRIS_OPEN, "hold")]
        bloom = [(0, 0.0, "out"), (12, 0.8, "sine"), (18, 0.6, "out"), (32, 0.1, "out"), (44, 0.0, "hold")]
        spin = [(0, s_ + 1.0, "inout"), (12, s_ + 0.35, (0.3, 0.0, 0.2, 1.0)), (44, s_, "hold")]
        return tr_ + [(IR["hole"], "propertyValue", hole), (IR["bloom"], "propertyValue", bloom), (IR["spin"], "propertyValue", spin)]

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
        fwd = [t for t in fwd if t[0] not in IRIS_IDS] + iris_forward(kk)
        THF_A[kk] = anim(f"Motif Through {kk} (forward)", max(open_f, IRIS_F_END[kk]), fwd)
        bwd = merge(pose_tracks(kk, 0, 1.45, 0.0, -0.55, 0.0),
                    pose_tracks(kk, 8, 1.45, 0.0, -0.55, 0.0, ease=(0.3, 0.0, 0.25, 1.0)),
                    pose_tracks(kk, 40))
        bwd = [t for t in bwd if t[0] not in IRIS_IDS] + iris_back(kk)
        THB_A[kk] = anim(f"Motif Through {kk} (back)", 44, bwd)
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
                a_num("currentScreen", kk), a_bool("onSummary", kk == 10),
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

    # --- Control router: what the centre and right slots mean depends on onSummary
    R = {n_: nid() for n_ in ("idle", "next", "share", "toggle", "replay")}
    layers.append(layer("Control Router", R["idle"], [
        El("AnimationState",
           tr(R["next"], c_trig("primaryPressed"), c_bool("onSummary", False)),
           tr(R["share"], c_trig("primaryPressed"), c_bool("onSummary", True)),
           tr(R["toggle"], c_trig("secondaryPressed"), c_bool("onSummary", False)),
           tr(R["replay"], c_trig("secondaryPressed"), c_bool("onSummary", True)),
           animationId=tick.id, x=0.0, y=0.0, id=R["idle"]),
        El("AnimationState", a_trig("navNext"), tr(R["idle"]), animationId=tick.id, reset=True, x=260.0, y=-180.0, id=R["next"]),
        El("AnimationState", El("StateMachineFireEvent", eventId=ev_share.id, occursValue=0), tr(R["idle"]), animationId=tick.id,
           reset=True, x=260.0, y=-60.0, id=R["share"]),
        El("AnimationState", a_toggle("isPaused", CV_NOT), tr(R["idle"]), animationId=tick.id, reset=True, x=260.0, y=60.0, id=R["toggle"]),
        El("AnimationState", a_trig("navReplay"), tr(R["idle"]), animationId=tick.id, reset=True, x=260.0, y=180.0, id=R["replay"]),
    ]))

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
    L.append(lst("Primary (Continue / Share)", next_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_trig("primaryPressed")]))
    L.append(lst("Secondary (Pause / Replay)", pause_hit.id, [it("click"), kb("enter", "kpEnter"), sem_tap()], [a_trig("secondaryPressed")]))
    for idx, hb in ((1, prev_hit), (2, pause_hit), (3, next_hit)):
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
    ab = El("Artboard", style, stage, clock, layout_probe, seq_dummy, stage_bg, ev_screen, ev_share, ev_fin, sm, *A,
            viewModelId=VMID, viewModelInstanceId=INST_IDS["Fixture"], defaultStateMachineId=smid, styleId=style.id,
            width=float(W), height=float(H), x=0.0, y=0.0, name="Nocturne Recap")
    return ab


CLOCK_SCRIPT = nid()
LAYOUT_SCRIPT = nid()


def main():
    scenes = [scene1(), scene2(), scene3(), scene4(), scene5(), scene6(), scene7(), scene8(), scene9(), scene10()]
    main_ab = build_main()
    os.makedirs(OUT, exist_ok=True)
    files = {
        "00_data.rml": [VM_EL, *CONVERTERS, *FONTS, El("ScriptAsset", file="clock.luau", name="clock", id=CLOCK_SCRIPT),
                        El("ScriptAsset", file="layout.luau", name="layout", id=LAYOUT_SCRIPT),
                        *[El("ScriptAsset", file=SCRIPT_FILES[n], name=n, id=i) for n, i in SCRIPT_IDS.items()
                          if os.path.exists(os.path.join(HERE, "..", SCRIPT_FILES[n]))]],
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
