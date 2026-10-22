"""The ten scenes: copy, layered art and per-scene choreography."""
from __future__ import annotations

import math

import motif as MF
from rml import (E, Anim, argb, bind, child, ellipse, fill, mix, node, poly, rect, shape, smooth_path,
                 smooth_vertices, solid, stroke)
from gen_kiln import (ART_H, ART_W, CHAR, CLAY, ENTER, EXIT, H, PORC, SCENES, ULTRA, W, Layer, settle)
from chrome import c_bool, c_num, scene_states, state, trans

SAND = "E7D2C0"


def S(el, **props):
    """author + register settled values for keyable props"""
    for k, v in props.items():
        settle(el, k, v)
    return el


# ---------------------------------------------------------------------------
# scene scaffold


class Scene:
    def __init__(self, g, n):
        self.g = g
        self.n = n
        self.ink = SCENES[n]["ink"]
        self.front = S(node(f"Scene {n} Front"), opacity=1.0, y=0.0)
        self.back = S(node(f"Scene {n} Back"), opacity=1.0, y=0.0)
        self.copy = None
        self.reveals: list[tuple[E, int, int]] = []   # (Text, start, duration)
        self.hooks: dict[str, list] = {k: [] for k in ("enterF", "enterB", "idle", "exitF", "exitB")}
        self.extra_roots: list[E] = []                # other things faded with the scene
        self.live_inputs: list[E] = []                # script `live` inputs: 0 while the scene is hidden
        self.idle_frames = 240

    # copy box: an absolute column whose four insets, content alignment and scale are
    # bound to the placement the sequencer computes from the real artboard size
    # (portrait: pinned under the header; landscape: a column beside the art)
    def copy_box(self, *children, top=86, left=28, right=28, align="topLeft", gap=6):
        g = self.g
        n = self.n
        st = g.abs_style(top=top, bottom=0, left=left, right=right, flexDirectionValue="column",
                         layoutAlignmentType=align, gapVertical=float(gap), gapVerticalUnitsValue="points",
                         name=f"Copy {n} Style")
        pl = "_altL" if n == 9 else "_copyL"
        pr = {9: "_altR", 4: "_copyR4"}.get(n, "_copyR")
        pt = {9: "_c9T", 10: "_c10T"}.get(n, "_copyT")
        pb = "_c10B" if n == 10 else "_copyB"
        pa = "_align10" if n == 10 else ("_alignC" if align == "topCenter" else "_alignL")
        for prop, key in ((pl, 516), (pr, 517), (pt, 518), (pb, 519), (pa, 632)):
            st.add(bind(g.p(prop), key))
        box = g.box(f"Copy {n}", st, *children, w=10, h=300, clip=False)
        box.add(bind(g.p("_copyS"), 16), bind(g.p("_copyS"), 17))
        # centred copy (portrait) becomes a left-aligned column beside the art (landscape)
        for t in _texts(box):
            if t.attrs.get("alignValue") == "center":
                t.add(bind(g.p("_textC"), 281))
        S(box, opacity=1.0, y=0.0)
        self.copy = box
        return box

    def spacer(self, h):
        g = self.g
        st = g.style(layoutWidthScaleType="fill", layoutHeightScaleType="fixed", name="Spacer Style")
        return g.box("Spacer", st, w=10, h=h)

    def reveal(self, t, start, dur=30):
        self.reveals.append((t, start, dur))
        return t

    def on(self, kind, fn):
        self.hooks[kind].append(fn)


def _texts(el):
    for c in el.children:
        if c.tag == "Text":
            yield c
        elif c.tag in ("LayoutComponent", "Node"):
            yield from _texts(c)


def scaled(g, t, key, base, name):
    """bind a LayoutParticipant size to base x _bigK: short canvases shrink the display type
    (headlines and hero numbers, through fitFontSize), never the body copy"""
    lp = child(t, "LayoutParticipant")
    f = g.formula(name, g.INPUT(), g.op("*"), g.tv(base))
    lp.add(bind(g.p("_bigK"), key, f.id))
    return t


def art_text_floor(g, t, ratio, name):
    """text drawn in art-stage units shrinks with the art; scale it back up so it never
    falls under `ratio` x its authored size on screen: scale = max(1, ratio / _artScale)"""
    f = g.formula(name, g.fn("max"), g.tv(1), g.SEP(), g.tv(ratio), g.op("/"), g.INPUT(), g.CLOSE())
    t.add(bind(g.p("_artScale"), 16, f.id), bind(g.p("_artScale"), 17, f.id))
    return t


def key_reveal(a: Anim, t: E, start: int, dur: int):
    rg = t.range
    a.k(rg, "modifyFrom", (0, -0.35, "hold"), (start, -0.35, "out"), (start + dur, 1.0, "hold"))
    a.k(rg, "falloffFrom", (0, 0.0, "hold"), (start, 0.0, "out"), (start + dur, 1.3, "hold"))


def finalize_scene(g, sc: Scene):
    n = sc.n
    L = Layer(f"Scene {n}")
    roots = [r for r in (sc.copy, sc.front, sc.back, *sc.extra_roots) if r is not None]

    hidden = L.anim(f"S{n} Hidden", 1)
    for r in roots:
        hidden.k(r, "opacity", (0, 0.0, "hold"))
    for inp in sc.live_inputs:
        hidden.k(inp, "propertyValue", (0, 0.0, "hold"))

    enterF = L.anim(f"S{n} Enter", ENTER + 72 if n in (4, 5, 7) else ENTER)
    if sc.copy is not None:
        enterF.k(sc.copy, "opacity", (0, 1.0, "hold"))
    for r in (sc.front, sc.back, *sc.extra_roots):
        enterF.k(r, "opacity", (0, 0.0, "hold"), (2, 0.0, "out"), (18, 1.0, "hold"))
    for (t, st, du) in sc.reveals:
        key_reveal(enterF, t, st, du)
    for fn in sc.hooks["enterF"]:
        fn(enterF)

    enterB = L.anim(f"S{n} Enter Back", 60)
    for r in (sc.front, sc.back, *sc.extra_roots):
        enterB.k(r, "opacity", (0, 0.0, "hold"), (4, 0.0, "out"), (30, 1.0, "hold"))
    if sc.copy is not None:
        # the outgoing copy clears first; the returning copy drops back in from above
        enterB.k(sc.copy, "opacity", (0, 0.0, "hold"), (20, 0.0, "out"), (40, 1.0, "hold"))
        enterB.k(sc.copy, "y", (0, -40.0, "hold"), (20, -40.0, "back"), (52, 0.0, "hold"))
    for fn in sc.hooks["enterB"]:
        fn(enterB)

    enterRM = L.anim(f"S{n} Enter Reduced", 14)
    for r in roots:
        enterRM.k(r, "opacity", (0, 0.0, "lin"), (14, 1.0, "hold"))

    idle = L.anim(f"S{n} Idle", sc.idle_frames, loop="loop")
    for fn in sc.hooks["idle"]:
        fn(idle)
    frozen = L.anim(f"S{n} Frozen", 1, exempt=True)

    exitF = L.anim(f"S{n} Exit", EXIT)
    exitB = L.anim(f"S{n} Exit Back", EXIT)
    for a, d in ((exitF, -1), (exitB, 1)):
        if sc.copy is not None:
            # the copy rewinds: each line sweeps out glyph by glyph, top line first, while the
            # column drifts away from the incoming scene; a short fade guarantees a clean end
            a.k(sc.copy, "y", (0, 0.0, "in"), (24, 26.0 * d, "hold"))
            a.k(sc.copy, "opacity", (0, 1.0, "hold"), (12, 1.0, "in"), (24, 0.0, "hold"))
            order = sorted(sc.reveals, key=lambda r: r[1])
            for j, (t, st0, du) in enumerate(order):
                f0 = min(j * 3, 10)
                a.k(t.range, "modifyFrom", (0, 1.0, "hold"), (f0, 1.0, "in"), (f0 + 14, -0.35, "hold"))
                a.k(t.range, "falloffFrom", (0, 1.3, "hold"), (f0, 1.3, "in"), (f0 + 14, 0.0, "hold"))
        for r in (sc.front, sc.back, *sc.extra_roots):
            a.k(r, "opacity", (0, 1.0, "soft"), (22, 0.0, "hold"))
    for fn in sc.hooks["exitF"]:
        fn(exitF)
    for fn in sc.hooks["exitB"]:
        fn(exitB)
    exitRM = L.anim(f"S{n} Exit Reduced", 10)
    for r in roots:
        exitRM.k(r, "opacity", (0, 1.0, "lin"), (10, 0.0, "hold"))

    scene_states(g, n, L, dict(hidden=hidden, enterF=enterF, enterB=enterB, enterRM=enterRM, idle=idle,
                               frozen=frozen, exitF=exitF, exitB=exitB, exitRM=exitRM))
    g.layers.append(L)


