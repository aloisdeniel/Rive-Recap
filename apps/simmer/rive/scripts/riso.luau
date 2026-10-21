--!strict
-- Simmer risograph stock (scripts/riso.wgsl). A fill-sized ScriptedLayout on
-- top of the whole recap: a paper tooth/fibre layer (multiply) and an ink
-- starvation layer (screen) are rendered once per size at the presenting pixel
-- density, then composited every frame as two image draws. Static: nothing
-- animates, so reduced motion and pause need nothing. Without GPU scripting it
-- draws nothing and the flat vector art still reads.

type Riso = {
    ctx: Context?,
    size: Vector,
    scale: number,
    pPaper: GPUPipeline?,
    pVoids: GPUPipeline?,
    ubo: GPUBuffer?,
    gPaper: GPUBindGroup?,
    gVoids: GPUBindGroup?,
    paper: GPUCanvas?,
    voids: GPUCanvas?,
    dirty: boolean,
    staging: buffer,
    sampler: ImageSampler,
}

function init(self: Riso, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('scripts/riso')
    if sh == nil then
        return true
    end
    local pPaper = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_paper' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local pVoids = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_voids' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'riso' })
    self.pPaper = pPaper
    self.pVoids = pVoids
    self.ubo = ubo
    self.gPaper = GPUBindGroup.new({ layout = pPaper:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.gVoids = GPUBindGroup.new({ layout = pVoids:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    return true
end

function resize(self: Riso, size: Vector, scale: number)
    self.size = size
    self.scale = if scale > 0 then scale else 1
    local ctx = self.ctx
    if ctx == nil or self.pPaper == nil or size.x <= 0 or size.y <= 0 then
        return
    end
    local w = math.ceil(size.x * self.scale)
    local h = math.ceil(size.y * self.scale)
    self.paper = ctx:gpuCanvas({ width = w, height = h })
    self.voids = ctx:gpuCanvas({ width = w, height = h })
    self.dirty = true
end

function advance(self: Riso, seconds: number): boolean
    return self.dirty
end

local function render(self: Riso, gc: GPUCanvas, pipe: GPUPipeline, group: GPUBindGroup, clear: number)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { clear, clear, clear, 1 } } },
        label = 'riso stock',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
end

function draw(self: Riso, renderer: Renderer)
    local paper, voids, ubo = self.paper, self.voids, self.ubo
    local pPaper, pVoids, gPaper, gVoids = self.pPaper, self.pVoids, self.gPaper, self.gVoids
    if paper == nil or voids == nil or ubo == nil or pPaper == nil or pVoids == nil or gPaper == nil or gVoids == nil then
        return
    end
    if self.dirty then
        self.dirty = false
        local b = self.staging
        -- size (px), px per point, seed | tooth, fibres, specks, voids
        local vals = { paper.width, paper.height, self.scale, 7.3, 0.045, 0.06, 0.16, 0.85 }
        for i, v in vals do
            buffer.writef32(b, (i - 1) * 4, v)
        end
        ubo:write(b)
        render(self, paper, pPaper, gPaper, 1)
        render(self, voids, pVoids, gVoids, 0)
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.scale, 1 / self.scale))
    renderer:drawImage(paper.image, self.sampler, 'multiply', 1)
    renderer:drawImage(voids.image, self.sampler, 'screen', 0.55)
    renderer:restore()
end

return function(context: Context): Layout<Riso>
    return {
        ctx = nil,
        size = Vector.xy(0, 0),
        scale = 1,
        pPaper = nil,
        pVoids = nil,
        ubo = nil,
        gPaper = nil,
        gVoids = nil,
        paper = nil,
        voids = nil,
        dirty = false,
        staging = buffer.create(32),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
