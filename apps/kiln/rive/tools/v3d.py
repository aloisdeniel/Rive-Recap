"""The 3D vessel drawable (scripts/vessel3d.luau + .wgsl) as a generator helper.

A V3D is one ScriptedDrawable with a ScriptInput per shape/material parameter.
`look()` turns a motif profile name plus material overrides into a full input
dict; `V3D.key()` keys any subset of it on a timeline, so the Motif and Persona
layers choreograph the 3D form the same way they keyed vector vertices before.
"""
from __future__ import annotations

import math

import motif as MF
from rml import COLOR_OBJS, E, argb, bind
from gen_kiln import PORC, ULTRA, settle

PROFILE_KEYS = ["h"] + [f"r{i}" for i in range(6)] + [f"c{i}" for i in range(6)]
MATERIAL_KEYS = ["cap", "dip", "flow", "bandW", "bandAt", "sway", "drip", "inner", "rings", "speck", "sheen",
                 "coils", "prints", "sphere", "heat", "gloss", "tilt", "roll", "yaw", "turnGain", "live", "seed"]
NUM_KEYS = PROFILE_KEYS + MATERIAL_KEYS
COLOR_KEYS = ["body", "glaze"]

DEFAULT = dict(cap=0.0, dip=0.0, flow=0.0, bandW=0.4, bandAt=math.pi / 2, sway=0.35, drip=0.6, inner=1.0,
               rings=1.0, speck=1.0, sheen=0.0, coils=0.0, prints=0.0, sphere=0.0, heat=0.0, gloss=1.0, tilt=0.2, roll=0.0, yaw=0.0,
               turnGain=1.0, live=1.0, seed=1.0, body="EFE7DC", glaze=ULTRA)

# canvas frame in the vessel's local units (base centre at 0,0; y down)
FRAME = dict(halfW=150.0, top=-366.0, bottom=34.0, res=2.0, msaa=4.0)


def profile(prof: str) -> dict:
    h, rows = MF.PROFILES[prof]
    d = {"h": float(h)}
    for i, (cx, w) in enumerate(rows):
        d[f"r{i}"] = float(w)
        d[f"c{i}"] = float(cx)
    return d


def look(prof: str, **kw) -> dict:
    d = dict(DEFAULT)
    d.update(profile(prof))
    d.update(kw)
    return d


class V3D:
    def __init__(self, g, name: str, init: dict, turn: bool = False, scene: bool = False, frame: dict | None = None,
                 keyed: bool = True):
        self.el = E("ScriptedDrawable", {"scriptAssetId": g.v3d_script.id, "name": name})
        self.inputs: dict[str, E] = {}
        for k in NUM_KEYS:
            v = float(init[k])
            inp = E("ScriptInputNumber", {"propertyValue": v, "name": k})
            inp.id  # noqa: B018 - keyed by id
            if keyed:
                settle(inp, "propertyValue", v)
            self.inputs[k] = inp
            self.el.add(inp)
        for k in COLOR_KEYS:
            c = argb(init[k])
            inp = E("ScriptInputColor", {"propertyValue": c, "name": k})
            COLOR_OBJS.add(inp.id)
            if keyed:
                settle(inp, "propertyValue", c)
            self.inputs[k] = inp
            self.el.add(inp)
        for k, v in (frame or FRAME).items():
            self.el.add(E("ScriptInputNumber", {"propertyValue": float(v), "name": k}))
        if keyed:
            # pieces on the art stage: the canvas follows the stage scale and the device ratio
            self.el.add(E("ScriptInputNumber", {"propertyValue": 1.0, "name": "zoom"}, bind(g.p("_artScale"), 243)))
            self.el.add(E("ScriptInputNumber", {"propertyValue": 1.0, "name": "dpr"}, bind(g.p("_dpr"), 243)))
        if turn:
            self.el.add(E("ScriptInputNumber", {"propertyValue": 0.0, "name": "turn"}, bind(g.p("_turnPhase"), 243)))
        if scene:
            self.el.add(E("ScriptInputNumber", {"propertyValue": 1.0, "name": "scene"},
                          bind(g.p("currentScreen"), 243)))

    def key(self, a, f: int, lk: dict, ease: str = "settle", only=None):
        """key every input present in `lk` (or the names in `only`) at frame f"""
        names = only if only is not None else [k for k in NUM_KEYS + COLOR_KEYS if k in lk]
        for k in names:
            if k not in lk:
                continue
            if k in COLOR_KEYS:
                a.k(self.inputs[k], "propertyValue", (f, argb(lk[k]), "lin" if ease != "hold" else "hold"))
            else:
                a.k(self.inputs[k], "propertyValue", (f, float(lk[k]), ease))
        return a
