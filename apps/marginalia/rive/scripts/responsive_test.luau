--!strict
-- Checks for the responsive layout rules (scripts/responsive.luau), run
-- headless with `rive . --test`. They sweep the validation matrix plus a fine
-- grid of sizes and assert, for every page:
--   * orientation is a pure width rule against layoutBreakpoint (767 portrait,
--     768 landscape, any height; a retuned breakpoint moves it)
--   * copy frames never shrink the smallest copy type below 11 pt, the summary
--     card never shrinks its unit labels below 11 pt
--   * copy and illustration stay inside the safe band (below the header,
--     above the controls) and inside the page width
--   * copy and illustration do not overlap (scene 3's numeral is the one
--     authored overlap, in its unit layout, and is excluded)
--   * the ribbon stays above the controls, inside the page, out of the copy
--   * controls are at least 44 x 44

local Resp = require('scripts/responsive')

local PORTRAIT = {
    { 320, 568 }, { 360, 640 }, { 390, 844 }, { 430, 932 }, { 600, 960 }, { 767, 1024 },
    { 667, 375 }, { 740, 360 },
}
local LANDSCAPE = {
    { 768, 1024 }, { 820, 1180 }, { 1024, 768 }, { 1280, 720 }, { 1440, 900 }, { 1920, 1080 },
    { 2560, 1080 }, { 1366, 600 },
}

type Box = Resp.Box

-- an assertion that also names the size and page when it fails
local function check(expect: (value: any) -> Expectation, ok: boolean, what: string)
    if not ok then
        print('FAIL ' .. what)
    end
    expect(ok).is(true)
end

local function tag(s: { number }, n: number): string
    return s[1] .. 'x' .. s[2] .. ' scene ' .. n
end

local EPS = 0.5

local function inside(b: Box, x0: number, y0: number, x1: number, y1: number): boolean
    return b.x >= x0 - EPS and b.y >= y0 - EPS and b.x + b.w <= x1 + EPS and b.y + b.h <= y1 + EPS
end

local function overlaps(a: Box, b: Box): boolean
    return a.x < b.x + b.w - EPS and b.x < a.x + a.w - EPS and a.y < b.y + b.h - EPS and b.y < a.y + a.h - EPS
end

-- every size of the matrix, plus a grid from 320x360 to 2560x1440
local function sizes(): { { number } }
    local out: { { number } } = {}
    for _, s in PORTRAIT do
        table.insert(out, s)
    end
    for _, s in LANDSCAPE do
        table.insert(out, s)
    end
    local w = 320
    while w <= 2560 do
        local h = 360
        while h <= 1440 do
            -- a phone-width canvas is a phone held upright: at least 560 tall
            if w >= 560 or h >= 560 then
                table.insert(out, { w, h })
            end
            h += 90
        end
        w += 74
    end
    return out
end

