"""Responsive layout: per-scene boxes and the bindings that place each scene's copy and art.

The director (scripts/director.luau + scripts/stage.luau) reads the artboard's real
size, picks the orientation (landscape when width >= layoutBreakpoint) and writes a
handful of orientation-resolved slot values into UserRecap (layoutTop, layoutCopyScale,
layoutArtX0a, ...). Every scene splits into a *copy* group and an *art* group, authored
in the 390 x 844 master's coordinates; the formulas below place each group from those
slot values and the group's own box. At 390 x 844 every formula is the identity, so the
master composition is unchanged.

The same box table is written to scripts/stageBoxes.luau so the scripts that need a
scene's frame (the pot motif carry, the steam origin, the steam lettering resolution)
compute exactly what the bindings compute.
"""
import os
from rml import E, bind
from data import P, formula, T_in, T_v, T_p, T_op, T_fn, T_sep, T_open, T_close, ROOT

BASE_W, BASE_H = 390.0, 844.0
ART_BOTTOM = 770.0      # bottom of every art box in the master (just above the controls)
COPY_LEFT, COPY_TOP = 24.0, 92.0

# side 'a': landscape puts the copy column on the LEFT and the art on the right; 'b' mirrors it.
# Left-aligned portrait copy is 'a', right-aligned is 'b', so landscape keeps the master's rhythm.
_B = {
    1: dict(by=284, side='a'),
    2: dict(by=380, side='a'),
    3: dict(by=380, side='b'),
    4: dict(by=380, side='a'),
    5: dict(by=380, side='b'),
    6: dict(by=380, side='a'),
    7: dict(by=380, side='b'),
    8: dict(by=380, side='a'),
    9: dict(by=290, side='b'),
    10: dict(by=200, side='a', copy_top=1),   # copy stays on top in short portraits (the card reflows under it)
    # scene 10 variants: the wide share card (chosen when it would print larger) and the
    # welcoming empty summary (its own, taller copy)
    # tight around the ticket; `reflow`: on short portraits (side mode) it drops under the copy and
    # takes the full width instead of sharing it with the copy column
    '10wide': dict(by=317, bx=-147, bw=680, bh=332, side='a', copy_h=72, reflow=1),
    '10empty': dict(by=262, side='a'),
}


def box(key):
    b = dict(_B[key])
    b.setdefault('bx', 0.0)
    b.setdefault('bw', BASE_W)
    b.setdefault('bh', ART_BOTTOM - b['by'])
    b.setdefault('copy_h', b['by'] - COPY_TOP)
    b.setdefault('reflow', 0)
    b.setdefault('copy_top', 0)
    return b


# ------------------------------------------------------------------ expression DSL -> formula tokens
class X:
    def __init__(self, kind, *a):
        self.kind, self.a = kind, a

    @staticmethod
    def of(v):
        return v if isinstance(v, X) else X('c', float(v))

    def const(self):
        return self.a[0] if self.kind == 'c' else None

    def _bin(self, op, other, rev=False):
        a, b = (X.of(other), self) if rev else (self, X.of(other))
        ca, cb = a.const(), b.const()
        if ca is not None and cb is not None:
            return X('c', {'+': ca + cb, '-': ca - cb, '*': ca * cb, '/': ca / cb}[op])
        if op == '+' and cb == 0: return a
        if op == '+' and ca == 0: return b
        if op == '-' and cb == 0: return a
        if op == '*' and (ca == 0 or cb == 0): return X('c', 0.0)
        if op == '*' and cb == 1: return a
        if op == '*' and ca == 1: return b
        if op == '/' and cb == 1: return a
        return X('op', op, a, b)

    __add__ = lambda s, o: s._bin('+', o)
    __radd__ = lambda s, o: s._bin('+', o, True)
    __sub__ = lambda s, o: s._bin('-', o)
    __rsub__ = lambda s, o: s._bin('-', o, True)
    __mul__ = lambda s, o: s._bin('*', o)
    __rmul__ = lambda s, o: s._bin('*', o, True)
    __truediv__ = lambda s, o: s._bin('/', o)
    __rtruediv__ = lambda s, o: s._bin('/', o, True)

    def tokens(self):
        k = self.kind
        if k == 'c':
            return [T_v(self.a[0])]
        if k == 'p':
            return [T_p(self.a[0])]
        if k == 'in':
            return [T_in()]
        if k == 'op':
            op, a, b = self.a
            return [T_open()] + a.tokens() + [T_op(op)] + b.tokens() + [T_close()]
        if k == 'fn':
            name, args = self.a
            out = [T_fn(name)]
            for i, x in enumerate(args):
                if i:
                    out.append(T_sep())
                out += x.tokens()
            return out + [T_close()]
        raise ValueError(k)


def p(name):
    return X('p', name)


INPUT = X('in')     # the bind's own source value


def fn(name, *args):
    return X('fn', name, [X.of(a) for a in args])


def vmin(a, b):
    return fn('min', a, b)


def vmax(a, b):
    return fn('max', a, b)


def clamp(x, lo, hi):
    return vmin(hi, vmax(lo, x))


