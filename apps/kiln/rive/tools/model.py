"""The single UserRecap view model: public contract + internal playheads."""
from __future__ import annotations

import json
import os

from rml import E, ID, argb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (name, type, default) -- public contract, in the brief's order.
PUBLIC = [
    ("userName", "string", "Alex"),
    ("year", "number", 2026),
    ("periodLabel", "string", "January 1–December 31, 2026"),
    ("locale", "string", "en-GB"),
    ("piecesMade", "number", 42),
    ("studioHours", "number", 118),
    ("glazeTests", "number", 27),
    ("firings", "number", 11),
    ("clayReclaimedKg", "number", 8.4),
    ("formsExplored", "number", 6),
    ("piecesGifted", "number", 13),
    ("personaIndex", "number", 1),
    ("personaName", "string", "Glaze Alchemist"),
    ("personaDescription", "string", "Always testing a little magic."),
    ("personaColor", "color", "#3547A2"),
    ("autoAdvanceSeconds", "number", 7),
    ("autoAdvanceEnabled", "boolean", True),
    ("isPaused", "boolean", False),
    ("reducedMotion", "boolean", False),
    ("soundEnabled", "boolean", False),
    ("currentScreen", "number", 1),
    ("screenProgress", "number", 0),
    ("shareIncludeName", "boolean", False),
    ("shareIncludeSensitiveValues", "boolean", False),
    ("continueLabel", "string", "Continue"),
    ("previousLabel", "string", "Previous"),
    ("pauseLabel", "string", "Pause"),
    ("playLabel", "string", "Play"),
    ("shareLabel", "string", "Share"),
    ("replayLabel", "string", "Replay"),
    ("introHeadline", "string", "Your 2026 on Kiln"),
    ("introSupport", "string", "A year, uniquely yours."),
    ("summaryHeadline", "string", "A little year. A lot of you."),
    ("summarySupport", "string", "Take a piece of your year with you."),
    ("emptyHeadline", "string", "Every story starts somewhere."),
    ("emptySupport", "string", "Your next chapter is waiting."),
    ("personaLabel", "string", "Your personal style"),
] + [(f"showScreen{i}", "boolean", True) for i in range(1, 11)] + [
    ("screen2Headline", "string", "You gave ideas a shape."),
    ("screen2Support", "string", "A year worked by hand."),
    ("screen2Unit", "string", "pieces made"),
    ("screen3Headline", "string", "Time well shaped."),
    ("screen3Support", "string", "Your practice found its own pace."),
    ("screen3Unit", "string", "studio hours"),
    ("screen4Headline", "string", "Curiosity, fired."),
    ("screen4Support", "string", "Small experiments. Unexpected color."),
    ("screen4Unit", "string", "glaze tests"),
    ("screen5Headline", "string", "Into the heat."),
    ("screen5Support", "string", "Each firing wrote a different ending."),
    ("screen5Unit", "string", "firings"),
    ("screen6Headline", "string", "Back to possibility."),
    ("screen6Support", "string", "Material ready for another beginning."),
    ("screen6Unit", "string", "kg clay reclaimed"),
    ("screen7Headline", "string", "One material. Many voices."),
    ("screen7Support", "string", "Bowls, cups, vases, and your own ideas."),
    ("screen7Unit", "string", "forms explored"),
    ("screen8Headline", "string", "Made by you. Held by someone."),
    ("screen8Support", "string", "Your work found a place in everyday life."),
    ("screen8Unit", "string", "pieces gifted"),
    # contract additions (documented in README)
    ("privateValueLabel", "string", "Private"),
    ("turntableHint", "string", "Drag to turn"),
    # responsive layout: landscape when the artboard width is >= layoutBreakpoint
    ("layoutBreakpoint", "number", 768),
]