# ---------------------------------------------------------------------------
# shared copy pieces


HEAD_LINES = {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 3}


def headline(sc, prop, literal, size=48, align="left", start=72):
    g = sc.g
    t = g.text(f"S{sc.n} Headline", g.serif_style(size, sc.ink, lh=size * 1.04), literal, prop=prop, align=align)
    # long or localized headlines shrink to a fixed number of lines rather than pushing into the art
    lp = child(t, "LayoutParticipant")
    mh = float(size * 1.04 * HEAD_LINES.get(sc.n, 2) + 4)
    lp.attrs["maxHeight"] = mh
    lp.attrs["maxHeightUnitsValue"] = "points"
    t.attrs["overflowValue"] = "fitFontSize"
    t.attrs["wordBreakValue"] = "normal"   # never split a word; shrink instead
    scaled(g, t, 501, mh, f"Headline {sc.n} Max")
    if sc.n != 6:
        # fitFontSize keeps the box at its max height; where the headline sits above the number,
        # a short headline in a wide column is set at the bottom of it (landscape), so the
        # reserved space never opens a gap between headline and number
        t.add(bind(g.p("_headVA"), 685))
    return sc.reveal(t, start, 30)


def max_w(t, w):
    """keep long localized copy clear of the hero art beside it"""
    if w:
        lp = child(t, "LayoutParticipant")
        lp.attrs["maxWidth"] = float(w)
        lp.attrs["maxWidthUnitsValue"] = "points"
    return t


def support(sc, prop, literal, size=16, align="left", start=86, alpha=0.86, width=None):
    g = sc.g
    st = g.sans_style(size, sc.ink, 500, lh=size * 1.4)
    child(child(st, "Fill"), "SolidColor").attrs["colorValue"] = argb(sc.ink, alpha)
    t = g.text(f"S{sc.n} Support", st, literal, prop=prop, align=align)
    return sc.reveal(max_w(t, width), start, 24)


def hero_number(sc, stat, literal, decimals=0, size=120, align="left", start=12, layout=True, x=0.0, y=0.0,
                origin=None):
    g = sc.g
    conv = g.count_converter(sc.n, decimals)
    t = g.text(f"S{sc.n} Number", g.serif_style(size, sc.ink, lh=size * 0.98), literal, prop=stat, conv=conv,
               width="fill" if layout else None, align=align, layout=layout, x=x, y=y, origin=origin, nowrap=True,
               height=size * 1.0 if layout else None)
    # very large or long localized values shrink to fit the column instead of overflowing
    t.attrs["overflowValue"] = "fitFontSize"
    t.attrs["verticalAlignValue"] = "bottom"
    if layout and sc.n in (2, 4, 8):
        lp = child(t, "LayoutParticipant")
        lp.attrs["maxWidth"] = 230.0      # keep the numeral clear of the hero art on the right
        lp.attrs["maxWidthUnitsValue"] = "points"
    if layout:
        scaled(g, t, 1067, size * 1.0, f"Number {sc.n} Height")
    if not layout:
        t.attrs["width"] = 340.0
        t.attrs["height"] = float(size)
        t.attrs["sizingValue"] = "fixed"
    return sc.reveal(t, start, 26)


def unit(sc, prop, literal, size=20, align="left", start=48, weight=600, layout=True, width=None, x=0.0, y=0.0,
         origin=None):
    g = sc.g
    t = g.text(f"S{sc.n} Unit", g.sans_style(size, sc.ink, weight, lh=size * 1.3), literal, prop=prop, align=align,
               layout=layout, width=width if width else "fill", x=x, y=y, origin=origin)
    return sc.reveal(t, start, 26)


# ---------------------------------------------------------------------------
# scene 1 -- invitation


