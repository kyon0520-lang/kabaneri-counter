# -*- coding: utf-8 -*-
"""stores.json をもとに、店舗ごとのページ一式を生成する。
   原本は src/app.html と src/manifest.webmanifest と src/sw.js。
   生成物（<店舗id>/index.html など）は直接編集しないこと。"""
import json, os, re, shutil, html

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(B, 'src')
cfg = json.load(open(os.path.join(B, 'stores.json'), encoding='utf-8'))['stores']

app = open(os.path.join(SRC, 'app.html'), encoding='utf-8').read()
evp = open(os.path.join(SRC, 'events.html'), encoding='utf-8').read()
man = open(os.path.join(SRC, 'manifest.webmanifest'), encoding='utf-8').read()
sw  = open(os.path.join(SRC, 'sw.js'), encoding='utf-8').read()

def fill(t, s):
    for k, v in s.items():
        t = t.replace('{{%s}}' % k.upper(), html.escape(str(v), quote=False) if isinstance(v, str) else str(v))
    return t

for s in cfg:
    d = os.path.join(B, s['id'])
    os.makedirs(os.path.join(d, 'data'), exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(fill(app, s))
    open(os.path.join(d, 'events.html'), 'w', encoding='utf-8').write(fill(evp, s))
    open(os.path.join(d, 'manifest.webmanifest'), 'w', encoding='utf-8').write(fill(man, s))
    open(os.path.join(d, 'sw.js'), 'w', encoding='utf-8').write(fill(sw, s))
    for ic in os.listdir(os.path.join(SRC, 'icons')):
        shutil.copy2(os.path.join(SRC, 'icons', ic), os.path.join(d, ic))
    print('生成: /matsuwaru/%s/  (%s)' % (s['id'], s['store']))

# 店舗一覧
cards = '\n'.join(
    '''      <a class="store" href="./%s/">
        <span class="nm">%s</span>
        <span class="sub">%s</span>
      </a>''' % (s['id'], html.escape(s['store']), html.escape(s['title'])) for s in cfg)
idx = open(os.path.join(SRC, 'stores.html'), encoding='utf-8').read().replace('{{CARDS}}', cards)
open(os.path.join(B, 'index.html'), 'w', encoding='utf-8').write(idx)
print('生成: /matsuwaru/  (店舗一覧 %d件)' % len(cfg))
