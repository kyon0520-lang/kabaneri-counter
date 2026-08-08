# カバネリ CZ発光カウンター — GitHub Pages 公開手順

このフォルダの中身をそのまま GitHub のリポジトリに置けば、iPhoneでアプリのように使えます。

## 入っているもの

| ファイル | 役割 |
|---|---|
| `index.html` | アプリ本体（これ1つで動きます） |
| `manifest.webmanifest` | アプリ名「カバネリカウンター」・全画面表示・アイコンの設定 |
| `sw.js` | オフラインで動かすための仕組み（圏外のホールでも起動できます） |
| `apple-touch-icon.png` | iPhoneのホーム画面アイコン（180px） |
| `icon-192.png` / `icon-512.png` | Android・PWA用アイコン |
| `ogp.png` | Xでシェアしたときに出る画像（1200×630） |

---

## 手順

### 1. リポジトリを作る

1. https://github.com/new を開く（アカウントがなければ先に作成）
2. **Repository name** に `kabaneri-counter` と入力
3. **Public** を選ぶ（Privateだと Pages が使えません）
4. 「Create repository」

### 2. ファイルをアップロードする

1. 作成後の画面で **uploading an existing file** をクリック
2. Finderで `/Users/Shared/kabaneri-counter/github-pages/` を開き、**中のファイルを全部**ドラッグ＆ドロップ
   （フォルダごとではなく、中身だけ。README.md は入れても入れなくてもOK）
3. 下の「Commit changes」を押す

### 3. Pages を有効にする

1. リポジトリの **Settings** → 左メニューの **Pages**
2. **Source** を `Deploy from a branch`、**Branch** を `main` / `/ (root)` にして Save
3. 1〜2分待つと、同じ画面に公開URLが出ます

```
https://あなたのユーザー名.github.io/kabaneri-counter/
```

### 4. X用の画像URLを直す（シェアする場合のみ）

`index.html` の中に `USERNAME` という文字が3か所あります。ここを自分のGitHubユーザー名に置き換えてください。Xのカード画像がこのURLを見に行くためです。

Macで一括置換するなら、ターミナルで（`あなたのユーザー名` の部分だけ書き換えて実行）:

```bash
sed -i '' 's/USERNAME/あなたのユーザー名/g' /Users/Shared/kabaneri-counter/github-pages/index.html
```

置き換えた `index.html` をGitHubに再アップロードすれば完了です。
（アプリの動作自体には影響しないので、シェアしないなら放置で問題ありません）

### 5. iPhoneでアプリにする

1. Safariで公開URLを開く
2. 共有ボタン → **ホーム画面に追加**
3. 名前が「カバネリカウンター」、アイコンが専用のものになっていることを確認して「追加」

ホーム画面から起動すると、Safariのアドレスバーやタブが出ない全画面表示になります。一度開いておけば、次からは**圏外でも起動できます**。

---

## あとから修正したいとき

1. `index.html` を編集
2. `sw.js` の1行目あたりにある `const CACHE = 'kabaneri-counter-v1';` の **数字を1つ上げる**（`v2`, `v3`…）
   ※ここを上げないと、古い画面がキャッシュされたままになります
3. GitHubで対象ファイルを開き、鉛筆アイコン → 内容を貼り替え → Commit

## 注意

- 公開URLは、知っている人なら誰でも開けます（検索には出にくいですが、非公開ではありません）
- カウントのデータは**開いた人それぞれの端末**に保存されます。他人の操作が自分の数字に影響することはありません
- 背景に使う画像も端末内に保存されるだけで、どこにも送信されません
