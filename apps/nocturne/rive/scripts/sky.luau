--!strict
-- Nocturne sky (shaders/sky.wgsl) as a ScriptedDrawable.
--
-- mode 0: the full-stage background, drawn from (0, 0) to (width, height);
--         width and height are bound to the laid-out artboard size, so the sky
--         bleeds edge to edge at any canvas size.
-- mode 1: a luminous sky disk centred on (cx, cy) with `radius`.
--
-- Every look and camera value is a script input, so scene and pose timelines
-- key them like any other property (the camera moves with the motif poses).
-- The canvas is re-rendered only when an input changed, or for the twinkle at
-- most 30 times a second while `live` and neither `still` (reduced motion) nor
-- `paused`. Otherwise the last image is drawn again. Without shader support the
-- background draws nothing (the vector gradient below shows) and a disk falls
-- back to a flat vector disk.

type Sky = {
    mode: Input<number>,
    width: Input<number>,
    height: Input<number>,
    cx: Input<number>,
    cy: Input<number>,
    radius: Input<number>,
    edge: Input<number>,
    viewX: Input<number>,
    viewY: Input<number>,
    viewScale: Input<number>,
    viewRot: Input<number>,
    density: Input<number>,
    band: Input<number>,
    twinkle: Input<number>,
    bandAngle: Input<number>,
    bandWidth: Input<number>,
    warm: Input<number>,
    vignette: Input<number>,
    exposure: Input<number>,
    seed: Input<number>,
    res: Input<number>,
    live: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    holding: Input<boolean>,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    started: boolean,
    time: number,
    sinceRender: number,
    sig: number,
    rendered: boolean,
    ox: number,
    oy: number,
    cw: number,
    ch: number,
    staging: buffer,
    sampler: ImageSampler,
    disc: Path,
    discPaint: Paint,
}

local MAX_PX = 4096

local function rect(self: Sky): (number, number, number, number)
    if self.mode < 0.5 then
        return 0, 0, math.max(1, self.width), math.max(1, self.height)
    end
    local r = self.radius + 2
    return self.cx - r, self.cy - r, r * 2, r * 2
end

-- canvas pixels for the current box and density (`res` = device px per point)
local function canvasSize(self: Sky): (number, number)
    local _, _, w, h = rect(self)
    local res = math.clamp(self.res, 0.5, 4)
    local k = math.min(1, MAX_PX / math.max(w * res, h * res))
    return math.max(1, math.ceil(w * res * k)), math.max(1, math.ceil(h * res * k))
end

function init(self: Sky, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    local sh = context:shader('shaders/sky')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 96, usage = 'uniform', label = 'nocturne sky' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local ox, oy = rect(self)
    self.ox, self.oy = ox, oy
    self.cw, self.ch = canvasSize(self)
    self.gc = context:gpuCanvas({ width = self.cw, height = self.ch })
    -- a closed circle for the no-shader disk fallback
    local r = self.radius
    local k = 0.5523
    local cx, cy = self.cx, self.cy
    local p = self.disc
    p:moveTo(Vector.xy(cx + r, cy))
    p:cubicTo(Vector.xy(cx + r, cy + r * k), Vector.xy(cx + r * k, cy + r), Vector.xy(cx, cy + r))
    p:cubicTo(Vector.xy(cx - r * k, cy + r), Vector.xy(cx - r, cy + r * k), Vector.xy(cx - r, cy))
    p:cubicTo(Vector.xy(cx - r, cy - r * k), Vector.xy(cx - r * k, cy - r), Vector.xy(cx, cy - r))
    p:cubicTo(Vector.xy(cx + r * k, cy - r), Vector.xy(cx + r, cy - r * k), Vector.xy(cx + r, cy))
    p:close()
    return true
end

local function moving(self: Sky): boolean
    return self.live > 0.5 and not self.still and not self.paused and not self.holding and self.twinkle > 0
end

function advance(self: Sky, seconds: number): boolean
    if moving(self) then
        self.time += seconds
        self.sinceRender += seconds
    end
    return true
end

local function signature(self: Sky): number
    -- cheap change detector over every input that shapes the image (not time)
    local s = self.viewX * 1.3 + self.viewY * 2.7 + self.viewScale * 113.1 + self.viewRot * 271.9
    s += self.density * 31.7 + self.band * 57.3 + self.bandAngle * 91.1 + self.bandWidth * 0.71
    s += self.warm * 13.9 + self.vignette * 7.3 + self.exposure * 19.7 + self.seed * 3.1 + self.mode * 1000
    s += self.width * 0.37 + self.height * 0.41
    return s
end

local function render(self: Sky, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local b = self.staging
    local res = gc.width / math.max(1, (if self.mode < 0.5 then self.width else (self.radius + 2) * 2))
    local vals = {
        gc.width, gc.height, res, self.time,
        self.ox, self.oy, self.mode, self.seed,
        self.viewX, self.viewY, self.viewScale, self.viewRot,
        self.density, self.band, self.twinkle, self.bandAngle,
        self.cx, self.cy, self.radius, self.edge,
        self.bandWidth, self.warm, self.vignette, self.exposure,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'nocturne sky',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
end

function draw(self: Sky, renderer: Renderer)
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        if self.mode > 0.5 then
            renderer:drawPath(self.disc, self.discPaint)
        end
        return
    end
    -- follow the laid-out size and density (live resize, rotation)
    local cw, ch = canvasSize(self)
    if cw ~= gc.width or ch ~= gc.height then
        gc:resize(cw, ch)
        self.cw, self.ch = cw, ch
        self.rendered = false
    end
    local ox, oy = rect(self)
    self.ox, self.oy = ox, oy
    local sig = signature(self)
    local due = moving(self) and self.sinceRender >= 1 / 30
    if not self.rendered or sig ~= self.sig or due then
        self.sig = sig
        self.sinceRender = 0
        self.rendered = true
        render(self, gc, pipe, ubo, group)
    end
    local _, _, w, _ = rect(self)
    local s = w / gc.width
    renderer:save()
    renderer:transform(Mat2D.withTranslation(self.ox, self.oy) * Mat2D.withScale(s, s))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Sky>
    return {
        mode = 0,
        width = 390,
        height = 844,
        cx = 195,
        cy = 300,
        radius = 150,
        edge = 1.5,
        viewX = 0,
        viewY = 0,
        viewScale = 1,
        viewRot = 0,
        density = 0.5,
        band = 1,
        twinkle = 1,
        bandAngle = -0.55,
        bandWidth = 120,
        warm = 0.6,
        vignette = 0.4,
        exposure = 1,
        seed = 1,
        res = 2,
        live = 1,
        still = false,
        paused = false,
        holding = false,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        started = false,
        time = 0,
        sinceRender = 0,
        sig = 0,
        rendered = false,
        ox = 0,
        oy = 0,
        cw = 1,
        ch = 1,
        staging = buffer.create(96),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        disc = Path.new(),
        discPaint = Paint.with({ color = Color.rgb(0x12, 0x2C, 0x52), style = 'fill' }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
