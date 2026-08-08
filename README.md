# みんなのスロット

パチスロを打ちながら数えるためのカウンター置き場です。
1機種目として、スマスロ 甲鉄城のカバネリ 海門決戦のCZ発光カウンターを公開しています。

- サイト: https://minnanoslot.com/
- カバネリカウンター: https://minnanoslot.com/kabaneri-unato/
- 取扱説明書: https://minnanoslot.com/kabaneri-unato/manual.html

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | サイトのトップページ（機種の一覧） |
| `kabaneri-unato/index.html` | カバネリカウンター本体（これ1つで動きます） |
| `kabaneri-unato/manual.html` | 取扱説明書 |
| `kabaneri-unato/manifest.webmanifest` | アプリ名「カバネリカウンター」・全画面表示・アイコンの設定 |
| `kabaneri-unato/sw.js` | オフラインで動かす仕組み（圏外のホールでも起動できます） |
| `kabaneri-unato/apple-touch-icon.png` | iPhoneのホーム画面アイコン（180px） |
| `kabaneri-unato/icon-192.png` / `icon-512.png` | Android・PWA用アイコン |
| `kabaneri-unato/ogp.png` | Xでシェアしたときに出る画像（1200×630） |

機種を増やすときは `機種名/` のフォルダを作り、トップページの一覧にリンクを足します。
フォルダ名はシリーズ名だけでなく機種まで区別できる形にします（例: `kabaneri-unato` = カバネリ 海門決戦）。

`kabaneri/` は旧URLで、新URLへ転送するためだけに残しています。
`index.html` と `sw.js` は実体を置く必要があります（旧サービスワーカーの後片づけのため、
リダイレクトにするとブラウザが更新を拒否して古い版が残り続けます）。
残りの転送は `_redirects` に書いてあります。

## 編集のしかた

**このフォルダのファイルを直接編集しないこと。** カウンター本体と取扱説明書は
`/Users/Shared/kabaneri-counter/` の `index.html` / `manual.html` が原本で、
ここのファイルはそこから自動生成されます（PWA・OGP・アクセス解析のタグが足されます）。

1. `/Users/Shared/kabaneri-counter/index.html` を編集
2. `kabaneri-unato/sw.js` の `const CACHE = 'kabaneri-counter-v12';` の**数字を1つ上げる**
   ※ここを上げないと、古い画面がキャッシュされたままになります
3. 生成する

   ```bash
   python3 /Users/Shared/kabaneri-counter/build-pages.py
   ```

トップページ（`index.html`）だけは原本がないので、ここで直接編集します。

## 公開のしかた（Cloudflare Pages）

このフォルダの中身をそのままアップロードする方式（直接アップロード）です。

```bash
cd /Users/Shared/kabaneri-counter/github-pages && npx wrangler pages deploy . --project-name=kabaneri-counter --branch=main
```

1〜2分で https://minnanoslot.com/ に反映されます。
`kabaneri-counter.pages.dev` でも同じものが見られます。

### 独自ドメイン

`minnanoslot.com` は Cloudflare のダッシュボードで
**Workers & Pages → kabaneri-counter → Custom domains** から接続しています。

### GitHub

コードの保管用です。push しても自動公開はされないので、上のコマンドと合わせて実行します。

```bash
git add -A && git commit -m "変更内容" && git push
```

## アクセス解析

Cloudflare Web Analytics を使っています。計測タグは `build-pages.py` が各ページに入れます。
Cookieを使わないため、同意バナーは不要です。

## 注意

- カウントのデータは**開いた人それぞれの端末**に保存されます。他人の操作が自分の数字に影響することはありません
- 数値は自分で数えた記録にもとづくもので、設定を保証するものではありません
