import json
import os

_LIBRARY_PATH = os.path.join(os.path.dirname(__file__), "library.json")


def load_library(category: str = "all") -> list:
    with open(_LIBRARY_PATH, encoding="utf-8") as f:
        attacks = json.load(f)["attacks"]
    if category != "all":
        attacks = [a for a in attacks if a["category"] == category]
    return attacks


__all__ = ["load_library"]
