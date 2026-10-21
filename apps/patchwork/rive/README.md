# Patchwork — 2026 Recap (Rive)

A ten-scene, Wrapped-style recap for the fictional local-volunteering app
**Patchwork**, authored as editable RML for the Rive CLI (1.6.0). Quilted
textile collage, visible running stitches, hinged fabric folds and a needle
that guides every hand-off. All user data comes from one view model,
`UserRecap`; the fixture values are only its authored defaults.

> Fictional dataset (January 1–December 31, 2026). Nothing here is measured
> real activity.

## Improvement pass (October 2026)

The first version worked but read as "solid". This pass keeps the `UserRecap`
contract, events, fixtures, reduced motion, hidden-scene skipping and the
390 × 844 artboard unchanged, and raises the craft.

**Critique before changes (what was weak)**

* The signature fold was a flat terracotta rectangle animated with `scaleX`, so
  it played as a wipe with five pale squares on it. The needle was barely
  visible. The opaque panel also hid the camera pull-back, so the "larger
  quilt" showed only as 7 px slivers.
* There was no material: every surface was a flat fill, while the art target is
  woven, felted and quilted cloth.
* Scene 2 put a sparse diamond on empty oat (the target is a full-bleed star
  block). Scene 4's ribbons were plain stroke bands, and their own running
  stitch was hidden because the ribbon paint drew over it. Scene 9's disc was
  flat navy. Scene 6's motifs were tiny on two large blobs.
* 9 → 10 hard-cut from oat to indigo.
* Scene 7's grey light-spill wedge sat under the support copy and muddied it.
* The support line sat at five different heights across the scenes.
* Replay had no icon (Continue has an arrow), which was inconsistent.

**What changed**

| Area | Before | After |
|---|---|---|
| Signature fold | 2D `scaleX` panel + small vector needle | a **3D quilt sheet rendered on the GPU** that unrolls over the scene from the right, holds a beat, then lifts at its free corner and rolls away to the left, showing its **gingham lining**. A needle rides the roll's crest pulling a running stitch, and the roll casts a soft shadow on the scene beneath. Back navigation uses a mirrored rose/teal quilt (lands from the left, leaves rightward) |
| Camera pull-back | 0.86, backdrop barely visible | 0.82, the scene **clipped to a patch with a stitched indigo binding and a feathered shadow**, set in a diamond-in-square quilt of half-square triangles (the same piecing as the sheet). Clip and backdrop are only on during hand-offs |
| Material | flat fills | a procedural **woven-cotton texture** (plain weave, slubbed threads, felted mottling, soft edge shade) generated once on the GPU and multiplied over everything at low strength |
| Scene 2 | small star block on oat | a full-bleed **quilt field** of 42 half-square triangles that assembles in a radial wave out from the block, with bound top/bottom edges; the star's pieces get cream outlines so they pop |
| Scene 4 | plain ribbons | ribbons **pieced from alternating patches** (a dashed second paint), with their running stitch now visible on top |
| Scene 6 | small motifs | bolder mug/book motifs and six appliqué patches that pop in after the seam is sewn |
| Scene 7 | grey spill wedge under the copy | a gradient spill that fades out before the copy |
| Scene 9 | flat navy disc | a **quilted medallion rendered on the GPU** (16-wedge Dresden-plate piecing with the outer ring offset, a hub, loft-shaded puffs, sunk seams, running stitches, woven texture, a rolled binding). Its light sweeps from low right over the top during each persona reveal, then rests. A faint keyline keeps Builder's oat accent ring readable on oat |
| 9 → 10 | colour cut | the indigo persona disc **blooms to fill the screen** and becomes the summary ground; the chrome turns light-on-dark only once the bloom is behind it; the card body fades and stitches up around the carried emblem (the same quilted medallion, shrunk into the card) |
| Copy | support lines at five different heights | one baseline (top at 686; the plated scenes 4/5 centre at 704) |
| Controls | Replay was text only | **Share** gets a tray-and-arrow icon. **Replay** gets a clockwise arc open at the top, with the arrowhead computed from geometry: it sits on the arc's end and points along the arc's tangent |

**3D / shader techniques used**

