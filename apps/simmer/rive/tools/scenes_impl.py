"""The ten scenes. Coordinates are artboard space (390 x 844)."""
import math
import random
from rml import (E, node, shape, fill, stroke, ellipse, rect, star, poly, smooth, straight, Anim, layer, astate, trans,
                 cond_num, cond_bool, bind, ms2f, col)
from data import P, count_converter, CONV_FORMAT, CONV_INT, SCRIPT_LETTERS, SCRIPT_BOOK
from text import style, text, reveal_modifier, key_reveal
from scene_base import Scene, hero_number, copy_styles, W, H, IDLE_MS
import art
import stage

NAMES = {1: 'S1 Invitation', 2: 'S2 Meals cooked', 3: 'S3 Recipes tried', 4: 'S4 Cuisines explored', 5: 'S5 New ingredients',
         6: 'S6 Favorite recipe', 7: 'S7 Shared meals', 8: 'S8 Cooking days', 9: 'S9 Persona', 10: 'S10 Summary'}
METRIC = {2: 'mealsCooked', 3: 'recipesTried', 4: 'cuisinesExplored', 5: 'newIngredients', 6: 'repeatRecipeCount', 7: 'sharedMeals', 8: 'cookingDays'}
EXTRA = []

HERO_IN = 250        # ms: hero number arrives (after the 0-200 ms orienting gesture)
COPY_IN = (1150, 1900)


def metric_copy(sc, k, align='left', y_num=98, y_copy=224):
    """Hero number (count-up) + unit / headline / support block for metric scene k."""
    hn = hero_number(sc, METRIC[k], count_converter(k), 24, y_num, align=align)
    u, h, s = copy_styles()
    tb = sc.text_block(24, y_copy, 342, [(u, 'unit', f'screen{k}Unit'), (h, 'Headline', f'screen{k}Headline'),
                                         (s, 'Support', f'screen{k}Support')], align=align)
    sc.reveal_text(tb, *COPY_IN)
    stage.bind_copy_width(tb)
    ox = 24 if align == 'left' else 366
    # the number swings up from its baseline with a little overshoot (pivot at its edge)
    holder = node('Hero holder', [hn], x=ox, y=y_num + 110)
    hn.attrs['x'] = float(24 - ox)
    hn.attrs['y'] = float(-110)
    if align != 'left':
        # right-aligned: the pivot rides the copy column's right edge
        stage.bind_expr(holder, 13, 'Layout copy right edge', stage.CW + 24.0)
        stage.bind_expr(hn, 13, 'Layout copy width negated', stage.CW * -1.0)
    sc.key(holder, 'opacity', [(0, 0.0, 'hold'), (HERO_IN, 0.0, 'soft'), (HERO_IN + 260, 1.0)])
    sc.key(holder, 'scaleY', [(0, 0.4, 'hold'), (HERO_IN, 0.4, 'back'), (HERO_IN + 520, 1.0)])
    sc.key(holder, 'scaleX', [(0, 0.85, 'hold'), (HERO_IN, 0.85, 'back'), (HERO_IN + 520, 1.0)])
    sc.key(holder, 'rotation', [(0, -0.08 if align == 'left' else 0.08, 'hold'), (HERO_IN, -0.08 if align == 'left' else 0.08, 'back'), (HERO_IN + 600, 0.0)])
    return holder, tb


def pop_in(sc, obj, t, dur=420, from_scale=0.0, ease='back', rot_from=None, rot_to=None):
    sc.key(obj, 'scaleX', [(0, from_scale, 'hold'), (t, from_scale, ease), (t + dur, float(obj.attrs.get('scaleX', 1.0)))])
    sc.key(obj, 'scaleY', [(0, from_scale, 'hold'), (t, from_scale, ease), (t + dur, float(obj.attrs.get('scaleY', 1.0)))])
    if rot_from is not None:
        rt = rot_to if rot_to is not None else float(obj.attrs.get('rotation', 0.0))
        sc.key(obj, 'rotation', [(0, rot_from, 'hold'), (t, rot_from, 'out'), (t + dur, rt)])


def arc_in(sc, obj, t, start, dur=600, lift=120, ease_y='out', spin=0.0):
    """Throw obj from `start` to its authored position along an arc (x linear-ish, y up then down)."""
    x1, y1 = float(obj.attrs.get('x', 0)), float(obj.attrs.get('y', 0))
    x0, y0 = start
    peak = min(y0, y1) - lift
    sc.key(obj, 'x', [(0, x0, 'hold'), (t, x0, 'soft'), (t + dur, x1)])
    sc.key(obj, 'y', [(0, y0, 'hold'), (t, y0, 'out'), (t + dur * 0.45, peak, 'in'), (t + dur, y1)])
    r1 = float(obj.attrs.get('rotation', 0.0))
    if spin:
        sc.key(obj, 'rotation', [(0, r1 - spin, 'hold'), (t, r1 - spin, 'soft'), (t + dur, r1)])


def hand(text_, size=26, color='aub', weight=600):
    return style('hand', size, weight, color, name='Hand')


# ============================================================================ 1. Invitation
def scene1(x_stage):
    sc = Scene(1, NAMES[1], x_stage)
    greet_st = style('hand', 32, 700, 'tomato', name='Greeting')
    greet = text('Greeting', [(greet_st, 'Hello!', 'greetingLine', None)], x=24, y=100, width=330, height=40, sizing='fixed',
                 overflow='ellipsis', wrap='noWrap', rot=-0.03)
    h = style('display', 44, 800, 'aub', lh=44, ls=-1.2, opsz=72, name='Intro headline')
    s = style('body', 19, 400, 'aub', lh=25, name='Intro support')
    tb = sc.text_block(24, 146, 342, [(h, 'Your 2026 on Simmer', 'introHeadline'), (s, 'A year, uniquely yours.', 'introSupport')])
    sc.reveal_text(tb, 300, 1100, y=30)
    sc.key(greet, 'opacity', [(0, 0.0, 'hold'), (120, 0.0, 'soft'), (420, 1.0)])
    sc.key(greet, 'x', [(0, 4.0, 'hold'), (120, 4.0, 'back'), (520, 24.0)])

    # period ticket (scalloped recipe ticket)
    pst = style('body', 15, 600, 'aub', name='Period')
    period = text('Period', [(pst, 'January 1–December 31, 2026', 'periodLabel', None)], x=-120, y=-10, width=240, height=20,
                  sizing='fixed', align='center', overflow='ellipsis', wrap='noWrap')
    ticket = node('Period ticket', [period, art.scallop_ticket('ticket', 262, 30, c='butter', edge='tomato')], x=190, y=316, rot=0.035)
    sc.key(ticket, 'y', [(0, 356.0, 'hold'), (1300, 356.0, 'back'), (1750, 316.0)])
    sc.key(ticket, 'opacity', [(0, 0.0, 'hold'), (1300, 0.0, 'soft'), (1550, 1.0)])

    # wordmark rising out of the steam
    wm_st = style('display', 84, 800, 'tomato', ls=-3, opsz=96, name='Big wordmark')
    wm_ink = style('display', 84, 800, 'aub', ls=-3, opsz=96, name='Big wordmark ink')
    wm = text('Wordmark', [(wm_st, 'Simmer', None, None)], x=195, y=396, ox=0.5, oy=0.5)
    wm2 = text('Wordmark ink', [(wm_ink, 'Simmer', None, None)], x=198, y=399, ox=0.5, oy=0.5, op=0.35)
    # the wordmark is condensed out of the pot's steam on the GPU (scripts/letters.luau + .wgsl);
    # the inked vector wordmark fades in underneath and is uncovered as the steam letters evaporate
    mask_ab = E('Artboard', isComponent=True, width=390.0, height=360.0, name='Wordmark mask', x=500.0, y=2100.0, clip=False)
    mask_st = E('LayoutComponentStyle', name='Artboard Style')
    mask_ab.attrs['styleId'] = mask_st.id
    mask_ab.add(mask_st, text('Mask wordmark', [(style('display', 84, 800, 'white', ls=-3, opsz=96, name='Mask wordmark'), 'Simmer', None, None)],
                              x=195, y=96, ox=0.5, oy=0.5))
    EXTRA.append((mask_ab, None))
    letters_p = E('ScriptInputNumber', propertyValue=0.0, name='progress')
    letters = E('ScriptedDrawable', [letters_p, E('ScriptInputArtboard', artboardId=mask_ab.id, name='mask')],
                scriptAssetId=SCRIPT_LETTERS, name='Steam lettering', x=0.0, y=300.0)
    sc.key(letters_p, 'propertyValue', [(0, 0.0, 'hold'), (300, 0.0, 'lin'), (1900, 1.0)])
    for w_, top in ((wm, 1.0), (wm2, 0.35)):
        sc.key(w_, 'opacity', [(0, 0.0, 'hold'), (1150, 0.0, 'soft'), (1450, top)])
    underline = shape('Wordmark swash', smooth([(-120, 0), (-40, 8), (40, -2), (120, 6)], False), stroke('basil', 5), x=195, y=444)
    sc.key(underline, 'scaleX', [(0, 0.0, 'hold'), (1250, 0.0, 'out'), (1700, 1.0)])

    # dancing vegetables thrown out of the pot when the lid pops (~420 ms)
    veg = [
        art.carrot('Carrot', 1.0, x=34, y=606, rot=-0.45),
        art.tomato('Tomato', 0.9, x=340, y=548, rot=0.15),
        art.leaf('Basil L', 1.0, x=48, y=470, rot=-0.9),
        art.leaf('Basil R', 0.9, x=306, y=478, rot=0.8, c='basilLt'),
        art.mushroom('Mushroom', 0.85, x=350, y=716, rot=0.2),
        art.garlic('Garlic', 0.8, x=36, y=716, rot=-0.15),
        art.chili('Chili', 0.75, x=258, y=500, rot=0.7),
        art.onion('Onion', 0.7, x=352, y=636, rot=-0.3),
    ]
    for i, v in enumerate(veg):
        arc_in(sc, v, 380 + i * 55, (195, 600), dur=620, lift=90 + (i % 3) * 30, spin=2.2 * (1 if i % 2 else -1))
        pop_in(sc, v, 380 + i * 55, dur=300, from_scale=0.3, ease='out')
        # dance: bob and sway with staggered phases
        bx, by, br = float(v.attrs['x']), float(v.attrs['y']), float(v.attrs.get('rotation', 0))
        n = 4 if i % 2 else 2
        per = IDLE_MS / n
        seq_y, seq_r = [], []
        for c in range(n):
            t0 = c * per
            off = (i * 137) % int(per * 0.5)
            seq_y += [(t0, by, 'inout'), (t0 + per * 0.5, by - 10 - (i % 3) * 3, 'inout')]
            seq_r += [(t0, br, 'inout'), (t0 + per * 0.5, br + (0.14 if i % 2 else -0.14), 'inout')]
        seq_y.append((IDLE_MS, by)); seq_r.append((IDLE_MS, br))
        sc.idle.ms(v, 'y', seq_y)
        sc.idle.ms(v, 'rotation', seq_r)
    dancers = node('Dancing vegetables', veg)

    stage.bind_copy_width(tb)
    stage.bind_copy_width(greet, 12)
    sc.inner.add(sc.copy_group([greet, tb]), sc.art_group([ticket, letters, wm, wm2, underline, dancers]))
    return sc


