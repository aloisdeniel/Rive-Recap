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
    # responsive layout: landscape when the artboard is at least this wide (points)
    ("layoutBreakpoint", "number", 768),
    # written by the director / state machine (read-only for hosts)
    ("_navDir", "number", 1), ("_visibleCount", "number", 10), ("_visibleIndex", "number", 1),
    ("_canGoBack", "bool", False), ("_canGoNext", "bool", True), ("_isSummary", "bool", False),
    ("_emptyState", "bool", False), ("_personaKnown", "bool", True), ("_personaSlot", "number", 0),
    ("_frozen", "bool", False), ("_holding", "bool", False), ("_finished", "bool", False),
    ("_pauseButtonLabel", "string", "Pause"), ("_focus", "number", 0),
    ("_chromeColor", "color", CREAM), ("_chromeOnColor", "color", INK),
    # responsive layout (director): orientation, the virtual stage (844 units
    # tall, as wide as the canvas), per-scene copy / art zones, chrome metrics
    ("_landscape", "bool", False), ("_split", "bool", False), ("_wideCard", "bool", False),
    ("_stageScale", "number", 1), ("_viewW", "number", W), ("_viewH", "number", H),
    ("_vcx", "number", W / 2), ("_rightOff", "number", 0), ("_barSX", "number", 1),
    ("_mfx", "number", 0), ("_mfy", "number", 0), ("_mfs", "number", 1),
    ("_hdrH", "number", 64), ("_ftrH", "number", 104), ("_ftrL", "number", 0), ("_ftrR", "number", 0),
    ("_btnH", "number", 54), ("_gpuRes", "number", 2), ("_gpuResStage", "number", 2),
    ("_handoffFwd", "trigger", None), ("_handoffBack", "trigger", None), ("_coinNudge", "trigger", None),
    # event mirrors: the CLI cannot observe Rive events, so each event also
    # fires one of these triggers on the same state/listener for verification
    ("_evtScreenChanged", "trigger", None), ("_evtRecapFinished", "trigger", None),
    ("_evtShareTapped", "trigger", None),
    # probes: pulsed by listeners that *hear* the three real Rive events (listener
    # type "event"), so headless checks observe the events themselves
    ("_heardScreenChanged", "trigger", None), ("_heardRecapFinished", "trigger", None),
    ("_heardShareTapped", "trigger", None),
] + [(f"_count{k}", "number", 0) for k in range(1, 11)] + [
    (f"_{z}{k}{a}", "number", 1 if a == "s" else 0) for k in range(1, 11) for z in "ca" for a in "xys"
] + [(f"_{z}{a}", "number", 1 if a == "s" else 0) for z in ("n10", "t7") for a in "xys"]
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


def write_poses():
    """motifpose.luau: the motif's per-scene pose and where its tap toy sits, so the
    director's hit test follows the machine (generated; keep in sync via gen.py)"""
    rows = ",\n".join(f"    [{k}] = {{ x = {x}, y = {y}, s = {sc}, r = {r}, on = {'true' if o else 'false'} }}"
                      for k, (x, y, sc, r, o) in POSES.items())
    src = ("--!strict\n-- GENERATED by tools/gen.py: the motif machine's pose per scene (design units)\n"
           "-- and the tap toy's resting point in machine space.\n"
           "export type Pose = { x: number, y: number, s: number, r: number, on: boolean }\n"
           "local M = {}\n"
           f"M.toy = {{ x = {TOY_AT[0]}, y = {TOY_AT[1]}, size = 40 }}\n"
           f"M.poses = {{\n{rows},\n}} :: {{ [number]: Pose }}\n"
           "return M\n")
    with open(os.path.join(ROOT, "motifpose.luau"), "w") as f:
        f.write(src)


# ---------------------------------------------------------------------
# Responsive layout boxes (design units of the 390 x 844 master). The director
# fits these into the real canvas (layoutboxes.luau, generated below):
#   copy     the copy zone's extent (headline slot, hero, unit, 2-line support)
#   art      the art zone's extent, motif machine pose included
#   artSplit art extent in a two-column split, when it differs (scene 7: the
#            ticket leaves for the copy column, the machine stays)
#   artWide  scene 10 with the wide card
#   ticket / note   extra zones that join the copy column in a split
#   stack    the vertical span the art claims under the copy in a portrait stack
#   minC / minA     the smallest scale at which the zone's smallest text is 11 px
# ---------------------------------------------------------------------
MIN_PX = 11.0
LAYOUT_BOXES = {
    1: dict(copy=(16, 78, 370, 300), art=(37, 312, 353, 740), stack=(300, 740), minC=MIN_PX / 16),
    2: dict(copy=(14, 55, 376, 376), art=(20, 347, 390, 764), stack=(376, 764), minC=MIN_PX / 18),
    3: dict(copy=(14, 55, 376, 390), art=(6, 372, 390, 750), stack=(390, 752), minC=MIN_PX / 18),
    4: dict(copy=(14, 55, 376, 434), art=(-20, 372, 410, 750), stack=(434, 752), minC=MIN_PX / 18),
    5: dict(copy=(14, 55, 376, 378), art=(43, 368, 363, 750), stack=(378, 752), minC=MIN_PX / 18),
    6: dict(copy=(14, 55, 376, 400), art=(43, 380, 347, 750), stack=(400, 752), minC=MIN_PX / 18),
    7: dict(copy=(28, 55, 362, 238), ticket=(28, 280, 362, 462), art=(27, 198, 363, 762), artSplit=(78, 430, 312, 762),
            stack=(238, 764), minC=MIN_PX / 18, minA=MIN_PX / 18),
    8: dict(copy=(14, 55, 376, 412), art=(27, 360, 363, 750), stack=(412, 752), minC=MIN_PX / 18),
    9: dict(copy=(15, 92, 375, 238), art=(9, 204, 381, 760), stack=(238, 762), minC=MIN_PX / 16),
    10: dict(copy=(100, 51, 290, 152), note=(100, 612, 290, 664), art=(20, 162, 372, 612),
             artWide=(-85, 236, 475, 548), stack=(160, 664), minC=MIN_PX / 17, minA=MIN_PX / 14.5,
             minAWide=MIN_PX / 15.5),
}


def write_boxes():
    def box(b):
        return f"{{ x0 = {b[0]}, y0 = {b[1]}, x1 = {b[2]}, y1 = {b[3]} }}"
    rows = []
    for k, d in LAYOUT_BOXES.items():
        f = [f"copy = {box(d['copy'])}", f"art = {box(d['art'])}"]
        for opt in ("artSplit", "artWide", "ticket", "note"):
            if opt in d:
                f.append(f"{opt} = {box(d[opt])}")
        f.append(f"stackTop = {d['stack'][0]}, stackBot = {d['stack'][1]}")
        f.append(f"minC = {d.get('minC', 0):.4f}, minA = {d.get('minA', 0):.4f}, minAWide = {d.get('minAWide', 0):.4f}")
        rows.append(f"    [{k}] = {{ " + ", ".join(f) + " }")
    src = ("--!strict\n-- GENERATED by tools/gen.py: per-scene responsive layout boxes in design units\n"
           "-- (390 x 844 master); the director fits them into the real canvas.\n"
           "export type Box = { x0: number, y0: number, x1: number, y1: number }\n"
           "export type SceneBoxes = { copy: Box, art: Box, artSplit: Box?, artWide: Box?, ticket: Box?, note: Box?,\n"
           "    stackTop: number, stackBot: number, minC: number, minA: number, minAWide: number }\n"
           "local M = {}\n"
           "M.scenes = {\n" + ",\n".join(rows) + ",\n} :: { [number]: SceneBoxes }\n"
           "return M\n")
    with open(os.path.join(ROOT, "layoutboxes.luau"), "w") as f:
        f.write(src)


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
                                     ("fmtMoneyExact", "scripts/fmt_money_exact.luau", False),
                                     ("coin3d", "scripts/coin3d.luau", False),
                                     ("jar3d", "scripts/jar3d.luau", False),
                                     ("spring3d", "scripts/spring3d.luau", False),
                                     ("motifpose", "motifpose.luau", True),
                                     ("crt", "scripts/crt.luau", False),
                                     ("layoutboxes", "layoutboxes.luau", True)]):
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
        # money counts in whole units (no flickering cents); the exact value,
        # cents included, only appears once the playhead reaches 1
        expr = (f"floor(in * $_count{k}) + (in - floor(in)) * floor($_count{k})" if k in MONEY_SCENES
                else f"in * $_count{k}")
        f = conv_formula(f"countUp{k}", expr)
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
TOY = {}


def coin(name, x, y, s=1.0, rot=0.0, cid=None, opacity=None, sx=None):
    """placement of the reusable Coin component (origin at its centre)"""
    return el("NestedArtboard", {"artboardId": COIN_AB, "x": x, "y": y, "scaleX": sx if sx is not None else s, "scaleY": s,
                                 "rotation": rot, "opacity": opacity, "name": name, "id": cid or nid()})


COIN_IN = ("size", "yaw", "pitch", "roll", "icon", "thick", "shine", "outline", "lightRoll")


def res_input(path="_gpuRes"):
    """canvas pixels per point for a scripted GPU drawable, bound to the director's
    estimate of the real on-screen scale so canvases follow the layout's zoom"""
    return el("ScriptInputNumber", {"propertyValue": 2, "name": "res"}, [bind(P(path), 243)])


def coin3d(name, size=58, icon=0, yaw=0.0, pitch=0.32, roll=0.0, outline=3.5, shine=0.55, thick=0.13,
           x=0, y=0, did=None, ids=None, gold=GOLD, opacity=None, light_roll=0.0, res="_gpuRes"):
    """a real 3D gold coin (scripts/coin3d): ScriptedDrawable with keyable inputs.

    ids (dict, optional) receives the ScriptInput ids by name so timelines can key
    yaw / pitch / roll (propertyKey 243)."""
    vals = {"size": size, "yaw": yaw, "pitch": pitch, "roll": roll, "icon": icon, "thick": thick,
            "shine": shine, "outline": outline, "lightRoll": light_roll}
    ins = []
    for k in COIN_IN:
        iid = nid()
        if ids is not None:
            ids[k] = iid
        ins.append(el("ScriptInputNumber", {"propertyValue": vals[k], "name": k, "id": iid}))
    ins.append(res_input(res))
    ins.append(el("ScriptInputColor", {"propertyValue": gold, "name": "gold"}))
    ins.append(el("ScriptInputColor", {"propertyValue": INK, "name": "ink"}))
    return el("ScriptedDrawable", {"scriptAssetId": SCRIPTS["coin3d"][0], "x": x, "y": y, "opacity": opacity,
                                   "name": name, "id": did or nid()}, ins)


def coin_art():
    """Coin component artwork: one 3D minted coin, ~64 units wide, resting pose"""
    return [coin3d("Coin 3D", 60, 0, 0.0, 0.34)]


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


def jar_profile(n=40):
    """the jar's half outline (radius, height above the floor), the same curve
    scripts/jar3d.wgsl lathes: a 178 x 198 rounded body (46 corners) + 64 neck"""
    R, RC, BODY_H, NECK, TOP = 89.0, 46.0, 198.0, 64.0, 217.0
    flat = R - RC
    side = BODY_H - 2 * RC
    dh = math.sqrt(RC * RC - (NECK - flat) ** 2)
    neck_h = BODY_H - RC + dh
    top_arc = math.asin(min(1.0, dh / RC))
    l0 = flat
    l1 = l0 + RC * math.pi / 2
    l2 = l1 + side
    l3 = l2 + RC * top_arc
    l4 = l3 + (TOP - neck_h)
    pts = []
    for i in range(n + 1):
        d = i / n * l4
        if d <= l0:
            pts.append((d, 0.0))
        elif d <= l1:
            a = (d - l0) / RC - math.pi / 2
            pts.append((flat + RC * math.cos(a), RC + RC * math.sin(a)))
        elif d <= l2:
            pts.append((R, RC + (d - l1)))
        elif d <= l3:
            a = (d - l2) / RC
            pts.append((flat + RC * math.cos(a), BODY_H - RC + RC * math.sin(a)))
        else:
            pts.append((NECK, neck_h + (d - l3)))
    return pts


def jar_outline(inset=0.0, floor_y=-75.0, n=40):
    prof = [(max(0.0, r - inset), h + inset * 0.5) for r, h in jar_profile(n) if r > 0.5]
    right = [(round(r, 2), round(floor_y - h, 2)) for r, h in prof]
    left = [(-x, y) for x, y in reversed(right)]
    return poly(right + left, closed=True, name="Jar profile")


def jar3d(name, layer, x=0, y=0):
    return el("ScriptedDrawable", {"scriptAssetId": SCRIPTS["jar3d"][0], "x": x, "y": y, "name": name, "id": nid()}, [
        el("ScriptInputNumber", {"propertyValue": layer, "name": "layer"}),
        el("ScriptInputNumber", {"propertyValue": 1, "name": "strength"}),
        el("ScriptInputNumber", {"propertyValue": 0.7, "name": "caustic"}),
        el("ScriptInputNumber", {"propertyValue": 0, "name": "sway", "id": M.setdefault(f"sway{layer}", nid())}),
        res_input(),
        el("ScriptInputColor", {"propertyValue": MINT, "name": "glass"}),
        el("ScriptInputColor", {"propertyValue": "FF4FB98F", "name": "edge"}),
    ])


