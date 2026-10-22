--!strict
-- Patchwork backdrop: the larger quilt seen around the scene patch while the
-- camera pulls back during a hand-off (shaders/backdrop.wgsl). It covers the
-- whole canvas at any size: `vw`/`vh`/`dpr` are bound to the stage script's
-- numbers. Rendered once per size at the device density (capped to a pixel
-- budget), then drawn as one image; nothing is drawn while `show` is 0 (the
-- Handoff timelines key it). Without shader support a flat indigo cloth fills
-- the margin instead, so the pull-back never shows a gap.

type Backdrop = {
    show: Input<number>,
    vw: Input<number>,
    vh: Input<number>,
    dpr: Input<number>,
    ctx: Context?,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    w: number,
    h: number,
    res: number,
    dirty: boolean,
    staging: buffer,
    sampler: ImageSampler,
    path: Path,
    flat: Paint,
}

local BUDGET = 3.6e6 -- max canvas pixels

function init(self: Backdrop, context: Context): boolean
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    local sh = context:shader('shaders/backdrop')
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
    local ubo = GPUBuffer.new({ size = 16, usage = 'uniform', label = 'backdrop' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    return true
end

function advance(self: Backdrop, seconds: number): boolean
    return self.show > 0.5
end

local function track(self: Backdrop)
    local w = if self.vw > 1 then self.vw else 390
    local h = if self.vh > 1 then self.vh else 844
    local res = math.max(self.dpr, 1)
    res = math.max(0.5, math.min(res, math.sqrt(BUDGET / (w * h))))
    if w ~= self.w or h ~= self.h or math.abs(res - self.res) > 0.01 then
        self.w = w
        self.h = h
        self.res = res
        self.gc = nil
        self.dirty = true
    end
end

function draw(self: Backdrop, renderer: Renderer)
    if self.show <= 0.5 then
        return
    end
    track(self)
    local ctx, pipe, ubo, group = self.ctx, self.pipe, self.ubo, self.group
    if ctx == nil or pipe == nil or ubo == nil or group == nil then
        -- no shader support: a flat binding-coloured cloth behind the patch
        local p = self.path
        p:reset()
        p:moveTo(Vector.xy(0, 0))
        p:lineTo(Vector.xy(self.w, 0))
        p:lineTo(Vector.xy(self.w, self.h))
        p:lineTo(Vector.xy(0, self.h))
        p:close()
        renderer:drawPath(p, self.flat)
        return
    end
    if self.gc == nil then
        self.gc = ctx:gpuCanvas({ width = math.ceil(self.w * self.res), height = math.ceil(self.h * self.res) })
    end
    local gc = self.gc
    if gc == nil then
        return
    end
    if self.dirty then
        self.dirty = false
        local b = self.staging
        buffer.writef32(b, 0, gc.width)
        buffer.writef32(b, 4, gc.height)
        buffer.writef32(b, 8, gc.width / self.w)
        buffer.writef32(b, 12, 0)
        ubo:write(b)
        local pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0.137, 0.227, 0.369, 1 } } },
            label = 'backdrop',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(6)
        pass:finish()
    end
    local k = gc.width / self.w
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Backdrop>
    return {
        show = 0,
        vw = 390,
        vh = 844,
        dpr = 1,
        ctx = nil,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        w = 0,
        h = 0,
        res = 0,
        dirty = true,
        staging = buffer.create(16),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        path = Path.new(),
        flat = Paint.with({ color = Color.rgb(0x23, 0x3A, 0x5E), style = 'fill' }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
