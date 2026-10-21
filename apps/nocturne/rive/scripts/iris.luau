--!strict
-- Nocturne aperture (shaders/iris.wgsl) as a ScriptedDrawable.
--
-- mode 0: the stage iris, the signature transition. It covers (0, 0, width,
--         height); the motif timelines key its centre, hole radius and spin, so
--         on every scene change it closes over the outgoing scene to a small
--         pupil, travels to the next hero and opens on the new sky.
-- mode 1: the motif's own blades, inside a housing of radius `outer` centred on
--         (cx, cy). The motif's Iris timeline keys `hole`.
--
-- Nothing is drawn (and no GPU pass is issued) while the hole is wider than the
-- area it would cover. The canvas is re-rendered only when an input changed:
-- the iris is static between transitions. Without shader support the blades
-- fall back to a flat vector ring that keeps the hole readable.

type Iris = {
    mode: Input<number>,
    width: Input<number>,
    height: Input<number>,
    cx: Input<number>,
    cy: Input<number>,
    hole: Input<number>,
    spin: Input<number>,
    blades: Input<number>,
    curl: Input<number>,
    curve: Input<number>,
    hand: Input<number>,
    bloom: Input<number>,
    rim: Input<number>,
    lightness: Input<number>,
    thick: Input<number>,
    outer: Input<number>,
    opacity: Input<number>,
    res: Input<number>,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    started: boolean,
    sig: number,
    rendered: boolean,
    ox: number,
    oy: number,
    rw: number,
    staging: buffer,
    sampler: ImageSampler,
    ring: Path,
    ringPaint: Paint,
}

local function rect(self: Iris): (number, number, number, number)
    if self.mode < 0.5 then
        return 0, 0, self.width, self.height
    end
    local r = self.outer + 2
    return self.cx - r, self.cy - r, r * 2, r * 2
end

function init(self: Iris, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    local ox, oy, w, h = rect(self)
    self.ox, self.oy, self.rw = ox, oy, w
    local sh = context:shader('shaders/iris')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 80, usage = 'uniform', label = 'nocturne iris' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local res = math.clamp(self.res, 0.5, 4)
    self.gc = context:gpuCanvas({ width = math.max(1, math.ceil(w * res)), height = math.max(1, math.ceil(h * res)) })
    return true
end

local function covers(self: Iris): boolean
    if self.opacity <= 0.001 then
        return false
    end
    if self.mode < 0.5 then
        local dx = math.max(self.cx, self.width - self.cx)
        local dy = math.max(self.cy, self.height - self.cy)
        return self.hole < math.sqrt(dx * dx + dy * dy) + 4
    end
    return self.hole < self.outer * 1.03
end

local function signature(self: Iris): number
    local s = self.cx * 1.7 + self.cy * 3.1 + self.hole * 11.3 + self.spin * 97.1 + self.blades * 5.3
    s += self.curl * 41.9 + self.curve * 23.3 + self.hand * 7.7 + self.bloom * 61.1 + self.rim * 13.7
    s += self.lightness * 29.3 + self.thick * 3.9 + self.outer * 0.37 + self.opacity * 71.3
    return s
end

local function render(self: Iris, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local b = self.staging
    local res = gc.width / math.max(1, self.rw)
    local vals = {
        gc.width, gc.height, res, self.mode,
        self.ox, self.oy, self.outer, math.clamp(self.opacity, 0, 1),
        self.cx, self.cy, math.max(self.hole, 0.5), self.spin,
        math.clamp(math.floor(self.blades + 0.5), 3, 16), self.curl, self.curve, self.hand,
        self.bloom, self.rim, self.lightness, self.thick,
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'nocturne iris',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
end

local function fallback(self: Iris, renderer: Renderer)
    -- flat blades: an annulus from the hole to the edge of the covered area
    local p = self.ring
    p:reset()
    local outerR = if self.mode < 0.5 then 1200 else self.outer
    local cx, cy = self.cx, self.cy
    local n = 48
    for i = 0, n do
        local a = i / n * math.pi * 2
        local v = Vector.xy(cx + math.cos(a) * outerR, cy + math.sin(a) * outerR)
        if i == 0 then
            p:moveTo(v)
        else
            p:lineTo(v)
        end
    end
    p:close()
    local r = math.max(self.hole, 0.5)
    for i = 0, n do
        local a = -i / n * math.pi * 2
        local v = Vector.xy(cx + math.cos(a) * r, cy + math.sin(a) * r)
        if i == 0 then
            p:moveTo(v)
        else
            p:lineTo(v)
        end
    end
    p:close()
    renderer:drawPath(p, self.ringPaint)
end

function draw(self: Iris, renderer: Renderer)
    if not covers(self) then
        return
    end
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        fallback(self, renderer)
        return
    end
    local sig = signature(self)
    if not self.rendered or sig ~= self.sig then
        self.sig = sig
        self.rendered = true
        render(self, gc, pipe, ubo, group)
    end
    local s = self.rw / gc.width
    renderer:save()
    renderer:transform(Mat2D.withTranslation(self.ox, self.oy) * Mat2D.withScale(s, s))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Iris>
    return {
        mode = 0,
        width = 390,
        height = 844,
        cx = 195,
        cy = 300,
        hole = 2000,
        spin = 0,
        blades = 9,
        curl = 0.85,
        curve = 0.55,
        hand = 1,
        bloom = 0,
        rim = 1,
        lightness = 1,
        thick = 2.2,
        outer = 150,
        opacity = 1,
        res = 2,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        started = false,
        sig = 0,
        rendered = false,
        ox = 0,
        oy = 0,
        rw = 390,
        staging = buffer.create(80),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        ring = Path.new(),
        ringPaint = Paint.with({ color = Color.rgb(0x0E, 0x1F, 0x36), style = 'fill' }),
        init = init,
        draw = draw,
    }
end
