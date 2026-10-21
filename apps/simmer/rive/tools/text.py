"""Text helpers: Bricolage Grotesque (display), Source Sans 3 (body), Caveat (hand)."""
from rml import E, col, bind
from data import FONT_DISPLAY, FONT_BODY, FONT_HAND, P

WGHT = 2003265652
WDTH = 2003072104
OPSZ = 1869640570

FACES = {
    'display': (FONT_DISPLAY, 'Bricolage Grotesque'),
    'body': (FONT_BODY, 'Source Sans 3'),
    'hand': (FONT_HAND, 'Caveat'),
}
WEIGHT_NAMES = {400: 'Regular', 500: 'Medium', 600: 'SemiBold', 700: 'Bold', 800: 'ExtraBold', 900: 'Black'}


def style(face, size, weight, color, lh=None, ls=None, wdth=None, opsz=None, name='Style', color_id=None):
    fid, fam = FACES[face]
    st = E('TextStylePaint', fontSize=float(size), fontAssetId=fid, familyName=fam,
           styleName=WEIGHT_NAMES.get(weight, 'Custom') if (wdth is None) else 'Custom', name=name)
    if lh:
        st.attrs['lineHeight'] = float(lh)
    if ls is not None:
        st.attrs['letterSpacing'] = float(ls)
    st.add(E('Fill', [E('SolidColor', colorValue=col(color), name='Color', id=color_id)], name='Fill'))
    st.add(E('TextStyleAxis', tag=WGHT, axisValue=float(weight), name='wght'))
    if face == 'display':
        st.add(E('TextStyleAxis', tag=OPSZ, axisValue=float(opsz if opsz else min(96, max(12, size))), name='opsz'))
        st.add(E('TextStyleAxis', tag=WDTH, axisValue=float(wdth if wdth else 100), name='wdth'))
    return st


def text(name, runs, x=0, y=0, width=None, height=None, sizing='autoWidth', align='left', overflow='visible',
         ox=0, oy=0, rot=0, wrap='wrap', id=None, op=1, vtrim=False):
    """runs: list of (style_el, literal, bind_prop or None, converter or None)."""
    t = E('Text', name=name, x=float(x), y=float(y), sizingValue=sizing, alignValue=align, overflowValue=overflow,
          wrapValue=wrap, originX=float(ox), originY=float(oy), id=id)
    if width is not None:
        t.attrs['width'] = float(width)
    if height is not None:
        t.attrs['height'] = float(height)
    if rot:
        t.attrs['rotation'] = float(rot)
    if op != 1:
        t.attrs['opacity'] = float(op)
    styles = []
    seen = set()
    for st, _lit, _b, _c in runs:
        if st.id not in seen:
            styles.append(st)
            seen.add(st.id)
    t.add(*styles)
    for st, lit, bp, conv in runs:
        r = E('TextValueRun', styleId=st.id, text=lit, name='Run')
        if bp:
            r.add(bind(P(bp), 268, conv))
        t.add(r)
    return t


def reveal_modifier(t, y=26, rot=0.0, units=2, soft=0.35):
    """Attach a word-by-word rise + fade modifier. Returns the range element (key modifyFrom/falloffFrom)."""
    rng = E('TextModifierRange', modifyFrom=-soft, modifyTo=1.0 + soft, falloffFrom=0.0, falloffTo=1.0 + soft,
            unitsValue=units, name='Reveal range')
    grp = E('TextModifierGroup', [rng], modifyOpacity=True, modifyTranslation=True, invertOpacity=True,
            opacity=0.0, y=float(y), name='Reveal')
    if rot:
        grp.attrs['modifyRotation'] = True
        grp.attrs['rotation'] = float(rot)
    t.add(grp)
    return rng


def key_reveal(anim, rng, t0, t1, soft=0.35, ease='soft'):
    """Sweep the hidden span out of the text between t0..t1 ms."""
    anim.ms(rng, 'modifyFrom', [(0, -soft, 'hold'), (t0, -soft, ease), (t1, 1.0 + soft)])
    anim.ms(rng, 'falloffFrom', [(0, 0.0, 'hold'), (t0, 0.0, ease), (t1, 1.0 + 2 * soft)])


def key_shown(anim, rng, t=0, soft=0.35):
    anim.ms(rng, 'modifyFrom', [(t, 1.0 + soft, 'hold')])
    anim.ms(rng, 'falloffFrom', [(t, 1.0 + 2 * soft, 'hold')])
