-- Kiln recap sequencer.
--
-- A fill-sized ScriptedLayout behind the whole recap. It draws nothing. It is
-- the clock and the navigation brain, and the only writer of UserRecap's
-- internal (underscore) properties:
--
--   * visible-scene list from showScreenN (intro/summary always eligible,
--     persona only with evidence), progress-segment visibility (_segN)
--   * navigation: _command (1 next, 2 previous, 3 pause toggle, 5 replay)
--     written by buttons/keys; tap zones (left third back, right two thirds
--     forward); press-and-hold pauses without firing a tap
--   * auto-advance after the entrance settles, frozen while paused/holding
--   * currentScreen, screenProgress, _navDir written back for every consumer
--   * the recapFinished latch (_finished), cleared by replay
--   * the optional turntable drag (_turnPhase) in its own hit region
--   * responsive placement (_art*, _card*, _copy*, ...): two layouts split by a
--     pure width breakpoint (layoutBreakpoint, default 768). Landscape when the
--     artboard is at least that wide, portrait otherwise; each one is computed
--     continuously from the real size, and recomputed on every resize
--
-- Scene choreography itself lives in the state machine, which reads these.

local rules = require('scripts/recap_rules')

type Props = {
    nums: { [string]: Property<number> },
    bools: { [string]: Property<boolean> },
    strs: { [string]: Property<string> },
}

type Seq = {
    p: Props?,
    vm: ViewModel?,
    size: Vector,
    lastScreen: number,
    sinceEnter: number,
    progress: number,
    latch: boolean,
    -- pointer
    mode: string,
    pressT: number,
    pressX: number,
    holding: boolean,
    lastX: number,
    dragAccum: number,
    dragDist: number,
    -- turntable
    phase: number,
    vel: number,
    started: boolean,
    cache: { [string]: number },
    -- responsive placement
    dpr: number,
    bp: number,
    land: boolean,
    artXR: number, -- art stage x for every scene
    artXL: number, -- landscape persona (scene 9): the art crosses to the other side
    artXCur: number,
    artXVel: number,
    snap: boolean,
    chrome: number,
}

local SETTLE = 1.8
local SETTLE_REDUCED = 0.35
local HOLD = 0.35
local MIN_DWELL = 3.0
local MAX_DWELL = 60.0
local SPIN = 0.02 -- turntable revolutions per second while idle (the 3D vessel turns with it)

-- turntable hit regions in art-stage coordinates (390 x 560, bottom anchored)
local TURN_ZONES: { [number]: { number } } = {
    [1] = { 110, 150, 280, 420 },
    [2] = { 165, 90, 345, 450 },
    [3] = { 80, 330, 310, 470 },
    [7] = { 110, 170, 335, 420 },
}

local NUMS = {
    'currentScreen', 'screenProgress', 'autoAdvanceSeconds', 'personaIndex', '_navDir', '_command', '_artX', '_artY',
    '_artScale', '_cardX', '_cardY', '_cardScale', '_isEmpty', '_personaVariant', '_namePublic', '_hoursPublic',
    '_countSeconds', '_turnPhase', '_finished', '_settled', '_seg1', '_seg2', '_seg3', '_seg4', '_seg5', '_seg6',
    '_seg7', '_seg8', '_seg9', '_seg10', 'layoutBreakpoint', '_landscape', '_stack', '_dpr', '_copyL', '_copyT',
    '_copyR', '_copyB', '_copyS', '_copyR4', '_c9T', '_altL', '_altR', '_c10T', '_c10B', '_alignL', '_alignC',
    '_align10', '_textC', '_bigK', '_padX', '_navX', '_actL', '_actR', '_actAlign', '_headVA', '_chromeS',
    '_chromeR', '_hdrT', '_ftrB', '_hintOn',
}
local BOOLS = {
    'autoAdvanceEnabled', 'isPaused', 'reducedMotion', 'shareIncludeName', 'shareIncludeSensitiveValues', '_frozen',
    '_holding', 'showScreen1', 'showScreen2', 'showScreen3', 'showScreen4', 'showScreen5', 'showScreen6', 'showScreen7',
    'showScreen8', 'showScreen9', 'showScreen10',
}
local STRS = { 'personaName' }