TOY_AT = (112, -50)   # the toy coin rests at the mouth of the coin path (machine space)


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
    # pile: a bounded heap of 3D coins rises with scene 2's count (and stays)
    pile_conv = conv_formula("Jar fill", "176 - (0.16 + 0.84 * in) * 176 * min(1, $totalSaved / 400)")
    import random
    rnd = random.Random(7)
    pile_coins = []
    rows = 8
    for r in range(rows - 1, -1, -1):           # top rows first: drawn on top
        y = -88 - r * 19
        xs = [-60, -20, 20, 60] if r % 2 == 0 else [-74, -38, 0, 38, 74]
        for j, cx in enumerate(xs):
            sc = rnd.uniform(0.6, 0.68)
            pile_coins.append(coin(f"Pile coin {r}.{j}", cx + rnd.uniform(-5, 5), y + rnd.uniform(-4, 4), sc,
                                   rnd.uniform(-0.5, 0.5), sx=sc * rnd.uniform(0.86, 1.0)))
    pile = el("Node", {"name": "Coin pile", "id": M["pile"], "y": 176},
              [bind(P("_count2"), 14, pile_conv)] + pile_coins)
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
        shape("Label shine", [rect(96, 5, 2.5, y=-14)], [fill("88FFFFFF")]),
        shape("Label plate", [rect(116, 44, 22)], [fill(CREAM), stroke(INK, 3.5)]),
        shape("Label shadow", [rect(116, 44, 22, y=5)], [fill(alpha(INK, 0.28))]),
    ])
    tally = []
    for tid_, src, cnt, nm in ((M["tyear"], "year", 1, "Year tally"), (M["tsaved"], "totalSaved", 2, "Saved tally")):
        wins = [digit_window(f"{nm} {p}", -60 + (3 - p) * 40, -36, 32, 42, src, cnt, p, 4, 26, INK, 34)
                for p in range(4)]
        tally.append(el("Node", {"name": nm, "id": tid_, "opacity": 1 if cnt == 1 else 0}, wins))
    track_path = [(112, -60), ("c", 124, -170, -1.57, 46), ("c", 112, -286, -2.0, 34),
                  ("c", 66, -340, 3.0, 26), (26, -326)]
    # the signature interaction lives on the motif: a coin waiting at the mouth of
    # the coin path; tap it (director hit test) and it rides into the lid
    for k in ("slot", "coin", "hint"):
        TOY[k] = nid()
    TOY["ids"] = {}
    toy = el("Node", {"name": "Toy coin slot", "id": TOY["slot"], "x": TOY_AT[0], "y": TOY_AT[1]}, [
        el("Node", {"name": "Toy coin", "id": TOY["coin"]}, [coin3d("Toy coin 3D", 40, 0, 0.0, 0.2, ids=TOY["ids"],
                                                                     outline=3)]),
        shape("Toy hint", [ellipse(46, 46)], [stroke(alpha(PEACH, 0.95), 3.5)], sid=TOY["hint"], opacity=0),
    ])
    M["pathcoin_ids"] = {}
    # scene 2's falling coins live inside the machine (behind the near glass, in
    # front of the pile) so they are seen dropping through the jar
    M["drops"] = []
    drops = []
    for i in range(7):
        nid_, ids = nid(), {}
        M["drops"].append((nid_, ids))
        drops.append(el("Node", {"name": f"Drop coin {i}", "id": nid_, "x": 120, "y": -335, "opacity": 0},
                        [coin3d(f"Drop coin {i} 3D", 40, 0, 0.0, 0.3, ids=ids, outline=3)]))
    parts = [
        toy,
        el("Node", {"name": "Path coin", "id": M["pathcoin"], "x": 124, "y": -170, "scaleX": 0, "scaleY": 0},
           [coin3d("Riding coin 3D", 40, 0, 0.0, 0.2, ids=M["pathcoin_ids"], outline=3)]),
        shape("Coin path rail", [poly(track_path, closed=False)], [stroke(CREAM, 4, name="Rail shine")], x=-2, y=-3,
              opacity=0.55),
        shape("Coin path", [poly(track_path, closed=False)], [stroke(INK, 24), stroke(MINT, 15, name="Track")]),
        el("Node", {"name": "Lid", "id": M["lid"], "y": -300}, [
            shape("Slot", [rect(56, 9, 4.5, y=-16)], [fill(INK)]),
            shape("Lid shine", [rect(112, 5, 2.5, y=-8)], [fill("99FFFFFF")]),
            shape("Lid cap", [rect(152, 32, 13)], [fill(grad=lin([(0, GRAPE_L), (0.55, GRAPE), (1, GRAPE_D)], 0, -16, 0, 16)),
                                                  stroke(INK, 4)]),
        ]),
        label,
        shape("Glass outline", [jar_outline()], [stroke(INK, 4.5)]),
        jar3d("Glass front 3D", 1, 0, -75),
    ] + drops + [
        jar_inner,
        shape("Jar clip shape", [jar_outline(inset=5)], [], sid=jar_clip),
        jar3d("Glass back 3D", 0, 0, -75),
    ]
    jar = el("Node", {"name": "Jar", "id": M["jar"]}, parts)
    plinth = [
        sparkle("Rivet L", -100, -38, 15, PEACH), sparkle("Rivet R", 100, -38, 15, PEACH),
    ] + tally + [
        shape("Tally bezel", [rect(170, 54, 12, y=-36)], [fill(INK)]),
        shape("Plinth lip shine", [rect(220, 4, 2, y=-77)], [fill("66FFFFFF")]),
        shape("Plinth lip", [rect(248, 20, 10, y=-72)], [fill(GRAPE_L), stroke(INK, 4)]),
        shape("Plinth", [rect(232, 74, 20, y=-37)], [fill(grad=lin([(0, GRAPE), (1, GRAPE_D)], 0, -70, 0, 0)), stroke(INK, 4)]),
        shape("Foot L", [rect(40, 14, 5, x=-78, y=4)], [fill(INK)]),
        shape("Foot R", [rect(40, 14, 5, x=78, y=4)], [fill(INK)]),
        shape("Machine shadow", [ellipse(270, 26, y=10)], [fill(alpha(INK, 0.3), feather=el("Feather", {"strength": 8}))]),
    ]
    bob = el("Node", {"name": "Machine bob", "id": M["bob"]}, [jar] + plinth)
    return el("Node", {"name": "Toy machine (motif)", "id": M["root"], "x": 195, "y": 690}, [bob])


# per-scene poses of the machine: x, y, scale, rotation, opacity
POSES = {
    1: (195, 712, 1.0, 0.0, 1), 2: (195, 726, 1.04, 0.0, 1), 3: (306, 738, 0.42, 0.0, 1),
    4: (84, 738, 0.4, -0.04, 1), 5: (306, 738, 0.42, 0.04, 1), 6: (195, 740, 0.36, 0.0, 1),
    7: (195, 742, 0.86, 0.0, 1), 8: (306, 738, 0.42, 0.0, 1), 9: (195, 746, 0.62, 0.0, 1),
    10: (195, 1080, 0.8, 0.0, 0),
}


# =====================================================================
# Scene framework
# =====================================================================
FWD_BASE = 34     # frame at which an incoming (forward) panel has (nearly) landed
BACK_BASE = 6
ENTER_LEN = 150   # 2.5 s: entrance + resolve; the director starts dwell after this
IDLE_LEN = 240


class Scene:
    def __init__(self, k, bg, dark):
        self.k = k
        self.bg = bg
        self.dark = dark
        # responsive zones: "copy" (headline, hero, unit, support), "art" (the
        # illustration, which the motif machine joins), "note" (scene 10's support
        # line) and "back" (backdrop twinkles); each zone is one node whose
        # transform the director binds per viewport
        self.zones = {"copy": [], "ticket": [], "art": [], "note": [], "back": []}
        self.zone = "art"
        self.keys = []      # (obj, prop, kfs relative to base, kind)
        self.idle = []      # (obj, prop, kfs, kind) looped over IDLE_LEN
        self.root = nid()
        self.content = nid()
        self.sem = []       # SemanticData ids hidden while the scene is not current
        self.ink = INK if not dark else CREAM

    @property
    def items(self):
        return self.zones[self.zone]

    @items.setter
    def items(self, value):
        self.zones[self.zone] = value

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


HEAD_BOTTOM = 176    # metric headlines sit on this line, so 2 or 3 lines both fit


def scene_text(sc, hx, hbottom, hw, halign="center", size=36, sup=None, color=None, hl_color=None):
    """headline (word cascade) + support line, the stable copy area.

    The headline slot is three lines tall and bottom-aligned on `hbottom`, so
    copy that needs a third line (e.g. +40% translations) grows upward at its
    full size instead of shrinking; only a fourth line triggers fitFontSize."""
    color = color or sc.ink
    prev_zone, sc.zone = sc.zone, "copy"
    rid = nid()
    hid = nid()
    head_path = {1: "introHeadline", 10: "summaryHeadline"}.get(sc.k, f"screen{sc.k}Headline")
    ox = {"left": 0, "center": 0.5, "right": 1}[halign]
    lh = size * 1.08
    slot = round(lh * 3 + 4)
    sc.items.append(text(f"S{sc.k} headline", hx, hbottom - slot, [run(head_path, "", font="rubik", size=size,
                                                                     color=hl_color or color, weight=800, lh=lh)],
                         width=hw, align=halign, ox=ox, tid=hid, extra=[sem(sc, "text", head_path, heading=1), word_cascade(rid)],
                         sizing="fixed", height=slot, overflow="fitFontSize", valign="bottom"))
    sc.key(rid, "modifyFrom", [(30, -0.45, "soft"), (74, 1.05)])
    sc.key(rid, "falloffFrom", [(30, -0.05, "soft"), (74, 1.45)])
    if sup:
        sx, sy, sw, salign = sup
        sid = nid()
        sup_path = {1: "introSupport", 10: "summarySupport"}.get(sc.k, f"screen{sc.k}Support")
        sc.items.append(text(f"S{sc.k} support", sx, sy, [run(sup_path, "", font="nunito", size=18,
                                                               color=color, weight=600, lh=24)],
                             width=sw, align=salign, ox={"left": 0, "center": 0.5, "right": 1}[salign], tid=sid,
                             extra=[sem(sc, "text", sup_path)]))
        sc.rise(sid, 62, 14, 26, y=sy)
    sc.zone = prev_zone
    return hid


def copy_block(sc, size, hero_color, unit_color=None, outline=None, sup_color=None, sup_w=300, gap=14):
    """the shared metric layout: centred headline, hero value, unit, support line.
    Returns the y below the block, where the scene's illustration may start."""
    prev_zone, sc.zone = sc.zone, "copy"
    scene_text(sc, 195, HEAD_BOTTOM, 334, "center", 36, color=sc.ink)
    hy = HEAD_BOTTOM + gap + size * 0.56
    uy = hy + size * 0.56 + 8
    hero_number(sc, 195, round(hy), size, hero_color, outline=outline,
                unit=(195, round(uy), 362, "center"), unit_color=unit_color or sc.ink)
    sy = uy + 34
    sid = nid()
    sc.items.append(text(f"S{sc.k} support", 195, round(sy), [run(f"screen{sc.k}Support", "", font="nunito", size=18,
                                                                  color=sup_color or sc.ink, weight=600, lh=24)],
                         width=sup_w, align="center", ox=0.5, tid=sid, extra=[sem(sc, "text", f"screen{sc.k}Support")]))
    sc.rise(sid, 62, 14, 26, y=round(sy))
    sc.zone = prev_zone
    return sy + 38


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
                             width=uw, align=ualign, ox={"left": 0, "center": 0.5, "right": 1}[ualign], tid=uid,
                             sizing="fixed", height=26, overflow="fitFontSize", wrap="noWrap", valign="top"))
        sc.rise(uid, 22, 12, 20, y=uy)
    return nid_


def bg_panel(sc):
    """full-bleed scene backdrop with a chunky outlined top edge (what the spring
    pushes). 12000 units wide, so it bleeds past any viewport (the stage is 844
    units tall and as wide as the canvas)."""
    return [
        shape(f"S{sc.k} panel edge", [rect(12000, 3200, 0, y=-140, oy=0)], [fill(sc.bg)]),
        shape(f"S{sc.k} panel lip", [rect(12000, 10, 0, y=-150, oy=0)], [fill(INK)]),
    ]


