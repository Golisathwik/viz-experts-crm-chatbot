import json
from pathlib import Path


CONFIG_PATH = Path(__file__).parent / "ai_config.json"


def load_ai_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)