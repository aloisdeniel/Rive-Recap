# Simmer — 2026 recap (Rive)

A ten-scene, data-bound Wrapped-style recap for the fictional home-cooking app
**Simmer**, authored as RML for the Rive CLI (1.6.0). Risograph-cookbook
collage art, a persistent joyous pot motif, a steam-ribbon + tablecloth-pull
handoff between scenes, four persona emblems with their own choreography, and a
collectible share card. All numbers and copy are fixture data (a fictional
2026), not measured activity.

```
apps/simmer/rive/
  rive.yaml                 project (default artboard: "Simmer Recap")
  data/user-recap.rml       UserRecap view model + 3 fixture instances, fonts, scripts, converters
  scenes/main.rml           root artboard: chrome, progress, controls, motif poses, handoff, director, events
  scenes/scenes.rml         S1..S10 scene components (each with its own state machine)
  scenes/components.rml     Pot motif + Share card components
  scenes/converters.rml     count-up / progress formulas
  scripts/director.luau     sequencing + input + derived-data adapter (runs inside the file)
  scripts/formatCount.luau  locale-aware count formatter (scripted data converter)
  scripts/eventAudit.luau   logs host events as they fire (verification aid)
  scripts/steam.luau/.wgsl  signature steam veil (GPU shader)            } improvement pass,
  scripts/cloth.luau/.wgsl  simulated 3D tablecloth pull (GPU mesh)      } see "Improvement
  scripts/letters.luau/.wgsl steam condensing into the wordmark (scene 1) } pass" below
  scripts/riso.luau/.wgsl   risograph paper + ink-starvation stock       }
  fixtures/*.json           fixture, new-user (zero), extreme / long-copy
  assets/fonts/             Bricolage Grotesque, Source Sans 3, Caveat (+ OFL texts)
  tools/build.py            generator that writes data/ and scenes/ (see "Editing")
  tools/capture.py          headless captures + behaviour checks
  captures/                 PNG evidence + captures/checks/*.json
  build/simmer-recap.riv    runtime export
```

## Preview

```bash
rive apps/simmer/rive                       # live previewer (opens a window; tap, hold, keys work)
rive apps/simmer/rive --data=personaIndex=2 # any UserRecap property can be overridden at launch
rive apps/simmer/rive --data=currentScreen=9 --data=reducedMotion=true
```

Fixture instances are exported on `UserRecap`: **Fixture** (default, from
`sample-data.json`), **New user** and **Extreme**. To preview another fixture as
the default, `python3 tools/capture.py fixtures` builds
`build/variants/new-user/` and `build/variants/extreme/`, each a complete
project you can open with `rive build/variants/new-user`.

Build the runtime file: `rive apps/simmer/rive --once` → `build/simmer-recap.riv`.

## Architecture

* **One user-data view model, one instance.** `UserRecap` is bound to the root
  artboard (`Simmer Recap`). Every scene, the pot motif and the share card are
  *non-stateful* nested artboards, so they inherit that same instance through
  the data context; their binds address `UserRecap` properties by absolute
  path. No component owns a copy of any statistic.
  *Why not `viewModelType="global"`?* It works in this toolchain (tested), but
  a global instance cannot be selected per fixture or set with `--data`, and
  instance binding at the root is supported by every runtime's auto-bind API.
  The root-bound instance is the single, shared ("global") source of truth the
  brief asks for; switching the declaration to `global` is a one-attribute
  change in `tools/data.py` if a host prefers Rive's global-VM API.
* **Sequencing state machine.** `Recap sequence` (root) has layers for the
  motif pose (an explicit state per scene, 720 ms eased carry between any two),
  the signature handoff (forward / mirrored back), controls swap, pause icon,
  focus ring, previous-enabled and boot focus. Each scene component runs its
  own `Life` machine: `Off → Enter → Idle`, `→ Exit forward | Exit back → Off`,
  plus reduced-motion `EnterRM / ExitRM`, all keyed on `currentScreen`,
  `navDirection` and `reducedMotion`. Rapid navigation always settles on the
  latest `currentScreen` because every scene only asks "am I current?".