local function num(self: Seq, name: string): number
    local p = self.p
    if p == nil then
        return 0
    end
    local h = p.nums[name]
    if h == nil then
        return 0
    end
    return h.value
end

local function setNum(self: Seq, name: string, v: number)
    local p = self.p
    if p == nil then
        return
    end
    local h = p.nums[name]
    if h == nil then
        return
    end
    -- only write on change so binds and conditions are not dirtied every frame
    if self.cache[name] ~= v or h.value ~= v then
        self.cache[name] = v
        h.value = v
    end
end

local function bool(self: Seq, name: string): boolean
    local p = self.p
    if p == nil then
        return false
    end
    local h = p.bools[name]
    if h == nil then
        return false
    end
    return h.value
end

local function setBool(self: Seq, name: string, v: boolean)
    local p = self.p
    if p == nil then
        return
    end
    local h = p.bools[name]
    if h ~= nil and h.value ~= v then
        h.value = v
    end
end

local function finite(v: number, fallback: number): number
    if v ~= v or v == math.huge or v == -math.huge then
        return fallback
    end
    return v
end

-- ---------------------------------------------------------------- visibility

local function isVisible(self: Seq, n: number): boolean
    local vm = self.vm
    if vm == nil then
        return n == 1 or n == 10
    end
    return rules.isVisible(vm, n)
end

local function nextVisible(self: Seq, from: number): number?
    for n = math.floor(from) + 1, 10 do
        if isVisible(self, n) then
            return n
        end
    end
    return nil
end

local function prevVisible(self: Seq, from: number): number?
    for n = math.ceil(from) - 1, 1, -1 do
        if isVisible(self, n) then
            return n
        end
    end
    return nil
end

-- ---------------------------------------------------------------- navigation

local function entered(self: Seq, n: number)
    self.lastScreen = n
    self.sinceEnter = 0
    self.progress = 0
    setNum(self, 'screenProgress', 0)
    setNum(self, '_settled', 0)
end

local function go(self: Seq, n: number, dir: number)
    setNum(self, '_navDir', dir)
    setNum(self, 'currentScreen', n)
    entered(self, n)
end

local function goNext(self: Seq)
    local n = nextVisible(self, num(self, 'currentScreen'))
    if n ~= nil then
        go(self, n, 1)
    end
end

local function goPrev(self: Seq)
    local n = prevVisible(self, num(self, 'currentScreen'))
    if n ~= nil then
        go(self, n, -1)
    end
end

local function replay(self: Seq)
    self.latch = false
    setNum(self, '_finished', 0)
    go(self, 1, 1)
end

-- ---------------------------------------------------------------- derived values

local function derive(self: Seq)
    local vm = self.vm
    if vm ~= nil then
        rules.derive(vm)
    end
end

-- Layout alignment values (LayoutComponentStyle.layoutAlignmentType) and text alignment
local TOP_LEFT, TOP_CENTER, CENTER_LEFT, CENTER, BOTTOM_LEFT = 0, 1, 3, 4, 6
local TEXT_LEFT, TEXT_CENTER = 0, 2
-- The art stage is a 390 x 560 frame (bottom-anchored). Its art spans x 15..375 and
-- y -45..560 of it (the scene-2 twig rises above the frame), so a box of 360 x 605 is
-- what has to fit between the header and the bottom edge.
local ART_CONTENT_W = 360
local ART_CONTENT_H = 605
local HEADER_BOTTOM = 64
-- copy heights in layout units (worst case: scene 8, three-line headline + number)
local COPY_FIXED = 87 -- unit, support, gaps
local COPY_BIG = 257 -- headline + hero number, the part _bigK shrinks

local function breakpoint(self: Seq): number
    local bp = finite(num(self, 'layoutBreakpoint'), 768)
    if bp <= 0 then
        bp = 768
    end
    return bp
end

-- the copy box: visual column [x, x + cw] x [y, y + ch] at scale sc
-- header and footer: scaled by k about their top-left, kept edge to edge and at their margins
local function chrome(self: Seq, w: number, k: number)
    self.chrome = k
    setNum(self, '_chromeS', k)
    setNum(self, '_chromeR', w - w / k)
    setNum(self, '_hdrT', 12 * k)
    setNum(self, '_ftrB', 74 * k - 56)
