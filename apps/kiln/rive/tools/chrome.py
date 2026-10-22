"""Artboard shell, chrome (header, progress, controls) and the state machine."""
from __future__ import annotations

from rml import E, bind, ellipse, fill, poly, rect, shape, solid, stroke, paint_color, child, argb, mix, node
from gen_kiln import (ART_H, ART_W, CHAR, CLAY, H, PORC, SCENES, W, XFADE, Layer, settle)

# --------------------------------------------------------------------------
# conditions / transitions


def _cmp_num(g, prop):
    return E("TransitionPropertyViewModelComparator", {},
             E("BindablePropertyNumber", {}, bind(g.p(prop), 636)))


def c_num(g, prop, value, op="equal"):
    return E("TransitionViewModelCondition", {"opValue": op}, _cmp_num(g, prop),
             E("TransitionValueNumberComparator", {"value": float(value)}))


def c_bool(g, prop, value=True):
    return E("TransitionViewModelCondition", {"opValue": "equal"},
             E("TransitionPropertyViewModelComparator", {},
               E("BindablePropertyBoolean", {}, bind(g.p(prop), 634))),
             E("TransitionValueBooleanComparator", {"value": bool(value)}))


def trans(to, duration=0, conds=(), exit_pct=None, ease=None):
    a = {"stateToId": to if isinstance(to, str) else to.id, "duration": int(duration)}
    if exit_pct is not None:
        a.update(enableExitTime=True, exitTimeIsPercetange=True, exitTime=int(exit_pct))
    t = E("StateTransition", a, *conds)
    if ease and duration:
        x1, y1, x2, y2 = {"out": (0.16, 1, 0.3, 1), "inout": (0.65, 0, 0.35, 1), "soft": (0.4, 0, 0.2, 1)}[ease]
        t.attrs["interpolationType"] = "cubic"
        t.add(E("CubicEaseInterpolator", {"x1": x1, "y1": y1, "x2": x2, "y2": y2}))
    return t


def state(anim, x, y, *children, **kw):
    a = {"animationId": anim.id, "x": float(x), "y": float(y)}
    a.update(kw)
    s = E("AnimationState", a, *children)
    s.id  # noqa: B018
    return s


def vm_set(g, prop, value):
    """a ListenerViewModelChange writing a constant number"""
    return E("ListenerViewModelChange", {},
             E("BindablePropertyNumber", {"propertyValue": float(value)},
               bind(g.p(prop), 636, direction=True)))


def vm_increment(g, prop):
    rid = g_ids_next(g)
    return E("ListenerViewModelChange", {"fromViewModelProperty": True, "fromDataBindId": rid},
             E("BindablePropertyNumber", {},
               bind(g.p(prop), 636, g.plus_one.id, id=rid),
               bind(g.p(prop), 636, direction=True)))


def g_ids_next(g):
    from rml import ID
    return ID()


# --------------------------------------------------------------------------
# chrome


def chevron(color, left=False, size=7.0, thick=1.8):
    s = size
    pts = [(s * 0.45, -s), (-s * 0.45, 0), (s * 0.45, s)] if left else [(-s * 0.45, -s), (s * 0.45, 0), (-s * 0.45, s)]
    return poly(pts, closed=False), stroke(color, thick)


def build_chrome(g):
    M = g.M
    g.plus_one = g.conv(E("DataConverterRangeMapper", {"minInput": 0.0, "maxInput": 1.0, "minOutput": 1.0,
                                                        "maxOutput": 2.0, "name": "Plus one"}))
    bg = solid(SCENES[1]["bg"], name="Background")
    g.bg_paints.append(bg)
    ab_style = g.style(name="Artboard Style")
    g.artboard = E("Artboard", {"width": float(W), "height": float(H), "clip": True, "styleId": ab_style.id,
                                "viewModelId": M.vmid, "viewModelInstanceId": M.default_instance,
                                "name": "KilnRecap"}, ab_style, E("Fill", {"name": "Background"}, bg))
    g.artboard.id  # noqa: B018
    g.extra_anims = []

    # ---- root stage: hosts keyboard focus for the whole recap
    st = g.style(layoutWidthScaleType="fill", layoutHeightScaleType="fill", name="Stage Style")
    g.stage = g.box("Stage", st, w=10, h=10)
    g.stage.add(E("FocusData", {"canFocus": False, "canTraverse": False, "name": "Focus"}))
    g.stage.add(E("SemanticData", {"role": "group", "label": "Kiln 2026 recap", "name": "Semantics"}))
    g.artboard.add(g.stage)

    # ---- sequencer script: clock, navigation, hold, turntable drag, derived values
    sq_st = g.abs_style(top=0, bottom=0, left=0, right=0, name="Sequencer Style")
    g.stage.add(g.box("Sequencer", sq_st, E("ScriptedLayout", {"scriptAssetId": g.seq_script.id, "name": "Sequencer"}),
                      w=10, h=10))

    build_header(g)
    build_footer(g)

    # containers filled by scenes.py, in front-to-back order
    g.copy_root = g.stage  # copy boxes are absolute children of the stage
    card_stage = E("Node", {"name": "CardStage"})
    for prop, key in (("_cardX", 13), ("_cardY", 14), ("_cardScale", 16), ("_cardScale", 17)):
        card_stage.add(bind(g.p(prop), key))
    g.card_stage = card_stage
    art = E("Node", {"name": "ArtStage"})
    for prop, key in (("_artX", 13), ("_artY", 14), ("_artScale", 16), ("_artScale", 17)):
        art.add(bind(g.p(prop), key))
    g.art_stage = art


