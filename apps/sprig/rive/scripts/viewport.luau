--!strict
-- Sprig viewport probe: the responsive layout's only source of truth.
--
-- A ScriptedLayout inside a fill-sized root LayoutComponent, so `resize` receives the artboard's
-- real size whenever the host lays it out (the runtime's layout fit resizes the artboard to the
-- canvas). It publishes into private UserRecap properties:
--
--   _vw, _vh      artboard size in points
--   _dpr          device pixels per point (GPU canvases size themselves with it)
--   _landscape    _vw >= layoutBreakpoint (host-tunable, default 768; non-finite or <= 0 -> 768)
--   _tall         _vh >= 1.1 * _vw (each orientation has a tall and a wide arrangement)
--   _rpt/_rpw/_rlw/_rlt   one-hot arrangement (portrait tall / wide, landscape wide / tall)
--   _l...         every long placement value, computed by the generated scripts/layoutsolve.luau
--
-- Inputs besides the size: currentScreen, layoutBreakpoint and _ch1.._ch10, each scene's copy column
-- height as actually laid out (the column binds its computedHeight back), so placements follow the
-- real, reflowed copy (long names, localized strings) rather than an estimate.
--
-- The markup binds to these (short expressions through native formula converters). A resize, a
-- breakpoint change from the host or a scene change re-solves at once, so crossing the threshold
-- mid-scene re-lays the current scene out on the next frame. Without scripting nothing is written and
-- every value keeps its default: the 390 x 844 design. Draws nothing.

local solver = require('scripts/layoutsolve')

type Probe = {
    vm: ViewModel?,
    pw: Property<number>?,
    ph: Property<number>?,
    pdpr: Property<number>?,
    pland: Property<boolean>?,
    ptall: Property<boolean>?,
    pbreak: Property<number>?,
    pscreen: Property<number>?,
    regs: { Property<number>? },
    ins: { Property<number>? },
    inp: { number },
    outs: { Property<number>? },
    vals: { number },
    w: number,
    h: number,
    dpr: number,
    key: string,
}

local function breakpoint(self: Probe): number
    local p = self.pbreak
    local b = if p ~= nil then p.value else 768
    if b ~= b or b == math.huge or b <= 0 then
        b = 768
    end
    return b
end

local function setNum(p: Property<number>?, v: number)
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function setBool(p: Property<boolean>?, v: boolean)
    if p ~= nil and p.value ~= v then
        p.value = v
    end
end

local function publish(self: Probe)
    local w, h = self.w, self.h
    if w <= 0 or h <= 0 or self.vm == nil then
        return
    end
    local land = w >= breakpoint(self)
    local tall = h >= 1.1 * w
    local ps = self.pscreen
    local cs = if ps ~= nil then ps.value else 1
    local key = string.format('%.2f|%.2f|%.2f|%s|%s|%d', w, h, self.dpr, tostring(land), tostring(tall), cs)
    for _, p in ipairs(self.ins) do
        if p ~= nil then
            key ..= string.format('|%.1f', p.value)
        end
    end
    if key == self.key then
        return
    end
    self.key = key
    setNum(self.pw, w)
    setNum(self.ph, h)
    setNum(self.pdpr, self.dpr)
    local l = if land then 1 else 0
    local t = if tall then 1 else 0
    local r = { (1 - l) * t, (1 - l) * (1 - t), l * (1 - t), l * t }
    for i = 1, 4 do
        setNum(self.regs[i], r[i])
    end
    local inp = self.inp
    inp[1], inp[2], inp[3], inp[4], inp[5], inp[6] = w, h, l, t, self.dpr, cs
    for i, p in ipairs(self.ins) do
        if p ~= nil then
            inp[6 + i] = p.value
        end
    end
    solver.solve(inp, self.vals)
    for i, p in ipairs(self.outs) do
        setNum(p, self.vals[i])
    end
    -- the orientation flags last: state that keys on them sees a fully solved layout
    setBool(self.ptall, tall)
    setBool(self.pland, land)
end

function init(self: Probe, context: Context): boolean
    -- init runs more than once: the view model is absent the first time, and a host that binds its own
    -- UserRecap instance re-inits with it. Always (re)bind to the instance we are given now.
    local vm = context:viewModel()
    if vm == nil then
        return true
    end
    self.vm = vm
    self.key = ''
    self.pw = vm:getNumber('_vw')
    self.ph = vm:getNumber('_vh')
    self.pdpr = vm:getNumber('_dpr')
    self.pland = vm:getBoolean('_landscape')
    self.ptall = vm:getBoolean('_tall')
    self.regs = { vm:getNumber('_rpt'), vm:getNumber('_rpw'), vm:getNumber('_rlw'), vm:getNumber('_rlt') }
    local outs: { Property<number>? } = {}
    for i, n in ipairs(solver.names) do
        outs[i] = vm:getNumber(n)
        self.vals[i] = 0
    end
    self.outs = outs
    local pb = vm:getNumber('layoutBreakpoint')
    self.pbreak = pb
    if pb ~= nil then
        pb:addListener(self, function(s: Probe)
            publish(s)
        end)
    end
    -- measured inputs (copy-column heights written back by the columns): re-solve when they change
    local ins: { Property<number>? } = {}
    local names: { string } = solver.inputs
    for i = 7, #names do
        local p = vm:getNumber(names[i])
        ins[i - 6] = p
        self.inp[i] = if p ~= nil then p.value else 0
        if p ~= nil then
            p:addListener(self, function(s: Probe)
                publish(s)
            end)
        end
    end
    self.ins = ins
    local sc = vm:getNumber('currentScreen')
    self.pscreen = sc
    if sc ~= nil then
        sc:addListener(self, function(s: Probe)
            publish(s)
        end)
    end
    publish(self)
    return true
end

function resize(self: Probe, size: Vector, scale: number)
    self.w = math.floor(size.x * 100 + 0.5) / 100
    self.h = math.floor(size.y * 100 + 0.5) / 100
    self.dpr = if scale > 0 then scale else 1
    publish(self)
end

function advance(self: Probe, seconds: number): boolean
    publish(self)
    return false
end

function draw(self: Probe, renderer: Renderer) end

return function(context: Context): Layout<Probe>
    return {
        vm = nil,
        pw = nil,
        ph = nil,
        pdpr = nil,
        pland = nil,
        ptall = nil,
        pbreak = nil,
        pscreen = nil,
        regs = {},
        ins = {},
        inp = { 0, 0, 0, 0, 1, 1 },
        outs = {},
        vals = {},
        w = 0,
        h = 0,
        dpr = 1,
        key = '',
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
    }
end
