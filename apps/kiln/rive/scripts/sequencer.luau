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
--   * responsive placement of the art and card stages (_art*, _card*)
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
}

local SETTLE = 1.8
local SETTLE_REDUCED = 0.35
local HOLD = 0.35
local MIN_DWELL = 3.0
local MAX_DWELL = 60.0
local SPIN = 0.045 -- revolutions per second while idle

-- turntable hit regions in art-stage coordinates (390 x 560, bottom anchored)
local TURN_ZONES: { [number]: { number } } = {
    [1] = { 110, 150, 280, 420 },
    [2] = { 165, 90, 345, 450 },
    [3] = { 95, 330, 295, 432 },
    [7] = { 110, 170, 335, 420 },
}

local NUMS = {
    'currentScreen', 'screenProgress', 'autoAdvanceSeconds', 'personaIndex', '_navDir', '_command', '_artX', '_artY',
    '_artScale', '_cardX', '_cardY', '_cardScale', '_isEmpty', '_personaVariant', '_namePublic', '_hoursPublic',
    '_countSeconds', '_turnPhase', '_finished', '_settled', '_seg1', '_seg2', '_seg3', '_seg4', '_seg5', '_seg6',
    '_seg7', '_seg8', '_seg9', '_seg10',
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

local function place(self: Seq)
    local w = if self.size.x > 0 then self.size.x else 390
    local h = if self.size.y > 0 then self.size.y else 844
    local s = math.clamp(math.min((h - 250) / 594, w / 370), 0.5, 1.15)
    setNum(self, '_artScale', s)
    setNum(self, '_artX', w / 2 - 195 * s)
    setNum(self, '_artY', h - 560 * s)
    local cs = math.clamp(math.min((h - 330) / 514, (w - 48) / 300), 0.5, 1.12)
    setNum(self, '_cardScale', cs)
    setNum(self, '_cardX', w / 2 - 150 * cs)
    setNum(self, '_cardY', math.clamp(h * 0.28, 150, 252))
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

function resize(self: Seq, size: Vector)
    self.size = size
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
    if y < 66 or y > h - 92 then
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
        init = init,
        resize = resize,
        advance = advance,
        pointerDown = pointerDown,
        pointerMove = pointerMove,
        pointerUp = pointerUp,
        pointerExit = pointerExit,
    }
end
