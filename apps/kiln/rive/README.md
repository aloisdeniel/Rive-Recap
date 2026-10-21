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
tools/capture_all.sh [section…]           # regenerates captures/
```

Desktop presentation: run the previewer with `--viewport=1280x800 --fit=contain`
(centred portrait), or host the artboard in a portrait container with `Fit.layout`.

### Project layout

| Path | What |
|---|---|
| `scene.rml` | the whole document (generated, but plain editable RML; ~2.8 MB because every state animation keys the full property union — see Limitations) |
| `tools/gen_kiln.py`, `chrome.py`, `scenes.py`, `motif.py`, `motif_build.py`, `sharecard.py`, `model.py`, `rml.py` | generator: view model, chrome, the ten scenes, the vessel/plinth motif, the share card |
| `scripts/sequencer.luau` | clock + navigation brain (ScriptedLayout behind the recap) |
| `scripts/recap_rules.luau` | shared visibility / privacy / persona-fallback rules (module) |
| `scripts/card_rules.luau` | applies those rules when ShareCard is rendered on its own |
| `scripts/format.luau` | locale-aware number formatter (ScriptedDataConverter) |
| `fixtures/fixture.json`, `new-user.json`, `extreme.json` | the three exported view-model instances |
| `assets/fonts/` | DM Serif Display, Manrope (SIL OFL 1.1, licence texts alongside) |
| `captures/` | settled scenes, personas, transitions, reduced motion, fixtures, responsive, share card, motion preview |

### Artboards

* **KilnRecap** (390 × 844, default, state machine `Recap`) — the experience.
* **ShareCard** (300 × 440, component) — the collectible card. Nested in scene 10 and
  assembled there through a `NestedRemapAnimation`; its authored pose is the settled
  card, so a host can instantiate it alone, bind the same `UserRecap` instance and
  snapshot it with no chrome or progress bar (`captures/share-card/`).

## Structure and choreography

Scene hierarchy (front to back): sequencer script → header (wordmark, progress, year)
→ footer controls → ten copy columns (layout, responsive) → card stage → **art stage**
(scene fronts → persona emblems → persistent vessel + plinth → scene backs).

State machine `Recap`, 16 layers:

* **Scene 1…10** — each: Hidden → Enter / Enter Back / Enter Reduced → Idle ⇄ Frozen →
  Exit / Exit Back / Exit Reduced → Hidden, gated by `currentScreen`, `_navDir`,
  `reducedMotion`, `_frozen`. Every animation in a layer keys the same property union,
  so interrupting at any point settles deterministically (rapid taps end clean on the
  final requested scene — `captures/…`, `check_interactions.sh`).
* **Motif** — the persistent vessel and plinth. Per scene a forward handoff, a reverse
  handoff and a reduced-motion cut, entered from AnyState. All vessel profiles share the
  same 12 cubic vertices, so the silhouette morphs continuously.
* **Persona** — four emblems, each with its own reveal, idle, reduced, frozen and exit.
* **Controls** (story vs share/replay footer, initial focus), **Pause Glyph**,
  **Events** (`screenChanged`), **Completion** (`recapFinished`).

Signature pieces:

| Brief | Implementation |
|---|---|
| Signature transition: vessel compresses into a clay slab that expands into the next plinth | every forward handoff (Motif layer): a 260 ms eased blend into the slab pose, then the slab expands into the scene's vessel and plinth with overshoot (`captures/transitions/forward-*`) |
| Signature interaction: drag rotates a turntable highlight; release settles with weighted easing | sequencer `pointerMove` writes `_turnPhase`; a feathered highlight clipped to the silhouette is bound through `sin`/`cos` formulas; release keeps velocity and decays exponentially. Separate hit regions on scenes 1, 2, 3, 7; a drag never navigates, a still tap on the vessel still does |
| Lump → vessel, glaze flowing down a clipped silhouette, firing colour shift | scene 1 motif timeline; glaze ribbon clipped by the vessel and scaled from its lip; scene 5 body colour raw grey → glow → porcelain while kiln bands glow then cool |
| Hero sequences (≥3) | 1 wordmark revealed through a disc opening from the vessel; 4 jug tilts and pours, nine tiles glaze in sequence; 5 kiln glow/cool; 7 six profiles morph in measured steps with the matching silhouettes lighting; 9 persona reveal |
| Continuity transitions (≥2) | the vessel/plinth carried through every scene; the vessel becomes the clay mound in 6 and the orb in 9; it compresses into the slab that becomes the card in 10 |
| Reverse navigation | separate Exit Back / Enter Back (copy drops in from above) and Motif Back (the piece sinks and springs up instead of the slab handoff) |
| Counting | each hero number: `stat × clamp(currentScreen − N + 1, 0, 1)` → eased `DataConverterInterpolator` (1.2 s, slow start ≈ the 200 ms orient beat) → `format.luau`. No placeholder digits flash; it counts down while leaving backwards |
| Staggered reveals | text modifiers (glyph opacity + rise) per run, timed to the brief's 0–200 / 200–1200 / 1200–1800 ms score |

Persona choreographies (scene 9, after the vessel shrinks into an orb with rings and sparks):
0 **Form Finder** — asymmetric vessel drawn as one stroke, then filled, leaning echo;
1 **Glaze Alchemist** — glazed test tile spins in, cobalt sphere drops, droplets orbit;
2 **Wheel Regular** — porcelain wheel disc, charcoal bowl rises, ripples, spin streak;
3 **Handbuilt Storyteller** — clay coils stack one by one, fingerprints appear.

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

Internal (file-owned, do not write): `_command` (1 next, 2 previous, 3 pause, 5 replay —
written by buttons/keys), `_navDir`, `_frozen`, `_holding`, `_seg1…10` (progress segment
display), `_isEmpty`, `_personaVariant`, `_namePublic`, `_hoursPublic`, `_countSeconds`,
`_turnPhase`, `_finished`, `_settled`, `_art*`/`_card*` (responsive placement), and
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

Tap right two-thirds → next, left third → previous (sequencer, outside header/footer).
Press-and-hold ≥ 0.35 s pauses timer + decorative motion; releasing never fires a tap.
Buttons: Previous, Pause/Play, Continue (story); Share, Replay (summary); all ≥ 44 pt.
Keys: Right / Left / Space on the stage (bubble from the focused control), Enter on the
focused button. Initial focus: Continue (`FocusActionTarget`).

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
* **Turntable "rotation"** — a moving clipped highlight and fixed core shade, not 3D.
* **Glaze flow** — a clipped ribbon scaled from the lip, not a fluid sim; drips are pooled shapes.
* **Depth / tactile surface** — feathered fills and layered facets; no raster grain.
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

* `build/kiln-recap.riv`: **592,051 bytes** (`--once`, unsigned scripts), of which ~241 KB are the two
  embedded fonts. `scene.rml` 2.8 MB source; 36,201 objects in KilnRecap, 337 in ShareCard.
* `rive . --bench=600` (headless CLI on the authoring MacBook, release-baked scripts, 390×844):
  advance mean 0.024–0.031 ms (p95 ≤ 0.065 ms); render-encode mean 0.06 ms on scenes 1/4/5,
  0.15 ms on scene 9 (one 38 ms first-frame outlier); no wasm memory growth over 600 frames.
  These are CPU-side CLI timings, **not** device GPU frame rates — no phone was available,
  so on-device fps is unmeasured.
* Bounded complexity: 9 tiles, 7 shards, 8 sparks, 4 droplets — no object per raw count;
  clips: one vessel silhouette, one wordmark disc, one kiln chamber, per-tile glaze clips.

## Remaining limitations

* **Focus is not drawn** — buttons are focusable and keyboard-operable, but there is no
  visible focus ring yet; hosts should draw one or this needs a focus/blur listener layer.
* In summary mode the story buttons are moved off-screen; focus may stay on the hidden Continue.
* 320 × 568 reflows (copy columns, header, footer) and the art scales to ~0.53, but it is tight:
  copy can touch the art on long locales and the summary headline nearly meets the card.
* Back navigation does not recount numbers (they stay at their value), by design.
* `soundEnabled` has no effect (no audio authored); haptics not used.
* RTL, CLDR plural rules and compact large-number labels ("12.5K") are host work.
* The jug in scene 4 and the bowl glaze in scene 3 are stylised and read less clearly than
  the concept art; the vessel art is flat-shaded vector, not the concept's textured render.
* `scene.rml` is generator output (2.8 MB); editing by hand is possible but the
  generator is the practical source. The .rev opens it in the editor.

## Exports

* `build/kiln-recap.riv` — produced and re-imported by the CLI (`--once`, `--verify` clean,
  `inspect` 0 problems).
* `build/kiln-recap.rev` — **not produced.** `rive . --once --rev=build/kiln-recap.rev` stops with
  "Not logged in. Run: rive login". After `rive login`, run that command (or `rev` in the
  previewer) to export the editor file. No other file was renamed to stand in for it.
* For web runtimes, scripts must be signed: `rive . --publish` (also needs login).

## Captures (`captures/`)

`settled/` all ten scenes · `personas/` four personas, settled + mid-reveal ·
`transitions/` every forward handoff at 8/20/40 frames, reverse 3→2, replay 10→1 ·
`reduced-motion/` · `fixtures/` new user, extreme/long copy, public share flags, runtime update
before/after, de-DE locale · `responsive/` 320×568, 430×932, desktop contain ·
`share-card/` standalone card (private default and public) · `motion-preview-autoplay.mp4`
(full auto-advance run, 3 s dwell, sampled at 8 fps from deterministic headless renders) ·
`interaction-checks.txt` (output of `tools/check_interactions.sh`).
