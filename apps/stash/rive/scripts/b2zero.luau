--!strict
-- ScriptedDataConverter: boolean -> number (0 when true, 1 when false).
-- Used to drive opacity from UserRecap flags (privacy, empty state, pause icon).
type B = {}

local function convert(self: B, input: DataValue): DataValue
    local out: DataValueNumber = DataValue.number()
    out.value = 1
    if input:isBoolean() and (input :: DataValueBoolean).value then
        out.value = 0
    end
    return out
end

local function reverseConvert(self: B, input: DataValue): DataValue
    return DataValue.boolean()
end

return function(): Converter<B, DataValue, DataValue>
    return { convert = convert, reverseConvert = reverseConvert }
end
