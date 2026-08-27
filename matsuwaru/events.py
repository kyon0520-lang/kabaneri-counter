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
LINEUP, INSTALLED, UNITS = None, None, {}
UHIST = {}   # 日付 → {機種: その日の台数}
_lp = B + '/data/lineup.json'
if _os.path.exists(_lp):
    LINEUP = _json.load(open(_lp, encoding='utf-8'))
    _rj = _json.load(open(B + '/data/readings.json', encoding='utf-8'))
    _read = _rj['readings']
    _adj = _rj.get('ラインナップ照合', {})
    _out = set(_adj.get('対象外', []))     # 現行にないと分かっている機種
    _only = _adj.get('限定', {})           # 照合にこの名前だけを使う機種
    _ng = _adj.get('除外語', {})           # この語を含む設置機種には当てない（アイム↔ネオアイム）
    import unicodedata as _ud
    def _n(x):
        return re.sub(r'[\s\u3000/／・~〜\-!！?？:：\.]', '', _ud.normalize('NFKC', x).lower())
    _hall = [(_n(nm), u) for nm, u in LINEUP['slots']]
    def _match(m):
        """(設置しているか, 台数) を返す"""
        if m in _out: return False, 0
        # 詳しい名前から先に当てる（からくり2 が からくり より先に決まるように）
        cand = _only[m] if m in _only else [m] + _read.get(m, [])
        for k in sorted(set(cand), key=len, reverse=True):
            if len(_n(k)) < 2: continue
            ng = [_n(x) for x in _ng.get(m, [])]
            hit = [u for h, u in _hall if _n(k) in h and not any(g in h for g in ng)]
            if hit: return True, sum(hit)
        return False, 0
    _mt = {m: _match(m) for m in MACHINES}
    INSTALLED = {m for m, (ok, _) in _mt.items() if ok}
    UNITS = {m: u for m, (ok, u) in _mt.items() if ok}
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
    # その日の台数（入れ替えで変わるので、現在の設置台数ではなく実施当日の値を使う）
    u = {}
    for r in a['results']:
        m = cn(r['machine'])
        if m in MACHINES and r.get('total'): u[m] = r['total']
    for x in a['assoc']:
        if not x.get('machine'): continue
        m = cn(x['machine']); res = x.get('result') or {}
        if m in MACHINES and res.get('total'): u.setdefault(m, res['total'])
    UHIST[t] = u
alldays = sorted(days)

# 台数が載っていない日は、その機種の直近の記録で埋める（入れ替えは月曜なので近い日ほど確か）
_seen = collections.defaultdict(list)
for _t in alldays:
    for _m, _u in UHIST.get(_t, {}).items(): _seen[_m].append((_t, _u))
def units_on(d, m):
    v = UHIST.get(d, {}).get(m)
    if v: return v
    rec = _seen.get(m)
    if rec: return min(rec, key=lambda x: abs((d2(x[0]) - d2(d)).days))[1]
    return UNITS.get(m)   # ブログに一度も台数が出ていない機種は現在の設置台数で代用

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
    rows.sort(key=lambda r: (-r[1], -UNITS.get(r[0], 0), -base[r[0]]))
    return {'label': label, 'days': n, 'small': n < 3, 'top': rows[:8]}

# --- 定義ファイルに従ってイベントを組み立てる（表示順もこの順） ---
DEFS = _json.load(open(B + '/data/event_defs.json', encoding='utf-8'))

def lastday(d):
    return (d2(d) + timedelta(days=1)).day == 1

# 店長ポストで判明した、日付ルールと食い違うイベント（data/schedule.json）。
# ここに載っている日は日付からの自動判定を捨てて、書かれたkeyだけをその日のイベントとする。
_sp = B + '/data/schedule.json'
SCHED = {}
if os.path.exists(_sp):
    SCHED = {d: set(v) for d, v in _json.load(open(_sp, encoding='utf-8')).items()
             if not d.startswith('_')}

def rule_dates(mt):
    """日付ルールだけで出した該当日（不定期イベントによる置き換えは考えない）"""
    if 'digit' in mt:
        return [d for d in alldays if int(d[-2:]) % 10 in mt['digit']]
    if 'day' in mt:
        return [d for d in alldays if int(d[-2:]) in mt['day']]
    if mt.get('monthend'):
        return [d for d in alldays if lastday(d)]
    return []

_rule_dates = rule_dates
def rule_dates(mt):
    ds = set(_rule_dates(mt))
    # 定例日から外れた開催もこのイベントに合流させる（やばたにえんの23日以外など）
    if mt.get('irregularAlso'):
        ds |= set(irr.get(mt['irregularAlso'], [])) & set(alldays)
    return sorted(ds)

