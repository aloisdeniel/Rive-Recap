-- Simmer recap director.
--
-- The one in-file adapter between UserRecap and the scenes. It owns the
-- sequencing state (currentScreen, screenProgress, currentSegment,
-- visibleCount, navDirection, countProgress, motionFrozen) and the derived
-- strings, and turns pointer / keyboard / control requests into navigation.
-- Every value it writes lives in the single bound UserRecap instance; scenes
-- and components only ever read that instance.
--
-- Responsive layout: it is also the one place that knows the artboard's real
-- size (a fill-sized ScriptedLayout receives it in `resize`). It picks the
-- orientation from `layoutBreakpoint` (landscape when the width reaches it),
-- writes the slot values the scenes' bindings read (scripts/stage.luau), eases
-- the pot motif's frame from scene to scene, and hit-tests taps against the
-- real width.

local stage = require('scripts/stage')

type Dir = {
    ctx: Context?,
    vm: ViewModel?,
    ready: boolean,
    visible: { number },
    pos: number,             -- 1-based position of currentScreen in `visible`
    lastScreen: number,
    sinceNav: number,
    dwell: number,
    finishedLatch: boolean,
    lastPersona: number,
    -- pointer
    down: boolean,
    downX: number,
    downY: number,
    held: number,
    holding: boolean,
    pausedBeforeHold: boolean,
    -- share
    sharing: boolean,
    pausedBeforeShare: boolean,
    -- queued requests (set from trigger listeners, consumed in advance)
    qNext: number,
    qPrev: number,
    qPause: number,
    qShare: number,
    qReplay: number,
    -- layout
    width: number,
    pixelRatio: number,
    height: number,
    layoutDirty: boolean,
    lastBreakpoint: number,
    slots: stage.Slots?,
    motifScreen: number,
    mx0: number, my0: number, ms0: number,   -- motif frame: carry start
    mx1: number, my1: number, ms1: number,   -- carry target
    mt: number,                              -- carry clock (s); >= MOTIF_CARRY when settled
}

local MOTIF_CARRY = 0.72 -- the pose carry in tools/main_board.py (720 ms, ease in-out)
local HOLD_SECONDS = 0.35
local SETTLE = 2.1
local SETTLE_RM = 0.3
local COUNT_START = 0.45
local COUNT_DURATION = 1.0

local METRICS: { [number]: string } = {
    [2] = 'mealsCooked',
    [3] = 'recipesTried',
    [4] = 'cuisinesExplored',
    [5] = 'newIngredients',
    [6] = 'repeatRecipeCount',
    [7] = 'sharedMeals',
    [8] = 'cookingDays',
}

local PERSONAS = {
    { name = 'Flavor Explorer', description = 'Always room for a new flavor.', color = Color.rgb(0xFF, 0xED, 0xB0) },
    { name = 'Comfort Cook', description = 'You make familiar things feel special.', color = Color.rgb(0x48, 0x29, 0x3D) },
    { name = 'Batch Wizard', description = 'You turn a little planning into good meals.', color = Color.rgb(0x4D, 0x76, 0x55) },
    { name = 'Weekend Baker', description = 'You make time for something warm from the oven.', color = Color.rgb(0xE4, 0x49, 0x32) },
}

-- ------------------------------------------------------------ model access
local function num(self: Dir, name: string, fallback: number): number
    local vm = self.vm
    if vm == nil then return fallback end
    local p = vm:getNumber(name)
    if p == nil then return fallback end
    return p.value
end

local function setNum(self: Dir, name: string, v: number)
    local vm = self.vm
    if vm == nil then return end
    local p = vm:getNumber(name)
    if p ~= nil and p.value ~= v then p.value = v end
end

local function bool(self: Dir, name: string, fallback: boolean): boolean
    local vm = self.vm
    if vm == nil then return fallback end
    local p = vm:getBoolean(name)
    if p == nil then return fallback end
    return p.value
end

local function setBool(self: Dir, name: string, v: boolean)
    local vm = self.vm
    if vm == nil then return end
    local p = vm:getBoolean(name)
    if p ~= nil and p.value ~= v then p.value = v end
