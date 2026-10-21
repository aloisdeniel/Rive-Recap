# Crux — 2026 recap (Rive)

A ten-scene, data-bound climbing recap for the fictional app Crux, built with Rive CLI 1.6.0. The fixture data is fictional; nothing here is measured activity.

| What | Where |
|---|---|
| Editable source (RML + Luau + WGSL) | `scene/*.rml`, `director.luau`, `hold3d.luau` + `hold3d.wgsl` (3D holds), `chalk.luau` + `chalk.wgsl` (chalk shader) |
| Generator for the RML (scenes, ~60 entrance/exit timelines, ~450 transitions) | `tools/gen.py` (+ `rml.py`, `art.py`, `stage.py`, `build_stage.py`, `main_ab.py`, `model.py`, `conv.py`) |
| Runtime file | `build/crux-recap.riv` (882 KB, unsigned local build) |
| Editor file `.rev` | **Not produced.** `rive . --once --rev=build/crux-recap.rev` fails with "Not logged in". Run `rive login` and then that command. |
| Fixtures | `fixtures/fixture.json` (sample data), `new-user.json`, `extreme.json`. The same three are also authored as `UserRecap` instances named `Fixture` (the default), `NewUser` and `Extreme`. |
| Captures | `captures/*.png` (58 stills), `captures/motion/*.mp4`, `captures/data/verify-report.json` |
| Checks | `tools/verify.py` (32 behavioural checks, all passing), `tools/capture.py` (re-renders every capture) |

## Preview

```bash
cd apps/crux/rive
python3 tools/gen.py          # only after editing tools/*.py; scene/*.rml is already generated
rive . --verify && rive inspect . --summary
rive .                        # live previewer (layout fit: resize the window to test responsiveness)
rive . --screenshot=out.png --data=currentScreen=9 --data=personaIndex=1 --advance=130
```

Any `UserRecap` field can be set with `--data=<name>=<value>`. `tools/capture.py` shows how to apply a whole fixture this way.

## Architecture

- **`Crux Recap`** is the host-facing artboard. It holds the chrome as a responsive flex layout: a top bar with the wordmark, progress segments and year, and a bottom bar with Previous, Pause/Replay and Continue/Share. Behind the chrome sits the `Stage` component, a `NestedArtboardLeaf` with `fit=cover` and `alignmentY=-0.8`. The **director** script fills the canvas, and the `Recap` state machine drives buttons, keys, focus and events.
- **`Stage`** (390×844) contains the ten scenes. Each scene has Text, Front, Mid and Back layers, which give parallax during transitions. The stage also holds the persistent acid **carrier hold** with its yank rope, the chalk occluder, and the `Story` state machine. That machine has four layers:
  - **Scenes:** one entrance per scene (forward, back or reduced) and one exit per scene (yank, lower-off or reduced fade), chosen by `currentScreen`, `navDirection` and `reducedMotion`. Scene 9 has four persona variants and scene 10 has two (full and new-user).
  - **Idle:** loops that start only after the scene has settled and freeze while paused.
  - **Grab Hold:** the signature interaction.
  - **Share Privacy:** hides or shows the name on the share card.
- **`Wordmark`** is a component artboard: an original stencil "CRUX" built from vector strokes, with a hold on the X. It is reused in the top bar, the intro and the share card.
- **Single model.** There is one view model, `UserRecap`, and one instance of it is bound to the main artboard. The nested Stage and Wordmark inherit that same instance, and no component owns a copy of any statistic.
  - **Deviation from the brief:** this is not Rive's `viewModelType="global"`. A global view model cannot be set with `--data`, cannot have per-fixture instances, and its host API support was unverified. So "global" is implemented as one shared, artboard-bound instance. To switch, set `viewModelType="global"` in `tools/model.py`; bind paths do not change.

## Binding contract (`UserRecap`)

**Host-owned (host writes, file reads):** every field in the brief's table, with these types:

