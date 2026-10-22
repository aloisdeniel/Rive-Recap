--!strict
-- Crux responsive layout engine (a module: pure maths, no scene access).
--
-- From the real canvas size it decides the layout and places every scene block
-- (rigdata.luau, generated from tools/rig.py), returning the numbers the stage and
-- the chrome are bound to through the global `CruxRig` view model.
--
--   landscape  = width >= layoutBreakpoint (a pure width rule)
--   portrait   = the phone composition. Tall canvases keep the design's relative
--                positions with one scale ("stack"); short, wide canvases fold the
--                column into side-by-side columns ("fold").
--   landscape  = side-by-side compositions at large-format scales, the wide share card.
--
-- Every value is in screen points here; the director divides by `k` (the stage's
-- viewport node scale, canvas height / 844) before writing.

local scenes = require('rigdata')

export type T = { x: number, y: number, s: number }
export type Chrome = { top: number, bot: number, pad: number, barPad: number, btn: number, pill: number }
export type Result = {
    mode: number, -- 0 portrait stack, 1 portrait fold, 2 landscape
    landscape: boolean,
    wide: number, -- 0 tall arrangement, 1 wide arrangement (the share card, text alignment)
    k: number,
    chrome: Chrome,
    blocks: { [string]: T }, -- key: '<scene>:<block>'
    carrier: { [number]: T }, -- per scene: the space the carrier hold lives in
    px: number, -- GPU canvas pixels per design point for the 3D holds
}

local M = {}

local DESIGN_W = 390
local DESIGN_TOP = 64 -- the design's top bar
local DESIGN_H = 844
local READ_MIN = 0.8 -- copy is never drawn below 0.8 of its design size (14 pt -> 11.2 pt)
local BLOCK_GAP = 14 -- design units between blocks stacked in one column

M.MODE_STACK = 0
M.MODE_FOLD = 1
M.MODE_LANDSCAPE = 2

-- scale bounds per column role: { lo, hi, shrink priority (lower shrinks first) }
local BOUNDS: { [string]: { [string]: { number } } } = {
    fold = {
        hero = { 0.56, 1.0, 3 }, text = { READ_MIN, 1.0, 4 }, copy = { READ_MIN, 1.05, 4 },
        title = { 0.75, 1.0, 4 }, art = { 0.3, 1.0, 1 }, card = { 0.7, 1.0, 2 }, stack = { READ_MIN, 1.0, 4 },
        ledge = { 0.35, 1.0, 1 },
        heroart = { 0.62, 1.0, 2 }, -- art carrying the number's unit label (16-18 pt): >= 10 pt
    },
    landscape = {
        hero = { 0.6, 2.0, 2 }, text = { READ_MIN, 1.8, 4 }, copy = { READ_MIN, 1.6, 4 },
        title = { READ_MIN, 1.8, 4 }, art = { 0.4, 1.8, 1 }, card = { 0.7, 1.4, 3 }, stack = { READ_MIN, 1.5, 4 },
        heroart = { 0.62, 1.8, 2 }, ledge = { 0.4, 1.8, 2 },
    },
}

local function clamp(v: number, lo: number, hi: number): number
    return math.max(lo, math.min(hi, v))
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

function M.chrome(W: number, H: number, landscape: boolean): Chrome
    local tier = if H >= 700 then 1 elseif H >= 420 then 2 else 3
    local tops = { 64, 56, 44 }
    local bots = if landscape then { 96, 80, 64 } else { 104, 84, 64 }
    local pads = { 18, 14, 10 }
    local btns = { 52, 48, 44 } -- never below the 44 pt touch minimum
    local pills = { 56, 50, 44 }
    local barPad = if landscape then clamp(math.floor(W * 0.03), 24, 56) elseif W >= 560 then 28 else 20
    return {
        top = tops[tier], bot = bots[tier], pad = pads[tier], barPad = barPad,
        btn = btns[tier], pill = pills[tier],
    }
end

local function boxOf(b: any, wide: number): { number }
    local t = b.box :: { number }
    local w = b.wbox :: { number }
    return { lerp(t[1], w[1], wide), lerp(t[2], w[2], wide), lerp(t[3], w[3], wide), lerp(t[4], w[4], wide) }
end

-- in a wide-mode column a block also owns the decoration hanging below its box
local function wideBoxOf(b: any, wide: number): { number }
    local bx = boxOf(b, wide)
    bx[4] += (b.tail or 0) * (1 - wide)
    return bx
end

