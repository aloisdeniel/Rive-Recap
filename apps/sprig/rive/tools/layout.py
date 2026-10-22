"""Sprig responsive layout: the chrome bands of each orientation and the placement of every scene group.

Two layouts, chosen by a pure width breakpoint (_landscape = _vw >= layoutBreakpoint, default 768):

  portrait   the phone composition. Chrome: wordmark + year + progress on top, Previous / Continue /
             Pause along the bottom. Tall canvases stack copy over art (the 390 x 844 design is the
             identity case); short wide canvases (a phone on its side, e.g. 740 x 360) put the copy
             column left and the art right, with compact chrome.
  landscape  the large-canvas composition. Chrome: wordmark, year and a full-width progress row on top,
             a control cluster at the bottom right. Wide canvases put the hero art left and the number +
             copy column right; tall ones (768 x 1024, 820 x 1180) set the number and the copy side by
             side in a row above the art.

Every value here is an expression of the viewport (resp.VW, VH, L, T) compiled into formula converters.
"""
from resp import *  # noqa
import resp
from rml import rect

# ------------------------------------------------------------------ portrait chrome
kP = clamp((VH - 400) / 300, 0, 1)          # 0 on short canvases (compact chrome) .. 1 from 700 pt
MP = clamp(VW / 16.25, 20, 48)               # side margin (24 at 390)
P_WM_Y = 12 + 10 * kP                        # wordmark top (22)
P_PROG_Y = 56 + 16 * kP                      # progress row (72)
P_TOP = 66 + 18 * kP                         # content top (84)
P_CTRL_Y = VH - 38 - 16 * kP                 # control centre line (790)
P_CB = P_CTRL_Y - 30                         # content bottom (760)

# ------------------------------------------------------------------ landscape chrome
U = xmin(VW / 1280, VH / 720)                # 1 at 1280 x 720
CSL = clamp(U, 1, 1.35)                      # chrome scale
ML = clamp(VW * 0.04, 32, 120)               # side margin
L_WM_Y = 24 * CSL
L_PROG_Y = 72 * CSL
L_TOP = 96 * CSL
L_CTRL_Y = VH - 34 - 26 * CSL                # control centre line (cluster bottom right)
L_CB = L_CTRL_Y - 26 * CSL - 22              # bottom of the copy column (above the cluster)
L_ART_B = VH - 22                            # the art side has no controls under it

# ------------------------------------------------------------------ shared
CS_ = by_orient(1, CSL)                      # chrome scale
MX = by_orient(MP, ML)                       # chrome side margin
WM_Y = by_orient(P_WM_Y, L_WM_Y)
PROG_Y = by_orient(P_PROG_Y, L_PROG_Y)
TOP = by_orient(P_TOP, L_TOP)
CTRL_Y = by_orient(P_CTRL_Y, L_CTRL_Y)

# control slots (centre points): a bottom row in tall portrait; a bottom-right cluster under the art in
# short portrait (so the copy column can use the full height) and under the copy column in landscape
PREV_X = sel(MP + 24, VW - MP - 282, VW - ML - 282 * CSL, VW - ML - 282 * CSL)
CONT_X = sel(VW / 2, VW - MP - 88, VW - ML - 88 * CSL, VW - ML - 88 * CSL)
PAUSE_X = sel(VW - MP - 24, VW - MP - 216, VW - ML - 216 * CSL, VW - ML - 216 * CSL)

# tap regions: between the top band and the controls, left third back / right two-thirds next
TAP_TOP = by_orient(P_TOP + 12, L_TOP)
TAP_BOT = by_orient(P_CTRL_Y - 38, L_CTRL_Y - 26 * CSL - 10)

# story vine (design: x 374..386 at the right edge, y 104..752): right-anchored, fills the band
VINE_TOP = by_orient(P_TOP + 20, L_TOP + 8)
VINE_BOT = by_orient(P_CB - 8, VH - 40)
SV = (VINE_BOT - VINE_TOP) / 648


