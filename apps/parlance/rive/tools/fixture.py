#!/usr/bin/env python3
"""Run the rive CLI headless with a JSON fixture applied through --data.

usage: tools/fixture.py fixtures/zero-user.json [rive flags ...]
e.g.   tools/fixture.py fixtures/extreme.json --screenshot=captures/x.png --advance=150

This is the reference "host adapter" for previews: it clamps negative or
non-finite counts to 0, maps "#RRGGBB" colours to ARGB, and writes every value
into the single UserRecap instance before the scene runs.
"""
import json, math, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
fx = json.load(open(sys.argv[1]))
COUNTS = {"conversations", "practiceMinutes", "phrasesSaved", "topicsExplored", "languagesPractised",
          "longestStreakDays", "voiceNotes"}
flags = []
for k, v in fx.items():
    if k in ("currentScreen", "screenProgress", "personaName", "personaDescription", "personaColor"):
        continue  # owned by the state machine / derived in-file from personaIndex
    if k in COUNTS:
        v = v if isinstance(v, (int, float)) and math.isfinite(v) and v > 0 else 0
        v = int(round(v))
    if isinstance(v, bool):
        v = "true" if v else "false"
    if isinstance(v, str) and v.startswith("#") and len(v) == 7:
        v = v[1:]
    flags.append(f"--data={k}={v}")
cmd = [os.path.expanduser("~/.rive/bin/rive"), root] + flags + sys.argv[2:]
sys.exit(subprocess.call(cmd))
