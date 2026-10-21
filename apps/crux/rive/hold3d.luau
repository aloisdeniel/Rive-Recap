--!strict
-- Crux 3D hold: a real, lit, faceted climbing hold rendered on the GPU and drawn in
-- the hosting node's local space, so keyed position / scale / 2D rotation still apply.
--
-- Every value comes in through ScriptInputs: the timelines key yaw / pitch / progress,
-- `live` gates the GPU work to the scene that is on screen, and `still` (reducedMotion)
-- and `paused` (isPaused) freeze the idle sway. A canvas is only re-rendered when the
-- pose changes; a settled, still hold costs one image draw.
--
-- Trail mode (copies > 1) draws the same mesh several times in one pass, as a solid
-- head, a solid anchor and translucent ghosts between them.

type Hold3D = {
    size: Input<number>,
    kind: Input<number>,
    color: Input<Color>,
    yaw: Input<number>,
    pitch: Input<number>,
    roll: Input<number>,
    bolt: Input<number>,
    speck: Input<number>,
    live: Input<number>,
    sway: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    extent: Input<number>,
    extentW: Input<number>,
    copies: Input<number>,
    progress: Input<number>,
    trailX: Input<number>,
    trailY: Input<number>,
    trailWave: Input<number>,
    trailSpin: Input<number>,
    trailShrink: Input<number>,
    ghost: Input<number>,
    ctx: Context?,
    gpu: boolean,
    canvas: GPUCanvas?,
    depth: GPUTexture?,
    pMain: GPUPipeline?,
    pLine: GPUPipeline?,
    pShadow: GPUPipeline?,
    pGhost: GPUPipeline?,
    vbuf: GPUBuffer?,
    vcount: number,
    ubos: { GPUBuffer },
    groups: { GPUBindGroup },
    lineGroups: { GPUBindGroup },
    shadowGroups: { GPUBindGroup },
    lineUbos: { GPUBuffer },
    shadowUbos: { GPUBuffer },
    staging: buffer,
    sampler: ImageSampler,
    outline: Path,
    outlinePaint: Paint,
    bodyPaint: Paint,
    halfW: number,
    halfH: number,
    res: number,
    t: number,
    lastKey: string,
}

local RES = 2 -- canvas pixels per point: the 2x render is filtered down on 1x screens
local MAX_COPIES = 14
local FOV = math.rad(22)

-- Depth buffers are transient (cleared every pass), so holds of the same canvas
-- size share one. Keyed by pixel size.
local DEPTH: { [string]: GPUTexture } = {}
local MAX_PX = 1100

