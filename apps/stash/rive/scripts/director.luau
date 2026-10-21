--!strict
-- Stash recap director.
--
-- A full-bleed ScriptedLayout that draws nothing. It owns the *sequencing
-- logic* that markup cannot express compactly and writes the results back into
-- the single UserRecap instance, where the state machine and every bind read
-- them:
--   * the derived visible-scene list (showScreenN, with intro/summary forced on)
--   * next / previous with hidden scenes skipped, rapid taps coalesced per frame
--   * the dwell timer (starts after the entrance settles) and screenProgress
--   * pause (isPaused, press-and-hold, isSharing, appBackgrounded)
--   * tap zones: left third = back, right two-thirds = next, hold = pause
--   * per-scene count-up playheads (_count1.._count10, local animation state)
--   * persona row mapping (personaIndex -> name/description/colour, atomic)
--   * input sanitising (negative / non-finite stats clamp to 0)
--   * stage fit for 320x568 .. desktop (_stageX/_stageY/_stageScale)
-- Events (screenChanged, recapFinished, shareTapped) are fired by the state
-- machine and listeners, not here: scripts cannot raise Rive events.

local DESIGN_W = 390
local DESIGN_H = 844
local HEADER_H = 64
local FOOTER_H = 104
local HOLD_SECONDS = 0.35
local MIN_DWELL = 3
local SETTLE = 2.2
local SETTLE_RM = 0.4
-- the decorative coin toy, in design coordinates (excluded from tap zones)
local TOY = { x0 = 4, y0 = 646, x1 = 98, y1 = 744 }

-- count-up windows (seconds after entry, forward navigation), timed to each
-- scene's illustration: coins landing, tokens snapping, jars arriving
local COUNT: { [number]: { start: number, dur: number, linear: boolean } } = {
    [1] = { start = 0.5, dur = 1.0, linear = false },
    [2] = { start = 0.6, dur = 1.0, linear = false },
    [3] = { start = 0.5, dur = 1.0, linear = false },
    [4] = { start = 1.0, dur = 0.65, linear = true },
    [5] = { start = 0.55, dur = 1.1, linear = false },
    [6] = { start = 0.45, dur = 1.0, linear = false },
    [7] = { start = 0.8, dur = 0.8, linear = false },
    [8] = { start = 0.9, dur = 0.7, linear = false },
    [9] = { start = 0.4, dur = 1.0, linear = false },
    [10] = { start = 0.4, dur = 1.0, linear = false },
}

local LIGHT_SCENES = { [3] = true, [4] = true, [5] = true, [7] = true, [8] = true }

local PERSONAS = {
    { name = "Steady Builder", desc = "Small steps, your own pace.", r = 0xBF, g = 0xF4, b = 0xD4 },
    { name = "Goal Collector", desc = "You make space for plans that matter.", r = 0xFF, g = 0xB4, b = 0x90 },
    { name = "Roundup Ranger", desc = "You give small amounts a place to grow.", r = 0x24, g = 0x1B, b = 0x3C },
    { name = "Patient Planner", desc = "You take your time with the next step.", r = 0xFF, g = 0xF4, b = 0xDD },
}

local STATS = { "totalSaved", "deposits", "goalsCompleted", "roundupsSaved", "activeMonths", "largestGoalAmount", "goalJars" }
local INTEGER_STATS = { deposits = true, goalsCompleted = true, activeMonths = true, goalJars = true }

type Director = {
    vm: ViewModel?,
    nums: { [string]: Property<number> },
    bools: { [string]: Property<boolean> },
    strs: { [string]: Property<string> },
    trigs: { [string]: PropertyTrigger },
    colors: { [string]: Property<Color> },
    size: Vector,
    t: number,
    dwell: number,
    pressT: number,
    pressX: number,
    pressY: number,
    pressing: boolean,
    holding: boolean,
    lastPersona: number,
    chromeT: number,
    pendingNav: number,
    started: boolean,
}

local function num(self: Director, name: string, fallback: number): number
    local p = self.nums[name]
    if p == nil then return fallback end
    local v = p.value
    if v ~= v then return fallback end
    return v
end

local function setNum(self: Director, name: string, v: number)
    local p = self.nums[name]
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function bool(self: Director, name: string, fallback: boolean): boolean
    local p = self.bools[name]
    if p == nil then return fallback end
    return p.value
end

