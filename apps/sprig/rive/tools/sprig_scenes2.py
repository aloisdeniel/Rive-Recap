"""Scenes 9 (persona) and 10 (summary) plus the standalone ShareCard component artboard."""
from sprig_scenes import *  # noqa
from rml import _f  # noqa

ARCH_D = "M-138 0 L-138 -262 C -138 -342 -76 -404 0 -404 C 76 -404 138 -342 138 -262 L138 0 Z"
PERSONAS = [
    ("Canopy Keeper", "You made room for a jungle.", "FFF6F1DC"),
    ("Propagation Pro", "You saw a new beginning in every cutting.", "FFA8CC72"),
    ("Patient Grower", "You gave growth the time it needed.", "FFF3AD7D"),
    ("Windowsill Wanderer", "You found possibility in every sunny corner.", "FF173E32"),
]


class PersonaArt:
    def __init__(self):
        self.groups = []
        self.enter = []
        self.idle = []
        self.final = []


def persona_emblems():
    """Four emblems, each with its own silhouette and choreography. Returns (elements, PersonaArt)."""
    pa = PersonaArt()
    els = []
    # ---------------- 0 Canopy Keeper: layered canopy (wide dome)
    g0 = ID(); a0 = Anim("Persona 0 Canopy Keeper reveal", 150); i0 = Anim("Persona 0 idle", 360, "loop")
    tiers = []
    tier_specs = [(684, 7, 200, LEAF_DEEP, FOREST_SOFT, 92), (628, 5, 150, LEAF_DARK, LEAF_DEEP, 80),
                  (574, 3, 96, LEAF, LEAF_DARK, 70)]
    for t, (ty, n, spread, c1, c2, L) in enumerate(tier_specs):
        tid = ID()
        leaves = []
        for j in range(n):
            f = (j / (n - 1)) - 0.5 if n > 1 else 0
            r = f * 2.0
            lx = f * spread * 0.55
            lf, lpp = leaf(f"Tier {t} leaf {j}", lx, 0, L, L * 0.62, rot=r, light=c1, dark=c2, rib_a=0.35)
            leaves.append(lf)
            d0 = 46 + t * 14 + abs(f) * 16
            a0.key(lpp["node"], "rotation", [(0, r * 0.2, "hold"), (d0, r * 0.2, "backs"), (d0 + 30, r)])
            a0.key(lpp["right"], "scaleX", [(0, 0.1, "hold"), (d0 + 4, 0.1, "out"), (d0 + 30, 1.0)])
            i0.key(lpp["node"], "rotation", [(0, r, "sine"), (90 + j * 9, r + 0.04, "sine"), (270, r - 0.03, "sine"), (360, r)])
        tiers.append(node(f"Tier {t}", *leaves, x=195, y=ty, id=tid))
        a0.key(tid, "y", [(0, ty - 120, "hold"), (40 + t * 14, ty - 120, "back"), (70 + t * 14, ty)])
        a0.key(tid, "opacity", [(0, 0.0, "hold"), (40 + t * 14, 0.0, "lin"), (52 + t * 14, 1.0)])
    trunk = line("Trunk", "M195 760 C 192 730 198 712 195 690", FOREST_SOFT, 8)
    els.append(node("Emblem Canopy Keeper", *stack(trunk, *tiers), id=g0, op=0.0))
    pa.groups.append(g0); pa.enter.append(a0); pa.idle.append(i0)

    # ---------------- 1 Propagation Pro: rooted cutting (tall, slim, roots)
    g1 = ID(); a1 = Anim("Persona 1 Propagation Pro reveal", 150); i1 = Anim("Persona 1 idle", 360, "loop")
    st_trim, r_trim = ID(), ID()
    water_id = ID()
    stem1 = line("Cutting stem", "M195 690 C 190 640 202 590 196 520", LEAF_DARK, 6, trim_el=trim(0, 0, id=st_trim))
    roots1 = line("Roots", "M195 690 C 190 712 176 726 160 748 M195 690 C 198 718 206 734 222 756 "
                           "M195 690 C 196 716 194 736 196 764 M178 722 C 168 724 156 730 146 738 "
                           "M208 728 C 220 730 232 736 240 746", CREAM_DARK, 2.4, trim_el=trim(0, 0, id=r_trim))
    water = shape("Water band", rect(276, 90), fill(col(LEAF, 0.25)), x=195, y=730, id=water_id)
    a1.key(st_trim, "end", [(0, 0.0, "hold"), (44, 0.0, "soft"), (82, 1.0)])
    a1.key(r_trim, "end", [(0, 0.0, "hold"), (70, 0.0, "soft"), (130, 1.0)])
    a1.key(water_id, "scaleY", [(0, 0.0, "hold"), (40, 0.0, "outs"), (70, 1.0)])
    tops1 = []
    for j, (L, r) in enumerate([(74, -0.7), (84, 0.6), (62, -0.05)]):
        lf, lpp = leaf(f"Cutting leaf {j}", 196, 528 + j * 4, L, L * 0.62, rot=r, light=[LEAF, LEAF_PALE, LEAF_DARK][j],
                       dark=[LEAF_DARK, LEAF, LEAF_DEEP][j])
        tops1.append(lf)
        a1.key(lpp["node"], "scaleX", [(0, 0.0, "hold"), (76 + j * 8, 0.0, "back"), (104 + j * 8, 1.0)])
        a1.key(lpp["node"], "scaleY", [(0, 0.0, "hold"), (76 + j * 8, 0.0, "back"), (104 + j * 8, 1.0)])
        i1.key(lpp["node"], "rotation", [(0, r, "sine"), (120, r + 0.05, "sine"), (240, r - 0.04, "sine"), (360, r)])
    els.append(node("Emblem Propagation Pro", *stack(water, roots1, stem1, *tops1), id=g1, op=0.0))
    pa.groups.append(g1); pa.enter.append(a1); pa.idle.append(i1)

    # ---------------- 2 Patient Grower: slow-opening bud (round)
    g2 = ID(); a2 = Anim("Persona 2 Patient Grower reveal", 230); i2 = Anim("Persona 2 idle", 480, "loop")
    stem2 = line("Bud stem", "M195 770 C 190 700 200 660 195 600", LEAF_DARK, 6)
    side_leaves = []
    for j, (y, r) in enumerate([(700, -0.9), (680, 0.85)]):
        lf, lpp = leaf(f"Bud leaf {j}", 195, y, 70, 40, rot=r, light=LEAF, dark=LEAF_DARK)
        side_leaves.append(lf)
        a2.key(lpp["node"], "scaleX", [(0, 0.0, "hold"), (40 + j * 10, 0.0, "back"), (74 + j * 10, 1.0)])
        a2.key(lpp["node"], "scaleY", [(0, 0.0, "hold"), (40 + j * 10, 0.0, "back"), (74 + j * 10, 1.0)])
    petals = []
    bud_id = ID()
    for j in range(7):
        f = j / 6 - 0.5
        open_r = f * 2.4
        lf, lpp = leaf(f"Petal {j}", 0, 0, 96 - abs(f) * 30, 58, rot=f * 0.25,
                       light=[APRICOT, APRICOT_PALE][j % 2], dark=[APRICOT_DARK, APRICOT][j % 2], rib=CREAM, rib_a=0.3)
        petals.append(lf)
        a2.key(lpp["node"], "rotation", [(0, f * 0.25, "hold"), (60, f * 0.25, (0.5, 0.0, 0.3, 1.0)), (220, open_r)])
        i2.key(lpp["node"], "rotation", [(0, open_r, "sine"), (240, open_r * 0.93, "sine"), (480, open_r)])
    center = shape("Bud heart", ellipse(26, 26), fill(col(CREAM)), y=-6)
    bud = node("Bud", center, *petals[::-1], x=195, y=604, id=bud_id)
    a2.key(bud_id, "scaleX", [(0, 0.0, "hold"), (30, 0.0, "back"), (64, 1.0)])
    a2.key(bud_id, "scaleY", [(0, 0.0, "hold"), (30, 0.0, "back"), (64, 1.0)])
    a2.key(center.id, "scaleX", [(0, 0.0, "hold"), (150, 0.0, "back"), (200, 1.0)])
    a2.key(center.id, "scaleY", [(0, 0.0, "hold"), (150, 0.0, "back"), (200, 1.0)])
    els.append(node("Emblem Patient Grower", *stack(stem2, *side_leaves, bud), id=g2, op=0.0))
    pa.groups.append(g2); pa.enter.append(a2); pa.idle.append(i2)

    # ---------------- 3 Windowsill Wanderer: arched window with leaves (arch silhouette)
    g3 = ID(); a3 = Anim("Persona 3 Windowsill Wanderer reveal", 160); i3 = Anim("Persona 3 idle", 600, "loop")
    w_arch = "M-78 0 L-78 -150 C -78 -200 -42 -232 0 -232 C 42 -232 78 -200 78 -150 L78 0 Z"
    fr_trim, mu_trim = ID(), ID()
    sun_id = ID()
    win = node("Window", *stack(
        poly("Pane", w_arch, APRICOT_PALE, a=0.8),
        shape("Accent sun", ellipse(54, 54), fill(col(APRICOT), color_id=None,
                                                  bind=bind(P("personaColor"), 37)),
              stroke(col(FOREST, 0.25), 1.5), x=-30, y=-170, id=sun_id),
        line("Mullions", "M0 -232 L0 0 M-78 -120 L78 -120", CREAM, 5, trim_el=trim(0, 0, id=mu_trim)),
        line("Frame", w_arch, FOREST_SOFT, 7, trim_el=trim(0, 0, id=fr_trim)),
        shape("Sill", rect(196, 16, 4), fill(col(FOREST_SOFT)), y=6),
    ), x=195, y=726)
    a3.key(fr_trim, "end", [(0, 0.0, "hold"), (40, 0.0, "soft"), (90, 1.0)])
    a3.key(mu_trim, "end", [(0, 0.0, "hold"), (70, 0.0, "soft"), (100, 1.0)])
    a3.key(sun_id, "x", [(0, -40, "hold"), (60, -40, "soft"), (150, 26)])
    a3.key(sun_id, "y", [(0, -100, "hold"), (60, -100, "soft"), (150, -176)])
    i3.key(sun_id, "x", [(0, 26, "sine"), (300, 34, "sine"), (600, 26)])
    peek = []
    for j, (x, y, L, r, c1, c2) in enumerate([(70, 700, 130, 0.9, LEAF, LEAF_DARK), (320, 690, 140, -0.95, LEAF_PALE, LEAF),
                                              (90, 600, 100, 1.3, LEAF_DARK, LEAF_DEEP), (300, 590, 96, -1.25, FOREST_PALE, FOREST_SOFT)]):
        lf, lpp = leaf(f"Peeking leaf {j}", x, y, L, L * 0.6, rot=r, light=c1, dark=c2)
        peek.append(lf)
        r0 = r + (0.9 if r > 0 else -0.9)
        a3.key(lpp["node"], "rotation", [(0, r0, "hold"), (80 + j * 10, r0, "back"), (116 + j * 10, r)])
        a3.key(lpp["node"], "opacity", [(0, 0.0, "hold"), (80 + j * 10, 0.0, "lin"), (90 + j * 10, 1.0)])
        i3.key(lpp["node"], "rotation", [(0, r, "sine"), (150, r + 0.05, "sine"), (450, r - 0.04, "sine"), (600, r)])
    potp = pot("Sill pot", 195, 690, 42, 34, APRICOT, APRICOT_DARK, APRICOT_PALE,
               plant=node("Sill plant", leaf("SP0", 0, 0, 40, 24, rot=-0.4)[0], leaf("SP1", 0, 0, 44, 24, rot=0.4)[0]))
    a3.key(potp.id, "scaleX", [(0, 0.0, "hold"), (100, 0.0, "back"), (124, 1.0)])
    a3.key(potp.id, "scaleY", [(0, 0.0, "hold"), (100, 0.0, "back"), (124, 1.0)])
    els.append(node("Emblem Windowsill Wanderer", *stack(win, potp, *peek), id=g3, op=0.0))
    pa.groups.append(g3); pa.enter.append(a3); pa.idle.append(i3)

    for a in pa.enter:  # final pose for reduced motion / mid-scene persona swaps
        fa = Anim(a.name.replace("reveal", "static"), 16)
        for (obj, p), keys in a.tracks.items():
            fa.key(obj, p, [(0, keys[-1][1], "hold")])
        pa.final.append(fa)
    for k in range(4):
        for anims in (pa.enter[k], pa.final[k]):
            for j, g in enumerate(pa.groups):
                if j == k:
                    if anims is pa.final[k]:
                        anims.key(g, "opacity", [(0, 0.0, "lin"), (14, 1.0)])
                    else:
                        anims.key(g, "opacity", [(0, 1.0, "hold")])
                else:
                    anims.key(g, "opacity", [(0, 0.0, "hold")])
    return els, pa