# ============================================================================ 2. Meals cooked
def scene2(x_stage):
    sc = Scene(2, NAMES[2], x_stage)
    hero, tb = metric_copy(sc, 2, 'left')
    rnd = random.Random(2)
    waves = [
        [art.tomato_half(f'w1 tomato {i}', 0.9, rot=rnd.uniform(-1, 1)) for i in range(3)],
        [art.leaf(f'w2 basil {i}', 0.8, rot=rnd.uniform(-1.5, 1.5)) for i in range(2)] +
        [node(f'w2 carrot coin {i}', [shape('coin', ellipse(26, 26), [fill('carrot'), stroke('tomatoDk', 2)]), art.ink(ellipse(26, 26), (3, 3))]) for i in range(2)],
        [art.mushroom('w3 mushroom', 0.8), art.chili('w3 chili', 0.8, rot=0.6), art.onion('w3 onion', 0.7), art.garlic('w3 garlic', 0.6)],
    ]
    pieces = []
    starts = [(250, -60), (330, -90), (380, -40), (300, -120), (360, -80), (230, -100), (390, -50)]
    for w, group in enumerate(waves):
        t0 = 350 + w * 330
        for j, p in enumerate(group):
            tx = 150 + ((j * 47 + w * 31) % 90)
            p.attrs['x'] = float(tx)
            p.attrs['y'] = float(700)      # ends inside the pot (behind the pot body)
            sx, sy = starts[(j + w * 2) % len(starts)]
            t = t0 + j * 70
            sc.enter.ms(p, 'x', [(0, float(sx), 'hold'), (t, float(sx), 'soft'), (t + 640, float(tx))])
            sc.enter.ms(p, 'y', [(0, float(sy), 'hold'), (t, float(sy), 'out'), (t + 260, float(sy) + 140, 'drop'), (t + 640, 700.0)])
            sc.enter.ms(p, 'rotation', [(0, 0.0, 'hold'), (t, 0.0, 'lin'), (t + 640, (j + 1) * 2.0 * (1 if w % 2 else -1))])
            sc.settle(p, 'y', 700.0)
            pieces.append(p)
    # splash + payoff: three leaves leap back out and hover in the steam
    hover = [art.leaf('hover basil', 0.9, x=118, y=500, rot=-0.6), art.tomato_half('hover tomato', 0.8, x=280, y=486, rot=0.4),
             art.leaf('hover basil 2', 0.7, x=214, y=452, rot=0.3, c='basilLt')]
    for i, h in enumerate(hover):
        arc_in(sc, h, 1350 + i * 90, (195, 640), dur=520, lift=40)
        pop_in(sc, h, 1350 + i * 90, dur=300, from_scale=0.2, ease='out')
        sc.wiggle(h, 'y', float(h.attrs['y']), -9, IDLE_MS / 2)
        sc.wiggle(h, 'rotation', float(h.attrs['rotation']), 0.12 if i % 2 else -0.12, IDLE_MS)
    # payoff 2: the rest of the ingredients burst up out of the pot and hang in the steam (concept)
    burst = [art.carrot('burst carrot', 0.9, x=340, y=468, rot=0.5), art.mushroom('burst mushroom', 0.72, x=300, y=560, rot=0.25),
             art.onion('burst onion', 0.62, x=356, y=530, rot=-0.3), art.leaf('burst basil', 0.85, x=60, y=430, rot=-0.7),
             art.tomato_half('burst tomato', 0.72, x=168, y=426, rot=-0.3), art.garlic('burst garlic', 0.55, x=104, y=566, rot=0.2),
             art.pea('burst pea', 1.3, x=246, y=430), art.pea('burst pea 2', 1.1, x=176, y=556, c='lemon'), art.pea('burst pea 3', 1.2, x=250, y=588)]
    for i, b_ in enumerate(burst):
        t_ = 1420 + i * 60
        arc_in(sc, b_, t_, (195 + (i % 3 - 1) * 30, 620), dur=560, lift=50 + (i % 3) * 25, spin=1.6 * (1 if i % 2 else -1))
        pop_in(sc, b_, t_, dur=320, from_scale=0.2, ease='out')
        sc.wiggle(b_, 'y', float(b_.attrs['y']), -6 - (i % 3) * 2, IDLE_MS / (1 + i % 2))
        if b_.attrs.get('rotation'):
            sc.wiggle(b_, 'rotation', float(b_.attrs['rotation']), 0.1 if i % 2 else -0.1, IDLE_MS)
    splash = node('Splash', [shape(f'drop {i}', ellipse(9, 9), fill('butterDk'), x=math.cos(a) * 30, y=math.sin(a) * 12)
                             for i, a in enumerate([3.4, 4.0, 4.7, 5.3, 5.9])], x=195, y=596)
    sc.key(splash, 'scaleX', [(0, 0.0, 'hold'), (1280, 0.0, 'out'), (1500, 2.6, 'in'), (1800, 3.2)])
    sc.key(splash, 'scaleY', [(0, 0.0, 'hold'), (1280, 0.0, 'out'), (1500, 2.2, 'in'), (1800, 1.6)])
    sc.key(splash, 'opacity', [(0, 1.0, 'hold'), (1500, 1.0, 'in'), (1800, 0.0)])
    # set dressing: gingham napkin + table garlic & tomato
    napkin = art.gingham('Napkin', 128, 92, cell=16, c='basil', bg='cream', x=26, y=702, rot=-0.32)
    tom = art.tomato('Table tomato', 0.7, x=346, y=734, rot=0.2)
    gar = art.garlic('Table garlic', 0.75, x=300, y=724, rot=-0.2)
    for i, o in enumerate((napkin, gar, tom)):
        sc.key(o, 'y', [(0, float(o.attrs['y']) + 80, 'hold'), (60 + i * 70, float(o.attrs['y']) + 80, 'back'), (480 + i * 70, float(o.attrs['y']))])
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([node('Hover', hover), node('Burst', burst), node('Waves', pieces), splash, gar, tom, napkin]))
    return sc


# ============================================================================ 3. Recipes tried
# The cookbook is a lit 3D book drawn on the GPU (scripts/book.luau + book.wgsl). Its printed
# surfaces (ten page faces, the endpaper and the cover) are one vector artboard, "Cookbook pages",
# laid out as an atlas the script renders once into a texture. Cell geometry must match book.luau.
ATLAS_COLS, ATLAS_ROWS = 5, 3
CELL_W, CELL_H = 150, 198          # atlas pitch (points)
FACE_W, FACE_H = 146, 194          # one page face, inset 2 pt in its cell
RECIPES = [
    # (title, meta, accent, motif, ingredients, method, hand note)
    ('Tomato soup', 'serves 4 · 35 min', 'tomato', lambda: art.tomato('art', 0.62),
     '6 ripe tomatoes\n1 onion, 2 garlic cloves\nolive oil, salt\na fistful of basil',
     '1. Soften the onion and garlic in oil.\n2. Add the tomatoes; simmer 20 min.\n3. Blend with the basil.\n4. Season, then a swirl of oil.',
     'roast them first!'),
    ('Lemon orzo', 'serves 2 · 20 min', 'lemon', lambda: art.lemon_slice('art', 0.72),
     '200 g orzo\n1 lemon, zest + juice\nbutter, parmesan\npeas, black pepper',
     '1. Toast the orzo in butter.\n2. Add stock a ladle at a time.\n3. Stir in peas, zest, juice.\n4. Finish with parmesan.',
     'double the zest'),
    ('Mushroom risotto', 'serves 4 · 45 min', 'onion', lambda: art.mushroom('art', 0.72),
     '300 g arborio rice\n400 g mushrooms\n1 shallot, thyme\nwhite wine, stock',
     '1. Brown the mushrooms hard.\n2. Sweat the shallot; add rice.\n3. Wine, then stock, stirring.\n4. Fold the mushrooms back in.',
     'Sunday favourite'),
    ('Chili beans', 'serves 6 · 1 hr', 'carrot', lambda: art.chili('art', 0.72, rot=0.6),
     '2 tins kidney beans\n1 tin tomatoes\n2 chilies, cumin\nonion, peppers',
     '1. Fry the onion and peppers.\n2. Toast the cumin and chili.\n3. Add beans and tomatoes.\n4. Simmer low for 40 min.',
     'better next day'),
    ('Basil pesto', 'makes 1 jar · 10 min', 'basil', lambda: art.leaf('art', 0.9, rot=0.8),
     '2 big bunches basil\n50 g pine nuts\nparmesan, 1 garlic clove\ngood olive oil',
     '', ''),
]


