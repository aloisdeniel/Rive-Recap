# Sprig 2026 recap — Rive implementation

Ten-scene, Wrapped-style houseplant recap for the fictional app **Sprig**, built as plain RML with the Rive CLI 1.6.0.
**No scripts**: the file contains no Luau, so the `.riv` needs no signing and plays in every runtime.

| Path | What |
|---|---|
| `scene.rml` | Editable source (generated, ~41k lines). Artboards `SprigRecap` (390×844, default) and `ShareCard` (330×476 component) |
| `tools/sprig_main.py`, `tools/sprig_scenes*.py`, `tools/build_sprig.py`, `tools/rml.py` | Generator. Edit these and rerun them rather than hand-editing 10 scenes × 8 timelines |
| `build/sprig-recap.riv` | Runtime export (1.48 MB). `build/` is git-ignored, so rebuild with the commands below |
| `assets/fonts/`, `assets/images/paper-grain.png` | Bundled fonts and the single raster grain overlay |
| `captures/` | Headless PNG captures (see the list below) |
| `tools/capture.sh`, `tools/capture_all.sh`, `tools/goto.sh` | Reproducible capture scripts |

## Build, preview and export

```bash
cd apps/sprig/rive
python3 tools/sprig_main.py          # regenerate scene.rml (Pillow is needed only to regenerate the grain PNG)
rive . --verify && rive inspect . --summary   # both clean: 0 errors, problems []
rive .                               # live previewer (window); click/tap or use ←/→/Space
rive . --once && cp build/rive.riv build/sprig-recap.riv
rive . --once --rev=build/sprig-recap.rev     # needs `rive login` (NOT produced, see Limitations)
tools/capture_all.sh                 # regenerate captures/
```

Fixtures: the view model carries three exported instances, `Sample` (the default, matching `sample-data.json`), `NewUser` and `Extreme`.
Headless, override any value with `--data=<property>=<value>`. `capture_all.sh` shows the zero-user and extreme sets.
`SPRIG_FIXTURE=NewUser python3 tools/sprig_main.py` makes another instance the default.

## Architecture

- **One view model, `UserRecap`**, bound to the root artboard. Every scene, and the nested `ShareCard` placement, reads this
  single instance (the nested artboard inherits the data context and keeps no copies). It is deliberately an artboard-bound
  view model rather than Rive's `viewModelType="global"`. The global flavour cannot be driven by `--data`, so runtime
  updates could not be proven headless, and runtimes auto-bind the artboard's instance. It is still the only user-data model in the file.
- **State machine `Recap`** (one machine, 19 layers):
  - `Sequence`: canonical scene states S1–S10. Transitions on `_navNext`/`_navPrev` skip any scene whose `showScreenN` is false, in both directions. Each state fires `screenChanged`, and a listener on that event writes `currentScreen`.
  - `Dwell clock`: settle wait (1.8 s), then 28 timed steps whose blend duration is bound to `autoAdvanceSeconds`. A probe node's x is keyed 0→1 and two-way bound to `screenProgress`. The final step fires `_autoNext`.
  - `Gesture`: distinguishes tap from hold.
  - `Finish latch`: fires `recapFinished` once.
  - `Chrome theme`: ink colour for light versus dark scenes.
  - `Controls`: Continue/Pause swap to Share/Replay on the summary.
  - `Leaf bend`: the signature interaction.
  - `Persona`: four reveal choreographies.
  - `Scene 1`…`Scene 10`: per-scene states Hidden / Enter-forward / Arrive-back / Reduced / Idle / Frozen / Leave-forward / Leave-back / Leave-reduced.
- **Hidden scenes** collapse out of the progress row (`displayValue` bound to `showScreenN`), so the row always shows exactly one segment per visible scene. Intro (1) and summary (10) are always eligible: that is the safe path for invalid visibility input.

## Binding and event contract

All names are on `UserRecap`. "Host" means the app adapter writes the value; "SM" means the state machine writes it, and the host reads it.

| Property | Rive type | Owner | Notes |
|---|---|---|---|
| userName, periodLabel, locale, all `*Headline/*Support/*Unit`, `*Label`, intro/summary/empty/persona copy | String | host | Pre-localized. `locale` is informational: Rive does no locale work itself |
| year, careMoments, plantsNurtured, newLeaves, cuttingsRooted, careStreak, plantsShared, activeMonths | Number | host | Integers. Negatives are clamped to 0 in-file (`max(0,x)`); the adapter must also replace NaN/∞ |
| personaIndex | Number | host | 0–3; any other value falls back to row 0's emblem |
| personaName, personaDescription | String | host | Written **atomically together with** personaIndex and personaColor (see the persona table) |
| personaColor | **Color** (ARGB) | host | Adapter converts `#F6F1DC` to `FFF6F1DC` |
| autoAdvanceSeconds | Number | host | Clamped in-file to 3–60 s |
| autoAdvanceEnabled, isPaused, reducedMotion, soundEnabled | Boolean | host (isPaused also SM) | The Pause button and Space toggle `isPaused`. `soundEnabled` is unused: the file is silent |
| currentScreen | Number | SM | Canonical 1–10 ID, written on every scene entry |
| screenProgress | Number | SM | 0–1 for the current dwell; holds while paused |
| shareIncludeName, shareIncludeSensitiveValues | Boolean | host | Default false. The name line and the period line on the card are hidden unless set |
| showScreen1…showScreen10 | Boolean | host | Hide absent metrics, not genuine zeros |
| groupSeparator | String | host (**adapter addition**) | Thousands separator for count-ups (default `,`; use `.` or a narrow NBSP per locale) |
| `_navNext`, `_navPrev`, `_replay` | Trigger | SM/host | Private plumbing. The host may fire them for its own buttons, setting `_navDir` (+1 or −1) first |
| `_navDir`, `_pressing`, `_pressSide`, `_holdPaused`, `_leafHeld`, `_focusIndex` | Number/Bool | SM | Private (leading underscore). Not user data |

