-- Switchyard recap sequencer.
--
-- The one authority over navigation. It owns no user data: it reads the
-- UserRecap instance bound to the artboard and writes back only the
-- documented sequencing fields (currentScreen, screenProgress, isPaused for
-- hold-to-pause) and "_"-prefixed playheads/signals.
--
--   * story taps: right two-thirds -> next, left third -> previous
--     (story window only; dock buttons, header and the route-chip region on
--     scene 4 are excluded so decorative hits never navigate)
--   * press-and-hold (> 0.35 s) pauses while held; the release never taps
--   * dwell timer starts after the entrance settles, never runs while paused,
--     auto-advance clamped to [4, 60] s, disabled by autoAdvanceEnabled
--   * derived visible-scene list from showScreenN (1 and 10 always kept),
--     skipping hidden scenes both ways; the progress segments drawn here are
--     exactly that list
--   * count-up playheads _count2.._count8 (0..1, 200 -> 1200 ms)
--   * persona row mapping (personaIndex -> slot, colour, ink, default copy)
--   * button triggers from the state machine (_nextTapped, _prevTapped,
--     _pauseTapped, _replayTapped)

type Seq = {
    vm: ViewModel?,
    size: Vector,
    sceneTime: number,
    settledAt: number,
    lastScreen: number,
    pressing: boolean,
    holding: boolean,
    pressTime: number,
    pressX: number,
    pressY: number,
    clock: number,
    prevPaused: boolean,
    lastPersona: number,
    initialised: boolean,
    paint: Paint,
    track: Paint,
    done: Paint,
    segPath: Path,
}

local W = 390
local STORY_TOP = 84
local STORY_BOTTOM = 738
local HOLD_SECONDS = 0.35
local SETTLE = 1.8
local SETTLE_RM = 0.35

local PERSONAS = {
    { name = 'City Connector', desc = 'You make the connections.', color = Color.rgb(0x1B, 0x4E, 0xD0), dark = true },
    { name = 'Scenic Rider', desc = 'You enjoy the view along the way.', color = Color.rgb(0xFF, 0xD6, 0x4B), dark = false },
    { name = 'Route Collector', desc = 'There is always another line to try.', color = Color.rgb(0xF5, 0xF2, 0xE9), dark = false },
    { name = 'Weekend Roamer', desc = 'You give curiosity a destination.', color = Color.rgb(0x17, 0x1B, 0x20), dark = true },
}

local function num(self: Seq, name: string, fallback: number): number
    local vm = self.vm
    if vm == nil then
        return fallback
    end
    local p = vm:getNumber(name)
    if p == nil then
        return fallback
    end
    local v = p.value
    if v ~= v or v == math.huge or v == -math.huge then
        return fallback
    end
    return v
end

local function setNum(self: Seq, name: string, v: number)
    local vm = self.vm
    if vm == nil then
        return
    end
    local p = vm:getNumber(name)
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function bool(self: Seq, name: string, fallback: boolean): boolean
    local vm = self.vm
    if vm == nil then
        return fallback
    end
    local p = vm:getBoolean(name)
    if p == nil then
        return fallback
    end
    return p.value
end

local function setBool(self: Seq, name: string, v: boolean)
    local vm = self.vm
    if vm == nil then
        return
    end
    local p = vm:getBoolean(name)
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function str(self: Seq, name: string): string
    local vm = self.vm
    if vm == nil then
        return ''
    end
    local p = vm:getString(name)
    if p == nil then
        return ''
    end
    return p.value
end

local function setStr(self: Seq, name: string, v: string)
    local vm = self.vm
    if vm == nil then
        return
    end
    local p = vm:getString(name)
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

-- ------------------------------------------------------------ visibility
local function isEmpty(self: Seq): boolean
    for n = 2, 8 do
        if bool(self, 'showScreen' .. tostring(n), true) then
            return false
        end
    end
    return true
end

local function visibleList(self: Seq): { number }
    local list = { 1 }
    local empty = isEmpty(self)
    for n = 2, 8 do
        if bool(self, 'showScreen' .. tostring(n), true) then
            table.insert(list, n)
        end
    end
    if not empty and bool(self, 'showScreen9', true) and str(self, 'personaName') ~= '' then
        table.insert(list, 9)
    end
    table.insert(list, 10) -- summary is always reachable (intro -> summary at minimum)
    return list
end

local function indexOf(list: { number }, n: number): number
    for i, v in ipairs(list) do
        if v == n then
            return i
        end
    end
    return 0
end

local function currentScreen(self: Seq): number
    local c = math.floor(num(self, 'currentScreen', 1) + 0.5)
    if c < 1 or c > 10 then
        c = 1
    end
    return c
end

-- ------------------------------------------------------------ navigation
local function goTo(self: Seq, target: number, dir: number)
    setNum(self, '_navDir', dir)
    setNum(self, 'currentScreen', target)
    setNum(self, 'screenProgress', 0)
    setNum(self, '_activeRoute', 0)
    if target >= 2 and target <= 8 then
        setNum(self, '_count' .. tostring(target), 0)
    end
    self.sceneTime = 0
    self.lastScreen = target
