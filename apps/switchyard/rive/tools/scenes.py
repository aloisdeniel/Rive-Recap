"""Scene art + choreography for the ten Switchyard screens.

Coordinates are in the 390 x 844 master artboard. The story window is
y 82..740 (between the header and dock ticket bands).
"""
from __future__ import annotations

import math

from rml import *  # noqa: F401,F403


def build(g):
    globals().update({k: v for k, v in g.items() if not k.startswith("__")})
    for fn in (scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8, scene9, scene10):
        sc = fn()
        SCENES[sc.n] = sc


NUM_PROP = {2: "journeys", 3: "distanceKm", 4: "routesExplored", 5: "stationsVisited", 6: "ferryTrips",
            7: "weekendOutings", 8: "activeMonths"}


# ---------------------------------------------------------------- helpers
def station(x, y, d=18.0, name="Station", fillc=WHITE, line=BLACK, lw=4.0):
    return circle(float(x), float(y), d, fillc, name=name, line=line, lw=lw)


def interchange(x, y, d=30.0, name="Interchange"):
    return circle(float(x), float(y), d, WHITE, name=name, line=BLACK, lw=6.0)


def draw(a, trim, f0, f1, ease=EIO):
    a.key(trim, "end", (0, 0.0, "hold"), (f0, 0.0, ease), (f1, 1.0, "hold"))


def pop(a, obj, f, dur=16, frm=0.0):
    a.key(obj, "scaleX", (0, frm, "hold"), (f, frm, POP), (f + dur, 1.0, "hold"))
    a.key(obj, "scaleY", (0, frm, "hold"), (f, frm, POP), (f + dur, 1.0, "hold"))


def fade_in(a, obj, f0, f1, ease=SOFT):
    a.key(obj, "opacity", (0, 0.0, "hold"), (f0, 0.0, ease), (f1, 1.0, "hold"))


def slide(a, obj, prop, frm, f0, f1, ease=EO):
    a.key(obj, prop, (0, float(frm), "hold"), (f0, float(frm), ease), (f1, rest_value(obj, prop), "hold"))


def stations_on(a, pts, stations, f0, f1):
    """Pop each station as the drawing line reaches it."""
    total = polyline_length(pts)
    for st in stations:
        sx, sy = st.attrs["x"], st.attrs["y"]
        best, acc = 0.0, 0.0
        bestd = 1e9
        for i in range(len(pts) - 1):
            ax, ay = pts[i][:2]
            bx, by = pts[i + 1][:2]
            seg = math.dist((ax, ay), (bx, by))
            for k in range(21):
                u = k / 20
                px, py = ax + (bx - ax) * u, ay + (by - ay) * u
                d = math.dist((px, py), (sx, sy))
                if d < bestd:
                    bestd, best = d, (acc + seg * u) / total
            acc += seg
        pop(a, st, int(f0 + (f1 - f0) * best), 14)


def metric_copy(sc, n, num_box, num_size, num_color, unit_box, head_box, head_size, sup_box,
                ink=BLACK, sup_color=None, num_align="center", unit_align="center", head_lines=3,
                unit_color=None):
    x, y, w, h = num_box
    hero = text(x, y, w, [("0", NUM_PROP[n], COUNT_CONV[n])],
                num_size, num_color, display=True, align=num_align, h=h, overflow="fitFontSize",
                valign="middle", wrap="noWrap", name="Hero number", lh=num_size * 1.0)
    sem = E("SemanticData", bind(NUM_PROP[n], 983, CONV_FMT), bind(f"screen{n}Unit", 984),
            role="text", isHidden=n != 2, name="Semantics (full exact value)")
    hero.children.insert(0, sem)
    sc.sems.append(sem)
    hero_roll = reveal_modifier(hero, units="characters", dy=-46.0)
    ux, uy, uw = unit_box
    unit = text(ux, uy, uw, [(SAMPLE[f"screen{n}Unit"], f"screen{n}Unit")], 22, unit_color or ink, weight=600,
                align=unit_align, h=56, overflow="ellipsis", name="Unit", lh=27)
    unit_rng = reveal_modifier(unit, units="words", dy=14.0)
    hx, hy, hw = head_box
    head = text(hx, hy, hw, [(SAMPLE[f"screen{n}Headline"], f"screen{n}Headline")], head_size, ink, display=True,
                h=head_size * 1.06 * head_lines + 4, overflow="fitFontSize", lh=head_size * 1.06, name="Headline")
    head_rng = reveal_modifier(head, units="words", dy=30.0)
    sx, sy, sw = sup_box
    sup = text(sx, sy, sw, [(SAMPLE[f"screen{n}Support"], f"screen{n}Support")], 17, sup_color or ink,
               h=46, overflow="ellipsis", lh=22, name="Support")
    sup_rng = reveal_modifier(sup, units="words", dy=12.0)
    copy = node("Copy", head, sup)
    heroes = node("Hero", hero, unit)
    sc.copy_bits = dict(hero=hero, hero_roll=hero_roll, unit_rng=unit_rng, head_rng=head_rng, sup_rng=sup_rng,
                        head=head, heroes=heroes)
    return heroes, copy


def standard_copy_motion(sc, ef, eb, hero_at=16):
    b = sc.copy_bits
    key_reveal(ef, b["hero_roll"], hero_at, hero_at + 26, EO)
    ef.key(b["hero"], "scaleX", (0, 0.86, "hold"), (hero_at, 0.86, EO), (hero_at + 40, 1.0, "hold"))
    ef.key(b["hero"], "scaleY", (0, 0.86, "hold"), (hero_at, 0.86, EO), (hero_at + 40, 1.0, "hold"))
    key_reveal(ef, b["unit_rng"], 48, 72)
    key_reveal(ef, b["head_rng"], 72, 100)
    key_reveal(ef, b["sup_rng"], 86, 108)
    content_enter_back(sc, eb)
    key_reveal(eb, b["head_rng"], 6, 34)
    key_reveal(eb, b["sup_rng"], 14, 40)


def finish(sc, ef_dur=110):
    """Common exit timelines."""
    xf = sc.anim("ExitFwd", 44)
    content_exit_fwd(sc, xf)
    xb = sc.anim("ExitBack", 40)
    motif_exit_back(sc, xb)
    return xf, xb


