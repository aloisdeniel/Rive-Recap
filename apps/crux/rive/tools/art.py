"""Reusable Crux vector artwork: cutout climbing holds, chalk, text, route lines."""
import math
from rml import (E, nid, node, shape, poly, ellipse, rect, fill, stroke, solid, bind,
                 CHALK, COAL, ACID, COBALT, CONCRETE, CONCRETE_D, CHALK_D, COAL_L, SHADES, RNG)
import model

# --------------------------------------------------------------- fonts
FONT_BLACK = "0:90"
FONT_XB = "0:91"
FONT_MONO = "0:92"
FONT_MONO_M = "0:93"
FONTS = {
    FONT_BLACK: ("BarlowCondensed-Black.ttf", "Barlow Condensed", "Black"),
    FONT_XB: ("BarlowCondensed-ExtraBold.ttf", "Barlow Condensed", "ExtraBold"),
    FONT_MONO: ("IBMPlexMono-Regular.ttf", "IBM Plex Mono", "Regular"),
    FONT_MONO_M: ("IBMPlexMono-Medium.ttf", "IBM Plex Mono", "Medium"),
}


def font_assets():
    return [E("FontAsset", file=f"assets/fonts/{fn}", name=fam + " " + sty, id=fid)
            for fid, (fn, fam, sty) in FONTS.items()]


BASE = {}   # node id -> dict of authored transform values (for animation helpers)


def N(name, kids=(), x=0.0, y=0.0, **kw):
    n = node(name, kids, x=x, y=y, **kw)
    BASE[n.id] = {"x": x, "y": y, "rotation": kw.get("rotation", 0.0),
                  "scaleX": kw.get("scaleX", 1.0), "scaleY": kw.get("scaleY", 1.0),
                  "opacity": kw.get("opacity", 1.0)}
    return n


def alpha(c, a):
    return f"{int(a * 255):02X}" + c[2:]


# --------------------------------------------------------------- text
def text(name, x, y, w, h, font, size, color, runs, align="left", sizing="fixed",
         overflow=None, lh=None, ls=None, valign=None, wrap=None, ox=None, oy=None, semantics=None):
    """runs: list of (literal, prop_or_None, converter_or_None)."""
    t = E("Text", x=x, y=y, width=w if sizing != "autoWidth" else None,
          height=h if sizing == "fixed" else None, sizingValue=sizing, alignValue=align,
          overflowValue=overflow, verticalAlignValue=valign, wrapValue=wrap,
          originX=ox, originY=oy, name=name)
    fn, fam, sty = FONTS[font]
    color_id = nid()
    st = E("TextStylePaint", fontSize=size, lineHeight=lh, letterSpacing=ls, fontAssetId=font,
           familyName=fam, styleName=sty, name=name + " Style")
    st.add(E("Fill", name="Fill", kids=[E("SolidColor", colorValue=color, name="Ink", id=color_id)]))
    t.add(st)
    if semantics:
        t.add(semantics)
    for (lit, prop, conv) in runs:
        r = E("TextValueRun", styleId=st.id, text=lit, name=(prop or "Run"))
        if prop:
            r.add(bind(model.path(prop), 268, conv))
        t.add(r)
    t.ink = color_id   # for keyed text colour
    return t


def hero(name, prop, x, y, w, h, size, color, align="left"):
    return text(name, x, y, w, h, FONT_BLACK, size, color, [("0", prop, None)], align=align,
                overflow="fitFontSize", lh=round(size * 0.84, 1), ls=-1.5, valign="bottom",
                wrap="noWrap")


def headline(name, prop, x, y, w, h, size, color, align="left"):
    return text(name, x, y, w, h, FONT_XB, size, color, [("", prop, None)], align=align,
                overflow="fitFontSize", lh=round(size * 0.92, 1), ls=-0.3)


def mono(name, prop, x, y, w, h, size, color, align="left", medium=False, overflow="ellipsis"):
    return text(name, x, y, w, h, FONT_MONO_M if medium else FONT_MONO, size, color,
                [("", prop, None)], align=align, overflow=overflow, lh=round(size * 1.38, 1))


