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
    # Responsive contract addition (host-owned): artboard width at or above which the
    # landscape layout is used; below it the portrait layout. Default 768.
    "layoutBreakpoint": ("Number", 768),
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
    "_focusVisible": ("Number", 0),
    "_nextTapped": ("Trigger", None),
    "_prevTapped": ("Trigger", None),
    "_pauseTapped": ("Trigger", None),
    "_replayTapped": ("Trigger", None),
    "_replay": ("Trigger", None),
}
# Idle-loop playheads (-1..1), one per scene, written by the sequencer and read by a
# Joystick per scene: they only advance while that scene is current, settled, not
# paused and not in reduced motion, so pause truly freezes decorative motion.
for _n in range(1, 11):
    ADDITIONS[f"_idle{_n}"] = ("Number", -1)


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


def add_num(name, default=0.0):
    """A file-owned number on UserRecap (declared on first use, before the instances)."""
    if name not in P:
        el = E("ViewModelPropertyNumber", name=name)
        VM.add(el)
        P[name], PTYPE[name] = el, "Number"
        ADDITIONS[name] = ("Number", float(default))
    return name


def path(name):
    return f"{VM.id}-{P[name].id}"


def bind(name, key, conv=None, **kw):
    return E("DataBindContext", sourcePathIds=path(name), propertyKey=key,
             converterId=conv.id if conv is not None else None, **kw)


# ======================================================================
# Assets and converters
# ======================================================================
FONT_DISPLAY = E("FontAsset", file="assets/fonts/ArchivoBlack-Regular.ttf", name="Archivo Black")
FONT_COND = E("FontAsset", file="assets/fonts/ArchivoCondensedBlack-Switchyard.ttf", name="Archivo Condensed Black")
FONT_TEXT = E("FontAsset", file="assets/fonts/Inter-Switchyard.ttf", name="Inter")
SCRIPT_FMT = E("ScriptAsset", file="scripts/formatCount.luau", name="formatCount")
# modules first: require() only finds a module declared above the script that imports it
SCRIPT_LDATA = E("ScriptAsset", file="scripts/layoutdata.luau", isModule=True, folderPath="scripts", name="layoutdata")
SCRIPT_LAYOUT = E("ScriptAsset", file="scripts/layout.luau", isModule=True, folderPath="scripts", name="layout")
SCRIPT_SEQ = E("ScriptAsset", file="scripts/sequencer.luau", name="sequencer")
SCRIPT_P3 = E("ScriptAsset", file="scripts/poster3d.luau", name="poster3d")
SCRIPT_FLAP = E("ScriptAsset", file="scripts/flapboard.luau", name="flapboard")
SCRIPT_PAPER = E("ScriptAsset", file="scripts/paper.luau", name="paper")

CONV_FMT = E("ScriptedDataConverter", scriptAssetId=SCRIPT_FMT.id, name="Format count (locale grouping)")
CONV_YEAR = E("DataConverterToString", decimals=0, round=True, name="Year to text")
ROOTS = [CONV_FMT, CONV_YEAR]
# -x : the inverse offset of a pivot wrapper (pivot at p, child at -p)
CONV_NEG = E("DataConverterFormula", E("FormulaTokenInput"), E("FormulaTokenOperation", operationType=2),
             E("FormulaTokenValue", operationValue=-1.0), name="Negate (pivot inverse)")
