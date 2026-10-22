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
def res3d(base, s, dims):
    """A 3D canvas's pixels-per-unit, bound to its real on-screen scale x device pixels (at least the
    authored supersampling), capped so the canvas stays <= 2048 px."""
    cap = min(3.0, 2048.0 / max(dims))
    return (float(base), LY.bindx(243, LY.clamp(s * LY.xmax(LY.DPR, base), 1, cap), "3D canvas res"))


def scene1():
    sc = Scene(1, FOREST, dur=118)
    st = LY.Stack(1, (None, None, "center"), None, (24, 104, 342, CH_DESIGN[1], "center"), (40, 336, 352, 742),
                  l_boost=1.3, ts_max_l=2.6, extra_h=36)
    sc.stack = st
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
    back = node("Back foliage", *stack(LY.corner("Back foliage BL", stack(back_leaves[0], back_leaves[2]), 0, 1),
                                       LY.corner("Back foliage BR", [back_leaves[1]], 1, 1)), id=bl_id)
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
        n, p = leaf(f"Jungle {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.4, morph=True)
        jungle.append(n)
        sc.unfurl(p, 26 + dl, 58 + dl, rot=r, rot0=r * 0.2)
        sc.sway(p["node"], r, 0.03 + 0.01 * (i % 3), 300 + 30 * (i % 4), i * 40)
    # the bendable hero leaf (signature interaction) sits in its own bend wrapper
    bend_id = ID()
    hl, hp = leaf("Hero leaf", 0, 0, 176, 168, rot=0.0, light=LEAF, dark=LEAF_DARK, kind="heart", rib_a=0.45, morph=True)
    sc.unfurl(hp, 30, 64, rot=0.0, rot0=-0.5)
    sc.sway(hp["node"], 0.0, 0.035, 330, 120)
    hero_bend = node("Hero bend", hl, x=226, y=660, rot=0.78, id=bend_id)
    sc.hero_bend = bend_id
    jungle.insert(3, hero_bend)

    # --- seed (motif): two paper shells hinged at the base
    seed_id = ID()
    stem_trim = ID()
    stem = line("Sprout", "M0 -24 C 8 -70 -10 -110 4 -168", LEAF, 6, trim_el=trim(0, 0, id=stem_trim))
    sc.key(stem_trim, "end", [(0, 0.0, "hold"), (16, 0.0, "outs"), (46, 1.0)])
    # two real paper half-shells (scripts/paperleaf, shape = 1): closed, they meet as an almond; they squash
    # (anticipation), crack along the seam and fall open, showing their darker inner faces
    s3, si = leaf3d("Seed shells 3D", 0, 6, pair=1, shape=1, L=160, W=64, fold=0.0, cup=1.1, curl=0.25, wave=0.0,
                    flip=1.45, spread=0.0, gap=0, veins=0.0, glow=0.25, fibre=0.8, ambient=0.66,
                    front=CREAM, back="#E6D8B0", rim="#FFFDF2", glowColor="#F8EED0", seed=7,
                    halfW=150, top=-210, bottom=40, res=res3d(2, st.art_t[2], (300, 250)))
    sc.live3d(si)
    sc.k3(si, "flip", [(0, 1.45, "hold"), (12, 1.45, "back"), (40, 1.12)])
    sc.k3(si, "spread", [(0, 0.0, "hold"), (12, 0.0, "back"), (42, 0.64)])
    sc.k3(si, "gap", [(0, 0.0, "hold"), (12, 0.0, "outs"), (40, 6.0)])
    sc.idle.key(si["spread"], "propertyValue", [(0, 0.64, "sine"), (180, 0.665, "sine"), (360, 0.64)])
    shells = node("Seed", *stack(stem, s3), x=195, y=700, id=seed_id)
    sc.key(seed_id, "scaleY", [(0, 1.0, "hold"), (1, 1.0, "in"), (12, 0.88, "back"), (26, 1.0)])
    sc.key(seed_id, "scaleX", [(0, 1.0, "hold"), (1, 1.0, "in"), (12, 1.08, "back"), (26, 1.0)])
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
    wm_leaf, wm_lp = leaf("Wordmark leaf", 286, 352, 34, 22, rot=0.7, light=LEAF, dark=LEAF_DARK, rib_a=0.5, morph=True)
    sc.unfurl(wm_lp, 70, 92, rot=0.7)

    # --- copy
    name_id, sup_id, col_id = ID(), ID(), ID()
    rg, rid = word_reveal()
    copy = column("Intro copy", 24, 104, 342, [
        text("Name", [("Alex", P("userName"))], font="fr", size=24, color=APRICOT, wght=520, soft=80, align="center",
             lp=lp(), id=name_id, overflow="ellipsis"),
        text("Headline", [("Your 2026 on Sprig", P("introHeadline"))], font="fr", size=38, color=CREAM, wght=560,
             soft=60, lh=40, align="center", lp=lp(), modifiers=[rg]),
        text("Support", [("A year, uniquely yours.", P("introSupport"))], font="dm", size=18, color=CREAM, lh=24,
             align="center", lp=lp(), op=0.82, id=sup_id),
    ], gap=10, align="topCenter", id=col_id)
    sc.key(name_id, "opacity", [(0, 0.0, "hold"), (52, 0.0, "outs"), (72, 1.0)])
    reveal_keys(sc.ef, rid, 58, 96)
    sc.key(sup_id, "opacity", [(0, 0.0, "hold"), (86, 0.0, "outs"), (108, 0.82)])
    period_id = ID()
    period = text("Period", [("January 1–December 31, 2026", P("periodLabel"))], font="dm", size=14, color=CREAM,
                  wght=500, ls=1.1, x=24, y=742, w=342, align="center", op=0.7, id=period_id)
    # the period line: above the controls in the tall portrait, under the copy column everywhere else
    ps = LY.clamp(st.ts, 0.85, 1.4)
    pcx = st.copy_left + st.copy_w * st.ts / 2
    period_place = LY.place("Period place", period,
                            x=LY.sel(LY.VW / 2 - 195 * ps, pcx - 195 * ps, pcx - 195 * ps, pcx - 195 * ps),
                            y=LY.sel(LY.P_CB - 18 - 742 * ps, st.copy_bottom + 14 - 742 * ps,
                                     st.copy_bottom + 22 - 742 * ps, st.copy_bottom + 22 - 742 * ps), s=ps)
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

    sc.art_t = st.art_t
    content = stack(bg_rect(FOREST), st.art_group(glow), back, LY.bottom_band("Hills", stack(hb, hf)),
                    st.art_group(*stack(seed_shadow, jungle, shells, wordmark, wm_leaf, handle, hit)),
                    st.copy_group(copy), period_place)
    root = build_scene_root(sc, content, clip=False)
    sc.ef.key(sc.root, "opacity", [(0, 1.0, "hold")])
    return sc, root


# ===================================================================== 2  Care moments
VINE2 = "M98 732 C 150 690 252 702 286 626 C 318 548 252 506 300 444 C 334 400 362 382 352 300"


def scene2():
    sc = Scene(2, FOREST)
    st = LY.Stack(2, (195, 118, "center"), 270, (32, 300, 300, CH_DESIGN[2], "left"), (52, 286, 392, 782))
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
    backn = node("Back foliage", LY.corner("Back foliage BL", stack(*back), 0, 1), id=back_id)
    sc.key(back_id, "x", [(0, -40, "hold"), (6, -40, "soft"), (70, 0)])
    sc.settle.append((back_id, "x", -14.0))

    # carried motif: the opened seed from scene 1 settles at the vine's root
    carry_id = ID()
    c3, ci = leaf3d("Carried seed 3D", 0, 6, pair=1, shape=1, L=160, W=64, fold=0.0, cup=1.1, curl=0.25, wave=0.0,
                    flip=1.12, spread=0.64, gap=6, veins=0.0, glow=0.25, fibre=0.8, ambient=0.66,
                    front=CREAM, back="#E6D8B0", rim="#FFFDF2", glowColor="#F8EED0", seed=7,
                    halfW=150, top=-210, bottom=40, res=res3d(2, st.art_t[2], (300, 250)))
    sc.live3d(ci)
    sc.k3(ci, "spread", [(0, 0.64, "hold"), (2, 0.64, "fold"), (42, 0.72)])
    seed = node("Carried seed", c3, x=92, y=744, sx=0.5, sy=0.5, id=carry_id)
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
        n, p = leaf(f"Vine leaf {i}", px, py, L, L * 0.62, rot=rot, light=c1, dark=c2, rib_a=0.4, morph=True)
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
    content = stack(bg_rect(FOREST), st.num_group(glow), backn, LY.bottom_band("Hills", stack(hb, hf)),
                    st.art_group(*stack(vine, vine_hi, leaves, drops, loop_drop, seed)),
                    st.num_group(*stack(hero, unit)), st.copy_group(copy))
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
    cols = [(LEAF, LEAF_DARK), (LEAF_PALE, LEAF), (LEAF_DARK, LEAF_DEEP), (LEAF_PALE, LEAF_DARK)]
    for j, spec in enumerate(kinds):
        x, y, L, Wd, r = spec[:5]
        kind = spec[5] if len(spec) > 5 else "leaf"
        c1, c2 = cols[(i + j) % 4]
        n, _ = leaf(f"Tuft {i}.{j}", x * s, y, L * s, Wd * s, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.35)
        kids.append(n)
    return node(f"Plant {i}", *kids)


def scene3():
    sc = Scene(3, FOREST_DEEP)
    st = LY.Stack(3, (28, 102, "left"), 310, (30, 340, 330, CH_DESIGN[3], "left"), (36, 486, 364, 770))
    layers = []
    specs = [  # y0, colour, shade: three sheets of green paper, lightest at the back (aerial depth)
        (556, "#4E8A69", FOREST_PALE),
        (626, FOREST_PALE, FOREST_SOFT),
        (704, FOREST_SOFT, FOREST_MID),
    ]
    for i, (y0, c, s) in enumerate(specs):
        lid = ID()
        # the sheets run far past the design edges (and down) so they still reach the viewport edges
        # when the art is scaled down or sits in one half of a wide canvas
        ridge = (f"C -1240 {y0+10} -620 {y0-30} -30 {y0+30} C 40 {y0-24} 120 {y0+18} 196 {y0-6} "
                 f"C 270 {y0-28} 340 {y0+10} 420 {y0-14} C 980 {y0-50} 1500 {y0+20} 2100 {y0-10}"
                 if i % 2 == 0 else
                 f"C -1240 {y0-30} -620 {y0+20} -30 {y0-10} C 60 {y0+20} 140 {y0-30} 220 {y0+4} "
                 f"C 300 {y0+30} 360 {y0-20} 420 {y0+6} C 980 {y0+40} 1500 {y0-24} 2100 {y0+6}")
        start = f"M-1900 {y0}"
        d = f"{start} {ridge} L2100 1700 L-1900 1700 Z"
        lyr = node(f"Paper layer {i}", *stack(
                   poly("Shadow", d, "#05130E", a=0.35, y=-8, feather=14),
                   poly("Paper", d, c),
                   line("Edge light", f"{start} {ridge}", LEAF_PALE, 1.6, 0.55)),
                   id=lid)
        layers.append(lyr)
        sc.key(lid, "y", [(0, 160 + 60 * i, "hold"), (2 + i * 6, 160 + 60 * i, "out"), (40 + i * 6, 0)])
        sc.settle.append((lid, "y", 10.0 + 6 * i))
    pots = []
    spots = [(70, 556, 0.62), (150, 548, 0.6), (240, 552, 0.62), (322, 545, 0.6),
             (104, 628, 0.8), (205, 622, 0.82), (300, 630, 0.78),
             (138, 712, 1.0), (262, 706, 1.02)]
    body = [(APRICOT, APRICOT_DARK, APRICOT_PALE), (CREAM, CREAM_DARK, "#FFFFFF"), (APRICOT_PALE, "#E9B48F", "#FFF1E4"),
            (CREAM_SHADE, CREAM_DARK, "#FFFFFF")]
    for i, (x, y, s) in enumerate(spots):
        pid = ID()
        b, sh, rim = body[i % 4]
        pt = pot(f"Pot {i}", x, y, 60, 50, b, sh, rim, plant=plant_tuft(i, 1.15), s=s, id=pid)
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
                    st.art_group(*stack(
                        shape("Glow", ellipse(500, 360), rad_grad([(0, col(LEAF, 0.12)), (1, col(LEAF, 0))], 0, 0, 250),
                              x=300, y=520),
                        layers[0], pots_sorted[0:4], layers[1], pots_sorted[4:7], layers[2], pots_sorted[7:])),
                    st.num_group(*stack(hero, unit)), st.copy_group(copy))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 4  New leaves
