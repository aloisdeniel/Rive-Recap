--!strict
-- Stash 3D spring: a chrome coil spring rendered on the GPU (scripts/spring3d.wgsl).
--
-- A ScriptedDrawable whose origin is the centre of the spring's base; the coil
-- grows upward (toward negative y). The timelines key `height` (points, base to
-- top of the wire) to compress and release it, and `twist` so the coils wind as
-- they close, like a real spring. The keyed plate above is ordinary vector art
-- placed at -height. Without GPU scripting a vector zigzag of the same height
-- is drawn instead.

type Spring3D = {
    height: Input<number>,
    radius: Input<number>,
    wire: Input<number>,
    turns: Input<number>,
    twist: Input<number>,
    tilt: Input<number>,
    outline: Input<number>,
    mirror: Input<number>,
    maxH: Input<number>,
    res: Input<number>,
    msaa: Input<number>,
    steel: Input<Color>,
    ink: Input<Color>,
    gpu: boolean,
    canvas: GPUCanvas?,
    color: GPUTexture?,
    depth: GPUTexture?,
    pMain: GPUPipeline?,
    pLine: GPUPipeline?,
    group: GPUBindGroup?,
    lineGroup: GPUBindGroup?,
    ubo: GPUBuffer?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    halfW: number,
    top: number,
    bottom: number,
    pw: number,
    ph: number,
    lastKey: string,
    zig: Path,
    zigPaint: Paint,
    zigInk: Paint,
}

local SEG_T = 44 -- segments per turn
local SEG_V = 12
local UBO_SIZE = 80

local function buildMesh(self: Spring3D)
    local turns = math.max(2, math.floor(self.turns + 0.5))
    local rows = turns * SEG_T
    local cols = SEG_V + 1
    local nr = rows + 1
    local vdata = buffer.create(nr * cols * 8)
    local o = 0
    for r = 0, rows do
        for c = 0, SEG_V do
            buffer.writef32(vdata, o, r / rows)
            buffer.writef32(vdata, o + 4, c / SEG_V)
            o += 8
        end
    end
    local icount = rows * SEG_V * 6
    local idata = buffer.create(icount * 2)
    o = 0
    for r = 0, rows - 1 do
        for c = 0, SEG_V - 1 do
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
    self.vbuf = GPUBuffer.new({ size = nr * cols * 8, usage = 'vertex', data = vdata, immutable = true,
        label = 'stash spring grid' })
    self.ibuf = GPUBuffer.new({ size = icount * 2, usage = 'index', data = idata, immutable = true,
        label = 'stash spring index' })
    self.icount = icount
end

local function buildFallback(self: Spring3D)
    local p = Path.new()
    local turns = math.max(2, math.floor(self.turns + 0.5))
    local n = turns * 2
    local h = math.max(self.height, self.wire * 2 * turns)
    p:moveTo(Vector.xy(0, -self.wire))
    for i = 1, n do
        local x = if i % 2 == 1 then -self.radius else self.radius
        p:lineTo(Vector.xy(x, -self.wire - (h - 2 * self.wire) * i / (n + 1)))
    end
    p:lineTo(Vector.xy(0, -h + self.wire))
    self.zig = p
end

local function setup(self: Spring3D, context: Context)
    local sh = context:shader('scripts/spring3d')
    if sh == nil then
        return
    end
    buildMesh(self)
    local want = math.max(1, math.floor(self.msaa + 0.5))
    local samples = if want >= 4 and context:features().maxSamples >= 4 then 4 else 1
    local function pipe(outline: boolean): GPUPipeline
        return GPUPipeline.new({
            vertex = { module = sh, entryPoint = if outline then 'vs_outline' else 'vs_main' },
            fragment = { module = sh, entryPoint = if outline then 'fs_ink' else 'fs_main' },
            vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
            colorTargets = { { format = 'rgba8unorm' } },
            depthStencil = { format = 'depth32float', compare = 'less', write = true },
            -- the tube is wound the other way round from the coin's lathe, so its
            -- outward faces are the 'back' ones: cull those for the hull
            cullMode = if outline then 'back' else 'none',
            sampleCount = samples,
        })
    end
    local pm = pipe(false)
    local pl = pipe(true)
    self.pMain = pm
    self.pLine = pl
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'stash spring' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pm:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.lineGroup = GPUBindGroup.new({ layout = pl:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(1, self.res)
    self.k = k
    local pad = self.wire + self.outline + 6
    self.halfW = self.radius + pad
    self.top = -(self.maxH + pad + self.radius * 0.5)
    self.bottom = pad + self.radius * 0.5
    local pw = math.ceil(self.halfW * 2 * k / 8) * 8
    local ph = math.ceil((self.bottom - self.top) * k / 8) * 8
    self.pw = pw
    self.ph = ph
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    if samples > 1 then
        self.color = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = samples, label = 'stash spring msaa' })
    end
    self.depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = samples, label = 'stash spring depth' })
    self.gpu = true
