# LEDビジョン X（Twitter）自動投稿システム

`led-vision-lp`（LEDビジョン販売サイト／株式会社JPクリエイト）向けに、1日3回、業種別のLEDビジョン紹介ツイートを自動生成・自動投稿する仕組みです。

## 仕組み

- `content/topics.json` — スタジアム／店舗／病院など10業種分の訴求文（LPページの実際のコピーから抽出）とハッシュタグ
- `lib/content.py` — 業種を順番にローテーションしながら、フック文・CTA・ハッシュタグの組み合わせを変えてツイート本文を生成し、`led-vision-lp/assets/img/` の中から業種に対応する画像をランダムに選択
- `content/state.json` — どこまでローテーションしたか（`cursor`）と投稿履歴（`history`、直近の重複回避に使用）。投稿の度にワークフローがコミットして更新
- `generate_post.py` — 投稿内容をプレビューするだけのCLI（state.jsonは変更しない）
- `post_to_x.py` — 実際にX APIへ投稿するスクリプト（`--dry-run` で投稿せず内容確認のみ可能）
- `.github/workflows/x-auto-post.yml` — 毎日 9:00 / 13:00 / 19:00（JST）に自動実行するGitHub Actions

## 画像について

新規に画像を作る代わりに、既存LPの `assets/img/` にある各業種のヒーロー画像・特徴画像・導入事例画像をそのまま使い回します（例: `stadium_hero.png`, `retail_feat_a.png` など）。同じ業種の中でも前回と違う画像を優先的に選ぶようにしているので、同じ業種が回ってきても毎回同じ画像にはなりません。

将来的にバナー風の画像（テキスト入り）を自動生成したい場合は、Pillow等で `assets/img` の写真にキャッチコピーを合成する処理を追加する拡張が考えられます（今回は未実装）。

## セットアップ手順

### 1. X Developer Portalでアプリを作成

1. https://developer.x.com/ でアプリを作成（Free枠でOK）
2. アプリの権限を **「Read and Write」** に変更
3. 権限変更後は **Access Token / Secretを再生成**（権限変更前のトークンは読み取り専用のまま）
4. 以下4つの値を控える
   - API Key / API Key Secret（Consumer Key/Secret）
   - Access Token / Access Token Secret

### 2. GitHubリポジトリにSecretsを登録

`Settings > Secrets and variables > Actions > New repository secret` で以下を登録:

| Secret名 | 内容 |
|---|---|
| `X_API_KEY` | API Key |
| `X_API_SECRET` | API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_SECRET` | Access Token Secret |

### 3. リンク先URLを設定（任意）

`social/config.json` の `"site_url"` にLPの公開URL（例: `https://jpcreate.com/led-vision/`）を設定すると、ツイート本文にリンクが入るようになります。現時点ではこのリポジトリのLPが実際にどこで公開されるか分からないため、空文字（リンクなし）を初期値にしています。GitHub Pages等で公開したら、そのURLを設定してください。

### 4. 動作確認

```bash
cd social
pip install -r requirements.txt

# 生成内容をプレビューするだけ（投稿しない・state.jsonも変更しない）
python3 generate_post.py

# 認証情報を設定した上で、投稿せずに内容だけ確認
X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_SECRET=... \
  python3 post_to_x.py --dry-run
```

GitHub Actionsの「Actions」タブから `X auto post (LED Vision)` ワークフローを手動実行（`workflow_dispatch`）し、`dry_run: true` を指定すれば、実際に投稿せずにログだけ確認できます。

## 投稿頻度・タイミングの変更

`.github/workflows/x-auto-post.yml` の `schedule.cron` を編集してください（UTC指定。JSTへは+9時間で変換）。X API Freeプランは投稿数の上限があるため、1日3件（月90件程度）であれば余裕があります。

## 文面の調整

- 訴求文そのもの: `content/topics.json` の `pain`（課題提起）/ `benefit`（解決策）
- フック接頭辞・CTA文言: `config.json` の `hook_prefixes` / `ctas`
- 共通ハッシュタグ・会社タグ: `config.json` の `common_hashtags` / `company_hashtag`
- 業種別ハッシュタグ: `content/topics.json` の各トピックの `hashtags`

文字数はX側の実際のカウントとは厳密には一致しない簡易計算（`lib/content.py:weighted_length`）で280文字制限の余裕を見て自動的に本文を切り詰めています（`config.json` の `max_weighted_length` で調整可）。
