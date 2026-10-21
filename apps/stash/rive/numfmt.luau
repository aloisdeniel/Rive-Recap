--!strict
-- Locale-aware number formatting shared by the hero and summary converters.
-- Rive's built-in DataConverterToString has no grouping separators, so this
-- module is the documented "formatting adapter" that lives inside the file.
-- It reads `locale` and `currencyCode` from UserRecap; nothing here stores a
-- formatted copy of any user value.

local M = {}

type Seps = { group: string, decimal: string, symbolAfter: boolean }

local NNBSP = utf8.char(0x202F)

local function seps(locale: string): Seps
    local lang = string.lower(string.sub(locale, 1, 2))
    if locale == "de-CH" then
        return { group = "’", decimal = ".", symbolAfter = false }
    end
    if lang == "de" or lang == "es" or lang == "it" or lang == "nl" or lang == "pt"
        or lang == "id" or lang == "tr" or lang == "da" or lang == "el" then
        return { group = ".", decimal = ",", symbolAfter = true }
    end
    if lang == "fr" or lang == "sv" or lang == "nb" or lang == "no" or lang == "fi"
        or lang == "cs" or lang == "pl" or lang == "ru" or lang == "uk" or lang == "sk" then
        return { group = NNBSP, decimal = ",", symbolAfter = true }
    end
    return { group = ",", decimal = ".", symbolAfter = false }
end

local function symbol(code: string): string
    if code == "EUR" then return "€" end
    if code == "USD" then return "$" end
    if code == "GBP" then return "£" end
    if code == "JPY" then return "¥" end
    if code == "INR" then return "₹" end
    return code .. " "
end

local function zeroDecimalCurrency(code: string): boolean
    return code == "JPY" or code == "KRW" or code == "CLP" or code == "ISK"
end

function M.clean(v: number): number
    if v ~= v or v == math.huge or v == -math.huge or v < 0 then
        return 0
    end
    return v
end

local function group(intPart: number, sep: string): string
    local s = string.format("%.0f", intPart)
    local out = ""
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

local function fixed(v: number, decimals: number, sp: Seps): string
    if decimals <= 0 then
        return group(math.floor(v + 0.5), sp.group)
    end
    local scale = 10 ^ decimals
    local r = math.floor(v * scale + 0.5)
    local ip = math.floor(r / scale)
    local fp = r - ip * scale
    local frac = string.format("%0" .. tostring(decimals) .. "d", fp)
    return group(ip, sp.group) .. sp.decimal .. frac
end

-- Values of a million or more get a compact visual label ("1.2M"); the exact
-- value stays available to the host's accessible text.
local function compact(v: number, sp: Seps): string?
    if v >= 1e9 then
        return fixed(math.floor(v / 1e8) / 10, 1, sp) .. "B"
    elseif v >= 1e6 then
        return fixed(math.floor(v / 1e5) / 10, 1, sp) .. "M"
    end
    return nil
end

function M.count(v: number, locale: string): string
    local sp = seps(locale)
    v = math.floor(M.clean(v) + 0.5)
    local c = compact(v, sp)
    if c then return c end
    return fixed(v, 0, sp)
end

function M.countExact(v: number, locale: string): string
    return fixed(math.floor(M.clean(v) + 0.5), 0, seps(locale))
end

function M.money(v: number, locale: string, code: string, settled: boolean, exact: boolean?): string
    local sp = seps(locale)
    v = M.clean(v)
    local body: string
    local c = if exact then nil else compact(v, sp)
    if c then
        body = c
    else
        local decimals = 0
        if not zeroDecimalCurrency(code) then
            local cents = math.floor(v * 100 + 0.5)
            if cents % 100 ~= 0 then
                decimals = 2
            end
        end
        if not settled then
            -- while counting up, keep whole units so digits do not flicker
            decimals = 0
        end
        body = fixed(v, decimals, sp)
    end
    local sym = symbol(code)
    if sp.symbolAfter then
        if string.sub(sym, -1) == " " then
            return body .. " " .. string.sub(sym, 1, -2)
        end
        return body .. utf8.char(0x00A0) .. sym
    end
    return sym .. body
end

function M.moneyExact(v: number, locale: string, code: string, settled: boolean): string
    return M.money(v, locale, code, settled, true)
end

return M
