#!/usr/bin/env python3
"""Check-only project: KilnRecap nested in a harness that resizes it mid-scene.

    python3 tools/resize_harness.py <outdir> [--screen 4] [--at 150] [--back 330]
    rive <outdir> --artboard=ResizeHarness --data-dump=- ...

The CLI lays a scene out at one --viewport for the whole run, so a resize across the
layout breakpoint cannot be driven from the command line. This writes a copy of the
project whose extra artboard, ResizeHarness (1280 x 844), holds KilnRecap as a
NestedArtboardLayout with its own view-model instance (starting on --screen) and
its own Recap state machine. A timeline keys the nested instance's width:
390 (portrait) until frame --at, 1280 (landscape) until frame --back, then 390 again.
The shipped .riv never contains this artboard.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_kiln  # noqa: E402
from model import INTERNAL, PUBLIC  # noqa: E402
from rml import Anim, E, argb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--screen", type=int, default=4)
    ap.add_argument("--at", type=int, default=150, help="frame where the width jumps to 1280")
    ap.add_argument("--back", type=int, default=330, help="frame where it returns to 390")
    ap.add_argument("--wide", type=float, default=1280.0)
    a = ap.parse_args()

    g = gen_kiln.Gen("Fixture")
    rml = g.build()
    M = g.M
    # the nested placement's own instance: the default fixture values, starting on --screen
    import json
    data = json.load(open(os.path.join(ROOT, "fixtures", "fixture.json")))
    data["currentScreen"] = a.screen
    data["autoAdvanceEnabled"] = False
    inst = E("ViewModelInstance", {"viewModelId": M.vmid, "exports": True, "name": "Harness Recap"})
    tag = {"string": "ViewModelInstanceString", "number": "ViewModelInstanceNumber",
           "boolean": "ViewModelInstanceBoolean", "color": "ViewModelInstanceColor"}
    for name, typ, dflt in PUBLIC + INTERNAL:
        v = data.get(name, dflt)
        v = {"number": float, "boolean": bool, "string": str}.get(typ, lambda x: argb(str(x)))(v)
        inst.add(E(tag[typ], {"propertyValue": v, "viewModelPropertyId": M.props[name][0]}))
    inst.id  # noqa: B018

    nest = E("NestedArtboardLayout", {"artboardId": g.artboard.id, "isStateful": True, "instanceWidth": 390.0,
                                      "instanceHeight": 844.0, "name": "Recap"},
             E("NestedStateMachine", {"animationId": g.artboard.attrs["defaultStateMachineId"], "name": "Recap"}),
             inst)
    nest.id  # noqa: B018
    resize = Anim("Resize", a.back + 600)
    resize.k(nest, "instanceWidth", (0, 390.0, "hold"), (a.at, a.wide, "hold"), (a.back, 390.0, "hold"))
    st = E("LayoutComponentStyle", {"name": "Harness Style"})
    st.id  # noqa: B018
    sm = E("StateMachine", {"name": "Harness"})
    lay = E("StateMachineLayer", {"name": "Resize"})
    s_r = E("AnimationState", {"animationId": resize.id, "x": 200.0, "y": 0.0})
    s_r.id  # noqa: B018
    lay.add(E("AnyState", {"x": 0.0, "y": -120.0}), E("ExitState", {"x": 400.0, "y": -120.0}),
            E("EntryState", {"x": 0.0, "y": 0.0}, E("StateTransition", {"stateToId": s_r.id})), s_r)
    sm.add(lay)
    ab = E("Artboard", {"x": 1000.0, "y": 0.0, "width": float(a.wide), "height": 844.0, "clip": True,
                        "styleId": st.id, "defaultStateMachineId": sm.id, "name": "ResizeHarness"},
           st, E("Fill", {"name": "Bg"}, E("SolidColor", {"colorValue": "FF111111", "name": "C"})), nest, sm,
           resize.render())
    rml = rml.replace("</Rive>\n", ab.render(1) + "\n</Rive>\n")

    os.makedirs(a.out, exist_ok=True)
    for d in ("scripts", "assets"):
        shutil.rmtree(os.path.join(a.out, d), ignore_errors=True)
        shutil.copytree(os.path.join(ROOT, d), os.path.join(a.out, d))
    shutil.copy(os.path.join(ROOT, "rive.yaml"), a.out)
    with open(os.path.join(a.out, "scene.rml"), "w") as f:
        f.write(rml)
    print(a.out)


if __name__ == "__main__":
    main()
