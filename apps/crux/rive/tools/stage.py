"""The Stage artboard: ten scenes, the persistent carrier hold + rope, chalk occluder,
and the scene-sequencing state machine that reads UserRecap.currentScreen."""
import math
from rml import (E, nid, node, shape, poly, ellipse, rect, fill, stroke, solid, bind, Anim,
                 cond_num, cond_bool, cond_trigger, write_num, write_bool, transition,
                 CHALK, COAL, ACID, COBALT, CONCRETE, CONCRETE_D, CHALK_D, COAL_L, RNG)
from art import (N, BASE, text, hero, headline, mono, Hold, Puff, speckles, bolt_grid, route_line,
                 arrow, alpha, WORDMARK_AB, FONT_MONO, FONT_MONO_M, FONT_XB, FONT_BLACK, hold_art,
                 Hold3, hold3d_drawable, chalk_drawable)
import conv
import model
from model import path

W, H = 390, 844
STAGE_AB = "0:70"
STAGE_SM = "0:71"

IN_DUR = 112          # 1.87 s entrance (settles by ~1.8 s)
CONTINUITY = {2: (300, 380, 1.05), 6: (215, 430, 0.85), 8: (198, 520, 1.15)}

CARRIER_POSE = {
    1: (334, 470, 0.9, 0.25), 2: (332, 190, 0.8, -0.15), 3: (322, 612, 1.2, 0.1),
    4: (306, 404, 0.6, 0.3), 5: (195, 626, 1.0, 0.0), 6: (96, 664, 0.85, -0.2),
    7: (348, 446, 0.5, 0.0), 8: (200, 650, 0.95, 0.0), 9: (195, 560, 0.0, 0.0),
    10: (352, 606, 0.55, 0.35),
}

# ------------------------------------------------------------------ globals in the stage
HERO_DRIVER = E("CustomPropertyNumber", propertyValue=0, name="heroDriver",
                kids=[bind(path("heroProgress"), 243, direction=True)])

# Carrier: the persistent acid "Crux hold" that carries the story + the yank rope.
rope_bow = E("CubicMirroredVertex", x=40, y=-520, rotation=-1.5708, distance=260, name="Bow")
rope_path = E("PointsPath", isClosed=False, isClockwise=True, name="Rope Path", kids=[
    E("StraightVertex", x=0, y=-30), rope_bow, E("StraightVertex", x=0, y=-1400)])
rope_twist = E("Stroke", thickness=3, cap="butt", join="round", name="Twist", kids=[
    solid(COBALT), E("DashPath", name="Twist", kids=[E("Dash", length=7, name="On"), E("Dash", length=7, name="Off")])])
ROPE = N("Rope", [shape("Rope Line", [rope_path], [stroke(COAL, 7, cap="round"), rope_twist])], opacity=0.0)
# The carrier is a real 3D hold (hold3d.luau): it tumbles in yaw while it is yanked.
CARRIER_3D, CARRIER_IN = hold3d_drawable("Carrier 3D", "jug", ACID, 96, bolt=0.0, speck=0.45, sway=0.07)
CARRIER_YAW = CARRIER_IN["yaw"].id
ENTRY_YAW = [0.0]   # carrier yaw an entrance starts from (set per entrance by build_stage)
CARRIER_PITCH = CARRIER_IN["pitch"].id
CARRIER_ART = N("Carrier Idle", [shape("Route Dot", [ellipse(15)], [fill(CHALK), stroke(COAL, 3.5)], x=4, y=0),
                                 CARRIER_3D])
CARRIER = N("Carrier", [ROPE, CARRIER_ART], x=CARRIER_POSE[1][0], y=CARRIER_POSE[1][1])


def chalk_cloud():
    rng = RNG(21)
    kids = []
    for i in range(12):
        a = i / 12 * 6.283 + rng.random() * 0.4
        d = 90 + rng.random() * 120
        r = 130 + rng.random() * 90
        kids.append(ellipse(round(r, 1), x=round(math.cos(a) * d, 1), y=round(math.sin(a) * d * 1.5, 1)))
    kids.append(ellipse(330, x=0, y=0))
    shades = [ellipse(round(e.a["width"] * 0.85, 1), x=round(e.a["x"] + 14, 1), y=round(e.a["y"] + 22, 1)) for e in kids]
    grains = speckles("Cloud Grains", 70, -240, -420, 240, 420, color=alpha(COAL, 0.25), seed=22, rmin=1.5, rmax=4)
    return N("Chalk Cloud", [grains, shape("Cloud", kids, [fill(CHALK)]),
                             shape("Cloud Shade", shades, [fill(CHALK_D)])],
             x=195, y=440, opacity=0.0, scaleX=0.35, scaleY=0.35)


CHALK = CHALK  # noqa
# The chalk occluder is a GPU shader (chalk.wgsl) keyed through script inputs.
CHALK_FX, CHALK_IN = chalk_drawable()
CLOUD = CHALK_FX


# ------------------------------------------------------------------ scene scaffold
class Scene:
    def __init__(self, k, bgc):
        self.k = k
        self.text = N("Text")
        self.front = N("Front")
        self.mid = N("Mid")
        self.back = N("Back")
        self.bg_color_id = nid()
        self.wall = shape("Wall", [rect(W, H)], [E("Fill", name="Fill", kids=[
            E("SolidColor", colorValue=bgc, name="Wall Color", id=self.bg_color_id)])], x=W / 2, y=H / 2)
        self.root = N(f"Scene {k}", [self.text, self.front, self.mid, self.back], opacity=0.0)
        self.variants = [0]
        self.variant_nodes = {}
        self.idle = []            # (node_id, prop, amplitude)
        self.hero_steps = [(12, 0.0, "outq"), (72, 1.0, "hold")]
        self.carrier_hook = None

    def choreo(self, a, v):
        pass


def fade_in(a, nid_, f, dur=16, dy=26, base_y=None):
    by = BASE[nid_]["y"] if base_y is None else base_y
    a.k(nid_, "opacity", 0, 0.0)
    a.tw(nid_, "opacity", f, f + dur, 0.0, 1.0, "out")
    if dy:
        a.tw(nid_, "y", f, f + dur + 6, by + dy, by, "out")


def pop(a, nid_, f, dur=14, ease="snap", s0=0.0, s1=None):
    s1 = BASE[nid_]["scaleX"] if s1 is None else s1
    a.tw(nid_, "scaleX", f, f + dur, s0, s1, ease)
    a.tw(nid_, "scaleY", f, f + dur, s0, s1, ease)


def snap_in(a, h, f, dx=260, dy=0, drot=0.8, dur=16):
    """hold flies in and snaps into place with overshoot."""
    a.tw(h.id, "x", f, f + dur, h.x + dx, h.x, "snap")
    a.tw(h.id, "y", f, f + dur, h.y + dy, h.y, "back")
    a.tw(h.id, "rotation", f, f + dur + 4, h.rot + drot, h.rot, "back")
    a.k(h.id, "opacity", 0, 0.0)
    a.k(h.id, "opacity", f, 1.0)


def wrap_text(t, name=None):
    n = N(name or (t.a.get("name", "T") + " Group"), [t])
    return n


def steps_curve(frames, ease="outq"):
    n = len(frames) - 1
    out = []
    for i, f in enumerate(frames):
        out.append((f, i / n, ease if i < n else "hold"))
    return out


