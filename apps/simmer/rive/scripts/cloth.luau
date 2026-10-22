--!strict
-- Simmer tablecloth pull (scripts/cloth.wgsl): the second half of the
-- signature handoff, a gingham tablecloth yanked across the bottom of the
-- stage that flings the ingredients riding on it.
--
-- The cloth is a real simulation: 30 x 13 particles joined by structural,
-- shear and bend constraints (position-based Verlet), with gravity, air drag
-- and table friction. Two "hands" hold the leading edge and follow a keyed
-- path: a tug back (anticipation), a fast pull in, a slow pass across the
-- middle where the cloth catches up, bunches and billows, then the yank out.
-- The simulation runs in the hands' moving frame (the frame's acceleration
-- enters as a fictitious force) and every particle is tethered to the hands
-- by its rest distance, so even a whip-fast pull never stretches the weave.
--
-- Four ingredients ride on the cloth. Each is drawn from its own small vector
-- artboard (rider*), stuck to a cloth particle until the yank throws it: it
-- leaves with the cloth's velocity plus a hop and spin, and tumbles out of
-- frame. Back navigation mirrors the whole pull.
--
-- Driven by two keyed inputs from the handoff timelines: `progress` (0..1
-- over 820 ms, 0 when idle) and `dir` (+1 / -1). Deterministic for a fixed
-- frame step, so headless captures reproduce. Reduced motion: never plays.
-- Paused (`motionFrozen`): the simulation holds. No GPU scripting: the same
-- simulation is drawn as flat-shaded vector quads.
--
-- Responsive: the simulation runs in master units (the 390 x 844 stage) on a
-- field as wide as the real stage, and is drawn scaled by kc onto the real
-- bottom band. kc follows the stage's size (0.6-1.5), so the cloth stays a
-- tablecloth next to the art; the hands' path stretches with the width, so
-- the pull still crosses the whole canvas. The canvas is allocated at the
-- band's real size times the presenting pixel density (capped at 2x).

type Rider = { i: number, j: number, launch: number, flying: boolean, x: number, y: number, z: number,
    vx: number, vy: number, vz: number, rot: number, spin: number, art: number }

type Cloth = {
    progress: Input<number>,
    dir: Input<number>,
    rider1: Input<Artboard>,
    rider2: Input<Artboard>,
    rider3: Input<Artboard>,
    rider4: Input<Artboard>,
    ctx: Context?,
    vm: ViewModel?,
    size: Vector,
    scale: number,
    kc: number,      -- stage points per simulation unit
    simW: number,    -- stage width in simulation units
    xk: number,      -- the hands' path stretch (simW / 390)
    -- simulation
    px: { number }, py: { number }, pz: { number },
    qx: { number }, qy: { number }, qz: { number },
    ca: { number }, cb: { number }, cr: { number },
    tether: { number },
    active: boolean,
    s: number,
    hx: number, hy: number, hz: number,
    vx: number, vy: number, vz: number,
    sdir: number,
    lastP: number,
    riders: { Rider },
    arts: { Artboard },
    -- GPU
    gpu: boolean,
    gc: GPUCanvas?,
    msaa: GPUTextureView?,
    depth: GPUTextureView?,
    samples: number,
    pCloth: GPUPipeline?,
    pShadow: GPUPipeline?,
    layout: GPUBindGroupLayout?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    vbuf: GPUBuffer?,
    ibuf: GPUBuffer?,
    icount: number,
    vstage: buffer,
    ustage: buffer,
    sampler: ImageSampler,
    -- fallback
    quad: Path,
    qpaint: Paint,
}

local BW, BH = 390, 844 -- the master the pull is authored on
local NX, NY = 30, 13
local SX, SY = 16, 15
local BAND_TOP = 360 -- the canvas covers the stage from here down
local BAND_H = BH - BAND_TOP
local LIFT = 0.9
local G = 2300
local DRAG = 0.992
local FRICTION = 0.32
local ITER = 6
local P0 = 0.33 -- the pull follows the steam: it starts as the veil begins to clear
local NV = NX * NY

local function idx(i: number, j: number): number
    return j * NX + i + 1
