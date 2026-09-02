# -*- coding: utf-8 -*-
"""P-WORLD の店舗ページから現行のスロット設置機種を取得して data/lineup.json に保存する。
   撤去済みの機種を「今月まだ来ていない」から外すために使う。
   stores.json に "lineupSource": "pworld" と書いた店舗を lineup.py がここに回す。

【台数は取らない】
P-WORLD は台数を GIF 画像で出しており、ページに「データ取得はお止め下さい」と
明示されている。よって台数は取得せず 0 を入れる。台数はブログ各記事の実測値
（results の total）が使われるので、判定に支障はない。

【機種名は別名ごと持つ】
data-machine-name には「Ｌ東京喰種ＣＴ/スマスロ　東京喰種/Ｌトーキョーグール…」のように
別名が / 区切りで全部入っている。events.py の照合は正規化した部分一致なので、
この塊をそのまま持たせるといちばん当たりがよい。表示には先頭の名前だけを使う。
"""
import sys, os, json as _json, re, html, urllib.request
from datetime import datetime, timezone, timedelta, date

_ROOT = os.path.dirname(os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'kabuki'
_cfg = [s for s in _json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg:
    raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = os.path.join(_ROOT, STORE)
URL = CONF.get('lineupUrl')
if not URL:
    print('[%s] lineupUrl が未設定のため、ラインナップ取得は行いません' % STORE)
    raise SystemExit(0)

# 入れ替え日が読めないので曜日では絞らず、7日より新しければ使い回す
JST = timezone(timedelta(hours=9))
today = datetime.now(JST).date()
force = '--force' in sys.argv
_lp = os.path.join(B, 'data', 'lineup.json')
if not force and os.path.exists(_lp):
    try:
        prev = _json.load(open(_lp, encoding='utf-8'))
        y, m, d = map(int, prev['fetched'].split('-'))
        age = (today - date(y, m, d)).days
    except Exception:
        prev, age = {}, 99
    if age < 7:
        print('[%s] 設置機種は前回(%s・%d日前)の結果を使います' % (STORE, prev.get('fetched', '?'), age))
        raise SystemExit(0)

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
try:
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30).read()
except Exception as e:
    print('::error::P-WORLDの取得に失敗: %s' % e)
    raise SystemExit(1)
src = raw.decode('euc_jp', 'replace')      # P-WORLD は EUC-JP

slots = []
seen = set()
for m in re.finditer(r'<li\b[^>]*>', src):
    tag = m.group(0)
    t = re.search(r'data-machine-type="(\w)"', tag)
    n = re.search(r'data-machine-name="([^"]*)"', tag)
    if not (t and n) or t.group(1) != 'S':   # S=スロット、P=パチンコ
        continue
    name = html.unescape(n.group(1)).strip()
    if not name or name in seen:
        continue
    seen.add(name)
    slots.append([name, 0])                  # 台数は取らない（上のコメント参照）

if len(slots) < 20:
    print('::error::スロットが%d件しか取れませんでした。ページの作りが変わった可能性' % len(slots))
    raise SystemExit(1)

_json.dump({'fetched': today.isoformat(), 'source': URL, 'unitsUnavailable': True, 'slots': slots},
           open(_lp, 'w'), ensure_ascii=False, indent=1)
print('[%s] 現行ラインナップ: %d機種（台数はP-WORLDの方針により取得しない）' % (STORE, len(slots)))
