-- Logs each host-facing event as its listener fires, so headless runs can prove
-- screenChanged / shareTapped / recapFinished fire exactly when documented.
-- Harmless in production (one log line per event).
type Audit = { label: Input<string> }

local function performAction(self: Audit, ctx: ListenerContext)
    print(`event: {self.label}`)
end

return function(): ListenerAction<Audit>
    return { label = '', performAction = performAction }
end
