import urllib.request, os, time, sys
ua = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}
base = '/Users/kyoji/matsuwaru'
urls = open(base + '/urls.txt').read().split()
os.makedirs(base + '/cache', exist_ok=True)
ok = skip = err = 0
for i, u in enumerate(urls):
    name = u.split('/entry/')[1].replace('/', '-') + '.html'
    p = os.path.join(base, 'cache', name)
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        skip += 1; continue
    try:
        d = urllib.request.urlopen(urllib.request.Request(u, headers=ua), timeout=30).read()
        open(p, 'wb').write(d); ok += 1
    except Exception as e:
        err += 1; print('ERR', u, e, flush=True)
    time.sleep(1.0)
    if i % 50 == 0: print('%d/%d ok=%d skip=%d err=%d' % (i, len(urls), ok, skip, err), flush=True)
print('DONE ok=%d skip=%d err=%d' % (ok, skip, err), flush=True)
