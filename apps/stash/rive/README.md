# Stash — 2026 recap (Rive)

A ten-scene, Wrapped-style recap for the fictional goal-based savings app
**Stash**, built as an editable Rive CLI project (RML + Luau). One global
`UserRecap` view model drives every scene, the progress segments, the persona
reveal and the share card. The brief is [`../PROMPT.md`](../PROMPT.md).

The dataset is the brief's **fictional** full-year 2026 fixture; nothing here
is measured user activity.

## Improvement pass (3D, shaders, motion, consistency)

### Critique of the first pass

* **Flat hero material.** Coins, the brief's hero material, were flat
  discs that read as stickers. The scene-2 jar was mostly empty, dull grey
  glass, far from the concept's overflowing mint jar.
* **The signature transition was tiny.** A 30 pt coin and a small spring sat
  in the bottom-right corner while a flat panel wiped up. It read as a slide.
* **Inconsistent type and alignment.** Headlines were left-aligned in scenes
  1, 2, 5, 6 and 7 and centred elsewhere; hero values alternated left, centre
  and right. Support lines floated at a different height in every scene.
  Headlines that needed a third line shrank.
* **Overlaps.**
  * The corner "pachinko board" toy collided with the machine's plinth in
    scenes 1, 2 and 9.
  * The motif jar sat behind the footer buttons in scenes 6 and 8.
  * Scenes 3–5 parked a 0.3× machine at the bottom as clutter.
  * The extreme fixture pushed long units and supports into the art.
* **Orphans.** "A little year. A lot of / you." on the summary, a lone
  "rhythm." in scene 5, and "…a place to / grow." for Roundup Ranger.
* **Money flicker.** Values flickered into cents while counting
  (€568.25, €1,208.37), contradicting the formatter's own rule.
* **Replay icon.** Its arrowhead sat at the arc's start, pointing nowhere.
* **Progress segments** were 6 pt hairlines in one colour, unlike the
  concept's chunky accent pills.
* **Reduced motion.** Idle loops (twinkles, rays) kept running.
* **Events** were verified only through mirror counter triggers.

### What changed

1. **Real 3D coins everywhere** (`scripts/coin3d.luau` + `.wgsl`).
   * **Geometry.** A lathed coin: flat face, raised rim, rounded reeded edge,
     mirrored back. It is built in the vertex shader from a shared (u, s) grid
     of 5.8k vertices.
   * **Embossed icons.** The face carries a star, house, graduation cap or palm
     from 2D signed distance fields, as bevel normals with an engraved edge line.
   * **Material.** Cel-softened gold reflects a small procedural studio, with a
     specular glint. An inverted-hull ink outline matches the art direction's
     chunky outline.
   * **Keyable pose.** `yaw`, `pitch` and `roll` are `ScriptInputNumber`s that
     the timelines key:
     * drop coins tumble;
     * the pachinko coin's roll is keyed from the distance it travels;
     * goal tokens flip two or three turns into the tray;
     * the merged roundup coin spins faster with each arrival, then brakes face-on.
   * **The `Coin` component is now this coin**, so all 60 placed coins share one
     material: the pile, persona spiral, share card and spills.
2. **A glass jar for the motif** (`scripts/jar3d.*`).
   * **Two layers.** The far wall (with a caustic band near the floor) draws
     behind the coin pile; the near wall draws in front. The near wall is clear
     face-on, thick and tinted at grazing angles, and carries two tall softbox
     streaks, a thin rim streak and a curved shoulder glint.
   * **No depth buffer, no `discard`.** Each layer returns transparent for the
     faces it does not own.
   * **Exact outline.** The profile matches the vector outline, which
     `tools/gen.py` traces from the same function.
   * **Fuller pile.** A bounded pile of 36 3D coins replaced the flat gold
     slab. The jar now visibly fills in scene 2 and stays full, and a glint
     sweeps the glass once it has filled.
