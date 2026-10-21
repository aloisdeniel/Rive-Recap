#!/usr/bin/env python3
"""Contact sheet: sheet.py out.png in1.png in2.png ... (needs Pillow). Labels each frame with its filename."""
import sys
from PIL import Image, ImageDraw
out, files = sys.argv[1], sys.argv[2:]
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
scale = 0.5 if len(ims) > 3 else 0.75
tw, th = int(w * scale), int(h * scale)
cols = min(len(ims), 5)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 26) + 8), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for i, (im, f) in enumerate(zip(ims, files)):
    x = 8 + (i % cols) * (tw + 8)
    y = 8 + (i // cols) * (th + 26)
    sheet.paste(im.resize((tw, th)), (x, y + 18))
    d.text((x, y + 2), f.split("/")[-1], fill=(255, 255, 255))
sheet.save(out)