- Numbers: `year`, `sessions`, `sends`, `attempts`, `techniqueSessions`, `longestSessionMinutes`, `activeWeeks`, `climbingPartners`, `personaIndex`, `autoAdvanceSeconds`.
- Booleans: `autoAdvanceEnabled`, `isPaused`, `reducedMotion`, `soundEnabled`, `shareIncludeName`, `shareIncludeSensitiveValues`, `showScreen1`–`showScreen10`.
- Strings: all labels, headlines, supports and units, plus `userName`, `periodLabel` and `locale`.
- Colour: `personaColor` is a native Color (ARGB), adapted from the JSON `"#RRGGBB"` by prefixing `FF`.

The host also sets `currentScreen` once, as the starting scene. After that the file owns it.

Fields added for the host:

| Field | Type | Owner | Meaning |
|---|---|---|---|
| `personaAdapterEnabled` | bool, default true | host | When true, the in-file adapter maps `personaIndex` to `personaName`, `personaDescription` and `personaColor` using the brief's English table, writing all three in the same frame. A localizing host sets it false and writes all four fields itself, in the same frame. |
| `shareDismissed` | trigger | host | Fire this when the platform share sheet closes. It restores the pause state that was saved when Share was tapped. |

**Adapter-owned (written by `director.luau`; the host may read them):**

| Field | Type | Meaning |
|---|---|---|
| `currentScreen` | number | Canonical scene ID, 1–10. |
| `screenProgress` | number | 0–1 progress through the current scene's dwell. |
| `navDirection` | number | +1 or −1. |
| `visibleScreenCount`, `visibleScreenPosition`, `progressValue` | number | The derived visible-scene list, which drives the progress segments. |
| `isEmptyRecap` | bool | True when no metric or persona scenes are visible. |
| `sceneSettled` | bool | True once the current scene's entrance has finished. |
| `personaSlot` | number | Sanitised persona index, 0–3. Unknown values become 0. |
| `sessionsDisplay`, `sendsDisplay`, `attemptsDisplay`, `techniqueSessionsDisplay`, `longestSessionMinutesDisplay`, `activeWeeksDisplay`, `climbingPartnersDisplay` | string | Integers formatted for the locale. The active scene's field counts up during its entrance and holds the exact final value at all other times. |
| `yearDisplay` | string | The year without grouping. |
| `pauseButtonLabel` | string | The pause button's accessible label. |
| `screenAnnouncement` | string | A full-sentence text equivalent of the current screen, using exact values, for the host's screen-reader announcements. |

**File-internal (do not write):** `enteredScreen`, `heroProgress` (the count playhead, written from a keyed timeline), `focusedControl`, `holdGrabbed`, `isSharing`, and the triggers `navNext`, `navPrev`, `togglePause`, `replay`, `shareRequested`, `screenSignal` and `finishSignal`.

**Events (main state machine):**

- `screenChanged` fires once per scene change. It carries a custom-property payload `screen`, bound to `currentScreen`. If the host's runtime does not surface event properties, read `currentScreen` when the event arrives.
- `recapFinished` fires once, when the summary first settles. Replay resets the latch.
- `shareTapped` fires on the Share button. The host owns the capture and the share sheet. Snapshot the Stage region after `sceneSettled`; the share card lives in the stage, separate from the chrome.

**Formatting and clamping:**

- Negative or non-finite counts are clamped to 0, and the raw field is rewritten.
- Grouping follows CLDR rules for common locales: `,` for en; `.` for de, it, nl, pt and others; a no-break space for fr, nordic and slavic locales; `’` for de-CH. es and pl do not group 4-digit numbers.
- Very large values shrink to fit using `fitFontSize`. There is no compact notation (for example "1.2M"); exact values are always shown.
- Pluralization of units is the host's job: pass singular or plural strings in `screenNUnit`.

**Host-adapter responsibilities:**