def _cell_origin(idx):
    return (idx % ATLAS_COLS) * CELL_W + (CELL_W - FACE_W) / 2, (idx // ATLAS_COLS) * CELL_H + (CELL_H - FACE_H) / 2


def _page_front(idx, r, page_no):
    title, meta, accent, motif, ingr, _m, _n = r
    ox, oy = _cell_origin(idx)
    ttl = style('display', 15, 800, 'aub', lh=16, ls=-0.3, opsz=24, name='Page title')
    met = style('body', 7.5, 600, 'aubLt', name='Page meta')
    hd = style('hand', 12, 700, 'tomato', name='Page hand')
    body = style('body', 7.5, 400, 'aub', lh=10, name='Page body')
    pg = style('hand', 10, 600, 'aubLt', name='Page number')
    art_el = motif()
    art_el.attrs['x'] = 73.0
    art_el.attrs['y'] = 78.0
    kids = [
        text('title', [(ttl, title, None, None)], x=12, y=16, width=122, sizing='autoHeight'),
        text('meta', [(met, meta, None, None)], x=12, y=35, width=122, sizing='autoHeight'),
        art_el,
        shape('photo', rect(122, 56, 8, 0, 0), fill(accent), x=12, y=50, op=0.32),
        text('ingredients head', [(hd, 'you will need', None, None)], x=12, y=110, rot=-0.03),
        text('ingredients', [(body, ingr, None, None)], x=12, y=127, width=122, sizing='autoHeight'),
        text('page', [(pg, str(page_no), None, None)], x=73, y=180, ox=0.5),
        shape('band', rect(FACE_W, 8, 0, 0, 0), fill(accent), x=0, y=0),
        shape('paper', rect(FACE_W, FACE_H, 0, 0, 0), fill('cream')),
    ]
    return node(f'Face {idx}', kids, x=ox, y=oy)


def _page_back(idx, r, page_no):
    title, _meta, accent, _motif, _i, method, note = r
    ox, oy = _cell_origin(idx)
    hd = style('display', 12, 800, 'aub', lh=13, opsz=18, name='Back head')
    body = style('body', 7.5, 400, 'aub', lh=11, name='Back body')
    hand = style('hand', 13, 700, 'tomato', name='Back note')
    pg = style('hand', 10, 600, 'aubLt', name='Page number')
    kids = [
        text('note', [(hand, note, None, None)], x=16, y=150, rot=-0.07),
        shape('note line', smooth([(0, 0), (30, 2), (62, -1)], False), stroke('tomato', 1.4), x=16, y=170, rot=-0.07),
        text('method head', [(hd, 'Method', None, None)], x=12, y=16),
        text('method', [(body, method, None, None)], x=12, y=36, width=122, sizing='autoHeight'),
        text('page', [(pg, str(page_no), None, None)], x=73, y=180, ox=0.5),
        shape('stain', ellipse(40, 32), fill('butterDk'), x=104, y=146, op=0.55),
        shape('stain ring', ellipse(40, 32), stroke('butterDk', 2), x=106, y=148, op=0.7),
        shape('band', rect(FACE_W, 8, 0, 0, 0), fill(accent), x=0, y=0, op=0.55),
        shape('paper', rect(FACE_W, FACE_H, 0, 0, 0), fill('cream')),
    ]
    return node(f'Face {idx}', kids, x=ox, y=oy)


def _endpaper(idx):
    ox, oy = _cell_origin(idx)
    plate_t = style('hand', 17, 700, 'aub', name='Bookplate')
    plate_s = style('body', 7, 600, 'aubLt', ls=1.2, name='Bookplate small')
    kids = [
        text('plate name', [(plate_t, 'kitchen notes', None, None)], x=73, y=88, ox=0.5, rot=-0.03),
        text('plate small', [(plate_s, 'FROM THE KITCHEN OF', None, None)], x=73, y=76, ox=0.5),
        art.scallop_ticket('plate', 104, 40, c='butter', edge='tomato', x=73, y=97),
        art.gingham('gingham', FACE_W, FACE_H, cell=12, c='tomato', bg='cream', x=FACE_W / 2, y=FACE_H / 2),
    ]
    return node(f'Face {idx}', kids, x=ox, y=oy)


def _cover(idx):
    ox, oy = _cell_origin(idx)
    lab = style('display', 20, 800, 'tomato', ls=-0.6, opsz=36, name='Cover title')
    sub = style('hand', 13, 700, 'aub', name='Cover sub')
    kids = [
        text('cover title', [(lab, 'Simmer', None, None)], x=73, y=70, ox=0.5),
        text('cover sub', [(sub, 'recipes & notes', None, None)], x=73, y=96, ox=0.5),
        shape('label', rect(104, 62, 6), fill('cream'), x=73, y=92),
        shape('label ink', rect(104, 62, 6), fill('ink25'), x=76, y=95),
        shape('rule', rect(FACE_W - 20, FACE_H - 20, 10), stroke('tomatoLt', 2), x=73, y=97),
        shape('cloth', rect(FACE_W, FACE_H, 0, 0, 0), fill('tomato')),
    ]
    return node(f'Face {idx}', kids, x=ox, y=oy)


def cookbook_atlas():
    """The printed surfaces of the 3D cookbook, as one atlas artboard (see book.luau for the cells)."""
    ab = E('Artboard', isComponent=True, width=float(ATLAS_COLS * CELL_W), height=float(ATLAS_ROWS * CELL_H),
           name='Cookbook pages', x=500.0, y=2560.0, clip=True)
    st = E('LayoutComponentStyle', name='Artboard Style')
    ab.attrs['styleId'] = st.id
    faces = []
    for i in range(4):
        faces.append(_page_front(i, RECIPES[i], 2 * i + 1))
        faces.append(_page_back(5 + i, RECIPES[i], 2 * i + 2))
    faces.append(_page_front(4, RECIPES[4], 9))
    faces.append(_endpaper(9))
    faces.append(_cover(10))
    ab.add(st, *faces)
    EXTRA.append((ab, None))
    return ab


def scene3(x_stage):
    sc = Scene(3, NAMES[3], x_stage)
    hero, tb = metric_copy(sc, 3, 'right')
    # The book: a ScriptedDrawable over the art box (0, 380)-(390, 770). It drops onto the table
    # closed, the cover swings open, and four leaves curl over the spine one after another, each
    # landing on the pile it passed over (depth-tested, so a turned leaf never stays on top).
    # `progress` is the entrance playhead (0-2000 ms); `idle` drives a small breeze in the idle loop.
    atlas = cookbook_atlas()
    book_p = E('ScriptInputNumber', propertyValue=0.0, name='progress')
    book_i = E('ScriptInputNumber', propertyValue=0.0, name='idle')
    book = E('ScriptedDrawable', [book_p, book_i, E('ScriptInputArtboard', artboardId=atlas.id, name='atlas')],
             scriptAssetId=SCRIPT_BOOK, name='Cookbook 3D', x=0.0, y=380.0)
    sc.key(book_p, 'propertyValue', [(0, 0.0, 'lin'), (2000, 1.0)])
    sc.idle.ms(book_i, 'propertyValue', [(0, 0.0, 'lin'), (IDLE_MS, 1.0)])
    # handwritten note + sparkles stay vector collage around the book
    note_st = hand('n', 26, 'tomato', 700)
    note = text('Note', [(note_st, 'make again!', None, None)], x=40, y=694, rot=-0.08)
    arrow_g, arrow_trim, arrow_head = art.handwritten_arrow('Note arrow', [(0, 0), (10, -24), (34, -44)], c='tomato', x=150, y=694)
    sc.key(note, 'opacity', [(0, 0.0, 'hold'), (1700, 0.0, 'soft'), (1950, 1.0)])
    sc.enter.ms(arrow_trim, 'end', [(0, 0.0, 'hold'), (1800, 0.0, 'soft'), (2100, 1.0)])
    sc.settle(arrow_trim, 'end', 1.0)
    sc.key(arrow_head, 'opacity', [(0, 0.0, 'hold'), (2050, 0.0, 'lin'), (2100, 1.0)])
    stars = [art.sparkle(f'spark {i}', 0.8, 'lemon', x=x, y=y) for i, (x, y) in enumerate([(40, 420), (352, 650), (70, 668)])]
    for i, s_ in enumerate(stars):
        pop_in(sc, s_, 1500 + i * 120, dur=360, rot_from=-1.2)
        sc.wiggle(s_, 'rotation', 0.0, 0.5, IDLE_MS / (i + 1))
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([note, arrow_g, *stars, book]))
    return sc


# ============================================================================ 4. Cuisines explored
def cluster(name, items):
    return node(name, items)


def scene4(x_stage):
    sc = Scene(4, NAMES[4], x_stage)
    hero, tb = metric_copy(sc, 4, 'left')
    cx, cy = 195, 572
    sauce_trim = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    spiral_pts = [(math.cos(a) * r, math.sin(a) * r) for a, r in [(t * 0.6, 8 + t * 3.2) for t in range(0, 18)]]
    sauce = shape('Sauce spiral', smooth(spiral_pts, False), [E('Stroke', [E('SolidColor', colorValue=col('tomato'), name='Color'), sauce_trim],
                                                                 thickness=7.0, cap='round', join='round', name='Stroke')], x=cx, y=cy)
    sc.enter.ms(sauce_trim, 'end', [(0, 0.0, 'hold'), (300, 0.0, 'soft'), (1200, 1.0)])
    sc.settle(sauce_trim, 'end', 1.0)
    herbs = [shape(f'herb {i}', ellipse(7, 4), fill('basil'), x=cx + math.cos(i * 1.7) * 44, y=cy + math.sin(i * 1.7) * 40, rot=i) for i in range(7)]
    plate = art.plate('Plate', 196, x=cx, y=cy)
    sc.key(plate, 'scaleX', [(0, 0.2, 'hold'), (0, 0.2, 'back'), (520, 1.0)])
    sc.key(plate, 'scaleY', [(0, 0.2, 'hold'), (0, 0.2, 'back'), (520, 1.0)])
    sc.key(plate, 'rotation', [(0, -0.6, 'hold'), (0, -0.6, 'out'), (700, 0.0)])

    clusters = [
        cluster('Arrangement A', [art.leaf('a leaf', 0.8, x=-26, y=-18, rot=-0.8), art.tomato('a tomato', 0.75, x=6, y=4),
                                  art.tomato_half('a half', 0.6, x=34, y=-20, rot=0.3), art.leaf('a leaf2', 0.6, x=30, y=24, rot=1.2, c='basilLt')]),
        cluster('Arrangement B', [art.ginger('b ginger', 0.9, x=-10, y=10, rot=0.2), art.lemon_slice('b lime', 0.7, x=28, y=-14),
                                  shape('b scallion', rect(6, 70, 3), fill('basil'), x=-30, y=-14, rot=0.6), shape('b scallion2', rect(5, 60, 3), fill('basilLt'), x=-22, y=-20, rot=0.8)]),
        cluster('Arrangement C', [art.avocado('c avocado', 0.85, x=-18, y=0, rot=-0.3), art.corn('c corn', 1.0, x=26, y=20), art.chili('c chili', 0.7, x=30, y=-24, rot=1.0)]),
        cluster('Arrangement D', [art.pomegranate('d pomegranate', 0.8, x=12, y=-6), art.lemon_slice('d lemon', 0.65, x=-30, y=16),
                                  art.pea('d chickpea', 1.4, x=-24, y=-22, c='mush'), art.pea('d chickpea2', 1.3, x=-12, y=-32, c='mush'), art.pea('d chickpea3', 1.4, x=36, y=26, c='mush')]),
    ]
    angles = [-2.35, -0.75, 2.35, 0.75]    # NW, NE, SW, SE
    radius = 140
    for cl in clusters:
        cl.attrs['scaleX'] = 1.18
        cl.attrs['scaleY'] = 1.18
    # butter swooshes: each arrangement leaves a curved trail as it spirals in (concept)
    swooshes = []
    for i, a in enumerate(angles):
        trim = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
        pts_ = [(math.cos(a - 1.05 + k * 0.15) * (rr), math.sin(a - 1.05 + k * 0.15) * (rr))
                for k, rr in enumerate([150, 146, 141, 136, 131, 126, 121])]
        sw = shape(f'Swoosh {i}', smooth(pts_, False), [E('Stroke', [E('SolidColor', colorValue=col('butterDk'), name='Color'), trim],
                                                         thickness=7.0, cap='round', join='round', name='Stroke')], x=cx, y=cy, op=0.85)
        t = 250 + i * 110
        sc.enter.ms(trim, 'end', [(0, 0.0, 'hold'), (t + 300, 0.0, 'soft'), (t + 1000, 1.0)])
        sc.enter.ms(trim, 'start', [(0, 0.0, 'hold'), (t + 700, 0.0, 'soft'), (t + 1500, 0.55)])
        sc.settle(trim, 'end', 1.0)
        sc.settle(trim, 'start', 0.55)
        swooshes.append(sw)
    arms = []
    for i, (cl, a) in enumerate(zip(clusters, angles)):
        cl.attrs['x'] = float(radius)
        arm = node(f'Orbit arm {i}', [cl], x=cx, y=cy, rot=a)
        cl.attrs['rotation'] = float(-a)
        t = 250 + i * 110
        sc.key(arm, 'rotation', [(0, a - 2.8, 'hold'), (t, a - 2.8, 'out'), (t + 1150, a)])
        sc.key(cl, 'rotation', [(0, -(a - 2.8), 'hold'), (t, -(a - 2.8), 'out'), (t + 1150, -a)])
        sc.key(cl, 'x', [(0, 330.0, 'hold'), (t, 330.0, 'out'), (t + 1150, float(radius))])
        sc.key(cl, 'opacity', [(0, 0.0, 'hold'), (t, 0.0, 'lin'), (t + 200, 1.0)])
        # idle: the arrangements keep drifting around the plate, very slowly
        sc.idle.ms(arm, 'rotation', [(0, a, 'inout'), (IDLE_MS / 2, a + 0.05, 'inout'), (IDLE_MS, a)])
        sc.idle.ms(cl, 'rotation', [(0, -a, 'inout'), (IDLE_MS / 2, -a - 0.05, 'inout'), (IDLE_MS, -a)])
        arms.append(arm)
    notes_txt = [('so fresh!', 6, 552, -0.1), ('a little zesty', 296, 560, 0.06), ('smoky?', 18, 712, -0.05), ('new favourite', 270, 712, 0.05)]
    notes = []
    for i, (t_, x, y, r) in enumerate(notes_txt):
        n = text(f'Note {i}', [(hand('n', 21, 'aub', 600), t_, None, None)], x=x, y=y, rot=r)
        sc.key(n, 'opacity', [(0, 0.0, 'hold'), (1500 + i * 90, 0.0, 'soft'), (1750 + i * 90, 1.0)])
        sc.key(n, 'y', [(0, y + 10.0, 'hold'), (1500 + i * 90, y + 10.0, 'back'), (1800 + i * 90, float(y))])
        notes.append(n)
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([*notes, *arms, *herbs, sauce, plate, *swooshes]))
    return sc