ROOTS.append(CONV_NEG)

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
    font = FONT_COND if display == "cond" else (FONT_DISPLAY if display else FONT_TEXT)
    sc = solid(color)
    if ink:
        sc.add(bind(ink, 37))
    st = E("TextStylePaint", E("Fill", sc, name="Fill"), fontSize=size, fontAssetId=font.id,
           familyName=font.attrs["name"],
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
IDLE_FRAMES = 480        # every idle loop is 8 s long (sequencer.luau IDLE_SECONDS)
Q = (195.0, 724.0)        # where the route dot departs from (bottom of the story window)
CENTER = (195.0, 411.0)   # centre of the story window (outgoing scenes recede toward it)
# Interchange roundel bands, inner to outer: the next scene shows through the
# centre; each band rides just outside the clip edge as the roundel expands.
BANDS = ((BLUE, 14.0, 7.0), (YEL, 14.0, 21.0), (RED, 14.0, 35.0), (BLACK, 6.0, 45.0))
EXPAND = (0.6, 0.0, 0.16, 1.0)   # slow start, very fast middle, long settle: a "breath"


# ----------------------------------------------------------------------
# Responsive layout plumbing. The artboard follows the canvas (layout fit);
# scripts/layout.luau solves a placement for the real size and writes the
# file-owned numbers below into UserRecap. Every wrapper bound here is never
# keyed by a timeline, so choreography (keyed in 390 x 844 design units inside
# the wrappers) and layout (on the wrappers) never fight.
# ----------------------------------------------------------------------
LAYOUT_BOXES = {}       # placed-group key -> design box (x0, y0, x1, y1), exported to layoutdata.luau
for _k, _v in (("_vw", W), ("_vh", H), ("_landscape", 0), ("_cs", 1), ("_scx", 195), ("_scy", 411),
               ("_artClipW", W), ("_copyClipX", 0), ("_copyClipW", W), ("_copyW", 342)):
    add_num(_k, _v)


def placed(key, *children, box=None, clip=None, name=None):
    """Wrapper whose x, y and uniform scale come from the layout solver (_<key>X/Y/S).
    Children stay in design units; `clip` restricts the group to the art panel or
    the copy column in landscape (the clip sources cover everything in portrait)."""
    add_num(f"_{key}X", 0.0)
    add_num(f"_{key}Y", 0.0)
    add_num(f"_{key}S", 1.0)
    g = node(name or f"{key} [placed]", *children)
    if clip is not None:
        g.children.insert(0, E("ClippingShape", sourceId=clip.id, name="Panel clip"))
    g.add(bind(f"_{key}X", 13), bind(f"_{key}Y", 14), bind(f"_{key}S", 16), bind(f"_{key}S", 17))
    if box is not None:
        LAYOUT_BOXES[key] = tuple(float(v) for v in box)
    return g


def offset(key, *children, name=None):
    """Wrapper moved inside its group by the solver (_<key>X/Y, design units)."""
    add_num(f"_{key}X", 0.0)
    add_num(f"_{key}Y", 0.0)
    g = node(name or f"{key} [offset]", *children)
    g.add(bind(f"_{key}X", 13), bind(f"_{key}Y", 14))
    return g


def shown(key, *children, default=1.0, name=None):
    """Wrapper whose opacity the solver sets (0/1) for one arrangement or another."""
    add_num(f"_{key}O", default)
    g = node(name or f"{key} [shown]", *children, opacity=float(default))
    g.add(bind(f"_{key}O", 18))
    return g


def full_rect(color, name, **attrs):
    """A rectangle that always covers the real artboard (bleeds edge to edge)."""
    r = E("Rectangle", width=float(W), height=float(H), originX=0.0, originY=0.0, name="Path")
    r.add(bind("_vw", 20), bind("_vh", 21))
    return E("Shape", r, fill(color), x=0.0, y=0.0, name=name, **attrs)


def pivot(name, child, px, py, dx, dy, scale=None):
    """pivot(child) -> Node at (px,py) holding a keyed node whose child sits at
    (-px,-py): scaling the keyed node then scales about the bound point."""
    p = node(name, child, x=float(dx), y=float(dy))
    p.add(bind(px, 13), bind(py, 14))
    if scale:
        p.add(bind(scale, 16), bind(scale, 17))
    return p


def unpivot(name, *children, px, py, dx, dy):
    u = node(name, *children, x=-float(dx), y=-float(dy))
    u.add(bind(px, 13, CONV_NEG), bind(py, 14, CONV_NEG))
    return u


# panel clip sources, in artboard coordinates: the art panel (left) and the copy
# column (right) in landscape; both cover the whole artboard in portrait
_acr = E("Rectangle", width=float(W), height=float(H), originX=0.0, originY=0.0, name="Path")
_acr.add(bind("_artClipW", 20), bind("_vh", 21))
ART_CLIP = E("Shape", _acr, x=0.0, y=0.0, name="Art panel (clip source)")
_ccr = E("Rectangle", width=float(W), height=float(H), originX=0.0, originY=0.0, name="Path")
_ccr.add(bind("_copyClipW", 20), bind("_vh", 21))
COPY_CLIP = E("Shape", _ccr, x=0.0, y=0.0, name="Copy column (clip source)")
COPY_CLIP.add(bind("_copyClipX", 13))


class Scene:
    def __init__(self, n, ring, bg, bg_bind=None):
        self.n, self.P = n, ring
        px, py, ds = add_num(f"_s{n}PX", ring[0]), add_num(f"_s{n}PY", ring[1]), add_num(f"_s{n}DS", 1.0)
        # the interchange disc that clips the scene; it sits on the scene's focal
        # point P (real coordinates) and is scaled so its full size always covers
        # the farthest corner of the real artboard
        self.disc_path = E("Ellipse", width=FULL, height=FULL, name="Disc")
        self.disc = E("Shape", self.disc_path, x=0.0, y=0.0, name=f"S{n} interchange disc (clip source)")
        self.disc_pivot = pivot(f"S{n} disc at P", self.disc, px, py, ring[0], ring[1], scale=ds)
        # placed groups live here; the keyed Content node scales them about the
        # story centre (outgoing scenes recede toward it)
        self.items = unpivot("Placed groups", px="_scx", py="_scy", dx=CENTER[0], dy=CENTER[1])
        self.content = node("Content", self.items)
        content_pivot = pivot("Content pivot (story centre)", self.content, "_scx", "_scy", CENTER[0], CENTER[1])
        bgr = full_rect(bg, "Background")
        if bg_bind:
            bgr.children[1].children[0].add(bind(bg_bind, 37))
        self.bg = bgr
        # depth shade: darkens the scene as it recedes behind the next one
        self.shade = full_rect(BLACK, "Depth shade", opacity=0.0)
        # camera: the incoming scene is pushed through its interchange ring (scaled about P)
        self.camera = node("Camera", unpivot("Camera unpivot", self.shade, content_pivot, bgr, px=px, py=py,
                                             dx=ring[0], dy=ring[1]))
        cam_pivot = pivot("Camera pivot (P)", self.camera, px, py, ring[0], ring[1])
        self.root = node(f"Scene {n}", E("ClippingShape", sourceId=self.disc.id, name="Interchange clip"),
                         cam_pivot, opacity=1.0 if n == 1 else 0.0)
        self.anims = {}
        self.extra_rest = []        # (obj, prop, value) forced into Hidden/Settled
        self.hidden_only = []       # (obj, prop, value) only in Hidden
        self.sems = []              # SemanticData hidden while the scene is offscreen
        self.trail = None
        self.focus = None           # placed-group key whose transform maps P (and the motif)
        scene_trail(self)

    def anim(self, name, dur, loop="oneShot"):
        a = Anim(f"S{self.n} {name}", dur, loop)
        self.anims[name] = a
        return a

    def add(self, *els):
        self.items.add(*els)

    def group(self, role, *children, box, clip=None, focus=False):
        key = f"s{self.n}{role}"
        g = placed(key, *children, box=box, clip=clip, name=f"{role} [placed s{self.n}]")
        if focus:
            self.focus = key
        return g


SCENES = {}

# ---------------- motif (persistent object carried between scenes)
MOTIF_DOT_CORE = circle(0.0, 0.0, 24.0, RED, name="Dot", line=BLACK, lw=4.0)
MOTIF_DOT = node("Route dot", MOTIF_DOT_CORE, x=Q[0], y=Q[1])
MOTIF_RINGS = []          # (shape, ellipse, offset)
for _c, _t, _off in BANDS:
    _el = E("Ellipse", width=0.0, height=0.0, name="Band")
    _sh = E("Shape", _el, stroke(_c, _t, "Band stroke", "butt"), x=195.0, y=400.0, name="Roundel band")
    MOTIF_RINGS.append((_sh, _el, _off))
MOTIF_ROUNDEL = node("Interchange roundel", *[r[0] for r in reversed(MOTIF_RINGS)], x=0.0, y=0.0)
# the roundel's bands ride the scene's clip disc, so they get the same extra
# coverage scale about P (_rkS = disc scale / motif scale, written by the solver)
for _k, _v in (("_rkX", 0), ("_rkY", 0), ("_rkS", 1)):
    add_num(_k, _v)
ROUNDEL_K = node("Interchange roundel (coverage)", MOTIF_ROUNDEL)
ROUNDEL_K.add(bind("_rkX", 13), bind("_rkY", 14), bind("_rkS", 16), bind("_rkS", 17))
MOTIF_TRAILS = node("Dot trails")
MOTIF = node("Motif (persistent route dot + interchange roundel)", MOTIF_DOT, ROUNDEL_K, MOTIF_TRAILS,
             opacity=0.0)
# the motif is authored in design units and follows the placed group that holds
# the focal point of the scene it is currently carrying the story into (or out of)
MOTIF_STAGE = placed("m", MOTIF, name="Motif stage [placed]")
TRAILS = []               # (scene, shape, trim)


def dot_path(p_from, p_to):
    """Angular schematic route from one point to another: vertical, then 45 degrees."""
    (x0, y0), (x1, y1) = p_from, p_to
    d = abs(x1 - x0)
    ymid = y1 + d if y0 > y1 else y1 - d
    if (y0 > y1 and ymid > y0) or (y0 < y1 and ymid < y0):
        return [p_from, p_to]
    return [p_from, (x0, ymid), p_to]


def scene_trail(sc):
    if sc.trail is None:
        shp, tr = route(dot_path(Q, sc.P), RED, 10, name=f"Trail to scene {sc.n}", radius=18)
        shp.attrs["opacity"] = 0.0
        tr.attrs["end"] = 0.0
        MOTIF_TRAILS.add(shp)
        sc.trail = (shp, tr)
        TRAILS.append((sc, shp, tr))
    return sc.trail


def key_along(anim, obj, pts, f0, f1, ease=None):
    """Key obj.x/.y through a polyline, timing proportional to distance."""
    fr = vertex_fractions(pts)
    for i, (p, u) in enumerate(zip(pts, fr)):
        f = round(f0 + (f1 - f0) * u)
        e = "lin"
        if i == 0 and ease:
            e = ease
        anim.key(obj, "x", (f, float(p[0]), e))
        anim.key(obj, "y", (f, float(p[1]), e))


def scale_about(a, obj, p, frames):
    """Key obj scale. obj sits inside a pivot wrapper bound to the real point p
    (Scene.camera about P, Scene.content about the story centre), so only the
    scale is keyed and the pivot follows the layout."""
    for prop in ("scaleX", "scaleY"):
        a.key(obj, prop, *frames)


# forward roundel timing (frames @60fps)
DOT_GO, DOT_IN = 4, 17            # dot leaves after a dip, arrives at the ring
POP0, SQZ0, EXP0, EXP1 = 9, 17, 23, 53


def motif_enter(sc, a):
    """Signature transition. A route dot dips, then runs a schematic route (its
    trail drawing behind it) into the next scene's interchange; a red/yellow/blue
    roundel pops around it (the next scene already showing through its centre),
    squeezes in anticipation and breathes out to become the whole screen, its
    colour bands riding the clip edge. The incoming camera is pushed through the
    ring and settles (follow-through)."""
    Px, Py = sc.P
    pts = dot_path(Q, sc.P)
    a.key(MOTIF, "opacity", (0, 1.0, "hold"))
    shp, tr = scene_trail(sc)
    a.key(shp, "opacity", (0, 1.0, "hold"), (EXP0 + 2, 1.0, "lin"), (EXP0 + 6, 0.0, "hold"))
    a.key(tr, "end", (0, 0.0, "hold"), (DOT_GO, 0.0, (0.5, 0.0, 0.6, 1.0)), (DOT_IN, 1.0, "hold"))
    a.key(tr, "start", (0, 0.0, "hold"), (DOT_GO + 6, 0.0, (0.5, 0.0, 0.5, 1.0)), (DOT_IN + 6, 1.0, "hold"))
    # dot: anticipation dip, run, dive into the ring
    a.key(MOTIF_DOT, "opacity", (0, 1.0, "hold"), (DOT_IN + 4, 1.0, "lin"), (DOT_IN + 7, 0.0, "hold"))
    a.key(MOTIF_DOT, "x", (0, Q[0], "hold"))
    a.key(MOTIF_DOT, "y", (0, Q[1], (0.3, 0.0, 0.7, 1.0)), (DOT_GO, Q[1] + 10, "lin"))
    key_along(a, MOTIF_DOT, pts, DOT_GO, DOT_IN, ease=(0.5, 0.0, 0.6, 1.0))
    for prop in ("scaleX", "scaleY"):
        a.key(MOTIF_DOT, prop, (0, 1.0, "hold"), (DOT_GO - 2, 1.0, "lin"), (DOT_GO, 0.86, (0.3, 0.0, 0.3, 1.0)),
              (DOT_GO + 5, 1.15, "lin"), (DOT_IN, 1.0, EIO), (DOT_IN + 6, 0.35, "hold"))
    # roundel: bands pop in (inner first), squeeze, then breathe out to full screen
    for i, (shp_r, el, off) in enumerate(MOTIF_RINGS):
        a.key(shp_r, "x", (0, float(Px), "hold"))
        a.key(shp_r, "y", (0, float(Py), "hold"))
        p0 = POP0 + i * 2
        lag = i * 1.0
        d_rest = RING_D + 2 * off
        for prop in ("width", "height"):
            a.key(el, prop, (0, 0.0, "hold"), (p0, 0.0, POP), (p0 + 8, d_rest, "lin"),
                  (SQZ0 + 1, d_rest, EIO), (EXP0 + lag, d_rest * 0.8, EXPAND), (EXP1 + lag, FULL + 2 * off, "hold"))
        a.key(shp_r, "opacity", (0, 1.0, "hold"), (EXP1 + lag, 1.0, "lin"), (EXP1 + lag + 1, 0.0, "hold"))
    # the clip: the next scene shows through the roundel's centre, then becomes the screen
    for prop in ("width", "height"):
        a.key(sc.disc_path, prop, (0, 0.0, "hold"), (POP0, 0.0, POP), (POP0 + 8, RING_D, "lin"),
              (SQZ0 + 1, RING_D, EIO), (EXP0, RING_D * 0.8, EXPAND), (EXP1, FULL, "hold"))
    # follow-through: the incoming camera is pushed through the ring
    scale_about(a, sc.camera, sc.P, [(0, 1.14, "hold"), (EXP0, 1.14, (0.2, 0.0, 0.1, 1.0)), (EXP1 + 22, 1.0, "hold")])


def motif_exit_back(sc, a, dur=44):
    """Reverse transition: the scene breathes back into its interchange roundel
    (bands contracting outside the shrinking clip), the roundel closes and the
    dot drops back down its route, revealing the previous scene underneath."""
    Px, Py = sc.P
    pts = list(reversed(dot_path(Q, sc.P)))
    a.key(MOTIF, "opacity", (0, 1.0, "hold"), (dur, 0.0, "hold"))
    C0, C1, CL = 0, 24, 32        # contract, closed, roundel gone
    for i, (shp_r, el, off) in enumerate(MOTIF_RINGS):
        a.key(shp_r, "x", (0, float(Px), "hold"))
        a.key(shp_r, "y", (0, float(Py), "hold"))
        lag = (len(MOTIF_RINGS) - 1 - i) * 1.0
        d_rest = RING_D + 2 * off
        for prop in ("width", "height"):
            a.key(el, prop, (0, FULL + 2 * off, "hold"), (C0 + lag, FULL + 2 * off, (0.75, 0.0, 0.4, 1.0)),
                  (C1 + lag, d_rest, POP), (CL - 4 + i, d_rest * 1.08, EI), (CL + i, 0.0, "hold"))
        a.key(shp_r, "opacity", (0, 1.0, "hold"), (CL + i, 1.0, "lin"), (CL + i + 1, 0.0, "hold"))
    for prop in ("width", "height"):
        a.key(sc.disc_path, prop, (0, FULL, (0.75, 0.0, 0.4, 1.0)), (C1, RING_D, "lin"), (CL - 4, RING_D, EI),
              (CL - 1, 0.0, "hold"))
    a.key(MOTIF_DOT, "opacity", (0, 0.0, "hold"), (C1, 0.0, "lin"), (C1 + 3, 1.0, "hold"), (dur - 2, 1.0, "lin"),
          (dur, 0.0, "hold"))
    for prop in ("scaleX", "scaleY"):
        a.key(MOTIF_DOT, prop, (0, 0.35, "hold"), (C1, 0.35, POP), (C1 + 8, 1.0, "hold"))
    a.key(MOTIF_DOT, "x", (0, float(Px), "hold"))
    a.key(MOTIF_DOT, "y", (0, float(Py), "hold"))
    key_along(a, MOTIF_DOT, pts, C1 + 4, dur, ease=EI)
    # the leaving scene's camera pulls back as it closes
    scale_about(a, sc.camera, sc.P, [(0, 1.0, (0.6, 0.0, 0.8, 0.4)), (C1, 1.12, "hold")])


def content_exit_fwd(sc, a, dur=50):
    """The outgoing scene recedes (scale toward the window centre) and darkens."""
    scale_about(a, sc.content, CENTER, [(0, 1.0, (0.5, 0.0, 0.3, 1.0)), (dur, 0.9, "hold")])
    a.key(sc.shade, "opacity", (0, 0.0, (0.4, 0.0, 0.4, 1.0)), (dur, 0.42, "hold"))


def content_enter_back(sc, a, dur=50):
    """Going back, the previous scene comes forward again from where it receded."""
    scale_about(a, sc.content, CENTER, [(0, 0.9, "hold"), (8, 0.9, (0.2, 0.0, 0.2, 1.0)), (dur, 1.0, "hold")])
    a.key(sc.shade, "opacity", (0, 0.42, "hold"), (6, 0.42, (0.3, 0.0, 0.3, 1.0)), (dur - 10, 0.0, "hold"))


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


YEAR_TEXT = text(0, 0, None, [("2026", "year", CONV_YEAR)], 15, BLACK, weight=700, ox=1.0, name="Year")

# Header ticket band. The node is scaled by the chrome scale _cs; inside it the
# wordmark is pinned to the left safe margin and the year to the right one, and
# the band spans the real width. The perforation, its notches and the progress
# segments are drawn by the sequencer script at the real size.
for _k, _v in (("_hdrWmX", 26), ("_hdrWmY", 32), ("_hdrYrX", 366), ("_hdrYrY", 22), ("_hdrBandW", W),
               ("_hdrBandH", 82)):
    add_num(_k, _v)
_hdr_wm = node("Wordmark slot", wordmark(0, 0), x=26.0, y=32.0)
_hdr_wm.add(bind("_hdrWmX", 13), bind("_hdrWmY", 14))
_hdr_yr = node("Year slot", YEAR_TEXT, x=366.0, y=22.0)
_hdr_yr.add(bind("_hdrYrX", 13), bind("_hdrYrY", 14))
_hdr_band = rect(0, 0, W, 82, WHITE, name="Band")
_hdr_band.children[0].add(bind("_hdrBandW", 20), bind("_hdrBandH", 21))
HEADER = node("Header ticket band", _hdr_wm, _hdr_yr, _hdr_band)
HEADER.add(bind("_cs", 16), bind("_cs", 17))

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


FOCUS_RINGS = []


def button(key, cx, w, h, bg, label_prop, ink, action, outline=None, icon=None, label=True, semantic_prop=None,
           icon_left=False):
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
    # like :focus-visible - only after the keyboard moved focus (Tab), hidden again on pointer input
    ring_vis = node("Focus visible", ring)
    ring_vis.add(bind("_focusVisible", 18))
    kids = [ring_vis]
    if icon:
        kids.append(icon)
    if label:
        if icon_left:
            lx, lw_ = -w / 2 + 44, w - 44 - 16
        else:
            pad = 22 if icon else 18
            lx, lw_ = -w / 2 + pad, w - (64 if icon else 2 * pad)
        lt = text(lx, 0, lw_, [(SAMPLE[label_prop], label_prop)], 17, ink,
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


def replay_icon(color, cx=0.0, cy=0.0, r=8.0, t=2.6):
    """Counter-clockwise replay arrow, built from geometry: an open arc whose
    arrowhead sits exactly on the arc's end and points along its tangent."""
    a0, a1 = math.radians(215), math.radians(-62)          # screen angles (y down); decreasing = ccw
    n_ = 22
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * k / n_), cy + r * math.sin(a0 + (a1 - a0) * k / n_))
           for k in range(n_ + 1)]
    ex, ey = pts[-1]
    tx, ty = math.sin(a1), -math.cos(a1)                   # tangent for decreasing angle
    nx, ny = -ty, tx
    hl, hw = 6.4, 4.6
    tip = (ex + tx * hl * 0.62, ey + ty * hl * 0.62)
    b1 = (ex - tx * hl * 0.38 + nx * hw, ey - ty * hl * 0.38 + ny * hw)
    b2 = (ex - tx * hl * 0.38 - nx * hw, ey - ty * hl * 0.38 - ny * hw)
    arc = route(pts[:-1], color, t, name="Arc", radius=0, trim=False, cap="round")[0]
    head = path_shape([tip, b1, b2], color, name="Arrowhead")
    return node("Replay icon", head, arc)


