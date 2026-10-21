--!strict
-- Crux recap director: the in-file host adapter + story sequencer.
--
-- Owns (writes): currentScreen, screenProgress, navDirection, visibleScreenCount,
-- visibleScreenPosition, progressValue, sceneSettled, isEmptyRecap, personaSlot,
-- *Display strings, yearDisplay, pauseButtonLabel, screenAnnouncement and - when
-- personaAdapterEnabled - personaName / personaDescription / personaColor.
-- Reads everything else from the single UserRecap instance bound to the artboard.
-- It never invents user data: numbers are only sanitised (negative / non-finite -> 0)
-- and formatted.

type Director = {
    size: Vector,
    n: { [string]: Property<number> },
    s: { [string]: Property<string> },
    b: { [string]: Property<boolean> },
    c: Property<Color>?,
    t: { [string]: PropertyTrigger },
    ready: boolean,
    dwellT: number,
    enterClock: number,
    holdDown: boolean,
    holdTime: number,
    holdEngaged: boolean,
    holdPrevPaused: boolean,
    moved: boolean,
    ignore: boolean,
    downX: number,
    downY: number,
    finished: boolean,
    sharing: boolean,
    sharePrevPaused: boolean,
    lastPersona: number,
    pending: { number },
}

local STAGE_W = 390
local STAGE_H = 844
local STAGE_ALIGN_Y = -0.8 -- must match the Stage NestedArtboardLeaf alignmentY
local TOP_BAR = 64
local BOTTOM_BAR = 104
local HOLD_HOME_X = 115
local HOLD_HOME_Y = 605
local HOLD_SECONDS = 0.32
local SETTLE = 1.75
local SETTLE_REDUCED = 0.35
local MIN_DWELL = 3
local MAX_DWELL = 60

local NUMBERS = {
    'year', 'sessions', 'sends', 'attempts', 'techniqueSessions', 'longestSessionMinutes',
    'activeWeeks', 'climbingPartners', 'personaIndex', 'autoAdvanceSeconds', 'currentScreen',
    'screenProgress', 'personaSlot', 'visibleScreenCount', 'visibleScreenPosition', 'progressValue',
    'navDirection', 'enteredScreen', 'heroProgress',
}
local STRINGS = {
    'locale', 'personaName', 'personaDescription', 'pauseLabel', 'playLabel', 'pauseButtonLabel',
    'sessionsDisplay', 'sendsDisplay', 'attemptsDisplay', 'techniqueSessionsDisplay',
    'longestSessionMinutesDisplay', 'activeWeeksDisplay', 'climbingPartnersDisplay', 'yearDisplay',
    'screenAnnouncement', 'introHeadline', 'introSupport', 'summaryHeadline', 'summarySupport',
    'emptyHeadline', 'emptySupport', 'personaLabel', 'userName', 'periodLabel',
    'screen2Headline', 'screen2Support', 'screen2Unit', 'screen3Headline', 'screen3Support', 'screen3Unit',
    'screen4Headline', 'screen4Support', 'screen4Unit', 'screen5Headline', 'screen5Support', 'screen5Unit',
    'screen6Headline', 'screen6Support', 'screen6Unit', 'screen7Headline', 'screen7Support', 'screen7Unit',
    'screen8Headline', 'screen8Support', 'screen8Unit',
}
local BOOLS = {
    'autoAdvanceEnabled', 'isPaused', 'reducedMotion', 'sceneSettled', 'isEmptyRecap', 'holdGrabbed',
    'personaAdapterEnabled', 'isSharing', 'showScreen1', 'showScreen2', 'showScreen3', 'showScreen4',
    'showScreen5', 'showScreen6', 'showScreen7', 'showScreen8', 'showScreen9', 'showScreen10',
}

-- metric scenes: screen -> raw number property, display property
local METRICS: { [number]: { string } } = {
    [2] = { 'sessions', 'sessionsDisplay' },
    [3] = { 'sends', 'sendsDisplay' },
    [4] = { 'attempts', 'attemptsDisplay' },
    [5] = { 'techniqueSessions', 'techniqueSessionsDisplay' },
    [6] = { 'longestSessionMinutes', 'longestSessionMinutesDisplay' },
    [7] = { 'activeWeeks', 'activeWeeksDisplay' },
    [8] = { 'climbingPartners', 'climbingPartnersDisplay' },
}

