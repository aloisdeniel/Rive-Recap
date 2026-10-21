# Switchyard — 2026 Rive recap

A ten-scene, Wrapped-style public-transit recap for the fictional app **Switchyard**, authored as RML + Luau for the
Rive CLI (1.6.0). The brief is `../PROMPT.md`; the art-direction reference is `../concept.png`.

All data is fictional sample data for a fictional period (January 1 – December 31, 2026).

## Improvement pass (October 2026)

### Critique of the first pass
* **Type was timid and inconsistent.** 32–34 px Archivo Black headlines (the concept uses tall condensed poster
  headlines), 28/32/34/44 px across scenes, a 100 px gap between headline and support on scene 2, an orphaned "you."
  on the summary, and the period label rendered as a black text-highlight strip that read as a selection bug.
* **Chrome looked buggy:** a blue focus ring was always drawn round Continue; the wordmark appeared twice on scene 1.
* **Generic art in places:** a crude block skyline and comb viaduct, a cropped blob tram, a toy ferry overlapping
  "18", a wheel-like City Connector emblem far from the concept's ring-framed city, flat 1-layer persona scenery.
* **Motion:** the signature transition was one thin ring and a circle wipe; the dot's trail was zero-length
  (invisible); the outgoing scene only lifted 28 px; no follow-through; reverse was a slide. The "departure board" was
  a `scaleY` squash. Pause eased loops back to rest instead of freezing. The intro opened on black.
* **Material:** all flat screen colour, no print or depth. `inspect` warned `no-default-artboard`.

### What changed
1. **Type system.** Headlines are Archivo Condensed Black 50/46 (persona title 64, summary 40, one line fitted),
   bottom-aligned on one baseline (y 650) so supports always sit 14 px below the last line; supports Inter 18/24;
   hero numbers Archivo Black with tight tracking. Period label is a route stub + label; greeting moved to the top.
2. **Signature transition rebuilt** (see Motion design): dip → trail-drawing run → four-band roundel pop with the
   next scene in its centre → squeeze → breath out with staggered bands → camera push-through; outgoing scene recedes
   under a depth shade. Reverse mirrors it. A paper base means the very first frame is the poster, not black.
3. **GPU 3D world disc (scene 1).** `poster3d` kind 1: the interchange roundel made solid — a cream board with
   blue/yellow/red rim bands, extruded route ribbons, rising blocks, station pucks with ink rims. It begins as a flat
   plan seen from above (matching the roundel that just opened) and the camera dives into an isometric view while
   the build input swells ribbons along their length and pops pucks with overshoot; idle sways the board.
4. **GPU 3D tram (scene 2).** `poster3d` kind 0: a lofted tram body with a sloped windscreen, livery painted in the
   fragment shader (windows, doors, headlights, destination blind, red stripe, roof), pantograph, contact shadow and
   ground stripes that fade into the distance. It brakes in from the vanishing point; idle sway.
5. **GPU split-flap board (scene 8).** `flapboard`: 12 instanced modules (one draw), each a static top half, static
   bottom half and a falling flap in perspective (gravity + shade on the half it covers, back face shows the next
   character), 5×7 dot-matrix month numbers, rolling through random numbers with a stagger; `active` is bound to
   `activeMonths`; idle ticks.
6. **Print stock shader** over everything (soft-light paper tooth, fibres, cloudy formation, flecks).
7. **Recompositions:** scene 2 old town with clock tower and arched viaduct + 3-car train; scene 3 orbits as transit
   lines with circling station-planets; scene 4 grey city architecture behind the lines; scene 6 paddle-steamer, sun
   with turning rays, quay; City Connector now the concept's ring-framed city (skyline, bridge, lake, a red train
   crossing in idle); Scenic Rider three-layer parallax (peaks, hills, catenary poles); Route Collector tickets with
   termini, barcode, print lines and a punch hole; welcoming summary in the condensed face.
