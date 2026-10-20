# Build Simmer's ten-screen Rive recap

Create a polished, interactive Wrapped-style **home cooking** recap for the fictional app **Simmer**. This is a motion-design showcase: deliver beautiful advanced animation, sophisticated transitions, and unmistakably original visuals. Build a continuous visual story with ten deliberately composed scenes, not ten copies of a statistic card.

Adapted from [the root prompt template](../../PROMPT_TEMPLATE.md). Read the Rive CLI project's agent instructions before writing RML; inspect the installed CLI documentation and look up unfamiliar Rive types instead of inventing APIs. Keep the live preview running with `rive <project>`. Deliver editable RML/source, a working `.riv`, and a `.rev` that opens in the Rive Editor. This directory is a brief and reference package; the implementation and exports are to be created.

## Product and reference
- **Core action:** Save recipes, cook meals, and explore new ingredients and cuisines.
- **Audience:** Curious home cooks.
- **Personality:** Warm, messy, celebratory.
- **Period:** January 1–December 31, 2026. This is a fictional full-year dataset, including dates after the brief was written; do not present it as measured real activity.
- **Vocabulary:** meals cooked, recipes tried, cuisines explored, new ingredients, favorite recipe cooks, shared meals, cooking days.
- **Reference:** [concept.png](concept.png) shows three illustrative recap screens: screen 2, screen 4, and screen 9. It is an AI-generated visual target, not a functioning UI or an asset to stretch behind the entire experience. Follow this written brief for exact copy, data, ten progress segments, and navigation when the illustration differs.
- **Source image prompt:** [IMAGE_PROMPT.md](IMAGE_PROMPT.md). **Runtime fixture:** [sample-data.json](sample-data.json).
- **Editorial boundaries:** Avoid calorie or diet moralizing, health claims, and treating cuisines as stereotypes. Recipe names are fictional sample data.

## Visual system
- **Palette:** Tomato #E44932, butter #FFEDB0, aubergine #48293D, basil #4D7655.
- **Typography:** Bricolage Grotesque for display; Source Sans 3 for body. These are font choices, not supplied files. Locate permitted font files in the implementation project or obtain appropriately licensed versions, bundle them under `assets/fonts/`, and document filenames and licenses. Provide a legible fallback when unavailable.
- **Art direction:** Risograph cookbook collage, bold flat ingredient cutouts, offset ink layers, handwritten annotation accents and scalloped recipe tickets.
- **Hero motif:** A joyous flat-illustrated pot with dancing vegetables.
- **Composition:** 390 × 844 portrait master artboard; validate 320 × 568, 430 × 932, and a centered portrait presentation on desktop. Keep important content inside responsive safe margins. Use dramatic scale, asymmetry, and changes of visual density, with a stable area for readable copy and controls.
- Create an original wordmark, the motif, persona emblems, and scene illustrations as layered editable Rive vector artwork. Separate foreground, hero, midground, background, and UI. Use restrained raster grain only where necessary; it cannot carry live text or a complete scene.
- Design depth through overlapping shapes, masks, highlights, and parallax. The image's tactile rendering is inspiration; do not require a real 3D renderer or make the animation depend on an opaque flattened image.

## Motion direction: make this unmistakably Simmer
Ingredients tumble in choreographed arcs, steam ribbons morph into lettering, a pot lid anticipates a pop, and a checked tablecloth ripples between scenes.

**Signature transition:** A steam ribbon curls into the next layout, followed by a tablecloth pull that rearranges ingredients.

**Signature interaction:** Tap the pot to trigger a brief lid wobble and ingredient flourish. Keep this optional delight in a distinct hit region so it cannot accidentally trigger story navigation.

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
| `mealsCooked` | number | 156 |
| `recipesTried` | number | 48 |
| `cuisinesExplored` | number | 14 |
| `newIngredients` | number | 32 |
| `repeatRecipeCount` | number | 17 |
| `sharedMeals` | number | 23 |
| `cookingDays` | number | 112 |
| `personaIndex` | number | 0 |
| `personaName` | string | "Flavor Explorer" |
| `personaDescription` | string | "Always room for a new flavor." |
| `personaColor` | string | "#FFEDB0" |
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
| `introHeadline` | string | "Your 2026 on Simmer" |
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
| `screen2Headline` | string | "You made something good." |
| `screen2Support` | string | "A year seasoned your way." |
| `screen2Unit` | string | "meals cooked" |
| `screen3Headline` | string | "Fresh pages. Full plates." |
| `screen3Support` | string | "Curiosity was always on the menu." |
| `screen3Unit` | string | "recipes tried" |
| `screen4Headline` | string | "Your kitchen went places." |
| `screen4Support` | string | "New flavors, one recipe at a time." |
| `screen4Unit` | string | "cuisines explored" |
| `screen5Headline` | string | "A pinch of possibility." |
| `screen5Support` | string | "You welcomed new flavors to the shelf." |
| `screen5Unit` | string | "new ingredients" |
| `screen6Headline` | string | "Worth making again." |
| `screen6Support` | string | "Your most-cooked recipe: lemon orzo." |
| `screen6Unit` | string | "favorite recipe cooks" |
| `screen7Headline` | string | "There was room at your table." |
| `screen7Support` | string | "Good food found good company." |
| `screen7Unit` | string | "shared meals" |
| `screen8Headline` | string | "A delicious kind of rhythm." |
| `screen8Support` | string | "From quick lunches to slow Sundays." |
| `screen8Unit` | string | "cooking days" |
| `favoriteRecipeName` | string | "Lemon orzo" |

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
Bound greeting with `userName`, `year`, and `periodLabel`; headline “Your 2026 on Simmer.” Reveal the wordmark through the hero motif: a joyous flat-illustrated pot with dancing vegetables. Establish the persistent visual object that will carry the story. The entrance should feel like opening this app's world.

