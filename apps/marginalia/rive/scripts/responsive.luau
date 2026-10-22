--!strict
-- Marginalia responsive layout: the one place that decides where things go.
--
-- Pure functions, no state, no Rive objects: the Director (chrome, tap zones,
-- progress) and the Page Stage (pages, ribbon, moon, cover) both call it with
-- the real artboard size, and scripts/responsive_test.luau checks it across a
-- sweep of sizes.
--
-- The rule: the LANDSCAPE layout when the artboard is at least
-- `layoutBreakpoint` wide (UserRecap, default 768), otherwise the PORTRAIT
-- layout. Width only, so a tall 768x1024 is landscape and a short 740x360 is
-- portrait. Each layout then follows the real size continuously.
--
-- Every page is authored once in a 390-unit design space (the original
-- portrait master: a 390x664 stage band). Each page groups its artwork into
-- frames - Copy, Art, Bleed (bands that run edge to edge), Paper - and this
-- module returns one transform per frame:
--
--   portrait  "column"  copy on top, illustration below, anchored to the floor
--             "unit"    scene 3 only, copy and art share one transform while it
--                       fits, so the page-edge ribbon still runs into the numeral
--             "row"     a short portrait stage (wider than it is tall) puts the
--                       illustration beside the copy instead of shrinking it away
--   landscape "row"     a spread: the copy column on one page, the illustration
--                       on the facing page, the bookmark ribbon in the gutter;
--                       scenes 3 and 9 mirror it (illustration on the left)
--             "stagger" the same spread in a tall frame (768x1024): the copy
--                       opens the page at the top, the illustration takes the
--                       lower part on the other side, the ribbon the margin
--   scene 10  the tall card, or a wide card (its spread arrangement) beside or
--             under the headline ("stack") - whichever keeps the card largest
--
-- Text never drops below MIN_TEXT points: every copy frame keeps its smallest
-- font (15 design units) at >= 11, the summary card its unit labels (14.5).

local R = {}

R.BREAKPOINT = 768
R.DW = 390 -- design width of a page
R.DH = 664 -- design height of the stage band
R.CX = 195 -- design centre line
R.MIN_TEXT = 11
R.MIN_COPY = 11 / 15 -- copy frames: the smallest copy font is 15
R.MIN_CARD = 11 / 14.5 -- summary card: the unit labels are 14.5
R.BUTTON = 48 -- previous / pause controls (square)
R.PRIMARY_H = 54 -- continue / share control height

export type Box = { x: number, y: number, w: number, h: number }
export type Xf = { tx: number, ty: number, sx: number, sy: number }

export type Chrome = {
    w: number,
    h: number,
    landscape: boolean,
    t: number, -- 0 compact (short canvas) .. 1 roomy
    headerH: number,
    headerPadT: number,
    progressY: number,
    controlsH: number,
    controlsPadB: number,
    marginX: number,
    top: number, -- safe band for copy and art: below the header ...
    bottom: number, -- ... and above the controls
}

export type Plan = {
    mode: string, -- 'column' | 'unit' | 'row'
    copy: Xf,
    art: Xf,
    bleed: Xf,
    paper: Xf,
    empty: Xf, -- scene 10's zero-user page (a centred unit)
    foot: Xf, -- scene 3's rule + support (with the copy, or under the art)
    wide: Xf, -- scene 10's wide card (hidden unless the spread uses it)
    sky: Xf, -- scene 10's skyline
    copyRect: Box, -- page-space rectangles, for checks
    artRect: Box,
    cardScale: number, -- the scale of whichever summary card is shown
    stacked: boolean, -- scene 10: copy over the wide card
    ribbonX: number, -- the bookmark ribbon: centre x ...
    ribbonS: number, -- ... and scale (its top always sits under the progress rule)
    ribbonEnd: number, -- page-space y of the ribbon's end, for checks
}