# --------------------------------------------------------------- holds
KINDS = {
    "tri": [(0, -0.55), (0.56, 0.42), (-0.56, 0.42)],
    "pyramid": [(-0.08, -0.62), (0.6, 0.38), (-0.58, 0.42)],
    "sloper": [(-0.64, 0.3), (-0.5, -0.16), (-0.12, -0.4), (0.4, -0.3), (0.64, 0.3)],
    "pinch": [(0, -0.52), (0.4, -0.02), (0.06, 0.5), (-0.42, 0.04)],
    "crimp": [(-0.62, -0.1), (0.6, -0.22), (0.56, 0.16), (-0.6, 0.22)],
    "jug": [(-0.58, 0.12), (-0.38, -0.36), (0.38, -0.36), (0.58, 0.12), (0.22, 0.34), (-0.22, 0.34)],
    "stone": [(-0.6, 0.18), (-0.42, -0.2), (0, -0.3), (0.44, -0.18), (0.62, 0.16), (0.2, 0.3), (-0.24, 0.3)],
    "bolt": [(-0.12, -0.62), (0.42, -0.62), (0.12, -0.12), (0.46, -0.12), (-0.2, 0.66), (0.0, 0.08), (-0.38, 0.08)],
}


def hold_art(kind, color, s, seed=1, ring=False, outline=CHALK, speck=True):
    rng = RNG(seed)
    pts = [(x * s, y * s) for x, y in KINDS[kind]]
    r = s * 0.15 if kind != "bolt" else s * 0.04
    shade, hi = SHADES.get(color, (CONCRETE_D, CHALK))
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    if ring:
        out.append(shape("Route Dot", [ellipse(15)], [fill(CHALK), stroke(COAL, 3.5)], x=round(cx, 1), y=round(cy, 1)))
    if speck:
        geo = []
        for _ in range(6):
            a = rng.random() * 6.283
            d = rng.random() * 0.32 * s
            geo.append(ellipse(round(1.4 + rng.random() * 2.2, 1), x=round(cx + math.cos(a) * d, 1),
                               y=round(cy + math.sin(a) * d * 0.8, 1)))
        out.append(shape("Chalk", geo, [fill("B3FFFFFF")]))
    if kind != "bolt":
        out.append(shape("Bolt", [ellipse(round(s * 0.075, 1), x=round(cx + s * 0.04, 1), y=round(cy, 1))],
                         [fill(COAL)]))
        out.append(shape("Bolt Rim", [ellipse(round(s * 0.14, 1), x=round(cx + s * 0.04, 1), y=round(cy, 1))],
                         [fill(shade)]))
    facet = [((x - cx) * 0.55 + cx - s * 0.06, (y - cy) * 0.55 + cy - s * 0.08) for x, y in pts]
    out.append(shape("Facet", [poly(facet, radius=r * 0.6)], [fill(alpha(hi, 0.55))]))
    out.append(shape("Body", [poly(pts, radius=r)], [fill(color), stroke(outline, 2.5)]))
    out.append(shape("Shadow", [poly([(x + s * 0.06, y + s * 0.09) for x, y in pts], radius=r)], [fill(shade)]))
    return out


class Hold:
    """outer (entrance-keyed) -> idle (idle-keyed) -> art."""

    def __init__(self, name, kind, color, s, x, y, rot=0.0, seed=1, ring=False, outline=CHALK):
        self.art = hold_art(kind, color, s, seed, ring, outline)
        self.idle = N(name + " Idle", self.art)
        self.outer = N(name, [self.idle], x=x, y=y, rotation=rot)
        self.x, self.y, self.rot, self.s = x, y, rot, s
        self.id = self.outer.id


