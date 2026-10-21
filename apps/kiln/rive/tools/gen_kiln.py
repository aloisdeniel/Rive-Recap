#!/usr/bin/env python3
"""Generates apps/kiln/rive/scene.rml -- the Kiln 2026 recap.

    python3 tools/gen_kiln.py                      # default fixture = Fixture
    python3 tools/gen_kiln.py --default NewUser --out /tmp/x/scene.rml

The generator is the maintainable source for the repetitive parts (ten scene
layers x eight states, ninety-odd transitions, keyframe unions). The RML it
writes is ordinary, fully editable RML; a designer can also open the exported
.rev in the Rive editor and keep working there.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("gen_kiln", sys.modules[__name__])  # one module instance when run as a script

from rml import (ID, Anim, E, argb, bind, child, ellipse, fill, mix, node, paint_color, poly,  # noqa: E402
                 rect, shape, smooth_path, stroke, style_color, text_style)
from model import Model  # noqa: E402
import motif as MF  # noqa: E402

W, H = 390, 844
ART_W, ART_H = 390, 560          # art stage local frame, bottom-anchored
ART_TOP = H - ART_H              # 284 on the master artboard

CLAY = "BC7057"
PORC = "F2ECE2"
ULTRA = "3547A2"
CHAR = "38322F"
INK_DARK = CHAR

# per scene: background, ink (chrome + copy), secondary art tone
SCENES = {
    1: dict(bg="F2ECE2", ink=CHAR),
    2: dict(bg=CLAY, ink=PORC),
    3: dict(bg=ULTRA, ink=PORC),
    4: dict(bg="F2ECE2", ink=CHAR),
    5: dict(bg="2E2926", ink=PORC),
    6: dict(bg="E7D2C0", ink=CHAR),
    7: dict(bg="A65F48", ink=PORC),
    8: dict(bg="EEE5D8", ink=CHAR),
    9: dict(bg="2A2523", ink=PORC),
    10: dict(bg="EFE7DC", ink=CHAR),
}

FPS = 60
ENTER = 108      # 1.8 s entrance (orient 0-12, hero 12-72, resolve 72-108)
EXIT = 40        # ~670 ms authored handoff
XFADE = 90       # ms blend between layer states (keeps interrupts clean)

SETTLED: dict[tuple[str, str], float | str] = {}


def settle(el: E, prop: str, value, set_attr: bool = True):
    """register the authored (settled) value of a keyable property"""
    if set_attr:
        el.attrs[prop] = value if isinstance(value, str) else float(value)
    SETTLED[(el.id, prop)] = value
    return el


class Layer:
    """A state machine layer whose animations share a keyed-property union."""

    def __init__(self, name: str):
        self.name = name
        self.anims: list[Anim] = []
        self.el = E("StateMachineLayer", {"name": name})
        self.el.id  # noqa: B018

    def anim(self, name, frames, loop="oneShot", exempt=False):
        a = Anim(name, frames, loop, exempt)
        self.anims.append(a)
        return a

    def finalize(self):
        union = set()
        for a in self.anims:
            union |= set(a.tracks.keys())
        for a in self.anims:
            if a.exempt:
                continue
            for key in union:
                if key not in a.tracks:
                    if key not in SETTLED:
                        raise KeyError(f"{self.name}/{a.name}: no settled value for {key}")
                    a.tracks[key] = [(0, SETTLED[key], "hold")]


class Gen:
    def __init__(self, default_fixture: str):
        ID.n = 100
        SETTLED.clear()
        self.M = Model(default_fixture)
        self.roots: list[E] = []
        self.serif = E("FontAsset", {"file": "assets/fonts/DMSerifDisplay-Regular.ttf", "name": "DM Serif Display"})
        self.sans = E("FontAsset", {"file": "assets/fonts/Manrope-VariableFont_wght.ttf", "name": "Manrope"})
        self.rules_script = E("ScriptAsset", {"file": "scripts/recap_rules.luau", "isModule": True, "folderPath": "scripts", "name": "recap_rules"})
        self.card_script = E("ScriptAsset", {"file": "scripts/card_rules.luau", "name": "card_rules"})
        self.fmt_script = E("ScriptAsset", {"file": "scripts/format.luau", "name": "format"})
        self.seq_script = E("ScriptAsset", {"file": "scripts/sequencer.luau", "name": "sequencer"})
        self.converters: list[E] = []
        self.events: dict[str, E] = {}
        # chrome paints keyed per scene by the Motif layer
        self.ink_paints: list[tuple[E, float]] = []   # (SolidColor, alpha)
        self.bg_paints: list[E] = []
        self.layers: list[Layer] = []
        self.listeners: list[E] = []

    # ------------------------------------------------------------------ helpers
    def p(self, name):
        return self.M.path(name)

    def conv(self, el: E) -> E:
        self.converters.append(el)
        el.id  # noqa: B018
        return el

    def fmt(self, decimals=0, grouping=1, name="Format"):
        c = E("ScriptedDataConverter", {"scriptAssetId": self.fmt_script.id, "name": name},
              E("ScriptInputNumber", {"propertyValue": float(decimals), "name": "decimals"}),
              E("ScriptInputNumber", {"propertyValue": float(grouping), "name": "grouping"}))
        return self.conv(c)

    def formula(self, name, *tokens):
        f = E("DataConverterFormula", {"name": name}, *tokens)
        return self.conv(f)

    def tv(self, v=None, prop=None):
        t = E("FormulaTokenValue", {"operationValue": float(v or 0)})
        if prop:
            t.add(bind(self.p(prop), 777))
        return t

    @staticmethod
    def op(o):
        return E("FormulaTokenOperation", {"operationType": {"+": 0, "-": 1, "*": 2, "/": 3}[o]})

    @staticmethod
    def fn(name):
        return E("FormulaTokenFunction", {"functionType": {"min": 0, "max": 1, "round": 2, "sin": 10, "cos": 9}[name]})

    SEP = staticmethod(lambda: E("FormulaTokenArgumentSeparator"))
    CLOSE = staticmethod(lambda: E("FormulaTokenParenthesisClose"))
    OPEN = staticmethod(lambda: E("FormulaTokenParenthesisOpen"))
    INPUT = staticmethod(lambda: E("FormulaTokenInput"))

    def group(self, name, *convs):
        g = E("DataConverterGroup", {"name": name})
        for c in convs:
            g.add(E("DataConverterGroupItem", {"converterId": c.id}))
        return self.conv(g)

    def count_converter(self, screen: int, decimals: int):
        """stat -> gate(currentScreen >= screen) -> eased count -> formatted"""
        gate = self.formula(
            f"Gate{screen}", self.INPUT(), self.op("*"),
            self.fn("min"), self.tv(1), self.SEP(), self.fn("max"), self.tv(0), self.SEP(),
            self.tv(0, "currentScreen"), self.op("-"), self.tv(screen - 1), self.CLOSE(), self.CLOSE())
        ip = E("DataConverterInterpolator", {"interpolationType": "cubic", "duration": 1.2, "name": f"Count{screen}"},
               E("CubicEaseInterpolator", {"x1": 0.6, "y1": 0.0, "x2": 0.2, "y2": 1.0}))
        ip.add(bind(self.p("_countSeconds"), 756))
        self.conv(ip)
        return self.group(f"CountLabel{screen}", gate, ip, self.fmt(decimals, 1, f"Fmt{screen}"))

    # text --------------------------------------------------------------------
    WEIGHTS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 300: "Light"}

    def serif_style(self, size, color, lh=None, spacing=None):
        return text_style(self.serif.id, size, color, "DM Serif Display", "Regular", line_height=lh, spacing=spacing)

    def sans_style(self, size, color, weight=500, lh=None, spacing=None):
        return text_style(self.sans.id, size, color, "Manrope", self.WEIGHTS.get(weight, "Custom"), weight=weight,
                          line_height=lh, spacing=spacing)

    def text(self, name, style, literal, prop=None, conv=None, width="fill", align="left", reveal=True,
             ellipsis=False, nowrap=False, height=None, layout=True, x=0.0, y=0.0, origin=None):
        t = E("Text", {"name": name, "alignValue": align, "x": float(x), "y": float(y)})
        if layout:
            lp = {"layoutWidthScaleType": "fill" if width == "fill" else "hug",
                  "layoutHeightScaleType": "fixed" if height else "hug", "name": "Layout"}
            if height:
                lp["height"] = float(height)
            t.add(E("LayoutParticipant", lp))
            t.attrs["sizingValue"] = "fixed" if height else ("autoHeight" if width == "fill" else "autoWidth")
        else:
            if isinstance(width, (int, float)):
                t.attrs["width"] = float(width)
                t.attrs["sizingValue"] = "autoHeight"
            else:
                t.attrs["sizingValue"] = "autoWidth"
            if origin:
                t.attrs["originX"], t.attrs["originY"] = float(origin[0]), float(origin[1])
        if nowrap:
            t.attrs["wrapValue"] = "noWrap"
        if ellipsis:
            t.attrs["overflowValue"] = "ellipsis"
        t.add(style)
        run = E("TextValueRun", {"styleId": style.id, "text": literal, "name": "Run"})
        if prop:
            run.add(bind(self.p(prop), 268, conv.id if conv is not None else None))
        t.add(run)
        t.run = run  # type: ignore[attr-defined]
        t.style = style  # type: ignore[attr-defined]
        t.range = None  # type: ignore[attr-defined]
        if reveal:
            rg = E("TextModifierRange", {"modifyTo": 1.0, "falloffTo": 1.0, "name": "Sweep"})
            settle(rg, "modifyFrom", 1.0)
            settle(rg, "falloffFrom", 1.3)
            grp = E("TextModifierGroup", {"modifyOpacity": True, "modifyTranslation": True, "invertOpacity": True,
                                          "opacity": 0.0, "y": 30.0, "name": "Reveal"}, rg)
            t.add(grp)
            t.range = rg  # type: ignore[attr-defined]
        return t

    # layout ------------------------------------------------------------------
    def style(self, **kw):
        a = {"name": kw.pop("name", "Style")}
        for k, v in kw.items():
            a[k] = v
        s = E("LayoutComponentStyle", a)
        s.id  # noqa: B018
        return s

    def box(self, name, st: E, *children, w=10.0, h=10.0, **kw):
        a = {"width": float(w), "height": float(h), "styleId": st.id, "name": name}
        a.update(kw)
        return E("LayoutComponent", a, st, *children)

    def abs_style(self, top=None, bottom=None, left=None, right=None, **kw):
        a = dict(positionTypeValue="absolute")
        for k, v in (("Top", top), ("Bottom", bottom), ("Left", left), ("Right", right)):
            if v is not None:
                a[f"position{k}"] = float(v)
                a[f"position{k}UnitsValue"] = "points"
        # pinned on both sides: let the insets decide the size (responsive)
        if left is not None and right is not None:
            a.setdefault("widthUnitsValue", "auto")
        if top is not None and bottom is not None:
            a.setdefault("heightUnitsValue", "auto")
        a.update(kw)
        return self.style(**a)

    # ------------------------------------------------------------------ build
    def build(self) -> str:
        M = self.M
        ev = lambda n: E("Event", {"name": n})  # noqa: E731
        self.events = {n: ev(n) for n in ("screenChanged", "shareTapped", "recapFinished")}
        idx = E("CustomPropertyNumber", {"propertyValue": 1.0, "name": "index"}, bind(self.p("currentScreen"), 243))
        self.events["screenChanged"].add(idx)

        self.art_back: dict[int, E] = {}
        self.art_front: dict[int, E] = {}
        self.copy: dict[int, E] = {}
        self.scene_layers: dict[int, Layer] = {}

        import scenes  # noqa: E402  (scene art + choreography)
        import chrome  # noqa: E402

        chrome.build_chrome(self)
        self.motif = motif_build(self)
        scenes.build_scenes(self)
        chrome.build_machine(self)

        return self.render()

    # ------------------------------------------------------------------ render
    def render(self) -> str:
        for L in self.layers:
            L.finalize()
        ab = self.artboard
        for a in [a for L in self.layers for a in L.anims] + self.extra_anims:
            ab.add(a.render())
        out = ['<Rive version="1" kind="fragment">',
               "  <!-- GENERATED by tools/gen_kiln.py from fixtures/*.json. Edit the generator, or edit this RML",
               "       directly and stop regenerating. See README.md for the binding/event contract. -->"]
        out.append(ab.render(1))
        out.append(self.card_artboard.render(1))
        out.append(E("ComponentAsset", {"artboardId": self.card_artboard.id, "name": "ShareCard"}).render(1))
        out.append(self.M.vm.render(1))
        for c in self.converters:
            out.append(c.render(1))
        out.append(self.serif.render(1))
        out.append(self.sans.render(1))
        out.append(self.rules_script.render(1))
        out.append(self.card_script.render(1))
        out.append(self.fmt_script.render(1))
        out.append(self.seq_script.render(1))
        out.append("</Rive>\n")
        return "\n".join(out)


def motif_build(g: Gen):
    import motif_build as mb  # noqa: E402
    return mb.build(g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--default", default="Fixture", help="Fixture | NewUser | Extreme")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene.rml"))
    a = ap.parse_args()
    g = Gen(a.default)
    s = g.build()
    with open(a.out, "w") as f:
        f.write(s)
    print(f"wrote {a.out} ({len(s)//1024} KB)")


if __name__ == "__main__":
    main()