-- ------------------------------------------------------------------ mesh
local function icosa(): ({ { number } }, { { number } })
    local p = (1 + math.sqrt(5)) / 2
    local v = {
        { -1, p, 0 }, { 1, p, 0 }, { -1, -p, 0 }, { 1, -p, 0 },
        { 0, -1, p }, { 0, 1, p }, { 0, -1, -p }, { 0, 1, -p },
        { p, 0, -1 }, { p, 0, 1 }, { -p, 0, -1 }, { -p, 0, 1 },
    }
    local f = {
        { 1, 12, 6 }, { 1, 6, 2 }, { 1, 2, 8 }, { 1, 8, 11 }, { 1, 11, 12 },
        { 2, 6, 10 }, { 6, 12, 5 }, { 12, 11, 3 }, { 11, 8, 7 }, { 8, 2, 9 },
        { 4, 10, 5 }, { 4, 5, 3 }, { 4, 3, 7 }, { 4, 7, 9 }, { 4, 9, 10 },
        { 5, 10, 6 }, { 3, 5, 12 }, { 7, 3, 11 }, { 9, 7, 8 }, { 10, 9, 2 },
    }
    for _, q in ipairs(v) do
        local l = math.sqrt(q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
        q[1] /= l
        q[2] /= l
        q[3] /= l
    end
    return v, f
end

local function subdivide(v: { { number } }, f: { { number } }): { { number } }
    local cache: { [string]: number } = {}
    local function mid(a: number, b: number): number
        local key = if a < b then tostring(a) .. ':' .. tostring(b) else tostring(b) .. ':' .. tostring(a)
        local hit = cache[key]
        if hit then
            return hit
        end
        local x = (v[a][1] + v[b][1]) * 0.5
        local y = (v[a][2] + v[b][2]) * 0.5
        local z = (v[a][3] + v[b][3]) * 0.5
        local l = math.sqrt(x * x + y * y + z * z)
        table.insert(v, { x / l, y / l, z / l })
        cache[key] = #v
        return #v
    end
    local out: { { number } } = {}
    for _, t in ipairs(f) do
        local a = mid(t[1], t[2])
        local b = mid(t[2], t[3])
        local c = mid(t[3], t[1])
        table.insert(out, { t[1], a, c })
        table.insert(out, { t[2], b, a })
        table.insert(out, { t[3], c, b })
        table.insert(out, { a, b, c })
    end
    return out
end

-- kind -> subdivisions, scale x / y / z, lumpiness, seed
local KINDS = {
    { 1, 1.30, 0.82, 0.62, 0.16, 3 }, -- 0 jug
    { 0, 1.05, 1.10, 0.95, 0.10, 7 }, -- 1 pyramid: chunky facets
    { 1, 1.40, 0.72, 0.42, 0.10, 5 }, -- 2 sloper
    { 0, 0.72, 1.12, 0.66, 0.14, 9 }, -- 3 pinch
    { 1, 1.45, 0.46, 0.40, 0.08, 4 }, -- 4 crimp
    { 2, 1.22, 0.78, 0.72, 0.07, 6 }, -- 5 stone: smooth
    { 0, 1.00, 0.95, 0.80, 0.22, 2 }, -- 6 volume: angular, irregular
}

local function lump(x: number, y: number, z: number, seed: number): number
    return math.sin(x * 3.1 + seed) * math.cos(y * 2.7 - seed * 0.7) * 0.6
        + math.sin(z * 4.3 + x * 1.7 + seed * 1.3) * 0.4
end

local function kindSpec(self: Hold3D): { number }
    local k = math.clamp(math.floor(self.kind + 0.5), 0, #KINDS - 1)
    return KINDS[k + 1]
end

local function buildMesh(self: Hold3D)
    local spec = kindSpec(self)
    local v: { { number } }, f: { { number } } = icosa()
    for _ = 1, spec[1] do
        f = subdivide(v, f)
    end
    local P: { { number } } = {}
    for i, q in ipairs(v) do
        local r = 1 + spec[5] * lump(q[1], q[2], q[3], spec[6])
        local z = q[3] * r * spec[4]
        if z < 0 then
            z = 0 -- holds are flat where they meet the wall
        end
        P[i] = { q[1] * r * spec[2], q[2] * r * spec[3], z }
    end
    local n = #f * 3
    local stride = 36
    local data = buffer.create(n * stride)
    local o = 0
    for _, t in ipairs(f) do
        local a: { number }, b: { number }, c: { number } = P[t[1]], P[t[2]], P[t[3]]
        local ux, uy, uz = b[1] - a[1], b[2] - a[2], b[3] - a[3]
        local vx, vy, vz = c[1] - a[1], c[2] - a[2], c[3] - a[3]
        local nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        local l = math.sqrt(nx * nx + ny * ny + nz * nz)
        if l < 1e-9 then
            l = 1
        end
        nx /= l
        ny /= l
        nz /= l
        local cx, cy, cz = (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3, (a[3] + b[3] + c[3]) / 3
        local order = { a, b, c }
        if nx * cx + ny * cy + nz * (cz - 0.2) < 0 then
            nx, ny, nz = -nx, -ny, -nz
            order = { a, c, b }
        end
        for _, p in ipairs(order) do
            buffer.writef32(data, o, p[1])
            buffer.writef32(data, o + 4, p[2])
            buffer.writef32(data, o + 8, p[3])
            buffer.writef32(data, o + 12, nx)
            buffer.writef32(data, o + 16, ny)
            buffer.writef32(data, o + 20, nz)
            local sz = p[3] - 0.15
            local sl = math.sqrt(p[1] * p[1] + p[2] * p[2] + sz * sz)
            if sl < 1e-6 then
                sl = 1
            end
            buffer.writef32(data, o + 24, p[1] / sl)
            buffer.writef32(data, o + 28, p[2] / sl)
            buffer.writef32(data, o + 32, sz / sl)
            o += stride
        end
    end
    self.vbuf = GPUBuffer.new({ size = n * stride, usage = 'vertex', data = data, immutable = true, label = 'hold mesh' })
    self.vcount = n
end

-- Vector silhouette used only where the runtime has no GPU canvas.
local function buildFallback(self: Hold3D)
    local spec = kindSpec(self)
    local r = self.size * 0.5
    local path = self.outline
    path:reset()
    for i = 0, 9 do
        local a = i / 10 * math.pi * 2
        local w = 1 + spec[5] * lump(math.cos(a), math.sin(a), 0.3, spec[6])
        local pt = Vector.xy(math.cos(a) * r * spec[2] * w, -math.sin(a) * r * spec[3] * w)
        if i == 0 then
            path:moveTo(pt)
        else
            path:lineTo(pt)
        end
    end
    path:close()
end

-- ------------------------------------------------------------------ lifecycle
function init(self: Hold3D, context: Context): boolean
    if self.gpu or self.ctx ~= nil then
        return true -- init can run more than once; build the GPU objects once
    end
    self.ctx = context
    buildFallback(self)
    local sh = context:shader('hold3d')
    if sh == nil then
        return true -- no GPU shaders on this runtime: draw the vector fallback
    end
    local layout: { VertexBufferLayout } = { {
        stride = 36,
        attributes = {
            { format = 'float32x3', slot = 0, offset = 0 },
            { format = 'float32x3', slot = 1, offset = 12 },
            { format = 'float32x3', slot = 2, offset = 24 },
        },
    } }
    local fmt: ColorFormat = 'rgba8unorm'
    local blend: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    self.pMain = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = layout,
        colorTargets = { { format = fmt } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
    })
    self.pLine = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_outline' },
        fragment = { module = sh, entryPoint = 'fs_flat' },
        vertexLayout = layout,
        colorTargets = { { format = fmt } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = 'front',
    })
    self.pShadow = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_shadow' },
        fragment = { module = sh, entryPoint = 'fs_flat' },
        vertexLayout = layout,
        colorTargets = { { format = fmt, blend = blend } },
        depthStencil = { format = 'depth32float', compare = 'always', write = false },
    })
    self.pGhost = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = layout,
        colorTargets = { { format = fmt, blend = blend } },
        depthStencil = { format = 'depth32float', compare = 'less', write = false },
        cullMode = 'back',
    })
    local copies = math.clamp(math.floor(self.copies + 0.5), 1, MAX_COPIES)
    for i = 1, copies do
        self.ubos[i] = GPUBuffer.new({ size = 256, usage = 'uniform', label = 'hold body' })
        self.lineUbos[i] = GPUBuffer.new({ size = 256, usage = 'uniform', label = 'hold line' })
        self.shadowUbos[i] = GPUBuffer.new({ size = 256, usage = 'uniform', label = 'hold shadow' })
        self.groups[i] = GPUBindGroup.new({ layout = (self.pMain :: GPUPipeline):getBindGroupLayout(0),
            ubos = { { slot = 0, buffer = self.ubos[i] } } })
        self.lineGroups[i] = GPUBindGroup.new({ layout = (self.pLine :: GPUPipeline):getBindGroupLayout(0),
            ubos = { { slot = 0, buffer = self.lineUbos[i] } } })
        self.shadowGroups[i] = GPUBindGroup.new({ layout = (self.pShadow :: GPUPipeline):getBindGroupLayout(0),
            ubos = { { slot = 0, buffer = self.shadowUbos[i] } } })
    end
    buildMesh(self)
    -- canvas in points, then pixels; very large trails trade resolution for memory
    local wPt = self.size * (if self.extentW > 0 then self.extentW else self.extent)
    local hPt = self.size * self.extent
    local res = math.min(RES, MAX_PX / math.max(wPt, hPt))
    local pw = math.max(32, math.ceil(wPt * res / 16) * 16)
    local ph = math.max(32, math.ceil(hPt * res / 16) * 16)
    self.res = res
    self.halfW = pw / res * 0.5
    self.halfH = ph / res * 0.5
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    local dk = tostring(pw) .. 'x' .. tostring(ph)
    local d = DEPTH[dk]
    if d == nil then
        d = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true, label = 'hold depth' })
        DEPTH[dk] = d
    end
    self.depth = d
    self.gpu = true
    return true
