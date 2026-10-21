--!strict
-- Stash 3D glass jar (scripts/jar3d.wgsl): one wall of the motif's mint jar.
--
-- Two ScriptedDrawables use this script: `layer` 0 (the far wall, drawn behind
-- the coin pile) and `layer` 1 (the near wall, drawn in front of it). The node's
-- origin is the centre of the jar floor; the ink outline is ordinary vector art
-- traced from the same profile. The jar is static, so each layer renders once
-- and then costs one image draw; `sway` (keyed in idle loops) slides the
-- reflections, and re-renders only while it moves. Without GPU scripting a flat
-- tinted silhouette is drawn instead.

type Jar3D = {
    layer: Input<number>,
    strength: Input<number>,
    caustic: Input<number>,
    sway: Input<number>,
    res: Input<number>,
    glass: Input<Color>,
    edge: Input<Color>,
    gpu: boolean,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    halfW: number,
    top: number,
    bottom: number,
    lastKey: string,
    path: Path,
    paint: Paint,
}

local SEG_U = 64
local ROWS = 72
local UBO_SIZE = 64

local SHARED: { vbuf: GPUBuffer?, ibuf: GPUBuffer?, icount: number, pipe: GPUPipeline? } =
    { vbuf = nil, ibuf = nil, icount = 0, pipe = nil }

local function buildMesh()
    if SHARED.vbuf ~= nil then
        return
    end
    local cols = SEG_U + 1
    local nr = ROWS + 1
    local vdata = buffer.create(nr * cols * 8)
    local o = 0
    for r = 0, ROWS do
        for c = 0, SEG_U do
            buffer.writef32(vdata, o, c / SEG_U)
            buffer.writef32(vdata, o + 4, r / ROWS)
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
        label = 'stash jar grid' })
    SHARED.ibuf = GPUBuffer.new({ size = icount * 2, usage = 'index', data = idata, immutable = true,
        label = 'stash jar index' })
    SHARED.icount = icount
end

local function buildFallback(self: Jar3D)
    -- the silhouette: body 178 x 198 (46 corners) and the neck, floor at y = 0
    local p = Path.new()
    local r, rc, h = 89, 46, 198
    p:moveTo(Vector.xy(-r + rc, 0))
    p:lineTo(Vector.xy(r - rc, 0))
    p:quadTo(Vector.xy(r, 0), Vector.xy(r, -rc))
    p:lineTo(Vector.xy(r, -(h - rc)))
    p:quadTo(Vector.xy(r, -h), Vector.xy(r - rc, -h))
    p:lineTo(Vector.xy(64, -h))
    p:lineTo(Vector.xy(64, -217))
    p:lineTo(Vector.xy(-64, -217))
    p:lineTo(Vector.xy(-64, -h))
    p:lineTo(Vector.xy(-r + rc, -h))
    p:quadTo(Vector.xy(-r, -h), Vector.xy(-r, -(h - rc)))
    p:lineTo(Vector.xy(-r, -rc))
    p:quadTo(Vector.xy(-r, 0), Vector.xy(-r + rc, 0))
    p:close()
    self.path = p
end

local function setup(self: Jar3D, context: Context)
    local sh = context:shader('scripts/jar3d')
    if sh == nil then
        return
    end
    buildMesh()
    local pipe = SHARED.pipe
    if pipe == nil then
        pipe = GPUPipeline.new({
            vertex = { module = sh, entryPoint = 'vs_main' },
            fragment = { module = sh, entryPoint = 'fs_main' },
            vertexLayout = { { stride = 8, attributes = { { format = 'float32x2', slot = 0, offset = 0 } } } },
            -- premultiplied glass over glass: the near and far halves of each layer
            -- never overlap, but the shoulder folds over the neck
            colorTargets = { { format = 'rgba8unorm', blend = { srcColor = 'one', dstColor = 'one-minus-src-alpha',
                srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha' } } },
            cullMode = 'none',
        })
        SHARED.pipe = pipe
    end
    if pipe == nil then
        return
    end
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'stash jar' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(1, self.res)
    self.k = k
    self.halfW = 92
    self.top = -220
    self.bottom = 3
    local pw = math.ceil(self.halfW * 2 * k / 8) * 8
    local ph = math.ceil((self.bottom - self.top) * k / 8) * 8
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    self.gpu = true
end

function init(self: Jar3D, context: Context): boolean
    if self.gpu then
        return true
    end
    buildFallback(self)
    setup(self, context)
    return true
end

local function render(self: Jar3D, canvas: GPUCanvas)
    local ubo, pipe, group, vbuf, ibuf = self.ubo, self.pipe, self.group, SHARED.vbuf, SHARED.ibuf
    if ubo == nil or pipe == nil or group == nil or vbuf == nil or ibuf == nil then
        return
    end
    local g = Color.toFloat(self.glass)
    local e = Color.toFloat(self.edge)
    local vals = {
        self.layer, self.halfW, self.top, self.bottom,
        g[1], g[2], g[3], self.strength,
        e[1], e[2], e[3], self.caustic,
        self.sway, 1, 1, 0,
    }
    local b = self.staging
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = canvas:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'stash jar',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:drawIndexed(SHARED.icount)
    pass:finish()
end

function draw(self: Jar3D, renderer: Renderer)
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        local c = Color.toFloat(self.glass)
        self.paint.color = Color.rgba(math.floor(c[1] * 255), math.floor(c[2] * 255), math.floor(c[3] * 255),
            if self.layer > 0.5 then 70 else 110)
        renderer:drawPath(self.path, self.paint)
        return
    end
    local key = string.format('%.3f|%.3f|%d|%d', self.sway, self.strength, self.glass, self.edge)
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

return function(): Node<Jar3D>
    return {
        layer = 1,
        strength = 1,
        caustic = 0.6,
        sway = 0,
        res = 2,
        glass = Color.rgb(191, 244, 212),
        edge = Color.rgb(98, 196, 160),
        gpu = false,
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        halfW = 92,
        top = -220,
        bottom = 3,
        lastKey = '',
        path = Path.new(),
        paint = Paint.with({ color = Color.rgba(191, 244, 212, 90) }),
        init = init,
        draw = draw,
    }
end
