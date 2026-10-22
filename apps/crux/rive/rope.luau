--!strict
-- Crux climbing rope: a dynamic kernmantle rope drawn as vector paths in the hosting
-- node's local space, so keyed position / scale / rotation still apply.
--
-- Every rope piece is drawn the same way, in the brutalist print style of the 3D holds:
-- a coal cut-out outline, the sheath colour, a posterised shade band on the side away
-- from the top-left light, a glint on the lit side, then the braided sheath pattern
-- (dark twill strands leaning one way, a thin acid tracer leaning the other) and
-- coal tape on cut ends. Pieces are drawn in order, so a later piece passes over an
-- earlier one with its own outline (knot crossings, coil turns).
--
-- Modes (`mode`):
--   0  yank: the rope the signature transition snaps taut. It is tied in with a
--      figure-eight on a bight to a locking carabiner clipped through the carrier
--      hold's bolt ring, and runs up past the top of the canvas. `bow` (keyed) is
--      the slack: 0 is taut, the snap overshoots through it, the lower-off pays it out.
--   1  floor (scene 6): a rope pile coiled on the ledge whose free end runs as slack
--      along the floor to the knot of the tie-in at (anchorX, anchorY) (mode 3 draws the
--      tie-in itself, inside the carrier, so it sits on top of the hold).
--      `unwind` (keyed) feeds turns off the pile, `reveal` (keyed) runs the slack out.
--   3  tie (scene 6): only the tie-in (carabiner, bight, knot, tail) at (anchorX, anchorY)
--      pointing along (dirX, dirY), plus a stub of running rope. It rides in the carrier,
--      above the hold, where the floor rope's slack (mode 1) ends; `reveal` fades it in.
--   2  arc (scene 6): the rope laid around the dial, `arc` (bound to the minutes) of a
--      full turn of radius `radius`, starting at 12 o'clock, taped at both ends.
--
-- Geometry is rebuilt only when an input changes; a settled rope costs its draws.
-- No GPU features are used, so this is its own flat fallback on every runtime.

type Rope = {
    mode: Input<number>,
    thick: Input<number>,
    color: Input<Color>,
    strand: Input<Color>,
    tracer: Input<Color>,
    ink: Input<Color>,
    bow: Input<number>,
    unwind: Input<number>,
    reveal: Input<number>,
    arc: Input<number>,
    radius: Input<number>,
    anchorX: Input<number>,
    anchorY: Input<number>,
    dirX: Input<number>,
    dirY: Input<number>,
    live: Input<number>,
    cmds: { { any } },
    key: string,
}

local LX, LY = -0.6, -0.8 -- light from the top left (screen space)
local STEEL = Color.rgb(205, 204, 197)
local STEEL_L = Color.rgb(250, 249, 244)
local SLEEVE = Color.rgb(142, 138, 130)
local TAU = math.pi * 2

-- ------------------------------------------------------------------ polylines
-- A polyline is a flat array {x1, y1, x2, y2, ...}; `measure` adds arc length and
-- unit normals (left of the direction of travel).
type Line = { xs: { number }, ys: { number }, s: { number }, nx: { number }, ny: { number }, len: number }

