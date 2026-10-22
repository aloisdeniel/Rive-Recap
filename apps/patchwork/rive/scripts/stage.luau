--!strict
-- Patchwork responsive stage: reads the real artboard size and writes the
-- layout of every scene into private `UserRecap` numbers that the markup is
-- bound to. Nothing is drawn here.
--
-- Orientation is a pure width breakpoint: landscape when the artboard width is
-- >= `layoutBreakpoint` (default 768), portrait otherwise. Each orientation then
-- adapts continuously to the real size:
--
--   portrait   phone chrome (header and progress on top, control bar at the
--              bottom, full width). Copy above and below the hero ("stack");
--              on short canvases (content wider than tall) the copy moves into
--              a column beside the hero ("split").
--   landscape  a spread: header and progress across the top, the hero art in a
--              left panel, a stitched fabric page on the right holding the copy
--              and the controls. Very wide canvases centre the composition and
--              let the grounds bleed.
--
-- The per-scene geometry (design boxes measured on the 390 x 844 master) comes
-- from `layout_spec`, which the generator writes. At 390 x 844 every number this
-- script writes reproduces the master composition exactly.

local spec = require('scripts/layout_spec')

type Stage = {
    vm: ViewModel?,
    nums: { [string]: Property<number> },
    bools: { [string]: Property<boolean> },
    cache: { [string]: number },
    bcache: { [string]: boolean },
    bp: Property<number>?,
    screen: Property<number>?,
    carryP: Property<number>?,
    s10T: Property<number>?,
    size: Vector,
    scale: number,
    key: string,
}

type Box = { x0: number, y0: number, x1: number, y1: number }
type Xf = { x: number, y: number, s: number }

local DW, T0, B0 = 390, 92, 736

local function clamp(v: number, lo: number, hi: number): number
    if v < lo then
        return lo
    elseif v > hi then
        return hi
    end
    return v
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

-- cubic-bezier ease (x1, y1, x2, y2) evaluated at x = t
local function bez(t: number, x1: number, y1: number, x2: number, y2: number): number
    t = clamp(t, 0, 1)
    local u = t
    for _ = 1, 8 do
        local iu = 1 - u
        local x = 3 * iu * iu * u * x1 + 3 * iu * u * u * x2 + u * u * u - t
        local dx = 3 * iu * iu * x1 + 6 * iu * u * (x2 - x1) + 3 * u * u * (1 - x2)
        if math.abs(dx) < 1e-5 then
            break
        end
        u = clamp(u - x / dx, 0, 1)
    end
    local iu = 1 - u
    return 3 * iu * iu * u * y1 + 3 * iu * u * u * y2 + u * u * u
end

local function setN(self: Stage, name: string, v: number)
    local p = self.nums[name]
    if p == nil then
        local vm = self.vm
        if vm == nil then
            return
        end
        local q = vm:getNumber(name)
        if q == nil then
            return
        end
        self.nums[name] = q
        p = q
    end
    v = math.floor(v * 1000 + 0.5) / 1000
    if self.cache[name] ~= v then
        self.cache[name] = v
        p.value = v
    end
end

local function setB(self: Stage, name: string, v: boolean)
    local p = self.bools[name]
    if p == nil then
        local vm = self.vm
        if vm == nil then
            return
        end
        local q = vm:getBoolean(name)
        if q == nil then
            return
        end
        self.bools[name] = q
        p = q
    end
    if self.bcache[name] ~= v then
        self.bcache[name] = v
        p.value = v
    end
end

local function fit(b: Box, rx0: number, ry0: number, rx1: number, ry1: number, smax: number): Xf
    local bw, bh = b.x1 - b.x0, b.y1 - b.y0
    local s = math.min((rx1 - rx0) / bw, (ry1 - ry0) / bh, smax)
    s = math.max(s, 0.2)
    return {
        x = (rx0 + rx1) * 0.5 - s * (b.x0 + b.x1) * 0.5,
        y = (ry0 + ry1) * 0.5 - s * (b.y0 + b.y1) * 0.5,
        s = s,
    }
