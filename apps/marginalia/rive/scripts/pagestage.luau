--!strict
-- Marginalia page stage: the signature page turn, as a real 3D paper curl,
-- and the responsive placement of every page.
--
-- This ScriptedLayout fills the whole canvas (the header and the controls are
-- drawn above it). It hosts the ten Page artboards and the Carry artboard
-- (bookmark ribbon, moon) as separate instances bound to the one UserRecap
-- instance, and keeps a small model of a book:
--
--   base    the flat page at the bottom of the stack (normally currentScreen)
--   turns   leaves in flight, each easing its progress p toward 1 (turned
--           away past the spine) or 0 (landed flat)
--
-- Responsive layout: a page is the full canvas. Each page's artwork is
-- authored in a 390-unit design space and grouped into frames (Copy Frame,
-- Art Frame, Bleed Front/Back, Paper Frame, Empty Frame); whenever the canvas
-- size or the breakpoint changes, scripts/responsive.luau plans every page
-- for the real size and orientation and this script moves those frames
-- (NodeData). The Carry's Ribbon Frame glides with the scene (to the page
-- margin in portrait, the spread's gutter in landscape) and its Moon Frame
-- follows the illustration of scenes 4-5. The Cover's cloth, gilt frame and
-- stamped title are placed the same way.
--
-- Forward: the page on top curls up from its lower-right corner, rolls over a
-- moving cylinder and leaves past the spine, revealing the next page playing
-- underneath. Back: the earlier page swings back over and lands. Reversing
-- mid-turn simply retargets the leaf, so rapid taps never pop.
--
-- Each leaf is the page's *live* artboard rendered into a canvas every frame
-- (its idle loop keeps playing on the paper), then curled, lit and shadowed on
-- the GPU (shaders/pageturn.wgsl). The pages' own state machines keep a leaving
-- page fully drawn for 1.2 s, longer than any turn.
--
-- The Carry artboard is drawn above the leaves, so the bookmark ribbon stays
-- unbroken across every cut and the moon is carried from scene 4 into 5.
--
-- Reduced motion: no turns; the page that left cross-fades out (the pages'
-- own 200 ms fades). Paused (_motionPaused): nothing advances, leaves freeze.
-- No shader support: the leaf folds flat toward the spine instead.

local Resp = require('scripts/responsive')
local Etch = require('scripts/etch3d')

type Turn = { page: number, p: number, target: number, slot: number, delay: number }

-- one composite of a 3D object onto a leaf (scripts/etch3d.luau, shaders/leafcomp.wgsl)
type Comp = { ubo: GPUBuffer, group: GPUBindGroup?, ov: GPUTextureView?, kv: GPUTextureView? }

type Slot = {
    canvas: Canvas,
    gc: GPUCanvas?,
    colorView: GPUTextureView?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    used: boolean,
    -- the page's 3D objects on the leaf: a half-resolution key render and
    -- up to three composites (lamp + its light, or a book)
    key: Canvas?,
    keyView: GPUTextureView?,
    pageView: GPUTextureView?,
    comps: { Comp },
}

-- the named frames of one hosted page
type Frames = {
    copy: NodeData?,
    art: NodeData?,
    bleedF: NodeData?,
    bleedB: NodeData?,
    paper: NodeData?,
    empty: NodeData?,
    foot: NodeData?,
    wide: NodeData?,
    sky: NodeData?,
}

type CoverFrames = {
    cloth: NodeData?,
    spine: NodeData?,
    title: NodeData?,
    gilt: NodeData?,
    fleurons: { NodeData },
}

type PageStage = {
    page1: Input<Artboard<Data.UserRecap>>,
    page2: Input<Artboard<Data.UserRecap>>,
    page3: Input<Artboard<Data.UserRecap>>,
    page4: Input<Artboard<Data.UserRecap>>,
    page5: Input<Artboard<Data.UserRecap>>,
    page6: Input<Artboard<Data.UserRecap>>,
    page7: Input<Artboard<Data.UserRecap>>,
    page8: Input<Artboard<Data.UserRecap>>,
    page9: Input<Artboard<Data.UserRecap>>,
    page10: Input<Artboard<Data.UserRecap>>,
    carry: Input<Artboard<Data.UserRecap>>,
    cover: Input<Artboard<Data.UserRecap>>,
    pages: { Artboard<Data.UserRecap> },
    frames: { Frames },
    coverInst: Artboard<Data.UserRecap>?,
    coverFrames: CoverFrames?,
    wantCover: boolean,
    ca: Artboard<Data.UserRecap>?,
    ribbonFrame: NodeData?,
    moonFrame: NodeData?,
    ctx: Context?,
    vm: ViewModel?,
    cur: Property<number>?,
    navDir: Property<number>?,
    reduced: Property<boolean>?,
    paused: Property<boolean>?,
    breakpoint: Property<number>?,
    chromeAlpha: Property<number>?,
    devScale: Property<number>?,
    size: Vector,
    scale: number,
    -- the page is the whole canvas: pw x ph layout points
    pw: number,
    ph: number,
    k: number, -- leaf canvas pixels per point (device density, capped)
    -- responsive state
    layoutKey: string,
    chrome: Resp.Chrome?,
    plans: { Resp.Plan },
    ribbon: { x0: number, s0: number, x1: number, s1: number, t: number, dur: number },
    moon: { a: Resp.Xf, b: Resp.Xf, t: number, dur: number, scene: number },
    -- the book: one flat base page, and leaves in flight above it
    lastScreen: number,
    base: number,
    turns: { Turn },
    fadeFrom: number,
    fadeT: number,
    slots: { Slot },
    -- GPU
    gpu: boolean,
    msaaView: GPUTextureView?,
    depthView: GPUTextureView?,
    samples: number,
    layout: GPUBindGroupLayout?,
    pLeaf: GPUPipeline?,
    pShadow: GPUPipeline?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    gx: number,
    gy: number,
    gpuSampler: GPUSampler?,
    pComp: GPUPipeline?,
    compStaging: buffer,
    staging: buffer,
    sampler: ImageSampler,
    shade: Paint,
    shadePath: Path,
}

