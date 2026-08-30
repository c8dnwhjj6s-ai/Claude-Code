#!/usr/bin/env python3
"""Generate the LED product catalog: one detail page per product plus an
index/listing page, from jpp/data/products.json.

Usage: python3 tools/generate_products_page.py
Run from anywhere; paths are resolved relative to this file.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "products.json"
PRODUCTS_DIR = ROOT / "products"
INDEX_FILE = ROOT / "index.html"

COMPANY_NAME = "株式会社JPクリエイト"
COMPANY_TEL = "0120-339-114"
COMPANY_EMAIL = "info@jpcreate.com"
SOURCE_SITE_NAME = "jp-signage.ocnk.net"


def e(value) -> str:
    return html.escape(str(value), quote=True)


def format_price(price) -> str:
    if price is None:
        return "価格はお問い合わせください"
    return f"¥{price:,}"


def render_stock_badge(stock_status) -> str:
    if not stock_status:
        return ""
    cls = "stock-out" if "なし" in stock_status else "stock-in"
    return f'<span class="stock-badge {cls}">{e(stock_status)}</span>'


def header(depth: str) -> str:
    """depth: '' for index.html at root, '../' for pages under products/"""
    return f"""<header>
  <div class="colorbar"><span></span><span></span><span></span><span></span><span></span></div>
  <div class="wrap nav">
    <div class="logo">LED<span>CATALOG</span></div>
    <ul class="nav-links">
      <li><a href="{depth}index.html">商品一覧</a></li>
      <li><a href="tel:{COMPANY_TEL}">お電話で相談</a></li>
    </ul>
    <a href="mailto:{COMPANY_EMAIL}" class="nav-cta">メールで問い合わせ</a>
  </div>
</header>"""


def footer() -> str:
    return f"""<footer>
  <div class="wrap footer-wrap">
    <div class="footer-company">
      <div class="footer-name">{e(COMPANY_NAME)}</div>
      <div class="footer-contact">TEL: {e(COMPANY_TEL)} &nbsp;/&nbsp; Email: {e(COMPANY_EMAIL)}</div>
    </div>
    <div>© 2026 JP CREATE Co., Ltd. All rights reserved.</div>
  </div>
</footer>

<button id="backToTop" class="back-to-top" aria-label="ページ上部に戻る" title="ページ上部に戻る">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 19V5M12 5L5 12M12 5L19 12" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>

<script>
  var backToTop = document.getElementById('backToTop');
  window.addEventListener('scroll', function () {{
    if (window.scrollY > 480) {{ backToTop.classList.add('show'); }}
    else {{ backToTop.classList.remove('show'); }}
  }});
  backToTop.addEventListener('click', function () {{
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }});
</script>"""


def render_gallery(images: list[str], name: str, depth: str) -> str:
    if not images:
        return '<div class="gallery-empty">画像なし</div>'
    main = f"{depth}{images[0]}"
    main_html = f'<div class="gallery-main"><img id="mainImg" src="{e(main)}" alt="{e(name)}"></div>'
    if len(images) == 1:
        return main_html
    thumbs = "\n".join(
        f'    <img src="{e(depth + img)}" alt="{e(name)} 画像{i+1}" class="{"active" if i == 0 else ""}" '
        f'onclick="document.getElementById(\'mainImg\').src=this.src; '
        f"document.querySelectorAll('.gallery-thumbs img').forEach(function(t){{t.classList.remove('active');}}); "
        f"this.classList.add('active');\">"
        for i, img in enumerate(images)
    )
    return f'{main_html}\n  <div class="gallery-thumbs">\n{thumbs}\n  </div>'


def render_description(description: str) -> str:
    if not description:
        return ""
    paragraphs = [p.strip() for p in description.split("\n") if p.strip()]
    return "\n".join(f"    <p>{e(p)}</p>" for p in paragraphs)


def render_specs(specs: list[dict]) -> str:
    if not specs:
        return ""
    rows = "\n".join(
        f'      <tr><td>{e(s["label"])}</td><td>{e(s["value"])}</td></tr>' for s in specs
    )
    return f"""<section class="product-specs-section">
  <div class="wrap">
    <div class="section-tag">Specifications</div>
    <h2 class="section-title">製品仕様</h2>
    <table class="spec-table">
{rows}
    </table>
  </div>
