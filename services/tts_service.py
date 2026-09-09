import asyncio
import re
from pathlib import Path

import edge_tts

from config import TEMP_DIR, TTS_RATE, TTS_VOLUME, TTS_VOICE


def english_question(question):
    """Return only the English question text."""
    if isinstance(question, dict):
        return str(question.get("en", "")).strip()
    return str(question).strip()


def _safe_name(text, index):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:50]
    return TEMP_DIR / f"question_{index}_{slug or 'speech'}.mp3"


async def _synthesize(text, output_file):
    # Keep the neural voice natural. Do not time-compress the finished audio.
    voice = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await voice.save(str(output_file))


def generate_question_speech(quiz):
    """Generate exactly one natural Indian-English track per question.

    Audio is not squeezed into one second or artificially sped up. The video
    starts each track once at the beginning of that question's countdown.
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    speech_files = []

    async def generate_all():
        tasks = []
        outputs = []
        for index, item in enumerate(quiz):
            text = english_question(item.get("question", ""))
            if not text:
                outputs.append(None)
                continue
            output_file = _safe_name(text, index)
            outputs.append(output_file)
            tasks.append(_synthesize(text, output_file))

        if tasks:
            await asyncio.gather(*tasks)
        return outputs

    return [str(path) if path else None for path in asyncio.run(generate_all())]
