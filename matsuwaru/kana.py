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

    target = [w for w in words if KANJI.search(w)]
    missing = sorted(w for w in target if w not in cache)
    if missing:
        made = _convert(missing)
        if made is None:
            print('  読みを作れません（pykakasi 未導入）。新しい語 %d 件は'
                  'ひらがなで引けません: %s' % (len(missing), '・'.join(missing[:5])))
        else:
            cache.update(made)
            out = {'_説明': NOTE}
            out.update({k: cache[k] for k in sorted(cache)})
            json.dump(out, open(path, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            print('  読みを %d 件追加（合計 %d 件）'
                  % (sum(1 for v in made.values() if v), sum(1 for v in cache.values() if v)))

    _lost = [w for w in manual if w not in target]
    if _lost: print('  読みの対象が見つからない語: ' + '、'.join(_lost))

    got = {}
    for w in target:
        rs = [r for r in [cache.get(w)] + manual.get(w, []) if r and r != w]
        if rs:
            got[w] = list(dict.fromkeys(rs))
    return got
