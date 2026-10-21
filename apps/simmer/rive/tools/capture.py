#!/usr/bin/env python3
"""Headless capture + behaviour checks for the Simmer recap.

    python3 tools/capture.py            # everything
    python3 tools/capture.py scenes     # one group: scenes personas reduced transitions fixtures hidden checks

Writes PNGs under captures/ and JSON evidence under captures/checks/.
Variant fixtures (new user, extreme) are built into build/variants/<name>/
with that fixture as the default UserRecap instance.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = os.path.expanduser('~/.rive/bin/rive')
CAP = os.path.join(ROOT, 'captures')


def run(args, project=ROOT, quiet=True):
    cmd = [RIVE, project] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('FAILED', ' '.join(cmd), r.stderr[-800:])
    return r


def shot(path, *args, project=ROOT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return run([f'--screenshot={path}'] + list(args), project=project)


def variant(fixture, name):
    out = os.path.join(ROOT, 'build', 'variants', name)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    subprocess.run([sys.executable, os.path.join(HERE, 'build.py'), f'--first={fixture}', f'--out={out}'], check=True, capture_output=True)
    shutil.copy(os.path.join(ROOT, 'rive.yaml'), out)
    shutil.copytree(os.path.join(ROOT, 'scripts'), os.path.join(out, 'scripts'))
    os.symlink(os.path.join(ROOT, 'assets'), os.path.join(out, 'assets'))
    return out


SETTLED = '2.8s'


def scenes():
    for k in range(1, 11):
        shot(f'{CAP}/settled/scene-{k:02d}.png', f'--data=currentScreen={k}', f'--advance={SETTLED}')


def personas():
    for p in range(4):
        shot(f'{CAP}/personas/persona-{p}.png', '--data=currentScreen=9', f'--data=personaIndex={p}', '--advance=3.2s')
        shot(f'{CAP}/personas/persona-{p}-reveal-1000ms.png', '--data=currentScreen=9', f'--data=personaIndex={p}', '--advance=1.0s')
    shot(f'{CAP}/personas/persona-unknown-index-7.png', '--data=currentScreen=9', '--data=personaIndex=7', '--advance=3.2s')


def reduced():
    for k in (1, 2, 4, 9, 10):
        shot(f'{CAP}/reduced-motion/scene-{k:02d}-at-300ms.png', '--data=reducedMotion=true', f'--data=currentScreen={k}', '--advance=300ms')
    shot(f'{CAP}/reduced-motion/nav-2-to-3-at-100ms.png', '--data=reducedMotion=true', '--data=currentScreen=2', '--advance=1s',
         '--pointer=click@259,792', '--advance=100ms')


def transitions():
    # one intermediate frame per forward handoff (300 ms and 520 ms into it)
    for k in range(1, 10):
        for ms in (300, 520):
            shot(f'{CAP}/transitions/forward-{k:02d}-to-{k + 1:02d}-{ms}ms.png', f'--data=currentScreen={k}', f'--advance={SETTLED}',
                 '--pointer=click@259,792', f'--advance={ms}ms')
    for k in (3, 7, 10):
        shot(f'{CAP}/transitions/back-{k:02d}-to-{k - 1:02d}-400ms.png', f'--data=currentScreen={k}', f'--advance={SETTLED}',
             '--pointer=click@50,792', f'--advance=400ms')
    # filmstrip of the 2 -> 3 handoff every 100 ms
    for ms in range(0, 900, 100):
        shot(f'{CAP}/transitions/filmstrip-2-to-3/{ms:03d}ms.png', '--data=currentScreen=2', f'--advance={SETTLED}',
             '--pointer=click@259,792', f'--advance={max(ms, 16)}ms')
    # the pot tap delight (distinct hit region; must not navigate)
    shot(f'{CAP}/transitions/pot-tap-250ms.png', '--data=currentScreen=2', f'--advance={SETTLED}', '--pointer=click@195,680', '--advance=250ms')


def fixtures():
    nu = variant('new-user.json', 'new-user')
    shot(f'{CAP}/fixtures/new-user-intro.png', f'--advance={SETTLED}', project=nu)
    shot(f'{CAP}/fixtures/new-user-summary.png', f'--advance={SETTLED}', '--pointer=click@259,792', f'--advance={SETTLED}', project=nu)
    ex = variant('extreme.json', 'extreme')
    for k in (1, 2, 3, 6, 7, 9, 10):
        shot(f'{CAP}/fixtures/extreme-scene-{k:02d}.png', f'--data=currentScreen={k}', f'--advance={SETTLED}', project=ex)
    shot(f'{CAP}/fixtures/extreme-summary-name-and-recipe-shared.png', '--data=currentScreen=10', '--data=shareIncludeName=true',
         '--data=shareIncludeSensitiveValues=true', f'--advance={SETTLED}', project=ex)
    # runtime data update on the default fixture: the same file, different bound numbers
    shot(f'{CAP}/fixtures/runtime-update-meals-4321.png', '--data=currentScreen=2', '--data=mealsCooked=4321', f'--advance={SETTLED}')
    shot(f'{CAP}/fixtures/locale-fr-FR-12345.png', '--data=currentScreen=2', '--data=mealsCooked=12345', '--data=locale=fr-FR', f'--advance={SETTLED}')


def hidden():
    shot(f'{CAP}/hidden/hide-4-and-7-scene-5.png', '--data=showScreen4=false', '--data=showScreen7=false', '--data=currentScreen=5', f'--advance={SETTLED}')
    shot(f'{CAP}/hidden/hide-4-next-from-3-lands-on-5.png', '--data=showScreen4=false', '--data=currentScreen=3', f'--advance={SETTLED}',
         '--pointer=click@259,792', f'--advance={SETTLED}')


def dump(name, *args, project=ROOT):
    path = f'{CAP}/checks/{name}.json'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = run([f'--data-dump={path}'] + list(args), project=project)
    with open(path) as f:
        d = json.load(f)
    vals = {p['name']: p.get('value') for p in d['viewModel']['properties']}
    events = [ln.split('event: ')[1] for ln in r.stdout.splitlines() + r.stderr.splitlines() if 'console' not in ln and ln.startswith('event: ')]
    return vals, events


def checks():
    report = {}

    def rec(name, vals, events, keys):
        report[name] = {'values': {k: vals.get(k) for k in keys}, 'events': events}

    K = ['currentScreen', 'currentSegment', 'visibleCount', 'screenProgress', 'isPaused', 'recapComplete', 'navDirection', 'focusedControl', 'isSharing']
    rec('boot', *dump('boot', '--advance=1s'), K)
    rec('next x1 (tap right two-thirds)', *dump('tap-next', '--advance=1s', '--pointer=click@300,400', '--advance=200ms'), K)
    rec('back (tap left third)', *dump('tap-back', '--data=currentScreen=4', '--advance=1s', '--pointer=click@60,400', '--advance=200ms'), K)
    rapid = ['--advance=500ms'] + sum([['--pointer=click@300,400', '--pointer=move@300,300'] for _ in range(6)], []) + ['--advance=3s']
    rec('rapid x6 taps', *dump('rapid', *rapid), K)
    hold = ['--advance=3s', '--pointer=down@300,400', '--advance=600ms']
    rec('hold (pressed 600 ms)', *dump('hold-down', *hold), K)
    rec('hold released (no tap)', *dump('hold-up', *hold, '--pointer=up@300,400', '--advance=200ms'), K)
    rec('pause button', *dump('pause', '--advance=3s', '--pointer=click@112,792', '--advance=10s'), K)
    rec('pause then resume', *dump('resume', '--advance=3s', '--pointer=click@112,792', '--advance=2s', '--pointer=move@300,300',
                                   '--pointer=click@112,792', '--advance=1s'), K)
    rec('keyboard right x2, left x1', *dump('keys', '--advance=500ms', '--key=right', '--advance=100ms', '--key=right', '--advance=100ms', '--key=left', '--advance=200ms'), K)
    rec('keyboard space pauses', *dump('key-space', '--advance=500ms', '--key=space', '--advance=200ms'), K)
    rec('keyboard tab focus + enter (prev)', *dump('key-tab', '--data=currentScreen=3', '--advance=500ms', '--key=tab', '--key=enter', '--advance=200ms'), K)
    rec('auto-advance full run (3 s dwell)', *dump('auto', '--data=autoAdvanceSeconds=3', '--advance=60s'), K)
    rec('auto-advance clamps 0.5 s to 3 s (after 4 s)', *dump('clamp', '--data=autoAdvanceSeconds=0.5', '--advance=4s'), K)
    rec('autoAdvanceEnabled=false (30 s)', *dump('no-auto', '--data=autoAdvanceEnabled=false', '--advance=30s'), K)
    rec('share tapped on summary', *dump('share', '--data=currentScreen=10', '--advance=3s', '--pointer=click@205,792', '--advance=200ms'), K)
    rec('replay from summary', *dump('replay', '--data=currentScreen=10', '--advance=3s', '--pointer=click@318,792', '--advance=500ms'), K)
    rec('hidden 4 & 7: next from 3', *dump('hidden', '--data=showScreen4=false', '--data=showScreen7=false', '--data=currentScreen=3',
                                           '--advance=1s', '--key=right', '--advance=200ms'), K)
    rec('pot tap does not navigate', *dump('pot', '--data=currentScreen=2', '--advance=1s', '--pointer=click@195,680', '--advance=200ms'), K)
    rec('negative count clamps', *dump('negative', '--data=sharedMeals=-4', '--advance=200ms'), K + ['sharedMeals'])
    rec('unknown persona index', *dump('persona', '--data=personaIndex=7', '--advance=200ms'), K + ['personaIndex', 'personaName'])
    with open(f'{CAP}/checks/report.json', 'w') as f:
        json.dump(report, f, indent=2)
    for k, v in report.items():
        print(f'{k:45s} {json.dumps(v["values"])}  events={v["events"]}')


GROUPS = dict(scenes=scenes, personas=personas, reduced=reduced, transitions=transitions, fixtures=fixtures, hidden=hidden, checks=checks)

if __name__ == '__main__':
    todo = sys.argv[1:] or list(GROUPS)
    for g in todo:
        print('==', g)
        GROUPS[g]()
