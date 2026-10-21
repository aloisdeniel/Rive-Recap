--!strict
-- Patchwork signature fold: a quilt sheet that lands over the scene patch and
-- folds away to reveal the next one, rendered as real 3D cloth on the GPU
-- (shaders/cloth.wgsl), with a needle riding the fold's crest and pulling a
-- running stitch behind it.
--
-- A ScriptedDrawable at the artboard origin, drawn above the World and below
-- the chrome. The Handoff layer's timelines key its three inputs:
--   fold  0..1 the sheet lands (unrolls over the old scene, leftward),
--         1..2 it folds away (rolls up from its free edge, leftward), revealing
--         the new scene underneath; 0 and 2 draw nothing
--   dir   +1 forward (terracotta quilt, lands from the right),
--         -1 back (rose quilt, mirrored: lands from the left, leaves rightward)
--   cam   the camera scale the World is keyed to, so the sheet always fits the
--         scene patch exactly while the camera pulls back to show the quilt
--
-- Reduced motion keys fold = 0 (the Handoff layer uses its oat veil instead).
-- Runtimes without shader support draw a flat, hinged 2D panel.

type Cloth = {
    fold: Input<number>,
    dir: Input<number>,
    cam: Input<number>,
    ctx: Context?,
    size: Vector,
    scale: number,
    seed: number,
    -- GPU
    gpu: boolean,
    gc: GPUCanvas?,
    colorView: GPUTextureView?,
    msaaView: GPUTextureView?,
    depthView: GPUTextureView?,
    samples: number,
    pSheet: GPUPipeline?,
    pShadow: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    staging: buffer,
    sampler: ImageSampler,
    -- vector parts (needle, thread, 2D fallback)
    path: Path,
    thread: Path,
    eyePath: Path,
    shinePath: Path,
    flat: Paint,
    steel: Paint,
    steelEdge: Paint,
    eye: Paint,
    shine: Paint,
    threadPaint: Paint,
    shade: Paint,
}

local AW, AH = 390, 844 -- artboard (scene patch at camera scale 1)
-- canvas pixels per point: a ScriptedDrawable gets no resize/pixel density, so
-- the sheet renders at 2x (supersampled on @1x captures, soft-ish only on @3x)
local RES = 2
local GX, GY = 44, 96 -- sheet mesh resolution (~9 pt cells)
local PI = math.pi

local function clamp01(x: number): number
    return math.clamp(x, 0, 1)
end

local function lerp(a: number, b: number, t: number): number
    return a + (b - a) * t
end

local function easeSine(q: number): number
    return 0.5 - 0.5 * math.cos(PI * clamp01(q))
end

local function easeOut(q: number): number
    local r = 1 - clamp01(q)
    return 1 - r * r * r
end

-- Pose of the roll at progress p (0 = flat, 1 = rolled away past the far edge),
-- in local sheet px (the roll always travels toward -x here). Anticipation: the
-- free corner lifts and settles back a touch before the sweep; the roll swells
-- to a soft, cloth-like radius mid-move. Returns axis point, unit normal, radius.
local function pose(p: number, W: number, H: number): (number, number, number, number, number)
    local phi = lerp(0.40, 0.04, easeSine(p))
    local nx, ny = math.cos(phi), math.sin(phi)
    local q = clamp01((p - 0.04) / 0.96)
    local R = W * (0.065 + 0.15 * math.sin(PI * q) ^ 1.1 + 0.05 * q)
    local span = W * nx + H * ny
    local cEnd = span + R * 1.2 / nx + W * 0.04
    local c
    if p < 0.07 then
        c = W * 0.09 * easeOut(p / 0.07)
    elseif p < 0.11 then
        c = W * (0.09 - 0.016 * math.sin(PI * 0.5 * (p - 0.07) / 0.04))
    else
        local q2 = clamp01((p - 0.11) / 0.89)
        c = lerp(W * 0.074, cEnd, 0.55 * easeSine(q2) + 0.45 * q2)
    end
    return W - nx * c, H - ny * c, nx, ny, R
end

