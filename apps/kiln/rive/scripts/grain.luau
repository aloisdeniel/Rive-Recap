--!strict
-- Matte mineral grain over the backgrounds (scripts/grain.wgsl). A fill-sized
-- ScriptedLayout at the back of the stage: the texture is rendered once per size,
-- then drawn every frame in soft-light at low opacity. Static, so reduced motion
-- needs nothing; without GPU scripting it simply draws nothing.

type Grain = {
    strength: Input<number>,
    ctx: Context?,
    size: Vector,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    dirty: boolean,
    k: number,
}

function init(self: Grain, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('scripts/grain')
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
    local ubo = GPUBuffer.new({ size = 16, usage = 'uniform', label = 'kiln grain' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.canvas = context:gpuCanvas()
    return true
end

-- the grain canvas covers the whole artboard at device resolution (up to 2x, and at
-- most ~8 million pixels on very large canvases); the pattern is defined in points, so
-- it looks the same at any resolution, only crisper
local MAX_PIXELS = 8000000

function resize(self: Grain, size: Vector, scale: number)
    self.size = size
    local c = self.canvas
    if c ~= nil and size.x > 0 and size.y > 0 then
        local k = math.clamp(if scale ~= nil then scale else 1, 1, 2)
        local area = size.x * size.y
        if area * k * k > MAX_PIXELS then
            k = math.max(1, math.sqrt(MAX_PIXELS / area))
        end
        self.k = k
        c:resize(math.ceil(size.x * k), math.ceil(size.y * k))
        self.dirty = true
    end
end

function advance(self: Grain, seconds: number): boolean
    return false
end

function draw(self: Grain, renderer: Renderer)
    local c = self.canvas
    local pipe = self.pipe
    local group = self.group
    local ubo = self.ubo
    if c == nil or pipe == nil or group == nil or ubo == nil or c.width <= 0 or self.strength <= 0 then
        return
    end
    if self.dirty then
        self.dirty = false
        local b = self.staging
        buffer.writef32(b, 0, c.width / self.k)
        buffer.writef32(b, 4, c.height / self.k)
        buffer.writef32(b, 8, 17.0)
        buffer.writef32(b, 12, 0)
        ubo:write(b)
        local pass = c:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0.5, 0.5, 0.5, 1 } } },
            label = 'kiln grain',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(3)
        pass:finish()
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.k, 1 / self.k))
    renderer:drawImage(c.image, self.sampler, 'softLight', self.strength)
    renderer:restore()
end

return function(context: Context): Layout<Grain>
    return {
        strength = 0.55,
        ctx = nil,
        size = Vector.xy(0, 0),
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(16),
        sampler = ImageSampler('clamp', 'clamp', 'nearest'),
        dirty = true,
        k = 1,
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
