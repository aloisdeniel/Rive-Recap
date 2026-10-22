#!/usr/bin/env python3
"""Responsive review captures: the viewport matrix as contact sheets in ../captures/responsive/.

python3 tools/capture_responsive.py            (needs Pillow for the sheets: pip install pillow)
JOBS=2 KEEP=/tmp/frames python3 tools/capture_responsive.py   (parallel renders; keep the full-size frames)

Every frame is a headless `rive . --screenshot --viewport=WxH` with the default layout fit, so the artboard is laid
out at that size (no letterboxing). Scenes are reached with the Right key, the way the walkthrough video does.
One sheet per subject, every size of the matrix on it: portrait sizes first, then landscape.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "captures", "responsive")
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
JOBS = int(os.environ.get("JOBS", "3"))

PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
ALL = PORTRAIT + LANDSCAPE


def keys(n, dwell=150):
    out = []
    for _ in range(n):
        out += [f"--advance={dwell}", "--key=right"]
    return out


def fixture(name):
    data = json.load(open(os.path.join(ROOT, "fixtures", name + ".json")))
    out = []
    for k, v in data.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        if k == "personaColor":
            v = str(v).lstrip("#")
        out.append(f"--data={k}={v}")
    return out


# subject -> (sizes, flags); scene k settled = k-1 Right presses then 4 s
SUBJECTS = {
    "scene-01-invitation": (ALL, keys(0) + ["--advance=240"]),
    "scene-02-nights": (ALL, keys(1) + ["--advance=240"]),
    "scene-03-objects": (ALL, keys(2) + ["--advance=240"]),
    "scene-06-meteors-mirrored": (ALL, keys(5) + ["--advance=240"]),
    "scene-07-lunar-mirrored": (ALL, keys(6) + ["--advance=240"]),
    "scene-09-persona": (ALL, keys(8) + ["--advance=240"]),
    "scene-10-summary": (ALL, keys(9) + ["--advance=240"]),
    # the signature iris shut over the 5 -> 6 cut (art left -> art right side by side): it covers every canvas
    "transition-iris-05-to-06-f17": (ALL, keys(4) + ["--advance=150", "--key=right", "--advance=17"]),
    "transition-iris-05-to-06-f34": (ALL, keys(4) + ["--advance=150", "--key=right", "--advance=34"]),
    "personas-0-3": (["390x844", "1280x720", "667x375", "768x1024"], None),   # built below, one row per persona
    "reduced-motion-scene-02": (["320x568", "390x844", "1280x720", "1920x1080"], ["--data=reducedMotion=true"] + keys(1) + ["--advance=30"]),
    "fixture-new-user-summary": (["320x568", "390x844", "667x375", "1280x720", "768x1024", "2560x1080"],
                                 fixture("new-user") + keys(1) + ["--advance=240"]),
    "fixture-extreme-scene-01": (["320x568", "390x844", "667x375", "1280x720", "768x1024", "2560x1080"],
                                 fixture("extreme-long-copy") + ["--advance=240"]),
    "fixture-extreme-scene-03": (["320x568", "390x844", "667x375", "1280x720", "768x1024", "2560x1080"],
                                 fixture("extreme-long-copy") + keys(2) + ["--advance=240"]),
    "fixture-extreme-summary": (["320x568", "390x844", "667x375", "1280x720", "768x1024", "2560x1080"],
                                fixture("extreme-long-copy") + keys(9) + ["--advance=240"]),
}


def shot(path, vp, flags, project=ROOT):
    cmd = [RIVE, project, "--quiet", f"--screenshot={path}", f"--viewport={vp}", "--data=autoAdvanceEnabled=false"] + flags
    r = subprocess.run(cmd, capture_output=True, text=True)
    return path if r.returncode == 0 and os.path.exists(path) else None


def probe_project(spec):
    """A copy of the project whose layout script re-lays out mid-run as if the canvas were resized (test hook)."""
    tmp = tempfile.mkdtemp(prefix="nocturne-resize-")
    for item in ("rive.yaml", "clock.luau", "layout.luau", "scripts", "shaders", "assets", "tools"):
        src = os.path.join(ROOT, item)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(tmp, item))
    os.makedirs(os.path.join(tmp, "rml"))
    subprocess.run([sys.executable, os.path.join(tmp, "tools", "generate.py")], check=True, capture_output=True,
                   env=dict(os.environ, NOCTURNE_RESIZE_PROBE=spec))
    return tmp


def sheet(out, files, tile=(360, 360), cols=4):
    from PIL import Image, ImageDraw
    files = [f for f in files if f and os.path.exists(f)]
    rows = (len(files) + cols - 1) // cols
    tw, th = tile
    im = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 30) + 12), (22, 24, 28))
    d = ImageDraw.Draw(im)
    for i, f in enumerate(files):
        src = Image.open(f).convert("RGB")
        s = min(tw / src.width, th / src.height)
        src = src.resize((max(1, round(src.width * s)), max(1, round(src.height * s))), Image.LANCZOS)
        x, y = 12 + (i % cols) * (tw + 12), 12 + (i // cols) * (th + 30)
        d.text((x, y), os.path.splitext(os.path.basename(f))[0], fill=(235, 235, 235))
        im.paste(src, (x + (tw - src.width) // 2, y + 16 + (th - src.height) // 2))
    im.save(out, optimize=True)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    tmp = tempfile.mkdtemp(prefix="nocturne-resp-")
    jobs, groups = [], {}
    for name, (sizes, flags) in SUBJECTS.items():
        if flags is None:
            continue
        for vp in sizes:
            p = os.path.join(tmp, name, f"{vp}.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            jobs.append((p, vp, flags, ROOT))
            groups.setdefault(name, []).append(p)
    for i in range(4):
        for vp in SUBJECTS["personas-0-3"][0]:
            p = os.path.join(tmp, "personas", f"persona-{i}-{vp}.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            jobs.append((p, vp, [f"--data=personaIndex={i}"] + keys(8) + ["--advance=240"], ROOT))
            groups.setdefault("personas-0-3", []).append(p)
    # resize across the threshold mid-scene (scene 3): before, just after, settled
    probes = {"landscape-to-portrait": probe_project("8.0:700x900"), "portrait-to-landscape": probe_project("8.0:1280x900:700x900")}
    # the canvas is 1280 x 900 in both; the portrait side lays out at 700 x 900 (the right of the canvas stays empty),
    # and the simulated resize happens at 8 s, once scene 3 has settled
    for tag, (vp, proj) in {"landscape-to-portrait": ("1280x900", probes["landscape-to-portrait"]),
                            "portrait-to-landscape": ("1280x900", probes["portrait-to-landscape"])}.items():
        for label, extra in (("a-before-7.8s", 158), ("b-after-8.1s", 176), ("c-settled-10s", 290)):
            p = os.path.join(tmp, "resize", f"{tag}-{label}.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            flags = ["--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=150", f"--advance={extra}"]
            jobs.append((p, vp, flags, proj))
            groups.setdefault("resize-mid-scene-03", []).append(p)
    with ThreadPoolExecutor(JOBS) as ex:
        res = list(ex.map(lambda j: shot(*j), jobs))
    failed = [j[0] for j, r in zip(jobs, res) if r is None]
    os.makedirs(OUT, exist_ok=True)
    for name, files in groups.items():
        cols = 4 if len(files) > 6 else 3
        tile = (360, 360) if len(files) > 6 else (480, 400)
        sheet(os.path.join(OUT, name + ".png"), files, tile, cols)
        print("sheet", name, len(files))
    for p in probes.values():
        shutil.rmtree(p, ignore_errors=True)
    keep = os.environ.get("KEEP")   # KEEP=<dir> keeps the full-size frames there for review
    if keep:
        shutil.rmtree(keep, ignore_errors=True)
        shutil.copytree(tmp, keep)
    shutil.rmtree(tmp, ignore_errors=True)
    if failed:
        print("FAILED", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
