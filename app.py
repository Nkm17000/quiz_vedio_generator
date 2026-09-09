from fastapi import BackgroundTasks, FastAPI

from services.pipeline import run_pipeline

app = FastAPI(title="Quiz Video Generator")


@app.get("/")
def home():
    return {"message": "Quiz Video API is running"}


@app.get("/generate-video")
def generate_video(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"status": "processing started"}


if __name__ == "__main__":
    run_pipeline()
