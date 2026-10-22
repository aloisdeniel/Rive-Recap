#!/usr/bin/env python3
"""Generates the Marginalia recap RML from one readable source.

    python3 tools/build_rml.py                 # writes rml/*.rml (fixture data)
    python3 tools/build_rml.py --fixture zero  # bakes fixtures/zero.json as the
                                                # default instance (captures only)

The generated .rml files are ordinary editable RML; this script exists because
ten scenes x (hidden / enter / enter-back / idle / exit / exit-back / static)
timelines and the 10x10 transition graphs are mechanical to write by hand.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import rmlkit as K  # noqa: E402
from rmlkit import (N, Anim, Layer, arch, bind, cbool, cnum, ctrig, ellipse, fill,  # noqa: E402
                    lin, node, poly, rad, rect, shape, smooth, solid, star, stroke,
                    text, trans, tstyle, write)
import art  # noqa: E402

# ---------------------------------------------------------------- palette
PARCH, PAPER, PSHADE, PDEEP = "F1E8D5", "F8F2E4", "E4D6B8", "CDBA94"
INK, INK2, INK3 = "252E3D", "3B4558", "5C667A"
OX, OXD, OXL = "782D3D", "571E2B", "9C4A59"
GOLD, GOLDL, GOLDD = "BD914C", "DDBD84", "8E6A33"

SW, SH = 390, 664          # Scenes artboard (the stage between header and controls)
RW, RH = 390, 844          # Recap root artboard
HEADER_H, CONTROLS_H = 76, 104

# ---------------------------------------------------------------- fixture
fixture_name = "sample"
if "--fixture" in sys.argv:
    fixture_name = sys.argv[sys.argv.index("--fixture") + 1]
with open(os.path.join(ROOT, "..", "sample-data.json")) as f:
    DATA = json.load(f)
if fixture_name != "sample":
    with open(os.path.join(ROOT, "fixtures", f"{fixture_name}.json")) as f:
        DATA.update(json.load(f))

# ---------------------------------------------------------------- fonts
FONTS = [
    K.N("FontAsset", file="assets/fonts/CormorantGaramond-VF.ttf", name="Cormorant Garamond").ensure(),
    K.N("FontAsset", file="assets/fonts/CormorantGaramond-Italic-VF.ttf", name="Cormorant Garamond Italic").ensure(),
    K.N("FontAsset", file="assets/fonts/LibreFranklin-VF.ttf", name="Libre Franklin").ensure(),
]
K.FONT_IDS.update(serif=FONTS[0].id, italic=FONTS[1].id, sans=FONTS[2].id)


def serif(size, color=INK, w=500, **kw):
    sn = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}.get(w, "Custom")
    return tstyle("serif", size, color, w, family="Cormorant Garamond", style_name=sn, **kw)


def italic(size, color=INK, w=500, **kw):
    sn = {400: "Italic", 500: "Medium Italic", 600: "SemiBold Italic", 700: "Bold Italic"}.get(w, "Custom")
    return tstyle("italic", size, color, w, family="Cormorant Garamond", style_name=sn, **kw)


def sans(size, color=INK, w=400, **kw):
    sn = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold"}.get(w, "Custom")
    return tstyle("sans", size, color, w, family="Libre Franklin", style_name=sn, **kw)


# ---------------------------------------------------------------- view model
V = K.VM("UserRecap")
K.V = V
art.K = K


def _d(k, fallback=None):
    return DATA.get(k, fallback)


def color_argb(s: str) -> str:
    return K.argb(s.lstrip("#"))


PUBLIC = [
    ("userName", "string"), ("year", "number"), ("periodLabel", "string"), ("locale", "string"),
    ("booksFinished", "number"), ("pagesRead", "number"), ("readingHours", "number"),
    ("genresExplored", "number"), ("passagesSaved", "number"), ("longestStreakDays", "number"),
    ("bookClubChats", "number"), ("personaIndex", "number"), ("personaName", "string"),
    ("personaDescription", "string"), ("personaColor", "color"), ("autoAdvanceSeconds", "number"),
    ("autoAdvanceEnabled", "bool"), ("isPaused", "bool"), ("reducedMotion", "bool"),
    ("soundEnabled", "bool"), ("currentScreen", "number"), ("screenProgress", "number"),
    ("shareIncludeName", "bool"), ("shareIncludeSensitiveValues", "bool"),
    ("continueLabel", "string"), ("previousLabel", "string"), ("pauseLabel", "string"),
    ("playLabel", "string"), ("shareLabel", "string"), ("replayLabel", "string"),
    ("introHeadline", "string"), ("introSupport", "string"), ("summaryHeadline", "string"),
    ("summarySupport", "string"), ("emptyHeadline", "string"), ("emptySupport", "string"),
    ("personaLabel", "string"),
] + [(f"showScreen{i}", "bool") for i in range(1, 11)] + [
    (f"screen{i}{k}", "string") for i in range(2, 9) for k in ("Headline", "Support", "Unit")
]
for name, kind in PUBLIC:
    v = _d(name)
    if kind == "color":
        v = color_argb(v)
    V.prop(name, kind, v)

# additions to the contract (documented in README)
V.prop("isSharing", "bool", False, "host clears after the share sheet closes")
V.prop("isBackgrounded", "bool", False, "host sets while the app is backgrounded")
for s in ("booksFinished", "pagesRead", "readingHours", "genresExplored", "passagesSaved",
          "longestStreakDays", "bookClubChats"):
    V.prop(f"{s}Text", "string", f"{int(_d(s, 0)):,}", "derived: formatted by the director")
V.prop("yearText", "string", str(_d("year", 2026)), "derived")
V.prop("a11yAnnouncement", "string", "", "derived: one sentence per scene for screen readers")
V.prop("primaryA11yLabel", "string", _d("continueLabel"), "derived: Continue / Share")
V.prop("secondaryA11yLabel", "string", _d("pauseLabel"), "derived: Pause / Play / Replay")
V.prop("layoutBreakpoint", "number", _d("layoutBreakpoint", 768),
       "host-tunable: the landscape layout applies when the artboard is at least this wide")
V.prop("visibleScreenCount", "number", 10, "derived")
V.prop("visibleScreenIndex", "number", 1, "derived")
# internal runtime state (underscore = private, not user data)
for name, kind, dv in [
    ("_navDir", "number", 1), ("_parallaxX", "number", 0), ("_parallaxY", "number", 0),
    ("_personaRow", "number", 0), ("_motionPaused", "bool", False), ("_hasStats", "bool", True),
    ("_cmdPrev", "trigger", None), ("_cmdNext", "trigger", None), ("_cmdPrimary", "trigger", None),
    ("_cmdSecondary", "trigger", None), ("_cmdPause", "trigger", None), ("_evtScreen", "trigger", None), ("_evtShare", "trigger", None),
    ("_evtFinished", "trigger", None), ("_focus", "number", 0),
    ("_dbgScreenEvents", "number", 0), ("_dbgShareEvents", "number", 0), ("_dbgFinishedEvents", "number", 0),
    # responsive layout, written by the Director from the real artboard size
    # (scripts/responsive.luau) and bound by the chrome
    ("_landscape", "bool", False), ("_vw", "number", RW), ("_vh", "number", RH),
    ("_headerH", "number", HEADER_H), ("_headerPadT", "number", 22), ("_controlsH", "number", CONTROLS_H),
    ("_controlsPadB", "number", 22), ("_marginX", "number", 24), ("_controlsAlign", "number", 4),
    ("_chromeAlpha", "number", 1),
]:
    V.prop(name, kind, dv)

# ---------------------------------------------------------------- converters
CONVERTERS: list[N] = []


def conv(el: N) -> N:
    el.ensure()
    CONVERTERS.append(el)
    return el


PARALLAX = {}
for depth, px in (("far", 5), ("mid", 10), ("near", 18)):
    PARALLAX[depth] = (
        conv(N("DataConverterRangeMapper", minInput=-1, maxInput=1, minOutput=-px, maxOutput=px,
               name=f"Parallax {depth} X")),
        conv(N("DataConverterRangeMapper", minInput=-1, maxInput=1, minOutput=-px * 0.5,
               maxOutput=px * 0.5, name=f"Parallax {depth} Y")),
    )


def plx(name, depth, *children):
    """A parallax wrapper: x/y bound to the pointer, never wraps text."""
    cx, cy = PARALLAX[depth]
    return N("Node", bind("_parallaxX", K.KEY["x"], cx), bind("_parallaxY", K.KEY["y"], cy),
             *children, x=0, y=0, name=f"Parallax {name} ({depth})")


art.plx = plx

# ---------------------------------------------------------------- scenes
EXIT_MS = 650
TURN_HOLD_MS = 1200   # > the Page Stage script's 840 ms turn


class Scene:
    """One scene group + its timelines. Choreography is declared once as
    forward-entrance tweens; hidden/static/back/exit poses derive from it."""

    def __init__(self, n: int, title: str):
        self.n = n
        self.title = title
        self.tweens: list[tuple] = []     # (obj, prop, t0, t1, v0, v1, ease, kind)
        self.idle: list[tuple] = []       # (obj, prop, [(ms, value, ease)...])
        self.idle_ms = 6000
        self.enter_ms = 1800
        self.extra_hidden: list[tuple] = []
        # Art functions add the "Copy" node and the parallax groups to
        # `content`; build_group sorts them into frames. Frames are plain
        # Nodes that are never keyed: the Page Stage script places them for the
        # real canvas (scripts/responsive.luau), the choreography inside them
        # stays in the 390-unit design space.
        self.content = N("Node", x=0, y=0, name="Content")
        self.copy_frame = node("Copy Frame").ensure()
        self.art_frame = node("Art Frame").ensure()
        self.bleed_front = node("Bleed Front").ensure()   # bands edge to edge, above the art
        self.bleed_back = node("Bleed Back").ensure()     # bands edge to edge, behind the art
        self.empty_frame = node("Empty Frame").ensure()   # scene 10's zero-user page
        self.foot_frame = node("Foot Frame").ensure()     # scene 3's rule + support
        self.wide_frame = node("Wide Frame").ensure()     # scene 10's wide (spread) card
        self.sky_frame = node("Sky Frame").ensure()       # scene 10's skyline, on the floor
        self.paper = shape("Paper", rect(SW + 40, SH + 240, x=SW / 2, y=SH / 2), fill(PARCH))
        self.paper_frame = node("Paper Frame", self.paper).ensure()
        self.group = N("Node", x=0, y=0, opacity=0, name=f"Scene {n} - {title}").ensure()

    # choreography
    def tw(self, obj, prop, t0, t1, v0, v1, ease="out", kind="double"):
        self.tweens.append((obj, prop, t0, t1, v0, v1, ease, kind))

    def idle_keys(self, obj, prop, keys):
        self.idle.append((obj, prop, keys))

    def build_group(self) -> N:
        for c in self.content.children:
            (self.copy_frame if c.attrs.get("name") == "Copy" else self.art_frame).add(c)
        # first child draws on top
        self.group.add(self.copy_frame, self.foot_frame, self.empty_frame, self.bleed_front, self.wide_frame,
                       self.art_frame, self.sky_frame, self.bleed_back, self.paper_frame)
        return self.group

    def anims(self) -> dict[str, Anim]:
        g, n = self.group, self.n
        A: dict[str, Anim] = {}

        def settled(a: Anim, ms=0):
            for obj, prop, t0, t1, v0, v1, ease, kind in self.tweens:
                a.set(obj, prop, v1, kind, ms)

        def start_pose(a: Anim):
            for obj, prop, t0, t1, v0, v1, ease, kind in self.tweens:
                a.set(obj, prop, v0, kind)

        def base(a: Anim, op=1.0):
            a.set(g, "opacity", op)

        h = Anim(f"S{n} Hidden", 17)
        base(h, op=0)
        start_pose(h)
        A["hidden"] = h

        e = Anim(f"S{n} Enter", self.enter_ms)
        base(e)
        firsts = {}
        for obj, prop, t0, t1, v0, v1, ease, kind in self.tweens:
            key = (obj.id, prop)
            if key in firsts:
                # chained tween on the same property: continue from previous end
                e.k(obj, prop, t0, v0, ease, kind)
                e.k(obj, prop, t1, v1, "linear", kind)
            else:
                firsts[key] = True
                e.tw(obj, prop, t0, t1, v0, v1, ease, kind)
        A["enter"] = e

        # back navigation: the page arrives settled; the Page Stage script lands
        # it as a live-textured 3D leaf over the page it covers
        eb = Anim(f"S{n} Enter Back", 200)
        base(eb)
        settled(eb)
        A["enterBack"] = eb

        st = Anim(f"S{n} Static", 17)
        base(st)
        settled(st)
        A["static"] = st

        idle = Anim(f"S{n} Idle", self.idle_ms, loop="loop")
        if not self.idle:
            idle.set(g, "opacity", 1)
        for obj, prop, keys in self.idle:
            for ms, val, ease in keys:
                idle.k(obj, prop, ms, val, ease)
        A["idle"] = idle

        # leaving: the page stays fully drawn (its idle pose frozen) for as long
        # as the Page Stage script needs it - as the turning 3D leaf (forward)
        # or as the page the previous one lands on (back) - then hides.
        xf = Anim(f"S{n} Exit", TURN_HOLD_MS)
        base(xf, op=1)
        A["exit"] = xf

        xb = Anim(f"S{n} Exit Back", TURN_HOLD_MS)
        base(xb, op=1)
        A["exitBack"] = xb
        return A


def scene_layer(sc: Scene, A: dict[str, Anim]) -> Layer:
    L = Layer(f"Scene {sc.n}")
    n = sc.n
    hid = L.state(A["hidden"], 100, 0)
    ent = L.state(A["enter"], 360, -160)
    entb = L.state(A["enterBack"], 360, 160)
    idle = L.state(A["idle"], 620, 0)
    stat = L.state(A["static"], 360, 320)
    ex = L.state(A["exit"], 880, -160)
    exb = L.state(A["exitBack"], 880, 160)
    L.start(hid)
    here = lambda: cnum("currentScreen", "equal", n)
    rm = lambda v: cbool("reducedMotion", v)
    # arrive
    trans(hid, ent, here(), cnum("_navDir", "greaterThan", 0), rm(False))
    trans(hid, entb, here(), cnum("_navDir", "lessThan", 0), rm(False))
    trans(hid, stat, here(), rm(True), ms=220, ease="soft")
    trans(ent, idle, exit_pct=100)
    trans(entb, idle, exit_pct=100)
    # leave (from anywhere visible); a short mix hides mid-entrance pops
    for s in (ent, entb, idle):
        trans(s, ex, cnum("currentScreen", "greaterThan", n), rm(False))
        trans(s, exb, cnum("currentScreen", "lessThan", n), rm(False))
        trans(s, hid, cnum("currentScreen", "notEqual", n), rm(True), ms=220, ease="soft")
        if s is not idle:
            trans(s, stat, here(), rm(True), ms=200)
    trans(idle, stat, here(), rm(True), ms=200)
    trans(stat, hid, cnum("currentScreen", "notEqual", n), ms=220, ease="soft")
    trans(stat, idle, here(), rm(False), ms=200)
    # rapid return while still turning away
    for s in (ex, exb):
        trans(s, entb, here(), cnum("_navDir", "lessThan", 0), rm(False))
        trans(s, ent, here(), cnum("_navDir", "greaterThan", 0), rm(False))
        trans(s, hid, exit_pct=100)
    return L


SCENES = [Scene(i, t) for i, t in enumerate(
    ["Invitation", "Books finished", "Pages read", "Reading hours", "Genres explored",
     "Passages saved", "Day reading streak", "Book-club chats", "Persona reveal",
     "Summary"], start=1)]

# metric-scene copy block (bound text); returns the nodes for choreography
def metric_copy(sc: Scene, stat: str, layout: str = "center", top: float = 8,
                num_size: float = 112, head_size: float = 36, head_w: float | None = None):
    n = sc.n
    cx = SW / 2
    left = layout == "left"
    al = "left" if left else "center"
    x0 = 30 if left else 20
    w = SW - 60 if left else SW - 40
    num_st = serif(num_size, OX, 600, ls=-1, lining=True)
    num = text("Hero Number", x0, top, [(num_st, f"{int(_d(stat, 0)):,}", bind(f"{stat}Text", 268))],
               w=w, h=num_size * 1.05, align=al, overflow="fitFontSize", wrap="noWrap",
               valign="middle")
    unit_st = sans(15, INK, 500, ls=1.5, lh=18)
    uy = top + num_size * 1.05 + 2
    # fixed boxes: unit/support ellipsize after two lines; the headline keeps two
    # lines and only shrinks (fitFontSize) when expanded copy would need a third
    unit = text("Unit", x0, uy, [(unit_st, _d(f"screen{n}Unit"), bind(f"screen{n}Unit", 268))],
                w=w, h=36, align=al, wrap="wrap", overflow="ellipsis")
    ry = uy + 44
    rule = art.gold_rule(cx if not left else 30 + 70, ry, 150 if not left else 140, left=left)
    head_st = serif(head_size, INK, 500, lh=head_size * 1.08)
    hw = head_w or w
    hx = x0 if left else (SW - hw) / 2
    hh = head_size * 1.08 * 2 + 4
    head = text("Headline", hx, ry + 12, [(head_st, _d(f"screen{n}Headline"), bind(f"screen{n}Headline", 268))],
                w=hw, h=hh, align=al, wrap="wrap", overflow="fitFontSize")
    sup_st = sans(15, INK2, 400, lh=20)
    sup = text("Support", x0, ry + 12 + hh + 6,
               [(sup_st, _d(f"screen{n}Support"), bind(f"screen{n}Support", 268))],
               w=w, h=40, align=al, wrap="wrap", overflow="ellipsis")
    copy = node("Copy", num, unit, rule, head, sup)
    # motion score: 0-200 anticipation (rule), 200-1200 hero, 1200-1800 copy
    sc.tw(rule, "scaleX", 0, 520, 0.0, 1.0, "inout")
    sc.tw(rule, "opacity", 0, 160, 0.0, 1.0, "linear")
    sc.tw(num, "opacity", 180, 520, 0.0, 1.0, "soft")
    sc.tw(num, "y", 180, 900, num.attrs["y"] + 26, num.attrs["y"], "out")
    sc.tw(unit, "opacity", 700, 1050, 0.0, 1.0, "soft")
    sc.tw(head, "opacity", 1150, 1550, 0.0, 1.0, "soft")
    sc.tw(head, "y", 1150, 1600, head.attrs["y"] + 14, head.attrs["y"], "out")
    sc.tw(sup, "opacity", 1350, 1800, 0.0, 1.0, "soft")
    return copy, dict(num=num, unit=unit, rule=rule, head=head, sup=sup)


def build_scenes():
    builders = [art.scene1, art.scene2, art.scene3, art.scene4, art.scene5, art.scene6,
                art.scene7, art.scene8, art.scene9, art.scene10]
    ctx = dict(V=V, serif=serif, italic=italic, sans=sans, metric_copy=metric_copy, DATA=DATA,
               SW=SW, SH=SH, conv=conv)
    extra_layers = []
    for sc, b in zip(SCENES, builders):
        sc.extra = b(sc, ctx) or []
    return extra_layers


# ---------------------------------------------------------------- build
def main():
    extra_layers = build_scenes()

    # --- one artboard per page. The Page Stage script hosts them as separate
    # instances, so the page that is leaving stays live and can be drawn on
    # its own (as the turning 3D leaf) while the next page plays underneath.
    page_abs = []
    for i, sc in enumerate(SCENES):
        ab = N("Artboard", isComponent=True, viewModelId=V.el.id, viewModelInstanceId=V.inst.id,
               width=SW, height=SH, clip=False, x=RW + 120 + (i % 5) * (SW + 80),
               y=(i // 5) * (SH + 120), name=f"Page {sc.n}").ensure()
        sm = N("StateMachine", name=f"Page {sc.n}").ensure()
        st = N("LayoutComponentStyle", name=f"Page {sc.n} Style").ensure()
        ab.attrs.update(styleId=st.id, defaultStateMachineId=sm.id)
        ab.add(st, sm, sc.build_group())
        A = sc.anims()
        sm.add(scene_layer(sc, A).build())
        anims = list(A.values())
        for L, AA in sc.extra:
            sm.add(L.build())
            anims.extend(AA)
        for an in anims:
            ab.add(an.build())
        page_abs.append(ab)
    persistent, pers_layers = art.persistent(ctx_global())

    # --- Carry artboard: the objects carried *through* the cuts (bookmark
    # ribbon, moon). Same coordinate space as Scenes; drawn above the turning
    # leaf by the Page Stage script so they stay unbroken across every turn.
    carry_ab = N("Artboard", isComponent=True, viewModelId=V.el.id, viewModelInstanceId=V.inst.id,
                 width=SW, height=SH, clip=False, x=RW + 120, y=2 * (SH + 120), name="Carry").ensure()
    carry_sm = N("StateMachine", name="Carry").ensure()
    ca_style = N("LayoutComponentStyle", name="Carry Style").ensure()
    carry_ab.attrs.update(styleId=ca_style.id, defaultStateMachineId=carry_sm.id)
    carry_ab.add(ca_style, carry_sm, persistent)
    for L, AA in pers_layers:
        carry_sm.add(L.build())
        for a in AA:
            carry_ab.add(a.build())

    cover_ab = art.cover_artboard(ctx_global())
    cover_ab.attrs.update(x=RW + 120 + 2 * (SW + 80), y=2 * (SH + 120))

    # --- Share card artboard (host snapshot target)
    card_ab, card_sm_layers, card_anims = art.share_card_artboard(ctx_global())
    card_ab.attrs.update(x=RW + 120 + SW + 80, y=2 * (SH + 120))

    # --- Recap root
    recap, recap_extra = build_root(page_abs, carry_ab, cover_ab)
    recap.attrs["isComponent"] = True   # so the resize harness can host it

    # --- Resize Harness: a test fixture, not part of the experience. It hosts
    # Recap (same UserRecap instance) and resizes it mid-run, the way a host's
    # layout fit does on a window resize or a rotation (see README, checks).
    h_script = N("ScriptAsset", file="scripts/resize_harness.luau", name="resize_harness").ensure()
    h_style = N("LayoutComponentStyle", name="Harness Style").ensure()
    h_sm = N("StateMachine", name="Harness").ensure()
    h_root_st = N("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fill",
                  name="Harness Root Style").ensure()
    harness = N("Artboard", h_style, h_sm,
                N("LayoutComponent", h_root_st,
                  N("ScriptedLayout", N("ScriptInputArtboard", artboardId=recap.id, name="recap"),
                    N("ScriptInputNumber", propertyValue=1.5, name="at"),
                    scriptAssetId=h_script.id, name="Harness"),
                  width=1280, height=720, styleId=h_root_st.id, name="Harness Root"),
                viewModelId=V.el.id, viewModelInstanceId=V.inst.id, width=1280, height=720,
                styleId=h_style.id, defaultStateMachineId=h_sm.id, clip=True,
                x=-1500, y=0, name="Resize Harness").ensure()
    recap_extra.append(h_script)

    roots = [recap, *page_abs, carry_ab, cover_ab, card_ab, harness,
             *[N("ComponentAsset", artboardId=ab.id, name=ab.attrs["name"]) for ab in page_abs],
             N("ComponentAsset", artboardId=carry_ab.id, name="Carry"),
             N("ComponentAsset", artboardId=cover_ab.id, name="Cover"),
             N("ComponentAsset", artboardId=card_ab.id, name="ShareCard"),
             N("ComponentAsset", artboardId=recap.id, name="Recap"),
             *FONTS, *recap_extra, ctx_global()["moon_script"], *CONVERTERS, V.finish()]
    out = K.doc(*roots)
    os.makedirs(os.path.join(ROOT, "rml"), exist_ok=True)
    with open(os.path.join(ROOT, "rml", "recap.rml"), "w") as f:
        f.write(out)
    print(f"wrote rml/recap.rml ({len(out)//1024} KB, fixture={fixture_name})")


_CTX = {}


def ctx_global():
    if not _CTX:
        _CTX.update(V=V, serif=serif, italic=italic, sans=sans, DATA=DATA, SW=SW, SH=SH,
                    conv=conv, SCENES=SCENES, EXIT_MS=EXIT_MS,
                    moon_script=N("ScriptAsset", file="scripts/moon.luau", name="moon").ensure())
    return _CTX


def label_box(name, style, literal, prop):
    t = text(name, 0, 0, [(style, literal, bind(prop, 268) if prop else None)], sizing="autoWidth",
             wrap="noWrap")
    t.add(N("LayoutParticipant", layoutWidthScaleType="hug", layoutHeightScaleType="hug", name="LP"))
    return t.ensure()


def button(name, w, h, label_style=None, label=None, label_prop=None, icon=None,
           radius=None, fill_hex=None, stroke_hex=GOLD, a11y_prop=None, grow=False):
    st = N("LayoutComponentStyle", layoutWidthScaleType="fill" if grow else "fixed",
           layoutHeightScaleType="fixed", layoutAlignmentType="center", layoutTypeValue="stack",
           cornerRadiusTL=radius if radius is not None else h / 2, name=f"{name} Style").ensure()
    if grow:   # the primary grows with the row, up to a comfortable width
        st.attrs.update(maxWidth=340, maxWidthUnitsValue="points")
    lc = N("LayoutComponent", width=w, height=h, styleId=st.id, name=name).ensure()
    lc.add(N("SemanticData", N("DataBindContext", sourcePathIds=V.path(a11y_prop), propertyKey=983)
             if a11y_prop else None, role="button", label=_d(a11y_prop) if a11y_prop else label,
             name="Semantics"))
    lc.add(N("FocusData", name="Focus"))
    lc.add(st)
    if icon is not None:
        lc.add(icon)
    if label_style is not None:
        lc.add(label_box(f"{name} Label", label_style, label, label_prop))
    # paints last-declared-on-top: fill then stroke
    if fill_hex:
        lc.add(fill(fill_hex))
    lc.add(stroke(stroke_hex, 1.2, name="Outline"))
    return lc


def build_root(page_abs: list, carry_ab: N, cover_ab: N):
    style = N("LayoutComponentStyle", flexDirectionValue="column", name="Recap Style").ensure()
    sm = N("StateMachine", name="Recap").ensure()
    ab = N("Artboard", viewModelId=V.el.id, viewModelInstanceId=V.inst.id, width=RW, height=RH,
           styleId=style.id, defaultStateMachineId=sm.id, clip=True, name="Recap").ensure()
    ab.add(sm)
    ab.add(N("FocusData", name="Keyboard Focus Scope"))
    ab.add(N("SemanticData", role="group", label="Marginalia year in review", name="Semantics"))
    ab.add(style)

    # input + progress overlay (absolute, full size, on top)
    in_st = N("LayoutComponentStyle", positionTypeValue="absolute", positionLeft=0,
              positionLeftUnitsValue="points", positionTop=0, positionTopUnitsValue="points",
              positionRight=0, positionRightUnitsValue="points", positionBottom=0,
              positionBottomUnitsValue="points", layoutWidthScaleType="fixed",
              layoutHeightScaleType="fixed", widthUnitsValue="percent", heightUnitsValue="percent",
              name="Overlay Style").ensure()
    # the responsive layout rules, shared by the Director and the Page Stage;
    # a module must be declared before the scripts that require it
    resp = N("ScriptAsset", file="scripts/responsive.luau", isModule=True, folderPath="scripts", name="responsive").ensure()
    script = N("ScriptAsset", file="scripts/director.luau", name="director").ensure()
    overlay = N("LayoutComponent", in_st, N("ScriptedLayout", scriptAssetId=script.id, name="Director"),
                width=100, height=100, styleId=in_st.id, name="Director Overlay")
    ab.add(overlay)

    # header
    h_st = N("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fixed",
             positionTypeValue="absolute", positionTop=0, positionTopUnitsValue="points",
             positionLeft=0, positionLeftUnitsValue="points", positionRight=0,
             positionRightUnitsValue="points", flexDirectionValue="row", layoutAlignmentType="spaceBetweenStart", paddingLeft=24,
             paddingRight=24, paddingTop=22, name="Header Style").ensure()
    wm = text("Wordmark", 0, 0, [(italic(23, INK, 600), "Marginalia", None)], sizing="autoWidth")
    wm.add(N("LayoutParticipant", layoutWidthScaleType="hug", layoutHeightScaleType="hug", name="LP"))
    wm.add(N("SemanticData", role="text", label="Marginalia", headingLevel=1, name="Semantics"))
    yr = text("Year", 0, 0, [(sans(13, GOLDD, 500, ls=1.5), str(_d("year")), bind("yearText", 268))],
              sizing="autoWidth")
    yr.add(N("LayoutParticipant", layoutWidthScaleType="hug", layoutHeightScaleType="hug", name="LP"))
    h_st.attrs.update(widthUnitsValue="percent", layoutWidthScaleType="fixed")
    # responsive: height, padding and margins follow the real canvas (the
    # Director writes them from scripts/responsive.luau); it fades in as the
    # closed cover opens (_chromeAlpha)
    h_st.add(bind("_headerPadT", 514), bind("_marginX", 512), bind("_marginX", 513))
    header = N("LayoutComponent", h_st, bind("_headerH", 8), bind("_chromeAlpha", 18), wm, yr, width=100,
               height=HEADER_H, styleId=h_st.id, name="Header")

    # stage
    # the stage is the whole canvas: pages bleed edge to edge under the header
    # and the controls, and every page turn covers the full viewport
    s_st = N("LayoutComponentStyle", positionTypeValue="absolute", positionLeft=0,
             positionLeftUnitsValue="points", positionTop=0, positionTopUnitsValue="points",
             positionRight=0, positionRightUnitsValue="points", positionBottom=0,
             positionBottomUnitsValue="points", layoutWidthScaleType="fixed",
             layoutHeightScaleType="fixed", widthUnitsValue="percent", heightUnitsValue="percent",
             name="Stage Style").ensure()
    # The stage is drawn by the Page Stage script: it hosts the ten Page
    # artboards and Carry (all bound to the same UserRecap instance),
    # contain-fits them, and renders every page turn as a lit 3D paper curl.
    pt_script = N("ScriptAsset", file="scripts/pagestage.luau", name="pagestage").ensure()
    leaf = N("ScriptedLayout", *[N("ScriptInputArtboard", artboardId=ab.id, name=f"page{i + 1}")
                                 for i, ab in enumerate(page_abs)],
             N("ScriptInputArtboard", artboardId=carry_ab.id, name="carry"),
             N("ScriptInputArtboard", artboardId=cover_ab.id, name="cover"),
             scriptAssetId=pt_script.id, name="Page Stage").ensure()
    stage_sem = N("SemanticData", N("DataBindContext", sourcePathIds=V.path("a11yAnnouncement"), propertyKey=983),
                  role="text", isLiveRegion=True, label="", name="Scene Announcement")
    stage = N("LayoutComponent", s_st, stage_sem, leaf, width=100, height=100, styleId=s_st.id, name="Stage")

    # controls
    c_st = N("LayoutComponentStyle", layoutWidthScaleType="fill", layoutHeightScaleType="fixed",
             positionTypeValue="absolute", positionBottom=0, positionBottomUnitsValue="points",
             positionLeft=0, positionLeftUnitsValue="points", positionRight=0,
             positionRightUnitsValue="points", flexDirectionValue="row", layoutAlignmentType="center", paddingLeft=22,
             paddingRight=22, paddingBottom=22, gapHorizontal=12, name="Controls Style").ensure()
    lab = sans(16, INK, 500, ls=0.3)
    chev = lambda d: N("Node", shape("Chevron", poly([(-3 * d, -6), (3 * d, 0), (-3 * d, 6)], closed=False),
                                     stroke(INK, 1.8, cap="round", join="round")), x=22, y=22, name="Icon")
    prev = button("Previous", 48, 48, icon=chev(-1), a11y_prop="previousLabel")
    # primary: Continue / Share
    p_icons = N("Node", x=0, y=0, name="Primary Icons")
    primary = button("Primary", 120, 54, label_style=lab, label=_d("continueLabel"),
                     label_prop="continueLabel", a11y_prop="primaryA11yLabel", grow=True,
                     fill_hex=PAPER)
    # find the label run so the Controls layer can swap it
    plabel = [c for c in primary.children if c.tag == "Text"][0]
    share_lab = label_box("Share Label", sans(16, PAPER, 500, ls=0.3), _d("shareLabel"), "shareLabel")
    share_lab.attrs["opacity"] = 0
    primary.children.insert(len(primary.children) - 2, share_lab)
    pfill = [c for c in primary.children if c.tag == "Fill"][0]
    pfill_color = pfill.children[0].ensure()
    # secondary: pause/play/replay icons
    pause_ic = N("Node", shape("Bar L", rect(3, 14, x=-4), fill(INK)), shape("Bar R", rect(3, 14, x=4), fill(INK)),
                 x=24, y=24, name="Pause Icon").ensure()
    play_ic = N("Node", shape("Play", poly([(-4, -7), (7, 0), (-4, 7)]), fill(INK)), x=24, y=24, opacity=0,
                name="Play Icon").ensure()
    # replay: a clockwise arc open at the top, its arrowhead on the arc's end,
    # aligned to the tangent there (tip ahead of the stroke, base centred on it)
    rr, t0 = 7.0, -math.pi / 2 + 0.55
    t1 = t0 + 2 * math.pi - 1.15
    arc = [(rr * math.cos(t0 + (t1 - t0) * k / 16), rr * math.sin(t0 + (t1 - t0) * k / 16)) for k in range(17)]
    ex, ey = rr * math.cos(t1), rr * math.sin(t1)
    tx, ty = -math.sin(t1), math.cos(t1)          # travel direction (clockwise, y down)
    nx, ny = math.cos(t1), math.sin(t1)           # outward normal
    head = [(ex - tx * 0.4 + nx * 3.6, ey - ty * 0.4 + ny * 3.6), (ex + tx * 4.2, ey + ty * 4.2),
            (ex - tx * 0.4 - nx * 3.6, ey - ty * 0.4 - ny * 3.6)]
    replay_ic = N("Node", shape("Arc", N("PointsPath", *[N("StraightVertex", x=x, y=y) for x, y in arc],
                                         isClosed=False, name="Path"),
                                stroke(INK, 1.8, cap="round", join="round")),
                  shape("Head", poly(head), fill(INK)),
                  x=24, y=24, opacity=0, name="Replay Icon").ensure()
    secondary = button("Secondary", 48, 48, icon=[pause_ic, play_ic, replay_ic], a11y_prop="secondaryA11yLabel")
    sec_sem = [c for c in secondary.children if c.tag == "SemanticData"][0]
    c_st.attrs.update(widthUnitsValue="percent", layoutWidthScaleType="fixed")
    # orientation: the landscape layout keeps the controls together at the
    # bottom right of the spread (centerRight = 5); portrait centres them (4)
    c_st.add(bind("_controlsPadB", 515), bind("_marginX", 512), bind("_marginX", 513),
             bind("_controlsAlign", 632))
    controls = N("LayoutComponent", c_st, bind("_controlsH", 8), bind("_chromeAlpha", 18), prev, primary,
                 secondary, width=100, height=CONTROLS_H, styleId=c_st.id, name="Controls")
    # focus rings (one per control), toggled by the Focus layer
    rings = {}
    for b, nm in ((prev, "prev"), (primary, "primary"), (secondary, "secondary")):
        ring = N("Stroke", solid(OX), thickness=2.5, name="Focus Ring").ensure()
        ring.children[0].attrs["colorValue"] = K.argb(OX, 0)
        ring_col = ring.children[0].ensure()
        b.add(ring)
        rings[nm] = ring_col

    # paper: a procedural fibre grain + edge wear, multiplied over everything
    paper_script = N("ScriptAsset", file="scripts/paper.luau", name="paper").ensure()
    pp_st = N("LayoutComponentStyle", positionTypeValue="absolute", positionLeft=0,
              positionLeftUnitsValue="points", positionTop=0, positionTopUnitsValue="points",
              positionRight=0, positionRightUnitsValue="points", positionBottom=0,
              positionBottomUnitsValue="points", layoutWidthScaleType="fixed",
              layoutHeightScaleType="fixed", widthUnitsValue="percent", heightUnitsValue="percent",
              name="Paper Style").ensure()
    paper = N("LayoutComponent", pp_st, N("ScriptedLayout", scriptAssetId=paper_script.id, name="Paper Grain"),
              width=100, height=100, styleId=pp_st.id, name="Paper Overlay")
    ab.children.insert(ab.children.index(overlay) + 1, paper)
    ab.add(header, controls, stage)
    ab.add(N("Fill", solid(PARCH), name="Parchment"))

    # events
    ev_screen = N("Event", N("CustomPropertyNumber", bind("currentScreen", 243), propertyValue=1, name="screen"),
                  name="screenChanged").ensure()
    ev_share = N("Event", name="shareTapped").ensure()
    ev_fin = N("Event", name="recapFinished").ensure()
    ab.add(ev_screen, ev_share, ev_fin)

    anims: list[Anim] = []
    layers: list[Layer] = []
    # event layers
    for trig, ev in (("_evtScreen", ev_screen), ("_evtShare", ev_share), ("_evtFinished", ev_fin)):
        L = Layer(f"Event {ev.attrs['name']}")
        a_idle = Anim(f"Evt {ev.attrs['name']} Idle", 17)
        a_fire = Anim(f"Evt {ev.attrs['name']} Fire", 17)
        anims += [a_idle, a_fire]
        s0 = L.state(a_idle, 100, 0)
        s1 = L.state(a_fire, 360, 0)
        s1.add(N("StateMachineFireEvent", eventId=ev.id, occursValue=0))
        L.start(s0)
        trans(s0, s1, ctrig(trig))
        trans(s1, s0, exit_pct=100)
        layers.append(L)

    # controls layer: story vs summary mode
    L = Layer("Controls Mode")
    story = Anim("Controls Story", 17)
    story.set(plabel, "opacity", 1).set(share_lab, "opacity", 0).set(pfill_color, "colorValue", K.argb(PAPER), "color")
    story.set(pause_ic, "opacity", 1).set(replay_ic, "opacity", 0)
    summ = Anim("Controls Summary", 17)
    summ.set(plabel, "opacity", 0).set(share_lab, "opacity", 1).set(pfill_color, "colorValue", K.argb(OX), "color")
    summ.set(pause_ic, "opacity", 0).set(replay_ic, "opacity", 1).set(play_ic, "opacity", 0)
    anims += [story, summ]
    s_story = L.state(story, 100, 0)
    s_sum = L.state(summ, 360, 0)
    L.start(s_story)
    trans(s_story, s_sum, cnum("currentScreen", "equal", 10), ms=250, ease="soft")
    trans(s_sum, s_story, cnum("currentScreen", "notEqual", 10), ms=250, ease="soft")
    layers.append(L)

    # pause/play icon
    L = Layer("Pause Icon")
    playing = Anim("Icon Playing", 17)
    playing.set(pause_ic, "scaleX", 1).set(play_ic, "scaleX", 1)
    paused = Anim("Icon Paused", 17)
    anims += [playing, paused]
    s_pl = L.state(playing, 100, 0)
    s_pa = L.state(paused, 360, 0)
    L.start(s_pl)
    trans(s_pl, s_pa, cbool("isPaused", True), cnum("currentScreen", "notEqual", 10), ms=150)
    trans(s_pa, s_pl, cbool("isPaused", False), ms=150)
    trans(s_pa, s_pl, cnum("currentScreen", "equal", 10), ms=150)
    paused.set(pause_ic, "opacity", 0).set(play_ic, "opacity", 1)
    layers.append(L)

    # focus rings
    for idx, nm in ((1, "prev"), (2, "primary"), (3, "secondary")):
        L = Layer(f"Focus {nm}")
        off = Anim(f"Focus {nm} Off", 17).set(rings[nm], "colorValue", K.argb(OX, 0), "color")
        on = Anim(f"Focus {nm} On", 17).set(rings[nm], "colorValue", K.argb(OX, 1), "color")
        anims += [off, on]
        s_off = L.state(off, 100, 0)
        s_on = L.state(on, 360, 0)
        L.start(s_off)
        trans(s_off, s_on, cnum("_focus", "equal", idx), ms=120)
        trans(s_on, s_off, cnum("_focus", "notEqual", idx), ms=120)
        layers.append(L)
    # initial focus on the primary control
    layers[0].states[0].add(N("FocusActionTarget", targetId=primary.id))

    for L in layers:
        sm.add(L.build())

    # listeners -------------------------------------------------------
    def click_listener(target, trig, label):
        lst = N("StateMachineListener", N("ListenerInputType", listenerTypeValue="click"),
                N("ListenerInputTypeSemantic", N("SemanticInput", actionType="tap"),
                  listenerTypeValue="semanticAction"),
                N("ListenerInputTypeKeyboard", N("KeyboardInput", keyType="enter", keyPhase=1),
                  N("KeyboardInput", keyType="kpEnter", keyPhase=1), listenerTypeValue="keyboard"),
                write(trig, 1), targetId=target.id, name=label)
        return lst
    sm.add(click_listener(prev, "_cmdPrev", "Previous"))
    sm.add(click_listener(primary, "_cmdPrimary", "Primary (Continue / Share)"))
    sm.add(click_listener(secondary, "_cmdSecondary", "Secondary (Pause / Replay)"))
    for b, idx, nm in ((prev, 1, "prev"), (primary, 2, "primary"), (secondary, 3, "secondary")):
        sm.add(N("StateMachineListenerSingle", write("_focus", idx), targetId=b.id,
                 listenerTypeValue="focus", name=f"Focus {nm}"))
        sm.add(N("StateMachineListenerSingle", write("_focus", 0), targetId=b.id,
                 listenerTypeValue="blur", name=f"Blur {nm}"))

    def key_listener(keys, trig_or_action, label, mods=0):
        lt = N("ListenerInputTypeKeyboard", listenerTypeValue="keyboard")
        for k in keys:
            lt.add(N("KeyboardInput", keyType=k, keyPhase=1, modifiers=mods or None))
        act = write(trig_or_action, 1) if isinstance(trig_or_action, str) else trig_or_action
        return N("StateMachineListener", lt, act, targetId=ab.id, name=label)
    sm.add(key_listener(["left"], "_cmdPrev", "Key Left"))
    sm.add(key_listener(["right"], "_cmdNext", "Key Right"))
    sm.add(key_listener(["space"], "_cmdPause", "Key Space"))
    sm.add(key_listener(["tab"], N("FocusActionTraversal", traversalKind="next"), "Key Tab"))
    sm.add(key_listener(["tab"], N("FocusActionTraversal", traversalKind="previous"), "Key Shift Tab", mods=1))

    # diagnostic counters: event listeners on our own events count every fire,
    # so headless runs can prove "exactly once" (see README, Verification)
    plus1 = conv(N("DataConverterRangeMapper", minInput=0, maxInput=1, minOutput=1, maxOutput=2, name="Plus one"))
    for ev, prop in ((ev_screen, "_dbgScreenEvents"), (ev_share, "_dbgShareEvents"), (ev_fin, "_dbgFinishedEvents")):
        rd = N("DataBindContext", sourcePathIds=V.path(prop), propertyKey=636, converterId=plus1.id).ensure()
        sm.add(N("StateMachineListenerSingle",
                 N("ListenerViewModelChange",
                   N("BindablePropertyNumber", rd,
                     N("DataBindContext", sourcePathIds=V.path(prop), propertyKey=636, direction=True)),
                   fromViewModelProperty=True, fromDataBindId=rd.id),
                 targetId=ab.id, listenerTypeValue="event", eventId=ev.id, name=f"Count {ev.attrs['name']}"))
    for a in anims:
        ab.add(a.build())
    return ab, [resp, script, pt_script, paper_script]


if __name__ == "__main__":
    main()
