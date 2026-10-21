"""Builds the persistent vessel + plinth and the Motif layer (one pose per
scene, a forward handoff, a reverse handoff and a reduced-motion cut)."""
from __future__ import annotations

import math

import motif as MF
from rml import E, ellipse, fill, mix, node, poly, shape, smooth_path, solid, stroke, bind, argb
from gen_kiln import CHAR, CLAY, PORC, SCENES, ULTRA, Layer, settle
from chrome import c_bool, c_num, state, trans

GLAZE = ULTRA
GLAZE_DEEP = "26337F"

# vessel pose: profile, x, y (base), scale, rot, body, glaze colour, glaze flow (0..1), opacity
# plinth pose: x, y (top surface), w, h, tilt, depth, front colour, top colour, opacity
POSES = {
    1: dict(v=("vessel", 195, 418, 1.0, 0.0, CLAY, GLAZE, 1.0, 1.0),
            p=(195, 418, 250, 150, 7, 18, "D9C9B6", "E8DDCF", 1.0)),
    2: dict(v=("vase", 252, 452, 1.0, 0.0, "EFE7DC", GLAZE, 1.0, 1.0),
            p=(222, 452, 300, 150, 9, 20, "94503B", "A9604A", 1.0)),
    3: dict(v=("bowl", 195, 424, 0.92, 0.0, "EFE7DC", GLAZE_DEEP, 1.0, 1.0),
            p=(195, 424, 236, 34, 0, 26, "1F2A66", "2D3B85", 1.0)),
    4: dict(v=("jug", 336, 70, 0.78, -2.25, "EDE5D9", GLAZE, 1.0, 1.0),
            p=(195, 476, 330, 14, 0, 10, "DCD1C2", "E7DED2", 1.0)),
    5: dict(v=("vessel", 195, 432, 0.7, 0.0, "EFE7DC", GLAZE, 1.0, 1.0),
            p=(195, 432, 210, 14, 0, 12, "4A403A", "5C504A", 1.0)),
    6: dict(v=("lump", 195, 432, 1.45, 0.0, CLAY, GLAZE, 0.0, 1.0),
            p=(195, 432, 300, 40, 4, 22, "C9AE95", "D8C2AC", 1.0)),
    7: dict(v=("idea", 222, 420, 1.0, 0.0, "EFE7DC", GLAZE, 1.0, 1.0),
            p=(222, 420, 160, 170, 6, 18, "8A4C3A", "B06C55", 1.0)),
    8: dict(v=("cup", 195, 436, 1.0, 0.0, "EFE7DC", GLAZE, 0.5, 1.0),
            p=(195, 436, 210, 60, 5, 16, "D8C9B6", "E6DACB", 1.0)),
    9: dict(v=("orb", 195, 270, 0.0, 0.0, ULTRA, GLAZE, 0.0, 0.0),
            p=(195, 384, 236, 220, 8, 22, "231E1C", "39312E", 1.0)),
    10: dict(v=("slab", 195, 300, 0.4, 0.0, "EFE7DC", GLAZE, 0.0, 0.0),
             p=(195, 470, 300, 6, 0, 4, "E2D6C6", "EEE6DA", 0.0)),
}
SLAB_V = ("slab", 195, 446, 1.0, 0.0, None, None, 0.0, 1.0)
SLAB_P = (195, 446, 300, 8, 0, 8, None, None, 1.0)

RIBBON = [(6, -12), (34, -12), (46, 30), (28, 100), (40, 164), (24, 224), (30, 268), (12, 262), (8, 196),
          (-4, 134), (12, 72), (2, 18)]


class Motif:
    pass


