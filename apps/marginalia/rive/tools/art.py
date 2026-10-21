"""Marginalia scene artwork and choreography.

Every object here is editable vector artwork (Shapes / PointsPaths / text) in
named, layered groups: Copy (never parallaxed) > Parallax near > mid > far.
Choreography is declared as forward-entrance tweens on the Scene object
(see build_rml.Scene); hidden / static / back / exit poses derive from them.
"""
from __future__ import annotations

import math
import random

from rmlkit import (N, Anim, Layer, arch, bind, cbool, cnum, ctrig, ellipse, fill, lin, node, solid,
                    poly, rad, rect, shape, smooth, solid, star, stroke, text, trans)

K = None   # rmlkit module, injected
plx = None  # parallax wrapper factory, injected

PARCH, PAPER, PSHADE, PDEEP = "F1E8D5", "F8F2E4", "E4D6B8", "CDBA94"
INK, INK2, INK3 = "252E3D", "3B4558", "5C667A"
OX, OXD, OXL = "782D3D", "571E2B", "9C4A59"
GOLD, GOLDL, GOLDD = "BD914C", "DDBD84", "8E6A33"
GREEN = "3E5446"
SW, SH = 390, 664
TAU = math.tau

rng = random.Random(7)


# ======================================================================= motifs
def gold_rule(cx, y, w, left=False):
    n = N("Node", x=cx, y=y, name="Gold Rule").ensure()
    n.add(shape("Star", star(11, 11, 4, 0.28), fill(GOLD)))
    n.add(shape("Line L", rect(w / 2 - 10, 1, x=-(w / 4 + 5)), fill(GOLD)))
    n.add(shape("Line R", rect(w / 2 - 10, 1, x=(w / 4 + 5)), fill(GOLD)))
    return n


def sparkle(name, x, y, s, color=GOLD, a=1.0):
    return shape(name, star(s, s, 4, 0.22), fill(color, a), x=x, y=y).ensure()


def cloud(name, x, y, s=1.0, color=PAPER, edge=PDEEP):
    puffs = [(-38, 4, 46, 30), (-12, -10, 54, 42), (18, -4, 50, 36), (42, 6, 40, 26), (0, 10, 96, 22)]
    g = node(name, x=x, y=y, scaleX=s, scaleY=s).ensure()
    sh = shape("Puffs")
    for px, py, w, h in puffs:
        sh.add(ellipse(w, h, x=px, y=py))
    sh.add(stroke(edge, 1.2, 0.8))
    sh.add(fill(color))
    shadow = shape("Shade", ellipse(100, 16, x=4, y=16), fill(PDEEP, 0.45))
    g.add(sh, shadow)
    return g


