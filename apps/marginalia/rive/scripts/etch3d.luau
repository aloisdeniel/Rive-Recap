--!strict
-- Marginalia etched 3D (module): the shared GPU plumbing behind the scripted
-- 3D objects - the open books (scenes 3, 4, 8, 9), the paper theatre (5) and
-- the reading lamp with its stack of volumes (7). Each object is a
-- ScriptedDrawable that describes itself as a list of parametric *patches*
-- (shaders/etch3d.wgsl) and lets this module draw them.
--
--   E.new(context, beam)        pipelines + uniform buffer (nil without shaders)
--   E.clear / E.add             the patch list for this frame (<= 96 patches)
--   E.camera / E.light / E.spot / E.beam   scene globals
--   E.ensure(e, box, k)         canvases sized to the box at k px per unit
--   E.render / E.renderBeam     one MSAA pass (depth tested) / the light pass
--   E.draw / E.drawBeam         composite into the drawable's own space
--   E.Clock                     entrance clock shared by the drawables
--
-- Patterns follow scripts/pagestage.luau and scripts/moon.luau: one explicit
-- bind-group layout shared by two pipelines, 4x MSAA resolved into the canvas,
-- canvases (re)created only when their pixel size changes, nothing allocated
-- per frame, no `discard`.

local Resp = require('scripts/responsive')

local E = {}

export type Mat = { number } -- affine 3x4, row-major (12 numbers)

export type Box = { x: number, y: number, w: number, h: number }

export type Etch = {
    pipe: GPUPipeline,
    ids: GPUBuffer,
    beamPipe: GPUPipeline?,
    ubo: GPUBuffer,
    group: GPUBindGroup,
    staging: buffer,
    n: number,
    samples: number,
    ctx: Context,
    gc: GPUCanvas?,
    colorView: GPUTextureView?,
    msaa: GPUTextureView?,
    depth: GPUTextureView?,
    bc: GPUCanvas?,
    beamView: GPUTextureView?,
    keyPath: Path,
    keyKey: string,
    pw: number,
    ph: number,
    box: Box,
    k: number,
    sampler: ImageSampler,
}

local GSIZE = 14 * 16 -- globals: 14 vec4
local PSIZE = 8 * 16 -- one patch: 8 vec4
E.MAXP = 96
local USIZE = GSIZE + E.MAXP * PSIZE
local GRID = 40 * 10 * 6 -- vertices per patch (shader: GU x GV cells)
local MAX_PX = 4200000 -- per canvas, as the page leaves

-- material ids (shader fs_main)
E.PAINT, E.PAGE, E.EDGES, E.BRASS, E.GLOW, E.SHADOW, E.CLOTH, E.NIGHT, E.BOARDS, E.VELVET =
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9
-- patch kinds (shader surf)
E.QUAD, E.FRUSTUM, E.SPHERE, E.PAGES, E.ARCH, E.CURTAIN, E.FACE = 0, 1, 2, 3, 4, 5, 6

-- ------------------------------------------------------------ matrices
function E.ident(): Mat
    return { 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0 }
end

function E.mul(a: Mat, b: Mat): Mat
    local r = table.create(12, 0)
    for i = 0, 2 do
        for j = 0, 3 do
            local s = a[i * 4 + 1] * b[j + 1] + a[i * 4 + 2] * b[4 + j + 1] + a[i * 4 + 3] * b[8 + j + 1]
            if j == 3 then
                s += a[i * 4 + 4]
            end
            r[i * 4 + j + 1] = s
        end
    end
    return r
end

-- chain(A, B, C) = A * B * C (C applies first)
function E.chain(...: Mat): Mat
    local args = { ... }
    local m = args[1]
    for i = 2, #args do
        m = E.mul(m, args[i])
    end
    return m
end

function E.T(x: number, y: number, z: number): Mat
    return { 1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z }
end

function E.S(x: number, y: number, z: number): Mat
    return { x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0 }
end

function E.RX(a: number): Mat
    local c, s = math.cos(a), math.sin(a)
    return { 1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0 }
end

function E.RY(a: number): Mat
    local c, s = math.cos(a), math.sin(a)
    return { c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0 }
end

function E.RZ(a: number): Mat
    local c, s = math.cos(a), math.sin(a)
    return { c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0 }
end