def build(g):
    m = Motif()
    base_vs = MF.profile_vertices("vessel")
    path, verts = smooth_path(base_vs, closed=True, name="Silhouette")
    m.verts = verts
    m.base = base_vs
    body = solid(CLAY, name="Body")
    m.body_color = body
    vessel_body = shape("Vessel Body", 0, 0, path, E("Fill", {"name": "Fill"}, body))
    m.body_shape = vessel_body

    # glaze ribbon, clipped by the silhouette, flows down by scaling from its top
    rib_vs = __import__("rml").smooth_vertices(RIBBON, closed=True, tension=0.2)
    rib_path, _ = smooth_path(rib_vs, closed=True, name="Ribbon")
    glaze_col = solid(GLAZE, name="Glaze")
    m.glaze_color = glaze_col
    glaze = shape("Glaze", 0, 0, rib_path, E("Fill", {"name": "Fill"}, glaze_col))
    drip = shape("Glaze Drip", 30, 262, ellipse(14, 20), E("Fill", {"name": "Fill"}, solid(GLAZE)))
    glaze_flow = node("Glaze Flow", 0, 0, glaze, drip)
    settle(glaze_flow, "scaleY", 1.0)
    glaze_frame = node("Glaze Frame", 0, -250, glaze_flow)
    settle(glaze_frame, "y", -250.0)
    settle(glaze_frame, "scaleX", 1.0)
    settle(glaze_frame, "scaleY", 1.0)
    settle(glaze_frame, "opacity", 1.0)
    m.glaze_flow, m.glaze_frame = glaze_flow, glaze_frame

    # turntable light: a highlight that orbits with _turnPhase, and a fixed core shade
    hl = shape("Highlight", 0, 0, ellipse(30, 300),
               fill("FFFFFF", alpha=0.6, feather=12))
    sin_f = g.formula("Turntable X", g.tv(46), g.op("*"), g.fn("sin"), g.INPUT(), g.op("*"), g.tv(6.283185),
                      g.CLOSE())
    hl.add(bind(g.p("_turnPhase"), 13, sin_f.id))
    cos_f = g.formula("Turntable Light", g.tv(0.2), g.op("+"), g.tv(0.32), g.op("*"), g.fn("cos"), g.INPUT(),
                      g.op("*"), g.tv(6.283185), g.CLOSE())
    hl.add(bind(g.p("_turnPhase"), 18, cos_f.id))
    shade = shape("Core Shade", -62, 0, ellipse(70, 320), fill(CHAR, alpha=0.26, feather=22))
    rim = shape("Rim Shade", 66, 0, ellipse(30, 320), fill(CHAR, alpha=0.14, feather=12))
    light = node("Turntable Light", 0, -125, hl, shade, rim)
    settle(light, "y", -125.0)
    settle(light, "scaleX", 1.0)
    settle(light, "scaleY", 1.0)
    m.light = light

    surface = node("Vessel Surface", 0, 0, E("ClippingShape", {"sourceId": vessel_body.id, "name": "Clip"}),
                   light, glaze_frame)
    contact = shape("Contact Shadow", 0, 2, ellipse(170, 16), fill(CHAR, alpha=0.28, feather=8))
    settle(contact, "scaleX", 1.0)
    settle(contact, "opacity", 1.0)
    m.contact = contact
    vessel = node("Vessel", 195, 418, surface, vessel_body, contact)
    for prop, v in (("x", 195.0), ("y", 418.0), ("scaleX", 1.0), ("scaleY", 1.0), ("rotation", 0.0), ("opacity", 1.0)):
        settle(vessel, prop, v)
    m.vessel = vessel

    # register vertex settled values
    for v, (x, y, r, d) in zip(verts, base_vs):
        for prop, val in (("x", x), ("y", y), ("rotation", r), ("distance", d)):
            settle(v, prop, val)
    settle(body, "colorValue", argb(CLAY), set_attr=False)
    settle(glaze_col, "colorValue", argb(GLAZE), set_attr=False)

    # plinth
    fpts, tpts = MF.plinth_points(250, 150, 7, 18)
    front_path = poly(fpts, name="Front")
    top_path = poly(tpts, name="Top")
    m.pf = front_path.children
    m.pt = top_path.children
    pf_col = solid("D9C9B6", name="Front")
    pt_col = solid("E8DDCF", name="Top")
    for v, (x, y) in zip(m.pf + m.pt, fpts + tpts):
        settle(v, "x", x)
        settle(v, "y", y)
    settle(pf_col, "colorValue", argb("D9C9B6"), set_attr=False)
    settle(pt_col, "colorValue", argb("E8DDCF"), set_attr=False)
    m.pf_col, m.pt_col = pf_col, pt_col
    p_top = shape("Plinth Top", 0, 0, top_path, E("Fill", {"name": "Fill"}, pt_col))
    p_front = shape("Plinth Front", 0, 0, front_path, E("Fill", {"name": "Fill"}, pf_col))
    p_grain = shape("Plinth Grain", 0, 0, poly([(-60, 30), (-20, 34), (30, 28)], closed=False),
                    poly([(-80, 70), (-30, 76)], closed=False), stroke(CHAR, 1.0, alpha=0.08))
    plinth = node("Plinth", 195, 418, p_top, p_grain, p_front)
    for prop, v in (("x", 195.0), ("y", 418.0), ("opacity", 1.0)):
        settle(plinth, prop, v)
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


