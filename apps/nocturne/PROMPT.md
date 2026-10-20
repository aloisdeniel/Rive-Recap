# Build Nocturne's ten-screen Rive recap

Create a polished, interactive Wrapped-style **stargazing journal** recap for the fictional app **Nocturne**. This is a motion-design showcase: deliver beautiful advanced animation, sophisticated transitions, and unmistakably original visuals. Build a continuous visual story with ten deliberately composed scenes, not ten copies of a statistic card.

Adapted from [the root prompt template](../../PROMPT_TEMPLATE.md). Read the Rive CLI project's agent instructions before writing RML; inspect the installed CLI documentation and look up unfamiliar Rive types instead of inventing APIs. Keep the live preview running with `rive <project>`. Deliver editable RML/source, a working `.riv`, and a `.rev` that opens in the Rive Editor. This directory is a brief and reference package; the implementation and exports are to be created.

## Product and reference
- **Core action:** Log observation nights, celestial objects, and astronomy sketches.
- **Audience:** Amateur observers and sky-curious beginners.
- **Personality:** Precise, spacious, full of wonder.
- **Period:** January 1–December 31, 2026. This is a fictional full-year dataset, including dates after the brief was written; do not present it as measured real activity.
- **Vocabulary:** nights outside, objects logged, hours observing, constellations logged, meteors spotted, lunar sessions, sky sketches.
- **Reference:** [concept.png](concept.png) shows three illustrative recap screens: screen 2, screen 4, and screen 9. It is an AI-generated visual target, not a functioning UI or an asset to stretch behind the entire experience. Follow this written brief for exact copy, data, ten progress segments, and navigation when the illustration differs.
- **Source image prompt:** [IMAGE_PROMPT.md](IMAGE_PROMPT.md). **Runtime fixture:** [sample-data.json](sample-data.json).
- **Editorial boundaries:** Never expose precise observing locations or claim live astronomical accuracy; all sky layouts are clearly decorative.

## Visual system
- **Palette:** Midnight #081526, ice #BCE4E8, electric blue #608BFF, amber #F7BE62.
- **Typography:** Space Grotesk for display; IBM Plex Mono for coordinates. These are font choices, not supplied files. Locate permitted font files in the implementation project or obtain appropriately licensed versions, bundle them under `assets/fonts/`, and document filenames and licenses. Provide a legible fallback when unavailable.
- **Art direction:** Observatory instrument graphics, hairline reticles, expansive negative space, luminous celestial disks, carefully sparse stars.
- **Hero motif:** A luminous illustrated celestial disk framed by an observatory reticle.
- **Composition:** 390 × 844 portrait master artboard; validate 320 × 568, 430 × 932, and a centered portrait presentation on desktop. Keep important content inside responsive safe margins. Use dramatic scale, asymmetry, and changes of visual density, with a stable area for readable copy and controls.
- Create an original wordmark, the motif, persona emblems, and scene illustrations as layered editable Rive vector artwork. Separate foreground, hero, midground, background, and UI. Use restrained raster grain only where necessary; it cannot carry live text or a complete scene.
- Design depth through overlapping shapes, masks, highlights, and parallax. The image's tactile rendering is inspiration; do not require a real 3D renderer or make the animation depend on an opaque flattened image.

## Motion direction: make this unmistakably Nocturne
An aperture iris opens, reticles align with damped precision, star trails draw through masks, and an orbital arc becomes a data ring. Light moves slowly against crisp instrument ticks.

**Signature transition:** The observatory aperture closes to a small pupil then opens on a different scale of sky.

**Signature interaction:** Dragging a bounded reticle reveals decorative stars; it is an abstract illustration rather than a live sky map. Keep this optional delight in a distinct hit region so it cannot accidentally trigger story navigation.

Use anticipation, follow-through, secondary motion, carefully staggered reveals, and custom easing appropriate to this material. Include at least three distinctly staged hero sequences, two continuity transitions that carry an object between scenes, a special persona reveal, and an intentional summary assembly. Keyed deformations, path reveals, clipping masks, nested artboards, and state-machine interactions are candidates; verify support in the installed Rive tooling before choosing an implementation. If a technique is unsupported, reproduce the intended result with supported primitives and explain the compromise.

Give each scene a clear motion score:
1. 0–200 ms: orient the eye through one anticipatory gesture.
2. 200–1,200 ms: reveal the hero and animate its numeric value from zero to the current bound value. Synchronize the counting rhythm with the illustration; do not let placeholder digits flash.
3. 1,200–1,800 ms: resolve the headline/support and secondary details.
4. Remaining dwell: allow reading, with only a restrained idle loop.
5. On navigation: a 450–850 ms authored handoff into the next scene. Reverse navigation gets a deliberately designed reverse or alternate transition.

