-- Marginalia recap director.
--
-- One ScriptedLayout that fills the root artboard. It is the in-file "host
-- adapter" and sequencer brain; the state machines own every visual state.
--
--   * reads the single UserRecap instance (context:viewModel())
--   * derives the eligible-scene list from showScreen1..10 (1 and 10 forced)
--   * owns currentScreen / screenProgress / _navDir and the dwell timer
--   * turns taps (left third = back, right two-thirds = next), hold-to-pause,
--     control-button triggers and keyboard triggers into navigation
--   * formats every stat into its *Text string once (locale separators) and
--     counts the current scene's hero value from zero
--   * maps personaIndex -> personaName / personaDescription / personaColor
--   * fires the internal triggers the Recap state machine turns into the
--     public events screenChanged / shareTapped / recapFinished
--   (the page turn itself is drawn by scripts/pagestage.luau)
--   * draws the progress segments (one per eligible scene)
--   * writes pointer parallax for the paper theater

type NumP = Property<number>
type BoolP = Property<boolean>
type StrP = Property<string>

type Director = {
    ready: boolean,
    size: Vector,
    nums: { [string]: NumP },
    bools: { [string]: BoolP },
    strs: { [string]: StrP },
    trigs: { [string]: PropertyTrigger },
    personaColor: Property<Color>?,
    cur: number,
    sinceEntry: number,
    dwell: number,
    countForward: boolean,
    finishedLatch: boolean,
    lastPersona: number,
    lastText: { [string]: string },
    downAt: Vector?,
    downTime: number,
    clock: number,
    dragging: boolean,
    holding: boolean,
    pX: number,
    pY: number,
    tX: number,
    tY: number,
    motionPaused: boolean,
    sharingWas: boolean,
    pausedBeforeShare: boolean,
    pending: { string },
    paths: { Path },
    track: Paint,
    ink: Paint,
}

local HEADER_H = 76
local CONTROLS_H = 104
local PROGRESS_Y = 60
local SETTLE = 1.8
local SETTLE_RM = 0.25
local COUNT_DELAY = 0.2
local COUNT_DUR = 1.0
local HOLD_S = 0.32
local MOVE_PX = 10

local STAT = {
    [2] = { raw = 'booksFinished', text = 'booksFinishedText' },
    [3] = { raw = 'pagesRead', text = 'pagesReadText' },
    [4] = { raw = 'readingHours', text = 'readingHoursText' },
    [5] = { raw = 'genresExplored', text = 'genresExploredText' },
    [6] = { raw = 'passagesSaved', text = 'passagesSavedText' },
    [7] = { raw = 'longestStreakDays', text = 'longestStreakDaysText' },
    [8] = { raw = 'bookClubChats', text = 'bookClubChatsText' },
}

local PERSONAS = {
    { name = 'World Wanderer', desc = 'At home in another world.', r = 0x25, g = 0x2E, b = 0x3D },
    { name = 'Deep Diver', desc = 'You follow a question all the way down.', r = 0x78, g = 0x2D, b = 0x3D },
    { name = 'Night Reader', desc = 'You make room for stories after dark.', r = 0xBD, g = 0x91, b = 0x4C },
    { name = 'Curious Collector', desc = 'Your next book can come from anywhere.', r = 0xF1, g = 0xE8, b = 0xD5 },
}