-- ------------------------------------------------------------------ portrait stack
-- The 390 x 844 design mapped with one scale: design y 64 lands under the real top
-- bar, extra width is shared out by each block's horizontal anchor, extra height
-- drops the bottom-anchored art to the floor. Short phones keep copy readable
-- (scale floor) and trim the design's breathing room under the top bar first.
local function stack(sc: any, W: number, H: number, ch: Chrome, out: { [string]: T })
    local sW = W / DESIGN_W
    local sH = (H - ch.top) / (DESIGN_H - DESIGN_TOP)
    local s = math.min(sW, sH)
    if s < READ_MIN then
        s = math.min(sW, READ_MIN)
    end
    local need = (DESIGN_H - DESIGN_TOP) * s
    local cut = 0
    if need > H - ch.top then
        cut = math.min(34, (need - (H - ch.top)) / s)
    end
    local y0 = ch.top - (DESIGN_TOP + cut) * s
    local vs = math.max(0, H - (y0 + DESIGN_H * s))
    local slackX = W - DESIGN_W * s
    for _, b in ipairs(sc.blocks) do
        local bx = slackX * b.ax
        local by = y0 + (if b.v == 'bottom' then vs else 0)
        local bs = s
        local over = (y0 + DESIGN_H * s) - H -- the design runs past the canvas bottom (short phones)
        if over > 0 and b.v == 'bottom' and not b.fit then
            -- shrink the bottom art about its top so it ends where the design ends
            local box = b.box :: { number }
            local top = by + box[2] * s
            local ns = math.max(s * 0.72, s * (1 - over / (box[4] * s)))
            local ax = box[1] + box[3] * b.ax
            bx = bx + ax * s - ax * ns
            by = top - box[2] * ns
            bs = ns
        end
        if b.fit then
            local box = b.box :: { number }
            local limit = H - ch.bot - 6
            local top = by + box[2] * s
            local bottom = top + box[4] * s
            if bottom > limit then
                local ns = math.max(s * 0.72, (limit - top) / box[4])
                -- keep the block's anchor point (left, centre or right edge) where it was
                local ax = box[1] + box[3] * b.ax
                bx = bx + ax * s - ax * ns
                by = top - box[2] * ns
                bs = ns
            end
        end
        out[tostring(sc.k) .. ':' .. b.name] = { x = bx, y = by, s = bs }
    end
end

-- ------------------------------------------------------------------ wide rows
type ColState = { c: any, w: number, h: number, s: number, lo: number, hi: number, prio: number, availH: number,
    boxes: { { number } } }

local function solveAlt(alt: { any }, sc: any, bounds: { [string]: { number } }, area: { number }, H: number,
    wide: number, gapMin: number): ({ ColState }, number, number)
    local cols: { ColState } = {}
    local byName: { [string]: any } = {}
    for _, b in ipairs(sc.blocks) do
        byName[b.name] = b
    end
    local violation = 0
    for _, c in ipairs(alt) do
        local w, h = 0, 0
        local boxes: { { number } } = {}
        for i, name in ipairs(c.blocks) do
            local bx = wideBoxOf(byName[name], wide)
            table.insert(boxes, bx)
            w = math.max(w, bx[3])
            h += bx[4] + (if i > 1 then BLOCK_GAP else 0)
        end
        local bd = bounds[c.role]
        local availH = if c.bleed then H - area[2] - 2 else area[4]
        local s = math.min(bd[2], availH / h)
        local lo = bd[1]
        if s < lo then
            -- too tall even at the readable floor: never overflow the area, count the cost
            violation += (lo - s) * 20
            lo = s
        end
        local prio = bd[3]
        if area[3] / area[4] < 1.3 and prio == 1 then
            prio = 4 -- a tall area: copy and art give up width together
        end
        table.insert(cols, { c = c, w = w, h = h, s = s, lo = lo, hi = bd[2], prio = prio, availH = availH, boxes = boxes })
    end
    local n = #cols
    local function total(): number
        local t = gapMin * (n - 1)
        for _, cs in ipairs(cols) do
            t += cs.w * cs.s
        end
        return t
    end
    local excess = total() - area[3]
    for prio = 1, 5 do
        if excess <= 0 then
            break
        end
        local room = 0
        for _, cs in ipairs(cols) do
            if cs.prio == prio then
                room += (cs.s - cs.lo) * cs.w
            end
        end
        if room > 0 then
            local f = math.min(1, excess / room)
            for _, cs in ipairs(cols) do
                if cs.prio == prio then
                    cs.s -= (cs.s - cs.lo) * f
                end
            end
            excess -= math.min(excess, room)
        end
    end
    if excess > 0.5 then
        -- even the minimum scales do not fit: shrink every column alike rather than
        -- run off the canvas (only the shortest, narrowest canvases get here)
        violation += excess / 50
        local widths = 0
        for _, cs in ipairs(cols) do
            widths += cs.w * cs.s
        end
        local f = math.max(0.5, (area[3] - gapMin * (n - 1)) / widths)
        for _, cs in ipairs(cols) do
            cs.s *= f
        end
    end
    -- coverage: how much of the area the composition uses
    local cover = 0
    for _, cs in ipairs(cols) do
        cover += cs.w * cs.h * cs.s * cs.s
    end
    return cols, violation, cover / (area[3] * area[4])
end

