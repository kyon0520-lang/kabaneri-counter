# -*- coding: utf-8 -*-
"""毎朝の更新: サイトマップ再取得 → 新着のみクロール → 解析 → 名寄せ まで一括"""
import urllib.request, re, os, time, subprocess, sys
B = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
SINCE = '2026-02-22'          # エンドウ店長就任以降のみ

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode('utf-8', 'replace')

# 1) サイトマップから最新のURL一覧を取り直す（直近2ファイルだけ見れば新着は拾える）
idx = get('https://sloslo-blog.hatenablog.com/sitemap.xml')
maps = [m.replace('&amp;', '&') for m in re.findall(r'<loc>(.*?)</loc>', idx) if 'periodical' in m][:2]
urls = set(open(B + '/urls.txt').read().split()) if os.path.exists(B + '/urls.txt') else set()
before = len(urls)
for m in maps:
    urls |= {u for u in re.findall(r'<loc>(.*?)</loc>', get(m)) if '/entry/' in u}
    time.sleep(0.5)
urls = sorted(u for u in urls if u.split('/entry/')[1][:10].replace('/', '-') >= SINCE)
open(B + '/urls.txt', 'w').write('\n'.join(urls))
print('URL一覧: %d件 (+%d)' % (len(urls), len(urls) - before))

# 2) 未取得のみクロール（既存キャッシュはスキップ）
new = [u for u in urls if not os.path.exists(os.path.join(B, 'cache', u.split('/entry/')[1].replace('/', '-') + '.html'))]
print('新着記事: %d件' % len(new))
for u in new:
    p = os.path.join(B, 'cache', u.split('/entry/')[1].replace('/', '-') + '.html')
    try:
        open(p, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
        print('  取得:', u)
    except Exception as e:
        print('  ERR', u, e)
    time.sleep(1.0)

# 3) 解析 → データ生成 → 名寄せ
for s in ('parse.py', 'build.py', 'finalize.py'):
    r = subprocess.run([sys.executable, os.path.join(B, s)], capture_output=True, text=True)
    if r.returncode: print(r.stderr); sys.exit(1)
    print(r.stdout.strip().split('\n')[-1])