end

local function str(self: Dir, name: string): string
    local vm = self.vm
    if vm == nil then return '' end
    local p = vm:getString(name)
    if p == nil then return '' end
    return p.value
end

local function setStr(self: Dir, name: string, v: string)
    local vm = self.vm
    if vm == nil then return end
    local p = vm:getString(name)
    if p ~= nil and p.value ~= v then p.value = v end
end

local function fire(self: Dir, name: string)
    local vm = self.vm
    if vm == nil then return end
    local t = vm:getTrigger(name)
    if t ~= nil then t:fire() end
end

local function finite(v: number): boolean
    return v == v and v ~= math.huge and v ~= -math.huge
end

local function fill(template: string, key: string, value: string): string
    local safe = string.gsub(value, '%%', '%%%%')
    local out = string.gsub(template, '{' .. key .. '}', safe)
    return out
end

-- ------------------------------------------------------------ derived data
local function sanitize(self: Dir)
    -- adapter rule: negative counts clamp to 0; non-finite values are "unknown" (scene hidden, see eligible)
    for _, name in pairs(METRICS) do
        local v = num(self, name, 0)
        if finite(v) and v < 0 then setNum(self, name, 0) end
    end
end

local function eligible(self: Dir, k: number): boolean
    if k == 1 or k == 10 then return true end          -- intro and summary are always available
    if not bool(self, 'showScreen' .. tostring(k), false) then return false end
    local metric = METRICS[k]
    if metric ~= nil then
        return finite(num(self, metric, 0 / 0))
    end
    return true
end

local function buildVisible(self: Dir): { number }
    local list: { number } = {}
    local anyMetric = false
    for k = 2, 8 do
        if eligible(self, k) then anyMetric = true end
    end
    for k = 1, 10 do
        if k == 9 then
            -- no persona without evidence: hidden when the recap has no eligible stats
            if anyMetric and eligible(self, 9) then table.insert(list, k) end
        elseif eligible(self, k) then
            table.insert(list, k)
        end
    end
    setBool(self, 'isEmptyRecap', not anyMetric)
    return list
end

local function derivePersona(self: Dir)
    local idx = num(self, 'personaIndex', 0)
    if idx == self.lastPersona then return end
    self.lastPersona = idx
    local row = 1
    if finite(idx) and idx >= 0 and idx <= 3 and math.floor(idx) == idx then row = idx + 1 end
    local p = PERSONAS[row]
    if idx ~= row - 1 then
        -- unknown / invalid index: fall back to row 0 and normalise the model so every consumer agrees
        setNum(self, 'personaIndex', row - 1)
        self.lastPersona = row - 1
    end
    local vm = self.vm
    if vm == nil then return end
    -- written together in one advance so label, palette and emblem never disagree on screen
    setStr(self, 'personaName', p.name)
    setStr(self, 'personaDescription', p.description)
    local c = vm:getColor('personaColor')
    if c ~= nil then c.value = p.color end
end

local function deriveStrings(self: Dir)
    local name = str(self, 'userName')
    local greet = str(self, 'greetingTemplate')
    if greet ~= '' then setStr(self, 'greetingLine', fill(greet, 'name', name)) end
    local introT = str(self, 'introHeadlineTemplate')
    if introT ~= '' then
        setStr(self, 'introHeadline', fill(introT, 'year', tostring(math.floor(num(self, 'year', 2026)))))
    end
    local recipe = str(self, 'favoriteRecipeName')
    local s6 = str(self, 'screen6SupportTemplate')
    if s6 ~= '' and recipe ~= '' then setStr(self, 'screen6Support', fill(s6, 'recipe', recipe)) end
    setStr(self, 'summaryNameLine', if bool(self, 'shareIncludeName', false) then name else '')
    setStr(self, 'summaryRecipeLine', if bool(self, 'shareIncludeSensitiveValues', false) then recipe else '')
end