end

local function copyBox(self: Seq, w: number, h: number, x: number, y: number, cw: number, ch: number, sc: number)
    setNum(self, '_copyS', sc)
    setNum(self, '_copyL', x)
    setNum(self, '_copyT', y)
    setNum(self, '_copyR', w - x - cw / sc)
    setNum(self, '_copyB', h - y - ch / sc)
end

local function place(self: Seq)
    local w = if self.size.x > 0 then self.size.x else 390
    local h = if self.size.y > 0 then self.size.y else 844
    local bp = breakpoint(self)
    self.bp = bp
    local land = w >= bp
    self.land = land
    -- portrait stacks copy over art while the canvas is tall enough; on short portrait
    -- canvases (a phone on its side, below the breakpoint) the art steps beside the copy
    local stack = not land and h >= w * 1.25
    setNum(self, '_landscape', if land then 1 else 0)
    -- the scene-1 hint is engraved on the plinth face (art y 452): hide it when it falls
    -- behind the footer controls
    local function hint(s: number, artY: number)
        setNum(self, '_hintOn', if artY + 458 * s < h - 78 then 1 else 0)
    end
    setNum(self, '_stack', if stack then 1 else 0)
    self.snap = true

    if stack then
        -- PORTRAIT, stacked: the 390 x 844 master, reflowed. Copy under the header, the
        -- art bottom-anchored and centred; type grows a little on wide/tall portraits.
        local s = math.clamp(math.min((h - 250) / 594, w / 370), 0.5, 1.15)
        setNum(self, '_artScale', s)
        self.artXR = w / 2 - 195 * s
        self.artXL = self.artXR
        -- bottom-anchored; on short stacks lifted so the lowest pieces (art y ~456: tile
        -- grid, persona bowl) stay above the footer controls
        local artY = math.min(h - 560 * s, h - 84 - 456 * s)
        setNum(self, '_artY', artY)
        hint(s, artY)
        local sc = math.clamp(math.min(w / 390, h / 844), 1, 1.3)
        local x = 28 * sc
        local cw = w - 2 * x
        copyBox(self, w, h, x, 86, cw, h - 86, sc)
        setNum(self, '_copyR4', w - x - cw / sc + 122) -- keeps scene-4 copy clear of the jug
        setNum(self, '_c9T', 92)
        setNum(self, '_altL', x)
        setNum(self, '_altR', w - x - cw / sc)
        setNum(self, '_c10T', 84)
        setNum(self, '_c10B', 0)
        setNum(self, '_alignL', TOP_LEFT)
        setNum(self, '_alignC', TOP_CENTER)
        setNum(self, '_align10', TOP_CENTER)
        setNum(self, '_textC', TEXT_CENTER)
        -- the art rises into the copy column on short stacks: shrink the display type (headline
        -- and number) so the copy ends where the art begins (1 at 390 x 844 and taller)
        local copyBottom = artY + 116 * s
        local k = math.clamp((copyBottom - 86 - COPY_FIXED) / 227, 0.45, 1)
        setNum(self, '_bigK', k)
        setNum(self, '_padX', 24)
        setNum(self, '_navX', 20)
        setNum(self, '_actL', 20)
        setNum(self, '_actR', 20)
        setNum(self, '_actAlign', CENTER)
        setNum(self, '_headVA', if k < 0.999 then 1 else 0)
        chrome(self, w, 1)
        -- the card starts below the summary copy (two headline lines + support at most) and
        -- ends above the footer; on short screens it shrinks rather than covering the copy
        local cy = math.clamp(h * 0.28, 196, 252)
        local cs = math.clamp(math.min((h - 330) / 514, (h - cy - 104) / 440, (w - 48) / 300), 0.5, 1.12)
        setNum(self, '_cardScale', cs)
        setNum(self, '_cardX', w / 2 - 150 * cs)
        setNum(self, '_cardY', cy)
        return
    end

    -- Two columns: copy on one side, the art (or the share card) on the other.
    local x, top, colW, gap, sc, padX
    -- landscape chrome grows with large canvases (1 at 1280 x 720, up to 1.5)
    local ck = if land then math.clamp(math.min(w / 1280, h / 720), 1, 1.5) else 1
    chrome(self, w, ck)
    local bandB = h - 90 * ck -- above the footer controls
    if land then
        -- LANDSCAPE: an editorial spread. Display type scales with the column, the copy is
        -- centred against the art, the composition is centred on very wide canvases.
        padX = math.clamp(w * 0.045, 32, 120)
        top = 76 * ck
        colW = math.clamp(w * 0.38, 300, 620)
        gap = math.clamp(w * 0.03, 24, 72)
        x = padX
    else
        -- PORTRAIT, short: portrait type at its authored size, copy top-aligned.
        padX = 24
        top = 72
        colW = math.clamp(w * 0.48, 240, 380)
        gap = 16
        x = 28
    end
    local regionR = w - (if land then padX else 20)
    -- landscape: the frame bottom-anchored (plinths rise from the bottom edge). Short portrait:
    -- the art (down to y 470, the lowest pieces) is fitted above the footer controls, which
    -- share the bottom row with it there
    local artBottom = if land then 0 else 80
    local artSpan = if land then ART_CONTENT_H else 515
    local s = math.min((h - artBottom - HEADER_BOTTOM * ck) / artSpan, (regionR - x - colW - gap) / ART_CONTENT_W)
    s = math.clamp(s, 0.35, 2.4)
    local artW = ART_CONTENT_W * s
    if land then
        -- centre the copy + art composition when the canvas is wider than it needs
        local extra = math.max(0, (regionR - x) - (colW + gap + artW))
        x += extra * 0.5
        regionR = x + colW + gap + artW
    end
    local artL = x + colW + gap -- art content box [artL, regionR]
    local artCx = (artL + regionR) / 2
    local artY = if land then h - 560 * s else h - artBottom - 470 * s
    setNum(self, '_artScale', s)
    setNum(self, '_artY', artY)
    hint(s, artY)
    self.artXR = artCx - 195 * s
    -- landscape persona: the art takes the left of the spread and the copy the right
    self.artXL = if land then x + artW / 2 - 195 * s else self.artXR

    local bh = bandB - top
    local regionH = if land then math.min(bh, math.max(w * 0.62, 300)) else bh
    if land then
        sc = math.clamp(math.min(colW / 330, regionH / 390), 1, 1.8)
    else
        sc = 1
    end
    copyBox(self, w, h, x, top, colW, regionH, sc)
    setNum(self, '_copyR4', w - x - colW / sc)
    setNum(self, '_c9T', top)
    local altX = if land then x + artW + gap else x
    setNum(self, '_altL', altX)
    setNum(self, '_altR', w - altX - colW / sc)
    -- summary: landscape centres its copy in the column, Share / Replay below it at the
    -- bottom; short portrait sets it right above Share / Replay, like a caption to the card
    setNum(self, '_c10T', top)
    setNum(self, '_c10B', if land then h - top - regionH / sc else h - top - (h - 96 - top) / sc)
    setNum(self, '_alignL', if land then CENTER_LEFT else TOP_LEFT)
    setNum(self, '_alignC', if land then CENTER_LEFT else TOP_LEFT)
    setNum(self, '_align10', if land then CENTER_LEFT else BOTTOM_LEFT)
    setNum(self, '_textC', TEXT_LEFT)
    setNum(self, '_bigK', math.clamp((regionH / sc - COPY_FIXED) / COPY_BIG, 0.45, 1))
    -- header / footer insets are in their own (scaled) units
    setNum(self, '_padX', padX / ck)
    setNum(self, '_navX', (padX - 4) / ck)
    setNum(self, '_actL', x / ck)
    setNum(self, '_actR', (w - x - colW) / ck)
    setNum(self, '_actAlign', CENTER_LEFT)
    setNum(self, '_headVA', if land then 1 else 0)
    -- the share card fills the art side, between the header and the bottom edge
    local cTop = top - 4
    local cH = h - 24 * ck - cTop
    local cW = regionR - artL
    local cs = math.clamp(math.min(cH / 440, cW / 300), 0.3, 2.2)
    setNum(self, '_cardScale', cs)
    setNum(self, '_cardX', artCx - 150 * cs)
    setNum(self, '_cardY', cTop + (cH - 440 * cs) / 2)
