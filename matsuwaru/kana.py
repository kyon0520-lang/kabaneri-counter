# -*- coding: utf-8 -*-
"""漢字の語に、検索用のひらがな読みを付ける。

表示にはいっさい使わない。「人参」を「にんじん」でも引けるようにするためだけのもの。
読みは pykakasi に作らせ、data/token_readings.json に貯めていく。

いちど作った読みは消さない。pykakasi が入っていない環境で作り直しても、
きのうまで引けていた言葉が急に引けなくなることがないようにするため。
そのぶんファイルは増え続けるが、語の数はたかだか数千なので放っておいてよい。

読みが違うとき（甲鉄城→こうてつしろ など）は readings.json の「語の読み」に
正しい読みを書き足す。書いた読みは自動の読みに"足される"（置き換えない）。
まちがった読みが1つ余分に残っても、誰もその字面では検索しないので害はない。
逆に置き換えにすると、別名を足したいだけのときに正しい読みを消してしまう。
"""
import json, os, re

KANJI = re.compile(r'[一-鿿々〆ヶ]')          # 読みを作る対象。カナ・かなは正規化で足りる

# 台数・日付の「かたち」だけを表す語には読みを付けない。
# 「5台機種」に読みを付けると「5だいきしゅ」になり、「だい」「きしゅ」で
# 台数表記が全部当たってしまう（実測で「きしゅ」が12件→173件）。
# この種の語は台数タブ・日付タブから辿るもので、読みで引く必要がない。
#
# 見分け方：数字・記号・ひらがな・ラテン文字を落とし、残った漢字が
# 「台・機種・設置・日・月・年・目・就任…」だけなら、かたちだけの語とみなす。
# 「花火の日」は花火が、「大都機種」は大都が、「黒筐体、5台」は黒筐体が残るので、
# 中身のある語はここで落ちない。カタカナも中身とみなして残す（「2台レールガン2」）。
# 一字だけの「月」「日」はそれ自体が示唆なので対象外にする。
CORE = re.compile(r'[^一-鿿々〆ァ-ヶ]')     # 漢字とカタカナ以外を落とす
FORM = re.compile(r'台|機種|設置|減|増|入替|日|月|年|目|周|就任|文字|字|全系')


def _form_only(w):
    # 一字の語（「月」「日」「台」）はそれ自体が示唆なので、かたちとはみなさない
    return len(w) > 1 and not FORM.sub('', CORE.sub('', w))


CACHE = 'data/token_readings.json'
NOTE = ('検索用のひらがな読み。pykakasi が自動で作ったもので、表示には使わない。'
        '読みが違うときは readings.json の「語の読み」に正しい読みを書く（そちらが勝つ）。'
        'このファイルは手で編集しなくてよい。')


def _convert(words):
    """pykakasi で読みを作る。入っていなければ None を返す（作らないだけで落とさない）"""
    try:
        import pykakasi
    except ImportError:
        return None
    k = pykakasi.kakasi()
    out = {}
    for w in words:
        h = ''.join(x['hira'] for x in k.convert(w))
        # 読みが元の字と同じ語も空で覚えておく。毎回やり直さないため
        out[w] = h if h != w else ''
    return out


def build(base, words, manual=None):
    """words のうち漢字を含むものに読みを付けて返す（語 → 読みの一覧）。

    base は店舗ディレクトリ。manual の値は文字列でも一覧でもよい。
    """
    manual = {w: ([r] if isinstance(r, str) else list(r))
              for w, r in (manual or {}).items() if r and not w.startswith('_')}
    path = os.path.join(base, CACHE)
    cache = {}
    if os.path.exists(path):
        cache = {k: v for k, v in json.load(open(path, encoding='utf-8')).items()
                 if not k.startswith('_')}

    target = [w for w in words if KANJI.search(w) and not _form_only(w)]
    # 対象から外した語の読みが残っていたら捨てる（見分け方を変えたときの掃除）
    stale = [w for w in cache if _form_only(w)]
    for w in stale: del cache[w]
    missing = sorted(w for w in target if w not in cache)
    if missing or stale:
        made = _convert(missing) if missing else {}
        if made is None:
            print('  読みを作れません（pykakasi 未導入）。新しい語 %d 件は'
                  'ひらがなで引けません: %s' % (len(missing), '・'.join(missing[:5])))
        else:
            cache.update(made)
            out = {'_説明': NOTE}
            out.update({k: cache[k] for k in sorted(cache)})
            json.dump(out, open(path, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            print('  読みを %d 件追加%s（合計 %d 件）'
                  % (sum(1 for v in made.values() if v),
                     '・%d 件を対象外として削除' % len(stale) if stale else '',
                     sum(1 for v in cache.values() if v)))

    _lost = [w for w in manual if w not in target]
    if _lost: print('  読みの対象が見つからない語: ' + '、'.join(_lost))

    got = {}
    for w in target:
        rs = [r for r in [cache.get(w)] + manual.get(w, []) if r and r != w]
        if rs:
            got[w] = list(dict.fromkeys(rs))
    return got