-- a frame whose +Y runs from a to b (for frustums along a segment)
function E.along(ax: number, ay: number, az: number, bx: number, by: number, bz: number): (Mat, number)
    local dx, dy, dz = bx - ax, by - ay, bz - az
    local len = math.sqrt(dx * dx + dy * dy + dz * dz)
    if len < 1e-6 then
        return E.T(ax, ay, az), 0
    end
    local yx, yy, yz = dx / len, dy / len, dz / len
    -- any vector not parallel to y
    local tx, ty, tz = 0, 0, 1
    if math.abs(yz) > 0.9 then
        tx, ty, tz = 1, 0, 0
    end
    -- x = normalize(t cross y), z = x cross y
    local xx, xy, xz = ty * yz - tz * yy, tz * yx - tx * yz, tx * yy - ty * yx
    local xl = math.sqrt(xx * xx + xy * xy + xz * xz)
    xx, xy, xz = xx / xl, xy / xl, xz / xl
    local zx, zy, zz = xy * yz - xz * yy, xz * yx - xx * yz, xx * yy - xy * yx
    return { xx, yx, zx, ax, xy, yy, zy, ay, xz, yz, zz, az }, len
end

-- ------------------------------------------------------------ setup
function E.new(context: Context, withBeam: boolean): Etch?
    local sh = context:shader('shaders/etch3d')
    if sh == nil then
        return nil
    end
    local f = context:features()
    local samples = if f.maxSamples >= 4 then 4 else 1
    local layout = GPUBindGroupLayout.new({ shader = sh, groupIndex = 0, label = 'etch3d' })
    local over: BlendState = {
        srcColor = 'one', dstColor = 'one-minus-src-alpha', srcAlpha = 'one', dstAlpha = 'one-minus-src-alpha',
    }
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = { { stride = 4, stepMode = 'instance',
            attributes = { { format = 'float32', slot = 0, offset = 0 } } } },
        bindGroupLayouts = { layout },
        colorTargets = { { format = 'rgba8unorm', blend = over } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        sampleCount = samples,
    })
    local beamPipe: GPUPipeline? = nil
    if withBeam then
        beamPipe = GPUPipeline.new({
            vertex = { module = sh, entryPoint = 'vs_quad' },
            fragment = { module = sh, entryPoint = 'fs_beam' },
            vertexLayout = {},
            bindGroupLayouts = { layout },
            colorTargets = { { format = 'rgba8unorm' } },
        })
    end
    local ubo = GPUBuffer.new({ size = USIZE, usage = 'uniform', label = 'etch3d' })
    -- patch index per instance
    local idb = buffer.create(E.MAXP * 4)
    for i = 0, E.MAXP - 1 do
        buffer.writef32(idb, i * 4, i)
    end
    local e: Etch = {
        pipe = pipe,
        ids = GPUBuffer.new({ size = E.MAXP * 4, usage = 'vertex', data = idb, immutable = true, label = 'patch ids' }),
        beamPipe = beamPipe,
        ubo = ubo,
        group = GPUBindGroup.new({ layout = layout, ubos = { { slot = 0, buffer = ubo } } }),
        staging = buffer.create(USIZE),
        n = 0,
        samples = samples,
        ctx = context,
        gc = nil,
        colorView = nil,
        msaa = nil,
        depth = nil,
        bc = nil,
        beamView = nil,
        keyPath = Path.new(),
        keyKey = '',
        pw = 0,
        ph = 0,
        box = { x = 0, y = 0, w = 1, h = 1 },
        k = 1,
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
    }
    -- sensible defaults
    E.camera(e, 0.5, 0, 900, 400)
    E.light(e, -0.45, 0.8, 0.5, 0.75, 0.42, 0.40, 0.36, 0.8)
    E.ink(e, 0x3A2E24)
    E.nospot(e)
    return e
end

local function g4(e: Etch, slot: number, a: number, b: number, c: number, d: number)
    local o = slot * 16
    local s = e.staging
    buffer.writef32(s, o, a)
    buffer.writef32(s, o + 4, b)
    buffer.writef32(s, o + 8, c)
    buffer.writef32(s, o + 12, d)
end

local function rgb(c: number): (number, number, number)
    return bit32.band(bit32.rshift(c, 16), 255) / 255, bit32.band(bit32.rshift(c, 8), 255) / 255,
        bit32.band(c, 255) / 255
end
E.rgb = rgb

