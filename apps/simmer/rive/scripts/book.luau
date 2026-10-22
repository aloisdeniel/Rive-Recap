--!strict
-- Simmer cookbook (scene 3): "recipe cards flip like a handmade cookbook", as
-- a lit 3D book on the GPU (scripts/book.wgsl).
--
-- A ScriptedDrawable over scene 3's art box (390 x 390 region points, the
-- spine at (195, 168)). The book drops onto the table closed, its cloth
-- cover swings open over the spine, and four recipe leaves turn one after
-- another: each one lifts by its lower corner, curls over the spine and lands
-- on the pile on the left, where the depth buffer puts it above the leaves
-- that turned before it (it lands higher). Nothing is ordered by a fixed
-- draw order, so no page can stay on top of the others.
--
-- Parts: back board, page block (stacked page edges on its sides), the front
-- board (a rigid box that rotates about the spine and sinks onto the table
-- once past vertical), the spine cloth (an arc that follows the front
-- board), the ribbon bookmark (draped over the block and the board, slides
-- out along the table), five leaves (four turn, the last stays). The printed
-- surfaces are one vector artboard ("Cookbook pages", an atlas of 15 cells)
-- rendered once into a texture: ten page faces, the endpaper, the cover.
--
-- Light from the upper left; shadows from a light-space depth map onto the
-- pages, the boards and the table (where only the shadow prints). Shading is
-- the collage's risograph: flat inks, a soft two-tone step, shadow printed as
-- an aubergine halftone.
--
-- Driven by two keyed inputs: `progress` (scene 3's entrance, 0..1 over
-- 2000 ms) and `idle` (the idle loop, 0..1 over 4 s), which lifts the open
-- leaves' corners in a short breeze and sways the ribbon.
--
-- Reduced motion: the reduced entrance holds progress at 1 (the open book)
-- and the breeze is off, so the book is static. Pause: both inputs come from
-- the scene's timelines, which freeze. No shader support: the same timeline
-- is drawn flat from the atlas, the leaves folding about the spine in the
-- order they land.
--
-- Resolution: the canvases follow the art box's real size, i.e. scene 3's
-- art scale (scripts/stage.luau) times the presenting density the director
-- publishes (`layoutPixelRatio`), capped at 4 px per region point. GPU passes
-- only run when the pose changed; a settled book is one image draw.

local stage = require('scripts/stage')

type Book = {
    progress: Input<number>,
    idle: Input<number>,
    atlas: Input<Artboard>,
    started: boolean,
    ctx: Context?,
    vm: ViewModel?,
    inst: Artboard?,
    -- resolution
    res: number,
    ares: number,
    -- surfaces
    acv: Canvas?,
    gc: GPUCanvas?,
    msaa: GPUTextureView?,
    depth: GPUTextureView?,
    shadowAttach: GPUTextureView?,
    shadowView: GPUTextureView?,
    atlasDirty: boolean,
    -- GPU
    gpu: boolean,
    samples: number,
    layout0: GPUBindGroupLayout?,
    layout1: GPUBindGroupLayout?,
    group0: GPUBindGroup?,
    group1: GPUBindGroup?,
    groupS: GPUBindGroup?,
    pStatic: GPUPipeline?,
    pLeaf: GPUPipeline?,
    pGround: GPUPipeline?,
    sStatic: GPUPipeline?,
    sLeaf: GPUPipeline?,
    ubo: GPUBuffer?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    lvbuf: GPUBuffer?,
    libuf: GPUBuffer?,
    licount: number,
    gsampler: GPUSampler?,
    csampler: GPUSampler?,
    staging: buffer,
    sampler: ImageSampler,
    lastKey: string,
    -- fallback
    clip: Path,
    rectPath: Path,
    paint: Paint,
}

