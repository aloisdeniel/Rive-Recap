--!strict
-- Switchyard split-flap departure board (scripts/flapboard.wgsl): twelve real 3D
-- flap modules, rendered into a GPU canvas in this node's local space (top-left at
-- the node origin, `w` x `h` points). The timeline keys `roll` (0..1: every module
-- flips through `flips` characters, staggered, and lands on its month), the scene's
-- idle Joystick keys `idle` (occasional same-character ticks), and `active` is bound
-- to UserRecap.activeMonths so only months on the move are lit. `live` skips GPU work
-- while the scene is hidden; the canvas re-renders only when an input changed.
-- Without GPU shader support it draws flat vector tiles.

type Flap = {
    w: Input<number>,
    h: Input<number>,
    res: Input<number>,
    live: Input<number>,
    roll: Input<number>,
    idle: Input<number>,
    active: Input<number>,
    flips: Input<number>,
    pitch: Input<number>,
    gpu: boolean,
    samples: number,
    pw: number,
    ph: number,
    canvas: GPUCanvas?,
    msaaTex: GPUTexture?,
    depth: GPUTexture?,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    lastKey: string,
    fbPath: Path,
    fbPaint: Paint,
}

local COLS, ROWS = 4, 3
local TILE_W, TILE_H = 0.78, 0.58
local PITCH_X, PITCH_Y = 0.88, 0.66
local FOV = 0.42

local function buildFallback(self: Flap)
    local p = Path.new()
    local s = 100 -- points per world unit
    for i = 0, COLS * ROWS - 1 do
        local c, r = i % COLS, i // COLS
        local cx = self.w * 0.5 + (c - (COLS - 1) * 0.5) * PITCH_X * s
        local cy = self.h * 0.5 + (r - 1) * PITCH_Y * s
        local x0, y0 = cx - TILE_W * s * 0.5, cy - TILE_H * s * 0.5
        p:moveTo(Vector.xy(x0, y0))
        p:lineTo(Vector.xy(x0 + TILE_W * s, y0))
        p:lineTo(Vector.xy(x0 + TILE_W * s, y0 + TILE_H * s))
        p:lineTo(Vector.xy(x0, y0 + TILE_H * s))
        p:close()
    end
    self.fbPath = p
end

-- canvas size in device pixels; `res` (pixels per point) is bound to the layout so
-- the board renders at its real on-screen resolution, re-allocated when it changes
local function targetSize(self: Flap): (number, number, number)
    local k = math.clamp(self.res, 1, 4)
    local pw = math.max(16, math.ceil(self.w * k / 8) * 8)
    local ph = math.max(16, math.ceil(self.h * k / 8) * 8)
    return k, pw, ph
end

local function allocTargets(self: Flap, pw: number, ph: number)
    if self.samples > 1 then
        self.msaaTex = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = self.samples, label = 'flap msaa' })
    end
    self.depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = self.samples, label = 'flap depth' })
end

function init(self: Flap, context: Context): boolean
    if self.gpu then
        return true
    end
    buildFallback(self)
    local sh = context:shader('scripts/flapboard')
    if sh == nil then
        return true
    end
    local samples = if context:features().maxSamples >= 4 then 4 else 1
    self.pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {
            { stride = 12, attributes = { { format = 'float32x3', slot = 0, offset = 0 } } },
            { stride = 8, stepMode = 'instance', attributes = { { format = 'float32x2', slot = 1, offset = 0 } } },
        },
        colorTargets = { { format = 'rgba8unorm' } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = 'none',
        sampleCount = samples,
    })
    local ubo = GPUBuffer.new({ size = 112, usage = 'uniform', label = 'flapboard' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = (self.pipe :: GPUPipeline):getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } } })
    -- one module: three quads (top half, bottom half, flap); corners as (role, u, v)
    local corners = { { 0, 0 }, { 1, 0 }, { 1, 1 }, { 0, 0 }, { 1, 1 }, { 0, 1 } }
    local vdata = buffer.create(3 * 6 * 12)
    local o = 0
    for role = 0, 2 do
        for _, c in ipairs(corners) do
            buffer.writef32(vdata, o, role)
            buffer.writef32(vdata, o + 4, c[1])
            buffer.writef32(vdata, o + 8, c[2])
            o += 12
        end
    end
    self.vbuf = GPUBuffer.new({ size = 3 * 6 * 12, usage = 'vertex', data = vdata, immutable = true,
        label = 'flap module' })
    local idata = buffer.create(COLS * ROWS * 8)
    for i = 0, COLS * ROWS - 1 do
        buffer.writef32(idata, i * 8, i)
        buffer.writef32(idata, i * 8 + 4, 0)
    end
    self.ibuf = GPUBuffer.new({ size = COLS * ROWS * 8, usage = 'vertex', data = idata, immutable = true,
        label = 'flap instances' })
    self.samples = samples
    local k, pw, ph = targetSize(self)
    self.k, self.pw, self.ph = k, pw, ph
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    allocTargets(self, pw, ph)
    self.gpu = true
    return true
