#!/usr/bin/env python3
"""Pick the next product, generate an image + tweet text, and publish it to X.

Credentials (environment variables / GitHub Actions secrets):
    X_API_KEY, X_API_SECRET           - X app consumer key/secret (permission: Read and Write)
    X_ACCESS_TOKEN, X_ACCESS_SECRET   - X user access token/secret
    OPENAI_API_KEY                    - for image generation (gpt-image-1)

Usage:
    python3 social/post_to_x.py             # generate + post for real
    python3 social/post_to_x.py --dry-run    # generate text + show the image prompt, no API calls, no state change
"""
import argparse
import os
import sys

from lib.catalog import load_catalog, load_json, load_state, save_state
from lib.copywriting import weighted_length
from lib.post import generate_post, record_post

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

X_ENV_VARS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]


def post_with_tweepy(post):
    import tweepy

    creds = {name: os.environ[name] for name in X_ENV_VARS}

    auth = tweepy.OAuth1UserHandler(
        creds["X_API_KEY"], creds["X_API_SECRET"],
        creds["X_ACCESS_TOKEN"], creds["X_ACCESS_SECRET"],
    )
    api_v1 = tweepy.API(auth)

    client = tweepy.Client(
        consumer_key=creds["X_API_KEY"],
        consumer_secret=creds["X_API_SECRET"],
        access_token=creds["X_ACCESS_TOKEN"],
        access_token_secret=creds["X_ACCESS_SECRET"],
    )

    media_ids = None
    if post["image"] and os.path.exists(post["image"]):
        media = api_v1.media_upload(post["image"])
        media_ids = [media.media_id]

    response = client.create_tweet(text=post["text"], media_ids=media_ids)
    tweet_id = response.data["id"]
    return tweet_id, f"https://x.com/i/web/status/{tweet_id}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                         help="generate and print the post, but do not call OpenAI/X, and do not touch state.json")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH, {})
    catalog = load_catalog()
    state = load_state()

    openai_key = None if args.dry_run else os.environ.get("OPENAI_API_KEY")
    if not args.dry_run and not openai_key:
        print("ERROR: missing required environment variable: OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    post = generate_post(config, catalog, state, openai_api_key=openai_key, generate_image=not args.dry_run)

    print(f"[product] #{post['product_id']} {post['product_name']}")
    print(f"[url]     {post['product_url']}")
    print(f"[weight]  {weighted_length(post['text'])} / 280 (approx.)")
    print(f"[image]   {post['image'] or '(dry run, not generated)'}")
    print("-" * 40)
    print(post["text"])
    print("-" * 40)

    if args.dry_run:
        print("(dry run: not posted, state.json not updated)")
        return

    missing = [v for v in X_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"ERROR: missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    tweet_id, tweet_url = post_with_tweepy(post)
    print(f"[posted] {tweet_url}")

    record_post(state, post, tweet_id=tweet_id, tweet_url=tweet_url)
    save_state(state)


if __name__ == "__main__":
    main()
