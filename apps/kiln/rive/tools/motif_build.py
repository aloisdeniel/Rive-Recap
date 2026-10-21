"""Builds the persistent vessel + plinth and the Motif layer (one pose per
scene, a forward handoff, a reverse handoff and a reduced-motion cut).

The vessel is a real 3D pot (scripts/vessel3d.luau + .wgsl): a lathed surface
whose profile, glaze and firing are ScriptInputs keyed here. The plinth stays
vector. The signature handoff -- the piece compresses into a lidded clay slab,
re-centres with a turn of the wheel, and is pulled up into the next form while
the slab under it expands into the next plinth -- is all keyed on this layer.
"""
from __future__ import annotations

import math

import motif as MF
from rml import E, ellipse, fill, node, poly, shape, solid, stroke, argb
from gen_kiln import CHAR, CLAY, PORC, SCENES, ULTRA, Layer, settle
from chrome import c_bool, c_num, state, trans
from v3d import V3D, look

GLAZE = ULTRA
GLAZE_DEEP = "1F2C7A"
STONE = "EFE6D8"   # speckled stoneware body
RAW = "8F857C"     # raw, unfired body

# plinth pose: x, y (top surface), w, h, tilt, depth, front colour, top colour, opacity
PLINTHS = {
    1: (195, 418, 250, 150, 7, 18, "D9C9B6", "E8DDCF", 1.0),
    2: (222, 452, 300, 150, 9, 20, "94503B", "A9604A", 1.0),
    3: (195, 450, 236, 34, 0, 26, "1F2A66", "2D3B85", 1.0),
    4: (195, 476, 330, 14, 0, 10, "DCD1C2", "E7DED2", 1.0),
    5: (195, 432, 210, 14, 0, 12, "4A403A", "5C504A", 1.0),
    6: (195, 432, 300, 40, 4, 22, "C9AE95", "D8C2AC", 1.0),
    7: (222, 420, 160, 170, 6, 18, "8A4C3A", "B06C55", 1.0),
    8: (195, 436, 210, 60, 5, 16, "D8C9B6", "E6DACB", 1.0),
    9: (195, 384, 236, 220, 8, 22, "231E1C", "39312E", 1.0),
    10: (195, 470, 300, 6, 0, 4, "E2D6C6", "EEE6DA", 0.0),
}
SLAB_P = (195, 446, 300, 8, 0, 8, None, None, 1.0)


def seat(n):
    """base centre of a vessel standing on scene n's plinth (the middle of its top face)"""
    x, y, w, h, tilt, depth = PLINTHS[n][:6]
    return x, y - depth * 0.5


# vessel pose per scene: node placement (x, y, scale, rotation, opacity) + the 3D look
def _poses():
    P = {}
    x, y = seat(1)
    P[1] = dict(x=x, y=y, s=1.0, r=0.0, op=1.0,
                lk=look("vessel", body=CLAY, dip=0.16, flow=0.92, bandW=0.36, sway=0.42, drip=0.8, yaw=0.15,
                        speck=0.8, seed=1.0))
    x, y = seat(2)
    P[2] = dict(x=x + 30, y=y, s=1.0, r=0.0, op=1.0,
                lk=look("vase", body=STONE, dip=0.1, flow=1.0, bandW=0.44, sway=0.55, drip=0.7, yaw=0.25,
                        seed=2.0))
    x, y = seat(3)
    P[3] = dict(x=x, y=y, s=0.86, r=0.0, op=1.0,
                lk=look("bowl", body="E9E1D5", glaze="F8F5EF", gloss=0.7, dip=0.14, drip=0.9, inner=1.0, tilt=0.5,
                        turnGain=3.0, rings=1.6, seed=3.0))
    P[4] = dict(x=356, y=58, s=0.78, r=-2.25, op=1.0, sh=0.0,
                lk=look("jug", body=STONE, dip=0.48, drip=1.0, inner=1.0, tilt=0.26, roll=-2.25, seed=4.0))
    x, y = seat(5)
    P[5] = dict(x=x, y=y, s=0.7, r=0.0, op=1.0,
                lk=look("vessel", body=STONE, dip=0.2, flow=0.9, bandW=0.34, sway=0.4, seed=5.0))
    x, y = seat(6)
    P[6] = dict(x=x, y=y, s=1.3, r=0.0, op=1.0,
                lk=look("lump", body=CLAY, cap=1.0, rings=0.55, speck=0.5, sheen=0.5, drip=0.0, seed=6.0))
    x, y = seat(7)
    P[7] = dict(x=x, y=y, s=1.0, r=0.0, op=1.0,
                lk=look("idea", body=STONE, dip=0.14, flow=1.0, bandW=0.32, sway=0.5, seed=7.0))
    x, y = seat(8)
    P[8] = dict(x=x, y=y, s=1.12, r=0.0, op=1.0,
                lk=look("cup", body=STONE, dip=0.2, drip=0.8, inner=1.0, tilt=0.24, seed=8.0))
    P[9] = dict(x=195, y=270, s=0.0, r=0.0, op=0.0, sh=0.0,
                lk=look("orb", body=GLAZE, cap=1.0, sphere=1.0, dip=1.0, drip=0.0, gloss=1.2, live=0.0, seed=9.0))
    P[10] = dict(x=195, y=300, s=0.4, r=0.0, op=0.0, sh=0.0,
                 lk=look("slab", body=STONE, cap=1.0, live=0.0, seed=10.0))
    return P


