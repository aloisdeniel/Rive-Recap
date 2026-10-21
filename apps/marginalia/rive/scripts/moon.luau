--!strict
-- Marginalia etched moon: a ScriptedDrawable inside the carried moon (Carry
-- artboard), so its keyed pendulum swing, the 4 -> 5 carry and the shrink into
-- the theatre spotlight all still apply. It renders shaders/moon.wgsl - a lit
-- sphere printed as a copperplate engraving - into a small GPU canvas and draws
-- that image centred on the node.
--
-- Cost control: the canvas is only re-rendered while the moon is on screen
-- (scene 4 or 5) and its turn has moved by a visible amount; otherwise the
-- last image is drawn (or nothing, off screen). Reduced motion and pause stop
-- the slow libration. Runtimes without shaders draw a flat vector moon.

type Moon = {
    size: Input<number>,
    screen: Input<number>,
    still: Input<boolean>,
    paused: Input<boolean>,
    pipe: GPUPipeline?,
    ubo: GPUBuffer?,
    group: GPUBindGroup?,
    gc: GPUCanvas?,
    px: number,
    turn: number,
    drawn: number,
    staging: buffer,
    sampler: ImageSampler,
    disc: Path,
    discPaint: Paint,
    rimPaint: Paint,
}

local RES = 3 -- canvas pixels per point
local SPEED = 0.07 -- radians of libration per second

function init(self: Moon, context: Context): boolean
    if self.pipe ~= nil then
        return true
    end
    local r = self.size * 0.5
    self.disc:reset()
    local k = 0.5523
    self.disc:moveTo(Vector.xy(r, 0))
    self.disc:cubicTo(Vector.xy(r, r * k), Vector.xy(r * k, r), Vector.xy(0, r))
    self.disc:cubicTo(Vector.xy(-r * k, r), Vector.xy(-r, r * k), Vector.xy(-r, 0))
    self.disc:cubicTo(Vector.xy(-r, -r * k), Vector.xy(-r * k, -r), Vector.xy(0, -r))
    self.disc:cubicTo(Vector.xy(r * k, -r), Vector.xy(r, -r * k), Vector.xy(r, 0))
    self.disc:close()
    local sh = context:shader('shaders/moon')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    local ubo = GPUBuffer.new({ size = 64, usage = 'uniform', label = 'moon' })
    self.pipe = pipe
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local px = math.ceil(self.size * 1.04 * RES)
    self.px = px
    self.gc = context:gpuCanvas({ width = px, height = px })
    self.drawn = -1
    return true
end

local function onScreen(self: Moon): boolean
    local s = math.floor(self.screen + 0.5)
    return s == 4 or s == 5
end

function advance(self: Moon, seconds: number): boolean
    if onScreen(self) and not self.still and not self.paused then
        self.turn += seconds * SPEED
    end
    return true
end

local function render(self: Moon, gc: GPUCanvas, pipe: GPUPipeline, ubo: GPUBuffer, group: GPUBindGroup)
    local b = self.staging
    local vals = {
        self.turn, 8.0, self.px, 0,
        0.972, 0.945, 0.872, 0, -- paper
        0.30, 0.22, 0.15, 0, -- sepia ink
        0.56, 0.42, 0.20, 0.035, -- gilt outline
    }
    for i, v in vals do
        buffer.writef32(b, (i - 1) * 4, v)
    end
    ubo:write(b)
    local pass = gc:beginRenderPass({
        color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
        label = 'etched moon',
    })
    pass:setPipeline(pipe)
    pass:setBindGroup(0, group)
    pass:draw(6)
    pass:finish()
end

function draw(self: Moon, renderer: Renderer)
    if not onScreen(self) then
        return
    end
    local gc, pipe, ubo, group = self.gc, self.pipe, self.ubo, self.group
    if gc == nil or pipe == nil or ubo == nil or group == nil then
        renderer:drawPath(self.disc, self.discPaint)
        renderer:drawPath(self.disc, self.rimPaint)
        return
    end
    if math.abs(self.turn - self.drawn) > 0.003 or self.drawn < 0 then
        self.drawn = self.turn
        render(self, gc, pipe, ubo, group)
    end
    local half = self.px / RES * 0.5
    renderer:save()
    renderer:transform(Mat2D.withTranslation(-half, -half) * Mat2D.withScale(1 / RES, 1 / RES))
    renderer:drawImage(gc.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Moon>
    return {
        size = 76,
        screen = 0,
        still = false,
        paused = false,
        pipe = nil,
        ubo = nil,
        group = nil,
        gc = nil,
        px = 1,
        turn = 0.6,
        drawn = -1,
        staging = buffer.create(64),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        disc = Path.new(),
        discPaint = Paint.with({ color = Color.rgb(0xF8, 0xF2, 0xE4), style = 'fill' }),
        rimPaint = Paint.with({ color = Color.rgb(0xBD, 0x91, 0x4C), style = 'stroke', thickness = 1.2 }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