# ============================================================================ 5. New ingredients
def scene5(x_stage):
    sc = Scene(5, NAMES[5], x_stage)
    hero, tb = metric_copy(sc, 5, 'right')
    shelves = []
    for i, (y, rot, x0, x1) in enumerate([(548, -0.025, 22, 368), (712, 0.02, 18, 372)]):
        plank = node(f'Shelf {i}', [
            shape('grain', smooth([(-150, -2), (-40, 1), (60, -3), (150, 0)], False), stroke('woodDk', 1.6), op=0.6),
            shape('plank', rect(x1 - x0, 16, 4), fill('wood')),
            shape('plank ink', rect(x1 - x0, 16, 4), fill('ink25'), x=4, y=5),
            shape('bracket L', straight([(-120, 8), (-104, 8), (-120, 28)], True, radius=2), fill('aub')),
            shape('bracket R', straight([(120, 8), (104, 8), (120, 28)], True, radius=2), fill('aub')),
        ], x=(x0 + x1) / 2, y=y + 8, rot=rot)
        sc.key(plank, 'scaleX', [(0, 0.0, 'hold'), (40 + i * 120, 0.0, 'snap'), (460 + i * 120, 1.0)])
        shelves.append(plank)
    jar_specs = [
        # x, base y, w, h, lid, spice, kind
        (58, 548, 50, 82, 'tomato', 'carrot', 0), (120, 548, 44, 100, 'basil', 'tomatoDk', 2), (182, 548, 56, 66, 'aub', 'lemon', 1),
        (244, 548, 42, 88, 'carrot', 'basilLt', 0),
        (52, 712, 46, 70, 'lemon', 'woodDk', 1), (112, 712, 52, 92, 'tomato', 'onion', 0), (176, 712, 40, 78, 'basil', 'carrot', 2),
        (234, 712, 54, 64, 'aub', 'tomato', 1), (300, 712, 46, 98, 'tomatoDk', 'lemon', 0), (350, 712, 34, 60, 'basilDk', 'mush', 2),
    ]
    jars = []
    rnd = random.Random(5)
    for i, (x, y, w, h, lid, spice, kind) in enumerate(jar_specs):
        rot = (-0.03 if i % 2 else 0.025) + (-0.025 if y < 600 else 0.02)
        j = art.jar(f'Jar {i}', w, h, lid=lid, spice=spice, x=x, y=y, rot=rot, kind=kind)
        t = 420 + i * 95
        start = (x - 60 + rnd.uniform(-20, 20), y + 140)
        sc.key(j, 'x', [(0, start[0], 'hold'), (t, start[0], 'soft'), (t + 420, float(x))])
        sc.key(j, 'y', [(0, start[1], 'hold'), (t, start[1], 'out'), (t + 230, float(y) - 70, 'in'), (t + 420, float(y))])
        # squash on landing, stretch on take-off
        sc.key(j, 'scaleY', [(0, 1.0, 'hold'), (t - 80, 1.0, 'out'), (t, 0.82, 'out'), (t + 120, 1.12, 'in'), (t + 420, 0.84, 'back'), (t + 620, 1.0)])
        sc.key(j, 'scaleX', [(0, 1.0, 'hold'), (t - 80, 1.0, 'out'), (t, 1.14, 'out'), (t + 120, 0.92, 'in'), (t + 420, 1.16, 'back'), (t + 620, 1.0)])
        sc.key(j, 'opacity', [(0, 0.0, 'hold'), (t - 80, 0.0, 'lin'), (t, 1.0)])
        sc.wiggle(j, 'rotation', rot, 0.05 if i % 2 else -0.05, IDLE_MS / (1 + i % 2))
        jars.append(j)
    # a pinch of spice drifting down from a tilted jar
    pinch = node('Pinch', [shape(f'grain {i}', ellipse(4, 4), fill('carrot'), x=rnd.uniform(-10, 10), y=i * 14) for i in range(6)], x=150, y=430)
    sc.key(pinch, 'opacity', [(0, 0.0, 'hold'), (1700, 0.0, 'soft'), (1900, 1.0)])
    sc.idle.ms(pinch, 'y', [(0, 430.0, 'lin'), (IDLE_MS, 460.0)])
    sc.idle.ms(pinch, 'opacity', [(0, 0.0, 'lin'), (IDLE_MS * 0.2, 1.0, 'lin'), (IDLE_MS * 0.8, 1.0, 'lin'), (IDLE_MS, 0.0)])
    tag = text('Tag', [(hand('t', 25, 'tomato', 700), 'new on the shelf', None, None)], x=40, y=394, rot=-0.06)
    sc.key(tag, 'opacity', [(0, 0.0, 'hold'), (1600, 0.0, 'soft'), (1850, 1.0)])
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([tag, pinch, *jars[:4], shelves[0], *jars[4:], shelves[1]]))
    return sc


# ============================================================================ 6. Favorite recipe cooks
def scene6(x_stage):
    sc = Scene(6, NAMES[6], x_stage)
    hero, tb = metric_copy(sc, 6, 'left')
    cx, cy = 210, 572
    rnd = random.Random(6)
    grains = []
    for i in range(34):
        a = rnd.uniform(0, math.tau)
        r = math.sqrt(rnd.uniform(0, 1)) * 56
        grains.append(shape(f'orzo {i}', ellipse(9, 4.2), fill('garlic' if i % 3 else 'butterDk'), x=math.cos(a) * r, y=math.sin(a) * r, rot=rnd.uniform(0, 3)))
    bowl = node('Orzo bowl', [
        art.leaf('bowl basil', 0.6, x=-18, y=-26, rot=0.7), art.leaf('bowl basil2', 0.45, x=-34, y=-6, rot=2.0, c='basilLt'),
        art.lemon_slice('bowl lemon', 0.62, x=22, y=12),
        *grains,
        shape('broth', ellipse(132, 132), fill('butter')),
        shape('inner', ellipse(148, 148), fill('aubLt')),
        shape('rim', ellipse(172, 172), fill('aub')),
        art.ink(ellipse(172, 172), (6, 7)),
    ], x=cx, y=cy)
    sc.key(bowl, 'y', [(0, -160.0, 'hold'), (260, -160.0, 'in'), (700, float(cy) + 8, 'back'), (900, float(cy))])
    sc.key(bowl, 'rotation', [(0, 0.0, 'hold'), (300, 0.0, 'out'), (1500, 4 * math.pi)])
    sc.key(bowl, 'scaleX', [(0, 1.0, 'hold'), (700, 1.0, 'out'), (760, 1.1, 'out'), (900, 1.0)])
    sc.key(bowl, 'scaleY', [(0, 1.0, 'hold'), (700, 1.0, 'out'), (760, 0.88, 'out'), (900, 1.0)])
    sc.idle.ms(bowl, 'rotation', [(0, 4 * math.pi, 'lin'), (IDLE_MS, 4 * math.pi + math.tau)])
    # the bowl's spin throws out a scalloped medallion
    medal = node('Medallion', [
        shape('ring', ellipse(222, 222), stroke('tomato', 3, extra=E('DashPath', [E('Dash', length=10.0, name='On'), E('Dash', length=7.0, name='Off')], name='Dashes'))),
        shape('scallop', star(292, 292, 26, 0.92, 12), [fill('butter'), stroke('tomato', 4)]),
        shape('scallop ink', star(292, 292, 26, 0.92, 12), fill('tomato'), x=6, y=7),
    ], x=cx, y=cy)
    sc.key(medal, 'scaleX', [(0, 0.0, 'hold'), (820, 0.0, 'back'), (1350, 1.0)])
    sc.key(medal, 'scaleY', [(0, 0.0, 'hold'), (820, 0.0, 'back'), (1350, 1.0)])
    sc.key(medal, 'rotation', [(0, 1.2, 'hold'), (820, 1.2, 'out'), (1500, 0.0)])
    sc.wiggle(medal, 'rotation', 0.0, 0.04, IDLE_MS)
    tails = []
    for i, sgn in enumerate((-1, 1)):
        t = shape(f'Ribbon tail {i}', straight([(-16, 0), (16, 0), (16, 96), (0, 82), (-16, 96)], True), [fill('tomato')], x=cx + sgn * 40, y=cy + 92, rot=sgn * 0.32)
        sc.key(t, 'scaleY', [(0, 0.0, 'hold'), (1150 + i * 80, 0.0, 'back'), (1550 + i * 80, 1.0)])
        sc.wiggle(t, 'rotation', sgn * 0.32, sgn * 0.06, IDLE_MS / 2)
        tails.append(t)
    rst = style('hand', 26, 700, 'aub', name='Recipe')
    rname = text('Recipe name', [(rst, 'Lemon orzo', 'favoriteRecipeName', None)], x=-104, y=-17, width=208, height=34, sizing='fixed',
                 align='center', overflow='ellipsis', wrap='wrap')
    banner = node('Banner', [rname, shape('band', rect(232, 40, 6), [fill('cream'), stroke('aub', 2.5)]),
                             shape('band ink', rect(232, 40, 6), fill('ink25'), x=4, y=5)], x=cx, y=cy + 118, rot=-0.03)
    sc.key(banner, 'scaleX', [(0, 0.0, 'hold'), (1350, 0.0, 'back'), (1800, 1.0)])
    sc.key(banner, 'opacity', [(0, 0.0, 'hold'), (1350, 0.0, 'lin'), (1450, 1.0)])
    # pot pours orzo into the bowl (pot pose 6 sits up-left, tilted)
    stream = []
    for i in range(7):
        g = shape(f'pour {i}', ellipse(8, 4), fill('garlic'), x=150, y=470)
        t = 260 + i * 90
        sc.enter.ms(g, 'x', [(0, 150.0, 'hold'), (t, 150.0, 'lin'), (t + 420, cx - 10 + i * 3.0)])
        sc.enter.ms(g, 'y', [(0, 470.0, 'hold'), (t, 470.0, 'drop'), (t + 420, float(cy) - 10)])
        sc.enter.ms(g, 'opacity', [(0, 0.0, 'hold'), (t, 1.0, 'hold'), (t + 420, 0.0, 'hold')])
        sc.settle(g, 'opacity', 0.0)
        stream.append(g)
    note = text('Note', [(hand('n', 24, 'tomato', 700), 'again & again', None, None)], x=262, y=404, rot=0.08)
    sc.key(note, 'opacity', [(0, 0.0, 'hold'), (1600, 0.0, 'soft'), (1850, 1.0)])
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([note, *stream, banner, bowl, *tails, medal]))
    return sc


