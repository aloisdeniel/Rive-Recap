--!strict
-- Simmer signature steam (scripts/steam.wgsl).
--
-- A full-stage ScriptedDrawable between the scenes and the pot motif. The
-- handoff timelines key two inputs: `progress` (0 -> 1 over the 820 ms
-- handoff, 0 when idle) and `dir` (+1 forward, -1 back). From them this script
-- builds the steam ribbon's spine: it leaves the pot where the pot stood when
-- the user navigated, rises, curls once through the layout and leaves past the
-- top corner (mirrored for back navigation). Each spine point is born as the
-- ribbon's head passes it and then billows wider with age, so the thin ribbon
-- becomes a veil that hides the cut; then the shader evaporates it through a
-- halftone screen while the swirl keeps turning, uncovering the next layout.
--
-- Rapid navigation: a handoff that restarts while steam is still on screen
-- continues from the veil instead of popping back to a thin ribbon.
-- Reduced motion: the handoff states never play, so `progress` stays 0 and
-- nothing is drawn. Pause: the steam freezes while `motionFrozen` is set.
-- No GPU scripting: a vector fallback draws the spine as a fat cream stroke.

type Steam = {
    progress: Input<number>,
    dir: Input<number>,
    started: boolean,
    gpu: boolean,
    vm: ViewModel?,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    staging: buffer,
    sampler: ImageSampler,
    -- simulation state
    lastP: number,
    carry: number,
    pe: number,
    time: number,
    seed: number,
    navCount: number,
    lastScreen: number,
    ox: number,
    oy: number,
    sdir: number,
    spine: { Vector },
    -- fallback
    path: Path,
    paint: Paint,
}

local W, H = 390, 844
local N = 24
local RES = 1 -- px per point; the steam is soft and its screen is coarse

-- where the pot's steam leaves it, per canonical screen (mirrors POSES in
-- tools/main_board.py: pot centre + lid height x scale)
local ORIGIN: { [number]: Vector } = {
    [1] = Vector.xy(195, 560),
    [2] = Vector.xy(195, 562),
    [3] = Vector.xy(322, 668),
    [4] = Vector.xy(195, 696),
    [5] = Vector.xy(318, 474),
    [6] = Vector.xy(126, 420),
    [7] = Vector.xy(195, 531),
    [8] = Vector.xy(195, 682),
    [9] = Vector.xy(195, 516),
    [10] = Vector.xy(290, 262),
}

local function clamp01(x: number): number
    return math.clamp(x, 0, 1)
end

local function smooth(a: number, b: number, x: number): number
    local t = clamp01((x - a) / (b - a))
    return t * t * (3 - 2 * t)
end

local function catmull(p0: Vector, p1: Vector, p2: Vector, p3: Vector, t: number): Vector
    local t2 = t * t
    local t3 = t2 * t
    return (p1 * 2 + (p2 - p0) * t + (p0 * 2 - p1 * 5 + p2 * 4 - p3) * t2 + (p1 * 3 - p0 - p2 * 3 + p3) * t3) * 0.5
end

