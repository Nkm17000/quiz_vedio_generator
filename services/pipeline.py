from config import OUTPUT_DIR, OUTPUT_VIDEO, PAGE_URL
from services.facebook_service import upload_video_to_facebook
from services.quiz_service import fetch_quiz
from services.video_service import create_video, generate_assets
from utils.file_utils import cleanup


CAPTION = (
    "📚 Daily practice for serious aspirants\n\n"
    "🎯 SSC | UPSC | Banking | Railway | RAS | IAS\n\n"
    "💬 Drop your answer below\n\n"
    f"🌐 Practice more: {PAGE_URL or 'https://smartlearninglab-react.pages.dev'}\n\n"
    "#sscpreparation #upsc #bankexam #railwayexam "
    "#mocktest #aptitude #reasoning #govtjobs #studyreels"
)


def run_pipeline():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("📥 Fetching quiz...")
    quiz, is_fallback = fetch_quiz()
    if is_fallback:
        print("🚫 Fallback detected. Stopping.")
        return
    if not quiz:
        print("❌ No quiz data received.")
        return

    print(f"✅ {len(quiz)} questions loaded")
    images = []
    speech_files = []

    try:
        print("🖼️ Generating slides and Indian-English question voice...")
        images, speech_files = generate_assets(quiz)

        print("🎬 Creating video...")
        create_video(images, speech_files, OUTPUT_VIDEO)

        if not OUTPUT_VIDEO.exists():
            raise RuntimeError("Video was not created.")

        print("📤 Uploading to Facebook...")
        upload_video_to_facebook(str(OUTPUT_VIDEO), caption=CAPTION)
        print("✅ Done!")
    finally:
        print("🧹 Cleaning temporary files...")
        cleanup(images + speech_files)
