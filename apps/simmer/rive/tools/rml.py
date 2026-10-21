"""Tiny RML builder used to generate the Simmer recap scene files.

Every element gets an explicit id so the CLI never has to write ids back
into the generated .rml files (regeneration stays deterministic).
"""
import math
from xml.sax.saxutils import quoteattr

_ID = [1000]


def nid():
    _ID[0] += 1
    return f"0:{_ID[0]}"


def reset_ids(start=1000):
    _ID[0] = start


NO_ID = set()


class E:
    def __init__(self, _tag, _children=None, **attrs):
        tag = _tag
        self.tag = tag
        self.attrs = {}
        for k, v in attrs.items():
            if v is None:
                continue
            k = k.rstrip('_')
            self.attrs[k] = v
        if 'id' not in self.attrs and tag not in NO_ID:
            self.attrs['id'] = nid()
        self.children = list(_children or [])

    @property
    def id(self):
        return self.attrs['id']

    def add(self, *kids):
        for k in kids:
            if k is None:
                continue
            if isinstance(k, (list, tuple)):
                self.add(*k)
            else:
                self.children.append(k)
        return self

    def xml(self, ind=0):
        pad = '  ' * ind
        parts = []
        for k, v in self.attrs.items():
            if isinstance(v, bool):
                v = 'true' if v else 'false'
            elif isinstance(v, float):
                v = fmt(v)
            parts.append(f'{k}={quoteattr(str(v))}')
        a = (' ' + ' '.join(parts)) if parts else ''
        if not self.children:
            return f'{pad}<{self.tag}{a}/>'
        inner = '\n'.join(c.xml(ind + 1) for c in self.children)
        return f'{pad}<{self.tag}{a}>\n{inner}\n{pad}</{self.tag}>'


def clone(el):
    c = E(el.tag, [clone(k) for k in el.children], **{k: v for k, v in el.attrs.items() if k != 'id'})
    return c


