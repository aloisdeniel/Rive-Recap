--!strict
-- Resize harness for tools/check.py (never shipped: check.py builds it into a throwaway project under
-- build/harness/ next to a copy of scene.rml).
--
-- The headless CLI cannot resize a running scene, so this script instances the SprigRecap artboard,
-- drives it and changes the instance's width / height mid-scene, the way a host's layout fit does
-- when a window or device rotates. It prints one `RESIZE` line per checkpoint with the values
-- check.py compares against static renders at the same sizes.
--
--   t 0.5   Continue -> scene 2, at 1280 x 800 (landscape)
--   t 3.5   resize to 600 x 900 (portrait) mid-scene        -> A (before), B (+3 frames), C (t 5.0)
--   t 5.0   Continue -> scene 3; t 5.25 (mid-transition) resize back to 1280 x 800 -> D (t 7.5)

local solver = require('scripts/layoutsolve')

type H = {
    recap: Input<Artboard<Data.UserRecap>>,
    inst: Artboard<Data.UserRecap>?,
    t: number,
    phase: number,
}

local function report(self: H, label: string, full: boolean)
    local inst = self.inst
    if inst == nil then
        return
    end
    local d = inst.data :: any
    local cs = d.currentScreen.value
    local parts: { string } = {
        'RESIZE', label,
        string.format('cs=%d', cs),
        string.format('land=%s', tostring(d._landscape.value)),
        string.format('vw=%.1f', d._vw.value),
        string.format('vh=%.1f', d._vh.value),
        string.format('progress=%.4f', d.screenProgress.value),
    }
    -- the placement the bind applied must equal the solved value (no stale layout after the resize)
    local k = math.floor(cs + 0.5)
    local n = inst:node(string.format('S%d art place', k))
    local want = d[string.format('_lS%dArtPlaceX', k)]
    if n ~= nil and want ~= nil then
        table.insert(parts, string.format('artx=%.2f', n.x))
        table.insert(parts, string.format('artx_solved=%.2f', want.value))
    end
    local c = inst:node(string.format('S%d content', k))
    if c ~= nil then
        table.insert(parts, string.format('content_scale=%.4f', c.scaleX))
    end
    if full then
        local names: { string } = solver.names
        for _, name in ipairs(names) do
            local p = d[name]
            if p ~= nil then
                table.insert(parts, name .. '=' .. string.format('%.3f', p.value :: number))
            end
        end
    end
    print(table.concat(parts, ' '))
end

local function resize(self: H, w: number, h: number)
    local inst = self.inst
    if inst ~= nil then
        inst.width = w
        inst.height = h
    end
end

local function next(self: H)
    local inst = self.inst
    if inst == nil then
        return
    end
    local d = inst.data :: any
    d._navDir.value = 1
    d._navNext:fire()
end

function init(self: H, context: Context): boolean
    -- the harness artboard is bound to the Sample instance of UserRecap; the recap instance shares it
    local vm = context:viewModel()
    if self.inst ~= nil or vm == nil then
        return true
    end
    local inst = self.recap:instance(vm)
    local d = inst.data :: any
    d.autoAdvanceEnabled.value = false
    inst.width = 1280
    inst.height = 800
    inst:advance(0)
    self.inst = inst
    return true
end

function advance(self: H, seconds: number): boolean
    local inst = self.inst
    if inst == nil then
        return true
    end
    self.t += seconds
    inst:advance(seconds)
    local t = self.t
    if self.phase == 0 and t >= 0.5 then
        next(self)
        self.phase = 1
    elseif self.phase == 1 and t >= 3.5 then
        report(self, 'A', false)
        resize(self, 600, 900)
        self.phase = 2
        self.t = 3.5
    elseif self.phase == 2 and t >= 3.5 + 3 / 60 then
        report(self, 'B', false)
        self.phase = 3
    elseif self.phase == 3 and t >= 5.0 then
        report(self, 'C', true)
        next(self)
        self.phase = 4
    elseif self.phase == 4 and t >= 5.25 then
        report(self, 'M', false)
        resize(self, 1280, 800)
        self.phase = 5
    elseif self.phase == 5 and t >= 7.5 then
        report(self, 'D', true)
        self.phase = 6
    end
    return true
end

function draw(self: H, renderer: Renderer)
    local inst = self.inst
    if inst ~= nil then
        inst:draw(renderer)
    end
end

return function(): Node<H>
    return {
        recap = late(),
        inst = nil,
        t = 0,
        phase = 0,
        init = init,
        advance = advance,
        draw = draw,
    }
end
