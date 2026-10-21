--!strict
-- Switchyard print stock (scripts/paper.wgsl). A fill-sized ScriptedLayout drawn on
-- top of the whole recap: the texture is rendered once per size (at the device's
-- pixel density) and then drawn every frame in soft-light. It is static, so pause
-- and reduced motion need nothing; without GPU scripting it draws nothing.

type Paper = {
    strength: Input<number>,
    size: Vector,
    scale: number,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    dirty: boolean,
}

function init(self: Paper, context: Context): boolean
    if self.pipe ~= nil then
        return true
    end
    local sh = context:shader('scripts/paper')
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
    local ubo = GPUBuffer.new({ size = 16, usage = 'uniform', label = 'paper' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.canvas = context:gpuCanvas()
    return true
end

function resize(self: Paper, size: Vector, scale: number)
    self.size = size
    self.scale = math.clamp(scale, 1, 3)
    local c = self.canvas
    if c ~= nil and size.x > 0 and size.y > 0 then
        c:resize(math.ceil(size.x * self.scale), math.ceil(size.y * self.scale))
        self.dirty = true
    end
end

function advance(self: Paper, seconds: number): boolean
    return false
end

function draw(self: Paper, renderer: Renderer)
    local c = self.canvas
    local pipe, group, ubo = self.pipe, self.group, self.ubo
    if c == nil or pipe == nil or group == nil or ubo == nil or c.width <= 0 or self.strength <= 0 then
        return
    end
    if self.dirty then
        self.dirty = false
        local b = self.staging
        buffer.writef32(b, 0, c.width)
        buffer.writef32(b, 4, c.height)
        buffer.writef32(b, 8, self.scale)
        buffer.writef32(b, 12, 31.0)
        ubo:write(b)
        local pass = c:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0.5, 0.5, 0.5, 1 } } },
            label = 'paper',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(3)
        pass:finish()
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.scale, 1 / self.scale))
    renderer:drawImage(c.image, self.sampler, 'softLight', self.strength)
    renderer:restore()
end

return function(context: Context): Layout<Paper>
    return {
        strength = 0.6,
        size = Vector.xy(0, 0),
        scale = 1,
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(16),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        dirty = true,
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