local MX, MY = 64, 88 -- GPU canvas margin around the page, points
local T_TURN = 0.84 -- seconds; the brief's 450-850 ms handoff
local T_COVER = 1.1 -- the board cover is heavier
local COVER_DELAY = 0.45 -- the closed book is held for a beat first
local T_RIBBON = 0.76 -- the ribbon's pose morph (Carry state machine)
local T_MOON = 0.82 -- the moon's carry 4 -> 5 (Carry state machine)
local CELLS = 6100 -- leaf mesh cells (~61x100 on a phone page), kept square
local MAX_LEAF_PX = 4.2e6 -- leaf texture budget per slot, device pixels
local PI = math.pi

-- ------------------------------------------------------------ easing
local function clamp01(x: number): number
    return math.clamp(x, 0, 1)
end

local function easeInOut(q: number): number
    q = clamp01(q)
    if q < 0.5 then
        return 4 * q * q * q
    end
    local r = -2 * q + 2
    return 1 - r * r * r * 0.5
end

local function easeOut(q: number): number
    local r = 1 - clamp01(q)
    return 1 - r * r * r
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

local function easeSine(q: number): number
    return 0.5 - 0.5 * math.cos(PI * clamp01(q))
end

-- Pose of the turn at progress p (0 = flat, 1 = gone past the spine), in
-- page pixels. Anticipation: the lower-right corner lifts (0-0.10) and eases
-- back a touch (0.10-0.16) before the sweep; the roll radius swells to a soft,
-- page-like bend mid-turn and tightens as the leaf leaves. Back navigation
-- plays the same pose in reverse, so the corner settles last (follow-through).
-- The roll is sized from the page's shorter side, so a wide landscape page
-- turns with the same paper-like bend as a phone page.
-- Returns axis point, unit normal toward the free edge, roll radius.
local function pose(p: number, W: number, H: number, stiff: boolean): (number, number, number, number, number)
    local L = math.min(W, H * 0.62)
    if stiff then
        -- the board cover: barely any curl, swings almost square to the spine
        local phi = lerp(0.16, 0.0, easeSine(p))
        local nx, ny = math.cos(phi), math.sin(phi)
        local R = L * (0.10 + 0.42 * math.sin(PI * clamp01(p)) ^ 0.8)
        local span = W * nx + H * ny
        local cEnd = span + R * 1.15 / nx + L * 0.03
        local c = lerp(0, cEnd, easeSine(p) * 0.92 + easeOut(p) * 0.08)
        return W - nx * c, H - ny * c, nx, ny, R
    end
    -- a wide page tilts its fold less (the corner diagonal is shallower)
    local tilt = math.clamp(0.52 * math.sqrt(math.min(1, (H / W) / 1.7)), 0.3, 0.52)
    local phi = lerp(tilt, 0.06, easeSine(p))
    local nx, ny = math.cos(phi), math.sin(phi)
    local q = clamp01((p - 0.06) / 0.94)
    local R = L * (0.045 + 0.14 * math.sin(PI * q) ^ 1.2 + 0.05 * q)
    local span = W * nx + H * ny
    -- done once the roll itself has cleared the spine (the flipped part lies
    -- beyond it, off the page)
    local cEnd = span + R * 1.15 / nx + L * 0.03
    local c
    if p < 0.10 then
        c = L * 0.075 * easeOut(p / 0.10)
    elseif p < 0.16 then
        c = L * (0.075 - 0.012 * math.sin(PI * 0.5 * (p - 0.10) / 0.06))
    else
        c = lerp(L * 0.063, cEnd, easeSine((p - 0.16) / 0.84))
    end
    -- the leading (lower-right) corner sits c beyond the axis
    return W - nx * c, H - ny * c, nx, ny, R
end