# ============================================================================ 7. Shared meals
def place_setting(name, napkin_c):
    return node(name, [
        shape('fork', straight([(0, -26), (0, 26)], False), stroke('aub', 3), x=-50),
        shape('fork tines', straight([(-5, -26), (-5, -14), (5, -14), (5, -26)], False), stroke('aub', 2.5), x=-50),
        shape('knife', rect(6, 52, 3), fill('aubLt'), x=50),
        art.plate('plate', 76),
        shape('napkin', straight([(-30, 20), (30, 20), (0, -10)], True, radius=4), fill(napkin_c), x=0, y=38),
    ])


def scene7(x_stage):
    sc = Scene(7, NAMES[7], x_stage)
    hero, tb = metric_copy(sc, 7, 'right')
    cx, cy, d = 195, 576, 336
    mask = shape('Table mask', ellipse(d, d), fill('01FFFFFF'), x=cx, y=cy)
    cloth = art.gingham('Tablecloth', d + 20, d + 20, cell=21, c='tomato', bg='cream', x=cx, y=cy)
    cloth.add(E('ClippingShape', sourceId=mask.id, name='Clip'))
    edge = shape('Table edge', ellipse(d, d), stroke('aub', 3), x=cx, y=cy)
    shadow = shape('Table shadow', ellipse(d, d), fill('ink15'), x=cx + 8, y=cy + 12)
    table = node('Table', [edge, cloth, mask, shadow])
    sc.key(table, 'scaleX', [(0, 0.6, 'hold'), (0, 0.6, 'back'), (520, 1.0)])
    sc.key(table, 'scaleY', [(0, 0.6, 'hold'), (0, 0.6, 'back'), (520, 1.0)])
    sc.key(table, 'opacity', [(0, 0.0, 'hold'), (0, 0.0, 'lin'), (200, 1.0)])
    table.attrs['x'] = 0.0
    # scale the table around its centre: wrap
    table_wrap = node('Table wrap', [table], x=cx, y=cy)
    for c in (edge, cloth, mask, shadow):
        c.attrs['x'] = float(c.attrs['x']) - cx
        c.attrs['y'] = float(c.attrs['y']) - cy
    sc.final.pop((table.id, 'scaleX', 'Double'), None)
    sc.enter.keys.pop(table.id, None)
    sc.key(table_wrap, 'scaleX', [(0, 0.6, 'hold'), (0, 0.6, 'back'), (520, 1.0)])
    sc.key(table_wrap, 'scaleY', [(0, 0.6, 'hold'), (0, 0.6, 'back'), (520, 1.0)])
    sc.key(table_wrap, 'opacity', [(0, 0.0, 'hold'), (0, 0.0, 'lin'), (200, 1.0)])
    sc.key(table_wrap, 'rotation', [(0, -0.4, 'hold'), (0, -0.4, 'out'), (700, 0.0)])
    settings = []
    napkins = ['basil', 'lemon', 'tomatoLt', 'basilLt', 'onion', 'carrot']
    r = 112
    for i in range(6):
        a = -math.pi / 2 + i * math.tau / 6 + math.pi / 6
        ps = place_setting(f'Setting {i}', napkins[i])
        holder = node(f'Seat {i}', [ps], x=cx, y=cy, rot=a + math.pi / 2)
        ps.attrs['y'] = float(-r)
        t = 520 + i * 90
        sc.key(ps, 'y', [(0, 0.0, 'hold'), (t, 0.0, 'back'), (t + 520, float(-r))])
        sc.key(ps, 'scaleX', [(0, 0.2, 'hold'), (t, 0.2, 'back'), (t + 520, 0.82)])
        sc.key(ps, 'scaleY', [(0, 0.2, 'hold'), (t, 0.2, 'back'), (t + 520, 0.82)])
        sc.key(ps, 'opacity', [(0, 0.0, 'hold'), (t, 0.0, 'lin'), (t + 160, 1.0)])
        sc.wiggle(ps, 'y', float(-r), -4, IDLE_MS / 2)
        settings.append(holder)
    glasses = []
    for i in range(6):
        a = -math.pi / 2 + i * math.tau / 6 + math.pi / 6 + 0.42
        g = node(f'Glass {i}', [shape('lemon', ellipse(10, 10), fill('lemon')), shape('glass', ellipse(22, 22), [fill('BFFFFFFF'), stroke('aub', 2)])],
                 x=cx + math.cos(a) * 150, y=cy + math.sin(a) * 150)
        pop_in(sc, g, 1250 + i * 60, dur=320)
        glasses.append(g)
    note = text('Note', [(hand('n', 24, 'basil', 700), 'pull up a chair', None, None)], x=26, y=396, rot=-0.07)
    sc.key(note, 'opacity', [(0, 0.0, 'hold'), (1600, 0.0, 'soft'), (1850, 1.0)])
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([note, *glasses, *settings, table_wrap]))
    return sc


# ============================================================================ 8. Cooking days
def scene8(x_stage):
    sc = Scene(8, NAMES[8], x_stage)
    hero, tb = metric_copy(sc, 8, 'left')
    cols, rows, cell, gap = 7, 5, 43.0, 4.5
    x0, y0 = 26.0, 404.0
    rnd = random.Random(8)
    cells, centers = [], {}
    for r_ in range(rows):
        for c in range(cols):
            x = x0 + c * (cell + gap) + cell / 2
            y = y0 + r_ * (cell + gap) + cell / 2
            centers[(r_, c)] = (x, y)
            cells.append(shape(f'day {r_}-{c}', rect(cell, cell, 7), [fill('cream'), stroke('aub', 1.6)], x=x, y=y, rot=rnd.uniform(-0.06, 0.06)))
    grid = node('Calendar', cells)
    sc.key(grid, 'opacity', [(0, 0.0, 'hold'), (60, 0.0, 'soft'), (380, 1.0)])
    sc.key(grid, 'y', [(0, 40.0, 'hold'), (60, 40.0, 'back'), (500, 0.0)])
    # serpentine order from the bottom row (nearest the pot) to the top
    order = []
    for k, r_ in enumerate(range(rows - 1, -1, -1)):
        cs_ = list(range(cols)) if k % 2 == 0 else list(range(cols - 1, -1, -1))
        order += [(r_, c) for c in cs_]
    pts = [(195, 690), (195, 650)]
    for i, rc in enumerate(order):
        x, y = centers[rc]
        if i:
            px, py = centers[order[i - 1]]
            if py == y:   # a little loop between neighbouring days
                mx = (px + x) / 2
                pts += [(mx - (4 if x > px else -4), y - 10), (mx + (2 if x > px else -2), y - 18), (mx + (6 if x > px else -6), y - 9)]
        pts.append((x, y))
    stitch_trim = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    stitch_trim2 = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    stitch = node('Steam stitch', [
        shape('thread', smooth(pts, False, tension=0.9), [E('Stroke', [E('SolidColor', colorValue=col('tomato'), name='Color'), stitch_trim],
                                                          thickness=2.2, cap='round', join='round', name='Stroke')]),
        shape('steam', smooth(pts, False, tension=0.9), [E('Stroke', [E('SolidColor', colorValue=col('FFFFFBEF'), name='Color'), stitch_trim2],
                                                         thickness=9.0, cap='round', join='round', name='Stroke')]),
    ])
    t0, t1 = 380, 1700
    for tr_ in (stitch_trim, stitch_trim2):
        sc.enter.ms(tr_, 'end', [(0, 0.0, 'hold'), (t0, 0.0, 'lin'), (t1, 1.0)])
        sc.settle(tr_, 'end', 1.0)
    colors = ['tomato', 'basil', 'lemon', 'carrot', 'onion']
    marks = []
    for i, rc in enumerate(order):
        if rnd.random() < 0.3:
            continue
        x, y = centers[rc]
        m = node(f'mark {i}', [shape('dot', ellipse(24, 24), fill(colors[i % len(colors)])), art.ink(ellipse(24, 24), (2.5, 2.5))], x=x, y=y)
        t = t0 + (t1 - t0) * (i / len(order))
        pop_in(sc, m, t, dur=320)
        if i % 5 == 0:
            sc.wiggle(m, 'scaleX', 1.0, 0.12, IDLE_MS / 2)
            sc.wiggle(m, 'scaleY', 1.0, 0.12, IDLE_MS / 2)
        marks.append(m)
    note = text('Note', [(hand('n', 24, 'tomato', 700), 'slow Sundays', None, None)], x=250, y=650, rot=-0.06)
    sc.key(note, 'opacity', [(0, 0.0, 'hold'), (1700, 0.0, 'soft'), (1950, 1.0)])
    sc.inner.add(sc.copy_group([hero, tb]), sc.art_group([note, *marks, stitch, grid]))
    return sc


# ============================================================================ 9. Persona reveal
def emblem_spice_pot():
    body = smooth([(-60, -20), (60, -20), (56, 30), (40, 56), (-40, 56), (-56, 30)], True, corners=(0, 1))
    arm_l = node('arm L', [shape('arm', smooth([(0, 0), (-22, -14), (-34, -44)], False), stroke('aub', 7)), shape('hand', ellipse(14, 14), fill('aub'), x=-34, y=-46)], x=-56, y=6)
    arm_r = node('arm R', [shape('arm', smooth([(0, 0), (22, -16), (30, -48)], False), stroke('aub', 7)), shape('hand', ellipse(14, 14), fill('aub'), x=30, y=-50)], x=56, y=6)
    leg_l = node('leg L', [shape('leg', smooth([(0, 0), (-8, 24), (-18, 42)], False), stroke('aub', 7)), shape('foot', ellipse(22, 10), fill('aub'), x=-22, y=44)], x=-22, y=54)
    leg_r = node('leg R', [shape('leg', smooth([(0, 0), (10, 22), (22, 40)], False), stroke('aub', 7)), shape('foot', ellipse(22, 10), fill('aub'), x=26, y=42)], x=22, y=54)
    spices = node('spices', [shape(f'sp {i}', ellipse(7, 7), fill(['tomato', 'basil', 'lemon', 'carrot'][i % 4]), x=math.cos(i) * 40, y=-70 - (i % 3) * 14) for i in range(8)])
    lid = node('lid', [shape('knob', ellipse(16, 10), fill('aub'), y=-16), shape('lid', smooth([(-62, 0), (-40, -14), (0, -18), (40, -14), (62, 0)], True, corners=(0, 4)), fill('tomato')),
                       art.ink(smooth([(-62, 0), (-40, -14), (0, -18), (40, -14), (62, 0)], True, corners=(0, 4)), (3, 3))], x=-10, y=-40, rot=-0.35)
    face = node('face', [shape('eye L', smooth([(-8, 0), (0, -6), (8, 0)], False), stroke('aub', 4), x=-20, y=12),
                         shape('eye R', smooth([(-8, 0), (0, -6), (8, 0)], False), stroke('aub', 4), x=20, y=12),
                         shape('mouth', smooth([(-12, 0), (0, 12), (12, 0)], True), fill('aub'), y=26)])
    pot = node('dancer', [spices, lid, face, shape('body', body, fill('tomato')), art.ink(body, (5, 5)), arm_l, arm_r, leg_l, leg_r])
    return pot, dict(arm_l=arm_l, arm_r=arm_r, leg_l=leg_l, leg_r=leg_r, spices=spices, lid=lid)


