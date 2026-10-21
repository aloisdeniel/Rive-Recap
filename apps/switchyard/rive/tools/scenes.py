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
def gpu_piece(sc, name, script, x, y, **inputs):
    """A ScriptedDrawable (GPU canvas) whose inputs are keyable ScriptInputNumbers.
    Its `live` input is gated per scene by gen.scene_layer (0 while hidden)."""
    d = E("ScriptedDrawable", scriptAssetId=script.id, name=name, x=float(x), y=float(y))
    ins = {}
    inputs.setdefault("live", 1.0)
    for k, v in inputs.items():
        el = E("ScriptInputNumber", propertyValue=float(v), name=k)
        d.add(el)
        ins[k] = el
    if not hasattr(sc, "live_inputs"):
        sc.live_inputs = []
    sc.live_inputs.append(ins["live"])
    return d, ins


def key_in(a, ins, name, *frames):
    a.key(ins[name], "propertyValue", *frames)


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


HEAD_SIZE, HEAD_LH = 50.0, 46.0       # Archivo Condensed Black poster headlines
HEAD_BOTTOM = 650.0                    # headlines are bottom-aligned on this line ...
SUP_Y = 664.0                          # ... so the support always sits 14 px below the last line


def headline(x, w, prop, color=BLACK, lines=3, size=HEAD_SIZE, lh=HEAD_LH, bottom=HEAD_BOTTOM, name="Headline",
             ink=None):
    h = lh * lines + 8
    return text(x, bottom - h, w, [(SAMPLE.get(prop, ""), prop)], size, color, display="cond", h=h,
                overflow="fitFontSize", lh=lh, ls=-0.3, valign="bottom", name=name, ink=ink)


def support(x, w, prop, color=BLACK, y=SUP_Y, name="Support", ink=None):
    return text(x, y, w, [(SAMPLE.get(prop, ""), prop)], 18, color, h=48, overflow="ellipsis", lh=24,
                name=name, ink=ink)


def metric_copy(sc, n, num_box, num_size, num_color, unit_box, head_box, head_size=None, sup_box=None,
                ink=BLACK, sup_color=None, num_align="center", unit_align="center", head_lines=3,
                unit_color=None):
    x, y, w, h = num_box
    hero = text(x, y, w, [("0", NUM_PROP[n], COUNT_CONV[n])],
                num_size, num_color, display=True, align=num_align, h=h, overflow="fitFontSize",
                valign="middle", wrap="noWrap", name="Hero number", lh=num_size * 1.0, ls=-num_size * 0.02)
    sem = E("SemanticData", bind(NUM_PROP[n], 983, CONV_FMT), bind(f"screen{n}Unit", 984),
            role="text", isHidden=n != 2, name="Semantics (full exact value)")
    hero.children.insert(0, sem)
    sc.sems.append(sem)
    hero_roll = reveal_modifier(hero, units="characters", dy=-46.0)
    ux, uy, uw = unit_box
    unit = text(ux, uy, uw, [(SAMPLE[f"screen{n}Unit"], f"screen{n}Unit")], 22, unit_color or ink, weight=600,
                align=unit_align, h=56, overflow="ellipsis", name="Unit", lh=27)
    unit_rng = reveal_modifier(unit, units="words", dy=14.0)
    hx, hw = head_box[0], head_box[1]
    head = headline(hx, hw, f"screen{n}Headline", ink, lines=head_lines)
    head_rng = reveal_modifier(head, units="words", dy=34.0)
    sx, sw = (sup_box or (hx, hw))[:2]
    sup = support(sx, sw, f"screen{n}Support", sup_color or ink)
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
    key_reveal(ef, b["head_rng"], 70, 100)
    key_reveal(ef, b["sup_rng"], 86, 108)
    content_enter_back(sc, eb)
    key_reveal(eb, b["head_rng"], 6, 34)
    key_reveal(eb, b["sup_rng"], 14, 40)


def finish(sc, ef_dur=110):
    """Common exit timelines."""
    xf = sc.anim("ExitFwd", 50)
    content_exit_fwd(sc, xf)
    xb = sc.anim("ExitBack", 44)
    motif_exit_back(sc, xb)
    return xf, xb