# internal, written by the in-file sequencer script / state machine only.
INTERNAL = [
    ("_navDir", "number", 1),
    ("_command", "number", 0),
    ("_frozen", "boolean", False),
    ("_holding", "boolean", False),
    ("_artX", "number", 0),
    ("_artY", "number", 284),
    ("_artScale", "number", 1),
    ("_cardX", "number", 45),
    ("_cardY", "number", 196),
    ("_cardScale", "number", 1),
    # responsive placement, written by the sequencer from the real artboard size
    # (defaults are the 390 x 844 portrait values)
    ("_landscape", "number", 0),
    ("_stack", "number", 1),
    ("_dpr", "number", 1),
    ("_copyL", "number", 28),
    ("_copyT", "number", 86),
    ("_copyR", "number", 28),
    ("_copyB", "number", 0),
    ("_copyS", "number", 1),
    ("_copyR4", "number", 150),
    ("_c9T", "number", 92),
    ("_altL", "number", 28),
    ("_altR", "number", 28),
    ("_c10T", "number", 84),
    ("_c10B", "number", 0),
    ("_alignL", "number", 0),
    ("_alignC", "number", 1),
    ("_align10", "number", 1),
    ("_textC", "number", 2),
    ("_bigK", "number", 1),
    ("_padX", "number", 24),
    ("_navX", "number", 20),
    ("_actL", "number", 20),
    ("_actR", "number", 20),
    ("_actAlign", "number", 4),
    ("_headVA", "number", 0),
    ("_chromeS", "number", 1),
    ("_chromeR", "number", 0),
    ("_hdrT", "number", 12),
    ("_ftrB", "number", 18),
    ("_hintOn", "number", 1),
] + [(f"_seg{i}", "number", 0) for i in range(1, 11)] + [
    ("_isEmpty", "number", 0),
    ("_personaVariant", "number", 1),
    ("_namePublic", "number", 0),
    ("_hoursPublic", "number", 0),
    ("_countSeconds", "number", 1.2),
    ("_turnPhase", "number", 0),
    ("_finished", "number", 0),
    ("_settled", "number", 0),
    ("_screenChangedCount", "number", 0),
    ("_shareTappedCount", "number", 0),
    ("_recapFinishedCount", "number", 0),
]

FIXTURES = [
    ("Fixture", "fixture.json"),
    ("NewUser", "new-user.json"),
    ("Extreme", "extreme.json"),
]


class Model:
    def __init__(self, default_fixture: str = "Fixture"):
        self.vm = E("ViewModel", {"name": "UserRecap"})
        self.vmid = self.vm.id
        self.props: dict[str, tuple[str, str]] = {}
        tag = {"string": "ViewModelPropertyString", "number": "ViewModelPropertyNumber",
               "boolean": "ViewModelPropertyBoolean", "color": "ViewModelPropertyColor"}
        for name, typ, _ in PUBLIC + INTERNAL:
            p = E(tag[typ], {"name": name})
            self.vm.add(p)
            self.props[name] = (p.id, typ)
        self.instances = []
        default_id = None
        order = sorted(FIXTURES, key=lambda f: f[0] != default_fixture)  # runtimes pick the first instance
        for inst_name, fname in order:
            data = json.load(open(os.path.join(ROOT, "fixtures", fname)))
            inst = E("ViewModelInstance", {"exports": True, "name": inst_name})
            for name, typ, dflt in PUBLIC + INTERNAL:
                v = data.get(name, dflt)
                pid = self.props[name][0]
                if typ == "string":
                    inst.add(E("ViewModelInstanceString", {"propertyValue": str(v), "viewModelPropertyId": pid}))
                elif typ == "number":
                    inst.add(E("ViewModelInstanceNumber", {"propertyValue": float(v), "viewModelPropertyId": pid}))
                elif typ == "boolean":
                    inst.add(E("ViewModelInstanceBoolean", {"propertyValue": bool(v), "viewModelPropertyId": pid}))
                elif typ == "color":
                    inst.add(E("ViewModelInstanceColor", {"propertyValue": argb(str(v)), "viewModelPropertyId": pid}))
            self.vm.add(inst)
            if inst_name == default_fixture:
                default_id = inst.id
        self.vm.attrs["defaultInstanceId"] = default_id
        self.default_instance = default_id

    def path(self, name: str) -> str:
        return f"{self.vmid}-{self.props[name][0]}"

    def typ(self, name: str) -> str:
        return self.props[name][1]