def deco_bg(sc, seed, color, n=7, wings=10):
    """quiet background starbursts / dots: mid-ground depth. They live in the
    scene's backdrop zone, centred on the viewport; the `wings` beyond the 390-unit
    design column only show when the viewport is wider than the design."""
    import random
    rnd = random.Random(seed)
    out = []
    spots = [(rnd.uniform(20, 370), rnd.uniform(90, 720)) for _ in range(n)]
    for i in range(wings):
        side = -1 if i % 2 == 0 else 1
        x = 195 + side * rnd.uniform(230, 1050)
        spots.append((x, rnd.uniform(100, 760)))
    for i, (x, y) in enumerate(spots):
        s = rnd.uniform(8, 16)
        sid = nid()
        out.append(sparkle(f"S{sc.k} twinkle {i}", x, y, s, color, sid=sid, opacity=0.55))
        ph = rnd.randint(0, 200)
        sc.loop(sid, "scaleX", [(0, 1.0, "soft"), ((ph % 120) + 40, 0.55, "soft"), (IDLE_LEN, 1.0)])
        sc.loop(sid, "scaleY", [(0, 1.0, "soft"), ((ph % 120) + 40, 0.55, "soft"), (IDLE_LEN, 1.0)])
    sc.zones["back"] += out
    return []


BG = {1: GRAPE_D, 2: GRAPE, 3: CREAM, 4: MINT, 5: CREAM, 6: INK, 7: PEACH, 8: MINT, 9: GRAPE, 10: GRAPE_D}
DARK = {1, 2, 6, 9, 10}


def new_scene(k):
    sc = Scene(k, BG[k], k in DARK)
    SCENES[k] = sc
    return sc


# ---------------------------------------------------------------- 1
def scene1():
    sc = new_scene(1)
    sc.zone = "copy"
    tag = nid()
    sc.items.append(el("Node", {"name": "Name tag", "x": 24, "y": 96, "id": tag}, [
        sem(sc, "text", "userName"),
        text("Name", 40, 0, [run("userName", "", font="nunito", size=18, color=MINT, weight=800, lh=22)],
             width=280, sizing="fixed", height=24, overflow="ellipsis", wrap="noWrap", oy=0.5, valign="middle"),
        sparkle("Tag star", 15, 0, 18, GRAPE),
        shape("Tag plate", [ellipse(32, 32, x=15)], [fill(MINT), stroke(INK, 3)]),
    ]))
    sc.pop(tag, 0, 0.6, 1.08, 20)
    scene_text(sc, 24, 232, 342, "left", 46, sup=(24, 240, 330, "left"), color=CREAM)
    pid = nid()
    sc.items.append(text("Period", 24, 274, [run("periodLabel", "", font="nunito", size=16, color=MINT, weight=700, lh=21)],
                         width=330, tid=pid, extra=[sem(sc, "text", "periodLabel")]))
    sc.rise(pid, 70, 10, 24, y=274)
    sc.zone = "art"
    sb = nid()
    sc.items.append(burst("Machine burst", 195, 470, 136, 158, 18, alpha(PEACH, 0.8), 5, bid=sb))
    sc.key(sb, "rotation", [(30, -0.4, "out"), (80, 0)])
    sc.key(sb, "opacity", [(30, 0, "linear"), (44, 1)])
    sc.loop(sb, "rotation", [(0, 0), (IDLE_LEN, 0.3491)])
    sc.items += deco_bg(sc, 11, MINT)
    # the machine drops in and lands with squash; the wordmark rises through the label window
    sc.key(M["bob"], "y", [(0, -820, "drop"), (24, 0, "out"), (31, -30, "in"), (38, 0, "out"), (43, -7, "in"), (47, 0)])
    sc.key(M["bob"], "scaleY", [(0, 1.06, "linear"), (24, 1.06, "out"), (28, 0.84, "soft"), (36, 1.05, "soft"), (44, 1.0)])
    sc.key(M["bob"], "scaleX", [(0, 0.96, "linear"), (24, 0.96, "out"), (28, 1.12, "soft"), (36, 0.97, "soft"), (44, 1.0)])
    sc.key(M["label"], "y", [(40, 50, "out"), (64, -4, "soft"), (72, 0)])
    # a coin rides the path into the lid, spinning in 3D as it climbs
    sc.key(M["pathcoin"], "x", [(46, 114, "linear"), (60, 124, "linear"), (72, 112, "linear"), (82, 66, "linear"), (90, 26)])
    sc.key(M["pathcoin"], "y", [(46, -70, "linear"), (60, -170, "linear"), (72, -290, "linear"), (82, -352, "linear"), (90, -330)])
    sc.key(M["pathcoin"], "scaleX", [(46, 0, "out"), (52, 1, "linear"), (88, 1, "in"), (96, 0)])
    sc.key(M["pathcoin"], "scaleY", [(46, 0, "out"), (52, 1, "linear"), (88, 1, "in"), (96, 0)])
    sc.key(M["pathcoin_ids"]["yaw"], 243, [(46, 0, "linear"), (92, 2 * TAU)])
    sc.key(M["pathcoin_ids"]["roll"], 243, [(46, 0, "linear"), (92, -3.0)])
    sc.key(M["lid"], "y", [(92, -300, "out"), (96, -306, "soft"), (104, -300)])
    # ... and a fresh coin pops into the mouth of the path: the tap toy
    sc.key(TOY["slot"], "scaleX", [(0, 0, "hold"), (98, 0, "out"), (108, 1.18, "soft"), (116, 1)])
    sc.key(TOY["slot"], "scaleY", [(0, 0, "hold"), (98, 0, "out"), (108, 1.18, "soft"), (116, 1)])
    return sc


# ---------------------------------------------------------------- 2
def scene2():
    sc = new_scene(2)
    copy_block(sc, 84, PEACH, unit_color=MINT, outline=(INK, 8), sup_color=CREAM)
    hy = HEAD_BOTTOM + 14 + 84 * 0.56
    for side, (bx, start) in enumerate(((195 - 158, 2.4), (195 + 158, -0.7))):
        b = nid()
        sc.zones["copy"].append(burst(f"Hero ticks {side}", bx, hy, 14, 28, 3, PEACH, 4.5, bid=b, sweep=1.4, start=start))
        sc.pop(b, 26, 0.2, 1.3, 18)
    # chute that feeds the jar
    chute = nid()
    sc.items.append(el("Node", {"name": "Chute", "id": chute}, [
        shape("Chute mouth", [ellipse(40, 14, x=198, y=396)], [fill(INK)]),
        shape("Chute stripe", [poly([(1700, 380), (280, 380), ("c", 220, 382, 1.3, 16), (198, 394)], closed=False)],
              [stroke(MINT, 6)], y=-6),
        shape("Chute", [poly([(1700, 380), (280, 380), ("c", 220, 382, 1.3, 16), (198, 394)], closed=False)],
              [stroke(INK, 40, cap="butt"), stroke(GRAPE_L, 30, cap="butt", name="Pipe")]),
    ]))
    sc.key(chute, "x", [(0, 220, "out"), (26, 0)])
    # a bounded pool of 3D coins tumbles out of the chute, through the lid slot and
    # down through the glass onto the rising pile, in time with the count
    import random
    rnd = random.Random(2)
    px, py, ps = POSES[2][0], POSES[2][1], POSES[2][2]
    loc = lambda x, y: ((x - px) / ps, (y - py) / ps)
    count_start = round(1.05 * 60) - FWD_BASE          # the director's COUNT[2] window (linear, 0.95 s)
    for i, (c, ids) in enumerate(M["drops"]):
        t0 = 18 + i * 6
        land = t0 + 20
        f = min(1.0, max(0.0, (land - count_start) / 57.0))
        top = -221 + 176 * (1 - (0.16 + 0.84 * f)) - 8    # the pile's surface then (machine space)
        tx = rnd.uniform(-50, 50)
        ty = top + rnd.uniform(-6, 6)
        sx, sy = loc(320, 378)
        mx, my = loc(198, 398)
        turn = rnd.choice([-1, 1]) * rnd.uniform(1.6, 2.4) * TAU
        sc.key(c, "opacity", [(t0, 0, "hold"), (t0 + 1, 1, "linear"), (land + 8, 1, "linear"), (land + 16, 0)])
        sc.key(c, "x", [(t0, sx, "linear"), (t0 + 7, mx, "soft"), (land, tx)])
        sc.key(c, "y", [(t0, sy, "linear"), (t0 + 7, my, "drop"), (land, ty, "out"), (land + 5, ty - 12, "in"), (land + 9, ty)])
        sc.key(ids["yaw"], 243, [(t0, 0, "linear"), (t0 + 7, 0.6, "out"), (land + 8, turn)])
        sc.key(ids["pitch"], 243, [(t0, 0.3, "linear"), (land, rnd.uniform(-0.6, 0.9), "out"), (land + 8, 0.5)])
    # the jar overflows: a few coins tumble out round the base
    for i, (x, y, s, r) in enumerate(((40, 722, 0.66, -0.5), (74, 744, 0.52, 0.4), (362, 740, 0.6, 0.6))):
        c = nid()
        sc.items.insert(0, el("Node", {"name": f"Spill coin {i}", "id": c, "x": x, "y": y, "opacity": 0},
                              [coin(f"Spill coin {i} art", 0, 0, s, r)]))
        t0 = 84 + i * 6
        sc.key(c, "opacity", [(t0, 0, "hold"), (t0 + 1, 1)])
        sc.key(c, "y", [(t0, y - 70, "drop"), (t0 + 12, y, "out"), (t0 + 16, y - 9, "in"), (t0 + 20, y)])
        sc.key(c, "x", [(t0, 195 + (x - 195) * 0.55, "out"), (t0 + 14, x)])
    sc.items += deco_bg(sc, 22, MINT, 6)
    sc.key(M["lid"], "y", [(88, -300, "out"), (92, -308, "soft"), (100, -300)])
    # a glint sweeps across the glass once the jar has filled
    sc.key(M["sway1"], 243, [(76, 0.55, "inout"), (104, -0.18, "soft"), (114, 0)])
    return sc


# ---------------------------------------------------------------- 3
def scene3():
    sc = new_scene(3)
    copy_block(sc, 96, GRAPE, unit_color=INK)
    board = nid()
    wins = [digit_window(f"Deposit tally {p}", -96 + (3 - p) * 64, 0, 54, 74, "deposits", 3, p, 4, 46, INK, 60)
            for p in range(4)]
    sc.items.append(el("Node", {"name": "Tally board", "x": 195, "y": 430, "id": board}, wins + [
        sparkle("Board rivet a", -150, -40, 13, PEACH), sparkle("Board rivet b", 150, -40, 13, PEACH),
        sparkle("Board rivet c", -150, 40, 13, PEACH), sparkle("Board rivet d", 150, 40, 13, PEACH),
        shape("Board bezel shine", [rect(250, 4, 2, y=-40)], [fill("33FFFFFF")]),
        shape("Board bezel", [rect(270, 92, 16)], [fill(INK)]),
        shape("Board shine", [rect(300, 6, 3, y=-50)], [fill("55FFFFFF")]),
        shape("Board", [rect(330, 116, 26)], [fill(grad=lin([(0, GRAPE_L), (1, GRAPE)], 0, -58, 0, 58)), stroke(INK, 5)]),
        shape("Board shadow", [rect(330, 116, 26, y=10)], [fill(alpha(INK, 0.25))]),
    ]))
    sc.key(board, "y", [(0, 520, "out"), (18, 422, "soft"), (28, 430)])
    sc.key(board, "rotation", [(0, 0.12, "out"), (24, 0)])
    sc.key(board, "opacity", [(0, 0, "linear"), (8, 1)])
    # pachinko zigzag: a 3D coin rolls every rail and drops into the machine's lid
    lid = (POSES[3][0], POSES[3][1] - POSES[3][2] * 312)
    zz = [(36, 512), (318, 538), (70, 564), (264, 590), lid]
    R = 18
    rail_pts = [(x, y + R + 3) for x, y in zz[:4]]
    sc.items.append(shape("Zigzag rail shine", [poly(rail_pts, closed=False)], [stroke(alpha(CREAM, 0.85), 3)], y=-3))
    sc.items.append(shape("Zigzag rail", [poly(rail_pts, closed=False)],
                          [stroke(INK, 15), stroke(MINT_D, 8, name="Rail")]))
    for i, (x, y) in enumerate(rail_pts[1:3]):
        sc.items.append(shape(f"Bumper {i}", [ellipse(22, 22, x=x + (10 if i == 0 else -10), y=y - 6)],
                              [fill(PEACH), stroke(INK, 3.5)]))
    pegs = [(x, y) for x, y in ((60, 600), (110, 610), (160, 604), (330, 576), (300, 600), (22, 548), (190, 530))]
    sc.items.append(shape("Pachinko pegs", [ellipse(7, 7, x=x, y=y) for x, y in pegs], [fill(alpha(GRAPE, 0.45))]))
    sc.items.append(shape("Pachinko board", [rect(356, 118, 22, x=184, y=566)],
                          [fill(alpha(GRAPE, 0.07)), stroke(alpha(GRAPE, 0.22), 3)]))
    zc = nid()
    ids = {}
    sc.items.insert(0, el("Node", {"name": "Zigzag coin", "id": zc, "x": 372, "y": 470},
                          [coin3d("Zigzag coin 3D", R * 2, 0, 0.0, 0.0, ids=ids, outline=3)]))
    seg = [0, 18, 34, 48, 62]
    sc.key(zc, "x", [(30 + f, x, "inout" if i < 3 else "out") for i, (f, (x, y)) in enumerate(zip(seg, zz))])
    sc.key(zc, "y", [(30 + f, y, "inout" if i < 3 else "drop") for i, (f, (x, y)) in enumerate(zip(seg, zz))])
    roll, rolls = 0.0, [(30, 0.0, "inout")]
    for i in range(3):
        (x0, y0), (x1, y1) = zz[i], zz[i + 1]
        roll += -math.copysign(math.hypot(x1 - x0, y1 - y0) / R, x1 - x0)
        rolls.append((30 + seg[i + 1], roll, "inout"))
    sc.key(ids["roll"], 243, rolls)
    sc.key(ids["yaw"], 243, [(30 + seg[3], 0, "out"), (30 + seg[4], 4.7)])
    sc.key(zc, "opacity", [(29, 0, "hold"), (30, 1, "linear"), (30 + seg[4] - 2, 1, "linear"), (30 + seg[4] + 2, 0)])
    sc.key(zc, "scaleX", [(30 + seg[3], 1, "in"), (30 + seg[4] + 2, 0.5)])
    sc.key(zc, "scaleY", [(30 + seg[3], 1, "in"), (30 + seg[4] + 2, 0.5)])
    t = 30 + seg[4]
    sc.key(M["lid"], "y", [(t, -300, "out"), (t + 4, -316, "soft"), (t + 12, -300)])
    sc.items += deco_bg(sc, 33, PEACH, 6)
    return sc