These are direction ranges, not a requirement to delay input. Navigation stays responsive. Let the host set dwell time; start its timer after the entrance settles. Pause freezes the timer and decorative motion, preserves progress, and resumes from the same point. Rapid navigation must settle cleanly into the final requested scene without duplicate events, orphaned layers, or stacked animations. Loop seams must be invisible. Avoid constant shake, generic confetti, aggressive zoom, and uniform fade/slide transitions. Reduced motion uses immediate final values, static hero compositions, and short opacity changes without camera movement.

## Single global runtime view model
Use exactly one global user-data view model named **UserRecap**. Bind all scenes, nested components, summary values, progress, and persona visuals to this shared instance. Do not create per-screen copies of user statistics. Examples below are fixture values only; do not bake them into text, animation endpoints, or geometry.

The following is a logical integration schema. Map these types to supported Rive types after checking the project's toolchain. Color strings in the JSON fixture are adapted to native color properties where supported; document any adapter. A host adapter may format or localize values, but must write into the same global model. Internal animation playheads may be local; user data must remain global.

| Property | Type | Example / default |
|---|---|---|
| `userName` | string | "Alex" |
| `year` | number | 2026 |
| `periodLabel` | string | "January 1–December 31, 2026" |
| `locale` | string | "en-GB" |
| `observationNights` | number | 47 |
| `objectsLogged` | number | 128 |
| `observationHours` | number | 93 |
| `constellationsLogged` | number | 31 |
| `meteorSightings` | number | 64 |
| `moonSessions` | number | 18 |
| `sketchesMade` | number | 22 |
| `personaIndex` | number | 0 |
| `personaName` | string | "Deep Sky Dreamer" |
| `personaDescription` | string | "Wonder beyond the familiar." |
| `personaColor` | string | "#BCE4E8" |
| `autoAdvanceSeconds` | number | 7 |
| `autoAdvanceEnabled` | boolean | true |
| `isPaused` | boolean | false |
| `reducedMotion` | boolean | false |
| `soundEnabled` | boolean | false |
| `currentScreen` | number | 1 |
| `screenProgress` | number | 0 |
| `shareIncludeName` | boolean | false |
| `shareIncludeSensitiveValues` | boolean | false |
| `continueLabel` | string | "Continue" |
| `previousLabel` | string | "Previous" |
| `pauseLabel` | string | "Pause" |
| `playLabel` | string | "Play" |
| `shareLabel` | string | "Share" |
| `replayLabel` | string | "Replay" |
| `introHeadline` | string | "Your 2026 on Nocturne" |
| `introSupport` | string | "A year, uniquely yours." |
| `summaryHeadline` | string | "A little year. A lot of you." |
| `summarySupport` | string | "Take a piece of your year with you." |
| `emptyHeadline` | string | "Every story starts somewhere." |
| `emptySupport` | string | "Your next chapter is waiting." |
| `personaLabel` | string | "Your personal style" |
| `showScreen1` | boolean | true |
| `showScreen2` | boolean | true |
| `showScreen3` | boolean | true |
| `showScreen4` | boolean | true |
| `showScreen5` | boolean | true |
| `showScreen6` | boolean | true |
| `showScreen7` | boolean | true |
| `showScreen8` | boolean | true |
| `showScreen9` | boolean | true |
| `showScreen10` | boolean | true |
| `screen2Headline` | string | "You looked up." |
| `screen2Support` | string | "And found a little more wonder." |
| `screen2Unit` | string | "nights outside" |
| `screen3Headline` | string | "A sky full of discoveries." |
| `screen3Support` | string | "Your observation journal kept expanding." |
| `screen3Unit` | string | "objects logged" |
| `screen4Headline` | string | "Time under the stars." |
| `screen4Support` | string | "A different kind of screen time." |
| `screen4Unit` | string | "hours observing" |
| `screen5Headline` | string | "Patterns you came to know." |
| `screen5Support` | string | "A personal atlas, night by night." |
| `screen5Unit` | string | "constellations logged" |
| `screen6Headline` | string | "Gone in a bright moment." |
| `screen6Support` | string | "You were there to notice." |
| `screen6Unit` | string | "meteors spotted" |
| `screen7Headline` | string | "An old friend, new details." |
| `screen7Support` | string | "You returned to the moon." |
| `screen7Unit` | string | "lunar sessions" |
| `screen8Headline` | string | "You kept a piece of the night." |
| `screen8Support` | string | "Observations became your own marks." |
| `screen8Unit` | string | "sky sketches" |