def scene9():
    sc = Scene(9, FOREST, dur=110)
    label_id, name_id, desc_id, col_id = ID(), ID(), ID(), ID()
    rg, rid = word_reveal(units=0)
    copy = column("Persona copy", 24, 104, 342, [
        text("Label", [("Your personal style", P("personaLabel"))], font="dm", size=14, color=CREAM, wght=500, ls=2.4,
             align="center", lp=lp(), op=0.8, id=label_id),
        text("Persona", [("Canopy Keeper", P("personaName"))], font="fr", size=46, color=CREAM, wght=600, soft=80,
             wonk=1, lh=48, align="center", lp=lp(), id=name_id, modifiers=[rg]),
        text("Description", [("You made room for a jungle.", P("personaDescription"))], font="dm", size=19,
             color=CREAM, lh=26, align="center", lp=lp(), op=0.86, id=desc_id),
    ], gap=12, align="topCenter", id=col_id)
    sc.key(label_id, "opacity", [(0, 0.0, "hold"), (40, 0.0, "outs"), (60, 0.8)])
    reveal_keys(sc.ef, rid, 48, 92, "out")
    sc.key(desc_id, "opacity", [(0, 0.0, "hold"), (84, 0.0, "outs"), (106, 0.86)])
    arch_id = ID()
    rim_bind = bind(P("personaColor"), 37)
    clip_src = ID()
    emb_els, pa = persona_emblems()
    # hanging pothos strands inside the arch (every persona): they unroll down from the arch top and sway
    strands = []
    for i, (x, L, ph) in enumerate([(-96, 230, 0), (-70, 150, 60), (84, 200, 30), (104, 120, 90)]):
        sid_, st_trim = ID(), ID()
        kids = [line("Strand", f"M0 0 C 6 {L*0.3:.1f} -6 {L*0.65:.1f} 2 {L:.1f}", LEAF_DEEP, 2.0,
                     trim_el=trim(0, 0, id=st_trim))]
        sc.key(st_trim, "end", [(0, 0.0, "hold"), (46 + i * 5, 0.0, "outs"), (96 + i * 5, 1.0)])
        n_l = int(L / 26)
        for j in range(n_l):
            f = (j + 0.7) / n_l
            (px, py), ang = point_at(f"M0 0 C 6 {L*0.3:.1f} -6 {L*0.65:.1f} 2 {L:.1f}", f)
            sd = 1 if j % 2 else -1
            lf_, lp_ = leaf(f"Pothos {i}.{j}", px, py, 22, 22, rot=sd * 1.9, light=[LEAF, LEAF_DARK, LEAF_PALE][j % 3],
                            dark=[LEAF_DARK, LEAF_DEEP, LEAF][j % 3], kind="heart", rib=None)
            kids.append(lf_)
            sc.pop(lp_["node"], 50 + i * 5 + f * 46, 64 + i * 5 + f * 46, 0.0, 1.0, "back")
        strands.append(node(f"Pothos strand {i}", *kids, x=195 + x, y=772 - 392 + abs(x) * 0.2, id=sid_))
        sc.sway(sid_, 0.0, 0.035, 420 + 40 * i, ph * 2)
    emb_wrap = node("Emblems", E("ClippingShape", sourceId=clip_src, name="Arch clip"), *emb_els, *strands)
    arch = node("Arch", *stack(
        poly("Arch shadow", ARCH_D, "#05130E", a=0.4, y=14, feather=24),
        shape("Arch rim", *path_el(ARCH_D), stroke(col(CREAM), 10, bind=rim_bind)),
        shape("Arch face", *path_el(ARCH_D), lin_grad([(0, col("#FBF4E2")), (0.7, col("#F6E4CC")), (1, col(CREAM_SHADE))],
                                                      0, -404, 0, 0)),
        shape("Accent halo", ellipse(170, 170), fill(col(CREAM), bind=bind(P("personaColor"), 37)),
              stroke(col(FOREST, 0.12), 2), x=50, y=-300, op=0.55),
        shape("Arch clip source", *path_el(ARCH_D), id=clip_src),
    ), x=195, y=772, id=arch_id)
    sc.key(arch_id, "scaleY", [(0, 0.0, "hold"), (22, 0.0, "back"), (58, 1.0)])
    sc.key(arch_id, "scaleX", [(0, 0.6, "hold"), (22, 0.6, "back"), (58, 1.0)])
    # the persona stage (arch + emblems) sits a little smaller and higher, clear of the controls
    stage_id = ID()
    stage = node("Persona stage", *stack(arch, emb_wrap), x=195 * 0.1, y=716 - 772 * 0.9, sx=0.9, sy=0.9, id=stage_id)
    # anticipation through the motif: a closed paper seed (3D) at the arch's foot swells, cracks and opens
    # into the cradle the arch rises out of
    c3, ci = leaf3d("Cradle shells 3D", 195, 790, pair=1, shape=1, L=210, W=112, fold=0.0, cup=1.0, curl=0.2,
                    wave=0.0, flip=1.45, spread=0.0, gap=0, veins=0.0, glow=0.25, fibre=0.8, ambient=0.64,
                    front="#F6EBCB", back="#E8DAB2", rim="#FFFDF2", glowColor="#FBF0CF", seed=9,
                    halfW=220, top=-280, bottom=40, res=1.6)
    sc.live3d(ci)
    seed_id = ID()
    seed = node("Persona seed", c3, x=0, y=0, id=seed_id)
    sc.key(seed_id, "y", [(0, 40, "hold"), (2, 40, "outs"), (14, 0.0)])
    sc.k3(ci, "L", [(0, 120, "hold"), (2, 120, "backs"), (16, 150, "io"), (24, 140, "outs"), (40, 196)])
    sc.k3(ci, "W", [(0, 64, "hold"), (2, 64, "backs"), (16, 82, "io"), (24, 76, "outs"), (40, 112)])
    sc.k3(ci, "flip", [(0, 1.45, "hold"), (22, 1.45, "back"), (52, 0.5)])
    sc.k3(ci, "spread", [(0, 0.0, "hold"), (22, 0.0, "back"), (54, 0.62)])
    sc.k3(ci, "gap", [(0, 0.0, "hold"), (22, 0.0, "outs"), (50, 40.0)])
    sc.idle.key(ci["spread"], "propertyValue", [(0, 0.62, "sine"), (200, 0.635, "sine"), (400, 0.62)])
    # foliage spilling over the cradle's lip
    spill = []
    for i, (x, y, L, Wd, r, c1, c2, kind) in enumerate([(86, 790, 96, 50, -1.05, LEAF, LEAF_DARK, "leaf"),
                                                        (304, 792, 104, 52, 1.1, LEAF_DARK, LEAF_DEEP, "leaf"),
                                                        (120, 800, 80, 74, -0.5, FOREST_PALE, FOREST_SOFT, "heart"),
                                                        (272, 802, 78, 70, 0.55, LEAF_PALE, LEAF, "heart")]):
        n, p = leaf(f"Spill leaf {i}", x, y, L, Wd, rot=r, light=c1, dark=c2, kind=kind, rib_a=0.35, morph=True)
        spill.append(n)
        sc.unfurl(p, 52 + i * 6, 84 + i * 6, rot=r)
        sc.sway(p["node"], r, 0.03, 360, i * 80)
    sparkles = []
    for i, (x, y, s) in enumerate([(338, 404, 16), (356, 446, 10), (48, 470, 12)]):
        spid = ID()
        sparkles.append(shape(f"Sparkle {i}", E("Star", width=float(s), height=float(s), points=4, innerRadius=0.3,
                                                name="Star"), fill(col(APRICOT)), x=x, y=y, id=spid, sx=0.0, sy=0.0))
        sc.pop(spid, 70 + i * 8, 86 + i * 8, 0.0, 1.0, "back")
        sc.idle.key(spid, "scaleX", [(0, 1.0, "sine"), (90 + i * 30, 0.6, "sine"), (360, 1.0)])
        sc.idle.key(spid, "scaleY", [(0, 1.0, "sine"), (90 + i * 30, 0.6, "sine"), (360, 1.0)])
    back = []
    for i, (x, y, L, r) in enumerate([(-10, 900, 300, 0.45), (400, 900, 300, -0.45)]):
        n, p = leaf(f"Frame leaf {i}", x, y, L, L * 0.5, rot=r, light=FOREST_SOFT, dark=FOREST_MID, rib_a=0.08)
        back.append(n)
        sc.sway(p["node"], r, 0.03, 400, i * 200)
    content = stack(bg_rect(FOREST),
                    shape("Glow", ellipse(520, 520), rad_grad([(0, col(LEAF, 0.2)), (1, col(LEAF, 0))], 0, 0, 260),
                          x=195, y=560),
                    back, stage, seed, spill, sparkles, copy)
    sc.settle.append((col_id, "y", 8.0))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    sc.persona = pa
    sc.emb_wrap = emb_wrap
    sc.stage = stage_id
    return sc, root