* `scripts/cloth.luau` + `shaders/cloth.wgsl` (ScriptedDrawable): a
  45 × 97-vertex grid curled in the vertex shader over a moving cylinder (in a
  mirrored local frame for the leftward moves). The part past half a turn lies
  flipped with a travelling ripple, under a pinhole perspective camera. The
  fragment shader computes the curl angle per pixel and procedurally pieces the
  quilt front (diamond-in-square half-square triangles, appliqué hearts,
  sewn-on buttons, seam stitches, binding). It takes a **normal from the
  quilted loft** (finite differences of a seam-distance height field),
  combines it with the curl frame, adds woven thread, seam occlusion, cloth
  sheen and inner-roll occlusion, and casts a shadow from the hovering part
  onto the flat part. A second pipeline casts the roll's shadow onto the scene
  underneath. Rendering uses a depth buffer and 2× MSAA at 2 px per point. The
  Handoff timelines key the script inputs `fold` (0..1 lands, 1..2 leaves),
  `dir` and `cam` (the camera scale, so the sheet always fits the patch). The
  state machine, the tap queue and the events are untouched.
* `scripts/weave.luau` + `shaders/weave.wgsl` (ScriptedLayout): a
  fragment-only texture rendered once per size at the presenting pixel density
  and drawn in `multiply`.
* `scripts/medallion.luau` + `shaders/medallion.wgsl` (ScriptedDrawable ×2):
  a fragment-only lit cushion, re-rendered only while its keyed `light` input
  moves, so a settled medallion costs one image draw.
* Not used: imported meshes and bones (the cloth is a procedural grid), and
  textures (everything is procedural). The thanks corner-lift stays a vector
  flap, because a 3D curl at that size would not read better.

**Reduced motion, pause and fallbacks.** Reduced-motion hand-offs key
`fold = 0`, so the sheet is never drawn and the 150 ms oat veil remains. The
reduced persona states key the medallion's `light` straight to 1, so it is
static. The weave texture is static. Without shader support, the fold draws a
flat 2D panel that folds toward its edge, the medallion falls back to the
vector disc beneath it, and the weave is skipped.

**Gotchas met (recorded for the next pass)**

* A `ScriptedLayout` in a `LayoutComponent` placed under a plain `Node`
  **does not sort with its sibling drawables**. Only the first such layout
  among the App's children kept its place. The cloth drew underneath the World
  (invisible) or covered the chrome, depending on order. The cloth is
  therefore a `ScriptedDrawable` at the artboard origin, and only the weave is a
  layout (as App's first child, it draws on top).
* `advance` is not relied on for the cloth: everything it needs is read in
  `draw` from the keyed inputs.
* The idle hand-off timeline keys `fold = 0` every frame, so a static input
  value is no use for testing. Probe with a temporary `print` in `draw`.
* The roll's large radius means the sheet visually covers the patch at about
  half its pose range. Progress is eased out (`1 − (1 − t)^1.8`) so the visible
  edge travels evenly.
* Within one shape, the paint declared later draws on top. The scene 4
  ribbon's stitch had been drawn under the ribbon since the first pass.

**Behaviour checks.** `tools/check.sh` (new) codifies the "Verification
performed" table as 15 headless assertions. All 15 pass, before and after this
pass. No check was changed. The hand-off is now 22 + 28 frames (was 18 + 26),
which is still within every check's timing.

**New compromises**

* **Web needs a signed build.** The `.riv` now contains three scripts and three
  shaders, so an unsigned local build is rejected by web runtimes. Ship
  `rive apps/patchwork/rive --publish` (not run here). Native runtimes with
  scripting run the local build.
* A `ScriptedDrawable` receives no pixel density, so the cloth renders at a
  fixed 2 px per point (supersampled on @1x captures, slightly soft on @3x
  phones) and the medallion likewise. The weave is a layout and renders at the
  device density.
* GPU memory: the cloth's surfaces (colour, 2× MSAA colour and depth at
  780 × 1688) are about 26 MB. They are allocated on the first fold, not at
  load, and then kept.
* The share card's medallion is the 290-pt render scaled to 0.3, so its fine
  stitches minify with bilinear filtering only.
* The flat-sheet beat mid-hand-off (about 8 frames) is deliberate: it is the
  moment the pull-back shows the scene as one patch of the larger quilt.
* Headless `--bench` measures CPU-side recording, not GPU time. Per fold frame
  the GPU draws one 2× MSAA pass of about 4.4 k vertices plus a full-canvas
  shadow pass; idle frames draw one cached weave image (plus the cached
  medallion on scenes 9 and 10).

**Performance** (Apple M5 Pro, Rive CLI 1.6.0, headless `--bench` at 390 × 844 @1x,
CPU-side render recording, not GPU time. Before and after were run interleaved,
three rounds each, while other renders were loading the machine, so read the
ranges, not single numbers.)

