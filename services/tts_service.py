import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts

from config import SLIDE_DURATION, TEMP_DIR, TTS_RATE, TTS_VOLUME, TTS_VOICE


def english_question(question):
    """Return only the English question text."""
    if isinstance(question, dict):
        return str(question.get("en", "")).strip()
    return str(question).strip()


def _safe_name(text, index):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:60]
    return f"question_{index}_{slug or 'speech'}.mp3"


async def _synthesize(text, output_file):
    voice = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await voice.save(str(output_file))


def _duration_seconds(audio_file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _fit_to_slide(audio_file):
    """Keep the question voice inside one countdown slide using FFmpeg."""
    duration = _duration_seconds(audio_file)
    if duration <= SLIDE_DURATION:
        return str(audio_file)

    # atempo accepts 0.5–2.0 per filter. Chaining keeps this robust for
    # unusually long questions while avoiding MoviePy speedx altogether.
    factor = duration / SLIDE_DURATION
    filters = []
    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0
    filters.append(f"atempo={factor:.6f}")

    fitted_file = audio_file.with_name(f"{audio_file.stem}_fit.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_file),
            "-filter:a",
            ",".join(filters),
            "-t",
            str(SLIDE_DURATION),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(fitted_file),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    audio_file.unlink(missing_ok=True)
    fitted_file.rename(audio_file)
    return str(audio_file)


def generate_question_speech(quiz):
    """Generate one Indian-English voice track for each question."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    speech_files = []

    for index, item in enumerate(quiz):
        text = english_question(item.get("question", ""))
        if not text:
            speech_files.append(None)
            continue

        output_file = TEMP_DIR / _safe_name(text, index)
        asyncio.run(_synthesize(text, output_file))
        speech_files.append(_fit_to_slide(output_file))

    return speech_files