# ===================================================================== share card (component artboard)
CARD_W, CARD_H = 330, 476


def has_stats_conv():
    toks = [tF("min"), tV(1), tSep(), tIn()]
    for i in range(3, 9):
        toks += [tOp("+"), tV(bind_el=bind(P(f"showScreen{i}"), 777, c_b2n()))]
    toks += [tC()]
    f = CV.add("hasstats", formula("Any metric scene visible", toks))
    return CV.group("hasstats", [c_b2n(), f], "Has stats")


def no_stats_conv():
    inv = CV.add("inv", formula("1 - x", [tV(1), tOp("-"), tIn()]))
    return CV.group("nostats", [has_stats_conv(), inv], "Has no stats")


def share_card():
    """330x476 collectible card. Separate artboard so the host can snapshot it without chrome."""
    ab = ID()
    st = E("LayoutComponentStyle", name="Card style", id=ID())
    cardbg_id = ID()
    pieces = []
    anim = Anim("Card assemble", 96)
    stat_cells = []
    stats = [(2, "careMoments"), (3, "plantsNurtured"), (4, "newLeaves"), (5, "cuttingsRooted"), (6, "careStreak")]
    for i, (k, m) in enumerate(stats):
        cx = 22 + (i % 2) * 150
        cy = 196 + (i // 2) * 84
        cell_id = ID()
        num = hero_number(10, m, 0, 0, 140, size=38, color=CREAM, align="left", wght=560, shrink=(0.12, 0.1, 0.1))
        unit = text("Unit", [("unit", P(f"screen{k}Unit"))], font="dm", size=12, color=CREAM, wght=500, ls=0.6, x=2,
                    y=44, w=132, h=16, sizing="fixed", op=0.78, overflow="ellipsis", wrap=False)
        stat_cells.append(node(f"Stat {m}", num, unit, x=cx, y=cy, id=cell_id))
        anim.key(cell_id, "opacity", [(0, 0.0, "hold"), (24 + i * 7, 0.0, "outs"), (44 + i * 7, 1.0)])
        anim.key(cell_id, "y", [(0, cy + 22, "hold"), (24 + i * 7, cy + 22, "outs"), (48 + i * 7, cy)])
    motif_id = ID()
    m_leaves = []
    for j, (L, r, c1, c2) in enumerate([(54, -0.6, LEAF, LEAF_DARK), (62, 0.5, LEAF_PALE, LEAF), (70, 0.0, LEAF_DARK, LEAF_DEEP),
                                        (40, 1.2, APRICOT, APRICOT_DARK)]):
        lf, lpp = leaf(f"Motif leaf {j}", 0, -20, L, L * 0.6, rot=r, light=c1, dark=c2)
        m_leaves.append(lf)
        anim.key(lpp["node"], "scaleX", [(0, 0.0, "hold"), (52 + j * 5, 0.0, "back"), (76 + j * 5, 1.0)])
        anim.key(lpp["node"], "scaleY", [(0, 0.0, "hold"), (52 + j * 5, 0.0, "back"), (76 + j * 5, 1.0)])
    motif = node("Motif", *stack(
        *m_leaves,
        node("SL", poly("F", "M0 0 C-30 0 -40 -26 -38 -50 C-36 -76 -18 -92 0 -94 L0 0 Z", CREAM), rot=-0.75, sx=0.6, sy=0.6),
        node("SR", poly("F", "M0 0 C30 0 40 -26 38 -50 C36 -76 18 -92 0 -94 L0 0 Z", CREAM_SHADE), rot=0.7, sx=0.6, sy=0.6),
    ), x=246, y=436, id=motif_id)
    grid_id = ID()
    grid = node("Stats", *stat_cells, motif, id=grid_id)
    empty_id = ID()
    empty = node("Empty state",
                 text("Empty headline", [("Every story starts somewhere.", P("emptyHeadline"))], font="fr", size=30,
                      color=CREAM, wght=560, soft=60, lh=33, x=22, y=200, w=286, align="left"),
                 text("Empty support", [("Your next chapter is waiting.", P("emptySupport"))], font="dm", size=15,
                      color=CREAM, x=22, y=300, w=286, op=0.8),
                 node("Small motif",
                      leaf("E0", 0, -10, 46, 28, rot=-0.3)[0], leaf("E1", 0, -10, 40, 24, rot=0.5, light=LEAF_PALE)[0],
                      node("SL", poly("F", "M0 0 C-30 0 -40 -26 -38 -50 C-36 -76 -18 -92 0 -94 L0 0 Z", CREAM), rot=-0.7,
                           sx=0.5, sy=0.5),
                      node("SR", poly("F", "M0 0 C30 0 40 -26 38 -50 C36 -76 18 -92 0 -94 L0 0 Z", CREAM_SHADE), rot=0.66,
                           sx=0.5, sy=0.5),
                      x=250, y=430),
                 id=empty_id)
    empty.kids.append(shape("Empty panel", rect(CARD_W - 24, 300, 18, 0, 0), fill(col(FOREST)), x=12, y=168))
    for i in range(2, 9):
        empty = node(f"Only if scene {i} hidden", empty, bind(P(f"showScreen{i}"), 18, CV.group("notb2n", [c_not(), c_b2n()], "Not as number")))
    head_id = ID()
    name_line = text("Name", [("Alex", P("userName"))], font="fr", size=20, color=APRICOT, wght=520, soft=80, x=22, y=60,
                     w=286, h=26, sizing="fixed", overflow="ellipsis", wrap=False)
    name_line.add(bind(P("shareIncludeName"), 18, c_b2n()))
    persona_id = ID()
    persona = node("Persona line",
                   text("Persona label", [("Your personal style", P("personaLabel"))], font="dm", size=11, color=CREAM,
                        wght=500, ls=2.0, x=22, y=98, w=286, op=0.7, wrap=False, overflow="ellipsis"),
                   text("Persona name", [("Canopy Keeper", P("personaName"))], font="fr", size=30, color=CREAM, wght=600,
                        soft=80, wonk=1, x=22, y=116, w=286, wrap=False, overflow="ellipsis"),
                   id=persona_id)
    persona.add(bind(P("showScreen9"), 18, c_b2n()))
    period = text("Period", [("January 1–December 31, 2026", P("periodLabel"))], font="dm", size=11, color=CREAM,
                  wght=500, ls=1.0, x=22, y=CARD_H - 30, w=200, op=0.7)
    period.add(bind(P("shareIncludeSensitiveValues"), 18, c_b2n()))
    header = node("Header",
                  text("Wordmark", ["Sprig"], font="fr", size=28, color=CREAM, wght=620, soft=100, wonk=1, x=22, y=18),
                  leaf("Mark leaf", 98, 40, 14, 9, rot=0.7, light=LEAF, dark=LEAF_DARK, rib=None)[0],
                  text("Year", [("2026", P("year"), CV.group("yeartxt", [c_tostr()], "Year text"))], font="dm",
                       size=13, color=CREAM, wght=600, ls=2.2, x=CARD_W - 22, y=28, ox=1.0),
                  name_line, id=head_id)
    anim.key(head_id, "opacity", [(0, 0.0, "hold"), (10, 0.0, "outs"), (28, 1.0)])
    anim.key(persona_id, "x", [(0, -30, "hold"), (14, -30, "out"), (40, 0)])
    anim.key(motif_id, "rotation", [(0, -0.4, "hold"), (50, -0.4, "back"), (80, 0.0)])
    bg = node("Card", *stack(
              shape("Card face", rect(CARD_W, CARD_H, 28, 0, 0), lin_grad([(0, col(FOREST_SOFT)), (1, col(FOREST))],
                                                                          0, 0, 0, CARD_H)),
              shape("Inner rule", rect(CARD_W - 20, CARD_H - 20, 22, 0, 0), stroke(col(CREAM, 0.18), 1.2), x=10, y=10),
              poly("Paper fold", f"M0 {CARD_H*0.62} C 120 {CARD_H*0.55} 220 {CARD_H*0.7} {CARD_W} {CARD_H*0.6} "
                                 f"L{CARD_W} {CARD_H-28} C {CARD_W} {CARD_H-12} {CARD_W-12} {CARD_H} {CARD_W-28} {CARD_H} "
                                 f"L28 {CARD_H} C 12 {CARD_H} 0 {CARD_H-12} 0 {CARD_H-28} Z", FOREST_MID, a=0.7)),
              id=cardbg_id)
    final = Anim("Card static", 12)
    for (obj, p), keys in anim.tracks.items():
        final.key(obj, p, [(0, keys[-1][1], "hold")])
    hidden = Anim("Card hidden", 1)
    for (obj, p), keys in anim.tracks.items():
        hidden.key(obj, p, [(0, keys[0][1], "hold")])
    empty_anim = Anim("Card hold", 44)
    # card state machine (runs inside the nested placement and when the host renders the card alone)
    cur = lambda v, op="equal": cond_num("currentScreen", v, op)
    rm = lambda v: cond_bool("reducedMotion", v)
    sH, sA, sF, sL = ID(), ID(), ID(), ID()
    sm_id, layer_id = ID(), ID()
    layer = E("StateMachineLayer",
              E("AnyState", x=500.0, y=-150.0), E("ExitState", x=700.0, y=-150.0),
              E("EntryState", E("StateTransition", stateToId=sH), x=0.0, y=0.0),
              E("AnimationState", trans(sF, [cur(10), rm(True)]), trans(sA, [cur(10)]), x=160.0, y=0.0,
                animationId=hidden.id, id=sH),
              E("AnimationState", trans(sL, [cur(10, "notEqual")]), x=360.0, y=-90.0, animationId=anim.id, id=sA),
              E("AnimationState", trans(sL, [cur(10, "notEqual")]), x=360.0, y=90.0, animationId=final.id, id=sF),
              E("AnimationState", trans(sH, [], exit_pct=100), trans(sA, [cur(10), rm(False)]),
                trans(sF, [cur(10), rm(True)]),
                x=560.0, y=0.0, animationId=empty_anim.id, id=sL),
              name="Assemble", id=layer_id)
    sm = E("StateMachine", layer, name="Card machine", id=sm_id)
    art = E("Artboard", st, sm, *stack(bg, grid, empty, persona, header, period),
            anim.el(), final.el(), hidden.el(), empty_anim.el(),
            isComponent=True, defaultStateMachineId=sm_id, viewModelId=VMID, width=float(CARD_W),
            height=float(CARD_H), styleId=st.id, x=float(W + 120), y=0.0, name="ShareCard", id=ab)
    # fix draw order: style + machine first are non-drawables; keep
    asset = E("ComponentAsset", artboardId=ab, name="ShareCard")
    return art, asset, ab, sm_id


# ---------------------------------------------------------------- condition helpers (used by machines)

def cond_num(name, v, op="equal"):
    key = 636
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator",
               E("BindablePropertyNumber", bind(P(name), key))),
             E("TransitionValueNumberComparator", value=float(v)), opValue=op)