local NUM_NAMES = {
    'currentScreen', 'screenProgress', 'autoAdvanceSeconds', 'year', 'personaIndex',
    'booksFinished', 'pagesRead', 'readingHours', 'genresExplored', 'passagesSaved',
    'longestStreakDays', 'bookClubChats', 'visibleScreenCount', 'visibleScreenIndex',
    '_navDir', '_parallaxX', '_parallaxY', '_personaRow',
}
local BOOL_NAMES = {
    'showScreen1', 'showScreen2', 'showScreen3', 'showScreen4', 'showScreen5',
    'showScreen6', 'showScreen7', 'showScreen8', 'showScreen9', 'showScreen10',
    'autoAdvanceEnabled', 'isPaused', 'reducedMotion', 'isSharing', 'isBackgrounded',
    '_motionPaused', '_hasStats',
}
local STR_NAMES = {
    'locale', 'personaName', 'personaDescription', 'yearText',
    'booksFinishedText', 'pagesReadText', 'readingHoursText', 'genresExploredText',
    'passagesSavedText', 'longestStreakDaysText', 'bookClubChatsText', 'a11yAnnouncement',
    'introHeadline', 'introSupport', 'periodLabel', 'personaLabel', 'summaryHeadline',
    'summarySupport', 'emptyHeadline', 'emptySupport',
    'screen2Unit', 'screen2Headline', 'screen2Support', 'screen3Unit', 'screen3Headline', 'screen3Support',
    'screen4Unit', 'screen4Headline', 'screen4Support', 'screen5Unit', 'screen5Headline', 'screen5Support',
    'screen6Unit', 'screen6Headline', 'screen6Support', 'screen7Unit', 'screen7Headline', 'screen7Support',
    'screen8Unit', 'screen8Headline', 'screen8Support',
    'continueLabel', 'shareLabel', 'pauseLabel', 'playLabel', 'replayLabel',
    'primaryA11yLabel', 'secondaryA11yLabel',
}
local TRIG_NAMES = {
    '_cmdPrev', '_cmdNext', '_cmdPrimary', '_cmdSecondary', '_cmdPause',
    '_evtScreen', '_evtShare', '_evtFinished',
}

-- ------------------------------------------------------------ helpers
local function num(self: Director, k: string, fallback: number): number
    local p = self.nums[k]
    if p == nil then
        return fallback
    end
    local v = p.value
    if v ~= v or v == math.huge or v == -math.huge then
        return fallback
    end
    return v
end

local function setNum(self: Director, k: string, v: number)
    local p = self.nums[k]
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function flag(self: Director, k: string): boolean
    local p = self.bools[k]
    return p ~= nil and p.value
end

local function setFlag(self: Director, k: string, v: boolean)
    local p = self.bools[k]
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function setStr(self: Director, k: string, v: string)
    local p = self.strs[k]
    if p ~= nil and self.lastText[k] ~= v then
        self.lastText[k] = v
        p.value = v
    end
end

local function fire(self: Director, k: string)
    local t = self.trigs[k]
    if t ~= nil then
        t:fire()
    end
end

-- Locale-aware integer grouping. Invalid, negative and non-finite input
-- clamps to 0 (the adapter rule from the brief); counts are integers.
local function separatorFor(locale: string): string
    local lang = string.lower(string.sub(locale, 1, 2))
    if lang == 'de' or lang == 'es' or lang == 'it' or lang == 'nl' or lang == 'pt'
        or lang == 'da' or lang == 'id' or lang == 'tr' then
        return '.'
    elseif lang == 'fr' or lang == 'sv' or lang == 'nb' or lang == 'fi' or lang == 'pl'
        or lang == 'cs' or lang == 'ru' or lang == 'uk' then
        return '\u{00A0}'
    end
    if string.lower(locale) == 'de-ch' then
        return '\u{2019}'
    end
    return ','
end

local function formatInt(v: number, locale: string): string
    if v ~= v or v == math.huge or v == -math.huge or v < 0 then
        v = 0
    end
    local n = math.floor(v + 0.5)
    local digits = tostring(n)
    if string.find(digits, 'e') then
        digits = string.format('%.0f', n)
    end
    local sep = separatorFor(locale)
    local out = ''
    local len = #digits
    for i = 1, len do
        out ..= string.sub(digits, i, i)
        local rest = len - i
        if rest > 0 and rest % 3 == 0 then
            out ..= sep
        end
    end
    return out
end

local function easeOutCubic(t: number): number
    local u = 1 - t
    return 1 - u * u * u
end

-- ------------------------------------------------------------ eligibility
local function hasStats(self: Director): boolean
    for k = 2, 8 do
        if flag(self, 'showScreen' .. k) then
            return true
        end
    end
    return false
end

local function eligible(self: Director, k: number): boolean
    if k == 1 or k == 10 then
        return true -- intro and summary are always available
    end
    if k == 9 then
        -- no persona without evidence
        return flag(self, 'showScreen9') and hasStats(self)
    end
    return flag(self, 'showScreen' .. k)
end