def key_vessel(a, m, f, pose, ease="settle", base=None):
    prof, x, y, s, r, body, gl, flow, op = pose
    vs = MF.profile_vertices(prof, base=m.base)
    for v, (vx, vy, vr, vd) in zip(m.verts, vs):
        a.k(v, "x", (f, vx, ease)).k(v, "y", (f, vy, ease)).k(v, "rotation", (f, vr, ease)).k(v, "distance", (f, vd, ease))
    h = MF.profile_height(prof)
    rows = MF.PROFILES[prof][1]
    wfac = max(w for _, w in rows) / 92.0
    a.k(m.vessel, "x", (f, x, ease)).k(m.vessel, "y", (f, y, ease))
    a.k(m.vessel, "scaleX", (f, s, ease)).k(m.vessel, "scaleY", (f, s, ease)).k(m.vessel, "rotation", (f, r, ease))
    a.k(m.vessel, "opacity", (f, op, ease))
    a.k(m.glaze_frame, "y", (f, -h, ease)).k(m.glaze_frame, "scaleY", (f, h / 250.0, ease))
    a.k(m.glaze_frame, "scaleX", (f, max(0.5, wfac), ease))
    a.k(m.light, "y", (f, -h / 2, ease)).k(m.light, "scaleX", (f, max(0.45, wfac), ease))
    a.k(m.light, "scaleY", (f, max(0.2, h / 260.0), ease))
    a.k(m.contact, "scaleX", (f, max(0.5, rows[0][1] / 50.0), ease))
    if body:
        a.k(m.body_color, "colorValue", (f, body, "lin"))
    if gl:
        a.k(m.glaze_color, "colorValue", (f, gl, "lin"))


def key_flow(a, m, f, flow, ease="heavy"):
    a.k(m.glaze_flow, "scaleY", (f, flow, ease))


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


def pose(n, part):
    return POSES[n][part]


def with_(t, **kw):
    names = ["prof", "x", "y", "s", "r", "body", "gl", "flow", "op"]
    d = dict(zip(names, t))
    d.update(kw)
    return tuple(d[k] for k in names)