def ink(g, sc, alpha=1.0):
    g.ink_paints.append((sc, alpha))
    return sc


def build_header(g):
    ink0 = SCENES[1]["ink"]
    hs = g.abs_style(top=12, left=0, right=0, flexDirectionValue="row", layoutAlignmentType="centerLeft",
                     paddingLeft=24.0, paddingLeftUnitsValue="points", paddingRight=24.0,
                     paddingRightUnitsValue="points", gapHorizontal=16.0, gapHorizontalUnitsValue="points",
                     layoutHeightScaleType="fixed", name="Header Style")
    # side padding follows the layout's safe margin (24 in portrait, wider in landscape)
    hs.add(bind(g.p("_padX"), 512), bind(g.p("_padX"), 513))
    # landscape on large canvases scales the chrome up (scale + insets keep it edge to edge)
    hs.add(bind(g.p("_chromeR"), 517), bind(g.p("_hdrT"), 518))
    header = g.box("Header", hs, w=10, h=48, clip=False)
    header.add(bind(g.p("_chromeS"), 16), bind(g.p("_chromeS"), 17))

    wm_style = g.serif_style(25, ink0)
    ink(g, child(child(wm_style, "Fill"), "SolidColor"))
    wm = g.text("Wordmark", wm_style, "Kiln", width="hug", reveal=False)
    wm.add(E("SemanticData", {"role": "image", "label": "Kiln", "name": "Semantics"}))
    header.add(wm)

    segs_st = g.style(layoutWidthScaleType="fill", layoutHeightScaleType="fixed", flexDirectionValue="row",
                      layoutAlignmentType="centerLeft", gapHorizontal=4.0, gapHorizontalUnitsValue="points",
                      name="Progress Style")
    segs = g.box("Progress", segs_st, w=10, h=3)
    segs.add(E("SemanticData", {"role": "group", "label": "Story progress", "name": "Semantics"}))
    for i in range(1, 11):
        s_st = g.style(layoutWidthScaleType="fill", layoutHeightScaleType="fixed", cornerRadiusTL=1.5,
                       name=f"Segment {i} Style")
        s_st.add(bind(g.p(f"_seg{i}"), 596))
        track = solid(ink0, alpha=0.28)
        ink(g, track, 0.28)
        f_st = g.abs_style(top=0, bottom=0, left=0, right=0, cornerRadiusTL=1.5, name=f"Fill {i} Style")
        fillc = solid(ink0)
        ink(g, fillc)
        # scaleX = clamp(currentScreen - i + screenProgress, 0, 1)
        prog = g.formula(f"Segment{i}", g.fn("min"), g.tv(1), g.SEP(), g.fn("max"), g.tv(0), g.SEP(),
                         g.INPUT(), g.op("-"), g.tv(i), g.op("+"), g.tv(0, "screenProgress"), g.CLOSE(), g.CLOSE())
        fill_box = g.box(f"Segment {i} Fill", f_st, E("ComponentOrigin", {"originX": 0.0, "originY": 0.5, "name": "Origin"}),
                         E("Fill", {"name": "Fill"}, fillc), bind(g.p("currentScreen"), 16, prog.id), w=2, h=3)
        seg = g.box(f"Segment {i}", s_st, fill_box, E("Fill", {"name": "Track"}, track), w=2, h=3)
        segs.add(seg)
    header.add(segs)

    yr_style = g.sans_style(13, ink0, 600, spacing=0.6)
    ink(g, child(child(yr_style, "Fill"), "SolidColor"))
    yr = g.text("Year", yr_style, "2026", prop="year", conv=g.fmt(0, 0, "Year"), width="hug", reveal=False)
    header.add(yr)
    g.stage.add(header)


