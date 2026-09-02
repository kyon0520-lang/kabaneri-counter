# -*- coding: utf-8 -*-
"""エスパス新宿歌舞伎町店の記事解析（スロッターギルド／WordPress REST API）

東宝(lib.py)との違いは SPEC.md の「新しい店舗を足すには」を参照。要点は3つ:
  ・連想チェーンの最後の要素が機種名（東宝は見出し行が機種名）
  ・結果行が1行で完結する（東宝は結果行の3行前まで遡って機種名を探す）
  ・署名行が2つ(ギルド/かぶぱ)あり英語日付なので、署名で本文を上下に割れない
    → 「全台系」「1/2系・高配分」「末尾」の見出しでセクションを判定する

入力は WP REST API が返す投稿オブジェクト（content.rendered を含む）。
"""
import re, html, unicodedata
from datetime import date, timedelta

ARROW = r'(?:[→➡👉⇒▶]|->|=>)'
# 結果行: 「マギレコ (12/13台+） ➡平均 +4,585枚」「■ネオアイム(30/37台+）➡平均+1,388枚」
# 平均は同じ行か次の行に来る。全角/半角の括弧が混在する。
RES = re.compile(r'^[■・▼\s]*(.+?)\s*[(（]\s*([+\-]?\d+)\s*/\s*(\d+)\s*台\s*[+＋]?\s*[)）]')
AVG = re.compile(r'平均\s*([+\-]?[\d,]+)\s*枚')
# 並び行「【3台並び】東京喰種(854-856番台)→平均+3,167枚」。矢印を使うので連想と紛れる
NARABI = re.compile(r'^[【\[]')
# 結果行が自前のラベルを持つ書式もある。見出しではなくこのラベルが正になる。
#   【全台系濃厚】スマスロ北斗の拳(6/8台+）→平均+1,506枚
#   【BF・全台系濃厚】カバネリ海門決戦(23/31台+）→平均+3,960枚
# 【で始まる行を一律に捨てると、この書式の全台系を丸ごと落とす（実際に落としていた）。
TAG = re.compile(r'^[【\[]([^】\]]*)[】\]]\s*')


def tag_section(tag):
    """行頭の【…】から、その行が何かを決める。None は「判別できないので見出しに従う」"""
    if re.search(r'並び|列仕掛け|BOX|ボックス', tag):
        return 'skip'          # 台番号の仕掛け。機種の全台系ではない
    if '末尾' in tag:
        return 'suffix'
    if re.search(r'1/2系|1／2系|高配分', tag):
        return 'high'
    if re.search(r'全台系|全系|全台', tag):
        return 'zen'
    if re.fullmatch(r'(?:BF|B1|[1-9]F|地下)', tag.strip()):
        return 'floor'     # 【3F】のようなフロア表記だけ。見出しの判定に従う
    return None

MONTHS = {m: i + 1 for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June',
     'July', 'August', 'September', 'October', 'November', 'December'])}
# 署名行「— かぶぱ©エスパス 新宿 歌舞伎 町店 (@kabupa777) August 31, 2026」
SIG = re.compile(r'^[—\-–]\s*(.+?)\s*\((@\w+)\)\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})')


def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    return re.sub(r'[\s　]+', '', s)


# 連想の末尾は「マギレコ!?」「カバネリ！？」のように煽りが付く。付いたままだと
# 結果欄の機種名と一致せず、示唆が当たったかを判定できない。
DECO = re.compile(r'^[\s　■・▼『「（(【]+|[\s　!?！？。、…〜~』」）)】]+$')


# 「ファンキー2(3F」「からくりサーカス(7台並び」のように、閉じない括弧が
# 機種名の尻に残る。フロア表記や補足なので落とす。
OPEN_TAIL = re.compile(r'[(（][^)）]*$')


# 「ファンキー2(3F)」のフロアは機種の区別そのものなので、括弧ごと落としてはいけない。
# DECO が末尾の ) を装飾として外し、残った「(3F」を OPEN_TAIL が丸ごと消していた。
FLOOR_PAREN = re.compile(r'[(（]\s*[1-9１-９]\s*[FＦ階]\s*[)）]$')