local function placeRow(cols: { ColState }, sc: any, area: { number }, H: number, gapMin: number, gapMax: number,
    out: { [string]: T })
    local n = #cols
    local used = 0
    for _, cs in ipairs(cols) do
        used += cs.w * cs.s
    end
    local gap = gapMin
    if n > 1 then
        gap = clamp((area[3] - used) / (n - 1) * 0.5, gapMin, gapMax)
    end
    local width = used + gap * (n - 1)
    local x = area[1] + math.max(0, (area[3] - width) * 0.5)
    for _, cs in ipairs(cols) do
        local c = cs.c
        local s = cs.s
        local colW = cs.w * s
        local colH = cs.h * s
        local y: number
        if c.v == 'bottom' then
            y = (if c.bleed then H else area[2] + area[4]) - colH
        elseif c.v == 'top' then
            y = area[2]
        else
            y = area[2] + (area[4] - colH) * 0.5
        end
        if not c.bleed then
            y = math.max(area[2], y)
        end
        for i, name in ipairs(c.blocks) do
            local bx = cs.boxes[i]
            local px = x + (colW - bx[3] * s) * c.h
            out[tostring(sc.k) .. ':' .. name] = { x = px - bx[1] * s, y = y - bx[2] * s, s = s }
            y += (bx[4] + BLOCK_GAP) * s
        end
        x += colW + gap
    end
end

local function wideScene(sc: any, W: number, H: number, ch: Chrome, landscape: boolean, wide: number,
    out: { [string]: T })
    local bounds = if landscape then BOUNDS.landscape else BOUNDS.fold
    local mx = if landscape then clamp(W * 0.045, 32, 110) else 20
    local padT = if landscape then 18 else 8
    local padB = if landscape then 10 else 4
    local area = { mx, ch.top + padT, W - 2 * mx, H - ch.top - ch.bot - padT - padB }
    local gapMin = if landscape then 40 else 12
    local gapMax = math.max(gapMin, W * 0.08)
    local wideAspect = area[3] / area[4] >= 1.9
    for _, row in ipairs(sc.rows) do
        local best: { ColState }? = nil
        local bestScore = -math.huge
        for i, alt in ipairs(row) do
            local cols, violation, cover = solveAlt(alt, sc, bounds, area, H, wide, gapMin)
            -- more columns suit very wide areas; otherwise the fullest arrangement wins
            local pref = if wideAspect then #alt * 0.15 else 0
            local score = cover + pref - violation
            if score > bestScore then
                bestScore = score
                best = cols
            end
        end
        if best then
            placeRow(best, sc, area, H, gapMin, gapMax, out)
        end
    end
    -- ground blocks ride the bottom of the canvas at the viewport's proportion
    for _, b in ipairs(sc.blocks) do
        if b.ground then
            local s = H / DESIGN_H
            out[tostring(sc.k) .. ':' .. b.name] = { x = (W - DESIGN_W * s) * 0.5, y = H - DESIGN_H * s, s = s }
        end
    end
end

-- ------------------------------------------------------------------ entry point
function M.compute(W: number, H: number, breakpoint: number, dpr: number): Result
    local bp = if breakpoint == breakpoint and breakpoint > 0 then breakpoint else 768
    local landscape = W >= bp
    local ch = M.chrome(W, H, landscape)
    local mode = M.MODE_LANDSCAPE
    if not landscape then
        local story = H - ch.top - ch.bot
        mode = if story / math.max(1, W) >= 0.9 then M.MODE_STACK else M.MODE_FOLD
    end
    -- the wide arrangement (landscape share card, flush-left columns) suits wide story
    -- areas; a tall landscape canvas (a tablet held upright) keeps the tall card
    local story = (H - ch.top - ch.bot) / math.max(1, W)
    local wide = if mode == M.MODE_FOLD or (mode == M.MODE_LANDSCAPE and story < 0.87) then 1 else 0
    local blocks: { [string]: T } = {}
    for _, sc in ipairs(scenes) do
        if mode == M.MODE_STACK then
            stack(sc, W, H, ch, blocks)
        else
            wideScene(sc, W, H, ch, landscape, wide, blocks)
        end
    end
    return M.finish(blocks, mode, landscape, wide, W, H, ch, dpr)
end

-- Carrier spaces and the GPU pixel scale, from (possibly blended) block transforms.
function M.finish(blocks: { [string]: T }, mode: number, landscape: boolean, wide: number, W: number, H: number,
    ch: Chrome, dpr: number): Result
    local carrier: { [number]: T } = {}
    local maxS = 1
    for _, sc in ipairs(scenes) do
        local t = blocks[tostring(sc.k) .. ':' .. sc.carrier]
        if t then
            local off = sc.carrierWide
            carrier[sc.k] = { x = t.x + off[1] * wide * t.s, y = t.y + off[2] * wide * t.s, s = t.s }
        else
            carrier[sc.k] = { x = 0, y = 0, s = 1 }
        end
    end
    for _, t in pairs(blocks) do
        maxS = math.max(maxS, t.s)
    end
    local px = clamp(math.ceil(dpr * maxS * 2) / 2, 2, 4)
    return {
        mode = mode, landscape = landscape, wide = wide, k = H / DESIGN_H, chrome = ch,
        blocks = blocks, carrier = carrier, px = px,
    }
end

M.scenes = scenes
M.lerp = lerp

return M