end

local function step(self: Seq, delta: number)
    local list = visibleList(self)
    local cur = currentScreen(self)
    local i = indexOf(list, cur)
    if i == 0 then
        -- current scene became ineligible: snap to the nearest visible one
        for k, v in ipairs(list) do
            if v >= cur then
                i = k
                break
            end
        end
        if i == 0 then
            i = #list
        end
    end
    local j = i + delta
    if j < 1 or j > #list then
        return
    end
    goTo(self, list[j], if delta > 0 then 1 else -1)
end

local function replay(self: Seq)
    for n = 2, 8 do
        setNum(self, '_count' .. tostring(n), 0)
    end
    local vm = self.vm
    if vm then
        local t = vm:getTrigger('_replay')
        if t then
            t:fire()
        end
    end
    goTo(self, 1, 1)
end

local function togglePause(self: Seq)
    setBool(self, 'isPaused', not bool(self, 'isPaused', false))
end

-- ------------------------------------------------------------ persona
local function applyPersona(self: Seq, overwriteCopy: boolean)
    local idx = math.floor(num(self, 'personaIndex', 0) + 0.5)
    local slot = if idx >= 0 and idx <= 3 then idx else 0
    local row = PERSONAS[slot + 1]
    setNum(self, '_personaSlot', slot)
    local vm = self.vm
    if vm == nil then
        return
    end
    local c = vm:getColor('personaColor')
    if c then
        c.value = row.color
    end
    local ink = vm:getColor('_personaInk')
    if ink then
        ink.value = if row.dark then Color.rgb(0xF5, 0xF2, 0xE9) else Color.rgb(0x17, 0x1B, 0x20)
    end
    -- Copy: the host may localise personaName/Description; we only fill the
    -- English defaults when the index changes at runtime or the copy is empty
    -- (and never for an explicit "no persona": personaIndex < 0).
    local current = str(self, 'personaName')
    local staleDefault = false
    for i, r in ipairs(PERSONAS) do
        if i ~= slot + 1 and r.name == current then
            staleDefault = true
        end
    end
    if idx >= 0 and (overwriteCopy or current == '' or staleDefault) then
        setStr(self, 'personaName', row.name)
        setStr(self, 'personaDescription', row.desc)
    end
    self.lastPersona = idx
end

