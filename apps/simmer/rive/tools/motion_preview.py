#!/usr/bin/env python3
"""Render motion previews as animated GIFs from headless frames (needs Pillow).

    python3 tools/motion_preview.py handoff   # 2 -> 3 handoff at 30 fps
    python3 tools/motion_preview.py full      # full auto-advance run (3 s dwell) at 4 fps

Each frame is a separate headless run (`--advance=<t>`), so these are exact
renders of the state machine at that time, not screen recordings.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = os.path.expanduser('~/.rive/bin/rive')


def frame(path, args):
    subprocess.run([RIVE, ROOT, f'--screenshot={path}'] + args, capture_output=True)
    im = Image.open(path).convert('RGB')
    return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)


def gif(out, frames, fps):
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True)
    print('wrote', out, len(frames), 'frames')


def handoff():
    tmp = tempfile.mkdtemp()
    frames = []
    for i in range(0, 75):
        ms = int(i * 1000 / 30)
        args = ['--data=currentScreen=2', '--advance=2.8s', '--pointer=click@259,792', f'--advance={max(ms, 16)}ms']
        frames.append(frame(os.path.join(tmp, f'{i:03d}.png'), args))
    gif(os.path.join(ROOT, 'captures', 'motion', 'handoff-2-to-3-30fps.gif'), frames, 30)


def full():
    tmp = tempfile.mkdtemp()
    frames = []
    total = 54.0
    fps = 4
    for i in range(int(total * fps)):
        t = (i + 1) / fps
        frames.append(frame(os.path.join(tmp, f'{i:04d}.png'), ['--data=autoAdvanceSeconds=3', f'--advance={t:.3f}s']))
    gif(os.path.join(ROOT, 'captures', 'motion', 'full-auto-advance-4fps.gif'), frames, fps)


if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'captures', 'motion'), exist_ok=True)
    for what in sys.argv[1:] or ['handoff', 'full']:
        {'handoff': handoff, 'full': full}[what]()