- Each `showScreenN` controls that scene's eligibility. Hide absent metrics, not genuine zeros automatically. Keep intro and summary available; validate invalid visibility input to a safe intro/summary path.
- `currentScreen` is the canonical one-based scene ID; `screenProgress` is normalized 0–1 for the current dwell. State-machine logic writes these back; consumers read the same values.
- `personaIndex` selects a row below. When it changes, one host adapter or supported derived-binding mechanism updates `personaName`, `personaDescription`, and `personaColor` in UserRecap atomically. Do not let the label, palette, and emblem disagree. Unknown indices fall back to row 0.
- All user-dependent text and colors are bound. Localized headings, supports, units, button labels, and empty-state copy are also model strings. In supplied examples that interpolate a recipe, goal, year, or name, assemble the localized sentence from runtime fields; never retain the sample name in production.
- Use locale-aware separators and pluralization; counts are integers, mass has at most one decimal, and money uses the bound currency code with appropriate precision. Large values may use a localized compact visual label with the full exact value in accessible text. Never imply that rounded display counts are the raw data.
- If the runtime lacks a formatting/converter feature, do it in a documented host adapter. Store each formatted field once in UserRecap and reuse it everywhere. Add any required localized or accessibility strings to the documented binding contract.
- Persona title and hero animation read the same bound values on first entry, back navigation, and replay. Updates received mid-transition must not leave mixed old/new data on screen.

## Ten-screen storyboard
Each metric scene has one hero value, one short headline, and one supporting line. Intro, persona, and summary are intentional exceptions to the one-stat composition. Respect the settled visual hierarchy in the reference, then extend its art direction into all ten screens.

### 1. Invitation
Bound greeting with `userName`, `year`, and `periodLabel`; headline “Your 2026 on Nocturne.” Reveal the wordmark through the hero motif: a luminous illustrated celestial disk framed by an observatory reticle. Establish the persistent visual object that will carry the story. The entrance should feel like opening this app's world.

### 2. Nights outside
- Hero binding: `observationNights` (fixture: **47 nights outside**).
- Headline: “You looked up.”
- Supporting line: “And found a little more wonder.”
- Choreography: An iris opens on a sparse field of stars. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 3. Objects logged
- Hero binding: `objectsLogged` (fixture: **128 objects logged**).
- Headline: “A sky full of discoveries.”
- Supporting line: “Your observation journal kept expanding.”
- Choreography: Luminous markers illuminate around an abstract instrument ring. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 4. Hours observing
- Hero binding: `observationHours` (fixture: **93 hours observing**).
- Headline: “Time under the stars.”
- Supporting line: “A different kind of screen time.”
- Choreography: A long-exposure arc traces around an empty midnight center. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 5. Constellations logged
- Hero binding: `constellationsLogged` (fixture: **31 constellations logged**).
- Headline: “Patterns you came to know.”
- Supporting line: “A personal atlas, night by night.”
- Choreography: Abstract points connect through staggered thin lines. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 6. Meteors spotted
- Hero binding: `meteorSightings` (fixture: **64 meteors spotted**).
- Headline: “Gone in a bright moment.”
- Supporting line: “You were there to notice.”
- Choreography: A small bounded pool of meteor trails crosses the frame. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 7. Lunar sessions
- Hero binding: `moonSessions` (fixture: **18 lunar sessions**).
- Headline: “An old friend, new details.”
- Supporting line: “You returned to the moon.”
- Choreography: A graphic moon disk reveals successive masked illumination. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 8. Sky sketches
- Hero binding: `sketchesMade` (fixture: **22 sky sketches**).
- Headline: “You kept a piece of the night.”
- Supporting line: “Observations became your own marks.”
- Choreography: Fine strokes trace an invented nebula study. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 9. Persona reveal
Build anticipation through the motif, then reveal the bound title, emblem, and one-line description. This should be the emotional high point, with a unique silhouette and choreography for **every** persona; changing only a label is insufficient. Persona selection is provided at runtime, not invented from arbitrary thresholds.

| Index | Persona | Emblem | Accent | Supporting line |
|---|---|---|---|---|
| 0 | Deep Sky Dreamer | nested nebula aperture | #BCE4E8 | Wonder beyond the familiar. |
| 1 | Lunar Archivist | lunar disk | #608BFF | You notice something new in an old companion. |
| 2 | Planet Tracker | orbital reticle | #F7BE62 | You enjoy following a moving mystery. |
| 3 | Meteor Watcher | meteor arc | #081526 | You are ready for a fleeting bright moment. |

