#!/usr/bin/env python3
"""Generate products.html from data/products.json.

Usage: python3 tools/generate_products_page.py
Run from anywhere; paths are resolved relative to this file so the
generator can be wired into a build step later without changes.
"""
import html
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "products.json"
OUTPUT_FILE = ROOT / "products.html"

THEME_COLOR_VARS = {
    "red": ("var(--red)", "var(--amber)", "var(--cyan)"),
    "amber": ("var(--amber)", "var(--cyan)", "var(--red)"),
    "cyan": ("var(--cyan)", "var(--red)", "var(--amber)"),
}


def e(value: str) -> str:
    return html.escape(value, quote=True)


def pixel_grid_svg(product_id: str, theme: str) -> str:
    """Deterministic LED-pixel-grid graphic used in place of a photo asset."""
    primary, secondary, tertiary = THEME_COLOR_VARS.get(theme, THEME_COLOR_VARS["cyan"])
    colors = [primary, primary, secondary, tertiary, "var(--line)"]
    rng = random.Random(product_id)
    cols, rows, cell = 8, 6, 30
    rects = []
    for row in range(rows):
        for col in range(cols):
            color = rng.choice(colors)
            opacity = round(rng.uniform(0.35, 1.0), 2)
            rects.append(
                f'<rect x="{col * cell}" y="{row * cell}" width="{cell - 3}" '
                f'height="{cell - 3}" fill="{color}" opacity="{opacity}"/>'
            )
    width, height = cols * cell, rows * cell
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="{e(product_id)} pixel pattern" style="width:100%;height:100%;background:var(--panel-2);">'
        + "".join(rects)
        + "</svg>"
    )


def render_specs(specs: list[dict]) -> str:
    items = "\n".join(
        f'          <li><span>{e(s["label"])}</span><span>{e(s["value"])}</span></li>'
        for s in specs
    )
    return f'        <ul class="fg-specs">\n{items}\n        </ul>'


def render_product_card(p: dict) -> str:
    best_for = " / ".join(p["best_for"])
    return f"""      <div class="fg-card">
        <div class="fg-media">{pixel_grid_svg(p["id"], p["theme"])}</div>
        <div class="fg-tag">{e(p["tag_en"])} &mdash; {e(p["code"])}</div>
        <h3>{e(p["name"])}</h3>
        <p>{e(p["summary"])}</p>
        <p style="color:var(--text-dim); font-size:12px; padding:0 24px; margin-bottom:10px;">主な設置先: {e(best_for)}</p>
{render_specs(p["specs"])}
      </div>"""


def render_page(data: dict) -> str:
    page = data["page"]
    products = data["products"]
    cards = "\n".join(render_product_card(p) for p in products)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(page["title"])}</title>
<meta name="description" content="{e(page["meta_description"])}">
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body class="theme-cyan">

<header>
  <div class="colorbar"><span></span><span></span><span></span><span></span><span></span></div>
  <div class="wrap nav">
    <div class="logo">LED<span>VISION</span></div>
    <ul class="nav-links">
      <li><a href="index.html">業種別に探す</a></li>
      <li><a href="#lineup">製品ラインナップ</a></li>
      <li><a href="#contact">お問い合わせ</a></li>
    </ul>
    <a href="#contact" class="nav-cta">資料請求</a>
  </div>
</header>

<section class="hero hero--center">
  <div class="wrap hero-center-inner">
    <div class="eyebrow">{e(page["eyebrow"])}</div>
    <h1 class="headline">{page["headline_html"]}</h1>
    <p class="hero-sub">{e(page["hero_sub"])}</p>
    <div class="hero-actions">
      <a href="#contact" class="btn-primary">お見積もりを依頼する</a>
      <a href="#lineup" class="btn-secondary">ラインナップを見る</a>
    </div>
  </div>
</section>

