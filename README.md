# url-exporter

YouTubeチャンネルURLから、NotebookLMに貼り付けやすいYouTube動画URL一覧を生成するツールです。

## 目的
- NotebookLM投入用URL一覧（TXT/CSV）を作成する。
- 通常動画とLIVE関連（アーカイブ/進行中/予約）を対象にする。
- Shorts完全判定は行わず、通常動画のうち3分以下を実用上除外する。

## 技術方針
- YouTube Data API v3のみを使用。
- HTMLスクレイピングはしない。
- OAuthは使わない（APIキーのみ）。
- `search.list` は使わない。
- 使用APIは `channels.list`, `playlistItems.list`, `videos.list` のみ。

## APIキーの用意
1. Google CloudでYouTube Data API v3を有効化。
2. APIキーを作成。
3. ローカルでは環境変数 `YOUTUBE_API_KEY` に設定。

## GitHub Secrets設定
1. GitHubリポジトリの **Settings > Secrets and variables > Actions** を開く。
2. `New repository secret` で `YOUTUBE_API_KEY` を作成。

## 設定ファイル `config/channels.yml`
```yaml
channels:
  - name: "target_channel"
    url: "https://www.youtube.com/@example"

settings:
  output_txt: "data/output/notebooklm_urls.txt"
  output_csv: "data/output/notebooklm_urls.csv"
  debug_csv: "data/debug/notebooklm_urls_debug.csv"
  exclude_shorts: true
  shorts_duration_threshold_sec: 180
  include_active_live: true
  include_upcoming_live: true
  fail_on_partial_api_error: true
  max_pages: null
  max_items: null
```

対応URL:
- `https://www.youtube.com/@handle`
- `https://www.youtube.com/channel/UC...`

未対応URL（`/c/...`, `/user/...`）はエラーにします。

`settings.fail_on_partial_api_error`:
- `true`（推奨）: API途中失敗時に不完全なURL一覧を出力しない。
- `false`: API失敗があっても取得済みの部分出力を許可（調査・一時運用向け）。

## ローカル実行
```bash
pip install -r requirements.txt
export YOUTUBE_API_KEY="YOUR_API_KEY"
python -m scripts.export_urls
```


## 初回実行手順
1. `YOUTUBE_API_KEY` を GitHub Secrets に設定する。
2. `config/channels.yml` を実チャンネルURLに変更する。
3. GitHub Actions から手動実行する。
4. `data/output/notebooklm_urls.txt` を確認する。

## GitHub Actions手動実行
1. GitHubの **Actions** タブを開く。
2. `Export YouTube URLs` を選ぶ。
3. `Run workflow` を実行。

定期実行は毎日 UTC 23:00（JST 08:00）です。

## 出力ファイル
- `data/output/notebooklm_urls.txt`: 1行1URL（ヘッダーなし）
- `data/output/notebooklm_urls.csv`: `url` 列のみ
- `data/debug/notebooklm_urls_debug.csv`: 判定理由つきデバッグ情報

主な除外理由:
- `short_like_duration`
- `duration_missing`
- `api_video_not_found`
- `unsupported_url`
- `channel_not_found`

## Shorts除外仕様
- `duration_sec > 180` は採用。
- ただし `live` / `upcoming` は長さ不明でも採用。
- `duration_sec <= 180` の通常動画はShorts相当として除外。

## Streamlit Cloudで使う
1. Streamlit Cloudで新規アプリを作成。
2. Repository: `kyo563/url-exporter`
3. Branch: `main`
4. Main file path: `streamlit_app.py`
5. Streamlit Secretsに以下を設定。

```toml
YOUTUBE_API_KEY = "YOUR_API_KEY"
```

補足:
- Streamlit UIは `config/channels.yml` を使わず、画面入力で1チャンネルを処理します。
- APIキーは `st.secrets["YOUTUBE_API_KEY"]` を優先し、なければ環境変数 `YOUTUBE_API_KEY` を参照します。
- UIはファイル保存せず、画面表示とダウンロード（TXT/CSV/debug CSV）のみ行います。