LEAD = re.compile(r'^[\s　■・▼『「（(【]+')
TRAIL_PLAIN = re.compile(r'[\s　!?！？⁉‼。、…〜~』」】]+$')   # 括弧は含めない
TRAIL_PAREN = re.compile(r'[\s　）)]+$')


def clean_machine(s):
    prev = None
    while prev != s:
        prev = s
        s = LEAD.sub('', s)
        s = TRAIL_PLAIN.sub('', s)    # 先に「!?」などを落としてからフロアを見る
        if FLOOR_PAREN.search(s):     # 末尾がフロア表記なら括弧を触らない
            break
        s = TRAIL_PAREN.sub('', s)
        s = OPEN_TAIL.sub('', s)
    return s


# セクション見出しは <h2>。結果行は <h3> と <p> の両方に出るので行の判定は別。
# 平文化して「短くて。が無い行＝見出し」と見なすと、
# 「良番を掴むだけでこの結果は美味しすぎ！」のような感想文（<p>）を見出しと誤認し、
# その直後の全台系を丸ごと落とす（実際に落としていた）。
HEAD_MARK = '\x01'


def totext(rendered, marks=False):
    """本文HTML → 行の配列。marks=True なら (行, h2かどうか) を返す"""
    b = re.sub(r'<(script|style).*?</\1>', '', rendered, flags=re.S)
    b = re.sub(r'<h2[^>]*>', '\n' + HEAD_MARK, b, flags=re.I)
    b = re.sub(r'<br\s*/?>', '\n', b)
    b = re.sub(r'</(p|div|li|h\d|tr|table|blockquote|figcaption)>', '\n', b)
    b = html.unescape(re.sub(r'<[^>]+>', '', b))
    b = re.sub(r'[ \t　]+', ' ', b)
    out = []
    for l in b.split('\n'):
        h = l.startswith(HEAD_MARK)
        l = l.lstrip(HEAD_MARK).strip()
        if l:
            out.append((l, h) if marks else l)
    return out


def section(head):
    """直前の見出しから、その結果行が何のセクションかを判定する。
       見出しの文言は日によって大きく揺れるので、含まれる語だけで見る。"""
    if not head:
        return None
    # 「全台データ」は店全体の勝率・総差枚の節。見出しに「全台」を含むが全台系ではない
    if re.search(r'全台データ|全体データ', head):
        return None
    # 「恒例の末尾を含めて全台系濃厚が充実！」のように両方を含む見出しがある。
    # 末尾を先に見ると、その節の全台系を丸ごと末尾扱いにしてしまう（実際にしていた）。
    # 末尾行そのものは finalize.py の NON が機種でないと判定するので取りこぼさない。
    if re.search(r'全台系|全系|全台', head):
        return 'zen'
    if '末尾' in head:
        return 'suffix'
    if re.search(r'1/2系|1／2系|高配分', head):
        return 'high'      # 全台系ではない。raw.json に残すが集計には入れない
    return None


FLOOR = re.compile(r'([1-9１-９])\s*[FＦ]')


def floor_of(name):
    """機種名からフロアを読む。「2Fファンキー2」「ファンキー2※3F」「3F・ファンキー2」など"""
    m = FLOOR.search(unicodedata.normalize('NFKC', name))
    return m.group(1) + 'F' if m else None


# 「3が好き→3F」のように、連想の終点がフロアだけの行がある。これは同じ日の
# 別の連想（「トイストーリー1(ワン)→犬→ファンキー」）のフロアを指している。
# 記事側も「上記2つのヒントから、今回は『2Fのファンキー』が当たり」と書いている。
FLOOR_ONLY = re.compile(r'^([1-9])\s*[F階]$')


def _split_cfg(name, split):
    for mname, c in split.items():
        pat = c.get('match')
        if re.search(pat, name) if pat else norm(mname) in norm(name):
            return mname, c
    return None, None