end

function init(self: Spring3D, context: Context): boolean
    if self.gpu then
        return true
    end
    buildFallback(self)
    setup(self, context)
    return true
end

function update(self: Spring3D)
    buildFallback(self)
end

local function writeUniforms(self: Spring3D)
    local b = self.staging
    local s = Color.toFloat(self.steel)
    local n = Color.toFloat(self.ink)
    local turns = math.max(2, math.floor(self.turns + 0.5))
    local vals = {
        self.height, self.radius, self.wire, turns,
        self.twist, self.tilt, self.halfW, self.outline,
        self.top, self.bottom, 0, 1,
        s[1], s[2], s[3], self.mirror,
        n[1], n[2], n[3], 0,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
end

local function render(self: Spring3D, canvas: GPUCanvas)
    local ubo, pm, pl, group, lineGroup = self.ubo, self.pMain, self.pLine, self.group, self.lineGroup
    local vbuf, ibuf, depth = self.vbuf, self.ibuf, self.depth
    if ubo == nil or pm == nil or pl == nil or group == nil or lineGroup == nil or vbuf == nil
        or ibuf == nil or depth == nil then
        return
    end
    writeUniforms(self)
    ubo:write(self.staging)
    local pass: GPURenderPass
    local mc = self.color
    if mc ~= nil then
        pass = canvas:beginRenderPass({
            color = { { view = mc:view(), resolveTarget = canvas:colorView(), loadOp = 'clear',
                storeOp = 'discard', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'stash spring',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'stash spring',
        })
    end
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:setPipeline(pl)
    pass:setBindGroup(0, lineGroup)
    pass:drawIndexed(self.icount)
    pass:setPipeline(pm)
    pass:setBindGroup(0, group)
    pass:drawIndexed(self.icount)
    pass:finish()
end

function draw(self: Spring3D, renderer: Renderer)
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        self.zigInk.color = self.ink
        self.zigPaint.color = self.steel
        renderer:drawPath(self.zig, self.zigInk)
        renderer:drawPath(self.zig, self.zigPaint)
        return
    end
    local key = string.format('%.2f|%.3f|%.3f|%d', self.height, self.twist, self.tilt, self.steel)
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

return function(): Node<Spring3D>
    return {
        height = 90,
        radius = 34,
        wire = 6,
        turns = 6,
        twist = 0,
        tilt = 0.32,
        outline = 2.5,
        mirror = 0.85,
        maxH = 360,
        res = 2,
        msaa = 4,
        steel = Color.rgb(214, 226, 240),
        ink = Color.rgb(36, 27, 60),
        gpu = false,
        canvas = nil,
        color = nil,
        depth = nil,
        pMain = nil,
        pLine = nil,
        group = nil,
        lineGroup = nil,
        ubo = nil,
        vbuf = nil,
        ibuf = nil,
        icount = 0,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        halfW = 50,
        top = -400,
        bottom = 20,
        pw = 100,
        ph = 400,
        lastKey = '',
        zig = Path.new(),
        zigPaint = Paint.with({ color = Color.rgb(214, 226, 240), style = 'stroke', thickness = 6 }),
        zigInk = Paint.with({ color = Color.rgb(36, 27, 60), style = 'stroke', thickness = 11 }),
        init = init,
        update = update,
        draw = draw,
    }
end