local function measure(pts: { number }): Line
    local xs, ys, s = {}, {}, {}
    local n = #pts // 2
    local acc = 0
    for i = 1, n do
        local x, y = pts[2 * i - 1], pts[2 * i]
        if i > 1 then
            local dx, dy = x - xs[#xs], y - ys[#ys]
            local d = math.sqrt(dx * dx + dy * dy)
            if d < 1e-4 then
                continue
            end
            acc += d
        end
        table.insert(xs, x)
        table.insert(ys, y)
        table.insert(s, acc)
    end
    local nx, ny = {}, {}
    local m = #xs
    for i = 1, m do
        local a, b = math.max(1, i - 1), math.min(m, i + 1)
        local tx, ty = xs[b] - xs[a], ys[b] - ys[a]
        local tl = math.sqrt(tx * tx + ty * ty)
        if tl < 1e-6 then
            tx, ty, tl = 1, 0, 1
        end
        nx[i], ny[i] = -ty / tl, tx / tl
    end
    return { xs = xs, ys = ys, s = s, nx = nx, ny = ny, len = acc }
end

-- position and normal at arc length `t` (walks from a hint index; returns the new hint)
local function at(l: Line, t: number, hint: number): (number, number, number, number, number)
    local m = #l.xs
    local i = math.clamp(hint, 1, math.max(1, m - 1))
    while i < m - 1 and l.s[i + 1] < t do
        i += 1
    end
    while i > 1 and l.s[i] > t do
        i -= 1
    end
    if m < 2 then
        return l.xs[1], l.ys[1], l.nx[1], l.ny[1], 1
    end
    local s0, s1 = l.s[i], l.s[i + 1]
    local f = if s1 > s0 then math.clamp((t - s0) / (s1 - s0), 0, 1) else 0
    local x = l.xs[i] + (l.xs[i + 1] - l.xs[i]) * f
    local y = l.ys[i] + (l.ys[i + 1] - l.ys[i]) * f
    local nx = l.nx[i] + (l.nx[i + 1] - l.nx[i]) * f
    local ny = l.ny[i] + (l.ny[i + 1] - l.ny[i]) * f
    local nl = math.sqrt(nx * nx + ny * ny)
    if nl > 1e-6 then
        nx, ny = nx / nl, ny / nl
    end
    return x, y, nx, ny, i
end

local function strokePath(xs: { number }, ys: { number }): Path
    local p = Path.new()
    p:moveTo(Vector.xy(xs[1], ys[1]))
    for i = 2, #xs do
        p:lineTo(Vector.xy(xs[i], ys[i]))
    end
    return p
end

-- the centreline offset sideways, towards (sign -1) or away from (sign 1) the light
local function offsetPath(l: Line, amount: number, sign: number): Path
    local xs, ys = {}, {}
    for i = 1, #l.xs do
        local k = math.clamp((l.nx[i] * -LX + l.ny[i] * -LY) * 1.7, -1, 1) * sign
        xs[i] = l.xs[i] + l.nx[i] * amount * k
        ys[i] = l.ys[i] + l.ny[i] * amount * k
    end
    return strokePath(xs, ys)
end

-- a quad wound one consistent way (scripted paths fill by the clockwise rule)
local function quad(p: Path, ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number)
    local area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay) + (cx - ax) * (dy - ay) - (dx - ax) * (cy - ay)
    if area < 0 then
        ax, ay, bx, by, cx, cy, dx, dy = dx, dy, cx, cy, bx, by, ax, ay
    end
    p:moveTo(Vector.xy(ax, ay))
    p:lineTo(Vector.xy(bx, by))
    p:lineTo(Vector.xy(cx, cy))
    p:lineTo(Vector.xy(dx, dy))
    p:close()
end

-- diagonal bands across the rope: from the -h edge at s to the +h edge at s + lean
local function bands(l: Line, h: number, s0: number, pitch: number, w: number, lean: number): Path
    local p = Path.new()
    local hint = 1
    local s = s0
    while s + w + math.abs(lean) <= l.len do
        local ax, ay, anx, any, i1 = at(l, s, hint)
        hint = i1
        local bx, by, bnx, bny = at(l, s + w, hint)
        local cx, cy, cnx, cny = at(l, s + w + lean, hint)
        local dx, dy, dnx, dny = at(l, s + lean, hint)
        quad(p, ax - anx * h, ay - any * h, bx - bnx * h, by - bny * h,
            cx + cnx * h, cy + cny * h, dx + dnx * h, dy + dny * h)
        s += pitch
    end
    return p
end

local function stroked(color: Color, th: number, cap: StrokeCap?): Paint
    return Paint.with({ style = 'stroke', color = color, thickness = th, cap = cap or 'round', join = 'round' })
end

local function filled(color: Color): Paint
    return Paint.with({ style = 'fill', color = color })
end

local function push(self: Rope, path: Path, paint: Paint)
    table.insert(self.cmds, { path, paint })
end

-- one rope piece: outline, sheath, shade, glint, braid, tape
local function piece(self: Rope, pts: { number }, T: number, phase: number, tapeA: boolean, tapeB: boolean)
    local l = measure(pts)
    if #l.xs < 2 or l.len < 0.5 then
        return
    end
    local line = strokePath(l.xs, l.ys)
    local ol = math.max(1.6, T * 0.2)
    local base: Color = self.color
    push(self, line, stroked(self.ink, T + ol * 2))
    push(self, line, stroked(base, T))
    push(self, offsetPath(l, T * 0.24, 1), stroked(Color.lerp(base, self.ink, 0.42), T * 0.4))
    push(self, offsetPath(l, T * 0.22, -1), stroked(Color.lerp(base, Color.rgb(255, 255, 255), 0.5), T * 0.16))
    local h = T * 0.5
    local pitch = T * 0.9
    push(self, bands(l, h, phase * pitch, pitch, T * 0.3, T * 0.62), filled(Color.lerp(self.strand, base, 0.1)))
    push(self, bands(l, h, phase * pitch + T * 0.45, pitch * 2.5, T * 0.16, -T * 0.62), filled(self.tracer))
    -- coal tape whipped over a cut end
    local tape = Path.new()
    local hh = T * 0.56
    local function band(s: number)
        local ax, ay, anx, any = at(l, s, 1)
        local bx, by, bnx, bny = at(l, s + T * 0.55, 1)
        quad(tape, ax - anx * hh, ay - any * hh, bx - bnx * hh, by - bny * hh,
            bx + bnx * hh, by + bny * hh, ax + anx * hh, ay + any * hh)
    end
    if tapeA and l.len > T * 1.2 then
        band(T * 0.3)
    end
    if tapeB and l.len > T * 1.2 then
        band(l.len - T * 0.85)
    end
    if tapeA or tapeB then
        push(self, tape, filled(self.ink))
    end
