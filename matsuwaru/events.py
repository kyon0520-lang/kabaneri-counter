# -*- coding: utf-8 -*-
"""イベント傾向と今月の実施状況を集計して data/events.json を作る。
   日付はすべて「対象日（実際に全台系が行われた日）」で扱う。
   記事の公開日は翌日、示唆のポストは前日なので、混同すると1日ずれる。"""
import sys, os, json as _json
import os as _os
from datetime import date, timedelta, datetime, timezone
import collections, statistics, re

_ROOT = _os.path.dirname(_os.path.abspath(__file__))
STORE = sys.argv[1] if len(sys.argv) > 1 else 'toho'
B = _os.path.join(_ROOT, STORE)

raw = _json.load(open(B + '/raw.json', encoding='utf-8'))
# finalize.py が確定した名寄せ表。decisions.json だけだと
# 「番長ゼロ→番長ZERO」のような自動統合分が反映されない
canon = _json.load(open(B + '/data/canon.json', encoding='utf-8'))
# 機種と判定された名前だけを集計する。末尾⑥・アナザー末尾・設置台数などは
# 機種ではないので、検索側と同じ判定（finalize.py）の結果を使って外す
MACHINES = set(_json.load(open(B + '/data/machines.json', encoding='utf-8')))

# 現行ラインナップ（店舗公式の設置機種ページ）。撤去済みを「まだ来ていない」から外す
LINEUP, INSTALLED = None, None
_lp = B + '/data/lineup.json'
if _os.path.exists(_lp):
    LINEUP = _json.load(open(_lp, encoding='utf-8'))
    _rj = _json.load(open(B + '/data/readings.json', encoding='utf-8'))
    _read = _rj['readings']
    # 読みが広すぎて別機種を掴む機種は、照合専用の名前だけを使う
    _only = {k: v for k, v in _rj.get('ラインナップ照合', {}).items() if not k.startswith('_')}
    import unicodedata as _ud
    def _n(x):
        return re.sub(r'[\s\u3000/／・~〜\-!！?？:：\.]', '', _ud.normalize('NFKC', x).lower())
    _hall = [_n(nm) for nm, _ in LINEUP['slots']]
    def _installed(m):
        # 詳しい名前から先に当てる（からくり2 が からくり より先に決まるように）
        cand = _only[m] if m in _only else [m] + _read.get(m, [])
        for k in sorted(set(cand), key=len, reverse=True):
            if len(_n(k)) < 2: continue
            if any(_n(k) in h for h in _hall): return True
        return False
    INSTALLED = {m for m in MACHINES if _installed(m)}
fixes = _json.load(open(B + '/data/event_fixes.json', encoding='utf-8')) if os.path.exists(B + '/data/event_fixes.json') else {}
DROP = {(x[0], x[1]) for x in fixes.get('除外', [])}
ADD  = [(x[0], x[1]) for x in fixes.get('追加', [])]

def cn(m): return canon.get(m, m)
def d2(s):
    y, m, dd = map(int, s.split('-')); return date(y, m, dd)

# --- 対象日ごとの全系機種 ---
days = {}
for a in raw:
    t = a.get('targetDate')
    if not t: continue
    # 台数付きの結果セクションと、連想の見出しの両方から拾う。
    # 連想にしか出てこない機種があり、結果だけだと取りこぼす。
    ms = {cn(r['machine']) for r in a['results']}
    ms |= {cn(x['machine']) for x in a['assoc'] if x['machine']}
    ms = {m for m in ms if m in MACHINES}
    if not ms: continue
    days[t] = sorted(ms)
alldays = sorted(days)

# --- 不定期イベント（対象日ベース。誤検出は event_fixes.json で直す） ---
irr = collections.defaultdict(list)
for a in raw:
    t = a.get('targetDate')
    if not t: continue
    for e in a.get('events', []):
        if (t, e) not in DROP: irr[e].append(t)
for t, e in ADD:
    if t not in irr[e]: irr[e].append(t)