def share_icon(color):
    """Share glyph: an open tray with an arrow leaving it."""
    tray = route([(-7, -1), (-7, 8), (7, 8), (7, -1)], color, 2.6, name="Tray", radius=0, trim=False)[0]
    shaft = route([(0, 3), (0, -10)], color, 2.6, name="Shaft", radius=0, trim=False)[0]
    head = route([(-5, -5), (0, -10), (5, -5)], color, 2.6, name="Head", radius=0, trim=False)[0]
    return node("Share icon", head, shaft, tray)


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
BTN_SHARE = button("share", 9158, 136, 56, RED, "shareLabel", WHITE, [E("ListenerFireEvent", eventId=SHARE_EVENT.id)],
                   icon=node("Share glyph", share_icon(WHITE), x=-40.0, y=1.0), icon_left=True)
BTN_REPLAY = button("replay", 9303, 126, 56, WHITE, "replayLabel", BLACK, [vm_trigger_write("_replayTapped")],
                    outline=BLACK, icon=node("Replay glyph", replay_icon(BLACK), x=-36.0, y=0.0), icon_left=True)
# Dock focus: summary-only buttons start unfocusable (keyed by the Dock layer)
BUTTONS["share"][2].attrs["canFocus"] = False
BUTTONS["replay"][2].attrs["canFocus"] = False

