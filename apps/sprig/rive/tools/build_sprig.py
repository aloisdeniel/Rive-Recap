#!/usr/bin/env python3
"""Generates ../scene.rml for the Sprig 2026 recap.

Run:  python3 tools/build_sprig.py   (from apps/sprig/rive)

The output RML is the editable deliverable.  This script keeps ten scenes,
their entrance / reverse / reduced-motion timelines and the sequencing state
machine consistent; re-run it after changing anything here.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rml import *  # noqa
from rml import _f  # noqa

W, H = 390, 844
FPS = 60
STEPS = 28  # dwell clock resolution (pause granularity = dwell / STEPS)

# ===================================================================== view model

VMID = ID()
PROPS = {}       # name -> (id, type)
VM_ORDER = []


def prop(name, typ, default):
    PROPS[name] = (ID(), typ, default)
    VM_ORDER.append(name)


SPEC = [
    ("userName", "string", "Alex"), ("year", "number", 2026),
    ("periodLabel", "string", "January 1–December 31, 2026"), ("locale", "string", "en-GB"),
    ("careMoments", "number", 248), ("plantsNurtured", "number", 18), ("newLeaves", "number", 73),
    ("cuttingsRooted", "number", 12), ("careStreak", "number", 21), ("plantsShared", "number", 6),
    ("activeMonths", "number", 11), ("personaIndex", "number", 0), ("personaName", "string", "Canopy Keeper"),
    ("personaDescription", "string", "You made room for a jungle."), ("personaColor", "color", "FFF6F1DC"),
    ("autoAdvanceSeconds", "number", 7), ("autoAdvanceEnabled", "bool", True), ("isPaused", "bool", False),
    ("reducedMotion", "bool", False), ("soundEnabled", "bool", False), ("currentScreen", "number", 1),
    ("screenProgress", "number", 0), ("shareIncludeName", "bool", False),
    ("shareIncludeSensitiveValues", "bool", False), ("continueLabel", "string", "Continue"),
    ("previousLabel", "string", "Previous"), ("pauseLabel", "string", "Pause"), ("playLabel", "string", "Play"),
    ("shareLabel", "string", "Share"), ("replayLabel", "string", "Replay"),
    ("introHeadline", "string", "Your 2026 on Sprig"), ("introSupport", "string", "A year, uniquely yours."),
    ("summaryHeadline", "string", "A little year. A lot of you."),
    ("summarySupport", "string", "Take a piece of your year with you."),
    ("emptyHeadline", "string", "Every story starts somewhere."),
    ("emptySupport", "string", "Your next chapter is waiting."), ("personaLabel", "string", "Your personal style"),
] + [(f"showScreen{i}", "bool", True) for i in range(1, 11)] + [
    ("screen2Headline", "string", "Little rituals. Big growth."),
    ("screen2Support", "string", "Each check-in made room for something green."),
    ("screen2Unit", "string", "care moments"),
    ("screen3Headline", "string", "Your own little jungle."),
    ("screen3Support", "string", "A collection with a character all its own."),
    ("screen3Unit", "string", "plants nurtured"),
    ("screen4Headline", "string", "Look what unfolded."),
    ("screen4Support", "string", "Small beginnings became a fuller canopy."),
    ("screen4Unit", "string", "new leaves"),
    ("screen5Headline", "string", "Good things branch out."),
    ("screen5Support", "string", "New roots, new possibilities."),
    ("screen5Unit", "string", "cuttings rooted"),
    ("screen6Headline", "string", "A rhythm that took root."),
    ("screen6Support", "string", "Your longest run of gentle check-ins."),
    ("screen6Unit", "string", "day care streak"),
    ("screen7Headline", "string", "You passed the green on."),
    ("screen7Support", "string", "A little life for someone else's windowsill."),
    ("screen7Unit", "string", "plants shared"),
    ("screen8Headline", "string", "A year of growing together."),
    ("screen8Support", "string", "Every season brought something different."),
    ("screen8Unit", "string", "active months"),
    # ---- adapter additions (documented in README)
    ("groupSeparator", "string", ","),
    # ---- private state-machine plumbing (leading underscore = not user data)
    ("_navNext", "trigger", None), ("_navPrev", "trigger", None), ("_replay", "trigger", None),
    ("_navDir", "number", 1), ("_pressing", "bool", False), ("_pressSide", "number", 0),
    ("_holdPaused", "bool", False), ("_leafHeld", "bool", False), ("_focusIndex", "number", 0),
]
for n, t, d in SPEC:
    prop(n, t, d)


def P(name):
    return f"{VMID}-{PROPS[name][0]}"


METRIC = {2: "careMoments", 3: "plantsNurtured", 4: "newLeaves", 5: "cuttingsRooted", 6: "careStreak",
          7: "plantsShared", 8: "activeMonths"}

FIXTURES = {
    "Sample": {},
    "NewUser": {"userName": "Sam", "careMoments": 0, "plantsNurtured": 0, "newLeaves": 0, "cuttingsRooted": 0,
                "careStreak": 0, "plantsShared": 0, "activeMonths": 0, "personaName": "",
                "personaDescription": "", **{f"showScreen{i}": False for i in range(2, 10)}},
    "Extreme": {"userName": "Maximiliana Wilhelmina Featherstonehaugh-Okonkwo", "careMoments": 128940,
                "plantsNurtured": 1204, "newLeaves": 98765, "cuttingsRooted": 4321, "careStreak": 365,
                "plantsShared": 999, "activeMonths": 12, "personaIndex": 3, "personaName": "Windowsill Wanderer",
                "personaDescription": "You found possibility in every sunny corner.", "personaColor": "FF173E32",
                "screen2Headline": "Little rituals, repeated with care. Big, beautiful growth.",
                "screen2Support": "Each and every gentle check-in made a little more room for something green.",
                "screen2Unit": "care moments logged with love",
                "introHeadline": "Your whole 2026, told through Sprig"},
}

# ===================================================================== converters
CV = Converters()


def c_tostr():
    return CV.add("tostr0", lambda cid: E("DataConverterToString", decimals=0, round=True, name="Integer text", id=cid))


def c_b2n():
    return CV.add("b2n", lambda cid: E("DataConverterToNumber", name="Bool to number", id=cid))


def c_not():
    return CV.add("not", lambda cid: E("DataConverterBooleanNegate", name="Not", id=cid))


def c_show_display():
    # bool (shown) -> displayValue (0 = flex, 1 = none)
    return CV.group("showdisp", [c_not(), c_b2n()], "Visible to display")


def c_rm_duration():
    rm = CV.add("rmmap", lambda cid: E("DataConverterRangeMapper", minInput=0.0, maxInput=1.0, minOutput=1.15,
                                       maxOutput=0.02, clampLower=True, clampUpper=True,
                                       name="Count duration (reduced motion = instant)", id=cid))
    return CV.group("rmdur", [c_b2n(), rm], "Reduced motion to duration")


def c_interp(key="count", dur=1.15, ease=(0.22, 0.0, 0.18, 1.0)):
    def b(cid):
        el = E("DataConverterInterpolator", interpolationType="cubic", duration=float(dur), name=f"Ease {key}", id=cid)
        el.add(E("CubicEaseInterpolator", x1=ease[0], y1=ease[1], x2=ease[2], y2=ease[3]))
        el.add(bind(P("reducedMotion"), 756, c_rm_duration()))
        return el
    return CV.add(("interp", key), b)


def c_gate(k):
    """input * (currentScreen == k ? 1 : 0)  -- count-up starts when scene k becomes current."""
    cur = lambda: tV(bind_el=bind(P("currentScreen"), 777))
    return CV.add(("gate", k), formula(f"Gate scene {k}", [
        tIn(), tOp("*"), tO(), tV(1), tOp("-"), tF("min"), tV(1), tSep(),
        tO(), cur(), tOp("-"), tV(k), tC(), tOp("*"), tO(), cur(), tOp("-"), tV(k), tC(), tC(), tC()]))


def c_clamp_nonneg():
    return CV.add("nonneg", formula("Clamp invalid negatives", [tF("max"), tV(0), tSep(), tIn(), tC()]))


def f_thousands():
    return CV.add("thou", formula("Thousands part", [tF("floor"), tF("round"), tIn(), tC(), tOp("/"), tV(1000), tC()]))


def f_rest():
    return CV.add("rest", formula("Below thousand", [tF("round"), tIn(), tC(), tOp("%"), tV(1000)]))


def f_disp_big():
    return CV.add("dbig", formula("Display when >= 1000", [tV(1), tOp("-"), tF("min"), tV(1), tSep(), tF("floor"),
                                                            tF("round"), tIn(), tC(), tOp("/"), tV(1000), tC(), tC()]))


def f_disp_small():
    return CV.add("dsmall", formula("Display when < 1000", [tF("min"), tV(1), tSep(), tF("floor"), tF("round"), tIn(),
                                                             tC(), tOp("/"), tV(1000), tC(), tC()]))


def c_pad3():
    return CV.add("pad3", lambda cid: E("DataConverterStringPad", length=3, text="0", padType="start",
                                        name="Pad to 3", id=cid))


def count_chain(k, tail, key):
    return CV.group((k, key), [c_clamp_nonneg(), c_gate(k), c_interp()] + tail, f"Count s{k} {key}")


def f_unit_clamp(i, scale=1.0, name="Lit"):
    # clamp((x - i) * scale, 0, 1)
    return CV.add(("lit", i, scale), formula(f"{name} {i}", [tF("max"), tV(0), tSep(), tF("min"), tV(1), tSep(), tO(),
                                                              tIn(), tOp("-"), tV(i), tC(), tOp("*"), tV(scale),
                                                              tC(), tC()]))


def f_div_clamp(d):
    return CV.add(("divc", d), formula(f"x/{d} clamped", [tF("min"), tV(1), tSep(), tIn(), tOp("/"), tV(d), tC()]))

# ===================================================================== text


AX = {"wght": 2003265652, "opsz": 1869640570, "SOFT": 1397704276, "WONK": 1464814155}
FONT_FR = ID()
FONT_DM = ID()


def tstyle(font, size, color, wght=400, opsz=None, soft=None, wonk=None, ls=None, lh=None, color_id=None,
           color_bind=None):
    sid = ID()
    fr = font == "fr"
    sc = solid(color, id=color_id)
    if color_bind is not None:
        sc.add(color_bind)
    style_name = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}.get(wght, "Custom")
    if fr and (soft or wonk):
        style_name = "Custom"
    el = E("TextStylePaint", E("Fill", sc, name="Fill"), fontSize=float(size), fontAssetId=FONT_FR if fr else FONT_DM,
           familyName="Fraunces" if fr else "DM Sans", styleName=style_name,
           letterSpacing=_f(ls), lineHeight=_f(lh), name=f"{'Fraunces' if fr else 'DM Sans'} {size}", id=sid)
    el.add(E("TextStyleAxis", tag=AX["wght"], axisValue=float(wght), name="wght"))
    el.add(E("TextStyleAxis", tag=AX["opsz"], axisValue=float(opsz or min(144 if fr else 40, max(9 if fr else 9, size))),
             name="opsz"))
    if fr:
        el.add(E("TextStyleAxis", tag=AX["SOFT"], axisValue=float(soft or 0), name="SOFT"))
        el.add(E("TextStyleAxis", tag=AX["WONK"], axisValue=float(wonk or 0), name="WONK"))
    return el, sid


def text(name, runs, font="dm", size=16, color=CREAM, wght=400, x=0, y=0, w=None, h=None, align="left",
         sizing=None, wrap=True, ox=0.0, oy=0.0, ls=None, lh=None, id=None, op=None, lp=None, overflow=None,
         soft=None, wonk=None, opsz=None, color_id=None, color_bind=None, modifiers=None):
    st, sid = tstyle(font, size, col(color) if not isinstance(color, Col) else color, wght, opsz, soft, wonk, ls, lh,
                     color_id, color_bind)
    t = E("Text", x=float(x), y=float(y), width=_f(w), height=_f(h), alignValue=align,
          sizingValue=sizing or ("autoHeight" if w else "autoWidth"), wrapValue="wrap" if wrap else "noWrap",
          originX=float(ox), originY=float(oy), overflowValue=overflow, opacity=_f(op), name=name, id=id or ID())
    if lp:
        t.add(lp)
    t.add(st)
    for r in runs:
        lit, path, conv = (r + (None, None))[:3] if isinstance(r, tuple) else (r, None, None)
        run = E("TextValueRun", styleId=sid, text=lit, name="Run")
        if path:
            run.add(bind(path, 268, conv))
        t.add(run)
    for m in modifiers or []:
        t.add(m)
    return t


def lp(w="fill", h="hug"):
    return E("LayoutParticipant", layoutWidthScaleType=w, layoutHeightScaleType=h, name="Layout")


def lstyle(**kw):
    return E("LayoutComponentStyle", id=ID(), name="Style", **kw)


def column(name, x, y, w, kids, gap=8.0, align="topLeft", id=None, op=None):
    st = lstyle(flexDirectionValue="column", gapVertical=float(gap), gapVerticalUnitsValue="points",
                layoutWidthScaleType="fixed", layoutHeightScaleType="hug", layoutAlignmentType=align,
                positionTypeValue="absolute")
    lc = E("LayoutComponent", st, *kids, x=float(x), y=float(y), width=float(w), height=10.0, styleId=st.id,
           opacity=_f(op), name=name, id=id or ID())
    return lc


def word_reveal(units=2):
    """Staggered word reveal: returns (modifier group, range id)."""
    rid = ID()
    g = E("TextModifierGroup",
          E("TextModifierRange", E("CubicInterpolatorComponent", x1=0.3, y1=0.0, x2=0.2, y2=1.0, name="Ease"),
            modifyFrom=0.0, modifyTo=1.0, falloffFrom=0.35, falloffTo=1.0, unitsValue=units, name="Sweep", id=rid),
          modifyOpacity=True, modifyTranslation=True, invertOpacity=True, opacity=0.0, y=18.0, name="Word reveal",
          id=ID())
    return g, rid


def reveal_keys(anim, rid, f0, f1, ease="outs"):
    # modifyFrom 327 / falloffFrom 317 swept together so the soft edge travels
    anim.key(rid, "modifyFrom", [(0, -0.4, "hold"), (f0, -0.4, ease), (f1, 1.0)])
    anim.key(rid, "falloffFrom", [(0, -0.05, "hold"), (f0, -0.05, ease), (f1, 1.35)])


def settle_reveal(anim, rid):
    anim.key(rid, "modifyFrom", [(0, 1.0, "hold")])
    anim.key(rid, "falloffFrom", [(0, 1.35, "hold")])


def hero_number(k, metric, x, y, w, size=112, color=CREAM, align="center", wght=560, row_id=None,
                shrink=(0.22, 0.13, 0.12)):
    """Count-up hero number with locale group separator, built from three hugging texts in a row.

    [thousands][sep] [rest padded to 3]  for >= 1000,  [raw] for < 1000.
    """
    src = P(metric)
    anchor = {"center": 0.5, "left": 0.0, "right": 1.0}[align]
    st = lstyle(flexDirectionValue="row", layoutWidthScaleType="fixed", layoutHeightScaleType="hug",
                positionTypeValue="absolute", layoutAlignmentType={"center": "topCenter", "left": "topLeft", "right": "topRight"}[align])
    kw = dict(font="fr", size=size, color=color, wght=wght, soft=40, wonk=0, lh=size * 1.0, wrap=False)

    def disp(conv_tail, key):
        return bind(src, 596, count_chain(k, conv_tail, key))

    def mk_box(name, txt, dkey, dtail):
        bst = lstyle(layoutWidthScaleType="hug", layoutHeightScaleType="hug")
        bst.add(disp(dtail, dkey))
        return E("LayoutComponent", bst, txt, width=10.0, height=10.0, styleId=bst.id, name=name, id=ID())

    t_th = text("Thousands", [("0", src, count_chain(k, [f_thousands(), c_tostr()], "thou")),
                              (",", P("groupSeparator"), None)], lp=lp("hug", "hug"), **kw)
    t_rest = text("Rest", [("000", src, count_chain(k, [f_rest(), c_tostr(), c_pad3()], "rest"))], lp=lp("hug", "hug"),
                  **kw)
    t_raw = text("Value", [("0", src, count_chain(k, [c_tostr()], "raw"))], lp=lp("hug", "hug"), **kw)
    row = E("LayoutComponent", st,
            mk_box("Big A", t_th, "dbig", [f_disp_big()]),
            mk_box("Big B", t_rest, "dbig", [f_disp_big()]),
            mk_box("Small", t_raw, "dsmall", [f_disp_small()]),
            x=float(-w * anchor), y=0.0, width=float(w), height=float(size), styleId=st.id, name=f"Hero {metric} row",
            id=ID())
    # large values shrink in steps (>=1,000 / >=10,000 / >=100,000) instead of overflowing; exact value stays
    big = lambda d: [tF("min"), tV(1), tSep(), tF("floor"), tIn(), tOp("/"), tV(d), tC(), tC()]
    fit = CV.add(("fit", shrink), formula("Shrink long numbers", [tV(1), tOp("-"), tV(shrink[0]), tOp("*")] + big(1000) +
                                          [tOp("-"), tV(shrink[1]), tOp("*")] + big(10000) +
                                          [tOp("-"), tV(shrink[2]), tOp("*")] + big(100000)))
    fconv = CV.group(("fit", shrink), [c_clamp_nonneg(), fit], "Number fit scale")
    return E("Node", row, bind(src, 16, fconv), bind(src, 17, fconv), x=float(x + w * anchor), y=float(y),
             name=f"Hero {metric}", id=row_id or ID())

# ===================================================================== art helpers


def stack(*items):
    """Painter's order in, RML order out (first child draws on top)."""
    out = []
    for it in items:
        if isinstance(it, (list, tuple)):
            out.extend(it)
        elif it is not None:
            out.append(it)
    return list(reversed(out))


