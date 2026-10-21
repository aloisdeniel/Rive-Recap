"""UserRecap view model: the single shared data model, plus fixtures."""
import json
import os
from rml import E, nid, CHALK, COAL, ACID, COBALT

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(HERE, "..", "fixtures")

# name -> (type, default) ; type in number|string|bool|color|trigger
# Order = order in the editor's data panel.
PROPS = [
    # ---- host-owned user data (logical schema from the brief)
    ("userName", "string", "Alex"),
    ("year", "number", 2026),
    ("periodLabel", "string", "January 1–December 31, 2026"),
    ("locale", "string", "en-GB"),
    ("sessions", "number", 86),
    ("sends", "number", 214),
    ("attempts", "number", 1320),
    ("techniqueSessions", "number", 24),
    ("longestSessionMinutes", "number", 105),
    ("activeWeeks", "number", 39),
    ("climbingPartners", "number", 9),
    ("personaIndex", "number", 0),
    ("personaName", "string", "Route Reader"),
    ("personaDescription", "string", "You see the way through."),
    ("personaColor", "color", COAL),
    ("autoAdvanceSeconds", "number", 7),
    ("autoAdvanceEnabled", "bool", True),
    ("isPaused", "bool", False),
    ("reducedMotion", "bool", False),
    ("soundEnabled", "bool", False),
    ("currentScreen", "number", 1),
    ("screenProgress", "number", 0),
    ("shareIncludeName", "bool", False),
    ("shareIncludeSensitiveValues", "bool", False),
    ("continueLabel", "string", "Continue"),
    ("previousLabel", "string", "Previous"),
    ("pauseLabel", "string", "Pause"),
    ("playLabel", "string", "Play"),
    ("shareLabel", "string", "Share"),
    ("replayLabel", "string", "Replay"),
    ("introHeadline", "string", "Your 2026 on Crux"),
    ("introSupport", "string", "A year, uniquely yours."),
    ("summaryHeadline", "string", "A little year. A lot of you."),
    ("summarySupport", "string", "Take a piece of your year with you."),
    ("emptyHeadline", "string", "Every story starts somewhere."),
    ("emptySupport", "string", "Your next chapter is waiting."),
    ("personaLabel", "string", "Your personal style"),
] + [(f"showScreen{i}", "bool", True) for i in range(1, 11)] + [
    ("screen2Headline", "string", "You kept showing up."),
    ("screen2Support", "string", "One wall. A thousand ways to move."),
    ("screen2Unit", "string", "sessions"),
    ("screen3Headline", "string", "Problems, solved."),
    ("screen3Support", "string", "Every finish started with a first move."),
    ("screen3Unit", "string", "sends"),
    ("screen4Headline", "string", "Every try counted."),
    ("screen4Support", "string", "The work between the wins mattered too."),
    ("screen4Unit", "string", "attempts"),
    ("screen5Headline", "string", "You found another way."),
    ("screen5Support", "string", "Footwork and balance got their own spotlight."),
    ("screen5Unit", "string", "technique sessions"),
    ("screen6Headline", "string", "Time on the wall."),
    ("screen6Support", "string", "Your longest logged session this year."),
    ("screen6Unit", "string", "minutes"),
    ("screen7Headline", "string", "Built over time."),
    ("screen7Support", "string", "Your rhythm, at your pace."),
    ("screen7Unit", "string", "active weeks"),
    ("screen8Headline", "string", "Better with a belay buddy."),
    ("screen8Support", "string", "People who shared the puzzle."),
    ("screen8Unit", "string", "climbing partners"),
    # ---- host-provided extras (documented additions)
    ("personaAdapterEnabled", "bool", True),
    ("shareDismissed", "trigger", None),
    # ---- adapter-owned derived fields (written by director.luau; host may read)
    ("sessionsDisplay", "string", "86"),
    ("sendsDisplay", "string", "214"),
    ("attemptsDisplay", "string", "1,320"),
    ("techniqueSessionsDisplay", "string", "24"),
    ("longestSessionMinutesDisplay", "string", "105"),
    ("activeWeeksDisplay", "string", "39"),
    ("climbingPartnersDisplay", "string", "9"),
    ("yearDisplay", "string", "2026"),
    ("personaSlot", "number", 0),
    ("isEmptyRecap", "bool", False),
    ("visibleScreenCount", "number", 10),
    ("visibleScreenPosition", "number", 1),
    ("progressValue", "number", 0),
    ("screenAnnouncement", "string", ""),
    ("pauseButtonLabel", "string", "Pause"),
    # ---- file-internal playheads / signals (do not write from the host)
    ("navDirection", "number", 1),
    ("enteredScreen", "number", 0),
    ("heroProgress", "number", 0),
    ("sceneSettled", "bool", False),
    ("focusedControl", "number", 0),
    ("holdGrabbed", "bool", False),
    ("isSharing", "bool", False),
    ("navNext", "trigger", None),
    ("navPrev", "trigger", None),
    ("togglePause", "trigger", None),
    ("replay", "trigger", None),
    ("shareRequested", "trigger", None),
    ("screenSignal", "trigger", None),
    ("finishSignal", "trigger", None),
]

VM_ID = "0:90000"
P = {}        # prop name -> id
TYPES = {}
_pid = [90000]
for name, typ, _ in PROPS:
    _pid[0] += 1
    P[name] = f"0:{_pid[0]}"
    TYPES[name] = typ


def path(name):
    return f"{VM_ID}-{P[name]}"


def load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name + ".json")) as f:
        return json.load(f)


def color_of(v):
    if isinstance(v, str) and v.startswith("#"):
        return "FF" + v[1:].upper()
    return v


def instance(inst_name, data, iid=None):
    inst = E("ViewModelInstance", exports=True, name=inst_name, id=iid or nid())
    for name, typ, default in PROPS:
        v = data.get(name, default)
        if typ == "number":
            inst.add(E("ViewModelInstanceNumber", propertyValue=v, viewModelPropertyId=P[name]))
        elif typ == "string":
            inst.add(E("ViewModelInstanceString", propertyValue=v, viewModelPropertyId=P[name]))
        elif typ == "bool":
            inst.add(E("ViewModelInstanceBoolean", propertyValue=bool(v), viewModelPropertyId=P[name]))
        elif typ == "color":
            inst.add(E("ViewModelInstanceColor", propertyValue=color_of(v), viewModelPropertyId=P[name]))
        elif typ == "trigger":
            inst.add(E("ViewModelInstanceTrigger", viewModelPropertyId=P[name]))
    return inst


DEFAULT_INSTANCE = "0:89999"


def view_model():
    vm = E("ViewModel", defaultInstanceId=DEFAULT_INSTANCE, name="UserRecap", id=VM_ID)
    for name, typ, _ in PROPS:
        tag = {"number": "ViewModelPropertyNumber", "string": "ViewModelPropertyString",
               "bool": "ViewModelPropertyBoolean", "color": "ViewModelPropertyColor",
               "trigger": "ViewModelPropertyTrigger"}[typ]
        vm.add(E(tag, name=name, id=P[name]))
    vm.add(instance("Fixture", load_fixture("fixture"), DEFAULT_INSTANCE))
    vm.add(instance("NewUser", load_fixture("new-user")))
    vm.add(instance("Extreme", load_fixture("extreme")))
    return vm