end

local function boxOf(t: { number }): Box
    return { x0 = t[1], y0 = t[2], x1 = t[3], y1 = t[4] }
end

-- ------------------------------------------------------------------ layout
type Frame = {
    W: number, H: number, land: boolean, split: boolean, band: boolean,
    m: number, T: number, B: number, ctlY: number,
    hdrY: number, progY: number,
    ui: number,                 -- chrome scale (landscape on large canvases)
    f: number,                  -- copy type scale
    -- split geometry
    rx0: number, rx1: number, ry0: number, ry1: number,   -- hero region
    cx0: number, cx1: number, cy0: number, cy1: number,   -- copy column
    px0: number, px1: number, py0: number, py1: number,   -- fabric page panel
    ctlL: number, ctlR: number, ctlM: number,             -- control row anchors
}

local function frameFor(W: number, H: number, land: boolean): Frame
    local k = clamp((H - 360) / (640 - 360), 0, 1)
    -- the chrome grows a little on large landscape canvases
    local ui = if land then clamp(math.min(W / 1280, H / 720), 1, 1.5) else 1
    local hdrY = lerp(26, 38, k) * ui
    local progY = lerp(46, 64, k) * ui
    local T = progY + lerp(14, 28, k) * ui
    local ctlY = H - lerp(46, 72, k) * ui
    local B = ctlY - (26 + lerp(8, 10, k)) * ui
    local fr: Frame = {
        W = W, H = H, land = land, split = land, band = false, m = 24, T = T, B = B, ctlY = ctlY,
        hdrY = hdrY, progY = progY, ui = ui, f = 1,
        rx0 = 0, rx1 = W, ry0 = T, ry1 = B,
        cx0 = 0, cx1 = W, cy0 = T, cy1 = B,
        px0 = 0, px1 = 0, py0 = 0, py1 = 0,
        ctlL = 0, ctlR = 0, ctlM = W * 0.5,
    }
    if land then
        local m = clamp(W * 0.035, 28, 72)
        local Wc = math.min(W - 2 * m, math.max(1100, H * 1.62))
        local x0 = (W - Wc) * 0.5
        local Cw = clamp(Wc * 0.36, 300, 640)
        local gut = clamp(Wc * 0.035, 28, 64)
        fr.m = m
        fr.cx1 = x0 + Wc
        fr.cx0 = fr.cx1 - Cw
        fr.rx0 = x0
        fr.rx1 = fr.cx0 - gut
        fr.ry0 = T
        fr.ry1 = H - math.max(m, 24)
        fr.px0 = fr.cx0 - 26
        fr.px1 = math.min(fr.cx1 + 26, W - 8)
        fr.py0 = T - 6
        fr.py1 = H - clamp(m * 0.5, 14, 28)
        fr.cy0 = T + 18
        fr.cy1 = ctlY - 52 * ui
        fr.ctlL = fr.cx0 + 28 * ui
        fr.ctlR = fr.cx1 - 28 * ui
        fr.ctlM = (fr.cx0 + fr.cx1) * 0.5
        fr.f = clamp(math.min(Cw / 340, H / 600), 0.85, 1.7)
        if (H - T) / W > 1.0 then
            -- a tall landscape canvas (a tablet held upright past the breakpoint):
            -- the hero spans the width on top, the fabric page becomes a band
            -- along the bottom holding the copy and the controls
            fr.band = true
            local bandH = clamp(H * 0.3, 250, 400)
            local by1 = H - clamp(m * 0.5, 14, 28)
            local by0 = by1 - bandH
            fr.px0 = m
            fr.px1 = W - m
            fr.py0 = by0
            fr.py1 = by1
            fr.cx0 = m + 32
            fr.cx1 = W - m - 32
            fr.cy0 = by0 + 26
            fr.cy1 = ctlY - 52 * ui
            fr.rx0 = m
            fr.rx1 = W - m
            fr.ry0 = T
            fr.ry1 = by0 - 24
            fr.ctlM = W * 0.5
            fr.ctlL = fr.ctlM - 150 * ui
            fr.ctlR = fr.ctlM + 150 * ui
            fr.f = clamp((fr.cx1 - fr.cx0) / 420, 0.9, 1.3)
        end
    else
        local m = clamp(W * 24 / DW, 16, 36)
        fr.m = m
        fr.ctlL = m + 20
        fr.ctlR = W - m - 20
        fr.ctlM = W * 0.5
        -- short canvases (content wider than tall) put the copy beside the hero
        fr.split = W / (B - T) > 1.1
        if fr.split then
            local Cw = clamp(W * 0.44, 230, 340)
            fr.cx1 = W - m
            fr.cx0 = fr.cx1 - Cw
            fr.rx0 = m
            fr.rx1 = fr.cx0 - 26
            fr.ry0 = T
            fr.ry1 = B
            fr.px0 = fr.cx0 - 16
            fr.px1 = fr.cx1 + 10
            fr.py0 = T - 4
            fr.py1 = B + 6
            fr.cy0 = T + 6
            fr.cy1 = B - 6
            fr.f = clamp(math.min(Cw / 380, (B - T) / 300), 0.78, 1.1)
        else
            fr.f = clamp(0.8 + (W - 320) / 350, 0.8, 1.2)
        end
    end
    return fr
