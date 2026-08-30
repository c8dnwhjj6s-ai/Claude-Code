"""Tweet copywriting for one scraped product."""
import random

BOILERPLATE_PREFIXES = ("[", "※", "・", "http", "TEL", "Tel")


def pick_benefit_line(description_lines, max_chars=90):
    """Pick the most useful sentence out of a product's free-text description.

    Product descriptions on the shop are unstructured (line breaks, a
    price/contact footer, sometimes an inline image). We skip obviously
    boilerplate lines and take the first real sentence, so the tweet
    reads like a pitch rather than dumping the whole page.
    """
    for line in description_lines:
        if len(line) < 6:
            continue
        if line.startswith(BOILERPLATE_PREFIXES):
            continue
        if "円" in line and "税" in line:  # pricing footer line
            continue
        return line[:max_chars]
    return ""


def category_hashtags(breadcrumb, category_hashtag_rules, limit=2):
    text = " ".join(breadcrumb)
    tags = []
    for keyword, tag in category_hashtag_rules:
        if keyword in text and tag not in tags:
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags


def choose_hashtags(breadcrumb, config):
    tags = list(config.get("common_hashtags", []))
    random.shuffle(tags)
    tags = tags[:2]
    tags += category_hashtags(breadcrumb, config.get("category_hashtag_rules", []))
    company_tag = config.get("company_hashtag", "").strip()
    if company_tag:
        tags.append(company_tag)
    # de-dupe while preserving order
    seen = set()
    ordered = []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            ordered.append(t)
    return " ".join(ordered)


def weighted_length(text):
    """Approximate X's weighted character count (see README for caveats)."""
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


def build_tweet_text(product, config, hook_prefix, cta, hashtag_line, max_len):
    name = product["name"]
    price_text = product.get("price_text") or ""
    benefit = pick_benefit_line(product.get("description_lines", []))
    url = product["url"]

    def assemble(benefit_text):
        lines = []
        if hook_prefix:
            lines.append(hook_prefix)
        lines.append(name)
        if price_text:
            lines.append(f"価格: {price_text}（税込）")
        if benefit_text:
            lines.append(benefit_text)
        lines.append("")
        lines.append(f"{cta}\n{url}")
        lines.append("")
        lines.append(hashtag_line)
        return "\n".join(lines)

    text = assemble(benefit)
    while weighted_length(text) > max_len and len(benefit) > 10:
        benefit = benefit[:-1]
        text = assemble(benefit.rstrip("、。") + "…")
    if weighted_length(text) > max_len:
        # even with no benefit line it doesn't fit (very long product name) - drop hook too
        text = assemble("")
    return text
