"""Responsive layout rig: the block spec of every scene, and the rig view model names.

Each scene is split into *blocks* (hero number, copy, art, ...). A block is a group of
content that always moves and scales together; every keyed animation inside it stays
in the block's own design coordinates (the original 390 x 844 portrait design). At run
time the director (director.luau + layout.luau) places every block for the real canvas
size and writes its transform (x, y, scale) into the global `CruxRig` view model; each
block's rig node in the stage is bound to those three numbers.

This file is the single source of truth for the blocks. gen.py writes it to
rigdata.luau for the runtime engine.

Box = (x, y, w, h) in design units: the *key* content of the block (what must stay
visible and must not overlap other blocks). Bleed art (floors, the wall) may extend past it.

Portrait (P): the design keeps its relative positions with one scale; `ax` anchors the
block horizontally inside the extra width (0 left, 0.5 centre, 1 right) and `v` says
whether it rides the top or the bottom of the canvas. `fit` blocks shrink to clear the
controls on short phones.

Wide (landscape, and portrait folded on short canvases): a list of rows; each row is a
list of alternative column arrangements (plus an automatic single stacked column). The
layout engine scores each one - how much of the story area it fills, minus any breach of
a readable floor; more columns are preferred on very wide areas - and keeps the best. A
column stacks its blocks; `role` sets its scale bounds and shrink priority (see BOUNDS in
layout.luau), `v` its vertical alignment, `h` the horizontal alignment of its blocks.
`bleed` (unused now) would let a column run under the bottom bar.
"""
import model

S = {}


def scene(k, blocks, rows, carrier="art", carrier_wide=(0, 0), stack_h=0.0):
    # every row also gets a stacked alternative (all its blocks in one column, in
    # reading order): on a tall landscape canvas it is often the fullest composition
    for row in rows:
        names = []
        for c in row[0]:
            names += c["blocks"]
        order = [b for b in blocks if b in names]
        row.append([col(order, "stack", h=stack_h)])
    S[k] = {"blocks": blocks, "rows": rows, "carrier": carrier, "carrier_wide": carrier_wide}


def B(box, ax=0.0, v="top", fit=False, wbox=None, tail=0):
    """tail: design units below the box that still belong to the block in wide modes
    (decoration hanging off it, such as the summary card's corner hold)."""
    return {"box": box, "wbox": wbox or box, "ax": ax, "v": v, "fit": fit, "tail": tail}


def col(blocks, role, v="center", h=0.0, bleed=False):
    return {"blocks": blocks, "role": role, "v": v, "h": h, "bleed": bleed}


def text_art():
    return [[col(["hero", "copy"], "text"), col(["art"], "art")],
            [col(["hero"], "hero"), col(["copy"], "text"), col(["art"], "art")]]

# 1 Invitation
scene(1, {"title": B((22, 118, 344, 160)), "copy": B((24, 280, 300, 186)),
          "art": B((0, 430, 390, 440), ax=1, v="bottom")},
      [[[col(["title", "copy"], "text"), col(["art"], "art", v="bottom", h=0.5)],
        [col(["title"], "text"), col(["copy"], "text"), col(["art"], "art", v="bottom", h=0.5)]]])
# 2 Sessions
scene(2, {"hero": B((20, 112, 268, 248)), "copy": B((22, 372, 214, 214)),
          "art": B((110, 150, 290, 730), ax=1, v="bottom")},
      [[[col(["hero", "copy"], "text"), col(["art"], "art", v="bottom", h=0.5)],
        [col(["hero"], "hero"), col(["copy"], "text"), col(["art"], "art", v="bottom", h=0.5)]]])
# 3 Sends
scene(3, {"hero": B((24, 110, 342, 252), ax=0.5), "copy": B((24, 372, 342, 128), ax=0.5),
          "art": B((-20, 500, 420, 320), ax=0.5, v="bottom")},
      [text_art()], stack_h=0.5)
# 4 Attempts: the number lives in the art (its attempt marks fly into it)
scene(4, {"copy": B((22, 366, 202, 214), ax=0.5), "art": B((10, 112, 380, 720), ax=0.5)},
      [[[col(["copy"], "copy"), col(["art"], "heroart")]]])
# 5 Technique sessions
scene(5, {"hero": B((24, 110, 342, 250)), "copy": B((22, 380, 302, 192)),
          "art": B((0, 560, 390, 170), ax=0.5, v="bottom")},
      [text_art()])
# 6 Minutes: the number sits inside the dial
scene(6, {"dial": B((23, 146, 344, 344), ax=0.5), "copy": B((22, 490, 342, 102)),
          "floor": B((30, 620, 340, 115), ax=0.5, v="bottom")},
      [[[col(["dial", "floor"], "heroart", h=0.5), col(["copy"], "copy")],
        [col(["dial"], "heroart", h=0.5), col(["copy"], "copy"), col(["floor"], "ledge", v="bottom", h=0.5)]]],
      carrier="floor", stack_h=0.5)
# 7 Active weeks
scene(7, {"hero": B((20, 110, 300, 250)), "copy": B((22, 370, 214, 190)),
          "art": B((20, 420, 360, 310), ax=1, v="bottom")},
      [[[col(["hero", "copy"], "text"), col(["art"], "art", v="bottom", h=0.5)],
        [col(["hero"], "hero"), col(["copy"], "text"), col(["art"], "art", v="bottom", h=0.5)]]])
