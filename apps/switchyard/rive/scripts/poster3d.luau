--!strict
-- Switchyard poster 3D (scripts/poster3d.wgsl): real 3D transit objects printed in
-- the recap's flat Swiss-poster palette, drawn into a GPU canvas in this node's
-- local space (top-left at the node origin, `w` x `h` points).
--
--   kind 0  a tram arriving on its track, ground stripes vanishing into the distance
--   kind 1  the intro's transit map: a cream board whose route ribbons and station
--           pucks assemble while the camera dives from a flat top-down plan into an
--           isometric view
--
-- Every value is a ScriptInput keyed by the state-machine timelines (the camera,
-- `build`, the tram's position) or by the scene's idle Joystick (`sway`), so
-- choreography stays in the timelines, pause freezes it and reduced motion holds
-- the settled pose. `w`, `h` and `res` (device pixels per point, bound to the
-- layout) may change at runtime: the canvas is re-allocated to match, so it is
-- always sized to its real box at device resolution. With `refW` > 0 the camera's
-- horizontal framing is authored for a `refW`-wide canvas and kept anchored to the
-- left edge (or the right edge with `alignR` = 1) when the canvas is wider. `live` (keyed per scene) skips all GPU work while hidden; the
-- canvas re-renders only when an input changed. With no GPU shader support the
-- script draws a flat vector stand-in.

type P3 = {
    kind: Input<number>,
    w: Input<number>,
    h: Input<number>,
    res: Input<number>,
    live: Input<number>,
    build: Input<number>,
    pitch: Input<number>,
    yaw: Input<number>,
    dist: Input<number>,
    fov: Input<number>,
    camX: Input<number>,
    camY: Input<number>,
    tz: Input<number>,
    sway: Input<number>,
    dim: Input<number>,
    outline: Input<number>,
    refW: Input<number>,
    alignR: Input<number>,
    gpu: boolean,
    samples: number,
    pw: number,
    ph: number,
    canvas: GPUCanvas?,
    msaaTex: GPUTexture?,
    depth: GPUTexture?,
    pMain: GPUPipeline?,
    pLine: GPUPipeline?,
    pGround: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    lineGroup: GPUBindGroup?,
    groundGroup: GPUBindGroup?,
    vbuf: GPUBuffer?,
    nOpaque: number,
    nOutline: number,
    nTotal: number,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    lastKey: string,
    fbPaths: { Path },
    fbPaints: { Paint },
}

local STRIDE = 68 -- 17 floats
local TRAM_LEN = 3.7

-- palette (linear-ish 0..1 sRGB values, printed flat)
local RED = { 0.957, 0.271, 0.2 }
local BLUE = { 0.106, 0.306, 0.816 }
local YEL = { 1.0, 0.839, 0.294 }
local WHITE = { 0.961, 0.949, 0.914 }
local BLACK = { 0.09, 0.106, 0.125 }
local BOARD = { 0.988, 0.976, 0.945 }
local GREY = { 0.36, 0.38, 0.41 }

-- ------------------------------------------------------------------ mesh builder
type MB = { v: { number }, count: number }

local function vtx(mb: MB, p: { number }, n: { number }, c: { number }, m: number, sn: { number }, an: { number })
    local v = mb.v
    table.insert(v, p[1]); table.insert(v, p[2]); table.insert(v, p[3])
    table.insert(v, n[1]); table.insert(v, n[2]); table.insert(v, n[3])
    table.insert(v, c[1]); table.insert(v, c[2]); table.insert(v, c[3]); table.insert(v, m)
    table.insert(v, sn[1]); table.insert(v, sn[2]); table.insert(v, sn[3])
    table.insert(v, an[1]); table.insert(v, an[2]); table.insert(v, an[3]); table.insert(v, an[4])
    mb.count += 1
end

local function sub(a: { number }, b: { number }): { number }
    return { a[1] - b[1], a[2] - b[2], a[3] - b[3] }
end

local function cross(a: { number }, b: { number }): { number }
    return { a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1] }
end

local function dot3(a: { number }, b: { number }): number
    return a[1] * b[1] + a[2] * b[2] + a[3] * b[3]
end

local function norm(a: { number }): { number }
    local l = math.sqrt(dot3(a, a))
    if l < 1e-9 then
        return { 0, 1, 0 }
    end
    return { a[1] / l, a[2] / l, a[3] / l }
end

-- One triangle, wound so its geometric normal agrees with `n` (counter-clockwise
-- seen from outside), which the outline pass's front-face culling relies on.
-- `ns` optionally gives per-corner shading normals.
type Corner = { p: { number }, sn: { number }, an: { number }, ns: { number }? }