end

-- the art stage glides to its side of the spread (landscape persona) on a critically
-- damped spring; resizes and reduced motion snap
local function glide(self: Seq, dt: number, reduced: boolean)
    local cs = num(self, 'currentScreen')
    local target = if self.land and cs == 9 then self.artXL else self.artXR
    if self.snap or reduced then
        self.snap = false
        self.artXCur = target
        self.artXVel = 0
    else
        local k = 7.0
        local d = self.artXCur - target
        local a = -k * k * d - 2 * k * self.artXVel
        self.artXVel += a * dt
        self.artXCur += self.artXVel * dt
        if math.abs(self.artXCur - target) < 0.05 and math.abs(self.artXVel) < 0.5 then
            self.artXCur = target
            self.artXVel = 0
        end
    end
    setNum(self, '_artX', self.artXCur)
end

-- ---------------------------------------------------------------- lifecycle

function init(self: Seq, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true -- init runs twice; the view model arrives on the second call
    end
    local p: Props = { nums = {}, bools = {}, strs = {} }
    for _, n in ipairs(NUMS) do
        local h = vm:getNumber(n)
        if h ~= nil then
            p.nums[n] = h
        end
    end
    for _, n in ipairs(BOOLS) do
        local h = vm:getBoolean(n)
        if h ~= nil then
            p.bools[n] = h
        end
    end
    for _, n in ipairs(STRS) do
        local h = vm:getString(n)
        if h ~= nil then
            p.strs[n] = h
        end
    end
    self.p = p
    self.vm = vm
    return true
end

function resize(self: Seq, size: Vector, scale: number)
    self.size = size
    self.dpr = if scale ~= nil and scale > 0 then scale else 1
    setNum(self, '_dpr', self.dpr)
    place(self)
end

function advance(self: Seq, seconds: number): boolean
    if self.p == nil then
        return true
    end
    local dt = math.min(seconds, 0.1)
    derive(self)
    if not self.started then
        self.started = true
        setNum(self, '_dpr', self.dpr)
        place(self)
        local cs0 = num(self, 'currentScreen')
        if not isVisible(self, cs0) then
            cs0 = 1
        end
        go(self, cs0, 1)
    end

    -- commands from buttons / keys
    local c = num(self, '_command')
    if c ~= 0 then
        setNum(self, '_command', 0)
        self.cache['_command'] = 0
        if c == 1 then
            goNext(self)
        elseif c == 2 then
            goPrev(self)
        elseif c == 3 then
            setBool(self, 'isPaused', not bool(self, 'isPaused'))
        elseif c == 5 then
            replay(self)
        end
    end

    -- the host may also write currentScreen directly
    local cs = num(self, 'currentScreen')
    if cs ~= self.lastScreen then
        local dir = if cs >= self.lastScreen then 1 else -1
        setNum(self, '_navDir', dir)
        entered(self, cs)
    end
    if not isVisible(self, cs) then
        local n = nextVisible(self, cs) or prevVisible(self, cs) or 1
        go(self, n, if n >= cs then 1 else -1)
        cs = n
    end

    -- press and hold
    if self.mode == 'turn' then
        self.pressT += dt
    end
    if self.mode == 'nav' then
        self.pressT += dt
        if self.pressT >= HOLD then
            self.holding = true
        end
    end
    setBool(self, '_holding', self.holding)

    local reduced = bool(self, 'reducedMotion')
    -- the host may tune the breakpoint at runtime: re-derive the orientation
    if breakpoint(self) ~= self.bp then
        place(self)
    end
    glide(self, dt, reduced)
    local paused = bool(self, 'isPaused')
    local frozen = paused or self.holding or reduced
    setBool(self, '_frozen', frozen)

    -- dwell clock: starts once the entrance has settled
    self.sinceEnter += dt
    local settle = if reduced then SETTLE_REDUCED else SETTLE
    local settled = self.sinceEnter >= settle
    setNum(self, '_settled', if settled then 1 else 0)
    local last = cs == 10
    if last then
        setNum(self, 'screenProgress', math.min(1, self.sinceEnter / settle))
        if settled and not self.latch then
            self.latch = true
            setNum(self, '_finished', 1)
        end
    elseif settled and not paused and not self.holding and bool(self, 'autoAdvanceEnabled') then
        local dwell = math.clamp(finite(num(self, 'autoAdvanceSeconds'), 7), MIN_DWELL, MAX_DWELL)
        self.progress = math.min(1, self.progress + dt / dwell)
        setNum(self, 'screenProgress', self.progress)
        if self.progress >= 1 then
            goNext(self)
        end
    end

    -- turntable: weighted inertia after release, a slow idle turn otherwise
    local drag = self.mode == 'turn'
    if drag then
        local v = if dt > 0 then self.dragAccum / dt else 0
        self.vel = self.vel * 0.6 + v * 0.4
        self.dragAccum = 0
    elseif not frozen then
        self.phase += dt * SPIN + dt * self.vel
        self.vel *= math.exp(-dt * 2.4)
    elseif paused or self.holding then
        self.vel = 0
    end
    if reduced and not drag then
        self.vel = 0
    end
    self.phase = self.phase - math.floor(self.phase)
    setNum(self, '_turnPhase', self.phase)
    return true
end

-- ---------------------------------------------------------------- pointer

local function toArt(self: Seq, x: number, y: number): (number, number)
    local s = num(self, '_artScale')
    if s <= 0 then
        s = 1
    end
    return (x - num(self, '_artX')) / s, (y - num(self, '_artY')) / s
end

local function inTurnZone(self: Seq, x: number, y: number): boolean
    local z = TURN_ZONES[num(self, 'currentScreen')]
    if z == nil then
        return false
    end
    local ax, ay = toArt(self, x, y)
    return ax >= z[1] and ax <= z[3] and ay >= z[2] and ay <= z[4]
end

function pointerDown(self: Seq, event: PointerEvent)
    local x, y = event.position.x, event.position.y
    local h = if self.size.y > 0 then self.size.y else 844
    local k = if self.chrome > 0 then self.chrome else 1
    if y < 66 * k or y > h - 92 * k then
        self.mode = 'none' -- header and controls belong to their own listeners
        return
    end
    if inTurnZone(self, x, y) then
        self.mode = 'turn'
        self.lastX = x
        self.pressX = x
        self.pressT = 0
        self.vel = 0
        self.dragAccum = 0
        self.dragDist = 0
        return
    end
    self.mode = 'nav'
    self.pressT = 0
    self.pressX = x
    self.holding = false
end

function pointerMove(self: Seq, event: PointerEvent)
    if self.mode == 'turn' then
        local x = event.position.x
        local s = math.max(0.5, num(self, '_artScale'))
        local d = (x - self.lastX) / (2 * math.pi * 92 * s)
        self.dragDist += math.abs(x - self.lastX)
        self.lastX = x
        self.phase += d
        self.dragAccum += d
    end
end

function pointerUp(self: Seq, event: PointerEvent)
    -- a still, quick press on the turntable is a plain tap; any drag never navigates
    local tapOnTurntable = self.mode == 'turn' and self.dragDist < 6 and self.pressT < HOLD
    if self.mode == 'nav' or tapOnTurntable then
        if not self.holding then
            local w = if self.size.x > 0 then self.size.x else 390
            if self.pressX < w / 3 then
                goPrev(self)
            else
                goNext(self)
            end
        end
        self.holding = false
    end
    self.mode = 'none'
end

function pointerExit(self: Seq, event: PointerEvent)
    self.holding = false
    self.mode = 'none'
end

return function(context: Context): Layout<Seq>
    return {
        p = nil,
        vm = nil,
        size = Vector.xy(0, 0),
        lastScreen = 1,
        sinceEnter = 0,
        progress = 0,
        latch = false,
        mode = 'none',
        pressT = 0,
        pressX = 0,
        holding = false,
        lastX = 0,
        dragAccum = 0,
        dragDist = 0,
        phase = 0.12,
        vel = 0,
        started = false,
        cache = {},
        dpr = 1,
        bp = 768,
        land = false,
        artXR = 0,
        artXL = 0,
        artXCur = 0,
        artXVel = 0,
        snap = true,
        chrome = 1,
        init = init,
        resize = resize,
        advance = advance,
        pointerDown = pointerDown,
        pointerMove = pointerMove,
        pointerUp = pointerUp,
        pointerExit = pointerExit,
    }
end
