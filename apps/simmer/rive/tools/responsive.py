#!/usr/bin/env python3
"""Responsive captures: the viewport matrix as contact sheets (needs ffmpeg).

    python3 tools/responsive.py                 # every sheet
    python3 tools/responsive.py 1 2 9 10 mid    # some sheets (scene numbers, 'mid', 'fixtures')
    python3 tools/responsive.py --jobs 2

Each frame is a headless render at that viewport with the CLI's default
--fit=layout, so the artboard is resized to the viewport exactly as a host's
layout fit would. Frames go to build/responsive/, sheets to
captures/responsive/<name>.png (portrait sizes on the top row, landscape on
the bottom row, each labelled with its size).
"""
import os
import shutil
import struct
import subprocess
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = shutil.which('rive') or os.path.expanduser('~/.rive/bin/rive')
FRAMES = os.path.join(ROOT, 'build', 'responsive')
OUT = os.path.join(ROOT, 'captures', 'responsive')

PORTRAIT = ['320x568', '360x640', '390x844', '430x932', '600x960', '767x1024', '667x375', '740x360']
LANDSCAPE = ['768x1024', '820x1180', '1024x768', '1280x720', '1440x900', '1920x1080', '2560x1080', '1366x600']
SETTLED = '2.8s'
BASE = ['--data=autoAdvanceEnabled=false']

# name -> extra args (after the viewport)
SHEETS = {f'scene-{k:02d}': [f'--data=currentScreen={k}', f'--advance={SETTLED}'] for k in range(1, 11)}
SHEETS['mid-transition-2-to-3-300ms'] = ['--data=currentScreen=2', f'--advance={SETTLED}', '--key=right', '--advance=300ms']
SHEETS['mid-transition-2-to-3-560ms'] = ['--data=currentScreen=2', f'--advance={SETTLED}', '--key=right', '--advance=560ms']
SHEETS['mid-transition-back-6-to-5-400ms'] = ['--data=currentScreen=6', f'--advance={SETTLED}', '--key=left', '--advance=400ms']
SHEETS['persona-3'] = ['--data=currentScreen=9', '--data=personaIndex=3', f'--advance={SETTLED}']
SHEETS['reduced-motion-scene-04'] = ['--data=currentScreen=4', '--data=reducedMotion=true', '--advance=400ms']
# fixtures (variant projects built by `tools/capture.py fixtures`): long copy / huge values, and the new user
VARIANT = {}
for k in (2, 7, 9, 10):
    SHEETS[f'extreme-scene-{k:02d}'] = [f'--data=currentScreen={k}', f'--advance={SETTLED}']
    VARIANT[f'extreme-scene-{k:02d}'] = 'extreme'
SHEETS['new-user-summary'] = [f'--advance={SETTLED}', '--key=right', f'--advance={SETTLED}']
VARIANT['new-user-summary'] = 'new-user'


# ---------------------------------------------------------------- tiny PNG label writer (no PIL here)
GLYPHS = {
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    'x': ['00000', '00000', '10001', '01010', '00100', '01010', '10001'],
    ' ': ['00000'] * 7,
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
}


def label_png(path, text, width, height=30, scale=3):
    rows = [[(251, 240, 214)] * width for _ in range(height)]
    x0 = 8
    y0 = (height - 7 * scale) // 2
    for ch in text:
        g = GLYPHS.get(ch, GLYPHS[' '])
        for gy, line in enumerate(g):
            for gx, bit in enumerate(line):
                if bit == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            x, y = x0 + gx * scale + dx, y0 + gy * scale + dy
                            if 0 <= x < width and 0 <= y < height:
                                rows[y][x] = (72, 41, 61)
        x0 += 6 * scale
    raw = b''.join(b'\x00' + bytes([c for px in r for c in px]) for r in rows)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) \
        + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


# ---------------------------------------------------------------- rendering
def render(path, vp, args, project=ROOT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [RIVE, project, '--quiet', f'--screenshot={path}', f'--viewport={vp}'] + BASE + list(args)
    for _ in range(2):
        if subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(path):
            return True
    print('FAILED', ' '.join(cmd))
    return False


CELL = 300      # each frame is fitted into a CELL x CELL box


def sheet(name, frames):
    """frames: list of (label, png) in matrix order; writes captures/responsive/<name>.png."""
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(FRAMES, '_labels')
    os.makedirs(tmp, exist_ok=True)
    inputs, filters, cells = [], [], []
    for i, (lab, png) in enumerate(frames):
        lp = os.path.join(tmp, f'{lab}.png')
        if not os.path.exists(lp):
            label_png(lp, lab, CELL)
        inputs += ['-i', png, '-i', lp]
        filters.append(f'[{2 * i}]scale={CELL}:{CELL}:force_original_aspect_ratio=decrease,'
                       f'pad={CELL}:{CELL}:(ow-iw)/2:(oh-ih)/2:color=0xD9CCB0[f{i}];[f{i}][{2 * i + 1}]vstack[c{i}]')
        cells.append(f'[c{i}]')
    n = len(frames)
    half = n // 2
    filters.append(''.join(cells[:half]) + f'hstack={half}[top]')
    filters.append(''.join(cells[half:]) + f'hstack={n - half}[bot]')
    filters.append('[top][bot]vstack')
    out = os.path.join(OUT, f'{name}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + inputs + ['-filter_complex', ';'.join(filters), '-frames:v', '1', out], check=True)
    return out


def main():
    argv = sys.argv[1:]
    jobs = 2
    if '--jobs' in argv:
        i = argv.index('--jobs')
        jobs = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = []
    for a in argv:
        if a.isdigit():
            names.append(f'scene-{int(a):02d}')
        elif a == 'mid':
            names += [n for n in SHEETS if n.startswith('mid-')]
        elif a == 'fixtures':
            names += list(VARIANT)
        else:
            names.append(a)
    names = names or list(SHEETS)
    todo = [(n, vp) for n in names for vp in PORTRAIT + LANDSCAPE]

    def job(t):
        n, vp = t
        proj = os.path.join(ROOT, 'build', 'variants', VARIANT[n]) if n in VARIANT else ROOT
        return render(os.path.join(FRAMES, n, f'{vp}.png'), vp, SHEETS[n], project=proj)

    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(job, todo))
    for n in names:
        frames = [(('P ' if vp in PORTRAIT else 'L ') + vp, os.path.join(FRAMES, n, f'{vp}.png')) for vp in PORTRAIT + LANDSCAPE]
        print(sheet(n, frames))


if __name__ == '__main__':
    main()
