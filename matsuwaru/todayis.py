# -*- coding: utf-8 -*-
"""「何の日」を netlab.click から取得し、各店舗の data/todayis.json に書き出す。
   イベント傾向チェッカーの「明日は何の日」タブ用。19時までは今日ぶん、19時を過ぎたら
   翌日ぶんを取得する（main()参照）。全店舗で同じ内容だが、
   /matsuwaru/data/* は旧URL向けの301リダイレクトが既にあるため（_redirects）、
   他のJSONと同様に店舗ごとのdata/配下に複製して置く。おまけ機能なので、
   先方の書式変更などで失敗しても他のパイプラインは止めない（前回分のまま据え置き）。"""
import urllib.request, re, os, json, html
from datetime import datetime, timedelta, timezone

B = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) matsuwaru-checker/personal'}

def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode('utf-8', 'replace')

def clean_text(s):
    s = re.sub(r'<span class="countrymei">(.*?)</span>', r'（\1）', s, flags=re.S)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    s = re.sub(r'[\r\n\t]+', '', s)
    s = re.sub(r' {2,}', ' ', s)
    return s.strip()

def parse(src):
    m = re.search(r'<article[^>]*>(.*?)</article>', src, re.S)
    body = m.group(1) if m else src
    s = body.find('id="kinenbi"')
    if s < 0:
        raise ValueError('記念日セクションが見つからない（書式変更の可能性）')
    e = body.find('id="dekigoto"')
    sec = body[s:e] if e > s else body[s:]

    # 「9月21日は何の日？」直下のピックアップ（h3見出し）を主要4件とし、
    # 「他にもある〜の記念日」以降（h4の小見出しの下にp.kinenbilistで並ぶ）をその他とする
    h3s = list(re.finditer(r'<h3[^>]*>(.*?)</h3>', sec, re.S))
    main, boundary = [], None
    for hm in h3s:
        t = clean_text(hm.group(1))
        if t.startswith('他にもある'):
            boundary = hm.end()
            break
        main.append(re.sub(r'【[^】]*】$', '', t))
    if not main:
        raise ValueError('主な記念日が1件も取れなかった')

    holiday_scope_end = h3s[1].start() if len(h3s) > 1 else len(sec)
    holiday = '国民の祝日' in sec[:holiday_scope_end]

    tail = sec[boundary:] if boundary else ''
    sub = [x for x in (clean_text(p) for p in re.findall(r'<p class="kinenbilist">(.*?)</p>', tail, re.S)) if x]

    return {'main': main, 'sub': sub, 'holiday': holiday}

def main():
    now = datetime.now(timezone(timedelta(hours=9)))
    # 19時までは今日ぶん、19時を過ぎたら翌日ぶんに切り替える（events.htmlのafterPostと同じ考え方）。
    # これが無いと、実行時刻に関係なく常に「翌日」を計算してしまい、19時の実行を待たずに
    # 朝の実行（9:17など）の時点で翌日ぶんが表に出てしまう
    target = now + timedelta(days=1) if now.hour >= 19 else now
    url = 'https://netlab.click/todayis/%02d%02d' % (target.month, target.day)
    stores = json.load(open(os.path.join(B, 'stores.json'), encoding='utf-8'))['stores']
    try:
        data = parse(get(url))
        data['date'] = target.strftime('%Y-%m-%d')
        data['sourceUrl'] = url
        # 取得時刻はあえて持たない。入れると内容が同じでも実行のたびにJSONが変わり、
        # git diffが毎回検知されて無駄なコミット・デプロイが走ってしまうため
        for s in stores:
            out = os.path.join(B, s['id'], 'data', 'todayis.json')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('OK  明日は何の日(%s): 主要%d件・その他%d件（%d店舗ぶん）' % (data['date'], len(data['main']), len(data['sub']), len(stores)))
    except Exception as e:
        print('::warning::明日は何の日の取得に失敗（%s）。前回分のデータのまま据え置き' % e)

if __name__ == '__main__':
    main()
