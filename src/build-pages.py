#!/usr/bin/env python3
"""src/index.html と src/manual.html から、公開用のファイルを作り直す。

原本を編集したら実行して同期させる:
    python3 src/build-pages.py

公開用だけに入るもの:
  - PWA/OGP のメタタグ
  - サービスワーカーの登録（その場描きアイコンの処理と入れ替え）
  - Cloudflare Web Analytics の計測タグ

機能フラグを False にすると、その機能を原本から外した版を書き出す（原本は触らない）。
戻すときは True にして、もう一度実行するだけ。

  SEND_ENABLED  … みんなのスロットへの送信・会員登録・読み出し・マイページ
  WINS_ENABLED  … 当選履歴カウンター（左端の「当選」つまみごと）
  CYCLE_ENABLED … 当選履歴の中の周期カウンター（何周期目・周期到達・周期別の当選率）

CYCLE は WINS の中に入っている。WINS を False にすれば周期も一緒に消えるので、
CYCLE を単体で False にするのは「当選履歴は残すが周期だけやめる」ときだけ。
"""
import os
import re

# ---- 公開版に含める機能 ----
SEND_ENABLED = False
WINS_ENABLED = False
CYCLE_ENABLED = False

# 内側（CYCLE）から順に処理する
FEATURES = {'SEND': SEND_ENABLED, 'CYCLE': CYCLE_ENABLED, 'WINS': WINS_ENABLED}

# 原本に置いた印。CSS/JS は /* */、HTML は <!-- --> で囲む
#   ==NAME:START==  〜 ==NAME:END==   … その機能を含めるときだけ残る
#   ==NAME!:START== 〜 ==NAME!:END==  … 含めないときだけ残る（差し替え文言に使う）
COMMENTS = [('/* ', ' */'), ('<!-- ', ' -->')]

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
<meta property="og:title" content="カバネリ海門カウンター">
<meta property="og:description" content="非発光1pt・発光15ptで数えて、平均発光率とCZ 1回あたりの平均ポイントを自動計算。スマホでそのまま使えます。">
<meta property="og:url" content="{SITE}">
<meta property="og:image" content="{SITE}ogp.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="カバネリ海門カウンター">
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

TITLE = '<title>カバネリ海門カウンター</title>'
ICON_BLOCK_START = '/* ---------- iOS ホーム画面用のアイコンと名前 ---------- */'
ICON_BLOCK_END = 'setupHomeScreen();\n'


def _strip(html, start, end, keep):
    """印で囲んだ範囲を、keep なら印だけ外し、そうでなければ中身ごと消す"""
    while start in html:
        i = html.index(start)
        assert end in html[i:], f'{start} に対応する {end} がありません'
        j = html.index(end, i)
        inner = html[i + len(start):j] if keep else ''
        html = html[:i] + inner + html[j + len(end):]
    assert end not in html, f'{end} が余っています。印の対が合っていません'
    return html


def apply_flags(html):
    """機能ごとの印を処理する。原本には手を触れず、書き出す側だけを削る"""
    for name, on in FEATURES.items():
        for a, b in COMMENTS:
            html = _strip(html, f'{a}=={name}:START=={b}', f'{a}=={name}:END=={b}', on)
            html = _strip(html, f'{a}=={name}!:START=={b}', f'{a}=={name}!:END=={b}', not on)
    # 外したはずのものが残っていたら、そこで気づけるようにする
    if not SEND_ENABLED:
        assert '/api/records' not in html, '送信の呼び出しが残っています'
    if not CYCLE_ENABLED:
        assert 'wincycle' not in html, '周期チップの参照が残っています'
        assert 'cycleTable' not in html, '周期別の表が残っています'
    if not WINS_ENABLED:
        assert 'winpanel' not in html, '当選履歴パネルの参照が残っています'
        assert 'renderWins' not in html, '当選履歴の描画が残っています'
    return html


def renumber_manual(html):
    """章を消したあとに、番号・id・目次を振り直す。
    手で直すと必ずどこか取り残すので、見出しから作り直す"""
    secs = re.findall(r'<section id="s\d+">\s*<h2><span class="n">\d+</span>(.*?)</h2>', html)

    def sec(m, n=[0]):
        n[0] += 1
        return f'<section id="s{n[0]}">\n    <h2><span class="n">{n[0]}</span>'
    html = re.sub(r'<section id="s\d+">\s*<h2><span class="n">\d+</span>', sec, html)

    items = '\n'.join(
        f'      <li><a href="#s{i}"><span class="tn">{i}</span>{t}</a></li>'
        for i, t in enumerate(secs, 1))
    html = re.sub(r'(<nav class="toc">.*?<ol>\n).*?(\n    </ol>)',
                  lambda m: m.group(1) + items + m.group(2), html, flags=re.S)

    # 本文中の「◯章」のような参照は使っていない前提。残っていたら気づけるようにする
    assert '#s0' not in html
    return html


def build_app():
    src = open(SRC, encoding='utf-8').read()
    src = apply_flags(src)

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
    man = apply_flags(man)
    man = renumber_manual(man)
    if 'cloudflareinsights' not in man:
        man = man.rstrip() + '\n' + BEACON
    open(MAN_DEST, 'w', encoding='utf-8').write(man)
    print(f'書き出し: {MAN_DEST}')


if __name__ == '__main__':
    build_app()
    build_manual()
    for name, on in FEATURES.items():
        print(f'{name}: {"あり" if on else "なし"}')
    print(f'公開URL: {SITE}')
