#!/usr/bin/env python3
"""Preview the next auto-generated product post without posting or advancing state.

Usage:
    python3 social/generate_post.py                # text only, image generation is skipped (no cost)
    python3 social/generate_post.py --with-image    # also calls OpenAI to render the image (costs money, needs OPENAI_API_KEY)
"""
import argparse
import copy
import os

from lib.catalog import load_catalog, load_json, load_state
from lib.copywriting import weighted_length
from lib.post import generate_post

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-image", action="store_true",
                         help="also generate the image via OpenAI (uses OPENAI_API_KEY, costs money)")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH, {})
    catalog = load_catalog()
    state = copy.deepcopy(load_state())  # never persist a preview

    api_key = os.environ.get("OPENAI_API_KEY") if args.with_image else None
    post = generate_post(config, catalog, state, openai_api_key=api_key, generate_image=args.with_image)

    print(f"[product] #{post['product_id']} {post['product_name']}")
    print(f"[url]     {post['product_url']}")
    print(f"[weight]  {weighted_length(post['text'])} / 280 (approx.)")
    print(f"[image]   {post['image'] or '(not generated in this preview)'}")
    print(f"[prompt]  {post['image_prompt']}")
    print("-" * 40)
    print(post["text"])
    print("-" * 40)


if __name__ == "__main__":
    main()
