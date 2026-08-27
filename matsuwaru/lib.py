# -*- coding: utf-8 -*-
"""記事HTMLの解析（parse.py / sync.py から共用）"""
import re, html, os, unicodedata

def totext(s):
    m = re.search(r'<div class="entry-content[^"]*">(.*?)</div>\s*<(?:footer|div class="entry-footer)', s, re.S)
    b = m.group(1) if m else ''
    tw = re.findall(r'https://(?:twitter|x)\.com/[A-Za-z0-9_]+/status/\d+', b)
    b = re.sub(r'<script.*?</script>', '', b, flags=re.S)
    b = re.sub(r'<br\s*/?>', '\n', b)
    b = re.sub(r'</(p|div|li|h\d|tr|table|blockquote)>', '\n', b)
    b = html.unescape(re.sub(r'<[^>]+>', '', b))
    b = re.sub(r'[ \t　]+', ' ', b)
    lines = [l.strip() for l in b.split('\n')]
    title = re.search(r'<title>(.*?)</title>', s, re.S)
    return (title.group(1) if title else ''), (tw[0] if tw else None), lines

# 不定期イベントの検出。記事タイトルと本文から拾う
IRREGULAR = [
    ('あかまる取材', r'あかまる取材|あかまる来店|アカマル取材'),
    ('ダンち',      r'ダンち|ダンチ'),
    ('エグち',      r'エグち|エグチ'),
    ('やばたにえん', r'やばたにえん'),
    ('東京大戦',    r'東京大戦'),
]

ARROW = '[→➡👉⇒]'
DAIS  = re.compile(r'^([+\-]?\d+)/(\d+)台')
AVG   = re.compile(r'平均\s*([+\-]?[\d,]+)\s*枚')

def norm(s):
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'[\s　]+', '', s)

def parse_html(src, ent):
    """src=記事HTML, ent='YYYY-MM-DD-HHMMSS'"""
    title, tweet_url, lines = totext(src)
    article_date = '-'.join(ent.split('-')[:3])
    m = re.match(r'(\d+)月(\d+)日', title)
    y = int(article_date[:4])
    target = None
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        ty = y - 1 if (mo == 12 and article_date[5:7] == '01') else y
        target = '%04d-%02d-%02d' % (ty, mo, d)

    # 店長ポストの投稿者・投稿日（引用の署名行）
    tenchou, post_date, sig_i = None, None, None
    for i, l in enumerate(lines):
        mm = re.match(r'^[—\-–]\s*(.+?)\s*\((@\w+)\)\s*(\d{4})年(\d+)月(\d+)日', l)
        if mm:
            tenchou = mm.group(2)
            post_date = '%s-%02d-%02d' % (mm.group(3), int(mm.group(4)), int(mm.group(5)))
            sig_i = i
            break

    # --- 結果セクション: 機種名 + N/M台 + 平均枚 ---
    results, order = {}, []
    head = lines[:sig_i] if sig_i else lines
    for i, l in enumerate(head):
        dm = DAIS.match(l)
        if not dm:
            continue
        name, seen = '', 0
        for j in range(i - 1, -1, -1):
            c = head[j].strip()
            if not c:
                continue
            seen += 1
            if seen > 3:
                break
            c = re.sub(r'^[・･]\s*', '', c)
            if c and not DAIS.match(c) and not AVG.search(c) and len(c) <= 30 and '。' not in c and not re.search(ARROW, c):
                name = c; break
        if not name:
            continue
        am = AVG.search(l) or (AVG.search(head[i+1]) if i+1 < len(head) else None)
        k = norm(name)
        if k in results:
            continue
        results[k] = {'machine': name, 'plus': int(dm.group(1)), 'total': int(dm.group(2)),
                      'avg': int(am.group(1).replace(',', '')) if am else None}
        order.append(k)

    # --- 連想セクション: 矢印の有無だけで見出し/連鎖を判定（・の付き方が記事ごとに揺れるため） ---
    assoc, cur, unknown = [], None, []
    tail = lines[sig_i+1:] if sig_i else []
    # 記事ごとに「・」の意味が反転する（連想行に付く記事と見出しに付く記事がある）
    bullet_is_chain = any(re.match(r'^[・･]', x) and re.search(ARROW, x) for x in tail)
    for l0 in tail:
        is_bullet = bool(re.match(r'^[・･]', l0))
        l = re.sub(r'^[・･]\s*', '', l0).strip()
        if not l:
            continue
        if bullet_is_chain and is_bullet and not re.search(ARROW, l) and len(l) <= 30:
            # 矢印なしの示唆ワード単独行（機種に直結）
            if cur:
                assoc.append({'machine': cur, 'matched': norm(cur) in results,
                              'keyword': l, 'chain': [l], 'raw': l0})
            continue
        if re.search(ARROW, l):
            chain = [c.strip() for c in re.split(ARROW, l) if c.strip()]
            if len(chain) < 2 or len(l) > 200:
                continue
            k = norm(cur) if cur else None
            rec = {'machine': cur, 'matched': bool(k and k in results),
                   'keyword': chain[0], 'chain': chain, 'raw': l}
            (assoc if cur else unknown).append(rec)
        elif len(l) <= 30 and '。' not in l:
            cur = l
        elif '。' in l and len(l) > 30:
            cur = None  # 解説文に入ったら区切る

    # 差枚実績を機種名で突き合わせて補完
    for a in assoc:
        r = results.get(norm(a['machine'])) if a['machine'] else None
        a['result'] = {k: r[k] for k in ('plus', 'total', 'avg')} if r else None

    flat = title + ' ' + ' '.join(lines)
    events = [n for n, pat in IRREGULAR if re.search(pat, flat)]

    return {'events': events, 'articleUrl': 'https://sloslo-blog.hatenablog.com/entry/' + ent.replace('-', '/', 3).replace('-', '/'),
            'articleDate': article_date, 'targetDate': target, 'postDate': post_date,
            'tenchou': tenchou, 'tweetUrl': tweet_url, 'title': title.split(' - ')[0],
            'results': [results[k] for k in order], 'assoc': assoc, 'unassigned': unknown}