def bg_rect(c, name="Background"):
    return shape(name, rect(W + 40, H + 40), fill(col(c)), x=W / 2, y=H / 2)


def poly(name, d, c, x=0, y=0, a=1.0, id=None, rot=None, sx=None, sy=None, op=None, feather=None):
    return shape(name, *path_el(d), fill(col(c, a), feather=feather), x=x, y=y, id=id, rot=rot, sx=sx, sy=sy, op=op)


def line(name, d, c, w, a=1.0, x=0, y=0, trim_el=None, id=None, op=None, cap="round"):
    return shape(name, *path_el(d, closed=False), stroke(col(c, a), w, trim=trim_el, cap=cap), x=x, y=y, id=id, op=op)


def shadow(name, w, h, x, y, a=0.28, s=12):
    return shape(name, ellipse(w, h), fill(col("#05130E", a), feather=s), x=x, y=y)


def drop_d(s=1.0):
    return (f"M0 {-18*s:.2f} C{5*s:.2f} {-9*s:.2f} {10*s:.2f} {-3*s:.2f} {10*s:.2f} {4*s:.2f} "
            f"C{10*s:.2f} {10*s:.2f} {5*s:.2f} {14*s:.2f} 0 {14*s:.2f} C{-5*s:.2f} {14*s:.2f} {-10*s:.2f} {10*s:.2f} "
            f"{-10*s:.2f} {4*s:.2f} C{-10*s:.2f} {-3*s:.2f} {-5*s:.2f} {-9*s:.2f} 0 {-18*s:.2f} Z")


