# -*- coding: utf-8 -*-
"""cache/*.html から raw.json を全再構築（通常は sync.py を使う）"""
import glob, json, os
from lib import parse_html
B = os.path.dirname(os.path.abspath(__file__))
out = []
for f in sorted(glob.glob(B + '/cache/*.html')):
    out.append(parse_html(open(f, encoding='utf-8', errors='replace').read(),
                          os.path.basename(f).replace('.html', '')))
json.dump(out, open(B + '/raw.json', 'w'), ensure_ascii=False, indent=1)
print('記事 %d件 / 全系機種 %d件 / 連想 %d件' % (len(out),
      sum(len(a['results']) for a in out), sum(len(a['assoc']) for a in out)))