def emblem_bowl():
    trims = []
    steams = []
    for i, dx in enumerate((-40, 0, 40)):
        g, tr, _ = art.steam_curl(f'bowl steam {i}', [(0, 0), (-14, -26), (8, -52), (-6, -80), (6, -104)], w=12, c='cream', x=dx, y=-40)
        steams.append(g)
        trims.append(tr)
    bowl = smooth([(-100, -20), (100, -20), (86, 30), (50, 62), (-50, 62), (-86, 30)], True, corners=(0, 1))
    grp = node('steaming bowl', steams + [
        shape('egg yolk', ellipse(16, 16), fill('lemon'), x=34, y=-26),
        shape('egg', ellipse(34, 26), fill('garlic'), x=34, y=-26),
        shape('noodle 1', smooth([(-60, -24), (-30, -30), (0, -22), (30, -30)], False), stroke('butterDk', 5)),
        shape('noodle 2', smooth([(-50, -18), (-20, -24), (10, -16)], False), stroke('butterDk', 5)),
        art.leaf('bowl herb', 0.5, x=-50, y=-28, rot=1.4),
        shape('broth', ellipse(196, 36), fill('butter'), y=-20),
        shape('band', rect(150, 8, 4), fill('lemon'), y=22),
        shape('bowl', bowl, [fill('tomato'), stroke('cream', 3)]),
        art.ink(bowl, (5, 6)),
    ])
    return grp, trims, steams


def emblem_tins():
    tins = []
    specs = [('basil', 'butter', 150, 44), ('lemon', 'tomato', 136, 42), ('tomato', 'cream', 120, 40)]
    y = 54
    for i, (body_c, lid_c, w, h) in enumerate(specs):
        t = node(f'tin {i}', [
            shape('label', rect(w * 0.45, 14, 4), fill('cream'), y=-h / 2 + 2),
            shape('lid', rect(w + 8, 10, 5, 0.5, 1), fill(lid_c), y=-h + 2),
            shape('tin', rect(w, h, 8, 0.5, 1), [fill(body_c), stroke('aub', 2.5)]),
            shape('tin ink', rect(w, h, 8, 0.5, 1), fill('ink25'), x=4, y=4),
        ], x=0, y=y)
        tins.append(t)
        y -= h + 10
    sparks = [art.sparkle(f'magic {i}', 0.9 - i * 0.15, 'lemon', x=x, y=yy) for i, (x, yy) in enumerate([(-92, -70), (96, -40), (70, -120)])]
    hat = shape('wizard tip', straight([(-14, 0), (14, 0), (4, -34)], True, radius=2), fill('aub'), x=0, y=y + 4)
    return node('stacked tins', sparks + [hat] + list(reversed(tins))), tins, sparks, hat


def emblem_mitt():
    rays = shape('sunburst', star(300, 300, 14, 0.62, 4), fill('lemon'))
    mitt_pts = [(-44, 70), (-50, 0), (-46, -50), (-20, -72), (8, -64), (14, -30), (30, -52), (52, -44), (50, -14), (36, 20), (40, 70)]
    mitt = node('mitt', [
        shape('patch', rect(36, 36, 4), fill('lemon'), x=-10, y=-10, rot=0.2),
        shape('cuff', rect(96, 30, 10), [fill('cream'), stroke('aub', 2.5)], y=80),
        shape('mitt', smooth(mitt_pts, True, corners=(0, 10)), [fill('tomato'), stroke('aub', 3)]),
        art.ink(smooth(mitt_pts, True, corners=(0, 10)), (5, 6)),
    ], rot=0.12)
    loaf = node('loaf', [shape('score', smooth([(-20, -6), (0, -12), (20, -6)], False), stroke('wood', 3)),
                         shape('bread', rect(90, 44, 22), [fill('FFD9A066'), stroke('aub', 2.5)])], x=74, y=86)
    return node('oven mitt', [loaf, mitt, rays]), rays, mitt, loaf


def scene9(x_stage):
    sc = Scene(9, NAMES[9], x_stage)
    lab = style('body', 18, 700, 'basil', lh=24, name='Persona label')
    nm = style('display', 46, 800, 'tomato', lh=46, ls=-1.4, opsz=72, name='Persona name')
    ds = style('body', 20, 400, 'aub', lh=26, name='Persona description')
    tb = sc.text_block(24, 100, 342, [(lab, 'Your personal style', 'personaLabel'), (nm, 'Flavor Explorer', 'personaName'), (ds, 'Always room for a new flavor.', 'personaDescription')])
    sc.reveal_text(tb, 1000, 1800, y=30)
    cx, cy = 195, 516
    halo_col = E('SolidColor', [bind(P('personaColor'), 37)], colorValue=col('butter'), name='Color')
    halo = node('Halo', [
        shape('halo ring', ellipse(356, 356), stroke('aub', 2, extra=E('DashPath', [E('Dash', length=3.0, name='On'), E('Dash', length=9.0, name='Off')], name='Dots'))),
        shape('halo burst', star(318, 318, 16, 0.8, 10), [E('Fill', [halo_col], name='Persona color'), stroke('aub', 3)]),
        shape('halo ink', star(318, 318, 16, 0.8, 10), fill('ink25'), x=6, y=7),
    ], x=cx, y=cy)
    sc.key(halo, 'scaleX', [(0, 0.0, 'hold'), (700, 0.0, 'back'), (1150, 1.0)])
    sc.key(halo, 'scaleY', [(0, 0.0, 'hold'), (700, 0.0, 'back'), (1150, 1.0)])
    sc.key(halo, 'rotation', [(0, -1.0, 'hold'), (700, -1.0, 'out'), (1300, 0.0)])
    sc.idle.ms(halo, 'rotation', [(0, 0.0, 'lin'), (IDLE_MS, math.tau / 16)])

    g0, p0 = emblem_spice_pot()
    g1, bowl_trims, _ = emblem_bowl()
    g2, tins, sparks, hat = emblem_tins()
    g3, rays, mitt, loaf = emblem_mitt()
    groups = [node(f'Persona {i}', [g], x=cx, y=cy, op=0.0, sx=1.2, sy=1.2) for i, g in enumerate((g0, g1, g2, g3))]
    # the ingredients the emblem throws out: a slow orbit round the reveal (shared by every persona)
    orbit_items = [art.lemon_slice('o lemon', 1.05), art.chili('o chili', 1.0, rot=0.6), art.leaf('o basil', 1.05, rot=-0.5),
                   art.onion('o onion', 0.8), art.tomato_half('o tomato', 0.95, rot=0.3), art.garlic('o garlic', 0.75),
                   art.carrot('o carrot', 0.8, rot=0.9), art.leaf('o basil 2', 0.9, rot=1.9, c='basilLt')]
    orbit_nodes = []
    for i, it in enumerate(orbit_items):
        a_ = -math.pi / 2 + math.pi / 8 + i * math.tau / 8
        ox_, oy_ = math.cos(a_) * 172, math.sin(a_) * 190
        holder = node(f'Orbit {i}', [it], x=ox_, y=oy_)
        t_ = 1050 + i * 45
        sc.key(holder, 'x', [(0, 0.0, 'hold'), (t_, 0.0, 'out'), (t_ + 520, ox_)])
        sc.key(holder, 'y', [(0, 0.0, 'hold'), (t_, 0.0, 'out'), (t_ + 520, oy_)])
        pop_in(sc, holder, t_, dur=420, from_scale=0.1, ease='back', rot_from=-2.5 if i % 2 else 2.5, rot_to=0.0)
        sc.wiggle(holder, 'rotation', 0.0, 0.18 if i % 2 else -0.18, IDLE_MS / 2)
        orbit_nodes.append(holder)
    orbit = node('Orbit', orbit_nodes, x=cx, y=cy)
    sc.idle.ms(orbit, 'rotation', [(0, 0.0, 'inout'), (IDLE_MS / 2, 0.06, 'inout'), (IDLE_MS, 0.0)])

    REV = 700
    reveals, idles, statics = [], [], []
    for j in range(4):
        r = Anim(f'Persona {j} reveal', ms2f(1900))
        i_ = Anim(f'Persona {j} idle', ms2f(IDLE_MS), loop='loop')
        s_ = Anim(f'Persona {j} static', 1)
        for q in range(4):
            r.ms(groups[q], 'opacity', [(0, 0.0, 'hold'), (REV, 1.0 if q == j else 0.0, 'hold')])
            s_.ms(groups[q], 'opacity', [(0, 1.0 if q == j else 0.0, 'hold')])
        reveals.append(r); idles.append(i_); statics.append(s_)

    # 0 Flavor Explorer: the pot bursts up and starts to dance
    r, i_, s_ = reveals[0], idles[0], statics[0]
    r.ms(g0, 'y', [(0, 160.0, 'hold'), (REV, 160.0, 'back'), (REV + 500, 0.0)])
    r.ms(g0, 'scaleX', [(0, 0.3, 'hold'), (REV, 0.3, 'back'), (REV + 500, 1.0)])
    r.ms(g0, 'scaleY', [(0, 0.3, 'hold'), (REV, 0.3, 'back'), (REV + 500, 1.0)])
    r.ms(g0, 'rotation', [(0, -0.6, 'hold'), (REV, -0.6, 'out'), (REV + 700, 0.0)])
    r.ms(p0['spices'], 'y', [(0, 60.0, 'hold'), (REV + 200, 60.0, 'out'), (REV + 800, 0.0)])
    r.ms(p0['spices'], 'opacity', [(0, 0.0, 'hold'), (REV + 200, 1.0, 'hold')])
    for nm_, a0, a1 in (('arm_l', 1.4, 0.0), ('arm_r', -1.4, 0.0)):
        r.ms(p0[nm_], 'rotation', [(0, a0, 'hold'), (REV + 300, a0, 'back'), (REV + 700, a1)])
    beat = IDLE_MS / 4
    for b in range(4):
        t = b * beat
        sgn = 1 if b % 2 == 0 else -1
        i_.ms(g0, 'rotation', [(t, 0.0, 'inout'), (t + beat * 0.5, 0.13 * sgn, 'inout')])
        i_.ms(p0['arm_l'], 'rotation', [(t, 0.0, 'inout'), (t + beat * 0.5, -0.5 if sgn > 0 else 0.2, 'inout')])
        i_.ms(p0['arm_r'], 'rotation', [(t, 0.0, 'inout'), (t + beat * 0.5, -0.2 if sgn > 0 else 0.5, 'inout')])
        i_.ms(p0['leg_l'], 'rotation', [(t, 0.0, 'inout'), (t + beat * 0.5, 0.35 if sgn > 0 else 0.0, 'inout')])
        i_.ms(p0['leg_r'], 'rotation', [(t, 0.0, 'inout'), (t + beat * 0.5, 0.0 if sgn > 0 else -0.35, 'inout')])
        i_.ms(g0, 'y', [(t, 0.0, 'out'), (t + beat * 0.5, -10.0, 'in')])
        i_.ms(p0['spices'], 'y', [(t, 0.0, 'inout'), (t + beat * 0.5, -8.0, 'inout')])
    for o in (g0, p0['arm_l'], p0['arm_r'], p0['leg_l'], p0['leg_r'], p0['spices']):
        i_.ms(o, 'rotation' if o is not p0['spices'] else 'y', [(IDLE_MS, 0.0)])
    i_.ms(g0, 'y', [(IDLE_MS, 0.0)])
    for o, props in ((g0, (('y', 0.0), ('scaleX', 1.0), ('scaleY', 1.0), ('rotation', 0.0))), (p0['spices'], (('y', 0.0), ('opacity', 1.0)))):
        for p, v in props:
            s_.ms(o, p, [(0, v, 'hold')])

    # 1 Comfort Cook: the bowl rises, steam draws on and keeps breathing
    r, i_, s_ = reveals[1], idles[1], statics[1]
    r.ms(g1, 'y', [(0, 200.0, 'hold'), (REV, 200.0, 'soft'), (REV + 650, 0.0)])
    for k_, trs in enumerate(bowl_trims):
        for tr in trs:
            r.ms(tr, 'end', [(0, 0.0, 'hold'), (REV + 400 + k_ * 120, 0.0, 'soft'), (REV + 1000 + k_ * 120, 1.0)])
            r.ms(tr, 'start', [(0, 0.0, 'hold')])
            ph = k_ * IDLE_MS / 3
            i_.ms(tr, 'end', [(0, 1.0, 'hold')])
            i_.ms(tr, 'start', [(0, 0.0, 'hold'), (ph, 0.0, 'soft'), (ph + 900, 1.0, 'hold'), (ph + 901, 0.0, 'hold'), (IDLE_MS, 0.0)])
            s_.ms(tr, 'end', [(0, 1.0, 'hold')]); s_.ms(tr, 'start', [(0, 0.0, 'hold')])
    i_.ms(g1, 'y', [(0, 0.0, 'inout'), (IDLE_MS / 2, -6.0, 'inout'), (IDLE_MS, 0.0)])
    s_.ms(g1, 'y', [(0, 0.0, 'hold')])

    # 2 Batch Wizard: tins drop and stack, squash on each landing, sparkles
    r, i_, s_ = reveals[2], idles[2], statics[2]
    for k_, t in enumerate(tins):
        y1 = float(t.attrs['y'])
        tt = REV + k_ * 170
        r.ms(t, 'y', [(0, y1 - 240, 'hold'), (tt, y1 - 240, 'drop'), (tt + 300, y1)])
        r.ms(t, 'opacity', [(0, 0.0, 'hold'), (tt, 0.0, 'lin'), (tt + 90, 1.0)])
        s_.ms(t, 'opacity', [(0, 1.0, 'hold')])
        r.ms(t, 'scaleY', [(0, 1.0, 'hold'), (tt + 300, 0.78, 'back'), (tt + 500, 1.0)])
        r.ms(t, 'scaleX', [(0, 1.0, 'hold'), (tt + 300, 1.16, 'back'), (tt + 500, 1.0)])
        for p, v in (('y', y1), ('scaleX', 1.0), ('scaleY', 1.0)):
            s_.ms(t, p, [(0, v, 'hold')])
    r.ms(hat, 'scaleY', [(0, 0.0, 'hold'), (REV + 800, 0.0, 'back'), (REV + 1100, 1.0)])
    s_.ms(hat, 'scaleY', [(0, 1.0, 'hold')])
    for k_, sp in enumerate(sparks):
        tt = REV + 900 + k_ * 110
        for p in ('scaleX', 'scaleY'):
            r.ms(sp, p, [(0, 0.0, 'hold'), (tt, 0.0, 'back'), (tt + 300, 1.0)])
            s_.ms(sp, p, [(0, 1.0, 'hold')])
            ph = k_ * 600
            i_.ms(sp, p, [(0, 1.0, 'hold'), (ph, 1.0, 'inout'), (ph + 300, 0.5, 'inout'), (ph + 600, 1.0, 'hold'), (IDLE_MS, 1.0)])
        i_.ms(sp, 'rotation', [(0, 0.0, 'lin'), (IDLE_MS, math.pi / 2)])
    i_.ms(tins[2], 'rotation', [(0, 0.0, 'inout'), (IDLE_MS * 0.25, 0.05, 'inout'), (IDLE_MS * 0.5, 0.0, 'inout'), (IDLE_MS * 0.75, -0.04, 'inout'), (IDLE_MS, 0.0)])

    # 3 Weekend Baker: the sunburst spins open behind a waving oven mitt
    r, i_, s_ = reveals[3], idles[3], statics[3]
    for p in ('scaleX', 'scaleY'):
        r.ms(rays, p, [(0, 0.0, 'hold'), (REV, 0.0, 'back'), (REV + 600, 1.0)])
        s_.ms(rays, p, [(0, 1.0, 'hold')])
    r.ms(rays, 'rotation', [(0, -2.0, 'hold'), (REV, -2.0, 'out'), (REV + 1000, 0.0)])
    i_.ms(rays, 'rotation', [(0, 0.0, 'lin'), (IDLE_MS, math.tau / 14)])
    r.ms(mitt, 'y', [(0, 220.0, 'hold'), (REV + 150, 220.0, 'back'), (REV + 650, 0.0)])
    r.ms(mitt, 'rotation', [(0, -0.6, 'hold'), (REV + 150, -0.6, 'back'), (REV + 800, 0.12)])
    i_.ms(mitt, 'rotation', [(0, 0.12, 'inout'), (IDLE_MS * 0.25, -0.1, 'inout'), (IDLE_MS * 0.5, 0.12, 'inout'), (IDLE_MS * 0.75, -0.1, 'inout'), (IDLE_MS, 0.12)])
    r.ms(loaf, 'x', [(0, 260.0, 'hold'), (REV + 500, 260.0, 'back'), (REV + 900, 74.0)])
    for o, p, v in ((mitt, 'y', 0.0), (mitt, 'rotation', 0.12), (loaf, 'x', 74.0), (rays, 'rotation', 0.0)):
        s_.ms(o, p, [(0, v, 'hold')])

    # persona layer: unique choreography per persona; a live personaIndex change re-reveals cleanly
    hidden = Anim('Persona hidden', 1)
    for g in groups:
        hidden.ms(g, 'opacity', [(0, 0.0, 'hold')])
    cs, pi, rm = P('currentScreen'), P('personaIndex'), P('reducedMotion')
    s_hidden = astate(hidden, 0, 0)
    s_rev = [astate(reveals[j], 260, -300 + j * 200) for j in range(4)]
    s_idle = [astate(idles[j], 520, -300 + j * 200) for j in range(4)]
    s_stat = [astate(statics[j], 780, -300 + j * 200) for j in range(4)]
    all_vis = s_rev + s_idle + s_stat
    for src in [s_hidden] + all_vis:
        for j in range(4):
            mine = src in (s_rev[j], s_idle[j], s_stat[j])
            if mine:
                continue
            src.add(trans(s_stat[j], [cond_num(cs, 9), cond_num(pi, j), cond_bool(rm, True)]),
                    trans(s_rev[j], [cond_num(cs, 9), cond_num(pi, j)]))
        if src is not s_hidden:
            src.add(trans(s_hidden, [cond_num(cs, 9, 'notEqual')], duration=450))
    for j in range(4):
        s_rev[j].add(trans(s_idle[j], [], exit_pct=100))
    sc.extra_layers.append(layer('Persona', s_hidden, [s_hidden] + all_vis))
    sc.extra_anims += [hidden] + reveals + idles + statics

    # the emblem lands with a little dust ring
    dust = shape('Landing ring', ellipse(240, 44), stroke('aub', 2.5), x=cx, y=cy + 152, op=0.0)
    sc.key(dust, 'opacity', [(0, 0.0, 'hold'), (1150, 0.0, 'lin'), (1200, 0.8, 'soft'), (1600, 0.0)])
    sc.key(dust, 'scaleX', [(0, 0.4, 'hold'), (1150, 0.4, 'out'), (1600, 1.4)])
    sc.settle(dust, 'opacity', 0.0)
    stage.bind_copy_width(tb)
    sc.inner.add(sc.copy_group([tb]), sc.art_group([orbit, *groups, dust, halo]))
    return sc


