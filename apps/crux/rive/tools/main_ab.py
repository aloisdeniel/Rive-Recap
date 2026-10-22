"""Main (host-facing) artboard: responsive chrome, the Stage component, the director
script, controls, focus/keyboard/semantics and the host events."""
from rml import (E, nid, shape, poly, ellipse, rect, fill, stroke, solid, bind, Anim,
                 cond_num, cond_bool, cond_trigger, write_num, fire_trigger, transition,
                 CHALK, COAL, ACID, COBALT, CHALK_D)
from art import text, FONT_MONO, FONT_MONO_M, WORDMARK_AB, arrow, alpha
import conv
import os
import model
from model import path, rig_path
from stage import STAGE_AB, STAGE_SM


def rb(name, key, conv_id=None):
    """Bind a property to a CruxRig value (the director's responsive layout)."""
    return bind(rig_path(name), key, conv_id)

MAIN_AB = "0:20"
MAIN_SM = "0:21"
DIRECTOR_ASSET = "0:80"

ANIMS = []


def style(**kw):
    kw.setdefault("name", "Style")
    return E("LayoutComponentStyle", **kw)


def box(name, w, h, st_kwargs, kids=(), fill_c=None, **kw):
    st = style(**st_kwargs)
    b = E("LayoutComponent", width=w, height=h, styleId=st.id, name=name, x=kw.get("x"), opacity=kw.get("opacity"))
    b.add(st)
    if fill_c:
        b.add(fill(fill_c))
    if kw.get("stroke_c"):
        b.add(stroke(kw["stroke_c"], kw.get("stroke_w", 2)))
    b.add(list(kids))
    return b


def absolute(top=None, left=None, right=None, bottom=None, **kw):
    d = dict(positionTypeValue="absolute", **kw)
    if left is not None and right is not None:
        d["widthUnitsValue"] = "auto"     # stretch between the insets
    if top is not None and bottom is not None:
        d["heightUnitsValue"] = "auto"
    for side, v in (("Top", top), ("Left", left), ("Right", right), ("Bottom", bottom)):
        if v is not None:
            d[f"position{side}"] = v
            d[f"position{side}UnitsValue"] = "points"
    return d


def pad(d, l=0, r=0, t=0, b=0):
    for side, v in (("Left", l), ("Right", r), ("Top", t), ("Bottom", b)):
        if v:
            d[f"padding{side}"] = v
            d[f"padding{side}UnitsValue"] = "points"
    return d


FOCUS = {}      # control -> index for focusedControl
CONTROLS = {}


def button(key, n, w, h, radius, fill_c, label_prop, icon_kids, extra=()):
    """A focusable, labelled control. The focus ring shows when focusedControl == n.
    Round buttons take their size from the rig (52 pt, 48 or 44 on short canvases)."""
    FOCUS[key] = n
    half = "pillHalf" if not w else "btnHalf"
    ring_st = style(**absolute(top=-5, left=-5, right=-5, bottom=-5), cornerRadiusTL=radius + 5,
                    layoutWidthScaleType="fill", layoutHeightScaleType="fill")
    ring_st.add(rb(half, 640, conv.affine(1, 5, "Plus 5")))
    ring = E("LayoutComponent", width=w + 10, height=h + 10, styleId=ring_st.id, name=f"{key} Focus Ring")
    ring.add(ring_st, stroke(COBALT, 3))
    ring.add(bind(path("focusedControl"), 18, conv.equals(n, "Focused is")))
    sem = E("SemanticData", role="button", label=key, name="Semantics",
            kids=[bind(path(label_prop), 983)])
    st = style(cornerRadiusTL=radius, layoutWidthScaleType="fixed" if w else "fill", layoutHeightScaleType="fixed")
    st.add(rb(half, 640))
    b = E("LayoutComponent", width=w or 40, height=h, styleId=st.id, name=key)
    b.add(st, fill(fill_c), stroke(CHALK if fill_c == COAL else COAL, 2))
    if w:
        b.add(rb("btn", 7), rb("btn", 8))
    b.kids.insert(1, E("FocusData", name="Focus"))
    b.kids.insert(2, sem)
    b.add(ring)
    b.add(list(extra))
    icon = E("Node", name=f"{key} Icon", x=(w or 0) / 2, y=h / 2, kids=list(icon_kids))
    if w:
        icon.add(rb("btnHalf", 13), rb("btnHalf", 14))
    b.add(icon)
    CONTROLS[key] = b
    return b


