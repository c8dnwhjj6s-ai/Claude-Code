"""Scraper for the JP-Signage / LED Vision online shop (Ocnk platform).

Two entry points:
  - crawl_catalog(...)     walks category listing pages and returns a
                            lightweight index of every product (id/url/
                            name/thumbnail/price text). Meant to be run
                            occasionally (see update_product_catalog.py),
                            not on every post.
  - fetch_product_detail() fetches ONE product page and returns the fresh
                            name/price/stock/description/image for it.
                            This is what runs on every scheduled post, so
                            it only ever issues a single request.
"""
import html
import re
import time

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; JPCreateSocialBot/1.0)"
REQUEST_TIMEOUT = 20
PAGE_DELAY_SECONDS = 0.6


def _get(session, url, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def _make_session():
    return requests.Session()


def list_products_in_category(base_url, category_id, session=None):
    """Yield {id, url, name, model_number, thumbnail, price_text} for one category."""
    session = session or _make_session()
    first_page_first_id = None
    page = 1
    while True:
        url = f"{base_url}/product-list/{category_id}" + (f"?page={page}" if page > 1 else "")
        soup = BeautifulSoup(_get(session, url), "html.parser")
        cards = soup.select("div.item_data[data-product-id]")
        if not cards:
            break

        first_id_this_page = cards[0]["data-product-id"]
        if page == 1:
            first_page_first_id = first_id_this_page
        elif first_id_this_page == first_page_first_id:
            # Pagination wrapped back to page 1: we've gone past the last page.
            break

        for card in cards:
            product_id = card["data-product-id"]
            link = card.select_one("a.item_data_link")
            name_el = card.select_one(".item_name .goods_name")
            model_el = card.select_one(".item_name .model_number_value")
            img_el = card.select_one(".global_photo img")
            price_el = card.select_one(".price .selling_price .figure")
            if not (link and name_el):
                continue
            yield {
                "id": product_id,
                "url": link["href"],
                "name": name_el.get_text(strip=True),
                "model_number": model_el.get_text(strip=True) if model_el else "",
                "thumbnail": img_el.get("src") if img_el else "",
                "price_text": price_el.get_text(strip=True) if price_el else "",
            }

        page += 1
        time.sleep(PAGE_DELAY_SECONDS)


def crawl_catalog(base_url, category_ids):
    """Crawl multiple categories and return a deduplicated product list."""
    session = _make_session()
    by_id = {}
    for category_id in category_ids:
        for product in list_products_in_category(base_url, category_id, session=session):
            by_id[product["id"]] = product
    return sorted(by_id.values(), key=lambda p: int(p["id"]))


_PRICE_META_RE = re.compile(r'property="product:price:amount"\s+content="(\d+)"')


def fetch_product_detail(url, session=None):
    session = session or _make_session()
    page_html = _get(session, url)
    soup = BeautifulSoup(page_html, "html.parser")

    def meta(prop):
        tag = soup.find("meta", attrs={"property": prop})
        return html.unescape(tag["content"]) if tag and tag.get("content") else ""

    name = meta("og:title")
    image = meta("og:image")
    price_match = _PRICE_META_RE.search(page_html)
    price_amount = int(price_match.group(1)) if price_match else None

    stock_el = soup.select_one(".detail_section.stock")
    in_stock = True
    if stock_el:
        in_stock = "soldout" not in stock_el.get("class", []) and "在庫なし" not in stock_el.get_text()

    desc_el = soup.select_one(".item_desc_text")
    description_lines = []
    if desc_el:
        raw = desc_el.get_text("\n", strip=True)
        for line in raw.split("\n"):
            line = line.strip()
            if line:
                description_lines.append(line)

    breadcrumb = [
        el.get_text(strip=True)
        for el in soup.select(".breadcrumb_list .breadcrumb_text")
    ]

    return {
        "url": url,
        "name": name,
        "price_amount": price_amount,
        "price_text": f"{price_amount:,}円" if price_amount is not None else "",
        "image": image,
        "in_stock": in_stock,
        "description_lines": description_lines,
        "breadcrumb": breadcrumb,
    }