POSES = _poses()


def slab_pose(n, **kw):
    """the lidded clay slab of the handoff, in scene n's clay, glaze drawn back up"""
    lk = look("slab", body=POSES[n]["lk"]["body"], glaze=POSES[n]["lk"]["glaze"], cap=1.0, rings=1.2, speck=0.8,
              tilt=0.2, seed=POSES[n]["lk"]["seed"], yaw=POSES[n]["lk"]["yaw"] - 2.2)
    d = dict(x=195, y=442, s=1.0, r=0.0, op=1.0, lk=lk)
    d.update(kw)
    return d


def with_(pose, lk=None, **kw):
    d = dict(pose)
    d.update(kw)
    nl = dict(pose["lk"])
    if lk:
        nl.update(lk)
    d["lk"] = nl
    return d


class Motif:
    pass


def build(g):
    m = Motif()
    p1 = POSES[1]
    v = V3D(g, "Vessel 3D", p1["lk"], turn=True, scene=True)
    m.v3d = v
    contact = shape("Contact Shadow", 0, 4, ellipse(170, 22), fill(CHAR, alpha=0.32, feather=10))
    settle(contact, "scaleX", 1.0)
    settle(contact, "opacity", 1.0)
    m.contact = contact
    vessel = node("Vessel", p1["x"], p1["y"], v.el, contact)
    for prop, val in (("x", p1["x"]), ("y", p1["y"]), ("scaleX", 1.0), ("scaleY", 1.0), ("rotation", 0.0),
                      ("opacity", 1.0)):
        settle(vessel, prop, val)
    m.vessel = vessel

    # plinth
    P1 = PLINTHS[1]
    fpts, tpts = MF.plinth_points(*P1[2:6])
    front_path = poly(fpts, name="Front")
    top_path = poly(tpts, name="Top")
    m.pf = front_path.children
    m.pt = top_path.children
    pf_col = solid(P1[6], name="Front")
    pt_col = solid(P1[7], name="Top")
    for vx, (x, y) in zip(m.pf + m.pt, fpts + tpts):
        settle(vx, "x", x)
        settle(vx, "y", y)
    settle(pf_col, "colorValue", argb(P1[6]), set_attr=False)
    settle(pt_col, "colorValue", argb(P1[7]), set_attr=False)
    m.pf_col, m.pt_col = pf_col, pt_col
    p_top = shape("Plinth Top", 0, 0, top_path, E("Fill", {"name": "Fill"}, pt_col))
    p_front = shape("Plinth Front", 0, 0, front_path, E("Fill", {"name": "Fill"}, pf_col))
    # carved-stone light: a soft top-edge highlight and a shaded lower front
    p_edge = shape("Plinth Edge", 0, 0, poly(fpts[:3], closed=False), stroke("FFFFFF", 1.4, alpha=0.22))
    p_grain = shape("Plinth Grain", 0, 0, poly([(-60, 30), (-20, 34), (30, 28)], closed=False),
                    poly([(-80, 70), (-30, 76)], closed=False), stroke(CHAR, 1.0, alpha=0.08))
    plinth = node("Plinth", P1[0], P1[1], p_top, p_edge, p_grain, p_front)
    for prop, val in (("x", float(P1[0])), ("y", float(P1[1])), ("opacity", 1.0)):
        settle(plinth, prop, val)
    m.plinth = plinth
    for sc, _a in g.ink_paints:
        settle(sc, "colorValue", sc.attrs["colorValue"], set_attr=False)
    for sc in g.bg_paints:
        settle(sc, "colorValue", sc.attrs["colorValue"], set_attr=False)

    g.motif_vessel = vessel
    g.motif_plinth = plinth
    build_layer(g, m)
    return m