local function visibleList(self: Director): { number }
    local list = {}
    for k = 1, 10 do
        if eligible(self, k) then
            table.insert(list, k)
        end
    end
    return list
end

local function nextOf(self: Director, cur: number, dir: number): number
    local k = cur + dir
    while k >= 1 and k <= 10 do
        if eligible(self, k) then
            return k
        end
        k += dir
    end
    return cur
end

-- ------------------------------------------------------------ persona
local function applyPersona(self: Director)
    local idx = math.floor(num(self, 'personaIndex', 0))
    local row = idx
    if row < 0 or row > 3 then
        row = 0 -- unknown indices fall back to row 0
    end
    if row == self.lastPersona then
        return
    end
    self.lastPersona = row
    local p = PERSONAS[row + 1]
    -- Written together in one frame so label, palette and emblem agree. The
    -- English row text is only a default: strings a localizing host wrote
    -- (anything that is not empty and not one of the defaults) are kept.
    local function isDefault(v: string, field: string): boolean
        if v == '' then
            return true
        end
        for _, q in PERSONAS do
            if (field == 'name' and q.name == v) or (field == 'desc' and q.desc == v) then
                return true
            end
        end
        return false
    end
    local np = self.strs['personaName']
    local dp = self.strs['personaDescription']
    if np ~= nil and isDefault(np.value, 'name') then
        np.value = p.name
    end
    if dp ~= nil and isDefault(dp.value, 'desc') then
        dp.value = p.desc
    end
    local c = self.personaColor
    if c ~= nil then
        c.value = Color.rgba(p.r, p.g, p.b, 255)
    end
    setNum(self, '_personaRow', row)
end

-- ------------------------------------------------------------ navigation
local function go(self: Director, k: number, dir: number)
    if k == self.cur or k < 1 or k > 10 then
        return
    end
    local rm = flag(self, 'reducedMotion')
    setNum(self, '_navDir', dir)
    self.cur = k
    setNum(self, 'currentScreen', k)
    setNum(self, 'screenProgress', 0)
    self.sinceEntry = 0
    self.dwell = 0
    self.countForward = dir > 0 and not rm
    -- (the Page Stage script watches currentScreen + _navDir and turns the page)
    fire(self, '_evtScreen')
end

local function resumeIfUserPaused(self: Director)
    -- Explicit navigation resumes playback (Stories convention): the scene
    -- state machine is frozen while paused, so a change made while paused
    -- would otherwise stay invisible.
    setFlag(self, 'isPaused', false)
end

local function navNext(self: Director)
    if self.cur == 10 then
        return -- summary stays visible; no endless loop
    end
    resumeIfUserPaused(self)
    go(self, nextOf(self, self.cur, 1), 1)
end

local function navPrev(self: Director)
    resumeIfUserPaused(self)
    go(self, nextOf(self, self.cur, -1), -1)
end

local function replay(self: Director)
    self.finishedLatch = false
    setFlag(self, 'isSharing', false)
    self.sharingWas = false
    setFlag(self, 'isPaused', false)
    go(self, 1, -1)
end

local function share(self: Director)
    if self.cur ~= 10 then
        return
    end
    self.pausedBeforeShare = flag(self, 'isPaused')
    setFlag(self, 'isSharing', true)
    fire(self, '_evtShare')
end

local function togglePause(self: Director)
    setFlag(self, 'isPaused', not flag(self, 'isPaused'))
end

local function primary(self: Director)
    if self.cur == 10 then
        share(self)
    else
        navNext(self)
    end
end

local function secondary(self: Director)
    if self.cur == 10 then
        replay(self)
    else
        togglePause(self)
    end
end

-- ------------------------------------------------------------ text
local function refreshTexts(self: Director)
    local lp = self.strs['locale']
    local locale = if lp ~= nil then lp.value else 'en-GB'
    local rm = flag(self, 'reducedMotion')
    for k = 2, 8 do
        local s = STAT[k]
        local raw = num(self, s.raw, 0)
        local shown = raw
        if k == self.cur and self.countForward and not rm then
            local t = math.clamp((self.sinceEntry - COUNT_DELAY) / COUNT_DUR, 0, 1)
            local clean = if raw ~= raw or raw < 0 then 0 else raw
            shown = math.floor(clean * easeOutCubic(t) + 0.5)
        end
        setStr(self, s.text, formatInt(shown, locale))
    end
    local y = math.floor(num(self, 'year', 2026))
    setStr(self, 'yearText', tostring(y))