local function tri(mb: MB, a: Corner, b: Corner, c: Corner, n: { number }, col: { number }, m: number)
    local g = cross(sub(b.p, a.p), sub(c.p, a.p))
    local order = { a, b, c }
    if dot3(g, n) < 0 then
        order = { a, c, b }
    end
    for _, q in ipairs(order) do
        local nn = q.ns or n
        vtx(mb, q.p, nn :: { number }, col, m, q.sn, q.an)
    end
end

local function quad(mb: MB, a: Corner, b: Corner, c: Corner, d: Corner, n: { number }, col: { number }, m: number)
    tri(mb, a, b, c, n, col, m)
    tri(mb, a, c, d, n, col, m)
end

local ZERO = { 0, 0, 0 }

local function corner(p: { number }, sn: { number }?, an: { number }?, ns: { number }?): Corner
    return { p = p, sn = sn or ZERO, an = an or { -1, 0, 0, 0 }, ns = ns }
end

-- ------------------------------------------------------------------ transit map
-- Polyline with rounded 45-degree corners -> dense centreline.
local function rounded(pts: { { number } }, r: number): { { number } }
    local out: { { number } } = { { pts[1][1], pts[1][2] } }
    for i = 2, #pts - 1 do
        local a, b, c = pts[i - 1], pts[i], pts[i + 1]
        local d1 = { b[1] - a[1], b[2] - a[2] }
        local d2 = { c[1] - b[1], c[2] - b[2] }
        local l1 = math.sqrt(d1[1] * d1[1] + d1[2] * d1[2])
        local l2 = math.sqrt(d2[1] * d2[1] + d2[2] * d2[2])
        local rr = math.min(r, l1 * 0.45, l2 * 0.45)
        local p0 = { b[1] - d1[1] / l1 * rr, b[2] - d1[2] / l1 * rr }
        local p1 = { b[1] + d2[1] / l2 * rr, b[2] + d2[2] / l2 * rr }
        for k = 0, 6 do
            local t = k / 6
            -- quadratic bezier through the corner
            local x = (1 - t) * (1 - t) * p0[1] + 2 * (1 - t) * t * b[1] + t * t * p1[1]
            local y = (1 - t) * (1 - t) * p0[2] + 2 * (1 - t) * t * b[2] + t * t * p1[2]
            table.insert(out, { x, y })
        end
    end
    table.insert(out, { pts[#pts][1], pts[#pts][2] })
    return out
end

-- An extruded route ribbon on the board (design px -> world: /100, y -> z).
local function ribbon(mb: MB, pts: { { number } }, cx: number, cz: number, width: number, height: number,
    col: { number }, t0: number, t1: number)
    local cl = rounded(pts, 30)
    local P: { { number } } = {}
    for _, q in ipairs(cl) do
        table.insert(P, { (q[1] - cx) / 100, (q[2] - cz) / 100 })
    end
    local n = #P
    local S: { number } = { 0 }
    for i = 2, n do
        local dx, dz = P[i][1] - P[i - 1][1], P[i][2] - P[i - 1][2]
        S[i] = S[i - 1] + math.sqrt(dx * dx + dz * dz)
    end
    local total = math.max(S[n], 1e-6)
    -- per-point perpendicular (mitred)
    local L: { { number } } = {}
    local R: { { number } } = {}
    local N: { { number } } = {}
    local hw = width * 0.5
    for i = 1, n do
        local ax, az, bx, bz = 0, 0, 0, 0
        if i == 1 then
            ax, az = P[2][1] - P[1][1], P[2][2] - P[1][2]
            bx, bz = ax, az
        elseif i == n then
            ax, az = P[n][1] - P[n - 1][1], P[n][2] - P[n - 1][2]
            bx, bz = ax, az
        else
            ax, az = P[i][1] - P[i - 1][1], P[i][2] - P[i - 1][2]
            bx, bz = P[i + 1][1] - P[i][1], P[i + 1][2] - P[i][2]
        end
        local la = math.max(math.sqrt(ax * ax + az * az), 1e-6)
        local lb = math.max(math.sqrt(bx * bx + bz * bz), 1e-6)
        local tx, tz = ax / la + bx / lb, az / la + bz / lb
        local lt = math.max(math.sqrt(tx * tx + tz * tz), 1e-6)
        tx, tz = tx / lt, tz / lt
        local px, pz = -tz, tx
        local miter = 1 / math.max(0.5, (px * (-az / la) + pz * (ax / la)))
        L[i] = { P[i][1] + px * hw * miter, P[i][2] + pz * hw * miter }
        R[i] = { P[i][1] - px * hw * miter, P[i][2] - pz * hw * miter }
        N[i] = { px, 0, pz }
    end
    local up = { 0, 1, 0 }
    for i = 1, n - 1 do
        local ta = t0 + (t1 - t0) * S[i] / total
        local tb = t0 + (t1 - t0) * S[i + 1] / total
        local ca = { ta, P[i][1], 0, P[i][2] }
        local cb = { tb, P[i + 1][1], 0, P[i + 1][2] }
        local l0 = { L[i][1], height, L[i][2] }
        local l1 = { L[i + 1][1], height, L[i + 1][2] }
        local r0 = { R[i][1], height, R[i][2] }
        local r1 = { R[i + 1][1], height, R[i + 1][2] }
        quad(mb, corner(l0, nil, ca), corner(l1, nil, cb), corner(r1, nil, cb), corner(r0, nil, ca), up, col, 0)
        local nl0, nl1 = N[i], N[i + 1]
        local nr0 = { -nl0[1], 0, -nl0[3] }
        local nr1 = { -nl1[1], 0, -nl1[3] }
        local navg = norm({ nl0[1] + nl1[1], 0, nl0[3] + nl1[3] })
        quad(mb, corner({ L[i][1], 0, L[i][2] }, nil, ca, nl0), corner({ L[i + 1][1], 0, L[i + 1][2] }, nil, cb, nl1),
            corner(l1, nil, cb, nl1), corner(l0, nil, ca, nl0), navg, col, 0)
        local nravg = { -navg[1], 0, -navg[3] }
        quad(mb, corner({ R[i][1], 0, R[i][2] }, nil, ca, nr0), corner(r0, nil, ca, nr0),
            corner(r1, nil, cb, nr1), corner({ R[i + 1][1], 0, R[i + 1][2] }, nil, cb, nr1), nravg, col, 0)
    end
end

-- A station puck: white face ringed in ink (the schematic station symbol), standing
-- on the board. `big` makes an interchange.
local function puck(mb: MB, x: number, z: number, r: number, hgt: number, ring: number, t0: number)
    local seg = 28
    local c = { t0, x, 0, z }
    local up = { 0, 1, 0 }
    for k = 0, seg - 1 do
        local a0 = k / seg * math.pi * 2
        local a1 = (k + 1) / seg * math.pi * 2
        local c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        local o0 = { x + c0 * r, hgt, z + s0 * r }
        local o1 = { x + c1 * r, hgt, z + s1 * r }
        local i0 = { x + c0 * (r - ring), hgt, z + s0 * (r - ring) }
        local i1 = { x + c1 * (r - ring), hgt, z + s1 * (r - ring) }
        local sn0 = norm({ c0, -0.25, s0 })
        local sn1 = norm({ c1, -0.25, s1 })
        -- face: white disc + ink ring
        tri(mb, corner({ x, hgt, z }, ZERO, c), corner(i0, sn0, c), corner(i1, sn1, c), up, WHITE, 0)
        quad(mb, corner(i0, sn0, c), corner(o0, sn0, c), corner(o1, sn1, c), corner(i1, sn1, c), up, BLACK, 0)
        -- side wall
        local w0 = { c0, 0, s0 }
        local w1 = { c1, 0, s1 }
        local sb0 = norm({ c0, -0.2, s0 })
        local sb1 = norm({ c1, -0.2, s1 })
        quad(mb, corner({ x + c0 * r, 0, z + s0 * r }, sb0, c, w0), corner(o0, sn0, c, w0), corner(o1, sn1, c, w1),
            corner({ x + c1 * r, 0, z + s1 * r }, sb1, c, w1), norm({ c0 + c1, 0, s0 + s1 }), WHITE, 0)
    end
end

-- A box (axis aligned), every face one colour; used for the board and tram parts.
local function box(mb: MB, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number,
    top: { number }, side: { number }, m: number, an: { number }?, outline: boolean?)
    local cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    local hx, hy, hz = math.max((x1 - x0) / 2, 1e-4), math.max((y1 - y0) / 2, 1e-4), math.max((z1 - z0) / 2, 1e-4)
    local function C(x: number, y: number, z: number): Corner
        local sn = ZERO
        if outline then
            sn = norm({ (x - cx) / hx, (y - cy) / hy, (z - cz) / hz })
        end
        return corner({ x, y, z }, sn, an)
    end
    quad(mb, C(x0, y1, z0), C(x1, y1, z0), C(x1, y1, z1), C(x0, y1, z1), { 0, 1, 0 }, top, m)
    quad(mb, C(x0, y0, z0), C(x0, y0, z1), C(x1, y0, z1), C(x1, y0, z0), { 0, -1, 0 }, side, m)
    quad(mb, C(x0, y0, z1), C(x0, y1, z1), C(x1, y1, z1), C(x1, y0, z1), { 0, 0, 1 }, side, m)
    quad(mb, C(x0, y0, z0), C(x1, y0, z0), C(x1, y1, z0), C(x0, y1, z0), { 0, 0, -1 }, side, m)
    quad(mb, C(x1, y0, z0), C(x1, y0, z1), C(x1, y1, z1), C(x1, y1, z0), { 1, 0, 0 }, side, m)
    quad(mb, C(x0, y0, z0), C(x0, y1, z0), C(x0, y1, z1), C(x0, y0, z1), { -1, 0, 0 }, side, m)
end

-- intro map: a round "world" board (the interchange roundel made solid). Design px
-- relative to the board centre; 100 px = 1 world unit.
local SKYC = { 0.31, 0.482, 0.918 }
local STONE = { 0.867, 0.847, 0.796 }
local MAP1 = {
    radius = 208,
    river = { { -206, 30 }, { -70, 30 }, { -30, -10 }, { 206, -10 } },
    lines = {
        { col = RED, t = { 0.04, 0.46 }, pts = { { -196, -20 }, { -100, -20 }, { -60, -60 }, { 60, -60 }, { 108, -108 }, { 132, -132 } } },
        { col = YEL, t = { 0.1, 0.52 }, pts = { { -168, 110 }, { -70, 110 }, { -30, 70 }, { 100, 70 }, { 150, 20 }, { 200, 20 } } },
        { col = BLUE, t = { 0.16, 0.58 }, pts = { { -60, -186 }, { -60, 30 }, { -120, 90 }, { -120, 162 } } },
        { col = BLACK, t = { 0.22, 0.64 }, pts = { { 100, -170 }, { 100, 120 }, { 60, 160 }, { 60, 196 } } },
    },
    stations = { { 0, -60 }, { -150, -20 }, { -60, -130 }, { 10, 70 }, { -120, 140 }, { 100, -130 }, { 160, 20 }, { 100, 20 } },
    hubs = { { -60, -60 }, { 100, -60 }, { 100, 70 }, { -70, 110 } },
    blocks = {
        { r = { 12, -160, 56, -112, 0.42 }, col = WHITE },
        { r = { -176, 34, -132, 70, 0.26 }, col = STONE },
        { r = { 128, 92, 170, 140, 0.5 }, col = WHITE },
        { r = { -26, 118, 22, 156, 0.22 }, col = STONE },
        { r = { -30, -130, 6, -90, 0.3 }, col = STONE },
        { r = { 136, -60, 172, -24, 0.34 }, col = WHITE },
    },
}

-- flat annulus (top ring band) at height y
local function annulus(mb: MB, r0: number, r1: number, y: number, col: { number }, t0: number)
    local seg = 96
    local up = { 0, 1, 0 }
    local an = { t0, 0, 0, 0 }
    for k = 0, seg - 1 do
        local a0 = k / seg * math.pi * 2
        local a1 = (k + 1) / seg * math.pi * 2
        local c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        quad(mb, corner({ c0 * r0, y, s0 * r0 }, nil, an), corner({ c0 * r1, y, s0 * r1 }, nil, an),
            corner({ c1 * r1, y, s1 * r1 }, nil, an), corner({ c1 * r0, y, s1 * r0 }, nil, an), up, col, 0)
    end
end

local function buildMap(mb: MB, map: typeof(MAP1))
    local R = map.radius / 100
    local seg = 120
    local up = { 0, 1, 0 }
    local an = { -1, 0, 0, 0 }
    -- the board: a thick disc, cream top, ink side
    for k = 0, seg - 1 do
        local a0 = k / seg * math.pi * 2
        local a1 = (k + 1) / seg * math.pi * 2
        local c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        tri(mb, corner({ 0, 0, 0 }, nil, an), corner({ c0 * R, 0, s0 * R }, nil, an),
            corner({ c1 * R, 0, s1 * R }, nil, an), up, BOARD, 0)
        quad(mb, corner({ c0 * R, -0.16, s0 * R }, nil, an, { c0, 0, s0 }), corner({ c0 * R, 0, s0 * R }, nil, an, { c0, 0, s0 }),
            corner({ c1 * R, 0, s1 * R }, nil, an, { c1, 0, s1 }), corner({ c1 * R, -0.16, s1 * R }, nil, an, { c1, 0, s1 }),
            norm({ c0 + c1, 0, s0 + s1 }), BLACK, 0)
    end
    -- the rim is the interchange roundel: blue, yellow and red bands
    annulus(mb, R - 0.1, R, 0.004, BLUE, 0.02)
    annulus(mb, R - 0.2, R - 0.1, 0.004, YEL, 0.06)
    annulus(mb, R - 0.3, R - 0.2, 0.004, RED, 0.1)
    ribbon(mb, map.river, 0, 0, 0.4, 0.012, SKYC, 0.12, 0.3)
    for k, bl in ipairs(map.blocks) do
        local r = bl.r
        local bx0, bz0, bx1, bz1 = r[1] / 100, r[2] / 100, r[3] / 100, r[4] / 100
        local ban = { 0.3 + k * 0.05, (bx0 + bx1) / 2, 0, (bz0 + bz1) / 2 }
        box(mb, bx0, 0, bz0, bx1, r[5], bz1, bl.col, bl.col, 0, ban, false)
    end
    -- Each line gets its own deck height: lines cross off-station (blue over
    -- yellow at -120,110), and equal heights put the two top faces in one
    -- plane, which z-fights. Later lines pass over earlier ones like a flyover.
    for k, ln in ipairs(map.lines) do
        ribbon(mb, ln.pts, 0, 0, 0.17, 0.07 + (k - 1) * 0.016, ln.col, ln.t[1], ln.t[2])
    end
    for k, s in ipairs(map.stations) do
        puck(mb, s[1] / 100, s[2] / 100, 0.1, 0.17, 0.04, 0.5 + k * 0.03)
    end
    for k, s in ipairs(map.hubs) do
        puck(mb, s[1] / 100, s[2] / 100, 0.17, 0.25, 0.06, 0.42 + k * 0.05)
    end
end

-- ------------------------------------------------------------------ tram
local PROFILE = {
    { -0.47, 0.03 }, { 0.47, 0.03 }, { 0.5, 0.14 }, { 0.5, 0.86 }, { 0.46, 1.0 }, { 0.36, 1.08 },
    { -0.36, 1.08 }, { -0.46, 1.0 }, { -0.5, 0.86 }, { -0.5, 0.14 },
}

local function ringAt(z: number, sx: number, sy: number, slope: number): { { number } }
    local r: { { number } } = {}
    for _, p in ipairs(PROFILE) do
        local y = p[2] * sy
        local zz = z - math.max(0, y - 0.55) * slope
        table.insert(r, { p[1] * sx, y, zz })
    end
    return r
end

local function tramSN(p: { number }): { number }
    return norm({ p[1] / 0.5, (p[2] - 0.55) / 0.55, (p[3] + TRAM_LEN * 0.5) / (TRAM_LEN * 0.5) })
end

local function buildTram(mb: MB)
    local L = TRAM_LEN
    -- rings: nose (sloped windscreen) -> body -> tail
    local rings = {
        ringAt(0.0, 0.86, 0.95, 0.42),
        ringAt(-0.16, 0.96, 0.985, 0.2),
        ringAt(-0.4, 1.0, 1.0, 0.0),
        ringAt(-(L - 0.25), 1.0, 1.0, 0.0),
        ringAt(-L, 0.92, 0.97, 0.0),
    }
    local an = { -1, 0, 0, 0 }
    local np = #PROFILE
    for ri = 1, #rings - 1 do
        local A, B = rings[ri], rings[ri + 1]
        for k = 1, np do
            local k2 = k % np + 1
            local a0, a1, b0, b1 = A[k], A[k2], B[k], B[k2]
            -- outward normal of this strip
            local e1 = sub(a1, a0)
            local e2 = sub(b0, a0)
            local n = norm(cross(e1, e2))
            local mid = { (a0[1] + a1[1]) * 0.5, (a0[2] + a1[2]) * 0.5 - 0.55, 0 }
            if dot3(n, mid) < 0 then
                n = { -n[1], -n[2], -n[3] }
            end
            quad(mb, corner(a0, tramSN(a0), an), corner(a1, tramSN(a1), an), corner(b1, tramSN(b1), an),
                corner(b0, tramSN(b0), an), n, BLUE, 1)
        end
    end
    -- caps: front (windscreen face) and back
    for ci, ring in ipairs({ rings[1], rings[#rings] }) do
        local n = if ci == 1 then norm({ 0, 0.38, 1 }) else { 0, 0, -1 }
        local c = { 0, 0, 0 }
        for _, p in ipairs(ring) do
            c[1] += p[1] / np
            c[2] += p[2] / np
            c[3] += p[3] / np
        end
        for k = 1, np do
            local k2 = k % np + 1
            tri(mb, corner(c, tramSN(c), an), corner(ring[k], tramSN(ring[k]), an),
                corner(ring[k2], tramSN(ring[k2]), an), n, BLUE, 1)
        end
    end
    -- roof equipment and pantograph
    box(mb, -0.22, 1.08, -1.9, 0.22, 1.2, -1.1, WHITE, GREY, 0, an, true)
    box(mb, -0.3, 1.2, -1.62, 0.3, 1.24, -1.52, BLACK, BLACK, 0, an, false)
    box(mb, -0.03, 1.2, -1.58, 0.03, 1.5, -1.54, BLACK, BLACK, 0, an, false)
    box(mb, -0.34, 1.5, -1.6, 0.34, 1.53, -1.52, BLACK, BLACK, 0, an, false)
    -- bogies peeking under the skirt
    box(mb, -0.4, 0.0, -0.95, 0.4, 0.06, -0.55, BLACK, BLACK, 0, an, false)
    box(mb, -0.4, 0.0, -(L - 0.55), 0.4, 0.06, -(L - 0.95), BLACK, BLACK, 0, an, false)
end

-- translucent ground: rails, colour stripes, contact shadow (fades with distance)
local function buildGround(mb: MB)
    local up = { 0, 1, 0 }
    local function strip(x0: number, x1: number, z0: number, z1: number, y: number, col: { number }, m: number)
        quad(mb, corner({ x0, y, z0 }), corner({ x1, y, z0 }), corner({ x1, y, z1 }), corner({ x0, y, z1 }), up, col, m)
    end
    strip(-1.55, -0.95, 3.0, -60, 0.0, YEL, 2)
    strip(0.92, 1.22, 3.0, -60, 0.0, RED, 2)
    strip(1.38, 1.5, 3.0, -60, 0.0, BLUE, 2)
    strip(-0.42, -0.36, 3.0, -60, 0.002, BLACK, 2)
    strip(0.36, 0.42, 3.0, -60, 0.002, BLACK, 2)
end

local function buildTramShadow(mb: MB, z0: number)
    local up = { 0, 1, 0 }
    -- soft-edged contact shadow: two nested quads (the outer one lighter via its own triangles)
    quad(mb, corner({ -0.62, 0.004, z0 + 0.22 }), corner({ 0.7, 0.004, z0 + 0.22 }),
        corner({ 0.7, 0.004, z0 - TRAM_LEN - 0.1 }), corner({ -0.62, 0.004, z0 - TRAM_LEN - 0.1 }), up, BLACK, 3)
end

-- ------------------------------------------------------------------ lifecycle
local function makeMesh(self: P3): (buffer, number, number, number)
    local opaque: MB = { v = {}, count = 0 }
    local kind = math.floor(self.kind + 0.5)
    if kind == 0 then
        buildTram(opaque)
    else
        buildMap(opaque, MAP1)
    end
    local ground: MB = { v = {}, count = 0 }
    if kind == 0 then
        buildGround(ground)
        buildTramShadow(ground, 0)
    end
    local nO = opaque.count
    local nG = ground.count
    local total = nO + nG
    local data = buffer.create(math.max(1, total) * STRIDE)
    local o = 0
    for _, f in ipairs(opaque.v) do
        buffer.writef32(data, o, f)
        o += 4
    end
    for _, f in ipairs(ground.v) do
        buffer.writef32(data, o, f)
        o += 4
    end
    -- the outline pass draws only the outlined part of the opaque range: every kind
    -- carries outline normals where it wants an ink edge, zero elsewhere
    return data, nO, nO, total
end

local function buildFallback(self: P3)
    local kind = math.floor(self.kind + 0.5)
    self.fbPaths = {}
    self.fbPaints = {}
    if kind == 0 then
        local p = Path.new()
        local x, y = self.w * 0.62, self.h * 0.32
        p:moveTo(Vector.xy(x, y))
        p:lineTo(Vector.xy(x + 100, y - 8))
        p:lineTo(Vector.xy(x + 104, y + 124))
        p:lineTo(Vector.xy(x + 4, y + 128))
        p:close()
        table.insert(self.fbPaths, p)
        table.insert(self.fbPaints, Paint.with({ color = Color.rgb(0x1B, 0x4E, 0xD0) }))
        return
    end
    -- the map seen straight down, as the vector plan
    for _, ln in ipairs(MAP1.lines) do
        local p = Path.new()
        for i, q in ipairs(ln.pts) do
            local pt = Vector.xy(self.w * 0.5 + q[1] * 0.8, self.h * 0.5 + q[2] * 0.55)
            if i == 1 then
                p:moveTo(pt)
            else
                p:lineTo(pt)
            end
        end
        table.insert(self.fbPaths, p)
        local c = ln.col
        table.insert(self.fbPaints, Paint.with({ style = 'stroke', thickness = 13, join = 'round', cap = 'round',
            color = Color.rgb(math.floor(c[1] * 255), math.floor(c[2] * 255), math.floor(c[3] * 255)) }))
    end
end

-- canvas size in device pixels for the current w x h points at `res` pixels per point
local function targetSize(self: P3): (number, number, number)
    local k = math.clamp(self.res, 1, 4)
    local pw = math.max(16, math.ceil(self.w * k / 8) * 8)
    local ph = math.max(16, math.ceil(self.h * k / 8) * 8)
    return k, pw, ph
end

local function allocTargets(self: P3, pw: number, ph: number)
    if self.samples > 1 then
        self.msaaTex = GPUTexture.new({ width = pw, height = ph, format = 'rgba8unorm', renderTarget = true,
            sampleCount = self.samples, label = 'poster3d msaa' })
    end
    self.depth = GPUTexture.new({ width = pw, height = ph, format = 'depth32float', renderTarget = true,
        sampleCount = self.samples, label = 'poster3d depth' })
end

function init(self: P3, context: Context): boolean
    if self.gpu then
        return true
    end
    buildFallback(self)
    local sh = context:shader('scripts/poster3d')
    if sh == nil then
        return true
    end
    local layout: { VertexBufferLayout } = { {
        stride = STRIDE,
        attributes = {
            { format = 'float32x3', slot = 0, offset = 0 },
            { format = 'float32x3', slot = 1, offset = 12 },
            { format = 'float32x4', slot = 2, offset = 24 },
            { format = 'float32x3', slot = 3, offset = 40 },
            { format = 'float32x4', slot = 4, offset = 52 },
        },
    } }
    local samples = if context:features().maxSamples >= 4 then 4 else 1
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
        sampleCount = samples,
    })
    self.pLine = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_outline' },
        fragment = { module = sh, entryPoint = 'fs_ink' },
        vertexLayout = layout,
        colorTargets = { { format = fmt } },
        depthStencil = { format = 'depth32float', compare = 'less', write = true },
        cullMode = 'front',
        sampleCount = samples,
    })
    self.pGround = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_ground' },
        vertexLayout = layout,
        colorTargets = { { format = fmt, blend = blend } },
        depthStencil = { format = 'depth32float', compare = 'less-equal', write = false },
        sampleCount = samples,
    })
    local ubo = GPUBuffer.new({ size = 192, usage = 'uniform', label = 'poster3d' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = (self.pMain :: GPUPipeline):getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } } })
    self.lineGroup = GPUBindGroup.new({ layout = (self.pLine :: GPUPipeline):getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } } })
    self.groundGroup = GPUBindGroup.new({ layout = (self.pGround :: GPUPipeline):getBindGroupLayout(0),
        ubos = { { slot = 0, buffer = ubo } } })
    local data, nO, nL, total = makeMesh(self)
    self.vbuf = GPUBuffer.new({ size = math.max(1, total) * STRIDE, usage = 'vertex', data = data, immutable = true,
        label = 'poster3d mesh' })
    self.nOpaque, self.nOutline, self.nTotal = nO, nL, total
    self.samples = samples
    local k, pw, ph = targetSize(self)
    self.k, self.pw, self.ph = k, pw, ph
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    allocTargets(self, pw, ph)
    self.gpu = true
    return true
