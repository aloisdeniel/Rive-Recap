--!strict
-- Kiln 3D vessel: a thrown pot, lathed and lit on the GPU (scripts/vessel3d.wgsl).
--
-- A ScriptedDrawable that sits where a vector vessel would. Its node keeps the
-- keyed x / y / scale / rotation / opacity, so the state machine stages it like
-- any other drawable. The 3D form comes in through ScriptInputs the timelines key:
--
--   h, r0..r5, c0..c5   the profile (height, radius and axis lean per row). Every
--                       form shares the six rows, so any two forms morph
--   cap                 0 open vessel .. 1 lidded (the clay slab, lump and orb)
--   dip, flow, bandW,   cobalt glaze: dipped rim depth, flowing band length,
--   bandAt, sway, drip  band half-width / centre / sway, drip fingers
--   inner               glazed interior
--   body, glaze         clay and glaze colours; `heat` makes the piece incandesce
--   rings, speck,       throwing rings, iron speckle, wet-clay sheen, coil ridges,
--   sheen, coils,       thumbprints, glaze gloss
--   prints, gloss
--   sphere              blends the profile into a true sphere (the orb)
--   tilt, roll          camera elevation; the node's own rotation (keeps the light fixed)
--   yaw, turn, turnGain base angle per scene + turntable phase (_turnPhase) x gain
--   scene               currentScreen: each scene starts from its authored angle
--   live                0 skips all GPU work (the node may be invisible but is still drawn)
--   zoom, dpr           the stage scale (_artScale) and the device pixel ratio (_dpr): the
--                       canvas follows the piece's real on-screen size, at device resolution
--                       (res is the floor in px per point; capped at 4 px per point)
--
-- The canvas re-renders only when an input or the angle changed, so a still pot
-- costs one image draw. Without GPU scripting (no shader) a flat vector silhouette
-- of the same profile is drawn instead.

type V3 = {
    h: Input<number>,
    r0: Input<number>,
    r1: Input<number>,
    r2: Input<number>,
    r3: Input<number>,
    r4: Input<number>,
    r5: Input<number>,
    c0: Input<number>,
    c1: Input<number>,
    c2: Input<number>,
    c3: Input<number>,
    c4: Input<number>,
    c5: Input<number>,
    cap: Input<number>,
    dip: Input<number>,
    flow: Input<number>,
    bandW: Input<number>,
    bandAt: Input<number>,
    sway: Input<number>,
    drip: Input<number>,
    inner: Input<number>,
    rings: Input<number>,
    speck: Input<number>,
    sheen: Input<number>,
    coils: Input<number>,
    prints: Input<number>,
    sphere: Input<number>,
    heat: Input<number>,
    gloss: Input<number>,
    tilt: Input<number>,
    roll: Input<number>,
    yaw: Input<number>,
    turn: Input<number>,
    turnGain: Input<number>,
    scene: Input<number>,
    live: Input<number>,
    seed: Input<number>,
    body: Input<Color>,
    glaze: Input<Color>,
    halfW: Input<number>,
    top: Input<number>,
    bottom: Input<number>,
    res: Input<number>,
    msaa: Input<number>,
    zoom: Input<number>,
    dpr: Input<number>,
    -- runtime state
    gpu: boolean,
    canvas: GPUCanvas?,
    targets: Targets?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    samples: number,
    targetKey: string,
    lastKey: string,
    lastScene: number,
    zero: number,
    zeroTarget: number,
    frames: number,
    -- fallback
    path: Path,
    bandPath: Path,
    bodyPaint: Paint,
    glazePaint: Paint,
}

type Targets = { color: GPUTexture?, depth: GPUTexture, samples: number }

local SEG_U = 72
local ROWS_OUT = 44
local ROWS_RIM = 4
local ROWS_IN = 30
local ROWS_FLOOR = 4
local UBO_SIZE = 176
local T = { 0.0, 0.2, 0.44, 0.68, 0.88, 1.0 }

-- One lathe grid, one pipeline per sample count, and transient render targets per
-- pixel size, shared by every vessel in the file: passes run one after another, each
-- clears, draws and resolves into its own canvas.
local SHARED: {
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    pipes: { [number]: GPUPipeline },
    targets: { [string]: Targets },
    uses: { [string]: number },
} = { vbuf = nil, ibuf = nil, icount = 0, pipes = {}, targets = {}, uses = {} }