end

function advance(self: Hold3D, seconds: number): boolean
    if self.live >= 0.5 and not self.still and not self.paused and self.sway > 0 then
        self.t += seconds
    end
    return true
end

local function writeU(b: buffer, vp: Mat4, model: Mat4, rot: Mat4, col: { number }, shade: { number },
    params: { number }, light: { number })
    vp:writeToBuffer(b, 0)
    model:writeToBuffer(b, 64)
    rot:writeToBuffer(b, 128)
    for j = 1, 4 do
        local o = (j - 1) * 4
        buffer.writef32(b, 192 + o, col[j])
        buffer.writef32(b, 208 + o, shade[j])
        buffer.writef32(b, 224 + o, params[j])
        buffer.writef32(b, 240 + o, light[j])
    end
end

local function render(self: Hold3D, canvas: GPUCanvas, depth: GPUTexture, vbuf: GPUBuffer)
    local copies = #self.ubos
    local wob = 0
    local wob2 = 0
    if not self.still and self.sway > 0 then
        wob = math.sin(self.t * 1.25) * self.sway
        wob2 = math.sin(self.t * 0.8 + 1.1) * self.sway * 0.5
    end
    local spec = kindSpec(self)
    local unit = self.size * 0.5 -- points per object unit
    local hy = self.halfH / unit -- canvas half-height in object units
    local dist = hy / math.tan(FOV * 0.5)
    local cx, cy = 0, 0
    if copies > 1 then
        cx, cy = self.trailX * 0.5, self.trailY * 0.5 -- frame the whole trail
    end
    local view = Mat4.lookAt(Vector.xyz(cx, cy, dist), Vector.xyz(cx, cy, 0), Vector.xyz(0, 1, 0))
    local proj = Mat4.perspective(FOV, self.halfW / self.halfH, math.max(0.1, dist - 8), dist + 8)
    local vp = proj * view
    local c = Color.toFloat(self.color)
    local shade = { c[1] * 0.42 + 0.03, c[2] * 0.44 + 0.03, c[3] * 0.5 + 0.03, 1 }
    -- light and shadow stay fixed on screen: the node's authored roll is undone in draw
    local light = { -0.62, 0.72, 0.42, 0.18 }
    local coal = { 0.125, 0.133, 0.122, 1 }
    local shadowCol = { 0.125, 0.133, 0.122, 0.26 }
    local params = { self.speck, spec[6] * 7, self.bolt, 0 }
    local lineParams = { self.speck, spec[6] * 7, self.bolt, 0.075 }
    local prog = math.clamp(self.progress, 0, 1)
    local b = self.staging
    local drawList: { { number } } = {}
    for i = 1, copies do
        local t = if copies > 1 then (i - 1) / (copies - 1) else 0
        local head = copies > 1 and i == copies
        if copies > 1 then
            if head then
                t = prog
            elseif t > prog then
                continue
            end
        end
        local sc = 1 - self.trailShrink * t
        local ox = self.trailX * t + math.sin(t * math.pi * 1.7) * self.trailWave
        local oy = self.trailY * t
        local rot = Mat4.fromRotationZ(-self.roll) * Mat4.fromRotationX(self.pitch - 0.42 + wob2)
            * Mat4.fromRotationY(self.yaw + 0.35 + wob + self.trailSpin * t)
        local model = Mat4.fromTranslation(ox, oy, 0) * Mat4.fromScale(sc) * rot
        local solid = copies == 1 or i == 1 or head
        local col = { c[1], c[2], c[3], 1 }
        if not solid then
            local g = self.ghost
            col = { c[1] * 0.6 + 0.38, c[2] * 0.6 + 0.37, c[3] * 0.6 + 0.36, g * (0.55 + 0.45 * t) }
        end
        writeU(b, vp, model, rot, col, shade, params, light)
        self.ubos[i]:write(b)
        if solid then
            writeU(b, vp, model, rot, col, coal, lineParams, light)
            self.lineUbos[i]:write(b)
            writeU(b, vp, model, rot, col, shadowCol, params, light)
            self.shadowUbos[i]:write(b)
        end
        table.insert(drawList, { i, if solid then 1 else 0 })
    end
    local pass = canvas:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
        label = 'hold',
    })
    pass:setVertexBuffer(0, vbuf)
    pass:setPipeline(self.pShadow :: GPUPipeline)
    for _, e in ipairs(drawList) do
        if e[2] == 1 then
            pass:setBindGroup(0, self.shadowGroups[e[1]])
            pass:draw(self.vcount)
        end
    end
    for _, e in ipairs(drawList) do
        if e[2] == 1 then
            pass:setPipeline(self.pLine :: GPUPipeline)
            pass:setBindGroup(0, self.lineGroups[e[1]])
            pass:draw(self.vcount)
            pass:setPipeline(self.pMain :: GPUPipeline)
            pass:setBindGroup(0, self.groups[e[1]])
            pass:draw(self.vcount)
        end
    end
    -- ghosts last, far to near, blended over the solids
    pass:setPipeline(self.pGhost :: GPUPipeline)
    for j = #drawList, 1, -1 do
        local e = drawList[j]
        if e[2] == 0 then
            pass:setBindGroup(0, self.groups[e[1]])
            pass:draw(self.vcount)
        end
    end
    pass:finish()