# ---------------------------------------------------------------------------


def key_vessel(a, m, f, pose, ease="settle", only=None):
    lk = pose["lk"]
    m.v3d.key(a, f, lk, ease, only=only)
    if only is not None:
        return
    a.k(m.v3d.inputs["roll"], "propertyValue", (f, float(pose["r"]), ease))
    a.k(m.vessel, "x", (f, pose["x"], ease)).k(m.vessel, "y", (f, pose["y"], ease))
    a.k(m.vessel, "scaleX", (f, pose["s"], ease)).k(m.vessel, "scaleY", (f, pose["s"], ease))
    a.k(m.vessel, "rotation", (f, pose["r"], ease)).k(m.vessel, "opacity", (f, pose["op"], ease))
    a.k(m.contact, "scaleX", (f, max(0.5, lk["r0"] / 50.0), ease))
    a.k(m.contact, "opacity", (f, float(pose.get("sh", 1.0)) * (1.0 if abs(pose["r"]) < 0.5 else 0.0), ease))


GLAZE_KEYS = ["dip", "flow", "drip"]


def key_glaze(a, m, f, lk, ease="heavy", scale=1.0):
    for k in GLAZE_KEYS:
        a.k(m.v3d.inputs[k], "propertyValue", (f, float(lk[k]) * (scale if k != "drip" else 1.0), ease))


def key_plinth(a, m, f, pp, ease="settle"):
    x, y, w, h, tilt, depth, fc, tc, op = pp
    fpts, tpts = MF.plinth_points(w, h, tilt, depth)
    for v, (vx, vy) in zip(m.pf + m.pt, fpts + tpts):
        a.k(v, "x", (f, vx, ease)).k(v, "y", (f, vy, ease))
    a.k(m.plinth, "x", (f, x, ease)).k(m.plinth, "y", (f, y, ease)).k(m.plinth, "opacity", (f, op, ease))
    if fc:
        a.k(m.pf_col, "colorValue", (f, fc, "lin"))
    if tc:
        a.k(m.pt_col, "colorValue", (f, tc, "lin"))


def key_chrome(g, a, n, f=0):
    sc = SCENES[n]
    for paint in g.bg_paints:
        a.k(paint, "colorValue", (f, sc["bg"], "lin"))
    for paint, alpha in g.ink_paints:
        a.k(paint, "colorValue", (f, argb(sc["ink"], alpha), "lin"))


