#!/usr/bin/env python3
"""Assembles scene.rml: chrome, controls, the sequencing state machine, listeners, view model, assets.

    cd apps/sprig/rive && python3 tools/sprig_main.py
"""
import os
from sprig_scenes2 import *  # noqa
from rml import _f  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

AB = ID()
SM = ID()
EV = {}


def event(name, payload=None):
    eid = ID()
    el = E("Event", name=name, id=eid)
    if payload is not None:
        el.add(E("CustomPropertyNumber", propertyValue=float(payload), name="index"))
    return eid, el


# ===================================================================== actions (listener bodies)

def set_num(name, v):
    return E("ListenerViewModelChange", E("BindablePropertyNumber", bind(P(name), 636, direction=True),
                                          propertyValue=float(v)))


def set_bool(name, v):
    return E("ListenerViewModelChange", E("BindablePropertyBoolean", bind(P(name), 634, direction=True),
                                          propertyValue=bool(v)))


def fire(name):
    return E("ListenerViewModelChange", E("BindablePropertyTrigger", bind(P(name), 686, direction=True),
                                          propertyValue=1))


def toggle(name):
    rid = ID()
    return E("ListenerViewModelChange",
             E("BindablePropertyBoolean", bind(P(name), 634, c_not(), id=rid), bind(P(name), 634, direction=True)),
             fromViewModelProperty=True, fromDataBindId=rid)


ACT = {
    "next": lambda: [set_num("_navDir", 1), fire("_navNext")],
    "prev": lambda: [set_num("_navDir", -1), fire("_navPrev")],
    "pause": lambda: [toggle("isPaused")],
    "share": lambda: [E("ListenerFireEvent", eventId=EV["shareTapped"])],
    "replay": lambda: [set_num("_navDir", -1), fire("_replay")],
}


def ptr(target, typ, actions, name):
    return E("StateMachineListenerSingle", *actions, targetId=target, listenerTypeValue=typ, name=name, id=ID())


def on_event(eid, actions, name):
    return E("StateMachineListener", E("ListenerInputTypeEvent", listenerTypeValue="event", eventId=eid), *actions,
             targetId=AB, name=name, id=ID())


def on_key(target, key, actions, name, mods=None):
    return E("StateMachineListener",
             E("ListenerInputTypeKeyboard", E("KeyboardInput", keyType=key, keyPhase=1, modifiers=mods),
               listenerTypeValue="keyboard"),
             *actions, targetId=target, name=name, id=ID())


def on_focus(target, idx, name):
    return E("StateMachineListener", E("ListenerInputType", listenerTypeValue="focus"),
             set_num("_focusIndex", idx), targetId=target, name=name, id=ID())

# ===================================================================== chrome


THEMED = []   # (solid colour id, dark-theme colour, light-theme colour)


def themed(dark, light, a=1.0, la=None):
    cid = ID()
    THEMED.append((cid, col(dark, a), col(light, la if la is not None else a)))
    return cid


def focus_ring(w, h, r, idx):
    conv = CV.add(("focus", idx), formula(f"Focused {idx}", [
        tV(1), tOp("-"), tF("min"), tV(1), tSep(), tO(), tIn(), tOp("-"), tV(idx), tC(), tOp("*"), tO(), tIn(),
        tOp("-"), tV(idx), tC(), tC()]))
    return shape("Focus ring", rect(w + 10, h + 10, r + 5), stroke(col(APRICOT), 2.5),
                 bind(P("_focusIndex"), 18, conv), op=0.0)


def semantic(label_prop, role="button"):
    return E("SemanticData", bind(P(label_prop), 983), role=role, label="", name="Semantics")


BTN = {}