<section id="lineup">
  <div class="wrap">
    <div class="section-tag">Product Lineup</div>
    <h2 class="section-title">用途に合わせた{len(products)}つのビジョンシリーズ</h2>
    <p class="section-lead">設置場所や運用要件に応じて、シリーズ単位で最適なモデルをご提案します。詳細スペックはお問い合わせ時に個別にご案内いたします。</p>
    <div class="features-grid-wrap">
{cards}
    </div>
  </div>
</section>

<section class="cta-section" id="contact">
  <div class="wrap">
    <div class="section-tag" style="justify-content:center; display:flex;">Get Started</div>
    <h2 class="section-title" style="margin-left:auto; margin-right:auto;">貴施設に最適な製品シリーズを、無料でご提案します。</h2>
    <p class="section-lead">設置場所の規模や用途を踏まえ、最適なシリーズとサイズ構成をあわせてご提案いたします。</p>

    <div class="contact-panel">
      <div class="contact-info">
        <div class="contact-info-item">
          <div class="ci-label">お電話でのお問い合わせ</div>
          <div class="ci-value">0120-339-114</div>
          <div class="ci-note">受付時間 平日9:00-18:00</div>
        </div>
        <div class="contact-info-item">
          <div class="ci-label">メールでのお問い合わせ</div>
          <div class="ci-value ci-mail">info@jpcreate.com</div>
        </div>
      </div>

      <form class="contact-form" id="contactForm" action="mail.php" method="post">
        <input type="hidden" name="form_page" value="{e(page["form_page_label"])}">
        <input type="hidden" name="form_started" id="formStarted" value="">
        <div class="hp-field" aria-hidden="true">
          <label for="website">Website</label>
          <input type="text" id="website" name="website" tabindex="-1" autocomplete="off">
        </div>
        <div class="form-row">
          <label for="company">会社名 <span class="req">必須</span></label>
          <input type="text" id="company" name="company" required placeholder="株式会社〇〇">
        </div>
        <div class="form-row">
          <label for="name">ご担当者名 <span class="req">必須</span></label>
          <input type="text" id="name" name="name" required placeholder="山田 太郎">
        </div>
        <div class="form-row form-row-half">
          <div>
            <label for="tel">電話番号</label>
            <input type="tel" id="tel" name="tel" placeholder="090-0000-0000">
          </div>
          <div>
            <label for="email">メールアドレス <span class="req">必須</span></label>
            <input type="email" id="email" name="email" required placeholder="you@example.com">
          </div>
        </div>
        <div class="form-row">
          <label for="venue">施設名・設置場所</label>
          <input type="text" id="venue" name="venue" placeholder="〇〇施設">
        </div>
        <div class="form-row">
          <label for="message">お問い合わせ内容 <span class="req">必須</span></label>
          <textarea id="message" name="message" rows="5" required placeholder="ご検討中のシリーズ、設置希望場所、規模、時期などご記入ください"></textarea>
        </div>
        <button type="submit" class="btn-primary form-submit">送信する</button>
        <p class="form-status" id="formStatus" aria-live="polite"></p>
      </form>
    </div>
  </div>
</section>

<footer>
  <div class="wrap footer-wrap">
    <div class="footer-company">
      <div class="footer-name">株式会社JPクリエイト</div>
      <div class="footer-contact">TEL: 0120-339-114 &nbsp;/&nbsp; Email: info@jpcreate.com</div>
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

  var form = document.getElementById('contactForm');
  var formStarted = document.getElementById('formStarted');
  if (formStarted) {{ formStarted.value = String(Date.now()); }}
  var status = document.getElementById('formStatus');
  form.addEventListener('submit', function () {{
    status.textContent = '送信しています…';
    status.classList.remove('form-status-ok');
  }});
</script>

</body>
</html>
"""


def main() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    OUTPUT_FILE.write_text(render_page(data), encoding="utf-8")
    print(f"Generated {OUTPUT_FILE.relative_to(ROOT)} from {DATA_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
