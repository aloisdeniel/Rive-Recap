# Switchyard — 2026 Rive recap

A ten-scene, Wrapped-style public-transit recap for the fictional app **Switchyard**, authored as RML + Luau for the
Rive CLI (1.6.0). The brief is `../PROMPT.md`; the art-direction reference is `../concept.png`.

All data is fictional sample data for a fictional period (January 1 – December 31, 2026).

## What is here

| Path | What it is |
|---|---|
| `scene.rml` | The whole Rive document: one artboard, the single `UserRecap` view model, 18-layer state machine, 89 timelines. **Generated** by `tools/gen.py` + `tools/scenes.py` (edit those and re-run, or edit the RML directly and stop regenerating). |
| `scripts/sequencer.luau` | Gestures, dwell timer, visible-scene list, progress segments, count-up playheads, persona mapping. |
| `scripts/formatCount.luau` | Data converter: number → locale-grouped integer string. |
| `assets/fonts/` | Subset Archivo Black + Inter (SIL OFL 1.1, licences alongside). |
| `fixtures/` | `sample.json` (= `../sample-data.json`), `zero-new-user.json`, `extreme-long-copy.json`. The same three data sets are also exported as view-model instances `Fixture` (default), `NewUser`, `Extreme`. |
| `build/switchyard-recap.riv` | Runtime export (unsigned local build, see *Limitations*). |
| `captures/` | Review captures (see *Captures*). |
| `tools/scenarios.py` | 13 headless interaction tests with assertions (`captures/scenarios/results.txt`). |
| `tools/capture.py` | Regenerates every capture (`--motion` adds the auto-advance GIF). |

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
  (persistent route dot + interchange ring), `Scene 10 … Scene 1` (each: `Content` layers over a `Background`, clipped
  by its own interchange disc), `Clip sources`.
* **State machine `Recap Sequencer`**, 18 layers:
  * `Scene 1` … `Scene 10` — each: `Hidden → EnterFwd | EnterBack | Settled(RM) → Idle ⇄ Settled(paused) → ExitFwd |
    ExitBack → Hidden`, all guarded on `currentScreen`, `_navDir`, `reducedMotion`, `isPaused`. Scene 9 has four
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
`_focusIndex` (focused dock button, drives focus rings), triggers `_nextTapped`, `_prevTapped`, `_pauseTapped`,
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

* **Signature transition (forward):** the red route dot leaves the bottom of the story window along an angular
  schematic path, enters an interchange ring placed on the next scene's focal point, the ring squeezes
  (anticipation) and then expands; its stroke rides the edge of the circular clip that reveals the next scene. The
  outgoing scene lifts 28 px and dims under it. ~700 ms.
* **Reverse transition:** the current scene collapses back into its interchange ring (clip + ring shrink together),
  the dot pops out and drops away, while the previous scene slides in from the left and re-sets its headline. ~650 ms.
* **Continuity objects:** the motif (dot + ring) is one persistent group carried across every handoff; the ring
  becomes each scene's edge. Scene 1 establishes it (wordmark lockup is the same ring + route stub).
* **Hero sequences:** (1) Invitation — four lines draw, interchanges snap in, oversized year rolls in, ticket chip
  feeds in, wordmark is revealed by its route stub; (2) Journeys — a route dot draws the angular network around the
  count, stations pop as it passes, train and tram arrive; (3) Km — orbits draw, a ticket strip feeds from a slot
  through a measuring frame carrying the unit; (5) Stations — a strictly schematic map draws on linear timing and
  stations populate in reading order; (6) Ferry — wave bands rise in sequence, the ferry sails in and settles;
  (7) Weekend — a white ticket drops, tears along its perforation, and the halves become red/blue weekend panels;
  (8) Months — the board slides up and twelve tiles flap like a departure board (lit by `activeMonths`);
  (9) persona reveals above; (10) Summary — the collectible ticket card is thrown in, lines draw, persona disc pops,
  stat cells stamp in sequence.
* **Counting:** 200 → 1200 ms, ease-out cubic, driven by the sequencer (`_countN` × value through a formula
  converter) so digits never flash placeholders and pause freezes the count.
* **Idle loops** (restrained, seamless): riders running routes with faded ends, orbit rotation, hub breathing,
  station pulse, wave bands translating exactly one crest period, ferry bob, slow sun-ray turn, occasional board
  flap, persona micro-motion. Pause or reduced motion eases them to their settled pose.

## Fonts and licences

| File | Family | Source | Licence |
|---|---|---|---|
| `assets/fonts/ArchivoBlack-Switchyard-Subset.ttf` | Archivo Black Regular | github.com/google/fonts `ofl/archivoblack` | SIL OFL 1.1 (`OFL-ArchivoBlack.txt`) |
| `assets/fonts/Inter-Switchyard-Subset.ttf` | Inter (variable `wght` 400–700, `opsz` pinned 14) | github.com/google/fonts `ofl/inter` (`Inter[opsz,wght].ttf`) | SIL OFL 1.1 (`OFL-Inter.txt`) |

