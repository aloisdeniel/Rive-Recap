--!strict
-- Nocturne orb (shaders/orb.wgsl): a lit 3D moon, ringed planet or eclipse as
-- a ScriptedDrawable centred on (cx, cy).
--
-- `phase` (moon), `turn`, `tint`, `exposure`, `halo`, `ring` are inputs so the
-- scene timelines key them: the lunar scene sweeps the sun round the moon in
-- step with the count, the persona emblems tint the body with personaColor.
-- While `live` and neither `still` (reduced motion) nor paused / holding, the
-- surface turns at `spinSpeed` rad/s; the canvas is re-rendered only when an
-- input or the turn changed (at most 30 times a second for the turn alone).
-- Without shader support a flat vector disk in the tint colour is drawn.

type Orb = {
    kind: Input<number>,
    cx: Input<number>,
    cy: Input<number>,
    radius: Input<number>,
    phase: Input<number>,
    turn: Input<number>,
    spinSpeed: Input<number>,
    tilt: Input<number>,
    earthshine: Input<number>,
    tint: Input<Color>,
    tintAmount: Input<number>,
    rimWarm: Input<number>,
    ringTilt: Input<number>,
    ring: Input<number>,
    exposure: Input<number>,
    halo: Input<number>,
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
    ext: number,
    spun: number,
    sinceRender: number,
    sig: number,
    rendered: boolean,
    staging: buffer,
    sampler: ImageSampler,
    disc: Path,
    discPaint: Paint,
}

local function extentFor(kind: number): number
    if kind > 0.5 and kind < 1.5 then
        return 2.35
    end
    if kind >= 1.5 then
        return 1.9
    end
    return 1.45
end

function init(self: Orb, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    self.ext = extentFor(self.kind)
    local r = self.radius
    local k = 0.5523
    local p = self.disc
    p:moveTo(Vector.xy(r, 0))
    p:cubicTo(Vector.xy(r, r * k), Vector.xy(r * k, r), Vector.xy(0, r))
    p:cubicTo(Vector.xy(-r * k, r), Vector.xy(-r, r * k), Vector.xy(-r, 0))
    p:cubicTo(Vector.xy(-r, -r * k), Vector.xy(-r * k, -r), Vector.xy(0, -r))
    p:cubicTo(Vector.xy(r * k, -r), Vector.xy(r, -r * k), Vector.xy(r, 0))
    p:close()
    local sh = context:shader('shaders/orb')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 80, usage = 'uniform', label = 'nocturne orb' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local res = math.clamp(self.res, 0.5, 4)
    local px = math.max(2, math.ceil(self.radius * self.ext * 2 * res))
    self.gc = context:gpuCanvas({ width = px, height = px })
    return true
end

local function moving(self: Orb): boolean
    return self.live > 0.5 and not self.still and not self.paused and not self.holding and self.spinSpeed ~= 0
end

function advance(self: Orb, seconds: number): boolean
    if moving(self) then
        self.spun += seconds * self.spinSpeed
        self.sinceRender += seconds
    end
    return true
end

local function signature(self: Orb): number
    local c = Color.toFloat(self.tint)
    local s = self.phase * 97.3 + self.turn * 31.1 + self.tilt * 13.7 + self.earthshine * 7.9 + self.tintAmount * 19.3
    s += c[1] * 3.1 + c[2] * 5.3 + c[3] * 7.7 + self.rimWarm * 11.1 + self.ringTilt * 17.9 + self.ring * 23.3
    s += self.exposure * 29.9 + self.halo * 37.1 + self.seed * 2.3 + self.kind * 1000
    return s
end

local function render(self: Orb, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local b = self.staging
    local c = Color.toFloat(self.tint)
    local res = gc.width / (self.radius * self.ext * 2)
    local vals = {
        gc.width, gc.height, res, self.kind,
        self.radius, self.ext, self.phase, self.turn + self.spun,
        c[1], c[2], c[3], self.tintAmount,
        self.earthshine, self.rimWarm, self.ringTilt, self.ring,
        self.exposure, self.halo, self.tilt, self.seed,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'nocturne orb',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
end

function draw(self: Orb, renderer: Renderer)
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        self.discPaint.color = self.tint
        renderer:save()
        renderer:transform(Mat2D.withTranslation(self.cx, self.cy))
        renderer:drawPath(self.disc, self.discPaint)
        renderer:restore()
        return
    end
    local sig = signature(self)
    local due = moving(self) and self.sinceRender >= 1 / 30
    if not self.rendered or sig ~= self.sig or due then
        self.sig = sig
        self.sinceRender = 0
        self.rendered = true
        render(self, gc, pipe, ubo, group)
    end
    local half = self.radius * self.ext
    local s = (half * 2) / gc.width
    renderer:save()
    renderer:transform(Mat2D.withTranslation(self.cx - half, self.cy - half) * Mat2D.withScale(s, s))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Orb>
    return {
        kind = 0,
        cx = 0,
        cy = 0,
        radius = 100,
        phase = 0.75,
        turn = 0,
        spinSpeed = 0.025,
        tilt = 0,
        earthshine = 0.6,
        tint = Color.rgb(0xBC, 0xE4, 0xE8),
        tintAmount = 0,
        rimWarm = 1,
        ringTilt = 0.42,
        ring = 1,
        exposure = 1,
        halo = 1,
        seed = 3,
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
        ext = 1.45,
        spun = 0,
        sinceRender = 0,
        sig = 0,
        rendered = false,
        staging = buffer.create(80),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        disc = Path.new(),
        discPaint = Paint.with({ color = Color.rgb(0xBC, 0xE4, 0xE8), style = 'fill' }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