* **Director (`scripts/director.luau`).** A full-bleed `ScriptedLayout` behind
  everything. It is the documented adapter the brief allows: it builds the
  visible-scene list, writes `currentScreen / currentSegment / visibleCount /
  screenProgress / navDirection / countProgress / motionFrozen`, runs the dwell
  timer, handles tap-left/tap-right/hold, keyboard, control requests, persona
  derivation, sanitising and sentence assembly. Controls and the pot are opaque
  hit targets above it, so they never also navigate.

## Binding / event contract

Owner: **H** = host writes, **D** = director writes (host reads), **H→D** = host
writes, director may normalise.

| Property | Type | Owner | Notes |
|---|---|---|---|
| `userName` | string | H | greeting; share card only when `shareIncludeName` |
| `year` | number | H | header + card (plain integer, no grouping) |
| `periodLabel`, `locale` | string | H | `locale` drives digit grouping (see formatting) |
| `mealsCooked` … `cookingDays` (7) | number | H→D | negative → clamped to 0; NaN/±∞ = unknown → scene hidden |
| `personaIndex` | number | H→D | 0–3; anything else normalised to 0 |
| `personaName`, `personaDescription` | string | D | derived atomically from `personaIndex` |
| `personaColor` | **color** (ARGB) | D | the fixture's `"#FFEDB0"` string is adapted to a native colour |
| `autoAdvanceSeconds` | number | H | clamped to 3–60 s; non-finite → 7 |
| `autoAdvanceEnabled`, `reducedMotion`, `soundEnabled` | bool | H | sound unused (silent by design) |
| `isPaused` | bool | H / D | button, Space and hold toggle it; host sets it on background |
| `currentScreen` | number | D (H may deep-link) | canonical 1-based id; external writes are honoured |
| `screenProgress` | number | D | 0–1 of the current dwell; 1 once the summary settles |
| `shareIncludeName`, `shareIncludeSensitiveValues` | bool | H | default false |
| `continueLabel` … `replayLabel`, all headlines / supports / units, `empty*`, `personaLabel`, `summary*`, `introSupport` | string | H | bound to text and to button semantics labels |
| `introHeadline`, `screen6Support` | string | D (from templates) | see additions |
| `showScreen1..10` | bool | H | 1 and 10 always shown; 9 hidden when no metric is eligible |
| `favoriteRecipeName` | string | H | scene 6 medallion + sentence; on the card only with `shareIncludeSensitiveValues` |

**Additions** (documented, all in the same instance):

| Property | Type | Owner | Purpose |
|---|---|---|---|
| `greetingTemplate` | string | H | localized, `{name}` placeholder → `greetingLine` |
| `introHeadlineTemplate` | string | H | `{year}` → `introHeadline` |
| `screen6SupportTemplate` | string | H | `{recipe}` → `screen6Support` |
| `greetingLine`, `summaryNameLine`, `summaryRecipeLine` | string | D | derived; the two summary lines are empty unless the privacy flags allow |
| `isSharing` | bool | D sets / **H clears** | set on Share; when the host clears it, the prior pause state is restored |
| `navDirection` | number | D | +1 forward, −1 back (choose exit/handoff variant) |
| `visibleCount`, `currentSegment` | number | D | progress segments (exactly `visibleCount` drawn) |
| `countProgress` | number | D | count-up playhead (animation state, not user data) |
| `motionFrozen` | bool | D | `isPaused && settled`: pauses every nested artboard |
| `isEmptyRecap` | bool | D | no eligible metric → welcoming summary, no persona |
| `focusedControl` | number | D | keyboard focus ring (1 prev, 2 pause/play, 3 continue, 4 share, 5 replay) |
| `recapComplete` | bool | D | completion latch (reset by Replay) |
| `navNextRequest`, `navPrevRequest`, `pauseToggleRequest`, `shareRequest`, `replayRequest`, `potTap` | trigger | controls → D / pot | requests; hosts may fire them too |
| `handoffForward`, `handoffBack`, `recapFinishedSignal` | trigger | D | internal signals |