end

local function clamp01(x: number): number
    return math.clamp(x, 0, 1)
end

-- Hermite through keyed (s, value, slope) knots
local function hermite(knots: { { number } }, s: number): number
    if s <= knots[1][1] then
        return knots[1][2]
    end
    for k = 1, #knots - 1 do
        local a, b = knots[k], knots[k + 1]
        if s <= b[1] then
            local h = b[1] - a[1]
            local t = (s - a[1]) / h
            local t2, t3 = t * t, t * t * t
            return (2 * t3 - 3 * t2 + 1) * a[2] + (t3 - 2 * t2 + t) * h * a[3]
                + (-2 * t3 + 3 * t2) * b[2] + (t3 - t2) * h * b[3]
        end
    end
    return knots[#knots][2]
end

-- the hands' path (forward; back navigation mirrors x at draw time)
local HX = { { 0, -40, -200 }, { 0.1, -70, 0 }, { 0.45, 330, 1400 }, { 0.75, 480, 260 }, { 1.0, 1060, 3400 } }
local HZ = { { 0, 6, 0 }, { 0.1, 4, 40 }, { 0.45, 104, 150 }, { 0.75, 84, -50 }, { 1.0, 150, 300 } }
local HY = { { 0, 664, 0 }, { 0.4, 648, -40 }, { 0.7, 640, 0 }, { 1.0, 618, -80 } }

local function hand(self: Cloth, s: number): (number, number, number)
    return hermite(HX, s) * self.xk, hermite(HY, s), hermite(HZ, s)
end

local function buildConstraints(self: Cloth)
    local ca, cb, cr = self.ca, self.cb, self.cr
    local function add(a: number, b: number, r: number)
        table.insert(ca, a)
        table.insert(cb, b)
        table.insert(cr, r)
    end
    local diag = math.sqrt(SX * SX + SY * SY)
    for j = 0, NY - 1 do
        for i = 0, NX - 1 do
            if i < NX - 1 then add(idx(i, j), idx(i + 1, j), SX) end
            if j < NY - 1 then add(idx(i, j), idx(i, j + 1), SY) end
            if i < NX - 1 and j < NY - 1 then
                add(idx(i, j), idx(i + 1, j + 1), diag)
                add(idx(i + 1, j), idx(i, j + 1), diag)
            end
            if i < NX - 2 then add(idx(i, j), idx(i + 2, j), SX * 2) end
            if j < NY - 2 then add(idx(i, j), idx(i, j + 2), SY * 2) end
        end
    end
    for j = 0, NY - 1 do
        for i = 0, NX - 1 do
            self.tether[idx(i, j)] = (NX - 1 - i) * SX * 1.03
        end
    end
end

local PIN_J = { 1, NY - 2 }

local function pinY(j: number): number
    return (j - (NY - 1) / 2) * SY * 0.86
end

local function reset(self: Cloth)
    local hx, hy, hz = hand(self, 0)
    self.hx, self.hy, self.hz = hx, hy, hz
    self.vx, self.vy, self.vz = 0, 0, 0
    self.s = 0
    for j = 0, NY - 1 do
        for i = 0, NX - 1 do
            local k = idx(i, j)
            -- flat on the table, trailing behind the hands, a few loose ripples
            local x = -(NX - 1 - i) * SX
            local y = (j - (NY - 1) / 2) * SY
            local z = -hz + 2 * math.sin(i * 0.9 + j * 0.4)
            self.px[k], self.py[k], self.pz[k] = x, y, z
            self.qx[k], self.qy[k], self.qz[k] = x, y, z
        end
    end
    local slots = { { NX - 7, 4, 0.40, 1 }, { NX - 13, 9, 0.47, 2 }, { NX - 18, 3, 0.53, 3 }, { NX - 23, 8, 0.6, 4 } }
    self.riders = {}
    for _, sl in slots do
        table.insert(self.riders, { i = sl[1], j = sl[2], launch = sl[3], flying = false, x = 0, y = 0, z = 0,
            vx = 0, vy = 0, vz = 0, rot = 0, spin = 0, art = sl[4] })
    end
end

local function step(self: Cloth, h: number, s1: number)
    local nx, ny, nz = hand(self, s1)
    local vx, vy, vz = (nx - self.hx) / h, (ny - self.hy) / h, (nz - self.hz) / h
    -- fictitious force of the accelerating frame (clamped for stability)
    local ax = math.clamp((vx - self.vx) / h, -9000, 9000)
    local ay = math.clamp((vy - self.vy) / h, -9000, 9000)
    local az = math.clamp((vz - self.vz) / h, -9000, 9000)
    local dfx, dfy = nx - self.hx, ny - self.hy
    local px, py, pz, qx, qy, qz = self.px, self.py, self.pz, self.qx, self.qy, self.qz
    local h2 = h * h
    for k = 1, NV do
        local x, y, z = px[k], py[k], pz[k]
        local nxp = x + (x - qx[k]) * DRAG - ax * h2
        local nyp = y + (y - qy[k]) * DRAG - ay * h2
        local nzp = z + (z - qz[k]) * DRAG - (G + az) * h2
        -- the table (world z = 0) with friction against the world, not the frame
        if nzp + nz <= 0 then
            nzp = -nz
            local wx = (nxp - x) + dfx
            local wy = (nyp - y) + dfy
            nxp = x + wx * (1 - FRICTION) - dfx
            nyp = y + wy * (1 - FRICTION) - dfy
        end
        qx[k], qy[k], qz[k] = x, y, z
        px[k], py[k], pz[k] = nxp, nyp, nzp
    end
    self.hx, self.hy, self.hz = nx, ny, nz
    self.vx, self.vy, self.vz = vx, vy, vz
    local ca, cb, cr = self.ca, self.cb, self.cr
    local nc = #ca
    local tether = self.tether
    for _ = 1, ITER do
        for c = 1, nc do
            local a, b = ca[c], cb[c]
            local dx, dy, dz = px[b] - px[a], py[b] - py[a], pz[b] - pz[a]
            local d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d > 1e-6 then
                local f = (d - cr[c]) / d * 0.5
                dx, dy, dz = dx * f, dy * f, dz * f
                px[a] += dx; py[a] += dy; pz[a] += dz
                px[b] -= dx; py[b] -= dy; pz[b] -= dz
            end
        end
        -- pins: the hands hold the leading edge
        for _, j in PIN_J do
            local k = idx(NX - 1, j)
            px[k], py[k], pz[k] = 0, pinY(j), 0
        end
        -- table and tethers
        for k = 1, NV do
            if pz[k] + nz < 0 then
                pz[k] = -nz
            end
            local d = math.sqrt(px[k] * px[k] + py[k] * py[k] + pz[k] * pz[k])
            local t = tether[k]
            if d > t then
                local f = t / d
                px[k] *= f; py[k] *= f; pz[k] *= f
            end
        end
    end
    for _, j in PIN_J do
        local k = idx(NX - 1, j)
        qx[k], qy[k], qz[k] = 0, pinY(j), 0
    end
end

local function stepRiders(self: Cloth, dt: number)
    for _, r in self.riders do
        local k = idx(r.i, r.j)
        local wx = self.px[k] + self.hx
        local wy = self.py[k] + self.hy
        local wz = self.pz[k] + self.hz
        if not r.flying then
            -- world velocity of the cloth under the rider
            local cvx = (self.px[k] - self.qx[k]) / dt * 0.5 + self.vx
            local cvy = (self.py[k] - self.qy[k]) / dt * 0.5 + self.vy
            local cvz = (self.pz[k] - self.qz[k]) / dt * 0.5 + self.vz
            if self.s >= r.launch then
                r.flying = true
                r.vx, r.vy, r.vz = cvx * 0.45, cvy * 0.45 - 120, math.max(cvz, 0) * 0.4 + 760 + r.art * 70
                r.spin = (if r.art % 2 == 0 then 1 else -1) * (6 + r.art)
            end
            r.x, r.y, r.z = wx, wy, wz + 8
        else
            r.vz -= G * dt
            r.x += r.vx * dt
            r.y += r.vy * dt
            r.z += r.vz * dt
            r.rot += r.spin * dt
        end
    end
end

function init(self: Cloth, context: Context): boolean
    if self.vm == nil then
        self.vm = context:viewModel()
    end
    if self.ctx ~= nil then
        return true
    end
    self.ctx = context
    for _, input in { self.rider1, self.rider2, self.rider3, self.rider4 } do
        local inst = input:instance()
        inst:advance(0)
        table.insert(self.arts, inst)
    end
    buildConstraints(self)
    reset(self)
    local sh = context:shader('scripts/cloth')
    if sh == nil then
        return true
    end
    local f = context:features()
    self.samples = if f.maxSamples >= 4 then 4 else 1
    local layout = GPUBindGroupLayout.new({ shader = sh, groupIndex = 0, label = 'cloth' })
    self.layout = layout
    local over: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    local vl: { VertexBufferLayout } = { {
        stride = 32,
        attributes = {
            { format = 'float32x3', slot = 0, offset = 0 },
            { format = 'float32x3', slot = 1, offset = 12 },
            { format = 'float32x2', slot = 2, offset = 24 },
        },
    } }
    self.pShadow = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_shadow' },
        fragment = { module = sh, entryPoint = 'fs_shadow' },
        vertexLayout = vl,
        bindGroupLayouts = { layout },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'always', write = false },
        sampleCount = self.samples,
    })
    self.pCloth = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_cloth' },
        fragment = { module = sh, entryPoint = 'fs_cloth' },
        vertexLayout = vl,
        bindGroupLayouts = { layout },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = self.samples,
    })
    local ubo = GPUBuffer.new({ size = 48, usage = 'uniform', label = 'cloth' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = layout, ubos = { { slot = 0, buffer = ubo } } })
    self.vbuf = GPUBuffer.new({ size = NV * 32, usage = 'vertex', label = 'cloth verts' })
    local n = (NX - 1) * (NY - 1) * 6
    local ib = buffer.create(n * 2)
    local o = 0
    for j = 0, NY - 2 do
        for i = 0, NX - 2 do
            local a = j * NX + i
            local b = a + 1
            local c = a + NX
            local d = c + 1
            for _, v in { a, c, b, b, c, d } do
                buffer.writeu16(ib, o, v)
                o += 2
            end
        end
    end
    self.ibuf = GPUBuffer.new({ size = n * 2, usage = 'index', data = ib, immutable = true, label = 'cloth tris' })
    self.icount = n
    self.gpu = true
    return true