end

local function str(self: Director, k: string): string
    local p = self.strs[k]
    return if p ~= nil then p.value else ''
end

-- One plain-language sentence per scene, assembled only from localized model
-- strings and the formatted values, for hosts to announce / expose.
local function announce(self: Director)
    local k = self.cur
    local out = ''
    if k == 1 then
        out = str(self, 'introHeadline') .. '. ' .. str(self, 'introSupport') .. ' ' .. str(self, 'periodLabel')
    elseif k >= 2 and k <= 8 then
        local s = STAT[k]
        local lp = self.strs['locale']
        local v = formatInt(num(self, s.raw, 0), if lp ~= nil then lp.value else 'en-GB')
        local p = 'screen' .. k
        out = v .. ' ' .. str(self, p .. 'Unit') .. '. ' .. str(self, p .. 'Headline') .. ' ' .. str(self, p .. 'Support')
    elseif k == 9 then
        out = str(self, 'personaLabel') .. ': ' .. str(self, 'personaName') .. '. ' .. str(self, 'personaDescription')
    else
        if hasStats(self) then
            out = str(self, 'summaryHeadline') .. ' ' .. str(self, 'summarySupport')
        else
            out = str(self, 'emptyHeadline') .. ' ' .. str(self, 'emptySupport')
        end
    end
    setStr(self, 'a11yAnnouncement', out)
    if k == 10 then
        setStr(self, 'primaryA11yLabel', str(self, 'shareLabel'))
        setStr(self, 'secondaryA11yLabel', str(self, 'replayLabel'))
    else
        setStr(self, 'primaryA11yLabel', str(self, 'continueLabel'))
        setStr(self, 'secondaryA11yLabel', str(self, if flag(self, 'isPaused') then 'playLabel' else 'pauseLabel'))
    end
end