3. **Signature transition rebuilt around chrome springs** (`scripts/spring3d.*`).
   * **The springs.** Two helix tubes are wound in the vertex shader from a
     keyed `height`, so they compress with round wire and twist as they close.
     Chrome reflects a cream sky, a sharp horizon and a grape floor, with an
     ink hull.
   * **The forward sequence:**
     * the next scene's panel rests on their launch bar at the bottom of the screen;
     * a 3D coin rolls off a rail onto the right spring (f24);
     * the bar and the panel dip under the impact while the outgoing scene dips
       in sympathy;
     * the springs fire (f29); the panel lands with overshoot at f48 while the
       coin is flung out of the top, spinning.
   * **After the launch** the springs recoil and drop out of view by f44.
   * **Back navigation** is the reverse story: the dropping panel lands on the
     springs, compresses them, and the coin is thrown back up the rail.
   * **Draw order.** The springs draw *behind* the motif machine, which stands
     on the bar; the coin draws in front.
4. **An arcade screen** (`scripts/crt.*`): a fragment-only CRT pass over
   scene 6's month windows.
   * Phosphor bloom spills from each window by how lit it is, computed from
     the same `activeMonths × _count6` as the vector windows.
   * Fine scanlines, a slow refresh band, a curved-glass sheen and a vignette.
   * The output is premultiplied with the glow in rgb and only the darkening in
     alpha, so it composites additively over the vector board.
5. **One copy system.**
   * Every metric scene stacks a centred headline, hero, unit and support
     line on the same grid (`copy_block`).
   * Headlines sit in a **three-line, bottom-anchored slot**, so a third line
     grows upward at full size; only a fourth line shrinks.
   * Units fit to one line; measures were chosen against orphans.
6. **Recompositions.**
   * Scene 3: a pachinko board feeds the machine's lid.
   * Scene 4: feeder chutes, plus one token launched from the machine.
   * Scene 8: the machine launches the jars onto the shelf, bumping its lid once per jar.
   * Scenes 2 and 4: the chute was moved clear of two-line copy.
   * The machine's poses now keep it whole above the footer in every scene.
7. **The signature interaction moved into the motif.**
   * The tap toy is the coin waiting at the mouth of the machine's coin path,
     present in scenes 1–9.
   * Tapping it sends it spinning up the tube into the lid, and a fresh coin
     pops back.
   * The director hit-tests it from the generated `motifpose.luau`, with a hit
     region of at least 46 pt, and never navigates on it.
   * The cluttering corner board is gone.
8. **Fixes.**
   * Money counts in whole units until it settles: €148 → €148.50 at the end,
     never €568.25 mid-count.
   * The replay glyph is rebuilt from geometry: a clockwise arc open at the
     top, its arrowhead on the arc's end along the tangent.
   * Progress pills are 8 pt; finished segments are mint on dark scenes and
     grape on light ones.
   * Idle loops rest under reduced motion.
9. **Events, verified as events.**
   * `screenChanged` carries an `index` payload bound to `currentScreen`.
   * A harness artboard, `EventProbe`, nests `Recap` and *hears* the three
     real Rive events, so the counts are observed headlessly.
   * The `Recap` artboard is now `isComponent` so it can be nested; it is
     still the file's main artboard.

### 3D / shader techniques used, and where they were not

* **Used:**
  * scripted GPU canvases with WGSL;
  * vertex-shader geometry from uniforms: a lathe for the coin and jar, a helix
    tube for the springs;
  * an inverted-hull outline pass with a depth buffer;
  * 4× MSAA on coins and springs where the GPU offers it;
  * premultiplied alpha blending for the glass;
  * a fragment-only fullscreen triangle for the CRT;
  * procedural materials only (no textures, no blobs).

  Every piece renders in the headless `--screenshot` path, so the video and
  captures show it.
* **Not used:**
  * 3D for the plinth, tray, ticket, shelf, jars, persona blocks and share card.
    They read better as the art direction's chunky vector, and keep text and
    bindings native.
  * A full-screen background shader for the dark scenes. It added cost on every
    frame without beating the flat grape.
  * Arcade flashing of any kind: the CRT band is slow and dim.

### Fallbacks and reduced motion

