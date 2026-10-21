"""The root artboard: chrome, persistent motif, signature handoff, controls, director."""
import math
import random
from rml import (E, node, shape, fill, stroke, ellipse, rect, star, smooth, straight, Anim, layer, astate, trans,
                 cond_num, cond_bool, cond_trig, bind, ms2f, col)
from data import P, VM_ID, SCRIPT_DIRECTOR, SCRIPT_AUDIT, CONV_INT, formula, T_in, T_v, T_p, T_op, T_fn, T_sep, T_close
from text import style, text
import art
import pot as potmod

W, H = 390, 844
CTRL_Y = 792

# motif poses per canonical screen: x, y, scale, rotation
POSES = {
    1: (195, 640, 1.08, 0.0),
    2: (195, 650, 1.16, 0.0),
    3: (322, 706, 0.5, -0.12),
    4: (195, 724, 0.36, 0.0),
    5: (318, 506, 0.4, 0.0),
    6: (104, 452, 0.5, -0.62),
    7: (195, 574, 0.6, 0.0),
    8: (195, 716, 0.48, 0.0),
    9: (195, 610, 0.9, 0.0),
    10: (294, 278, 0.3, 0.0),
}


def build_main(scene_boards, pot_board, pot_sm, x_stage=0):
    ab = E('Artboard', width=float(W), height=float(H), name='Simmer Recap', x=float(x_stage), y=0.0,
           viewModelId=VM_ID, viewModelInstanceId='0:401', clip=True)
    st = E('LayoutComponentStyle', name='Artboard Style')
    ab.attrs['styleId'] = st.id
    anims = []
    listeners = []
    layers = []

    # ================================================================ header
    head_style = style('display', 25, 800, 'aub', ls=-0.5, opsz=36, name='Wordmark')
    wordmark = text('Wordmark', [(head_style, 'Simmer', None, None)], x=24, y=24)
    steam_mark = node('Wordmark steam', [
        shape(f'w{i}', smooth([(0, 0), (-3, -6), (2, -12), (-1, -17)], False), stroke('tomato', 2.4), x=i * 6) for i in range(3)
    ], x=127, y=45)
    year_st = style('body', 15, 700, 'aub', name='Year')
    year = text('Year', [(year_st, '2026', 'year', CONV_INT)], x=286, y=30, width=80, sizing='fixed', height=22, align='right')

    # progress segments: geometry derived from visibleCount, fill from currentSegment + screenProgress
    TW, GAP, X0, PY = 342.0, 5.0, 24.0, 72.0
    seg_w = formula('Segment width', [T_open_(), T_v(TW), T_op('-'), T_v(GAP), T_op('*'), T_open_(), T_in(), T_op('-'), T_v(1), T_close(), T_close(), T_op('/'), T_fn('max'), T_v(1), T_sep(), T_in(), T_close()])
    segs = []
    for i in range(10):
        # x_i = X0 + i * (w + GAP)
        cx = formula(f'Segment {i} x', [T_v(X0), T_op('+'), T_v(i), T_op('*'), T_open_(), T_open_(), T_v(TW), T_op('-'), T_v(GAP), T_op('*'), T_open_(), T_in(), T_op('-'), T_v(1), T_close(), T_close(), T_op('/'), T_fn('max'), T_v(1), T_sep(), T_in(), T_close(), T_op('+'), T_v(GAP), T_close()])
        cop = formula(f'Segment {i} visible', [T_fn('min'), T_v(1), T_sep(), T_fn('max'), T_v(0), T_sep(), T_in(), T_op('-'), T_v(i), T_close(), T_close()])
        cfill = formula(f'Segment {i} fill', [T_open_(), T_open_(), T_v(TW), T_op('-'), T_v(GAP), T_op('*'), T_open_(), T_p('visibleCount'), T_op('-'), T_v(1), T_close(), T_close(), T_op('/'), T_fn('max'), T_v(1), T_sep(), T_p('visibleCount'), T_close(), T_close(), T_op('*'),
                                                   T_fn('min'), T_v(1), T_sep(), T_fn('max'), T_v(0), T_sep(), T_p('currentSegment'), T_op('+'), T_in(), T_op('-'), T_v(i), T_close(), T_close()])
        track_r = E('Rectangle', width=30.0, height=4.0, cornerRadiusTL=2.0, originX=0.0, originY=0.5, name='Path')
        track_r.add(bind(P('visibleCount'), 20, seg_w))
        fill_r = E('Rectangle', width=0.0, height=4.0, cornerRadiusTL=2.0, originX=0.0, originY=0.5, name='Path')
        fill_r.add(bind(P('screenProgress'), 20, cfill))
        sg = node(f'Segment {i}', [
            shape('fill', fill_r, fill('tomato')),
            shape('track', track_r, fill('3348293D')),
        ], x=X0 + i * 34, y=PY)
        sg.add(bind(P('visibleCount'), 13, cx))
        sg.add(bind(P('visibleCount'), 18, cop))
        segs.append(sg)
    progress = node('Progress', segs)
    header = node('Header', [wordmark, steam_mark, year, progress])

    # ================================================================ controls
    def button(name, cx, w, label_prop, req_prop, kind='solid', icon=None, show_label=True, c='aub', tc='cream'):
        h = 52
        kids = []
        if show_label:
            lst = style('body', 18, 700, tc, name='Label')
            kids.append(text('Label', [(lst, 'Label', label_prop, None)], x=-w / 2 + 12 + (0 if not icon else 0), y=-12, width=w - 24 - (22 if icon else 0),
                             height=26, sizing='fixed', align='center', overflow='ellipsis', wrap='noWrap'))
        if icon is not None:
            kids.append(icon)
        sem = E('SemanticData', role='button', label='', name='Semantics')
        sem.add(bind(P(label_prop), 983))
        paints = [fill(c)] if kind == 'solid' else [fill('cream'), stroke('aub', 2.5)]
        btn = E('Shape', name=name, x=float(cx), y=float(CTRL_Y), isTargetOpaque=True)
        btn.add(sem, rect(w, h, h / 2), *paints)
        grp = node(name + ' group', kids + [btn, shape(name + ' ink', rect(w, h, h / 2), fill('ink25'), x=cx + 3, y=CTRL_Y + 4)])
        # labels/icons are authored relative to the button centre
        for kd in kids:
            kd.attrs['x'] = float(kd.attrs.get('x', 0.0)) + cx
            kd.attrs['y'] = float(kd.attrs.get('y', 0.0)) + CTRL_Y
        lis = E('StateMachineListener', targetId=btn.id, name=f'{name} press')
        lis.add(E('ListenerInputType', listenerTypeValue='click'),
                E('ListenerInputTypeSemantic', [E('SemanticInput', actionType='tap')], listenerTypeValue='semanticAction'),
                E('ListenerViewModelChange', [E('BindablePropertyTrigger', [bind(P(req_prop), 686, direction=True)], propertyValue=1)]))
        listeners.append(lis)
        return grp, btn, lis

    chev_l = shape('chevron', straight([(6, -10), (-4, 0), (6, 10)], False), stroke('aub', 3.2))
    prev_g, prev_b, _ = button('Previous', 50, 52, 'previousLabel', 'navPrevRequest', kind='outline', icon=chev_l, show_label=False)
    pause_icon = node('pause bars', [shape('b1', rect(5, 18, 2), fill('cream'), x=-5), shape('b2', rect(5, 18, 2), fill('cream'), x=5)])
    pause_g, pause_b, _ = button('Pause', 112, 52, 'pauseLabel', 'pauseToggleRequest', icon=pause_icon, show_label=False)
    play_icon = shape('play', straight([(-5, -10), (9, 0), (-5, 10)], True, radius=2), fill('cream'))
    play_g, play_b, _ = button('Play', 112, 52, 'playLabel', 'pauseToggleRequest', icon=play_icon, show_label=False, c='tomato')
    arrow = node('arrow', [shape('a', straight([(-8, 0), (8, 0)], False), stroke('cream', 2.6)),
                           shape('h', straight([(2, -6), (8, 0), (2, 6)], False), stroke('cream', 2.6))], x=84)
    cont_g, cont_b, _ = button('Continue', 259, 214, 'continueLabel', 'navNextRequest', icon=arrow)
    share_icon = node('share', [shape('a', straight([(0, 7), (0, -8)], False), stroke('cream', 2.6)),
                                shape('h', straight([(-5, -3), (0, -8), (5, -3)], False), stroke('cream', 2.6))], x=38)
    share_g, share_b, share_l = button('Share', 205, 114, 'shareLabel', 'shareRequest', icon=share_icon, c='tomato')
    replay_g, replay_b, _ = button('Replay', 318, 96, 'replayLabel', 'replayRequest', kind='outline', tc='aub')
    ev_share = E('Event', name='shareTapped')
    share_l.add(E('ListenerFireEvent', eventId=ev_share.id))
    share_l.add(E('ScriptedListenerAction', [E('ScriptInputString', propertyValue='shareTapped', name='label')], scriptAssetId=SCRIPT_AUDIT))

    play_g.attrs['x'] = -400.0   # parked off-canvas until paused
    share_g.attrs['x'] = -400.0
    replay_g.attrs['x'] = -400.0
    controls = node('Controls', [share_g, replay_g, cont_g, play_g, pause_g, prev_g])

    # focus ring (keyboard focus is owned by the director; focusedControl picks the ring pose)
    ring_r = rect(60, 60, 30)
    ring = shape('Focus ring', ring_r, stroke('tomato', 3), x=50, y=CTRL_Y, op=0)
    rings = {0: (50, 60, 0), 1: (50, 62, 1), 2: (112, 62, 1), 3: (259, 224, 1), 4: (205, 124, 1), 5: (318, 106, 1)}
    s_focus = []
    for idx, (fx, fw, fo) in rings.items():
        a = Anim(f'Focus {idx}', 1)
        a.ms(ring, 'x', [(0, float(fx), 'hold')])
        a.ms(ring, 'opacity', [(0, float(fo), 'hold')])
        a.ms(ring_r, 'width', [(0, float(fw), 'hold')])
        anims.append(a)
        s_focus.append(astate(a, 200 + idx * 160, 0))
    for s in s_focus:
        for idx, s2 in enumerate(s_focus):
            if s2 is not s:
                s.add(trans(s2, [cond_num(P('focusedControl'), idx)], duration=120, ease='soft'))
    layers.append(layer('Focus ring', s_focus[0], s_focus))

    # controls swap (summary shows Share + Replay; Continue retires)
    a_norm = Anim('Controls: story', ms2f(300))
    a_sum = Anim('Controls: summary', ms2f(420))
    for g, xn, xs in ((cont_g, 0.0, -400.0), (share_g, -400.0, 0.0), (replay_g, -400.0, 0.0)):
        a_norm.ms(g, 'x', [(0, xn, 'hold')])
        a_sum.ms(g, 'x', [(0, xs, 'hold')])
    for g in (share_g, replay_g):
        a_sum.ms(g, 'scaleX', [(0, 1.0, 'hold')])
        a_sum.ms(g, 'opacity', [(0, 0.0, 'soft'), (380, 1.0)])
        a_sum.ms(g, 'y', [(0, 26.0, 'back'), (380, 0.0)])
    a_norm.ms(cont_g, 'opacity', [(0, 0.0, 'soft'), (280, 1.0)])
    a_norm.ms(cont_g, 'y', [(0, 20.0, 'back'), (280, 0.0)])
    # keep the accessibility tree in step with what is on screen
    def sem(b):
        return b.children[0]
    for b, hn, hs in ((cont_b, False, True), (share_b, True, False), (replay_b, True, False)):
        a_norm.ms(sem(b), 'isHidden', [(0, hn, 'hold')], 'Bool')
        a_sum.ms(sem(b), 'isHidden', [(0, hs, 'hold')], 'Bool')
    s_n = astate(a_norm, 200, 0)
    s_s = astate(a_sum, 400, 0)
    s_n.add(trans(s_s, [cond_num(P('currentScreen'), 10)]))
    s_s.add(trans(s_n, [cond_num(P('currentScreen'), 10, 'notEqual')]))
    layers.append(layer('Controls', s_n, [s_n, s_s]))

    # pause <-> play
    a_pl = Anim('Pause shown', 1)
    a_pa = Anim('Play shown', 1)
    a_pl.ms(pause_g, 'x', [(0, 0.0, 'hold')]); a_pl.ms(play_g, 'x', [(0, -400.0, 'hold')])
    a_pa.ms(pause_g, 'x', [(0, -400.0, 'hold')]); a_pa.ms(play_g, 'x', [(0, 0.0, 'hold')])
    a_pl.ms(pause_b.children[0], 'isHidden', [(0, False, 'hold')], 'Bool'); a_pl.ms(play_b.children[0], 'isHidden', [(0, True, 'hold')], 'Bool')
    a_pa.ms(pause_b.children[0], 'isHidden', [(0, True, 'hold')], 'Bool'); a_pa.ms(play_b.children[0], 'isHidden', [(0, False, 'hold')], 'Bool')
    s_pl = astate(a_pl, 200, 0)
    s_pa = astate(a_pa, 400, 0)
    s_pl.add(trans(s_pa, [cond_bool(P('isPaused'), True)]))
    s_pa.add(trans(s_pl, [cond_bool(P('isPaused'), False)]))
    layers.append(layer('Pause icon', s_pl, [s_pl, s_pa]))

    # previous dims on the first visible scene
    a_pv_on = Anim('Previous enabled', ms2f(200))
    a_pv_off = Anim('Previous disabled', ms2f(200))
    a_pv_on.ms(prev_g, 'opacity', [(0, 0.35, 'soft'), (200, 1.0)])
    a_pv_off.ms(prev_g, 'opacity', [(0, 1.0, 'soft'), (200, 0.35)])
    a_pv_on.ms(prev_b.children[0], 'isDisabled', [(0, False, 'hold')], 'Bool')
    a_pv_off.ms(prev_b.children[0], 'isDisabled', [(0, True, 'hold')], 'Bool')
    s_pv1 = astate(a_pv_off, 200, 0)
    s_pv2 = astate(a_pv_on, 400, 0)
    s_pv1.add(trans(s_pv2, [cond_num(P('currentSegment'), 0, 'greaterThan')]))
    s_pv2.add(trans(s_pv1, [cond_num(P('currentSegment'), 0, 'equal')]))
    layers.append(layer('Previous enabled', s_pv1, [s_pv1, s_pv2]))
    anims += [a_norm, a_sum, a_pl, a_pa, a_pv_on, a_pv_off]

    # ================================================================ persistent motif
    pot_na = E('NestedArtboard', [E('NestedStateMachine', animationId=pot_sm.id, name='Pot machine')],
               artboardId=pot_board.id, x=float(-potmod.CX), y=float(-potmod.CY), name='Pot')
    pot_na.add(bind(P('motionFrozen'), 895))
    pot_hit = E('Shape', [ellipse(214, 176), fill('00FFFFFF')], name='Pot hit area', isTargetOpaque=True, y=14.0)
    pot_hit.add(E('SemanticData', role='button', label='Stir the pot', name='Semantics'))
    motif = node('Motif', [pot_hit, pot_na], x=POSES[1][0], y=POSES[1][1], sx=POSES[1][2], sy=POSES[1][2])
    lis = E('StateMachineListener', targetId=pot_hit.id, name='Pot tap')
    lis.add(E('ListenerInputType', listenerTypeValue='click'),
            E('ListenerInputTypeSemantic', [E('SemanticInput', actionType='tap')], listenerTypeValue='semanticAction'),
            E('ListenerViewModelChange', [E('BindablePropertyTrigger', [bind(P('potTap'), 686, direction=True)], propertyValue=1)]))
    listeners.append(lis)

    pose_states = []
    pose_anims = {}
    for k, (px, py, sc, rot) in POSES.items():
        if k == 9:
            a = Anim('Motif pose 9 (anticipation)', ms2f(1500))
            a.ms(motif, 'x', [(0, px, 'hold'), (500, px, 'lin'), (560, px - 6, 'lin'), (620, px + 6, 'lin'), (680, px - 4, 'lin'), (740, px, 'hold')])
            # anticipation: arrive, rattle, then dissolve into the emblem as it bursts out
            a.ms(motif, 'y', [(0, py, 'hold'), (740, py, 'backin'), (1050, 556.0)])
            a.ms(motif, 'scaleX', [(0, sc, 'hold'), (740, sc, 'backin'), (1050, 0.2)])
            a.ms(motif, 'scaleY', [(0, sc, 'hold'), (740, sc, 'backin'), (1050, 0.2)])
            a.ms(motif, 'rotation', [(0, rot, 'hold')])
            a.ms(motif, 'opacity', [(0, 1.0, 'hold'), (820, 1.0, 'lin'), (1050, 0.0)])
        elif k == 10:
            a = Anim('Motif pose 10 (into the card)', ms2f(1400))
            a.ms(motif, 'x', [(0, 195.0, 'hold')])
            a.ms(motif, 'y', [(0, 470.0, 'snap'), (700, py)])
            a.ms(motif, 'scaleX', [(0, 0.7, 'snap'), (700, sc)])
            a.ms(motif, 'scaleY', [(0, 0.7, 'snap'), (700, sc)])
            a.ms(motif, 'rotation', [(0, 0.0, 'hold')])
            a.ms(motif, 'opacity', [(0, 1.0, 'hold'), (760, 1.0, 'lin'), (1000, 0.0)])
        else:
            a = Anim(f'Motif pose {k}', 1)
            for p, v in (('x', px), ('y', py), ('scaleX', sc), ('scaleY', sc), ('rotation', rot), ('opacity', 1.0)):
                a.ms(motif, p, [(0, float(v), 'hold')])
        pose_anims[k] = a
        anims.append(a)
        pose_states.append(astate(a, 120 * k, 260 if k % 2 else -260))
    # reduced motion: the timed poses (9, 10) get static end poses
    rm_targets = {k: pose_states[k - 1] for k in POSES}
    rm_states = []
    for k, (px, py, sc, rot) in ((9, (195.0, 556.0, 0.2, 0.0)), (10, POSES[10])):
        a = Anim(f'Motif pose {k} (reduced motion)', 1)
        for p, v in (('x', px), ('y', py), ('scaleX', sc), ('scaleY', sc), ('rotation', rot), ('opacity', 0.0)):
            a.ms(motif, p, [(0, float(v), 'hold')])
        anims.append(a)
        st_ = astate(a, 120 * k, 520)
        rm_states.append(st_)
        rm_targets[k] = st_
    # explicit transitions between every pair (no AnyState), motion-reduced variants first
    every = pose_states + rm_states
    for s in every:
        for k in POSES:
            if rm_targets[k] is not s:
                s.add(trans(rm_targets[k], [cond_num(P('currentScreen'), k), cond_bool(P('reducedMotion'), True)], duration=0))
            if pose_states[k - 1] is not s:
                s.add(trans(pose_states[k - 1], [cond_num(P('currentScreen'), k), cond_bool(P('reducedMotion'), False)], duration=720, ease='inout'))
    layers.append(layer('Motif pose', pose_states[0], every))

    # ================================================================ signature handoff (steam ribbon + tablecloth pull)
    ribbon_pts = [(-260, 300), (-150, 240), (-60, 120), (40, 60), (90, -40), (30, -110), (-40, -60), (10, 10), (120, -40), (190, -180), (300, -300)]
    rib, rib_trims, (rib_path, rib_ink) = art.steam_curl('Steam ribbon', ribbon_pts, w=30, c='cream')
    # thin tomato thread inside the ribbon: the hand-drawn ink line
    thread_trim = E('TrimPath', start=0.0, end=1.0, modeValue='sequential', name='Trim')
    thread = shape('Ribbon thread', smooth(ribbon_pts, False), [E('Stroke', [E('SolidColor', colorValue=col('tomato'), name='Color'), thread_trim], thickness=3.0, cap='round', join='round', name='Stroke')])
    rib.children.insert(0, thread)

    cloth_w, cloth_h = 470, 190
    wave = [(-cloth_w / 2, -cloth_h / 2 + 10), (-cloth_w / 4, -cloth_h / 2 - 8), (0, -cloth_h / 2 + 8), (cloth_w / 4, -cloth_h / 2 - 10),
            (cloth_w / 2, -cloth_h / 2 + 6), (cloth_w / 2, cloth_h / 2), (-cloth_w / 2, cloth_h / 2)]
    clip_path = smooth(wave, True, corners=(0, 4, 5, 6))
    clip_shape = shape('Cloth mask', clip_path, fill('01FFFFFF'))
    cloth_check = art.gingham('Cloth check', cloth_w, cloth_h, cell=24, c='basil', bg='cream')
    cloth_check.add(E('ClippingShape', sourceId=clip_shape.id, name='Clip'))
    hem = shape('Cloth hem', smooth(wave[:5], False), stroke('basilDk', 4))
    riders = [art.tomato('rider tomato', 0.6, x=-120, y=-cloth_h / 2 - 12), art.garlic('rider garlic', 0.6, x=30, y=-cloth_h / 2 - 14),
              art.leaf('rider basil', 0.7, x=120, y=-cloth_h / 2 - 16, rot=0.9), art.lemon_slice('rider lemon', 0.6, x=-40, y=-cloth_h / 2 - 12)]
    cloth = node('Tablecloth', riders + [hem, cloth_check, clip_shape, shape('cloth ink', clip_path_copy(wave), fill('ink25'), x=6, y=8)], x=-700, y=300)
    handoff = node('Handoff', [rib, cloth], x=W / 2, y=H / 2)
    handoff.attrs['opacity'] = 0.0

    def handoff_anim(name, sx):
        a = Anim(name, ms2f(820))
        a.ms(handoff, 'opacity', [(0, 1.0, 'hold'), (820, 0.0, 'hold')])
        a.ms(handoff, 'scaleX', [(0, float(sx), 'hold')])
        for tr in rib_trims + [thread_trim]:
            a.ms(tr, 'end', [(0, 0.0, 'soft'), (420, 1.0, 'hold')])
            a.ms(tr, 'start', [(0, 0.0, 'hold'), (200, 0.0, 'in'), (700, 1.0, 'hold')])
        # the ribbon curls tighter as it travels (vertex morph)
        for path in (rib_path, rib_ink):
            vs = path.children
            for vi in (5, 6, 7):
                v = vs[vi]
                vx, vy = float(v.attrs['x']), float(v.attrs['y'])
                a.ms(v, 'x', [(0, vx * 1.4, 'soft'), (500, vx * 0.8, 'inout'), (820, vx)])
                a.ms(v, 'y', [(0, vy * 0.6, 'soft'), (500, vy * 1.15, 'inout'), (820, vy)])
        a.ms(cloth, 'x', [(0, -470.0, 'hold'), (220, -470.0, 'inout'), (820, 470.0)])
        a.ms(cloth, 'y', [(0, 300.0, 'hold'), (240, 300.0, 'inout'), (520, 286.0, 'inout'), (820, 300.0)])
        a.ms(cloth, 'rotation', [(0, 0.0, 'hold'), (240, 0.04, 'inout'), (520, -0.03, 'inout'), (820, 0.0)])
        # the hem ripples
        for path in (clip_path, hem.children[0]):
            vs = path.children
            for vi in (1, 2, 3):
                if vi >= len(vs):
                    continue
                v = vs[vi]
                vy = float(v.attrs['y'])
                a.ms(v, 'y', [(0, vy, 'hold'), (240, vy, 'inout'), (420, vy + (-16 if vi % 2 else 14), 'inout'), (620, vy + (12 if vi % 2 else -10), 'inout'), (820, vy)])
        # riders get flung and rearranged as the cloth is pulled
        for i, r in enumerate(riders):
            ry = float(r.attrs['y'])
            a.ms(r, 'y', [(0, ry, 'hold'), (300 + i * 40, ry, 'out'), (480 + i * 40, ry - 90 - i * 18, 'in'), (700 + i * 40, ry)])
            a.ms(r, 'rotation', [(0, float(r.attrs.get('rotation', 0.0)), 'hold'), (300 + i * 40, 0.0, 'lin'), (700 + i * 40, (1 if i % 2 else -1) * 2.4)])
        return a

    a_fwd = handoff_anim('Handoff forward', 1)
    a_back = handoff_anim('Handoff back (mirrored)', -1)
    a_hidle = Anim('Handoff idle', 1)
    a_hidle.ms(handoff, 'opacity', [(0, 0.0, 'hold')])
    s_hi = astate(a_hidle, 0, 0)
    s_hf = astate(a_fwd, 240, -120)
    s_hb = astate(a_back, 240, 120)
    rm = P('reducedMotion')
    for s in (s_hi, s_hf, s_hb):
        s.add(trans(s_hf, [cond_trig(P('handoffForward')), cond_bool(rm, False)]),
              trans(s_hb, [cond_trig(P('handoffBack')), cond_bool(rm, False)]))
    s_hf.add(trans(s_hi, [], exit_pct=100))
    s_hb.add(trans(s_hi, [], exit_pct=100))
    layers.append(layer('Signature handoff', s_hi, [s_hi, s_hf, s_hb]))
    anims += [a_fwd, a_back, a_hidle]

    # ================================================================ scenes
    scene_nodes = []
    for sab, ssm in scene_boards:
        na = E('NestedArtboard', [E('NestedStateMachine', animationId=ssm.id, name='machine')], artboardId=sab.id,
               x=0.0, y=0.0, name=sab.attrs['name'])
        na.add(bind(P('motionFrozen'), 895))
        scene_nodes.append(na)
    scenes = node('Scenes', list(reversed(scene_nodes)))

    # ================================================================ backdrop
    rnd = random.Random(7)
    specks = [shape(f'speck {i}', ellipse(r, r), fill('1A48293D'), x=rnd.uniform(8, 382), y=rnd.uniform(90, 760))
              for i, r in enumerate([rnd.uniform(1.5, 3.2) for _ in range(46)])]
    backdrop = node('Backdrop', specks + [
        shape('Paper', rect(W, H, 0, 0, 0), fill('paper')),
    ])

    # ================================================================ director (input + sequencing)
    root = E('LayoutComponent', width=float(W), height=float(H), name='Director root')
    rst = E('LayoutComponentStyle', layoutWidthScaleType='fill', layoutHeightScaleType='fill', name='Director root style')
    root.attrs['styleId'] = rst.id
    director = E('ScriptedLayout', [E('FocusData', name='Keyboard focus')], scriptAssetId=SCRIPT_DIRECTOR, name='Director')
    root.add(rst, director)

    # ================================================================ events
    ev_screen = E('Event', name='screenChanged')
    ev_fin = E('Event', name='recapFinished')
    l_screen = E('StateMachineListener', [
        E('ListenerInputTypeViewModel', viewModelPathIds=P('currentScreen'), listenerTypeValue='viewModel'),
        E('ListenerFireEvent', eventId=ev_screen.id),
        E('ScriptedListenerAction', [E('ScriptInputString', propertyValue='screenChanged', name='label')], scriptAssetId=SCRIPT_AUDIT),
    ], targetId=ab.id, name='screenChanged event')
    l_fin = E('StateMachineListener', [
        E('ListenerInputTypeViewModel', viewModelPathIds=P('recapFinishedSignal'), listenerTypeValue='viewModel'),
        E('ListenerFireEvent', eventId=ev_fin.id),
        E('ScriptedListenerAction', [E('ScriptInputString', propertyValue='recapFinished', name='label')], scriptAssetId=SCRIPT_AUDIT),
    ], targetId=ab.id, name='recapFinished event')
    listeners += [l_screen, l_fin]

    # give the director keyboard focus on load
    a_boot = Anim('Boot', 1)
    s_boot = astate(a_boot, 0, 0)
    s_boot.add(E('FocusActionTarget', targetId=director.id))
    layers.append(layer('Boot focus', s_boot, [s_boot]))
    anims.append(a_boot)

    sm = E('StateMachine', name='Recap sequence')
    sm.add(*listeners)
    sm.add(*layers)
    ab.attrs['defaultStateMachineId'] = sm.id
    ab.add(st, ring, controls, header, handoff, motif, scenes, backdrop, root, ev_screen, ev_fin, ev_share, sm)
    ab.add(*[a.build() for a in anims])
    return ab


def T_open_():
    return E('FormulaTokenParenthesisOpen')


def clip_path_copy(wave):
    return smooth(wave, True, corners=(0, 4, 5, 6))


def _semantic_label_key():
    return 'label'