def fern(name, x, y, L, rot, n=7, c1=LEAF_DARK, c2=LEAF_DEEP, s=1.0):
    """A frond: a curved stem with paired leaflets shrinking toward the tip."""
    kids = [line("Stem", f"M0 0 C {L*0.1:.1f} {-L*0.35:.1f} {L*0.05:.1f} {-L*0.7:.1f} {L*0.18:.1f} {-L:.1f}", c2, 2.2)]
    for i in range(n):
        f = (i + 1) / (n + 1)
        (px, py), ang = point_at(f"M0 0 C {L*0.1:.1f} {-L*0.35:.1f} {L*0.05:.1f} {-L*0.7:.1f} {L*0.18:.1f} {-L:.1f}", f)
        ll = L * 0.32 * (1 - f * 0.65)
        for sd in (-1, 1):
            kids.append(leaf(f"{name} leaflet {i}{'LR'[sd > 0]}", px, py, ll, ll * 0.36, rot=ang + math.pi / 2 + sd * 1.05,
                             light=c1, dark=c2, rib=None)[0])
    return node(name, *kids, x=x, y=y, rot=rot, sx=s, sy=s)


def scene4():
    sc = Scene(4, CREAM, light=True)
    st = LY.Stack(4, (195, 100, "center"), 250, (32, 268, 326, CH_DESIGN[4], "center"), (8, 318, 382, 840),
                  art_ay=(1.0, 0.5, 0.75, 0.5))
    # --- the sunrise inside the opened leaves
    sun_id, disc_id = ID(), ID()
    sun = shape("Sun glow", ellipse(420, 420), rad_grad([(0, col(APRICOT_PALE, 0.95)), (0.45, col(APRICOT_PALE, 0.55)),
                                                       (1, col(APRICOT_PALE, 0))], 0, 0, 210), x=195, y=560, id=sun_id)
    disc = shape("Sun", ellipse(140, 140), fill(col("#FBE3C8")), x=195, y=548, id=disc_id)
    sc.pop(sun_id, 6, 60, 0.3, 1.0, "outs")
    sc.pop(disc_id, 20, 62, 0.0, 1.0, "outs")
    sc.idle.key(sun_id, "scaleX", [(0, 1.0, "sine"), (180, 1.04, "sine"), (360, 1.0)])
    sc.idle.key(sun_id, "scaleY", [(0, 1.0, "sine"), (180, 1.04, "sine"), (360, 1.0)])
    # --- the jungle diorama the leaves open around: misty back strap leaves, ferns, big hearts, bright front
    back, mid, front = [], [], []
    for i, (x, y, L, Wd, r) in enumerate([(128, 756, 230, 46, -0.42), (176, 760, 270, 40, -0.14), (226, 760, 262, 42, 0.2),
                                           (268, 756, 214, 46, 0.46)]):
        n, p = leaf(f"Mist strap {i}", x, y, L, Wd, rot=r, light="#CFE3AE", dark="#B8D394", rib=None, morph=True)
        back.append(n)
        sc.unfurl(p, 30 + i * 4, 70 + i * 4, rot=r, rot0=r * 0.3)
        sc.sway(p["node"], r, 0.018, 420, i * 70)
    for i, (x, y, L, r, c1, c2) in enumerate([(118, 770, 220, -0.55, LEAF_DARK, LEAF_DEEP), (276, 770, 210, 0.55, LEAF, LEAF_DARK),
                                               (160, 772, 160, -0.18, FOREST_PALE, FOREST_SOFT)]):
        fid = ID()
        fr = fern(f"Fern {i}", x, y, L, r, c1=c1, c2=c2)
        fr.attrs["id"] = fid
        mid.append(fr)
        sc.key(fid, "scaleY", [(0, 0.0, "hold"), (34 + i * 6, 0.0, "backs"), (74 + i * 6, 1.0)])
        sc.key(fid, "scaleX", [(0, 0.6, "hold"), (34 + i * 6, 0.6, "backs"), (74 + i * 6, 1.0)])
        sc.sway(fid, r, 0.025, 380, i * 90)
    for i, (x, y, L, Wd, r, c1, c2, kind) in enumerate([
        (136, 744, 140, 128, -0.62, FOREST_SOFT, FOREST_MID, "heart"),
        (256, 740, 132, 120, 0.66, FOREST_PALE, FOREST_SOFT, "heart"),
        (178, 760, 120, 104, -0.22, LEAF_DARK, LEAF_DEEP, "heart"),
        (218, 760, 112, 98, 0.3, LEAF, LEAF_DARK, "heart"),
        (156, 772, 112, 48, -1.0, APRICOT, APRICOT_DARK, "leaf"),
        (238, 772, 118, 46, 0.95, APRICOT_DARK, "#C97B4C", "leaf"),
        (196, 776, 140, 42, 0.04, LEAF_PALE, LEAF, "leaf"),
    ]):
        n, p = leaf(f"Canopy {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.4, morph=True)
        front.append(n)
        sc.unfurl(p, 40 + i * 6, 76 + i * 6, rot=r)
        sc.sway(p["node"], r, 0.03, 320 + 25 * i, i * 45)
    # --- the hero: one enormous folded paper leaf pair (real 3D, scripts/paperleaf) opening around it all.
    # Closed it is a tall paper bud; it shivers (anticipation), then the halves fall open and roll their inner
    # cream faces toward us, tips curling over, exactly the concept's cradle.
    g3, gi = leaf3d("Giant leaves 3D", 195, 812, pair=1, L=440, W=138, shape=0, fold=0.3, cup=0.55, curl=0.0,
                    tipCurl=0.5, twist=0.4, wave=0.6, gap=8, spread=0.0, flip=-0.2, pitch=0.0, persp=1500,
                    front="#7FA850", back="#F2EBD3", glowColor="#E6F2B8", rim="#FFFBEA", glow=0.6, veins=0.9,
                    ambient=0.5, shadow=0.2, shadowX=0, shadowY=16, shadowBlur=30, seed=4,
                    halfW=275, top=-530, bottom=20, res=res3d(1.6, st.art_t[2], (550, 550)))
    sc.live3d(gi)
    # closed: a tall paper bud. It shivers (anticipation), then falls open, twisting its cream inner faces out
    sc.k3(gi, "spread", [(0, 0.0, "hold"), (16, 0.0, "io"), (21, -0.018, "io"), (26, 0.022, "antic"), (32, 0.0, "backs"),
                         (88, 0.47)])
    sc.k3(gi, "gap", [(0, 8, "hold"), (32, 8, "outs"), (84, 76)])
    sc.k3(gi, "flip", [(0, -0.2, "hold"), (32, -0.2, "outs"), (88, -0.42)])
    sc.k3(gi, "twist", [(0, 0.4, "hold"), (36, 0.4, "backs"), (96, 2.0)])
    sc.k3(gi, "curl", [(0, 0.0, "hold"), (36, 0.0, "outs"), (92, -0.12)])
    sc.k3(gi, "tipCurl", [(0, 0.5, "hold"), (40, 0.5, "backs"), (104, 0.9)])
    sc.idle.key(gi["spread"], "propertyValue", [(0, 0.47, "sine"), (180, 0.482, "sine"), (360, 0.47)])
    sc.idle.key(gi["twist"], "propertyValue", [(0, 2.0, "sine"), (180, 2.06, "sine"), (360, 2.0)])
    sc.settle.append((gi["spread"], "propertyValue", -0.08))
    hero, unit, copy = metric_text(sc, dict(x=24, y=100, w=342, size=124, align="center", color=FOREST), (32, 268),
                                   326, "center", unit_kw=dict(x=24, y=230, w=342, align="center"))
    flutter = []
    for i, (x, y, r) in enumerate([(60, 806, 0.8), (330, 812, -0.6), (98, 830, 1.6), (296, 834, 2.2)]):
        n, p = leaf(f"Fallen leaf {i}", x, y, 24, 13, rot=r, light=LEAF_DARK, dark=LEAF_DEEP, rib=None)
        flutter.append(n)
        sc.key(p["node"], "y", [(0, y - 320, "hold"), (40 + i * 8, y - 320, "outs"), (96 + i * 8, y)])
        sc.key(p["node"], "x", [(0, x + 40, "hold"), (40 + i * 8, x + 40, "sine"), (68 + i * 8, x - 24, "sine"),
                                (96 + i * 8, x)])
        sc.key(p["node"], "rotation", [(0, r - 3, "hold"), (40 + i * 8, r - 3, "outs"), (96 + i * 8, r)])
    ground = shape("Ground shadow", ellipse(420, 90), fill(col("#B7A77A", 0.3), feather=26), x=195, y=800)
    content = stack(bg_rect(CREAM), st.art_group(*stack(sun, disc, back, g3, mid, ground, front, flutter)),
                    st.num_group(*stack(hero, unit)), st.copy_group(copy))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 5  Cuttings rooted
def scene5():
    sc = Scene(5, FOREST)
    st = LY.Stack(5, (362, 104, "right"), 252, (30, 290, 330, CH_DESIGN[5], "left"), (96, 436, 332, 782))
    JX, JY = 214, 650   # jar centre (clear of the controls)
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
                        light=[LEAF, LEAF_PALE, LEAF_DARK][(i + j) % 3], dark=[LEAF_DARK, LEAF, LEAF_DEEP][(i + j) % 3], morph=True)
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
                    st.art_group(*stack(shape("Glow", ellipse(460, 460), rad_grad([(0, col(LEAF, 0.16)), (1, col(LEAF, 0))],
                                                                                   0, 0, 230), x=JX, y=JY), jar)),
                    st.num_group(*stack(hero, unit)), st.copy_group(copy), st.art_group(cl))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 6  Day care streak