def icon_pause(color):
    s = shape("Pause Icon", 0, 0, rect(3.2, 13, 1.2, ox=0.5, oy=0.5), fill(color))
    s.children[0].attrs["x"] = -3.6
    s.add(E("Rectangle", {"x": 3.6, "width": 3.2, "height": 13.0, "cornerRadiusTL": 1.2, "originX": 0.5,
                          "originY": 0.5, "name": "Bar 2"}))
    return s


def icon_play(color):
    return shape("Play Icon", 1.5, 0, poly([(-5, -7), (7, 0), (-5, 7)], radius=1.5), fill(color))


def focus_ring(g, name, ink0, d=54.0):
    """keyboard focus ring: an outer ring in the scene's ink, shown by the Focus Ring layer"""
    sc = solid(ink0)
    ink(g, sc)
    ring = shape(f"{name} Focus Ring", 0, 0, ellipse(d, d), E("Stroke", {"thickness": 2.0, "name": "Ring"}, sc))
    settle(ring, "opacity", 0.0)
    settle(ring, "scaleX", 1.0)
    settle(ring, "scaleY", 1.0)
    g.focus_rings.append(ring)
    # a plain Node is not a layout participant, so the ring stays centred on the 44pt button
    return E("Node", {"x": 22.0, "y": 22.0, "name": f"{name} Focus"}, ring)


def focus_data(g, b):
    fd = E("FocusData", {"name": "Focus"})
    settle(fd, "canFocus", True, set_attr=False)
    g.focus_datas[b.attrs["name"]] = fd
    return fd


def circle_button(g, name, label_prop, icon_children, ink0, filled=False):
    st = g.style(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", cornerRadiusTL=22.0,
                 layoutAlignmentType="center", name=f"{name} Style")
    b = g.box(name, st, w=44, h=44)
    b.add(focus_data(g, b))
    b.add(E("SemanticData", {"role": "button", "name": "Semantics"}, bind(g.p(label_prop), 983)))
    sc = solid(ink0, alpha=0.5)
    ink(g, sc, 0.5)
    b.add(E("Stroke", {"thickness": 1.3, "name": "Ring"}, sc))
    holder = E("Node", {"x": 22.0, "y": 22.0, "name": "Icon"}, *icon_children)
    b.add(holder)
    b.add(focus_ring(g, name, ink0))
    return b


