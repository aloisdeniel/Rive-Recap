--!strict
-- Sprig folded-paper leaf (scripts/paperleaf.wgsl): a real 3D paper blade, lit on the GPU.
--
-- A ScriptedDrawable that sits where a vector leaf would. Its node keeps the keyed
-- x / y / scale / opacity; the 3D pose and the paper come in as ScriptInputs that the
-- scene timelines key, so choreography stays in the state machine:
--
--   L, W                 blade length and half width (local units)
--   shape                0 pointed leaf .. 1 seed half-shell
--   fold, cup, curl,     fold about the midrib, cross cupping, curl toward the viewer,
--   tipCurl, twist, wave extra roll at the tip, twist along the blade, edge ripple
--   flip                 roll about the blade's own midrib (shows the inner face past 90 deg)
--   spread, gap, pair    pair = 1 draws a mirrored twin: splay angle and base offset
--   cy                   pivot: the assembly turns about this point along the blade
--   yaw, pitch, spin     the assembly's pose; spin is the in-plane angle, applied in 3D so
--                        the light stays top-left (do not key the node's own rotation)
--   front, back, glowColor, rim   outer / inner paper stock, light-through tint, cut edge
--   glow, veins, fibre, ambient, light
--   shadow, shadowX/Y, shadowBlur  a soft cast shadow drawn under the blade
--   alpha                multiplies the image (node opacity also applies)
--   live                 0 skips all GPU work and draws nothing (off-screen scenes)
--   halfW, top, bottom   the canvas box in local units; res = pixels per unit; msaa
--
-- The canvas re-renders only when an input changed, so a settled leaf costs one image
-- draw. Without GPU scripting the projected outline is drawn as a flat vector leaf.

type Leaf = {
    L: Input<number>,
    W: Input<number>,
    shape: Input<number>,
    fold: Input<number>,
    cup: Input<number>,
    curl: Input<number>,
    tipCurl: Input<number>,
    twist: Input<number>,
    wave: Input<number>,
    flip: Input<number>,
    spread: Input<number>,
    gap: Input<number>,
    pair: Input<number>,
    yaw: Input<number>,
    pitch: Input<number>,
    spin: Input<number>,
    persp: Input<number>,
    cy: Input<number>,
    seed: Input<number>,
    glow: Input<number>,
    veins: Input<number>,
    fibre: Input<number>,
    ambient: Input<number>,
    light: Input<number>,
    front: Input<Color>,
    back: Input<Color>,
    glowColor: Input<Color>,
    rim: Input<Color>,
    shadow: Input<number>,
    shadowX: Input<number>,
    shadowY: Input<number>,
    shadowBlur: Input<number>,
    alpha: Input<number>,
    live: Input<number>,
    halfW: Input<number>,
    top: Input<number>,
    bottom: Input<number>,
    res: Input<number>,
    msaa: Input<number>,
    -- runtime
    gpu: boolean,
    canvas: GPUCanvas?,
    targets: Targets?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    lastKey: string,
    outline: Path,
    outlineKey: string,
    fillPaint: Paint,
    shadowPaint: Paint,
}

type Targets = { color: GPUTexture?, depth: GPUTexture }

local NU = 64
local NV = 24
local UBO_SIZE = 160

local SHARED: {
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    pipes: { [number]: GPUPipeline },
    targets: { [string]: Targets },
} = { vbuf = nil, ibuf = nil, icount = 0, pipes = {}, targets = {} }

local function buildMesh()
    if SHARED.vbuf ~= nil then
        return
    end
    -- the grid twice: copy 1 has mirror sign +1, copy 2 has -1 (a pair draws both)
    local cols = NV + 1
    local rows = NU + 1
    local per = rows * cols
    local vdata = buffer.create(per * 2 * 12)
    local o = 0
    for copy = 0, 1 do
        local mir = if copy == 0 then 1 else -1
        for r = 0, NU do
            -- denser toward base and tip where the outline turns fastest
            local s = r / NU
            local t = s * s * (3 - 2 * s) * 0.5 + s * 0.5
            for c = 0, NV do
                buffer.writef32(vdata, o, t)
                buffer.writef32(vdata, o + 4, -1 + 2 * c / NV)
                buffer.writef32(vdata, o + 8, mir)
                o += 12
            end
        end
    end
    local icount = NU * NV * 6
    local idata = buffer.create(icount * 2 * 2)
    o = 0
    for copy = 0, 1 do
        local base = copy * per
        for r = 0, NU - 1 do
            for c = 0, NV - 1 do
                local a = base + r * cols + c
                local d = a + cols
                buffer.writeu16(idata, o, a)
                buffer.writeu16(idata, o + 2, d)
                buffer.writeu16(idata, o + 4, a + 1)
                buffer.writeu16(idata, o + 6, a + 1)
                buffer.writeu16(idata, o + 8, d)
                buffer.writeu16(idata, o + 10, d + 1)
                o += 12
            end
        end
    end
    SHARED.vbuf = GPUBuffer.new({ size = per * 2 * 12, usage = 'vertex', data = vdata, immutable = true,
        label = 'sprig leaf grid' })
    SHARED.ibuf = GPUBuffer.new({ size = icount * 4, usage = 'index', data = idata, immutable = true,
        label = 'sprig leaf index' })
    SHARED.icount = icount
end

local function pipeline(sh: Shader, samples: number): GPUPipeline
    local p = SHARED.pipes[samples]
    if p ~= nil then
        return p
    end
    local np = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = { { stride = 12, attributes = { { format = 'float32x3', slot = 0, offset = 0 } } } },
        colorTargets = { { format = 'rgba8unorm' } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = 'none',
        sampleCount = samples,
    })
    SHARED.pipes[samples] = np
    return np