end

type Slot = { x: number, y: number, s: number, w: number }
type SceneOut = {
    hero: Xf,
    slots: { Slot },
    num: Xf,
    copyOn: number,
}

-- Portrait stack: copy blocks keep their design order and gaps; the hero absorbs
-- the size change by scaling, gaps compress (to 30 %) before the hero shrinks.
local function stackScene(sc: any, fr: Frame): SceneOut
    local f = fr.f
    local hero = boxOf(sc.hero)
    local Eh = hero.y1 - hero.y0
    local blocks = sc.blocks
    local n = #blocks
    local sumH, sumG = 0, 0
    local prevBottom = T0
    local hs: { number } = {}
    local gs: { number } = {}
    for i = 1, n do
        local b = blocks[i]
        local top: number = b[2]
        local h: number = b[3]
        gs[i] = math.max(0, top - prevBottom)
        prevBottom = top + h
        if b[1] == 0 then
            hs[i] = 0
        else
            hs[i] = h * f
            sumH += h * f
        end
        sumG += gs[i]
    end
    gs[n + 1] = math.max(0, B0 - prevBottom)
    sumG += gs[n + 1]
    local A = fr.B - fr.T
    local sW = 1 + (fr.W / DW - 1) * 0.85
    local sH = (A - sumH - 0.3 * sumG) / Eh
    local s = clamp(math.min(sW, sH), 0.45, 1.6)
    local gamma = if sumG > 0 then (A - sumH - Eh * s) / sumG else 1
    local out: SceneOut = { hero = { x = 0, y = 0, s = s }, slots = {}, num = { x = 0, y = 0, s = s }, copyOn = 1 }
    local y = fr.T + gs[1] * gamma
    for i = 1, n do
        local b = blocks[i]
        if b[1] == 0 then
            out.hero.x = fr.W * 0.5 - (DW * 0.5) * s
            out.hero.y = y - hero.y0 * s
            y += Eh * s
        else
            local it = sc.items[b[1]]
            local w: number = it.w
            local lw = math.min(fr.W - (DW - w), w * 1.5 * f) / f
            out.slots[it.slot] = { x = fr.W * 0.5, y = y + (it.ty - it.by0) * f, s = f, w = lw }
            y += hs[i]
        end
        y += gs[i + 1] * gamma
    end
    out.num = { x = out.hero.x, y = out.hero.y, s = s }
    return out
end

