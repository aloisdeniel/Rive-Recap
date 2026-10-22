--!strict
-- Kiln 3D effects (scripts/fx3d.wgsl): small ray-marched scenes in a GPU canvas.
--
--   mode 1  the glaze drip of scene 4 (bead at the jug's lip, fall, splash, ripples)
--   mode 2  orbit rings with droplets (scene 9: anticipation rings, Glaze Alchemist orbit)
--   mode 3  the gift box of scene 8 (walls fold up, tissue blooms, ribbon, bow)
--
-- The frame (x0, y0, w, h) is the canvas rectangle in the node's local units. `side`
-- splits a scene around a piece another drawable draws (-1 behind it, 1 in front of
-- it): the same scene is hosted twice, one instance on either side of that piece.
-- Animated values are ScriptInputs keyed by the state machine; the drip's cycle and
-- the orbit's travel run on an internal clock that stops while `still` (paused, held
-- or reduced motion), so a paused frame freezes in place and reduced motion is calm.
-- `live` = 0 skips all work while the scene is hidden. `zoom` (the art stage scale) and
-- `dpr` (device pixel ratio) keep the canvas at the piece's real on-screen resolution.
-- Without GPU scripting a flat vector version of each scene is drawn instead.

type Fx = {
    mode: Input<number>,
    side: Input<number>,
    live: Input<number>,
    still: Input<boolean>,
    x0: Input<number>,
    y0: Input<number>,
    w: Input<number>,
    h: Input<number>,
    res: Input<number>,
    zoom: Input<number>,
    dpr: Input<number>,
    tilt: Input<number>,
    opacity: Input<number>,
    -- mode 1
    lipX: Input<number>,
    lipY: Input<number>,
    hitX: Input<number>,
    hitY: Input<number>,
    size: Input<number>,
    amount: Input<number>,
    period: Input<number>,
    surf: Input<number>,
    -- mode 2
    radius: Input<number>,
    tube: Input<number>,
    ring: Input<number>,
    drops: Input<number>,
    incline: Input<number>,
    count: Input<number>,
    dropSize: Input<number>,
    spin: Input<number>,
    precess: Input<number>,
    roll: Input<number>,
    spread: Input<number>,
    gloss: Input<number>,
    -- mode 3
    fold: Input<number>,
    tissue: Input<number>,
    ribbon: Input<number>,
    bow: Input<number>,
    boxB: Input<number>,
    boxH: Input<number>,
    cupR: Input<number>,
    cupH: Input<number>,
    col0: Input<Color>,
    col1: Input<Color>,
    col2: Input<Color>,
    -- runtime
    gpu: boolean,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    k: number,
    t: number,
    ang: number,
    lastKey: string,
    paintA: Paint,
    paintB: Paint,
    paintS: Paint,
}

local UBO_SIZE = 160
local TAU = math.pi * 2

local function pixelsPerPoint(self: Fx): number
    local z = math.max(0.25, self.zoom)
    local k = math.clamp(z * math.max(math.max(1, self.dpr), self.res), 1, 4)
    return math.floor(k * 4 + 0.5) / 4
end

local function canvasSize(self: Fx, k: number): (number, number)
    return math.max(8, math.ceil(self.w * k)), math.max(8, math.ceil(self.h * k))
end

function init(self: Fx, context: Context): boolean
    if self.gpu then
        return true
    end
    local sh = context:shader('scripts/fx3d')
    if sh == nil then
        return true -- no GPU scripting: the vector fallback draws
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = UBO_SIZE, usage = 'uniform', label = 'kiln fx3d' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = pixelsPerPoint(self)
    self.k = k
    local pw, ph = canvasSize(self, k)
    self.canvas = context:gpuCanvas({ width = pw, height = ph })
    self.gpu = true
    return true
end

function advance(self: Fx, seconds: number): boolean
    if self.live < 0.5 then
        return true
    end
    local canvas = self.canvas
    if self.gpu and canvas ~= nil then
        local k = pixelsPerPoint(self)
        if k ~= self.k then
            self.k = k
            local pw, ph = canvasSize(self, k)
            canvas:resize(pw, ph)
            self.lastKey = ''
        end
    end
    local dt = math.min(seconds, 0.1)
    if self.mode < 1.5 then
        -- the drip starts its cycle (a fresh bead) whenever it is switched on
        if self.amount < 0.01 then
            self.t = 0
        elseif not self.still then
            self.t += dt
        end
    elseif self.mode < 2.5 then
        if not self.still then
            self.ang = (self.ang + dt * self.spin * TAU) % TAU
        end
    end
    return true