export type Spec = {
    copy: Box, -- design-space box of the copy (text) frame
    art: Box, -- design-space box of the illustration; always ends at y = 664
    tuck: number, -- how far the illustration may rise into the copy box's empty foot
    unit: boolean,
    mirror: boolean, -- landscape: illustration on the left
    ground: boolean, -- landscape: keep the illustration on the floor (it has a bleed band)
    floor: number, -- design height of the bleed band the copy must stay above
    ribbon: number, -- the ribbon's design x in the portrait master
    ribbonArt: boolean, -- the ribbon belongs to the illustration (bookmark / card corner)
    ribbonEnd: number, -- design y of the ribbon's end (its pose)
    artRow: Box?, -- the illustration's box in a spread, when it differs
    foot: Box?, -- scene 3: a caption block that can leave the copy column
    wide: Box?, -- scene 10: the wide card's box (its own frame space)
    valign: number, -- portrait: >= 0 places the art in its region (0 top .. 1 bottom)
    bandTop: number, -- design y where the bleed band starts (it ends at 664)
}

local function box(x: number, y: number, w: number, h: number): Box
    return { x = x, y = y, w = w, h = h }
end

local METRIC = box(20, 8, 350, 304)
local METRIC_LEFT = box(30, 8, 330, 304)

local function spec(copy: Box, art: Box, ribbon: number, ribbonEnd: number): Spec
    return {
        copy = copy,
        art = art,
        tuck = 0,
        unit = false,
        mirror = false,
        ground = false,
        floor = 0,
        ribbon = ribbon,
        ribbonArt = false,
        ribbonEnd = ribbonEnd,
        artRow = nil,
        foot = nil,
        wide = nil,
        valign = -1,
        bandTop = 600,
    }
end

local SPECS: { Spec } = {
    spec(box(20, 14, 350, 214), box(0, 240, 390, 424), 382, 300), -- 1 invitation
    spec(METRIC, box(0, 318, 390, 346), 378, 128), -- 2 books
    spec(box(10, 4, 370, 326), box(40, 190, 340, 474), 12, 214), -- 3 pages
    spec(METRIC, box(0, 290, 390, 374), 378, 112), -- 4 hours (moon)
    spec(METRIC, box(0, 290, 390, 374), 378, 226), -- 5 genres (moon spotlight)
    spec(METRIC_LEFT, box(120, 360, 290, 304), 274, 448), -- 6 passages
    spec(box(30, 8, 330, 322), box(40, 336, 360, 328), 378, 168), -- 7 streak
    spec(METRIC, box(0, 318, 390, 346), 12, 300), -- 8 book club
    spec(box(10, 4, 370, 156), box(20, 180, 350, 484), 378, 150), -- 9 persona
    spec(box(20, 6, 350, 106), box(35, 124, 320, 448), 362, 168), -- 10 summary (the tall card)
}
SPECS[1].ground = true
SPECS[2].ground = true
SPECS[2].floor = 60
SPECS[1].bandTop = 500
SPECS[2].bandTop = 604
SPECS[3].unit = true
SPECS[3].mirror = true
SPECS[4].tuck = 28
SPECS[5].tuck = 28
SPECS[6].ribbonArt = true
SPECS[3].foot = box(60, 326, 270, 64)
SPECS[8].artRow = box(-50, 318, 490, 346) -- the satin ribbons run past the page edges
SPECS[9].mirror = true
SPECS[10].ribbonArt = true
SPECS[10].tuck = 8
SPECS[10].valign = 0.15
SPECS[10].wide = box(-362, -112, 730, 226)
R.SPECS = SPECS

local EMPTY = box(30, 140, 330, 350) -- scene 10, zero-user invitation

local function clamp(x: number, a: number, b: number): number
    return math.max(a, math.min(b, x))
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

local function xf(tx: number, ty: number, s: number): Xf
    return { tx = tx, ty = ty, sx = s, sy = s }
end

local HIDE: Xf = { tx = -100000, ty = -100000, sx = 0.001, sy = 0.001 }
R.HIDE = HIDE

local function rectOf(b: Box, t: Xf): Box
    return box(t.tx + b.x * t.sx, t.ty + b.y * t.sy, b.w * t.sx, b.h * t.sy)
end

--- A usable breakpoint: non-finite or non-positive values fall back to 768.
function R.breakpoint(bp: number): number
    if bp ~= bp or bp <= 0 or bp == math.huge then
        return R.BREAKPOINT
    end
    return bp
end

function R.isLandscape(w: number, bp: number): boolean
    return w >= R.breakpoint(bp)
end

