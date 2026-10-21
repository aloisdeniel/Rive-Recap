# Stash — 2026 recap (Rive)

A ten-scene, Wrapped-style recap for the fictional goal-based savings app
**Stash**, built as an editable Rive CLI project (RML + Luau). One global
`UserRecap` view model drives every scene, the progress segments, the persona
reveal and the share card. The brief is [`../PROMPT.md`](../PROMPT.md).

The dataset is the brief's **fictional** full-year 2026 fixture; nothing here
is measured user activity.

## Preview

```bash
cd apps/stash/rive
rive .                       # live previewer (rebuilds on save); 390×844 master
rive . --viewport=320x568    # small phone          (layout reflows; stage scales)
rive . --viewport=430x932    # large phone
rive . --viewport=1440x900   # desktop: centred portrait column
rive . --data=personaIndex=2 --data=reducedMotion=true   # any UserRecap field
```

In the window: click/tap the right two-thirds to advance, the left third to go
back, press-and-hold to pause; Left/Right/Space/Tab/Enter on the keyboard; tap
the little pachinko board (bottom-left) to nudge its coin.

Builds:

| Output | Command | Status |
|---|---|---|
| `build/stash-recap.riv` (also `export/stash-recap.riv`) | `rive . --once` | **built**, 1.18 MB, unsigned |
| `build/stash-recap.rev` | `rive . --once --rev=build/stash-recap.rev` | **not produced** — the CLI requires `rive login` (“Not logged in. Run: rive login”). Run that command after logging in. |
| signed `.riv` for shipping | `rive . --publish` | needs `rive login` (see *Limitations*: scripts) |

## Project layout

| Path | What |
|---|---|
| `a_data.rml` | `UserRecap` view model (+ `ZeroUser`, `Extreme` fixture instances), converters, font and script assets |
| `b_recap.rml` | `Recap` artboard: chrome, stage, ten scenes, motif, overlays, the `Recap` state machine and its 116 timelines |
| `c_components.rml` | `Coin` and `ShareCard` component artboards + their `ComponentAsset`s |
| `scripts/director.luau` | sequencing director (ScriptedLayout, draws nothing) |
| `scripts/progress.luau` | progress segments (ScriptedLayout, data-driven drawing) |
| `numfmt.luau`, `scripts/fmt_*.luau` | locale formatter module + four ScriptedDataConverters |
| `scripts/b2*.luau` | boolean → opacity converters (privacy, empty state, pause icon) |
| `tools/gen.py`, `tools/rml.py` | generator for the three `.rml` files (see note) |
| `tools/behaviour.py` | 25 headless behaviour checks → `captures/tests/behaviour.txt` |
| `tools/capture.py`, `tools/motion_preview.py`, `tools/grid.sh` | review captures and the MP4 |
| `fixtures/*.json` | `sample` (identical to `../sample-data.json`), `zero-user`, `extreme-long-copy` |
| `assets/fonts/` | Rubik + Nunito Sans variable fonts and their OFL texts |
| `captures/` | settled scenes, personas, reduced motion, fixtures, transitions, viewports, share, interaction, motion MP4 |

The `.rml` files are ordinary, editable RML. They are emitted by
`python3 tools/gen.py` because the recap repeats a lot of structure (ten scene
layers with an identical state graph, coins, odometer windows, formula
tokens). Either keep editing the generator and re-run it, or edit the RML
directly and drop the generator — the CLI writes ids back into the RML on
build either way.

## Architecture

```
Recap artboard (bound to UserRecap/Default)
├─ Director            ScriptedLayout, absolute full-bleed (logic only)
├─ Header              layout row: wordmark · progress segments (script) · year · pause
├─ Footer: story       layout row: previous · continue
├─ Footer: summary     layout row: replay · share   (swapped by the Footer mode layer)
└─ Stage               x/y/scale bound to _stageX/_stageY/_stageScale (fit 390×844)
   ├─ Coin toy         signature interaction, own hit region
   ├─ Handoff          coin + spring overlay (signature transition)
   ├─ Toy machine      the persistent motif (pose per scene)
   └─ Scene 10 … Scene 1   each: content group + full-bleed panel with an ink lip
```

**One state machine, `Recap`, 15 layers** (all run simultaneously):

