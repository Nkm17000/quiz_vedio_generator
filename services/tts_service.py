import asyncio
import re
from pathlib import Path

import edge_tts
from moviepy.editor import AudioFileClip
from moviepy.audio.fx.all import speedx

from config import SLIDE_DURATION, TEMP_DIR, TTS_RATE, TTS_VOICE, TTS_VOLUME


def english_question(question):
    """Return only the English question text; never include options or Hindi text."""
    if isinstance(question, dict):
        return str(question.get("en", "")).strip()
    return str(question).strip()


def _safe_name(text, index):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:60]
    return f"question_{index}_{slug or 'speech'}.mp3"


async def _synthesize(text, output_file):
    communicate = edge_tts.Communicate(
        text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await communicate.save(str(output_file))


def _fit_to_slide(audio_file):
    """Speed up speech when necessary so it never runs past one slide."""
    clip = AudioFileClip(str(audio_file))
    if clip.duration <= SLIDE_DURATION:
        clip.close()
        return str(audio_file)

    factor = clip.duration / SLIDE_DURATION
    fitted_file = audio_file.with_name(audio_file.stem + "_fit.mp3")
    fitted = clip.fx(speedx, factor=factor)
    fitted.write_audiofile(
        str(fitted_file),
        fps=24000,
        codec="libmp3lame",
        logger=None,
    )
    fitted.close()
    clip.close()
    audio_file.unlink(missing_ok=True)
    fitted_file.rename(audio_file)
    return str(audio_file)


def generate_question_speech(quiz):
    """
    Generate one Indian-English voice track per question.

    The same track is reused on all countdown slides for that question.
    Only the English question is spoken—never the options or Hindi text.
    """
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
