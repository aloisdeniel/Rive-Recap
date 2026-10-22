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

## Responsive layout

The recap adapts to any canvas. The host uses the runtime's **layout fit**, so the artboard is resized to the
canvas rather than scaled; the file then lays itself out for that real width × height, continuously, and again
whenever the canvas is resized (including across the breakpoint in the middle of a scene).

### The rule: one width breakpoint, two layouts

* **Landscape layout when the artboard width ≥ `layoutBreakpoint`** (default **768**), otherwise the **portrait
  layout**. It is a pure width rule: 768 × 1024 and 820 × 1180 get the landscape layout, 667 × 375 and 740 × 360
  get the portrait layout.
* `layoutBreakpoint` is a new host-owned `UserRecap` number (**contract addition**, default 768). A host may tune
  it at runtime; the layout is re-solved on the next frame.
* The current orientation is derived from the real artboard width on every resize and exposed read-only as
  `_landscape` (0/1).

**Portrait** — phone chrome: the header ticket band (wordmark, progress, year) and the dock band (Prev, Pause,
Continue). The story stacks: the poster art with its hero number on top, the copy anchored above the dock. Copy and
art scale independently — the copy is sized from the width (0.86–1.3 × the design), the art takes the height that
is left and is centred, so wider phones and tablets in portrait get a bigger poster with its art bleeding to the
sides, and short ones a smaller poster with readable copy. When the story is too short for that stack (a phone held
sideways: 667 × 375, 740 × 360) the portrait layout keeps its slim phone chrome and lets the story run side by side
(art | copy) instead of shrinking type below the minimum; on those very short canvases the share card takes the
whole story and the summary headline steps aside.

**Landscape** — a real ticket composition, not the portrait column between bars:

* the story is split into an **art panel** (left) and a **stub** (right, about 40 % of the width) separated by a
  vertical perforation with half-punched notches in the bands. The art is clipped to its panel, the copy column to
  the stub; backgrounds still bleed edge to edge.
* the copy is a poster column: its scale follows the height (headline 45–95 pt), its measure is capped so headlines
  wrap like posters, it sits vertically centred in the stub.
* scene-specific arrangements: the intro puts the year + 3D world in the panel and the greeting at the head of the
  stub with the wordmark lockup (its route stub now runs out of the perforation) and the copy at its foot; the tram
  of scene 2 brakes into the bottom-right corner of the stub under the copy; the bus of scene 3 keeps to the
  stub's right margin; the **sea of scene 6 runs under both halves**, the count and sun stand above it in the
  panel, the ferry sails to the right of the count and the copy is printed on the deep water of the stub (on very
  short canvases the stub itself turns deep water); the **persona** emblem fills the panel with its title,
  description and label beside it; the **summary card becomes a wide ticket** (wordmark, routes and persona on the
  left, a vertical perforation, the five stats in a 2 × 3 grid on the right) with the summary headline set as a
  wrapped poster headline in the stub.
* the dock keeps Prev/Pause on the left safe margin and Continue (Share/Replay on the summary) on the right one.

Everything follows the real size: backgrounds, the paper texture, the print shader and the depth shade cover the
whole artboard; bands, perforations and the **progress segments span the real width**; the tap zones (left third
back, right two-thirds next), hold-to-pause and the route chips use real coordinates; the controls never drop below
**44 × 44** (52 × 52 pt plates at the minimum chrome scale 0.86 → 44.7); text never renders below **12 px** (the
smallest labels were raised to 13–14 pt so they stay ≥ 12 px at the minimum copy scale); the three GPU canvases are
sized to their real box and re-allocated at **device resolution** (`resize` scale × group scale) when the layout
changes; full-screen transitions cover the whole artboard at every size (each scene's interchange disc is scaled so
its full size reaches the farthest corner from its focal point; the roundel bands ride it).

### Mechanism

* **One solver, bound wrappers.** `scripts/layout.luau` (a module, required by the sequencer) takes the real size
  from the sequencer's `resize(size, scale)` and returns a placement for every *placed group*. Each scene's content
  is split by the generator into placed groups (`art`, `copy`, `top`, `tram`, `lower`, `sea`, `emblem`, `card`,
  `head`, `sup`, …): plain wrapper nodes whose `x`, `y` and uniform scale are data-bound to file-owned numbers
  (`_s4artX/Y/S`, …) that the sequencer writes into `UserRecap`. No timeline keys a wrapper, so the authored
  choreography (in 390 × 844 design units inside the wrappers) and the layout never fight.
* **Copy reflows**: headline/support/persona text widths are bound (`_copyW`, …), so lines rewrap to the real
  column instead of being scaled.
* **Clips**: two clip sources (`Art panel`, `Copy column`) are bound rectangles; in portrait they cover everything.
* **Pivots**: the camera push and the outgoing scene's recede scale about bound pivots (the scene's real focal point
  `_sNPX/PY`, the real story centre `_scx/_scy`), so the keyed scales stay correct at any size; the motif (route
  dot + roundel) follows the placed group of the scene it is carrying the story into (or out of).
