--!strict
-- Marginalia paper theatre in 3D (scene 5, "genres explored").
--
-- A ScriptedDrawable that replaces the flat theatre with a small lit stage on
-- the GPU (scripts/etch3d.luau + shaders/etch3d.wgsl): a boarded stage with
-- two risers, a starry night backdrop, velvet curtains with real folds that
-- part and tie back, a pelmet with a gilt rail, and nine genre arches standing
-- in three rows at real depths. The carried moon (scene 4 -> 5) is the
-- theatre's spotlight: a spot light from where it hangs pools on the stage and
-- lights the arches; arch k is lit only when genresExplored >= k, otherwise it
-- stays an engraved ghost (hatched, unpainted) - the data still drives it.
--
-- Origin: the front centre of the stage floor (the vector theatre's origin).
-- Entrance (the scene's timing): curtains part 100-800 ms, the arches unfold
-- up from the boards row by row (back first) from 450 ms, the spot comes up
-- 800-1300 ms. Back navigation / reduced motion: settled at once. Pause
-- freezes it. It re-renders only while something moves or the size changes.
-- Without shaders it draws nothing and the vector theatre (Flat Fallback)
-- stays visible.

local E = require('scripts/etch3d')

type Etch = E.Etch

type Theatre = {
    genres: Input<number>,
    id: Input<number>,
    scene: Input<number>,
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
    key: string,
    drawn: string,
    built: boolean,
}

local OX, OXD, INK, INK2 = 0x782D3D, 0x571E2B, 0x252E3D, 0x3B4558
local PARCH, PAPER, PSHADE = 0xF1E8D5, 0xF8F2E4, 0xE4D6B8
local GREEN, GOLD = 0x3E5446, 0xBD914C

-- three rows (back to front): z, floor height, scale, face colour
local RISE = 46 -- each riser
local ROWS = {
    { z = -212, y = 2 * RISE, s = 0.86, col = PSHADE },
    { z = -134, y = RISE, s = 0.93, col = PAPER },
    { z = -52, y = 0, s = 1.0, col = PARCH },
}
local PELMET = 262 -- underside of the pelmet
local DOORS = { INK2, GREEN, OX }

function init(self: Theatre, context: Context): boolean
    if self.e == nil then
        self.e = E.new(context, false)
    end
    return true
end

local function here(self: Theatre): boolean
    return math.floor(self.screen + 0.5) == math.floor(self.scene + 0.5)
end

function advance(self: Theatre, seconds: number): boolean
    E.tick(self.clock, here(self), self.navDir < 0, self.still, self.paused, seconds)
    return true
end

-- the animated quantities at clock time t (s)
local function poseAt(t: number, genres: number)
    local open = E.easeInOut(E.prog(t, 100, 700))
    local arches = {}
    local k = 0
    for r = 1, 3 do
        for c = 1, 3 do
            k += 1
            local t0 = 450 + (r - 1) * 160 + (c - 1) * 60
            arches[k] = E.easeBack(E.prog(t, t0, 520))
        end
    end
    local spot = E.easeInOut(E.prog(t, 800, 500))
    local g = math.clamp(math.floor((genres or 0) + 0.5), 0, 99)
    return open, arches, spot, g
end

-- the height of a wall at (x, z) whose top lands just behind the pelmet
local function hiddenHeight(e: Etch, x: number, z: number): number
    local _, target = E.project(e, 0, PELMET, 26)
    target -= 12 -- a little above the pelmet's lower edge (hidden behind it)
    local lo, hi = 0, 900
    for _ = 1, 24 do
        local mid = (lo + hi) * 0.5
        local _, py = E.project(e, x, mid, z)
        if py < target then
            hi = mid
        else
            lo = mid
        end
    end
    return lo
end

local function build(self: Theatre, e: Etch, open: number, arches: { number }, spot: number, g: number)
    E.clear(e)
    local W2 = 196 -- half stage width
    local DEP = 250 -- stage depth
    -- stage floor, lip, risers
    E.add(e, E.QUAD, W2 * 2, DEP, 0, 0, 0, 0, 0, E.T(0, 0, -DEP * 0.5), 0xCDBA94, E.BOARDS, 1, 0, 0, 0.16, 1, 0, 0)
    E.add(e, E.QUAD, W2 * 2 + 8, 16, 0, 0, 0, 0, 0, E.chain(E.T(0, -8, 0.5), E.RX(math.pi / 2)), 0x8C6E45, E.PAINT,
        1, 0, 0, 0.2, 1, 0, 0)
    for i, rz in { -95, -172 } do
        local h = RISE * i
        local zf = rz
        local depth = (DEP + zf)
        E.add(e, E.QUAD, W2 * 2 - 30, depth, 0, 0, 0, 0, 0, E.T(0, h, zf - depth * 0.5), 0xD6C49E, E.BOARDS,
            1, 0, 0, 0.16, 1, 0, 0)
        E.add(e, E.QUAD, W2 * 2 - 30, RISE, 0, 0, 0, 0, 0, E.chain(E.T(0, h - RISE * 0.5, zf), E.RX(math.pi / 2)),
            0xA88B5E, E.PAINT, 1, 0, 0, 0.25, 1, 0, 0)
    end
    -- backdrop and wings: exactly as tall as the pelmet hides (nothing above it)
    local bh = hiddenHeight(e, 0, -DEP)
    E.add(e, E.QUAD, W2 * 2, bh, 0, 0, 0, 0, 0, E.chain(E.T(0, bh * 0.5, -DEP), E.RX(math.pi / 2)), INK2, E.NIGHT,
        1, 0, 0, 0, 0.7, 0, 0)
    local wh = hiddenHeight(e, W2, 0)
    for side = -1, 1, 2 do
        E.add(e, E.QUAD, wh, DEP, 0, 0, 0, 0, 0,
            E.chain(E.T(side * W2, wh * 0.5, -DEP * 0.5), E.RZ(math.pi / 2)), INK, E.PAINT, 0, 1, 0, 0, 0.5, 0, 0)
    end
    -- contact shadows under the arches, then the arches
    local k = 0
    for r = 1, 3 do
        local row = ROWS[r]
        for c = -1, 1 do
            k += 1
            local a = arches[k]
            local s = row.s
            local x = c * 100
            E.add(e, E.QUAD, 92 * s, 34 * s, 0, 0, 0, 0, 0, E.T(x, row.y + 0.35, row.z - 6 * s), 0x1A1410, E.SHADOW,
                0, 0, 0, 0, 0.30 * math.clamp(a, 0, 1), 0.7, 0)
        end
    end
    k = 0
    for r = 1, 3 do
        local row = ROWS[r]
        for c = -1, 1 do
            k += 1
            local a = arches[k]
            if a > 0.001 then
                local s = row.s
                local lit = if g >= k then 1 else 0.12
                local w, h, fr, dz = 70 * s, 120 * s, 9.5 * s, 12 * s
                -- hinged at its base: lies back on the boards, unfolds upright
                local m = E.chain(E.T(c * 100, row.y, row.z), E.RX(-math.pi / 2 * (1 - a)))
                local face = row.col
                E.add(e, E.ARCH, w, h, fr, dz, 0, 0, 0, m, face, E.PAINT, 0, 1, 0, 0.30, lit, 0, 0, 0.5)
                E.add(e, E.ARCH, w, h, fr, dz, 1, 0, 0, m, 0xD9C8A4, E.PAINT, 0, 0, 1, 0.45, lit, 0, 0, 0.45)
                E.add(e, E.ARCH, w, h, fr, dz, 2, 0, 0, m, 0xC9B48A, E.PAINT, 0, 0, 1, 0.45, lit, 0, 0, 0.6)
                E.add(e, E.ARCH, w, h, fr, dz, 3, 0, 0, m, DOORS[(k - 1) % 3 + 1], E.CLOTH, 0, 1, 0, 0.3, lit, 0, 0)
                -- gilt keystone boss
                E.add(e, E.SPHERE, 0, math.pi * 2, 0.05, math.pi - 0.05, 3.2 * s, 0, 0,
                    E.mul(m, E.T(0, h - fr * 0.5, dz * 0.5 + 1.2)), GOLD, E.BRASS, 1, 1, 0, 0.6, math.max(lit, 0.6), 0, 0)
            end
        end
    end
    -- curtains: hung behind the pelmet, parted and tied back
    local tie = 1 + (0.36 - 1) * open
    local widen = 2.02 - 1.02 * open
    for side = -1, 1, 2 do
        local m = E.chain(E.S(side, 1, 1), E.T(-206, 262, 16))
        E.add(e, E.CURTAIN, 104, 268, 7, 4.5, tie, widen, 0, m, OX, E.VELVET, 1, 0, 0, 0.30, 1, 0, 0)
    end
    -- pelmet (valance) with a gilt rail
    E.add(e, E.QUAD, 420, 36, 0, 0, 0, 0, 0, E.chain(E.T(0, 280, 26), E.RX(math.pi / 2)), OXD, E.VELVET,
        1, 0, 0, 0.3, 1, 0, 0)
    E.add(e, E.QUAD, 420, 26, 0, 0, 0, 0, 0, E.T(0, 262, 13), 0x431620, E.VELVET, 1, 0, 0, 0.3, 1, 0, 0)
    local rail, len = E.along(-210, 263, 27, 210, 263, 27)
    E.add(e, E.FRUSTUM, 0, math.pi * 2, 1.9, 1.9, len, 0, 0, rail, GOLD, E.BRASS, 1, 0, 0, 0, 1, 0, 0)
    -- the moon's light
    E.spot(e, 0, 360, 40, 0, -300, -190, math.rad(25), math.rad(11), 0xFFEBC4, 1.55 * spot, 430)
end

local function frame(e: Etch): E.Box
    local x0, y0, x1, y1 = 0, 0, 0, 0
    for _, p in { { -216, -18, 30 }, { 216, -18, 30 }, { -216, 310, 30 }, { 216, 310, 30 }, { -196, 0, -250 },
        { 196, 0, -250 } } do
        local px, py = E.project(e, p[1], p[2], p[3])
        x0 = math.min(x0, px)
        x1 = math.max(x1, px)
        y0 = math.min(y0, py)
        y1 = math.max(y1, py)
    end
    return { x = x0 - 2, y = y0 - 2, w = x1 - x0 + 4, h = y1 - y0 + 4 }
end

function draw(self: Theatre, renderer: Renderer)
    local e = self.e
    if e == nil then
        return
    end
    if not E.visible(self.clock) then
        E.register(self.scene, self.id, e, 0, 0, false, false)
        return
    end
    if not self.built then
        E.camera(e, math.rad(14), 0, 620, 800)
        E.light(e, -0.35, 0.55, 0.75, 0.42, 0.34, 0.34, 0.40, 0.9)
        E.ink(e, 0x231B16)
        self.built = true
    end
    local k = math.max(self.dev, 1) * E.artScale(math.floor(self.scene + 0.5), self.vw, self.vh, self.bp)
    local resized = E.ensure(e, frame(e), k, false)
    local open, arches, spot, g = poseAt(self.clock.t, self.genres)
    -- a cheap key of everything that moves, so a settled stage is not re-rendered
    local key = string.format('%.3f|%.3f|%d', open, spot, g)
    for i = 1, 9 do
        key ..= string.format('|%.3f', arches[i])
    end
    if resized or key ~= self.drawn then
        self.drawn = key
        build(self, e, open, arches, spot, g)
        E.render(e)
    end
    E.register(self.scene, self.id, e, 0, 0, false, true)
    E.present(e, renderer, false)
end

return function(): Node<Theatre>
    return {
        genres = 9,
        id = 1,
        scene = 5,
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
        key = '',
        drawn = '',
        built = false,
        init = init,
        advance = advance,
        draw = draw,
    }
end
