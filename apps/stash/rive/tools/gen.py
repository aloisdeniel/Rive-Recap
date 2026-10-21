#!/usr/bin/env python3
"""Generate the Stash recap RML (data.rml, recap.rml, components.rml).

    python3 tools/gen.py && rive . --verify && rive inspect . --summary

The generated .rml files are ordinary, editable RML. This script exists because
the recap repeats a lot of structure (ten scene layers with the same state
graph, coins, digit windows, formula tokens); regenerate after editing it, or
edit the .rml directly and stop using the script -- both are supported.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rml import *  # noqa: E402,F401,F403
import rml  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 390, 844
TAU = 6.2831855

# =====================================================================
# Data: the single UserRecap view model
# =====================================================================
VM = "0:5000"
VMI = "0:5001"
_pid = [5001]
PROPS = {}      # name -> (id, kind, default)
PROP_ORDER = []


def prop(name, kind, default):
    _pid[0] += 1
    pid = f"0:{_pid[0]}"
    PROPS[name] = (pid, kind, default)
    PROP_ORDER.append(name)


def P(name):
    """absolute bind path to a UserRecap property"""
    return f"{VM}-{PROPS[name][0]}"


# --- the brief's schema, in its order -------------------------------
BRIEF = [
    ("userName", "string", "Alex"), ("year", "number", 2026),
    ("periodLabel", "string", "January 1–December 31, 2026"), ("locale", "string", "en-GB"),
    ("totalSaved", "number", 1248), ("deposits", "number", 96), ("goalsCompleted", "number", 3),
    ("roundupsSaved", "number", 148.5), ("activeMonths", "number", 10), ("largestGoalAmount", "number", 420),
    ("goalJars", "number", 5), ("personaIndex", "number", 0), ("personaName", "string", "Steady Builder"),
    ("personaDescription", "string", "Small steps, your own pace."), ("personaColor", "color", MINT),
    ("autoAdvanceSeconds", "number", 7), ("autoAdvanceEnabled", "bool", True), ("isPaused", "bool", False),
    ("reducedMotion", "bool", False), ("soundEnabled", "bool", False), ("currentScreen", "number", 1),
    ("screenProgress", "number", 0), ("shareIncludeName", "bool", False),
    ("shareIncludeSensitiveValues", "bool", False), ("continueLabel", "string", "Continue"),
    ("previousLabel", "string", "Previous"), ("pauseLabel", "string", "Pause"), ("playLabel", "string", "Play"),
    ("shareLabel", "string", "Share"), ("replayLabel", "string", "Replay"),
    ("introHeadline", "string", "Your 2026 on Stash"), ("introSupport", "string", "A year, uniquely yours."),
    ("summaryHeadline", "string", "A little year. A lot of you."),
    ("summarySupport", "string", "Take a piece of your year with you."),
    ("emptyHeadline", "string", "Every story starts somewhere."),
    ("emptySupport", "string", "Your next chapter is waiting."), ("personaLabel", "string", "Your personal style"),
] + [(f"showScreen{k}", "bool", True) for k in range(1, 11)] + [
    ("screen2Headline", "string", "Little by little, you built this."),
    ("screen2Support", "string", "Your deposits, on your terms."), ("screen2Unit", "string", "EUR saved"),
    ("screen3Headline", "string", "Small moves added up."),
    ("screen3Support", "string", "Every contribution had a place."), ("screen3Unit", "string", "deposits"),
    ("screen4Headline", "string", "You made room for a yes."),
    ("screen4Support", "string", "Plans turned into possibilities."), ("screen4Unit", "string", "goals completed"),
    ("screen5Headline", "string", "Change made a difference."),
    ("screen5Support", "string", "Optional roundups found their own rhythm."),
    ("screen5Unit", "string", "EUR from roundups"),
    ("screen6Headline", "string", "A habit at your pace."),
    ("screen6Support", "string", "Some months looked different. That's okay."),
    ("screen6Unit", "string", "active months"),
    ("screen7Headline", "string", "A plan became real."),
    ("screen7Support", "string", "Your completed goal: weekend away."), ("screen7Unit", "string", "EUR goal funded"),
    ("screen8Headline", "string", "A little space for what matters."),
    ("screen8Support", "string", "Your plans each got a place."), ("screen8Unit", "string", "goal jars"),
    ("currencyCode", "string", "EUR"), ("completedGoalName", "string", "Weekend away"),
]
for n, k, d in BRIEF:
    prop(n, k, d)

# --- adapter additions (documented in README) ------------------------
ADAPTER = [
    # host-owned inputs
    ("navNext", "trigger", None), ("navPrev", "trigger", None), ("togglePause", "trigger", None),
    ("replay", "trigger", None), ("isSharing", "bool", False), ("appBackgrounded", "bool", False),
    ("personaAutoMap", "bool", True),
    # written by the director / state machine (read-only for hosts)
    ("_navDir", "number", 1), ("_visibleCount", "number", 10), ("_visibleIndex", "number", 1),
    ("_canGoBack", "bool", False), ("_canGoNext", "bool", True), ("_isSummary", "bool", False),
    ("_emptyState", "bool", False), ("_personaKnown", "bool", True), ("_personaSlot", "number", 0),
    ("_frozen", "bool", False), ("_holding", "bool", False), ("_finished", "bool", False),
    ("_pauseButtonLabel", "string", "Pause"), ("_focus", "number", 0),
    ("_chromeColor", "color", CREAM), ("_chromeOnColor", "color", INK),
    ("_stageX", "number", 0), ("_stageY", "number", 0), ("_stageScale", "number", 1),
    ("_viewW", "number", W), ("_viewH", "number", H), ("_chromeInset", "number", 0),
    ("_handoffFwd", "trigger", None), ("_handoffBack", "trigger", None), ("_coinNudge", "trigger", None),
    # event mirrors: the CLI cannot observe Rive events, so each event also
    # fires one of these triggers on the same state/listener for verification
    ("_evtScreenChanged", "trigger", None), ("_evtRecapFinished", "trigger", None),
    ("_evtShareTapped", "trigger", None),
] + [(f"_count{k}", "number", 0) for k in range(1, 11)]
for n, k, d in ADAPTER:
    prop(n, k, d)

# fixtures stored as extra instances (the host binds exactly one)
FIX_ZERO = {"userName": "Sam", "totalSaved": 0, "deposits": 0, "goalsCompleted": 0, "roundupsSaved": 0,
            "activeMonths": 0, "largestGoalAmount": 0, "goalJars": 0, "personaName": "", "personaDescription": "",
            "personaAutoMap": False,
            **{f"showScreen{k}": False for k in range(2, 10)}}
FIX_EXTREME = {"userName": "Maximiliana Alexandrina Featherstonehaugh-Wolfeschlegel",
               "totalSaved": 12345678.9, "deposits": 48213, "goalsCompleted": 248, "roundupsSaved": 98765.43,
               "activeMonths": 12, "largestGoalAmount": 2500000, "goalJars": 64, "personaIndex": 2,
               "screen2Headline": "Little by little, bit by bit, you really built all of this.",
               "screen2Support": "Every one of your deposits, entirely on your own terms.",
               "screen2Unit": "EUR saved across all of your jars",
               "screen5Unit": "EUR from optional roundups this year",
               "screen3Headline": "Small, steady moves added up to something big.",
               "summaryHeadline": "A little year. A lot of you. Truly, a lot of you.",
               "continueLabel": "Continue to the next chapter"}


def write_fixtures():
    import json
    d = os.path.join(ROOT, "fixtures")
    os.makedirs(d, exist_ok=True)
    base = {n: PROPS[n][2] for n, _, _ in BRIEF}
    base["personaColor"] = "#BFF4D4"
    for name, over in (("sample", {}), ("zero-user", FIX_ZERO), ("extreme-long-copy", FIX_EXTREME)):
        data = dict(base)
        data.update(over)
        with open(os.path.join(d, f"{name}.json"), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def vm_xml():
    props, inst = [], {"Default": [], "ZeroUser": [], "Extreme": []}
    for n in PROP_ORDER:
        pid, kind, d = PROPS[n]
        tag = {"string": "String", "number": "Number", "bool": "Boolean", "color": "Color",
               "trigger": "Trigger"}[kind]
        props.append(el(f"ViewModelProperty{tag}", {"name": n, "id": pid}))
        for iname, over in (("Default", {}), ("ZeroUser", FIX_ZERO), ("Extreme", FIX_EXTREME)):
            v = over.get(n, d)
            if kind == "trigger":
                inst[iname].append(el("ViewModelInstanceTrigger", {"viewModelPropertyId": pid}))
            else:
                inst[iname].append(el(f"ViewModelInstance{tag}", {"propertyValue": v, "viewModelPropertyId": pid}))
    ids = {"Default": VMI, "ZeroUser": "0:5900", "Extreme": "0:5901"}
    insts = [el("ViewModelInstance", {"exports": True, "name": k, "id": ids[k]}, v) for k, v in inst.items()]
    return el("ViewModel", {"defaultInstanceId": VMI, "name": "UserRecap", "id": VM}, props + insts)


# =====================================================================
# Assets, converters
# =====================================================================
F_RUBIK, F_NUNITO = "0:4001", "0:4002"
SCRIPTS = {}  # name -> id
for i, (name, f, mod) in enumerate([("numfmt", "numfmt.luau", True),
                                     ("director", "scripts/director.luau", False),
                                     ("progress", "scripts/progress.luau", False),
                                     ("fmtCount", "scripts/fmt_count.luau", False),
                                     ("fmtMoney", "scripts/fmt_money.luau", False),
                                     ("b2one", "scripts/b2one.luau", False),
                                     ("b2zero", "scripts/b2zero.luau", False),
                                     ("b2dim", "scripts/b2dim.luau", False),
                                     ("fmtCountExact", "scripts/fmt_count_exact.luau", False),
                                     ("fmtMoneyExact", "scripts/fmt_money_exact.luau", False)]):
    SCRIPTS[name] = (f"0:{4010 + i}", f, mod)

CONV = []          # root converter xml
C = {}             # converter name -> id


def conv_script(name, script):
    cid = nid()
    CONV.append(el("ScriptedDataConverter", {"scriptAssetId": SCRIPTS[script][0], "name": name, "id": cid}))
    C[name] = cid
    return cid


def conv_formula(name, expr):
    cid = nid()
    toks = Formula(expr, P).emit()
    CONV.append(el("DataConverterFormula", {"name": name, "id": cid}, toks))
    C[name] = cid
    return cid


def conv_group(name, members):
    cid = nid()
    CONV.append(el("DataConverterGroup", {"name": name, "id": cid},
                   [el("DataConverterGroupItem", {"converterId": m}) for m in members]))
    C[name] = cid
    return cid


conv_script("fmtCount", "fmtCount")
conv_script("fmtMoney", "fmtMoney")
conv_script("b2one", "b2one")
conv_script("b2zero", "b2zero")
conv_script("b2dim", "b2dim")
conv_script("fmtCountExact", "fmtCountExact")
conv_script("fmtMoneyExact", "fmtMoneyExact")
C["not"] = nid()
CONV.append(el("DataConverterBooleanNegate", {"name": "Not", "id": C["not"]}))
C["toStr0"] = nid()
CONV.append(el("DataConverterToString", {"decimals": 0, "round": True, "name": "Whole number", "id": C["toStr0"]}))

MONEY_SCENES = {2, 5, 7}


def hero_conv(k):
    """count-up: stat x _count{k}, then localized formatting"""
    key = f"hero{k}"
    if key not in C:
        f = conv_formula(f"countUp{k}", f"in * $_count{k}")
        conv_group(key, [f, C["fmtMoney" if k in MONEY_SCENES else "fmtCount"]])
    return C[key]


# =====================================================================
# Text
# =====================================================================
FONTS = {"rubik": (F_RUBIK, "Rubik"), "nunito": (F_NUNITO, "Nunito Sans")}
WEIGHT_NAME = {500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def tstyle(font="nunito", size=16, color=CREAM, weight=700, lh=-1, ls=0, cbind=None, outline=None, sid=None):
    fid, fam = FONTS[font]
    sid = sid or nid()
    ch = []
    if outline:
        ch.append(stroke(outline[0], outline[1], name="Outline"))
    ch.append(fill(color, bind=bind(cbind, 37) if cbind else None))
    ch.append(el("TextStyleAxis", {"tag": 2003265652, "axisValue": weight, "name": "wght"}))
    return sid, el("TextStylePaint", {"fontSize": size, "fontAssetId": fid, "familyName": fam,
                                      "styleName": WEIGHT_NAME.get(weight, "Custom"), "lineHeight": lh,
                                      "letterSpacing": ls, "name": f"{fam} {weight}", "id": sid}, ch)


def text(name, x, y, runs, width=None, align="left", ox=0.0, oy=0.0, sizing=None, overflow=None,
         tid=None, extra=None, wrap=None, opacity=None, height=None, valign=None):
    """runs: list of dicts {style: kwargs for tstyle, text, path, conv}"""
    tid = tid or nid()
    styles, rs = [], []
    for r in runs:
        sid, sx = tstyle(**r["style"])
        styles.append(sx)
        b = bind(P(r["path"]), 268, r.get("conv")) if r.get("path") else None
        rs.append(el("TextValueRun", {"styleId": sid, "text": r.get("text", ""), "name": r.get("name", "Run")},
                     [b] if b else None))
    if sizing is None:
        sizing = "autoHeight" if width else "autoWidth"
    a = {"x": x, "y": y, "width": width, "height": height, "sizingValue": sizing, "alignValue": align,
         "originX": ox, "originY": oy, "overflowValue": overflow, "wrapValue": wrap, "opacity": opacity,
         "verticalAlignValue": valign, "name": name, "id": tid}
    return el("Text", a, styles + rs + list(extra or []))


def run(path=None, text_="", conv=None, **style):
    return {"style": style, "text": text_, "path": path, "conv": conv}


def word_cascade(rid):
    """modifier group that hides words until its range is swept (keyed by scenes)"""
    return el("TextModifierGroup", {"modifyOpacity": True, "modifyTranslation": True, "invertOpacity": True,
                                     "opacity": 0, "y": 26, "name": "Word cascade"},
              [el("TextModifierRange", {"unitsValue": 2, "modifyFrom": 1.05, "modifyTo": 1.0,
                                        "falloffFrom": 1.45, "falloffTo": 1.0, "name": "Sweep", "id": rid})])


# =====================================================================
# Art primitives
# =====================================================================
COIN_AB = "0:3000"


def coin(name, x, y, s=1.0, rot=0.0, cid=None, opacity=None):
    """placement of the reusable Coin component (origin at its centre)"""
    return el("NestedArtboard", {"artboardId": COIN_AB, "x": x, "y": y, "scaleX": s, "scaleY": s,
                                 "rotation": rot, "opacity": opacity, "name": name, "id": cid or nid()})


def coin_art():
    """Coin component artwork: chunky outlined bevelled coin, ~64 units wide"""
    return [
        shape("Shine", [ellipse(44, 44)], [stroke("CCFFFFFF", 3.2, trim=el("TrimPath", {"start": 0.58, "end": 0.74}))]),
        shape("Star", [star(22, 22, 5, 0.5, 1.5)], [fill(GOLD_D)], y=1),
        shape("Star Emboss", [star(22, 22, 5, 0.5, 1.5)], [fill(GOLD_L)], y=-0.5, opacity=0.9),
        shape("Face", [ellipse(44, 44)], [fill(grad=lin([(0, GOLD_L), (1, GOLD)], -12, -22, 12, 22)),
                                          stroke(GOLD_D, 2.5)]),
        shape("Rim", [ellipse(58, 58)], [fill(GOLD), stroke(INK, 3.5)]),
        shape("Edge", [ellipse(58, 58)], [fill(GOLD_D), stroke(INK, 3.5)], y=4.5),
    ]


def sparkle(name, x, y, s=16, color=CREAM, sid=None, opacity=None, rot=0):
    return shape(name, [star(s, s, 4, 0.28, 0)], [fill(color)], x=x, y=y, sid=sid or nid(),
                 opacity=opacity, rot=rot)


def burst(name, x, y, r0=34, r1=50, n=8, color=PEACH, th=4, bid=None, opacity=None, sweep=TAU, start=0):
    """tick starburst: short radial strokes (one shape, several paths)"""
    paths = []
    for i in range(n):
        a = start + sweep * (i / n if sweep >= TAU - 0.01 else i / max(1, n - 1))
        paths.append(poly([(math.cos(a) * r0, math.sin(a) * r0), (math.cos(a) * r1, math.sin(a) * r1)],
                          closed=False, name=f"Tick {i}"))
    return shape(name, paths, [stroke(color, th)], x=x, y=y, sid=bid or nid(), opacity=opacity)




def digit_window(name, x, y, w, h, src, count, place, places, size, color, lh, frame=True):
    """one mechanical tally window: a 0-9 strip scrolled by a formula, clipped.

    pos = (value*count / 10^place) % 10, floored for every place but the ones,
    so the ones digit rolls continuously while higher digits tick over. Values
    that do not fit the window count show a star instead of wrapping."""
    lim = 10 ** places
    if place == 0:
        pos = f"((in * $_count{count}) % 10)"
    else:
        pos = f"(floor(in * $_count{count} / {10 ** place}) % 10)"
    over = f"min(1, floor(in * $_count{count} / {lim}))"
    expr = f"0 - ({pos} * (1 - {over}) + 11 * {over}) * {lh}"
    cid = conv_formula(f"{name} roll", expr)
    clip_id = nid()
    glyphs = []
    for i, g in enumerate("01234567890+"):
        glyphs.append(text(f"{name} {i}", 0, i * lh, [run(None, g, font="rubik", size=size, color=color, weight=900)],
                           ox=0.5, oy=0.5))
    sid = nid()
    strip_node = el("Node", {"name": f"{name} roll", "id": sid}, [bind(P(src), 14, cid)] + glyphs)
    parts = [
        el("Node", {"name": f"{name} reel", "id": nid()},
           [el("ClippingShape", {"sourceId": clip_id, "name": "Window clip"}), strip_node]),
        shape(f"{name} mask", [rect(w, h, 6)], [], sid=clip_id),
    ]
    if frame:
        parts.insert(0, shape(f"{name} glass", [rect(w - 6, h * 0.4, 4, y=-h * 0.24)], [fill("33FFFFFF")]))
        parts.append(shape(f"{name} frame", [rect(w, h, 7)], [fill(CREAM), stroke(INK, 3.5)]))
    return el("Node", {"x": x, "y": y, "name": name, "id": nid()}, parts)


# ---------------------------------------------------------------------
# The motif: toy savings machine (mint jar on a tally plinth, coin path)
# origin = bottom centre of the plinth
# ---------------------------------------------------------------------
M = {}  # ids of motif parts


def machine():
    M["root"] = nid()
    M["label"] = nid()
    M["pile"] = nid()
    M["tyear"] = nid()
    M["tsaved"] = nid()
    M["lid"] = nid()
    M["pathcoin"] = nid()
    M["jar"] = nid()
    M["bob"] = nid()
    jar_clip = nid()
    label_clip = nid()
    # pile: rises with scene 2's count, scaled by how much was saved
    pile_conv = conv_formula("Jar fill", "150 - in * 128 * min(1, $totalSaved / 60)")
    pile_coins = []
    for i, (cx, cy, r) in enumerate([(-58, -94, 0.4), (-20, -104, -0.3), (22, -98, 0.8), (60, -92, -0.6),
                                     (-40, -122, 1.2), (4, -128, -1.0), (44, -120, 0.2), (-8, -150, 0.5)]):
        pile_coins.append(coin(f"Pile coin {i}", cx, cy + 8, 0.72, r))
    pile = el("Node", {"name": "Coin pile", "id": M["pile"], "y": 150},
              [bind(P("_count2"), 14, pile_conv)] + pile_coins +
              [shape("Pile body", [rect(176, 200, 0, y=-6, oy=0)], [fill(grad=lin([(0, GOLD), (1, GOLD_D)], 0, -10, 0, 120))])])
    jar_inner = el("Node", {"name": "Jar inside", "id": nid()},
                   [el("ClippingShape", {"sourceId": jar_clip, "name": "Jar clip"}), pile])
    label = el("Node", {"name": "Wordmark label", "x": 0, "y": -176, "id": nid()}, [
        el("Node", {"name": "Label reveal", "id": M["label"]}, [
            el("ClippingShape", {"sourceId": label_clip, "name": "Label clip"}),
            text("Wordmark", 0, 0, [run(None, "Stash", font="rubik", size=27, color=GRAPE, weight=900, ls=-0.5)],
                 ox=0.5, oy=0.5),
            sparkle("Label spark", 44, -12, 10, PEACH),
        ]),
        shape("Label clip shape", [rect(116, 44, 22)], [], sid=label_clip),
        shape("Label plate", [rect(116, 44, 22)], [fill(CREAM), stroke(INK, 3.5)]),
    ])
    tally = []
    for tid_, src, cnt, nm in ((M["tyear"], "year", 1, "Year tally"), (M["tsaved"], "totalSaved", 2, "Saved tally")):
        wins = [digit_window(f"{nm} {p}", -60 + (3 - p) * 40, -36, 32, 42, src, cnt, p, 4, 26, INK, 34)
                for p in range(4)]
        tally.append(el("Node", {"name": nm, "id": tid_, "opacity": 1 if cnt == 1 else 0}, wins))
    track_path = [(112, -60), ("c", 124, -170, -1.57, 46), ("c", 112, -286, -2.0, 34),
                  ("c", 66, -340, 3.0, 26), (26, -326)]
    parts = [
        el("Node", {"name": "Path coin", "id": M["pathcoin"], "x": 124, "y": -170}, [coin("Riding coin", 0, 0, 0.62)]),
        shape("Coin path rail", [poly(track_path, closed=False)], [stroke(CREAM, 4, name="Rail shine")], x=-2, y=-3,
              opacity=0.55),
        shape("Coin path", [poly(track_path, closed=False)], [stroke(INK, 24), stroke(MINT, 15, name="Track")]),
        el("Node", {"name": "Lid", "id": M["lid"], "y": -300}, [
            shape("Slot", [rect(56, 9, 4.5, y=-16)], [fill(INK)]),
            shape("Lid shine", [rect(120, 6, 3, y=-6)], [fill("55FFFFFF")]),
            shape("Lid cap", [rect(152, 32, 13)], [fill(grad=lin([(0, GRAPE_L), (1, GRAPE)], 0, -16, 0, 16)), stroke(INK, 4)]),
        ]),
        shape("Neck", [rect(128, 24, 8, y=-280)], [fill(alpha(MINT, 0.6)), stroke(INK, 4)]),
        label,
        shape("Glass shine", [poly([(-64, -110), (-64, -224), ("c", -54, -246, -0.6, 10), (-40, -252)], closed=False)],
              [stroke("AAFFFFFF", 7)]),
        shape("Glass", [rect(178, 198, 46, y=-174)], [fill(alpha(MINT, 0.34)), stroke(INK, 4.5)]),
        jar_inner,
        shape("Jar clip shape", [rect(170, 190, 42, y=-174)], [], sid=jar_clip),
        shape("Jar back", [rect(178, 198, 46, y=-174)], [fill(alpha(MINT_D, 0.55))]),
    ]
    jar = el("Node", {"name": "Jar", "id": M["jar"]}, parts)
    plinth = [
        sparkle("Rivet L", -100, -38, 15, PEACH), sparkle("Rivet R", 100, -38, 15, PEACH),
    ] + tally + [
        shape("Tally bezel", [rect(170, 54, 12, y=-36)], [fill(INK)]),
        shape("Plinth lip", [rect(248, 20, 10, y=-72)], [fill(GRAPE_L), stroke(INK, 4)]),
        shape("Plinth", [rect(232, 74, 20, y=-37)], [fill(grad=lin([(0, GRAPE), (1, GRAPE_D)], 0, -70, 0, 0)), stroke(INK, 4)]),
        shape("Foot L", [rect(40, 14, 5, x=-78, y=4)], [fill(INK)]),
        shape("Foot R", [rect(40, 14, 5, x=78, y=4)], [fill(INK)]),
        shape("Machine shadow", [ellipse(260, 26, y=10)], [fill("33241B3C")]),
    ]
    bob = el("Node", {"name": "Machine bob", "id": M["bob"]}, [jar] + plinth)
    return el("Node", {"name": "Toy machine (motif)", "id": M["root"], "x": 195, "y": 690}, [bob])


# per-scene poses of the machine: x, y, scale, rotation, opacity
POSES = {
    1: (195, 712, 1.0, 0.0, 1), 2: (195, 724, 1.04, 0.0, 1), 3: (70, 742, 0.42, -0.08, 1),
    4: (334, 312, 0.34, 0.12, 1), 5: (330, 738, 0.4, 0.06, 1), 6: (300, 1010, 0.9, 0.18, 1),
    7: (195, 742, 0.86, 0.0, 1), 8: (195, 1060, 0.9, 0.0, 1), 9: (195, 806, 0.72, 0.0, 1),
    10: (195, 1080, 0.8, 0.0, 0),
}


# =====================================================================
# Scene framework
# =====================================================================
FWD_BASE = 26     # frame at which an incoming (forward) panel has landed
BACK_BASE = 6
ENTER_LEN = 132   # 2.2 s: entrance + resolve; the director starts dwell after this
IDLE_LEN = 240


class Scene:
    def __init__(self, k, bg, dark):
        self.k = k
        self.bg = bg
        self.dark = dark
        self.items = []
        self.keys = []      # (obj, prop, kfs relative to base, kind)
        self.idle = []      # (obj, prop, kfs, kind) looped over IDLE_LEN
        self.root = nid()
        self.content = nid()
        self.sem = []       # SemanticData ids hidden while the scene is not current
        self.ink = INK if not dark else CREAM

    def key(self, obj, prop, kfs, kind="double"):
        self.keys.append((obj, prop, kfs, kind))

    def pop(self, obj, at, s0=0.4, peak=1.1, dur=22, op=True):
        """scale pop with overshoot and settle"""
        self.key(obj, "scaleX", [(at, s0, "out"), (at + dur * 0.55, peak, "soft"), (at + dur, 1.0)])
        self.key(obj, "scaleY", [(at, s0, "out"), (at + dur * 0.55, peak, "soft"), (at + dur, 1.0)])
        if op:
            self.key(obj, "opacity", [(at, 0, "linear"), (at + 6, 1)])

    def rise(self, obj, at, dy=18, dur=20, y=0):
        self.key(obj, "y", [(at, y + dy, "out"), (at + dur, y)])
        self.key(obj, "opacity", [(at, 0, "soft"), (at + dur * 0.7, 1)])

    def loop(self, obj, prop, kfs, kind="double"):
        self.idle.append((obj, prop, kfs, kind))

    def finals(self):
        out = {}
        for obj, prop, kfs, kind in self.keys:
            out[(obj, prop)] = (kfs[-1][1], kind)
        return out

    def starts(self):
        out = {}
        for obj, prop, kfs, kind in self.keys:
            out.setdefault((obj, prop), (kfs[0][1], kind))
        return out


SCENES = {}


def sem(sc, role="text", label=None, value=None, heading=0, label_conv=None, value_conv=None):
    sid = nid()
    sc.sem.append(sid)
    ch = []
    if label:
        ch.append(bind(P(label), 983, label_conv))
    if value:
        ch.append(bind(P(value), 984, value_conv))
    return el("SemanticData", {"role": role, "headingLevel": heading or None, "isHidden": True,
                               "name": "Semantics", "id": sid}, ch)


def scene_text(sc, hx, hy, hw, halign="left", size=34, sup=None, color=None, hl_color=None):
    """headline (word cascade) + support line, the stable copy area"""
    color = color or sc.ink
    rid = nid()
    hid = nid()
    head_path = {1: "introHeadline", 10: "summaryHeadline"}.get(sc.k, f"screen{sc.k}Headline")
    ox = {"left": 0, "center": 0.5, "right": 1}[halign]
    # two-line slot: copy that needs a third line (e.g. +40% translations) shrinks
    # the headline only, never the hero value, labels or controls
    sc.items.append(text(f"S{sc.k} headline", hx, hy, [run(head_path, "", font="rubik", size=size,
                                                            color=hl_color or color, weight=800, lh=size * 1.08)],
                         width=hw, align=halign, ox=ox, tid=hid, extra=[sem(sc, "text", head_path, heading=1), word_cascade(rid)], sizing="fixed",
                         height=round(size * 1.08 * 2 + 4), overflow="fitFontSize", valign="top"))
    sc.key(rid, "modifyFrom", [(30, -0.45, "soft"), (74, 1.05)])
    sc.key(rid, "falloffFrom", [(30, -0.05, "soft"), (74, 1.45)])
    if sup:
        sx, sy, sw, salign = sup
        sid = nid()
        sup_path = {1: "introSupport", 10: "summarySupport"}.get(sc.k, f"screen{sc.k}Support")
        sc.items.append(text(f"S{sc.k} support", sx, sy, [run(sup_path, "", font="nunito", size=17,
                                                               color=color, weight=600, lh=23)],
                             width=sw, align=salign, ox={"left": 0, "center": 0.5, "right": 1}[salign], tid=sid,
                             extra=[sem(sc, "text", sup_path)]))
        sc.rise(sid, 62, 14, 26, y=sy)
    return hid


def hero_number(sc, x, y, size, color, align="center", width=350, outline=None, unit=None, unit_color=None):
    """bound hero value (counts up via _count{k}) + unit label"""
    k = sc.k
    src = {2: "totalSaved", 3: "deposits", 4: "goalsCompleted", 5: "roundupsSaved", 6: "activeMonths",
           7: "largestGoalAmount", 8: "goalJars"}[k]
    nid_ = nid()
    hid = nid()
    ox = {"left": 0, "center": 0.5, "right": 1}[align]
    t = text(f"S{k} hero value", 0, 0, [run(src, "0", conv=hero_conv(k), font="rubik", size=size, color=color,
                                              weight=900, lh=size * 1.02, ls=-1, outline=outline)],
             width=width, align=align, ox=ox, oy=0.5, sizing="fixed", height=size * 1.15, overflow="fitFontSize",
             wrap="noWrap", valign="middle", tid=hid)
    exact = C["fmtMoneyExact" if k in MONEY_SCENES else "fmtCountExact"]
    sc.items.append(el("Node", {"name": f"S{k} hero", "x": x, "y": y, "id": nid_},
                       [sem(sc, "text", f"screen{k}Unit", value=src, value_conv=exact), t]))
    sc.pop(nid_, 4, 0.55, 1.08, 26)
    uid = None
    if unit:
        ux, uy, uw, ualign = unit
        uid = nid()
        sc.items.append(text(f"S{k} unit", ux, uy, [run(f"screen{k}Unit", "", font="nunito", size=19,
                                                        color=unit_color or sc.ink, weight=800, lh=24)],
                             width=uw, align=ualign, ox={"left": 0, "center": 0.5, "right": 1}[ualign], tid=uid))
        sc.rise(uid, 22, 12, 20, y=uy)
    return nid_


def bg_panel(sc):
    """full-bleed scene backdrop with a chunky outlined top edge (what the spring pushes)"""
    return [
        shape(f"S{sc.k} panel edge", [rect(4000, 3200, 0, y=-140, oy=0)], [fill(sc.bg)]),
        shape(f"S{sc.k} panel lip", [rect(4000, 10, 0, y=-150, oy=0)], [fill(INK)]),
    ]


def deco_bg(sc, seed, color, n=7):
    """quiet background starbursts / dots: mid-ground depth"""
    import random
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(20, 370), rnd.uniform(90, 720)
        s = rnd.uniform(8, 16)
        sid = nid()
        out.append(sparkle(f"S{sc.k} twinkle {i}", x, y, s, color, sid=sid, opacity=0.55))
        ph = rnd.randint(0, 200)
        sc.loop(sid, "scaleX", [(0, 1.0, "soft"), ((ph % 120) + 40, 0.55, "soft"), (IDLE_LEN, 1.0)])
        sc.loop(sid, "scaleY", [(0, 1.0, "soft"), ((ph % 120) + 40, 0.55, "soft"), (IDLE_LEN, 1.0)])
    return out


POSES.update({3: (195, 756, 0.34, 0.0, 1), 4: (195, 756, 0.3, -0.04, 1), 5: (195, 756, 0.3, 0.04, 1),
              6: (195, 984, 0.9, 0.0, 1)})
BG = {1: GRAPE_D, 2: GRAPE, 3: CREAM, 4: MINT, 5: CREAM, 6: INK, 7: PEACH, 8: MINT, 9: GRAPE, 10: GRAPE_D}
DARK = {1, 2, 6, 9, 10}


def new_scene(k):
    sc = Scene(k, BG[k], k in DARK)
    SCENES[k] = sc
    return sc


# ---------------------------------------------------------------- 1
def scene1():
    sc = new_scene(1)
    tag = nid()
    sc.items.append(el("Node", {"name": "Name tag", "x": 24, "y": 96, "id": tag}, [
        sem(sc, "text", "userName"),
        text("Name", 40, 0, [run("userName", "", font="nunito", size=18, color=MINT, weight=800, lh=22)],
             width=280, sizing="fixed", height=24, overflow="ellipsis", wrap="noWrap", oy=0.5, valign="middle"),
        sparkle("Tag star", 15, 0, 18, GRAPE),
        shape("Tag plate", [ellipse(32, 32, x=15)], [fill(MINT), stroke(INK, 3)]),
    ]))
    sc.pop(tag, 0, 0.6, 1.08, 20)
    scene_text(sc, 24, 128, 342, "left", 46, sup=(24, 236, 330, "left"), color=CREAM)
    pid = nid()
    sc.items.append(text("Period", 24, 268, [run("periodLabel", "", font="nunito", size=15, color=MINT, weight=700, lh=20)],
                         width=330, tid=pid, extra=[sem(sc, "text", "periodLabel")]))
    sc.rise(pid, 70, 10, 24, y=268)
    sb = nid()
    sc.items.append(burst("Machine burst", 195, 420, 128, 150, 18, alpha(PEACH, 0.8), 5, bid=sb))
    sc.key(sb, "rotation", [(30, -0.4, "out"), (80, 0)])
    sc.key(sb, "opacity", [(30, 0, "linear"), (44, 1)])
    sc.loop(sb, "rotation", [(0, 0), (IDLE_LEN, 0.3491)])
    sc.items += deco_bg(sc, 11, MINT)
    # the machine drops in and lands with squash; the wordmark rises through the label window
    sc.key(M["bob"], "y", [(0, -820, "drop"), (24, 0, "out"), (31, -30, "in"), (38, 0, "out"), (43, -7, "in"), (47, 0)])
    sc.key(M["bob"], "scaleY", [(0, 1.06, "linear"), (24, 1.06, "out"), (28, 0.84, "soft"), (36, 1.05, "soft"), (44, 1.0)])
    sc.key(M["bob"], "scaleX", [(0, 0.96, "linear"), (24, 0.96, "out"), (28, 1.12, "soft"), (36, 0.97, "soft"), (44, 1.0)])
    sc.key(M["label"], "y", [(40, 50, "out"), (64, -4, "soft"), (72, 0)])
    sc.key(M["pathcoin"], "x", [(46, 114, "linear"), (60, 124, "linear"), (72, 112, "linear"), (82, 66, "linear"), (90, 26)])
    sc.key(M["pathcoin"], "y", [(46, -70, "linear"), (60, -170, "linear"), (72, -290, "linear"), (82, -352, "linear"), (90, -330)])
    sc.key(M["pathcoin"], "scaleX", [(46, 0, "out"), (52, 1, "linear"), (88, 1, "in"), (96, 0)])
    sc.key(M["pathcoin"], "scaleY", [(46, 0, "out"), (52, 1, "linear"), (88, 1, "in"), (96, 0)])
    sc.key(M["pathcoin"], "rotation", [(46, 0, "linear"), (92, -9)])
    sc.key(M["lid"], "y", [(92, -300, "out"), (96, -306, "soft"), (104, -300)])
    # idle: the coin keeps riding the path every 4 seconds
    sc.loop(M["pathcoin"], "x", [(0, 114, "hold"), (150, 114, "linear"), (166, 124, "linear"), (180, 112, "linear"), (192, 66, "linear"), (200, 26, "hold"), (IDLE_LEN, 114)])
    sc.loop(M["pathcoin"], "y", [(0, -70, "hold"), (150, -70, "linear"), (166, -170, "linear"), (180, -290, "linear"), (192, -352, "linear"), (200, -330, "hold"), (IDLE_LEN, -70)])
    sc.loop(M["pathcoin"], "scaleX", [(0, 0, "hold"), (150, 0, "out"), (156, 1, "linear"), (196, 1, "in"), (204, 0, "hold"), (IDLE_LEN, 0)])
    sc.loop(M["pathcoin"], "scaleY", [(0, 0, "hold"), (150, 0, "out"), (156, 1, "linear"), (196, 1, "in"), (204, 0, "hold"), (IDLE_LEN, 0)])
    return sc


# ---------------------------------------------------------------- 2
def scene2():
    sc = new_scene(2)
    scene_text(sc, 24, 86, 330, "left", 36, sup=(195, 294, 330, "center"), color=CREAM)
    hero_number(sc, 195, 210, 80, PEACH, outline=(INK, 8), unit=(195, 254, 340, "center"), unit_color=MINT)
    for side, (bx, start) in enumerate(((195 - 150, 2.4), (195 + 150, -0.7))):
        b = nid()
        sc.items.append(burst(f"Hero ticks {side}", bx, 210, 14, 28, 3, PEACH, 4.5, bid=b, sweep=1.4, start=start))
        sc.pop(b, 26, 0.2, 1.3, 18)
    # chute that feeds the jar
    chute = nid()
    sc.items.append(el("Node", {"name": "Chute", "id": chute}, [
        shape("Chute mouth", [ellipse(40, 14, x=198, y=380)], [fill(INK)]),
        shape("Chute stripe", [poly([(440, 360), (280, 360), ("c", 216, 364, 1.25, 22), (198, 378)], closed=False)],
              [stroke(MINT, 6)], y=-6),
        shape("Chute", [poly([(440, 360), (280, 360), ("c", 216, 364, 1.25, 22), (198, 378)], closed=False)],
              [stroke(INK, 40, cap="butt"), stroke(GRAPE_L, 30, cap="butt", name="Pipe")]),
    ]))
    sc.key(chute, "x", [(0, 220, "out"), (26, 0)])
    # a bounded pool of coins drops into the jar, in time with the count
    import random
    rnd = random.Random(2)
    for i in range(7):
        c = nid()
        sc.items.insert(0, el("Node", {"name": f"Drop coin {i}", "id": c, "x": 300, "y": 352, "opacity": 0},
                              [coin(f"Drop coin {i} art", 0, 0, 0.7)]))
        t0 = 18 + i * 6
        tx = 195 + rnd.uniform(-48, 48)
        ty = 560 - i * 4
        sc.key(c, "opacity", [(t0, 0, "hold"), (t0 + 1, 1, "linear"), (t0 + 30, 1, "linear"), (t0 + 38, 0)])
        sc.key(c, "x", [(t0, 320, "linear"), (t0 + 7, 198, "soft"), (t0 + 22, tx)])
        sc.key(c, "y", [(t0, 360, "linear"), (t0 + 7, 382, "drop"), (t0 + 20, ty, "out"), (t0 + 25, ty - 14, "in"), (t0 + 30, ty)])
        sc.key(c, "rotation", [(t0, 0, "linear"), (t0 + 30, rnd.choice([-1, 1]) * rnd.uniform(4, 9))])
    sc.items += deco_bg(sc, 22, MINT, 6)
    # glass glint sweeps once the jar has filled
    sc.key(M["lid"], "y", [(88, -300, "out"), (92, -308, "soft"), (100, -300)])
    sc.loop(M["pathcoin"], "scaleX", [(0, 0, "hold"), (IDLE_LEN, 0)])
    sc.loop(M["pathcoin"], "scaleY", [(0, 0, "hold"), (IDLE_LEN, 0)])
    return sc


# ---------------------------------------------------------------- 3
def scene3():
    sc = new_scene(3)
    scene_text(sc, 195, 88, 340, "center", 36, sup=(195, 452, 320, "center"), color=INK)
    hero_number(sc, 34, 222, 104, GRAPE, align="left", width=330, unit=(38, 280, 300, "left"), unit_color=INK)
    board = nid()
    wins = [digit_window(f"Deposit tally {p}", -96 + (3 - p) * 64, 0, 54, 74, "deposits", 3, p, 4, 46, INK, 60)
            for p in range(4)]
    sc.items.append(el("Node", {"name": "Tally board", "x": 195, "y": 380, "id": board}, wins + [
        sparkle("Board rivet a", -150, -40, 13, PEACH), sparkle("Board rivet b", 150, -40, 13, PEACH),
        sparkle("Board rivet c", -150, 40, 13, PEACH), sparkle("Board rivet d", 150, 40, 13, PEACH),
        shape("Board bezel", [rect(270, 92, 16)], [fill(INK)]),
        shape("Board", [rect(330, 116, 26)], [fill(grad=lin([(0, GRAPE_L), (1, GRAPE)], 0, -58, 0, 58)), stroke(INK, 5)]),
        shape("Board shadow", [rect(330, 116, 26, y=10)], [fill(alpha(INK, 0.25))]),
    ]))
    sc.key(board, "y", [(0, 470, "out"), (18, 372, "soft"), (28, 380)])
    sc.key(board, "rotation", [(0, 0.12, "out"), (24, 0)])
    sc.key(board, "opacity", [(0, 0, "linear"), (8, 1)])
    # zigzag track: a coin takes every turn on its way into the machine
    zz = [(40, 498), (300, 528), (86, 558), (250, 588), (195, 646)]
    sc.items.append(shape("Zigzag rail shine", [poly([(x, y + 19) for x, y in zz[:4]], closed=False)],
                          [stroke(alpha(CREAM, 0.8), 3)], y=-3))
    sc.items.append(shape("Zigzag rail", [poly([(x, y + 21) for x, y in zz[:4]], closed=False)],
                          [stroke(INK, 15), stroke(MINT_D, 8, name="Rail")]))
    zc = nid()
    sc.items.insert(0, el("Node", {"name": "Zigzag coin", "id": zc, "x": 372, "y": 470}, [coin("Zigzag coin art", 0, 0, 0.62)]))
    seg = [0, 18, 32, 48, 58]
    sc.key(zc, "x", [(30 + f, x, "inout" if i < 3 else "drop") for i, (f, (x, y)) in enumerate(zip(seg, zz))])
    sc.key(zc, "y", [(30 + f, y, "inout" if i < 3 else "drop") for i, (f, (x, y)) in enumerate(zip(seg, zz))])
    sc.key(zc, "rotation", [(30, 0, "inout"), (48, -6.0, "inout"), (62, -2.0, "inout"), (78, -8.0, "drop"), (88, -9.0)])
    sc.key(zc, "opacity", [(29, 0, "hold"), (30, 1, "linear"), (86, 1, "linear"), (90, 0)])
    sc.items += deco_bg(sc, 33, PEACH, 6)
    return sc


# ---------------------------------------------------------------- 4
def token_icon(kind):
    if kind == 0:   # house
        return [shape("House", [poly([(-12, 2), (0, -10), (12, 2), (8, 2), (8, 11), (-8, 11), (-8, 2)])], [fill(GOLD_D)])]
    if kind == 1:   # graduation cap
        return [shape("Cap", [poly([(-14, -2), (0, -9), (14, -2), (0, 5)]), rect(14, 8, 2, y=6)], [fill(GOLD_D)])]
    return [shape("Palm", [poly([(-1, 12), (1, -4), (3, 12)]), poly([(0, -5), (-13, -1), (-6, -9)]),
                           poly([(0, -5), (13, -1), (6, -9)]), poly([(0, -6), (-3, -14), (3, -14)])], [fill(GOLD_D)])]


def token(name, kind, tid, inner_bind=None):
    inner = el("Node", {"name": f"{name} face", "id": nid()}, ([inner_bind] if inner_bind else []) + token_icon(kind) + [
        shape(f"{name} face", [ellipse(50, 50)], [fill(grad=lin([(0, GOLD_L), (1, GOLD)], -10, -24, 10, 24)), stroke(GOLD_D, 2.5)]),
        shape(f"{name} rim", [ellipse(64, 64)], [fill(GOLD), stroke(INK, 4)]),
        shape(f"{name} edge", [ellipse(64, 64, y=5)], [fill(GOLD_D), stroke(INK, 4)]),
    ])
    return el("Node", {"name": name, "id": tid}, [inner])


def scene4():
    sc = new_scene(4)
    scene_text(sc, 195, 88, 340, "center", 36, sup=(195, 600, 320, "center"), color=INK)
    hero_number(sc, 195, 236, 136, CREAM, outline=(INK, 9), unit=(195, 318, 340, "center"), unit_color=INK)
    for side, (bx, start) in enumerate(((195 - 96, 2.3), (195 + 96, -0.75))):
        b = nid()
        sc.items.append(burst(f"Yes ticks {side}", bx, 230, 16, 32, 3, GRAPE, 5, bid=b, sweep=1.5, start=start))
        sc.pop(b, 30, 0.2, 1.3, 18)
    tray = nid()
    slots = []
    for i, x in enumerate((-100, 0, 100)):
        slots.append(shape(f"Slot {i}", [rect(82, 52, 14, x=x, y=-14)], [fill(INK)]))
        slots.append(shape(f"Slot glow {i}", [rect(64, 10, 5, x=x, y=-34)], [fill(alpha(GRAPE_L, 0.9))]))
    tray_parts = [
        sparkle("Plate star L", -40, 40, 12, GRAPE), sparkle("Plate star R", 40, 40, 12, GRAPE),
        shape("Plate", [rect(120, 26, 13, y=40)], [fill(MINT), stroke(INK, 3)]),
    ] + slots + [
        shape("Tray top", [rect(318, 74, 22, y=-14)], [fill(GRAPE_L), stroke(INK, 4.5)]),
        shape("Tray body", [rect(340, 124, 28, y=8)], [fill(grad=lin([(0, GRAPE), (1, GRAPE_D)], 0, -50, 0, 70)), stroke(INK, 5)]),
        shape("Tray shadow", [ellipse(330, 30, y=74)], [fill(alpha(INK, 0.22))]),
    ]
    # rails that deliver the tokens
    rails = []
    for side in (-1, 1):
        rails.append(shape(f"Feeder {side}", [poly([(195 + side * 230, 364), (195 + side * 120, 392)], closed=False)],
                           [stroke(INK, 26, cap="round"), stroke(PEACH, 16, name="Feeder track")]))
    sc.items.insert(0, el("Node", {"name": "Reward tray", "x": 195, "y": 500, "id": tray}, tray_parts))
    sc.key(tray, "y", [(0, 600, "out"), (20, 494, "soft"), (28, 500)])
    sc.key(tray, "opacity", [(0, 0, "linear"), (8, 1)])
    # three tokens arc in and snap into the slots (only as many as were completed)
    starts = [(-60, 300), (195, 250), (450, 300)]
    for i, (sx, sy) in enumerate(starts):
        t = nid()
        tb = bind(P("goalsCompleted"), 18, conv_formula(f"Token {i} shown", f"max(0, min(1, in - {i}))"))
        sc.items.insert(0, token(f"Goal token {i}", i, t, tb).replace(f'id="{t}"', f'id="{t}" x="{sx}" y="{sy}"', 1))
        t0 = 30 + i * 12
        tx = 195 + (i - 1) * 100
        sc.key(t, "x", [(t0, sx, "soft"), (t0 + 18, tx)])
        sc.key(t, "y", [(t0, sy, "rise"), (t0 + 9, 350, "drop"), (t0 + 18, 478, "out"), (t0 + 21, 470, "in"), (t0 + 24, 478)])
        sc.key(t, "scaleY", [(t0, 1, "linear"), (t0 + 18, 1, "out"), (t0 + 20, 0.78, "soft"), (t0 + 26, 1.04, "soft"), (t0 + 30, 1)])
        sc.key(t, "scaleX", [(t0, 1, "linear"), (t0 + 18, 1, "out"), (t0 + 20, 1.16, "soft"), (t0 + 26, 0.98, "soft"), (t0 + 30, 1)])
        sc.key(t, "rotation", [(t0, (i - 1) * -1.6, "soft"), (t0 + 18, 0)])
        sc.key(t, "opacity", [(t0 - 1, 0, "hold"), (t0, 1)])
        f = nid()
        sc.items.insert(0, burst(f"Snap flash {i}", tx, 462, 40, 56, 10, PEACH, 5, bid=f, opacity=0))
        sc.key(f, "opacity", [(t0 + 18, 0, "linear"), (t0 + 19, 1, "linear"), (t0 + 30, 0)])
        sc.key(f, "scaleX", [(t0 + 18, 0.6, "out"), (t0 + 30, 1.25)])
        sc.key(f, "scaleY", [(t0 + 18, 0.6, "out"), (t0 + 30, 1.25)])
        sc.loop(t, "y", [(0, 478, "inout"), (60 + i * 20, 474, "inout"), (120 + i * 20, 478, "hold"), (IDLE_LEN, 478)])
    sc.items += deco_bg(sc, 44, GRAPE_L, 6)
    return sc


# ---------------------------------------------------------------- 5
def scene5():
    sc = new_scene(5)
    scene_text(sc, 24, 88, 330, "left", 36, sup=(195, 600, 320, "center"), color=INK)
    hero_number(sc, 24, 222, 86, GRAPE, align="left", width=342, unit=(26, 274, 330, "left"), unit_color=INK)
    cx, cy = 205, 452
    big = nid()
    flash = nid()
    sc.items.append(el("Node", {"name": "Merged coin", "id": big, "x": cx, "y": cy, "scaleX": 1, "scaleY": 1},
                       [coin("Merged coin art", 0, 0, 2.3)]))
    sc.items.append(burst("Merge flash", cx, cy, 82, 112, 14, GRAPE, 6, bid=flash, opacity=0))
    ring = shape("Orbit ring", [ellipse(268, 268)], [stroke(alpha(GRAPE, 0.35), 3,
                  trim=None)], x=cx, y=cy, sid=nid())
    ring_id = ring.split('id="')[-1].split('"')[0]
    sc.items.append(ring)
    sc.key(ring_id, "opacity", [(0, 0, "linear"), (14, 1, "linear"), (70, 1, "linear"), (84, 0)])
    sc.key(ring_id, "scaleX", [(0, 1.2, "out"), (70, 0.4)])
    sc.key(ring_id, "scaleY", [(0, 1.2, "out"), (70, 0.4)])
    for i in range(8):
        a = i / 8 * TAU - 1.2
        sx, sy = cx + math.cos(a) * 134, cy + math.sin(a) * 134
        c = nid()
        sc.items.insert(0, el("Node", {"name": f"Roundup coin {i}", "id": c, "x": sx, "y": sy},
                              [coin(f"Roundup coin {i} art", 0, 0, 0.55)]))
        t0 = 6 + i * 3
        arrive = 46 + i * 4
        # spiral in: a quarter turn around the centre before merging
        mid_a = a + 0.9
        mx, my = cx + math.cos(mid_a) * 80, cy + math.sin(mid_a) * 80
        sc.key(c, "x", [(t0, sx, "soft"), (arrive - 12, mx, "in"), (arrive, cx)])
        sc.key(c, "y", [(t0, sy, "soft"), (arrive - 12, my, "in"), (arrive, cy)])
        sc.key(c, "opacity", [(t0 - 6, 0, "linear"), (t0, 1, "linear"), (arrive - 2, 1, "linear"), (arrive, 0)])
        sc.key(c, "scaleX", [(t0 - 6, 0.2, "out"), (t0, 1.0, "linear"), (arrive - 10, 1.0, "in"), (arrive, 0.6)])
        sc.key(c, "scaleY", [(t0 - 6, 0.2, "out"), (t0, 1.0, "linear"), (arrive - 10, 1.0, "in"), (arrive, 0.6)])
    sc.key(big, "scaleX", [(40, 0, "linear"), (46, 0.2, "out"), (78, 0.55, "out"), (86, 1.1, "soft"), (96, 1.0)])
    sc.key(big, "scaleY", [(40, 0, "linear"), (46, 0.2, "out"), (78, 0.55, "out"), (86, 1.1, "soft"), (96, 1.0)])
    sc.key(big, "rotation", [(46, -1.2, "out"), (96, 0)])
    sc.key(flash, "opacity", [(78, 0, "linear"), (80, 1, "linear"), (96, 0)])
    sc.key(flash, "scaleX", [(78, 0.7, "out"), (96, 1.3)])
    sc.key(flash, "scaleY", [(78, 0.7, "out"), (96, 1.3)])
    sc.loop(big, "rotation", [(0, 0, "inout"), (120, 0.08, "inout"), (IDLE_LEN, 0)])
    sc.items += deco_bg(sc, 55, GRAPE_L, 6)
    return sc


# ---------------------------------------------------------------- 6
RANKS = [3, 7, 1, 10, 5, 12, 2, 9, 6, 11, 4, 8]


def scene6():
    sc = new_scene(6)
    scene_text(sc, 24, 88, 330, "left", 36, sup=(24, 600, 340, "left"), color=CREAM)
    hero_number(sc, 366, 220, 104, PEACH, align="right", width=342, unit=(366, 278, 330, "right"), unit_color=CREAM)
    grid = nid()
    wins = []
    for i in range(12):
        r, c = divmod(i, 4)
        x, y = -114 + c * 76, -70 + r * 70
        lit = conv_formula(f"Month window {i} lit", f"max(0, min(1, in * $_count6 - {RANKS[i] - 1}))")
        w = nid()
        wins.append(el("Node", {"name": f"Month window {i}", "x": x, "y": y, "id": w}, [
            el("Node", {"name": f"Month {i} light", "id": nid()}, [bind(P("activeMonths"), 18, lit),
                sparkle(f"Month {i} star", 0, 0, 20, CREAM),
                shape(f"Month {i} glow", [rect(50, 44, 10)], [fill(PEACH)]),
                shape(f"Month {i} halo", [rect(58, 52, 13)], [fill(alpha(PEACH, 0.5),
                      feather=el("Feather", {"strength": 14}))])]),
            shape(f"Month {i} shine", [rect(40, 6, 3, y=-16)], [fill("22FFFFFF")]),
            shape(f"Month {i} glass", [rect(50, 44, 10)], [fill(GRAPE_D)]),
            shape(f"Month {i} frame", [rect(62, 56, 14)], [fill(GRAPE), stroke("FF0E0A1A", 4)]),
        ]))
        sc.pop(w, 4 + RANKS[i] * 2, 0.5, 1.06, 18)
    sc.items.append(el("Node", {"name": "Month windows", "x": 195, "y": 430, "id": grid}, wins + [
        shape("Window board", [rect(330, 236, 30)], [fill(alpha(GRAPE, 0.35)), stroke(alpha(GRAPE_L, 0.6), 3)]),
    ]))
    sc.items += deco_bg(sc, 66, PEACH, 8)
    return sc


# ---------------------------------------------------------------- 7
def scene7():
    sc = new_scene(7)
    scene_text(sc, 24, 88, 330, "left", 36, sup=(24, 176, 330, "left"), color=INK)
    tk = nid()
    clip = nid()
    hid = nid()
    ticket = el("Node", {"name": "Goal ticket", "id": tk, "x": 195, "y": 366}, [
        sem(sc, "text", "screen7Unit", value="largestGoalAmount", value_conv=C["fmtMoneyExact"]),
        el("Node", {"name": "Ticket hero", "y": -2, "id": hid}, [
            text("S7 hero value", -22, 0, [run("largestGoalAmount", "0", conv=hero_conv(7), font="rubik", size=62,
                                              color=INK, weight=900, lh=64, ls=-1)],
                 width=230, align="center", ox=0.5, oy=0.5, sizing="fixed", height=70, overflow="fitFontSize",
                 wrap="noWrap", valign="middle"),
        ]),
        text("Goal name", -22, -54, [run("completedGoalName", "", font="nunito", size=16, color=GRAPE, weight=800, lh=20)],
             width=220, align="center", ox=0.5, oy=0.5, sizing="fixed", height=22, overflow="ellipsis", wrap="noWrap"),
        text("S7 unit", -22, 42, [run("screen7Unit", "", font="nunito", size=15, color=INK, weight=800, lh=19)],
             width=220, align="center", ox=0.5, oy=0.5),
        sparkle("Stub star", 118, 0, 30, GRAPE),
        shape("Perforation", [poly([(84, -70), (84, 70)], closed=False)],
              [el("Stroke", {"thickness": 3, "cap": "round", "name": "Dots"}, [solid(INK), el("DashPath", {"name": "Dash"}, [
                  el("Dash", {"length": 2, "name": "On"}), el("Dash", {"length": 8, "name": "Off"})])])]),
        shape("Notch L", [ellipse(30, 30, x=-150)], [fill(PEACH), stroke(INK, 4)]),
        shape("Notch R", [ellipse(30, 30, x=150)], [fill(PEACH), stroke(INK, 4)]),
        shape("Ticket", [rect(300, 168, 18)], [fill(CREAM), stroke(INK, 5)]),
        shape("Ticket shadow", [rect(300, 168, 18, y=10)], [fill(alpha(INK, 0.25))]),
    ])
    sc.items.append(el("Node", {"name": "Ticket slot reveal", "id": nid()},
                       [el("ClippingShape", {"sourceId": clip, "name": "Above lid"}), ticket]))
    sc.items.append(shape("Above lid mask", [rect(800, 900, 0, y=470, oy=1)], [], sid=clip))
    sc.key(tk, "y", [(10, 610, "out"), (46, 350, "soft"), (58, 370, "soft"), (66, 366)])
    sc.key(tk, "rotation", [(10, 0, "linear"), (40, 0, "soft"), (54, -0.07, "soft"), (66, -0.045)])
    sc.pop(hid, 40, 0.5, 1.1, 22)
    sc.key(M["lid"], "y", [(0, -300, "out"), (10, -340, "soft"), (60, -340, "out"), (70, -300)])
    sc.key(M["lid"], "rotation", [(0, 0, "out"), (10, -0.3, "soft"), (60, -0.3, "out"), (70, 0)])
    b = nid()
    sc.items.insert(0, burst("Ticket burst", 195, 366, 150, 168, 16, INK, 4, bid=b, opacity=0))
    sc.key(b, "opacity", [(56, 0, "linear"), (60, 1, "linear"), (80, 1, "linear"), (96, 0.5)])
    sc.key(b, "scaleX", [(56, 0.85, "out"), (80, 1.0)])
    sc.key(b, "scaleY", [(56, 0.85, "out"), (80, 1.0)])
    sc.loop(tk, "rotation", [(0, -0.045, "inout"), (120, -0.02, "inout"), (IDLE_LEN, -0.045)])
    sc.loop(tk, "y", [(0, 366, "inout"), (120, 360, "inout"), (IDLE_LEN, 366)])
    sc.items += deco_bg(sc, 77, CREAM, 6)
    return sc


# ---------------------------------------------------------------- 8
JAR_COLORS = [MINT, PEACH, GRAPE_L, CREAM, MINT_D, PEACH_D]


def mini_jar(name, color, tall):
    h = 64 if tall else 52
    return [
        shape(f"{name} coin", [ellipse(16, 16, y=-h / 2 + 8)], [fill(GOLD), stroke(INK, 2.5)]),
        shape(f"{name} lid", [rect(34, 12, 4, y=-h / 2 - 4)], [fill(GRAPE), stroke(INK, 3)]),
        shape(f"{name} shine", [rect(5, h * 0.5, 2.5, x=-11, y=-h / 2 + 4)], [fill("88FFFFFF")]),
        shape(f"{name} body", [rect(44, h, 13, y=-h / 2 + 4)], [fill(color), stroke(INK, 3.5)]),
    ]


def scene8():
    sc = new_scene(8)
    scene_text(sc, 195, 88, 340, "center", 36, sup=(195, 616, 320, "center"), color=INK)
    hero_number(sc, 195, 244, 116, GRAPE, unit=(195, 318, 340, "center"), unit_color=INK)
    shelf = nid()
    sc.items.append(el("Node", {"name": "Shelf", "id": shelf, "y": 0}, [
        shape("Shelf plank", [rect(336, 18, 9, x=195, y=560)], [fill(grad=lin([(0, PEACH), (1, PEACH_D)], 0, -9, 0, 9)), stroke(INK, 4)]),
        shape("Bracket L", [poly([(70, 568), (70, 604), (96, 568)])], [fill(GRAPE), stroke(INK, 3.5)]),
        shape("Bracket R", [poly([(320, 568), (320, 604), (294, 568)])], [fill(GRAPE), stroke(INK, 3.5)]),
    ]))
    sc.key(shelf, "y", [(0, 40, "out"), (18, 0)])
    sc.key(shelf, "opacity", [(0, 0, "linear"), (10, 1)])
    xs = [64, 116, 168, 222, 274, 326]
    for i, x in enumerate(xs):
        j = nid()
        shown = conv_formula(f"Jar {i} shown", f"max(0, min(1, in - {i}))")
        jar = el("Node", {"name": f"Goal jar {i}", "id": j, "x": 195, "y": 700}, [
            el("Node", {"name": f"Goal jar {i} art", "id": nid()},
               [bind(P("goalJars"), 18, shown)] + mini_jar(f"Jar {i}", JAR_COLORS[i], i % 2 == 0))])
        sc.items.insert(0, jar)
        t0 = 30 + abs(i - 2.5) * 6
        rot0 = (i - 2.5) * 0.5
        sc.key(j, "x", [(t0, 195, "out"), (t0 + 22, x)])
        sc.key(j, "y", [(t0, 700, "rise"), (t0 + 12, 470, "drop"), (t0 + 22, 551, "out"), (t0 + 26, 543, "in"), (t0 + 30, 551)])
        sc.key(j, "rotation", [(t0, rot0, "out"), (t0 + 22, -rot0 * 0.15, "soft"), (t0 + 30, 0)])
        sc.key(j, "opacity", [(t0 - 1, 0, "hold"), (t0, 1)])
        sc.loop(j, "rotation", [(0, 0, "inout"), (40 + i * 25, 0.05 * (1 if i % 2 else -1), "inout"), (90 + i * 25, 0, "hold"), (IDLE_LEN, 0)])
    sc.items += deco_bg(sc, 88, GRAPE_L, 6)
    return sc


# ---------------------------------------------------------------- 9
EMB = {}


def emblem_builder():
    """four persona emblems, each its own silhouette; animated by the Persona layer"""
    groups = []
    # 0 Steady Builder: stacked toy blocks
    blocks = []
    EMB[0] = {"root": nid(), "parts": []}
    spec = [(0, 58, 104, 46, MINT), (-6, 12, 92, 44, PEACH), (8, -32, 80, 42, CREAM), (-2, -72, 62, 38, GRAPE_L)]
    for i, (x, y, w, h, c) in enumerate(spec):
        b = nid()
        EMB[0]["parts"].append((b, x, y))
        blocks.insert(0, el("Node", {"name": f"Block {i}", "id": b, "x": x, "y": y}, [
            shape(f"Block {i} stud", [ellipse(14, 14, y=0)], [fill(GOLD), stroke(INK, 2.5)]),
            shape(f"Block {i} shine", [rect(w - 22, 5, 2.5, y=-h / 2 + 8)], [fill("66FFFFFF")]),
            shape(f"Block {i}", [rect(w, h, 10)], [fill(c), stroke(INK, 4)]),
        ]))
    groups.append(el("Node", {"name": "Emblem Steady Builder", "id": EMB[0]["root"], "opacity": 0}, blocks))
    # 1 Goal Collector: goal-token tray
    EMB[1] = {"root": nid(), "parts": []}
    tray = [shape("Mini tray", [rect(196, 56, 18, y=46)], [fill(GRAPE_D), stroke(INK, 4.5)])]
    for i in range(3):
        slot_x = -62 + i * 62
        tray.insert(0, shape(f"Mini slot {i}", [rect(48, 22, 8, x=slot_x, y=40)], [fill(INK)]))
        t = nid()
        EMB[1]["parts"].append((t, slot_x, 22))
        tray.insert(0, token(f"Collector token {i}", i, t).replace(f'id="{t}"', f'id="{t}" x="{slot_x}" y="22" scaleX="0.8" scaleY="0.8"', 1))
    groups.append(el("Node", {"name": "Emblem Goal Collector", "id": EMB[1]["root"], "opacity": 0}, tray))
    # 2 Roundup Ranger: small coin spiral
    EMB[2] = {"root": nid(), "parts": []}
    sp = []
    for i in range(11):
        a = i * 0.78
        r = 14 + i * 8.5
        c = nid()
        EMB[2]["parts"].append((c, math.cos(a) * r, math.sin(a) * r))
        sp.insert(0, el("Node", {"name": f"Spiral coin {i}", "id": c, "x": math.cos(a) * r, "y": math.sin(a) * r},
                        [coin(f"Spiral coin {i} art", 0, 0, 0.28 + i * 0.035)]))
    spin = nid()
    EMB[2]["spin"] = spin
    spiral_pts = [(math.cos(t / 10 * 0.78) * (14 + t / 10 * 8.5), math.sin(t / 10 * 0.78) * (14 + t / 10 * 8.5)) for t in range(0, 101, 2)]
    sp.append(shape("Spiral track", [poly(spiral_pts, closed=False)], [stroke(alpha(MINT, 0.8), 5), stroke(INK, 9, name="Track edge")]))
    groups.append(el("Node", {"name": "Emblem Roundup Ranger", "id": EMB[2]["root"], "opacity": 0},
                     [el("Node", {"name": "Spiral", "id": spin}, sp)]))
    # 3 Patient Planner: calendar-shaped jar
    EMB[3] = {"root": nid(), "parts": []}
    cal = []
    for i in range(9):
        r, c = divmod(i, 3)
        d = nid()
        EMB[3]["parts"].append((d, -32 + c * 32, -6 + r * 30))
        cal.insert(0, shape(f"Day {i}", [rect(24, 22, 6)], [fill(GRAPE_L if i != 8 else PEACH), stroke(INK, 2.5)],
                            x=-32 + c * 32, y=-6 + r * 30, sid=d))
    rings = []
    for x in (-34, 34):
        rings.append(shape(f"Ring {x}", [rect(12, 34, 6, x=x, y=-80)], [fill(GOLD), stroke(INK, 3)]))
    page = nid()
    EMB[3]["page"] = page
    cal_parts = cal + rings + [
        shape("Calendar page", [rect(116, 30, 8, y=-58)], [fill(PEACH), stroke(INK, 4)], sid=page),
        shape("Calendar lid", [rect(132, 26, 10, y=-74)], [fill(GRAPE), stroke(INK, 4)]),
        shape("Calendar jar", [rect(140, 150, 30, y=12)], [fill(CREAM), stroke(INK, 5)]),
    ]
    groups.append(el("Node", {"name": "Emblem Patient Planner", "id": EMB[3]["root"], "opacity": 0}, cal_parts))
    return groups


def scene9():
    sc = new_scene(9)
    lid = nid()
    sc.items.append(text("Persona label", 195, 96, [run("personaLabel", "", font="nunito", size=16, color=MINT, weight=800, lh=20)],
                         width=340, align="center", ox=0.5, tid=lid))
    sc.rise(lid, 44, 10, 20, y=96)
    nm = nid()
    sc.items.append(el("Node", {"name": "Persona title", "x": 195, "y": 150, "id": nm}, [
        sem(sc, "text", "personaName", value="personaDescription", heading=1),
        text("Persona name", 0, 0, [run("personaName", "", font="rubik", size=46, color=CREAM, weight=900, lh=48,
                                         ls=-0.5, outline=(INK, 8))],
             width=350, align="center", ox=0.5, oy=0.5, sizing="fixed", height=56, overflow="fitFontSize", wrap="noWrap",
             valign="middle")]))
    sc.pop(nm, 58, 0.3, 1.12, 24)
    ds = nid()
    sc.items.append(text("Persona description", 195, 186, [run("personaDescription", "", font="nunito", size=18, color=CREAM,
                                                                 weight=600, lh=24)],
                         width=320, align="center", ox=0.5, tid=ds))
    sc.rise(ds, 70, 12, 22, y=186)
    disc = nid()
    disc_parts = [el("Node", {"name": "Emblems", "id": nid(), "y": 6}, emblem_builder())] + [
        shape("Spotlight", [ellipse(250, 250)], [fill(PEACH, bind=bind(P("personaColor"), 37)), stroke(INK, 5)]),
        shape("Spotlight ring", [ellipse(284, 284)], [el("Stroke", {"thickness": 4, "cap": "round", "name": "Dashes"}, [
            solid(alpha(CREAM, 0.7)), el("DashPath", {"name": "Dash"}, [el("Dash", {"length": 10, "name": "On"}),
                                                                       el("Dash", {"length": 12, "name": "Off"})])])]),
    ]
    sc.items.append(el("Node", {"name": "Persona stage", "x": 195, "y": 424, "id": disc}, disc_parts))
    sc.key(disc, "scaleX", [(30, 0, "out"), (46, 1.08, "soft"), (56, 1)])
    sc.key(disc, "scaleY", [(30, 0, "out"), (46, 1.08, "soft"), (56, 1)])
    sc.loop(disc, "rotation", [(0, 0, "inout"), (120, 0.04, "inout"), (IDLE_LEN, 0)])
    rays = nid()
    sc.items.append(burst("Persona rays", 195, 424, 150, 186, 20, alpha(PEACH, 0.85), 6, bid=rays, opacity=0))
    sc.key(rays, "opacity", [(44, 0, "linear"), (54, 1)])
    sc.key(rays, "rotation", [(44, -0.5, "out"), (90, 0)])
    sc.loop(rays, "rotation", [(0, 0), (IDLE_LEN, 0.314)])
    # anticipation: the machine rattles and its lid pops before the reveal
    sc.key(M["bob"], "rotation", [(0, 0, "inout"), (6, -0.06, "inout"), (12, 0.06, "inout"), (18, -0.07, "inout"),
                                  (24, 0.05, "inout"), (30, 0)])
    sc.key(M["bob"], "scaleY", [(0, 1, "in"), (24, 0.9, "out"), (32, 1.06, "soft"), (40, 1)])
    sc.key(M["lid"], "y", [(24, -300, "out"), (34, -372, "soft"), (60, -330, "soft"), (74, -300)])
    sc.key(M["lid"], "rotation", [(24, 0, "out"), (34, 0.5, "soft"), (74, 0)])
    sc.items += deco_bg(sc, 99, MINT, 7)
    return sc


# ---------------------------------------------------------------- 10
SHARE_AB = "0:3100"
SHARE_ASSEMBLE = nid()


def scene10():
    sc = new_scene(10)
    scene_text(sc, 195, 84, 340, "center", 30, sup=(195, 628, 300, "center"), color=CREAM)
    card = nid()
    remap = nid()
    sc.items.append(el("NestedArtboard", {"artboardId": SHARE_AB, "x": 195, "y": 392, "name": "Share card", "id": card},
                       [el("NestedRemapAnimation", {"animationId": SHARE_ASSEMBLE, "time": 1, "name": "Assemble", "id": remap})]))
    sc.key(card, "y", [(0, 760, "rise"), (24, 380, "soft"), (34, 396, "soft"), (42, 392)])
    sc.key(card, "rotation", [(0, 0.25, "out"), (30, -0.03, "soft"), (42, 0)])
    sc.key(remap, "time", [(20, 0, "linear"), (92, 1)])
    for i, (x, y) in enumerate(((44, 170), (352, 210), (36, 560), (356, 590))):
        s = nid()
        sc.items.append(sparkle(f"Summary star {i}", x, y, 20 + i * 3, PEACH if i % 2 else MINT, sid=s))
        sc.pop(s, 60 + i * 6, 0, 1.3, 16)
        sc.loop(s, "rotation", [(0, 0), (IDLE_LEN, 1.5708 * (1 if i % 2 else -1))])
    sc.items += deco_bg(sc, 100, MINT, 5)
    return sc


# =====================================================================
# Share card component (also rendered on its own by the host for capture)
# =====================================================================
def tile(name, x, y, w, h, color, src, label_path, money=False):
    tid = nid()
    conv = C["fmtMoney"] if money else C["fmtCount"]
    return tid, el("Node", {"name": name, "x": x, "y": y, "id": tid}, [
        text(f"{name} value", -w / 2 + 14, -h / 2 + 10, [run(src, "0", conv=conv, font="rubik", size=28, color=INK,
                                                             weight=900, lh=30, ls=-0.5)],
             width=w - 28, sizing="fixed", height=32, overflow="fitFontSize", wrap="noWrap"),
        text(f"{name} label", -w / 2 + 14, -h / 2 + 44, [run(label_path, "", font="nunito", size=12.5, color=INK,
                                                             weight=800, lh=15)],
             width=w - 28, sizing="fixed", height=h - 50, overflow="ellipsis"),
        shape(f"{name} bg", [rect(w, h, 16)], [fill(color), stroke(INK, 3.5)]),
    ])


def share_card():
    a = Anim("Assemble", 72, aid=SHARE_ASSEMBLE)
    priv, sens = [], []
    pspec = [("Deposits", -73, 26, MINT, "deposits", "screen3Unit"), ("Goals", 73, 26, PEACH, "goalsCompleted", "screen4Unit"),
             ("Months", -73, 134, GRAPE_L, "activeMonths", "screen6Unit"), ("Jars", 73, 134, CREAM, "goalJars", "screen8Unit")]
    order = 0
    for nm, x, y, c, src, lab in pspec:
        tid, t = tile(f"Private {nm}", x, y, 140, 98, c if c != CREAM else "FFFFE9C2", src, lab)
        priv.append(t)
        a.key(tid, "scaleX", [(10 + order * 6, 0.3, "out"), (22 + order * 6, 1.08, "soft"), (30 + order * 6, 1)])
        a.key(tid, "scaleY", [(10 + order * 6, 0.3, "out"), (22 + order * 6, 1.08, "soft"), (30 + order * 6, 1)])
        a.key(tid, "opacity", [(10 + order * 6, 0, "linear"), (16 + order * 6, 1)])
        order += 1
    sspec = [("Saved", 0, -2, 286, 70, PEACH, "totalSaved", "screen2Unit", True),
             ("Roundups", -73, 82, 140, 84, MINT, "roundupsSaved", "screen5Unit", True),
             ("Deposits", 73, 82, 140, 84, "FFFFE9C2", "deposits", "screen3Unit", False),
             ("Goals", -73, 172, 140, 84, GRAPE_L, "goalsCompleted", "screen4Unit", False),
             ("Months", 73, 172, 140, 84, MINT_D, "activeMonths", "screen6Unit", False)]
    order = 0
    for nm, x, y, w, h, c, src, lab, money in sspec:
        tid, t = tile(f"Full {nm}", x, y, w, h, c, src, lab, money)
        sens.append(t)
        a.key(tid, "scaleX", [(10 + order * 5, 0.3, "out"), (22 + order * 5, 1.08, "soft"), (30 + order * 5, 1)])
        a.key(tid, "scaleY", [(10 + order * 5, 0.3, "out"), (22 + order * 5, 1.08, "soft"), (30 + order * 5, 1)])
        a.key(tid, "opacity", [(10 + order * 5, 0, "linear"), (16 + order * 5, 1)])
        order += 1
    chip = nid()
    a.key(chip, "x", [(4, -40, "out"), (24, 0)])
    a.key(chip, "opacity", [(4, 0, "linear"), (14, 1)])
    yr = nid()
    a.key(yr, "scaleX", [(0, 0.5, "out"), (16, 1.1, "soft"), (24, 1)])
    a.key(yr, "scaleY", [(0, 0.5, "out"), (16, 1.1, "soft"), (24, 1)])
    stats = el("Node", {"name": "Stats", "id": nid()}, [
        bind(P("_emptyState"), 18, C["b2zero"]),
        el("Node", {"name": "Privacy: full values", "id": nid()}, [bind(P("shareIncludeSensitiveValues"), 18, C["b2one"])] + sens),
        el("Node", {"name": "Privacy: counts only", "id": nid()}, [bind(P("shareIncludeSensitiveValues"), 18, C["b2zero"])] + priv),
    ])
    empty = el("Node", {"name": "Empty state", "id": nid()}, [
        bind(P("_emptyState"), 18, C["b2one"]),
        text("Empty headline", 0, 0, [run("emptyHeadline", "", font="rubik", size=26, color=INK, weight=800, lh=29)],
             width=270, align="center", ox=0.5),
        text("Empty support", 0, 78, [run("emptySupport", "", font="nunito", size=16, color=INK, weight=600, lh=21)],
             width=260, align="center", ox=0.5),
        coin("Empty coin", 0, 160, 0.9),
        shape("Empty slot", [rect(70, 12, 6, y=196)], [fill(INK)]),
    ])
    chip_n = el("Node", {"name": "Persona chip", "id": chip}, [
        el("Node", {"name": "Persona chip shown", "id": nid()}, [bind(P("_personaKnown"), 18, C["b2one"]),
            text("Chip name", -112, -62, [run("personaName", "", font="nunito", size=15, color=INK, weight=800, lh=18)],
                 width=230, sizing="fixed", height=20, overflow="ellipsis", wrap="noWrap", oy=0.5, valign="middle"),
            shape("Chip dot", [ellipse(18, 18, x=-128, y=-62)], [fill(MINT, bind=bind(P("personaColor"), 37)), stroke(INK, 3)]),
            shape("Chip", [rect(286, 34, 17, y=-62)], [fill("FFFFE9C2"), stroke(INK, 3)]),
        ])])
    header = [
        el("Node", {"name": "Name (opt-in)", "id": nid()}, [bind(P("shareIncludeName"), 18, C["b2one"]),
            text("Card name", -139, -142, [run("userName", "", font="nunito", size=16, color=MINT, weight=800, lh=20)],
                 width=170, sizing="fixed", height=22, overflow="ellipsis", wrap="noWrap")]),
        el("Node", {"name": "Card year", "x": 140, "y": -150, "id": yr}, [
            text("Year", 0, 0, [run("year", "2026", conv=C["toStr0"], font="rubik", size=50, color=MINT, weight=900, lh=52,
                                    outline=(INK, 7))], ox=1, oy=0.5)]),
        text("Card wordmark", -139, -196, [run(None, "Stash", font="rubik", size=28, color=CREAM, weight=900, lh=30)]),
        coin("Card coin", 112, -192, 0.5),
        shape("Header band", [rect(330, 136, 0, y=-152, radii=(30, 30, 0, 0))], [fill(GRAPE), stroke(INK, 5)]),
    ]
    art = [stats, empty, chip_n] + header + [
        sparkle("Card star a", -136, 206, 14, PEACH), sparkle("Card star b", 136, 206, 14, GRAPE_L),
        shape("Card", [rect(330, 452, 30)], [fill(CREAM), stroke(INK, 5)]),
        shape("Card shadow", [rect(330, 452, 30, y=12)], [fill(alpha(INK, 0.35))]),
    ]
    sm = nid()
    lay = nid()
    st = nid()
    settled = Anim("Settled", 1)
    machine_xml = el("StateMachine", {"name": "Card", "id": sm}, [
        el("StateMachineLayer", {"name": "Card", "id": lay}, [
            el("AnyState", {"x": 300, "y": -100}), el("ExitState", {"x": 500, "y": -100}),
            el("EntryState", {"x": 0, "y": 0}, [el("StateTransition", {"stateToId": st})]),
            el("AnimationState", {"x": 160, "y": 0, "animationId": settled.id, "id": st}),
        ])])
    style = nid()
    return el("Artboard", {"isComponent": True, "defaultStateMachineId": sm, "styleId": style, "clip": False,
                           "viewModelId": VM, "viewModelInstanceId": VMI,
                           "originX": 0.5, "originY": 0.5, "width": 340, "height": 470, "x": 900, "y": 0,
                           "name": "ShareCard", "id": SHARE_AB},
              [el("LayoutComponentStyle", {"name": "Card style", "id": style})] + art +
              [machine_xml, settled.xml(), a.xml()])


def coin_artboard():
    sm, lay, st = nid(), nid(), nid()
    idle = Anim("Rest", 1)
    style = nid()
    return el("Artboard", {"isComponent": True, "defaultStateMachineId": sm, "styleId": style, "clip": False,
                           "originX": 0.5, "originY": 0.5, "width": 64, "height": 64, "x": 800, "y": 0,
                           "name": "Coin", "id": COIN_AB},
              [el("LayoutComponentStyle", {"name": "Coin style", "id": style})] + coin_art() + [
                  el("StateMachine", {"name": "Coin", "id": sm}, [
                      el("StateMachineLayer", {"name": "Coin", "id": lay}, [
                          el("AnyState", {"x": 300, "y": -100}), el("ExitState", {"x": 500, "y": -100}),
                          el("EntryState", {"x": 0, "y": 0}, [el("StateTransition", {"stateToId": st})]),
                          el("AnimationState", {"x": 160, "y": 0, "animationId": idle.id, "id": st})])]),
                  idle.xml()])


# =====================================================================
# Overlays: signature handoff (coin -> spring) and the coin toy
# =====================================================================
HO = {}


def handoff():
    for k in ("root", "rail", "coin", "coil", "plate", "spring"):
        HO[k] = nid()
    zig = [(0, 0)]
    for i in range(1, 8):
        zig.append(((-26 if i % 2 else 26), -i * 9.4))
    zig.append((0, -70))
    return el("Node", {"name": "Handoff: coin and spring", "id": HO["root"], "opacity": 0}, [
        el("Node", {"name": "Handoff coin", "id": HO["coin"], "x": 430, "y": 600}, [coin("Handoff coin art", 0, 0, 0.82)]),
        el("Node", {"name": "Spring", "id": HO["spring"], "x": 346, "y": 742}, [
            el("Node", {"name": "Spring plate", "id": HO["plate"], "y": -76}, [
                shape("Plate shine", [rect(70, 4, 2, y=-3)], [fill("66FFFFFF")]),
                shape("Plate", [rect(96, 16, 8)], [fill(GRAPE_L), stroke(INK, 4)])]),
            el("Node", {"name": "Spring coil", "id": HO["coil"]}, [
                shape("Coil", [poly(zig, closed=False)], [stroke(INK, 9, join="round"), stroke(MINT, 4.5, name="Coil steel")])]),
            shape("Spring base", [rect(100, 14, 6, y=2)], [fill(INK)]),
        ]),
        el("Node", {"name": "Exit rail", "id": HO["rail"]}, [
            shape("Rail", [poly([(460, 560), (372, 580)], closed=False)], [stroke(INK, 12), stroke(PEACH, 6, name="Rail top")])]),
    ])


def handoff_anims():
    fwd = Anim("Handoff forward", 56)
    fwd.key(HO["root"], "opacity", [(0, 1, "hold"), (44, 1, "linear"), (54, 0)])
    fwd.key(HO["rail"], "x", [(0, 80, "out"), (8, 0, "linear"), (40, 0, "in"), (50, 120)])
    fwd.key(HO["coin"], "x", [(0, 440, "linear"), (10, 372, "linear"), (17, 346, "linear"), (40, 300)])
    fwd.key(HO["coin"], "y", [(0, 540, "linear"), (10, 556, "drop"), (17, 635, "linear"), (23, 674, "out"), (40, -140)])
    fwd.key(HO["coin"], "rotation", [(0, 0, "linear"), (17, -5.4, "linear"), (23, -5.6, "out"), (40, -12)])
    fwd.key(HO["coin"], "scaleY", [(0, 1, "linear"), (17, 1, "out"), (20, 0.82, "soft"), (24, 1.08, "soft"), (30, 1)])
    fwd.key(HO["coil"], "scaleY", [(0, 1, "linear"), (17, 1, "in"), (23, 0.42, "out"), (29, 1.32, "soft"), (37, 0.92, "soft"), (44, 1)])
    fwd.key(HO["plate"], "y", [(0, -76, "linear"), (17, -76, "in"), (23, -38, "out"), (29, -98, "soft"), (37, -70, "soft"), (44, -76)])
    fwd.key(HO["spring"], "y", [(0, 830, "out"), (10, 742)])
    back = Anim("Handoff back", 56)
    back.key(HO["root"], "opacity", [(0, 1, "hold"), (44, 1, "linear"), (54, 0)])
    back.key(HO["rail"], "x", [(0, 400, "hold"), (56, 400)])
    back.key(HO["spring"], "y", [(0, 830, "out"), (8, 742)])
    back.key(HO["coil"], "scaleY", [(0, 1, "out"), (8, 1.4, "in"), (20, 0.46, "out"), (32, 1.1, "soft"), (40, 1)])
    back.key(HO["plate"], "y", [(0, -76, "out"), (8, -104, "in"), (20, -40, "out"), (32, -82, "soft"), (40, -76)])
    back.key(HO["coin"], "x", [(0, 346, "linear"), (8, 346, "out"), (34, 470)])
    back.key(HO["coin"], "y", [(0, 646, "linear"), (8, 616, "out"), (20, 420, "in"), (34, 560)])
    back.key(HO["coin"], "rotation", [(0, 0, "linear"), (34, 9)])
    back.key(HO["coin"], "scaleY", [(0, 1, "hold"), (56, 1)])
    rest = Anim("Handoff rest", 1)
    rest.hold(HO["root"], "opacity", 0)
    return rest, fwd, back


TOY = {}


def coin_toy():
    """a tiny pachinko board in the corner: tap the coin to nudge it down a fixed track"""
    for k in ("root", "coin", "cup", "hit", "hint"):
        TOY[k] = nid()
    rails = [((-30, -18), (12, -8)), ((30, 2), (-12, 12)), ((-30, 22), (8, 30))]
    rail_paths = [poly([a, b], closed=False, name=f"Peg rail {i}") for i, (a, b) in enumerate(rails)]
    return el("Node", {"name": "Coin toy (decorative)", "id": TOY["root"], "x": 50, "y": 694}, [
        el("Node", {"name": "Toy coin", "id": TOY["coin"], "x": -24, "y": -30}, [coin("Toy coin art", 0, 0, 0.3)]),
        shape("Toy hint", [ellipse(30, 30, x=-24, y=-30)], [stroke(alpha(PEACH, 0.9), 3)], sid=TOY["hint"]),
        shape("Toy rails", rail_paths, [stroke(INK, 5), stroke(MINT, 2.2, name="Rail top")]),
        el("Node", {"name": "Toy cup", "id": TOY["cup"], "x": 18, "y": 38}, [
            shape("Cup", [rect(22, 10, 4)], [fill(INK)])]),
        shape("Toy glass", [rect(66, 6, 3, x=-4, y=-38)], [fill("44FFFFFF")]),
        shape("Toy board", [rect(78, 90, 16)], [fill(GRAPE_L), stroke(INK, 3.5)]),
        shape("Toy shadow", [rect(80, 92, 16, y=5)], [fill(alpha(INK, 0.35))]),
        shape("Toy hit area", [rect(92, 96, 18, y=2)], [fill(CLEAR)], sid=TOY["hit"]),
    ])


def toy_anims():
    idle = Anim("Toy idle", 180, loop="loop")
    idle.key(TOY["coin"], "rotation", [(0, 0, "inout"), (20, -0.25, "inout"), (40, 0.18, "inout"), (56, 0, "hold"), (180, 0)])
    idle.key(TOY["hint"], "opacity", [(0, 0, "soft"), (20, 0.9, "soft"), (60, 0, "hold"), (180, 0)])
    idle.key(TOY["hint"], "scaleX", [(0, 0.8, "out"), (60, 1.5, "hold"), (180, 1.5)])
    idle.key(TOY["hint"], "scaleY", [(0, 0.8, "out"), (60, 1.5, "hold"), (180, 1.5)])
    for k, v in (("x", -24), ("y", -30), ("scaleX", 1), ("scaleY", 1), ("opacity", 1)):
        idle.hold(TOY["coin"], k, v)
    idle.hold(TOY["cup"], "scaleY", 1)
    nudge = Anim("Toy nudge", 84)
    pts = [(-24, -30, 0), (-22, -28, 5), (10, -18, 16), (16, -12, 20), (24, -8, 24), (-10, 2, 34), (-18, 8, 38),
           (-24, 12, 42), (4, 20, 50), (18, 30, 56)]
    nudge.key(TOY["coin"], "x", [(f, x, "inout" if f < 50 else "drop") for x, y, f in pts] + [(70, 18, "hold"), (71, -24)])
    nudge.key(TOY["coin"], "y", [(f, y, "inout" if f < 50 else "drop") for x, y, f in pts] + [(70, 30, "hold"), (71, -30)])
    nudge.key(TOY["coin"], "rotation", [(0, 0, "inout"), (52, -10, "hold"), (70, 0)])
    nudge.key(TOY["coin"], "scaleX", [(0, 1, "linear"), (50, 1, "in"), (56, 0.4, "hold"), (70, 0, "out"), (84, 1)])
    nudge.key(TOY["coin"], "scaleY", [(0, 1, "linear"), (50, 1, "in"), (56, 0.4, "hold"), (70, 0, "out"), (84, 1)])
    nudge.key(TOY["coin"], "opacity", [(0, 1, "linear"), (54, 1, "linear"), (58, 0, "hold"), (70, 0, "linear"), (74, 1)])
    nudge.key(TOY["cup"], "scaleY", [(0, 1, "linear"), (54, 1, "out"), (58, 0.7, "soft"), (66, 1.1, "soft"), (72, 1)])
    nudge.hold(TOY["hint"], "opacity", 0)
    return idle, nudge


# =====================================================================
# Chrome: header and footers (layout, so they respond to the viewport)
# =====================================================================
CH = {}


def lstyle(sid, **kw):
    a = {"name": kw.pop("name", "Style"), "id": sid}
    for k, v in kw.items():
        a[k] = v
        if k.startswith(("padding", "gap", "position", "margin")) and not k.endswith("UnitsValue") and k != "positionTypeValue":
            a[k + "UnitsValue"] = "points"
    return el("LayoutComponentStyle", a)


def box(name, bid, style_kw, children, w=0, h=0, extra_attrs=None, style_binds=None):
    sid = nid()
    a = {"width": w, "height": h, "styleId": sid, "clip": False, "name": name, "id": bid}
    a.update(extra_attrs or {})
    st = lstyle(sid, name=f"{name} style", **style_kw)
    if style_binds:
        st = st[:-2] + ">\n" + "\n".join(style_binds) + "\n</LayoutComponentStyle>"
    return el("LayoutComponent", a, [st] + children), sid


INSET = None


def inset_binds():
    # keeps the chrome a centred portrait column on wide (desktop) viewports
    return [bind(P("_chromeInset"), 516), bind(P("_chromeInset"), 517)]


def chrome_text(name, path, txt, size, weight, font="nunito", onc=False, conv=None, participant="hug"):
    cp = P("_chromeOnColor" if onc else "_chromeColor")
    tid = nid()
    fid, fam = FONTS[font]
    sid = nid()
    style = el("TextStylePaint", {"fontSize": size, "fontAssetId": fid, "familyName": fam,
                                  "styleName": WEIGHT_NAME.get(weight, "Custom"), "name": f"{name} style", "id": sid},
               [fill(CREAM, bind=bind(cp, 37)), el("TextStyleAxis", {"tag": 2003265652, "axisValue": weight, "name": "wght"})])
    b = [bind(P(path), 268, conv)] if path else None
    lp = el("LayoutParticipant", {"layoutWidthScaleType": participant, "layoutHeightScaleType": "hug", "name": "LP"})
    return el("Text", {"name": name, "id": tid, "wrapValue": "noWrap", "overflowValue": "ellipsis" if participant == "fill" else None,
                       "alignValue": "center" if participant == "fill" else None},
              [lp, style, el("TextValueRun", {"styleId": sid, "text": txt, "name": "Run"}, b)])


def icon(name, paths, color_path="_chromeColor", th=3.5, fill_=False):
    lp = el("LayoutParticipant", {"layoutWidthScaleType": "hug", "layoutHeightScaleType": "hug", "name": "LP"})
    paint = (fill(CREAM, bind=bind(P(color_path), 37)) if fill_ else
             stroke(CREAM, th, bind=bind(P(color_path), 37)))
    return el("Shape", {"name": name, "id": nid()}, [lp] + paths + [paint])


def focus_ring(name, k, r, w=None, h=None):
    """visible keyboard focus: opacity = 1 when _focus == k"""
    cv = conv_formula(f"{name} focus", f"max(0, 1 - (in - {k}) * (in - {k}))")
    rid = nid()
    ring, _ = box(f"{name} focus ring", rid, dict(positionTypeValue="absolute", positionLeft=-6, positionRight=-6,
                                                    positionTop=-6, positionBottom=-6, cornerRadiusTL=r + 6),
                  [stroke(PEACH, 4), bind(P("_focus"), 18, cv)], extra_attrs={"opacity": 0})
    return ring


def button(name, bid, k, label_path, sem_path, w=None, primary=False, accent=None, children=None, weight_=1):
    kw = dict(flexDirectionValue="row", layoutAlignmentType="center", gapHorizontal=8,
              paddingLeft=18, paddingRight=18, cornerRadiusTL=27, layoutHeightScaleType="fixed")
    if w:
        kw["layoutWidthScaleType"] = "fixed"
        kw.update(paddingLeft=0, paddingRight=0)
    else:
        kw["layoutWidthScaleType"] = "fill"
    paints = []
    if primary:
        paints.append(fill(CREAM, bind=bind(P("_chromeColor"), 37)))
    elif accent:
        paints.append(fill(accent))
        paints.append(stroke(INK, 3))
    else:
        paints.append(fill(CLEAR))
        paints.append(stroke(CREAM, 2.5, bind=bind(P("_chromeColor"), 37)))
    CH[f"sem_{bid}"] = nid()
    sem_ch = [bind(P(sem_path), 983)]
    if bid == CH.get("prev"):
        sem_ch.append(bind(P("_canGoBack"), 1002, C["not"]))
    sem_ = el("SemanticData", {"role": "button", "name": "Semantics", "id": CH[f"sem_{bid}"]}, sem_ch)
    ch = [sem_, el("FocusData", {"name": "Focus"})] + paints + [focus_ring(name, k, 27)] + (children or [])
    attrs = {"fractionalWidth": weight_} if not w else {}
    b, _ = box(name, bid, kw, ch, w=w or 0, h=54, extra_attrs=attrs)
    return b


def chrome():
    CH.update({k: nid() for k in ("header", "pause", "nav", "sum", "prev", "next", "replay", "share", "progress")})
    pause_icons = el("Node", {"name": "Pause icons", "x": 22, "y": 22, "id": nid()}, [
        el("Node", {"name": "Pause glyph", "id": nid()}, [bind(P("isPaused"), 18, C["b2zero"]),
            shape("Bars", [rect(5, 16, 2, x=-5), rect(5, 16, 2, x=5)], [fill(CREAM, bind=bind(P("_chromeColor"), 37))])]),
        el("Node", {"name": "Play glyph", "id": nid()}, [bind(P("isPaused"), 18, C["b2one"]),
            shape("Triangle", [poly([(-5, -9, 2), (10, 0, 2), (-5, 9, 2)])], [fill(CREAM, bind=bind(P("_chromeColor"), 37))])]),
    ])
    sem = el("SemanticData", {"role": "button", "name": "Semantics"}, [bind(P("_pauseButtonLabel"), 983)])
    pause, _ = box("Pause button", CH["pause"], dict(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed",
                                                     cornerRadiusTL=22),
                   [sem, el("FocusData", {"name": "Focus"}), fill(CLEAR), stroke(CREAM, 2, bind=bind(P("_chromeColor"), 37)),
                    focus_ring("Pause", 1, 22), pause_icons], w=44, h=44)
    prog_box, _ = box("Progress slot", CH["progress"], dict(layoutWidthScaleType="fill", layoutHeightScaleType="fixed"),
                      [el("ScriptedLayout", {"scriptAssetId": SCRIPTS["progress"][0], "name": "Progress segments", "id": nid()})],
                      h=20)
    wordmark = chrome_text("Header wordmark", None, "Stash", 23, 900, font="rubik")
    year = chrome_text("Header year", "year", "2026", 14, 800, conv=C["toStr0"])
    header, _ = box("Header", CH["header"], dict(positionTypeValue="absolute", positionTop=0, positionLeft=0, positionRight=0,
                                                 widthUnitsValue="auto", layoutHeightScaleType="fixed",
                                                 flexDirectionValue="row", layoutAlignmentType="centerLeft",
                                                 paddingLeft=18, paddingRight=10, gapHorizontal=12),
                    [wordmark, prog_box, year, pause], h=64, style_binds=inset_binds())

    chev_l = icon("Chevron left", [poly([(6, -8), (-2, 0), (6, 8)], closed=False)])
    chev_r = icon("Chevron right", [poly([(-3, -7), (4, 0), (-3, 7)], closed=False)], "_chromeOnColor", 3)
    prev = button("Previous button", CH["prev"], 2, None, "previousLabel", w=54, children=[chev_l])
    prev = prev.replace(f'id="{CH["prev"]}">', f'id="{CH["prev"]}">\n' + bind(P("_canGoBack"), 18, C["b2dim"]), 1)
    nxt = button("Continue button", CH["next"], 3, "continueLabel", "continueLabel", primary=True, children=[
        chrome_text("Continue label", "continueLabel", "Continue", 17, 800, onc=True, participant="fill"), chev_r])
    replay_icon = icon("Replay glyph", [poly([("c", 7, -2, 1.9, 4), ("c", 0, 7, 3.1, 4), ("c", -7, 0, -1.6, 4),
                                               ("c", 0, -7, 0, 4)], closed=False), poly([(1, -10), (5, -7), (1, -4)], closed=False)], th=2.6)
    replay = button("Replay button", CH["replay"], 4, "replayLabel", "replayLabel", children=[
        replay_icon, chrome_text("Replay label", "replayLabel", "Replay", 16, 800, participant="hug")])
    share_icon = el("Shape", {"name": "Share glyph", "id": nid()}, [
        el("LayoutParticipant", {"layoutWidthScaleType": "hug", "layoutHeightScaleType": "hug", "name": "LP"}),
        poly([(0, 4), (0, -9)], closed=False), poly([(-5, -4), (0, -9), (5, -4)], closed=False),
        poly([(-7, -1), (-7, 9), (7, 9), (7, -1)], closed=False), stroke(INK, 2.6)])
    share_txt = text("Share label", 0, 0, [run("shareLabel", "Share", font="nunito", size=17, color=INK, weight=900)],
                     extra=[el("LayoutParticipant", {"layoutWidthScaleType": "hug", "layoutHeightScaleType": "hug", "name": "LP"})])
    share = button("Share button", CH["share"], 5, "shareLabel", "shareLabel", accent=PEACH, children=[share_icon, share_txt],
                   weight_=1.5)
    fkw = dict(positionTypeValue="absolute", positionBottom=0, positionLeft=0, positionRight=0,
               widthUnitsValue="auto", layoutHeightScaleType="fixed", flexDirectionValue="row",
               layoutAlignmentType="centerLeft", paddingLeft=16, paddingRight=16, gapHorizontal=12)
    nav, CH["nav_style"] = box("Footer: story", CH["nav"], dict(fkw), [prev, nxt], h=104, style_binds=inset_binds())
    fkw2 = dict(fkw, positionBottom=-400)
    sm_, CH["sum_style"] = box("Footer: summary", CH["sum"], fkw2, [replay, share], h=104, extra_attrs={"opacity": 0},
                               style_binds=inset_binds())
    return [header, nav, sm_]


# =====================================================================
# State machine
# =====================================================================
def c_num(p, op, v):
    return el("TransitionViewModelCondition", {"opValue": op}, [
        el("TransitionPropertyViewModelComparator", {}, [el("BindablePropertyNumber", {}, [bind(P(p), 636)])]),
        el("TransitionValueNumberComparator", {"value": v})])


def c_bool(p, v):
    return el("TransitionViewModelCondition", {"opValue": "equal"}, [
        el("TransitionPropertyViewModelComparator", {}, [el("BindablePropertyBoolean", {}, [bind(P(p), 634)])]),
        el("TransitionValueBooleanComparator", {"value": v})])


def c_trig(p):
    return el("TransitionViewModelCondition", {}, [
        el("TransitionPropertyViewModelComparator", {}, [el("BindablePropertyTrigger", {}, [bind(P(p), 686)])]),
        el("TransitionValueTriggerComparator")])


def a_bool(p, v):
    return el("ListenerViewModelChange", {}, [el("BindablePropertyBoolean", {"propertyValue": v},
                                                  [bind(P(p), 634, direction=True)])])


def a_trig(p):
    return el("ListenerViewModelChange", {}, [el("BindablePropertyTrigger", {"propertyValue": 1},
                                                  [bind(P(p), 686, direction=True)])])


def a_num(p, v):
    return el("ListenerViewModelChange", {}, [el("BindablePropertyNumber", {"propertyValue": v},
                                                  [bind(P(p), 636, direction=True)])])


def tr(to, conds=(), dur=0, exit_pct=None, ease=None):
    a = {"stateToId": to, "duration": dur}
    ch = list(conds)
    if exit_pct is not None:
        a.update({"enableExitTime": True, "exitTimeIsPercetange": True, "exitTime": exit_pct})
    if ease:
        a["interpolationType"] = "cubic"
        ch.append(el("CubicEaseInterpolator", {"x1": ease[0], "y1": ease[1], "x2": ease[2], "y2": ease[3]}))
    return el("StateTransition", a, ch)


def astate(aid, sid, x, y, children=(), reset=False):
    return el("AnimationState", {"x": x, "y": y, "animationId": aid, "reset": reset or None, "id": sid}, list(children))


def layer(name, entry_to, states, any_tr=()):
    return el("StateMachineLayer", {"name": name, "id": nid()}, [
        el("AnyState", {"x": 900, "y": -160}, list(any_tr) or None),
        el("ExitState", {"x": 1100, "y": -160}),
        el("EntryState", {"x": -140, "y": 0}, [tr(entry_to)]),
    ] + states)


EV = {"screenChanged": "0:3901", "recapFinished": "0:3902", "shareTapped": "0:3903"}
ANIMS = []


def scene_layer(sc):
    k = sc.k
    root, content = sc.root, sc.content
    ids = {n: nid() for n in ("H", "EF", "EB", "ER", "SH", "SF", "FZ", "XF", "XB", "XR")}
    starts, finals = sc.starts(), sc.finals()
    idle_rest = {(o, p): (kfs[0][1], kind) for o, p, kfs, kind in sc.idle}

    def scene_keys(an, base):
        merged = {}
        for obj, prop, kfs, kind in sc.keys:
            shifted = [(kf[0] + base, kf[1], kf[2] if len(kf) == 3 else "linear") for kf in kfs]
            if (obj, prop) in merged:
                merged[(obj, prop)][1].extend(shifted)
            else:
                merged[(obj, prop)] = (kind, shifted)
        for (obj, prop), (kind, kfs) in merged.items():
            kfs.sort(key=lambda t: t[0])
            if kfs[0][0] > 0:
                kfs.insert(0, (0, kfs[0][1], "hold"))
            an.key(obj, prop, kfs, kind)
        for (o, p), (v, kind) in idle_rest.items():
            if (o, p) not in finals:
                an.key(o, p, [(0, v, "hold")], kind)

    last = max(kf[0] for _, _, kfs, _ in sc.keys for kf in kfs) if sc.keys else 0
    if last + FWD_BASE > ENTER_LEN:
        print(f"warning: scene {k} keys end at {last + FWD_BASE} > {ENTER_LEN}")
    h = Anim(f"S{k} hidden", 1)
    h.hold(root, "opacity", 0)
    for sid_ in sc.sem:
        h.key(sid_, "isHidden", [(0, True, "hold")], "bool")
    ef = Anim(f"S{k} enter forward", ENTER_LEN)
    ef.hold(root, "opacity", 1)
    if k == 1:
        ef.hold(root, "y", 0)
    else:
        ef.key(root, "y", [(0, 1000, "hold"), (19, 1000, (0.2, 0.0, 0.1, 1.0)), (36, -16, "soft"), (42, 5, "soft"), (48, 0)])
    for p, v in (("scaleX", 1), ("scaleY", 1), ("y", 422), ("opacity", 1)):
        ef.hold(content, p, v)
    scene_keys(ef, FWD_BASE if k != 1 else 0)
    eb = Anim(f"S{k} enter back", ENTER_LEN)
    eb.hold(root, "opacity", 1)
    eb.hold(root, "y", 0)
    eb.key(content, "y", [(0, 382, "out"), (30, 422)])
    eb.key(content, "scaleX", [(0, 1.06, "out"), (30, 1)])
    eb.key(content, "scaleY", [(0, 1.06, "out"), (30, 1)])
    eb.key(content, "opacity", [(0, 0.4, "out"), (16, 1)])
    scene_keys(eb, BACK_BASE)
    er = Anim(f"S{k} enter reduced", 18)
    er.key(root, "opacity", [(0, 0, "hold"), (6, 0, "linear"), (16, 1)])
    er.hold(root, "y", 0)
    for p, v in (("scaleX", 1), ("scaleY", 1), ("y", 422), ("opacity", 1)):
        er.hold(content, p, v)
    for (o, p), (v, kind) in finals.items():
        er.key(o, p, [(0, v, "hold")], kind)
    for (o, p), (v, kind) in idle_rest.items():
        if (o, p) not in finals:
            er.key(o, p, [(0, v, "hold")], kind)
    idle = Anim(f"S{k} idle", IDLE_LEN, loop="loop")
    for o, p, kfs, kind in sc.idle:
        idle.key(o, p, kfs, kind)
    if not sc.idle:
        idle.hold(root, "opacity", 1)
    fz = Anim(f"S{k} frozen", 1)
    fz.hold(root, "opacity", 1)
    for (o, p), (v, kind) in idle_rest.items():
        fz.key(o, p, [(0, v, "hold")], kind)
    xf = Anim(f"S{k} exit forward", 48)
    xf.key(content, "scaleX", [(0, 1, "in"), (22, 0.93)])
    xf.key(content, "scaleY", [(0, 1, "in"), (22, 0.93)])
    xf.key(content, "y", [(0, 422, "in"), (22, 436)])
    xf.key(content, "opacity", [(0, 1, "linear"), (36, 0.5)])
    xf.key(root, "opacity", [(0, 1, "hold"), (47, 0)])
    xb = Anim(f"S{k} exit back", 40)
    xb.key(root, "y", [(0, 0, "out"), (8, -22, "drop"), (32, 1000)])
    xb.key(root, "opacity", [(0, 1, "hold"), (39, 0)])
    xr = Anim(f"S{k} exit reduced", 8)
    xr.key(root, "opacity", [(0, 1, "linear"), (6, 0)])
    for an in (ef, eb, er):
        for sid_ in sc.sem:
            an.key(sid_, "isHidden", [(0, False, "hold")], "bool")
    ANIMS.extend([h, ef, eb, er, idle, fz, xf, xb, xr])

    cs_is, cs_not = c_num("currentScreen", "equal", k), c_num("currentScreen", "notEqual", k)
    rm_on, rm_off = c_bool("reducedMotion", True), c_bool("reducedMotion", False)
    fwd, back = c_num("_navDir", "greaterThanOrEqual", 0), c_num("_navDir", "lessThan", 0)
    exits = [tr(ids["XR"], [cs_not, rm_on]), tr(ids["XF"], [cs_not, rm_off, fwd], 90),
             tr(ids["XB"], [cs_not, rm_off, back], 90)]
    enters = [tr(ids["ER"], [cs_is, rm_on]), tr(ids["EF"], [cs_is, rm_off, fwd], 0),
              tr(ids["EB"], [cs_is, rm_off, back], 0)]
    reenters = [tr(ids["ER"], [cs_is, rm_on]), tr(ids["EF"], [cs_is, rm_off, fwd], 90),
                tr(ids["EB"], [cs_is, rm_off, back], 90)]
    announce = [el("StateMachineFireEvent", {"eventId": EV["screenChanged"], "occursValue": 0}), a_trig("_evtScreenChanged")]
    if k == 10:
        settle = [tr(ids["SF"], [c_bool("_finished", False)], 0, exit_pct=100), tr(ids["SH"], [], 0, exit_pct=100)]
    else:
        settle = [tr(ids["SH"], [], 0, exit_pct=100)]
    froz = [tr(ids["FZ"], [c_bool("_frozen", True)], 200)]
    y0 = (k - 1) * 0
    states = [
        astate(h.id, ids["H"], 0, y0, enters),
        astate(ef.id, ids["EF"], 220, -160, announce + exits + settle, reset=True),
        astate(eb.id, ids["EB"], 220, 0, announce + exits + settle, reset=True),
        astate(er.id, ids["ER"], 220, 160, announce + exits + settle, reset=True),
        astate(idle.id, ids["SH"], 460, 0, exits + froz),
        astate(fz.id, ids["FZ"], 460, 160, exits + [tr(ids["SH"], [c_bool("_frozen", False)], 200)]),
        astate(xf.id, ids["XF"], 700, -160, reenters + [tr(ids["H"], [], 0, exit_pct=100)], reset=True),
        astate(xb.id, ids["XB"], 700, 0, reenters + [tr(ids["H"], [], 0, exit_pct=100)], reset=True),
        astate(xr.id, ids["XR"], 700, 160, reenters + [tr(ids["H"], [], 0, exit_pct=100)], reset=True),
    ]
    if k == 10:
        states.append(astate(idle.id, ids["SF"], 460, -160,
                             [el("StateMachineFireEvent", {"eventId": EV["recapFinished"], "occursValue": 0}),
                              a_trig("_evtRecapFinished"), a_bool("_finished", True)] + exits + froz))
    return layer(f"Scene {k}", ids["H"], states)


def motif_layer():
    ids = {k: nid() for k in POSES}
    anims = {}
    for k, (x, y, s, r, o) in POSES.items():
        a = Anim(f"Motif pose {k}", 1)
        for p, v in (("x", x), ("y", y), ("scaleX", s), ("scaleY", s), ("rotation", r), ("opacity", o)):
            a.hold(M["root"], p, v)
        a.hold(M["tyear"], "opacity", 0 if k == 2 else 1)
        a.hold(M["tsaved"], "opacity", 1 if k == 2 else 0)
        a.hold(M["pathcoin"], "opacity", 1 if k in (1, 2) else 0)
        anims[k] = a
        ANIMS.append(a)
    states = []
    for k in POSES:
        trs = []
        for j in POSES:
            if j == k:
                continue
            cs = c_num("currentScreen", "equal", j)
            trs.append(tr(ids[j], [cs, c_bool("reducedMotion", True)], 0))
            trs.append(tr(ids[j], [cs, c_bool("reducedMotion", False)], 760, ease=(0.6, 0.0, 0.25, 1.0)))
        states.append(astate(anims[k].id, ids[k], 200 * ((k - 1) % 5), 160 * ((k - 1) // 5), trs))
    return layer("Motif (persistent machine)", ids[1], states)


def handoff_layer():
    rest, fwd, back = handoff_anims()
    ANIMS.extend([rest, fwd, back])
    i, fa, fb, ba, bb = (nid() for _ in range(5))
    F, B = c_trig("_handoffFwd"), c_trig("_handoffBack")
    states = [
        astate(rest.id, i, 0, 0, [tr(fa, [F]), tr(ba, [B])]),
        astate(fwd.id, fa, 240, -120, [tr(fb, [F]), tr(ba, [B]), tr(i, [], 0, exit_pct=100)], reset=True),
        astate(fwd.id, fb, 480, -120, [tr(fa, [F]), tr(ba, [B]), tr(i, [], 0, exit_pct=100)], reset=True),
        astate(back.id, ba, 240, 120, [tr(bb, [B]), tr(fa, [F]), tr(i, [], 0, exit_pct=100)], reset=True),
        astate(back.id, bb, 480, 120, [tr(ba, [B]), tr(fa, [F]), tr(i, [], 0, exit_pct=100)], reset=True),
    ]
    return layer("Handoff (coin and spring)", i, states)


def persona_layer():
    idle = Anim("Persona none", 1)
    for k in range(4):
        idle.hold(EMB[k]["root"], "opacity", 0)
    ANIMS.append(idle)
    revs, statics = {}, {}
    for k in range(4):
        a = Anim(f"Persona reveal {k}", 150)
        s = Anim(f"Persona static {k}", 1)
        for j in range(4):
            a.key(EMB[j]["root"], "opacity", [(0, 1 if j == k else 0, "hold")])
            s.hold(EMB[j]["root"], "opacity", 1 if j == k else 0)
        base = 44
        if k == 0:      # blocks stack one by one with squash
            for i, (b, x, y) in enumerate(EMB[0]["parts"]):
                t0 = base + i * 12
                a.key(b, "y", [(0, y - 340, "hold"), (t0, y - 340, "drop"), (t0 + 12, y, "out"), (t0 + 16, y - 8, "in"), (t0 + 20, y)])
                a.key(b, "scaleY", [(0, 1, "hold"), (t0 + 11, 1, "out"), (t0 + 13, 0.74, "soft"), (t0 + 20, 1.05, "soft"), (t0 + 26, 1)])
                a.key(b, "scaleX", [(0, 1, "hold"), (t0 + 11, 1, "out"), (t0 + 13, 1.18, "soft"), (t0 + 20, 0.97, "soft"), (t0 + 26, 1)])
                a.key(b, "opacity", [(0, 0, "hold"), (t0, 1)])
                for p, v in (("y", y), ("scaleX", 1), ("scaleY", 1), ("opacity", 1)):
                    s.hold(b, p, v)
            a.key(EMB[0]["parts"][-1][0], "rotation", [(0, 0, "hold"), (base + 56, 0, "inout"), (base + 70, 0.12, "inout"), (base + 90, 0)])
            s.hold(EMB[0]["parts"][-1][0], "rotation", 0)
        elif k == 1:    # tokens hop into the tray in arcs; the tray tilts to catch them
            for i, (t, x, y) in enumerate(EMB[1]["parts"]):
                t0 = base + i * 10
                sx = -200 + i * 200
                a.key(t, "x", [(0, sx, "hold"), (t0, sx, "soft"), (t0 + 18, x)])
                a.key(t, "y", [(0, -120, "hold"), (t0, -120, "rise"), (t0 + 9, -150, "drop"), (t0 + 18, y, "out"), (t0 + 22, y - 10, "in"), (t0 + 26, y)])
                a.key(t, "rotation", [(0, -2, "hold"), (t0, -2, "out"), (t0 + 18, 0)])
                a.key(t, "opacity", [(0, 0, "hold"), (t0, 1)])
                for p, v in (("x", x), ("y", y), ("rotation", 0), ("opacity", 1)):
                    s.hold(t, p, v)
            a.key(EMB[1]["root"], "rotation", [(0, 0, "hold"), (base + 16, 0, "inout"), (base + 22, 0.08, "inout"), (base + 34, -0.06, "inout"), (base + 46, 0)])
            s.hold(EMB[1]["root"], "rotation", 0)
        elif k == 2:    # coins wind into a spiral that keeps turning
            a.key(EMB[2]["spin"], "rotation", [(0, -3.2, "hold"), (base, -3.2, "out"), (base + 60, 0, "linear"), (150, 0.5)])
            a.key(EMB[2]["spin"], "scaleX", [(0, 0.2, "hold"), (base, 0.2, "out"), (base + 40, 1)])
            a.key(EMB[2]["spin"], "scaleY", [(0, 0.2, "hold"), (base, 0.2, "out"), (base + 40, 1)])
            s.hold(EMB[2]["spin"], "rotation", 0)
            s.hold(EMB[2]["spin"], "scaleX", 1)
            s.hold(EMB[2]["spin"], "scaleY", 1)
            for i, (c, x, y) in enumerate(EMB[2]["parts"]):
                t0 = base + i * 4
                a.key(c, "scaleX", [(0, 0, "hold"), (t0, 0, "out"), (t0 + 10, 1.2, "soft"), (t0 + 16, 1)])
                a.key(c, "scaleY", [(0, 0, "hold"), (t0, 0, "out"), (t0 + 10, 1.2, "soft"), (t0 + 16, 1)])
                s.hold(c, "scaleX", 1)
                s.hold(c, "scaleY", 1)
        else:           # calendar jar: rings snap, page flips, days tick in patiently
            a.key(EMB[3]["root"], "y", [(0, 180, "hold"), (base, 180, "out"), (base + 22, -8, "soft"), (base + 30, 0)])
            s.hold(EMB[3]["root"], "y", 0)
            a.key(EMB[3]["page"], "scaleY", [(0, 1, "hold"), (base + 30, 1, "in"), (base + 36, -1, "out"), (base + 42, 1)])
            s.hold(EMB[3]["page"], "scaleY", 1)
            for i, (d, x, y) in enumerate(EMB[3]["parts"]):
                t0 = base + 34 + i * 6
                a.key(d, "opacity", [(0, 0, "hold"), (t0, 0, "linear"), (t0 + 4, 1)])
                a.key(d, "scaleX", [(0, 0.5, "hold"), (t0, 0.5, "out"), (t0 + 8, 1)])
                a.key(d, "scaleY", [(0, 0.5, "hold"), (t0, 0.5, "out"), (t0 + 8, 1)])
                for p in ("opacity", "scaleX", "scaleY"):
                    s.hold(d, p, 1)
        revs[k], statics[k] = a, s
        ANIMS.extend([a, s])
    ids = {("R", k): nid() for k in range(4)}
    ids.update({("S", k): nid() for k in range(4)})
    none = nid()
    on9, off9 = c_num("currentScreen", "equal", 9), c_num("currentScreen", "notEqual", 9)
    rm_on, rm_off = c_bool("reducedMotion", True), c_bool("reducedMotion", False)

    def go(k):
        sl = c_num("_personaSlot", "equal", k)
        return [tr(ids[("S", k)], [on9, sl, rm_on]), tr(ids[("R", k)], [on9, sl, rm_off])]

    states = [astate(idle.id, none, 0, 0, sum((go(k) for k in range(4)), []))]
    for k in range(4):
        switch = []
        for j in range(4):
            if j != k:
                switch.append(tr(ids[("S", j)], [on9, c_num("_personaSlot", "equal", j)], 0))
        for kind, a in (("R", revs[k]), ("S", statics[k])):
            states.append(astate(a.id, ids[(kind, k)], 240 + (300 if kind == "S" else 0), -240 + k * 160,
                                 [tr(none, [off9], 0, exit_pct=None)] + switch, reset=True))
    return layer("Persona reveal", none, states)


def footer_layer(focus_target):
    nav = Anim("Footer story", 1)
    for b in ("prev", "next"):
        nav.key(CH[f"sem_{CH[b]}"], "isHidden", [(0, False, "hold")], "bool")
    for b in ("replay", "share"):
        nav.key(CH[f"sem_{CH[b]}"], "isHidden", [(0, True, "hold")], "bool")
    nav.hold(CH["nav_style"], "positionBottom", 0)
    nav.hold(CH["sum_style"], "positionBottom", -400)
    nav.hold(CH["nav"], "opacity", 1)
    nav.hold(CH["sum"], "opacity", 0)
    sm = Anim("Footer summary", 1)
    for b in ("prev", "next"):
        sm.key(CH[f"sem_{CH[b]}"], "isHidden", [(0, True, "hold")], "bool")
    for b in ("replay", "share"):
        sm.key(CH[f"sem_{CH[b]}"], "isHidden", [(0, False, "hold")], "bool")
    sm.hold(CH["nav_style"], "positionBottom", -400)
    sm.hold(CH["sum_style"], "positionBottom", 0)
    sm.hold(CH["nav"], "opacity", 0)
    sm.hold(CH["sum"], "opacity", 1)
    ANIMS.extend([nav, sm])
    a, b = nid(), nid()
    return layer("Footer mode", a, [
        astate(nav.id, a, 0, 0, [el("FocusActionTarget", {"targetId": focus_target}),
                                 tr(b, [c_num("currentScreen", "equal", 10)], 260, ease=(0.6, 0, 0.3, 1))]),
        astate(sm.id, b, 240, 0, [tr(a, [c_num("currentScreen", "notEqual", 10)], 260, ease=(0.6, 0, 0.3, 1))]),
    ])


def toy_layer():
    idle, nudge = toy_anims()
    ANIMS.extend([idle, nudge])
    a, b = nid(), nid()
    return layer("Coin toy", a, [
        astate(idle.id, a, 0, 0, [tr(b, [c_trig("_coinNudge")])]),
        astate(nudge.id, b, 240, 0, [tr(a, [], 120, exit_pct=100)], reset=True),
    ])


def key_listener(name, target, keys, action, mods=0):
    inputs = [el("KeyboardInput", {"keyType": k, "keyPhase": 1, "modifiers": mods}) for k in keys]
    return el("StateMachineListener", {"targetId": target, "name": name},
              [el("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"}, inputs)] + action)


def button_listener(name, target, actions, k):
    return [
        el("StateMachineListener", {"targetId": target, "name": name}, [
            el("ListenerInputType", {"listenerTypeValue": "click"}),
            el("ListenerInputTypeSemantic", {"listenerTypeValue": "semanticAction"}, [el("SemanticInput", {"actionType": "tap"})]),
            el("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"}, [
                el("KeyboardInput", {"keyType": "enter", "keyPhase": 1}), el("KeyboardInput", {"keyType": "kpEnter", "keyPhase": 1})]),
        ] + actions),
        el("StateMachineListener", {"targetId": target, "name": f"{name} focus"}, [
            el("ListenerInputType", {"listenerTypeValue": "focus"}), a_num("_focus", k)]),
        el("StateMachineListener", {"targetId": target, "name": f"{name} blur"}, [
            el("ListenerInputType", {"listenerTypeValue": "blur"}), a_num("_focus", 0)]),
    ]


# =====================================================================
# Assemble
# =====================================================================
MAIN = "0:2"


def main():
    mach = machine()
    builders = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8, scene9, scene10]
    for b in builders:
        b()
    scenes_xml = []
    for k in range(10, 0, -1):
        sc = SCENES[k]
        inner = el("Node", {"name": f"S{k} art", "x": -195, "y": -422, "id": nid()}, sc.items)
        content = el("Node", {"name": f"S{k} content", "x": 195, "y": 422, "id": sc.content}, [inner])
        scenes_xml.append(el("Node", {"name": f"Scene {k}", "id": sc.root, "opacity": 0}, [content] + bg_panel(sc)))
    toy = coin_toy()
    ho = handoff()
    stage = el("Node", {"name": "Stage (fit by director)", "id": nid()}, [
        bind(P("_stageX"), 13), bind(P("_stageY"), 14), bind(P("_stageScale"), 16), bind(P("_stageScale"), 17),
        toy, ho, mach] + scenes_xml)
    chrome_xml = chrome()
    director_box, _ = box("Director", nid(), dict(positionTypeValue="absolute", positionTop=0, positionBottom=0,
                                                   positionLeft=0, positionRight=0, widthUnitsValue="auto",
                                                   heightUnitsValue="auto"),
                          [el("ScriptedLayout", {"scriptAssetId": SCRIPTS["director"][0], "name": "Director", "id": nid()})])
    # ---- state machine
    layers = [scene_layer(SCENES[k]) for k in range(1, 11)]
    layers.append(motif_layer())
    layers.append(handoff_layer())
    layers.append(persona_layer())
    layers.append(footer_layer(MAIN))
    layers.append(toy_layer())
    listeners = [
        key_listener("Key next", MAIN, ["right"], [a_trig("navNext")]),
        key_listener("Key previous", MAIN, ["left"], [a_trig("navPrev")]),
        key_listener("Key pause", MAIN, ["space"], [a_trig("togglePause")]),
        key_listener("Tab", MAIN, ["tab"], [el("FocusActionTraversal", {"traversalKind": "next"})]),
        key_listener("Shift tab", MAIN, ["tab"], [el("FocusActionTraversal", {"traversalKind": "previous"})], mods=1),
        el("StateMachineListenerSingle", {"targetId": TOY["hit"], "listenerTypeValue": "click", "name": "Coin toy nudge"},
           [a_trig("_coinNudge")]),
    ]
    listeners += button_listener("Pause", CH["pause"], [a_trig("togglePause")], 1)
    listeners += button_listener("Previous", CH["prev"], [a_trig("navPrev")], 2)
    listeners += button_listener("Continue", CH["next"], [a_trig("navNext")], 3)
    listeners += button_listener("Replay", CH["replay"], [a_trig("replay")], 4)
    listeners += button_listener("Share", CH["share"], [el("ListenerFireEvent", {"eventId": EV["shareTapped"]}),
                                                        a_trig("_evtShareTapped")], 5)
    sm_id = "0:3"
    sm = el("StateMachine", {"name": "Recap", "id": sm_id}, listeners + layers)
    events = [el("Event", {"name": n, "id": i}) for n, i in EV.items()]
    style = "0:4"
    art = el("Artboard", {"defaultStateMachineId": sm_id, "viewModelId": VM, "viewModelInstanceId": VMI,
                          "styleId": style, "clip": True, "width": W, "height": H, "x": 0, "y": 0,
                          "name": "Recap", "id": MAIN},
             [el("LayoutComponentStyle", {"name": "Recap style", "id": style}),
              el("FocusData", {"name": "Keyboard surface", "id": nid()}),
              fill(INK, name="Backdrop"),
              director_box] + chrome_xml + [stage] + events + [sm] + [a.xml() for a in ANIMS])
    comps = [coin_artboard(), share_card(),
             el("ComponentAsset", {"artboardId": COIN_AB, "name": "Coin"}),
             el("ComponentAsset", {"artboardId": SHARE_AB, "name": "ShareCard"})]
    assets = [el("FontAsset", {"file": "assets/fonts/Rubik-VF.ttf", "name": "Rubik", "id": F_RUBIK}),
              el("FontAsset", {"file": "assets/fonts/NunitoSans-VF.ttf", "name": "Nunito Sans", "id": F_NUNITO})]
    scripts = [el("ScriptAsset", {"file": f, "isModule": mod or None, "name": n, "id": i})
               for n, (i, f, mod) in sorted(SCRIPTS.items(), key=lambda kv: kv[1][0])]
    hdr = "<!-- GENERATED by tools/gen.py -- see README.md. Editable RML; regenerate or edit by hand. -->\n"

    def write(name, body):
        with open(os.path.join(ROOT, name), "w") as f:
            f.write(hdr + el("Rive", {"version": 1, "kind": "fragment"}, body) + "\n")
    # scripts first so modules register before anything requires them
    write("a_data.rml", scripts + assets + [vm_xml()] + CONV)
    write("b_recap.rml", [art])
    write("c_components.rml", comps)
    write_fixtures()
    print("wrote", len(ANIMS), "animations,", len(CONV), "converters,", len(PROPS), "properties")


if __name__ == "__main__":
    main()
