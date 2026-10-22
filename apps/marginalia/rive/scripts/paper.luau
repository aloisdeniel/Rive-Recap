--!strict
-- Marginalia paper grain: a laid-paper texture rendered once on the GPU (at the
-- presenting pixel density) and multiplied over the whole recap, so pages,
-- type and chrome all sit on the same tactile stock. Static: it never animates,
-- so it needs no reduced-motion handling and costs one image draw per frame.
-- Runtimes without shaders simply skip it (the parchment fills still read).

type Paper = {
    ctx: Context?,
    size: Vector,
    scale: number,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    dirty: boolean,
    staging: buffer,
    sampler: ImageSampler,
}

function init(self: Paper, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('shaders/paper')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'paper' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    return true
end

function resize(self: Paper, size: Vector, scale: number)
    self.size = size
    -- device resolution, within an 8 MP budget on very large canvases (the
    -- grain is soft; it is generated once per resize)
    local sc = if scale > 0 then scale else 1
    if size.x > 0 and size.y > 0 then
        sc = math.min(sc, math.sqrt(8e6 / (size.x * size.y)))
    end
    self.scale = sc
    local ctx = self.ctx
    if ctx == nil or self.pipe == nil or size.x <= 0 or size.y <= 0 then
        return
    end
    self.gc = ctx:gpuCanvas({ width = math.ceil(size.x * self.scale), height = math.ceil(size.y * self.scale) })
    self.dirty = true
end

function advance(self: Paper, seconds: number): boolean
    return self.dirty
end

function draw(self: Paper, renderer: Renderer)
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        return
    end
    if self.dirty then
        self.dirty = false
        local b = self.staging
        local vals = { gc.width, gc.height, self.scale, 13.7, 0.028, 0.010, 0.10, 0.07 }
        for i, v in vals do
            buffer.writef32(b, (i - 1) * 4, v)
        end
        ubo:write(b)
        local pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 1, 1, 1, 1 } } },
            label = 'paper',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(6)
        pass:finish()
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.scale, 1 / self.scale))
    renderer:drawImage(gc.image, self.sampler, 'multiply', 1)
    renderer:restore()
end

return function(context: Context): Layout<Paper>
    return {
        ctx = nil,
        size = Vector.xy(0, 0),
        scale = 1,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        dirty = false,
        staging = buffer.create(32),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
