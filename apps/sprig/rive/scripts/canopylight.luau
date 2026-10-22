--!strict
-- Sprig paper stock + light through the canopy (scripts/canopylight.wgsl).
--
-- A ScriptedDrawable covering the artboard, drawn above the scenes and below the chrome:
--   * paper: a static fibre/tooth/mottle texture with a soft vignette, rendered once,
--     drawn in soft-light at `paper` strength (replaces a 580 KB raster grain);
--   * dapple: light falling through leaves, rendered at low resolution (it is soft by
--     nature) and drawn in overlay at `dapple` strength, which each scene keys.
-- The dapple drifts only while motion is allowed: `still` (reducedMotion), `paused`
-- (isPaused) and `held` (_holdPaused) freeze it, and a frozen pattern is not re-rendered.
-- Without GPU scripting nothing is drawn and the flat paper colours show.
--
-- Responsive: `w`/`h` are bound to the artboard's real size and `dpr` to the device pixel ratio
-- (scripts/viewport.luau publishes both). When they change the canvases are resized (the paper at
-- device resolution, capped at 4096 px) and the paper is rendered again, so it always covers the
-- whole viewport edge to edge.

type Light = {
    w: Input<number>,
    h: Input<number>,
    dpr: Input<number>,
    paperRes: Input<number>,
    lightRes: Input<number>,
    paper: Input<number>,
    dapple: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    held: Input<boolean>,
    seed: Input<number>,
    dirX: Input<number>,
    dirY: Input<number>,
    scale: Input<number>,
    sway: Input<number>,
    -- runtime
    gpu: boolean,
    paperCanvas: GPUCanvas?,
    lightCanvas: GPUCanvas?,
    paperPipe: GPUPipeline?,
    lightPipe: GPUPipeline?,
    paperGroup: GPUBindGroup?,
    lightGroup: GPUBindGroup?,
    paperUbo: GPUBuffer?,
    lightUbo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    t: number,
    paperDone: boolean,
    lastLight: string,
    sizeKey: string,
}

local function paperK(self: Light): number
    local big = math.max(1, self.w, self.h)
    return math.max(0.25, math.min(math.max(self.paperRes, self.dpr), 4096 / big))
end

local function lightK(self: Light): number
    local big = math.max(1, self.w, self.h)
    return math.max(0.05, math.min(self.lightRes, 1024 / big))
end

-- canvases follow the real size: resize them (and re-render the paper) when w / h / dpr change
local function fitCanvases(self: Light)
    local pc, lc = self.paperCanvas, self.lightCanvas
    if pc == nil or lc == nil then
        return
    end
    local pk, lk = paperK(self), lightK(self)
    local pw, ph = math.max(1, math.ceil(self.w * pk)), math.max(1, math.ceil(self.h * pk))
    local lw, lh = math.max(1, math.ceil(self.w * lk)), math.max(1, math.ceil(self.h * lk))
    local key = string.format('%d|%d|%d|%d', pw, ph, lw, lh)
    if key == self.sizeKey then
        return
    end
    self.sizeKey = key
    if pc.width ~= pw or pc.height ~= ph then
        pc:resize(pw, ph)
        self.paperDone = false
    end
    if lc.width ~= lw or lc.height ~= lh then
        lc:resize(lw, lh)
        self.lastLight = ''
    end
end

local function makePipe(sh: Shader, entry: string): GPUPipeline
    return GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = entry },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
end

function init(self: Light, context: Context): boolean
    if self.gpu then
        return true
    end
    local sh = context:shader('scripts/canopylight')
    if sh == nil then
        return true
    end
    local pp = makePipe(sh, 'fs_paper')
    local lp = makePipe(sh, 'fs_light')
    self.paperPipe = pp
    self.lightPipe = lp
    local pu = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'sprig paper' })
    local lu = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'sprig canopy light' })
    self.paperUbo = pu
    self.lightUbo = lu
    self.paperGroup = GPUBindGroup.new({ layout = pp:getBindGroupLayout(0), ubos = { { slot = 0, buffer = pu } } })
    self.lightGroup = GPUBindGroup.new({ layout = lp:getBindGroupLayout(0), ubos = { { slot = 0, buffer = lu } } })
    local pk, lk = paperK(self), lightK(self)
    self.paperCanvas = context:gpuCanvas({ width = math.ceil(self.w * pk), height = math.ceil(self.h * pk) })
    self.lightCanvas = context:gpuCanvas({ width = math.ceil(self.w * lk), height = math.ceil(self.h * lk) })
    self.gpu = true
    fitCanvases(self)
    return true
