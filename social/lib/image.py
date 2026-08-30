"""Generate a marketing visual for a product using the OpenAI Images API.

We deliberately do NOT try to recreate the exact scraped product photo.
gpt-image-1 cannot reproduce a specific real-world unit faithfully, and
presenting a fabricated "photo" of the literal SKU risks misleading
customers about what they'd actually receive. Instead we generate a
generic, on-brand scene for the product's category (indoor lobby,
outdoor storefront, stadium, etc.) with no readable text/logos, and let
the tweet text + the linked product page carry the actual specifics.
"""
import base64
import os

import requests

API_URL = "https://api.openai.com/v1/images/generations"
REQUEST_TIMEOUT = 120

_SCENE_RULES = [
    (("屋外", "outdoor"), "on the exterior wall of a modern city building, street-level, daytime"),
    (("スタジアム", "アリーナ", "stadium"), "inside a large sports stadium, overlooking the field"),
    (("駅", "空港", "transit"), "inside a busy train station concourse"),
    (("店舗", "retail", "モール"), "inside a bright modern retail store"),
    (("天吊り", "吊り"), "suspended from the ceiling of a modern commercial interior"),
    (("スタンド",), "on a freestanding floor display in a modern lobby"),
]
_DEFAULT_SCENE = "in a modern commercial interior space"


def _pick_scene(name, breadcrumb):
    haystack = name + " " + " ".join(breadcrumb)
    for keywords, scene in _SCENE_RULES:
        if any(k in haystack for k in keywords):
            return scene
    return _DEFAULT_SCENE


def build_prompt(product):
    scene = _pick_scene(product["name"], product.get("breadcrumb", []))
    return (
        "Professional product marketing photograph of a sleek digital signage "
        f"LED/LCD display screen, mounted {scene}. The screen shows vibrant, "
        "colorful abstract graphic content (no readable text, no logos, no "
        "brand names, no watermarks). Clean modern architecture, soft "
        "professional lighting, shallow depth of field, high-end commercial "
        "photography style, photorealistic, 4k quality."
    )


def generate_image(product, api_key, out_path, size="1536x1024", model="gpt-image-1"):
    prompt = build_prompt(product)
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "prompt": prompt, "size": size, "n": 1},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()["data"][0]

    if "b64_json" in data:
        image_bytes = base64.b64decode(data["b64_json"])
    else:
        image_bytes = requests.get(data["url"], timeout=REQUEST_TIMEOUT).content

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(image_bytes)
    return out_path, prompt
