--!strict
-- Stash 3D coin: a gold toy coin lathed and lit on the GPU (scripts/coin3d.wgsl).
--
-- A ScriptedDrawable that sits where a vector coin would. Its node keeps the
-- keyed x / y / scale / opacity, so the state machine stages it like any other
-- drawable. The 3D pose comes in through ScriptInputs the timelines key:
--
--   size      diameter in points
--   yaw       spin about the coin's vertical axis (rad): a real flip
--   pitch     tilt toward / away from the viewer (rad)
--   roll      turn about the coin's own axis (rad); keyed instead of the node's
--             rotation so the light stays top-left
--   icon      0 star, 1 house, 2 graduation cap, 3 palm, 4 plain
--   thick     half thickness (object units, radius = 1)
--   shine     0 satin .. 1 mirror gold
--   outline   ink outline width in points
--   lightRoll counter-rotation for a node whose parent is rolled (rad)
--   gold, ink colours
--
-- The canvas re-renders only when an input changed, so a coin at rest costs one
-- image draw; static coins (the Coin component) render once. Without GPU
-- scripting (no shader) a flat vector coin with the same pose is drawn instead.

type Coin3D = {
    size: Input<number>,
    yaw: Input<number>,
    pitch: Input<number>,
    roll: Input<number>,
    icon: Input<number>,
    thick: Input<number>,
    shine: Input<number>,
    outline: Input<number>,
    lightRoll: Input<number>,
    res: Input<number>,
    msaa: Input<number>,
    gold: Input<Color>,
    ink: Input<Color>,
    -- runtime state
    gpu: boolean,
    canvas: GPUCanvas?,
    targets: Targets?,
    pMain: GPUPipeline?,
    pLine: GPUPipeline?,
    group: GPUBindGroup?,
    lineGroup: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    ext: number,
    px: number,
    samples: number,
    lastKey: string,
    -- fallback
    rimPath: Path,
    facePath: Path,
    rimPaint: Paint,
    facePaint: Paint,
    inkPaint: Paint,
}

type Targets = { color: GPUTexture?, depth: GPUTexture, samples: number }

local SEG_U = 72
local ROWS = 80
local UBO_SIZE = 64
local EXTENT = 1.16 -- canvas half width in coin radii (room for tilt and outline)

-- One lathe grid and one pipeline pair per sample count, shared by every coin in
-- the file; transient MSAA / depth targets are shared per pixel size.
local SHARED: {
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    pipes: { [string]: GPUPipeline },
    targets: { [string]: Targets },
} = { vbuf = nil, ibuf = nil, icount = 0, pipes = {}, targets = {} }

local function buildMesh()
    if SHARED.vbuf ~= nil then
        return
    end
    local cols = SEG_U + 1
    local nr = ROWS + 1
    local vdata = buffer.create(nr * cols * 8)
    local o = 0
    for r = 0, ROWS do
        local s = r / ROWS
        for c = 0, SEG_U do
            buffer.writef32(vdata, o, c / SEG_U)
            buffer.writef32(vdata, o + 4, s)
            o += 8
        end
    end
    local icount = ROWS * SEG_U * 6
    local idata = buffer.create(icount * 2)
    o = 0
    for r = 0, ROWS - 1 do
        for c = 0, SEG_U - 1 do
            local a = r * cols + c
            local d = a + cols
            buffer.writeu16(idata, o, a)
            buffer.writeu16(idata, o + 2, d)
            buffer.writeu16(idata, o + 4, a + 1)
            buffer.writeu16(idata, o + 6, a + 1)
            buffer.writeu16(idata, o + 8, d)
            buffer.writeu16(idata, o + 10, d + 1)
            o += 12
        end
    end
    SHARED.vbuf = GPUBuffer.new({ size = nr * cols * 8, usage = 'vertex', data = vdata, immutable = true,
        label = 'stash coin grid' })
    SHARED.ibuf = GPUBuffer.new({ size = icount * 2, usage = 'index', data = idata, immutable = true,
        label = 'stash coin index' })
    SHARED.icount = icount
end