-- persona rows (index -> name, line, accent)
local PERSONAS = {
    { 'Route Reader', 'You see the way through.', 0x20, 0x22, 0x1F },
    { 'Power Mover', 'You bring energy to the next move.', 0xDC, 0xFF, 0x3F },
    { 'Balance Seeker', 'You find strength in a thoughtful shift.', 0x38, 0x5D, 0xF4 },
    { 'Persistent Solver', 'You keep returning to the puzzle.', 0xF1, 0xEE, 0xE7 },
}

-- ------------------------------------------------------------------ helpers
local function num(self: Director, k: string): number
    local p = self.n[k]
    if p then
        return p.value
    end
    return 0
end

local function setNum(self: Director, k: string, v: number)
    local p = self.n[k]
    if p and p.value ~= v then
        p.value = v
    end
end

local function str(self: Director, k: string): string
    local p = self.s[k]
    if p then
        return p.value
    end
    return ''
end

local function setStr(self: Director, k: string, v: string)
    local p = self.s[k]
    if p and p.value ~= v then
        p.value = v
    end
end

local function bool(self: Director, k: string): boolean
    local p = self.b[k]
    if p then
        return p.value
    end
    return false
end

local function setBool(self: Director, k: string, v: boolean)
    local p = self.b[k]
    if p and p.value ~= v then
        p.value = v
    end
end

local function fire(self: Director, k: string)
    local t = self.t[k]
    if t then
        t:fire()
    end
end

local function finite(v: number): boolean
    return v == v and v ~= math.huge and v ~= -math.huge
end

-- Locale-aware integer grouping (CLDR-style separators for common locales).
local function groupSep(locale: string): (string, number)
    local lang = string.lower(string.sub(locale, 1, 2))
    local region = string.upper(string.sub(locale, 4, 5))
    if lang == 'de' and region == 'CH' then
        return '\u{2019}', 4
    end
    if lang == 'de' or lang == 'it' or lang == 'nl' or lang == 'pt' or lang == 'da' or lang == 'id'
        or lang == 'tr' or lang == 'el' or lang == 'ro' or lang == 'hr' or lang == 'sl' or lang == 'sr' then
        return '.', 4
    end
    if lang == 'es' then
        return '.', 5 -- Spanish only groups from five digits
    end
    if lang == 'pl' then
        return '\u{00A0}', 5
    end
    if lang == 'fr' or lang == 'nb' or lang == 'no' or lang == 'sv' or lang == 'fi' or lang == 'cs'
        or lang == 'sk' or lang == 'ru' or lang == 'uk' or lang == 'hu' or lang == 'bg' or lang == 'et'
        or lang == 'lv' or lang == 'lt' then
        return '\u{00A0}', 4
    end
    return ',', 4
end

local function fmtInt(v: number, locale: string): string
    if not finite(v) or v < 0 then
        v = 0
    end
    local n = math.floor(v + 0.5)
    local digits = string.format('%d', n)
    local sep, minDigits = groupSep(locale)
    if #digits < minDigits then
        return digits
    end
    local out = ''
    local count = 0
    for i = #digits, 1, -1 do
        out = string.sub(digits, i, i) .. out
        count += 1
        if count % 3 == 0 and i > 1 then
            out = sep .. out
        end
    end
    return out
end

local function visible(self: Director, k: number): boolean
    if k == 1 or k == 10 then
        return true -- intro and summary are always eligible (safe path)
    end
    return bool(self, 'showScreen' .. tostring(k))
end

local function findFrom(self: Director, from: number, dir: number): number
    local k = from + dir
    while k >= 1 and k <= 10 do
        if visible(self, k) then
            return k
        end
        k += dir
    end
    return 0
end

local function navigate(self: Director, dir: number)
    local cur = num(self, 'currentScreen')
    local target = findFrom(self, cur, dir)
    if target == 0 then
        return
    end
    setNum(self, 'navDirection', dir)
    setNum(self, 'currentScreen', target)
    self.dwellT = 0
    self.enterClock = 0
    setNum(self, 'screenProgress', 0)
    setBool(self, 'sceneSettled', false)
    fire(self, 'screenSignal')