### 2. Meals cooked
- Hero binding: `mealsCooked` (fixture: **156 meals cooked**).
- Headline: “You made something good.”
- Supporting line: “A year seasoned your way.”
- Choreography: Ingredient cutouts drop into a pot in three timed waves. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 3. Recipes tried
- Hero binding: `recipesTried` (fixture: **48 recipes tried**).
- Headline: “Fresh pages. Full plates.”
- Supporting line: “Curiosity was always on the menu.”
- Choreography: Recipe cards flip like a handmade cookbook. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 4. Cuisines explored
- Hero binding: `cuisinesExplored` (fixture: **14 cuisines explored**).
- Headline: “Your kitchen went places.”
- Supporting line: “New flavors, one recipe at a time.”
- Choreography: Four imaginary ingredient arrangements spiral around a plate. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 5. New ingredients
- Hero binding: `newIngredients` (fixture: **32 new ingredients**).
- Headline: “A pinch of possibility.”
- Supporting line: “You welcomed new flavors to the shelf.”
- Choreography: Spice jars hop onto an uneven illustrated shelf. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 6. Favorite recipe cooks
- Hero binding: `repeatRecipeCount` (fixture: **17 favorite recipe cooks**).
- Headline: “Worth making again.”
- Supporting line: “Your most-cooked recipe: lemon orzo.”
- Choreography: An orzo bowl spins into a scalloped recipe medallion. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 7. Shared meals
- Hero binding: `sharedMeals` (fixture: **23 shared meals**).
- Headline: “There was room at your table.”
- Supporting line: “Good food found good company.”
- Choreography: Plates expand outward into a welcoming table setting. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 8. Cooking days
- Hero binding: `cookingDays` (fixture: **112 cooking days**).
- Headline: “A delicious kind of rhythm.”
- Supporting line: “From quick lunches to slow Sundays.”
- Choreography: Steam loops stitch together a loose calendar. Give this screen its own composition, silhouette, staging, and visual payoff. Keep the number unobstructed.
- Reuse the persistent brand motif for the exit, transforming it into the next scene rather than just sliding the whole screen.

### 9. Persona reveal
Build anticipation through the motif, then reveal the bound title, emblem, and one-line description. This should be the emotional high point, with a unique silhouette and choreography for **every** persona; changing only a label is insufficient. Persona selection is provided at runtime, not invented from arbitrary thresholds.

| Index | Persona | Emblem | Accent | Supporting line |
|---|---|---|---|---|
| 0 | Flavor Explorer | dancing spice pot | #FFEDB0 | Always room for a new flavor. |
| 1 | Comfort Cook | steaming bowl | #48293D | You make familiar things feel special. |
| 2 | Batch Wizard | stacked meal tins | #4D7655 | You turn a little planning into good meals. |
| 3 | Weekend Baker | sunburst oven mitt | #E44932 | You make time for something warm from the oven. |

### 10. Summary and sharing
Assemble a collectible composition using the app's motif, wordmark, year, persona, and these five existing properties: `mealsCooked`, `recipesTried`, `cuisinesExplored`, `newIngredients`, `repeatRecipeCount`. Do not duplicate these values into new per-summary user-data fields. Give the share card its own balanced static layout, separate from navigation chrome.

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
1. Editable project/source and documented asset/font licenses; exported `simmer-recap.riv` and `simmer-recap.rev`. Confirm compilation and opening the editor export. Do not rename another format to fake an export.
2. A live host preview connected to UserRecap plus the supplied fixture, a zero/new-user fixture, and an extreme-value/long-copy fixture. Implement runtime data updates and prove the visible numbers change.
3. Capture all ten settled scenes, each persona, reduced-motion states, and the zero/extreme fixtures. Capture at least one intermediate frame per transition; also record a complete motion preview so timing and continuity can be reviewed.
4. Exercise next/back, rapid taps, hold/release, pause/resume, background/foreground, hidden scenes, replay, runtime updates, and full auto-advance. Confirm progress adapts, the sequence reaches summary, and events fire exactly as documented.
5. Verify the share card's contents, privacy flags, stable capture state, and host share event. State clearly if only event wiring is supplied rather than a real platform share integration.
6. Deliver a binding/event contract with names, types, ownership, formatting rules, persona mapping, and every adapter addition. List unsupported techniques, substitutions, performance measurements, and remaining limitations honestly.

The quality bar is a memorable motion piece whose numbers happen to be personalized. Make Simmer's material, pacing, transformations, and personality recognizable even with the text hidden.