end

function advance(self: Flap, seconds: number): boolean
    return self.live >= 0.5
end

local function render(self: Flap, canvas: GPUCanvas)
    local pipe, ubo, group, vbuf, ibuf, depth = self.pipe, self.ubo, self.group, self.vbuf, self.ibuf, self.depth
    if pipe == nil or ubo == nil or group == nil or vbuf == nil or ibuf == nil or depth == nil then
        return
    end
    -- straight-on camera framing the board at 100 points per unit, board tipped back a touch
    local hUnits = self.h / 100
    local dist = (hUnits * 0.5) / math.tan(FOV * 0.5)
    local view = Mat4.lookAt(Vector.xyz(0, 0, dist), Vector.xyz(0, 0, 0), Vector.xyz(0, 1, 0))
    local proj = Mat4.perspective(FOV, self.w / math.max(1, self.h), 0.1, dist + 10)
    local vp = proj * view * Mat4.fromRotationX(-self.pitch)
    local b = self.staging
    vp:writeToBuffer(b, 0)
    local vals = {
        math.clamp(self.roll, 0, 1), self.idle - math.floor(self.idle), math.max(0, self.active), self.flips,
        TILE_W, TILE_H, COLS, 0.045,
        PITCH_X, PITCH_Y, 0, 0,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, 64 + (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass: GPURenderPass
    local mt = self.msaaTex
    if mt ~= nil then
        pass = canvas:beginRenderPass({
            color = { { view = mt:view(), resolveTarget = canvas:colorView(), loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'flapboard',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'flapboard',
        })
    end
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:setVertexBuffer(0, vbuf)
    pass:setVertexBuffer(1, ibuf)
    pass:draw(18, COLS * ROWS)
    pass:finish()
end

function draw(self: Flap, renderer: Renderer)
    if self.live < 0.5 then
        return
    end
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        renderer:drawPath(self.fbPath, self.fbPaint)
        return
    end
    local k, pw, ph = targetSize(self)
    if pw ~= self.pw or ph ~= self.ph then
        canvas:resize(pw, ph)
        allocTargets(self, pw, ph)
        self.pw, self.ph = pw, ph
        self.lastKey = ''
    end
    self.k = k
    local key = string.format('%.4f|%.4f|%.2f|%.2f|%.4f', self.roll, self.idle, self.active, self.flips, self.pitch)
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas)
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.k, 1 / self.k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Flap>
    return {
        w = 390,
        h = 240,
        res = 2,
        live = 1,
        roll = 1,
        idle = 0,
        active = 12,
        flips = 6,
        pitch = 0.12,
        gpu = false,
        samples = 1,
        pw = 0,
        ph = 0,
        canvas = nil,
        msaaTex = nil,
        depth = nil,
        pipe = nil,
        ubo = nil,
        group = nil,
        vbuf = nil,
        ibuf = nil,
        staging = buffer.create(112),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        lastKey = '',
        fbPath = Path.new(),
        fbPaint = Paint.with({ color = Color.rgb(0x2A, 0x30, 0x38) }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