**Events** (root state machine):

| Event | Fired when | Payload |
|---|---|---|
| `screenChanged` | a view-model listener sees `currentScreen` change | none — read `currentScreen` |
| `shareTapped` | the Share button (click or screen-reader tap) | none — host captures and opens the share sheet |
| `recapFinished` | the summary first settles (once until Replay) | none |

Event payload custom properties were not used: the host reads the canonical
values from `UserRecap` at the moment the event arrives. Each event listener
also logs `event: <name>` (eventAudit) so headless runs show exactly when they
fire. Verified counts are in `captures/checks/report.json` (e.g. a full
auto-advance run fires `screenChanged` ×9 and `recapFinished` ×1).

**Formatting.** Counts go through `Count-up + format scene N` = formula
(`round(value × max(countProgress, min(1, |currentScreen − N|)))`) then
`formatCount.luau`, which groups digits by `locale` (en `,` · de/es/it/pt/nl `.`
· fr/sv/pl/… narrow no-break space · de-CH `’`). Values ≥ 100 000 render as a
compact visual label (`123.4K`, `1M`); the exact value must be provided by the
host in accessible text. Pluralisation is the host's job: units are bound
strings (`screen2Unit` …) the host writes in the right plural form.

**Persona mapping** (director table; unknown → 0):

| Index | Name | Emblem (unique choreography) | Accent |
|---|---|---|---|
| 0 | Flavor Explorer | dancing spice pot (bursts up, arms, legs, spice beat) | `FFFFEDB0` |
| 1 | Comfort Cook | steaming bowl (rises, steam draws on and breathes) | `FF48293D` |
| 2 | Batch Wizard | stacked meal tins (drop, squash-stack, wizard tip, sparkles) | `FF4D7655` |
| 3 | Weekend Baker | sunburst oven mitt (sunburst spins open, mitt waves, loaf slides in) | `FFE44932` |

Localising persona names: the director writes English defaults on every
`personaIndex` change. A localising host should write `personaName` /
`personaDescription` **after** setting `personaIndex` in the same frame (or
replace the table in `director.luau`).

**Host adapter responsibilities.** Bind the instance; fill strings (localised
units with correct plurals, templates); set `showScreenN` from data
availability (unknown ≠ zero); set `isPaused=true` and stop advancing when the
app backgrounds; on `shareTapped`, render the **Share card** artboard (it
inherits the bound instance and assembles itself when `currentScreen == 10`;
capture ≥ 1.9 s after it starts, or after `recapFinished`) and open the platform
share sheet, then set `isSharing=false`; provide screen-reader announcements
for scene changes with the exact values.

## Input

| Gesture | Result |
|---|---|
| tap right ⅔ of the content area | next visible scene |
| tap left ⅓ | previous visible scene |
| press and hold ≥ 350 ms | pause while held; release resumes and does **not** count as a tap |
| ← / → | previous / next |
| Space | pause / play |
| Tab / Shift+Tab | move the visible focus ring across the controls; Enter activates it (Enter with no focus = next) |
| Previous / Pause-Play / Continue (Share / Replay on the summary) | 52 pt tall buttons with semantics labels bound to the label strings |
| tap the pot | lid wobble + ingredient flourish; opaque hit region, never navigates |

## Fonts and licences

| File | Family | Licence |
|---|---|---|
| `assets/fonts/BricolageGrotesque.ttf` (variable: opsz, wdth, wght) | Bricolage Grotesque | SIL OFL 1.1 — `OFL-BricolageGrotesque.txt` |
| `assets/fonts/SourceSans3.ttf` (variable: wght) | Source Sans 3 | SIL OFL 1.1 — `OFL-SourceSans3.txt` |
| `assets/fonts/Caveat.ttf` (variable: wght) | Caveat (handwritten annotations) | SIL OFL 1.1 — `OFL-Caveat.txt` |