local function pipeline(sh: Shader, samples: number, outline: boolean): GPUPipeline
    local key = (if outline then 'line' else 'main') .. tostring(samples)
    local p = SHARED.pipes[key]
    if p ~= nil then
        return p
    end
    local np = GPUPipeline.new({
        vertex = { module = sh, entryPoint = if outline then 'vs_outline' else 'vs_main' },
        fragment = { module = sh, entryPoint = if outline then 'fs_ink' else 'fs_main' },
        vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
        colorTargets = { { format = 'rgba8unorm' } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = if outline then 'front' else 'none',
        sampleCount = samples,
    })
    SHARED.pipes[key] = np
    return np
end

local function targets(px: number, samples: number): Targets
    local key = tostring(px) .. 'x' .. tostring(samples)
    local t = SHARED.targets[key]
    if t ~= nil then
        return t
    end
    local color: GPUTexture? = nil
    if samples > 1 then
        color = GPUTexture.new({ width = px, height = px, format = 'rgba8unorm', renderTarget = true,
            sampleCount = samples, label = 'stash coin msaa' })
    end
    local depth = GPUTexture.new({ width = px, height = px, format = 'depth32float', renderTarget = true,
        sampleCount = samples, label = 'stash coin depth' })
    local nt: Targets = { color = color, depth = depth, samples = samples }
    SHARED.targets[key] = nt
    return nt
end

-- ------------------------------------------------------------------ fallback

local function ellipsePath(p: Path, rx: number, ry: number, cy: number)
    local k = 0.5523
    p:moveTo(Vector.xy(0, cy - ry))
    p:cubicTo(Vector.xy(rx * k, cy - ry), Vector.xy(rx, cy - ry * k), Vector.xy(rx, cy))
    p:cubicTo(Vector.xy(rx, cy + ry * k), Vector.xy(rx * k, cy + ry), Vector.xy(0, cy + ry))
    p:cubicTo(Vector.xy(-rx * k, cy + ry), Vector.xy(-rx, cy + ry * k), Vector.xy(-rx, cy))
    p:cubicTo(Vector.xy(-rx, cy - ry * k), Vector.xy(-rx * k, cy - ry), Vector.xy(0, cy - ry))
    p:close()
end

local function buildFallback(self: Coin3D)
    local r = self.size * 0.5
    local sx = math.max(0.08, math.abs(math.cos(self.yaw)))
    local sy = math.max(0.08, math.abs(math.cos(self.pitch)))
    local rim = Path.new()
    ellipsePath(rim, r * sx, r * sy, 0)
    local face = Path.new()
    ellipsePath(face, r * 0.74 * sx, r * 0.74 * sy, 0)
    self.rimPath = rim
    self.facePath = face
end

-- ------------------------------------------------------------------ lifecycle

local function setup(self: Coin3D, context: Context)
    local sh = context:shader('scripts/coin3d')
    if sh == nil then
        return -- no GPU scripting on this runtime: the vector fallback draws
    end
    buildMesh()
    local want = math.max(1, math.floor(self.msaa + 0.5))
    local samples = if want >= 4 and context:features().maxSamples >= 4 then 4 else 1
    local pm = pipeline(sh, samples, false)
    local pl = pipeline(sh, samples, true)
    self.pMain = pm
    self.pLine = pl
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'stash coin' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pm:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.lineGroup = GPUBindGroup.new({ layout = pl:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(1, self.res)
    self.k = k
    -- the outline grows the silhouette, so the extent leaves room for it
    local ext = EXTENT + 2 * self.outline / math.max(1, self.size)
    self.ext = ext
    local px = math.ceil(self.size * ext * k / 8) * 8
    self.px = px
    self.canvas = context:gpuCanvas({ width = px, height = px })
    self.targets = targets(px, samples)
    self.samples = samples
    self.gpu = true
end

-- `res` (canvas pixels per point) is bound to the director's _gpuRes, which
-- follows the real on-screen scale (viewport x zone scale x device pixel ratio),
-- so the canvas is re-sized when the layout zooms the coin, not upscaled
local function applyRes(self: Coin3D)
    local canvas = self.canvas
    if canvas == nil then
        return
    end
    local k = math.clamp(self.res, 1, 4)
    if math.abs(k - self.k) < 0.01 then
        return
    end
    self.k = k
    local px = math.ceil(self.size * self.ext * k / 8) * 8
    if px ~= self.px then
        self.px = px
        canvas:resize(px, px)
        self.targets = targets(px, self.samples)
    end
    self.lastKey = ''
end

function init(self: Coin3D, context: Context): boolean
    if self.gpu then
        return true -- init can run more than once; build the GPU objects once
    end
    buildFallback(self)
    setup(self, context)
    return true
end

function update(self: Coin3D)
    buildFallback(self)
end

local function writeUniforms(self: Coin3D)
    local b = self.staging
    local g = Color.toFloat(self.gold)
    local n = Color.toFloat(self.ink)
    local r = self.size * 0.5
    local vals = {
        self.yaw, self.pitch, self.roll, self.ext,
        self.thick, self.icon, self.outline / math.max(1, r), 1,
        g[1], g[2], g[3], self.shine,
        n[1], n[2], n[3], self.lightRoll,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
end

local function render(self: Coin3D, canvas: GPUCanvas)
    local ubo = self.ubo
    local pm = self.pMain
    local pl = self.pLine
    local group = self.group
    local lineGroup = self.lineGroup
    local vbuf = SHARED.vbuf
    local ibuf = SHARED.ibuf
    local tg = self.targets
    if ubo == nil or pm == nil or pl == nil or group == nil or lineGroup == nil or vbuf == nil
        or ibuf == nil or tg == nil then
        return
    end
    writeUniforms(self)
    ubo:write(self.staging)
    local pass: GPURenderPass
    local mc = tg.color
    if mc ~= nil then
        pass = canvas:beginRenderPass({
            color = { { view = mc:view(), resolveTarget = canvas:colorView(), loadOp = 'clear',
                storeOp = 'discard', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = tg.depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'stash coin',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = tg.depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'stash coin',
        })
    end
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:setPipeline(pl)
    pass:setBindGroup(0, lineGroup)
    pass:drawIndexed(SHARED.icount)
    pass:setPipeline(pm)
    pass:setBindGroup(0, group)
    pass:drawIndexed(SHARED.icount)
    pass:finish()
end

local function stateKey(self: Coin3D): string
    return string.format('%.4f|%.4f|%.4f|%.2f|%.3f|%.3f|%.2f|%.3f|%d|%d',
        self.yaw, self.pitch, self.roll, self.icon, self.thick, self.shine, self.outline, self.lightRoll,
        self.gold, self.ink)
end

function draw(self: Coin3D, renderer: Renderer)
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        self.rimPaint.color = self.gold
        self.facePaint.color = Color.lerp(self.gold, Color.rgb(255, 240, 200), 0.35)
        self.inkPaint.color = self.ink
        renderer:drawPath(self.rimPath, self.rimPaint)
        renderer:drawPath(self.rimPath, self.inkPaint)
        renderer:drawPath(self.facePath, self.facePaint)
        return
    end
    applyRes(self)
    local key = stateKey(self)
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas)
    end
    local k = self.k
    local half = self.px / k * 0.5
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-half, -half) * Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Coin3D>
    return {
        size = 64,
        yaw = 0,
        pitch = 0.3,
        roll = 0,
        icon = 0,
        thick = 0.13,
        shine = 0.55,
        outline = 3,
        lightRoll = 0,
        res = 2,
        msaa = 4,
        gold = Color.rgb(255, 203, 92),
        ink = Color.rgb(36, 27, 60),
        gpu = false,
        canvas = nil,
        targets = nil,
        pMain = nil,
        pLine = nil,
        group = nil,
        lineGroup = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        ext = EXTENT,
        px = 128,
        samples = 1,
        lastKey = '',
        rimPath = Path.new(),
        facePath = Path.new(),
        rimPaint = Paint.with({ color = Color.rgb(255, 203, 92) }),
        facePaint = Paint.with({ color = Color.rgb(255, 231, 163) }),
        inkPaint = Paint.with({ color = Color.rgb(36, 27, 60), style = 'stroke', thickness = 3 }),
        init = init,
        update = update,
        draw = draw,
    }
end