* **Without GPU scripting** (`context:shader` returns nil):
  * coins draw as flat vector discs scaled by their pose;
  * the jar draws a tinted vector silhouette;
  * the springs draw ink-and-steel zigzags;
  * the CRT adds nothing.

  The story, bindings and controls are unchanged.
* **Reduced motion:** 3D inputs are held at their final values, the handoff
  never plays, and idle loops rest. Coins, the CRT band and the toy are
  therefore still.
* **Pause, hold and sharing:** the same rest pose applies, plus 200 ms blends.

### New compromises

* **GPU is required for the captured look.** Unsigned local builds already
  need `--publish` for web, and the 3D now depends on it too.
* **Memory.** About 80 small GPU canvases (78 coins, most about 150 px
  square at 2 px per pt), two jar layers (about 370 × 450 px), two springs
  (about 180 × 960 px each) and one CRT canvas (about 390 × 296 px).
  * Static coins render exactly once.
  * Animated pieces re-render only while their pose changes.
* **Resolution.** Pieces are rendered at 2 px per pt, so they are slightly
  softer than vector on 3× screens.
* **Light under rotation.** Light is fixed relative to each piece, so a
  2D-rotated pile coin rotates its highlight. Hero coins use the keyed `roll`
  instead, which keeps the light top-left.
* **Longer handoff.** The forward handoff is ~0.8 s (panel lands at f48),
  longer than the first pass's 0.6 s. Count-up windows and the settle time
  (2.5 s) moved with it.
* **The springs sit near the controls.** They rise behind the footer; for
  ~0.5 s their coils show either side of the Continue button.
* **`EventProbe` ships in the file.** It is 24 objects and never instantiated
  by a host.

### Performance

Apple M5 Pro, CLI 1.6.0, headless @1x. Render figures are CPU-side submission,
not device GPU time. The "this pass" runs were taken while other projects were
rendering on the same machine, so they overstate the cost somewhat. Scene 6
alone (CRT live): render mean 0.56 ms, p95 1.27 ms.

Render submission is about 4× the first pass, because of the GPU passes and
their image draws. Each script's `draw` also builds a pose-key string per frame.
It stays far under a 16.7 ms frame except for single first-draw frames.