| Metric | Before (first pass) | After |
|---|---|---|
| `patchwork-recap.riv` | 368,150 bytes (134,505 gzipped) | **639,722 bytes (199,608 gzipped)**. The object count rose only 18 % (18,301 → 21,578); most of the growth is the three compiled scripts and three shaders |
| `--bench=600` (intro, idle) render p50 | 0.36–0.42 ms | **0.30–0.32 ms** (mean 0.45–0.61, p95 0.70–1.96) |
| `--bench=1200`, `autoAdvanceSeconds=3` (scenes + folds) render p50 | 0.34–0.35 ms | **0.26–0.29 ms** (mean 0.40–0.52, p95 0.78–1.13) |
| First-frame spike (one-time: shader pipelines, weave texture) | max ≈ 9 ms | max 9–95 ms on the first frame only; the cloth surfaces are allocated on the first fold |
| Advance mean | 0.03–0.04 ms | 0.06–0.09 ms |
| wasm memory over 1,200 frames | +0 pages | +0 pages |
| Quiet-machine reference (earlier, unloaded) | 600: mean 0.211 ms; 1200: mean 0.187 ms | 600: mean 0.267 ms; 1200: mean 0.179 ms |

The walkthrough `video.webm` grew from 2.7 MB to 9.0 MB at the same encoder
settings, because the woven texture is fine detail that VP9 has to keep.

## What is where

| Path | What |
|---|---|
| `scene.rml` | **The editable source.** One artboard (`Patchwork Recap`, 390 × 844), one state machine (`Recap`), the `UserRecap` view model, converters, fonts. |
| `../tools/gen_scene.py`, `../tools/art.py`, `../tools/rml.py` | Generator that writes `scene.rml` (keeps ~600 repetitive state-machine nodes consistent). Small tweaks can be made directly in `scene.rml`; larger ones in the generator, then `python3 apps/patchwork/tools/gen_scene.py`. |
| `assets/fonts/` | Bree Serif, Atkinson Hyperlegible Regular/Bold + their OFL licence texts. |
| `scripts/cloth.luau` + `shaders/cloth.wgsl` | The signature fold: a GPU-rendered 3D quilt sheet (see "Improvement pass"). |
| `scripts/weave.luau` + `shaders/weave.wgsl` | Woven-cotton ground texture multiplied over the whole recap. |
| `scripts/medallion.luau` + `shaders/medallion.wgsl` | The quilted, lit persona medallion (scene 9 and the card). |
| `build/patchwork-recap.riv` | Runtime export (unsigned local build; **contains scripts**, so web hosts need a signed `--publish` build). |
| `build/patchwork-recap.rev` | Editor export — see "Exports" for its status. |
| `captures/` | Headless review captures (scenes, personas, transitions, fixtures, reduced motion, states, viewports) and `captures/motion-preview.mp4` (an H.264 transcode of `../video.webm`, the full walkthrough rendered by `scripts/render-video.py`). |
| `../fixtures/` | `zero-user.json` / `extreme.json` host fixtures plus `.args` files that replay them through `rive --data`. The supplied `../sample-data.json` is the authored default instance. |
| `../tools/check.sh` | The behaviour checks below, as 15 headless assertions (exit code = failures). |
| `../tools/capture_all.sh`, `shoot.sh`, `probe.sh` | Regenerate captures; drive taps headlessly; dump the live view-model values. |

## Preview

```bash
rive apps/patchwork/rive                 # live previewer (window, rebuilds on save)
rive apps/patchwork/rive --verify        # compile check
rive inspect apps/patchwork/rive --summary
apps/patchwork/tools/check.sh            # behaviour checks (15 assertions, headless)
apps/patchwork/tools/capture_all.sh      # every PNG in captures/ (headless)
apps/patchwork/tools/probe.sh --advance=120s   # full auto-advance run, prints key view-model values
```

Fixtures in the live previewer or a capture: append `--data=<property>=<value>`
(e.g. `--data=personaIndex=2 --data=reducedMotion=true`), or use the `.args`
files (`tools/shootfx.sh ../fixtures/extreme.args out.png 1`).

**Hosts must use `Fit.contain` (or `layout` with the 390 × 844 artboard
centred) and paint the letterbox with oat `#F5EBDD`** — see Limitations.

## Exports

* `.riv`: `rive apps/patchwork/rive --once`, copied to `build/patchwork-recap.riv`.
  Since the improvement pass the file **contains three Luau scripts and three
  WGSL shaders**, so web runtimes reject the unsigned local build: ship a signed
  `rive apps/patchwork/rive --publish` build to web hosts (not done here).
* `.rev`: `rive apps/patchwork/rive --once --rev=build/patchwork-recap.rev`
  needs `rive login`. See the status line at the end of this file.

---

## Binding contract — `UserRecap`

