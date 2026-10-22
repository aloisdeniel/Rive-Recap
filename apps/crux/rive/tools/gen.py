#!/usr/bin/env python3
"""Generates the Crux recap RML sources.

    python3 tools/gen.py        # from apps/crux/rive

Writes scene/*.rml. The RML is the editable source of truth for the Rive file;
this generator exists because ten scenes x (forward/back/reduced) entrances,
exits and ~450 state transitions are far easier to keep consistent from code.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rml  # noqa: E402

rml.reset_ids(200)
import model  # noqa: E402
import art  # noqa: E402
import conv  # noqa: E402
import rig  # noqa: E402
import build_stage  # noqa: E402
import main_ab  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.environ.get("CRUX_OUT") or os.path.join(ROOT, "scene")


def doc(*els):
    r = rml.E("Rive", version="1", kind="fragment")
    r.add(list(els))
    return r.xml() + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    main_board = main_ab.artboard()
    stage_board = build_stage.artboard()
    files = {
        "1-main.rml": doc(main_board),
        "2-stage.rml": doc(stage_board, rml.E("ComponentAsset", artboardId=stage_board.id, name="Stage")),
        "3-components.rml": doc(art.wordmark_artboard(), art.wordmark_asset()),
        "4-data.rml": doc(model.view_model(), *conv.CONVS,
                          *art.script_assets(),
                          rml.E("ScriptAsset", file="director.luau", name="director", id=main_ab.DIRECTOR_ASSET),
                          *art.font_assets()),
    }
    with open(os.path.join(ROOT, "rigdata.luau"), "w") as f:
        f.write(rig.luau())
    print("wrote rigdata.luau")
    for name, text in files.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(text)
        print(f"wrote scene/{name} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
