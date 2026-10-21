# Parlance — 2026 recap (Rive)

A ten-scene, data-bound Wrapped-style recap for the fictional language-practice app **Parlance**, authored as RML for the Rive CLI (1.6.0). Pure RML: there are **no Luau scripts**, so the unsigned `.riv` from `--once` has nothing that needs signing.

| | |
|---|---|
| Source of truth | `tools/generate.py` (+ `tools/rml.py`) generates `scene.rml`, `components.rml` and `data.rml`. Edit the generator, then run `python3 tools/generate.py`. The RML can also be edited directly, but the next generator run overwrites it. |
| Runtime file | `build/parlance-recap.riv` (1.63 MB, built with `rive . --once`) |
| Editor file | `build/parlance-recap.rev` was **not produced**: `rive . --once --rev=build/parlance-recap.rev` returns `Not logged in`. Run `rive login`, then that same command. |
| Fixtures | `fixtures/sample.json` (the brief's fixture), `fixtures/zero-user.json`, `fixtures/extreme.json` (huge values, a long name, copy at least 40% longer) |
| Captures | `captures/` holds settled scenes, personas, reduced motion, fixtures, transition frames, viewports and `motion-preview.gif`. The behaviour report is `captures/qa-report.txt` (26/26 pass). |

## Preview

```bash
cd apps/parlance/rive
rive .                                   # live previewer (window at 390x844)
python3 tools/fixture.py fixtures/extreme.json         # previewer with a fixture applied (--data)
python3 tools/fixture.py fixtures/zero-user.json --screenshot=out.png --advance=150
tools/shot.sh 9 out.png --data=personaIndex=3          # headless: navigate to scene 9 and capture
tools/trans.sh 3 40 out.png next                       # headless: frame 40 of the 3->4 handoff
python3 tools/qa.py                                    # behaviour checks -> captures/qa-report.txt
```

**Host fit:** the master artboard is a fixed 390×844 design frame. Present it with `Fit.contain` centred, and fill the letterbox with paper `#FFF8EC` or a neutral colour. Captures at 320×568, 430×932 and 1280×800 (a centred desktop presentation) are in `captures/viewports/`. At 320×568 the frame scales to 67%, and there is no separate compact layout (see limitations). All content sits in a fixed `Stage` layout box, so a `Fit.layout` host crops instead of reflowing.

## Structure

- **Artboard `Parlance Recap`** (main, 390×844). From top to bottom of the hierarchy: chrome (wordmark, year, progress row, a `Controls` focus scope holding 5 buttons, the nav hit regions), the mouth hit target, the `Dwell Clock` placement, the hero-reveal driver, the quote aperture, the **persistent motif** (`Motif A` is a persimmon comma-bubble and `Motif B` is a lilac one, each with a face), then `Scene 10` … `Scene 1`. Each scene node holds its copy, foreground, mid and background art. All art is layered editable vectors (PointsPath, parametric shapes and font glyphs). There are no raster images.
- **Component `Dwell Clock`** (nested). It owns the auto-advance timer. Its speed is bound to `1/clamp(autoAdvanceSeconds, 4, 60)` and its `isPaused` to `UserRecap.isPaused`.
- **Component `Share Card`** (nested, 342×556). This is the collectible summary card: wordmark, year, persona emblem, title and the five aggregate tiles. It has its own state machine (assembly, privacy flags, persona pick, new-user mode). It has no chrome, so a host can render it alone for the share snapshot.
- **State machine `Recap`** has these layers:
  - `Sequence`: about 110 states. Per scene there are forward and back gates, In, Back-In, Reduced-motion-In, Dwell, Out, Out-Back and reduced-motion fades, plus carry gates.
  - `Idle loops`
  - `Persona` and `Persona idle`
  - `Chrome theme`
  - `Controls mode`
  - `Pause icon`
  - 8 × `Segment k visibility`
  - `Summary copy`
  - `Press (tap vs hold)`
  - `Mouth tap`

## Single global view model `UserRecap`

There is exactly one view model, `UserRecap`. Every scene, the nested Clock and Share Card, the summary, the progress row and the persona visuals bind to the same instance. The nested artboards inherit the root's data context. **Rive-specific note:** I bound `UserRecap` to the main artboard and did not use Rive's `viewModelType="global"`. The reason: a Rive *global* VM has a single instance and cannot be reached by `--data`/instance selection, which would make fixtures and host instance swapping impossible. Functionally it is still one shared instance. Exported instances: `Sample fixture` (default), `New user fixture`, `Extreme fixture`.

All contract properties from the brief exist with these names and types. Colour strings are `ViewModelPropertyColor` (ARGB): the adapter maps `#RRGGBB` to `FFRRGGBB`.

**Ownership**
- *Host writes:* user data, the `showScreenN` flags, labels and localized copy, `locale`, `autoAdvanceSeconds`, `autoAdvanceEnabled`, `isPaused` (also on app background or while sharing), `reducedMotion`, `soundEnabled`, the `share*` flags, `personaIndex`.
- *File writes (host reads):* `currentScreen` (canonical 1–10), `screenProgress` (0–1 dwell, written by the Clock), and `personaName`, `personaDescription`, `personaColor`. The file derives these three atomically from `personaIndex`; unknown or non-integer indices fall back to row 0.
- *The file also writes `isPaused`* on Pause/Play, Space, and hold-to-pause.

**Adapter additions (not in the brief's table)**

| name | type | purpose |
|---|---|---|
| `groupSeparator` | string | locale digit-group separator (`,` for en-GB, `.` for de, ` ` for fr). The file groups digits itself. |
| `personaName0..3`, `personaDescription0..3` | string | localized persona table. The Persona layer copies the row for `personaIndex` into `personaName`/`personaDescription` and writes `personaColor`, all in one state entry, so the label, palette and emblem never disagree. |
| `goNext`, `goPrevious`, `requestReplay` | trigger | host-callable navigation (the same triggers the buttons, keys and taps fire). |
| `_dwellStart`, `_dwellStop`, `_heroReveal`, `_focusIndex`, `_pointerDown`, `_pressSide`, `_finishedLatch`, `_mouthTap` | internal | animation playheads and latches. The underscore marks them private, and hosts should not write them. |

**Formatting:** counts are clamped with `max(0, round(x))` in converters. Three tiers (<1,000, <1,000,000, larger) build `1,860` or `1,234,567` from `groupSeparator`, and `fitFontSize` handles extreme widths without compacting. Hero numbers count from 0 to the value through the bound `_heroReveal` driver, so no placeholder digits flash. **The host adapter must:** clamp NaN/∞ (converters can't), choose singular or plural unit strings (`screenNUnit`), compose the localized `introHeadline`/`periodLabel` from year and name, and provide accessible full-value text and announcements. `tools/fixture.py` is a reference adapter for previews.

**Events**
- `screenChanged`: fires on every scene entry. Its payload is the custom property `screen`, bound to `currentScreen`. Read `currentScreen` as the source of truth.
- `shareTapped`: fires from the Share button or Enter. The host owns the capture and the platform share sheet. Only the event wiring is supplied; there is no real share integration. Set `isPaused=true` while the sheet is open and restore the previous value afterwards.
- `recapFinished`: fires once, the first time the summary settles. Replay clears the latch.
- `mouthTapped`: fires on the signature interaction. Its payload is `soundEnabled`. The file is silent; if `soundEnabled` is true, the host may play an opt-in sound.

The headless CLI does not report plain events. `qa.py` therefore verifies the state each firing state writes, and confirms that the events exist in the `.riv`.

## Behaviour (all verified in `captures/qa-report.txt`)

- **Navigation:** the right two-thirds of the story area advances and the left third goes back. Holding pauses (350 ms threshold), and releasing resumes without a tap. Previous, Pause/Play and Continue have 52 pt targets; the summary shows Replay and Share. Left/Right navigate and Space pauses. Tab and Shift+Tab move focus (a persimmon ring shows it), and Enter activates the focused button. Buttons carry `SemanticData` labels bound to the label strings.
- **Hidden scenes:** skipped in both directions. The progress row is a flex row with `display:none` per hidden segment, so exactly the visible count renders. Intro and summary are always eligible, whatever their flags say. With no eligible metric scenes, the flow goes intro → welcoming summary (`emptyHeadline`) with a neutral motif and no persona.
- **Auto-advance:** 7 s by default, counted after the entrance settles and clamped to at least 4 s. `autoAdvanceEnabled=false` holds the current scene. Pause freezes the timer, the idle loops and the persona idle while keeping progress. The summary never auto-loops.
- **Rapid taps:** a tap during an entrance skips straight to the next scene, and a tap during an exit skips one further, blending in over 150 ms. Five quick taps from scene 1 land on scene 6, and no scene is entered twice.
- **Reduced motion:** every arrival uses the scene's final pose, a 200 ms fade and no camera or motif movement. The idle loops are frozen and every control still works.
- **Privacy:** the card hides the name unless `shareIncludeName` is set. `practiceMinutes` is treated as the one sensitive aggregate and shows "—" unless `shareIncludeSensitiveValues` is set. No recordings, transcripts or locations appear anywhere.

## Motion

Timings are at 60 fps.

- Scene entrances follow the score: 0–200 ms is the cover reveal or anticipation, 400–1,400 ms is the hero and count, then the copy resolves by about 1.8 s, then a restrained idle runs.
- Handoffs are 450–850 ms. The reverse direction uses a mirrored lilac wipe from the left with a compressed rebuild.

**Hero sequences**
1. Intro: the cover collapses into the motif pair, and the wordmark letters stretch out of an envelope (text modifier).
2. Scene 3: an elastic mouth opens around the rolling numerals.
3. Scene 4: multilingual word blocks cascade into giant quotation marks.
4. Scene 9: the persona reveal. The motif pair orbits and winds up, then collapses into the emblem. Each persona has its own emblem silhouette and choreography: welcoming faces with speech marks, a stacked quotation-mark archive, an open-parenthesis ear with sound ripples, and an elastic exclamation mark with squash and stretch.
5. Scene 10: the summary card assembles.

**Continuity carries**
- 1→2: the two speech forms travel down into the conversation.
- 2→3: the persimmon form flies to centre stage, and its mouth becomes scene 3's mouth.

**Signature transition (3→4):** the mouth elongates until it fills the frame, then scene 4 opens through a quote-shaped clipping aperture. Every other forward handoff uses the motif bubble itself as a stretched wipe.

**Signature interaction:** tapping the illustrated mouth in scene 3 or 2 plays a silent elastic squash. Its opaque hit target cancels the story tap, so it cannot navigate.

## Fonts and licences

| file | source | licence |
|---|---|---|
| `assets/fonts/BricolageGrotesque-VF.ttf` | google/fonts `ofl/bricolagegrotesque/BricolageGrotesque[opsz,wdth,wght].ttf` | SIL OFL 1.1, `assets/fonts/OFL-BricolageGrotesque.txt` |
| `assets/fonts/NotoSans-wght400-700.ttf` | google/fonts `ofl/notosans/NotoSans[wdth,wght].ttf`, instanced to cut size (2.0→1.0 MB, full Latin/Greek/Cyrillic coverage kept) with `fonttools varLib.instancer NotoSans[wdth,wght].ttf wdth=100 wght=400:700` | SIL OFL 1.1 (no Reserved Font Name), `assets/fonts/OFL-NotoSans.txt` |

Both are embedded in the `.riv`. Rive has no system fallback, so a host that strips them must supply them by asset name. CJK strings would need a Noto Sans CJK subset; the word blocks use only Latin, Greek and Cyrillic.

## Measurements

These come from the CLI on this Mac. The headless renderer is not a phone, so treat the numbers as indicative.

- `.riv`: **1,629,196 bytes**. About 1.4 MB of that is the two fonts.
- `rive . --bench=600` (scene 1, 390×844 @1x): advance mean 0.032 ms (p95 0.23 ms), render mean 0.060 ms (p95 0.08 ms). That is far under the 16.7 ms budget for 60 fps. No measurement was taken on a real device.
- Objects: main artboard 17,637, Share Card 2,017. Particle and token pools are bounded at 7–13 objects per scene, so nothing scales with a raw count.

## Unsupported or substituted techniques (honest list)

- **Global VM:** uses one shared bound instance rather than Rive's `global` type (see above).
- **Locale formatting:** there is no locale-aware converter, so the file groups digits from the host's `groupSeparator`. Plurals and decimals beyond integers are the adapter's job.
- **Dwell timing:** an `AnimationState` cannot bind its speed, so the dwell timer is a nested artboard whose bindable `speed` scales a 1 s timeline. The timeline writes `screenProgress` and fires `goNext`.
- **State-machine writes:** a state machine can't write a VM number from a timeline, so animated drivers use two-way binds (`_heroReveal` on a hidden node's `x`, `screenProgress` on the Clock driver).
- **Morphs:** shape morphs and "letters stretch along envelopes" use node scale/rotation, keyed vertex-free squash and stretch, TrimPath reveals, text modifiers and `TextFollowPathModifier` (scene 6 ribbons). There are no true path-to-path vertex morphs between different silhouettes.
- **Texture:** the tactile, grainy rendering of the concept image is approximated with flat layered vectors, depth offsets, highlights and a feathered card shadow. No raster grain is used.
- **Audio:** no audio asset is shipped. The sound is opt-in and host-played via `mouthTapped`.

## Remaining limitations

- No `.rev` export yet (needs `rive login`).
- The file has not been opened in the editor or on a device, so frame rate there is unmeasured.
- 320×568 is a scaled (67%) presentation, not a bespoke compact layout.
- With `extreme.json`, the longest copy can sit over illustration in scenes 2, 4 and 5, but never over controls or other copy.
- RTL was not verified (no RTL locale required).
- The keyboard focus ring also shows for pointer users, because Rive cannot tell input modalities apart.
- `screenChanged`'s `screen` payload is bound at fire time, so read `currentScreen`.
- The scene-6 weave is faked with a trimmed overlay segment.
- Plain events are not observable headlessly, so verify them in a host.
