# -*- coding: utf-8 -*-
import json, csv, re, unicodedata, collections, os
import os
B=os.path.dirname(os.path.abspath(__file__))
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
json.dump(recs,open(B+'/data/matsuwaru.json','w'),ensure_ascii=False,indent=1)

with open(B+'/data/matsuwaru.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['対象日','ポスト日','機種','示唆ワード','連想経路','プラス台数','設置台数','平均差枚','実績照合','記事URL','ポストURL'])
    for r in recs:
        res=r['result'] or {}
        w.writerow([r['targetDate'],r['postDate'],r['machine'],r['keyword'],'→'.join(r['chain']),
                    res.get('plus',''),res.get('total',''),res.get('avg',''),
                    'OK' if r['confirmed'] else '',r['articleUrl'],r['tweetUrl'] or ''])

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