def building(name, x, base, w, h, color, roof="pointed", windows=True, win=GOLDL):
    g = node(name, x=x, y=base).ensure()
    if windows:
        for i in range(max(1, int(h // 26))):
            wy = -h + 18 + i * 24
            if wy > -10:
                break
            g.add(shape("Window", arch(5, 9, x=0, y=wy + 9), fill(win, 0.9)))
    body = shape("Body", rect(w, h, x=0, y=-h / 2), fill(color))
    if roof == "pointed":
        g.add(shape("Roof", poly([(-w / 2 - 2, -h), (0, -h - w * 0.9), (w / 2 + 2, -h)]), fill(color)))
    elif roof == "dome":
        g.add(shape("Dome", ellipse(w, w * 0.9, x=0, y=-h), fill(color)))
    elif roof == "crenel":
        for i in range(3):
            g.add(shape("Merlon", rect(w / 5, 6, x=-w / 2 + w / 10 + i * (w * 0.4), y=-h - 3), fill(color)))
    g.add(body)
    return g


def book_spine(name, x, base, w, h, color, band=GOLD, door=True):
    """A standing book spine (pivot at its base) with an arched lit doorway."""
    g = node(name, x=x, y=base).ensure()
    parts = {}
    if door:
        glow = shape("Door Glow", ellipse(w * 1.3, w * 1.1, x=0, y=-w * 0.55),
                     fill(paint=rad(0, -w * 0.55, w * 0.7, [(0, GOLDL, 0.85), (1, GOLD, 0)])), opacity=0)
        dw = w * 0.52
        d = shape("Door", arch(dw, dw * 1.5, x=0, y=-6),
                  fill(paint=lin(0, -dw * 1.5, 0, 0, [(0, "FFF3D2", 1), (1, GOLD, 1)])), opacity=0.25)
        frame = shape("Door Frame", arch(dw + 5, dw * 1.5 + 4, x=0, y=-4), fill(OXD, 0.55))
        g.add(glow.ensure(), d.ensure(), frame)
        parts["door"] = d
        parts["glow"] = glow
    for by in (-h + 14, -h + 22, -h * 0.55):
        g.add(shape("Band", rect(w - 6, 2, x=0, y=by), fill(band, 0.9)))
    g.add(shape("Emblem", star(10, 10, 4, 0.3, x=0, y=-h * 0.72), fill(band)))
    g.add(shape("Spine Shade", rect(w * 0.22, h, x=w * 0.39, y=-h / 2), fill("000000", 0.14)))
    g.add(shape("Spine", rect(w, h, x=0, y=-h / 2, r=3), fill(color)))
    return g, parts


def open_book(name, x, y, w, cover=OX, pages=PAPER, depth=6):
    """Open book seen from slightly above; origin at the spine bottom."""
    g = node(name, x=x, y=y).ensure()
    hw = w / 2
    left = node("Left Pages").ensure()
    right = node("Right Pages").ensure()
    for i in range(depth):
        o = i * 2.2
        lp = shape(f"Leaf L{i}", smooth([(-2, -54 + o), (-hw * 0.45, -70 + o), (-hw + 4, -58 + o),
                                         (-hw, -6 + o), (-hw * 0.5, -14 + o), (-2, 0 + o)]),
                   fill(pages if i == 0 else PSHADE), stroke(PDEEP, 0.8))
        rp = shape(f"Leaf R{i}", smooth([(2, -54 + o), (hw * 0.45, -70 + o), (hw - 4, -58 + o),
                                         (hw, -6 + o), (hw * 0.5, -14 + o), (2, 0 + o)]),
                   fill(pages if i == 0 else PSHADE), stroke(PDEEP, 0.8))
        left.add(lp)
        right.add(rp)
    # type lines on the top leaves (anonymous greeked text)
    lines = node("Type Lines").ensure()
    for i in range(5):
        yy = -50 + i * 8
        lines.add(shape("Line", rect(hw * 0.62, 1.4, x=-hw * 0.5, y=yy + i * 0.4), fill(INK3, 0.35)))
        lines.add(shape("Line", rect(hw * 0.62, 1.4, x=hw * 0.5, y=yy + i * 0.4), fill(INK3, 0.35)))
    cov = shape("Cover", smooth([(-hw - 8, -4), (-hw - 6, 10), (0, 18), (hw + 6, 10), (hw + 8, -4), (0, 6)]),
                fill(cover))
    gutter = shape("Gutter", rect(3, 60, x=0, y=-30), fill(PDEEP, 0.8))
    g.add(gutter, lines, left, right, cov)
    return g, dict(left=left, right=right, lines=lines)


# ======================================================================= copy
def copy_text(ctx, name, x, y, style, prop, w=None, align="center", **kw):
    lit = ctx["DATA"].get(prop, "")
    if isinstance(lit, (int, float)) and not isinstance(lit, bool):
        lit = f"{int(lit):,}"
    return text(name, x, y, [(style, str(lit), bind(prop, 268))], w=w, align=align, **kw)


def fade_up(sc, obj, t0, t1, dy=14, ease="out"):
    sc.tw(obj, "opacity", t0, t1, 0.0, 1.0, "soft")
    sc.tw(obj, "y", t0, t1 + 80, obj.attrs.get("y", 0) + dy, obj.attrs.get("y", 0), ease)


# ======================================================================= scene 1
def scene1(sc, ctx):
    serif, sans, italic = ctx["serif"], ctx["sans"], ctx["italic"]
    sc.enter_ms = 2300
    period = copy_text(ctx, "Period", 20, 18, sans(12, GOLDD, 500, ls=1.8), "periodLabel", w=350)
    head = copy_text(ctx, "Intro Headline", 30, 40, serif(42, INK, 500, lh=44, lining=True), "introHeadline", w=330,
                     h=92, overflow="fitFontSize", wrap="wrap")
    sup = copy_text(ctx, "Intro Support", 30, 140, sans(15, INK2, 400, lh=19), "introSupport", w=330, h=40,
                    overflow="ellipsis", wrap="wrap")
    # ex-libris plate carrying the bound name (long names truncate with an ellipsis)
    plate = node("Name Plate", x=SW / 2, y=196).ensure()
    plate.add(text("Reader Name", -100, -14, [(italic(23, OX, 600), ctx["DATA"].get("userName", ""),
                                                bind("userName", 268))],
                   w=200, h=30, align="center", overflow="ellipsis", wrap="wrap", valign="top"))
    plate.add(shape("Plate Rule", rect(150, 1, y=20), fill(GOLD)))
    plate.add(shape("Plate Dot L", star(7, 7, 4, 0.3, x=-82, y=20), fill(GOLD)))
    plate.add(shape("Plate Dot R", star(7, 7, 4, 0.3, x=82, y=20), fill(GOLD)))
    copy = node("Copy", period, head, sup, plate)

    # --- hero: a book unfolds into a paper city
    far = node("Far Hills").ensure()
    far.add(shape("Hill", smooth([(-40, 664), (60, 520), (150, 560), (260, 500), (430, 560), (430, 664)]),
                  fill(PSHADE)))
    far.add(cloud("Cloud A", 70, 300, 0.8), cloud("Cloud B", 320, 330, 0.65))
    stars = [sparkle(f"Spark {i}", x, y, s) for i, (x, y, s) in
             enumerate([(48, 262, 13), (346, 250, 16), (300, 300, 9), (90, 330, 8)])]
    far.add(stars)

    book_root = node("Pop-up Book", x=SW / 2, y=600).ensure()
    city = node("Paper City", x=0, y=-40).ensure()
    towers = []
    spec = [(-118, 70, 30, PDEEP, "pointed"), (-86, 112, 26, PSHADE, "crenel"), (-52, 150, 34, PAPER, "pointed"),
            (-14, 190, 30, PSHADE, "dome"), (22, 168, 36, PAPER, "pointed"), (58, 128, 28, PDEEP, "crenel"),
            (92, 96, 32, PSHADE, "pointed"), (124, 64, 26, PAPER, "dome")]
    for i, (bx, h, w, c, roof) in enumerate(spec):
        b = building(f"Tower {i}", bx, 0, w, h, c, roof)
        b.add(shape("Edge", rect(1.2, h, x=w / 2, y=-h / 2), fill(PDEEP)))
        towers.append(b)
    # banner with the wordmark, revealed by a mask
    banner = node("Wordmark Banner", x=0, y=-232).ensure()
    mask = shape("Banner Mask", rect(300, 70, x=0, y=0), scaleX=0.0).ensure()
    bshape = shape("Banner", smooth([(-150, -22), (0, -30), (150, -22), (138, 0), (150, 22), (0, 30),
                                     (-150, 22), (-138, 0)], sharp={3, 7}), fill(OX)).ensure()
    btext = text("Wordmark", -150, -22, [(italic(40, PAPER, 600), "Marginalia", None)], w=300, align="center")
    bwrap = node("Banner Art", btext, bshape).ensure()
    bwrap.add(N("ClippingShape", sourceId=mask.id, name="Reveal Mask"))
    banner.add(bwrap, mask)
    city.add(towers)
    book, bparts = open_book("Book", 0, 0, 300, cover=INK)
    book_root.add(banner, city, book)
    # the book's own ribbon tail is the persistent ribbon (see persistent())

    sc.content.add(copy, plx("hero", "near", book_root), plx("far", "far", far))

    # --- choreography (score: anticipation, hero, copy)
    sc.tw(book_root, "y", 0, 200, 600, 612, "antic")
    sc.tw(book_root, "y", 200, 600, 612, 600, "back")
    sc.tw(bparts["left"], "scaleX", 160, 700, 0.04, 1.0, "inout")
    sc.tw(bparts["right"], "scaleX", 160, 700, 0.04, 1.0, "inout")
    sc.tw(bparts["lines"], "opacity", 600, 900, 0.0, 1.0, "soft")
    for i, b in enumerate(sorted(towers, key=lambda t: abs(t.attrs["x"]))):
        t0 = 520 + i * 70
        sc.tw(b, "scaleY", t0, t0 + 520, 0.0, 1.0, "back")
    sc.tw(mask, "scaleX", 1150, 1650, 0.0, 1.0, "inout")
    sc.tw(banner, "y", 1100, 1700, -214, -232, "out")
    for i, s in enumerate(stars):
        sc.tw(s, "scaleX", 900 + i * 90, 1300 + i * 90, 0.0, 1.0, "back")
        sc.tw(s, "scaleY", 900 + i * 90, 1300 + i * 90, 0.0, 1.0, "back")
    sc.tw(far, "opacity", 0, 600, 0.0, 1.0, "soft")
    fade_up(sc, period, 1000, 1400)
    fade_up(sc, head, 1150, 1600, 18)
    fade_up(sc, sup, 1350, 1800)
    fade_up(sc, plate, 1550, 2100)
    # idle: stars twinkle, banner breathes (seamless: first == last)
    sc.idle_ms = 6000
    for i, s in enumerate(stars):
        o = i * 700
        sc.idle_keys(s, "opacity", [(0, 1, "sine"), (1500 + o, 0.45, "sine"), (3000 + o, 1, "sine"), (6000, 1, "linear")])
    sc.idle_keys(banner, "y", [(0, -232, "sine"), (3000, -236, "sine"), (6000, -232, "linear")])


# ======================================================================= scene 2
def scene2(sc, ctx):
    copy, P = ctx["metric_copy"](sc, "booksFinished", head_w=260)
    far = node("Far City").ensure()
    for i, (bx, h, w, roof) in enumerate([(30, 250, 30, "pointed"), (70, 300, 36, "crenel"), (115, 230, 26, "dome"),
                                          (300, 280, 34, "pointed"), (345, 240, 28, "crenel"), (372, 320, 22, "pointed")]):
        far.add(building(f"Far {i}", bx, 620, w, h, PSHADE, roof, win=PDEEP))
    spines_n = node("Spines").ensure()
    cols = [OX, GREEN, INK, OXD, INK2, OX, GREEN, INK]
    xs = [44, 86, 132, 174, 218, 262, 304, 346]
    hs = [230, 290, 250, 200, 270, 215, 260, 190]
    ws = [40, 42, 46, 38, 44, 40, 42, 38]
    spines = []
    for i in range(8):
        g, parts = book_spine(f"Book {i + 1}", xs[i], 612, ws[i], hs[i], cols[i],
                              band=GOLD if cols[i] != GOLD else OX)
        spines.append((g, parts))
    for g, _ in reversed(spines):
        spines_n.add(g)
    ground = node("Bridge").ensure()
    ground.add(shape("Walk", smooth([(-20, 612), (120, 604), (260, 616), (410, 606), (410, 640), (-20, 640)],
                                    sharp={4, 5}), fill(PAPER), stroke(PDEEP, 1)))
    ground.add(shape("Water", rect(440, 40, x=195, y=652), fill(paint=lin(0, 632, 0, 672, [(0, INK2, 0.9), (1, INK, 1)]))))
    glints = [shape(f"Glint {i}", rect(14 + i % 3 * 6, 1.5, x=30 + i * 47, y=646 + (i % 2) * 8), fill(GOLDL, 0.8)).ensure()
              for i in range(8)]
    ground.children[0:0] = glints  # glints above the water
    birds = node("Birds", x=300, y=330).ensure()
    for bx, by in ((0, 0), (16, -8), (30, 4)):
        birds.add(shape("Bird", poly([(-5, 0), (0, 3), (5, 0)], closed=False), stroke(INK3, 1.2, cap="round"), x=bx, y=by))
    sc.content.add(copy, plx("near", "near", ground), plx("spines", "mid", spines_n, birds), plx("far", "far", far))
    # choreography: spines rise as doorways, lit one after another
    order = sorted(range(8), key=lambda i: abs(xs[i] - 195))
    for k, i in enumerate(order):
        g, parts = spines[i]
        t0 = 200 + k * 65
        sc.tw(g, "scaleY", t0, t0 + 560, 0.0, 1.0, "back")
        sc.tw(parts["door"], "opacity", 900 + k * 70, 1200 + k * 70, 0.25, 1.0, "soft")
        sc.tw(parts["glow"], "opacity", 950 + k * 70, 1350 + k * 70, 0.0, 0.9, "soft")
    sc.tw(far, "opacity", 0, 500, 0.0, 1.0, "soft")
    sc.tw(far, "y", 0, 900, 30, 0, "out")
    sc.tw(birds, "x", 600, 1800, 250, 300, "out")
    sc.tw(birds, "opacity", 600, 900, 0.0, 1.0, "soft")
    # idle: doorway glow breathes, glints shimmer
    for k, (g, parts) in enumerate(spines):
        o = (k * 530) % 2400
        sc.idle_keys(parts["glow"], "opacity", [(0, 0.9, "sine"), (1200 + o, 0.55, "sine"), (2400 + o, 0.9, "sine"), (6000, 0.9, "linear")])
    for k, gl in enumerate(glints):
        o = k * 400
        sc.idle_keys(gl, "opacity", [(0, 1, "sine"), (900 + o, 0.2, "sine"), (1800 + o, 1, "sine"), (6000, 1, "linear")])
    sc.idle_keys(birds, "y", [(0, 330, "sine"), (3000, 322, "sine"), (6000, 330, "linear")])


# ======================================================================= scene 3
def scene3(sc, ctx):
    serif, sans = ctx["serif"], ctx["sans"]
    # composition: headline on top, monumental numeral mid-stage, support low
    head = copy_text(ctx, "Headline", 24, 6, serif(34, INK, 500, lh=37), "screen3Headline", w=342, h=78,
                     overflow="fitFontSize", wrap="wrap")
    num = text("Hero Number", 10, 150, [(serif(150, OX, 600, ls=-3, lining=True), "9,840", bind("pagesReadText", 268))],
               w=370, h=160, align="center", overflow="fitFontSize", wrap="noWrap", valign="middle")
    unit = copy_text(ctx, "Unit", 20, 314, sans(15, INK, 500, ls=1.6, lh=18), "screen3Unit", w=350, h=36,
                     overflow="ellipsis", wrap="wrap")
    rule = gold_rule(SW / 2, 356, 150)
    sup = copy_text(ctx, "Support", 30, 612, sans(14, INK2, 400), "screen3Support", w=330)
    copy = node("Copy", head, num, unit, rule, sup)
    # ribbon of page edges: parallel strokes sweeping up into the numeral
    rib = node("Page-edge Ribbon").ensure()
    base = [(90, 612), (150, 560), (170, 470), (120, 390), (200, 330), (300, 270), (420, 250)]
    trims = []
    for i in range(9):
        off = (i - 4) * 4.2
        pts = [(x + off * 0.4, y + off) for x, y in base]
        col = [PAPER, PDEEP, PAPER, PSHADE, PAPER, PDEEP, PAPER, PSHADE, PAPER][i]
        tr = N("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Draw").ensure()
        sh = shape(f"Edge {i}", smooth(pts, closed=False), stroke(col, 3.2, cap="round", effects=[tr]))
        rib.add(sh)
        trims.append(tr)
    glint_tr = N("TrimPath", start=0, end=0.08, offset=0, name="Glint").ensure()
    glint = shape("Gold Glint", smooth(base, closed=False), stroke(GOLDL, 2.0, cap="round", effects=[glint_tr]), opacity=0).ensure()
    rib.add(glint)
    shadow = shape("Ribbon Shadow", smooth([(x + 6, y + 14) for x, y in base], closed=False),
                   stroke(PDEEP, 26, 0.35, cap="round"))
    stack = node("Source Book", x=70, y=628, rotation=-0.12).ensure()
    stack.add(shape("Edge Lines", *[rect(118, 0.8, x=4, y=-17 + j * 4) for j in range(9)], fill(PDEEP)))
    stack.add(shape("Pages", rect(120, 36, x=4, y=0), fill(PAPER)))
    stack.add(shape("Cover", rect(134, 46, x=0, y=0, r=4), fill(INK)))
    stack.add(shape("Cover Band", rect(4, 46, x=-50, y=0), fill(GOLD)))
    sc.content.add(copy, plx("ribbon", "mid", rib, shadow, stack))
    # choreography: edges flow in (staggered), numeral resolves from them
    for i, tr in enumerate(trims):
        sc.tw(tr, "end", 120 + i * 35, 950 + i * 35, 0.0, 1.0, "inout")
    sc.tw(stack, "y", 0, 300, 680, 640, "out")
    sc.tw(num, "opacity", 650, 1100, 0.0, 1.0, "soft")
    sc.tw(num, "scaleX", 650, 1200, 0.9, 1.0, "back")
    sc.tw(num, "scaleY", 650, 1200, 0.9, 1.0, "back")
    sc.tw(head, "opacity", 0, 400, 0.0, 1.0, "soft")
    sc.tw(unit, "opacity", 1000, 1300, 0.0, 1.0, "soft")
    sc.tw(rule, "scaleX", 1100, 1500, 0.0, 1.0, "inout")
    fade_up(sc, sup, 1300, 1750)
    sc.tw(glint, "opacity", 1200, 1500, 0.0, 1.0, "soft")
    # idle: a gold glint travels along the ribbon (offset loops 0->1, seamless)
    sc.idle_ms = 4000
    sc.idle_keys(glint_tr, "offset", [(0, 0, "linear"), (4000, 1, "linear")])


# ======================================================================= scene 4
def scene4(sc, ctx):
    copy, P = ctx["metric_copy"](sc, "readingHours", head_w=300)
    win = node("Night Window", x=SW / 2, y=610).ensure()
    sky_mask = shape("Sky Mask", arch(318, 300, x=0, y=0)).ensure()
    sky = node("Sky").ensure()
    sky.add(shape("Night", rect(330, 310, x=0, y=-155), fill(paint=lin(0, -300, 0, 0, [(0, INK, 1), (1, INK2, 1)]))))
    stars = []
    for i, (x, y, s) in enumerate([(-110, -250, 12), (-60, -200, 8), (90, -255, 14), (120, -180, 9), (-130, -150, 7),
                                   (40, -220, 6), (-20, -270, 9), (140, -110, 8)]):
        s_ = sparkle(f"Star {i}", x, y, s, GOLDL)
        stars.append(s_)
        sky.add(s_)
    town = node("Town").ensure()
    for i, (bx, h, w, roof) in enumerate([(-120, 90, 26, "dome"), (-90, 130, 22, "pointed"), (-56, 100, 30, "crenel"),
                                          (60, 120, 28, "pointed"), (96, 90, 30, "dome"), (126, 70, 22, "crenel")]):
        town.add(building(f"House {i}", bx, -40, w, h, PSHADE, roof, win=GOLDL))
    town.add(shape("Sail", poly([(0, -80), (0, -40), (26, -46)]), fill(PAPER), x=150 - 150, y=0))
    sky.add(town)
    sky.children.reverse()  # night gradient at the back, town in front
    sky.add(N("ClippingShape", sourceId=sky_mask.id, name="Window Clip"))
    frame = shape("Arch Frame", arch(326, 306, x=0, y=2), stroke(GOLD, 2.0))
    book, bparts = open_book("Open Book", 0, 40, 330, cover=OX)
    clouds_l = cloud("Cloud L", -150, -150, 0.95)
    clouds_r = cloud("Cloud R", 155, -60, 0.85)
    win.add(clouds_l, clouds_r, book, frame, sky, sky_mask)
    sc.content.add(copy, plx("window", "mid", win))
    # the moon itself is the carried object (persistent layer); here: reveal
    sc.tw(sky_mask, "scaleY", 150, 800, 0.0, 1.0, "inout")
    sc.tw(frame, "opacity", 100, 500, 0.0, 1.0, "soft")
    sc.tw(bparts["left"], "scaleX", 200, 760, 0.05, 1.0, "inout")
    sc.tw(bparts["right"], "scaleX", 200, 760, 0.05, 1.0, "inout")
    sc.tw(town, "y", 400, 1100, 60, 0, "back")
    sc.tw(clouds_l, "x", 300, 1200, -230, -150, "out")
    sc.tw(clouds_r, "x", 350, 1250, 230, 155, "out")
    for i, s in enumerate(stars):
        sc.tw(s, "scaleX", 800 + i * 70, 1100 + i * 70, 0.0, 1.0, "back")
        sc.tw(s, "scaleY", 800 + i * 70, 1100 + i * 70, 0.0, 1.0, "back")
    sc.idle_ms = 8000
    for i, s in enumerate(stars):
        o = (i * 830) % 4000
        sc.idle_keys(s, "opacity", [(0, 1, "sine"), (1000 + o, 0.35, "sine"), (2000 + o, 1, "sine"), (8000, 1, "linear")])
    sc.idle_keys(clouds_l, "x", [(0, -150, "sine"), (4000, -142, "sine"), (8000, -150, "linear")])
    sc.idle_keys(clouds_r, "x", [(0, 155, "sine"), (4000, 162, "sine"), (8000, 155, "linear")])


# ======================================================================= scene 5
def scene5(sc, ctx):
    copy, P = ctx["metric_copy"](sc, "genresExplored", layout="left", head_w=330)
    conv = ctx["conv"]
    theater = node("Paper Theater", x=SW / 2, y=640).ensure()
    floor = shape("Stage Floor", poly([(-190, 0), (190, 0), (150, -40), (-150, -40)]), fill(PDEEP))
    back = shape("Backdrop", rect(320, 260, x=0, y=-170), fill(paint=lin(0, -300, 0, -40, [(0, INK, 1), (1, INK2, 1)])))
    arches = []
    # three depth rows of three arches: back (small) to front (large)
    rows = [(-150, 0.62, PSHADE), (-95, 0.8, PAPER), (-40, 1.0, PARCH)]
    k = 0
    arch_nodes = node("Genre Arches").ensure()
    for r, (ry, sc_, col) in enumerate(rows):
        for c in (-1, 0, 1):
            k += 1
            ax = c * 98 * sc_
            g = node(f"Genre Arch {k}", x=ax, y=ry).ensure()
            w = 70 * sc_
            h = 120 * sc_
            g.add(shape("Inner", arch(w * 0.62, h * 0.72, x=0, y=0), fill(OX if k % 3 == 0 else (INK2 if k % 3 == 1 else GREEN), 0.85)))
            g.add(shape("Keystone", star(8, 8, 4, 0.3, x=0, y=-h * 0.82), fill(GOLD)))
            g.add(shape("Arch", arch(w, h, x=0, y=0), fill(col), stroke(GOLDD, 1.0)))
            # data: arch k is lit only when genresExplored >= k (faint outline otherwise)
            cv = conv(N("DataConverterRangeMapper", minInput=k - 1, maxInput=k, minOutput=0.18, maxOutput=1,
                        clampLower=True, clampUpper=True, name=f"Genre arch {k} lit"))
            lit = node(f"Arch {k} Data", g, x=0, y=0)
            lit.add(bind("genresExplored", 18, cv))
            arches.append((r, g))
            arch_nodes.add(lit)
    # reverse so front row draws on top
    arch_nodes.children.reverse()
    curt_l = node("Curtain L", x=-190, y=-300).ensure()
    curt_l.add(shape("Swag", smooth([(0, 0), (90, 0), (60, 80), (30, 200), (20, 300), (0, 300)], sharp={0, 1, 5}),
                     fill(paint=lin(0, 0, 90, 0, [(0, OXD, 1), (1, OX, 1)]))))
    curt_r = node("Curtain R", x=190, y=-300, scaleX=-1).ensure()
    curt_r.add(shape("Swag", smooth([(0, 0), (90, 0), (60, 80), (30, 200), (20, 300), (0, 300)], sharp={0, 1, 5}),
                     fill(paint=lin(0, 0, 90, 0, [(0, OXD, 1), (1, OX, 1)]))))
    pelmet = shape("Pelmet", rect(400, 26, x=0, y=-300), fill(OXD))
    tassels = shape("Pelmet Trim", rect(400, 2, x=0, y=-287), fill(GOLD))
    cone = shape("Spot Cone", poly([(-10, -290), (10, -290), (90, -40), (-90, -40)]),
                 fill(paint=lin(0, -290, 0, -40, [(0, GOLDL, 0.5), (1, GOLDL, 0)])), opacity=0).ensure()
    theater.add(tassels, pelmet, curt_l, curt_r, cone, arch_nodes, floor, back)
    sc.content.add(copy, plx("theater", "mid", theater))
    # choreography: curtains part, arches unfold row by row (hinge at base)
    sc.tw(curt_l, "scaleX", 100, 800, 2.1, 1.0, "inout")
    sc.tw(curt_r, "scaleX", 100, 800, -2.1, -1.0, "inout")
    sc.tw(back, "opacity", 0, 400, 0.0, 1.0, "soft")
    for i, (r, g) in enumerate(arches):
        t0 = 450 + r * 160 + (i % 3) * 60
        sc.tw(g, "scaleY", t0, t0 + 520, 0.0, 1.0, "back")
        sc.tw(g, "scaleX", t0, t0 + 420, 0.6, 1.0, "out")
    sc.tw(cone, "opacity", 800, 1300, 0.0, 1.0, "soft")
    sc.idle_ms = 6000
    sc.idle_keys(cone, "opacity", [(0, 1, "sine"), (3000, 0.7, "sine"), (6000, 1, "linear")])
    sc.idle_keys(curt_l, "scaleX", [(0, 1.0, "sine"), (3000, 1.04, "sine"), (6000, 1.0, "linear")])
    sc.idle_keys(curt_r, "scaleX", [(0, -1.0, "sine"), (3000, -1.04, "sine"), (6000, -1.0, "linear")])


# ======================================================================= scene 6
def scene6(sc, ctx):
    serif = ctx["serif"]
    italic = ctx["italic"]
    copy, P = ctx["metric_copy"](sc, "passagesSaved", layout="left", head_w=250)
    # the persistent ribbon becomes the big bookmark (see persistent pose 6)
    pile = node("Fragment Pile").ensure()
    frags = []
    targets = []
    for i in range(12):
        targets.append((318 + rng.uniform(-34, 26), 628 - i * 15, rng.uniform(-0.07, 0.07)))
    for i, (tx, ty, tr) in enumerate(targets):
        w = rng.choice([90, 120, 140, 80, 110])
        g = node(f"Fragment {i}", x=tx, y=ty, rotation=tr).ensure()
        g.add(shape("Lines", rect(w * 0.8, 1.8, y=-3.5), rect(w * 0.55, 1.8, x=-w * 0.12, y=2.5), fill(INK3, 0.55)))
        g.add(shape("Slip", rect(w, 15, r=1), fill(PAPER), stroke(PDEEP, 0.9)))
        frags.append(g)
    glyphs = []
    for i, (gch, gx, gy, gs, col) in enumerate([("“", 238, 410, 84, OX), ("¶", 372, 452, 50, GOLDD), ("”", 372, 548, 70, OX),
                                               ("§", 232, 520, 44, GOLDD)]):
        t = text(f"Glyph {i}", gx - 30, gy - gs * 0.6, [(italic(gs, col, 500), gch, None)], w=60, align="center")
        glyphs.append(t)
    for g in reversed(frags):
        pile.add(g)
    pile.children[0:0] = glyphs
    sc.content.add(copy, plx("pile", "mid", pile))
    starts = [(-60, 380), (450, 300), (-40, 560), (440, 640), (120, 720), (460, 450), (-80, 470), (200, 260),
              (480, 560), (60, 700), (-70, 300), (470, 380)]
    for i, g in enumerate(frags):
        sx, sy = starts[i]
        t0 = 200 + i * 75
        sc.tw(g, "x", t0, t0 + 700, sx, g.attrs["x"], "out")
        sc.tw(g, "y", t0, t0 + 700, sy, g.attrs["y"], "back")
        sc.tw(g, "rotation", t0, t0 + 700, rng.uniform(-1.2, 1.2), g.attrs["rotation"], "out")
        sc.tw(g, "opacity", t0, t0 + 200, 0.0, 1.0, "linear")
    for i, t in enumerate(glyphs):
        t0 = 900 + i * 110
        sc.tw(t, "opacity", t0, t0 + 300, 0.0, 1.0, "soft")
        sc.tw(t, "scaleX", t0, t0 + 500, 1.6, 1.0, "back")
        sc.tw(t, "scaleY", t0, t0 + 500, 1.6, 1.0, "back")
    sc.idle_ms = 6000
    for i, t in enumerate(glyphs):
        y0 = t.attrs["y"]
        o = i * 600
        sc.idle_keys(t, "y", [(0, y0, "sine"), (1500 + o, y0 - 5, "sine"), (3000 + o, y0, "sine"), (6000, y0, "linear")])


# ======================================================================= scene 7
def scene7(sc, ctx):
    copy, P = ctx["metric_copy"](sc, "longestStreakDays", layout="left", num_size=128, head_w=300)
    stack = node("Lit Stack", x=230, y=630).ensure()
    glow = shape("Lamp Glow", ellipse(420, 300, x=-40, y=-200),
                 fill(paint=rad(-40, -200, 210, [(0, GOLDL, 0.55), (1, GOLDL, 0)]))).ensure()
    books = node("Books").ensure()
    cols = [INK, OX, GREEN, INK2]
    hs = [46, 38, 52, 40]
    y = 0
    blocks = []
    for i in range(4):
        h = hs[i]
        b = node(f"Volume {i + 1}", x=(i % 2) * 10 - 5, y=y - h / 2).ensure()
        b.add(shape("Page Lines", *[rect(176, 0.8, x=6, y=-h / 2 + 6 + j * 4) for j in range(int((h - 10) // 4))],
                    fill(PDEEP)))
        b.add(shape("Pages", rect(178, h - 8, x=6, y=0), fill(PAPER)))
        b.add(shape("Cover", rect(196, h, x=0, y=0, r=4), fill(cols[i])))
        blocks.append(b)
        y -= h + 2
    for b in reversed(blocks):
        books.add(b)
    tabs = []
    tab_cols = [OX, GOLD, INK2, OX, GOLD, INK2, OX]
    tabs_n = node("Day Tabs").ensure()
    for i in range(7):
        t = node(f"Tab {i + 1}", x=96, y=-12 - i * 24).ensure()
        t.add(shape("Tab", rect(26, 16, x=13, y=0, rtl=0.1, rtr=6, rbl=0.1, rbr=6), fill(tab_cols[i])))
        tabs.append(t)
        tabs_n.add(t)
    stack.add(books, tabs_n, glow)
    sc.content.add(copy, plx("stack", "mid", stack))
    for i, b in enumerate(blocks):
        sc.tw(b, "y", 150 + i * 90, 650 + i * 90, b.attrs["y"] - 60, b.attrs["y"], "back")
        sc.tw(b, "opacity", 150 + i * 90, 300 + i * 90, 0.0, 1.0, "linear")
    for i, t in enumerate(tabs):
        t0 = 700 + i * 110   # ticking rhythm
        sc.tw(t, "x", t0, t0 + 180, 70, 96, "back")
        sc.tw(t, "opacity", t0, t0 + 60, 0.0, 1.0, "linear")
    sc.tw(glow, "opacity", 0, 900, 0.0, 1.0, "soft")
    sc.idle_ms = 7000
    for i, t in enumerate(tabs):
        o = 300 + i * 160
        sc.idle_keys(t, "x", [(0, 96, "linear"), (o, 96, "out"), (o + 140, 102, "inout"), (o + 360, 96, "linear"), (7000, 96, "linear")])
    sc.idle_keys(glow, "opacity", [(0, 1, "sine"), (3500, 0.75, "sine"), (7000, 1, "linear")])


# ======================================================================= scene 8
def scene8(sc, ctx):
    italic = ctx["italic"]
    copy, P = ctx["metric_copy"](sc, "bookClubChats", head_w=300)
    hero = node("Weave", x=SW / 2, y=560).ensure()
    book, bparts = open_book("Open Book", 0, 40, 300, cover=INK)
    # two ribbons weave around the book: each passes behind it, then over it
    trs = []

    def band(name, pts, col, w, edge):
        tr = N("TrimPath", start=0, end=1, modeValue="sequential", name="Draw").ensure()
        trs.append(tr)
        return shape(name, smooth(pts, closed=False), stroke(edge, w + 3, cap="round", effects=[tr]),
                     stroke(col, w, cap="round", effects=[N("TrimPath", start=0, end=1, name="Draw Twin").ensure()]))
    a_back = [(-210, -230), (-150, -150), (-60, -95), (40, -80)]
    a_front = [(40, -80), (120, -60), (150, -10), (90, 40), (-40, 46)]
    b_back = [(210, -250), (140, -170), (60, -100), (-40, -78)]
    b_front = [(-40, -78), (-120, -55), (-150, -5), (-90, 42), (40, 50)]
    back = node("Under").ensure()
    back.add(band("Gold Ribbon (behind)", b_back, GOLD, 12, GOLDD), band("Oxblood Ribbon (behind)", a_back, OX, 12, OXD))
    front = node("Over").ensure()
    front.add(band("Gold Ribbon (over)", b_front, GOLD, 12, GOLDD), band("Oxblood Ribbon (over)", a_front, OX, 12, OXD))
    quotes = []
    for i, (qx, qy, ch, s) in enumerate([(-130, -190, "“", 54), (120, -200, "”", 54), (0, -240, "“", 30)]):
        q = text(f"Quote {i}", qx - 25, qy, [(italic(s, OX if i < 2 else GOLDD, 500), ch, None)], w=50, align="center")
        quotes.append(q)
    hero.add(quotes, front, book, back)
    sc.content.add(copy, plx("weave", "mid", hero))
    sc.tw(bparts["left"], "scaleX", 100, 650, 0.05, 1.0, "inout")
    sc.tw(bparts["right"], "scaleX", 100, 650, 0.05, 1.0, "inout")
    twins = [c for sh in back.children + front.children for st in sh.children if st.tag == "Stroke"
             for c in st.children if c.tag == "TrimPath"]
    order = {0: 0, 1: 0, 2: 1, 3: 1}  # back segments first, then the over-pass
    for i, sh in enumerate(back.children + front.children):
        t0 = 350 + (0 if i < 2 else 650) + (i % 2) * 120
        for st in sh.children:
            if st.tag == "Stroke":
                for tr in st.children:
                    if tr.tag == "TrimPath":
                        sc.tw(tr, "end", t0, t0 + 700, 0.0, 1.0, "inout" if i < 2 else "out")
    for i, q in enumerate(quotes):
        fade_up(sc, q, 1100 + i * 150, 1500 + i * 150, 20)
    sc.idle_ms = 6000
    for i, q in enumerate(quotes):
        y0 = q.attrs["y"]
        sc.idle_keys(q, "y", [(0, y0, "sine"), (1500 + i * 500, y0 - 6, "sine"), (3000 + i * 500, y0, "sine"), (6000, y0, "linear")])


# ======================================================================= scene 9 (persona)
def emblem_wanderer():
    g = node("Emblem World Wanderer", x=0, y=0).ensure()
    parts = {}
    door_mask = shape("Door Mask", arch(150, 220, x=0, y=60)).ensure()
    land = node("Landscape").ensure()
    land.add(shape("Sky", rect(170, 240, x=0, y=-60), fill(paint=lin(0, -180, 0, 60, [(0, INK2, 1), (0.7, GOLDD, 1), (1, GOLDL, 1)]))))
    land.add(shape("Moon", ellipse(40, 40, x=40, y=-110), fill(PAPER)))
    land.add(shape("Mountains", poly([(-90, 40), (-50, -40), (-20, 0), (20, -70), (60, -10), (90, 40)]), fill(PDEEP)))
    land.add(shape("Castle", rect(14, 50, x=40, y=-5), rect(10, 70, x=55, y=-15), rect(30, 26, x=48, y=10), fill(PSHADE)))
    path_tr = N("TrimPath", start=0, end=1, name="Draw").ensure()
    land.add(shape("Path", smooth([(0, 60), (-20, 30), (10, 0), (-5, -30)], closed=False),
                   stroke(GOLDL, 3, cap="round", effects=[path_tr])))
    land.children.reverse()  # sky at the back
    land.add(N("ClippingShape", sourceId=door_mask.id, name="Door Clip"))
    frame = shape("Door Frame", arch(160, 228, x=0, y=62), stroke(GOLD, 2.5))
    book, bp = open_book("Doorway Book", 0, 110, 250, cover=OX)
    stars = [sparkle(f"Star {i}", x, y, s, GOLDL) for i, (x, y, s) in enumerate([(-110, -140, 14), (100, -170, 18), (120, -40, 10), (-120, -30, 9)])]
    g.add(stars, frame, land, door_mask, book)
    parts.update(mask=door_mask, path=path_tr, book=bp, stars=stars, frame=frame)
    return g, parts


def emblem_diver():
    """Layered paper well: hollow paper rings receding into a lit depth."""
    g = node("Emblem Deep Diver", x=0, y=0).ensure()
    rings = []
    cols = [PAPER, PARCH, PSHADE, PDEEP, GOLDD, OXD]
    for i in range(6):
        w = 250 - i * 36
        h = w * 0.5
        r = node(f"Layer {i + 1}", x=0, y=-40 + i * 24).ensure()
        r.add(shape("Rim Edge", ellipse(w - 22, h - 14, y=2), stroke("000000", 3, 0.18)))
        ring = shape("Paper Ring", ellipse(w, h), ellipse(w - 26, h - 16, y=3),
                     N("Fill", solid(cols[i]), fillRule="evenOdd", name="Fill"), stroke(GOLD if i % 2 == 0 else OXD, 1.2))
        r.add(ring)
        rings.append(r)
    hole = shape("Depth", ellipse(70, 32, x=0, y=-40 + 6 * 24 - 8), fill(INK)).ensure()
    core = shape("Deep Glow", ellipse(60, 26, x=0, y=-40 + 6 * 24 - 8),
                 fill(paint=rad(0, -40 + 6 * 24 - 8, 30, [(0, GOLDL, 1), (1, GOLD, 0)]))).ensure()
    tr = N("TrimPath", start=0, end=1, name="Draw").ensure()
    spiral = [(math.cos(a) * (118 - a * 11), -46 + a * 13 + math.sin(a) * 30) for a in [i * 0.55 for i in range(13)]]
    rib = shape("Descending Ribbon", smooth(spiral, closed=False), stroke(GOLDL, 3, cap="round", effects=[tr]))
    g.add(rib)
    g.add(rings)          # outermost first => drawn on top; inner layers show through
    g.add(core, hole)
    return g, dict(rings=rings, tr=tr, core=core)


def emblem_night():
    g = node("Emblem Night Reader", x=0, y=0).ensure()
    swing = node("Crescent Swing", x=0, y=-150).ensure()
    cres = shape("Crescent", smooth([(0, 0), (60, 30), (90, 110), (60, 190), (0, 220), (40, 180), (58, 110), (40, 40)],
                                    sharp={0, 4}), fill(INK), x=-40, y=0)
    tassel = node("Tassel", x=-40, y=220).ensure()
    tassel.add(shape("Cord", rect(3, 60, x=0, y=30), fill(OX)))
    tassel.add(shape("Tail", poly([(-10, 60), (10, 60), (10, 96), (0, 86), (-10, 96)]), fill(OX)))
    swing.add(tassel, cres)
    stars = [sparkle(f"Star {i}", x, y, s, INK) for i, (x, y, s) in enumerate([(70, -110, 18), (110, -40, 10), (-110, -90, 12), (90, 40, 8), (-100, 30, 9)])]
    lamp = shape("Reading Glow", ellipse(200, 80, x=40, y=120), fill(paint=rad(40, 120, 100, [(0, PAPER, 0.8), (1, PAPER, 0)]))).ensure()
    book, bp = open_book("Night Book", 40, 130, 150, cover=INK)
    g.add(stars, swing, book, lamp)
    return g, dict(swing=swing, tassel=tassel, stars=stars, lamp=lamp)


def emblem_collector():
    g = node("Emblem Curious Collector", x=0, y=0).ensure()
    fan = node("Fan", x=0, y=120).ensure()
    cols = [OX, INK, GREEN, GOLDD, OXD, INK2, OX, GREEN, INK]
    spines = []
    for i in range(9):
        a = (i - 4) * 0.24
        s = node(f"Spine {i + 1}", x=0, y=0).ensure()
        s.add(shape("Band", rect(26, 2, y=-190), rect(26, 2, y=-180), fill(GOLD)))
        s.add(shape("Body", rect(30, 210, x=0, y=-105, r=3), fill(cols[i]), stroke(OXD, 0.6)))
        spines.append((s, a))
    for s, a in spines:
        fan.add(s)
    hub = shape("Hub", ellipse(26, 26), fill(GOLD), x=0, y=120)
    g.add(hub, fan)
    return g, dict(spines=spines, fan=fan)


def scene9(sc, ctx):
    serif, sans, italic = ctx["serif"], ctx["sans"], ctx["italic"]
    sc.enter_ms = 2300
    label = copy_text(ctx, "Persona Label", 20, 6, sans(12, GOLDD, 500, ls=1.8), "personaLabel", w=350)
    name = text("Persona Name", 15, 28, [(serif(46, OX, 600, lh=48), ctx["DATA"].get("personaName"), bind("personaName", 268))],
                w=360, h=56, align="center", overflow="fitFontSize", wrap="noWrap", valign="middle")
    rule = gold_rule(SW / 2, 96, 180)
    desc = copy_text(ctx, "Persona Description", 30, 108, italic(21, INK, 500, lh=24), "personaDescription", w=330,
                     h=50, overflow="ellipsis", wrap="wrap")
    copy = node("Copy", label, name, rule, desc)
    plate = node("Persona Plate", x=SW / 2, y=652).ensure()
    plate_fill = solid(INK)
    plate_fill.add(bind("personaColor", 37))
    plate.add(shape("Plate Inner Rule", arch(296, 440, x=0, y=-12), stroke(GOLD, 1.2)))
    plate.add(shape("Plate", arch(320, 464, x=0, y=0), N("Fill", plate_fill, name="Fill"), stroke(GOLD, 2.4)))
    emblems = node("Emblems", x=0, y=-230).ensure()
    e0, p0 = emblem_wanderer()
    e1, p1 = emblem_diver()
    e2, p2 = emblem_night()
    e3, p3 = emblem_collector()
    for e in (e0, e1, e2, e3):
        e.attrs["opacity"] = 0
    emblems.add(e0, e1, e2, e3)
    plate.children.insert(0, emblems)
    sc.content.add(copy, plx("plate", "near", plate))
    # scene choreography: anticipation (rule), plate rises, then copy
    sc.tw(rule, "scaleX", 0, 450, 0.0, 1.0, "inout")
    sc.tw(plate, "scaleY", 250, 950, 0.0, 1.0, "back")
    sc.tw(plate, "scaleX", 250, 800, 0.7, 1.0, "out")
    fade_up(sc, label, 300, 700)
    sc.tw(name, "opacity", 1300, 1700, 0.0, 1.0, "soft")
    sc.tw(name, "scaleX", 1300, 1900, 0.85, 1.0, "back")
    sc.tw(name, "scaleY", 1300, 1900, 0.85, 1.0, "back")
    fade_up(sc, desc, 1600, 2100)

    # ---- persona layer: unique choreography for every persona
    L = Layer("Persona")
    anims = []
    E = [(e0, p0), (e1, p1), (e2, p2), (e3, p3)]

    def only(a, k):
        for j, (e, _) in enumerate(E):
            a.set(e, "opacity", 1.0 if j == k else 0.0)

    def pose(a, k, settled, t_off=0):
        """Key persona k either at its start pose or its settled pose."""
        e, p = E[k]
        if k == 0:
            a.set(p["mask"], "scaleY", 1.0 if settled else 0.0)
            a.set(p["path"], "end", 1.0 if settled else 0.0)
            a.set(p["book"]["left"], "scaleX", 1.0 if settled else 0.05)
            a.set(p["book"]["right"], "scaleX", 1.0 if settled else 0.05)
            for s in p["stars"]:
                a.set(s, "scaleX", 1.0 if settled else 0.0).set(s, "scaleY", 1.0 if settled else 0.0)
        elif k == 1:
            for i, r in enumerate(p["rings"]):
                a.set(r, "opacity", 1.0 if settled else 0.0)
                a.set(r, "y", -40 + i * 24 if settled else -160)
            a.set(p["tr"], "end", 1.0 if settled else 0.0)
            a.set(p["core"], "opacity", 1.0 if settled else 0.0)
        elif k == 2:
            a.set(p["swing"], "rotation", 0.0 if settled else 1.3)
            a.set(p["tassel"], "rotation", 0.0 if settled else -0.6)
            for s in p["stars"]:
                a.set(s, "opacity", 1.0 if settled else 0.0)
            a.set(p["lamp"], "opacity", 1.0 if settled else 0.0)
        else:
            for s, ang in p["spines"]:
                a.set(s, "rotation", ang if settled else 0.0)
            a.set(p["fan"], "y", 120 if settled else 260)

    hidden = Anim("Persona Hidden", 17)
    for k in range(4):
        pose(hidden, k, False)
    only(hidden, -1)
    anims.append(hidden)
    s_hidden = L.state(hidden, 100, 0)
    L.start(s_hidden)
    D = 850  # reveal waits for the plate (anticipation)
    for k in range(4):
        e, p = E[k]
        rv = Anim(f"Persona {k} Reveal", 2400)
        only(rv, k)
        pose(rv, k, False)
        if k == 0:   # book opens, doorway rises, path draws, stars burst
            rv.tw(p["book"]["left"], "scaleX", D, D + 500, 0.05, 1.0, "inout")
            rv.tw(p["book"]["right"], "scaleX", D, D + 500, 0.05, 1.0, "inout")
            rv.tw(p["mask"], "scaleY", D + 300, D + 1000, 0.0, 1.0, "back")
            rv.tw(p["path"], "end", D + 800, D + 1400, 0.0, 1.0, "inout")
            for i, s in enumerate(p["stars"]):
                t0 = D + 900 + i * 110
                rv.tw(s, "scaleX", t0, t0 + 400, 0.0, 1.0, "back").tw(s, "scaleY", t0, t0 + 400, 0.0, 1.0, "back")
        elif k == 1:  # paper layers drop into the well, ribbon spirals down
            for i, r in enumerate(p["rings"]):
                t0 = D + i * 110
                rv.tw(r, "y", t0, t0 + 600, -160, -40 + i * 24, "back")
                rv.tw(r, "opacity", t0, t0 + 200, 0.0, 1.0, "linear")
            rv.tw(p["tr"], "end", D + 600, D + 1500, 0.0, 1.0, "inout")
            rv.tw(p["core"], "opacity", D + 1100, D + 1500, 0.0, 1.0, "soft")
        elif k == 2:  # crescent swings in on its hinge, tassel follows through
            rv.k(p["swing"], "rotation", 0, 1.3, "hold")
            rv.k(p["swing"], "rotation", D, 1.3, ("elastic", 0.6, 0.35))
            rv.k(p["swing"], "rotation", D + 1300, 0.0)
            rv.k(p["tassel"], "rotation", 0, -0.6, "hold")
            rv.k(p["tassel"], "rotation", D + 150, -0.6, ("elastic", 0.8, 0.3))
            rv.k(p["tassel"], "rotation", D + 1500, 0.0)
            for i, s in enumerate(p["stars"]):
                t0 = D + 700 + i * 120
                rv.tw(s, "opacity", t0, t0 + 250, 0.0, 1.0, "soft")
            rv.tw(p["lamp"], "opacity", D + 500, D + 1100, 0.0, 1.0, "soft")
        else:         # spines fan out from a single stack, hinge by hinge
            rv.tw(p["fan"], "y", D, D + 450, 260, 120, "back")
            for i, (s, ang) in enumerate(p["spines"]):
                t0 = D + 350 + abs(i - 4) * 70
                rv.tw(s, "rotation", t0, t0 + 600, 0.0, ang, "back")
        anims.append(rv)
        idle = Anim(f"Persona {k} Idle", 6000, loop="loop")
        if k == 0:
            for i, s in enumerate(p["stars"]):
                o = i * 500
                idle.k(s, "opacity", 0, 1, "sine").k(s, "opacity", 1200 + o, 0.4, "sine").k(s, "opacity", 2400 + o, 1, "sine").k(s, "opacity", 6000, 1)
        elif k == 1:
            idle.k(p["core"], "opacity", 0, 1, "sine").k(p["core"], "opacity", 3000, 0.5, "sine").k(p["core"], "opacity", 6000, 1)
        elif k == 2:
            idle.k(p["swing"], "rotation", 0, 0, "sine").k(p["swing"], "rotation", 1500, 0.05, "sine") \
                .k(p["swing"], "rotation", 4500, -0.05, "sine").k(p["swing"], "rotation", 6000, 0)
            idle.k(p["tassel"], "rotation", 0, 0, "sine").k(p["tassel"], "rotation", 1800, -0.08, "sine") \
                .k(p["tassel"], "rotation", 4800, 0.08, "sine").k(p["tassel"], "rotation", 6000, 0)
        else:
            idle.k(p["fan"], "scaleX", 0, 1, "sine").k(p["fan"], "scaleX", 3000, 1.03, "sine").k(p["fan"], "scaleX", 6000, 1)
        anims.append(idle)
        static = Anim(f"Persona {k} Static", 17)
        only(static, k)
        pose(static, k, True)
        anims.append(static)
        hold = Anim(f"Persona {k} Leaving", 650)
        only(hold, k)
        anims.append(hold)
        s_rv = L.state(rv, 360, -300 + k * 200)
        s_id = L.state(idle, 620, -300 + k * 200)
        s_st = L.state(static, 880, -300 + k * 200)
        s_lv = L.state(hold, 1140, -300 + k * 200)
        here = lambda: cnum("currentScreen", "equal", 9)
        row = lambda: cnum("_personaRow", "equal", k)
        trans(s_hidden, s_rv, here(), row(), cbool("reducedMotion", False))
        trans(s_hidden, s_st, here(), row(), cbool("reducedMotion", True), ms=200)
        trans(s_rv, s_id, exit_pct=100)
        for s in (s_rv, s_id, s_st):
            trans(s, s_lv, cnum("currentScreen", "notEqual", 9))
            # runtime persona change: clear first, never mix two personas
            trans(s, s_hidden, cnum("_personaRow", "notEqual", k), ms=180)
        trans(s_rv, s_st, cbool("reducedMotion", True), ms=150)
        trans(s_id, s_st, cbool("reducedMotion", True), ms=150)
        trans(s_lv, s_hidden, exit_pct=100)
        trans(s_lv, s_st, here(), row(), ms=120)
    return [(L, anims)]


# ======================================================================= card (summary + share)
def card_content(ctx, prefix="Card"):
    serif, sans, italic = ctx["serif"], ctx["sans"], ctx["italic"]
    D = ctx["DATA"]
    W, H = 320, 440
    g = node(f"{prefix}", x=0, y=0).ensure()
    parts = {}
    # paper card with jacket rules
    face = shape("Card Face", rect(W, H, x=0, y=0, r=6), fill(PAPER), stroke(PDEEP, 1))
    inner = shape("Jacket Rule", rect(W - 22, H - 22, x=0, y=0, r=3), stroke(GOLD, 1))
    corner = [shape(f"Corner {i}", star(10, 10, 4, 0.3, x=cx, y=cy), fill(GOLD))
              for i, (cx, cy) in enumerate([(-W / 2 + 11, -H / 2 + 11), (W / 2 - 11, -H / 2 + 11),
                                             (-W / 2 + 11, H / 2 - 11), (W / 2 - 11, H / 2 - 11)])]
    wm = text("Card Wordmark", -W / 2, -H / 2 + 26, [(italic(30, INK, 600), "Marginalia", None)], w=W, align="center")
    yr = text("Card Year", -W / 2, -H / 2 + 64, [(sans(12, GOLDD, 500, ls=3), str(D.get("year")), bind("yearText", 268))],
              w=W, align="center")
    # persona medallion (colour bound; four mini emblems switch with the row)
    med = node("Persona Medallion", x=0, y=-H / 2 + 126).ensure()
    mfill = solid(INK)
    mfill.add(bind("personaColor", 37))
    minis = []
    m0 = shape("Mini Door", arch(18, 26, x=0, y=12), fill(GOLDL)).ensure()
    m1 = shape("Mini Well", ellipse(30, 12, y=-6), ellipse(20, 8, y=2), ellipse(10, 4, y=8), stroke(GOLDL, 1.4)).ensure()
    m2 = shape("Mini Crescent", smooth([(0, -14), (10, -6), (12, 2), (6, 12), (0, 14), (6, 4), (6, -4)], sharp={0, 4}),
               fill(INK), x=-4).ensure()
    m3 = node("Mini Fan", x=0, y=10).ensure()
    for i in range(5):
        m3.add(shape("Leaf", rect(5, 22, y=-11), fill([OX, INK, GREEN, OXD, INK2][i]), rotation=(i - 2) * 0.35))
    for m in (m0, m1, m2, m3):
        m.attrs["opacity"] = 0
        minis.append(m)
    med.add(minis)
    med.add(shape("Medallion", ellipse(52, 52), N("Fill", mfill, name="Fill"), stroke(GOLD, 2)))
    pname = text("Card Persona", -W / 2 + 10, -H / 2 + 158, [(serif(26, OX, 600), D.get("personaName"), bind("personaName", 268))],
                 w=W - 20, h=30, align="center", overflow="fitFontSize", wrap="noWrap")
    rname = text("Card Reader", -W / 2 + 20, -H / 2 + 190, [(italic(16, INK2, 500), D.get("userName"), bind("userName", 268))],
                 w=W - 40, h=20, align="center", overflow="ellipsis", wrap="wrap", valign="top", opacity=0).ensure()
    rule = gold_rule(0, -H / 2 + 222, 200)
    stats = []
    spec = [("booksFinished", "screen2Unit"), ("pagesRead", "screen3Unit"), ("readingHours", "screen4Unit"),
            ("genresExplored", "screen5Unit"), ("passagesSaved", "screen6Unit")]
    pos = [(-80, 250), (80, 250), (-80, 318), (80, 318), (0, 386)]
    for (stat, unit), (sx, sy) in zip(spec, pos):
        s = node(f"Stat {stat}", x=sx, y=-H / 2 + sy).ensure()
        s.add(text("Value", -75, -30, [(serif(34, OX, 600, lining=True), f"{int(D.get(stat, 0)):,}", bind(f"{stat}Text", 268))],
                   w=150, h=38, align="center", overflow="fitFontSize", wrap="noWrap", valign="middle"))
        s.add(text("Unit", -75, 10, [(sans(10.5, INK2, 500, ls=1.2), D.get(unit), bind(unit, 268))],
                   w=150, h=15, align="center", overflow="ellipsis", wrap="wrap", valign="top"))
        stats.append(s)
    g.add(wm, yr, med, pname, rname, rule, stats, corner, inner, face)
    parts.update(face=face, wm=wm, yr=yr, med=med, minis=minis, pname=pname, rname=rname, rule=rule, stats=stats)
    return g, parts


def card_layers(prefix, parts):
    """Persona mini-emblem + optional-name layers (shared by scene 10 and ShareCard)."""
    out = []
    L = Layer(f"{prefix} Persona Mini")
    anims = []
    states = []
    for k in range(4):
        a = Anim(f"{prefix} Mini {k}", 17)
        for j, m in enumerate(parts["minis"]):
            a.set(m, "opacity", 1.0 if j == k else 0.0)
        anims.append(a)
        states.append(L.state(a, 100 + k * 240, 0))
    L.start(states[0])
    for k, s in enumerate(states):
        for j, s2 in enumerate(states):
            if j != k:
                trans(s, s2, cnum("_personaRow", "equal", j))
    out.append((L, anims))
    L2 = Layer(f"{prefix} Reader Name")
    hide = Anim(f"{prefix} Name Hidden", 17).set(parts["rname"], "opacity", 0.0)
    show = Anim(f"{prefix} Name Shown", 17).set(parts["rname"], "opacity", 1.0)
    s_h = L2.state(hide, 100, 0)
    s_s = L2.state(show, 360, 0)
    L2.start(s_h)
    trans(s_h, s_s, cbool("shareIncludeName", True))
    trans(s_s, s_h, cbool("shareIncludeName", False))
    out.append((L2, [hide, show]))
    return out


def scene10(sc, ctx):
    serif, sans, italic = ctx["serif"], ctx["sans"], ctx["italic"]
    sc.enter_ms = 2000
    head = copy_text(ctx, "Summary Headline", 85, 0, serif(32, INK, 500, lh=34), "summaryHeadline", w=220,
                     h=72, overflow="fitFontSize", wrap="wrap")
    sup = copy_text(ctx, "Summary Support", 30, 80, sans(14, INK2, 400, lh=18), "summarySupport", w=330, h=36,
                    overflow="ellipsis", wrap="wrap")
    full = node("Full Summary").ensure()
    card, cp = card_content(ctx, "Summary Card")
    card_holder = node("Card Holder", card, x=SW / 2, y=346).ensure()
    shadow = shape("Card Shadow", rect(320, 440, x=6, y=10, r=8), N("Fill", solid("000000", 0.18),
                   N("Feather", strength=14, name="Feather"), fillRule="clockwise", name="Fill"))
    card_holder.children.append(shadow)
    skyline = node("Skyline").ensure()
    for i, (bx, h, w, roof) in enumerate([(30, 160, 30, "pointed"), (64, 120, 26, "dome"), (330, 150, 30, "crenel"), (362, 190, 24, "pointed")]):
        skyline.add(building(f"Spire {i}", bx, 640, w, h, PSHADE, roof, win=PDEEP))
    full.add(head, sup, card_holder, plx("skyline", "far", skyline))
    # zero / new user: a small complete motif + invitation
    empty = node("Empty Summary", opacity=0).ensure()
    eh = copy_text(ctx, "Empty Headline", 40, 150, serif(36, INK, 500, lh=40), "emptyHeadline", w=310, h=84,
                   overflow="fitFontSize", wrap="wrap")
    es = copy_text(ctx, "Empty Support", 30, 248, sans(15, INK2, 400, lh=19), "emptySupport", w=330, h=40,
                   overflow="ellipsis", wrap="wrap")
    eb, ebp = open_book("Small Book", SW / 2, 470, 200, cover=OX)
    empty.add(eh, es, eb, sparkle("Spark", SW / 2, 360, 16))
    sc.content.add(full, empty)
    # assembly: card lands, rules draw, medallion turns, stats file in
    sc.tw(card_holder, "y", 0, 700, 420, 346, "back")
    sc.tw(card_holder, "rotation", 0, 800, -0.08, 0.0, "back")
    sc.tw(card_holder, "opacity", 0, 200, 0.0, 1.0, "linear")
    sc.tw(cp["wm"], "opacity", 350, 700, 0.0, 1.0, "soft")
    sc.tw(cp["med"], "scaleX", 450, 950, 0.0, 1.0, "back")
    sc.tw(cp["med"], "scaleY", 450, 950, 0.0, 1.0, "back")
    sc.tw(cp["med"], "rotation", 450, 950, -1.2, 0.0, "out")
    sc.tw(cp["rule"], "scaleX", 650, 1050, 0.0, 1.0, "inout")
    for i, s in enumerate(cp["stats"]):
        t0 = 800 + i * 110
        sc.tw(s, "opacity", t0, t0 + 260, 0.0, 1.0, "soft")
        sc.tw(s, "y", t0, t0 + 420, s.attrs["y"] + 16, s.attrs["y"], "back")
    fade_up(sc, head, 0, 400, 10)
    fade_up(sc, sup, 150, 550, 10)
    sc.tw(skyline, "y", 300, 1200, 120, 0, "out")
    sc.tw(eb, "scaleY", 200, 800, 0.0, 1.0, "back")
    sc.idle_ms = 8000
    sc.idle_keys(cp["med"], "rotation", [(0, 0, "sine"), (4000, 0.06, "sine"), (8000, 0, "linear")])
    # layers: full vs empty, and the card's persona/name layers
    L = Layer("Summary Mode")
    a_full = Anim("Summary Full", 17).set(full, "opacity", 1.0).set(empty, "opacity", 0.0)
    a_empty = Anim("Summary Empty", 17).set(full, "opacity", 0.0).set(empty, "opacity", 1.0)
    s_f = L.state(a_full, 100, 0)
    s_e = L.state(a_empty, 360, 0)
    L.start(s_f)
    trans(s_f, s_e, cbool("_hasStats", False))
    trans(s_e, s_f, cbool("_hasStats", True))
    return [(L, [a_full, a_empty])] + card_layers("Summary Card", cp)


# ======================================================================= persistent objects
RIBBON_POSES = {
    #  x,   end-y, sway, width, tilt     (kept clear of the copy: edges, or art zones)
    1: (378, 300, 3, 18, -40),   # runs down the margin into the pop-up book
    2: (378, 128, 3, 18, 0),
    3: (12, 214, 5, 18, 4),
    4: (378, 112, 3, 18, 0),
    5: (378, 226, -4, 18, 0),
    6: (322, 470, 5, 44, 0),     # becomes the bookmark the fragments collect under
    7: (378, 168, 4, 18, -3),
    8: (12, 300, 5, 18, 10),
    9: (378, 150, 2, 18, 0),
    10: (362, 206, 2, 18, -4),   # drapes over the share card's corner
}


def ribbon_vertices(end, sway, w, tilt):
    top = -110
    ts = [0, 0.25, 0.5, 0.75, 1.0]
    cxs = [sway * math.sin(math.pi * t) + tilt * t for t in ts]
    cys = [top + (end - top) * t for t in ts]
    left = [(cx - w / 2, cy) for cx, cy in zip(cxs, cys)]
    right = [(cx + w / 2, cy) for cx, cy in zip(cxs, cys)]
    ex, ey = cxs[-1], cys[-1]
    tail = [(ex - w / 2, ey + w * 0.9), (ex, ey + w * 0.25), (ex + w / 2, ey + w * 0.9)]
    return left + tail + right[::-1]


def persistent(ctx):
    root = node("Persistent (above scenes)").ensure()
    layers = []
    # ---- the bookmark ribbon: one object for the whole story
    verts0 = ribbon_vertices(*RIBBON_POSES[1][1:])
    path = N("PointsPath", isClosed=True, isClockwise=False, name="Ribbon Path").ensure()
    vnodes = []
    for x, y in verts0:
        v = N("StraightVertex", x=x, y=y).ensure()
        vnodes.append(v)
        path.add(v)
    ribbon_shape = shape("Ribbon", path, fill(paint=lin(-12, 0, 12, 0, [(0, OXD, 1), (0.45, OXL, 1), (1, OXD, 1)])))
    sheen = shape("Ribbon Stitch", rect(1, 40, y=-60), fill(GOLD, 0.6))
    rib_sway = node("Ribbon Sway", ribbon_shape, x=0, y=0).ensure()
    ribbon = node("Bookmark Ribbon", rib_sway, x=RIBBON_POSES[1][0], y=0).ensure()
    root.add(ribbon)
    L = Layer("Ribbon")
    anims = []
    states = {}
    for n, (x, end, sway, w, tilt) in RIBBON_POSES.items():
        a = Anim(f"Ribbon Pose {n}", 17)
        a.set(ribbon, "x", x)
        for v, (vx, vy) in zip(vnodes, ribbon_vertices(end, sway, w, tilt)):
            a.set(v, "x", vx).set(v, "y", vy)
        anims.append(a)
        states[n] = L.state(a, 100 + ((n - 1) % 5) * 260, -200 + ((n - 1) // 5) * 400 + (n % 2) * 60)
    L.start(states[1])
    for n, s in states.items():
        for m, s2 in states.items():
            if m == n:
                continue
            here = cnum("currentScreen", "equal", m)
            trans(s, s2, here, cbool("reducedMotion", False), ms=760, ease="inout")
            trans(s, s2, cnum("currentScreen", "equal", m), cbool("reducedMotion", True), ms=0)
    layers.append((L, anims))
    # idle flutter of the ribbon (separate layer, separate property)
    L2 = Layer("Ribbon Flutter")
    fl = Anim("Ribbon Flutter", 5000, loop="loop")
    fl.k(rib_sway, "rotation", 0, 0.0, "sine").k(rib_sway, "rotation", 1250, 0.012, "sine") \
      .k(rib_sway, "rotation", 3750, -0.012, "sine").k(rib_sway, "rotation", 5000, 0.0)
    still = Anim("Ribbon Still", 17).set(rib_sway, "rotation", 0.0)
    s_fl = L2.state(fl, 100, 0)
    s_still = L2.state(still, 360, 0)
    L2.start(s_fl)
    trans(s_fl, s_still, cbool("reducedMotion", True), ms=150)
    trans(s_still, s_fl, cbool("reducedMotion", False), ms=150)
    layers.append((L2, [fl, still]))

    # ---- the moon: carried from scene 4 into scene 5 (becomes the spotlight)
    moon = node("Carried Moon", x=SW / 2, y=280, opacity=0).ensure()
    line = shape("Pendulum Line", rect(1.4, 120, x=0, y=60), fill(GOLD)).ensure()
    disc = node("Moon Disc", x=0, y=120).ensure()
    halo = shape("Halo", ellipse(130, 130), fill(paint=rad(0, 0, 65, [(0, PAPER, 0.55), (1, PAPER, 0)]))).ensure()
    disc.add(shape("Craters", ellipse(14, 12, x=-14, y=-8), ellipse(9, 8, x=12, y=10), ellipse(7, 6, x=8, y=-16),
                   fill(PDEEP, 0.75)))
    disc.add(shape("Moon", ellipse(76, 76), fill(paint=rad(-12, -14, 50, [(0, PAPER, 1), (1, PSHADE, 1)])), stroke(GOLD, 1.2)))
    disc.add(halo)
    moon.add(line, disc)
    root.add(moon)
    L3 = Layer("Moon Carrier")
    a_hidden = Anim("Moon Hidden", 17).set(moon, "opacity", 0.0).set(moon, "scaleX", 0.6).set(moon, "scaleY", 0.6)
    a_swing = Anim("Moon Swing In", 1600)
    a_swing.set(moon, "x", SW / 2).set(moon, "y", 300).set(line, "opacity", 1).set(halo, "opacity", 1)
    a_swing.set(moon, "scaleX", 1).set(moon, "scaleY", 1)
    a_swing.tw(moon, "opacity", 150, 450, 0.0, 1.0, "soft")
    a_swing.k(moon, "rotation", 0, -1.1, "hold").k(moon, "rotation", 150, -1.1, ("elastic", 0.55, 0.3)).k(moon, "rotation", 1550, 0.0)
    a_idle = Anim("Moon Pendulum", 6000, loop="loop")
    a_idle.k(moon, "rotation", 0, 0.0, "sine").k(moon, "rotation", 1500, 0.07, "sine").k(moon, "rotation", 4500, -0.07, "sine") \
        .k(moon, "rotation", 6000, 0.0)
    a_moon_static = Anim("Moon Static", 17).set(moon, "x", SW / 2).set(moon, "y", 300).set(moon, "opacity", 1) \
        .set(moon, "rotation", 0).set(moon, "scaleX", 1).set(moon, "scaleY", 1).set(line, "opacity", 1).set(halo, "opacity", 1)
    # pose 5: small spotlight lamp above the theater's pelmet
    a_spot = Anim("Moon As Spotlight", 17).set(moon, "x", SW / 2).set(moon, "y", 270).set(moon, "rotation", 0) \
        .set(moon, "scaleX", 0.34).set(moon, "scaleY", 0.34).set(moon, "opacity", 1).set(line, "opacity", 0).set(halo, "opacity", 1)
    anims3 = [a_hidden, a_swing, a_idle, a_moon_static, a_spot]
    s_h = L3.state(a_hidden, 100, 0)
    s_sw = L3.state(a_swing, 360, -160)
    s_id = L3.state(a_idle, 620, -160)
    s_ms = L3.state(a_moon_static, 360, 160)
    s_sp = L3.state(a_spot, 880, 0)
    L3.start(s_h)
    rmf, rmt = (lambda: cbool("reducedMotion", False)), (lambda: cbool("reducedMotion", True))
    at = lambda n: cnum("currentScreen", "equal", n)
    trans(s_h, s_sw, at(4), cnum("_navDir", "greaterThan", 0), rmf())
    trans(s_h, s_ms, at(4), cnum("_navDir", "lessThan", 0), rmf(), ms=500, ease="soft")
    trans(s_h, s_ms, at(4), rmt(), ms=200)
    trans(s_sw, s_id, exit_pct=100)
    trans(s_ms, s_id, rmf(), at(4))
    for s in (s_sw, s_id, s_ms):
        trans(s, s_sp, at(5), rmf(), ms=820, ease="inout")      # the carry
        trans(s, s_sp, at(5), rmt(), ms=200)
        trans(s, s_h, cnum("currentScreen", "notEqual", 4), cnum("currentScreen", "notEqual", 5), ms=350, ease="soft")
    trans(s_id, s_ms, rmt(), ms=150)
    trans(s_sp, s_ms, at(4), rmf(), ms=820, ease="inout")         # carried back
    trans(s_sp, s_ms, at(4), rmt(), ms=200)
    trans(s_sp, s_h, cnum("currentScreen", "notEqual", 5), cnum("currentScreen", "notEqual", 4), ms=350, ease="soft")
    trans(s_h, s_sp, at(5), ms=400, ease="soft")
    layers.append((L3, anims3))

    # ---- page-turn fold shadow (cast by the turning leaf)
    fold = node("Page Fold", x=SW, y=0, opacity=0).ensure()
    fold.add(shape("Fold Shadow", rect(70, SH + 300, x=35, y=SH / 2),
                   fill(paint=lin(0, 0, 70, 0, [(0, INK, 0.38), (1, INK, 0)]))))
    fold.add(shape("Fold Light", rect(10, SH + 300, x=-5, y=SH / 2),
                   fill(paint=lin(-10, 0, 0, 0, [(0, "FFFFFF", 0), (1, "FFFFFF", 0.7)]))))
    root.add(fold)
    L4 = Layer("Page Turn")
    ms = ctx["EXIT_MS"]
    rest = Anim("Turn Rest", 17).set(fold, "opacity", 0.0)
    fwd = Anim("Turn Forward", ms)
    fwd.tw(fold, "x", 0, ms, SW, 0, "inout")
    fwd.k(fold, "opacity", 0, 0.0, "out").k(fold, "opacity", 120, 1.0, "linear").k(fold, "opacity", ms - 80, 1.0, "linear").k(fold, "opacity", ms, 0.0)
    bwd = Anim("Turn Back", ms)
    bwd.tw(fold, "x", 0, ms, 0, SW, "inout")
    bwd.k(fold, "opacity", 0, 0.0, "out").k(fold, "opacity", 120, 1.0, "linear").k(fold, "opacity", ms - 80, 1.0, "linear").k(fold, "opacity", ms, 0.0)
    s_r = L4.state(rest, 100, 0)
    s_f = L4.state(fwd, 360, -120)
    s_b = L4.state(bwd, 360, 120)
    L4.start(s_r)
    trans(L4.any, s_f, ctrig("_turnFwd"))
    trans(L4.any, s_b, ctrig("_turnBack"))
    trans(s_f, s_r, exit_pct=100)
    trans(s_b, s_r, exit_pct=100)
    layers.append((L4, [rest, fwd, bwd]))
    root.children = [fold, ribbon, moon]
    return root, layers


# ======================================================================= share card artboard
def share_card_artboard(ctx):
    V = ctx["V"]
    st = N("LayoutComponentStyle", name="ShareCard Style").ensure()
    sm = N("StateMachine", name="ShareCard").ensure()
    ab = N("Artboard", isComponent=True, width=340, height=460, defaultStateMachineId=sm.id, styleId=st.id,
           viewModelId=V.el.id, viewModelInstanceId=V.inst.id, clip=True, name="ShareCard").ensure()
    card, cp = card_content(ctx, "Share Card")
    holder = node("Card", card, x=170, y=230)
    ab.add(sm, st, holder, shape("Backdrop", rect(340, 460, x=170, y=230), fill(PARCH)))
    layers = card_layers("Share Card", cp)
    anims = []
    for L, aa in layers:
        sm.add(L.build())
        anims += aa
    for a in anims:
        ab.add(a.build())
    return ab, layers, anims