# ---------------------------------------------------------------- 4
def token(name, kind, tid, inner_bind=None, size=64, ids=None):
    """a goal token: a 3D minted coin with the goal's icon (house, cap, palm)"""
    inner = el("Node", {"name": f"{name} face", "id": nid()}, ([inner_bind] if inner_bind else []) +
               [coin3d(f"{name} 3D", size, kind + 1, 0.0, 0.12, ids=ids, outline=3.5)])
    return el("Node", {"name": name, "id": tid}, [inner])


def scene4():
    sc = new_scene(4)
    copy_block(sc, 136, CREAM, unit_color=INK, outline=(INK, 9))
    hy = HEAD_BOTTOM + 14 + 136 * 0.56
    for side, (bx, start) in enumerate(((195 - 96, 2.3), (195 + 96, -0.75))):
        b = nid()
        sc.zones["copy"].append(burst(f"Yes ticks {side}", bx, hy, 16, 32, 3, GRAPE, 5, bid=b, sweep=1.5, start=start))
        sc.pop(b, 30, 0.2, 1.3, 18)
    TY = 534
    tray = nid()
    slots = []
    for i, x in enumerate((-100, 0, 100)):
        slots.append(shape(f"Slot {i}", [rect(82, 52, 14, x=x, y=-14)], [fill(INK)]))
        slots.append(shape(f"Slot glow {i}", [rect(64, 10, 5, x=x, y=-34)], [fill(alpha(GRAPE_L, 0.9))]))
    tray_parts = [
        sparkle("Plate star L", -40, 40, 12, GRAPE), sparkle("Plate star R", 40, 40, 12, GRAPE),
        shape("Plate", [rect(120, 26, 13, y=40)], [fill(MINT), stroke(INK, 3)]),
    ] + slots + [
        shape("Tray top shine", [rect(290, 5, 2.5, y=-44)], [fill("66FFFFFF")]),
        shape("Tray top", [rect(318, 74, 22, y=-14)], [fill(GRAPE_L), stroke(INK, 4.5)]),
        shape("Tray body", [rect(340, 124, 28, y=8)], [fill(grad=lin([(0, GRAPE), (1, GRAPE_D)], 0, -50, 0, 70)), stroke(INK, 5)]),
        shape("Tray shadow", [ellipse(330, 30, y=72)], [fill(alpha(INK, 0.22), feather=el("Feather", {"strength": 6}))]),
    ]
    # feeder rails that deliver two of the tokens; the third comes out of the machine
    for side in (-1, 1):
        pts = [(195 + side * 200, 398), (195 + side * 150, 412), ("c", 195 + side * 128, 424, 1.2 if side < 0 else 1.94, 10)]
        # sits 26 units lower than the first pass, clear of a one-line support
        sc.items.append(el("Node", {"name": f"Feeder {side}", "y": 26, "id": nid()}, [
            shape("Feeder flange", [rect(14, 50, 6, x=195 + side * 203, y=398)], [fill(GRAPE_D), stroke(INK, 3.5)]),
            shape("Feeder mouth", [ellipse(18, 30, x=195 + side * 128, y=426)], [fill(INK)]),
            shape("Feeder stripe", [poly(pts, closed=False)], [stroke(MINT, 5)], y=-7),
            shape("Feeder chute", [poly(pts, closed=False)], [stroke(INK, 36, cap="butt"), stroke(GRAPE_L, 26, cap="butt", name="Pipe")]),
        ]))
    sc.items.insert(0, el("Node", {"name": "Reward tray", "x": 195, "y": TY, "id": tray}, tray_parts))
    sc.key(tray, "y", [(0, TY + 100, "out"), (20, TY - 6, "soft"), (28, TY)])
    sc.key(tray, "opacity", [(0, 0, "linear"), (8, 1)])
    lid = (POSES[4][0], POSES[4][1] - POSES[4][2] * 312)
    starts = [(195 - 196, 424), lid, (195 + 196, 424)]
    peaks = [408, 430, 408]
    land = TY - 26
    for i, (sx, sy) in enumerate(starts):
        t = nid()
        ids = {}
        tb = bind(P("goalsCompleted"), 18, conv_formula(f"Token {i} shown", f"max(0, min(1, in - {i}))"))
        node = token(f"Goal token {i}", i, t, tb, ids=ids).replace(f'id="{t}"', f'id="{t}" x="{sx}" y="{sy}"', 1)
        sc.items.insert(0, node)
        t0 = 30 + i * 12
        tx = 195 + (i - 1) * 100
        sc.key(t, "x", [(t0, sx, "soft"), (t0 + 18, tx)])
        sc.key(t, "y", [(t0, sy, "rise"), (t0 + 9, peaks[i], "drop"), (t0 + 18, land, "out"), (t0 + 21, land - 8, "in"), (t0 + 24, land)])
        sc.key(t, "scaleY", [(t0, 0.5 if i == 1 else 1, "out"), (t0 + 10, 1, "linear"), (t0 + 18, 1, "out"),
                             (t0 + 20, 0.8, "soft"), (t0 + 26, 1.04, "soft"), (t0 + 30, 1)])
        sc.key(t, "scaleX", [(t0, 0.5 if i == 1 else 1, "out"), (t0 + 10, 1, "linear"), (t0 + 18, 1, "out"),
                             (t0 + 20, 1.14, "soft"), (t0 + 26, 0.98, "soft"), (t0 + 30, 1)])
        sc.key(t, "opacity", [(t0 - 1, 0, "hold"), (t0, 1)])
        flips = (1 if i != 1 else -1) * (2 if i != 1 else 3)
        sc.key(ids["yaw"], 243, [(t0, flips * TAU + (i - 1) * 0.6, "out"), (t0 + 20, 0)])
        sc.key(ids["pitch"], 243, [(t0, 0.7, "out"), (t0 + 20, 0.12)])
        f = nid()
        sc.items.insert(0, burst(f"Snap flash {i}", tx, land - 16, 40, 56, 10, PEACH, 5, bid=f, opacity=0))
        sc.key(f, "opacity", [(t0 + 18, 0, "linear"), (t0 + 19, 1, "linear"), (t0 + 30, 0)])
        sc.key(f, "scaleX", [(t0 + 18, 0.6, "out"), (t0 + 30, 1.25)])
        sc.key(f, "scaleY", [(t0 + 18, 0.6, "out"), (t0 + 30, 1.25)])
        sc.loop(t, "y", [(0, land, "inout"), (60 + i * 20, land - 4, "inout"), (120 + i * 20, land, "hold"), (IDLE_LEN, land)])
        sc.loop(ids["yaw"], 243, [(0, 0, "inout"), (70 + i * 25, 0.32 * (1 if i % 2 else -1), "inout"),
                                  (150 + i * 25, 0, "hold"), (IDLE_LEN, 0)])
    sc.key(M["lid"], "y", [(36, -300, "out"), (42, -330, "soft"), (54, -300)])
    sc.items += deco_bg(sc, 44, GRAPE_L, 6)
    return sc


# ---------------------------------------------------------------- 5
def scene5():
    sc = new_scene(5)
    copy_block(sc, 86, GRAPE, unit_color=INK, sup_w=270)
    cx, cy = 195, 520
    big = nid()
    flash = nid()
    bids = {}
    sc.items.append(el("Node", {"name": "Merged coin", "id": big, "x": cx, "y": cy, "scaleX": 1, "scaleY": 1},
                       [coin3d("Merged coin 3D", 150, 0, 0.0, 0.18, ids=bids, outline=5, shine=0.7)]))
    sc.items.append(burst("Merge flash", cx, cy, 92, 122, 14, GRAPE, 6, bid=flash, opacity=0))
    ring = shape("Orbit ring", [ellipse(268, 268)], [stroke(alpha(GRAPE, 0.35), 3)], x=cx, y=cy, sid=nid())
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
        mid_a = a + 0.9
        mx, my = cx + math.cos(mid_a) * 80, cy + math.sin(mid_a) * 80
        sc.key(c, "x", [(t0, sx, "soft"), (arrive - 12, mx, "in"), (arrive, cx)])
        sc.key(c, "y", [(t0, sy, "soft"), (arrive - 12, my, "in"), (arrive, cy)])
        sc.key(c, "opacity", [(t0 - 6, 0, "linear"), (t0, 1, "linear"), (arrive - 2, 1, "linear"), (arrive, 0)])
        sc.key(c, "scaleX", [(t0 - 6, 0.2, "out"), (t0, 1.0, "linear"), (arrive - 10, 1.0, "in"), (arrive, 0.6)])
        sc.key(c, "scaleY", [(t0 - 6, 0.2, "out"), (t0, 1.0, "linear"), (arrive - 10, 1.0, "in"), (arrive, 0.6)])
    # every arrival spins the growing coin faster; it brakes and settles face-on, catching the light
    sc.key(big, "scaleX", [(40, 0, "linear"), (46, 0.2, "out"), (78, 0.55, "out"), (86, 1.08, "soft"), (96, 1.0)])
    sc.key(big, "scaleY", [(40, 0, "linear"), (46, 0.2, "out"), (78, 0.55, "out"), (86, 1.08, "soft"), (96, 1.0)])
    sc.key(bids["yaw"], 243, [(40, 0, "in"), (78, 3.5 * TAU, "out"), (104, 4 * TAU)])
    sc.key(bids["pitch"], 243, [(40, 0.7, "linear"), (78, 0.5, "out"), (104, 0.18)])
    sc.key(flash, "opacity", [(78, 0, "linear"), (80, 1, "linear"), (96, 0)])
    sc.key(flash, "scaleX", [(78, 0.7, "out"), (96, 1.3)])
    sc.key(flash, "scaleY", [(78, 0.7, "out"), (96, 1.3)])
    sc.loop(bids["yaw"], 243, [(0, 4 * TAU, "inout"), (120, 4 * TAU + 0.42, "inout"), (IDLE_LEN, 4 * TAU)])
    sc.items += deco_bg(sc, 55, GRAPE_L, 6)
    return sc


# ---------------------------------------------------------------- 6
RANKS = [3, 7, 1, 10, 5, 12, 2, 9, 6, 11, 4, 8]


def scene6():
    sc = new_scene(6)
    copy_block(sc, 104, PEACH, unit_color=CREAM, sup_color=CREAM, sup_w=360)
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
    # the board is an arcade screen: a CRT pass (bloom from the lit windows,
    # scanlines, a slow refresh band, curved glass) over the vector windows
    band = nid()
    crt = el("ScriptedDrawable", {"scriptAssetId": SCRIPTS["crt"][0], "name": "Arcade screen (CRT)", "id": nid()}, [
        el("ScriptInputNumber", {"propertyValue": -200, "name": "band", "id": band}),
        el("ScriptInputNumber", {"propertyValue": 1, "name": "strength"}),
        el("ScriptInputNumber", {"propertyValue": 165, "name": "halfW"}),
        el("ScriptInputNumber", {"propertyValue": 118, "name": "halfH"}),
        res_input(),
        el("ScriptInputColor", {"propertyValue": PEACH, "name": "glow"}),
    ])
    sc.loop(band, 243, [(0, -200, "linear"), (40, -200, "linear"), (220, 190, "linear"), (IDLE_LEN, 190)])
    sc.items.append(el("Node", {"name": "Month windows", "x": 195, "y": 494, "scaleX": 0.92, "scaleY": 0.92, "id": grid}, [crt] + wins + [
        shape("Window board", [rect(330, 236, 30)], [fill(alpha(GRAPE, 0.35)), stroke(alpha(GRAPE_L, 0.6), 3)]),
    ]))
    sc.items += deco_bg(sc, 66, PEACH, 8)
    return sc