def build():
    # -------------------------------------------------------------- top bar
    wm_slot = box("Wordmark Slot", 66, 24, dict(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed"),
                  [E("NestedArtboardLeaf", artboardId=WORDMARK_AB, fit="contain", name="Wordmark")])
    segs = []
    for j in range(1, 11):
        bar = box(f"Segment {j} Fill", 2, 4, dict(absolute(top=0, left=0, right=0, bottom=0),
                                                   layoutWidthScaleType="fill", layoutHeightScaleType="fill"), fill_c=COAL)
        bar.kids.insert(1, E("ComponentOrigin", originX=0, originY=0.5, name="Origin"))
        bar.add(bind(path("progressValue"), 16, conv.range_map(f"Segment {j} Fill", j - 1, j, 0, 1)))
        slot_st = style(layoutWidthScaleType="fill", layoutHeightScaleType="fixed", cornerRadiusTL=2, name=f"Segment {j} Style")
        slot_st.add(bind(path("visibleScreenCount"), 596, conv.hidden_after(j, f"Segment {j} hidden")))
        slot = E("LayoutComponent", width=2, height=4, styleId=slot_st.id, clip=True, name=f"Segment {j}")
        slot.add(slot_st, fill(alpha(COAL, 0.18)), bar)
        segs.append(slot)
    progress = box("Progress", 40, 4, dict(layoutWidthScaleType="fill", layoutHeightScaleType="fixed",
                                            flexDirectionValue="row", gapHorizontal=4, gapHorizontalUnitsValue="points"), segs)
    progress.add(E("SemanticData", role="text", isLiveRegion=True, label="Story progress", name="Semantics",
                   kids=[bind(path("screenAnnouncement"), 984)]))
    year = text("Year", 0, 0, 0, 0, FONT_MONO_M, 13, COAL, [("2026", "yearDisplay", None)], sizing="autoWidth", lh=16)
    year.kids.insert(0, E("LayoutParticipant", layoutWidthScaleType="hug", layoutHeightScaleType="hug", name="Year Layout"))
    rule = box("Rule", 390, 2, dict(absolute(left=0, right=0, bottom=0), layoutWidthScaleType="fill",
                                    layoutHeightScaleType="fixed"), fill_c=COAL)
    top = box("Top Bar", 390, 64, pad(dict(layoutWidthScaleType="fill",
                                            layoutHeightScaleType="fixed", flexDirectionValue="row",
                                            layoutAlignmentType="centerLeft", gapHorizontal=14,
                                            gapHorizontalUnitsValue="points"), l=20, r=20),
              [rule, wm_slot, progress, year], fill_c=CHALK)
    # responsive chrome: bar height and side padding follow the canvas (rig)
    top.add(rb("topH", 8))
    top.kids[0].add(rb("barPad", 512), rb("barPad", 513))

    # -------------------------------------------------------------- bottom bar
    prev = button("Previous", 1, 52, 52, 26, COAL, "previousLabel", [arrow("Back", CHALK, 3, 0, 0, 1.0, flip=True)])
    pause_icon = E("Node", name="Pause Glyph", kids=[shape("Bars", [rect(5, 18, x=-5), rect(5, 18, x=5)], [fill(CHALK)])])
    play_icon = E("Node", name="Play Glyph", opacity=0.0, kids=[shape("Play", [poly([(-5, -9), (9, 0), (-5, 9)], radius=1.5)], [fill(ACID)])])
    pause = button("Pause", 2, 52, 52, 26, COAL, "pauseButtonLabel", [pause_icon, play_icon])
    replay_trim = E("TrimPath", start=0.08, end=0.86, offset=0, modeValue="sequential", name="Open")
    replay = button("Replay", 3, 52, 52, 26, COAL, "replayLabel", [
        shape("Loop", [ellipse(20)], [E("Stroke", thickness=3, cap="round", name="Stroke", kids=[solid(CHALK), replay_trim])]),
        shape("Head", [poly([(6, -12), (12, -4), (2, -3)], radius=1)], [fill(CHALK)])])
    mid = box("Middle Slot", 52, 52, dict(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed"), [replay, pause])
    mid.add(rb("btn", 7), rb("btn", 8))
    cont_label = text("Continue Label", 0, 0, 0, 0, FONT_MONO_M, 15, CHALK, [("Continue", "continueLabel", None)],
                      sizing="autoWidth", lh=18, overflow="ellipsis")
    cont_label.kids.insert(0, E("LayoutParticipant", layoutWidthScaleType="fill", layoutHeightScaleType="hug", name="Label Layout"))
    cont_label.a["wrapValue"] = "noWrap"
    share_label = text("Share Label", 0, 0, 0, 0, FONT_MONO_M, 15, COAL, [("Share", "shareLabel", None)],
                       sizing="autoWidth", lh=18, overflow="ellipsis")
    share_label.kids.insert(0, E("LayoutParticipant", layoutWidthScaleType="fill", layoutHeightScaleType="hug", name="Label Layout"))
    pill_st = lambda: pad(dict(layoutWidthScaleType="fill",
                               layoutHeightScaleType="fill", flexDirectionValue="row", layoutAlignmentType="centerLeft",
                               cornerRadiusTL=28, gapHorizontal=10, gapHorizontalUnitsValue="points"), l=24, r=20)
    cont = button("Continue", 4, 0, 56, 28, COAL, "continueLabel", [])
    cont.kids[0].a.update(pill_st())
    cont.kids.pop()  # pills lay their content out instead of a centred icon
    cont.add(cont_label, box("Continue Arrow", 24, 24, dict(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed"),
                             [E("Node", name="Arrow Art", x=12, y=12, kids=[arrow("Arrow", ACID, 3, 0, 0)])]))
    share = button("Share", 5, 0, 56, 28, ACID, "shareLabel", [])
    share.kids[0].a.update(pill_st())
    share.kids.pop()
    share.add(share_label, box("Share Glyph", 24, 24, dict(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed"),
                               [E("Node", name="Share Art", x=12, y=12, kids=[
                                   shape("Up", [poly([(0, 6), (0, -9)], closed=False), poly([(-6, -3), (0, -9), (6, -3)], closed=False)],
                                         [stroke(COAL, 3, cap="square", join="miter")]),
                                   shape("Tray", [poly([(-9, 2), (-9, 10), (9, 10), (9, 2)], closed=False)], [stroke(COAL, 3, join="miter")])])]))
    # the pill fills the bar on phones and stops at 380 pt on wide canvases, where the
    # bar spreads into [Previous, Pause] ... [Continue]
    pill = box("Pill Slot", 40, 56, dict(layoutWidthScaleType="fill", layoutHeightScaleType="fixed",
                                         maxWidth=380, maxWidthUnitsValue="points"), [share, cont])
    pill.add(rb("pill", 8))
    cluster = box("Left Controls", 114, 52, dict(layoutWidthScaleType="hug", layoutHeightScaleType="hug",
                                                 flexDirectionValue="row", layoutAlignmentType="centerLeft",
                                                 gapHorizontal=10, gapHorizontalUnitsValue="points"), [prev, mid])
    bottom = box("Bottom Bar", 390, 104, pad(dict(layoutWidthScaleType="fill",
                                                  layoutHeightScaleType="fixed", flexDirectionValue="row",
                                                  layoutAlignmentType="spaceBetweenCenter", gapHorizontal=10,
                                                  gapHorizontalUnitsValue="points"), l=20, r=20, b=18),
                 [cluster, pill])
    bottom.add(rb("botH", 8))
    bottom.kids[0].add(rb("barPad", 512), rb("barPad", 513), rb("botPad", 515))

    # -------------------------------------------------------------- stage + director
    # fit=layout: the stage artboard is resized to the canvas; the director lays its blocks out
    stage_leaf = E("NestedArtboardLeaf", artboardId=STAGE_AB, fit="layout", name="Stage",
                   kids=[E("NestedStateMachine", animationId=STAGE_SM, name="Story")])
    stage_box = box("Stage Box", 390, 844, dict(absolute(top=0, left=0, right=0, bottom=0), layoutWidthScaleType="fill",
                                                layoutHeightScaleType="fill"), [stage_leaf], fill_c=CHALK)
    stage_box.a["clip"] = True
    director = E("ScriptedLayout", scriptAssetId=DIRECTOR_ASSET, name="Director",
                 kids=[E("FocusData", canTraverse=False, name="Focus")])
    dbox = box("Director Box", 390, 844, dict(absolute(top=0, left=0, right=0, bottom=0), layoutWidthScaleType="fill",
                                              layoutHeightScaleType="fill"), [director])
    root_focus = E("FocusData", canFocus=False, name="Keys")
    spacer = box("Story Area", 390, 600, dict(layoutWidthScaleType="fill", layoutHeightScaleType="fill"))
    root = box("Root", 390, 844, dict(layoutWidthScaleType="fill", layoutHeightScaleType="fill",
                                      flexDirectionValue="column"),
               [top, spacer, bottom, dbox, stage_box])
    root.kids.insert(1, root_focus)
    root.kids.insert(2, E("SemanticData", role="group", label="Crux recap", name="Semantics",
                          kids=[bind(path("screenAnnouncement"), 984)]))
    return root, director, prev, pause, replay, cont, share, play_icon, pause_icon


def state(anim, x, y, actions=()):
    st = E("AnimationState", animationId=anim.id, x=x, y=y)
    st.add(list(actions))
    return st


def layer(name, entry_to, states):
    l = E("StateMachineLayer", name=name)
    l.add(E("AnyState", x=-200, y=-200), E("ExitState", x=-200, y=-300),
          E("EntryState", x=-200, y=0, kids=[transition(entry_to.id)]))
    l.add(states)
    return l


def key_input(key, mods=None):
    return E("KeyboardInput", keyType=key, keyPhase=1, modifiers=mods)


def artboard():
    root, director, prev, pause, replay, cont, share, play_icon, pause_icon = build()
    ab = E("Artboard", defaultStateMachineId=MAIN_SM, viewModelId=model.VM_ID, viewModelInstanceId=model.DEFAULT_INSTANCE,
           width=390, height=844, x=0, y=0, styleId="0:22", name="Crux Recap", id=MAIN_AB)
    ab.add(E("LayoutComponentStyle", name="Artboard Style", id="0:22"))
    ab.add(root)
    ev_screen = E("Event", name="screenChanged", kids=[
        E("CustomPropertyNumber", propertyValue=1, name="screen", kids=[bind(path("currentScreen"), 243)])])
    ev_finish = E("Event", name="recapFinished")
    ev_share = E("Event", name="shareTapped")
    ab.add(ev_screen, ev_finish, ev_share)

    blank = Anim("Blank", 1)
    ANIMS.append(blank)
    sm = E("StateMachine", name="Recap", id=MAIN_SM)

    # ---------------- listeners
    def control(target, trig, name, extra=()):
        return E("StateMachineListener", targetId=target.id, name=name, kids=[
            E("ListenerInputType", listenerTypeValue="click"),
            E("ListenerInputTypeSemantic", listenerTypeValue="semanticAction", kids=[E("SemanticInput", actionType="tap")]),
            E("ListenerInputTypeKeyboard", listenerTypeValue="keyboard", kids=[key_input("enter"), key_input("kpEnter")]),
            fire_trigger(path(trig))] + list(extra))
    sm.add(control(prev, "navPrev", "Previous"))
    sm.add(control(pause, "togglePause", "Pause / Play"))
    sm.add(control(replay, "replay", "Replay"))
    sm.add(control(cont, "navNext", "Continue"))
    sm.add(control(share, "shareRequested", "Share", [E("ListenerFireEvent", eventId=ev_share.id)]))
    for b, n in ((prev, 1), (pause, 2), (replay, 3), (cont, 4), (share, 5)):
        sm.add(E("StateMachineListener", targetId=b.id, name=f"{b.a['name']} Focus", kids=[
            E("ListenerInputType", listenerTypeValue="focus"), write_num(path("focusedControl"), n)]))
        sm.add(E("StateMachineListener", targetId=b.id, name=f"{b.a['name']} Blur", kids=[
            E("ListenerInputType", listenerTypeValue="blur"), write_num(path("focusedControl"), 0)]))
    for keys, trig, nm in ((["right", "pageDown"], "navNext", "Key Next"), (["left", "pageUp"], "navPrev", "Key Previous"),
                           (["space"], "togglePause", "Key Pause")):
        sm.add(E("StateMachineListener", targetId=root.id, name=nm, kids=[
            E("ListenerInputTypeKeyboard", listenerTypeValue="keyboard", kids=[key_input(k) for k in keys]),
            fire_trigger(path(trig))]))
    sm.add(E("StateMachineListener", targetId=root.id, name="Tab", kids=[
        E("ListenerInputTypeKeyboard", listenerTypeValue="keyboard", kids=[key_input("tab")]),
        E("FocusActionTraversal", traversalKind="next")]))
    sm.add(E("StateMachineListener", targetId=root.id, name="Shift Tab", kids=[
        E("ListenerInputTypeKeyboard", listenerTypeValue="keyboard", kids=[key_input("tab", 1)]),
        E("FocusActionTraversal", traversalKind="previous")]))

    # ---------------- layer: boot focus + screenChanged event
    ready = state(blank, 0, 0, [E("FocusActionTarget", targetId=director.id)])
    emit = state(blank, 260, 0, [E("StateMachineFireEvent", eventId=ev_screen.id, occursValue=0)])
    ready.add(transition(emit.id, [cond_trigger(path("screenSignal"))]))
    emit.add(transition(ready.id, [cond_trigger(path("screenSignal"))]))
    emit.add(transition(ready.id, []))
    sm.add(layer("Signals", ready, [ready, emit]))
    # ---------------- layer: recapFinished
    r2 = state(blank, 0, 0)
    e2 = state(blank, 260, 0, [E("StateMachineFireEvent", eventId=ev_finish.id, occursValue=0)])
    r2.add(transition(e2.id, [cond_trigger(path("finishSignal"))]))
    e2.add(transition(r2.id, []))
    sm.add(layer("Finish", r2, [r2, e2]))

    # ---------------- layer: chrome mode (intro / story / final)
    def mode_anim(name, final, first):
        a = Anim(name, 1)
        # displayValue: 0 = flex (shown), 1 = none (removed from layout, drawing and hit-testing)
        for b, show in ((cont, not final), (share, final), (pause, not final), (replay, final)):
            a.hold(b.kids[0].id, "displayValue", 0 if show else 1, kind="uint")
        a.hold(prev.id, "opacity", 0.35 if first else 1.0)
        ANIMS.append(a)
        return a
    a_first, a_story, a_final = mode_anim("Chrome Intro", False, True), mode_anim("Chrome Story", False, False), mode_anim("Chrome Final", True, False)
    s_first, s_story, s_final = state(a_first, 0, 0), state(a_story, 260, 0), state(a_final, 520, 0)
    cs = path("currentScreen")
    for s in (s_story, s_final):
        s.add(transition(s_first.id, [cond_num(cs, "equal", 1)], duration=200))
    for s in (s_first, s_story):
        s.add(transition(s_final.id, [cond_num(cs, "equal", 10)], duration=200))
    for s in (s_first, s_final):
        s.add(transition(s_story.id, [cond_num(cs, "greaterThan", 1), cond_num(cs, "lessThan", 10)], duration=200))
    sm.add(layer("Chrome", s_first, [s_first, s_story, s_final]))

    # ---------------- layer: pause glyph
    ap = Anim("Glyph Pause", 1)
    ap.hold(pause_icon.id, "opacity", 1.0).hold(play_icon.id, "opacity", 0.0)
    ay = Anim("Glyph Play", 1)
    ay.hold(pause_icon.id, "opacity", 0.0).hold(play_icon.id, "opacity", 1.0)
    ANIMS.extend([ap, ay])
    sp, sy = state(ap, 0, 0), state(ay, 260, 0)
    sp.add(transition(sy.id, [cond_bool(path("isPaused"), True)], duration=120))
    sy.add(transition(sp.id, [cond_bool(path("isPaused"), False)], duration=120))
    sm.add(layer("Pause Glyph", sp, [sp, sy]))

    ab.add(sm)
    for a in ANIMS:
        ab.add(a.el())
    return ab
