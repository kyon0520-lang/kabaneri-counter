# まつわるチェッカー 仕様まとめ

2026-09-02 時点。**新しい店舗（エスパス歌舞伎など）を足す人が、最初に読む文書。**
やることリストは `TODO.md`、日々の運用手順もそちらにある。

- 示唆から検索: https://minnanoslot.com/matsuwaru/toho/
- イベント傾向: https://minnanoslot.com/matsuwaru/toho/events
- 店舗一覧: https://minnanoslot.com/matsuwaru/
- 置き場所: `/Users/Shared/kabaneri-counter/github-pages/matsuwaru/`
  （**ユーザーのホーム配下には置かない。**本名がSNSに漏れるため）

---

## 0. 何をするものか

マルハン新宿東宝ビル店の店長が、**前夜にXへ「示唆」を投稿し、翌日その機種が全台系（全台高設定）になる**。
示唆は「会議 → 怪奇 → 化物語」のような**言葉の連想**で書かれる。
それを毎朝まとめている個人ブログがあり、そこから

1. **その日の全系機種と差枚実績**（結果欄）
2. **示唆の連想経路**（矢印でつながった言葉の列）

を機械で取り出して、2つの画面にしている。

| 画面 | できること |
|---|---|
| **まつわるチェッカー**（`/<店舗id>/`） | 示唆の単語から、過去に全台系になった機種を逆引きする |
| **イベント傾向チェッカー**（`/<店舗id>/events`） | 「0のつく日」などのイベント別に、何がどれだけ選ばれてきたかを見る |

**AI・APIは実行時に一切使わない。**素のHTML/CSS/JSとJSONだけのPWA。
生成もPythonの標準ライブラリだけ（唯一の外部依存は検索用の読みを作る `pykakasi`。無くても動く）。

---

## 1. 絶対に守ること

**① 生成物を直接編集しない。**
`<店舗id>/index.html` `<店舗id>/events.html` `<店舗id>/sw.js` `<店舗id>/manifest.webmanifest` は
`src/` から自動生成される。毎朝の自動更新で上書きされるので、直した内容は消える。
**必ず `src/app.html` `src/events.html` を直して `python3 src/build-pages.py` を回す。**

**② 直したら必ず push する。**
毎朝の更新は GitHub のリポジトリからコードを取り出して動く。
ローカルでコミットしてデプロイしただけでは、次の自動更新に巻き戻される
（2026-08-29に24コミット分が実際に消えた）。

```bash
cd /Users/Shared/kabaneri-counter/github-pages
git add -A && git commit -m "..." && git push origin main
npx wrangler pages deploy . --project-name=kabaneri-counter --branch=main
```

自動更新が先に走っていて push が弾かれたら、`git fetch` → `git merge origin/main`。
`toho/data/events.json` が衝突したら生成物なので `git checkout --ours` で自分側を採り、
`events.py` と `src/build-pages.py` を流し直してからコミットする。

**③ `events.py` は `build-pages.py` より先。**
`build-pages.py` はHTMLを組むだけで、集計はしない。順番を逆にすると古い集計のまま公開される。

**④ ブログは他人の著作物。**
運営者への許諾連絡は**まだ送っていない**（`/Users/Shared/matsuwaru-permission-draft.md`）。
ユーザーは承知のうえで進めている。**この話を繰り返し持ち出さないこと。**

---

## 2. 全体の流れ

```
   ブログ（はてな）              店舗公式の設置機種ページ
        │ sitemap.xml                    │
        ▼                                ▼
   sync.py ──► cache/<店>/*.html    lineup.py ──► data/lineup.json
        │      （記事HTMLの保存）                 （現行の設置機種と台数）
        ▼
   lib.parse_html()  ← ここが記事の書式に強く依存する
        │
        ▼
   raw.json  ★正本。ここさえあれば全部作り直せる
        │
        ├─ build.py    ──► data/records.json（連想を1件1行に展開）
        │
        ├─ finalize.py ──► data/canon.json（名寄せ表）
        │                  data/machines.json（機種と判定された名前）
        │                  data/index.json ★検索画面が読む
        │                  data/token_readings.json（ひらがな読みの貯め置き）
        │
        └─ events.py   ──► data/events.json ★イベント傾向ページが読む
                           data/lead.json   ★トップのカードが読む
        │
        ▼
   src/build-pages.py ──► <店舗id>/index.html ・ events.html ・ sw.js ・ manifest
```

