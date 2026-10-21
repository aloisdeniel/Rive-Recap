#!/usr/bin/env python3
"""Headless capture helper: python3 tools/shoot.py OUT.png [--next N] [--back N] [--settle F] [--data k=v ...] [extra rive flags]

--next N   taps the Continue button N times (with a short settle between taps)
--fixture  name of a JSON fixture in fixtures/ whose values are applied with --data
"""
import json, os, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RIVE = os.path.expanduser("~/.rive/bin/rive")


def main(argv):
    out = argv[0]
    nxt = back = 0
    settle = 160
    gap = 26
    extra = []
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--next":
            nxt = int(argv[i + 1]); i += 2; continue
        if a == "--back":
            back = int(argv[i + 1]); i += 2; continue
        if a == "--settle":
            settle = argv[i + 1]; i += 2; continue
        if a == "--gap":
            gap = int(argv[i + 1]); i += 2; continue
        if a == "--fixture":
            data = json.load(open(os.path.join(ROOT, "fixtures", argv[i + 1] + ".json")))
            for k, v in data.items():
                if isinstance(v, bool):
                    v = "true" if v else "false"
                if k == "personaColor":
                    v = str(v).lstrip("#")
                extra.append(f"--data={k}={v}")
            i += 2; continue
        extra.append(a); i += 1
    cmd = [RIVE, ".", f"--screenshot={out}"] + extra
    for _ in range(nxt):
        cmd += ["--pointer=click@195,780", f"--advance={gap}", "--pointer=move@380,20", "--advance=2"]
    for _ in range(back):
        cmd += ["--pointer=click@70,780", f"--advance={gap}", "--pointer=move@380,20", "--advance=2"]
    cmd += [f"--advance={settle}"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines():
        if any(s in line for s in (" error", "warning", "console", "no property", "rejected")):
            print(line)
    if r.returncode:
        print("FAILED", r.returncode)


if __name__ == "__main__":
    main(sys.argv[1:])