def build_layer(g, m):
    L = Layer("Motif")
    g.layers.append(L)
    any_ = E("AnyState", {"x": 0.0, "y": -260.0})
    L.el.add(any_, E("ExitState", {"x": 1600.0, "y": -260.0}), E("EntryState", {"x": -200.0, "y": 0.0}))

    for n in range(1, 11):
        V, P = POSES[n], PLINTHS[n]
        lk = V["lk"]
        slab = slab_pose(n)
        bare = with_(V, lk=dict(dip=0.0, flow=0.0))   # the form before its glaze flows

        # ---------------- forward handoff: compress to slab, re-centre on the wheel, pull up the next form
        a = L.anim(f"Motif {n} Forward", 300 if n == 7 else 160)
        key_chrome(g, a, n)
        if n == 1:
            # opening: a closed lump on the wheel is opened, pulled up tall, then shaped
            lump = with_(bare, lk=dict(look("lump", body=lk["body"], cap=1.0, sheen=0.4, seed=lk["seed"],
                                            yaw=lk["yaw"] - 3.0)), s=0.9)
            key_vessel(a, m, 0, lump, "hold")
            key_vessel(a, m, 14, with_(lump, lk=dict(look("pinch", body=lk["body"], cap=0.6, sheen=0.3,
                                                          seed=lk["seed"], yaw=lk["yaw"] - 2.2)), s=0.95), "in")
            key_vessel(a, m, 48, with_(bare, lk=dict(look("tall", body=lk["body"], seed=lk["seed"],
                                                          yaw=lk["yaw"] - 0.8, rings=1.4))), "settle")
            key_vessel(a, m, 80, bare, "back")
            key_glaze(a, m, 0, bare["lk"], "hold")
            key_glaze(a, m, 76, bare["lk"], "heavy")
            key_glaze(a, m, 124, lk)
            key_plinth(a, m, 0, (P[0], P[1], P[2], 4, 0, 4, P[6], P[7], 1.0), "hold")
            key_plinth(a, m, 6, (P[0], P[1], P[2], 4, 0, 4, P[6], P[7], 1.0), "back")
            key_plinth(a, m, 44, P)
        elif n == 9:
            orb = with_(V, s=0.85, op=1.0, lk=dict(live=1.0))
            key_vessel(a, m, 0, slab, "hold")
            key_vessel(a, m, 14, slab, "back")
            key_vessel(a, m, 44, with_(orb, lk=dict(dip=0.0)), "settle")
            key_glaze(a, m, 44, dict(dip=0.0, flow=0.0, drip=0.0), "heavy")
            key_glaze(a, m, 60, orb["lk"], "out")
            key_vessel(a, m, 60, with_(orb, s=0.95), "inout", only=None)
            key_vessel(a, m, 72, with_(orb, s=0.7), "in")
            key_vessel(a, m, 86, with_(orb, s=0.0, op=0.0), "hold")
            key_vessel(a, m, 87, V, "hold")
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 14, SLAB_P, "back")
            key_plinth(a, m, 54, P)
        elif n == 10:
            key_vessel(a, m, 0, slab, "hold")
            key_vessel(a, m, 16, slab, "in")
            key_vessel(a, m, 40, with_(slab, y=300, s=0.6, op=0.0), "hold")
            key_vessel(a, m, 41, V, "hold")
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 16, SLAB_P, "in")
            key_plinth(a, m, 40, P, "hold")
        else:
            key_vessel(a, m, 0, slab, "hold")
            key_vessel(a, m, 12, slab, "back")
            if n == 4:
                upright = with_(bare, r=0.0, x=300, y=180)
                key_vessel(a, m, 52, upright, "settle")
                key_vessel(a, m, 66, with_(upright, r=0.18), "in")
                key_vessel(a, m, 104, bare, "back")
                key_glaze(a, m, 0, bare["lk"], "hold")
                key_glaze(a, m, 40, bare["lk"], "heavy")
                key_glaze(a, m, 92, lk)
            elif n == 7:
                key_vessel(a, m, 52, with_(bare, lk=look("bowl", **{k: lk[k] for k in ("body", "glaze", "seed")},
                                                          yaw=lk["yaw"])), "back")
                t0 = 70
                for k, prof in enumerate(MF.SEVEN[1:], start=1):
                    f_hold = t0 + (k - 1) * 40
                    key_vessel(a, m, f_hold, with_(V, lk=dict(MF_profile(MF.SEVEN[k - 1]))), "inout",
                               only=PROFILE_ONLY)
                    key_vessel(a, m, f_hold + 24, with_(V, lk=dict(MF_profile(prof))), "settle", only=PROFILE_ONLY)
                key_vessel(a, m, 300, V, "hold")
                key_glaze(a, m, 0, bare["lk"], "hold")
                key_glaze(a, m, 46, bare["lk"], "heavy")
                key_glaze(a, m, 96, lk)
            elif n == 5:
                # into the kiln: raw grey body glows white-hot, the glaze melts in, then it cools
                raw = with_(bare, lk=dict(body=RAW, heat=0.0))
                key_vessel(a, m, 52, raw, "back")
                key_vessel(a, m, 100, with_(raw, lk=dict(body=lk["body"])), "hold", only=["body"])
                a.k(m.v3d.inputs["heat"], "propertyValue", (0, 0.0, "hold"), (52, 0.0, "in"), (84, 0.72, "out"),
                    (104, 1.0, "inout"), (126, 0.85, "soft"), (160, 0.0, "hold"))
                key_glaze(a, m, 0, bare["lk"], "hold")
                key_glaze(a, m, 90, bare["lk"], "heavy")
                key_glaze(a, m, 120, lk)
            elif n == 6:
                key_vessel(a, m, 22, with_(V, s=0.3), "heavy")
                key_vessel(a, m, 70, with_(V, s=1.1), "back")
                key_vessel(a, m, 84, V, "settle")
            else:
                key_vessel(a, m, 54, bare, "back")
                key_glaze(a, m, 0, bare["lk"], "hold")
                key_glaze(a, m, 50, bare["lk"], "heavy")
                key_glaze(a, m, 108, lk)
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 12, SLAB_P, "back")
            key_plinth(a, m, 52, P)
        fw = state(a, 200 + (n - 1) * 150, -120)

        # ---------------- reverse handoff: the piece sinks back into the wheel and springs up
        b = L.anim(f"Motif {n} Back", 70)
        key_chrome(g, b, n)
        if n in (9, 10):
            key_vessel(b, m, 0, with_(V, s=0.0, op=0.0), "hold")
        else:
            sunk = with_(V, y=V["y"] + 50, s=V["s"] * 0.55, r=V["r"] - 0.35, lk=dict(yaw=lk["yaw"] + 1.6))
            key_vessel(b, m, 0, sunk, "hold")
            key_vessel(b, m, 8, sunk, "back")
            key_vessel(b, m, 46, V, "settle")
        key_glaze(b, m, 0, lk, "hold", scale=0.3)
        key_glaze(b, m, 10, lk, "out", scale=0.3)
        key_glaze(b, m, 60, lk)
        x, y, w, h, tilt, depth, fc, tc, op = P
        key_plinth(b, m, 0, (x, y, w * 0.8, h * 0.4, tilt, depth, fc, tc, op), "hold")
        key_plinth(b, m, 4, (x, y, w * 0.8, h * 0.4, tilt, depth, fc, tc, op), "back")
        key_plinth(b, m, 40, P)
        bk = state(b, 200 + (n - 1) * 150, 20)

        # ---------------- reduced motion: final composition, short opacity change only
        r = L.anim(f"Motif {n} Reduced", 14)
        key_chrome(g, r, n)
        key_vessel(r, m, 0, with_(V, op=0.0), "hold")
        r.k(m.vessel, "opacity", (0, 0.0, "lin"), (14, V["op"], "hold"))
        key_plinth(r, m, 0, P, "hold")
        rm = state(r, 200 + (n - 1) * 150, 160)

        any_.add(trans(rm, 0, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", True)]))
        any_.add(trans(fw, 260, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", False),
                                 c_num(g, "_navDir", 0, "greaterThanOrEqual")], ease="inout"))
        any_.add(trans(bk, 320, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", False),
                                 c_num(g, "_navDir", 0, "lessThan")], ease="inout"))
        L.el.add(fw, bk, rm)


PROFILE_ONLY = ["h"] + [f"r{i}" for i in range(6)] + [f"c{i}" for i in range(6)]


def MF_profile(prof):
    from v3d import profile
    return profile(prof)