- Localized strings.
- Plural units.
- Persona strings, if you localize them.
- Stop advancing the runtime, or set `isPaused`, while the app is backgrounded.
- Set the visibility flags. Hide absent metrics, never genuine zeros. The new-user fixture hides scenes 2–9, which yields the intro followed by a welcoming summary.
- Show the full layout at phone sizes with Fit.layout. On desktop, use Fit.contain with centred alignment (captured as `viewport-desktop-1280x800-contain-*`).

## Motion and interaction (what was built)

**Signature transition ("Yank").** On Next, the rope drops onto the carrier hold and snaps taut, with an elastic bow. After an 8-frame anticipation dip, the four parallax layers are yanked up at different distances, and a graphic chalk cloud (shaded puffs and grain) occludes the cut. The next scene arrives from below with a back-ease overshoot while the chalk clears. The exit takes about 630 ms.

**Reverse transition.** Previous uses a lower-off instead: a small lift, then the panel drops away on a slackening rope, and the next scene arrives from above.

**Continuity transitions.** The acid carrier hold persists through the whole story. In three hand-offs it rides across the cut instead of leaving:
- 2→3: it becomes the finish hold that gets stamped.
- 6→7: it moves from the rope coil to the top wall panel.
- 8→9: it moves from the hub of the partner web to the persona emblem, where it is consumed.

**Hero sequences.**
- Scene 2: holds snap into a vertical route in sync with a stepped count.
- Scene 3: an acid route trace runs to a punched finish stamp.
- Scene 4: a kinetic stack of ghost holds; the attempt marks fly into the number.
- Scene 5: three holds rotate into alignment, then a level bubble settles.
- Scene 6: the rope arc uncoils around the dial. The arc length is data-driven: minutes/180 × count progress.
- Scene 7: thirteen wall panels rise, each one filled from `activeWeeks`, while the camera pulls back.
- Scene 8: up to twelve knots join a web. The pool is bounded and each knot is shown only if `climbingPartners` ≥ k.

**Persona reveal.** A shared anticipation scribble leads into one of four distinct reveals:
- Route Reader: a route draws across a diamond map, followed by a reading lens.
- Power Mover: a lightning hold slams in with squash, a starburst and rays.
- Balance Seeker: a stone teeters to balance on a disc.
- Persistent Solver: the background flips to coal and a looping chalk route is drawn.

The accent panel is bound to `personaColor`.

**Summary.** The collectible card assembles itself: it rises and unfolds, the header wipes in, the persona row and the five stats stamp in, then a route draws. The name appears only when `shareIncludeName` is true; otherwise a mini route motif fills its cell.

**Signature interaction.** A draggable acid hold on scene 1 compresses on press and rebounds elastically on release. It never navigates: the director excludes its hit region.

**Scene timing.** Each entrance follows the brief's score: an orientation gesture at 0–200 ms; the hero and count at 200–1200 ms, with the number transparent until frame 12 so no placeholder digits flash; the headline and support at 1.2–1.8 s. The dwell timer starts only after the scene has settled.

**Reduced motion.** Final values appear immediately, with about 200 ms opacity cross-fades. There is no camera movement, rope or chalk, and the idle loops are off. The full story and every control remain.

**Controls.**
- Tap: the right two-thirds advances and the left third goes back.
- Hold (0.32 s or longer) pauses; releasing restores the previous state and never counts as a tap.
- Pointer and touch work on all of the above.
- Keys: Right/PageDown advance, Left/PageUp go back, Space pauses.
- Tab and Shift+Tab move focus across the buttons, and a cobalt ring shows which one is focused. Enter activates it.
- Buttons carry `SemanticData` with labels bound to the model, and the chrome buttons are 52 px.

**Auto-advance.** It uses `autoAdvanceSeconds`, clamped to 3–60 s; 7 s is the default. `autoAdvanceEnabled=false` disables it. It never advances while paused or sharing, and it does not loop after the summary.

## Verification