8. **True pause freeze:** each scene's idle loop is a 480-frame timeline scrubbed by a `Joystick` bound to a new
   file-owned playhead `_idle1…_idle10`, advanced by the sequencer only while that scene is current, settled, playing
   and in full motion. Pause freezes mid-motion (`captures/gpu/pause_freeze_a/b.png`), reduced motion stays on frame
   0 (the rest pose), the leaving scene's loop simply stops (no snap). Idle keys only dedicated wrapper nodes; the
   generator refuses any idle key that another state also keys.
9. **Controls:** focus ring only after Tab (`_focusVisible`, reset by pointer input, like `:focus-visible`); summary
   dock hides Pause and shows Share (tray-arrow glyph) and Replay with a rebuilt replay icon — an open
   counter-clockwise arc whose arrowhead is computed from the arc's end point and tangent; ticket-notch perforations.
10. **Fonts:** full Archivo Black, a condensed Archivo instance, and Inter widened to Greek/Cyrillic/Vietnamese.
11. **`no-default-artboard` fixed** (the artboard now has an id that `rive.yaml`'s `main` resolves to).

### 3D / shader techniques (and where not)
* Used: `GPUCanvas` + WGSL with depth and 4× MSAA (when the device offers it); vertex-shader build animation
  (per-vertex start time + centre); inverted-hull ink outlines with per-vertex outline normals; object-space light
  quantised into three printed tones that shade toward ink, not black; procedural decals; an instanced flap board
  computing its whole roll in the vertex shader; a fullscreen-triangle paper shader rendered once per size. Every
  input is a keyed `ScriptInputNumber`, so choreography stays in state-machine timelines; `live` is keyed 0 in each
  scene's Hidden state so off-screen pieces do no GPU work.
* Not used: imported meshes/textures (everything is procedural), a 3D scene-5 map (kept flat on purpose — the brief
  asks for a strictly schematic map and a second tilted map would repeat the intro), and 3D for type, copy or the
  share card (vector is sharper and stays editable/accessible).
* Reduced motion: the Settled state holds every 3D input at its final value (static poses), idle playheads stay at
  rest, transitions are the 220 ms opacity fade.

### New compromises
* GPU scripting is required for the 3D/print look. Without it, `poster3d` draws a flat vector stand-in (plan view of
  the disc's lines / a blue tram silhouette), `flapboard` draws plain tiles (no digits), and the paper is skipped.
* 3D canvases render at 2 px per point; on 3× screens they are slightly softer than the vector art.
* `_focusVisible` and `_idle1…_idle10` are new file-owned (underscore) properties on `UserRecap`; hosts must not write them.
* The roundel adds ~1,200 keyframes, part of the `.riv` growth; the persona scene keeps a ~0.5 s blue beat before the
  emblem lands (the anticipation orbit), which some may find long.
* Long Share/Replay labels ellipsize inside fixed pills.

## What is here

| Path | What it is |
|---|---|
| `scene.rml` | The whole Rive document: one artboard, the single `UserRecap` view model, 18-layer state machine, 89 timelines. **Generated** by `tools/gen.py` + `tools/scenes.py` (edit those and re-run, or edit the RML directly and stop regenerating). |
| `scripts/sequencer.luau` | Gestures, dwell timer, visible-scene list, progress segments, count-up and idle-loop playheads, persona mapping. |
| `scripts/poster3d.luau` + `.wgsl` | GPU 3D in poster inks: the intro's world disc (kind 1) and the scene-2 tram (kind 0). |
| `scripts/flapboard.luau` + `.wgsl` | GPU split-flap departure board (scene 8), dot-matrix month numbers. |
| `scripts/paper.luau` + `.wgsl` | Print-stock shader laid over the whole recap in soft-light. |
| `scripts/formatCount.luau` | Data converter: number → locale-grouped integer string. |
| `assets/fonts/` | Archivo Black, Archivo Condensed Black (static instance), Inter (SIL OFL 1.1, licences alongside). |
| `fixtures/` | `sample.json` (= `../sample-data.json`), `zero-new-user.json`, `extreme-long-copy.json`. The same three data sets are also exported as view-model instances `Fixture` (default), `NewUser`, `Extreme`. |
| `build/switchyard-recap.riv` | Runtime export (unsigned local build, see *Limitations*). |
| `captures/` | Review captures (see *Captures*). |
| `tools/scenarios.py` | 13 headless interaction tests with assertions (`captures/scenarios/results.txt`). |
| `tools/capture.py` | Regenerates every capture (`--motion` adds a slow auto-advance GIF; `../video.webm` is the walkthrough). |

## Preview

```bash
rive apps/switchyard/rive                       # live previewer window (rebuilds on save)
rive apps/switchyard/rive --verify               # compile + reload check
rive inspect apps/switchyard/rive --summary      # wiring problems
rive apps/switchyard/rive --screenshot=out.png --advance=3s --data=currentScreen=4
```

Useful `--data` switches (they set the bound `UserRecap` instance): `currentScreen=N`, `personaIndex=0..3`,
`reducedMotion=true`, `isPaused=true`, `autoAdvanceSeconds=4`, `showScreen5=false`, `locale=de-DE`,
`shareIncludeName=true`. `python3 tools/run.py`'s `fixture_args()` turns a fixture JSON into `--data` flags.

Controls: tap the right two-thirds of the story window → next, left third → previous; press-and-hold
(>350 ms) pauses while held (release never navigates); Right/Left arrows, Space = pause/play, Tab/Shift-Tab move
focus, Enter activates the focused button. On scene 4 tap the **R4 / B12 / Y7** route chips (signature interaction).

Rebuild after editing the generator:

```bash
cd apps/switchyard/rive && python3 tools/gen.py && rive . --verify && rive inspect . --summary
python3 tools/scenarios.py          # interaction assertions (rebuilds a debug-event variant, then restores)
```

## Architecture

* **One artboard** `Switchyard Recap`, 390 × 844, bound to **one view model `UserRecap`** (exported instance
  `Fixture`). Every scene, the persistent motif, the summary card, progress, controls and persona visuals bind to that
  same instance; nothing duplicates a statistic (the summary reads `journeys`, `distanceKm`, … directly).
* Scene hierarchy: `Recap` (keyboard scope) → `Header ticket band`, `Dock ticket band` (controls), `Motif`
  (persistent route dot, per-scene route trails, four-band interchange roundel), `Scene 10 … Scene 1` (each: a
  `Camera` node holding a `Depth shade`, `Content` and `Background`, clipped by its own interchange disc), a paper
  base, `Clip sources`. A `Print layer` (absolute-positioned `ScriptedLayout`, paper shader) sits on top of all of it.
* **State machine `Recap Sequencer`**, 18 layers:
  * `Scene 1` … `Scene 10` — each: `Hidden → EnterFwd | EnterBack | Settled(RM) → Settled → ExitFwd |
    ExitBack → Hidden`, all guarded on `currentScreen`, `_navDir`, `reducedMotion`. Idle loops are not states: each
    scene's loop is a 480-frame timeline scrubbed by a `Joystick` bound to `_idleN` (see Improvement pass). Scene 9 has four
    `EnterFwd` states, one per persona. Re-entry from a half-played exit is wired, so rapid navigation always settles
    on the last requested scene with no stacked layers.
  * `Events: screenChanged` (one state per canonical id), `Events: recapFinished latch`, `Dock`, `Pause icon`,
    `Greeting visibility`, `Share privacy: name`, `Summary variant`, `Signature: route chips`.
* **Sequencer script** (a full-artboard `ScriptedLayout`) is the single navigation authority. Buttons, keys and
  semantic actions fire view-model triggers; the script listens and moves `currentScreen`.

## Binding / event contract

Owner: **host** = host app/adapter writes it; **file** = the Rive file writes it (host may read); **both** = host may
set it, the file also writes it.

### User data and copy (host-owned)

| Property | Type | Notes / formatting |
|---|---|---|
| `userName` | string | Greeting on scene 1 (hidden when empty), summary card only when `shareIncludeName` is true. Ellipsis-truncated, never shrinks UI. |
| `year` | number | Rendered with `DataConverterToString` (no grouping). |
| `periodLabel` | string | Localised by host. Ticket chip on scene 1; summary card stub. |
| `locale` | string | Read once by `formatCount` at load to choose the digit-group separator (`,` en; `.` de/es/it/nl/pt/da/id/tr; U+202F fr/sv/nb/fi/pl/cs/ru/uk; `’` de-CH). Changing locale at runtime requires reloading the instance. |
| `journeys`, `distanceKm`, `routesExplored`, `stationsVisited`, `ferryTrips`, `weekendOutings`, `activeMonths` | number | Integer counts. Displayed through `formatCount` (rounds, clamps negative/NaN/∞ to 0, groups digits). Hero numbers animate 0 → value; the accessible label (`SemanticData` on each hero) always carries the exact final value. Very large values use `fitFontSize` (shrink-to-fit of that one numeral only). `activeMonths` also lights board tiles (`RangeMapper` per month). |
| `personaIndex` | number | 0–3 selects the persona row; anything else falls back to row 0. Negative = "no persona" (scene hidden only if `personaName` is empty). |
| `personaName`, `personaDescription` | string | Host-localised. See *Persona mapping*. |
| `personaColor` | **color** (ARGB) | The JSON `"#1B4ED0"` must be converted to `0xFF1B4ED0` by the adapter. The sequencer re-derives it from `personaIndex` so label/palette/emblem cannot disagree. |
| `introHeadline`, `introSupport`, `summaryHeadline`, `summarySupport`, `emptyHeadline`, `emptySupport`, `personaLabel`, `screen2…8Headline/Support/Unit` | string | All localised copy is bound; nothing is baked. Units must arrive already pluralised (`"journey"` vs `"journeys"`) — the file does no pluralisation. Headlines sit in fixed boxes with `fitFontSize` as a safety net for +40 % copy; supports/units ellipsize at 2 lines. |
| `continueLabel`, `previousLabel`, `pauseLabel`, `playLabel`, `shareLabel`, `replayLabel` | string | Button labels + semantic labels. |
| **`greetingLabel`** *(adapter addition)* | string | `"Hi,"` — the localised greeting word before `userName`. |
| `showScreen1` … `showScreen10` | boolean | Eligibility. 1 and 10 are always kept (invalid input degrades to intro → summary). 9 also requires stats and a non-empty `personaName`. All of 2–8 false ⇒ new-user path: intro → welcoming summary (`emptyHeadline`/`emptySupport`, no stats, no persona). |
| `autoAdvanceSeconds` | number | Dwell after the entrance settles; clamped to 4–60 s. |
| `autoAdvanceEnabled` | boolean | Off ⇒ manual only. |
| `reducedMotion` | boolean | Immediate final values, static compositions, 220 ms opacity cross-fades, no motif/camera movement, idle loops off. |
| `soundEnabled` | boolean | Accepted, unused: the piece is silent by design (no audio assets). |
| `shareIncludeName` | boolean | Default false ⇒ name never appears on the card. |
| `shareIncludeSensitiveValues` | boolean | Accepted and passed through. UserRecap holds no sensitive raw content (only aggregates + persona), so the card has nothing to gate; the host must still honour it in its share pipeline. |

### Sequencing (both)

| Property | Type | Notes |
|---|---|---|
| `currentScreen` | number | Canonical 1-based scene id (stable when scenes are hidden). Written by the sequencer; a host write is treated as a jump (snapped forward to the next visible scene). |
| `screenProgress` | number | 0–1 dwell progress of the current scene (summary: 0–1 settle). Read-only for hosts. |
| `isPaused` | boolean | Host sets it for background/foreground and while a share sheet is open (restore the previous value afterwards). The file toggles it from the pause button/Space and temporarily during press-and-hold (restored on release). |

### File-owned additions (prefixed `_`; hosts must not write)

`_navDir` (+1/−1), `_count2`…`_count8` (count-up playheads 0–1), `_personaSlot` (0–3), `_isEmpty`,
`_personaInk` (color: text ink on the persona background), `_pauseButtonLabel`, `_activeRoute` (0–3, route chips),
`_focusIndex` (focused dock button, drives focus rings), `_focusVisible` (0/1: rings shown only after Tab),
`_idle1`…`_idle10` (idle-loop playheads −1..1 scrubbed by one Joystick per scene), triggers `_nextTapped`, `_prevTapped`, `_pauseTapped`,
`_replayTapped`, `_replay`. They are animation playheads / control signals, not user data.

### Events (state-machine events reported to the host)

| Event | When | Payload |
|---|---|---|
| `screenChanged` | Every change of `currentScreen` (and once at start for scene 1). | Custom property `screen` (number) bound to `currentScreen`. If your runtime does not surface event properties, read `currentScreen` from the instance. |
| `shareTapped` | Share button (click, Enter, or screen-reader tap). | none — host captures the card and opens the platform share sheet. **Only event wiring is supplied; there is no real share integration in the file.** |
| `recapFinished` | Once, 1.8 s after the summary first becomes current (settled). Navigating away/back does not re-fire; **Replay** resets the latch. | none |

Verified headlessly by `tools/scenarios.py` (events temporarily built as `OpenUrlEvent`s so the CLI logs them):
next/back, rapid taps, hold/release, pause/resume, keyboard, hidden scenes, full auto-advance (10 × `screenChanged`,
1 × `recapFinished`), share + replay latch, auto-advance off, zero user, unknown persona fallback, route-chip
isolation, reduced motion — **13/13 pass**.

### Host-adapter responsibilities

1. Bind the `UserRecap` instance (or set values on `Fixture`) and write all user data/copy into it — one place,
   formatted once (localised units, pluralisation, optional compact labels such as "1.2M" go into the copy strings,
   never as separate per-screen stat copies).
2. Convert `#RRGGBB` → ARGB colour for `personaColor`; clamp invalid/negative/non-finite counts before writing
   (the formatter also clamps as a safety net); write `personaIndex` first, then localised `personaName` /
   `personaDescription` in the same frame.
3. Set `isPaused = true` when backgrounded or while sharing, restore the previous value afterwards.
4. On `shareTapped`: wait for the summary to settle (or `recapFinished`), capture the node `Share card` region
   (x 24–366, y 166–682 in artboard units) — it contains no progress bar or controls — then open the share sheet.
5. Use **Fit.contain** with alignment centre and a `#F5F2E9` letterbox (the master artboard is a fixed 390 × 844
   composition; see *Limitations*). Give the artboard keyboard focus if your platform needs it, and expose the
   `SemanticData` tree (buttons are labelled from the bound label strings; the current scene's hero number
   carries its exact value as label and its unit as value; offscreen scenes and summary-only buttons are marked
   hidden). Headlines are not separately announced — post a screen announcement from `screenChanged`.
6. For web delivery, build signed with `rive --publish` (scripts in a local build are unsigned).

### Persona mapping

| `personaIndex` | Persona (default copy) | Emblem | Accent / background | Ink | Reveal choreography |
|---|---|---|---|---|---|
| 0 | City Connector — "You make the connections." | interchange knot | `#1B4ED0` | warm white | four lines shoot through the core, orbit ring springs out (elastic), stations spin into place |
| 1 | Scenic Rider — "You enjoy the view along the way." | window with passing shapes | `#FFD64B` | black | frame opens from a horizontal slit, landscape slides through the clipped glass, sill extends |
| 2 | Route Collector — "There is always another line to try." | stacked route tickets | `#F5F2E9` | black | four tickets are dealt from below and spin into a fan |
| 3 | Weekend Roamer — "You give curiosity a destination." | compass-like station ring | `#171B20` | warm white | ring draws on, stations pop in sequence, needle spins two turns and settles (elastic) |

All four share the anticipation beat (route dot orbits the interchange ring before the persona colour floods the
screen). Mapping is done in `sequencer.luau` (`applyPersona`): slot, colour and ink always follow the index;
English default copy is filled only when the copy is empty, stale (another row's default) or the index changes at
runtime — so a host's localised strings are kept.

## Motion design

* **Signature transition (forward), ~880 ms:** the red route dot dips (anticipation), runs an angular schematic
  route to the next scene's focal point while its trail draws behind it and retracts, and dives into an interchange
  roundel (blue/yellow/red bands + ink rim) that pops in band by band with the next scene already visible through its
  centre. The roundel squeezes, then "breathes out" (slow start, very fast middle, long settle) until it is the whole
  screen, its colour bands riding the clip edge with a 1-frame stagger so they spread at peak speed. The outgoing
  scene recedes (scales to 0.9 toward the window centre) under a depth shade; the incoming camera is pushed through
  the ring (1.14 → 1, follow-through).
* **Reverse transition, ~730 ms:** the scene breathes back into its roundel (bands contracting outside the shrinking
  clip, outer band first), the roundel closes, the dot re-emerges and drops back down its route; the previous scene
  comes forward again from where it receded (0.9 → 1, shade lifts) and re-sets its headline.
* **Continuity objects:** the motif (dot + ring) is one persistent group carried across every handoff; the ring
  becomes each scene's edge. Scene 1 establishes it (wordmark lockup is the same ring + route stub).
* **Hero sequences:** (1) Invitation — the roundel opens onto a flat plan of a round world board that the camera
  dives into (GPU 3D): route ribbons swell along their length, blocks rise, station pucks pop, while the oversized
  year rolls in and the wordmark is revealed by its route stub; (2) Journeys — a route dot draws the angular network
  around the count, stations pop as it passes, the train crosses the arched viaduct and a 3D tram brakes into the stop; (3) Km — orbits draw, a ticket strip feeds from a slot
  through a measuring frame carrying the unit; (5) Stations — a strictly schematic map draws on linear timing and
  stations populate in reading order; (6) Ferry — wave bands rise in sequence, the ferry sails in and settles;
  (7) Weekend — a white ticket drops, tears along its perforation, and the halves become red/blue weekend panels;
  (8) Months — a real split-flap board: twelve 3D flap modules roll through random numbers and land on their month
  in a dot-matrix face, staggered, lit by `activeMonths`;
  (9) persona reveals above; (10) Summary — the collectible ticket card is thrown in, lines draw, persona disc pops,
  stat cells stamp in sequence.
* **Counting:** 200 → 1200 ms, ease-out cubic, driven by the sequencer (`_countN` × value through a formula
  converter) so digits never flash placeholders and pause freezes the count.
* **Idle loops** (restrained, seamless): riders running routes with faded ends, orbit rotation, hub breathing,
  station pulse, wave bands translating exactly one crest period, ferry bob, slow sun-ray turn, occasional board
  tick, persona micro-motion (parallax landscape, a train crossing the city vignette). Pause freezes them mid-motion;
  reduced motion keeps them on their rest pose.

## Fonts and licences

| File | Family | Source | Licence |
|---|---|---|---|
| `assets/fonts/ArchivoBlack-Regular.ttf` | Archivo Black Regular (full, unsubset) — hero numbers, wordmark | github.com/google/fonts `ofl/archivoblack` | SIL OFL 1.1 (`OFL-ArchivoBlack.txt`) |
| `assets/fonts/ArchivoCondensedBlack-Switchyard.ttf` | Archivo, static instance `wght` 900 / `wdth` 72 — headlines | github.com/google/fonts `ofl/archivo` (`Archivo[wdth,wght].ttf`) | SIL OFL 1.1 (`OFL-Archivo.txt`) |
| `assets/fonts/Inter-Switchyard.ttf` | Inter (variable `wght`, `opsz` pinned 14) — labels | github.com/google/fonts `ofl/inter` (`Inter[opsz,wght].ttf`) | SIL OFL 1.1 (`OFL-Inter.txt`) |

Archivo Black ships whole. Archivo Condensed Black and Inter were instanced/subset with fontTools to Latin,
Latin Extended A/B, IPA schwa, combining marks, **Greek, Cyrillic (incl. Cyrillic Supplement)**, Latin Extended
Additional (Vietnamese), general punctuation, currency, letterlike symbols and arrows. Archivo Black and Archivo have
no Cyrillic/Greek glyphs at all (the families do not draw them), so display type in those scripts falls back per
runtime; Inter covers them for labels. CJK, Arabic, Hebrew and Indic scripts are not included.

## Unsupported techniques and substitutions

| Brief asks for | What was done |
|---|---|
| Responsive layout across 320 × 568 / 430 × 932 / desktop | Fixed 390 × 844 master composition presented with `Fit.contain` (verified in `captures/viewports/`). A true reflowing layout of layered vector illustration was not attempted; at 320 × 568 the piece scales to ~67 %. |
| Event payloads | `screenChanged` carries a bound `screen` custom property; hosts without event-property support read `currentScreen`. |
| Locale-aware formatting | Built-in converters cannot group digits, so a Luau `ScriptedDataConverter` does it; plurals and compact labels are host-adapter work. |
| Pause freezes decorative motion | Done (improvement pass): idle loops are scrubbed by Joysticks from sequencer-owned playheads that stop while paused. GPU pieces' idle inputs are keyed in those loops, so they freeze too. |
| Raster grain / tactile texture | A procedural print-stock shader (`paper.wgsl`), rendered once per size and drawn in soft-light; no raster assets, never carries text. |
| Keyboard "focus visible" | Blue focus ring on dock buttons driven by focus/blur listeners. The file focuses Continue at start (and Share on the summary), so the ring is visible from the first frame. |
| Hidden decorative hit regions | Route chips are hit-tested inside the sequencer script (only on scene 4), so invisible chips can never intercept taps. |
| Single *global* view model | Implemented as one artboard-bound `UserRecap` instance (not Rive's `viewModelType="global"`), because the CLI's `--data`, scripts' `context:viewModel()` and per-fixture instances all need the bound form. There is still exactly one instance in play at runtime. |
| Sound | None (silent by design; `soundEnabled` is accepted and ignored). |

## Measurements (CLI headless, Apple M5 Pro, macOS 26.6.2)

`rive . --bench=600 --data=currentScreen=N`, release-baked scripts, 390 × 844 @1x. The "after" run was taken while
three other recap renders were using the CPU, so means and maxima are inflated; p50 is the most comparable figure.

| | before (advance mean / p95, render mean / p95) | after (advance mean / p50 / p95, render mean / p50 / p95) |
|---|---|---|
| scene 1 (3D world disc) | 0.017 / 0.051, 0.073 / 0.091 ms | 0.067 / 0.023 / 0.162, 0.266 / 0.151 / 0.439 ms |
| scene 2 (3D tram) | 0.018 / 0.056, 0.079 / 0.098 ms | 0.128 / 0.028 / 0.142, 0.339 / 0.160 / 0.526 ms |
| scene 8 (split-flap board) | 0.015 / 0.048, 0.074 / 0.097 ms | 0.063 / 0.031 / 0.099, 0.314 / 0.146 / 0.330 ms |
| scene 9 (persona) | — | 0.055 / 0.034 / 0.125, 0.363 / 0.165 / 0.453 ms |
| scene 10 (summary) | — | 0.075 / 0.019 / 0.058, 0.238 / 0.165 / 0.392 ms |
| 1200 frames, auto-advance 4 s | — | 0.055 / 0.036 / 0.131, 0.276 / 0.142 / 0.405 ms |

Single 10–60 ms maxima are first-frame pipeline compiles / canvas allocation. Script memory: 0 wasm-page growth.
`.riv`: 323 KB → **936 KB** (fonts 513 KB: full Archivo Black, a condensed Archivo instance, Inter with
Greek/Cyrillic/Vietnamese; four GPU scripts + shaders ≈ 45 KB; the rest is the larger roundel/camera keyframe set).
These are CPU-side CLI timings, **not** on-device GPU frame rates — no phone was available. GPU work per frame:
only the pieces of the scene on screen render (`live` gating); a canvas re-renders only when one of its inputs
changed (during the dive, the tram's arrival, a flap roll, or an idle sway), otherwise it costs one image draw.
GPU memory (estimate): world disc 780 × 524 and tram 780 × 672 canvases + 4× MSAA colour/depth each (~9 MB and
~11 MB), flap board 780 × 480 (~8 MB), print stock one screen-sized canvas (~1.3 MB at @1x): ≈30 MB.
Budgets kept: one clip mask per scene, ≤16 parallax poles, 12 flap modules (instanced, one draw), no per-count objects.

## Captures

Regenerated by `tools/capture.py` after the improvement pass (stale ones were replaced, not added to):
`captures/settled/` (all ten scenes + sheets), `captures/personas/` (each persona settled + three reveal frames),
`captures/reduced-motion/` (static 3D poses, 220 ms fade), `captures/fixtures/` (zero/new user, extreme/long copy on
every scene, name opt-in, runtime update `journeys=9999`, `de-DE` grouping), `captures/transitions/` (three frames of
every forward roundel handoff 1→10, reverse collapses 3→2 / 6→5 / 10→9, route-chip ride), `captures/gpu/` (the intro
camera dive, the tram braking, the flap roll, and a pause-freeze pair that differs only in the pause icon),
`captures/viewports/`, `captures/scenarios/` (interaction test end frames + `results.txt`). The full walkthrough is
`../video.webm` (`scripts/render-video.py switchyard`).

## Limitations (honest list)

* **`.rev` (editor export) not produced** unless someone runs `rive login` and then
  `rive apps/switchyard/rive --once --rev=apps/switchyard/rive/build/switchyard-recap.rev`. Editor opening is
  therefore unverified.
* The `.riv` is an unsigned local build containing six Luau scripts and four WGSL shaders: it needs a Rive runtime
  with scripting (and GPU scripting for the 3D/print pieces), and web runtimes reject unsigned scripts — use
  `rive --publish` (login required) for web. Without GPU shaders the 3D pieces draw flat vector stand-ins and the
  print stock is skipped.
* Without the sequencer script nothing navigates (taps, timer, progress bar, count-up and persona mapping live
  there). The progress segments are script-drawn, so they are not editable as vector layers in the editor.
* Fixed composition + `Fit.contain` instead of true responsive reflow; no RTL layout (no RTL target locale in
  the brief; text boxes are left-aligned, an RTL locale would need mirrored compositions).
* Headless captures cannot judge feel at real frame timing; the walkthrough video is 30 fps from deterministic
  headless frames. Open the
  previewer for real-time review. No live host app (iOS/Android/web) was built — the "host preview" is the Rive
  previewer plus `--data` runtime updates.
* Hold-to-pause and story taps are implemented for pointer/touch in the script; multi-touch edge cases
  (two fingers) were not tested.
