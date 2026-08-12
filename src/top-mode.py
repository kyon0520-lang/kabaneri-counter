#!/usr/bin/env python3
"""トップページを「準備中」と「本編」で切り替える。

    python3 src/top-mode.py soon   # 準備中の画面にする
    python3 src/top-mode.py full   # 本編に戻す
    python3 src/top-mode.py        # いまどちらかを見る

本編の原本は src/top.html。ここだけを編集すること。
公開される index.html は、このスクリプトが書き出す。

準備中にする理由：カウンター単体を先に配りたいが、
「みんなのスロット」の説明（実戦データを持ち寄る話）はまだ出せる状態にない。
本編には送信機能の記述が残っているので、実態とも食い違う。
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))       # src/
PUB = os.path.dirname(BASE)
FULL = os.path.join(BASE, 'top.html')
DEST = os.path.join(PUB, 'index.html')

MARK = '<!-- 準備中の画面（src/top-mode.py が書き出す。直接編集しない） -->'

# ロゴマークは本編と同じものを使う。ここだけ別の絵にすると、
# カウンター側から来た人に別サイトに見える
SOON = MARK + '''
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#fdfdfd">
<title>みんなのスロット</title>
<meta name="description" content="パチスロを打ちながら数えるカウンターを作っています。">
<meta property="og:type" content="website">
<meta property="og:site_name" content="みんなのスロット">
<meta property="og:title" content="みんなのスロット">
<meta property="og:description" content="パチスロを打ちながら数えるカウンターを作っています。">
<meta property="og:url" content="https://minnanoslot.com/">
<link rel="icon" type="image/png" href="./kabaneri-unato/icon-192.png">
<link rel="apple-touch-icon" href="./kabaneri-unato/apple-touch-icon.png">
<style>
  :root{
    --bg:#fdfdfd; --ink:#26262a; --ink-2:#5c6270; --ink-3:#8d94a3;
    --line:#e6e9ef; --accent:#2f7cf6; --accent-soft:#e4efff;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html{background:var(--bg)}
  body{
    margin:0;background:var(--bg);color:var(--ink);
    font-family:"Hiragino Sans","Hiragino Kaku Gothic ProN",-apple-system,BlinkMacSystemFont,
                "Noto Sans JP","Yu Gothic",Meiryo,sans-serif;
    font-size:14px;line-height:1.9;letter-spacing:.02em;
    -webkit-font-smoothing:antialiased;
    min-height:100svh;display:flex;flex-direction:column;justify-content:center;
  }
  .wrap{width:100%;max-width:600px;margin:0 auto;padding:48px 24px}
  .logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;letter-spacing:.04em}
  .logo .mk{width:22px;height:35px;flex:0 0 auto;display:block;color:var(--ink)}
  .tag{
    display:inline-block;margin:34px 0 0;font-size:11px;font-weight:700;letter-spacing:.18em;
    color:var(--accent);background:var(--accent-soft);border-radius:999px;padding:6px 14px;
  }
  h1{margin:16px 0 0;font-weight:700;font-size:clamp(22px,6vw,30px);line-height:1.6;letter-spacing:.03em}
  p{margin:14px 0 0;color:var(--ink-2);max-width:32em}
  .go{
    display:inline-flex;align-items:center;gap:8px;margin:30px 0 0;text-decoration:none;
    background:var(--accent);color:#fff;font-weight:700;font-size:14px;
    padding:14px 26px;border-radius:999px;letter-spacing:.04em;
    transition:opacity .2s,transform .2s;
  }
  .go:active{transform:scale(.97)}
  @media (hover:hover){.go:hover{opacity:.85}}
  .note{margin:38px 0 0;padding-top:22px;border-top:1px solid var(--line);
        font-size:11.5px;color:var(--ink-3)}
</style>
</head>
<body>

<svg style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true" focusable="false">
  <symbol id="mk" viewBox="0 0 60 96">
    <g transform="translate(30,48)">
      <g transform="translate(0,-34) rotate(-8)" fill="none" stroke="#2f7cf6" stroke-width="4" stroke-linecap="round">
        <path d="M -26 6 A 26 10 0 0 0 26 6"></path>
        <line x1="-26" y1="0" x2="-26" y2="6"></line>
        <line x1="26" y1="0" x2="26" y2="6"></line>
        <ellipse rx="26" ry="10"></ellipse>
      </g>
      <g fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round">
        <ellipse rx="22" ry="8"></ellipse>
        <line x1="-22" y1="0" x2="-22" y2="4.6"></line>
        <line x1="22" y1="0" x2="22" y2="4.6"></line>
        <path d="M -22 4.6 A 22 8 0 0 0 22 4.6"></path>
        <line x1="-24" y1="4.6" x2="-24" y2="11"></line>
        <line x1="20" y1="4.6" x2="20" y2="11"></line>
        <path d="M -24 11 A 22 8 0 0 0 20 11"></path>
        <line x1="-21" y1="11" x2="-21" y2="15.2"></line>
        <line x1="23" y1="11" x2="23" y2="15.2"></line>
        <path d="M -21 15.2 A 22 8 0 0 0 23 15.2"></path>
        <line x1="-24" y1="15.2" x2="-24" y2="21.4"></line>
        <line x1="20" y1="15.2" x2="20" y2="21.4"></line>
        <path d="M -24 21.4 A 22 8 0 0 0 20 21.4"></path>
        <line x1="-21" y1="21.4" x2="-21" y2="26.2"></line>
        <line x1="23" y1="21.4" x2="23" y2="26.2"></line>
        <path d="M -21 26.2 A 22 8 0 0 0 23 26.2"></path>
        <line x1="-23" y1="26.2" x2="-23" y2="31.6"></line>
        <line x1="21" y1="26.2" x2="21" y2="31.6"></line>
        <path d="M -23 31.6 A 22 8 0 0 0 21 31.6"></path>
        <line x1="-22" y1="31.6" x2="-22" y2="36"></line>
        <line x1="22" y1="31.6" x2="22" y2="36"></line>
        <path d="M -22 36 A 22 8 0 0 0 22 36"></path>
      </g>
    </g>
  </symbol>
</svg>

<div class="wrap">
  <div class="logo"><svg class="mk" viewBox="0 0 60 96" aria-hidden="true"><use href="#mk"></use></svg>みんなのスロット</div>

  <span class="tag">COMING SOON</span>
  <h1>準備中です。</h1>
  <p>パチスロを打ちながら数えるカウンターを作っています。<br>いまはカバネリの1機種だけ、先に公開しています。</p>

  <a class="go" href="./kabaneri-unato/">カバネリ海門カウンターを開く</a>

  <p class="note">数値は自分で数えた記録にもとづくもので、設定を保証するものではありません。</p>
</div>

<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token": "c71c6cecd8e04f668c0d4b7e50d706da"}'></script>
</body>
</html>
'''


def current_mode():
    if not os.path.exists(DEST):
        return '（index.html がありません）'
    return 'soon' if MARK in open(DEST, encoding='utf-8').read() else 'full'


def write(mode):
    if mode == 'soon':
        out = SOON
    else:
        out = open(FULL, encoding='utf-8').read()
        assert MARK not in out, 'src/top.html が準備中の画面になっています。原本を確認してください'
    open(DEST, 'w', encoding='utf-8').write(out)
    print(f'index.html を書き出しました: {"準備中" if mode == "soon" else "本編"}')
    print('公開するには: npx wrangler pages deploy . --project-name=kabaneri-counter --branch=main')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg in ('soon', 'full'):
        write(arg)
    elif arg:
        sys.exit('使い方: python3 src/top-mode.py [soon|full]')
    else:
        print(f'いまのトップページ: {current_mode()}')
        print('切り替え: python3 src/top-mode.py soon / full')
