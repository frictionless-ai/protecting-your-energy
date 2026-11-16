---
name: video-to-gif
description: Convert video files (webm, mp4, mov, mkv, avi, gif) to high-quality animated GIFs with ffmpeg. Use when the user asks to turn a screen recording or video clip into a GIF, or mentions webm-to-gif / mp4-to-gif conversion.
---

You convert video files into good-looking animated GIFs using ffmpeg.

## Requirements

- `ffmpeg` and `ffprobe` must be on PATH. If missing, tell the user how to install them and stop.

## Method (two-pass palette)

Always use a generated palette so colors stay clean:

1. Generate palette:

```
ffmpeg -y -i INPUT -vf "fps=FPS,scale=WIDTH:-1:flags=lanczos,palettegen=stats_mode=diff" PALETTE.png
```

2. Render the GIF with the palette:

```
ffmpeg -y -i INPUT -i PALETTE.png -lavfi "fps=FPS,scale=WIDTH:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3" OUTPUT.gif
```

3. Delete the temp palette.

## Defaults

- `FPS=15` — good balance of smoothness and size. Drop to 10 for smaller files, raise to 24 for smooth motion.
- `WIDTH=800` — scales height automatically (`-1`). Use the source width if it is smaller.
- Output next to the source with the same stem and `.gif`.

## Intake (only ask if unclear)

- Which file(s)
- Target width or fps if the user cares about size vs quality
- Whether to trim (`-ss START -to END` on the input) or loop count (`-loop 0` = infinite, the default)

## After converting

Report the output path and file size. If the GIF is large (>10 MB), suggest lower fps or width and offer to re-run.

## Do not

- Re-encode without a palette (produces banded, ugly GIFs).
- Overwrite the source file.
