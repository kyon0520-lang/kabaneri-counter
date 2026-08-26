# -*- coding: utf-8 -*-
import json, re, csv, collections, unicodedata
from datetime import date
import os
B=os.path.dirname(os.path.abspath(__file__))
raw=json.load(open(B+'/raw.json')); recs=json.load(open(B+'/data/records.json'))  # build.py の出力（名寄せ前）
dec=json.load(open(B+'/data/decisions.json'))
cnt=collections.Counter(r['machine'] for r in recs)

def clean(s):
    s=unicodedata.normalize('NFKC',s); s=re.sub(r'[（(].*?[）)]','',s)
    for a,b in [('Ⅴ','V'),('Ⅲ','III'),('Ⅱ','II'),('Ⅵ','VI')]: s=s.replace(a,b)
    return re.sub(r'[！!、,\s　]+$','',s).strip()
def d2(s):
    y,m,dd=map(int,s.split('-')); return date(y,m,dd)

NON=re.compile(r'末尾|設置機種|減台|増台|バラエティ|にまつわる|記念|誕生日|周年|年目|日目|全系\d|画像の|回想|担当責任者|背景|山佐の日')
DUP={'カバネリ海門決戦、Sカバネリ':['カバネリ海門','Sカバネリ'],
     'キンハナ、ドラハナ、スタハナ、ニューキンハナ':['キンハナ','ドラハナ','スタハナ','ニューキンハナ'],
     'このすばシリーズ':['Sこのすば','Aこのすば']}
# 私の判断で寄せた分（ユーザー確認済み）
AUTO=[['マイジャグV','マイジャグ','マイジャグⅤ','マイジャグラーV'],
      ['ファンキー2','ファンキージャグラー','ファンキージャグラー2','ファンキー２'],
      ['ウルミラ','ウルミラジャグラー','ウルトラミラクルジャグラー','ウルトラミラクル','ミラクル'],
      ['戦国乙女4','戦国乙女','乙女','乙女4'],['炎炎2','L炎炎2'],
      ['七つ魔','七つ魔剣','七つま','ななつま'],['いせかる','いせかるBT','異世界かるてっと'],
      ['アイム','Sアイム','アイムジャグラー','アイムEX'],['ネオアイムEX','ネオアイム'],
      ['かぐや様','かぐや'],['超電磁砲2','超電磁砲'],['ヨルムンガンド','スマスロヨルムンガンド'],
      ['銀河英雄伝説','銀河英雄伝'],['DMC5','DMC','デビルメイクライ','デビルメイクライ5'],
      ['ミスタージャグラー','ミスター'],['ハッピー','ハッピーVⅢ','ハッピージャグラー'],
      ['からくり','からくりサーカス'],['北斗','スマスロ北斗'],['北斗転生2','北斗転生'],
      ['グランベルム','回胴式遊技機 グランベルム'],['ToLOVEる','ToLOVEるトランス'],
      ['モンハンライズ','モンハン'],['アバサー','Sアバサー'],['鏡','スマスロ鏡'],
      ['アレックス','アレックスBT'],['ゴージャグ3','ゴージャグ'],['サンダーV','サンダー'],
      ['Lハナビ','スマスロハナビ'],['モンキーV','モンキーⅤ'],['シェイク','シェイクBT'],
      ['不二子','不二子BT'],['新鬼武者3','L新鬼武者3','新鬼3'],['番長ZERO','番長ゼロ','番長ＺＥＲＯ'],
      ['化物語','L化物語','化物語（池袋店合同）'],['バンドリ','バンドリ！'],
      ['リオエース2','リオエース'],['Lディスク','ディスク2'],['ひぐらし','ひぐらし祭2'],
      ['ヴヴヴ'],['ヴヴヴ2'],['戦国乙女5'],['L炎炎'],['SAOⅡ'],['ギアスC.C.','ギアスCC'],
      ['バイオRE:2','バイオRE2'],['東リベ','東リべ'],['スタハナ','スターハナハナ'],
      ['絆2天膳','バジ絆2天膳','天膳'],['ジャグラーガールズ','ジャグガ','ガールズ'],
      ['沖ドキゴージャス','沖ドキ！ゴージャス'],['レビュースタァ','レヴュスタァ'],
      ['マギレコ','スマスロ マギアレコード 魔法少女まどか☆マギカ外伝'],['キンハナ','Sキンハナ','キングハナハナ‐30'],
      ['ニューキンハナ','Lキンハナ'],['エウレカ','エウレカA','Sエウレカ','エウレカセブン'],
      ['いざ番長','いざ番'],['リゼロ2','リゼロ','リゼロ2nd','Re:ゼロ'],
      ['Sこのすば','このすば'],['Sカバネリ','カバネリ','Sカバネリ（※1台稼働停止）'],
      ['カバネリ海門','Lカバネリ','カバネリ海門決戦']]

