--!strict
-- Sprig dwell clock: owns `screenProgress` and the auto-advance.
--
-- Replaces the 28-step state-machine chain of the first version, whose pause only took
-- effect at the next step boundary (up to dwell/28). Here pause is exact: the clock
-- simply stops accumulating on the frame `isPaused` or `_holdPaused` turns true and
-- resumes from the same progress.
--
--   * Every change of `currentScreen` restarts the clock (navigation, replay, auto).
--   * The dwell starts after the entrance settles (`settle`, 1.8 s), not on entry.
--   * Dwell = autoAdvanceSeconds clamped to 3..60 s (non-finite -> 7 s).
--   * autoAdvanceEnabled = false holds progress at 0; the summary (10) never advances.
--   * At 1.0 it writes _navDir = 1 and fires _navNext once, exactly like the Continue button.
--
-- Draws nothing. Without scripting the recap still navigates by tap/keys/buttons, it
-- just does not auto-advance.

type Clock = {
    settle: Input<number>,
    vm: ViewModel?,
    screen: Property<number>?,
    progress: Property<number>?,
    paused: Property<boolean>?,
    held: Property<boolean>?,
    enabled: Property<boolean>?,
    seconds: Property<number>?,
    navDir: Property<number>?,
    navNext: PropertyTrigger?,
    last: number,
    elapsed: number,
    value: number,
    fired: boolean,
}

function init(self: Clock, context: Context): boolean
    -- init runs more than once: the view model is absent the first time, and a host that binds its own
    -- UserRecap instance re-inits with it. Always (re)bind to the instance we are given now.
    local vm = context:viewModel()
    if vm == nil then
        return true
    end
    self.vm = vm
    self.screen = vm:getNumber('currentScreen')
    self.progress = vm:getNumber('screenProgress')
    self.paused = vm:getBoolean('isPaused')
    self.held = vm:getBoolean('_holdPaused')
    self.enabled = vm:getBoolean('autoAdvanceEnabled')
    self.seconds = vm:getNumber('autoAdvanceSeconds')
    self.navDir = vm:getNumber('_navDir')
    self.navNext = vm:getTrigger('_navNext')
    return true
end

local function dwell(self: Clock): number
    local p = self.seconds
    local s = if p ~= nil then p.value else 7
    if s ~= s or s == math.huge or s == -math.huge then
        s = 7
    end
    return math.clamp(s, 3, 60)
end

local function write(self: Clock, v: number)
    if v ~= self.value then
        self.value = v
        local p = self.progress
        if p ~= nil then
            p.value = v
        end
    end
end

function advance(self: Clock, seconds: number): boolean
    local sp = self.screen
    if sp == nil then
        return true
    end
    local cs = sp.value
    if cs ~= self.last then
        self.last = cs
        self.elapsed = 0
        self.fired = false
        write(self, 0)
    end
    local pz = self.paused
    local hd = self.held
    local en = self.enabled
    if (pz ~= nil and pz.value) or (hd ~= nil and hd.value) then
        return true -- frozen exactly where it is
    end
    if cs >= 10 or (en ~= nil and not en.value) then
        write(self, 0)
        self.elapsed = 0
        return true
    end
    self.elapsed += math.min(seconds, 0.1)
    local run = self.elapsed - self.settle
    if run <= 0 then
        return true
    end
    local v = math.min(1, run / dwell(self))
    write(self, v)
    if v >= 1 and not self.fired then
        self.fired = true
        local nd = self.navDir
        if nd ~= nil then
            nd.value = 1
        end
        local tr = self.navNext
        if tr ~= nil then
            tr:fire()
        end
    end
    return true
end

function draw(self: Clock, renderer: Renderer) end

return function(): Node<Clock>
    return {
        settle = 1.8,
        vm = nil,
        screen = nil,
        progress = nil,
        paused = nil,
        held = nil,
        enabled = nil,
        seconds = nil,
        navDir = nil,
        navNext = nil,
        last = -1,
        elapsed = 0,
        value = -1,
        fired = false,
        init = init,
        advance = advance,
        draw = draw,
    }
end