# ======================================================================
# 1. Invitation
# ======================================================================
def scene1():
    sc = Scene(1, (195, 353), WHITE)
    ef = sc.anim("EnterFwd", 120)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    # the network is a real 3D world disc (scripts/poster3d.luau, kind 1), the
    # interchange roundel made solid: it starts as a flat plan seen from above and
    # the camera dives into an isometric view while the route ribbons swell into
    # being, the blocks rise and the station pucks pop up
    map3d, m_in = gpu_piece(sc, "Transit world 3D", SCRIPT_P3, 0, 222, kind=1, w=390, h=262, res=2,
                            build=1.0, pitch=1.0, yaw=-0.42, dist=6.7, fov=0.5, camX=0.0, camY=0.0,
                            tz=0.0, sway=0.0, dim=0.0, outline=0.018)
    network = node("Network (3D world)", map3d)
    year = text(24, 138, 342, [("2026", "year", CONV_YEAR)], 128, BLACK, display=True, h=128, align="center",
                overflow="fitFontSize", valign="middle", wrap="noWrap", name="Oversized year", lh=128, ls=-3.5)
    year_roll = reveal_modifier(year, units="characters", dy=-60.0)
    greet = text(24, 92, 342, [(SAMPLE.get("greetingLabel", "Hi,"), "greetingLabel"), " ",
                               (SAMPLE["userName"], "userName")], 20, BLACK, weight=700, h=26,
                 overflow="ellipsis", wrap="noWrap", name="Greeting")
    greet_rng = reveal_modifier(greet, units="words", dy=12.0)
    # period: a route stub leading into the label (no highlight box)
    chip = text(42, 118, 324, [(SAMPLE["periodLabel"], "periodLabel")], 13, INK60, weight=600, h=18,
                overflow="ellipsis", wrap="noWrap", name="Period label", ls=0.2)
    chip_holder = node("Period chip", chip, rect(24, 123, 12, 6, RED, r=3, name="Route stub"), x=0.0)
    # wordmark lockup revealed through the motif
    lock_text = text(66, 492, 300, ["Switchyard"], 34, BLACK, display=True, name="Wordmark lockup text",
                     wrap="noWrap", ls=-0.6)
    lock_rng = reveal_modifier(lock_text, units="characters", dy=0.0)
    lock_ring = circle(42.0, 514.0, 30.0, WHITE, name="Lockup ring", line=BLACK, lw=6.0)
    lock_stub, lock_trim = route([(-20, 514), (36, 514)], RED, 10, name="Lockup route", radius=0)
    lockup = node("Wordmark lockup", lock_text, lock_ring, lock_stub)
    head = headline(24, 342, "introHeadline", lines=2, name="Intro headline")
    head_rng = reveal_modifier(head, units="words", dy=34.0)
    sup = support(24, 342, "introSupport", name="Intro support")
    sup_rng = reveal_modifier(sup, units="words", dy=12.0)
    sc.greeting = greet
    sc.network = network
    sc.add(node("Copy", head, sup), greet, lockup, chip_holder, year, network)

    motif_enter(sc, ef)
    # camera dive: plan view -> isometric, with a little overshoot in the yaw
    key_in(ef, m_in, "build", (0, 0.0, "hold"), (8, 0.0, (0.35, 0.0, 0.6, 1.0)), (104, 1.0, "hold"))
    key_in(ef, m_in, "pitch", (0, 0.0, "hold"), (16, 0.0, (0.55, 0.0, 0.2, 1.0)), (108, 1.0, "hold"))
    key_in(ef, m_in, "yaw", (0, 0.5, "hold"), (12, 0.5, (0.5, 0.0, 0.25, 1.0)), (96, -0.5, (0.4, 0.0, 0.5, 1.0)),
           (118, -0.42, "hold"))
    key_in(ef, m_in, "dist", (0, 11.0, "hold"), (6, 11.0, (0.45, 0.0, 0.15, 1.0)), (104, 6.7, "hold"))
    
    key_reveal(ef, year_roll, 16, 46, EO)
    ef.key(year, "scaleX", (0, 0.7, "hold"), (14, 0.7, EO), (50, 1.0, "hold"))
    ef.key(year, "scaleY", (0, 0.7, "hold"), (14, 0.7, EO), (50, 1.0, "hold"))
    slide(ef, chip_holder, "x", -380, 30, 62, EIO)
    draw(ef, lock_trim, 48, 60, EO)
    pop(ef, lock_ring, 58, 18)
    key_reveal(ef, lock_rng, 62, 90, EO)
    key_reveal(ef, greet_rng, 76, 96)
    key_reveal(ef, head_rng, 84, 112)
    key_reveal(ef, sup_rng, 98, 120)

    content_enter_back(sc, eb)
    key_reveal(eb, head_rng, 6, 34)

    # the board sways gently on its pivot (Joystick-scrubbed, so pause freezes it)
    key_in(idle, m_in, "sway", (0, 0.0, SOFT), (120, 0.07, SOFT), (360, -0.07, SOFT), (480, 0.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 2. Journeys  (concept: left screen)
# ======================================================================
def arch_viaduct(x0, x1, deck_y, spring_y, pier_w, span, color=BLACK, name="Viaduct"):
    """A schematic arched viaduct: deck, piers and arch spandrels as one silhouette."""
    kids = [rect(x0, deck_y, x1 - x0, 12, color, name="Deck")]
    x = x0
    k = 0
    while x < x1:
        kids.append(rect(x, deck_y + 12, pier_w, (spring_y - deck_y) + 30, color, name=f"Pier {k}"))
        xa, xb = x + pier_w, min(x + pier_w + span, x1 + 40)
        r = (xb - xa) / 2.0
        cx = (xa + xb) / 2.0
        pts = [(xa, deck_y + 12), (xb, deck_y + 12), (xb, spring_y)]
        for j in range(1, 12):
            t = j / 12.0 * math.pi
            pts.append((cx + r * math.cos(t), spring_y - r * 0.82 * math.sin(t)))
        pts.append((xa, spring_y))
        kids.append(path_shape(pts, color, name=f"Spandrel {k}"))
        x = xb
        k += 1
    return node(name, *kids)


def skyline_old_town(color=BLACK):
    g = 232
    return node("Old town",
                path_shape([(14, g), (14, 186), (35, 164), (56, 186), (56, g)], color, name="Gable A"),
                path_shape([(52, g), (52, 196), (70, 178), (88, 196), (88, g)], color, name="Gable B"),
                rect(87, 120, 29, 112, color, name="Clock tower"),
                path_shape([(88, 122), (103, 84), (118, 122)], color, name="Spire"),
                rect(101, 76, 4, 10, color, name="Finial"),
                circle(103.0, 140.0, 15.0, WHITE, name="Clock face"),
                rect(102, 134, 2.5, 7, color, name="Hand H"), rect(102, 139, 6, 2.5, color, name="Hand M"),
                rect(116, 190, 34, 42, color, name="Hall"), rect(138, 176, 8, 16, color, name="Chimney"),
                circle(160.0, 214.0, 34.0, color, name="Tree A"), circle(141.0, 222.0, 24.0, color, name="Tree B"),
                rect(0, 230, 184, 6, color, name="Ground"))


def train_cars(n_cars, color, x=0.0, y=0.0, name="Train", car_w=74.0, h=24.0):
    kids = []
    for c in range(n_cars):
        ox = c * (car_w + 4)
        for k in range(4):
            kids.append(rect(ox + 9 + k * 15, 6, 10, 8, WHITE, r=2, name=f"Window {c}.{k}"))
        kids.append(rect(ox, h - 6, car_w, 3, RED if color != RED else YEL, name=f"Stripe {c}"))
        if c == 0:
            kids.append(path_shape([(ox, 0), (ox + car_w, 0), (ox + car_w, h), (ox - 8, h), (ox - 8, 10)],
                                   color, name=f"Cab {c}", line=BLACK, lw=2.5))
        else:
            kids.append(rect(ox, 0, car_w, h, color, r=5, name=f"Car {c}", line=BLACK, lw=2.5))
    return node(name, *kids, x=x, y=y)


def scene2():
    sc = Scene(2, (318, 176), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    sun = circle(132.0, 172.0, 112.0, YEL, name="Sun")
    sky = skyline_old_town()
    via = arch_viaduct(170, 410, 212, 262, 10, 42)
    train = train_cars(3, BLUE, x=192.0, y=186.0, name="Blue train")
    train_idle = node("Blue train (idle drift)", train)
    red = [(-20, 252), (30, 252), (30, 452), (70, 492), (318, 492), (360, 450), (360, 300), (410, 250)]
    blu = [(150, 82), (150, 116), (196, 162), (410, 162)]
    red_s, red_t = route(red, RED, 14, name="Red route (drawn by the dot)", radius=30)
    blu_s, blu_t = route(blu, BLUE, 12, name="Blue route", radius=24)
    sts = [station(30, 330), station(130, 492), station(250, 492), station(360, 380)]
    ring = interchange(30, 452, name="Interchange")
    rider = circle(-20.0, 252.0, 20.0, RED, name="Route dot (drawing)", line=BLACK, lw=4.0, opacity=0.0)
    idle_rider = circle(-20.0, 252.0, 16.0, WHITE, name="Idle rider", line=RED, lw=4.5, opacity=0.0)
    # a real 3D tram (scripts/poster3d.luau, kind 0) brakes into the stop at the
    # bottom right; its ground stripes run away to the vanishing point
    tram, t_in = gpu_piece(sc, "Tram 3D", SCRIPT_P3, 0, 404, kind=0, w=390, h=336, res=2, build=1.0,
                           pitch=0.2, yaw=-0.58, dist=6.2, fov=0.52, camX=0.5, camY=-0.4, tz=0.0, sway=0.0,
                           dim=0.0, outline=0.022)
    sc.tram_slot = tram
    heroes, copy = metric_copy(sc, 2, (24, 262, 342, 150), 150, RED, (24, 414, 342), (24, 228))
    sc.add(copy, heroes, rider, idle_rider, node("Stations", ring, *sts), tram,
           node("Network", red_s, blu_s), train_idle, via, sky, sun)

    motif_enter(sc, ef)
    draw(ef, red_t, 12, 72, (0.45, 0, 0.55, 1))
    ef.key(rider, "opacity", (0, 1.0, "hold"), (72, 1.0, "lin"), (80, 0.0, "hold"))
    key_along(ef, rider, red, 12, 72)
    stations_on(ef, red, sts + [ring], 12, 72)
    draw(ef, blu_t, 20, 50)
    slide(ef, train, "x", 420, 26, 70, EO)
    # the tram runs in from the distance and brakes (a long ease-out with a tiny settle)
    key_in(ef, t_in, "tz", (0, -16.0, "hold"), (24, -16.0, (0.15, 0.55, 0.25, 1.0)), (92, 0.06, SOFT),
           (106, 0.0, "hold"))
    slide(ef, sky, "y", 70, 14, 46, EO)
    slide(ef, via, "y", 40, 18, 50, EO)
    pop(ef, sun, 10, 30)
    standard_copy_motion(sc, ef, eb)

    key_along(idle, idle_rider, red, 40, 400)
    idle.key(idle_rider, "x", (0, -20.0, "hold"))
    idle.key(idle_rider, "y", (0, 252.0, "hold"))
    idle.key(idle_rider, "opacity", (0, 0.0, "hold"), (40, 0.0, "lin"), (60, 1.0, "lin"), (380, 1.0, "lin"),
             (400, 0.0, "hold"))
    idle.key(train_idle, "x", (0, 0.0, SOFT), (240, 14.0, SOFT), (480, 0.0, "lin"))
    key_in(idle, t_in, "sway", (0, 0.0, SOFT), (240, 0.035, SOFT), (480, 0.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 3. Km travelled - ticket strip through a measuring frame
# ======================================================================
def scene3():
    sc = Scene(3, (52, 390), YEL)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    # "your own little universe": three orbits drawn as transit lines, each with a
    # station-planet that circles once (or twice) per idle loop
    orbits, orbit_trims, spinners, spin_idle = [], [], [], []
    for i, (d, col, lw_, pd, pc) in enumerate(((236.0, BLACK, 5.0, 18.0, RED), (318.0, RED, 7.0, 22.0, WHITE),
                                                (404.0, BLUE, 5.0, 16.0, YEL))):
        shp = E("Shape", E("Ellipse", width=d, height=d * 0.6, name="Path"),
                stroke(col, lw_, "Orbit", "round", "round",
                       (tr := E("TrimPath", start=0.0, end=1.0, modeValue="sequential", name="Draw"))),
                x=195.0, y=252.0, name=f"Orbit {i}")
        orbits.append(shp)
        orbit_trims.append(tr)
        a0 = 0.6 + i * 2.0
        planet = circle(d / 2 * math.cos(a0), d * 0.3 * math.sin(a0), pd, pc, name="Station planet",
                        line=BLACK, lw=4.0)
        spin = node(f"Orbit {i} spinner", planet, x=195.0, y=252.0)
        spinners.append(spin)
        spin_idle.append((planet, d, a0))
    plate = rect(10, 200, 370, 104, YEL, name="Number plate")
    frame = node("Measuring frame",
                 rect(24, 352, 342, 76, None, r=4, name="Frame", line=BLACK, lw=6.0),
                 *[rect(28 + i * 16.8, 334 if i % 5 == 0 else 340, 3, 14 if i % 5 == 0 else 8, BLACK,
                        name=f"Tick {i}") for i in range(21)])
    slot = rect(-6, 360, 34, 60, BLACK, r=4, name="Slot")
    window = E("Shape", E("Rectangle", width=336.0, height=70.0, originX=0.0, originY=0.0, name="Path"),
               x=27.0, y=355.0, name="Frame window (clip source)")
    unit = text(44, 378, 300, [(SAMPLE["screen3Unit"], "screen3Unit")], 20, BLACK, weight=700, h=26,
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
               x=270.0, y=676.0)
    bus_idle = node("Bus (idle)", bus)
    road, road_t = route([(-10, 724), (400, 724)], BLACK, 3, name="Road", trim=True, dash=[10, 8], cap="butt")
    hero = text(24, 202, 342, [("0", "distanceKm", COUNT_CONV[3])], 104, BLACK, display=True, align="center",
                h=104, overflow="fitFontSize", valign="middle", wrap="noWrap", name="Hero number", lh=104, ls=-2.0)
    sem = E("SemanticData", bind("distanceKm", 983, CONV_FMT), bind("screen3Unit", 984),
            role="text", isHidden=True, name="Semantics (full exact value)")
    hero.children.insert(0, sem)
    sc.sems.append(sem)
    hero_roll = reveal_modifier(hero, units="characters", dy=-46.0)
    head = headline(24, 342, "screen3Headline", lines=3, bottom=618)
    head_rng = reveal_modifier(head, units="words", dy=34.0)
    sup = support(24, 300, "screen3Support", y=630)
    sup_rng = reveal_modifier(sup, units="words", dy=12.0)
    sc.add(node("Copy", head, sup), hero, plate, strip, window, slot, frame, bus_idle, road,
           node("Orbits", *spinners, *orbits))

    motif_enter(sc, ef)
    for i, tr in enumerate(orbit_trims):
        draw(ef, tr, 10 + i * 6, 50 + i * 6)
    for i, s_ in enumerate(spinners):
        fade_in(ef, s_, 40 + i * 5, 52 + i * 5)
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

    for i, (pl, d, a0) in enumerate(spin_idle):
        turns = (1.0, -1.0, 2.0)[i]
        steps = 48
        for k in range(steps + 1):
            ang = a0 + turns * 2 * math.pi * k / steps
            f = round(IDLE_FRAMES * k / steps)
            idle.key(pl, "x", (f, d / 2 * math.cos(ang), "lin"))
            idle.key(pl, "y", (f, d * 0.3 * math.sin(ang), "lin"))
    idle.key(bus_idle, "y", (0, 0.0, SOFT), (8, -1.5, SOFT), (16, 0.0, "lin"), (240, 0.0, SOFT), (248, -1.5, SOFT),
             (256, 0.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 4. Routes explored  (concept: centre screen) + signature route chips
# ======================================================================
CHIP_ROUTES = {}


def scene4():
    sc = Scene(4, (195, 164), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    red = [(-20, 96), (110, 96), (195, 164), (276, 246), (346, 246), (346, 424), (410, 488)]
    blu = [(195, 82), (195, 164), (118, 241), (44, 241), (44, 424), (-20, 488)]
    yel = [(410, 132), (300, 132), (268, 164), (122, 164), (90, 132), (-20, 132)]
    lines = {}
    for key, pts, col in (("red", red, RED), ("blue", blu, BLUE), ("yellow", yel, YEL)):
        shp, tr = route(pts, col, 16, name=f"{key} route", radius=34)
        wrap = node(f"{key} route (chip highlight)", shp)
        lines[key] = (wrap, shp, tr, pts)
    hub = circle(195.0, 164.0, 58.0, WHITE, name="Central interchange", line=BLACK, lw=10.0)
    hub_breath = node("Central interchange (idle breath)", hub, x=195.0, y=164.0)
    hub.attrs["x"], hub.attrs["y"] = 0.0, 0.0
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
    heroes, copy = metric_copy(sc, 4, (24, 252, 342, 168), 168, BLUE, (24, 418, 342), (24, 342), head_lines=2)
    # grey architecture behind the lines (depth, as in the concept)
    stone = "FFDDD8CB"
    city = node("Grey city",
                circle(326.0, 118.0, 64.0, stone, name="Dome"), rect(294, 118, 64, 92, stone, name="Drum"),
                rect(322, 70, 8, 22, stone, name="Lantern"),
                rect(18, 96, 40, 130, stone, name="Tower A"), rect(58, 140, 30, 86, stone, name="Block B"),
                rect(236, 196, 46, 50, stone, name="Block C"), rect(140, 214, 40, 36, stone, name="Block D"),
                path_shape([(18, 96), (38, 70), (58, 96)], stone, name="Tower roof"))
    sc.add(copy, chip_row, heroes, vehicle, hub_breath, node("Stations", *sts),
           node("Network", *[l[0] for l in lines.values()]), city)
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

    slide(ef, city, "y", 60, 10, 50, EO)
    fade_in(ef, city, 10, 30)
    for f0 in (0, 240):
        for prop in ("scaleX", "scaleY"):
            idle.key(hub_breath, prop, (f0, 1.0, SOFT), (f0 + 40, 1.12, SOFT), (f0 + 80, 1.0, "lin"))
    for prop in ("scaleX", "scaleY"):
        idle.key(hub_breath, prop, (IDLE_FRAMES, 1.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 5. Stations visited - stations populate a strictly schematic map
# ======================================================================
def scene5():
    sc = Scene(5, (330, 560), BLUE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

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
    heroes, copy = metric_copy(sc, 5, (24, 108, 250, 168), 168, WHITE, (24, 270, 250), (24, 342), ink=WHITE,
                               sup_color=YEL, num_align="left", unit_align="left", head_lines=2)
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

    idle.key(pulse, "opacity", (0, 0.0, "hold"))
    idle.key(pulse, "scaleX", (0, 1.0, "hold"))
    idle.key(pulse, "scaleY", (0, 1.0, "hold"))
    for f0 in (30, 190, 350):
        idle.key(pulse, "opacity", (f0, 0.9, "lin"), (f0 + 60, 0.0, "hold"))
        idle.key(pulse, "scaleX", (f0, 1.0, EO), (f0 + 60, 2.6, "hold"), (f0 + 61, 1.0, "hold"))
        idle.key(pulse, "scaleY", (f0, 1.0, EO), (f0 + 60, 2.6, "hold"), (f0 + 61, 1.0, "hold"))
    finish(sc)
    return sc


# ======================================================================
# 6. Ferry trips - graphic wave bands carry a geometric ferry
# ======================================================================
def ferry_art():
    """A Swiss-lake paddle-steamer reduced to poster geometry."""
    return node("Ferry body",
                rect(-6, -78, 3, 30, BLACK, name="Mast"),
                path_shape([(-3, -78), (16, -72), (-3, -66)], YEL, name="Pennant", line=BLACK, lw=2.0),
                rect(14, -66, 16, 30, BLACK, name="Funnel"), rect(14, -66, 16, 7, RED, name="Funnel band"),
                rect(-36, -40, 64, 8, BLACK, name="Upper deck rail"),
                *[rect(-30 + k * 13, -30, 8, 9, BLUE, r=2, name=f"Window {k}") for k in range(5)],
                rect(-40, -36, 76, 30, WHITE, r=4, name="Saloon", line=BLACK, lw=3.0),
                rect(-56, -10, 112, 4, BLACK, name="Main deck"),
                circle(0.0, -2.0, 30.0, RED, name="Paddle box", line=BLACK, lw=3.0),
                path_shape([(-70, -8), (66, -8), (50, 16), (-58, 16)], RED, name="Hull", line=BLACK, lw=3.0),
                rect(-60, 4, 116, 5, WHITE, name="Waterline"))


def scene6():
    sc = Scene(6, (300, 176), WHITE)
    ef = sc.anim("EnterFwd", 110)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    sun = circle(306.0, 168.0, 104.0, YEL, name="Sun")
    rays = node("Sun rays", *[node(f"Ray {k}", rect(-2.5, -78, 5, 14, YEL, r=2.5, name="Ray"),
                                  rotation=k * math.pi / 6) for k in range(12)], x=306.0, y=168.0)
    rays_idle = node("Sun rays (idle turn)", rays)
    stone = "FFDDD8CB"
    skyline = node("Far shore",
                   *[rect(x, 410 - h, w, h, stone, name=f"Shore {i}")
                     for i, (x, w, h) in enumerate(((150, 30, 34), (180, 22, 56), (202, 40, 24), (242, 18, 70),
                                                    (260, 44, 40), (304, 30, 28), (334, 56, 50)))],
                   path_shape([(242, 340), (251, 318), (260, 340)], stone, name="Spire"),
                   rect(0, 404, 390, 8, stone, name="Quay"))
    bands = []
    for i, (top, col, period, travel) in enumerate(((410, SKY, 40, 80), (468, BLUE, 48, 96),
                                                    (548, DEEP, 60, 120), (636, "FF0F2F80", 80, 160))):
        kids = [circle(float(-160 + k * period), float(top + 16), float(period), col, name=f"Crest {k}")
                for k in range((1080 // period) + 2)]
        kids.append(rect(-160, top + 16, 1080, 844 - top, col, name="Band"))
        b = node(f"Wave band {i}", *kids, x=0.0)
        drift = node(f"Wave band {i} (idle drift)", b)
        bands.append((b, drift, period, travel))
    ferry = ferry_art()
    ferry_bob = node("Ferry (idle bob)", ferry)
    ferry_n = node("Ferry", ferry_bob, x=150.0, y=420.0)
    wake, wake_t = route([(20, 432), (96, 432)], WHITE, 4, name="Wake", dash=[10, 7], cap="butt")
    heroes, copy = metric_copy(sc, 6, (24, 112, 236, 168), 168, BLACK, (24, 276, 236), (24, 342), ink=WHITE,
                               sup_color=YEL, num_align="left", unit_align="left", unit_color=BLACK, head_lines=2)
    sc.add(copy, heroes, *[d for _, d, _, _ in bands[1:]], wake, ferry_n, bands[0][1], skyline, rays_idle, sun)

    motif_enter(sc, ef)
    pop(ef, sun, 10, 36)
    for k, ray in enumerate(rays.children):
        pop(ef, ray, 24 + k * 2, 14)
    for i, (b, drift, period, travel) in enumerate(bands):
        ef.key(b, "y", (0, 260.0, "hold"), (10 + i * 6, 260.0, EO), (50 + i * 6, 0.0, "hold"))
    slide(ef, ferry_n, "x", -140, 30, 92, (0.25, 0.1, 0.25, 1))
    ef.key(ferry_n, "rotation", (0, 0.0, "hold"), (30, -0.1, SOFT), (60, 0.07, SOFT), (92, 0.0, "hold"))
    draw(ef, wake_t, 60, 96, EO)
    slide(ef, skyline, "y", 60, 20, 60, EO)
    standard_copy_motion(sc, ef, eb)

    for b, drift, period, travel in bands:
        idle.key(drift, "x", (0, 0.0, "lin"), (IDLE_FRAMES, -float(travel) * 2, "lin"))
    for f0 in (0, 160, 320):
        idle.key(ferry_bob, "rotation", (f0, 0.0, SOFT), (f0 + 40, 0.04, SOFT), (f0 + 120, -0.04, SOFT))
        idle.key(ferry_bob, "y", (f0, 0.0, SOFT), (f0 + 80, 4.0, SOFT))
    idle.key(ferry_bob, "rotation", (IDLE_FRAMES, 0.0, "lin"))
    idle.key(ferry_bob, "y", (IDLE_FRAMES, 0.0, "lin"))
    idle.key(rays_idle, "rotation", (0, 0.0, "lin"), (IDLE_FRAMES, math.pi / 6, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 7. Weekend outings - a ticket splits into two bold panels
# ======================================================================
def scene7():
    sc = Scene(7, (195, 216), WHITE)
    ef = sc.anim("EnterFwd", 120)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

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
    heroes, copy = metric_copy(sc, 7, (24, 322, 342, 156), 156, BLACK, (24, 476, 342), (24, 342), head_lines=2)
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
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    # a real split-flap departure board (scripts/flapboard.luau): twelve 3D flap
    # modules roll through random numbers and land on their month, staggered, in a
    # 5x7 dot-matrix face; months beyond activeMonths stay dark
    flaps, f_in = gpu_piece(sc, "Split-flap board 3D", SCRIPT_FLAP, 0, 296, w=390, h=240, res=2, roll=1.0,
                            idle=0.0, active=12.0, flips=7.0, pitch=0.14)
    f_in["active"].add(bind("activeMonths", 243))
    heroes, copy = metric_copy(sc, 8, (24, 100, 220, 168), 168, YEL, (24, 264, 342), (24, 342), ink=WHITE,
                               sup_color="FFB9B4A8", num_align="left", unit_align="left", head_lines=2)
    housing = node("Board housing",
                   rect(14, 312, 362, 216, "FF0E1116", r=10, name="Housing"),
                   rect(14, 312, 362, 216, None, r=10, name="Housing edge", line="FF2A3038", lw=2.0))
    board = node("Departure board", flaps, housing)
    sc.add(copy, heroes, board)

    motif_enter(sc, ef)
    slide(ef, board, "y", 260, 14, 50, EO)
    key_in(ef, f_in, "roll", (0, 0.0, "hold"), (34, 0.0, "lin"), (108, 1.0, "hold"))
    standard_copy_motion(sc, ef, eb)

    key_in(idle, f_in, "idle", (0, 0.0, "lin"), (IDLE_FRAMES, 1.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 9. Persona reveal - four distinct emblems & choreographies
# ======================================================================
PERSONA_GROUPS = []


def scene9():
    sc = Scene(9, (195, 296), BLUE, bg_bind="personaColor")
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")
    C = (195.0, 296.0)

    # p0 City Connector: an interchange ring holding the whole city - skyline, sun,
    # an arched bridge, water and a red train - with the lines running through it
    k_lines = []
    for nm, pts, col in (("Knot red", [(20, 470), (370, 120)], RED), ("Knot white", [(30, 120), (360, 470)], WHITE),
                         ("Knot yellow", [(-10, 330), (400, 262)], YEL), ("Knot black", [(150, 82), (240, 520)], BLACK)):
        k_lines.append(route(pts, col, 16, name=nm, radius=0))
    R_V = 112.0
    v_clip = circle(0.0, 0.0, R_V * 2, None, name="Vignette glass (clip source)")
    v_train = train_cars(2, RED, x=-150.0, y=-6.0, name="Vignette train", car_w=58.0, h=20.0)
    v_train_idle = node("Vignette train (idle run)", v_train)
    v_water = node("Water", *[route([(-120 + k * 37, 64 + (k % 3) * 14), (-100 + k * 37, 64 + (k % 3) * 14)], WHITE, 3,
                                    name=f"Glint {k}", radius=0, trim=False, cap="round")[0] for k in range(7)],
                   rect(-120, 40, 240, 80, BLUE, name="Lake"))
    v_bridge = node("Bridge", arch_viaduct(-130, 130, 14, 46, 9, 34, name="Arches"))
    v_city = node("Skyline",
                  rect(-92, -58, 26, 80, BLUE, name="Glass tower A", line=BLACK, lw=2.5),
                  rect(-62, -78, 22, 100, BLACK, name="Tower B"),
                  rect(4, -54, 14, 70, BLACK, name="Spire L"), path_shape([(4, -54), (11, -92), (18, -54)], BLACK, name="Spire L top"),
                  rect(26, -48, 14, 64, BLACK, name="Spire R"), path_shape([(26, -48), (33, -84), (40, -48)], BLACK, name="Spire R top"),
                  rect(0, -20, 46, 36, BLACK, name="Nave"),
                  rect(58, -40, 30, 56, BLUE, name="Glass tower C", line=BLACK, lw=2.5),
                  rect(-36, -26, 34, 42, BLACK, name="Block"),
                  circle(-104.0, 30.0, 36.0, BLACK, name="Tree A"), circle(100.0, 26.0, 30.0, BLACK, name="Tree B"))
    v_sun = circle(-6.0, -46.0, 74.0, YEL, name="Sun")
    k_core = node("Vignette (city in the interchange)",
                  v_train_idle, v_water, v_bridge, v_city, v_sun,
                  rect(-R_V, -R_V, 2 * R_V, 2 * R_V, WHITE, name="Sky"),
                  E("ClippingShape", sourceId=v_clip.id, name="Glass clip"), v_clip, x=C[0], y=C[1])
    k_outer = node("Interchange ring",
                   *[E("Shape", E("Ellipse", width=2 * R_V + 18, height=2 * R_V + 18, name="Path"),
                       stroke(col, 16.0, "Arc", "butt", "round",
                              E("TrimPath", start=a0_, end=a1_, modeValue="sequential", name="Arc span")),
                       name=f"Ring arc {k}") for k, (col, a0_, a1_) in
                     enumerate(((RED, 0.0, 0.34), (YEL, 0.34, 0.67), (BLACK, 0.67, 1.0)))],
                   x=C[0], y=C[1], rotation=-0.6)
    k_dots = node("Knot stations", *[station((R_V + 9) * math.cos(a), (R_V + 9) * math.sin(a), 24.0 if k % 2 else 18.0,
                                             name=f"Knot stop {k}")
                                     for k, a in enumerate([j * math.pi / 3 + math.pi / 6 for j in range(6)])])
    k_dots_idle = node("Knot stations (idle turn)", k_dots, x=C[0], y=C[1])
    p0 = node("Emblem: interchange knot", k_dots_idle, k_outer, k_core, *[l[0] for l in k_lines])

    # p1 Scenic Rider: window with passing shapes
    win_clip = E("Shape", E("Rectangle", width=244.0, height=170.0, originX=0.5, originY=0.5, cornerRadiusTL=30.0,
                            name="Path"), x=C[0], y=C[1], name="Window glass (clip source)")
    # three parallax layers seen through the glass: far peaks, blue hills, near
    # catenary poles - each repeats exactly within its idle travel (seamless loop)
    stone = "FFDDD8CB"
    peaks = []
    for k in range(-1, 4):
        ox = 73 + k * 240
        peaks += [path_shape([(ox, 330), (ox + 60, 262), (ox + 96, 300), (ox + 150, 244), (ox + 240, 330)], stone,
                             name=f"Peaks {k}"),
                  path_shape([(ox + 134, 262), (ox + 150, 244), (ox + 168, 264), (ox + 156, 270), (ox + 146, 262)],
                             WHITE, name=f"Snow {k}")]
    far = node("Far peaks", *peaks)
    hills = node("Hills", *[circle(float(40 + k * 200), 392.0, 220.0, DEEP, name=f"Hill {k}", line=BLACK, lw=3.0)
                            for k in range(6)],
                 *[circle(float(140 + k * 200), 404.0, 170.0, BLUE, name=f"Knoll {k}", line=BLACK, lw=3.0)
                   for k in range(6)])
    near = node("Near poles", *[node(f"Pole {k}", rect(-3, -110, 6, 120, BLACK, name="Mast"),
                                     rect(-16, -104, 32, 4, BLACK, name="Arm"), x=float(80 + k * 120), y=390.0)
                                for k in range(16)])
    lake = rect(60, 324, 280, 14, SKY, name="Lake")
    far_i, hills_i, near_i = node("Far peaks (idle)", far), node("Hills (idle)", hills), node("Near poles (idle)", near)
    sun1 = circle(250.0, 248.0, 40.0, RED, name="Sun")
    wire = rect(60, 222, 280, 2, BLACK, name="Catenary")
    glint = path_shape([(140, 212), (176, 212), (110, 380), (74, 380)], "33FFFFFF", name="Glass glint")
    scenery = node("Passing scenery", near_i, hills_i, lake, far_i, x=0.0)
    scenery_idle = node("Window extras", glint, wire, sun1)
    glass = node("Window view", scenery_idle, scenery, rect(73, 211, 244, 170, WHITE, name="Sky"),
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
                  circle(-70.0, 22.0, 12.0, WHITE, name="From", line=BLACK, lw=3.0),
                  circle(70.0, -8.0, 12.0, WHITE, name="To", line=BLACK, lw=3.0),
                  *[rect(-84 + j * 9, 30, 3 if j % 3 else 5, 10, BLACK, name=f"Code bar {j}") for j in range(7)],
                  rect(28, 30, 46, 4, "FFB9B4A8", r=2, name="Print line A"),
                  rect(28, 37, 30, 4, "FFB9B4A8", r=2, name="Print line B"),
                  circle(86.0, 0.0, 10.0, WHITE, name="Punch hole", line=BLACK, lw=2.0),
                  rect(-100, -46, 200, 18, col, r=4, name="Stripe"),
                  rect(-100, -46, 200, 92, "FFFFFFFF", r=8, name="Ticket", line=BLACK, lw=4.0),
                  x=C[0], y=C[1] + 90, rotation=rot)
        tk_idle = node(f"Ticket {k} (idle sway)", tk)
        pivot = node(f"Ticket {k} pivot", tk_idle, y=0.0)
        tickets.append((tk, pivot, rot, tk_idle))
    p2 = node("Emblem: stacked route tickets", *[t[1] for t in reversed(tickets)])
    for tk, pv, rot, ti in tickets:
        # fan around a pivot below the stack: offset each ticket upward along its rotated axis
        ti.attrs["x"] = C[0] + 130 * math.sin(rot)
        ti.attrs["y"] = C[1] + 110 - 130 * math.cos(rot) + 30
        tk.attrs["x"], tk.attrs["y"] = 0.0, 0.0

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
                  rotation=0.785)
    needle_idle = node("Needle (idle drift)", needle, x=C[0], y=C[1])
    p3 = node("Emblem: compass station ring", needle_idle, c_ticks, c_inner, c_ring_shape)

    groups = []
    for p, grp in enumerate((p0, p1, p2, p3)):
        w = node(f"Persona {p} (visible when _personaSlot == {p})", grp, opacity=1.0 if p == 0 else 0.0)
        w.add(bind("_personaSlot", 18, eq_conv(p)))
        groups.append(w)
    PERSONA_GROUPS.extend(groups)

    label = text(24, 532, 342, [(SAMPLE["personaLabel"], "personaLabel")], 16, WHITE, weight=600, h=22,
                 overflow="ellipsis", wrap="noWrap", ink="_personaInk", name="Persona label")
    title = text(22, 556, 346, [(SAMPLE["personaName"], "personaName")], 64, WHITE, display="cond", h=66,
                 overflow="fitFontSize", wrap="noWrap", lh=62, ls=-0.5, valign="bottom", ink="_personaInk",
                 name="Persona title")
    desc = text(24, 630, 342, [(SAMPLE["personaDescription"], "personaDescription")], 20, WHITE, h=54,
                overflow="ellipsis", lh=26, ink="_personaInk", name="Persona description")
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
    # the glass opens elastically and the city slides up into it
    a0.key(k_core, "scaleX", (0, 0.0, "hold"), (64, 0.0, ("el", 1.0, 0.4)), (104, 1.0, "hold"))
    a0.key(k_core, "scaleY", (0, 0.0, "hold"), (64, 0.0, ("el", 1.0, 0.4)), (104, 1.0, "hold"))
    slide(a0, v_city, "y", 70, 74, 106, EO)
    slide(a0, v_sun, "y", 50, 70, 112, EO)
    slide(a0, v_bridge, "y", 40, 80, 108, EO)
    a0.key(k_outer, "scaleX", (0, 0.0, "hold"), (70, 0.0, ("el", 1.0, 0.35)), (110, 1.0, "hold"))
    a0.key(k_outer, "scaleY", (0, 0.0, "hold"), (70, 0.0, ("el", 1.0, 0.35)), (110, 1.0, "hold"))
    a0.key(k_outer, "rotation", (0, -2.4, "hold"), (70, -2.4, EO), (116, -0.6, "hold"))
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
    for k, (tk, pv, rot, ti) in enumerate(tickets):
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

    idle.key(k_dots_idle, "rotation", (0, 0.0, "lin"), (IDLE_FRAMES, math.pi / 3, "lin"))
    idle.key(v_train_idle, "x", (0, -40.0, "lin"), (IDLE_FRAMES, 300.0, "lin"))
    idle.key(far_i, "x", (0, 0.0, "lin"), (IDLE_FRAMES, -240.0, "lin"))
    idle.key(hills_i, "x", (0, 0.0, "lin"), (IDLE_FRAMES, -400.0, "lin"))
    idle.key(near_i, "x", (0, 0.0, "lin"), (IDLE_FRAMES, -1440.0, "lin"))
    for k, (tk, pv, rot, ti) in enumerate(tickets):
        idle.key(ti, "rotation", (0, 0.0, SOFT), (120 + k * 20, 0.03, SOFT), (IDLE_FRAMES, 0.0, "lin"))
    idle.key(needle_idle, "rotation", (0, 0.0, SOFT), (160, 0.075, SOFT), (320, -0.065, SOFT), (IDLE_FRAMES, 0.0, "lin"))
    finish(sc)
    return sc


# ======================================================================
# 10. Summary - collectible ticket card + share
# ======================================================================
def scene10():
    sc = Scene(10, (195, 430), RED)
    ef = sc.anim("EnterFwd", 130)
    eb = sc.anim("EnterBack", 50)
    idle = sc.anim("Idle", IDLE_FRAMES, "loop")

    head = text(24, 92, 342, [(SAMPLE["summaryHeadline"], "summaryHeadline")], 40, WHITE, display="cond", h=50,
                overflow="fitFontSize", wrap="noWrap", lh=46, ls=-0.3, valign="middle", name="Summary headline")
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
    e_head = text(24, 196, 342, [(SAMPLE["emptyHeadline"], "emptyHeadline")], 60, WHITE, display="cond", h=170,
                  overflow="fitFontSize", lh=56, ls=-0.4, valign="bottom", name="Empty headline")
    e_sup = text(24, 380, 342, [(SAMPLE["emptySupport"], "emptySupport")], 20, WHITE, h=52, overflow="ellipsis",
                 lh=26, name="Empty support")
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
