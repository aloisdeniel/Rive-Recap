--!strict
-- Crux chalk burst: a full-stage procedural chalk cloud (chalk.wgsl) that the scene
-- timelines key through ScriptInputs - amount, clear, origin, drift, seed, direction.
-- At amount 0 it issues no GPU work and draws nothing. Without GPU shaders it falls
-- back to a cluster of vector puffs with the same keyed amount.

type Chalk = {
    amount: Input<number>,
    clear: Input<number>,
    originX: Input<number>,
    originY: Input<number>,
    drift: Input<number>,
    seed: Input<number>,
    direction: Input<number>,
    width: Input<number>,
    height: Input<number>,
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

local RES = 1 -- the cloud is soft and grainy; 1 px per point is plenty

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
    self.canvas = context:gpuCanvas({ width = math.floor(self.width * RES), height = math.floor(self.height * RES) })
    self.gpu = true
    return true
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
    local canvas = self.canvas
    if not self.gpu or canvas == nil or self.pipe == nil or self.ubo == nil or self.group == nil then
        fallback(self, renderer)
        return
    end
    local b = self.staging
    local vals = {
        canvas.width, canvas.height, self.originX, self.originY,
        math.min(self.amount, 1.2), self.seed, self.drift, self.direction,
        0.945, 0.933, 0.906, 1,
        0.70, 0.68, 0.64, 1,
        math.clamp(self.clear, 0, 1.5), RES, 0, 0,
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
    renderer:transform(Mat2D.withScale(1 / RES, 1 / RES))
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
        width = 390,
        height = 844,
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
