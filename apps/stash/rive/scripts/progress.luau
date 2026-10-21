--!strict
-- Story progress segments, drawn from UserRecap: exactly _visibleCount
-- segments (hidden scenes removed), past ones full, the current one filled by
-- screenProgress. Colour follows _chromeColor so it reads on every backdrop.
type Progress = {
    vm: ViewModel?,
    count: Property<number>?,
    index: Property<number>?,
    progress: Property<number>?,
    color: Property<Color>?,
    size: Vector,
}

local function init(self: Progress, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then return true end
    self.vm = vm
    self.count = vm:getNumber("_visibleCount")
    self.index = vm:getNumber("_visibleIndex")
    self.progress = vm:getNumber("screenProgress")
    self.color = vm:getColor("_chromeColor")
    return true
end

local function resize(self: Progress, size: Vector, scale: number)
    self.size = size
end

local function advance(self: Progress, seconds: number): boolean
    return true
end

local function pill(x: number, y: number, w: number, h: number): Path
    local p = Path.new()
    local r = math.min(h / 2, w / 2)
    if w <= 0 then return p end
    p:moveTo(Vector.xy(x + r, y))
    p:lineTo(Vector.xy(x + w - r, y))
    p:cubicTo(Vector.xy(x + w - r * 0.45, y), Vector.xy(x + w, y + r * 0.55), Vector.xy(x + w, y + r))
    p:cubicTo(Vector.xy(x + w, y + h - r * 0.55), Vector.xy(x + w - r * 0.45, y + h), Vector.xy(x + w - r, y + h))
    p:lineTo(Vector.xy(x + r, y + h))
    p:cubicTo(Vector.xy(x + r * 0.45, y + h), Vector.xy(x, y + h - r * 0.55), Vector.xy(x, y + h - r))
    p:cubicTo(Vector.xy(x, y + r * 0.55), Vector.xy(x + r * 0.45, y), Vector.xy(x + r, y))
    p:close()
    return p
end

local function draw(self: Progress, renderer: Renderer)
    local cp, ip, pp = self.count, self.index, self.progress
    if cp == nil or ip == nil or pp == nil then return end
    local n = math.max(1, math.floor(cp.value + 0.5))
    local idx = math.floor(ip.value + 0.5)
    local prog = math.clamp(pp.value, 0, 1)
    local w = self.size.x
    local h = 6
    local y = (self.size.y - h) / 2
    local gap = 4
    local segW = (w - gap * (n - 1)) / n
    if segW <= 0 then return end
    local base = Color.rgb(0xFF, 0xF4, 0xDD)
    local cc = self.color
    if cc ~= nil then base = cc.value end
    local track = Paint.with({ color = Color.lerp(Color.rgba(0, 0, 0, 0), base, 0.28), style = "fill" })
    local done = Paint.with({ color = base, style = "fill" })
    for i = 1, n do
        local x = (i - 1) * (segW + gap)
        renderer:drawPath(pill(x, y, segW, h), track)
        local f = 0
        if i < idx then f = 1 elseif i == idx then f = prog end
        if f > 0 then
            renderer:drawPath(pill(x, y, math.max(h, segW * f), h), done)
        end
    end
end

return function(context: Context): Layout<Progress>
    return {
        vm = nil, count = nil, index = nil, progress = nil, color = nil,
        size = Vector.xy(0, 0),
        init = init, resize = resize, advance = advance, draw = draw,
    }
end