def vine_map(x, y):
    """Screen position of a design point on the story vine."""
    return VW - (390 - x) * SV, VINE_TOP + (y - 104) * SV


# decor scale for edge/corner foliage
SD = by_orient(clamp(xmin(VW / 390, VH / 844), 0.6, 1.6), clamp(VH / 760, 0.85, 1.6))
# hills / paper landscapes: stretched to the full width, bottom anchored
SH = by_orient(clamp(xmin(VH / 844 * 1.1, VW / 390), 0.45, 1.5), clamp(VH / 844, 0.6, 1.5))

# iris / mask cover factor and the 3D transition leaf's scale
K_IRIS = xmax(1, VW / 390, VH / 844)
K_LEAF = clamp(xmax(VW / 390, VH / 844) * 0.62 + 0.38, 1, 4.2)


def corner(name, kids, cx, cy, s=None, id=None, land_dy=0):
    """Keep a design-corner decoration glued to the same viewport corner (cx, cy in {0, 1}).
    land_dy shifts it (design units) in the landscape layout, e.g. to clear the copy column."""
    s = SD if s is None else s
    return place(name, *kids, id=id, x=cx * VW - cx * 390 * s,
                 y=cy * VH - cy * 844 * s + by_orient(0, land_dy) * s, s=s)


def bottom_band(name, kids, id=None):
    """Full-width ground (hills, paper layers): stretched horizontally, bottom anchored."""
    return place(name, *kids, id=id, x=0, y=VH - 844 * SH, sx=VW / 390, sy=SH)


def cover_rect(shape_el, rect_el, extra=1.12):
    """The scene paper: a rectangle covering the viewport even while the scene recedes (0.94)."""
    resp.apply(rect_el, "Paper", rect_w=VW * extra + 40, rect_h=VH * extra + 40)
    resp.apply(shape_el, "Paper", x=VW / 2, y=VH / 2)
    return shape_el


# ------------------------------------------------------------------ metric scene stack + art
STACKS = {}   # scene -> Stack (for numeric audits)


