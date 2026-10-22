--!strict
-- Marginalia reading lamp in 3D (scene 7, "day reading streak").
--
-- A ScriptedDrawable that replaces the flat lamp, cone and stack with a lit
-- 3D still life on the GPU (scripts/etch3d.luau + shaders/etch3d.wgsl):
--
--   * a brass architect's lamp - weighted foot, two arms with ball joints, a
--     conical shade lit warm inside, a glowing bulb - whose bulb is a real
--     spot light: the five closed volumes below are lit by it (cloth covers,
--     board edges, page blocks), brightest where its cone lands;
--   * a second pass in the drawable's own space draws the light itself: a
--     soft cone with a long falloff, a pool on the top volume, and dust motes
--     drifting slowly through the beam; the room outside the light dims a
--     little, fading to nothing at the canvas edge.
--
-- Origin: the bottom centre of the stack's front (the vector stack's origin).
-- The day tabs stay vector, sliding out from under the volumes.
-- Entrance (the scene's timing): the volumes drop in one by one (150 ms
-- apart), the lamp swings upright (0-700 ms), the bulb lights (520 ms), the
-- beam and the pool come up (600-1100 ms). Idle: the motes drift and the light
-- breathes very slightly. Reduced motion: settled, motes still. Pause: frozen.
-- The 3D is re-rendered only while it moves; the light pass runs per frame
-- only while the motes are drifting. Without shaders it draws nothing and the
-- vector lamp and stack (Flat Fallback) stay visible.

local E = require('scripts/etch3d')

type Etch = E.Etch

type Lamp = {
    scene: Input<number>,
    id: Input<number>,
    screen: Input<number>,
    navDir: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    vw: Input<number>,
    vh: Input<number>,
    bp: Input<number>,
    dev: Input<number>,
    e: Etch?,
    clock: E.Clock,
    idle: number,
    drawn: string,
    beamDrawn: string,
    built: boolean,
}

local INK, OX, GREEN, INK2, OXD = 0x252E3D, 0x782D3D, 0x3E5446, 0x3B4558, 0x571E2B
local GOLD, GOLDD, GOLDL = 0xBD914C, 0x8E6A33, 0xDDBD84

-- the volumes, bottom to top: colour, width, thickness, x offset (as the vector stack)
local VOLS = {
    { c = INK, w = 228, h = 40, x = -8 },
    { c = OX, w = 214, h = 34, x = 0 },
    { c = GREEN, w = 232, h = 46, x = 8 },
    { c = INK2, w = 206, h = 36, x = -8 },
    { c = OXD, w = 196, h = 30, x = 0 },
}
local DEPTH = 150 -- head to tail of a volume
local GAP = 2

