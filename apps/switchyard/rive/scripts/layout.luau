--!strict
-- Switchyard responsive layout solver (module, required by sequencer.luau).
--
-- The host uses the runtime's layout fit, so the artboard IS the canvas: any
-- width x height. `compute` takes that real size and returns every file-owned
-- layout number the markup binds to (wrapper x/y/scale, band sizes, clip rects,
-- copy widths, GPU canvas resolution), plus a `Frame` the sequencer uses for hit
-- regions and for drawing the progress segments and perforations.
--
-- Rule: width >= layoutBreakpoint (default 768) -> landscape layout, else portrait.
--
--   portrait   phone chrome (header + dock bands). The story stacks: the poster
--              art (with its hero number) on top, the copy anchored above the dock.
--              Art and copy scale independently: copy never below 0.86 (18 pt
--              support -> 15.5 px, 14 pt labels -> 12 px), art shrinks to what is
--              left, never below the size where its unit labels stay >= 12 px. On
--              canvases too short for that (a phone held sideways, 667 x 375) the
--              portrait story flows side by side instead (art | copy).
--   landscape  a ticket: the art panel on the left, a perforated stub on the right
--              carrying the copy column (headline sized from the height), scene-
--              specific arrangements (sea across the full width, the tram under the
--              copy, the persona emblem beside its title, the share card as a wide
--              ticket), controls pinned to the dock's safe margins.
--
-- Everything is in real artboard points; groups are authored in the 390 x 844
-- design and placed by (x, y, s): real = (x, y) + s * design.

local D = require('scripts/layoutdata')

type Box = { x0: number, y0: number, x1: number, y1: number }
export type Out = { [string]: number }
export type Xf = { x: number, y: number, s: number }
export type Frame = {
    vw: number,
    vh: number,
    landscape: boolean,
    row: boolean,
    slim: boolean,
    cs: number,
    top: number,
    bottom: number,
    margin: number,
    divider: number, -- x of the art/copy perforation, -1 when stacked
    short: boolean, -- side-by-side on a very short story (the summary card then spans it)
    progX0: number,
    progX1: number,
    progY: number,
    progH: number,
    hdrPerfY: number,
    dockPerfY: number,
}

local M = {}

local function clamp(v: number, lo: number, hi: number): number
    if v < lo then
        return lo
    end
    if v > hi then
        return hi
    end
    return v
end

local function box(key: string): Box
    local b = D.boxes[key]
    if b == nil then
        return { x0 = 0, y0 = 0, x1 = 390, y1 = 844 }
    end
    return b
end

local function put(o: Out, key: string, x: number, y: number, s: number)
    o['_' .. key .. 'X'] = x
    o['_' .. key .. 'Y'] = y
    o['_' .. key .. 'S'] = s
end

-- place a group so that design point (dx, dy) lands on real (x, y) at scale s
local function anchor(o: Out, key: string, dx: number, dy: number, x: number, y: number, s: number)
    put(o, key, x - dx * s, y - dy * s, s)
end

-- contain box b inside the rect (rx, ry, rw, rh), scale <= smax, aligned ax/ay (0..1)
local function fit(o: Out, key: string, b: Box, rx: number, ry: number, rw: number, rh: number, smax: number,
    ax: number, ay: number): number
    local bw, bh = b.x1 - b.x0, b.y1 - b.y0
    local s = math.max(0.05, math.min(rw / bw, rh / bh, smax))
    anchor(o, key, b.x0, b.y0, rx + (rw - bw * s) * ax, ry + (rh - bh * s) * ay, s)
    return s
end

local function xf(o: Out, key: string): Xf
    return { x = o['_' .. key .. 'X'] or 0, y = o['_' .. key .. 'Y'] or 0, s = o['_' .. key .. 'S'] or 1 }
end

-- ------------------------------------------------------------------ context
type L = {
    vw: number,
    vh: number,
    land: boolean,
    row: boolean,
    top: number,
    bottom: number,
    sh: number,
    m: number,
    uc: number, -- copy scale
    colX: number, -- copy column left edge (row flow), 0 when stacked
    colW: number,
    panelW: number, -- art panel width (row flow), vw when stacked
    copyW: number, -- copy text width in design units
    inset: number, -- copy left edge inside the column (real points)
    short: boolean, -- side-by-side flow on a very short story (< 330 pt)
}

