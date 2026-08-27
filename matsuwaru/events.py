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
    # 機種ではない見出し（色の注記、シリーズ表記、設置台数など）を落とす。
    # 残すと「かぐや様（ピンク）」のような表記が別機種として数えられてしまう。
    ms = {m for m in ms if not re.search(
        r'[（(]|シリーズ|バラエティ|設置機種|減台|増台|にまつわる|記念|誕生日|周年|年目|日目'
        r'|全系\d|画像の|回想|担当責任者|背景|山佐の日|据え置き', m)}
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
    """その日付群でよく来る機種を、全体との比を添えて返す"""
    ds = [d for d in dates if d in days]
    n = len(ds)
    if not n: return None
    c = collections.Counter()
    for d in ds:
        for m in days[d]: c[m] += 1
    rows = []
    for m, k in c.items():
        rate, b = k / n, base[m] / tot
        # 倍率は、その機種が2回以上出ていて、かつ開催3日以上のときだけ出す。
        # 1回だけの機種は50%×88倍のような無意味な数字になるため。
        mul = round(rate / b, 1) if (b and k >= 2 and n >= 3) else 0
        rows.append([m, k, round(rate * 100), mul])
    # 回数 → 全体での多さ の順に並べる（表示と同じ基準にする）
    rows.sort(key=lambda r: (-r[1], -base[r[0]]))
    return {'label': label, 'days': n, 'small': n < 3, 'top': rows[:8]}

# --- 末尾ごと（◯のつく日）---
bydigit = {}
for dg in range(10):
    p = profile([d for d in alldays if int(d[-2:]) % 10 == dg], '%dのつく日' % dg)
    if p: bydigit[str(dg)] = p

# --- 特殊な日 ---
special = {}
for key, sel in [
    ('ゾロ目の日', lambda d: d[-2:] in ('11','22') or int(d[5:7]) == int(d[-2:])),
    ('月末最終日', lambda d: (d2(d) + timedelta(days=1)).day == 1),
    ('1日',        lambda d: int(d[-2:]) == 1),
]:
    p = profile([d for d in alldays if sel(d)], key)
    if p: special[key] = p

# --- 21-27WEEK は日ごとに内容が違うので分ける（内訳は event_fixes.json）---
WEEKSUB = fixes.get('21-27WEEKの内訳', {})
for dd in range(21, 28):
    sub = WEEKSUB.get(str(dd))
    key = '21-27WEEK %d日' % dd
    p = profile([d for d in alldays if int(d[-2:]) == dd],
                key + ('・%s' % sub if sub else ''))
    if p: special[key] = p

# --- 不定期イベント ---
irregular = {}
for e, ds in irr.items():
    p = profile(ds, e)
    if p: p['dates'] = ds; irregular[e] = p

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
    avg, sd = gaps.get(m, (None, None))
    notyet.append([m, avg, sd, (today - d2(last[m])).days, last[m]])
thismonth = {
    'month': ym,
    'done': [[m, n, last[m]] for m, n in donec.most_common()],
    'notYet': notyet,
}

out = {'generated': today.isoformat(), 'totalDays': tot,
       'byDigit': bydigit, 'special': special, 'irregular': irregular,
       'thisMonth': thismonth}
_json.dump(out, open(B + '/data/events.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('イベント集計: 対象%d日 / 不定期%d種 / 今月実施%d機種・未実施%d機種 (%.0fKB)' % (
    tot, len(irregular), len(thismonth['done']), len(notyet),
    os.path.getsize(B + '/data/events.json') / 1024))
for e, p in irregular.items():
    print('   %-12s %d回  %s' % (e, p['days'], ', '.join(p['dates'])))