# --------------------------------------------------------------- chalk
def speckles(name, n, x0, y0, x1, y1, color="59202220", seed=3, rmin=1.0, rmax=2.6):
    rng = RNG(seed)
    geo = [ellipse(round(rmin + rng.random() * (rmax - rmin), 1),
                   x=round(x0 + rng.random() * (x1 - x0), 1), y=round(y0 + rng.random() * (y1 - y0), 1))
           for _ in range(n)]
    return shape(name, geo, [fill(color)])


def bolt_grid(name, pts, color=alpha(COAL, 0.35)):
    return shape(name, [ellipse(7, x=x, y=y) for x, y in pts], [fill(color)])


def puff_art(r, seed=5, color=CHALK, shade=CHALK_D):
    rng = RNG(seed)
    blobs, shades = [], []
    for i in range(7):
        a = i / 7 * 6.283 + rng.random() * 0.5
        d = r * (0.35 + rng.random() * 0.3)
        w = r * (0.55 + rng.random() * 0.35)
        blobs.append(ellipse(round(w, 1), x=round(math.cos(a) * d, 1), y=round(math.sin(a) * d * 0.8, 1)))
        shades.append(ellipse(round(w * 0.9, 1), x=round(math.cos(a) * d + r * 0.06, 1),
                              y=round(math.sin(a) * d * 0.8 + r * 0.08, 1)))
    dots = []
    for i in range(9):
        a = rng.random() * 6.283
        d = r * (0.9 + rng.random() * 0.5)
        dots.append(ellipse(round(2 + rng.random() * 3, 1), x=round(math.cos(a) * d, 1), y=round(math.sin(a) * d, 1)))
    return [shape("Grains", dots, [fill(color)]),
            shape("Puff", blobs, [fill(color)]),
            shape("Puff Shade", shades, [fill(shade)])]


class Puff:
    def __init__(self, name, x, y, r, seed=5, color=CHALK):
        self.inner = N(name + " Burst", puff_art(r, seed, color), scaleX=0.2, scaleY=0.2, opacity=0.0)
        self.outer = N(name, [self.inner], x=x, y=y)

    def fire(self, a, f, dur=22, scale=1.25):
        a.tw(self.inner.id, "scaleX", f, f + dur, 0.25, scale, "out")
        a.tw(self.inner.id, "scaleY", f, f + dur, 0.25, scale, "out")
        a.k(self.inner.id, "opacity", f - 1 if f > 0 else 0, 0.0)
        a.k(self.inner.id, "opacity", f, 1.0, "inq")
        a.k(self.inner.id, "opacity", f + dur, 0.0)


def route_line(name, pts, color=COAL, th=3.0, dash=(9, 7), cid=None):
    """Open polyline with a trim (returned) and optional dash."""
    trim = E("TrimPath", start=0, end=1, offset=0, modeValue="sequential", name="Reveal")
    eff = [trim]
    if dash:
        eff.append(E("DashPath", name="Dashes", kids=[E("Dash", length=dash[0], name="On"),
                                                      E("Dash", length=dash[1], name="Off")]))
    s = shape(name, [poly(pts, closed=False)],
              [stroke(color, th, cap="round" if not dash else "butt", join="round", effects=eff, cid=cid)])
    return s, trim.id


def arrow(name, color, th, x, y, scale=1.0, flip=False):
    sx = -1 if flip else 1
    pts = [(-9 * sx, 0), (8 * sx, 0)]
    head = [(1 * sx, -7), (8 * sx, 0), (1 * sx, 7)]
    return shape(name, [poly(pts, closed=False), poly(head, closed=False)],
                 [stroke(color, th, cap="square", join="miter")], x=x, y=y, scaleX=scale, scaleY=scale)


# --------------------------------------------------------------- wordmark (component artboard)
WORDMARK_AB = "0:60"