-- the art box in the space it is given; stacked = top-pinned, horizontally centred, never
-- wider than the screen; row = centred in the art panel with a margin
local function artIn(o: Out, l: L, key: string, b: Box, y0: number, y1: number)
    if l.row then
        local pad = math.min(l.m, 40)
        fit(o, key, b, pad, y0 + 6, l.panelW - 2 * pad, (y1 - y0) - 12, 3.2, 0.5, 0.5)
    else
        fit(o, key, b, 0, y0, l.vw, y1 - y0, l.vw / 390, 0.5, 0)
    end
end

-- copy anchored with its design point (24, 740) on (left margin, story bottom)
local function copyBottom(o: Out, l: L, key: string)
    anchor(o, key, 24, 740, l.colX + l.inset, l.bottom, l.uc)
end

-- copy block b vertically centred between y0 and y1 in the column
local function copyCentred(o: Out, l: L, key: string, b: Box, y0: number, y1: number)
    local h = (b.y1 - b.y0) * l.uc
    local y = y0 + math.max(0, ((y1 - y0) - h) * 0.5)
    anchor(o, key, 24, b.y0, l.colX + l.inset, y, l.uc)
end

-- ------------------------------------------------------------------ scenes
local function metric(o: Out, l: L, n: number)
    local a, c = 's' .. n .. 'art', 's' .. n .. 'copy'
    local ab, cb = box(a), box(c)
    if l.row then
        artIn(o, l, a, ab, l.top, l.bottom)
        copyCentred(o, l, c, cb, l.top, l.bottom)
    else
        copyBottom(o, l, c)
        artIn(o, l, a, ab, l.top, l.bottom - (740 - cb.y0) * l.uc)
    end
end

local function scene1(o: Out, l: L)
    local tb, ab, cb = box('s1top'), box('s1art'), box('s1copy')
    if l.row then
        artIn(o, l, 's1art', ab, l.top, l.bottom)
        -- greeting at the head of the stub, lockup + copy at its foot; on a short
        -- story the two blocks close up (and shrink a touch) rather than collide
        local need = (tb.y1 - tb.y0) + 16 + (cb.y1 - cb.y0)
        local s = math.min(l.uc, (l.sh - 20) / need)
        local x = l.colX + l.inset
        anchor(o, 's1top', 24, tb.y0, x, l.top + math.min(18 * s, 10), s)
        local copyY = math.max(l.top + (tb.y1 - tb.y0 + 16) * s + 8, l.bottom - (740 - cb.y0) * s)
        copyY = math.min(copyY, l.bottom - (cb.y1 - cb.y0) * s - 6)
        anchor(o, 's1copy', 24, cb.y0, x, copyY, s)
    else
        anchor(o, 's1top', 24, 82, l.m, l.top, l.uc)
        copyBottom(o, l, 's1copy')
        artIn(o, l, 's1art', ab, l.top + (tb.y1 + 2 - 82) * l.uc, l.bottom - (740 - cb.y0) * l.uc)
    end
end

local function scene2(o: Out, l: L)
    local ab, cb = box('s2art'), box('s2copy')
    local ut = l.uc
    if l.row then
        artIn(o, l, 's2art', ab, l.top, l.bottom)
        -- the tram brakes into the bottom-right corner of the stub, the copy sits above it
        local copyH = (cb.y1 - cb.y0) * l.uc
        ut = clamp((l.sh - copyH - 24) / 230, 0.5, l.uc * 1.15)
        anchor(o, 's2tram', 0, 740, l.colX + l.inset - 24 * ut, l.bottom, ut)
        local tramTop = l.bottom - (740 - 512) * ut
        copyCentred(o, l, 's2copy', cb, l.top, tramTop)
        o._copyW2 = l.copyW
    else
        copyBottom(o, l, 's2copy')
        anchor(o, 's2tram', 0, 740, l.m - 24 * l.uc, l.bottom, l.uc)
        artIn(o, l, 's2art', ab, l.top, l.bottom - (740 - cb.y0) * l.uc)
        o._copyW2 = l.copyW - 114
    end
    local t = xf(o, 's2tram')
    o._tramW = (l.vw - t.x) / t.s + 4
end

local function scene3(o: Out, l: L)
    local ab, cb = box('s3art'), box('s3copy')
    -- the bus keeps to the right margin, the road runs the full width of its space
    anchor(o, 's3lower', 366, 740, l.vw - l.m, l.bottom, l.uc)
    if l.row then
        artIn(o, l, 's3art', ab, l.top, l.bottom)
        copyCentred(o, l, 's3copy', cb, l.top, l.bottom - 70 * l.uc)
    else
        copyBottom(o, l, 's3copy')
        artIn(o, l, 's3art', ab, l.top, l.bottom - (740 - cb.y0) * l.uc)
    end
    o._copyWs = l.copyW - 42