end

local function targets(pw: number, ph: number, samples: number): Targets
    local key = tostring(pw) .. 'x' .. tostring(ph) .. 'x' .. tostring(samples)
    local t = SHARED.targets[key]
    if t ~= nil then
        return t
    end
    local color: GPUTexture? = nil
    if samples > 1 then
        color = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = samples, label = 'sprig leaf msaa' })
    end
    local depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = samples, label = 'sprig leaf depth' })
    local nt: Targets = { color = color, depth = depth }
    SHARED.targets[key] = nt
    return nt
end

-- ------------------------------------------------------------------ CPU twin of the vertex shader
-- (used for the cast shadow and for the no-GPU fallback outline)

local function halfWidth(self: Leaf, t: number): number
    local tc = math.clamp(t, 0, 1)
    local lf = math.max(math.sin(math.pi * tc ^ 0.72), 0) ^ 0.95
    local sh = math.sqrt(math.max(1 - (2 * tc - 1) ^ 2, 0)) * (1 - 0.18 * tc)
    return self.W * (lf + (sh - lf) * self.shape)
end

local function shapeAt(self: Leaf, t: number, v: number): (number, number, number)
    local w = halfWidth(self, t)
    local d = v * w
    local X = d * math.cos(self.fold)
    local Z = math.abs(d) * math.sin(self.fold) + self.cup * w * v * v
    local tw = self.twist * t
    local X2 = X * math.cos(tw) - Z * math.sin(tw)
    local Z2 = X * math.sin(tw) + Z * math.cos(tw)
    local th = self.curl * t + self.tipCurl * t * t * t
    local h = t / 8
    local my, mz = 0, 0
    for i = 0, 7 do
        local s0 = (i + 0.5) * h
        local a = self.curl * s0 + self.tipCurl * s0 * s0 * s0
        my -= math.cos(a) * self.L * h
        mz += math.sin(a) * self.L * h
    end
    return X2, my + math.sin(th) * Z2, mz + math.cos(th) * Z2
end