end

function draw(self: Hold3D, renderer: Renderer)
    if self.live < 0.5 then
        return -- off-screen scene: no GPU work at all
    end
    local canvas = self.canvas
    local vbuf = self.vbuf
    local depth = self.depth
    if not self.gpu or canvas == nil or vbuf == nil or depth == nil then
        self.bodyPaint.color = self.color
        renderer:drawPath(self.outline, self.bodyPaint)
        renderer:drawPath(self.outline, self.outlinePaint)
        return
    end
    -- only re-render the canvas when the pose changed; its contents persist
    local key = string.format('%.4f|%.4f|%.4f|%.4f|%.4f|%s', self.yaw, self.pitch, self.roll,
        if self.still then 0 else self.t, self.progress, tostring(self.color))
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas, depth, vbuf)
    end
    local k = self.size * 0.5
    local ox, oy = 0, 0
    if #self.ubos > 1 then
        ox, oy = self.trailX * 0.5 * k, -self.trailY * 0.5 * k
    end
    renderer:save()
    renderer:transform(Mat2D.withRotation(-self.roll) * Mat2D.withTranslation(ox - self.halfW, oy - self.halfH)
        * Mat2D.withScale(1 / self.res, 1 / self.res))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Hold3D>
    return {
        size = 120,
        kind = 0,
        color = Color.rgb(220, 255, 63),
        yaw = 0,
        pitch = 0,
        roll = 0,
        bolt = 0.13,
        speck = 0.5,
        live = 1,
        sway = 0,
        still = false,
        paused = false,
        extent = 1.7,
        extentW = 0,
        copies = 1,
        progress = 1,
        trailX = 0,
        trailY = 0,
        trailWave = 0,
        trailSpin = 0,
        trailShrink = 0,
        ghost = 0.4,
        ctx = nil,
        gpu = false,
        canvas = nil,
        depth = nil,
        pMain = nil,
        pLine = nil,
        pShadow = nil,
        pGhost = nil,
        vbuf = nil,
        vcount = 0,
        ubos = {},
        groups = {},
        lineGroups = {},
        shadowGroups = {},
        lineUbos = {},
        shadowUbos = {},
        staging = buffer.create(256),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        outline = Path.new(),
        outlinePaint = Paint.with({ style = 'stroke', thickness = 3, color = Color.rgb(32, 34, 31) }),
        bodyPaint = Paint.with({ color = Color.rgb(220, 255, 63) }),
        halfW = 60,
        halfH = 60,
        res = 2,
        t = 0,
        lastKey = '',
        init = init,
        advance = advance,
        draw = draw,
    }
end
