# Quiz Video Generator

Generates vertical quiz videos with a 3-second countdown, bilingual English + Hindi text, natural Indian-English question narration, background music, countdown ticks, answer sound, and optional Facebook upload.

## Hindi / Devanagari rendering

- The project includes `assets/fonts/NotoSansDevanagari-Regular.ttf`.
- Hindi text always uses the bundled Devanagari font first; it never falls back to a Latin-only font.
- Pillow RAQM shaping is used when available so Devanagari combining marks render correctly.
- English and Hindi explanation text are rendered separately with the correct script font.
- The renderer dynamically fits long questions and explanations so text does not overlap the timer, options, or screen edges.
- Unsupported emoji that could become tofu/square boxes are replaced with plain text labels.
- DejaVu Sans and DejaVu Sans Bold are also bundled so English rendering is independent of runner fonts.

## Voice behavior

- Default voice: `en-IN-NeerjaNeural` (Indian English female)
- Male option: `en-IN-PrabhatNeural`
- Only the English question is narrated.
- Each question is narrated exactly once, at the start of its first countdown slide.
- The narration uses normal human speaking speed and follows the question length.
- A longer question may continue naturally beyond one 3-second slide; it is never artificially accelerated to force it into one second.
- The narration is never repeated on the second/third countdown slide and options are never spoken.
- `TTS_RATE=+0%` is the default natural rate.

## Performance

The video pipeline uses Pillow for slide rendering and FFmpeg directly for slideshow encoding and audio mixing. This removes the wkhtmltoimage/imgkit rendering dependency and avoids MoviePy's frame-by-frame encoding overhead.

FFmpeg is supplied by `imageio-ffmpeg`, so GitHub Actions does not depend on a system-level FFmpeg installation.

GitHub Actions caches both pip downloads and the complete Python virtual environment. Dependencies are installed only when `requirements.txt` changes or the cache is unavailable.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Branding and final CTA

- The source logo is cropped and fitted proportionally into a true circular badge; it is never stretched from its original aspect ratio.
- Every answer slide ends with the centered attribution `By Nitin Mittal Innovations`.
- Every generated video ends with a dedicated 5-second Smart Learning Lab CTA slide containing the page URL.
- Configure the page with `PAGE_URL` in `.env` or as the GitHub Actions secret `PAGE_URL`.
- If `PAGE_URL` is missing or empty, the built-in default is `https://smartlearninglab-react.pages.dev`.
- The same URL is also included in the Facebook post caption.
