# Clipz Hub

Clipz Hub turns long streams into short, captioned clips and the post text for each one. You
approve every clip, and you post it yourself. It runs on your computer for now.

The GitHub repository is still named StreamClipz.

## Windows: first-time setup (once)

1. Install Python 3 from python.org. On the first screen, tick **Add python.exe to PATH**.
2. Install ffmpeg (free, from ffmpeg.org). Check it: open Command Prompt and type `ffmpeg -version`.
3. Download the code: `https://github.com/R-enord/StreamClipz/archive/refs/heads/claude/focused-brahmagupta-22ndjd.zip`
4. Extract the ZIP into `C:\Users\<you>`. Rename the folder it creates to `ClipzHub`.
5. Double-click `start.bat` in ClipzHub. It copies your old login data if there is any, and asks you
   to create a login if there is none.

After that, updates are one double-click: `update.bat`. See [the runbook](docs/RUNBOOK.md).

## Commands

Open a Command Prompt in the ClipzHub folder (click the address bar, type `cmd`, press Enter).

Find moments in a stream, in two-hour parts, with short previews:

```
py -3 -m core.moments "C:\path\to\stream.mkv" --out stream-moments.json --previews 5 --chunk-hours 2
```

Make a clip with captions (times are in seconds, so 3600 is one hour):

```
py -3 -m core.render "C:\path\to\stream.mkv" --start 3600 --end 3608 --style keyword_punch --captions "TRAILER. *GAME*." "CLIP THAT." --out clip1.mp4
```

Styles: `keyword_punch` (big outlined words, the key word in colour) and `streamer_split`
(the face on top, gameplay below). For the split, `--face X Y W H` sets where the face is,
as fractions of the picture from 0 to 1, for example `--face 0 0 0.3 0.3`.
A word wrapped in `*stars*` is shown in colour.

## Docs

- [Runbook](docs/RUNBOOK.md): start, update, back up, restore.
- [Product](docs/PRODUCT.md): from stream to posted clip.
- [Style guide](docs/STYLE.md): the styles, in plain words.
- [Workflow](docs/WORKFLOW.md): campaigns, streams and two-hour parts.
- [Architecture](docs/ARCHITECTURE.md): phases and what is done.
- [Decisions](docs/decisions/): why we chose what we chose.

## For developers

```
python -m pip install -r requirements-dev.txt
ruff check .
python -m pytest -q
```

The tests generate their own media. No real footage is stored in this repository.
