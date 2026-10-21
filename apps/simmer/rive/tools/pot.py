"""The persistent hero motif: a joyous flat-illustrated pot (component artboard)."""
import math
from rml import E, node, shape, fill, stroke, ellipse, rect, star, smooth, straight, Anim, layer, astate, trans, cond_num, cond_bool, cond_trig, ms2f
from data import P
import art

PW, PH = 280, 260
CX, CY = 140, 160      # pot centre inside its artboard


def pot_body_path():
    return smooth([(-104, -26), (104, -26), (98, 40), (80, 84), (40, 100), (-40, 100), (-80, 84), (-98, 40)], True, corners=(0, 1))


def lid_path():
    return smooth([(-100, 0), (-86, -26), (-46, -44), (0, -50), (46, -44), (86, -26), (100, 0)], True, corners=(0, 6))


def build_pot(x_stage):
    ab = E('Artboard', isComponent=True, width=float(PW), height=float(PH), name='Pot motif', x=float(x_stage), y=1000.0)
    st = E('LayoutComponentStyle', name='Artboard Style')
    ab.attrs['styleId'] = st.id

    # ---- flourish bits (pop out on tap)
    bits = []
    specs = [(art.tomato, 0.35, -0.3), (art.leaf, 0.55, 0.4), (art.carrot, 0.3, 0.9), (art.chili, 0.4, -0.8), (art.leaf, 0.45, -1.2), (art.mushroom, 0.4, 0.2)]
    for i, (fn, s, r) in enumerate(specs):
        b = fn(f'flourish {i}', s=s, rot=r)
        b.attrs['scaleX'] = 0.0
        b.attrs['scaleY'] = 0.0
        bits.append(b)
    flourish = node('Flourish', bits, x=0, y=-40)

    # ---- steam wisps
    wisps = []
    wisp_trims = []
    for i, dx in enumerate((-40, 6, 48)):
        g, trims, _ = art.steam_curl(f'wisp {i}', [(0, 0), (-10, -22), (6, -44), (-6, -66)], w=9, x=dx, y=-74)
        wisps.append(g)
        wisp_trims.append(trims)
    steam = node('Steam', wisps)

    # ---- lid (pivot at rim)
    lid = node('Lid', [
        shape('knob', ellipse(30, 18), [fill('aub')], y=-56),
        shape('knob stem', rect(12, 12, 3), fill('aub'), y=-48),
        shape('lid shine', smooth([(-70, -18), (-40, -34), (-10, -40), (-14, -32), (-44, -26), (-66, -12)], True), fill('tomatoLt')),
        shape('lid', lid_path(), fill('tomato')),
        shape('lid ink', lid_path(), fill('ink25'), x=4, y=4),
        shape('lid rim', rect(206, 10, 5), fill('tomatoDk'), y=-2),
    ], x=0, y=-28)

    # ---- stew (seen when the lid lifts)
    stew = node('Stew', [
        art.tomato_half('stew tomato', 0.4, x=-40, y=-30, rot=0.2),
        art.leaf('stew basil', 0.5, x=10, y=-34, rot=1.2),
        art.pea('stew pea', 1.2, x=40, y=-30),
        art.pea('stew pea2', 1.0, x=-10, y=-26, c='lemon'),
        shape('broth', ellipse(196, 30), fill('butterDk'), y=-26),
    ])

    face = node('Face', [
        shape('eye L', smooth([(-12, 0), (0, -8), (12, 0)], False), stroke('aub', 4.5), x=-30, y=24),
        shape('eye R', smooth([(-12, 0), (0, -8), (12, 0)], False), stroke('aub', 4.5), x=30, y=24),
        shape('smile', smooth([(-16, 0), (0, 12), (16, 0)], False), stroke('aub', 4.5), y=44),
        shape('cheek L', ellipse(16, 9), fill('tomatoLt'), x=-50, y=40),
        shape('cheek R', ellipse(16, 9), fill('tomatoLt'), x=50, y=40),
    ])

    body = node('Body', [
        face,
        shape('band', smooth([(-100, -8), (100, -8), (99, 4), (-99, 4)], True, corners=(0, 1, 2, 3)), fill('tomatoDk')),
        shape('shine', smooth([(-84, 0), (-70, -14), (-60, 40), (-48, 76), (-62, 70), (-80, 36)], True), fill('tomatoLt')),
        shape('pot', pot_body_path(), fill('tomato')),
        shape('pot ink', pot_body_path(), fill('ink25'), x=5, y=5),
        shape('handle L', rect(34, 20, 10), [fill('aub')], x=-108, y=6),
        shape('handle R', rect(34, 20, 10), [fill('aub')], x=108, y=6),
        shape('rim', rect(214, 16, 8), fill('tomatoDk'), y=-28),
    ])

    shadow = shape('Shadow', ellipse(220, 26), fill('ink15'), y=104)
    pot = node('Pot', [flourish, steam, lid, stew, body, shadow], x=CX, y=CY)
    ab.add(st, pot)

    # ---------------- animations
    idle = Anim('Pot simmer', ms2f(2400), loop='loop')
    for i, trims in enumerate(wisp_trims):
        ph = i * 800
        for tr in trims:
            # a wisp draws on, then lifts away; staggered so a puff is always rising
            idle.ms(tr, 'end', [(0, 0.0, 'hold'), (ph, 0.0, 'soft'), (ph + 900, 1.0, 'hold'), (2400, 1.0, 'hold')])
            idle.ms(tr, 'start', [(0, 0.0, 'hold'), (ph + 600, 0.0, 'soft'), (ph + 1500, 1.0, 'hold'), (2400, 1.0, 'hold')])
    idle.ms(body, 'scaleY', [(0, 1.0, 'inout'), (1200, 1.018, 'inout'), (2400, 1.0)])
    idle.ms(body, 'scaleX', [(0, 1.0, 'inout'), (1200, 0.992, 'inout'), (2400, 1.0)])
    idle.ms(lid, 'rotation', [(0, 0.0, 'hold'), (1700, 0.0, 'inout'), (1800, 0.025, 'inout'), (1900, -0.02, 'inout'), (2000, 0.0, 'hold'), (2400, 0.0)])

    rest = Anim('Lid rest', 1)
    rest.ms(lid, 'y', [(0, -28.0, 'hold')])
    rest.ms(lid, 'x', [(0, 0.0, 'hold')])
    rest.ms(lid, 'rotation', [(0, 0.0, 'hold')])
    rest.ms(stew, 'opacity', [(0, 0.0, 'hold')])

    def pop_anim(name, height, total):
        a = Anim(name, ms2f(total))
        # anticipation: the pot squats and the lid rattles, then POP, then the lid hangs ajar
        a.ms(body, 'scaleY', [(0, 1.0, 'backin'), (180, 0.9, 'back'), (420, 1.06, 'out'), (700, 1.0)])
        a.ms(body, 'scaleX', [(0, 1.0, 'backin'), (180, 1.07, 'back'), (420, 0.97, 'out'), (700, 1.0)])
        a.ms(lid, 'rotation', [(0, 0.0, 'lin'), (60, 0.06, 'lin'), (120, -0.06, 'lin'), (180, 0.05, 'out'), (420, -0.55, 'back'), (total, -0.42)])
        a.ms(lid, 'y', [(0, -28.0, 'lin'), (180, -24.0, 'out'), (420, -28 - height, 'soft'), (total, -28 - height * 0.62)])
        a.ms(lid, 'x', [(0, 0.0, 'hold'), (180, 0.0, 'out'), (420, -46.0, 'soft'), (total, -62.0)])
        a.ms(stew, 'opacity', [(0, 0.0, 'hold'), (200, 0.0, 'lin'), (320, 1.0)])
        return a

    pop1 = pop_anim('Lid pop (invitation)', 92, 1200)
    open2 = Anim('Lid off (meals)', ms2f(500))
    open2.ms(lid, 'rotation', [(0, 0.0, 'backin'), (420, -0.5)])
    open2.ms(lid, 'y', [(0, -28.0, 'soft'), (420, -28 - 70.0)])
    open2.ms(lid, 'x', [(0, 0.0, 'soft'), (420, -96.0)])
    open2.ms(stew, 'opacity', [(0, 0.0, 'lin'), (200, 1.0)])
    pop9 = pop_anim('Lid pop (persona)', 160, 1100)
    ajar_rm = Anim('Lid ajar (reduced motion)', 1)
    ajar_rm.ms(lid, 'rotation', [(0, -0.42, 'hold')])
    ajar_rm.ms(lid, 'y', [(0, -28 - 74.0, 'hold')])
    ajar_rm.ms(lid, 'x', [(0, -62.0, 'hold')])
    ajar_rm.ms(stew, 'opacity', [(0, 1.0, 'hold')])

    wob = Anim('Tap wobble + flourish', ms2f(1100))
    wob.ms(lid, 'rotation', [(0, 0.0, 'lin'), (90, 0.22, 'inout'), (220, -0.18, 'inout'), (360, 0.12, 'inout'), (500, -0.06, 'inout'), (640, 0.0)])
    wob.ms(body, 'scaleY', [(0, 1.0, 'backin'), (100, 0.92, 'back'), (300, 1.05, 'out'), (520, 1.0)])
    wob.ms(body, 'scaleX', [(0, 1.0, 'backin'), (100, 1.06, 'back'), (300, 0.97, 'out'), (520, 1.0)])
    dests = [(-150, -120), (-80, -170), (10, -190), (90, -160), (150, -110), (40, -140)]
    for i, b in enumerate(bits):
        dx, dy = dests[i]
        t0 = 60 + i * 40
        wob.ms(b, 'scaleX', [(0, 0.0, 'hold'), (t0, 0.0, 'back'), (t0 + 200, 1.0, 'hold'), (t0 + 700, 1.0, 'in'), (t0 + 900, 0.0)])
        wob.ms(b, 'scaleY', [(0, 0.0, 'hold'), (t0, 0.0, 'back'), (t0 + 200, 1.0, 'hold'), (t0 + 700, 1.0, 'in'), (t0 + 900, 0.0)])
        wob.ms(b, 'x', [(0, 0.0, 'hold'), (t0, 0.0, 'out'), (t0 + 520, dx * 0.8, 'soft'), (t0 + 900, dx * 1.1)])
        wob.ms(b, 'y', [(0, 0.0, 'hold'), (t0, 0.0, 'out'), (t0 + 420, dy, 'in'), (t0 + 900, dy + 120)])
        wob.ms(b, 'rotation', [(0, 0.0, 'hold'), (t0, 0.0, 'lin'), (t0 + 900, (1 if i % 2 else -1) * 3.2)])
    wob_rm = Anim('Tap wobble (reduced motion)', ms2f(300))
    wob_rm.ms(lid, 'rotation', [(0, 0.0, 'lin'), (150, 0.08, 'lin'), (300, 0.0)])
    still = Anim('Wobble still', 1)

    cs = P('currentScreen')
    rm = P('reducedMotion')

    s_idle = astate(idle, 0, 0, reset=False)
    l_simmer = layer('Simmer', s_idle, [s_idle])

    s_rest = astate(rest, 0, 0)
    s_p1 = astate(pop1, 260, -120)
    s_p9 = astate(pop9, 260, 120)
    s_aj = astate(ajar_rm, 520, 0)
    s_o2 = astate(open2, 260, 260)
    open_states = {1: s_p1, 2: s_o2, 9: s_p9}
    for src in (s_rest, s_p1, s_o2, s_p9, s_aj):
        if src is not s_aj:
            src.add(trans(s_aj, [cond_num(cs, 1), cond_bool(rm, True)]),
                    trans(s_aj, [cond_num(cs, 2), cond_bool(rm, True)]),
                    trans(s_aj, [cond_num(cs, 9), cond_bool(rm, True)]))
        for k, dst in open_states.items():
            if dst is not src:
                src.add(trans(dst, [cond_num(cs, k)], duration=0 if src is s_rest else 250))
        if src is not s_rest:
            # reduced motion cuts; otherwise the lid settles back on
            src.add(trans(s_rest, [cond_num(cs, 1, 'notEqual'), cond_num(cs, 2, 'notEqual'), cond_num(cs, 9, 'notEqual'), cond_bool(rm, True)]))
            src.add(trans(s_rest, [cond_num(cs, 1, 'notEqual'), cond_num(cs, 2, 'notEqual'), cond_num(cs, 9, 'notEqual')], duration=320, ease='inout'))
    l_lid = layer('Lid', s_rest, [s_rest, s_p1, s_o2, s_p9, s_aj])

    s_still = astate(still, 0, 0)
    s_wob = astate(wob, 260, -100)
    s_wobrm = astate(wob_rm, 260, 100)
    tap = P('potTap')
    s_still.add(trans(s_wobrm, [cond_trig(tap), cond_bool(rm, True)]), trans(s_wob, [cond_trig(tap)]))
    s_wob.add(trans(s_still, [], exit_pct=100))
    s_wobrm.add(trans(s_still, [], exit_pct=100))
    l_wob = layer('Tap wobble', s_still, [s_still, s_wob, s_wobrm])

    # anticipation for the signature handoff: the pot squats, then puffs up as the steam leaves it
    puff = Anim('Handoff puff', ms2f(380))
    puff.ms(body, 'scaleY', [(0, 1.0, 'out'), (90, 0.9, 'back'), (210, 1.08, 'inout'), (380, 1.0)])
    puff.ms(body, 'scaleX', [(0, 1.0, 'out'), (90, 1.08, 'back'), (210, 0.95, 'inout'), (380, 1.0)])
    calm = Anim('No puff', 1)
    s_calm = astate(calm, 0, 0)
    s_puff = astate(puff, 260, 0)
    for src in (s_calm, s_puff):
        src.add(trans(s_puff, [cond_trig(P('handoffForward')), cond_bool(rm, False)]),
                trans(s_puff, [cond_trig(P('handoffBack')), cond_bool(rm, False)]))
    s_puff.add(trans(s_calm, [], exit_pct=100))
    l_puff = layer('Handoff puff', s_calm, [s_calm, s_puff])

    sm = E('StateMachine', [l_simmer, l_lid, l_puff, l_wob], name='Pot machine')
    ab.attrs['defaultStateMachineId'] = sm.id
    ab.add(sm)
    for a in (idle, rest, pop1, open2, pop9, ajar_rm, wob, wob_rm, still, puff, calm):
        ab.add(a.build())
    return ab, sm