def step(x):
    """1 when x > 0, else 0 (hard switch, used to pick a variant)."""
    return clamp(x * 10000.0, 0.0, 1.0)


_cache = {}


def conv(name, expr):
    """A formula converter for `expr` (cached by name). The bind's own input is not used:
    every operand is read from UserRecap through the tokens, which re-evaluate on change."""
    if name not in _cache:
        _cache[name] = formula(name, expr.tokens())
    return _cache[name]


def bind_expr(target, key, name, expr, source='stageWidth'):
    c = expr.const()
    if c is not None:
        target.attrs[{13: 'x', 14: 'y', 16: 'scaleX', 17: 'scaleY', 18: 'opacity', 20: 'width', 21: 'height', 285: 'width'}[key]] = float(c)
        return target
    target.add(bind(P(source), key, conv(name, expr)))
    return target


# ------------------------------------------------------------------ the shared slot values
W, H = p('stageWidth'), p('stageHeight')
OFF_X = W * 0.5 - BASE_W / 2      # the scene's Stage node: Content pivots on the real stage centre
OFF_Y = H * 0.5 - BASE_H / 2
CS = p('layoutCopyScale')
CW = p('layoutCopyWidth')


def art_frame(key):
    """(tx, ty, s): stage position of the box's authored origin and the uniform scale."""
    b = box(key)
    side = b['side']
    x0, x1 = p('layoutArtX0' + side), p('layoutArtX1' + side)
    stack = p('layoutStack')
    if b['reflow']:
        sm = p('layoutSide')
        x0 = x0 * (1.0 - sm)
        x1 = x1 * (1.0 - sm) + W * sm
        stack = stack + sm
    top = p('layoutTop') + stack * CS * b['copy_h']
    bot = p('layoutBottom')
    s = vmin((x1 - x0) / b['bw'], (bot - top) / b['bh'])
    tx = (x0 + x1) * 0.5 - s * (b['bx'] + b['bw'] / 2)
    ty = top + ((bot - top) - s * b['bh']) * 0.5 - s * b['by']
    return tx, ty, s


def copy_frame(key):
    b = box(key)
    x = p('layoutCopyX' + b['side'])
    avail = p('layoutCopyAvail')
    if b['copy_top']:
        avail = avail * (1.0 - p('layoutSide'))
    y = p('layoutTop') + vmax(0.0, (avail - CS * b['copy_h']) * 0.5)
    return x - CS * COPY_LEFT, y - CS * COPY_TOP


def place_art(group, key, in_scene=True):
    tx, ty, s = art_frame(key)
    if in_scene:
        tx, ty = tx - OFF_X, ty - OFF_Y
    tag = f'Layout {key} art'
    bind_expr(group, 13, f'{tag} x{"" if in_scene else " (root)"}', tx)
    bind_expr(group, 14, f'{tag} y{"" if in_scene else " (root)"}', ty)
    bind_expr(group, 16, f'{tag} scale', s)
    bind_expr(group, 17, f'{tag} scale', s)
    return group


def place_copy(group, key):
    gx, gy = copy_frame(key)
    tag = f'Layout {key} copy'
    bind_expr(group, 13, f'{tag} x', gx - OFF_X)
    bind_expr(group, 14, f'{tag} y', gy - OFF_Y)
    group.add(bind(P('layoutCopyScale'), 16), bind(P('layoutCopyScale'), 17))
    return group


def place_stage(node_):
    bind_expr(node_, 13, 'Layout stage offset x', OFF_X)
    bind_expr(node_, 14, 'Layout stage offset y', OFF_Y)
    return node_


def bind_copy_width(text_el, minus=0.0):
    if minus:
        bind_expr(text_el, 285, f'Layout copy width - {minus:g}', CW - minus)
    else:
        text_el.add(bind(P('layoutCopyWidth'), 285))
    return text_el


def wide_card_wins():
    """1 when the wide share card prints its tile labels larger (18 pt type vs 15 pt)."""
    _, _, s_tall = art_frame(10)
    _, _, s_wide = art_frame('10wide')
    return step(s_wide * 18.0 - s_tall * 15.0 * 1.05)


# ------------------------------------------------------------------ Luau mirror of the box table
def write_luau(scripts_dir=None):
    out = os.path.join(scripts_dir or os.path.join(ROOT, 'scripts'), 'stageBoxes.luau')
    lines = ['--!strict', '-- GENERATED by tools/stage.py -- the per-scene layout boxes the bindings use.',
             '-- Read by scripts/stage.luau; edit tools/stage.py and rebuild, not this file.', '',
             'export type Box = { bx: number, by: number, bw: number, bh: number, copyH: number, side: string, reflow: number }', '',
             'local boxes: { [string]: Box } = {']
    for key in _B:
        b = box(key)
        lines.append(f"    ['{key}'] = {{ bx = {b['bx']:g}, by = {b['by']:g}, bw = {b['bw']:g}, bh = {b['bh']:g}, "
                     f"copyH = {b['copy_h']:g}, side = '{b['side']}', reflow = {b['reflow']} }},")
    lines += ['}', '', 'return boxes', '']
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        f.write('\n'.join(lines))