-- region (the art box) and the book, in points
local RW, RH = 390, 390
local CX, CY = 195, 168 -- the spine's centre in the region
local LW, LH = 146, 194 -- a leaf
local NLEAF = 5
local TURNS = 4
local COVER_W, COVER_H, COVER_T, COVER_S0 = 152, 204, 4, 3
local BLOCK_X0, BLOCK_X1, BLOCK_Y, BLOCK_Z0, BLOCK_Z1 = 1.5, 145, 96, 4, 14.4
local LEAF_GAP = 0.8
-- atlas (tools/scenes_impl.py: cookbook_atlas)
local A_COLS, A_ROWS, A_CW, A_CH, A_FW, A_FH = 5, 3, 150, 198, 146, 194
local AW, AH = A_COLS * A_CW, A_ROWS * A_CH
local CELL_FRONT = { 0, 1, 2, 3, 4 }
local CELL_BACK = { 5, 6, 7, 8, 5 }
local CELL_ENDPAPER = 9 -- (cell 10, the cover, is read by the shader)
-- camera and light
local TILT = 0.38
local DIST = 760
local TARGET_Z = 8
local LIGHT = { -0.42, -0.5, 0.76 }
local AMBIENT = 0.62
local SHADOW_PX = 1536
local SHADOW_EXT = 270
local SHADOW_RANGE = 400
local MAX_RES = 4
local VSTRIDE = 40 -- pos3 nrm3 uv2 tag2
local UBO_SIZE = 368
local PI = math.pi
-- timeline (ms of the 2000 ms entrance)
local T_TOTAL = 2000
local LEAF_T0, LEAF_STEP, LEAF_DUR = 740, 230, 550
local RIBBON_LEN = 78

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

local function smooth(q: number): number
    q = clamp01(q)
    return q * q * (3 - 2 * q)
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

-- ------------------------------------------------------------ the pose
type Leaf = { th: number, k: number, lead: number, hz: number, mid: number }
type Pose = {
    alpha: number,
    lift: number,
    yaw: number,
    shift: number,
    psi: number,
    coverZ: number,
    ribbon: number,
    sway: number,
    leaves: { Leaf },
}

local function zRight(i: number): number
    return BLOCK_Z1 + 0.2 + (NLEAF - i) * LEAF_GAP -- i = 1 (first to turn) on top
end

local function zLeft(i: number): number
    return COVER_T + 0.6 + (i - 1) * LEAF_GAP
end

-- a leaf turned by p (0 flat on the right .. 1 flat on the left). Each row of
-- the leaf is an arc: base angle th at the spine, curvature k, and the lower
-- corner leading by `lead`. Early on the corner lifts first (the edge leads);
-- past half-way the free edge lags and lands last. The hinge stays at the
-- right pile's height until the leaf is past vertical, then sinks to the left
-- pile's, so a leaf never cuts through either pile.
local function turnLeaf(i: number, p: number): Leaf
    local zr, zl = zRight(i), zLeft(i)
    if p <= 0 then
        return { th = 0, k = 0, lead = 0, hz = zr, mid = 0 }
    elseif p >= 1 then
        return { th = PI, k = 0, lead = 0, hz = zl, mid = PI }
    end
    local sp = math.sin(PI * p)
    local mid = PI * easeInOut(p)
    local bend = 1.3 * sp * (0.35 - p) * 2
    local th = math.clamp(mid - bend * 0.5, 0, PI)
    local hz = if mid <= PI * 0.5 then zr else lerp(zr, zl, smooth((mid / PI - 0.5) * 2))
    return { th = th, k = bend / LW, lead = 0.45 * sp, hz = hz, mid = mid }
end

local function poseAt(tms: number, breeze: number, idlePhase: number): Pose
    local q = clamp01(tms / 420)
    local r = 1 - q
    local open = easeInOut((tms - 330) / 520)
    local psi = PI * open
    local coverZ = if psi <= PI * 0.5 then zRight(1) + 0.6 else lerp(zRight(1) + 0.6, COVER_T, smooth((psi / PI - 0.5) * 2))
    local leaves: { Leaf } = {}
    for i = 1, NLEAF do
        if i <= TURNS then
            local t0 = LEAF_T0 + (i - 1) * LEAF_STEP
            leaves[i] = turnLeaf(i, clamp01((tms - t0) / LEAF_DUR))
        else
            leaves[i] = turnLeaf(i, 0)
        end
    end
    -- the breeze: the open spread's free corners lift a little, then settle
    if breeze > 0 then
        local top = leaves[TURNS]
        top.k = -0.16 * breeze / LW
        top.lead = -0.16 * breeze
        local last = leaves[NLEAF]
        local b2 = breeze * breeze
        last.k = 0.2 * b2 / LW
        last.lead = 0.22 * b2
    end
    return {
        alpha = clamp01(tms / 120),
        lift = 150 * r * r * r,
        yaw = 0.14 * r * r,
        -- closed, the book sits centred; it slides over as the cover opens onto the left
        shift = -(COVER_S0 + COVER_W) * 0.5 * (1 - smooth((tms - 380) / 520)),
        psi = psi,
        coverZ = coverZ,
        ribbon = RIBBON_LEN * easeOut((tms - 1450) / 450),
        sway = 0.06 * breeze * math.sin(idlePhase * 2 * PI * 3),
        leaves = leaves,
    }