Exactly one view model, `UserRecap`, bound to the artboard (`viewModelId`).
The runtime instance the host binds (auto-bind the default instance, or
create one from `UserRecap`) is the single shared data source for every
scene, the summary card, progress and persona visuals. No scene owns a copy of
a statistic.

*Why a bound view model rather than a `viewModelType="global"` one:* the CLI
documents that a global instance cannot be set with `--data`, and the bound
instance is the path every runtime's data-binding API (auto-bind / instance
from view model) supports, so the fixtures could not have been proven against
a global one. The bound instance gives the same
"one shared instance" semantics with full runtime access. All nested
components read it by absolute path.

Ownership: **H** = host writes, file reads. **F** = file writes (state machine),
host reads. **H/F** = both (host may set, file updates).

### User data and copy (host-owned)

| Property | Rive type | Own | Notes |
|---|---|---|---|
| `userName` | String | H | Name tag (scene 1) and summary card (only when `shareIncludeName`). Truncated with ellipsis at a word boundary; never shrinks other text. |
| `year` | Number | H | Header + card year, rendered with 0 decimals. |
| `periodLabel` | String | H | Localised period, scene 1. |
| `locale` | String | H | Informational for the adapter; the file does no locale logic itself. |
| `volunteerHours`, `projectsJoined`, `communityDays`, `gardenSessions`, `repairItems`, `welcomeSessions`, `activeMonths` | Number | H | Integers ≥ 0 (adapter clamps negatives / NaN / ∞ to 0 and rounds). Rendered with digit grouping (see Formatting). |
| `personaIndex` | Number | H | 0–3; anything else falls back to row 0 for the emblem. |
| `personaName`, `personaDescription` | String | H | Written atomically with `personaColor` by the adapter from the table below. |
| `personaColor` | **Color** | H | Native ARGB colour. Adapter converts `"#CC7051"` → `0xFFCC7051`. Drives the accent ring on scene 9 and the summary card. |
| `continueLabel`, `previousLabel`, `pauseLabel`, `playLabel`, `shareLabel`, `replayLabel` | String | H | Visible labels and accessibility labels (`SemanticData.label` is bound to the same strings). |
| `introHeadline`, `introSupport`, `summaryHeadline`, `summarySupport`, `emptyHeadline`, `emptySupport`, `personaLabel` | String | H | Localised copy. `introHeadline` is assembled by the host from `year` (e.g. "Your 2026 on Patchwork"). |
| `screen2…8Headline`, `screen2…8Support`, `screen2…8Unit` | String | H | Localised, **already pluralised** by the host for the bound count ("1 hour contributed" vs "84 hours contributed" ⇒ unit string). Units wrap to two lines and only then shrink. |
| `showScreen1…10` | Boolean | H | Eligibility. Hidden scenes are skipped in both directions and drop out of the progress bar. `showScreen1` and `showScreen10` are **ignored (always shown)** — the safe intro/summary path. Hide absent metrics; a genuine 0 stays visible. |

### Playback and control (host ↔ file)

| Property | Type | Own | Notes |
|---|---|---|---|
| `autoAdvanceSeconds` | Number | H | Settled dwell per scene. Clamped in-file to ≥ 3 s. |
| `autoAdvanceEnabled` | Boolean | H | `false` = manual only. |
| `isPaused` | Boolean | H/F | Pause button / Space toggle it; the host sets it when backgrounded or presenting the share sheet (and restores the previous value afterwards). Freezes the timer and ambient loops, preserves `screenProgress`. |
| `reducedMotion` | Boolean | H | Map from the OS setting. Immediate final values, static heroes, short opacity fades, no camera move. |
| `soundEnabled` | Boolean | H | Reserved; the file has no audio — the experience is fully silent. |
| `currentScreen` | Number | **F** | Canonical 1-based scene id, written on every scene entry. Host reads it (do not write it to navigate — use the triggers). |
| `screenProgress` | Number | **F** | 0–1 of the current dwell; drives the active progress segment. |
| `shareIncludeName` | Boolean | H | Shows `userName` on the share card. Default false. |
| `shareIncludeSensitiveValues` | Boolean | H | Default false. The card only ever contains the five aggregate stats + persona (no locations, recordings, notes or beneficiary data exist in the model), so the file has nothing further to reveal; the flag is passed through for the host's capture pipeline. |

### Additions (documented, not in the brief's table)