--- Chrome metrics for a canvas. Heights compact smoothly on short canvases
--- (360..844 tall) so the stage keeps room; controls stay 48x48 / 54 tall.
function R.chrome(w: number, h: number, bp: number): Chrome
    local land = R.isLandscape(w, bp)
    local t = clamp((h - 400) / (844 - 400), 0, 1)
    local headerH = lerp(44, 76, t)
    local controlsH = lerp(58, 104, t)
    local mx = if land then clamp(w * 0.04, 32, 96) else clamp(w * 0.05, 24, 40)
    return {
        w = w,
        h = h,
        landscape = land,
        t = t,
        headerH = headerH,
        headerPadT = lerp(4, 22, t),
        progressY = headerH - lerp(10, 16, t),
        controlsH = controlsH,
        controlsPadB = lerp(4, 22, t),
        marginX = mx,
        top = headerH,
        bottom = h - controlsH,
    }
end

-- scene 10 on a short or narrow canvas: the headline + support centred on
-- top, the wide card below. Returns the copy and card scales.
local function stackScales(sp: Spec, c: Chrome, y0: number, y1: number): (number, number)
    local wb = sp.wide :: Box
    local cb = sp.copy
    local cw = c.w - 2 * math.min(c.marginX, 16)
    local availH = y1 - y0
    local saMax = if c.landscape then 2.6 else 1.3
    local sc = clamp(math.min(cw / cb.w, if c.landscape then 1.5 else 1.15), R.MIN_COPY, 1.5)
    local sw = math.min(cw / wb.w, (availH - cb.h * sc - 4) / wb.h, saMax)
    if sw < R.MIN_CARD and sc > R.MIN_COPY then
        sc = math.max(R.MIN_COPY, math.min(sc, (availH - 4 - R.MIN_CARD * wb.h) / cb.h))
        sw = math.min(cw / wb.w, (availH - cb.h * sc - 4) / wb.h, saMax)
    end
    return sc, math.max(sw, 0.2)
end

local function applyStack(sp: Spec, c: Chrome, p: Plan, y0: number, y1: number)
    local wb = sp.wide :: Box
    local cb = sp.copy
    local sc, sw = stackScales(sp, c, y0, y1)
    local copyH = cb.h * sc
    local groupH = copyH + 4 + wb.h * sw
    local top = y0 + math.max(0, (y1 - y0 - groupH) * 0.5)
    p.copy = xf(c.w * 0.5 - (cb.x + cb.w * 0.5) * sc, top - cb.y * sc, sc)
    p.foot = p.copy
    p.wide = xf(c.w * 0.5 - (wb.x + wb.w * 0.5) * sw, top + copyH + 4 - wb.y * sw, sw)
    p.art = HIDE
    p.sky = HIDE
    p.stacked = true
end

-- portrait: copy on top, illustration below (or one shared transform)
local function column(sp: Spec, c: Chrome, p: Plan)
    local W = c.w
    local top, bottom = c.top, c.bottom
    local stageH = bottom - top
    if sp.unit then
        local su = math.min(W / R.DW, stageH / R.DH)
        if su >= R.MIN_COPY then
            local t = xf(W * 0.5 - R.CX * su, top, su)
            p.mode = 'unit'
            p.copy = t
            p.art = t
            p.foot = t
            return
        end
    end
    p.mode = 'column'
    local sc = math.min(W / R.DW, 1.3, 0.5 * stageH / sp.copy.h)
    sc = math.max(sc, R.MIN_COPY)
    p.copy = xf(W * 0.5 - R.CX * sc, top, sc)
    p.foot = p.copy
    local copyBottom = top + (math.max(sp.copy.y + sp.copy.h, if sp.foot then sp.foot.y + sp.foot.h else 0)) * sc
    local regionTop = copyBottom + (6 - sp.tuck) * sc
    local a = sp.art
    local sa = (bottom - regionTop) / a.h
    -- stay inside the page (the art is centred on the design centre line)
    local reach = math.max(R.CX - a.x, a.x + a.w - R.CX, 1)
    sa = math.min(sa, (W * 0.5) / reach, math.max(sc, 0.9 * W / R.DW), 2.2)
    sa = math.max(sa, 0.2)
    if sp.valign >= 0 then
        -- placed in the region (the summary card), not stood on the floor
        local slack = (bottom - regionTop) - a.h * sa
        p.art = xf(W * 0.5 - R.CX * sa, regionTop + slack * sp.valign - a.y * sa, sa)
        p.sky = xf(W * 0.5 - R.CX * sa, bottom - R.DH * sa, sa)
        if sp.wide and sa < R.MIN_CARD then
            -- the tall card would shrink its labels below 11 pt: stack the
            -- wide one when it reads larger
            local _, sw = stackScales(sp, c, top + 1, bottom - 1)
            if sw > sa then
                applyStack(sp, c, p, top + 1, bottom - 1)
            end
        end
    else
        p.art = xf(W * 0.5 - R.CX * sa, bottom - (a.y + a.h) * sa, sa)
        p.sky = p.art
    end