Both were subset with fontTools to Basic Latin, Latin-1, Latin Extended-A, common punctuation (en dash, curly
quotes, U+202F) and arrows, to keep the `.riv` small. Glyphs outside that set (e.g. Greek, Cyrillic, CJK, Arabic)
will not render: ship a wider subset (or the full OFL files) for those locales. No system fonts are embedded.

## Unsupported techniques and substitutions

| Brief asks for | What was done |
|---|---|
| Responsive layout across 320 × 568 / 430 × 932 / desktop | Fixed 390 × 844 master composition presented with `Fit.contain` (verified in `captures/viewports/`). A true reflowing layout of layered vector illustration was not attempted; at 320 × 568 the piece scales to ~67 %. |
| Event payloads | `screenChanged` carries a bound `screen` custom property; hosts without event-property support read `currentScreen`. |
| Locale-aware formatting | Built-in converters cannot group digits, so a Luau `ScriptedDataConverter` does it; plurals and compact labels are host-adapter work. |
| Pause freezes decorative motion | Rive has no bindable playback speed per state, so pausing eases idle loops back to their settled pose (320 ms) rather than freezing mid-frame. Dwell timer and count-up do freeze exactly. |
| Raster grain / tactile texture | Not used — all artwork is flat layered vector. |
| Keyboard "focus visible" | Blue focus ring on dock buttons driven by focus/blur listeners. The file focuses Continue at start (and Share on the summary), so the ring is visible from the first frame. |
| Hidden decorative hit regions | Route chips are hit-tested inside the sequencer script (only on scene 4), so invisible chips can never intercept taps. |
| Single *global* view model | Implemented as one artboard-bound `UserRecap` instance (not Rive's `viewModelType="global"`), because the CLI's `--data`, scripts' `context:viewModel()` and per-fixture instances all need the bound form. There is still exactly one instance in play at runtime. |
| Sound | None (silent by design; `soundEnabled` is accepted and ignored). |

## Measurements (CLI headless, Apple M5 Pro, macOS 26.6.2, `rive --bench=600`)

| Scene | advance mean / p95 | render mean / p95 |
|---|---|---|
| 1 (intro, incl. entrance) | 0.016 / 0.051 ms | 0.164 / 0.090 ms (one 55 ms first-frame outlier: font/shaper warm-up) |
| 4 | 0.015 / 0.048 ms | 0.068 / 0.091 ms |
| 6 (waves) | 0.018 / 0.049 ms | 0.100 / 0.109 ms |
| 9 (persona) | 0.015 / 0.046 ms | 0.084 / 0.124 ms |
| 10 (summary) | 0.010 / 0.016 ms | 0.099 / 0.132 ms |

Script memory: 0 wasm-page growth over 600 frames. `.riv` size ≈ 322 KB (≈160 KB of it fonts). These are CLI timings
on a desktop, **not** on-device frame rates — no phone was available; measure on target hardware before shipping.
Budgets kept: one clip mask per scene (only one or two visible at a time), no per-count objects (12 board tiles,
≤14 stations), scene layers sit in a static `Hidden` state when offscreen.

## Captures

`captures/settled/` (all ten scenes + sheets), `captures/personas/` (each persona settled + three reveal frames),
`captures/reduced-motion/`, `captures/fixtures/` (zero/new user, extreme/long copy on every scene, name opt-in,
runtime update `journeys=9999`, `de-DE` grouping), `captures/transitions/` (three intermediate frames for every
forward handoff 1→10, reverse collapses 3→2 / 6→5 / 10→9, route-chip ride), `captures/viewports/`,
`captures/motion/switchyard-auto-advance.gif` (full auto-advance run at 12 fps, `autoAdvanceSeconds=4`),
`captures/scenarios/` (interaction test end frames + `results.txt`).

## Limitations (honest list)

* **`.rev` (editor export) not produced** unless someone runs `rive login` and then
  `rive apps/switchyard/rive --once --rev=apps/switchyard/rive/build/switchyard-recap.rev`. Editor opening is
  therefore unverified.
* The `.riv` is an unsigned local build containing two Luau scripts: it needs a Rive runtime with scripting
  support, and web runtimes reject unsigned scripts — use `rive --publish` (login required) for web.
* Without the sequencer script nothing navigates (taps, timer, progress bar, count-up and persona mapping live
  there). The progress segments are script-drawn, so they are not editable as vector layers in the editor.
* Fixed composition + `Fit.contain` instead of true responsive reflow; no RTL layout (no RTL target locale in
  the brief; text boxes are left-aligned, an RTL locale would need mirrored compositions).
* `inspect` reports one warning, `no-default-artboard`, even though `rive.yaml` sets `main` (single artboard, so the
  runtime fallback is the same artboard).
* Headless captures cannot judge feel at real frame timing; the motion GIF is sampled at 12 fps. Open the
  previewer for real-time review. No live host app (iOS/Android/web) was built — the "host preview" is the Rive
  previewer plus `--data` runtime updates.
* Hold-to-pause and story taps are implemented for pointer/touch in the script; multi-touch edge cases
  (two fingers) were not tested.
