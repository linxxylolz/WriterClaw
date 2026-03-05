import json
import os
from typing import Any, Dict

COMMUNITY_DATA_FILE = "community_data.json"


def load_community_data() -> Dict[str, Any]:
    if os.path.exists(COMMUNITY_DATA_FILE):
        try:
            with open(COMMUNITY_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "posts": [],
        "templates": [],
        "commissions": []
    }


def save_community_data(data: Dict[str, Any]) -> None:
    with open(COMMUNITY_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def initialize_community_storage() -> Dict[str, Any]:
    data = load_community_data()
    data.setdefault("posts", [])
    data.setdefault("templates", [])
    data.setdefault("commissions", [])
    return data
