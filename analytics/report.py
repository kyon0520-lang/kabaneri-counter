# -*- coding: utf-8 -*-
"""3ページ（カバネリ発光カウンタ／東宝まつわるチェッカー／イベントチェッカー）の
   日次アクセスレポートを作る。

   データ元は Cloudflare Web Analytics（RUM ビーコン）。GraphQL Analytics API の
   rumPageloadEventsAdaptiveGroups を account 単位で叩く。
   API トークンは GitHub Secrets の CLOUDFLARE_ANALYTICS_TOKEN のみが持ち、
   このスクリプトを実行する人（Claude含む）には渡さない運用（BRIEF.md の方針）。

   集計対象日は「JSTでの1日」。GitHub Actions は UTC で動くため、日付の境界だけ
   JSTで計算してUTCに変換している。前日分を対象にするのは、実行時点でその日の
   計測がまだ途中の可能性があるため（当日分だと過小に出る）。

   異常時は終了コード1で落とす（GitHub Actions の失敗通知を出すため）。
"""
import json, os, sys, urllib.request, urllib.error
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(ROOT, 'data.json')
REPORTS_DIR = os.path.join(ROOT, 'reports')

ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')
API_TOKEN = os.environ.get('CLOUDFLARE_ANALYTICS_TOKEN', '')
HOST = 'minnanoslot.com'

# (レポート上のラベル, requestPath の完全一致)
PAGES = [
    ('カバネリ発光カウンタ', '/kabaneri-unato/'),
    ('東宝まつわるチェッカー', '/matsuwaru/toho/'),
    ('イベントチェッカー', '/matsuwaru/toho/events'),
]

JST = timezone(timedelta(hours=9))
GRAPHQL_URL = 'https://api.cloudflare.com/client/v4/graphql'

QUERY = '''
query Report($accountTag: string!, $filter: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject) {
  viewer {
    accounts(filter: {accountTag: $accountTag}) {
      pages: rumPageloadEventsAdaptiveGroups(filter: $filter, limit: 100) {
        count
        avg { sampleInterval }
        sum { visits }
        dimensions { requestPath }
      }
    }
  }
}
'''


def die(msg):
    print('::error::' + msg)
    sys.exit(1)


def jst_day_range_utc(d):
    """JSTでのその日（00:00〜24:00）をUTCのISO8601文字列2つ（開始・終了）で返す。"""
    start_jst = datetime(d.year, d.month, d.day, tzinfo=JST)
    end_jst = start_jst + timedelta(days=1)
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    return start_jst.astimezone(timezone.utc).strftime(fmt), end_jst.astimezone(timezone.utc).strftime(fmt)


def fetch_pageviews(target_date):
    if not ACCOUNT_ID:
        die('CLOUDFLARE_ACCOUNT_ID が設定されていません')
    if not API_TOKEN:
        die('CLOUDFLARE_ANALYTICS_TOKEN が設定されていません（Account Analytics: Read 権限のトークンが必要）')

    start, end = jst_day_range_utc(target_date)
    variables = {
        'accountTag': ACCOUNT_ID,
        'filter': {
            'AND': [
                {'datetime_geq': start, 'datetime_lt': end},
                {'requestHost': HOST},
                {'requestPath_in': [path for _, path in PAGES]},
                {'bot': 0},
            ]
        },
    }
    body = json.dumps({'query': QUERY, 'variables': variables}).encode('utf-8')
    req = urllib.request.Request(GRAPHQL_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + API_TOKEN,
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        die('Cloudflare API がエラーを返した (HTTP %d): %s' % (e.code, e.read().decode('utf-8', 'replace')))

    if payload.get('errors'):
        die('Cloudflare GraphQL がエラーを返した: %s' % json.dumps(payload['errors'], ensure_ascii=False))

    accounts = payload.get('data', {}).get('viewer', {}).get('accounts', [])
    if not accounts:
        die('accountTag %s のアカウントが見つからない（CLOUDFLARE_ACCOUNT_ID を確認）' % ACCOUNT_ID)

    rows = {row['dimensions']['requestPath']: row for row in accounts[0].get('pages', [])}

    result = {}
    for label, path in PAGES:
        row = rows.get(path)
        if row is None:
            result[path] = {'pageviews': 0, 'visits': 0}
            continue
        sample_interval = (row.get('avg') or {}).get('sampleInterval') or 1
        pageviews = round(row['count'] * sample_interval)
        visits = round((row.get('sum') or {}).get('visits') or 0)
        result[path] = {'pageviews': pageviews, 'visits': visits}
    return result


def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, encoding='utf-8'))
    return []


