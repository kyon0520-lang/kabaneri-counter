# -*- coding: utf-8 -*-
import json,re,collections,unicodedata,csv
B='/Users/kyoji/matsuwaru'
raw=json.load(open(B+'/raw.json')); recs=json.load(open(B+'/data/matsuwaru.json'))
cnt=collections.Counter(r['machine'] for r in recs)

NON=re.compile(r'末尾|設置機種|減台|増台|バラエティ|にまつわる|記念|誕生日|周年|年目|日目|全系\d|画像の|回想|担当責任者|背景|山佐の日')
NOISE={'チキンカツ','キャベツ'}
def clean(s):
    s=unicodedata.normalize('NFKC',s); s=re.sub(r'[（(].*?[）)]','',s)
    for a,b in [('Ⅴ','V'),('Ⅲ','III'),('Ⅱ','II'),('Ⅵ','VI'),('Ⅰ','I')]: s=s.replace(a,b)
    return re.sub(r'[！!、,\s　]+$','',s).strip()
def core(s):
    s=clean(s); s=re.sub(r'^(スマスロ|回胴式遊技機|パチスロ)\s*','',s)
    return re.sub(r'^[SLA](?=[ぁ-んァ-ヶ一-龠])','',s)
def num(s):                                    # 作品番号（2作目/3作目…）
    m=re.search(r'(\d+|II|III|IV|V|VI|VII|VIII)(nd|st|th)?$',core(s))
    return m.group(1) if m else None
def stem(s):                                   # 番号を除いた幹
    return re.sub(r'(\d+|II|III|IV|V|VI|VII|VIII)(nd|st|th)?$','',core(s))

names=[m for m in cnt if not NON.search(m) and '、' not in m and m not in NOISE]
res={a['articleDate']:{r['machine']:r for r in a['results']} for a in raw}
appear={a['articleDate']:set(r['machine'] for r in a['results'])|set(x['machine'] for x in a['assoc'] if x['machine']) for a in raw}

# 確定分離：同日に両方が台数付きで別数値
split=set()
for d,s in appear.items():
    ns=[m for m in s if m in names]
    for i in range(len(ns)):
        for j in range(i+1,len(ns)):
            a,b=ns[i],ns[j]
            ra,rb=res[d].get(a),res[d].get(b)
            if ra and rb and (ra['plus'],ra['total'])!=(rb['plus'],rb['total']):
                if stem(a)==stem(b) or core(a).startswith(core(b)) or core(b).startswith(core(a)):
                    split.add(tuple(sorted([a,b])))

parent={m:m for m in names}
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[max(ra,rb,key=lambda m:(cnt[m],m))]=parent[min(ra,rb,key=lambda m:(cnt[m],m))] if False else parent.__setitem__(rb,ra) or ra

edges=[]; flagged=[]
for i,a in enumerate(names):
    for b in names[i+1:]:
        if tuple(sorted([a,b])) in split: continue
        ca,cb=core(a),core(b)
        if ca==cb: edges.append((a,b,'型式/表記ゆれ')); continue
        if stem(a)==stem(b):
            na,nb=num(a),num(b)
            if na and nb and na!=nb: continue                 # 番号違い＝別作品
            if (na is None) != (nb is None):
                flagged.append((a,b,'番号省略の可能性')); continue
        if ca!=cb and (ca.startswith(cb) or cb.startswith(ca)) and min(len(ca),len(cb))>=2:
            flagged.append((a,b,'略称の可能性'))
for a,b,_ in edges:
    ra,rb=find(a),find(b)
    if ra!=rb: parent[rb]=ra
groups=collections.defaultdict(list)
for m in names: groups[find(m)].append(m)
canon={}
for g in groups.values():
    c=max(g,key=lambda m:(cnt[m],len(m)))
    for m in g: canon[m]=c

# 曖昧略称：ある短縮名が複数の別機種グループに接続しうる
amb=collections.defaultdict(set)
for a,b,why in flagged:
    amb[a].add(canon[b]); amb[b].add(canon[a])
need=[(m,sorted(v)) for m,v in amb.items() if v-{canon[m]}]

json.dump({'canonical':canon,
           'split_confirmed':[list(x) for x in sorted(split)],
           'non_machine':sorted([m for m in cnt if NON.search(m)]),
           'noise':sorted(NOISE),
           'multi':sorted([m for m in cnt if '、' in m])},
          open(B+'/data/aliases_proposed.json','w'),ensure_ascii=False,indent=1)

with open(B+'/data/review.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['要確認','見出し','件数','統合先(案)','同一候補','根拠'])
    for m,v in sorted(need,key=lambda x:-cnt[x[0]]):
        w.writerow(['◆',m,cnt[m],canon[m],' / '.join(v),'複数の機種に接続しうる'])
    for g in sorted(groups.values(),key=lambda g:-sum(cnt[m] for m in g)):
        if len(g)>1:
            c=canon[g[0]]
            for m in sorted(g,key=lambda x:-cnt[x]):
                if m!=c: w.writerow(['',m,cnt[m],c,'','型式/表記ゆれ→自動統合'])

print('統合後の機種数: %d種（見出し231種から）'%len(set(canon.values())))
print('確定分離: %d組 / 要確認: %d件'%(len(split),len(need)))
print()
print('★ 人の判断が必要（%d件）'%len(need))
for m,v in sorted(need,key=lambda x:-cnt[x[0]]):
    print('  %-14s(%2d件)  案:%-12s  他の候補: %s'%(m,cnt[m],canon[m],' / '.join(x for x in v if x!=canon[m])))