end

local function allocate(self: Cloth)
    local ctx = self.ctx
    if ctx == nil or not self.gpu then
        return
    end
    local w = math.ceil(self.size.x * self.scale)
    local h = math.ceil(BAND_H * self.kc * self.scale)
    self.gc = ctx:gpuCanvas({ width = w, height = h })
    if self.samples > 1 then
        self.msaa = GPUTexture.new({ width = w, height = h, format = 'rgba8unorm', renderTarget = true,
            sampleCount = self.samples, label = 'cloth msaa' }):view()
    end
    self.depth = GPUTexture.new({ width = w, height = h, format = 'depth32float', renderTarget = true,
        sampleCount = self.samples, label = 'cloth depth' }):view()
end

function resize(self: Cloth, size: Vector, scale: number)
    local sc = math.min(if scale > 0 then scale else 1, 2)
    if size.x <= 0 or size.y <= 0 then
        return
    end
    if self.gc ~= nil and sc == self.scale and size.x == self.size.x and size.y == self.size.y then
        return
    end
    self.size = size
    self.scale = sc
    self.kc = math.clamp(math.min(math.sqrt(size.x * size.y / (BW * BH)), size.y / 600), 0.6, 1.5)
    self.simW = size.x / self.kc
    self.xk = self.simW / BW
    allocate(self)