# 8 Climbing partners
scene(8, {"hero": B((20, 110, 304, 250)), "copy": B((22, 370, 290, 190)),
          "art": B((20, 490, 360, 270), ax=0.5, v="bottom")},
      [text_art()])
# 9 Persona: landscape puts the emblem first, the title in its own column
scene(9, {"title": B((22, 118, 346, 256)), "art": B((0, 400, 390, 440), ax=0.5, v="bottom")},
      [[[col(["art"], "art", h=0.5), col(["title"], "title")]]], stack_h=0.5)
# 10 Summary: the share card has a wide variant (690 x 300) in landscape
scene(10, {"head": B((24, 112, 342, 140), ax=0.5, wbox=(24, 112, 220, 178)),
           "card": B((24, 262, 350, 362), ax=0.5, fit=True, wbox=(0, 262, 724, 348), tail=100),
           "ehead": B((24, 120, 342, 198), ax=0.5), "eart": B((40, 320, 320, 250), ax=0.5),
           "ground": B((0, 560, 390, 284), ax=0.5, v="bottom")},
      [[[col(["head"], "copy"), col(["card"], "card", h=0.5)],
        [col(["head", "card"], "card", h=0.0)]],
       [[col(["ehead"], "text"), col(["eart"], "art", h=0.5)]]],
      carrier="card", carrier_wide=(348, -52))

# ground blocks: in wide modes they are pinned to the bottom of the canvas
GROUND = {(10, "ground")}


# ---------------------------------------------------------------- rig view model names
def block_names(k, b):
    cap = b[0].upper() + b[1:]
    return f"s{k}{cap}X", f"s{k}{cap}Y", f"s{k}{cap}S"


GLOBALS = {
    # viewport: k = canvas height / 844 is the scale of the stage's viewport node
    "k": 1.0, "uw": 390.0, "uh": 844.0, "vw": 390.0, "vh": 844.0, "dpr": 1.0, "px": 2.0,
    "landscape": 0.0, "wide": 0.0, "mode": 0.0,
    # chrome
    "topH": 64.0, "botH": 104.0, "botPad": 18.0, "barPad": 20.0, "btn": 52.0, "btnHalf": 26.0,
    "pill": 56.0, "pillHalf": 28.0,
    # the persistent carrier hold and the chalk cloud (both in the carrier scene's space)
    "carX": 0.0, "carY": 0.0, "carS": 1.0, "chX": 0.0, "chY": 0.0, "chS": 1.0,
}


def register():
    for name, v in GLOBALS.items():
        model.rig_prop(name, v)
    for k in sorted(S):
        for b in S[k]["blocks"]:
            x, y, s = block_names(k, b)
            model.rig_prop(x, 0.0)
            model.rig_prop(y, 0.0)
            model.rig_prop(s, 1.0)


register()


# ---------------------------------------------------------------- Luau export
def _lua(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(float(v), 3)).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return "'" + v + "'"
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(_lua(x) for x in v) + " }"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_lua(x)}" for k, x in v.items()) + " }"
    raise TypeError(v)


def luau():
    out = ["--!strict",
           "-- GENERATED by tools/rig.py (python3 tools/gen.py) -- do not edit by hand.",
           "-- Per-scene layout blocks for layout.luau: design boxes, portrait anchors and",
           "-- the wide-mode column arrangements. See tools/rig.py for the field meanings.",
           "",
           "export type Box = { number }",
           "export type Block = { name: string, box: Box, wbox: Box, ax: number, v: string, fit: boolean, ground: boolean, tail: number }",
           "export type Col = { blocks: { string }, role: string, v: string, h: number, bleed: boolean }",
           "export type Scene = { k: number, blocks: { Block }, rows: { { { Col } } }, carrier: string, carrierWide: { number } }",
           "",
           "local scenes: { Scene } = {"]
    for k in sorted(S):
        sc = S[k]
        blocks = []
        for name, b in sc["blocks"].items():
            blocks.append({"name": name, "box": list(b["box"]), "wbox": list(b["wbox"]), "ax": float(b["ax"]),
                           "v": b["v"], "fit": b["fit"], "ground": (k, name) in GROUND, "tail": float(b["tail"])})
        rows = []
        for row in sc["rows"]:
            alts = []
            for alt in row:
                alts.append([{"blocks": c["blocks"], "role": c["role"], "v": c["v"], "h": float(c["h"]),
                              "bleed": c["bleed"]} for c in alt])
            rows.append(alts)
        out.append("    {")
        out.append(f"        k = {k},")
        out.append("        blocks = {")
        for b in blocks:
            out.append(f"            {_lua(b)},")
        out.append("        },")
        out.append("        rows = {")
        for alts in rows:
            out.append("            {")
            for alt in alts:
                out.append("                { " + ", ".join(_lua(c) for c in alt) + " },")
            out.append("            },")
        out.append("        },")
        out.append(f"        carrier = '{sc['carrier']}',")
        out.append(f"        carrierWide = {_lua(list(sc['carrier_wide']))},")
        out.append("    },")
    out.append("}")
    out.append("")
    out.append("return scenes")
    return "\n".join(out) + "\n"
