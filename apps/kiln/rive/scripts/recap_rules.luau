-- Shared rules for derived UserRecap values. Required by the sequencer (main
-- artboard) and by card_rules (the ShareCard artboard), so a standalone
-- ShareCard render applies the same privacy and visibility rules.

local M = {}

local function flag(vm: ViewModel, name: string): boolean
    local h = vm:getBoolean(name)
    if h == nil then
        return false
    end
    return h.value
end

local function number(vm: ViewModel, name: string): number
    local h = vm:getNumber(name)
    if h == nil then
        return 0
    end
    return h.value
end

local function set(vm: ViewModel, name: string, v: number)
    local h = vm:getNumber(name)
    if h ~= nil and h.value ~= v then
        h.value = v
    end
end

function M.anyStat(vm: ViewModel): boolean
    for n = 2, 8 do
        if flag(vm, 'showScreen' .. n) then
            return true
        end
    end
    return false
end

-- intro and summary are always eligible; the persona needs evidence and a name
function M.isVisible(vm: ViewModel, n: number): boolean
    if n == 1 or n == 10 then
        return true
    end
    if n < 1 or n > 10 or n ~= math.floor(n) then
        return false
    end
    if n == 9 then
        local name = vm:getString('personaName')
        local named = name ~= nil and name.value ~= ''
        return flag(vm, 'showScreen9') and named and M.anyStat(vm)
    end
    return flag(vm, 'showScreen' .. n)
end

function M.derive(vm: ViewModel)
    for n = 1, 10 do
        set(vm, '_seg' .. n, if M.isVisible(vm, n) then 0 else 1)
    end
    set(vm, '_isEmpty', if M.anyStat(vm) then 0 else 1)
    local idx = number(vm, 'personaIndex')
    if idx ~= idx or idx ~= math.floor(idx) or idx < 0 or idx > 3 then
        idx = 0 -- unknown rows fall back to row 0
    end
    set(vm, '_personaVariant', idx)
    set(vm, '_namePublic', if flag(vm, 'shareIncludeName') then 1 else 0)
    set(vm, '_hoursPublic', if flag(vm, 'shareIncludeSensitiveValues') then 1 else 0)
    set(vm, '_countSeconds', if flag(vm, 'reducedMotion') then 0.01 else 1.2)
end

return M
