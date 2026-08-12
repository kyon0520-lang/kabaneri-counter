# みんなのスロット

パチスロを打ちながら数えるためのカウンター置き場です。
1機種目として、スマスロ 甲鉄城のカバネリ 海門決戦のCZ発光カウンターを公開しています。

- サイト: https://minnanoslot.com/
- カバネリカウンター: https://minnanoslot.com/kabaneri-unato/
- 取扱説明書: https://minnanoslot.com/kabaneri-unato/manual.html

## ファイル構成

原本は `src/`、公開されるのはそれ以外です。

| ファイル | 役割 |
|---|---|
| `src/index.html` | **カウンター本体の原本。ここを編集する** |
| `src/manual.html` | **取扱説明書の原本。ここを編集する** |
| `src/share.html` | claude.ai アーティファクト版（移行案内を掲示中） |
| `src/build-pages.py` | 原本から公開用ファイルを生成する |
| `src/make-icons.py` | アイコンとOGP画像を書き出す（macOS専用・後述） |
| `src/icon.html` | 旧アイコン生成ページ。`make-icons.py` に置き換わり、現在は未使用 |
| `src/top.html` | **トップページの原本。ここを編集する** |
| `src/top-mode.py` | トップページを「準備中」と「本編」で切り替える |
| `index.html` | 生成物。直接編集しない |
| `kabaneri-unato/index.html` | 生成物。直接編集しない |
| `kabaneri-unato/manual.html` | 生成物。直接編集しない |
| `kabaneri-unato/manifest.webmanifest` | アプリ名「カバネリカウンター」・全画面表示・アイコンの設定 |
| `kabaneri-unato/sw.js` | オフラインで動かす仕組み（圏外のホールでも起動できます） |
| `kabaneri-unato/apple-touch-icon.png` | iPhoneのホーム画面アイコン（180px） |
| `kabaneri-unato/icon-192.png` / `icon-512.png` | Android・PWA用アイコン |
| `kabaneri-unato/icon-maskable-512.png` | Android用。切り抜かれても文字が欠けないよう内側に寄せてある |
| `kabaneri-unato/ogp.png` | Xでシェアしたときに出る画像（1200×630） |

`src/` はリポジトリに置いてあるだけで、配信はされません（`_redirects` でトップへ転送）。

機種を増やすときは `機種名/` のフォルダを作り、トップページの一覧にリンクを足します。
フォルダ名はシリーズ名だけでなく機種まで区別できる形にします（例: `kabaneri-unato` = カバネリ 海門決戦）。

`kabaneri/` は旧URLで、新URLへ転送するためだけに残しています。
`index.html` と `sw.js` は実体を置く必要があります（旧サービスワーカーの後片づけのため、
リダイレクトにするとブラウザが更新を拒否して古い版が残り続けます）。

## 編集のしかた

**`kabaneri-unato/` の中は直接編集しないこと。** `src/` から自動生成されます
（PWA・OGP・アクセス解析のタグが足されます）。

1. `src/index.html` を編集する
2. `kabaneri-unato/sw.js` の `const CACHE = 'kabaneri-counter-vNN';` の**数字を1つ上げる**
   ※ここを上げないと、古い画面がキャッシュされたままになります
3. 生成する

   ```bash
   python3 src/build-pages.py
   ```

### トップページ

原本は `src/top.html`。公開される `index.html` は `top-mode.py` が書き出します。

```bash
python3 src/top-mode.py          # いまどちらか見る
python3 src/top-mode.py soon     # 準備中の画面にする
python3 src/top-mode.py full     # 本編に戻す
```

**いまは準備中（soon）です。** カウンター単体を先に配っているためで、
本編には「みんなのスロット」の説明と送信機能の記述が残っており、実態と合いません。
戻すときは、カウンター側の送信機能（`build-pages.py` の `SEND_ENABLED`）と
合わせて判断してください。

## 公開のしかた（Cloudflare Pages）

このフォルダの中身をアップロードする方式（直接アップロード）です。

```bash
npx wrangler pages deploy . --project-name=kabaneri-counter --branch=main
```

1〜2分で https://minnanoslot.com/ に反映されます。
`kabaneri-counter.pages.dev` でも同じものが見られます。

反映されないときは、Cloudflare のエッジキャッシュがまだ古い可能性があります。
数十秒待って読み直してください。

### 独自ドメイン

`minnanoslot.com` は Cloudflare のダッシュボードで
**Workers & Pages → kabaneri-counter → Custom domains** から接続しています。

### GitHub

```bash
git add -A && git commit -m "変更内容" && git push
```

**push しても自動公開はされません。** 公開は上の `wrangler` コマンドが必要です。
push だけで公開されるようにしたい場合は、ダッシュボードで Pages を GitHub 連携に
切り替えます（未実施）。

## 外出先から直すとき

原本が `src/` に入っているので、スマホなどからクラウド上のセッションで編集できます。
できること・できないことは次のとおりです。

| | 可否 |
|---|---|
| 文言・色・計算・レイアウトの修正 | できる |
| `build-pages.py` の実行（生成） | できる |
| コミットと push | できる |
| **公開（wrangler）** | **できない。Macに戻って上のコマンドを実行する** |
| **アイコン・OGP画像の作り直し** | **できない。下記のとおりmacOS専用** |

`make-icons.py` はヒラギノ明朝・ヒラギノ角ゴシックを使っており、これは macOS にしか
入っていません。画像を変えるときは Mac で実行してください。Pillow が必要です。

```bash
python3 -m pip install Pillow
python3 src/make-icons.py
```

## サーバー側（Cloudflare D1 ＋ Pages Functions）

実戦データの受け口と集計を `functions/api/` に置いています。

| ファイル | 役割 |
|---|---|
| `functions/api/records.js` | 実戦データを受ける（POST）。検算・重複排除・1日の上限つき |
| `functions/api/stats.js` | みんなの集計を返す（GET） |
| `functions/api/transfer.js` | 記録の引き継ぎ。8文字のコードで別端末へ移す。3日で消える |
| `src/schema.sql` | D1 のテーブル定義 |
| `wrangler.toml` | D1 の紐づけ（binding は `DB`） |

```bash
npx wrangler d1 execute minnanoslot --remote --file=src/schema.sql
```

### 送信機能の入り切り

`src/build-pages.py` の `SEND_ENABLED` で、公開版に含めるかを切り替えます。

```python
SEND_ENABLED = False   # みんなのスロットへの送信を外した版を書き出す
```

原本の該当箇所は `==SEND:START==` / `==SEND:END==` の印で囲んであります。
`False` のときはその中を消して書き出し、取扱説明書の章番号と目次も振り直します。
消し漏れがあるとビルドが止まります。

**いまは False（保存のみの版）です。** 記録の引き継ぎは送信とは別物なので残しています。

## アクセス解析

Cloudflare Web Analytics を使っています。計測タグは `build-pages.py` が各ページに入れます。
Cookieを使わないため、同意バナーは不要です。

## 注意

- カウントのデータは**開いた人それぞれの端末**に保存されます。他人の操作が自分の数字に影響することはありません
- 数値は自分で数えた記録にもとづくもので、設定を保証するものではありません