-- ------------------------------------------------------------ layout
-- the pose carry's ease (cubic-bezier 0.65, 0, 0.35, 1), solved for x
local function easeInOut(x: number): number
    if x <= 0 then return 0 end
    if x >= 1 then return 1 end
    local x1, x2, y1, y2 = 0.65, 0.35, 0, 1
    local t = x
    for _ = 1, 8 do
        local cx = 3 * x1 * t * (1 - t) ^ 2 + 3 * x2 * t ^ 2 * (1 - t) + t ^ 3
        local dx = 3 * x1 * (1 - t) ^ 2 + 6 * (x2 - x1) * t * (1 - t) + 3 * (1 - x2) * t ^ 2
        if math.abs(dx) < 1e-6 then break end
        t = math.clamp(t - (cx - x) / dx, 0, 1)
    end
    return 3 * y1 * t * (1 - t) ^ 2 + 3 * y2 * t ^ 2 * (1 - t) + t ^ 3
end

local function writeMotif(self: Dir)
    local k = easeInOut(math.min(self.mt / MOTIF_CARRY, 1))
    setNum(self, 'motifFrameX', self.mx0 + (self.mx1 - self.mx0) * k)
    setNum(self, 'motifFrameY', self.my0 + (self.my1 - self.my0) * k)
    setNum(self, 'motifFrameScale', self.ms0 + (self.ms1 - self.ms0) * k)
end

-- the motif frame follows the current scene's art; a scene change carries it, a resize snaps it
local function aimMotif(self: Dir, carry: boolean)
    local s = self.slots
    if s == nil then return end
    local screen = num(self, 'currentScreen', 1)
    local tx, ty, sc = stage.sceneFrame(s, screen)
    if carry and not bool(self, 'reducedMotion', false) then
        local k = easeInOut(math.min(self.mt / MOTIF_CARRY, 1))
        self.mx0 = self.mx0 + (self.mx1 - self.mx0) * k
        self.my0 = self.my0 + (self.my1 - self.my0) * k
        self.ms0 = self.ms0 + (self.ms1 - self.ms0) * k
        self.mt = 0
    else
        self.mx0, self.my0, self.ms0 = tx, ty, sc
        self.mt = MOTIF_CARRY
    end
    self.mx1, self.my1, self.ms1 = tx, ty, sc
    self.motifScreen = screen
    writeMotif(self)
end

local function applyLayout(self: Dir)
    local bp = num(self, 'layoutBreakpoint', 768)
    if not finite(bp) or bp <= 0 then bp = 768 end
    self.lastBreakpoint = num(self, 'layoutBreakpoint', 768)
    self.layoutDirty = false
    local s = stage.compute(self.width, self.height, bp)
    self.slots = s
    setNum(self, 'stageWidth', s.W)
    setNum(self, 'stageHeight', s.H)
    setBool(self, 'isLandscape', s.landscape)
    setNum(self, 'layoutMargin', s.m)
    setNum(self, 'layoutTop', s.top)
    setNum(self, 'layoutBottom', s.bottom)
    setNum(self, 'layoutControlsY', s.controlsY)
    setNum(self, 'layoutContinueWidth', s.continueW)
    setNum(self, 'layoutCopyScale', s.cs)
    setNum(self, 'layoutCopyWidth', s.cw)
    setNum(self, 'layoutCopyAvail', s.avail)
    setNum(self, 'layoutCopyXa', s.copyXa)
    setNum(self, 'layoutCopyXb', s.copyXb)
    setNum(self, 'layoutArtX0a', s.artX0a)
    setNum(self, 'layoutArtX1a', s.artX1a)
    setNum(self, 'layoutArtX0b', s.artX0b)
    setNum(self, 'layoutArtX1b', s.artX1b)
    setNum(self, 'layoutStack', s.stack)
    setNum(self, 'layoutSide', s.side)
    setNum(self, 'layoutPixelRatio', self.pixelRatio)
    -- a resize (even across the breakpoint mid-scene) keeps the scene and snaps the motif to it
    aimMotif(self, false)
end