def cond_bool(name, v):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator",
               E("BindablePropertyBoolean", bind(P(name), 634))),
             E("TransitionValueBooleanComparator", value=bool(v)))


def cond_trig(name):
    return E("TransitionViewModelCondition",
             E("TransitionPropertyViewModelComparator",
               E("BindablePropertyTrigger", bind(P(name), 686))),
             E("TransitionValueTriggerComparator"))


def trans(to, conds, dur=0, exit_pct=None, exit_ms=None, dur_bind=None, interp=None, early=False):
    t = E("StateTransition", *conds, stateToId=to, duration=int(dur) if dur else None,
          enableExitTime=True if (exit_pct is not None or exit_ms is not None) else None,
          exitTimeIsPercetange=True if exit_pct is not None else None,
          exitTime=int(exit_pct if exit_pct is not None else exit_ms) if (exit_pct is not None or exit_ms is not None) else None,
          enableEarlyExit=True if early else None)
    if dur_bind is not None:
        t.kids.insert(0, dur_bind)
    if interp == "elastic":
        t.attrs["interpolationType"] = "elastic"
        t.add(E("ElasticInterpolator", easingValue="easeOut", amplitude=0.9, period=0.35))
    elif interp:
        t.attrs["interpolationType"] = "cubic"
        x1, y1, x2, y2 = EASES[interp]
        t.add(E("CubicEaseInterpolator", x1=x1, y1=y1, x2=x2, y2=y2))
    return t