# ---------------------------------------------------------------- 7
def scene7():
    sc = new_scene(7)
    scene_text(sc, 195, HEAD_BOTTOM, 334, "center", 36, sup=(195, 188, 320, "center"), color=INK)
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
        text("Goal name", -22, -54, [run("completedGoalName", "", font="nunito", size=18, color=GRAPE, weight=800, lh=22)],
             width=220, align="center", ox=0.5, oy=0.5, sizing="fixed", height=24, overflow="ellipsis", wrap="noWrap"),
        text("S7 unit", -22, 44, [run("screen7Unit", "", font="nunito", size=18, color=INK, weight=800, lh=22)],
             width=226, align="center", ox=0.5, oy=0.5, sizing="fixed", height=24, overflow="fitFontSize", wrap="noWrap"),
        sparkle("Stub star", 118, 0, 30, GRAPE),
        shape("Perforation", [poly([(84, -70), (84, 70)], closed=False)],
              [el("Stroke", {"thickness": 3, "cap": "round", "name": "Dots"}, [solid(INK), el("DashPath", {"name": "Dash"}, [
                  el("Dash", {"length": 2, "name": "On"}), el("Dash", {"length": 8, "name": "Off"})])])]),
        shape("Notch L", [ellipse(30, 30, x=-150)], [fill(PEACH), stroke(INK, 4)]),
        shape("Notch R", [ellipse(30, 30, x=150)], [fill(PEACH), stroke(INK, 4)]),
        shape("Ticket shine", [rect(270, 5, 2.5, y=-74)], [fill("CCFFFFFF")]),
        shape("Ticket", [rect(300, 168, 18)], [fill(CREAM), stroke(INK, 5)]),
        shape("Ticket shadow", [rect(300, 168, 18, y=10)], [fill(alpha(INK, 0.25))]),
    ])
    # the ticket (it carries the scene's number) is its own zone: it rides the art
    # zone in a portrait stack, and joins the copy column in a two-column split
    sc.zone = "ticket"
    sc.items.append(el("Node", {"name": "Ticket slot reveal", "id": nid()},
                       [el("ClippingShape", {"sourceId": clip, "name": "Above lid"}), ticket]))
    sc.items.append(shape("Above lid mask", [rect(800, 900, 0, y=470, oy=1)], [], sid=clip))
    sc.key(tk, "y", [(10, 610, "out"), (46, 350, "soft"), (58, 370, "soft"), (66, 366)])
    sc.key(tk, "rotation", [(10, 0, "linear"), (40, 0, "soft"), (54, -0.07, "soft"), (66, -0.045)])
    sc.pop(hid, 40, 0.5, 1.1, 22)
    sc.key(M["lid"], "y", [(0, -300, "out"), (10, -340, "soft"), (60, -340, "out"), (70, -300)])
    sc.key(M["lid"], "rotation", [(0, 0, "out"), (10, -0.3, "soft"), (60, -0.3, "out"), (70, 0)])
    b = nid()
    # the burst rings the ticket in the stack only (in a split it would reach the copy)
    # squashed to hug the ticket, so its top ticks clear the support line
    sc.items.insert(0, el("Node", {"name": "Ticket burst (stack)", "x": 195, "y": 370, "scaleY": 0.74, "id": nid()}, [
        bind(P("_split"), 18, C["b2zero"]), burst("Ticket burst", 0, 0, 150, 168, 16, INK, 4, bid=b, opacity=0)]))
    sc.zone = "art"
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
        shape(f"{name} lid shine", [rect(24, 3, 1.5, y=-h / 2 - 7)], [fill("88FFFFFF")]),
        shape(f"{name} lid", [rect(34, 12, 4, y=-h / 2 - 4)], [fill(GRAPE), stroke(INK, 3)]),
        shape(f"{name} shine", [rect(5, h * 0.5, 2.5, x=-11, y=-h / 2 + 4)], [fill("88FFFFFF")]),
        shape(f"{name} body", [rect(44, h, 13, y=-h / 2 + 4)], [fill(color), stroke(INK, 3.5)]),
    ]


def scene8():
    sc = new_scene(8)
    copy_block(sc, 116, GRAPE, unit_color=INK)
    SY = 540
    shelf = nid()
    sc.items.append(el("Node", {"name": "Shelf", "id": shelf, "y": 0}, [
        shape("Shelf shine", [rect(318, 4, 2, x=195, y=SY - 5)], [fill("88FFFFFF")]),
        shape("Shelf plank", [rect(336, 18, 9, x=195, y=SY)], [fill(grad=lin([(0, PEACH), (1, PEACH_D)], 0, -9, 0, 9)), stroke(INK, 4)]),
        shape("Bracket L", [poly([(70, SY + 8), (70, SY + 44), (96, SY + 8)])], [fill(GRAPE), stroke(INK, 3.5)]),
        shape("Bracket R", [poly([(320, SY + 8), (320, SY + 44), (294, SY + 8)])], [fill(GRAPE), stroke(INK, 3.5)]),
        shape("Shelf shadow", [rect(330, 14, 7, x=195, y=SY + 14)], [fill(alpha(INK, 0.18))]),
    ]))
    sc.key(shelf, "y", [(0, 40, "out"), (18, 0)])
    sc.key(shelf, "opacity", [(0, 0, "linear"), (10, 1)])
    # the machine dispenses the jars: each one is launched from its lid and lands on the shelf
    lid = (POSES[8][0], POSES[8][1] - POSES[8][2] * 312)
    xs = [55, 111, 167, 223, 279, 335]
    land = SY - 14
    bumps = []
    for i, x in enumerate(xs):
        j = nid()
        shown = conv_formula(f"Jar {i} shown", f"max(0, min(1, in - {i}))")
        jar = el("Node", {"name": f"Goal jar {i}", "id": j, "x": lid[0], "y": lid[1], "opacity": 0}, [
            el("Node", {"name": f"Goal jar {i} art", "id": nid(), "scaleX": 1.22, "scaleY": 1.22},
               [bind(P("goalJars"), 18, shown)] + mini_jar(f"Jar {i}", JAR_COLORS[i], i % 2 == 0))])
        sc.items.insert(0, jar)
        t0 = 26 + (5 - i) * 7
        bumps.append(t0)
        rot0 = (i - 2.5) * 0.5 - 1.2
        peak = 392 - abs(x - lid[0]) * 0.18
        sc.key(j, "x", [(t0, lid[0], "linear"), (t0 + 24, x)])
        sc.key(j, "y", [(t0, lid[1], "rise"), (t0 + 12, peak, "drop"), (t0 + 24, land, "out"), (t0 + 28, land - 8, "in"), (t0 + 32, land)])
        sc.key(j, "scaleX", [(t0, 0.3, "out"), (t0 + 14, 1.0, "linear"), (t0 + 24, 1.0, "out"), (t0 + 26, 1.14, "soft"), (t0 + 32, 1)])
        sc.key(j, "scaleY", [(t0, 0.3, "out"), (t0 + 14, 1.0, "linear"), (t0 + 24, 1.0, "out"), (t0 + 26, 0.84, "soft"), (t0 + 32, 1)])
        sc.key(j, "rotation", [(t0, rot0, "out"), (t0 + 24, -0.08, "soft"), (t0 + 32, 0)])
        sc.key(j, "opacity", [(t0 - 1, 0, "hold"), (t0, 1)])
        sc.loop(j, "rotation", [(0, 0, "inout"), (40 + i * 25, 0.05 * (1 if i % 2 else -1), "inout"), (90 + i * 25, 0, "hold"), (IDLE_LEN, 0)])
    lid_keys = [(0, -300, "hold")]
    for t0 in sorted(bumps):
        lid_keys += [(t0 - 2, -300, "out"), (t0, -326, "soft"), (t0 + 4, -300, "hold")]
    sc.key(M["lid"], "y", lid_keys)
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
    sc.zone = "copy"
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
                         width=352, align="center", ox=0.5, tid=ds))
    sc.rise(ds, 70, 12, 22, y=186)
    sc.zone = "art"
    disc = nid()
    disc_parts = [el("Node", {"name": "Emblems", "id": nid(), "y": 6}, emblem_builder())] + [
        shape("Spotlight", [ellipse(250, 250)], [fill(PEACH, bind=bind(P("personaColor"), 37)), stroke(INK, 5)]),
        shape("Spotlight ring", [ellipse(284, 284)], [el("Stroke", {"thickness": 4, "cap": "round", "name": "Dashes"}, [
            solid(alpha(CREAM, 0.7)), el("DashPath", {"name": "Dash"}, [el("Dash", {"length": 10, "name": "On"}),
                                                                       el("Dash", {"length": 12, "name": "Off"})])])]),
    ]
    sc.items.append(el("Node", {"name": "Persona stage", "x": 195, "y": 390, "id": disc}, disc_parts))
    sc.key(disc, "scaleX", [(30, 0, "out"), (46, 1.08, "soft"), (56, 1)])
    sc.key(disc, "scaleY", [(30, 0, "out"), (46, 1.08, "soft"), (56, 1)])
    sc.loop(disc, "rotation", [(0, 0, "inout"), (120, 0.04, "inout"), (IDLE_LEN, 0)])
    rays = nid()
    sc.items.append(burst("Persona rays", 195, 390, 150, 186, 20, alpha(PEACH, 0.85), 6, bid=rays, opacity=0))
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
SHARE_WIDE_AB = "0:3150"
SHARE_WIDE_ASSEMBLE = nid()
CARD_Y = 386          # the card's centre in scene 10's design space


def scene10():
    sc = new_scene(10)
    scene_text(sc, 195, 152, 190, "center", 30, color=CREAM)
    # the support line is its own zone: under the card in a portrait stack,
    # under the headline in a two-column split
    sc.zone = "note"
    sid = nid()
    sc.items.append(text("S10 support", 195, 616, [run("summarySupport", "", font="nunito", size=17, color=CREAM,
                                                       weight=600, lh=23)],
                         width=184, align="center", ox=0.5, tid=sid, extra=[sem(sc, "text", "summarySupport")]))
    sc.rise(sid, 62, 14, 26, y=616)
    sc.zone = "art"
    mount, tall, wide, rt, rw = nid(), nid(), nid(), nid(), nid()
    # two arrangements of the same card, one shown at a time (_wideCard): the tall
    # collectible, and a wide one for canvases too short for the tall card's type
    sc.items.append(el("Node", {"name": "Card mount", "x": 195, "y": CARD_Y, "id": mount}, [
        el("NestedArtboard", {"artboardId": SHARE_AB, "name": "Share card", "id": tall},
           [bind(P("_wideCard"), 18, C["b2zero"]),
            el("NestedRemapAnimation", {"animationId": SHARE_ASSEMBLE, "time": 1, "name": "Assemble", "id": rt})]),
        el("NestedArtboard", {"artboardId": SHARE_WIDE_AB, "name": "Share card (wide)", "id": wide},
           [bind(P("_wideCard"), 18, C["b2one"]),
            el("NestedRemapAnimation", {"animationId": SHARE_WIDE_ASSEMBLE, "time": 1, "name": "Assemble", "id": rw})]),
    ]))
    sc.key(mount, "y", [(0, 760, "rise"), (24, CARD_Y - 12, "soft"), (34, CARD_Y + 4, "soft"), (42, CARD_Y)])
    sc.key(mount, "rotation", [(0, 0.25, "out"), (30, -0.03, "soft"), (42, 0)])
    sc.key(rt, "time", [(20, 0, "linear"), (92, 1)])
    sc.key(rw, "time", [(20, 0, "linear"), (92, 1)])
    for variant, spots, conv in (("tall", ((40, 176), (352, 212), (34, 560), (356, 584)), "b2zero"),
                                 ("wide", ((-98, 246), (488, 272), (-92, 520), (486, 508)), "b2one")):
        stars = []
        for i, (x, y) in enumerate(spots):
            st = nid()
            stars.append(sparkle(f"Summary star {variant} {i}", x, y, 20 + i * 3, PEACH if i % 2 else MINT, sid=st))
            sc.pop(st, 60 + i * 6, 0, 1.3, 16)
            sc.loop(st, "rotation", [(0, 0), (IDLE_LEN, 1.5708 * (1 if i % 2 else -1))])
        sc.items.append(el("Node", {"name": f"Summary stars ({variant})", "id": nid()},
                           [bind(P("_wideCard"), 18, C[conv])] + stars))
    sc.items += deco_bg(sc, 100, MINT, 5)
    return sc


# =====================================================================
# Share card component (also rendered on its own by the host for capture)
# =====================================================================
def tile(name, x, y, w, h, color, src, label_path, money=False, vsize=30, lsize=14.5):
    tid = nid()
    conv = C["fmtMoney"] if money else C["fmtCount"]
    vh = round(vsize * 1.08)
    return tid, el("Node", {"name": name, "x": x, "y": y, "id": tid}, [
        text(f"{name} value", -w / 2 + 14, -h / 2 + 9, [run(src, "0", conv=conv, font="rubik", size=vsize, color=INK,
                                                            weight=900, lh=vh, ls=-0.5)],
             width=w - 28, sizing="fixed", height=vh + 2, overflow="fitFontSize", wrap="noWrap"),
        text(f"{name} label", -w / 2 + 14, -h / 2 + 13 + vh, [run(label_path, "", font="nunito", size=lsize, color=INK,
                                                                   weight=800, lh=round(lsize * 1.12, 1))],
             width=w - 28, sizing="fixed", height=h - vh - 15, overflow="ellipsis"),
        shape(f"{name} bg", [rect(w, h, 16)], [fill(color), stroke(INK, 3.5)]),
    ])


