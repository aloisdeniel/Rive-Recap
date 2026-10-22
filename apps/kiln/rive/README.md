# Kiln — 2026 recap (Rive)

A ten-scene, Wrapped-style ceramics-studio recap for the fictional app **Kiln**,
authored as RML + Luau with the Rive CLI (1.6.0). Brief: `../PROMPT.md`.
All data is the fictional fixture in `fixtures/`; nothing here is measured real activity.

## Preview and build

```bash
cd apps/kiln/rive
rive .                                    # live previewer (window, rebuilds on save)
rive . --verify && rive inspect . --summary
rive . --once                             # -> build/kiln-recap.riv
rive . --once --rev=build/kiln-recap.rev  # needs `rive login` (see "Exports")
python3 tools/gen_kiln.py                 # regenerate scene.rml (default instance: Fixture)
python3 tools/gen_kiln.py --default NewUser|Extreme --out <dir>/scene.rml
tools/check_interactions.sh               # headless navigation/event checks (prints VM values)
tools/check_responsive.sh                 # orientation, breakpoint, landscape input, mid-scene resize
tools/capture_all.sh [section…]           # regenerates captures/
```

Any size works: the previewer's default `--fit=layout` resizes the artboard to the window, and
`--viewport=WxH` renders it laid out at that size (see "Responsive layout").

### Project layout

| Path | What |
|---|---|
| `scene.rml` | the whole document (generated, but plain editable RML; ~2.8 MB because every state animation keys the full property union — see Limitations) |
| `tools/gen_kiln.py`, `chrome.py`, `scenes.py`, `motif.py`, `motif_build.py`, `v3d.py`, `sharecard.py`, `model.py`, `rml.py` | generator: view model, chrome, the ten scenes, the vessel/plinth motif, the 3D vessel inputs, the share card |
| `tools/resize_harness.py`, `check_responsive.sh`, `contact_sheet.py` | check-only resize harness (KilnRecap nested in a resizing artboard, never shipped), responsive checks, capture contact sheets |
| `scripts/vessel3d.luau` + `vessel3d.wgsl` | the 3D thrown pot: a GPU-lathed, lit, glazed vessel (ScriptedDrawable), used by the motif, the four persona emblems and the share card |
| `scripts/kiln.luau` + `kiln.wgsl` | the scene-5 kiln chamber: firebrick courses that heat, flicker and cool into the palette (fragment shader) |
| `scripts/grain.luau` + `grain.wgsl` | a static matte-mineral grain laid over the background colour (rendered once, drawn in soft-light) |
| `scripts/sequencer.luau` | clock + navigation brain + responsive placement (ScriptedLayout behind the recap) |
| `scripts/recap_rules.luau` | shared visibility / privacy / persona-fallback rules (module) |
| `scripts/card_rules.luau` | applies those rules when ShareCard is rendered on its own |
| `scripts/format.luau` | locale-aware number formatter (ScriptedDataConverter) |
| `fixtures/fixture.json`, `new-user.json`, `extreme.json` | the three exported view-model instances |
| `assets/fonts/` | DM Serif Display, Manrope (SIL OFL 1.1, licence texts alongside) |
| `captures/` | settled scenes, personas, transitions, reduced motion, fixtures, responsive, share card, motion preview |

### Artboards

* **KilnRecap** (authored at 390 × 844, default, state machine `Recap`) — the experience; it lays
  itself out at any size (portrait below 768 wide, landscape from 768).
* **ShareCard** (300 × 440, component) — the collectible card. Nested in scene 10 and
  assembled there through a `NestedRemapAnimation`; its authored pose is the settled
  card, so a host can instantiate it alone, bind the same `UserRecap` instance and
  snapshot it with no chrome or progress bar (`captures/share-card/`).

## Structure and choreography

Scene hierarchy (front to back): sequencer script → header (wordmark, progress, year)
→ footer controls → ten copy columns (layout, responsive) → card stage → **art stage**
(scene fronts → persona emblems → persistent 3D vessel + vector plinth → scene backs) → grain.

State machine `Recap`, 17 layers:

* **Scene 1…10** — each: Hidden → Enter / Enter Back / Enter Reduced → Idle ⇄ Frozen →
  Exit / Exit Back / Exit Reduced → Hidden, gated by `currentScreen`, `_navDir`,
  `reducedMotion`, `_frozen`. Every animation in a layer keys the same property union,
  so interrupting at any point settles deterministically (rapid taps end clean on the
  final requested scene — `captures/…`, `check_interactions.sh`).
* **Motif** — the persistent 3D vessel and plinth. Per scene a forward handoff, a reverse
  handoff and a reduced-motion cut, entered from AnyState. Every form is the same six-row
  lathe profile (radius + axis lean per row, height) keyed as script inputs, so any two
  forms morph continuously in 3D, and the glaze, firing heat and camera are keyed alongside.