-- pitch: radians the camera looks down; D: camera distance; R: depth half-range;
-- look: the height (world y) of the point the camera looks at, on the axis
function E.camera(e: Etch, pitch: number, yaw: number, D: number, R: number, look: number?)
    local ly = look or 0
    local cp, sp = math.cos(pitch), math.sin(pitch)
    g4(e, 0, cp, sp, D, R)
    -- camera position in world: inverse of (yaw, then pitch) applied to (0, 0, D)
    local vy, vz = sp * D, cp * D
    local cy, sy = math.cos(yaw), math.sin(yaw)
    g4(e, 1, -sy * vz, vy + ly, cy * vz, e.k)
    g4(e, 13, cy, sy, ly, 0)
end

-- project a world point into drawable space (same maths as the shader)
function E.project(e: Etch, x: number, y: number, z: number): (number, number)
    local s = e.staging
    local cp, sp, D = buffer.readf32(s, 0), buffer.readf32(s, 4), buffer.readf32(s, 8)
    local cy, sy, ly = buffer.readf32(s, 13 * 16), buffer.readf32(s, 13 * 16 + 4), buffer.readf32(s, 13 * 16 + 8)
    local x1 = cy * x + sy * z
    local z1 = -sy * x + cy * z
    local y1 = y - ly
    local vy = cp * y1 - sp * z1
    local vz = sp * y1 + cp * z1
    local f = D / math.max(D - vz, 1)
    return x1 * f, -vy * f - ly
end

function E.light(e: Etch, kx: number, ky: number, kz: number, strength: number, ar: number, ag: number,
    ab: number, etch: number)
    local l = math.sqrt(kx * kx + ky * ky + kz * kz)
    g4(e, 3, kx / l, ky / l, kz / l, strength)
    g4(e, 4, ar, ag, ab, etch)
end

function E.ink(e: Etch, c: number)
    local r, g, b = rgb(c)
    local s = e.staging
    g4(e, 8, r, g, b, buffer.readf32(s, 8 * 16 + 12))
end

function E.nospot(e: Etch)
    g4(e, 5, 0, 0, 0, 0)
end

function E.spot(e: Etch, px: number, py: number, pz: number, dx: number, dy: number, dz: number, outer: number,
    inner: number, c: number, intensity: number, range: number)
    g4(e, 5, px, py, pz, intensity)
    local l = math.sqrt(dx * dx + dy * dy + dz * dz)
    g4(e, 6, dx / l, dy / l, dz / l, math.cos(outer))
    local r, g, b = rgb(c)
    g4(e, 7, r, g, b, math.cos(inner))
    local s = e.staging
    g4(e, 8, buffer.readf32(s, 8 * 16), buffer.readf32(s, 8 * 16 + 4), buffer.readf32(s, 8 * 16 + 8), range)
end

-- the light pass (drawable space): apex, direction, mouth radius, spread, length,
-- intensity; pool centre/radii; dim, time, motes, pool strength
function E.beam(e: Etch, ax: number, ay: number, dx: number, dy: number, mouth: number, spread: number,
    len: number, intensity: number, cx: number, cy: number, rx: number, ry: number, dim: number, time: number,
    motes: number, pool: number)
    local l = math.sqrt(dx * dx + dy * dy)
    g4(e, 9, ax, ay, dx / l, dy / l)
    g4(e, 10, mouth, spread, len, intensity)
    g4(e, 11, cx, cy, rx, ry)
    g4(e, 12, dim, time, motes, pool)
end

-- ------------------------------------------------------------ patches
function E.clear(e: Etch)
    e.n = 0
end

-- kind, seven params, model, colour (0xRRGGBB), material,
-- hatch direction (patch space) + lines per unit, ex = lit, detail, emissive,
-- and how strongly its hatching prints (default 1)
function E.add(e: Etch, kind: number, p1: number, p2: number, p3: number, p4: number, p5: number, p6: number,
    p7: number, m: Mat, c: number, mat: number, hx: number, hy: number, hz: number, hd: number, lit: number,
    detail: number, emis: number, inkAmt: number?)
    if e.n >= E.MAXP then
        return
    end
    local o = GSIZE + e.n * PSIZE
    local s = e.staging
    local function w4(off: number, a: number, b: number, cc: number, d: number)
        buffer.writef32(s, o + off, a)
        buffer.writef32(s, o + off + 4, b)
        buffer.writef32(s, o + off + 8, cc)
        buffer.writef32(s, o + off + 12, d)
    end
    w4(0, kind, p1, p2, p3)
    w4(16, p4, p5, p6, p7)
    w4(32, m[1], m[2], m[3], m[4])
    w4(48, m[5], m[6], m[7], m[8])
    w4(64, m[9], m[10], m[11], m[12])
    local r, g, b = rgb(c)
    w4(80, r, g, b, mat)
    w4(96, hx, hy, hz, hd)
    w4(112, lit, detail, emis, inkAmt or 1)
    e.n += 1