def wordmark_artboard():
    """Original stencil wordmark: CRUX drawn as heavy route strokes; the X carries a hold."""
    ab = E("Artboard", isComponent=True, width=160, height=56, x=1000, y=0, clip=False,
           styleId="0:61", name="Wordmark", id=WORDMARK_AB)
    ab.add(E("LayoutComponentStyle", name="Wordmark Style", id="0:61"))
    th = 10.5
    ink = lambda: [stroke(COAL, th, cap="butt", join="miter")]
    # X hold (acid) sits on the crossing
    ab.add(shape("X Hold", [poly([(-7, -8), (8, -5), (6, 8), (-8, 6)], radius=3)],
                 [fill(ACID), stroke(COAL, 3)], x=133, y=28))
    ab.add(shape("X", [poly([(116, 6), (150, 50)], closed=False), poly([(150, 6), (116, 50)], closed=False)],
                 [stroke(COAL, th, cap="butt")]))
    ab.add(shape("U", [poly([(82, 6), (82, 40), (88, 50), (102, 50), (108, 40), (108, 6)], closed=False)], ink()))
    ab.add(shape("R", [poly([(45, 50), (45, 6), (64, 6), (70, 12), (70, 23), (64, 28), (45, 28)], closed=False),
                       poly([(58, 28), (72, 50)], closed=False)], ink()))
    c = E("Stroke", thickness=th, cap="butt", join="miter", name="Stroke")
    c.add(solid(COAL))
    c.add(E("TrimPath", start=0.1, end=0.9, offset=0, modeValue="sequential", name="Open"))
    ab.add(shape("C", [ellipse(30, 40)], [c], x=19, y=28, rotation=1.5708))
    return ab


def wordmark_asset():
    return E("ComponentAsset", artboardId=WORDMARK_AB, name="Wordmark")


# --------------------------------------------------------------- GPU 3D holds + chalk (improvement pass)
HOLD3D_ASSET = "0:84"
CHALK_ASSET = "0:85"
WALL_ASSET = "0:86"
LAYOUT_ASSET = "0:87"
RIGDATA_ASSET = "0:88"
KIND3D = {"jug": 0, "pyramid": 1, "sloper": 2, "pinch": 3, "crimp": 4, "stone": 5, "tri": 6, "volume": 6}
SIZE3D = {"jug": 0.86, "pyramid": 0.92, "sloper": 0.86, "pinch": 0.86, "crimp": 0.84, "stone": 0.9, "tri": 1.0}
LIVE = {}          # scene k -> [live input ids]; build_stage keys them per entrance


def script_assets():
    # modules first: `require` only finds a module declared above its importer
    return [E("ScriptAsset", file="rigdata.luau", name="rigdata", isModule=True, id=RIGDATA_ASSET),
            E("ScriptAsset", file="layout.luau", name="layout", isModule=True, id=LAYOUT_ASSET),
            E("ScriptAsset", file="hold3d.luau", name="hold3d", id=HOLD3D_ASSET),
            E("ScriptAsset", file="chalk.luau", name="chalk", id=CHALK_ASSET),
            E("ScriptAsset", file="wall.luau", name="wall", id=WALL_ASSET)]


def rig_input(name, rig_name, v=0.0):
    """A script number input bound to one CruxRig value."""
    return E("ScriptInputNumber", propertyValue=v, name=name, kids=[bind(model.rig_path(rig_name), 243)])


def _num(name, v):
    return E("ScriptInputNumber", propertyValue=v, name=name)


def hold3d_drawable(name, kind, color, size, scene=None, roll=0.0, bolt=0.13, speck=0.5, sway=0.0,
                    extent=1.7, trail=None, live=None):
    """A ScriptedDrawable running hold3d.luau. Returns (drawable, inputs-by-name)."""
    d = E("ScriptedDrawable", scriptAssetId=HOLD3D_ASSET, name=name)
    ins = {}

    def add(el):
        d.add(el)
        ins[el.a["name"]] = el
        return el
    add(_num("size", round(size, 1)))
    add(_num("kind", KIND3D.get(kind, 0)))
    add(E("ScriptInputColor", propertyValue=color, name="color"))
    add(_num("yaw", 0.0))
    add(_num("pitch", 0.0))
    add(_num("roll", round(roll, 4)))
    add(_num("bolt", bolt))
    add(_num("speck", speck))
    add(_num("sway", sway))
    add(_num("extent", extent))
    add(_num("live", 1.0 if live is None else live))
    add(E("ScriptInputBoolean", propertyValue=False, name="still", kids=[bind(model.path("reducedMotion"), 245)]))
    add(E("ScriptInputBoolean", propertyValue=False, name="paused", kids=[bind(model.path("isPaused"), 245)]))
    add(rig_input("px", "px", 2.0))   # canvas pixels per design point, from the real on-screen scale
    if trail:
        for k, v in trail.items():
            add(_num(k, v))
    if scene is not None:
        LIVE.setdefault(scene, []).append(ins["live"].id)
        ins["live"].a["propertyValue"] = 0.0
    return d, ins