end

function advance(self: P3, seconds: number): boolean
    return self.live >= 0.5
end

local function writeU(self: P3)
    local b = self.staging
    local aspect = self.w / math.max(1, self.h)
    local fov = math.max(0.1, self.fov)
    local dist = math.max(0.5, self.dist)
    local view = Mat4.lookAt(Vector.xyz(0, 0, dist), Vector.xyz(0, 0, 0), Vector.xyz(0, 1, 0))
    local proj = Mat4.perspective(fov, aspect, math.max(0.05, dist - 30), dist + 60)
    -- off-centre framing: shift the image without changing the perspective. The
    -- projection keeps the vertical field of view, so on-screen sizes do not depend
    -- on the canvas width; only the centre has to be re-anchored when it widens.
    local sx = self.camX
    if self.refW > 0 and self.w > 0 then
        local centre = if self.alignR >= 0.5 then self.w - self.refW * (1 - self.camX) * 0.5
            else self.refW * (1 + self.camX) * 0.5
        sx = 2 * centre / self.w - 1
    end
    local shift = Mat4.fromTranslation(sx, self.camY, 0)
    local vp = shift * proj * view
    local kind = math.floor(self.kind + 0.5)
    local model: Mat4
    if kind == 0 then
        model = Mat4.fromRotationX(self.pitch) * Mat4.fromRotationY(self.yaw + self.sway)
            * Mat4.fromTranslation(0, -0.55, 0)
    else
        model = Mat4.fromRotationX(math.pi * 0.5 - self.pitch) * Mat4.fromRotationY(self.yaw + self.sway)
    end
    vp:writeToBuffer(b, 0)
    model:writeToBuffer(b, 64)
    local lx, ly, lz = -0.45, 1.0, 0.42
    if kind == 0 then
        lx, ly, lz = -0.55, 0.9, 0.6
    end
    local vals = {
        lx, ly, lz, self.outline,
        math.clamp(self.build, -0.2, 1.4), 0, if kind == 0 then 9 else 40, if kind == 0 then 26 else 80,
        BLACK[1], BLACK[2], BLACK[3], 0.16,
        TRAM_LEN, 0, math.clamp(self.dim, 0, 1), if kind == 0 then self.tz else 0,
    }
    for i, v in ipairs(vals) do
        buffer.writef32(b, 128 + (i - 1) * 4, v)
    end