-- lamp geometry (world: y up, the stack's front at z = 0)
local FOOT = { x = 184, y = 0, z = 14 }
local ELBOW = { x = 178, y = 188, z = 14 }
local PIVOT = { x = 132, y = 268, z = 22 }

function init(self: Lamp, context: Context): boolean
    if self.e == nil then
        self.e = E.new(context, true)
    end
    return true
end

local function here(self: Lamp): boolean
    return math.floor(self.screen + 0.5) == math.floor(self.scene + 0.5)
end

function advance(self: Lamp, seconds: number): boolean
    E.tick(self.clock, here(self), self.navDir < 0, self.still, self.paused, seconds)
    if here(self) and not self.still and not self.paused then
        self.idle += seconds
    end
    return true
end

local function stackTop(): number
    local y = 0
    for _, v in VOLS do
        y += v.h + GAP
    end
    return y - GAP
end

-- the shade's axis (unit) and the bulb position, for a swing angle
local function shadeFrame(swing: number)
    local top = stackTop()
    local tx, ty, tz = -6, top - 30, -DEPTH * 0.2 -- where the light is aimed
    local ax, ay, az = tx - PIVOT.x, ty - PIVOT.y, tz - PIVOT.z
    local l = math.sqrt(ax * ax + ay * ay + az * az)
    ax, ay, az = ax / l, ay / l, az / l
    -- the swing rotates everything about the foot (z axis)
    local c, s = math.cos(swing), math.sin(swing)
    local function rot(x: number, y: number): (number, number)
        local dx, dy = x - FOOT.x, y - FOOT.y
        return FOOT.x + c * dx - s * dy, FOOT.y + s * dx + c * dy
    end
    local px, py = rot(PIVOT.x, PIVOT.y)
    local rax, ray = c * ax - s * ay, s * ax + c * ay
    return px, py, PIVOT.z, rax, ray, az
end

local function build(self: Lamp, e: Etch, t: number)
    E.clear(e)
    -- soft shadows: under the stack and under the lamp's foot
    local first = E.clamp01(E.prog(t, 150, 500))
    E.add(e, E.QUAD, 300, DEPTH + 40, 0, 0, 0, 0, 0, E.T(0, -0.6, -DEPTH * 0.5), 0x1A1410, E.SHADOW,
        0, 0, 0, 0, 0.22 * first, 0.5, 0)
    E.add(e, E.QUAD, 96, 70, 0, 0, 0, 0, 0, E.T(FOOT.x - 6, -0.6, FOOT.z - 4), 0x1A1410, E.SHADOW,
        0, 0, 0, 0, 0.25, 0.8, 0)
    -- the volumes drop in
    local y = 0
    for i, v in VOLS do
        local t0 = 150 + (i - 1) * 80
        local a = E.easeBack(E.prog(t, t0, 500))
        if E.prog(t, t0, 1) > 0 then
            local lift = 60 * (1 - a)
            local m = E.T(v.x, y + lift, -DEPTH * 0.5)
            local w, h, tb = v.w, v.h, 2.6
            -- top cover (cloth), with the hatching laid along the book
            E.add(e, E.QUAD, w - 2, DEPTH - 2, 0, 0, 0, 0, 0, E.mul(m, E.T(1, h, 0)), v.c, E.CLOTH,
                1, 0, 0, 0.30, 1, 0, 0, 0.8)
            -- front: board edges top and bottom, the page block recessed between
            E.add(e, E.QUAD, w - 2, tb, 0, 0, 0, 0, 0, E.mul(m, E.chain(E.T(1, h - tb * 0.5, DEPTH * 0.5), E.RX(math.pi / 2))),
                v.c, E.CLOTH, 1, 0, 0, 0.3, 1, 0, 0, 0.8)
            E.add(e, E.QUAD, w - 2, tb, 0, 0, 0, 0, 0, E.mul(m, E.chain(E.T(1, tb * 0.5, DEPTH * 0.5), E.RX(math.pi / 2))),
                v.c, E.CLOTH, 1, 0, 0, 0.3, 1, 0, 0, 0.8)
            local pw = w - 18
            E.add(e, E.FACE, pw, h - 2 * tb, 0, 0, 0, 0, 0, E.mul(m, E.T(w * 0.5 - 4 - pw * 0.5, h * 0.5, DEPTH * 0.5 - 2.2)),
                0xF6EEDC, E.EDGES, 0, 1, 0, 0, 1, math.max(6, (h - 2 * tb) * 0.9), 0)
            -- the rounded spine: its end facing us (a half disc) and the spine itself
            local sp = E.chain(E.T(-w * 0.5 + 6, h * 0.5, 0), E.S(0.35, 1, 1), E.RX(math.pi / 2))
            E.add(e, E.FRUSTUM, math.pi * 0.5, math.pi * 1.5, 0.3, h * 0.5, 0, 0, 0,
                E.mul(m, E.mul(E.T(0, 0, DEPTH * 0.5 + 0.01), sp)), v.c, E.CLOTH, 0, 1, 0, 0.3, 1, 0, 0, 0.8)
            E.add(e, E.FRUSTUM, math.pi * 0.5, math.pi * 1.5, h * 0.5, h * 0.5, DEPTH, 0, 0,
                E.mul(m, E.mul(E.T(0, 0, -DEPTH * 0.5), sp)), v.c, E.CLOTH, 0, 0, 1, 0.3, 1, 0, 0, 0.8)
            -- gilt bands across the spine end
            for _, gy in { h * 0.28, h * 0.72 } do
                E.add(e, E.QUAD, 7, 1.6, 0, 0, 0, 0, 0,
                    E.mul(m, E.chain(E.T(-w * 0.5 + 3, gy, DEPTH * 0.5 + 0.6), E.RX(math.pi / 2))), GOLD, E.BRASS,
                    1, 0, 0, 0, 1, 0, 0)
            end
        end
        y += v.h + GAP
    end
    -- the lamp: it swings upright about its foot
    local swing = -0.18 * (1 - E.easeBack(E.prog(t, 0, 700)))
    local R = E.chain(E.T(FOOT.x, FOOT.y, 0), E.RZ(swing), E.T(-FOOT.x, -FOOT.y, 0))
    -- weighted foot
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 28, 25, 9, 0, 0, E.mul(R, E.T(FOOT.x, FOOT.y, FOOT.z)), GOLDD, E.BRASS,
        0, 1, 0, 0.5, 1, 0, 0)
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 0.4, 25, 0, 0, 0, E.mul(R, E.T(FOOT.x, FOOT.y + 9, FOOT.z)), GOLD, E.BRASS,
        1, 0, 0, 0.4, 1, 0, 0)
    E.add(e, E.SPHERE, 0, math.pi * 2, 0.05, math.pi * 0.5, 9, 0, 0, E.mul(R, E.T(FOOT.x, FOOT.y + 9, FOOT.z)), GOLD,
        E.BRASS, 0, 1, 0, 0.5, 1, 0, 0)
    -- arms and joints
    local function rod(a: { x: number, y: number, z: number }, b: { x: number, y: number, z: number }, r: number)
        local m, len = E.along(a.x, a.y, a.z, b.x, b.y, b.z)
        E.add(e, E.FRUSTUM, 0, math.pi * 2, r, r, len, 0, 0, E.mul(R, m), GOLD, E.BRASS, 0, 1, 0, 0.6, 1, 0, 0)
    end
    rod({ x = FOOT.x, y = FOOT.y + 12, z = FOOT.z }, ELBOW, 3.4)
    rod(ELBOW, PIVOT, 3.0)
    E.add(e, E.SPHERE, 0, math.pi * 2, 0.05, math.pi - 0.05, 6.5, 0, 0, E.mul(R, E.T(ELBOW.x, ELBOW.y, ELBOW.z)),
        GOLDD, E.BRASS, 0, 1, 0, 0.6, 1, 0, 0)
    E.add(e, E.SPHERE, 0, math.pi * 2, 0.05, math.pi - 0.05, 5.5, 0, 0, E.mul(R, E.T(PIVOT.x, PIVOT.y, PIVOT.z)),
        GOLDD, E.BRASS, 0, 1, 0, 0.6, 1, 0, 0)
    -- shade: a cone from the pivot along the axis; brass outside, warm inside
    local px, py, pz, ax, ay, az = shadeFrame(swing)
    local base = { x = px + ax * 4, y = py + ay * 4, z = pz + az * 4 }
    local m = E.along(base.x, base.y, base.z, base.x + ax, base.y + ay, base.z + az)
    local L = 48
    local bulbOn = E.easeOut(E.prog(t, 520, 120))
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 10, 33, L, 0, 0, m, GOLD, E.BRASS, 0, 1, 0, 0.45, 1, 0, 0)
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 9.2, 31.8, L - 0.6, 0, 0, m, 0xF3D9A4, E.GLOW, 0, 0, 0, 0, 1, 0, 0.35 + 0.5 * bulbOn)
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 33.4, 33.4, 2.4, 0, 0, E.mul(m, E.T(0, L - 2.4, 0)), GOLDL, E.BRASS,
        0, 1, 0, 0, 1, 0, 0)
    E.add(e, E.SPHERE, 0, math.pi * 2, 0.05, math.pi - 0.05, 10, 0, 0, E.mul(m, E.T(0, L - 15, 0)), 0xFFF3D2, E.GLOW,
        0, 0, 0, 0, 1, 0, 0.15 + 0.85 * bulbOn)
    -- the bulb is the light
    local bx, by, bz = base.x + ax * (L - 15), base.y + ay * (L - 15), base.z + az * (L - 15)
    E.spot(e, bx, by, bz, ax, ay, az, math.rad(36), math.rad(14), 0xFFE2B0, 1.5 * bulbOn, 260)
    return bx, by, bz, ax, ay, az, bulbOn