def fmt(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


# --------------------------------------------------------------- palette
C = dict(
    tomato='FFE44932', tomatoDk='FFB8331F', tomatoLt='FFF27C61',
    butter='FFFFEDB0', butterDk='FFF5D77E', cream='FFFDF5E1', paper='FFFBF0D6',
    aub='FF48293D', aubLt='FF6E4560', aubPale='FFB89AAB',
    basil='FF4D7655', basilLt='FF7FA27E', basilDk='FF365A3E',
    lemon='FFF4C542', carrot='FFEE7B30', garlic='FFFFF8EC', mush='FFD9C3A5',
    onion='FFA45C8A', wood='FFC98B5A', woodDk='FF9C6640', white='FFFFFFFF',
    ink15='26482938', ink25='40482938', clear='00FFFFFF', shadow='3348293D',
)


def col(c):
    return C.get(c, c)


# --------------------------------------------------------------- paint
def fill(c, name='Fill', opacity=None, solid_id=None):
    sc = E('SolidColor', colorValue=col(c), name='Color', id=solid_id)
    return E('Fill', [sc], name=name)


def stroke(c, w, cap='round', join='round', name='Stroke', extra=None):
    s = E('Stroke', [E('SolidColor', colorValue=col(c), name='Color')],
          thickness=float(w), cap=cap, join=join, name=name)
    if extra:
        s.add(extra)
    return s


# --------------------------------------------------------------- geometry
def ellipse(w, h, ox=0.5, oy=0.5):
    return E('Ellipse', width=float(w), height=float(h), originX=float(ox), originY=float(oy), name='Path')


def rect(w, h, r=0, ox=0.5, oy=0.5):
    return E('Rectangle', width=float(w), height=float(h), cornerRadiusTL=float(r),
             originX=float(ox), originY=float(oy), name='Path')


def star(w, h, points, inner, r=0):
    return E('Star', width=float(w), height=float(h), points=points, innerRadius=float(inner),
             cornerRadius=float(r), name='Path')


def poly(w, h, points, r=0):
    return E('Polygon', width=float(w), height=float(h), points=points, cornerRadius=float(r), name='Path')


def _clockwise(pts):
    a = 0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a > 0  # y down => positive area is clockwise


def smooth(pts, closed=True, tension=1.0, name='Path', corners=()):
    """Catmull-Rom style smooth path through points (CubicDetachedVertex)."""
    n = len(pts)
    verts = []
    for i, (x, y) in enumerate(pts):
        if i in corners or (not closed and (i == 0 or i == n - 1)):
            if not closed and (i == 0 or i == n - 1) and i not in corners:
                # open ends: one-sided handle
                j = 1 if i == 0 else n - 2
                px, py = pts[j]
                ang = math.atan2(py - y, px - x)
                d = math.hypot(px - x, py - y) / 3 * tension
                verts.append(E('CubicDetachedVertex', x=float(x), y=float(y), inRotation=float(ang), inDistance=float(d),
                               outRotation=float(ang), outDistance=float(d), name='V'))
            else:
                verts.append(E('StraightVertex', x=float(x), y=float(y), name='V'))
            continue
        p0 = pts[(i - 1) % n]
        p2 = pts[(i + 1) % n]
        tx, ty = (p2[0] - p0[0]) / 2, (p2[1] - p0[1]) / 2
        ang = math.atan2(ty, tx)
        din = math.hypot(x - p0[0], y - p0[1]) / 3 * tension
        dout = math.hypot(p2[0] - x, p2[1] - y) / 3 * tension
        verts.append(E('CubicDetachedVertex', x=float(x), y=float(y), inRotation=float(ang + math.pi), inDistance=float(din),
                       outRotation=float(ang), outDistance=float(dout), name='V'))
    cw = _clockwise(pts) if closed else True
    return E('PointsPath', verts, isClosed=closed, isClockwise=cw, name=name)


def straight(pts, closed=True, radius=0, name='Path'):
    verts = [E('StraightVertex', x=float(x), y=float(y), radius=float(radius), name='V') for x, y in pts]
    return E('PointsPath', verts, isClosed=closed, isClockwise=_clockwise(pts) if closed else True, name=name)


def shape(name, geoms, paints, x=0, y=0, rot=0, sx=1, sy=1, op=1, id=None, **kw):
    s = E('Shape', name=name, x=float(x), y=float(y), id=id, **kw)
    if rot:
        s.attrs['rotation'] = float(rot)
    if sx != 1:
        s.attrs['scaleX'] = float(sx)
    if sy != 1:
        s.attrs['scaleY'] = float(sy)
    if op != 1:
        s.attrs['opacity'] = float(op)
    if not isinstance(geoms, (list, tuple)):
        geoms = [geoms]
    if not isinstance(paints, (list, tuple)):
        paints = [paints]
    s.add(*geoms)
    s.add(*paints)
    return s


def node(name, kids=(), x=0, y=0, rot=0, sx=1, sy=1, op=1, id=None, **kw):
    n = E('Node', name=name, x=float(x), y=float(y), id=id, **kw)
    if rot:
        n.attrs['rotation'] = float(rot)
    if sx != 1:
        n.attrs['scaleX'] = float(sx)
    if sy != 1:
        n.attrs['scaleY'] = float(sy)
    if op != 1:
        n.attrs['opacity'] = float(op)
    n.add(*kids)
    return n


def riso(name, geom_fn, c, x=0, y=0, off=(3, 3), ink='ink25', rot=0, sx=1, sy=1, extra_paints=()):
    """A flat cutout with an offset ink layer underneath (risograph misregistration)."""
    top = shape(name, geom_fn(), [fill(c)] + list(extra_paints))
    under = shape(name + ' ink', geom_fn(), fill(ink), x=off[0], y=off[1])
    return node(name + ' grp', [top, under], x=x, y=y, rot=rot, sx=sx, sy=sy)


# --------------------------------------------------------------- binding
def bind(path, key, conv=None, **kw):
    return E('DataBindContext', sourcePathIds=path, propertyKey=str(key), converterId=conv, **kw)


# --------------------------------------------------------------- animation
EASES = {
    'out': (0.16, 1, 0.3, 1),
    'in': (0.6, 0, 0.9, 0.4),
    'inout': (0.65, 0, 0.35, 1),
    'back': (0.34, 1.56, 0.64, 1),      # overshoot settle
    'backin': (0.36, 0, 0.66, -0.56),   # anticipation
    'soft': (0.33, 0, 0.2, 1),
    'snap': (0.7, 0, 0.2, 1.0),
    'drop': (0.5, 0, 0.75, 0.2),        # gravity
}


def kf(frame, value, ease='lin', kind='Double'):
    attrs = dict(frame=int(round(frame)), value=value if kind != 'Double' else float(value))
    if kind != 'Double':
        ease = 'hold' if kind in ('Bool', 'Id', 'String') else ease
    if ease == 'hold':
        e = E('KeyFrame' + kind, interpolationType='hold', **attrs)
    elif ease == 'lin':
        e = E('KeyFrame' + kind, interpolationType='linear', **attrs)
    else:
        x1, y1, x2, y2 = EASES[ease]
        e = E('KeyFrame' + kind, [E('CubicEaseInterpolator', x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2))],
              interpolationType='cubic', **attrs)
    return e


