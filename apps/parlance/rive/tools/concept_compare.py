#!/usr/bin/env python3
"""captures/concept-vs-build.png: each concept.png screen (2, 4, 9) next to the same settled scene from the build.
Run with a Python that has Pillow (macOS: /usr/bin/python3) after captures/settled/ exists."""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
concept = Image.open(os.path.join(ROOT, "..", "concept.png")).convert("RGB")
BOXES = [(53, 15, 538, 955), (564, 15, 1046, 955), (1073, 15, 1558, 955)]  # the three screens in concept.png
SCENES = [2, 4, 9]
W, H, PAD, LBL = 390, 844, 16, 30
out = Image.new("RGB", (3 * (2 * W + PAD) + 2 * PAD + PAD, H + LBL + 2 * PAD), (36, 32, 44))
d = ImageDraw.Draw(out)
for i, (box, n) in enumerate(zip(BOXES, SCENES)):
    x = PAD + i * (2 * W + 2 * PAD)
    c = concept.crop(box)
    c = c.resize((W, round(W * c.height / c.width)), Image.LANCZOS)
    out.paste(c, (x, PAD + LBL))
    b = Image.open(os.path.join(ROOT, "captures", "settled", f"scene-{n:02d}.png")).convert("RGB").resize((W, H))
    out.paste(b, (x + W + PAD // 2, PAD + LBL))
    d.text((x, PAD), f"concept screen {n}", fill=(230, 225, 240))
    d.text((x + W + PAD // 2, PAD), f"build scene {n} (settled)", fill=(230, 225, 240))
out.save(os.path.join(ROOT, "captures", "concept-vs-build.png"))
print("captures/concept-vs-build.png")