* `Scene 1…10` — identical graphs: `Hidden → Enter (forward | back | reduced) →
  Shown ⇄ Frozen → Exit (forward | back | reduced) → Hidden`, conditioned on
  `currentScreen`, `_navDir`, `reducedMotion`, `_frozen`. Only the current and
  the outgoing scene ever animate, so hidden scenes are skipped for free and
  rapid input re-targets mid-transition (90 ms blends) without stacking.
  Higher scenes draw above lower ones, so forward = the next panel is pushed
  up over the current one; back = the current panel drops away and reveals the
  previous one (a different, deliberately reversed design).
* `Motif` — ten poses of the toy machine; every pose→pose transition is a 760 ms
  eased blend (0 ms in reduced motion). This is continuity transition #1.
* `Handoff` — forward: a coin rolls off a rail, lands on a spring, the spring
  compresses and fires as the next panel rises (signature transition,
  continuity #2). Back: the spring stretches and yanks the current panel down
  while the coin is thrown back up the rail. A/B states let it retrigger.
* `Persona reveal` — four distinct reveal timelines (+ four static
  reduced-motion poses), chosen by `_personaSlot`.
* `Footer mode`, `Coin toy`.

**The director** (Luau) owns what markup cannot express compactly and writes
results back into the *same* UserRecap instance: the derived visible-scene
list, skip-hidden navigation, coalesced input, dwell timer and
`screenProgress`, press-and-hold, pause sources, per-scene count-up playheads,
persona row mapping, input sanitising, stage fit and chrome colour.

## Binding contract

### UserRecap — the brief's schema (all present, same names)

Owner “host” = the host adapter writes it; the file only reads it (except
where noted). Types are native Rive view-model types.

| Property | Type | Owner | Notes |
|---|---|---|---|
| `userName` | String | host | truncated with an ellipsis at the tag width; hidden on the share card unless `shareIncludeName` |
| `year` | Number | host | whole-number converter; rolls in the machine's odometer |
| `periodLabel` | String | host |  |
| `locale` | String | host | drives separators/symbol placement in the in-file formatter |
| `totalSaved` | Number | host | money; clamped ≥ 0 by the director |
| `deposits` | Number | host | integer; rounded, clamped ≥ 0 |
| `goalsCompleted` | Number | host | integer |
| `roundupsSaved` | Number | host | money (2 decimals when it has cents) |
| `activeMonths` | Number | host | integer, clamped to 0–12 |
| `largestGoalAmount` | Number | host | money |
| `goalJars` | Number | host | integer |
| `personaIndex` | Number | host | 0–3; anything else falls back to row 0 |
| `personaName` | String | host / director | see *Persona mapping* |
| `personaDescription` | String | host / director | see *Persona mapping* |
| `personaColor` | Color | host / director | fixture `"#BFF4D4"` is adapted to native `FFBFF4D4` |
| `autoAdvanceSeconds` | Number | host | clamped to ≥ 3 s; non-finite → 7 |
| `autoAdvanceEnabled` | Boolean | host |  |
| `isPaused` | Boolean | host + controls | pause button, Space and `togglePause` write it |
| `reducedMotion` | Boolean | host | OS setting |
| `soundEnabled` | Boolean | host | accepted; the recap is silent by design (no audio assets) |
| `currentScreen` | Number | director / state machine | canonical 1-based scene id; hosts read it (writing it jumps) |
| `screenProgress` | Number | director | 0–1 of the current dwell (summary: 1 once settled) |
| `shareIncludeName` | Boolean | host | share card privacy |
| `shareIncludeSensitiveValues` | Boolean | host | share card privacy (all money) |
| `continueLabel` `previousLabel` `pauseLabel` `playLabel` `shareLabel` `replayLabel` | String | host | button text and accessibility labels |
| `introHeadline` `introSupport` `summaryHeadline` `summarySupport` `emptyHeadline` `emptySupport` `personaLabel` | String | host | localized copy |
| `showScreen1` … `showScreen10` | Boolean | host | eligibility; 1 and 10 are always shown |
| `screen2…8Headline` / `Support` / `Unit` | String | host | localized copy; units are reused as summary tile labels |
| `currencyCode` | String | host | symbol + precision (EUR € / USD $ / GBP £ / JPY ¥ / INR ₹, else the code) |
| `completedGoalName` | String | host | on the scene-7 ticket |

### Adapter additions (documented extensions of the same view model)

| Property | Type | Owner | Purpose |
|---|---|---|---|
| `navNext`, `navPrev`, `togglePause`, `replay` | Trigger | host / controls | the same actions the buttons, keys and screen-reader taps fire |
| `isSharing` | Boolean | host | true while the platform share sheet is up: freezes the timer and idle motion |
| `appBackgrounded` | Boolean | host | true while the app is backgrounded: freezes the timer |
| `personaAutoMap` | Boolean | host | default true: the director writes persona name/description/colour from `personaIndex`. Set false when the host supplies localized persona strings |
| `_count1`…`_count10` | Number | director | count-up playheads (local animation state, not user data) |
| `_navDir`, `_visibleCount`, `_visibleIndex`, `_canGoBack`, `_canGoNext`, `_isSummary`, `_emptyState`, `_personaKnown`, `_personaSlot`, `_frozen`, `_holding`, `_finished`, `_pauseButtonLabel`, `_focus` | various | director / SM | derived sequencing state — read-only for hosts |
| `_chromeColor`, `_chromeOnColor` | Color | director | header/footer ink, eased between cream (dark scenes) and ink (light scenes) |
| `_stageX`, `_stageY`, `_stageScale`, `_viewW`, `_viewH`, `_chromeInset` | Number | director | responsive fit |
| `_handoffFwd`, `_handoffBack`, `_coinNudge` | Trigger | director / toy | drive the overlay layers |
| `_evtScreenChanged`, `_evtRecapFinished`, `_evtShareTapped` | Trigger | state machine | verification mirrors of the three events (the CLI cannot observe Rive events) |

No per-screen copy of any statistic exists: every hero value, odometer,
token/jar/window count, share tile and accessible value binds the global
property directly (through converters).

### Events

| Event | Fired by | Payload |
|---|---|---|
| `screenChanged` | the Enter state of each scene (forward, back or reduced), once per actual change, plus once for the initial scene | none — **read `currentScreen`** when it arrives (Rive events can carry custom properties, but a bound payload was not needed and was not verified, so the documented integration is “event + read the model”) |
| `recapFinished` | the summary's first settle (`_finished` latch); not again until `replay` | none |
| `shareTapped` | the Share button (click, Enter, screen-reader tap) | none — the host captures and opens the share sheet |

### Formatting (in-file adapter)

Rive's `DataConverterToString` has no grouping separators, so formatting is a
documented in-file adapter: `numfmt.luau` + `ScriptedDataConverter`s.
`fmtCount` / `fmtMoney` (visual) and `fmtCountExact` / `fmtMoneyExact`
(accessible text, never compacted). Rules: counts are integers; money uses
`currencyCode` with two decimals only when the value has cents (whole units
while counting up, so digits never flicker); ≥ 1,000,000 shows a compact visual
label (“€12.3M”) while the accessible value stays exact (“€12,345,678.90”).
Locales: en-* `1,248.50` / prefix symbol; de/es/it/nl/pt/… `1.248,50 €`;
fr/sv/nb/fi/pl/… narrow-space grouping `1 248,50 €`; de-CH `1’248.50`. RTL
locales are **not** handled (see limitations). A host that prefers its own ICU
formatting can replace the two converters without touching any scene.

### Persona mapping

| `personaIndex` | `personaName` | Emblem (unique reveal) | `personaColor` | `personaDescription` |
|---|---|---|---|---|
| 0 (and any invalid value) | Steady Builder | stacked toy blocks drop and squash into a tower | `#BFF4D4` | Small steps, your own pace. |
| 1 | Goal Collector | three tokens hop in arcs into a tilting tray | `#FFB490` | You make space for plans that matter. |
| 2 | Roundup Ranger | eleven coins wind into a turning spiral | `#241B3C` | You give small amounts a place to grow. |
| 3 | Patient Planner | calendar jar rises, its page flips, nine days tick in | `#FFF4DD` | You take your time with the next step. |

The director writes the three fields in one frame (`personaAutoMap`); the
emblem is chosen from the same sanitized slot, so label, palette and emblem
cannot disagree. A runtime persona change while scene 9 is showing switches
straight to the new emblem's settled pose. An empty `personaName` (or
`showScreen9=false`, or no visible statistics) removes the persona scene and the
summary's persona chip.

