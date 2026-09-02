# -*- coding: utf-8 -*-
"""cache/<店>/*.json から raw.json を全再構築する（source=wp の店舗用）。
   ネットに触らないので、解析器を直したあとの作り直しはこれで足りる。
   はてなの店舗は parse.py を使う。"""
import json, os, sys, importlib

_ROOT = os.path.dirname(os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'kabuki'
_cfg = [s for s in json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg:
    raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = os.path.join(_ROOT, STORE)
CACHE = os.path.join(_ROOT, 'cache', STORE)

parse_post = importlib.import_module('lib_' + CONF['parser']).parse_post
IRR_PATH = os.path.join(B, 'data', 'irregular.json')
IRREGULAR = []
if os.path.exists(IRR_PATH):
    IRREGULAR = json.load(open(IRR_PATH, encoding='utf-8'))['irregular']
_FL = os.path.join(B, 'data', 'floors.json')
FLOORS = json.load(open(_FL, encoding='utf-8'))['split'] if os.path.exists(_FL) else None

raw, skipped = [], 0
for fn in sorted(os.listdir(CACHE)):
    if not fn.endswith('.json'):
        continue
    p = json.load(open(os.path.join(CACHE, fn), encoding='utf-8'))
    if p['date'][:10] < CONF['since']:
        continue
    a = parse_post(p, CONF, IRREGULAR, FLOORS)
    if not a['targetDate']:
        skipped += 1
        continue
    raw.append(a)

raw.sort(key=lambda a: a['articleDate'])
json.dump(raw, open(B + '/raw.json', 'w'), ensure_ascii=False, indent=1)
print('再構築: %d件（対象日が読めずスキップ %d件） 期間 %s〜%s'
      % (len(raw), skipped, raw[0]['targetDate'], raw[-1]['targetDate']))
print('  連想 %d件 / 全台系 %d行 / 高配分(正本のみ) %d行'
      % (sum(len(a['assoc']) for a in raw), sum(len(a['results']) for a in raw),
         sum(len(a.get('highShare', [])) for a in raw)))
