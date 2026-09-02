# -*- coding: utf-8 -*-
"""店舗の現行ラインナップを取得して data/lineup.json に保存する。
   撤去済みの機種を「今月まだ来ていない」から外すために使う。
   出どころは店舗公式の設置機種ページ（stores.json の lineupUrl）。"""
import sys, os, json as _json, re, html, unicodedata, urllib.request
from datetime import datetime, timezone, timedelta, date

_ROOT = os.path.dirname(os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'toho'
_cfg = [s for s in _json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg: raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = os.path.join(_ROOT, STORE)
# P-WORLD から取る店舗は lineup_pworld.py が担当する
if CONF.get('lineupSource') == 'pworld':
    import subprocess
    raise SystemExit(subprocess.run([sys.executable,
        os.path.join(_ROOT, 'lineup_pworld.py'), STORE] + sys.argv[2:]).returncode)

URL = CONF.get('lineupUrl')
if not URL:
    print('[%s] lineupUrl が未設定のため、ラインナップ取得は行いません' % STORE); raise SystemExit(0)

# 入れ替えは月曜（祝日なら火曜）なので、月・火だけ取りに行く。
# それ以外の日は前回の結果を使い回す（取得先に無駄な負荷をかけないため）。
# 8日以上古い場合と、--force を付けたときは曜日によらず取得する。
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
        age = 99
    if today.weekday() not in (0, 1) and age < 8:
        print('[%s] 設置機種の取得は月・火のみ。前回(%s・%d日前)の結果を使います'
              % (STORE, prev.get('fetched', '?'), age))
        raise SystemExit(0)

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
try:
    src = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30).read().decode('utf-8', 'replace')
except Exception as e:
    print('::error::設置機種ページの取得に失敗: %s' % e); raise SystemExit(1)

slots = []
for kind, body in re.findall(r'<div class="kisyu-tab (\w+)"[^>]*>(.*?)(?=<div class="kisyu-tab |\Z)', src, re.S):
    if kind != 'slot': continue
    for x in re.findall(r'<div class="kisyu-item">(.*?)</div>', body, re.S):
        x = unicodedata.normalize('NFKC', html.unescape(re.sub(r'<[^>]+>', '', x))).strip()
        m = re.match(r'(.+?)\((\d+)台\)$', x)
        if m: slots.append([m.group(1).strip(), int(m.group(2))])

if len(slots) < 20:
    print('::error::スロットが%d件しか取れませんでした。ページの作りが変わった可能性' % len(slots)); raise SystemExit(1)

_json.dump({'fetched': today.isoformat(), 'source': URL, 'slots': slots},
           open(B + '/data/lineup.json', 'w'), ensure_ascii=False, indent=1)
print('[%s] 現行ラインナップ: %d機種 / %d台' % (STORE, len(slots), sum(n for _, n in slots)))
