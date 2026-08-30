# JPシグネージ 通販サイト X（Twitter）自動投稿システム

通販サイト https://jp-signage.ocnk.net/ （デジタルサイネージ・LED表示機の専門ショップ）から商品を自動選定し、紹介文・ハッシュタグ・画像をすべて自動生成して1日3回Xに投稿する仕組みです。

## 仕組み

1. **`update_product_catalog.py`**（週1回、自動実行）— ショップの「屋外デジタルサイネージ」「屋内デジタルサイネージ」「LED」カテゴリ（`config.json`の`target_category_ids`）を巡回し、商品ID・URL・商品名・価格・サムネイルの一覧を`content/product_catalog.json`に保存します（現時点で371商品）。
2. **`post_to_x.py`**（1日3回、自動実行）— カタログから商品を順番にローテーション選定 → その商品ページを1件だけ読みに行き、最新の価格・在庫・説明文を取得（在庫切れの商品は自動的にスキップ） → 紹介文とハッシュタグを生成 → OpenAI (`gpt-image-1`) で商品カテゴリに合わせた画像を毎回新規生成 → Xに画像付きで投稿します。
3. 投稿履歴とローテーション位置は`content/state.json`に記録し、ワークフローが自動コミットします（直近15件と同じ文面にはならないよう調整）。

## 画像について（重要な設計判断）

**実際の商品写真をそのまま使うのではなく、毎回AIで新しい画像を生成します。** ただし、gpt-image-1は実在する特定の商品を正確に再現できないため、「その商品そのものの写真」として生成すると、お客様が実物と違う印象を持ってしまうリスクがあります。そのため、商品名やカテゴリ（屋外／屋内／スタジアム／駅など）から**業種イメージに合った一般的な導入シーン**（例:「屋外の建物壁面に設置されたLEDビジョン」）を英語プロンプトで生成し、判読可能な文字・ロゴ・ブランド名は入れないようにしています。正確なスペック・実物写真はツイート内の商品ページリンクで確認してもらう設計です。

もし「実物写真の方が正確で良い」という場合は、`lib/image.py`を使わず`product["image"]`（スクレイピングで取得したショップ掲載の実写真）をそのまま添付する方式に切り替えることも可能です（画像生成コストもかかりません）。必要であれば言ってください。

## セットアップ手順

### 1. X Developer Portalでアプリを作成

1. https://developer.x.com/ でアプリを作成
2. 権限を **「Read and Write」** に変更
3. 権限変更後は **Access Token / Secretを再生成**
4. API Key / API Key Secret / Access Token / Access Token Secret を控える

### 2. OpenAI APIキーを取得

https://platform.openai.com/ でAPIキーを発行してください（`gpt-image-1`が使えるアカウントである必要があります）。画像生成は1枚あたり数円〜十数円程度のコストがかかります（1日3枚 = 月90枚程度）。

### 3. GitHubリポジトリにSecretsを登録

`Settings > Secrets and variables > Actions > New repository secret`:

| Secret名 | 内容 |
|---|---|
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Key Secret |
| `X_ACCESS_TOKEN` | X Access Token |
| `X_ACCESS_SECRET` | X Access Token Secret |
| `OPENAI_API_KEY` | OpenAI APIキー |

### 4. 商品カタログの初回作成

このリポジトリには既に初回クロール済みの`content/product_catalog.json`（371商品）が入っていますが、最新化したい場合は手動でも実行できます:

```bash
cd social
pip install -r requirements.txt
python3 update_product_catalog.py
```

GitHub Actionsの「Actions」タブから `Update product catalog (JP Signage)` を手動実行（workflow_dispatch）することもできます。以降は毎週日曜に自動更新されます。

### 5. 動作確認

```bash
cd social

# テキストのみプレビュー（無料・state.jsonも変更しない）
python3 generate_post.py

# 画像生成も含めてプレビュー（OpenAI課金が発生します）
OPENAI_API_KEY=... python3 generate_post.py --with-image

# 投稿はせず、生成内容とプロンプトだけ確認（無料）
X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_SECRET=... \
  python3 post_to_x.py --dry-run
```

GitHub Actionsの `X auto post (JP Signage products)` ワークフローも `workflow_dispatch` の `dry_run: true` で手動テストできます。

## 投稿頻度・タイミングの変更

`.github/workflows/x-auto-post.yml` の `schedule.cron` を編集してください（UTC指定、JSTは+9時間）。デフォルトは 9:00 / 13:00 / 19:00 JST の1日3回です。

## 文面・画像の調整

- 商品説明の抽出ロジック: `lib/copywriting.py` の `pick_benefit_line`（ショップの説明文から最初の実質的な1文を採用）
- フック接頭辞・CTA文言: `config.json` の `hook_prefixes` / `ctas`
- ハッシュタグ: `config.json` の `common_hashtags` / `category_hashtag_rules` / `company_hashtag`
- 対象カテゴリ（クロール範囲）: `config.json` の `target_category_ids`（現在: 5=屋外デジタルサイネージ, 6=屋内デジタルサイネージ, 13=LED）
- 画像生成プロンプト・シーンの出し分け: `lib/image.py` の `_SCENE_RULES`

文字数はXの実カウントに厳密には一致しない簡易計算（`lib/copywriting.py:weighted_length`）で280文字制限の余裕を見て自動調整しています（`config.json` の `max_weighted_length` で調整可）。

## スクレイピングについて

`https://jp-signage.ocnk.net/` は株式会社JPクリエイト自社の通販サイトという前提で、そのショップ自身のSNSアカウントから自社商品を紹介する用途を想定しています。カタログ更新時のみ複数ページを巡回し、投稿ごとには対象商品ページを1件だけ取得する設計にして、サイトへの負荷を抑えています。
