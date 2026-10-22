--!strict
-- Nocturne responsive layout.
--
-- A ScriptedLayout in an absolutely positioned box that fills the main
-- artboard, so `resize` receives the real laid-out size (the host uses the
-- runtime's layout fit, which resizes the artboard to the canvas) and the
-- device scale. From those it computes one layout and writes it into
-- UserRecap; the markup is bound to those numbers. Nothing here draws.
--
-- The rule: the LANDSCAPE layout when the artboard width is >= the host's
-- `layoutBreakpoint` (default 768), otherwise the PORTRAIT layout. It is a pure
-- width test, so a tall 768 x 1024 canvas is landscape and a short 667 x 375
-- canvas is portrait. Each layout then adapts continuously to the size:
--
-- * portrait stacks the hero art over the copy and puts the transport in a
--   centred bottom row. When the canvas is too short to stack readable copy
--   under the art (a phone held sideways), the art moves beside the copy and
--   the transport becomes a right-hand rail; the chrome stays compact.
-- * landscape always sets art and copy side by side in a centred composition
--   with a capped width, aligns the copy toward the art (scenes 6 and 7 are
--   mirrored: art on the right), gives the persona its own split and the
--   summary a wide two-panel share card. The transport is a right-hand rail on
--   wide canvases and a bottom row on tall ones.
--
-- Scenes are authored in a 390 x 844 design space. Their hero art lives in an
-- "art frame" (translate + uniform scale of the design art box 0..390 x
-- 100..480), their copy in a "copy frame" (the design copy box 28..362 x
-- 458..752), the summary in a "card frame". The motif, the lodestar and the
-- stage iris follow the current scene's frame (the "hero frame"), which this
-- script eases on a scene change (while the iris is shut) and snaps on resize.
--
-- Test hook: `simAt` (seconds, < 0 off), `simWidth`, `simHeight` let a probe
-- build lay out as if the canvas were resized mid-scene (and `simFromWidth`,
-- `simFromHeight`, when > 0, as if it had another size before that).
-- Production leaves simAt at -1; the CLI cannot resize a headless run.

type L = {
    nums: { [string]: Property<number>? },
    landProp: Property<boolean>?,
    sideProp: Property<boolean>?,
    bp: Property<number>?,
    screen: Property<number>?,
    reduced: Property<boolean>?,
    simAt: Input<number>,
    simWidth: Input<number>,
    simHeight: Input<number>,
    simFromWidth: Input<number>,
    simFromHeight: Input<number>,
    w: number,
    h: number,
    scale: number,
    elapsed: number,
    simDone: boolean,
    dirty: boolean,
    lastBp: number,
    lastScreen: number,
    frames: { [string]: number },
    hero: { number },
    heroFrom: { number },
    heroTo: { number },
    heroT: number,
    hdrAlpha: number,
    hdrTarget: number,
}

-- design constants (keep in step with tools/generate.py)
local ART_CX, ART_CY, ART_TOP, ART_H, ART_W = 195, 290, 100, 380, 390
local COPY_L, COPY_R, COPY_W, COPY_TOP, COPY_H, NUM_H = 28, 362, 334, 458, 294, 116
local OVERLAP = 22 -- the number box's top padding may sit over the art box
local TALL_CARD = { x0 = 28, y0 = 96, w = 334, h = 580 } -- portrait share card + support line
local WIDE_CARD = { x0 = 75, y0 = 88, w = 600, h = 386 } -- landscape share card + support line
local MIRRORED = { [6] = true, [7] = true }
local HERO_DELAY, HERO_DUR = 0.1, 0.36

local NAMES = {
    'layoutWidth', 'layoutHeight', 'layScale', 'laySideT', 'layCardT', 'layChrome',
    'layHdrLX', 'layHdrRX', 'layHdrY', 'layHdrAlpha', 'layProgX', 'layProgY', 'layProgW', 'layProgH',
    'layPrevX', 'layPrevY', 'layPrimX', 'layPrimY', 'laySecX', 'laySecY',
    'layTapTop', 'layTapH', 'layTapPrevW', 'layTapNextX', 'layTapNextW',
    'layArtX', 'layArtXB', 'layArtY', 'layArtS', 'layCopyX', 'layCopyXB', 'layCopyY', 'layCopyS', 'layNumBox',
    'layCardX', 'layCardY', 'layCardS', 'layHeroX', 'layHeroY', 'layHeroS',
    'layArtRes', 'layStageRes', 'layAnnot', 'laySkyX', 'laySkyY', 'laySkyS',
}

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

local function clamp(v: number, lo: number, hi: number): number
    return math.max(lo, math.min(hi, v))
end

local function finite(v: number, fallback: number): number
    if v ~= v or v == math.huge or v == -math.huge then
        return fallback
    end
    return v
end

function init(self: L, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true -- init runs twice; the view model arrives on the second call
    end
    for _, n in NAMES do
        self.nums[n] = vm:getNumber(n)
    end
    self.landProp = vm:getBoolean('isLandscape')
    self.sideProp = vm:getBoolean('isSideBySide')
    self.bp = vm:getNumber('layoutBreakpoint')
    self.screen = vm:getNumber('currentScreen')
    self.reduced = vm:getBoolean('reducedMotion')
    self.dirty = true
    return true
end

function resize(self: L, size: Vector, scale: number)
    self.w = size.x
    self.h = size.y
    self.scale = if scale > 0 then scale else 1
    self.dirty = true
end

local function set(self: L, name: string, v: number)
    local p = self.nums[name]
    if p ~= nil and math.abs(p.value - v) > 1e-4 then
        p.value = v
    end
end

local function heroFor(self: L, screen: number): { number }
    local f = self.frames
    if screen >= 10 then
        return { f.layCardX, f.layCardY, f.layCardS }
    end
    if MIRRORED[screen] then
        return { f.layArtXB, f.layArtY, f.layArtS }
    end
    return { f.layArtX, f.layArtY, f.layArtS }
end

-- The whole layout for a W x H canvas. Returns the frame table, whether the
-- width rule picked landscape, whether art and copy sit side by side, and the
-- header alpha the summary wants (the header steps aside when the share card
-- needs the room).
local function compute(W: number, H: number, ds: number, bp: number, screen: number): ({ [string]: number }, boolean, boolean, number)
    local o: { [string]: number } = {}
    local land = W >= bp
    o.layoutWidth, o.layoutHeight, o.layScale = W, H, ds

    -- chrome scale (never below 1: labels and 44 pt targets keep their size)
    local u = if land then clamp(math.min(W / 1280, H / 720), 1, 1.5) else clamp(math.min(W / 390, H / 844), 1, 1.25)
    -- compactness from the height: 0 roomy .. 1 compact header and transport
    local c = clamp((700 - H / u) / 160, 0, 1)
    local rowY, progY, hdrB = lerp(42, 26, c) * u, lerp(66, 44, c) * u, lerp(84, 56, c) * u

    -- portrait: try the stacked arrangement first
    local side = land
    local m = clamp(W * 28 / 390, 16, 40)
    local by = H - lerp(64, 50, c) * u
    local ctlTop = by - 32 * u
    local sTop = hdrB + lerp(16, 8, c) * u
    local sBottom = ctlTop + 4
    local sAvail = sBottom - sTop
    local copyS, artS, nb = 1, 1, NUM_H
    if not land then
        local capW = clamp((W - 2 * m) / COPY_W, 0.86, 1.3)
        local k = 1.12
        local a0 = sAvail / (ART_H + (COPY_H - OVERLAP) * k)
        copyS = clamp(k * a0, 0.86, capW)
        local function artFor(numBox: number): number
            local hd = COPY_H - (NUM_H - numBox)
            return math.min(W / ART_W, (sAvail - (hd - OVERLAP) * copyS) / ART_H, 1.6)
        end
        artS = artFor(NUM_H)
        if artS < 0.62 then
            nb = clamp(NUM_H - (0.62 - artS) * ART_H / copyS, 84, NUM_H)
            artS = artFor(nb)
        end
        if artS < 0.5 or W / H >= 1.1 then
            side = true
        end
    end

    local hdrAlpha = 1
    local rail = false
    if not side then
        -- ---------------- portrait, stacked: art over copy, transport row
        local hd = COPY_H - (NUM_H - nb)
        local used = ART_H * artS + (hd - OVERLAP) * copyS
        local extra = math.max(0, sAvail - used)
        local artTop = sTop + extra * 0.4
        local copyTop = artTop + ART_H * artS - OVERLAP * copyS + extra * 0.2
        o.layArtS, o.layCopyS, o.layNumBox = artS, copyS, nb
        o.layArtX = W / 2 - ART_CX * artS
        o.layArtXB = o.layArtX
        o.layArtY = artTop - ART_TOP * artS
        o.layCopyX = W / 2 - 195 * copyS
        o.layCopyXB = o.layCopyX
        o.layCopyY = copyTop - COPY_TOP * copyS
        local gap = math.min(125 * u, W / 2 - 44 * u)
        o.layPrevX, o.layPrimX, o.laySecX = W / 2 - gap, W / 2, W / 2 + gap
        o.layPrevY, o.layPrimY, o.laySecY = by, by, by
        o.layTapTop = hdrB + 20 * u
        o.layTapH = ctlTop + 6 - o.layTapTop
        o.layTapPrevW = W / 3
        o.layTapNextX, o.layTapNextW = W / 3, W - W / 3
        -- summary: the tall card; the header steps aside if the card needs the room
        local function tallCard(top: number): number
            return math.min((W - 2 * m) / TALL_CARD.w, (sBottom - top) / TALL_CARD.h, 1.3)
        end
        local cTop = hdrB + 12 * u
        local cs = tallCard(cTop)
        if cs < 0.95 then
            local alt = tallCard(14 * u)
            if alt > cs then
                cs, cTop = alt, 14 * u
                if screen >= 10 then
                    hdrAlpha = 0
                end
            end
        end
        local cExtra = math.max(0, (sBottom - cTop) - TALL_CARD.h * cs)
        o.layCardS = cs
        o.layCardX = W / 2 - 195 * cs
        o.layCardY = cTop + math.max(0, cExtra - 76 * u) * 0.4 - TALL_CARD.y0 * cs
        o.layCardT = 0
    else
        -- ---------------- side by side (landscape, or portrait held sideways)
        rail = W / H >= 1.2
        if land then
            m = clamp(W * 0.03, 24, 72)
        else
            m = clamp(W * 0.025, 12, 24)
        end
        local top = hdrB + lerp(16, 8, c) * u
        local left, right, bottom = 0, 0, 0
        local railCx = 0
        if rail then
            railCx = W - m - 38 * u
            right = railCx - 42 * u - lerp(16, 8, c) * u
            bottom = H - lerp(28, 12, c) * u
        else
            right = W - m
            bottom = ctlTop - lerp(12, 6, c) * u
        end
        left = m
        local cw, chh = right - left, bottom - top
        local maxW = math.max(860 * u, chh * 2.3)
        if cw > maxW then
            local mid = (left + right) / 2
            left, right, cw = mid - maxW / 2, mid + maxW / 2, maxW
        end
        local g = clamp(cw * 0.065, 20, 110)
        local f = if land then 0.46 else 0.55
        local copyColW, artColW = (cw - g) * f, (cw - g) * (1 - f)
        artS = math.min(artColW / ART_W, chh / ART_H, 3.2)
        local capCopy = if land then 2.2 else 1.3
        copyS = math.min(copyColW / COPY_W, chh / COPY_H, capCopy, artS * 1.25)
        copyS = math.max(0.86, copyS)
        nb = NUM_H
        if COPY_H * copyS > chh then
            nb = clamp(NUM_H - (COPY_H * copyS - chh) / copyS, 84, NUM_H)
        end
        local hd = COPY_H - (NUM_H - nb)
        local midY = (top + bottom) / 2
        if chh > cw * 0.9 then
            -- a tall canvas in the side-by-side layout (768 x 1024, 820 x 1180): stagger the two columns on a
            -- diagonal, the art large at the top on its side and the copy below it on the other side, so the
            -- art can use most of the width without the copy ever sitting under it
            local artW = cw * 0.66
            copyS = clamp(math.min(cw * 0.52 / COPY_W, capCopy), 0.86, capCopy)
            nb = NUM_H
            hd = COPY_H
            artS = math.min(artW / ART_W, (chh - (hd - OVERLAP) * copyS) / ART_H, 3.2)
            local total = ART_H * artS + (hd - OVERLAP) * copyS
            local top0 = top + math.max(0, chh - total) * 0.45
            o.layArtY = top0 - ART_TOP * artS
            o.layCopyY = top0 + ART_H * artS - OVERLAP * copyS - COPY_TOP * copyS
            o.layArtX = left + (artW - ART_W * artS) / 2
            o.layCopyX = right - COPY_R * copyS
            o.layArtXB = right - artW + (artW - ART_W * artS) / 2
            o.layCopyXB = left - COPY_L * copyS
        else
            o.layArtY = midY - ART_CY * artS
            o.layCopyY = midY - (COPY_TOP + hd / 2) * copyS
            o.layArtX = left + artColW / 2 - ART_CX * artS
            o.layCopyX = left + artColW + g - COPY_L * copyS
            o.layCopyXB = left + copyColW - COPY_R * copyS
            o.layArtXB = left + copyColW + g + artColW / 2 - ART_CX * artS
        end
        o.layArtS, o.layCopyS, o.layNumBox = artS, copyS, nb
        if rail then
            local my = (top + bottom) / 2
            o.layPrevX, o.layPrimX, o.laySecX = railCx, railCx, railCx
            o.layPrevY, o.layPrimY, o.laySecY = my - 96 * u, my, my + 96 * u
            o.layTapTop = hdrB + 12 * u
            o.layTapH = H - o.layTapTop
            local zone = railCx - 42 * u
            o.layTapPrevW = zone / 3
            o.layTapNextX, o.layTapNextW = zone / 3, zone - zone / 3
        else
            o.layPrevX, o.layPrimX, o.laySecX = W / 2 - 125 * u, W / 2, W / 2 + 125 * u
            o.layPrevY, o.layPrimY, o.laySecY = by, by, by
            o.layTapTop = hdrB + 20 * u
            o.layTapH = ctlTop + 6 - o.layTapTop
            o.layTapPrevW = W / 3
            o.layTapNextX, o.layTapNextW = W / 3, W - W / 3
        end
        -- summary: the wide two-panel card over the whole content width
        -- (the tall card on a tall canvas, where it fills the space far better than the wide one)
        local fullL, fullR = m, (if rail then railCx - 42 * u - lerp(16, 8, c) * u else W - m)
        local tallCanvas = chh > cw * 0.9
        local card = if tallCanvas then TALL_CARD else WIDE_CARD
        local capCard = if tallCanvas then 1.6 else 2.2
        local function fitCard(t: number): number
            return math.min((fullR - fullL) / card.w, (bottom - t) / card.h, capCard)
        end
        local cTop = top
        local cs = fitCard(cTop)
        if cs < 0.95 then
            local alt = fitCard(12 * u)
            if alt > cs then
                cs, cTop = alt, 12 * u
                if screen >= 10 then
                    hdrAlpha = 0
                end
            end
        end
        o.layCardS = cs
        o.layCardX = (fullL + fullR) / 2 - (card.x0 + card.w / 2) * cs
        o.layCardY = (cTop + bottom) / 2 - (card.y0 + card.h / 2) * cs
        o.layCardT = if tallCanvas then 0 else 1
    end

    -- chrome
    o.layChrome = u
    o.laySideT = if side then 1 else 0
    o.layHdrLX, o.layHdrRX, o.layHdrY = m, W - m, rowY
    o.layProgX, o.layProgY, o.layProgW, o.layProgH = m, progY, W - 2 * m, 3 * u
    -- densities: art drawables render at art scale x device scale, the stage at
    -- device scale (supersampled on small canvases, where it is cheap)
    o.layArtRes = clamp(o.layArtS * ds, 0.5, 4)
    o.layStageRes = clamp(math.max(ds, math.min(2, 1600 / math.max(W, H))), 0.5, 4)
    -- decorative instrument annotations (9-10 pt in design) fade out before
    -- they would render below 8 pt
    o.layAnnot = clamp((o.layArtS - 0.82) / 0.08, 0, 1)
    -- vector fallback sky: cover the canvas
    local sk = math.max(W / 390, H / 844)
    o.laySkyS, o.laySkyX, o.laySkyY = sk, (W - 390 * sk) / 2, (H - 844 * sk) / 2
    return o, land, side, hdrAlpha
end

local function smooth(t: number): number
    local x = clamp(t, 0, 1)
    return x * x * (3 - 2 * x)
end

function advance(self: L, seconds: number): boolean
    self.elapsed += seconds
    local W, H = self.w, self.h
    if self.simAt >= 0 and self.elapsed >= self.simAt and self.simWidth > 0 and self.simHeight > 0 then
        W, H = self.simWidth, self.simHeight
        if not self.simDone then
            self.simDone = true
            self.dirty = true
        end
    elseif self.simAt >= 0 and self.simFromWidth > 0 and self.simFromHeight > 0 then
        W, H = self.simFromWidth, self.simFromHeight
    end
    if W <= 1 or H <= 1 then
        return true
    end
    local bp = 768
    local bpp = self.bp
    if bpp ~= nil then
        bp = clamp(finite(bpp.value, 768), 1, 100000)
    end
    local screen = 1
    local sp = self.screen
    if sp ~= nil then
        screen = sp.value
    end
    local reduced = false
    local rp = self.reduced
    if rp ~= nil then
        reduced = rp.value
    end
    if bp ~= self.lastBp then
        self.lastBp = bp
        self.dirty = true
    end
    local screenChanged = screen ~= self.lastScreen
    if self.dirty or screenChanged then
        local o, land, side, hdrA = compute(W, H, self.scale, bp, screen)
        self.frames = o
        self.hdrTarget = hdrA
        for k, v in o do
            set(self, k, v)
        end
        local lp, sp2 = self.landProp, self.sideProp
        if lp ~= nil and lp.value ~= land then
            lp.value = land
        end
        if sp2 ~= nil and sp2.value ~= side then
            sp2.value = side
        end
        local target = heroFor(self, screen)
        if screenChanged and self.lastScreen > 0 and not self.dirty and not reduced then
            -- a scene change: glide the hero frame while the stage iris is shut
            self.heroFrom = { self.hero[1], self.hero[2], self.hero[3] }
            self.heroTo = target
            self.heroT = 0
        else
            -- first layout or a resize: snap
            self.hero = target
            self.heroTo = target
            self.heroT = HERO_DELAY + HERO_DUR
        end
        self.lastScreen = screen
        self.dirty = false
    end
    -- hero frame easing
    if self.heroT < HERO_DELAY + HERO_DUR then
        self.heroT += seconds
        local t = smooth((self.heroT - HERO_DELAY) / HERO_DUR)
        local a, b = self.heroFrom, self.heroTo
        self.hero = { lerp(a[1], b[1], t), lerp(a[2], b[2], t), lerp(a[3], b[3], t) }
    end
    set(self, 'layHeroX', self.hero[1])
    set(self, 'layHeroY', self.hero[2])
    set(self, 'layHeroS', self.hero[3])
    -- the header steps aside on the summary only when the card needs the room
    local ha = self.hdrAlpha
    local want = self.hdrTarget
    if ha ~= want then
        if reduced then
            ha = want
        else
            local step = seconds / 0.3
            ha = if ha < want then math.min(want, ha + step) else math.max(want, ha - step)
        end
        self.hdrAlpha = ha
    end
    set(self, 'layHdrAlpha', ha)
    return true
end

function draw(self: L, renderer: Renderer) end

return function(context: Context): Layout<L>
    return {
        nums = {},
        landProp = nil,
        sideProp = nil,
        bp = nil,
        screen = nil,
        reduced = nil,
        simAt = -1,
        simWidth = 0,
        simHeight = 0,
        simFromWidth = 0,
        simFromHeight = 0,
        w = 0,
        h = 0,
        scale = 1,
        elapsed = 0,
        simDone = false,
        dirty = true,
        lastBp = -1,
        lastScreen = -1,
        frames = {},
        hero = { 0, 0, 1 },
        heroFrom = { 0, 0, 1 },
        heroTo = { 0, 0, 1 },
        heroT = 1,
        hdrAlpha = 1,
        hdrTarget = 1,
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