- `rive . --verify`: 0 errors, 0 warnings.
- `rive inspect . --summary`: 0 problems. Object counts are 622 (main), 24,057 (stage) and 50 (wordmark).
- `python3 tools/verify.py`: 32/32 checks pass (re-run after the improvement pass). The results are in `captures/data/verify-report.json`. Covered:
  - Tap zones, rapid taps (settle on the last requested scene, one signal per change), and hold/release.
  - Pause freezing and resuming progress.
  - Skipping hidden scenes in both directions, the all-hidden safe path, and starting on a hidden scene.
  - `recapFinished` firing once, replay resetting the latch, and a full auto-advance run reaching the summary.
  - Dwell clamping, auto-advance disabled, keyboard, Tab focus, and Enter activation.
  - Atomic persona mapping and fallback, negative clamping, fr/es formatting, count-up, and reduced motion.
  - The share tap pausing the story, and dragging the hold not navigating.
- The full auto-advance sequence (1→10 at 3 s dwell) was confirmed with `--data-dump-every`.

**Captures.**
- All ten settled scenes and all four personas.
- Reduced motion.
- New-user and extreme/long-copy fixtures. The extreme fixture uses de-DE, a 50-character name, about 40% longer copy and an invalid persona index.
- Name privacy on the share card.
- Viewports 320×568 and 430×932, plus desktop contain.
- Intermediate transition frames, the hold drag/rebound, hold-to-pause and paused states.
- Motion previews (`captures/motion/*.mp4`, 30 fps): the forward yank 2→3, the reverse 5→4, and the Power Mover reveal. Frames are deterministic headless renders stitched with ffmpeg.

**Measurements.** Taken with `rive . --bench=600` on an Apple M5 Pro running macOS 26.6.2, headless at @1x.
- Advance: mean 0.022 ms, p95 0.051 ms.
- Render submission: mean 0.084 ms, p95 0.139 ms.
- Wasm memory growth: none.
- File sizes: `.riv` 781 KB; fonts about 490 KB of that.

On-device GPU frame rate was **not** measured.

## Fonts (SIL Open Font License 1.1)

| File | Family | License |
|---|---|---|
| `assets/fonts/BarlowCondensed-Black.ttf` (hero numbers) | Barlow Condensed, © 2017 The Barlow Project Authors | `assets/fonts/OFL-BarlowCondensed.txt` |
| `assets/fonts/BarlowCondensed-ExtraBold.ttf` (headlines) | Barlow Condensed | `assets/fonts/OFL-BarlowCondensed.txt` |
| `assets/fonts/IBMPlexMono-Regular.ttf`, `IBMPlexMono-Medium.ttf` (labels) | IBM Plex Mono, © 2017 IBM Corp. | `assets/fonts/OFL-IBMPlexMono.txt` |

The fonts were downloaded from github.com/google/fonts and are embedded in the `.riv`.

## Unsupported techniques and substitutions

- **Sequencing logic is a Luau script.** It handles the visible-list, hold-versus-tap timing, and the dwell timer with its clamping. The state machine still drives every scene state, transition and event, and reads `currentScreen`.
  - **Web hosts:** a locally built `.riv` carries unsigned scripts, which web runtimes reject. Ship with `rive . --publish` (requires login).
- **Count-up.** A keyed custom property writes `heroProgress` back into the model, and the script formats the result.
- **Keyed deformation.** Squash and stretch use scale on nested nodes. The rope slack uses a keyed bezier vertex. There are no meshes or bones.
- **Chalk.** The transition occluder is a WGSL shader (see below). Impact puffs are still bounded vector puffs.
- **Holds.** Since the improvement pass, the large holds are real GPU 3D (see below). Small route holds (scene 9 Route Reader, scene 8 knots, scene 1 wordmark hold) are still flat vector.
- **No sound.** Sound is off by default and no audio ships.

## Remaining limitations (honest)