end

local function render(self: P3, canvas: GPUCanvas)
    local ubo, vbuf, depth = self.ubo, self.vbuf, self.depth
    local pMain, pLine, pGround = self.pMain, self.pLine, self.pGround
    local g, lg, gg = self.group, self.lineGroup, self.groundGroup
    if ubo == nil or vbuf == nil or depth == nil or pMain == nil or pLine == nil or pGround == nil
        or g == nil or lg == nil or gg == nil then
        return
    end
    writeU(self)
    ubo:write(self.staging)
    local pass: GPURenderPass
    local mt = self.msaaTex
    if mt ~= nil then
        pass = canvas:beginRenderPass({
            color = { { view = mt:view(), resolveTarget = canvas:colorView(), loadOp = 'clear', storeOp = 'discard',
                clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'poster3d',
        })
    else
        pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            depthStencil = { view = depth:view(), depthLoadOp = 'clear', depthStoreOp = 'discard', depthClearValue = 1 },
            label = 'poster3d',
        })
    end
    pass:setVertexBuffer(0, vbuf)
    if self.outline > 0 and self.nOutline > 0 then
        pass:setPipeline(pLine)
        pass:setBindGroup(0, lg)
        pass:draw(self.nOutline)
    end
    pass:setPipeline(pMain)
    pass:setBindGroup(0, g)
    pass:draw(self.nOpaque)
    if self.nTotal > self.nOpaque then
        pass:setPipeline(pGround)
        pass:setBindGroup(0, gg)
        pass:draw(self.nTotal - self.nOpaque, 1, self.nOpaque)
    end
    pass:finish()
