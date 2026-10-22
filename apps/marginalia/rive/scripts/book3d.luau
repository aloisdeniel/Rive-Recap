--!strict
-- Marginalia 3D open book (scenes 3, 4, 8 and the persona plates of 9).
--
-- A ScriptedDrawable that replaces the flat vector "open book". It is a real
-- book on the GPU (scripts/etch3d.luau + shaders/etch3d.wgsl): two cloth
-- boards with thickness and overhang, two page blocks whose tops rise out of
-- the gutter and roll over to the fore-edge (greeked type on the top leaves,
-- the leaves visible as fine lines on the tail and the fore-edge), a soft
-- shadow on whatever it lies on, lit from the upper left and printed with the
-- recap's engraved hatching in its shade.
--
-- The drawable's origin is the front of the gutter, at the base of the pages
-- (the vector book's origin), so it drops into the same place.
--
-- Entrance: the two halves stand up against each other and open flat (the
-- vector book's "pages open" beat), on the scene's own timing (delay, dur).
-- Back navigation and reduced motion show it open at once; pause freezes it.
-- It renders only while the pose or the size changes; otherwise it redraws the
-- cached image. Without shader support it draws nothing, and the Page Stage
-- leaves the vector book (the "Flat Fallback" nodes) visible instead.

local E = require('scripts/etch3d')

type Book = {
    width: Input<number>,
    id: Input<number>, -- unique per page; the node is named 'GPU <id>' (see Page Stage)
    cover: Input<number>, -- 0xRRGGBB
    scene: Input<number>,
    want: Input<number>, -- persona row this book belongs to (-1: any)
    delay: Input<number>, -- ms after the scene (row) arrives
    dur: Input<number>, -- ms to open
    screen: Input<number>,
    row: Input<number>,
    navDir: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    vw: Input<number>,
    vh: Input<number>,
    bp: Input<number>,
    dev: Input<number>,
    e: Etch?,
    clock: E.Clock,
    pose: number,
    drawn: number,
    built: boolean,
}

type Etch = E.Etch

local PAPER, EDGE = 0xF8F2E4, 0xE9DDC2
local START = math.rad(78) -- each half stands up this far before it opens

function init(self: Book, context: Context): boolean
    if self.e == nil then
        self.e = E.new(context, false)
    end
    return true
end

local function here(self: Book): boolean
    if math.floor(self.screen + 0.5) ~= math.floor(self.scene + 0.5) then
        return false
    end
    local w = math.floor(self.want + 0.5)
    return w < 0 or math.floor(self.row + 0.5) == w
end

function advance(self: Book, seconds: number): boolean
    E.tick(self.clock, here(self), self.navDir < 0, self.still, self.paused, seconds)
    local p = E.prog(self.clock.t, self.delay, self.dur)
    self.pose = E.easeInOut(p)
    return true
end

-- dimensions from the spread width (design units)
local function dims(W: number)
    local hw = W * 0.5
    return {
        hw = hw,
        D = W * 0.47, -- page depth (head to tail)
        tb = math.max(1.6, W * 0.010), -- board thickness
        T = W * 0.030, -- page block at the fore-edge
        C = W * 0.026, -- the crown of the pages
        ov = W * 0.016, -- board overhang
        g0 = W * 0.0008, -- half the gutter gap
        Wp = hw - W * 0.024, -- page block width (per half)
    }
end

local function build(self: Book, e: Etch, open: number)
    local W = math.max(self.width, 40)
    local d = dims(W)
    local cover = math.floor(self.cover + 0.5)
    local a = START * (1 - open)
    E.clear(e)
    -- soft shadow on the table / plate (first, so it lies under everything)
    local sw = W + 2 * d.ov + W * 0.10
    local sd = d.D + 2 * d.ov + W * 0.08
    local spread = 0.55 + 0.45 * open
    E.add(e, E.QUAD, sw * spread, sd, 0, 0, 0, 0, 0, E.T(0, -d.tb - 0.4, 0), 0x2A2118, E.SHADOW,
        0, 0, 0, 0, 0.30, 0.42, 0)
    local bw = d.g0 + d.Wp + d.ov -- board width per half
    local bd = d.D + 2 * d.ov
    for side = -1, 1, 2 do
        -- hinge: the inner bottom edge of the board, on the spine axis
        local hinge = E.chain(E.S(side, 1, 1), E.T(0, -d.tb, 0), E.RZ(a), E.T(0, d.tb, 0))
        -- board: top, front edge (tail), outer edge
        E.add(e, E.QUAD, bw, bd, 0, 0, 0, 0, 0, E.mul(hinge, E.T(bw * 0.5, 0, 0)), cover, E.CLOTH,
            1, 0, 0, 0.25, 1, 0, 0)
        E.add(e, E.QUAD, bw, d.tb, 0, 0, 0, 0, 0,
            E.mul(hinge, E.chain(E.T(bw * 0.5, -d.tb * 0.5, bd * 0.5), E.RX(math.pi / 2))), cover, E.CLOTH,
            1, 0, 0, 0.3, 1, 0, 0)
        E.add(e, E.QUAD, d.tb, bd, 0, 0, 0, 0, 0,
            E.mul(hinge, E.chain(E.T(bw, -d.tb * 0.5, 0), E.RZ(math.pi / 2))), cover, E.CLOTH,
            0, 0, 1, 0.3, 1, 0, 0)
        -- page block on the board: top (type), fore-edge, tail (facing us), head
        local pm = E.mul(hinge, E.T(d.g0, 0, 0))
        local spacing = math.max(3.2, W * 0.024)
        E.add(e, E.PAGES, d.Wp, d.D, d.T, d.C, 0, side * 3.7, 0, pm, PAPER, E.PAGE,
            1, 0, 0, 0.22, 1, spacing, 1)
        E.add(e, E.PAGES, d.Wp, d.D, d.T, d.C, 1, 0, 0, pm, EDGE, E.EDGES,
            0, 1, 0, 0, 1, math.max(4, d.T * 0.9), 0)
        E.add(e, E.PAGES, d.Wp, d.D, d.T, d.C, 2, 0, 0, pm, EDGE, E.EDGES,
            0, 1, 0, 0, 1, math.max(4, d.T * 0.9), 0)
        E.add(e, E.PAGES, d.Wp, d.D, d.T, d.C, 3, 0, 0, pm, EDGE, E.EDGES,
            0, 1, 0, 0, 1, math.max(4, d.T * 0.9), 0)
    end
end

local function frame(self: Book, e: Etch): E.Box
    -- bounds of every pose: open flat, and the halves stood up
    local W = math.max(self.width, 40)
    local d = dims(W)
    local x0, y0, x1, y1 = 0, 0, 0, 0
    local bw = d.g0 + d.Wp + d.ov
    local zs = { -d.D * 0.5 - d.ov, d.D * 0.5 + d.ov }
    local function grow(x: number, y: number, z: number)
        local px, py = E.project(e, x, y, z)
        x0 = math.min(x0, px)
        x1 = math.max(x1, px)
        y0 = math.min(y0, py)
        y1 = math.max(y1, py)
    end
    for _, z in zs do
        for side = -1, 1, 2 do
            grow(side * (bw + W * 0.07), -d.tb, z * 1.12)
            grow(side * bw, d.T + d.C * 1.2, z)
            local c, s = math.cos(START), math.sin(START)
            grow(side * (bw * c + (d.T + d.C) * s), bw * s + d.T, z)
        end
    end
    local m = 4
    return { x = x0 - m, y = y0 - m, w = x1 - x0 + 2 * m, h = y1 - y0 + 2 * m }
end

local function setScene(self: Book, e: Etch)
    local W = math.max(self.width, 40)
    E.camera(e, math.rad(31), 0, W * 3.4, W * 1.4)
    E.light(e, -0.55, 0.85, 0.55, 0.62, 0.50, 0.47, 0.42, 0.85)
    E.ink(e, 0x3A2E24)
end

function draw(self: Book, renderer: Renderer)
    local e = self.e
    if e == nil then
        return
    end
    if not E.visible(self.clock) then
        E.register(self.scene, self.id, e, 0, 0, false, false)
        return
    end
    if not self.built then
        setScene(self, e)
        self.built = true
    end
    local k = math.max(self.dev, 1) * E.artScale(math.floor(self.scene + 0.5), self.vw, self.vh, self.bp)
    local W = math.max(self.width, 40)
    local d = dims(W)
    renderer:save()
    -- world origin = the gutter's centre; shift so its front edge sits on ours
    local fx, fy = E.project(e, 0, 0, d.D * 0.5)
    renderer:transform(Mat2D.withTranslation(-fx, -fy))
    local resized = E.ensure(e, frame(self, e), k, false)
    if resized or math.abs(self.pose - self.drawn) > 0.002 or self.drawn < 0 then
        self.drawn = self.pose
        build(self, e, self.pose)
        E.render(e)
    end
    E.register(self.scene, self.id, e, -fx, -fy, false, true)
    E.present(e, renderer, false)
    renderer:restore()
end

return function(): Node<Book>
    return {
        width = 300,
        id = 1,
        cover = 0x252E3D,
        scene = 8,
        want = -1,
        delay = 0,
        dur = 500,
        screen = 0,
        row = 0,
        navDir = 1,
        still = false,
        paused = false,
        vw = 390,
        vh = 844,
        bp = 768,
        dev = 1,
        e = nil,
        clock = E.clock(),
        pose = 1,
        drawn = -1,
        built = false,
        init = init,
        advance = advance,
        draw = draw,
    }
end
