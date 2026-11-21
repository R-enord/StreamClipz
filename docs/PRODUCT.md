# Product: from live stream to posted clip

Status: specification, 2026-11-21. Built from a 20-second example screen recording of the
editor the owner wants: 720×900 (4:5), 60 fps, H.264 video, AAC stereo audio, measured
loudness -16.0 LUFS. The example uses a real streamer's footage. That footage is not stored here.

## The flow the example shows

| Stage | What the example shows | What the system does | Module | Status |
| --- | --- | --- | --- | --- |
| 01 HOOK | The opening segment is chosen as the hook | Ranks candidate moments; the opening line or moment can be the hook | `core` moments (Phase 3) | planned |
| 02 CUT | "Drag edge / find the moment" | Sets in and out points around a moment | moments and review screen (Phases 3 and 4) | planned |
| 03 REFRAME | "Keyframe / punch into the reaction"; a 9:16 crop box moves and eases over time | Tracks the subject and moves a 9:16 crop with smoothing | `render.reframe` (Phase 3) | planned |
| 04 FINISH | "Render / caption, mix, export"; boxed on-screen captions; H.264 | Burns in caption beats, sets the audio loudness, exports MP4 | `render.finish` (Phase 3) | planned |
| 05 SHIP | Not shown in the example. The title says "CLIP IT. SHIP IT." | Post text: hook, caption and hashtags. A person approves. Posting is manual, with a checklist | `core.content` (text rules done); publish (Phase 5) | text rules done |

## Specs taken from the example

- **Caption beats:** four on-screen beats in 20 seconds, each about 5 seconds, each five words or
  fewer, in boxed uppercase text at the bottom. `core.content.plan_caption_beats` builds these.
- **Hook:** the first beat is the hook.
- **Picture:** the example is 4:5. The output is 9:16, 1080×1920, H.264 with AAC audio.
- **Loudness:** -16 LUFS integrated. The example measures exactly -16.0.
- **Reframe:** the crop position changes over time, with keyframes and easing. The example's
  crop moves between about 41% and 57% of the picture width.

## Post text (stage 05)

- **Hook:** one line of eight words or fewer, built from a verified event. If no event is
  verified, a neutral hook is used and flagged. Neutral hooks make no claim about the footage.
- **Caption:** the verified event as a sentence, then any campaign lines, then the credit line.
- **Hashtags:** campaign tags first and never dropped, then the game, the person and the moment's
  labels. Duplicates are removed. The limit per platform defaults to five. We have not verified
  each platform's current limit, so check it before relying on the default.
- **Rules:** every package needs a person's approval. Claim words such as "first" or "exclusive"
  are flagged for checking. AI footage or voices are refused for campaigns that do not allow them.

## Long streams: how they reach us (Phase 2)

Streams are often 8 hours or more. They never travel through chat or the cloud. The flow is:

1. **Scan on your computer.** `python -m core.moments <stream file> --out list.json --previews 5`.
   It reads only the audio, so an hour takes about 15 seconds on the test machine. Eight hours
   should take a few minutes on a laptop (not yet measured there).
2. **Send the small files.** The list (a few kilobytes) and the previews (about 175 KB each for
   30 seconds). The stream itself stays on the laptop.
3. **Plan the edit.** We pick the moments, write hooks, captions and hashtags, and choose a
   style family from `docs/STYLE.md`.
4. **Render on the computer.** Phase 3 adds the renderer. Until then, the cuts are made locally.

The scan is a first version based on loudness. It will need tuning on real streams.

## Source intake (Phase 2)

- Input is a file the owner provides, downloaded or exported from a source they are allowed to use.
- Checks: length, picture size, audio present, loudness, checksum, and a match to a stream record.
- Downloading straight from platforms is **not built**. It waits for a terms review.

## Acceptance test (Phase 3 is done when this passes)

Input: a 20-second clip in 4:5, one verified moment, and four caption phrases.

Output:
- a 9:16 MP4 at 1080×1920, H.264 with AAC audio;
- loudness within 1 LU of -16 LUFS;
- four caption beats, each about 5 seconds;
- a post package with a hook, a caption and hashtags, marked as needing review.

## Not in scope yet

- Automatic posting to platforms. Posting stays manual until a platform's API is approved.
- Downloading streams from platforms, until each source's terms are reviewed.
- AI voices or AI-generated footage in campaign clips.

## Toolkit and licences

The example lists 22 open-source tools for downloading, transcription, tracking, rendering and
editing. Before a company ships a product built on them, check each licence for commercial use,
and whether it requires sharing source code. AI model files can carry their own licence terms.

## Naming

Product name: **Clipz Hub** (chosen by the owner). The repository is still named StreamClipz,
and the screens still say StreamClipz. Renaming the repository and screens is a separate decision.