VINE6 = ("M28 512 C 140 500 260 524 330 512 C 386 502 386 602 330 594 C 250 582 140 606 60 594 "
         "C 4 586 4 686 60 676 C 150 664 270 688 364 672")


def scene6():
    sc = Scene(6, LEAF, light=True)
    st = LY.Stack(6, (195, 104, "center"), 256, (32, 274, 326, CH_DESIGN[6], "center"), (16, 462, 374, 724))
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
        n, p = leaf(f"Streak leaf {i}", px, py, 30, 18, rot=ang - 1.2, light=LEAF, dark=LEAF_DEEP, rib_a=0.4, morph=True)
        sprigs.append(n)
        sc.unfurl(p, 40 + i * 9, 62 + i * 9, rot=ang - 1.2)
        sc.sway(p["node"], ang - 1.2, 0.06, 240, i * 40)
    hero, unit, copy = metric_text(sc, dict(x=24, y=104, w=342, size=124, align="center", color=FOREST), (32, 274),
                                   326, "center", unit_kw=dict(x=24, y=236, w=342, align="center"))
    deco = []
    for i, (x, y, L, r) in enumerate([(-6, 860, 230, 0.5), (396, 870, 210, -0.55)]):
        n, p = leaf(f"Corner leaf {i}", x, y, L, L * 0.5, rot=r, light=LEAF_DARK, dark=LEAF_DEEP, rib_a=0.25)
        deco.append(LY.corner(f"Corner leaf {i} place", [n], i, 1))
        sc.sway(p["node"], r, 0.03, 380, i * 150)
        sc.key(p["node"], "y", [(0, y + 120, "hold"), (6, y + 120, "out"), (50, y)])
    content = stack(bg_rect(LEAF),
                    st.num_group(shape("Glow", ellipse(500, 380), rad_grad([(0, col(LEAF_PALE, 0.8)), (1, col(LEAF_PALE, 0))],
                                                                           0, 0, 250), x=195, y=200)),
                    deco, st.art_group(*stack(paper, vine, knots, sprigs)), st.num_group(*stack(hero, unit)),
                    st.copy_group(copy))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 7  Plants shared
