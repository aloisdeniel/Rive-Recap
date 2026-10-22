--!strict
-- Crux chalk burst: a full-stage procedural chalk cloud (chalk.wgsl) that the scene
-- timelines key through ScriptInputs - amount, clear, origin, drift, seed, direction.
-- At amount 0 it issues no GPU work and draws nothing. Without GPU shaders it falls
-- back to a cluster of vector puffs with the same keyed amount.
--
-- Responsive: the cloud lives in the carrier's space (its origin and drift are keyed
-- there, at the carrier pose), but its canvas always covers the whole real canvas.
-- `rigX` / `rigY` / `rigS` place this space in the stage viewport (scale `k`), so the
-- canvas rectangle is mapped back into local units; the canvas itself is sized in
-- device pixels (`vw` x `vh` x `dpr`, capped for memory).

type Chalk = {
    amount: Input<number>,
    clear: Input<number>,
    originX: Input<number>,
    originY: Input<number>,
    drift: Input<number>,
    seed: Input<number>,
    direction: Input<number>,
    rigX: Input<number>,
    rigY: Input<number>,
    rigS: Input<number>,
    k: Input<number>,
    vw: Input<number>,
    vh: Input<number>,
    dpr: Input<number>,
    ctx: Context?,
    allocKey: string,
    gpu: boolean,
    started: boolean,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    staging: buffer,
    sampler: ImageSampler,
    puffs: Path,
    puffPaint: Paint,
}

local MAX_PIXELS = 4200000 -- a 2048 x 2048 canvas: the cloud is soft, grain survives

function init(self: Chalk, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    local sh = context:shader('chalk')
    if sh == nil then
        return true
    end
    local blend: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm', blend = blend } },
    })
    local ubo = GPUBuffer.new({ size = 80, usage = 'uniform', label = 'chalk' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.ctx = context
    self.gpu = true
    return true
end

-- The canvas covers the real canvas in device pixels; reallocated only when that changes.
local function ensureCanvas(self: Chalk): GPUCanvas?
    local ctx = self.ctx
    if ctx == nil then
        return nil
    end
    local d = math.max(1, self.dpr)
    local f = 1
    if self.vw * self.vh * d * d > MAX_PIXELS then
        f = math.sqrt(MAX_PIXELS / (self.vw * self.vh * d * d))
    end
    local pw: number = math.max(16, math.floor(self.vw * d * f))
    local ph: number = math.max(16, math.floor(self.vh * d * f))
    local key = tostring(pw) .. 'x' .. tostring(ph)
    if self.canvas == nil or key ~= self.allocKey then
        self.allocKey = key
        self.canvas = ctx:gpuCanvas({ width = pw, height = ph })
    end
    return self.canvas
end

-- The canvas rectangle in this node's local (carrier) units: origin and size.
local function view(self: Chalk): (number, number, number, number)
    local s = math.max(1e-4, self.rigS)
    local k = math.max(1e-4, self.k)
    return -self.rigX / s, -self.rigY / s, self.vw / k / s, self.vh / k / s
end

local function fallback(self: Chalk, renderer: Renderer)
    local path = self.puffs
    path:reset()
    local amt = math.clamp(self.amount * 1.6 - self.clear, 0, 1.2)
    if amt <= 0 then
        return
    end
    local cx, cy = self.originX, self.originY
    for i = 0, 11 do
        local a = i / 12 * math.pi * 2 + self.seed
        local d = 140 + 60 * math.sin(i * 2.3 + self.seed)
        local r = (150 + 50 * math.cos(i * 1.7)) * amt
        local x = cx + math.cos(a) * d * amt
        local y = cy + math.sin(a) * d * 1.5 * amt - self.drift * self.direction
        path:moveTo(Vector.xy(x + r, y))
        for j = 1, 12 do
            local b = j / 12 * math.pi * 2
            path:lineTo(Vector.xy(x + math.cos(b) * r, y + math.sin(b) * r))
        end
        path:close()
    end
    renderer:drawPath(path, self.puffPaint)
end

function draw(self: Chalk, renderer: Renderer)
    if self.amount <= 0.001 then
        return -- nothing to draw: no pass, no composite
    end
    if self.gpu then
        ensureCanvas(self)
    end
    local canvas = self.canvas
    if not self.gpu or canvas == nil or self.pipe == nil or self.ubo == nil or self.group == nil then
        fallback(self, renderer)
        return
    end
    local vx, vy, vwLocal, _ = view(self)
    local res = canvas.width / vwLocal -- canvas pixels per local unit
    local b = self.staging
    local vals = {
        canvas.width, canvas.height, self.originX - vx, self.originY - vy,
        math.min(self.amount, 1.2), self.seed, self.drift, self.direction,
        0.945, 0.933, 0.906, 1,
        0.70, 0.68, 0.64, 1,
        math.clamp(self.clear, 0, 1.5), res, 0, 0,
    }
    for j = 1, 20 do
        buffer.writef32(b, (j - 1) * 4, vals[j])
    end
    (self.ubo :: GPUBuffer):write(b)
    local pass = canvas:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'chalk',
    })
    pass:setPipeline(self.pipe :: GPUPipeline)
    pass:setBindGroup(0, self.group :: GPUBindGroup)
    pass:draw(3)
    pass:finish()
    renderer:save()
    renderer:transform(Mat2D.withTranslation(vx, vy) * Mat2D.withScale(1 / res, 1 / res))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Chalk>
    return {
        amount = 0,
        clear = 0,
        originX = 195,
        originY = 500,
        drift = 0,
        seed = 1,
        direction = 1,
        rigX = 0,
        rigY = 0,
        rigS = 1,
        k = 1,
        vw = 390,
        vh = 844,
        dpr = 1,
        ctx = nil,
        allocKey = '',
        gpu = false,
        started = false,
        canvas = nil,
        pipe = nil,
        ubo = nil,
        group = nil,
        staging = buffer.create(80),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        puffs = Path.new(),
        puffPaint = Paint.with({ color = Color.rgb(241, 238, 231) }),
        init = init,
        draw = draw,
    }
end