canon={}
for g in AUTO:
    for m in g:
        if m in cnt: canon[m]=g[0]
for m,c in dec.get('merge',{}).items():      # ユーザー決定を最優先で上書き
    canon[m]=c
for m in cnt:
    if m in DUP or NON.search(m): continue
    canon.setdefault(m, clean(m) if clean(m) in cnt else m)

out=[]
for r in recs:
    m=r['machine']
    if m in DUP:
        for t in DUP[m]:
            x=dict(r); x['machine']=t; x['category']='機種'; x['note']='並記見出しを分割'; out.append(x)
        continue
    x=dict(r)
    if NON.search(m):
        x['category']='末尾・設置・記念日など'; x['machine']=m
    else:
        x['category']='機種'; x['machine']=canon.get(m,m)
    out.append(x)

# --- 手動修正の適用（data/corrections.json） ---
_cpath = B + '/data/corrections.json'
if os.path.exists(_cpath):
    _corr = json.load(open(_cpath, encoding='utf-8')).get('records', [])
    _applied = 0
    for c in _corr:
        m, st = c['match'], c['set']
        for r in out:
            if r['targetDate'] == m['date'] and '→'.join(r['chain']) == m['raw']:
                if 'machine' in st: r['machine'] = st['machine']
                if 'chain' in st: r['chain'] = st['chain']
                if 'category' in st: r['category'] = st['category']
                r['corrected'] = c.get('note', '')
                _applied += 1
    _miss = len(_corr) - _applied
    print('手動修正: %d件を適用%s' % (_applied, '（%d件は対象が見つからず未適用）' % _miss if _miss else ''))

for i,x in enumerate(out): x['id']='%s-%03d'%(x['targetDate'],i)

json.dump(out,open(B+'/data/matsuwaru.json','w'),ensure_ascii=False,indent=1)
with open(B+'/data/matsuwaru.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['対象日','ポスト日','区分','機種','示唆ワード','連想経路','プラス台数','設置台数','平均差枚','記事URL','ポストURL'])
    for r in sorted(out,key=lambda x:(x['targetDate'],x['machine'])):
        res=r.get('result') or {}
        w.writerow([r['targetDate'],r['postDate'],r['category'],r['machine'],r['keyword'],'→'.join(r['chain']),
                    res.get('plus',''),res.get('total',''),res.get('avg',''),r['articleUrl'],r['tweetUrl'] or ''])
mm=[r for r in out if r['category']=='機種']
print('レコード %d件（うち機種 %d件 / その他示唆 %d件）'%(len(out),len(mm),len(out)-len(mm)))
print('機種数: %d種（見出し231種から名寄せ）'%len(set(r['machine'] for r in mm)))
print('示唆ワード ユニーク: %d語'%len(set(r['keyword'] for r in mm)))
top=collections.Counter(r['machine'] for r in mm).most_common(8)
print('件数上位:', ', '.join('%s(%d)'%(m,c) for m,c in top))

# --- 検索用の軽量インデックス（ページが読むのはこれ） ---
arts, ai = [], {}
for r in sorted(out, key=lambda x: x['targetDate']):
    k = r['articleUrl']
    if k not in ai:
        ai[k] = len(arts); arts.append([r['targetDate'], k, r['tweetUrl'] or ''])
mi, mnames = {}, []
for r in out:
    if r['machine'] not in mi:
        mi[r['machine']] = len(mnames); mnames.append(r['machine'])
def _n(x): return re.sub(r'[\s\u3000]+','',unicodedata.normalize('NFKC',x or '')).lower()
_alias = {_n(k): v for k, v in canon.items()}
rows, trimmed = [], 0
for r in out:
    res = r.get('result') or {}
    ch = list(r['chain'])
    # 連想の終点が機種名そのもの（旧表記含む）なら、表示側で機種名を足すので落とす
    while len(ch) > 1 and (_n(ch[-1]) == _n(r['machine']) or _alias.get(_n(ch[-1])) == r['machine']):
        ch.pop(); trimmed += 1
    rows.append([ai[r['articleUrl']], mi[r['machine']], ch,
                 res.get('plus'), res.get('total'), res.get('avg'),
                 0 if r['category'] == '機種' else 1])
idx = {'generated': __import__('datetime').date.today().isoformat(),
       'machines': mnames, 'articles': arts, 'recs': rows}
json.dump(idx, open(B + '/data/index.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('検索インデックス: %d件 / %.0fKB（終点の重複を%d件整理）' % (len(rows), os.path.getsize(B + '/data/index.json')/1024, trimmed))