end

-- ------------------------------------------------------------ geometry
type MeshBuilder = { v: { number }, i: { number }, n: number }

local function vert(m: MeshBuilder, x: number, y: number, z: number, nx: number, ny: number, nz: number,
    u: number, w: number, mat: number, part: number): number
    local v = m.v
    for _, f in { x, y, z, nx, ny, nz, u, w, mat, part } do
        table.insert(v, f)
    end
    m.n += 1
    return m.n - 1
end

local function tri(m: MeshBuilder, a: number, b: number, c: number)
    table.insert(m.i, a)
    table.insert(m.i, b)
    table.insert(m.i, c)
end

-- an axis-aligned quad: corners in order around it, one normal, uv per corner
local function quad(m: MeshBuilder, p: { { number } }, n: { number }, uv: { { number } }, mat: number, part: number)
    local ids: { number } = {}
    for k = 1, 4 do
        ids[k] = vert(m, p[k][1], p[k][2], p[k][3], n[1], n[2], n[3], uv[k][1], uv[k][2], mat, part)
    end
    tri(m, ids[1], ids[2], ids[3])
    tri(m, ids[1], ids[3], ids[4])
end

local UV0 = { { 0, 0 }, { 1, 0 }, { 1, 1 }, { 0, 1 } }

-- the sides of a box (no bottom: it sits on something); top optional
local function boxSides(m: MeshBuilder, x0: number, x1: number, y0: number, y1: number, z0: number, z1: number,
    mat: number, part: number, top: number?)
    -- uv.y carries z for the page-edge lines
    local zu = { { 0, z1 }, { 1, z1 }, { 1, z0 }, { 0, z0 } }
    quad(m, { { x0, y1, z1 }, { x1, y1, z1 }, { x1, y1, z0 }, { x0, y1, z0 } }, { 0, 1, 0 }, zu, mat, part)
    quad(m, { { x1, y0, z1 }, { x0, y0, z1 }, { x0, y0, z0 }, { x1, y0, z0 } }, { 0, -1, 0 }, zu, mat, part)
    quad(m, { { x1, y1, z1 }, { x1, y0, z1 }, { x1, y0, z0 }, { x1, y1, z0 } }, { 1, 0, 0 }, zu, mat, part)
    quad(m, { { x0, y0, z1 }, { x0, y1, z1 }, { x0, y1, z0 }, { x0, y0, z0 } }, { -1, 0, 0 }, zu, mat, part)
    if top ~= nil then
        quad(m, { { x0, y0, z1 }, { x1, y0, z1 }, { x1, y1, z1 }, { x0, y1, z1 } }, { 0, 0, 1 }, UV0, top, part)
    end
end

