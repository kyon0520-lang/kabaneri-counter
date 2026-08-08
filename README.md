# カバネリ CZ発光カウンター

スマスロ 甲鉄城のカバネリのCZ抽選を、その場で押して数えるためのカウンターです。
無名・生駒・銅藍の非発光／発光／高確発光を数えると、発光率とCZ 1回あたりの平均ポイントが自動で出ます。

- 公開URL: https://kabaneri-counter.pages.dev/
- 取扱説明書: https://kabaneri-counter.pages.dev/manual.html

## ファイル

| ファイル | 役割 |
|---|---|
| `index.html` | アプリ本体（これ1つで動きます） |
| `manual.html` | 取扱説明書 |
| `manifest.webmanifest` | アプリ名「カバネリカウンター」・全画面表示・アイコンの設定 |
| `sw.js` | オフラインで動かす仕組み（圏外のホールでも起動できます） |
| `apple-touch-icon.png` | iPhoneのホーム画面アイコン（180px） |
| `icon-192.png` / `icon-512.png` | Android・PWA用アイコン |
| `ogp.png` | Xでシェアしたときに出る画像（1200×630） |

## 公開のしかた（Cloudflare Pages）

このリポジトリを Cloudflare Pages に接続すると、`git push` するだけで自動的に公開されます。

### 初回だけ必要な設定

1. https://dash.cloudflare.com/ でアカウントを作成（メール認証のみ・無料）
2. 左メニューの **Workers & Pages** → **Create** → **Pages** タブ → **Connect to Git**
3. GitHubとの連携を許可し、`kabaneri-counter` リポジトリを選択
4. ビルド設定は以下のとおり（静的ファイルだけなのでビルド不要）

   | 項目 | 値 |
   |---|---|
   | Project name | `kabaneri-counter` |
   | Production branch | `main` |
   | Framework preset | None |
   | Build command | （空欄） |
   | Build output directory | `/` |

5. **Save and Deploy** → 1〜2分で `https://kabaneri-counter.pages.dev/` が公開されます

※ プロジェクト名を変えると公開URLも変わります。`index.html` のOGP設定（`og:url` / `og:image`）が `kabaneri-counter.pages.dev` を指しているので、別名にした場合はそこも直してください。

### 2回目以降

`main` ブランチに push すれば自動で反映されます。

```bash
git add -A && git commit -m "変更内容" && git push
```

## アクセス解析

Cloudflare Pages のプロジェクト設定から **Web Analytics** を有効にすると、日別のアクセス数・参照元が見られます。Cookieを使わないため、同意バナーは不要です。

## 修正するとき

1. `index.html` を編集
2. `sw.js` の `const CACHE = 'kabaneri-counter-v1';` の**数字を1つ上げる**（`v2`, `v3`…）
   ※ここを上げないと、古い画面がキャッシュされたままになります
3. commit して push

## 注意

- カウントのデータは**開いた人それぞれの端末**に保存されます。他人の操作が自分の数字に影響することはありません
- 数値は自分で数えた記録にもとづくもので、設定を保証するものではありません
