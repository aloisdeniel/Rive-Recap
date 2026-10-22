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
--
-- Responsive: the drawable lives in scene 1's art group, which the layout
-- scales by s (scripts/stage.luau). The canvases are re-allocated at 2 px per
-- *stage* point (2 x s per region point, up to 5) so the letters stay crisp
-- when the art is drawn larger than the master.

local stage = require('scripts/stage')

type Letters = {
    progress: Input<number>,
    mask: Input<Artboard>,
    started: boolean,
    ctx: Context?,
    vm: ViewModel?,
    res: number,
    lastW: number,
    lastH: number,
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
local BASE_RES = 2 -- px per stage point: the letters must stay crisp

local function allocate(self: Letters, res: number)
    local ctx, pipe, ubo = self.ctx, self.pipe, self.ubo
    if ctx == nil or pipe == nil or ubo == nil then
        return
    end
    self.res = res
    local w, h = math.ceil(RW * res), math.ceil(RH * res)
    local cv = ctx:canvas({ width = w, height = h })
    self.cv = cv
    self.gc = ctx:gpuCanvas({ width = w, height = h })
    self.group = GPUBindGroup.new({
        layout = pipe:getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } },
        textures = { { slot = 1, view = cv.image:view() } },
        samplers = { { slot = 2, sampler = GPUSampler.new({ min = 'linear', mag = 'linear', mipmap = 'nearest' }) } },
    })
    self.maskDirty = true
end

-- resolution for the current stage: scene 1's art scale x 2 px per point
local function wantedRes(self: Letters): number
    local slots = stage.fromModel(self.vm)
    if slots == nil then
        return BASE_RES
    end
    local _, _, sc = stage.frame(slots, '1')
    return math.clamp(math.ceil(BASE_RES * sc * 2) / 2, BASE_RES, 5)
end

function init(self: Letters, context: Context): boolean
    if self.vm == nil then
        self.vm = context:viewModel()
    end
    if self.started then
        return true
    end
    self.started = true
    self.ctx = context
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
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'letters' })
    self.pipe = pipe
    self.ubo = ubo
    allocate(self, wantedRes(self))
    return true
end

function advance(self: Letters, seconds: number): boolean
    local active = self.progress > 0 and self.progress < 1
    if active and self.pipe ~= nil then
        -- follow a resize: re-allocate only when the stage size actually changed
        local vm = self.vm
        local wp = if vm ~= nil then vm:getNumber('stageWidth') else nil
        local hp = if vm ~= nil then vm:getNumber('stageHeight') else nil
        local w = if wp ~= nil then wp.value else 390
        local h = if hp ~= nil then hp.value else 844
        if w ~= self.lastW or h ~= self.lastH then
            self.lastW, self.lastH = w, h
            local res = wantedRes(self)
            if res ~= self.res then
                allocate(self, res)
            end
        end
    end
    return active
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
        r:transform(Mat2D.withScale(self.res, self.res))
        inst:draw(r)
        r:restore()
        cv:endFrame()
    end
    local b = self.staging
    local vals = { gc.width, gc.height, self.res, p, RW, RH, LID_X, LID_Y }
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
    renderer:transform(Mat2D.withScale(1 / self.res, 1 / self.res))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Letters>
    return {
        progress = 0,
        mask = late(),
        started = false,
        ctx = nil,
        vm = nil,
        res = BASE_RES,
        lastW = 390,
        lastH = 844,
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
