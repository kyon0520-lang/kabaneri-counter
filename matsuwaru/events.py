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

# 「モンキーV（青）」「防振り ※1台稼働停止中」のような但し書き付きの表記があり、
# そのままだと機種として拾えず台数を取りこぼす。落としてから名寄せし直す。
_ANN = re.compile(r'[（(][^）)]*[）)]|※.*$')
COLOR_TAG = re.compile(r'[（(](青|赤|黄|緑|紫|ピンク|白|黒|オレンジ|水色)[）)]')
def cn(m):
    c = canon.get(m, m)
    if c in MACHINES: return c
    s = _ANN.sub('', m).strip()
    return canon.get(s, s)
def d2(s):
    y, m, dd = map(int, s.split('-')); return date(y, m, dd)

# --- 対象日ごとの全系機種 ---
days = {}
for a in raw:
    t = a.get('targetDate')
    if not t: continue
    # 台数付きの結果セクションと、連想の見出しの両方から拾う。
    # 連想にしか出てこない機種があり、結果だけだと取りこぼす。
    # 「かぐや様（ピンク）」のような色付きは、その日の機種イベントの対象台を示す
    # 一覧表であって全台系の結果ではない。台数は使うが、全系機種としては数えない。
    ms = {cn(r['machine']) for r in a['results'] if not COLOR_TAG.search(r['machine'])}
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
# 台数の出どころは2つ。ブログの各記事（その日の実測）と、マルハン公式の設置機種ページ
# （取得日つき）。ブログに台数が載らない日があるので、日付がいちばん近いほうを使う。
# 直近の日なら公式のほうが確か、古い日ならその頃のブログ記録のほうが確か。
LINEUP_DATE = LINEUP['fetched'] if LINEUP else None

def units_on(d, m):
    v = UHIST.get(d, {}).get(m)
    if v: return v
    cand = list(_seen.get(m, ()))
    cu = UNITS.get(m)
    if cu and LINEUP_DATE: cand.append((LINEUP_DATE, cu))
    if not cand: return cu
    return min(cand, key=lambda x: abs((d2(x[0]) - d2(d)).days))[1]

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
        # その日群でいちばん多かった台数。台数帯で絞り込むときの代表値にする
        us = collections.Counter(u for u in (units_on(d, m) for d in ds if m in days[d]) if u)
        rows.append([m, k, round(100 * k / n), us.most_common(1)[0][0] if us else 0])
    rows.sort(key=lambda r: (-r[1], -UNITS.get(r[0], 0), -base[r[0]]))
    # 上位3位までをチップに出し、残りは一覧のシートで見せるので全件返す
    return {'label': label, 'days': n, 'small': n < 3, 'top': rows}

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

# 系統（data/machine_groups.json）。その系統の機種が1つでも選ばれた日を数える
_gp = B + '/data/machine_groups.json'
GROUPS = {}
if os.path.exists(_gp):
    GROUPS = {k: set(v) for k, v in _json.load(open(_gp, encoding='utf-8')).items()
              if not k.startswith('_')}

# 種別（ノーマルAタイプ／AT機）。系統と違い「1機種でも入ったか」ではほぼ毎日両方入って
# 差が出ないので、その日に選ばれた機種のうち何割がノーマルかで見る。
_tp = B + '/data/machine_types.json'
NORMAL = set(_json.load(open(_tp, encoding='utf-8'))['ノーマル']) if os.path.exists(_tp) else set()

def norm_share(dates):
    n = sum(len(days.get(d, ())) for d in dates)
    if not n: return None
    k = sum(1 for d in dates for m in days.get(d, ()) if m in NORMAL)
    return {'k': k, 'n': n, 'pct': round(100 * k / n)}

# バラエティ機種＝1台構成。台数は日によって変わるので、その日に1台だった機種で数える。
def variety_share(dates):
    n = sum(len(days.get(d, ())) for d in dates)
    if not n: return None
    k = sum(1 for d in dates for m in days.get(d, ()) if units_on(d, m) == 1)
    return {'k': k, 'n': n, 'pct': round(100 * k / n)}

# 手書きのリード文・結論（data/event_lead.json）。末尾のように、全台系の機種データには
# 出てこない性格を持つ日のためのもの。
_ld = B + '/data/event_lead.json'
LEAD = {k: v for k, v in (_json.load(open(_ld, encoding='utf-8')).items()
                          if os.path.exists(_ld) else []) if not k.startswith('_')}

# 看板機種（data/event_signature.json）。そのイベントで名指しされている機種が
# 実際に入っているか。顔ぶれが途中で変わったイベントは since 以降だけで数える。
_sg = B + '/data/event_signature.json'
SIG = {k: v for k, v in (_json.load(open(_sg, encoding='utf-8')).items()
                         if os.path.exists(_sg) else []) if not k.startswith('_')}

