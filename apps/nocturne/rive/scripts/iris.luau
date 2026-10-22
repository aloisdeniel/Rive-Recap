--!strict
-- Nocturne aperture (shaders/iris.wgsl) as a ScriptedDrawable.
--
-- mode 0: the stage iris, the signature transition. It covers (0, 0, width,
--         height), the real canvas (width and height are bound to the laid-out
--         artboard size); the motif timelines key its centre, hole radius and
--         spin in the 390 x 844 *design* space of the hero art, and the hero
--         frame (fx, fy, fs, written by layout.luau) maps them onto the canvas:
--         on every scene change it closes over the outgoing scene to a small
--         pupil, travels to the next hero and opens on the new sky. The keyed
--         "open" radius (farthest design corner + 20) is stretched to the
--         farthest real corner, so at any canvas size the blades start and end
--         exactly off-screen and close with no gap at the edges.
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
    fx: Input<number>,
    fy: Input<number>,
    fs: Input<number>,
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
    rh: number,
    staging: buffer,
    sampler: ImageSampler,
    ring: Path,
    ringPaint: Paint,
}

local DESIGN_W, DESIGN_H = 390, 844
local MAX_PX = 4096

local function rect(self: Iris): (number, number, number, number)
    if self.mode < 0.5 then
        return 0, 0, math.max(1, self.width), math.max(1, self.height)
    end
    local r = self.outer + 2
    return self.cx - r, self.cy - r, r * 2, r * 2
end

-- Centre and hole radius in canvas points. The housing (mode 1) is drawn in its
-- own space; the stage (mode 0) maps the keyed design values through the hero
-- frame and stretches the open radius to the real canvas.
local function stage(self: Iris): (number, number, number)
    if self.mode >= 0.5 then
        return self.cx, self.cy, self.hole
    end
    local fs = math.max(0.01, self.fs)
    local cx, cy = self.fx + fs * self.cx, self.fy + fs * self.cy
    local dx = math.max(self.cx, DESIGN_W - self.cx)
    local dy = math.max(self.cy, DESIGN_H - self.cy)
    local openD = math.sqrt(dx * dx + dy * dy) + 20
    local rx = math.max(cx, self.width - cx)
    local ry = math.max(cy, self.height - cy)
    local openR = math.sqrt(rx * rx + ry * ry) + 20
    local t = math.clamp(self.hole / openD, 0, 1)
    return cx, cy, self.hole * fs + t * t * (openR - openD * fs)
end

local function canvasSize(self: Iris): (number, number)
    local _, _, w, h = rect(self)
    local res = math.clamp(self.res, 0.5, 4)
    local k = math.min(1, MAX_PX / math.max(w * res, h * res))
    return math.max(1, math.ceil(w * res * k)), math.max(1, math.ceil(h * res * k))
end

function init(self: Iris, context: Context): boolean
    if self.started then
        return true
    end
    self.started = true
    local ox, oy, w, h = rect(self)
    self.ox, self.oy, self.rw, self.rh = ox, oy, w, h
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
    local cw, ch = canvasSize(self)
    self.gc = context:gpuCanvas({ width = cw, height = ch })
    return true
end

local function covers(self: Iris): boolean
    if self.opacity <= 0.001 then
        return false
    end
    if self.mode < 0.5 then
        local cx, cy, hole = stage(self)
        local dx = math.max(cx, self.width - cx)
        local dy = math.max(cy, self.height - cy)
        return hole < math.sqrt(dx * dx + dy * dy) + 4
    end
    return self.hole < self.outer * 1.03
end

local function signature(self: Iris): number
    local s = self.cx * 1.7 + self.cy * 3.1 + self.hole * 11.3 + self.spin * 97.1 + self.blades * 5.3
    s += self.curl * 41.9 + self.curve * 23.3 + self.hand * 7.7 + self.bloom * 61.1 + self.rim * 13.7
    s += self.lightness * 29.3 + self.thick * 3.9 + self.outer * 0.37 + self.opacity * 71.3
    s += self.fx * 0.53 + self.fy * 0.71 + self.fs * 43.7 + self.width * 0.19 + self.height * 0.23
    return s
end

local function render(self: Iris, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local b = self.staging
    local res = gc.width / math.max(1, self.rw)
    local cx, cy, hole = stage(self)
    local vals = {
        gc.width, gc.height, res, self.mode,
        self.ox, self.oy, self.outer, math.clamp(self.opacity, 0, 1),
        cx, cy, math.max(hole, 0.5), self.spin,
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
    local cx, cy, hole = stage(self)
    local outerR = if self.mode < 0.5 then math.sqrt(self.width * self.width + self.height * self.height) + 40 else self.outer
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
    local r = math.max(hole, 0.5)
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
    -- follow the laid-out size: re-allocate the canvas when the box or the
    -- device density changes (live resize, rotation, a new breakpoint)
    local ox, oy, w, h = rect(self)
    local cw, ch = canvasSize(self)
    if cw ~= gc.width or ch ~= gc.height then
        gc:resize(cw, ch)
        self.rendered = false
    end
    self.ox, self.oy, self.rw, self.rh = ox, oy, w, h
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
        fx = 0,
        fy = 0,
        fs = 1,
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
        rh = 844,
        staging = buffer.create(80),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        ring = Path.new(),
        ringPaint = Paint.with({ color = Color.rgb(0x0E, 0x1F, 0x36), style = 'fill' }),
        init = init,
        draw = draw,
    }
end