def scene1(g, sc):
    ink = sc.ink
    st = g.sans_style(15, ink, 700, spacing=0.4)
    name = g.text("S1 Name", st, "Alex", prop="userName", ellipsis=True, nowrap=True, height=22)
    sc.reveal(name, 10, 24)
    head = headline(sc, "introHeadline", "Your 2026 on Kiln", size=52, start=24)
    sup = support(sc, "introSupport", "A year, uniquely yours.", size=17, start=46)
    pst = g.sans_style(13, ink, 600, spacing=0.3)
    child(child(pst, "Fill"), "SolidColor").attrs["colorValue"] = argb(ink, 0.62)
    period = sc.reveal(g.text("S1 Period", pst, "January 1–December 31, 2026", prop="periodLabel"), 60, 24)
    sc.copy_box(name, head, sup, period, gap=8)

    # the wordmark, revealed through a disc that opens from the vessel
    disc = S(shape("Reveal Disc", 195, 300, ellipse(80, 80)), scaleX=6.5, scaleY=6.5)
    word = g.text("Giant Wordmark", g.serif_style(184, ULTRA), "Kiln", reveal=False, layout=False, x=195, y=112,
                  origin=(0.5, 0.5))
    S(word, y=112.0, opacity=1.0)
    reveal_node = node("Wordmark Reveal", 0, 0, E("ClippingShape", {"sourceId": disc.id, "name": "Clip"}), word)
    rings = []
    for i, (w, h) in enumerate(((300, 70), (356, 86), (420, 104))):
        tr = E("TrimPath", {"start": 0.0, "end": 1.0, "name": "Trim"})
        settle(tr, "end", 1.0)
        dash = [3, 9] if i == 2 else None
        s = stroke(ink, 1.2, alpha=0.16 if i < 2 else 0.22, dash=dash)
        s.add(tr)
        r = S(shape(f"Ring {i}", 195, 424, ellipse(w, h), s), scaleX=1.0, scaleY=1.0, opacity=1.0)
        r.trim = tr
        rings.append(r)
    dash_path = child(child(rings[2], "Stroke"), "DashPath")
    S(dash_path, offset=0.0)
    hint_st = g.sans_style(11, CHAR, 700, spacing=1.6)
    child(child(hint_st, "Fill"), "SolidColor").attrs["colorValue"] = argb(CHAR, 0.5)
    hint = g.text("Turntable Hint", hint_st, "Drag to turn", prop="turntableHint", reveal=False, layout=False,
                  x=195, y=452, origin=(0.5, 0.5))
    S(hint, opacity=1.0)
    art_text_floor(g, hint, 1.0, "Hint Floor")
    # on small canvases the plinth face (and the hint on it) drops behind the footer: hide it
    hint_holder = node("Hint Holder", 0, 0, hint)
    hint_holder.add(bind(g.p("_hintOn"), 18))
    sc.front.add(hint_holder)
    sc.back.add(reveal_node, disc, *rings)

    def enter(a):
        a.k(disc, "scaleX", (0, 0.0, "hold"), (40, 0.0, "out"), (100, 6.5, "hold"))
        a.k(disc, "scaleY", (0, 0.0, "hold"), (40, 0.0, "out"), (100, 6.5, "hold"))
        a.k(word, "y", (0, 172.0, "hold"), (40, 172.0, "out"), (104, 112.0, "hold"))
        for i, r in enumerate(rings):
            a.k(r.trim, "end", (0, 0.0, "hold"), (6 + i * 10, 0.0, "out"), (56 + i * 10, 1.0, "hold"))
        a.k(hint, "opacity", (0, 0.0, "hold"), (96, 0.0, "out"), (108, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(dash_path, "offset", (0, 0.0, "lin"), (240, -120.0, "hold"))
    sc.on("idle", idle)

    def exitF(a):
        a.k(word, "y", (0, 112.0, "in"), (34, 52.0, "hold"))
        for r in rings:
            a.k(r, "scaleX", (0, 1.0, "in"), (30, 0.4, "hold")).k(r, "scaleY", (0, 1.0, "in"), (30, 0.4, "hold"))
    sc.on("exitF", exitF)


# ---------------------------------------------------------------------------
# scene 2 -- pieces made


def scene2(g, sc):
    head = headline(sc, "screen2Headline", "You gave ideas a shape.", size=48)
    num = hero_number(sc, "piecesMade", "0")
    un = max_w(unit(sc, "screen2Unit", "pieces made"), 230)
    sup = support(sc, "screen2Support", "A year worked by hand.", width=205)
    sc.copy_box(head, num, un, sc.spacer(4), sup, gap=4)

    rock = S(shape("Rock", 0, 0,
                   poly([(-50, 480), (-50, 250), (22, 178), (118, 150), (196, 214), (236, 316), (226, 480)], radius=10),
                   fill("A3573F")), x=0.0, opacity=1.0)
    facet = shape("Rock Facet", 0, 0, poly([(22, 178), (118, 150), (140, 214), (60, 246)], radius=6), fill("B9694F"))
    shadow_face = shape("Rock Shadow", 0, 0, poly([(140, 214), (196, 214), (236, 316), (226, 480), (150, 480)], radius=6),
                        fill("8E4A35"))
    rock_g = S(node("Rock Group", 0, 0, facet, shadow_face, rock), x=0.0, opacity=1.0)
    twig_parts = []
    for i, pts in enumerate([[(296, 120), (318, 60), (340, 10), (352, -40)], [(318, 60), (356, 40), (372, 22)],
                             [(340, 10), (316, -16), (308, -34)]]):
        tr = E("TrimPath", {"start": 0.0, "end": 1.0, "name": "Trim"})
        settle(tr, "end", 1.0)
        s = stroke("5A3426", 2.2 - i * 0.4)
        s.add(tr)
        p = E("PointsPath", {"isClosed": False, "name": "Stem"})
        for (x, y, r, d) in smooth_vertices(pts, closed=False, tension=0.2):
            p.add(E("CubicMirroredVertex", {"x": float(x), "y": float(y), "rotation": float(r), "distance": float(d)}))
        sh = shape(f"Twig {i}", 0, 0, p, s)
        sh.trim = tr
        twig_parts.append(sh)
    buds = [S(shape(f"Bud {i}", x, y, ellipse(9, 11), fill("6E4130")), scaleX=1.0, scaleY=1.0)
            for i, (x, y) in enumerate([(352, -42), (373, 20), (307, -36), (330, 32)])]
    twig = S(node("Twig", 0, 0, *buds, *twig_parts), rotation=0.0)
    sc.back.add(twig, rock_g)

    def enter(a):
        a.k(rock_g, "x", (0, -90.0, "hold"), (8, -90.0, "out"), (70, 0.0, "hold"))
        a.k(rock_g, "opacity", (0, 0.0, "hold"), (8, 0.0, "out"), (40, 1.0, "hold"))
        for i, t in enumerate(twig_parts):
            a.k(t.trim, "end", (0, 0.0, "hold"), (60 + i * 12, 0.0, "out"), (100 + i * 12, 1.0, "hold"))
        for i, b in enumerate(buds):
            f0 = 96 + i * 8
            a.k(b, "scaleX", (0, 0.0, "hold"), (f0, 0.0, "back"), (f0 + 20, 1.0, "hold"))
            a.k(b, "scaleY", (0, 0.0, "hold"), (f0, 0.0, "back"), (f0 + 20, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(twig, "rotation", (0, 0.0, "inout"), (120, 0.03, "inout"), (240, 0.0, "hold"))
    sc.on("idle", idle)

    def exitF(a):
        a.k(rock_g, "x", (0, 0.0, "in"), (EXIT, -70.0, "hold"))
    sc.on("exitF", exitF)


# ---------------------------------------------------------------------------
# scene 3 -- studio hours


def scene3(g, sc):
    head = headline(sc, "screen3Headline", "Time well shaped.", size=44, align="center")
    sup = support(sc, "screen3Support", "Your practice found its own pace.", align="center")
    sc.copy_box(head, sup, align="topCenter", gap=10)

    num = hero_number(sc, "studioHours", "0", size=168, align="center", layout=False, x=195, y=128,
                      origin=(0.5, 0.5))
    un = unit(sc, "screen3Unit", "studio hours", size=18, align="center", layout=False, width=300, x=195, y=274,
              origin=(0.5, 0.0))
    art_text_floor(g, un, 15.0 / 18.0, "Hours Unit Floor")

    def ring(name, w, h, start, end, alpha, thick, dash=None):
        tr = E("TrimPath", {"start": float(start), "end": float(end), "name": "Trim"})
        settle(tr, "end", float(end))
        settle(tr, "start", float(start))
        s = stroke(PORC, thick, alpha=alpha, dash=dash)
        s.add(tr)
        sh = S(shape(name, 195, 214, ellipse(w, h), s), scaleX=1.0, scaleY=1.0)
        sh.trim = tr
        return sh

    front_arc = ring("Ring Front", 344, 96, 0.0, 0.5, 1.0, 2.4)
    back_arc = ring("Ring Back", 344, 96, 0.5, 1.0, 0.55, 2.4)
    ticks = ring("Hour Ticks", 300, 80, 0.0, 1.0, 0.45, 1.4, dash=[2, 12])
    dp = child(child(ticks, "Stroke"), "DashPath")
    S(dp, offset=0.0)
    sc.front.add(front_arc, num, un, back_arc, ticks)

    def enter(a):
        a.k(front_arc.trim, "end", (0, 0.0, "hold"), (10, 0.0, "out"), (64, 0.5, "hold"))
        a.k(back_arc.trim, "end", (0, 0.5, "hold"), (40, 0.5, "out"), (92, 1.0, "hold"))
        a.k(ticks, "scaleX", (0, 0.6, "hold"), (20, 0.6, "out"), (90, 1.0, "hold"))
        a.k(ticks, "scaleY", (0, 0.6, "hold"), (20, 0.6, "out"), (90, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(dp, "offset", (0, 0.0, "lin"), (240, -140.0, "hold"))
    sc.on("idle", idle)

    def exitF(a):
        a.k(front_arc.trim, "end", (0, 0.5, "in"), (30, 0.0, "hold"))
        a.k(back_arc.trim, "end", (0, 1.0, "in"), (30, 0.5, "hold"))
    sc.on("exitF", exitF)


# ---------------------------------------------------------------------------
# scene 4 -- glaze tests


TILE = 76
GAP = 12


def tile(i, cx, cy):
    """returns (tile node, glaze node to key)"""
    kind = i
    sh = 4.0
    if kind in (1, 6):
        geo = lambda: ellipse(TILE, TILE)  # noqa: E731
    else:
        geo = lambda: rect(TILE, TILE, 9)  # noqa: E731
    body = shape(f"Tile {i} Body", 0, 0, geo(), fill("F4EEE5"), stroke("E2D8CA", 1.0))
    side = shape(f"Tile {i} Edge", 0, 4.5, geo(), fill("D2C5B3"))
    shadow = shape(f"Tile {i} Shadow", 4, 10, geo(), fill(CHAR, alpha=0.2, feather=10))
    half = TILE / 2
    glazes = {
        0: [poly([(-half, -half), (12, -half), (2, -8), (-14, 6), (-half, 14)], radius=8)],
        1: [rect(TILE, half + 4, 0, oy=0.0)],
        2: [rect(TILE, 22, 0, oy=0.0), rect(9, 44, 4, ox=0.5, oy=0.0), rect(8, 30, 4, oy=0.0)],
        3: [poly([(-half, -half), (half, -half), (-half, half)])],
        4: [rect(TILE - 14, TILE - 14, 6)],
        5: [ellipse(TILE, TILE)],
        6: [poly([(-half, half), (half, -half), (half, half)])],
        7: [rect(TILE, 18, 0, oy=0.0), rect(10, 52, 5, oy=0.0), rect(8, 40, 4, oy=0.0), rect(9, 60, 4, oy=0.0)],
        8: [ellipse(10, 10), ellipse(7, 7), ellipse(12, 12), ellipse(6, 6), ellipse(9, 9)],
    }[kind]
    # position the pieces
    gl_children = []
    offs = {
        1: [(0, 0)], 2: [(0, 0), (-18, 0), (16, 0)], 5: [(half, -half)],
        7: [(0, 0), (-22, 0), (2, 0), (24, 0)], 8: [(-14, -10), (12, -18), (8, 14), (-18, 18), (20, 2)],
    }.get(kind, [(0, 0)] * len(glazes))
    for j, (geo_el, (ox, oy)) in enumerate(zip(glazes, offs)):
        if geo_el.tag in ("Rectangle", "Ellipse"):
            geo_el.attrs["x"] = float(ox)
            geo_el.attrs["y"] = float(oy + (half if kind in (1,) else 0))
        gl_children.append(geo_el)
    if kind in (1, 2, 7):
        # rectangles with originY=0 hang from the tile's top edge
        for geo_el in gl_children:
            if geo_el.tag == "Rectangle":
                geo_el.attrs["y"] = float(-half + (0 if kind != 1 else half - 4)) if geo_el.attrs.get("originY") == 0.0 else geo_el.attrs.get("y", 0.0)
    gshape = shape(f"Tile {i} Glaze", 0, half, *gl_children, fill(ULTRA if kind != 4 else "2C3D93"),
                   stroke("1F2C7A", 1.2, alpha=0.5))
    gnode = S(node(f"Tile {i} Glaze Flow", 0, -half, gshape), scaleY=1.0)
    # wet-glaze gloss: a soft window reflection that only lands on the glaze
    gloss = node(f"Tile {i} Gloss", 0, 0, E("ClippingShape", {"sourceId": gshape.id, "name": "Clip"}),
                 shape(f"Tile {i} Shine", -12, -18, ellipse(34, 13), fill("FFFFFF", alpha=0.42, feather=5)),
                 shape(f"Tile {i} Rim Light", 14, 22, ellipse(40, 8), fill("8EA0EE", alpha=0.35, feather=6)))
    clip = node(f"Tile {i} Surface", 0, 0, E("ClippingShape", {"sourceId": body.id, "name": "Clip"}), gloss, gnode)
    t = S(node(f"Tile {i}", cx, cy, clip, body, side, shadow), scaleX=1.0, scaleY=1.0, opacity=1.0, y=float(cy))
    return t, gnode


def scene4(g, sc):
    head = headline(sc, "screen4Headline", "Curiosity, fired.", size=48)
    num = hero_number(sc, "glazeTests", "0")
    un = unit(sc, "screen4Unit", "glaze tests")
    sup = support(sc, "screen4Support", "Small experiments. Unexpected color.", width=172)
    sc.copy_box(head, num, un, sc.spacer(4), sup, right=150, gap=4)

    tiles = []
    x0 = 195 - (TILE + GAP)
    y0 = 236
    order = [1, 0, 2, 4, 3, 5, 7, 6, 8]
    for k in range(9):
        r, c = divmod(k, 3)
        t, gl = tile(k, x0 + c * (TILE + GAP), y0 + r * (TILE + GAP))
        tiles.append((t, gl, order[k]))
    grid = node("Tile Grid", 0, 0, *[t for t, _, _ in tiles])
    # pour stream from the jug lip into the top-centre tile
    tr = E("TrimPath", {"start": 0.0, "end": 1.0, "name": "Trim"})
    settle(tr, "start", 1.0, set_attr=True)
    settle(tr, "end", 1.0)
    sp = E("PointsPath", {"isClosed": False, "name": "Stream"})
    for (x, y, r_, d) in smooth_vertices([(238, 150), (216, 178), (206, 210)], closed=False, tension=0.25):
        sp.add(E("CubicMirroredVertex", {"x": float(x), "y": float(y), "rotation": float(r_), "distance": float(d)}))
    stream_stroke = stroke(ULTRA, 9.0)
    stream_stroke.add(tr)
    stream = shape("Glaze Stream", 0, 0, sp, stream_stroke)
    drops = [S(shape(f"Drop {i}", x, 0, ellipse(8, 11), fill(ULTRA)), y=float(y), opacity=0.0)
             for i, (x, y) in enumerate([(124, 492), (200, 500), (276, 488)])]
    sc.front.add(stream)
    sc.back.add(*drops, grid)

    def enter(a):
        for k, (t, gl, o) in enumerate(tiles):
            f0 = 4 + k * 4
            a.k(t, "opacity", (0, 0.0, "hold"), (f0, 0.0, "out"), (f0 + 20, 1.0, "hold"))
            a.k(t, "y", (0, t.attrs["y"] + 26, "hold"), (f0, t.attrs["y"] + 26, "back"), (f0 + 30, t.attrs["y"], "hold"))
            g0 = 104 + o * 10
            a.k(gl, "scaleY", (0, 0.0, "hold"), (g0, 0.0, "heavy"), (g0 + 34, 1.0, "hold"))
        a.k(tr, "end", (0, 0.0, "hold"), (92, 0.0, "out"), (108, 1.0, "hold"))
        a.k(tr, "start", (0, 0.0, "hold"), (150, 0.0, "in"), (172, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        for i, d in enumerate(drops):
            f0 = i * 50
            y0_ = d.attrs["y"]
            a.k(d, "y", (0, y0_, "hold"), (f0, y0_, "in"), (f0 + 40, y0_ + 34, "hold"))
            a.k(d, "opacity", (0, 0.0, "hold"), (f0, 0.0, "lin"), (f0 + 6, 0.9, "lin"), (f0 + 40, 0.0, "hold"))
    sc.on("idle", idle)

    def exitF(a):
        for k, (t, gl, o) in enumerate(tiles):
            a.k(t, "scaleY", (0, 1.0, "in"), (24 + k, 0.2, "hold"))
            a.k(t, "scaleX", (0, 1.0, "in"), (24 + k, 1.3, "hold"))
    sc.on("exitF", exitF)


# ---------------------------------------------------------------------------
# scene 5 -- firings

GLOW = ["FFE3A3", "FFC46E", "F9A04F", "EE7B3E", "D9592F", "B54128"]
COOL = [PORC, "E3CDB4", "C99A7E", CLAY, "5C6CB8", ULTRA]


def scene5(g, sc):
    head = headline(sc, "screen5Headline", "Into the heat.", size=46, align="center")
    num = hero_number(sc, "firings", "0", size=112, align="center")
    un = unit(sc, "screen5Unit", "firings", align="center")
    sup = support(sc, "screen5Support", "Each firing wrote a different ending.", align="center")
    sc.copy_box(head, num, un, sup, align="topCenter", gap=4)

    arch_geo = lambda: E("Rectangle", {"width": 300.0, "height": 380.0, "originX": 0.5, "originY": 0.0,  # noqa: E731
                                       "linkCornerRadius": False, "cornerRadiusTL": 150.0, "cornerRadiusTR": 150.0,
                                       "cornerRadiusBL": 6.0, "cornerRadiusBR": 6.0, "name": "Arch"})
    arch = shape("Kiln Arch", 195, 112, arch_geo(), fill("1C1816"))
    bands = []
    for i in range(6):
        c = solid("2A2422", name="Band")
        settle(c, "colorValue", argb(COOL[i]), set_attr=False)
        c.attrs["colorValue"] = argb(COOL[i])
        b = shape(f"Band {i}", 195, 150 + i * 58, rect(300, 58.5, 0), E("Fill", {"name": "Fill"}, c))
        bands.append(c)
        bands_shape = b
        bands.append(b)
    band_colors = bands[0::2]
    band_shapes = bands[1::2]
    # the chamber itself is a WGSL shader (scripts/kiln.wgsl); the vector bands under it are the
    # fallback for runtimes without GPU scripting
    fire = E("ScriptInputNumber", {"propertyValue": 2.0, "name": "fire"})
    settle(fire, "propertyValue", 2.0)
    live = E("ScriptInputNumber", {"propertyValue": 1.0, "name": "live"})
    settle(live, "propertyValue", 1.0)
    chamber = E("ScriptedDrawable", {"x": 45.0, "y": 112.0, "scriptAssetId": g.kiln_script.id, "name": "Kiln Fire"},
                fire, live,
                E("ScriptInputBoolean", {"propertyValue": False, "name": "still"}, bind(g.p("_frozen"), 245)),
                E("ScriptInputNumber", {"propertyValue": 300.0, "name": "w"}),
                E("ScriptInputNumber", {"propertyValue": 380.0, "name": "h"}),
                E("ScriptInputNumber", {"propertyValue": 1.5, "name": "res"}),
                E("ScriptInputNumber", {"propertyValue": 1.0, "name": "zoom"}, bind(g.p("_artScale"), 243)),
                E("ScriptInputNumber", {"propertyValue": 1.0, "name": "dpr"}, bind(g.p("_dpr"), 243)))
    sc.live_inputs.append(live)
    band_clip = node("Kiln Chamber", 0, 0, E("ClippingShape", {"sourceId": arch.id, "name": "Clip"}), chamber,
                     *band_shapes)
    glow = S(shape("Heat Glow", 195, 250, ellipse(360, 420), fill("F08A3C", alpha=0.9, feather=60)), opacity=0.25)
    rim = shape("Arch Rim", 195, 112, arch_geo(), stroke(PORC, 1.5, alpha=0.16))
    sc.front.add(rim)
    sc.back.add(band_clip, arch, glow)

    def enter(a):
        for i, c in enumerate(band_colors):
            j = 5 - i  # heat rises from the floor
            a.k(c, "colorValue", (0, "2A2422", "hold"), (10 + j * 6, "2A2422", "lin"), (46 + j * 6, GLOW[i], "lin"),
                (96 + i * 8, GLOW[i], "lin"), (150 + i * 8, COOL[i], "hold"))
        a.k(glow, "opacity", (0, 0.0, "hold"), (10, 0.0, "out"), (56, 0.9, "lin"), (100, 0.9, "soft"), (170, 0.25, "hold"))
        a.k(fire, "propertyValue", (0, 0.0, "hold"), (8, 0.0, "in"), (78, 1.0, "soft"), (108, 1.0, "inout"),
            (176, 2.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(glow, "opacity", (0, 0.25, "inout"), (120, 0.36, "inout"), (240, 0.25, "hold"))
    sc.on("idle", idle)


# ---------------------------------------------------------------------------
# scene 6 -- clay reclaimed

SHARDS = [
    ([(-30, -18), (26, -24), (34, 10), (-16, 22)], (-40, 60), 0.9, (150, 418), "C47D61"),
    ([(-22, -26), (30, -8), (6, 26)], (420, 120), -1.4, (240, 420), "A9614A"),
    ([(-34, -10), (18, -30), (30, 18), (-8, 24)], (-60, 330), 2.1, (110, 430), "B86E52"),
    ([(-20, -20), (24, -16), (20, 22), (-24, 14)], (430, 300), -2.4, (282, 432), "D19378"),
    ([(-26, -12), (28, -20), (12, 24)], (190, -80), 1.2, (196, 300), "A55C45"),
    ([(-18, -24), (20, -20), (26, 16), (-20, 20)], (40, 520), -0.7, (128, 444), "C98468"),
    ([(-24, -14), (26, -22), (18, 20), (-14, 18)], (360, 520), 0.5, (262, 446), "B26A4F"),
]


def scene6(g, sc):
    num = hero_number(sc, "clayReclaimedKg", "0.0", decimals=1, size=116)
    un = unit(sc, "screen6Unit", "kg clay reclaimed", start=46)
    head = headline(sc, "screen6Headline", "Back to possibility.", size=40)
    sup = support(sc, "screen6Support", "Material ready for another beginning.")
    sc.copy_box(num, un, sc.spacer(10), head, sup, gap=4)

    shards = []
    for i, (pts, start, rot, end, col) in enumerate(SHARDS):
        sh = shape(f"Shard {i}", 0, 0, poly(pts, radius=3), fill(col), stroke("8E4A35", 1.0, alpha=0.5))
        nd = S(node(f"Shard {i} Pivot", end[0], end[1], sh), x=float(end[0]), y=float(end[1]), rotation=rot * 0.1,
               scaleX=0.0, scaleY=0.0)
        nd.start = start
        nd.rot = rot
        shards.append(nd)
    halo = S(shape("Halo", 195, 380, ellipse(330, 330), fill("FFFFFF", alpha=0.35, feather=40)), scaleX=1.0, scaleY=1.0)
    sc.front.add(*shards)
    sc.back.add(halo)

    def enter(a):
        for i, nd in enumerate(shards):
            sx, sy = nd.start
            ex, ey = nd.attrs["x"], nd.attrs["y"]
            f0 = 4 + i * 6
            # fly in tumbling, hang for a beat at the edge of the mound, then merge into it
            a.k(nd, "x", (0, sx, "hold"), (f0, sx, "out"), (f0 + 38, ex, "in"), (f0 + 58, 195.0, "hold"))
            a.k(nd, "y", (0, sy, "hold"), (f0, sy, "out"), (f0 + 38, ey, "in"), (f0 + 58, 392.0, "hold"))
            a.k(nd, "rotation", (0, nd.rot, "hold"), (f0, nd.rot, "out"), (f0 + 58, nd.rot * 0.1, "hold"))
            a.k(nd, "scaleX", (0, 1.0, "hold"), (f0, 1.0, "out"), (f0 + 38, 0.7, "in"), (f0 + 58, 0.0, "hold"))
            a.k(nd, "scaleY", (0, 1.0, "hold"), (f0, 1.0, "out"), (f0 + 38, 0.7, "in"), (f0 + 58, 0.0, "hold"))
        a.k(halo, "scaleX", (0, 0.4, "hold"), (40, 0.4, "out"), (110, 1.0, "hold"))
        a.k(halo, "scaleY", (0, 0.4, "hold"), (40, 0.4, "out"), (110, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(halo, "scaleX", (0, 1.0, "inout"), (120, 1.06, "inout"), (240, 1.0, "hold"))
        a.k(halo, "scaleY", (0, 1.0, "inout"), (120, 1.06, "inout"), (240, 1.0, "hold"))
    sc.on("idle", idle)


# ---------------------------------------------------------------------------
# scene 7 -- forms explored


def scene7(g, sc):
    head = headline(sc, "screen7Headline", "One material. Many voices.", size=42, align="center")
    num = hero_number(sc, "formsExplored", "0", size=100, align="center")
    un = unit(sc, "screen7Unit", "forms explored", align="center")
    sup = support(sc, "screen7Support", "Bowls, cups, vases, and your own ideas.", align="center")
    sc.copy_box(head, num, un, sup, align="topCenter", gap=4)

    icons = []
    times = [52, 94, 134, 174, 214, 254]
    for k, prof in enumerate(MF.SEVEN):
        h = MF.profile_height(prof)
        sc_ = 40.0 / max(h, 120)
        p, _ = smooth_path(MF.profile_vertices(prof), closed=True, name="Profile")
        fc = solid(PORC, alpha=0.0)
        settle(fc, "colorValue", argb(PORC, 0.95), set_attr=False)
        fc.attrs["colorValue"] = argb(PORC, 0.95)
        ic = shape(f"Form {k}", 0, 0, p, E("Fill", {"name": "Fill"}, fc), stroke(PORC, 1.4 / sc_, alpha=0.7))
        nd = S(node(f"Form {k} Slot", 44, 160 + k * 52, ic, scaleX=sc_, scaleY=sc_), y=float(160 + k * 52))
        nd.attrs["scaleX"] = sc_
        nd.attrs["scaleY"] = sc_
        icons.append((nd, fc, times[k]))
    sc.front.add(*[i for i, _, _ in icons])

    def enter(a):
        for k, (nd, fc, t) in enumerate(icons):
            a.k(fc, "colorValue", (0, argb(PORC, 0.0), "hold"), (t, argb(PORC, 0.0), "lin"), (t + 14, argb(PORC, 0.95), "hold"))
            y = nd.attrs["y"]
            a.k(nd, "y", (0, y + 20, "hold"), (4 + k * 5, y + 20, "out"), (34 + k * 5, y, "hold"))
    sc.on("enterF", enter)


# ---------------------------------------------------------------------------
# scene 8 -- pieces gifted


def scene8(g, sc):
    head = headline(sc, "screen8Headline", "Made by you. Held by someone.", size=44)
    num = hero_number(sc, "piecesGifted", "0")
    un = unit(sc, "screen8Unit", "pieces gifted")
    sup = support(sc, "screen8Support", "Your work found a place in everyday life.")
    sc.copy_box(head, num, un, sc.spacer(4), sup, gap=4)

    def petal(name, pts, fold, rot, col="FBF8F3"):
        body = shape(f"{name} Paper", 0, 0, poly(pts, radius=4), fill(col), stroke("D6C8B5", 1.0))
        crease = shape(f"{name} Fold", 0, 0, poly(fold, radius=2), fill("ECE2D4"))
        return S(node(name, 195, 446, crease, body), rotation=rot)

    back_l = petal("Wrap Left", [(-6, 0), (-118, -150), (-52, -184), (14, -24)], [(-6, 0), (-52, -184), (14, -24)], -0.12)
    back_r = petal("Wrap Right", [(6, 0), (118, -150), (52, -184), (-14, -24)], [(6, 0), (52, -184), (-14, -24)], 0.12)
    front = S(node("Wrap Front", 195, 446,
                   shape("Front Paper", 0, 0, poly([(-78, 0), (-70, -84), (0, -96), (72, -86), (80, 0)], radius=5),
                         fill("F8F3EC"), stroke("D6C8B5", 1.0)),
                   shape("Front Fold", 0, 0, poly([(-70, -84), (0, -96), (-6, -40)], radius=3), fill("EDE4D7"))),
              scaleY=1.0, rotation=0.0)
    tr = E("TrimPath", {"start": 0.0, "end": 1.0, "name": "Trim"})
    settle(tr, "end", 1.0)
    tw = stroke(CLAY, 2.4)
    tw.add(tr)
    tp = E("PointsPath", {"isClosed": False, "name": "Twine"})
    for (x, y, r_, d) in smooth_vertices([(-74, -52), (-20, -60), (0, -58), (-18, -82), (4, -66), (22, -84), (2, -56), (40, -62), (76, -56)],
                                         closed=False, tension=0.22):
        tp.add(E("CubicMirroredVertex", {"x": float(x), "y": float(y), "rotation": float(r_), "distance": float(d)}))
    twine = shape("Twine", 195, 446, tp, tw)
    glow = S(shape("Gift Glow", 195, 360, ellipse(320, 300), fill(CLAY, alpha=0.22, feather=50)), opacity=1.0)
    sc.front.add(twine, front)
    sc.back.add(back_l, back_r, glow)

    def enter(a):
        a.k(back_l, "rotation", (0, -1.45, "hold"), (40, -1.45, "back"), (86, -0.12, "hold"))
        a.k(back_r, "rotation", (0, 1.45, "hold"), (46, 1.45, "back"), (92, 0.12, "hold"))
        a.k(front, "scaleY", (0, 0.0, "hold"), (60, 0.0, "back"), (100, 1.0, "hold"))
        a.k(tr, "end", (0, 0.0, "hold"), (96, 0.0, "out"), (132, 1.0, "hold"))
        a.k(glow, "opacity", (0, 0.0, "hold"), (60, 0.0, "out"), (120, 1.0, "hold"))
    sc.on("enterF", enter)

    def idle(a):
        a.k(glow, "opacity", (0, 1.0, "inout"), (120, 0.7, "inout"), (240, 1.0, "hold"))
    sc.on("idle", idle)

    def exitF(a):
        a.k(back_l, "rotation", (0, -0.12, "in"), (30, -1.2, "hold"))
        a.k(back_r, "rotation", (0, 0.12, "in"), (30, 1.2, "hold"))
    sc.on("exitF", exitF)


# ---------------------------------------------------------------------------
# scene 9 -- persona


def scene9(g, sc):
    lab_st = g.sans_style(14, sc.ink, 600, spacing=1.2)
    child(child(lab_st, "Fill"), "SolidColor").attrs["colorValue"] = argb(sc.ink, 0.7)
    lab = sc.reveal(g.text("S9 Label", lab_st, "Your personal style", prop="personaLabel", align="center"), 70, 20)
    title = sc.reveal(g.text("S9 Persona", g.serif_style(50, sc.ink, lh=52), "Glaze Alchemist", prop="personaName",
                             align="center"), 82, 30)
    bar_st = g.style(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", cornerRadiusTL=1.5, name="Accent Style")
    bar_col = solid(ULTRA, name="Persona Accent")
    bar_col.add(bind(g.p("personaColor"), 37))
    bar = g.box("Persona Accent", bar_st, E("Fill", {"name": "Fill"}, bar_col),
                E("Stroke", {"thickness": 1.0, "name": "Edge"}, solid(PORC, alpha=0.35)), w=44, h=3)
    S(bar, scaleX=1.0)
    bar.add(E("ComponentOrigin", {"originX": 0.5, "originY": 0.5, "name": "Origin"}))
    desc = sc.reveal(g.text("S9 Description", g.sans_style(17, sc.ink, 500, lh=24), "Always testing a little magic.",
                            prop="personaDescription", align="center"), 100, 24)
    sc.copy_box(lab, title, bar, sc.spacer(2), desc, top=92, align="topCenter", gap=8)

    rings = [S(shape(f"Anticipation {i}", 195, 300, ellipse(140, 140), stroke(PORC, 1.4, alpha=0.4)),
               scaleX=1.0, scaleY=1.0, opacity=0.0) for i in range(3)]
    sparks = []
    for i in range(8):
        ang = i * math.pi / 4 + 0.3
        s = S(shape(f"Spark {i}", 195, 300, ellipse(5, 5), fill(PORC, alpha=0.9)), x=195.0, y=300.0, opacity=0.0)
        s.ang = ang
        sparks.append(s)
    sc.back.add(*sparks, *rings)

    def enter(a):
        a.k(bar, "scaleX", (0, 0.0, "hold"), (90, 0.0, "back"), (116, 1.0, "hold"))
        for i, r in enumerate(rings):
            f0 = 30 + i * 10
            a.k(r, "scaleX", (0, 0.2, "hold"), (f0, 0.2, "out"), (f0 + 50, 2.2, "hold"))
            a.k(r, "scaleY", (0, 0.2, "hold"), (f0, 0.2, "out"), (f0 + 50, 2.2, "hold"))
            a.k(r, "opacity", (0, 0.0, "hold"), (f0, 0.0, "lin"), (f0 + 6, 1.0, "out"), (f0 + 50, 0.0, "hold"))
        for s in sparks:
            dx, dy = math.cos(s.ang) * 150, math.sin(s.ang) * 150
            a.k(s, "x", (0, 195.0, "hold"), (74, 195.0, "out"), (110, 195 + dx, "hold"))
            a.k(s, "y", (0, 300.0, "hold"), (74, 300.0, "out"), (110, 300 + dy, "hold"))
            a.k(s, "opacity", (0, 0.0, "hold"), (74, 0.0, "lin"), (78, 1.0, "soft"), (110, 0.0, "hold"))
    sc.on("enterF", enter)

    build_persona_layer(g)


def build_persona_layer(g):
    """Four emblems, each a real 3D piece with its own staging. All stand on the
    scene-9 plinth (base at y=373 in art-stage units)."""
    from v3d import V3D, look
    L = Layer("Persona")
    BASE_Y = 373.0

    def piece(name, lk, x=0.0, y=0.0, turn=True, **node_kw):
        v = V3D(g, name, lk, turn=turn)
        settle(v.inputs["live"], "propertyValue", 0.0)
        v.inputs["live"].attrs["propertyValue"] = 0.0
        nd = node(f"{name} Pivot", x, y, v.el, **node_kw)
        return v, nd

    # 0 Form Finder -- the asymmetric vessel: sketched as one stroke, then it turns into porcelain
    p0, _ = smooth_path(MF.profile_vertices("idea"), closed=True, name="Profile")
    tr0 = E("TrimPath", {"start": 0.0, "end": 1.0, "name": "Trim"})
    settle(tr0, "end", 1.0)
    s0 = stroke(PORC, 2.0)
    s0.add(tr0)
    sketch = S(shape("Form Finder Sketch", 0, 0, p0, s0), opacity=0.35)
    p0e, _ = smooth_path(MF.profile_vertices("vase"), closed=True, name="Echo")
    echo = S(shape("Form Finder Echo", 26, 0, p0e, stroke(CLAY, 1.6, alpha=0.8)), rotation=0.14, opacity=1.0)
    v0, n0 = piece("Form Finder 3D", look("idea", body="F4EFE8", rings=1.3, speck=0.45, sheen=0.1, seed=11.0))
    S(n0, y=0.0, opacity=1.0)
    e0 = S(node("Emblem Form Finder", 195, BASE_Y, echo, sketch, n0), rotation=0.0, opacity=1.0, y=BASE_Y)
    e0.trim, e0.sketch, e0.echo, e0.v, e0.piece = tr0, sketch, echo, [v0], n0

    # 1 Glaze Alchemist -- a cobalt-lined shell, a glossy cobalt orb levitating above it, droplets in orbit
    v1b, n1b = piece("Alchemist Shell 3D", look("shell", body="F2ECE2", dip=0.22, drip=1.0, inner=1.0, tilt=0.62,
                                                 roll=-0.32, seed=12.0, turnGain=0.6), rotation=-0.32)
    S(n1b, scaleX=1.0, scaleY=1.0, rotation=-0.32)
    v1o, n1o = piece("Alchemist Orb 3D", look("orb", body="2B3C95", cap=1.0, sphere=1.0, dip=1.0, drip=0.0, gloss=1.35,
                                               seed=13.0, rings=0.0), y=-118.0)
    S(n1o, y=-118.0, scaleX=1.0, scaleY=1.0)
    glow1 = S(shape("Orb Glow", 0, -170, ellipse(220, 220), fill("4C63D2", alpha=0.35, feather=48)), opacity=1.0)
    drops = []
    for i in range(5):
        a_ = i * 2 * math.pi / 5 + 0.4
        r_ = 6 + (i % 3) * 3
        d = shape(f"Droplet {i}", math.cos(a_) * 118, math.sin(a_) * 34, ellipse(r_ + 3, (r_ + 3) * 1.15),
                  fill("3F55C4"), stroke("A9B6F5", 1.0, alpha=0.7))
        d.add(shape(f"Droplet {i} Shine", -1.5, -2.0, ellipse(r_ * 0.45, r_ * 0.35), fill("FFFFFF", alpha=0.75)))
        drops.append(d)
    orbit = S(node("Droplet Orbit", 0, -176, *drops), rotation=0.0, scaleX=1.0, scaleY=1.0)
    e1 = S(node("Emblem Glaze Alchemist", 195, BASE_Y, orbit, n1o, n1b, glow1), opacity=1.0, y=BASE_Y)
    e1.shell, e1.orb, e1.orbit, e1.glow, e1.v = n1b, n1o, orbit, glow1, [v1b, v1o]

    # 2 Wheel Regular -- a charcoal bowl spinning on the porcelain wheel, rings of rhythm
    disc = S(shape("Wheel Disc", 0, -96, ellipse(250, 250), fill(PORC)), scaleX=1.0, scaleY=1.0)
    head = shape("Wheel Head", 0, -10, ellipse(210, 46), fill("C9BDAE"), stroke(CHAR, 1.4, alpha=0.4))
    v2, n2 = piece("Wheel Bowl 3D", look("bowl", body="3C3532", glaze="EDE6DA", dip=0.32, drip=0.9, inner=1.0,
                                         gloss=0.4, tilt=0.42, rings=1.9, speck=0.3, turnGain=4.0, seed=14.0),
                   y=-14.0)
    S(n2, y=-14.0, scaleX=0.92, scaleY=0.92)
    ripples = [S(shape(f"Ripple {i}", 0, -10, ellipse(230 + i * 40, 52 + i * 10), stroke(CHAR, 1.4, alpha=0.5)),
                 scaleX=1.0, scaleY=1.0, opacity=1.0) for i in range(3)]
    streak_tr = E("TrimPath", {"start": 0.0, "end": 0.18, "offset": 0.0, "name": "Trim"})
    settle(streak_tr, "offset", 0.0)
    st_s = stroke(CHAR, 2.0, alpha=0.6)
    st_s.add(streak_tr)
    streak = shape("Spin Streak", 0, -10, ellipse(250, 60), st_s)
    e2 = S(node("Emblem Wheel Regular", 195, BASE_Y, n2, streak, head, *ripples, disc), opacity=1.0, y=BASE_Y)
    e2.disc, e2.bowl, e2.ripples, e2.streak, e2.v = disc, n2, ripples, streak_tr, [v2]

    # 3 Handbuilt Storyteller -- a coil pot that rises coil by coil, thumbprints pressed into its wall
    lk3 = look("coilpot", body=CLAY, coils=1.0, prints=1.0, rings=0.0, speck=0.6, sheen=0.22, tilt=0.24,
               turnGain=0.0, yaw=0.0, seed=15.0)
    v3, n3 = piece("Coil Pot 3D", lk3, turn=False)
    S(n3, scaleX=1.25, scaleY=1.25)
    crumbs = [S(shape(f"Clay Crumb {i}", x, y, ellipse(w, w * 0.6), fill(mix(CLAY, "8E4A35", 0.3))), scaleX=1.0,
                scaleY=1.0) for i, (x, y, w) in enumerate([(-92, -2, 9), (-74, 4, 6), (88, 2, 8), (104, -4, 5)])]
    e3 = S(node("Emblem Handbuilt Storyteller", 195, BASE_Y, n3, *crumbs), opacity=1.0, y=BASE_Y, rotation=0.0)
    e3.v, e3.pot, e3.crumbs, e3.lk = [v3], n3, crumbs, lk3

    root = S(node("Persona Emblems", 0, 0, e0, e1, e2, e3), opacity=1.0)
    g.persona_root = root
    em = [e0, e1, e2, e3]

    def show_only(a, k, f=0):
        for j, e in enumerate(em):
            a.k(e, "opacity", (f, 1.0 if j == k else 0.0, "hold"))
            for v in e.v:
                a.k(v.inputs["live"], "propertyValue", (f, 1.0 if j == k else 0.0, "hold"))

    hidden = L.anim("Persona Hidden", 1)
    for e in em:
        hidden.k(e, "opacity", (0, 0.0, "hold"))
        for v in e.v:
            hidden.k(v.inputs["live"], "propertyValue", (0, 0.0, "hold"))
    enters, idles = [], []
    for k in range(4):
        a = L.anim(f"Persona {k} Reveal", 180)
        show_only(a, k)
        e = em[k]
        if k == 0:
            a.k(e.trim, "end", (0, 0.0, "hold"), (40, 0.0, "heavy"), (104, 1.0, "hold"))
            a.k(e.sketch, "opacity", (0, 1.0, "hold"), (110, 1.0, "soft"), (150, 0.35, "hold"))
            a.k(e.piece, "opacity", (0, 0.0, "hold"), (86, 0.0, "out"), (130, 1.0, "hold"))
            a.k(e.piece, "y", (0, 24.0, "hold"), (86, 24.0, "back"), (136, 0.0, "hold"))
            a.k(e, "rotation", (0, 0.16, "hold"), (40, 0.16, "back"), (140, 0.0, "hold"))
            a.k(e.echo, "opacity", (0, 0.0, "hold"), (110, 0.0, "out"), (150, 1.0, "hold"))
            e.v[0].key(a, 0, dict(yaw=-2.4), "hold")
            e.v[0].key(a, 86, dict(yaw=-2.4), "out")
            e.v[0].key(a, 170, dict(yaw=0.0), "hold")
        elif k == 1:
            a.k(e.shell, "scaleX", (0, 0.0, "hold"), (56, 0.0, "back"), (96, 1.0, "hold"))
            a.k(e.shell, "scaleY", (0, 0.0, "hold"), (56, 0.0, "back"), (96, 1.0, "hold"))
            a.k(e.shell, "rotation", (0, 0.6, "hold"), (56, 0.6, "back"), (104, -0.32, "hold"))
            e.v[0].key(a, 0, dict(roll=0.6, dip=0.0, inner=0.0), "hold")
            e.v[0].key(a, 56, dict(roll=0.6, dip=0.0, inner=0.0), "back")
            e.v[0].key(a, 104, dict(roll=-0.32), "hold")
            e.v[0].key(a, 96, dict(dip=0.0, inner=0.0), "heavy")
            e.v[0].key(a, 150, dict(dip=0.22, inner=1.0), "hold")
            # the travelling orb dips into the shell and this one swells out of the same spot:
            # one glossy cobalt orb, handed over from the motif to the emblem, then it levitates
            a.k(e.orb, "y", (0, -96.0, "hold"), (76, -96.0, "out"), (128, -118.0, "hold"))
            a.k(e.orb, "scaleY", (0, 0.0, "hold"), (74, 0.0, "back"), (96, 1.12, "inout"), (112, 0.94, "soft"),
                (126, 1.0, "hold"))
            a.k(e.orb, "scaleX", (0, 0.0, "hold"), (74, 0.0, "back"), (96, 1.06, "inout"), (112, 1.03, "soft"),
                (126, 1.0, "hold"))
            a.k(e.orbit, "scaleX", (0, 0.0, "hold"), (108, 0.0, "back"), (150, 1.0, "hold"))
            a.k(e.orbit, "scaleY", (0, 0.0, "hold"), (108, 0.0, "back"), (150, 1.0, "hold"))
            a.k(e.orbit, "rotation", (0, -1.5, "hold"), (108, -1.5, "out"), (180, 0.0, "hold"))
            a.k(e.glow, "opacity", (0, 0.0, "hold"), (96, 0.0, "out"), (140, 1.0, "hold"))
        elif k == 2:
            a.k(e.disc, "scaleX", (0, 0.0, "hold"), (52, 0.0, "back"), (90, 1.0, "hold"))
            a.k(e.disc, "scaleY", (0, 0.0, "hold"), (52, 0.0, "back"), (90, 1.0, "hold"))
            for i, r in enumerate(e.ripples):
                f0 = 84 + i * 10
                a.k(r, "scaleX", (0, 0.3, "hold"), (f0, 0.3, "out"), (f0 + 40, 1.0, "hold"))
                a.k(r, "scaleY", (0, 0.3, "hold"), (f0, 0.3, "out"), (f0 + 40, 1.0, "hold"))
            a.k(e.bowl, "y", (0, 90.0, "hold"), (70, 90.0, "back"), (114, -14.0, "hold"))
            e.v[0].key(a, 0, look("cup", body="3C3532", glaze="EDE6DA", dip=0.0, inner=0.0, tilt=0.42, rings=1.9),
                       "hold", only=PROFILE_ONLY + ["dip", "inner"])
            e.v[0].key(a, 70, look("cup", body="3C3532", glaze="EDE6DA", dip=0.0, inner=0.0), "settle",
                       only=PROFILE_ONLY + ["dip", "inner"])
            e.v[0].key(a, 124, look("bowl", dip=0.0, inner=0.0), "back", only=PROFILE_ONLY + ["dip", "inner"])
            e.v[0].key(a, 170, dict(dip=0.32, inner=1.0), "hold", only=["dip", "inner"])
            a.k(e.streak, "offset", (0, 0.0, "hold"), (100, 0.0, "out"), (180, 1.0, "hold"))
        else:
            # coil by coil: the wall rises in five weighted steps, the rib smooths it, prints appear
            H = e.lk["h"]
            for i in range(6):
                f0 = 50 + i * 16
                hv = H * min(1.0, i / 5.0)
                if i == 0:
                    e.v[0].key(a, 0, dict(h=2.0, prints=0.0), "hold", only=["h", "prints"])
                    e.v[0].key(a, f0, dict(h=2.0), "back", only=["h"])
                else:
                    e.v[0].key(a, f0, dict(h=hv), "back" if i < 5 else "hold", only=["h"])
            e.v[0].key(a, 140, dict(prints=0.0), "out", only=["prints"])
            e.v[0].key(a, 172, dict(prints=1.0), "hold", only=["prints"])
            for i, c in enumerate(e.crumbs):
                f0 = 60 + i * 14
                a.k(c, "scaleX", (0, 0.0, "hold"), (f0, 0.0, "back"), (f0 + 14, 1.0, "hold"))
                a.k(c, "scaleY", (0, 0.0, "hold"), (f0, 0.0, "back"), (f0 + 14, 1.0, "hold"))
        enters.append(a)
        i_ = L.anim(f"Persona {k} Idle", 240, loop="loop")
        show_only(i_, k)
        if k == 1:
            i_.k(e.orbit, "rotation", (0, 0.0, "lin"), (240, 6.283185, "hold"))
            i_.k(e.orb, "y", (0, -118.0, "inout"), (120, -128.0, "inout"), (240, -118.0, "hold"))
            i_.k(e.glow, "opacity", (0, 1.0, "inout"), (120, 0.7, "inout"), (240, 1.0, "hold"))
        elif k == 2:
            i_.k(e.streak, "offset", (0, 0.0, "lin"), (240, 1.0, "hold"))
        elif k == 3:
            e.v[0].key(i_, 0, dict(yaw=0.0), "inout", only=["yaw"])
            e.v[0].key(i_, 120, dict(yaw=0.35), "inout", only=["yaw"])
            e.v[0].key(i_, 240, dict(yaw=0.0), "hold", only=["yaw"])
        elif k == 0:
            i_.k(e.echo, "rotation", (0, 0.14, "inout"), (120, 0.2, "inout"), (240, 0.14, "hold"))
        idles.append(i_)
    reduced = []
    for k in range(4):
        r = L.anim(f"Persona {k} Reduced", 14)
        show_only(r, k)
        r.k(em[k], "opacity", (0, 0.0, "lin"), (14, 1.0, "hold"))
        reduced.append(r)
    outs, frozens = [], []
    for k in range(4):
        o = L.anim(f"Persona {k} Exit", 30)
        show_only(o, k)
        e = em[k]
        o.k(e, "y", (0, e.attrs["y"], "in"), (30, e.attrs["y"] + 60, "hold"))
        o.k(root, "opacity", (0, 1.0, "in"), (30, 0.0, "hold"))
        outs.append(o)
        frozens.append(L.anim(f"Persona {k} Frozen", 1, exempt=True))
    for a in [hidden] + enters + idles + reduced:
        a.k(root, "opacity", (0, 1.0, "hold"))
    hidden.k(root, "opacity", (0, 0.0, "hold"))

    sH = state(hidden, 0, 0)
    on9 = lambda op="equal": c_num(g, "currentScreen", 9, op)  # noqa: E731
    v = lambda k: c_num(g, "_personaVariant", k)  # noqa: E731
    rm = lambda b: c_bool(g, "reducedMotion", b)  # noqa: E731
    sE = [state(a, 260, -300 + k * 150) for k, a in enumerate(enters)]
    sI = [state(a, 560, -300 + k * 150) for k, a in enumerate(idles)]
    sR = [state(a, 260, 320 + k * 120) for k, a in enumerate(reduced)]
    sO = [state(a, 900, -300 + k * 150) for k, a in enumerate(outs)]
    sF = [state(a, 760, 320 + k * 120) for k, a in enumerate(frozens)]
    for k in range(4):
        sH.add(trans(sR[k], 0, [on9(), v(k), rm(True)]))
        sH.add(trans(sE[k], 0, [on9(), v(k), rm(False)]))
        for s_ in (sE[k], sI[k], sR[k], sF[k]):
            s_.add(trans(sO[k], 90, [on9("notEqual")]))
            for j in range(4):
                if j != k:   # persona changed while shown: re-reveal the new one, never a mix
                    s_.add(trans(sE[j], 120, [on9(), v(j)]))
        sE[k].add(trans(sI[k], 0, [], exit_pct=100))
        sR[k].add(trans(sI[k], 0, [], exit_pct=100))
        sI[k].add(trans(sF[k], 0, [c_bool(g, "_frozen", True)]))
        sF[k].add(trans(sI[k], 0, [c_bool(g, "_frozen", False)]))
        for j in range(4):
            sO[k].add(trans(sE[j], 120, [on9(), v(j), rm(False)]))
            sO[k].add(trans(sR[j], 0, [on9(), v(j), rm(True)]))
        sO[k].add(trans(sH, 0, [], exit_pct=100))
    L.el.add(E("AnyState", {"x": 0.0, "y": -460.0}), E("ExitState", {"x": 1000.0, "y": -460.0}),
             E("EntryState", {"x": -220.0, "y": 0.0}, trans(sH)), sH, *sE, *sI, *sR, *sO, *sF)
    g.layers.append(L)


PROFILE_ONLY = ["h"] + [f"r{i}" for i in range(6)] + [f"c{i}" for i in range(6)]


# ---------------------------------------------------------------------------
# scene 10 -- summary + share card


def scene10(g, sc):
    hd = g.text("S10 Headline", g.serif_style(30, sc.ink, lh=34), "A little year. A lot of you.", prop="summaryHeadline",
                align="center")
    sp = support(sc, "summarySupport", "Take a piece of your year with you.", size=15, align="center", start=40)
    eh = g.text("S10 Empty Headline", g.serif_style(30, sc.ink, lh=34), "Every story starts somewhere.",
                prop="emptyHeadline", align="center")
    es = support(sc, "emptySupport", "Your next chapter is waiting.", size=15, align="center", start=40)
    es.attrs["name"] = "S10 Empty Support"
    inv = g.formula("Invert", g.tv(1), g.op("-"), g.INPUT())
    g.invert = inv
    for t, show_when_empty in ((hd, False), (sp, False), (eh, True), (es, True)):
        lp = child(t, "LayoutParticipant")
        if show_when_empty:
            lp.add(bind(g.p("_isEmpty"), 596, inv.id))
        else:
            lp.add(bind(g.p("_isEmpty"), 596))
    sc.reveal(hd, 24, 30)
    sc.reveal(eh, 24, 30)
    sc.copy_box(hd, eh, sp, es, top=84, align="topCenter", gap=6)

    import sharecard  # noqa: E402
    card_ab, assemble = sharecard.build(g)
    g.card_artboard = card_ab
    nest = E("NestedArtboard", {"artboardId": card_ab.id, "name": "Share Card"})
    remap = E("NestedRemapAnimation", {"animationId": assemble.id, "name": "Assemble"})
    settle(remap, "time", 1.0)
    nest.add(remap)
    S(nest, y=0.0, rotation=0.0, opacity=1.0, x=0.0)
    shadow = S(shape("Card Shadow", 150, 236, rect(280, 420, 26), fill(CHAR, alpha=0.3, feather=26)), opacity=1.0)
    card_root = S(node("Card Root", 0, 0, nest, shadow), opacity=1.0)
    g.card_stage.add(card_root)
    sc.extra_roots.append(card_root)

    def enter(a):
        a.k(nest, "y", (0, -520.0, "hold"), (14, -520.0, "back"), (58, 0.0, "hold"))
        a.k(nest, "rotation", (0, -0.12, "hold"), (14, -0.12, "back"), (66, 0.0, "hold"))
        a.k(shadow, "opacity", (0, 0.0, "hold"), (40, 0.0, "out"), (70, 1.0, "hold"))
        a.k(remap, "time", (0, 0.0, "hold"), (30, 0.0, "lin"), (120, 1.0, "hold"))
    sc.on("enterF", enter)

    def enterB(a):
        a.k(remap, "time", (0, 1.0, "hold"))
    sc.on("enterB", enterB)


SCENE_FUNCS = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8, 9: scene9,
               10: scene10}


def build_scenes(g):
    scs = []
    for n in range(1, 11):
        sc = Scene(g, n)
        SCENE_FUNCS[n](g, sc)
        finalize_scene(g, sc)
        scs.append(sc)
    # art stage: scene fronts, persona emblems, the motif, scene backs
    art = g.art_stage
    for sc in scs:
        art.add(sc.front)
    art.add(g.persona_root)
    art.add(g.motif.vessel, g.motif.plinth)
    for sc in scs:
        art.add(sc.back)
    # stage order (front to back): sequencer/header/footer already in; copy, card, art
    for sc in scs:
        if sc.copy is not None:
            g.stage.add(sc.copy)
    g.stage.add(g.card_stage)
    g.stage.add(art)
    # matte mineral grain over the flat background colour, behind everything else
    gst = g.abs_style(top=0, bottom=0, left=0, right=0, name="Grain Style")
    g.stage.add(g.box("Grain", gst, E("ScriptedLayout", {"scriptAssetId": g.grain_script.id, "name": "Grain"},
                                       E("ScriptInputNumber", {"propertyValue": 0.42, "name": "strength"})),
                      w=10, h=10))