`sync.py` が 2〜5 をまとめて呼ぶので、**通常は `python3 sync.py toho` 一発**。
ネットに触らず作り直したいときは `python3 parse.py toho`（`cache/` から `raw.json` を再構築）。

---

## 3. ファイルの役割

### スクリプト

| ファイル | 役割 | 店舗に依存するか |
|---|---|---|
| `sync.py` | 毎朝の更新。未取得の記事だけ取って追記し、2〜5を順に呼ぶ | サイトマップの形に依存 |
| `lib.py` | **記事HTMLの解析。この仕組みの心臓部** | **強く依存（後述）** |
| `parse.py` | `cache/` から `raw.json` を全再構築（通常は使わない） | しない |
| `build.py` | `raw.json` → `records.json` と表記ゆれ候補 | しない |
| `finalize.py` | 名寄せ・機種判定・検索インデックス作成 | しない |
| `kana.py` | 漢字にひらがな読みを付ける（人参→にんじん） | しない |
| `lineup.py` | 店舗公式から現行の設置機種と台数を取る | **強く依存（HTMLの作り）** |
| `events.py` | イベント別の集計。**630行でいちばん重い** | しない（設定で動く） |
| `src/build-pages.py` | `src/*.html` から店舗ごとのページを書き出す | しない |

### 手で書く設定（店舗ごとに1式ずつ必要）

| ファイル | 中身 |
|---|---|
| `stores.json` | 店舗の定義。**ここに1件足すと画面が生える**（唯一リポジトリ直下） |
| `data/decisions.json` | 機種名の名寄せ（`merge`）。「チバリヨ→チバリヨ2」など |
| `data/corrections.json` | 誤解を招く連想を手で直す。対象日と元の文字列で特定する |
| `data/readings.json` | 機種の読み・別名／`語の読み`（自動読みの誤りを足し直す）／ラインナップ照合の調整／まつわり数字 |
| `data/event_defs.json` | **イベントの定義と表示順。`match` で対象日を決める** |
| `data/event_fixes.json` | 不定期イベントの検出ミス（除外・追加） |
| `data/event_lead.json` | 傾向のリード文を手で書くイベント |
| `data/event_notes.json` | イベントごとの概要文 |
| `data/event_signature.json` | イベントの看板機種 |
| `data/machine_groups.json` | 機種の系統（ジャグラー・大都・サミー…）。1機種が複数に入ってよい |
| `data/machine_types.json` | ノーマルAタイプの機種。ここに無ければAT機 |
| `data/schedule.json` | 店長ポストで判明した、日付ルールと食い違う日 |

**設定ファイルは毎朝の再生成を生き延びる。**直したい結果があるときは、
生成物を触るのではなく必ずこちら側に書く。

### 生成物（触らない）

`raw.json` / `data/records.json` / `data/canon.json` / `data/machines.json` /
`data/index.json` / `data/lineup.json` / `data/events.json` / `data/lead.json` /
`data/token_readings.json` / `data/machine_variants.txt` / `data/matsuwaru.{json,csv}` /
`<店舗id>/*.html` `sw.js` `manifest.webmanifest`

---

## 4. データの形

### `raw.json`（正本・記事1本＝1要素）

```jsonc
{
  "articleUrl": "https://.../entry/2026/09/01/074936",
  "articleDate": "2026-09-01",   // 記事が出た日
  "targetDate":  "2026-08-31",   // 全系が実施された営業日（タイトルの「8月31日」から）
  "postDate":    "2026-08-30",   // 示唆ポストの日
  "tenchou": "@endo1maruhan", "tweetUrl": "https://x.com/.../status/...",
  "title": "8月31日の…まとめ✏️月末は圧巻の全系仕掛け！",
  "results": [ {"machine":"ゴッドイーター","plus":7,"total":13,"avg":4285} ],
  "assoc":   [ {"machine":"ゴッドイーター","matched":true,
                "keyword":"GETSUMATSU","chain":["GETSUMATSU","GE","ゴッドイーター"],
                "raw":"GETSUMATSU→GE→ゴッドイーター","result":{...}} ],
  "unassigned": [],              // 機種に結び付けられなかった連想
  "events": []                   // 記事から検出した不定期イベント名
}
```