| Property | Type | Own | Purpose |
|---|---|---|---|
| `navNext`, `navPrevious` | Trigger | H/F | Programmatic navigation (the file fires them from taps, keys and the timer). Hosts can fire them for hardware keys / switch control. |
| `replayRecap` | Trigger | H/F | Replay from scene 1; resets progress and the `recapFinished` latch. |
| `thanksLabel` | String | H | The tiny "Thank you!" under the lifting quilt-patch corner. |
| `numberGroupSeparator` | String | H | Locale digit-group separator ("," en-GB, "." de-DE, " " fr-FR, "" to disable). |
| `shareCaptureMode` | Boolean | H | Hides header, progress and controls so the host can snapshot a clean, settled card. |
| `screenChangedCount`, `shareTappedCount`, `recapFinishedCount` | Number | F | Diagnostic mirrors incremented in the exact state/listener that fires each event — lets tests (and `--data-dump`) prove "exactly once". |
| `_commitNext`, `_commitPrev`, `_commitReplay`, `_settled`, `_pressing`, `_pressSide`, `_holdPaused`, `_heroT`, `_finishedLatch`, `_thanksOpen`, `_focusIndex`, `_noActivity` | — | F | Private plumbing (leading underscore). `_heroT` is the shared 0→1 count-up playhead, not user data. Hosts must not write these. |

### Events

| Event | When | Payload |
|---|---|---|
| `screenChanged` | On entering a scene (forward, back, auto, replay, reduced motion). Fired once per entered scene; rapid taps that pass *through* scenes report each scene actually entered. | Custom property `index` (Number) = canonical scene id. Ten `Event` objects share the name `screenChanged`, each with a literal `index`, so the payload is exact. `currentScreen` holds the same value. |
| `shareTapped` | Share button (click, Enter, or screen-reader tap). | none — host captures (with `shareCaptureMode=true`) and opens the platform share sheet. **Only event wiring is supplied; there is no real share integration in the file.** |
| `recapFinished` | First time the summary settles; latched until `replayRecap`. | none |

Headless runs cannot observe reported events directly (the CLI has no event
log and in-file event listeners do not receive the machine's own events), so
the `*Count` mirrors are what the verification below asserts.

### Formatting rules

* Counts render as integers (`round`), with digit grouping done in-file:
  three run tiers (≥ 1,000,000 / ≥ 1,000 / < 1,000) in one `Text`; tiers that
  do not apply collapse to a 0-pt font size, and `numberGroupSeparator` is
  bound between groups. Hero numerals use `fitFontSize`, so 1,234,567 fits
  the same slot as 84 (it shrinks only that numeral). No compact
  ("1.2M") labels are used, so displayed values are always exact.
* The count-up is `round(value × _heroT)`: `_heroT` is keyed 0→1 inside each
  scene's entrance (written back through a custom property bind), so first
  entry, back navigation and replay all count from 0 to the *current* bound
  value, and placeholder digits never show (authored literal is "0").
* Pluralisation, localisation and the assembly of sentences that contain the
  name/year are the host adapter's job; each formatted string is stored once in
  `UserRecap` and reused.

### Persona mapping (adapter writes all four fields together)

| `personaIndex` | `personaName` | Emblem (unique choreography) | `personaColor` | `personaDescription` |
|---|---|---|---|---|
| 0 | Neighborhood Weaver | Interwoven quilt star: eight diamonds spin out of the hub, a woven band closes | `#CC7051` | You help the pieces belong. |
| 1 | Quiet Helper | Small stitched heart: grows from a seed-sized heart, beats twice, rings ripple, hands cradle | `#E9ACB2` | Your care shows up in small ways. |
| 2 | Hands-on Builder | Joined cloth tools: hammer, wrench and needle slide in from three sides and lock with a squash | `#F5EBDD` | You enjoy making something useful together. |
| 3 | Community Welcomer | Open fabric doorway: arch rises, door swings open, guests arrive | `#4D8F83` | You make it easier to join in. |

The `Persona` layer selects the emblem for both scene 9 and the summary card
in a single frame (one Solo key each), so label, colour and emblem cannot
disagree once the adapter has written the row. Unknown indices fall back to
row 0's emblem. With no evidence (new user) the host sets
`showScreen9=false`; the summary then hides the persona block too.

### Host adapter responsibilities

1. Bind the `UserRecap` instance to the artboard and state machine `Recap` (default).
2. Validate/clamp counts (finite, ≥ 0, integer), and set `showScreenN=false` for **missing** metrics (unknown ≠ 0).
3. Map `personaIndex` → name/description/colour atomically; hex → ARGB colour.
4. Localise and pluralise all strings; set `numberGroupSeparator` for the locale.
5. Set `reducedMotion` from the OS; set `isPaused=true` while backgrounded or sharing (restore afterwards).
6. On `shareTapped`: set `shareCaptureMode=true`, wait one frame, snapshot the artboard (the card occupies x 27–363, y 148–688), set it back, present the share sheet.
7. Listen for `screenChanged` / `recapFinished`; announce `currentScreen`'s headline + hero value via the platform screen reader (the file exposes button semantics; long-form announcements are the host's job).
8. Paint the letterbox oat and use `Fit.contain`.