# ------------------------------------------------------------------ scenes
def scene1():
    s = Scene(1, CHALK)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=101))
    s.back.add(bolt_grid("Bolts", [(250 + (i % 4) * 36, 330 + (i // 4) * 44) for i in range(40) if (250 + (i % 4) * 36) > 240 - (i // 4) * 8]))
    s.back.add(shape("Panel", [poly([(214, 300), (390, 240), (390, 844), (140, 844)])], [fill(CONCRETE)]))
    # zigzag route through oversized holds
    h1 = Hold3("Sloper", "sloper", COBALT, 236, 92, 784, rot=-0.1, scene=1, sway=0.05)
    h2 = Hold3("Pyramid", "pyramid", COAL, 156, 296, 684, rot=0.15, scene=1, sway=0.06, speck=0.12)
    pts = [(95, 790), (296, 688), (115, 605), (334, 470)]
    rl, trim = route_line("Route", pts, COAL, 3.5)
    dots = [shape(f"Dot {i}", [ellipse(14)], [fill(CHALK), stroke(COAL, 3.5)], x=x, y=y) for i, (x, y) in enumerate(pts[:3])]
    dotn = [N(f"Route Dot {i}", [d], x=0, y=0) for i, d in enumerate(dots)]
    s.mid.add(dotn, rl, h2.outer, h1.outer)
    # signature interaction: draggable acid hold (squash node keyed by GrabHold layer)
    # the 3D hold draws itself; a transparent cut-out of its silhouette is the hit region
    grab_d, grab_in = hold3d_drawable("Grab Hold 3D", "jug", ACID, 104, scene=1, sway=0.05)
    s.grab_yaw, s.grab_pitch = grab_in["yaw"].id, grab_in["pitch"].id
    hit = shape("Body", [poly([(x * 120, y * 120) for x, y in
                               [(-0.6, 0.14), (-0.4, -0.38), (0.4, -0.38), (0.62, 0.14), (0.24, 0.38), (-0.24, 0.38)]])],
                [fill("00000000")])
    s.grab_target = hit.id
    s.grab_squash = N("Grab Squash", [hit, grab_d])
    s.grab_hold = N("Grab Hold", [s.grab_squash])
    s.grab_slot = N("Grab Slot", [s.grab_hold], x=115, y=605)
    s.front.add(s.grab_slot)
    s.grab_home = (115, 605)
    # text
    s.wm_clip_rect = N("Wordmark Mask Grow", [shape("Mask Shape", [rect(272, 112, ox=0, oy=0)], [])], x=22, y=118,
                       scaleX=0.0)
    wm_leaf = E("NestedArtboard", artboardId=WORDMARK_AB, x=0, y=0, scaleX=1.6, scaleY=1.6, name="Wordmark")
    s.wm = N("Wordmark Reveal", [wm_leaf, E("ClippingShape", sourceId=s.wm_clip_rect.kids[0].id, name="Reveal Clip")],
             x=24, y=130)
    greet = text("Greeting", 0, 0, 342, 40, FONT_MONO_M, 14, COAL,
                 [("Alex", "userName", None), ("  ·  ", None, None), ("", "periodLabel", None)],
                 overflow="ellipsis", lh=19)
    s.greet = N("Greeting Group", [greet], x=24, y=238)
    s.head = N("Headline Group", [headline("Intro Headline", "introHeadline", 0, 0, 300, 132, 64, COAL)], x=24, y=280)
    s.sup = N("Support Group", [mono("Intro Support", "introSupport", 0, 0, 250, 46, 15, COAL)], x=24, y=420)
    s.text.add(s.wm_clip_rect, s.wm, s.greet, s.head, s.sup)
    s.p = [Puff("Puff A", 95, 760, 70, 3), Puff("Puff B", 296, 700, 55, 4), Puff("Puff C", 334, 490, 60, 5)]
    s.front.add([p.outer for p in s.p])
    s.idle = [(h1.idle.id, "rotation", 0.03), (h2.idle.id, "rotation", -0.04)]

    def choreo(a, v):
        pop(a, h1.id, 6, 16, "back")
        a.tw(h1.yaw, 243, 6, 30, 1.6, 0.0, "back")
        a.tw(h1.pitch, 243, 6, 30, 0.7, 0.0, "back")
        s.p[0].fire(a, 12)
        a.tw(trim, "end", 10, 64, 0.0, 1.0, "inout")
        pop(a, h2.id, 22, 16, "snap")
        a.tw(h2.yaw, 243, 22, 44, -2.2, 0.0, "back")
        s.p[1].fire(a, 28)
        for i, d in enumerate(dotn):
            pop(a, d.id, 12 + i * 14, 10, "snap")
        pop(a, s.grab_slot.id, 34, 16, "snap")
        a.tw(s.grab_yaw, 243, 34, 58, 2.6, 0.0, "back")
        s.p[2].fire(a, 50)
        a.tw(s.wm_clip_rect.id, "scaleX", 40, 74, 0.0, 1.0, "inout")
        a.tw(s.wm.id, "y", 40, 74, 150, 130, "out")
        fade_in(a, s.greet.id, 58)
        fade_in(a, s.head.id, 64, 20, 34)
        fade_in(a, s.sup.id, 78)
    s.choreo = choreo
    s.carrier_t = (40, 66)
    return s


def scene2():
    s = Scene(2, CHALK)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=102))
    s.back.add(bolt_grid("Bolts", [(330 + (i % 2) * 34, 400 + (i // 2) * 46) for i in range(18)]))
    s.back.add(shape("Concrete", [poly([(390, 300), (390, 844), (200, 844)])], [fill(CONCRETE)]))
    hs = [Hold3("Sloper", "sloper", COBALT, 262, 250, 796, -0.05, scene=2, sway=0.04),
          Hold3("Acid Tri", "tri", ACID, 128, 222, 636, -0.2, scene=2, sway=0.06),
          Hold3("Coal Pyramid", "pyramid", COAL, 164, 306, 500, 0.1, scene=2, sway=0.05, speck=0.12),
          Hold3("Cobalt Tri", "tri", COBALT, 100, 304, 352, 0.25, scene=2, sway=0.07)]
    pts = [(248, 790), (222, 640), (306, 505), (304, 356), (332, 190)]
    rl, trim = route_line("Route", pts, COAL, 3.0)
    dots = [N(f"Dot {i}", [shape("Dot", [ellipse(14)], [fill(CHALK), stroke(COAL, 3.5)])], x=x, y=y)
            for i, (x, y) in enumerate(pts[:4])]
    s.mid.add(dots, rl, [h.outer for h in reversed(hs)])
    s.p = [Puff(f"Puff {i}", h.x, h.y + 10, 46 + i * 4, 30 + i) for i, h in enumerate(hs)]
    s.front.add([p.outer for p in s.p])
    num = N("Hero", [hero("Sessions", "sessionsDisplay", 0, 0, 268, 214, 236, COAL)], x=20, y=112)
    unit = N("Unit", [mono("Unit", "screen2Unit", 0, 0, 260, 26, 18, COAL, medium=True)], x=24, y=334)
    hd = N("Headline", [headline("Headline", "screen2Headline", 0, 0, 214, 122, 58, COAL)], x=22, y=372)
    sp = N("Support", [mono("Support", "screen2Support", 0, 0, 196, 80, 14, COAL, overflow="ellipsis")], x=24, y=506)
    s.text.add(num, unit, hd, sp)
    frames = [12, 24, 36, 48, 60, 72]
    s.hero_steps = steps_curve(frames)
    s.idle = [(h.idle.id, "rotation", 0.025 * (1 if i % 2 else -1)) for i, h in enumerate(hs)]

    def choreo(a, v):
        for i, h in enumerate(hs):
            snap_in(a, h, frames[i], dx=240, dy=-40, drot=0.9 if i % 2 else -0.7)
            # each hold spins on its bolt as it snaps onto the wall
            a.tw(h.yaw, 243, frames[i], frames[i] + 20, 2.8 if i % 2 else -2.4, 0.0, "back")
            a.tw(h.pitch, 243, frames[i], frames[i] + 20, -0.6, 0.0, "out")
            s.p[i].fire(a, frames[i] + 10)
            pop(a, dots[i].id, frames[i] + 8, 10, "snap")
        a.tw(trim, "end", 12, 76, 0.0, 1.0, "soft")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 12, 1.0)
        a.tw(num.id, "y", 12, 30, 140, 112, "back")
        fade_in(a, unit.id, 30, 14, 12)
        fade_in(a, hd.id, 72, 18, 30)
        fade_in(a, sp.id, 86, 16, 18)
    s.choreo = choreo
    s.carrier_t = (54, 76)
    return s


def scene3():
    s = Scene(3, COAL)
    s.back.add(speckles("Speckle", 70, 0, 60, 390, 844, color=alpha(CHALK, 0.25), seed=103))
    s.back.add(bolt_grid("Bolts", [(30 + (i % 8) * 47, 90 + (i // 8) * 52) for i in range(8 * 15)], color=COAL_L))
    pts = [(30, 772), (116, 690), (74, 606), (194, 640), (232, 548), (322, 612)]
    rl, trim = route_line("Trace", pts, ACID, 10, dash=None)
    kinds = [("crimp", CHALK), ("pinch", COBALT), ("tri", CHALK), ("jug", COBALT), ("pinch", CHALK)]
    hs = [Hold3(f"Hold {i}", k, c, 78 + (i % 2) * 12, x, y, 0.2 * (i - 2), scene=3, sway=0.08, speck=0.4)
          for i, ((k, c), (x, y)) in enumerate(zip(kinds, pts[:5]))]
    # finish stamp (checkered badge)
    cells = []
    for i in range(3):
        for j in range(3):
            if (i + j) % 2 == 0:
                cells.append(rect(16, 16, x=-16 + i * 16, y=-16 + j * 16))
    stamp = N("Finish Stamp", [
        shape("Checks", cells, [fill(COAL)]),
        shape("Badge", [rect(62, 62, r=6)], [fill(CHALK), stroke(ACID, 5)]),
    ], x=318, y=528, rotation=0.22)
    s.stamp = stamp
    s.mid.add(stamp, [h.outer for h in hs], rl)
    s.p = [Puff("Stamp Puff", 318, 540, 70, 50, CHALK)]
    s.front.add(s.p[0].outer)
    num = N("Hero", [hero("Sends", "sendsDisplay", 0, 0, 342, 224, 250, CHALK, align="center")], x=24, y=110)
    unit = N("Unit", [mono("Unit", "screen3Unit", 0, 0, 342, 26, 18, ACID, align="center", medium=True)], x=24, y=336)
    hd = N("Headline", [headline("Headline", "screen3Headline", 0, 0, 342, 64, 56, CHALK, align="center")], x=24, y=372)
    sp = N("Support", [mono("Support", "screen3Support", 0, 0, 300, 60, 14, CHALK, align="center")], x=45, y=440)
    s.text.add(num, unit, hd, sp)
    frames = [10, 22, 34, 46, 58, 70]
    s.hero_steps = steps_curve(frames)
    s.idle = [(h.idle.id, "rotation", 0.03 * (1 if i % 2 else -1)) for i, h in enumerate(hs)]

    def choreo(a, v):
        for i, h in enumerate(hs):
            pop(a, h.id, 8 + i * 9, 12, "snap")
            a.tw(h.yaw, 243, 8 + i * 9, 30 + i * 9, -2.4 if i % 2 else 2.0, 0.0, "back")
        a.tw(trim, "end", 14, 70, 0.0, 1.0, "inout")
        a.k(stamp.id, "opacity", 0, 0.0)
        a.k(stamp.id, "opacity", 70, 1.0)
        a.tw(stamp.id, "scaleX", 70, 84, 2.4, 1.0, "punch")
        a.tw(stamp.id, "scaleY", 70, 84, 2.4, 1.0, "punch")
        a.tw(stamp.id, "rotation", 70, 86, -0.7, 0.22, "back")
        s.p[0].fire(a, 74, 24, 1.4)
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 10, 1.0)
        pop(a, num.id, 10, 18, "back", s0=0.86, s1=1.0)
        fade_in(a, unit.id, 28, 14, 10)
        fade_in(a, hd.id, 76, 18, 26)
        fade_in(a, sp.id, 88, 16, 16)
    s.choreo = choreo
    s.carrier_t = (40, 72)
    return s


def scene4():
    s = Scene(4, CHALK)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=104))
    # tick scale
    ticks = [rect(10 if i % 3 else 18, 2, x=352 - (0 if i % 3 else 4), y=780 - i * 30) for i in range(13)]
    s.back.add(shape("Scale", ticks + [rect(2, 372, x=358, y=600)], [fill(alpha(COAL, 0.6))]))
    # kinetic stack: one real 3D sloper drawn as a solid anchor, a tumbling trail of
    # translucent ghosts and a solid head that climbs with the count (hold3d trail mode)
    stack_d, stack_in = hold3d_drawable("Attempt Stack 3D", "sloper", COBALT, 170, scene=4, sway=0.05, speck=0.45,
                                        extent=3.35, trail={"copies": 12, "progress": 0.0, "trailX": 1.94,
                                                            "trailY": 3.53, "trailWave": 0.7, "trailSpin": 2.6,
                                                            "trailShrink": 0.6, "ghost": 0.42, "extentW": 3.25})
    stack = N("Attempt Stack", [stack_d], x=150, y=780, rotation=0.0)
    s.stack_progress = stack_in["progress"].id
    s.stack_yaw = stack_in["yaw"].id
    sw_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Swoosh Reveal")
    swoosh = shape("Swoosh", [ellipse(300, 96)], [E("Stroke", thickness=4, cap="round", name="Stroke", kids=[solid(ACID), sw_trim])],
                   x=235, y=650, rotation=-0.42)
    marks = []
    rng = RNG(44)
    for i in range(14):
        x = 40 + rng.random() * 300
        y = 560 + rng.random() * 240
        m = shape(f"Mark {i}", [poly([(-6, -6), (6, 6)], closed=False), poly([(6, -6), (-6, 6)], closed=False)],
                  [stroke(COAL, 2.6, cap="round")])
        marks.append(N(f"Attempt {i}", [m], x=round(x, 1), y=round(y, 1), rotation=round(rng.random(), 2)))
    s.mid.add(marks, swoosh, stack)
    num = N("Hero", [hero("Attempts", "attemptsDisplay", 0, 0, 346, 206, 230, COAL)], x=20, y=112)
    unit = N("Unit", [mono("Unit", "screen4Unit", 0, 0, 260, 26, 18, COAL, medium=True)], x=24, y=328)
    hd = N("Headline", [headline("Headline", "screen4Headline", 0, 0, 200, 122, 58, COAL)], x=22, y=366)
    sp = N("Support", [mono("Support", "screen4Support", 0, 0, 186, 80, 14, COAL)], x=24, y=500)
    s.text.add(num, unit, hd, sp)
    s.idle = []
    s.hero_steps = [(12, 0.0, "inq"), (64, 0.86, "out"), (78, 1.0, "hold")]

    def choreo(a, v):
        # the trail grows in step with the counter, then the whole stack twists home
        a.k(s.stack_progress, 243, 0, 0.0)
        a.k(s.stack_progress, 243, 10, 0.0, "inq")
        a.k(s.stack_progress, 243, 64, 0.86, "out")
        a.k(s.stack_progress, 243, 78, 1.0)
        a.tw(s.stack_yaw, 243, 8, 90, -1.4, 0.0, "soft")
        a.k(stack.id, "opacity", 0, 0.0)
        a.tw(stack.id, "opacity", 6, 14, 0.0, 1.0, "out")
        a.tw(stack.id, "y", 6, 26, 860, 780, "back")
        a.tw(sw_trim, "end", 30, 80, 0.0, 1.0, "inout")
        for i, m in enumerate(marks):
            f = 12 + i * 3
            b = BASE[m.id]
            a.k(m.id, "opacity", 0, 0.0)
            a.k(m.id, "opacity", f, 1.0)
            a.tw(m.id, "y", f, f + 12, b["y"] - 120, b["y"], "back")
            a.tw(m.id, "rotation", f, f + 12, b["rotation"] + 2, b["rotation"], "out")
            # resolve: marks fly into the number
            a.tw(m.id, "x", 62 + i, 76 + i // 2, b["x"], 120 + (i % 5) * 40, "in")
            a.tw(m.id, "y", 62 + i, 76 + i // 2, b["y"], 230, "in")
            a.k(m.id, "opacity", 76 + i // 2, 0.0)
            a.tw(m.id, "scaleX", 62 + i, 76 + i // 2, 1.0, 0.3, "in")
            a.tw(m.id, "scaleY", 62 + i, 76 + i // 2, 1.0, 0.3, "in")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 12, 1.0)
        a.tw(num.id, "y", 12, 28, 134, 112, "out")
        a.k(num.id, "scaleX", 0, 1.0)
        a.k(num.id, "scaleY", 0, 1.0)
        a.tw(num.id, "scaleX", 78, 92, 1.05, 1.0, "back")
        a.tw(num.id, "scaleY", 78, 92, 1.05, 1.0, "back")
        fade_in(a, unit.id, 30, 14, 10)
        fade_in(a, hd.id, 76, 18, 30)
        fade_in(a, sp.id, 88, 16, 16)
    s.choreo = choreo
    s.carrier_t = (60, 84)
    return s


def scene5():
    s = Scene(5, COBALT)
    s.back.add(speckles("Speckle", 80, 0, 60, 390, 844, color=alpha(CHALK, 0.3), seed=105))
    s.back.add(shape("Rings", [ellipse(260, x=70, y=180), ellipse(180, x=70, y=180)], [stroke(alpha(CHALK, 0.18), 2)]))
    lvl_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Align Reveal")
    level = shape("Level Line", [poly([(24, 664), (366, 664)], closed=False)],
                  [E("Stroke", thickness=3, cap="square", name="Stroke", kids=[solid(CHALK), lvl_trim])])
    guide_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Guide Reveal")
    guide = shape("Guide", [poly([(40, 586), (350, 586)], closed=False)],
                  [E("Stroke", thickness=2, cap="butt", name="Stroke", kids=[solid(ACID), guide_trim,
                   E("DashPath", name="Dash", kids=[E("Dash", length=8, name="On"), E("Dash", length=6, name="Off")])])])
    hl = Hold3("Crimp", "crimp", CHALK, 140, 84, 636, 0.0, scene=5, sway=0.05)
    hr = Hold3("Pinch", "pinch", COAL, 116, 304, 632, 0.0, scene=5, sway=0.05, speck=0.12)
    bubble = N("Bubble", [shape("Bubble", [ellipse(18)], [fill(ACID)])], x=195, y=712)
    vial = shape("Vial", [rect(110, 26, r=13)], [stroke(CHALK, 3)], x=195, y=712)
    s.mid.add(bubble, vial, guide, level, hr.outer, hl.outer)
    num = N("Hero", [hero("Technique", "techniqueSessionsDisplay", 0, 0, 342, 220, 240, CHALK, align="right")], x=24, y=110)
    unit = N("Unit", [mono("Unit", "screen5Unit", 0, 0, 342, 26, 18, ACID, align="right", medium=True)], x=24, y=334)
    hd = N("Headline", [headline("Headline", "screen5Headline", 0, 0, 300, 122, 58, CHALK)], x=22, y=380)
    sp = N("Support", [mono("Support", "screen5Support", 0, 0, 300, 60, 14, CHALK)], x=24, y=512)
    s.text.add(num, unit, hd, sp)
    s.hero_steps = [(14, 0.0, "outq"), (40, 0.34, "outq"), (54, 0.67, "outq"), (68, 1.0, "hold")]
    s.idle = [(hl.idle.id, "rotation", 0.02), (hr.idle.id, "rotation", -0.02)]

    def choreo(a, v):
        # three articulated holds tumble in 3D and rotate into one shared alignment
        for h, f, r0, dy, yw, pt in [(hl, 14, 1.5, -220, 2.9, 1.1), (hr, 30, 2.3, -260, -3.1, -0.9)]:
            a.k(h.id, "opacity", 0, 0.0)
            a.k(h.id, "opacity", f, 1.0)
            a.tw(h.id, "y", f, f + 16, h.y + dy, h.y, "back")
            a.tw(h.id, "rotation", f, f + 30, r0, 0.0, "back")
            a.tw(h.yaw, 243, f, f + 44, yw, 0.0, "back")
            a.tw(h.pitch, 243, f, f + 40, pt, 0.0, "back")
        a.tw(lvl_trim, "end", 6, 36, 0.0, 1.0, "inout")
        a.tw(guide_trim, "end", 66, 90, 0.0, 1.0, "out")
        a.tw(bubble.id, "x", 10, 94, 150, 195, "back")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 14, 1.0)
        a.tw(num.id, "x", 14, 34, 64, 24, "back")
        fade_in(a, unit.id, 32, 14, 10)
        fade_in(a, hd.id, 74, 18, 30)
        fade_in(a, sp.id, 88, 16, 16)

    def carrier_hook(a, sx, sy, ss, sr):
        # the carrier is the middle articulated hold: it rotates into alignment too
        a.tw(CARRIER.id, "x", 0, 24, sx, 195, "inout")
        a.tw(CARRIER.id, "y", 0, 24, sy, 500, "out")
        a.tw(CARRIER.id, "y", 24, 44, 500, 626, "back")
        a.tw(CARRIER.id, "scaleX", 0, 24, ss, 1.0, "out")
        a.tw(CARRIER.id, "scaleY", 0, 24, ss, 1.0, "out")
        a.tw(CARRIER.id, "rotation", 0, 52, -1.9, 0.0, "back")
        a.tw(CARRIER_YAW, 243, 0, 60, ENTRY_YAW[0] - 1.0, 0.0, "back")
        a.tw(CARRIER_PITCH, 243, 0, 56, 1.0, 0.0, "back")
    s.carrier_hook = carrier_hook
    s.choreo = choreo
    return s


def scene6():
    s = Scene(6, CHALK)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=106))
    cx, cy = 195, 318
    ring_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Dial Reveal")
    ring = shape("Dial Ring", [ellipse(296)], [E("Stroke", thickness=14, cap="butt", name="Stroke", kids=[solid(COAL), ring_trim])],
                 rotation=-1.5708)
    minor = [rect(2, 9, x=round(math.cos(i / 60 * 6.283) * 132, 1), y=round(math.sin(i / 60 * 6.283) * 132, 1),
                  rot=round(i / 60 * 6.283 + 1.5708, 3)) for i in range(60) if i % 5]
    major = [rect(4, 18, x=round(math.cos(i / 12 * 6.283) * 128, 1), y=round(math.sin(i / 12 * 6.283) * 128, 1),
                  rot=round(i / 12 * 6.283 + 1.5708, 3)) for i in range(12)]
    ticks = N("Ticks", [shape("Major", major, [fill(COAL)]), shape("Minor", minor, [fill(alpha(COAL, 0.5))])])
    rope_conv = conv.formula("Minutes Arc", conv.clamp01([("in",), ("op", "/"), ("v", 180)]) + [("op", "*"), ("b", "heroProgress")])
    arc_trims = []
    arcs = []
    for nm, col, th, dash in [("Rope Twist", "FF2440B8", 16, True), ("Rope", COBALT, 18, False)]:
        tr = E("TrimPath", start=0, end=0.5, offset=0, modeValue="sequential", name="Arc",
               kids=[bind(path("longestSessionMinutes"), 115, rope_conv)])
        eff = [tr]
        if dash:
            eff.append(E("DashPath", name="Twist", kids=[E("Dash", length=5, name="On"), E("Dash", length=9, name="Off")]))
        arcs.append(shape(nm, [ellipse(344)], [E("Stroke", thickness=th, cap="round", name="Stroke", kids=[solid(col)] + eff)],
                          rotation=-1.5708))
    dial = N("Dial", [arcs[0], arcs[1], ticks, ring], x=cx, y=cy)
    coil_rings = [shape(f"Coil {i}", [ellipse(124, 46)], [stroke(COBALT, 10)], x=0, y=-i * 13) for i in range(4)]
    coil = N("Coil", coil_rings[::-1], x=304, y=690)
    # floor: the rope bag sits on a concrete ledge, its slack running to the carrier hold
    s.back.add(shape("Floor", [poly([(0, 652), (390, 618), (390, 844), (0, 844)])], [fill(CONCRETE)]))
    s.back.add(bolt_grid("Floor Bolts", [(36 + (i % 8) * 46, 690 + (i // 8) * 40) for i in range(16)]))
    slack_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Slack Reveal")
    slack = shape("Slack", [poly([(262, 700), (214, 724), (160, 712), (112, 682)], closed=False)],
                  [E("Stroke", thickness=12, cap="round", join="round", name="Rope", kids=[solid(COBALT), slack_trim])])
    s.mid.add(dial, coil, slack)
    num = N("Hero", [hero("Minutes", "longestSessionMinutesDisplay", 0, 0, 220, 150, 160, COAL, align="center")], x=85, y=208)
    unit = N("Unit", [mono("Unit", "screen6Unit", 0, 0, 220, 26, 16, COAL, align="center", medium=True)], x=85, y=362)
    hd = N("Headline", [headline("Headline", "screen6Headline", 0, 0, 342, 60, 54, COAL)], x=22, y=490)
    sp = N("Support", [mono("Support", "screen6Support", 0, 0, 300, 44, 14, COAL)], x=24, y=548)
    s.text.add(num, unit, hd, sp)
    s.hero_steps = [(12, 0.0, "inout"), (74, 1.0, "hold")]
    s.idle = [(coil.id, "rotation", 0.0)]

    def choreo(a, v):
        a.tw(ring_trim, "end", 4, 40, 0.0, 1.0, "inout")
        pop(a, ticks.id, 18, 18, "back", s0=0.6)
        a.k(ticks.id, "opacity", 0, 0.0)
        a.tw(ticks.id, "opacity", 18, 30, 0.0, 1.0, "out")
        a.tw(dial.id, "rotation", 4, 50, -0.5, 0.0, "back")
        a.tw(slack_trim, "end", 6, 40, 0.0, 1.0, "out")
        a.tw(coil.id, "scaleX", 12, 74, 1.0, 0.55, "inout")
        a.tw(coil.id, "scaleY", 12, 74, 1.0, 0.55, "inout")
        a.tw(coil.id, "rotation", 12, 74, 0.0, 0.4, "inout")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 12, 1.0)
        pop(a, num.id, 12, 16, "back", s0=0.7, s1=1.0)
        fade_in(a, unit.id, 28, 14, 8)
        fade_in(a, hd.id, 74, 18, 28)
        fade_in(a, sp.id, 88, 16, 14)
    s.choreo = choreo
    return s


def scene7():
    s = Scene(7, ACID)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, color=alpha(COAL, 0.22), seed=107))
    # extruded wall panels: a coal face, a lit chalk cap and a shaded side, one per 4 weeks
    base_y = 722
    panels = []
    outlines = []
    for k in range(1, 14):
        x = 28 + (k - 1) * 25.6
        h = 58 + 17 * (k - 1)
        c = conv.scaled_progress(4, 4 * (k - 1), f"Weeks Panel {k}")
        side = shape("Side", [poly([(20, 0), (27, -7), (27, -h - 7), (20, -h)])], [fill(COAL_L)])
        cap = shape("Cap", [poly([(0, -h), (7, -h - 7), (27, -h - 7), (20, -h)])], [fill(CHALK)])
        face = shape("Face", [rect(20, h, ox=0, oy=1)], [fill(COAL)])
        pnode = E("Node", x=round(x, 1), y=base_y, name=f"Panel {k} Fill")
        pnode.add(cap, face, side)
        pnode.add(bind(path("activeWeeks"), 17, c))
        panels.append(pnode)
        outlines.append(poly([(x, base_y), (x, base_y - h), (x + 7, base_y - h - 7), (x + 27, base_y - h - 7),
                              (x + 27, base_y - 7), (x + 20, base_y), (x, base_y)], closed=False))
        outlines.append(poly([(x, base_y - h), (x + 20, base_y - h), (x + 27, base_y - h - 7)], closed=False))
        outlines.append(poly([(x + 20, base_y - h), (x + 20, base_y)], closed=False))
    outl = N("Panel Outlines", [shape("Outlines", outlines, [stroke(alpha(COAL, 0.7), 1.5, join="miter")], y=-base_y)],
             x=0, y=base_y)
    ground = shape("Ground", [rect(390, 4, x=195, y=base_y + 2)], [fill(COAL)])
    ascent = N("Ascent", panels + [outl, ground], x=0, y=0)
    s.ascent = ascent
    s.mid.add(ascent)
    num = N("Hero", [hero("Weeks", "activeWeeksDisplay", 0, 0, 300, 220, 240, COAL)], x=20, y=110)
    unit = N("Unit", [mono("Unit", "screen7Unit", 0, 0, 260, 26, 18, COAL, medium=True)], x=24, y=334)
    hd = N("Headline", [headline("Headline", "screen7Headline", 0, 0, 214, 122, 58, COAL)], x=22, y=370)
    sp = N("Support", [mono("Support", "screen7Support", 0, 0, 196, 60, 14, COAL)], x=24, y=500)
    s.text.add(num, unit, hd, sp)
    s.hero_steps = [(14, 0.0, "inout"), (80, 1.0, "hold")]

    def choreo(a, v):
        a.tw(ascent.id, "y", 8, 84, 120, 0.0, "inout")
        a.tw(ascent.id, "scaleX", 8, 84, 1.12, 1.0, "inout")
        a.tw(ascent.id, "scaleY", 8, 84, 1.12, 1.0, "inout")
        a.tw(outl.id, "scaleY", 4, 30, 0.0, 1.0, "out")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 14, 1.0)
        a.tw(num.id, "y", 14, 32, 150, 110, "back")
        fade_in(a, unit.id, 30, 14, 10)
        fade_in(a, hd.id, 78, 18, 30)
        fade_in(a, sp.id, 90, 16, 16)
    s.choreo = choreo
    return s


def scene8():
    s = Scene(8, CHALK)
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=108))
    hub = (200, 650)
    K = [(48, 612), (116, 566), (238, 562), (322, 584), (354, 650), (334, 716), (262, 734),
         (176, 738), (96, 722), (40, 676), (350, 512), (128, 648)]
    spokes, rings, knots = [], [], []
    for i, (x, y) in enumerate(K):
        k = i + 1
        vis = conv.step_visible(k - 1, f"Partner >= {k}")
        tr = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Join")
        sp_ = E("Shape", name=f"Spoke {k}")
        sp_.add(poly([hub, (x, y)], closed=False), E("Stroke", thickness=2.5, cap="round", name="Stroke", kids=[solid(COAL), tr]))
        sp_.add(bind(path("climbingPartners"), 18, vis))
        spokes.append((sp_, tr))
        if k < len(K):
            nx, ny = K[i + 1]
            rv = conv.step_visible(k, f"Partner >= {k + 1}")
            rtr = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Join")
            rs = E("Shape", name=f"Web {k}")
            rs.add(poly([(x, y), (nx, ny)], closed=False), E("Stroke", thickness=2, cap="butt", name="Stroke", kids=[
                solid(alpha(COAL, 0.55)), rtr, E("DashPath", name="Dash", kids=[E("Dash", length=5, name="On"), E("Dash", length=5, name="Off")])]))
            rs.add(bind(path("climbingPartners"), 18, rv))
            rings.append((rs, rtr))
        col = [COBALT, ACID, COAL][i % 3]
        art = [shape("Loop A", [ellipse(20, x=0, y=-7)], [stroke(COAL, 3.5)]),
               shape("Loop B", [ellipse(20, x=0, y=7)], [stroke(COAL, 3.5)]),
               shape("Core", [ellipse(30)], [fill(col), stroke(CHALK, 3)])]
        inner = N(f"Knot {k} Pop", art)
        outer = N(f"Knot {k}", [inner], x=x, y=y)
        outer.add(bind(path("climbingPartners"), 18, vis))
        knots.append((outer, inner))
    s.mid.add([o for o, _ in knots], [sh for sh, _ in spokes], [sh for sh, _ in rings])
    num = N("Hero", [hero("Partners", "climbingPartnersDisplay", 0, 0, 270, 220, 240, COAL)], x=20, y=110)
    unit = N("Unit", [mono("Unit", "screen8Unit", 0, 0, 300, 26, 18, COAL, medium=True)], x=24, y=334)
    hd = N("Headline", [headline("Headline", "screen8Headline", 0, 0, 290, 122, 54, COAL)], x=22, y=370)
    sp = N("Support", [mono("Support", "screen8Support", 0, 0, 260, 60, 14, COAL)], x=24, y=500)
    s.text.add(num, unit, hd, sp)
    s.hero_steps = [(12, 0.0, "outq"), (70, 1.0, "hold")]
    s.idle = [(inner.id, "rotation", 0.06 * (1 if i % 2 else -1)) for i, (_, inner) in enumerate(knots[::2])]

    def choreo(a, v):
        for i, ((o, inner), (sp_, tr)) in enumerate(zip(knots, spokes)):
            f = 12 + i * 4
            a.tw(tr.id, "end", f, f + 14, 0.0, 1.0, "out")
            pop(a, inner.id, f + 8, 12, "snap")
        for i, (rs, rtr) in enumerate(rings):
            f = 44 + i * 3
            a.tw(rtr.id, "end", f, f + 12, 0.0, 1.0, "inout")
        a.k(num.id, "opacity", 0, 0.0)
        a.k(num.id, "opacity", 12, 1.0)
        a.tw(num.id, "y", 12, 30, 140, 110, "back")
        fade_in(a, unit.id, 30, 14, 10)
        fade_in(a, hd.id, 74, 18, 30)
        fade_in(a, sp.id, 88, 16, 16)
    s.choreo = choreo
    s.carrier_t = (0, 22)
    return s


def scene9():
    s = Scene(9, CHALK)
    s.variants = [0, 1, 2, 3]
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, color=alpha(COAL, 0.25), seed=109))
    ink = {}

    def persona_text(nm, x, y, w, h, font, size, prop, lh):
        t = text(nm, 0, 0, w, h, font, size, COAL, [("", prop, None)], overflow="fitFontSize" if font == FONT_XB else "ellipsis",
                 lh=lh, ls=-0.5 if font == FONT_XB else None)
        ink[nm] = t.ink
        return N(nm + " Group", [t], x=x, y=y)
    lbl = persona_text("Persona Label", 24, 118, 342, 24, FONT_MONO_M, 15, "personaLabel", 20)
    ttl = persona_text("Persona Title", 22, 146, 346, 168, FONT_XB, 88, "personaName", 78)
    dsc = persona_text("Persona Line", 24, 322, 330, 52, FONT_MONO, 17, "personaDescription", 24)
    s.text.add(lbl, ttl, dsc)
    # anticipation scribble shared by every persona
    ant_pts = [(110, 640), (250, 600), (130, 560), (270, 520), (160, 480)]
    ant, ant_trim = route_line("Anticipation", ant_pts, COAL, 4, dash=(10, 6))
    s.ant = N("Anticipation Route", [ant])
    s.front.add(s.ant)

    def accent(geom, x, y, **kw):
        sc_id = nid()
        sh = E("Shape", x=x, y=y, name="Accent", rotation=kw.get("rot"))
        sh.add(geom, E("Fill", name="Fill", kids=[E("SolidColor", colorValue=COAL, name="Accent", id=sc_id,
                                                    kids=[bind(path("personaColor"), 37)])]))
        return sh
    groups = {}
    # ---- 0: Route Reader - route diagram on a diamond map
    p0_holds = [Hold(f"R Hold {i}", kd, c, sz, x, y, r, 90 + i, outline=CHALK)
                for i, (kd, c, sz, x, y, r) in enumerate([("pinch", ACID, 54, 120, 720, 0.2), ("tri", COBALT, 50, 250, 668, -0.3),
                                                          ("crimp", CHALK, 60, 150, 600, 0.1), ("jug", ACID, 50, 262, 540, 0.0),
                                                          ("pinch", COBALT, 44, 196, 476, 0.4)])]
    p0_route, p0_trim = route_line("Reader Route", [(120, 720), (250, 668), (150, 600), (262, 540), (196, 476)], CHALK, 4, dash=(10, 7))
    lens = N("Lens", [shape("Lens", [ellipse(52)], [stroke(ACID, 4)]), shape("Lens Handle", [poly([(18, 18), (34, 34)], closed=False)], [stroke(ACID, 5, cap="round")])],
             x=120, y=720)
    p0_panel = N("Map", [accent(rect(300, 300, r=18), 0, 0, rot=0.785)], x=195, y=610)
    g0 = N("Persona Route Reader", [lens, p0_route, [h.outer for h in p0_holds], p0_panel])
    groups[0] = g0
    # ---- 1: Power Mover - angular lightning hold
    bolt = N("Bolt", [N("Bolt Squash", hold_art("bolt", COAL, 300, seed=95, outline=CHALK))], x=195, y=620)
    rays = []
    for i in range(10):
        ang = i / 10 * 6.283
        rays.append(N(f"Ray {i}", [shape("Ray", [poly([(math.cos(ang) * 170, math.sin(ang) * 170), (math.cos(ang) * 214, math.sin(ang) * 214)], closed=False)],
                                         [stroke(COAL, 7, cap="square")])], x=195, y=620))
    p1_panel = N("Burst", [accent(E("Star", width=440, height=440, points=11, innerRadius=0.72, name="Path"), 0, 0)], x=195, y=620)
    p1_puff = Puff("Impact", 195, 760, 90, 96)
    g1 = N("Persona Power Mover", [p1_puff.outer, bolt, rays, p1_panel])
    groups[1] = g1
    # ---- 2: Balance Seeker - balanced stone pair
    top_d, top_in = hold3d_drawable("Top Stone 3D", "stone", ACID, 142, scene=9, bolt=0.12, speck=0.4, sway=0.05)
    base_d, base_in = hold3d_drawable("Base Stone 3D", "stone", CHALK, 214, scene=9, bolt=0.1, speck=0.3, sway=0.0)
    top = N("Top Stone", [top_d], x=195, y=596)
    base = N("Base Stone", [base_d], x=195, y=692)
    top_yaw, base_yaw = top_in["yaw"].id, base_in["yaw"].id
    pivot = shape("Pivot", [poly([(0, -20), (24, 22), (-24, 22)], radius=4)], [fill(COAL)], x=195, y=770)
    horizon = shape("Horizon", [poly([(40, 792), (350, 792)], closed=False)], [stroke(CHALK, 3)])
    p2_panel = N("Disc", [accent(ellipse(380), 0, 0)], x=195, y=650)
    g2 = N("Persona Balance Seeker", [top, base, pivot, horizon, p2_panel])
    groups[2] = g2
    # ---- 3: Persistent Solver - looping chalk route (bg flips to coal)
    loop_pts = []
    for i in range(200):
        t = i / 199
        ang = t * 6.283 * 4.0
        x = 60 + 270 * t + 46 * math.cos(ang + 3.1416)
        y = 640 + 70 * math.sin(ang) - 60 * t + 20
        loop_pts.append((x, y))
    loop_trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Loop Reveal")
    loop = E("Shape", name="Chalk Loop")
    loop.add(poly(loop_pts[::4], closed=False), E("Stroke", thickness=7, cap="round", join="round", name="Stroke", kids=[
        E("SolidColor", colorValue=CHALK, name="Chalk", kids=[bind(path("personaColor"), 37)]), loop_trim]))
    loop_dots = [N(f"Loop Hold {i}", [hold_art(kd, c, 46, seed=99 + i, outline=COAL)], x=x, y=y)
                 for i, (kd, c, x, y) in enumerate([("pinch", ACID, 70, 720), ("tri", COBALT, 330, 560)])]
    g3 = N("Persona Persistent Solver", [loop_dots, loop])
    groups[3] = g3
    s.variant_nodes = {k: g.id for k, g in groups.items()}
    s.mid.add(g0, g1, g2, g3)
    s.idle = [(top.id, "rotation", 0.03), (lens.id, "rotation", 0.15)]

    def choreo(a, v):
        for k, g in groups.items():
            a.hold(g.id, "opacity", 1.0 if k == v else 0.0)
        dark = v == 3
        a.hold(s.bg_color_id, "colorValue", COAL if dark else CHALK, kind="color")
        for nm, cid in ink.items():
            a.hold(cid, "colorValue", CHALK if dark else COAL, kind="color")
        # anticipation: the motif scribbles and charges, then gets consumed by the reveal
        a.tw(ant_trim, "end", 0, 26, 0.0, 1.0, "inout")
        a.k(s.ant.id, "opacity", 0, 1.0)
        a.tw(s.ant.id, "opacity", 30, 38, 1.0, 0.0, "linear")
        a.tw(s.ant.id, "scaleX", 22, 34, 1.0, 0.2, "in")
        a.k(s.ant.id, "x", 0, 0.0)
        a.tw(s.ant.id, "x", 22, 34, 0.0, 156, "in")
        a.tw(s.ant.id, "scaleY", 22, 34, 1.0, 0.2, "in")
        a.k(s.ant.id, "y", 0, 0.0)
        a.tw(s.ant.id, "y", 22, 34, 0.0, 450, "in")
        fade_in(a, lbl.id, 30, 14, 12)
        a.k(ttl.id, "opacity", 0, 0.0)
        a.tw(ttl.id, "opacity", 36, 46, 0.0, 1.0, "out")
        a.tw(ttl.id, "y", 36, 56, 196, 146, "snap")
        fade_in(a, dsc.id, 70, 18, 16)
        if v == 0:
            pop(a, p0_panel.id, 30, 20, "back")
            a.tw(p0_panel.id, "rotation", 30, 56, -0.8, 0.0, "back")
            for i, h in enumerate(p0_holds):
                pop(a, h.id, 40 + i * 6, 12, "snap")
            a.tw(p0_trim, "end", 44, 90, 0.0, 1.0, "inout")
            lp = [(120, 720), (250, 668), (150, 600), (262, 540), (196, 476)]
            for i, (x, y) in enumerate(lp):
                f = 48 + i * 11
                a.k(lens.id, "x", f, x, "inout")
                a.k(lens.id, "y", f, y, "inout")
            a.k(lens.id, "opacity", 0, 0.0)
            a.tw(lens.id, "opacity", 46, 52, 0.0, 1.0)
        elif v == 1:
            pop(a, p1_panel.id, 34, 16, "punch")
            a.tw(p1_panel.id, "rotation", 34, 70, 0.4, 0.0, "out")
            a.tw(bolt.id, "y", 20, 34, -260, 620, "in")
            a.k(bolt.id, "opacity", 0, 0.0)
            a.k(bolt.id, "opacity", 20, 1.0)
            sq = bolt.kids[0].id
            a.k(sq, "scaleY", 0, 1.0)
            a.k(sq, "scaleX", 0, 1.0)
            a.tw(sq, "scaleY", 34, 38, 1.0, 0.68, "out")
            a.tw(sq, "scaleX", 34, 38, 1.0, 1.25, "out")
            a.tw(sq, "scaleY", 38, 56, 0.68, 1.0, "snap")
            a.tw(sq, "scaleX", 38, 56, 1.25, 1.0, "snap")
            for i, r in enumerate(rays):
                pop(a, r.id, 36 + (i % 3) * 2, 12, "punch", s0=0.6)
                a.k(r.id, "opacity", 0, 0.0)
                a.tw(r.id, "opacity", 36, 40, 0.0, 1.0)
            p1_puff.fire(a, 36, 26, 1.5)
        elif v == 2:
            pop(a, p2_panel.id, 30, 22, "back")
            a.tw(base.id, "y", 30, 46, 860, 690, "back")
            a.k(top.id, "opacity", 0, 0.0)
            a.k(top.id, "opacity", 40, 1.0)
            a.tw(top.id, "y", 40, 54, 380, 598, "in")
            for f, r in [(40, 0.0), (54, 0.42), (66, -0.26), (78, 0.14), (90, -0.06), (100, 0.0)]:
                a.k(top.id, "rotation", f, r, "inout")
                a.k(top_yaw, 243, f, r * -2.2, "inout")
            a.tw(base_yaw, 243, 30, 60, 1.2, 0.0, "back")
            a.tw(base.id, "rotation", 54, 70, 0.06, 0.0, "back")
        else:
            a.tw(loop_trim, "start", 70, 104, 0.0, 0.0, "linear")
            a.tw(loop_trim, "end", 30, 96, 0.0, 1.0, "inout")
            for i, d in enumerate(loop_dots):
                pop(a, d.id, 32 + i * 50, 14, "snap")

    def carrier_hook(a, sx, sy, ss, sr):
        a.tw(CARRIER.id, "x", 0, 22, sx, 195, "inout")
        a.tw(CARRIER.id, "y", 0, 22, sy, 600, "inout")
        a.tw(CARRIER.id, "scaleX", 0, 22, ss, 1.2, "out")
        a.tw(CARRIER.id, "scaleY", 0, 22, ss, 1.2, "out")
        a.tw(CARRIER.id, "scaleX", 26, 34, 1.2, 0.0, "in")
        a.tw(CARRIER.id, "scaleY", 26, 34, 1.2, 0.0, "in")
        a.tw(CARRIER.id, "rotation", 0, 34, sr, 1.2, "in")
        a.tw(CARRIER_YAW, 243, 0, 34, ENTRY_YAW[0], ENTRY_YAW[0] + 6.2832, "in")
    s.carrier_hook = carrier_hook
    s.choreo = choreo
    s.hero_steps = [(0, 1.0, "hold")]
    return s


def scene10():
    s = Scene(10, CHALK)
    s.variants = [0, 1]           # 0 = full summary card, 1 = new-user welcome
    s.back.add(speckles("Speckle", 90, 0, 60, 390, 844, seed=110))
    s.back.add(shape("Concrete", [poly([(0, 640), (390, 560), (390, 844), (0, 844)])], [fill(CONCRETE)]))
    s.back.add(bolt_grid("Bolts", [(40 + (i % 8) * 44, 700 + (i // 8) * 44) for i in range(24)]))
    # ----- full card
    hd = N("Summary Headline", [headline("Summary Headline", "summaryHeadline", 0, 0, 342, 96, 46, COAL)], x=24, y=112)
    sup = N("Summary Support", [mono("Summary Support", "summarySupport", 0, 0, 342, 40, 14, COAL)], x=24, y=212)
    card = N("Card", [], x=24, y=262)
    cw, ch = 342, 352
    ys = [146, 206, 266]
    cells = []
    stats = [("sessionsDisplay", "screen2Unit"), ("sendsDisplay", "screen3Unit"), ("attemptsDisplay", "screen4Unit"),
             ("techniqueSessionsDisplay", "screen5Unit"), ("longestSessionMinutesDisplay", "screen6Unit")]
    for i, (vp, up) in enumerate(stats):
        cx_ = 18 + (i % 2) * 166
        cy_ = ys[i // 2]
        val = text(f"Stat {i}", 0, 0, 150, 42, FONT_BLACK, 44, CHALK, [("0", vp, None)], overflow="fitFontSize",
                   lh=40, wrap="noWrap", valign="bottom")
        un = text(f"Stat {i} Unit", 0, 44, 150, 16, FONT_MONO, 11, CHALK_D, [("", up, None)], overflow="ellipsis", lh=15)
        cells.append(N(f"Stat Cell {i}", [val, un], x=cx_, y=cy_))
    # 6th cell: the name (only with shareIncludeName) or a mini route motif
    name_cell = N("Name Cell", [text("Card Name", 0, 0, 150, 58, FONT_MONO_M, 13, ACID, [("", "userName", None)],
                                     overflow="ellipsis", lh=18)], x=184, y=270, opacity=0.0)
    motif = N("Motif Cell", [shape("Mini Route", [poly([(0, 40), (40, 20), (14, 6), (60, 0)], closed=False)],
                                   [stroke(ACID, 3, cap="round")]),
                             shape("Mini Holds", [ellipse(12, x=0, y=40), ellipse(10, x=40, y=20), ellipse(9, x=14, y=6)], [fill(CHALK)])],
                 x=200, y=272)
    s.name_cell, s.motif_cell = name_cell, motif
    # persona row
    mini = []
    for k, geom in enumerate([rect(30, 30, r=4, rot=0.785), E("Star", width=46, height=46, points=11, innerRadius=0.7, name="Path"),
                              ellipse(42), ellipse(40, 24)]):
        sc = E("SolidColor", colorValue=COAL, name="Accent", kids=[bind(path("personaColor"), 37)])
        sh = E("Shape", name=f"Mini Emblem {k}")
        sh.add(geom, E("Fill", name="Fill", kids=[sc]), stroke(CHALK, 2.5))
        m = N(f"Mini {k}", [sh], x=40, y=106)
        m.add(bind(path("personaSlot"), 18, conv.equals(k, "Persona is")))
        mini.append(m)
    persona_lbl = text("Card Persona Label", 0, 0, 240, 16, FONT_MONO, 11, CHALK_D, [("", "personaLabel", None)], overflow="ellipsis", lh=15)
    persona_name = text("Card Persona", 0, 18, 250, 40, FONT_XB, 34, CHALK, [("", "personaName", None)], overflow="fitFontSize", lh=34, wrap="noWrap")
    persona_row = N("Persona Row", [N("Persona Text", [persona_lbl, persona_name], x=76, y=78)] + mini)
    header = N("Header", [
        text("Card Year", 0, 0, 120, 24, FONT_MONO_M, 16, COAL, [("2026", "yearDisplay", None)], align="right", lh=20, sizing="fixed"),
    ], x=206, y=18)
    header_wm = E("NestedArtboard", artboardId=WORDMARK_AB, x=16, y=12, scaleX=0.62, scaleY=0.62, name="Card Wordmark")
    strip = N("Header Strip", [shape("Strip", [rect(cw, 56, x=cw / 2, y=28, r=18)], [fill(ACID)]),
                               shape("Strip Fill", [rect(cw, 20, x=cw / 2, y=46)], [fill(ACID)])])
    card_route, card_trim = route_line("Card Route", [(18, 338), (100, 328), (170, 340), (250, 326), (324, 336)], ACID, 3, dash=(8, 6))
    card_panel = shape("Card Panel", [rect(cw, ch, x=cw / 2, y=ch / 2, r=20)], [fill(COAL)])
    card_shadow = shape("Card Shadow", [rect(cw, ch, x=cw / 2 + 8, y=ch / 2 + 10, r=20)], [fill(alpha(COAL, 0.25))])
    card.add(header, N("Header Mark", [header_wm]), persona_row, cells, name_cell, motif, card_route, strip, card_panel, card_shadow)
    corner = Hold3("Corner Hold", "sloper", COBALT, 156, 40, 644, 0.3, scene=10, sway=0.04)
    full = N("Summary Full", [hd, sup, card, corner.outer])
    # ----- empty / new-user welcome
    e_hd = N("Empty Headline", [headline("Empty Headline", "emptyHeadline", 0, 0, 342, 140, 62, COAL)], x=24, y=120)
    e_sp = N("Empty Support", [mono("Empty Support", "emptySupport", 0, 0, 300, 44, 15, COAL)], x=24, y=274)
    e_h1 = Hold3("Start Hold", "jug", COBALT, 124, 120, 520, -0.1, scene=10, sway=0.05)
    e_h2 = Hold3("Next Hold", "tri", COAL, 94, 250, 430, 0.2, scene=10, sway=0.06, speck=0.12)
    e_route, e_trim = route_line("First Route", [(120, 520), (250, 430), (330, 330)], COAL, 3.5)
    empty = N("Summary Empty", [e_hd, e_sp, e_route, e_h2.outer, e_h1.outer])
    s.variant_nodes = {0: full.id, 1: empty.id}
    s.text.add(full, empty)
    s.idle = [(corner.idle.id, "rotation", 0.03), (e_h1.idle.id, "rotation", 0.03)]

    def choreo(a, v):
        a.hold(full.id, "opacity", 1.0 if v == 0 else 0.0)
        a.hold(empty.id, "opacity", 1.0 if v == 1 else 0.0)
        if v == 0:
            fade_in(a, hd.id, 6, 16, 24)
            fade_in(a, sup.id, 14, 16, 12)
            a.k(card.id, "opacity", 0, 0.0)
            a.tw(card.id, "opacity", 10, 18, 0.0, 1.0)
            a.tw(card.id, "y", 10, 34, 420, 262, "back")
            a.tw(card.id, "rotation", 10, 40, 0.12, 0.0, "back")
            a.tw(strip.id, "scaleX", 24, 40, 0.0, 1.0, "out")
            fade_in(a, header.id, 34, 12, 0)
            pop(a, persona_row.id, 38, 14, "snap", s0=0.6)
            a.k(persona_row.id, "opacity", 0, 0.0)
            a.k(persona_row.id, "opacity", 38, 1.0)
            for i, c in enumerate(cells):
                f = 46 + i * 6
                a.k(c.id, "opacity", 0, 0.0)
                a.k(c.id, "opacity", f, 1.0)
                pop(a, c.id, f, 12, "punch", s0=1.5, s1=1.0)
            a.tw(card_trim, "end", 60, 92, 0.0, 1.0, "inout")
            pop(a, corner.id, 70, 16, "snap")
            a.tw(corner.yaw, 243, 70, 96, 2.4, 0.0, "back")
        else:
            fade_in(a, e_hd.id, 8, 18, 30)
            fade_in(a, e_sp.id, 24, 16, 14)
            pop(a, e_h1.id, 34, 16, "snap")
            a.tw(e_h1.yaw, 243, 34, 60, -2.4, 0.0, "back")
            pop(a, e_h2.id, 44, 16, "snap")
            a.tw(e_h2.yaw, 243, 44, 70, 2.2, 0.0, "back")
            a.tw(e_trim, "end", 40, 80, 0.0, 1.0, "inout")
    s.choreo = choreo
    s.hero_steps = [(0, 1.0, "hold")]
    s.carrier_t = (20, 50)
    return s


def all_scenes():
    out = [scene1(), scene2(), scene3(), scene4(), scene5(), scene6(), scene7(), scene8(), scene9(), scene10()]
    for s in out:
        s.back.add(s.wall)   # the wall paints behind everything else in its scene
    return out