# 不定期イベントの日は定例イベントが走っていない（上乗せではなく置き換え）ので、
# その日を定例イベントの母数から外す。
# ただし「やばたにえん＝23日」のように定例としても組んであるものは、
# その定例の日に当たる分は置き換えではないため除外に数えない（scheduled で指定）。
IRR_DATES = {}      # イベントkey → 置き換えが起きた日
_replaced = set()   # 置き換えが起きた日の集合
for _g, _items in DEFS.items():
    if _g.startswith('_'): continue
    for _it in _items:
        if 'irregular' not in _it['match']: continue
        _ds = [d for d in irr.get(_it['match']['irregular'], []) if d in alldays]
        _sch = _it.get('scheduled')
        if _sch:
            _sd = set()
            for _g2, _i2 in DEFS.items():
                if _g2.startswith('_'): continue
                for _x in _i2:
                    if _x['key'] == _sch: _sd = set(rule_dates(_x['match']))
            _ds = [d for d in _ds if d not in _sd]
        IRR_DATES[_it['key']] = sorted(_ds)
        _replaced |= set(_ds)

# グループの優先順位（先にあるほど強い）。上位グループのイベントがある日は
# 下位グループのイベントは走っていないので、その日を母数から外す。
# 例：23日は21-27WEEK（やばたにえん）なので3のつく日には数えない。
PRIO = DEFS.get('_優先順位') or ['不定期イベント', '特別な日', '◯のつく日']
_claimed = {}
for _g in PRIO:
    _ds = set()
    for _it in DEFS.get(_g, []):
        _ds |= (set(IRR_DATES.get(_it['key'], [])) if 'irregular' in _it['match']
                else set(rule_dates(_it['match'])))
    _claimed[_g] = _ds

def outranked(group):
    up = set()
    for g in PRIO:
        if g == group: break
        up |= _claimed.get(g, set())
    return up

def match_dates(mt, key, group):
    if 'irregular' in mt:
        ds = list(IRR_DATES.get(key, []))
    else:
        ds = [d for d in rule_dates(mt) if d not in outranked(group)]
    # 店長ポストで判明した日は、その日に指定されたイベントだけを残す／足す
    ds = [d for d in ds if key in SCHED.get(d, {key})]
    ds += [d for d, ks in SCHED.items() if key in ks and d in alldays and d not in ds]
    return sorted(set(ds))

events = []
for group, items in DEFS.items():
    if group.startswith('_'): continue
    for it in items:
        ds = match_dates(it['match'], it['key'], group)
        p = profile(ds, it['label'])
        if not p: continue
        p.update({'g': group, 'key': it['key'], 'sub': it.get('sub', ''),
                  'match': it['match']})
        p['dates'] = ds
        events.append(p)
print('   不定期による置き換え %d日' % len(_claimed.get('不定期イベント', ())))

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

# --- 台数の傾向（多=20台以上／中=10〜19台／小=9台以下） ---
# 台数は現在の設置台数。撤去済みで台数が分からない機種は母数から外す。
def size_profile(dates):
    """「その日に○台数の機種が1つでも選ばれたか」を開催日ごとに数える。
    ユーザーは日付で「この日は多台数が来ないな」と読むので、延べ機種数ではなく日数で出す。"""
    c = collections.Counter(); us = []; picked = 0; n = 0
    for d in dates:
        ms = days.get(d, ())
        if not ms: continue
        n += 1; picked += len(ms)
        seen = set()
        for m in ms:
            u = units_on(d, m)
            if u is None: continue
            seen.add('big' if u >= 20 else ('mid' if u >= 10 else ('small' if u >= 4 else 'tiny')))
            us.append(u)
        for b in seen: c[b] += 1
    if not n or not us: return None
    return {'n': n,
            'big': round(100 * c['big'] / n), 'mid': round(100 * c['mid'] / n),
            'small': round(100 * c['small'] / n), 'tiny': round(100 * c['tiny'] / n),
            'bigN': c['big'], 'midN': c['mid'], 'smallN': c['small'], 'tinyN': c['tiny'],
            'avg': round(sum(us) / len(us), 1),
            'perDay': round(picked / n, 1)}

for p in events:
    p['size'] = size_profile(p['dates'])

# イベント概要（data/event_notes.json に key → 文章。無ければ空）
_np = B + '/data/event_notes.json'
NOTES = {k: v for k, v in (_json.load(open(_np, encoding='utf-8')).items()
                           if os.path.exists(_np) else []) if not k.startswith('_')}
for p in events:
    if NOTES.get(p['key']): p['note'] = NOTES[p['key']]

out = {'generated': today.isoformat(), 'totalDays': tot,
       'sizeAll': size_profile(alldays),
       'events': events, 'thisMonth': thismonth,
       'schedule': {d: sorted(ks) for d, ks in SCHED.items()}}
_json.dump(out, open(B + '/data/events.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('イベント集計: 対象%d日 / イベント%d件 / 今月実施%d機種・未実施%d機種 (%.0fKB)' % (
    tot, len(events), len(thismonth['done']), len(notyet),
    os.path.getsize(B + '/data/events.json') / 1024))
for p in events:
    tail = ('  ' + '・'.join(x[5:] for x in p['dates'])) if p.get('dates') else ''
    print('   [%s] %-18s %2d日%s' % (p['g'][:4], p['label'] + (' ' + p['sub'] if p['sub'] else ''), p['days'], tail))