end

-- a spread in a tall frame (768x1024, 820x1180): beside each other they would
-- be small, so they stagger - the copy column opens the page at the top
-- (left, or right when mirrored), the illustration takes the lower part on
-- the other side, larger than the column could hold it.
local function stagger(sp: Spec, c: Chrome, p: Plan, y0: number, y1: number)
    p.mode = 'stagger'
    local W = c.w
    local mx = c.marginX
    local cw = W - 2 * mx
    local g = clamp(c.h * 0.03, 24, 48)
    local foot = sp.foot
    local cb = sp.copy
    local cTop, cBot = cb.y, cb.y + cb.h
    if foot then
        cBot = math.max(cBot, foot.y + foot.h)
    end
    local copyHd = cBot - cTop
    local availH = y1 - y0
    local a = sp.art
    local sc = clamp(math.min(cw * 0.62 / cb.w, 1.4, availH * 0.45 / copyHd), 0.9, 1.4)
    local copyH = copyHd * sc
    local regionTop = y0 + copyH + g - sp.tuck * sc
    local sa = math.min(cw * 0.92 / a.w, (y1 - regionTop) / a.h, 2.6)
    sa = math.max(sa, 0.2)
    local artW, artH = a.w * sa, a.h * sa
    -- the pair is centred in the band as a block
    local blockH = (regionTop - y0) + artH
    local shift = math.max(0, (availH - blockH) * 0.5)
    local copyX, artX
    if sp.mirror then
        copyX = W - mx - cb.w * sc
        artX = mx
    else
        copyX = mx
        artX = W - mx - artW
    end
    p.copy = xf(copyX - cb.x * sc, y0 + shift - cTop * sc, sc)
    p.foot = p.copy
    p.art = xf(artX - a.x * sa, regionTop + shift - a.y * sa, sa)
    p.sky = xf(p.art.tx, c.bottom - R.DH * sa, sa) -- the skyline stands on the floor
end

