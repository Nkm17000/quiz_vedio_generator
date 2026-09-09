import requests

from config import FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID


def upload_video_to_facebook(video_path, caption="Daily Quiz 🎯"):
    if not FACEBOOK_ACCESS_TOKEN:
        raise ValueError("FACEBOOK_ACCESS_TOKEN is missing.")
    if not FACEBOOK_PAGE_ID:
        raise ValueError("FACEBOOK_PAGE_ID is missing.")

    url = f"https://graph-video.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/videos"

    with open(video_path, "rb") as video_file:
        response = requests.post(
            url,
            files={"source": video_file},
            data={
                "description": caption,
                "access_token": FACEBOOK_ACCESS_TOKEN,
            },
            timeout=300,
        )

    response.raise_for_status()
    result = response.json()
    print("📤 Facebook upload:", result)
    return result