---

## Sequencing and controls

One state machine, `Recap`, ten layers:

| Layer | Job |
|---|---|
| `Scenes` | Forward/back gate states per scene skip hidden scenes in both directions; entrance (or reduced-motion) state per scene → settled idle. Writes `currentScreen`, resets `screenProgress`, fires `screenChanged`. Scene 9 has four persona entrances. Scene 10 fires `recapFinished` once (latched). |
| `Handoff` | The signature transition. `navNext` → cover fold (fires `_commitNext` at its end) → reveal fold. A one-deep queue makes rapid taps land exactly (`k` taps → `k` commits) without stacking animations. 8→9 and 9→10 use a short "carry" instead (continuity transitions). Reduced motion uses an oat veil. |
| `Gesture` | Tap vs hold. Press in the right ⅔ / left ⅓ region; release < 350 ms = tap (next / previous); held ≥ 350 ms = hold-pause (`_holdPaused`), and the release does **not** also tap. |
| `Timer` | 100 ms ticks add `0.1 / max(3, autoAdvanceSeconds)` to `screenProgress` only while settled, enabled, unpaused, not held and not on the summary; at 1 it fires `navNext` once. |
| `Ambient sway`, `Ambient flow` | Restrained idle loops (pingPong sway; seamless running-stitch dash crawl). Frozen while paused/held, static in reduced motion. |
| `Activity` | Derives `_noActivity` (all metric scenes hidden) → summary switches to the welcoming empty state. |
| `Persona` | Emblem selection (see above). |
| `Pause icon`, `Thanks` | Pause/play glyph; the lifting-corner interaction. |

Input map (artboard coordinates):

| Input | Region / key | Result |
|---|---|---|
| Tap | x 130–390, y 92–736 | next |
| Tap | x 0–130, y 92–736 | previous |
| Press & hold ≥ 350 ms | same regions | pause while held, resume on release, no navigation |
| Buttons (y 746–798, ≥ 48 × 48 hit areas) | Previous (44), Continue (195) / Share (139) + Replay (259) on summary, Pause/Play (346) | as labelled; keyboard Enter and screen-reader tap work on the focused button |
| Keys (focus host = `App`, focused at start) | ← / → navigate, Space toggles pause, Tab / Shift+Tab move focus across the buttons (visible terracotta focus ring), Enter activates | |
| Thanks patch | scene 1 top-right quilt patch, summary card corner patch | lifts its corner to reveal `thanksLabel`; opaque hit target so it never navigates |

---

## Motion design

**Signature transition — "quilt fold".** On navigation the camera pulls back
to 0.82 and the scene becomes one patch, with a stitched indigo binding, set in a
larger diamond-in-square quilt. A real 3D quilt sheet, rendered on the GPU,
unrolls over the patch from the right while a needle rides the crest of the roll
and pulls a running stitch behind it. Under cover the scene switches. After a
short beat the sheet lifts at its free corner (anticipation), rolls up from the
right and leaves past the left edge, showing its gingham lining. It casts a soft
shadow onto the new scene as the camera pushes back in (22 + 28 frames ≈ 833 ms).
Reverse navigation uses a differently pieced rose/teal quilt, mirrored: it lands
from the left and rolls away to the right. Rapid taps keep the sheet flat while
the queued commits run. Reduced motion keeps the 150 ms oat veil and never draws
the sheet.

**Signature interaction.** Tap a quilt patch (scene 1, top-right; summary card
corner) to lift its corner on a hinged diagonal and reveal a tiny
"Thank you!"; it settles back after ~2.5 s.

**Per-scene score** (60 fps; 0–200 ms anticipation → 200–1200 ms hero + count
→ 1200–1800 ms headline/support → restrained idle):