-- Split (landscape, or a short portrait canvas): hero fitted into its region,
-- copy stacked in the column and centred vertically.
local function splitScene(sc: any, fr: Frame, heroBox: Box, smax: number): SceneOut
    local out: SceneOut = {
        hero = fit(heroBox, fr.rx0, fr.ry0, fr.rx1, fr.ry1, smax),
        slots = {}, num = { x = 0, y = 0, s = 1 }, copyOn = 1,
    }
    local order = sc.sorder
    if fr.band and #sc.num > 0 then
        -- the band is short: the numeral stays with the hero, as in the stack
        out.hero = fit(boxOf(sc.hero), fr.rx0, fr.ry0, fr.rx1, fr.ry1, smax)
        out.num = { x = out.hero.x, y = out.hero.y, s = out.hero.s }
        local o2: { number } = {}
        for _, idx in order do
            if idx ~= 0 then
                table.insert(o2, idx)
            end
        end
        order = o2
    end
    local f = fr.f
    local Cw = fr.cx1 - fr.cx0
    local function total(ff: number): number
        local t = 0
        for i, idx in order do
            if idx == 0 then
                t += sc.num[4] * ff * 0.9 + sc.num[5] * ff
            else
                local it = sc.items[idx]
                t += (it.h + it.sh) * ff
                if i < #order then
                    t += it.gap * ff
                end
            end
        end
        return t
    end
    local avail = fr.cy1 - fr.cy0
    local tot = total(f)
    if tot > avail then
        f = math.max(0.7, f * avail / tot)
        tot = total(f)
    end
    local y = fr.cy0 + math.max(0, (avail - tot) * 0.5)
    for _, idx in order do
        if idx == 0 then
            local ns = f * 0.9
            out.num = { x = fr.cx0 - sc.num[1] * ns, y = y - sc.num[2] * ns, s = ns }
            y += sc.num[4] * ns + sc.num[5] * f
        else
            local it = sc.items[idx]
            local x = fr.cx0
            if it.box then
                x = fr.cx0 - it.bx0 * f
            end
            out.slots[it.slot] = { x = x, y = y + (it.sty - it.by0) * f, s = f, w = Cw / f }
            y += (it.h + it.sh + it.gap) * f
        end
    end
    return out
end

local function sceneLayout(n: number, fr: Frame): SceneOut
    local sc = spec.scenes[n]
    if fr.split then
        return splitScene(sc, fr, boxOf(sc.shero), if fr.land then 2.2 else 1.4)
    end
    return stackScene(sc, fr)
end

-- ------------------------------------------------------------------ summary card
-- Two arrangements: TALL (portrait card, 336 x 540) and WIDE (a landscape
-- postcard, 780 x 340). The split layouts take whichever fits larger; a short
-- portrait canvas where neither fits legibly beside the copy gives the card the
-- full width and drops the summary copy.
type Card = { out: SceneOut, wide: boolean, full: boolean }

local function cardLayout(fr: Frame): Card
    local sc = spec.scenes[10]
    if not fr.split then
        return { out = stackScene(sc, fr), wide = false, full = false }
    end
    local tall = boxOf(sc.shero)
    local wide = boxOf(spec.wideCard)
    local smax = if fr.land then 2.2 else 1.4
    local a = splitScene(sc, fr, tall, smax)
    local b = splitScene(sc, fr, wide, smax)
    -- landscape prefers the postcard whenever it stays legible
    local pick = b.hero.s >= a.hero.s * 0.92 or (fr.land and not fr.band and b.hero.s >= 0.8)
    local best = if pick then b else a
    local isWide = best == b
    if not fr.land and best.hero.s < 0.8 then
        local full = fit(wide, fr.m, fr.T, fr.W - fr.m, fr.B, 1.4)
        if full.s > best.hero.s then
            local o: SceneOut = { hero = full, slots = best.slots, num = best.num, copyOn = 0 }
            return { out = o, wide = true, full = true }
        end
    end
    return { out = best, wide = isWide, full = false }
end