end

local function scene6(o: Out, l: L)
    local ab, cb = box('s6art'), box('s6copy')
    if l.row then
        -- the sea runs under both halves; the sun and the count sit in the art
        -- panel above it, the copy is printed on the deep water in the stub
        -- the waterline sits as high as the copy needs (white type on the deep
        -- bands), at most 44 % down plus the shore; the count may overlap the pale
        -- far shore, never the copy
        local us = clamp(l.uc, 0.6, 2.4)
        local copyH = (cb.y1 - cb.y0) * l.uc + 30 * l.uc
        local water = math.min(l.top + l.sh * 0.44 + 112 * us, l.bottom - copyH)
        o._s6stubO = 0
        if l.short then
            -- the stub turns deep water; the sea drops low in the panel
            o._s6stubO = 1
            us = l.uc * 0.7
            water = l.top + l.sh * 0.66
        end
        -- the count keeps clear of the ferry's mast when there is room for it,
        -- otherwise it may stand in front of the pale far shore
        local artBottom = water - 112 * us
        if artBottom - l.top < 0.6 * (ab.y1 - ab.y0) then
            artBottom = math.max(l.top + l.sh * 0.3, water - 30 * us)
        end
        artIn(o, l, 's6art', ab, l.top, artBottom)
        -- the ferry sails in to the right of the count
        local a = xf(o, 's6art')
        local fx = math.min(math.max(a.x + 300 * a.s, a.x + 250 * a.s + 76 * us), l.panelW - 76 * us)
        anchor(o, 's6sea', 150, 430, fx, water, us)
        copyCentred(o, l, 's6copy', cb, if l.short then l.top else water + 12 * l.uc, l.bottom)
    else
        o._s6stubO = 0
        copyBottom(o, l, 's6copy')
        anchor(o, 's6sea', 24, 740, l.m, l.bottom, l.uc)
        local seaTop = l.bottom - (740 - 318) * l.uc
        artIn(o, l, 's6art', ab, l.top, seaTop)
    end
end

local function scene9(o: Out, l: L)
    local eb, cb = box('s9emblem'), box('s9copy')
    if l.row then
        artIn(o, l, 's9emblem', eb, l.top, l.bottom)
        copyCentred(o, l, 's9copy', cb, l.top, l.bottom)
    else
        copyBottom(o, l, 's9copy')
        artIn(o, l, 's9emblem', eb, l.top, l.bottom - (740 - cb.y0) * l.uc)
    end
    o._copyWt = l.copyW + 4
end

-- share card arrangements: tall / compact / wide (see tools/scenes.py scene10)
local function cardFormat(o: Out, fmt: string)
    local cy = 0
    if fmt == 'compact' then
        cy = -90
    end
    o._clinesO = if fmt == 'compact' then 0 else 1
    o._cdivO = if fmt == 'wide' then 0 else 1
    o._chperfO = if fmt == 'wide' then 0 else 1
    o._cvperfO = if fmt == 'wide' then 1 else 0
    o._cperX, o._cperY = 0, cy
    o._cdiscX, o._cdiscY = 0, if fmt == 'compact' then -16 else 0
    o._cdivpX, o._cdivpY = 0, cy
    o._cstubX, o._cstubY = 0, cy
    o._cinfoX, o._cinfoY = 0, if fmt == 'wide' then -220 else cy
    o._cyrX, o._cyrY = 0, 0
    o._cardNameW = if fmt == 'compact' then 228 else 302
    o._cardW = if fmt == 'wide' then 696 else 342
    o._cardH = if fmt == 'wide' then 300 elseif fmt == 'compact' then 426 else 516
    for i = 0, 4 do
        local r, c = i // 2, i % 2
        if fmt == 'wide' then
            o['_cc' .. i .. 'X'], o['_cc' .. i .. 'Y'] = 374 - 10 * c, -186 + 4 * r
        else
            o['_cc' .. i .. 'X'], o['_cc' .. i .. 'Y'] = 0, cy
        end
    end
end

