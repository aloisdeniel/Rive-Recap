# Patchwork — 2026 Recap (Rive)

A ten-scene, Wrapped-style recap for the fictional local-volunteering app
**Patchwork**, authored as editable RML for the Rive CLI (1.6.0). Quilted
textile collage, visible running stitches, hinged fabric folds and a needle
that guides every hand-off. All user data comes from one view model,
`UserRecap`; the fixture values are only its authored defaults.

> Fictional dataset (January 1–December 31, 2026). Nothing here is measured
> real activity.

## What is where

| Path | What |
|---|---|
| `scene.rml` | **The editable source.** One artboard (`Patchwork Recap`, 390 × 844), one state machine (`Recap`), the `UserRecap` view model, converters, fonts. |
| `../tools/gen_scene.py`, `../tools/art.py`, `../tools/rml.py` | Generator that writes `scene.rml` (keeps ~600 repetitive state-machine nodes consistent). Small tweaks can be made directly in `scene.rml`; larger ones in the generator, then `python3 apps/patchwork/tools/gen_scene.py`. |
| `assets/fonts/` | Bree Serif, Atkinson Hyperlegible Regular/Bold + their OFL licence texts. |
| `build/patchwork-recap.riv` | Runtime export (unsigned local build, no scripts inside). |
| `build/patchwork-recap.rev` | Editor export — see "Exports" for its status. |
| `captures/` | Headless review captures (scenes, personas, transitions, fixtures, reduced motion, states, viewports) and `captures/motion-preview.mp4`. |
| `../fixtures/` | `zero-user.json` / `extreme.json` host fixtures plus `.args` files that replay them through `rive --data`. The supplied `../sample-data.json` is the authored default instance. |
| `../tools/capture_all.sh`, `shoot.sh`, `probe.sh` | Regenerate captures; drive taps headlessly; dump the live view-model values. |

## Preview

```bash
rive apps/patchwork/rive                 # live previewer (window, rebuilds on save)
rive apps/patchwork/rive --verify        # compile check
rive inspect apps/patchwork/rive --summary
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
  The file contains **no Luau scripts**, so the unsigned local build is not
  rejected by web runtimes (that restriction only applies to scripted files).
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

**Signature transition — "running stitch fold".** A needle runs down the
leading edge of a full-bleed appliquéd fabric panel that hinges in from the
right (forward, terracotta) and stitches a running seam as it travels; under
cover the scene switches, the camera has pulled back to 0.86 so the larger
backdrop quilt shows at the edges as the panel folds away to the left and the
camera settles to 1.0 (≈ 18 + 26 frames = 730 ms). Reverse navigation uses a
rose panel hinged from the left and folding away to the right — a mirrored,
differently coloured fold, not the same animation played backwards.

**Signature interaction.** Tap a quilt patch (scene 1, top-right; summary card
corner) to lift its corner on a hinged diagonal and reveal a tiny
"Thank you!"; it settles back after ~2.5 s.

**Per-scene score** (60 fps; 0–200 ms anticipation → 200–1200 ms hero + count
→ 1200–1800 ms headline/support → restrained idle):

| # | Scene | Anticipation | Hero sequence | Idle |
|---|---|---|---|---|
| 1 | Invitation | Name tag lifts and swings in | Nine patches fly in from scattered positions and settle into a quilt; a running thread draws around it; the wordmark banner unfolds across the middle row | banner sway |
| 2 | Hours | Centre card squashes | Four triangles unfold on hinges around the embroidered numeral, corner patches spin in | triangles breathe, motifs sway |
| 3 | Projects | Numeral leans back | Twelve patches rise and land one by one with a squash, then the grid seams are sewn | grid sways |
| 4 | Community days | Calendar lifts before it drops | Calendar swings down, five fabric strips unroll from it, days are marked | calendar sway, clouds drift, sun turns |
| 5 | Garden | Soil dips | Cloth soil layers rise, a stitched sprout grows, leaves unfold, a bloom opens | leaves sway |
| 6 | Repairs | Two fabric shapes pull apart | They snap together, a zig-zag seam is sewn and cross-stitches pop down the join; darning weave fills the numeral disc | shapes breathe |
| 7 | Welcome | Doors shiver | Two cloth arches swing open into a lit doorway, a mat unrolls, neighbours walk in | light spill breathes, stars twinkle |
| 8 | Active months | Numeral squashes | Ten seasonal patches pop along a path while one thread loops through them | running-stitch dash crawls |
| 9 | Persona | Scene 8's ten patches converge and spin into the disc | Persona-specific emblem reveal (four choreographies), then title and line | — |
| 10 | Summary | Persona emblem flies from scene 9's disc into its card slot | Card border is sewn, five stat patches drop into place and count up together | — |

Hero sequences: scenes 1, 4, 9 (plus 2, 6, 7). Continuity transitions that
carry an object: **8 → 9** (the ten seasonal patches and thread continue into
the persona disc) and **9 → 10** (the emblem shrinks into the share card), plus
the global guide needle that threads every fold. Custom cubic eases are named
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
| Keyed deformation of cloth / real page-curl folds | No mesh authored (images only) and no 3D | Folds are hinged scale on pivot nodes + gradient fold shadows; the corner lift is a mirrored triangle flap. |
| Camera pull-back revealing a larger quilt | No camera object | A `World camera` node scaled about the centre over a backdrop quilt. |
| Raster grain | Avoided | Texture comes from vector quilting lines and stitches only. |
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

## Measurements

Measured on the authoring machine (Apple M5 Pro, macOS, Rive CLI 1.6.0
native runtime, headless `--bench`, 390 × 844 @1x). **No phone was available**,
so treat these as relative numbers, not device frame rates.

| Metric | Value |
|---|---|
| `patchwork-recap.riv` | 368,150 bytes (134,505 gzipped); ~150 kB of that is the three embedded fonts |
| Objects | 1 artboard, 49 timelines, 1 state machine with 10 layers |
| Idle scene, 600 frames | advance mean 0.039 ms (p95 0.16), render mean 0.28 ms (p95 0.38) |
| Auto-advancing through scenes + fold hand-offs (3 s dwell), 1,200 frames | advance mean 0.10 ms (p95 0.17, max 24 ms on first text shaping), render mean 0.43 ms (p95 0.49, max 21.5 ms) |
| Memory | no wasm growth over 1,200 frames (no scripts) |

Budget notes: inactive scenes are collapsed by a `Solo` (not drawn, not
hit-tested); decorative counts are fixed (12 patches, 10 months, 21 days) and
never one object per raw count; no masks/clips are used; only the fold shadow
uses a gradient; no feathering.

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
* The motion preview video is assembled from headless captures at a reduced
  frame rate; review exact timing in the live previewer.
* Copy hard-coded in the file: only the wordmark "Patchwork" (brand) — all
  other text is bound.
