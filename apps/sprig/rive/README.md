# Sprig 2026 recap — Rive implementation

Ten-scene, Wrapped-style houseplant recap for the fictional app **Sprig**, built as RML with the Rive CLI 1.6.0.
**Since the improvement pass the file carries Luau scripts and WGSL shaders** (`scripts/`): a GPU folded-paper leaf, a
paper/canopy-light shader and the dwell clock. Native runtimes and the CLI previewer play the unsigned build; **web hosts
need a signed build** (`rive . --publish`, requires `rive login`, not produced here). See [Improvement pass](#improvement-pass).

| Path | What |
|---|---|
| `scene.rml` | Editable source (generated, ~84k lines). Artboards `SprigRecap` (designed at 390×844, laid out at any size, default) and `ShareCard` (330×476 component) |
| `tools/sprig_main.py`, `tools/sprig_scenes*.py`, `tools/build_sprig.py`, `tools/rml.py` | Generator. Edit these and rerun them rather than hand-editing 10 scenes × 8 timelines |
| `tools/layout.py`, `tools/resp.py` | Responsive layout: chrome bands and per-scene placements as expressions, compiled to formula converters or to the generated solver (see [Responsive layout](#responsive-layout)) |
| `scripts/viewport.luau`, `scripts/layoutsolve.luau` | Viewport probe (`ScriptedLayout`) and the layout solver it runs (**generated** by `tools/resp.py`, do not edit) |
| `scripts/paperleaf.luau` + `.wgsl` | Lit 3D folded-paper leaf / seed half-shell (transition sweep, scene 1–2 seed, scene 4 giant leaves, scene 9 cradle) |
| `scripts/canopylight.luau` + `.wgsl` | Paper stock + light falling through a canopy, over every scene |
| `scripts/dwellclock.luau` | Owns `screenProgress` and the auto-advance (exact pause) |
| `build/sprig-recap.riv` | Runtime export (1.37 MB, unsigned). `build/` is git-ignored except this file |
| `assets/fonts/` | Bundled fonts (no raster assets remain) |
| `captures/` | Headless PNG captures (see the list below); the full walkthrough is `../video.webm` |
| `tools/capture.sh`, `tools/capture_all.sh`, `tools/goto.sh` | Reproducible capture scripts (`goto.sh` frames count from the last click) |
| `tools/check.py`, `tools/harness/` | Headless behaviour checks (19: 14 at 390×844, 5 responsive), see [Checks](#checks) |
| `tools/responsive.py` | Renders the viewport matrix into `captures/responsive/` contact sheets |

## Build, preview and export

```bash
cd apps/sprig/rive
python3 tools/sprig_main.py          # regenerate scene.rml
rive . --verify && rive inspect . --summary   # both clean: 0 errors, problems []
rive .                               # live previewer (window); click/tap or use ←/→/Space
rive . --once && cp build/rive.riv build/sprig-recap.riv
rive . --once --rev=build/sprig-recap.rev     # needs `rive login` (NOT produced, see Limitations)
tools/capture_all.sh                 # regenerate captures/ (removes stale PNGs first)
python3 tools/check.py               # 19 headless behaviour checks (incl. a mid-scene resize)
python3 tools/responsive.py --mid    # viewport matrix -> captures/responsive/*.png
(cd ../../.. && scripts/render-video.py sprig --jobs 2)   # walkthrough -> apps/sprig/video.webm (390x844)
(cd ../../.. && scripts/render-video.py sprig --jobs 2 --viewport 1280x720 --output apps/sprig/video-landscape.webm)
```

Fixtures: the view model carries three exported instances, `Sample` (the default, matching `sample-data.json`), `NewUser` and `Extreme`.
Headless, override any value with `--data=<property>=<value>`. `capture_all.sh` shows the zero-user and extreme sets.
`SPRIG_FIXTURE=NewUser python3 tools/sprig_main.py` makes another instance the default.

## Architecture

- **One view model, `UserRecap`**, bound to the root artboard. Every scene, and the nested `ShareCard` placement, reads this
  single instance (the nested artboard inherits the data context and keeps no copies). It is deliberately an artboard-bound
  view model rather than Rive's `viewModelType="global"`. The global flavour cannot be driven by `--data`, so runtime
  updates could not be proven headless, and runtimes auto-bind the artboard's instance. It is still the only user-data model in the file.
- **State machine `Recap`** (one machine, 18 layers):
  - `Sequence`: canonical scene states S1–S10. Transitions on `_navNext`/`_navPrev` skip any scene whose `showScreenN` is false, in both directions. Each state fires `screenChanged`, and a listener on that event writes `currentScreen`.
  - (Dwell clock: since the improvement pass this is `scripts/dwellclock.luau`, a draw-less `ScriptedDrawable`. It waits 1.8 s after each `currentScreen` change, then advances `screenProgress` over `autoAdvanceSeconds` (clamped 3–60 s, non-finite → 7), freezes on the exact frame `isPaused`/`_holdPaused` turns true, and at 1.0 writes `_navDir=1` and fires `_navNext` once.)
  - `Gesture`: distinguishes tap from hold.
  - `Finish latch`: fires `recapFinished` once.
  - `Chrome theme`: ink colour for light versus dark scenes.
  - `Controls`: Continue/Pause swap to Share/Replay on the summary.
  - `Leaf bend`: the signature interaction.
  - `Persona`: four reveal choreographies.
  - `Scene 1`…`Scene 10`: per-scene states Hidden / Enter-forward / Arrive-back / Reduced / Idle / Frozen / Leave-forward / Leave-back / Leave-reduced.
- **Hidden scenes** collapse out of the progress row (`displayValue` bound to `showScreenN`), so the row always shows exactly one segment per visible scene. Intro (1) and summary (10) are always eligible: that is the safe path for invalid visibility input.

## Binding and event contract

All names are on `UserRecap`. "Host" means the app adapter writes the value; "SM" means the file writes it (state machine, or for `screenProgress` the dwell-clock script), and the host reads it. Names, types and events are unchanged by the improvement pass.

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
| screenProgress | Number | SM (script) | 0–1 for the current dwell; freezes on the exact frame of a pause; 0 on the summary |
| shareIncludeName, shareIncludeSensitiveValues | Boolean | host | Default false. The name line and the period line on the card are hidden unless set |
| showScreen1…showScreen10 | Boolean | host | Hide absent metrics, not genuine zeros |
| groupSeparator | String | host (**adapter addition**) | Thousands separator for count-ups (default `,`; use `.` or a narrow NBSP per locale) |
| layoutBreakpoint | Number | host (**contract addition**, optional) | Width in points at which the landscape layout takes over (default **768**: landscape when the artboard width ≥ 768). Non-finite or ≤ 0 falls back to 768. May change at any time; the scene re-lays out at once |
| `_navNext`, `_navPrev`, `_replay` | Trigger | SM/host | Private plumbing. The host may fire them for its own buttons, setting `_navDir` (+1 or −1) first |
| `_navDir`, `_pressing`, `_pressSide`, `_holdPaused`, `_leafHeld`, `_focusIndex` | Number/Bool | SM | Private (leading underscore). Not user data |
| `_vw`, `_vh`, `_dpr`, `_landscape`, `_tall`, `_rpt`/`_rpw`/`_rlw`/`_rlt`, `_ch1…_ch10`, `_l…` (147) | Number/Bool | file (scripts) | Private responsive-layout state, see [Responsive layout](#responsive-layout). Hosts never write them; `_landscape` is safe to read |

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

- **Tap regions** (between the top band and the controls; y 96–752 at 390×844): the left third of the **real width** goes back, the right two-thirds go forward. Holding for 350 ms or more pauses (`_holdPaused`, progress dims), and releasing after a hold does **not** navigate.
- **Visible controls**: Previous, Continue, and Pause/Play (Share and Replay on the summary). All are at least 48 × 48 px, have `SemanticData` labels bound to the label strings, and a `FocusData` focus ring.
- **Keyboard**: ←/→ navigate, Space pauses, Tab and Shift+Tab move focus, Enter activates the focused button. The file focuses its keyboard surface on start.
- **Signature interaction**: hold the big heart leaf on the intro and it bends toward the pointer (a joystick driving two pose timelines). On release it springs back with an elastic overshoot. Its hit region is `isTargetOpaque`, so it never triggers navigation or a hold-pause, and it is moved off-canvas whenever scene 1 isn't current.
- **Rapid navigation**: every scene layer reacts to `currentScreen` with zero-duration transitions, so interrupted entrances jump straight to leave states. The dwell clock restarts on every `currentScreen` change. Verified headless: 12 Continue clicks 4 frames apart land cleanly on scene 10 (no overshoot), and taps every 40 frames step exactly one scene each.

## Motion system

- **Per-scene score**: 0–200 ms is an anticipation beat (the vine-tip bud swells; scene 4's closed paper bud shivers;
  scene 1/9 seeds squash). 200–1200 ms reveals the hero, and the number counts up from 0 through a `currentScreen`-gated
  formula and a cubic `DataConverterInterpolator` (1.15 s); a following formula snaps to the final value under reduced
  motion. Headline words cascade in via text modifiers by 1.6 s, then the support line. After that only restrained idle
  loops run (seamless sine keys), and they freeze while paused (Idle ↔ Frozen states resume where they left off).
- **Signature transition** (≈750 ms forward, ≈700 ms back; see [Improvement pass](#improvement-pass)):
  - The persistent story vine on the right edge grows with `currentScreen`; its tip buds (anticipation).
  - From the tip a second vine races round the screen edge in both directions, sprouting leaves, and **becomes the frame**
    the next scene arrives in, then lets go.
  - Inside the frame a leaf-shaped clipping mask unfolds from the tip with a glowing paper edge, while a **real 3D paper
    leaf** (GPU) folds across the camera: it enters folded, opens, flips over its midrib (green face → cream underside),
    curls toward the lens and casts a soft shadow. The outgoing scene recedes a little (camera pull-back).
  - Going back: the frame **unweaves** into the vine tip, the 3D leaf sweeps the other way inner face first, the mask folds
    back into the left margin, the closing scene is pushed toward the camera and the previous one re-settles with a
    parallax drift.
- **Continuity carries**: the opened 3D seed travels from scene 1 to the vine root in scene 2, and a leaf from scene 4's
  canopy swoops into scene 5's jar as a cutting leaf.
- **Hero sequences**:
  - a closed 3D paper seed squashes, cracks and falls open; a jungle **unfurls** out of it (vertex-deformed leaves) and the
    wordmark rises letter by letter (1)
  - droplets slide onto a drawing vine and merge into leaves that uncurl from fiddleheads (2)
  - pots fan out onto three sheets of green paper landscape (3)
  - a giant 3D folded-paper bud shivers, then falls open, twisting its cream inner faces out around a sunrise diorama (4)
  - roots trace through a translucent jar (5)
  - the vine advances through 21 calendar knots that light up in sync with the count (6)
  - a cutting is passed between two large paper hands toward a windowsill (7)
  - four paper seasons orbit a persistent plant, with month ticks lit by the count (8)
  - the persona reveal: a 3D seed swells and opens into a cradle, the arch rises out of it, pothos strands unroll inside,
    then the persona's own emblem choreography (9)
  - card assembly (10)
- **Reduced motion**: every scene uses a 250 ms opacity fade into its final pose. There is no wipe, frame vine, 3D sweep,
  camera move or idle loop (the canopy light is frozen), and numbers show their final value immediately. All controls
  stay available.

## Responsive layout

The artboard is designed at 390×844 but is laid out at whatever size the host gives it. There are **two layouts,
chosen by a pure width breakpoint**, and each adapts continuously to every size on its side of the threshold.

### The rule

- **Landscape layout when the artboard width ≥ `layoutBreakpoint`** (a new `UserRecap` number, default **768**),
  otherwise the **portrait layout**. Height plays no part in the choice: 768×1024 and 820×1180 get the landscape layout,
  667×375 and 740×360 the portrait one.
- The orientation is derived from the **actual artboard width at runtime** and re-derived on every resize and on every
  change of `layoutBreakpoint`, including mid-scene: the current scene, its progress and its state are kept, and only
  the placement changes on the next frame (checked headless, below). `_landscape` is readable by the host.
- Inside each layout, an aspect switch (`_tall`: height ≥ 1.1 × width) picks one of two arrangements, so the
  portrait layout also works on a phone on its side and the landscape layout on a tablet held upright.

| | Portrait layout (width < breakpoint) | Landscape layout (width ≥ breakpoint) |
|---|---|---|
| Chrome | Wordmark, year and the progress row across the top; Previous / Continue / Pause along the bottom (short canvases: a cluster under the art) | Wordmark, year and a full-width progress row; Previous / Pause / Continue as a cluster at the bottom right, under the copy |
| Tall canvas | The 390×844 composition: number and copy on top (text scale 0.78–1.3), hero art below, bottom-anchored and fitted to the space left. **390×844 is the identity case** | Number and copy side by side in a row (number left, copy column right), the hero art below at up to 2.2× |
| Wide canvas | Copy column left (the number above it), hero art right, compact chrome | **Hero art left, the big number and the copy column right**, type up to 2.1× (2.6–2.8× for the intro, persona and summary), copy vertically centred |
| Persona (9) | Label, name and line over the arch stage, which now sits clear of the controls | Arch stage, cradle and pothos left; label, a large persona name and the line right |
| Summary (10) | Headline over the share card | The share card left at up to 1.8×, headline and support right, Share / Replay under them |

Everywhere: backgrounds are sized to the viewport (with room for the 0.94 camera recede), the ground (hills, the
paper terraces of scene 3, scene 7's floor) is stretched to the full width, corner foliage stays glued to its corner,
the progress row spans the real width (one flex segment per visible scene), the tap zones and hold-to-pause cover the
real width, text columns re-wrap at their new width, and controls are 52 pt (×1–1.35 in landscape).

### Mechanism

1. **Viewport probe** (`scripts/viewport.luau`): a `ScriptedLayout` in a fill-sized root `LayoutComponent`, so its
   `resize(size, scale)` receives the artboard's real size and the device pixel ratio. It writes private `UserRecap`
   numbers: `_vw`, `_vh`, `_dpr`, `_landscape`, `_tall` and the arrangement one-hots `_rpt/_rpw/_rlw/_rlt`.
2. **Placement as data binding.** Every responsive object is a plain wrapper `Node` (or a rectangle, a text column
   width, a path vertex, a trim offset, a script input, the joystick) whose properties are bound. Children keep their
   authored design coordinates and all their keyed animation, so choreography is untouched: the wrappers only map
   design space to screen space. The layout is written once, in Python (`tools/layout.py`), as expressions of the
   viewport; `tools/resp.py` compiles each one:
   - short expressions → native `DataConverterFormula` converters (49);
   - long ones (min/max over four arrangements) → `scripts/layoutsolve.luau`, a **generated** solver with shared
     subexpressions computed once; the probe runs it and writes 147 private `_l…` numbers, bound directly.
3. **Measured copy.** Each copy column binds its `computedHeight` back into `_ch1…_ch10` (`direction="true"`), and the
   solver re-runs when they change. Column widths come from estimates (no feedback loop); scales and positions use
   the **measured** height, so long names and localized copy push what follows instead of colliding.
4. **Full-screen pieces follow the viewport**: the signature frame vine is a rounded rectangle whose vertices are bound
   to the real edges (its trims start at the real vine tip), the leaf iris and its paper edge grow from the real vine
   tip scaled to cover any viewport, the content camera recedes/pushes about the viewport centre, and the 3D transition
   leaf sits in a viewport-centred wrapper scaled with the screen.
5. **GPU canvases at their real size**: `paperleaf` takes `res` bound to its on-screen scale × device pixels (at least
   the authored supersampling, capped at a 2048 px canvas) and resizes its canvas and MSAA/depth targets when it changes
   (targets are shared per size and released when unused); `canopylight` takes `w`/`h`/`dpr` and resizes the paper
   sheet (device resolution, ≤ 4096 px) and the light canvas, re-rendering the paper.
6. **Rebinding.** `viewport.luau` and `dwellclock.luau` now rebind on every `init` that carries a view model, so a host
   that binds its own `UserRecap` instance after load gets a working layout and clock (the earlier first-`init`-only
   guard silently kept the default instance, which the resize harness exposed).

Without scripting nothing is written: every private value keeps its default, which is the 390×844 design.

### Host setup

- **Use the runtime's layout fit** so the artboard is resized to the canvas and reflows (in the CLI this is the default
  `--fit=layout`). The option is the `Layout` fit in each runtime, e.g. `Fit.Layout` on the web
  (`new Layout({ fit: Fit.Layout })`, then call `resizeDrawingSurfaceToCanvas()` on resize), `.layout` on Apple,
  `Fit.LAYOUT` on Android, `Fit.layout` in Flutter; **check the Rive runtime docs for your version's exact names**,
  and for the layout scale factor, which should stay at the device pixel ratio so 1 artboard unit = 1 pt.
- Do **not** use `contain`/`cover`: they scale the 390×844 artboard instead of re-laying it out.
- Optionally write `layoutBreakpoint`. Everything else responsive is internal.
- Unchanged: web hosts still need a signed build (`rive . --publish`).

### Tested sizes (`captures/responsive/`)

Each sheet is one scene, portrait row then landscape row, in this order:
portrait 320×568, 360×640, 390×844, 430×932, 600×960, 767×1024, 667×375, 740×360;
landscape 768×1024, 820×1180, 1024×768, 1280×720, 1440×900, 1920×1080, 2560×1080, 1366×600.
`mid-fwd-1to2-f20.png` and `mid-back-4to3-f18.png` show a forward and a reverse transition 20 / 18 frames in at
every size: the frame vine hugs the real edges, the iris and 3D leaf cover the whole viewport. The walkthroughs are
`../video.webm` (390×844) and `../video-landscape.webm` (1280×720).

Responsive checks in `tools/check.py`:
- `orientation_follows_width`: 767×1024 portrait, 768×1024 landscape, 740×360 portrait, 1366×600 landscape…
- `breakpoint_is_tunable`: `layoutBreakpoint` 1100 keeps 1024 wide portrait, 600 makes 700 wide landscape.
- `right_arrow_and_tap_zones_at_other_sizes`: Right ×2 and tap next/next/back at 1280×720, 740×360, 320×568 and 820×1180.
- `hold_pauses_on_real_width`: hold on the real right edge pauses and its release does not navigate.
- `resize_across_threshold_mid_scene`: a throwaway harness project (`build/harness`, never shipped) instances the
  recap, settles scene 2 at 1280×800, resizes it to 600×900 mid-scene (still scene 2, now portrait, settled, the
  applied placement equals the solved one), presses Continue and resizes back to 1280×800 **mid-transition** (lands on
  scene 3, landscape, settled). All 147 solved values then equal those of a fresh start at the same size.

### Compromises

- **Placement, not per-shape reflow.** Hand-drawn art moves and scales as groups (art, number block, copy column,
  corner foliage, ground). Copy re-wraps for real; illustrations do not re-compose shape by shape.
- **Private view-model state.** `UserRecap` carries 166 private underscore numbers for the layout (147 solved
  placements, 10 measured heights, the viewport). They are not user data and hosts never write them, but they show up
  in a data dump. The alternative, formulas only, made the RML 3× larger.
- **Smallest phones.** At 320×568 copy is 0.78× (support 14 px, units 11.5 px), but the share card on the summary is
  drawn at about 0.53×, so its stat labels are about 6 px on screen. The host's share image renders the `ShareCard`
  artboard at native size, so the shared card is unaffected.
- **Extreme copy.** The 40%-longer extreme fixture fits everywhere except the 740×360 short phone, where scene 2's
  four-line headline plus support runs past the bottom at the 0.66× floor, and 320×568, where it reaches the vine.
- **Backdrops under copy.** In landscape, scene 3's paper terraces and the story vine run behind the copy column; scene
  4's foliage and scene 7's hands still bleed under the portrait control row, as in the design. Scene 7's hands are
  framed in a paper panel in side-by-side arrangements so the arms do not end mid-screen.
- **Very wide screens** (2560×1080) keep the copy column capped at 420 design units and the art at 2.6×, so there is
  generous empty paper rather than giant type.
- **3D resolution** is capped at 2048 px canvases (transition leaf ≈ 2.3 px/unit): slightly soft on a 5K display.
- A live resize between two arrangements is a cut, not an animated reflow.

## Captures (`captures/`)

Regenerated by `tools/capture_all.sh` (it deletes the old PNGs first). Frame numbers count from the navigating click.

| Files | What |
|---|---|
| `scene-01…10.png` | Settled scenes |
| `persona-0…3-*.png` | Each persona (copy written with `--data`, as the adapter would) |
| `transition-1to2-f8/16/24/34.png`, `transition-4to5-f12/24.png` | Forward: frame vine, leaf iris, 3D leaf across the camera |
| `transition-back-4to3-f6/20/34.png` | Reverse handoff (frame unweaves, leaf sweeps back inner face first) |
| `scene1-seed-closed-f8.png`, `scene4-paper-bud-f30.png`, `scene4-opening-f60.png`, `scene9-seed-cradle-f30.png`, `scene2-unfurl-f50.png` | 3D and deformation moments mid-motion |
| `reduced-motion-*.png` | Reduced motion (scene 2 at 6 frames already shows 248) |
| `zero-user-intro.png`, `zero-user-summary.png` | Intro, then the welcoming empty card |
| `extreme-*.png` | 128,940 values, 52-character name, 40%+ longer copy |
| `hidden-3-4-7-nav.png` | 7 progress segments; navigation skips the hidden scenes |
| `paused-scene1.png` | Paused state |
| `responsive/scene01…10.png` | Each settled scene across the 16-size viewport matrix (see [Responsive layout](#responsive-layout)) |
| `responsive/mid-fwd-1to2-f20.png`, `responsive/mid-back-4to3-f18.png` | A forward and a reverse transition, mid-flight, at every size |

Motion preview: `apps/sprig/video.webm` (34.5 s, every scene and transition, rendered headless by
`scripts/render-video.py sprig`).

## Fonts and licenses

| File | Font | License |
|---|---|---|
| `assets/fonts/Fraunces-Variable.ttf` | Fraunces variable (opsz, wght, SOFT, WONK), google/fonts | SIL OFL 1.1 (`OFL-Fraunces.txt`) |
| `assets/fonts/DMSans-Variable.ttf` | DM Sans variable (opsz, wght), google/fonts | SIL OFL 1.1 (`OFL-DMSans.txt`) |

Both are embedded in the `.riv`. All textures (paper fibre, canopy light, leaf veins) are procedural shaders.

## Unsupported techniques and substitutions

- **Keyed deformation for unfurling**: now real (vertex x/y and bezier handles keyed from a rolled fiddlehead through a
  half-open shape to the authored leaf). Rive has no "curl" primitive, so the roll is approximated by a short, narrow,
  sideways-bent blade; the halves stay hinged on the midrib.
- **3D**: Rive has no 3D scene graph; the 3D paper is drawn by `scripts/paperleaf` into GPU canvases (see below).
- **Interpolator duration binding**: binding `DataConverterInterpolator.duration` to `reducedMotion` had no effect at
  runtime (the first pass relied on it; counts still took 1.15 s under reduced motion). Substitute: a snap formula after the
  interpolator, `x + rm·(target − x)`, reading the metric and `reducedMotion` through bound formula tokens.
- **Event payloads**: `screenChanged` carries a constant `index` per scene through the Event's custom property. Read `currentScreen` if your runtime doesn't expose payloads.
- **Locale formatting**: there is no in-file locale formatter. Count-ups group thousands with the adapter-supplied `groupSeparator`. Values at or above 1,000,000 show without inner grouping. Large values scale the numeral down in steps instead of overflowing.
- **Responsive reflow**: since the responsive pass the file lays itself out at any size with a portrait and a landscape layout; see [Responsive layout](#responsive-layout). Hand-drawn art is placed and scaled by group rather than reflowed shape by shape.
- **Relative bind paths**: the CLI can't author them. All binds are absolute paths into `UserRecap`.

## Measurements

See the table in [Improvement pass](#performance). Object counts: SprigRecap 51,592 objects (24,658 in the first version; the
increase is almost all keyframes for the vertex morphs and their reverse/reduced holds, plus 370 from the responsive
pass), ShareCard 882, 18 state-machine layers.
Frame rate on a device was not measured; no device or runtime profiler was available.

## Remaining limitations (honest)

- **Web needs a signed build**: the `.riv` contains unsigned Luau/WGSL. Native runtimes and the previewer run it; web
  runtimes reject unsigned scripts. Ship with `rive . --publish` (needs `rive login`, not done here). WebGPU validation of
  the shaders was not exercised.
- **No-script runtimes**: without scripting the recap still navigates, but does not auto-advance, the 3D pieces draw as
  flat outlines (seed shells, giant leaves, cradle, transition leaf) and the paper/canopy light is absent.
- **`.rev` not produced**: `rive . --once --rev=…` returned `Not logged in`. Run `rive login`, then the command above.
- **`recapFinished`/`shareTapped`**: the headless CLI doesn't log fired events. `screenChanged` is proven indirectly, because `currentScreen` is written by its listener. These two are present in the binary but were not observed firing.
- **Entrance freezing**: pause freezes the dwell clock (exactly), idle loops, the 3D idle sway and the canopy light, but an entrance that is already playing finishes its ≤1.9 s choreography.
- **Mid-scene data changes**: a host update of the current scene's number re-animates the count. A persona update during scene 9 swaps to the new persona's final pose without replaying its reveal. Returning to a scene replays its count-up.
- **Untested here**: right-to-left layout, real screen readers, touch hardware, and the web runtime. Hit regions were exercised only with headless pointer clicks and keys.
- **Copy positions**: some scenes position copy for English plus 40%. Very long headlines in scene 2 run under the vine art (see `extreme-scene2.png`), and a summary headline of 4+ lines would reach the share card.

## Improvement pass

### Critique of the first version (before changing anything)

- **Flat leaves everywhere.** Every leaf "unfurled" by scaling two flat halves on a hinge; nothing had depth, and the
  signature "leaf folds across the camera" was a flat two-tone vector leaf scaled up, which read as a cardboard cut-out.
- **Gaps against the concept.** Scene 4 had the headline at the top, a pink blob behind the number and two flat green
  wedges cutting the screen edges; the concept has the number on top and a huge folded paper leaf pair cradling a jungle
  diorama. Scene 9's arch was a near-empty cream panel running behind the controls; the concept nests a lush arch in an
  opened seed shell. Scene 1's seed was two flat ovals.
- **The vine never became a frame.** The brief's signature ("a growing vine becomes the next screen's frame") was only a
  thin vine on the right edge plus an iris wipe.
- **Inconsistencies / overlaps.** Scene 7's support line ran into the window; scene 3's cream terraces swallowed the cream
  Previous/Pause buttons (they vanished); scene 5's jar and scene 9's arch sat behind the controls; the summary headline
  broke as "A little year. A lot / of you."; body text was 10.7 px at 320×568.
- **Motion.** Every transition was the same iris + flat sweep; the outgoing scene never reacted; reverse was the same
  move mirrored. Pause lagged up to 250 ms (28-step clock).
- **Replay icon.** The arrowhead sat on the arc's *start* and pointed sideways, not along the arc.
- **Latent bug.** Reduced motion did not make numbers final: the interpolator's bound duration is not honoured, so counts
  still took 1.15 s.
- **Paper.** A 580 KB static noise PNG did the "paper grain" and nothing suggested light through leaves.

### What changed

1. **Real 3D folded paper (`scripts/paperleaf.luau` + `.wgsl`).** One (u, v) grid (65 × 25, stored twice with a
   mirror sign so a pair draws in one indexed draw) is shaped entirely in the vertex shader: a pointed leaf or an
   almond seed half-shell outline, folded about the midrib, cupped, curled toward the camera (integrated bent midrib),
   rolled at the tip, twisted and rippled; finite-difference normals; perspective projection. The fragment shader is the
   paper: two stocks (green outer / cream inner face), pressed veins, long fibres + tooth + mottle, a cut-paper rim, crease
   occlusion and **light through the blade when lit from behind** (veins darken against the glow). 4× MSAA where available.
   Every pose value is a `ScriptInputNumber` keyed by the existing scene timelines, so choreography stays in the state
   machine. A CPU twin of the vertex maths produces the outline for a feathered cast shadow and for the no-GPU fallback.
   Used for: the transition leaf, scene 1's seed (closed almond → squash → crack → open), the carried seed in scene 2,
   scene 4's giant leaf pair (closed paper bud → shiver → falls open, twisting its cream faces out) and scene 9's cradle.
2. **The signature transition rebuilt.** A frame vine grows from the story-vine tip round the whole screen edge in both
   directions (one closed path, two trimmed strokes whose `offset` starts at that scene's tip, 22 leaves popping as the
   growth passes) and becomes the frame; the leaf iris opens inside it; the 3D leaf crosses the screen centre exactly
   while the iris is half open, flipping from its green face to its cream underside; the old scene recedes. Reverse is
   its own move: the frame unweaves into the tip, the leaf sweeps back inner face first, the closing scene pushes toward
   the camera. The global pieces are keyed only by the entering scene's forward timeline and the leaving scene's back
   timeline, and are excluded from the derived arrive/reduced holds, so no two layers fight over them.
3. **Leaves unfurl through keyed vertex deformation** (`leaf(..., morph=True)` in `tools/rml.py`): each half's vertices
   and bezier handles are keyed from a rolled fiddlehead through a half-open blade to the authored shape (angles unwrapped
   to interpolate the short way), with the midrib drawing on. Every unfurling leaf in scenes 1, 2, 4, 5, 6, 9 and 10 uses it.
4. **Paper + canopy light (`scripts/canopylight.luau` + `.wgsl`)** replaces the grain PNG: a static fibre/tooth/mottle
   sheet with a soft vignette (rendered once, soft-light), and komorebi — light through gaps between leaves as soft flecks
   drifting in a breeze, brightest from the upper left (low-res canvas, overlay). Its strength follows `currentScreen`
   through an eased converter; reduced motion, pause and hold freeze it (a frozen pattern is not re-rendered).
5. **Recompositions.** Scene 4 now matches the concept (number → unit → headline on top; sunrise, mist straps, ferns,
   heart leaves and apricot leaves inside the opening 3D pair). Scene 9: the arch stage is smaller and higher, rises out
   of a 3D seed cradle, has pothos strands unrolling inside and leaves spilling over the lip. Scene 3: green paper terraces
   with lit edges and larger cream/apricot pots. Scene 7: two large paper hands reach in from the bottom corners and pass
   the cutting (arc computed from the transformed palms); copy no longer touches the window. Scene 5's jar and scene 8's
   orbit moved clear of the copy/controls. Summary headline width-capped so it breaks "A little year. / A lot of you.",
   share card nudged down.
6. **Exact pause (`scripts/dwellclock.luau`).** The 28-step state-machine clock and its probe are gone; the script owns
   `screenProgress` and the auto-advance and stops on the very frame `isPaused`/`_holdPaused` flips (verified: 0.5222 →
   0.5222 across 120 paused frames).
7. **Type and fixes.** Support 16 → 18 px, units 15 → 16, persona description 17 → 19, labels 13 → 14 (12.1 px body at
   320×568). Replay icon rebuilt from geometry: clockwise arc, arrowhead on its end aligned to the tangent. Reduced
   motion now shows final numbers at once (snap formula).

### 3D / shader techniques (and where not)

- **Used:** `ScriptedDrawable` + `GPUCanvas` + `GPUPipeline` with a depth buffer and 4× MSAA resolve (paper leaf);
  vertex-shader geometry from uniforms (no mesh data shipped), finite-difference normals, two-sided paper shading with
  translucency; fragment-only full-screen-triangle passes for the paper sheet and the canopy light. All render headless in
  `--screenshot` and in the video. MSAA/depth targets are cached per canvas size and shared.
- **Not used:** imported meshes/bones (nothing needs them), textures (all procedural), 3D for the pots, jar, hands,
  calendar or share card — those read well as flat folded paper and keep the editorial graphic edge; the share card stays
  pure vector so host snapshots never depend on GPU scripting.
- **Instancing note:** `@builtin(instance_index)` does not bake to MSL with this toolchain, and a per-instance vertex
  buffer did not deliver the mirror sign; the grid is stored twice instead.

### Fallbacks and reduced motion

- No GPU scripting → each paper piece draws its projected outline as a flat vector shape (same keyed pose), the
  paper/canopy overlay draws nothing. No scripting at all → no auto-advance (navigation still works).
- Reduced motion → the ER/LR timelines hide the transition leaf and frame (`alpha`/`live` 0), 3D pieces hold their final
  pose (no idle sway), the canopy light is frozen, numbers snap.
- Every 3D piece has a `live` input keyed on scene entry and cleared by the scene's Hidden state, so off-screen pieces
  issue no GPU work; a settled piece re-renders only when an input changes (idle sway does re-render it each frame).

### New compromises

- **Web needs `rive . --publish`** (signed scripts). Not done here (no login).
- **GPU memory** (all canvases allocated up front): five paper canvases (transition 880×880, scene 4 pair 880×880,
  two seeds 600×500, cradle 704×512) ≈ 10.1 MB, plus 4× MSAA colour + depth targets shared per size (three sizes)
  ≈ 46.0 MB, plus the paper sheet 585×1266 (3.0 MB) and canopy light 133×287 — about 59 MB in
  total. Only the current scene's pieces render; the scene 4 pair has the same pixel size as the transition leaf, so the
  two share one MSAA/depth set.
- 3D pieces render at a fixed pixel density (`res`, 1–2 px per unit, because a `Node` script is not told the surface
  scale): sharp at 1×/2×, slightly soft at 3×.
- Object count roughly doubled (vertex-morph keyframes); `.riv` still shrank because the grain PNG is gone.
- The transition leaf is a single shared object: two transitions within ~0.7 s restart its sweep rather than stacking.

### Checks

`python3 tools/check.py` — 19/19 pass (14 at 390×844 below, plus 5 responsive checks listed in
[Responsive layout](#responsive-layout)): Right/Left keys, hidden-scene skipping both ways, 12 rapid taps land on 10,
auto-advance at 1.8 s settle + dwell, dwell clamped to 3 s, auto-advance disabled holds, pause freezes progress exactly
and resumes from the same point, the summary never auto-advances, Replay returns to 1, Space pauses, hold pauses and its
release does not navigate. `rive . --verify` 0 errors / 0 warnings, `rive inspect . --summary` problems `[]`.
(The first version had no check script; nothing was changed to make a check pass.)

### Performance
`rive . --bench`, Apple-silicon Mac, headless at @1x, warm runs. Render is CPU-side submission, not GPU time; on-device
frame rate and GPU time were not measured.

| | Before | After |
|---|---|---|
| `.riv` size | 1,484,906 B | **1,296,615 B** (grain PNG removed; scripts, shaders and morph keyframes added) |
| Scripts in the file | none | 3 Luau + 2 WGSL (web hosts need `rive . --publish`) |
| `--bench=600` (intro) advance mean / p95 | 0.044 / 0.086 ms | 0.043 / 0.093 ms |
| `--bench=600` (intro) render mean / p95 | 0.085 / 0.104 ms | 0.113 / 0.213 ms |
| `--bench=1200`, `autoAdvanceSeconds=3` (four auto-advanced cuts) advance mean / p95 | 0.051 / 0.088 ms | 0.051 / 0.100 ms |
| same, render mean / p95 (max = first frame incl. shader setup) | 0.134 / 0.127 ms (max 36 ms) | 0.169 / 0.225 ms (max 44 ms) |
| Wasm memory growth | +0 | +0 |
| Pause latency | up to dwell/28 (250 ms at 7 s) | 0 (same frame) |
| Body text at 320×568 | 10.7 px | 12.1 px |

**Responsive pass:** `.riv` 1,296,615 → **1,370,377 B** (+5.7%: wrapper nodes, binds, 49 formula converters, the
generated solver); SprigRecap 51,222 → 51,592 objects; `scene.rml` ~84.9k lines. `--bench=600` (intro) p50 advance /
render 0.090 / 0.206 ms at 390×844 and 0.096 / 0.218 ms at 1280×720 (measured while other renders shared the machine,
so means and p95 are noisy); wasm memory +0. The solver runs only when the size, breakpoint, scene or a copy height
changes. The canopy paper sheet is now rendered at the real size × device pixels (≤ 4096 px), e.g. 1920×1080 at @1x
→ 2880×1620 (≈ 18.7 MB) instead of a fixed 585×1266.

GPU work per frame: the current scene's 3D piece re-renders only while one of its inputs moves (entrance, idle sway);
the transition leaf renders only during a cut (~45 frames); the canopy light renders a 133×287 pass while it drifts;
the paper sheet renders once.