| | First pass | This pass |
|---|---|---|
| `.riv` (`--once`) | 1,183,175 B | 1,459,124 B (+276 KB: 4 scripts, 4 shaders, the pile coins and timelines) |
| `--bench=600` (intro) advance mean / p95 | 0.023 / 0.097 ms | 0.058 / 0.158 ms |
| `--bench=600` render mean / p95 / max | 0.116 / 0.142 / 0.675 ms | 0.468 / 1.127 / 7.8 ms (first-frame GPU setup and the one-time pile render) |
| `--bench=1500 --data=autoAdvanceSeconds=3` advance mean / p95 | 0.030 / 0.088 ms | 0.097 / 0.265 ms |
| `--bench=1500 …` render mean / p95 / max | 0.133 / 0.178 / 0.607 ms | 0.693 / 1.812 / 19.6 ms (worst frame: a scene's first draw of its 3D pieces) |
| wasm memory growth | +0 | +0 |

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
the gold coin waiting at the mouth of the machine's coin path to send it up the
tube into the lid.

Builds:

| Output | Command | Status |
|---|---|---|
| `build/stash-recap.riv` (also `export/stash-recap.riv`, an identical copy) | `rive . --once` | **built**, 1.46 MB (1,459,124 B), unsigned |
| `build/stash-recap.rev` | `rive . --once --rev=build/stash-recap.rev` | **not produced** — the CLI requires `rive login` (“Not logged in. Run: rive login”). Run that command after logging in. |
| signed `.riv` for shipping | `rive . --publish` | needs `rive login` (see *Limitations*: scripts) |

## Project layout

| Path | What |
|---|---|
| `a_data.rml` | `UserRecap` view model (+ `ZeroUser`, `Extreme` fixture instances), converters, font and script assets |
| `b_recap.rml` | `Recap` artboard: chrome, stage, ten scenes, motif, overlays, the `Recap` state machine and its 116 timelines |
| `c_components.rml` | `Coin`, `ShareCard` and `EventProbe` (test harness) artboards + their `ComponentAsset`s |
| `scripts/coin3d.luau` + `.wgsl` | the 3D gold coin (every coin and goal token in the file) |
| `scripts/jar3d.luau` + `.wgsl` | the motif's glass jar walls (back and front layer) |
| `scripts/spring3d.luau` + `.wgsl` | the chrome coil springs of the signature transition |
| `scripts/crt.luau` + `.wgsl` | the arcade-screen (CRT) pass over scene 6's month windows |
| `motifpose.luau` | generated module: motif pose per scene + toy position (the director's toy hit test) |
| `scripts/director.luau` | sequencing director (ScriptedLayout, draws nothing) |
| `scripts/progress.luau` | progress segments (ScriptedLayout, data-driven drawing) |
| `numfmt.luau`, `scripts/fmt_*.luau` | locale formatter module + four ScriptedDataConverters |
| `scripts/b2*.luau` | boolean → opacity converters (privacy, empty state, pause icon) |
| `tools/gen.py`, `tools/rml.py` | generator for the three `.rml` files (see note) |
| `tools/behaviour.py` | 29 headless behaviour checks → `captures/tests/behaviour.txt` |
| `tools/capture.py`, `tools/motion_preview.py`, `tools/grid.sh` | review captures (incl. `captures/gpu/` 2× close-ups) and an optional autoplay MP4 |
| `fixtures/*.json` | `sample` (identical to `../sample-data.json`), `zero-user`, `extreme-long-copy` |
| `assets/fonts/` | Rubik + Nunito Sans variable fonts and their OFL texts |
| `captures/` | settled scenes, personas, reduced motion, fixtures, transitions, viewports, share, interaction, GPU close-ups, walkthrough MP4 |

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
   ├─ Handoff: coin    the 3D coin of the signature transition (above the machine)
   ├─ Toy machine      the persistent motif (pose per scene): 3D glass jar, 3D coin
   │                   pile, coin path with the tap-toy coin (signature interaction)
   ├─ Handoff: springs launch bar on two 3D chrome springs (below the machine)
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
* `Handoff` — forward: a 3D coin rolls off a rail and lands on the right of two
  chrome springs; the next scene's panel rests on their launch bar, dips with
  the impact, and the springs fire it into view while the coin is flung out the
  top (signature transition, continuity #2). Back: the current panel drops onto
  the springs, compresses them, and the coin is thrown back up the rail. A/B
  states let it retrigger.
* `Persona reveal` — four distinct reveal timelines (+ four static
  reduced-motion poses), chosen by `_personaSlot`.
* `Footer mode`, `Coin toy` (idle wobble ⇄ still under pause / reduced motion;
  nudge, or a calm opacity-only nudge under reduced motion).

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
| `_handoffFwd`, `_handoffBack`, `_coinNudge` | Trigger | director | drive the handoff and coin-toy layers (the director hit-tests the toy coin) |
| `_evtScreenChanged`, `_evtRecapFinished`, `_evtShareTapped` | Trigger | state machine | mirrors fired beside each event, kept for the existing checks |
| `_heardScreenChanged`, `_heardRecapFinished`, `_heardShareTapped` | Trigger | `EventProbe` | pulsed by a harness artboard whose listeners *hear the real Rive events* reported by the nested Recap (verification only; hosts ignore them) |

No per-screen copy of any statistic exists: every hero value, odometer,
token/jar/window count, share tile and accessible value binds the global
property directly (through converters).

### Events

| Event | Fired by | Payload |
|---|---|---|
| `screenChanged` | the Enter state of each scene (forward, back or reduced), once per actual change, plus once for the initial scene | custom property **`index`** (Number) bound to `currentScreen`, the canonical 1-based id; reading `currentScreen` on arrival is equivalent |
| `recapFinished` | the summary's first settle (`_finished` latch); not again until `replay` | none |
| `shareTapped` | the Share button (click, Enter, screen-reader tap) | none — the host captures and opens the share sheet |

The three events are verified *as Rive events*: the `EventProbe` artboard nests
`Recap` (same instance) and its event listeners pulse `_heard*`; checks 26–29 of
`tools/behaviour.py` count them (10 `screenChanged` in a full run, 1
`recapFinished`, 1 `shareTapped`). `EventProbe` is a test harness, not part of
the experience; hosts never instantiate it.

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

Material: chunky ink-outlined toy-bank parts, real 3D minted gold coins (a
reusable `Coin` component and keyable `coin3d` drawables), a lathed glass jar,
chrome springs, mechanical odometer windows, an arcade CRT board, starbursts.
Every scene follows the
score: anticipation (panel push / lift), hero reveal with a count-up timed to
its illustration (`COUNT` windows in the director), headline word cascade and
support resolve, then a restrained idle loop (paused by `_frozen`).

| Scene | Hero sequence |
|---|---|
| 1 Invitation | machine drops in with squash, the wordmark rises through the jar label (clip), a 3D coin spins up the path into the lid, a fresh tap-toy coin pops into the path's mouth; odometer rolls to the year |
| 2 EUR saved | seven 3D coins tumble out of a chute into the glass; the 3D coin pile rises through the jar clip, synced to the count; the jar overflows (coins drop round the base) and a glint sweeps the glass |
| 3 Deposits | odometer board rolls (ones digit continuous, higher digits tick); a 3D coin rolls every rail of a pachinko board (roll keyed from the distance travelled) and drops into the machine's lid |
| 4 Goals | three 3D goal tokens (house, cap, palm) flip in, two from feeder chutes and one launched from the machine, and snap into the tray with squash + click flash (shown = min(goals, 3)) |
| 5 Roundups | eight coins spiral in; each arrival spins the growing 3D coin faster; it brakes and settles face-on catching the light |
| 6 Active months | twelve windows light in a loose, non-calendar order (lit = activeMonths); a CRT pass blooms from each lit window |
| 7 Goal funded | the lid pops and a ticket rises out of the slot through a clip mask |
| 8 Goal jars | the machine launches up to six jars from its lid, one bump per jar, onto a shelf |
| 9 Persona | the machine rattles, its lid pops, the spotlight opens, then one of four emblem choreographies |
| 10 Summary | the share card flips in; its tiles stamp in via a nested timeline (`NestedRemapAnimation`) |

Reduced motion: every scene uses a static final pose (all keyed values at
their end, including every 3D yaw/pitch/roll) with a short sequential opacity
change (out 100 ms, in 170 ms), no handoff overlay (no springs, no flying
coin), no motif travel (0 ms pose blends), counts at their final value
immediately, and idle loops parked in their rest pose (new: before this pass
they kept running): coins do not turn, the CRT refresh band stays off, the toy
coin is still. A toy tap under reduced motion is an opacity blink.

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
* `python3 tools/behaviour.py` — 29/29 pass (`captures/tests/behaviour.txt`):
  tap zones, rapid taps (5 taps → scene 6, one `screenChanged` per scene),
  hold/release (no nav on release), pause/resume, keyboard, hidden scenes 3/5/6
  skipped both ways with 7 segments, full auto-advance 1→10 with exactly one
  `recapFinished` and no loop, auto-advance off, unsafe duration clamp,
  backgrounded freeze, replay resets latch, share fires once, buttons, persona
  remap + invalid fallback, negative/non-integer sanitising, zero user
  (intro → summary, 2 segments), the motif's tap toy (nudges, never navigates),
  and the real `screenChanged` ×10 / `recapFinished` ×1 / `shareTapped` ×1
  heard through `EventProbe`.
* Runtime data updates: `captures/interaction/runtime-update-*.png` (deposits
  96 → 4,321 and `locale=de-DE` → `4.321`).
* Captures: `captures/settled` (10 scenes + sheets), `personas` (settled +
  mid-reveal for all four), `reduced-motion`, `fixtures/zero-user`,
  `fixtures/extreme-long-copy`, `transitions` (forward f26/f34 and back f24 for
  every adjacent pair + a 6-frame strip of the signature handoff),
  `viewports` (320×568, 430×932, 1440×900), `share` (private default, name +
  values, standalone `ShareCard`, zero user), `interaction` (coin toy, focus
  ring, paused), `gpu` (2× close-ups: jar and pile, merged coin, goal tokens,
  arcade board, springs firing), `motion/walkthrough.mp4` (the walkthrough,
  `../video.webm`, transcoded: 30 fps, Right pressed every 3.5 s).

### Measurements (Apple M5 Pro, macOS 26.6, CLI 1.6.0, headless @1x)

| | |
|---|---|
| `.riv` size | 1,459,124 B (≈ 930 KB of it is the two variable fonts, embedded); first pass 1,183,175 B |
| objects | Recap 22.7k (state machine + keyframes dominate), Coin 22, ShareCard 465, EventProbe 24 |
| bench | see *Improvement pass → Performance* |
| bounded pools | ≤ 8 moving coins per scene, 36 static pile coins (each rendered once), 12 windows, 6 jars, 3 tokens; one clip per mask; offscreen scenes sit in `Hidden` (no loops) |

These are CLI headless numbers, not an on-device frame-rate measurement — no
physical test device was available; measure on target hardware before
shipping.

## Unsupported techniques and substitutions

| Brief asks | Done instead |
|---|---|
| “global” view model | `UserRecap` is one instance bound at the root and inherited by every nested component (`Coin`, `ShareCard`). Rive's `viewModelType="global"` was not used: `--data` cannot reach a global (no headless proof of runtime updates) and runtime support for host-bound globals varies. Functionally it is the single shared instance. |
| Locale/currency formatting | in-file Luau converters (Rive has no grouping/ICU converter) |
| Event payloads | `screenChanged` carries `index` (bound to `currentScreen`); the other two need none |
| Derived persona binding | director script mapping (atomic), switchable off for host-localized strings |
| Visible-scene list / skip logic / timers / hold-to-pause | director script; the state machine still owns all scene, motif, handoff, persona and footer sequencing and every event |
| Progress segments | scripted drawing (segment count is data) |
| Keyed deformation / bones | squash-and-stretch via keyed scale on grouped parts; real deformation where it matters is done on the GPU (springs compress by keyed height, coins turn by keyed yaw/pitch/roll) |
| Path-following coin | keyed x/y along authored rail vertices (no follow-path constraint) |
| Freezing decorative motion on pause | idle loops cross-fade (200 ms) to their rest pose; entrance animations already in flight finish |
| Raster grain | not used; the only non-vector pixels are the scripted GPU renders (coins, glass, springs, CRT), all procedural |
| “do not require a real 3D renderer” | the 3D pieces enhance but are not required: without GPU scripting each script draws a flat vector stand-in, and nothing in the story depends on them |
| `.rev` export | blocked on login (see Builds) |

## Remaining limitations (honest list)

* **Scripts are unsigned in `--once` builds.** Web runtimes reject unsigned
  scripts; without the director nothing sequences and the counters stay at 0.
  A shippable file must be built with `rive login` + `rive . --publish`. This
  was not done here.
* `.rev` not produced (not logged in), so “opens in the Rive Editor” is
  unverified. RML carries `familyName`/`styleName`, state positions and
  artboard positions for a clean editor import.
* Events are verified headlessly as real Rive events (through `EventProbe`),
  but the `index` payload's value is not observable from the CLI; check it in
  the host.
* Headlines get three full-size lines (bottom-anchored slot); a fourth line
  shrinks the headline (`fitFontSize`). Long unit labels fit to one line; the
  hero value also uses `fitFontSize`. Names truncate with an ellipsis.
* The 3D pieces and the CRT pass need GPU scripting; elsewhere they fall back
  to flat vector stand-ins (see *Improvement pass*).
* RTL locales and right-to-left layout were not implemented or tested.
* With the extreme fixture's two-line support, scene 2's last line touches the
  top of the coin chute. Sample-length copy clears it by 20 pt.
* The incoming panel and the outgoing scene share hues on 1→2 (both grape), so
  that handoff reads mostly through the springs and the coin.
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
