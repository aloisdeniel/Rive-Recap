# Task: Build a 10-screen "Year in Review" (Wrapped-style) experience in Rive

You are working in a Rive CLI project. Before writing any RML, read the agent
instructions that came with this project and look up any Rive type you're unsure
of rather than guessing. Build the scene in RML, keep the live preview running
(`rive <project>`), and produce a `.riv` for the app plus a `.rev` I can open
in the Rive Editor.

## 1. App description
- App name: {{APP_NAME}}
- Category: {{CATEGORY}}  (e.g. fitness, finance, music, language learning,
  productivity, food delivery, social, game)
- What users do in the app (core action): {{CORE_ACTION}}
  (e.g. "log workouts", "save money", "listen to podcasts", "complete lessons")
- Tone & personality: {{TONE}}  (e.g. playful, motivational, premium, calm)
- Audience: {{AUDIENCE}}
- Recap period: {{PERIOD}}  (e.g. Jan 1 – Dec 15, 2026)
- Product vocabulary to reuse (feature names, units, nicknames for users,
  catchphrases): {{APP_VOCABULARY}}
- Topics to avoid or handle carefully: {{SENSITIVE_TOPICS}}
  (e.g. exact spending amounts, body weight, health data)

## 2. Branding & visual elements
- Primary colors (hex): {{PRIMARY_COLORS}}
- Secondary / accent colors (hex): {{ACCENT_COLORS}}
- Background treatment: {{BACKGROUNDS}}  (gradients, textures, per-screen color shifts)
- Typography: {{FONTS}}  (display font for big numbers, body font for captions;
  font files are in {{FONT_PATH}})
- Logo & assets: {{ASSET_LIST_AND_PATHS}}  (logo, mascot, icons, illustrations)
- Iconography / illustration style: {{ILLUSTRATION_STYLE}}
- Motion style: {{MOTION_STYLE}}  (snappy and bouncy / smooth and premium / minimal)
- Do / don't: {{BRAND_RULES}}

## 3. User stats (all values are runtime data, never hardcoded)
Bind all user data to a single global view model named {{VIEW_MODEL_NAME}}
(default: "UserRecap"). Every screen, the progress bar, the persona reveal, and
the share card read from this one view model, so the app sets each user's data
once and the whole experience updates.
- Do not create per-screen or per-artboard view models for user data, and do not
  duplicate a property across screens; screens reference the same global
  properties.
- Nested artboards/components bind to the global view model's properties
  rather than holding their own copies of the values.
- Control properties (auto-advance duration, screen visibility booleans,
  persona selection) live in the same global view model.
- Text, numbers, colors, and images that depend on user data are all bound,
  never baked in.

| Property | Type | Example value | Unit / format | Notes |
|---|---|---|---|---|
| userName | string | {{EX}} | | |
| {{STAT_1_NAME}} | {{TYPE}} | {{EX}} | {{UNIT}} | {{NOTES}} |
| {{STAT_2_NAME}} | {{TYPE}} | {{EX}} | {{UNIT}} | |
| ... | | | | |
| {{STAT_N_NAME}} | {{TYPE}} | {{EX}} | {{UNIT}} | |

Formatting rules: {{FORMATTING}}  (thousands separators, currency symbol and
placement, hours vs minutes, km vs miles, percent precision, ordinal ranks)
Localization: {{LANGUAGES}}  (if more than one, all copy comes from bound
strings, not baked-in text)

## 4. The ten screens
Each screen has one hero stat, one short headline, and one supporting line.
Big numbers count up from 0 to their value when the screen enters.

1. Intro — "Your {{YEAR}} on {{APP_NAME}}" greeting with userName. Logo reveal.
2. {{SCREEN_2_TOPIC}} — stat: {{STAT}} — headline: {{HEADLINE_OR_"write one"}}
3. {{SCREEN_3_TOPIC}} — stat: {{STAT}} — headline: {{...}}
4. {{SCREEN_4_TOPIC}} — stat: {{STAT}} — headline: {{...}}
5. {{SCREEN_5_TOPIC}} — stat: {{STAT}} — headline: {{...}}
6. {{SCREEN_6_TOPIC}} — stat: {{STAT}} — headline: {{...}}
7. {{SCREEN_7_TOPIC}} — stat: {{STAT}} — headline: {{...}}
8. {{SCREEN_8_TOPIC}} — stat: {{STAT}} — headline: {{...}}
9. User persona — reveal an archetype chosen from {{PERSONA_LIST}} via a bound
   enum/number property; each persona has its own color, icon, and one-line
   description.
10. Summary / share card — compact recap of the top 4–5 stats, logo, and a
    "Share" button that fires an event the app listens for.

Suggested topics if I left slots blank (pick what fits the category):
- Volume: total time spent, sessions, items completed/created/consumed
- Favorites: top item, category, feature, or time of day
- Peak moment: best day, biggest achievement, personal record
- Consistency: longest streak, most active month, active days
- Growth: change vs last year or vs the user's first month
- Community: percentile vs other users, people connected with
- Fun equivalence: translate a stat into something tangible
  ("that's 12 marathons", "enough to fill 3 bookshelves")

## 5. Interaction & structure
- One state machine drives the sequence: screen states 1→10.
- Tap right two-thirds = next, tap left third = previous, hold = pause.
- Auto-advance after {{SECONDS_PER_SCREEN}} s per screen (bound number so the
  app can change it).
- Segmented progress bar at the top: 10 segments, the current one fills over the
  screen's duration.
- Enter/exit transitions between every screen, consistent with the motion style.
- Fire events the app can listen to: screenChanged (with index), shareTapped,
  recapFinished.
- Optional screen skipping: a bound boolean per screen so the app can hide
  screens where the user has no meaningful data (the progress bar adapts).

## 6. Edge cases to handle
- Very long userName (truncate or scale down)
- Zero or missing values: show {{ZERO_STATE_COPY}} instead of awkward "0" copy
- New users with little activity: {{LOW_ACTIVITY_BEHAVIOR}}
- Very large numbers (e.g. 1,234,567) still fit the hero slot
- Longest expected translated strings still fit
- Each persona option renders correctly

## 7. Verify before you call it done
- The project compiles with no errors.
- Capture a frame of every screen (1–10) at its settled state and show me.
- Drive the scene with simulated data: my example values, a zero/new user, and
  an extreme user (huge numbers, long name, longest translation). Capture those
  frames too.
- Simulate taps forward, back, pause, and the full auto-advance run to confirm
  the state machine reaches screen 10 and fires recapFinished.
- Report: the list of bound properties and events (names + types) so I can wire
  them up in the app, plus any compromises you made.
