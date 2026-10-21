#!/usr/bin/env python3
"""Generates ../scene.rml for the Switchyard recap.

Run:  python3 tools/gen.py   (from apps/switchyard/rive)

The generator exists so ten scene layers x ~20 guarded transitions, the
rest/hidden poses derived from every keyed property, and the binding paths
into the single UserRecap view model stay consistent. The emitted RML is
plain, editable markup (and is what the .rev opens as).
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rml import *  # noqa: E402,F401,F403

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 390, 844
STORY_TOP, STORY_BOTTOM = 82, 740

# ======================================================================
# View model: exactly one, UserRecap
# ======================================================================
SAMPLE = json.load(open(os.path.join(ROOT, "fixtures", "sample.json")))
ZERO = json.load(open(os.path.join(ROOT, "fixtures", "zero-new-user.json")))
EXTREME = json.load(open(os.path.join(ROOT, "fixtures", "extreme-long-copy.json")))

# Adapter additions (documented in README): file-owned playheads and
# control signals live on the same UserRecap instance, prefixed with "_".
ADDITIONS = {
    "greetingLabel": ("String", "Hi,"),
    "_navDir": ("Number", 1),
    "_count2": ("Number", 0), "_count3": ("Number", 0), "_count4": ("Number", 0),
    "_count5": ("Number", 0), "_count6": ("Number", 0), "_count7": ("Number", 0),
    "_count8": ("Number", 0),
    "_personaSlot": ("Number", 0),
    "_isEmpty": ("Boolean", False),
    "_pauseButtonLabel": ("String", "Pause"),
    "_personaInk": ("Color", WHITE),
    "_activeRoute": ("Number", 0),
    "_focusIndex": ("Number", -1),
    "_nextTapped": ("Trigger", None),
    "_prevTapped": ("Trigger", None),
    "_pauseTapped": ("Trigger", None),
    "_replayTapped": ("Trigger", None),
    "_replay": ("Trigger", None),
}


def vm_type(name, value):
    if name == "personaColor":
        return "Color"
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, (int, float)):
        return "Number"
    return "String"


def hex_to_argb(s):
    s = s.lstrip("#")
    return ("FF" + s).upper() if len(s) == 6 else s.upper()


VM = E("ViewModel", name="UserRecap")
P = {}           # property name -> element
PTYPE = {}
for k, v in SAMPLE.items():
    t = vm_type(k, v)
    el = E(f"ViewModelProperty{t}", name=k)
    VM.add(el)
    P[k], PTYPE[k] = el, t
for k, (t, _) in ADDITIONS.items():
    el = E(f"ViewModelProperty{t}", name=k)
    VM.add(el)
    P[k], PTYPE[k] = el, t


def instance(name, data):
    inst = E("ViewModelInstance", exports=True, name=name)
    for k, el in P.items():
        t = PTYPE[k]
        if t == "Trigger":
            inst.add(E("ViewModelInstanceTrigger", viewModelPropertyId=el.id))
            continue
        v = data[k] if k in data else ADDITIONS[k][1]
        if t == "Color":
            v = hex_to_argb(v) if isinstance(v, str) and v.startswith("#") else v
        if t == "Number":
            v = float(v)
        inst.add(E(f"ViewModelInstance{t}", propertyValue=v, viewModelPropertyId=el.id))
    return inst


INST_FIXTURE = instance("Fixture", SAMPLE)
INST_ZERO = instance("NewUser", ZERO)
INST_EXTREME = instance("Extreme", EXTREME)
VM.add(INST_FIXTURE, INST_ZERO, INST_EXTREME)
VM.attrs["defaultInstanceId"] = INST_FIXTURE.id


def path(name):
    return f"{VM.id}-{P[name].id}"


def bind(name, key, conv=None, **kw):
    return E("DataBindContext", sourcePathIds=path(name), propertyKey=key,
             converterId=conv.id if conv is not None else None, **kw)


# ======================================================================
# Assets and converters
# ======================================================================
FONT_DISPLAY = E("FontAsset", file="assets/fonts/ArchivoBlack-Switchyard-Subset.ttf", name="Archivo Black")
FONT_TEXT = E("FontAsset", file="assets/fonts/Inter-Switchyard-Subset.ttf", name="Inter")
SCRIPT_FMT = E("ScriptAsset", file="scripts/formatCount.luau", name="formatCount")
SCRIPT_SEQ = E("ScriptAsset", file="scripts/sequencer.luau", name="sequencer")

CONV_FMT = E("ScriptedDataConverter", scriptAssetId=SCRIPT_FMT.id, name="Format count (locale grouping)")
CONV_YEAR = E("DataConverterToString", decimals=0, round=True, name="Year to text")
ROOTS = [CONV_FMT, CONV_YEAR]

COUNT_CONV = {}
for n in range(2, 9):
    f = E("DataConverterFormula",
          E("FormulaTokenInput"),
          E("FormulaTokenOperation", operationType=2),
          E("FormulaTokenValue", bind(f"_count{n}", 777)),
          name=f"Count-up s{n} (value x playhead)")
    g = E("DataConverterGroup", E("DataConverterGroupItem", converterId=f.id),
          E("DataConverterGroupItem", converterId=CONV_FMT.id), name=f"Hero s{n}: count + format")
    ROOTS += [f, g]
    COUNT_CONV[n] = g

_EQ = {}


def eq_conv(i):
    """1 when input == i, else 0  ->  1 - min(1, (in-i)*(in-i))."""
    if i in _EQ:
        return _EQ[i]
    c = E("DataConverterFormula",
          E("FormulaTokenValue", operationValue=1.0),
          E("FormulaTokenOperation", operationType=1),
          E("FormulaTokenFunction", functionType=0),
          E("FormulaTokenValue", operationValue=1.0),
          E("FormulaTokenArgumentSeparator"),
          E("FormulaTokenParenthesisOpen"), E("FormulaTokenInput"), E("FormulaTokenOperation", operationType=1),
          E("FormulaTokenValue", operationValue=float(i)), E("FormulaTokenParenthesisClose"),
          E("FormulaTokenOperation", operationType=2),
          E("FormulaTokenParenthesisOpen"), E("FormulaTokenInput"), E("FormulaTokenOperation", operationType=1),
          E("FormulaTokenValue", operationValue=float(i)), E("FormulaTokenParenthesisClose"),
          E("FormulaTokenParenthesisClose"),
          name=f"Equals {i} -> 1/0")
    ROOTS.append(c)
    _EQ[i] = c
    return c


def ramp_conv(lo, hi, out_lo, out_hi, name):
    c = E("DataConverterRangeMapper", minInput=float(lo), maxInput=float(hi), minOutput=float(out_lo),
          maxOutput=float(out_hi), clampLower=True, clampUpper=True, name=name)
    ROOTS.append(c)
    return c


# ======================================================================
# Text
# ======================================================================
def text(x, y, w, runs, size, color=BLACK, display=False, weight=400, align="left", h=None,
         overflow=None, sizing=None, lh=None, ls=None, name="Text", ink=None, ox=None, oy=None, valign=None,
         wrap=None, **extra):
    font = FONT_DISPLAY if display else FONT_TEXT
    sc = solid(color)
    if ink:
        sc.add(bind(ink, 37))
    st = E("TextStylePaint", E("Fill", sc, name="Fill"), fontSize=size, fontAssetId=font.id,
           familyName="Archivo Black" if display else "Inter",
           styleName="Regular" if (display or weight == 400) else {500: "Medium", 600: "SemiBold", 700: "Bold"}[weight],
           lineHeight=lh, letterSpacing=ls, name="Style")
    if not display:
        st.add(E("TextStyleAxis", tag=2003265652, axisValue=float(weight), name="Weight"))
    if sizing is None:
        sizing = "fixed" if h else ("autoHeight" if w else "autoWidth")
    t = E("Text", st, x=x, y=y, width=w if w else None, height=h, sizingValue=sizing, overflowValue=overflow,
          alignValue=align, verticalAlignValue=valign, originX=ox, originY=oy, wrapValue=wrap, name=name, **extra)
    for r in runs:
        if isinstance(r, str):
            t.add(E("TextValueRun", styleId=st.id, text=r, name="Run"))
        else:
            literal, prop, conv = (list(r) + [None, None])[:3]
            run = E("TextValueRun", styleId=st.id, text=literal, name=prop or "Run")
            if prop:
                run.add(bind(prop, 268, conv))
            t.add(run)
    return t


def reveal_modifier(t, units="words", dy=26.0, rot=None):
    """Glyph-group reveal: everything inside the range is hidden & dropped.
    Rest pose (authored) = fully revealed."""
    rng = E("TextModifierRange", modifyFrom=1.0, modifyTo=1.0, falloffFrom=1.35, falloffTo=1.0,
            unitsValue=units, name="Reveal Range")
    g = E("TextModifierGroup", rng, modifyOpacity=True, modifyTranslation=True, invertOpacity=True,
          opacity=0.0, y=dy, x=0.0, name="Reveal")
    if rot is not None:
        g.attrs["modifyRotation"] = True
        g.attrs["rotation"] = rot
    t.add(g)
    return rng


def key_reveal(anim, rng, f0, f1, ease=EIO):
    anim.key(rng, "modifyFrom", (0, -0.4, "hold"), (f0, -0.4, ease), (f1, 1.0, "lin"))
    anim.key(rng, "falloffFrom", (0, 0.0, "hold"), (f0, 0.0, ease), (f1, 1.35, "lin"))
    anim.key(rng, "modifyTo", (0, 1.0, "hold"))
    anim.key(rng, "falloffTo", (0, 1.0, "hold"))


# ======================================================================
# Scenes
# ======================================================================
RING_D = 32.0
FULL = 1900.0
Q = (195.0, 720.0)        # where the route dot departs from (bottom of the story window)


class Scene:
    def __init__(self, n, ring, bg, bg_bind=None):
        self.n, self.P = n, ring
        self.disc_path = E("Ellipse", width=FULL, height=FULL, name="Disc")
        self.disc = E("Shape", self.disc_path, x=float(ring[0]), y=float(ring[1]),
                      name=f"S{n} interchange disc (clip source)")
        self.content = node("Content")
        bgr = rect(0, 0, W, H, bg, name="Background")
        if bg_bind:
            bgr.children[1].children[0].add(bind(bg_bind, 37))
        self.bg = bgr
        self.root = node(f"Scene {n}", E("ClippingShape", sourceId=self.disc.id, name="Interchange clip"),
                         self.content, bgr, opacity=1.0 if n == 1 else 0.0)
        self.anims = {}
        self.extra_rest = []        # (obj, prop, value) forced into Hidden/Settled
        self.hidden_only = []       # (obj, prop, value) only in Hidden
        self.sems = []              # SemanticData hidden while the scene is offscreen

    def anim(self, name, dur, loop="oneShot"):
        a = Anim(f"S{self.n} {name}", dur, loop)
        self.anims[name] = a
        return a

    def add(self, *els):
        self.content.add(*els)


SCENES = {}

# ---------------- motif (persistent object carried between scenes)
MOTIF_RING_PATH = E("Ellipse", width=RING_D, height=RING_D, name="Ring")
MOTIF_RING = E("Shape", MOTIF_RING_PATH, stroke(BLACK, 6.0, "Ring stroke"), x=195.0, y=400.0, name="Interchange ring")
MOTIF_DOT = circle(Q[0], Q[1], 18.0, RED, name="Route dot", line=BLACK, lw=3.5)
MOTIF_TRAIL, MOTIF_TRAIL_TRIM = route([Q, Q], RED, 6, name="Dot trail")
MOTIF = node("Motif (persistent route dot + interchange ring)", MOTIF_DOT, MOTIF_RING, MOTIF_TRAIL, opacity=0.0)


def dot_path(p_from, p_to):
    """Angular schematic route from one point to another: vertical, then 45 degrees."""
    (x0, y0), (x1, y1) = p_from, p_to
    d = abs(x1 - x0)
    ymid = y1 + d if y0 > y1 else y1 - d
    if (y0 > y1 and ymid > y0) or (y0 < y1 and ymid < y0):
        return [p_from, p_to]
    return [p_from, (x0, ymid), p_to]


def key_along(anim, obj, pts, f0, f1, ease=None):
    """Key obj.x/.y through a polyline, timing proportional to distance."""
    fr = vertex_fractions(pts)
    for i, (p, u) in enumerate(zip(pts, fr)):
        f = round(f0 + (f1 - f0) * u)
        e = "lin" if i < len(pts) - 1 else "lin"
        if i == 0 and ease:
            e = ease
        anim.key(obj, "x", (f, float(p[0]), e))
        anim.key(obj, "y", (f, float(p[1]), e))


def motif_enter(sc, a, ring_at=12, expand=(12, 42), extra_orbit=None):
    """Signature transition: a route dot runs into an interchange ring which
    expands to become the next scene."""
    Px, Py = sc.P
    pts = dot_path(Q, sc.P)
    a.key(MOTIF, "opacity", (0, 1.0, "hold"))
    a.key(MOTIF_DOT, "opacity", (0, 1.0, "hold"), (expand[0] + 2, 1.0, "lin"), (expand[0] + 6, 0.0, "hold"))
    key_along(a, MOTIF_DOT, pts, 0, ring_at, ease=SOFT)
    a.key(MOTIF_RING, "x", (0, float(Px), "hold"))
    a.key(MOTIF_RING, "y", (0, float(Py), "hold"))
    a.key(MOTIF_RING, "opacity", (0, 1.0, "hold"), (expand[1] - 10, 1.0, "lin"), (expand[1], 0.0, "hold"))
    a.key(MOTIF_RING_PATH, "width", (0, 0.0, POP), (6, RING_D + 6, SOFT), (expand[0], RING_D - 6, EIO),
          (expand[1], FULL, "hold"))
    a.key(MOTIF_RING_PATH, "height", (0, 0.0, POP), (6, RING_D + 6, SOFT), (expand[0], RING_D - 6, EIO),
          (expand[1], FULL, "hold"))
    # trail: the route draws behind the dot then retracts into the ring
    a.key(MOTIF_TRAIL, "opacity", (0, 1.0, "hold"), (expand[0] + 4, 0.0, "hold"))
    for i, p in enumerate([Q, sc.P]):
        pass
    a.key(sc.disc_path, "width", (0, 0.0, "hold"), (expand[0], 0.0, EIO), (expand[1], FULL, "hold"))
    a.key(sc.disc_path, "height", (0, 0.0, "hold"), (expand[0], 0.0, EIO), (expand[1], FULL, "hold"))


def motif_exit_back(sc, a, dur=40):
    """Reverse transition: the scene collapses back into its interchange ring and
    the dot departs downward, revealing the previous scene underneath."""
    Px, Py = sc.P
    a.key(MOTIF, "opacity", (0, 1.0, "hold"), (dur, 0.0, "hold"))
    a.key(MOTIF_RING, "x", (0, float(Px), "hold"))
    a.key(MOTIF_RING, "y", (0, float(Py), "hold"))
    a.key(MOTIF_RING, "opacity", (0, 1.0, "hold"), (dur - 6, 1.0, "lin"), (dur, 0.0, "hold"))
    for prop in ("width", "height"):
        a.key(MOTIF_RING_PATH, prop, (0, FULL, (0.5, 0.0, 0.3, 1.0)), (24, RING_D, POP), (30, RING_D + 6, SOFT),
              (dur, 0.0, "hold"))
        a.key(sc.disc_path, prop, (0, FULL, (0.5, 0.0, 0.3, 1.0)), (24, 0.0, "hold"))
    a.key(MOTIF_DOT, "opacity", (0, 0.0, "hold"), (24, 1.0, "lin"), (dur, 0.0, "hold"))
    pts = list(reversed(dot_path(Q, sc.P)))
    key_along(a, MOTIF_DOT, pts, 24, dur, ease=EI)
    a.key(MOTIF_TRAIL, "opacity", (0, 0.0, "hold"))


def content_exit_fwd(sc, a, dur=44):
    a.key(sc.content, "y", (0, 0.0, EIO), (dur, -28.0, "hold"))
    a.key(sc.content, "opacity", (0, 1.0, "hold"), (24, 1.0, SOFT), (dur, 0.0, "hold"))
    a.key(MOTIF_TRAIL, "opacity", (0, 0.0, "hold"))


def content_enter_back(sc, a, dur=48):
    a.key(sc.content, "x", (0, -36.0, EO), (dur, 0.0, "hold"))
    a.key(sc.content, "opacity", (0, 0.35, EO), (30, 1.0, "hold"))


# ======================================================================
# Chrome: header ticket band, dock ticket band, controls
# ======================================================================
def wordmark(x, y, size=19, name="Wordmark"):
    """Original Switchyard wordmark: a red route stub entering an interchange ring."""
    s = size / 19.0
    return node(name,
                text(18 * s, -size * 0.62, None, ["Switchyard"], size, BLACK, display=True, name="Wordmark text"),
                circle(8 * s, 0, 13 * s, WHITE, name="Ring", line=BLACK, lw=3.2 * s),
                rect(-8 * s, -3 * s, 14 * s, 6 * s, RED, r=3 * s, name="Route stub"),
                x=float(x), y=float(y))


YEAR_TEXT = text(366, 22, None, [("2026", "year", CONV_YEAR)], 15, BLACK, weight=600, ox=1.0, name="Year")
HEADER = node("Header ticket band",
              wordmark(26, 32),
              YEAR_TEXT,
              route([(0, 81), (W, 81)], BLACK, 2, name="Perforation", trim=False, dash=[5, 5], cap="butt")[0],
              rect(0, 0, W, 82, WHITE, name="Band"))

BUTTONS = {}
SEMS = {}
LISTENERS = []
FOCUS_INDEX = {"prev": 0, "pause": 1, "continue": 2, "share": 3, "replay": 4}


def vm_trigger_write(name):
    return E("ListenerViewModelChange",
             E("BindablePropertyTrigger", bind(name, 686, direction=True), propertyValue=1))


def vm_num_write(name, v):
    return E("ListenerViewModelChange",
             E("BindablePropertyNumber", bind(name, 636, direction=True), propertyValue=float(v)))


def button(key, cx, w, h, bg, label_prop, ink, action, outline=None, icon=None, label=True, semantic_prop=None):
    shape = rect(0, 0, w, h, bg, r=h / 2, name=f"{key} hit + plate", ox=0.5, oy=0.5,
                 line=outline, lw=2.5 if outline else 0)
    focus = E("FocusData", name="Focus")
    shape.children.insert(0, focus)
    sem = E("SemanticData", bind(semantic_prop or label_prop, 983), role="button", label=SAMPLE.get(label_prop, "Pause"),
            name="Semantics")
    shape.children.insert(0, sem)
    SEMS[key] = sem
    ring = E("Shape", E("Rectangle", width=w + 10, height=h + 10, originX=0.5, originY=0.5,
                        cornerRadiusTL=(h + 10) / 2, name="Path"), stroke(BLUE, 3.0, "Focus ring"),
             name="Focus ring", opacity=0.0)
    ring.add(bind("_focusIndex", 18, eq_conv(FOCUS_INDEX[key])))
    kids = [ring]
    if icon:
        kids.append(icon)
    if label:
        pad = 22 if icon else 18
        lt = text(-w / 2 + pad, 0, w - (64 if icon else 2 * pad), [(SAMPLE[label_prop], label_prop)], 17, ink,
                  weight=600, h=24, oy=0.5, valign="middle", overflow="ellipsis", wrap="noWrap",
                  align="left", name=f"{key} label")
        kids.append(lt)
    kids.append(shape)
    n = node(f"Button {key}", *kids, x=float(cx), y=790.0)
    BUTTONS[key] = (n, shape, focus)
    lst = E("StateMachineListener",
            E("ListenerInputType", listenerTypeValue="click"),
            E("ListenerInputTypeKeyboard", E("KeyboardInput", keyType="enter", keyPhase=1),
              E("KeyboardInput", keyType="kpEnter", keyPhase=1), listenerTypeValue="keyboard"),
            E("ListenerInputTypeSemantic", E("SemanticInput", actionType="tap"), listenerTypeValue="semanticAction"),
            *action, targetId=shape.id, name=f"{key} activate")
    LISTENERS.append(lst)
    LISTENERS.append(E("StateMachineListener", E("ListenerInputType", listenerTypeValue="focus"),
                       vm_num_write("_focusIndex", FOCUS_INDEX[key]), targetId=shape.id, name=f"{key} focus"))
    LISTENERS.append(E("StateMachineListener", E("ListenerInputType", listenerTypeValue="blur"),
                       vm_num_write("_focusIndex", -1), targetId=shape.id, name=f"{key} blur"))
    return n


def chevron(pts, color, t=3.2, name="Icon"):
    return route(pts, color, t, name=name, radius=0, trim=False)[0]


PAUSE_BARS = node("Pause bars", rect(-7, -9, 5, 18, BLACK, r=1.5, name="Bar L"), rect(2, -9, 5, 18, BLACK, r=1.5, name="Bar R"))
PLAY_TRI = path_shape([(-5, -9), (9, 0), (-5, 9)], BLACK, name="Play triangle", opacity=0.0)
# SWITCHYARD_DEBUG_EVENTS=1 builds the three host events as OpenUrlEvents so a
# headless run logs "url event://<name>" each time one fires (test harness only).
DEBUG_EVENTS = os.environ.get("SWITCHYARD_DEBUG_EVENTS") == "1"


def host_event(name, *children):
    if DEBUG_EVENTS:
        return E("OpenUrlEvent", *children, url=f"event://{name}", targetValue=0, name=name)
    return E("Event", *children, name=name)


SHARE_EVENT = host_event("shareTapped")

BTN_PREV = button("prev", 50, 52, 52, WHITE, "previousLabel", BLACK, [vm_trigger_write("_prevTapped")],
                  outline=BLACK, icon=chevron([(4, -9), (-5, 0), (4, 9)], BLACK, name="Chevron"), label=False)
BTN_PAUSE = button("pause", 114, 52, 52, WHITE, "pauseLabel", BLACK, [vm_trigger_write("_pauseTapped")],
                   outline=BLACK, icon=node("Pause icon", PAUSE_BARS, PLAY_TRI), label=False,
                   semantic_prop="_pauseButtonLabel")
BTN_CONT = button("continue", 259, 214, 56, BLACK, "continueLabel", WHITE, [vm_trigger_write("_nextTapped")],
                  icon=node("Arrow", chevron([(70, 0), (88, 0)], WHITE, 2.6, "Shaft"),
                            chevron([(81, -7), (88, 0), (81, 7)], WHITE, 2.6, "Head")))
BTN_SHARE = button("share", 1207, 110, 56, RED, "shareLabel", WHITE, [E("ListenerFireEvent", eventId=SHARE_EVENT.id)])
BTN_REPLAY = button("replay", 1318, 96, 56, WHITE, "replayLabel", BLACK, [vm_trigger_write("_replayTapped")],
                    outline=BLACK)
# Dock focus: summary-only buttons start unfocusable (keyed by the Dock layer)
BUTTONS["share"][2].attrs["canFocus"] = False
BUTTONS["replay"][2].attrs["canFocus"] = False

DOCK = node("Dock ticket band",
            BTN_PREV, BTN_PAUSE, BTN_CONT, BTN_SHARE, BTN_REPLAY,
            route([(0, 741), (W, 741)], BLACK, 2, name="Perforation", trim=False, dash=[5, 5], cap="butt")[0],
            rect(0, 740, W, 104, WHITE, name="Band"))

# ======================================================================
# Scene builders live in scenes.py (imported for side effects)
# ======================================================================
import scenes  # noqa: E402

scenes.build(globals())

# ======================================================================
# State machine
# ======================================================================
def bp(kind, name, key):
    return E(f"BindableProperty{kind}", bind(name, key))


def c_num(name, op, val):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator", bp("Number", name, 636)),
             E("TransitionValueNumberComparator", value=float(val)), opValue=op)


def c_bool(name, val):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator", bp("Boolean", name, 634)),
             E("TransitionValueBooleanComparator", value=val), opValue="equal")


def c_str(name, op, val):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator", bp("String", name, 635)),
             E("TransitionValueStringComparator", value=val), opValue=op)


def c_trig(name):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator", bp("Trigger", name, 686)),
             E("TransitionValueTriggerComparator"))


def go(to, *conds, dur=0, exit_pct=None, ease=None):
    t = E("StateTransition", *conds, stateToId=to.id, duration=dur if dur else None)
    if exit_pct is not None:
        t.attrs.update(enableExitTime=True, exitTimeIsPercetange=True, exitTime=exit_pct)
    if ease:
        t.add(E("CubicEaseInterpolator", x1=ease[0], y1=ease[1], x2=ease[2], y2=ease[3]))
        t.attrs["interpolationType"] = "cubic"
    return t


ANIMS = []          # every LinearAnimation (declared after the machine)
LAYERS = []


def state(anim, x, y, **kw):
    if anim not in ANIMS:
        ANIMS.append(anim)
    return E("AnimationState", animationId=anim.build().id, x=float(x), y=float(y), **kw)


def layer(name, entry_to, states, ex=0):
    l = E("StateMachineLayer", E("AnyState", x=float(ex + 700), y=-200.0), E("ExitState", x=float(ex + 900), y=-200.0),
          E("EntryState", go(entry_to), x=0.0, y=0.0), *states, name=name)
    LAYERS.append(l)
    return l


def collect_rest(sc):
    rest = {}
    for a in sc.anims.values():
        for (obj, prop) in a.order:
            if obj in (MOTIF, MOTIF_DOT, MOTIF_RING, MOTIF_RING_PATH, MOTIF_TRAIL, MOTIF_TRAIL_TRIM):
                continue
            if obj is sc.root:
                continue
            rest[(obj, prop)] = rest_value(obj, prop)
    for obj, prop, v in sc.extra_rest:
        rest[(obj, prop)] = v
    return rest


def scene_layer(sc):
    n = sc.n
    rest = collect_rest(sc)
    hidden = Anim(f"S{n} Hidden", 1)
    settled = Anim(f"S{n} Settled", 1)
    for (obj, prop), v in rest.items():
        hidden.hold(obj, prop, v)
        settled.hold(obj, prop, v)
    for obj, prop, v in sc.hidden_only:
        hidden.hold(obj, prop, v)
    hidden.hold(sc.root, "opacity", 0.0)
    for sem in sc.sems:
        hidden.hold(sem, "isHidden", True)
        settled.hold(sem, "isHidden", False)
        for name, a in sc.anims.items():
            if name.startswith("Enter"):
                a.hold(sem, "isHidden", False)
            elif name.startswith("Exit"):
                a.hold(sem, "isHidden", True)
    settled.hold(sc.root, "opacity", 1.0)
    settled.hold(MOTIF, "opacity", 0.0)
    for name, a in sc.anims.items():
        if name != "Idle":
            a.hold(sc.root, "opacity", 1.0)
    for name in ("EnterBack", "ExitFwd"):
        a = sc.anims[name]
        for prop in ("width", "height"):
            if not a.has(sc.disc_path, prop):
                a.hold(sc.disc_path, prop, FULL)

    cs_is = c_num("currentScreen", "equal", n)
    rm_off, rm_on = c_bool("reducedMotion", False), c_bool("reducedMotion", True)
    paused, playing = c_bool("isPaused", True), c_bool("isPaused", False)
    fwd, back = c_num("_navDir", "greaterThan", 0), c_num("_navDir", "lessThan", 0)

    S_H = state(hidden, 160, 0)
    enters = []
    if n == 9:
        for p in range(4):
            enters.append((state(sc.anims[f"EnterFwd{p}"], 420, -300 + 110 * p), p))
    else:
        enters.append((state(sc.anims["EnterFwd"], 420, -200), None))
    S_EB = state(sc.anims["EnterBack"], 420, 220)
    S_I = state(sc.anims["Idle"], 700, 0)
    S_S = state(settled, 700, 260)
    S_XF = state(sc.anims["ExitFwd"], 980, -160)
    S_XB = state(sc.anims["ExitBack"], 980, 160)

    def ef_conds(p):
        c = [c_num("currentScreen", "equal", n), c_num("_navDir", "greaterThan", 0), c_bool("reducedMotion", False)]
        if p is not None:
            c.append(c_num("_personaSlot", "equal", p))
        return c

    for st, p in enters:
        S_H.add(go(st, *ef_conds(p)))
    S_H.add(go(S_EB, c_num("currentScreen", "equal", n), c_num("_navDir", "lessThan", 0), c_bool("reducedMotion", False)))
    S_H.add(go(S_S, c_num("currentScreen", "equal", n), c_bool("reducedMotion", True), dur=220))

    live = [st for st, _ in enters] + [S_EB, S_I, S_S]
    for st in live:
        st.add(go(S_XF, c_num("currentScreen", "greaterThan", n), c_bool("reducedMotion", False), dur=90))
        st.add(go(S_XB, c_num("currentScreen", "lessThan", n), c_bool("reducedMotion", False), dur=90))
        st.add(go(S_H, c_num("currentScreen", "notEqual", n), c_bool("reducedMotion", True), dur=220))
    for st in [s for s, _ in enters] + [S_EB]:
        st.add(go(S_I, c_bool("isPaused", False), c_bool("reducedMotion", False), exit_pct=100))
        st.add(go(S_S, c_bool("isPaused", True), exit_pct=100))
        st.add(go(S_S, c_bool("reducedMotion", True), dur=220))
    S_I.add(go(S_S, c_bool("isPaused", True), dur=320))
    S_I.add(go(S_S, c_bool("reducedMotion", True), dur=220))
    S_S.add(go(S_I, c_num("currentScreen", "equal", n), c_bool("isPaused", False), c_bool("reducedMotion", False),
               dur=320))
    for st in (S_XF, S_XB):
        st.add(go(S_H, exit_pct=100))
        for est, p in enters:
            st.add(go(est, *ef_conds(p), dur=120))
        st.add(go(S_EB, c_num("currentScreen", "equal", n), c_num("_navDir", "lessThan", 0),
                  c_bool("reducedMotion", False), dur=120))
        st.add(go(S_S, c_num("currentScreen", "equal", n), c_bool("reducedMotion", True), dur=220))
    states = [S_H] + [s for s, _ in enters] + [S_EB, S_I, S_S, S_XF, S_XB]
    return layer(f"Scene {n}", S_H, states)


for n in range(1, 11):
    scene_layer(SCENES[n])

# -------- screenChanged tracker (one state per canonical id; event payload = screen)
EV_SCREEN = host_event("screenChanged",
                       E("CustomPropertyNumber", bind("currentScreen", 243), propertyValue=1.0, name="screen"))
EV_FINISHED = host_event("recapFinished")
BLIP = Anim("Util blip", 1)
TRACK = [state(BLIP, 200 + 120 * (i % 5), 120 * (i // 5)) for i in range(10)]
for i, st in enumerate(TRACK):
    st.add(E("StateMachineFireEvent", eventId=EV_SCREEN.id, occursValue="atStart"))
    for j, other in enumerate(TRACK):
        if i != j:
            st.add(go(other, c_num("currentScreen", "equal", j + 1)))
TRACK_ENTRY = state(BLIP, 60, 300)
for j, other in enumerate(TRACK):
    TRACK_ENTRY.add(go(other, c_num("currentScreen", "equal", j + 1)))
layer("Events: screenChanged", TRACK_ENTRY, [TRACK_ENTRY] + TRACK)

# -------- recapFinished latch
SETTLE = Anim("Util summary settle", 108)
F_WAIT = state(BLIP, 160, 0)
F_SETTLING = state(SETTLE, 360, 0)
F_DONE = state(BLIP, 560, 0)
F_DONE.add(E("StateMachineFireEvent", eventId=EV_FINISHED.id, occursValue="atStart"))
F_WAIT.add(go(F_SETTLING, c_num("currentScreen", "equal", 10)))
F_SETTLING.add(go(F_WAIT, c_num("currentScreen", "notEqual", 10)))
F_SETTLING.add(go(F_DONE, exit_pct=100))
F_DONE.add(go(F_WAIT, c_trig("_replay")))
layer("Events: recapFinished latch", F_WAIT, [F_WAIT, F_SETTLING, F_DONE])

# -------- dock: Continue vs Share/Replay
cont, share, replay = BUTTONS["continue"], BUTTONS["share"], BUTTONS["replay"]
DOCK_N = Anim("Dock normal", 1)
DOCK_S = Anim("Dock summary", 24)
for a, (cx, sx, rx), foc in ((DOCK_N, (259, 1207, 1318), (True, False, False)),
                             (DOCK_S, (-1000, 207, 318), (False, True, True))):
    a.hold(cont[0], "x", float(cx))
    a.hold(share[0], "x", float(sx))
    a.hold(replay[0], "x", float(rx))
    a.key(cont[2], "canFocus", (0, foc[0], "hold"))
    a.key(SEMS["continue"], "isHidden", (0, not foc[0], "hold"))
    a.key(SEMS["share"], "isHidden", (0, not foc[1], "hold"))
    a.key(SEMS["replay"], "isHidden", (0, not foc[2], "hold"))
    a.key(share[2], "canFocus", (0, foc[1], "hold"))
    a.key(replay[2], "canFocus", (0, foc[2], "hold"))
DOCK_S.key(share[0], "scaleX", (0, 0.6, POP), (18, 1.0, "hold"))
DOCK_S.key(share[0], "scaleY", (0, 0.6, POP), (18, 1.0, "hold"))
DOCK_S.key(replay[0], "scaleX", (4, 0.6, POP), (22, 1.0, "hold"))
DOCK_S.key(replay[0], "scaleY", (4, 0.6, POP), (22, 1.0, "hold"))
D_N = state(DOCK_N, 200, 0)
D_S = state(DOCK_S, 400, 0)
D_N.add(E("FocusActionTarget", targetId=cont[1].id))
D_S.add(E("FocusActionTarget", targetId=share[1].id))
D_N.add(go(D_S, c_num("currentScreen", "equal", 10)))
D_S.add(go(D_N, c_num("currentScreen", "notEqual", 10)))
layer("Dock", D_N, [D_N, D_S])

# -------- pause icon
PI_PLAY = Anim("Pause icon playing", 1)
PI_PAUSED = Anim("Pause icon paused", 1)
PI_PLAY.hold(PAUSE_BARS, "opacity", 1.0).hold(PLAY_TRI, "opacity", 0.0)
PI_PAUSED.hold(PAUSE_BARS, "opacity", 0.0).hold(PLAY_TRI, "opacity", 1.0)
PS1, PS2 = state(PI_PLAY, 200, 0), state(PI_PAUSED, 400, 0)
PS1.add(go(PS2, c_bool("isPaused", True), dur=120))
PS2.add(go(PS1, c_bool("isPaused", False), dur=120))
layer("Pause icon", PS1, [PS1, PS2])

scenes.extra_layers(globals())

# -------- keyboard root listeners
KEYROOT_FOCUS = E("FocusData", canFocus=False, name="Key scope")


def key_listener(name, keys, *actions, mods=0):
    return E("StateMachineListener",
             E("ListenerInputTypeKeyboard",
               *[E("KeyboardInput", keyType=k, keyPhase=1, modifiers=mods or None) for k in keys],
               listenerTypeValue="keyboard"),
             *actions, name=name)


KEYROOT = node("Recap", KEYROOT_FOCUS, HEADER, DOCK, MOTIF,
               *[SCENES[n].root for n in range(10, 0, -1)],
               node("Clip sources", *[SCENES[n].disc for n in range(1, 11)]))
for l in [key_listener("Key next", ["right"], vm_trigger_write("_nextTapped")),
          key_listener("Key previous", ["left"], vm_trigger_write("_prevTapped")),
          key_listener("Key pause", ["space"], vm_trigger_write("_pauseTapped")),
          key_listener("Key tab", ["tab"], E("FocusActionTraversal", traversalKind="next")),
          key_listener("Key shift-tab", ["tab"], E("FocusActionTraversal", traversalKind="previous"), mods=1)]:
    l.attrs["targetId"] = KEYROOT.id
    LISTENERS.append(l)

SM = E("StateMachine", *LISTENERS, *LAYERS, name="Recap Sequencer")

ART_STYLE = E("LayoutComponentStyle", name="Artboard Style")
ROOT_STYLE = E("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fill",
               widthUnitsValue="auto", heightUnitsValue="auto", name="Style")
SEQ = E("ScriptedLayout", E("FocusData", canFocus=False, name="No focus"), scriptAssetId=SCRIPT_SEQ.id,
        name="Sequencer (gestures, timer, progress)")
ARTBOARD = E("Artboard",
             ART_STYLE,
             E("LayoutComponent", ROOT_STYLE, SEQ, width=float(W), height=float(H), styleId=ROOT_STYLE.id,
               name="Sequencer layer"),
             KEYROOT,
             SHARE_EVENT, EV_SCREEN, EV_FINISHED,
             SM,
             *[a.build() for a in ANIMS],
             defaultStateMachineId=SM.id, viewModelId=VM.id, viewModelInstanceId=INST_FIXTURE.id,
             styleId=ART_STYLE.id, width=float(W), height=float(H), clip=True, name="Switchyard Recap")

doc = E("Rive", ARTBOARD, FONT_DISPLAY, FONT_TEXT, SCRIPT_FMT, SCRIPT_SEQ, *ROOTS, VM, version=1, kind="fragment")
out = os.path.join(ROOT, "scene.rml")
with open(out, "w") as f:
    f.write("<!-- GENERATED by tools/gen.py - edit the generator, or edit here and stop regenerating. -->\n")
    f.write(doc.xml())
    f.write("\n")
print("wrote", out, "animations:", len(ANIMS), "layers:", len(LAYERS))
