#!/usr/bin/env python3
"""Generate one post and publish it to X (Twitter).

Credentials are read from environment variables (set as GitHub Actions
secrets in production):
    X_API_KEY, X_API_SECRET           - app consumer key/secret
    X_ACCESS_TOKEN, X_ACCESS_SECRET   - user access token/secret
                                         (app permission must be "Read and Write")

Usage:
    python3 social/post_to_x.py             # generate + post for real
    python3 social/post_to_x.py --dry-run    # generate + print only, no API calls, no state change
"""
import argparse
import os
import sys

from lib.content import generate_post, record_post, weighted_length

REQUIRED_ENV_VARS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]


def post_with_tweepy(post):
    import tweepy

    creds = {name: os.environ[name] for name in REQUIRED_ENV_VARS}

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
                         help="generate and print the post, but do not call the X API or touch state.json")
    args = parser.parse_args()

    post, state = generate_post(advance_state=False)

    print(f"[topic]  {post['topic_id']} / {post['topic_name']}")
    print(f"[image]  {post['image']}")
    print(f"[weight] {weighted_length(post['text'])} / 280 (approx.)")
    print("-" * 40)
    print(post["text"])
    print("-" * 40)

    if args.dry_run:
        print("(dry run: not posted, state.json not updated)")
        return

    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"ERROR: missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    tweet_id, tweet_url = post_with_tweepy(post)
    print(f"[posted] {tweet_url}")

    record_post(state, post, tweet_id=tweet_id, tweet_url=tweet_url)


if __name__ == "__main__":
    main()