| # | Scene | Anticipation | Hero sequence | Idle |
|---|---|---|---|---|
| 1 | Invitation | Name tag lifts and swings in | Nine patches fly in from scattered positions and settle into a quilt; a running thread draws around it; the wordmark banner unfolds across the middle row | banner sway |
| 2 | Hours | Centre card squashes | A full-bleed field of 42 half-square triangles flips in as a wave rippling out from the block; four triangles unfold on hinges around the embroidered numeral; corner patches spin in | triangles breathe, motifs sway |
| 3 | Projects | Numeral leans back | Twelve patches rise and land one by one with a squash, then the grid seams are sewn | grid sways |
| 4 | Community days | Calendar lifts before it drops | Calendar swings down, five pieced patchwork ribbons unroll from it with their stitch following, days are marked | calendar sway, clouds drift, sun turns |
| 5 | Garden | Soil dips | Cloth soil layers rise, a stitched sprout grows, leaves unfold, a bloom opens | leaves sway |
| 6 | Repairs | Two fabric shapes pull apart | They snap together, a zig-zag seam is sewn and cross-stitches pop down the join, appliqué patches pop on; darning weave fills the numeral disc | shapes breathe |
| 7 | Welcome | Doors shiver | Two cloth arches swing open into a lit doorway, a mat unrolls, neighbours walk in | light spill breathes, stars twinkle |
| 8 | Active months | Numeral squashes | Ten seasonal patches pop along a path while one thread loops through them | running-stitch dash crawls |
| 9 | Persona | Scene 8's ten patches converge and spin into the disc | The quilted medallion pops in and its light sweeps round it while the persona-specific emblem is revealed (four choreographies), then the title and line | — |
| 10 | Summary | Scene 9's indigo disc blooms to fill the screen | The persona emblem flies from the disc into its card slot while the card body stitches up around it; the border is sewn, five stat patches drop into place and count up together | — |

Hero sequences: scenes 1, 4, 9 (plus 2, 6, 7). Continuity transitions that
carry an object: **8 → 9** (the ten seasonal patches and thread continue into
the persona disc) and **9 → 10** (the disc blooms into the summary ground and the
emblem shrinks into the share card), plus the guide needle that rides every fold. Custom cubic eases are named
in `tools/rml.py` (`cloth`, `back`, `antic`, `thread`, …).

**Reduced motion:** every scene has a generated reduced variant that sets all
entrance properties to their final values and only fades the scene in over
200 ms; hand-offs become a 150 ms oat veil; no camera move; ambient loops held
at rest; counts show final values immediately. Story, controls and timing are
unchanged.

---

## Fonts

| File | Family | Licence |
|---|---|---|
| `assets/fonts/BreeSerif-Regular.ttf` | Bree Serif (TypeTogether) | SIL Open Font License 1.1 — `assets/fonts/OFL-BreeSerif.txt` |
| `assets/fonts/AtkinsonHyperlegible-Regular.ttf` | Atkinson Hyperlegible (Braille Institute) | SIL OFL 1.1 — `assets/fonts/OFL-AtkinsonHyperlegible.txt` |
| `assets/fonts/AtkinsonHyperlegible-Bold.ttf` | Atkinson Hyperlegible Bold | SIL OFL 1.1 |

Downloaded from `github.com/google/fonts` (`ofl/breeserif`, `ofl/atkinsonhyperlegible`).
Fonts are embedded in the `.riv`; the OFL permits embedding and
redistribution (the fonts may not be sold on their own). Fallback: none is
needed because both faces are bundled; a host that strips them must supply the
same family names through its asset loader.

---

## Unsupported techniques and substitutions

| Brief asks for | Status in this toolchain | What was done |
|---|---|---|
| A *global* view model | Supported as `viewModelType="global"`, but not writable through `--data` and not addressable by most runtime instance APIs | Single **bound** `UserRecap` instance shared by everything (see contract). |
| Event payload with the scene index | Supported (custom properties on `Event`) | Ten same-named `screenChanged` events with literal `index`. |
| Locale-aware number formatting | No formatter converter | In-file digit-group tiers + host-provided separator; pluralisation by host. |
| Formula converters reading other properties | Tokens bound to *host-written* booleans did not re-evaluate when only those inputs changed (observed with `--data`) | Derived state moved into state-machine layers (`Activity`), which read live values. |
| Keyed deformation of cloth / real page-curl folds | Supported through scripted GPU rendering | The fold is a GPU-curled 3D quilt (`scripts/cloth.luau`). The thanks corner lift is still a vector triangle flap. |
| Camera pull-back revealing a larger quilt | No camera object | A `World camera` node scaled about the centre over a backdrop quilt. |
| Raster grain | Restrained, procedural | A woven-cotton texture is generated once on the GPU and multiplied over everything at low strength. It never carries text or a scene. |
| Responsive reflow to 320 × 568 / 430 × 932 | Hand-composed 390 × 844 art; layout reflow of illustrated scenes is not practical | Fixed artboard, host `Fit.contain` with oat letterbox; validated at 320 × 568, 430 × 932 and a 1280 × 800 desktop (captures/viewports). |
| Sound | Not used | Silent; `soundEnabled` reserved. |
| Visible focus | Supported (focus/blur listeners) | Focus ring bound to `_focusIndex`; pointer clicks do not focus (`canTouch=false`). |
| Screen announcements | Rive exposes semantics, not live announcements | Buttons carry `SemanticData` (labels bound); host announces scene changes. |
| Haptics | n/a | none required. |

