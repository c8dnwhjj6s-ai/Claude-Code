"""Tweet content generation for the LED Vision auto-post system.

Builds a post (text + image) for one industry topic, rotating through
all topics so the account doesn't spam the same industry twice in a row,
and varying hooks / CTAs / hashtags so consecutive posts about the same
industry don't read as identical.
"""
import glob
import json
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BASE_DIR)
IMG_DIR = os.path.join(REPO_ROOT, "led-vision-lp", "assets", "img")

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
TOPICS_PATH = os.path.join(BASE_DIR, "content", "topics.json")
STATE_PATH = os.path.join(BASE_DIR, "content", "state.json")

# How many recent posts to check when avoiding an exact-duplicate tweet text.
DEDUPE_WINDOW = 15
MAX_GENERATION_ATTEMPTS = 25


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def weighted_length(text):
    """Approximate X's weighted character count.

    X (twitter-text) counts most non-Latin characters -- including the
    Japanese ranges we use here -- as weight 2, and a URL as a flat 23
    regardless of its real length. This is an approximation, not the
    official twitter-text algorithm, so callers should keep a safety
    margin below the real 280 limit (see config.json:max_weighted_length).
    """
    total = 0
    i = 0
    while i < len(text):
        if text[i:].startswith(("http://", "https://")):
            end = i
            while end < len(text) and not text[end].isspace():
                end += 1
            total += 23
            i = end
            continue
        total += 1 if ord(text[i]) < 0x2000 else 2
        i += 1
    return total


def pick_image(topic_id, avoid=None):
    candidates = sorted(glob.glob(os.path.join(IMG_DIR, f"{topic_id}_*.png")))
    if not candidates:
        return None
    if avoid and len(candidates) > 1:
        filtered = [c for c in candidates if c != avoid]
        if filtered:
            candidates = filtered
    return random.choice(candidates)


def last_image_for(topic_id, history):
    for entry in reversed(history):
        if entry.get("topic_id") == topic_id:
            return entry.get("image")
    return None


def build_tweet_text(topic, config, hook_prefix, cta, hashtag_line, max_len):
    pain = topic["pain"]
    benefit = topic["benefit"]
    url = config.get("site_url") or ""

    def assemble(benefit_text):
        lines = []
        if hook_prefix:
            lines.append(hook_prefix)
        lines.append(pain)
        lines.append(benefit_text)
        lines.append("")
        cta_line = f"{cta}{('　' + url) if url else ''}"
        lines.append(cta_line)
        lines.append("")
        lines.append(hashtag_line)
        return "\n".join(lines)

    text = assemble(benefit)
    while weighted_length(text) > max_len and len(benefit) > 10:
        benefit = benefit[:-1]
        text = assemble(benefit.rstrip("、。") + "…")
    return text


def choose_hashtags(topic, config):
    tags = list(config.get("common_hashtags", []))
    random.shuffle(tags)
    tags = tags[:2]
    tags += topic.get("hashtags", [])
    tags.append(config.get("company_hashtag", "").strip())
    tags = [t for t in tags if t]
    return " ".join(tags)


def next_topic(topics, state):
    cursor = state.get("cursor", 0) % len(topics)
    topic = topics[cursor]
    state["cursor"] = (cursor + 1) % len(topics)
    return topic


def generate_post(advance_state=True):
    config = load_json(CONFIG_PATH)
    topics = load_json(TOPICS_PATH)
    state = load_json(STATE_PATH)

    topic = next_topic(topics, state)
    history = state.get("history", [])
    recent_texts = {h["text"] for h in history[-DEDUPE_WINDOW:]}

    text = None
    for _ in range(MAX_GENERATION_ATTEMPTS):
        hook_prefix = random.choice(config["hook_prefixes"])
        cta = random.choice(config["ctas"])
        hashtag_line = choose_hashtags(topic, config)
        candidate = build_tweet_text(
            topic, config, hook_prefix, cta, hashtag_line,
            config.get("max_weighted_length", 260),
        )
        if candidate not in recent_texts:
            text = candidate
            break
    if text is None:
        text = candidate  # exhausted attempts; post it anyway

    avoid_image = last_image_for(topic["id"], history)
    image_path = pick_image(topic["id"], avoid=avoid_image)

    post = {
        "topic_id": topic["id"],
        "topic_name": topic["name"],
        "text": text,
        "image": image_path,
    }

    if advance_state:
        save_json(STATE_PATH, state)

    return post, state


def record_post(state, post, tweet_id=None, tweet_url=None):
    entry = {
        "topic_id": post["topic_id"],
        "text": post["text"],
        "image": post["image"],
        "tweet_id": tweet_id,
        "tweet_url": tweet_url,
    }
    import datetime

    entry["posted_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state.setdefault("history", []).append(entry)
    state["history"] = state["history"][-200:]
    save_json(STATE_PATH, state)