# Dock ticket band, scaled by _cs and pinned to the real bottom edge. Prev/Pause
# keep to the left safe margin, Continue (and Share/Replay on the summary) to the
# right one; the timelines still key each button's x inside its cluster.
for _k, _v in (("_dockY", 0), ("_dockL", 0), ("_dockR", 0), ("_dockBtnY", 0), ("_dockBandW", W),
               ("_dockBandH", 104)):
    add_num(_k, _v)
DOCK_LEFT = node("Left controls", BTN_PREV, BTN_PAUSE)
DOCK_LEFT.add(bind("_dockL", 13))
DOCK_RIGHT = node("Right controls", BTN_CONT, BTN_SHARE, BTN_REPLAY)
DOCK_RIGHT.add(bind("_dockR", 13))
DOCK_BTNS = node("Controls", DOCK_LEFT, DOCK_RIGHT)
DOCK_BTNS.add(bind("_dockBtnY", 14))
_dock_band = rect(0, 740, W, 104, WHITE, name="Band")
_dock_band.children[0].add(bind("_dockBandW", 20), bind("_dockBandH", 21))
DOCK = node("Dock ticket band", DOCK_BTNS, _dock_band)
DOCK.add(bind("_dockY", 14), bind("_cs", 16), bind("_cs", 17))

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