end

local function phase(self: Fx): number
    local p = math.max(0.2, self.period)
    return (self.t / p) % 1
end

local function split(self: Fx): number
    if self.mode > 2.5 then
        return self.cupH * 0.5 * math.sin(self.tilt)
    end
    return 0
end

local function writeUniforms(self: Fx)
    local c0 = Color.toFloat(self.col0)
    local c1 = Color.toFloat(self.col1)
    local c2 = Color.toFloat(self.col2)
    local p0 = { 0, 0, 0, 0 }
    local p1 = { 0, 0, 0, 0 }
    local p2 = { 0, 0, 0, 0 }
    local m = self.mode
    if m < 1.5 then
        p0 = { self.lipX, self.lipY, self.hitX, self.hitY }
        p1 = { phase(self), self.amount, self.size, 0 }
        p2 = { self.surf, 0, 0, 0 }
    elseif m < 2.5 then
        p0 = { self.radius, self.tube, self.ring, self.drops }
        p1 = { self.incline, self.ang, self.count, self.dropSize }
        p2 = { self.precess, self.roll, self.spread, 0 }
    else
        p0 = { self.fold, self.tissue, self.ribbon, self.bow }
        p1 = { self.boxB, self.boxH, self.cupR, self.cupH }
    end
    local vals = {
        self.x0, self.y0, self.w, self.h,
        m, self.side, split(self), 1 / self.k,
        self.tilt, self.opacity, 0, 0,
        p0[1], p0[2], p0[3], p0[4],
        p1[1], p1[2], p1[3], p1[4],
        p2[1], p2[2], p2[3], p2[4],
        c0[1], c0[2], c0[3], c0[4],
        c1[1], c1[2], c1[3], c1[4],
        self.gloss, c2[2], c2[3], c2[4],
        0, 0, 0, 0,
    }
    if m > 2.5 then
        vals[33] = c2[1]
    end
    local b = self.staging
    for i, v in ipairs(vals) do
        buffer.writef32(b, (i - 1) * 4, v)
    end
end

local function stateKey(self: Fx): string
    local m = self.mode
    local a, b, c, d = 0, 0, 0, 0
    if m < 1.5 then
        a, b, c, d = phase(self), self.amount, self.size, self.lipX + self.lipY * 3 + self.hitX * 7 + self.hitY * 11
    elseif m < 2.5 then
        a, b, c, d = self.ang, self.radius + self.tube * 7, self.ring + self.drops * 3, self.incline + self.precess * 3
            + self.roll * 7
    else
        a, b, c, d = self.fold, self.tissue, self.ribbon, self.bow
    end
    return string.format('%.4f|%.4f|%.4f|%.4f|%.3f|%.3f|%d|%d|%d|%.3f', a, b, c, d, self.opacity, self.k,
        self.col0, self.col1, self.col2, self.tilt)
end

-- ------------------------------------------------------------------ vector fallback

local KAPPA = 0.5523

local function ellipse(p: Path, cx: number, cy: number, rx: number, ry: number)
    p:moveTo(Vector.xy(cx + rx, cy))
    p:cubicTo(Vector.xy(cx + rx, cy + ry * KAPPA), Vector.xy(cx + rx * KAPPA, cy + ry), Vector.xy(cx, cy + ry))
    p:cubicTo(Vector.xy(cx - rx * KAPPA, cy + ry), Vector.xy(cx - rx, cy + ry * KAPPA), Vector.xy(cx - rx, cy))
    p:cubicTo(Vector.xy(cx - rx, cy - ry * KAPPA), Vector.xy(cx - rx * KAPPA, cy - ry), Vector.xy(cx, cy - ry))
    p:cubicTo(Vector.xy(cx + rx * KAPPA, cy - ry), Vector.xy(cx + rx, cy - ry * KAPPA), Vector.xy(cx + rx, cy))
    p:close()
end

