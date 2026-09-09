import base64
from pathlib import Path

import imgkit
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.audio.fx.all import audio_loop

from config import (
    ASSETS_DIR,
    FPS,
    IMGKIT_CONFIG,
    SLIDE_DURATION,
    TEMP_DIR,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)
from services.answer_html import answer_html
from services.html_generator import create_html
from services.tts_service import generate_question_speech


def _render_html(html, filename):
    imgkit.from_string(
        html,
        str(filename),
        config=IMGKIT_CONFIG,
        options={
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "enable-local-file-access": "",
        },
    )


def generate_assets(quiz):
    """Render countdown/answer slides and generate question voice tracks."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    images = []

    for index, question in enumerate(quiz):
        for timer in range(SLIDE_DURATION, 0, -1):
            image = TEMP_DIR / f"slide_{index}_{timer}.png"
            _render_html(create_html(question, index, timer), image)
            images.append(str(image))

        answer_image = TEMP_DIR / f"answer_{index}.png"
        _render_html(answer_html(question, index), answer_image)
        images.append(str(answer_image))

    speech_files = generate_question_speech(quiz)
    return images, speech_files


def _add_audio(video, images, speech_files):
    audio_tracks = []

    bg_music = ASSETS_DIR / "bg_music.mp3"
    tick = ASSETS_DIR / "tick.mp3"
    correct = ASSETS_DIR / "correct.mp3"

    if bg_music.exists():
        bg = AudioFileClip(str(bg_music))
        audio_tracks.append(audio_loop(bg, duration=video.duration).volumex(0.15))

    current_time = 0
    for image in images:
        if Path(image).name.startswith("slide_") and tick.exists():
            tick_clip = AudioFileClip(str(tick)).set_start(current_time).volumex(0.45)
            audio_tracks.append(tick_clip)
        current_time += SLIDE_DURATION

    # Speak each question exactly once, at the start of its first countdown slide.
    # A question owns three countdown slides, but its voice track must not repeat.
    current_time = 0
    question_index = 0
    for image in images:
        filename = Path(image).name
        if filename.startswith("slide_") and filename.endswith(f"_{SLIDE_DURATION}.png"):
            speech = speech_files[question_index] if question_index < len(speech_files) else None
            if speech:
                voice = AudioFileClip(speech).set_start(current_time).volumex(1.0)
                audio_tracks.append(voice)
            question_index += 1
        current_time += SLIDE_DURATION

    current_time = 0
    if correct.exists():
        for image in images:
            if Path(image).name.startswith("answer_"):
                answer = AudioFileClip(str(correct)).set_start(current_time).volumex(0.8)
                audio_tracks.append(answer)
            current_time += SLIDE_DURATION

    if not audio_tracks:
        return video

    return video.set_audio(
        CompositeAudioClip(audio_tracks).set_duration(video.duration)
    )


def create_video(images, speech_files, output_file):
    """Create the final vertical quiz video."""
    if not images:
        raise ValueError("No images were generated.")

    clips = [ImageClip(image).set_duration(SLIDE_DURATION) for image in images]
    video = concatenate_videoclips(clips)

    try:
        video = _add_audio(video, images, speech_files)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        video.write_videofile(
            str(output_file),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            logger="bar",
        )
    finally:
        video.close()
        for clip in clips:
            clip.close()


def get_logo_base64():
    logo = ASSETS_DIR / "logo.png"
    with logo.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")
