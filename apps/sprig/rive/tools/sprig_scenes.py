"""The ten Sprig scenes: layered vector art, typography and entrance choreography."""
from build_sprig import *  # noqa
from rml import _f  # noqa
import re


def hills(name, back, front, y0=690, y1=748, dark=True):
    b = poly(f"{name} back", f"M-30 {y0+20} C 70 {y0-30} 170 {y0+12} 250 {y0-10} C 320 {y0-26} 380 {y0-18} 420 {y0-6} "
                             f"L420 880 L-30 880 Z", back)
    f = poly(f"{name} front", f"M-30 {y1+20} C 80 {y1-14} 190 {y1+30} 290 {y1+2} C 345 {y1-12} 390 {y1-6} 420 {y1} "
                              f"L420 880 L-30 880 Z", front)
    return b, f


# ===================================================================== 1  Invitation
def scene1():
    sc = Scene(1, FOREST, dur=118)
    glow_id = ID()
    glow = shape("Glow", ellipse(600, 600), rad_grad([(0, col(LEAF, 0.30)), (0.55, col(LEAF, 0.08)), (1, col(LEAF, 0))],
                                                    0, 0, 300), x=195, y=610, id=glow_id)
    hb, hf = hills("Hill", FOREST_MID, "#12352A", 700, 760)
    back_leaves = []
    for i, (x, y, L, Wd, r, c1, c2) in enumerate([(-10, 880, 330, 170, 0.55, FOREST_SOFT, FOREST_MID),
                                                   (400, 870, 300, 160, -0.6, FOREST_SOFT, FOREST_MID),
                                                   (60, 900, 240, 120, 0.15, FOREST_MID, "#163D30")]):
        n, p = leaf(f"Back leaf {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, rib=CREAM, rib_a=0.08)
        back_leaves.append(n)
        sc.sway(p["node"], r, 0.025, 420, i * 90)
    bl_id = ID()
    back = node("Back foliage", *stack(*back_leaves), id=bl_id)
    sc.key(bl_id, "y", [(0, 60, "hold"), (0, 60, "soft"), (60, 0)])

    # --- jungle that grows out of the seed (hero)
    jungle = []
    specs = [  # x, y, L, W, rot, light, dark, kind, delay
        (180, 652, 200, 66, -0.22, LEAF_PALE, LEAF, "leaf", 4),
        (206, 650, 228, 70, 0.10, LEAF, LEAF_DARK, "leaf", 0),
        (172, 660, 150, 132, -0.92, LEAF_DARK, LEAF_DEEP, "heart", 10),
        (214, 664, 120, 72, 1.15, APRICOT, APRICOT_DARK, "leaf", 22),
        (176, 668, 120, 78, -1.35, FOREST_PALE, FOREST_SOFT, "leaf", 18),
        (196, 660, 150, 56, -0.5, LEAF, LEAF_DEEP, "leaf", 14),
        (204, 664, 132, 60, 0.62, LEAF_PALE, LEAF_DARK, "leaf", 8),
    ]
    for i, (x, y, L, Wd, r, c1, c2, kind, dl) in enumerate(specs):
        n, p = leaf(f"Jungle {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.4)
        jungle.append(n)
        sc.unfurl(p, 26 + dl, 58 + dl, rot=r, rot0=r * 0.2)
        sc.sway(p["node"], r, 0.03 + 0.01 * (i % 3), 300 + 30 * (i % 4), i * 40)
    # the bendable hero leaf (signature interaction) sits in its own bend wrapper
    bend_id = ID()
    hl, hp = leaf("Hero leaf", 0, 0, 176, 168, rot=0.0, light=LEAF, dark=LEAF_DARK, kind="heart", rib_a=0.45)
    sc.unfurl(hp, 30, 64, rot=0.0, rot0=-0.5)
    sc.sway(hp["node"], 0.0, 0.035, 330, 120)
    hero_bend = node("Hero bend", hl, x=226, y=660, rot=0.78, id=bend_id)
    sc.hero_bend = bend_id
    jungle.insert(3, hero_bend)

    # --- seed (motif): two paper shells hinged at the base
    seed_id, ls_id, rs_id = ID(), ID(), ID()
    shell_l = "M0 0 C-50 0 -66 -44 -64 -84 C-62 -126 -30 -154 0 -156 L-7 -122 L4 -92 L-5 -58 L3 -30 Z"
    shell_r = "M0 0 C50 0 66 -44 64 -84 C62 -126 30 -154 0 -156 L-7 -122 L4 -92 L-5 -58 L3 -30 Z"
    inner = shape("Seed inner", ellipse(104, 132), lin_grad([(0, col(CREAM_DARK)), (1, col("#B9A87A"))], 0, -60, 0, 60),
                  y=-74)
    stem_trim = ID()
    stem = line("Sprout", "M0 -24 C 8 -70 -10 -110 4 -168", LEAF, 6, trim_el=trim(0, 0, id=stem_trim))
    sc.key(stem_trim, "end", [(0, 0.0, "hold"), (16, 0.0, "outs"), (46, 1.0)])
    shells = node("Seed", *stack(
        inner, stem,
        node("Shell L", poly("Shell L face", shell_l, CREAM), line("Shell L rim", shell_l, CREAM_DARK, 1.6, 0.9),
             id=ls_id),
        node("Shell R", poly("Shell R face", shell_r, CREAM_SHADE), line("Shell R rim", shell_r, CREAM_DARK, 1.6, 0.9),
             id=rs_id),
    ), x=195, y=716, id=seed_id)
    sc.key(seed_id, "scaleY", [(0, 1.0, "hold"), (1, 1.0, "in"), (12, 0.88, "back"), (26, 1.0)])
    sc.key(seed_id, "scaleX", [(0, 1.0, "hold"), (1, 1.0, "in"), (12, 1.08, "back"), (26, 1.0)])
    sc.key(ls_id, "rotation", [(0, 0.0, "hold"), (12, 0.0, "back"), (38, -0.66)])
    sc.key(rs_id, "rotation", [(0, 0.0, "hold"), (14, 0.0, "back"), (40, 0.6)])
    sc.sway(ls_id, -0.66, 0.02, 360, 0)
    sc.sway(rs_id, 0.6, 0.02, 360, 180)
    seed_shadow = shadow("Seed shadow", 190, 30, 195, 722, 0.35, 12)
    sc.seed_id = seed_id

    # --- wordmark revealed through the motif (rises out of the jungle, letter by letter)
    wm_id = ID()
    wm_rid = ID()
    wm_mod = E("TextModifierGroup",
               E("TextModifierRange", E("CubicInterpolatorComponent", x1=0.3, y1=0.0, x2=0.2, y2=1.0, name="Ease"),
                 modifyFrom=0.0, modifyTo=1.0, falloffFrom=0.3, falloffTo=1.0, unitsValue=0, name="Sweep", id=wm_rid),
               modifyOpacity=True, modifyTranslation=True, modifyScale=True, invertOpacity=True, opacity=0.0, y=46.0,
               scaleX=0.6, scaleY=0.6, name="Rise", id=ID())
    wordmark = text("Wordmark", ["Sprig"], font="fr", size=96, color=CREAM, wght=620, soft=100, wonk=1, x=195, y=402,
                    ox=0.5, oy=0.5, id=wm_id, modifiers=[wm_mod])
    reveal_keys(sc.ef, wm_rid, 40, 80, "out")
    wm_leaf, wm_lp = leaf("Wordmark leaf", 286, 352, 34, 22, rot=0.7, light=LEAF, dark=LEAF_DARK, rib_a=0.5)
    sc.unfurl(wm_lp, 70, 92, rot=0.7)

    # --- copy
    name_id, sup_id, col_id = ID(), ID(), ID()
    rg, rid = word_reveal()
    copy = column("Intro copy", 24, 104, 342, [
        text("Name", [("Alex", P("userName"))], font="fr", size=24, color=APRICOT, wght=520, soft=80, align="center",
             lp=lp(), id=name_id, overflow="ellipsis"),
        text("Headline", [("Your 2026 on Sprig", P("introHeadline"))], font="fr", size=38, color=CREAM, wght=560,
             soft=60, lh=40, align="center", lp=lp(), modifiers=[rg]),
        text("Support", [("A year, uniquely yours.", P("introSupport"))], font="dm", size=16, color=CREAM, lh=22,
             align="center", lp=lp(), op=0.82, id=sup_id),
    ], gap=10, align="topCenter", id=col_id)
    sc.key(name_id, "opacity", [(0, 0.0, "hold"), (52, 0.0, "outs"), (72, 1.0)])
    reveal_keys(sc.ef, rid, 58, 96)
    sc.key(sup_id, "opacity", [(0, 0.0, "hold"), (86, 0.0, "outs"), (108, 0.82)])
    period_id = ID()
    period = text("Period", [("January 1–December 31, 2026", P("periodLabel"))], font="dm", size=13, color=CREAM,
                  wght=500, ls=1.2, x=24, y=742, w=342, align="center", op=0.7, id=period_id)
    sc.key(period_id, "opacity", [(0, 0.0, "hold"), (96, 0.0, "outs"), (116, 0.7)])

    sc.key(glow_id, "scaleX", [(0, 0.2, "hold"), (8, 0.2, "outs"), (70, 1.0)])
    sc.key(glow_id, "scaleY", [(0, 0.2, "hold"), (8, 0.2, "outs"), (70, 1.0)])
    sc.idle.key(glow_id, "scaleX", [(0, 1.0, "sine"), (180, 1.05, "sine"), (360, 1.0)])
    sc.idle.key(glow_id, "scaleY", [(0, 1.0, "sine"), (180, 1.05, "sine"), (360, 1.0)])
    sc.settle += [(bl_id, "y", 24.0), (col_id, "y", 8.0)]

    # --- signature interaction: hold the hero to bend a leaf toward the pointer
    hit_id, handle_id = ID(), ID()
    sc.leaf_hit = hit_id
    sc.leaf_handle = handle_id
    hit = shape("Leaf hold region", ellipse(150, 170), fill(col("#000000", 0.0)), x=268, y=572, id=hit_id, opaque=True)
    handle = node("Leaf handle", x=268, y=572, id=handle_id)
    sc.hits.append((hit_id, 268))

    content = stack(bg_rect(FOREST), glow, back, hb, hf, seed_shadow, jungle, shells, wordmark, wm_leaf, copy, period,
                    handle, hit)
    root = build_scene_root(sc, content, clip=False)
    sc.ef.key(sc.root, "opacity", [(0, 1.0, "hold")])
    return sc, root


# ===================================================================== 2  Care moments
VINE2 = "M98 732 C 150 690 252 702 286 626 C 318 548 252 506 300 444 C 334 400 362 382 352 300"


def scene2():
    sc = Scene(2, FOREST)
    glow = shape("Glow", ellipse(520, 420), rad_grad([(0, col(CREAM, 0.07)), (1, col(CREAM, 0))], 0, 0, 260), x=195,
                 y=190)
    hb, hf = hills("Hill", FOREST_MID, "#12352A", 730, 786)
    back = []
    for i, (x, y, L, Wd, r) in enumerate([(30, 890, 360, 190, 0.35), (130, 900, 260, 140, -0.25),
                                          (-20, 760, 220, 110, 1.0)]):
        n, p = leaf(f"Shadow leaf {i}", x, y, L, Wd, rot=r, light=FOREST_SOFT, dark=FOREST_MID, rib_a=0.07)
        back.append(n)
        sc.sway(p["node"], r, 0.02, 400, i * 120)
    back_id = ID()
    backn = node("Back foliage", *stack(*back), id=back_id)
    sc.key(back_id, "x", [(0, -40, "hold"), (6, -40, "soft"), (70, 0)])
    sc.settle.append((back_id, "x", -14.0))

    # carried motif: the opened seed from scene 1 settles at the vine's root
    shell_l = "M0 0 C-50 0 -66 -44 -64 -84 C-62 -126 -30 -154 0 -156 L-7 -122 L4 -92 L-5 -58 L3 -30 Z"
    shell_r = "M0 0 C50 0 66 -44 64 -84 C62 -126 30 -154 0 -156 L-7 -122 L4 -92 L-5 -58 L3 -30 Z"
    carry_id = ID()
    seed = node("Carried seed",
                node("Shell L", poly("Face", shell_l, CREAM), rot=-0.66),
                node("Shell R", poly("Face", shell_r, CREAM_SHADE), rot=0.6),
                shape("Inner", ellipse(104, 132), fill(col(CREAM_DARK)), y=-74),
                x=92, y=744, sx=0.5, sy=0.5, id=carry_id)
    sc.key(carry_id, "x", [(0, 195, "hold"), (2, 195, "fold"), (42, 92)])
    sc.key(carry_id, "y", [(0, 716, "hold"), (2, 716, "fold"), (42, 744)])
    sc.key(carry_id, "scaleX", [(0, 1.0, "hold"), (2, 1.0, "fold"), (42, 0.5)])
    sc.key(carry_id, "scaleY", [(0, 1.0, "hold"), (2, 1.0, "fold"), (42, 0.5)])

    vtrim = ID()
    vine = line("Vine", VINE2, LEAF, 7, trim_el=trim(0, 0, id=vtrim))
    vtrim2 = ID()
    vine_hi = line("Vine light", VINE2, LEAF_PALE, 2, 0.7, x=-1.5, trim_el=trim(0, 0, id=vtrim2))
    for t in (vtrim, vtrim2):
        sc.key(t, "end", [(0, 0.0, "hold"), (12, 0.0, "soft"), (84, 1.0)])
    leaves = []
    drops = []
    fr = [0.12, 0.22, 0.33, 0.44, 0.55, 0.66, 0.77, 0.88, 0.97]
    for i, f in enumerate(fr):
        (px, py), ang = point_at(VINE2, f)
        side = 1 if i % 2 else -1
        L = 44 + 18 * ((i * 7) % 3)
        rot = ang + math.pi / 2 + side * 0.95
        c1, c2 = [(LEAF, LEAF_DARK), (LEAF_PALE, LEAF), (LEAF_DARK, LEAF_DEEP)][i % 3]
        n, p = leaf(f"Vine leaf {i}", px, py, L, L * 0.62, rot=rot, light=c1, dark=c2, rib_a=0.4)
        leaves.append(n)
        t0 = 12 + f * 72
        sc.unfurl(p, t0 + 4, t0 + 28, rot=rot, rot0=rot - side * 0.8)
        sc.sway(p["node"], rot, 0.05, 280 + 20 * (i % 3), i * 31)
        if i % 2 == 0:  # droplets become leaves
            d, did = droplet(f"Droplet {i}", px, py, 1.0)
            drops.append(d)
            sc.key(did, "y", [(0, py - 150, "hold"), (t0 - 22, py - 150, "in"), (t0 + 2, py)])
            sc.key(did, "x", [(0, px + 18, "hold"), (t0 - 22, px + 18, "sine"), (t0 + 2, px)])
            sc.key(did, "opacity", [(0, 0.0, "hold"), (t0 - 22, 0.0, "lin"), (t0 - 14, 1.0, "hold"), (t0 + 2, 1.0, "in"),
                                    (t0 + 10, 0.0)])
            sc.key(did, "scaleX", [(0, 1.0, "hold"), (t0 - 2, 1.0, "in"), (t0 + 2, 1.3, "in"), (t0 + 10, 0.2)])
            sc.key(did, "scaleY", [(0, 1.0, "hold"), (t0 - 2, 1.0, "in"), (t0 + 2, 0.75, "in"), (t0 + 10, 0.2)])
    # idle: one droplet slides down the vine on a loop
    loop_drop, ldid = droplet("Idle droplet", 352, 300, 0.8, op=0.0)
    pts = [point_at(VINE2, 1 - f)[0] for f in (0.0, 0.15, 0.3, 0.45, 0.6)]
    sc.idle.key(ldid, "x", [(0, pts[0][0], "hold")] + [(60 + i * 30, p[0], "sine") for i, p in enumerate(pts)] + [(360, pts[-1][0])])
    sc.idle.key(ldid, "y", [(0, pts[0][1], "hold")] + [(60 + i * 30, p[1], "sine") for i, p in enumerate(pts)] + [(360, pts[-1][1])])
    sc.idle.key(ldid, "opacity", [(0, 0.0, "hold"), (50, 0.0, "lin"), (64, 0.9, "hold"), (170, 0.9, "lin"), (186, 0.0, "hold"), (360, 0.0)])

    hero, unit, copy = metric_text(sc, dict(x=24, y=118, w=342, size=124, align="center"), (32, 300), 300, "left",
                                   unit_kw=dict(x=24, y=250, w=342, align="center"))
    content = stack(bg_rect(FOREST), glow, backn, hb, hf, vine, vine_hi, leaves, drops, loop_drop, seed, hero, unit, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 3  Plants nurtured
def plant_tuft(i, s=1.0):
    kids = []
    kinds = [
        [(-6, 0, 40, 22, -0.5), (6, 0, 46, 22, 0.4), (0, 0, 54, 20, 0.0)],
        [(0, 0, 44, 44, -0.3, "heart"), (0, 0, 40, 40, 0.5, "heart")],
        [(-4, 0, 60, 16, -0.15), (4, 0, 56, 16, 0.2), (0, 0, 66, 14, 0.02), (-2, 0, 40, 16, -0.6)],
        [(0, 0, 30, 30, -0.9), (0, 0, 34, 28, 0.9), (0, 0, 38, 28, 0.0)],
    ][i % 4]
    cols = [(LEAF, LEAF_DARK), (LEAF_PALE, LEAF), (LEAF_DARK, LEAF_DEEP), (FOREST_PALE, FOREST_SOFT)]
    for j, spec in enumerate(kinds):
        x, y, L, Wd, r = spec[:5]
        kind = spec[5] if len(spec) > 5 else "leaf"
        c1, c2 = cols[(i + j) % 4]
        n, _ = leaf(f"Tuft {i}.{j}", x * s, y, L * s, Wd * s, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.35)
        kids.append(n)
    return node(f"Plant {i}", *kids)


def scene3():
    sc = Scene(3, FOREST_DEEP)
    layers = []
    specs = [  # y0, colour, shade
        (560, CREAM_DARK, "#C4B68A"),
        (628, CREAM_SHADE, CREAM_DARK),
        (708, CREAM, CREAM_SHADE),
    ]
    for i, (y0, c, s) in enumerate(specs):
        lid = ID()
        d = (f"M-30 {y0+30} C 40 {y0-24} 120 {y0+18} 196 {y0-6} C 270 {y0-28} 340 {y0+10} 420 {y0-14} L420 900 L-30 900 Z"
             if i % 2 == 0 else
             f"M-30 {y0-10} C 60 {y0+20} 140 {y0-30} 220 {y0+4} C 300 {y0+30} 360 {y0-20} 420 {y0+6} L420 900 L-30 900 Z")
        lyr = node(f"Paper layer {i}", *stack(
                   poly("Shadow", d, "#05130E", a=0.35, y=-8, feather=14),
                   poly("Paper", d, c),
                   line("Edge light", d.split(" L420")[0], "#FFFFFF", 1.5, 0.5)),
                   id=lid)
        layers.append(lyr)
        sc.key(lid, "y", [(0, 160 + 60 * i, "hold"), (2 + i * 6, 160 + 60 * i, "out"), (40 + i * 6, 0)])
        sc.settle.append((lid, "y", 10.0 + 6 * i))
    pots = []
    spots = [(70, 556, 0.62), (150, 548, 0.6), (240, 552, 0.62), (322, 545, 0.6),
             (104, 628, 0.8), (205, 622, 0.82), (300, 630, 0.78),
             (138, 712, 1.0), (262, 706, 1.02)]
    body = [(APRICOT, APRICOT_DARK, APRICOT_PALE), (LEAF, LEAF_DARK, LEAF_PALE), (CREAM, CREAM_DARK, "#FFFFFF"),
            (FOREST_PALE, FOREST_SOFT, LEAF_PALE)]
    for i, (x, y, s) in enumerate(spots):
        pid = ID()
        b, sh, rim = body[i % 4]
        pt = pot(f"Pot {i}", x, y, 56, 46, b, sh, rim, plant=plant_tuft(i), s=s, id=pid)
        pots.append(pt)
        t0 = 18 + i * 5
        sc.key(pid, "x", [(0, 195, "hold"), (t0, 195, "back"), (t0 + 30, x)])
        sc.key(pid, "y", [(0, 880, "hold"), (t0, 880, "back"), (t0 + 30, y)])
        sc.key(pid, "rotation", [(0, (x - 195) / 200, "hold"), (t0, (x - 195) / 200, "back"), (t0 + 34, 0.0)])
        sc.key(pid, "scaleX", [(0, s * 0.4, "hold"), (t0, s * 0.4, "back"), (t0 + 30, s)])
        sc.key(pid, "scaleY", [(0, s * 0.4, "hold"), (t0, s * 0.4, "back"), (t0 + 30, s)])
        sc.sway(pid, 0.0, 0.015, 300 + 40 * (i % 3), i * 33)
    # order pots back->front by y
    pots_sorted = [p for _, p in sorted(zip([s[1] for s in spots], pots), key=lambda t: t[0])]
    hero, unit, copy = metric_text(sc, dict(x=28, y=102, w=334, size=172, align="left"), (30, 340), 330, "left",
                                   unit_kw=dict(x=34, y=290, w=330, align="left"))
    # paper landscape interleaves with pots (back layer, back pots, mid layer, mid pots, front layer, front pots)
    content = stack(bg_rect(FOREST_DEEP),
                    shape("Glow", ellipse(500, 360), rad_grad([(0, col(LEAF, 0.12)), (1, col(LEAF, 0))], 0, 0, 250),
                          x=300, y=520),
                    layers[0], pots_sorted[0:4], layers[1], pots_sorted[4:7], layers[2], pots_sorted[7:],
                    hero, unit, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 4  New leaves
def scene4():
    sc = Scene(4, CREAM, light=True)
    sun_id = ID()
    sun = shape("Sun", ellipse(300, 300), rad_grad([(0, col(APRICOT_PALE, 0.95)), (0.7, col(APRICOT_PALE, 0.5)),
                                                   (1, col(APRICOT_PALE, 0))], 0, 0, 150), x=195, y=520, id=sun_id)
    sc.pop(sun_id, 6, 50, 0.3, 1.0, "outs")
    canopy = []
    for i, (x, y, L, Wd, r, c1, c2, kind) in enumerate([
        (150, 760, 170, 70, -0.55, FOREST_SOFT, FOREST_MID, "leaf"),
        (240, 760, 170, 70, 0.55, FOREST_SOFT, FOREST_MID, "leaf"),
        (175, 770, 150, 120, -0.25, LEAF_DARK, LEAF_DEEP, "heart"),
        (215, 770, 140, 110, 0.3, LEAF, LEAF_DARK, "heart"),
        (195, 776, 150, 44, 0.02, LEAF_PALE, LEAF, "leaf"),
        (160, 774, 110, 60, -1.0, APRICOT, APRICOT_DARK, "leaf"),
        (232, 774, 120, 56, 1.05, FOREST_PALE, FOREST_SOFT, "leaf"),
    ]):
        n, p = leaf(f"Canopy {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.4)
        canopy.append(n)
        sc.unfurl(p, 24 + i * 5, 54 + i * 5, rot=r)
        sc.sway(p["node"], r, 0.03, 320 + 25 * i, i * 45)
    outer_l = "M0 0 C -130 -30 -222 -200 -196 -390 C -176 -530 -76 -608 0 -640 C -38 -470 -42 -230 0 0 Z"
    inner_l = "M0 0 C -40 -230 -38 -470 0 -640 C -34 -560 -62 -470 -68 -330 C -74 -190 -40 -60 0 0 Z"
    veins_l = ["M-10 -120 C -60 -140 -110 -170 -150 -210", "M-16 -260 C -70 -290 -120 -320 -160 -370",
               "M-20 -400 C -60 -430 -100 -470 -128 -510"]

    def mirror(d):
        return re.sub(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)",
                      lambda m: f"{-float(m.group(1)):g} {m.group(2)}", d)
    halves = {}
    for side, sgn in (("L", 1), ("R", -1)):
        hid = ID()
        o = outer_l if side == "L" else mirror(outer_l)
        inn = inner_l if side == "L" else mirror(inner_l)
        veins = [line(f"Vein {j}", v if side == "L" else mirror(v), CREAM, 2.2, 0.3) for j, v in enumerate(veins_l)]
        face = LEAF_DARK if side == "L" else LEAF_DEEP
        halves[side] = node(f"Giant leaf {side}", *stack(
            poly("Drop shadow", o, "#3A3A1A", a=0.25, x=sgn * 10, y=8, feather=18),
            poly("Outer", o, face), *veins,
            poly("Inner fold", inn, CREAM_SHADE),
            line("Fold crease", "M0 0 C -38 -230 -36 -470 0 -640" if side == "L" else "M0 0 C 38 -230 36 -470 0 -640",
                 "#FFFFFF", 1.6, 0.6)), x=195, y=800, sx=0.92, sy=0.86, id=hid)
        closed, opened = (0.34, -0.44) if side == "L" else (-0.34, 0.44)
        sc.key(hid, "rotation", [(0, closed, "hold"), (1, closed, "antic"), (12, closed + 0.04 * sgn, "back"),
                                 (52, opened)])
        sc.sway(hid, opened, 0.012, 360, 0 if side == "L" else 180)
    hero, unit, copy = metric_text(sc, dict(x=24, y=410, w=342, size=118, align="center", color=FOREST), (32, 112),
                                   326, "center", unit_kw=dict(x=24, y=532, w=342, align="center"))
    plate_id = ID()
    plate = shape("Number plate", ellipse(250, 210), fill(col(CREAM, 0.55), feather=26), x=195, y=486, id=plate_id)
    sc.pop(plate_id, 20, 50, 0.4, 1.0, "outs")
    flutter = []
    for i, (x, y, r) in enumerate([(70, 790, 0.8), (320, 800, -0.6), (110, 818, 1.6), (280, 822, 2.2)]):
        n, p = leaf(f"Fallen leaf {i}", x, y, 26, 14, rot=r, light=LEAF_DARK, dark=LEAF_DEEP, rib=None)
        flutter.append(n)
        sc.key(p["node"], "y", [(0, y - 300, "hold"), (30 + i * 8, y - 300, "outs"), (84 + i * 8, y)])
        sc.key(p["node"], "rotation", [(0, r - 3, "hold"), (30 + i * 8, r - 3, "outs"), (84 + i * 8, r)])
    content = stack(bg_rect(CREAM), sun, canopy, plate, hero, unit, halves["L"], halves["R"], flutter, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    sc.giant = (halves["L"].id, halves["R"].id)
    return sc, root


# ===================================================================== 5  Cuttings rooted
def scene5():
    sc = Scene(5, FOREST)
    JX, JY = 214, 676   # jar centre
    jar_id = ID()
    water_id = ID()
    roots = []
    root_paths = [
        "M-40 -96 C -44 -40 -60 0 -54 60 M-48 -20 C -70 0 -84 10 -96 30 M-52 30 C -40 50 -30 70 -36 96",
        "M0 -100 C 6 -40 -6 10 4 80 M2 -10 C 24 10 38 20 50 46 M-2 40 C -22 60 -28 80 -26 104",
        "M40 -96 C 46 -50 62 -10 58 50 M50 -30 C 72 -16 84 -6 92 12 M56 20 C 74 44 78 70 70 96",
    ]
    for i, d in enumerate(root_paths):
        tid = ID()
        roots.append(line(f"Roots {i}", d, CREAM_SHADE, 2.0, 0.85, trim_el=trim(0, 0, id=tid)))
        sc.key(tid, "end", [(0, 0.0, "hold"), (34 + i * 6, 0.0, "soft"), (100 + i * 4, 1.0)])
    stems = []
    tops = []
    for i, (sx, lean) in enumerate([(-40, -0.25), (0, 0.05), (40, 0.3)]):
        stems.append(line(f"Stem {i}", f"M{sx} -96 C {sx + lean*30} -140 {sx + lean*60} -170 {sx + lean*80} -196",
                          LEAF_DARK, 4))
        tx, ty = sx + lean * 80, -196
        for j, (L, r) in enumerate([(54, lean - 0.7), (60, lean + 0.65), (44, lean - 0.1)]):
            n, p = leaf(f"Cutting {i}.{j}", tx, ty + 6 * j, L, L * 0.6, rot=r,
                        light=[LEAF, LEAF_PALE, LEAF_DARK][(i + j) % 3], dark=[LEAF_DARK, LEAF, LEAF_DEEP][(i + j) % 3])
            tops.append(n)
            sc.unfurl(p, 30 + i * 6 + j * 4, 58 + i * 6 + j * 4, rot=r)
            sc.sway(p["node"], r, 0.04, 300, (i * 3 + j) * 37)
    bubbles = []
    for i in range(6):
        bid = ID()
        bx = -60 + i * 24
        bubbles.append(shape(f"Bubble {i}", ellipse(6 + i % 3 * 2, 6 + i % 3 * 2), stroke(col(CREAM, 0.6), 1.2),
                             x=bx, y=100, op=0.0, id=bid))
        p0 = i * 40
        sc.idle.key(bid, "y", [(0, 110, "hold"), (p0, 110, "lin"), (p0 + 120, -20, "hold"), (360, -20)])
        sc.idle.key(bid, "opacity", [(0, 0.0, "hold"), (p0, 0.0, "lin"), (p0 + 20, 0.8, "lin"), (p0 + 110, 0.6, "lin"),
                                     (p0 + 120, 0.0, "hold"), (360, 0.0)])
    jar = node("Jar", *stack(
        shadow("Jar shadow", 220, 26, 0, 136, 0.35, 12),
        shape("Water", rect(196, 168, 26, oy=0.0), fill(col(LEAF, 0.22)), y=-36, id=water_id),
        shape("Water line", rect(186, 3, 2), fill(col(LEAF_PALE, 0.7)), y=-36),
        roots, bubbles, stems,
        shape("Glass", rect(204, 268, 34), fill(col(CREAM, 0.08)), stroke(col(CREAM, 0.55), 2.2), y=-2),
        shape("Neck", rect(138, 26, 8), fill(col(CREAM, 0.06)), stroke(col(CREAM, 0.5), 2), y=-146),
        shape("Highlight", rect(14, 180, 7), fill(col("#FFFFFF", 0.22)), x=-78, y=-10),
        shape("Highlight 2", rect(6, 60, 3), fill(col("#FFFFFF", 0.18)), x=-60, y=-80),
        tops,
    ), x=JX, y=JY, sx=0.86, sy=0.86, id=jar_id)
    sc.key(jar_id, "y", [(0, JY + 260, "hold"), (4, JY + 260, "out"), (40, JY)])
    sc.key(jar_id, "rotation", [(0, 0.12, "hold"), (4, 0.12, "back"), (46, 0.0)])
    sc.key(water_id, "scaleY", [(0, 0.0, "hold"), (14, 0.0, "outs"), (50, 1.0)])
    sc.settle.append((jar_id, "y", 18.0))
    # carried object: one leaf of the giant folded leaf (scene 4) swoops in and becomes a cutting leaf
    cl, cp = leaf("Carried leaf", 214, 400, 60, 38, rot=-0.2, light=LEAF_DARK, dark=LEAF_DEEP, rib_a=0.4)
    sc.key(cp["node"], "x", [(0, 120, "hold"), (2, 120, "fold"), (46, JX + 4)])
    sc.key(cp["node"], "y", [(0, 640, "hold"), (2, 640, "fold"), (46, JY - 176)])
    sc.key(cp["node"], "scaleX", [(0, 6.0, "hold"), (2, 6.0, "fold"), (46, 0.86)])
    sc.key(cp["node"], "scaleY", [(0, 9.0, "hold"), (2, 9.0, "fold"), (46, 0.86)])
    sc.key(cp["node"], "rotation", [(0, -0.3, "hold"), (2, -0.3, "fold"), (46, 0.05)])
    sc.key(cp["node"], "opacity", [(0, 1.0, "hold"), (46, 1.0, "lin"), (60, 0.0)])
    hero, unit, copy = metric_text(sc, dict(x=24, y=104, w=338, size=124, align="right"), (30, 290), 330, "left",
                                   unit_kw=dict(x=30, y=232, w=332, align="right"))
    content = stack(bg_rect(FOREST),
                    shape("Glow", ellipse(460, 460), rad_grad([(0, col(LEAF, 0.16)), (1, col(LEAF, 0))], 0, 0, 230),
                          x=JX, y=JY),
                    jar, hero, unit, copy, cl)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 6  Day care streak
VINE6 = ("M28 512 C 140 500 260 524 330 512 C 386 502 386 602 330 594 C 250 582 140 606 60 594 "
         "C 4 586 4 686 60 676 C 150 664 270 688 364 672")


def scene6():
    sc = Scene(6, LEAF, light=True)
    k = 6
    paper_id = ID()
    paper = node("Calendar paper", *stack(
                 shape("Paper shadow", rect(352, 248, 30), fill(col("#2E4A1C", 0.35), feather=16), y=10),
                 shape("Paper", rect(352, 248, 30), fill(col(CREAM, 0.94))),
                 shape("Paper fold", rect(352, 124, 30, oy=0.0), fill(col(CREAM_SHADE, 0.8)), y=0)),
                 x=195, y=594, id=paper_id)
    sc.key(paper_id, "scaleY", [(0, 0.0, "hold"), (4, 0.0, "back"), (34, 1.0)])
    sc.key(paper_id, "rotation", [(0, -0.08, "hold"), (4, -0.08, "back"), (34, 0.0)])
    trim_id = ID()
    src = P(METRIC[k])
    vine_conv = count_chain(k, [CV.add("vine6", formula("Streak to trim", [tF("min"), tV(1), tSep(), tIn(), tOp("/"),
                                                                           tV(22), tOp("+"), tV(0.02), tC()]))], "trim")
    vine = line("Streak vine", VINE6, LEAF_DEEP, 5, trim_el=trim(0, 0.02, id=trim_id, bind=bind(src, 115, vine_conv)))
    knots = []
    for i in range(21):
        (px, py), _ = point_at(VINE6, (i + 1) / 22.0)
        lit_conv = count_chain(k, [f_unit_clamp(i)], f"knot{i}")
        kid = ID()
        knots.append(node(f"Knot {i + 1}",
                          shape("Lit", ellipse(20, 20), fill(col(APRICOT)), stroke(col(APRICOT_DARK), 1.5),
                                E("DataBindContext", sourcePathIds=src, propertyKey=18, converterId=lit_conv)),
                          shape("Ring", ellipse(20, 20), stroke(col(FOREST, 0.35), 1.6), fill(col(CREAM))),
                          x=px, y=py, id=kid))
        sc.pop(kid, 10 + i * 1.5, 26 + i * 1.5, 0.0, 1.0, "back")
    sprigs = []
    for i, f in enumerate([0.1, 0.3, 0.5, 0.7, 0.9]):
        (px, py), ang = point_at(VINE6, f)
        n, p = leaf(f"Streak leaf {i}", px, py, 30, 18, rot=ang - 1.2, light=LEAF, dark=LEAF_DEEP, rib_a=0.4)
        sprigs.append(n)
        sc.unfurl(p, 40 + i * 9, 62 + i * 9, rot=ang - 1.2)
        sc.sway(p["node"], ang - 1.2, 0.06, 240, i * 40)
    hero, unit, copy = metric_text(sc, dict(x=24, y=104, w=342, size=124, align="center", color=FOREST), (32, 274),
                                   326, "center", unit_kw=dict(x=24, y=236, w=342, align="center"))
    deco = []
    for i, (x, y, L, r) in enumerate([(-6, 860, 230, 0.5), (396, 870, 210, -0.55)]):
        n, p = leaf(f"Corner leaf {i}", x, y, L, L * 0.5, rot=r, light=LEAF_DARK, dark=LEAF_DEEP, rib_a=0.25)
        deco.append(n)
        sc.sway(p["node"], r, 0.03, 380, i * 150)
        sc.key(p["node"], "y", [(0, y + 120, "hold"), (6, y + 120, "out"), (50, y)])
    content = stack(bg_rect(LEAF),
                    shape("Glow", ellipse(500, 380), rad_grad([(0, col(LEAF_PALE, 0.8)), (1, col(LEAF_PALE, 0))],
                                                              0, 0, 250), x=195, y=200),
                    deco, paper, vine, knots, sprigs, hero, unit, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 7  Plants shared
HAND_D = ("M-260 -24 L-20 -26 C 0 -27 14 -36 30 -48 C 42 -57 54 -50 50 -40 C 46 -31 38 -26 46 -22 "
          "L 112 -20 C 126 -19 126 -6 112 -5 L 64 -2 C 86 0 110 2 118 6 C 130 12 124 24 110 22 "
          "L 70 18 C 84 22 96 26 98 32 C 100 40 88 42 80 38 L 40 26 C 20 28 0 26 -20 24 L -260 24 Z")
HAND_SHADE_D = ("M-260 4 L-20 6 C 4 8 26 6 46 4 L 118 6 C 130 12 124 24 110 22 L 70 18 C 84 22 96 26 98 32 "
                "C 100 40 88 42 80 38 L 40 26 C 20 28 0 26 -20 24 L -260 24 Z")


def hand(name, sgn, colours, id=None):
    """Flat folded-paper hand, palm up, reaching from the screen edge (mirrored with sgn = -1)."""
    c1, c2, c3 = colours
    return node(name, node("Paper hand", *stack(
        poly("Hand shadow", HAND_D, "#3A3420", a=0.18, y=10, feather=10),
        poly("Hand", HAND_D, c1),
        poly("Hand shade", HAND_SHADE_D, c2),
        shape("Cuff", rect(26, 56, 6), fill(col(c3)), x=-70),
        line("Crease", "M 46 -20 C 40 -10 44 -4 56 -2", c2, 1.6, 0.8),
    ), sx=float(sgn)), id=id or ID())


def scene7():
    sc = Scene(7, CREAM, light=True)
    win_id = ID()
    arch = "M-70 0 L-70 -150 C -70 -200 -36 -230 0 -230 C 36 -230 70 -200 70 -150 L70 0 Z"
    window = node("Windowsill", *stack(
        poly("Window glow", arch, APRICOT_PALE, a=0.9),
        shape("Sun", ellipse(70, 70), fill(col(APRICOT)), x=24, y=-150),
        line("Mullion V", "M0 -228 L0 0", CREAM, 5),
        line("Mullion H", "M-70 -120 L70 -120", CREAM, 5),
        line("Frame", arch, CREAM_DARK, 8),
        shape("Sill", rect(180, 16, 4), fill(col(CREAM_DARK)), y=6),
        shape("Sill shadow", rect(180, 10, 4), fill(col("#000000", 0.08), feather=8), y=20),
    ), x=296, y=596, id=win_id)
    sc.key(win_id, "opacity", [(0, 0.0, "hold"), (8, 0.0, "outs"), (36, 1.0)])
    sc.key(win_id, "y", [(0, 640, "hold"), (8, 640, "outs"), (40, 596)])
    lh_id, rh_id = ID(), ID()
    lhand = hand("Giving hand", 1, (APRICOT, APRICOT_DARK, CREAM_SHADE), lh_id)
    rhand = hand("Receiving hand", -1, (LEAF, LEAF_DARK, CREAM_SHADE), rh_id)
    lh_x, lh_y, rh_x, rh_y = 60, 690, 330, 650
    sc.key(lh_id, "x", [(0, -180, "hold"), (2, -180, "out"), (34, lh_x)])
    sc.key(lh_id, "y", [(0, lh_y, "hold")])
    sc.key(rh_id, "x", [(0, 580, "hold"), (12, 580, "out"), (44, rh_x)])
    sc.key(rh_id, "y", [(0, rh_y, "hold")])
    sc.key(lh_id, "rotation", [(0, 0.0, "hold"), (52, 0.0, "io"), (64, -0.12, "back"), (84, 0.0)])
    sc.key(rh_id, "rotation", [(0, 0.0, "hold"), (78, 0.0, "back"), (90, 0.1, "io"), (104, 0.0)])
    sc.sway(lh_id, 0.0, 0.02, 360, 0)
    sc.sway(rh_id, 0.0, 0.02, 360, 180)
    cut_id = ID()
    cutting = pot("Shared cutting", 0, 0, 40, 32, APRICOT_DARK, "#C9784A", APRICOT_PALE, plant=node("Cutting plant",
                  *[leaf(f"Cut leaf {j}", 0, 0, L, L * 0.6, rot=r, light=LEAF, dark=LEAF_DARK)[0]
                    for j, (L, r) in enumerate([(40, -0.5), (46, 0.45), (52, 0.0)])]), id=cut_id)
    # arc: giving palm -> over -> receiving palm (synchronised with the count)
    p0 = (lh_x + 70, lh_y - 44)
    p2 = (rh_x - 70, rh_y - 44)
    arc = [(0, p0), (54, p0), (66, ((p0[0] + p2[0]) / 2 - 20, p0[1] - 90)), (80, (p2[0] - 6, p2[1] - 50)), (90, p2)]
    sc.key(cut_id, "x", [(0, p0[0] - 272, "hold"), (2, p0[0] - 272, "out"), (34, p0[0], "hold")] +
           [(f, p[0], "sine") for f, p in arc[1:]])
    sc.key(cut_id, "y", [(0, p0[1], "hold"), (54, p0[1], "out")] + [(f, p[1], "sine" if f < 80 else "back") for f, p in arc[2:]])
    sc.key(cut_id, "rotation", [(0, 0.0, "hold"), (54, 0.0, "io"), (68, 0.25, "io"), (90, 0.0)])
    trail_trim = ID()
    trail = line("Green trail", f"M{p0[0]} {p0[1]-10} C {p0[0]+30} {p0[1]-110} {p2[0]-40} {p2[1]-120} {p2[0]} {p2[1]-30}",
                 LEAF_DARK, 2.5, 0.6, trim_el=trim(0, 0, id=trail_trim))
    sc.key(trail_trim, "end", [(0, 0.0, "hold"), (56, 0.0, "io"), (88, 1.0)])
    sc.key(trail_trim, "start", [(0, 0.0, "hold"), (76, 0.0, "io"), (104, 1.0)])
    sparks = []
    for i, (x, y) in enumerate([(212, 520), (250, 540), (178, 548)]):
        sid = ID()
        sparks.append(shape(f"Spark {i}", E("Star", width=14.0, height=14.0, points=4, innerRadius=0.35, name="Star"),
                            fill(col(APRICOT)), x=x, y=y, sx=0.0, sy=0.0, id=sid))
        sc.key(sid, "scaleX", [(0, 0.0, "hold"), (86 + i * 4, 0.0, "back"), (98 + i * 4, 1.0)])
        sc.key(sid, "scaleY", [(0, 0.0, "hold"), (86 + i * 4, 0.0, "back"), (98 + i * 4, 1.0)])
        sc.idle.key(sid, "rotation", [(0, 0.0, "lin"), (360, 6.2831855)])
    hero, unit, copy = metric_text(sc, dict(x=30, y=100, w=330, size=124, align="left", color=FOREST), (30, 290), 330,
                                   "left", unit_kw=dict(x=34, y=232, w=330, align="left"))
    content = stack(bg_rect(CREAM),
                    shape("Floor", rect(W + 40, 160), fill(col(CREAM_SHADE)), x=195, y=800),
                    window, trail, rhand, lhand, cutting, sparks, hero, unit, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 8  Active months
def scene8():
    sc = Scene(8, FOREST)
    k = 8
    CX, CY, R = 195, 596, 128
    src = P(METRIC[k])
    ring_trim = ID()
    arc_conv = count_chain(k, [f_div_clamp(12)], "arc")
    ring = node("Year ring",
                shape("Track", ellipse(2 * R, 2 * R), stroke(col(CREAM, 0.14), 12)),
                shape("Active arc", ellipse(2 * R, 2 * R),
                      stroke(col(APRICOT), 12, cap="round", trim=trim(0, 0, id=ring_trim, bind=bind(src, 115, arc_conv))),
                      rot=-math.pi / 2),
                x=CX, y=CY)
    ticks = []
    for i in range(12):
        a = -math.pi / 2 + (i + 0.5) * 2 * math.pi / 12
        tx, ty = CX + (R + 26) * math.cos(a), CY + (R + 26) * math.sin(a)
        lit = count_chain(k, [f_unit_clamp(i)], f"month{i}")
        ticks.append(node(f"Month {i + 1}",
                          shape("Lit", ellipse(9, 9), fill(col(APRICOT)), bind(src, 18, lit)),
                          shape("Dot", ellipse(9, 9), fill(col(CREAM, 0.22))),
                          x=tx, y=ty))
    orbit_id = ID()
    seasons = []
    season_specs = [
        ("Spring", LEAF, LEAF_DARK, "leaf"), ("Summer", APRICOT, APRICOT_DARK, "sun"),
        ("Autumn", APRICOT_DARK, "#B86A3E", "leaf2"), ("Winter", CREAM, CREAM_DARK, "snow")]
    for i, (nm, c1, c2, icon) in enumerate(season_specs):
        a = -math.pi / 2 + i * math.pi / 2
        sx_, sy_ = R * math.cos(a), R * math.sin(a)
        if icon == "sun":
            ic = [shape("Rays", E("Star", width=34.0, height=34.0, points=8, innerRadius=0.6, name="Star"),
                        fill(col(CREAM, 0.9))), shape("Core", ellipse(18, 18), fill(col(APRICOT_PALE)))]
        elif icon == "snow":
            ic = [shape("Flake", E("Star", width=30.0, height=30.0, points=6, innerRadius=0.3, name="Star"),
                        fill(col(FOREST_PALE)))]
        else:
            ic = [leaf("Icon", 0, 12, 28, 18, rot=0.4 if icon == "leaf2" else -0.2, light=CREAM, dark=CREAM_SHADE,
                       rib=None)[0]]
        cid = ID()
        seasons.append(node(nm, *stack(
            shadow("Shadow", 60, 18, 0, 30, 0.3, 8),
            shape("Disc L", *path_el("M0 -30 C -18 -30 -30 -16 -30 0 C -30 16 -18 30 0 30 Z"), fill(col(c1))),
            shape("Disc R", *path_el("M0 -30 C 18 -30 30 -16 30 0 C 30 16 18 30 0 30 Z"), fill(col(c2))),
            *ic), x=sx_, y=sy_, id=cid))
        sc.pop(cid, 20 + i * 8, 44 + i * 8, 0.0, 1.0, "back")
    orbit = node("Seasons orbit", *seasons, x=CX, y=CY, id=orbit_id)
    sc.key(orbit_id, "rotation", [(0, -1.6, "hold"), (14, -1.6, "out"), (90, 0.0)])
    sc.idle.key(orbit_id, "rotation", [(0, 0.0, "lin"), (2400, 6.2831855)])
    sc.idle.dur = 2400
    for i, s in enumerate(seasons):  # counter-rotate so discs stay upright
        sc.key(s.id, "rotation", [(0, 1.6, "hold"), (14, 1.6, "out"), (90, 0.0)])
        sc.idle.key(s.id, "rotation", [(0, 0.0, "lin"), (2400, -6.2831855)])
    plant_id = ID()
    plant = pot("Persistent plant", CX, CY + 30, 64, 52, APRICOT, APRICOT_DARK, APRICOT_PALE,
                plant=node("Plant",
                           *[leaf(f"P{j}", x, 0, L, L * 0.55, rot=r, light=c1, dark=c2)[0] for j, (x, L, r, c1, c2) in
                             enumerate([(-4, 70, -0.55, LEAF, LEAF_DARK), (4, 76, 0.5, LEAF_PALE, LEAF),
                                        (0, 92, 0.02, LEAF_DARK, LEAF_DEEP), (0, 58, -1.1, FOREST_PALE, FOREST_SOFT)])]),
                id=plant_id)
    sc.pop(plant_id, 6, 40, 0.5, 1.0, "back")
    sc.sway(plant_id, 0.0, 0.02, 300, 0)
    hero, unit, copy = metric_text(sc, dict(x=24, y=100, w=342, size=124, align="center"), (32, 270), 326, "center",
                                   unit_kw=dict(x=24, y=232, w=342, align="center"))
    content = stack(bg_rect(FOREST),
                    shape("Glow", ellipse(420, 420), rad_grad([(0, col(LEAF, 0.18)), (1, col(LEAF, 0))], 0, 0, 210),
                          x=CX, y=CY),
                    ring, ticks, plant, orbit, hero, unit, copy)
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root