All three were downloaded from the `google/fonts` GitHub repository and are
embedded in the `.riv` (OFL permits embedding). Fallback: Rive has no system
font fallback; if a host strips embedded fonts it must supply these families by
asset name (`Bricolage Grotesque`, `Source Sans 3`, `Caveat`).

## Editing

The `.rml` files are the editable source the CLI compiles, but they were
**generated** by `tools/build.py` (art, keyframes and the 100+ near-identical
transitions are parameterised there). Edit the generator and run
`python3 tools/build.py`, then `rive . --verify` and `rive inspect . --summary`.
Hand edits to the `.rml` are overwritten on the next generation.

## Verification

* `rive . --verify` → 0 errors, 0 warnings; `rive inspect . --summary` → 0 problems.
* `captures/motion/*.webm` (30 fps, frame-exact headless renders, encoded with
  ffmpeg by `tools/motion_preview.py`): the forward handoff 2→3, the mirrored
  back handoff 5→4, the scene-1 steam lettering and the 8→9 persona reveal.
  The full walkthrough is `apps/simmer/video.webm`
  (`scripts/render-video.py simmer` from the repo root).
* `python3 tools/capture.py` writes:
  `captures/settled/` (all ten scenes), `captures/personas/` (each persona +
  a mid-reveal frame + unknown index), `captures/reduced-motion/`,
  `captures/transitions/` (two intermediate frames per forward handoff, three
  back handoffs, a 100 ms filmstrip of 2→3, the pot tap), `captures/fixtures/`
  (new user intro + welcoming summary, extreme / long copy, runtime data
  update, fr-FR grouping, privacy flags on), `captures/hidden/`,
  `captures/sizes/` and `captures/checks/` (data dumps for every interaction).

## Signature motion, as built

| Brief | Implementation |
|---|---|
| Persistent motif | The pot is one component (`Pot motif`) placed once at the root; a `Motif pose` layer carries it between scenes with a 720 ms eased move/scale/tilt (lid pops on 1 and 9, comes off for 2, closes elsewhere). |
| Continuity transitions (≥2 carrying an object) | pot → shrinks into the bottom of the cookbook (2→3), → tilts and pours orzo into the bowl (5→6), → becomes the centre of the table (6→7), → rattles and dissolves into the persona emblem (8→9), → flies into the share card's emblem slot (9→10). |
| Signature handoff | Every navigation fires `handoffForward` / `handoffBack`. The pot squats and puffs (anticipation); a steam ribbon with a tomato ink thread leaves the pot, curls once through the layout and billows into a risograph-printed veil that hides the cut (GPU shader), then evaporates through a halftone dot screen while its swirl keeps turning. As it clears, a simulated gingham tablecloth is pulled across the bottom of the stage (tug back, pull, billow, yank) and throws the tomato, garlic, basil and lemon riding on it. Back navigation mirrors both. See "Improvement pass". |
| Hero sequences | 1 lid pop → vegetables thrown out in arcs, the pot's steam condenses into the wordmark and evaporates into ink; 2 three timed waves of cutouts dropping into the pot + splash + the whole stew bursting back out and hanging in the steam; 3 four cookbook pages flipping over the spine; 4 four arrangements spiralling in around a plate while sauce draws a spiral; 5 jars hopping onto uneven shelves with squash and stretch; 6 bowl spins and throws out a scalloped medallion + ribbon banner; 7 place settings expand outward round a gingham table; 8 a steam stitch loops through a loose calendar, days popping as it passes; 9 per-persona reveal with eight ingredients thrown into orbit; 10 share card slides in and assembles stamp by stamp. |
| Count-up | 200–1200 ms window: the director's eased `countProgress` drives a formula per scene, so digits count from 0 to the bound value in sync with the hero motion and never show the placeholder. |
| Signature interaction | Tap the pot (opaque hit region, also a semantics button "Stir the pot"): lid wobble, squash, six ingredients flourish out and fall. |
| Reduced motion | `reducedMotion=true`: scenes cut to their settled composition with a 220 ms opacity fade, motif poses jump, the lid cuts, no handoff (no steam, no cloth), the wordmark is already set, count shows the final value at once, persona emblem static. |
| Pause | `motionFrozen` (pause after the entrance settles) is bound to `isPaused` of every nested artboard, so decorative loops freeze in place and resume from the same frame; the dwell timer stops; navigating while paused still works. |