-- ------------------------------------------------------------ GPU setup
-- A grid of near-square cells over the page, rebuilt when its aspect changes.
local function buildMesh(self: PageStage, GX: number, GY: number)
    if GX == self.gx and GY == self.gy and self.vbuf ~= nil then
        return
    end
    self.gx = GX
    self.gy = GY
    local nv = (GX + 1) * (GY + 1)
    local vb = buffer.create(nv * 8)
    local o = 0
    for j = 0, GY do
        for i = 0, GX do
            buffer.writef32(vb, o, i / GX)
            buffer.writef32(vb, o + 4, j / GY)
            o += 8
        end
    end
    self.vbuf = GPUBuffer.new({ size = nv * 8, usage = 'vertex', data = vb, immutable = true, label = 'leaf grid' })
    local n = GX * GY * 6
    local ib = buffer.create(n * 2)
    o = 0
    for j = 0, GY - 1 do
        for i = 0, GX - 1 do
            local a = j * (GX + 1) + i
            local b = a + 1
            local c = a + GX + 1
            local d = c + 1
            for _, v in { a, c, b, b, c, d } do
                buffer.writeu16(ib, o, v)
                o += 2
            end
        end
    end
    self.ibuf = GPUBuffer.new({ size = n * 2, usage = 'index', data = ib, immutable = true, label = 'leaf tris' })
    self.icount = n
end

local function initGpu(self: PageStage, context: Context)
    local sh = context:shader('shaders/pageturn')
    if sh == nil then
        return -- no shaders on this runtime: the 2D fold fallback is used
    end
    local f = context:features()
    self.samples = if f.maxSamples >= 4 then 4 else 1
    local layout = GPUBindGroupLayout.new({ shader = sh, groupIndex = 0, label = 'page' })
    self.layout = layout
    local fmt: ColorFormat = 'rgba8unorm'
    local over: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    self.pShadow = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_shadow' },
        fragment = { module = sh, entryPoint = 'fs_shadow' },
        vertexLayout = {},
        bindGroupLayouts = { layout },
        colorTargets = { { format = fmt, blend = over } },
        depthStencil = { format = 'depth32float', compare = 'always', write = false },
        sampleCount = self.samples,
    })
    self.pLeaf = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_leaf' },
        fragment = { module = sh, entryPoint = 'fs_leaf' },
        vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
        bindGroupLayouts = { layout },
        colorTargets = { { format = fmt, blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = self.samples,
    })
    self.gpuSampler = GPUSampler.new({ min = 'linear', mag = 'linear', mipmap = 'nearest' })
    self.gpu = true
    -- compositing a page's scripted 3D objects onto its leaf (see draw)
    local cs = context:shader('shaders/leafcomp')
    if cs ~= nil then
        self.pComp = GPUPipeline.new({
            vertex = { module = cs, entryPoint = 'vs_main' },
            fragment = { module = cs, entryPoint = 'fs_main' },
            vertexLayout = {},
            colorTargets = { { format = fmt, blend = over } },
        })
    end
end

-- ------------------------------------------------------------ lifecycle
local function findTurn(self: PageStage, page: number): Turn?
    for _, t in self.turns do
        if t.page == page then
            return t
        end
    end
    return nil
end

local function finish(self: PageStage, t: Turn)
    if t.target <= 0 and t.page >= 1 and t.page < self.base then
        self.base = t.page -- landed: it now covers the old base
    end
    local slot = self.slots[t.slot]
    if slot ~= nil then
        slot.used = false
    end
    local i = table.find(self.turns, t)
    if i ~= nil then
        table.remove(self.turns, i)
    end
end

-- every leaf in flight lands where it was going, at once
local function settleTurns(self: PageStage)
    for _, t in table.clone(self.turns) do
        t.p = t.target
        finish(self, t)
    end
end

-- (Re)allocate every surface for the current canvas size and pixel density.
-- Two leaf slots: two pages can be in flight at once (rapid navigation).
local SLOTS = 2

