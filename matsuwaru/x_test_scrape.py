# -*- coding: utf-8 -*-
"""GitHub Actionsの共有ランナーからXを読めるか確認するための使い捨てテスト。
   本番導入が決まったら消すか、正式なパーサーに置き換える。"""
import json, re, time
from playwright.sync_api import sync_playwright

URL = 'https://x.com/sloneko222'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')

seen = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='chromium')
    ctx = browser.new_context(user_agent=UA, viewport={'width': 1280, 'height': 2000}, locale='ja-JP')
    page = ctx.new_page()
    resp = page.goto(URL, wait_until='load', timeout=30000)
    print('HTTP status:', resp.status if resp else None)
    try:
        page.wait_for_selector('article', timeout=15000)
    except Exception as e:
        print('article待機失敗:', e)
        print('body length:', len(page.content()))
        print(page.content()[:1000])
        browser.close()
        raise SystemExit(1)

    for round_ in range(18):
        arts = page.locator('article')
        n = arts.count()
        for i in range(n):
            art = arts.nth(i)
            try:
                href = art.locator('a[href*="/status/"]').first.get_attribute('href')
            except Exception:
                continue
            if not href:
                continue
            m = re.search(r'status/(\d+)', href)
            if not m:
                continue
            sid = m.group(1)
            if sid in seen:
                continue
            try:
                more = art.locator('button:has-text("さらに表示")')
                if more.count():
                    more.first.click(timeout=1500)
                    time.sleep(0.3)
            except Exception:
                pass
            try:
                text = art.inner_text()
            except Exception:
                continue
            seen[sid] = text
        page.mouse.wheel(0, 1800)
        time.sleep(1.0)

    browser.close()

out = [{'id': k, 'text': v} for k, v in seen.items()]
print('総取得件数:', len(out))
kabuki = [r for r in out if '歌舞伎' in r['text']]
print('歌舞伎関連:', len(kabuki))
for r in kabuki:
    print('====', r['id'], '====')
    print(r['text'])
    print()