def droplet(name, x, y, s=1.0, op=None):
    nid = ID()
    return node(name,
                shape("Glint", ellipse(4 * s, 6 * s), fill(col("#FFFFFF", 0.85)), x=-3.5 * s, y=-1 * s),
                poly("Drop", drop_d(s), LEAF_PALE, a=0.78),
                x=x, y=y, op=op, id=nid), nid


def pot(name, x, y, w=54, h=46, body=APRICOT, shade=APRICOT_DARK, rim=APRICOT_PALE, plant=None, s=1.0, id=None):
    hw = w / 2
    kids = stack(
        shadow("Shadow", w * 1.1, 12, 0, h + 2, 0.3, 6),
        poly("Body L", f"M{-hw} 0 L0 0 L0 {h} L{-hw*0.74} {h} Z", body),
        poly("Body R", f"M0 0 L{hw} 0 L{hw*0.74} {h} L0 {h} Z", shade),
        shape("Rim", rect(w * 1.12, h * 0.24, 3), fill(col(rim)), y=h * 0.06),
        plant,
    )
    return node(name, *kids, x=x, y=y, sx=s if s != 1 else None, sy=s if s != 1 else None, id=id or ID())


def sample_bezier(d, n=400):
    cs = parse_d(d)
    pts = []
    for c in cs:
        p0 = c["start"]
        for s in c["segs"]:
            if s[0] == "L":
                p1 = s[1]
                for i in range(n // 10):
                    t = i / (n // 10)
                    pts.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t))
                p0 = p1
            else:
                c1, c2, p3 = s[1], s[2], s[3]
                for i in range(n // 4):
                    t = i / (n // 4)
                    mt = 1 - t
                    pts.append((mt**3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t**3 * p3[0],
                                mt**3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t**3 * p3[1]))
                p0 = p3
        pts.append(p0)
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return pts, acc


def point_at(d, f):
    pts, acc = sample_bezier(d)
    target = acc[-1] * f
    for i in range(1, len(acc)):
        if acc[i] >= target:
            a, b = pts[i - 1], pts[i]
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            return a, ang
    return pts[-1], 0.0

# ===================================================================== global vine (narrative thread)


VINE_D = ("M386 752 C 366 700 386 650 376 590 C 366 530 388 480 379 420 C 370 360 388 312 378 252 "
          "C 370 200 386 150 374 104")


def vine_tip(k):
    (x, y), a = point_at(VINE_D, k / 10.0)
    return x, y

# ===================================================================== scene scaffolding


class Scene:
    def __init__(self, k, bgc, light=False, dur=108):
        self.k = k
        self.bgc = bgc
        self.light = light
        self.root = ID()
        self.content = ID()
        self.mask = ID()
        self.overlay = ID()
        self.ef = Anim(f"S{k} enter", dur)
        self.idle = Anim(f"S{k} idle", 360, "loop")
        self.settle = []      # (id, prop, offset) drifts for reverse arrival
        self.fade_leave = []  # ids faded quickly on leave (numbers)
        self.hits = []        # (id, x) hit regions active only while scene is current
        self.extra_hidden = []

    def key(self, obj, prop, keys):
        self.ef.key(obj, prop, keys)

    def appear(self, obj, f0, f1, dy=24.0, y0=None, ease="outs", fade=True, base_y=None):
        """fade + rise; base_y is the authored y."""
        if fade:
            self.key(obj, "opacity", [(0, 0.0, "hold"), (f0, 0.0, ease), (f1, 1.0)])
        if base_y is not None:
            self.key(obj, "y", [(0, base_y + dy, "hold"), (f0, base_y + dy, ease), (f1, base_y)])

    def pop(self, obj, f0, f1, s0=0.0, s1=1.0, ease="back"):
        self.key(obj, "scaleX", [(0, s0, "hold"), (f0, s0, ease), (f1, s1)])
        self.key(obj, "scaleY", [(0, s0, "hold"), (f0, s0, ease), (f1, s1)])

    def unfurl(self, parts, f0, f1, rot=None, rot0=None):
        """Leaf opens from its folded midrib: halves widen, node scales and rotates into place."""
        self.pop(parts["node"], f0, f1, 0.0, 1.0, "backs")
        self.key(parts["left"], "scaleX", [(0, 0.05, "hold"), (f0 + 3, 0.05, "out"), (f1 + 6, 1.0)])
        self.key(parts["right"], "scaleX", [(0, 0.05, "hold"), (f0 + 7, 0.05, "out"), (f1 + 10, 1.0)])
        if rot is not None:
            r0 = rot0 if rot0 is not None else rot * 0.3
            self.key(parts["node"], "rotation", [(0, r0, "hold"), (f0, r0, "out"), (f1 + 8, rot)])

    def sway(self, obj, base, amp, period=360, phase=0, prop="rotation"):
        """seamless loop: base -> +amp -> base -> -amp -> base (phase in frames)."""
        p = period
        ks = []
        pts = [(0, base), (p / 4, base + amp), (p / 2, base), (3 * p / 4, base - amp), (p, base)]
        # rotate the phase while keeping the loop seamless
        sh = [((f + phase) % p, v) for f, v in pts]
        sh.sort()
        if sh[0][0] != 0:
            # value at 0 by linear-ish interpolation from wrap
            f_last, v_last = sh[-1]
            f_first, v_first = sh[0]
            span = (p - f_last) + f_first
            v0 = v_last + (v_first - v_last) * ((p - f_last) / span)
            sh = [(0, v0)] + sh + [(p, v0)]
        else:
            sh.append((p, sh[0][1]))
        dedup = []
        for f, v in sh:
            if dedup and dedup[-1][0] == f:
                continue
            dedup.append((f, v))
        self.idle.key(obj, prop, [(f, v, "sine") for f, v in dedup])


def wipe_leaf_d():
    # leaf silhouette centred on origin (length 100, width 70), tip up-left
    return ("M0 -50 C 26 -36 36 -6 30 14 C 24 34 10 46 0 50 C -10 46 -24 34 -30 14 C -36 -6 -26 -36 0 -50 Z")


def build_scene_root(sc, content_kids, overlay_kids=None, clip=True):
    """root node: [overlay (unclipped wipe edge, flying leaf)] above [content (clipped by mask)] + mask shape."""
    k = sc.k
    ox, oy = vine_tip(k)
    sc.origin = (ox, oy)
    mask = shape(f"S{k} wipe mask", *path_el(wipe_leaf_d()), x=ox, y=oy, sx=26, sy=26, rot=0.2, id=sc.mask)
    content = node(f"S{k} content", *content_kids, id=sc.content)
    if clip and k > 1:
        content.kids.insert(0, E("ClippingShape", sourceId=sc.mask, name="Wipe clip"))
    # wipe overlay: edge outline following the mask + a big folded leaf crossing the camera
    edge_id = ID()
    sc.edge = edge_id
    edge = shape(f"S{k} wipe edge", *path_el(wipe_leaf_d()),
                 stroke(col(CREAM, 0.9), 2.2, fixed=True),
                 stroke(col(LEAF, 0.55), 14, fixed=True, feather=8),
                 x=ox, y=oy, sx=26, sy=26, rot=0.2, op=0.0, id=edge_id)
    fl, fparts = leaf(f"S{k} fold leaf", ox + 120, oy + 300, 560, 330, rot=-0.5, light=LEAF, dark=LEAF_DEEP,
                      rib=CREAM, rib_a=0.5)
    sc.fold = fparts
    fl.attrs["opacity"] = 0.0
    bud_id = ID()
    bud = node(f"S{k} bud",
               shape("Bud glow", ellipse(30, 30), fill(col(LEAF_PALE, 0.5), feather=8)),
               shape("Bud", *path_el(leaf_full_d(18, 14)), fill(col(LEAF)), y=8),
               x=ox, y=oy, sx=0.0, sy=0.0, id=bud_id)
    sc.bud = bud_id
    ov = node(f"S{k} wipe overlay", fl, edge, bud, *(overlay_kids or []), id=sc.overlay)
    root = node(f"Scene {k}", ov, content, mask, op=0.0, id=sc.root)
    return root


def scene_wipe_in(sc):
    """Signature transition: vine tip buds (anticipation), a leaf-shaped iris unfolds from it while a big paper
    leaf folds across the camera."""
    ox, oy = sc.origin
    a = sc.ef
    a.key(sc.root, "opacity", [(0, 1.0, "hold")])
    a.key(sc.bud, "scaleX", [(0, 0.0, "hold"), (1, 0.0, "back"), (10, 1.5, "in"), (18, 0.0)])
    a.key(sc.bud, "scaleY", [(0, 0.0, "hold"), (1, 0.0, "back"), (10, 1.5, "in"), (18, 0.0)])
    a.key(sc.mask, "x", [(0, ox, "hold")])
    a.key(sc.mask, "y", [(0, oy, "hold")])
    a.key(sc.mask, "scaleX", [(0, 0.01, "hold"), (8, 0.01, "fold"), (44, 26.0)])
    a.key(sc.mask, "scaleY", [(0, 0.01, "hold"), (8, 0.01, "fold"), (44, 26.0)])
    a.key(sc.mask, "rotation", [(0, -0.6, "hold"), (8, -0.6, "fold"), (44, 0.2)])
    for p in ("x", "y", "scaleX", "scaleY", "rotation"):
        a.tracks[(sc.edge, p)] = list(a.tracks[(sc.mask, p)])
    a.key(sc.edge, "opacity", [(0, 0.0, "hold"), (8, 1.0, "hold"), (40, 1.0, "in"), (46, 0.0)])
    f = sc.fold
    a.key(f["node"], "opacity", [(0, 0.0, "hold"), (4, 1.0, "hold"), (40, 1.0, "hold"), (41, 0.0)])
    a.key(f["node"], "x", [(0, ox + 160, "hold"), (4, ox + 160, "fold"), (40, ox - 640)])
    a.key(f["node"], "y", [(0, oy + 520, "hold"), (4, oy + 520, "fold"), (40, oy - 380)])
    a.key(f["node"], "rotation", [(0, -0.2, "hold"), (4, -0.2, "fold"), (40, -1.25)])
    a.key(f["right"], "scaleX", [(0, 1.0, "hold"), (10, 1.0, "fold"), (34, -0.85)])
    a.key(f["left"], "scaleX", [(0, 1.0, "hold"), (14, 1.0, "fold"), (38, 0.35)])


def scene_derive(sc):
    """Build reverse (EB), reduced-motion (ER), leave (LF/LB/LR) and hidden (H) timelines from the entrance."""
    k = sc.k
    ox, oy = sc.origin
    final = {}
    for (obj, p), keys in sc.ef.tracks.items():
        final[(obj, p)] = keys[-1][1]
    # wipe pieces settle invisible / mask fully open
    final[(sc.root, "opacity")] = 1.0
    eb = Anim(f"S{k} arrive back", 48)
    for (obj, p), v in final.items():
        eb.key(obj, p, [(0, v, "hold")])
    for obj, p, off in sc.settle:
        v = final.get((obj, p))
        if v is None:
            continue
        eb.key(obj, p, [(0, v + off, "soft"), (44, v)])
    er = Anim(f"S{k} reduced", 16)
    for (obj, p), v in final.items():
        er.key(obj, p, [(0, v, "hold")])
    er.key(sc.root, "opacity", [(0, 0.0, "lin"), (14, 1.0)])
    lf = Anim(f"S{k} leave fwd", 50)
    lf.key(sc.root, "opacity", [(0, 1.0, "hold"), (48, 0.0, "hold")])
    for i in sc.fade_leave:
        lf.key(i, "opacity", [(0, 1.0, "lin"), (10, 0.0)])
    for hid, hx in sc.hits:
        lf.key(hid, "x", [(0, hx + 2000, "hold")])
    lb = Anim(f"S{k} leave back", 44)
    lb.key(sc.root, "opacity", [(0, 1.0, "hold"), (42, 0.0, "hold")])
    lx, ly = 18.0, oy + 60
    lb.key(sc.mask, "x", [(0, ox, "fold"), (38, lx)])
    lb.key(sc.mask, "y", [(0, oy, "fold"), (38, ly)])
    lb.key(sc.mask, "scaleX", [(0, 26.0, "fold"), (38, 0.01)])
    lb.key(sc.mask, "scaleY", [(0, 26.0, "fold"), (38, 0.01)])
    lb.key(sc.mask, "rotation", [(0, 0.2, "fold"), (38, 1.1)])
    for p in ("x", "y", "scaleX", "scaleY", "rotation"):
        lb.tracks[(sc.edge, p)] = list(lb.tracks[(sc.mask, p)])
    lb.key(sc.edge, "opacity", [(0, 0.0, "lin"), (6, 1.0, "hold"), (34, 1.0, "lin"), (40, 0.0)])
    f = sc.fold
    lb.key(f["node"], "opacity", [(0, 0.0, "hold"), (2, 1.0, "hold"), (36, 1.0, "hold"), (37, 0.0)])
    lb.key(f["node"], "x", [(0, -260, "fold"), (36, W + 300)])
    lb.key(f["node"], "y", [(0, oy - 420, "fold"), (36, oy + 560)])
    lb.key(f["node"], "rotation", [(0, 2.4, "fold"), (36, 1.6)])
    lb.key(f["right"], "scaleX", [(0, -0.85, "fold"), (30, 1.0)])
    lb.key(f["left"], "scaleX", [(0, 0.35, "fold"), (30, 1.0)])
    for i in sc.fade_leave:
        lb.key(i, "opacity", [(0, 1.0, "lin"), (8, 0.0)])
    for hid, hx in sc.hits:
        lb.key(hid, "x", [(0, hx + 2000, "hold")])
    lr = Anim(f"S{k} leave reduced", 13)
    lr.key(sc.root, "opacity", [(0, 1.0, "lin"), (12, 0.0)])
    for hid, hx in sc.hits:
        lr.key(hid, "x", [(0, hx + 2000, "hold")])
    hd = Anim(f"S{k} hidden", 1)
    hd.key(sc.root, "opacity", [(0, 0.0, "hold")])
    for hid, hx in sc.hits:
        hd.key(hid, "x", [(0, hx + 2000, "hold")])
        for a in (sc.ef, eb, er):
            a.key(hid, "x", [(0, hx, "hold")])
    for obj, p, v in sc.extra_hidden:
        hd.key(obj, p, [(0, v, "hold")])
    sc.anims = {"EF": sc.ef, "EB": eb, "ER": er, "LF": lf, "LB": lb, "LR": lr, "H": hd, "I": sc.idle}
    return sc.anims


def metric_text(sc, num_kw, head_xy, head_w, head_align, unit_kw=None, dark_text=None, head_size=40,
                color=None):
    """Standard metric typography: hero number + unit, headline + support column. Returns elements."""
    k = sc.k
    c = color or (FOREST if sc.light else CREAM)
    hero_id = ID()
    nk = dict(num_kw)
    nk.setdefault("color", c)
    hero = hero_number(k, METRIC[k], row_id=hero_id, **nk)
    sc.fade_leave.append(hero_id)
    uk = dict(unit_kw or {})
    unit_id = ID()
    unit = text("Unit", [("unit", P(f"screen{k}Unit"))], font="dm", size=15, color=c, wght=500, ls=1.6,
                op=0.86, id=unit_id, wrap=True, **uk)
    hx, hy = head_xy
    rg, rid = word_reveal()
    head = text("Headline", [("Headline", P(f"screen{k}Headline"))], font="fr", size=head_size, color=c, wght=560,
                soft=60, lh=head_size * 1.06, align=head_align, lp=lp(), modifiers=[rg])
    sup_id = ID()
    sup = text("Support", [("Support", P(f"screen{k}Support"))], font="dm", size=16, color=c, wght=400, lh=23,
               align=head_align, op=0.82, lp=lp(), id=sup_id)
    col_id = ID()
    al = {"left": "topLeft", "center": "topCenter", "right": "topRight"}[head_align]
    colm = column("Copy", hx, hy, head_w, [head, sup], gap=12, align=al, id=col_id)
    # motion score
    sc.appear(hero_id, 10, 34, dy=30, base_y=num_kw["y"])
    sc.appear(unit_id, 40, 64, dy=10, base_y=uk.get("y", 0))
    reveal_keys(sc.ef, rid, 64, 98)
    sc.key(sup_id, "opacity", [(0, 0.0, "hold"), (82, 0.0, "outs"), (106, 0.82)])
    sc.settle.append((col_id, "y", 10.0))
    return hero, unit, colm
