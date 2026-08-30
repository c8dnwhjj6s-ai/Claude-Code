"""Ties together: pick a product -> fetch fresh detail -> write copy -> (optionally) generate an image."""
import datetime
import os
import random

from . import copywriting
from . import image as imagegen
from .scraper import fetch_product_detail

DEDUPE_WINDOW = 15
MAX_GENERATION_ATTEMPTS = 20
MAX_STOCK_SKIPS = 8

IMAGE_OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "tmp")


def _pick_in_stock_product(catalog, state):
    """Walk the rotation starting at state['cursor'], skipping sold-out items.

    Returns (product_detail_dict, catalog_entry). Mutates state['cursor'] to
    point at the *next* item after the one we're using.
    """
    if not catalog:
        raise RuntimeError("product_catalog.json is empty - run update_product_catalog.py first")

    n = len(catalog)
    cursor = state.get("cursor", 0) % n
    last_error = None
    for attempt in range(min(MAX_STOCK_SKIPS, n)):
        entry = catalog[cursor]
        try:
            detail = fetch_product_detail(entry["url"])
        except Exception as e:  # noqa: BLE001 - surface after retries are exhausted
            last_error = e
            cursor = (cursor + 1) % n
            continue
        state["cursor"] = (cursor + 1) % n
        if detail["in_stock"]:
            return detail, entry
        cursor = (cursor + 1) % n

    if last_error:
        raise last_error
    raise RuntimeError("no in-stock product found after skipping sold-out items")


def generate_post(config, catalog, state, openai_api_key=None, generate_image=True):
    detail, catalog_entry = _pick_in_stock_product(catalog, state)
    # merge: catalog entry gives us the id, detail gives fresh name/price/desc/stock
    product = {**catalog_entry, **detail}

    history = state.get("history", [])
    recent_texts = {h["text"] for h in history[-DEDUPE_WINDOW:]}

    text = None
    for _ in range(MAX_GENERATION_ATTEMPTS):
        hook_prefix = random.choice(config["hook_prefixes"])
        cta = random.choice(config["ctas"])
        hashtag_line = copywriting.choose_hashtags(product.get("breadcrumb", []), config)
        candidate = copywriting.build_tweet_text(
            product, config, hook_prefix, cta, hashtag_line,
            config.get("max_weighted_length", 260),
        )
        if candidate not in recent_texts:
            text = candidate
            break
    if text is None:
        text = candidate

    post = {
        "product_id": product["id"],
        "product_name": product["name"],
        "product_url": product["url"],
        "text": text,
        "image": None,
        "image_prompt": imagegen.build_prompt(product),
    }

    if generate_image and openai_api_key:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        out_path = os.path.join(IMAGE_OUT_DIR, f"{product['id']}_{timestamp}.png")
        image_path, _prompt = imagegen.generate_image(product, openai_api_key, out_path)
        post["image"] = image_path

    return post


def record_post(state, post, tweet_id=None, tweet_url=None):
    entry = {
        "product_id": post["product_id"],
        "text": post["text"],
        "image": post["image"],
        "tweet_id": tweet_id,
        "tweet_url": tweet_url,
        "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    state.setdefault("history", []).append(entry)
    state["history"] = state["history"][-200:]