-- The spine for a handoff leaving origin (ox, oy) in direction d: control
-- points through a curl, sampled densely and resampled to N points evenly
-- spaced along the arc.
local function buildSpine(self: Steam)
    local d = self.sdir
    local ox, oy = self.ox, self.oy
    local cy = math.clamp(oy - 230, 230, 390)
    local cx = 195
    local R = 118
    local function mx(x: number): number
        return if d >= 0 then x else W - x
    end
    local ctrl: { Vector } = {
        Vector.xy(ox, oy + 30),
        Vector.xy(ox, oy),
        Vector.xy(ox + (mx(cx) - ox) * 0.35 - 14 * d, oy - (oy - (cy + R)) * 0.55),
        Vector.xy(mx(cx + 10), cy + R),
        Vector.xy(mx(cx - R * 0.78), cy + R * 0.62),
        Vector.xy(mx(cx - R), cy - 10),
        Vector.xy(mx(cx - R * 0.6), cy - R * 0.85),
        Vector.xy(mx(cx + 20), cy - R),
        Vector.xy(mx(cx + R * 0.85), cy - R * 0.45),
        Vector.xy(mx(cx + R * 0.95), cy + R * 0.2),
        Vector.xy(mx(cx + R * 1.35), cy - R * 0.2),
        Vector.xy(mx(cx + R * 1.9), cy - R * 1.6),
        Vector.xy(mx(cx + R * 2.4), cy - R * 3.2),
        Vector.xy(mx(cx + R * 2.6), cy - R * 4.0),
    }
    local dense: { Vector } = {}
    local lens: { number } = { 0 }
    for i = 2, #ctrl - 2 do
        for k = 0, 9 do
            local v = catmull(ctrl[i - 1], ctrl[i], ctrl[i + 1], ctrl[i + 2], k / 10)
            if #dense > 0 then
                table.insert(lens, lens[#lens] + Vector.distance(v, dense[#dense]))
            end
            table.insert(dense, v)
        end
    end
    local total = lens[#lens]
    local spine: { Vector } = {}
    local j = 1
    for i = 0, N - 1 do
        local target = total * i / (N - 1)
        while j < #lens - 1 and lens[j + 1] < target do
            j += 1
        end
        local seg = math.max(lens[j + 1] - lens[j], 1e-3)
        local t = clamp01((target - lens[j]) / seg)
        local a, b = dense[j], dense[j + 1]
        table.insert(spine, a + (b - a) * t)
    end
    self.spine = spine
end

function init(self: Steam, context: Context): boolean
    if self.vm == nil then
        self.vm = context:viewModel()
    end
    if self.started then
        return true
    end
    self.started = true
    local sh = context:shader('scripts/steam')
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
    local ubo = GPUBuffer.new({ size = 48 + N * 16, usage = 'uniform', label = 'steam' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    self.canvas = context:gpuCanvas({ width = math.floor(W * RES), height = math.floor(H * RES) })
    self.gpu = true
    return true
end

local function readNumber(self: Steam, name: string, fallback: number): number
    local vm = self.vm
    if vm == nil then
        return fallback
    end
    local p = vm:getNumber(name)
    return if p ~= nil then p.value else fallback
end

local function readBool(self: Steam, name: string): boolean
    local vm = self.vm
    if vm == nil then
        return false
    end
    local p = vm:getBoolean(name)
    return p ~= nil and p.value
end

function advance(self: Steam, seconds: number): boolean
    local p = clamp01(self.progress)
    local cs = math.floor(readNumber(self, 'currentScreen', 1))
    if p <= 0 then
        self.lastP = 0
        self.pe = 0
        self.carry = 0
        self.lastScreen = cs
        return false
    end
    if p < self.lastP - 0.02 or self.lastP <= 0 then
        -- a new handoff: continue from whatever veil is still on screen
        local from = self.lastScreen
        if from == cs then
            from = math.clamp(cs - (if self.dir >= 0 then 1 else -1), 1, 10)
        end
        if self.lastP > 0 then
            self.carry = math.min(self.pe, 0.4)
        else
            self.carry = 0
            local o = ORIGIN[from] or ORIGIN[1]
            self.ox, self.oy = o.x, o.y
            self.sdir = if self.dir >= 0 then 1 else -1
            buildSpine(self)
        end
        self.navCount += 1
        self.seed = (self.navCount * 0.618034) % 1 * 10
        self.time = 0
    end
    self.lastP = p
    self.lastScreen = cs
    self.pe = self.carry + p * (1 - self.carry)
    if not readBool(self, 'motionFrozen') then
        self.time += seconds
    end
    return true
end

local function radiusAt(age: number): number
    if age <= 0 then
        return 0
    end
    local g = clamp01(age / 0.34)
    return 10 + 300 * (g ^ 1.35)
end

function draw(self: Steam, renderer: Renderer)
    local pe = self.pe
    if pe <= 0.001 or pe >= 0.999 or #self.spine ~= N then
        return
    end
    local headT = 0.3
    local clear = 2.3 * smooth(0.4, 1.0, pe)
    local canvas, pipe, ubo, group = self.canvas, self.pipe, self.ubo, self.group
    if not self.gpu or canvas == nil or pipe == nil or ubo == nil or group == nil then
        -- vector fallback: the spine as a thick cream ribbon that fades
        local path = self.path
        path:reset()
        local started = false
        for i = 1, N do
            local born = (i - 1) / (N - 1) * headT
            if pe >= born then
                local v = self.spine[i]
                if not started then
                    path:moveTo(v)
                    started = true
                else
                    path:lineTo(v)
                end
            end
        end
        local a = math.floor(255 * clamp01(1 - clear / 1.4))
        self.paint.color = Color.rgba(255, 250, 238, a)
        self.paint.thickness = radiusAt(pe) * 0.6 + 10
        renderer:drawPath(path, self.paint)
        return
    end
    local b = self.staging
    local cy = math.clamp(self.oy - 230, 230, 390)
    local cx = if self.sdir >= 0 then 195 else W - 195
    local vals = {
        canvas.width, canvas.height, RES, self.time,
        pe, 22 + 70 * pe, self.seed, clear,
        1 - smooth(0.12, 0.42, pe), cx, cy, self.sdir * (0.5 * pe + 1.1 * smooth(0.35, 1.0, pe)),
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    for i = 1, N do
        local born = (i - 1) / (N - 1) * headT
        local age = pe - born
        local v = self.spine[i]
        local o = 48 + (i - 1) * 16
        buffer.writef32(b, o, v.x)
        buffer.writef32(b, o + 4, v.y)
        buffer.writef32(b, o + 8, radiusAt(age))
        buffer.writef32(b, o + 12, if age > 0 then 1 else 0)
    end
    ubo:write(b)
    local pass = canvas:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'steam',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(3)
    pass:finish()
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / RES, 1 / RES))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Steam>
    return {
        progress = 0,
        dir = 1,
        started = false,
        gpu = false,
        vm = nil,
        canvas = nil,
        pipe = nil,
        ubo = nil,
        group = nil,
        staging = buffer.create(48 + N * 16),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        lastP = 0,
        carry = 0,
        pe = 0,
        time = 0,
        seed = 0,
        navCount = 0,
        lastScreen = 1,
        ox = 195,
        oy = 560,
        sdir = 1,
        spine = {},
        path = Path.new(),
        paint = Paint.with({ style = 'stroke', thickness = 20, cap = 'round', join = 'round', color = Color.rgba(255, 250, 238, 255) }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
