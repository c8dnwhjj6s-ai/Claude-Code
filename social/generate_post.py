#!/usr/bin/env python3
"""Preview the next auto-generated post without posting or advancing state.

Usage:
    python3 social/generate_post.py
"""
from lib.content import generate_post, weighted_length


def main():
    post, _state = generate_post(advance_state=False)
    print(f"[topic]  {post['topic_id']} / {post['topic_name']}")
    print(f"[image]  {post['image']}")
    print(f"[weight] {weighted_length(post['text'])} / 280 (approx.)")
    print("-" * 40)
    print(post["text"])
    print("-" * 40)


if __name__ == "__main__":
    main()