## Unsupported techniques and substitutions

* **Steam ribbon morphing into lettering.** Rive cannot morph a path into glyph
  outlines, so this is done on the GPU instead (`scripts/letters.*`): the
  wordmark is rendered from a vector artboard into a texture and the steam
  shader condenses into it. Without GPU scripting the wordmark simply fades in.
* **Cloth.** A real position-based simulation in Luau drawn as a lit 3D mesh
  (`scripts/cloth.*`); without GPU scripting the same simulation is drawn as
  flat vector quads.
* **Raster grain.** Procedural only (`scripts/riso.*`, rendered once per size);
  no bitmap ships. Without GPU scripting the offset ink layers and specks
  still carry the risograph look.
* **Event payloads.** Not used (see contract); hosts read `UserRecap`.
* **Responsive layout.** The master is a fixed 390 × 844 artboard with
  absolute-positioned art (clipped). Hosts should use `Fit.contain` and fill
  the letterbox with paper `#FBF0D6`. Captured at 320 × 568, 430 × 932 and
  1280 × 800 (desktop, centred) in `captures/sizes/`. It does not reflow;
  320 × 568 renders at 0.67× scale (text ≥ 12 pt effective for body copy).
* **Keyboard focus.** Focus is owned by the director (one `FocusData`), which
  draws its own focus ring and maps Tab/Enter; it is not the runtime's native
  `FocusData` traversal across buttons. Screen-reader activation of every
  button goes through semantic listeners.
* **Accessible text.** Buttons and the pot expose semantics; scene copy and
  numbers are ordinary `Text` (not exposed as semantics nodes). The host must
  announce scene changes with the exact values.
* **Sound / haptics.** None; `soundEnabled` is accepted and ignored.
* **RTL.** Not verified (no RTL locale in scope); copy blocks are left/right
  aligned per scene, not mirrored.

## Measurements

These are the first-pass figures; the improvement pass's numbers are in its
own section at the end.

* `build/simmer-recap.riv`: **1,749,061 bytes**, of which ~1.46 MB are the three
  embedded variable fonts (Bricolage 408 KB, Source Sans 3 646 KB, Caveat
  404 KB). Subsetting them would bring the file under ~400 KB.
* `rive . --bench=600` (release-baked scripts, Apple M5 Pro, macOS 26.6, CLI
  headless renderer, 390 × 844 @1x): advance mean **0.024 ms** (p95 0.062 ms),
  render mean **0.121 ms** (p95 0.112 ms, max 18.5 ms = first frame), wasm
  memory flat over 600 frames. Not measured on a phone.
* Object counts (`rive inspect --summary`): root 3.8k, scenes 0.5k–2.8k each
  (S9 with four persona emblems is the heaviest), pot 1.3k, share card 0.9k.
  Particles are bounded pools (≤ 34 orzo grains, 6 flourish pieces, 7 pour
  grains); nothing scales with raw counts. Offscreen scenes sit in a static
  1-frame `Off` state, so their loops do not run. (Improvement pass: root 4.0k,
  S9 3.5k, S2 2.2k; the GPU pieces are four scripts, not objects. The cloth
  is one bounded 30 × 13 particle grid, and the riders are four.)

## Status and honest limitations