def build_layer(g, m):
    L = Layer("Motif")
    g.layers.append(L)
    any_ = E("AnyState", {"x": 0.0, "y": -260.0})
    L.el.add(any_, E("ExitState", {"x": 1600.0, "y": -260.0}), E("EntryState", {"x": -200.0, "y": 0.0}))

    for n in range(1, 11):
        V, P = pose(n, "v"), pose(n, "p")
        body, gl = V[5], V[6]

        # ---------------- forward handoff: compress to slab, expand into the scene
        a = L.anim(f"Motif {n} Forward", 300 if n == 7 else 150)
        key_chrome(g, a, n)
        if n == 1:
            # opening: a lump on the wheel is thrown up into the vessel
            lump = with_(V, prof="lump", y=418, s=0.9)
            key_vessel(a, m, 0, lump, "hold")
            key_vessel(a, m, 14, with_(lump, prof="pinch", s=0.95), "in")
            key_vessel(a, m, 46, with_(V, prof="tall", s=1.0), "settle")
            key_vessel(a, m, 76, V, "back")
            key_flow(a, m, 0, 0.0, "hold")
            key_flow(a, m, 70, 0.0, "heavy")
            key_flow(a, m, 118, 1.0)
            key_plinth(a, m, 0, (195, 418, 250, 4, 0, 4, P[6], P[7], 1.0), "hold")
            key_plinth(a, m, 6, (195, 418, 250, 4, 0, 4, P[6], P[7], 1.0), "back")
            key_plinth(a, m, 44, P)
        elif n == 9:
            key_vessel(a, m, 0, with_(SLAB_V, body=body, gl=gl), "hold")
            orb = with_(V, s=0.85, op=1.0)
            key_vessel(a, m, 14, with_(SLAB_V, body=body, gl=gl), "back")
            key_vessel(a, m, 44, orb, "settle")
            key_vessel(a, m, 60, with_(orb, s=0.95), "inout")
            key_vessel(a, m, 70, with_(orb, s=0.7), "in")
            key_vessel(a, m, 84, with_(orb, s=0.0, op=0.0), "hold")
            key_flow(a, m, 0, 0.0, "hold")
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 14, SLAB_P, "back")
            key_plinth(a, m, 54, P)
        elif n == 10:
            key_vessel(a, m, 0, with_(SLAB_V, body=body, gl=gl), "hold")
            key_vessel(a, m, 16, with_(SLAB_V, body=body, gl=gl), "in")
            key_vessel(a, m, 40, with_(SLAB_V, y=300, s=0.6, op=0.0, body=body, gl=gl), "hold")
            key_flow(a, m, 0, 0.0, "hold")
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 16, SLAB_P, "in")
            key_plinth(a, m, 40, P, "hold")
        else:
            key_vessel(a, m, 0, with_(SLAB_V, body=body, gl=gl), "hold")
            key_vessel(a, m, 12, with_(SLAB_V, body=body, gl=gl), "back")
            if n == 4:
                upright = with_(V, r=0.0, x=300, y=180)
                key_vessel(a, m, 52, upright, "settle")
                key_vessel(a, m, 66, with_(upright, r=0.18), "in")
                key_vessel(a, m, 104, V, "back")
            elif n == 7:
                key_vessel(a, m, 52, with_(V, prof="bowl"), "back")
                t0 = 70
                for k, prof in enumerate(MF.SEVEN[1:], start=1):
                    f_hold = t0 + (k - 1) * 40
                    key_vessel(a, m, f_hold, with_(V, prof=MF.SEVEN[k - 1]), "inout")
                    key_vessel(a, m, f_hold + 24, with_(V, prof=prof), "settle")
                key_vessel(a, m, 300, V, "hold")
            elif n == 5:
                raw = with_(V, body="8F857C")
                key_vessel(a, m, 52, raw, "back")
                a.k(m.body_color, "colorValue", (0, "8F857C", "hold"), (52, "8F857C", "lin"), (78, "F2A15A", "lin"),
                    (100, "F07E45", "lin"), (150, "EFE7DC", "hold"))
            elif n == 6:
                key_vessel(a, m, 22, with_(V, s=0.3), "heavy")
                key_vessel(a, m, 70, with_(V, s=1.1), "back")
                key_vessel(a, m, 84, V, "settle")
            else:
                key_vessel(a, m, 54, V, "back")
            key_flow(a, m, 0, 0.0, "hold")
            if V[7] > 0:
                key_flow(a, m, 50 if n != 4 else 96, 0.0)
                key_flow(a, m, 104 if n != 4 else 140, V[7])
            key_plinth(a, m, 0, SLAB_P, "hold")
            key_plinth(a, m, 12, SLAB_P, "back")
            key_plinth(a, m, 52, P)
        fw = state(a, 200 + (n - 1) * 150, -120)

        # ---------------- reverse handoff: the piece sinks back and springs up
        b = L.anim(f"Motif {n} Back", 70)
        key_chrome(g, b, n)
        if n in (9, 10):
            key_vessel(b, m, 0, with_(V, s=0.0, op=0.0), "hold")
        else:
            key_vessel(b, m, 0, with_(V, y=V[2] + 50, s=V[3] * 0.55, r=V[4] - 0.35), "hold")
            key_vessel(b, m, 8, with_(V, y=V[2] + 50, s=V[3] * 0.55, r=V[4] - 0.35), "back")
            key_vessel(b, m, 46, V, "settle")
        key_flow(b, m, 0, V[7] * 0.3, "hold")
        key_flow(b, m, 10, V[7] * 0.3, "out")
        key_flow(b, m, 60, V[7])
        x, y, w, h, tilt, depth, fc, tc, op = P
        key_plinth(b, m, 0, (x, y, w * 0.8, h * 0.4, tilt, depth, fc, tc, op), "hold")
        key_plinth(b, m, 4, (x, y, w * 0.8, h * 0.4, tilt, depth, fc, tc, op), "back")
        key_plinth(b, m, 40, P)
        if n == 7:
            key_vessel(b, m, 46, V, "hold")
        bk = state(b, 200 + (n - 1) * 150, 20)

        # ---------------- reduced motion: final composition, short opacity change only
        r = L.anim(f"Motif {n} Reduced", 14)
        key_chrome(g, r, n)
        key_vessel(r, m, 0, with_(V, op=0.0), "hold")
        key_vessel(r, m, 1, with_(V, op=0.0), "lin")
        r.k(m.vessel, "opacity", (0, 0.0, "lin"), (14, V[8], "lin"))
        key_flow(r, m, 0, V[7], "hold")
        key_plinth(r, m, 0, P, "hold")
        rm = state(r, 200 + (n - 1) * 150, 160)

        cs = c_num(g, "currentScreen", n)
        any_.add(trans(rm, 0, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", True)]))
        any_.add(trans(fw, 260, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", False),
                                 c_num(g, "_navDir", 0, "greaterThanOrEqual")], ease="inout"))
        any_.add(trans(bk, 320, [c_num(g, "currentScreen", n), c_bool(g, "reducedMotion", False),
                                 c_num(g, "_navDir", 0, "lessThan")], ease="inout"))
        L.el.add(fw, bk, rm)