end

local function frame(e: Etch): E.Box
    local x0, y0, x1, y1 = 0, 0, 0, 0
    for _, p in { { -150, -6, 10 }, { 240, -6, 10 }, { -150, 300, -160 }, { 240, 300, -40 }, { 60, 300, -40 } } do
        local px, py = E.project(e, p[1], p[2], p[3])
        x0 = math.min(x0, px)
        x1 = math.max(x1, px)
        y0 = math.min(y0, py)
        y1 = math.max(y1, py)
    end
    local m = 30 -- room for the dimming to fade out
    return { x = x0 - m, y = y0 - m, w = x1 - x0 + 2 * m, h = y1 - y0 + 2 * m }
end

function draw(self: Lamp, renderer: Renderer)
    local e = self.e
    if e == nil then
        return
    end
    if not E.visible(self.clock) then
        E.register(self.scene, self.id, e, 0, 0, true, false)
        return
    end
    if not self.built then
        E.camera(e, math.rad(13), 0, 900, 700, 120)
        E.light(e, -0.5, 0.6, 0.65, 0.40, 0.56, 0.53, 0.48, 0.85)
        E.ink(e, 0x231B16)
        self.built = true
    end
    local k = math.max(self.dev, 1) * E.artScale(math.floor(self.scene + 0.5), self.vw, self.vh, self.bp)
    local resized = E.ensure(e, frame(e), k, true)
    local t = self.clock.t
    -- the mesh: only while something in it moves
    local mk = string.format('%.3f', math.min(t, 1.4))
    local bx, by, bz, ax, ay, az, bulbOn = 0, 0, 0, 0, -1, 0, 1
    if resized or mk ~= self.drawn then
        self.drawn = mk
        bx, by, bz, ax, ay, az, bulbOn = build(self, e, t)
        E.render(e)
    else
        local swing = -0.18 * (1 - E.easeBack(E.prog(t, 0, 700)))
        local px, py, pz, ax2, ay2, az2 = shadeFrame(swing)
        ax, ay, az = ax2, ay2, az2
        bx, by, bz = px + ax * 37, py + ay * 37, pz + az * 37
        bulbOn = E.easeOut(E.prog(t, 520, 120))
    end
    -- the light, in drawable space
    local apx, apy = E.project(e, bx, by, bz)
    local tx, ty = E.project(e, bx + ax * 100, by + ay * 100, bz + az * 100)
    local top = stackTop()
    local hit = (by - top) / math.max(-ay, 0.2)
    local hx, hy = E.project(e, bx + ax * hit, top, bz + az * hit)
    local beamUp = E.easeInOut(E.prog(t, 600, 400))
    local poolUp = E.easeInOut(E.prog(t, 700, 400))
    local breathe = 1 - 0.08 * (0.5 - 0.5 * math.cos(self.idle * 2 * math.pi / 7))
    local time = if self.still then 3.0 else self.idle + 3.0
    local motes = beamUp * (if self.still then 0.7 else 1)
    local bkey = string.format('%.3f|%.3f|%.3f|%.2f', beamUp, poolUp, breathe, time)
    if resized or bkey ~= self.beamDrawn then
        self.beamDrawn = bkey
        local len = math.sqrt((hx - apx) ^ 2 + (hy - apy) ^ 2) * 1.25
        E.beam(e, apx, apy, tx - apx, ty - apy, 20, 0.62, len, 0.9 * beamUp * breathe, hx + 6, hy + 4, 118, 30,
            0.16 * beamUp, time, motes, 0.30 * poolUp * breathe * bulbOn)
        E.renderBeam(e)
    end
    E.register(self.scene, self.id, e, 0, 0, true, true)
    E.present(e, renderer, true)
end

return function(): Node<Lamp>
    return {
        scene = 7,
        id = 1,
        screen = 0,
        navDir = 1,
        still = false,
        paused = false,
        vw = 390,
        vh = 844,
        bp = 768,
        dev = 1,
        e = nil,
        clock = E.clock(),
        idle = 0,
        drawn = '',
        beamDrawn = '',
        built = false,
        init = init,
        advance = advance,
        draw = draw,
    }
end
