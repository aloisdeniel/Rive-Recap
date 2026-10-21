"""Original flat 'risograph cookbook' cutouts, all centred on their own origin."""
import math
from rml import E, clone, node, shape, fill, stroke, ellipse, rect, star, poly, smooth, straight, col


def ink(geom, off=(3, 3), c='ink25', name='ink'):
    return shape(name, clone(geom), fill(c), x=off[0], y=off[1])


# ---------------------------------------------------------------- vegetables
def tomato(name='Tomato', s=1.0, x=0, y=0, rot=0):
    body = lambda: ellipse(64 * s, 56 * s)
    leaves = star(34 * s, 34 * s, 5, 0.35, 3 * s)
    return node(name, [
        shape('stem', rect(4 * s, 10 * s, 2 * s), fill('basilDk'), y=-30 * s),
        shape('calyx', leaves, fill('basil'), y=-24 * s),
        shape('shine', ellipse(14 * s, 8 * s), fill('tomatoLt'), x=-14 * s, y=-12 * s, rot=-0.5),
        shape('body', body(), fill('tomato')),
        ink(body(), (4 * s, 4 * s)),
    ], x=x, y=y, rot=rot)


def tomato_half(name='Tomato half', s=1.0, x=0, y=0, rot=0):
    pts = [(-30, 0), (-26, 16), (-12, 26), (0, 28), (12, 26), (26, 16), (30, 0)]
    seeds = [shape(f'seed{i}', ellipse(5 * s, 8 * s), fill('butter'), x=dx * s, y=dy * s, rot=r)
             for i, (dx, dy, r) in enumerate([(-14, 9, 0.6), (-4, 15, 0.2), (8, 14, -0.2), (17, 7, -0.7)])]
    return node(name, seeds + [
        shape('flesh', smooth([(px * s * 0.82, py * s * 0.82 + 2 * s) for px, py in pts], True), fill('tomatoLt')),
        shape('skin', smooth([(px * s, py * s) for px, py in pts], True), fill('tomato')),
        ink(smooth([(px * s, py * s) for px, py in pts], True), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def carrot(name='Carrot', s=1.0, x=0, y=0, rot=0):
    body = lambda: smooth([(-12 * s, -40 * s), (12 * s, -40 * s), (6 * s, 10 * s), (0, 46 * s), (-6 * s, 10 * s)], True)
    ridges = [shape(f'ridge{i}', rect(10 * s, 2.4 * s, 1.2 * s), fill('tomatoDk'), x=(-3 + i % 2 * 4) * s, y=(-24 + i * 14) * s, op=0.6)
              for i in range(4)]
    tops = [shape(f'leaf{i}', smooth([(0, 0), (-5 * s, -14 * s), (0, -30 * s), (5 * s, -14 * s)], True), fill('basil'),
                  y=-38 * s, rot=r) for i, r in enumerate([-0.5, 0, 0.45])]
    return node(name, ridges + tops + [shape('body', body(), fill('carrot')), ink(body(), (3 * s, 3 * s))], x=x, y=y, rot=rot)


def leaf(name='Basil', s=1.0, x=0, y=0, rot=0, c='basil'):
    g = lambda: smooth([(0, -26 * s), (14 * s, -6 * s), (10 * s, 14 * s), (0, 24 * s), (-10 * s, 14 * s), (-14 * s, -6 * s)], True)
    return node(name, [
        shape('vein', rect(1.8 * s, 40 * s, 1), fill('basilDk'), op=0.8),
        shape('blade', g(), fill(c)),
        ink(g(), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def mushroom(name='Mushroom', s=1.0, x=0, y=0, rot=0):
    cap = lambda: smooth([(-30 * s, 4 * s), (-24 * s, -16 * s), (0, -26 * s), (24 * s, -16 * s), (30 * s, 4 * s)], True, corners=(0, 4))
    return node(name, [
        shape('spot1', ellipse(8 * s, 6 * s), fill('cream'), x=-10 * s, y=-12 * s),
        shape('spot2', ellipse(6 * s, 5 * s), fill('cream'), x=9 * s, y=-15 * s),
        shape('cap', cap(), fill('woodDk')),
        shape('stem', rect(18 * s, 26 * s, 7 * s), fill('mush'), y=14 * s),
        ink(cap(), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def onion(name='Onion', s=1.0, x=0, y=0, rot=0):
    b = lambda: smooth([(0, -34 * s), (16 * s, -8 * s), (24 * s, 14 * s), (0, 28 * s), (-24 * s, 14 * s), (-16 * s, -8 * s)], True)
    rings = [shape(f'ring{i}', smooth([(0, -24 * s + i * 8 * s), (10 * s - i * 3 * s, 8 * s), (0, 22 * s)], False),
                   stroke('aubPale', 2.2 * s), op=0.9) for i in range(2)]
    return node(name, rings + [shape('bulb', b(), fill('onion')), ink(b(), (3 * s, 3 * s))], x=x, y=y, rot=rot)


def garlic(name='Garlic', s=1.0, x=0, y=0, rot=0):
    b = lambda: smooth([(0, -30 * s), (10 * s, -10 * s), (24 * s, 6 * s), (14 * s, 22 * s), (-14 * s, 22 * s), (-24 * s, 6 * s), (-10 * s, -10 * s)], True)
    return node(name, [
        shape('line1', smooth([(0, -20 * s), (-6 * s, 4 * s), (-4 * s, 20 * s)], False), stroke('mush', 1.8 * s)),
        shape('line2', smooth([(0, -20 * s), (7 * s, 4 * s), (5 * s, 20 * s)], False), stroke('mush', 1.8 * s)),
        shape('bulb', b(), fill('garlic')),
        ink(b(), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def chili(name='Chili', s=1.0, x=0, y=0, rot=0):
    b = lambda: smooth([(-6 * s, -26 * s), (6 * s, -24 * s), (8 * s, 0), (2 * s, 22 * s), (-10 * s, 34 * s), (-4 * s, 10 * s)], True)
    return node(name, [
        shape('stem', rect(4 * s, 12 * s, 2 * s), fill('basil'), y=-30 * s, rot=0.3),
        shape('pod', b(), fill('tomato')),
        ink(b(), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def lemon_slice(name='Lemon', s=1.0, x=0, y=0, rot=0):
    segs = [shape(f'seg{i}', rect(2 * s, 20 * s, 1), fill('butter'), rot=i * math.pi / 4) for i in range(4)]
    return node(name, segs + [
        shape('pulp', ellipse(40 * s, 40 * s), fill('lemon')),
        shape('pith', ellipse(48 * s, 48 * s), fill('butter')),
        shape('rind', ellipse(54 * s, 54 * s), fill('FFE9AE1C')),
        ink(ellipse(54 * s, 54 * s), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def pea(name='Pea', s=1.0, x=0, y=0, c='basilLt'):
    return node(name, [shape('p', ellipse(10 * s, 10 * s), fill(c)), ink(ellipse(10 * s, 10 * s), (2, 2))], x=x, y=y)


def avocado(name='Avocado', s=1.0, x=0, y=0, rot=0):
    b = lambda: smooth([(0, -34 * s), (16 * s, -12 * s), (24 * s, 14 * s), (0, 34 * s), (-24 * s, 14 * s), (-16 * s, -12 * s)], True)
    return node(name, [
        shape('pit', ellipse(22 * s, 24 * s), fill('woodDk'), y=10 * s),
        shape('flesh', smooth([(0, -26 * s), (12 * s, -8 * s), (18 * s, 14 * s), (0, 28 * s), (-18 * s, 14 * s), (-12 * s, -8 * s)], True), fill('FFD6E39A')),
        shape('skin', b(), fill('basilDk')),
        ink(b(), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def ginger(name='Ginger', s=1.0, x=0, y=0, rot=0):
    b = lambda: smooth([(-30 * s, 0), (-20 * s, -14 * s), (-6 * s, -8 * s), (4 * s, -22 * s), (16 * s, -14 * s), (14 * s, -2 * s), (30 * s, 4 * s), (20 * s, 16 * s), (-24 * s, 14 * s)], True)
    return node(name, [shape('root', b(), fill('mush')), ink(b(), (3 * s, 3 * s))], x=x, y=y, rot=rot)


def pomegranate(name='Pomegranate', s=1.0, x=0, y=0, rot=0):
    seeds = [shape(f's{i}', ellipse(7 * s, 9 * s), fill('tomatoLt'), x=(math.cos(i * 1.3) * 11) * s, y=(math.sin(i * 1.3) * 11) * s) for i in range(6)]
    return node(name, seeds + [
        shape('in', ellipse(38 * s, 38 * s), fill('FF9E2238')),
        shape('crown', star(18 * s, 14 * s, 5, 0.5), fill('FF9E2238'), y=-26 * s),
        shape('skin', ellipse(48 * s, 48 * s), fill('FFC4314B')),
        ink(ellipse(48 * s, 48 * s), (3 * s, 3 * s)),
    ], x=x, y=y, rot=rot)


def corn(name='Corn', s=1.0, x=0, y=0):
    return node(name, [pea(f'k{i}', s * 0.9, x=(i % 3 - 1) * 9 * s, y=(i // 3 - 1) * 9 * s, c='lemon') for i in range(9)], x=x, y=y)


# ---------------------------------------------------------------- tableware & set dressing
def gingham(name, w, h, cell=22, c='basil', bg='cream', x=0, y=0, rot=0, clip_geom=None):
    kids = []
    nx = int(w // cell) + 2
    ny = int(h // cell) + 2
    for i in range(0, nx, 2):
        kids.append(shape(f'v{i}', rect(cell, h + cell * 2, 0, 0, 0), fill(c), x=-w / 2 + i * cell - cell, y=-h / 2 - cell, op=0.55))
    for j in range(0, ny, 2):
        kids.append(shape(f'h{j}', rect(w + cell * 2, cell, 0, 0, 0), fill(c), x=-w / 2 - cell, y=-h / 2 + j * cell - cell, op=0.55))
    kids.append(shape('base', rect(w + cell * 2, h + cell * 2, 0), fill(bg)))
    return node(name, kids, x=x, y=y, rot=rot)


def scallop_ticket(name, w, h, c='butter', edge='tomato', bumps=None, x=0, y=0, rot=0, shadow=True):
    """A rectangular ticket with scalloped top/bottom edges (built from a row of circles)."""
    r = 9
    n = bumps or int(w // (r * 2))
    step = w / n
    kids = []
    circles_top = [ellipse(r * 2, r * 2) for _ in range(n)]
    body = []
    for i in range(n):
        cx = -w / 2 + step * (i + 0.5)
        body.append(shape(f'bt{i}', ellipse(step + 1, step + 1), fill(c), x=cx, y=-h / 2))
        body.append(shape(f'bb{i}', ellipse(step + 1, step + 1), fill(c), x=cx, y=h / 2))
    kids.extend(body)
    kids.append(shape('body', rect(w, h, 4), fill(c)))
    if shadow:
        sh = [shape(f'st{i}', ellipse(step + 1, step + 1), fill(edge), x=-w / 2 + step * (i + 0.5) + 5, y=h / 2 + 5) for i in range(n)]
        kids.extend(sh)
        kids.append(shape('shadow', rect(w, h, 4), fill(edge), x=5, y=5))
    return node(name, kids, x=x, y=y, rot=rot)


def plate(name, d, x=0, y=0, rim='cream', well='paper', c_edge='aub'):
    return node(name, [
        shape('well', ellipse(d * 0.68, d * 0.68), fill(well)),
        shape('ring', ellipse(d * 0.74, d * 0.74), stroke('butterDk', 2)),
        shape('rim', ellipse(d, d), [fill(rim), stroke(c_edge, 2.5)]),
        ink(ellipse(d, d), (5, 6), 'ink15'),
    ], x=x, y=y)


def jar(name, w, h, lid='tomato', body='cream', label='butter', spice='carrot', x=0, y=0, rot=0, kind=0):
    """Spice jar standing on y=0 (its base)."""
    r = 10 if kind == 0 else (w / 2 - 2 if kind == 1 else 6)
    g = lambda: rect(w, h, r, 0.5, 1)
    return node(name, [
        shape('lid band', rect(w * 0.82, 5, 2, 0.5, 1), fill('FFFFFFFF'), y=-h - 2, op=0.35),
        shape('lid', rect(w * 0.86, 16, 5, 0.5, 1), fill(lid), y=-h + 2),
        shape('label text', rect(w * 0.42, 3, 1.5), fill('aub'), y=-h * 0.42, op=0.7),
        shape('label', rect(w * 0.7, h * 0.32, 3), fill(label), y=-h * 0.42),
        shape('spice', rect(w - 8, h * 0.62, max(2, r - 4), 0.5, 1), fill(spice), y=-4),
        shape('glass', g(), [fill(body), stroke('aub', 2.2)]),
        shape('ink', g(), fill('ink25'), x=4, y=3),
    ], x=x, y=y, rot=rot)


def steam_curl(name, pts, w=10, c='cream', x=0, y=0, outline='aub'):
    """Thick ribbon of steam: a cream stroke with an ink offset stroke. Returns (node, trims[], vertices_main)."""
    p_main = smooth(pts, False)
    p_ink = smooth(pts, False)
    trim_a = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    trim_b = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    s_main = shape(name, p_main, [E('Stroke', [E('SolidColor', colorValue=col(c), name='Color'), trim_a], thickness=float(w), cap='round', join='round', name='Stroke')])
    s_ink = shape(name + ' ink', p_ink, [E('Stroke', [E('SolidColor', colorValue=col(outline), name='Color'), trim_b], thickness=float(w), cap='round', join='round', name='Stroke')], x=3, y=3, op=0.85)
    return node(name + ' grp', [s_main, s_ink], x=x, y=y), [trim_a, trim_b], (p_main, p_ink)


def sparkle(name, s=1, c='lemon', x=0, y=0):
    return node(name, [shape('s', star(22 * s, 22 * s, 4, 0.28, 1), fill(c))], x=x, y=y)


def handwritten_arrow(name, pts, c='aub', w=2.2, x=0, y=0):
    head = pts[-1]
    prev = pts[-2]
    ang = math.atan2(head[1] - prev[1], head[0] - prev[0])
    a1 = (head[0] - 9 * math.cos(ang - 0.5), head[1] - 9 * math.sin(ang - 0.5))
    a2 = (head[0] - 9 * math.cos(ang + 0.5), head[1] - 9 * math.sin(ang + 0.5))
    trim = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    line = shape(name, smooth(pts, False), [E('Stroke', [E('SolidColor', colorValue=col(c), name='Color'), trim], thickness=float(w), cap='round', join='round', name='Stroke')])
    hd = shape(name + ' head', straight([a1, head, a2], False), stroke(c, w))
    return node(name + ' grp', [hd, line], x=x, y=y), trim, hd