for e in irr: irr[e] = sorted(set(irr[e]))

# --- 全体の出現率（比較の基準） ---
tot = len(days)
base = collections.Counter()
for ms in days.values():
    for m in ms: base[m] += 1

def profile(dates, label):
    """その日付群でよく来る機種を、回数の多い順に返す"""
    ds = [d for d in dates if d in days]
    n = len(ds)
    if not n: return None
    c = collections.Counter()
    for d in ds:
        for m in days[d]: c[m] += 1
    rows = []
    for m, k in c.items():
        rate, b = k / n, base[m] / tot
        # 倍率は表示していないが、並びの補助として持っておく
        mul = round(rate / b, 1) if (b and k >= 2 and n >= 3) else 0
        rows.append([m, k, round(rate * 100), mul])
    rows.sort(key=lambda r: (-r[1], -base[r[0]]))
    return {'label': label, 'days': n, 'small': n < 3, 'top': rows[:8]}

# --- 定義ファイルに従ってイベントを組み立てる（表示順もこの順） ---
DEFS = _json.load(open(B + '/data/event_defs.json', encoding='utf-8'))

def lastday(d):
    return (d2(d) + timedelta(days=1)).day == 1

def match_dates(mt):
    if 'digit' in mt:
        return [d for d in alldays if int(d[-2:]) % 10 in mt['digit']]
    if 'day' in mt:
        return [d for d in alldays if int(d[-2:]) in mt['day']]
    if mt.get('monthend'):
        return [d for d in alldays if lastday(d)]
    if 'irregular' in mt:
        return irr.get(mt['irregular'], [])
    return []

events = []
for group, items in DEFS.items():
    if group.startswith('_'): continue
    for it in items:
        ds = match_dates(it['match'])
        p = profile(ds, it['label'])
        if not p: continue
        p.update({'g': group, 'key': it['key'], 'sub': it.get('sub', ''),
                  'match': it['match']})
        if 'irregular' in it['match']: p['dates'] = ds
        events.append(p)

# --- 今月の実施状況 ---
today = datetime.now(timezone(timedelta(hours=9))).date()
ym = today.strftime('%Y-%m')
donec = collections.Counter()
for d, ms in days.items():
    if d.startswith(ym):
        for m in ms: donec[m] += 1
last, gaps = {}, {}
for m in base:
    ds = sorted(d for d in alldays if m in days[d])
    last[m] = ds[-1]
    if len(ds) >= 4:
        g = [(d2(ds[i+1]) - d2(ds[i])).days for i in range(len(ds)-1)]
        gaps[m] = (round(statistics.mean(g), 1), round(statistics.pstdev(g), 1))
notyet = []
for m, n in base.most_common():
    if donec.get(m) or n < 4: continue
    if INSTALLED is not None and m not in INSTALLED: continue   # 撤去済みは出さない
    avg, sd = gaps.get(m, (None, None))
    notyet.append([m, avg, sd, (today - d2(last[m])).days, last[m]])
thismonth = {
    'month': ym,
    'lineup': ({'fetched': LINEUP['fetched'], 'machines': len(LINEUP['slots']),
                'installed': len(INSTALLED)} if LINEUP else None),
    'done': [[m, n, last[m]] for m, n in donec.most_common()],
    'notYet': notyet,
}

out = {'generated': today.isoformat(), 'totalDays': tot,
       'events': events, 'thisMonth': thismonth}
_json.dump(out, open(B + '/data/events.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('イベント集計: 対象%d日 / イベント%d件 / 今月実施%d機種・未実施%d機種 (%.0fKB)' % (
    tot, len(events), len(thismonth['done']), len(notyet),
    os.path.getsize(B + '/data/events.json') / 1024))
for p in events:
    tail = ('  ' + '・'.join(x[5:] for x in p['dates'])) if p.get('dates') else ''
    print('   [%s] %-18s %2d日%s' % (p['g'][:4], p['label'] + (' ' + p['sub'] if p['sub'] else ''), p['days'], tail))