class Anim:
    """Collects keyframes per object/property and emits a LinearAnimation."""

    def __init__(self, name, frames, loop='oneShot', fps=60):
        self.name = name
        self.frames = int(frames)
        self.loop = loop
        self.fps = fps
        self.keys = {}  # (objid) -> {prop: [(f, v, ease, kind)]}
        self.el = E('LinearAnimation', name=name, duration=self.frames, loopValue=loop, fps=fps)

    @property
    def id(self):
        return self.el.id

    def k(self, obj, prop, seq, kind='Double'):
        """seq: list of (frame, value[, ease]); ms if frame given as string 'Nms'."""
        oid = obj if isinstance(obj, str) else obj.id
        lst = self.keys.setdefault(oid, {}).setdefault(prop, [])
        for item in seq:
            f, v = item[0], item[1]
            ease = item[2] if len(item) > 2 else 'out'
            if isinstance(f, str) and f.endswith('ms'):
                f = float(f[:-2]) * self.fps / 1000.0
            lst.append((f, v, ease, kind))
        return self

    def ms(self, obj, prop, seq, kind='Double'):
        oid = obj if isinstance(obj, str) else obj.id
        lst = self.keys.setdefault(oid, {}).setdefault(prop, [])
        for item in seq:
            t, v = item[0], item[1]
            ease = item[2] if len(item) > 2 else 'out'
            lst.append((t * self.fps / 1000.0, v, ease, kind))
        return self

    def build(self):
        el = self.el
        el.children = []
        for oid, props in self.keys.items():
            ko = E('KeyedObject', objectId=oid)
            for prop, lst in props.items():
                lst = sorted(lst, key=lambda t: t[0])
                kp = E('KeyedProperty', property=prop) if not str(prop).isdigit() else E('KeyedProperty', propertyKey=str(prop))
                seen = set()
                for f, v, ease, kind in lst:
                    fr = min(int(round(f)), self.frames)
                    if fr in seen:
                        continue
                    seen.add(fr)
                    kp.add(kf(fr, v, ease, kind))
                ko.add(kp)
            el.add(ko)
        return el


def ms2f(ms):
    return int(round(ms * 60 / 1000))


# --------------------------------------------------------------- state machine helpers
def cond_num(path, value, op='equal'):
    return E('TransitionViewModelCondition', [
        E('TransitionPropertyViewModelComparator', [
            E('BindablePropertyNumber', [bind(path, 636)])]),
        E('TransitionValueNumberComparator', value=float(value))], opValue=op)


def cond_bool(path, value=True):
    return E('TransitionViewModelCondition', [
        E('TransitionPropertyViewModelComparator', [
            E('BindablePropertyBoolean', [bind(path, 634)])]),
        E('TransitionValueBooleanComparator', value=bool(value))], opValue='equal')


def cond_trig(path):
    return E('TransitionViewModelCondition', [
        E('TransitionPropertyViewModelComparator', [
            E('BindablePropertyTrigger', [bind(path, 686)])]),
        E('TransitionValueTriggerComparator')], opValue='equal')


def trans(to, conds=(), duration=0, exit_pct=None, ease=None):
    t = E('StateTransition', stateToId=to if isinstance(to, str) else to.id, duration=int(duration))
    if exit_pct is not None:
        t.attrs['enableExitTime'] = True
        t.attrs['exitTimeIsPercetange'] = True
        t.attrs['exitTime'] = float(exit_pct)
    if ease and duration:
        x1, y1, x2, y2 = EASES[ease]
        t.attrs['interpolationType'] = 'cubic'
        t.add(E('CubicEaseInterpolator', x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2)))
    t.add(*conds)
    return t


def astate(anim, x, y, reset=True, speed=None):
    s = E('AnimationState', animationId=anim if isinstance(anim, str) else anim.id, x=float(x), y=float(y))
    if reset:
        s.attrs['reset'] = True
    if speed is not None:
        s.attrs['speed'] = float(speed)
    return s


def layer(name, entry_to, states, any_trans=(), ex=(0, 0)):
    lay = E('StateMachineLayer', name=name)
    anys = E('AnyState', x=-160.0, y=-160.0)
    anys.add(*any_trans)
    lay.add(anys, E('ExitState', x=-160.0, y=320.0),
            E('EntryState', [trans(entry_to)], x=-160.0, y=80.0))
    lay.add(*states)
    return lay