**Events** (reported to the host):

| Event | When |
|---|---|
| `screenChanged` | On each scene entry. Payload: custom number property `index` = canonical scene ID (10 Event objects share the name, each with its own constant index). `currentScreen` holds the same value |
| `shareTapped` | Share button (click, or Enter while focused). The host owns capture and the platform share sheet: **only event wiring is supplied** |
| `recapFinished` | Once, 1.8 s after the summary first settles. It is latched and re-armed only by Replay |

**Persona mapping (adapter)**, written in one update:

| index | personaName | personaDescription | personaColor | emblem / choreography |
|---|---|---|---|---|
| 0 | Canopy Keeper | You made room for a jungle. | FFF6F1DC | layered canopy: three leaf tiers drop and fan out |
| 1 | Propagation Pro | You saw a new beginning in every cutting. | FFA8CC72 | rooted cutting: stem draws up, roots trace down through water |
| 2 | Patient Grower | You gave growth the time it needed. | FFF3AD7D | slow-opening bud (2.5 s bloom) |
| 3 | Windowsill Wanderer | You found possibility in every sunny corner. | FF173E32 | arched window: frame draws on, leaves peek in, accent sun travels |

If the persona is unknown or empty, the host sets `showScreen9=false`. The zero-user fixture does this, so no persona is invented.

**Host-adapter responsibilities:**
- Localize and format all copy.
- Supply `groupSeparator`, convert `personaColor` to ARGB, and sanitize numbers.
- Map persona atomically.
- Set `isPaused=true` while the app is backgrounded or the share sheet is open, then restore the previous value on return.
- Provide screen-reader announcements on `screenChanged`, and an accessible full-precision text equivalent of every value.
- For sharing, render the `ShareCard` artboard on its own, bound to the same instance with `currentScreen=10`, and snapshot it after 1.6 s (or immediately with `reducedMotion=true`). It contains no progress bar and no controls.

## Interaction

- **Tap regions** (y 96–752): the left third goes back, the right two-thirds go forward. Holding for 350 ms or more pauses (`_holdPaused`, progress dims), and releasing after a hold does **not** navigate.
- **Visible controls**: Previous, Continue, and Pause/Play (Share and Replay on the summary). All are at least 48 × 48 px, have `SemanticData` labels bound to the label strings, and a `FocusData` focus ring.
- **Keyboard**: ←/→ navigate, Space pauses, Tab and Shift+Tab move focus, Enter activates the focused button. The file focuses its keyboard surface on start.
- **Signature interaction**: hold the big heart leaf on the intro and it bends toward the pointer (a joystick driving two pose timelines). On release it springs back with an elastic overshoot. Its hit region is `isTargetOpaque`, so it never triggers navigation or a hold-pause, and it is moved off-canvas whenever scene 1 isn't current.
- **Rapid navigation**: every scene layer reacts to `currentScreen` with zero-duration transitions, so interrupted entrances jump straight to leave states. The clock layer uses early exit, so it resets on every navigation. Verified headless: 12 Continue clicks 4 frames apart land cleanly on scene 10 (no overshoot), and taps every 40 frames step exactly one scene each.

## Motion system

- **Per-scene score**: 0–200 ms is an anticipation beat (the vine-tip bud swells). 200–1200 ms reveals the hero, and the number counts up from 0 through a `currentScreen`-gated formula and a cubic `DataConverterInterpolator` (1.15 s, which reduced motion shortens to 20 ms). Headline words cascade in via text modifiers by 1.6 s, then the support line. After that only restrained idle loops run (seamless sine keys), and they freeze while paused (Idle ↔ Frozen states resume where they left off).
- **Signature transition**:
  - The persistent story vine on the right edge grows with `currentScreen`.
  - A leaf-shaped clipping mask unfolds from the vine tip, with a glowing paper edge, while a large folded paper leaf sweeps across the camera (its halves flip mid-flight). This takes 730 ms.
  - Going back uses a different handoff: the mask folds back into the left margin and the leaf sweeps the opposite way, uncovering the previous scene, which re-settles with a parallax drift.
