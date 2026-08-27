# -*- coding: utf-8 -*-
"""毎朝の更新。raw.json を正本にして、未取得の記事だけを取得・追記する。
   異常時は終了コード1で落とす（GitHub Actions の失敗通知を出すため）。"""
import urllib.request, re, os, sys, json, time, subprocess
from datetime import date, timedelta, datetime, timezone
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
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
SINCE = CONF['since']        # 示唆の癖が変わる区切り（stores.json）
BLOG = CONF['blogUrl'].rstrip('/')
MAX_GAP = 2                   # ブログは毎日更新。これ以上空いたら異常

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode('utf-8', 'replace')

def die(msg):
    print('::error::' + msg); sys.exit(1)

raw = json.load(open(B + '/raw.json', encoding='utf-8')) if os.path.exists(B + '/raw.json') else []
have = {a['articleUrl'] for a in raw}

# --- 1) サイトマップから最新URLを取得（直近2ヶ月分で十分） ---
try:
    idx = get(BLOG + '/sitemap.xml')
    maps = [m.replace('&amp;', '&') for m in re.findall(r'<loc>(.*?)</loc>', idx) if 'periodical' in m][:2]
    urls = set()
    for m in maps:
        urls |= {u for u in re.findall(r'<loc>(.*?)</loc>', get(m)) if '/entry/' in u}
        time.sleep(0.5)
except Exception as e:
    die('サイトマップの取得に失敗: %s' % e)
urls = sorted(u for u in urls if u.split('/entry/')[1][:10].replace('/', '-') >= SINCE)
if not urls:
    die('サイトマップから記事URLが取れなかった（書式変更の可能性）')

# --- 2) 未取得の記事だけ取得して解析 ---
new = [u for u in urls if u not in have]
print('[%s] 既存 %d件 / 新着 %d件' % (STORE, len(raw), len(new)))
added = []
for u in new:
    ent = u.split('/entry/')[1].replace('/', '-')
    try:
        src = get(u)
        # 全再構築（parse.py）できるようキャッシュにも残す
        try:
            os.makedirs(CACHE, exist_ok=True)
            open(os.path.join(CACHE, ent + '.html'), 'w', encoding='utf-8').write(src)
        except Exception:
            pass
        a = parse_html(src, ent)
    except Exception as e:
        die('記事の解析に失敗 %s: %s' % (u, e))
    if not a['assoc']:
        die('連想が1件も取れなかった %s（記事の書式が変わった可能性）' % u)
    added.append(a); raw.append(a)
    print('  追加: %s  連想%d件 / 全系%d機種' % (a['targetDate'], len(a['assoc']), len(a['results'])))
    time.sleep(1.0)

raw.sort(key=lambda a: a['articleDate'])
json.dump(raw, open(B + '/raw.json', 'w'), ensure_ascii=False, indent=1)

# --- 3) 鮮度チェック：最新記事が古すぎたら異常 ---
latest = max(a['articleDate'] for a in raw)
y, m, d = map(int, latest.split('-'))
# 実行環境はUTCなので、日本時間の「今日」で比べる
# （9時JST＝0時UTCだと、UTCの日付が前日になり判定がずれるため）
today_jst = datetime.now(timezone(timedelta(hours=9))).date()
gap = (today_jst - date(y, m, d)).days
if gap > MAX_GAP:
    die('最新記事が%d日前(%s)。ブログの更新停止か取得失敗の可能性' % (gap, latest))

# --- 4) データ生成 → 名寄せ ---
for s in ('build.py', 'finalize.py', 'lineup.py', 'events.py'):
    r = subprocess.run([sys.executable, os.path.join(_ROOT, s), STORE], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr); die('%s が失敗' % s)
    print(r.stdout.strip().split('\n')[-1])
print('OK  最新記事: %s (%d日前)' % (latest, gap))