MOTIF_OBJS = {MOTIF, MOTIF_DOT, MOTIF_DOT_CORE, MOTIF_ROUNDEL} | {r[0] for r in MOTIF_RINGS} | \
    {r[1] for r in MOTIF_RINGS} | {t[2] for t in TRAILS}


def collect_rest(sc):
    rest = {}
    for name, a in sc.anims.items():
        if name == "Idle":
            continue
        for (obj, prop) in a.order:
            if obj in MOTIF_OBJS:
                continue
            if obj is sc.root:
                continue
            rest[(obj, prop)] = rest_value(obj, prop)
    for obj, prop, v in sc.extra_rest:
        rest[(obj, prop)] = v
    return rest


JOYSTICKS = []


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
    for inp in getattr(sc, "live_inputs", []):
        hidden.hold(inp, "propertyValue", 0.0)
        settled.hold(inp, "propertyValue", 1.0)
        for name, a in sc.anims.items():
            if name != "Idle":
                a.hold(inp, "propertyValue", 1.0)
    trail = sc.trail[0]
    for name, a in sc.anims.items():
        if name != "Idle":
            a.hold(sc.root, "opacity", 1.0)
        if name.startswith("Exit") or name == "EnterBack":
            a.hold(trail, "opacity", 0.0)
    for name in ("EnterBack", "ExitFwd"):
        a = sc.anims[name]
        for prop in ("width", "height"):
            if not a.has(sc.disc_path, prop):
                a.hold(sc.disc_path, prop, FULL)

    # Idle loop: not a state. A Joystick scrubs it from _idleN, which only the
    # sequencer advances (current scene, settled, playing, full motion), so pause
    # freezes it mid-motion and reduced motion keeps it at frame 0 (the rest pose).
    idle = sc.anims["Idle"]
    assert idle.dur == IDLE_FRAMES, (n, idle.dur)
    for (obj, prop) in idle.order:
        for name, a in sc.anims.items():
            if name != "Idle" and a.has(obj, prop):
                raise SystemExit(f"S{n}: idle key {obj.attrs.get('name')}.{prop} also keyed by {name}")
        if (obj, prop) in rest:
            raise SystemExit(f"S{n}: idle key {obj.attrs.get('name')}.{prop} has a rest hold")
    if idle not in ANIMS:
        ANIMS.append(idle)
    JOYSTICKS.append(E("Joystick", bind(f"_idle{n}", 299), x=-1.0, y=0.0, xId=idle.build().id,
                       name=f"Scene {n} idle playhead"))

    S_H = state(hidden, 160, 0)
    enters = []
    if n == 9:
        for p in range(4):
            enters.append((state(sc.anims[f"EnterFwd{p}"], 420, -300 + 110 * p), p))
    else:
        enters.append((state(sc.anims["EnterFwd"], 420, -200), None))
    S_EB = state(sc.anims["EnterBack"], 420, 220)
    S_S = state(settled, 700, 0)
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

    live = [st for st, _ in enters] + [S_EB, S_S]
    for st in live:
        st.add(go(S_XF, c_num("currentScreen", "greaterThan", n), c_bool("reducedMotion", False), dur=90))
        st.add(go(S_XB, c_num("currentScreen", "lessThan", n), c_bool("reducedMotion", False), dur=90))
        st.add(go(S_H, c_num("currentScreen", "notEqual", n), c_bool("reducedMotion", True), dur=220))
    for st in [s for s, _ in enters] + [S_EB]:
        st.add(go(S_S, c_bool("reducedMotion", True), dur=220))
        st.add(go(S_S, exit_pct=100))
    for st in (S_XF, S_XB):
        st.add(go(S_H, exit_pct=100))
        for est, p in enters:
            st.add(go(est, *ef_conds(p), dur=120))
        st.add(go(S_EB, c_num("currentScreen", "equal", n), c_num("_navDir", "lessThan", 0),
                  c_bool("reducedMotion", False), dur=120))
        st.add(go(S_S, c_num("currentScreen", "equal", n), c_bool("reducedMotion", True), dur=220))
    states = [S_H] + [s for s, _ in enters] + [S_EB, S_S, S_XF, S_XB]
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
pause_b = BUTTONS["pause"]
# hidden buttons park far outside any canvas (the clusters follow the real width)
for a, (cx, sx, rx, px), foc in ((DOCK_N, (259, 9158, 9303, 114), (True, False, False)),
                                 (DOCK_S, (-9000, 158, 303, -9000), (False, True, True))):
    a.hold(cont[0], "x", float(cx))
    a.hold(pause_b[0], "x", float(px))
    a.key(pause_b[2], "canFocus", (0, foc[0], "hold"))
    a.key(SEMS["pause"], "isHidden", (0, not foc[0], "hold"))
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


