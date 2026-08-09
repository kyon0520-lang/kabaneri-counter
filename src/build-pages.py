#!/usr/bin/env python3
"""src/index.html と src/manual.html から、公開用のファイルを作り直す。

原本を編集したら実行して同期させる:
    python3 src/build-pages.py

公開用だけに入るもの:
  - PWA/OGP のメタタグ
  - サービスワーカーの登録（その場描きアイコンの処理と入れ替え）
  - Cloudflare Web Analytics の計測タグ
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))       # src/
PUB = os.path.dirname(BASE)                             # 公開ディレクトリ
SRC = os.path.join(BASE, 'index.html')
DEST = os.path.join(PUB, 'kabaneri-unato', 'index.html')
MAN_SRC = os.path.join(BASE, 'manual.html')
MAN_DEST = os.path.join(PUB, 'kabaneri-unato', 'manual.html')

SITE = 'https://minnanoslot.com/kabaneri-unato/'

HEAD_ADD = f'''<link rel="manifest" href="./manifest.webmanifest">
<link rel="apple-touch-icon" href="./apple-touch-icon.png">
<link rel="icon" type="image/png" href="./icon-192.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="みんなのスロット">
<meta property="og:title" content="カバネリ CZ発光カウンター">
<meta property="og:description" content="非発光1pt・発光15ptで数えて、平均発光率とCZ 1回あたりの平均ポイントを自動計算。スマホでそのまま使えます。">
<meta property="og:url" content="{SITE}">
<meta property="og:image" content="{SITE}ogp.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="カバネリ CZ発光カウンター">
<meta name="twitter:description" content="非発光1pt・発光15ptで数えて、平均発光率とCZ 1回あたりの平均ポイントを自動計算。">
<meta name="twitter:image" content="{SITE}ogp.png">
'''

SW_REG = '''/* ---------- オフライン対応（サービスワーカー） ---------- */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}

'''

# Cloudflare Web Analytics。公開版だけに入れる（アーティファクトでは外部読み込みが弾かれるため）
BEACON_TOKEN = 'c71c6cecd8e04f668c0d4b7e50d706da'
BEACON = (
    '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
    "data-cf-beacon='{\"token\": \"" + BEACON_TOKEN + "\"}'></script>\n"
)

TITLE = '<title>カバネリ CZ発光カウンター</title>'
ICON_BLOCK_START = '/* ---------- iOS ホーム画面用のアイコンと名前 ---------- */'
ICON_BLOCK_END = 'setupHomeScreen();\n'


def build_app():
    src = open(SRC, encoding='utf-8').read()

    assert TITLE in src, 'title タグが見つかりません'
    out = src.replace(TITLE, HEAD_ADD + TITLE, 1)

    # 実ファイルのアイコンを使うので、その場描きのアイコン登録だけを差し替える
    # （範囲を広く取ると、あいだに書いた処理まで消えるので終端を明示する）
    start = out.index(ICON_BLOCK_START)
    end = out.index(ICON_BLOCK_END, start) + len(ICON_BLOCK_END)
    out = out[:start] + SW_REG.rstrip('\n') + '\n' + out[end:]

    if 'cloudflareinsights' not in out:
        out = out.replace('</body>', BEACON + '</body>', 1)

    open(DEST, 'w', encoding='utf-8').write(out)
    print(f'書き出し: {DEST}')


def build_manual():
    if not os.path.exists(MAN_SRC):
        return
    man = open(MAN_SRC, encoding='utf-8').read()
    if 'cloudflareinsights' not in man:
        man = man.rstrip() + '\n' + BEACON
    open(MAN_DEST, 'w', encoding='utf-8').write(man)
    print(f'書き出し: {MAN_DEST}')


if __name__ == '__main__':
    build_app()
    build_manual()
    print(f'公開URL: {SITE}')
