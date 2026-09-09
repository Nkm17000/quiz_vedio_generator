# Quiz Video Generator

Generates vertical quiz videos with a 3-second countdown, English + Hindi text, natural Indian-English question narration, background music, countdown ticks, answer sound, and optional Facebook upload.

## Voice behavior

- Default voice: `en-IN-NeerjaNeural` (Indian English female)
- Male option: `en-IN-PrabhatNeural`
- Only the English question is narrated.
- Each question is narrated exactly once, at the start of its first countdown slide.
- The narration uses normal human speaking speed and follows the question length.
- A short question may finish quickly; a longer question is allowed to use more of the countdown time instead of being forced into one second.
- The narration is never repeated on the second/third countdown slide and options are never spoken.
- `TTS_RATE=+0%` is the default natural rate.
- FFmpeg is bundled through `imageio-ffmpeg`, so GitHub Actions does not depend on a system-level FFmpeg installation.

## Performance

The video pipeline uses Pillow for local slide rendering and FFmpeg directly for slideshow encoding and audio mixing. This removes the wkhtmltoimage/imgkit rendering dependency and avoids MoviePy's frame-by-frame encoding overhead.

GitHub Actions caches both pip downloads and the complete Python virtual environment. Dependencies are installed only when `requirements.txt` changes or the cache is unavailable.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

FFmpeg is supplied by the `imageio-ffmpeg` Python package.