local function setBool(self: Director, name: string, v: boolean)
    local p = self.bools[name]
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function str(self: Director, name: string): string
    local p = self.strs[name]
    if p == nil then return "" end
    return p.value
end

local function setStr(self: Director, name: string, v: string)
    local p = self.strs[name]
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function fire(self: Director, name: string)
    local t = self.trigs[name]
    if t ~= nil then t:fire() end
end

local function clamp01(v: number): number
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

local function easeOutCubic(t: number): number
    local u = 1 - t
    return 1 - u * u * u
end

-- intro (1) and summary (10) are always eligible; the persona scene needs at
-- least one visible statistic so a brand-new user is never handed a persona.
local function visibleList(self: Director): { number }
    local list: { number } = { 1 }
    local anyStat = false
    for k = 2, 8 do
        if bool(self, "showScreen" .. tostring(k), true) then
            anyStat = true
            table.insert(list, k)
        end
    end
    if anyStat and bool(self, "showScreen9", true) and str(self, "personaName") ~= "" then
        table.insert(list, 9)
    end
    table.insert(list, 10)
    return list
end

local function indexOf(list: { number }, v: number): number
    for i, x in ipairs(list) do
        if x == v then return i end
    end
    return 0
end

local function goTo(self: Director, target: number, dir: number)
    local cur = num(self, "currentScreen", 1)
    if target == cur then return end
    setNum(self, "_navDir", dir)
    setNum(self, "currentScreen", target)
    setNum(self, "_count" .. tostring(target), 0)
    setNum(self, "screenProgress", 0)
    self.t = 0
    self.dwell = 0
    if not bool(self, "reducedMotion", false) then
        if dir >= 0 then fire(self, "_handoffFwd") else fire(self, "_handoffBack") end
    end
end