---

## Verification performed

Run from `apps/patchwork/rive` with `tools/probe.sh` (dumps the live
`UserRecap` after a scripted, headless run). All results below were observed.

| Check | Result |
|---|---|
| `--verify` / `inspect --summary` | 0 errors / `problems: []` |
| Full auto-advance (120 s, no input) | ends on 10, `screenChangedCount` 10, `recapFinishedCount` 1 |
| Hidden 3, 4, 9 + auto-advance | ends on 10, 7 scenes entered, progress row shows 7 segments |
| Zero user (2–9 hidden) + one tap | intro → welcoming summary (`_noActivity`), 2 segments, no persona |
| 5 rapid taps (3 frames apart) | lands on 6, exactly 6 `screenChanged` (1 + 5), no stacked layers |
| 3 forward, 1 back | lands on 3 |
| Hold 90 frames, release | `_holdPaused` true while held, no navigation on release |
| Pause button, wait 10 s | `isPaused` true, progress frozen; resume continues from the same value |
| Keys → → → ← / Space / Tab Tab Enter | 3 / pause toggled / Continue focused (`_focusIndex` 2) and activated |
| Previous on scene 1 | no-op (no fold plays) |
| Summary: Share, back, forward, Replay | `shareTappedCount` 1, `recapFinishedCount` stays 1 (latched), replay returns to 1 and clears the latch |
| Thanks patch tap | flap lifts, `currentScreen` unchanged |
| Runtime data (`--data=volunteerHours=512`, `autoAdvanceSeconds=3/20`) | numerals and dwell change accordingly (captures/fixtures) |

## Measurements (first pass, before the improvement pass)

Measured on the authoring machine (Apple M5 Pro, macOS, Rive CLI 1.6.0
native runtime, headless `--bench`, 390 × 844 @1x). **No phone was available**,
so treat these as relative numbers, not device frame rates.

| Metric | Value |
|---|---|
| `patchwork-recap.riv` | 368,150 bytes (134,505 gzipped); ~150 kB of that is the three embedded fonts |
| Objects | 1 artboard, 49 timelines, 1 state machine with 10 layers |
| Idle scene, 600 frames | advance mean 0.039 ms (p95 0.16), render mean 0.28 ms (p95 0.38) |
| Auto-advancing through scenes + fold hand-offs (3 s dwell), 1,200 frames | advance mean 0.10 ms (p95 0.17, max 24 ms on first text shaping), render mean 0.43 ms (p95 0.49, max 21.5 ms) |
| Memory | no wasm growth over 1,200 frames |

Budget notes: inactive scenes are collapsed by a `Solo` (not drawn, not
hit-tested); decorative counts are fixed (12 patches, 10 months, 21 days) and
never one object per raw count. Since the improvement pass, one rectangular clip
(the scene patch) and the backdrop quilt are switched on only during hand-offs,
and one feathered shadow sits under the patch binding (only visible during
hand-offs).

## Remaining limitations (honest list)

* `.rev` export status: **not produced.** `rive apps/patchwork/rive --once --rev=apps/patchwork/rive/build/patchwork-recap.rev` stopped with "Not logged in. Run: rive login". After `rive login`, run that command; nothing else is required. The editor round-trip therefore has not been confirmed.
* Event delivery was verified through the diagnostic counters, not by a host
  receiving the events; confirm `screenChanged`/`shareTapped`/`recapFinished`
  in a real runtime.
* Background/foreground is host-driven (`isPaused`); the file cannot detect it.
* Hidden/empty persona: the scene is hidden via `showScreen9`; there is no
  separate "neutral persona" emblem.
* The fixed 390 × 844 composition scales (contain) rather than reflows; at
  320 × 568 text renders at ~0.67× — readable but small.
* Right-to-left layouts were not built or verified (no RTL target locale in the brief's fixture).
* Frame-rate numbers come from the CLI's headless `--bench` on the authoring
  Mac, not from a phone.
* The motion preview (`captures/motion-preview.mp4`, `../video.webm`) is 30 fps
  headless renders; review exact timing in the live previewer.
* Pluralisation is still the host's job (units are bound strings), and the
  layout still scales rather than reflows. The improvement pass did not change
  either.
* The scripted 3D and shaders were only verified in the native CLI runtime
  (headless). A signed web build, and GPU frame times on a phone, are
  unverified.
* Copy hard-coded in the file: only the wordmark "Patchwork" (brand) — all
  other text is bound.