local function allocate(self: PageStage)
    local ctx = self.ctx
    if ctx == nil or self.size.x <= 0 or self.size.y <= 0 then
        return
    end
    -- leaves in flight land where they were going (a resize mid-turn settles
    -- cleanly on the page the reader asked for)
    settleTurns(self)
    self.pw = self.size.x
    self.ph = self.size.y
    -- device resolution, within a per-leaf texture budget on very large canvases
    self.k = math.min(self.scale, math.sqrt(MAX_LEAF_PX / (self.pw * self.ph)))
    local k = self.k
    local w = math.max(1, math.ceil(self.pw * k))
    local h = math.max(1, math.ceil(self.ph * k))
    local gw = math.ceil((self.pw + 2 * MX) * k)
    local gh = math.ceil((self.ph + 2 * MY) * k)
    self.slots = {}
    for i = 1, SLOTS do
        local cv = ctx:canvas({ width = w, height = h })
        local slot: Slot = { canvas = cv, gc = nil, colorView = nil, ubo = nil, group = nil, used = false,
            key = nil, keyView = nil, pageView = nil, comps = {} }
        local layout, smp = self.layout, self.gpuSampler
        if self.gpu and layout ~= nil and smp ~= nil then
            local gc = ctx:gpuCanvas({ width = gw, height = gh })
            local ubo = GPUBuffer.new({ size = 96, usage = 'uniform', label = 'leaf uniforms' })
            slot.gc = gc
            slot.colorView = gc:colorView()
            slot.ubo = ubo
            local pv = cv.image:view()
            slot.pageView = pv
            slot.group = GPUBindGroup.new({
                layout = layout,
                ubos = { { slot = 0, buffer = ubo } },
                textures = { { slot = 1, view = pv } },
                samplers = { { slot = 2, sampler = smp } },
            })
            if self.pComp ~= nil then
                local key = ctx:canvas({ width = math.max(1, math.ceil(w * 0.5)), height = math.max(1, math.ceil(h * 0.5)) })
                slot.key = key
                slot.keyView = key.image:view()
                for c = 1, 3 do
                    slot.comps[c] = { ubo = GPUBuffer.new({ size = 48, usage = 'uniform', label = 'leaf comp' }),
                        group = nil, ov = nil, kv = nil }
                end
            end
        end
        self.slots[i] = slot
    end
    if self.gpu then
        local gx = math.max(8, math.floor(math.sqrt(CELLS * self.pw / self.ph) + 0.5))
        local gy = math.max(8, math.floor(CELLS / gx + 0.5))
        buildMesh(self, gx, gy)
        if self.samples > 1 then
            self.msaaView = GPUTexture.new({ width = gw, height = gh, format = 'rgba8unorm', renderTarget = true,
                sampleCount = self.samples, label = 'leaf msaa' }):view()
        end
        self.depthView = GPUTexture.new({ width = gw, height = gh, format = 'depth32float', renderTarget = true,
            sampleCount = self.samples, label = 'leaf depth' }):view()
    end
end

-- ------------------------------------------------------------ responsive
local function place(n: NodeData?, t: Resp.Xf)
    if n ~= nil then
        n.x = t.tx
        n.y = t.ty
        n.scaleX = t.sx
        n.scaleY = t.sy
    end
end

local function placeAt(n: NodeData?, x: number, y: number)
    if n ~= nil then
        n.x = x
        n.y = y
    end
end

local function framesOf(a: Artboard<Data.UserRecap>): Frames
    return {
        copy = a:node('Copy Frame'),
        art = a:node('Art Frame'),
        bleedF = a:node('Bleed Front'),
        bleedB = a:node('Bleed Back'),
        paper = a:node('Paper Frame'),
        empty = a:node('Empty Frame'),
        foot = a:node('Foot Frame'),
        wide = a:node('Wide Frame'),
        sky = a:node('Sky Frame'),
    }
end

local function currentScene(self: PageStage): number
    local cur = self.cur
    return if cur ~= nil then math.clamp(math.floor(cur.value), 1, 10) else self.lastScreen
end

local function setRibbon(self: PageStage, x: number, y: number, s: number)
    local n = self.ribbonFrame
    if n ~= nil then
        n.x = x
        n.y = y
        n.scaleX = s
        n.scaleY = s
    end
end

-- Plan every page for the real canvas and orientation, and move the frames.
-- Cheap (a few dozen node writes) and only when the size or breakpoint moves.
local function relayout(self: PageStage)
    local w, h = self.size.x, self.size.y
    if w <= 0 or h <= 0 or #self.pages == 0 then
        return
    end
    local bpp = self.breakpoint
    local bp = Resp.breakpoint(if bpp ~= nil then bpp.value else Resp.BREAKPOINT)
    local key = w .. 'x' .. h .. '@' .. bp
    if key == self.layoutKey then
        return
    end
    self.layoutKey = key
    local c = Resp.chrome(w, h, bp)
    self.chrome = c
    for i, pg in self.pages do
        local p = Resp.plan(i, c)
        self.plans[i] = p
        local f = self.frames[i]
        if f ~= nil then
            place(f.copy, p.copy)
            place(f.art, p.art)
            place(f.bleedF, p.bleed)
            place(f.bleedB, p.bleed)
            place(f.paper, p.paper)
            place(f.empty, p.empty)
            place(f.foot, p.foot)
            place(f.wide, p.wide)
            place(f.sky, p.sky)
        end
        pg:advance(0)
    end
    -- the ribbon and the moon snap to the new layout (a resize is not a cut)
    local sc = currentScene(self)
    local p = self.plans[sc]
    if p ~= nil then
        local r = self.ribbon
        r.x0 = p.ribbonX
        r.x1 = p.ribbonX
        r.s0 = p.ribbonS
        r.s1 = p.ribbonS
        r.t = r.dur
        local mp = self.plans[if sc == 5 then 5 else 4]
        if mp ~= nil then
            self.moon.a = mp.art
            self.moon.b = mp.art
            self.moon.t = self.moon.dur
            place(self.moonFrame, mp.art)
        end
        setRibbon(self, p.ribbonX, Resp.ribbonFrameY(c, p.ribbonS), p.ribbonS)
    end
    -- the closed book: cloth to the edges, gilt frame inset, title centred
    local cf = self.coverFrames
    if cf ~= nil then
        local cp = Resp.cover(c)
        place(cf.cloth, cp.cloth)
        place(cf.spine, cp.spine)
        place(cf.title, cp.title)
        placeAt(cf.gilt, w * 0.5, h * 0.5)
        local fl = cf.fleurons
        if #fl == 4 then
            placeAt(fl[1], 22, 22)
            placeAt(fl[2], w - 22, 22)
            placeAt(fl[3], 22, h - 22)
            placeAt(fl[4], w - 22, h - 22)
        end
    end
    local ca = self.ca
    if ca ~= nil then
        ca:advance(0)
    end
