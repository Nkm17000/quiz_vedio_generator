import json
import random
from pathlib import Path

from config import QUIZ_DIR
from utils.memory import load_memory, save_memory

BATCH_SIZE = 4


def _load_batch(path, start):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data[start : start + BATCH_SIZE]
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read {path.name}: {exc}")
        return []


def fetch_quiz():
    memory = load_memory()
    counter = memory.get("counter", 0)

    files = sorted(QUIZ_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No quiz JSON files found in {QUIZ_DIR}")

    quiz = []
    for path in files:
        quiz.extend(_load_batch(path, counter))

    random.shuffle(quiz)

    memory["counter"] = counter + BATCH_SIZE
    save_memory(memory)

    return quiz, False
