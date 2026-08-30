#!/usr/bin/env python3
"""Crawl the shop's category listing pages and refresh content/product_catalog.json.

Run this occasionally (weekly is plenty - see the update-product-catalog
GitHub Actions workflow), not on every post: it walks every listing page
in the configured categories, which is dozens of requests.

Usage:
    python3 social/update_product_catalog.py
"""
from lib.catalog import load_json, save_catalog, CATALOG_PATH
from lib.scraper import crawl_catalog

BASE_DIR = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
CONFIG_PATH = f"{BASE_DIR}/config.json"


def main():
    config = load_json(CONFIG_PATH, {})
    base_url = config["base_url"].rstrip("/")
    category_ids = config["target_category_ids"]

    print(f"Crawling categories {category_ids} on {base_url} ...")
    products = crawl_catalog(base_url, category_ids)
    save_catalog(products)
    print(f"Saved {len(products)} products to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
