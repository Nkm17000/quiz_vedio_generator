import os
from pathlib import Path

import imgkit
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Video
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SLIDE_DURATION = 3
FPS = 24

# Paths
ASSETS_DIR = BASE_DIR / "assets"
QUIZ_DIR = ASSETS_DIR / "quiz_data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_VIDEO = OUTPUT_DIR / "quiz_video.mp4"
TEMP_DIR = OUTPUT_DIR / "temp"

# Rendering
WKHTML_PATH = os.getenv("WKHTMLTOIMAGE_PATH", "/usr/bin/wkhtmltoimage")
try:
    IMGKIT_CONFIG = imgkit.config(wkhtmltoimage=WKHTML_PATH)
except Exception:
    IMGKIT_CONFIG = None

# Voice: Indian English only.
# Female: en-IN-NeerjaNeural
# Male:   en-IN-PrabhatNeural
TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")
TTS_RATE = os.getenv("TTS_RATE", "+10%")
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")

# Facebook
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