-- materials (book.wgsl fs_static): 0 cover cloth, 1 endpaper, 2 board edge, 3 page edges, 4 ribbon, 5 spine
local function buildStatic(): MeshBuilder
    local m: MeshBuilder = { v = {}, i = {}, n = 0 }
    local hy = COVER_H * 0.5
    local s0, s1 = COVER_S0, COVER_S0 + COVER_W
    -- back board (its turn-in shows as a cloth rim round the page block)
    boxSides(m, s0, s1, -hy, hy, 0, COVER_T, 2, 0, 2)
    -- the page block
    boxSides(m, BLOCK_X0, BLOCK_X1, -BLOCK_Y, BLOCK_Y, BLOCK_Z0, BLOCK_Z1, 3, 0, nil)
    -- the front board, in its own frame (x = s from the spine, z = t through the board)
    local t = COVER_T
    -- outside (t = T): the printed cover, read left to right when closed
    quad(m, { { s0, -hy, t }, { s1, -hy, t }, { s1, hy, t }, { s0, hy, t } }, { 0, 0, 1 },
        { { 0, 0 }, { 1, 0 }, { 1, 1 }, { 0, 1 } }, 0, 1)
    -- inside (t = 0): the endpaper, read left to right once open (spine on its right)
    quad(m, { { s0, -hy, 0 }, { s1, -hy, 0 }, { s1, hy, 0 }, { s0, hy, 0 } }, { 0, 0, -1 },
        { { 1, 0 }, { 0, 0 }, { 0, 1 }, { 1, 1 } }, 1, 1)
    local zu = { { 0, 0 }, { 1, 0 }, { 1, 1 }, { 0, 1 } }
    quad(m, { { s0, hy, t }, { s1, hy, t }, { s1, hy, 0 }, { s0, hy, 0 } }, { 0, 1, 0 }, zu, 2, 1)
    quad(m, { { s1, -hy, t }, { s0, -hy, t }, { s0, -hy, 0 }, { s1, -hy, 0 } }, { 0, -1, 0 }, zu, 2, 1)
    quad(m, { { s1, hy, t }, { s1, -hy, t }, { s1, -hy, 0 }, { s1, hy, 0 } }, { 1, 0, 0 }, zu, 2, 1)
    quad(m, { { s0, -hy, t }, { s0, hy, t }, { s0, hy, 0 }, { s0, -hy, 0 } }, { -1, 0, 0 }, zu, 2, 1)
    -- spine cloth: an arc strip (positions computed in the shader from a = uv.x)
    local SEG = 12
    local first = m.n
    for k = 0, SEG do
        vert(m, 0, -hy, 0, 0, 0, 1, k / SEG, 0, 5, 3)
        vert(m, 0, hy, 0, 0, 0, 1, k / SEG, 1, 5, 3)
    end
    for k = 0, SEG - 1 do
        local a = first + k * 2
        tri(m, a, a + 1, a + 2)
        tri(m, a + 1, a + 3, a + 2)
    end
    -- ribbon: three columns (the centre one carries the swallowtail notch) along d
    local ds: { number } = {}
    local d = 0
    while d < 22 do
        table.insert(ds, d)
        d += 1
    end
    while d < 104 do
        table.insert(ds, d)
        d += 4
    end
    table.insert(ds, 400) -- the tail row: always clamped to the length shown
    local rfirst = m.n
    for _, dd in ds do
        vert(m, 0, 0, 0, 0, 0, 1, dd, -1, 4, 2)
        vert(m, 9, 0, 0, 0, 0, 1, dd, 0, 4, 2)
        vert(m, 0, 0, 0, 0, 0, 1, dd, 1, 4, 2)
    end
    for r = 0, #ds - 2 do
        local a = rfirst + r * 3
        local b = a + 3
        tri(m, a, b, a + 1)
        tri(m, a + 1, b, b + 1)
        tri(m, a + 1, b + 1, a + 2)
        tri(m, a + 2, b + 1, b + 2)
    end
    return m
end