end

-- ------------------------------------------------------------------ tie-in
-- Proportions of the tie-in, in rope thicknesses, along the rope from the bolt ring.
local TIE_U0 = -0.55 -- the carabiner's bottom bar, through the ring
local TIE_LC = 3.3 -- carabiner length
local TIE_WC = 1.7 -- carabiner width
local TIE_GAP = 0.75 -- bar to knot
local TIE_KL = 3.3 -- knot length

-- where the running rope leaves the knot (u along the rope, v across it), in thicknesses
local function tieExit(): (number, number)
    return TIE_U0 + TIE_LC + TIE_GAP + TIE_KL * 0.95, 0.15
end

-- A locking carabiner clipped through the bolt ring at (ax, ay), a bight of rope round
-- its top bar, a figure-eight knot and a taped tail. (dx, dy) points from the ring
-- along the rope. Returns where the running rope leaves the knot.
local function tieIn(self: Rope, ax: number, ay: number, dx: number, dy: number, T: number,
    drawRope: () -> ()): (number, number)
    local vx, vy = -dy, dx -- across the rope
    local function P(u: number, v: number): (number, number)
        return ax + dx * u + vx * v, ay + dy * u + vy * v
    end
    local Lc, Wc = T * TIE_LC, T * TIE_WC
    local u0 = T * TIE_U0
    local uBar = u0 + Lc
    -- carabiner: a D-shaped oval, the flat spine on the +v side
    local cpts = {}
    local cu, cv = (u0 + uBar) * 0.5, 0
    for i = 0, 48 do
        local t = i / 48 * TAU
        local c, s = math.cos(t), math.sin(t)
        local u = cu + Lc * 0.5 * math.sign(c) * math.abs(c) ^ 0.7
        local v = cv + Wc * 0.5 * math.sign(s) * math.abs(s) ^ 0.7
        if v > Wc * 0.36 then
            v = Wc * 0.36
        end
        local x, y = P(u, v)
        table.insert(cpts, x)
        table.insert(cpts, y)
    end
    local cl = measure(cpts)
    local cpath = strokePath(cl.xs, cl.ys)
    cpath:close()
    local tc = T * 0.34
    local ol = math.max(1.4, T * 0.17)
    -- the running rope goes first, so the knot sits over its start
    drawRope()
    push(self, cpath, stroked(self.ink, tc + ol * 2))
    push(self, cpath, stroked(STEEL, tc))
    push(self, offsetPath(cl, tc * 0.25, -1), stroked(STEEL_L, tc * 0.35))
    -- screw-gate sleeve on the spine
    local sl = Path.new()
    local s1x, s1y = P(cu - Lc * 0.16, Wc * 0.36)
    local s2x, s2y = P(cu + Lc * 0.12, Wc * 0.36)
    sl:moveTo(Vector.xy(s1x, s1y))
    sl:lineTo(Vector.xy(s2x, s2y))
    push(self, sl, stroked(self.ink, tc * 1.9 + ol * 2, 'butt'))
    push(self, sl, stroked(SLEEVE, tc * 1.9, 'butt'))
    -- the bight round the top bar, its two strands running up into the knot
    local uK0 = uBar + T * TIE_GAP
    local kL = T * TIE_KL
    local r = T * 0.52
    local bpts = {}
    local function add(u: number, v: number)
        local x, y = P(u, v)
        table.insert(bpts, x)
        table.insert(bpts, y)
    end
    add(uK0 + T * 0.4, r)
    add(uBar, r)
    for i = 1, 15 do
        local t = i / 16 * math.pi
        add(uBar - math.sin(t) * r * 1.1, math.cos(t) * r)
    end
    add(uBar, -r)
    add(uK0 + T * 0.4, -r)
    piece(self, bpts, T, 0.3, false, false)
    -- figure eight: a lemniscate along the rope, drawn as two halves for the crossing
    local mid = uK0 + kL * 0.5
    local function lobe(t0: number, t1: number): { number }
        local out = {}
        for i = 0, 24 do
            local t = t0 + (t1 - t0) * i / 24
            local x, y = P(mid + kL * 0.5 * math.cos(t), T * 0.8 * math.sin(2 * t))
            table.insert(out, x)
            table.insert(out, y)
        end
        return out
    end
    piece(self, lobe(-0.15 * math.pi, 1.05 * math.pi), T, 0.0, false, false)
    piece(self, lobe(0.95 * math.pi, 2.15 * math.pi), T, 0.5, false, false)
    -- the tail, taped, kicked out beside the running rope
    local tpts = {}
    for i = 0, 10 do
        local f = i / 10
        local x, y = P(uK0 + kL * (0.75 + 0.55 * f), -T * (0.35 + 0.9 * f * f))
        table.insert(tpts, x)
        table.insert(tpts, y)
    end
    piece(self, tpts, T * 0.94, 0.2, false, true)
    local eu, ev = tieExit()
    return P(eu * T, ev * T)
