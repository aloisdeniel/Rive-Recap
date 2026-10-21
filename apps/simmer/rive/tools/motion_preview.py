#!/usr/bin/env python3
"""Render motion previews as WebM clips from headless frames (needs ffmpeg).

    python3 tools/motion_preview.py              # every clip
    python3 tools/motion_preview.py handoff back intro persona

Each frame is a separate headless run (`--advance=<t>`), so these are exact
renders of the state machines at that time, not screen recordings. The full
walkthrough is apps/simmer/video.webm (scripts/render-video.py simmer).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = shutil.which('rive') or os.path.expanduser('~/.rive/bin/rive')
OUT = os.path.join(ROOT, 'captures', 'motion')
FPS = 30


def clip(name, frame_args, n, jobs=3):
    tmp = tempfile.mkdtemp()

    def one(i):
        path = os.path.join(tmp, f'f{i:04d}.png')
        subprocess.run([RIVE, ROOT, '--quiet', f'--screenshot={path}', '--data=autoAdvanceEnabled=false'] + frame_args(i),
                       capture_output=True)
    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(one, range(n)))
    out = os.path.join(OUT, name + '.webm')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                    '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '24', '-pix_fmt', 'yuv420p', '-an', out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print('wrote', os.path.relpath(out, ROOT), n, 'frames')


def ms(i):
    return max(16, int(i * 1000 / FPS))


def handoff():
    # forward handoff 2 -> 3: steam ribbon veils the cut, then the tablecloth pull
    clip('handoff-forward-2-to-3', lambda i: ['--data=currentScreen=2', '--advance=2.8s', '--key=right', f'--advance={ms(i)}ms'], 45)


def back():
    # back handoff 5 -> 4: the mirrored version
    clip('handoff-back-5-to-4', lambda i: ['--data=currentScreen=5', '--advance=2.8s', '--key=left', f'--advance={ms(i)}ms'], 45)


def intro():
    # scene 1: the lid pops, steam rises and condenses into the wordmark, then evaporates into ink
    clip('intro-steam-lettering', lambda i: [f'--advance={ms(i)}ms'], 75)


def persona():
    # 8 -> 9: handoff, the pot rattles and dissolves into the persona emblem
    clip('persona-reveal-8-to-9', lambda i: ['--data=currentScreen=8', '--advance=2.8s', '--key=right', f'--advance={ms(i)}ms'], 84)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    todo = sys.argv[1:] or ['handoff', 'back', 'intro', 'persona']
    for what in todo:
        {'handoff': handoff, 'back': back, 'intro': intro, 'persona': persona}[what]()