### Host-adapter responsibilities

1. Bind one `UserRecap` instance to the `Recap` artboard / state machine (the
   file ships `Default` = sample, `ZeroUser`, `Extreme`). To capture the share
   card, instantiate artboard `ShareCard` with the **same** instance.
2. Write fixture/user fields; convert colour strings to native colours; supply
   localized strings; set `showScreenN` from metric availability (unknown → hide,
   genuine zero → show).
3. Listen for `screenChanged` (then read `currentScreen`), `recapFinished`,
   `shareTapped`. On `shareTapped`: set `isSharing=true`, render `ShareCard`
   (it is already settled), open the platform sheet, then restore `isSharing=false`
   (the user's `isPaused` is never touched, so the previous pause state returns).
4. Set `appBackgrounded`, `reducedMotion`; provide screen announcements if the
   platform needs them (the semantics tree is exposed — see Accessibility).
5. Ship a **signed** build (`rive . --publish`) — see Limitations.

## Motion design

Material: chunky ink-outlined toy-bank parts, bevelled coins (a reusable `Coin`
component), mechanical odometer windows, starbursts. Every scene follows the
score: anticipation (panel push / lift), hero reveal with a count-up timed to
its illustration (`COUNT` windows in the director), headline word cascade and
support resolve, then a restrained idle loop (paused by `_frozen`).

| Scene | Hero sequence |
|---|---|
| 1 Invitation | machine drops in with squash, the wordmark rises through the jar label (clip), a coin rides the path into the lid; odometer rolls to the year |
| 2 EUR saved | seven coins slide down a chute into the lid slot and fall into the glass; the coin pile rises through a clip mask, synced to the count |
| 3 Deposits | odometer board rolls (ones digit continuous, higher digits tick); a coin takes a zigzag track into the machine |
| 4 Goals | up to three tokens arc in and snap into the tray with squash + click flash (shown = min(goals, 3)) |
| 5 Roundups | eight small coins spiral in and merge into one large coin with a flash |
| 6 Active months | twelve windows light in a loose, non-calendar order (lit = activeMonths) |
| 7 Goal funded | the lid pops and a ticket rises out of the slot through a clip mask |
| 8 Goal jars | up to six jars fan out onto a shelf from below |
| 9 Persona | the machine rattles, its lid pops, the spotlight opens, then one of four emblem choreographies |
| 10 Summary | the share card flips in; its tiles stamp in via a nested timeline (`NestedRemapAnimation`) |

Reduced motion: every scene uses a static final pose (all keyed values at
their end) with a short sequential opacity change (out 100 ms, in 170 ms), no
handoff overlay, no motif travel (0 ms pose blends), counts at their final
value immediately.

## Accessibility

* Buttons (pause/play, previous, continue, replay, share) are 44–54 pt targets
  with `SemanticData` role button, labels bound to the model, `FocusData`, a
  visible peach focus ring, Enter/keypad-Enter and screen-reader tap.
  Previous reports disabled on the first scene; the inactive footer's buttons
  are hidden from the tree.
* Each scene exposes its headline (heading level 1), support line and hero
  value (label = unit, value = exact formatted value); non-current scenes are
  hidden from the tree. Verified with `rive . --semantics`.
* Keys on the artboard: Right/Left navigate, Space pauses, Tab/Shift+Tab move
  focus. The entry state focuses the artboard so keys work immediately.
* No flashing (flashes are single, < 300 ms, low-contrast bursts); the
  experience is silent.

## Verification

* `rive . --verify` — 0 errors, 0 warnings. `rive inspect . --summary` —
  `problems: []`.
* `python3 tools/behaviour.py` — 25/25 pass (`captures/tests/behaviour.txt`):
  tap zones, rapid taps (5 taps → scene 6, one `screenChanged` per scene),
  hold/release (no nav on release), pause/resume, keyboard, hidden scenes 3/5/6
  skipped both ways with 7 segments, full auto-advance 1→10 with exactly one
  `recapFinished` and no loop, auto-advance off, unsafe duration clamp,
  backgrounded freeze, replay resets latch, share fires once, buttons, persona
  remap + invalid fallback, negative/non-integer sanitising, zero user
  (intro → summary, 2 segments).
* Runtime data updates: `captures/interaction/runtime-update-*.png` (deposits
  96 → 4,321 and `locale=de-DE` → `4.321`).
* Captures: `captures/settled` (10 scenes + sheets), `personas` (settled +
  mid-reveal for all four), `reduced-motion`, `fixtures/zero-user`,
  `fixtures/extreme-long-copy`, `transitions` (forward f20/f30 and back f14 for
  every adjacent pair + a 6-frame strip of the signature handoff),
  `viewports` (320×568, 430×932, 1440×900), `share` (private default, name +
  values, standalone `ShareCard`, zero user), `interaction` (coin toy, focus
  ring, paused), `motion/autoplay-full-run.mp4` (15 fps, real timing, full
  auto-advanced run with 3 s dwell).

### Measurements (Apple M5 Pro, macOS 26.6, CLI 1.6.0, headless @1x)

| | |
|---|---|
| `.riv` size | 1,183,175 B (≈ 930 KB of it is the two variable fonts, embedded) |
| objects | Recap 19.8k (state machine + keyframes dominate), Coin 43, ShareCard 465 |
| `rive . --bench=3200` (full auto-run) | advance mean 0.033 ms (p95 0.098), render mean 0.170 ms (p95 0.243, one 24.7 ms outlier at load) |
| bounded pools | ≤ 8 moving coins per scene, 12 windows, 6 jars, 3 tokens; one clip per mask; offscreen scenes sit in `Hidden` (no loops) |

These are CLI headless numbers, not an on-device frame-rate measurement — no
physical test device was available; measure on target hardware before
shipping.

## Unsupported techniques and substitutions

| Brief asks | Done instead |
|---|---|
| “global” view model | `UserRecap` is one instance bound at the root and inherited by every nested component (`Coin`, `ShareCard`). Rive's `viewModelType="global"` was not used: `--data` cannot reach a global (no headless proof of runtime updates) and runtime support for host-bound globals varies. Functionally it is the single shared instance. |
| Locale/currency formatting | in-file Luau converters (Rive has no grouping/ICU converter) |
| Event payloads | events carry no payload; hosts read `currentScreen` |
| Derived persona binding | director script mapping (atomic), switchable off for host-localized strings |
| Visible-scene list / skip logic / timers / hold-to-pause | director script; the state machine still owns all scene, motif, handoff, persona and footer sequencing and every event |
| Progress segments | scripted drawing (segment count is data) |
| Keyed deformation / bones | squash-and-stretch via keyed scale on grouped parts; no meshes |
| Path-following coin | keyed x/y along authored rail vertices (no follow-path constraint) |
| Freezing decorative motion on pause | idle loops cross-fade (200 ms) to their rest pose; entrance animations already in flight finish |
| Raster grain | not used (pure vector) |
| `.rev` export | blocked on login (see Builds) |

## Remaining limitations (honest list)

* **Scripts are unsigned in `--once` builds.** Web runtimes reject unsigned
  scripts; without the director nothing sequences and the counters stay at 0.
  A shippable file must be built with `rive login` + `rive . --publish`. This
  was not done here.
* `.rev` not produced (not logged in), so “opens in the Rive Editor” is
  unverified. RML carries `familyName`/`styleName`, state positions and
  artboard positions for a clean editor import.
* Event delivery verified only through the mirror triggers (the CLI does not
  surface Rive events); verify `screenChanged`/`recapFinished`/`shareTapped`
  in the host.
* Long headlines (+40 %) shrink the headline only (`fitFontSize` in a two-line
  slot) rather than reflowing the scene; the hero value also uses
  `fitFontSize`. Names truncate with an ellipsis.
* RTL locales and right-to-left layout were not implemented or tested.
* Odometers show `+` in every window for values ≥ 10,000 (deliberately not
  modulo); the hero text carries the real value.
* Header/footer colour eases between cream and ink during a transition, so for
  ~250 ms the chrome has reduced contrast.
* Frame-rate figures are CLI headless, not device measurements; the font
  files are full variable fonts (no subsetting tool was available).
* The CLI capture is @1x; check Retina sharpness in the live window.

## Fonts

| File | Family | Source | License |
|---|---|---|---|
| `assets/fonts/Rubik-VF.ttf` | Rubik (variable, wght 300–900) | `google/fonts` `ofl/rubik/Rubik[wght].ttf` | SIL OFL 1.1 — `assets/fonts/OFL-Rubik.txt` (© 2015 The Rubik Project Authors) |
| `assets/fonts/NunitoSans-VF.ttf` | Nunito Sans (variable) | `google/fonts` `ofl/nunitosans/NunitoSans[YTLC,opsz,wdth,wght].ttf` | SIL OFL 1.1 — `assets/fonts/OFL-NunitoSans.txt` (© 2016 The Nunito Sans Project Authors) |

Both are embedded unmodified (OFL permits bundling/embedding with software).
Weights are set with `TextStyleAxis wght`; display uses Rubik 800/900, body
Nunito Sans 600–900. Fallback: if either file is missing the CLI build fails
loudly; to ship without embedding, remove `file=` from the `FontAsset` and have
the host supply the bytes by asset name (`Rubik`, `Nunito Sans`).
