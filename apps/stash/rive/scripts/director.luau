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
--   * the responsive layout: orientation from the real artboard width against
--     layoutBreakpoint, then a continuous fit of every scene's copy / art zones,
--     the motif frame, the chrome metrics and the GPU canvas resolution
-- Events (screenChanged, recapFinished, shareTapped) are fired by the state
-- machine and listeners, not here: scripts cannot raise Rive events.

local DESIGN_W = 390
local STAGE_H = 844 -- the stage is always 844 units tall and as wide as the canvas
local COPY_TOP = 64 -- design y of the header's bottom edge (the copy's anchor in a stack)
local HOLD_SECONDS = 0.35
local MIN_DWELL = 3
local SETTLE = 2.5
local SETTLE_RM = 0.4
-- the tap toy rides on the motif machine (motifpose.luau, generated with the
-- poses): its hit region follows the machine and is never smaller than this
local TOY_MIN = 46
local poses = require('motifpose')
local boxes = require('layoutboxes')

-- the responsive layout, recomputed from the real size every frame
type Xf = { x: number, y: number, s: number }
type Lay = {
    w: number, h: number, u: number, vw: number,
    land: boolean, split: boolean, compact: boolean, wide: boolean,
    hdrH: number, ftrH: number, ftrL: number, ftrR: number, btnH: number,
    copy: { [number]: Xf }, art: { [number]: Xf }, ticket: Xf, note: Xf, maxA: number,
}

-- count-up windows (seconds after entry, forward navigation), timed to each
-- scene's illustration: coins landing, tokens snapping, jars arriving. The
-- forward handoff (coin -> spring -> panel) lands the panel ~0.57 s in.
local COUNT: { [number]: { start: number, dur: number, linear: boolean } } = {
    [1] = { start = 0.5, dur = 1.0, linear = false },
    [2] = { start = 1.05, dur = 0.95, linear = true }, -- in step with the coins landing in the jar
    [3] = { start = 0.65, dur = 1.0, linear = false },
    [4] = { start = 1.15, dur = 0.65, linear = true },
    [5] = { start = 0.7, dur = 1.1, linear = false },
    [6] = { start = 0.6, dur = 1.0, linear = false },
    [7] = { start = 0.95, dur = 0.8, linear = false },
    [8] = { start = 1.0, dur = 0.75, linear = false },
    [9] = { start = 0.55, dur = 1.0, linear = false },
    [10] = { start = 0.55, dur = 1.0, linear = false },
}
local BACK_LEAD = 0.47 -- back entrances start their keys 28 frames earlier

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
    toyPress: boolean,
    dpr: number,
    lay: Lay?,
    layW: number,
    layH: number,
    mfScene: number,
    mfT: number,
    mfFrom: Xf,
    mfShown: Xf,
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

-- the toy coin's centre on screen: motif pose (machine space) -> motif frame
-- (stage units) -> real pixels; the hit region is never under TOY_MIN px
local function inToy(self: Director, p: Vector): boolean
    local pose = poses.poses[num(self, "currentScreen", 1)]
    local L = self.lay
    if pose == nil or not pose.on or L == nil then return false end
    local mf = self.mfShown
    local c, sn = math.cos(pose.r), math.sin(pose.r)
    local px = pose.x + pose.s * (c * poses.toy.x - sn * poses.toy.y)
    local py = pose.y + pose.s * (sn * poses.toy.x + c * poses.toy.y)
    local tx = (mf.x + mf.s * px) * L.u
    local ty = (mf.y + mf.s * py) * L.u
    local half = math.max(TOY_MIN, pose.s * poses.toy.size * 1.3 * mf.s * L.u) * 0.5
    return math.abs(p.x - tx) <= half and math.abs(p.y - ty) <= half
end

