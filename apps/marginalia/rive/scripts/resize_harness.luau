--!strict
-- Test fixture (not part of the recap): hosts the Recap artboard, bound to
-- the same UserRecap instance, and resizes it mid-run, the way a host's
-- layout fit does when a window is resized or a device is rotated.
--
--   rive . --artboard="Resize Harness" --viewport=1280x720 --data=currentScreen=4 ...
--
-- Until `at` seconds the Recap is laid out at the viewport turned on its side
-- (720x1280 here: portrait), then at the viewport itself (1280x720: landscape),
-- so one run crosses the 768 breakpoint mid-scene. Pointer events are passed
-- through, so taps can navigate before or during the resize.

type Harness = {
    recap: Input<Artboard<Data.UserRecap>>,
    at: Input<number>,
    inst: Artboard<Data.UserRecap>?,
    size: Vector,
    clock: number,
}

function init(self: Harness, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil or self.inst ~= nil then
        return true
    end
    self.inst = self.recap:instance(vm)
    return true
end

function resize(self: Harness, size: Vector, scale: number)
    self.size = size
end

function advance(self: Harness, seconds: number): boolean
    local a = self.inst
    if a == nil or self.size.x <= 0 then
        return true
    end
    self.clock += seconds
    local w, h = self.size.y, self.size.x
    if self.clock >= self.at then
        w, h = self.size.x, self.size.y
    end
    if a.width ~= w or a.height ~= h then
        a.width = w
        a.height = h
    end
    a:advance(seconds)
    return true
end

function draw(self: Harness, renderer: Renderer)
    local a = self.inst
    if a ~= nil then
        a:draw(renderer)
    end
end

function pointerDown(self: Harness, event: PointerEvent)
    local a = self.inst
    if a ~= nil then
        a:pointerDown(event)
    end
end

function pointerMove(self: Harness, event: PointerEvent)
    local a = self.inst
    if a ~= nil then
        a:pointerMove(event)
    end
end

function pointerUp(self: Harness, event: PointerEvent)
    local a = self.inst
    if a ~= nil then
        a:pointerUp(event)
    end
end

return function(context: Context): Layout<Harness>
    return {
        recap = late(),
        at = 1.5,
        inst = nil,
        size = Vector.xy(0, 0),
        clock = 0,
        init = init,
        resize = resize,
        advance = advance,
        draw = draw,
        pointerDown = pointerDown,
        pointerMove = pointerMove,
        pointerUp = pointerUp,
    }
end
