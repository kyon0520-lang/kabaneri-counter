# -*- coding: utf-8 -*-
"""cache/*.html から raw.json を全再構築（通常は sync.py を使う）"""
import glob, json, os
from lib import parse_html
import sys, os, json as _json
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'toho'
_cfg = [s for s in _json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg: raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = _os.path.join(_ROOT, STORE)
CACHE = _os.path.join(_ROOT, 'cache', STORE)
out = []
for f in sorted(glob.glob(CACHE + '/*.html')):
    out.append(parse_html(open(f, encoding='utf-8', errors='replace').read(),
                          os.path.basename(f).replace('.html', '')))
json.dump(out, open(B + '/raw.json', 'w'), ensure_ascii=False, indent=1)
print('記事 %d件 / 全系機種 %d件 / 連想 %d件' % (len(out),
      sum(len(a['results']) for a in out), sum(len(a['assoc']) for a in out)))