-- ------------------------------------------------------------ navigation
local function indexOf(list: { number }, v: number): number
    for i, x in ipairs(list) do
        if x == v then return i end
    end
    return 0
end

local function goTo(self: Dir, pos: number, dir: number, withHandoff: boolean)
    local list = self.visible
    if pos < 1 or pos > #list then return end
    local screen = list[pos]
    self.pos = pos
    self.sinceNav = 0
    self.dwell = 0
    -- order matters: playheads reset before the scene id changes, so no stale digits flash
    setNum(self, 'countProgress', if bool(self, 'reducedMotion', false) then 1 else 0)
    setNum(self, 'screenProgress', 0)
    setNum(self, 'navDirection', dir)
    setNum(self, 'currentSegment', pos - 1)
    setBool(self, 'motionFrozen', false)
    if screen ~= self.lastScreen then
        self.lastScreen = screen
        setNum(self, 'currentScreen', screen)
        if withHandoff then
            fire(self, if dir >= 0 then 'handoffForward' else 'handoffBack')
        end
    end
end

local function nextScreen(self: Dir)
    if self.pos < #self.visible then goTo(self, self.pos + 1, 1, true) end
end

local function prevScreen(self: Dir)
    if self.pos > 1 then goTo(self, self.pos - 1, -1, true) end
end

local function togglePause(self: Dir)
    setBool(self, 'isPaused', not bool(self, 'isPaused', false))
end

local function replay(self: Dir)
    self.finishedLatch = false
    setBool(self, 'recapComplete', false)
    setBool(self, 'isPaused', false)
    if self.sharing then
        self.sharing = false
        setBool(self, 'isSharing', false)
    end
    goTo(self, 1, -1, true)
end

local function share(self: Dir)
    if self.sharing then return end
    self.sharing = true
    self.pausedBeforeShare = bool(self, 'isPaused', false)
    setBool(self, 'isPaused', true)
    setBool(self, 'isSharing', true)
end

local function controlsFor(self: Dir): { number }
    if self.visible[self.pos] == 10 then return { 1, 2, 4, 5 } end
    return { 1, 2, 3 }
end

local function activate(self: Dir, control: number)
    if control == 1 then prevScreen(self)
    elseif control == 2 then togglePause(self)
    elseif control == 4 then share(self)
    elseif control == 5 then replay(self)
    else nextScreen(self) end
end

-- ------------------------------------------------------------ lifecycle
local function hook(self: Dir, vm: ViewModel)
    local function on(name: string, cb: () -> ())
        local t = vm:getTrigger(name)
        if t ~= nil then t:addListener(cb) end
    end
    on('navNextRequest', function() self.qNext += 1 end)
    on('navPrevRequest', function() self.qPrev += 1 end)
    on('pauseToggleRequest', function() self.qPause += 1 end)
    on('shareRequest', function() self.qShare += 1 end)
    on('replayRequest', function() self.qReplay += 1 end)
end

function init(self: Dir, context: Context): boolean
    self.ctx = context
    local vm = context:viewModel()
    if vm ~= nil and self.vm == nil then
        self.vm = vm
        hook(self, vm)
    end
    return true
end