### `data/index.json`（検索画面）

配列を短くするため**位置で持つ**。1レコードは

```
[記事番号, 機種番号, 連想の配列, plus, total, avg, その他フラグ, 種類]
  r[6]=1 なら機種以外の示唆（末尾・設置台数など）
  r[7]  0=本文 1=画像 2=日付・記念日 3=投稿時刻 4=来店・イベント
```

画面側で `r[8]=正規化トークン` と `r[9]=そのひらがな読み` を足す。
`machines` `readings` `treads`（語→読みの一覧）`articles` が同梱される。

### `data/events.json`（イベント傾向ページ）

`events[]`（イベントごとの集計）、`thisMonth`（今月の実施状況）、
`sizeAll` / `groupsAll` / `normAll` / `variAll`（全体の基準値）など。

### `data/lead.json`（トップのカード）

イベントごとに `say`（傾向の1文）と `top`（上位3機種）だけを持つ軽い版。
`schedule` も入っていて、日付からその日のイベントを引ける。

---

## 5. まつわるチェッカー（検索画面）の仕様

- **検索対象**は連想の各語と機種名。`NFKC` 正規化 → 小文字化 → 空白除去 → **カタカナをひらがなに**。
  さらに **漢字語にひらがな読みを付けてある**ので「人参」を「にんじん」でも引ける。
- **数字だけの検索**は前後に数字が来ない位置だけ当てる（「1080円」の1を拾わないため）。
- **並び順は日付の新しい順**。関連度順にすると帯が変わるたび日付が巻き戻って混乱するため、
  同じ日の中だけ関連度順にしている。
- **タブ**は示唆の出どころ（本文・画像／日付・記念日／投稿時刻／来店／末尾系）。
- **トップのカード**（`lead.json`）は、その日のイベントの傾向を出して `/events` へ送る導線。
  20:30を過ぎると翌日ぶんに切り替わる。✕で**その日ぶんだけ**消せる（localStorage）。
  順位は**回数が同じなら同じ順位**（1・1・1／1・2・2／1・1・3）。
- **メモ**は端末内だけ（localStorage）。どこにも送らない。
- 読み込み中は**骨組み**を出して高さを先に取る（CLS対策。`min-height:102vh` で
  後ろの中身が必ず画面の外から始まるようにしてある）。

## 6. イベント傾向チェッカーの仕様

- タブは**イベント傾向**と**月間全系実施機種**の2つ。
- イベントは `event_defs.json` の順に出る。`match` の書き方は
  `digit`（日付の末尾）／`day`（その日）／`monthend`（月末最終日）／`irregular`（記事から検出）。
- **同じ日に複数当てはまるときは、細かいほうだけを数える。**
  優先順位は 不定期イベント > 特別な日 > ◯のつく日。
  上位のイベントがある日は、下位のイベントの**母数からも外す**
  （23日は21-27WEEKなので「3のつく日」には数えない）。
- **順位は同率を同率として出す**（`ranked()`）。22%が5機種並ぶ日に順位だけ違うと誤解を招くため。
- 傾向文は「結論 → 根拠 → 結論」で組む。根拠はいちばん効いている軸から。
  **全体との差が8ポイント未満の軸は書かない**（`DIFF_MIN`。誤差の範囲なので）。
- 手で書いたリード文（`event_lead.json`）があればそちらが優先。文中の `{山佐}` は
  その系統の代表機種に置き換わる（その系統が入った日の**半分以上**を1機種が占めるときだけ）。
- **月間全系実施機種**は、現行の設置機種と突き合わせて「今月まだ来ていない機種」を出す。
  たたんであり、押すと全件開く。並びは全系になった回数の多い順。