local function placeCard(o: Out, l: L, rx: number, ry: number, rw: number, rh: number, preferWide: boolean)
    local formats = { 'tall', 'compact', 'wide' }
    local sizes: { [string]: Box } = { tall = box('s10card'), compact = box('cardCompact'), wide = box('cardWide') }
    local best, bestS = 'tall', -1
    for _, f in ipairs(formats) do
        local b = sizes[f]
        local s = math.min(rw / (b.x1 - b.x0), rh / (b.y1 - b.y0), 1.9)
        if f == 'wide' and preferWide then
            s *= 1.15
        end
        -- the tall card is the designed one: keep it while it is comfortably readable
        if f == 'tall' and s >= 0.92 and not preferWide then
            s += 10
        end
        if f == 'wide' and preferWide and s >= 0.9 then
            s += 10
        end
        if s > bestS then
            best, bestS = f, s
        end
    end
    cardFormat(o, best)
    fit(o, 's10card', sizes[best], rx, ry, rw, rh, 1.9, 0.5, 0.5)
end

local function scene10(o: Out, l: L)
    local h2, sb = box('s10head2'), box('s10sup')
    local eb, ea = box('s10ecopy'), box('s10eart')
    if l.row then
        o._shead1O, o._shead2O, o._ssupO = 0, 1, 1
        local pad = math.min(l.m, 40)
        if l.short then
            -- too short for card + headline side by side: the card takes the story
            -- (the share card is the point of this scene), the headline steps aside
            o._shead2O, o._ssupO = 0, 0
            placeCard(o, l, pad, l.top + 6, l.vw - 2 * pad, l.sh - 12, true)
        else
            placeCard(o, l, pad, l.top + 10, l.panelW - 2 * pad, l.sh - 20, true)
        end
        local blockH = (h2.y1 - h2.y0 + 16 + sb.y1 - sb.y0) * l.uc
        local y = l.top + math.max(0, (l.sh - blockH) * 0.5)
        anchor(o, 's10head', 24, h2.y0, l.colX + l.inset, y, l.uc)
        anchor(o, 's10sup', 24, sb.y0, l.colX + l.inset, y + (h2.y1 - h2.y0 + 16) * l.uc, l.uc)
        artIn(o, l, 's10eart', ea, l.top, l.bottom)
        copyCentred(o, l, 's10ecopy', eb, l.top, l.bottom)
    else
        o._shead1O, o._shead2O, o._ssupO = 1, 0, 1
        anchor(o, 's10head', 24, 82, l.m, l.top, l.uc)
        anchor(o, 's10sup', 24, 740, l.m, l.bottom, l.uc)
        local ry0 = l.top + (166 - 82) * l.uc
        local ry1 = l.bottom - (740 - 682) * l.uc
        placeCard(o, l, l.m - 24 * l.uc, ry0, l.vw - 2 * (l.m - 24 * l.uc), ry1 - ry0, false)
        anchor(o, 's10ecopy', 24, 82, l.m, l.top, l.uc)
        local ey = l.top + (eb.y1 + 40 - 82) * l.uc
        local s = math.min(l.vw / 390, l.uc * 1.1)
        anchor(o, 's10eart', 195, ea.y0, l.vw * 0.5, ey, s)
    end
end