local function step(self: Director, delta: number)
    local list = visibleList(self)
    local cur = num(self, "currentScreen", 1)
    local i = indexOf(list, cur)
    if i == 0 then i = 1 end
    local j = math.clamp(i + delta, 1, #list)
    goTo(self, list[j], if delta >= 0 then 1 else -1)
end

local function replay(self: Director)
    for k = 1, 10 do
        setNum(self, "_count" .. tostring(k), 0)
    end
    setBool(self, "_finished", false)
    local cur = num(self, "currentScreen", 1)
    if cur ~= 1 then
        goTo(self, 1, -1)
    else
        self.t = 0
        self.dwell = 0
    end
end

local function sanitize(self: Director)
    for _, name in ipairs(STATS) do
        local p = self.nums[name]
        if p ~= nil then
            local v = p.value
            local c = v
            if c ~= c or c == math.huge or c == -math.huge or c < 0 then
                c = 0
            end
            if INTEGER_STATS[name] then
                c = math.floor(c + 0.5)
            end
            if name == "activeMonths" and c > 12 then
                c = 12
            end
            if c ~= v then
                p.value = c
            end
        end
    end
end

local function personaSlot(self: Director): number
    local v = num(self, "personaIndex", 0)
    if v ~= math.floor(v) or v < 0 or v > 3 then
        return 0
    end
    return v
end

local function applyPersona(self: Director)
    local slot = personaSlot(self)
    setNum(self, "_personaSlot", slot)
    local raw = num(self, "personaIndex", 0)
    if raw == self.lastPersona then return end
    self.lastPersona = raw
    if not bool(self, "personaAutoMap", true) then return end
    local row = PERSONAS[slot + 1]
    -- one frame, three writes: label, description and colour never disagree
    setStr(self, "personaName", row.name)
    setStr(self, "personaDescription", row.desc)
    local c = self.colors["personaColor"]
    if c ~= nil then
        c.value = Color.rgb(row.r, row.g, row.b)
    end
end

local function inToy(self: Director, p: Vector): boolean
    local s = num(self, "_stageScale", 1)
    local sx = num(self, "_stageX", 0)
    local sy = num(self, "_stageY", 0)
    local x = (p.x - sx) / s
    local y = (p.y - sy) / s
    return x >= TOY.x0 and x <= TOY.x1 and y >= TOY.y0 and y <= TOY.y1
end

local function inStory(self: Director, p: Vector): boolean
    local h = self.size.y
    if p.y < HEADER_H or p.y > h - FOOTER_H then return false end
    if inToy(self, p) then return false end
    return true
end

local function init(self: Director, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then return true end
    self.vm = vm
    local numbers = {
        "currentScreen", "screenProgress", "autoAdvanceSeconds", "personaIndex",
        "_navDir", "_visibleCount", "_visibleIndex", "_personaSlot",
        "_stageX", "_stageY", "_stageScale", "_viewW", "_viewH", "_chromeInset",
    }
    for _, n in ipairs(STATS) do table.insert(numbers, n) end
    for k = 1, 10 do table.insert(numbers, "_count" .. tostring(k)) end
    for _, n in ipairs(numbers) do
        local p = vm:getNumber(n)
        if p ~= nil then self.nums[n] = p end
    end
    local booleans = {
        "autoAdvanceEnabled", "isPaused", "reducedMotion", "isSharing", "appBackgrounded",
        "personaAutoMap", "_frozen", "_holding", "_finished", "_canGoBack", "_canGoNext",
        "_isSummary", "_emptyState", "_personaKnown",
    }
    for k = 1, 10 do table.insert(booleans, "showScreen" .. tostring(k)) end
    for _, n in ipairs(booleans) do
        local p = vm:getBoolean(n)
        if p ~= nil then self.bools[n] = p end
    end
    for _, n in ipairs({ "personaName", "personaDescription", "pauseLabel", "playLabel", "_pauseButtonLabel" }) do
        local p = vm:getString(n)
        if p ~= nil then self.strs[n] = p end
    end
    for _, n in ipairs({ "personaColor", "_chromeColor", "_chromeOnColor" }) do
        local p = vm:getColor(n)
        if p ~= nil then self.colors[n] = p end
    end
    for _, n in ipairs({ "_handoffFwd", "_handoffBack" }) do
        local p = vm:getTrigger(n)
        if p ~= nil then self.trigs[n] = p end
    end
    local function on(name: string, fn: () -> ())
        local p = vm:getTrigger(name)
        if p ~= nil then
            p:addListener(vm, function(_a) fn() end)
        end
    end
    -- buttons, keys and screen-reader actions all arrive as triggers; several in
    -- one frame are coalesced into a single net step so rapid input settles on
    -- the last requested scene without stacking transitions
    on("navNext", function() self.pendingNav += 1 end)
    on("navPrev", function() self.pendingNav -= 1 end)
    on("togglePause", function()
        local p = self.bools["isPaused"]
        if p ~= nil then p.value = not p.value end
    end)
    on("replay", function() replay(self) end)
    self.lastPersona = -999
    return true
end

local function resize(self: Director, size: Vector, scale: number)
    self.size = size
end

local function layoutStage(self: Director)
    local w = self.size.x
    local h = self.size.y
    if w <= 0 or h <= 0 then return end
    local s = math.min(w / DESIGN_W, h / DESIGN_H)
    setNum(self, "_stageScale", s)
    setNum(self, "_stageX", (w - DESIGN_W * s) / 2)
    setNum(self, "_stageY", (h - DESIGN_H * s) / 2)
    setNum(self, "_viewW", w)
    setNum(self, "_viewH", h)
    setNum(self, "_chromeInset", math.max(0, (w - 520) / 2))
end

local CREAM = { 0xFF, 0xF4, 0xDD }
local INK = { 0x24, 0x1B, 0x3C }

local function chrome(self: Director, cur: number, dt: number, rm: boolean)
    local target = if LIGHT_SCENES[cur] then 1 else 0
    local speed = if rm then 100 else 4
    if self.chromeT < target then
        self.chromeT = math.min(target, self.chromeT + dt * speed)
    elseif self.chromeT > target then
        self.chromeT = math.max(target, self.chromeT - dt * speed)
    end
    local t = self.chromeT
    local function mix(a: { number }, b: { number }): Color
        return Color.rgb(
            math.floor(a[1] + (b[1] - a[1]) * t + 0.5),
            math.floor(a[2] + (b[2] - a[2]) * t + 0.5),
            math.floor(a[3] + (b[3] - a[3]) * t + 0.5))
    end
    local c = self.colors["_chromeColor"]
    if c ~= nil then c.value = mix(CREAM, INK) end
    local o = self.colors["_chromeOnColor"]
    if o ~= nil then o.value = mix(INK, CREAM) end
end

local function advance(self: Director, seconds: number): boolean
    if self.vm == nil then return true end
    local dt = math.min(seconds, 0.1)
    sanitize(self)
    applyPersona(self)
    layoutStage(self)

    if self.pendingNav ~= 0 then
        local n = self.pendingNav
        self.pendingNav = 0
        step(self, n)
    end

    local list = visibleList(self)
    local cur = num(self, "currentScreen", 1)
    local idx = indexOf(list, cur)
    if idx == 0 then
        -- invalid or newly hidden scene: settle on the next eligible one
        local target = list[#list]
        for _, v in ipairs(list) do
            if v > cur then target = v; break end
        end
        if cur < 1 or cur ~= math.floor(cur) then target = 1 end
        setNum(self, "_navDir", 1)
        setNum(self, "currentScreen", target)
        cur = target
        idx = indexOf(list, cur)
        self.t = 0
        self.dwell = 0
    end
    if not self.started then
        self.started = true
        setNum(self, "_count" .. tostring(cur), 0)
    end
    setNum(self, "_visibleCount", #list)
    setNum(self, "_visibleIndex", idx)
    setBool(self, "_canGoBack", idx > 1)
    setBool(self, "_canGoNext", idx < #list)
    setBool(self, "_isSummary", cur == 10)
    setBool(self, "_emptyState", #list <= 2)
    setBool(self, "_personaKnown", indexOf(list, 9) > 0)

    local rm = bool(self, "reducedMotion", false)
    local paused = bool(self, "isPaused", false)
    local frozen = paused or self.holding or bool(self, "isSharing", false) or bool(self, "appBackgrounded", false)
    setBool(self, "_frozen", frozen)
    setBool(self, "_holding", self.holding)
    setStr(self, "_pauseButtonLabel", if paused then str(self, "playLabel") else str(self, "pauseLabel"))
    chrome(self, cur, dt, rm)

    -- press-and-hold pauses; the release that ends a hold never navigates
    if self.pressing and not self.holding then
        self.pressT += dt
        if self.pressT >= HOLD_SECONDS then
            self.holding = true
        end
    end

    self.t += dt
    -- count-up playhead for the current scene (local animation state)
    local dir = num(self, "_navDir", 1)
    local w = COUNT[cur] or COUNT[1]
    local start = w.start - (if dir >= 0 then 0 else 0.33)
    local raw = clamp01((self.t - start) / w.dur)
    local c = if rm then 1 elseif w.linear then raw else easeOutCubic(raw)
    setNum(self, "_count" .. tostring(cur), c)

    local settle = if rm then SETTLE_RM else SETTLE
    local autoOn = bool(self, "autoAdvanceEnabled", true)
    local secs = num(self, "autoAdvanceSeconds", 7)
    if secs ~= secs or secs == math.huge then secs = 7 end
    secs = math.max(MIN_DWELL, secs)
    if self.t >= settle and not frozen and autoOn and cur ~= 10 then
        self.dwell += dt
    end
    if cur == 10 then
        setNum(self, "screenProgress", if self.t >= settle then 1 else clamp01(self.t / settle))
    else
        setNum(self, "screenProgress", clamp01(self.dwell / secs))
    end
    if self.dwell >= secs and cur ~= 10 then
        step(self, 1)
    end
    return true
end

local function pointerDown(self: Director, event: PointerEvent)
    if not inStory(self, event.position) then return end
    self.pressing = true
    self.pressT = 0
    self.pressX = event.position.x
    self.pressY = event.position.y
end

local function pointerUp(self: Director, event: PointerEvent)
    if not self.pressing then return end
    self.pressing = false
    if self.holding then
        self.holding = false
        return
    end
    if self.size.x <= 0 then return end
    if self.pressX < self.size.x / 3 then
        self.pendingNav -= 1
    else
        self.pendingNav += 1
    end
end

local function pointerExit(self: Director, event: PointerEvent)
    self.pressing = false
    self.holding = false
end

return function(context: Context): Layout<Director>
    return {
        vm = nil,
        nums = {}, bools = {}, strs = {}, trigs = {}, colors = {},
        size = Vector.xy(0, 0),
        t = 0, dwell = 0, pressT = 0, pressX = 0, pressY = 0,
        pressing = false, holding = false, lastPersona = -999, chromeT = 0,
        pendingNav = 0, started = false,
        init = init, resize = resize, advance = advance,
        pointerDown = pointerDown, pointerUp = pointerUp, pointerExit = pointerExit,
    }
end