def card_parts(a, spec):
    """the parts both card arrangements share, placed by `spec`; keys the
    assembly into the Anim `a`. Returns the art list (front to back)."""
    priv, sens = [], []
    for order, (nm, x, y, w, h, c, src, lab) in enumerate(spec["private"]):
        tid, t = tile(f"Private {nm}", x, y, w, h, c, src, lab)
        priv.append(t)
        a.key(tid, "scaleX", [(10 + order * 6, 0.3, "out"), (22 + order * 6, 1.08, "soft"), (30 + order * 6, 1)])
        a.key(tid, "scaleY", [(10 + order * 6, 0.3, "out"), (22 + order * 6, 1.08, "soft"), (30 + order * 6, 1)])
        a.key(tid, "opacity", [(10 + order * 6, 0, "linear"), (16 + order * 6, 1)])
    for order, (nm, x, y, w, h, c, src, lab, money) in enumerate(spec["sensitive"]):
        tid, t = tile(f"Full {nm}", x, y, w, h, c, src, lab, money, vsize=28 if nm == "Saved" else 26,
                      lsize=14.5)
        sens.append(t)
        a.key(tid, "scaleX", [(10 + order * 5, 0.3, "out"), (22 + order * 5, 1.08, "soft"), (30 + order * 5, 1)])
        a.key(tid, "scaleY", [(10 + order * 5, 0.3, "out"), (22 + order * 5, 1.08, "soft"), (30 + order * 5, 1)])
        a.key(tid, "opacity", [(10 + order * 5, 0, "linear"), (16 + order * 5, 1)])
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
    ex, ey, ew = spec["empty"]
    empty = el("Node", {"name": "Empty state", "x": ex, "y": ey, "id": nid()}, [
        bind(P("_emptyState"), 18, C["b2one"]),
        text("Empty headline", 0, 0, [run("emptyHeadline", "", font="rubik", size=26, color=INK, weight=800, lh=29)],
             width=ew, align="center", ox=0.5),
        text("Empty support", 0, 72, [run("emptySupport", "", font="nunito", size=16, color=INK, weight=600, lh=21)],
             width=ew - 10, align="center", ox=0.5),
        coin("Empty coin", 0, 146, 0.9),
        shape("Empty slot", [rect(70, 12, 6, y=182)], [fill(INK)]),
    ])
    cx, cy, cw = spec["chip"]
    chip_n = el("Node", {"name": "Persona chip", "id": chip}, [
        el("Node", {"name": "Persona chip shown", "id": nid()}, [bind(P("_personaKnown"), 18, C["b2one"]),
            text("Chip name", cx - cw / 2 + 31, cy, [run("personaName", "", font="nunito", size=15, color=INK, weight=800, lh=18)],
                 width=cw - 44, sizing="fixed", height=20, overflow="ellipsis", wrap="noWrap", oy=0.5, valign="middle"),
            shape("Chip dot", [ellipse(18, 18, x=cx - cw / 2 + 17, y=cy)], [fill(MINT, bind=bind(P("personaColor"), 37)), stroke(INK, 3)]),
            shape("Chip", [rect(cw, 34, 17, x=cx, y=cy)], [fill("FFFFE9C2"), stroke(INK, 3)]),
        ])])
    nx, ny, nw = spec["name"]
    wx, wy = spec["wordmark"]
    yx, yy = spec["year"]
    kx, ky = spec["coin"]
    header = [
        el("Node", {"name": "Name (opt-in)", "id": nid()}, [bind(P("shareIncludeName"), 18, C["b2one"]),
            text("Card name", nx, ny, [run("userName", "", font="nunito", size=16, color=MINT, weight=800, lh=20)],
                 width=nw, sizing="fixed", height=22, overflow="ellipsis", wrap="noWrap")]),
        el("Node", {"name": "Card year", "x": yx, "y": yy, "id": yr}, [
            text("Year", 0, 0, [run("year", "2026", conv=C["toStr0"], font="rubik", size=50, color=MINT, weight=900, lh=52,
                                    outline=(INK, 7))], ox=spec.get("year_ox", 1), oy=0.5)]),
        text("Card wordmark", wx, wy, [run(None, "Stash", font="rubik", size=28, color=CREAM, weight=900, lh=30)]),
        coin("Card coin", kx, ky, 0.5),
        spec["band"],
    ]
    return [stats, empty, chip_n] + header


def card_artboard(name, abid, aid, w, h, spec, x):
    a = Anim("Assemble", 72, aid=aid)
    art = card_parts(a, spec) + spec["deco"] + [
        shape("Card", [rect(w, h, 30)], [fill(CREAM), stroke(INK, 5)]),
        shape("Card shadow", [rect(w, h, 30, y=12)], [fill(alpha(INK, 0.35))]),
    ]
    sm, lay, st, style = nid(), nid(), nid(), nid()
    settled = Anim("Settled", 1)
    machine_xml = el("StateMachine", {"name": "Card", "id": sm}, [
        el("StateMachineLayer", {"name": "Card", "id": lay}, [
            el("AnyState", {"x": 300, "y": -100}), el("ExitState", {"x": 500, "y": -100}),
            el("EntryState", {"x": 0, "y": 0}, [el("StateTransition", {"stateToId": st})]),
            el("AnimationState", {"x": 160, "y": 0, "animationId": settled.id, "id": st}),
        ])])
    return el("Artboard", {"isComponent": True, "defaultStateMachineId": sm, "styleId": style, "clip": False,
                           "viewModelId": VM, "viewModelInstanceId": VMI,
                           "originX": 0.5, "originY": 0.5, "width": w + 10, "height": h + 20, "x": x, "y": 0,
                           "name": name, "id": abid},
              [el("LayoutComponentStyle", {"name": f"{name} style", "id": style})] + art +
              [machine_xml, settled.xml(), a.xml()])


def share_card():
    """the tall collectible card (330 x 420): header band, persona chip, 2x2 tiles.
    Tile labels are 14.5 pt so they stay >= 11 px wherever the layout shows it."""
    W2, H2 = 330, 420
    top = -H2 / 2
    spec = {
        "private": [("Deposits", -73, 6, 140, 108, MINT, "deposits", "screen3Unit"),
                    ("Goals", 73, 6, 140, 108, PEACH, "goalsCompleted", "screen4Unit"),
                    ("Months", -73, 126, 140, 108, GRAPE_L, "activeMonths", "screen6Unit"),
                    ("Jars", 73, 126, 140, 108, "FFFFE9C2", "goalJars", "screen8Unit")],
        "sensitive": [("Saved", 0, -15, 286, 66, PEACH, "totalSaved", "screen2Unit", True),
                      ("Roundups", -73, 62, 140, 80, MINT, "roundupsSaved", "screen5Unit", True),
                      ("Deposits", 73, 62, 140, 80, "FFFFE9C2", "deposits", "screen3Unit", False),
                      ("Goals", -73, 148, 140, 80, GRAPE_L, "goalsCompleted", "screen4Unit", False),
                      ("Months", 73, 148, 140, 80, MINT_D, "activeMonths", "screen6Unit", False)],
        "empty": (0, -36, 270),
        "chip": (0, -72, 286),
        "name": (-139, top + 70, 150),
        "wordmark": (-139, top + 18),
        "year": (140, top + 70),
        "coin": (112, top + 22),
        "band": shape("Header band", [rect(W2, 112, 0, y=top + 56, radii=(30, 30, 0, 0))], [fill(GRAPE), stroke(INK, 5)]),
        "deco": [sparkle("Card star a", -146, 198, 12, PEACH), sparkle("Card star b", 146, 198, 12, GRAPE_L)],
    }
    return card_artboard("ShareCard", SHARE_AB, SHARE_ASSEMBLE, W2, H2, spec, 900)


def share_card_wide():
    """the wide arrangement (560 x 300) of the same card, for canvases too short
    for the tall one: the header becomes a band down the left, the tiles a 2x2
    grid on the right. Same bindings, same privacy rules."""
    W2, H2 = 560, 300
    L = -W2 / 2
    bw = 196                       # band width
    gx0 = L + bw + 16              # tile grid left edge
    gw = W2 / 2 - 16 - gx0         # grid width
    tw = (gw - 12) / 2
    c1, c2 = gx0 + tw / 2, gx0 + tw + 12 + tw / 2
    spec = {
        "private": [("Deposits", c1, -62, tw, 116, MINT, "deposits", "screen3Unit"),
                    ("Goals", c2, -62, tw, 116, PEACH, "goalsCompleted", "screen4Unit"),
                    ("Months", c1, 62, tw, 116, GRAPE_L, "activeMonths", "screen6Unit"),
                    ("Jars", c2, 62, tw, 116, "FFFFE9C2", "goalJars", "screen8Unit")],
        "sensitive": [("Saved", gx0 + gw / 2, -90, gw, 64, PEACH, "totalSaved", "screen2Unit", True),
                      ("Roundups", c1, -6, tw, 82, MINT, "roundupsSaved", "screen5Unit", True),
                      ("Deposits", c2, -6, tw, 82, "FFFFE9C2", "deposits", "screen3Unit", False),
                      ("Goals", c1, 84, tw, 82, GRAPE_L, "goalsCompleted", "screen4Unit", False),
                      ("Months", c2, 84, tw, 82, MINT_D, "activeMonths", "screen6Unit", False)],
        "empty": (gx0 + gw / 2, -108, gw - 20),
        "chip": (L + bw / 2, 112, bw - 24),
        "name": (L + 22, -84, bw - 40),
        "wordmark": (L + 22, -128),
        "year": (L + 22, 10),
        "year_ox": 0,
        "coin": (L + bw - 34, -112),
        "band": shape("Side band", [rect(bw, H2, 0, x=L + bw / 2, radii=(30, 0, 0, 30))], [fill(GRAPE), stroke(INK, 5)]),
        "deco": [sparkle("Card star a", L + bw - 30, 52, 14, PEACH), sparkle("Card star b", L + 30, 62, 12, MINT)],
    }
    return card_artboard("ShareCardWide", SHARE_WIDE_AB, SHARE_WIDE_ASSEMBLE, W2, H2, spec, 1300)


def event_probe():
    """EventProbe: a verification harness, not part of the experience. It nests the
    Recap artboard (same UserRecap instance) and listens to the three events the
    nested state machine *reports*, pulsing the _heard* probes, so a headless run
    observes the real Rive events rather than the mirror triggers."""
    sm, lay, st, nest, style = nid(), nid(), nid(), nid(), nid()
    idle = Anim("Probe idle", 1)
    lis = [el("StateMachineListenerSingle", {"targetId": nest, "listenerTypeValue": "event", "eventId": i,
                                             "name": f"Hear {n}"}, [a_trig("_heard" + n[0].upper() + n[1:])])
           for n, i in EV.items()]
    return el("Artboard", {"defaultStateMachineId": sm, "styleId": style, "clip": True,
                           "viewModelId": VM, "viewModelInstanceId": VMI,
                           "width": W, "height": H, "x": 2000, "y": 0, "name": "EventProbe", "id": nid()},
              [el("LayoutComponentStyle", {"name": "Probe style", "id": style}),
               el("NestedArtboard", {"artboardId": MAIN, "x": 0, "y": 0, "name": "Recap under test", "id": nest},
                  [el("NestedStateMachine", {"animationId": "0:3", "name": "Recap"})]),
               el("StateMachine", {"name": "Probe", "id": sm}, lis + [
                   el("StateMachineLayer", {"name": "Probe", "id": lay}, [
                       el("AnyState", {"x": 300, "y": -100}), el("ExitState", {"x": 500, "y": -100}),
                       el("EntryState", {"x": 0, "y": 0}, [el("StateTransition", {"stateToId": st})]),
                       el("AnimationState", {"x": 160, "y": 0, "animationId": idle.id, "id": st})])]),
               idle.xml()])


RESIZE_W = 1100