class Stack:
    """Placement of a scene's number block, copy column and hero art in all four arrangements.

    hero: (hx, hy, align) the hero number's anchor point and alignment (design)
    ub:   bottom of the unit line (design)
    col:  (cx, cy, cw, ch, align) copy column origin, width, estimated height, text alignment
    art:  (x0, y0, x1, y1) design box of the hero art
    """

    def __init__(self, k, hero, ub, col, art, art_pw=None, art_l=None, art_lt=None, num_ratio=None,
                 ts_max_l=2.1, l_boost=1.0, pt_bottom=760, extra_h=0, keep_cw=True, l_align=None, art_ay=(1.0, 0.5, 0.55, 0.5), art_smax=(None, 1.25, 2.6, 2.2),
                 pt_art_min=0.42):
        self.k = k
        STACKS[k] = self
        hx, hy, halign = hero
        cx, cy, cw, ch, calign = col
        self.hero, self.col, self.art = hero, col, art
        has_num = hy is not None
        if not has_num:
            hx, hy, ub = cx, cy, cy
        a_num = {"center": 0.5, "left": 0.0, "right": 1.0}[halign]
        a_col = {"center": 0.5, "left": 0.0, "right": 1.0}[calign]
        gap_d = cy - hy                      # number top -> copy top (includes number + unit)
        Cd = cy + ch                         # copy bottom
        ax0, ay0, ax1, ay1 = art

        # ---------------- portrait tall: copy at top (centre map), art bottom-anchored below it
        band = P_CB - P_TOP
        ts = clamp(xmin(VW / 390, band / 676 * 1.12), 0.78, 1.3)
        ns = clamp(xmin(VW / 390, band / 676), 0.72, 1.3) if has_num else ts   # unit text >= 11.5 px
        num_pt = (VW / 2 - 195 * ns, P_TOP - 84 * ns, ns)
        ctop = P_TOP + (hy - 84) * ns + gap_d * ns
        cleft = VW / 2 + (cx - 195) * ts
        copy_pt = (cleft, ctop, ts)
        cw_pt = cw
        chr_ = CH(k)                         # measured copy height (design units, at this column width)
        chm = chr_ + extra_h                 # ... plus a line that follows the column (scene 1's period)
        top_allowed = ctop - (cy - ay0) * ts + xmax(0, chr_ - ch) * ts
        pb = pt_bottom                       # design y that sits on the content bottom (760 = design)
        sa = clamp(xmin(VW / 390, (P_CB - top_allowed) / (pb - ay0)), pt_art_min, 1.6)
        art_pt = (VW / 2 - 195 * sa, P_CB - pb * sa, sa)
        self.s_art_pt = sa

        # ---------------- portrait wide: copy column left, art right
        colL, colR = MP, VW * 0.5 - 8
        avail = VH - 16 - P_TOP               # controls sit under the art, the copy column runs to the bottom
        nr = num_ratio if num_ratio is not None else 0.8
        Hs = gap_d * nr + ch * 1.3            # estimate (sets the column width: no feedback loop)
        tse = clamp(avail / Hs, 0.7, 0.92)
        cw_pw = (colR - colL) / tse
        tsw = clamp(xmin(tse, avail / (gap_d * nr + chm)), 0.66, 0.92)   # then fit the measured copy
        nsw = xmax(tsw * nr, 0.72) if has_num else tsw
        ytop = P_TOP + xmax(0, (avail - (gap_d * nr + chm) * tsw) / 2)
        anc = colL + (colR - colL) * a_num
        num_pw = (anc - hx * nsw, ytop - hy * nsw, nsw)
        copy_pw = (colL, ytop + gap_d * nsw, tsw)
        tw_ = art_pw or (VW * 0.5 + 8, P_TOP, VW - MP - 14, P_CB)
        art_pwp = fit_box(art, tw_, 0.5, art_ay[1], smax=art_smax[1])

        # ---------------- landscape wide: art left, number + copy right
        split = VW * 0.5
        lcolL, lcolR = split + 24 * CSL, VW - ML - 22
        lav = L_CB - L_TOP
        nrl = num_ratio if num_ratio is not None else 1.15
        Hl = gap_d * nrl + ch
        tle = clamp(xmin(1.55 * l_boost * U, lav / Hl), 1.0, ts_max_l)   # estimate: sets the width
        lw = lcolR - lcolL
        cwl = xmin(420, lw / tle)
        Hm = gap_d * nrl + chm
        tsl = clamp(xmin(tle, lav / Hm), 0.9, ts_max_l)                   # fit the measured copy
        nsl = tsl * nrl if has_num else tsl
        la = l_align if l_align is not None else a_col
        lytop = L_TOP + xmax(0, (lav - Hm * tsl) / 2)
        lanc = lcolL + lw * (a_num if l_align is None else la)
        num_lw = (lanc - hx * nsl, lytop - hy * nsl, nsl)
        copy_lw = (lcolL + (lw - cwl * tsl) * la, lytop + gap_d * nsl, tsl)
        lt_ = art_l or (ML, L_TOP + 6, split - 12, L_ART_B)
        art_lwp = fit_box(art, lt_, 0.5, art_ay[2], smax=art_smax[2])

        # ---------------- landscape tall: number | copy in a row on top, art below
        tst = clamp(VW / 640, 1.1, 1.5)
        nst = tst * 1.1 if has_num else tst
        half = VW / 2
        rtop = L_TOP + 12
        NB = ub - hy
        if has_num:
            num_lt = (ML + (half - 12 - ML) * a_num - hx * nst, rtop - hy * nst, nst)
            cL, cR = half + 12, VW - ML - 22
            copy_lt = (cL, rtop, tst)
            cw_lt = (cR - cL) / tst
            rbot = rtop + xmax(NB * nst, chm * tst)
        else:
            num_lt = num_lw
            cL, cR = ML + 24, VW - ML - 46
            cwd = xmin(560, (cR - cL) / tst)
            copy_lt = (cL + ((cR - cL) - cwd * tst) * a_col, rtop, tst)
            cw_lt = cwd
            rbot = rtop + chm * tst
        lt2 = art_lt or (ML, rbot + 20, VW - ML - 22, L_CTRL_Y - 26 * CSL - 18)
        art_ltp = fit_box(art, lt2, 0.5, art_ay[3], smax=art_smax[3])

        self.box_pw, self.box_lw, self.box_lt = tw_, lt_, lt2
        self.num = sel3(num_pt, num_pw, num_lw, num_lt)
        self.copy = sel3(copy_pt, copy_pw, copy_lw, copy_lt)
        self.copy_w = sel(cw_pt, cw_pw, cwl, cw_lt)
        self.art_t = sel3(art_pt, art_pwp, art_lwp, art_ltp)
        self.ts = self.copy[2]
        # where the copy column ends (for a following line such as the intro's period)
        self.copy_bottom = self.copy[1] + chr_ * self.copy[2]
        self.copy_left = self.copy[0]
        self.copy_right = self.copy[0] + self.copy_w * self.copy[2]

    # ---- wrappers
    def num_group(self, *kids):
        x, y, s = self.num
        return place(f"S{self.k} number place", *kids, x=x, y=y, s=s)

    def copy_group(self, col_el):
        """Re-bases the copy column to (0, 0) inside a wrapper and binds its width (it rewraps)."""
        col_el.attrs["x"] = 0.0
        col_el.attrs["y"] = 0.0
        resp.apply(col_el, f"S{self.k} copy", lc_w=self.copy_w)
        # the column's real (reflowed) height flows back into the view model: the layout uses the measured
        # copy, not an estimate, so long or localized text pushes what follows instead of colliding
        col_el.add(B.bind(B.P(f"_ch{self.k}"), 811, direction=True))
        x, y, s = self.copy
        return place(f"S{self.k} copy place", col_el, x=x, y=y, s=s)

    def art_group(self, *kids, id=None):
        x, y, s = self.art_t
        return place(f"S{self.k} art place", *kids, id=id, x=x, y=y, s=s)