def save_data(records):
    records.sort(key=lambda r: r['date'])
    json.dump(records, open(DATA_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(DATA_FILE, 'a', encoding='utf-8').write('\n')


def fmt_diff(curr, prev):
    if prev is None:
        return ''
    diff = curr - prev
    if diff == 0:
        return '（±0）'
    pct = (diff / prev * 100) if prev else 0
    sign = '+' if diff > 0 else ''
    return '（%s%d／%s%.0f%%）' % (sign, diff, sign, pct)


def build_report_md(target_date, records):
    by_date = {r['date']: r for r in records}
    today = by_date[target_date.isoformat()]
    prev_date = (target_date - timedelta(days=1)).isoformat()
    prev = by_date.get(prev_date)

    lines = []
    lines.append('# アクセスレポート %s' % target_date.isoformat())
    lines.append('')
    lines.append('Cloudflare Web Analytics（RUM）集計。ボット除外・JST 1日単位。')
    lines.append('')
    lines.append('| ページ | PV | 前日比 | 訪問者数 | 前日比 |')
    lines.append('|---|---:|---|---:|---|')
    for label, path in PAGES:
        curr = today['pages'][path]
        prev_row = prev['pages'][path] if prev else None
        pv_diff = fmt_diff(curr['pageviews'], prev_row['pageviews'] if prev_row else None)
        v_diff = fmt_diff(curr['visits'], prev_row['visits'] if prev_row else None)
        lines.append('| %s | %d | %s | %d | %s |' % (
            label, curr['pageviews'], pv_diff, curr['visits'], v_diff))

    lines.append('')
    lines.append('## 直近7日の推移（PV）')
    lines.append('')
    header = ['日付'] + [label for label, _ in PAGES]
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '---|' * len(header))
    recent = [r for r in records if r['date'] <= target_date.isoformat()][-7:]
    for r in recent:
        row = [r['date']] + [str(r['pages'][path]['pageviews']) for _, path in PAGES]
        lines.append('| ' + ' | '.join(row) + ' |')

    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('PV・訪問者数はCloudflareのアダプティブサンプリングに基づく推定値'
                  '（ダッシュボードの表示と同じ方式）。'
                  '東宝まつわるチェッカーは `/matsuwaru/toho/` の完全一致のみ集計'
                  '（`/matsuwaru/toho/events` は別集計）。')
    lines.append('')
    return '\n'.join(lines) + '\n'


def main():
    target_arg = os.environ.get('TARGET_DATE') or (sys.argv[1] if len(sys.argv) > 1 else None)
    if target_arg:
        target_date = date.fromisoformat(target_arg)
    else:
        target_date = (datetime.now(JST) - timedelta(days=1)).date()

    pages_data = fetch_pageviews(target_date)

    records = load_data()
    records = [r for r in records if r['date'] != target_date.isoformat()]
    records.append({'date': target_date.isoformat(), 'pages': pages_data})
    save_data(records)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_md = build_report_md(target_date, records)
    report_path = os.path.join(REPORTS_DIR, '%s.md' % target_date.isoformat())
    open(report_path, 'w', encoding='utf-8').write(report_md)

    print('レポート作成: %s' % report_path)
    print(report_md)


if __name__ == '__main__':
    main()