-- a spread: copy column beside the illustration
local function row(sp: Spec, c: Chrome, p: Plan)
    p.mode = 'row'
    local land = c.landscape
    local W = c.w
    local mx = c.marginX
    local padY = if land then clamp((c.h - 400) * 0.05, 2, 32) else 2
    local y0, y1 = c.top + padY, c.bottom - padY
    local availH = y1 - y0
    local cw = W - 2 * mx
    local g = if land then clamp(W * 0.035, 30, 72) else 24
    local ratio = if land then 0.42 else 0.5
    local scMax = if land then 1.75 else 1.15
    local saMax = if land then 2.6 else 1.2
    local cb = sp.copy
    if land and availH > cw * 0.95 then
        stagger(sp, c, p, y0, y1)
        return
    end
    local sc = math.min(cw * ratio / cb.w, availH / cb.h, scMax)
    -- a spread keeps its copy at 0.9 or more where the height allows
    sc = math.max(sc, math.min(if land then 0.9 else 0, availH / cb.h), R.MIN_COPY)
    local copyW = cb.w * sc
    local artWAvail = cw - copyW - g
    -- scene 3: the rule + support caption the illustration
    local foot = sp.foot
    local footH = if foot then foot.h * sc + 6 else 0
    -- scene 10: the tall card or the wide one, whichever reads larger
    local a = sp.artRow or sp.art
    local useWide = false
    local wb = sp.wide
    if wb then
        -- the tall card beside the copy, the wide one beside it, or the wide
        -- one under it: whichever keeps the card largest (the tall card wins
        -- a near tie, it is the master)
        local sTall = math.min(artWAvail / a.w, availH / a.h, saMax)
        local sWide = math.min(artWAvail / wb.w, availH / wb.h, saMax)
        local _, sStack = stackScales(sp, c, c.top + 1, c.bottom - 1)
        local best = math.max(sWide, sStack)
        if not (sTall >= R.MIN_CARD and sTall >= best * 0.85) then
            if sStack > sWide then
                applyStack(sp, c, p, c.top + 1, c.bottom - 1)
                return
            end
            useWide = true
            a = wb
        end
    end
    local sa = math.min(artWAvail / a.w, (availH - footH) / a.h, saMax)
    -- the floor band (water, bridge) is part of the art height: copy stays above it
    local floorPx = if sp.floor > 0 then sp.floor * sa + 8 else 0
    if cb.h * sc > availH - floorPx * 2 then
        sc = math.max(R.MIN_COPY, (availH - floorPx) / cb.h)
        copyW = cb.w * sc
    end
    sa = math.max(sa, 0.2)
    local artW = a.w * sa
    if foot then
        artW = math.max(artW, foot.w * sc)
    end
    local groupW = copyW + g + artW
    local x0 = mx + math.max(0, (cw - groupW) * 0.5)
    local copyX, artX
    if land and sp.mirror then
        artX = x0
        copyX = x0 + artW + g
    else
        copyX = x0
        artX = x0 + copyW + g
    end
    local artH = a.h * sa
    local blockH = artH + footH
    -- a grounded illustration (it has a band) stands on the floor while it
    -- nearly fills the height; in a tall frame it is centred and its band
    -- stretches down to the floor (see plan())
    local slack = availH - blockH
    local vb = if sp.ground and slack < availH * 0.2 then 1 else 0.5
    local artTop = y0 + slack * vb
    local axf = xf(artX + (artW - a.w * sa) * 0.5 - a.x * sa, artTop - a.y * sa, sa)
    if useWide then
        p.wide = axf
        p.art = HIDE
        p.sky = HIDE
    else
        p.art = axf
        p.sky = if sp.wide then xf(axf.tx, c.bottom - R.DH * sa, sa) else axf
    end
    local copyH = cb.h * sc
    local copyTop = artTop + blockH * 0.5 - copyH * 0.5
    if sp.floor > 0 then
        -- above the band, wherever the band starts
        floorPx = y1 - (artTop + (sp.bandTop - a.y) * sa) + 8
    end
    copyTop = clamp(copyTop, y0, math.max(y0, y1 - floorPx - copyH))
    p.copy = xf(copyX - cb.x * sc, copyTop - cb.y * sc, sc)
    if foot then
        p.foot = xf(artX + (artW - foot.w * sc) * 0.5 - foot.x * sc, artTop + artH + 6 - foot.y * sc, sc)
    else
        p.foot = p.copy
    end
end

