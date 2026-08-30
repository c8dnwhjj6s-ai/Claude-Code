import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "content", "product_catalog.json")
STATE_PATH = os.path.join(BASE_DIR, "content", "state.json")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_catalog():
    return load_json(CATALOG_PATH, [])


def save_catalog(products):
    save_json(CATALOG_PATH, products)


def load_state():
    return load_json(STATE_PATH, {"cursor": 0, "history": []})


def save_state(state):
    save_json(STATE_PATH, state)