def signature(key, dates):
    cfg = SIG.get(key)
    if not cfg: return None
    ms = set(cfg['machines'])
    ds = [d for d in dates if days.get(d) and (not cfg.get('since') or d >= cfg['since'])]
    if not ds: return None
    hit = [d for d in ds if set(days[d]) & ms]
    cnt = collections.Counter()
    for d in ds:
        for m in set(days[d]) & ms: cnt[m] += 1
    return {'k': len(hit), 'n': len(ds), 'label': cfg['label'],
            'since': cfg.get('sinceNote', ''),
            'top': cnt.most_common(4),
            'miss': [d for d in ds if d not in hit]}

# 小台数（4〜9台）のジャグラー。島単位で狙える形なので、割合で見ると日ごとの差が出る。
JUGGLER = set(GROUPS.get('ジャグラー', ()))
def smalljug_share(dates):
    """開催のうち、小台数（4〜9台）のジャグラーが入った回数"""
    ds = [d for d in dates if days.get(d)]
    if not ds: return None
    k = 0; who = collections.Counter()
    for d in ds:
        hit = [m for m in days[d]
               if m in JUGGLER and 4 <= (units_on(d, m) or 0) <= 9]
        if hit: k += 1
        for m in hit: who[m] += 1
    return {'k': k, 'n': len(ds), 'pct': round(100 * k / len(ds)),
            'top': who.most_common(2)}

def three_share(dates):
    """開催のうち、ちょうど3台構成の機種が入った回数。3台並びの日に効く"""
    ds = [d for d in dates if days.get(d)]
    if not ds: return None
    k = 0; who = collections.Counter()
    for d in ds:
        hit = [m for m in days[d] if units_on(d, m) == 3]
        if hit: k += 1
        for m in hit: who[m] += 1
    return {'k': k, 'n': len(ds), 'pct': round(100 * k / len(ds)),
            'top': who.most_common(3)}

def group_main(dates):
    """系統ごとの「中身」。その系統が入った日のうち、どの機種が何日を占めるか。
    手書きの文中に {山佐} と書くと「（SBJ）」のように差し込むために使う。"""
    out = {}
    for g, mem in GROUPS.items():
        gk = 0; who = collections.Counter()
        for d in dates:
            hit = mem & set(days.get(d, ()))
            if hit: gk += 1
            for m in hit: who[m] += 1
        if not gk: continue
        m, k = who.most_common(1)[0]
        out[g] = [m, k, gk]
    return out

def group_counts(dates):
    c = collections.Counter()
    for d in dates:
        ms = set(days.get(d, ()))
        for g, mem in GROUPS.items():
            if ms & mem: c[g] += 1
    return [[g, n] for g, n in c.most_common()]

# --- 数字まつわり ---------------------------------------------------
# この店は「まつわる」で機種を決める。日付の数字は機種名だけでなく設置台数にも掛かる。
# 例：7のつく日の「アイム 7台」「七つ魔」。台数は末尾一致も見る（17台・27台）。
# 数字の言い換え。ローマ数字は前後に英字が来ないときだけ数として扱う
# （「ToLOVEる」のVや「ストⅥ」のVを5と誤認しないため）。
NUMWORD = {0: ['0', 'ゼロ', 'ZERO', '〇', '零'], 1: ['1', '一', 'ワン'],
           2: ['2', '二', 'ツー'], 3: ['3', '三', 'スリー'],
           4: ['4', '四', 'フォー'], 5: ['5', '五', 'ファイブ'],
           6: ['6', '六', 'シックス'], 7: ['7', '七', 'セブン'],
           8: ['8', '八', 'エイト'], 9: ['9', '九', 'ナイン']}
ROMAN = {5: 'V', 8: 'VIII', 2: 'II', 3: 'III', 6: 'VI', 4: 'IV', 7: 'VII', 9: 'IX'}
def _nu(x): return _ud.normalize('NFKC', x).upper()
_ROMAN_RE = {d: re.compile(r'(?<![A-Z])' + r + r'(?![A-Z])') for d, r in ROMAN.items()}

# 機種名＋読み・別名。まつわりは正式名称にも掛かる（エウレカ＝エウレカセブン＝7）。
# 型番やリール径は数えたくないので、readings.json の「まつわり除外読み」で外す。
_RJ = _json.load(open(B + '/data/readings.json', encoding='utf-8'))
NUM_SKIP = set(_RJ.get('まつわり除外読み', []))
ALIAS = {m: [m] + [r for r in _RJ['readings'].get(m, []) if r not in NUM_SKIP]
         for m in MACHINES}

NUM_FIX = {k: v for k, v in _RJ.get('まつわり数字', {}).items() if not k.startswith('_')}
# その日にだけ通じるまつわり。1日の東京大戦のファンキー（犬→ワン）のように、
# 店の言い伝えとしてその日にだけ掛かるものはイベント単位で持つ
NUM_EVENT = {k: v for k, v in _RJ.get('イベント限定まつわり', {}).items()
             if not k.startswith('_')}

