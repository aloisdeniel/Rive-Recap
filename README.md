# Rive-Recap

[Watch the portrait showcase](apps/showcase.mp4) (ten fictional Rive recaps in a 5×2 grid) · [Watch the landscape showcase](apps/showcase-landscape.mp4) (all ten at once)

**An example showcase of ten fictional apps, each with its own Wrapped-style year-in-review built in [Rive](https://rive.app).** It shows how quickly a personalised, animated recap can be generated for your own app: every experience here started from a written brief and was built end to end with the [Rive CLI](https://rive.app/docs) — vector art, ten scenes, motion, personas, a share card and a data-bound runtime model — into a `.riv` that ships straight into an app.

Every app is a different visual world, and every one runs on the same contract: one `UserRecap` view model that your app fills with real numbers.

| App | Domain | Style | Recap |
|---|---|---|---|
| [Sprig](apps/sprig/PROMPT.md) | Houseplant care | Folded-paper botanical dioramas | [portrait](apps/sprig/video.mp4) · [landscape](apps/sprig/video-landscape.mp4) · [project](apps/sprig/rive/) |
| [Crux](apps/crux/PROMPT.md) | Indoor climbing | Brutalist climbing-wall graphics | [portrait](apps/crux/video.mp4) · [landscape](apps/crux/video-landscape.mp4) · [project](apps/crux/rive/) |
| [Simmer](apps/simmer/PROMPT.md) | Home cooking | Risograph cookbook collage | [portrait](apps/simmer/video.mp4) · [landscape](apps/simmer/video-landscape.mp4) · [project](apps/simmer/rive/) |
| [Marginalia](apps/marginalia/PROMPT.md) | Reading journal | Literary book-jacket design | [portrait](apps/marginalia/video.mp4) · [landscape](apps/marginalia/video-landscape.mp4) · [project](apps/marginalia/rive/) |
| [Nocturne](apps/nocturne/PROMPT.md) | Stargazing journal | Observatory instrument graphics | [portrait](apps/nocturne/video.mp4) · [landscape](apps/nocturne/video-landscape.mp4) · [project](apps/nocturne/rive/) |
| [Kiln](apps/kiln/PROMPT.md) | Ceramics studio | Sculptural ceramic silhouettes | [portrait](apps/kiln/video.mp4) · [landscape](apps/kiln/video-landscape.mp4) · [project](apps/kiln/rive/) |
| [Switchyard](apps/switchyard/PROMPT.md) | Public transit | Swiss transit posters | [portrait](apps/switchyard/video.mp4) · [landscape](apps/switchyard/video-landscape.mp4) · [project](apps/switchyard/rive/) |
| [Stash](apps/stash/PROMPT.md) | Personal savings | Retro toy-bank arcade | [portrait](apps/stash/video.mp4) · [landscape](apps/stash/video-landscape.mp4) · [project](apps/stash/rive/) |
| [Parlance](apps/parlance/PROMPT.md) | Language practice | Kinetic typography posters | [portrait](apps/parlance/video.mp4) · [landscape](apps/parlance/video-landscape.mp4) · [project](apps/parlance/rive/) |
| [Patchwork](apps/patchwork/PROMPT.md) | Local volunteering | Quilted textile collage | [portrait](apps/patchwork/video.mp4) · [landscape](apps/patchwork/video-landscape.mp4) · [project](apps/patchwork/rive/) |

All apps, names and statistics are fictional sample data for the year 2026.

## What each recap includes

- Ten scenes: an invitation, seven personalised stats, a persona reveal and a shareable summary.
- One global `UserRecap` view model — every number, string, colour, persona and visibility flag is bound to it, so your app sets the data once.
- A sequencing state machine: tap right/left to navigate, hold to pause, keyboard support, auto-advance, progress segments that adapt to hidden scenes, replay.
- Events for your host app: `screenChanged`, `shareTapped`, `recapFinished`.
- A responsive layout that fills any canvas: a portrait layout below 768 px wide and a landscape layout from 768 px, each reflowing to any size on its side of the breakpoint. The breakpoint is the bound `layoutBreakpoint` property, so your app can move it.
- Four personas with distinct emblems and choreography, reduced-motion variants, and new-user / extreme-value fixtures.

Each project's `README.md` documents its exact binding and event contract, fonts and licences, and known limitations.

## How it was made

1. [PROMPT_TEMPLATE.md](PROMPT_TEMPLATE.md) describes a recap in general terms: scenes, data model, navigation, motion, rendering techniques (GPU Canvas 3D and shaders) and verification.
2. Each app gets a brief adapted from it — `apps/<app>/PROMPT.md` with a concept image, palette and sample data ([gallery](apps/README.md)).
3. An agent reads the brief and builds the project with the Rive CLI: RML scene source, artwork, state machines and data binding, checked with `rive <project> --verify`, `rive inspect` and headless screenshots, then exported with `rive <project> --once`.
4. A refinement pass reviews the first version against the concept, fixes inconsistencies, pushes the motion further and adds 3D or shaders where they earn their place, while keeping every check passing.

To make one for your own app, copy the template, describe your product, metrics and visual direction, and run the same loop.

**Recommended model:** Anthropic Claude Opus 5.5 (at the time of writing, October 2026). All ten recaps in this repository were built with it, one agent per app working in parallel.

## Use a recap in your app (web)

Install the [Rive web runtime](https://rive.app/docs/runtimes/web/web-js):

```bash
npm install @rive-app/canvas
```

Load the `.riv`, let it lay itself out to the canvas, auto-bind its `UserRecap` view model, fill it with your user's data and listen for the recap's events. The canvas can be any size: `Fit.Layout` resizes the artboard to it, and the recap picks its portrait or landscape layout from the width.

```html
<canvas id="recap" style="width: 100vw; height: 100vh"></canvas>
```

```js
import { Rive, Layout, Fit, EventType } from "@rive-app/canvas";

const recap = new Rive({
  src: "/sprig-recap.riv",
  canvas: document.getElementById("recap"),
  stateMachines: "Recap",
  autoplay: true,
  autoBind: true, // binds the artboard's UserRecap view model instance
  layout: new Layout({ fit: Fit.Layout }), // the artboard tracks the canvas size
  onLoad: () => {
    recap.resizeDrawingSurfaceToCanvas();

    // Write your user's stats into the single shared view model.
    const data = recap.viewModelInstance;
    data.string("userName").value = user.firstName;
    data.number("plantsNurtured").value = stats.plantsNurtured;
    data.number("careMoments").value = stats.careMoments;
    data.number("personaIndex").value = stats.personaIndex;
    data.string("personaName").value = personas[stats.personaIndex].name;
    data.boolean("reducedMotion").value =
      matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Observe the state machine's progress.
    data.number("currentScreen").on((event) => console.log("scene", event.data));
  },
});

// Re-layout when the window or the device pixel ratio changes.
const resize = () => recap.resizeDrawingSurfaceToCanvas();
window.addEventListener("resize", resize);
matchMedia(`(resolution: ${devicePixelRatio}dppx)`).addEventListener("change", resize);

recap.on(EventType.RiveEvent, ({ data }) => {
  if (data.name === "shareTapped") shareSummaryCard(); // your capture + share sheet
  if (data.name === "recapFinished") analytics.track("recap_finished");
});
```

Property and state machine names come from each project's `README.md`. To move the portrait/landscape switch, set `data.number("layoutBreakpoint").value` (default 768). Build the `.riv` with `rive apps/<app>/rive --once`; projects that contain Luau scripts and shaders (every app except Parlance) must instead be built signed with `rive apps/<app>/rive --publish`, because web runtimes reject unsigned scripts.

Full documentation: [Rive web runtime](https://rive.app/docs/runtimes/web/web-js) · [Data binding on the web](https://rive.app/docs/runtimes/web/data-binding) · [All runtimes](https://rive.app/docs/runtimes/getting-started)

## Preview and render

```bash
rive apps/simmer/rive                 # live preview window, rebuilds on edit
rive apps/simmer/rive --screenshot=out.png --viewport=1280x720   # one frame at any canvas size
scripts/render-video.py simmer        # apps/simmer/video.webm (portrait, 390x844)
scripts/render-video.py simmer --viewport 1280x720 --output apps/simmer/video-landscape.webm
scripts/merge-videos.py               # apps/showcase.webm: all ten apps in a 5x2 grid
scripts/merge-videos.py --video video-landscape.webm --rows 2 --scale 0.35 --output apps/showcase-landscape.webm
scripts/export-mp4.sh                 # the committed MP4s (apps/<app>/video*.mp4, apps/showcase*.mp4)
scripts/render-all.sh                 # re-render everything above
```

The video scripts drive each recap headlessly with `rive --screenshot` (one run per frame, in parallel, pressing Right every 3.5 s) and encode directly to VP9 WebM with `ffmpeg` (`brew install ffmpeg`, with the `libvpx-vp9` encoder). The merger reads `apps/<app>/video.webm` (or the file named by `--video`) and writes `apps/showcase.webm`; `--rows` (default 2) stacks rows, so both showcases play all ten apps at once in a 5×2 grid. The `--quality` option remains 0–100 (higher is better), mapped to VP9 CRF 63–0. WebM is the local working format and is git-ignored; `scripts/export-mp4.sh` converts every render to the H.264 MP4s committed in the repo. Run `scripts/render-video.py --help` for frame rate, timing and fixture options.

All linked recap videos and the showcases are H.264 MP4 files. Open the video links to play or download them; looping is controlled by your player.