end

-- The ribbon glides to the new scene's place with its pose morph; the moon
-- follows the illustration it belongs to.
local function retargetCarry(self: PageStage, scene: number, reduced: boolean)
    local p = self.plans[scene]
    local c = self.chrome
    if p == nil or c == nil then
        return
    end
    local r = self.ribbon
    local k = if r.dur > 0 then easeInOut(r.t / r.dur) else 1
    r.x0 = lerp(r.x0, r.x1, k)
    r.s0 = lerp(r.s0, r.s1, k)
    r.x1 = p.ribbonX
    r.s1 = p.ribbonS
    r.t = if reduced then T_RIBBON else 0
    r.dur = T_RIBBON
    if scene == 4 or scene == 5 then
        local m = self.moon
        if m.scene ~= scene then
            local km = if m.dur > 0 then easeInOut(m.t / m.dur) else 1
            local cur: Resp.Xf = {
                tx = lerp(m.a.tx, m.b.tx, km),
                ty = lerp(m.a.ty, m.b.ty, km),
                sx = lerp(m.a.sx, m.b.sx, km),
                sy = lerp(m.a.sy, m.b.sy, km),
            }
            m.a = cur
            m.b = p.art
            m.t = if reduced or (m.scene ~= 4 and m.scene ~= 5) then T_MOON else 0
            m.dur = T_MOON
            m.scene = scene
        end
    end
end

local function stepCarry(self: PageStage, seconds: number)
    local c = self.chrome
    if c == nil then
        return
    end
    local r = self.ribbon
    r.t = math.min(r.dur, r.t + seconds)
    local k = if r.dur > 0 then easeInOut(r.t / r.dur) else 1
    local s = lerp(r.s0, r.s1, k)
    setRibbon(self, lerp(r.x0, r.x1, k), Resp.ribbonFrameY(c, s), s)
    local m = self.moon
    m.t = math.min(m.dur, m.t + seconds)
    local km = if m.dur > 0 then easeInOut(m.t / m.dur) else 1
    place(self.moonFrame, {
        tx = lerp(m.a.tx, m.b.tx, km),
        ty = lerp(m.a.ty, m.b.ty, km),
        sx = lerp(m.a.sx, m.b.sx, km),
        sy = lerp(m.a.sy, m.b.sy, km),
    })
end

-- ------------------------------------------------------------ navigation
local function startTurn(self: PageStage, page: number, p: number, target: number)
    local free = 0
    for i, slot in self.slots do
        if not slot.used then
            free = i
            break
        end
    end
    if free == 0 then
        -- a third leaf in flight: the oldest one completes at once
        local oldest = self.turns[1]
        free = oldest.slot
        oldest.p = oldest.target
        finish(self, oldest)
    end
    self.slots[free].used = true
    table.insert(self.turns, { page = page, p = p, target = target, slot = free, delay = 0 })
end

-- currentScreen moved from a to b.
local function navigate(self: PageStage, a: number, b: number, dir: number, reduced: boolean)
    if reduced or #self.slots == 0 then
        settleTurns(self)
        self.fadeFrom = self.base
        self.fadeT = 0
        self.base = b
        return
    end
    if dir > 0 then
        -- the page on top turns away (or, if it was still landing, goes back)
        local t = findTurn(self, a)
        if t ~= nil then
            t.target = 1
        elseif a == self.base then
            startTurn(self, a, 0, 1)
        end
        for _, o in self.turns do
            if o.page < b then
                o.target = 1
            end
        end
        if findTurn(self, b) == nil then
            self.base = b
        end
    else
        -- the earlier page swings back over and lands
        local t = findTurn(self, b)
        if t ~= nil then
            t.target = 0
        else
            startTurn(self, b, 1, 0)
        end
    end
end

-- the device density, for the GPU drawables inside the pages (they size their
-- canvases to their box at device resolution)
local function publishScale(self: PageStage)
    local d = self.devScale
    if d ~= nil and d.value ~= self.scale then
        d.value = self.scale
    end
end

