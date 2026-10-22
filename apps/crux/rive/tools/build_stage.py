"""Animations + state machine for the Stage artboard."""
from rml import (E, nid, Anim, cond_num, cond_bool, cond_trigger, write_num, write_bool, transition,
                 CHALK, COAL)
from art import BASE
import stage
from stage import (CARRIER, CARRIER_FLY, ROPE, CLOUD, HERO_DRIVER, CARRIER_POSE, CONTINUITY, IN_DUR, rope_bow,
                   STAGE_AB, STAGE_SM, W, H, CHALK_IN, CARRIER_YAW, CARRIER_PITCH, ENTRY_YAW)
from art import LIVE
import model
from model import path, rig_path
from rml import bind

SCENES = stage.all_scenes()
BY_K = {s.k: s for s in SCENES}

ANIMS = []
YAW_OUT = 6.2832     # a full turn: the carrier spins once as it is yanked and lands face-on
TILT = {"back": 0.0, "mid": 0.035, "front": 0.07, "text": 0.02}   # camera swing per parallax layer


def chalk_burst(a, k, x, y, direction, dur):
    """Exit: the chalk shader blooms from the yank point and occludes the cut."""
    c = CHALK_IN
    a.k(c["originX"], 243, 0, float(x))
    a.k(c["originY"], 243, 0, float(y))
    a.k(c["seed"], 243, 0, round(1.7 + k * 1.37, 3))
    a.k(c["direction"], 243, 0, float(direction))
    a.k(c["clear"], 243, 0, 0.0)
    a.k(c["amount"], 243, 0, 0.0)
    a.k(c["amount"], 243, 8, 0.0, "out")
    a.k(c["amount"], 243, 14, 0.16, "inout")
    a.k(c["amount"], 243, dur - 3, 0.58)
    a.k(c["drift"], 243, 0, 0.0, "in")
    a.k(c["drift"], 243, dur, 150.0)


def chalk_clear(a):
    """Entrance: the cloud keeps drifting and thins out from its edges."""
    c = CHALK_IN
    a.k(c["amount"], 243, 0, 0.58)
    a.k(c["amount"], 243, 26, 0.58)
    a.k(c["amount"], 243, 27, 0.0)
    a.k(c["clear"], 243, 0, 0.0, "outq")
    a.k(c["clear"], 243, 26, 1.5)
    a.k(c["drift"], 243, 0, 150.0, "out")
    a.k(c["drift"], 243, 26, 280.0)


def chalk_off(a):
    a.hold(CHALK_IN["amount"], 243, 0.0)
    a.hold(CHALK_IN["clear"], 243, 0.0)


def live_keys(a, sc):
    for o in SCENES:
        for lid in LIVE.get(o.k, []):
            a.hold(lid, 243, 1.0 if o is sc else 0.0)


LAYERS = [("back", 150, 24, "out"), ("mid", 240, 26, "out"), ("front", 360, 30, "back"), ("text", 200, 22, "out")]


def carrier_set(a, f, x, y, s, r, ease="hold"):
    a.k(CARRIER.id, "x", f, x, ease)
    a.k(CARRIER.id, "y", f, y, ease)
    a.k(CARRIER.id, "scaleX", f, s, ease)
    a.k(CARRIER.id, "scaleY", f, s, ease)
    a.k(CARRIER.id, "rotation", f, r, ease)


def variant_cond(sc, v):
    if sc.k == 9:
        return [cond_num(path("personaSlot"), "equal", v)]
    if sc.k == 10:
        return [cond_bool(path("isEmptyRecap"), v == 1)]
    return []