* **`.riv`: built** (`build/simmer-recap.riv`, unsigned local build).
* **`.rev`: not produced.** `rive . --once --rev=…` requires `rive login`; this
  run was not logged in ("Not logged in. Run: rive login"). After logging in:
  `rive apps/simmer/rive --once --rev=apps/simmer/rive/build/simmer-recap.rev`.
  Opening in the editor was therefore not verified.
* The `.riv` carries Luau scripts (director, formatter, audit). Local builds are
  unsigned; web runtimes reject unsigned scripts, so a web host needs a signed
  build (`--publish`, requires login). Without the director script nothing
  sequences.
* Share is event wiring only: the host owns capture and the platform sheet.
* Frame rate was measured on the desktop CLI, not on a phone.
* The previewer's live window was not opened by this agent (headless captures
  only); interaction was verified with synthesised pointer/key input and data
  dumps (`captures/checks/report.json`).

## Improvement pass

### Critique of the first pass

* **The signature handoff was the weakest moment.** It used the same vector
  ribbon on every cut, and the outgoing scene sat almost unchanged under it.
  Mid-cut, the incoming hero number ("0", then counting) landed on top of the
  old copy (1→2 showed "0" over "Your 2026 on Simmer"; 4→5 showed "14" and
  "0" side by side). Every exit was the same lift-and-fade.
* **The tablecloth was a flat gingham rectangle** wiping along the bottom over
  the controls. Its "ripple" was three keyed hem vertices, and the riders were
  flung up into the header.
* **The steam never became lettering.** The wordmark rose out of a trimmed
  stroke.
* **Flat colour fields.** There was no printed surface, although the brief is
  risograph.
* **Composition:**
  * Scene 1 crowded the period ticket, wordmark, swash and popped lid together.
  * Scene 2 repeated scene 1's pot with a near-empty band above it and a weak
    payoff (three hovering leaves, against the concept's burst of
    ingredients). Its napkin ran into the Previous button.
  * Scene 9's emblem was small inside a large dashed circle, leaving a dead
    band under the title (the concept fills it with a dancing pot and
    swirling ingredients).
  * Scene 4 was sparse and small. Its pot overlapped the "new favourite" note.
  * Scene 8's steam stitch was too faint to read.
  * On the share card, the stamp crowded the last tile.
* **Inconsistency:** Share had an icon and Replay did not. The replay arrowhead
  check from the other demos did not apply, because there was no icon.
* **Reduced motion:** after scenes 1, 2 and 9, the lid still eased back on for
  320 ms.

### What changed

1. **Steam veil, the signature cut (GPU shader, `scripts/steam.*`).** The pot
   squats and puffs (anticipation). A steam ribbon then leaves the pot from
   where it stood, with a tomato ink thread along its spine. It rises, curls
   once through the layout, and its spine points billow as they age, until
   the veil hides the cut at about 300 ms.
   * It is printed like a riso: paper-white cumulus lobes lit from their own
     relief, a cream mid tone, the shadow side as a 45° tomato halftone, and
     an aubergine ink layer offset under it (the same misregistration every
     cutout has).
   * It clears through the dot screen: the fringe breaks into dots that shrink
     away while the swirl keeps turning, uncovering the next layout.
   * Back navigation mirrors it.
   * Rapid navigation continues from the veil instead of popping.
   * The new hero number now arrives behind the veil and is revealed counting,
     so there is no old/new overlap.
2. **A simulated tablecloth pull (3D GPU mesh, `scripts/cloth.*`).** The cloth
   is 30 × 13 particles with structural, shear and bend constraints
   (position-based Verlet), gravity, drag and table friction.
   * Two "hands" pull the leading edge along a keyed path: a tug back, a pull
     in, a slow billowing pass, then the yank. The cloth bunches, lifts and
     folds for real.
   * The simulation runs in the hands' accelerating frame, and every particle
     is tethered to them, so a whip-fast pull never stretches the weave.
   * It is drawn as a lit, depth-tested mesh (4× MSAA) at the presenting pixel
     density, with a cast shadow on the table.
   * The material is woven gingham with darker crossings, a tomato hem with a
     stitch line, and a paler underside where a fold turns over. Light is
     posterised, with the shadow printed as an aubergine halftone.
   * Tomato, garlic, basil and lemon (small vector artboards) ride the cloth.
     When the yank comes, each is thrown with the cloth's velocity plus a hop
     and spin, and tumbles out of frame.
   * The pull follows the steam, as the brief orders it. The pot rides over it.
