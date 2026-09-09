import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Video
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SLIDE_DURATION = 3
FINAL_SLIDE_DURATION = 5
FPS = 24

# Paths
ASSETS_DIR = BASE_DIR / "assets"
QUIZ_DIR = ASSETS_DIR / "quiz_data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_VIDEO = OUTPUT_DIR / "quiz_video.mp4"
TEMP_DIR = OUTPUT_DIR / "temp"

# Natural Indian-English neural voice.
# Female: en-IN-NeerjaNeural | Male: en-IN-PrabhatNeural
TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")

# Facebook
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")

# Smart Learning Lab website/page shown on the final CTA slide.
PAGE_URL = os.getenv("PAGE_URL", "https://smartlearninglab-react.pages.dev").strip()