-- ------------------------------------------------------------------ entry
function M.compute(vw: number, vh: number, dpr: number, breakpoint: number): (Out, Frame)
    local o: Out = {}
    vw = math.max(1, vw)
    vh = math.max(1, vh)
    local land = vw >= breakpoint
    local slim = vh < 640

    -- chrome: one scale for bands, buttons and their type (buttons stay >= 44 pt)
    local cs = if land then clamp(vh / 844, 0.86, 1.3) else clamp(math.min(vw / 390, vh / 844), 0.86, 1.25)
    local hl = if slim then 50 else 82 -- header height in chrome units
    local dl = if slim then 66 else 104 -- dock height in chrome units
    local top, bottom = hl * cs, vh - dl * cs
    local sh = bottom - top
    local m = if land then clamp(vw * 0.035, 24, 72) else clamp(24 * cs, 16, 40)

    o._vw, o._vh, o._cs = vw, vh, cs
    o._landscape = if land then 1 else 0
    o._hdrBandW, o._hdrBandH = vw / cs, hl
    o._hdrWmX, o._hdrWmY = m / cs + 2, if slim then hl * 0.5 else 32
    o._hdrYrX, o._hdrYrY = (vw - m) / cs, if slim then hl * 0.5 - 10 else 22
    o._dockY = vh - (740 + dl) * cs
    o._dockBandW, o._dockBandH = vw / cs, dl
    o._dockBtnY = dl * 0.5 - 52
    o._dockL = m / cs - 24
    o._dockR = (vw - m) / cs - 366
    o._scx, o._scy = vw * 0.5, (top + bottom) * 0.5

    -- story flow
    local uc = clamp(math.min(vw / 390, sh / 658), 0.86, 1.3)
    local row = land or (sh - 236 * uc) / 418 < 0.55
    local l: L = {
        vw = vw,
        vh = vh,
        land = land,
        row = row,
        top = top,
        bottom = bottom,
        sh = sh,
        m = m,
        uc = uc,
        colX = 0,
        colW = vw,
        panelW = vw,
        copyW = 342,
        inset = m,
        short = false,
    }
    if row then
        local colW = if land then clamp(vw * 0.4, 300, 1000) else clamp(vw * 0.46, 280, 420)
        l.colW = colW
        l.colX = vw - colW
        l.panelW = vw - colW
        local target = if land then clamp(sh / 470, 0.9, 1.9) else 0.86
        l.uc = math.max(0.82, math.min(target, (colW - 2 * m) / 300, sh / 300))
        -- a poster measure: headlines wrap like the portrait ones instead of running
        -- across a wide stub; the block sits a little left of the column's centre
        l.copyW = math.min((colW - 2 * m) / l.uc, 390)
        l.inset = m + math.max(0, (colW - 2 * m) - l.copyW * l.uc) * 0.4
        l.short = sh < 330
        o._artClipW = l.panelW
        o._copyClipX, o._copyClipW = l.colX, colW
    else
        l.copyW = (vw - 2 * m) / uc
        o._artClipW = vw
        o._copyClipX, o._copyClipW = 0, vw
    end
    o._copyW = l.copyW
    o._copyWt = l.copyW + 4
    o._cardTextW = 302

    scene1(o, l)
    scene2(o, l)
    scene3(o, l)
    metric(o, l, 4)
    metric(o, l, 5)
    scene6(o, l)
    metric(o, l, 7)
    metric(o, l, 8)
    scene9(o, l)
    scene10(o, l)

    -- focal points: real P, and the disc scale that makes the full disc cover the
    -- farthest corner of the artboard from P
    local half = D.full * 0.5
    for n = 1, 10 do
        local g = xf(o, D.focus[n])
        local p = D.P[n]
        local px, py = g.x + p[1] * g.s, g.y + p[2] * g.s
        local far = 0
        for _, c in ipairs({ { 0, 0 }, { vw, 0 }, { 0, vh }, { vw, vh } }) do
            far = math.max(far, math.sqrt((c[1] - px) ^ 2 + (c[2] - py) ^ 2))
        end
        o['_s' .. n .. 'PX'] = px
        o['_s' .. n .. 'PY'] = py
        o['_s' .. n .. 'DS'] = math.max(g.s, far * 1.04 / half)
    end

    -- GPU canvases render at device pixels: design units x group scale x device scale
    local k = clamp(dpr, 1, 3)
    o._res1 = clamp(xf(o, 's1art').s * k, 1, 4)
    o._res2 = clamp(xf(o, 's2tram').s * k, 1, 4)
    o._res8 = clamp(xf(o, 's8art').s * k, 1, 4)

    local f: Frame = {
        vw = vw,
        vh = vh,
        landscape = land,
        row = row,
        slim = slim,
        cs = cs,
        top = top,
        bottom = bottom,
        margin = m,
        divider = if row then l.panelW else -1,
        short = l.short,
        progX0 = if slim then m + 158 * cs else m,
        progX1 = if slim then vw - m - 58 * cs else vw - m,
        progY = if slim then (hl * 0.5 - 2) * cs else 62 * cs,
        progH = 4 * cs,
        hdrPerfY = top - 1 * cs,
        dockPerfY = bottom + 1 * cs,
    }
    return o, f
end

-- the motif (route dot + roundel) follows the focus group of the scene it is
-- carrying the story into (forward) or out of (back)
function M.motif(o: Out, n: number)
    local i = math.clamp(math.floor(n + 0.5), 1, 10)
    local g = xf(o, D.focus[i])
    o._mX, o._mY, o._mS = g.x, g.y, g.s
    local ds = o['_s' .. i .. 'DS'] or g.s
    local kk = ds / math.max(0.0001, g.s)
    local p = D.P[i]
    o._rkS = kk
    o._rkX = p[1] * (1 - kk)
    o._rkY = p[2] * (1 - kk)
end

-- real point -> design point of a placed group
function M.toDesign(o: Out, key: string, x: number, y: number): (number, number)
    local g = xf(o, key)
    return (x - g.x) / g.s, (y - g.y) / g.s
end

return M