def build_footer(g):
    g.focus_rings, g.focus_pills, g.focus_datas = [], [], {}
    ink0 = SCENES[1]["ink"]
    bg0 = SCENES[1]["bg"]
    fs = g.abs_style(bottom=18, left=0, right=0, layoutHeightScaleType="fixed", name="Footer Style")
    fs.add(bind(g.p("_chromeR"), 517), bind(g.p("_ftrB"), 519))
    footer = g.box("Footer", fs, w=10, h=56, clip=False)
    footer.add(bind(g.p("_chromeS"), 16), bind(g.p("_chromeS"), 17))

    # --- story navigation controls
    ns = g.abs_style(top=0, bottom=0, left=20, right=20, flexDirectionValue="row",
                     layoutAlignmentType="spaceBetweenCenter", name="Nav Style")
    ns.add(bind(g.p("_navX"), 516), bind(g.p("_navX"), 517))
    nav = g.box("Nav Controls", ns, w=10, h=56)
    cl_st = g.style(layoutWidthScaleType="hug", layoutHeightScaleType="hug", flexDirectionValue="row",
                    gapHorizontal=10.0, gapHorizontalUnitsValue="points", name="Left Cluster Style")
    left = g.box("Left Cluster", cl_st, w=98, h=44)

    pc = solid(ink0)
    ink(g, pc)
    pv_path, pv_stroke = chevron(ink0, left=True)
    pv_stroke.children[0] = pc
    prev_icon = shape("Chevron", -1, 0, pv_path, pv_stroke)
    g.btn_prev = circle_button(g, "Previous Button", "previousLabel", [prev_icon], ink0)

    pz = solid(ink0)
    ink(g, pz)
    pause = icon_pause(ink0)
    pause.children[-2].children[0] = pz  # the fill's colour
    py = solid(ink0)
    ink(g, py)
    play = icon_play(ink0)
    play.children[-1].children[0] = py
    settle(play, "opacity", 0.0)
    settle(pause, "opacity", 1.0)
    g.icon_play, g.icon_pause = play, pause
    g.btn_pause = circle_button(g, "Pause Button", "pauseLabel", [pause, play], ink0)
    left.add(g.btn_prev, g.btn_pause)
    nav.add(left)

    cs = g.style(layoutWidthScaleType="hug", layoutHeightScaleType="fixed", flexDirectionValue="row",
                 layoutAlignmentType="centerRight", gapHorizontal=12.0, gapHorizontalUnitsValue="points",
                 paddingLeft=14.0, paddingLeftUnitsValue="points", name="Continue Style")
    cont = g.box("Continue Button", cs, w=150, h=48)
    cont.add(focus_data(g, cont))
    cont.add(E("SemanticData", {"role": "button", "name": "Semantics"}, bind(g.p("continueLabel"), 983)))
    lab_style = g.sans_style(16, ink0, 600)
    ink(g, child(child(lab_style, "Fill"), "SolidColor"))
    lab = g.text("Continue Label", lab_style, "Continue", prop="continueLabel", width="hug", reveal=False,
                 nowrap=True)
    cont.add(lab)
    circ_st = g.style(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", cornerRadiusTL=22.0, name="Circle Style")
    cc = solid(ink0)
    ink(g, cc)
    chv_c = solid(bg0)
    g.bg_paints.append(chv_c)
    cp, cst = chevron(bg0)
    cst.children[0] = chv_c
    circle = g.box("Continue Circle", circ_st, E("Fill", {"name": "Fill"}, cc),
                   E("Node", {"x": 23.0, "y": 22.0, "name": "Icon"}, shape("Chevron", 0, 0, cp, cst)),
                   focus_ring(g, "Continue", ink0), w=44, h=44)
    cont.add(circle)
    # transparent hit pad so the whole pill is a 48pt target
    cont.add(E("Fill", {"name": "Hit"}, solid(ink0, alpha=0.0)))
    nav.add(cont)
    g.btn_continue = cont
    footer.add(nav)

    # --- summary actions (share / replay)
    ss = g.abs_style(top=0, bottom=0, left=20, right=20, flexDirectionValue="row", layoutAlignmentType="center",
                     gapHorizontal=12.0, gapHorizontalUnitsValue="points", name="Summary Actions Style")
    # portrait: centred in the footer; landscape: left-aligned under the summary copy column
    ss.add(bind(g.p("_actL"), 516), bind(g.p("_actR"), 517), bind(g.p("_actAlign"), 632))
    acts = g.box("Summary Actions", ss, w=10, h=56)

    def pill(name, label_prop, literal, filled, icon):
        st = g.style(layoutWidthScaleType="hug", layoutHeightScaleType="fixed", flexDirectionValue="row",
                     layoutAlignmentType="center", gapHorizontal=8.0, gapHorizontalUnitsValue="points",
                     paddingLeft=16.0, paddingLeftUnitsValue="points", paddingRight=16.0,
                     paddingRightUnitsValue="points", cornerRadiusTL=24.0, name=f"{name} Style")
        b = g.box(name, st, w=140, h=48)
        b.add(focus_data(g, b))
        b.add(E("SemanticData", {"role": "button", "name": "Semantics"}, bind(g.p(label_prop), 983)))
        tcol = PORC if filled else CHAR
        b.add(icon)
        ls = g.sans_style(15, tcol, 700)
        b.add(g.text(f"{name} Label", ls, literal, prop=label_prop, width="hug", reveal=False, nowrap=True))
        # keyboard focus: a clay outline on the pill itself, faded in by the Focus Ring layer
        fc = solid(CLAY, alpha=0.0)
        settle(fc, "colorValue", argb(CLAY, 0.0), set_attr=False)
        g.focus_pills.append(fc)
        b.add(E("Stroke", {"thickness": 3.0, "name": "Focus"}, fc))
        if filled:
            b.add(E("Fill", {"name": "Fill"}, solid(CHAR)))
        else:
            b.add(E("Stroke", {"thickness": 1.4, "name": "Ring"}, solid(CHAR, alpha=0.7)))
            b.add(E("Fill", {"name": "Hit"}, solid(CHAR, alpha=0.0)))
        return b

    share_icon = shape("Share Icon", 0, 0,
                       poly([(-6, -1), (-6, 7), (6, 7), (6, -1)], closed=False), stroke(PORC, 1.8))
    share_icon.add(E("LayoutParticipant", {"layoutWidthScaleType": "hug", "layoutHeightScaleType": "hug", "name": "Layout"}))
    share_arrow = shape("Share Arrow", 0, 0, poly([(0, 3), (0, -9)], closed=False), poly([(-4, -5), (0, -9), (4, -5)], closed=False),
                        stroke(PORC, 1.8))
    share_holder = E("Node", {"name": "Share Glyph"}, share_arrow)
    share_icon.add(share_holder)
    replay_icon = shape("Replay Icon", 0, 0,
                        E("PointsPath", {"isClosed": False, "name": "Arc"},
                          *[E("StraightVertex", {"x": round(7 * __import__('math').cos(a), 2), "y": round(7 * __import__('math').sin(a), 2)})
                            for a in [(-0.6 + k * 0.45) for k in range(12)]]),
                        poly([(5.0, -8.0), (5.8, -3.6), (1.4, -3.4)], closed=False),
                        stroke(CHAR, 1.8))
    replay_icon.add(E("LayoutParticipant", {"layoutWidthScaleType": "hug", "layoutHeightScaleType": "hug", "name": "Layout"}))
    g.btn_share = pill("Share Button", "shareLabel", "Share", True, share_icon)
    g.btn_replay = pill("Replay Button", "replayLabel", "Replay", False, replay_icon)
    acts.add(g.btn_share, g.btn_replay)
    footer.add(acts)
    g.nav_controls, g.summary_actions = nav, acts
    settle(nav, "opacity", 1.0)
    settle(nav, "x", 0.0)
    settle(acts, "opacity", 0.0)
    settle(acts, "x", 4000.0)
    g.stage.add(footer)
    g.footer = footer


# --------------------------------------------------------------------------
# state machine


def scene_states(g, n, L: Layer, A: dict):
    """Wire one scene layer. A: hidden, enterF, enterB, enterRM, idle, frozen, exitF, exitB, exitRM"""
    cs = lambda op="equal": c_num(g, "currentScreen", n, op)  # noqa: E731
    rm = lambda v: c_bool(g, "reducedMotion", v)  # noqa: E731
    fw = c_num(g, "_navDir", 0, "greaterThanOrEqual")
    S = {}
    pos = {"hidden": (0, 0), "enterF": (220, -140), "enterB": (220, 0), "enterRM": (220, 140), "idle": (460, -60),
           "frozen": (460, 120), "exitF": (700, -140), "exitB": (700, 0), "exitRM": (700, 140)}
    for k, a in A.items():
        S[k] = state(a, *pos[k])

    def enters(dur):
        return [trans(S["enterRM"], 0, [cs(), rm(True)]),
                trans(S["enterF"], dur, [cs(), rm(False), c_num(g, "_navDir", 0, "greaterThanOrEqual")]),
                trans(S["enterB"], dur, [cs(), rm(False), c_num(g, "_navDir", 0, "lessThan")])]

    def exits():
        return [trans(S["exitRM"], 0, [cs("notEqual"), rm(True)]),
                trans(S["exitF"], XFADE, [cs("notEqual"), rm(False), c_num(g, "_navDir", 0, "greaterThanOrEqual")]),
                trans(S["exitB"], XFADE, [cs("notEqual"), rm(False), c_num(g, "_navDir", 0, "lessThan")])]

    S["hidden"].add(*enters(0))
    for k in ("enterF", "enterB", "enterRM"):
        S[k].add(*exits())
        S[k].add(trans(S["idle"], 0, [], exit_pct=100))
    S["idle"].add(*exits())
    S["idle"].add(trans(S["frozen"], 0, [c_bool(g, "_frozen", True)]))
    S["frozen"].add(*exits())
    S["frozen"].add(trans(S["idle"], 0, [c_bool(g, "_frozen", False)]))
    for k in ("exitF", "exitB", "exitRM"):
        S[k].add(*enters(XFADE))
        S[k].add(trans(S["hidden"], 0, [], exit_pct=100))
    L.el.add(E("AnyState", {"x": 0.0, "y": -200.0}), E("ExitState", {"x": 900.0, "y": -200.0}),
             E("EntryState", {"x": -220.0, "y": 0.0}, trans(S["hidden"])))
    for s in S.values():
        L.el.add(s)


def build_machine(g):
    sm = E("StateMachine", {"name": "Recap"})
    g.artboard.attrs["defaultStateMachineId"] = sm.id

    # ---- footer mode + initial focus
    L = Layer("Controls")
    a_nav = L.anim("Controls Story", 20)
    a_nav.k(g.nav_controls, "opacity", (0, 1.0, "out")).k(g.nav_controls, "x", (0, 0.0, "hold"))
    a_nav.k(g.summary_actions, "opacity", (0, 0.0, "hold")).k(g.summary_actions, "x", (0, 4000.0, "hold"))
    a_sum = L.anim("Controls Summary", 30)
    a_sum.k(g.nav_controls, "opacity", (0, 0.0, "hold")).k(g.nav_controls, "x", (0, 4000.0, "hold"))
    a_sum.k(g.summary_actions, "opacity", (0, 0.0, "hold"), (10, 0.0, "out"), (30, 1.0, "out"))
    a_sum.k(g.summary_actions, "x", (0, 0.0, "hold"))
    # only the visible controls take focus: hidden ones leave the tab order
    story = ("Previous Button", "Pause Button", "Continue Button")
    for nm, fd in g.focus_datas.items():
        a_nav.k(fd, "canFocus", (0, nm in story, "hold"))
        a_sum.k(fd, "canFocus", (0, nm not in story, "hold"))
    # a second, settled state per mode re-targets focus once its controls are focusable again
    # (a FocusActionTarget in the same frame that keys canFocus finds nothing to focus)
    a_nav2 = L.anim("Controls Story Ready", 1)
    a_sum2 = L.anim("Controls Summary Ready", 1)
    a_nav2.k(g.nav_controls, "opacity", (0, 1.0, "hold")).k(g.nav_controls, "x", (0, 0.0, "hold"))
    a_nav2.k(g.summary_actions, "opacity", (0, 0.0, "hold")).k(g.summary_actions, "x", (0, 4000.0, "hold"))
    a_sum2.k(g.nav_controls, "opacity", (0, 0.0, "hold")).k(g.nav_controls, "x", (0, 4000.0, "hold"))
    a_sum2.k(g.summary_actions, "opacity", (0, 1.0, "hold")).k(g.summary_actions, "x", (0, 0.0, "hold"))
    for nm, fd in g.focus_datas.items():
        a_nav2.k(fd, "canFocus", (0, nm in story, "hold"))
        a_sum2.k(fd, "canFocus", (0, nm not in story, "hold"))
    s_nav = state(a_nav, 200, 0, E("FocusActionTarget", {"targetId": g.btn_continue.id}))
    s_nav2 = state(a_nav2, 420, 0, E("FocusActionTarget", {"targetId": g.btn_continue.id}))
    s_sum = state(a_sum, 200, 140)
    s_sum2 = state(a_sum2, 420, 140, E("FocusActionTarget", {"targetId": g.btn_share.id}))
    for st in (s_nav, s_nav2):
        st.add(trans(s_sum, 0, [c_num(g, "currentScreen", 10)]))
    for st in (s_sum, s_sum2):
        st.add(trans(s_nav, 0, [c_num(g, "currentScreen", 10, "notEqual")]))
    s_nav.add(trans(s_nav2, 0, [], exit_pct=100))
    s_sum.add(trans(s_sum2, 0, [], exit_pct=100))
    L.el.add(E("AnyState", {"x": 0.0, "y": -140.0}), E("ExitState", {"x": 400.0, "y": -140.0}),
             E("EntryState", {"x": 0.0, "y": 0.0}, trans(s_nav)), s_nav, s_nav2, s_sum, s_sum2)
    g.layers.append(L)

    # ---- pause / play glyph
    L = Layer("Pause Glyph")
    a_pl = L.anim("Playing", 12)
    a_pl.k(g.icon_pause, "opacity", (0, 1.0, "out")).k(g.icon_play, "opacity", (0, 0.0, "hold"))
    a_pa = L.anim("Paused", 12)
    a_pa.k(g.icon_pause, "opacity", (0, 0.0, "hold")).k(g.icon_play, "opacity", (0, 1.0, "out"))
    s_pl = state(a_pl, 200, 0)
    s_pa = state(a_pa, 200, 140)
    s_pl.add(trans(s_pa, 120, [c_bool(g, "isPaused", True)]))
    s_pa.add(trans(s_pl, 120, [c_bool(g, "isPaused", False)]))
    L.el.add(E("AnyState", {"x": 0.0, "y": -140.0}), E("ExitState", {"x": 400.0, "y": -140.0}),
             E("EntryState", {"x": 0.0, "y": 0.0}, trans(s_pl)), s_pl, s_pa)
    g.layers.append(L)

    # ---- screenChanged: exactly one emission per change of currentScreen
    L = Layer("Events")
    any_ = E("AnyState", {"x": 0.0, "y": -160.0})
    for n in range(1, 11):
        a = L.anim(f"Screen {n} Event", 1, exempt=True)
        s = state(a, 200 + (n - 1) * 140, 100 if n % 2 else 220,
                  E("StateMachineFireEvent", {"eventId": g.events["screenChanged"].id, "occursValue": 0}),
                  vm_increment(g, "_screenChangedCount"))
        any_.add(trans(s, 0, [c_num(g, "currentScreen", n)]))
        L.el.add(s)
    L.el.children.insert(0, any_)
    L.el.children.insert(1, E("ExitState", {"x": 1700.0, "y": -160.0}))
    L.el.children.insert(2, E("EntryState", {"x": -200.0, "y": 0.0}))
    g.layers.append(L)

    # ---- recapFinished: latched by the sequencer once the summary has settled
    L = Layer("Completion")
    a_w = L.anim("Waiting", 1, exempt=True)
    a_f = L.anim("Finished", 1, exempt=True)
    s_w = state(a_w, 200, 0)
    s_f = state(a_f, 200, 140, E("StateMachineFireEvent", {"eventId": g.events["recapFinished"].id, "occursValue": 0}),
                vm_increment(g, "_recapFinishedCount"))
    s_w.add(trans(s_f, 0, [c_num(g, "_finished", 1)]))
    s_f.add(trans(s_w, 0, [c_num(g, "_finished", 0)]))
    L.el.add(E("AnyState", {"x": 0.0, "y": -140.0}), E("ExitState", {"x": 400.0, "y": -140.0}),
             E("EntryState", {"x": 0.0, "y": 0.0}, trans(s_w)), s_w, s_f)
    g.layers.append(L)

    # ---- keyboard focus ring. Driven by two state-machine inputs (not view model data: focus is
    # presentation only and the UserRecap contract stays unchanged). Rings appear only after Tab,
    # like :focus-visible, so pointer users and the arrow-key walkthrough never see them.
    in_idx = E("StateMachineNumber", {"name": "focusedControl"})
    in_kb = E("StateMachineBool", {"name": "keyboardFocus"})
    in_idx.id, in_kb.id  # noqa: B018
    g.sm_inputs = [in_idx, in_kb]
    L = Layer("Focus Ring")
    rings = g.focus_rings          # previous, pause, continue
    pills = g.focus_pills          # share, replay
    targets = [("ring", r) for r in rings] + [("pill", p) for p in pills]
    a_none = L.anim("Focus None", 10)
    for kind, t in targets:
        if kind == "ring":
            a_none.k(t, "opacity", (0, 0.0, "hold"))
        else:
            a_none.k(t, "colorValue", (0, argb(CLAY, 0.0), "hold"))
    s_none = state(a_none, 200, 0)
    focus_states = []
    for k, (kind, t) in enumerate(targets, start=1):
        a = L.anim(f"Focus {k}", 16)
        for j, (kind2, t2) in enumerate(targets, start=1):
            if kind2 == "ring":
                if j == k:
                    a.k(t2, "opacity", (0, 0.0, "hold"), (1, 0.0, "out"), (10, 1.0, "hold"))
                    a.k(t2, "scaleX", (0, 1.3, "hold"), (1, 1.3, "back"), (14, 1.0, "hold"))
                    a.k(t2, "scaleY", (0, 1.3, "hold"), (1, 1.3, "back"), (14, 1.0, "hold"))
                else:
                    a.k(t2, "opacity", (0, 0.0, "hold"))
            else:
                if j == k:
                    a.k(t2, "colorValue", (0, argb(CLAY, 0.0), "hold"), (1, argb(CLAY, 0.0), "out"),
                        (10, argb(CLAY, 1.0), "hold"))
                else:
                    a.k(t2, "colorValue", (0, argb(CLAY, 0.0), "hold"))
        focus_states.append(state(a, 420, -200 + k * 90))
    any_f = E("AnyState", {"x": 0.0, "y": -160.0})
    any_f.add(E("StateTransition", {"stateToId": s_none.id, "duration": 0},
                E("TransitionBoolCondition", {"inputId": in_kb.id, "opValue": "notEqual"})))
    any_f.add(E("StateTransition", {"stateToId": s_none.id, "duration": 0},
                E("TransitionNumberCondition", {"inputId": in_idx.id, "opValue": "equal", "value": 0.0})))
    for k, st in enumerate(focus_states, start=1):
        any_f.add(E("StateTransition", {"stateToId": st.id, "duration": 0},
                    E("TransitionBoolCondition", {"inputId": in_kb.id, "opValue": "equal"}),
                    E("TransitionNumberCondition", {"inputId": in_idx.id, "opValue": "equal", "value": float(k)})))
    L.el.add(any_f, E("ExitState", {"x": 700.0, "y": -160.0}),
             E("EntryState", {"x": 0.0, "y": 0.0}, trans(s_none)), s_none, *focus_states)
    g.layers.append(L)

    for inp in g.sm_inputs:
        sm.add(inp)
    for L in g.layers:
        sm.add(L.el)

    # ---- listeners
    def cmd_listener(name, target, value, keys=(), semantic=True, click=True):
        li = E("StateMachineListener", {"targetId": target.id, "name": name})
        if click:
            li.add(E("ListenerInputType", {"listenerTypeValue": "click"}))
        if keys:
            kb = E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"})
            for k in keys:
                kb.add(E("KeyboardInput", {"keyType": k, "keyPhase": 1}))
            li.add(kb)
        if semantic:
            li.add(E("ListenerInputTypeSemantic", {"listenerTypeValue": "semanticAction"},
                     E("SemanticInput", {"actionType": "tap"})))
        return li

    li = cmd_listener("Continue", g.btn_continue, 1, keys=("enter",))
    li.add(vm_set(g, "_command", 1))
    sm.add(li)
    li = cmd_listener("Previous", g.btn_prev, 2, keys=("enter",))
    li.add(vm_set(g, "_command", 2))
    sm.add(li)
    li = cmd_listener("Pause", g.btn_pause, 3, keys=("enter",))
    li.add(vm_set(g, "_command", 3))
    sm.add(li)
    li = cmd_listener("Replay", g.btn_replay, 5, keys=("enter",))
    li.add(vm_set(g, "_command", 5))
    sm.add(li)
    li = cmd_listener("Share", g.btn_share, 4, keys=("enter",))
    li.add(E("ListenerFireEvent", {"eventId": g.events["shareTapped"].id}))
    li.add(vm_increment(g, "_shareTappedCount"))
    sm.add(li)
    # focus tracking for the ring: each control reports itself as it takes focus
    controls = [g.btn_prev, g.btn_pause, g.btn_continue, g.btn_share, g.btn_replay]
    for k, b in enumerate(controls, start=1):
        li = E("StateMachineListener", {"targetId": b.id, "name": f"Focus {k}"},
               E("ListenerInputType", {"listenerTypeValue": "focus"}),
               E("ListenerNumberChange", {"inputId": in_idx.id, "value": float(k)}))
        sm.add(li)
    # Tab / Shift+Tab move focus between the visible controls and switch the rings on;
    # any pointer press switches them off again
    for name, mods, kind in (("Tab Next", 0, "next"), ("Tab Previous", 1, "previous")):
        sm.add(E("StateMachineListener", {"targetId": g.stage.id, "name": name},
                 E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
                   E("KeyboardInput", {"keyType": "tab", "keyPhase": 3, "modifiers": mods})),
                 E("FocusActionTraversal", {"traversalKind": kind}),
                 E("ListenerBoolChange", {"inputId": in_kb.id, "value": 1})))
    sm.add(E("StateMachineListener", {"targetId": g.stage.id, "name": "Pointer Hides Focus"},
             E("ListenerInputType", {"listenerTypeValue": "down"}),
             E("ListenerBoolChange", {"inputId": in_kb.id, "value": 0})))
    # stage-wide keys (bubble up from whichever control holds focus)
    for name, key, value in (("Key Next", "right", 1), ("Key Previous", "left", 2), ("Key Pause", "space", 3)):
        li = E("StateMachineListener", {"targetId": g.stage.id, "name": name},
               E("ListenerInputTypeKeyboard", {"listenerTypeValue": "keyboard"},
                 E("KeyboardInput", {"keyType": key, "keyPhase": 1})))
        li.add(vm_set(g, "_command", value))
        sm.add(li)

    g.artboard.add(sm)
    for ev in g.events.values():
        g.artboard.add(ev)