local function buildMesh()
    if SHARED.vbuf ~= nil then
        return
    end
    local rows: { number } = {}
    for j = 0, ROWS_OUT do
        table.insert(rows, j / ROWS_OUT)
    end
    for j = 1, ROWS_RIM do
        table.insert(rows, 1 + 0.1 * j / ROWS_RIM)
    end
    for j = 1, ROWS_IN do
        table.insert(rows, 1.1 + j / ROWS_IN)
    end
    for j = 1, ROWS_FLOOR do
        table.insert(rows, 2.1 + 0.1 * j / ROWS_FLOOR)
    end
    local nr = #rows
    local cols = SEG_U + 1
    local vdata = buffer.create(nr * cols * 8)
    local o = 0
    for _, s in ipairs(rows) do
        for c = 0, SEG_U do
            buffer.writef32(vdata, o, c / SEG_U)
            buffer.writef32(vdata, o + 4, s)
            o += 8
        end
    end
    local icount = (nr - 1) * SEG_U * 6
    local idata = buffer.create(icount * 2)
    o = 0
    for r = 0, nr - 2 do
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
        label = 'kiln lathe grid' })
    SHARED.ibuf = GPUBuffer.new({ size = icount * 2, usage = 'index', data = idata, immutable = true,
        label = 'kiln lathe index' })
    SHARED.icount = icount
end

local function pipeline(sh: Shader, samples: number): GPUPipeline
    local p = SHARED.pipes[samples]
    if p ~= nil then
        return p
    end
    local np = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
        colorTargets = { { format = 'rgba8unorm' } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = 'none',
        sampleCount = samples,
    })
    SHARED.pipes[samples] = np
    return np
end

local function targetKey(pw: number, ph: number, samples: number): string
    return tostring(pw) .. 'x' .. tostring(ph) .. 'x' .. tostring(samples)
end

-- pieces of the same pixel size share one MSAA colour + depth set; a set nobody uses
-- any more (after a resize) is dropped
local function release(key: string)
    local n = (SHARED.uses[key] or 0) - 1
    if n <= 0 then
        SHARED.uses[key] = nil
        SHARED.targets[key] = nil
    else
        SHARED.uses[key] = n
    end
end

local function targets(pw: number, ph: number, samples: number): Targets
    local key = targetKey(pw, ph, samples)
    SHARED.uses[key] = (SHARED.uses[key] or 0) + 1
    local t = SHARED.targets[key]
    if t ~= nil then
        return t
    end
    local color: GPUTexture? = nil
    if samples > 1 then
        color = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = samples, label = 'kiln vessel msaa' })
    end
    local depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = samples, label = 'kiln vessel depth' })
    local nt: Targets = { color = color, depth = depth, samples = samples }
    SHARED.targets[key] = nt
    return nt
end

-- ------------------------------------------------------------------ fallback

local function interp(v: number, a: { number }): number
    local i = 1
    for k = 1, 5 do
        if v >= T[k] then
            i = k
        end
    end
    local t = math.clamp((v - T[i]) / (T[i + 1] - T[i]), 0, 1)
    local s = t * t * (3 - 2 * t)
    return a[i] + (a[i + 1] - a[i]) * s
end