# ============================================================================ 10. Summary + share card
def mini_pot(scale=1.0):
    body = smooth([(-50, -12), (50, -12), (46, 20), (30, 42), (-30, 42), (-46, 20)], True, corners=(0, 1))
    lid = smooth([(-48, 0), (-30, -16), (0, -22), (30, -16), (48, 0)], True, corners=(0, 4))
    return node('Mini pot', [
        shape('w1', smooth([(0, 0), (-5, -10), (3, -20)], False), stroke('aub', 3), x=-12, y=-40),
        shape('w2', smooth([(0, 0), (-5, -10), (3, -20)], False), stroke('aub', 3), x=8, y=-44),
        shape('knob', ellipse(14, 9), fill('aub'), y=-34),
        shape('lid', lid, fill('tomato'), y=-12),
        shape('eye L', smooth([(-6, 0), (0, -4), (6, 0)], False), stroke('aub', 3), x=-14, y=10),
        shape('eye R', smooth([(-6, 0), (0, -4), (6, 0)], False), stroke('aub', 3), x=14, y=10),
        shape('smile', smooth([(-8, 0), (0, 6), (8, 0)], False), stroke('aub', 3), y=20),
        shape('h L', rect(16, 10, 5), fill('aub'), x=-54),
        shape('h R', rect(16, 10, 5), fill('aub'), x=54),
        shape('body', body, fill('tomato')),
        art.ink(body, (4, 4)),
    ], sx=scale, sy=scale)


# share card geometry: the tall card (the master; the host captures this one) and a wide
# arrangement of the same pieces for landscape and short stages. Card-local coordinates.
CARD = {
    False: dict(W=342, H=500, ticket=(318, 466), wm=(26, 24), yr=(26, 62), pot=(270, 62), chip=(38, 116), pname=(58, 102),
                big=(26, 142, 290), unit=(26, 214), tiles=[(26, 252), (176, 252), (26, 340), (176, 340)],
                name=(26, 428, 222), recipe=(26, 458, 222), stamp=(290, 464)),
    # the wide card is only shown scaled down (landscape, short stages), so its type is larger
    True: dict(W=700, H=360, ticket=(676, 326), wm=(26, 22), yr=(26, 62), pot=(262, 62), chip=(38, 118), pname=(58, 103),
               big=(26, 142, 290), unit=(26, 216), tiles=[(340, 30), (500, 30), (340, 132), (500, 132)],
               name=(26, 262, 280), recipe=(26, 296, 280), stamp=(622, 296), big_type=True),
}
# where each card sits in scene 10 (centre), see scene10 and scripts/stage.luau (motif fly-in)
CARD_CENTRE = {False: (195, 466), True: (195, 485)}
TILE = {False: dict(w=140, h=80, unit=15, lh=16, uy=42, uh=37, uw=122, val=30, vh=34),
        True: dict(w=150, h=92, unit=18, lh=19, uy=42, uh=50, uw=132, val=34, vh=38)}