-- ------------------------------------------------------------ lifecycle
function init(self: Seq, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true
    end
    self.vm = vm
    local nt = vm:getTrigger('_nextTapped')
    if nt then
        nt:addListener(vm, function(_a)
            step(self, 1)
        end)
    end
    local pt = vm:getTrigger('_prevTapped')
    if pt then
        pt:addListener(vm, function(_a)
            step(self, -1)
        end)
    end
    local pa = vm:getTrigger('_pauseTapped')
    if pa then
        pa:addListener(vm, function(_a)
            togglePause(self)
        end)
    end
    local rp = vm:getTrigger('_replayTapped')
    if rp then
        rp:addListener(vm, function(_a)
            replay(self)
        end)
    end
    return true
end

function resize(self: Seq, size: Vector, scale: number)
    self.size = size
end

local function easeOutCubic(t: number): number
    local u = 1 - t
    return 1 - u * u * u
end

function advance(self: Seq, seconds: number): boolean
    if self.vm == nil then
        return true
    end
    self.clock += seconds
    if not self.initialised then
        self.initialised = true
        applyPersona(self, false)
        local cur = currentScreen(self)
        local list = visibleList(self)
        if indexOf(list, cur) == 0 then
            goTo(self, 1, 1)
        end
        self.lastScreen = currentScreen(self)
    end
    -- runtime persona change -> remap atomically in this frame
    local pidx = math.floor(num(self, 'personaIndex', 0) + 0.5)
    if pidx ~= self.lastPersona then
        applyPersona(self, true)
    end
    setBool(self, '_isEmpty', isEmpty(self))

    local paused = bool(self, 'isPaused', false)
    local rm = bool(self, 'reducedMotion', false)
    setStr(self, '_pauseButtonLabel', if paused then str(self, 'playLabel') else str(self, 'pauseLabel'))

    -- host wrote currentScreen directly (deep link / replay from host)
    local cur = currentScreen(self)
    if cur ~= self.lastScreen then
        local list = visibleList(self)
        if indexOf(list, cur) == 0 then
            for _, v in ipairs(list) do
                if v >= cur then
                    cur = v
                    break
                end
            end
            if indexOf(list, cur) == 0 then
                cur = list[#list]
            end
        end
        goTo(self, cur, if cur >= self.lastScreen then 1 else -1)
    end

    -- hold-to-pause
    if self.pressing and not self.holding and self.clock - self.pressTime > HOLD_SECONDS then
        self.holding = true
        self.prevPaused = paused
        setBool(self, 'isPaused', true)
        paused = true
    end

    if not paused then
        self.sceneTime += seconds
    end

    -- count-up playhead for the current metric scene (200 -> 1200 ms)
    if cur >= 2 and cur <= 8 then
        local v = 1
        if not rm then
            local t = math.clamp((self.sceneTime - 0.2) / 1.0, 0, 1)
            v = easeOutCubic(t)
        end
        setNum(self, '_count' .. tostring(cur), v)
    end

    -- dwell timer (starts once the entrance has settled)
    local settle = if rm then SETTLE_RM else SETTLE
    if cur == 9 then
        settle = if rm then SETTLE_RM else 2.6
    end
    local dwell = num(self, 'autoAdvanceSeconds', 7)
    dwell = math.clamp(dwell, 4, 60)
    local enabled = bool(self, 'autoAdvanceEnabled', true)
    local progress = 0
    if cur == 10 then
        progress = math.clamp(self.sceneTime / settle, 0, 1)
    elseif self.sceneTime > settle then
        progress = math.clamp((self.sceneTime - settle) / dwell, 0, 1)
    end
    setNum(self, 'screenProgress', progress)
    if enabled and not paused and cur ~= 10 and progress >= 1 then
        step(self, 1)
    end
    return true
end

-- ------------------------------------------------------------ pointer
local function inChips(self: Seq, x: number, y: number): number
    if currentScreen(self) ~= 4 then
        return 0
    end
    if y < 460 or y > 516 then
        return 0
    end
    for i = 1, 3 do
        local x0 = 24 + (i - 1) * 84
        if x >= x0 - 4 and x <= x0 + 80 then
            return i
        end
    end
    return 0
end

function pointerDown(self: Seq, event: PointerEvent)
    local x, y = event.position.x, event.position.y
    if y < STORY_TOP or y > STORY_BOTTOM or inChips(self, x, y) > 0 then
        return
    end
    self.pressing = true
    self.holding = false
    self.pressTime = self.clock
    self.pressX = x
    self.pressY = y
end

function pointerUp(self: Seq, event: PointerEvent)
    local x, y = event.position.x, event.position.y
    local chip = inChips(self, x, y)
    if chip > 0 and not self.pressing then
        local active = num(self, '_activeRoute', 0)
        setNum(self, '_activeRoute', if active == chip then 0 else chip)
        return
    end
    if not self.pressing then
        return
    end
    self.pressing = false
    if self.holding then
        self.holding = false
        setBool(self, 'isPaused', self.prevPaused)
        return
    end
    if y < STORY_TOP or y > STORY_BOTTOM then
        return
    end
    local w = if self.size.x > 0 then self.size.x else W
    if x < w / 3 then
        step(self, -1)
    else
        step(self, 1)
    end
end

function pointerExit(self: Seq, event: PointerEvent)
    if self.holding then
        setBool(self, 'isPaused', self.prevPaused)
    end
    self.pressing = false
    self.holding = false
end

-- ------------------------------------------------------------ progress segments
function draw(self: Seq, renderer: Renderer)
    if self.vm == nil then
        return
    end
    local list = visibleList(self)
    local count = #list
    local cur = currentScreen(self)
    local idx = indexOf(list, cur)
    local x0, x1, y, h, gap = 24, 366, 62, 4, 4
    local segW = ((x1 - x0) - gap * (count - 1)) / count
    local prog = num(self, 'screenProgress', 0)
    for i = 1, count do
        local sx = x0 + (i - 1) * (segW + gap)
        local p = Path.new()
        p:moveTo(Vector.xy(sx, y))
        p:lineTo(Vector.xy(sx + segW, y))
        p:lineTo(Vector.xy(sx + segW, y + h))
        p:lineTo(Vector.xy(sx, y + h))
        p:close()
        renderer:drawPath(p, self.track)
        local f = 0
        if i < idx then
            f = 1
        elseif i == idx then
            f = prog
        end
        if f > 0 then
            local q = Path.new()
            q:moveTo(Vector.xy(sx, y))
            q:lineTo(Vector.xy(sx + segW * f, y))
            q:lineTo(Vector.xy(sx + segW * f, y + h))
            q:lineTo(Vector.xy(sx, y + h))
            q:close()
            renderer:drawPath(q, if i < idx then self.done else self.paint)
        end
    end
end

return function(context: Context): Layout<Seq>
    return {
        vm = nil,
        size = Vector.xy(390, 844),
        sceneTime = 0,
        settledAt = 0,
        lastScreen = 1,
        pressing = false,
        holding = false,
        pressTime = 0,
        pressX = 0,
        pressY = 0,
        clock = 0,
        prevPaused = false,
        lastPersona = -99,
        initialised = false,
        paint = Paint.with({ color = Color.rgb(0xF4, 0x45, 0x33) }),
        track = Paint.with({ color = Color.rgba(0x17, 0x1B, 0x20, 40) }),
        done = Paint.with({ color = Color.rgb(0x17, 0x1B, 0x20) }),
        segPath = Path.new(),
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
        pointerDown = pointerDown,
        pointerUp = pointerUp,
        pointerExit = pointerExit,
    }
end
