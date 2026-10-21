#!/usr/bin/env python3
"""Writes assets/images/grain.png: a deterministic paper-grain tile (needs Pillow; macOS /usr/bin/python3 has it).

Grey 128 is neutral under the `overlay` blend the scenes use, so the tile only nudges each pixel lighter or
darker. It is quantised to a few grey levels so the PNG stays small; it never carries text or a scene.
"""
import os
import random
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 195, 422  # drawn at 2x over the 390x844 frame -> 2 pt grain, close to the concept's tooth
rnd = random.Random(2026)
im = Image.new("L", (W, H))
px = im.load()
levels = [96, 116, 128, 128, 128, 140, 160]
for y in range(H):
    for x in range(W):
        px[x, y] = levels[max(0, min(len(levels) - 1, int(round(rnd.gauss(3, 1.25)))))]
os.makedirs(os.path.join(ROOT, "assets", "images"), exist_ok=True)
out = os.path.join(ROOT, "assets", "images", "grain.png")
im.save(out, optimize=True)
print(out, os.path.getsize(out), "bytes")
