# アクセスレポート

3ページ（カバネリ発光カウンタ／東宝まつわるチェッカー／イベントチェッカー）の
PV・訪問者数を毎日 Cloudflare Web Analytics から取得し、`reports/YYYY-MM-DD.md` に記録する。
`.github/workflows/analytics-daily.yml` が毎日 JST 01:00 に自動実行。

- `report.py` — 集計スクリプト。stdlib のみで動く（`pip install` 不要）
- `data.json` — 日別の生データ（正本）。`report.py` が自動で追記する
- `reports/YYYY-MM-DD.md` — 人が読む日次レポート（前日比・直近7日の推移つき）

## 初回セットアップ（1回だけ）

GitHub リポジトリの Settings → Secrets and variables → Actions で、以下を追加する。

| Secret名 | 値 |
|---|---|
| `CLOUDFLARE_ANALYTICS_TOKEN` | **Account Analytics: Read** 権限だけを持つ新規APIトークン |

作り方: Cloudflare ダッシュボード → 右上のプロフィール → API Tokens →
Create Token → Custom token →
Permissions に `Account` / `Account Analytics` / `Read` を追加 →
Account Resources はこのアカウントに限定 → 作成。

**`CLOUDFLARE_API_TOKEN`（デプロイ用）は流用しない。** 権限を混ぜると事故の元なので、
読み取り専用の別トークンを分けて発行する。`CLOUDFLARE_ACCOUNT_ID` は
デプロイで使っているものをそのまま使うので、追加登録は不要。

## 手動実行・過去日の取得

GitHub の Actions タブ → 「アクセスレポート」→ Run workflow。
`target_date` に `YYYY-MM-DD`（JST）を入れると、その日を（再)集計できる。
空のまま実行すると前日分。

## 集計方法の注意

- 対象は `requestPath` の**完全一致**のみ。まつわるチェッカーの `/matsuwaru/toho/` と
  イベントチェッカーの `/matsuwaru/toho/events` は別集計（後者は前者に含まれない）
- PV・訪問者数は Cloudflare のアダプティブサンプリングに基づく推定値
  （ダッシュボードの表示方式と同じ）
- 集計単位は JST の1日。実行は翌 01:00（JST）で、前日分が対象