# 本文が言葉でフロアを書いていることがある。
#   「ファンキージャグラーは２・３Fに設置されていますが、おそらく3Fが全台系濃厚。」
#   「2Fのファンキーは全台系濃厚の結果に！」
# 台番の表は画像なので読めない。この文が唯一の手がかりになる日がある。
PROSE_FLOOR = re.compile(r'([1-9])\s*[F階][^。！!]{0,14}?全台系|全台系[^。！!]{0,14}?([1-9])\s*[F階]')


def floor_from_prose(lines, mname, cfg):
    """本文の地の文からフロアを読む。機種と全台系に触れている文だけを見る"""
    pat = cfg.get('match') or re.escape(mname)
    for l in lines:
        if not re.search(pat, l) or '全台系' not in l:
            continue
        m = PROSE_FLOOR.search(l)
        if m:
            f = (m.group(1) or m.group(2)) + 'F'
            if f in cfg['floors']:
                return f
    return None


def floor_hint(assoc, split, lines=()):
    """その日の連想から (フロア, 対象の機種名) を読む。無ければ (None, None)

    2通りある:
      ・フロアだけの行「3が好き→3F」が、別の連想のフロアを指す
      ・連想の終点にフロアが埋まっている「チョウテン→１位→ファンキー3F(3カ国)」
    どちらも、その日のフロア表記がない記録を確定させるのに使える。
    2Fと3Fの両方が名指しされている日は決められないので使わない。
    """
    if not split:
        return None, None
    bare, named = None, {}
    for x in assoc:
        m = FLOOR_ONLY.match(norm(x['machine']))
        if m:
            bare = m.group(1) + 'F'
            continue
        mname, c = _split_cfg(x['machine'], split)
        if mname:
            f = floor_of(x['machine'])
            if f in c['floors']:
                named.setdefault(mname, set()).add(f)
    # 機種名にフロアが埋まっていた場合。1つに定まるときだけ採る
    for mname, fs in named.items():
        if len(fs) == 1:
            return next(iter(fs)), mname
    if bare:
        # フロアだけの行。その日に出ている分割対象の機種に結び付ける
        for x in assoc:
            mname, c = _split_cfg(x['machine'], split)
            if mname and bare in c['floors']:
                return bare, mname
    # 最後に本文の地の文を見る（機種名にもフロアだけの行にも出ていない日）
    for x in assoc:
        mname, c = _split_cfg(x['machine'], split)
        if mname:
            f = floor_from_prose(lines, mname, c)
            if f:
                return f, mname
    return None, None


def split_floors(rows, split, key='machine', day_floor=None, day_machine=None):
    """フロアごとに別枠で動く機種を、別機種として展開する。
       フロア表記のない記録は unmarked の指定に従う（both=全フロアに1件ずつ）。
       表記がないときの台数はフロアごとに違うので捨てる。events.py が
       『その機種の直近の記録』で埋めてくれる。"""
    if not split:
        return rows
    out = []
    for r in rows:
        base = r[key]
        # フロアだけの連想は、その日の対象機種にフロアを付けた形に置き換える
        # （「3が好き→3F」→「3が好き→ファンキー2(3F)」）
        if day_machine and FLOOR_ONLY.match(norm(base)):
            x = dict(r)
            x[key] = '%s(%s)' % (day_machine, day_floor)
            if isinstance(x.get('chain'), list):
                x['chain'] = x['chain'][:-1] + [x[key]]
            out.append(x)
            continue
        cfg = None
        for m, c in split.items():
            pat = c.get('match')
            ok = re.search(pat, base) if pat else (norm(m) in norm(base))
            if ok:
                cfg, mname = c, m
                break
        if not cfg:
            out.append(r)
            continue
        f = floor_of(base)
        # その日にフロア指定の連想があれば、表記のない記録はそれに従う
        if not f and day_floor and mname == day_machine:
            f = day_floor
        floors = [f] if f in cfg['floors'] else (cfg['floors'] if cfg.get('unmarked') == 'both' else [None])
        for fl in floors:
            x = dict(r)
            x[key] = '%s(%s)' % (mname, fl) if fl else mname
            if not f:                      # 表記がなかった記録は台数を持たせない
                for k in ('plus', 'total'):
                    if k in x:
                        x[k] = None
                if isinstance(x.get('result'), dict):
                    x['result'] = {**x['result'], 'plus': None, 'total': None}
            out.append(x)
    return out