KEYROOT = node("Recap", KEYROOT_FOCUS, HEADER, DOCK, MOTIF_STAGE,
               *[SCENES[n].root for n in range(10, 0, -1)],
               full_rect(WHITE, "Paper (under every scene)"),
               node("Clip sources", *[SCENES[n].disc_pivot for n in range(1, 11)], ART_CLIP, COPY_CLIP))
for l in [key_listener("Key next", ["right"], vm_trigger_write("_nextTapped")),
          key_listener("Key previous", ["left"], vm_trigger_write("_prevTapped")),
          key_listener("Key pause", ["space"], vm_trigger_write("_pauseTapped")),
          key_listener("Key tab", ["tab"], E("FocusActionTraversal", traversalKind="next"),
                       vm_num_write("_focusVisible", 1)),
          key_listener("Key shift-tab", ["tab"], E("FocusActionTraversal", traversalKind="previous"),
                       vm_num_write("_focusVisible", 1), mods=1)]:
    l.attrs["targetId"] = KEYROOT.id
    LISTENERS.append(l)

SM = E("StateMachine", *LISTENERS, *LAYERS, name="Recap Sequencer")

# stack: the print stock and the sequencer layer share one cell, both filling the artboard
ART_STYLE = E("LayoutComponentStyle", layoutTypeValue="stack", name="Artboard Style")
ROOT_STYLE = E("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fill",
               widthUnitsValue="auto", heightUnitsValue="auto", name="Style")