* **Persona** — four 3D emblems, each with its own reveal, idle, reduced, frozen and exit.
* **Controls** (story vs share/replay footer, focusable set, initial focus), **Pause Glyph**,
  **Events** (`screenChanged`), **Completion** (`recapFinished`), **Focus Ring** (keyboard).

Signature pieces:

| Brief | Implementation |
|---|---|
| Signature transition: vessel compresses into a clay slab that expands into the next plinth | every forward handoff (Motif layer): the glaze draws back up, the pot compresses into a lidded 3D clay slab while it re-centres with a turn of the wheel (yaw −2.2 rad → 0), then the next form is pulled up out of the slab with overshoot and its glaze flows down; the slab under it expands into the next plinth (`captures/transitions/forward-*`) |
| Signature interaction: drag rotates a turntable; release settles with weighted easing | sequencer `pointerMove` writes `_turnPhase`; the 3D vessel turns with it for real (glaze band, drips, speckle and throwing rings come round), release keeps velocity and decays exponentially, idle spin 0.02 rev/s (the wheel in scene 3 turns 3×). Each scene opens on its authored angle. Separate hit regions on scenes 1, 2, 3, 7; a drag never navigates, a still tap on the vessel still does |
| Lump → vessel, glaze flowing down a clipped silhouette, firing colour shift | scene 1: a closed lump is opened (lid → open lip), pulled up tall, then shaped, and the cobalt glaze flows down from the lip; scene 5: the raw grey pot incandesces (blackbody) while the WGSL kiln chamber heats from the floor, then both cool — the courses into the six palette bands, the pot into porcelain with its glaze |
| Hero sequences (≥3) | 1 wordmark revealed through a disc opening from the vessel; 4 the 3D jug rises, tips and pours, nine glossy tiles glaze in sequence; 5 the kiln firing; 7 six profiles morph in 3D in measured steps with the matching silhouettes lighting; 9 persona reveal |
| Continuity transitions (≥2) | the vessel/plinth carried through every scene; the vessel becomes the clay mound in 6 and the cobalt orb in 9, which is handed over to the Glaze Alchemist emblem; it compresses into the slab that becomes the card in 10 |
| Reverse navigation | separate Exit Back / Enter Back (copy drops in from above once the old copy has rewound) and Motif Back (the piece sinks into the wheel turning backwards and springs up instead of the slab handoff) |
| Copy exits | each line rewinds glyph by glyph (the reveal's text modifier run backwards, staggered top line first) while the column drifts away from the incoming scene |
| Counting | each hero number: `stat × clamp(currentScreen − N + 1, 0, 1)` → eased `DataConverterInterpolator` (1.2 s, slow start ≈ the 200 ms orient beat) → `format.luau`. No placeholder digits flash; it counts down while leaving backwards |
| Staggered reveals | text modifiers (glyph opacity + rise) per run, timed to the brief's 0–200 / 200–1200 / 1200–1800 ms score |

Persona choreographies (scene 9, after the vessel becomes a glossy cobalt orb inside
anticipation rings and sparks). Every emblem is a real 3D piece (`vessel3d`) on the plinth:
0 **Form Finder** — the asymmetric vessel is sketched as one stroke, then turns into matte
porcelain that keeps turning, with a leaning clay echo;
1 **Glaze Alchemist** — a porcelain shell tips in and its cobalt lining flows in, the travelling
orb dips into it and swells back out as a levitating glossy cobalt orb, droplets orbit;
2 **Wheel Regular** — the porcelain wheel opens, a charcoal cup is pulled into a bowl that spins
fast on the wheel (throwing rings), its white glaze dips in, ripples and a spin streak;
3 **Handbuilt Storyteller** — a clay coil pot rises coil by coil in five weighted steps, then
thumbprints are pressed into its wall (shader dents with whorl ridges), crumbs land around it.

## Improvement pass (3D, shaders, motion, consistency)

### Critique of the previous pass (what was weak)

* The hero vessel was flat-shaded vector everywhere: no form, no material, a straight glaze
  ribbon. The scene-3 bowl read as a crack in a white blob, the scene-4 jug as an unclear tilted
  shape, and the scene-9 emblem (sphere over a tilted tile) was far from the concept's lit shell.
* The "turntable" was a highlight sliding over a fixed silhouette: dragging changed nothing
  about the object itself.
* Scene 5's kiln was six flat stripes with dark seams (read as a flag, not a firing).
* The scene-6 shards ended stuck on the mound; the mound had a pointed knob.
* Every copy exit was the same block fade/slide; on reverse navigation the incoming copy
  overlapped the outgoing one.
* Overlaps: "Drag to turn" sat across the plinth edge; the share card covered the summary
  support line at 320 × 568 and its last stat label crowded the period line; long copy in
  scenes 2 and 4 ran into the hero art (dark text on the cobalt lip).
* Keyboard: focus was never drawn, Tab did not move focus at all (Rive needs explicit
  `FocusActionTraversal`), and on the summary the focused control was the off-screen Continue.
* Flat colour fields with no tactile surface, against a brief asking for matte mineral surfaces.

### What changed

1. **A real 3D thrown pot** (`scripts/vessel3d.luau` + `vessel3d.wgsl`). The mesh is only a
   (u, s) grid (72 × 83, 11.8k triangles, built once and shared); the vertex shader lathes it
   from a six-row profile (radius + axis lean per row, height) held in a uniform buffer, with an
   outer wall, a rounded lip (or a lid for slabs/lumps), an inner wall and a floor, and an
   optional true-sphere blend. Normals come from finite differences of the same profile, so any
   keyed shape is lit correctly. The fragment shader is the material: speckled stoneware with
   iron spots, grog and mottling, throwing rings in the normal, wet-clay sheen, coil ridges and
   pressed thumbprints; a cobalt glaze (dipped rim with drip fingers, flowing S-band, glazed
   interior) that pools darker at drips and breaks lighter over edges, with Blinn-Phong plus two
   studio softbox reflections; and a blackbody `heat` term for the firing. The light is
   counter-rotated by the node's roll so tipped pieces (the jug) stay lit from the top-left.
   4× MSAA where the GPU offers it, rendered at 2 px per point; the canvas re-renders only when
   an input or the turntable angle changes. All shape/material values are ScriptInputs keyed by
   the existing state-machine layers, so choreography stays in the timelines.
2. **Signature transition rebuilt in 3D**: the glaze draws back up the pot, the pot compresses
   into a lidded clay slab while the wheel re-centres it (a 2.2 rad turn), then the next form is
   pulled up out of it with overshoot and its glaze flows down; scene 1 now opens a closed lump,
   pulls it up tall and shapes it. The turntable is real: dragging turns the actual pot (glaze,
   drips, speckle come round), with inertia; each scene opens on its authored angle.
3. **Scene 5 kiln chamber shader** (`kiln.wgsl`): firebrick courses in running bond heat from the
   floor up (dull red → orange-yellow) with rising heat haze and ember flicker, then cool from
   the crown down into the six palette bands, while the pot incandesces and cools into porcelain
   with its glaze. The keyed vector bands stay underneath as the no-GPU fallback.
4. **3D persona emblems**: Form Finder (sketch → turning porcelain), Glaze Alchemist (cobalt-lined
   shell + levitating glossy orb handed over from the motif), Wheel Regular (charcoal bowl pulled
   up and spun on the wheel), Handbuilt Storyteller (coil pot rising coil by coil, thumbprints).
5. **Glaze tiles** got thickness, a contact shadow and a gloss reflection clipped to the glaze;
   the scene-3 bowl became a white-glazed porcelain bowl spinning on the wheel (reads on the
   ultramarine), the scene-8 cup a dipped cup in its wrap, the card's mini motif the same 3D pot.
6. **Motion**: copy exits rewind glyph by glyph (staggered, top line first); reverse entrances wait
   for the old copy to clear; shards now tumble in, hang at the mound's edge and merge into it.
7. **Fixes**: hint engraved on the plinth face; card placement keeps clear of the summary copy on
   short screens and the stats/period no longer crowd; long copy beside the art is width-capped;
   the lump is a rounded dome.
8. **Keyboard focus**: Tab / Shift+Tab traversal, only the visible control set is focusable
   (`canFocus` keyed per mode, focus re-targeted once it applies), Share takes focus on the
   summary, and a focus ring (ink ring on the circle buttons, clay outline on the pills) is shown
   only after Tab, like `:focus-visible`. Driven by two state-machine inputs
   (`focusedControl`, `keyboardFocus`), not view-model data: the `UserRecap` contract is unchanged.
9. **Matte mineral grain** (`grain.wgsl`): a procedural paper/clay tooth with soft mottling and a
   few specks, rendered once per size and drawn behind all content in soft-light.

### 3D / shader techniques used (and where they were not)

* Used: GPU canvas + WGSL lathe (vertex-shader geometry from uniforms), MSAA resolve, depth
  buffer, procedural material/glaze/heat; a fragment-only fullscreen-triangle shader for the kiln
  and the grain. Everything renders headlessly (`--screenshot`, video) through the CLI.
* Not used: imported meshes/blobs (a lathe needs no mesh data), textures (all procedural), and 3D
  for the plinths, tiles, paper wrap and twig — those read well as vector and keep the art
  direction's graphic edge; the share card keeps vector everything except the pot.

### New compromises

* GPU scripting is required for the pieces to look as captured. Without it (a runtime that
  returns no shader) the pot falls back to a flat vector silhouette with a glaze band, the kiln to
  the keyed vector bands, and the grain to nothing.
* GPU memory: each 3D piece owns a 600 × 800 canvas (≈1.9 MB; the motif, five persona pieces),
  plus one shared 4× MSAA colour + depth set (≈15 MB), the card's 300 × 400 canvas, the kiln's
  450 × 570 canvas and the grain's screen-sized one: roughly 30 MB on a 390 × 844 screen. Hidden
  pieces skip all GPU work (`live` input) but keep their canvases.
* The pieces are rendered at 2 px per point. On 3× phones they are slightly softer than vector.
* The glaze is procedural (no fluid sim); the drag hit regions are still rectangles.
* Focus rings use deprecated state-machine inputs on purpose (presentation-only state that must
  not enter the host contract).

## Responsive layout

The recap adapts to any canvas size. There are **two layouts**, split by a pure **width**
breakpoint, and each one is recomputed continuously from the real artboard size. It is not
two fixed artboards scaled with letterboxing.

### The rule: `layoutBreakpoint`

* **Landscape when the artboard width is ≥ `layoutBreakpoint`** (a `UserRecap` number, default
  **768**), **portrait otherwise**. Height plays no part in the choice: 768 × 1024 and 820 × 1180
  are landscape, and 667 × 375 and 740 × 360 are portrait.
* `layoutBreakpoint` is a **contract addition** (host-owned; non-finite or ≤ 0 falls back to 768).
  The sequencer reads it every frame, so a host can tune it at runtime. The current orientation
  is file-owned (`_landscape` 0/1). It is derived from the real width on every resize, including a
  resize that crosses the threshold in the middle of a scene or a transition (see the checks).

### Mechanism

* **One placement brain.** `scripts/sequencer.luau` is the fill-sized `ScriptedLayout` behind the
  recap. Its `resize(size, scale)` receives the real artboard size and the device pixel ratio.
  `place()` turns them into a few internal view-model numbers (insets, scales, alignments), and
  those numbers are **data-bound** onto the layout:
  * The **copy columns** are absolute `LayoutComponent`s whose four `position*` insets,
    `layoutAlignmentType`, and `scaleX`/`scaleY` are bound. Text inside them reflows (flex
    layout), and centred text switches to left-aligned in two-column layouts (`Text.alignValue`
    bound).
  * The **art stage** and the **card stage** are `Node`s with bound x / y / scale. The 390 × 560 art
    frame is fitted, as a unit, into the region the layout gives it.
  * The **header and footer** are absolute boxes. Their padding and insets are bound, and in
    landscape they are scaled up on large canvases while staying edge to edge.
  * **Display type** compacts on short canvases. The headline `maxHeight` and the hero-number
    height are bound to `_bigK` through formula converters, so `fitFontSize` shrinks only the big
    type. Body copy never goes below its authored size.
* **No duplicate artboards or states.** All ten scene layers, the Motif and Persona choreography,
  the transitions and the reduced-motion paths are the same in both layouts. Only the placement
  changes. A resize snaps to the new placement, with nothing replayed, and the current scene
  and its timelines continue.
* **Portrait** (width < breakpoint):
  * *Stacked*, when height ≥ 1.25 × width. This is the 390 × 844 master, reflowed: copy under the
    header, art bottom-anchored and centred below it. Type grows up to 1.3× on large portraits.
    On short stacks (320 × 568, 360 × 640) the display type compacts so the copy ends where the
    art begins, and the art is lifted so its lowest pieces clear the footer controls.
    **390 × 844 renders pixel-identically to the previous version.**
  * *Side by side*, on short portraits such as a phone on its side below the breakpoint. A
    stack cannot fit there, so the copy stays top-left at its authored size and the art is
    fitted to its right, between the header and the footer. The summary copy sits bottom-left as
    a caption above Share / Replay, with the card on the right.
* **Landscape** (width ≥ breakpoint): an editorial spread.
  * The copy column (38 % of the width, 300–620 pt) sits beside the art. Its type is scaled to
    the column, 1–1.8×, and it is centred vertically against the art. On tall landscapes it
    centres in the upper band, which gives a diagonal composition with the art at the bottom
    right.
  * The art is bottom-anchored, as large as the height allows, with the plinths rising from the
    bottom edge. On wide canvases the copy + art composition is centred, and the header and
    progress still span the full width.
  * **Persona (9):** the spread mirrors. The art stage glides to the left on a critically damped
    spring (about 0.7 s, during the slab → orb handoff) and the persona copy takes the right
    column. It glides back for the summary. Reduced motion and resizes snap.
  * **Summary (10):** the share card fills the right side between the header and the bottom edge,
    up to about 2× its size. The summary copy is centred in the left column, and Share / Replay
    move under that column, bottom-left.
  * Chrome scales with the canvas: 1× at 1280 × 720, up to 1.5× at 1920 × 1080 and above.
* **Everything follows the real size:**
  * Backgrounds (artboard fill, grain) bleed edge to edge.
  * The progress segments span the real header width.
  * The tap zones (left third back, right two-thirds next) and hold-to-pause use the real width.
  * The header and footer exclusion bands scale with the chrome.
  * The turntable drag regions are mapped through the live art transform.
  * Controls stay 44 pt or larger.
  * Art-space text has a scale floor: the "Drag to turn" hint and the scene-3 unit scale back up
    when the art shrinks. The hint hides when its plinth face drops behind the footer.
* **GPU canvases follow their real box.**
  * The 3D vessels (motif and persona pieces) and the kiln chamber take `zoom` (`_artScale`) and
    `dpr` (`_dpr`, from `resize`'s `scale`) inputs. They size their canvas to
    `stage scale × max(device ratio, res)` px per point (quarter steps, capped at 4). The canvas
    is resized in place (`GPUCanvas:resize`) and the shared MSAA/depth targets are re-allocated
    and released per size.
  * The grain renders at the artboard size × device ratio (up to 2×, at most ~8 MP), with the
    pattern defined in points so it looks the same at every resolution.
  * Full-viewport changes are the artboard background and the grain layer, so they cover every
    size with no edge gaps. Kiln has no full-screen wipe.

### Host setup

* Use the runtime's **layout fit**, so the artboard is resized to the canvas and reflowed. Do not
  use contain / cover. Keep the canvas's drawing surface in step with its CSS size and the device
  pixel ratio on resize. The `scale` handed to `resize` is what keeps the 3D canvases sharp.
* Confirm the exact option names in the Rive runtime docs for your target. At the time of
  writing they are:
  * Web: `Fit.Layout` in a `Layout`, plus `resizeDrawingSurfaceToCanvas()` on resize.
  * Apple: `.layout`.
  * Android: `Fit.LAYOUT`.
  * Flutter: `Fit.layout`.

  These names were not verified from this environment (no network); check them before relying on
  them.
* Optionally write `layoutBreakpoint`, for example to keep a tablet in portrait.
* Nothing else changes: same `UserRecap` instance, events, labels, and pause / background handling.

### Sizes tested (`captures/responsive/`, `tools/check_responsive.sh`)

* **Portrait:** 320×568, 360×640, 390×844, 430×932, 600×960, 767×1024, 667×375, 740×360.
* **Landscape:** 768×1024, 820×1180, 1024×768, 1280×720, 1440×900, 1920×1080, 2560×1080, 1366×600.
* **Captured per size:** scenes 1, 2, 4, 5, 9 and 10 settled, plus two mid-transition frames
  (2 → 3 at f20, and 8 → 9 at f24, where the landscape art crosses the spread). There is one
  contact sheet per scene.
* **Check output** (`responsive-checks.txt`):
  * the orientation at every size;
  * the breakpoint tuned both ways;
  * landscape taps at x = 420 / 440 / 1200 (the left third ends at 426.7), hold, keys
    (Right / Left), and the Continue button at 1× and 1.5× chrome;
  * the persona glide, and its snap under reduced motion;
  * a **resize across the breakpoint mid-scene** (390 → 1280 → 390 on scene 4: the scene is kept,
    the `screenChanged` count is unchanged, and the layout settles cleanly both ways);
  * a **resize mid-transition** (2 → 3 tapped at f140, resized at f150: it settles on 3 in
    landscape, with exactly 2 events). See `resize-across-breakpoint-mid-transition.png`.
* The `--viewport` matrix runs one size per run. Mid-run resizes go through
  `tools/resize_harness.py`, a temporary copy of the project in which KilnRecap is a stateful
  `NestedArtboardLayout` whose `instanceWidth` is keyed. In that nested context the counting
  converters show 0. This is a harness artefact: their `currentScreen` gate does not resolve in
  a nested stateful instance. Hosting the artboard directly is unaffected.
* `tools/check_interactions.sh` (all 22 scenarios at 390 × 844) prints exactly what it printed
  before this pass.

### Compromises

* **Portrait has two arrangements.** The stack switches to side by side below height 1.25 × width.
  This is a second, height-based switch inside the portrait layout. The type, the chrome and the
  breakpoint rule are unchanged by it; only the art moves beside the copy.
* **The share card is a fixed-proportion collectible** (300 × 440). On small portraits it is shown
  at 0.5–0.65× (320 × 568: 0.5, 360 × 640: 0.6, 667 × 375: 0.64, 740 × 360: 0.61), so its 11 pt
  captions fall to roughly 6–7 pt on screen. The shared image itself is full size.
  Everything outside the card keeps its readable sizes. From 390 × 844 up it is shown at
  1× or larger.
* **Short canvases compact the display type** (headline and number, `_bigK` down to 0.45 at
  740 × 360). The art there is small (about 0.45–0.5× the master).
* **The plinths are ground.** In portrait and tall landscape, the lower plinth faces sit behind
  the footer controls, as in the original portrait design. The pieces on them, the copy and
  the controls do not overlap.
* **Tall landscapes leave the upper right quiet** (768 × 1024, 820 × 1180): the art is bottom-
  anchored and limited by the column width.
* **Larger GPU memory on large or dense screens:**
  * at 4 px per point a vessel canvas is 1200 × 1600 (about 7.7 MB), plus the shared 4× MSAA
    colour + depth targets for that size;
  * the grain is capped at about 8 MP;
  * hidden pieces still skip all GPU work.
* `--screenshot` renders at 1×, so device-ratio sharpness was not observed in the PNGs (see
  gotchas: check it in a live window or on a device).

## Binding contract — `UserRecap`

One view model, **UserRecap**, bound to the KilnRecap artboard; one instance is shared by
every scene, the nested ShareCard and all converters. Three instances are exported
(`Fixture` = default, `NewUser`, `Extreme`). The host writes the public properties; the
file writes only `currentScreen`, `screenProgress`, `isPaused` (pause toggle) and the
underscore properties.

| Property | Rive type | Owner | Notes |
|---|---|---|---|
| `userName` | String | host | intro (ellipsis, one line), card only if `shareIncludeName` |
| `year` | Number | host | formatted without grouping |
| `periodLabel`, `locale` | String | host | `locale` drives `format.luau` separators |
| `piecesMade`, `studioHours`, `glazeTests`, `firings`, `formsExplored`, `piecesGifted` | Number | host | integers; adapter clamps negatives / non-finite to 0 (formatter also clamps) |
| `clayReclaimedKg` | Number | host | one decimal |
| `personaIndex` | Number | host | 0–3; anything else renders row 0 (`_personaVariant`) |
| `personaName`, `personaDescription` | String | host | written atomically with index + colour; empty name hides scene 9 |
| `personaColor` | **Color** (ARGB) | host | JSON `"#3547A2"` → `0xFF3547A2`; accent bars on scene 9 and the card |
| `autoAdvanceSeconds` | Number | host | clamped to 3–60 s; non-finite → 7 |
| `autoAdvanceEnabled`, `reducedMotion`, `soundEnabled` | Boolean | host | `soundEnabled` unused — the piece is silent |
| `isPaused` | Boolean | host + file | pause button / Space toggle it; host may set it (e.g. backgrounded) |
| `currentScreen` | Number | file (host may write) | canonical 1-based scene id; invalid/hidden values are moved to the nearest visible scene |
| `screenProgress` | Number | file | 0–1 of the current dwell, starts after the entrance settles; 1 on the summary |
| `shareIncludeName`, `shareIncludeSensitiveValues` | Boolean | host | default false. "Sensitive" in Kiln = `studioHours` (routine), shown as `privateValueLabel` |
| labels: `continueLabel`, `previousLabel`, `pauseLabel`, `playLabel`, `shareLabel`, `replayLabel` | String | host | visible labels and SemanticData labels |
| copy: `introHeadline`, `introSupport`, `summaryHeadline`, `summarySupport`, `emptyHeadline`, `emptySupport`, `personaLabel`, `screen2…8Headline/Support/Unit` | String | host | localized, assembled by the host (no sample name/year baked in) |
| `showScreen1…10` | Boolean | host | eligibility. 1 and 10 are always shown; 9 also needs a persona name and at least one stat scene |
| **additions:** `privateValueLabel` ("Private"), `turntableHint` ("Drag to turn") | String | host | localized |
| **addition:** `layoutBreakpoint` | Number | host | default 768: landscape layout when the artboard width is ≥ this, portrait below. Non-finite or ≤ 0 → 768. Read every frame, so it can be tuned at runtime |

Internal (file-owned, do not write): `_command` (1 next, 2 previous, 3 pause, 5 replay —
written by buttons/keys), `_navDir`, `_frozen`, `_holding`, `_seg1…10` (progress segment
display), `_isEmpty`, `_personaVariant`, `_namePublic`, `_hoursPublic`, `_countSeconds`,
`_turnPhase`, `_finished`, `_settled`, `_art*`/`_card*`/`_copy*`/`_c9T`/`_c10*`/`_alt*`/`_align*`/
`_textC`/`_headVA`/`_bigK`/`_padX`/`_navX`/`_act*`/`_chrome*`/`_hdrT`/`_ftrB`/`_hintOn`/`_landscape`/
`_stack`/`_dpr` (responsive placement, see "Responsive layout"), and
diagnostic counters `_screenChangedCount`, `_shareTappedCount`, `_recapFinishedCount`.
Animation playheads are local; user data is never duplicated (the card reads the same five
stat properties).

### Events

| Event | When | Payload |
|---|---|---|
| `screenChanged` | once per change of `currentScreen` (Events layer, AnyState per id) | custom property `index` bound to `currentScreen`; hosts can also read `currentScreen` |
| `shareTapped` | Share button (click, Enter, screen-reader tap) | none — host captures ShareCard and opens its share sheet |
| `recapFinished` | once, when the summary has settled; Replay clears the latch | none |

Only event wiring is supplied — there is no platform share integration here.

### Host adapter responsibilities

* Map the fixture JSON into the instance: colours to ARGB, clamp negatives / NaN / ∞,
  integers vs one-decimal kg, and pluralize unit strings (`"1 firing"`) — the file shows
  units verbatim.
* Write `personaIndex`, `personaName`, `personaDescription`, `personaColor` in the same
  frame (the runtime applies them together on the next advance, so a mid-transition update
  never mixes rows). Table: 0 Form Finder `#F2ECE2` · 1 Glaze Alchemist `#3547A2` ·
  2 Wheel Regular `#38322F` · 3 Handbuilt Storyteller `#BC7057`. Unknown → row 0, or set
  `showScreen9=false` / empty name to hide the persona.
* Locales: `format.luau` groups for en / de-es-it-nl-pt-tr-id / fr-sv-nb-fi-pl-cs-ru /
  de-CH. Anything else falls back to en; a host that needs full CLDR output should
  override the strings it cares about. RTL is not verified.
* Pause when backgrounded (stop advancing the state machine or set `isPaused`), resume after.
* Provide the accessible text equivalent (e.g. "42 pieces made") and screen announcements on
  `screenChanged`; buttons carry SemanticData (role button, bound labels).
* Share: on `shareTapped`, render **ShareCard** with the same instance, snapshot, share.
  The summary never auto-advances, so sharing needs no pause bookkeeping.

## Controls

Tap right two-thirds → next, left third → previous, of the real canvas width (sequencer, outside
the header/footer bands, which scale with the chrome).
Press-and-hold ≥ 0.35 s pauses timer + decorative motion; releasing never fires a tap.
Buttons: Previous, Pause/Play, Continue (story); Share, Replay (summary); all ≥ 44 pt.
Keys: Right / Left / Space on the stage (bubble from the focused control), Enter on the
focused button, Tab / Shift+Tab move focus between the visible controls. Initial focus:
Continue; on the summary focus moves to Share (`FocusActionTarget`). Only the visible set is
focusable (`canFocus` keyed per mode). A focus ring is drawn once Tab has been used
(focus-visible semantics); any pointer press hides it again.

## Edge cases verified (`tools/check_interactions.sh`, `captures/fixtures/`)

rapid taps ×5 (→ scene 6, exactly 6 `screenChanged`), back, hold/release, pause/resume
(progress frozen), Continue / Previous buttons, keys, hidden scenes 3/4/7 (segments
`..xx..x...`, skipped both ways), full auto-advance (1→10 at 3 s dwell, one
`recapFinished`), auto-advance disabled, unsafe dwell clamped, share tap counter, replay
resets latch, new user (intro → welcoming summary, no persona, no stats), persona index 7 →
row 0, start screen 0 → intro, turntable drag never navigates, runtime update
(`piecesMade=1234` → "1,234"), de-DE (`1.234,5`), extreme fixture (+40 % copy, long name
ellipsis, 5-digit values fit, headlines capped to 2–3 lines via fit-font-size).

## Fonts

| File | Family | Licence |
|---|---|---|
| `assets/fonts/DMSerifDisplay-Regular.ttf` | DM Serif Display (display) | SIL OFL 1.1 — `OFL-DMSerifDisplay.txt` (google/fonts) |
| `assets/fonts/Manrope-VariableFont_wght.ttf` | Manrope variable, wght 400–700 used (body) | SIL OFL 1.1 — `OFL-Manrope.txt` (google/fonts) |

Both are embedded in the .riv. Fallback if a host strips them: serve the same names via
the runtime asset loader; there is no system fallback in Rive.

## Unsupported techniques and substitutions

* **Global view model** — the brief's "single global UserRecap" is one artboard-bound
  instance inherited by every nested artboard, not Rive's `viewModelType="global"`:
  `--data` (all fixture/runtime-update testing) cannot reach globals and host auto-binding
  is better supported. Switching is one attribute plus host binding changes; untested.
* **Timer / navigation logic** — a state machine cannot run a data-bound dwell timer or
  compute "next visible scene", so a Luau ScriptedLayout owns the clock and navigation and
  writes `currentScreen`; the state machine owns all choreography. Local builds carry
  **unsigned scripts**: web runtimes need `rive . --publish` (login) to sign them.
* **Turntable rotation** — real: the vessel is a 3D lathe rendered by a WGSL shader and turns
  with `_turnPhase` (drag, inertia, idle spin). Runtimes without GPU scripting draw a flat vector
  silhouette of the same profile instead (`vessel3d.luau` fallback) and the kiln chamber falls back
  to the keyed vector bands under it.
* **Glaze flow** — a procedural glaze in the fragment shader (dipped rim with drip fingers, a
  flowing band, glazed interior, pooling and breaking), keyed by `dip` / `flow`; not a fluid sim.
* **Depth / tactile surface** — lit 3D ceramics (speckle, throwing rings, wet sheen, glaze
  softbox reflections) and a static procedural grain in soft-light; no bitmap textures.
* **Nested artboards and data-driven conditions** — conditions inside a nested component
  do not see the inherited instance, so the card's assembly is driven from the parent via a
  remap and its privacy via a script + binds.
* **Number → visibility** — bools cannot bind to `displayValue`/opacity, so the rules
  module derives 0/1 numbers (`_seg*`, `_namePublic`, …).
* **Pause** — idle loops freeze in place (Frozen state) and the turntable stops; an entrance
  already playing finishes. Resume-from-same-frame of idle loops relies on Rive resuming a
  non-`reset` state; not separately verified.
* **Events** — the CLI does not print plain events; firing is proven with state-owned
  counters on the same states (`_screenChangedCount`, `_recapFinishedCount`) and a counter
  on the Share listener.

## Measurements (MacBook, headless, CLI 1.6.0)

* `build/kiln-recap.riv`: **777,550 bytes** (`--once`, unsigned scripts; 764,643 before the
  responsive pass, 592,051 before the improvement pass), of which ~241 KB are the two embedded fonts; scripts + shaders add ~25 KB and
  the 3D input keys replaced the per-vertex vessel keys. `scene.rml` ~2.6 MB source.
* `rive . --bench=600` (headless CLI on the authoring MacBook, release-baked scripts, 390×844),
  before → after: advance mean 0.022–0.037 ms → 0.077–0.095 ms (p95 ≤ 0.16 ms; the extra is the
  Luau of the 3D pieces, which skip all work while hidden); render-encode mean 0.09–0.17 ms →
  0.10–0.19 ms (scenes 1/3/5/6/9/10; single 13–44 ms first-frame outliers on scenes that compile
  a pipeline); no wasm memory growth over 600 frames either way. These are CPU-side CLI timings,
  **not** device GPU frame rates — the CLI does not time GPU work and no phone was available, so
  on-device fps is unmeasured. GPU load per frame: one 11.8k-triangle lathe draw per visible pot
  (re-rendered only while it turns or morphs), the kiln shader only while hot, grain once.
* GPU memory (estimate, 390 × 844 @1x): ≈30 MB of canvases and render targets — see compromises in
  "Improvement pass". Canvases now follow the stage scale and the device ratio (see "Responsive
  layout"), so this grows with large or dense screens.
* Bounded complexity: 9 tiles, 7 shards, 8 sparks, 5 droplets — no object per raw count;
  clips: one wordmark disc, one kiln chamber, per-tile glaze/gloss clips.

## Remaining limitations

* The 3D pieces, kiln chamber and grain need GPU scripting (WGSL). Elsewhere the flat fallbacks
  draw (vector silhouette, vector bands, no grain) and the piece looks plainer than the captures.
* 3D pieces render at stage scale × device ratio px per point, capped at 4. Above that (for
  example a 3× phone with the art scaled above 1.33) they are slightly softer than the vector art.
* Small and short canvases: see "Responsive layout" → compromises (share-card captions under
  ~600 pt tall, compact display type, smaller art).
* Back navigation does not recount numbers (they stay at their value), by design.
* `soundEnabled` has no effect (no audio authored); haptics not used.
* RTL, CLDR plural rules and compact large-number labels ("12.5K") are host work.
* The glaze is procedural, not a fluid simulation; drag hit regions are rectangles.
* `scene.rml` is generator output; editing by hand is possible but the generator is the
  practical source. The .rev opens it in the editor.

## Exports

* `build/kiln-recap.riv` — produced and re-imported by the CLI (`--once`, `--verify` clean,
  `inspect` 0 problems).
* `build/kiln-recap.rev` — **not produced.** `rive . --once --rev=build/kiln-recap.rev` stops with
  "Not logged in. Run: rive login". After `rive login`, run that command (or `rev` in the
  previewer) to export the editor file. No other file was renamed to stand in for it.
* For web runtimes, scripts must be signed: `rive . --publish` (also needs login). This now
  matters more: the 3D vessel, kiln and grain are scripts, so an unsigned build on the web shows
  none of them.

## Captures (`captures/`)

`settled/` all ten scenes · `personas/` four personas, settled + mid-reveal ·
`transitions/` every forward handoff at 8/20/40 frames, reverse 3→2, replay 10→1 ·
`reduced-motion/` · `fixtures/` new user, extreme/long copy, public share flags, runtime update
before/after, de-DE locale · `responsive/` the 16-size matrix (one contact sheet per scene,
two mid-transition sheets, the mid-transition resize, `responsive-checks.txt`) ·
`share-card/` standalone card (private default and public) · `focus/` keyboard focus rings
(story, summary, hidden again after a pointer press) · `firing/` the scene-5 kiln heating and
cooling · `motion-preview-autoplay.mp4`
(full auto-advance run, 3 s dwell, sampled at 8 fps from deterministic headless renders) ·
`interaction-checks.txt` (output of `tools/check_interactions.sh`).