# ======================================================================
# 1. Invitation
# ======================================================================
def scene1():
    sc = Scene(1, (195, 292), WHITE)
    ef = sc.anim("EnterFwd", 120)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 300, "loop")

    red = [(-20, 202), (70, 202), (122, 150), (300, 150), (346, 104), (410, 104)]
    yel = [(-20, 410), (96, 410), (136, 450), (262, 450), (302, 410), (410, 410)]
    blu = [(-20, 150), (22, 192), (22, 420), (-20, 462)]
    blk = [(410, 236), (368, 236), (368, 430), (410, 472)]
    lines = []
    for pts, col, nm in ((red, RED, "Red line"), (yel, YEL, "Yellow line"), (blu, BLUE, "Blue line"),
                         (blk, BLACK, "Black line")):
        shp, tr = route(pts, col, 14, name=nm, radius=30)
        lines.append((shp, tr, pts))
    sts = [station(300, 150), station(22, 300), station(368, 330), station(136, 450), station(262, 450)]
    rings = [interchange(122, 150, name="Interchange A"), interchange(22, 410, name="Interchange B"),
             interchange(368, 410, name="Interchange C")]
    year = text(30, 228, 330, [("2026", "year", CONV_YEAR)], 118, BLACK, display=True, h=128, align="center",
                overflow="fitFontSize", valign="middle", wrap="noWrap", name="Oversized year", lh=118)
    year_roll = reveal_modifier(year, units="characters", dy=-60.0)
    chip = text(24, 92, 342, [(SAMPLE["periodLabel"], "periodLabel")], 13, WHITE, weight=600, h=20,
                overflow="ellipsis", wrap="noWrap", name="Period ticket")
    chip.children[0].add(E("TextStyleBackground", E("Fill", solid(BLACK), name="Ticket ink"), cornerRadius=3.0,
                           name="Ticket"))
    chip_holder = node("Period chip", chip, x=0.0)
    # big wordmark lockup revealed through the motif
    lock_text = text(70, 474, 300, ["Switchyard"], 44, BLACK, display=True, name="Wordmark lockup text",
                     wrap="noWrap")
    lock_rng = reveal_modifier(lock_text, units="characters", dy=0.0)
    lock_ring = circle(44.0, 502.0, 40.0, WHITE, name="Lockup ring", line=BLACK, lw=8.0)
    lock_stub, lock_trim = route([(-20, 502), (40, 502)], RED, 14, name="Lockup route", radius=0)
    lockup = node("Wordmark lockup", lock_text, lock_ring, lock_stub)
    greet = text(24, 560, 342, [(SAMPLE.get("greetingLabel", "Hi,"), "greetingLabel"), " ",
                                (SAMPLE["userName"], "userName")], 20, BLACK, weight=600, h=26,
                 overflow="ellipsis", wrap="noWrap", name="Greeting")
    greet_rng = reveal_modifier(greet, units="words", dy=12.0)
    head = text(24, 592, 342, [(SAMPLE["introHeadline"], "introHeadline")], 32, BLACK, display=True,
                h=72, overflow="fitFontSize", lh=34, name="Intro headline")
    head_rng = reveal_modifier(head, units="words", dy=28.0)
    sup = text(24, 672, 342, [(SAMPLE["introSupport"], "introSupport")], 17, BLACK, h=46, overflow="ellipsis",
               lh=22, name="Intro support")
    sup_rng = reveal_modifier(sup, units="words", dy=12.0)
    idle_dot = circle(-20.0, 202.0, 14.0, WHITE, name="Idle rider", line=RED, lw=4.0, opacity=0.0)
    sc.greeting = greet
    sc.add(node("Copy", greet, head, sup), lockup, chip_holder, year, idle_dot,
           node("Stations", *rings, *sts), node("Network", *[l[0] for l in lines]))

    motif_enter(sc, ef)
    for i, (shp, tr, pts) in enumerate(lines):
        draw(ef, tr, 10 + i * 7, 54 + i * 7)
    for i, r in enumerate(rings):
        pop(ef, r, 30 + i * 8)
    for i, s in enumerate(sts):
        pop(ef, s, 38 + i * 4)
    key_reveal(ef, year_roll, 16, 46, EO)
    ef.key(year, "scaleX", (0, 0.7, "hold"), (14, 0.7, EO), (50, 1.0, "hold"))
    ef.key(year, "scaleY", (0, 0.7, "hold"), (14, 0.7, EO), (50, 1.0, "hold"))
    slide(ef, chip_holder, "x", -380, 20, 52, EIO)
    draw(ef, lock_trim, 48, 60, EO)
    pop(ef, lock_ring, 58, 18)
    key_reveal(ef, lock_rng, 62, 90, EO)
    key_reveal(ef, greet_rng, 76, 96)
    key_reveal(ef, head_rng, 84, 112)
    key_reveal(ef, sup_rng, 98, 120)

    content_enter_back(sc, eb)
    key_reveal(eb, head_rng, 6, 34)

    key_along(idle, idle_dot, red, 0, 300)
    idle.key(idle_dot, "opacity", (0, 0.0, "lin"), (30, 1.0, "lin"), (270, 1.0, "lin"), (300, 0.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 2. Journeys  (concept: left screen)
# ======================================================================
def scene2():
    sc = Scene(2, (318, 176), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 360, "loop")

    sun = circle(112.0, 176.0, 116.0, YEL, name="Sun")
    sky = node("Skyline",
               rect(24, 178, 28, 54, BLACK, name="Block A"), rect(50, 156, 26, 76, BLACK, name="Block B"),
               rect(76, 196, 40, 36, BLACK, name="Block C"), rect(116, 168, 22, 64, BLACK, name="Block D"),
               rect(91, 118, 22, 80, BLACK, name="Clock tower"),
               path_shape([(91, 118), (102, 96), (113, 118)], BLACK, name="Spire"),
               circle(102.0, 136.0, 10.0, WHITE, name="Clock face"),
               rect(0, 230, 170, 8, BLACK, name="Ground"))
    via = node("Viaduct",
               rect(176, 214, 240, 12, BLACK, name="Deck"),
               *[rect(196 + i * 52, 226, 14, 40, BLACK, name=f"Pier {i}") for i in range(4)])
    train = node("Blue train",
                 *[rect(12 + i * 26, 6, 16, 9, WHITE, r=2, name=f"Window {i}") for i in range(5)],
                 rect(0, 0, 150, 26, BLUE, r=7, name="Body", line=BLACK, lw=2.5),
                 x=196.0, y=186.0)
    red = [(-20, 252), (30, 252), (30, 452), (70, 492), (318, 492), (360, 450), (360, 300), (410, 250)]
    blu = [(150, 82), (150, 116), (196, 162), (410, 162)]
    yel = [(410, 540), (360, 540), (330, 570), (330, 760)]
    red_s, red_t = route(red, RED, 14, name="Red route (drawn by the dot)", radius=30)
    blu_s, blu_t = route(blu, BLUE, 12, name="Blue route", radius=24)
    yel_s, yel_t = route(yel, YEL, 14, name="Yellow route", radius=26)
    sts = [station(30, 330), station(130, 492), station(250, 492), station(360, 380)]
    ring = interchange(30, 452, name="Interchange")
    rider = circle(-20.0, 252.0, 20.0, RED, name="Route dot (drawing)", line=BLACK, lw=4.0, opacity=0.0)
    tram = node("Tram",
                rect(14, 10, 68, 8, BLACK, r=2, name="Destination blind"),
                circle(18.0, 96.0, 12.0, YEL, name="Headlight L", line=BLACK, lw=2.0),
                circle(78.0, 96.0, 12.0, YEL, name="Headlight R", line=BLACK, lw=2.0),
                rect(10, 24, 76, 46, BLACK, r=10, name="Windscreen frame"),
                rect(16, 30, 64, 34, SKY, r=7, name="Windscreen"),
                rect(0, 0, 96, 124, BLUE, r=18, name="Front", line=BLACK, lw=3.5),
                *[rect(104 + k * 22, -8 - k * 6, 14, 26, WHITE, r=3, name=f"Side window {k}") for k in range(2)],
                path_shape([(96, 6), (150, -18), (150, 120), (96, 118)], DEEP, name="Side", line=BLACK, lw=3.0),
                x=262.0, y=566.0)
    rails = node("Rails", path_shape([(150, 740), (276, 690), (300, 690), (226, 740)], YEL, name="Rail yellow"),
                 path_shape([(250, 740), (334, 690), (358, 690), (316, 740)], RED, name="Rail red"))
    heroes, copy = metric_copy(sc, 2, (24, 262, 342, 150), 150, RED, (24, 414, 342), (24, 520, 232), 32,
                               (24, 666, 232))
    sc.add(copy, heroes, rider, tram, node("Stations", ring, *sts), node("Network", red_s, blu_s, yel_s),
           rails, train, via, sky, sun)

    motif_enter(sc, ef)
    draw(ef, red_t, 12, 72, (0.45, 0, 0.55, 1))
    ef.key(rider, "opacity", (0, 1.0, "hold"), (72, 1.0, "lin"), (80, 0.0, "hold"))
    key_along(ef, rider, red, 12, 72)
    stations_on(ef, red, sts + [ring], 12, 72)
    draw(ef, blu_t, 20, 50)
    draw(ef, yel_t, 40, 70)
    slide(ef, train, "x", 420, 26, 70, EO)
    slide(ef, tram, "x", 470, 36, 84, EO)
    slide(ef, sky, "y", 70, 14, 46, EO)
    pop(ef, sun, 10, 30)
    standard_copy_motion(sc, ef, eb)

    key_along(idle, rider, red, 0, 360)
    idle.key(rider, "opacity", (0, 0.0, "lin"), (30, 1.0, "lin"), (330, 1.0, "lin"), (360, 0.0, "lin"))
    idle.key(train, "x", (0, 196.0, SOFT), (180, 208.0, SOFT), (360, 196.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 3. Km travelled - ticket strip through a measuring frame
# ======================================================================
def scene3():
    sc = Scene(3, (52, 390), YEL)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 720, "loop")

    orbits, orbit_trims, spinners = [], [], []
    for i, (d, col, pd, pc) in enumerate(((250.0, BLACK, 14.0, RED), (330.0, BLACK, 18.0, BLUE),
                                            (410.0, BLACK, 12.0, WHITE))):
        shp = E("Shape", E("Ellipse", width=d, height=d * 0.62, name="Path"),
                stroke(col, 2.0, "Orbit", "round", "round",
                       (tr := E("TrimPath", start=0.0, end=1.0, modeValue="sequential", name="Draw"))),
                x=195.0, y=250.0, name=f"Orbit {i}")
        orbits.append(shp)
        orbit_trims.append(tr)
        planet = circle(d / 2, 0.0, pd, pc, name="Planet", line=BLACK, lw=3.0)
        spin = node(f"Orbit {i} spinner", planet, x=195.0, y=250.0, scaleY=0.62, rotation=0.6 + i * 2.0)
        spinners.append(spin)
    plate = rect(10, 196, 370, 112, YEL, name="Number plate")
    frame = node("Measuring frame",
                 rect(24, 352, 342, 76, None, r=4, name="Frame", line=BLACK, lw=6.0),
                 *[rect(28 + i * 16.8, 334 if i % 5 == 0 else 340, 3, 14 if i % 5 == 0 else 8, BLACK,
                        name=f"Tick {i}") for i in range(21)])
    slot = rect(-6, 360, 34, 60, BLACK, r=4, name="Slot")
    window = E("Shape", E("Rectangle", width=336.0, height=70.0, originX=0.0, originY=0.0, name="Path"),
               x=27.0, y=355.0, name="Frame window (clip source)")
    unit = text(44, 378, 300, [(SAMPLE["screen3Unit"], "screen3Unit")], 20, BLACK, weight=600, h=26,
                overflow="ellipsis", wrap="noWrap", name="Unit on ticket")
    unit_rng = reveal_modifier(unit, units="characters", dy=0.0)
    strip = node("Ticket strip",
                 unit,
                 *[circle(38.0 + i * 22, 410.0, 5.0, YEL, name=f"Punch {i}") for i in range(15)],
                 rect(27, 364, 340, 6, RED, name="Red band"),
                 rect(27, 362, 340, 56, WHITE, name="Ticket"),
                 E("ClippingShape", sourceId=window.id, name="Frame clip"), x=0.0)
    bus = node("Bus",
               *[rect(10 + i * 21, 7, 14, 11, WHITE, r=2, name=f"Window {i}") for i in range(4)],
               rect(0, 0, 96, 34, RED, r=8, name="Body", line=BLACK, lw=3.0),
               circle(22.0, 34.0, 14.0, BLACK, name="Wheel A"), circle(74.0, 34.0, 14.0, BLACK, name="Wheel B"),
               x=270.0, y=678.0)
    road, road_t = route([(-10, 726), (400, 726)], BLACK, 3, name="Road", trim=True, dash=[10, 8], cap="butt")
    x, y = 24, 200
    hero = text(24, 200, 342, [("0", "distanceKm", COUNT_CONV[3])], 104, BLACK, display=True, align="center",
                h=104, overflow="fitFontSize", valign="middle", wrap="noWrap", name="Hero number", lh=104)
    hero_roll = reveal_modifier(hero, units="characters", dy=-46.0)
    head = text(24, 470, 342, [(SAMPLE["screen3Headline"], "screen3Headline")], 34, BLACK, display=True,
                h=34 * 1.06 * 3 + 4, overflow="fitFontSize", lh=34 * 1.06, name="Headline")
    head_rng = reveal_modifier(head, units="words", dy=30.0)
    sup = text(24, 598, 342, [(SAMPLE["screen3Support"], "screen3Support")], 17, BLACK, h=46, overflow="ellipsis",
               lh=22, name="Support")
    sup_rng = reveal_modifier(sup, units="words", dy=12.0)
    sc.add(node("Copy", head, sup), hero, plate, strip, window, slot, frame, bus, road,
           node("Orbits", *spinners, *orbits))

    motif_enter(sc, ef)
    for i, tr in enumerate(orbit_trims):
        draw(ef, tr, 10 + i * 6, 50 + i * 6)
    for i, s in enumerate(spinners):
        fade_in(ef, s, 40 + i * 5, 52 + i * 5)
    key_reveal(ef, hero_roll, 16, 42, EO)
    ef.key(plate, "scaleY", (0, 0.0, "hold"), (12, 0.0, EO), (30, 1.0, "hold"))
    slide(ef, strip, "x", -360, 30, 84, (0.3, 0.0, 0.2, 1.0))
    key_reveal(ef, unit_rng, 56, 86, EO)
    slide(ef, slot, "x", -60, 18, 34, EO)
    for i, tick in enumerate(frame.children[1:]):
        pop(ef, tick, 30 + i * 2, 10)
    draw(ef, road_t, 50, 90, EO)
    slide(ef, bus, "x", 430, 60, 104, EO)
    key_reveal(ef, head_rng, 72, 100)
    key_reveal(ef, sup_rng, 86, 108)
    content_enter_back(sc, eb)
    key_reveal(eb, head_rng, 6, 34)

    for i, s in enumerate(spinners):
        r0 = rest_value(s, "rotation")
        idle.key(s, "rotation", (0, r0, "lin"), (720, r0 + (2 * math.pi if i != 1 else -2 * math.pi), "lin"))
    finish(sc)
    return sc


# ======================================================================
# 4. Routes explored  (concept: centre screen) + signature route chips
# ======================================================================
CHIP_ROUTES = {}


def scene4():
    sc = Scene(4, (195, 164), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 240, "loop")

    red = [(-20, 96), (110, 96), (195, 164), (276, 246), (346, 246), (346, 424), (410, 488)]
    blu = [(195, 82), (195, 164), (118, 241), (44, 241), (44, 424), (-20, 488)]
    yel = [(410, 132), (300, 132), (268, 164), (122, 164), (90, 132), (-20, 132)]
    lines = {}
    for key, pts, col in (("red", red, RED), ("blue", blu, BLUE), ("yellow", yel, YEL)):
        shp, tr = route(pts, col, 16, name=f"{key} route", radius=34)
        wrap = node(f"{key} route (chip highlight)", shp)
        lines[key] = (wrap, shp, tr, pts)
    hub = circle(195.0, 164.0, 58.0, WHITE, name="Central interchange", line=BLACK, lw=10.0)
    sts = [station(110, 96), station(346, 330), station(44, 330), station(300, 132)]
    vehicle = node("Route vehicle", rect(-14, -8, 28, 16, BLACK, r=5, name="Body"),
                   rect(-9, -4, 18, 6, WHITE, r=2, name="Windows"), x=-40.0, y=-40.0, opacity=0.0)
    chips = []
    for i, (label, col, ink) in enumerate((("R4", RED, WHITE), ("B12", BLUE, WHITE), ("Y7", YEL, BLACK))):
        cx = 24 + i * 84
        chip = node(f"Route chip {label}",
                    text(0, 0, None, [label], 16, ink, weight=700, ox=0.5, oy=0.5, name="Code"),
                    rect(-38, -22, 76, 44, col, r=22, name="Chip", line=BLACK, lw=2.5),
                    x=float(cx + 38), y=488.0)
        chips.append(chip)
    chip_row = node("Route chips (signature interaction; hit-tested by the sequencer)", *chips)
    heroes, copy = metric_copy(sc, 4, (24, 252, 342, 168), 168, BLUE, (24, 418, 342), (24, 530, 342), 34,
                               (24, 656, 342))
    # buildings behind the lines
    dome = node("Dome", circle(330.0, 560.0, 70.0, "FFD9D4C6", name="Dome"),
                rect(292, 560, 76, 120, "FFD9D4C6", name="Drum"), opacity=0.0)
    sc.add(copy, chip_row, heroes, vehicle, hub, node("Stations", *sts),
           node("Network", *[l[0] for l in lines.values()]))
    CHIP_ROUTES.update(lines=lines, vehicle=vehicle, chips=chips)

    motif_enter(sc, ef)
    for i, (key, (wrap, shp, tr, pts)) in enumerate(lines.items()):
        draw(ef, tr, 14 + i * 8, 62 + i * 8)
    pop(ef, hub, 20, 22)
    stations_on(ef, red, sts[:2], 14, 62)
    pop(ef, sts[2], 52)
    pop(ef, sts[3], 46)
    for i, c in enumerate(chips):
        slide(ef, c, "y", 558, 66 + i * 5, 90 + i * 5, EO)
        fade_in(ef, c, 66 + i * 5, 78 + i * 5)
    standard_copy_motion(sc, ef, eb, hero_at=24)
    ef.key(sc.copy_bits["hero"], "rotation", (0, -0.12, "hold"), (24, -0.12, EO), (64, 0.0, "hold"))

    idle.key(hub, "scaleX", (0, 1.0, SOFT), (40, 1.12, SOFT), (80, 1.0, "lin"), (240, 1.0, "lin"))
    idle.key(hub, "scaleY", (0, 1.0, SOFT), (40, 1.12, SOFT), (80, 1.0, "lin"), (240, 1.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 5. Stations visited - stations populate a strictly schematic map
# ======================================================================
def scene5():
    sc = Scene(5, (330, 560), BLUE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 180, "loop")

    l1 = [(-20, 352), (160, 352), (220, 412), (410, 412)]
    l2 = [(300, 82), (300, 300), (240, 360), (240, 520)]
    l3 = [(-20, 470), (60, 470), (120, 410), (120, 300)]
    l4 = [(410, 200), (346, 200), (346, 470), (300, 516), (180, 516)]
    defs = ((l1, WHITE, 10), (l2, YEL, 10), (l3, RED, 10), (l4, WHITE, 6))
    lines = [route(p, c, t, name=f"Line {i}", radius=22) + (p,) for i, (p, c, t) in enumerate(defs)]
    st_pts = [(40, 352), (100, 352), (160, 352), (270, 412), (330, 412), (300, 140), (300, 220), (240, 450),
              (60, 470), (120, 350), (346, 260), (346, 340), (220, 516), (280, 516)]
    sts = [station(x, y, 18.0, name=f"Station {i}") for i, (x, y) in enumerate(st_pts)]
    ix = [interchange(240, 412, 34.0, "Interchange A"), interchange(346, 412, 34.0, "Interchange B"),
          interchange(120, 410, 34.0, "Interchange C")]
    pulse = circle(240.0, 412.0, 34.0, None, name="Pulse", line=WHITE, lw=3.0, opacity=0.0)
    heroes, copy = metric_copy(sc, 5, (24, 108, 250, 168), 168, WHITE, (24, 270, 250), (24, 540, 342), 34,
                               (24, 664, 342), ink=WHITE, sup_color=YEL, num_align="left", unit_align="left")
    sc.add(copy, heroes, node("Stations", *ix, *sts), pulse, node("Map", *[l[0] for l in lines]))

    motif_enter(sc, ef)
    for i, (shp, tr, pts) in enumerate(lines):
        draw(ef, tr, 14 + i * 6, 46 + i * 6, "lin")
    order = sorted(range(len(sts)), key=lambda i: (st_pts[i][1], st_pts[i][0]))
    for k, i in enumerate(order):
        pop(ef, sts[i], 30 + k * 3, 12)
    for k, s in enumerate(ix):
        pop(ef, s, 60 + k * 4, 16)
    standard_copy_motion(sc, ef, eb)

    idle.key(pulse, "opacity", (0, 0.9, "lin"), (60, 0.0, "lin"), (180, 0.0, "lin"))
    idle.key(pulse, "scaleX", (0, 1.0, EO), (60, 2.6, "lin"), (180, 2.6, "lin"))
    idle.key(pulse, "scaleY", (0, 1.0, EO), (60, 2.6, "lin"), (180, 2.6, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 6. Ferry trips - graphic wave bands carry a geometric ferry
# ======================================================================
def scene6():
    sc = Scene(6, (292, 196), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 240, "loop")

    sun = circle(292.0, 196.0, 150.0, YEL, name="Sun")
    skyline = node("Far shore", *[rect(x, 410 - h, w, h, "FFD9D4C6", name=f"Shore {i}")
                                  for i, (x, w, h) in enumerate(((176, 30, 34), (206, 22, 56), (228, 40, 24),
                                                                  (268, 18, 70), (286, 44, 40), (330, 30, 28),
                                                                  (360, 40, 50)))])
    bands = []
    for i, (top, col, period, travel) in enumerate(((410, SKY, 36, 36), (468, BLUE, 44, 88),
                                                    (548, DEEP, 52, 52), (636, "FF0F2F80", 60, 120))):
        kids = [circle(float(-120 + k * period), float(top + 16), float(period), col, name=f"Crest {k}")
                for k in range((600 // period) + 4)]
        kids.append(rect(-120, top + 16, 640, 844 - top, col, name="Band"))
        b = node(f"Wave band {i}", *kids, x=0.0)
        bands.append((b, period, travel))
    ferry = node("Ferry",
                 rect(-14, -48, 12, 20, BLACK, name="Funnel"), rect(-14, -40, 12, 5, RED, name="Funnel band"),
                 *[rect(-24 + k * 14, -24, 9, 8, BLACK, r=2, name=f"Porthole {k}") for k in range(4)],
                 rect(-30, -30, 56, 22, WHITE, r=3, name="Cabin", line=BLACK, lw=3.0),
                 path_shape([(-52, -8), (52, -8), (38, 14), (-40, 14)], RED, name="Hull", line=BLACK, lw=3.0),
                 x=150.0, y=416.0)
    heroes, copy = metric_copy(sc, 6, (24, 120, 220, 168), 168, BLACK, (24, 284, 220), (24, 530, 342), 34,
                               (24, 660, 342), ink=WHITE, sup_color=YEL, num_align="left", unit_align="left",
                               unit_color=BLACK)
    sc.add(copy, heroes, *[b for b, _, _ in bands[1:]], ferry, bands[0][0], skyline, sun)

    motif_enter(sc, ef)
    pop(ef, sun, 10, 36)
    for i, (b, period, travel) in enumerate(bands):
        ef.key(b, "y", (0, 260.0, "hold"), (10 + i * 6, 260.0, EO), (50 + i * 6, 0.0, "hold"))
    slide(ef, ferry, "x", -120, 30, 92, (0.25, 0.1, 0.25, 1))
    ef.key(ferry, "rotation", (0, 0.0, "hold"), (30, -0.12, SOFT), (60, 0.08, SOFT), (92, 0.0, "hold"))
    slide(ef, skyline, "y", 60, 20, 60, EO)
    standard_copy_motion(sc, ef, eb)

    for b, period, travel in bands:
        idle.key(b, "x", (0, 0.0, "lin"), (240, -float(travel), "lin"))
    idle.key(ferry, "rotation", (0, 0.0, SOFT), (60, 0.05, SOFT), (180, -0.05, SOFT), (240, 0.0, "lin"))
    idle.key(ferry, "y", (0, 416.0, SOFT), (120, 421.0, SOFT), (240, 416.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 7. Weekend outings - a ticket splits into two bold panels
# ======================================================================
def scene7():
    sc = Scene(7, (195, 216), WHITE)
    ef = sc.anim("EnterFwd", 120)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 480, "loop")

    def panel(cx, col, name):
        rp = E("Rectangle", width=166.0, height=210.0, originX=0.5, originY=0.5, cornerRadiusTL=12.0, name="Path")
        c = solid(col, name="Panel colour")
        shp = E("Shape", rp, E("Fill", c, name="Fill"), stroke(BLACK, 4.0), name="Panel")
        n = node(name, shp, x=float(cx), y=216.0)
        return n, rp, c

    L, Lr, Lc = panel(107, RED, "Saturday panel")
    R, Rr, Rc = panel(283, BLUE, "Sunday panel")
    sun = node("Sun + rays", circle(0.0, 0.0, 62.0, YEL, name="Sun", line=BLACK, lw=3.0),
               *[node(f"Ray {k}", rect(-3, -54, 6, 14, BLACK, r=3, name="Ray"), rotation=k * math.pi / 4) for k in range(8)],
               x=107.0, y=186.0)
    sat_route, sat_t = route([(44, 290), (84, 250), (130, 250), (170, 290)], BLACK, 6, name="Saturday route",
                             radius=12)
    park = node("Park", path_shape([(-14, 12), (0, -18), (14, 12)], "FF1F7A4A", name="Tree", line=BLACK, lw=2.0),
                circle(0.0, 0.0, 70.0, WHITE, name="Park", line=BLACK, lw=3.0),
                x=283.0, y=186.0)
    sun_route, sun_t = route([(216, 300), (260, 270), (330, 270)], WHITE, 6, name="Sunday route", radius=10,
                             dash=[8, 7], cap="butt")
    perf, perf_t = route([(195, 118), (195, 314)], BLACK, 3, name="Perforation", dash=[6, 6], cap="butt")
    stub_dot = circle(195.0, 216.0, 20.0, YEL, name="Ticket punch", line=BLACK, lw=3.0)
    heroes, copy = metric_copy(sc, 7, (24, 334, 342, 168), 168, BLACK, (24, 500, 342), (24, 560, 342), 34,
                               (24, 650, 342), head_lines=2)
    sc.add(copy, heroes, stub_dot, perf, sun, sat_route, park, sun_route, L, R)

    motif_enter(sc, ef)
    # ticket arrives whole (white), then tears along the perforation into two panels
    for n_, rp, c, x_join, col in ((L, Lr, Lc, 127.5, RED), (R, Rr, Rc, 262.5, BLUE)):
        ef.key(n_, "x", (0, x_join, "hold"), (44, x_join, (0.5, -0.4, 0.3, 1.4)), (72, rest_value(n_, "x"), "hold"))
        ef.key(n_, "y", (0, -180.0, "hold"), (8, -180.0, EO), (34, 216.0, "hold"))
        ef.key(n_, "rotation", (0, -0.1, "hold"), (34, -0.1, SOFT), (44, -0.05, EO),
               (72, 0.0, "hold"))
        ef.key(rp, "width", (0, 135.0, "hold"), (44, 135.0, EO), (72, 166.0, "hold"))
        ef.key(rp, "height", (0, 150.0, "hold"), (44, 150.0, EO), (72, 210.0, "hold"))
        ef.key(c, "colorValue", (0, WHITE, "hold"), (46, WHITE, "lin"), (62, col, "hold"))
    ef.key(perf, "opacity", (0, 1.0, "hold"), (44, 1.0, "lin"), (50, 0.0, "hold"))
    ef.key(perf, "y", (0, 0.0, "hold"))
    slide(ef, perf, "y", -396, 8, 34, EO)
    ef.key(stub_dot, "opacity", (0, 1.0, "hold"), (40, 1.0, "lin"), (46, 0.0, "hold"))
    slide(ef, stub_dot, "y", -180, 8, 34, EO)
    pop(ef, sun, 66, 22)
    pop(ef, park, 72, 22)
    draw(ef, sat_t, 74, 96)
    draw(ef, sun_t, 80, 102)
    standard_copy_motion(sc, ef, eb, hero_at=50)
    sc.extra_rest += [(perf, "opacity", 0.0), (stub_dot, "opacity", 0.0)]
    perf.attrs["opacity"] = 0.0
    stub_dot.attrs["opacity"] = 0.0

    idle.key(sun, "rotation", (0, 0.0, "lin"), (480, math.pi / 2, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 8. Months on the move - departure board
# ======================================================================
def scene8():
    sc = Scene(8, (60, 420), BLACK)
    ef = sc.anim("EnterFwd", 120)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 480, "loop")

    tiles, labels = [], []
    for i in range(12):
        r, c = divmod(i, 4)
        cx, cy = 63.0 + c * 88, 350.0 + r * 66
        lab = text(0, 2, None, [f"{i + 1:02d}"], 30, YEL, display=True, ox=0.5, oy=0.5, name="Code")
        lab_n = node("Flap", lab)
        t = node(f"Board tile {i + 1:02d}",
                 lab_n, rect(-39, -0.5, 78, 1, "FF11141A", name="Split"),
                 rect(-39, -29, 78, 58, GREY, r=6, name="Tile"), x=cx, y=cy)
        lit = node(f"Lit {i + 1:02d}", t)
        lit.add(bind("activeMonths", 18, ramp_conv(i, i + 1, 0.22, 1.0, f"Month {i + 1} lit")))
        tiles.append((t, lab_n, lit))
    heroes, copy = metric_copy(sc, 8, (24, 100, 220, 168), 168, YEL, (24, 264, 342), (24, 548, 342), 34,
                               (24, 668, 342), ink=WHITE, sup_color="FFB9B4A8", num_align="left", unit_align="left",
                               head_lines=3)
    board = node("Departure board", *[t[2] for t in tiles],
                 rect(14, 312, 362, 216, "FF0E1116", r=10, name="Board housing"))
    sc.add(copy, heroes, board)

    motif_enter(sc, ef)
    slide(ef, board, "y", 260, 14, 50, EO)
    for i, (t, lab, lit) in enumerate(tiles):
        f0 = 30 + i * 4
        ef.key(lab, "scaleY", (0, 0.0, "hold"), (f0, 0.0, "lin"), (f0 + 4, 1.0, "lin"), (f0 + 8, 0.0, "lin"),
               (f0 + 12, 1.0, "lin"), (f0 + 16, 0.0, "lin"), (f0 + 22, 1.0, "hold"))
    standard_copy_motion(sc, ef, eb)

    for i, (t, lab, lit) in enumerate(tiles[:4]):
        f0 = 60 + i * 100
        idle.key(lab, "scaleY", (0, 1.0, "hold"), (f0, 1.0, "lin"), (f0 + 5, 0.0, "lin"), (f0 + 10, 1.0, "hold"),
                 (480, 1.0, "hold"))
    finish(sc)
    return sc


# ======================================================================
# 9. Persona reveal - four distinct emblems & choreographies
# ======================================================================
PERSONA_GROUPS = []


def scene9():
    sc = Scene(9, (195, 296), BLUE, bg_bind="personaColor")
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 480, "loop")
    C = (195.0, 296.0)

    # p0 City Connector: interchange knot
    k_lines = []
    for nm, pts, col in (("Knot red", [(60, 430), (330, 160)], RED), ("Knot black", [(60, 160), (330, 430)], BLACK),
                         ("Knot white", [(195, 110), (195, 482)], WHITE), ("Knot yellow", [(20, 296), (370, 296)], YEL)):
        k_lines.append(route(pts, col, 16, name=nm, radius=0))
    k_outer = circle(C[0], C[1], 250.0, None, name="Knot orbit", line=YEL, lw=16.0)
    k_dots = node("Knot stations", *[station(125 * math.cos(a) , 125 * math.sin(a), 24.0, name=f"Knot stop {k}")
                                     for k, a in enumerate([j * math.pi / 4 + math.pi / 8 for j in range(8)])],
                  x=C[0], y=C[1])
    k_core = circle(C[0], C[1], 78.0, WHITE, name="Knot core", line=BLACK, lw=12.0)
    p0 = node("Emblem: interchange knot", k_core, k_dots, k_outer, *[l[0] for l in k_lines])

    # p1 Scenic Rider: window with passing shapes
    win_clip = E("Shape", E("Rectangle", width=244.0, height=170.0, originX=0.5, originY=0.5, cornerRadiusTL=30.0,
                            name="Path"), x=C[0], y=C[1], name="Window glass (clip source)")
    scenery_items = []
    for rep in range(2):
        ox = rep * 300
        scenery_items += [circle(float(ox + 60), 400.0, 190.0, BLUE, name="Hill A", line=BLACK, lw=3.0),
                          circle(float(ox + 210), 410.0, 230.0, "FF1F7A4A", name="Hill B", line=BLACK, lw=3.0),
                          path_shape([(ox + 120, 330), (ox + 136, 290), (ox + 152, 330)], BLACK, name="Tree"),
                          rect(ox + 250, 300, 20, 50, BLACK, name="Tower"),
                          circle(float(ox + 240), 250.0, 44.0, RED, name="Sun")]
    scenery = node("Passing scenery", *scenery_items, x=0.0)
    glass = node("Window view", scenery, rect(73, 211, 244, 170, WHITE, name="Sky"),
                 E("ClippingShape", sourceId=win_clip.id, name="Glass clip"))
    frame_rp = E("Rectangle", width=270.0, height=196.0, originX=0.5, originY=0.5, cornerRadiusTL=40.0, name="Path")
    frame = E("Shape", frame_rp, stroke(BLACK, 18.0), x=C[0], y=C[1], name="Window frame")
    sill = rect(60, 404, 270, 16, BLACK, r=8, name="Sill")
    p1 = node("Emblem: window with passing shapes", frame, sill, glass, win_clip)

    # p2 Route Collector: stacked route tickets
    tickets = []
    for k, (col, rot) in enumerate(((BLACK, -0.42), (YEL, -0.14), (BLUE, 0.14), (RED, 0.42))):
        tk = node(f"Ticket {k}",
                  route([(-70, 22), (-20, 22), (10, -8), (70, -8)], col, 7, name="Ticket route", radius=8,
                        trim=False)[0],
                  rect(-100, -46, 200, 18, col, r=4, name="Stripe"),
                  rect(-100, -46, 200, 92, "FFFFFFFF", r=8, name="Ticket", line=BLACK, lw=4.0),
                  x=C[0], y=C[1] + 90, rotation=rot)
        pivot = node(f"Ticket {k} pivot", tk, y=0.0)
        tickets.append((tk, pivot, rot))
    p2 = node("Emblem: stacked route tickets", *[t[1] for t in reversed(tickets)])
    for tk, pv, rot in tickets:
        # fan around a pivot below the stack: offset each ticket upward along its rotated axis
        tk.attrs["x"] = C[0] + 130 * math.sin(rot)
        tk.attrs["y"] = C[1] + 110 - 130 * math.cos(rot) + 30

    # p3 Weekend Roamer: compass-like station ring
    c_ring_shape, c_ring_t = (lambda s: (s, s.children[1].children[1]))(
        E("Shape", E("Ellipse", width=270.0, height=270.0, name="Path"),
          stroke(WHITE, 10.0, "Ring", "round", "round", E("TrimPath", start=0.0, end=1.0, modeValue="sequential",
                                                          name="Draw")),
          x=C[0], y=C[1], name="Compass ring"))
    c_inner = circle(C[0], C[1], 170.0, None, name="Inner ring", line=YEL, lw=4.0)
    c_ticks = node("Compass stations",
                   *[station(135 * math.cos(a), 135 * math.sin(a), 26.0 if k % 2 == 0 else 16.0,
                             name=f"Compass stop {k}") for k, a in enumerate([j * math.pi / 4 for j in range(8)])],
                   x=C[0], y=C[1])
    needle = node("Needle",
                  path_shape([(0, -112), (16, 0), (-16, 0)], RED, name="North", line=BLACK, lw=3.0),
                  path_shape([(0, 112), (16, 0), (-16, 0)], WHITE, name="South", line=BLACK, lw=3.0),
                  circle(0.0, 0.0, 20.0, YEL, name="Hub", line=BLACK, lw=3.0),
                  x=C[0], y=C[1], rotation=0.785)
    p3 = node("Emblem: compass station ring", needle, c_ticks, c_inner, c_ring_shape)

    groups = []
    for p, grp in enumerate((p0, p1, p2, p3)):
        w = node(f"Persona {p} (visible when _personaSlot == {p})", grp, opacity=1.0 if p == 0 else 0.0)
        w.add(bind("_personaSlot", 18, eq_conv(p)))
        groups.append(w)
    PERSONA_GROUPS.extend(groups)

    label = text(24, 498, 342, [(SAMPLE["personaLabel"], "personaLabel")], 15, WHITE, weight=600, h=20,
                 overflow="ellipsis", wrap="noWrap", ink="_personaInk", name="Persona label")
    title = text(24, 522, 342, [(SAMPLE["personaName"], "personaName")], 44, WHITE, display=True, h=98,
                 overflow="fitFontSize", lh=46, ink="_personaInk", name="Persona title")
    desc = text(24, 628, 342, [(SAMPLE["personaDescription"], "personaDescription")], 19, WHITE, h=52,
                overflow="ellipsis", lh=25, ink="_personaInk", name="Persona description")
    l_rng = reveal_modifier(label, units="characters", dy=0.0)
    t_rng = reveal_modifier(title, units="characters", dy=-40.0, rot=-0.3)
    d_rng = reveal_modifier(desc, units="words", dy=14.0)
    halo = circle(C[0], C[1], 330.0, None, name="Halo", line="33FFFFFF", lw=2.0)
    sc.add(node("Copy", label, title, desc), *groups, halo)

    def ef_common(a, emblem_at):
        motif_enter(sc, a)
        # anticipation: once the persona colour has flooded in, the route dot
        # circles the empty interchange (halo) before the emblem lands
        a.key(MOTIF_DOT, "opacity", (0, 1.0, "hold"), (14, 1.0, "lin"), (18, 0.0, "hold"), (40, 0.0, "lin"),
              (46, 1.0, "hold"), (70, 1.0, "lin"), (76, 0.0, "hold"))
        orbit = [(C[0] + 52 * math.cos(t), C[1] + 52 * math.sin(t))
                 for t in [math.pi / 2 + k * math.pi / 6 for k in range(13)]]
        for k, (x, y) in enumerate(orbit):
            f = 42 + k * 30 / 12
            a.key(MOTIF_DOT, "x", (round(f), x, "lin"))
            a.key(MOTIF_DOT, "y", (round(f), y, "lin"))
        pop(a, halo, emblem_at - 6, 30)
        key_reveal(a, l_rng, emblem_at + 20, emblem_at + 44, EO)
        key_reveal(a, t_rng, emblem_at + 28, emblem_at + 62, EO)
        key_reveal(a, d_rng, emblem_at + 48, emblem_at + 74)

    a0 = sc.anim("EnterFwd0", 160)
    ef_common(a0, 70)
    for i, (shp, tr) in enumerate(k_lines):
        draw(a0, tr, 64 + i * 5, 96 + i * 5, EO)
    pop(a0, k_core, 66, 22)
    a0.key(k_outer, "scaleX", (0, 0.0, "hold"), (72, 0.0, ("el", 1.0, 0.35)), (110, 1.0, "hold"))
    a0.key(k_outer, "scaleY", (0, 0.0, "hold"), (72, 0.0, ("el", 1.0, 0.35)), (110, 1.0, "hold"))
    a0.key(k_dots, "rotation", (0, -1.2, "hold"), (78, -1.2, EO), (118, 0.0, "hold"))
    fade_in(a0, k_dots, 78, 90)

    a1 = sc.anim("EnterFwd1", 160)
    ef_common(a1, 70)
    a1.key(frame, "scaleY", (0, 0.04, "hold"), (64, 0.04, (0.2, 1.3, 0.4, 1)), (92, 1.0, "hold"))
    a1.key(frame, "scaleX", (0, 0.2, "hold"), (60, 0.2, EO), (82, 1.0, "hold"))
    fade_in(a1, frame, 60, 66)
    slide(a1, scenery, "x", 320, 78, 130, (0.2, 0.0, 0.1, 1.0))
    a1.key(sill, "scaleX", (0, 0.0, "hold"), (86, 0.0, EO), (106, 1.0, "hold"))

    a2 = sc.anim("EnterFwd2", 160)
    ef_common(a2, 70)
    for k, (tk, pv, rot) in enumerate(tickets):
        f0 = 62 + k * 8
        a2.key(pv, "y", (0, 520.0, "hold"), (f0, 520.0, EO), (f0 + 28, 0.0, "hold"))
        a2.key(tk, "rotation", (0, rot + 1.4, "hold"), (f0, rot + 1.4, EO), (f0 + 34, rot, "hold"))

    a3 = sc.anim("EnterFwd3", 160)
    ef_common(a3, 70)
    draw(a3, c_ring_t, 62, 92, EO)
    pop(a3, c_inner, 70, 20)
    for k, tick in enumerate(c_ticks.children):
        pop(a3, tick, 74 + k * 3, 12)
    a3.key(needle, "rotation", (0, 0.785 - 4 * math.pi, "hold"), (66, 0.785 - 4 * math.pi, (0.15, 0.6, 0.3, 1.0)),
           (100, 0.6, ("el", 1.0, 0.3)), (136, 0.785, "hold"))
    pop(a3, needle, 64, 16)

    content_enter_back(sc, eb)
    key_reveal(eb, t_rng, 6, 34, EO)

    idle.key(k_dots, "rotation", (0, 0.0, "lin"), (480, math.pi / 4, "lin"))
    idle.key(scenery, "x", (0, 0.0, "lin"), (480, -300.0, "lin"))
    for k, (tk, pv, rot) in enumerate(tickets):
        idle.key(tk, "rotation", (0, rot, SOFT), (120 + k * 20, rot + 0.03, SOFT), (480, rot, "lin"))
    idle.key(needle, "rotation", (0, 0.785, SOFT), (160, 0.86, SOFT), (320, 0.72, SOFT), (480, 0.785, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 10. Summary - collectible ticket card + share
# ======================================================================
def scene10():
    sc = Scene(10, (195, 430), RED)
    ef = sc.anim("EnterFwd", 130)
    eb = sc.anim("EnterBack", 48)
    idle = sc.anim("Idle", 60, "loop")

    head = text(24, 94, 342, [(SAMPLE["summaryHeadline"], "summaryHeadline")], 28, WHITE, display=True, h=62,
                overflow="fitFontSize", lh=30, name="Summary headline")
    h_rng = reveal_modifier(head, units="words", dy=20.0)
    sup = text(24, 696, 342, [(SAMPLE["summarySupport"], "summarySupport")], 16, WHITE, weight=500, h=40,
               overflow="ellipsis", lh=20, name="Summary support")
    s_rng = reveal_modifier(sup, units="words", dy=10.0)

    # ---- share card (own static layout; no progress/controls inside)
    cx0, cy0 = 24, 166
    disc = circle(318.0, 252.0, 58.0, BLUE, name="Persona disc", line=BLACK, lw=4.0)
    disc.children[1].children[0].add(bind("personaColor", 37))
    m1, m1t = route([(36, 236), (120, 236), (150, 266), (290, 266)], RED, 9, name="Card red", radius=14)
    m2, m2t = route([(36, 272), (90, 272), (130, 232), (290, 232)], BLUE, 9, name="Card blue", radius=14)
    m3, m3t = route([(200, 300), (200, 210)], YEL, 9, name="Card yellow", radius=0)
    p_label = text(44, 300, 260, [(SAMPLE["personaLabel"], "personaLabel")], 12, BLACK, weight=600, h=16,
                   overflow="ellipsis", wrap="noWrap", name="Card persona label")
    p_name = text(44, 318, 302, [(SAMPLE["personaName"], "personaName")], 26, BLACK, display=True, h=34,
                  overflow="fitFontSize", wrap="noWrap", name="Card persona name")
    persona = node("Card persona", p_label, p_name)
    cells = []
    stats = (("journeys", 2, RED), ("distanceKm", 3, YEL), ("routesExplored", 4, BLUE),
             ("stationsVisited", 5, BLACK), ("ferryTrips", 6, SKY))
    for i, (prop, n, col) in enumerate(stats):
        r, c = divmod(i, 2)
        x, y = 44 + c * 160, 376 + r * 82
        cell = node(f"Stat {prop}",
                    text(12, 0, 136, [("0", prop, CONV_FMT)], 30, BLACK, display=True, h=36, overflow="fitFontSize",
                         wrap="noWrap", name="Value"),
                    text(12, 38, 136, [(SAMPLE[f"screen{n}Unit"], f"screen{n}Unit")], 12, BLACK, weight=500, h=32,
                         overflow="ellipsis", lh=15, name="Unit"),
                    rect(0, 2, 5, 62, col, r=2, name="Line colour"),
                    x=float(x), y=float(y))
        cells.append(cell)
    name_t = text(44, 630, 302, [(SAMPLE["userName"] or " ", "userName")], 14, BLACK, weight=600, h=18,
                  overflow="ellipsis", wrap="noWrap", name="Card name (privacy-gated)", opacity=0.0)
    period = text(44, 652, 302, [(SAMPLE["periodLabel"], "periodLabel")], 12, INK60, weight=500, h=16,
                  overflow="ellipsis", wrap="noWrap", name="Card period")
    card = node("Share card",
                name_t, period, *cells, persona, disc, m3, m1, m2,
                wordmark(48, 196, 18, "Card wordmark"),
                text(346, 186, None, [("2026", "year", CONV_YEAR)], 15, BLACK, weight=600, ox=1.0, name="Card year"),
                route([(40, 362), (350, 362)], BLACK, 2, name="Divider", trim=False, dash=[4, 5], cap="butt")[0],
                route([(40, 620), (350, 620)], BLACK, 2, name="Stub perforation", trim=False, dash=[4, 5],
                      cap="butt")[0],
                circle(24.0, 620.0, 22.0, RED, name="Notch L"), circle(366.0, 620.0, 22.0, RED, name="Notch R"),
                rect(cx0, cy0, 342, 516, WHITE, r=18, name="Card", line=BLACK, lw=3.0))
    full = node("Summary (has stats)", head, sup, card)
    # ---- empty / new user variant
    e_head = text(24, 236, 342, [(SAMPLE["emptyHeadline"], "emptyHeadline")], 36, WHITE, display=True, h=120,
                  overflow="fitFontSize", lh=38, name="Empty headline")
    e_sup = text(24, 366, 342, [(SAMPLE["emptySupport"], "emptySupport")], 18, WHITE, h=48, overflow="ellipsis",
                 lh=24, name="Empty support")
    e_line, e_t = route([(60, 520), (330, 520)], WHITE, 12, name="First route", radius=0)
    empty = node("Summary (new user)", e_head, e_sup, station(130, 520, 22.0), station(260, 520, 22.0),
                 interchange(195, 520, 40.0, "First interchange"), e_line, opacity=0.0)
    sc.add(empty, full)
    sc.full, sc.empty, sc.name_t = full, empty, name_t

    motif_enter(sc, ef)
    key_reveal(ef, h_rng, 18, 46)
    slide(ef, card, "y", 640, 26, 66, (0.2, 0.9, 0.3, 1.0))
    ef.key(card, "rotation", (0, -0.08, "hold"), (26, -0.08, EO), (70, 0.0, "hold"))
    for t in (m1t, m2t, m3t):
        draw(ef, t, 56, 84)
    pop(ef, disc, 60, 20)
    fade_in(ef, persona, 64, 76)
    for i, cell in enumerate(cells):
        f0 = 70 + i * 6
        ef.key(cell, "scaleX", (0, 1.3, "hold"), (f0, 1.3, EO), (f0 + 14, 1.0, "hold"))
        ef.key(cell, "scaleY", (0, 1.3, "hold"), (f0, 1.3, EO), (f0 + 14, 1.0, "hold"))
        fade_in(ef, cell, f0, f0 + 6)
    key_reveal(ef, s_rng, 100, 124)
    draw(ef, e_t, 20, 50)
    content_enter_back(sc, eb)
    idle.hold(card, "y", 0.0)
    finish(sc)
    return sc


# ======================================================================
# Extra layers that depend on scene content
# ======================================================================
def extra_layers(g):
    globals().update({k: v for k, v in g.items() if not k.startswith("__")})
    s1, s10 = SCENES[1], SCENES[10]

    # greeting hidden when there is no name
    a_on, a_off = Anim("Greeting shown", 1), Anim("Greeting hidden", 1)
    a_on.hold(s1.greeting, "opacity", 1.0)
    a_off.hold(s1.greeting, "opacity", 0.0)
    on, off = state(a_on, 200, 0), state(a_off, 400, 0)
    on.add(go(off, c_str("userName", "equal", "")))
    off.add(go(on, c_str("userName", "notEqual", "")))
    layer("Greeting visibility", on, [on, off])

    # share card name only when the host opts in AND a name exists
    n_on, n_off = Anim("Card name shown", 1), Anim("Card name hidden", 1)
    n_on.hold(s10.name_t, "opacity", 1.0)
    n_off.hold(s10.name_t, "opacity", 0.0)
    son, soff = state(n_on, 200, 0), state(n_off, 400, 0)
    soff.add(go(son, c_bool("shareIncludeName", True), c_str("userName", "notEqual", ""), dur=200))
    son.add(go(soff, c_bool("shareIncludeName", False), dur=200))
    son.add(go(soff, c_str("userName", "equal", ""), dur=200))
    layer("Share privacy: name", soff, [soff, son])

    # empty / new-user summary
    e_full, e_empty = Anim("Summary full", 1), Anim("Summary empty", 1)
    e_full.hold(s10.full, "opacity", 1.0).hold(s10.empty, "opacity", 0.0)
    e_empty.hold(s10.full, "opacity", 0.0).hold(s10.empty, "opacity", 1.0)
    ef_, ee_ = state(e_full, 200, 0), state(e_empty, 400, 0)
    ef_.add(go(ee_, c_bool("_isEmpty", True)))
    ee_.add(go(ef_, c_bool("_isEmpty", False)))
    layer("Summary variant", ef_, [ef_, ee_])

    # signature interaction: route chips highlight a route + run a vehicle on it
    lines, veh, chips = CHIP_ROUTES["lines"], CHIP_ROUTES["vehicle"], CHIP_ROUTES["chips"]
    keys = list(lines.keys())
    none = Anim("Chips none", 1)
    for k in keys:
        none.hold(lines[k][0], "opacity", 1.0)
    for c in chips:
        none.hold(c, "scaleX", 1.0).hold(c, "scaleY", 1.0)
    none.hold(veh, "opacity", 0.0)
    st_none = state(none, 200, 0)
    sts = []
    for i, k in enumerate(keys):
        a = Anim(f"Chip {k} ride", 150)
        for j, kk in enumerate(keys):
            a.key(lines[kk][0], "opacity", (0, 1.0, SOFT), (12, 1.0 if kk == k else 0.18, "hold"))
            c = chips[j]
            sc_ = 1.12 if kk == k else 0.94
            a.key(c, "scaleX", (0, 1.0, POP), (14, sc_, "hold"))
            a.key(c, "scaleY", (0, 1.0, POP), (14, sc_, "hold"))
        pts = lines[k][3]
        a.key(veh, "opacity", (0, 0.0, "hold"), (8, 1.0, "hold"), (140, 1.0, "lin"), (150, 0.0, "hold"))
        key_along(a, veh, pts, 8, 140, ease=EIO)
        sts.append(state(a, 420, -120 + i * 120))
    for i, st in enumerate([st_none] + sts):
        for j, other in enumerate(sts):
            if st is not other:
                st.add(go(other, c_num("_activeRoute", "equal", j + 1), dur=120))
        if st is not st_none:
            st.add(go(st_none, c_num("_activeRoute", "equal", 0), dur=200))
    layer("Signature: route chips", st_none, [st_none] + sts)
