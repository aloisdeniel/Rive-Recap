"""The root artboard: chrome, persistent motif, signature handoff, controls, director."""
import math
import random
from rml import (E, node, shape, fill, stroke, ellipse, rect, star, smooth, straight, Anim, layer, astate, trans,
                 cond_num, cond_bool, cond_trig, bind, ms2f, col)
from data import P, VM_ID, SCRIPT_DIRECTOR, SCRIPT_AUDIT, SCRIPT_RISO, SCRIPT_STEAM, SCRIPT_CLOTH, CONV_INT, formula, T_in, T_v, T_p, T_op, T_fn, T_sep, T_close
from text import style, text
import art
import pot as potmod
import stage as lay
from stage import p as vp, vmax, INPUT

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
    9: (195, 570, 0.9, 0.0),
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
    # follows the stage: brand on the left margin, year on the right, progress across the real width;
    # on short canvases the header tightens with the content top (layoutTop)
    M_, TOP_ = vp('layoutMargin'), vp('layoutTop')
    head_dy = (TOP_ - 92.0) * 0.5
    head_style = style('display', 25, 800, 'aub', ls=-0.5, opsz=36, name='Wordmark')
    wordmark = text('Wordmark', [(head_style, 'Simmer', None, None)], x=24, y=24)
    steam_mark = node('Wordmark steam', [
        shape(f'w{i}', smooth([(0, 0), (-3, -6), (2, -12), (-1, -17)], False), stroke('tomato', 2.4), x=i * 6) for i in range(3)
    ], x=127, y=45)
    brand = node('Brand', [wordmark, steam_mark])
    lay.bind_expr(brand, 13, 'Layout header left', M_ - 24.0)
    lay.bind_expr(brand, 14, 'Layout header dy', head_dy)
    year_st = style('body', 15, 700, 'aub', name='Year')
    year = text('Year', [(year_st, '2026', 'year', CONV_INT)], x=286, y=30, width=80, sizing='fixed', height=22, align='right')
    year_slot = node('Year slot', [year])
    lay.bind_expr(year_slot, 13, 'Layout header right', lay.W - M_ - 366.0)
    lay.bind_expr(year_slot, 14, 'Layout header dy', head_dy)

    # progress segments: geometry derived from visibleCount and the real width, fill from currentSegment + screenProgress
    GAP, PY = 5.0, 72.0
    TW, X0 = lay.W - M_ * 2.0, M_
    n_in = INPUT
    vc = vp('visibleCount')
    seg_w = formula('Segment width', ((TW - GAP * (n_in - 1.0)) / vmax(1.0, n_in)).tokens())
    segs = []
    for i in range(10):
        cx = formula(f'Segment {i} x', (X0 + i * ((TW - GAP * (n_in - 1.0)) / vmax(1.0, n_in) + GAP)).tokens())
        cop = formula(f'Segment {i} visible', lay.clamp(n_in - float(i), 0.0, 1.0).tokens())
        cfill = formula(f'Segment {i} fill', (((TW - GAP * (vc - 1.0)) / vmax(1.0, vc)) * lay.clamp(vp('currentSegment') + n_in - float(i), 0.0, 1.0)).tokens())
        track_r = E('Rectangle', width=30.0, height=4.0, cornerRadiusTL=2.0, originX=0.0, originY=0.5, name='Path')
        track_r.add(bind(P('visibleCount'), 20, seg_w))
        fill_r = E('Rectangle', width=0.0, height=4.0, cornerRadiusTL=2.0, originX=0.0, originY=0.5, name='Path')
        fill_r.add(bind(P('screenProgress'), 20, cfill))
        sg = node(f'Segment {i}', [
            shape('fill', fill_r, fill('tomato')),
            shape('track', track_r, fill('3348293D')),
        ], x=24 + i * 34, y=PY)
        sg.add(bind(P('visibleCount'), 13, cx))
        sg.add(bind(P('visibleCount'), 18, cop))
        segs.append(sg)
    progress = node('Progress', segs)
    lay.bind_expr(progress, 14, 'Layout progress dy', TOP_ - 92.0)
    header = node('Header', [brand, year_slot, progress])

    # ================================================================ controls
    # Each control is drawn around (0, 0) inside a slot node the layout places: Previous and
    # Pause/Play at the left margin, Continue (or Share + Replay on the summary) at the right.
    # The swap layers park hidden controls by keying the group's x far off any canvas.
    PARK = -20000.0
    CONT_W = vp('layoutContinueWidth')
    rings = {}
    parts = {}
    # summary row: Share + Replay sit right of Pause. Where they do not fit at full size (narrow
    # portraits, < 222 pt free) Replay becomes a 52 pt icon button and Share takes what is left.
    SUM_AVAIL = lay.W - M_ * 2.0 - 120.0
    COMPACT = lay.step(221.5 - SUM_AVAIL)
    REPLAY_W = 108.0 - COMPACT * 56.0
    SHARE_W = 112.0 - COMPACT * vmax(0.0, 112.0 - (SUM_AVAIL - 58.0))

    def button(name, w, label_prop, req_prop, kind='solid', icon=None, show_label=True, c='aub', tc='cream', icon_left=False, w_expr=None):
        h = 52
        kids = []
        label = None
        if show_label:
            lst = style('body', 18, 700, tc, name='Label')
            label = text('Label', [(lst, 'Label', label_prop, None)], x=-w / 2 + 12 + (22 if icon_left else 0), y=-12, width=w - 24 - (22 if icon else 0),
                         height=26, sizing='fixed', align='center', overflow='ellipsis', wrap='noWrap')
            kids.append(label)
        if icon is not None:
            kids.append(icon)
        sem = E('SemanticData', role='button', label='', name='Semantics')
        sem.add(bind(P(label_prop), 983))
        paints = [fill(c)] if kind == 'solid' else [fill('cream'), stroke('aub', 2.5)]
        body_r = rect(w, h, h / 2)
        ink_r = rect(w, h, h / 2)
        btn = E('Shape', name=name, x=0.0, y=0.0, isTargetOpaque=True)
        btn.add(sem, body_r, *paints)
        grp = node(name + ' group', kids + [btn, shape(name + ' ink', ink_r, fill('ink25'), x=3, y=4)])
        if w_expr is not None:
            # a button whose width follows the layout (Continue)
            for r_ in (body_r, ink_r):
                lay.bind_expr(r_, 20, f'Layout {name} width', w_expr)
            if label is not None:
                lay.bind_expr(label, 13, f'Layout {name} label x', w_expr * -0.5 + 12.0)
                lay.bind_expr(label, 285, f'Layout {name} label width', w_expr - 46.0)
            if icon is not None:
                lay.bind_expr(icon, 13, f'Layout {name} icon x', w_expr * 0.5 - 23.0)
        parts[name] = dict(body=body_r, ink=ink_r, label=label, icon=icon)
        lis = E('StateMachineListener', targetId=btn.id, name=f'{name} press')
        lis.add(E('ListenerInputType', listenerTypeValue='click'),
                E('ListenerInputTypeSemantic', [E('SemanticInput', actionType='tap')], listenerTypeValue='semanticAction'),
                E('ListenerViewModelChange', [E('BindablePropertyTrigger', [bind(P(req_prop), 686, direction=True)], propertyValue=1)]))
        listeners.append(lis)
        return grp, btn, lis

    def focus_ring(idx, w, w_expr=None):
        rr = rect(w + 10, 62, 31)
        if w_expr is not None:
            lay.bind_expr(rr, 20, f'Layout focus ring {idx} width', w_expr + 10.0)
        r_ = shape(f'Focus ring {idx}', rr, stroke('tomato', 3), op=0)
        rings[idx] = r_
        return r_

    def slot(name, kids, x_expr):
        sl = node(name + ' slot', kids)
        lay.bind_expr(sl, 13, f'Layout {name} slot x', x_expr)
        sl.add(bind(P('layoutControlsY'), 14))
        return sl

    chev_l = shape('chevron', straight([(6, -10), (-4, 0), (6, 10)], False), stroke('aub', 3.2))
    prev_g, prev_b, _ = button('Previous', 52, 'previousLabel', 'navPrevRequest', kind='outline', icon=chev_l, show_label=False)
    pause_icon = node('pause bars', [shape('b1', rect(5, 18, 2), fill('cream'), x=-5), shape('b2', rect(5, 18, 2), fill('cream'), x=5)])
    pause_g, pause_b, _ = button('Pause', 52, 'pauseLabel', 'pauseToggleRequest', icon=pause_icon, show_label=False)
    play_icon = shape('play', straight([(-5, -10), (9, 0), (-5, 10)], True, radius=2), fill('cream'))
    play_g, play_b, _ = button('Play', 52, 'playLabel', 'pauseToggleRequest', icon=play_icon, show_label=False, c='tomato')
    arrow = node('arrow', [shape('a', straight([(-8, 0), (8, 0)], False), stroke('cream', 2.6)),
                           shape('h', straight([(2, -6), (8, 0), (2, 6)], False), stroke('cream', 2.6))], x=84)
    cont_g, cont_b, _ = button('Continue', 214, 'continueLabel', 'navNextRequest', icon=arrow, w_expr=CONT_W)
    share_icon = node('share', [shape('a', straight([(0, 7), (0, -8)], False), stroke('cream', 2.6)),
                                shape('h', straight([(-5, -3), (0, -8), (5, -3)], False), stroke('cream', 2.6))], x=38)
    share_g, share_b, share_l = button('Share', 112, 'shareLabel', 'shareRequest', icon=share_icon, c='tomato')
    replay_g, replay_b, _ = button('Replay', 108, 'replayLabel', 'replayRequest', kind='outline', tc='aub', icon=replay_icon(), icon_left=True)
    ev_share = E('Event', name='shareTapped')
    share_l.add(E('ListenerFireEvent', eventId=ev_share.id))
    share_l.add(E('ScriptedListenerAction', [E('ScriptInputString', propertyValue='shareTapped', name='label')], scriptAssetId=SCRIPT_AUDIT))

    for nm, w_ in (('Share', SHARE_W), ('Replay', REPLAY_W)):
        pt = parts[nm]
        for r_ in (pt['body'], pt['ink']):
            lay.bind_expr(r_, 20, f'Layout {nm} width', w_)
        lay.bind_expr(pt['label'], 285, f'Layout {nm} label width', w_ - 46.0)
    lay.bind_expr(parts['Share']['label'], 13, 'Layout Share label x', SHARE_W * -0.5 + 12.0)
    lay.bind_expr(parts['Share']['icon'], 13, 'Layout Share icon x', SHARE_W * 0.5 - 18.0)
    lay.bind_expr(parts['Replay']['label'], 13, 'Layout Replay label x', REPLAY_W * -0.5 + 34.0)
    lay.bind_expr(parts['Replay']['label'], 18, 'Layout Replay label shown', 1.0 - COMPACT)
    lay.bind_expr(parts['Replay']['icon'], 13, 'Layout Replay icon x', (REPLAY_W * -0.5 + 18.0) * (1.0 - COMPACT))

    play_g.attrs['x'] = PARK   # parked off-canvas until paused
    share_g.attrs['x'] = PARK
    replay_g.attrs['x'] = PARK
    RIGHT = lay.W - M_
    controls = node('Controls', [
        slot('Share', [focus_ring(4, 112, SHARE_W), share_g], (1.0 - COMPACT) * (RIGHT - 166.0) + COMPACT * (RIGHT - 58.0 - SHARE_W * 0.5)),
        slot('Replay', [focus_ring(5, 108, REPLAY_W), replay_g], RIGHT - 50.0 + COMPACT * 24.0),
        slot('Continue', [focus_ring(3, 214, CONT_W), cont_g], RIGHT - CONT_W * 0.5),
        slot('Pause', [focus_ring(2, 52), play_g, pause_g], M_ + 88.0),
        slot('Previous', [focus_ring(1, 52), prev_g], M_ + 26.0),
    ])

    # focus ring (keyboard focus is owned by the director; focusedControl picks which ring shows)
    s_focus = []
    for idx in range(6):
        a = Anim(f'Focus {idx}', 1)
        for j, r_ in rings.items():
            a.ms(r_, 'opacity', [(0, 1.0 if j == idx else 0.0, 'hold')])
        anims.append(a)
        s_focus.append(astate(a, 200 + idx * 160, 0))
    for s_ in s_focus:
        for idx, s2 in enumerate(s_focus):
            if s2 is not s_:
                s_.add(trans(s2, [cond_num(P('focusedControl'), idx)], duration=120, ease='soft'))
    layers.append(layer('Focus ring', s_focus[0], s_focus))

    # controls swap (summary shows Share + Replay; Continue retires)
    a_norm = Anim('Controls: story', ms2f(300))
    a_sum = Anim('Controls: summary', ms2f(420))
    for g, xn, xs in ((cont_g, 0.0, PARK), (share_g, PARK, 0.0), (replay_g, PARK, 0.0)):
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
    a_pl.ms(pause_g, 'x', [(0, 0.0, 'hold')]); a_pl.ms(play_g, 'x', [(0, PARK, 'hold')])
    a_pa.ms(pause_g, 'x', [(0, PARK, 'hold')]); a_pa.ms(play_g, 'x', [(0, 0.0, 'hold')])
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
    # the poses are authored in each scene's master coordinates; the frame maps them onto the
    # current scene's art (the director eases it over the same 720 ms as the pose carry)
    motif_frame = node('Motif frame', [motif])
    motif_frame.add(bind(P('motifFrameX'), 13), bind(P('motifFrameY'), 14),
                    bind(P('motifFrameScale'), 16), bind(P('motifFrameScale'), 17))
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
            a.ms(motif, 'y', [(0, py, 'hold'), (740, py, 'backin'), (1050, 516.0)])
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
    for k, (px, py, sc, rot) in ((9, (195.0, 516.0, 0.2, 0.0)), (10, POSES[10])):
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
    # the steam ribbon is a GPU shader now (scripts/steam.luau + .wgsl): keyed progress + direction
    steam_p = E('ScriptInputNumber', propertyValue=0.0, name='progress')
    steam_d = E('ScriptInputNumber', propertyValue=1.0, name='dir')
    steam_root = E('LayoutComponent', width=float(W), height=float(H), name='Steam root')
    steam_st = overlay_style('Steam style')
    steam_root.attrs['styleId'] = steam_st.id
    steam_root.add(steam_st, E('ScriptedLayout', [steam_p, steam_d], scriptAssetId=SCRIPT_STEAM, name='Steam'))

    # the tablecloth is a simulated 3D cloth (scripts/cloth.luau + .wgsl) in a fill-sized layout so it
    # renders at the presenting pixel density; the ingredients riding on it are small vector artboards
    import scenes_impl
    rider_specs = [('Rider tomato', lambda: art.tomato('tomato', 1.0, x=50, y=54)),
                   ('Rider garlic', lambda: art.garlic('garlic', 1.0, x=50, y=54)),
                   ('Rider basil', lambda: art.leaf('basil', 1.2, x=50, y=50, rot=0.9)),
                   ('Rider lemon', lambda: art.lemon_slice('lemon', 1.0, x=50, y=50))]
    rider_ids = []
    for i, (rname, fn) in enumerate(rider_specs):
        rb = E('Artboard', isComponent=True, width=100.0, height=100.0, name=rname, x=float(500 + i * 140), y=1900.0, clip=False)
        rst_ = E('LayoutComponentStyle', name='Artboard Style')
        rb.attrs['styleId'] = rst_.id
        rb.add(rst_, fn())
        scenes_impl.EXTRA.append((rb, None))
        rider_ids.append(rb.id)
    cloth_p = E('ScriptInputNumber', propertyValue=0.0, name='progress')
    cloth_d = E('ScriptInputNumber', propertyValue=1.0, name='dir')
    cloth_root = E('LayoutComponent', width=float(W), height=float(H), name='Tablecloth root')
    cloth_st = overlay_style('Tablecloth style')
    cloth_root.attrs['styleId'] = cloth_st.id
    cloth_root.add(cloth_st, E('ScriptedLayout', [cloth_p, cloth_d] + [E('ScriptInputArtboard', artboardId=rid, name=f'rider{i + 1}') for i, rid in enumerate(rider_ids)],
                                scriptAssetId=SCRIPT_CLOTH, name='Tablecloth'))

    def handoff_anim(name, sx):
        a = Anim(name, ms2f(820))
        for inp in (steam_p, cloth_p):
            a.ms(inp, 'propertyValue', [(0, 0.0, 'lin'), (820, 1.0, 'hold')])
        for inp in (steam_d, cloth_d):
            a.ms(inp, 'propertyValue', [(0, float(sx), 'hold')])
        return a

    a_fwd = handoff_anim('Handoff forward', 1)
    a_back = handoff_anim('Handoff back (mirrored)', -1)
    a_hidle = Anim('Handoff idle', 1)
    a_hidle.ms(steam_p, 'propertyValue', [(0, 0.0, 'hold')])
    a_hidle.ms(cloth_p, 'propertyValue', [(0, 0.0, 'hold')])
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
    paper_r = rect(W, H, 0, 0, 0)
    paper_r.add(bind(P('stageWidth'), 20), bind(P('stageHeight'), 21))
    speck_g = node('Specks', specks)
    cover = vmax(lay.W / 390.0, lay.H / 844.0)
    lay.bind_expr(speck_g, 16, 'Layout cover scale', cover)
    lay.bind_expr(speck_g, 17, 'Layout cover scale', cover)
    backdrop = node('Backdrop', [speck_g, shape('Paper', paper_r, fill('paper'))])

    # ================================================================ director (input + sequencing)
    root = E('LayoutComponent', width=float(W), height=float(H), name='Director root')
    rst = overlay_style('Director root style')
    root.attrs['styleId'] = rst.id
    director = E('ScriptedLayout', [E('FocusData', name='Keyboard focus')], scriptAssetId=SCRIPT_DIRECTOR, name='Director')
    root.add(rst, director)

    # risograph stock over everything (scripts/riso.luau): paper tooth (multiply) + ink voids (screen)
    riso_root = E('LayoutComponent', width=float(W), height=float(H), name='Riso stock root')
    riso_st = overlay_style('Riso stock style')
    riso_root.attrs['styleId'] = riso_st.id
    riso_root.add(riso_st, E('ScriptedLayout', scriptAssetId=SCRIPT_RISO, name='Riso stock'))

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
    ab.add(st, riso_root, controls, header, motif_frame, cloth_root, steam_root, scenes, backdrop, root, ev_screen, ev_fin, ev_share, sm)
    ab.add(*[a.build() for a in anims])
    return ab