### 10. Summary and sharing
Assemble a collectible composition using the app's motif, wordmark, year, persona, and these five existing properties: `observationNights`, `objectsLogged`, `observationHours`, `constellationsLogged`, `meteorSightings`. Do not duplicate these values into new per-summary user-data fields. Give the share card its own balanced static layout, separate from navigation chrome.

Provide Share and Replay actions. Share emits `shareTapped`; the host owns actual capture and the platform share sheet. Default to hiding the user's name and sensitive data according to the model flags. Exclude private location, recordings, annotations, beneficiary information, or other sensitive raw content; the public card uses aggregate sample stats and the persona. Snapshot the card after it has settled, without progress bars or controls. If the full experience pauses for sharing, restore its previous pause state when the host returns.

## Sequence and controls
- A single sequencing state machine drives scenes 1–10, skipping hidden scenes in both directions. Build a derived visible-scene list and render exactly that many progress segments. Canonical scene IDs stay stable even when segment positions change.
- Right two-thirds of the non-control canvas advances; left third goes back. Hold pauses; releasing a hold must not also fire a tap. Provide visible previous/continue and pause/play controls as accessible alternatives. Decorative hit regions do not steal those controls.
- Pointer, keyboard, and touch work: Left/Right navigate, Space pauses, Enter activates a focused button, and focus is visible. Have the host provide semantic labels and screen announcements if the runtime surface needs them.
- Auto-advance defaults to 7 seconds of settled dwell, bound through `autoAdvanceSeconds`; disable it with `autoAdvanceEnabled`. Clamp unsafe durations to a readable minimum. Never advance while paused, sharing, or the host app is backgrounded.
- The final scene stays visible for sharing. Emit `recapFinished` once when it first settles; no endless auto-loop. Replay resets progress and the completion latch.
- Events: `screenChanged` with canonical numeric index, `shareTapped`, and `recapFinished`. If event payloads are unavailable, emit the event and let the host read `currentScreen`; document that supported integration rather than claiming nonexistent payload support.
- Export one maintainable scene hierarchy with reusable UI and motif components. Components reference the global data instance; they never own duplicate stat values.

## Edge cases and accessibility
- Zero/new user: “Every story starts somewhere.” Use a small, complete motif and an invitation to continue. With no eligible stats, show intro → welcoming summary; do not assign a boastful persona without evidence.
- Missing data: use visibility flags supplied by the host. Zero is a valid number; unknown is not zero. Empty or unknown persona information hides the persona scene or uses a neutral fallback explicitly marked as such.
- Clamp invalid negative counts and non-finite values in the adapter; preserve valid decimals such as kg or money. Test exceptionally large values, long names, and long unit labels.
- Long name: wrap or truncate at a sensible boundary; do not shrink all UI text to fit. Support English plus an expansion test of at least 40% longer copy. Include right-to-left verification if a supported target locale requires it.
- Reduced motion retains the full story and all controls. Maintain readable contrast, 44 × 44 minimum control targets, and an accessible host text equivalent for important data. No flashing.
- Sound is off by default and optional; the entire experience must work silently. Do not require haptics or audio to understand progress.
- Budget render complexity: use bounded particle pools and few large masks, suspend offscreen loops, and avoid one graphical object per raw count. Record actual frame-rate and file-size measurements on the documented test device.

## Deliver and verify
1. Editable project/source and documented asset/font licenses; exported `nocturne-recap.riv` and `nocturne-recap.rev`. Confirm compilation and opening the editor export. Do not rename another format to fake an export.
2. A live host preview connected to UserRecap plus the supplied fixture, a zero/new-user fixture, and an extreme-value/long-copy fixture. Implement runtime data updates and prove the visible numbers change.
3. Capture all ten settled scenes, each persona, reduced-motion states, and the zero/extreme fixtures. Capture at least one intermediate frame per transition; also record a complete motion preview so timing and continuity can be reviewed.
4. Exercise next/back, rapid taps, hold/release, pause/resume, background/foreground, hidden scenes, replay, runtime updates, and full auto-advance. Confirm progress adapts, the sequence reaches summary, and events fire exactly as documented.
5. Verify the share card's contents, privacy flags, stable capture state, and host share event. State clearly if only event wiring is supplied rather than a real platform share integration.
6. Deliver a binding/event contract with names, types, ownership, formatting rules, persona mapping, and every adapter addition. List unsupported techniques, substitutions, performance measurements, and remaining limitations honestly.

The quality bar is a memorable motion piece whose numbers happen to be personalized. Make Nocturne's material, pacing, transformations, and personality recognizable even with the text hidden.
