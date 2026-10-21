--!strict
-- Stash arcade screen (scripts/crt.wgsl): CRT bloom, scanlines and glass over
-- scene 6's month windows. A ScriptedDrawable centred on the window board.
--
-- How lit each window is comes from the same UserRecap values the vector
-- windows bind (activeMonths x _count6 against each window's rank), so the glow
-- and the windows can never disagree. `band` (the refresh band's y) is keyed by
-- the scene's idle loop, which rests under pause and reduced motion, so the
-- screen is then perfectly still. The canvas re-renders only when the lit
-- amounts or the band moved. Without GPU scripting nothing is added: the vector
-- windows stand on their own.

type Crt = {
    band: Input<number>,
    strength: Input<number>,
    halfW: Input<number>,
    halfH: Input<number>,
    res: Input<number>,
    glow: Input<Color>,
    vm: ViewModel?,
    months: Property<number>?,
    count: Property<number>?,
    gpu: boolean,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    ext: number,
    lastKey: string,
}

-- the order in which months light (rank of window i), as in the vector board
local RANKS = { 3, 7, 1, 10, 5, 12, 2, 9, 6, 11, 4, 8 }
local UBO_SIZE = 112
local PAD = 28

function init(self: Crt, context: Context): boolean
    if self.gpu then
        return true
    end
    local vm = context:viewModel()
    if vm ~= nil then
        self.vm = vm
        self.months = vm:getNumber('activeMonths')
        self.count = vm:getNumber('_count6')
    end
    local sh = context:shader('scripts/crt')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
        cullMode = 'none',
    })
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'stash crt' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(1, self.res)
    self.k = k
    local pw = math.ceil((self.halfW + PAD) * 2 * k / 8) * 8
    local ph = math.ceil((self.halfH + PAD) * 2 * k / 8) * 8
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    self.gpu = true
    return true
end

local function lit(self: Crt): { number }
    local m = if self.months ~= nil then self.months.value else 0
    local c = if self.count ~= nil then self.count.value else 1
    local out: { number } = {}
    for i = 1, 12 do
        out[i] = math.clamp(m * c - (RANKS[i] - 1), 0, 1)
    end
    return out
end

function draw(self: Crt, renderer: Renderer)
    local canvas = self.canvas
    local ubo, pipe, group = self.ubo, self.pipe, self.group
    if not self.gpu or canvas == nil or ubo == nil or pipe == nil or group == nil then
        return
    end
    local l = lit(self)
    local key = string.format('%.2f|%.3f', self.band, self.strength)
    for i = 1, 12 do
        key ..= string.format('|%.3f', l[i])
    end
    if key ~= self.lastKey then
        self.lastKey = key
        local g = Color.toFloat(self.glow)
        local hw, hh = self.halfW + PAD, self.halfH + PAD
        local vals = {
            hw, hh, self.band, 1,
            l[1], l[2], l[3], l[4],
            l[5], l[6], l[7], l[8],
            l[9], l[10], l[11], l[12],
            g[1], g[2], g[3], self.strength,
            76, 70, 25, 22,
            self.halfW, self.halfH, 30, 3.2,
        }
        local b = self.staging
        for i, v in ipairs(vals) do
            buffer.writef32(b, (i - 1) * 4, v)
        end
        ubo:write(b)
        local pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            label = 'stash crt',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(3)
        pass:finish()
    end
    local k = self.k
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-(self.halfW + PAD), -(self.halfH + PAD)) * Mat2D.withScale(1 / k, 1 / k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Crt>
    return {
        band = -200,
        strength = 1,
        halfW = 165,
        halfH = 118,
        res = 2,
        glow = Color.rgb(255, 180, 144),
        vm = nil,
        months = nil,
        count = nil,
        gpu = false,
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        ext = 0,
        lastKey = '',
        init = init,
        draw = draw,
    }
end