def resize_probe():
    """ResizeProbe: a verification harness, not part of the experience. It nests
    the Recap artboard as a layout child and keys the instance's width, so a
    headless run resizes the live recap across the layout breakpoint mid-scene
    (390 -> 1100 at 2.5 s, -> 560 at 5 s, -> 900 at 7 s)."""
    sm, lay, st, nest, style = nid(), nid(), nid(), nid(), nid()
    a = Anim("Resize", 600)
    a.key(nest, "instanceWidth", [(0, 390, "hold"), (150, RESIZE_W, "hold"), (300, 560, "hold"), (420, 900, "hold"),
                                  (600, 900)])
    return el("Artboard", {"defaultStateMachineId": sm, "styleId": style, "clip": True,
                           "viewModelId": VM, "viewModelInstanceId": VMI,
                           "width": RESIZE_W, "height": H, "x": 2500, "y": 0, "name": "ResizeProbe", "id": nid()},
              [el("LayoutComponentStyle", {"flexDirectionValue": "row", "layoutAlignmentType": "topLeft",
                                           "name": "Probe style", "id": style}),
               fill("FF000000", name="Probe backdrop"),
               el("NestedArtboardLayout", {"artboardId": MAIN, "instanceWidth": 390, "instanceHeight": H,
                                           "name": "Recap under test", "id": nest},
                  [el("NestedStateMachine", {"animationId": "0:3", "name": "Recap"})]),
               el("StateMachine", {"name": "Probe", "id": sm}, [
                   el("StateMachineLayer", {"name": "Probe", "id": lay}, [
                       el("AnyState", {"x": 300, "y": -100}), el("ExitState", {"x": 500, "y": -100}),
                       el("EntryState", {"x": 0, "y": 0}, [el("StateTransition", {"stateToId": st})]),
                       el("AnimationState", {"x": 160, "y": 0, "animationId": a.id, "id": st})])]),
               a.xml()])