* **Chrome**: header and dock bands are scaled by one chrome scale `_cs` (0.86–1.3) with their contents pinned to the
  safe margins; the perforations, notches, landscape divider and progress segments are drawn by the sequencer at the
  real size. The print stock layer fills the artboard (stack cell), so its shader canvas is the real size.
* **Bleed**: art that touched the 390-wide frame continues past it (bleed stubs on the routes, a longer viaduct,
  more old town, a wider far shore and sea, longer knot lines); stubs are drawn just before/after their route so the
  timing inside the 390 frame is the authored one.
* `scripts/layoutdata.luau` is generated by `tools/gen.py` (each group's design box, each scene's focal point), so
  the solver and the art cannot drift apart.

At 390 × 844 every placement is the identity: the portrait composition is pixel-for-pixel the authored one.

### Host setup

1. Use the runtime's **layout fit** so the artboard tracks the canvas (and resize the drawing surface with the
   canvas). At the time of writing that is `Fit.Layout` on the web runtime (with `layoutScaleFactor`, and
   `resizeDrawingSurfaceToCanvas()` on resize), `.layout` on Apple, `Fit.LAYOUT` on Android and `Fit.layout` in
   Flutter — **check the Rive runtime docs for your runtime's exact option names**. With `Fit.contain` the file
   still works, as the 390 × 844 portrait poster.
2. Optionally write `layoutBreakpoint` (points; default 768) to move the switch.
3. Nothing else: orientation changes, window resizes and split-screen are handled inside the file; the current
   scene, progress, pause state and events are untouched by a resize.

### Sizes tested

Rendered with the CLI's default `--fit=layout` (`tools/responsive.py` → `captures/responsive/`, one contact sheet
per scene, top row portrait, bottom row landscape, plus a mid-transition sheet per direction):

* portrait: 320 × 568, 360 × 640, 390 × 844, 430 × 932, 600 × 960, 767 × 1024, 667 × 375, 740 × 360
* landscape: 768 × 1024, 820 × 1180, 1024 × 768, 1280 × 720, 1440 × 900, 1920 × 1080, 2560 × 1080, 1366 × 600

Checked in `tools/scenarios.py` (debug build only: the artboard size is bound to `_testW/_testH` so a headless run
can resize it mid-scene, as a host's layout fit does): the breakpoint edges (767 → portrait, 768 → landscape, short
phones portrait, `layoutBreakpoint=1300` keeps 1280 portrait), landscape taps on the real thirds, Right arrow,
Prev/Continue where they are drawn, hold-to-pause, route chips in landscape, a resize portrait → landscape in the
middle of scene 3 (scene kept, no event re-fired, progress carries on, next tap works), a resize landscape →
portrait while the 4 → 5 roundel is mid-flight, and a resize on the settled summary (`recapFinished` still once).
**20/20 pass** (the 13 original checks at 390 × 844 included).

### Compromises

* Groups scale **uniformly**; only copy text reflows. Inside a group the art keeps its proportions, so very wide
  canvases show more of the (extended) bleed rather than a recomposed illustration.
* Below roughly 330 pt of story height the portrait layout runs side by side (with phone chrome) — the closest it
  gets to the landscape composition — and the summary hides its headline/support so the share card stays readable.
* Tall landscape canvases (768 × 1024, 820 × 1180) give a narrow stub: copy runs at ~0.84 × and the art panel has
  slack above and below the poster.
* The perforation divider is drawn on top of the scene by the sequencer, so during a handoff it stays put while the
  roundel opens (it reads as part of the ticket, not of the scene).
* The share card's on-screen region now depends on the layout; capture the `Share card` node's bounds (or the
  whole artboard minus the bands) rather than fixed coordinates.
* Layout numbers are ~170 extra file-owned `_` properties on `UserRecap` (written only on resize or breakpoint
  change; nothing per frame). `.riv` 936 KB → **987 KB**.
* Headless captures are @1x; the device-resolution GPU path was exercised through the `res` inputs, not on a Retina
  device.

## What is here