end

-- ------------------------------------------------------------ surfaces
-- Canvases cover `box` (drawable space) at k pixels per unit, capped.
-- Returns true when they were (re)created (the caller re-renders).
function E.ensure(e: Etch, box: Box, k: number, beam: boolean): boolean
    local kk = math.max(0.25, k)
    if box.w * box.h * kk * kk > MAX_PX then
        kk = math.sqrt(MAX_PX / (box.w * box.h))
    end
    local pw = math.max(1, math.ceil(box.w * kk))
    local ph = math.max(1, math.ceil(box.h * kk))
    e.box = box
    g4(e, 2, box.x, box.y, box.w, box.h)
    if pw == e.pw and ph == e.ph and e.gc ~= nil then
        return false
    end
    e.pw = pw
    e.ph = ph
    e.k = kk
    local gc = e.ctx:gpuCanvas({ width = pw, height = ph })
    e.gc = gc
    e.colorView = gc:colorView()
    if e.samples > 1 then
        e.msaa = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = e.samples, label = 'etch3d msaa' }):view()
    end
    e.depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = e.samples, label = 'etch3d depth' }):view()
    if beam and e.beamPipe ~= nil then
        local bc = e.ctx:gpuCanvas({ width = pw, height = ph })
        e.bc = bc
        e.beamView = bc:colorView()
    end
    -- eye.w carries the density (AA hints)
    local s = e.staging
    buffer.writef32(s, 16 + 12, kk)
    return true
end

function E.render(e: Etch)
    local gc, depth = e.gc, e.depth
    if gc == nil or depth == nil then
        return
    end
    e.ubo:write(e.staging, 0, 0, GSIZE + math.max(e.n, 1) * PSIZE)
    local pass: GPURenderPass
    local msaa = e.msaa
    if msaa ~= nil then
        pass = gc:beginRenderPass({
            color = { { view = msaa, resolveTarget = e.colorView, loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'etch3d',
        })
    else
        pass = gc:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth, depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'etch3d',
        })
    end
    if e.n > 0 then
        pass:setPipeline(e.pipe)
        pass:setBindGroup(0, e.group)
        pass:setVertexBuffer(0, e.ids)
        pass:draw(GRID, e.n)
    end
    pass:finish()
end

function E.renderBeam(e: Etch)
    local bc, bp = e.bc, e.beamPipe
    if bc == nil or bp == nil then
        return
    end
    e.ubo:write(e.staging, 0, 0, GSIZE + math.max(e.n, 1) * PSIZE)
    local pass = bc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'etch3d light',
    })
    pass:setPipeline(bp)
    pass:setBindGroup(0, e.group)
    pass:draw(6)
    pass:finish()
end

local function blit(e: Etch, renderer: Renderer, img: Image, opacity: number)
    local b = e.box
    renderer:save()
    renderer:transform(Mat2D.withTranslation(b.x, b.y) * Mat2D.withScale(b.w / e.pw, b.h / e.ph))
    renderer:drawImage(img, e.sampler, 'srcOver', opacity)
    renderer:restore()
end

function E.draw(e: Etch, renderer: Renderer, opacity: number?)
    local gc = e.gc
    if gc ~= nil then
        blit(e, renderer, gc.image, opacity or 1)
    end
end

function E.drawBeam(e: Etch, renderer: Renderer, opacity: number?)
    local bc = e.bc
    if bc ~= nil then
        blit(e, renderer, bc.image, opacity or 1)
    end
end

-- ------------------------------------------------------------ on a turning leaf
-- A turning page is rendered into a 2D canvas, which cannot show an image the
-- GPU made in the same frame. So the Page Stage renders such a page twice and
-- composites the objects itself (shaders/leafcomp.wgsl):
--   leafMode 1  the page's leaf texture: objects draw nothing (but still render)
--   leafMode 2  the key: objects fill their box with pure magenta
-- Each object registers its textures and box here (scene -> id -> entry).
E.leafMode = 0

export type Entry = {
    e: Etch,
    ox: number, -- the box's offset in the drawable's own space
    oy: number,
    beam: boolean,
    active: boolean,
}

E.reg = {} :: { [number]: { [number]: Entry } }

