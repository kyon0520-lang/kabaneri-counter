# -*- coding: utf-8 -*-
"""stores.json をもとに、店舗ごとのページ一式を生成する。
   原本は src/app.html と src/manifest.webmanifest と src/sw.js。
   生成物（<店舗id>/index.html など）は直接編集しないこと。"""
import json, os, re, shutil, html, subprocess, sys

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(B, 'src')
cfg = json.load(open(os.path.join(B, 'stores.json'), encoding='utf-8'))['stores']

app = open(os.path.join(SRC, 'app.html'), encoding='utf-8').read()
evp = open(os.path.join(SRC, 'events.html'), encoding='utf-8').read()
news = open(os.path.join(SRC, 'news.html'), encoding='utf-8').read()
man = open(os.path.join(SRC, 'manifest.webmanifest'), encoding='utf-8').read()
sw  = open(os.path.join(SRC, 'sw.js'), encoding='utf-8').read()

# 「このツールについて」の読み物への案内。読み物（/column/）は東宝向けなので、
# stores.json で columns:true の店舗だけに出す
ABOUT_GUIDE = {
    'app': """      <dt>使い方をもっと詳しく知りたい</dt>
      <dd><a href="/column/matsuwaru-guide">全台系まつわるチェッカーの使い方</a>にまとめています。</dd>
""",
    'events': """      <dt>集計結果をもっと詳しく知りたい</dt>
      <dd><a href="/column/events-guide">イベント傾向チェッカーの見かた</a>や、<a href="/column/toho-event-medals">イベントごとの平均差枚</a>にまとめています。</dd>
""",
}
def guide(t, kind, s):
    return t.replace('{{ABOUT_GUIDE}}', ABOUT_GUIDE[kind] if s.get('columns') else '')

def fill(t, s):
    for k, v in s.items():
        t = t.replace('{{%s}}' % k.upper(), html.escape(str(v), quote=False) if isinstance(v, str) else str(v))
    return t

for s in cfg:
    d = os.path.join(B, s['id'])
    os.makedirs(os.path.join(d, 'data'), exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(fill(guide(app, 'app', s), s))
    open(os.path.join(d, 'events.html'), 'w', encoding='utf-8').write(fill(guide(evp, 'events', s), s))
    open(os.path.join(d, 'news.html'), 'w', encoding='utf-8').write(fill(news, s))
    open(os.path.join(d, 'manifest.webmanifest'), 'w', encoding='utf-8').write(fill(man, s))
    open(os.path.join(d, 'sw.js'), 'w', encoding='utf-8').write(fill(sw, s))
    for ic in os.listdir(os.path.join(SRC, 'icons')):
        shutil.copy2(os.path.join(SRC, 'icons', ic), os.path.join(d, ic))
    print('生成: /matsuwaru/%s/  (%s)' % (s['id'], s['store']))

# 店舗一覧（public:false の店舗はページ自体は生成するが一覧には出さない＝ソフトローンチ）
cards = '\n'.join(
    '''      <a class="store" href="./%s/">
        <span class="nm">%s</span>
        <span class="sub">%s</span>
      </a>''' % (s['id'], html.escape(s['store']), html.escape(s['title']))
    for s in cfg if s.get('public', True))
idx = open(os.path.join(SRC, 'stores.html'), encoding='utf-8').read().replace('{{CARDS}}', cards)
open(os.path.join(B, 'index.html'), 'w', encoding='utf-8').write(idx)
print('生成: /matsuwaru/  (店舗一覧 %d件)' % len(cfg))

# 「明日は何の日」データ（全店舗共通）。失敗しても非致命なので戻り値は見ない
subprocess.run([sys.executable, os.path.join(B, 'todayis.py')])