end

-- simulation units -> stage points: the master's bottom edge sits on the stage's
local function toStage(self: Cloth): Mat2D
    return Mat2D.withTranslation(0, self.size.y - BH * self.kc) * Mat2D.withScale(self.kc, self.kc)
end

local function frozen(self: Cloth): boolean
    local vm = self.vm
    if vm == nil then
        return false
    end
    local b = vm:getBoolean('motionFrozen')
    return b ~= nil and b.value
end

function advance(self: Cloth, seconds: number): boolean
    local p = clamp01(self.progress)
    if p <= 0 or p >= 1 then
        if self.active then
            self.active = false
            reset(self)
        end
        self.lastP = p
        return false
    end
    if p < self.lastP - 0.02 then
        reset(self) -- restarted by rapid navigation: a fresh pull
    end
    if not self.active then
        self.active = true
        self.sdir = if self.dir >= 0 then 1 else -1
        reset(self)
    end
    self.lastP = p
    if frozen(self) or seconds <= 0 then
        return true
    end
    local target = clamp01((p - P0) / (1 - P0))
    if target <= self.s then
        return true
    end
    -- two substeps per frame, following the keyed progress exactly
    local s0 = self.s
    local n = 1
    for k = 1, n do
        step(self, seconds / n, s0 + (target - s0) * k / n)
    end
    self.s = target
    stepRiders(self, seconds)
    return true