def name_digits(m, dg, aliases, xfix=None):
    """機種名・読みのどれかに、その数字が入っているか"""
    if xfix and m in xfix: return dg in xfix[m]  # そのイベントだけの決めごとが最優先
    if m in NUM_FIX: return dg in NUM_FIX[m]   # 手で決めたものが最優先
    for nm in aliases:
        t = _nu(nm)
        if any(_nu(w) in t for w in NUMWORD[dg]): return True
        if dg in _ROMAN_RE and _ROMAN_RE[dg].search(t): return True
    return False

def event_digit(mt):
    """そのイベントが「何の数字の日」か。決まらないものは None"""
    if 'digit' in mt and len(mt['digit']) == 1: return mt['digit'][0]
    if 'day' in mt:
        ds = {d % 10 for d in mt['day']}
        if len(ds) == 1: return ds.pop()
    return None

def numtie(dates, dg, xfix=None):
    if dg is None: return None
    hit_days = 0; who = collections.Counter(); why = collections.defaultdict(set)
    for d in dates:
        found = False
        for m in days.get(d, ()):
            u = units_on(d, m)
            # 名前でも台数でも掛かる機種がある（北斗転生2＝北斗七星の7かつ7台）。
            # どちらか片方で止めず、両方を理由として残す。
            why_ = []
            if name_digits(m, dg, ALIAS.get(m, [m]), xfix): why_.append('名前')
            if u is not None and u % 10 == dg: why_.append('%d台' % u)
            if why_:
                found = True; who[m] += 1; why[m] |= set(why_)
        if found: hit_days += 1
    if not hit_days: return None
    return {'digit': dg, 'days': hit_days,
            'top': [[m, '・'.join(sorted(why[m], key=lambda x: 0 if x == '名前' else 1)), k]
                    for m, k in who.most_common(4)]}

for p in events:
    p['size'] = size_profile(p['dates'])
    p['numTie'] = numtie(p['dates'], event_digit(p['match']), NUM_EVENT.get(p['key']))
    p['norm'] = norm_share(p['dates'])
    p['vari'] = variety_share(p['dates'])
    p['sjug'] = smalljug_share(p['dates'])
    p['three'] = three_share(p['dates'])
    p['sig'] = signature(p['key'], p['dates'])
    if LEAD.get(p['key']): p['lead'] = LEAD[p['key']]
    p['groups'] = group_counts(p['dates'])
    p['gmain'] = group_main(p['dates'])
    # 多台数が入った日と、その機種（何がその1回を作ったのかを見せる）
    bl, bigdays = {}, set()
    for d in p['dates']:
        for m in days.get(d, ()):
            u = units_on(d, m)
            if not u or u < 20: continue
            bigdays.add(d)
            cur = bl.get(m)
            bl[m] = [m, max(u, cur[1]) if cur else u, (cur[2] + 1) if cur else 1]
    p['bigList'] = sorted(bl.values(), key=lambda x: -x[1])[:4]
    # 中台数が入らなかった日が、多台数を選んだ日と一致するか
    nomid = [d for d in p['dates']
             if not any((units_on(d, m) or 0) >= 10 and (units_on(d, m) or 0) < 20
                        for m in days.get(d, ()))]
    p['midFills'] = bool(nomid) and all(d in bigdays for d in nomid)

# イベント概要（data/event_notes.json に key → 文章。無ければ空）
_np = B + '/data/event_notes.json'
NOTES = {k: v for k, v in (_json.load(open(_np, encoding='utf-8')).items()
                           if os.path.exists(_np) else []) if not k.startswith('_')}
for p in events:
    if NOTES.get(p['key']): p['note'] = NOTES[p['key']]

out = {'generated': today.isoformat(), 'totalDays': tot,
       'sizeAll': size_profile(alldays),
       'groupsAll': group_counts(alldays),
       'normAll': norm_share(alldays),
       'variAll': variety_share(alldays),
       'jug': sorted(JUGGLER),
       'sjugAll': smalljug_share(alldays),
       'threeAll': three_share(alldays),
       'events': events, 'thisMonth': thismonth,
       'schedule': {d: sorted(ks) for d, ks in SCHED.items()}}
_json.dump(out, open(B + '/data/events.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('イベント集計: 対象%d日 / イベント%d件 / 今月実施%d機種・未実施%d機種 (%.0fKB)' % (
    tot, len(events), len(thismonth['done']), len(notyet),
    os.path.getsize(B + '/data/events.json') / 1024))
for p in events:
    tail = ('  ' + '・'.join(x[5:] for x in p['dates'])) if p.get('dates') else ''
    print('   [%s] %-18s %2d日%s' % (p['g'][:4], p['label'] + (' ' + p['sub'] if p['sub'] else ''), p['days'], tail))