SEQ = E("ScriptedLayout", E("FocusData", canFocus=False, name="No focus"), scriptAssetId=SCRIPT_SEQ.id,
        name="Sequencer (gestures, timer, progress)")
# the print stock fills the artboard (stack cell), so it covers the real artboard
# and its ScriptedLayout receives the real size and device scale
PAPER_STYLE = E("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fill",
                widthUnitsValue="auto", heightUnitsValue="auto", name="Style")
PAPER = E("LayoutComponent", PAPER_STYLE,
          E("ScriptedLayout", E("ScriptInputNumber", propertyValue=0.62, name="strength"),
            scriptAssetId=SCRIPT_PAPER.id, name="Print stock (paper shader)"),
          width=float(W), height=float(H), styleId=PAPER_STYLE.id, name="Print layer")

# Test harness only (SWITCHYARD_DEBUG_EVENTS=1): the artboard size is bound to
# _testW/_testH so a headless run can resize the artboard mid-scene (the
# sequencer swaps in _testW2/_testH2 at _testAt seconds), exactly as a host's
# layout fit does when its canvas is resized. Never in the shipped file.
ART_BINDS = []
if DEBUG_EVENTS:
    for _k, _v in (("_testW", W), ("_testH", H), ("_testW2", 0), ("_testH2", 0), ("_testAt", -1)):
        add_num(_k, _v)
    ART_BINDS = [bind("_testW", 7), bind("_testH", 8)]