local function buildFallback(self: V3)
    local R = { self.r0, self.r1, self.r2, self.r3, self.r4, self.r5 }
    local C = { self.c0, self.c1, self.c2, self.c3, self.c4, self.c5 }
    local p = Path.new()
    local n = 24
    -- clockwise on screen (up the left side, down the right): Rive's script paths
    -- fill with the clockwise rule, so the other winding would be a hole
    for j = 0, n do
        local v = j / n
        local pt = Vector.xy(interp(v, C) - interp(v, R), -self.h * v)
        if j == 0 then
            p:moveTo(pt)
        else
            p:lineTo(pt)
        end
    end
    for j = n, 0, -1 do
        local v = j / n
        p:lineTo(Vector.xy(interp(v, C) + interp(v, R), -self.h * v))
    end
    p:close()
    self.path = p
    local b = Path.new()
    local top = -self.h - 6
    if self.dip > 0.01 then
        local y = -self.h * (1 - math.min(1, self.dip))
        b:moveTo(Vector.xy(-200, top))
        b:lineTo(Vector.xy(200, top))
        b:lineTo(Vector.xy(200, y))
        b:lineTo(Vector.xy(-200, y))
        b:close()
    end
    if self.flow > 0.01 and self.bandW > 0.01 then
        local w = math.max(6, self.bandW * 40)
        local y0 = -self.h * (1 - math.min(1, self.flow))
        b:moveTo(Vector.xy(-w * 0.5, top))
        b:lineTo(Vector.xy(w * 0.9, top))
        b:lineTo(Vector.xy(w * 0.6, y0))
        b:lineTo(Vector.xy(-w * 0.7, y0))
        b:close()
    end
    self.bandPath = b
end

-- ------------------------------------------------------------------ resolution

-- px per point of the frame: the stage scale times the device pixel ratio (never under
-- `res`, the supersampling floor), in quarter steps so small resizes do not reallocate
local function pixelsPerPoint(self: V3): number
    local z = math.max(0.25, self.zoom)
    local d = math.max(1, self.dpr)
    local k = math.clamp(z * math.max(d, self.res), 1, 4)
    return math.floor(k * 4 + 0.5) / 4
end

local function canvasSize(self: V3, k: number): (number, number)
    local pw = math.ceil(self.halfW * 2 * k / 8) * 8
    local ph = math.ceil((self.bottom - self.top) * k / 8) * 8
    return pw, ph
end

-- ------------------------------------------------------------------ lifecycle

function init(self: V3, context: Context): boolean
    if self.gpu then
        return true -- init can run more than once; build the GPU objects once
    end
    buildFallback(self)
    local sh = context:shader('scripts/vessel3d')
    if sh == nil then
        return true -- no GPU scripting on this runtime: the vector fallback draws
    end
    buildMesh()
    local want = math.max(1, math.floor(self.msaa + 0.5))
    local samples = if want >= 4 and context:features().maxSamples >= 4 then 4 else 1
    local pipe = pipeline(sh, samples)
    self.pipe = pipe
    self.samples = samples
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'kiln vessel' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = pixelsPerPoint(self)
    self.k = k
    local pw, ph = canvasSize(self, k)
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    self.targets = targets(pw, ph, samples)
    self.targetKey = targetKey(pw, ph, samples)
    self.gpu = true
    return true
end

-- keep the canvas at the piece's real resolution when the stage is resized
local function fitCanvas(self: V3)
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        return
    end
    local k = pixelsPerPoint(self)
    if k == self.k then
        return
    end
    self.k = k
    local pw, ph = canvasSize(self, k)
    canvas:resize(pw, ph)
    release(self.targetKey)
    self.targets = targets(pw, ph, self.samples)
    self.targetKey = targetKey(pw, ph, self.samples)
    self.lastKey = '' -- re-render at the new size
end

function update(self: V3)
    buildFallback(self)
end

local function wrapHalf(x: number): number
    return x - math.floor(x + 0.5)
end

function advance(self: V3, seconds: number): boolean
    -- Each scene opens on its authored angle: the turntable phase at the moment the
    -- scene changes becomes the new zero. It is eased in over ~0.4 s, while the piece
    -- is still the rotation-free slab of the handoff, so the reset never reads as a jump.
    self.frames += 1
    if self.live >= 0.5 then
        fitCanvas(self)
    end
    if self.frames <= 3 then
        -- bound inputs land over the first frames: start exactly on the authored angle
        self.lastScene = self.scene
        self.zero = self.turn
        self.zeroTarget = self.turn
    elseif self.scene ~= self.lastScene then
        self.lastScene = self.scene
        self.zeroTarget = self.turn
    end
    local d = wrapHalf(self.zeroTarget - self.zero)
    if math.abs(d) > 1e-5 then
        self.zero = self.zero + d * (1 - math.exp(-math.min(seconds, 0.1) * 9))
    end
    return true
end