- **No `.rev`.** It needs `rive login`; nothing was renamed to fake one. The project has also not been opened in the Rive Editor, so editor-only labels and layout are unverified.
- **`shareDismissed` not exercised.** `--data` cannot fire a trigger mid-run, so restoring the pause state after sharing is code-reviewed only.
- **Event delivery not observed.** The CLI does not print events. `screenChanged`, `recapFinished` and `shareTapped` are verified through their driving signals (`screenSignal`/`finishSignal` fire exactly as expected) and through their presence in the `.riv`.
- **Full-story video.** `apps/crux/video.webm` is the walkthrough, rendered by `scripts/render-video.py crux` from the repo root. `python3 tools/motion.py full` produces an auto-advance version.
- **Small screens.** At 320×568 the cover-scaled stage crops about 15 px at the top and 136 px at the bottom (in stage pixels). Scene 6's support line and the bottom edge of the summary card sit close to the controls there.
- **Persona text is English unless the host takes over.** With `personaAdapterEnabled` true, the persona name and line are English; a localizing host must take them over. There is no right-to-left layout pass.
- **No mid-entrance switch to reduced motion.** If `reducedMotion` changes partway through an entrance, it applies from the next navigation.
- **Brief deviations kept as designed:**
  - `shareIncludeSensitiveValues` has no visual effect. The card shows only aggregate counts and the persona, none of which are classed as sensitive.
  - `UserRecap` is a single shared instance rather than Rive's `global` view model type (see Architecture).

## Improvement pass

### Critique of the previous version
- The holds, the hero motif, were flat polygons with a single facet, so they read as stickers next to the concept's chunky, speckled volumes.
- The signature yank cut to a flat beige blob: four to six frames of near-solid chalk colour with no texture or light. It read as a fade to white.
- Every hold entered the same way (a 2D pop or slide). The yank was a pure vertical slide; only the rope moved with any physicality.
- Scene 4's "kinetic stack" was twelve flat ghost polygons. Scene 7's weeks were a plain bar chart running under the controls.
- Several layouts had problems:
  - Scene 3 crammed its route into the bottom 200 px and left an empty band.
  - In scene 6, the coil and carrier floated with nothing under them.
  - Scene 8 had knots clipped at the right edge and hidden behind the Continue button.

### What changed
- **Real 3D holds (`hold3d.luau` + `hold3d.wgsl`).** A `ScriptedDrawable` builds a faceted, lumpy icosphere mesh per hold kind: jug, pyramid, sloper, pinch, crimp, stone and volume. It renders the mesh into a `GPUCanvas` with a depth buffer, in three draws:
  - a graphic wall shadow;
  - a coal cut-out outline, drawn as an inverted hull;
  - the lit body, with half-Lambert light posterised per facet, contact occlusion, a bolt socket and chalk speckles concentrated on the upward faces.

  The image is drawn in the host node's local space, so every keyed position, scale, squash and 2D rotation still applies. Each node's authored roll is undone inside the script, so the light stays top-left on screen. 22 holds use it: the persistent carrier and the large holds in scenes 1, 2, 3, 5, 9 (Balance Seeker) and 10.
- **3D motion.** Timelines key the script inputs `yaw`, `pitch` and `progress` (each is a `ScriptInputNumber`, which is animatable):
  - Holds spin on their bolts as they snap into the route (scenes 1–3 and 10).
  - Scene 5's three holds tumble and rotate into one shared alignment.
  - The carrier twists against the load in the anticipation dip, then makes a full turn as it is yanked, and lands with a settle wobble.
  - The scene 1 grab hold pitches under load when pressed and rocks back on release.
  - The scene 9 Balance Seeker stone teeters in yaw as well as in roll.
  - A slow idle sway, the `sway` input, runs only while the scene is live, not paused and not in reduced motion.
