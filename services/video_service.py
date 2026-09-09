import base64
import subprocess
from pathlib import Path

import imageio_ffmpeg

from config import ASSETS_DIR, FPS, SLIDE_DURATION, TEMP_DIR, VIDEO_HEIGHT, VIDEO_WIDTH
from services.slide_renderer import render_answer, render_question
from services.tts_service import generate_question_speech

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def generate_assets(quiz):
    """Render all slides and create one natural voice track per question."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    images = []

    for index, question in enumerate(quiz):
        for timer in range(SLIDE_DURATION, 0, -1):
            image = TEMP_DIR / f"slide_{index}_{timer}.jpg"
            render_question(question, index, timer, image)
            images.append(str(image))

        answer_image = TEMP_DIR / f"answer_{index}.jpg"
        render_answer(question, index, answer_image)
        images.append(str(answer_image))

    speech_files = generate_question_speech(quiz)
    return images, speech_files


def _run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def _write_concat_file(images):
    concat_file = TEMP_DIR / "slides.txt"
    with concat_file.open("w", encoding="utf-8") as file:
        for image in images:
            file.write(f"file '{Path(image).resolve()}'\n")
            file.write(f"duration {SLIDE_DURATION}\n")
        # concat demuxer needs the final file repeated after a duration entry.
        file.write(f"file '{Path(images[-1]).resolve()}'\n")
    return concat_file


def _build_audio(images, speech_files, output_audio):
    """Build one mixed audio track with FFmpeg.

    Question narration is inserted exactly once, at the first countdown slide.
    TTS is deliberately left at its natural duration/rate; it is never squeezed
    into one second or artificially accelerated to match a slide.
    """
    bg = ASSETS_DIR / "bg_music.mp3"
    tick = ASSETS_DIR / "tick.mp3"
    correct = ASSETS_DIR / "correct.mp3"

    inputs = []
    if bg.exists():
        inputs += ["-stream_loop", "-1", "-i", str(bg)]
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    tick_index = None
    if tick.exists():
        tick_index = len([x for x in inputs if x == "-i"])
        inputs += ["-i", str(tick)]

    correct_index = None
    if correct.exists():
        correct_index = len([x for x in inputs if x == "-i"])
        inputs += ["-i", str(correct)]

    speech_indices = {}
    for q_index, speech in enumerate(speech_files):
        if speech:
            speech_indices[q_index] = len([x for x in inputs if x == "-i"])
            inputs += ["-i", str(speech)]

    total_duration = len(images) * SLIDE_DURATION
    filters = []
    mix_labels = []

    # Background music at low volume.
    filters.append("[0:a]volume=0.15[bg]")
    mix_labels.append("[bg]")

    slide_starts = []
    question_starts = []
    answer_starts = []
    elapsed = 0
    question_index = 0
    for image in images:
        name = Path(image).name
        if name.startswith("slide_"):
            slide_starts.append(elapsed)
            if name.endswith(f"_{SLIDE_DURATION}.jpg"):
                question_starts.append((question_index, elapsed))
                question_index += 1
        elif name.startswith("answer_"):
            answer_starts.append(elapsed)
        elapsed += SLIDE_DURATION

    # Split the reusable tick and correct sounds once, then delay each copy.
    if tick_index is not None and slide_starts:
        labels = [f"[tick{i}]" for i in range(len(slide_starts))]
        filters.append(f"[{tick_index}:a]asplit={len(labels)}" + "".join(labels))
        for i, start in enumerate(slide_starts):
            filters.append(f"[tick{i}]adelay={start * 1000}:all=1,volume=0.45[td{i}]")
            mix_labels.append(f"[td{i}]")

    if correct_index is not None and answer_starts:
        labels = [f"[correct{i}]" for i in range(len(answer_starts))]
        filters.append(f"[{correct_index}:a]asplit={len(labels)}" + "".join(labels))
        for i, start in enumerate(answer_starts):
            filters.append(f"[correct{i}]adelay={start * 1000}:all=1,volume=0.8[cd{i}]")
            mix_labels.append(f"[cd{i}]")

    for q_index, start in question_starts:
        if q_index not in speech_indices:
            continue
        input_index = speech_indices[q_index]
        filters.append(f"[{input_index}:a]adelay={start * 1000}:all=1,volume=1.0[voice{q_index}]")
        mix_labels.append(f"[voice{q_index}]")

    filters.append(
        f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=longest:dropout_transition=0:normalize=0," 
        f"atrim=duration={total_duration},asetpts=N/SR/TB[aout]"
    )

    command = [FFMPEG, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[aout]", "-c:a", "aac", "-b:a", "128k", str(output_audio)]
    _run(command)


def create_video(images, speech_files, output_file):
    """Create the vertical quiz video using FFmpeg for faster encoding."""
    if not images:
        raise ValueError("No images were generated.")

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    concat_file = _write_concat_file(images)
    audio_file = TEMP_DIR / "quiz_audio.m4a"
    silent_video = TEMP_DIR / "quiz_video_silent.mp4"

    _build_audio(images, speech_files, audio_file)

    # FFmpeg is considerably faster than MoviePy for a slideshow of static images.
    _run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={FPS},format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-crf", "28",
        "-movflags", "+faststart",
        str(silent_video),
    ])

    _run([
        FFMPEG, "-y",
        "-i", str(silent_video),
        "-i", str(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_file),
    ])


def get_logo_base64():
    """Backward-compatible helper for older imports."""
    logo = ASSETS_DIR / "logo.png"
    with logo.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")
