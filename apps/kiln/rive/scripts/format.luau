-- Locale-aware number formatting for bound stat labels.
--
-- number -> string. Rounds to `decimals`, clamps negatives and non-finite
-- input to 0 (the host adapter should already have done this; this is the
-- last line of defence so a bad value can never render as "nan"), and groups
-- thousands with the separator of UserRecap.locale.
--
-- Supported separators: en / default (1,234.5), de / es / it / nl / pt / tr /
-- id (1.234,5), fr / sv / nb / fi / pl / cs / ru (1 234,5 with a narrow nbsp),
-- de-CH (1'234.5). Anything else falls back to en. A host that needs full CLDR
-- formatting can pre-format strings instead; see README "Host adapter".

type Format = {
    decimals: Input<number>,
    grouping: Input<number>,
    locale: Property<string>?,
}

local function group(intPart: string, sep: string): string
    if sep == '' then
        return intPart
    end
    local out = ''
    local n = #intPart
    for i = 1, n do
        out ..= string.sub(intPart, i, i)
        local rem = n - i
        if rem > 0 and rem % 3 == 0 then
            out ..= sep
        end
    end
    return out
end

local function separators(loc: string): (string, string)
    local lang = string.lower(string.sub(loc, 1, 2))
    if loc == 'de-CH' then
        return "'", '.'
    end
    if lang == 'de' or lang == 'es' or lang == 'it' or lang == 'nl' or lang == 'pt' or lang == 'tr' or lang == 'id' then
        return '.', ','
    end
    if lang == 'fr' or lang == 'sv' or lang == 'nb' or lang == 'fi' or lang == 'pl' or lang == 'cs' or lang == 'ru' then
        return '\u{202F}', ','
    end
    return ',', '.'
end

function init(self: Format, context: Context): boolean
    local vm = context:rootViewModel()
    if vm ~= nil then
        self.locale = vm:getString('locale')
    end
    return true
end

function convert(self: Format, input: DataValueNumber): DataValueString
    local out: DataValueString = DataValue.string()
    local d = math.clamp(math.floor(self.decimals), 0, 3)
    local v = 0
    if input:isNumber() then
        v = input.value
    end
    if v ~= v or v == math.huge or v == -math.huge or v < 0 then
        v = 0
    end
    local scale = 10 ^ d
    local r = math.floor(v * scale + 0.5)
    local ip = math.floor(r / scale)
    local fp = r - ip * scale
    local loc = 'en-GB'
    if self.locale ~= nil then
        loc = self.locale.value
    end
    local gsep, dsep = separators(loc)
    if self.grouping < 0.5 then
        gsep = ''
    end
    local s = group(string.format('%d', ip), gsep)
    if d > 0 then
        local f = string.format('%d', fp)
        while #f < d do
            f = '0' .. f
        end
        s ..= dsep .. f
    end
    out.value = s
    return out
end

function reverseConvert(self: Format, input: DataValueString): DataValueNumber
    local dv: DataValueNumber = DataValue.number()
    dv.value = tonumber(input.value) or 0
    return dv
end

return function(): Converter<Format, DataValueNumber, DataValueString>
    return {
        decimals = 0,
        grouping = 1,
        locale = nil,
        init = init,
        convert = convert,
        reverseConvert = reverseConvert,
    }
end