def coin_artboard():
    sm, lay, st = nid(), nid(), nid()
    idle = Anim("Rest", 1)
    style = nid()
    # bound to UserRecap only so the 3D coin's canvas resolution follows _gpuRes
    return el("Artboard", {"isComponent": True, "defaultStateMachineId": sm, "styleId": style, "clip": False,
                           "viewModelId": VM, "viewModelInstanceId": VMI,
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
SPRING_BASE = 862      # stage y of the spring's base when it is up (just below the screen)
SPRING_REST = 160      # coil height at rest
PLATE_H = 8            # half thickness of the bar the coils carry
SPRING_X = (42, 348)   # the two springs sit at the screen edges


def handoff():
    """signature transition: a coin rolls off a rail, lands on a 3D chrome spring,
    compresses it, and the spring fires the next scene's panel into view"""
    for k in ("root", "rail", "coin", "plate", "spring", "coil"):
        HO[k] = nid()
    HO["coin_ids"] = {}
    HO["coil_ids"] = {"height": [], "twist": []}

    def coil(name, x, flip):
        h, t = nid(), nid()
        HO["coil_ids"]["height"].append(h)
        HO["coil_ids"]["twist"].append(t)
        return el("ScriptedDrawable", {"scriptAssetId": SCRIPTS["spring3d"][0], "x": x, "name": name, "id": nid(),
                                       "scaleX": -1 if flip else 1}, [
            el("ScriptInputNumber", {"propertyValue": SPRING_REST, "name": "height", "id": h}),
            el("ScriptInputNumber", {"propertyValue": 30, "name": "radius"}),
            el("ScriptInputNumber", {"propertyValue": 6, "name": "wire"}),
            el("ScriptInputNumber", {"propertyValue": 7, "name": "turns"}),
            el("ScriptInputNumber", {"propertyValue": 0, "name": "twist", "id": t}),
            el("ScriptInputNumber", {"propertyValue": 0.34, "name": "tilt"}),
            el("ScriptInputNumber", {"propertyValue": 2.4, "name": "outline"}),
            el("ScriptInputNumber", {"propertyValue": 0.88, "name": "mirror"}),
            el("ScriptInputNumber", {"propertyValue": 420, "name": "maxH"}),
            res_input("_gpuResStage"),
            el("ScriptInputColor", {"propertyValue": "FFDCE6F2", "name": "steel"}),
            el("ScriptInputColor", {"propertyValue": INK, "name": "ink"}),
        ])
    # the next scene rides a launch bar carried by two chrome springs at the screen
    # edges (clear of every motif pose); the coin lands on the right-hand one
    HO["root2"] = nid()
    right = lambda name, ch: el("Node", {"name": name, "id": nid()}, [bind(P("_rightOff"), 13)] + ch)
    HO["coin_layer"] = el("Node", {"name": "Handoff: coin", "id": HO["root2"], "opacity": 0}, [
        right("Right edge (coin)", [
            el("Node", {"name": "Handoff coin", "id": HO["coin"], "x": 432, "y": 572},
               [coin3d("Handoff coin 3D", 56, 0, 0.0, 0.25, ids=HO["coin_ids"], outline=3.5, shine=0.7,
                       res="_gpuResStage")])])])
    return el("Node", {"name": "Handoff: springs", "id": HO["root"], "opacity": 0}, [
        right("Right edge (rail)", [el("Node", {"name": "Exit rail", "id": HO["rail"]}, [
            shape("Rail shine", [poly([(470, 584), (380, 600)], closed=False)], [stroke(alpha(CREAM, 0.8), 3)], y=-4),
            shape("Rail", [poly([(470, 588), (380, 604)], closed=False)], [stroke(INK, 16), stroke(PEACH, 9, name="Rail top")]),
            shape("Rail stop", [ellipse(18, 18, x=380, y=604)], [fill(PEACH), stroke(INK, 3.5)]),
        ])]),
        el("Node", {"name": "Springs", "id": HO["spring"], "x": 0, "y": 1000}, [
            el("Node", {"name": "Launch bar", "id": HO["plate"], "y": -SPRING_REST - PLATE_H}, [
                el("Node", {"name": "Bar span", "id": nid()}, [bind(P("_vcx"), 13), bind(P("_barSX"), 16), 
                    shape("Bar shine", [rect(380, 3, 1.5, y=-4)], [fill("77FFFFFF")]),
                    shape("Bar", [rect(398, 16, 8)], [fill(grad=lin([(0, GRAPE_L), (1, GRAPE)], 0, -8, 0, 8)), stroke(INK, 4)]),
                ]),
                shape("Cap L", [rect(76, 22, 9, x=SPRING_X[0], y=2)], [fill(GRAPE_D), stroke(INK, 3.5)]),
                right("Right edge (cap)", [shape("Cap R", [rect(76, 22, 9, x=SPRING_X[1], y=2)], [fill(GRAPE_D), stroke(INK, 3.5)])]),
            ]),
            coil("Spring L 3D", SPRING_X[0], True),
            right("Right edge (spring)", [coil("Spring R 3D", SPRING_X[1], False)]),
        ]),
    ])


def spring_keys(an, pts):
    """pts: (frame, coil height, ease) -> keys the coil and the plate that rides on it"""
    pts = [p if len(p) == 3 else (p[0], p[1], "linear") for p in pts]
    for hid in HO["coil_ids"]["height"]:
        an.key(hid, 243, [(f, h, e) for f, h, e in pts])
    an.key(HO["plate"], "y", [(f, -h - PLATE_H, e) for f, h, e in pts])


# forward handoff timing (frames @60): coin lands at IMPACT, the spring is fully
# compressed at FIRE and the next panel has landed at FWD_LAND
IMPACT, FIRE, FWD_LAND = 24, 29, 48


def handoff_anims():
    fwd = Anim("Handoff forward", 60)
    for r in (HO["root"], HO["root2"]):
        fwd.key(r, "opacity", [(0, 1, "hold"), (52, 1, "linear"), (58, 0)])
    fwd.key(HO["rail"], "x", [(0, 120, "out"), (8, 0, "linear"), (36, 0, "in"), (46, 160)])
    # after firing, the springs recoil and drop away fast so the new scene is clear
    fwd.key(HO["spring"], "y", [(0, 1000, "out"), (8, SPRING_BASE, "linear"), (FIRE + 4, SPRING_BASE, "in"), (FIRE + 15, 1240)])
    spring_keys(fwd, [(0, SPRING_REST, "linear"), (IMPACT, SPRING_REST, "out"), (FIRE, 104, "snap"), (FIRE + 5, 290, "soft"),
                      (FIRE + 12, 150, "soft"), (FIRE + 18, SPRING_REST + 10, "soft"), (FIRE + 24, SPRING_REST)])
    for tid in HO["coil_ids"]["twist"]:
        fwd.key(tid, 243, [(0, 0, "linear"), (IMPACT, 0, "out"), (FIRE, 0.5, "snap"), (FIRE + 8, -0.4, "soft"), (FIRE + 20, 0)])
    plate_top = SPRING_BASE - SPRING_REST - 2 * PLATE_H
    land_y = plate_top - 26
    cid = HO["coin_ids"]
    fwd.key(HO["coin"], "x", [(0, 432, "linear"), (8, 432, "linear"), (16, 382, "linear"), (IMPACT, SPRING_X[1] - 6, "linear"),
                              (FIRE, SPRING_X[1] - 6, "out"), (FIRE + 16, 250)])
    fwd.key(HO["coin"], "y", [(0, 574, "linear"), (8, 574, "linear"), (16, 584, "drop"), (IMPACT, land_y, "linear"),
                              (FIRE, land_y + 56, "out"), (FIRE + 16, -90)])
    fwd.key(HO["coin"], "scaleY", [(0, 1, "linear"), (IMPACT, 1, "out"), (IMPACT + 2, 0.78, "soft"), (FIRE, 0.84, "out"),
                                   (FIRE + 4, 1.1, "soft"), (FIRE + 10, 1)])
    fwd.key(HO["coin"], "scaleX", [(0, 1, "linear"), (IMPACT, 1, "out"), (IMPACT + 2, 1.16, "soft"), (FIRE, 1.1, "out"),
                                   (FIRE + 4, 0.92, "soft"), (FIRE + 10, 1)])
    fwd.key(cid["roll"], 243, [(0, 0, "linear"), (8, 0, "linear"), (16, 2.0, "linear"), (IMPACT, 2.6)])
    fwd.key(cid["yaw"], 243, [(0, 0, "linear"), (16, 0, "in"), (IMPACT, TAU, "linear"), (FIRE, TAU, "out"), (FIRE + 16, 4 * TAU)])
    fwd.key(cid["pitch"], 243, [(0, 0.25, "linear"), (16, 0.25, "out"), (IMPACT, 0.9, "linear"), (FIRE, 0.9, "out"), (FIRE + 16, 0.2)])
    back = Anim("Handoff back", 60)
    for r in (HO["root"], HO["root2"]):
        back.key(r, "opacity", [(0, 1, "hold"), (52, 1, "linear"), (58, 0)])
    back.key(HO["rail"], "x", [(0, 160, "hold"), (18, 160, "out"), (28, 0, "linear"), (44, 0, "in"), (56, 160)])
    back.key(HO["spring"], "y", [(0, 1000, "out"), (8, SPRING_BASE, "linear"), (40, SPRING_BASE, "in"), (52, 1240)])
    # the dropping panel lands on the plate, compresses the coil, and the coin is
    # thrown back up the rail it came from
    spring_keys(back, [(0, SPRING_REST, "linear"), (24, SPRING_REST, "out"), (30, 104, "soft"), (38, 210, "soft"),
                       (44, 140, "soft"), (50, SPRING_REST)])
    for tid in HO["coil_ids"]["twist"]:
        back.key(tid, 243, [(0, 0, "linear"), (24, 0, "out"), (30, 0.5, "soft"), (40, -0.3, "soft"), (50, 0)])
    back.key(HO["coin"], "x", [(0, SPRING_X[1] - 6, "linear"), (30, SPRING_X[1] - 6, "out"), (40, 372, "linear"), (46, 400, "linear"), (54, 470)])
    back.key(HO["coin"], "y", [(0, 900, "hold"), (29, 900, "hold"), (30, land_y + 56, "out"), (40, 520, "drop"), (46, 596, "linear"), (54, 584)])
    back.key(cid["yaw"], 243, [(0, 0, "linear"), (30, 0, "out"), (40, 3 * TAU)])
    back.key(cid["roll"], 243, [(0, 0, "linear"), (40, 0, "linear"), (54, -5.0)])
    back.key(cid["pitch"], 243, [(0, 0.25, "hold"), (60, 0.25)])
    back.key(HO["coin"], "scaleX", [(0, 1, "hold"), (60, 1)])
    back.key(HO["coin"], "scaleY", [(0, 1, "hold"), (60, 1)])
    rest = Anim("Handoff rest", 1)
    rest.hold(HO["root"], "opacity", 0)
    rest.hold(HO["root2"], "opacity", 0)
    return rest, fwd, back


def toy_anims():
    """the motif's tap toy: a coin waiting at the mouth of the coin path"""
    tids = TOY["ids"]
    idle = Anim("Toy idle", 240, loop="loop")
    idle.key(tids["yaw"], 243, [(0, 0, "inout"), (36, 0.55, "inout"), (72, -0.35, "inout"), (100, 0, "hold"), (240, 0)])
    idle.key(TOY["hint"], "opacity", [(0, 0, "soft"), (20, 0.85, "soft"), (64, 0, "hold"), (240, 0)])
    idle.key(TOY["hint"], "scaleX", [(0, 0.8, "out"), (64, 1.6, "hold"), (240, 1.6)])
    idle.key(TOY["hint"], "scaleY", [(0, 0.8, "out"), (64, 1.6, "hold"), (240, 1.6)])
    rest_vals = (("x", 0), ("y", 0), ("scaleX", 1), ("scaleY", 1), ("opacity", 1))
    for k, v in rest_vals:
        idle.hold(TOY["coin"], k, v)
    still = Anim("Toy still", 1)
    for k, v in rest_vals:
        still.hold(TOY["coin"], k, v)
    still.hold(tids["yaw"], 243, 0)
    still.hold(TOY["hint"], "opacity", 0)
    nudge = Anim("Toy nudge", 80)
    ox, oy = TOY_AT
    path = [(112, -60), (124, -170), (112, -290), (66, -352), (26, -330)]
    frames = [6, 16, 28, 38, 46]
    nudge.key(TOY["coin"], "x", [(0, 0, "hold"), (4, 0, "linear")] +
              [(f, x - ox, "inout" if i < 4 else "in") for i, (f, (x, y)) in enumerate(zip(frames, path))] +
              [(52, path[-1][0] - ox, "hold"), (53, 0)])
    nudge.key(TOY["coin"], "y", [(0, 0, "out"), (4, 6, "snap")] +
              [(f, y - oy, "inout" if i < 4 else "in") for i, (f, (x, y)) in enumerate(zip(frames, path))] +
              [(52, path[-1][1] - oy, "hold"), (53, 0)])
    nudge.key(TOY["coin"], "scaleY", [(0, 1, "out"), (4, 0.74, "snap"), (10, 1.1, "soft"), (16, 1, "linear"), (44, 1, "in"),
                                      (50, 0, "hold"), (62, 0, "out"), (70, 1.15, "soft"), (78, 1)])
    nudge.key(TOY["coin"], "scaleX", [(0, 1, "out"), (4, 1.2, "snap"), (10, 0.92, "soft"), (16, 1, "linear"), (44, 1, "in"),
                                      (50, 0, "hold"), (62, 0, "out"), (70, 1.15, "soft"), (78, 1)])
    nudge.key(tids["yaw"], 243, [(0, 0, "linear"), (6, 0, "in"), (46, 4 * TAU, "hold"), (62, 0)])
    nudge.hold(TOY["coin"], "opacity", 1)
    nudge.hold(TOY["hint"], "opacity", 0)
    calm = Anim("Toy nudge reduced", 48)
    calm.key(TOY["coin"], "opacity", [(0, 1, "linear"), (8, 0, "hold"), (30, 0, "linear"), (40, 1)])
    calm.hold(TOY["hint"], "opacity", 0)
    return idle, still, nudge, calm


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


def footer_binds():
    # the footer's horizontal extent (director): full width in a portrait stack,
    # capped and centred on wide portrait canvases, the copy column in landscape
    return [bind(P("_ftrL"), 516), bind(P("_ftrR"), 517)]


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
    # 54 pt tall, 48 pt on short canvases (never under the 44 pt minimum)
    b, _ = box(name, bid, kw, [bind(P("_btnH"), 8)] + ch, w=w or 0, h=54, extra_attrs=attrs)
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
                    [bind(P("_hdrH"), 8), wordmark, prog_box, year, pause], h=64)

    chev_l = icon("Chevron left", [poly([(6, -8), (-2, 0), (6, 8)], closed=False)])
    chev_r = icon("Chevron right", [poly([(-3, -7), (4, 0), (-3, 7)], closed=False)], "_chromeOnColor", 3)
    prev = button("Previous button", CH["prev"], 2, None, "previousLabel", w=54, children=[chev_l])
    prev = prev.replace(f'id="{CH["prev"]}">', f'id="{CH["prev"]}">\n' + bind(P("_canGoBack"), 18, C["b2dim"]), 1)
    nxt = button("Continue button", CH["next"], 3, "continueLabel", "continueLabel", primary=True, children=[
        chrome_text("Continue label", "continueLabel", "Continue", 17, 800, onc=True, participant="fill"), chev_r])
    # a clockwise arc, open at the top; the arrowhead sits on the arc's end and
    # points along its tangent (built from geometry, not placed by eye)
    r, a0, a1 = 7.0, math.radians(-62), math.radians(232)
    arc = [(round(r * math.cos(a0 + (a1 - a0) * i / 24), 3), round(r * math.sin(a0 + (a1 - a0) * i / 24), 3)) for i in range(25)]
    ex, ey = arc[-1]
    dx, dy = -math.sin(a1), math.cos(a1)          # d(angle) > 0 is clockwise on screen (y down)
    px, py = -dy, dx
    tip = (ex + dx * 2.2, ey + dy * 2.2)
    head = [(round(tip[0] - dx * 4.6 + px * 3.8, 3), round(tip[1] - dy * 4.6 + py * 3.8, 3)), (round(tip[0], 3), round(tip[1], 3)),
            (round(tip[0] - dx * 4.6 - px * 3.8, 3), round(tip[1] - dy * 4.6 - py * 3.8, 3))]
    replay_icon = icon("Replay glyph", [poly(arc, closed=False, name="Arc"), poly(head, closed=False, name="Arrowhead")], th=2.6)
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
    nav, CH["nav_style"] = box("Footer: story", CH["nav"], dict(fkw), [bind(P("_ftrH"), 8), prev, nxt], h=104,
                               style_binds=footer_binds())
    fkw2 = dict(fkw, positionBottom=-400)
    sm_, CH["sum_style"] = box("Footer: summary", CH["sum"], fkw2, [bind(P("_ftrH"), 8), replay, share], h=104,
                               extra_attrs={"opacity": 0}, style_binds=footer_binds())
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
        # the panel rides the spring: its lip sits on the plate, dips under the
        # coin's impact, then the spring fires it up into view
        lip = lambda base, h: base - h - 2 * PLATE_H + 140
        ef.key(root, "y", [(0, lip(1000, SPRING_REST), "out"), (8, lip(SPRING_BASE, SPRING_REST), "linear"),
                           (IMPACT, lip(SPRING_BASE, SPRING_REST), "out"), (FIRE, lip(SPRING_BASE, 104), (0.3, 0.55, 0.2, 1.0)),
                           (FWD_LAND - 2, -16, "soft"), (FWD_LAND + 3, 6, "soft"), (FWD_LAND + 8, 0)])
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
    xf = Anim(f"S{k} exit forward", 58)
    # the outgoing scene feels the coin land (a small sympathetic dip), then
    # recedes while the fired panel covers it
    xf.key(content, "scaleX", [(0, 1, "linear"), (FIRE, 1, "in"), (FWD_LAND, 0.93)])
    xf.key(content, "scaleY", [(0, 1, "linear"), (FIRE, 1, "in"), (FWD_LAND, 0.93)])
    xf.key(content, "y", [(0, 422, "linear"), (IMPACT, 422, "out"), (IMPACT + 3, 431, "soft"), (FIRE, 426, "in"), (FWD_LAND, 440)])
    xf.key(content, "opacity", [(0, 1, "linear"), (FIRE, 1, "linear"), (FWD_LAND, 0.55)])
    xf.key(root, "opacity", [(0, 1, "hold"), (57, 0)])
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
    # paused, held, sharing -- or reduced motion: idle loops rest in their still pose
    froz = [tr(ids["FZ"], [c_bool("_frozen", True)], 200), tr(ids["FZ"], [rm_on], 0)]
    y0 = (k - 1) * 0
    states = [
        astate(h.id, ids["H"], 0, y0, enters),
        astate(ef.id, ids["EF"], 220, -160, announce + exits + settle, reset=True),
        astate(eb.id, ids["EB"], 220, 0, announce + exits + settle, reset=True),
        astate(er.id, ids["ER"], 220, 160, announce + exits + settle, reset=True),
        astate(idle.id, ids["SH"], 460, 0, exits + froz),
        astate(fz.id, ids["FZ"], 460, 160, exits + [tr(ids["SH"], [c_bool("_frozen", False), rm_off], 200)]),
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
    idle, still, nudge, calm = toy_anims()
    ANIMS.extend([idle, still, nudge, calm])
    a, b, c, d = nid(), nid(), nid(), nid()
    rm_on, fz_on = c_bool("reducedMotion", True), c_bool("_frozen", True)
    calm_ok = [c_bool("reducedMotion", False), c_bool("_frozen", False)]
    return layer("Coin toy", a, [
        astate(idle.id, a, 0, 0, [tr(c, [c_trig("_coinNudge")]), tr(b, [rm_on], 200), tr(b, [fz_on], 200)]),
        astate(still.id, b, 0, 160, [tr(d, [c_trig("_coinNudge")]), tr(a, calm_ok, 200)]),
        astate(nudge.id, c, 240, 0, [tr(a, [], 120, exit_pct=100)], reset=True),
        astate(calm.id, d, 240, 160, [tr(b, [], 0, exit_pct=100)], reset=True),
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
    def zone(name, k, z, items):
        # one responsive zone: its transform is the director's per-scene fit
        pre = {"note": "n10", "ticket": "t7"}.get(z, f"{z[0]}{k}")
        if z in ("note", "ticket") and not items:
            return None
        return el("Node", {"name": name, "id": nid()},
                  [bind(P(f"_{pre}x"), 13), bind(P(f"_{pre}y"), 14), bind(P(f"_{pre}s"), 16), bind(P(f"_{pre}s"), 17)]
                  + items)
    for k in range(10, 0, -1):
        sc = SCENES[k]
        zs = sc.zones
        parts = [zone(f"S{k} copy zone", k, "copy", zs["copy"]), zone(f"S{k} note zone", k, "note", zs["note"]),
                 zone(f"S{k} ticket zone", k, "ticket", zs["ticket"]),
                 zone(f"S{k} art zone", k, "art", zs["art"]),
                 el("Node", {"name": f"S{k} backdrop", "id": nid()}, zs["back"])]
        # design space: x 195 is the viewport's centre, y is the 844-unit stage
        inner = el("Node", {"name": f"S{k} art", "x": -195, "y": -422, "id": nid()}, [p_ for p_ in parts if p_])
        content = el("Node", {"name": f"S{k} content", "x": 195, "y": 422, "id": sc.content}, [bind(P("_vcx"), 13), inner])
        scenes_xml.append(el("Node", {"name": f"Scene {k}", "id": sc.root, "opacity": 0}, [content] + bg_panel(sc)))
    ho = handoff()
    # the motif machine stands in the current scene's art zone: its frame is that
    # zone's transform in stage space, blended by the director on scene changes
    motif_frame = el("Node", {"name": "Motif frame", "id": nid()},
                     [bind(P("_mfx"), 13), bind(P("_mfy"), 14), bind(P("_mfs"), 16), bind(P("_mfs"), 17), mach])
    stage = el("Node", {"name": "Stage (844 units tall, director-scaled)", "id": nid()}, [
        bind(P("_stageScale"), 16), bind(P("_stageScale"), 17),
        HO["coin_layer"], motif_frame, ho] + scenes_xml)
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
    ]
    listeners += button_listener("Pause", CH["pause"], [a_trig("togglePause")], 1)
    listeners += button_listener("Previous", CH["prev"], [a_trig("navPrev")], 2)
    listeners += button_listener("Continue", CH["next"], [a_trig("navNext")], 3)
    listeners += button_listener("Replay", CH["replay"], [a_trig("replay")], 4)
    listeners += button_listener("Share", CH["share"], [el("ListenerFireEvent", {"eventId": EV["shareTapped"]}),
                                                        a_trig("_evtShareTapped")], 5)
    sm_id = "0:3"
    sm = el("StateMachine", {"name": "Recap", "id": sm_id}, listeners + layers)
    # screenChanged carries the canonical scene id as a payload (custom property
    # bound to currentScreen); hosts may also read currentScreen
    events = [el("Event", {"name": n, "id": i},
                 [el("CustomPropertyNumber", {"propertyValue": 1, "name": "index", "id": nid()},
                     [bind(P("currentScreen"), 243)])] if n == "screenChanged" else None)
              for n, i in EV.items()]

    style = "0:4"
    # a component so the EventProbe harness can nest it; still the file's main artboard
    art = el("Artboard", {"isComponent": True, "defaultStateMachineId": sm_id, "viewModelId": VM, "viewModelInstanceId": VMI,
                          "styleId": style, "clip": True, "width": W, "height": H, "x": 0, "y": 0,
                          "name": "Recap", "id": MAIN},
             [el("LayoutComponentStyle", {"name": "Recap style", "id": style}),
              el("FocusData", {"name": "Keyboard surface", "id": nid()}),
              fill(INK, name="Backdrop"),
              director_box] + chrome_xml + [stage] + events + [sm] + [a.xml() for a in ANIMS])
    comps = [coin_artboard(), share_card(), share_card_wide(), event_probe(), resize_probe(),
             el("ComponentAsset", {"artboardId": COIN_AB, "name": "Coin"}),
             el("ComponentAsset", {"artboardId": SHARE_AB, "name": "ShareCard"}),
             el("ComponentAsset", {"artboardId": SHARE_WIDE_AB, "name": "ShareCardWide"}),
             el("ComponentAsset", {"artboardId": MAIN, "name": "Recap"})]
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
    write_poses()
    write_boxes()
    print("wrote", len(ANIMS), "animations,", len(CONV), "converters,", len(PROPS), "properties")


if __name__ == "__main__":
    main()