-- ------------------------------------------------------------ GPU
local function buildMesh(self: Cloth)
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
    self.vbuf = GPUBuffer.new({ size = nv * 8, usage = 'vertex', data = vb, immutable = true, label = 'quilt grid' })
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
    self.ibuf = GPUBuffer.new({ size = n * 2, usage = 'index', data = ib, immutable = true, label = 'quilt tris' })
    self.icount = n
end

local function initGpu(self: Cloth, context: Context)
    local sh = context:shader('shaders/cloth')
    if sh == nil then
        return
    end
    local f = context:features()
    -- the sheet is already supersampled (2 px per pt); 2x MSAA is enough for its edges
    self.samples = if f.maxSamples >= 2 then 2 else 1
    local layout = GPUBindGroupLayout.new({ shader = sh, groupIndex = 0, label = 'cloth' })
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
    self.pSheet = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_sheet' },
        fragment = { module = sh, entryPoint = 'fs_sheet' },
        vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
        bindGroupLayouts = { layout },
        colorTargets = { { format = fmt, blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = self.samples,
    })
    local ubo = GPUBuffer.new({ size = 96, usage = 'uniform', label = 'cloth uniforms' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = layout, ubos = { { slot = 0, buffer = ubo } } })
    buildMesh(self)
    self.gpu = true
end

local function allocate(self: Cloth)
    local ctx = self.ctx
    if ctx == nil or not self.gpu or self.size.x <= 0 or self.size.y <= 0 then
        return
    end
    local w = math.max(1, math.ceil(self.size.x * self.scale))
    local h = math.max(1, math.ceil(self.size.y * self.scale))
    local gc = ctx:gpuCanvas({ width = w, height = h })
    self.gc = gc
    self.colorView = gc:colorView()
    if self.samples > 1 then
        self.msaaView = GPUTexture.new({ width = w, height = h, format = 'rgba8unorm', renderTarget = true,
            sampleCount = self.samples, label = 'cloth msaa' }):view()
    end
    self.depthView = GPUTexture.new({ width = w, height = h, format = 'depth32float', renderTarget = true,
        sampleCount = self.samples, label = 'cloth depth' }):view()
end