end

-- ------------------------------------------------------------------ modes
local function catmull(ctrl: { number }, steps: number): { number }
    local out = {}
    local n = #ctrl // 2
    local function cp(i: number): (number, number)
        i = math.clamp(i, 1, n)
        return ctrl[2 * i - 1], ctrl[2 * i]
    end
    for i = 1, n - 1 do
        local x0, y0 = cp(i - 1)
        local x1, y1 = cp(i)
        local x2, y2 = cp(i + 1)
        local x3, y3 = cp(i + 2)
        for j = 0, steps - 1 do
            local t = j / steps
            local t2, t3 = t * t, t * t * t
            local function f(a: number, b: number, c: number, d: number): number
                return 0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
            end
            table.insert(out, f(x0, x1, x2, x3))
            table.insert(out, f(y0, y1, y2, y3))
        end
    end
    local xl, yl = cp(n)
    table.insert(out, xl)
    table.insert(out, yl)
    return out
end

local function buildYank(self: Rope)
    local T = self.thick
    local bow = self.bow
    tieIn(self, 4, 0, 0, -1, T, function()
        -- running rope: from the knot up past the canvas; the slack bows out to the
        -- side, most near the hold, like the old keyed bezier
        local pts = {}
        local eu, ev = tieExit()
        local y0, yPeak, y1 = -T * (eu - 0.4), -520, -2800
        local y = y0
        while y > y1 do
            local g
            if y > yPeak then
                g = math.sin((y0 - y) / (y0 - yPeak) * math.pi * 0.5)
            else
                g = math.cos((yPeak - y) / (yPeak - y1) * math.pi * 0.5)
            end
            table.insert(pts, 4 - T * ev + bow * g)
            table.insert(pts, y)
            y -= if y > -700 then 4 else 14
        end
        table.insert(pts, 4 - T * ev)
        table.insert(pts, y1)
        piece(self, pts, T, 0, false, false)
    end)
end

local function buildArc(self: Rope)
    local T = self.thick
    -- a full dial (180 minutes or more) leaves a hair of a gap so both taped ends read
    local f = math.clamp(self.arc, 0, 0.972)
    if f < 0.004 then
        return
    end
    local r = self.radius
    local n = math.max(2, math.floor(f * 160))
    local pts = {}
    for i = 0, n do
        local a = -math.pi * 0.5 + f * TAU * i / n
        table.insert(pts, math.cos(a) * r)
        table.insert(pts, math.sin(a) * r)
    end
    piece(self, pts, T, 0, true, true)
end

