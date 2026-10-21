--!strict
-- Simmer intro: steam that becomes the wordmark (scripts/letters.wgsl).
--
-- A ScriptedDrawable in scene 1, over the band between the period ticket and
-- the pot. The wordmark artboard (`mask`, the same "Simmer" lettering as the
-- vector wordmark beneath) is rendered once into a canvas and handed to the
-- shader as the target the steam condenses into, so the steam forms the real
-- glyphs. Scene 1's entrance keys `progress`; the vector wordmark fades in
-- under the steam letters and is uncovered as they evaporate.
--
-- Reduced motion: the reduced entrance holds `progress` at 1, which draws
-- nothing (the settled vector wordmark is all that shows). Pause freezes the
-- scene timeline and so the steam. No GPU scripting: nothing is drawn and the
-- wordmark simply fades in.

type Letters = {
    progress: Input<number>,
    mask: Input<Artboard>,
    started: boolean,
    inst: Artboard?,
    cv: Canvas?,
    gc: GPUCanvas?,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    maskDirty: boolean,
    staging: buffer,
    sampler: ImageSampler,
}

local RW, RH = 390, 360 -- region size (points), matches the mask artboard
local LID_X, LID_Y = 195, 262 -- pot lid in region points (scene 1 pose)
local RES = 2 -- px per point: the letters must stay crisp

function init(self: Letters, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    local inst = self.mask:instance()
    inst:advance(0)
    self.inst = inst
    local sh = context:shader('scripts/letters')
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
    local cv = context:canvas({ width = RW * RES, height = RH * RES })
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'letters' })
    self.pipe = pipe
    self.ubo = ubo
    self.cv = cv
    self.gc = context:gpuCanvas({ width = RW * RES, height = RH * RES })
    self.group = GPUBindGroup.new({
        layout = pipe:getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } },
        textures = { { slot = 1, view = cv.image:view() } },
        samplers = { { slot = 2, sampler = GPUSampler.new({ min = 'linear', mag = 'linear', mipmap = 'nearest' }) } },
    })
    return true
end

function advance(self: Letters, seconds: number): boolean
    return self.progress > 0 and self.progress < 1
end

function draw(self: Letters, renderer: Renderer)
    local p = self.progress
    if p <= 0.001 or p >= 0.999 then
        return
    end
    local cv, gc, pipe, ubo, group, inst = self.cv, self.gc, self.pipe, self.ubo, self.group, self.inst
    if cv == nil or gc == nil or pipe == nil or ubo == nil or group == nil or inst == nil then
        return
    end
    if self.maskDirty then
        self.maskDirty = false
        local r = cv:beginFrame()
        r:save()
        r:transform(Mat2D.withScale(RES, RES))
        inst:draw(r)
        r:restore()
        cv:endFrame()
    end
    local b = self.staging
    local vals = { gc.width, gc.height, RES, p, RW, RH, LID_X, LID_Y }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'steam letters',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / RES, 1 / RES))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Letters>
    return {
        progress = 0,
        mask = late(),
        started = false,
        inst = nil,
        cv = nil,
        gc = nil,
        pipe = nil,
        ubo = nil,
        group = nil,
        maskDirty = true,
        staging = buffer.create(32),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        init = init,
        advance = advance,
        draw = draw,
    }
end