end

function update(self: Light)
    fitCanvases(self)
end

function advance(self: Light, seconds: number): boolean
    if self.dapple > 0.005 and not self.still and not self.paused and not self.held then
        self.t += math.min(seconds, 0.1)
        return true
    end
    return false
end

local function writeU(self: Light, ubo: GPUBuffer, c: GPUCanvas, time: number)
    local b = self.staging
    buffer.writef32(b, 0, c.width)
    buffer.writef32(b, 4, c.height)
    buffer.writef32(b, 8, time)
    buffer.writef32(b, 12, self.seed)
    buffer.writef32(b, 16, self.dirX)
    buffer.writef32(b, 20, self.dirY)
    buffer.writef32(b, 24, self.scale)
    buffer.writef32(b, 28, self.sway)
    ubo:write(b)
end

local function pass(c: GPUCanvas, pipe: GPUPipeline, group: GPUBindGroup, label: string)
    local p = c:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0.5, 0.5, 0.5, 1 } } },
        label = label,
    })
    p:setPipeline(pipe)
    p:setBindGroup(0, group)
    p:draw(3)
    p:finish()
end

function draw(self: Light, renderer: Renderer)
    if not self.gpu then
        return
    end
    local pc, lc = self.paperCanvas, self.lightCanvas
    local pp, lp = self.paperPipe, self.lightPipe
    local pg, lg = self.paperGroup, self.lightGroup
    local pu, lu = self.paperUbo, self.lightUbo
    if pc == nil or lc == nil or pp == nil or lp == nil or pg == nil or lg == nil or pu == nil or lu == nil then
        return
    end
    if self.dapple > 0.005 then
        local key = string.format('%.4f|%.2f|%.2f|%.3f|%.3f', self.t, self.dirX, self.dirY, self.scale, self.sway)
        if key ~= self.lastLight then
            self.lastLight = key
            writeU(self, lu, lc, self.t)
            pass(lc, lp, lg, 'sprig canopy light')
        end
        renderer:save()
        renderer:transform(Mat2D.withScale(self.w / lc.width, self.h / lc.height))
        renderer:drawImage(lc.image, self.sampler, 'overlay', math.clamp(self.dapple, 0, 1))
        renderer:restore()
    end
    if self.paper > 0.005 then
        if not self.paperDone then
            self.paperDone = true
            writeU(self, pu, pc, 0)
            pass(pc, pp, pg, 'sprig paper')
        end
        renderer:save()
        renderer:transform(Mat2D.withScale(self.w / pc.width, self.h / pc.height))
        renderer:drawImage(pc.image, self.sampler, 'softLight', math.clamp(self.paper, 0, 1))
        renderer:restore()
    end
end

return function(): Node<Light>
    return {
        w = 390,
        h = 844,
        dpr = 1,
        paperRes = 1.5,
        lightRes = 0.34,
        paper = 0.6,
        dapple = 0,
        still = false,
        paused = false,
        held = false,
        seed = 3,
        dirX = -0.6,
        dirY = -0.8,
        scale = 1,
        sway = 1,
        gpu = false,
        paperCanvas = nil,
        lightCanvas = nil,
        paperPipe = nil,
        lightPipe = nil,
        paperGroup = nil,
        lightGroup = nil,
        paperUbo = nil,
        lightUbo = nil,
        staging = buffer.create(32),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        t = 0,
        paperDone = false,
        lastLight = '',
        sizeKey = '',
        init = init,
        update = update,
        advance = advance,
        draw = draw,
    }
end
