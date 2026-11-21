# Style guide: what the clips should look like

Status: 2026-11-21. Built from 15 reference clips the owner supplied (17 to 115 seconds, 14 of
them 9:16). The references are other creators' work. They are kept out of this repository. This
guide describes patterns, not footage, wording, music or creator marks, and nothing in it may be
copied from a reference.

## Eight families

Each family is a template for the renderer (Phase 3). Length and cut pace are defaults.

| Family | What it looks like | Length | Cuts per minute | Use it for |
| --- | --- | --- | --- | --- |
| F1 Numbered tips | Big number and short title pill ("1. GUNS"), 5 to 7 points, one coloured keyword per caption | 40 to 75 s | 15 to 30 | GTA tips |
| F2 Warning list | Red "NEVER #n" pill at the lower third, captions above it, map or HUD inserts | 40 to 50 s | 20 to 30 | GTA "never do this" |
| F3 Stat cards | Neon cards with numbers (time, money, counts) and a short quote card | 60 to 90 s | 15 to 25 | GTA facts. Every number must be verified |
| F4 HUD and icon inserts | Wanted-star card, route card, icon badges that appear with a caption | 60 to 70 s | 20 to 30 | GTA gameplay tips |
| F5 Mood and mystery | Title card at the top (two lines, one highlighted word), black-and-white grade for tense parts, a single serif word centred for mood edits | 15 to 30 s | 0 to 4 | GTA discovery and mood |
| F6 Keyword punch | One or two words at a time, big and outlined, synced to the action or speech | 60 to 80 s | 20 to 30 | Streamer clips and gameplay |
| F7 Streamer split | Talking head at the top, gameplay at the bottom, short captions with a yellow or green keyword | 60 to 120 s | 1 to 7 | Streamer reactions |
| F8 How-to | UI motion graphics, step counters ("1/4"), a chat-activity graph, mission-style progress | 30 to 60 s | 0 to 10 | Clipz Hub's own tutorials, later |

## Shared rules (all families)

- **Format:** 1080×1920, 30 fps, H.264 High profile, AAC 128 kbps. The references are small
  (576 px wide); our output is larger for better quality on phones.
- **Loudness:** -16 LUFS integrated, true peak no higher than -1 dBTP. The references range from
  -13.7 to -26.6 LUFS, so we normalise every clip.
- **Hook:** the first 1 to 2 seconds show the hook, as a title card or the first caption.
- **Captions:** uppercase, heavy outlined sans, at most five words per beat, one keyword in colour.
  Keep them in the lower-middle third. In F7, keep them off the face.
- **Progress bar:** a thin coloured bar along the bottom edge that fills as the clip plays.
- **Watermark:** our handle only, bottom-left, as the owner's rule says. Campaign clips follow the
  campaign's own watermark rule. Never reuse a creator's mark.
- **End card:** our handle and one short prompt. No copy of any platform's interface.
- **Colour:** dark backgrounds with accent colours (pink, yellow, green, orange). Pick our own
  palette before launch and keep it consistent.
- **Fonts:** heavy, condensed or bold italic sans. Use fonts with an open licence, and check it.

## Rules that come from the business

- **Style only.** No reference footage, music, wording or creator marks are used.
- **Rights.** Only footage we have the right to use. Campaign rules override this guide. Game
  footage has its publisher's terms, so check them before any clip earns money.
- **No AI voice or AI footage** in campaign clips. The originals may use an AI voice, but never
  without saying what is generated.
- **Facts only.** Every tip, warning and number needs a verified source, written into the post
  package. A neutral line is used when nothing is verified (see `docs/PRODUCT.md`).

## Mixing the families

The owner wants GTA motion graphics mixed with streamer clips. Two lanes, one brand:

1. **Streamer lane:** F6 or F7 on a streamer's clip, with our captions, hook and hashtags.
2. **GTA lane:** F1 to F5 on gameplay we have the right to use, with motion graphics.
3. **Mixed:** a streamer clip with an F3 stat card or F4 insert as a middle beat, and an F5 title
   card as the hook.

Each finished clip records its family, its sources and who approved it.