## 7. 集計で外さないための決めごと

- **バラも全系に含める。**記事タイトルは「全系6機種+バラ3機種」と分けて書かれ、
  結果欄（台数つき）に載るのが全系、連想の見出しにだけ出るのがバラ。
  全体の15.7%が後者で、その68%が1台構成。**どちらも全系として数えるのが正しい。**
- **台数の出どころは2つ。**ブログ各記事の実測と、店舗公式の設置機種ページ（取得日つき）。
  **日付がいちばん近いほうを使う。**
- **同数のときの選び方は必ず決め打ちにする。**`most_common()` は同数だと集合の並び順で決まり、
  Pythonの文字列ハッシュが実行ごとに変わるため、同じデータでも答えが変わる。
  **回数の多い順 → いまの設置台数の多い順 → 機種名順**で固定する。
- 台数帯は 多=20台以上／中=10〜19台／小=9台以下。

---

## 8. 新しい店舗（エスパス歌舞伎）を足すには

**結論から言うと、画面は設定だけで生えるが、データを取る部分は作り直しになる。**

### すぐ済むこと

`stores.json` に1件足して `python3 src/build-pages.py` を回すだけで、
`/matsuwaru/<新id>/` と `/matsuwaru/<新id>/events` のページ一式と、
店舗一覧へのカードが生成される。**画面のコードは1行も書かなくていい。**

```jsonc
{
  "id": "kabuki",                        // URLになる
  "title": "全台系まつわるチェッカー",
  "label": "エスパス歌舞伎",              // 見出しの横のバッジ
  "store": "エスパス日拓新宿歌舞伎町店",
  "blogName": "…", "blogUrl": "https://…/",
  "since": "YYYY-MM-DD",                 // 示唆の癖が変わる区切り（店長交代日など）
  "sinceNote": "⚠️ 検索できるデータは…",
  "example": "会議",                      // いまはどこからも参照されていない（残骸）
  "version": 4,                          // sw.js のキャッシュ名 matsuwaru-<id>-v<version> になる
  "lineupUrl": "…", "lineupName": "…"     // 無ければ省略可（未実施リストが弱くなるだけ）
}
```

`events.py` `finalize.py` `build.py` `kana.py` は**店舗に依存していない**ので、
そのまま動く。設定ファイルさえ揃えば集計まで通る。

### 作り直しになること

**① 記事の解析（`lib.py`）。ここが最大の作業。**
いまの `parse_html()` は、このブログの書き方に強く合わせてある。

- **はてなブログ前提**：本文を `<div class="entry-content">` から `<footer>` までで切り出す
- **記事URLがハードコード**：`'https://sloslo-blog.hatenablog.com/entry/' + ent`
  → **`stores.json` の `blogUrl` を使うよう直すのが最初の一手**
- **署名行で記事を上下に割る**：`— 名前 (@id) 2026年8月30日` の行を境に、
  上が結果欄、下が連想。この行が無い形式だと何も取れない
- **結果欄の見つけ方**：`+7/13台` `平均4,285枚` の行を見つけ、**その3行前までを機種名とみなす**
- **連想の見つけ方**：矢印（`→ ➡ 👉 ⇒`）の有無だけで見出しと連鎖を判定。
  「・」の意味が記事ごとに反転するので、記事単位で判定し直している
- **タイトルから対象日**：`8月31日の…` を正規表現で読む
- **不定期イベント名が東宝固有**：`IRREGULAR`（あかまる取材・ダンち・エグち・
  やばたにえん・東京大戦）

**別のブログなら、この関数は書き直しになる可能性が高い。**
店舗ごとに解析器を差し替えられる形（`stores.json` に `parser` を書いて `lib_<name>.py` を
呼ぶなど）に変えるのが素直。**いまは1店舗しかないので、その仕組みはまだ無い。**

**② 記事の見つけ方（`sync.py`）。**
`<blogUrl>/sitemap.xml` の `periodical` を含むサブマップを直近2つだけ読む、という
はてな特有の形。別サービスなら差し替えがいる。