def map_pt(t, px, py):
    """Screen position of design point (px, py) under a placement triple (x, y, s)."""
    x, y, s = t
    return x + px * s, y + py * s


def panel(stk, art_el, color, radius=28):
    """Side-by-side arrangements frame the art in a paper panel that clips it (scene 7's arms reach in
    from the panel edges instead of ending mid-screen). Stacked arrangements leave the art unclipped."""
    k = stk.k
    big = (-80, -80, VW + 80, VH + 80)
    boxes = [big, stk.box_pw, stk.box_lw, big]
    x0, y0, x1, y1 = (sel(*[b[i] for b in boxes]) for i in range(4))
    on = sel(0, 1, 1, 0)
    src = B.ID()
    r1 = rect(10, 10, radius, 0.0, 0.0)
    resp.apply(r1, "Panel clip", rect_w=x1 - x0, rect_h=y1 - y0)
    clip_src = resp.apply(E("Shape", r1, name=f"S{k} panel clip", id=src), "Panel clip", x=x0, y=y0)
    r2 = rect(10, 10, radius, 0.0, 0.0)
    resp.apply(r2, "Panel", rect_w=x1 - x0, rect_h=y1 - y0)
    face = resp.apply(E("Shape", r2, B.fill(B.col(color, 0.7)), B.stroke(B.col(B.CREAM_DARK, 0.9), 1.5),
                        name=f"S{k} panel", id=B.ID()), "Panel", x=x0, y=y0, op=on)
    clipped = E("Node", E("ClippingShape", sourceId=src, name="Panel clip"), art_el, name=f"S{k} panel art",
                id=B.ID())
    return E("Node", clip_src, clipped, face, name=f"S{k} art panel", id=B.ID())
