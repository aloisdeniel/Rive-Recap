-- Locale-aware integer formatting for every bound count.
--
-- Input: a number (already multiplied by the count-up playhead and rounded).
-- Output: grouped digits using the separator for UserRecap.locale, e.g.
--   en-GB 12,345   de-DE 12.345   fr-FR 12 345 (narrow no-break space)   de-CH 12'345
-- Values of 100,000 and above use a compact visual label (123.4K, 1.2M) with
-- the locale's decimal mark; the exact value belongs in host accessible text.
-- Negative or non-finite input renders as 0 (the director also clamps).

type Fmt = { vm: ViewModel?, ctx: Context? }

local DOT = { de = true, es = true, it = true, pt = true, nl = true, da = true, id = true, tr = true, el = true, ro = true, hr = true, sl = true }
local SPACE = { fr = true, sv = true, nb = true, no = true, fi = true, pl = true, cs = true, sk = true, ru = true, uk = true, hu = true, bg = true, et = true, lv = true, lt = true }

local function separators(locale: string): (string, string)
    local lang = string.lower(string.sub(locale, 1, 2))
    if locale == 'de-CH' or locale == 'de-LI' then return '\u{2019}', '.' end
    if DOT[lang] then return '.', ',' end
    if SPACE[lang] then return '\u{202F}', ',' end
    return ',', '.'
end

local function group(n: number, sep: string): string
    local s = tostring(math.floor(n))
    local out = ''
    local len = #s
    for i = 1, len do
        out ..= string.sub(s, i, i)
        local rem = len - i
        if rem > 0 and rem % 3 == 0 then out ..= sep end
    end
    return out
end

local function format(n: number, locale: string): string
    if n ~= n or n == math.huge or n == -math.huge or n < 0 then n = 0 end
    n = math.floor(n + 0.5)
    local sep, dec = separators(locale)
    if n >= 1000000 then
        local v = math.floor(n / 100000) / 10
        local whole = math.floor(v)
        local frac = math.floor((v - whole) * 10 + 0.5)
        return group(whole, sep) .. (if frac > 0 then dec .. tostring(frac) else '') .. 'M'
    elseif n >= 100000 then
        local v = math.floor(n / 100) / 10
        local whole = math.floor(v)
        local frac = math.floor((v - whole) * 10 + 0.5)
        return group(whole, sep) .. (if frac > 0 then dec .. tostring(frac) else '') .. 'K'
    end
    return group(n, sep)
end

function init(self: Fmt, context: Context): boolean
    self.ctx = context
    return true
end

local function locale(self: Fmt): string
    if self.vm == nil then
        local ctx = self.ctx
        if ctx ~= nil then
            self.vm = ctx:rootViewModel() or ctx:viewModel()
        end
    end
    local vm = self.vm
    if vm ~= nil then
        local p = vm:getString('locale')
        if p ~= nil then return p.value end
    end
    return 'en-GB'
end

function convert(self: Fmt, input: DataValue): DataValue
    local out = DataValue.string()
    if input:isNumber() then
        out.value = format((input :: DataValueNumber).value, locale(self))
    elseif input:isString() then
        out.value = (input :: DataValueString).value
    end
    return out
end

function reverseConvert(self: Fmt, input: DataValue): DataValue
    return DataValue.number()
end

return function(): Converter<Fmt, DataValue, DataValue>
    return { vm = nil, ctx = nil, init = init, convert = convert, reverseConvert = reverseConvert }
end