end

local function replay(self: Director)
    self.finished = false
    self.dwellT = 0
    self.enterClock = 0
    setNum(self, 'navDirection', 1)
    if num(self, 'currentScreen') ~= 1 then
        setNum(self, 'currentScreen', 1)
        setBool(self, 'sceneSettled', false)
        fire(self, 'screenSignal')
    end
end

local function applyPersona(self: Director, force: boolean)
    local idx = num(self, 'personaIndex')
    local slot = 0
    if finite(idx) and idx == math.floor(idx) and idx >= 0 and idx <= 3 then
        slot = idx
    end
    if slot ~= num(self, 'personaSlot') then
        setNum(self, 'personaSlot', slot)
    end
    if (force or idx ~= self.lastPersona) and bool(self, 'personaAdapterEnabled') then
        local row = PERSONAS[slot + 1]
        -- written together in one frame so label, palette and emblem never disagree
        setStr(self, 'personaName', row[1] :: string)
        setStr(self, 'personaDescription', row[2] :: string)
        if self.c then
            (self.c :: Property<Color>).value = Color.rgb(row[3] :: number, row[4] :: number, row[5] :: number)
        end
    end
    self.lastPersona = idx
end

local function sanitize(self: Director)
    for _, k in ipairs({ 'sessions', 'sends', 'attempts', 'techniqueSessions', 'longestSessionMinutes',
        'activeWeeks', 'climbingPartners' }) do
        local v = num(self, k)
        if not finite(v) or v < 0 then
            setNum(self, k, 0)
        end
    end
end

local function stageToArtboard(self: Director, x: number, y: number): (number, number, number)
    local w = self.size.x
    local h = self.size.y
    local s = math.max(w / STAGE_W, h / STAGE_H)
    local ox = (w - STAGE_W * s) * 0.5
    local oy = (h - STAGE_H * s) * (STAGE_ALIGN_Y + 1) * 0.5
    return ox + x * s, oy + y * s, s
end

local function excluded(self: Director, x: number, y: number): boolean
    if y < TOP_BAR or y > self.size.y - BOTTOM_BAR then
        return true -- chrome: buttons handle themselves
    end
    if bool(self, 'holdGrabbed') then
        return true
    end
    if num(self, 'currentScreen') == 1 then
        local hx, hy, s = stageToArtboard(self, HOLD_HOME_X, HOLD_HOME_Y)
        local dx = x - hx
        local dy = y - hy
        if dx * dx + dy * dy < (80 * s) * (80 * s) then
            return true -- the draggable hold is a distinct, non-navigating hit region
        end
    end
    return false
end

local function announcement(self: Director, cur: number): string
    if cur == 1 then
        return str(self, 'introHeadline') .. '. ' .. str(self, 'introSupport') .. ' ' .. str(self, 'periodLabel')
    end
    local m = METRICS[cur]
    if m then
        local raw = num(self, m[1])
        local exact = fmtInt(raw, str(self, 'locale'))
        local p = 'screen' .. tostring(cur)
        return exact .. ' ' .. str(self, p .. 'Unit') .. '. ' .. str(self, p .. 'Headline') .. ' ' .. str(self, p .. 'Support')
    end
    if cur == 9 then
        return str(self, 'personaLabel') .. ': ' .. str(self, 'personaName') .. '. ' .. str(self, 'personaDescription')
    end
    if bool(self, 'isEmptyRecap') then
        return str(self, 'emptyHeadline') .. ' ' .. str(self, 'emptySupport')
    end
    local loc = str(self, 'locale')
    local parts = { str(self, 'summaryHeadline') }
    for k = 2, 6 do
        local mm = METRICS[k]
        table.insert(parts, fmtInt(num(self, mm[1]), loc) .. ' ' .. str(self, 'screen' .. tostring(k) .. 'Unit'))
    end
    table.insert(parts, str(self, 'personaName'))
    return table.concat(parts, '. ')
end