local function rot(x: number, y: number, z: number, ax: number, ay: number, az: number): (number, number, number)
    -- rotate about x, then y, then z (the shader's ring frame, inverted)
    local c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, z * c - x * s
    c, s = math.cos(az), math.sin(az)
    x, y = x * c - y * s, x * s + y * c
    return x, y, z
end

local function drawFallback(self: Fx, renderer: Renderer)
    local m = self.mode
    local pa, pb, ps = self.paintA, self.paintB, self.paintS
    pa.color = self.col0
    pb.color = self.col1
    if m < 1.5 then
        if self.amount < 0.01 then
            return
        end
        local ph = phase(self)
        local R = self.size
        local p = Path.new()
        if ph < 0.56 then
            local g = math.min(1, ph / 0.5)
            ellipse(p, self.lipX, self.lipY + R * (0.5 + g), R * (0.4 + 0.6 * g), R * (0.4 + 0.75 * g))
        else
            ellipse(p, self.lipX, self.lipY + R * 0.2, R * 0.35, R * 0.35)
            if ph < 0.68 then
                local f = (ph - 0.56) / 0.12
                local y = self.lipY + R * 2 + (self.hitY - self.lipY - R * 2) * f * f
                ellipse(p, self.lipX + (self.hitX - self.lipX) * f * f, y, R * 0.9, R * (1.05 + 0.4 * f))
            end
        end
        renderer:drawPath(p, pa)
        if ph >= 0.68 then
            local v = (ph - 0.68) / 0.32
            local r = Path.new()
            ellipse(r, self.hitX, self.hitY, R * (1.2 + 6 * v), R * (1.2 + 6 * v) * math.cos(self.surf))
            ps.color = Color.opacity(self.col0, 0.8 * (1 - v)) :: Color
            ps.thickness = math.max(0.6, R * 0.25 * (1 - v))
            renderer:drawPath(r, ps)
        end
    elseif m < 2.5 then
        local n = math.floor(self.count + 0.5)
        local front = self.side > 0
        ps.color = self.col0
        ps.thickness = math.max(0.5, self.tube * 2 * self.ring)
        if self.ring > 0.01 then
            for i = 0, n - 1 do
                local ax, ay = self.incline + i * self.spread, self.precess + i * 1.2
                local R = self.radius * (1 + 0.09 * i)
                local p = Path.new()
                local pen = false
                for j = 0, 64 do
                    local a = j / 64 * TAU
                    local x, y, z = rot(math.cos(a) * R, 0, math.sin(a) * R, ax, ay, self.roll)
                    if (z >= 0) == front then
                        if pen then
                            p:lineTo(Vector.xy(x, -y))
                        else
                            p:moveTo(Vector.xy(x, -y))
                            pen = true
                        end
                    else
                        pen = false
                    end
                end
                renderer:drawPath(p, ps)
            end
        end
        if self.drops > 0.01 then
            local p = Path.new()
            for k = 0, 4 do
                local a = self.ang + k * TAU / 5 + 0.25 * math.sin(k * 1.7)
                local x, y, z = rot(math.cos(a) * self.radius, 0, math.sin(a) * self.radius, self.incline, self.precess,
                    self.roll)
                if (z >= 0) == front then
                    local r = self.dropSize * self.drops
                    ellipse(p, x, -y, r, r)
                end
            end
            renderer:drawPath(p, pb)
        end
    else
        -- flat walls: back and sides behind the cup, the front wall (and its ribbon) before it
        local B, Hw, e = self.boxB, self.boxH, self.tilt
        local phi = math.pi / 2 * math.clamp(self.fold, 0, 1)
        local function proj(x: number, y: number, z: number): Vector
            return Vector.xy(x, -(y * math.cos(e) - z * math.sin(e)))
        end
        local function wall(nx: number, nz: number, lo: number, hi: number): Path
            local tx, tz = nz, -nx
            local p = Path.new()
            local vs: { Vector } = {}
            for _, q in ipairs({ { -B, lo }, { B, lo }, { B, hi }, { -B, hi } }) do
                local a, b = q[2] * math.cos(phi), q[2] * math.sin(phi)
                table.insert(vs, proj(nx * (B + a) + tx * q[1], b, nz * (B + a) + tz * q[1]))
            end
            -- script paths fill clockwise (on screen); flip the quad when it winds the other way
            local area = 0
            for i = 1, 4 do
                local a, b = vs[i], vs[i % 4 + 1]
                area += a.x * b.y - b.x * a.y
            end
            if area < 0 then
                vs = { vs[4], vs[3], vs[2], vs[1] }
            end
            for i, v in ipairs(vs) do
                if i == 1 then
                    p:moveTo(v)
                else
                    p:lineTo(v)
                end
            end
            p:close()
            return p
        end
        if self.side < 0 then
            pa.color = Color.lerp(self.col0, Color.rgb(60, 45, 35), 0.25)
            renderer:drawPath(wall(0, -1, 0, Hw), pa)
            pa.color = Color.lerp(self.col0, Color.rgb(60, 45, 35), 0.12)
            renderer:drawPath(wall(-1, 0, 0, Hw), pa)
            renderer:drawPath(wall(1, 0, 0, Hw), pa)
        else
            renderer:drawPath(wall(0, 1, 0, Hw), pa)
            if self.ribbon > 0.01 then
                renderer:drawPath(wall(0, 1, Hw * 0.46 - 7, Hw * 0.46 + 7), pb)
            end
            if self.bow > 0.01 and self.fold > 0.99 then
                local c = proj(0, Hw * 0.46, B + 2)
                local s = 1.4 * math.min(1, self.bow)
                local p = Path.new()
                ellipse(p, c.x - 11 * s, c.y - 3 * s, 10 * s, 6 * s)
                ellipse(p, c.x + 11 * s, c.y - 3 * s, 10 * s, 6 * s)
                ellipse(p, c.x, c.y, 5 * s, 5 * s)
                renderer:drawPath(p, pb)
            end
        end
    end
end

-- ------------------------------------------------------------------ draw

function draw(self: Fx, renderer: Renderer)
    if self.live < 0.5 or self.opacity <= 0.001 then
        return
    end
    local canvas = self.canvas
    local pipe = self.pipe
    local group = self.group
    local ubo = self.ubo
    if not self.gpu or canvas == nil or pipe == nil or group == nil or ubo == nil then
        drawFallback(self, renderer)
        return
    end
    local key = stateKey(self)
    if key ~= self.lastKey then
        self.lastKey = key
        writeUniforms(self)
        ubo:write(self.staging)
        local pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 0 } } },
            label = 'kiln fx3d',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(3)
        pass:finish()
    end
    renderer:save()
    renderer:transform(Mat2D.withTranslation(self.x0, self.y0) * Mat2D.withScale(1 / self.k, 1 / self.k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Fx>
    return {
        mode = 1,
        side = 0,
        live = 1,
        still = false,
        x0 = -100,
        y0 = -100,
        w = 200,
        h = 200,
        res = 2,
        zoom = 1,
        dpr = 1,
        tilt = 0,
        opacity = 1,
        lipX = 0,
        lipY = 0,
        hitX = 0,
        hitY = 60,
        size = 6,
        amount = 1,
        period = 2.2,
        surf = 1.0,
        radius = 100,
        tube = 2,
        ring = 1,
        drops = 1,
        incline = 0.3,
        count = 1,
        dropSize = 7,
        spin = 0.12,
        precess = 0,
        roll = 0,
        spread = 0.46,
        gloss = 1,
        fold = 1,
        tissue = 1,
        ribbon = 1,
        bow = 1,
        boxB = 80,
        boxH = 58,
        cupR = 63,
        cupH = 143,
        col0 = Color.rgb(53, 71, 162),
        col1 = Color.rgb(63, 85, 196),
        col2 = Color.rgb(247, 241, 232),
        gpu = false,
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(UBO_SIZE),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        k = 2,
        t = 0,
        ang = 0,
        lastKey = '',
        paintA = Paint.with({ color = Color.rgb(53, 71, 162), style = 'fill' }),
        paintB = Paint.with({ color = Color.rgb(188, 112, 87), style = 'fill' }),
        paintS = Paint.with({ color = Color.rgb(242, 236, 226), style = 'stroke', thickness = 1.5, cap = 'round' }),
        init = init,
        advance = advance,
        draw = draw,
    }
end
