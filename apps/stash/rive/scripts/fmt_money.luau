--!strict
-- ScriptedDataConverter: number -> localized money string.
-- Input is either the raw UserRecap value or (for hero numbers) the value
-- multiplied by that scene's count-up playhead.
local numfmt = require('numfmt')

type Fmt = { vm: ViewModel? }

local function str(self: Fmt, name: string, fallback: string): string
    local vm = self.vm
    if vm == nil then return fallback end
    local p = vm:getString(name)
    if p == nil or p.value == "" then return fallback end
    return p.value
end

local function init(self: Fmt, context: Context): boolean
    self.vm = context:viewModel()
    return true
end

local function convert(self: Fmt, input: DataValue): DataValue
    local out: DataValueString = DataValue.string()
    if input:isNumber() then
        local v = (input :: DataValueNumber).value
        -- a value with a fractional part of exactly .x after the count-up has
        -- settled shows cents; during the count it shows whole units
        local settled = math.abs(v - math.floor(v)) < 1e-9 or math.abs(v * 100 - math.floor(v * 100 + 0.5)) < 0.05
        out.value = numfmt.money(v, str(self, "locale", "en-GB"), str(self, "currencyCode", "EUR"), settled)
    end
    return out
end

local function reverseConvert(self: Fmt, input: DataValue): DataValue
    return DataValue.number()
end

return function(): Converter<Fmt, DataValue, DataValue>
    return { vm = nil, init = init, convert = convert, reverseConvert = reverseConvert }
end