HAND_D = ("M-1400 -24 L-20 -26 C 0 -27 14 -36 30 -48 C 42 -57 54 -50 50 -40 C 46 -31 38 -26 46 -22 "
          "L 112 -20 C 126 -19 126 -6 112 -5 L 64 -2 C 86 0 110 2 118 6 C 130 12 124 24 110 22 "
          "L 70 18 C 84 22 96 26 98 32 C 100 40 88 42 80 38 L 40 26 C 20 28 0 26 -20 24 L -1400 24 Z")
HAND_SHADE_D = ("M-1400 4 L-20 6 C 4 8 26 6 46 4 L 118 6 C 130 12 124 24 110 22 L 70 18 C 84 22 96 26 98 32 "
                "C 100 40 88 42 80 38 L 40 26 C 20 28 0 26 -20 24 L -1400 24 Z")


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
    st = LY.Stack(7, (30, 96, "left"), 246, (30, 268, 330, CH_DESIGN[7], "left"), (0, 380, 390, 844),
                  art_ay=(1.0, 1.0, 1.0, 1.0))
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
    ), x=292, y=636, sx=0.9, sy=0.9, id=win_id)
    sc.key(win_id, "opacity", [(0, 0.0, "hold"), (8, 0.0, "outs"), (36, 1.0)])
    sc.key(win_id, "y", [(0, 680, "hold"), (8, 680, "outs"), (40, 636)])
    lh_id, rh_id = ID(), ID()
    lhand = hand("Giving hand", 1, (APRICOT, APRICOT_DARK, CREAM_SHADE), lh_id)
    rhand = hand("Receiving hand", -1, (LEAF, LEAF_DARK, CREAM_SHADE), rh_id)
    # two big paper hands reach up from the bottom corners toward each other (palms up)
    HS, HR = 1.38, 0.34
    lh_x, lh_y, rh_x, rh_y = 30, 734, 362, 706
    for hid, hx, hy, r, sgn, d0 in ((lh_id, lh_x, lh_y, -HR, 1, 2), (rh_id, rh_x, rh_y, HR, -1, 12)):
        sc.key(hid, "scaleX", [(0, HS, "hold")])
        sc.key(hid, "scaleY", [(0, HS, "hold")])
        sc.key(hid, "x", [(0, hx - sgn * 220, "hold"), (d0, hx - sgn * 220, "out"), (d0 + 34, hx)])
        sc.key(hid, "y", [(0, hy + 120, "hold"), (d0, hy + 120, "out"), (d0 + 34, hy)])
    sc.key(lh_id, "rotation", [(0, -HR + 0.3, "hold"), (2, -HR + 0.3, "out"), (36, -HR, "io"), (52, -HR, "io"),
                               (62, -HR - 0.14, "back"), (84, -HR)])
    sc.key(rh_id, "rotation", [(0, HR - 0.3, "hold"), (12, HR - 0.3, "out"), (46, HR, "back"), (78, HR, "back"),
                               (90, HR + 0.1, "io"), (104, HR)])
    sc.sway(lh_id, -HR, 0.02, 360, 0)
    sc.sway(rh_id, HR, 0.02, 360, 180)

    def palm(hx, hy, r, sgn):
        lx, ly = 58 * sgn, -26
        c, s_ = math.cos(r), math.sin(r)
        return hx + HS * (lx * c - ly * s_), hy + HS * (lx * s_ + ly * c)
    cut_id = ID()
    cutting = pot("Shared cutting", 0, 0, 40, 32, APRICOT_DARK, "#C9784A", APRICOT_PALE, plant=node("Cutting plant",
                  *[leaf(f"Cut leaf {j}", 0, 0, L, L * 0.6, rot=r, light=LEAF, dark=LEAF_DARK)[0]
                    for j, (L, r) in enumerate([(40, -0.5), (46, 0.45), (52, 0.0)])]), s=1.3, id=cut_id)
    # arc: giving palm -> over -> receiving palm (synchronised with the count); the pot stands on the palm
    pl, pr = palm(lh_x, lh_y, -HR, 1), palm(rh_x, rh_y, HR, -1)
    p0 = (pl[0], pl[1] - 32 * 1.3)
    p2 = (pr[0], pr[1] - 32 * 1.3)
    arc = [(0, p0), (54, p0), (66, ((p0[0] + p2[0]) / 2 - 10, min(p0[1], p2[1]) - 110)), (80, (p2[0] - 6, p2[1] - 40)),
           (90, p2)]
    sc.key(cut_id, "x", [(0, p0[0] - 220, "hold"), (2, p0[0] - 220, "out"), (36, p0[0], "hold")] +
           [(f, p[0], "sine") for f, p in arc[1:]])
    sc.key(cut_id, "y", [(0, p0[1] + 120, "hold"), (2, p0[1] + 120, "out"), (36, p0[1], "hold"), (54, p0[1], "out")] +
           [(f, p[1], "sine" if f < 80 else "back") for f, p in arc[2:]])
    sc.key(cut_id, "rotation", [(0, 0.0, "hold"), (54, 0.0, "io"), (68, 0.25, "io"), (90, 0.0)])
    trail_trim = ID()
    trail = line("Green trail", f"M{p0[0]} {p0[1]-10} C {p0[0]+30} {p0[1]-110} {p2[0]-40} {p2[1]-120} {p2[0]} {p2[1]-30}",
                 LEAF_DARK, 2.5, 0.6, trim_el=trim(0, 0, id=trail_trim))
    sc.key(trail_trim, "end", [(0, 0.0, "hold"), (56, 0.0, "io"), (88, 1.0)])
    sc.key(trail_trim, "start", [(0, 0.0, "hold"), (76, 0.0, "io"), (104, 1.0)])
    sparks = []
    for i, (x, y) in enumerate([(200, 500), (244, 522), (166, 530)]):
        sid = ID()
        sparks.append(shape(f"Spark {i}", E("Star", width=14.0, height=14.0, points=4, innerRadius=0.35, name="Star"),
                            fill(col(APRICOT)), x=x, y=y, sx=0.0, sy=0.0, id=sid))
        sc.key(sid, "scaleX", [(0, 0.0, "hold"), (86 + i * 4, 0.0, "back"), (98 + i * 4, 1.0)])
        sc.key(sid, "scaleY", [(0, 0.0, "hold"), (86 + i * 4, 0.0, "back"), (98 + i * 4, 1.0)])
        sc.idle.key(sid, "rotation", [(0, 0.0, "lin"), (360, 6.2831855)])
    hero, unit, copy = metric_text(sc, dict(x=30, y=96, w=330, size=124, align="left", color=FOREST), (30, 268), 330,
                                   "left", unit_kw=dict(x=34, y=226, w=330, align="left"))
    floor = LY.bottom_band("Floor place", [shape("Floor", rect(W + 40, 160), fill(col(CREAM_SHADE)), x=195, y=800)])
    art = st.art_group(*stack(window, trail, rhand, lhand, cutting, sparks))
    content = stack(bg_rect(CREAM), floor, LY.panel(st, art, CREAM_SHADE), st.num_group(*stack(hero, unit)),
                    st.copy_group(copy))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root


# ===================================================================== 8  Active months
def scene8():
    sc = Scene(8, FOREST)
    st = LY.Stack(8, (195, 100, "center"), 252, (32, 270, 326, CH_DESIGN[8], "center"), (40, 468, 350, 780))
    k = 8
    CX, CY, R = 195, 624, 114
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
                    st.art_group(*stack(shape("Glow", ellipse(420, 420), rad_grad([(0, col(LEAF, 0.18)), (1, col(LEAF, 0))],
                                                                                0, 0, 210), x=CX, y=CY),
                                        ring, ticks, plant, orbit)),
                    st.num_group(*stack(hero, unit)), st.copy_group(copy))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root
