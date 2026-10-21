--!strict
-- Patchwork cloth ground: shaders/weave.wgsl rendered once per size (at the
-- presenting pixel density) and multiplied over the whole recap, so patches,
-- panels, type and buttons all sit on one woven cotton. Static: it never
-- animates, so reduced motion and pause need nothing, and an idle frame costs
-- one image draw. Runtimes without shaders skip it (the flat fills still read).

type Weave = {
    strength: Input<number>,
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

function init(self: Weave, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('shaders/weave')
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
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'weave' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    return true
end

function resize(self: Weave, size: Vector, scale: number)
    local sc = if scale > 0 then scale else 1
    if size.x == self.size.x and size.y == self.size.y and sc == self.scale and self.gc ~= nil then
        return
    end
    self.size = size
    self.scale = sc
    local ctx = self.ctx
    if ctx == nil or self.pipe == nil or size.x <= 0 or size.y <= 0 then
        return
    end
    self.gc = ctx:gpuCanvas({ width = math.ceil(size.x * sc), height = math.ceil(size.y * sc) })
    self.dirty = true
end

function advance(self: Weave, seconds: number): boolean
    return self.dirty
end

function draw(self: Weave, renderer: Renderer)
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        return
    end
    if self.dirty then
        self.dirty = false
        local s = self.strength
        local b = self.staging
        local vals = { gc.width, gc.height, self.scale, 7.3, 0.085 * s, 0.035 * s, 0.05 * s, 0.07 * s }
        for i, v in vals do
            buffer.writef32(b, (i - 1) * 4, v)
        end
        ubo:write(b)
        local pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 1, 1, 1, 1 } } },
            label = 'weave',
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

return function(context: Context): Layout<Weave>
    return {
        strength = 1,
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
