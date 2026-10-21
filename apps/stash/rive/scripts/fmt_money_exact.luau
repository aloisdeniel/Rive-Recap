--!strict
-- ScriptedDataConverter: number -> exact localized money (never compacted), for accessible text.
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
        -- raw (never counting) values: cents show whenever the value has them
        out.value = numfmt.moneyExact(v, str(self, "locale", "en-GB"), str(self, "currencyCode", "EUR"), true)
    end
    return out
end

local function reverseConvert(self: Fmt, input: DataValue): DataValue
    return DataValue.number()
end

return function(): Converter<Fmt, DataValue, DataValue>
    return { vm = nil, init = init, convert = convert, reverseConvert = reverseConvert }
end