local function upload(m: MeshBuilder, label: string): (GPUBuffer, GPUBuffer, number)
    local vb = buffer.create(#m.v * 4)
    for k, f in m.v do
        buffer.writef32(vb, (k - 1) * 4, f)
    end
    local n = #m.i
    local ib = buffer.create(n * 2)
    for k, x in m.i do
        buffer.writeu16(ib, (k - 1) * 2, x)
    end
    local vbuf = GPUBuffer.new({ size = #m.v * 4, usage = 'vertex', data = vb, immutable = true, label = label .. ' verts' })
    local ibuf = GPUBuffer.new({ size = n * 2, usage = 'index', data = ib, immutable = true, label = label .. ' tris' })
    return vbuf, ibuf, n
end

-- every leaf's grid in one buffer: (s, y, leaf index), so all five draw in one call
-- (the leaf index is a vertex attribute: instance_index does not bake to every target)
local function buildLeafGrid(): (GPUBuffer, GPUBuffer, number)
    local GX, GY = 30, 14
    local per = (GX + 1) * (GY + 1)
    local vb = buffer.create(per * NLEAF * 12)
    local o = 0
    for l = 0, NLEAF - 1 do
        for j = 0, GY do
            for i = 0, GX do
                -- denser near the spine, where the curl is tightest
                local s = i / GX
                buffer.writef32(vb, o, s * (0.55 + 0.45 * s))
                buffer.writef32(vb, o + 4, j / GY)
                buffer.writef32(vb, o + 8, l)
                o += 12
            end
        end
    end
    local n = GX * GY * 6 * NLEAF
    local ib = buffer.create(n * 2)
    o = 0
    for l = 0, NLEAF - 1 do
        for j = 0, GY - 1 do
            for i = 0, GX - 1 do
                local a = l * per + j * (GX + 1) + i
                local b = a + 1
                local c = a + GX + 1
                local d = c + 1
                for _, x in { a, c, b, b, c, d } do
                    buffer.writeu16(ib, o, x)
                    o += 2
                end
            end
        end
    end
    local vbuf = GPUBuffer.new({ size = per * NLEAF * 12, usage = 'vertex', data = vb, immutable = true, label = 'leaf grids' })
    local ibuf = GPUBuffer.new({ size = n * 2, usage = 'index', data = ib, immutable = true, label = 'leaf tris' })
    return vbuf, ibuf, n
end

-- ------------------------------------------------------------ setup
local function initGpu(self: Book, context: Context)
    local sh = context:shader('scripts/book')
    if sh == nil then
        return
    end
    local f = context:features()
    self.samples = if f.maxSamples >= 4 then 4 else 1
    local l0 = GPUBindGroupLayout.new({ shader = sh, groupIndex = 0, label = 'book' })
    local l1 = GPUBindGroupLayout.new({ shader = sh, groupIndex = 1, label = 'book shadow map' })
    self.layout0 = l0
    self.layout1 = l1
    local over: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    local vl: { VertexBufferLayout } = { {
        stride = VSTRIDE,
        attributes = {
            { format = 'float32x3', slot = 0, offset = 0 },
            { format = 'float32x3', slot = 1, offset = 12 },
            { format = 'float32x2', slot = 2, offset = 24 },
            { format = 'float32x2', slot = 3, offset = 32 },
        },
    } }
    local ll: { VertexBufferLayout } = { { stride = 12, attributes = {
        { format = 'float32x2', slot = 0, offset = 0 },
        { format = 'float32', slot = 1, offset = 8 },
    } } }
    self.pGround = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_ground' },
        fragment = { module = sh, entryPoint = 'fs_ground' },
        vertexLayout = {},
        bindGroupLayouts = { l0, l1 },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'always', write = false },
        sampleCount = self.samples,
    })
    self.pStatic = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_static' },
        fragment = { module = sh, entryPoint = 'fs_static' },
        vertexLayout = vl,
        bindGroupLayouts = { l0, l1 },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = self.samples,
    })
    self.pLeaf = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_leaf' },
        fragment = { module = sh, entryPoint = 'fs_leaf' },
        vertexLayout = ll,
        bindGroupLayouts = { l0, l1 },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = self.samples,
    })
    self.sStatic = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_static_shadow' },
        vertexLayout = vl,
        bindGroupLayouts = { l0, l1 },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
    })
    self.sLeaf = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_leaf_shadow' },
        vertexLayout = ll,
        bindGroupLayouts = { l0, l1 },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
    })
    self.ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'book' })
    self.vbuf, self.ibuf, self.icount = upload(buildStatic(), 'book')
    self.lvbuf, self.libuf, self.licount = buildLeafGrid()
    self.gsampler = GPUSampler.new({ min = 'linear', mag = 'linear', mipmap = 'nearest' })
    self.csampler = GPUSampler.new({ min = 'linear', mag = 'linear', mipmap = 'nearest', compare = 'less-equal' })
    local stex = GPUTexture.new({ width = SHADOW_PX, height = SHADOW_PX, format = 'depth32float', renderTarget = true,
        label = 'book shadow map' })
    self.shadowAttach = stex:view()
    self.shadowView = stex:view({ aspect = 'depth-only' })
    -- the shadow pass binds a 1 x 1 stand-in at group 1: the map is never bound while it is written
    local dummy = GPUTexture.new({ width = 1, height = 1, format = 'depth32float', renderTarget = true,
        label = 'book shadow stand-in' })
    self.groupS = GPUBindGroup.new({
        layout = l1,
        textures = { { slot = 0, view = dummy:view({ aspect = 'depth-only' }) } },
        samplers = { { slot = 1, sampler = self.csampler :: GPUSampler } },
    })
    self.group1 = GPUBindGroup.new({
        layout = l1,
        textures = { { slot = 0, view = self.shadowView :: GPUTextureView } },
        samplers = { { slot = 1, sampler = self.csampler :: GPUSampler } },
    })
    self.gpu = true
end