function init(self: Cloth, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    initGpu(self, context) -- surfaces are allocated on the first fold, not up front
    return true
end

function advance(self: Cloth, seconds: number): boolean
    return true
end

-- Current state as (p, mirrored, phase u, landing).
local function phase(self: Cloth): (number, boolean, number, boolean)
    local f = math.clamp(self.fold, 0, 2)
    local fwd = self.dir >= 0
    -- the roll covers/uncovers most of the patch in the first half of its pose
    -- range (its radius is large), so progress is eased out to keep the visible
    -- edge travelling evenly through the whole hand-off
    if f <= 1 then
        -- landing: a time-reversed roll that arrives from the leading side
        return 1 - (1 - (1 - f)) ^ 1.8, fwd, f, true
    end
    return 1 - (1 - (f - 1)) ^ 1.8, not fwd, f - 1, false
end

-- Sheet placement in layout points: origin and size of the scene patch.
local function sheetRect(self: Cloth): (number, number, number, number)
    local c = math.clamp(self.cam, 0.5, 1.2)
    local sw, sh = self.size.x * c, self.size.y * c
    return (self.size.x - sw) * 0.5, (self.size.y - sh) * 0.5, sw, sh
end

local function writeUniforms(self: Cloth, ubo: GPUBuffer, p: number, mirrored: boolean)
    local k = self.scale
    local ox, oy, sw, sh = sheetRect(self)
    local W, H = sw * k, sh * k
    local ax, ay, nx, ny, R = pose(p, W, H)
    local ptK = sw / AW * k -- px per sheet point
    local b = self.staging
    local vals = {
        W, H, ox * k, oy * k,
        self.size.x * k, self.size.y * k, self.size.y * k * 2.0, if mirrored then 1 else 0,
        ax, ay, nx, ny,
        R, 1, ptK, 3.2 * ptK * math.sin(PI * clamp01(p * 1.4)),
        -0.42, -0.58, 0.70, 0.55,
        if self.dir >= 0 then 0 else 1, self.seed, AW, AH,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
end

local function renderSheet(self: Cloth, p: number, mirrored: boolean): boolean
    local gc, pSheet, pShadow, ubo, g = self.gc, self.pSheet, self.pShadow, self.ubo, self.group
    local vbuf, ibuf, depth = self.vbuf, self.ibuf, self.depthView
    if gc == nil or pSheet == nil or pShadow == nil or ubo == nil or g == nil or vbuf == nil or ibuf == nil
        or depth == nil then
        return false
    end
    writeUniforms(self, ubo, p, mirrored)
    local pass: GPURenderPass
    local msaa = self.msaaView
    if msaa ~= nil then
        pass = gc:beginRenderPass({
            color = { { view = msaa, resolveTarget = self.colorView, loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'quilt fold',
        })
    else
        pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'quilt fold',
        })
    end
    pass:setBindGroup(0, g)
    pass:setPipeline(pShadow)
    pass:draw(6)
    pass:setPipeline(pSheet)
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:drawIndexed(self.icount)
    pass:finish()
    return true
end

-- Project a local-frame sheet point (px, with height z px) to layout points.
local function projectPt(self: Cloth, lx: number, ly: number, z: number, mirrored: boolean): Vector
    local k = self.scale
    local ox, oy, sw, _ = sheetRect(self)
    local W = sw * k
    local x = if mirrored then W - lx else lx
    local px, py = x + ox * k, ly + oy * k
    local cx, cy = self.size.x * k * 0.5, self.size.y * k * 0.5
    local D = self.size.y * k * 2.0
    local f = D / math.max(D - z, 1)
    return Vector.xy((cx + (px - cx) * f) / k, (cy + (py - cy) * f) / k)
end

-- The guide needle rides the crest of the roll, pulling a running stitch along
-- it: down the sheet while it lands, back up while it folds away.
local function drawNeedle(self: Cloth, r: Renderer, p: number, mirrored: boolean, u: number, landing: boolean)
    local k = self.scale
    local _, _, sw, sh = sheetRect(self)
    local W, H = sw * k, sh * k
    local ax, ay, nx, ny, R = pose(p, W, H)
    local tx, ty = -ny, nx -- along the axis, pointing down the sheet
    local cx, cy = ax + nx * R, ay + ny * R -- the crest line (a quarter turn up the roll)
    local e = easeSine(u)
    local yStart = if landing then -0.10 * H else 1.10 * H
    local yEnd = if landing then 1.10 * H else -0.10 * H
    local yN = lerp(yStart, yEnd, e)
    local function at(y: number): Vector
        local s = (y - cy) / ty
        return projectPt(self, cx + s * tx, cy + s * ty, R * 1.05, mirrored)
    end
    local tip = at(yN)
    local back = at(yN + (if landing then -1 else 1) * 86 * k)
    local start = at(yStart)
    -- running stitch: dashes from the edge it started at to the needle's eye
    local th = self.thread
    th:reset()
    local dxv, dyv = back.x - start.x, back.y - start.y
    local len = math.sqrt(dxv * dxv + dyv * dyv)
    if len > 1 then
        local ux, uy = dxv / len, dyv / len
        local s = 0
        while s < len do
            local s2 = math.min(len, s + 7)
            th:moveTo(Vector.xy(start.x + ux * s, start.y + uy * s))
            th:lineTo(Vector.xy(start.x + ux * s2, start.y + uy * s2))
            s += 12
        end
        r:drawPath(th, self.threadPaint)
    end
    -- the needle, tip leading along the crest
    local vx, vy = tip.x - back.x, tip.y - back.y
    local vl = math.max(0.001, math.sqrt(vx * vx + vy * vy))
    local ang = math.atan2(vy, vx)
    local L = vl
    local w = 4.6
    local pth = self.path
    pth:reset()
    pth:moveTo(Vector.xy(L, 0))
    pth:cubicTo(Vector.xy(L * 0.55, -w * 0.6), Vector.xy(L * 0.22, -w), Vector.xy(0, -w * 0.7))
    pth:cubicTo(Vector.xy(-3, -w * 0.6), Vector.xy(-3, w * 0.6), Vector.xy(0, w * 0.7))
    pth:cubicTo(Vector.xy(L * 0.22, w), Vector.xy(L * 0.55, w * 0.6), Vector.xy(L, 0))
    pth:close()
    r:save()
    r:transform(Mat2D.withTranslation(back.x, back.y) * Mat2D.withRotation(ang))
    -- soft contact shadow under the needle
    r:save()
    r:transform(Mat2D.withTranslation(4, 6))
    r:drawPath(pth, self.shade)
    r:restore()
    r:drawPath(pth, self.steel)
    r:drawPath(pth, self.steelEdge)
    local eye = self.eyePath
    eye:reset()
    eye:moveTo(Vector.xy(5, 0))
    eye:lineTo(Vector.xy(15, 0))
    r:drawPath(eye, self.eye)
    local sh2 = self.shinePath
    sh2:reset()
    sh2:moveTo(Vector.xy(14, -1.2))
    sh2:lineTo(Vector.xy(L * 0.8, -0.6))
    r:drawPath(sh2, self.shine)
    r:restore()
end

-- No shader support: a flat panel hinged on its leading edge.
local function drawFlat(self: Cloth, r: Renderer, p: number, mirrored: boolean)
    local ox, oy, sw, sh = sheetRect(self)
    local wv = sw * (1 - easeSine(p))
    local x0 = if mirrored then ox + sw - wv else ox
    local pth = self.path
    pth:reset()
    pth:moveTo(Vector.xy(x0, oy))
    pth:lineTo(Vector.xy(x0 + wv, oy))
    pth:lineTo(Vector.xy(x0 + wv, oy + sh))
    pth:lineTo(Vector.xy(x0, oy + sh))
    pth:close()
    self.flat.color = if self.dir >= 0 then Color.rgb(0xCC, 0x70, 0x51) else Color.rgb(0xE9, 0xAC, 0xB2)
    r:drawPath(pth, self.flat)
end

function draw(self: Cloth, renderer: Renderer)
    local f = self.fold
    if f <= 0.001 or f >= 1.999 then
        return
    end
    -- one piecing per direction: stable through every fold, rapid taps and skips
    self.seed = if self.dir < 0 then 0.71 else 0.23
    local p, mirrored, u, landing = phase(self)
    if self.gpu and self.gc == nil then
        allocate(self)
    end
    local gc = self.gc
    if self.gpu and gc ~= nil and renderSheet(self, p, mirrored) then
        renderer:save()
        renderer:transform(Mat2D.withScale(1 / self.scale, 1 / self.scale))
        renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
        renderer:restore()
    else
        drawFlat(self, renderer, p, mirrored)
    end
    drawNeedle(self, renderer, p, mirrored, u, landing)
end

return function(): Node<Cloth>
    return {
        fold = 0,
        dir = 1,
        cam = 1,
        ctx = nil,
        size = Vector.xy(AW, AH),
        scale = RES,
        seed = 0.2,
        gpu = false,
        gc = nil,
        colorView = nil,
        msaaView = nil,
        depthView = nil,
        samples = 1,
        pSheet = nil,
        pShadow = nil,
        ubo = nil,
        group = nil,
        vbuf = nil,
        ibuf = nil,
        icount = 0,
        staging = buffer.create(96),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        path = Path.new(),
        thread = Path.new(),
        eyePath = Path.new(),
        shinePath = Path.new(),
        flat = Paint.with({ color = Color.rgb(0xCC, 0x70, 0x51), style = 'fill' }),
        steel = Paint.with({ color = Color.rgb(0xB4, 0xBE, 0xCC), style = 'fill' }),
        steelEdge = Paint.with({ color = Color.rgb(0x23, 0x3A, 0x5E), style = 'stroke', thickness = 1.3 }),
        eye = Paint.with({ color = Color.rgb(0x23, 0x3A, 0x5E), style = 'stroke', thickness = 1.6, cap = 'round' }),
        shine = Paint.with({ color = Color.rgba(255, 255, 255, 235), style = 'stroke', thickness = 1.4, cap = 'round' }),
        threadPaint = Paint.with({ color = Color.rgb(0xCC, 0x70, 0x51), style = 'stroke', thickness = 3.0, cap = 'round' }),
        shade = Paint.with({ color = Color.rgba(0x23, 0x3A, 0x5E, 95), style = 'fill' }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