3. **Steam that becomes the wordmark (GPU, `scripts/letters.*`).** The
   "Simmer" lettering is rendered from a vector artboard into a texture, and
   the shader uses it as the target.
   * The plume off the popped lid is drawn into the real glyphs: a blur and a
     noise warp that both relax to zero.
   * The steam letters then lift and evaporate through the dot screen,
     uncovering the inked vector wordmark printed underneath.
   * This replaces the substitute from the first pass.
4. **Risograph stock (GPU, `scripts/riso.*`).** Two static layers are rendered
   once per size and laid over everything:
   * a paper layer (multiply): tooth, pulp fibres, mottling and inclusions;
   * an ink-starvation layer (screen): clustered pin-holes that show only on
     inked areas, so tomato numbers and aubergine buttons read as printed
     while the paper stays clean.
5. **Composition:**
   * Scene 1: ticket, wordmark and swash raised, and a lower lid pop.
   * Scene 2: the whole stew bursts back out and hangs in the steam (carrot,
     mushroom, onion, basil, tomato, garlic, peas, as in the concept). The
     napkin now sits clear of the controls.
   * Scene 4: a larger plate and arrangements, with butter swooshes trailing
     each arrangement as it spirals in, and the notes moved clear of the pot.
   * Scene 8: the stitch is now the ribbon's cream steam with a tomato thread.
   * Scene 9: the emblem is 1.2× larger and raised 40 pt, with eight
     ingredients thrown into a slow orbit (the motif's persona pose follows).
   * Scene 10: the stamp sits clear of the tiles.
6. **Replay icon.** A counter-clockwise arc open on the right, built from
   geometry. The arrowhead sits on the arc's end and points along its tangent
   (checked at 4×). Share and Replay now both carry icons.
7. **Reduced motion.** The lid now cuts instead of easing.

### 3D and shader techniques: what is used, and where they are not

* **Used:**
  * GPU canvases with WGSL.
  * A dynamic vertex buffer: CPU-simulated cloth, normals per frame, a 32-byte
    interleaved layout.
  * A depth buffer, 4× MSAA resolve, and two pipelines over one bind group
    layout (cast shadow plus cloth).
  * Fragment-only full-screen passes for the steam, the lettering and the
    stock.
  * A Rive 2D canvas used as a texture: the wordmark artboard is sampled by the
    lettering shader.
  * Script-hosted artboard instances for the riders.
  * No `discard` anywhere. No per-frame allocations: buffers, canvases and
    views are created once.
* **Not used: a 3D pot.** A lathed, lit pot was considered and rejected. The
  pot is a flat character with a face and a keyed lid, and the concept art is
  flat illustration, so a shaded 3D pot would break the risograph art
  direction and the character's expressions. Depth comes from the cloth, the
  steam's relief and the print texture instead.

### Fallbacks, reduced motion, pause

* **No shader support:**
  * The steam draws as a thick cream vector stroke along the same spine.
  * The cloth runs the same simulation, drawn as flat vector quads.
  * The lettering draws nothing, and the wordmark fades in.
  * The riso stock is skipped.
* **Reduced motion:** the handoff states never play (progress stays 0, so
  nothing is drawn). The reduced scene-1 entrance holds the lettering's
  progress at 1, so it is already set.
* **Pause** (`motionFrozen`): the steam's flow clock and the cloth simulation
  hold, and the lettering follows its paused scene timeline. Navigating while
  paused still plays the handoff, as before.

### New compromises

* **Constants that must stay in step.**
  * The steam origin per scene (`ORIGIN` in `steam.luau`) mirrors the motif
    poses in `tools/main_board.py`. It has to be kept in step by hand.
  * Likewise the lettering region (`letters.luau`) mirrors scene 1's wordmark
    position.
* **Rapid navigation restarts the cloth.** A handoff that restarts during the
  pull resets the cloth off screen; it is at most 0.5 s of cloth.
* **Overlay roots are absolutely positioned.** The two full-stage overlay
  layouts (cloth, stock) and the Director root are now absolutely positioned
  (`overlay_style`). The artboard is a flex row: in the first attempt the new
  layouts were laid out beside the Director, which shifted its hit area by
  260 pt and broke tap navigation. The checks caught it.
* **Rendering resolution:**
  * The steam renders at 1 px per point (soft by nature, with a coarse dot
    screen).
  * The lettering renders at 2 px per point.
  * The cloth renders at the presenting density, capped at 2×.
  * The stock renders at the presenting density.
* **Headless captures are @1x.**
* **GPU memory:**
  * steam: 1.3 MB;
  * lettering: 2 × 2.2 MB;
  * cloth canvas: 0.75 MB at 1× (3 MB at 2×), plus 4× MSAA colour and depth
    (about 6 MB at 1×);
  * stock: 2 × 1.3 MB at 1× (× scale²).
* **Web needs a signed build.** These are four more unsigned scripts and four
  shaders. WebGPU validation was not exercised; the native preview was.

### Checks

`python3 tools/capture.py checks` gives 20/20 results identical to the
pre-pass `captures/checks/report.json`: same values and same events for tap,
back, rapid ×6, hold/release, pause/resume, keys, Tab/Enter, auto-advance to
the summary, clamping, share, replay, hidden scenes, the pot tap, the negative
clamp and the unknown persona. No check was changed. `rive . --verify` gives
0 errors and 0 warnings; `rive inspect . --summary` reports 0 problems.

### Performance

`rive . --bench`, Apple M5 Pro, headless at @1x. Render times are CPU-side
submission, not GPU time.

| | Before | After |
|---|---|---|
| `build/simmer-recap.riv` | 1,749,061 B | 1,978,084 B (+229 KB: four scripts and shaders, four rider artboards, the wordmark mask, the scene 2/4/9 additions; fonts are still ~1.46 MB of it) |
| `--bench=600` from boot (includes one handoff at 9.1 s): advance mean / p95 | 0.030 / 0.072 ms | 0.08 / 0.92 ms |
| same run: render submission mean / p95 | 0.173 / 0.158 ms | 0.15 / 0.24–0.28 ms |
| `--bench=1200`, `autoAdvanceSeconds=3` (three handoffs): advance mean / p95 / max | — | 0.144 / 0.98 / 1.51 ms |
| same run: render mean / p95 | — | 0.157 / 0.343 ms |
| scene 1 only (`--bench=150`, the lettering shader live): advance / render p95 | — | 0.038 / 0.148 ms |
| wasm memory growth | +0 | +0 |
| walkthrough `video.webm` | 3.8 MB | 10.1 MB (the grain and halftone carry real detail at the same CRF) |

Where the time goes:
* The advance p95 during a handoff is the Luau cloth solver: one substep of
  six iterations over 2,127 constraints plus the tethers, for about 0.5 s per
  cut. It was 3 ms at 2 × 10 iterations and was tuned down until the folds
  stopped changing visibly.
* GPU work exists only while it is visible:
  * the steam: one full-screen pass per frame for about 0.7 s;
  * the cloth: one 806-triangle mesh twice (shadow and body), 4× MSAA, for
    about 0.5 s;
  * the lettering: one pass during scene 1's first 1.6 s;
  * the stock: two passes once per resize, then two image draws per frame.
* Idle frames do no GPU passes beyond the stock composite. On-device GPU time
  was not measured (CLI figures, M5 Pro, @1x).