local function boot(self: Dir)
    sanitize(self)
    derivePersona(self)
    deriveStrings(self)
    self.visible = buildVisible(self)
    setNum(self, 'visibleCount', #self.visible)
    local cs = num(self, 'currentScreen', 1)
    local p = indexOf(self.visible, cs)
    if p == 0 then p = 1 end
    self.pos = p
    self.lastScreen = num(self, 'currentScreen', 1)
    goTo(self, p, 1, false)
    self.ready = true
end

function resize(self: Dir, size: Vector, scale: number)
    if size.x > 0 and size.y > 0 and (size.x ~= self.width or size.y ~= self.height) then
        self.width, self.height = size.x, size.y
        self.layoutDirty = true
    end
    -- the presenting density, for the scripts that allocate GPU surfaces from a Node (the cookbook)
    local pr = if scale > 0 then scale else 1
    if pr ~= self.pixelRatio then
        self.pixelRatio = pr
        self.layoutDirty = true
    end
end

function advance(self: Dir, seconds: number): boolean
    if self.vm == nil then
        local ctx = self.ctx
        if ctx ~= nil then
            local vm = ctx:viewModel()
            if vm ~= nil then
                self.vm = vm
                hook(self, vm)
            end
        end
        if self.vm == nil then return true end
    end
    if not self.ready then boot(self) end
    if self.layoutDirty or num(self, 'layoutBreakpoint', 768) ~= self.lastBreakpoint then
        applyLayout(self)
    end

    -- host data may change at any time: keep the derived model consistent
    sanitize(self)
    derivePersona(self)
    deriveStrings(self)
    local list = buildVisible(self)
    local changed = #list ~= #self.visible
    if not changed then
        for i, v in ipairs(list) do
            if self.visible[i] ~= v then changed = true end
        end
    end
    if changed then
        local current = self.visible[self.pos] or 1
        self.visible = list
        setNum(self, 'visibleCount', #list)
        local p = indexOf(list, current)
        if p == 0 then
            -- the scene on screen became ineligible: move forward to the next eligible one
            p = #list
            for i, v in ipairs(list) do
                if v > current then
                    p = i
                    break
                end
            end
            goTo(self, p, 1, true)
        else
            self.pos = p
            setNum(self, 'currentSegment', p - 1)
        end
    end

    -- an external write to currentScreen (deep link / host navigation)
    local cs = num(self, 'currentScreen', 1)
    if cs ~= self.lastScreen then
        local p = indexOf(self.visible, cs)
        self.lastScreen = -1
        if p == 0 then p = math.min(self.pos, #self.visible) end
        goTo(self, p, if p >= self.pos then 1 else -1, true)
    end

    -- queued control requests
    while self.qReplay > 0 do
        self.qReplay -= 1
        replay(self)
    end
    while self.qShare > 0 do
        self.qShare -= 1
        share(self)
    end
    while self.qPause > 0 do
        self.qPause -= 1
        togglePause(self)
    end
    while self.qNext > 0 do
        self.qNext -= 1
        nextScreen(self)
    end
    while self.qPrev > 0 do
        self.qPrev -= 1
        prevScreen(self)
    end

    -- the host closes the share sheet by clearing isSharing: restore the prior pause state
    if self.sharing and not bool(self, 'isSharing', true) then
        self.sharing = false
        setBool(self, 'isPaused', self.pausedBeforeShare)
    end

    -- hold to pause
    if self.down then
        self.held += seconds
        if not self.holding and self.held >= HOLD_SECONDS then
            self.holding = true
            self.pausedBeforeHold = bool(self, 'isPaused', false)
            setBool(self, 'isPaused', true)
        end
    end

    local rm = bool(self, 'reducedMotion', false)
    local paused = bool(self, 'isPaused', false) or self.sharing
    self.sinceNav += seconds
    local settleAt = if rm then SETTLE_RM else SETTLE
    local settled = self.sinceNav >= settleAt

    -- count-up playhead, eased (ease-out cubic) and synchronised with the scene's 200-1200 ms hero window
    local cp = 1
    if not rm then
        local t = math.clamp((self.sinceNav - COUNT_START) / COUNT_DURATION, 0, 1)
        cp = 1 - (1 - t) ^ 3
    end
    setNum(self, 'countProgress', cp)

    local isLast = self.pos >= #self.visible
    if settled then
        if isLast then
            setNum(self, 'screenProgress', 1)
            if not self.finishedLatch then
                self.finishedLatch = true
                setBool(self, 'recapComplete', true)
                fire(self, 'recapFinishedSignal')
            end
        elseif not paused and bool(self, 'autoAdvanceEnabled', true) then
            local secs = num(self, 'autoAdvanceSeconds', 7)
            if not finite(secs) then secs = 7 end
            secs = math.clamp(secs, 3, 60)       -- readable minimum, sane maximum
            self.dwell += seconds
            setNum(self, 'screenProgress', math.clamp(self.dwell / secs, 0, 1))
            if self.dwell >= secs then nextScreen(self) end
        end
    end
    setBool(self, 'motionFrozen', paused and settled)

    -- the motif frame: carry to the new scene's art when the scene changes
    if num(self, 'currentScreen', 1) ~= self.motifScreen then
        aimMotif(self, true)
    elseif self.mt < MOTIF_CARRY then
        self.mt += seconds
        writeMotif(self)
    end
    return true
end

function draw(self: Dir, renderer: Renderer) end

-- ------------------------------------------------------------ input
-- taps count between the progress bar and the controls row, across the real width
local function inContent(self: Dir, event: PointerEvent): boolean
    local y = event.position.y
    local s = self.slots
    local top = if s ~= nil then s.top else 92
    local bottom = if s ~= nil then s.controlsY - 40 else 752
    return y >= top and y <= bottom
end

function pointerDown(self: Dir, event: PointerEvent)
    if not inContent(self, event) then return end
    self.down = true
    self.downX = event.position.x
    self.downY = event.position.y
    self.held = 0
    self.holding = false
    event:hit()
end

function pointerUp(self: Dir, event: PointerEvent)
    if not self.down then return end
    self.down = false
    if self.holding then
        -- releasing a hold resumes; it never also counts as a tap
        self.holding = false
        setBool(self, 'isPaused', self.pausedBeforeHold)
        return
    end
    -- left third goes back, right two-thirds go forward, of the real width
    if self.downX < self.width / 3 then self.qPrev += 1 else self.qNext += 1 end
    event:hit()
end

function pointerExit(self: Dir, event: PointerEvent)
    if self.down and self.holding then
        setBool(self, 'isPaused', self.pausedBeforeHold)
    end
    self.down = false
    self.holding = false
end

local KEY_RIGHT = 262
local KEY_LEFT = 263
local KEY_SPACE = 32
local KEY_ENTER = 257
local KEY_KP_ENTER = 335
local KEY_TAB = 258
local KEY_ESCAPE = 256

function keyboardEvent(self: Dir, event: KeyboardEvent): boolean
    if event.phase ~= 'down' then return false end
    local k = event.key
    if k == KEY_RIGHT then self.qNext += 1
    elseif k == KEY_LEFT then self.qPrev += 1
    elseif k == KEY_SPACE then self.qPause += 1
    elseif k == KEY_TAB then
        local controls = controlsFor(self)
        local cur = num(self, 'focusedControl', 0)
        local i = indexOf(controls, cur)
        if event.shift then i -= 1 else i += 1 end
        if i < 1 then i = #controls end
        if i > #controls then i = 1 end
        setNum(self, 'focusedControl', controls[i])
    elseif k == KEY_ENTER or k == KEY_KP_ENTER then
        activate(self, num(self, 'focusedControl', 0))
    elseif k == KEY_ESCAPE then
        setNum(self, 'focusedControl', 0)
    else
        return false
    end
    return true
end

return function(context: Context): Layout<Dir>
    return {
        ctx = nil, vm = nil, ready = false, visible = {}, pos = 1, lastScreen = 1,
        sinceNav = 0, dwell = 0, finishedLatch = false, lastPersona = -999,
        down = false, downX = 0, downY = 0, held = 0, holding = false, pausedBeforeHold = false,
        sharing = false, pausedBeforeShare = false,
        qNext = 0, qPrev = 0, qPause = 0, qShare = 0, qReplay = 0,
        width = 390, height = 844, pixelRatio = 1, layoutDirty = true, lastBreakpoint = 768, slots = nil, motifScreen = -1,
        mx0 = 0, my0 = 0, ms0 = 1, mx1 = 0, my1 = 0, ms1 = 1, mt = MOTIF_CARRY,
        init = init, resize = resize, advance = advance, draw = draw,
        pointerDown = pointerDown, pointerUp = pointerUp, pointerExit = pointerExit,
        keyboardEvent = keyboardEvent,
    }
end