local function place(self: Leaf, x: number, y: number, z: number, mir: number): (number, number, number)
    local a = self.flip
    local c, s = math.cos(a), math.sin(a)
    x, z = x * c + z * s, -x * s + z * c
    a = self.spread
    c, s = math.cos(a), math.sin(a)
    x, y = x * c - y * s, x * s + y * c
    x = (x + self.gap) * mir
    y = y + self.cy
    a = self.yaw
    c, s = math.cos(a), math.sin(a)
    x, z = x * c + z * s, -x * s + z * c
    a = self.pitch
    c, s = math.cos(a), math.sin(a)
    y, z = y * c - z * s, y * s + z * c
    a = self.spin
    c, s = math.cos(a), math.sin(a)
    x, y = x * c - y * s, x * s + y * c
    return x, y, z
end

local function screenAt(self: Leaf, t: number, v: number, mir: number): Vector
    local x, y, z = shapeAt(self, t, v)
    x, y, z = place(self, x, y, z, mir)
    local D = self.persp
    local f = D / math.max(D - z, D * 0.2)
    return Vector.xy(x * f, y * f)
end

local function buildOutline(self: Leaf)
    local key = string.format('%.2f|%.2f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.2f|%.1f|%.3f|%.2f',
        self.L, self.W, self.shape, self.fold, self.cup, self.curl, self.tipCurl, self.twist, self.flip, self.spread,
        self.gap, self.yaw, self.pitch, self.spin, self.persp, self.pair, self.wave, self.cy)
    if key == self.outlineKey then
        return
    end
    self.outlineKey = key
    local p = Path.new()
    local n = 20
    local count = if self.pair >= 0.5 then 2 else 1
    for inst = 1, count do
        local mir = if inst == 1 then 1 else -1
        -- outer edge up one side, back down the other; mirrored twins wind the other
        -- way, so walk them in reverse to keep one winding (clockwise fill rule)
        local v0 = if mir > 0 then 1 else -1
        for j = 0, n do
            local pt = screenAt(self, j / n, v0, mir)
            if j == 0 then
                p:moveTo(pt)
            else
                p:lineTo(pt)
            end
        end
        for j = n, 0, -1 do
            p:lineTo(screenAt(self, j / n, -v0, mir))
        end
        p:close()
    end
    self.outline = p
end

-- ------------------------------------------------------------------ lifecycle

function init(self: Leaf, context: Context): boolean
    if self.gpu then
        return true
    end
    local sh = context:shader('scripts/paperleaf')
    if sh == nil then
        return true -- no GPU scripting: the flat outline draws instead
    end
    buildMesh()
    local want = math.max(1, math.floor(self.msaa + 0.5))
    local samples = if want >= 4 and context:features().maxSamples >= 4 then 4 else 1
    local pipe = pipeline(sh, samples)
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'sprig leaf' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(0.5, self.res)
    self.k = k
    local pw = math.ceil(self.halfW * 2 * k / 8) * 8
    local ph = math.ceil((self.bottom - self.top) * k / 8) * 8
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    self.targets = targets(pw, ph, samples)
    self.gpu = true
    return true
end

function update(self: Leaf) end

function advance(self: Leaf, seconds: number): boolean
    return self.live >= 0.5
end