return function(): Tests
    return function(test: Tester)
        test.group('orientation', function()
            test.case('width only, at 768 by default', function(expect)
                expect(Resp.isLandscape(767, 768)).is(false)
                expect(Resp.isLandscape(768, 768)).is(true)
                expect(Resp.chrome(767, 300, 768).landscape).is(false)
                expect(Resp.chrome(768, 2000, 768).landscape).is(true)
                expect(Resp.chrome(740, 360, 768).landscape).is(false)
                expect(Resp.chrome(820, 1180, 768).landscape).is(true)
            end)
            test.case('the host can retune the breakpoint', function(expect)
                expect(Resp.isLandscape(1024, 1100)).is(false)
                expect(Resp.isLandscape(600, 500)).is(true)
            end)
            test.case('unusable breakpoints fall back to 768', function(expect)
                expect(Resp.breakpoint(0)).is(768)
                expect(Resp.breakpoint(-5)).is(768)
                expect(Resp.breakpoint(0 / 0)).is(768)
                expect(Resp.breakpoint(math.huge)).is(768)
            end)
            test.case('the matrix lands on the expected side', function(expect)
                for _, s in PORTRAIT do
                    expect(Resp.chrome(s[1], s[2], 768).landscape).is(false)
                end
                for _, s in LANDSCAPE do
                    expect(Resp.chrome(s[1], s[2], 768).landscape).is(true)
                end
            end)
        end)

        test.group('chrome', function()
            test.case('controls are at least 44 x 44 and fit their band', function(expect)
                expect(Resp.BUTTON).greaterThanOrEqual(44)
                expect(Resp.PRIMARY_H).greaterThanOrEqual(44)
                for _, s in sizes() do
                    local c = Resp.chrome(s[1], s[2], 768)
                    expect(c.controlsH - c.controlsPadB).greaterThanOrEqual(Resp.PRIMARY_H)
                    expect(c.progressY).lessThan(c.headerH)
                    expect(c.bottom - c.top).greaterThan(0)
                end
            end)
            test.case('390x844 keeps the portrait master chrome', function(expect)
                local c = Resp.chrome(390, 844, 768)
                expect(c.headerH).is(76)
                expect(c.controlsH).is(104)
                expect(c.progressY).is(60)
            end)
        end)

        test.group('pages', function()
            test.case('390x844 is the portrait master (identity frames)', function(expect)
                local c = Resp.chrome(390, 844, 768)
                for n = 1, 10 do
                    local p = Resp.plan(n, c)
                    expect(math.abs(p.copy.sx - 1)).lessThan(0.001)
                    expect(math.abs(p.copy.tx)).lessThan(0.001)
                    expect(math.abs(p.copy.ty - 76)).lessThan(0.001)
                end
            end)
            test.case('type never below 11 pt', function(expect)
                for _, s in sizes() do
                    local c = Resp.chrome(s[1], s[2], 768)
                    for n = 1, 10 do
                        local p = Resp.plan(n, c)
                        local m = Resp.MIN_TEXT - 0.01
                        check(expect, p.copy.sx * 15 >= m, tag(s, n) .. ' copy ' .. p.copy.sx)
                        check(expect, p.foot.sx * 15 >= m, tag(s, n) .. ' foot')
                        check(expect, p.empty.sx * 15 >= m, tag(s, n) .. ' empty')
                        if n == 10 then
                            check(expect, p.cardScale * 14.5 >= m, tag(s, n) .. ' card ' .. p.cardScale)
                        end
                    end
                end
            end)
            test.case('copy and art stay in the safe band and the page', function(expect)
                for _, s in sizes() do
                    local c = Resp.chrome(s[1], s[2], 768)
                    for n = 1, 10 do
                        local p = Resp.plan(n, c)
                        local cr, ar = p.copyRect, p.artRect
                        check(expect, inside(cr, 0, c.top, c.w, c.bottom), tag(s, n) .. ' copy outside '
                            .. cr.x .. ',' .. cr.y .. ' ' .. cr.w .. 'x' .. cr.h .. ' band ' .. c.top .. '-' .. c.bottom)
                        -- the illustration may bleed past the page edges by
                        -- design (curtains, satin ribbons), never past the band
                        check(expect, ar.y >= c.top - EPS and ar.y + ar.h <= c.bottom + EPS,
                            tag(s, n) .. ' art outside ' .. ar.y .. '-' .. (ar.y + ar.h))
                    end
                end
            end)
            test.case('copy and art do not overlap', function(expect)
                for _, s in sizes() do
                    local c = Resp.chrome(s[1], s[2], 768)
                    for n = 1, 10 do
                        local p = Resp.plan(n, c)
                        if p.mode ~= 'unit' then
                            local cr = p.copyRect
                            local ar = p.artRect
                            -- the authored tuck lets an illustration rise into
                            -- the copy box's empty foot
                            local tuck = Resp.SPECS[n].tuck * p.copy.sx + 1
                            local trimmed: Box = { x = cr.x, y = cr.y, w = cr.w, h = cr.h - tuck }
                            check(expect, not overlaps(trimmed, ar), tag(s, n) .. ' overlap ' .. p.mode)
                        end
                    end
                end
            end)
            test.case('the ribbon stays clear of the controls and the copy', function(expect)
                for _, s in sizes() do
                    local c = Resp.chrome(s[1], s[2], 768)
                    for n = 1, 10 do
                        local p = Resp.plan(n, c)
                        check(expect, p.ribbonEnd + 18 * p.ribbonS <= c.bottom, tag(s, n) .. ' ribbon low')
                        check(expect, p.ribbonX > 0 and p.ribbonX < c.w, tag(s, n) .. ' ribbon x')
                        if p.mode == 'row' and not Resp.SPECS[n].ribbonArt then
                            local cr = p.copyRect
                            local half = 9 * p.ribbonS
                            local clear = p.ribbonX + half <= cr.x + EPS or p.ribbonX - half >= cr.x + cr.w - EPS
                            check(expect, clear, tag(s, n) .. ' ribbon on copy')
                        end
                    end
                end
            end)
        end)
    end
end