def build_share_card(x_stage, wide=False):
    g = CARD[wide]
    CW, CH = g['W'], g['H']
    ab = E('Artboard', isComponent=True, width=float(CW), height=float(CH), name='Share card wide' if wide else 'Share card',
           x=float(x_stage), y=1400.0 + (600.0 if wide else 0.0))
    st = E('LayoutComponentStyle', name='Artboard Style')
    ab.attrs['styleId'] = st.id
    bg = art.scallop_ticket('Ticket', g['ticket'][0], g['ticket'][1], c='butter', edge='tomato', x=CW / 2 - 3, y=CH / 2 - 3)
    wm = text('Wordmark', [(style('display', 30, 800, 'tomato', ls=-0.8, opsz=48, name='Card wordmark'), 'Simmer', None, None)], x=g['wm'][0], y=g['wm'][1])
    big_type = g.get('big_type', False)
    T = TILE[wide]
    yr = text('Year', [(style('body', 18 if big_type else 16, 700, 'aub', name='Card year'), '2026', 'year', CONV_INT)], x=g['yr'][0], y=g['yr'][1])
    pot = node('Card pot', [mini_pot(0.82)], x=g['pot'][0], y=g['pot'][1])
    chip_col = E('SolidColor', [bind(P('personaColor'), 37)], colorValue=col('butter'), name='Color')
    chip = node('Persona chip', [shape('Persona dot', ellipse(14, 14), [E('Fill', [chip_col], name='Persona color')]), shape('chip ring', ellipse(26, 26), [fill('aub')])], x=g['chip'][0], y=g['chip'][1])
    pname = text('Persona', [(style('display', 24 if big_type else 22, 700, 'aub', opsz=24, name='Card persona'), 'Flavor Explorer', 'personaName', None)], x=g['pname'][0], y=g['pname'][1],
                 width=250, height=30 if big_type else 28, sizing='fixed', overflow='ellipsis', wrap='noWrap')
    persona = node('Persona row', [chip, pname])
    bx, by, bw = g['big']
    big_v = text('Meals value', [(style('display', 66, 800, 'tomato', ls=-2, opsz=96, name='Card big'), '0', 'mealsCooked', CONV_FORMAT)], x=bx, y=by,
                 width=bw, height=70, sizing='fixed', overflow='fitFontSize', wrap='noWrap')
    big_u = text('Meals unit', [(style('body', 19 if big_type else 17, 600, 'aub', name='Card unit'), 'meals cooked', 'screen2Unit', None)], x=g['unit'][0], y=g['unit'][1],
                 width=bw, height=26 if big_type else 24, sizing='fixed', overflow='ellipsis', wrap='noWrap')
    tiles = []
    props = [('recipesTried', 'screen3Unit'), ('cuisinesExplored', 'screen4Unit'), ('newIngredients', 'screen5Unit'), ('repeatRecipeCount', 'screen6Unit')]
    for i, ((prop, unit), (x, y)) in enumerate(zip(props, g['tiles'])):
        v = text('value', [(style('display', T['val'], 800, 'tomato', ls=-0.8, opsz=36, name='Tile value'), '0', prop, CONV_FORMAT)], x=12, y=8,
                 width=T['w'] - 24, height=T['vh'], sizing='fixed', overflow='fitFontSize', wrap='noWrap')
        # 15 pt (was 13) / 18 pt on the wide card: the card is the smallest text once the layout scales it down
        u = text('unit', [(style('body', T['unit'], 600, 'aub', lh=T['lh'], name='Tile unit'), 'unit', unit, None)], x=12, y=T['uy'], width=T['uw'], height=T['uh'],
                 sizing='fixed', overflow='ellipsis')
        tile = node(f'Tile {i}', [v, u, shape('tile', rect(T['w'], T['h'], 12, 0, 0), [fill('cream'), stroke('aub', 2)]),
                                  shape('tile ink', rect(T['w'], T['h'], 12, 0, 0), fill('ink25'), x=3, y=4)], x=x, y=y)
        tiles.append(tile)
    nx, ny, nw = g['name']
    name_line = text('Name line', [(style('hand', 26, 700, 'tomato', name='Card name'), '', 'summaryNameLine', None)], x=nx, y=ny,
                     width=nw, height=32, sizing='fixed', overflow='ellipsis', wrap='noWrap', rot=-0.03)
    rx, ry, rw = g['recipe']
    recipe_line = text('Recipe line', [(style('hand', 19, 600, 'aub', name='Card recipe'), '', 'summaryRecipeLine', None)], x=rx, y=ry,
                       width=rw, height=24, sizing='fixed', overflow='ellipsis', wrap='noWrap')
    stamp = node('Stamp', [text('stamp text', [(style('display', 14, 800, 'basil', opsz=14, name='Stamp'), 'COOKED\nWITH\nLOVE', None, None)],
                                 x=-34, y=-26, width=68, sizing='autoHeight', align='center'),
                            shape('stamp ring', ellipse(84, 84), stroke('basil', 3))], x=g['stamp'][0], y=g['stamp'][1], rot=-0.25, sx=0.8, sy=0.8)
    card = node('Card', [wm, yr, pot, persona, big_v, big_u, *tiles, name_line, recipe_line, stamp, bg])
    ab.add(st, card)

    # assemble: each piece stamps onto the ticket in turn (runs when the summary is current)
    asm = Anim('Card assemble', ms2f(1800))
    still = Anim('Card settled', 1)
    off = Anim('Card waiting', 1)
    pieces = [wm, yr, persona, big_v, big_u] + tiles + [name_line, recipe_line]
    for i, p in enumerate(pieces):
        t = 380 + i * 90
        asm.ms(p, 'opacity', [(0, 0.0, 'hold'), (t, 0.0, 'lin'), (t + 140, 1.0)])
        asm.ms(p, 'scaleX', [(0, 1.25, 'hold'), (t, 1.25, 'back'), (t + 360, 1.0)])
        asm.ms(p, 'scaleY', [(0, 1.25, 'hold'), (t, 1.25, 'back'), (t + 360, 1.0)])
        for a, v in ((still, 1.0), (off, 0.0)):
            a.ms(p, 'opacity', [(0, v, 'hold')])
        still.ms(p, 'scaleX', [(0, 1.0, 'hold')]); still.ms(p, 'scaleY', [(0, 1.0, 'hold')])
    asm.ms(pot, 'scaleX', [(0, 0.0, 'hold'), (700, 0.0, 'back'), (1000, 1.0)])
    asm.ms(pot, 'scaleY', [(0, 0.0, 'hold'), (700, 0.0, 'back'), (1000, 1.0)])
    asm.ms(stamp, 'scaleX', [(0, 3.0, 'hold'), (1500, 3.0, 'in'), (1700, 1.0)])
    asm.ms(stamp, 'scaleY', [(0, 3.0, 'hold'), (1500, 3.0, 'in'), (1700, 1.0)])
    asm.ms(stamp, 'opacity', [(0, 0.0, 'hold'), (1500, 0.0, 'lin'), (1600, 1.0)])
    for o in (pot, stamp):
        still.ms(o, 'scaleX', [(0, 1.0, 'hold')]); still.ms(o, 'scaleY', [(0, 1.0, 'hold')])
        off.ms(o, 'scaleX', [(0, 0.0, 'hold')])
    still.ms(stamp, 'opacity', [(0, 1.0, 'hold')])
    cs, rm = P('currentScreen'), P('reducedMotion')
    s_off = astate(off, 0, 0)
    s_asm = astate(asm, 260, -100)
    s_still = astate(still, 260, 100)
    s_off.add(trans(s_still, [cond_num(cs, 10), cond_bool(rm, True)]), trans(s_asm, [cond_num(cs, 10)]))
    s_asm.add(trans(s_still, [], exit_pct=100))
    for s in (s_asm, s_still):
        s.add(trans(s_off, [cond_num(cs, 10, 'notEqual')], duration=0) if False else trans(s_off, [cond_num(cs, 10, 'notEqual'), cond_bool(P('isSharing'), False)], duration=500))
    sm = E('StateMachine', [layer('Assemble', s_off, [s_off, s_asm, s_still])], name='Share card machine')
    ab.attrs['defaultStateMachineId'] = sm.id
    ab.add(sm, off.build(), asm.build(), still.build())
    return ab, sm


def scene10(x_stage):
    sc = Scene(10, NAMES[10], x_stage)
    card_ab, card_sm = build_share_card(500 + 10 * 440)
    EXTRA.append((card_ab, card_sm))
    wide_ab, wide_sm = build_share_card(500 + 10 * 440, wide=True)
    EXTRA.append((wide_ab, wide_sm))
    hd = style('display', 32, 800, 'aub', lh=34, ls=-0.8, opsz=48, name='Summary headline')
    sp = style('body', 18, 400, 'aub', lh=24, name='Summary support')
    tb = sc.text_block(24, 98, 342, [(hd, 'A little year. A lot of you.', 'summaryHeadline'), (sp, 'Take a piece of your year with you.', 'summarySupport')])
    sc.reveal_text(tb, 250, 1000, y=24)
    stage.bind_copy_width(tb)
    cards = []
    for wide, (ab_, sm_) in ((False, (card_ab, card_sm)), (True, (wide_ab, wide_sm))):
        g = CARD[wide]
        cx_, cy_ = CARD_CENTRE[wide]
        nest = E('NestedArtboard', [E('NestedStateMachine', animationId=sm_.id, name='machine')], artboardId=ab_.id,
                 x=-g['W'] / 2, y=-g['H'] / 2, name='Share card wide' if wide else 'Share card')
        card = node('Wide card holder' if wide else 'Card holder', [nest], x=cx_, y=cy_)
        sc.key(card, 'y', [(0, cy_ + 434.0 + (80.0 if wide else 0.0), 'hold'), (120, cy_ + 434.0 + (80.0 if wide else 0.0), 'back'), (720, float(cy_))])
        sc.key(card, 'rotation', [(0, 0.22, 'hold'), (120, 0.22, 'back'), (820, -0.02 if not wide else -0.012)])
        cards.append(card)
    # the tall card is the master; the wide arrangement takes over where it would print >= 12% larger
    tall_art = sc.art_group([cards[0]], key=10, name='Tall card art')
    wide_art = sc.art_group([cards[1]], key='10wide', name='Wide card art')
    wide_on = stage.wide_card_wins()
    stage.bind_expr(tall_art, 18, 'Layout tall card shown', 1.0 - wide_on)
    stage.bind_expr(wide_art, 18, 'Layout wide card shown', wide_on)
    normal = node('Normal summary', [sc.copy_group([tb], key=10), tall_art, wide_art])

    # empty / new-user summary: welcoming, no stats, no persona
    eh = style('display', 40, 800, 'aub', lh=42, ls=-1.0, opsz=72, name='Empty headline')
    es = style('body', 20, 400, 'aub', lh=26, name='Empty support')
    etb = sc.text_block(24, 120, 342, [(eh, 'Every story starts somewhere.', 'emptyHeadline'), (es, 'Your next chapter is waiting.', 'emptySupport')])
    sc.reveal_text(etb, 300, 1100, y=24)
    stage.bind_copy_width(etb)
    epot = node('Empty motif', [mini_pot(1.6)], x=195, y=470)
    sc.key(epot, 'y', [(0, 560.0, 'hold'), (200, 560.0, 'back'), (800, 470.0)])
    sc.wiggle(epot, 'rotation', 0.0, 0.05, IDLE_MS / 2)
    seeds = [art.leaf('sprout', 0.9, x=195, y=380, rot=0.3)]
    pop_in(sc, seeds[0], 900, dur=420)
    empty = node('Empty summary', [sc.copy_group([etb], key='10empty'), sc.art_group([epot] + seeds, key='10empty')], op=0.0)

    a_norm = Anim('Summary normal', 1)
    a_empty = Anim('Summary empty', 1)
    a_norm.ms(normal, 'opacity', [(0, 1.0, 'hold')]); a_norm.ms(empty, 'opacity', [(0, 0.0, 'hold')])
    a_empty.ms(normal, 'opacity', [(0, 0.0, 'hold')]); a_empty.ms(empty, 'opacity', [(0, 1.0, 'hold')])
    s_n = astate(a_norm, 0, 0)
    s_e = astate(a_empty, 260, 0)
    s_n.add(trans(s_e, [cond_bool(P('isEmptyRecap'), True)]))
    s_e.add(trans(s_n, [cond_bool(P('isEmptyRecap'), False)]))
    sc.extra_layers.append(layer('Mode', s_n, [s_n, s_e]))
    sc.extra_anims += [a_norm, a_empty]
    sc.inner.add(normal, empty)
    return sc