function E.register(scene: number, id: number, e: Etch, ox: number, oy: number, beam: boolean, active: boolean)
    local s = math.floor(scene + 0.5)
    local i = math.floor(id + 0.5)
    local page = E.reg[s]
    if page == nil then
        page = {}
        E.reg[s] = page
    end
    local en = page[i]
    if en == nil then
        page[i] = { e = e, ox = ox, oy = oy, beam = beam, active = active }
    else
        en.e = e
        en.ox = ox
        en.oy = oy
        en.beam = beam
        en.active = active
    end
end

local keyPaint = Paint.with({ color = Color.rgb(255, 0, 255), style = 'fill' })

-- draw the object for the current mode (normal / leaf texture / key)
function E.present(e: Etch, renderer: Renderer, beam: boolean)
    local m = E.leafMode
    if m == 1 then
        return
    end
    if m == 2 then
        local b = e.box
        local kk = b.x .. ',' .. b.y .. ',' .. b.w .. ',' .. b.h
        if kk ~= e.keyKey then
            -- (a path is only rebuilt when its box moves, never after a draw this frame)
            e.keyKey = kk
            local kp = Path.new()
            kp:moveTo(Vector.xy(b.x, b.y))
            kp:lineTo(Vector.xy(b.x + b.w, b.y))
            kp:lineTo(Vector.xy(b.x + b.w, b.y + b.h))
            kp:lineTo(Vector.xy(b.x, b.y + b.h))
            kp:close()
            e.keyPath = kp
        end
        renderer:drawPath(e.keyPath, keyPaint)
        return
    end
    E.draw(e, renderer)
    if beam then
        E.drawBeam(e, renderer)
    end
end

-- ------------------------------------------------------------ timing
-- The entrance clock of a drawable that belongs to one scene (and optionally
-- one persona row). It restarts when the scene (row) arrives going forward,
-- arrives settled going back or under reduced motion, freezes while paused,
-- and keeps the object drawable for a moment after the scene leaves (the
-- leaving page is still drawn as the turning leaf).
export type Clock = { t: number, here: boolean, left: number, init: boolean }

E.SETTLED = 1e6

function E.clock(): Clock
    return { t = E.SETTLED, here = false, left = E.SETTLED, init = false }
end

function E.tick(c: Clock, here: boolean, back: boolean, still: boolean, paused: boolean, seconds: number)
    if here and not c.here then
        c.t = if (still or back) then E.SETTLED else 0
        c.left = 0
    end
    c.here = here
    if here then
        c.left = 0
        if still then
            c.t = E.SETTLED
        elseif not paused then
            c.t += seconds
        end
    elseif not paused then
        c.left += seconds
    end
end

-- may it draw? (on its scene, or leaving for at most the turn hold)
function E.visible(c: Clock): boolean
    return c.here or c.left < 1.3
end

-- device pixels per design unit of a page's illustration: the art frame's
-- scale for this canvas (scripts/responsive.luau) x the device density
local cacheKey = ''
local cacheVal: { number } = {}
function E.artScale(scene: number, vw: number, vh: number, bp: number): number
    if vw <= 0 or vh <= 0 then
        return 1
    end
    local key = vw .. 'x' .. vh .. '@' .. bp
    if key ~= cacheKey then
        cacheKey = key
        cacheVal = {}
    end
    local v = cacheVal[scene]
    if v == nil then
        local c = Resp.chrome(vw, vh, Resp.breakpoint(bp))
        local p = Resp.plan(scene, c)
        v = math.max(p.art.sx, 0.2)
        cacheVal[scene] = v
    end
    return v
end

-- easing used by the drawables (match the timelines' "back", "out", "inout")
function E.clamp01(x: number): number
    return math.clamp(x, 0, 1)
end

function E.easeInOut(q: number): number
    q = math.clamp(q, 0, 1)
    return if q < 0.5 then 4 * q * q * q else 1 - (-2 * q + 2) ^ 3 / 2
end

function E.easeOut(q: number): number
    q = math.clamp(q, 0, 1)
    return 1 - (1 - q) ^ 3
end

function E.easeBack(q: number): number
    q = math.clamp(q, 0, 1)
    local c1 = 1.70158
    local c3 = c1 + 1
    return 1 + c3 * (q - 1) ^ 3 + c1 * (q - 1) ^ 2
end

-- progress of a tween [t0, t0 + dur] (ms) at clock time t (s)
function E.prog(t: number, t0: number, dur: number): number
    if dur <= 0 then
        return if t * 1000 >= t0 then 1 else 0
    end
    return math.clamp((t * 1000 - t0) / dur, 0, 1)
end

return E