-- story taps: anywhere but the header, the footer's box and the toy
local function inStory(self: Director, p: Vector): boolean
    local L = self.lay
    if L == nil then return false end
    if p.y < L.hdrH then return false end
    if p.y > L.h - L.ftrH and p.x >= L.ftrL and p.x <= L.w - L.ftrR then return false end
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
        "layoutBreakpoint", "_stageScale", "_viewW", "_viewH", "_vcx", "_rightOff", "_barSX",
        "_mfx", "_mfy", "_mfs", "_hdrH", "_ftrH", "_ftrL", "_ftrR", "_btnH", "_gpuRes", "_gpuResStage",
        "_n10x", "_n10y", "_n10s", "_t7x", "_t7y", "_t7s",
    }
    for k = 1, 10 do
        for _, z in ipairs({ "c", "a" }) do
            for _, a in ipairs({ "x", "y", "s" }) do
                table.insert(numbers, "_" .. z .. tostring(k) .. a)
            end
        end
    end
    for _, n in ipairs(STATS) do table.insert(numbers, n) end
    for k = 1, 10 do table.insert(numbers, "_count" .. tostring(k)) end
    for _, n in ipairs(numbers) do
        local p = vm:getNumber(n)
        if p ~= nil then self.nums[n] = p end
    end
    local booleans = {
        "autoAdvanceEnabled", "isPaused", "reducedMotion", "isSharing", "appBackgrounded",
        "personaAutoMap", "_frozen", "_holding", "_finished", "_canGoBack", "_canGoNext",
        "_isSummary", "_emptyState", "_personaKnown", "_landscape", "_split", "_wideCard",
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
    for _, n in ipairs({ "_handoffFwd", "_handoffBack", "_coinNudge" }) do
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
    self.dpr = if scale > 0 then scale else 1
end

-- ------------------------------------------------------------------ layout
--
-- Orientation is a pure width rule: landscape when the artboard is at least
-- layoutBreakpoint (default 768) points wide. Both layouts then fit continuously:
--   * the stage (scenes, motif, handoff) is 844 units tall and w/u wide, u = h/844,
--     so full-screen transitions keep their timing and always cover the canvas;
--   * every scene has a copy zone and an art zone (design boxes in layoutboxes),
--     each with its own scale, so type stays readable while the art takes the rest;
--   * portrait stacks copy over art (a two-column split once the canvas is wider
--     than tall); landscape is always the two-column split, copy left, art right,
--     with the footer under the copy column.

local CMAX_SPLIT = 1.75
local AMAX_SPLIT = 2.1
local GAP_DESIGN = 18 -- between boxes stacked in a split copy column

local function bw(b: boxes.Box): number return b.x1 - b.x0 end
local function bh(b: boxes.Box): number return b.y1 - b.y0 end

-- a zone transform (design space, where x 195 is the viewport's centre and y is
-- in stage units) that puts design point (dx, dy) on real point (rx, ry) at
-- `s` real pixels per design unit
local function place(L: Lay, dx: number, dy: number, rx: number, ry: number, s: number): Xf
    local z = s / L.u
    return { x = (rx - L.w * 0.5) / L.u + 195 - dx * z, y = ry / L.u - dy * z, s = z }
end

local function computeLayout(self: Director): Lay?
    local w, h = self.size.x, self.size.y
    if w <= 0 or h <= 0 then return nil end
    local bp = num(self, "layoutBreakpoint", 768)
    if bp ~= bp or bp == math.huge or bp <= 0 then bp = 768 end
    local land = w >= bp
    local compact = h < 600
    local u = h / STAGE_H
    local L: Lay = {
        w = w, h = h, u = u, vw = w / u,
        land = land, split = land or w >= h * 0.95, compact = compact, wide = false,
        hdrH = if compact then 52 else 64,
        ftrH = if land then (if compact then 72 else 96) else (if compact then 62 else 104),
        ftrL = 0, ftrR = 0,
        btnH = if compact then 48 else 54,
        copy = {}, art = {}, ticket = { x = 0, y = 0, s = 1 }, note = { x = 0, y = 0, s = 1 }, maxA = 0,
    }
    local m = math.clamp(w * 0.045, 18, 80)
    local gap = math.clamp(w * 0.03, 16, 64)
    local iw = w - 2 * m - gap
    local baseFrac = if land then 0.42 else 0.48
    if land then
        -- the footer sits under the copy column (it has 16 pt of its own padding)
        L.ftrL = m - 16
        L.ftrR = w - (m + iw * baseFrac) - 16
    else
        local inset = math.max(0, (w - 620) / 2)
        L.ftrL = inset
        L.ftrR = inset
    end
    for k = 1, 10 do
        local b = boxes.scenes[k]
        if L.split then
            local colTop = L.hdrH + 6
            local copyBot = h - L.ftrH - (if land then 8 else 6)
            -- copy column: the copy box, then the ticket (7) or the note (10)
            local extra = if k == 7 then b.ticket elseif k == 10 then b.note else nil
            local totW = bw(b.copy)
            local totH = bh(b.copy)
            if extra ~= nil then
                totW = math.max(totW, bw(extra))
                totH += GAP_DESIGN + bh(extra)
            end
            -- a landscape canvas that is about as tall as wide (a tablet held
            -- upright) staggers the columns: copy upper left, art lower right,
            -- each wider than half, instead of two thin side-by-side columns
            local stagger = land and h >= w * 0.9
            local cw, aw, artH, ax, c
            local cx, top
            if stagger then
                cw = iw * 0.68
                aw = iw * 0.76
                local availH = copyBot - colTop
                c = math.max(b.minC, math.min(cw / totW, availH * 0.5 / totH, CMAX_SPLIT))
                cx = m + cw * 0.5
                top = colTop
                artH = availH - totH * c - 24
                ax = w - m - aw
            else
                local frac = baseFrac
                if k == 10 then frac = if land then 0.40 else 0.32 end
                cw = iw * frac
                aw = iw - cw
                artH = (if land then h - m * 0.6 else h - L.ftrH - 6) - colTop
                local colH = copyBot - colTop
                c = math.max(b.minC, math.min(cw / totW, colH / totH, CMAX_SPLIT))
                cx = m + cw * 0.5
                top = colTop + math.max(0, (colH - totH * c) * 0.5)
                ax = m + cw + gap
            end
            local artBox = b.artSplit or b.art
            if k == 10 then
                -- the tall card while its labels stay readable, else the wide one
                local tall = math.min(aw / bw(b.art), artH / bh(b.art), AMAX_SPLIT)
                local wb = b.artWide
                if wb ~= nil and tall < b.minA then
                    local wd = math.min(aw / bw(wb), artH / bh(wb), AMAX_SPLIT)
                    if wd > tall * 1.02 then
                        L.wide = true
                        artBox = wb
                    end
                end
            end
            local a = math.min(aw / bw(artBox), artH / bh(artBox), AMAX_SPLIT)
            local artTop
            if stagger then
                -- share the leftover height around and between the two blocks
                local slack = math.max(0, (copyBot - colTop) - totH * c - 24 - bh(artBox) * a)
                top = colTop + slack * 0.35
                artTop = top + totH * c + 24 + slack * 0.3
            else
                artTop = colTop + (artH - bh(artBox) * a) * 0.5
            end
            L.copy[k] = place(L, (b.copy.x0 + b.copy.x1) * 0.5, b.copy.y0, cx, top, c)
            if extra ~= nil then
                local xf = place(L, (extra.x0 + extra.x1) * 0.5, extra.y0, cx, top + (bh(b.copy) + GAP_DESIGN) * c, c)
                if k == 7 then L.ticket = xf else L.note = xf end
            end
            L.art[k] = place(L, (artBox.x0 + artBox.x1) * 0.5, artBox.y0, ax + aw * 0.5, artTop, a)
            L.maxA = math.max(L.maxA, a)
        else
            -- portrait stack: copy under the header, art in the rest, footer below
            local T = L.hdrH
            local H = h - L.ftrH - T
            local cs = b.stackTop - COPY_TOP
            local as = b.stackBot - b.stackTop
            local c = math.min(w / DESIGN_W, 1.4)
            local a = math.min(w / DESIGN_W, 1.45)
            local need = cs * c + as * a
            if need > H then
                c *= H / need
                a *= H / need
            end
            if c < b.minC then
                c = b.minC
                a = (H - cs * c) / as
            end
            if a < b.minA then
                a = b.minA
                c = math.max(b.minC, (H - as * a) / cs)
            end
            local slack = math.max(0, H - cs * c - as * a)
            local copyTop = T + slack * 0.3
            L.copy[k] = place(L, 195, COPY_TOP, w * 0.5, copyTop, c)
            L.art[k] = place(L, 195, b.stackTop, w * 0.5, copyTop + cs * c + slack * 0.35, a)
            if k == 7 then L.ticket = L.art[k] end
            if k == 10 then L.note = L.art[k] end
            L.maxA = math.max(L.maxA, a)
        end
    end
    return L
end

-- the designer's motif blend: cubic-bezier(0.6, 0, 0.25, 1), as the Motif layer
local function bezier(t: number): number
    local x1, y1, x2, y2 = 0.6, 0.0, 0.25, 1.0
    local s = t
    for _ = 1, 8 do
        local x = 3 * (1 - s) * (1 - s) * s * x1 + 3 * (1 - s) * s * s * x2 + s * s * s - t
        local dx = 3 * (1 - s) * (1 - s) * x1 + 6 * (1 - s) * s * (x2 - x1) + 3 * s * s * (1 - x2)
        if math.abs(dx) < 1e-6 then break end
        s = math.clamp(s - x / dx, 0, 1)
    end
    return 3 * (1 - s) * (1 - s) * s * y1 + 3 * (1 - s) * s * s * y2 + s * s * s
end

local function quant(v: number, lo: number, hi: number): number
    return math.clamp(math.ceil(v * 2 - 0.05) / 2, lo, hi)
end

local function writeXf(self: Director, prefix: string, xf: Xf)
    setNum(self, prefix .. "x", xf.x)
    setNum(self, prefix .. "y", xf.y)
    setNum(self, prefix .. "s", xf.s)
end

local function layoutStage(self: Director, cur: number, dt: number, rm: boolean)
    local L = computeLayout(self)
    if L == nil then return end
    local resized = L.w ~= self.layW or L.h ~= self.layH
    self.layW = L.w
    self.layH = L.h
    self.lay = L
    setBool(self, "_landscape", L.land)
    setBool(self, "_split", L.split)
    setBool(self, "_wideCard", L.wide)
    setNum(self, "_stageScale", L.u)
    setNum(self, "_viewW", L.w)
    setNum(self, "_viewH", L.h)
    setNum(self, "_vcx", L.vw * 0.5)
    setNum(self, "_rightOff", L.vw - DESIGN_W)
    setNum(self, "_barSX", L.vw / DESIGN_W + 0.05)
    setNum(self, "_hdrH", L.hdrH)
    setNum(self, "_ftrH", L.ftrH)
    setNum(self, "_ftrL", L.ftrL)
    setNum(self, "_ftrR", L.ftrR)
    setNum(self, "_btnH", L.btnH)
    for k = 1, 10 do
        writeXf(self, "_c" .. tostring(k), L.copy[k])
        writeXf(self, "_a" .. tostring(k), L.art[k])
    end
    writeXf(self, "_t7", L.ticket)
    writeXf(self, "_n10", L.note)
    -- GPU canvases at the real on-screen scale (x device pixel ratio), never
    -- under the 2x the art was tuned at; stepped by 0.5 so a live resize only
    -- re-allocates them now and then
    setNum(self, "_gpuRes", quant(math.max(2, self.dpr * L.maxA), 2, 4))
    setNum(self, "_gpuResStage", quant(math.max(2, self.dpr * L.u), 2, 4))
    -- the motif frame follows the current scene's art zone, blended over the
    -- Motif layer's own 760 ms pose blend; a resize snaps it
    local a = L.art[cur] or L.art[1]
    local target: Xf = { x = a.x + L.vw * 0.5 - 195, y = a.y, s = a.s }
    if cur ~= self.mfScene then
        self.mfFrom = if self.mfScene == 0 then target else self.mfShown
        self.mfScene = cur
        self.mfT = if rm then 1 else 0
    end
    if resized then self.mfT = 1 end
    self.mfT = math.min(1, self.mfT + dt / 0.76)
    local e = bezier(self.mfT)
    local f = self.mfFrom
    local shown: Xf = { x = f.x + (target.x - f.x) * e, y = f.y + (target.y - f.y) * e, s = f.s + (target.s - f.s) * e }
    self.mfShown = shown
    writeXf(self, "_mf", shown)
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
    layoutStage(self, cur, dt, rm)

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
    local start = w.start - (if dir >= 0 then 0 else BACK_LEAD)
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
    if inToy(self, event.position) then
        self.toyPress = true
        return
    end
    if not inStory(self, event.position) then return end
    self.pressing = true
    self.pressT = 0
    self.pressX = event.position.x
    self.pressY = event.position.y
end

local function pointerUp(self: Director, event: PointerEvent)
    if self.toyPress then
        -- the signature interaction: a distinct hit region that never navigates
        self.toyPress = false
        if inToy(self, event.position) then fire(self, "_coinNudge") end
        return
    end
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
    self.toyPress = false
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
        pendingNav = 0, started = false, toyPress = false,
        dpr = 1, lay = nil, layW = 0, layH = 0, mfScene = 0, mfT = 1,
        mfFrom = { x = 0, y = 0, s = 1 }, mfShown = { x = 0, y = 0, s = 1 },
        init = init, resize = resize, advance = advance,
        pointerDown = pointerDown, pointerUp = pointerUp, pointerExit = pointerExit,
    }
end