-- resolution for the art box's real size: scene 3's art scale x the presenting density
local function wantedRes(self: Book): number
    local vm = self.vm
    local slots = stage.fromModel(vm)
    local sc = 1
    if slots ~= nil then
        local _, _, s = stage.frame(slots, '3')
        sc = s
    end
    local prp = if vm ~= nil then vm:getNumber('layoutPixelRatio') else nil
    local pr = if prp ~= nil and prp.value > 0 then prp.value else 1
    return math.clamp(math.ceil(sc * pr * 4) / 4, 1, MAX_RES)
end

local function allocate(self: Book, res: number)
    local ctx = self.ctx
    if ctx == nil then
        return
    end
    self.res = res
    -- the atlas a little denser than the region: lifted leaves come closer to the camera
    local ares = math.min(res * 1.25, MAX_RES)
    if ares ~= self.ares or self.acv == nil then
        self.ares = ares
        self.acv = ctx:canvas({ width = math.ceil(AW * ares), height = math.ceil(AH * ares) })
        self.atlasDirty = true
    end
    if not self.gpu then
        return
    end
    local w, h = math.ceil(RW * res), math.ceil(RH * res)
    self.gc = ctx:gpuCanvas({ width = w, height = h })
    if self.samples > 1 then
        self.msaa = GPUTexture.new({ width = w, height = h, format = 'rgba8unorm', renderTarget = true,
            sampleCount = self.samples, label = 'book msaa' }):view()
    end
    self.depth = GPUTexture.new({ width = w, height = h, format = 'depth32float', renderTarget = true,
        sampleCount = self.samples, label = 'book depth' }):view()
    local l0, ubo, smp, acv = self.layout0, self.ubo, self.gsampler, self.acv
    if l0 ~= nil and ubo ~= nil and smp ~= nil and acv ~= nil then
        self.group0 = GPUBindGroup.new({
            layout = l0,
            ubos = { { slot = 0, buffer = ubo } },
            textures = { { slot = 1, view = acv.image:view() } },
            samplers = { { slot = 2, sampler = smp } },
        })
    end
    self.lastKey = ''
end

function init(self: Book, context: Context): boolean
    if self.vm == nil then
        self.vm = context:viewModel()
    end
    if self.started then
        return true
    end
    self.started = true
    self.ctx = context
    local inst = self.atlas:instance()
    inst:advance(0)
    self.inst = inst
    initGpu(self, context)
    allocate(self, wantedRes(self))
    return true
end

function advance(self: Book, seconds: number): boolean
    local res = wantedRes(self)
    if res ~= self.res then
        allocate(self, res)
    end
    return true
end

