--!strict
-- Patchwork persona medallion: the quilted cushion behind the persona emblem
-- (shaders/medallion.wgsl), drawn centred on its node so the disc's keyed
-- pop-in, the 9 -> 10 carry and the card's 0.3 scale all still apply.
--
-- `light` (0..1) is keyed by the persona reveals: the light sweeps round the
-- cushion as the emblem arrives, then rests at 1. The canvas is re-rendered
-- only when `light` has moved visibly, so a settled medallion costs one image
-- draw. Reduced-motion reveals key light = 1 at once (static). Runtimes without
-- shaders draw nothing here and the vector disc underneath shows instead.
--
-- `res` (canvas pixels per point) is bound to the stage script: the device
-- density times the medallion's largest on-screen scale, so the cushion stays
-- sharp when a large canvas scales scene 9 up. The canvas is reallocated when
-- it changes.

type Medallion = {
    size: Input<number>,
    light: Input<number>,
    res: Input<number>,
    ctx: Context?,
    rpx: number,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    px: number,
    drawn: number,
    staging: buffer,
    sampler: ImageSampler,
}

local function resOf(self: Medallion): number
    return math.clamp(self.res, 1, 4)
end

local function allocate(self: Medallion)
    local ctx = self.ctx
    if ctx == nil then
        return
    end
    local r = resOf(self)
    local px = math.ceil((self.size + 4) * r)
    self.px = px
    self.rpx = r
    self.gc = ctx:gpuCanvas({ width = px, height = px })
    self.drawn = -1
end

function init(self: Medallion, context: Context): boolean
    if self.pipe ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('shaders/medallion')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 48, usage = 'uniform', label = 'medallion' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    allocate(self)
    return true
end

local function render(self: Medallion, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local t = math.clamp(self.light, 0, 1)
    local e = t * t * (3 - 2 * t)
    -- the light swings from low right, over the top, to rest at the upper left
    local az = math.rad(-20) + (math.rad(-128) - math.rad(-20)) * e
    local el = 0.55 + 0.25 * math.sin(math.pi * e)
    local lx, ly = math.cos(az) * 0.8, math.sin(az) * 0.8
    local b = self.staging
    local vals = {
        self.px, self.rpx, self.size, 4.2,
        lx, ly, el, 0.52,
        0.10 + 0.30 * math.sin(math.pi * e), 0.5, 0, 0,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'medallion',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(6)
    pass:finish()
end

function draw(self: Medallion, renderer: Renderer)
    if self.pipe ~= nil and math.abs(resOf(self) - self.rpx) > 0.05 then
        allocate(self)
    end
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        return
    end
    if self.drawn < 0 or math.abs(self.light - self.drawn) > 0.004 then
        self.drawn = self.light
        render(self, gc, pipe, ubo, group)
    end
    local r = self.rpx
    local half = self.px / r * 0.5
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-half, -half) * Mat2D.withScale(1 / r, 1 / r))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Medallion>
    return {
        size = 290,
        light = 1,
        res = 2,
        ctx = nil,
        rpx = 2,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        px = 1,
        drawn = -1,
        staging = buffer.create(48),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        init = init,
        draw = draw,
    }
end