def build_in(sc, v, mode):
    tag = f"{sc.k}" + (f"v{v}" if len(sc.variants) > 1 else "")
    a = Anim(f"Scene {tag} In {mode}", IN_DUR)
    for o in SCENES:
        a.hold(o.root.id, "opacity", 1.0 if o is sc else 0.0)
    sign = 1 if mode == "F" else -1
    live_keys(a, sc)
    for attr, off, f1, ease in LAYERS:
        a.tw(getattr(sc, attr).id, "y", 0, f1, sign * off, 0.0, ease)
        a.tw(getattr(sc, attr).id, "rotation", 0, f1 + 6, -sign * TILT[attr], 0.0, "back")
    stage.ENTRY_YAW[0] = 0.0
    # carrier hand-off. A continuity entrance starts where the previous exit left the
    # hold; any other flies in from off-canvas on `Carrier Fly` (viewport units).
    px, py, ps, pr = CARRIER_POSE[sc.k]
    fly0 = 0.0
    if mode == "F" and (sc.k - 1) in CONTINUITY:
        sx, sy, ss = CONTINUITY[sc.k - 1]
        sr = CARRIER_POSE[sc.k - 1][3]
    else:
        sx, sy, ss, sr = px, py, ps, pr + 0.6 * sign
        fly0 = sign * 760.0
    a.k(CARRIER_FLY.id, "y", 0, fly0)
    if sc.carrier_hook:
        sc.carrier_hook(a, sx, sy, ss, sr, fly0)
    else:
        # the hold keeps turning from the yank and lands square on the wall
        a.k(CARRIER_PITCH, 243, 0, 0.0)
        t0_, t1_ = getattr(sc, "carrier_t", (0, 26))
        a.k(CARRIER_YAW, 243, 0, 0.0)
        a.k(CARRIER_YAW, 243, t0_, 0.0, "inout")
        a.k(CARRIER_YAW, 243, (t0_ + t1_) // 2 + 2, -0.55 * sign, "inout")
        a.k(CARRIER_YAW, 243, t1_ + 10, 0.0)
        t0, t1 = getattr(sc, "carrier_t", (0, 26))
        carrier_set(a, 0, sx, sy, ss, sr)
        a.k(CARRIER.id, "x", t0, sx, "inout")
        a.k(CARRIER.id, "y", t0, sy, "back")
        a.k(CARRIER_FLY.id, "y", t0, fly0, "back")
        a.k(CARRIER_FLY.id, "y", t1, 0.0)
        a.k(CARRIER.id, "rotation", t0, sr, "back")
        a.k(CARRIER.id, "scaleX", t0, ss, "out")
        a.k(CARRIER.id, "scaleY", t0, ss, "out")
        carrier_set(a, t1, px, py, ps, pr)
    # chalk occluder thins out, rope releases
    chalk_clear(a)
    a.tw(ROPE.id, "opacity", 0, 12, 1.0, 0.0, "linear")
    a.tw(rope_bow.id, "x", 0, 14, 0.0, 60.0, "out")
    # hero count driver (bound to UserRecap.heroProgress)
    for f, val, ease in sc.hero_steps:
        a.k(HERO_DRIVER.id, 243, f, val, ease)
    sc.choreo(a, v)
    return a


def build_reduced(sc, v, full):
    tag = f"{sc.k}" + (f"v{v}" if len(sc.variants) > 1 else "")
    a = Anim(f"Scene {tag} In Reduced", 14)
    for (obj, prop), (val, kind) in full.final_values().items():
        a.hold(obj, prop, val, kind=kind)
    a.tw(sc.root.id, "opacity", 0, 12, 0.0, 1.0, "linear")
    chalk_off(a)
    a.hold(ROPE.id, "opacity", 0.0)
    a.hold(HERO_DRIVER.id, 243, 1.0)
    a.hold(CARRIER_YAW, 243, 0.0)
    a.hold(CARRIER_PITCH, 243, 0.0)
    for attr, *_ in LAYERS:
        a.hold(getattr(sc, attr).id, "y", 0.0)
        a.hold(getattr(sc, attr).id, "rotation", 0.0)
    return a


def build_exit(sc, mode):
    k = sc.k
    px, py, ps, pr = CARRIER_POSE[k]
    if mode == "R":
        a = Anim(f"Scene {k} Out Reduced", 10)
        a.tw(sc.root.id, "opacity", 0, 9, 1.0, 0.0, "linear")
        a.hold(CARRIER_FLY.id, "y", 0.0)
        chalk_off(a)
        a.hold(ROPE.id, "opacity", 0.0)
        a.hold(HERO_DRIVER.id, 243, 1.0)
        a.tw(CARRIER.id, "scaleX", 0, 9, ps, 0.0, "linear")
        a.tw(CARRIER.id, "scaleY", 0, 9, ps, 0.0, "linear")
        return a
    if mode == "F":
        # Signature transition: a taut route line yanks the wall panel upward; chalk occludes the cut.
        a = Anim(f"Scene {k} Out Yank", 38)
        dests = {"back": -520, "mid": -860, "front": -1060, "text": -940}
        ants = {"back": 6, "mid": 10, "front": 16, "text": 8}
        for attr, *_ in LAYERS:
            lid = getattr(sc, attr).id
            a.k(lid, "y", 0, 0.0, "out")
            a.k(lid, "y", 8, ants[attr], "in")
            a.k(lid, "y", 34, dests[attr])
            a.k(lid, "rotation", 0, 0.0, "out")
            a.k(lid, "rotation", 8, -TILT[attr] * 0.3, "in")
            a.k(lid, "rotation", 34, TILT[attr])
        a.k(ROPE.id, "opacity", 0, 0.0, "linear")
        a.k(ROPE.id, "opacity", 5, 1.0)
        a.k(rope_bow.id, "x", 0, 60.0, "snap")
        a.k(rope_bow.id, "x", 9, 0.0)
        # the hold twists against the load, then spins as it is ripped upward
        a.k(CARRIER_PITCH, 243, 0, 0.0, "out")
        a.k(CARRIER_PITCH, 243, 8, 0.5, "in")
        a.k(CARRIER_PITCH, 243, 34, 0.0)
        a.k(CARRIER_YAW, 243, 0, 0.0, "out")
        a.k(CARRIER_YAW, 243, 8, -0.35, "in")
        a.k(CARRIER_YAW, 243, 34, YAW_OUT)
        chalk_burst(a, k, px, py, 1, 38)
        carrier_set(a, 0, px, py, ps, pr)
        a.k(CARRIER.id, "y", 0, py, "out")
        a.k(CARRIER.id, "y", 8, py + 12, "in")
        a.k(CARRIER_FLY.id, "y", 0, 0.0)
        if k in CONTINUITY:
            mx, my, ms = CONTINUITY[k]
            a.k(CARRIER.id, "x", 8, px, "inout")
            a.k(CARRIER.id, "scaleX", 8, ps, "back")
            a.k(CARRIER.id, "scaleY", 8, ps, "back")
            carrier_set(a, 34, mx, my, ms, pr)
            a.k(CARRIER.id, "y", 8, py + 12, "inout")
        else:
            a.k(CARRIER_FLY.id, "y", 8, 0.0, "in")
            a.k(CARRIER_FLY.id, "y", 34, -1050.0)
        a.k(sc.root.id, "opacity", 0, 1.0)
        a.k(sc.root.id, "opacity", 37, 1.0)
        a.k(sc.root.id, "opacity", 38, 0.0)
        dur = 38
    else:
        # Reverse: a controlled lower-off - the rope goes slack and the panel drops away.
        a = Anim(f"Scene {k} Out Lower", 40)
        dests = {"back": 440, "mid": 720, "front": 920, "text": 780}
        for attr, *_ in LAYERS:
            lid = getattr(sc, attr).id
            a.k(lid, "y", 0, 0.0, "out")
            a.k(lid, "y", 7, -12.0, "in")
            a.k(lid, "y", 36, dests[attr])
            a.k(lid, "rotation", 0, 0.0, "in")
            a.k(lid, "rotation", 36, -TILT[attr])
        a.k(CARRIER_PITCH, 243, 0, 0.0, "in")
        a.k(CARRIER_PITCH, 243, 36, -0.6)
        a.k(CARRIER_YAW, 243, 0, 0.0, "in")
        a.k(CARRIER_YAW, 243, 36, -YAW_OUT)
        chalk_burst(a, k, px, py, -1, 40)
        a.k(ROPE.id, "opacity", 0, 0.0, "linear")
        a.k(ROPE.id, "opacity", 5, 1.0)
        a.k(rope_bow.id, "x", 0, 0.0, "out")
        a.k(rope_bow.id, "x", 22, 140.0)
        carrier_set(a, 0, px, py, ps, pr)
        a.k(CARRIER.id, "y", 0, py, "out")
        a.k(CARRIER.id, "y", 7, py - 16)
        a.k(CARRIER_FLY.id, "y", 0, 0.0)
        a.k(CARRIER_FLY.id, "y", 7, 0.0, "in")
        a.k(CARRIER_FLY.id, "y", 36, 1000.0)
        a.k(CARRIER.id, "rotation", 0, pr, "in")
        a.k(CARRIER.id, "rotation", 36, pr - 0.8)
        a.k(sc.root.id, "opacity", 0, 1.0)
        a.k(sc.root.id, "opacity", 39, 1.0)
        a.k(sc.root.id, "opacity", 40, 0.0)
        dur = 40
    a.hold(HERO_DRIVER.id, 243, 1.0)
    return a


# ------------------------------------------------------------------ idle loops
def build_idle(sc):
    a = Anim(f"Scene {sc.k} Idle", 240, loop="loop")
    for i, (nid_, prop, amp) in enumerate(sc.idle):
        if amp == 0:
            a.k(nid_, prop, 0, 0.0, "linear")
            a.k(nid_, prop, 240, 6.2831853 * 0.02)
            continue
        ph = (i * 37) % 120
        a.k(nid_, prop, 0, 0.0, "inout")
        a.k(nid_, prop, 60 + ph // 4, amp, "inout")
        a.k(nid_, prop, 180 - ph // 4, -amp * 0.7, "inout")
        a.k(nid_, prop, 240, 0.0)
    # carrier breathes everywhere (seamless: returns to 0)
    a.k(stage.CARRIER_ART.id, "rotation", 0, 0.0, "inout")
    a.k(stage.CARRIER_ART.id, "rotation", 120, 0.06, "inout")
    a.k(stage.CARRIER_ART.id, "rotation", 240, 0.0)
    return a


def build_idle_rest():
    a = Anim("Idle Rest", 1)
    for sc in SCENES:
        for nid_, prop, amp in sc.idle:
            a.hold(nid_, prop, 0.0)
    a.hold(stage.CARRIER_ART.id, "rotation", 0.0)
    return a


# ------------------------------------------------------------------ state machine
def state(anim, x, y, actions=(), sid=None):
    st = E("AnimationState", animationId=anim.id, x=x, y=y, id=sid or nid())
    st.add(list(actions))
    return st


def build():
    sm = E("StateMachine", name="Story", id=STAGE_SM)
    blank = Anim("Blank", 1)
    ANIMS.append(blank)
    ins, xs = {}, {}
    full_by = {}
    for sc in SCENES:
        for v in sc.variants:
            for mode in ("F", "B"):
                a = build_in(sc, v, mode)
                ANIMS.append(a)
                ins[(sc.k, v, mode)] = a
                if mode == "F":
                    full_by[(sc.k, v)] = a
            r = build_reduced(sc, v, full_by[(sc.k, v)])
            ANIMS.append(r)
            ins[(sc.k, v, "R")] = r
        for mode in ("F", "B", "R"):
            a = build_exit(sc, mode)
            ANIMS.append(a)
            xs[(sc.k, mode)] = a

    # ---------------- scenes layer
    lay = E("StateMachineLayer", name="Scenes")
    lay.add(E("AnyState", x=-200, y=-200), E("ExitState", x=-200, y=-300))
    boot = state(blank, 0, 0)
    entry = E("EntryState", x=-200, y=0, kids=[transition(boot.id)])
    lay.add(entry, boot)
    in_states, x_states = {}, {}
    row = {"F": 0, "B": 1, "R": 2}
    for (k, v, mode), a in ins.items():
        enter = write_num(path("enteredScreen"), k)
        in_states[(k, v, mode)] = state(a, 260 * k, 220 + 140 * row[mode] + 40 * v, [enter])
    for (k, mode), a in xs.items():
        x_states[(k, mode)] = state(a, 260 * k + 120, 760 + 140 * row[mode], [write_num(path("enteredScreen"), 0)])

    rm = path("reducedMotion")
    cs = path("currentScreen")

    def entries(mode, exit_pct=None, dur=0):
        out = []
        for sc in SCENES:
            for v in sc.variants:
                out.append((sc.k, v, [cond_num(cs, "equal", sc.k)] + variant_cond(sc, v)))
        return out

    for k, v, conds in entries("F"):
        boot.add(transition(in_states[(k, v, "R")].id, [cond_bool(rm, True)] + conds))
    for k, v, conds in entries("F"):
        boot.add(transition(in_states[(k, v, "F")].id, [cond_bool(rm, False)] + conds))
    for (k, v, mode), st in in_states.items():
        sc = BY_K[k]
        st.add(transition(x_states[(k, "R")].id, [cond_num(cs, "notEqual", k), cond_bool(rm, True)]))
        st.add(transition(x_states[(k, "F")].id, [cond_num(cs, "notEqual", k), cond_bool(rm, False),
                                                   cond_num(path("navDirection"), "greaterThanOrEqual", 0)], duration=100))
        st.add(transition(x_states[(k, "B")].id, [cond_num(cs, "notEqual", k), cond_bool(rm, False),
                                                   cond_num(path("navDirection"), "lessThan", 0)], duration=100))
        for v2 in sc.variants:
            if v2 != v:
                tgt = (k, v2, "R" if mode == "R" else "F")
                st.add(transition(in_states[tgt].id, [cond_num(cs, "equal", k)] + variant_cond(sc, v2), duration=250))
    for (k, mode), st in x_states.items():
        for kk, v, conds in entries(mode):
            st.add(transition(in_states[(kk, v, mode)].id, conds, exit_pct=100))
    lay.add(list(in_states.values()), list(x_states.values()))
    sm.add(lay)

    # ---------------- idle layer: restrained loops, frozen by pause, off for reduced motion
    rest_a = build_idle_rest()
    freeze_a = Anim("Idle Freeze", 1)
    ANIMS.extend([rest_a, freeze_a])
    il = E("StateMachineLayer", name="Idle")
    il.add(E("AnyState", x=-200, y=-200), E("ExitState", x=-200, y=-300))
    rest = state(rest_a, 0, 0)
    freeze = state(freeze_a, 0, 300)
    il.add(E("EntryState", x=-200, y=0, kids=[transition(rest.id)]), rest, freeze)
    settled = path("sceneSettled")
    paused = path("isPaused")
    for sc in SCENES:
        ia = build_idle(sc)
        ANIMS.append(ia)
        st = state(ia, 260 * sc.k, 150)
        rest.add(transition(st.id, [cond_num(cs, "equal", sc.k), cond_bool(settled, True), cond_bool(paused, False),
                                    cond_bool(rm, False)], duration=300))
        st.add(transition(freeze.id, [cond_bool(paused, True)]))
        st.add(transition(rest.id, [cond_num(cs, "notEqual", sc.k)], duration=250))
        st.add(transition(rest.id, [cond_bool(rm, True)], duration=150))
        st.add(transition(rest.id, [cond_bool(settled, False)], duration=250))
        il.add(st)
    freeze.add(transition(rest.id, [cond_bool(paused, False)], duration=300))
    freeze.add(transition(rest.id, [cond_bool(rm, True)]))
    sm.add(il)

    # ---------------- signature interaction: draggable hold compresses and rebounds
    s1 = BY_K[1]
    g_rest = Anim("Grab Rest", 1)
    g_rest.hold(s1.grab_squash.id, "scaleX", 1.0).hold(s1.grab_squash.id, "scaleY", 1.0)
    g_rest.hold(s1.grab_pitch, 243, 0.0)
    g_press = Anim("Grab Press", 10)
    g_press.tw(s1.grab_squash.id, "scaleX", 0, 8, 1.0, 1.16, "out")
    g_press.tw(s1.grab_squash.id, "scaleY", 0, 8, 1.0, 0.8, "out")
    g_press.tw(s1.grab_pitch, 243, 0, 8, 0.0, 0.55, "out")      # the 3D hold pivots under load
    g_reb = Anim("Grab Rebound", 40)
    g_reb.hold(s1.grab_hold.id, "x", 0.0).hold(s1.grab_hold.id, "y", 0.0)
    for f, sx, sy, e in [(0, 1.16, 0.8, "out"), (8, 0.86, 1.18, "inout"), (18, 1.07, 0.94, "inout"),
                         (28, 0.97, 1.03, "inout"), (40, 1.0, 1.0, "hold")]:
        g_reb.k(s1.grab_squash.id, "scaleX", f, sx, e)
        g_reb.k(s1.grab_squash.id, "scaleY", f, sy, e)
    for f, p_, e in [(0, 0.55, "out"), (9, -0.32, "inout"), (19, 0.16, "inout"), (29, -0.06, "inout"), (40, 0.0, "hold")]:
        g_reb.k(s1.grab_pitch, 243, f, p_, e)
    ANIMS.extend([g_rest, g_press, g_reb])
    gl = E("StateMachineLayer", name="Grab Hold")
    gl.add(E("AnyState", x=-200, y=-200), E("ExitState", x=-200, y=-300))
    gr = state(g_rest, 0, 0)
    gp = state(g_press, 260, 0)
    gb = state(g_reb, 520, 0)
    grabbed = path("holdGrabbed")
    gr.add(transition(gp.id, [cond_bool(grabbed, True)], duration=60))
    gp.add(transition(gb.id, [cond_bool(grabbed, False)], duration=420, interp="back"))
    gb.add(transition(gr.id, [], exit_pct=100))
    gb.add(transition(gp.id, [cond_bool(grabbed, True)], duration=60))
    gl.add(E("EntryState", x=-200, y=0, kids=[transition(gr.id)]), gr, gp, gb)
    sm.add(gl)

    # ---------------- share privacy: name only when shareIncludeName
    s10 = BY_K[10]
    n_off = Anim("Card Name Hidden", 1)
    n_off.hold(s10.name_cell.id, "opacity", 0.0).hold(s10.motif_cell.id, "opacity", 1.0)
    n_on = Anim("Card Name Shown", 1)
    n_on.hold(s10.name_cell.id, "opacity", 1.0).hold(s10.motif_cell.id, "opacity", 0.0)
    ANIMS.extend([n_off, n_on])
    nl = E("StateMachineLayer", name="Share Privacy")
    nl.add(E("AnyState", x=-200, y=-200), E("ExitState", x=-200, y=-300))
    so = state(n_off, 0, 0)
    sn = state(n_on, 260, 0)
    inc = path("shareIncludeName")
    so.add(transition(sn.id, [cond_bool(inc, True)], duration=200))
    sn.add(transition(so.id, [cond_bool(inc, False)], duration=200))
    nl.add(E("EntryState", x=-200, y=0, kids=[transition(so.id)]), so, sn)
    sm.add(nl)

    # ---------------- listeners: the hold (distinct hit region, never navigates)
    sm.kids.insert(0, E("StateMachineListenerSingle", targetId=s1.grab_target, listenerTypeValue="drag",
                        name="Drag Hold", kids=[E("ListenerAlignTarget", targetId=s1.grab_hold.id, preserveOffset=True)]))
    sm.kids.insert(0, E("StateMachineListenerSingle", targetId=s1.grab_target, listenerTypeValue="down",
                        name="Grab Hold", kids=[write_bool(grabbed, True)]))
    for t in ("up", "dragEnd"):
        sm.kids.insert(0, E("StateMachineListenerSingle", targetId=s1.grab_target, listenerTypeValue=t,
                            name=f"Release Hold ({t})", kids=[write_bool(grabbed, False)]))
    return sm


def artboard():
    sm = build()
    ab = E("Artboard", isComponent=True, defaultStateMachineId=STAGE_SM, viewModelId=model.VM_ID,
           viewModelInstanceId=model.DEFAULT_INSTANCE, width=W, height=H, x=500, y=0, clip=True, styleId="0:72",
           name="Stage", id=STAGE_AB)
    ab.add(E("LayoutComponentStyle", name="Stage Style", id="0:72"))
    ab.add(HERO_DRIVER)
    # Viewport: scale k = canvas height / 844, so keyed parallax offsets and the
    # carrier's flights cover any canvas height; the director writes every rig value
    # in these units.
    vp = E("Node", name="Viewport", kids=[bind(rig_path("k"), 16), bind(rig_path("k"), 17)])
    vp.add(CARRIER_FLY, CLOUD)
    for sc in SCENES:
        vp.add(sc.root)
    ab.add(vp)
    ab.add(sm)
    for a in ANIMS:
        ab.add(a.el())
    return ab
