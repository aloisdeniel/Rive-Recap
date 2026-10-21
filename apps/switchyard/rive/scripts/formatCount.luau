-- formatCount: number -> grouped integer string, used by every hero number,
-- the summary card and the semantic (accessible) labels.
--
-- * clamps negative, NaN and infinite inputs to 0 (adapter safety net)
-- * rounds to an integer: every Switchyard metric is a count
-- * picks the digit-group separator from UserRecap.locale once, at init
--   (en: "," | de, es, it, nl, pt, da, id, tr: "." | fr, sv, nb, fi, pl, cs, ru, uk: U+202F)
-- Localised compact labels ("1.2M") are NOT produced here: a host that wants
-- them formats in its adapter and writes a string field (see README).

type Fmt = { sep: string }

local DOT = { de = true, es = true, it = true, nl = true, pt = true, da = true, id = true, tr = true }
local THIN = { fr = true, sv = true, nb = true, fi = true, pl = true, cs = true, ru = true, uk = true }

local function separatorFor(locale: string): string
    local lang = string.lower(string.sub(locale, 1, 2))
    if DOT[lang] then
        return '.'
    end
    if THIN[lang] then
        return '\u{202F}'
    end
    if string.sub(locale, 1, 5) == 'de-CH' then
        return '\u{2019}'
    end
    return ','
end

local function group(n: number, sep: string): string
    if n ~= n or n == math.huge or n == -math.huge or n < 0 then
        n = 0
    end
    local s = string.format('%.0f', math.floor(n + 0.5))
    local out = ''
    local len = #s
    for i = 1, len do
        out ..= string.sub(s, i, i)
        local rem = len - i
        if rem > 0 and rem % 3 == 0 then
            out ..= sep
        end
    end
    return out
end

function init(self: Fmt, context: Context): boolean
    local vm = context:viewModel()
    if vm then
        local loc = vm:getString('locale')
        if loc then
            self.sep = separatorFor(loc.value)
        end
    end
    return true
end

local function convert(self: Fmt, input: DataValueNumber): DataValueString
    local dv: DataValueString = DataValue.string()
    dv.value = group(input.value, self.sep)
    return dv
end

local function reverseConvert(self: Fmt, input: DataValueString): DataValueNumber
    local dv: DataValueNumber = DataValue.number()
    local digits = string.gsub(input.value, '[^0-9]', '')
    dv.value = tonumber(digits) or 0
    return dv
end

return function(): Converter<Fmt, DataValueNumber, DataValueString>
    return { sep = ',', init = init, convert = convert, reverseConvert = reverseConvert }
end