end

-- world position of particle k after mirroring for direction
local function wx(self: Cloth, k: number): number
    local x = self.px[k] + self.hx
    return if self.sdir >= 0 then x else self.simW - x
end

local function writeVertices(self: Cloth)
    local b = self.vstage
    local px, py, pz = self.px, self.py, self.pz
    local o = 0
    for j = 0, NY - 1 do
        for i = 0, NX - 1 do
            local k = idx(i, j)
            local il, ir = math.max(i - 1, 0), math.min(i + 1, NX - 1)
            local jd, ju = math.max(j - 1, 0), math.min(j + 1, NY - 1)
            local ax, ay, az = px[idx(ir, j)] - px[idx(il, j)], py[idx(ir, j)] - py[idx(il, j)], pz[idx(ir, j)] - pz[idx(il, j)]
            local bx, by, bz = px[idx(i, ju)] - px[idx(i, jd)], py[idx(i, ju)] - py[idx(i, jd)], pz[idx(i, ju)] - pz[idx(i, jd)]
            -- n = a x b, oriented so the flat cloth faces up (+z)
            local nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
            local l = math.sqrt(nx * nx + ny * ny + nz * nz)
            if l < 1e-6 then
                nx, ny, nz, l = 0, 0, 1, 1
            end
            if self.sdir < 0 then
                nx = -nx
            end
            buffer.writef32(b, o, wx(self, k))
            buffer.writef32(b, o + 4, py[k] + self.hy)
            buffer.writef32(b, o + 8, math.max(pz[k] + self.hz, 0))
            buffer.writef32(b, o + 12, nx / l)
            buffer.writef32(b, o + 16, ny / l)
            buffer.writef32(b, o + 20, nz / l)
            buffer.writef32(b, o + 24, i / (NX - 1))
            buffer.writef32(b, o + 28, j / (NY - 1))
            o += 32
        end
    end
end

local function drawRiders(self: Cloth, renderer: Renderer)
    -- riders still airborne at the end fade out instead of popping
    local q = clamp01((self.progress - 0.84) / 0.13)
    local fade = 1 - q * q * (3 - 2 * q)
    if fade <= 0 then
        return
    end
    for _, r in self.riders do
        local art = self.arts[r.art]
        local x = if self.sdir >= 0 then r.x else self.simW - r.x
        local sy = r.y - r.z * LIFT
        if art ~= nil and sy < 900 and x > -80 and x < self.simW + 80 then
            local sc = 0.62 + math.max(r.z, 0) * 0.0011
            renderer:save()
            renderer:modulateOpacity(fade)
            renderer:transform(Mat2D.withTranslation(x, sy) * Mat2D.withRotation(r.rot * self.sdir)
                * Mat2D.withScale(sc, sc) * Mat2D.withTranslation(-50, -50))
            art:draw(renderer)
            renderer:restore()
        end
    end
end