**③ 設置機種の取得（`lineup.py`）。**
マルハン公式の `<div class="kisyu-tab slot">` `<div class="kisyu-item">機種名(N台)</div>` を
正規表現で読んでいる。**エスパスのサイトは作りが違うので、ここも書き直し。**
`lineupUrl` を書かなければ取得ごと飛ばせる（撤去済みの機種が「未実施」に残るだけで、
検索とイベント傾向は動く）。

**④ 設定ファイル一式をゼロから作る。**
とくに `event_defs.json`（その店のイベントの日付ルール）と
`machine_groups.json`（系統）は、店ごとに中身がまったく違う。
`decisions.json`（名寄せ）と `readings.json` は、記事を数十本入れてから
`data/machine_variants.txt`（表記ゆれ候補）を見ながら育てる。

### 進め方の目安

1. `stores.json` に足して `build-pages.py` → **空のページが出ることを確認**
2. 記事を数本、手で `cache/<新id>/` に置いて `parse.py <新id>` → **解析器を合わせ込む**
3. `build.py` → `data/machine_variants.txt` を見て `decisions.json` を作る
4. `finalize.py` まで通す → **検索画面が動く**（ここがひとまずの完成）
5. `event_defs.json` を書いて `events.py` → イベント傾向が出る
6. `lineup.py` を新しいサイト向けに書く（後回しでよい）
7. `sync.py` を新しいブログ向けに直し、GitHub Actions のループに入れる
   （ワークフローは `stores.json` の全店舗をまわす作りなので**変更不要**）

---

## 9. 運用

- **自動更新**：GitHub Actions `matsuwaru-daily.yml`。`stores.json` の全店舗をまわし、
  差分があればコミット＆Cloudflare Pages へデプロイ。
  `pip install -r matsuwaru/requirements.txt`（pykakasi）は `continue-on-error: true` で、
  入らなくても更新は止まらない。
- **起動**：GitHub の cron は10時間以上ずれることがあったため、
  **Cloudflare Worker（`/Users/Shared/kabaneri-counter/dispatch-worker/`・リポジトリ外）**の
  定時実行から `workflow_dispatch` を叩いている。08:10 / 09:10 / 10:10 / 13:10 JST。
  GitHub側のcronも保険として残してある。
- **ブログの投稿時刻**は中央値 07:49、6〜10時台に散る。**08:10時点でまだ出ていない日が26%**ある。
- **異常時**：`sync.py` は終了コード1で落ちる（サイトマップが取れない／連想が0件／
  最新記事が3日以上前）。Actionsの失敗通知で気づく作り。
- **Cloudflare**：プロジェクト名は `kabaneri-counter`（`minnanoslot.com` を担当）。
  名前は変えられない仕様なので、そのままにしている（経緯はリポジトリ直下の `README.md`）。

## 10. ハマった落とし穴

- **未pushのまま自動更新が走ると、全部巻き戻る。**（実際に24コミット消えた）
- **`most_common()` は同数だと実行ごとに答えが変わる。**必ず決め打ちの並びにする。
- **`set` の並び順に依存しない。**読みの照合順も長いものから、と明示している。
- **6/30 は「0のつく日」と「月末最終日」の両方に当たる。**日付ぴったりのイベントを優先する。
- **記事は翌朝公開なので、本文の「本日」は対象日の翌日を指すことがある。**
  不定期イベントの誤検出はここから来る（`event_fixes.json` で直す）。
- **公式の表記とブログの表記は濁点1つで違うことがある**（ビック／ビッグドリーム）。
  照合が静かに外れるので、`readings.json` に別名を足す。
- **新旧2機種が両方設置されていることがある**（ヴァルヴレイヴ 2jF 41台 / D 5台）。
  片方を「対象外」にすると、もう片方の枠が「一度も全系になっていない」に落ちる。
  `限定` で1枠ずつに固定する。**設置枠の数と機種の数が1対1になるかが検算になる。**
- **一覧に決め打ちの上限を置かない。**`slice(0,20)` で切っていたせいで、
  82機種のうち20機種しか出ていないことに誰も気づけなかった。
- **アーティファクト（公開ページ）内では `confirm` / `alert` が効かない。**確認UIは自前で作る。