--- The plan for one page (scene 1..10) on a canvas.
function R.plan(scene: number, c: Chrome): Plan
    local sp = SPECS[math.clamp(scene, 1, 10)]
    local W, H = c.w, c.h
    local ident = xf(0, 0, 1)
    local p: Plan = {
        mode = 'column',
        copy = ident,
        art = ident,
        foot = ident,
        wide = HIDE,
        sky = ident,
        bleed = ident,
        paper = { tx = 0, ty = 0, sx = W / R.DW, sy = H / R.DH },
        empty = ident,
        copyRect = box(0, 0, 0, 0),
        artRect = box(0, 0, 0, 0),
        cardScale = 1,
        stacked = false,
        ribbonX = 0,
        ribbonS = 1,
        ribbonEnd = 0,
    }
    local stageH = c.bottom - c.top
    if c.landscape or W / math.max(stageH, 1) >= 1.25 then
        row(sp, c, p)
    else
        column(sp, c, p)
    end
    local wideShown = p.wide.sx > 0.01
    local artXf = if wideShown then p.wide else p.art
    -- bands run edge to edge: stretched across the page, from the art's
    -- floor line down to the stage floor (taller when the art is centred)
    local bandTopY = artXf.ty + sp.bandTop * artXf.sy
    local bsy = math.max(artXf.sy, (c.bottom - bandTopY) / (R.DH - sp.bandTop))
    p.bleed = { tx = 0, ty = bandTopY - sp.bandTop * bsy, sx = W / R.DW, sy = bsy }
    p.copyRect = rectOf(sp.copy, p.copy)
    if p.stacked then
        p.mode = 'stack'
    end
    local wb = sp.wide
    if wideShown and wb then
        p.artRect = rectOf(wb, p.wide)
    else
        p.artRect = rectOf(if p.mode == 'row' then (sp.artRow or sp.art) else sp.art, p.art)
    end
    p.cardScale = artXf.sx

    -- scene 10 zero-user invitation: a centred unit
    local mx = c.marginX
    local se = math.min((W - 2 * mx) / EMPTY.w, stageH * 0.92 / EMPTY.h, if c.landscape then 1.6 else 1.3)
    se = math.max(se, R.MIN_COPY)
    p.empty = xf(W * 0.5 - R.CX * se, c.top + (stageH - EMPTY.h * se) * 0.5 - EMPTY.y * se, se)

    -- the bookmark ribbon
    local sc = p.copy.sx
    if p.mode == 'stagger' then
        -- down the outer margin, beside the copy column
        local s = clamp(sc * 0.85, 1, 1.3)
        p.ribbonS = s
        if sp.ribbonArt then
            p.ribbonX = p.art.tx + sp.ribbon * p.art.sx
        elseif sp.mirror then
            p.ribbonX = c.marginX * 0.5
        else
            p.ribbonX = W - c.marginX * 0.5
        end
    elseif p.mode == 'row' then
        local s = if c.landscape then clamp(sc * 0.85, 1, 1.5) else sc
        p.ribbonS = s
        if sp.ribbonArt and wideShown then
            p.ribbonX = p.wide.tx + 334 * p.wide.sx -- tucked over the wide card's corner
        elseif sp.ribbonArt then
            p.ribbonX = p.art.tx + sp.ribbon * p.art.sx
        else
            local cr, ar = p.copyRect, p.artRect
            if cr.x < ar.x then
                p.ribbonX = (cr.x + cr.w + ar.x) * 0.5
            else
                p.ribbonX = (ar.x + ar.w + cr.x) * 0.5
            end
        end
    else
        p.ribbonS = sc
        if sp.ribbonArt and wideShown then
            p.ribbonX = p.wide.tx + 334 * p.wide.sx -- tucked over the wide card's corner
        elseif sp.ribbonArt and scene == 10 then
            -- over the card's corner, never across the headline
            -- (378: just past the headline box, which long copy fills)
            p.ribbonX = math.min(W - 9 * sc, math.max(p.art.tx + sp.ribbon * p.art.sx, p.copy.tx + 378 * sc))
        elseif sp.ribbonArt then
            p.ribbonX = p.copy.tx + sp.ribbon * sc -- clear of the copy as authored
        elseif sp.ribbon > R.CX then
            p.ribbonX = W - (R.DW - sp.ribbon) * sc
        else
            p.ribbonX = sp.ribbon * sc
        end
    end
    local top = R.ribbonTop(c, p.ribbonS)
    if sp.ribbonArt and wideShown then
        -- the bookmark ends just inside the wide card's top edge, above the stats
        local target = p.wide.ty + (-112 + 40) * p.wide.sy
        p.ribbonS = clamp((target - top) / (sp.ribbonEnd + 14), 0.6, 2)
    end
    -- the ribbon never hangs into the controls
    local len = sp.ribbonEnd + 14 + 18 -- to the tip of its swallowtail
    if top + len * p.ribbonS > c.bottom - 6 then
        p.ribbonS = math.max(0.45, (c.bottom - 6 - top) / len)
    end
    p.ribbonEnd = top + (sp.ribbonEnd + 14) * p.ribbonS
    return p
end

--- Page-space y of the ribbon frame origin: the ribbon's top (design y -14)
--- tucks under the progress rule, its headband.
function R.ribbonTop(c: Chrome, s: number): number
    return c.progressY + 2
end

function R.ribbonFrameY(c: Chrome, s: number): number
    return c.progressY + 2 + 14 * s
end

--- The closed book the recap opens on: cloth to the edges, a gilt frame 22
--- in, the stamped title block centred.
export type CoverPlan = { cloth: Xf, spine: Xf, title: Xf, w: number, h: number }

function R.cover(c: Chrome): CoverPlan
    local W, H = c.w, c.h
    local s = clamp(math.min(W / R.DW, H / 720), 0.8, 2)
    return {
        cloth = { tx = 0, ty = 0, sx = W / R.DW, sy = H / R.DH },
        spine = { tx = 0, ty = 0, sx = 1, sy = H / R.DH },
        -- the title block's design centre (195, 345) goes to the page centre
        title = xf(W * 0.5 - R.CX * s, H * 0.5 - 345 * s, s),
        w = W,
        h = H,
    }
end

return R