-- ------------------------------------------------------------------ main
local function relayout(self: Stage)
    local W, H = self.size.x, self.size.y
    if W <= 0 or H <= 0 then
        return
    end
    local bpP = self.bp
    local bp = if bpP ~= nil then bpP.value else 768
    if bp <= 0 then
        bp = 768
    end
    local land = W >= bp
    local fr = frameFor(W, H, land)
    local scP = self.screen
    local cur = if scP ~= nil then math.floor(scP.value + 0.5) else 1
    if cur < 1 or cur > 10 then
        cur = 1
    end

    setB(self, '_landscape', land)
    setB(self, '_split', fr.split)
    setN(self, '_vw', W)
    setN(self, '_vh', H)
    setN(self, '_dpr', self.scale)

    -- chrome
    local ui = fr.ui
    setN(self, '_ui', ui)
    setN(self, '_hdrL', fr.m)
    setN(self, '_hdrLogo', fr.m + 10 * ui)
    setN(self, '_hdrWord', fr.m + 26 * ui)
    setN(self, '_hdrR', W - fr.m)
    setN(self, '_hdrY', fr.hdrY)
    setN(self, '_progX', fr.m)
    setN(self, '_progY', fr.progY)
    setN(self, '_progW', W - 2 * fr.m)
    setN(self, '_ctlY', fr.ctlY)
    setN(self, '_ctlL', fr.ctlL)
    setN(self, '_ctlR', fr.ctlR)
    setN(self, '_ctlM', fr.ctlM)
    -- button widths are in the buttons' own (ui-scaled) units
    local avail = ((fr.ctlR - 36 * ui) - (fr.ctlL + 36 * ui)) / ui
    setN(self, '_contW', clamp(avail, 150, 196))
    local shareW = clamp(avail * 0.51, 84, 118)
    local replayW = clamp(avail - 8 - shareW, 80, 106)
    local pairL = fr.ctlM - (shareW + 8 + replayW) * 0.5 * ui
    setN(self, '_shareW', shareW)
    setN(self, '_replayW', replayW)
    setN(self, '_shareX', pairL + shareW * 0.5 * ui)
    setN(self, '_replayX', pairL + (shareW + 8 + replayW * 0.5) * ui)
    -- tap zones: left third back, right two-thirds next, between the progress
    -- row and the control row
    local navTop = fr.T
    local navBottom = fr.ctlY - 36 * ui
    setN(self, '_navY', navTop)
    setN(self, '_navH', navBottom - navTop)
    setN(self, '_navSplit', W / 3)
    setN(self, '_navRW', W - W / 3)

    -- copy alignment: centred in the stack, ranged left in a column
    setN(self, '_cAlign', if fr.split then 0 else 2)
    setN(self, '_cOrigin', if fr.split then 0 else 0.5)
    setN(self, '_panX', fr.px0)
    setN(self, '_panY', fr.py0)
    setN(self, '_panW', fr.px1 - fr.px0)
    setN(self, '_panH', fr.py1 - fr.py0)

    -- every scene's hero transform (all are live: the 8 -> 9 and 9 -> 10
    -- carries read their neighbour's frame)
    local outs: { SceneOut } = {}
    local card = cardLayout(fr)
    for n = 1, 10 do
        local o = if n == 10 then card.out else sceneLayout(n, fr)
        outs[n] = o
        setN(self, `_h{n}x`, o.hero.x)
        setN(self, `_h{n}y`, o.hero.y)
        setN(self, `_h{n}s`, o.hero.s)
    end

    -- the current scene's copy slots, number group and panel
    local o = outs[cur]
    for k = 1, 4 do
        local sl = o.slots[k]
        if sl ~= nil then
            setN(self, `_c{k}x`, sl.x)
            setN(self, `_c{k}y`, sl.y)
            setN(self, `_c{k}s`, sl.s)
            setN(self, `_c{k}w`, sl.w)
        end
    end
    setN(self, '_nx', o.num.x)
    setN(self, '_ny', o.num.y)
    setN(self, '_ns', o.num.s)
    local panelOn = fr.split and not (cur == 10 and card.full)
    setN(self, '_panelOn', if panelOn then 1 else 0)
    setN(self, '_copyOn', if cur == 10 then o.copyOn else 1)

    -- scene 8 -> 9 carry: the patches leave scene 8's frame and converge on
    -- scene 9's disc wherever the two frames put them
    local h8, h9, h10 = outs[8].hero, outs[9].hero, outs[10].hero
    local cpP = self.carryP
    local cp = if cpP ~= nil then cpP.value else 1
    local e9 = bez(cp, 0.45, 0, 0.3, 1)
    local d9x = (h9.x + h9.s * 195) - (h8.x + h8.s * 195)
    local d9y = (h9.y + h9.s * 500) - (h8.y + h8.s * 500)
    setN(self, '_c9dx', d9x * e9)
    setN(self, '_c9dy', d9y * e9)

    -- scene 9 -> 10: the indigo disc blooms to cover the whole viewport, the
    -- emblem flies from the disc into its slot on the card
    local tP = self.s10T
    local t = if tP ~= nil then tP.value else 1
    local f = t * 52
    local dcx, dcy = h9.x + h9.s * 195, h9.y + h9.s * 500
    local far = 0
    for _, c in { { 0, 0 }, { W, 0 }, { 0, H }, { W, H } } do
        far = math.max(far, math.sqrt((c[1] - dcx) ^ 2 + (c[2] - dcy) ^ 2))
    end
    local eb = bez(f / 22, 0.55, 0, 0.35, 1)
    setN(self, '_bloomX', dcx)
    setN(self, '_bloomY', dcy)
    setN(self, '_bloomS', lerp(h9.s, (far + 6) / 145, eb))

    setB(self, '_cardWide', card.wide)
    local slot = if card.wide then spec.wideSlot else spec.tallSlot
    local sx = h10.x + h10.s * (195 + slot[1])
    local sy = h10.y + h10.s * (418 + slot[2])
    local ss = h10.s * slot[3]
    local ee = bez((f - 12) / 40, 0.65, 0, 0.35, 1)
    setN(self, '_embX', lerp(dcx, sx, ee))
    setN(self, '_embY', lerp(dcy, sy, ee))
    setN(self, '_embS', lerp(h9.s, ss, ee))
    -- the medallion renders at device resolution for its largest on-screen size
    setN(self, '_medRes', clamp(math.max(2, self.scale * math.max(h9.s, 1)), 1, 4))

    -- share card bounds (artboard points), for a host that crops its snapshot
    local cw = if card.wide then 780 else 336
    local ch = if card.wide then 340 else 540
    setN(self, '_cardX', h10.x + h10.s * (195 - cw * 0.5))
    setN(self, '_cardY', h10.y + h10.s * (418 - ch * 0.5))
    setN(self, '_cardW', cw * h10.s)
    setN(self, '_cardH', ch * h10.s)