class Hold3:
    """Drop-in for Hold with a real 3D body: outer (entrance-keyed) -> idle -> [ring?, 3D]."""

    def __init__(self, name, kind, color, s, x, y, rot=0.0, seed=1, ring=False, outline=CHALK, scene=None,
                 sway=0.06, speck=0.4, bolt=None):
        size = s * SIZE3D.get(kind, 0.9)
        if bolt is None:
            bolt = 0.0 if ring else 0.13
        self.drawable, self.ins = hold3d_drawable(name + " 3D", kind, color, size, scene=scene, roll=rot,
                                                  bolt=bolt, speck=speck, sway=sway)
        kids = []
        if ring:
            kids.append(shape("Route Dot", [ellipse(15)], [fill(CHALK), stroke(COAL, 3.5)], x=round(s * 0.04, 1), y=0))
        kids.append(self.drawable)
        self.art = kids
        self.idle = N(name + " Idle", kids)
        self.outer = N(name, [self.idle], x=x, y=y, rotation=rot)
        self.x, self.y, self.rot, self.s = x, y, rot, s
        self.id = self.outer.id
        self.yaw = self.ins["yaw"].id
        self.pitch = self.ins["pitch"].id


def chalk_drawable():
    d = E("ScriptedDrawable", scriptAssetId=CHALK_ASSET, name="Chalk Burst")
    ins = {}
    for nm, v in (("amount", 0.0), ("clear", 0.0), ("originX", 195.0), ("originY", 500.0), ("drift", 0.0),
                  ("seed", 1.0), ("direction", 1.0)):
        el = _num(nm, v)
        d.add(el)
        ins[nm] = el.id
    # the cloud covers the whole canvas: it maps the viewport into its own (carrier) space
    for nm, rn, v in (("rigX", "chX", 0.0), ("rigY", "chY", 0.0), ("rigS", "chS", 1.0), ("k", "k", 1.0),
                      ("vw", "vw", 390.0), ("vh", "vh", 844.0), ("dpr", "dpr", 1.0)):
        d.add(rig_input(nm, rn, v))
    return d, ins


def wall_drawable(name, color, seed, density=2.9, dmin=1.0, dmax=2.6, scene=None, grid=None):
    """Procedural wall texture (wall.luau): chalk speckles, and optionally a bolt grid,
    over the whole canvas whatever its size. `density` = dots per 10,000 square points."""
    d = E("ScriptedDrawable", scriptAssetId=WALL_ASSET, name=name)
    d.add(E("ScriptInputColor", propertyValue=color, name="color"))
    for nm, v in (("seed", seed), ("density", density), ("dmin", dmin), ("dmax", dmax)):
        d.add(_num(nm, v))
    if grid:
        gx, gy, step_x, step_y, dia, gcol = grid
        for nm, v in (("gridX", gx), ("gridY", gy), ("gridStepX", step_x), ("gridStepY", step_y), ("gridD", dia)):
            d.add(_num(nm, v))
        d.add(E("ScriptInputColor", propertyValue=gcol, name="gridColor"))
    d.add(rig_input("w", "uw", 390.0))
    d.add(rig_input("h", "uh", 844.0))
    live = _num("live", 1.0 if scene is None else 0.0)
    d.add(live)
    if scene is not None:
        LIVE.setdefault(scene, []).append(live.id)
    return d