local function buildFloor(self: Rope)
    local T = self.thick
    -- the pile: a helix of turns seen from the front, each turn a little higher
    local cx, cy, rx, ry, rise = 304, 694, 58, 20, 11.5
    local turns = 4.6 - 1.7 * math.clamp(self.unwind, 0, 1)
    local total = turns * TAU
    -- start at the front left of the bottom turn; settled, the free end leaves the top
    -- turn at its front left too, heading for the hold
    local th0 = math.pi * 0.8
    local function H(t: number): (number, number)
        return cx + rx * math.cos(th0 + t), cy + ry * math.sin(th0 + t) - rise * t / TAU
    end
    -- half turns as separate pieces: each one passes over the turn below it
    local t = 0
    local half = math.pi
    while t < total - 1e-3 do
        local t1 = math.min(total, t + half)
        local pts = {}
        local n = math.max(2, math.floor((t1 - t) / half * 22))
        for i = 0, n do
            local x, y = H(t + (t1 - t) * i / n)
            table.insert(pts, x)
            table.insert(pts, y)
        end
        piece(self, pts, T, (t / TAU) % 1, t == 0, false)
        t = t1
    end
    -- the slack leaves the top turn along its tangent, drops to the floor, snakes to the hold
    local ex, ey = H(total)
    local tx, ty = -rx * math.sin(th0 + total), ry * math.cos(th0 + total)
    local tl = math.sqrt(tx * tx + ty * ty)
    tx, ty = tx / tl, ty / tl
    local ax, ay = self.anchorX, self.anchorY
    local reveal = math.clamp(self.reveal, 0, 1)
    if reveal <= 0.001 then
        return
    end
    -- the knot exit of the tie-in (mode 3), in this space
    local dx, dy = self.dirX, self.dirY
    local dl = math.sqrt(dx * dx + dy * dy)
    dx, dy = dx / math.max(dl, 1e-6), dy / math.max(dl, 1e-6)
    local eu, ev = tieExit()
    local kx, ky = ax + dx * eu * T - dy * ev * T, ay + dy * eu * T + dx * ev * T
    local function slack()
        local ctrl = { ex, ey, ex + tx * 16, ey + ty * 16, 236, 718, 188, 730, 152, 718, kx + dx * T * 0.6, ky + dy * T * 0.6, kx, ky }
        local pts = catmull(ctrl, 14)
        if reveal < 1 then
            local l = measure(pts)
            local cut = l.len * reveal
            local out = {}
            for i = 1, #l.xs do
                if l.s[i] > cut then
                    local x, y = at(l, cut, i)
                    table.insert(out, x)
                    table.insert(out, y)
                    break
                end
                table.insert(out, l.xs[i])
                table.insert(out, l.ys[i])
            end
            pts = out
        end
        piece(self, pts, T, 0.35, false, true)
    end
    slack()
end

local function buildTie(self: Rope)
    local T = self.thick
    local dx, dy = self.dirX, self.dirY
    local dl = math.sqrt(dx * dx + dy * dy)
    if dl < 1e-6 then
        return
    end
    dx, dy = dx / dl, dy / dl
    local ax, ay = self.anchorX, self.anchorY
    tieIn(self, ax, ay, dx, dy, T, function()
        local eu, ev = tieExit()
        local sx, sy = ax + dx * eu * T - dy * ev * T, ay + dy * eu * T + dx * ev * T
        piece(self, { sx - dx * T, sy - dy * T, sx + dx * T * 1.6, sy + dy * T * 1.6 }, T, 0.35, false, false)
    end)
end

local function rebuild(self: Rope)
    self.cmds = {}
    if self.mode < 0.5 then
        buildYank(self)
    elseif self.mode < 1.5 then
        buildFloor(self)
    elseif self.mode < 2.5 then
        buildArc(self)
    else
        buildTie(self)
    end
end

function update(self: Rope)
    local key = string.format('%d|%.3f|%.2f|%.4f|%.4f|%.4f|%.2f|%.2f|%.2f|%.4f|%.4f|%d|%d|%d|%d',
        math.floor(self.mode + 0.5), self.thick, self.bow, self.unwind, self.reveal, self.arc, self.radius,
        self.anchorX, self.anchorY, self.dirX, self.dirY, self.color, self.strand, self.tracer, self.ink)
    if key ~= self.key then
        self.key = key
        rebuild(self)
    end
end

function draw(self: Rope, renderer: Renderer)
    if self.live < 0.5 then
        return
    end
    if self.key == '' then
        update(self)
    end
    -- the tie-in fades in with `reveal`
    local fade = self.mode > 2.5 and self.reveal < 0.999
    if fade then
        if self.reveal <= 0.001 then
            return
        end
        renderer:save()
        renderer:modulateOpacity(self.reveal)
    end
    for _, c in ipairs(self.cmds) do
        renderer:drawPath(c[1], c[2])
    end
    if fade then
        renderer:restore()
    end
end

return function(): Node<Rope>
    return {
        mode = 0,
        thick = 9,
        color = Color.rgb(56, 93, 244),
        strand = Color.rgb(28, 44, 140),
        tracer = Color.rgb(220, 255, 63),
        ink = Color.rgb(32, 34, 31),
        bow = 0,
        unwind = 0,
        reveal = 1,
        arc = 0,
        radius = 172,
        anchorX = 0,
        anchorY = 0,
        dirX = 1,
        dirY = 0,
        live = 1,
        cmds = {},
        key = '',
        update = update,
        draw = draw,
    }
end
