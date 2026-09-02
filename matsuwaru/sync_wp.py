# -*- coding: utf-8 -*-
"""WordPress REST API から記事を取得する店舗の更新（stores.json の source=wp）。

はてなの sync.py と役割は同じだが、記事一覧と本文が1リクエストでまとめて取れるため
サイトマップを辿る必要がない。取得した投稿は cache/<店>/ に JSON のまま残し、
parse.py 相当の作り直しができるようにしておく。

異常時は終了コード1で落とす（GitHub Actions の失敗通知を出すため）。
"""
import urllib.request, json, os, sys, time, importlib, subprocess
from datetime import date, timedelta, datetime, timezone

_ROOT = os.path.dirname(os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'kabuki'
_cfg = [s for s in json.load(open(_ROOT + '/stores.json', encoding='utf-8'))['stores'] if s['id'] == STORE]
if not _cfg:
    raise SystemExit('stores.json に店舗 "%s" がありません' % STORE)
CONF = _cfg[0]
B = os.path.join(_ROOT, STORE)
CACHE = os.path.join(_ROOT, 'cache', STORE)
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
SINCE = CONF['since']
BLOG = CONF['blogUrl'].rstrip('/')
CAT = CONF['apiCategory']
MAX_GAP = 3          # 全台系が無い日でも記事は出る。3日空いたら異常

parse_post = importlib.import_module('lib_' + CONF['parser']).parse_post
IRR_PATH = os.path.join(B, 'data', 'irregular.json')
IRREGULAR = []
if os.path.exists(IRR_PATH):
    IRREGULAR = json.load(open(IRR_PATH, encoding='utf-8'))['irregular']
_FL = os.path.join(B, 'data', 'floors.json')
FLOORS = json.load(open(_FL, encoding='utf-8'))['split'] if os.path.exists(_FL) else None


def die(msg):
    print('::error::' + msg)
    sys.exit(1)


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode('utf-8', 'replace')


raw = json.load(open(B + '/raw.json', encoding='utf-8')) if os.path.exists(B + '/raw.json') else []
have = {a['articleUrl'] for a in raw}

# --- 1) 新しい順に取得し、既知の記事しか出てこなくなったら止める ---
fresh, page = [], 1
try:
    while page <= 6:
        u = ('%s/wp-json/wp/v2/posts?categories=%d&per_page=100&page=%d'
             '&_fields=id,date,link,title,content' % (BLOG, CAT, page))
        batch = json.loads(get(u))
        if not batch:
            break
        fresh += batch
        # このページが全部既知なら、これより古い記事も持っているはず
        if all(p['link'] in have for p in batch):
            break
        # 最終ページ。範囲外のページを要求すると WordPress は 400 を返す
        if len(batch) < 100:
            break
        page += 1
        time.sleep(1.0)
except Exception as e:
    die('記事一覧の取得に失敗: %s' % e)
if not fresh:
    die('記事が1件も取れなかった（APIの書式変更の可能性）')

new = [p for p in fresh if p['link'] not in have and p['date'][:10] >= SINCE]
print('[%s] 既存 %d件 / 新着 %d件' % (STORE, len(raw), len(new)))

# --- 2) 解析して追記 ---
os.makedirs(CACHE, exist_ok=True)
added = 0
for p in sorted(new, key=lambda x: x['date']):
    try:
        with open(os.path.join(CACHE, '%s-%s.json' % (p['date'][:10], p['id'])), 'w', encoding='utf-8') as f:
            json.dump(p, f, ensure_ascii=False)
    except Exception:
        pass
    try:
        a = parse_post(p, CONF, IRREGULAR, FLOORS)
    except Exception as e:
        die('記事の解析に失敗 %s: %s' % (p['link'], e))
    if not a['targetDate']:
        print('  ⚠ 対象日が読めずスキップ: %s' % p['link'])
        continue
    raw.append(a)
    added += 1
    print('  追加: %s  連想%d件 / 全台系%d機種' % (a['targetDate'], len(a['assoc']), len(a['results'])))

# 全台系は毎日あるわけではないので、記事単位では落とさない。
# ただし新着がまとまってあるのに連想が一件も無いのは書式変更を疑う
if added >= 3 and not any(a['assoc'] for a in raw[-added:]):
    die('新着%d件から連想が1件も取れなかった（記事の書式が変わった可能性）' % added)

raw.sort(key=lambda a: a['articleDate'])
json.dump(raw, open(B + '/raw.json', 'w'), ensure_ascii=False, indent=1)

# --- 3) 鮮度チェック ---
latest = max(a['articleDate'] for a in raw)
y, m, d = map(int, latest.split('-'))
today_jst = datetime.now(timezone(timedelta(hours=9))).date()
gap = (today_jst - date(y, m, d)).days
if gap > MAX_GAP:
    die('最新記事が%d日前(%s)。ブログの更新停止か取得失敗の可能性' % (gap, latest))

# --- 4) データ生成 → 名寄せ ---
for s in ('build.py', 'finalize.py', 'lineup.py', 'events.py'):
    if s == 'lineup.py' and not CONF.get('lineupUrl'):
        continue
    r = subprocess.run([sys.executable, os.path.join(_ROOT, s), STORE], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
        die('%s が失敗' % s)
    print(r.stdout.strip().split('\n')[-1])
print('OK  最新記事: %s (%d日前)' % (latest, gap))