local function angle(self: V3): number
    return self.yaw + self.turnGain * wrapHalf(self.turn - self.zero) * math.pi * 2
end

local function writeUniforms(self: V3)
    local b = self.staging
    local c = Color.toFloat(self.body)
    local gcol = Color.toFloat(self.glaze)
    local vals = {
        self.r0, self.r1, self.r2, self.r3,
        self.r4, self.r5, self.h, self.cap,
        self.c0, self.c1, self.c2, self.c3,
        self.c4, self.c5, angle(self), self.tilt,
        c[1], c[2], c[3], self.speck,
        gcol[1], gcol[2], gcol[3], self.gloss,
        self.dip, self.flow, self.bandW, self.drip,
        self.inner, self.rings, self.heat, 5.0,
        self.halfW, self.top, self.bottom, 1,
        self.bandAt, self.sway, self.sphere, self.seed,
        self.roll, self.sheen, self.coils, self.prints,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
end

local function render(self: V3, canvas: GPUCanvas)
    local ubo = self.ubo
    local pipe = self.pipe
    local group = self.group
    local vbuf = SHARED.vbuf
    local ibuf = SHARED.ibuf
    local tg = self.targets
    if ubo == nil or pipe == nil or group == nil or vbuf == nil or ibuf == nil or tg == nil then
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
            label = 'kiln vessel',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = tg.depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'kiln vessel',
        })
    end
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:drawIndexed(SHARED.icount)
    pass:finish()
end

local function stateKey(self: V3): string
    return string.format(
        '%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.4f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%d|%d',
        self.h, self.r0, self.r1, self.r2, self.r3, self.r4, self.r5, self.c0, self.c1, self.c2, self.c3, self.c4,
        self.c5, self.cap + self.sphere * 7, self.dip, self.flow, self.bandW, self.bandAt, self.sway, self.drip, self.inner,
        self.heat, self.tilt, angle(self), self.roll, self.sheen, self.coils + self.prints * 10, self.rings, self.speck, self.gloss,
        self.body, self.glaze)
end

function draw(self: V3, renderer: Renderer)
    if self.live < 0.5 then
        return -- off-screen: no GPU work and nothing drawn
    end
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        self.bodyPaint.color = self.body
        self.glazePaint.color = self.glaze
        renderer:drawPath(self.path, self.bodyPaint)
        renderer:save()
        renderer:clipPath(self.path)
        renderer:drawPath(self.bandPath, self.glazePaint)
        renderer:restore()
        return
    end
    local key = stateKey(self)
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas)
    end
    local k = self.k
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-self.halfW, self.top) * Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<V3>
    return {
        h = 250,
        r0 = 46,
        r1 = 80,
        r2 = 92,
        r3 = 60,
        r4 = 32,
        r5 = 46,
        c0 = 0,
        c1 = 0,
        c2 = 0,
        c3 = 0,
        c4 = 0,
        c5 = 0,
        cap = 0,
        dip = 0,
        flow = 0,
        bandW = 0.4,
        bandAt = 1.5708,
        sway = 0.35,
        drip = 0.6,
        inner = 1,
        rings = 1,
        speck = 1,
        sheen = 0,
        coils = 0,
        prints = 0,
        sphere = 0,
        heat = 0,
        gloss = 1,
        tilt = 0.2,
        roll = 0,
        yaw = 0,
        turn = 0,
        turnGain = 1,
        scene = 1,
        live = 1,
        seed = 1,
        body = Color.rgb(239, 231, 220),
        glaze = Color.rgb(53, 71, 162),
        halfW = 150,
        top = -366,
        bottom = 34,
        res = 2,
        msaa = 4,
        zoom = 1,
        dpr = 1,
        gpu = false,
        canvas = nil,
        targets = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        samples = 1,
        targetKey = '',
        lastKey = '',
        lastScene = -1,
        zero = 0,
        zeroTarget = 0,
        frames = 0,
        path = Path.new(),
        bandPath = Path.new(),
        bodyPaint = Paint.with({ color = Color.rgb(239, 231, 220) }),
        glazePaint = Paint.with({ color = Color.rgb(53, 71, 162) }),
        init = init,
        update = update,
        advance = advance,
        draw = draw,
    }
end