- **Continuity carries**: the opened seed travels from scene 1 to the vine root in scene 2, and the giant folded leaf of scene 4 shrinks into a cutting leaf in scene 5's jar.
- **Hero sequences**:
  - seed opening into a jungle, with the wordmark rising letter by letter (1)
  - droplets sliding onto the vine and becoming leaves (2)
  - pots fanning into a paper landscape (3)
  - one enormous folded leaf opening around the number (4)
  - roots tracing through a translucent jar (5)
  - the vine advancing through 21 calendar knots that light up in sync with the count (6)
  - a cutting passing between paper hands (7)
  - four paper seasons orbiting a persistent plant, with month ticks lit by the count (8)
  - the persona reveal (9)
  - card assembly (10)
- **Reduced motion**: every scene uses a 250 ms opacity fade into its final pose. There is no wipe, camera move or idle loop, and numbers show their final value immediately. All controls stay available.

## Captures (`captures/`)

| Files | What |
|---|---|
| `scene-01…10.png` | Settled scenes |
| `persona-0…3-*.png` | Each persona (copy written with `--data`, as the adapter would) |
| `transition-1to2-f4/14/24/34.png`, `transition-5to6-f10/24.png` | Forward wipe |
| `transition-back-3to2-f8/20/32.png` | Reverse handoff |
| `reduced-motion-*.png` | Reduced motion |
| `zero-user-intro.png`, `zero-user-summary.png` | Intro, then the welcoming empty card |
| `extreme-*.png` | 128,940 values, 52-character name, 40%+ longer copy |
| `hidden-3-4-7-nav.png` | 7 progress segments; navigation skips the hidden scenes |
| `paused-scene1.png` | Paused state |
| `viewport-*.png` | 320×568, 430×932 and desktop 1280×800 with `fit=contain` |

A complete motion preview is not exported: the CLI captures single frames. Run `rive .` to review timing.

## Fonts and licenses

| File | Font | License |
|---|---|---|
| `assets/fonts/Fraunces-Variable.ttf` | Fraunces variable (opsz, wght, SOFT, WONK), google/fonts | SIL OFL 1.1 (`OFL-Fraunces.txt`) |
| `assets/fonts/DMSans-Variable.ttf` | DM Sans variable (opsz, wght), google/fonts | SIL OFL 1.1 (`OFL-DMSans.txt`) |

Both are embedded in the `.riv`. `paper-grain.png` is generated noise (`make_grain()` in `sprig_main.py`), so there are no rights issues.

## Unsupported techniques and substitutions

- **Keyed vertex deformation for unfurling**: replaced by folded two-half leaves, where keyed scaleX on each half hinges on the midrib, plus rotation and back-eased scale.
- **Variable-speed timer, and pause mid-timeline**: an AnimationState's speed can't be bound. Substitute: a 28-step chain whose blend durations are bound. Pause takes effect at the next step boundary, at most dwell/28 (250 ms at 7 s), and resumes from the same progress.
- **Event payloads**: `screenChanged` carries a constant `index` per scene through the Event's custom property. Read `currentScreen` if your runtime doesn't expose payloads.
- **Locale formatting**: there is no in-file locale formatter. Count-ups group thousands with the adapter-supplied `groupSeparator`. Values at or above 1,000,000 show without inner grouping. Large values scale the numeral down in steps instead of overflowing.
- **Responsive reflow**: the master is a fixed 390×844 composition, and smaller or wider screens rely on host `Fit.contain` with a forest letterbox (see the viewport captures). At 320×568 everything scales to 0.67, with body text at about 10.7 px. This is the main layout compromise.
- **Relative bind paths**: the CLI can't author them. All binds are absolute paths into `UserRecap`.

## Measurements

- **`.riv` size**: 1,484,906 bytes. Fonts are about 600 KB and the grain is 580 KB; shrinking the grain or subsetting the fonts would roughly halve the file.
- **Object counts**: SprigRecap has 24,658 objects and ShareCard 882; there are 19 state-machine layers.
- **Frame rate**: not measured. No device or runtime profiler was available in this session. Headless renders of the full scene stack advance about 500 frames in 1.6 s on an M-series Mac.
- **Render budget**: hidden scenes sit in a Hidden state (opacity 0, no idle loops). There is one clip mask per scene and bounded particle counts (5 droplets, 6 bubbles); nothing scales with raw counts.

## Remaining limitations (honest)

- **`.rev` not produced**: `rive . --once --rev=…` returned `Not logged in`. Run `rive login`, then the command above.
- **`recapFinished`/`shareTapped`**: the headless CLI doesn't log fired events. `screenChanged` is proven indirectly, because `currentScreen` is written by its listener. These two are present in the binary but were not observed firing.
- **Entrance freezing**: pause freezes the dwell clock and idle loops, but an entrance that is already playing finishes its ≤1.9 s choreography.
- **Mid-scene data changes**: a host update of the current scene's number re-animates the count. A persona update during scene 9 swaps to the new persona's final pose without replaying its reveal.
- **Untested here**: right-to-left layout, real screen readers, touch hardware, and the web runtime. Hit regions were exercised only with headless pointer clicks. Keyboard was checked with `--key` (Right twice gives scene 3, Space pauses).
- **Copy positions**: some scenes position copy for English plus 40%. Very long headlines in scene 2 run under the vine art (see `extreme-scene2.png`).