def scene10(card_ab, card_sm):
    sc = Scene(10, CREAM, light=True, dur=110)
    head_id, sup_id, col_id = ID(), ID(), ID()
    rg, rid = word_reveal()
    # the headline is width-capped so English breaks after the first sentence ("A little year. / A lot of you.");
    # the support line keeps the full column so it never orphans a word
    copy = column("Summary copy", 30, 100, 330, [
        E("LayoutComponent", hst := lstyle(layoutWidthScaleType="fixed", layoutHeightScaleType="hug"),
          text("Headline", [("A little year. A lot of you.", P("summaryHeadline"))], font="fr", size=30, color=FOREST,
               wght=560, soft=60, lh=32, align="center", lp=lp(), modifiers=[rg], id=head_id),
          width=192.0, height=10.0, styleId=hst.id, name="Headline box", id=ID()),
        text("Support", [("Take a piece of your year with you.", P("summarySupport"))], font="dm", size=17,
             color=FOREST, lh=23, align="center", lp=lp(), op=0.8, id=sup_id),
    ], gap=8, align="topCenter", id=col_id)
    reveal_keys(sc.ef, rid, 40, 80)
    sc.key(sup_id, "opacity", [(0, 0.0, "hold"), (70, 0.0, "outs"), (94, 0.8)])
    card_id = ID()
    card = E("NestedArtboard", E("NestedStateMachine", animationId=card_sm, name="Card machine"),
             artboardId=card_ab, x=195 - CARD_W * 0.47, y=256.0, scaleX=0.94, scaleY=0.94, name="Share card", id=card_id)
    sc.key(card_id, "y", [(0, 410, "hold"), (8, 410, "back"), (54, 256)])
    sc.key(card_id, "rotation", [(0, -0.08, "hold"), (8, -0.08, "back"), (60, 0.0)])
    sc.idle.key(card_id, "rotation", [(0, 0.0, "sine"), (180, 0.006, "sine"), (360, 0.0)])
    shadow_id = ID()
    card_shadow = shape("Card shadow", rect(CARD_W - 20, CARD_H - 30, 30), fill(col("#3A3420", 0.35), feather=22),
                        x=195, y=256 + CARD_H * 0.47 + 18, sx=0.94, sy=0.94, id=shadow_id)
    sc.key(shadow_id, "opacity", [(0, 0.0, "hold"), (20, 0.0, "outs"), (60, 1.0)])
    deco = []
    for i, (x, y, L, r, c1, c2) in enumerate([(-4, 300, 160, 1.1, LEAF, LEAF_DARK), (396, 640, 170, -1.1, LEAF_DARK, LEAF_DEEP),
                                              (14, 690, 120, 0.7, APRICOT, APRICOT_DARK)]):
        n, p = leaf(f"Summary leaf {i}", x, y, L, L * 0.55, rot=r, light=c1, dark=c2, morph=True)
        deco.append(n)
        sc.unfurl(p, 20 + i * 10, 50 + i * 10, rot=r)
        sc.sway(p["node"], r, 0.03, 360, i * 100)
    content = stack(bg_rect(CREAM), deco, card_shadow, card, copy)
    sc.settle.append((card_id, "y", 18.0))
    root = build_scene_root(sc, content)
    scene_wipe_in(sc)
    return sc, root