| Path | What it is |
|---|---|
| `scene.rml` | The whole Rive document: one artboard, the single `UserRecap` view model, 18-layer state machine, 89 timelines. **Generated** by `tools/gen.py` + `tools/scenes.py` (edit those and re-run, or edit the RML directly and stop regenerating). |
| `scripts/sequencer.luau` | Gestures, dwell timer, visible-scene list, progress segments, count-up and idle-loop playheads, persona mapping; runs the layout solver on resize and draws perforations/divider at the real size. |
| `scripts/layout.luau` | Responsive layout solver (module): real size → placement of every group, chrome, clips, copy widths, GPU resolution. |
| `scripts/layoutdata.luau` | **Generated** design boxes and focal points the solver reads. |
| `scripts/poster3d.luau` + `.wgsl` | GPU 3D in poster inks: the intro's world disc (kind 1) and the scene-2 tram (kind 0). |
| `scripts/flapboard.luau` + `.wgsl` | GPU split-flap departure board (scene 8), dot-matrix month numbers. |
| `scripts/paper.luau` + `.wgsl` | Print-stock shader laid over the whole recap in soft-light. |
| `scripts/formatCount.luau` | Data converter: number → locale-grouped integer string. |
| `assets/fonts/` | Archivo Black, Archivo Condensed Black (static instance), Inter (SIL OFL 1.1, licences alongside). |
| `fixtures/` | `sample.json` (= `../sample-data.json`), `zero-new-user.json`, `extreme-long-copy.json`. The same three data sets are also exported as view-model instances `Fixture` (default), `NewUser`, `Extreme`. |
| `build/switchyard-recap.riv` | Runtime export (unsigned local build, see *Limitations*). |
| `captures/` | Review captures (see *Captures*). |
| `tools/scenarios.py` | 20 headless interaction tests (13 at 390 × 844 + 7 orientation/resize) with assertions (`captures/scenarios/results.txt`). |
| `tools/responsive.py` | Renders the viewport matrix and writes the `captures/responsive/` contact sheets. |
| `tools/capture.py` | Regenerates every capture (`--motion` adds a slow auto-advance GIF; `../video.webm` is the walkthrough). |

## Preview

```bash
rive apps/switchyard/rive                       # live previewer window (rebuilds on save)
rive apps/switchyard/rive --verify               # compile + reload check
rive inspect apps/switchyard/rive --summary      # wiring problems
rive apps/switchyard/rive --screenshot=out.png --advance=3s --data=currentScreen=4
rive apps/switchyard/rive --screenshot=out.png --advance=3s --data=currentScreen=9 --viewport=1280x720   # landscape
python3 tools/responsive.py --scenes 2 9 --sizes 390x844 1280x720 --out /tmp/matrix   # contact sheets
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
| **`layoutBreakpoint`** *(contract addition, responsive)* | number | Default `768`. Artboard width (points) at or above which the landscape layout is used; below it the portrait layout. Non-positive values fall back to 768. Read every frame; a change re-solves the layout. The resulting orientation is readable as `_landscape` (0/1, file-owned). |
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
`_idle1`…`_idle10` (idle-loop playheads −1..1 scrubbed by one Joystick per scene), the responsive layout outputs
(`_vw`, `_vh`, `_landscape`, `_cs`, `_s<N><group>X/Y/S`, `_s<N>PX/PY/DS`, `_m*`, `_rk*`, `_hdr*`, `_dock*`,
`_copyW*`, `_card*`, `_c*`, `_res1/2/8`, `_tramW`, …; written by the sequencer on resize), triggers `_nextTapped`, `_prevTapped`, `_pauseTapped`,
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
isolation, reduced motion — **13/13 pass** at 390 × 844; plus 7 responsive checks (see *Responsive layout*) — **20/20**.

### Host-adapter responsibilities

1. Bind the `UserRecap` instance (or set values on `Fixture`) and write all user data/copy into it — one place,
   formatted once (localised units, pluralisation, optional compact labels such as "1.2M" go into the copy strings,
   never as separate per-screen stat copies).
2. Convert `#RRGGBB` → ARGB colour for `personaColor`; clamp invalid/negative/non-finite counts before writing
   (the formatter also clamps as a safety net); write `personaIndex` first, then localised `personaName` /
   `personaDescription` in the same frame.
3. Set `isPaused = true` when backgrounded or while sharing, restore the previous value afterwards.
4. On `shareTapped`: wait for the summary to settle (or `recapFinished`), capture the node `Share card` region
   (its position depends on the layout: x 24–366, y 166–682 at 390 × 844; use the node's bounds) — it contains no
   progress bar or controls — then open the share sheet.
5. Use the runtime's **layout fit** so the artboard follows the canvas (see *Responsive layout → Host setup*);
   optionally set `layoutBreakpoint`. Give the artboard keyboard focus if your platform needs it, and expose the
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
| Responsive layout across 320 × 568 / 430 × 932 / desktop | Done: layout fit + a Luau solver placing bound group wrappers; portrait and landscape layouts split at `layoutBreakpoint` (see *Responsive layout*). |
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
`captures/responsive/` (the viewport matrix, `tools/responsive.py`), `captures/scenarios/` (interaction test end frames + `results.txt`). The full walkthrough is
`../video.webm` at 390 × 844 (`scripts/render-video.py switchyard`) and the landscape walkthrough
`../video-landscape.webm` at 1280 × 720 (`scripts/render-video.py switchyard --viewport 1280x720 --output
apps/switchyard/video-landscape.webm`).

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
* No RTL layout (no RTL target locale in the brief; text boxes are left-aligned, an RTL locale would need mirrored
  compositions). Responsive limits: see *Responsive layout → Compromises*.
* Headless captures cannot judge feel at real frame timing; the walkthrough video is 30 fps from deterministic
  headless frames. Open the
  previewer for real-time review. No live host app (iOS/Android/web) was built — the "host preview" is the Rive
  previewer plus `--data` runtime updates.
* Hold-to-pause and story taps are implemented for pointer/touch in the script; multi-touch edge cases
  (two fingers) were not tested.
