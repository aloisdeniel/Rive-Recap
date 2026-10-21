#!/usr/bin/env python3
"""Generate apps/patchwork/rive/scene.rml — the Patchwork ten-scene recap.

Run:  python3 apps/patchwork/tools/gen_scene.py
The RML it writes is the editable source of truth for the Rive project; this
script exists so the large, repetitive state-machine wiring stays consistent.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rml import *  # noqa
from art import *  # noqa

OUT = os.path.join(HERE, "..", "rive", "scene.rml")
W, H = 390, 844
reset_ids(1000)

# =====================================================================
# View model: the single UserRecap
# =====================================================================
vm = VM("UserRecap")
P = vm.prop
fixture = dict(
    userName="Alex", year=2026, periodLabel="January 1–December 31, 2026", locale="en-GB",
    volunteerHours=84, projectsJoined=12, communityDays=18, gardenSessions=9, repairItems=31,
    welcomeSessions=7, activeMonths=10, personaIndex=0, personaName="Neighborhood Weaver",
    personaDescription="You help the pieces belong.",
)
P("userName", "String", "Alex")
P("year", "Number", 2026)
P("periodLabel", "String", "January 1–December 31, 2026")
P("locale", "String", "en-GB")
for k in ["volunteerHours", "projectsJoined", "communityDays", "gardenSessions", "repairItems",
          "welcomeSessions", "activeMonths"]:
    P(k, "Number", fixture[k])
P("personaIndex", "Number", 0)
P("personaName", "String", "Neighborhood Weaver")
P("personaDescription", "String", "You help the pieces belong.")
P("personaColor", "Color", "FFCC7051")
P("autoAdvanceSeconds", "Number", 7)
P("autoAdvanceEnabled", "Boolean", True)
P("isPaused", "Boolean", False)
P("reducedMotion", "Boolean", False)
P("soundEnabled", "Boolean", False)
P("currentScreen", "Number", 1)
P("screenProgress", "Number", 0)
P("shareIncludeName", "Boolean", False)
P("shareIncludeSensitiveValues", "Boolean", False)
for k, v in [("continueLabel", "Continue"), ("previousLabel", "Previous"), ("pauseLabel", "Pause"),
             ("playLabel", "Play"), ("shareLabel", "Share"), ("replayLabel", "Replay"),
             ("introHeadline", "Your 2026 on Patchwork"), ("introSupport", "A year, uniquely yours."),
             ("summaryHeadline", "A little year. A lot of you."),
             ("summarySupport", "Take a piece of your year with you."),
             ("emptyHeadline", "Every story starts somewhere."),
             ("emptySupport", "Your next chapter is waiting."), ("personaLabel", "Your personal style")]:
    P(k, "String", v)
for i in range(1, 11):
    P(f"showScreen{i}", "Boolean", True)
COPY = {
    2: ("You showed up for your community.", "Your time joined something bigger.", "hours contributed"),
    3: ("Many ways to lend a hand.", "Different projects. A shared sense of care.", "projects joined"),
    4: ("A place in your calendar.", "Small commitments became shared moments.", "community days"),
    5: ("You helped something grow.", "Hands in the soil, alongside your neighbors.", "garden sessions"),
    6: ("More life in everyday things.", "Things repaired together, ready to be used again.", "items repaired"),
    7: ("You made space for someone.", "A warmer welcome, one gathering at a time.", "welcome sessions"),
    8: ("Care has a rhythm.", "You found your own way to contribute.", "active months"),
}
for n, (hd, sp, un) in COPY.items():
    P(f"screen{n}Headline", "String", hd)
    P(f"screen{n}Support", "String", sp)
    P(f"screen{n}Unit", "String", un)
# ---- documented additions (see README "binding contract")
P("thanksLabel", "String", "Thank you!")
P("numberGroupSeparator", "String", ",")
P("shareCaptureMode", "Boolean", False)
P("navNext", "Trigger")
P("navPrevious", "Trigger")
P("replayRecap", "Trigger")
P("screenChangedCount", "Number", 0)
P("shareTappedCount", "Number", 0)
P("recapFinishedCount", "Number", 0)
# ---- private (leading underscore): state-machine plumbing, never user data
P("_commitNext", "Trigger")
P("_commitPrev", "Trigger")
P("_commitReplay", "Trigger")
P("_settled", "Boolean", False)
P("_pressing", "Boolean", False)
P("_pressSide", "Number", 1)
P("_holdPaused", "Boolean", False)
P("_heroT", "Number", 0)
P("_finishedLatch", "Boolean", False)
P("_thanksOpen", "Boolean", False)
P("_focusIndex", "Number", 0)
P("_noActivity", "Boolean", False)

STAT = {2: "volunteerHours", 3: "projectsJoined", 4: "communityDays", 5: "gardenSessions",
        6: "repairItems", 7: "welcomeSessions", 8: "activeMonths"}

# =====================================================================
# Converters (root elements)
# =====================================================================
CONVS = []


def C(e):
    CONVS.append(e)
    return e.id


def tok_v(v):
    return el("FormulaTokenValue", operationValue=v)


def tok_b(prop, conv=None):
    return el("FormulaTokenValue", bind(vm, prop, 777, conv=conv))


def op(t):
    return el("FormulaTokenOperation", operationType=t)  # 0+ 1- 2* 3/ 4%


def fn(t):
    return el("FormulaTokenFunction", functionType=t)  # 0min 1max 2round 4floor


SEP = el("FormulaTokenArgumentSeparator")


def sep():
    return el("FormulaTokenArgumentSeparator")


def close():
    return el("FormulaTokenParenthesisClose")


def formula(name, *toks):
    return C(el("DataConverterFormula", *toks, name=name))


def group(name, *ids):
    return C(el("DataConverterGroup", *[el("DataConverterGroupItem", converterId=i) for i in ids], name=name))


TO_STR0 = C(el("DataConverterToString", decimals=0, round=True, name="Integer text"))
PAD3 = C(el("DataConverterStringPad", length=3, text="0", padType=0, name="Pad to 3"))
NEGATE = C(el("DataConverterBooleanNegate", name="Not"))
TO_NUM = C(el("DataConverterToNumber", name="To number"))
BOOL_TO_NUM = TO_NUM
HIDE_IF_FALSE = group("Visible to display", NEGATE, TO_NUM)  # false -> 1 (display none)
INC = C(el("DataConverterOperationValue", operationType=0, operationValue=1, name="Plus one"))


def roundT():
    """round(input * _heroT): the count-up value."""
    return [fn(2), el("FormulaTokenInput"), op(2), tok_b("_heroT"), close()]


C_MIL = formula("Count millions", fn(4), *roundT(), op(3), tok_v(1000000), close())
C_THOU = formula("Count thousands", fn(4), *roundT(), op(3), tok_v(1000), close())
C_THOU_MOD = formula("Count thousands mod", fn(4), *roundT(), op(3), tok_v(1000), close(), op(4), tok_v(1000))
C_REST = formula("Count remainder", *roundT(), op(4), tok_v(1000))
G_MIL = group("Millions text", C_MIL, TO_STR0)
G_THOU = group("Thousands text", C_THOU, TO_STR0)
G_THOUPAD = group("Thousands padded", C_THOU_MOD, TO_STR0, PAD3)
G_REST = group("Remainder text", C_REST, TO_STR0)
G_RESTPAD = group("Remainder padded", C_REST, TO_STR0, PAD3)
_size_cache = {}


def _tier(div):
    """min(1, floor(round(v*T)/div)) as a token list."""
    return [fn(0), tok_v(1), sep(), fn(4), *roundT(), op(3), tok_v(div), close(), close()]


def size_tier(S, tier):
    """Font size for one digit-group tier: 'M' (>= 1e6), 'K' (1e3..1e6) or '1' (< 1e3)."""
    key = (tier, S)
    if key not in _size_cache:
        if tier == "M":
            toks = [*_tier(1000000), op(2), tok_v(S)]
        elif tier == "K":
            toks = [el("FormulaTokenParenthesisOpen"), *_tier(1000), op(1), *_tier(1000000),
                    el("FormulaTokenParenthesisClose"), op(2), tok_v(S)]
        else:
            toks = [el("FormulaTokenParenthesisOpen"), tok_v(1), op(1), *_tier(1000), el("FormulaTokenParenthesisClose"),
                    op(2), tok_v(S)]
        _size_cache[key] = formula(f"Digits tier {tier} ({S})", *toks)
    return _size_cache[key]


# progress: tick increment of 0.1 s against a clamped dwell (min 3 s)
TICK_FRAMES = 6
C_TICK = formula("Progress tick", el("FormulaTokenInput"), op(0), tok_v(TICK_FRAMES / 60.0), op(3), fn(1), tok_v(3), sep(),
                 tok_b("autoAdvanceSeconds"), close())
C_BOOL_OPACITY = group("Bool to opacity", TO_NUM)
G_NOT_OPACITY = group("Negated bool to opacity", NEGATE, TO_NUM)
C_CHROME = formula("Chrome visible", tok_v(1), op(1), el("FormulaTokenInput"))  # input = shareCaptureMode as number
G_CHROME = group("Hide in capture", TO_NUM, C_CHROME)


def seg_fill(k):
    return formula(f"Segment {k} fill", fn(0), tok_v(1), sep(), fn(1), tok_v(0), sep(), el("FormulaTokenInput"), op(1),
                   tok_v(k), op(0), tok_b("screenProgress"), close(), close())


def focus_ring(k):
    return formula(f"Focus ring {k}", fn(1), tok_v(0), sep(), tok_v(1), op(1), el("FormulaTokenParenthesisOpen"),
                   el("FormulaTokenInput"), op(1), tok_v(k), el("FormulaTokenParenthesisClose"), op(2),
                   el("FormulaTokenParenthesisOpen"), el("FormulaTokenInput"), op(1), tok_v(k),
                   el("FormulaTokenParenthesisClose"), close())


# =====================================================================
# Fonts and text
# =====================================================================
FONT_BREE = new_id()
FONT_ATK = new_id()
FONT_ATKB = new_id()
FONTS = {
    "bree": (FONT_BREE, "Bree Serif", "Regular"),
    "atk": (FONT_ATK, "Atkinson Hyperlegible", "Regular"),
    "atkb": (FONT_ATKB, "Atkinson Hyperlegible", "Bold"),
}


class T:
    pass


def text(name, x, y, w, size, font, color, prop=None, lit="", align="center", lh=None, reveal=False,
         h=None, overflow=None, wrap=True, ls=None, conv=None, oy=0.0, rise=14):
    t = T()
    fid, fam, sty = FONTS[font]
    t.solid = solid(color)
    sa = dict(fontSize=size, fontAssetId=fid, familyName=fam, styleName=sty, name=name + " style")
    if lh:
        sa["lineHeight"] = lh
    if ls is not None:
        sa["letterSpacing"] = ls
    style = el("TextStylePaint", el("Fill", t.solid, name="Ink"), **sa)
    run_kids = [bind(vm, prop, 268, conv=conv)] if prop else []
    run = el("TextValueRun", *run_kids, styleId=style.id, text=lit, name=name + " run")
    kids = [style, run]
    if reveal:
        t.range = el("TextModifierRange", unitsValue=2, modifyFrom=-0.35, modifyTo=1, falloffFrom=0, falloffTo=1,
                     name="Words")
        t.mod = el("TextModifierGroup", t.range, modifyOpacity=True, modifyTranslation=True, invertOpacity=True,
                   opacity=0, y=rise, name="Reveal")
        kids.append(t.mod)
    ox = {"center": 0.5, "left": 0.0, "right": 1.0}[align]
    ta = dict(x=x, y=y, width=w, originX=ox, originY=oy, alignValue=align, name=name)
    if h is not None:
        ta.update(sizingValue="fixed", height=h, verticalAlignValue="middle")
    else:
        ta.update(sizingValue="autoHeight")
    ta["wrapValue"] = "wrap" if wrap else "noWrap"
    if overflow:
        ta["overflowValue"] = overflow
    t.el = el("Text", *kids, **ta)
    t.style = style
    return t


def reveal_keys(anim, t, f0, f1, ease="out"):
    anim.tween(t.range.id, 327, f0, -0.35, f1, 1.0, ease)
    anim.tween(t.range.id, 317, f0, 0.0, f1, 1.35, ease)


def hero_num(name, prop, x, y, w, size, color, stitch=OAT, align="center"):
    """Count-up numeral with locale digit grouping.

    Three run tiers share one Text; the tiers that do not apply collapse to a
    0-pt font size, so 84 / 4,821 / 1,234,567 all render with the bound
    numberGroupSeparator and no host-side string formatting.
    """
    t = T()
    fid, fam, sty = FONTS["bree"]

    def st(nm, conv):
        kids = [el("Fill", solid(color), name="Ink")]
        if stitch:
            kids.append(el("Stroke", solid(a(stitch, 0.9)),
                           el("DashPath", el("Dash", length=3.2, name="on"), el("Dash", length=2.6, name="off"), name="Stitch"),
                           thickness=max(1.0, size / 70.0), cap="round", name="Embroidery"))
        kids.append(bind(vm, prop, 274, conv=conv))
        return el("TextStylePaint", *kids, fontSize=size, fontAssetId=fid, familyName=fam, styleName=sty, name=nm)

    sM = st(name + " millions tier", size_tier(size, "M"))
    sK = st(name + " thousands tier", size_tier(size, "K"))
    s1 = st(name + " units tier", size_tier(size, "1"))
    R = lambda conv, style, nm, lit="": el("TextValueRun", bind(vm, prop, 268, conv=conv), styleId=style.id, text=lit, name=nm)
    S_ = lambda style, nm: el("TextValueRun", bind(vm, "numberGroupSeparator", 268), styleId=style.id, text="", name=nm)
    runs = [R(G_MIL, sM, "M millions"), S_(sM, "M sep 1"), R(G_THOUPAD, sM, "M thousands"), S_(sM, "M sep 2"),
            R(G_RESTPAD, sM, "M units"),
            R(G_THOU, sK, "K thousands"), S_(sK, "K sep"), R(G_RESTPAD, sK, "K units"),
            R(G_REST, s1, "value", "0")]
    ox = {"center": 0.5, "left": 0.0, "right": 1.0}[align]
    t.el = el("Text", sM, sK, s1, *runs, x=x, y=y, width=w, height=size * 1.15, originX=ox, originY=0.5,
              sizingValue="fixed", overflowValue="fitFontSize", alignValue=align, verticalAlignValue="middle",
              wrapValue="noWrap", name=name)
    return t


# =====================================================================
# Shared state for scenes
# =====================================================================
ANIMS = []
SCENES = {}
AMB_SWAY = Anim("ambient_sway", 240, loop="pingPong")
AMB_FLOW = Anim("ambient_flow", 240, loop="loop")
REST_SWAY = Anim("ambient_rest", 1)
HERO_CP = el("CustomPropertyNumber", bind(vm, "_heroT", 243, direction=True), propertyValue=0, name="heroCount")
HERO_DRIVER = node("Count driver", el("CustomPropertyGroup", HERO_CP, name="Count"))


def sway(obj, prop, rest, amp, ease="inout", flow=False):
    """Restrained idle: pingPong between rest and rest+amp."""
    if flow:
        AMB_FLOW.tween(obj, prop, 0, rest, 240, rest + amp, "linear")
    else:
        AMB_SWAY.tween(obj, prop, 0, rest, 240, rest + amp, ease)
    REST_SWAY.key(obj, prop, 0, rest)


class Scene:
    def __init__(self, n, title, frames=110, dark=False):
        self.n = n
        self.title = title
        self.frames = frames
        self.dark = dark
        self.root = node(f"S{n} {title}")
        self.anims = []  # entrance anims (one, or four for the persona scene)
        SCENES[n] = self

    def new_anim(self, suffix=""):
        an = Anim(f"s{self.n}_enter{suffix}", self.frames)
        self.anims.append(an)
        return an


def scene_text_block(sc, an, headline_prop, support_prop, hy=104, sy=694, dark=False, hsize=30, ssize=17, h_at=(66, 100),
                     s_at=(84, 110), hw=330, sdark=None):
    col = OAT if dark else IND
    sdark = dark if sdark is None else sdark
    scol = a(OAT, 0.92) if sdark else IND_D
    th = text(f"S{sc.n} headline", W / 2, hy, hw, hsize, "bree", col, prop=headline_prop, reveal=True, lh=hsize * 1.12)
    ts = text(f"S{sc.n} support", W / 2, sy, 320, ssize, "atk", scol, prop=support_prop, reveal=True, lh=ssize * 1.3,
              rise=8)
    reveal_keys(an, th, *h_at)
    reveal_keys(an, ts, *s_at)
    return th, ts


def pop(an, obj, f0, f1, ease="cloth", s0=0.0, s1=1.0):
    an.tween(obj, "scaleX", f0, s0, f1, s1, ease)
    an.tween(obj, "scaleY", f0, s0, f1, s1, ease)


def count_keys(an, f0=14, f1=72, ease="thread"):
    an.tween(HERO_CP.id, "propertyValue", f0, 0.0, f1, 1.0, ease)


def bg(color, name="Ground"):
    return shape(name, rect(W + 80, H + 80, ox=0, oy=0), fill(color), x=-40, y=-40)


def quilt_lines(color, step=48, name="Quilting"):
    """Faint diagonal quilting lines across the background (one shape, many paths)."""
    paths = []
    for i in range(-10, 20):
        x0 = i * step
        paths.append(el("PointsPath", el("StraightVertex", x=x0, y=-40), el("StraightVertex", x=x0 + 900, y=880),
                        isClosed=False, name=f"L{i}"))
    return shape(name, *paths, stroke(color, 1.0, dash=(6, 6)))


# =====================================================================
# Scene 1 — Invitation
# =====================================================================
def build_s1():
    sc = Scene(1, "Invitation", frames=118)
    an = sc.new_anim()
    cx, cy, cell, gap = 195, 386, 82, 6
    motifs = [
        (TER, lambda: m_house(56, OAT, IND, x=0, y=-4)),
        (ROSE, lambda: m_heart(52, TER)),
        (TEAL, lambda: m_leaf(60, OAT)),
        (IND, lambda: m_people(58, OAT)),
        (OAT_D, None),
        (TER_L, lambda: m_sun(58, MUST, ray=OAT)),
        (TEAL_D, lambda: m_tree(56, TEAL_L, trunk=OAT)),
        (IND_L, lambda: m_book(52, ROSE)),
        (ROSE_D, lambda: m_bike(60, IND)),
    ]
    starts = [(-150, -260, -0.8), (40, -300, 0.5), (220, -200, 0.9), (-240, 20, -0.6), (0, 0, 0),
              (240, 60, 0.7), (-200, 280, 0.8), (30, 320, -0.5), (230, 260, -0.9)]
    patches = []
    flap = None
    for i, (col, mf) in enumerate(motifs):
        r, c = divmod(i, 3)
        px = cx + (c - 1) * (cell + gap)
        py = cy + (r - 1) * (cell + gap)
        inner = None
        if i == 2:
            # the signature-interaction patch: a corner flap hides a tiny thanks
            thanks = text("S1 thanks", 21, -21, 56, 9, "atkb", IND, prop="thanksLabel", lit="Thank you!", align="center",
                          oy=0.5)
            thanks.el.attrs["rotation"] = 0.785398
            under = shape("Under flap", el("PointsPath", el("StraightVertex", x=41, y=-41), el("StraightVertex", x=41, y=12),
                                              el("StraightVertex", x=-12, y=-41), isClosed=True, name="Path"),
                          fill(CREAM))
            flap = node("Thanks flap hinge", shape("Flap", el("PointsPath", el("StraightVertex", x=0, y=-34),
                                                                   el("StraightVertex", x=34, y=0),
                                                                   el("StraightVertex", x=0, y=34),
                                                                   isClosed=True, name="Path"),
                                                   fill(TEAL_L), stroke(a(OAT, 0.9), 1.2, dash=(4, 3))),
                        x=17, y=-17, rotation=-0.785398)
            inner = [flap, thanks.el, under]
        outer, body = patch(f"S1 patch {i}", cell, cell, col, motif=mf() if mf else None, x=px, y=py, inner=inner)
        patches.append((outer, body, px, py))
        sx, sy, sr = starts[i]
        f0 = 10 + [4, 0, 8, 12, 2, 16, 20, 6, 24][i] * 1.5
        an.tween(outer.id, "x", f0, px + sx, f0 + 34, px, "cloth")
        an.tween(outer.id, "y", f0, py + sy, f0 + 34, py, "cloth")
        an.tween(outer.id, "rotation", f0, sr, f0 + 40, 0.0, "back")
        an.tween(outer.id, "opacity", f0, 0.0, f0 + 8, 1.0, "linear")
        an.tween(body.id, "scaleX", f0, 0.55, f0 + 34, 1.0, "cloth")
        an.tween(body.id, "scaleY", f0, 0.55, f0 + 34, 1.0, "cloth")
    sc.flap = flap
    # wordmark banner unfolding over the middle row
    word = text("S1 wordmark", 0, 0, 250, 40, "bree", IND, lit="Patchwork", oy=0.5)
    bstitch = shape("Banner stitch", rect(258, 62, r=4), stroke(a(TER, 0.9), 1.5, dash=(6, 4)))
    bcloth = shape("Banner cloth", fabric_quad(276, 78, j=2), fill(CREAM))
    bshade = shape("Banner shade", fabric_quad(276, 78, j=2), fill(SHADOW), x=3, y=5)
    tabL = shape("Banner tail L", el("PointsPath", el("StraightVertex", x=-150, y=-30), el("StraightVertex", x=-128, y=-30),
                                     el("StraightVertex", x=-128, y=30), el("StraightVertex", x=-150, y=30),
                                     el("StraightVertex", x=-140, y=0), isClosed=True, name="Path"), fill(TER))
    tabR = shape("Banner tail R", el("PointsPath", el("StraightVertex", x=150, y=-30), el("StraightVertex", x=128, y=-30),
                                     el("StraightVertex", x=128, y=30), el("StraightVertex", x=150, y=30),
                                     el("StraightVertex", x=140, y=0), isClosed=True, name="Path"), fill(TER))
    banner_in = node("Banner sway", word.el, bstitch, bcloth, bshade)
    banner = node("S1 banner", banner_in, tabL, tabR, x=cx, y=cy)
    an.tween(banner.id, "scaleX", 52, 0.0, 84, 1.0, "cloth")
    an.tween(banner.id, "scaleY", 52, 0.4, 76, 1.0, "back")
    an.tween(banner.id, "opacity", 52, 0.0, 58, 1.0, "linear")
    sway(banner_in.id, "rotation", -0.012, 0.024)
    # running thread around the quilt
    thread_trim = el("TrimPath", start=0, end=0, name="Draw")
    tpath = curve_path([(-30, 520, -0.4, 50), (44, 470, -1.4, 50), (52, 270, -1.7, 50), (195, 206, 0.0, 70),
                        (338, 270, 1.6, 50), (342, 470, 1.5, 40), (420, 520, 0.4, 40)])
    thread = shape("S1 thread", tpath, el("Stroke", solid(TER), el("DashPath", el("Dash", length=7, name="on"),
                                                                    el("Dash", length=5, name="off"), name="Running stitch"),
                                          thread_trim, thickness=2.2, cap="round", name="Thread"))
    an.tween(thread_trim.id, "end", 4, 0.0, 96, 1.0, "inout")
    # name tag + period
    tag_txt = text("S1 name", 0, 0, 220, 21, "bree", IND, prop="userName", lit="", overflow="ellipsis", h=28, wrap=True,
                   oy=0.5)
    tag_txt.el.attrs["verticalAlignValue"] = "top"
    tag_txt.el.attrs["y"] = -14
    tag_txt.el.attrs["originY"] = 0
    tag = node("S1 name tag", tag_txt.el,
               shape("Tag stitch", rect(236, 40, r=6), stroke(a(OAT, 0.95), 1.3, dash=(5, 4))),
               shape("Tag cloth", fabric_quad(250, 52, j=1.5), fill(ROSE)), x=cx, y=146)
    period = text("S1 period", cx, 180, 320, 14, "atk", IND_D, prop="periodLabel", reveal=True)
    head = text("S1 headline", cx, 552, 330, 32, "bree", IND, prop="introHeadline", reveal=True, lh=36)
    sup = text("S1 support", cx, 640, 320, 17, "atk", IND_D, prop="introSupport", reveal=True)
    an.seq(tag.id, "y", [(0, 110, "antic"), (10, 100, "cloth"), (40, 146)])
    an.tween(tag.id, "rotation", 6, -0.22, 54, 0.0, (0.3, 1.6, 0.5, 1.0))
    an.tween(tag.id, "opacity", 4, 0.0, 12, 1.0, "linear")
    reveal_keys(an, period, 40, 76)
    reveal_keys(an, head, 72, 104)
    reveal_keys(an, sup, 88, 116)
    an.key(HERO_CP.id, "propertyValue", 0, 1.0)
    sc.root.add(tag, period.el, banner, *[p[0] for p in reversed(patches)], thread, head.el, sup.el,
                quilt_lines(a(OAT_DD, 0.35)), bg(OAT))
    return sc


# =====================================================================
# Scene 2 — Hours contributed (star block around an embroidered numeral)
# =====================================================================
def build_s2():
    sc = Scene(2, "Hours", frames=112)
    an = sc.new_anim()
    cx, cy = 195, 420
    card_w, card_h = 196, 176
    # four hinged triangles + four corner squares
    tri = []
    specs = [  # (name, pivot dx, dy, rotation, colour, motif)
        ("top", 0, -card_h / 2, 0.0, TER, lambda: m_heart(40, ROSE, y=-34)),
        ("right", card_w / 2, 0, math.pi / 2, ROSE, lambda: m_leaf(46, TEAL, y=-36)),
        ("bottom", 0, card_h / 2, math.pi, TEAL, lambda: m_sun(46, MUST, ray=OAT, y=-36)),
        ("left", -card_w / 2, 0, -math.pi / 2, IND, lambda: m_people(44, OAT, y=-36)),
    ]
    for i, (nm, dx, dy, rot, col, mf) in enumerate(specs):
        base = card_w if nm in ("top", "bottom") else card_h
        tri_path = el("PointsPath", el("StraightVertex", x=-base / 2 - 8, y=0), el("StraightVertex", x=0, y=-82, radius=6),
                      el("StraightVertex", x=base / 2 + 8, y=0), isClosed=True, isClockwise=True, name="Path")
        st_path = el("PointsPath", el("StraightVertex", x=-base / 2 + 12, y=-7), el("StraightVertex", x=0, y=-68),
                     el("StraightVertex", x=base / 2 - 12, y=-7), isClosed=True, isClockwise=True, name="Path")
        body = node(f"S2 {nm} body", *mf(), shape("Stitch", st_path, stroke(a(OAT, 0.85), 1.3, dash=(5, 4))),
                    shape("Cloth", tri_path, fill(col)))
        hinge = node(f"S2 {nm} hinge", body, x=cx + dx, y=cy + dy, rotation=rot)
        tri.append(hinge)
        f0 = 14 + i * 7
        an.seq(body.id, "scaleY", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 26, 1.0)])
        an.seq(body.id, "scaleX", [(0, 0.6), (f0, 0.6, "back"), (f0 + 26, 1.0)])
        sway(body.id, "scaleY", 1.0, 0.03)
    corners = []
    cspec = [(-1, -1, TEAL_D, lambda: m_house(46, OAT, TER)), (1, -1, IND_L, lambda: m_tree(46, TEAL_L, trunk=OAT)),
             (-1, 1, TER_L, lambda: m_flower(46, ROSE_L)), (1, 1, ROSE_D, lambda: m_bike(50, IND))]
    for i, (sx, sy, col, mf) in enumerate(cspec):
        px, py = cx + sx * 132, cy + sy * 122
        outer, body = patch(f"S2 corner {i}", 74, 74, col, motif=mf(), x=px, y=py, rot=sx * sy * 0.06)
        corners.append(outer)
        f0 = 38 + i * 6
        an.seq(outer.id, "scaleX", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 24, 1.0)])
        an.seq(outer.id, "scaleY", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 24, 1.0)])
        an.seq(outer.id, "rotation", [(0, sx * 0.8), (f0, sx * 0.8, "back"), (f0 + 30, sx * sy * 0.06)])
        sway(body.id, "rotation", -0.02 * sx, 0.04 * sx)
    num = hero_num("S2 hours", "volunteerHours", 0, -12, 180, 96, IND)
    unit = text("S2 unit", 0, 50, 176, 15, "atkb", IND, prop="screen2Unit", oy=0.5, h=40, overflow="fitFontSize", wrap=True, lh=17)
    card = node("S2 card", num.el, unit.el,
                shape("Card stitch", rect(card_w - 16, card_h - 16, r=4), stroke(a(TER, 0.8), 1.4, dash=(6, 4))),
                shape("Card cloth", fabric_quad(card_w, card_h, j=1.5), fill(CREAM)),
                shape("Card shade", fabric_quad(card_w, card_h, j=1.5), fill(SHADOW), x=3, y=5),
                x=cx, y=cy)
    an.seq(card.id, "scaleX", [(0, 0.92, "antic"), (10, 0.86, "cloth"), (30, 1.0)])
    an.seq(card.id, "scaleY", [(0, 0.92, "antic"), (10, 0.86, "cloth"), (30, 1.0)])
    an.tween(card.id, "opacity", 0, 0.0, 6, 1.0, "linear")
    an.tween(unit.el.id, "opacity", 50, 0.0, 70, 1.0, "out")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen2Headline", "screen2Support", hy=104, sy=650)
    sc.root.add(th.el, card, *tri, *corners, ts.el, quilt_lines(a(OAT_DD, 0.4)), bg(OAT))
    return sc


# =====================================================================
# Scene 3 — Projects joined (twelve patches stitch into a flexible grid)
# =====================================================================
def build_s3():
    sc = Scene(3, "Projects", frames=112)
    an = sc.new_anim()
    num = hero_num("S3 projects", "projectsJoined", 34, 268, 200, 150, TER, stitch=OAT, align="left")
    unit = text("S3 unit", 40, 350, 200, 18, "atkb", IND, prop="screen3Unit", align="left", wrap=True)
    gx, gy, cell, gap = 210, 540, 70, 4
    grid = node("S3 quilt", x=gx, y=gy, rotation=-0.07)
    items = [(TER, lambda: m_house(44, OAT, IND)), (ROSE, lambda: m_heart(40, TER)), (TEAL, lambda: m_leaf(48, OAT)),
             (IND, lambda: m_people(44, ROSE)), (MUST, lambda: m_sun(46, TER, ray=OAT)),
             (TEAL_D, lambda: m_tree(44, TEAL_L, trunk=OAT)),
             (ROSE_D, lambda: m_book(42, IND)), (IND_L, lambda: m_mug(40, OAT)), (TER_L, lambda: m_bike(48, IND)),
             (OAT_D, lambda: m_star(44, TER)), (TEAL_L, lambda: m_flower(44, OAT, centre=TER)),
             (TER_D, lambda: m_tools(40, OAT, ROSE))]
    seams = []
    for i, (col, mf) in enumerate(items):
        r, c = divmod(i, 4)
        px = (c - 1.5) * (cell + gap)
        py = (r - 1) * (cell + gap)
        outer, body = patch(f"S3 patch {i}", cell, cell, col, motif=mf(), x=px, y=py, rot=((i * 37) % 7 - 3) * 0.012)
        grid.add(outer)
        f0 = 8 + i * 4.2
        an.seq(outer.id, "y", [(0, py + 420), (f0, py + 420, "cloth"), (f0 + 26, py)])
        an.seq(outer.id, "rotation", [(0, (1 if i % 2 else -1) * 0.7), (f0, (1 if i % 2 else -1) * 0.7, "back"),
                                      (f0 + 30, ((i * 37) % 7 - 3) * 0.012)])
        an.seq(body.id, "scaleY", [(0, 1.0), (f0 + 24, 1.0, "out"), (f0 + 28, 0.9, "cloth"), (f0 + 38, 1.0)])
    # seam stitches between rows / columns
    seam_trim = el("TrimPath", start=0, end=0, modeValue="synchronized", name="Sew")
    sp = []
    for r in range(1, 3):
        y = (r - 1.5) * (cell + gap)
        sp.append(el("PointsPath", el("StraightVertex", x=-2 * (cell + gap), y=y), el("StraightVertex", x=2 * (cell + gap), y=y),
                     isClosed=False, name=f"Row{r}"))
    for c in range(1, 4):
        x = (c - 2) * (cell + gap)
        sp.append(el("PointsPath", el("StraightVertex", x=x, y=-1.5 * (cell + gap)), el("StraightVertex", x=x, y=1.5 * (cell + gap)),
                     isClosed=False, name=f"Col{c}"))
    seam = shape("S3 seams", *sp, el("Stroke", solid(IND_D), el("DashPath", el("Dash", length=5, name="on"),
                                                              el("Dash", length=4, name="off"), name="d"),
                                     seam_trim, thickness=2, cap="round", name="Seam thread"))
    grid.children.insert(0, seam)
    an.tween(seam_trim.id, "end", 62, 0.0, 96, 1.0, "inout")
    sway(grid.id, "rotation", -0.075, 0.012)
    an.tween(unit.el.id, "opacity", 48, 0.0, 70, 1.0, "out")
    an.seq(num.el.id, "x", [(0, 34, "antic"), (12, 22, "cloth"), (40, 34)])
    an.tween(num.el.id, "opacity", 0, 0.0, 10, 1.0, "linear")
    count_keys(an, 12, 62, (0.3, 0.1, 0.4, 1.0))
    th, ts = scene_text_block(sc, an, "screen3Headline", "screen3Support", hy=104, sy=690)
    sc.root.add(th.el, num.el, unit.el, grid, ts.el, quilt_lines(a(OAT_DD, 0.35)), bg(OAT))
    return sc


# =====================================================================
# Scene 4 — Community days (a calendar folds into fabric strips)
# =====================================================================
def build_s4():
    sc = Scene(4, "Days", frames=116)
    an = sc.new_anim()
    sky = "FFDDE7E1"
    # landscape
    sun_rays = m_sun(80, TER, ray=a(TER, 0.6))
    sun = node("S4 sun", *sun_rays, x=318, y=228)
    sway(sun.id, "rotation", 0.0, 0.12)
    clouds = []
    for i, (x, y, s) in enumerate([(70, 236, 1.0), (300, 300, 0.8)]):
        c = node(f"S4 cloud {i}", shape("Cloud", el("Ellipse", width=70 * s, height=34 * s, name="a"),
                                          el("Ellipse", width=44 * s, height=40 * s, x=-16 * s, y=-12 * s, name="b"),
                                          el("Ellipse", width=40 * s, height=36 * s, x=16 * s, y=-10 * s, name="c"),
                                          fill(CREAM), stroke(a(OAT_DD, 0.9), 1.2, dash=(4, 3))), x=x, y=y)
        clouds.append(c)
        sway(c.id, "x", x - 6, 12)
    hills = [
        shape("S4 hill back", curve_path([(-40, 560, 0, 0), (60, 500, 0.3, 60), (200, 540, 0.0, 70), (330, 480, -0.2, 60),
                                          (440, 520, 0, 0), (440, 900, 0, 0), (-40, 900, 0, 0)], closed=True),
              fill(TEAL_L), stroke(a(OAT, 0.7), 1.3, dash=(5, 4))),
        shape("S4 hill front", curve_path([(-40, 640, 0, 0), (120, 590, 0.1, 70), (260, 640, 0.2, 60), (440, 600, 0, 0),
                                           (440, 900, 0, 0), (-40, 900, 0, 0)], closed=True),
              fill(TEAL_D), stroke(a(OAT, 0.6), 1.3, dash=(5, 4))),
    ]
    # fabric strips unrolling from the calendar like a scarf
    strips = []
    strip_cols = [ROSE, TER, IND, MUST, TEAL]
    for i, col in enumerate(strip_cols):
        off = (i - 2) * 30
        trim = el("TrimPath", start=0, end=0, name="Unroll")
        pth = curve_path([(196 + off, 440, 1.57, 30), (150 + off * 0.8, 560, 2.2, 50), (60 + off * 0.6, 640, 2.0, 50),
                          (-30 + off * 0.4, 760, 2.4, 40)])
        strips.append(shape(f"S4 strip {i}", pth,
                            el("Stroke", solid(a(OAT, 0.9)), el("DashPath", el("Dash", length=6, name="on"), el("Dash", length=5, name="off"), name="d"),
                               el("TrimPath", start=0, end=0, name="Unroll stitch"), thickness=1.3, cap="round", name="Stitch"),
                            el("Stroke", solid(col), trim, thickness=28, cap="butt", name="Ribbon")))
        f0 = 34 + i * 6
        an.tween(trim.id, "end", f0, 0.0, f0 + 40, 1.0, "out")
        an.tween(strips[-1].children[1].children[2].id, "end", f0 + 6, 0.0, f0 + 46, 1.0, "out")
    # calendar
    cw, chh = 222, 252
    num = hero_num("S4 days", "communityDays", 0, -40, 180, 92, IND)
    unit = text("S4 unit", 0, 20, 190, 15, "atkb", IND, prop="screen4Unit", oy=0.5, h=36, overflow="fitFontSize", wrap=True, lh=17)
    days = []
    marks = {3: ROSE, 8: TEAL, 10: TER, 16: IND, 19: ROSE}
    for d in range(21):
        r, c = divmod(d, 7)
        col = marks.get(d)
        sq = shape(f"Day {d}", rect(20, 16, r=2), fill(col if col else a(OAT_DD, 0.8)),
                   x=-75 + c * 25, y=52 + r * 21)
        days.append(sq)
        if col:
            an.seq(sq.id, "scaleX", [(0, 0.0), (60 + d * 1.6, 0.0, "back"), (72 + d * 1.6, 1.0)])
            an.seq(sq.id, "scaleY", [(0, 0.0), (60 + d * 1.6, 0.0, "back"), (72 + d * 1.6, 1.0)])
    heart = node("Cal heart", *m_heart(22, TER, stitch=False), x=88, y=-104)
    pop(an, heart.id, 86, 100, "back")
    rings = [shape(f"Ring {i}", rect(8, 26, r=4), fill(IND_D), x=x, y=-chh / 2 - 2) for i, x in enumerate((-60, 60))]
    cal_in = node("Calendar body", heart, *rings, num.el, unit.el, *days,
                  shape("Header", rect(cw - 2, 40, r=6, oy=0), fill(TER), stroke(a(OAT, 0.9), 1.3, dash=(5, 4)), y=-chh / 2),
                  shape("Page stitch", rect(cw - 16, chh - 16, r=4), stroke(a(TER, 0.6), 1.3, dash=(5, 4))),
                  shape("Page", fabric_quad(cw, chh, j=1.5, r=8), fill(CREAM)),
                  shape("Page shade", fabric_quad(cw, chh, j=1.5, r=8), fill(SHADOW), x=4, y=6))
    cal = node("S4 calendar", cal_in, x=205, y=372, rotation=0.06)
    an.seq(cal.id, "y", [(0, 352, "antic"), (8, 342, "in"), (14, 342, "cloth"), (44, 372)])
    an.seq(cal.id, "rotation", [(0, -0.05), (14, -0.2, (0.3, 1.5, 0.5, 1.0)), (56, 0.06)])
    an.seq(cal_in.id, "scaleY", [(0, 1.0), (40, 1.0, "out"), (46, 0.94, "cloth"), (62, 1.0)])
    an.tween(cal.id, "opacity", 0, 0.0, 6, 1.0, "linear")
    an.tween(unit.el.id, "opacity", 50, 0.0, 68, 1.0, "out")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen4Headline", "screen4Support", hy=104, sy=712, sdark=False)
    ts.el.attrs["originY"] = 0.5
    sway(cal.id, "rotation", 0.05, 0.02)
    plate = shape("S4 copy plate", rect(340, 58, r=14), fill(a(CREAM, 0.94)), stroke(a(TER, 0.5), 1.2, dash=(5, 4)), x=W / 2, y=712)
    sc.root.add(th.el, ts.el, plate, cal, *strips, *hills, *clouds, sun, bg(sky))
    return sc


# =====================================================================
# Scene 5 — Garden sessions (a stitched sprout grows through cloth soil)
# =====================================================================
def build_s5():
    sc = Scene(5, "Garden", frames=114)
    an = sc.new_anim()
    bands = []
    bcols = [TER, ROSE_D, IND, TEAL_L]
    for i, col in enumerate(bcols):
        y0 = 500 + i * 62
        pth = curve_path([(-40, y0 + 10, 0, 0), (90, y0 - 12 + (i % 2) * 18, 0.1, 60), (220, y0 + 8, -0.1, 60),
                          (430, y0 - 6, 0, 0), (430, 900, 0, 0), (-40, 900, 0, 0)], closed=True)
        b = shape(f"S5 soil {i}", pth, fill(col), stroke(a(OAT, 0.75), 1.4, dash=(6, 4)))
        bands.append(b)
        f0 = 6 + i * 5
        an.seq(b.id, "y", [(0, 260), (f0, 260, "cloth"), (f0 + 30, 0)])
    seeds = [shape(f"Seed {i}", ellipse(10, 6), fill(a(OAT, 0.8)), x=x, y=y, rotation=r)
             for i, (x, y, r) in enumerate([(60, 590, 0.4), (330, 660, -0.3), (150, 720, 0.2), (250, 780, -0.5), (80, 790, 0.1)])]
    # sprout
    stem_trim = el("TrimPath", start=0, end=0, name="Grow")
    stem = shape("S5 stem", curve_path([(272, 520, 0, 0), (262, 430, -1.75, 40), (284, 330, -1.4, 40), (276, 250, -1.6, 30)]),
                 el("Stroke", solid(TEAL), stem_trim, thickness=9, cap="round", name="Stem"),
                 el("Stroke", solid(a(OAT, 0.7)), el("DashPath", el("Dash", length=4, name="on"), el("Dash", length=4, name="off"), name="d"),
                    el("TrimPath", start=0, end=0, name="Grow stitch"), thickness=1.2, cap="round", name="Stem stitch"))
    an.tween(stem_trim.id, "end", 20, 0.0, 78, 1.0, "out")
    an.tween(stem.children[2].children[2].id, "end", 24, 0.0, 82, 1.0, "out")
    leaves = []
    for i, (x, y, side, s, f0) in enumerate([(266, 440, -1, 1.0, 40), (270, 400, 1, 0.9, 50), (281, 330, -1, 0.8, 60),
                                              (282, 300, 1, 0.75, 66)]):
        leaf_shape = shape("Leaf", el("Ellipse", width=70 * s, height=30 * s, x=35 * s, name="Path"), fill(TEAL if i % 2 else TEAL_D))
        mid = shape("Midrib", el("PointsPath", el("StraightVertex", x=4, y=0), el("StraightVertex", x=64 * s, y=0),
                                 isClosed=False, name="Path"), stroke(a(OAT, 0.85), 1.2, dash=(4, 3)))
        sway_n = node("Leaf sway", mid, leaf_shape)
        lf = node(f"S5 leaf {i}", sway_n, x=x, y=y, rotation=(-2.6 if side < 0 else -0.5), scaleX=1)
        leaves.append(lf)
        an.seq(lf.id, "scaleX", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 24, 1.0)])
        an.seq(lf.id, "scaleY", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 24, 1.0)])
        sway(sway_n.id, "rotation", -0.05 * side, 0.1 * side)
    bloom = node("S5 bloom", *m_flower(54, ROSE, centre=MUST), x=276, y=244)
    an.seq(bloom.id, "scaleX", [(0, 0.0), (78, 0.0, "back"), (96, 1.0)])
    an.seq(bloom.id, "scaleY", [(0, 0.0), (78, 0.0, "back"), (96, 1.0)])
    an.seq(bloom.id, "rotation", [(0, -1.0), (78, -1.0, "out"), (100, 0.0)])
    sway(bloom.id, "rotation", -0.06, 0.12)
    num = hero_num("S5 garden", "gardenSessions", 116, 360, 200, 150, TER, align="center")
    unit = text("S5 unit", 116, 440, 190, 17, "atkb", IND, prop="screen5Unit", wrap=True)
    an.tween(unit.el.id, "opacity", 50, 0.0, 70, 1.0, "out")
    an.seq(num.el.id, "y", [(0, 380, "antic"), (12, 392, "cloth"), (40, 360)])
    an.tween(num.el.id, "opacity", 0, 0.0, 12, 1.0, "linear")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen5Headline", "screen5Support", hy=104, sy=712, sdark=False)
    ts.el.attrs["originY"] = 0.5
    plate = shape("S5 copy plate", rect(340, 58, r=14), fill(a(CREAM, 0.94)), stroke(a(TER, 0.5), 1.2, dash=(5, 4)), x=W / 2, y=712)
    sc.root.add(th.el, ts.el, plate, num.el, unit.el, bloom, *leaves, stem, *seeds, *reversed(bands), bg("FFF6E3DC"))
    return sc


# =====================================================================
# Scene 6 — Items repaired (a seam reconnects two fabric shapes)
# =====================================================================
def build_s6():
    sc = Scene(6, "Repairs", frames=114)
    an = sc.new_anim()
    left = shape("Left cloth", curve_path([(0, -120, 0, 0), (-60, -110, 2.8, 30), (-130, -40, 1.9, 50), (-120, 80, 1.2, 50),
                                           (-50, 130, 0.2, 40), (0, 120, 0, 0)], closed=True),
                 fill(TEAL), stroke(a(OAT, 0.8), 1.4, dash=(6, 4)))
    right = shape("Right cloth", curve_path([(0, -120, 0, 0), (70, -126, 0.2, 40), (136, -60, 1.3, 50), (124, 70, 1.9, 50),
                                             (60, 128, 2.9, 40), (0, 120, 0, 0)], closed=True),
                  fill(IND), stroke(a(OAT, 0.8), 1.4, dash=(6, 4)))
    lpatch = node("Left motif", *m_mug(46, OAT), x=-66, y=-6)
    rpatch = node("Right motif", *m_book(48, ROSE), x=66, y=8)
    L = node("S6 left", lpatch, left, x=195, y=520)
    R = node("S6 right", rpatch, right, x=195, y=520)
    an.seq(L.id, "x", [(0, 120), (8, 96, "in"), (14, 96, "cloth"), (40, 195)])
    an.seq(R.id, "x", [(0, 270), (8, 294, "in"), (14, 294, "cloth"), (40, 195)])
    an.seq(L.id, "rotation", [(0, -0.25), (14, -0.3, "back"), (46, 0.0)])
    an.seq(R.id, "rotation", [(0, 0.25), (14, 0.3, "back"), (46, 0.0)])
    xs = []
    for i in range(9):
        y = 520 - 96 + i * 24
        xm = node(f"Stitch {i}", m_cross_stitch(14, CREAM), x=195 + (2 if i % 2 else -2), y=y)
        xs.append(xm)
        an.seq(xm.id, "scaleX", [(0, 0.0), (40 + i * 4, 0.0, "back"), (50 + i * 4, 1.0)])
        an.seq(xm.id, "scaleY", [(0, 0.0), (40 + i * 4, 0.0, "back"), (50 + i * 4, 1.0)])
    seam_trim = el("TrimPath", start=0, end=0, name="Sew")
    zig = [(195 + (6 if i % 2 else -6), 520 - 108 + i * 12) for i in range(19)]
    seam = shape("S6 seam", el("PointsPath", *[el("StraightVertex", x=x, y=y) for x, y in zig], isClosed=False, name="Path"),
                 el("Stroke", solid(TER), seam_trim, thickness=2.2, cap="round", join="round", name="Thread"))
    an.tween(seam_trim.id, "end", 38, 0.0, 84, 1.0, "inout")
    # darning circle holding the numeral
    weave = []
    wtrim = el("TrimPath", start=0, end=0, modeValue="synchronized", name="Weave")
    lines = []
    for i in range(-3, 4):
        d = i * 20
        hlen = math.sqrt(max(0, 84 ** 2 - d ** 2))
        lines.append(el("PointsPath", el("StraightVertex", x=-hlen, y=d), el("StraightVertex", x=hlen, y=d), isClosed=False, name=f"H{i}"))
        lines.append(el("PointsPath", el("StraightVertex", x=d, y=-hlen), el("StraightVertex", x=d, y=hlen), isClosed=False, name=f"V{i}"))
    weave = shape("Darning", *lines, el("Stroke", solid(a(TER, 0.25)), wtrim, thickness=6, cap="round", name="Weave"))
    an.tween(wtrim.id, "end", 8, 0.0, 56, 1.0, "out")
    num = hero_num("S6 repairs", "repairItems", 0, -14, 150, 78, IND)
    unit = text("S6 unit", 0, 44, 140, 14, "atkb", IND, prop="screen6Unit", oy=0.5, h=34, overflow="fitFontSize", wrap=True, lh=16)
    darn = node("S6 darning patch", num.el, unit.el, weave,
                shape("Ring stitch", ellipse(178, 178), stroke(a(TER, 0.8), 1.5, dash=(6, 4))),
                shape("Disc", ellipse(196, 196), fill(CREAM)), shape("Disc shade", ellipse(196, 196), fill(SHADOW), x=3, y=5),
                x=195, y=290)
    an.seq(darn.id, "scaleX", [(0, 0.0), (4, 0.0, "cloth"), (34, 1.0)])
    an.seq(darn.id, "scaleY", [(0, 0.0), (4, 0.0, "cloth"), (34, 1.0)])
    an.tween(unit.el.id, "opacity", 50, 0.0, 70, 1.0, "out")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen6Headline", "screen6Support", hy=104, sy=680)
    sway(L.id, "rotation", 0.0, -0.015)
    sway(R.id, "rotation", 0.0, 0.015)
    sc.root.add(th.el, darn, *xs, seam, R, L, ts.el, quilt_lines(a(OAT, 0.35)), bg(ROSE))
    return sc


# =====================================================================
# Scene 7 — Welcome sessions (two cloth arches open into a doorway)
# =====================================================================
def build_s7():
    sc = Scene(7, "Welcome", frames=116, dark=True)
    an = sc.new_anim()
    dx, dy, dw, dh = 195, 470, 176, 270
    light = shape("Doorway light", rect(dw, dh, linkCornerRadius=False, cornerRadiusTL=dw / 2, cornerRadiusTR=dw / 2),
                  el("Fill", el("LinearGradient", el("GradientStop", colorValue=CREAM, position=0),
                                el("GradientStop", colorValue=ROSE_L, position=1), startX=0, startY=-dh / 2, endX=0, endY=dh / 2,
                                name="Glow"), name="Fill"), x=dx, y=dy)
    rays = shape("Light spill", el("PointsPath", el("StraightVertex", x=-dw / 2, y=dh / 2), el("StraightVertex", x=dw / 2, y=dh / 2),
                                    el("StraightVertex", x=dw / 2 + 120, y=dh / 2 + 150), el("StraightVertex", x=-dw / 2 - 120, y=dh / 2 + 150),
                                    isClosed=True, name="Path"), fill(a(ROSE_L, 0.35)), x=dx, y=dy)
    an.tween(rays.id, "opacity", 20, 0.0, 60, 1.0, "out")
    an.tween(light.id, "opacity", 10, 0.3, 40, 1.0, "out")
    sway(rays.id, "scaleX", 1.0, 0.05)
    frame = shape("Arch frame", rect(dw + 28, dh + 14, linkCornerRadius=False, cornerRadiusTL=(dw + 28) / 2, cornerRadiusTR=(dw + 28) / 2),
                  fill(TER_D), stroke(a(OAT, 0.7), 1.4, dash=(6, 4)), x=dx, y=dy - 7)
    num = hero_num("S7 welcome", "welcomeSessions", dx, dy - 30, 150, 110, IND)
    unit = text("S7 unit", dx, dy + 46, 150, 15, "atkb", IND, prop="screen7Unit", wrap=True)
    doors = []
    for side, col in ((-1, TEAL), (1, ROSE)):
        hw = dw / 2
        shp = shape("Door cloth", rect(hw, dh, ox=0 if side > 0 else 1, oy=0.5, linkCornerRadius=False,
                                       cornerRadiusTL=(hw if side > 0 else 0), cornerRadiusTR=(0 if side > 0 else hw)),
                    fill(col), x=0)
        stc = shape("Door stitch", rect(hw - 14, dh - 14, ox=0 if side > 0 else 1, oy=0.5, linkCornerRadius=False,
                                        cornerRadiusTL=((hw - 14) if side > 0 else 0), cornerRadiusTR=(0 if side > 0 else (hw - 14))),
                    stroke(a(OAT, 0.85), 1.3, dash=(5, 4)), x=-7 * side * -1)
        mot = node("Door motif", *(m_heart(30, OAT, stitch=False) if side < 0 else m_leaf(36, OAT)), x=side * -1 * -44 if False else (-44 if side < 0 else 44), y=-10)
        hinge_x = dx - hw if side < 0 else dx + hw
        # pivot on the outer edge: content extends inward
        inner = node("Door panel", mot, stc, shp)
        # for the left door the cloth sits right of the hinge, so mirror via geometry origin
        dnode = node(f"S7 door {'left' if side < 0 else 'right'}", inner, x=hinge_x, y=dy)
        if side < 0:
            shp.children[0].attrs["originX"] = 0
            shp.children[0].attrs["cornerRadiusTL"] = hw
            shp.children[0].attrs["cornerRadiusTR"] = 0
            stc.children[0].attrs["originX"] = 0
            stc.children[0].attrs["cornerRadiusTL"] = hw - 14
            stc.children[0].attrs["cornerRadiusTR"] = 0
            stc.attrs["x"] = 7
            mot.attrs["x"] = 44
        else:
            shp.children[0].attrs["originX"] = 1
            shp.children[0].attrs["cornerRadiusTL"] = 0
            shp.children[0].attrs["cornerRadiusTR"] = hw
            stc.children[0].attrs["originX"] = 1
            stc.children[0].attrs["cornerRadiusTL"] = 0
            stc.children[0].attrs["cornerRadiusTR"] = hw - 14
            stc.attrs["x"] = -7
            mot.attrs["x"] = -44
        doors.append(dnode)
        f0 = 16 if side < 0 else 20
        an.seq(dnode.id, "scaleX", [(0, 1.0), (6, 1.04, "antic"), (f0, 1.03, "out"), (f0 + 36, 0.2)])
        an.seq(inner.id, "scaleY", [(0, 1.0), (f0, 1.0, "out"), (f0 + 36, 1.04)])
    people = []
    for i, (x, col, d) in enumerate([(88, ROSE, -1), (300, TEAL_L, 1), (332, MUST, 1)]):
        pn = node(f"S7 neighbour {i}", shape("Head", ellipse(20, 20), fill(col), y=-34),
                  shape("Body", rect(30, 44, r=14), fill(col)), x=x, y=dy + dh / 2 - 22)
        people.append(pn)
        an.seq(pn.id, "x", [(0, x + d * 140), (50 + i * 8, x + d * 140, "out"), (84 + i * 8, x)])
        an.seq(pn.id, "y", [(0, dy + dh / 2 - 22), (60 + i * 8, dy + dh / 2 - 22, "inout"), (66 + i * 8, dy + dh / 2 - 30, "inout"),
                            (72 + i * 8, dy + dh / 2 - 22, "inout"), (78 + i * 8, dy + dh / 2 - 28, "inout"), (84 + i * 8, dy + dh / 2 - 22)])
    mat = shape("S7 mat", rect(150, 16, r=4), fill(TER), stroke(a(OAT, 0.8), 1.2, dash=(5, 4)), x=dx, y=dy + dh / 2 + 8)
    an.seq(mat.id, "scaleX", [(0, 0.0), (40, 0.0, "cloth"), (64, 1.0)])
    stars = [shape(f"Star {i}", el("Star", width=s, height=s, points=4, innerRadius=0.35, name="Path"), fill(a(OAT, 0.75)), x=x, y=y)
             for i, (x, y, s) in enumerate([(52, 250, 12), (338, 230, 10), (300, 320, 8), (70, 380, 9), (360, 410, 7)])]
    for i, s in enumerate(stars):
        sway(s.id, "opacity", 0.4 + 0.1 * (i % 3), 0.5)
    an.tween(unit.el.id, "opacity", 50, 0.0, 70, 1.0, "out")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen7Headline", "screen7Support", hy=104, sy=694, dark=True)
    floor = shape("S7 floor", rect(W + 80, 140, ox=0, oy=0), fill(IND_D), x=-40, y=dy + dh / 2)
    sc.root.add(th.el, *people, mat, *doors, num.el, unit.el, light, frame, rays, ts.el, floor, *stars,
                quilt_lines(a(IND_L, 0.35)), bg(IND))
    return sc


# =====================================================================
# Scene 8 — Active months (one thread loops through ten seasonal patches)
# =====================================================================
S8_POS = [(52, 470), (118, 432), (186, 458), (254, 428), (322, 462), (68, 560), (136, 590), (204, 560), (272, 594), (338, 560)]
S8_COLS = [IND, IND_L, ROSE, TEAL, MUST, TER, TER_D, ROSE_D, TEAL_D, IND]
S8_MOT = [lambda: m_snow(34, OAT), lambda: m_snow(30, ROSE_L), lambda: m_flower(34, OAT, centre=TER),
          lambda: m_leaf(36, OAT), lambda: m_sun(36, TER, ray=OAT), lambda: m_sun(34, MUST, ray=OAT),
          lambda: m_leaf(34, MUST), lambda: m_heart(30, OAT, stitch=False), lambda: m_tree(32, TEAL_L, trunk=OAT),
          lambda: m_snow(32, OAT)]


def build_s8():
    sc = Scene(8, "Months", frames=114)
    an = sc.new_anim()
    pts = []
    patches = []
    for i, ((x, y), col) in enumerate(zip(S8_POS, S8_COLS)):
        outer, body = patch(f"S8 month {i}", 58, 58, col, motif=S8_MOT[i](), x=x, y=y, rot=((i * 13) % 5 - 2) * 0.05)
        patches.append(outer)
        f0 = 16 + i * 5
        an.seq(outer.id, "scaleX", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 22, 1.0)])
        an.seq(outer.id, "scaleY", [(0, 0.0), (f0, 0.0, "cloth"), (f0 + 22, 1.0)])
        an.seq(outer.id, "rotation", [(0, 0.9), (f0, 0.9, "back"), (f0 + 26, ((i * 13) % 5 - 2) * 0.05)])
        sway(body.id, "y", -2 if i % 2 else 2, 4 if i % 2 else -4)
    # the single thread: loop over/under every patch
    order = [5, 0, 1, 6, 7, 2, 3, 8, 9, 4]
    verts = [(-20, 520, 0.0, 30)]
    for k, idx in enumerate(order):
        x, y = S8_POS[idx]
        verts.append((x, y + (14 if k % 2 else -14), 0.2 if k % 2 else -0.2, 30))
    verts.append((420, 500, 0.0, 30))
    trim = el("TrimPath", start=0, end=0, name="Thread through")
    dash = el("DashPath", el("Dash", length=8, name="on"), el("Dash", length=6, name="off"), name="Running stitch")
    thread = shape("S8 thread", curve_path(verts), el("Stroke", solid(TER), dash, trim, thickness=2.6, cap="round", name="Thread"))
    an.tween(trim.id, "end", 10, 0.0, 92, 1.0, "inout")
    AMB_FLOW.tween(dash.id, 690, 0, 0.0, 240, 14.0 * 6, "linear")
    REST_SWAY.key(dash.id, 690, 0, 0.0)
    num = hero_num("S8 months", "activeMonths", 195, 262, 240, 130, IND)
    unit = text("S8 unit", 195, 332, 240, 17, "atkb", TER_D, prop="screen8Unit", wrap=True)
    an.tween(unit.el.id, "opacity", 50, 0.0, 70, 1.0, "out")
    an.seq(num.el.id, "scaleX", [(0, 0.9, "antic"), (10, 0.86, "cloth"), (36, 1.0)])
    an.seq(num.el.id, "scaleY", [(0, 0.9, "antic"), (10, 0.86, "cloth"), (36, 1.0)])
    an.tween(num.el.id, "opacity", 0, 0.0, 10, 1.0, "linear")
    count_keys(an)
    th, ts = scene_text_block(sc, an, "screen8Headline", "screen8Support", hy=104, sy=672)
    sc.thread_verts = verts
    sc.root.add(th.el, num.el, unit.el, thread, *patches, ts.el, quilt_lines(a(OAT_DD, 0.35)), bg(OAT))
    return sc


# =====================================================================
# Persona emblems (built twice: scene 9 hero, and the summary card copy)
# =====================================================================
def emblem_weaver(p):
    parts = {}
    diamonds = []
    cols = [TER, ROSE, OAT, TEAL, TER, ROSE, OAT, TEAL]
    for i in range(8):
        d = el("PointsPath", el("StraightVertex", x=0, y=0), el("StraightVertex", x=22, y=-40),
               el("StraightVertex", x=0, y=-96), el("StraightVertex", x=-22, y=-40), isClosed=True, name="Path")
        st = el("PointsPath", el("StraightVertex", x=0, y=-12), el("StraightVertex", x=14, y=-42),
                el("StraightVertex", x=0, y=-82), el("StraightVertex", x=-14, y=-42), isClosed=True, name="Path")
        dn = node(f"{p} diamond {i}", shape("Stitch", st, stroke(a(IND, 0.5) if cols[i] == OAT else a(OAT, 0.8), 1.2, dash=(4, 3))),
                  shape("Cloth", d, fill(cols[i])), rotation=i * math.pi / 4)
        diamonds.append(dn)
    weave = node(f"{p} weave", shape("Band A", ellipse(212, 212), stroke(MUST, 7, dash=(30, 14))),
                 shape("Band B", ellipse(212, 212), stroke(a(OAT, 0.9), 7, dash=(14, 30))))
    star = node(f"{p} star", *diamonds)
    centre = node(f"{p} centre", *m_heart(34, TER, stitch=False), shape("Hub", ellipse(40, 40), fill(OAT)))
    root = node(f"{p} Weaver", centre, star, weave)
    parts.update(diamonds=diamonds, weave=weave, star=star, centre=centre)
    return root, parts


def emblem_helper(p):
    rings = [node(f"{p} ring {i}", shape("Ring", ellipse(r, r), stroke(a(ROSE, 0.55 - i * 0.12), 8 - i * 2, dash=(10, 6))))
             for i, r in enumerate((120, 170, 220))]
    heart = node(f"{p} heart", *m_heart(96, ROSE, stitch=True))
    hands = node(f"{p} hands", shape("Palm L", rect(46, 22, r=11), fill(OAT), x=-34, y=58, rotation=-0.35),
                 shape("Palm R", rect(46, 22, r=11), fill(OAT), x=34, y=58, rotation=0.35))
    root = node(f"{p} Helper", heart, hands, *rings)
    return root, dict(rings=rings, heart=heart, hands=hands)


def emblem_builder(p):
    hammer = node(f"{p} hammer", shape("Head", rect(70, 24, r=5), fill(OAT_D), stroke(a(IND, 0.5), 1.2, dash=(4, 3)), y=-58),
                  shape("Handle", rect(16, 120, r=6), fill(TER), stroke(a(OAT, 0.8), 1.2, dash=(4, 3))), rotation=-0.6)
    wrench = node(f"{p} wrench", shape("Jaw", ellipse(48, 48), stroke(OAT, 12), y=-62),
                  shape("Shaft", rect(16, 120, r=6), fill(OAT), stroke(a(IND, 0.5), 1.2, dash=(4, 3))), rotation=0.6)
    needle_n = node(f"{p} needle", needle("Needle", scale=1.4), rotation=0.0)
    knot = node(f"{p} knot", shape("Binding", ellipse(64, 64), stroke(MUST, 6, dash=(9, 5))))
    root = node(f"{p} Builder", knot, needle_n, wrench, hammer, scaleX=1.3, scaleY=1.3)
    return root, dict(hammer=hammer, wrench=wrench, needle=needle_n, knot=knot)


def emblem_welcomer(p):
    glow = shape("Glow", rect(96, 140, linkCornerRadius=False, cornerRadiusTL=48, cornerRadiusTR=48), fill(CREAM), y=4)
    door = node(f"{p} door", shape("Leaf", rect(96, 140, ox=0, linkCornerRadius=False, cornerRadiusTL=48), fill(TEAL),
                                   stroke(a(OAT, 0.85), 1.2, dash=(4, 3))), x=-48, y=4)
    arch = node(f"{p} arch", shape("Arch", rect(130, 170, linkCornerRadius=False, cornerRadiusTL=65, cornerRadiusTR=65),
                                   fill(TER), stroke(a(OAT, 0.8), 1.4, dash=(6, 4))), y=0)
    folks = [node(f"{p} guest {i}", shape("Head", ellipse(16, 16), fill(c), y=-26), shape("Body", rect(24, 34, r=11), fill(c)), x=x, y=78)
             for i, (x, c) in enumerate([(-88, ROSE), (88, MUST), (-62, OAT)])]
    root = node(f"{p} Welcomer", door, glow, *folks, arch)
    return root, dict(door=door, arch=arch, folks=folks, glow=glow)


EMBLEMS = [emblem_weaver, emblem_helper, emblem_builder, emblem_welcomer]


# =====================================================================
# Scene 9 — Persona reveal (four distinct choreographies)
# =====================================================================
def build_s9():
    sc = Scene(9, "Persona", frames=134)
    anims = [sc.new_anim(f"_p{k}") for k in range(4)]
    ecx, ecy = 195, 500
    disc = node("S9 disc", shape("Accent ring", ellipse(300, 300), el("Stroke", el("SolidColor", bind(vm, "personaColor", 37), colorValue=TER, name="Accent"),
                                                                       thickness=6, name="Accent")),
                shape("Stitch ring", ellipse(276, 276), stroke(a(OAT, 0.7), 1.5, dash=(6, 4))),
                shape("Disc", ellipse(290, 290), fill(IND)), x=ecx, y=ecy)
    roots, parts = [], []
    for k, fnc in enumerate(EMBLEMS):
        r, pp = fnc(f"S9 P{k}")
        roots.append(r)
        parts.append(pp)
    esolo = el("Solo", *roots, activeComponentId=roots[0].id, name="S9 emblem solo", x=ecx, y=ecy)
    sc.esolo = esolo
    sc.eroots = roots
    # anticipation: ten patches carried over from scene 8 converge into the disc
    carry = []
    for i, ((x, y), col) in enumerate(zip(S8_POS, S8_COLS)):
        cp, _ = patch(f"S9 carry {i}", 58, 58, col, motif=S8_MOT[i](), x=x, y=y, rot=((i * 13) % 5 - 2) * 0.05)
        carry.append(cp)
    lbl = text("S9 label", 195, 112, 320, 15, "atkb", TER_D, prop="personaLabel", reveal=True, ls=0.6)
    name = text("S9 title", 195, 136, 350, 40, "bree", IND, prop="personaName", reveal=True, lh=42, rise=24, h=92,
                overflow="fitFontSize")
    desc = text("S9 description", 195, 238, 320, 19, "atk", IND_D, prop="personaDescription", reveal=True, lh=24, h=52,
                overflow="fitFontSize")
    thr = shape("S9 thread echo", curve_path(SCENES[8].thread_verts), stroke(TER, 2.6, dash=(8, 6)))
    for k, an in enumerate(anims):
        an.tween(thr.id, "opacity", 0, 1.0, 14, 0.0, "out")
        for i, cp in enumerate(carry):
            x, y = S8_POS[i]
            ang = i * 2 * math.pi / 10 + k * 0.4
            rx, ry = ecx + math.cos(ang) * 96, ecy + math.sin(ang) * 96
            d = i * 1.2
            an.seq(cp.id, "x", [(0, x), (4 + d, x, "antic"), (30 + d, rx, "inout"), (46, ecx)])
            an.seq(cp.id, "y", [(0, y), (4 + d, y, "antic"), (30 + d, ry, "inout"), (46, ecy)])
            an.seq(cp.id, "rotation", [(0, ((i * 13) % 5 - 2) * 0.05), (30 + d, ang, "in"), (46, ang + 2.0)])
            an.seq(cp.id, "scaleX", [(0, 1.0), (30 + d, 0.8, "in"), (48, 0.1)])
            an.seq(cp.id, "scaleY", [(0, 1.0), (30 + d, 0.8, "in"), (48, 0.1)])
            an.seq(cp.id, "opacity", [(0, 1.0), (44, 1.0, "linear"), (50, 0.0)])
        an.seq(disc.id, "scaleX", [(0, 0.0), (20, 0.0, "cloth"), (50, 1.0)])
        an.seq(disc.id, "scaleY", [(0, 0.0), (20, 0.0, "cloth"), (50, 1.0)])
        reveal_keys(an, lbl, 56, 80)
        reveal_keys(an, name, 70, 108, "cloth")
        reveal_keys(an, desc, 92, 126)
        an.key(HERO_CP.id, "propertyValue", 0, 1.0)
    # --- persona-specific choreographies
    a0, a1, a2, a3 = anims
    p = parts[0]  # Weaver: diamonds spin out of the hub and weave closes
    for i, dmd in enumerate(p["diamonds"]):
        f0 = 46 + i * 3
        a0.seq(dmd.id, "scaleY", [(0, 0.0), (f0, 0.0, "back"), (f0 + 20, 1.0)])
        a0.seq(dmd.id, "scaleX", [(0, 0.2), (f0, 0.2, "cloth"), (f0 + 24, 1.0)])
    a0.seq(p["star"].id, "rotation", [(0, -1.2), (46, -1.2, "cloth"), (96, 0.0)])
    a0.seq(p["weave"].id, "rotation", [(0, 1.5), (60, 1.5, "out"), (110, 0.0)])
    a0.seq(p["weave"].id, "opacity", [(0, 0.0), (60, 0.0, "linear"), (74, 1.0)])
    pop(a0, p["centre"].id, 84, 100, "back")
    p = parts[1]  # Helper: a tiny heart beats twice, rings ripple out
    a1.seq(p["heart"].id, "scaleX", [(0, 0.0), (48, 0.0, "out"), (60, 0.35, "inout"), (70, 0.3, "back"), (84, 1.12, "inout"),
                                     (92, 0.96, "inout"), (100, 1.06, "inout"), (110, 1.0)])
    a1.seq(p["heart"].id, "scaleY", [(0, 0.0), (48, 0.0, "out"), (60, 0.35, "inout"), (70, 0.3, "back"), (84, 1.12, "inout"),
                                     (92, 0.96, "inout"), (100, 1.06, "inout"), (110, 1.0)])
    for i, rg in enumerate(p["rings"]):
        f0 = 80 + i * 6
        a1.seq(rg.id, "scaleX", [(0, 0.3), (f0, 0.3, "out"), (f0 + 30, 1.0)])
        a1.seq(rg.id, "scaleY", [(0, 0.3), (f0, 0.3, "out"), (f0 + 30, 1.0)])
        a1.seq(rg.id, "opacity", [(0, 0.0), (f0, 0.0, "linear"), (f0 + 10, 1.0)])
    a1.seq(p["hands"].id, "y", [(0, 80), (56, 80, "cloth"), (84, 0)])
    a1.seq(p["hands"].id, "opacity", [(0, 0.0), (56, 0.0, "linear"), (66, 1.0)])
    p = parts[2]  # Builder: tools slide in from three sides and lock with a squash
    a2.seq(p["hammer"].id, "x", [(0, -220), (46, -220, "in"), (70, 0)])
    a2.seq(p["hammer"].id, "rotation", [(0, -2.2), (46, -2.2, "in"), (70, -0.6, "back"), (82, -0.6)])
    a2.seq(p["wrench"].id, "x", [(0, 220), (52, 220, "in"), (74, 0)])
    a2.seq(p["wrench"].id, "rotation", [(0, 2.2), (52, 2.2, "in"), (74, 0.6, "back"), (86, 0.6)])
    a2.seq(p["needle"].id, "y", [(0, -260), (58, -260, "in"), (78, 0)])
    a2.seq(p["knot"].id, "scaleX", [(0, 1.0), (74, 1.0, "out"), (78, 1.3, "cloth"), (96, 1.0)])
    a2.seq(p["knot"].id, "scaleY", [(0, 1.0), (74, 1.0, "out"), (78, 0.7, "cloth"), (96, 1.0)])
    a2.seq(p["knot"].id, "opacity", [(0, 0.0), (72, 0.0, "linear"), (78, 1.0)])
    p = parts[3]  # Welcomer: the arch rises, the door swings open, guests arrive
    a3.seq(p["arch"].id, "scaleY", [(0, 0.0), (44, 0.0, "cloth"), (70, 1.0)])
    a3.seq(p["arch"].id, "y", [(0, 85), (44, 85, "cloth"), (70, 0)])
    a3.seq(p["door"].id, "scaleX", [(0, 1.0), (66, 1.0, "inout"), (96, 0.18)])
    a3.seq(p["glow"].id, "opacity", [(0, 0.0), (66, 0.0, "out"), (90, 1.0)])
    for i, f in enumerate(p["folks"]):
        a3.seq(f.id, "y", [(0, 160), (78 + i * 6, 160, "back"), (98 + i * 6, 78)])
        a3.seq(f.id, "opacity", [(0, 0.0), (78 + i * 6, 0.0, "linear"), (86 + i * 6, 1.0)])
    sc.root.add(lbl.el, name.el, desc.el, *carry, esolo, disc, thr, bg(OAT))
    return sc


# =====================================================================
# Scene 10 — Summary and share card
# =====================================================================
def build_s10():
    sc = Scene(10, "Summary", frames=120, dark=True)
    an = sc.new_anim()
    card_x, card_y, cw, ch = 195, 418, 336, 540
    top = card_y - ch / 2
    # card frame
    border_trim = el("TrimPath", start=0, end=0, name="Sew border")
    border = shape("Card border", rect(cw - 18, ch - 18, r=12), el("Stroke", solid(TER), el("DashPath", el("Dash", length=7, name="on"),
                                                                                         el("Dash", length=5, name="off"), name="d"),
                                                                  border_trim, thickness=1.8, cap="round", name="Running stitch"))
    an.tween(border_trim.id, "end", 8, 0.0, 70, 1.0, "inout")
    cloth = shape("Card cloth", rect(cw, ch, r=18), fill(CREAM))
    shade = shape("Card shade", rect(cw, ch, r=18), fill(a(IND_D, 0.6)), x=4, y=8)
    # header row inside card
    logo = logo_mark("Card logo", 12)
    logo.attrs.update(x=-cw / 2 + 34, y=-ch / 2 + 40)
    wm = text("Card wordmark", -cw / 2 + 52, -ch / 2 + 40, 160, 22, "bree", IND, lit="Patchwork", align="left", oy=0.5, wrap=False)
    yr = text("Card year", cw / 2 - 28, -ch / 2 + 40, 90, 15, "atkb", TER_D, prop="year", conv=TO_STR0, align="right", oy=0.5,
              wrap=False)
    who = text("Card name", -cw / 2 + 28, -ch / 2 + 66, 236, 15, "atkb", TER_D, prop="userName", align="left", wrap=True,
               overflow="ellipsis", h=20)
    who.el.attrs["verticalAlignValue"] = "top"
    who_n = node("Card name gate", who.el)
    who_n.add(bind(vm, "shareIncludeName", 18, conv=C_BOOL_OPACITY))
    # persona block
    proots = []
    for k, fnc in enumerate(EMBLEMS):
        r, _ = fnc(f"Card P{k}")
        proots.append(r)
    psolo = el("Solo", *proots, activeComponentId=proots[0].id, name="Card emblem solo")
    pdisc = node("Card emblem", psolo, shape("Accent ring", ellipse(300, 300),
                                              el("Stroke", el("SolidColor", bind(vm, "personaColor", 37), colorValue=TER, name="Accent"),
                                                 thickness=6, name="Accent")),
                 shape("Disc", ellipse(290, 290), fill(IND)), x=-cw / 2 + 64, y=-ch / 2 + 136, scaleX=0.3, scaleY=0.3)
    plabel = text("Card persona label", -cw / 2 + 118, -ch / 2 + 104, 196, 12, "atkb", TER_D, prop="personaLabel", align="left")
    pname = text("Card persona", -cw / 2 + 118, -ch / 2 + 122, 196, 21, "bree", IND, prop="personaName", align="left", lh=23,
                 h=48, overflow="fitFontSize")
    pname.el.attrs["verticalAlignValue"] = "top"
    persona = node("Card persona block", plabel.el, pname.el)
    persona_gate_in = node("Persona activity gate", persona, pdisc)
    persona_gate_in.add(bind(vm, "_noActivity", 18, conv=G_NOT_OPACITY))
    persona_gate = node("Persona gate", persona_gate_in)
    persona_gate.add(bind(vm, "showScreen9", 18, conv=C_BOOL_OPACITY))
    # five stat patches
    stats = []
    layout = [(2, -78, 0, 150, 96, TER), (3, 78, 0, 150, 96, TEAL), (4, -78, 104, 150, 96, IND), (5, 78, 104, 150, 96, ROSE_D),
              (6, 0, 208, 306, 84, MUST)]
    for (n, sx, sy, w, h, col) in layout:
        ink = OAT if col in (TER, TEAL, IND) else IND
        num = hero_num(f"Card {STAT[n]}", STAT[n], 0, -12 if h > 90 else -10, w - 20, 40, ink, stitch=None)
        un = text(f"Card {n} unit", 0, 24 if h > 90 else 20, w - 20, 12, "atkb", ink, prop=f"screen{n}Unit", oy=0.5, h=30,
                  overflow="fitFontSize", wrap=True)
        outer, body = patch(f"Card stat {n}", w, h, col, inner=[num.el, un.el], x=sx, y=sy + 20, shadow=False)
        stats.append(outer)
        f0 = 30 + len(stats) * 6
        an.seq(outer.id, "y", [(0, sy + 300), (f0, sy + 300, "cloth"), (f0 + 26, sy + 20)])
        an.seq(outer.id, "rotation", [(0, 0.5 * (1 if n % 2 else -1)), (f0, 0.5 * (1 if n % 2 else -1), "back"), (f0 + 30, 0.0)])
        an.seq(outer.id, "opacity", [(0, 0.0), (f0, 0.0, "linear"), (f0 + 6, 1.0)])
    stat_grid = node("Card stats", *stats, y=-20)
    stat_grid.add(bind(vm, "_noActivity", 18, conv=G_NOT_OPACITY))
    # empty-state block (no eligible stats)
    e_mot = node("Empty motif", *[patch(f"Empty patch {i}", 44, 44, c, x=(i % 2 - 0.5) * 48, y=(i // 2 - 0.5) * 48)[0]
                                  for i, c in enumerate([TER, ROSE, TEAL, IND])], y=-60)
    e_sup = text("Empty support", 0, 30, 260, 20, "bree", IND, prop="emptySupport", lh=25)
    empty = node("Card empty state", e_mot, e_sup.el, y=60)
    empty.add(bind(vm, "_noActivity", 18, conv=C_BOOL_OPACITY))
    # bottom quilt strip
    strip = node("Card strip", *[shape(f"Strip {i}", rect(34, 18, r=3), fill(c), x=-cw / 2 + 36 + i * 38, y=ch / 2 - 30)
                                 for i, c in enumerate([TER, ROSE, TEAL, IND, MUST, ROSE_D, TEAL_L, TER_D])])
    # thanks flap on the card (signature interaction, summary instance)
    thanks = text("Card thanks", cw / 2 - 22, -ch / 2 + 72, 40, 7.5, "atkb", IND, prop="thanksLabel", align="center", oy=0.5)
    thanks.el.attrs["rotation"] = 0.785398
    flap = node("Card flap hinge", shape("Flap", el("PointsPath", el("StraightVertex", x=0, y=-28), el("StraightVertex", x=28, y=0),
                                                     el("StraightVertex", x=0, y=28), isClosed=True, name="Path"),
                                         fill(ROSE), stroke(a(OAT, 0.9), 1.2, dash=(4, 3))),
                x=cw / 2 - 28, y=-ch / 2 + 76, rotation=-0.785398)
    corner = shape("Card corner patch", rect(64, 64, r=6), fill(ROSE_L), stroke(a(TER, 0.6), 1.2, dash=(4, 3)),
                   x=cw / 2 - 40, y=-ch / 2 + 88)
    sc.flap = flap
    card = node("S10 share card", flap, thanks.el, corner, logo, wm.el, yr.el, who_n, persona_gate, stat_grid, empty, strip, border,
                cloth, shade, x=card_x, y=card_y)
    an.seq(card.id, "scaleX", [(0, 0.9), (6, 0.9, "cloth"), (40, 1.0)])
    an.seq(card.id, "scaleY", [(0, 0.9), (6, 0.9, "cloth"), (40, 1.0)])
    an.seq(card.id, "opacity", [(0, 1.0)])
    # continuity: the persona emblem arrives from scene 9's disc position
    an.seq(pdisc.id, "x", [(0, 195 - card_x), (12, 195 - card_x, "inout"), (52, -cw / 2 + 64)])
    an.seq(pdisc.id, "y", [(0, 500 - card_y), (12, 500 - card_y, "inout"), (52, -ch / 2 + 136)])
    an.seq(pdisc.id, "scaleX", [(0, 1.0), (12, 1.0, "inout"), (52, 0.3)])
    an.seq(pdisc.id, "scaleY", [(0, 1.0), (12, 1.0, "inout"), (52, 0.3)])
    an.tween(persona.id, "opacity", 50, 0.0, 70, 1.0, "out")
    an.tween(HERO_CP.id, "propertyValue", 40, 0.0, 96, 1.0, "thread")
    head = text("S10 headline", 195, 96, 340, 24, "bree", OAT, prop="summaryHeadline", reveal=True, lh=27)
    head_e = text("S10 empty headline", 195, 96, 340, 24, "bree", OAT, prop="emptyHeadline", reveal=True, lh=27)
    sup = text("S10 support", 195, 704, 330, 15, "atk", a(OAT, 0.92), prop="summarySupport", reveal=True)
    reveal_keys(an, head, 70, 100)
    reveal_keys(an, head_e, 70, 100)
    reveal_keys(an, sup, 84, 112)
    hg = node("Headline gate", head.el)
    hg.add(bind(vm, "_noActivity", 18, conv=G_NOT_OPACITY))
    hge = node("Empty headline gate", head_e.el)
    hge.add(bind(vm, "_noActivity", 18, conv=C_BOOL_OPACITY))
    sc.psolo = psolo
    sc.proots = proots
    sc.root.add(hg, hge, card, sup.el, quilt_lines(a(IND_L, 0.45), step=40), bg(IND))
    return sc


def logo_mark(name, s=9):
    g = s + 1.5
    return node(name, *[shape(f"{name} {i}", rect(s, s, r=1.5), fill(c), x=(i % 2 - 0.5) * g, y=(i // 2 - 0.5) * g,
                              rotation=(0.08 if i % 2 else -0.06))
                        for i, c in enumerate([TER, TEAL, ROSE, IND])])


# =====================================================================
# Build everything
# =====================================================================
for b in (build_s1, build_s2, build_s3, build_s4, build_s5, build_s6, build_s7, build_s8, build_s9, build_s10):
    b()

scene_nodes = [SCENES[n].root for n in range(1, 11)]
SCENE_SOLO = el("Solo", *scene_nodes, activeComponentId=scene_nodes[0].id, name="Scenes")

# ---------------------------------------------------------------- backdrop (the larger quilt seen on camera pull-back)
backdrop_kids = []
bcols = [IND_D, TER_D, TEAL_D, IND, ROSE_D, TEAL]
for r in range(-1, 11):
    for c in range(-1, 6):
        col = bcols[(r * 3 + c * 5) % len(bcols)]
        backdrop_kids.append(shape(f"Q{r}_{c}", rect(86, 86, r=3), fill(col), stroke(a(OAT, 0.35), 1.2, dash=(5, 4)),
                                   x=c * 90 + 15, y=r * 90 + 2))
BACKDROP = node("Backdrop quilt", *backdrop_kids)

WORLD_INNER = node("World content", SCENE_SOLO, x=-W / 2, y=-H / 2)
WORLD = node("World camera", WORLD_INNER, x=W / 2, y=H / 2)

# ---------------------------------------------------------------- handoff (signature transition)


def fold_panel(name, col, pivot_x, extend_dir, accent):
    """A full-screen fabric panel hinged on a vertical seam at pivot_x."""
    x0 = 0 if extend_dir > 0 else -W
    patches = []
    rng = [(0.2, 0.15, 70), (0.65, 0.3, 54), (0.35, 0.62, 80), (0.8, 0.8, 60), (0.15, 0.88, 48)]
    for i, (fx, fy, s) in enumerate(rng):
        patches.append(shape(f"Applique {i}", rect(s, s, r=4), fill(a(accent, 0.55)), stroke(a(OAT, 0.6), 1.2, dash=(5, 4)),
                             x=x0 + fx * W, y=fy * H, rotation=0.1 * (i - 2)))
    edge_x = x0 + (0 if extend_dir > 0 else 0)
    lead = W if extend_dir > 0 else -W  # x of the free (leading) edge
    trim = el("TrimPath", start=0, end=1, name="Stitch run")
    stitch = shape("Leading stitch", el("PointsPath", el("StraightVertex", x=lead - extend_dir * 14, y=-20),
                                         el("StraightVertex", x=lead - extend_dir * 14, y=H + 20), isClosed=False, name="Path"),
                   el("Stroke", solid(OAT), el("DashPath", el("Dash", length=9, name="on"), el("Dash", length=6, name="off"), name="d"),
                      trim, thickness=2.4, cap="round", name="Running stitch"))
    fold_shadow = shape("Fold shadow", rect(26, H + 40, ox=0.5, oy=0), el("Fill", el("LinearGradient",
                                                                                    el("GradientStop", colorValue=a(IND_D, 0.0), position=0),
                                                                                    el("GradientStop", colorValue=a(IND_D, 0.45), position=1),
                                                                                    startX=-13 * extend_dir, startY=0, endX=13 * extend_dir, endY=0,
                                                                                    name="Shade"), name="Fill"),
                        x=lead - extend_dir * 13, y=-20)
    cloth = shape("Panel cloth", rect(W + 4, H + 40, ox=0 if extend_dir > 0 else 1, oy=0), fill(col), y=-20)
    n = node(name, stitch, fold_shadow, *patches, cloth, x=pivot_x, y=0, scaleX=0)
    return n, trim


FOLD_FR, FOLD_FR_TRIM = fold_panel("Fold fwd cover", TER, W, -1, ROSE)
FOLD_FL, FOLD_FL_TRIM = fold_panel("Fold fwd reveal", TER, 0, 1, ROSE)
FOLD_BL, FOLD_BL_TRIM = fold_panel("Fold back cover", ROSE, 0, 1, TEAL)
FOLD_BR, FOLD_BR_TRIM = fold_panel("Fold back reveal", ROSE, W, -1, TEAL)
NEEDLE = needle("Guide needle", x=W + 40, y=-80, rot=math.pi, scale=1.0)
NEEDLE_THREAD = shape("Needle thread", el("PointsPath", el("StraightVertex", x=0, y=-46), el("StraightVertex", x=0, y=-140),
                                          isClosed=False, name="Path"), stroke(TER, 2.0, dash=(7, 5)))
NEEDLE_RIG = node("Needle rig", NEEDLE, NEEDLE_THREAD, x=W + 40, y=-80)
NEEDLE.attrs.update(x=0, y=0)
RM_VEIL = shape("Reduced-motion veil", rect(W, H, ox=0, oy=0), fill(OAT), opacity=0)
HANDOFF = node("Handoff", NEEDLE_RIG, FOLD_FR, FOLD_FL, FOLD_BL, FOLD_BR, RM_VEIL)

# ---------------------------------------------------------------- chrome: header, progress, controls
THEME = {}


def themed(key, light, dark):
    s = solid(light, name=key)
    THEME[key] = (s.id, light, dark)
    return s


hdr_logo = logo_mark("Header logo", 9)
hdr_logo.attrs.update(x=34, y=38)
wm_t = text("Header wordmark", 50, 38, 160, 21, "bree", IND, lit="Patchwork", align="left", oy=0.5, wrap=False)
wm_t.solid.attrs["name"] = "wordmark ink"
THEME["wordmark"] = (wm_t.solid.id, IND, OAT)
yr_t = text("Header year", 366, 38, 80, 13, "atkb", IND, prop="year", conv=TO_STR0, align="right", oy=0.5, wrap=False)
THEME["year"] = (yr_t.solid.id, IND, OAT)

segs = []
seg_track = []
seg_fill_ids = []
for k in range(1, 11):
    sid = new_id()
    fs = solid(IND)
    ts = solid(OAT_DD)
    seg_fill_ids.append(fs.id)
    seg_track.append(ts.id)
    segs.append(el("LayoutComponent",
                   el("LayoutComponentStyle", bind(vm, f"showScreen{k}", 596, conv=HIDE_IF_FALSE) if k not in (1, 10) else None,
                      layoutWidthScaleType="fill", layoutHeightScaleType="fixed", id=sid, name=f"Seg {k} style"),
                   shape(f"Seg {k} fill", rect(10, 4, ox=0, oy=0, r=2), el("Fill", fs, name="Fill"),
                         el("LayoutParticipant", layoutWidthScaleType="fill", layoutHeightScaleType="fill", name="Fill size"),
                         bind(vm, "currentScreen", 16, conv=seg_fill(k))),
                   el("Fill", ts, name="Track"), height=4, styleId=sid, name=f"Segment {k}"))
row_style = new_id()
PROGRESS = el("LayoutComponent", el("LayoutComponentStyle", layoutWidthScaleType="fixed", layoutHeightScaleType="fixed",
                                    flexDirectionValue="row", gapHorizontal=5, gapHorizontalUnitsValue="points", id=row_style,
                                    name="Progress style"),
              *segs, x=24, y=64, width=342, height=4, styleId=row_style, name="Progress segments")
for i, k in enumerate(range(1, 11)):
    THEME[f"segfill{k}"] = (seg_fill_ids[i], IND, OAT)
    THEME[f"segtrack{k}"] = (seg_track[i], OAT_DD, IND_L)

# buttons -------------------------------------------------------------
BTN_Y = 772
FOCUSABLE = []


def button(k, name, x, w, h, r, label_prop, content, fill_key, stroke_key=None, light=IND, dark=OAT, role_label=None):
    fs = themed(f"{name} fill", light, dark)
    ring_s = shape(f"{name} focus ring", rect(w + 12, h + 12, r=r + 6), stroke(TER_L, 3.0))
    ring_s.add(bind(vm, "_focusIndex", 18, conv=focus_ring(k)))
    body = shape(f"{name} body", rect(w, h, r=r), el("Fill", fs, name="Fill") if fill_key == "fill" else None,
                 el("Stroke", fs, thickness=1.6, name="Outline") if fill_key == "outline" else None,
                 el("FocusData", canTouch=False, name="Focus"),
                 el("SemanticData", bind(vm, label_prop, 983), role="button", label="", name="Semantics"))
    hit = shape(f"{name} hit", rect(max(w, 48), max(h, 48)), fill("00000000"))
    btn = node(name, *content, ring_s, body, hit, x=x, y=BTN_Y)
    btn.body = body
    btn.hit = hit
    FOCUSABLE.append((k, body))
    return btn


def label(name, prop, w, size=16, color_key=None, light=OAT, dark=IND):
    t = text(name, 0, 0, w, size, "atkb", light, prop=prop, oy=0.5, wrap=False, overflow="fitFontSize", h=24)
    if color_key:
        THEME[color_key] = (t.solid.id, light, dark)
    return t


def chevron(name, d, key, light=IND, dark=OAT):
    s = themed(key, light, dark)
    return shape(name, el("PointsPath", el("StraightVertex", x=3 * d, y=-7), el("StraightVertex", x=-3 * d, y=0),
                          el("StraightVertex", x=3 * d, y=7), isClosed=False, name="Path"),
                 el("Stroke", s, thickness=2.4, cap="round", join="round", name="Stroke"))


prev_btn = button(1, "Previous button", 44, 52, 52, 26, "previousLabel", [chevron("Prev chevron", 1, "prev icon")], "outline")
cont_lbl = label("Continue label", "continueLabel", 120, 16, "continue text")
cont_arrow_s = themed("continue arrow", OAT, IND)
cont_arrow = shape("Continue arrow", el("PointsPath", el("StraightVertex", x=-6, y=0), el("StraightVertex", x=6, y=0),
                                        el("StraightVertex", x=1, y=-5), el("StraightVertex", x=6, y=0), el("StraightVertex", x=1, y=5),
                                        isClosed=False, name="Path"), el("Stroke", cont_arrow_s, thickness=2.2, cap="round", join="round", name="S"),
                   x=64)
cont_lbl.el.attrs["x"] = -8
cont_btn = button(2, "Continue button", 195, 196, 52, 26, "continueLabel", [cont_lbl.el, cont_arrow], "fill", light=IND, dark=OAT)
share_lbl = label("Share label", "shareLabel", 90, 15, "share text")
share_btn = button(3, "Share button", 139, 118, 52, 26, "shareLabel", [share_lbl.el], "fill", light=IND, dark=OAT)
replay_lbl = label("Replay label", "replayLabel", 84, 15, "replay text", light=IND, dark=OAT)
replay_btn = button(4, "Replay button", 259, 106, 52, 26, "replayLabel", [replay_lbl.el], "outline", light=IND, dark=OAT)
pause_icon = themed("pause icon", IND, OAT)
play_icon = themed("play icon", IND, OAT)
PAUSE_GLYPH = shape("Pause glyph", el("Rectangle", width=4, height=16, x=-4, cornerRadiusTL=1.5, name="L"),
                    el("Rectangle", width=4, height=16, x=4, cornerRadiusTL=1.5, name="R"), el("Fill", pause_icon, name="F"))
PLAY_GLYPH = shape("Play glyph", el("Triangle", width=16, height=16, rotation=math.pi / 2, x=1, name="P"), el("Fill", play_icon, name="F"))
PAUSE_SOLO = el("Solo", PAUSE_GLYPH, PLAY_GLYPH, activeComponentId=PAUSE_GLYPH.id, name="Pause icon solo")
pause_btn = button(5, "Pause button", 346, 52, 52, 26, "pauseLabel", [PAUSE_SOLO], "outline")
pause_btn.body.children[-1].attrs["isToggleable"] = True
pause_btn.body.children[-1].add(bind(vm, "isPaused", 1000))

NAV_GROUP = node("Story controls", cont_btn)
SUM_GROUP = node("Summary controls", share_btn, replay_btn)
CTRL_SOLO = el("Solo", NAV_GROUP, SUM_GROUP, activeComponentId=NAV_GROUP.id, name="Control set")

# delight hits (above navigation, opaque so the story never advances from them)
DEL_NONE = node("No delight")
DEL_S1 = shape("Thanks hit S1", rect(82, 82), fill("00000000"), x=195 + 88, y=386 - 88, isTargetOpaque=True)
DEL_S10 = shape("Thanks hit S10", rect(70, 70), fill("00000000"), x=195 + 336 / 2 - 40, y=418 - 540 / 2 + 88, isTargetOpaque=True)
DEL_SOLO = el("Solo", DEL_NONE, DEL_S1, DEL_S10, activeComponentId=DEL_NONE.id, name="Delight hits")

NAV_TOP, NAV_BOTTOM = 92, 736
NAV_LEFT = shape("Tap back region", rect(130, NAV_BOTTOM - NAV_TOP, ox=0, oy=0), fill("00000000"), x=0, y=NAV_TOP)
NAV_RIGHT = shape("Tap forward region", rect(W - 130, NAV_BOTTOM - NAV_TOP, ox=0, oy=0), fill("00000000"), x=130, y=NAV_TOP)
SURFACE = shape("Release surface", rect(W, H, ox=0, oy=0), fill("00000000"))

CHROME = node("Chrome", hdr_logo, wm_t.el, yr_t.el, PROGRESS, prev_btn, CTRL_SOLO, pause_btn)
CHROME.add(bind(vm, "shareCaptureMode", 18, conv=G_CHROME))
APP = node("App", el("FocusData", canTouch=False, canTraverse=False, name="Keyboard host"),
           CHROME, DEL_SOLO, NAV_LEFT, NAV_RIGHT, HANDOFF, HERO_DRIVER, WORLD, BACKDROP, SURFACE)

# =====================================================================
# Animations
# =====================================================================
EV_SCREEN = [el("Event", el("CustomPropertyNumber", propertyValue=n, name="index"), name="screenChanged") for n in range(1, 11)]
EV_SHARE = el("Event", name="shareTapped")
EV_FINISH = el("Event", name="recapFinished")


def finalize_scene_anim(sc, an):
    n = sc.n
    an.key(SCENE_SOLO.id, "activeComponentId", 0, sc.root.id, kind="Id")
    an.key(CTRL_SOLO.id, "activeComponentId", 0, (SUM_GROUP if n == 10 else NAV_GROUP).id, kind="Id")
    an.key(DEL_SOLO.id, "activeComponentId", 0, {1: DEL_S1, 10: DEL_S10}.get(n, DEL_NONE).id, kind="Id")
    an.key(prev_btn.id, "opacity", 0, 0.35 if n == 1 else 1.0)
    for key, (sid, light, dark) in THEME.items():
        an.key(sid, "colorValue", 0, dark if sc.dark else light, kind="Color")
    an.key(sc.root.id, "opacity", 0, 1.0)


def rm_anim(sc, an):
    """Reduced motion: final values immediately, then a short opacity fade."""
    rm = Anim(an.name.replace("enter", "reduced"), 14)
    for (o, p) in an.order:
        frames = an.keys[(o, p)]
        last = max(frames, key=lambda f: f[0])
        rm.key(o, p, 0, last[1], kind=last[2])
    rm.keys[(sc.root.id, "opacity")] = []
    rm.tween(sc.root.id, "opacity", 0, 0.0, 12, 1.0, "linear")
    return rm


ENTER = {}
REDUCED = {}
for n in range(1, 11):
    sc = SCENES[n]
    ENTER[n] = []
    REDUCED[n] = []
    for an in sc.anims:
        finalize_scene_anim(sc, an)
        ENTER[n].append(an)
        REDUCED[n].append(rm_anim(sc, an))

REST = Anim("rest", 1)

# handoff animations ------------------------------------------------
COVER_F = 18
REVEAL_F = 26


def handoff_cover(name, panel, trim, from_x_edge, dir_):
    an = Anim(name, COVER_F)
    for pnl in (FOLD_FR, FOLD_FL, FOLD_BL, FOLD_BR):
        if pnl is not panel:
            an.key(pnl.id, "scaleX", 0, 0.0)
    an.seq(panel.id, "scaleX", [(0, 0.0, (0.55, 0.0, 0.25, 1.0)), (COVER_F, 1.0)])
    an.seq(trim.id, "end", [(0, 0.0, "inout"), (COVER_F, 1.0)])
    # the guide needle runs down the leading edge as the fold travels
    lead0 = W + 30 if dir_ > 0 else -30
    lead1 = 30 if dir_ > 0 else W - 30
    an.seq(NEEDLE_RIG.id, "x", [(0, lead0, (0.55, 0.0, 0.25, 1.0)), (COVER_F, lead1)])
    an.seq(NEEDLE_RIG.id, "y", [(0, -60, "inout"), (COVER_F, H + 120)])
    an.seq(NEEDLE_RIG.id, "rotation", [(0, math.pi - 0.25 * dir_), (COVER_F, math.pi + 0.1 * dir_)])
    an.seq(WORLD.id, "scaleX", [(0, 1.0, "inout"), (COVER_F, 0.86)])
    an.seq(WORLD.id, "scaleY", [(0, 1.0, "inout"), (COVER_F, 0.86)])
    an.key(RM_VEIL.id, "opacity", 0, 0.0)
    return an


def handoff_reveal(name, panel, dir_):
    an = Anim(name, REVEAL_F)
    for pnl in (FOLD_FR, FOLD_FL, FOLD_BL, FOLD_BR):
        if pnl is not panel:
            an.key(pnl.id, "scaleX", 0, 0.0)
    an.seq(panel.id, "scaleX", [(0, 1.0, (0.6, 0.0, 0.2, 1.0)), (REVEAL_F, 0.0)])
    an.seq(WORLD.id, "scaleX", [(0, 0.86, (0.3, 0.0, 0.2, 1.0)), (REVEAL_F, 1.0)])
    an.seq(WORLD.id, "scaleY", [(0, 0.86, (0.3, 0.0, 0.2, 1.0)), (REVEAL_F, 1.0)])
    an.key(NEEDLE_RIG.id, "y", 0, H + 160)
    an.key(RM_VEIL.id, "opacity", 0, 0.0)
    return an


A_COVER_F = handoff_cover("handoff_cover_forward", FOLD_FR, FOLD_FR_TRIM, W, 1)
A_REVEAL_F = handoff_reveal("handoff_reveal_forward", FOLD_FL, 1)
A_COVER_B = handoff_cover("handoff_cover_back", FOLD_BL, FOLD_BL_TRIM, 0, -1)
A_REVEAL_B = handoff_reveal("handoff_reveal_back", FOLD_BR, -1)
A_QUEUE = Anim("handoff_queue_hold", 6)
A_CARRY = Anim("handoff_carry", 8)
A_CARRY.seq(WORLD.id, "scaleX", [(0, 1.0, "inout"), (4, 0.97, "inout"), (8, 1.0)])
A_CARRY.seq(WORLD.id, "scaleY", [(0, 1.0, "inout"), (4, 0.97, "inout"), (8, 1.0)])
A_RM_COVER = Anim("handoff_reduced_cover", 9)
A_RM_COVER.tween(RM_VEIL.id, "opacity", 0, 0.0, 9, 1.0, "linear")
A_RM_REVEAL = Anim("handoff_reduced_reveal", 12)
A_RM_REVEAL.tween(RM_VEIL.id, "opacity", 0, 1.0, 12, 0.0, "linear")
for a_ in (A_RM_COVER, A_RM_REVEAL, A_CARRY):
    for pnl in (FOLD_FR, FOLD_FL, FOLD_BL, FOLD_BR):
        a_.key(pnl.id, "scaleX", 0, 0.0)
for a_ in (A_RM_COVER, A_RM_REVEAL):
    a_.key(WORLD.id, "scaleX", 0, 1.0)
    a_.key(WORLD.id, "scaleY", 0, 1.0)
A_HANDOFF_IDLE = Anim("handoff_idle", 1)
A_HANDOFF_IDLE.key(RM_VEIL.id, "opacity", 0, 0.0)
for pnl in (FOLD_FR, FOLD_FL, FOLD_BL, FOLD_BR):
    A_HANDOFF_IDLE.key(pnl.id, "scaleX", 0, 0.0)

# thanks flap
A_THANKS_OPEN = Anim("thanks_open", 150)
A_THANKS_SHUT = Anim("thanks_closed", 12)
for flap in (SCENES[1].flap, SCENES[10].flap):
    A_THANKS_OPEN.seq(flap.id, "scaleX", [(0, 1.0, "antic"), (6, 1.08, "cloth"), (24, -0.85), (130, -0.85, "inout"), (150, -0.85)])
    A_THANKS_OPEN.seq(flap.id, "scaleY", [(0, 1.0, "out"), (10, 1.05, "out"), (24, 1.0)])
    A_THANKS_SHUT.seq(flap.id, "scaleX", [(0, -0.85, "cloth"), (12, 1.0)])
    A_THANKS_SHUT.key(flap.id, "scaleY", 0, 1.0)

# pause icon
A_PLAYING = Anim("ui_playing", 1)
A_PLAYING.key(PAUSE_SOLO.id, "activeComponentId", 0, PAUSE_GLYPH.id, kind="Id")
A_PAUSED = Anim("ui_paused", 1)
A_PAUSED.key(PAUSE_SOLO.id, "activeComponentId", 0, PLAY_GLYPH.id, kind="Id")

# persona selection
A_PERSONA = []
for k in range(4):
    ap = Anim(f"persona_{k}", 1)
    ap.key(SCENES[9].esolo.id, "activeComponentId", 0, SCENES[9].eroots[k].id, kind="Id")
    ap.key(SCENES[10].psolo.id, "activeComponentId", 0, SCENES[10].proots[k].id, kind="Id")
    A_PERSONA.append(ap)

A_TICK = Anim("timer_tick", TICK_FRAMES)
A_PRESS = Anim("gesture_press_window", 21)  # 350 ms decides tap vs hold

# =====================================================================
# State machine
# =====================================================================
L = []  # layers
B = lambda prop, v=True: cond(vm, prop, "Boolean", v)
N = lambda prop, v, o="equal": cond(vm, prop, "Number", v, o)
TR = lambda prop: cond(vm, prop, "Trigger")


def st(anim, x, y, *kids, **kw):
    a_ = dict(x=x, y=y)
    if anim is not None:
        a_["animationId"] = anim.id
    a_.update(kw)
    return E("AnimationState", a_, list(kids))


def fire(prop, at_end=False):
    return el("StateMachineFireTrigger", viewModelPathIds=vm.path(prop), occursValue=1 if at_end else 0)


def fire_event(ev, at_end=False):
    return el("StateMachineFireEvent", eventId=ev.id, occursValue=1 if at_end else 0)


# ---- Layer: Scenes ----------------------------------------------------------
sid = {}
for n in range(1, 11):
    sid[("gf", n)] = new_id()
    sid[("gb", n)] = new_id()
    sid[("idle", n)] = new_id()
    for v in range(len(ENTER[n])):
        sid[("in", n, v)] = new_id()
        sid[("rm", n, v)] = new_id()
sid["replay"] = new_id()
sid["finish"] = new_id()

scene_states = []


def nav_out(n):
    out = []
    if n < 10:
        out.append(trans(sid[("gf", n + 1)], TR("_commitNext")))
    if n > 1:
        out.append(trans(sid[("gb", n - 1)], TR("_commitPrev")))
    return out


def entry_actions(n):
    return [set_vm(vm, "currentScreen", "Number", n), set_vm(vm, "screenProgress", "Number", 0),
            set_vm(vm, "_settled", "Boolean", False), set_vm_from(vm, "screenChangedCount", "screenChangedCount", "Number", INC),
            fire_event(EV_SCREEN[n - 1])]


for n in range(1, 11):
    X = 300 + (n - 1) * 260
    always = n in (1, 10)
    variants = len(ENTER[n])
    # forward gate
    g = []
    for gate, step, yy in (("gf", 1, -420), ("gb", -1, 420)):
        kids = []
        show_ = (lambda n=n: []) if always else (lambda n=n: [B(f"showScreen{n}")])
        if n == 9:
            for k in (1, 2, 3):
                kids.append(trans(sid[("in", n, k)], *show_(), B("reducedMotion", False), N("personaIndex", k)))
                kids.append(trans(sid[("rm", n, k)], *show_(), B("reducedMotion", True), N("personaIndex", k)))
            kids.append(trans(sid[("in", n, 0)], *show_(), B("reducedMotion", False)))
            kids.append(trans(sid[("rm", n, 0)], *show_(), B("reducedMotion", True)))
        else:
            kids.append(trans(sid[("in", n, 0)], *show_(), B("reducedMotion", False)))
            kids.append(trans(sid[("rm", n, 0)], *show_(), B("reducedMotion", True)))
        if not always:
            nxt = sid[(gate, n + step)]
            kids.append(trans(nxt, B(f"showScreen{n}", False)))
        scene_states.append(E("AnimationState", {"x": X, "y": yy}, kids, id=sid[(gate, n)]))
    for v in range(variants):
        for kind, anims, yy in (("in", ENTER[n], -140 + v * 40), ("rm", REDUCED[n], 140 + v * 40)):
            kids = list(entry_actions(n))
            if n == 1:
                kids.append(el("FocusActionTarget", targetId=APP.id))
            kids += nav_out(n)
            if n == 10:
                kids.append(trans(sid["finish"], B("_finishedLatch", False), exit_pct=100))
                kids.append(trans(sid[("idle", n)], B("_finishedLatch", True), exit_pct=100))
            else:
                kids.append(trans(sid[("idle", n)], exit_pct=100))
            scene_states.append(E("AnimationState", {"x": X + (v * 30 if kind == "in" else v * 30), "y": yy,
                                                     "animationId": anims[v].id}, kids, id=sid[(kind, n, v)]))
    kids = [set_vm(vm, "_settled", "Boolean", True)] + nav_out(n)
    scene_states.append(E("AnimationState", {"x": X + 130, "y": 0, "animationId": REST.id}, kids, id=sid[("idle", n)]))

finish_kids = [set_vm(vm, "_finishedLatch", "Boolean", True),
               set_vm_from(vm, "recapFinishedCount", "recapFinishedCount", "Number", INC),
               fire_event(EV_FINISH), trans(sid[("idle", 10)])] + nav_out(10)
scene_states.append(E("AnimationState", {"x": 300 + 9 * 260 + 130, "y": 260, "animationId": REST.id}, finish_kids, id=sid["finish"]))
replay_kids = [set_vm(vm, "_finishedLatch", "Boolean", False), set_vm(vm, "screenProgress", "Number", 0),
               trans(sid[("gf", 1)])]
scene_states.append(E("AnimationState", {"x": 120, "y": 0, "animationId": REST.id}, replay_kids, id=sid["replay"]))
L.append(el("StateMachineLayer",
            el("AnyState", trans(sid["replay"], TR("_commitReplay")), x=120, y=-300),
            el("ExitState", x=120, y=300),
            el("EntryState", trans(sid["replay"]), x=-60, y=0),
            *scene_states, name="Scenes"))

# ---- Layer: Handoff (signature fold transition with a one-deep tap queue) --
h = {k: new_id() for k in ["idle", "cf", "rf", "cb", "rb", "qf1", "qf2", "qb1", "qb2", "carry", "rmcf", "rmcb", "rmr", "replay"]}
CAN_NEXT = lambda: N("currentScreen", 10, "lessThan")
CAN_PREV = lambda: N("currentScreen", 1, "greaterThan")
RM = lambda v=True: B("reducedMotion", v)


def to_next_from_idle():
    return [
        trans(h["carry"], TR("navNext"), RM(False), N("currentScreen", 8), B("showScreen9")),
        trans(h["carry"], TR("navNext"), RM(False), N("currentScreen", 9)),
        trans(h["cf"], TR("navNext"), RM(False), CAN_NEXT()),
        trans(h["rmcf"], TR("navNext"), RM(True), CAN_NEXT()),
        trans(h["cb"], TR("navPrevious"), RM(False), CAN_PREV()),
        trans(h["rmcb"], TR("navPrevious"), RM(True), CAN_PREV()),
        trans(h["replay"], TR("replayRecap")),
    ]


H_STATES = [
    st(A_HANDOFF_IDLE, 0, 0, *to_next_from_idle(), id=h["idle"]),
    st(A_COVER_F, 260, -200, fire("_commitNext", True),
       trans(h["qf1"], TR("navNext"), CAN_NEXT()),
       trans(h["rf"], TR("navPrevious"), duration=80),
       trans(h["rf"], exit_pct=100), id=h["cf"]),
    st(A_QUEUE, 520, -260, fire("_commitNext"), fire("_commitNext", True),
       trans(h["qf2"], TR("navNext"), CAN_NEXT()),
       trans(h["rmr"], RM(True), exit_pct=100), trans(h["rf"], exit_pct=100), id=h["qf1"]),
    st(A_QUEUE, 520, -140, fire("_commitNext"), fire("_commitNext", True),
       trans(h["qf1"], TR("navNext"), CAN_NEXT()),
       trans(h["rmr"], RM(True), exit_pct=100), trans(h["rf"], exit_pct=100), id=h["qf2"]),
    st(A_REVEAL_F, 780, -200, trans(h["cf"], TR("navNext"), CAN_NEXT(), RM(False), duration=60),
       trans(h["cb"], TR("navPrevious"), CAN_PREV(), RM(False), duration=60),
       trans(h["idle"], exit_pct=100), id=h["rf"]),
    st(A_COVER_B, 260, 200, fire("_commitPrev", True),
       trans(h["qb1"], TR("navPrevious"), CAN_PREV()),
       trans(h["rb"], TR("navNext"), duration=80),
       trans(h["rb"], exit_pct=100), id=h["cb"]),
    st(A_QUEUE, 520, 140, fire("_commitPrev"), fire("_commitPrev", True),
       trans(h["qb2"], TR("navPrevious"), CAN_PREV()),
       trans(h["rmr"], RM(True), exit_pct=100), trans(h["rb"], exit_pct=100), id=h["qb1"]),
    st(A_QUEUE, 520, 260, fire("_commitPrev"), fire("_commitPrev", True),
       trans(h["qb1"], TR("navPrevious"), CAN_PREV()),
       trans(h["rmr"], RM(True), exit_pct=100), trans(h["rb"], exit_pct=100), id=h["qb2"]),
    st(A_REVEAL_B, 780, 200, trans(h["cf"], TR("navNext"), CAN_NEXT(), RM(False), duration=60),
       trans(h["cb"], TR("navPrevious"), CAN_PREV(), RM(False), duration=60),
       trans(h["idle"], exit_pct=100), id=h["rb"]),
    st(A_CARRY, 260, -420, fire("_commitNext", True), trans(h["idle"], exit_pct=100), id=h["carry"]),
    st(A_RM_COVER, 260, 420, fire("_commitNext", True), trans(h["qf1"], TR("navNext"), CAN_NEXT()),
       trans(h["rmr"], exit_pct=100), id=h["rmcf"]),
    st(A_RM_COVER, 260, 560, fire("_commitPrev", True), trans(h["qb1"], TR("navPrevious"), CAN_PREV()),
       trans(h["rmr"], exit_pct=100), id=h["rmcb"]),
    st(A_RM_REVEAL, 520, 480, *[t for t in to_next_from_idle()[2:6]], trans(h["idle"], exit_pct=100), id=h["rmr"]),
    st(A_COVER_F, 260, -560, fire("_commitReplay", True), trans(h["rmr"], RM(True), exit_pct=100),
       trans(h["rf"], exit_pct=100), id=h["replay"]),
]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-560), el("ExitState", x=0, y=560),
            el("EntryState", trans(h["idle"]), x=-200, y=0), *H_STATES, name="Handoff"))

# ---- Layer: Gesture (tap vs hold) ----------------------------------------------
g = {k: new_id() for k in ["idle", "press", "tapn", "tapp", "hold", "release"]}
G_STATES = [
    st(REST, 0, 0, trans(g["press"], B("_pressing")), id=g["idle"]),
    st(A_PRESS, 220, 0, trans(g["tapn"], B("_pressing", False), N("_pressSide", 0, "greaterThan")),
       trans(g["tapp"], B("_pressing", False), N("_pressSide", 0, "lessThan")),
       trans(g["hold"], exit_pct=100), id=g["press"]),
    st(REST, 440, -120, fire("navNext"), trans(g["idle"]), id=g["tapn"]),
    st(REST, 440, 120, fire("navPrevious"), trans(g["idle"]), id=g["tapp"]),
    st(REST, 440, 0, set_vm(vm, "_holdPaused", "Boolean", True), trans(g["release"], B("_pressing", False)), id=g["hold"]),
    st(REST, 660, 0, set_vm(vm, "_holdPaused", "Boolean", False), trans(g["idle"]), id=g["release"]),
]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-240), el("ExitState", x=660, y=-240),
            el("EntryState", trans(g["idle"]), x=-220, y=0), *G_STATES, name="Gesture"))

# ---- Layer: Timer (auto-advance) ------------------------------------------------
t_ = {k: new_id() for k in ["idle", "a", "b", "fire", "wait"]}


def run_conds():
    return [B("_settled"), B("autoAdvanceEnabled"), B("isPaused", False), B("_holdPaused", False),
            N("currentScreen", 10, "lessThan")]


def stop_trans():
    return [trans(t_["idle"], B("_settled", False)), trans(t_["idle"], B("autoAdvanceEnabled", False)),
            trans(t_["idle"], B("isPaused")), trans(t_["idle"], B("_holdPaused"))]


def tick_state(me, other, x, y):
    return st(A_TICK, x, y, set_vm_from(vm, "screenProgress", "screenProgress", "Number", C_TICK),
              trans(t_["fire"], N("screenProgress", 1, "greaterThanOrEqual")),
              *stop_trans(), trans(other, *run_conds(), exit_pct=100), id=me)


T_STATES = [
    st(REST, 0, 0, trans(t_["a"], *run_conds()), id=t_["idle"]),
    tick_state(t_["a"], t_["b"], 220, -100),
    tick_state(t_["b"], t_["a"], 220, 100),
    st(REST, 440, 0, set_vm(vm, "screenProgress", "Number", 1), fire("navNext"), trans(t_["wait"]), id=t_["fire"]),
    st(REST, 660, 0, trans(t_["idle"], B("_settled", False)), trans(t_["idle"], B("isPaused")), id=t_["wait"]),
]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-240), el("ExitState", x=660, y=-240),
            el("EntryState", trans(t_["idle"]), x=-220, y=0), *T_STATES, name="Timer"))

# ---- Layers: Ambient (restrained idle loops, frozen on pause, static in reduced motion)
for nm, loop_anim in (("Ambient sway", AMB_SWAY), ("Ambient flow", AMB_FLOW)):
    am = {k: new_id() for k in ["run", "frozen", "rest"]}
    A_STATES = [
        st(loop_anim, 0, 0, trans(am["rest"], RM(True), duration=200), trans(am["frozen"], B("isPaused")),
           trans(am["frozen"], B("_holdPaused")), id=am["run"]),
        st(None, 220, -100, trans(am["rest"], RM(True)),
           trans(am["run"], B("isPaused", False), B("_holdPaused", False), RM(False), duration=250), id=am["frozen"]),
        st(REST_SWAY, 220, 100, trans(am["run"], RM(False), B("isPaused", False), B("_holdPaused", False), duration=250),
           id=am["rest"]),
    ]
    L.append(el("StateMachineLayer", el("AnyState", x=0, y=-240), el("ExitState", x=440, y=-240),
                el("EntryState", trans(am["run"], RM(False)), trans(am["rest"], RM(True)), x=-220, y=0), *A_STATES, name=nm))

# ---- Layer: Persona (atomic emblem selection; unknown index falls back to row 0)
pp = [new_id() for _ in range(4)]
P_STATES = []
for k in range(4):
    kids = []
    for j in range(4):
        if j == k:
            continue
        if j == 0:
            kids.append(trans(pp[0], N("personaIndex", 1, "notEqual"), N("personaIndex", 2, "notEqual"),
                              N("personaIndex", 3, "notEqual")))
        else:
            kids.append(trans(pp[j], N("personaIndex", j)))
    P_STATES.append(st(A_PERSONA[k], 220 * k, 0, *kids, id=pp[k]))
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-200), el("ExitState", x=660, y=-200),
            el("EntryState", trans(pp[1], N("personaIndex", 1)), trans(pp[2], N("personaIndex", 2)),
               trans(pp[3], N("personaIndex", 3)), trans(pp[0]), x=-220, y=0), *P_STATES, name="Persona"))

# ---- Layer: Activity (derives _noActivity from the metric-scene visibility flags)
ac = [new_id(), new_id()]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-200), el("ExitState", x=440, y=-200),
            el("EntryState", trans(ac[0]), x=-220, y=0),
            st(REST, 0, 0, set_vm(vm, "_noActivity", "Boolean", False),
               trans(ac[1], *[B(f"showScreen{i}", False) for i in range(2, 9)]), id=ac[0]),
            st(REST, 220, 0, set_vm(vm, "_noActivity", "Boolean", True),
               *[trans(ac[0], B(f"showScreen{i}")) for i in range(2, 9)], id=ac[1]), name="Activity"))

# ---- Layer: Pause UI -------------------------------------------------------------
pu = [new_id(), new_id()]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-200), el("ExitState", x=440, y=-200),
            el("EntryState", trans(pu[0]), x=-220, y=0),
            st(A_PLAYING, 0, 0, trans(pu[1], B("isPaused")), id=pu[0]),
            st(A_PAUSED, 220, 0, trans(pu[0], B("isPaused", False)), id=pu[1]), name="Pause icon"))

# ---- Layer: Thanks flap (signature interaction) ---------------------------------
th_ = [new_id(), new_id()]
L.append(el("StateMachineLayer", el("AnyState", x=0, y=-200), el("ExitState", x=440, y=-200),
            el("EntryState", trans(th_[0]), x=-220, y=0),
            st(A_THANKS_SHUT, 0, 0, trans(th_[1], B("_thanksOpen")), id=th_[0]),
            st(A_THANKS_OPEN, 220, 0, set_vm(vm, "_thanksOpen", "Boolean", False),
               trans(th_[0], exit_pct=100), id=th_[1]), name="Thanks"))

# ---- Listeners --------------------------------------------------------------------
TOGGLE_PAUSE = lambda: set_vm_from(vm, "isPaused", "isPaused", "Boolean", NEGATE)


def key_input(key, mods=None):
    a_ = dict(keyType=key, keyPhase=1)
    if mods:
        a_["modifiers"] = mods
    return el("KeyboardInput", **a_)


LISTENERS = [
    el("StateMachineListenerSingle", set_vm(vm, "_pressSide", "Number", -1), set_vm(vm, "_pressing", "Boolean", True),
       targetId=NAV_LEFT.id, listenerTypeValue="down", name="Press back region"),
    el("StateMachineListenerSingle", set_vm(vm, "_pressSide", "Number", 1), set_vm(vm, "_pressing", "Boolean", True),
       targetId=NAV_RIGHT.id, listenerTypeValue="down", name="Press forward region"),
    el("StateMachineListenerSingle", set_vm(vm, "_pressing", "Boolean", False), targetId=SURFACE.id, listenerTypeValue="up",
       name="Release anywhere"),
    el("StateMachineListenerSingle", set_vm(vm, "_thanksOpen", "Boolean", True), targetId=DEL_S1.id, listenerTypeValue="click",
       name="Lift thanks flap S1"),
    el("StateMachineListenerSingle", set_vm(vm, "_thanksOpen", "Boolean", True), targetId=DEL_S10.id, listenerTypeValue="click",
       name="Lift thanks flap S10"),
    # global keyboard on the App focus host
    el("StateMachineListener", el("ListenerInputTypeKeyboard", key_input("right"), listenerTypeValue="keyboard"),
       set_vm(vm, "navNext", "Trigger", 1), targetId=APP.id, name="Key right"),
    el("StateMachineListener", el("ListenerInputTypeKeyboard", key_input("left"), listenerTypeValue="keyboard"),
       set_vm(vm, "navPrevious", "Trigger", 1), targetId=APP.id, name="Key left"),
    el("StateMachineListener", el("ListenerInputTypeKeyboard", key_input("space"), listenerTypeValue="keyboard"),
       TOGGLE_PAUSE(), targetId=APP.id, name="Key space"),
    el("StateMachineListener", el("ListenerInputTypeKeyboard", key_input("tab"), listenerTypeValue="keyboard"),
       el("FocusActionTraversal", traversalKind="next"), targetId=APP.id, name="Key tab"),
    el("StateMachineListener", el("ListenerInputTypeKeyboard", key_input("tab", 1), listenerTypeValue="keyboard"),
       el("FocusActionTraversal", traversalKind="previous"), targetId=APP.id, name="Key shift tab"),
]


def button_listener(btn, name, *actions):
    return el("StateMachineListener",
              el("ListenerInputType", listenerTypeValue="click"),
              el("ListenerInputTypeSemantic", el("SemanticInput", actionType="tap"), listenerTypeValue="semanticAction"),
              *actions, targetId=btn.body.id, name=name)


def enter_listener(btn, name, *actions):
    return el("StateMachineListener",
              el("ListenerInputTypeKeyboard", key_input("enter"), key_input("kpEnter"), listenerTypeValue="keyboard"),
              *actions, targetId=btn.body.id, name=name + " (enter)")


BTN_ACTIONS = [
    (prev_btn, "Previous", lambda: [set_vm(vm, "navPrevious", "Trigger", 1)]),
    (cont_btn, "Continue", lambda: [set_vm(vm, "navNext", "Trigger", 1)]),
    (share_btn, "Share", lambda: [el("ListenerFireEvent", eventId=EV_SHARE.id),
                                  set_vm_from(vm, "shareTappedCount", "shareTappedCount", "Number", INC)]),
    (replay_btn, "Replay", lambda: [set_vm(vm, "replayRecap", "Trigger", 1)]),
    (pause_btn, "Pause", lambda: [TOGGLE_PAUSE()]),
]
for btn, nm, acts in BTN_ACTIONS:
    # click listeners target the generous hit shape; semantic + keyboard target the focusable body
    LISTENERS.append(el("StateMachineListenerSingle", *acts(), targetId=btn.hit.id, listenerTypeValue="click", name=nm + " click"))
    LISTENERS.append(el("StateMachineListener",
                        el("ListenerInputTypeSemantic", el("SemanticInput", actionType="tap"), listenerTypeValue="semanticAction"),
                        *acts(), targetId=btn.body.id, name=nm + " semantic"))
    LISTENERS.append(enter_listener(btn, nm, *acts()))
for k, body in FOCUSABLE:
    LISTENERS.append(el("StateMachineListener", el("ListenerInputType", listenerTypeValue="focus"),
                        set_vm(vm, "_focusIndex", "Number", k), targetId=body.id, name=f"Focus {k}"))
    LISTENERS.append(el("StateMachineListener", el("ListenerInputType", listenerTypeValue="blur"),
                        set_vm(vm, "_focusIndex", "Number", 0), targetId=body.id, name=f"Blur {k}"))

SM = el("StateMachine", *LISTENERS, *L, name="Recap")

# =====================================================================
# Assemble document
# =====================================================================
ALL_ANIMS = []
for n in range(1, 11):
    ALL_ANIMS += ENTER[n] + REDUCED[n]
ALL_ANIMS += [REST, AMB_SWAY, AMB_FLOW, REST_SWAY, A_COVER_F, A_REVEAL_F, A_COVER_B, A_REVEAL_B, A_QUEUE, A_CARRY,
              A_RM_COVER, A_RM_REVEAL, A_HANDOFF_IDLE, A_THANKS_OPEN, A_THANKS_SHUT, A_PLAYING, A_PAUSED, *A_PERSONA,
              A_TICK, A_PRESS]

inst_id = new_id()
style_id = new_id()
ARTBOARD = el("Artboard", el("LayoutComponentStyle", name="Artboard style", id=style_id),
              APP, *EV_SCREEN, EV_SHARE, EV_FINISH, SM, *[a_.element() for a_ in ALL_ANIMS],
              defaultStateMachineId=SM.id, viewModelId=vm.id, viewModelInstanceId=inst_id, styleId=style_id,
              width=W, height=H, clip=True, name="Patchwork Recap")

ROOT = el("Rive", ARTBOARD, *CONVS,
          E("FontAsset", {"file": "assets/fonts/BreeSerif-Regular.ttf", "name": "Bree Serif"}, id=FONT_BREE),
          E("FontAsset", {"file": "assets/fonts/AtkinsonHyperlegible-Regular.ttf", "name": "Atkinson Hyperlegible"}, id=FONT_ATK),
          E("FontAsset", {"file": "assets/fonts/AtkinsonHyperlegible-Bold.ttf", "name": "Atkinson Hyperlegible Bold"}, id=FONT_ATKB),
          vm.element(inst_id), version=1, kind="fragment")

header = ("<!-- GENERATED by apps/patchwork/tools/gen_scene.py — Patchwork ten-scene recap.\n"
          "     Edit here for small tweaks, or change the generator and re-run it. -->\n")
with open(OUT, "w") as f:
    f.write("\n".join(ROOT.render()) + "\n")
print("wrote", os.path.normpath(OUT), "anims:", len(ALL_ANIMS))
