import json
from pathlib import Path

MEMORY_FILE = Path("data/history/history.json")


def load_memory():
    if not MEMORY_FILE.exists():
        return {"counter": 0}

    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        data.setdefault("counter", 0)
        return data
    except (OSError, json.JSONDecodeError):
        return {"counter": 0}


def save_memory(memory):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = MEMORY_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    temp_file.replace(MEMORY_FILE)