def parse_post(post, conf, irregular=(), floors=None):
    """post = WP REST API の投稿オブジェクト。conf = stores.json の1件。
       floors = data/floors.json の split（フロアごとに別枠で動く機種）。"""
    title = html.unescape(re.sub(r'<[^>]+>', '', post['title']['rendered'])).strip()
    rendered = post['content']['rendered']
    marked = totext(rendered, marks=True)
    lines = [l for l, _ in marked]
    # <h2> が1つも無い記事は昔の書式。その場合だけ従来の当て推量に戻す
    has_h2 = any(h for _, h in marked)
    article_date = post['date'][:10]

    # --- 対象日: タイトル冒頭の「9月1日(火)｜…」 ---
    target = None
    m = re.match(r'\s*(\d+)月(\d+)日', title)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = int(article_date[:4])
        # 1月1日の記事が1月2日に出るような年跨ぎ
        if mo == 12 and article_date[5:7] == '01':
            y -= 1
        target = '%04d-%02d-%02d' % (y, mo, d)

    # --- 示唆ポスト: かぶぱの署名行から投稿者と投稿日 ---
    tenchou, post_date = None, None
    for l in lines:
        sm = SIG.match(l)
        if sm and 'kabupa' in sm.group(2):
            tenchou = sm.group(2)
            mo = MONTHS.get(sm.group(3))
            if mo:
                post_date = '%s-%02d-%02d' % (sm.group(5), mo, int(sm.group(4)))
            break
    if not tenchou:
        tenchou = '@kabupa777'
    if not post_date and target:
        # かぶぱポストは前日21時頃に出る
        y, mo, d = map(int, target.split('-'))
        post_date = str(date(y, mo, d) - timedelta(days=1))

    # --- 示唆ポストのURL: かぶぱの引用ブロックにある status リンク ---
    tweet_url = None
    for u in re.findall(r'https://(?:twitter|x)\.com/([A-Za-z0-9_]+)/status/(\d+)', rendered):
        if 'kabupa' in u[0].lower():
            tweet_url = 'https://twitter.com/%s/status/%s' % u
            break

    # --- 結果行: 直前の見出しでセクションを判定して振り分ける ---
    results, high, order, seen_head = {}, [], [], None
    for i, (l, is_h2) in enumerate(marked):
        if has_h2 and is_h2:
            seen_head = l
            continue
        body, override = l, None
        tm = TAG.match(l)
        if tm:
            override = tag_section(tm.group(1))
            if override == 'skip':
                continue
            if override is None:   # 判別できない【】は並びのことが多いので触らない
                continue
            if override == 'floor':
                override = None    # 見出しの判定にゆだねる
            body = l[tm.end():]
        rm = RES.match(body)
        if rm:
            sec = override or section(seen_head)
            if sec not in ('zen', 'high', 'suffix'):
                continue
            name = clean_machine(rm.group(1))
            # 「勝率 45.0％ (337/749台)」のような店全体の集計行が紛れる
            if not name or len(name) > 30 or re.search(r'勝率|総差枚|^平均', name):
                continue
            am = AVG.search(l) or (AVG.search(lines[i + 1]) if i + 1 < len(lines) else None)
            row = {'machine': name, 'plus': int(rm.group(2)), 'total': int(rm.group(3)),
                   'avg': int(am.group(1).replace(',', '')) if am else None}
            if sec == 'high':
                # 全台系ではないので集計には出さない。取り直しを避けるため正本にだけ残す
                high.append(row)
                continue
            k = norm(name)
            if k not in results:
                results[k] = row
                order.append(k)
        elif (not has_h2 and not NARABI.match(l) and len(l) <= 45
              and '。' not in l and not l.startswith('http')):
            seen_head = l

    # --- 連想 ---
    # 導入文の書き方が日によって違うため、マーカーだけに頼ると丸ごと落とす。
    # 「今回は以下の3機種がヒントの答えだったと思われます」（2025-07-14）は
    # どのマーカーにも当たらず、その日の連想が全部消えていた。
    # そこで「マーカー直後のブロック」に加えて「行頭が箇条書き記号の行」も拾う。
    # 記号は ■・◆▼🔑┗※ と揺れるが、地の文と紛れないので判定に使える。
    BULLET = '■・･▼◆◇●○🔑┗└※'

    def as_chain(l0):
        """連想として使える行なら (機種, 連鎖) を返す"""
        if NARABI.match(l0) or '番台' in l0 or RES.match(l0) or len(l0) > 150:
            return None
        # 「ToLOVEる8.7＋ToLOVEる【28–31】 ➡ 平均 +5,525枚」は並びの行。
        # 行頭が【ではないので NARABI をすり抜ける
        if re.search(r'【\s*\d+\s*[–\-—〜~]\s*\d+\s*】', l0) or re.search(r'枚\s*$', l0):
            return None
        if not re.search(ARROW, l0):
            return None
        chain = [c.strip(' 　' + BULLET) for c in re.split(ARROW, l0) if c.strip(' 　' + BULLET)]
        if len(chain) < 2:
            return None
        machine = clean_machine(chain[-1])   # ★東宝と違い、連鎖の最後が機種名
        if not machine or len(machine) > 30:
            return None
        return machine, chain

    def block_range(s0):
        e0 = None
        for j in range(s0 + 1, len(lines)):
            if re.match(r'^かぶぱポスト', lines[j]) or re.search(r'ヒントが隠されている', lines[j]):
                e0 = j
                break
        return range(s0 + 1, (e0 if e0 else s0 + 9))

    marks = [i for i, l in enumerate(lines)
             if re.search(r'ヒントを確認|下記のヒント|ヒントはコチラ|ヒントがあった|ヒントの答え', l)]
    inblk = set()
    for s0 in marks:
        rng = [j for j in block_range(s0) if j < len(lines)]
        if any(as_chain(lines[j]) for j in rng):
            inblk = set(rng)
            break

    assoc = []
    for i, l0 in enumerate(lines):
        if i not in inblk and l0[0] not in BULLET:
            continue
        got = as_chain(l0)
        if not got:
            continue
        machine, chain = got
        k = norm(machine)
        r = results.get(k)
        assoc.append({'machine': machine, 'matched': k in results,
                      'keyword': chain[0], 'chain': chain, 'raw': l0,
                      'result': {x: r[x] for x in ('plus', 'total', 'avg')} if r else None})

    flat = title + ' ' + ' '.join(lines)
    # irregular は {'label','pattern','excludes'} の配列（(label, pattern) のタプルも可）
    _irr = [x if isinstance(x, dict) else {'label': x[0], 'pattern': x[1]} for x in irregular]
    events = [x['label'] for x in _irr if re.search(x['pattern'], flat)]
    # 記事は比較のために別のイベント名も何度も出す（「はぐれキングぱないなー」の記事に
    # 「キングぱないなー」が10回以上出る）。文字列では区別できないので排他を宣言で解く。
    drop = {y for x in _irr if x['label'] in events for y in x.get('excludes', [])}
    events = [e for e in events if e not in drop]

    dfl, dmc = floor_hint(assoc, floors, lines)
    res = split_floors([results[k] for k in order], floors, day_floor=dfl, day_machine=dmc)
    asc = split_floors(assoc, floors, day_floor=dfl, day_machine=dmc)
    return {'events': events, 'articleUrl': post['link'], 'articleDate': article_date,
            'targetDate': target, 'postDate': post_date, 'tenchou': tenchou,
            'tweetUrl': tweet_url, 'title': title,
            'results': res, 'assoc': asc,
            'unassigned': [], 'highShare': high}