end

function init(self: Stage, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true
    end
    self.vm = vm
    self.bp = vm:getNumber('layoutBreakpoint')
    self.screen = vm:getNumber('currentScreen')
    self.carryP = vm:getNumber('_carryP')
    self.s10T = vm:getNumber('_s10T')
    self.key = ''
    return true
end

function resize(self: Stage, size: Vector, scale: number)
    self.size = size
    self.scale = if scale > 0 then scale else 1
    self.key = ''
end

function advance(self: Stage, seconds: number): boolean
    if self.vm == nil then
        return true
    end
    local function v(p: Property<number>?): number
        return if p ~= nil then p.value else 0
    end
    local key = string.format('%gx%g@%g|%g|%g|%g|%g', self.size.x, self.size.y, self.scale, v(self.bp),
        v(self.screen), v(self.carryP), v(self.s10T))
    if key ~= self.key then
        self.key = key
        relayout(self)
    end
    return true
end

function draw(self: Stage, renderer: Renderer) end

return function(context: Context): Layout<Stage>
    return {
        vm = nil,
        nums = {},
        bools = {},
        cache = {},
        bcache = {},
        bp = nil,
        screen = nil,
        carryP = nil,
        s10T = nil,
        size = Vector.xy(0, 0),
        scale = 1,
        key = '',
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
