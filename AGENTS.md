# AGENTS

このリポジトリで YouTube 入力形式を扱うときの最小ルール:

- 入力判定は `scripts/input_resolver.py` の `resolve_input()` に集約する。
- `watch` URL でも `list=` があれば、動画IDではなく playlist ID を優先する。
- playlist ID は形式を限定せず、`list=` の値をそのまま使う。
- `playlistItems.list` は `nextPageToken` で最後までページングする。
- Streamlit / CLI / GitHub Actions で判定ロジックを重複させない。