-- ------------------------------------------------------------------ lifecycle
function init(self: Director, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true -- init runs twice; the view model arrives on the second call
    end
    for _, k in ipairs(NUMBERS) do
        local p = vm:getNumber(k)
        if p then
            self.n[k] = p
        end
    end
    for _, k in ipairs(STRINGS) do
        local p = vm:getString(k)
        if p then
            self.s[k] = p
        end
    end
    for _, k in ipairs(BOOLS) do
        local p = vm:getBoolean(k)
        if p then
            self.b[k] = p
        end
    end
    self.c = vm:getColor('personaColor')
    for _, k in ipairs({ 'navNext', 'navPrev', 'togglePause', 'replay', 'shareRequested',
        'shareDismissed', 'screenSignal', 'finishSignal' }) do
        local t = vm:getTrigger(k)
        if t then
            self.t[k] = t
        end
    end
    -- Commands are queued and applied in advance() so a burst of taps settles cleanly.
    local function on(k: string, code: number)
        local t = self.t[k]
        if t then
            t:addListener(function()
                table.insert(self.pending, code)
            end)
        end
    end
    on('navNext', 1)
    on('navPrev', 2)
    on('togglePause', 3)
    on('replay', 4)
    on('shareRequested', 5)
    on('shareDismissed', 6)
    self.ready = true
    -- validate the starting scene (hidden or out-of-range -> safe intro/summary path)
    local cur = num(self, 'currentScreen')
    if not finite(cur) or cur < 1 or cur > 10 or cur ~= math.floor(cur) then
        setNum(self, 'currentScreen', 1)
    elseif not visible(self, cur) then
        local f = findFrom(self, cur, 1)
        setNum(self, 'currentScreen', if f ~= 0 then f else 10)
    end
    applyPersona(self, true)
    return true
end

function resize(self: Director, size: Vector, scale: number)
    self.size = size
end

local function run(self: Director, code: number)
    if code == 1 then
        navigate(self, 1)
    elseif code == 2 then
        navigate(self, -1)
    elseif code == 3 then
        setBool(self, 'isPaused', not bool(self, 'isPaused'))
    elseif code == 4 then
        replay(self)
    elseif code == 5 then
        if not self.sharing then
            self.sharing = true
            self.sharePrevPaused = bool(self, 'isPaused')
            setBool(self, 'isPaused', true)
            setBool(self, 'isSharing', true)
        end
    elseif code == 6 then
        if self.sharing then
            self.sharing = false
            setBool(self, 'isPaused', self.sharePrevPaused)
            setBool(self, 'isSharing', false)
        end
    end
end

function advance(self: Director, seconds: number): boolean
    if not self.ready then
        return true
    end
    local dt = math.min(seconds, 0.1)
    -- 1. commands
    if #self.pending > 0 then
        local q = self.pending
        self.pending = {}
        for _, code in ipairs(q) do
            run(self, code)
        end
    end
    sanitize(self)
    applyPersona(self, false)
    local loc = str(self, 'locale')
    local rm = bool(self, 'reducedMotion')

    -- 2. visible-scene list
    local count = 0
    local pos = 1
    local cur = num(self, 'currentScreen')
    if not visible(self, cur) then
        local f = findFrom(self, cur, 1)
        if f == 0 then
            f = 10
        end
        setNum(self, 'currentScreen', f)
        cur = f
        fire(self, 'screenSignal')
    end
    local any = false
    for k = 1, 10 do
        if visible(self, k) then
            count += 1
            if k == cur then
                pos = count
            end
            if k > 1 and k < 10 then
                any = true
            end
        end
    end
    setNum(self, 'visibleScreenCount', count)
    setNum(self, 'visibleScreenPosition', pos)
    setBool(self, 'isEmptyRecap', not any)

    -- 3. formatted display strings; the active metric counts up with heroProgress
    local entered = num(self, 'enteredScreen')
    local hp = math.clamp(num(self, 'heroProgress'), 0, 1)
    for k, m in pairs(METRICS) do
        local raw = num(self, m[1])
        if entered == k and k == cur and hp < 1 then
            setStr(self, m[2], fmtInt(math.floor(raw * hp + 0.5), loc))
        else
            setStr(self, m[2], fmtInt(raw, loc))
        end
    end
    setStr(self, 'yearDisplay', string.format('%d', math.floor(num(self, 'year'))))
    setStr(self, 'pauseButtonLabel', if bool(self, 'isPaused') then str(self, 'playLabel') else str(self, 'pauseLabel'))

    -- 4. hold-to-pause (a hold never becomes a tap)
    if self.holdDown and not self.holdEngaged then
        self.holdTime += dt
        if self.holdTime >= HOLD_SECONDS and not self.moved then
            self.holdEngaged = true
            self.holdPrevPaused = bool(self, 'isPaused')
            setBool(self, 'isPaused', true)
        end
    end

    -- 5. settle + dwell timer (starts only once the entrance has settled)
    if entered == cur then
        self.enterClock += dt
    end
    local settled = entered == cur and self.enterClock >= (if rm then SETTLE_REDUCED else SETTLE)
    setBool(self, 'sceneSettled', settled)
    local progress = 0
    if cur == 10 then
        if settled then
            progress = 1
            if not self.finished then
                self.finished = true -- recapFinished fires once per playthrough
                fire(self, 'finishSignal')
            end
        end
    elseif settled then
        local secs = num(self, 'autoAdvanceSeconds')
        if not finite(secs) or secs <= 0 then
            secs = 7
        end
        local dwell = math.clamp(secs, MIN_DWELL, MAX_DWELL)
        if bool(self, 'autoAdvanceEnabled') and not bool(self, 'isPaused') and not self.sharing then
            self.dwellT += dt
        end
        progress = math.clamp(self.dwellT / dwell, 0, 1)
        if progress >= 1 then
            navigate(self, 1)
            progress = 0
        end
    end
    if num(self, 'currentScreen') == cur then
        setNum(self, 'screenProgress', progress)
        setNum(self, 'progressValue', (pos - 1) + progress)
    else
        setNum(self, 'progressValue', pos)
    end
    setStr(self, 'screenAnnouncement', announcement(self, num(self, 'currentScreen')))
    return true
end

function draw(self: Director, renderer: Renderer) end

-- ------------------------------------------------------------------ pointer: tap zones + hold
function pointerDown(self: Director, event: PointerEvent)
    local p = event.position
    if excluded(self, p.x, p.y) then
        self.ignore = true
        return
    end
    self.ignore = false
    self.holdDown = true
    self.holdTime = 0
    self.moved = false
    self.downX = p.x
    self.downY = p.y
end

function pointerMove(self: Director, event: PointerEvent)
    if self.holdDown then
        local dx = event.position.x - self.downX
        local dy = event.position.y - self.downY
        if dx * dx + dy * dy > 14 * 14 then
            self.moved = true
        end
    end
end

local function endHold(self: Director): boolean
    local wasHold = self.holdEngaged
    if self.holdEngaged then
        self.holdEngaged = false
        setBool(self, 'isPaused', self.holdPrevPaused)
    end
    self.holdDown = false
    return wasHold
end

function pointerUp(self: Director, event: PointerEvent)
    if self.ignore then
        self.ignore = false
        return
    end
    if not self.holdDown then
        return
    end
    if endHold(self) or self.moved then
        return
    end
    -- left third goes back, right two-thirds advance
    if event.position.x < self.size.x / 3 then
        table.insert(self.pending, 2)
    else
        table.insert(self.pending, 1)
    end
end

function pointerExit(self: Director, event: PointerEvent)
    if self.holdDown then
        endHold(self)
    end
end

return function(context: Context): Layout<Director>
    return {
        size = Vector.xy(390, 844),
        n = {},
        s = {},
        b = {},
        c = nil,
        t = {},
        ready = false,
        dwellT = 0,
        enterClock = 0,
        holdDown = false,
        holdTime = 0,
        holdEngaged = false,
        holdPrevPaused = false,
        moved = false,
        ignore = false,
        downX = 0,
        downY = 0,
        finished = false,
        sharing = false,
        sharePrevPaused = false,
        lastPersona = -999,
        pending = {},
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
        pointerDown = pointerDown,
        pointerMove = pointerMove,
        pointerUp = pointerUp,
        pointerExit = pointerExit,
    }
end
