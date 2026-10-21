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
* `captures/motion/handoff-2-to-3-30fps.gif` (one handoff, frame-exact) and
  `captures/motion/full-auto-advance-4fps.gif` (the whole recap auto-advancing
  with a 3 s dwell) are rendered from headless frames by `tools/motion_preview.py`.
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
| Signature handoff | Every navigation fires `handoffForward` / `handoffBack`: a cream steam ribbon with a tomato ink thread draws across the screen while its loop vertices morph, followed by a checked tablecloth pulled across the bottom with a rippling hem; tomato, garlic, basil and lemon riding on it are flung up and land rearranged. Back navigation plays the mirrored version, and each scene has distinct forward (lift up-left) and back (sink down-right) exits. |
| Hero sequences | 1 lid pop → vegetables thrown out in arcs, wordmark rising out of steam; 2 three timed waves of cutouts dropping into the pot + splash + leaves leaping back out; 3 four cookbook pages flipping over the spine; 4 four arrangements spiralling in around a plate while sauce draws a spiral; 5 jars hopping onto uneven shelves with squash and stretch; 6 bowl spins and throws out a scalloped medallion + ribbon banner; 7 place settings expand outward round a gingham table; 8 a steam stitch loops through a loose calendar, days popping as it passes; 9 per-persona reveal; 10 share card slides in and assembles stamp by stamp. |
| Count-up | 200–1200 ms window: the director's eased `countProgress` drives a formula per scene, so digits count from 0 to the bound value in sync with the hero motion and never show the placeholder. |
| Signature interaction | Tap the pot (opaque hit region, also a semantics button "Stir the pot"): lid wobble, squash, six ingredients flourish out and fall. |
| Reduced motion | `reducedMotion=true`: scenes cut to their settled composition with a 220 ms opacity fade, motif poses jump, no handoff, count shows the final value at once, persona emblem static. |
| Pause | `motionFrozen` (pause after the entrance settles) is bound to `isPaused` of every nested artboard, so decorative loops freeze in place and resume from the same frame; the dwell timer stops; navigating while paused still works. |

## Unsupported techniques and substitutions

* **Steam ribbon morphing into lettering.** Rive cannot morph a path into glyph
  outlines. Substitute: the steam stroke trims up into the wordmark while the
  wordmark's glyphs rise out of it with a text-modifier reveal.
* **Cloth simulation / keyed deformation of the tablecloth.** No mesh deform on
  vector art here; the ripple is keyed vertex animation of the hem (and the
  clip path), with the gingham clipped to it.
* **Raster grain.** Not used. Risograph texture comes from offset ink layers
  (25 % aubergine copies offset 3–6 pt under every cutout) and sparse vector
  specks.
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
  1-frame `Off` state, so their loops do not run.

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