-- ------------------------------------------------------------ uniforms
local function writeUniforms(self: Book, ps: Pose)
    local b = self.staging
    local sa, ca = math.sin(TILT), math.cos(TILT)
    local ex, ey, ez = 0, DIST * sa, TARGET_Z + DIST * ca
    local lx, ly, lz = LIGHT[1], LIGHT[2], LIGHT[3]
    local ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll
    -- light basis: a = normalize(up x L), b = L x a
    local ax, ay, az = -ly, lx, 0
    local al = math.sqrt(ax * ax + ay * ay)
    ax, ay = ax / al, ay / al
    local bx, by, bz = ly * az - lz * ay, lz * ax - lx * az, lx * ay - ly * ax
    local vals = {
        ex, ey, ez, DIST,
        1, 0, 0, CX,
        0, -ca, sa, CY,
        0, -sa, -ca, DIST - 460,
        RW, RH, DIST + 460, self.res,
        math.cos(ps.yaw), math.sin(ps.yaw), ps.lift, ps.shift,
        lx, ly, lz, AMBIENT,
        ax, ay, az, SHADOW_EXT,
        bx, by, bz, SHADOW_RANGE,
        ps.psi, ps.coverZ, ps.ribbon, ps.sway,
        ps.alpha, 1 / SHADOW_PX, LW, LH,
        A_FW / AW, A_FH / AH, A_CW / AW, A_CH / AH,
        (A_CW - A_FW) * 0.5 / AW, (A_CH - A_FH) * 0.5 / AH, A_COLS, 0,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    local o = #vals * 4
    for i = 1, NLEAF do
        local lf = ps.leaves[i]
        buffer.writef32(b, o, lf.th)
        buffer.writef32(b, o + 4, lf.k)
        buffer.writef32(b, o + 8, lf.lead)
        buffer.writef32(b, o + 12, lf.hz)
        o += 16
    end
    for i = 1, NLEAF do
        buffer.writef32(b, o, CELL_FRONT[i])
        buffer.writef32(b, o + 4, CELL_BACK[i])
        buffer.writef32(b, o + 8, 0)
        buffer.writef32(b, o + 12, 0)
        o += 16
    end
    local ubo = self.ubo
    if ubo ~= nil then
        ubo:write(b)
    end
end

local function renderBook(self: Book, ps: Pose)
    local gc, depth, g0, g1, gS, ubo = self.gc, self.depth, self.group0, self.group1, self.groupS, self.ubo
    local pS, pL, pG, sS, sL = self.pStatic, self.pLeaf, self.pGround, self.sStatic, self.sLeaf
    local vb, ib, lvb, lib, sh = self.vbuf, self.ibuf, self.lvbuf, self.libuf, self.shadowAttach
    if gc == nil or depth == nil or g0 == nil or g1 == nil or gS == nil or ubo == nil or pS == nil or pL == nil or pG == nil
        or sS == nil or sL == nil or vb == nil or ib == nil or lvb == nil or lib == nil or sh == nil then
        return
    end
    writeUniforms(self, ps)
    -- 1. the light's depth map (group 1 is the stand-in: the map is not bound while it is written)
    local sp = gc:beginRenderPass({
        depthStencil = { view = sh, depthLoadOp = 'clear', depthStoreOp = 'store', depthClearValue = 1 },
        label = 'book shadow map',
    })
    sp:setViewport(0, 0, SHADOW_PX, SHADOW_PX)
    sp:setBindGroup(0, g0)
    sp:setBindGroup(1, gS)
    sp:setPipeline(sS)
    sp:setVertexBuffer(0, vb)
    sp:setIndexBuffer(ib, 'uint16')
    sp:drawIndexed(self.icount)
    sp:setPipeline(sL)
    sp:setVertexBuffer(0, lvb)
    sp:setIndexBuffer(lib, 'uint16')
    sp:drawIndexed(self.licount)
    sp:finish()
    -- 2. the book
    local pass: GPURenderPass
    local msaa = self.msaa
    if msaa ~= nil then
        pass = gc:beginRenderPass({
            color = { { view = msaa, resolveTarget = gc:colorView(), loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'cookbook',
        })
    else
        pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'cookbook',
        })
    end
    pass:setBindGroup(0, g0)
    pass:setBindGroup(1, g1)
    pass:setPipeline(pG)
    pass:draw(6)
    pass:setPipeline(pS)
    pass:setVertexBuffer(0, vb)
    pass:setIndexBuffer(ib, 'uint16')
    pass:drawIndexed(self.icount)
    pass:setPipeline(pL)
    pass:setVertexBuffer(0, lvb)
    pass:setIndexBuffer(lib, 'uint16')
    pass:drawIndexed(self.licount)
    pass:finish()
end

-- ------------------------------------------------------------ 2D fallback
-- One atlas cell drawn into the rectangle x0..x0+w (region points), y centred
-- on the spine; w may be narrower than the face (a leaf folding over).
local function drawCell(self: Book, r: Renderer, cell: number, x0: number, w: number, y0: number, h: number)
    local acv = self.acv
    if acv == nil or w <= 0.2 then
        return
    end
    local cx = (cell % A_COLS) * A_CW + (A_CW - A_FW) * 0.5
    local cy = math.floor(cell / A_COLS) * A_CH + (A_CH - A_FH) * 0.5
    local clip = self.clip
    clip:reset()
    clip:moveTo(Vector.xy(x0, y0))
    clip:lineTo(Vector.xy(x0 + w, y0))
    clip:lineTo(Vector.xy(x0 + w, y0 + h))
    clip:lineTo(Vector.xy(x0, y0 + h))
    clip:close()
    r:save()
    r:clipPath(clip)
    local sx, sy = w / A_FW, h / A_FH
    r:transform(Mat2D.withScaleAndTranslation(sx / self.ares, sy / self.ares, x0 - cx * sx, y0 - cy * sy))
    r:drawImage(acv.image, self.sampler, 'srcOver', 1)
    r:restore()
end

local function fillRect(self: Book, r: Renderer, x: number, y: number, w: number, h: number, c: Color)
    local p = self.rectPath
    p:reset()
    p:moveTo(Vector.xy(x, y))
    p:lineTo(Vector.xy(x + w, y))
    p:lineTo(Vector.xy(x + w, y + h))
    p:lineTo(Vector.xy(x, y + h))
    p:close()
    self.paint.color = c
    r:drawPath(p, self.paint)
end

local function drawFlat(self: Book, r: Renderer, ps: Pose)
    r:save()
    r:modulateOpacity(ps.alpha)
    local hy = COVER_H * 0.5
    local top = CY - LH * 0.5
    fillRect(self, r, CX - COVER_W - COVER_S0 + 6, CY - hy + 6, 2 * (COVER_W + COVER_S0), COVER_H, Color.rgba(0x48, 0x29, 0x3D, 64))
    fillRect(self, r, CX - COVER_W - COVER_S0, CY - hy, 2 * (COVER_W + COVER_S0), COVER_H, Color.rgb(0xE4, 0x49, 0x32))
    drawCell(self, r, CELL_ENDPAPER, CX - LW, LW, top, LH)
    drawCell(self, r, CELL_FRONT[NLEAF], CX, LW, top, LH)
    -- leaves, lowest first: what lies higher (or is in the air) draws later
    local order: { number } = {}
    for i = 1, TURNS do
        table.insert(order, i)
    end
    local function key(i: number): number
        local lf = ps.leaves[i]
        return lf.hz + 60 * math.sin(lf.mid)
    end
    table.sort(order, function(a: number, b: number): boolean
        return key(a) < key(b)
    end)
    for _, i in order do
        local c = math.cos(ps.leaves[i].mid)
        if c >= 0 then
            drawCell(self, r, CELL_FRONT[i], CX, LW * c, top, LH)
        else
            drawCell(self, r, CELL_BACK[i], CX + LW * c, -LW * c, top, LH)
        end
    end
    r:restore()
end

-- ------------------------------------------------------------ draw
local function reducedMotion(self: Book): boolean
    local vm = self.vm
    local p = if vm ~= nil then vm:getBoolean('reducedMotion') else nil
    return p ~= nil and p.value
end

function draw(self: Book, renderer: Renderer)
    local inst, acv = self.inst, self.acv
    if inst == nil or acv == nil then
        return
    end
    if self.atlasDirty then
        self.atlasDirty = false
        local r = acv:beginFrame()
        r:save()
        r:transform(Mat2D.withScale(self.ares, self.ares))
        inst:draw(r)
        r:restore()
        acv:endFrame()
        self.lastKey = ''
    end
    local tms = clamp01(self.progress) * T_TOTAL
    local idle = self.idle
    local breeze = 0
    if tms >= T_TOTAL and not reducedMotion(self) then
        local w = (idle - 0.55) / 0.35
        if w > 0 and w < 1 then
            local s = math.sin(PI * w)
            breeze = s * s
        end
    end
    local ps = poseAt(tms, breeze, if breeze > 0 then idle else 0)
    local gc = self.gc
    if not self.gpu or gc == nil then
        drawFlat(self, renderer, ps)
        return
    end
    local key = string.format('%.2f|%.4f|%.4f|%g', tms, breeze, ps.sway, self.res)
    if key ~= self.lastKey then
        self.lastKey = key
        renderBook(self, ps)
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.res, 1 / self.res))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', ps.alpha)
    renderer:restore()
end

return function(): Node<Book>
    return {
        progress = 0,
        idle = 0,
        atlas = late(),
        started = false,
        ctx = nil,
        vm = nil,
        inst = nil,
        res = 0,
        ares = 0,
        acv = nil,
        gc = nil,
        msaa = nil,
        depth = nil,
        shadowAttach = nil,
        shadowView = nil,
        atlasDirty = true,
        gpu = false,
        samples = 1,
        layout0 = nil,
        layout1 = nil,
        group0 = nil,
        group1 = nil,
        groupS = nil,
        pStatic = nil,
        pLeaf = nil,
        pGround = nil,
        sStatic = nil,
        sLeaf = nil,
        ubo = nil,
        vbuf = nil,
        ibuf = nil,
        icount = 0,
        lvbuf = nil,
        libuf = nil,
        licount = 0,
        gsampler = nil,
        csampler = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        lastKey = '',
        clip = Path.new(),
        rectPath = Path.new(),
        paint = Paint.with({ style = 'fill', color = Color.rgb(0xE4, 0x49, 0x32) }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