function init(self: PageStage, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil or vm == self.vm then
        return true
    end
    -- (re)bind: init can run again with the instance the host finally binds
    -- (e.g. Recap hosted inside another artboard); everything follows it
    self.vm = vm
    self.pages = {}
    self.frames = {}
    self.plans = {}
    self.turns = {}
    for _, slot in self.slots do
        slot.used = false
    end
    self.layoutKey = ''
    self.ctx = context
    for _, input in { self.page1, self.page2, self.page3, self.page4, self.page5, self.page6, self.page7,
        self.page8, self.page9, self.page10 } do
        local a = input:instance(vm)
        table.insert(self.pages, a)
        table.insert(self.frames, framesOf(a))
    end
    local ca = self.carry:instance(vm)
    self.ca = ca
    self.ribbonFrame = ca:node('Ribbon Frame')
    self.moonFrame = ca:node('Moon Frame')
    local cover = self.cover:instance(vm)
    self.coverInst = cover
    local fl: { NodeData } = {}
    for i = 0, 3 do
        local n = cover:node('Fleuron ' .. i)
        if n ~= nil then
            table.insert(fl, n)
        end
    end
    self.coverFrames = {
        cloth = cover:node('Cloth'),
        spine = cover:node('Cover Spine'),
        title = cover:node('Cover Title'),
        gilt = cover:node('Gilt Frame'),
        fleurons = fl,
    }
    self.cur = vm:getNumber('currentScreen')
    self.navDir = vm:getNumber('_navDir')
    self.reduced = vm:getBoolean('reducedMotion')
    self.paused = vm:getBoolean('_motionPaused')
    self.breakpoint = vm:getNumber('layoutBreakpoint')
    self.chromeAlpha = vm:getNumber('_chromeAlpha')
    self.devScale = vm:getNumber('_devScale')
    publishScale(self)
    -- the scripted 3D objects (books, theatre, lamp: scripts/etch3d.luau) draw
    -- themselves when shaders exist; their flat vector versions stay as the
    -- fallback and are folded away here when the 3D can draw
    if context:shader('shaders/etch3d') ~= nil then
        for _, a in self.pages do
            for i = 1, 4 do
                local n = a:node('Flat Fallback ' .. i)
                if n ~= nil then
                    n.scaleX = 0
                    n.scaleY = 0
                end
            end
        end
    end
    local cur = self.cur
    self.lastScreen = if cur ~= nil then math.clamp(math.floor(cur.value), 1, 10) else 1
    self.base = self.lastScreen
    self.moon.scene = self.lastScreen
    initGpu(self, context)
    allocate(self)
    relayout(self)
    -- the recap opens on the closed book: the cover swings open onto page 1
    local rm = self.reduced
    self.wantCover = self.lastScreen == 1 and (rm == nil or not rm.value)
    return true
end

function resize(self: PageStage, size: Vector, scale: number)
    local sc = if scale > 0 then scale else 1
    if size.x == self.size.x and size.y == self.size.y and sc == self.scale and #self.slots > 0 then
        return
    end
    self.size = size
    self.scale = sc
    publishScale(self)
    allocate(self)
    relayout(self)
end

-- the header and the controls fade in as the closed cover swings open
local function updateChromeAlpha(self: PageStage)
    local a = 1
    local t = findTurn(self, 0)
    if t ~= nil then
        a = math.clamp((t.p - 0.12) / 0.45, 0, 1)
    elseif self.wantCover then
        a = 0
    end
    local cp = self.chromeAlpha
    if cp ~= nil and cp.value ~= a then
        cp.value = a
    end
end

function advance(self: PageStage, seconds: number): boolean
    local ca = self.ca
    if ca == nil or #self.pages == 0 then
        return true
    end
    -- the host may retune layoutBreakpoint at any time
    relayout(self)
    local paused = self.paused ~= nil and (self.paused :: Property<boolean>).value
    local reduced = self.reduced ~= nil and (self.reduced :: Property<boolean>).value
    if self.wantCover and #self.slots > 0 then
        self.wantCover = false
        -- the closed book only opens onto page 1 (a host may jump first)
        if not reduced and currentScene(self) == 1 then
            startTurn(self, 0, 0, 1)
            self.turns[#self.turns].delay = COVER_DELAY
        end
    end
    local cs = currentScene(self)
    if cs ~= self.lastScreen then
        local nd = self.navDir
        local dir = if nd ~= nil and nd.value < 0 then -1 else 1
        navigate(self, self.lastScreen, cs, dir, reduced)
        retargetCarry(self, cs, reduced)
        self.lastScreen = cs
    end
    if reduced and #self.turns > 0 then
        navigate(self, cs, cs, 1, true)
    end
    updateChromeAlpha(self)
    if paused then
        return true
    end
    self.fadeT += seconds
    local step = seconds / T_TURN
    for _, t in table.clone(self.turns) do
        local st = if t.page == 0 then seconds / T_COVER else step
        if t.delay > 0 then
            t.delay = math.max(0, t.delay - seconds)
            st = 0
        end
        if t.p < t.target then
            t.p = math.min(t.target, t.p + st)
        else
            t.p = math.max(t.target, t.p - st)
        end
        if t.p == t.target then
            finish(self, t)
        end
    end
    stepCarry(self, seconds)
    for _, pg in self.pages do
        pg:advance(seconds)
    end
    local cover = self.coverInst
    if cover ~= nil and findTurn(self, 0) ~= nil then
        cover:advance(seconds) -- static artwork; only needs laying out while it is on screen
    end
    ca:advance(seconds)
    return true
end

local function drawImagePx(self: PageStage, r: Renderer, img: Image, ox: number, oy: number)
    r:save()
    r:transform(Mat2D.withTranslation(ox, oy) * Mat2D.withScale(1 / self.k, 1 / self.k))
    r:drawImage(img, self.sampler, 'srcOver', 1)
    r:restore()
end

local function renderInto(self: PageStage, cv: Canvas, sc: Artboard<Data.UserRecap>, scale: number?)
    local k = scale or self.k
    local r = cv:beginFrame()
    r:save()
    r:transform(Mat2D.withScale(k, k))
    sc:draw(r)
    r:restore()
    cv:endFrame()
end

local function writeUniforms(self: PageStage, ubo: GPUBuffer, p: number, cover: boolean)
    local k = self.k
    local W, H = self.pw * k, self.ph * k
    local ax, ay, nx, ny, R = pose(p, W, H, cover)
    local b = self.staging
    local vals = {
        W, H, MX * k, MY * k, -- page
        (self.pw + 2 * MX) * k, (self.ph + 2 * MY) * k, math.max(W, H) * 1.75, if cover then 1 else 0, -- view: canvas, camera, endpaper
        ax, ay, nx, ny, -- axis
        R, 1, 0.11, p, -- curl: radius, shadow strength, show-through, progress
        -0.38, -0.52, 0.76, 0.62, -- light dir (upper-left, toward the reader), ambient
        0.968, 0.944, 0.89, 0.035, -- back-of-leaf paper, grain
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
end

local function renderLeaf(self: PageStage, slot: Slot, p: number, cover: boolean)
    local gc, pLeaf, pShadow, ubo, g = slot.gc, self.pLeaf, self.pShadow, slot.ubo, slot.group
    local vbuf, ibuf, depth = self.vbuf, self.ibuf, self.depthView
    if gc == nil or pLeaf == nil or pShadow == nil or ubo == nil or g == nil or vbuf == nil or ibuf == nil
        or depth == nil then
        return
    end
    writeUniforms(self, ubo, p, cover)
    local pass: GPURenderPass
    local msaa = self.msaaView
    if msaa ~= nil then
        pass = gc:beginRenderPass({
            color = { { view = msaa, resolveTarget = slot.colorView, loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'page turn',
        })
    else
        pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'page turn',
        })
    end
    pass:setBindGroup(0, g)
    pass:setPipeline(pShadow)
    pass:draw(6)
    pass:setPipeline(pLeaf)
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:drawIndexed(self.icount)
    pass:finish()
end

-- A page with scripted 3D objects (scripts/etch3d.luau) cannot show them in
-- its 2D leaf canvas (a canvas cannot draw an image the GPU made this frame).
-- So: render the page with the objects drawing nothing, render a key at half
-- resolution (objects = pure magenta where they lie on top), then draw each
-- object's own texture into the leaf canvas through the key on the GPU
-- (shaders/leafcomp.wgsl). Returns false when there is nothing to compose.
local function composeLeaf(self: PageStage, slot: Slot, pg: Artboard<Data.UserRecap>, page: number): boolean
    local pipe, key, kv, pv, gc, smp = self.pComp, slot.key, slot.keyView, slot.pageView, slot.gc, self.gpuSampler
    if pg:node('GPU 1') == nil or pipe == nil or key == nil or kv == nil or pv == nil or gc == nil or smp == nil then
        return false
    end
    -- the page itself; its objects register (and render) as they are drawn
    Etch.leafMode = 1
    renderInto(self, slot.canvas, pg)
    Etch.leafMode = 0
    local reg = Etch.reg[page]
    local any = false
    if reg ~= nil then
        for _, en in reg do
            if en.active then
                any = true
            end
        end
    end
    if reg == nil or not any then
        return true
    end
    Etch.leafMode = 2
    renderInto(self, key, pg, self.k * 0.5)
    Etch.leafMode = 0
    local W, H = slot.canvas.width, slot.canvas.height
    local pass: GPURenderPass? = nil
    local c = 0
    for id = 1, 2 do
        local en = reg[id]
        local node = pg:node('GPU ' .. id)
        if en ~= nil and en.active and node ~= nil then
            local wt = node.worldTransform
            local b = en.e.box
            local k = self.k
            local function at(x: number, y: number): Vector
                return (wt * Vector.xy(b.x + en.ox + x, b.y + en.oy + y)) * k
            end
            local p0, p1, p2, p3 = at(0, 0), at(b.w, 0), at(0, b.h), at(b.w, b.h)
            local views = { en.e.colorView }
            if en.beam then
                table.insert(views, en.e.beamView)
            end
            for _, ov in views do
                c += 1
                local cp = slot.comps[c]
                if cp ~= nil and ov ~= nil then
                    if cp.ov ~= ov or cp.kv ~= kv or cp.group == nil then
                        cp.ov = ov
                        cp.kv = kv
                        cp.group = GPUBindGroup.new({
                            layout = pipe:getBindGroupLayout(0),
                            ubos = { { slot = 0, buffer = cp.ubo } },
                            textures = { { slot = 1, view = ov }, { slot = 2, view = kv } },
                            samplers = { { slot = 3, sampler = smp } },
                        })
                    end
                    local st = self.compStaging
                    local vals = { p0.x, p0.y, p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, W, H, 1, 0 }
                    for i, v in vals do
                        buffer.writef32(st, (i - 1) * 4, v)
                    end
                    cp.ubo:write(st)
                    if pass == nil then
                        pass = gc:beginRenderPass({
                            color = { { view = pv, loadOp = 'load', storeOp = 'store' } },
                            label = 'leaf 3D',
                        })
                    end
                    local ps = pass :: GPURenderPass
                    ps:setPipeline(pipe)
                    ps:setBindGroup(0, cp.group :: GPUBindGroup)
                    ps:draw(6)
                end
            end
        end
    end
    if pass ~= nil then
        pass:finish()
    end
    return true
end

-- 2D fallback (no shader support): the frozen page folds toward the spine.
local function drawFold(self: PageStage, r: Renderer, img: Image, p: number)
    local e = easeInOut(p)
    local sx = math.max(0.001, 1 - e)
    r:save()
    r:transform(Mat2D.withScale(sx, 1))
    drawImagePx(self, r, img, 0, 0)
    r:restore()
    local path = self.shadePath
    path:reset()
    path:moveTo(Vector.xy(0, 0))
    path:lineTo(Vector.xy(self.pw * sx, 0))
    path:lineTo(Vector.xy(self.pw * sx, self.ph))
    path:lineTo(Vector.xy(0, self.ph))
    path:close()
    self.shade.color = Color.rgba(0x25, 0x2E, 0x3D, math.floor(110 * math.sin(PI * p)))
    r:drawPath(path, self.shade)
end

function draw(self: PageStage, renderer: Renderer)
    local ca = self.ca
    if ca == nil or #self.pages == 0 or #self.slots == 0 then
        return
    end
    local base = self.pages[self.base]
    if base ~= nil then
        base:draw(renderer)
    end
    -- reduced motion: the page that left cross-fades out above the new one
    if self.fadeFrom ~= self.base and self.fadeT < 0.4 then
        local old = self.pages[self.fadeFrom]
        if old ~= nil then
            old:draw(renderer)
        end
    end
    -- leaves, deepest first (a lower page number lies on top)
    local order = table.clone(self.turns)
    table.sort(order, function(x: Turn, y: Turn): boolean
        return x.page > y.page
    end)
    local carried = false
    for _, t in order do
        if t.page == 0 and not carried then
            -- the ribbon is page 1's bookmark: it lies under the closed cover
            ca:draw(renderer)
            carried = true
        end
        local slot = self.slots[t.slot]
        local pg = if t.page == 0 then self.coverInst else self.pages[t.page]
        if slot ~= nil and pg ~= nil then
            if not (t.page > 0 and composeLeaf(self, slot, pg, t.page)) then
                renderInto(self, slot.canvas, pg)
            end
            local gc = slot.gc
            if self.gpu and gc ~= nil then
                renderLeaf(self, slot, t.p, t.page == 0)
                drawImagePx(self, renderer, gc.image, -MX, -MY)
            else
                drawFold(self, renderer, slot.canvas.image, t.p)
            end
        end
    end
    if not carried then
        ca:draw(renderer)
    end
end

return function(context: Context): Layout<PageStage>
    return {
        page1 = late(),
        page2 = late(),
        page3 = late(),
        page4 = late(),
        page5 = late(),
        page6 = late(),
        page7 = late(),
        page8 = late(),
        page9 = late(),
        page10 = late(),
        carry = late(),
        cover = late(),
        pages = {},
        frames = {},
        coverInst = nil,
        coverFrames = nil,
        wantCover = false,
        ca = nil,
        ribbonFrame = nil,
        moonFrame = nil,
        ctx = nil,
        vm = nil,
        cur = nil,
        navDir = nil,
        reduced = nil,
        paused = nil,
        breakpoint = nil,
        chromeAlpha = nil,
        devScale = nil,
        size = Vector.xy(0, 0),
        scale = 1,
        pw = 390,
        ph = 844,
        k = 1,
        layoutKey = '',
        chrome = nil,
        plans = {},
        ribbon = { x0 = 0, s0 = 1, x1 = 0, s1 = 1, t = 0, dur = 0 },
        moon = {
            a = { tx = 0, ty = 0, sx = 1, sy = 1 },
            b = { tx = 0, ty = 0, sx = 1, sy = 1 },
            t = 0,
            dur = 0,
            scene = 1,
        },
        lastScreen = 1,
        base = 1,
        turns = {},
        fadeFrom = 1,
        fadeT = 1,
        slots = {},
        gpu = false,
        msaaView = nil,
        depthView = nil,
        samples = 1,
        layout = nil,
        pLeaf = nil,
        pShadow = nil,
        vbuf = nil,
        ibuf = nil,
        icount = 0,
        gx = 0,
        gy = 0,
        gpuSampler = nil,
        pComp = nil,
        compStaging = buffer.create(48),
        staging = buffer.create(96),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        shade = Paint.with({ color = Color.rgba(0x25, 0x2E, 0x3D, 0), style = 'fill' }),
        shadePath = Path.new(),
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
