#!/usr/bin/env python3
"""アイコンとOGP画像を書き出す。

    python3 src/make-icons.py

筐体パネルの配色（氷の淡い青・濃紺・深紅・真鍮の金）を参考にした自作のデザイン。
パネルの絵柄やロゴそのものは使っていない。

書き出し先は kabaneri-unato/:
  apple-touch-icon.png (180) / icon-192.png / icon-512.png
  icon-maskable-512.png … Android用。周囲を切り取られても中身が残るよう内側に寄せてある
  ogp.png (1200x630)   … Xでシェアしたときの画像
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))       # src/
DEST = os.path.join(os.path.dirname(BASE), 'kabaneri-unato')

MINCHO = '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc'          # index 2 = W6
GOTHIC_W8 = '/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc'
GOTHIC_W6 = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'

S = 720          # アイコンの下描きサイズ（各サイズへ縮小する）

# パネルから拾った色
BG = ((132, 174, 206), (38, 72, 108))    # 薄明の氷（上→下）
ICE = (226, 240, 250)
EMBER = (255, 140, 58)
RING = (238, 246, 252)
NAVY = (16, 36, 60)
WHITE = (255, 255, 255)

CIRCLES = (((222, 46, 50), (146, 12, 22)),      # 無名（赤）
           ((70, 196, 128), (16, 118, 62)),     # 生駒（緑）
           ((92, 152, 244), (22, 80, 190)))     # 銅藍（青）
CHARS = ['無', '生', '銅']


def mincho(px):
    return ImageFont.truetype(MINCHO, px, index=2)


def gothic8(px):
    return ImageFont.truetype(GOTHIC_W8, px, index=0)


def gothic6(px):
    return ImageFont.truetype(GOTHIC_W6, px, index=0)


def vgrad(size, top, bottom):
    w, h = size
    g = Image.new('RGB', (1, h))
    px = g.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return g.resize((w, h), Image.BICUBIC)


def glow(img, xy, radius, color, strength=90):
    """ぼんやりした光。外側から内側へ明るくなるマスクを作って重ねる"""
    n = 96
    m = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(m)
    for i in range(n // 2, 0, -1):
        d.ellipse((n / 2 - i, n / 2 - i, n / 2 + i, n / 2 + i),
                  fill=int(strength * (1 - i / (n / 2)) ** 2.0))
    m = m.resize((radius * 2, radius * 2), Image.BICUBIC)
    img.paste(Image.new('RGB', (radius * 2, radius * 2), color),
              (xy[0] - radius, xy[1] - radius), m)


def circle(img, box, colors):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    img.paste(vgrad((w, h), *colors), (x0, y0), mask)


def center(d, xy, text, f, fill, stroke=0, stroke_fill=None, spacing=0):
    """中心そろえ。spacing で字間を空ける"""
    if spacing:
        widths = [d.textlength(c, font=f) for c in text]
        total = sum(widths) + spacing * (len(text) - 1)
        _, t, _, b = d.textbbox((0, 0), text, font=f)
        x = xy[0] - total / 2
        for c, w in zip(text, widths):
            d.text((x, xy[1] - (t + b) / 2), c, font=f, fill=fill,
                   stroke_width=stroke, stroke_fill=stroke_fill)
            x += w + spacing
        return
    l, t, r, b = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
    d.text((xy[0] - (l + r) / 2, xy[1] - (t + b) / 2), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)


def sky(size, ember=True):
    """氷の空。左上が明るく、右下に火の粉"""
    w, h = size
    img = vgrad((w, h), *BG).convert('RGB')
    glow(img, (int(w * 0.14), int(h * 0.08)), int(max(w, h) * 0.66), ICE, strength=104)
    if ember:
        glow(img, (int(w * 0.90), int(h * 0.95)), int(max(w, h) * 0.44), EMBER, strength=26)
    return img


def icon_content():
    """アイコンの中身（円と文字）だけを透明地に描く。
    マスカブル用に縮めて置き直せるよう、背景とは分けてある。"""
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    r = int(S * 0.122)
    gap = int(S * 0.042)
    cy = int(S * 0.295)
    xs = [S / 2 - (2 * r + gap), S / 2, S / 2 + (2 * r + gap)]

    for x, col in zip(xs, CIRCLES):
        glow(layer, (int(x), cy), int(r * 2.0), col[0], strength=48)
    d = ImageDraw.Draw(layer)
    for x, col, ch in zip(xs, CIRCLES, CHARS):
        circle(layer, (int(x - r), cy - r, int(x + r), cy + r), col)
        d = ImageDraw.Draw(layer)
        d.ellipse((int(x - r), cy - r, int(x + r), cy + r), outline=RING, width=int(S * 0.0075))
        center(d, (x, cy), ch, mincho(int(r * 1.3)), WHITE)

    center(d, (S / 2, int(S * 0.60)), 'カバネリ', gothic8(int(S * 0.185)),
           NAVY, stroke=int(S * 0.016), stroke_fill=WHITE)
    center(d, (S / 2, int(S * 0.825)), 'カウンター', gothic8(int(S * 0.152)),
           NAVY, stroke=int(S * 0.013), stroke_fill=WHITE)
    return layer


def icon(scale=1.0):
    """scale を下げると中身が内側に寄る（マスカブル用）"""
    bg = sky((S, S)).convert('RGBA')
    content = icon_content()
    if scale != 1.0:
        n = int(S * scale)
        content = content.resize((n, n), Image.LANCZOS)
        pad = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        pad.paste(content, ((S - n) // 2, (S - n) // 2), content)
        content = pad
    return Image.alpha_composite(bg, content).convert('RGB')


def ogp():
    W, H = 1200, 630
    img = sky((W, H))
    d = ImageDraw.Draw(img)

    r, gap = 74, 26
    cy = 196
    xs = [W / 2 - (2 * r + gap), W / 2, W / 2 + (2 * r + gap)]
    for x, col in zip(xs, CIRCLES):
        glow(img, (int(x), cy), int(r * 2.0), col[0], strength=48)
    d = ImageDraw.Draw(img)
    for x, col, ch in zip(xs, CIRCLES, CHARS):
        circle(img, (int(x - r), cy - r, int(x + r), cy + r), col)
        d = ImageDraw.Draw(img)
        d.ellipse((int(x - r), cy - r, int(x + r), cy + r), outline=RING, width=6)
        center(d, (x, cy), ch, mincho(int(r * 1.3)), WHITE)

    center(d, (W / 2, 372), 'カバネリ CZ発光カウンター', mincho(70),
           NAVY, stroke=6, stroke_fill=WHITE, spacing=3)
    center(d, (W / 2, 462), '非発光 1pt ／ 発光 15pt ／ CZ 1回あたりの平均ptを自動計算',
           gothic6(31), (32, 58, 90))
    d.line([(W * 0.30, 522), (W * 0.70, 522)], fill=WHITE, width=3)
    center(d, (W / 2, 566), 'minnanoslot.com/kabaneri-unato', gothic6(28), (38, 66, 100))
    return img


def main():
    out = [
        ('apple-touch-icon.png', icon(), 180),
        ('icon-192.png', icon(), 192),
        ('icon-512.png', icon(), 512),
        ('icon-maskable-512.png', icon(scale=0.72), 512),
    ]
    for name, im, size in out:
        im.resize((size, size), Image.LANCZOS).save(os.path.join(DEST, name))
        print(f'{name} ({size}px)')
    ogp().save(os.path.join(DEST, 'ogp.png'))
    print('ogp.png (1200x630)')


if __name__ == '__main__':
    main()
