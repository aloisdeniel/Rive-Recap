-- Nocturne dwell clock.
--
-- The sequencing state machine owns *which* scene is shown; this script owns
-- only *time*: it waits for the entrance to settle, fills `screenProgress`
-- (0..1) over `autoAdvanceSeconds`, and fires the `navNext` trigger once when
-- the dwell completes. It never advances while paused, while a hold-to-pause
-- gesture is active, on the summary (screen 10), or when auto-advance is off.
-- Hosts that cannot ship scripts (unsigned web builds) can set
-- autoAdvanceEnabled=false and drive screenProgress / navNext themselves.

type Clock = {
    current: Property<number>?,
    progress: Property<number>?,
    seconds: Property<number>?,
    enabled: Property<boolean>?,
    paused: Property<boolean>?,
    holding: Property<boolean>?,
    reduced: Property<boolean>?,
    nextTrigger: PropertyTrigger?,
    lastScreen: number,
    settle: number,
    elapsed: number,
    fired: boolean,
}

local MIN_SECONDS = 3.0 -- readable minimum
local MAX_SECONDS = 60.0
local DEFAULT_SECONDS = 7.0
local SETTLE = 1.6 -- entrance settles ~1,200-1,800 ms after a scene change
local SETTLE_REDUCED = 0.35

local function clampSeconds(v: number): number
    if v ~= v or v == math.huge or v == -math.huge then
        return DEFAULT_SECONDS
    end
    return math.max(MIN_SECONDS, math.min(MAX_SECONDS, v))
end

local function bool(p: Property<boolean>?): boolean
    if p == nil then
        return false
    end
    return p.value
end

function init(self: Clock, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true -- init runs twice; the view model arrives on the second call
    end
    self.current = vm:getNumber('currentScreen')
    self.progress = vm:getNumber('screenProgress')
    self.seconds = vm:getNumber('autoAdvanceSeconds')
    self.enabled = vm:getBoolean('autoAdvanceEnabled')
    self.paused = vm:getBoolean('isPaused')
    self.holding = vm:getBoolean('isHolding')
    self.reduced = vm:getBoolean('reducedMotion')
    self.nextTrigger = vm:getTrigger('navNext')
    return true
end

local function setProgress(self: Clock, v: number)
    local p = self.progress
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

function advance(self: Clock, seconds: number): boolean
    local cur = self.current
    if cur == nil then
        return true
    end
    local screen = cur.value
    if screen ~= self.lastScreen then
        self.lastScreen = screen
        self.settle = 0
        self.elapsed = 0
        self.fired = false
        setProgress(self, 0)
    end
    if bool(self.paused) or bool(self.holding) then
        return true -- frozen: progress is preserved and resumes from here
    end
    local settleFor = if bool(self.reduced) then SETTLE_REDUCED else SETTLE
    if self.settle < settleFor then
        self.settle += seconds
        return true
    end
    local isFinal = screen >= 10
    if not bool(self.enabled) and not isFinal then
        return true
    end
    local secs = DEFAULT_SECONDS
    local s = self.seconds
    if s ~= nil then
        secs = clampSeconds(s.value)
    end
    self.elapsed += seconds
    local p = math.min(1, self.elapsed / secs)
    if isFinal then
        p = 1 -- the summary stays put; its segment simply reads complete
    end
    setProgress(self, p)
    if p >= 1 and not isFinal and not self.fired then
        self.fired = true
        local t = self.nextTrigger
        if t ~= nil then
            t:fire()
        end
    end
    return true
end

function draw(self: Clock, renderer: Renderer) end

return function(context: Context): Layout<Clock>
    return {
        current = nil, progress = nil, seconds = nil, enabled = nil, paused = nil, holding = nil, reduced = nil,
        nextTrigger = nil, lastScreen = -1, settle = 0, elapsed = 0, fired = false,
        init = init, advance = advance, draw = draw,
    }
end