local function fallback(self: Cloth, renderer: Renderer)
    local path, paint = self.quad, self.qpaint
    for j = 0, NY - 2 do
        for i = 0, NX - 2 do
            local k1, k2, k3, k4 = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            path:reset()
            local first = true
            for _, k in { k1, k2, k3, k4 } do
                local v = Vector.xy(wx(self, k), self.py[k] + self.hy - math.max(self.pz[k] + self.hz, 0) * LIFT)
                if first then
                    path:moveTo(v)
                    first = false
                else
                    path:lineTo(v)
                end
            end
            path:close()
            local check = (math.floor(i / 2.5) % 2) + (math.floor(j / 2.5) % 2)
            paint.color = if check == 2 then Color.rgb(77, 118, 85) elseif check == 1 then Color.rgb(170, 186, 150)
                else Color.rgb(253, 245, 225)
            renderer:drawPath(path, paint)
        end
    end
end

function draw(self: Cloth, renderer: Renderer)
    if not self.active or self.s <= 0 then
        return
    end
    local gc, pc, ps, ubo, g, vb, ib, depth = self.gc, self.pCloth, self.pShadow, self.ubo, self.group, self.vbuf,
        self.ibuf, self.depth
    if not self.gpu or gc == nil or pc == nil or ps == nil or ubo == nil or g == nil or vb == nil or ib == nil
        or depth == nil then
        renderer:save()
        renderer:transform(toStage(self))
        fallback(self, renderer)
        drawRiders(self, renderer)
        renderer:restore()
        return
    end
    writeVertices(self)
    vb:write(self.vstage)
    local u = self.ustage
    local vals = { self.simW, BAND_H, BAND_TOP, LIFT, -0.42 * self.sdir, -0.5, 0.76, 0.3, 12, 5.5, 0.26, self.scale * self.kc }
    for i, v in vals do
        buffer.writef32(u, (i - 1) * 4, v)
    end
    ubo:write(u)
    local pass: GPURenderPass
    local msaa = self.msaa
    if msaa ~= nil then
        pass = gc:beginRenderPass({
            color = { { view = msaa, resolveTarget = gc:colorView(), loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'cloth',
        })
    else
        pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'cloth',
        })
    end
    pass:setBindGroup(0, g)
    pass:setVertexBuffer(0, vb)
    pass:setIndexBuffer(ib, 'uint16')
    pass:setPipeline(ps)
    pass:drawIndexed(self.icount)
    pass:setPipeline(pc)
    pass:drawIndexed(self.icount)
    pass:finish()
    renderer:save()
    renderer:transform(Mat2D.withTranslation(0, self.size.y - BAND_H * self.kc) * Mat2D.withScale(1 / self.scale, 1 / self.scale))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
    renderer:save()
    renderer:transform(toStage(self))
    drawRiders(self, renderer)
    renderer:restore()
end

return function(context: Context): Layout<Cloth>
    return {
        progress = 0,
        dir = 1,
        rider1 = late(),
        rider2 = late(),
        rider3 = late(),
        rider4 = late(),
        ctx = nil,
        vm = nil,
        size = Vector.xy(BW, BH),
        scale = 1,
        kc = 1,
        simW = BW,
        xk = 1,
        px = table.create(NV, 0), py = table.create(NV, 0), pz = table.create(NV, 0),
        qx = table.create(NV, 0), qy = table.create(NV, 0), qz = table.create(NV, 0),
        ca = {}, cb = {}, cr = {},
        tether = table.create(NV, 0),
        active = false,
        s = 0,
        hx = 0, hy = 0, hz = 0,
        vx = 0, vy = 0, vz = 0,
        sdir = 1,
        lastP = 0,
        riders = {},
        arts = {},
        gpu = false,
        gc = nil,
        msaa = nil,
        depth = nil,
        samples = 1,
        pCloth = nil,
        pShadow = nil,
        layout = nil,
        group = nil,
        ubo = nil,
        vbuf = nil,
        ibuf = nil,
        icount = 0,
        vstage = buffer.create(NV * 32),
        ustage = buffer.create(48),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        quad = Path.new(),
        qpaint = Paint.with({ style = 'fill', color = Color.rgb(253, 245, 225) }),
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
