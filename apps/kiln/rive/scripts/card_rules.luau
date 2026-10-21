-- Applies recap_rules to the bound UserRecap so the ShareCard artboard renders
-- correctly on its own (host snapshot) as well as nested in the summary.
local rules = require('scripts/recap_rules')

type CardRules = { vm: ViewModel? }

function init(self: CardRules, context: Context): boolean
    local vm = context:viewModel()
    if vm ~= nil then
        self.vm = vm
        rules.derive(vm)
    end
    return true
end

function advance(self: CardRules, seconds: number): boolean
    local vm = self.vm
    if vm ~= nil then
        rules.derive(vm)
    end
    return true
end

function draw(self: CardRules, renderer: Renderer) end

return function(context: Context): Layout<CardRules>
    return { vm = nil, init = init, advance = advance, draw = draw }
end