# ---------------------------------------------------------------- instances (after every add_num)
INST_FIXTURE = instance("Fixture", SAMPLE)
INST_ZERO = instance("NewUser", ZERO)
INST_EXTREME = instance("Extreme", EXTREME)
VM.add(INST_FIXTURE, INST_ZERO, INST_EXTREME)
VM.attrs["defaultInstanceId"] = INST_FIXTURE.id

ARTBOARD = E("Artboard",
             ART_STYLE,
             *ART_BINDS,
             PAPER,
             E("LayoutComponent", ROOT_STYLE, SEQ, width=float(W), height=float(H), styleId=ROOT_STYLE.id,
               name="Sequencer layer"),
             KEYROOT,
             SHARE_EVENT, EV_SCREEN, EV_FINISHED,
             *JOYSTICKS,
             SM,
             *[a.build() for a in ANIMS],
             defaultStateMachineId=SM.id, viewModelId=VM.id, viewModelInstanceId=INST_FIXTURE.id,
             styleId=ART_STYLE.id, width=float(W), height=float(H), clip=True, name="Switchyard Recap", id="0:900")


# ---------------------------------------------------------------- layout data module
def write_layout_data():
    """scripts/layoutdata.luau: the design boxes of every placed group and each
    scene's focal point, so the solver (scripts/layout.luau) and the art cannot
    drift apart."""
    lines = ["--!strict", "-- GENERATED by tools/gen.py - do not edit. Design units (390 x 844 master).", "",
             "export type Box = { x0: number, y0: number, x1: number, y1: number }", "",
             "local boxes: { [string]: Box } = {"]
    for k in sorted(LAYOUT_BOXES):
        x0, y0, x1, y1 = LAYOUT_BOXES[k]
        lines.append(f"    {k} = {{ x0 = {fmt(x0)}, y0 = {fmt(y0)}, x1 = {fmt(x1)}, y1 = {fmt(y1)} }},")
    lines += ["}", "", "-- focal point P of each scene (interchange disc, camera push) and the group that holds it",
              "local P: { { number } } = {"]
    for n in range(1, 11):
        lines.append(f"    {{ {fmt(float(SCENES[n].P[0]))}, {fmt(float(SCENES[n].P[1]))} }},")
    lines += ["}", "local focus: { string } = {"]
    for n in range(1, 11):
        lines.append(f"    '{SCENES[n].focus}',")
    lines += ["}", "",
              f"return {{ boxes = boxes, P = P, focus = focus, Q = {{ {fmt(Q[0])}, {fmt(Q[1])} }}, "
              f"full = {fmt(FULL)}, center = {{ {fmt(CENTER[0])}, {fmt(CENTER[1])} }} }}", ""]
    with open(os.path.join(ROOT, "scripts", "layoutdata.luau"), "w") as f:
        f.write("\n".join(lines))


write_layout_data()

doc = E("Rive", ARTBOARD, FONT_DISPLAY, FONT_COND, FONT_TEXT, SCRIPT_FMT, SCRIPT_LDATA, SCRIPT_LAYOUT, SCRIPT_SEQ, SCRIPT_P3, SCRIPT_FLAP, SCRIPT_PAPER, *ROOTS, VM, version=1, kind="fragment")
out = os.path.join(ROOT, "scene.rml")
with open(out, "w") as f:
    f.write("<!-- GENERATED by tools/gen.py - edit the generator, or edit here and stop regenerating. -->\n")
    f.write(doc.xml())
    f.write("\n")
print("wrote", out, "animations:", len(ANIMS), "layers:", len(LAYERS))
