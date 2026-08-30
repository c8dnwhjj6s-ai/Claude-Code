#!/usr/bin/env python3
"""Scrape LED-category product data from jp-signage.ocnk.net.

Fetches every product in category 13 (LED), saves structured data to
jpp/data/products.json, and downloads each product's photos into
jpp/assets/img/products/<id>/.

Usage: python3 tools/scrape_products.py
Run from jpp/ or anywhere; paths are resolved relative to this file.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "products.json"
IMG_DIR = ROOT / "assets" / "img" / "products"

BASE = "https://jp-signage.ocnk.net"
CATEGORY_URL = f"{BASE}/product-list/13"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; jpp-catalog-builder/1.0)"}
REQUEST_DELAY = 0.4


def fetch(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return BeautifulSoup(resp.text, "lxml")


def collect_product_urls() -> list[str]:
    soup = fetch(CATEGORY_URL)
    count_el = soup.select_one(".category_item_count .number")
    total = int(count_el.get_text(strip=True)) if count_el else None
    urls: list[str] = []
    seen: set[str] = set()

    def collect_from(soup: BeautifulSoup) -> None:
        for a in soup.select('a[href*="/product/"]'):
            href = a.get("href", "")
            m = re.search(r"/product/(\d+)", href)
            if not m:
                continue
            full = f"{BASE}/product/{m.group(1)}"
            if full not in seen:
                seen.add(full)
                urls.append(full)

    collect_from(soup)
    page_nums = [int(n) for n in re.findall(r"product-list/13\?page=(\d+)", str(soup))]
    max_page = max(page_nums) if page_nums else 1
    for page in range(2, max_page + 1):
        page_soup = fetch(f"{CATEGORY_URL}?page={page}")
        collect_from(page_soup)

    print(f"category reports {total} items; collected {len(urls)} product URLs across {max_page} page(s)")
    return urls


def parse_price(soup: BeautifulSoup) -> int | None:
    el = soup.select_one("#pricech")
    if not el:
        return None
    digits = re.sub(r"[^\d]", "", el.get_text())
    return int(digits) if digits else None


def parse_specs(soup: BeautifulSoup) -> list[dict]:
    specs = []
    table = soup.select_one("table.data_table")
    if not table:
        return specs
    for tr in table.select("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            specs.append({"label": th.get_text(strip=True), "value": td.get_text(strip=True)})
    return specs


def parse_images(soup: BeautifulSoup, product_url: str) -> list[str]:
    """Product photos are served through a resizing proxy whose URL is a hex-encoded,
    NUL-separated record: <original path>\\0<size>\\0<watermark text>\\0... . Decode it
    to pick the 400px variant and dedupe the 74px thumbnail of the same photo."""
    urls: list[str] = []
    seen_originals: set[str] = set()
    for img in soup.select("img"):
        src = img.get("src", "")
        m = re.search(r"/data/jp-signage/_/([0-9a-fA-F]+)\.\w+$", src)
        if not m:
            continue
        try:
            raw = bytes.fromhex(m.group(1)).decode("utf-8", errors="ignore")
        except ValueError:
            continue
        parts = raw.split("\x00")
        if len(parts) < 2:
            continue
        original_path, size = parts[0], parts[1]
        if size != "400" or original_path in seen_originals:
            continue
        seen_originals.add(original_path)
        urls.append(urljoin(product_url, src))
    return urls


def parse_stock_status(soup: BeautifulSoup) -> str | None:
    el = soup.select_one(".detail_section.stock")
    return el.get_text(strip=True) if el else None


def parse_product(url: str) -> dict | None:
    soup = fetch(url)
    product_id = re.search(r"/product/(\d+)", url).group(1)

    name_el = soup.select_one("h1 .goods_name")
    if not name_el:
        print(f"  ! skip {url}: no product name found (removed/unavailable listing)")
        return None
    name = name_el.get_text(strip=True)
    code_el = soup.select_one(".model_number_value")
    code = code_el.get_text(strip=True) if code_el else ""

    desc_el = soup.select_one(".item_desc_text")
    description = desc_el.get_text("\n", strip=True) if desc_el else ""

    return {
        "id": product_id,
        "code": code,
        "name": name,
        "price": parse_price(soup),
        "stock_status": parse_stock_status(soup),
        "description": description,
        "specs": parse_specs(soup),
        "images": parse_images(soup, url),
        "source_url": url,
    }


def download_images(product: dict) -> list[str]:
    local_paths = []
    product_dir = IMG_DIR / product["id"]
    product_dir.mkdir(parents=True, exist_ok=True)
    for i, img_url in enumerate(product["images"], start=1):
        ext = ".jpg"
        dest = product_dir / f"{i}{ext}"
        try:
            resp = requests.get(img_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            local_paths.append(f"assets/img/products/{product['id']}/{i}{ext}")
            time.sleep(REQUEST_DELAY)
        except requests.RequestException as e:
            print(f"  ! image download failed for {product['id']} #{i}: {e}")
    return local_paths


def main() -> None:
    urls = collect_product_urls()
    products = []
    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {url}")
        product = parse_product(url)
        if product is None:
            continue
        product["local_images"] = download_images(product)
        products.append(product)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps({"products": products}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {len(products)} products to {DATA_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
