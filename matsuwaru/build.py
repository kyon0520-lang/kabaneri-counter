# -*- coding: utf-8 -*-
import json, csv, re, unicodedata, collections, os
import sys, os, json as _json
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'toho'
_cfg = [s for s in _json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg: raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = _os.path.join(_ROOT, STORE)
CACHE = _os.path.join(_ROOT, 'cache', STORE)
d=json.load(open(B+'/raw.json'))
os.makedirs(B+'/data',exist_ok=True)

def norm(s):
    s=unicodedata.normalize('NFKC',s or '')
    return re.sub(r'[\s　]+','',s).lower()

recs=[]
for art in d:
    for i,a in enumerate(art['assoc']):
        recs.append({
            'id': '%s-%02d'%(art['targetDate'],i),
            'targetDate': art['targetDate'],       # 全台系が実施された営業日
            'postDate': art['postDate'],           # 示唆ポストの日（前日夜）
            'machine': a['machine'],
            'machineKey': norm(a['machine']),
            'keyword': a['chain'][0],              # 示唆の入口ワード
            'chain': a['chain'],                   # 連想経路
            'tokens': [norm(c) for c in a['chain']],
            'result': a.get('result'),
            'confirmed': a['matched'],             # 差枚実績と機種名が一致
            'tenchou': art['tenchou'],
            'articleUrl': art['articleUrl'],
            'tweetUrl': art['tweetUrl'],
        })
json.dump(recs,open(B+'/data/records.json','w'),ensure_ascii=False,indent=1)

# 機種名の表記ゆれ候補（正規化前に人が確認するリスト）
c=collections.Counter(r['machine'] for r in recs)
groups=collections.defaultdict(list)
for m in c:
    k=re.sub(r'^[SsLl]','',norm(m))
    groups[k[:3]].append(m)
with open(B+'/data/machine_variants.txt','w',encoding='utf-8') as f:
    for k,v in sorted(groups.items()):
        if len(v)>1:
            f.write(' | '.join('%s(%d)'%(m,c[m]) for m in sorted(v,key=lambda x:-c[x]))+'\n')

print('レコード %d件 / 機種見出し %d種 / 期間 %s〜%s'%(
    len(recs), len(c), min(r['targetDate'] for r in recs), max(r['targetDate'] for r in recs)))
print('ポストURL付き: %d件'%sum(1 for r in recs if r['tweetUrl']))
print('示唆ワード ユニーク: %d'%len(set(r['keyword'] for r in recs)))