end

function draw(self: P3, renderer: Renderer)
    if self.live < 0.5 then
        return
    end
    local canvas = self.canvas
    if not self.gpu or canvas == nil then
        for i, p in ipairs(self.fbPaths) do
            renderer:drawPath(p, self.fbPaints[i])
        end
        return
    end
    -- follow the layout: a new box size or device scale re-allocates the canvas
    local res, pw, ph = targetSize(self)
    if pw ~= self.pw or ph ~= self.ph then
        canvas:resize(pw, ph)
        allocTargets(self, pw, ph)
        self.pw, self.ph = pw, ph
        self.lastKey = ''
    end
    self.k = res
    local key = string.format('%.4f|%.4f|%.4f|%.4f|%.4f|%.4f|%.4f|%.4f|%.4f|%.4f|%.3f|%.2f|%.2f', self.build, self.pitch,
        self.yaw, self.dist, self.fov, self.camX, self.camY, self.tz, self.sway, self.dim, self.outline, self.w, self.h)
    if key ~= self.lastKey then
        self.lastKey = key
        render(self, canvas)
    end
    local k = self.k
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<P3>
    return {
        kind = 1,
        w = 390,
        h = 420,
        res = 2,
        live = 1,
        build = 1,
        pitch = 0.8,
        yaw = -0.4,
        dist = 9,
        fov = 0.5,
        camX = 0,
        camY = 0,
        tz = 0,
        sway = 0,
        dim = 0,
        outline = 0.02,
        refW = 0,
        alignR = 0,
        gpu = false,
        samples = 1,
        pw = 0,
        ph = 0,
        canvas = nil,
        msaaTex = nil,
        depth = nil,
        pMain = nil,
        pLine = nil,
        pGround = nil,
        ubo = nil,
        group = nil,
        lineGroup = nil,
        groundGroup = nil,
        vbuf = nil,
        nOpaque = 0,
        nOutline = 0,
        nTotal = 0,
        staging = buffer.create(192),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        lastKey = '',
        fbPaths = {},
        fbPaints = {},
        init = init,
        advance = advance,
        draw = draw,
    }
end
