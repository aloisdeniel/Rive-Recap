--!strict
-- Crux wall texture: seeded chalk speckles, and optionally a bolt-hole grid, over the
-- whole canvas whatever its size or aspect. The wall colour itself is a plain shape;
-- this is the grain on top of it.
--
-- The canvas size arrives through `w` / `h` (CruxRig uw / uh, in the stage's viewport
-- units). The path is rebuilt only when the size changes, and nothing is drawn while
-- the scene is off-screen (`live`, keyed by every scene entrance like the 3D holds).

type Wall = {
    color: Input<Color>,
    seed: Input<number>,
    density: Input<number>, -- dots per 10,000 square points
    dmin: Input<number>, -- dot diameter range
    dmax: Input<number>,
    gridX: Input<number>,
    gridY: Input<number>,
    gridStepX: Input<number>,
    gridStepY: Input<number>,
    gridD: Input<number>,
    gridColor: Input<Color>,
    w: Input<number>,
    h: Input<number>,
    live: Input<number>,
    dots: Path,
    grid: Path,
    paint: Paint,
    gridPaint: Paint,
    key: string,
}

local K = 0.5523 -- cubic circle handle

local function circle(path: Path, x: number, y: number, r: number)
    local c = r * K
    path:moveTo(Vector.xy(x + r, y))
    path:cubicTo(Vector.xy(x + r, y + c), Vector.xy(x + c, y + r), Vector.xy(x, y + r))
    path:cubicTo(Vector.xy(x - c, y + r), Vector.xy(x - r, y + c), Vector.xy(x - r, y))
    path:cubicTo(Vector.xy(x - r, y - c), Vector.xy(x - c, y - r), Vector.xy(x, y - r))
    path:cubicTo(Vector.xy(x + c, y - r), Vector.xy(x + r, y - c), Vector.xy(x + r, y))
    path:close()
end

local function rebuild(self: Wall)
    -- cover the canvas plus the travel of the parallax layer (the yank lifts it 520,
    -- an entrance drops it in from 150 above)
    local x0, y0 = -40, -220
    local x1, y1 = self.w + 40, self.h + 640
    -- fresh paths: a path the renderer may still hold from the last frame is never mutated
    local dots = Path.new()
    self.dots = dots
    local state = math.floor(self.seed * 7919) % 2147483647 + 1
    local function rnd(): number
        state = (state * 48271) % 2147483647
        return state / 2147483647
    end
    local n = math.floor((x1 - x0) * (y1 - y0) / 10000 * self.density)
    for _ = 1, math.min(n, 6000) do
        local x = x0 + rnd() * (x1 - x0)
        local y = y0 + rnd() * (y1 - y0)
        local d = self.dmin + rnd() * (self.dmax - self.dmin)
        circle(dots, x, y, d * 0.5)
    end
    local grid = Path.new()
    self.grid = grid
    if self.gridStepX > 0 and self.gridStepY > 0 then
        local r = self.gridD * 0.5
        local i0 = math.floor((x0 - self.gridX) / self.gridStepX)
        local i1 = math.ceil((x1 - self.gridX) / self.gridStepX)
        local j0 = math.floor((y0 - self.gridY) / self.gridStepY)
        local j1 = math.ceil((y1 - self.gridY) / self.gridStepY)
        for i = i0, i1 do
            for j = j0, j1 do
                circle(grid, self.gridX + i * self.gridStepX, self.gridY + j * self.gridStepY, r)
            end
        end
    end
end

function update(self: Wall)
    self.paint.color = self.color
    self.gridPaint.color = self.gridColor
    local key = string.format('%d|%d|%.2f', math.floor(self.w + 0.5), math.floor(self.h + 0.5), self.seed)
    if key ~= self.key then
        self.key = key
        rebuild(self)
    end
end

function draw(self: Wall, renderer: Renderer)
    if self.live < 0.5 then
        return
    end
    if self.key == '' then
        update(self)
    end
    if self.gridStepX > 0 then
        renderer:drawPath(self.grid, self.gridPaint)
    end
    renderer:drawPath(self.dots, self.paint)
end

return function(): Node<Wall>
    return {
        color = Color.rgba(32, 34, 31, 89),
        seed = 1,
        density = 2.9,
        dmin = 1,
        dmax = 2.6,
        gridX = 0,
        gridY = 0,
        gridStepX = 0,
        gridStepY = 0,
        gridD = 7,
        gridColor = Color.rgb(58, 60, 56),
        w = 390,
        h = 844,
        live = 1,
        dots = Path.new(),
        grid = Path.new(),
        paint = Paint.with({ color = Color.rgba(32, 34, 31, 89) }),
        gridPaint = Paint.with({ color = Color.rgb(58, 60, 56) }),
        key = '',
        update = update,
        draw = draw,
    }
end