- **Scene 4 kinetic stack.** This uses the script's trail mode. One mesh is drawn as a solid anchor, up to ten translucent tumbling ghosts and a solid head, which climbs with the counter through a keyed `progress` input.
- **Chalk shader (`chalk.luau` + `chalk.wgsl`).** A full-stage procedural cloud replaces the flat vector occluder. It is built from domain-warped fBm billows, lit from their own gradient, with a printed shadow band, mineral grain and a stippled powdery fringe.
  - It blooms from the yank point, drifts in the pull direction (down for the reverse lower-off) and thins from its edges as the next scene lands.
  - Origin, seed, drift, direction, amount and clear are keyed per exit.
  - The first scene opens through the tail of the same cloud.
- **Camera swing.** The yank and the lower-off now tilt the four parallax layers by different amounts, and entrances swing back with a back-ease, so the cut is no longer a pure slide.
- **Recompositions.**
  - Scene 3's route was lifted and its holds enlarged.
  - Scene 6 has a concrete ledge with floor bolts and a slack rope that runs from the coil to the carrier.
  - Scene 7's panels are extruded into an isometric staircase (coal face, chalk cap, shaded side) that stands on a ground line above the controls.
  - Scene 8's web was redrawn inside the safe area.
  - Coal holds have fewer speckles, so they stop reading as glitter.

### How the GPU work stays bounded
- **`live` gating.** Every 3D hold has a `live` input that each scene entrance keys: 1 for that scene's holds, 0 for every other scene's. Off-screen holds issue no passes and no draws. Only the carrier is always live.
- **Re-render only on change.** A canvas is re-rendered only when its pose key (yaw, pitch, roll, sway clock, progress, colour) changes. A settled hold that is paused or in reduced motion costs one image draw.
- **Canvas sizes.** Canvases are 2 px per point, capped at 1100 px. Holds with the same canvas size share one depth texture. There is no MSAA: the 2x render is filtered down.
- **The chalk pass.** It runs only while `amount` is above 0: about 1.2 s per transition, as one full-screen triangle at 1 px per point.
- **Fallbacks.** If a runtime returns no shader, `hold3d` draws a vector silhouette and `chalk` draws vector puffs from the same keyed inputs.

### Reduced motion and the contract
- **Reduced motion.**
  - The `still` input is bound to `reducedMotion` and the `paused` input to `isPaused`, so both freeze the sway.
  - The reduced entrances hold every keyed yaw, pitch and progress at its final value, with the carrier at yaw 0.
  - The chalk amount is held at 0, so there is no cloud and no spin.
- **The contract is unchanged.** It is the same `UserRecap` model, property names, events, ten scenes, personas, fixtures, navigation (including the Right arrow key) and 390×844 artboard. No view model property was added: the shaders are driven only by keyed or bound script inputs. `tools/verify.py` passes 32/32 with no check changed.

### New compromises and limits
- **The flat back of a hold.** Holds have flat backs, as real ones do. In the middle of the carrier's full-turn spin, one or two frames show that back as a flat olive disc.
- **Sharpness on Retina.** Canvases are sized at 2 px per point, not at the device scale, because a `Node` script is not told the surface scale. Holds are sharp at 1x and 2x, but slightly soft at 3x.
- **Web needs a signed build.** `.wgsl` and `.luau` assets are unsigned in a local build. Web runtimes need `rive . --publish`, which requires login. WebGPU validation was not exercised; the native preview was.
- **Memory.** 22 GPU canvases are allocated up front: about 0.5–4.7 MB each, plus shared depth textures. On-device GPU time was not measured.

### Performance
`rive . --bench=600`, Apple M5 Pro, headless at 1x. Render times are CPU-side submission, not GPU time.

| | Before | After |
|---|---|---|
| `.riv` size | 788 KB | 882 KB |
| Advance, mean / p95 | 0.023 / 0.057 ms | 0.023 / 0.058 ms |
| Render submission, mean / p95, scene 1 | 0.074 / 0.089 ms | 0.138 / 0.287 ms |
| Render submission, mean / p95, scene 4 (3D stack) | — | 0.121 / 0.267 ms |
| Wasm memory growth | +0 | +0 |
