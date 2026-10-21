"""ShareCard: a separate, chrome-free component artboard.

It is nested into the summary scene (and assembled there through a
NestedRemapAnimation), and a host can also instantiate it on its own, bind the
same UserRecap instance, and snapshot it -- its authored pose is the settled
card, so a standalone render needs no animation at all.
"""
from __future__ import annotations

import motif as MF
from rml import E, Anim, argb, bind, child, ellipse, fill, node, poly, rect, shape, smooth_path, smooth_vertices, solid, stroke
from gen_kiln import CHAR, CLAY, PORC, ULTRA, settle

CW, CH = 300, 440


def build(g):
    S = lambda el, **kw: [settle(el, k, v) for k, v in kw.items()] and el  # noqa: E731
    st = g.style(name="Card Style")
    ab = E("Artboard", {"x": 500.0, "y": 0.0, "width": float(CW), "height": float(CH), "clip": True,
                        "isComponent": True, "styleId": st.id, "viewModelId": g.M.vmid,
                        "viewModelInstanceId": g.M.default_instance, "name": "ShareCard"}, st)
    ab.id  # noqa: B018
    a = Anim("Assemble", 60)

    # background slab with a clay plinth sweep
    bg = shape("Card Body", CW / 2, CH / 2, rect(CW, CH, 24), fill("332D2A"))
    edge = shape("Card Edge", CW / 2, CH / 2, rect(CW - 10, CH - 10, 19), stroke(PORC, 1.0, alpha=0.08))
    rule = shape("Card Rule", 0, 0, poly([(24, 196), (CW - 24, 196)], closed=False), stroke(PORC, 1.0, alpha=0.14))
    sweep = S(shape("Clay Sweep", 270, 540, ellipse(420, 300), fill(CLAY, alpha=0.9)), scaleX=1.0, scaleY=1.0)
    sweep2 = shape("Ultramarine Sweep", -60, 520, ellipse(260, 210), fill(ULTRA, alpha=0.85))
    deco = node("Card Decor", 0, 0, E("ClippingShape", {"sourceId": bg.id, "name": "Clip"}), sweep2, sweep)

    word = S(g.text("Card Wordmark", g.serif_style(28, PORC), "Kiln", reveal=False, layout=False, x=24, y=18),
             y=18.0, opacity=1.0)
    yst = g.sans_style(13, PORC, 600, spacing=0.6)
    child(child(yst, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.75)
    year = g.text("Card Year", yst, "2026", prop="year", conv=g.fmt(0, 0, "Card Year"), reveal=False, layout=False,
                  x=276, y=28, origin=(1.0, 0.0))
    nst = g.sans_style(13, PORC, 600)
    child(child(nst, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.8)
    name = g.text("Card Name", nst, "Alex", prop="userName", reveal=False, layout=False, x=24, y=58, nowrap=True,
                  ellipsis=True)
    name.attrs["width"] = 170.0
    name.attrs["height"] = 20.0
    name.attrs["sizingValue"] = "fixed"
    name.add(bind(g.p("_namePublic"), 18))

    # persona block (hidden with the persona scene)
    pst = g.abs_style(top=88, left=24, flexDirectionValue="column", layoutWidthScaleType="fixed",
                      layoutHeightScaleType="hug", gapVertical=4.0, gapVerticalUnitsValue="points", name="Persona Style")
    lst = g.sans_style(11, PORC, 600, spacing=0.8)
    child(child(lst, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.6)
    plabel = g.text("Card Persona Label", lst, "Your personal style", prop="personaLabel", reveal=False)
    ptitle = g.text("Card Persona", g.serif_style(26, PORC, lh=28), "Glaze Alchemist", prop="personaName", reveal=False)
    bar_st = g.style(layoutWidthScaleType="fixed", layoutHeightScaleType="fixed", cornerRadiusTL=1.5, name="Bar Style")
    bcol = solid(ULTRA, name="Persona Accent")
    bcol.add(bind(g.p("personaColor"), 37))
    bar = g.box("Card Accent", bar_st, E("Fill", {"name": "Fill"}, bcol),
                E("Stroke", {"thickness": 1.0, "name": "Edge"}, solid(PORC, alpha=0.4)), w=36, h=3)
    persona = g.box("Card Persona Block", pst, plabel, ptitle, bar, w=176, h=80)
    persona.add(bind(g.p("_seg9"), 18, g.invert.id))
    S(persona, y=0.0)

    # the collectible's piece: the same 3D vessel, static, on a small carved plinth under a spotlight
    import v3d
    piece = v3d.V3D(g, "Card Vessel 3D", v3d.look("vessel", body="EFE6D8", dip=0.16, flow=0.92, bandW=0.36,
                                                   sway=0.42, drip=0.8, yaw=0.15, seed=1.0, tilt=0.22),
                    keyed=False, frame=dict(halfW=150.0, top=-366.0, bottom=34.0, res=1.0, msaa=1.0))
    spot = shape("Card Spotlight", 0, -120, ellipse(300, 300), fill("F2ECE2", alpha=0.10, feather=60))
    fpts, tpts = MF.plinth_points(220, 120, 6, 18)
    mplinth = node("Mini Plinth", 0, 0, shape("Mini Plinth Top", 0, 0, poly(tpts), fill("4A403A")),
                   shape("Mini Plinth Front", 0, 0, poly(fpts), fill("231F1D")),
                   shape("Mini Plinth Edge", 0, 0, poly(fpts[:3], closed=False), stroke("FFFFFF", 2.0, alpha=0.12)))
    mshadow = shape("Mini Shadow", 0, -6, ellipse(120, 18), fill("000000", alpha=0.35, feather=10))
    piece_node = node("Mini Piece", 0, -9, piece.el)
    mini = S(node("Mini Motif", 232, 172, spot, piece_node, mshadow, mplinth, scaleX=0.38, scaleY=0.38),
             y=172.0, opacity=1.0)

    # stats: five existing UserRecap properties, no duplicated summary fields
    sst = g.abs_style(top=210, left=24, right=24, flexDirectionValue="row", flexWrapValue="wrap",
                      layoutHeightScaleType="hug", gapHorizontal=16.0, gapHorizontalUnitsValue="points",
                      gapVertical=6.0, gapVerticalUnitsValue="points", name="Stats Style")
    sst.add(bind(g.p("_isEmpty"), 596))
    stats = g.box("Card Stats", sst, w=252, h=200)
    items = []
    for scr, prop, unit_prop, lit, dec in ((2, "piecesMade", "screen2Unit", "pieces made", 0),
                                           (3, "studioHours", "screen3Unit", "studio hours", 0),
                                           (4, "glazeTests", "screen4Unit", "glaze tests", 0),
                                           (5, "firings", "screen5Unit", "firings", 0),
                                           (6, "clayReclaimedKg", "screen6Unit", "kg clay reclaimed", 1)):
        ist = g.style(layoutWidthScaleType="fixed", layoutHeightScaleType="hug", flexDirectionValue="column",
                      gapVertical=0.0, name=f"Stat {scr} Style")
        ist.add(bind(g.p(f"_seg{scr}"), 596))
        num = g.text(f"Card Stat {scr}", g.serif_style(30, PORC, lh=34), "0", prop=prop,
                     conv=g.fmt(dec, 1, f"Card Fmt {scr}"), reveal=False, width="hug", nowrap=True)
        ust = g.sans_style(11, PORC, 600, lh=14)
        child(child(ust, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.68)
        un = g.text(f"Card Unit {scr}", ust, lit, prop=unit_prop, reveal=False, nowrap=True, ellipsis=True, height=14)
        kids = [num]
        if prop == "studioHours":
            # sensitive: shown only when the host opts in
            child(num, "LayoutParticipant").add(bind(g.p("_hoursPublic"), 596, g.invert.id))
            pst2 = g.serif_style(22, PORC, lh=34)
            child(child(pst2, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.55)
            priv = g.text("Card Private", pst2, "Private", prop="privateValueLabel", reveal=False, width="hug",
                          nowrap=True)
            child(priv, "LayoutParticipant").add(bind(g.p("_hoursPublic"), 596))
            kids.append(priv)
        item = g.box(f"Card Item {scr}", ist, *kids, un, w=110, h=50)
        S(item, opacity=1.0, y=0.0)
        items.append(item)
        stats.add(item)

    est = g.serif_style(24, PORC, lh=28)
    empty = g.text("Card Empty", est, "Your next chapter is waiting.", prop="emptySupport", reveal=False,
                   layout=False, x=24, y=250, width=200)
    empty.add(bind(g.p("_isEmpty"), 18))
    per_st = g.sans_style(11, PORC, 500)
    child(child(per_st, "Fill"), "SolidColor").attrs["colorValue"] = argb(PORC, 0.6)
    period = g.text("Card Period", per_st, "January 1–December 31, 2026", prop="periodLabel", reveal=False,
                    layout=False, x=24, y=410, width=200)
    rules_st = g.abs_style(top=0, bottom=0, left=0, right=0, name="Rules Style")
    rules = g.box("Card Rules", rules_st, E("ScriptedLayout", {"scriptAssetId": g.card_script.id, "name": "Card Rules"}),
                  w=CW, h=CH)
    ab.add(rules, word, year, name, persona, stats, empty, period, mini, rule, edge, deco, bg)

    # assembly timeline (driven from the summary scene through a remap)
    a.k(word, "y", (0, 6.0, "hold"), (2, 6.0, "out"), (20, 18.0, "hold"))
    a.k(word, "opacity", (0, 0.0, "hold"), (2, 0.0, "out"), (16, 1.0, "hold"))
    a.k(persona, "y", (0, 16.0, "hold"), (10, 16.0, "out"), (30, 0.0, "hold"))
    for i, it in enumerate(items):
        f0 = 20 + i * 5
        a.k(it, "y", (0, 22.0, "hold"), (f0, 22.0, "back"), (f0 + 16, 0.0, "hold"))
        a.k(it, "opacity", (0, 0.0, "hold"), (f0, 0.0, "out"), (f0 + 12, 1.0, "hold"))
    a.k(mini, "y", (0, 120.0, "hold"), (24, 120.0, "back"), (50, 172.0, "hold"))
    a.k(mini, "opacity", (0, 0.0, "hold"), (24, 0.0, "out"), (34, 1.0, "hold"))
    a.k(sweep, "scaleX", (0, 0.3, "hold"), (0, 0.3, "out"), (40, 1.0, "hold"))
    a.k(sweep, "scaleY", (0, 0.3, "hold"), (0, 0.3, "out"), (40, 1.0, "hold"))

    sm = E("StateMachine", {"name": "Card"})
    ab.attrs["defaultStateMachineId"] = sm.id
    sm.add(E("StateMachineLayer", {"name": "Static"}, E("AnyState", {"x": 0.0, "y": -120.0}),
             E("ExitState", {"x": 300.0, "y": -120.0}), E("EntryState", {"x": 0.0, "y": 0.0})))
    ab.add(sm)
    ab.add(a.render())
    return ab, a