</section>"""


def render_product_page(p: dict) -> str:
    images = p.get("local_images") or []
    name = p["name"]
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(name)} | LED製品カタログ</title>
<meta name="description" content="{e((p.get('description') or name)[:120])}">
<link rel="stylesheet" href="../assets/css/style.css">
<link rel="stylesheet" href="../assets/css/product.css">
</head>
<body class="theme-cyan">

{header("../")}

<div class="wrap">
  <div class="breadcrumb"><a href="../index.html">商品一覧</a><span>/</span>{e(name)}</div>
</div>

<section class="product-hero">
  <div class="wrap product-grid">
    <div class="product-gallery">
      {render_gallery(images, name, "../")}
    </div>
    <div class="product-info">
      <div class="product-code">{e(p.get("code") or p["id"])}{render_stock_badge(p.get("stock_status"))}</div>
      <h1 class="product-name">{e(name)}</h1>
      <div class="product-price">{format_price(p.get("price"))}<span class="unit">(税込)</span></div>
      <p class="product-price-note">価格・在庫状況は変動する場合があります。最新情報はお問い合わせください。</p>
      <div class="product-actions">
        <a href="tel:{COMPANY_TEL}" class="btn-primary">電話で相談する</a>
        <a href="mailto:{COMPANY_EMAIL}?subject={e(name)}について" class="btn-secondary">メールで問い合わせる</a>
      </div>
      <div class="product-desc">
{render_description(p.get("description", ""))}
      </div>
    </div>
  </div>
</div>
</section>

{render_specs(p.get("specs", []))}

<div class="wrap">
  <p class="source-note">この製品情報は{e(SOURCE_SITE_NAME)}の商品ページを基に作成しています。</p>
</div>

{footer()}

</body>
</html>
"""


def render_index_card(p: dict) -> str:
    images = p.get("local_images") or []
    media = (
        f'<img src="{e(images[0])}" alt="{e(p["name"])}" loading="lazy">'
        if images
        else '<div class="gallery-empty" style="height:100%;">画像なし</div>'
    )
    return f"""      <a class="fg-card-link" href="products/{p['id']}.html">
        <div class="fg-card">
          <div class="fg-media">{media}</div>
          <div class="fg-tag">{e(p.get("code") or p["id"])}</div>
          <h3>{e(p["name"])}</h3>
          <div class="fg-price">{format_price(p.get("price"))}</div>
        </div>
      </a>"""


def render_index(products: list[dict]) -> str:
    cards = "\n".join(render_index_card(p) for p in products)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LED製品カタログ | {e(COMPANY_NAME)}</title>
<meta name="description" content="{e(COMPANY_NAME)}が取り扱うLED関連製品の一覧です。屋内外LED表示機、LEDパネルセット、コントローラーなどを掲載しています。">
<link rel="stylesheet" href="assets/css/style.css">
<link rel="stylesheet" href="assets/css/product.css">
</head>
<body class="theme-cyan">

{header("")}

<section class="hero hero--center" style="background:var(--bg);padding:64px 0 0;">
  <div class="wrap hero-center-inner">
    <div class="eyebrow">LED Product Catalog</div>
    <h1 class="headline">LED製品を、<em>{len(products)}</em>点掲載中。</h1>
    <p class="hero-sub">屋内外LED表示機・LEDパネルセット・コントローラーなど、取り扱いLED製品を1点ずつご紹介します。</p>
  </div>
</section>

<section id="lineup">
  <div class="wrap">
    <div class="section-tag">Product List</div>
    <h2 class="section-title">製品一覧</h2>
    <p class="section-lead">気になる製品をクリックすると、価格・仕様・写真など詳細情報をご覧いただけます。</p>
    <div class="features-grid-wrap">
{cards}
    </div>
  </div>
</section>

<section class="cta-section" id="contact">
  <div class="wrap">
    <div class="section-tag" style="justify-content:center; display:flex;">Get Started</div>
    <h2 class="section-title" style="margin-left:auto; margin-right:auto;">ご希望の製品や設置に関するご相談を承ります。</h2>
    <p class="section-lead" style="margin-left:auto; margin-right:auto; text-align:center;">お電話またはメールでお気軽にお問い合わせください。</p>
    <div class="hero-actions" style="justify-content:center; margin-top:32px;">
      <a href="tel:{COMPANY_TEL}" class="btn-primary">電話で相談する ({COMPANY_TEL})</a>
      <a href="mailto:{COMPANY_EMAIL}" class="btn-secondary">メールで問い合わせる</a>
    </div>
  </div>
</section>

{footer()}

</body>
</html>
"""


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    products = data["products"]

    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in products:
        out = PRODUCTS_DIR / f"{p['id']}.html"
        out.write_text(render_product_page(p), encoding="utf-8")
    print(f"Generated {len(products)} product pages in {PRODUCTS_DIR.relative_to(ROOT)}/")

    INDEX_FILE.write_text(render_index(products), encoding="utf-8")
    print(f"Generated {INDEX_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
