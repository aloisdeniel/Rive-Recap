"""Scene component scaffolding: artboard, content group, standard state machine.

Every scene is a component artboard placed (non-stateful) in the main
artboard, so it inherits the single UserRecap instance. Its own state machine
watches `currentScreen`, `navDirection` and `reducedMotion`:

    Off --(cs==k, rm)--> EnterRM --> Idle
    Off --(cs==k)------> Enter ----> Idle (restrained loop)
    Enter/Idle --(cs!=k, rm)--> ExitRM --> Off
    Enter/Idle --(cs!=k, dir>0)--> ExitF --> Off   (lift up-left into the steam)
    Enter/Idle --(cs!=k, dir<0)--> ExitB --> Off   (sink down-right, reversed)
    Exit* --(cs==k)--> Enter                        (rapid back-and-forth)
"""
from rml import E, node, shape, fill, rect, Anim, layer, astate, trans, cond_num, cond_bool, ms2f
from data import P
from text import style, text, reveal_modifier, key_reveal, key_shown
import stage

W, H = 390, 844
ENTER_MS = 2100        # the director starts the dwell timer after this
IDLE_MS = 4000


class Scene:
    def __init__(self, k, name, x_stage):
        self.k = k
        self.name = name
        # clip off: the scene draws wherever the layout puts it on the (resizable) root stage
        self.ab = E('Artboard', isComponent=True, width=float(W), height=float(H), name=name, x=float(x_stage), y=0.0, clip=False)
        self.style = E('LayoutComponentStyle', name='Artboard Style')
        self.ab.attrs['styleId'] = self.style.id
        self.content = node('Content', x=W / 2, y=H / 2)
        self.inner = node('Inner', x=-W / 2, y=-H / 2)   # children authored in artboard coordinates
        self.content.add(self.inner)
        # Stage: offsets the scene so Content (keyed around the master's centre) pivots on the real stage centre
        self.stage = stage.place_stage(node('Stage', [self.content]))
        self.enter = Anim(f'{name} enter', ms2f(ENTER_MS))
        self.idle = Anim(f'{name} idle', ms2f(IDLE_MS), loop='loop')
        self.final = {}   # (oid, prop) -> settled value, for the reduced-motion entrance
        self.extra_layers = []
        self.extra_anims = []
        self.exit_extra = []   # callables(anim, sign)

    # -------- responsive groups (see tools/stage.py)
    def copy_group(self, kids, key=None, name='Copy'):
        return stage.place_copy(node(name, kids), key if key is not None else self.k)

    def art_group(self, kids, key=None, name='Art'):
        return stage.place_art(node(name, kids), key if key is not None else self.k)

    # -------- helpers that record settled values
    def key(self, obj, prop, seq, kind='Double'):
        """Enter keys in ms; last value is recorded as the settled value."""
        self.enter.ms(obj, prop, seq, kind)
        oid = obj if isinstance(obj, str) else obj.id
        self.final[(oid, prop, kind)] = seq[-1][1]

    def settle(self, obj, prop, value, kind='Double'):
        oid = obj if isinstance(obj, str) else obj.id
        self.final[(oid, prop, kind)] = value

    def wiggle(self, obj, prop, base, amp, period_ms=IDLE_MS, phase=0.0, ease='inout'):
        """Seamless idle oscillation around the settled value."""
        n = max(1, int(round(IDLE_MS / period_ms)))
        per = IDLE_MS / n
        seq = []
        for i in range(n):
            t0 = i * per
            seq += [(t0, base, ease), (t0 + per * 0.5, base + amp, ease)]
        seq.append((IDLE_MS, base, ease))
        if phase:
            # rotate the sequence by phase (fraction of a period) keeping the seam at base
            seq = [(t, v, e) for (t, v, e) in seq]
        self.idle.ms(obj, prop, seq)

    def reveal_text(self, t, t0, t1, y=24, soft=0.35):
        rng = reveal_modifier(t, y=y, soft=soft)
        key_reveal(self.enter, rng, t0, t1, soft=soft)
        self.settle(rng, 'modifyFrom', 1.0 + soft)
        self.settle(rng, 'falloffFrom', 1.0 + 2 * soft)
        return rng

    def text_block(self, x, y, width, items, align='left', name='Copy', rot=0):
        """items: list of (style, literal, prop) joined with newlines into one rich Text."""
        runs = []
        for i, (st, lit, prop) in enumerate(items):
            if i:
                runs.append((items[i - 1][0], '\n', None, None))
            runs.append((st, lit, prop, None))
        return text(name, runs, x=x, y=y, width=width, sizing='autoHeight', align=align, rot=rot)

    # -------- assembly
    def build(self):
        k = self.k
        cs = P('currentScreen')
        rm = P('reducedMotion')
        dirp = P('navDirection')
        c = self.content

        off = Anim(f'{self.name} off', 1)
        off.ms(c, 'opacity', [(0, 0.0, 'hold')])

        # content reset at the start of every entrance
        self.enter.ms(c, 'opacity', [(0, 1.0, 'hold')])
        for p, v in (('y', H / 2), ('x', W / 2), ('rotation', 0.0), ('scaleX', 1.0), ('scaleY', 1.0)):
            self.enter.ms(c, p, [(0, v, 'hold')])

        enter_rm = Anim(f'{self.name} enter (reduced motion)', ms2f(240))
        enter_rm.ms(c, 'opacity', [(0, 0.0, 'lin'), (220, 1.0)])
        for p, v in (('y', H / 2), ('x', W / 2), ('rotation', 0.0), ('scaleX', 1.0), ('scaleY', 1.0)):
            enter_rm.ms(c, p, [(0, v, 'hold')])
        for (oid, prop, kind), v in self.final.items():
            enter_rm.ms(oid, prop, [(0, v, 'hold')], kind)

        exits = []
        for sign, label in ((1, 'forward'), (-1, 'back')):
            a = Anim(f'{self.name} exit {label}', ms2f(560))
            # forward: lift up-left and tilt into the rising steam; back: sink down-right
            a.ms(c, 'y', [(0, H / 2, 'backin'), (560, H / 2 - 70 * sign)])
            a.ms(c, 'x', [(0, W / 2, 'in'), (560, W / 2 - 28 * sign)])
            a.ms(c, 'rotation', [(0, 0.0, 'in'), (560, -0.06 * sign)])
            a.ms(c, 'scaleX', [(0, 1.0, 'in'), (560, 0.94)])
            a.ms(c, 'scaleY', [(0, 1.0, 'in'), (560, 0.94)])
            a.ms(c, 'opacity', [(0, 1.0, 'hold'), (120, 1.0, 'in'), (520, 0.0)])
            for fn in self.exit_extra:
                fn(a, sign)
            exits.append(a)
        exit_rm = Anim(f'{self.name} exit (reduced motion)', ms2f(160))
        exit_rm.ms(c, 'opacity', [(0, 1.0, 'lin'), (150, 0.0)])

        anims = [off, self.enter, self.idle, enter_rm, exits[0], exits[1], exit_rm]
        s_off, s_en, s_idle, s_enrm, s_exf, s_exb, s_exrm = [
            astate(a, x, y) for a, (x, y) in zip(anims, [(0, 0), (240, -120), (480, 0), (240, 120), (720, -120), (720, 120), (720, 0)])]
        s_idle.attrs.pop('reset', None)

        def is_me():
            return cond_num(cs, k, 'equal')

        def not_me():
            return cond_num(cs, k, 'notEqual')

        s_off.add(trans(s_enrm, [is_me(), cond_bool(rm, True)]),
                  trans(s_en, [is_me()]))
        s_en.add(trans(s_exrm, [not_me(), cond_bool(rm, True)]),
                 trans(s_exf, [not_me(), cond_num(dirp, 0, 'greaterThanOrEqual')], duration=120),
                 trans(s_exb, [not_me(), cond_num(dirp, 0, 'lessThan')], duration=120),
                 trans(s_idle, [], exit_pct=100))
        s_enrm.add(trans(s_exrm, [not_me()]), trans(s_idle, [], exit_pct=100))
        s_idle.add(trans(s_exrm, [not_me(), cond_bool(rm, True)]),
                   trans(s_exf, [not_me(), cond_num(dirp, 0, 'greaterThanOrEqual')], duration=120),
                   trans(s_exb, [not_me(), cond_num(dirp, 0, 'lessThan')], duration=120))
        for s in (s_exf, s_exb, s_exrm):
            s.add(trans(s_enrm, [is_me(), cond_bool(rm, True)]),
                  trans(s_en, [is_me()], duration=100),
                  trans(s_off, [], exit_pct=100))

        life = layer('Life', s_off, [s_off, s_en, s_idle, s_enrm, s_exf, s_exb, s_exrm])
        sm = E('StateMachine', name=f'{self.name} machine')
        sm.add(life, *self.extra_layers)
        self.ab.attrs['defaultStateMachineId'] = sm.id
        self.ab.add(self.style, self.stage, sm)
        self.ab.add(*[a.build() for a in anims])
        self.ab.add(*[a.build() for a in self.extra_anims])
        return self.ab

    def component_asset(self):
        return E('ComponentAsset', artboardId=self.ab.id, name=self.name)


def hero_number(scene, prop, conv, x, y, w=342, align='left', size=118, color='tomato'):
    st = style('display', size, 800, color, lh=size * 0.98, ls=-3, opsz=96, name='Hero')
    t = text('Hero number', [(st, '0', prop, conv)], x=x, y=y, width=w, height=size * 1.05, sizing='fixed',
             align=align, overflow='fitFontSize', wrap='noWrap')
    stage.bind_copy_width(t)
    return t


def copy_styles(color_head='aub', color_body='aub'):
    unit = style('body', 22, 600, color_body, lh=28, name='Unit')
    head = style('display', 33, 700, color_head, lh=36, ls=-0.6, opsz=36, name='Headline')
    sup = style('body', 18, 400, color_body, lh=24, name='Support')
    return unit, head, sup