def build_chrome():
    els = []
    # brand wordmark (small) + leaf mark
    wm = text("Wordmark", ["Sprig"], font="fr", size=26, color=CREAM, wght=620, soft=100, wonk=1, x=24, y=22,
              color_id=themed(CREAM, FOREST))
    mark, mp = leaf("Mark leaf", 99, 44, 15, 10, rot=0.7, light=LEAF, dark=LEAF_DARK, rib=None)
    year = text("Year", [("2026", P("year"), CV.group("yeartxt", [c_tostr()], "Year text"))], font="dm", size=12,
                color=CREAM, wght=600, ls=2.4, x=366, y=34, ox=1.0, color_id=themed(CREAM, FOREST, 0.85))
    # progress: exactly one segment per visible scene (hidden scenes collapse out of the flex row)
    row_st = lstyle(flexDirectionValue="row", gapHorizontal=5.0, gapHorizontalUnitsValue="points",
                    layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", positionTypeValue="absolute")
    segs = []
    for k in range(1, 11):
        fst = lstyle(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", widthUnitsValue="percent",
                     heightUnitsValue="percent", positionTypeValue="absolute", positionLeft=0.0, positionTop=0.0,
                     positionLeftUnitsValue="points", positionTopUnitsValue="points")
        if k < 10:
            conv = CV.add(("segfill", k), formula(f"Segment {k} fill %", [
                tF("max"), tV(0), tSep(), tF("min"), tV(1), tSep(), tIn(), tOp("-"), tV(k), tOp("+"),
                tV(bind_el=bind(P("screenProgress"), 777)), tC(), tC(), tOp("*"), tV(100)]))
        else:
            conv = CV.add(("segfill", k), formula("Summary segment fill %", [
                tF("max"), tV(0), tSep(), tF("min"), tV(1), tSep(), tIn(), tOp("-"), tV(9), tC(), tC(), tOp("*"),
                tV(100)]))
        fill_lc = E("LayoutComponent", fst, fill(col(APRICOT)), bind(P("currentScreen"), 7, conv),
                    width=0.0, height=100.0, styleId=fst.id, name="Fill", id=ID())
        sst = lstyle(layoutWidthScaleType="fill", layoutHeightScaleType="fill", cornerRadiusTL=1.5)
        if 1 < k < 10:
            sst.add(bind(P(f"showScreen{k}"), 596, c_show_display()))
        segs.append(E("LayoutComponent", sst, fill_lc,
                      E("Fill", solid(col(CREAM, 0.26), id=themed(CREAM, FOREST, 0.26, 0.18)), name="Track"),
                      width=10.0, height=3.0, styleId=sst.id, name=f"Segment {k}", id=ID()))
    prog_id = ID()
    progress = E("LayoutComponent", row_st, *segs, x=24.0, y=72.0, width=342.0, height=3.0, styleId=row_st.id,
                 name="Progress", id=prog_id)
    BTN["progress"] = prog_id

    # ---- controls (44x44+ targets)
    def circle_btn(name, x, idx, icon_kids, label_prop):
        hit = ID()
        n = node(name,
                 focus_ring(48, 48, 24, idx),
                 *icon_kids,
                 shape(f"{name} hit", ellipse(52, 52), fill(col(CREAM, 0.08), color_id=themed(CREAM, FOREST, 0.08, 0.07)),
                       stroke(col(CREAM, 0.55), 1.6, color_id=themed(CREAM, FOREST, 0.55, 0.5)),
                       E("FocusData", name="Focus"), semantic(label_prop), id=hit),
                 x=x, y=790, id=ID())
        return n, hit

    chev = shape("Chevron", *path_el("M5 -9 L-4 0 L5 9", closed=False),
                 stroke(col(CREAM), 2.6, color_id=themed(CREAM, FOREST)))
    prev_n, prev_hit = circle_btn("Previous", 48, 1, [chev], "previousLabel")
    pause_icon = node("Pause icon",
                      shape("Bar L", rect(4, 16, 2), fill(col(CREAM), color_id=themed(CREAM, FOREST)), x=-5),
                      shape("Bar R", rect(4, 16, 2), fill(col(CREAM), color_id=themed(CREAM, FOREST)), x=5),
                      bind(P("isPaused"), 18, CV.group("notb2n", [c_not(), c_b2n()], "Not as number")))
    play_icon = shape("Play icon", *path_el("M-5 -9 L9 0 L-5 9 Z"), fill(col(CREAM), color_id=themed(CREAM, FOREST)),
                      bind(P("isPaused"), 18, c_b2n()), x=1)
    pause_n, pause_hit = circle_btn("Pause", 342, 3, [pause_icon, play_icon], "pauseLabel")
    replay_icon = node("Replay icon",
                       shape("Arc", *path_el("M7 -6 C 3 -11 -6 -11 -9 -4 C -12 4 -5 11 2 10 C 6 9 8 7 9 4", closed=False),
                             stroke(col(CREAM), 2.4, color_id=themed(CREAM, FOREST))),
                       shape("Head", *path_el("M3 -10 L9 -6 L3 -1 Z"), fill(col(CREAM), color_id=themed(CREAM, FOREST))))
    replay_n, replay_hit = circle_btn("Replay", 342 + 2000, 5, [replay_icon], "replayLabel")

    def pill(name, x, idx, label_prop, icon):
        hit = ID()
        n = node(name,
                 focus_ring(176, 52, 26, idx),
                 text("Label", [("Continue", P(label_prop))], font="dm", size=16, color=FOREST, wght=600, x=-8, y=0,
                      ox=0.5, oy=0.5, wrap=False),
                 icon,
                 shape(f"{name} hit", rect(176, 52, 26), fill(col(APRICOT)),
                       fill(col(APRICOT_PALE, 0.6), feather=6), E("FocusData", name="Focus"),
                       semantic(label_prop), id=hit),
                 x=x, y=790, id=ID())
        return n, hit
    arrow = shape("Arrow", *path_el("M-6 0 L6 0 M1 -5 L6 0 L1 5", closed=False), stroke(col(FOREST), 2.2), x=62)
    cont_n, cont_hit = pill("Continue", 195, 2, "continueLabel", arrow)
    share_ic = shape("Share icon", *path_el("M0 4 L0 -7 M-5 -3 L0 -8 L5 -3", closed=False), stroke(col(FOREST), 2.2),
                     x=52)
    share_n, share_hit = pill("Share", 195 + 2000, 4, "shareLabel", share_ic)
    BTN.update(prev=(prev_n, prev_hit), pause=(pause_n, pause_hit), cont=(cont_n, cont_hit),
               share=(share_n, share_hit), replay=(replay_n, replay_hit))
    controls = node("Controls", prev_n, cont_n, share_n, pause_n, replay_n)
    els = [controls, progress, year, wm, mark]
    return node("Chrome", *els, id=ID())


def build_vine():
    """The single vine that carries the story: its growth follows currentScreen."""
    grow = CV.add("vinegrow", formula("Screen to vine growth", [tIn(), tOp("/"), tV(10)]))
    vi = CV.add(("interp", "vine"), lambda cid: E("DataConverterInterpolator",
                                                   E("CubicEaseInterpolator", x1=0.6, y1=0.0, x2=0.2, y2=1.0),
                                                   interpolationType="cubic", duration=0.9, name="Ease vine", id=cid))
    vconv = CV.group("vine", [grow, vi], "Vine growth")
    vt = ID()
    kids = [line("Vine stem", VINE_D, LEAF, 2.6, 0.95, trim_el=trim(0, 0.1, id=vt, bind=bind(P("currentScreen"), 115, vconv)))]
    for i in range(1, 10):
        f = i / 10.0 - 0.04
        (px, py), ang = point_at(VINE_D, f)
        side = 1 if i % 2 else -1
        lconv = CV.group(("vineleaf", i), [grow, vi, f_unit_clamp(f, 14.0, "Vine leaf")], f"Vine leaf {i}")
        n, p = leaf(f"Vine leaf {i}", px, py, 15, 10, rot=ang + math.pi / 2 + side * 1.0, light=LEAF, dark=LEAF_DARK,
                    rib=None)
        n.add(bind(P("currentScreen"), 16, lconv))
        n.add(bind(P("currentScreen"), 17, lconv))
        kids.append(n)
    return node("Story vine", *stack(*kids), id=ID())


def make_grain():
    path = os.path.join(PROJ, "assets", "images", "paper-grain.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        from PIL import Image
        import random
        rnd = random.Random(7)
        im = Image.new("LA", (W, H))
        px = im.load()
        for y in range(H):
            for x in range(W):
                v = rnd.randint(0, 255)
                a = int(abs(rnd.gauss(0, 1)) * 9)
                px[x, y] = (v, min(a, 30))
        im.save(path, optimize=True)
    except ImportError:
        print("Pillow missing: grain not generated", file=sys.stderr)
    return path

# ===================================================================== state machine


class Layer:
    def __init__(self, name):
        self.name = name
        self.id = ID()
        self.states = []
        self.entry = []
        self.any = []
        self.n = 0

    def state(self, anim_id, sid=None, reset=None, fire=None, focus=None, x=None, y=None):
        sid = sid or ID()
        i = len(self.states)
        st = E("AnimationState", animationId=anim_id, reset=reset, id=sid,
               x=float(x if x is not None else 200 + (i % 6) * 220), y=float(y if y is not None else (i // 6) * 160 - 80))
        if fire:
            st.add(E("StateMachineFireEvent", eventId=fire, occursValue=0))
        if focus:
            st.add(E("FocusActionTarget", targetId=focus))
        self.states.append(st)
        return sid, st

    def el(self):
        return E("StateMachineLayer",
                 E("AnyState", *self.any, x=0.0, y=-260.0),
                 E("ExitState", x=0.0, y=-360.0),
                 E("EntryState", *self.entry, x=0.0, y=0.0),
                 *self.states, name=self.name, id=self.id)


def paused_conds():
    return [cond_bool("isPaused", False), cond_bool("_holdPaused", False)]


def build_machine(scenes, card_anims):
    layers = []
    anims = []
    empty = Anim("Hold", 1)
    anims.append(empty)

    # ---- boot: give the keyboard surface focus so Left/Right/Space work without host help
    boot = Layer("Boot")
    sid, _ = boot.state(empty.id, focus=BTN["surface"])
    boot.entry.append(trans(sid, []))
    layers.append(boot)

    # ---- sequence: canonical scene IDs, skipping hidden scenes in both directions
    seq = Layer("Sequence")
    S = {k: ID() for k in range(1, 11)}
    st = {}
    for k in range(1, 11):
        _, st[k] = seq.state(empty.id, sid=S[k], fire=EV[f"screen{k}"], x=200 + (k - 1) * 200,
                             y=0 if k % 2 else 160)
    seq.entry.append(trans(S[1], []))
    eligible = lambda m: [] if m in (1, 10) else [cond_bool(f"showScreen{m}", True)]
    for n in range(1, 11):
        for m in range(n + 1, 11):
            conds = [cond_trig("_navNext")] + eligible(m) + [cond_bool(f"showScreen{j}", False) for j in range(n + 1, m)]
            st[n].add(trans(S[m], conds))
            if m in (1, 10) or True:
                if m == 10:
                    break
                # stop once we reach an always-eligible scene
        for m in range(n - 1, 0, -1):
            conds = [cond_trig("_navPrev")] + eligible(m) + [cond_bool(f"showScreen{j}", False) for j in range(m + 1, n)]
            st[n].add(trans(S[m], conds))
    seq.any.append(trans(S[1], [cond_trig("_replay")]))
    layers.append(seq)

    # ---- clock: dwell timer. Starts after the entrance settles, frozen while paused/held, variable duration
    clock = Layer("Dwell clock")
    probe = BTN["probe"]
    wait = Anim("Clock settle", 108)
    wait.key(probe, "x", [(0, 0.0, "hold")])
    steps = []
    for i in range(STEPS + 1):
        a = Anim(f"Clock {i}/{STEPS}", 1)
        a.key(probe, "x", [(0, i / STEPS, "hold")])
        steps.append(a)
    anims += [wait] + steps
    step_conv = CV.add("stepms", formula("Dwell step ms (clamped 3-60 s)", [
        tF("max"), tV(3), tSep(), tF("min"), tV(60), tSep(), tIn(), tC(), tC(), tOp("*"), tV(1000.0 / STEPS)]))
    W_id = ID()
    clock.state(wait.id, sid=W_id, reset=True, x=200, y=0)
    sids = [ID() for _ in range(STEPS + 1)]
    run = lambda: paused_conds() + [cond_bool("autoAdvanceEnabled", True), cond_num("currentScreen", 10, "notEqual")]
    durb = lambda: bind(P("autoAdvanceSeconds"), 158, step_conv)
    clock.entry.append(trans(W_id, []))
    for i in range(STEPS + 1):
        sid_, s_el = clock.state(steps[i].id, sid=sids[i], x=400 + (i % 10) * 160, y=(i // 10) * 160)
        if i < STEPS:
            reached = [cond_num("screenProgress", max(0.0, i / STEPS - 0.002), "greaterThanOrEqual")] if i else []
            s_el.add(trans(sids[i + 1], run() + reached, dur_bind=durb(), early=True))
        else:
            done_id = ID()
            s_el.add(trans(done_id, run() + [cond_num("screenProgress", 0.998, "greaterThanOrEqual")]))
            clock.state(steps[i].id, sid=done_id, fire=EV["_autoNext"], x=400, y=-200)
    clock.states[0].add(trans(sids[1], run(), exit_pct=100, dur_bind=durb(), early=True))
    # sids[0] unused as a target; first move goes W -> step 1 directly
    for trig in ("_navNext", "_navPrev", "_replay"):
        clock.any.append(trans(W_id, [cond_trig(trig)]))
    layers.append(clock)

    # ---- gesture: tap (left third back / right two-thirds next), hold pauses, release after hold is not a tap
    g = Layer("Gesture")
    press = Anim("Press", 21)
    held = Anim("Held", 12)
    held.key(BTN["progress"], "opacity", [(0, 1.0, "lin"), (10, 0.45)])
    rel = Anim("Released", 12)
    rel.key(BTN["progress"], "opacity", [(0, 0.45, "lin"), (10, 1.0)])
    anims += [press, held, rel]
    gI, gP, gTN, gTP, gH, gE = (ID() for _ in range(6))
    g.entry.append(trans(gI, []))
    _, e = g.state(empty.id, sid=gI, x=200, y=0)
    e.add(trans(gP, [cond_bool("_pressing", True)]))
    _, e = g.state(press.id, sid=gP, reset=True, x=420, y=0)
    e.add(trans(gTN, [cond_bool("_pressing", False), cond_num("_pressSide", 1)]))
    e.add(trans(gTP, [cond_bool("_pressing", False), cond_num("_pressSide", -1)]))
    e.add(trans(gI, [cond_bool("_pressing", False)]))
    e.add(trans(gH, [], exit_pct=100))
    _, e = g.state(empty.id, sid=gTN, fire=EV["_tapNext"], x=640, y=-120)
    e.add(trans(gI, [], exit_pct=100))
    _, e = g.state(empty.id, sid=gTP, fire=EV["_tapPrev"], x=640, y=120)
    e.add(trans(gI, [], exit_pct=100))
    _, e = g.state(held.id, sid=gH, fire=EV["_holdOn"], x=420, y=200)
    e.add(trans(gE, [cond_bool("_pressing", False)]))
    _, e = g.state(rel.id, sid=gE, fire=EV["_holdOff"], x=200, y=200)
    e.add(trans(gI, [], exit_pct=100))
    layers.append(g)

    # ---- finish latch: recapFinished fires once when the summary first settles; replay re-arms it
    fin = Layer("Finish latch")
    settle = Anim("Summary settle", 110)
    anims.append(settle)
    f0, f1, f2 = ID(), ID(), ID()
    fin.entry.append(trans(f0, []))
    _, e = fin.state(empty.id, sid=f0, x=200, y=0)
    e.add(trans(f1, [cond_num("currentScreen", 10)]))
    _, e = fin.state(settle.id, sid=f1, reset=True, x=420, y=0)
    e.add(trans(f0, [cond_num("currentScreen", 10, "notEqual")]))
    e.add(trans(f2, [], exit_pct=100))
    _, e = fin.state(empty.id, sid=f2, fire=EV["recapFinished"], x=640, y=0)
    fin.any.append(trans(f0, [cond_trig("_replay")]))
    layers.append(fin)

    # ---- theme: chrome ink follows the scene's paper (dark forest vs light cream/leaf)
    th = Layer("Chrome theme")
    dark, light = Anim("Theme dark", 1), Anim("Theme light", 1)
    for cid, dc, lc in THEMED:
        dark.key(cid, "colorValue", [(0, dc, "hold")])
        light.key(cid, "colorValue", [(0, lc, "hold")])
    anims += [dark, light]
    tD, tL = ID(), ID()
    th.entry.append(trans(tD, []))
    _, e = th.state(dark.id, sid=tD, x=200, y=0)
    for v in (4, 6, 7, 10):
        e.add(trans(tL, [cond_num("currentScreen", v)], dur=420, interp="io"))
    _, e = th.state(light.id, sid=tL, x=420, y=0)
    e.add(trans(tD, [cond_num("currentScreen", v, "notEqual") for v in (4, 6, 7, 10)], dur=420, interp="io"))
    layers.append(th)

    # ---- controls: Continue/Pause become Share/Replay on the summary (inactive hit regions move off-canvas)
    ct = Layer("Controls")
    cN, cS = Anim("Controls story", 14), Anim("Controls summary", 14)
    for a, on, off in ((cN, ("cont", "pause"), ("share", "replay")), (cS, ("share", "replay"), ("cont", "pause"))):
        for nm in on:
            nd = BTN[nm][0]
            x0 = 195 if nm in ("cont", "share") else 342
            a.key(nd.id, "x", [(0, x0, "hold")])
            a.key(nd.id, "opacity", [(0, 0.0, "outs"), (12, 1.0)])
            a.key(nd.id, "scaleX", [(0, 0.85, "back"), (12, 1.0)])
            a.key(nd.id, "scaleY", [(0, 0.85, "back"), (12, 1.0)])
        for nm in off:
            nd = BTN[nm][0]
            x0 = 195 if nm in ("cont", "share") else 342
            a.key(nd.id, "x", [(0, x0 + 2000, "hold")])
            a.key(nd.id, "opacity", [(0, 0.0, "hold")])
    anims += [cN, cS]
    c1, c2 = ID(), ID()
    ct.entry.append(trans(c1, []))
    _, e = ct.state(cN.id, sid=c1, x=200, y=0)
    e.add(trans(c2, [cond_num("currentScreen", 10)]))
    _, e = ct.state(cS.id, sid=c2, x=420, y=0)
    e.add(trans(c1, [cond_num("currentScreen", 10, "notEqual")]))
    layers.append(ct)

    # ---- signature interaction: hold the hero leaf, it bends toward the pointer, release settles with overshoot
    lb = Layer("Leaf bend")
    sc1 = scenes[1]
    rest = Anim("Leaf rest", 1)
    rest.key(sc1.leaf_handle, "x", [(0, 268.0, "hold")])
    rest.key(sc1.leaf_handle, "y", [(0, 572.0, "hold")])
    anims.append(rest)
    r1, r2 = ID(), ID()
    lb.entry.append(trans(r1, []))
    _, e = lb.state(rest.id, sid=r1, x=200, y=0)
    e.add(trans(r2, [cond_bool("_leafHeld", True)]))
    _, e = lb.state(empty.id, sid=r2, x=420, y=0)
    e.add(trans(r1, [cond_bool("_leafHeld", False)], dur=1100, interp="elastic", early=True))
    layers.append(lb)

    # ---- persona: unique choreography per persona; unknown index falls back to row 0
    pl = Layer("Persona")
    pa = scenes[9].persona
    anims += pa.enter + pa.idle + pa.final
    p_hide = Anim("Persona hidden", 1)
    for gid in pa.groups:
        p_hide.key(gid, "opacity", [(0, 0.0, "hold")])
    p_leave = Anim("Persona leaving", 50)
    anims += [p_hide, p_leave]
    PH, PL = ID(), ID()
    PE = [ID() for _ in range(4)]
    PI = [ID() for _ in range(4)]
    PZ = [ID() for _ in range(4)]
    PR = [ID() for _ in range(4)]

    def idx_conds(k):
        if k == 0:
            return [cond_num("personaIndex", v, "notEqual") for v in (1, 2, 3)]
        return [cond_num("personaIndex", k)]

    def enter_set(e, include_static_only=False):
        for k in (1, 2, 3, 0):
            e.add(trans(PR[k], [cond_num("currentScreen", 9), cond_bool("reducedMotion", True)] + idx_conds(k)))
        if not include_static_only:
            for k in (1, 2, 3, 0):
                e.add(trans(PE[k], [cond_num("currentScreen", 9)] + idx_conds(k)))

    pl.entry.append(trans(PH, []))
    _, e = pl.state(p_hide.id, sid=PH, x=200, y=0)
    enter_set(e)
    _, e = pl.state(p_leave.id, sid=PL, x=200, y=300)
    enter_set(e)
    e.add(trans(PH, [], exit_pct=100))
    for k in range(4):
        def swaps(e, k=k):
            e.add(trans(PL, [cond_num("currentScreen", 9, "notEqual")]))
            for j in (1, 2, 3, 0):
                if j != k:
                    e.add(trans(PR[j], idx_conds(j)))
        _, e = pl.state(pa.enter[k].id, sid=PE[k], reset=True, x=440, y=-240 + k * 160)
        swaps(e)
        e.add(trans(PI[k], [], exit_pct=100))
        _, e = pl.state(pa.idle[k].id, sid=PI[k], x=680, y=-240 + k * 160)
        swaps(e)
        for c in (cond_bool("isPaused", True), cond_bool("_holdPaused", True), cond_bool("reducedMotion", True)):
            e.add(trans(PZ[k], [c]))
        _, e = pl.state(empty.id, sid=PZ[k], x=920, y=-240 + k * 160)
        swaps(e)
        e.add(trans(PI[k], paused_conds() + [cond_bool("reducedMotion", False)]))
        _, e = pl.state(pa.final[k].id, sid=PR[k], reset=True, x=1160, y=-240 + k * 160)
        swaps(e)
        e.add(trans(PZ[k], [], exit_pct=100))
    layers.append(pl)

    # ---- one layer per scene: hidden / enter (forward wipe, reverse arrival, reduced) / idle / frozen / leave
    for k in range(10, 0, -1):
        sc = scenes[k]
        A = sc.anims
        if k == 1:
            A["EB"] = A["EF"]
        anims += [A[n] for n in ("H", "EF", "EB", "ER", "I", "LF", "LB", "LR") if not (k == 1 and n == "EB")]
        L = Layer(f"Scene {k}")
        ids = {n: ID() for n in ("H", "EF", "EB", "ER", "I", "Z", "LF", "LB", "LR")}
        here = lambda: cond_num("currentScreen", k)
        away = lambda: cond_num("currentScreen", k, "notEqual")
        rm = lambda v=True: cond_bool("reducedMotion", v)

        def leaves(e):
            e.add(trans(ids["LR"], [away(), rm()]))
            e.add(trans(ids["LF"], [cond_num("currentScreen", k, "greaterThan")]))
            e.add(trans(ids["LB"], [cond_num("currentScreen", k, "lessThan")]))

        L.entry.append(trans(ids["H"], []))
        pos = {"H": (200, 0), "EF": (440, -160), "EB": (440, 0), "ER": (440, 160), "I": (700, -80), "Z": (700, 120),
               "LF": (960, -160), "LB": (960, 0), "LR": (960, 160)}
        anim_for = {"H": A["H"].id, "EF": A["EF"].id, "EB": A["EB"].id, "ER": A["ER"].id, "I": A["I"].id,
                    "Z": empty.id, "LF": A["LF"].id, "LB": A["LB"].id, "LR": A["LR"].id}
        E_ = {}
        for n in ids:
            _, E_[n] = L.state(anim_for[n], sid=ids[n], reset=True if n not in ("I", "Z") else None,
                               x=pos[n][0], y=pos[n][1])
        E_["H"].add(trans(ids["ER"], [here(), rm()]))
        E_["H"].add(trans(ids["EF"], [here(), cond_num("_navDir", 0, "greaterThanOrEqual")]))
        E_["H"].add(trans(ids["EB"], [here()]))
        for n in ("EF", "EB", "ER"):
            leaves(E_[n])
            E_[n].add(trans(ids["I"], paused_conds() + [rm(False)], exit_pct=100))
            E_[n].add(trans(ids["Z"], [], exit_pct=100))
        leaves(E_["I"])
        for c in (cond_bool("isPaused", True), cond_bool("_holdPaused", True), rm()):
            E_["I"].add(trans(ids["Z"], [c]))
        leaves(E_["Z"])
        E_["Z"].add(trans(ids["I"], paused_conds() + [rm(False)]))
        for n, back_to in (("LF", "EB"), ("LB", "EF"), ("LR", "ER")):
            E_[n].add(trans(ids["ER"], [here(), rm()]))
            E_[n].add(trans(ids[back_to], [here()]))
            E_[n].add(trans(ids["H"], [], exit_pct=100))
        layers.append(L)

    sm = E("StateMachine", *[l.el() for l in layers], name="Recap", id=SM)
    return sm, anims


def build_listeners():
    out = []
    tp, tn = BTN["tapPrev"], BTN["tapNext"]
    out.append(ptr(tp, "down", [set_num("_pressSide", -1), set_bool("_pressing", True)], "Back region press"))
    out.append(ptr(tn, "down", [set_num("_pressSide", 1), set_bool("_pressing", True)], "Next region press"))
    for t, nm in ((tp, "Back"), (tn, "Next")):
        out.append(ptr(t, "up", [set_bool("_pressing", False)], f"{nm} region release"))
        out.append(ptr(t, "exit", [set_bool("_pressing", False)], f"{nm} region leave"))
    out.append(on_event(EV["_tapNext"], ACT["next"](), "Tap -> next"))
    out.append(on_event(EV["_tapPrev"], ACT["prev"](), "Tap -> previous"))
    out.append(on_event(EV["_holdOn"], [set_bool("_holdPaused", True)], "Hold -> pause"))
    out.append(on_event(EV["_holdOff"], [set_bool("_holdPaused", False)], "Release -> resume"))
    out.append(on_event(EV["_autoNext"], ACT["next"](), "Dwell elapsed -> next"))
    for k in range(1, 11):
        out.append(on_event(EV[f"screen{k}"], [set_num("currentScreen", k)], f"Scene {k} is current"))
    for nm, act in (("prev", "prev"), ("cont", "next"), ("pause", "pause"), ("share", "share"), ("replay", "replay")):
        hit = BTN[nm][1]
        out.append(ptr(hit, "click", ACT[act](), f"{nm} button"))
        out.append(on_key(hit, "enter", ACT[act](), f"{nm} Enter"))
    focusables = [("surface", 0), ("prev", 1), ("cont", 2), ("pause", 3), ("share", 4), ("replay", 5)]
    for nm, idx in focusables:
        t = BTN["surface"] if nm == "surface" else BTN[nm][1]
        out.append(on_key(t, "right", ACT["next"](), f"{nm} Right"))
        out.append(on_key(t, "left", ACT["prev"](), f"{nm} Left"))
        out.append(on_key(t, "space", ACT["pause"](), f"{nm} Space"))
        out.append(on_key(t, "tab", [E("FocusActionTraversal", traversalKind="next")], f"{nm} Tab", mods=None))
        out.append(on_key(t, "tab", [E("FocusActionTraversal", traversalKind="previous")], f"{nm} Shift+Tab", mods=1))
        out.append(on_focus(t, idx, f"{nm} focused"))
    # signature interaction
    sc1 = SC[1]
    out.append(ptr(sc1.leaf_hit, "down", [set_bool("_leafHeld", True)], "Leaf hold"))
    out.append(ptr(sc1.leaf_hit, "up", [set_bool("_leafHeld", False)], "Leaf release"))
    out.append(ptr(sc1.leaf_hit, "exit", [set_bool("_leafHeld", False)], "Leaf leave"))
    out.append(ptr(sc1.leaf_hit, "drag", [E("ListenerAlignTarget", targetId=sc1.leaf_handle, preserveOffset=True)],
                   "Leaf drag"))
    return out


def vm_el():
    vm = E("ViewModel", name="UserRecap", id=VMID, defaultInstanceId=None)
    for n in VM_ORDER:
        pid, t, d = PROPS[n]
        tag = {"string": "ViewModelPropertyString", "number": "ViewModelPropertyNumber",
               "bool": "ViewModelPropertyBoolean", "color": "ViewModelPropertyColor",
               "trigger": "ViewModelPropertyTrigger"}[t]
        vm.add(E(tag, name=n, id=pid))
    inst_ids = {}
    for fname, over in FIXTURES.items():
        iid = ID()
        inst_ids[fname] = iid
        inst = E("ViewModelInstance", exports=True, name=fname, id=iid)
        for n in VM_ORDER:
            pid, t, d = PROPS[n]
            v = over.get(n, d)
            if t == "trigger":
                inst.add(E("ViewModelInstanceTrigger", viewModelPropertyId=pid))
                continue
            tag = {"string": "ViewModelInstanceString", "number": "ViewModelInstanceNumber",
                   "bool": "ViewModelInstanceBoolean", "color": "ViewModelInstanceColor"}[t]
            if t == "number":
                v = float(v)
            inst.add(E(tag, propertyValue=v, viewModelPropertyId=pid))
        vm.add(inst)
    vm.attrs["defaultInstanceId"] = inst_ids[os.environ.get("SPRIG_FIXTURE", "Sample")]
    return vm, inst_ids


SC = {}


def main():
    global SC
    sc1, r1 = scene1()
    sc2, r2 = scene2()
    sc3, r3 = scene3()
    sc4, r4 = scene4()
    sc5, r5 = scene5()
    sc6, r6 = scene6()
    sc7, r7 = scene7()
    sc8, r8 = scene8()
    sc9, r9 = scene9()
    card_el, card_asset, card_ab, card_sm = share_card()
    sc10, r10 = scene10(card_ab, card_sm)
    SC = {1: sc1, 2: sc2, 3: sc3, 4: sc4, 5: sc5, 6: sc6, 7: sc7, 8: sc8, 9: sc9, 10: sc10}
    for sc in SC.values():
        scene_derive(sc)
    # scene 1 has no wipe; its idle starts after the intro
    for k in range(1, 11):
        EV[f"screen{k}"], _ = None, None
    events = []
    for k in range(1, 11):
        eid, el = event("screenChanged", k)
        EV[f"screen{k}"] = eid
        events.append(el)
    for n in ("recapFinished", "shareTapped", "_autoNext", "_tapNext", "_tapPrev", "_holdOn", "_holdOff"):
        eid, el = event(n)
        EV[n] = eid
        events.append(el)

    chrome = build_chrome()
    vine = build_vine()
    grain_path = make_grain()
    grain_asset = ID()
    grain = E("Image", assetId=grain_asset, x=195.0, y=422.0, originX=0.5, originY=0.5, opacity=0.55,
              blendModeValue="overlay", name="Paper grain", id=ID())
    probe = ID()
    BTN["probe"] = probe
    probe_el = node("Progress probe", bind(P("screenProgress"), 13, two_way=True), id=probe)
    surface = ID()
    BTN["surface"] = surface
    surface_el = shape("Keyboard surface", rect(W, H), E("FocusData", name="Focus"), x=195, y=422, id=surface)
    tap_prev, tap_next = ID(), ID()
    BTN["tapPrev"], BTN["tapNext"] = tap_prev, tap_next
    taps = [shape("Tap back region", rect(130, 656), fill(col("#000000", 0.0)), x=65, y=424, id=tap_prev),
            shape("Tap next region", rect(260, 656), fill(col("#000000", 0.0)), x=260, y=424, id=tap_next)]
    # joystick for the bendable hero leaf
    bendx, bendy = Anim("Leaf bend X", 60), Anim("Leaf bend Y", 60)
    hb = sc1.hero_bend
    bendx.key(hb, "rotation", [(0, 0.78 - 0.42, "lin"), (30, 0.78, "lin"), (60, 0.78 + 0.34)])
    bendy.key(hb, "scaleY", [(0, 1.12, "lin"), (30, 1.0, "lin"), (60, 0.9)])
    bendy.key(hb, "scaleX", [(0, 0.94, "lin"), (30, 1.0, "lin"), (60, 1.06)])
    joy = E("Joystick", posX=268.0, posY=572.0, width=260.0, height=260.0, xId=bendx.id, yId=bendy.id,
            handleSourceId=sc1.leaf_handle, name="Leaf bend joystick", id=ID())

    sm, anims = build_machine(SC, None)
    listeners = build_listeners()
    sm.kids = listeners + sm.kids
    vm, inst_ids = vm_el()

    style = E("LayoutComponentStyle", name="Artboard style", id=ID())
    roots = [r10, r9, r8, r7, r6, r5, r4, r3, r2, r1]
    art = E("Artboard", style, sm,
            surface_el, chrome, vine, grain, *roots, *taps, probe_el, joy, *events,
            *[a.el() for a in anims], bendx.el(), bendy.el(),
            defaultStateMachineId=SM, viewModelId=VMID, viewModelInstanceId=inst_ids["Sample"], clip=True,
            width=float(W), height=float(H), styleId=style.id, name="SprigRecap", id=AB, x=0.0, y=0.0)
    doc = E("Rive", art, card_el, card_asset,
            E("FontAsset", file="assets/fonts/Fraunces-Variable.ttf", name="Fraunces", id=FONT_FR),
            E("FontAsset", file="assets/fonts/DMSans-Variable.ttf", name="DM Sans", id=FONT_DM),
            E("ImageAsset", file=os.path.relpath(grain_path, PROJ), name="paper-grain", id=grain_asset),
            *CV.items, vm, version="1", kind="fragment")
    out = os.path.join(PROJ, "scene.rml")
    with open(out, "w") as f:
        f.write("<!-- Generated by tools/sprig_main.py. Sprig 2026 recap. -->\n")
        f.write("\n".join(render(doc)) + "\n")
    print("wrote", out, "ids up to", ID.n)


if __name__ == "__main__":
    main()
