#!/usr/bin/env python3
"""Headless capture + behaviour checks for the Simmer recap.

    python3 tools/capture.py            # everything
    python3 tools/capture.py scenes     # one group: scenes personas reduced transitions fixtures hidden checks
    (the responsive viewport matrix is tools/responsive.py)

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
    shutil.copytree(os.path.join(ROOT, 'scripts'), os.path.join(out, 'scripts'), dirs_exist_ok=True)   # scripts + shaders
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
    # filmstrip of the 2 -> 3 handoff every 100 ms (steam veil, then the simulated tablecloth)
    for ms in range(0, 900, 100):
        shot(f'{CAP}/transitions/filmstrip-2-to-3/{ms:03d}ms.png', '--data=currentScreen=2', f'--advance={SETTLED}',
             '--pointer=click@259,792', f'--advance={max(ms, 16)}ms')
    # filmstrip of the opening: steam condensing into the wordmark
    for ms in range(300, 2100, 200):
        shot(f'{CAP}/transitions/filmstrip-intro-steam-lettering/{ms:04d}ms.png', f'--advance={ms}ms')
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


HARNESS_SIZES = [(0.0, 390, 844), (3.0, 1024, 768), (6.0, 390, 844), (9.0, 1280, 720)]


def harness():
    """A test-only variant: the recap nested in a 'Resize harness' artboard through a
    NestedArtboardLayout whose size is keyed to cross the breakpoint mid-scene
    (390x844 -> 1024x768 at 3 s -> 390x844 at 6 s -> 1280x720 at 9 s). The CLI has no
    live-resize flag, so this is how a host resizing the canvas is reproduced headless.
    Not part of the shipped .riv."""
    import re
    out = variant('fixture.json', 'resize-harness')
    main = open(os.path.join(out, 'scenes', 'main.rml')).read()
    m = re.search(r'<Artboard [^>]*name="Simmer Recap"[^>]*>', main)
    ab_id = re.search(r' id="([^"]+)"', m.group(0)).group(1)
    sm_id = re.search(r'defaultStateMachineId="([^"]+)"', m.group(0)).group(1)
    def keys(prop, idx):
        frames = ''.join(f'<KeyFrameDouble frame="{int(t * 60)}" value="{wh[idx]}" interpolationType="hold"/>' for t, *wh in HARNESS_SIZES)
        return f'<KeyedProperty propertyKey="{prop}">{frames}</KeyedProperty>'
    xml = f'''<!-- test-only resize harness (tools/capture.py harness) -->
<Rive version="1" kind="fragment">
  <Artboard width="1280" height="1024" name="Resize harness" x="0" y="3000" viewModelId="0:10" viewModelInstanceId="0:401"
            clip="true" styleId="0:990002" defaultStateMachineId="0:990010" id="0:990001">
    <LayoutComponentStyle name="Harness style" id="0:990002"/>
    <NestedArtboardLayout artboardId="{ab_id}" instanceWidth="390" instanceHeight="844" name="Recap" id="0:990003">
      <NestedStateMachine animationId="{sm_id}" name="machine" id="0:990004"/>
    </NestedArtboardLayout>
    <LinearAnimation name="Resize" duration="720" loopValue="oneShot" fps="60" id="0:990005">
      <KeyedObject objectId="0:990003">{keys(663, 0)}{keys(664, 1)}</KeyedObject>
    </LinearAnimation>
    <StateMachine name="Harness" id="0:990010">
      <StateMachineLayer name="Resize" id="0:990011">
        <AnyState id="0:990012"/><ExitState id="0:990013"/>
        <EntryState id="0:990014"><StateTransition stateToId="0:990015" duration="0"/></EntryState>
        <AnimationState animationId="0:990005" id="0:990015"/>
      </StateMachineLayer>
    </StateMachine>
  </Artboard>
</Rive>
'''
    with open(os.path.join(out, 'scenes', 'harness.rml'), 'w') as f:
        f.write(xml)
    y = open(os.path.join(out, 'rive.yaml')).read().replace('main: Simmer Recap', 'main: Resize harness')
    with open(os.path.join(out, 'rive.yaml'), 'w') as f:
        f.write(y)
    return out


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

    # ---- responsive: orientation follows the real width; input uses the real width
    O = K[:3] + ['stageWidth', 'stageHeight', 'isLandscape', 'layoutBreakpoint', 'layoutCopyScale', 'layoutStack']
    for vp in ('390x844', '767x1024', '768x1024', '740x360', '1280x720', '2560x1080'):
        rec(f'orientation at {vp}', *dump(f'orientation-{vp}', f'--viewport={vp}', '--advance=500ms'), O)
    rec('layoutBreakpoint=1300 keeps 1280x720 portrait', *dump('breakpoint-1300', '--viewport=1280x720', '--data=layoutBreakpoint=1300', '--advance=500ms'), O)
    rec('layoutBreakpoint=320 makes 390x844 landscape', *dump('breakpoint-320', '--viewport=390x844', '--data=layoutBreakpoint=320', '--advance=500ms'), O)
    # 1280 wide: the left third ends at 426.7
    rec('1280x720 tap at x=400 goes back (4 -> 3)', *dump('wide-tap-back', '--viewport=1280x720', '--data=currentScreen=4', '--advance=1s',
                                                          '--pointer=click@400,360', '--advance=200ms'), O)
    rec('1280x720 tap at x=460 goes forward (4 -> 5)', *dump('wide-tap-next', '--viewport=1280x720', '--data=currentScreen=4', '--advance=1s',
                                                            '--pointer=click@460,360', '--advance=200ms'), O)
    rec('1280x720 hold pauses, release does not tap', *dump('wide-hold', '--viewport=1280x720', '--advance=3s', '--pointer=down@900,360',
                                                         '--advance=600ms', '--pointer=up@900,360', '--advance=200ms'), O)
    rec('1920x1080 keyboard right x2', *dump('wide-keys', '--viewport=1920x1080', '--advance=500ms', '--key=right', '--advance=100ms',
                                             '--key=right', '--advance=200ms'), O)
    rec('1280x720 Continue button (right edge)', *dump('wide-continue', '--viewport=1280x720', '--advance=1s', '--pointer=click@1100,669',
                                                       '--advance=200ms'), O)
    rec('320x568 Previous button', *dump('narrow-prev', '--viewport=320x568', '--data=currentScreen=3', '--advance=1s',
                                         '--pointer=click@46,520', '--advance=200ms'), O)
    # ---- resize across the breakpoint mid-scene (test harness, see harness())
    hz = harness()
    R = O + ['motifFrameX', 'motifFrameY', 'motifFrameScale']
    for t, label in (('2.5s', 'before (390x844)'), ('3.2s', 'just after resize to 1024x768'), ('5s', 'settled at 1024x768'),
                     ('6.5s', 'back to 390x844'), ('10s', 'then 1280x720')):
        rec(f'resize mid-scene 4: {label}', *dump(f'resize-{t}', '--data=currentScreen=4', '--data=autoAdvanceEnabled=false', f'--advance={t}', project=hz), R)
    # a resize while the handoff is running (navigate at 2.8 s, resize at 3 s): settles on the new scene
    rec('resize during handoff 4 -> 5, settled', *dump('resize-during-handoff', '--data=currentScreen=4', '--data=autoAdvanceEnabled=false',
                                                       '--advance=2.8s', '--key=right', '--advance=2.2s', project=hz), R)
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