local function writeUniforms(self: Leaf)
    local b = self.staging
    local fr = Color.toFloat(self.front)
    local bk = Color.toFloat(self.back)
    local gl = Color.toFloat(self.glowColor)
    local rm = Color.toFloat(self.rim)
    local vals = {
        self.L, self.W, self.fold, self.cup,
        self.curl, self.twist, self.flip, self.pitch,
        self.spin, self.yaw, self.spread, self.gap,
        self.shape, self.wave, self.persp, self.pair,
        self.halfW, self.top, self.bottom, self.seed,
        fr[1], fr[2], fr[3], self.glow,
        bk[1], bk[2], bk[3], self.veins,
        gl[1], gl[2], gl[3], self.fibre,
        rm[1], rm[2], rm[3], self.tipCurl,
        self.light, self.ambient, self.cy, 0,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
end

local function render(self: Leaf, canvas: GPUCanvas)
    local ubo = self.ubo
    local pipe = self.pipe
    local group = self.group
    local vbuf = SHARED.vbuf
    local ibuf = SHARED.ibuf
    local tg = self.targets
    if ubo == nil or pipe == nil or group == nil or vbuf == nil or ibuf == nil or tg == nil then
        return
    end
    writeUniforms(self)
    ubo:write(self.staging)
    local pass: GPURenderPass
    local mc = tg.color
    if mc ~= nil then
        pass = canvas:beginRenderPass({
            color = { { view = mc:view(), resolveTarget = canvas:colorView(), loadOp = 'clear',
                storeOp = 'discard', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = tg.depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'sprig leaf',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = tg.depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard',
                depthClearValue = 1 },
            label = 'sprig leaf',
        })
    end
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:setVertexBuffer(0, vbuf)
    pass:setIndexBuffer(ibuf, 'uint16')
    pass:drawIndexed(if self.pair >= 0.5 then SHARED.icount * 2 else SHARED.icount)
    pass:finish()
end

local function stateKey(self: Leaf): string
    return string.format('%s|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f|%.2f|%d|%d|%d|%d|%.3f',
        self.outlineKey, self.glow, self.veins, self.fibre, self.ambient, self.light, self.seed, self.tipCurl,
        self.front, self.back, self.glowColor, self.rim, self.wave)
end

function draw(self: Leaf, renderer: Renderer)
    local a = math.clamp(self.alpha, 0, 1)
    if self.live < 0.5 or a <= 0.002 then
        return
    end
    buildOutline(self)
    if self.shadow > 0.002 then
        self.shadowPaint.color = Color.rgba(8, 26, 20, math.floor(255 * math.clamp(self.shadow * a, 0, 1)))
        self.shadowPaint.feather = math.max(1, self.shadowBlur)
        renderer:save()
        renderer:transform(Mat2D.withTranslation(self.shadowX, self.shadowY))
        renderer:drawPath(self.outline, self.shadowPaint)
        renderer:restore()
    end
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        self.fillPaint.color = Color.lerp(self.back, self.front, 1)
        renderer:drawPath(self.outline, self.fillPaint)
        return
    end
    local key = stateKey(self)
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas)
    end
    local k = self.k
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-self.halfW, self.top) * Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', a)
    renderer:restore()
end

return function(): Node<Leaf>
    return {
        L = 300,
        W = 110,
        shape = 0,
        fold = 0.35,
        cup = 0.1,
        curl = 0.3,
        tipCurl = 0,
        twist = 0,
        wave = 0.3,
        flip = 0,
        spread = 0,
        gap = 0,
        pair = 0,
        yaw = 0,
        pitch = 0,
        spin = 0,
        persp = 1400,
        cy = 0,
        seed = 1,
        glow = 0.8,
        veins = 1,
        fibre = 1,
        ambient = 0.42,
        light = 0,
        front = Color.rgb(168, 204, 114),
        back = Color.rgb(233, 224, 194),
        glowColor = Color.rgb(214, 236, 150),
        rim = Color.rgb(246, 241, 220),
        shadow = 0,
        shadowX = 14,
        shadowY = 22,
        shadowBlur = 24,
        alpha = 1,
        live = 1,
        halfW = 200,
        top = -360,
        bottom = 60,
        res = 2,
        msaa = 4,
        gpu = false,
        canvas = nil,
        targets = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        lastKey = '',
        outline = Path.new(),
        outlineKey = '',
        fillPaint = Paint.with({ color = Color.rgb(168, 204, 114) }),
        shadowPaint = Paint.with({ color = Color.rgba(8, 26, 20, 80), feather = 24 }),
        init = init,
        update = update,
        advance = advance,
        draw = draw,
    }
end