-- ------------------------------------------------------------ lifecycle
function init(self: Director, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then
        return true
    end
    for _, n in NUM_NAMES do
        local p = vm:getNumber(n)
        if p ~= nil then
            self.nums[n] = p
        end
    end
    for _, n in BOOL_NAMES do
        local p = vm:getBoolean(n)
        if p ~= nil then
            self.bools[n] = p
        end
    end
    for _, n in STR_NAMES do
        local p = vm:getString(n)
        if p ~= nil then
            self.strs[n] = p
        end
    end
    for _, n in TRIG_NAMES do
        local p = vm:getTrigger(n)
        if p ~= nil then
            self.trigs[n] = p
        end
    end
    self.personaColor = vm:getColor('personaColor')

    -- Control and keyboard listeners in the state machine fire these
    -- triggers; queue them and apply in advance() so a burst of taps in one
    -- frame resolves deterministically.
    local function queue(name: string)
        local t = self.trigs[name]
        if t ~= nil then
            t:addListener(function()
                table.insert(self.pending, name)
            end)
        end
    end
    queue('_cmdPrev')
    queue('_cmdNext')
    queue('_cmdPrimary')
    queue('_cmdSecondary')
    queue('_cmdPause')

    -- Validate the host's starting scene into a safe eligible one.
    local start = math.floor(num(self, 'currentScreen', 1))
    if start < 1 or start > 10 or not eligible(self, start) then
        start = 1
    end
    self.cur = start
    setNum(self, 'currentScreen', start)
    setNum(self, '_navDir', 1)
    self.countForward = true
    self.lastPersona = -1
    applyPersona(self)
    refreshTexts(self)
    self.ready = true
    return true
end

function resize(self: Director, size: Vector, scale: number)
    self.size = size
end

local function inStage(self: Director, p: Vector): boolean
    return p.y > HEADER_H and p.y < self.size.y - CONTROLS_H
end

local function inTapZone(self: Director, p: Vector): boolean
    return p.y >= 0 and p.y < self.size.y - CONTROLS_H and p.x >= 0 and p.x <= self.size.x
end

function pointerDown(self: Director, event: PointerEvent)
    local p = event.position
    if not inTapZone(self, p) then
        return
    end
    self.downAt = p
    self.downTime = self.clock
    self.dragging = false
    self.holding = false
end

function pointerMove(self: Director, event: PointerEvent)
    local p = event.position
    local down = self.downAt
    if down ~= nil and not self.dragging then
        local dx = p.x - down.x
        local dy = p.y - down.y
        if dx * dx + dy * dy > MOVE_PX * MOVE_PX then
            -- a drag is parallax, never navigation
            self.dragging = true
        end
    end
    -- Parallax only reads the paper-theater band (between the header and the
    -- controls); outside it the theater eases home.
    if inStage(self, p) and self.size.x > 0 then
        self.tX = math.clamp((p.x / self.size.x) * 2 - 1, -1, 1)
        local stageH = self.size.y - HEADER_H - CONTROLS_H
        self.tY = math.clamp(((p.y - HEADER_H) / stageH) * 2 - 1, -1, 1)
    else
        self.tX = 0
        self.tY = 0
    end
end

function pointerUp(self: Director, event: PointerEvent)
    local down = self.downAt
    self.downAt = nil
    if down == nil then
        return
    end
    if self.holding then
        self.holding = false -- releasing a hold never also taps
        return
    end
    if self.dragging then
        self.dragging = false
        return
    end
    if self.size.x <= 0 then
        return
    end
    if down.x < self.size.x / 3 then
        table.insert(self.pending, '_cmdPrev')
    else
        table.insert(self.pending, '_cmdNext')
    end
end

function pointerExit(self: Director, event: PointerEvent)
    self.downAt = nil
    self.holding = false
    self.dragging = false
    self.tX = 0
    self.tY = 0
end

function advance(self: Director, seconds: number): boolean
    self.clock += seconds
    if not self.ready then
        return true
    end

    -- external writes to currentScreen (host jump) are validated and honoured
    local ext = math.floor(num(self, 'currentScreen', self.cur))
    if ext ~= self.cur then
        local target = if ext >= 1 and ext <= 10 and eligible(self, ext) then ext else 1
        local c = self.cur
        self.cur = -1
        go(self, target, if target >= c then 1 else -1)
        if target == c then
            self.cur = c
            setNum(self, 'currentScreen', c)
        end
    end
    -- the current scene may have become ineligible at runtime
    if not eligible(self, self.cur) then
        go(self, nextOf(self, self.cur, 1), 1)
    end

    -- commands
    if #self.pending > 0 then
        local cmds = self.pending
        self.pending = {}
        for _, c in cmds do
            if c == '_cmdNext' then
                navNext(self)
            elseif c == '_cmdPrev' then
                navPrev(self)
            elseif c == '_cmdPrimary' then
                primary(self)
            elseif c == '_cmdSecondary' then
                secondary(self)
            elseif c == '_cmdPause' then
                if self.cur ~= 10 then
                    togglePause(self)
                end
            end
        end
    end

    -- hold to pause
    if self.downAt ~= nil and not self.dragging and not self.holding
        and self.clock - self.downTime >= HOLD_S then
        self.holding = true
    end

    -- sharing: restore the previous pause state when the host clears it
    local sharing = flag(self, 'isSharing')
    if self.sharingWas and not sharing then
        setFlag(self, 'isPaused', self.pausedBeforeShare)
    end
    self.sharingWas = sharing

    local paused = flag(self, 'isPaused') or self.holding or sharing
        or flag(self, 'isBackgrounded')
    if paused ~= self.motionPaused then
        self.motionPaused = paused
        setFlag(self, '_motionPaused', paused)
    end

    setFlag(self, '_hasStats', hasStats(self))
    applyPersona(self)

    local rm = flag(self, 'reducedMotion')
    local settle = if rm then SETTLE_RM else SETTLE
    if not paused then
        self.sinceEntry += seconds
        if self.sinceEntry > settle then
            self.dwell += seconds
        end
    end

    local dwellDur = num(self, 'autoAdvanceSeconds', 7)
    dwellDur = math.clamp(dwellDur, 3, 120) -- readable minimum, sane maximum
    if self.cur == 10 then
        setNum(self, 'screenProgress', math.clamp(self.sinceEntry / settle, 0, 1))
        if self.sinceEntry >= settle and not self.finishedLatch then
            self.finishedLatch = true
            fire(self, '_evtFinished')
        end
    else
        setNum(self, 'screenProgress', math.clamp(self.dwell / dwellDur, 0, 1))
        if not paused and flag(self, 'autoAdvanceEnabled') and self.dwell >= dwellDur then
            go(self, nextOf(self, self.cur, 1), 1)
        end
    end

    -- visible-list bookkeeping for the host / screen readers
    local list = visibleList(self)
    setNum(self, 'visibleScreenCount', #list)
    for i, k in list do
        if k == self.cur then
            setNum(self, 'visibleScreenIndex', i)
        end
    end

    refreshTexts(self)
    announce(self)

    -- parallax (frozen while paused, zero under reduced motion)
    if not paused then
        local kk = 1 - math.exp(-6 * seconds)
        local tx = if rm then 0 else self.tX
        local ty = if rm then 0 else self.tY
        self.pX += (tx - self.pX) * kk
        self.pY += (ty - self.pY) * kk
        setNum(self, '_parallaxX', math.floor(self.pX * 1000 + 0.5) / 1000)
        setNum(self, '_parallaxY', math.floor(self.pY * 1000 + 0.5) / 1000)
    end
    return true
end

function draw(self: Director, renderer: Renderer)
    if not self.ready or self.size.x <= 0 then
        return
    end
    local list = visibleList(self)
    local n = #list
    if n == 0 then
        return
    end
    local left = 24
    local width = self.size.x - 48
    local gap = 5
    local segW = (width - gap * (n - 1)) / n
    local prog = num(self, 'screenProgress', 0)
    local curPos = 0
    for i, k in list do
        if k == self.cur then
            curPos = i
        end
    end
    for i = 1, n do
        local x = left + (i - 1) * (segW + gap)
        local tp = self.paths[i * 2 - 1]
        if tp == nil then
            tp = Path.new()
            self.paths[i * 2 - 1] = tp
        end
        tp:reset()
        tp:moveTo(Vector.xy(x, PROGRESS_Y))
        tp:lineTo(Vector.xy(x + segW, PROGRESS_Y))
        tp:lineTo(Vector.xy(x + segW, PROGRESS_Y + 2.5))
        tp:lineTo(Vector.xy(x, PROGRESS_Y + 2.5))
        tp:close()
        renderer:drawPath(tp, self.track)
        local f = if i < curPos then 1 elseif i == curPos then prog else 0
        if f > 0 then
            local fp = self.paths[i * 2]
            if fp == nil then
                fp = Path.new()
                self.paths[i * 2] = fp
            end
            fp:reset()
            local fx = x + segW * f
            fp:moveTo(Vector.xy(x, PROGRESS_Y))
            fp:lineTo(Vector.xy(fx, PROGRESS_Y))
            fp:lineTo(Vector.xy(fx, PROGRESS_Y + 2.5))
            fp:lineTo(Vector.xy(x, PROGRESS_Y + 2.5))
            fp:close()
            renderer:drawPath(fp, self.ink)
        end
    end
end

return function(context: Context): Layout<Director>
    return {
        ready = false,
        size = Vector.xy(0, 0),
        nums = {},
        bools = {},
        strs = {},
        trigs = {},
        personaColor = nil,
        cur = 1,
        sinceEntry = 0,
        dwell = 0,
        countForward = true,
        finishedLatch = false,
        lastPersona = -1,
        lastText = {},
        downAt = nil,
        downTime = 0,
        clock = 0,
        dragging = false,
        holding = false,
        pX = 0,
        pY = 0,
        tX = 0,
        tY = 0,
        motionPaused = false,
        sharingWas = false,
        pausedBeforeShare = false,
        pending = {},
        paths = {},
        track = Paint.with({ color = Color.rgba(0x25, 0x2E, 0x3D, 46), style = 'fill' }),
        ink = Paint.with({ color = Color.rgba(0x78, 0x2D, 0x3D, 255), style = 'fill' }),
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
