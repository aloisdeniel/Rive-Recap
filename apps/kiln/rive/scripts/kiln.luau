--!strict
-- Kiln chamber (scene 5): draws scripts/kiln.wgsl into a GPU canvas the size of the
-- arch interior. The hosting node is clipped by the arch, so the shader only fills
-- a rectangle. `fire` (0 cold, 1 full heat, 2 cooled into the palette) is keyed by
-- the scene's timeline; `still` (reducedMotion or frozen) stops the heat haze.
-- The canvas re-renders only while something changes: a cooled kiln is one image draw.
-- Without GPU scripting it draws nothing and the vector bands beneath show instead.

type Kiln = {
    fire: Input<number>,
    still: Input<boolean>,
    live: Input<number>,
    w: Input<number>,
    h: Input<number>,
    res: Input<number>,
    gpu: boolean,
    canvas: GPUCanvas?,
    pipe: GPUPipeline?,
    group: GPUBindGroup?,
    ubo: GPUBuffer?,
    staging: buffer,
    sampler: ImageSampler,
    t: number,
    k: number,
    lastKey: string,
}

function init(self: Kiln, context: Context): boolean
    if self.gpu then
        return true
    end
    local sh = context:shader('scripts/kiln')
    if sh == nil then
        return true
    end
    local pipe = GPUPipeline.new({
        vertex = { module = sh, entryPoint = 'vs_main' },
        fragment = { module = sh, entryPoint = 'fs_main' },
        vertexLayout = {},
        colorTargets = { { format = 'rgba8unorm' } },
    })
    self.pipe = pipe
    local ubo = GPUBuffer.new({ size = 32, usage = 'uniform', label = 'kiln chamber' })
    self.ubo = ubo
    self.group = GPUBindGroup.new({ layout = pipe:getBindGroupLayout(0), ubos = { { slot = 0, buffer = ubo } } })
    local k = math.max(0.5, self.res)
    self.k = k
    self.canvas = context:gpuCanvas({ width = math.ceil(self.w * k), height = math.ceil(self.h * k) })
    self.gpu = true
    return true
end

function advance(self: Kiln, seconds: number): boolean
    -- haze only moves while the kiln is hot and motion is allowed
    if not self.still and self.live >= 0.5 and self.fire > 0.02 and self.fire < 1.98 then
        self.t += math.min(seconds, 0.1)
    end
    return true
end

function draw(self: Kiln, renderer: Renderer)
    if self.live < 0.5 then
        return
    end
    local canvas = self.canvas
    local pipe = self.pipe
    local group = self.group
    local ubo = self.ubo
    if not self.gpu or canvas == nil or pipe == nil or group == nil or ubo == nil then
        return
    end
    local key = string.format('%.4f|%.3f|%s', self.fire, self.t, tostring(self.still))
    if key ~= self.lastKey then
        self.lastKey = key
        local b = self.staging
        buffer.writef32(b, 0, self.w)
        buffer.writef32(b, 4, self.h)
        buffer.writef32(b, 8, self.fire)
        buffer.writef32(b, 12, self.t)
        buffer.writef32(b, 16, if self.still then 1 else 0)
        ubo:write(b)
        local pass = canvas:beginRenderPass({
            color = { { loadOp = 'clear', storeOp = 'store', clearColor = { 0, 0, 0, 1 } } },
            label = 'kiln chamber',
        })
        pass:setPipeline(pipe)
        pass:setBindGroup(0, group)
        pass:draw(3)
        pass:finish()
    end
    renderer:save()
    renderer:transform(Mat2D.withScale(1 / self.k, 1 / self.k))
    renderer:drawImage(canvas.image, self.sampler, 'srcOver', 1)
    renderer:restore()
end

return function(): Node<Kiln>
    return {
        fire = 2,
        still = false,
        live = 1,
        w = 300,
        h = 380,
        res = 1.5,
        gpu = false,
        canvas = nil,
        pipe = nil,
        group = nil,
        ubo = nil,
        staging = buffer.create(32),
        sampler = ImageSampler('clamp', 'clamp', 'bilinear'),
        t = 0,
        k = 1.5,
        lastKey = '',
        init = init,
        advance = advance,
        draw = draw,
    }
end