def overlay_style(name):
    """A full-stage layout box pinned to all four edges. Absolute, so several of them can
    overlay each other: the artboard is a flex row and would otherwise lay them side by side."""
    a = dict(positionTypeValue='absolute', widthUnitsValue='auto', heightUnitsValue='auto', name=name)
    for k in ('Top', 'Bottom', 'Left', 'Right'):
        a[f'position{k}'] = 0.0
        a[f'position{k}UnitsValue'] = 'points'
    return E('LayoutComponentStyle', **a)


def replay_icon():
    """A counter-clockwise circular arrow, built from geometry: the arc is open on the right,
    and the arrowhead sits on the arc's end, pointing along the arc's tangent there."""
    r = 6.5
    t0, t1 = math.radians(-10), math.radians(-10 - 265)   # decreasing angle = counter-clockwise on screen
    pts = [(r * math.cos(t0 + (t1 - t0) * k / 16), r * math.sin(t0 + (t1 - t0) * k / 16)) for k in range(17)]
    ex, ey = pts[-1]
    # direction of travel at the end: d/dt of (cos, sin) with t decreasing
    dx, dy = math.sin(t1), -math.cos(t1)
    px, py = -dy, dx
    tip = (ex + dx * 2.2, ey + dy * 2.2)
    w1 = (tip[0] - dx * 5.2 + px * 4.0, tip[1] - dy * 5.2 + py * 4.0)
    w2 = (tip[0] - dx * 5.2 - px * 4.0, tip[1] - dy * 5.2 - py * 4.0)
    return node('replay', [
        shape('head', straight([w1, tip, w2], False), stroke('aub', 2.4)),
        shape('arc', smooth(pts, False), stroke('aub', 2.4)),
    ], x=-36)


def T_open_():
    return E('FormulaTokenParenthesisOpen')


def clip_path_copy(wave):
    return smooth(wave, True, corners=(0, 4, 5, 6))


def _semantic_label_key():
    return 'label'
